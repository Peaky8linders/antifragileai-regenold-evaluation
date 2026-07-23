"""Layer 1 — knowledge graph & ontology for the EU AI Act (plan §4).

The graph is built in two tiers:

* a **deterministic backbone** (:mod:`euaiact.graph.builder`) derived entirely from
  the Phase-1 ``Provision`` metadata + a zero-hallucination citation parser — no LLM,
  fully offline-testable; and
* an optional **ML enrichment** pass (:mod:`euaiact.graph.enrich`) that adds the
  deontic/actor/risk layer via schema-constrained extractors (lazy, heavy deps).

Everything is backend-agnostic in memory (:class:`euaiact.graph.model.KnowledgeGraph`)
and exports to Neo4j via idempotent Cypher (:mod:`euaiact.graph.cypher`).
"""

from __future__ import annotations

from .model import KnowledgeGraph
from .schema import Edge, EdgeType, Node, NodeType

__all__ = ["KnowledgeGraph", "Node", "Edge", "NodeType", "EdgeType"]
