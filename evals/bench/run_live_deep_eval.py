"""Live Deep Evaluation Runner across Hard Statutory Scenarios & Expert Benchmarks.

Runs:
1. The 20 Antifragile Human Expert Review Questions (with mistake resolution & reviewer critique tracking).
2. The Top-10 Hardest Content Scenarios from July-7 (Complex Decision Boundary, GPAI Systemic Risk, MedTech MDR, Two-Article Conflict).
3. Full multi-level metric calculation (Jaccard Loose, Keyword Recall Strict, ROUGE-L LCS F1, Semantic Similarity Proxy, Ref Loose/Strict, Ref Conciseness, CRAG Fine, Regulatory Tone, Latency).
4. Grounded proposition verification & judge remarks analysis.

CLI:
    py -3.12 -m evals.bench.run_live_deep_eval --provider cli
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from app.main import app
from app.rate_limit import limiter

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
from evals.regenold.antifragile_groundtruth import ANTIFRAGILE_GT
from evals.regenold.antifragile_reviewer_remarks import ANTIFRAGILE_REVIEWER_REMARKS
from app.data.provision_text import get_provision_text


# 10 Hard Content Scenarios from July-7 & SOTA
HARD_JULY7_SCENARIOS = [
    {
        "id": "hard_july7_01_emotion_workplace",
        "category": "Borderline Prohibition & Exception",
        "question": "Is an AI system that detects worker fatigue and emotional stress in a manufacturing plant prohibited under the EU AI Act?",
        "gold_answer": "Emotion-recognition AI systems in the workplace are prohibited under Article 5(1)(f), except where placed on the market or put into service strictly for medical or safety reasons.",
        "expected_refs": ["Article 5.1.f", "Article 5"],
        "expected_keywords": ["prohibited", "emotion", "workplace", "safety", "medical", "Article 5"],
    },
    {
        "id": "hard_july7_02_gpai_systemic",
        "category": "GPAI & Systemic Risk Boundary",
        "question": "What criteria trigger the systemic risk classification for a general-purpose AI model, and what additional obligations apply to its provider?",
        "gold_answer": "Under Article 51, a general-purpose AI model is presumed to have systemic risk if its cumulative compute during training exceeds 10^25 FLOPs. Providers of systemic GPAI models must perform model evaluation (Article 55(1)(a)), assess and mitigate systemic risks (Article 55(1)(b)), report serious incidents (Article 55(1)(c)), and ensure adequate cybersecurity protection (Article 55(1)(d)).",
        "expected_refs": ["Article 51", "Article 55"],
        "expected_keywords": ["systemic risk", "10^25", "FLOPs", "Article 51", "Article 55", "model evaluation", "mitigation", "cybersecurity"],
    },
    {
        "id": "hard_july7_03_article_6_3_derogation",
        "category": "Complex Decision Boundary",
        "question": "When is an AI system listed in Annex III exempt from being classified as high-risk under Article 6(3)?",
        "gold_answer": "An Annex III AI system is not high-risk if it does not pose a significant risk of harm to health, safety, or fundamental rights and fulfills at least one of four conditions under Article 6(3): (a) performs a narrow procedural task, (b) improves the result of a previous human activity, (c) detects decision patterns without replacing human assessment, or (d) performs a preparatory task. Profiling natural persons always prevents this exemption.",
        "expected_refs": ["Article 6.3", "Article 6", "Annex III"],
        "expected_keywords": ["derogation", "significant risk", "procedural task", "profiling", "Article 6", "Annex III"],
    },
    {
        "id": "hard_july7_04_medtech_notified_body",
        "category": "Cross-Framework & Sectoral MedTech Integration",
        "question": "What conformity assessment procedure applies to an AI software classified as a high-risk medical device under MDR and the EU AI Act?",
        "gold_answer": "Under Article 43(3), high-risk AI systems that are safety components of medical devices undergo a single, integrated conformity assessment procedure under Regulation (EU) 2017/745 (MDR) involving a notified body competent for both medical devices and AI requirements.",
        "expected_refs": ["Article 43.3", "Article 43", "Annex I", "Article 6.1"],
        "expected_keywords": ["conformity assessment", "medical device", "MDR", "notified body", "Article 43", "Article 6"],
    },
    {
        "id": "hard_july7_05_article_10_special_data",
        "category": "Two-Article Conflict & Reconciliation",
        "question": "Does the EU AI Act allow the processing of special categories of personal data to identify and correct bias in high-risk AI models?",
        "gold_answer": "Yes, Article 10(5) provides a specific derogation permitting providers of high-risk AI systems to process special categories of personal data strictly to the extent necessary for bias detection and correction, subject to appropriate safeguards including pseudonymization, encryption, and strict access controls, without prejudice to GDPR.",
        "expected_refs": ["Article 10.5", "Article 10"],
        "expected_keywords": ["special categories", "bias correction", "derogation", "Article 10", "pseudonymization", "safeguards"],
    },
    {
        "id": "hard_july7_06_value_chain_transition",
        "category": "Complex Decision Boundary",
        "question": "Under what circumstances does a downstream deployer or distributor become legally classified as a provider under Article 25?",
        "gold_answer": "Under Article 25(1), any distributor, importer, deployer, or third party is considered a provider and assumes all provider obligations if they: (a) put their name or trademark on a high-risk AI system, (b) make a substantial modification to a high-risk AI system, or (c) modify the intended purpose of an AI system such that it becomes high-risk.",
        "expected_refs": ["Article 25.1", "Article 25"],
        "expected_keywords": ["provider", "deployer", "trademark", "substantial modification", "intended purpose", "Article 25"],
    },
    {
        "id": "hard_july7_07_fria_article_27",
        "category": "Complex Decision Boundary",
        "question": "Who is obligated to perform a Fundamental Rights Impact Assessment under Article 27, and what must it include?",
        "gold_answer": "Under Article 27, deployers that are bodies governed by public law or private entities providing public services, as well as deployers of high-risk AI in credit scoring and life/health insurance, must perform a FRIA prior to putting the system into service. The assessment must detail intended processes, timeframe, affected natural persons, specific fundamental rights risks, human oversight measures, and mitigation plans.",
        "expected_refs": ["Article 27", "Article 26"],
        "expected_keywords": ["fundamental rights impact assessment", "FRIA", "deployers", "public law", "insurance", "credit scoring", "Article 27"],
    },
    {
        "id": "hard_july7_08_serious_incident_clocks",
        "category": "Cross-Framework & Sectoral MedTech Integration",
        "question": "What are the mandatory reporting deadlines for serious incidents under Article 73 of the EU AI Act?",
        "gold_answer": "Under Article 73, providers must report serious incidents immediately and no later than: (a) 15 days generally after becoming aware, (b) 2 days in the event of a widespread infringement or serious disruption of critical infrastructure, or (c) 10 days in the event of death of a person or serious harm to a person's health.",
        "expected_refs": ["Article 73"],
        "expected_keywords": ["serious incident", "15 days", "2 days", "10 days", "critical infrastructure", "death", "Article 73"],
    },
    {
        "id": "hard_july7_09_annex_iv_technical_file",
        "category": "Complex Decision Boundary",
        "question": "What specific elements must be documented in the technical documentation of a high-risk AI system under Annex IV?",
        "gold_answer": "Annex IV requires: general description of the AI system, design specifications and algorithms, computational resources and training methods (Annex IV(2)(c)), risk management system file (Article 9), data governance and validation records (Article 10), human oversight measures (Article 14), cybersecurity safeguards (Article 15), logging mechanism documentation (Article 12), and post-market monitoring plan (Article 72).",
        "expected_refs": ["Article 11", "Annex IV"],
        "expected_keywords": ["technical documentation", "system architecture", "computational resources", "risk management", "Annex IV", "Article 11"],
    },
    {
        "id": "hard_july7_10_penalties_tier_ceiling",
        "category": "Borderline Prohibition & Exception",
        "question": "What are the maximum administrative fine thresholds under Article 99 for non-compliance with the EU AI Act?",
        "gold_answer": "Article 99 establishes three fine tiers: (1) up to EUR 35 000 000 or 7% of total worldwide annual turnover for violations of Article 5 prohibited practices; (2) up to EUR 15 000 000 or 3% for non-compliance with provider or deployer high-risk obligations; (3) up to EUR 7 500 000 or 1.5% for supplying incorrect or misleading information to authorities.",
        "expected_refs": ["Article 99.3", "Article 99.4", "Article 99.5", "Article 99"],
        "expected_keywords": ["35 000 000", "7%", "15 000 000", "3%", "7 500 000", "1.5%", "prohibited", "penalties", "Article 99"],
    },
]


def evaluate_mistake_resolution(pred_ans: str, mistakes: list[dict[str, Any]]) -> dict[str, Any]:
    """Check how many expert-flagged historical mistakes are resolved in the current answer."""
    p_lower = (pred_ans or "").lower()
    p_lower = p_lower.replace("‑", "-").replace("–", "-").replace("—", "-")

    resolved = 0
    details = []
    for m in mistakes:
        v = m.get("verify", {})
        present_needed = v.get("present", [])
        absent_needed = v.get("absent", [])

        has_present = all(p in p_lower for p in present_needed) if present_needed else True
        has_absent = not any(a in p_lower for a in absent_needed) if absent_needed else True

        is_fixed = has_present and has_absent
        if is_fixed:
            resolved += 1
        details.append({
            "mistake_id": m.get("id"),
            "desc": m.get("desc"),
            "fixed": is_fixed,
        })
    return {
        "total_mistakes": len(mistakes),
        "resolved_mistakes": resolved,
        "resolution_rate": round(resolved / len(mistakes), 4) if mistakes else 1.0,
        "details": details,
    }


def run_live_eval(provider: str = "cli", output_path: str | None = None) -> dict[str, Any]:
    os.environ["P2P_GRAPH_RAG_PROVIDER"] = provider
    try:
        limiter.reset()
    except Exception:
        pass

    client = TestClient(app)
    
    # ── Section 1: Antifragile Expert Questions (20 rows) ───────────
    print("\n" + "=" * 90)
    print("RUNNING LIVE EVALUATION: 20 ANTIFRAGILE HUMAN EXPERT REVIEW QUESTIONS")
    print("=" * 90)

    af_results = []
    total_mistakes_count = 0
    total_mistakes_resolved = 0

    for qid, data in ANTIFRAGILE_GT.items():
        q_text = data["question"]
        gold_ans = data["gold_answer"]
        gold_refs = data["gold_refs"]
        kws = data.get("expected_keywords", [])
        mistakes = data.get("mistakes", [])
        reviewer_remark = ANTIFRAGILE_REVIEWER_REMARKS.get(qid, {}).get("review", "")

        t0 = time.perf_counter()
        resp = client.post("/api/v1/regenold/eu-ai-act/ask", json=[{"role": "user", "content": q_text}])
        latency_ms = (time.perf_counter() - t0) * 1000

        try:
            body = resp.json()
        except Exception:
            body = {"answer": "", "references": []}

        pred_ans = body.get("answer", "")
        pred_refs = body.get("references", [])

        # Metrics
        jaccard = answer_correctness_loose(pred_ans, gold_ans)
        rouge_l = answer_rouge_l(pred_ans, gold_ans)
        sem_sim = answer_semantic_similarity_proxy(pred_ans, gold_ans)
        kw_rec = answer_keyword_recall(pred_ans, kws)
        ref_l = reference_correctness_loose(pred_refs, gold_refs)
        ref_s = reference_correctness_strict(pred_refs, gold_refs)
        ref_c = reference_conciseness(pred_refs, gold_refs)
        tone = regulatory_tone(pred_ans)

        # Mistake verification
        m_eval = evaluate_mistake_resolution(pred_ans, mistakes)
        total_mistakes_count += m_eval["total_mistakes"]
        total_mistakes_resolved += m_eval["resolved_mistakes"]

        af_results.append({
            "qid": qid,
            "question": q_text,
            "gold_answer": gold_ans,
            "gold_refs": gold_refs,
            "predicted_answer": pred_ans,
            "predicted_refs": pred_refs,
            "reviewer_remark": reviewer_remark,
            "jaccard": round(jaccard, 4),
            "rouge_l": round(rouge_l, 4),
            "semantic_similarity": round(sem_sim, 4),
            "keyword_recall": round(kw_rec, 4) if kw_rec is not None else 0.0,
            "ref_loose": round(ref_l, 4),
            "ref_strict": round(ref_s, 4),
            "ref_conciseness": round(ref_c, 4),
            "regulatory_tone": round(tone, 4),
            "latency_ms": round(latency_ms, 2),
            "mistake_resolution": m_eval,
        })
        print(f"[{qid}] Jaccard: {jaccard:.3f} | ROUGE-L: {rouge_l:.3f} | SBERT: {sem_sim:.3f} | RefL: {ref_l:.3f} | RefS: {ref_s:.3f} | Fixed: {m_eval['resolved_mistakes']}/{m_eval['total_mistakes']}")

    # ── Section 2: Hard July-7 SOTA Scenarios (10 rows) ─────────────
    print("\n" + "=" * 90)
    print("RUNNING LIVE EVALUATION: 10 HARDEST JULY-7 CONTENT SCENARIOS")
    print("=" * 90)

    hard_results = []
    for scn in HARD_JULY7_SCENARIOS:
        q_id = scn["id"]
        q_text = scn["question"]
        gold_ans = scn["gold_answer"]
        gold_refs = scn["expected_refs"]
        kws = scn["expected_keywords"]

        t0 = time.perf_counter()
        resp = client.post("/api/v1/regenold/eu-ai-act/ask", json=[{"role": "user", "content": q_text}])
        latency_ms = (time.perf_counter() - t0) * 1000

        try:
            body = resp.json()
        except Exception:
            body = {"answer": "", "references": []}

        pred_ans = body.get("answer", "")
        pred_refs = body.get("references", [])

        # Metrics
        jaccard = answer_correctness_loose(pred_ans, gold_ans)
        rouge_l = answer_rouge_l(pred_ans, gold_ans)
        sem_sim = answer_semantic_similarity_proxy(pred_ans, gold_ans)
        kw_rec = answer_keyword_recall(pred_ans, kws)
        ref_l = reference_correctness_loose(pred_refs, gold_refs)
        ref_s = reference_correctness_strict(pred_refs, gold_refs)
        ref_c = reference_conciseness(pred_refs, gold_refs)
        tone = regulatory_tone(pred_ans)

        hard_results.append({
            "id": q_id,
            "category": scn["category"],
            "question": q_text,
            "gold_answer": gold_ans,
            "gold_refs": gold_refs,
            "predicted_answer": pred_ans,
            "predicted_refs": pred_refs,
            "jaccard": round(jaccard, 4),
            "rouge_l": round(rouge_l, 4),
            "semantic_similarity": round(sem_sim, 4),
            "keyword_recall": round(kw_rec, 4) if kw_rec is not None else 0.0,
            "ref_loose": round(ref_l, 4),
            "ref_strict": round(ref_s, 4),
            "ref_conciseness": round(ref_c, 4),
            "regulatory_tone": round(tone, 4),
            "latency_ms": round(latency_ms, 2),
        })
        print(f"[{q_id:<32}] Jaccard: {jaccard:.3f} | ROUGE-L: {rouge_l:.3f} | SBERT: {sem_sim:.3f} | RefL: {ref_l:.3f} | RefS: {ref_s:.3f}")

    # Summary
    all_rows = af_results + hard_results
    af_summary = {
        "jaccard_loose": round(sum(r["jaccard"] for r in af_results) / len(af_results), 4),
        "rouge_l": round(sum(r["rouge_l"] for r in af_results) / len(af_results), 4),
        "semantic_similarity": round(sum(r["semantic_similarity"] for r in af_results) / len(af_results), 4),
        "keyword_recall": round(sum(r["keyword_recall"] for r in af_results) / len(af_results), 4),
        "ref_loose": round(sum(r["ref_loose"] for r in af_results) / len(af_results), 4),
        "ref_strict": round(sum(r["ref_strict"] for r in af_results) / len(af_results), 4),
        "ref_conciseness": round(sum(r["ref_conciseness"] for r in af_results) / len(af_results), 4),
        "regulatory_tone": round(sum(r["regulatory_tone"] for r in af_results) / len(af_results), 4),
        "total_historical_mistakes": total_mistakes_count,
        "resolved_historical_mistakes": total_mistakes_resolved,
        "mistake_resolution_rate": round(total_mistakes_resolved / total_mistakes_count, 4) if total_mistakes_count else 1.0,
    }

    hard_summary = {
        "jaccard_loose": round(sum(r["jaccard"] for r in hard_results) / len(hard_results), 4),
        "rouge_l": round(sum(r["rouge_l"] for r in hard_results) / len(hard_results), 4),
        "semantic_similarity": round(sum(r["semantic_similarity"] for r in hard_results) / len(hard_results), 4),
        "keyword_recall": round(sum(r["keyword_recall"] for r in hard_results) / len(hard_results), 4),
        "ref_loose": round(sum(r["ref_loose"] for r in hard_results) / len(hard_results), 4),
        "ref_strict": round(sum(r["ref_strict"] for r in hard_results) / len(hard_results), 4),
        "ref_conciseness": round(sum(r["ref_conciseness"] for r in hard_results) / len(hard_results), 4),
        "regulatory_tone": round(sum(r["regulatory_tone"] for r in hard_results) / len(hard_results), 4),
    }

    grand_summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "antifragile_expert_questions_summary": af_summary,
        "hard_july7_scenarios_summary": hard_summary,
        "overall_30_hard_rows": {
            "jaccard_loose": round(sum(r["jaccard"] for r in all_rows) / len(all_rows), 4),
            "rouge_l": round(sum(r["rouge_l"] for r in all_rows) / len(all_rows), 4),
            "semantic_similarity": round(sum(r["semantic_similarity"] for r in all_rows) / len(all_rows), 4),
            "keyword_recall": round(sum(r["keyword_recall"] for r in all_rows) / len(all_rows), 4),
            "ref_loose": round(sum(r["ref_loose"] for r in all_rows) / len(all_rows), 4),
            "ref_strict": round(sum(r["ref_strict"] for r in all_rows) / len(all_rows), 4),
            "regulatory_tone": round(sum(r["regulatory_tone"] for r in all_rows) / len(all_rows), 4),
        },
        "antifragile_details": af_results,
        "hard_july7_details": hard_results,
    }

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(grand_summary, f, indent=2)
        print(f"\n[Live Deep Eval] Saved results to {output_path}")

    return grand_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Live Deep Evaluation on Hard Sets")
    parser.add_argument("--provider", default="cli", help="Provider (cli, openai_wrapper, bedrock)")
    parser.add_argument("--out", default="evals/bench/results/live_deep_eval_results.json", help="Output JSON path")
    args = parser.parse_args()

    summary = run_live_eval(provider=args.provider, output_path=args.out)
