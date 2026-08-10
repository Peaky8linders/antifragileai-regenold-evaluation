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
from pathlib import Path

# Disable Neo4j auto-seeding before any app imports
os.environ["NEO4J_AUTO_SEED"] = "0"
os.environ.setdefault("REGENOLD_GRAPH_VECTOR_RECALL", "1")
# Step 1 evaluates ranking, so retain the top-k even below the production
# admission threshold. Applying 0.35 first would censor low-score negatives and
# make correct-vs-wrong AUC optimistic.
os.environ["REGENOLD_VECTOR_MIN_SIM"] = "-1.0"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("eval_vector_recall_gold")

from app.data import article_existence  # noqa: E402
from app.data.kb_search import top_articles_by_relevance  # noqa: E402
from app.engines.embeddings_index import is_available as embeddings_available  # noqa: E402
from app.engines.vector_recall import recall_articles_with_provenance  # noqa: E402

VALID_ARTICLES = set(article_existence.ARTICLE_EXISTENCE)


def roc_auc(scored_labels: list[tuple[float, bool]]) -> float | None:
    """Tie-aware Mann-Whitney ROC-AUC without an optional sklearn dependency."""
    positives = [score for score, label in scored_labels if label]
    negatives = [score for score, label in scored_labels if not label]
    if not positives or not negatives:
        return None
    wins = 0.0
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return wins / (len(positives) * len(negatives))

def normalize_exact_ref(ref: str) -> str:
    """Normalize spelling while retaining a supplied sub-provision coordinate."""
    r = str(ref).strip()
    import re

    art = re.search(r"(?i)\b(?:article_|article\s+|art\.?\s*)(\d{1,3}(?:[.(]\w+\)?)*)(?:\b|$)", r)
    if art:
        coordinate = art.group(1).replace("(", ".").replace(")", "").strip(".")
        return f"Article {coordinate}"
    annex = re.search(r"(?i)\b(?:annex_|annex\s+)([IVXLCDM]+(?:\.\w+)*)", r)
    if annex:
        return f"Annex {annex.group(1).upper()}"
    return r


def normalize_ref(ref: str) -> str:
    """Collapse an exact coordinate to the canonical retrieval head."""
    exact = normalize_exact_ref(ref)
    if exact.startswith("Article "):
        return f"Art. {exact.split()[1].split('.')[0]}"
    if exact.startswith("Annex "):
        return f"Annex {exact.split()[1]}"
    return exact


def run_evaluation() -> int:
    ckpt_path = Path("evals/bench/results/official-r318-july7-easy-easy.ckpt.jsonl")
    grounded_path = Path("evals/bench/results/grounded-r318-july7-grounded.json")

    if not ckpt_path.exists() or not grounded_path.exists():
        logger.error("Missing input files: %s or %s", ckpt_path, grounded_path)
        return 2

    if not embeddings_available():
        logger.error("Embedding assets are unavailable; vector recall was not evaluated")
        return 2

    with open(grounded_path, encoding="utf-8") as f:
        grounded_data = json.load(f)

    grounded_map = {}
    for row in grounded_data.get("rows", []):
        row_id = row.get("id")
        ref_verdict = row.get("verdicts", {}).get("reference_correctness", {})
        if not ref_verdict:
            continue
        wrong = [normalize_exact_ref(r) for r in ref_verdict.get("wrong_refs", [])]
        missing = [normalize_exact_ref(r) for r in ref_verdict.get("missing_refs", [])]
        grounded_map[row_id] = {"wrong": set(wrong), "missing": set(missing)}

    ckpt_rows = []
    with open(ckpt_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ckpt_rows.append(json.loads(line))

    logger.info("Loaded %d rows from checkpoint, %d grounded verdicts", len(ckpt_rows), len(grounded_map))

    total_rows = 0
    bm25_miss_count = 0
    vector_recovered_count = 0
    recovered_refs = 0
    missed_refs = 0
    reciprocal_rank_sum = 0.0
    native_rows = 0
    local_rows = 0
    auc_observations: list[tuple[float, bool]] = []
    native_auc_observations: list[tuple[float, bool]] = []
    recovered_rows = []

    for row in ckpt_rows:
        row_id = row.get("id")
        question = row.get("question", "")
        pred_refs = [normalize_exact_ref(r) for r in row.get("pred_refs", [])]

        g_info = grounded_map.get(row_id)
        if g_info is None:
            # Absence of a verdict is missing evidence, not proof that every
            # predicted reference was correct.
            continue
        wrong_set = g_info["wrong"]
        missing_set = g_info["missing"]

        # This is judge-adjudicated pseudo-gold, not the competition's hidden
        # official ground truth. Remove wrong refs at their exact coordinate
        # before collapsing to heads, otherwise a wrong parent erases a correct
        # child of the same Article.
        gold_exact = (set(pred_refs) - wrong_set) | missing_set
        gold_set = {normalize_ref(r) for r in gold_exact}
        gold_set &= VALID_ARTICLES

        if not gold_set:
            continue

        total_rows += 1

        # 1. BM25 candidate set B (top 5)
        bm25_hits_raw = top_articles_by_relevance(question, k=5, min_score=1.0)
        B = set(normalize_ref(r) for r in bm25_hits_raw if normalize_ref(r) in VALID_ARTICLES)

        # 2. Production vector path, including native-first valid-hit fallback.
        v_hits = recall_articles_with_provenance(question, top_k=50)
        sorted_v_refs = [hit.ref for hit in v_hits]
        V = set(sorted_v_refs[:5])
        for hit in v_hits:
            observation = (hit.score, hit.ref in gold_set)
            auc_observations.append(observation)
            if hit.source.startswith("neo4j:"):
                native_auc_observations.append(observation)
        if any(hit.source.startswith("neo4j:") for hit in v_hits):
            native_rows += 1
        if any(hit.source.startswith("local:") for hit in v_hits):
            local_rows += 1

        # Gold missed by BM25: gold \ B
        gold_bm25_misses = gold_set - B
        if gold_bm25_misses:
            bm25_miss_count += 1
            missed_refs += len(gold_bm25_misses)

        # Gold recovered by Vector that BM25 missed: V \cap (gold \ B)
        recovered_gold = V & gold_bm25_misses
        if recovered_gold:
            vector_recovered_count += 1
            recovered_refs += len(recovered_gold)
            first_rank = min(
                idx for idx, ref in enumerate(sorted_v_refs, start=1)
                if ref in recovered_gold
            )
            reciprocal_rank_sum += 1.0 / first_rank
            recovered_rows.append({
                "id": row_id,
                "question": question[:80],
                "gold": list(gold_set),
                "B": list(B),
                "V": list(sorted_v_refs[:3]),
                "sources": [hit.source for hit in v_hits[:3]],
                "recovered": list(recovered_gold)
            })

    recovery_pct = (vector_recovered_count / total_rows * 100) if total_rows > 0 else 0
    miss_pct = (bm25_miss_count / total_rows * 100) if total_rows > 0 else 0
    conditional_pct = (
        vector_recovered_count / bm25_miss_count * 100
        if bm25_miss_count else 0
    )
    ref_recall = recovered_refs / missed_refs if missed_refs else 0.0
    mrr = reciprocal_rank_sum / bm25_miss_count if bm25_miss_count else 0.0
    overall_auc = roc_auc(auc_observations)
    native_auc = roc_auc(native_auc_observations)

    print("=" * 60)
    print(f"STEP 1 EVALUATION RESULTS ({total_rows} evaluated rows)")
    print("=" * 60)
    print(f"Rows where BM25 missed at least 1 gold ref: {bm25_miss_count}/{total_rows} ({miss_pct:.1f}%)")
    print(f"Rows where Vector layer recovered gold missed by BM25: {vector_recovered_count}/{total_rows} ({recovery_pct:.1f}%)")
    print(f"Conditional recovery on BM25-miss rows: {conditional_pct:.1f}%")
    print(f"Missed-reference Recall@5: {ref_recall:.3f} | MRR@5: {mrr:.3f}")
    print(f"Retrieval provenance: native rows={native_rows}, local-fallback rows={local_rows}")
    print(
        "Correct-vs-wrong ROC-AUC (judge pseudo-gold): "
        f"overall={overall_auc if overall_auc is not None else 'unscorable'} | "
        f"native={native_auc if native_auc is not None else 'unscorable'}"
    )
    if native_auc is not None:
        role = "ranker signal" if native_auc > 0.703 else "recall-only signal"
        print(f"Native AUC interpretation vs 0.703 benchmark: {role}")
    print("-" * 60)

    if total_rows == 0 or (native_rows + local_rows) == 0:
        print("--> DECISION: INCONCLUSIVE (no usable gold rows or vector evidence)")
    elif native_rows == 0 or native_auc is None:
        print(
            "--> DECISION: INCONCLUSIVE_NATIVE "
            "(local fallback was measured, but Aura native recall was not)"
        )
    elif recovery_pct >= 10.0:
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
            print(f"      Vector provenance: {item['sources']}")

    if (
        total_rows == 0
        or (native_rows + local_rows) == 0
        or native_rows == 0
        or native_auc is None
    ):
        return 2
    return 0 if recovery_pct >= 5.0 else 1

if __name__ == "__main__":
    raise SystemExit(run_evaluation())
