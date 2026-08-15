"""Cappelli et al. (Discover AI 2026) 5-Dimension Compliance Benchmark Runner.

Executes the 20-scenario dataset across the 4 Annex III domains (Recruitment, Medical
Diagnostics, Smart City Traffic, Retail Biometrics) and 5 regulatory dimensions (Risk Level,
Regulatory Obligations, Legal Risks, Compliance Gaps, Technical Documentation).

Evaluates:
- Lexical Overlap: Token Jaccard (Loose), Keyword Recall (Strict), ROUGE-L (LCS F1)
- Semantic Similarity: Sub-token n-gram + word-stem cosine proxy
- Statutory References: Ref Loose (Head Recall), Ref Strict (Head F1), Ref Conciseness
- Score Retention: how many rows survive each similarity cutoff [0.10 - 0.80]. R338/[I6] —
  this used to be a "Precision / Recall / F1 curve"; it was not one. The label vector was
  derived from the same score being thresholded, so precision was 1.0 by construction.
- Direct comparative analysis against Cappelli et al. (2026) Table 8 baseline

CLI:
    py -3.12 -m evals.bench.run_cappelli_bench                    # openai_wrapper (live Stage-2)
    py -3.12 -m evals.bench.run_cappelli_bench --provider cli     # DETERMINISTIC — see warning below

⚠ R338/[I7] — THE PROVIDER IS THE INSTRUMENT. This runner used to default to
``--provider cli``, which is exactly the ground on which CLAUDE.md retired the
davidath 476 harness: ``cli`` short-circuits Stage-2 (``_graph_rag_impl`` returns
before ``_two_stage_generate``), so a Stage-2 prompt change, a judge change, the
reranker and the whole KG-context block are invisible to it *by construction* —
and a green run on such a change is the instrument trap, not a pass. The first
archived run of this benchmark (``cappelli_bench_results.json``,
2026-08-14T20:14:34Z) carries per-row ``latency_ms`` of 14.5-440 ms against a
~16 s live baseline, i.e. it was shipped in the same commit as a live Stage-2
prompt edit that it could not see. The default is now ``openai_wrapper``, an
explicitly-requested ``cli`` prints a loud banner naming what it is blind to, and
the resolved provider / Stage-2 model / per-row ``stage2_landed`` are written into
the DURABLE artifact — nothing in the eval pipeline reads logs.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from app.llm import resolve_provider

# ONE CONCEPT, ONE DEFINITION — the canonical Stage-2 provenance scraper is
# ``run_official_batch._provenance`` (R292). It already knows the trace shape
# (``stage2_polish`` / ``retrieval_path`` / the ``stage2_model=`` note) that
# ``_bedrock_complete_for_graph_rag`` and the wrapper path both emit. Do not
# write a second copy here; a duplicated scraper that drifts is this repo's
# most expensive recurring bug.
from evals.regenold.run_official_batch import _provenance

from evals.bench.metrics import (
    answer_correctness_loose,
    answer_correctness_strict,
    answer_keyword_recall,
    answer_rouge_l,
    answer_semantic_similarity_proxy,
    reference_correctness_loose,
    reference_correctness_strict,
    reference_conciseness,
    regulatory_tone,
    score_threshold_retention_curve,
)


def load_dataset() -> list[dict[str, Any]]:
    dataset_path = Path(__file__).parent / "data" / "cappelli_compliance_2026.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


# The live path is where the product is. ``cli`` is a deterministic probe, not a
# grading instrument — see the module docstring.
_DEFAULT_PROVIDER = "openai_wrapper"

# R338/[I7] — the route only serialises the reasoning trace when asked, and the
# trace is the ONLY place ``stage2_polish`` / ``stage2_model=`` live. Same query
# param ``run_official_batch`` appends for the same reason. The rubric ignores
# the ``reasoning`` field, so this cannot move a score; it only makes a silently
# degraded (or Stage-2-less) run detectable from the artifact alone.
_ASK_URL = "/api/v1/regenold/eu-ai-act/ask?include_reasoning=true"

_CLI_BLINDNESS_BANNER = """
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!  PROVIDER = cli  --  THIS RUN CANNOT OBSERVE STAGE-2. IT IS NOT A GATE.    !!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  The deterministic path returns before `_two_stage_generate`, so this
  configuration is STRUCTURALLY BLIND to:
    * every Stage-2 prompt / instruction change (system AND user channel)
    * the KG-context block, the grounding text and the semantic layers
    * the Cohere reranker and every Stage-2-gated post-process
    * `set_answer_no_cap`, which is gated on Stage-2 landing -- so
      MAX_ANSWER_SENTENCES=3 and the soft char cap stay ARMED and this run
      scores <=3-sentence answers against multi-sentence gold
  CLAUDE.md retired the davidath 476 harness on exactly this ground. A green
  scorecard here is the instrument trap, not a pass. Re-run without
  `--provider cli` before quoting any number from it.
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""


def resolve_run_provider(provider_arg: str | None) -> str:
    """Resolve the provider WITHOUT clobbering an operator's exported value.

    R338/[I7]. The old code did ``os.environ["P2P_GRAPH_RAG_PROVIDER"] = provider``
    unconditionally with ``provider`` defaulting to ``"cli"``, so an operator who
    had already exported ``openai_wrapper`` silently got the deterministic path.
    Read-with-default, not assign:

    * an explicit ``--provider`` always wins (that is the operator speaking now);
    * otherwise an already-exported value is left EXACTLY as it stands — including
      ``auto``/``""``, which the engine itself resolves via ``resolve_provider``;
    * only a genuinely unset/blank env is filled, with ``openai_wrapper``.

    Returns the provider the engine will actually use, resolved through the
    canonical ``app.llm.resolve_provider`` (one concept, one definition) so the
    string we record is the string the engine dispatches on, not the raw env.
    """
    if provider_arg:
        os.environ["P2P_GRAPH_RAG_PROVIDER"] = provider_arg
    elif not (os.environ.get("P2P_GRAPH_RAG_PROVIDER") or "").strip():
        os.environ["P2P_GRAPH_RAG_PROVIDER"] = _DEFAULT_PROVIDER
    return resolve_provider(
        os.environ.get("P2P_GRAPH_RAG_PROVIDER"),
        default_when_auto=_DEFAULT_PROVIDER,
    )


def run_benchmark(provider: str | None = None, output_path: str | None = None) -> dict[str, Any]:
    dataset = load_dataset()
    print(f"[Cappelli Benchmark] Loaded {len(dataset)} scenarios across 5 dimensions.")

    env_before = os.environ.get("P2P_GRAPH_RAG_PROVIDER")
    resolved_provider = resolve_run_provider(provider)
    print(
        f"[Cappelli Benchmark] resolved provider = {resolved_provider} "
        f"(--provider={provider or 'unset'}, "
        f"P2P_GRAPH_RAG_PROVIDER={env_before if env_before is not None else 'unset'} "
        f"-> {os.environ.get('P2P_GRAPH_RAG_PROVIDER')})"
    )
    if resolved_provider == "cli":
        print(_CLI_BLINDNESS_BANNER, file=sys.stderr)
        print(_CLI_BLINDNESS_BANNER)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.rate_limit import limiter

    client = TestClient(app)
    results: list[dict[str, Any]] = []
    http_errors: list[dict[str, Any]] = []

    # Aggregation buckets
    dim_scores: dict[str, dict[str, list[float]]] = {
        "risk_level": {"jaccard": [], "rouge_l": [], "semantic": [], "kw_recall": [], "ref_loose": [], "ref_strict": []},
        "regulatory_obligations": {"jaccard": [], "rouge_l": [], "semantic": [], "kw_recall": [], "ref_loose": [], "ref_strict": []},
        "legal_risks": {"jaccard": [], "rouge_l": [], "semantic": [], "kw_recall": [], "ref_loose": [], "ref_strict": []},
        "compliance_gaps": {"jaccard": [], "rouge_l": [], "semantic": [], "kw_recall": [], "ref_loose": [], "ref_strict": []},
        "technical_documentation": {"jaccard": [], "rouge_l": [], "semantic": [], "kw_recall": [], "ref_loose": [], "ref_strict": []},
    }

    all_sim_scores: list[float] = []

    for i, row in enumerate(dataset, 1):
        q_id = row["id"]
        dim = row["dimension"]
        q_text = row["question"]
        gold_ans = row["gold_answer"]
        expected_refs = row.get("expected_refs", [])
        expected_kws = row.get("expected_keywords", [])

        # Call engine via wire.
        # R338/[I7] — `limiter.reset()` belongs INSIDE the loop, per request, the
        # way `evals/bench/runner.py:47-49` has always done it. Resetting once
        # before the loop leaves the window to fill up mid-run, at which point
        # every remaining row 429s and (below) scored 0.0 as if the model had
        # answered badly.
        try:
            limiter.reset()
        except Exception:  # noqa: BLE001
            pass
        payload = [{"role": "user", "content": q_text}]
        t0 = time.perf_counter()
        resp = client.post(_ASK_URL, json=payload)
        latency_ms = (time.perf_counter() - t0) * 1000

        try:
            body = resp.json()
        except Exception:
            body = {"answer": "", "references": [], "reasoning": None}
        if not isinstance(body, dict):
            body = {"answer": "", "references": [], "reasoning": None}

        # R338/[I7] — a non-200 used to fall through as answer=""/references=[]
        # and be SCORED 0.0, i.e. a 429 or a 500 was indistinguishable from a
        # model that answered wrongly. Record it as an error instead; the row is
        # still scored (dropping it would silently change n) but the artifact now
        # says why the zero happened.
        http_status = resp.status_code
        if http_status != 200:
            # The app's own error shape is ``{"code": ..., "message": ...}``
            # (``app/rate_limit.py:24-32`` — measured, a real 429 carries NO
            # ``detail`` key), while FastAPI's default validation/HTTPException
            # shape uses ``detail``. Record whichever is present rather than
            # guessing, so the artifact never says "429, detail: null".
            http_errors.append({
                "id": q_id,
                "http_status": http_status,
                "code": body.get("code"),
                "message": (str(body.get("message") or body.get("detail") or ""))[:300] or None,
            })
            print(
                f"  [{i}/{len(dataset)}] {q_id}: HTTP {http_status} - scored as an "
                f"empty answer; see `http_errors` in the artifact.",
                file=sys.stderr,
            )

        pred_ans = body.get("answer", "") or ""
        pred_refs = body.get("references", []) or []

        # Canonical Stage-2 provenance (see the import note).
        prov = _provenance(body)
        stage2_landed = bool(prov.get("stage2_polish"))

        # Calculate metrics
        jaccard = answer_correctness_loose(pred_ans, gold_ans)
        rouge_l = answer_rouge_l(pred_ans, gold_ans)
        sem_sim = answer_semantic_similarity_proxy(pred_ans, gold_ans)
        kw_rec = answer_keyword_recall(pred_ans, expected_kws) if expected_kws else answer_correctness_strict(pred_ans, gold_ans)
        ref_l = reference_correctness_loose(pred_refs, expected_refs)
        ref_s = reference_correctness_strict(pred_refs, expected_refs)
        ref_c = reference_conciseness(pred_refs, expected_refs)
        tone = regulatory_tone(pred_ans)

        dim_scores[dim]["jaccard"].append(jaccard)
        dim_scores[dim]["rouge_l"].append(rouge_l)
        dim_scores[dim]["semantic"].append(sem_sim)
        if kw_rec is not None:
            dim_scores[dim]["kw_recall"].append(kw_rec)
        dim_scores[dim]["ref_loose"].append(ref_l)
        dim_scores[dim]["ref_strict"].append(ref_s)

        all_sim_scores.append(sem_sim)

        results.append({
            "id": q_id,
            "dimension": dim,
            "domain": row["domain"],
            "question": q_text,
            "predicted_answer": pred_ans,
            "predicted_refs": pred_refs,
            "gold_answer": gold_ans,
            "expected_refs": expected_refs,
            "jaccard": round(jaccard, 4),
            "rouge_l": round(rouge_l, 4),
            "semantic_similarity": round(sem_sim, 4),
            "keyword_recall": round(kw_rec, 4) if kw_rec is not None else None,
            "ref_loose": round(ref_l, 4),
            "ref_strict": round(ref_s, 4),
            "ref_conciseness": round(ref_c, 4),
            "regulatory_tone": round(tone, 4),
            "latency_ms": round(latency_ms, 2),
            # R338/[I7] — provenance in the DURABLE artifact. Nothing in the eval
            # pipeline reads logs, so an archived scorecard without these fields
            # cannot be re-attributed later: a Stage-2-less run and a live one
            # produce the same-shaped JSON.
            "http_status": http_status,
            "stage2_landed": stage2_landed,
            "stage2_model": prov.get("stage2_model") or "",
            "retrieval_path": prov.get("retrieval_path"),
        })

    # Compute category averages
    summary_by_dim: dict[str, dict[str, float]] = {}
    for d_name, metrics in dim_scores.items():
        summary_by_dim[d_name] = {
            m_name: round(sum(vals) / len(vals), 4) if vals else 0.0
            for m_name, vals in metrics.items()
        }

    # R338/[I6] — `threshold_precision_recall_curve` was WITHDRAWN (it raises a
    # tombstone NotImplementedError now) because its only caller — this one —
    # derived the gold-relevance vector from the very score it thresholded
    # (`all_relevance = [sem_sim >= 0.25]`), pinning precision at exactly 1.0 for
    # every cut >= 0.25 by construction. The replacement takes NO label vector,
    # so it cannot manufacture a precision; it reports only where the score
    # distribution lives. IF YOU CHANGE A FORMULA, CHANGE ITS NAME — hence the
    # summary key below is renamed too, so no historical
    # `threshold_sensitivity_curve` number is silently compared against this.
    retention_curve = score_threshold_retention_curve(all_sim_scores)

    # R338/[I7] — run provenance. `stage2_landed_rate` well under 1.0 (or a mean
    # row latency in the tens of ms) means the arm never ran the live path, and
    # every number below grades the deterministic fallback. Same aggregate
    # `run_official_batch` computes, for the same reason.
    n = len(results) or 1
    mean_latency_ms = round(sum(r["latency_ms"] for r in results) / n, 2)
    stage2_landed_rate = round(sum(1 for r in results if r["stage2_landed"]) / n, 4)
    stage2_models = sorted({r["stage2_model"] for r in results if r["stage2_model"]})
    # CLAUDE.md's cheapest inert-arm detector: a live Stage-2 row costs seconds,
    # the deterministic path costs milliseconds. Report WHICH condition fired —
    # they mean different things and only one of them is "you asked for cli".
    # Measured with the wrapper port closed: mean_latency_ms 2975.68 (Stage-2 WAS
    # attempted, `stage2_models=['claude-opus-5']`) but `stage2_landed_rate=0.0`,
    # i.e. every row silently served the deterministic fallback. A latency-only
    # detector would have called that run healthy.
    deterministic_reasons: list[str] = []
    if stage2_landed_rate == 0.0:
        deterministic_reasons.append("no row recorded a Stage-2 polish")
    if mean_latency_ms < 2000.0:
        deterministic_reasons.append(f"mean row latency {mean_latency_ms} ms is under 2 s")
    looks_deterministic = bool(deterministic_reasons)

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_scenarios": len(results),
        "run_provenance": {
            "resolved_provider": resolved_provider,
            "provider_arg": provider,
            "env_provider_before": env_before,
            "env_provider_effective": os.environ.get("P2P_GRAPH_RAG_PROVIDER"),
            "stage2_landed_rate": stage2_landed_rate,
            "stage2_models": stage2_models,
            "mean_latency_ms": mean_latency_ms,
            "looks_deterministic": looks_deterministic,
            "deterministic_reasons": deterministic_reasons,
            "http_errors": http_errors,
            "instrument_warning": (
                _CLI_BLINDNESS_BANNER.strip() if resolved_provider == "cli" else None
            ),
        },
        "summary_by_dimension": summary_by_dim,
        "overall_averages": {
            "jaccard_loose": round(sum(r["jaccard"] for r in results) / len(results), 4),
            "rouge_l": round(sum(r["rouge_l"] for r in results) / len(results), 4),
            "semantic_similarity": round(sum(r["semantic_similarity"] for r in results) / len(results), 4),
            "keyword_recall": round(sum(r["keyword_recall"] for r in results if r["keyword_recall"] is not None) / len(results), 4),
            "ref_loose": round(sum(r["ref_loose"] for r in results) / len(results), 4),
            "ref_strict": round(sum(r["ref_strict"] for r in results) / len(results), 4),
            "ref_conciseness": round(sum(r["ref_conciseness"] for r in results) / len(results), 4),
            "regulatory_tone": round(sum(r["regulatory_tone"] for r in results) / len(results), 4),
        },
        "score_threshold_retention_curve": retention_curve,
        "results": results,
    }

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"[Cappelli Benchmark] Saved results to {output_path}")

    return summary


def print_scorecard(summary: dict[str, Any]) -> None:
    print("\n" + "=" * 90)
    print("CAPPELLI ET AL. (2026) 5-DIMENSION COMPLIANCE BENCHMARK SCORECARD")
    print("=" * 90)
    # R338/[I7] — the provider line sits ABOVE the numbers on purpose: a reader
    # must know which instrument produced them before reading them.
    rp = summary.get("run_provenance") or {}
    print(
        f"provider={rp.get('resolved_provider')} | "
        f"stage2_landed_rate={rp.get('stage2_landed_rate')} | "
        f"stage2_models={rp.get('stage2_models') or '-'} | "
        f"mean_latency={rp.get('mean_latency_ms')} ms"
    )
    if rp.get("http_errors"):
        print(f"!! {len(rp['http_errors'])} row(s) returned a non-200 - see `http_errors`.")
    if rp.get("looks_deterministic"):
        print(
            "!! INSTRUMENT WARNING (" + "; ".join(rp.get("deterministic_reasons") or []) + ")"
            " - this scorecard grades the DETERMINISTIC path and cannot observe a"
            " Stage-2, prompt, KG-context or reranker change."
        )
    print("=" * 90)
    print(f"{'Dimension':<26} | {'Jaccard':<8} | {'ROUGE-L':<8} | {'Semantic':<8} | {'KW Recall':<10} | {'Ref Loose':<10} | {'Ref Strict':<10}")
    print("-" * 90)
    for dim, s in summary["summary_by_dimension"].items():
        print(f"{dim:<26} | {s['jaccard']:<8.4f} | {s['rouge_l']:<8.4f} | {s['semantic']:<8.4f} | {s['kw_recall']:<10.4f} | {s['ref_loose']:<10.4f} | {s['ref_strict']:<10.4f}")
    print("-" * 90)
    oa = summary["overall_averages"]
    print(f"{'OVERALL AVERAGE':<26} | {oa['jaccard_loose']:<8.4f} | {oa['rouge_l']:<8.4f} | {oa['semantic_similarity']:<8.4f} | {oa['keyword_recall']:<10.4f} | {oa['ref_loose']:<10.4f} | {oa['ref_strict']:<10.4f}")
    print("=" * 90)

    # R338/[I6] — a DISTRIBUTION shape of the similarity ruler, NOT a score. The
    # old header said "Decoupling Precision & Recall" over a precision column that
    # was 1.0 by construction; both the maths and its NAME are gone.
    print("\n" + "-" * 62)
    print("SIMILARITY SCORE RETENTION (ruler shape - NOT a correctness score)")
    print("-" * 62)
    print(f"{'Threshold':<12} | {'Rows >= t':<12} | {'Of total':<12} | {'Retention':<12}")
    print("-" * 62)
    for pt in summary["score_threshold_retention_curve"]:
        print(f"{pt['threshold']:<12.2f} | {pt['n_at_or_above']:<12d} | {pt['n_total']:<12d} | {pt['retention']:<12.4f}")
    print("-" * 62 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Cappelli 5-Dimension Compliance Benchmark")
    # R338/[I7] — default None, NOT "cli". None means "whatever the operator
    # exported, else openai_wrapper"; a string here is an explicit override.
    parser.add_argument(
        "--provider",
        default=None,
        help=(
            "Provider override (cli, openai_wrapper, anthropic, bedrock). "
            "Unset = honour an exported P2P_GRAPH_RAG_PROVIDER, else "
            f"'{_DEFAULT_PROVIDER}'. '--provider cli' disables Stage-2 and is "
            "NOT a gate - it prints a blindness banner."
        ),
    )
    parser.add_argument("--out", default="evals/bench/results/cappelli_bench_results.json", help="Output JSON path")
    args = parser.parse_args()

    summary = run_benchmark(provider=args.provider, output_path=args.out)
    print_scorecard(summary)
