"""Unbiased eval harness — wrapper runner for 3 cross-cutting probes.

Why this exists:
    The in-sample ``evals.bench.runner`` has been tuned against
    davidath/ai-act-evaluation-benchmark since Round 23. Each new
    optimisation feeds back into the bench, so the score over-states
    real-world generalisation. The unbiased harness runs THREE
    disjoint probes to expose that overfit:

        1. davidath HOLD-OUT (~20% slice the in-sample loop never sees)
        2. AIReg-Bench       (held-out cross-domain HRAIS scenarios)
        3. Regenold probe    (3 PDF examples + 20 paraphrases)

Each harness scores against the LIVE Regenold wire (POST
/api/v1/regenold/eu-ai-act/ask via FastAPI's TestClient). The runner
writes a single JSON sidecar at
``evals/bench/results/unbiased-<label>.json`` and prints a combined
scorecard to stdout.

CLI:
    py -3.12 -m evals.bench.unbiased_runner --label r37-baseline
    py -3.12 -m evals.bench.unbiased_runner --label smoke --qa-limit 5
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import settings
from app.main import app
from app.rate_limit import limiter

from evals.bench import aireg_bench, holdout, metrics, regenold_probe, airbench_2024
import os



_EVAL_KEY = "regenold-unbiased-eval-key"
_DEFAULT_OUTPUT_DIR = Path(__file__).parent / "results"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _reset_limiter() -> None:
    try:
        limiter.reset()
    except Exception:  # noqa: BLE001
        pass


def _ask(client: TestClient, question: str) -> tuple[dict, float]:
    """Single-turn wire call. Returns ``(body, latency_ms)``."""
    _reset_limiter()
    payload = [{"role": "user", "content": question}]
    start = time.perf_counter()
    resp = client.post("/api/v1/regenold/eu-ai-act/ask", json=payload)
    elapsed = (time.perf_counter() - start) * 1000.0
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        body = {"answer": "", "references": [], "reasoning": None}
    if not isinstance(body, dict):
        body = {"answer": "", "references": [], "reasoning": None}
    return body, elapsed


# ── davidath hold-out ────────────────────────────────────────────────────


def _scenario_to_question(s: dict[str, Any]) -> str:
    """Mirrors evals.bench.runner._scenario_to_question without importing it."""
    role = (s.get("role") or "Provider").strip()
    intended_use = (s.get("intended_use") or "").strip()
    system_type = (s.get("system_type") or "").strip()
    domain = (s.get("domain") or "").strip()
    parts = [f"We are a {role.lower()}"]
    if system_type:
        parts.append(f"offering a {system_type.lower()}")
    if intended_use:
        parts.append(f"intended to {intended_use.lower()}")
    if domain:
        parts.append(f"in the {domain.lower()} domain")
    prelude = ", ".join(parts) + "."
    return (
        f"{prelude} Under the EU AI Act, what is the risk classification of "
        f"this system and what are the key obligations on us as {role.lower()}?"
    )


def _run_holdout(
    client: TestClient,
    qa_limit: int | None,
    scenario_limit: int | None,
) -> dict[str, Any]:
    qa_items = holdout.load_holdout_qa()
    sc_items = holdout.load_holdout_scenarios()
    if qa_limit is not None:
        qa_items = qa_items[:qa_limit]
    if scenario_limit is not None:
        sc_items = sc_items[:scenario_limit]

    qa_scores: list[metrics.RowScore] = []
    sc_scores: list[metrics.RowScore] = []

    for item in qa_items:
        q = item.get("question") or ""
        gold_answer = item.get("answer") or ""
        gold_article = item.get("relevant_article")
        body, latency = _ask(client, q)
        score = metrics.score_row(
            pred_answer=body.get("answer") or "",
            pred_refs=body.get("references") or [],
            gold_answer=gold_answer,
            gold_articles=gold_article,
            latency_ms=latency,
            expected_keywords=item.get("expected_keywords"),
        )
        qa_scores.append(score)

    for item in sc_items:
        q = _scenario_to_question(item)
        obligations = item.get("obligations") or []
        gold_answer = (
            f"This system is classified as {item.get('risk_level','')}. "
            + " ".join(obligations[:3])
        )
        gold_articles = item.get("related_articles") or []
        body, latency = _ask(client, q)
        score = metrics.score_row(
            pred_answer=body.get("answer") or "",
            pred_refs=body.get("references") or [],
            gold_answer=gold_answer,
            gold_articles=gold_articles,
            latency_ms=latency,
            expected_keywords=item.get("expected_keywords"),
        )
        sc_scores.append(score)

    return {
        "qa": metrics.aggregate(qa_scores),
        "scenarios": metrics.aggregate(sc_scores),
        "overall": metrics.aggregate(qa_scores + sc_scores),
        "split_summary": holdout.summary(),
        "qa_n_run": len(qa_items),
        "scenarios_n_run": len(sc_items),
    }


# ── AIReg-Bench ──────────────────────────────────────────────────────────


def _build_aireg_agent(client: TestClient):
    """Wrap the wire as an ``agent_fn`` callable for AIReg-Bench."""

    def _agent(item: dict[str, Any]) -> dict[str, Any]:
        question = (
            "Consider the following AI system description and assess its "
            f"compliance with EU AI Act Article {item.get('article','').split('.')[-1].strip()}: "
            + item.get("scenario", "")
        )
        body, _ = _ask(client, question)
        return {
            "answer": body.get("answer") or "",
            "references": body.get("references") or [],
        }

    return _agent


def _run_aireg(
    client: TestClient, aireg_limit: int | None, *, source: str
) -> dict[str, Any]:
    items = aireg_bench.load_aireg_bench()
    fallback_used = items is aireg_bench.load_aireg_fixture()
    # ``is`` check above is fragile (returns new lists). Detect fallback
    # via the id prefix instead.
    fallback_used = bool(items and items[0].get("id", "").startswith("aireg-"))
    if aireg_limit is not None:
        items = items[:aireg_limit]
    agent = _build_aireg_agent(client)
    result = aireg_bench.score_aireg_bench(items, agent)
    result["fallback_used"] = fallback_used
    result["source"] = source
    return result


# ── Regenold probe ───────────────────────────────────────────────────────


def _build_probe_agent(client: TestClient):
    def _agent(item: dict[str, Any]) -> dict[str, Any]:
        body, _ = _ask(client, item.get("question", ""))
        return {
            "answer": body.get("answer") or "",
            "references": body.get("references") or [],
        }

    return _agent


def _run_probe(
    client: TestClient, probe_limit: int | None
) -> dict[str, Any]:
    items = regenold_probe.load_regenold_probe()
    if probe_limit is not None:
        items = items[:probe_limit]
    agent = _build_probe_agent(client)
    return regenold_probe.score_regenold_probe(items, agent)


# ── AIR-Bench 2024 ───────────────────────────────────────────────────────


def _run_airbench(
    client: TestClient,
    airbench_limit: int | None,
) -> dict[str, Any]:
    """Run the AIR-Bench 2024 ``eu_mandatory`` subset.

    Prompts are adversarial and verify the scope gate and Article 5
    prohibited practice refusal logic.
    """
    env_gate = os.environ.get("REGENOLD_AIRBENCH", "").strip().lower()
    if env_gate not in ("1", "true", "yes", "on"):
        return {
            "n": 0,
            "refusal_correctness": 0.0,
            "ref_correctness_loose": 0.0,
            "rows": [],
            "skipped": True,
        }

    rows_raw = airbench_2024.load_eu_mandatory()
    if not rows_raw:
        return {
            "n": 0,
            "refusal_correctness": 0.0,
            "ref_correctness_loose": 0.0,
            "rows": [],
        }
    if airbench_limit is not None:
        rows_raw = rows_raw[:airbench_limit]

    result_rows: list[dict[str, Any]] = []
    for idx, raw in enumerate(rows_raw):
        prompt = raw["prompt"]
        cate_idx = raw["cate_idx"]
        l3_name = raw["l3_name"]
        gold_refs = airbench_2024.derive_gold_refs(cate_idx)

        body, latency_ms = _ask(client, prompt)
        answer = body.get("answer") or ""
        pred_refs = body.get("references") or []

        score = airbench_2024.score_row(
            answer=answer,
            refs=pred_refs,
            gold_refs=gold_refs,
        )

        result_rows.append(
            {
                "item_id": f"air_{idx:05d}",
                "cate_idx": cate_idx,
                "l3_name": l3_name,
                "prompt_preview": prompt[:200],
                "gold_refs": gold_refs,
                "pred_answer_preview": answer[:300],
                "pred_refs": pred_refs,
                "latency_ms": round(latency_ms, 2),
                "refused": score["refused"],
                "ref_loose": score["ref_loose"],
            }
        )

    refused_flags = [r["refused"] for r in result_rows]
    ref_loose_scores = [r["ref_loose"] for r in result_rows]
    n = len(result_rows)

    refusal_rate = metrics.refusal_correctness(refused_flags)
    avg_ref_loose = sum(ref_loose_scores) / n if n else 0.0

    return {
        "n": n,
        "refusal_correctness": round(refusal_rate, 4),
        "ref_correctness_loose": round(avg_ref_loose, 4),
        "rows": result_rows,
    }


# ── Top-level run() ──────────────────────────────────────────────────────



def run(
    *,
    label: str = "adhoc",
    output_dir: Path | None = None,
    qa_limit: int | None = None,
    scenario_limit: int | None = None,
    aireg_limit: int | None = None,
    probe_limit: int | None = None,
    airbench_limit: int | None = None,
) -> dict[str, Any]:
    """Run all harnesses and persist a JSON sidecar.

    Returns the persisted payload. The sidecar path is included in the
    payload under ``sidecar_path``.
    """
    out_dir = Path(output_dir) if output_dir is not None else _DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    started_at = _now_iso()

    prev_key = settings.regenold.api_key
    settings.regenold.api_key = SecretStr(_EVAL_KEY)
    try:
        with TestClient(
            app, headers={"X-Regenold-Api-Key": _EVAL_KEY}
        ) as client:
            davidath_block = _run_holdout(client, qa_limit, scenario_limit)
            aireg_block = _run_aireg(client, aireg_limit, source="fixture")
            probe_block = _run_probe(client, probe_limit)
            airbench_block = _run_airbench(client, airbench_limit)
    finally:
        settings.regenold.api_key = prev_key

    finished_at = _now_iso()

    payload: dict[str, Any] = {
        "label": label,
        "started_at": started_at,
        "finished_at": finished_at,
        "davidath_holdout": davidath_block,
        "aireg_bench": aireg_block,
        "regenold_probe": probe_block,
        "air_bench": airbench_block,
    }

    sidecar_path = out_dir / f"unbiased-{label}.json"
    sidecar_path.write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )

    payload["sidecar_path"] = str(sidecar_path)
    return payload


# ── Human summary ────────────────────────────────────────────────────────


def _format_summary(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append(f"UNBIASED EVAL — label={payload.get('label')!r}")
    lines.append("=" * 78)

    # davidath hold-out
    hb = payload.get("davidath_holdout", {})
    split = hb.get("split_summary", {})
    lines.append("")
    lines.append(
        f"[DAVIDATH HOLD-OUT]  qa held-out={split.get('qa',{}).get('holdout','?')}/"
        f"{split.get('qa',{}).get('total','?')}  scenarios held-out="
        f"{split.get('scenarios',{}).get('holdout','?')}/"
        f"{split.get('scenarios',{}).get('total','?')}"
    )
    for source in ("qa", "scenarios", "overall"):
        block = hb.get(source) or {}
        if not block:
            continue
        n = block.get("n", 0)
        lines.append(
            f"  {source.upper():<10} n={n}  "
            f"AnsLoose={block.get('ans_correctness_loose','-')}  "
            f"AnsStrict={block.get('ans_correctness_strict','-')}  "
            f"RefLoose={block.get('ref_correctness_loose','-')}  "
            f"RefStrict={block.get('ref_correctness_strict','-')}  "
            f"p50={block.get('latency_p50_ms','-')}ms"
        )

    # AIReg-Bench
    ab = payload.get("aireg_bench", {})
    lines.append("")
    lines.append(
        f"[AIREG-BENCH] n={ab.get('n','-')}  "
        f"source={ab.get('source','-')}  "
        f"fallback={ab.get('fallback_used','-')}"
    )
    lines.append(
        f"  ArticleF1={ab.get('article_f1','-')}  "
        f"VerdictAcc={ab.get('verdict_accuracy','-')}  "
        f"Precision={ab.get('article_precision','-')}  "
        f"Recall={ab.get('article_recall','-')}"
    )

    # Regenold probe
    rp = payload.get("regenold_probe", {})
    summary = rp.get("summary", {})
    lines.append("")
    lines.append(
        f"[REGENOLD PROBE] n={summary.get('n','-')}  "
        f"RefStrict={summary.get('ref_strict','-')}  "
        f"AnsOverlap={summary.get('ans_overlap','-')}"
    )
    per_q = rp.get("per_question", {})
    for qid in sorted(per_q.keys()):
        q = per_q[qid]
        lines.append(
            f"  {qid:<24} n={q.get('n','-')}  "
            f"RefStrict={q.get('ref_strict','-')} "
            f"(canon={q.get('ref_strict_canonical','-')}/"
            f"para={q.get('ref_strict_paraphrase','-')})  "
            f"AnsOverlap={q.get('ans_overlap','-')}"
        )

    # AIR-Bench 2024
    air = payload.get("air_bench", {})
    if air:
        lines.append("")
        if air.get("skipped"):
            lines.append("[AIR-BENCH 2024] n=0 (skipped; set REGENOLD_AIRBENCH=1 to run)")
        else:
            lines.append(f"[AIR-BENCH 2024] n={air.get('n','-')}")
            lines.append(
                f"  RefusalCorrectness={air.get('refusal_correctness','-')}  "
                f"RefLoose={air.get('ref_correctness_loose','-')}"
            )

    lines.append("")
    lines.append(f"sidecar: {payload.get('sidecar_path','?')}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="adhoc")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--qa-limit", type=int, default=None)
    parser.add_argument("--scenario-limit", type=int, default=None)
    parser.add_argument("--aireg-limit", type=int, default=None)
    parser.add_argument("--probe-limit", type=int, default=None)
    parser.add_argument("--airbench-limit", type=int, default=None)
    args = parser.parse_args(argv)

    payload = run(
        label=args.label,
        output_dir=Path(args.output_dir) if args.output_dir else None,
        qa_limit=args.qa_limit,
        scenario_limit=args.scenario_limit,
        aireg_limit=args.aireg_limit,
        probe_limit=args.probe_limit,
        airbench_limit=args.airbench_limit,
    )
    print(_format_summary(payload))
    return 0



if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
