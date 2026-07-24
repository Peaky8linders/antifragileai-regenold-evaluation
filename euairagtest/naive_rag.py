"""Naive retrieval baseline (§8 baseline #2, retrieval-only variant).

Cites the top-k provisions returned by a lexical/dense ``Retriever`` -- no graph,
no cross-reference traversal, no generation step. It is the floor the GraphRAG
system must clear on citation recall. The optional-generation variant (feed the
retrieved passages to an LLM, then extract citations from its answer) plugs in
the same way once an LLM client is available -- see ``llm.py``.
"""

from __future__ import annotations

try:
    from .models import Provision
except (ImportError, ValueError):
    from ..models import Provision
from .base import Baseline, question_text
from .retrieval import Retriever, TfidfRetriever

__all__ = ["NaiveRetrievalBaseline"]


class NaiveRetrievalBaseline(Baseline):
    name = "naive-retrieval-tfidf"

    def __init__(
        self,
        provisions: list[Provision],
        k: int = 5,
        retriever: Retriever | None = None,
    ) -> None:
        self.k = k
        self.retriever = retriever or TfidfRetriever(provisions)

    def predict(self, item: dict) -> list[str]:
        return self.retriever.search(question_text(item), self.k)
