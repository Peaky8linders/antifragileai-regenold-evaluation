"""Checkpointed live evaluation of the 20 Antifragile expert-review questions,
generated on AWS Bedrock and graded by an LLM judge that reads the expert's own
remarks.

WHY THIS EXISTS, given ``antifragile_live.py`` already scores these 20 rows:

* ``antifragile_live`` has **no checkpoint**. It accumulates rows in memory and
  writes one JSON at the end, so a throttle or a timeout on row 18 destroys the
  seventeen answers already paid for. On Bedrock, where a single enumerative
  Stage-2 answer costs 38-62 s, that is an expensive way to learn nothing.
* ``antifragile_live`` has **no judge**. It scores lexical overlap against a
  ~60-word synthesized gold, plus substring proxies for the expert's flagged
  mistakes. Those proxies are honest about being proxies — the module says so —
  but they cannot see the defect the expert complained about most often, which
  is a citation that the answer body never discusses.
* ``antifragile_live`` **requires a remote endpoint**. This module runs the same
  wire in-process through FastAPI's ``TestClient``, so the route-level passes
  under test (Component D, the parent-collapse, the sentence/char caps) all
  execute, with no deploy in the loop.

Both phases checkpoint per row to JSONL and resume by skipping ids already
present, so an interrupted run resumes instead of restarting.

TRUNCATION IS TREATED AS A FIRST-CLASS FAILURE, at every stage. The operator
directive for this system is that nothing may be silently cut, so this module
records, per row: the Stage-2 ``stopReason`` as reported in the reasoning trace,
whether the answer ends on terminal punctuation, the reference-clamp note, the
judge call's ``finish_reason``, and the judge's token usage against its ceiling.
A judge reply cut at ``max_tokens`` is recorded as ``judge_truncated`` and is
NOT scored — an unparseable reply must never become a silent zero that divides
into the pass rate.

Usage::

    # both phases, fresh
    py -3.12 -m evals.regenold.antifragile_bedrock --label r333

    # resume an interrupted run (skips ids already checkpointed)
    py -3.12 -m evals.regenold.antifragile_bedrock --label r333 --resume

    # re-judge existing generations without regenerating
    py -3.12 -m evals.regenold.antifragile_bedrock --label r333 --phase judge --resume
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any

# ── Model pins ───────────────────────────────────────────────────────────────
# Operator ask (2026-08-14): Opus 4.6 for the RAG, Sonnet 4.6 for the judge.
# These are the tiers this account is measured to be ENTITLED to invoke; the
# newer pins (opus-4-8 / opus-5 / sonnet-5) return AccessDeniedException on the
# current key. Pinning them EXPLICITLY rather than letting the entitlement
# fallback chain reach them matters twice over: it saves a 403 round-trip on
# every call, and — because the chain would otherwise serve a tier nobody chose
# — it keeps ``stage2_models`` in the artifact equal to what was requested.
DEFAULT_RAG_MODEL = "eu.anthropic.claude-opus-4-6-v1"
DEFAULT_JUDGE_MODEL = "eu.anthropic.claude-sonnet-4-6"

# Generous by design. The ceiling must never be the thing that stops the model:
# an answer that has to enumerate eight Article 5 prohibitions, four Article
# 6(3) carve-outs and four risk tiers is legitimately long, and a cut there is
# indistinguishable from the incomplete-enumeration defect we are measuring.
DEFAULT_JUDGE_MAX_TOKENS = 8000

_OUT_ROOT = Path(".evalout/antifragile-bedrock")


# ── Checkpoint I/O ───────────────────────────────────────────────────────────


def _ckpt_path(out_dir: Path, phase: str, label: str) -> Path:
    return out_dir / f"{phase}-{label}.jsonl"


def _load_ckpt(path: Path) -> dict[str, dict[str, Any]]:
    """Read a checkpoint into ``{id: row}``.

    Tolerates a torn final line: a run killed mid-``write`` leaves a partial
    JSON object, and refusing to resume because of it would defeat the point of
    checkpointing at all. Complete rows before the tear are kept.
    """
    if not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            print(f"  ! checkpoint has a torn line; keeping the {len(out)} complete rows")
            continue
        if isinstance(rec, dict) and rec.get("id"):
            out[rec["id"]] = rec
    return out


def _append_ckpt(path: Path, rec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


# ── Truncation forensics ─────────────────────────────────────────────────────

_TERMINAL = tuple(".!?\"')]}*`")


def _truncation_forensics(answer: str, reasoning_raw: str | None) -> dict[str, Any]:
    """Everything we can say about whether this answer was cut.

    ``stopReason`` is the only honest signal and it reaches us through the
    reasoning trace, so read the notes rather than guessing from the prose. The
    prose heuristic is kept only as a secondary flag: a false positive there is
    expensive (it discards the Stage-2 polish and re-arms the sentence cap), so
    it is reported, never acted on.
    """
    notes: list[str] = []
    stage2_model = None
    stage2_polish = None
    if reasoning_raw:
        try:
            d = json.loads(reasoning_raw)
            notes = list(d.get("notes") or [])
            stage2_polish = d.get("stage2_polish")
        except (ValueError, TypeError):
            notes = []
    for n in notes:
        m = re.search(r"stage2_model=(\S+)", n)
        if m:
            stage2_model = m.group(1)

    def _note_like(*frags: str) -> list[str]:
        return [n for n in notes if any(f in n for f in frags)]

    stripped = answer.rstrip()
    return {
        "stage2_model": stage2_model,
        "stage2_polish": stage2_polish,
        "stage2_truncated_note": _note_like("stage2_truncated", "truncated_max_tokens"),
        "ref_clamp_note": _note_like("adaptive_ref_clamp_to=", "final_ref_clamp"),
        "dropped_note": _note_like("dropped_over_budget", "dropped_", "[...]"),
        "notes_overflow": _note_like("notes_truncated", "note_overflow"),
        "ends_on_terminal_punctuation": bool(stripped) and stripped.endswith(_TERMINAL),
        "answer_chars": len(answer),
        "answer_sentences": len([s for s in re.split(r"(?<=[.!?])\s+", stripped) if s.strip()]),
        "all_notes": notes,
    }


# ── Phase A: generation ──────────────────────────────────────────────────────


def _warm(verbose: bool) -> None:
    """Warm the graph client before the first timed row.

    A cold TLS + driver handshake to Aura measured a MISS against the 750 ms
    graph budget on query 1 and 40-68 ms on every query after, so without this
    the first row of the batch silently loses its graph context and its latency
    is not comparable to the rest.
    """
    try:
        from app.graph.client import get_graph_client

        c = get_graph_client()
        if not getattr(c, "enabled", False):
            if verbose:
                print("  graph: DISABLED (no driver / no DSN) — rows will run without graph context")
            return
        t0 = time.perf_counter()
        try:
            c.run("RETURN 1 AS ok", {})
        except Exception:  # noqa: BLE001 — a failed warm-up is not a failed run
            pass
        if verbose:
            print(f"  graph: warmed in {(time.perf_counter() - t0) * 1000:.0f} ms")
    except Exception as exc:  # noqa: BLE001
        if verbose:
            print(f"  graph: warm-up skipped ({type(exc).__name__})")


def run_generation(*, label: str, out_dir: Path, resume: bool, limit: int | None,
                   timeout: float, throttle: float, verbose: bool) -> dict[str, dict[str, Any]]:
    from fastapi.testclient import TestClient

    from evals.regenold.antifragile_groundtruth import ANTIFRAGILE_GT
    from evals.regenold.runner_v2 import _ensure_local_auth, _USER_AGENT

    path = _ckpt_path(out_dir, "gen", label)
    done = _load_ckpt(path) if resume else {}
    if not resume and path.exists():
        # Each run owns its checkpoint. Merging a previous run's rows into this
        # one silently mixes two configurations in a single artifact, which is
        # exactly the confusion the label is supposed to prevent.
        path.unlink()
        done = {}

    qids = list(ANTIFRAGILE_GT.keys())
    if limit:
        qids = qids[:limit]
    todo = [q for q in qids if q not in done]
    print(f"[gen] {len(todo)} to run, {len(done)} already checkpointed -> {path}")
    if not todo:
        return done

    key = _ensure_local_auth()
    headers = {"User-Agent": _USER_AGENT, "X-Regenold-Api-Key": key}

    from app.main import app as _app

    with TestClient(_app) as client:
        _warm(verbose)
        try:
            from app.rate_limit import limiter as _limiter
        except Exception:  # noqa: BLE001
            _limiter = None

        for qid in todo:
            gt = ANTIFRAGILE_GT[qid]
            if _limiter is not None:
                try:
                    _limiter.reset()
                except Exception:  # noqa: BLE001
                    pass
            t0 = time.perf_counter()
            status, body, err = 0, {"answer": "", "references": [], "reasoning": None}, None
            try:
                resp = client.post(
                    "/api/v1/regenold/eu-ai-act/ask?include_reasoning=true",
                    json=[{"role": "user", "content": gt["question"]}],
                    headers=headers,
                    timeout=timeout,
                )
                status = resp.status_code
                try:
                    parsed = resp.json()
                    if isinstance(parsed, dict):
                        body = parsed
                except ValueError:
                    err = "json_decode"
                if err is None and not (200 <= status < 300):
                    err = f"http_{status}"
            except Exception as exc:  # noqa: BLE001
                err = f"local_error: {type(exc).__name__}: {exc}"[:300]
            elapsed = (time.perf_counter() - t0) * 1000.0

            answer = body.get("answer") or ""
            refs = body.get("references") or []
            reasoning_raw = body.get("reasoning")
            rec = {
                "id": qid,
                "question": gt["question"],
                "answer": answer,           # FULL, never previewed here
                "references": refs,
                "reasoning_raw": reasoning_raw,
                "http_status": status,
                "latency_ms": round(elapsed, 1),
                "error": err,
                "truncation": _truncation_forensics(answer, reasoning_raw),
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            _append_ckpt(path, rec)
            done[qid] = rec
            if verbose:
                t = rec["truncation"]
                flag = ""
                if t["stage2_truncated_note"]:
                    flag += " !TRUNC"
                if not t["ends_on_terminal_punctuation"] and answer:
                    flag += " !NOTERM"
                if err:
                    flag += f" !{err[:28]}"
                print(f"  [{qid}] {status} {rec['latency_ms']:>7.0f}ms "
                      f"model={t['stage2_model']} polish={t['stage2_polish']} "
                      f"chars={t['answer_chars']:>5} sent={t['answer_sentences']:>2} "
                      f"refs={len(refs)}{flag}")
            time.sleep(throttle)
    return done


# ── Phase B: the judge ───────────────────────────────────────────────────────

_JUDGE_SYSTEM = """You are an EU AI Act legal expert grading answers produced by a \
retrieval-augmented compliance assistant, working to Regulation (EU) 2024/1689 as \
ADOPTED (in force 1 August 2024, CELEX 32024R1689). Do NOT apply the Digital Omnibus \
or any later amendment.

You are given, for each question: the remarks a human EU AI Act expert wrote when \
grading an EARLIER answer to the same question, a corrected reference answer, the \
corrected citation set, and the NEW answer now under review.

Grade the NEW answer. The earlier answer and the expert's remarks are context that \
tells you which mistakes matter here — they are NOT the thing being graded, and the \
new answer must not be penalised for a defect it does not have, nor credited for \
avoiding one it still has.

Judge law, not style. Be exacting about four things the expert repeatedly flagged:
 1. CITATIONS THAT THE BODY NEVER DISCUSSES. A reference is only earned if the answer \
    actually says something about that provision. Listing a provision the prose never \
    addresses is a defect, however apt the provision may be.
 2. SUB-POINT PRECISION. Where a specific paragraph or point governs (Article 99(4) \
    rather than Article 99; Annex IV point 1(e) rather than Annex IV.2.a; Annex III \
    point 1(c) rather than Annex III.5), citing only the parent, or citing the wrong \
    sibling, is an error.
 3. OPERATOR ROLE. Article 50 splits duties between providers (50(1), 50(2)) and \
    deployers (50(3), 50(4)). Attributing one to the wrong role is a legal error.
 4. COMPLETENESS OF CLOSED SETS. Where the law enumerates a closed set — the eight \
    Article 5(1) prohibitions, the four Article 6(3) carve-outs, the four risk tiers, \
    the Article 5(1)(g) list of sensitive attributes — a partial list is an error even \
    when everything listed is correct.

Reply with ONE JSON object and nothing else. Do not wrap it in a code fence."""


def _judge_prompt(gen: dict[str, Any], gt: dict[str, Any], subpoint: list[str],
                  remarks: dict[str, str]) -> str:
    mistakes = gt.get("mistakes", []) or []
    mlines = "\n".join(
        f'  - id "{m["id"]}" ({m.get("type", "?")}): {m["desc"]}' for m in mistakes
    ) or "  (the expert found no defect in the earlier answer for this question)"

    refs = gen.get("references") or []
    reflist = "\n".join(f"  {i + 1}. {r}" for i, r in enumerate(refs)) or "  (none)"

    return f"""QUESTION
{gt["question"]}

=== CONTEXT: WHAT A HUMAN EU AI ACT EXPERT SAID ABOUT AN EARLIER ANSWER ===

The earlier answer that was graded:
{remarks.get("lexy_answer", "(not recorded)")}

Its citations: {remarks.get("lexy_citations", "(not recorded)")}

The expert's remarks, verbatim:
{remarks.get("review", "(not recorded)")}

Machine-readable list of the defects the expert flagged in that earlier answer:
{mlines}

=== CORRECTED REFERENCE MATERIAL ===

Reference answer (a corrected, deliberately concise statement of the law):
{gt.get("gold_answer", "")}

Correct citations at article/annex level: {", ".join(gt.get("gold_refs", [])) or "(none)"}
Correct citations at exact sub-point grain: {", ".join(subpoint) or "(none)"}

=== THE NEW ANSWER UNDER REVIEW ===

Answer:
{gen.get("answer") or "(EMPTY — the system returned no answer)"}

Its citations, in the order emitted:
{reflist}

=== WHAT TO RETURN ===

{{
  "answer_correctness": {{
    "verdict": "correct" | "partially_correct" | "incorrect",
    "reasoning": "<what the answer gets right and wrong, as law>"
  }},
  "legal_errors": [
    {{"statement": "<the incorrect proposition, quoted from the answer>",
      "why_wrong": "<the correct position, with the governing provision>",
      "severity": "critical" | "moderate" | "minor"}}
  ],
  "citation_assessment": [
    {{"ref": "<exactly as emitted>",
      "discussed_in_body": true | false,
      "legally_apt": true | false,
      "verdict": "correct" | "wrong_provision" | "imprecise_subpoint" | "unaddressed",
      "reasoning": "<one sentence>"}}
  ],
  "missing_citations": [
    {{"ref": "<a provision the answer should have cited>", "why": "<one sentence>"}}
  ],
  "role_attribution": {{
    "correct": true | false,
    "reasoning": "<provider/deployer duties correctly assigned? n/a if the question raises no role question>"
  }},
  "completeness": {{
    "closed_set_expected": "<the closed set this question requires, or 'none'>",
    "complete": true | false,
    "missing_items": ["<item>"],
    "reasoning": "<one sentence>"
  }},
  "scenario_application": {{
    "applicable": true | false,
    "applied": true | false,
    "reasoning": "<for a fact-pattern question, is the rule applied to THESE facts, or merely stated?>"
  }},
  "expert_defects": [
    {{"id": "<one of the ids listed above>",
      "resolved": true | false,
      "evidence": "<quote from the new answer, or what is still missing>"}}
  ],
  "overall_verdict": "correct" | "correct_with_minor_issues" | "partially_correct" | "incorrect",
  "critique": "<a short paragraph in the voice of the expert above: what still needs fixing>"
}}

Include one "citation_assessment" entry for EVERY citation listed above, in order.
Include one "expert_defects" entry for EVERY defect id listed above."""


def _extract_json(text: str) -> tuple[dict[str, Any] | None, str]:
    """Parse the judge's reply, tolerating a code fence or a prose preamble.

    Bedrock honours the system prompt (the Claude Max wrapper drops it), so the
    judge tends to comply with 'JSON only' — but a preamble still happens, and
    losing a whole graded row to it would be a measurement bug rather than a
    model failure. Returns ``(obj, reason)``; ``obj`` is None on failure and
    ``reason`` says why, so the caller can record an ERROR instead of a zero.
    """
    if not text or not text.strip():
        return None, "empty_reply"
    s = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", s, re.DOTALL)
    if fence:
        s = fence.group(1).strip()
    start = s.find("{")
    if start == -1:
        return None, "no_json_object"
    depth, in_str, esc = 0, False, False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(s[start:i + 1]), "ok"
                except ValueError as exc:
                    return None, f"json_decode: {exc}"[:120]
    return None, "unbalanced_json"


def run_judge(*, label: str, out_dir: Path, resume: bool, gen_rows: dict[str, dict[str, Any]],
              model: str, max_tokens: int, timeout: float, throttle: float,
              verbose: bool) -> dict[str, dict[str, Any]]:
    from app.llm.bedrock_client import BedrockRequest, complete_with_fallback

    from evals.regenold.antifragile_groundtruth import ANTIFRAGILE_GT
    from evals.regenold.antifragile_reviewer_remarks import ANTIFRAGILE_REVIEWER_REMARKS
    from evals.regenold.antifragile_subpoint_gold import ANTIFRAGILE_SUBPOINT_GOLD

    path = _ckpt_path(out_dir, "judge", label)
    done = _load_ckpt(path) if resume else {}
    if not resume and path.exists():
        path.unlink()
        done = {}

    todo = [q for q in gen_rows if q not in done]
    print(f"[judge] {len(todo)} to grade, {len(done)} already checkpointed -> {path}")
    print(f"[judge] model={model} max_tokens={max_tokens}")

    for qid in todo:
        gen = gen_rows[qid]
        gt = ANTIFRAGILE_GT[qid]
        sub = ANTIFRAGILE_SUBPOINT_GOLD.get(qid, {}).get("refs", gt.get("gold_refs", []))
        remarks = ANTIFRAGILE_REVIEWER_REMARKS.get(qid, {})
        prompt = _judge_prompt(gen, gt, sub, remarks)

        t0 = time.perf_counter()
        resp = complete_with_fallback(BedrockRequest(
            user=prompt,
            system=_JUDGE_SYSTEM,
            model=model,
            max_tokens=max_tokens,
            temperature=0.0,
            timeout_seconds=timeout,
        ))
        elapsed = (time.perf_counter() - t0) * 1000.0

        parsed, parse_reason = (None, "provider_error") if resp.error else _extract_json(resp.text)
        # A reply stopped by the token ceiling is NOT a bad answer, it is an
        # unusable measurement. Record it as an error so it can be re-run;
        # never let it collapse into a scored zero.
        truncated = (resp.finish_reason or "").lower() in {"max_tokens", "length"}

        rec = {
            "id": qid,
            "judge_model_requested": model,
            "judge_model_served": resp.model or model,
            "judge_model_comparable": (resp.model or model) == model,
            "finish_reason": resp.finish_reason,
            "judge_truncated": truncated,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "max_tokens": max_tokens,
            "headroom_tokens": max_tokens - (resp.output_tokens or 0),
            "elapsed_ms": round(elapsed, 1),
            "provider_error": resp.error,
            "parse_reason": parse_reason,
            "raw_reply": resp.text,          # FULL, always kept
            "verdict": parsed,
            "scorable": bool(parsed) and not truncated and not resp.error,
            "prompt_chars": len(prompt),
            "judged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _append_ckpt(path, rec)
        done[qid] = rec
        if verbose:
            if rec["scorable"]:
                v = parsed.get("overall_verdict", "?")
                nc = len(parsed.get("citation_assessment") or [])
                bad = sum(1 for c in (parsed.get("citation_assessment") or [])
                          if c.get("verdict") != "correct")
                res = sum(1 for d in (parsed.get("expert_defects") or []) if d.get("resolved"))
                tot = len(parsed.get("expert_defects") or [])
                print(f"  [{qid}] {v:<26} refs={nc} bad={bad} defects_fixed={res}/{tot} "
                      f"out={resp.output_tokens}/{max_tokens} {rec['elapsed_ms']:.0f}ms")
            else:
                print(f"  [{qid}] UNSCORABLE err={resp.error} parse={parse_reason} "
                      f"trunc={truncated} finish={resp.finish_reason}")
        time.sleep(throttle)
    return done


# ── Aggregation ──────────────────────────────────────────────────────────────


def _aggregate(gen_rows: dict[str, dict], judge_rows: dict[str, dict]) -> dict[str, Any]:
    from evals.regenold.antifragile_groundtruth import ANTIFRAGILE_GT

    ids = sorted(gen_rows)
    scorable = [q for q in ids if judge_rows.get(q, {}).get("scorable")]
    unscorable = [q for q in ids if q in judge_rows and not judge_rows[q].get("scorable")]
    ungraded = [q for q in ids if q not in judge_rows]

    verdict_counts: dict[str, int] = {}
    cite_total = cite_correct = cite_undiscussed = cite_wrong = cite_imprecise = 0
    missing_total = 0
    role_ok = role_n = 0
    complete_ok = complete_n = 0
    applied_ok = applied_n = 0
    defects_resolved = defects_total = 0
    legal_errors: list[dict[str, Any]] = []

    for q in scorable:
        v = judge_rows[q]["verdict"]
        verdict_counts[v.get("overall_verdict", "?")] = verdict_counts.get(v.get("overall_verdict", "?"), 0) + 1
        for c in v.get("citation_assessment") or []:
            cite_total += 1
            ver = (c.get("verdict") or "").strip()
            if ver == "correct":
                cite_correct += 1
            elif ver == "wrong_provision":
                cite_wrong += 1
            elif ver == "imprecise_subpoint":
                cite_imprecise += 1
            elif ver == "unaddressed":
                cite_undiscussed += 1
            if c.get("discussed_in_body") is False:
                # counted separately from the verdict bucket: a ref can be apt
                # AND undiscussed, which is precisely the expert's complaint
                pass
        missing_total += len(v.get("missing_citations") or [])
        ra = v.get("role_attribution") or {}
        if isinstance(ra.get("correct"), bool):
            role_n += 1
            role_ok += 1 if ra["correct"] else 0
        cp = v.get("completeness") or {}
        if (cp.get("closed_set_expected") or "none").lower() not in ("none", "", "n/a"):
            complete_n += 1
            complete_ok += 1 if cp.get("complete") else 0
        sa = v.get("scenario_application") or {}
        if sa.get("applicable"):
            applied_n += 1
            applied_ok += 1 if sa.get("applied") else 0
        for d in v.get("expert_defects") or []:
            defects_total += 1
            defects_resolved += 1 if d.get("resolved") else 0
        for e in v.get("legal_errors") or []:
            legal_errors.append({"id": q, **e})

    undiscussed = sum(
        1 for q in scorable
        for c in (judge_rows[q]["verdict"].get("citation_assessment") or [])
        if c.get("discussed_in_body") is False
    )

    lat = sorted(gen_rows[q]["latency_ms"] for q in ids if not gen_rows[q].get("error"))
    n_expert_defects = sum(len(ANTIFRAGILE_GT[q].get("mistakes", []) or []) for q in ids)

    def _rate(a: int, b: int) -> float | None:
        return round(a / b, 4) if b else None

    return {
        "n_rows": len(ids),
        "n_scorable": len(scorable),
        "n_unscorable": len(unscorable),
        "unscorable_ids": unscorable,
        "n_ungraded": len(ungraded),
        "ungraded_ids": ungraded,
        "gen_errors": [q for q in ids if gen_rows[q].get("error")],
        "overall_verdicts": verdict_counts,
        "citations": {
            "total": cite_total,
            "correct": cite_correct,
            "wrong_provision": cite_wrong,
            "imprecise_subpoint": cite_imprecise,
            "unaddressed": cite_undiscussed,
            "not_discussed_in_body": undiscussed,
            "precision": _rate(cite_correct, cite_total),
            "undiscussed_rate": _rate(undiscussed, cite_total),
            "missing_gold_citations": missing_total,
            "refs_per_row": round(cite_total / len(scorable), 2) if scorable else None,
        },
        "role_attribution_rate": _rate(role_ok, role_n),
        "closed_set_completeness_rate": _rate(complete_ok, complete_n),
        "scenario_application_rate": _rate(applied_ok, applied_n),
        "expert_defects": {
            "encoded_total": n_expert_defects,
            "graded_total": defects_total,
            "resolved": defects_resolved,
            "resolved_rate": _rate(defects_resolved, defects_total),
        },
        "legal_errors": legal_errors,
        "truncation": {
            "stage2_truncated_rows": [q for q in ids if gen_rows[q]["truncation"]["stage2_truncated_note"]],
            "no_terminal_punctuation_rows": [
                q for q in ids
                if gen_rows[q].get("answer") and not gen_rows[q]["truncation"]["ends_on_terminal_punctuation"]
            ],
            "ref_clamped_rows": [q for q in ids if gen_rows[q]["truncation"]["ref_clamp_note"]],
            "judge_truncated_rows": [q for q in ids if judge_rows.get(q, {}).get("judge_truncated")],
            "min_judge_headroom_tokens": min(
                (judge_rows[q]["headroom_tokens"] for q in judge_rows
                 if judge_rows[q].get("headroom_tokens") is not None), default=None),
        },
        "stage2_models": sorted({
            gen_rows[q]["truncation"]["stage2_model"] for q in ids
            if gen_rows[q]["truncation"]["stage2_model"]
        }),
        "judge_models_served": sorted({
            judge_rows[q]["judge_model_served"] for q in judge_rows
            if judge_rows[q].get("judge_model_served")
        }),
        "judge_model_comparable": all(
            judge_rows[q].get("judge_model_comparable", True) for q in judge_rows
        ),
        "answer_chars_median": round(statistics.median(
            [gen_rows[q]["truncation"]["answer_chars"] for q in ids] or [0]), 1),
        "latency_p50_ms": lat[len(lat) // 2] if lat else None,
        "latency_p95_ms": lat[min(len(lat) - 1, int(len(lat) * 0.95))] if lat else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--label", required=True)
    ap.add_argument("--phase", choices=["generate", "judge", "both"], default="both")
    ap.add_argument("--resume", action="store_true",
                    help="skip ids already present in the checkpoint")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", type=Path, default=_OUT_ROOT)
    ap.add_argument("--rag-model", default=DEFAULT_RAG_MODEL)
    ap.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    ap.add_argument("--judge-max-tokens", type=int, default=DEFAULT_JUDGE_MAX_TOKENS)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--judge-timeout", type=float, default=240.0)
    ap.add_argument("--throttle", type=float, default=1.0)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Env MUST be set before app.main is imported: the provider is resolved at
    # dispatch and the model pins are read as module constants in the engine,
    # so importing first would bake in whatever .env happened to say.
    from dotenv import load_dotenv
    load_dotenv()
    os.environ["P2P_GRAPH_RAG_PROVIDER"] = "bedrock"
    os.environ["REGENOLD_BEDROCK_MODEL"] = args.rag_model
    os.environ["REGENOLD_BEDROCK_COMPLEX_MODEL"] = args.rag_model
    os.environ["REGENOLD_BEDROCK_JUDGE_MODEL"] = args.judge_model
    os.environ.setdefault("BEDROCK_REGION", "eu-central-1")
    os.environ["NEO4J_AUTO_SEED"] = "0"      # hard rule: never re-seed the shared graph from here

    verbose = not args.quiet
    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print(f"ANTIFRAGILE 20 — live on Bedrock   label={args.label}")
    print(f"  RAG    {args.rag_model}")
    print(f"  judge  {args.judge_model}  max_tokens={args.judge_max_tokens}")
    print(f"  out    {out_dir}")
    print("=" * 78)

    gen_rows: dict[str, dict[str, Any]] = {}
    if args.phase in ("generate", "both"):
        gen_rows = run_generation(
            label=args.label, out_dir=out_dir, resume=args.resume, limit=args.limit,
            timeout=args.timeout, throttle=args.throttle, verbose=verbose)
    else:
        gen_rows = _load_ckpt(_ckpt_path(out_dir, "gen", args.label))
        if args.limit:
            gen_rows = {k: v for k, v in list(gen_rows.items())[:args.limit]}
        print(f"[gen] loaded {len(gen_rows)} rows from checkpoint")

    judge_rows: dict[str, dict[str, Any]] = {}
    if args.phase in ("judge", "both"):
        if not gen_rows:
            raise SystemExit("no generated rows to judge — run --phase generate first")
        judge_rows = run_judge(
            label=args.label, out_dir=out_dir, resume=args.resume, gen_rows=gen_rows,
            model=args.judge_model, max_tokens=args.judge_max_tokens,
            timeout=args.judge_timeout, throttle=args.throttle, verbose=verbose)
    else:
        judge_rows = _load_ckpt(_ckpt_path(out_dir, "judge", args.label))

    summary = _aggregate(gen_rows, judge_rows)
    report = {
        "label": args.label,
        "rag_model": args.rag_model,
        "judge_model": args.judge_model,
        "judge_max_tokens": args.judge_max_tokens,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "aggregate": summary,
        "rows": [
            {**gen_rows[q], "judge": judge_rows.get(q)}
            for q in sorted(gen_rows)
        ],
    }
    dest = out_dir / f"report-{args.label}.json"
    dest.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print("\n" + "=" * 78)
    print(json.dumps(summary, indent=2, default=str))
    print("=" * 78)
    print(f"wrote {dest}")
    if summary["n_unscorable"] or summary["truncation"]["judge_truncated_rows"]:
        print("\n! some rows are UNSCORABLE — they are excluded from rates, not scored zero.")
        print("  re-run with --phase judge --resume to retry only those rows.")


if __name__ == "__main__":
    main()
