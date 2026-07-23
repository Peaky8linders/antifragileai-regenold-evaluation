"""§8 baseline #3: graph-expansion retrieval -- the first system that actually
*uses* the knowledge graph for retrieval.

The naive baseline (``naive_rag.py``) retrieves flat lexical top-k and stops.
This one adds the whole point of the project: after a lexical **seed** step it
**propagates** each seed's score one (or more) hop along the deterministic graph
--

  * ``HAS_CHILD`` up  -> the containing paragraph / article  (RAPTOR: "retrieve
    the sub-point *and* its parent")
  * ``HAS_CHILD`` down -> the sub-points of a retrieved paragraph
  * ``CROSS_REFERENCES_INTERNAL`` -> provisions this one explicitly points to
    (PathRAG-style relational paths = citation chains)
  * ``INTERPRETED_BY`` -> the recital that interprets the provision

Scores **accumulate** across seeds (HippoRAG-2-style evidence aggregation): a
provision that several seeds converge on -- via shared parents or mutual
cross-references -- rises to the top even when its own lexical match was weak.
That multi-fact convergence is exactly where GraphRAG is supposed to beat flat
retrieval on legal cross-reference questions, and the citation scorer measures
whether it actually does.

Deterministic and dependency-light: seeds come from the pure-Python
``TfidfRetriever`` and expansion walks the in-memory ``KnowledgeGraph`` built in
Phase 2 -- no embeddings, no API, no network. Only citeable node types
(Provision / Recital / Annex / AnnexPoint) are ever emitted; vocabulary nodes
(DefinedTerm / Actor / RiskClass / DateMilestone) are traversal aids, never
citations.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..graph.model import KnowledgeGraph
from ..graph.schema import EdgeType, PROVISION_NODE_TYPES
from ..models import Provision
from .base import Baseline, question_text
from .retrieval import Retriever, TfidfRetriever

__all__ = ["ExpansionWeights", "GraphExpansionRetriever", "GraphRAGBaseline"]


@dataclass(frozen=True)
class ExpansionWeights:
    """Per-relation multipliers for one expansion hop. A neighbour reached from a
    node scoring ``s`` gains ``s * weight * decay**(hop-1)``. Zero disables a
    relation. These are tunable knobs, deliberately conservative (< 1 so an
    expanded node never outranks its own strong seed on a single vote)."""

    parent: float = 0.6  # HAS_CHILD, incoming: the containing paragraph/article
    child: float = 0.5  # HAS_CHILD, outgoing: sub-points of a retrieved node
    cross_ref: float = 0.5  # CROSS_REFERENCES_INTERNAL, outgoing
    recital: float = 0.4  # INTERPRETED_BY, outgoing: the interpreting recital
    decay: float = 0.5  # extra multiplicative decay applied on hops >= 2


class GraphExpansionRetriever(Retriever):
    """Lexical seed retrieval + deterministic graph score-propagation.

    ``seed_k`` seeds are retrieved (score = TF-IDF cosine), then scores propagate
    out ``max_hops`` along the structural edges and **accumulate** per node. The
    final ranking is by accumulated score (ties broken by id, so it's
    deterministic). ``min_seed_score`` gives the system something the flat
    retriever lacks -- the ability to **abstain**: if the best seed's cosine is
    below the threshold the query is treated as out-of-scope and ``[]`` returned.
    """

    def __init__(
        self,
        provisions: list[Provision],
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

    # ---- graph helpers ------------------------------------------------
    def _is_citeable(self, node_id: str) -> bool:
        node = self.graph.get_node(node_id)
        return node is not None and node.type in PROVISION_NODE_TYPES

    def _one_hop(self, node_id: str) -> list[tuple[str, float]]:
        """(neighbour_id, relation_weight) for a single hop out of ``node_id``.

        All these relations land on provision-like nodes, so the propagation
        frontier stays within the citeable subgraph."""
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

    # ---- retrieval ----------------------------------------------------
    def search(self, query: str, k: int) -> list[str]:
        return [pid for pid, _ in self.search_scored(query, k)]

    def search_scored(self, query: str, k: int) -> list[tuple[str, float]]:
        seeds = self.seeder.search_scored(query, self.seed_k)
        if not seeds or seeds[0][1] < self.min_seed_score:
            return []  # abstain: nothing retrieved, or best seed too weak (out-of-scope)

        scores: dict[str, float] = {}

        def add(node_id: str, value: float) -> None:
            if value > 0 and self._is_citeable(node_id):
                scores[node_id] = scores.get(node_id, 0.0) + value

        # hop 0 -- the seeds themselves
        for eid, s in seeds:
            add(eid, s)

        # hops 1..max_hops -- propagate & accumulate along structural edges
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


class GraphRAGBaseline(Baseline):
    """§8 baseline wrapping :class:`GraphExpansionRetriever`."""

    def __init__(
        self,
        provisions: list[Provision],
        graph: KnowledgeGraph,
        *,
        k: int = 5,
        seed_k: int = 10,
        weights: ExpansionWeights | None = None,
        max_hops: int = 1,
        min_seed_score: float = 0.0,
        seeder: Retriever | None = None,
        seeder_name: str = "tfidf",
    ) -> None:
        self.k = k
        self.retriever = GraphExpansionRetriever(
            provisions,
            graph,
            seed_k=seed_k,
            weights=weights,
            max_hops=max_hops,
            min_seed_score=min_seed_score,
            retriever=seeder,
        )
        abstain = f",abstain>={min_seed_score}" if min_seed_score else ""
        self.name = f"graph-expansion({seeder_name},seed={seed_k},hops={max_hops}{abstain})"

    def predict(self, item: dict) -> list[str]:
        return self.retriever.search(question_text(item), self.k)
