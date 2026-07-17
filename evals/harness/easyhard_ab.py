"""R281 — gold-scored easy/hard A/B runner (the ref-precision merge gate).

WHY THIS EXISTS
---------------
CLAUDE.md hard rule #6 makes the live pairwise ``evals.harness.ab_judge`` the
merge gate. That is right for answer-QUALITY changes and WRONG for a
reference-COUNT change, because ab_judge's refs axis cannot see precision:

    evals/harness/pairwise_prompts.py::render_refs asks which answer's prose
    "more faithfully describes the articles it cites ... and cites the
     load-bearing gold articles"

— faithfulness + RECALL, with no minimality term. Dropping a non-gold ref earns
nothing there; dropping a gold ref is punished. So that instrument rejects
every precision fix regardless of merit (this is exactly how R142.1's clamp
lost 11-0), and it CANNOT be the gate for this round.

The competition scores references against gold on two axes that DO reward
precision. Verbatim from ``docs/2026-eu-ai-act-competition-rules_official.pdf``:

    "references (list[str]): Should contain the minimal set of relevant
     references."
    "Is the answer sufficiently concise? ... Similarly, the amount of proposed
     references is checked against ground-truth ones."

This runner scores the gold-bearing probe set on exactly those axes
(``evals.bench.metrics``: reference_correctness_loose = recall,
_strict = F1, reference_conciseness = count-ratio) plus keyword recall + tone,
for two env arms, and reports the paired delta.

The R280 checkpoint's own hard-won lessons are built in:
  * PER-ROW CHECKPOINTING — R280's frontier runner was killed at 65/95 and
    wrote its sidecar only at the end, losing every row (recovered only by
    scraping stdout). Every row is appended to a .ckpt.jsonl as it lands.
  * NEVER run two wrapper-bound jobs concurrently — everything funnels to ONE
    local Claude Max; arms run SEQUENTIALLY, never in parallel.
  * NO ``?include_reasoning=true`` — it forces Stage-2 and distorts an eval
    comparison (R112).

HONESTY / SCOPE
---------------
* Ref Correctness LOOSE (recall) is the GUARD. The R142.1 failure mode is
  dropping gold. Any arm that reduces recall materially is rejected regardless
  of its F1 / conciseness gain.
* Two live LLM arms are NOT deterministic. This is a paired, gold-scored diff
  over n=132, not a pairwise judge — legitimate for a large ref-count effect,
  weak for a small prose effect. Report n and per-row deltas, never just means.
* Our probe gold is head-form; regenold's example gold is sub-point form
  (``["Annex IV.2","Article 3.1"]``). Head-level scoring is therefore the
  honest granularity here, and it is sound for this defect: the measured excess
  is 97% entirely NON-GOLD ARTICLES, which is a granularity-independent error.

USAGE
-----
    # baseline arm vs branch arm, live prod, sequential
    .venv/Scripts/python.exe -m evals.harness.easyhard_ab \\
        --endpoint https://<prod>/api/v1/regenold/eu-ai-act/ask \\
        --api-key $REGENOLD_API_KEY --label r281 \\
        --baseline-env REGENOLD_REF_MINIMALITY=0 \\
        --branch-env  REGENOLD_REF_MINIMALITY=1

    # single arm (a plain scorecard, e.g. to reproduce easyhard-r279-live)
    .venv/Scripts/python.exe -m evals.harness.easyhard_ab --local --label x
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import time
from pathlib import Path
from typing import Any

from evals.bench import metrics as bench_metrics
from evals.harness.probe_set import ProbeRow, load_probe_set

_RESULTS = Path(__file__).resolve().parents[1] / "bench" / "results"

# Marginal leverage on the official Overall (a plain geometric mean of the 8
# axes) at our operating point — pp of Overall per +1pp of the axis.
# Source: .planning/R276-PLAN.md (reproduces every reported figure to <0.05pp).
_LEVERAGE = {"ref_strict": 0.163, "ref_conc": 0.121, "ref_loose": 0.113}


def _keyword_recall(answer: str, expected: list[str]) -> float:
    if not expected:
        return 1.0
    low = (answer or "").lower()
    return sum(1 for k in expected if k.lower() in low) / len(expected)


def _score_row(row: ProbeRow, answer: str, refs: list[str]) -> dict[str, float]:
    gold = list(row.expected_refs or [])
    return {
        "ref_loose": bench_metrics.reference_correctness_loose(refs, gold),
        "ref_strict": bench_metrics.reference_correctness_strict(refs, gold),
        "ref_conc": bench_metrics.reference_conciseness(refs, gold),
        "tone": bench_metrics.regulatory_tone(answer),
        "kw_recall": _keyword_recall(answer, list(row.expected_keywords or [])),
    }


_AXES = ("ref_loose", "ref_strict", "ref_conc", "tone", "kw_recall")


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in rows if not r.get("error")]
    if not ok:
        return {"n": 0, "errors": len(rows)}
    out: dict[str, Any] = {"n": len(ok), "errors": len(rows) - len(ok)}
    for a in _AXES:
        out[a] = st.mean(r["scores"][a] for r in ok)
    lat = sorted(r["latency_ms"] for r in ok)
    out["latency_p50_ms"] = lat[len(lat) // 2]
    out["latency_p90_ms"] = lat[int(len(lat) * 0.9)] if len(lat) > 1 else lat[0]
    n_pred = sum(len(bench_metrics.article_heads(r["pred_refs"])) for r in ok)
    n_gold = sum(len(bench_metrics.article_heads(r["gold_refs"])) for r in ok)
    out["pred_gold_ratio"] = (n_pred / n_gold) if n_gold else 0.0
    return out


def _run_arm(
    probe: list[ProbeRow],
    *,
    endpoint: str | None,
    api_key: str | None,
    local: bool,
    timeout: float,
    arm_env: dict[str, str],
    ckpt_path: Path,
) -> list[dict[str, Any]]:
    """Run every probe row under `arm_env`. Appends each row to `ckpt_path`."""
    # Apply the arm env BEFORE the first request. Route-level flags are read
    # fresh per call; engine/import-time settings are NOT A/B-able in-process
    # (the R271 gotcha) — the caller is responsible for choosing an in-proc-safe
    # flag or running two processes.
    saved: dict[str, str | None] = {}
    for k, v in arm_env.items():
        saved[k] = os.environ.get(k)
        os.environ[k] = v

    # Import transports lazily so --endpoint mode keeps a lean import surface.
    from evals.regenold.runner_v2 import _post, _post_local

    poster = _post_local if local else _post
    url = "local://app.main:app/api/v1/regenold/eu-ai-act/ask" if local else str(endpoint)

    rows: list[dict[str, Any]] = []
    ckpt = ckpt_path.open("a", encoding="utf-8")
    try:
        for i, pr in enumerate(probe, 1):
            history = [dict(m) for m in pr.messages]
            body, latency_ms, status, err, attempts, _retried = poster(
                url, api_key, history, timeout
            )
            answer = str((body or {}).get("answer") or "")
            refs = list((body or {}).get("references") or [])
            rec: dict[str, Any] = {
                "id": pr.id,
                "source": pr.source,
                "category": pr.category,
                "is_multiturn": pr.is_multiturn,
                "pred_answer": answer,
                "pred_refs": refs,
                "gold_refs": list(pr.expected_refs or []),
                "expected_keywords": list(pr.expected_keywords or []),
                "latency_ms": latency_ms,
                "http_status": status,
                "attempts": attempts,
                "answer_chars": len(answer),
            }
            if err or not answer:
                rec["error"] = err or "empty_answer"
            else:
                rec["scores"] = _score_row(pr, answer, refs)
            rows.append(rec)
            # R280 lesson: checkpoint EVERY row immediately — a killed run
            # must not lose its work.
            ckpt.write(json.dumps(rec, ensure_ascii=False) + "\n")
            ckpt.flush()
            tag = "ERR " if rec.get("error") else "ok  "
            print(
                f"  [{i:3d}/{len(probe)}] {tag}{pr.id:<34} "
                f"{latency_ms/1000:6.1f}s refs={len(refs):2d}",
                flush=True,
            )
    finally:
        ckpt.close()
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return rows


def _split(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "easy": [r for r in rows if not r["is_multiturn"]],
        "hard": [r for r in rows if r["is_multiturn"]],
    }


def _report(label: str, base: dict[str, Any], branch: dict[str, Any] | None) -> None:
    for split in ("easy", "hard"):
        b = base.get(split) or {}
        if not b.get("n"):
            continue
        print(f"\n=== {label} — {split} (n={b['n']}, errors={b['errors']}) ===")
        if branch is None:
            for a in _AXES:
                print(f"  {a:<12}{b[a]:>9.4f}")
            print(f"  {'pred:gold':<12}{b['pred_gold_ratio']:>9.2f}")
            print(f"  {'latency p50':<12}{b['latency_p50_ms']/1000:>9.1f}s")
            continue
        c = branch.get(split) or {}
        print(f"  {'axis':<12}{'baseline':>10}{'branch':>10}{'delta':>10}")
        for a in _AXES:
            d = c[a] - b[a]
            flag = ""
            if a == "ref_loose" and d < -0.005:
                flag = "  <-- GOLD LOSS (R142.1 failure mode)"
            print(f"  {a:<12}{b[a]:>10.4f}{c[a]:>10.4f}{d:>+10.4f}{flag}")
        print(
            f"  {'pred:gold':<12}{b['pred_gold_ratio']:>10.2f}"
            f"{c['pred_gold_ratio']:>10.2f}"
            f"{c['pred_gold_ratio']-b['pred_gold_ratio']:>+10.2f}"
        )
        print(
            f"  {'lat p50 s':<12}{b['latency_p50_ms']/1000:>10.1f}"
            f"{c['latency_p50_ms']/1000:>10.1f}"
            f"{(c['latency_p50_ms']-b['latency_p50_ms'])/1000:>+10.1f}"
        )
        uplift = sum(
            _LEVERAGE[a] * (c[a] - b[a]) * 100.0 for a in _LEVERAGE if a in c
        )
        print(f"  => est. Overall uplift from the 3 reference axes: {uplift:+.2f} pp")


def _parse_env(pairs: list[str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in pairs or []:
        if "=" not in p:
            raise SystemExit(f"--*-env expects KEY=VALUE, got {p!r}")
        k, v = p.split("=", 1)
        out[k.strip()] = v
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--endpoint", help="live ask URL")
    ap.add_argument("--local", action="store_true", help="in-process TestClient")
    ap.add_argument("--api-key")
    ap.add_argument("--label", required=True)
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--multiturn", choices=("only", "skip"))
    ap.add_argument("--baseline-env", action="append")
    ap.add_argument("--branch-env", action="append")
    args = ap.parse_args()

    if not args.local and not args.endpoint:
        raise SystemExit("need --endpoint or --local")

    mt = None
    if args.multiturn == "only":
        mt = True
    elif args.multiturn == "skip":
        mt = False
    probe = load_probe_set(multiturn=mt, limit=args.limit)
    print(f"probe rows: {len(probe)} (easy={sum(1 for p in probe if not p.is_multiturn)}, "
          f"hard={sum(1 for p in probe if p.is_multiturn)})")

    _RESULTS.mkdir(parents=True, exist_ok=True)
    base_env = _parse_env(args.baseline_env)
    branch_env = _parse_env(args.branch_env)

    print(f"\n### ARM A (baseline) env={base_env or '{}'}")
    a_rows = _run_arm(
        probe, endpoint=args.endpoint, api_key=args.api_key, local=args.local,
        timeout=args.timeout, arm_env=base_env,
        ckpt_path=_RESULTS / f"easyhard-{args.label}-A.ckpt.jsonl",
    )
    a_agg = {k: _aggregate(v) for k, v in _split(a_rows).items()}

    b_agg = None
    b_rows: list[dict[str, Any]] = []
    if branch_env:
        # SEQUENTIAL by construction — both arms hairpin to ONE local Claude
        # Max; concurrent wrapper jobs corrupt each other's latency.
        print(f"\n### ARM B (branch) env={branch_env}")
        b_rows = _run_arm(
            probe, endpoint=args.endpoint, api_key=args.api_key, local=args.local,
            timeout=args.timeout, arm_env=branch_env,
            ckpt_path=_RESULTS / f"easyhard-{args.label}-B.ckpt.jsonl",
        )
        b_agg = {k: _aggregate(v) for k, v in _split(b_rows).items()}

    _report(args.label, a_agg, b_agg)

    out = _RESULTS / f"easyhard-{args.label}.json"
    out.write_text(
        json.dumps(
            {
                "label": args.label,
                "endpoint": args.endpoint or "local",
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "baseline_env": base_env,
                "branch_env": branch_env,
                "baseline": a_agg,
                "branch": b_agg,
                "baseline_rows": a_rows,
                "branch_rows": b_rows,
            },
            indent=1,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
