"""HippoRAG-2 style Graph Expansion Engine over the KnowledgeGraph (plan §5, §7).

Lexical/dense seed retrieval + deterministic graph score-propagation along
HAS_CHILD, CROSS_REFERENCES_INTERNAL, and INTERPRETED_BY edges.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.engines.retrieval_stack import Retriever, TfidfRetriever
from app.graph.knowledge_graph import KnowledgeGraph, build_graph
from app.graph.provision_schema import PROVISION_NODE_TYPES, EdgeType

__all__ = ["ExpansionWeights", "GraphExpansionRetriever"]


@dataclass(frozen=True)
class ExpansionWeights:
    """Per-relation multipliers for one expansion hop."""

    parent: float = 0.6
    child: float = 0.5
    cross_ref: float = 0.5
    recital: float = 0.4
    decay: float = 0.5


class GraphExpansionRetriever(Retriever):
    """Seed retrieval + deterministic graph score-propagation."""

    def __init__(
        self,
        provisions: list[Any],
        graph: KnowledgeGraph,
        *,
        seed_k: int = 10,
        weights: ExpansionWeights | None = None,
        max_hops: int = 1,
        min_seed_score: float = 0.0,
        retriever: Retriever | None = None,
    ) -> None:
        self.graph = graph
        self.seed_k = seed_k
        self.weights = weights or ExpansionWeights()
        self.max_hops = max_hops
        self.min_seed_score = min_seed_score
        self.seeder = retriever or TfidfRetriever(provisions)

    def _is_citeable(self, node_id: str) -> bool:
        node = self.graph.get_node(node_id)
        return node is not None and node.type in PROVISION_NODE_TYPES

    def _one_hop(self, node_id: str) -> list[tuple[str, float]]:
        w = self.weights
        out: list[tuple[str, float]] = []
        if w.parent:
            parent = self.graph.parent(node_id)
            if parent:
                out.append((parent, w.parent))
        if w.child:
            out.extend((c, w.child) for c in self.graph.children(node_id))
        if w.cross_ref:
            out.extend(
                (t, w.cross_ref)
                for t in self.graph.neighbors(node_id, EdgeType.CROSS_REFERENCES_INTERNAL)
            )
        if w.recital:
            out.extend(
                (r, w.recital) for r in self.graph.neighbors(node_id, EdgeType.INTERPRETED_BY)
            )
        return out

    def search(self, query: str, k: int) -> list[str]:
        return [pid for pid, _ in self.search_scored(query, k)]

    def search_scored(self, query: str, k: int) -> list[tuple[str, float]]:
        seeds = self.seeder.search_scored(query, self.seed_k)
        if not seeds or seeds[0][1] < self.min_seed_score:
            return []

        scores: dict[str, float] = {}

        def add(node_id: str, value: float) -> None:
            if value > 0 and self._is_citeable(node_id):
                scores[node_id] = scores.get(node_id, 0.0) + value

        # Hop 0 — seeds
        for eid, s in seeds:
            add(eid, s)

        # Hops 1..max_hops — propagate along structural edges
        frontier = list(seeds)
        for hop in range(1, self.max_hops + 1):
            decay = self.weights.decay ** (hop - 1)
            nxt: list[tuple[str, float]] = []
            for eid, s in frontier:
                for neighbor, weight in self._one_hop(eid):
                    contrib = s * weight * decay
                    add(neighbor, contrib)
                    nxt.append((neighbor, contrib))
            frontier = nxt

        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        return ranked[:k]


_GLOBAL_EXPANSION_RETRIEVER: GraphExpansionRetriever | None = None
_GLOBAL_GRAPHRAG_GRAPH: KnowledgeGraph | None = None


def get_global_graph_expansion_retriever() -> GraphExpansionRetriever | None:
    """Return singleton GraphExpansionRetriever loaded over full provisions corpus."""
    global _GLOBAL_EXPANSION_RETRIEVER, _GLOBAL_GRAPHRAG_GRAPH
    if _GLOBAL_EXPANSION_RETRIEVER is not None:
        return _GLOBAL_EXPANSION_RETRIEVER
    try:
        import json
        from pathlib import Path
        root_dir = Path(__file__).resolve().parents[2]
        prov_path = root_dir / "euairagtest" / "provisions.json"
        if prov_path.exists():
            with open(prov_path, encoding="utf-8") as f:
                provisions = json.load(f)
            _GLOBAL_GRAPHRAG_GRAPH = build_graph(provisions)
            _GLOBAL_EXPANSION_RETRIEVER = GraphExpansionRetriever(
                provisions, _GLOBAL_GRAPHRAG_GRAPH, seed_k=10, max_hops=1
            )
            return _GLOBAL_EXPANSION_RETRIEVER
    except Exception:
        pass
    return None
