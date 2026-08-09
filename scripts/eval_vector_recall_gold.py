"""R326 Step 1 Offline Evaluation: Does the vector layer find gold BM25 misses?

Evaluates |V ∩ gold \\ B| across the 100 recorded rows in:
- evals/bench/results/official-r318-july7-easy-easy.ckpt.jsonl
- evals/bench/results/grounded-r318-july7-grounded.json

Gate Criteria:
- PROCEED if vector recall finds gold missed by BM25 on >= 10% of rows.
- KILL if < 5% of rows, or if hits are merely the same BM25 articles re-ordered.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

# Disable Neo4j auto-seeding before any app imports
os.environ["NEO4J_AUTO_SEED"] = "0"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval_vector_recall_gold")

from app.data.kb_search import top_articles_by_relevance
from app.engines.embeddings_index import query as embeddings_query, is_available as embeddings_available
from app.data import article_existence

VALID_ARTICLES = set(article_existence.ARTICLE_EXISTENCE)

def normalize_ref(ref: str) -> str:
    """Normalize 'Article 5' / 'Art. 5' / 'article_5' to 'Article N'."""
    r = str(ref).strip()
    if r.startswith("article_"):
        try:
            return f"Article {int(r.split('_')[1])}"
        except (IndexError, ValueError):
            pass
    if r.lower().startswith("art."):
        return f"Article {r[4:].strip()}"
    if r.lower().startswith("art "):
        return f"Article {r[4:].strip()}"
    if r.lower().startswith("article "):
        return f"Article {r[8:].strip()}"
    return r

def run_evaluation():
    ckpt_path = Path("evals/bench/results/official-r318-july7-easy-easy.ckpt.jsonl")
    grounded_path = Path("evals/bench/results/grounded-r318-july7-grounded.json")

    if not ckpt_path.exists() or not grounded_path.exists():
        logger.error("Missing input files: %s or %s", ckpt_path, grounded_path)
        sys.exit(1)

    with open(grounded_path, "r", encoding="utf-8") as f:
        grounded_data = json.load(f)

    grounded_map = {}
    for row in grounded_data.get("rows", []):
        row_id = row.get("id")
        ref_verdict = row.get("verdicts", {}).get("reference_correctness", {})
        wrong = [normalize_ref(r) for r in ref_verdict.get("wrong_refs", [])]
        missing = [normalize_ref(r) for r in ref_verdict.get("missing_refs", [])]
        grounded_map[row_id] = {"wrong": set(wrong), "missing": set(missing)}

    ckpt_rows = []
    with open(ckpt_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ckpt_rows.append(json.loads(line))

    logger.info("Loaded %d rows from checkpoint, %d grounded verdicts", len(ckpt_rows), len(grounded_map))

    total_rows = 0
    bm25_miss_count = 0
    vector_recovered_count = 0
    recovered_rows = []

    for row in ckpt_rows:
        row_id = row.get("id")
        question = row.get("question", "")
        pred_refs = [normalize_ref(r) for r in row.get("pred_refs", [])]

        g_info = grounded_map.get(row_id, {"wrong": set(), "missing": set()})
        wrong_set = g_info["wrong"]
        missing_set = g_info["missing"]

        # Gold = (pred_refs - wrong_refs) | missing_refs
        gold_set = (set(pred_refs) - wrong_set) | missing_set
        gold_set = {r for r in gold_set if r in VALID_ARTICLES}

        if not gold_set:
            continue

        total_rows += 1

        # 1. BM25 candidate set B (top 5)
        bm25_hits_raw = top_articles_by_relevance(question, k=5, min_score=1.0)
        B = set(normalize_ref(r) for r in bm25_hits_raw if normalize_ref(r) in VALID_ARTICLES)

        # 2. Vector candidate set V (sentence embeddings top 50 collapsed to articles)
        v_hits_raw = embeddings_query(question, top_k=50, threshold=0.35)
        v_article_scores = {}
        for hit in v_hits_raw:
            ref_norm = normalize_ref(hit.article_ref)
            if ref_norm in VALID_ARTICLES:
                if ref_norm not in v_article_scores:
                    v_article_scores[ref_norm] = hit.similarity
                else:
                    v_article_scores[ref_norm] = max(v_article_scores[ref_norm], hit.similarity)

        sorted_v_refs = sorted(v_article_scores.keys(), key=lambda r: v_article_scores[r], reverse=True)
        V = set(sorted_v_refs[:5])

        # Gold missed by BM25: gold \ B
        gold_bm25_misses = gold_set - B
        if gold_bm25_misses:
            bm25_miss_count += 1

        # Gold recovered by Vector that BM25 missed: V \cap (gold \ B)
        recovered_gold = V & gold_bm25_misses
        if recovered_gold:
            vector_recovered_count += 1
            recovered_rows.append({
                "id": row_id,
                "question": question[:80],
                "gold": list(gold_set),
                "B": list(B),
                "V": list(sorted_v_refs[:3]),
                "recovered": list(recovered_gold)
            })

    recovery_pct = (vector_recovered_count / total_rows * 100) if total_rows > 0 else 0
    miss_pct = (bm25_miss_count / total_rows * 100) if total_rows > 0 else 0

    print("=" * 60)
    print(f"STEP 1 EVALUATION RESULTS ({total_rows} evaluated rows)")
    print("=" * 60)
    print(f"Rows where BM25 missed at least 1 gold ref: {bm25_miss_count}/{total_rows} ({miss_pct:.1f}%)")
    print(f"Rows where Vector layer recovered gold missed by BM25: {vector_recovered_count}/{total_rows} ({recovery_pct:.1f}%)")
    print("-" * 60)

    if recovery_pct >= 10.0:
        print(f"--> DECISION: PROCEED (>= 10.0% target met: {recovery_pct:.1f}%)")
    elif recovery_pct >= 5.0:
        print(f"--> DECISION: MARGINAL ({recovery_pct:.1f}%, between 5% and 10%)")
    else:
        print(f"--> DECISION: KILL (< 5.0% target: {recovery_pct:.1f}%)")

    if recovered_rows:
        print("\nSample Recovered Gold Rows:")
        for item in recovered_rows[:5]:
            print(f"  [{item['id']}] Question: {item['question']}...")
            print(f"      Gold: {item['gold']} | BM25: {item['B']} | Recovered by V: {item['recovered']}")

if __name__ == "__main__":
    run_evaluation()
