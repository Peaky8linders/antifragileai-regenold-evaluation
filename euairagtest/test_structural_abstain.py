"""Tests for the structural abstention gate (structural_abstain.py).

Fixture strategy: tiny in-memory KnowledgeGraph built by hand, with a stub
Retriever that returns a deterministic fixed seed list, and a stub Baseline
that returns a fixed prediction.  This isolates the cohesion logic from any
real corpus data.
"""

from __future__ import annotations

from euaiact.baselines.base import Baseline
from euaiact.baselines.retrieval import Retriever
from euaiact.baselines.structural_abstain import (
    StructuralAbstentionBaseline,
    article_root_key,
    structural_cohesion,
)
from euaiact.graph.model import KnowledgeGraph
from euaiact.graph.schema import EdgeType, NodeType
from euaiact.models import Provision


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

def _provision(pid: str, text: str = "text") -> Provision:
    return Provision(provision_id=pid, chunk_type="paragraph", text=text)


def _make_graph_with_provisions(*pids: str) -> KnowledgeGraph:
    g = KnowledgeGraph()
    for pid in pids:
        g.add_node(pid, NodeType.PROVISION)
    return g


class _FixedRetriever(Retriever):
    """Returns a predetermined ordered list of provision_ids."""

    def __init__(self, seeds: list[str]) -> None:
        self._seeds = seeds

    def search(self, query: str, k: int) -> list[str]:
        return self._seeds[:k]

    def search_scored(self, query: str, k: int) -> list[tuple[str, float]]:
        return [(pid, 1.0 / (i + 1)) for i, pid in enumerate(self._seeds[:k])]


class _FixedBaseline(Baseline):
    name = "fixed"

    def __init__(self, predictions: list[str]) -> None:
        self._predictions = predictions

    def predict(self, item: dict) -> list[str]:
        return list(self._predictions)


_DUMMY_ITEM: dict = {"id": "q1", "question": "dummy question"}


# ---------------------------------------------------------------------------
# article_root_key
# ---------------------------------------------------------------------------

def test_article_root_key_deep_provision() -> None:
    assert article_root_key("art_6__para_2__point_a") == "art_6"


def test_article_root_key_top_level() -> None:
    assert article_root_key("art_6") == "art_6"


def test_article_root_key_annex() -> None:
    assert article_root_key("annex_III__point_4__point_a") == "annex_III"


def test_article_root_key_recital() -> None:
    assert article_root_key("recital_5") == "recital_5"


def test_article_root_key_unparseable_fallback() -> None:
    # An unparseable id should not raise — it returns itself as the bucket.
    val = article_root_key("totally_invalid__xyz__123__nope")
    assert val == "totally_invalid__xyz__123__nope"


# ---------------------------------------------------------------------------
# structural_cohesion — all seeds share one article root
# ---------------------------------------------------------------------------

def test_cohesion_same_article_root() -> None:
    """All seeds under art_6 → cohesion == 1.0."""
    seeds = [
        "art_6",
        "art_6__para_1",
        "art_6__para_2",
        "art_6__para_2__point_a",
    ]
    g = _make_graph_with_provisions(*seeds)
    r = structural_cohesion(seeds, g)
    assert r.cohesion == 1.0
    assert r.largest_cluster_size == 4
    assert r.n_seeds == 4
    assert r.distinct_article_roots == 1


# ---------------------------------------------------------------------------
# structural_cohesion — seeds scattered, no cross-refs
# ---------------------------------------------------------------------------

def test_cohesion_scattered_no_crossref() -> None:
    """Each seed is from a different article, no cross-refs → cohesion == 1/N."""
    seeds = ["art_1", "art_2", "art_3", "art_4"]
    g = _make_graph_with_provisions(*seeds)
    r = structural_cohesion(seeds, g)
    assert r.cohesion == 1.0 / 4  # largest cluster is size 1
    assert r.distinct_article_roots == 4
    assert r.article_dispersion == 1.0


# ---------------------------------------------------------------------------
# structural_cohesion — cross-refs link otherwise-separate articles
# ---------------------------------------------------------------------------

def test_cohesion_crossref_bridges_articles() -> None:
    """art_6 and art_9 are from different articles but cross-reference each other
    → they are in the same cluster, so cohesion should be > 1/N."""
    seeds = ["art_6", "art_9", "art_15", "art_22"]
    g = _make_graph_with_provisions(*seeds)
    # art_6 -> art_9 via CROSS_REFERENCES_INTERNAL
    g.add_edge(EdgeType.CROSS_REFERENCES_INTERNAL, "art_6", "art_9")
    r = structural_cohesion(seeds, g)
    # cluster {art_6, art_9} = size 2; others = size 1
    assert r.largest_cluster_size == 2
    assert r.cohesion == 2.0 / 4


def test_cohesion_crossref_incoming_direction() -> None:
    """Incoming cross-ref (target in seeds) must also cluster the pair."""
    seeds = ["art_10", "art_11"]
    g = _make_graph_with_provisions(*seeds)
    # art_11 references art_10; art_10 is the target — incoming from art_10's perspective
    g.add_edge(EdgeType.CROSS_REFERENCES_INTERNAL, "art_11", "art_10")
    r = structural_cohesion(seeds, g)
    assert r.cohesion == 1.0


# ---------------------------------------------------------------------------
# structural_cohesion — edge cases
# ---------------------------------------------------------------------------

def test_cohesion_empty_seeds() -> None:
    g = KnowledgeGraph()
    r = structural_cohesion([], g)
    assert r.cohesion == 0.0
    assert r.article_dispersion == 0.0
    assert r.n_seeds == 0


def test_cohesion_single_seed() -> None:
    seeds = ["art_6"]
    g = _make_graph_with_provisions(*seeds)
    r = structural_cohesion(seeds, g)
    assert r.cohesion == 1.0
    assert r.largest_cluster_size == 1


def test_cohesion_deduplicates_seeds() -> None:
    """Duplicate provision_ids in the seed list should be treated as N distinct items
    equal to the number of unique ids, not the raw list length."""
    seeds = ["art_6", "art_6", "art_6"]
    g = _make_graph_with_provisions("art_6")
    r = structural_cohesion(seeds, g)
    assert r.n_seeds == 1
    assert r.cohesion == 1.0


# ---------------------------------------------------------------------------
# StructuralAbstentionBaseline — no abstain when min_cohesion == 0.0
# ---------------------------------------------------------------------------

def test_min_cohesion_zero_never_abstains() -> None:
    """min_cohesion=0.0 must be a pure passthrough regardless of seed scatter."""
    # Seeds are from four different articles → very low cohesion
    seeds = ["art_1", "art_2", "art_3", "art_4"]
    provisions = [_provision(s) for s in seeds]
    g = _make_graph_with_provisions(*seeds)
    retriever = _FixedRetriever(seeds)
    expected = ["art_6__para_2", "art_9__para_1"]
    base = _FixedBaseline(expected)

    gate = StructuralAbstentionBaseline(
        base=base,
        provisions=provisions,
        graph=g,
        retriever=retriever,
        seed_n=4,
        min_cohesion=0.0,
    )
    result = gate.predict(_DUMMY_ITEM)
    assert result == expected


# ---------------------------------------------------------------------------
# StructuralAbstentionBaseline — abstains when cohesion below threshold
# ---------------------------------------------------------------------------

def test_abstains_when_cohesion_below_threshold() -> None:
    """With seeds from four separate articles and min_cohesion=0.5, must return []."""
    seeds = ["art_1", "art_2", "art_3", "art_4"]
    provisions = [_provision(s) for s in seeds]
    g = _make_graph_with_provisions(*seeds)
    retriever = _FixedRetriever(seeds)
    base = _FixedBaseline(["art_1"])

    gate = StructuralAbstentionBaseline(
        base=base,
        provisions=provisions,
        graph=g,
        retriever=retriever,
        seed_n=4,
        min_cohesion=0.5,  # cohesion is 0.25 → should abstain
    )
    assert gate.predict(_DUMMY_ITEM) == []


# ---------------------------------------------------------------------------
# StructuralAbstentionBaseline — does NOT abstain when cohesion at threshold
# ---------------------------------------------------------------------------

def test_does_not_abstain_when_cohesion_at_threshold() -> None:
    """Cohesion exactly equal to min_cohesion: should NOT abstain (< not <=)."""
    # 2 seeds from same article → cohesion 1.0
    seeds = ["art_6__para_1", "art_6__para_2"]
    provisions = [_provision(s) for s in seeds]
    g = _make_graph_with_provisions(*seeds)
    retriever = _FixedRetriever(seeds)
    expected = ["art_6__para_2"]
    base = _FixedBaseline(expected)

    gate = StructuralAbstentionBaseline(
        base=base,
        provisions=provisions,
        graph=g,
        retriever=retriever,
        seed_n=2,
        min_cohesion=1.0,  # cohesion == 1.0, not strictly less than threshold
    )
    assert gate.predict(_DUMMY_ITEM) == expected


def test_does_not_abstain_when_cohesion_above_threshold() -> None:
    """Cohesion above threshold → base predictions pass through."""
    seeds = ["art_6__para_1", "art_6__para_2"]
    provisions = [_provision(s) for s in seeds]
    g = _make_graph_with_provisions(*seeds)
    retriever = _FixedRetriever(seeds)
    expected = ["art_6__para_2"]
    base = _FixedBaseline(expected)

    gate = StructuralAbstentionBaseline(
        base=base,
        provisions=provisions,
        graph=g,
        retriever=retriever,
        seed_n=2,
        min_cohesion=0.5,  # cohesion == 1.0 > 0.5 → no abstain
    )
    assert gate.predict(_DUMMY_ITEM) == expected


# ---------------------------------------------------------------------------
# cohesion_for — returns expected fraction
# ---------------------------------------------------------------------------

def test_cohesion_for_returns_known_fraction() -> None:
    """cohesion_for must return the correct raw cohesion for a known seed set."""
    seeds = ["art_1", "art_2", "art_3", "art_4"]
    provisions = [_provision(s) for s in seeds]
    g = _make_graph_with_provisions(*seeds)
    retriever = _FixedRetriever(seeds)
    base = _FixedBaseline([])

    gate = StructuralAbstentionBaseline(
        base=base,
        provisions=provisions,
        graph=g,
        retriever=retriever,
        seed_n=4,
        min_cohesion=0.0,
    )
    score = gate.cohesion_for(_DUMMY_ITEM)
    assert score == 0.25  # each seed is isolated → largest cluster = 1 → 1/4


def test_cohesion_for_high_cohesion() -> None:
    seeds = ["art_6__para_1", "art_6__para_2", "art_6__para_3"]
    provisions = [_provision(s) for s in seeds]
    g = _make_graph_with_provisions(*seeds)
    retriever = _FixedRetriever(seeds)
    base = _FixedBaseline([])

    gate = StructuralAbstentionBaseline(
        base=base,
        provisions=provisions,
        graph=g,
        retriever=retriever,
        seed_n=3,
        min_cohesion=0.0,
    )
    assert gate.cohesion_for(_DUMMY_ITEM) == 1.0


# ---------------------------------------------------------------------------
# Determinism — same item twice yields same result
# ---------------------------------------------------------------------------

def test_determinism_predict() -> None:
    seeds = ["art_6", "art_9", "art_15"]
    provisions = [_provision(s) for s in seeds]
    g = _make_graph_with_provisions(*seeds)
    g.add_edge(EdgeType.CROSS_REFERENCES_INTERNAL, "art_6", "art_9")
    retriever = _FixedRetriever(seeds)
    base = _FixedBaseline(["art_6", "art_9"])

    gate = StructuralAbstentionBaseline(
        base=base,
        provisions=provisions,
        graph=g,
        retriever=retriever,
        seed_n=3,
        min_cohesion=0.5,
    )
    r1 = gate.predict(_DUMMY_ITEM)
    r2 = gate.predict(_DUMMY_ITEM)
    assert r1 == r2


def test_determinism_cohesion_for() -> None:
    seeds = ["art_1", "art_2", "art_3"]
    provisions = [_provision(s) for s in seeds]
    g = _make_graph_with_provisions(*seeds)
    retriever = _FixedRetriever(seeds)
    base = _FixedBaseline([])

    gate = StructuralAbstentionBaseline(
        base=base,
        provisions=provisions,
        graph=g,
        retriever=retriever,
        seed_n=3,
    )
    assert gate.cohesion_for(_DUMMY_ITEM) == gate.cohesion_for(_DUMMY_ITEM)


# ---------------------------------------------------------------------------
# Mixed cluster: some share root, one isolated — verify expected arithmetic
# ---------------------------------------------------------------------------

def test_partial_clustering_arithmetic() -> None:
    """3 seeds under art_6, 1 isolated under art_9, no cross-refs.
    Largest cluster = 3 → cohesion = 3/4 = 0.75."""
    seeds = ["art_6__para_1", "art_6__para_2", "art_6__para_3", "art_9__para_1"]
    provisions = [_provision(s) for s in seeds]
    g = _make_graph_with_provisions(*seeds)
    retriever = _FixedRetriever(seeds)
    base = _FixedBaseline([])

    gate = StructuralAbstentionBaseline(
        base=base,
        provisions=provisions,
        graph=g,
        retriever=retriever,
        seed_n=4,
        min_cohesion=0.0,
    )
    assert gate.cohesion_for(_DUMMY_ITEM) == 0.75
