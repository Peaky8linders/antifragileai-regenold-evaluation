"""§8 evaluation baselines: systems the GraphRAG design must beat (and the first
graph-using system among them).

  * ``NaiveRetrievalBaseline`` -- lexical/dense retrieval, no graph (runnable now)
  * ``GraphRAGBaseline``       -- lexical seed + deterministic graph-expansion
    (the first retriever that uses the Phase-2 knowledge graph; runnable now)
  * ``FrontierLLMBaseline``    -- frontier LLM, optional full-Act context (needs
    the ``baselines`` optional dep + an API key; import lazily)

All baselines emit ``{item_id: [citation, ...]}`` via ``run_baseline`` /
``write_predictions`` for ``eu-ai-act-benchmark/scorer.py``.
"""

from __future__ import annotations

from .base import Baseline, question_text, run_baseline, write_predictions
from .extract import extract_citations
from .graph_rag import ExpansionWeights, GraphExpansionRetriever, GraphRAGBaseline
from .naive_rag import NaiveRetrievalBaseline
from .retrieval import Retriever, TfidfRetriever, tokenize

__all__ = [
    "Baseline",
    "question_text",
    "run_baseline",
    "write_predictions",
    "extract_citations",
    "NaiveRetrievalBaseline",
    "GraphRAGBaseline",
    "GraphExpansionRetriever",
    "ExpansionWeights",
    "Retriever",
    "TfidfRetriever",
    "tokenize",
]
