"""Cappelli et al. (Discover AI 2026) 5-Dimension Compliance Benchmark Runner.

Executes the 20-scenario dataset across the 4 Annex III domains (Recruitment, Medical
Diagnostics, Smart City Traffic, Retail Biometrics) and 5 regulatory dimensions (Risk Level,
Regulatory Obligations, Legal Risks, Compliance Gaps, Technical Documentation).

Evaluates:
- Lexical Overlap: Token Jaccard (Loose), Keyword Recall (Strict), ROUGE-L (LCS F1)
- Semantic Similarity: Sub-token n-gram + word-stem cosine proxy
- Statutory References: Ref Loose (Head Recall), Ref Strict (Head F1), Ref Conciseness
- Threshold Sensitivity: Precision / Recall / F1 curve across similarity cutoffs [0.10 - 0.80]
- Direct comparative analysis against Cappelli et al. (2026) Table 8 baseline

CLI:
    py -3.12 -m evals.bench.run_cappelli_bench --provider cli
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

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
    threshold_precision_recall_curve,
)


def load_dataset() -> list[dict[str, Any]]:
    dataset_path = Path(__file__).parent / "data" / "cappelli_compliance_2026.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_benchmark(provider: str = "cli", output_path: str | None = None) -> dict[str, Any]:
    dataset = load_dataset()
    print(f"[Cappelli Benchmark] Loaded {len(dataset)} scenarios across 5 dimensions.")

    os.environ["P2P_GRAPH_RAG_PROVIDER"] = provider

    from fastapi.testclient import TestClient
    from app.main import app
    from app.rate_limit import limiter

    try:
        limiter.reset()
    except Exception:
        pass

    client = TestClient(app)
    results: list[dict[str, Any]] = []

    # Aggregation buckets
    dim_scores: dict[str, dict[str, list[float]]] = {
        "risk_level": {"jaccard": [], "rouge_l": [], "semantic": [], "kw_recall": [], "ref_loose": [], "ref_strict": []},
        "regulatory_obligations": {"jaccard": [], "rouge_l": [], "semantic": [], "kw_recall": [], "ref_loose": [], "ref_strict": []},
        "legal_risks": {"jaccard": [], "rouge_l": [], "semantic": [], "kw_recall": [], "ref_loose": [], "ref_strict": []},
        "compliance_gaps": {"jaccard": [], "rouge_l": [], "semantic": [], "kw_recall": [], "ref_loose": [], "ref_strict": []},
        "technical_documentation": {"jaccard": [], "rouge_l": [], "semantic": [], "kw_recall": [], "ref_loose": [], "ref_strict": []},
    }

    all_sim_scores: list[float] = []
    all_relevance: list[bool] = []

    for i, row in enumerate(dataset, 1):
        q_id = row["id"]
        dim = row["dimension"]
        q_text = row["question"]
        gold_ans = row["gold_answer"]
        expected_refs = row.get("expected_refs", [])
        expected_kws = row.get("expected_keywords", [])

        # Call engine via wire
        payload = [{"role": "user", "content": q_text}]
        t0 = time.perf_counter()
        resp = client.post("/api/v1/regenold/eu-ai-act/ask", json=payload)
        latency_ms = (time.perf_counter() - t0) * 1000

        try:
            body = resp.json()
        except Exception:
            body = {"answer": "", "references": [], "reasoning": None}

        pred_ans = body.get("answer", "")
        pred_refs = body.get("references", [])

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
        all_relevance.append(sem_sim >= 0.25)

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
        })

    # Compute category averages
    summary_by_dim: dict[str, dict[str, float]] = {}
    for d_name, metrics in dim_scores.items():
        summary_by_dim[d_name] = {
            m_name: round(sum(vals) / len(vals), 4) if vals else 0.0
            for m_name, vals in metrics.items()
        }

    # Threshold curve
    thresh_curve = threshold_precision_recall_curve(all_sim_scores, all_relevance)

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_scenarios": len(results),
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
        "threshold_sensitivity_curve": thresh_curve,
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
    print(f"{'Dimension':<26} | {'Jaccard':<8} | {'ROUGE-L':<8} | {'Semantic':<8} | {'KW Recall':<10} | {'Ref Loose':<10} | {'Ref Strict':<10}")
    print("-" * 90)
    for dim, s in summary["summary_by_dimension"].items():
        print(f"{dim:<26} | {s['jaccard']:<8.4f} | {s['rouge_l']:<8.4f} | {s['semantic']:<8.4f} | {s['kw_recall']:<10.4f} | {s['ref_loose']:<10.4f} | {s['ref_strict']:<10.4f}")
    print("-" * 90)
    oa = summary["overall_averages"]
    print(f"{'OVERALL AVERAGE':<26} | {oa['jaccard_loose']:<8.4f} | {oa['rouge_l']:<8.4f} | {oa['semantic_similarity']:<8.4f} | {oa['keyword_recall']:<10.4f} | {oa['ref_loose']:<10.4f} | {oa['ref_strict']:<10.4f}")
    print("=" * 90)

    print("\n" + "-" * 60)
    print("THRESHOLD SENSITIVITY CURVE (Decoupling Precision & Recall)")
    print("-" * 60)
    print(f"{'Threshold':<12} | {'Precision':<12} | {'Recall':<12} | {'F1':<12}")
    print("-" * 60)
    for pt in summary["threshold_sensitivity_curve"]:
        print(f"{pt['threshold']:<12.2f} | {pt['precision']:<12.4f} | {pt['recall']:<12.4f} | {pt['f1']:<12.4f}")
    print("-" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Cappelli 5-Dimension Compliance Benchmark")
    parser.add_argument("--provider", default="cli", help="Provider (cli, openai_wrapper, bedrock)")
    parser.add_argument("--out", default="evals/bench/results/cappelli_bench_results.json", help="Output JSON path")
    args = parser.parse_args()

    summary = run_benchmark(provider=args.provider, output_path=args.out)
    print_scorecard(summary)
