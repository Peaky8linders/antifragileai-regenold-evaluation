"""Benchmark harness test bridging euairagtest gold benchmark into pytest."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from app.data.ids import ProvisionId
from app.graph.knowledge_graph import build_graph
from app.engines.graph_expansion_engine import GraphExpansionRetriever, ExpansionWeights
from app.engines.retrieval_stack import TfidfRetriever

BENCHMARK_PATH = Path(__file__).resolve().parents[1] / "euairagtest" / "eu_ai_act_bench_easy.json"
PROVISIONS_PATH = Path(__file__).resolve().parents[1] / "euairagtest" / "provisions.json"


def _common_prefix_len(a: ProvisionId, b: ProvisionId) -> int:
    n = 0
    for sa, sb in zip(a.segments, b.segments):
        if sa.kind == sb.kind and sa.value == sb.value:
            n += 1
        else:
            break
    return n


def provision_similarity(a: ProvisionId, b: ProvisionId) -> float:
    da, db = len(a.segments), len(b.segments)
    lcp = _common_prefix_len(a, b)
    if lcp == min(da, db):
        return lcp / max(da, db)
    return 0.0


def score_item(preds: list[str], golds: list[Any]) -> tuple[float, float, float]:
    """Return (precision, recall, f1) soft scores."""
    if not golds:
        return (0.0, 1.0, 1.0) if not preds else (0.0, 0.0, 0.0)
    if not preds:
        return (0.0, 0.0, 0.0)

    gold_strs = []
    for g in golds:
        if isinstance(g, dict):
            gold_strs.append(g.get("provision_id") or g.get("citation"))
        elif isinstance(g, str):
            gold_strs.append(g)

    pred_ids = []
    for p in preds:
        try:
            pred_ids.append(ProvisionId.parse(p))
        except Exception:
            pass

    gold_ids = []
    for g in gold_strs:
        if not g:
            continue
        try:
            gold_ids.append(ProvisionId.parse(g))
        except Exception:
            pass

    if not pred_ids or not gold_ids:
        return (0.0, 0.0, 0.0)

    # Calculate max match for each pred in gold
    p_sims = [max(provision_similarity(p, g) for g in gold_ids) for p in pred_ids]
    precision = sum(p_sims) / len(pred_ids)

    # Calculate max match for each gold in pred
    g_sims = [max(provision_similarity(p, g) for p in pred_ids) for g in gold_ids]
    recall = sum(g_sims) / len(gold_ids)

    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return (precision, recall, f1)


@pytest.mark.skipif(not BENCHMARK_PATH.exists() or not PROVISIONS_PATH.exists(), reason="euairagtest data files not found")
def test_graphrag_benchmark_easy_sample():
    with open(BENCHMARK_PATH, encoding="utf-8") as f:
        bench_data = json.load(f)

    items = bench_data.get("items", bench_data) if isinstance(bench_data, dict) else bench_data

    with open(PROVISIONS_PATH, encoding="utf-8") as f:
        provisions = json.load(f)

    graph = build_graph(provisions)
    retriever = GraphExpansionRetriever(provisions, graph, seed_k=10)

    f1_scores = []
    # Test on a sample of 10 items for speed
    for item in items[:10]:
        q = item.get("question") or item.get("query")
        golds = item.get("gold_citations", [])
        if not q or not golds:
            continue

        preds = retriever.search(q, k=5)
        _, _, f1 = score_item(preds, golds)
        f1_scores.append(f1)

    avg_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
    # Graph expansion should achieve non-zero citation recall on easy benchmark items
    assert avg_f1 > 0.10
