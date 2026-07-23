"""Deterministic structural abstention gate for the EU AI Act GraphRAG retrieval system.

This module probes whether *graph topology* can distinguish in-scope questions
from out-of-scope ones, given that no lexical/latent signal (TF-IDF cosine, LSA
cosine, idf coverage) has succeeded in separating the benchmark's negative controls
from answerable items.

Hypothesis: for an answerable question, the top-k lexical seeds tend to cluster
structurally — they share a parent article, or are linked via CROSS_REFERENCES_INTERNAL.
For an out-of-scope question, seeds scatter across unrelated articles.  Whether this
hypothesis holds is an open empirical question; the module exists to measure it honestly
and does not assume a particular outcome.

Cohesion definition
-------------------
Given N seeds (provision_ids), build clusters via union-find where two seeds are in
the same cluster iff they share the same **article-root key** (the first segment of
their eid, e.g. ``art_6`` for ``art_6__para_2__point_a``) OR they are within 1 hop
of each other via CROSS_REFERENCES_INTERNAL (either direction).

    cohesion = size(largest_cluster) / N

Secondary: ``article_dispersion = distinct_article_roots / N`` (lower = more cohesive).

``min_cohesion=0.0`` is the identity passthrough — ``StructuralAbstentionBaseline``
behaves exactly as its wrapped base when the threshold is 0.
"""

from __future__ import annotations

__all__ = [
    "article_root_key",
    "structural_cohesion",
    "StructuralAbstentionBaseline",
]

from dataclasses import dataclass, field

from ..baselines.base import Baseline, question_text
from ..baselines.retrieval import Retriever, TfidfRetriever
from ..graph.model import KnowledgeGraph
from ..graph.schema import EdgeType
from ..ids import ProvisionId, ProvisionIdError
from ..models import Provision


# ---------------------------------------------------------------------------
# Article-root key
# ---------------------------------------------------------------------------

def article_root_key(provision_id: str) -> str:
    """Return the article-root key for a provision_id.

    The root key is the first ``kind_value`` segment of the eid, which identifies
    the top-level structural node (e.g. ``art_6``, ``annex_III``, ``recital_5``).
    Falls back to the full provision_id if parsing fails (silently degrades rather
    than crashing — an unparseable id gets its own unique cluster bucket).
    """
    try:
        pid = ProvisionId.from_eid(provision_id)
        root_seg = pid.segments[0]
        return f"{root_seg.kind}_{root_seg.value}"
    except ProvisionIdError:
        return provision_id


# ---------------------------------------------------------------------------
# Union-Find (path compression, deterministic)
# ---------------------------------------------------------------------------

class _UnionFind:
    def __init__(self, items: list[str]) -> None:
        self._parent: dict[str, str] = {x: x for x in items}

    def find(self, x: str) -> str:
        while self._parent[x] != x:
            # path compression (two-step)
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            # deterministic tie-break: smaller string becomes root
            if ra < rb:
                self._parent[rb] = ra
            else:
                self._parent[ra] = rb

    def cluster_sizes(self) -> dict[str, int]:
        """Return {root: count} for all clusters."""
        counts: dict[str, int] = {}
        for x in self._parent:
            root = self.find(x)
            counts[root] = counts.get(root, 0) + 1
        return counts


# ---------------------------------------------------------------------------
# Core cohesion function
# ---------------------------------------------------------------------------

@dataclass
class CohesionResult:
    cohesion: float
    article_dispersion: float
    largest_cluster_size: int
    n_seeds: int
    distinct_article_roots: int


def structural_cohesion(
    seed_ids: list[str],
    graph: KnowledgeGraph,
) -> CohesionResult:
    """Compute structural cohesion over a list of seed provision_ids.

    Two seeds are in the same cluster iff:
    - They share the same article-root key (e.g. both under ``art_6``), OR
    - They are within 1 hop of each other via CROSS_REFERENCES_INTERNAL (either
      direction).

    Returns a :class:`CohesionResult` with ``cohesion`` in [0,1] and
    ``article_dispersion`` in [0,1].  Both are defined as 0 when N=0.
    """
    # Deduplicate while preserving order for determinism.
    # n and all ratios are computed over unique seeds so duplicate ids don't
    # inflate the denominator and produce sub-1 cohesion for an all-same list.
    seen: set[str] = set()
    seeds: list[str] = []
    for s in seed_ids:
        if s not in seen:
            seen.add(s)
            seeds.append(s)

    n = len(seeds)
    if n == 0:
        return CohesionResult(
            cohesion=0.0,
            article_dispersion=0.0,
            largest_cluster_size=0,
            n_seeds=0,
            distinct_article_roots=0,
        )

    uf = _UnionFind(seeds)
    seed_set = set(seeds)

    # --- criterion 1: shared article-root ---
    root_to_seeds: dict[str, list[str]] = {}
    for s in seeds:
        root = article_root_key(s)
        root_to_seeds.setdefault(root, []).append(s)

    for same_root_group in root_to_seeds.values():
        if len(same_root_group) > 1:
            first = same_root_group[0]
            for other in same_root_group[1:]:
                uf.union(first, other)

    # --- criterion 2: 1-hop CROSS_REFERENCES_INTERNAL (either direction) ---
    for s in seeds:
        # outgoing: s -> target
        for target in graph.neighbors(s, EdgeType.CROSS_REFERENCES_INTERNAL):
            if target in seed_set:
                uf.union(s, target)
        # incoming: source -> s
        for source in graph.neighbors(s, EdgeType.CROSS_REFERENCES_INTERNAL, incoming=True):
            if source in seed_set:
                uf.union(s, source)

    cluster_sizes = uf.cluster_sizes()
    largest = max(cluster_sizes.values()) if cluster_sizes else 0
    distinct_roots = len(root_to_seeds)

    return CohesionResult(
        cohesion=largest / n,
        article_dispersion=distinct_roots / n,
        largest_cluster_size=largest,
        n_seeds=n,
        distinct_article_roots=distinct_roots,
    )


# ---------------------------------------------------------------------------
# Baseline wrapper
# ---------------------------------------------------------------------------

class StructuralAbstentionBaseline(Baseline):
    """Wraps any Baseline and optionally abstains based on seed structural cohesion.

    When ``min_cohesion=0.0`` (the default) the gate never fires — output is
    identical to the wrapped base baseline.  Set ``min_cohesion > 0.0`` to
    abstain (return ``[]``) whenever the top-N seeds are too structurally scattered.

    The orchestrator can call :meth:`cohesion_for` on any item to extract the raw
    cohesion score without affecting prediction, enabling offline threshold sweeps.
    """

    name: str = "structural_abstain"

    def __init__(
        self,
        base: Baseline,
        provisions: list[Provision],
        graph: KnowledgeGraph,
        retriever: Retriever | None = None,
        seed_n: int = 10,
        min_cohesion: float = 0.0,
    ) -> None:
        self._base = base
        self._graph = graph
        self._retriever: Retriever = retriever if retriever is not None else TfidfRetriever(provisions)
        self._seed_n = seed_n
        self._min_cohesion = min_cohesion

    def _seed_ids(self, item: dict) -> list[str]:
        query = question_text(item)
        return [pid for pid, _ in self._retriever.search_scored(query, self._seed_n)]

    def cohesion_for(self, item: dict) -> float:
        """Return the raw cohesion score for *item* without making a prediction.

        Safe to call repeatedly — purely deterministic read over the retriever and
        graph; no side effects.
        """
        seeds = self._seed_ids(item)
        return structural_cohesion(seeds, self._graph).cohesion

    def predict(self, item: dict) -> list[str]:
        """Return base predictions, or ``[]`` if structural cohesion is below threshold.

        ``min_cohesion=0.0`` → never abstains (pure passthrough).
        """
        if self._min_cohesion <= 0.0:
            return list(self._base.predict(item))
        seeds = self._seed_ids(item)
        result = structural_cohesion(seeds, self._graph)
        if result.cohesion < self._min_cohesion:
            return []
        return list(self._base.predict(item))
