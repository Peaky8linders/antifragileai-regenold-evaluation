"""Route-safe additive recall module using Neo4j vector indexes and local SVD embedding index.

This module surfaces article/annex candidates that BM25 may miss by leveraging:
1. Neo4j native vector indexes (`v_article_embedding`, `v_annex_embedding`) when active.
2. Local sentence-level TF-IDF+SVD embedding index as a fail-soft fallback.

It is purely additive and route-safe (returns `[]` on any exception).
It respects two environment variables (read fresh per call):
- REGENOLD_GRAPH_VECTOR_RECALL: If "1", activates the recall path. Default OFF.
- REGENOLD_VECTOR_MIN_SIM: The similarity floor for candidates. Default "0.35".
"""
from __future__ import annotations

import logging
import os

import re
logger = logging.getLogger(__name__)

def _norm_ref(r: str) -> str:
    r = str(r).strip()
    m_art = re.search(r"(?i)\b(?:Art\.?|Article|article_)\s*(\d+)", r)
    if m_art: return f"Art. {m_art.group(1)}"
    m_ann = re.search(r"(?i)\b(?:Annex|annex_)\s*([IVXLCDM]+)", r)
    if m_ann: return f"Annex {m_ann.group(1).upper()}"
    return r

def is_enabled() -> bool:
    """Return True if the vector recall path is enabled via env and assets exist."""
    if os.environ.get("REGENOLD_GRAPH_VECTOR_RECALL") != "1":
        return False
        
    try:
        from app.engines import embeddings_index
        return embeddings_index.is_available()
    except Exception as exc:  # noqa: BLE001
        logger.warning("vector_recall: is_available check failed: %s", exc)
        return False


def _query_neo4j_vector_index(question: str, top_k: int, min_sim: float) -> list[tuple[str, float]]:
    """Query Neo4j native vector indexes if driver is connected. Returns list of (ref, score)."""
    try:
        from app.graph.client import get_graph_client  # noqa: PLC0415
        client = get_graph_client()
        if not getattr(client, "enabled", False):
            return []

        from app.engines.embeddings_index import _embed_query  # noqa: PLC0415
        from app.engines.kg_context import _bounded_execute_read  # noqa: PLC0415

        vec = _embed_query(question)
        if vec is None:
            return []

        emb_list = [float(x) for x in vec]
        hits: list[tuple[str, float]] = []

        cypher_art = """
        CALL db.index.vector.queryNodes('v_article_embedding', $k, $emb)
        YIELD node, score
        RETURN coalesce(node.strict_citation, node.id) AS ref, score
        """
        art_res = _bounded_execute_read(cypher_art, {"k": top_k * 2, "emb": emb_list})
        for r in art_res or []:
            ref = str(r.get("ref") or "").strip()
            score = float(r.get("score") or 0.0)
            if ref and score >= min_sim:
                hits.append((ref, score))

        cypher_annex = """
        CALL db.index.vector.queryNodes('v_annex_embedding', $k, $emb)
        YIELD node, score
        RETURN coalesce(node.strict_citation, node.id) AS ref, score
        """
        annex_res = _bounded_execute_read(cypher_annex, {"k": top_k * 2, "emb": emb_list})
        for r in annex_res or []:
            ref = str(r.get("ref") or "").strip()
            score = float(r.get("score") or 0.0)
            if ref and score >= min_sim:
                hits.append((ref, score))

        return hits
    except Exception as exc:  # noqa: BLE001
        logger.debug("vector_recall: neo4j vector query skipped/failed: %s", exc)
        return []


def recall_articles(question: str, *, top_k: int = 3) -> list[str]:
    """Return up to `top_k` unique article refs matching the question.

    Queries Neo4j vector indexes first if active; falls back to the local sentence-level
    embeddings index.

    Returns `[]` on every error path (route-safe). Filters hits by the
    `REGENOLD_VECTOR_MIN_SIM` threshold and verifies the article exists
    in `ARTICLE_EXISTENCE`.
    """
    if not is_enabled():
        return []

    try:
        from app.engines import embeddings_index
        from app.data import article_existence
    except Exception as exc:  # noqa: BLE001
        logger.warning("vector_recall: failed to import dependencies: %s", exc)
        return []

    try:
        min_sim_str = os.environ.get("REGENOLD_VECTOR_MIN_SIM", "0.35")
        min_sim = float(min_sim_str)
    except Exception as exc:  # noqa: BLE001
        logger.warning("vector_recall: failed to parse REGENOLD_VECTOR_MIN_SIM: %s", exc)
        min_sim = 0.35

    article_scores: dict[str, float] = {}

    # 1. Primary path: Try Neo4j native vector search
    n4j_hits = _query_neo4j_vector_index(question, top_k=top_k * 2, min_sim=min_sim)
    for raw_ref, score in n4j_hits:
        ref = _norm_ref(raw_ref)
        if ref not in article_scores or score > article_scores[ref]:
            article_scores[ref] = score

    # 2. Fallback path: If Neo4j yielded no hits, query local embeddings index
    if not article_scores:
        try:
            hits = embeddings_index.query(question, top_k=50, threshold=min_sim)
            for hit in hits:
                ref = _norm_ref(hit.article_ref)
                if ref not in article_scores:
                    article_scores[ref] = hit.similarity
                else:
                    article_scores[ref] = max(article_scores[ref], hit.similarity)
        except Exception as exc:  # noqa: BLE001
            logger.warning("vector_recall: embeddings_index.query failed: %s", exc)
            return []

    try:
        sorted_refs = sorted(article_scores.keys(), key=lambda r: article_scores[r], reverse=True)
        valid_refs = set(article_existence.ARTICLE_EXISTENCE)
    except Exception as exc:  # noqa: BLE001
        logger.warning("vector_recall: failed to process hits: %s", exc)
        return []

    results = []
    for ref in sorted_refs:
        if ref in valid_refs:
            results.append(ref)
            if len(results) >= top_k:
                break

    return results

__all__ = [
    "is_enabled",
    "recall_articles",
]
