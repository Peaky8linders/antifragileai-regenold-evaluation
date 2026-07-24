"""Compliance Pipeline Orchestrator for Graph RAG Engine."""

from __future__ import annotations

import logging
from app.models import GraphRAGRequest, GraphRAGResponse
from app.engines.graph_rag.models import GraphQuery, GraphContext
from app.engines.graph_rag.parser import deterministic_parse
from app.engines.graph_rag.risk_engine import evaluate_ast_exemptions
from app.engines.graph_rag.retrieval import enrich_context
from app.engines.graph_rag.generators import extract_citations
from app.engines.graph_rag.config import config

logger = logging.getLogger(__name__)


def compute_confidence(context: GraphContext) -> float:
    """Compute confidence score based on context richness."""
    if getattr(context, "degraded", False):
        return 0.2
    if context.nodes_traversed == 0:
        return 0.3
    if context.nodes_traversed < 5:
        return 0.5
    if context.gaps or context.satisfied:
        return 0.85
    if len(getattr(context, "obligations", None) or ()) >= 3:
        return 0.85
    return 0.7
