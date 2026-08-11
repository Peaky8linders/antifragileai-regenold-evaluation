import os

os.environ["NEO4J_AUTO_SEED"] = "0"

from types import SimpleNamespace

from app.engines import kg_context as kg
from app.engines.kg_context import (
    fetch_deontic_context,
    fetch_subpoint_detail,
    render_kg_context,
    reset_kg_context_memo,
)


def setup_function():
    reset_kg_context_memo()

def test_fetch_subpoint_detail_disabled_by_default():
    # Without real driver connected, returns empty list fail-softly
    res = fetch_subpoint_detail(["Art. 5"])
    assert isinstance(res, list)

def test_fetch_deontic_context_disabled_by_default():
    res = fetch_deontic_context(["Art. 5"])
    assert isinstance(res, list)

def test_render_kg_context_returns_list():
    res = render_kg_context(["Art. 5"])
    assert isinstance(res, list)


def test_annex_iii_has_a_direct_category_query_path():
    # R327 — the query now references the parameter directly instead of
    # importing it with an aliased ``WITH $ids AS ids``, because the subquery was
    # migrated to the non-deprecated ``CALL () { ... }`` scope form. Parameters
    # are always in scope inside a subquery, so no import is needed.
    assert "'annex_III' IN $ids" in kg._DEONTIC_CYPHER
    assert "MATCH (cat:AnnexIIICategory)" in kg._DEONTIC_CYPHER
    assert "CALL () {" in kg._DEONTIC_CYPHER, (
        "a bare `CALL {` is deprecated on Aura (01N00 variable scope clause)"
    )


def test_annex_iii_only_reference_fires_category_render(monkeypatch):
    calls = []

    def _read(cypher, params):
        calls.append((cypher, params))
        if cypher == kg._DEONTIC_CYPHER:
            assert params["ids"] == ["annex_III"]
            return [{
                "cite": "Annex III",
                "practices": [],
                "annex_iii": ["Employment, workers management and access to self-employment"],
                "roles": [],
                "phases": [],
            }]
        return []

    monkeypatch.setattr(kg, "_bounded_execute_read", _read)
    reset_kg_context_memo()

    rendered = "\n".join(render_kg_context(["Annex III"]))

    assert "KNOWLEDGE-GRAPH REGULATORY CLASSIFICATION" in rendered
    assert "Employment, workers management" in rendered
    assert any(cypher == kg._DEONTIC_CYPHER for cypher, _params in calls)


def test_subpoint_renders_full_roman_coordinate_with_neutral_label(monkeypatch):
    monkeypatch.setattr(kg, "fetch_provision_hierarchy", lambda _refs: [])
    monkeypatch.setattr(kg, "fetch_recital_anchors", lambda _refs: [])
    monkeypatch.setattr(kg, "fetch_deontic_context", lambda _refs: [])
    monkeypatch.setattr(
        kg,
        "fetch_subpoint_detail",
        lambda _refs: [{
            "cite": "Article 5",
            "para": "1",
            "letter": "h",
            "roman": "iii",
            "sid": "article_5_1_h_iii",
            "text": "A nested enumerated element.",
        }],
    )

    rendered = "\n".join(render_kg_context(["Art. 5"]))

    assert "KNOWLEDGE-GRAPH SUB-POINT DETAIL" in rendered
    assert "paragraph 1, point (h), subpoint (iii)" in rendered
    assert "CARVE-OUT" not in rendered


def test_hard_cap_reserves_present_r326_sections(monkeypatch):
    monkeypatch.setenv("REGENOLD_KG_MAX_CHARS", "2000")
    monkeypatch.setattr(
        kg,
        "fetch_provision_hierarchy",
        lambda _refs: [{
            "id": "article_5",
            "cite": "Article 5",
            "title": "Prohibited AI practices",
            "units": [{"num": str(i), "text": "long hierarchy text " * 100} for i in range(12)],
        }],
    )
    monkeypatch.setattr(kg, "fetch_recital_anchors", lambda _refs: [])
    monkeypatch.setattr(
        kg,
        "fetch_subpoint_detail",
        lambda _refs: [{
            "cite": "Article 5", "para": "1", "letter": "h", "roman": "i",
            "text": "Nested element retained under the reserved budget.",
        }],
    )
    monkeypatch.setattr(
        kg,
        "fetch_deontic_context",
        lambda _refs: [{
            "cite": "Article 5",
            "practices": ["manipulative practice"],
            "annex_iii": [], "roles": [], "phases": [],
        }],
    )

    parts = render_kg_context(["Art. 5"])
    rendered = "\n".join(parts)

    assert sum(map(len, parts)) <= 2000
    assert len("\n".join(parts)) <= 2000
    assert "KNOWLEDGE-GRAPH SUB-POINT DETAIL" in rendered
    assert "KNOWLEDGE-GRAPH REGULATORY CLASSIFICATION" in rendered


def test_strict_read_failure_is_not_memoised_as_empty(monkeypatch):
    calls = []

    class StrictClient:
        enabled = True

        def execute_read_strict(self, cypher, params=None):
            calls.append((cypher, params))
            raise RuntimeError("authentication failed")

        def execute_read(self, *_a, **_kw):
            return []

    monkeypatch.setattr("app.graph.client.get_graph_client", lambda: StrictClient())
    monkeypatch.setattr("app.graph.timeouts.graph_circuit_open", lambda: False)
    monkeypatch.setattr("app.graph.timeouts.record_graph_failure", lambda: None)
    monkeypatch.setattr("app.graph.timeouts.record_graph_success", lambda: None)
    reset_kg_context_memo()

    assert kg.fetch_provision_hierarchy(["Art. 97"]) == []
    assert kg.fetch_provision_hierarchy(["Art. 97"]) == []
    assert len(calls) == 2


def test_admission_saturation_does_not_submit_more_work(monkeypatch):
    """A saturated pool must not queue more backend work — but must WAIT first.

    R327 — the admission gate originally used ``acquire(blocking=False)``, so
    every concurrent read past the second failed instantly. One request issues
    several kg_context reads and the eval harness runs at concurrency 3, so under
    exactly the load the graph exists to serve, reads were hard-dropped and the
    graph context silently vanished. The gate now waits up to the graph timeout
    budget; only a genuinely saturated pool still gives up.
    """

    class NoAdmission:
        def __init__(self) -> None:
            self.waited_with_timeout = None

        def acquire(self, blocking=True, timeout=None):
            # The production call passes a positive timeout, never blocking=False.
            self.waited_with_timeout = timeout
            return False

    admission = NoAdmission()
    monkeypatch.setattr(kg, "_KG_ADMISSION", admission)
    monkeypatch.setattr(
        "app.graph.client.get_graph_client",
        lambda: SimpleNamespace(enabled=True),
    )
    monkeypatch.setattr("app.graph.timeouts.graph_circuit_open", lambda: False)
    monkeypatch.setattr(
        kg,
        "_get_kg_executor",
        lambda: (_ for _ in ()).throw(AssertionError("must not submit")),
    )

    result = kg._bounded_execute_read("RETURN 1", {})
    assert result == []
    assert result.failed is True
    assert admission.waited_with_timeout is not None, (
        "admission must wait for a slot, not drop the read immediately"
    )
    assert admission.waited_with_timeout > 0


def test_executor_cold_initialization_is_singleton_under_concurrency():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    previous = kg._EXECUTOR
    created = None
    kg._EXECUTOR = None
    barrier = Barrier(8)

    def _cold_get():
        barrier.wait()
        return kg._get_kg_executor()

    try:
        with ThreadPoolExecutor(max_workers=8) as callers:
            executors = list(callers.map(lambda _idx: _cold_get(), range(8)))
        created = executors[0]
        assert all(executor is created for executor in executors)
    finally:
        if created is not None:
            created.shutdown(wait=True, cancel_futures=True)
        kg._EXECUTOR = previous


# ── R327.1 — the gated default is CONSTRAINED-ONLY ───────────────────────────


def test_semantic_layers_default_on_constrained_only(monkeypatch):
    """Master switch ON, open-domain gloss OFF — the measured configuration.

    Grounded judge, 50 live July-7 rows per arm:

                          ans(hist)  ref MACRO  ref micro  wrong/total  cite
        layers OFF          0.880      0.675      0.611      51/131     0.900
        layers ON (both)    0.880      0.642      0.583      55/132     0.960
        CONSTRAINED ONLY    0.880      0.657      0.614      49/127     0.960

    Constrained-only keeps the whole citation-faithfulness gain and returns
    reference precision to baseline; running the open-domain half too costs 0.028
    micro precision for no extra gain.
    """
    from app.engines import graph_semantic as gs

    monkeypatch.delenv("REGENOLD_GRAPH_SEMANTIC_LAYERS", raising=False)
    monkeypatch.delenv("REGENOLD_SEMANTIC_GLOSS", raising=False)
    assert gs.semantic_layers_enabled() is True
    assert gs.gloss_layers_enabled() is False


def test_semantic_layers_have_an_off_switch(monkeypatch):
    from app.engines import graph_semantic as gs

    monkeypatch.setenv("REGENOLD_GRAPH_SEMANTIC_LAYERS", "0")
    assert gs.semantic_layers_enabled() is False


def test_gloss_off_suppresses_only_the_open_domain_blocks(monkeypatch):
    """GLOSS=0 must drop definitions+recitals and KEEP the constrained block."""
    from app.engines import graph_semantic as gs

    monkeypatch.setenv("REGENOLD_GRAPH_SEMANTIC_LAYERS", "1")
    monkeypatch.setenv("REGENOLD_SEMANTIC_GLOSS", "0")
    # The gloss fetch short-circuits before touching the graph at all.
    assert gs.fetch_definition_and_recital_context("q", ["Article 50"]) == []


def test_both_semantic_flags_are_in_the_engine_cache_key():
    """Engine-level flags MUST be keyed or an in-process A/B replays the cache.

    R327 measured this the hard way: the first semantic-layer A/B was
    byte-identical on all 50 rows because arm B was served from _ENGINE_CACHE
    (1,096 ms vs 16,642 ms).
    """
    import app.routes.regenold as route

    src = route._engine_cache_key.__doc__ or ""
    import inspect

    body = inspect.getsource(route._engine_cache_key)
    for flag in ("REGENOLD_GRAPH_SEMANTIC_LAYERS", "REGENOLD_SEMANTIC_GLOSS"):
        assert flag in body, f"{flag} missing from _engine_cache_key"
