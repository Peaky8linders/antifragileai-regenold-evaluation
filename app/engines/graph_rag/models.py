"""Domain models for Graph RAG Compliance Q&A Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from app.models import CitationNode


@dataclass
class GraphQuery:
    """Structured query extracted from a natural language question."""
    intent: str = "general_compliance"
    entities: list[str] = field(default_factory=list)
    risk_context: str | None = None
    dimension_hint: str | None = None
    keywords: list[str] = field(default_factory=list)
    raw_question: str = ""


@dataclass
class GraphContext:
    """Structured context retrieved from the compliance graph."""
    obligations: list[dict] = field(default_factory=list)
    gaps: list[dict] = field(default_factory=list)
    bridging_context: list[str] = field(default_factory=list)
    satisfied: list[dict] = field(default_factory=list)
    dimension_info: list[dict] = field(default_factory=list)
    cross_framework: dict = field(default_factory=dict)
    article_info: list[dict] = field(default_factory=list)
    transitive_deps: list[dict] = field(default_factory=list)
    nodes_traversed: int = 0
    edges_followed: int = 0
    stage2_call_failed: bool = False
    degraded: bool = False
    xrefs: list[str] = field(default_factory=list)
    semantically_relevant_statements: list[str] = field(default_factory=list)
    referenced_annexes_and_recitals: list[dict] = field(default_factory=list)
    question: str = ""
    web_search_results: list[str] = field(default_factory=list)
    retrieval_path: str = "neo4j"
    synthesis_memory: str = ""
    ast_evaluations: list[str] = field(default_factory=list)
