"""R347 — hybrid-RAG KG supplementation of the Cohere rerank pool.

R340 proved the cross-encoder rerank FIRES but measured it as a wash inside
noise (UNDERPOWERED at n=60, +1.0s latency): the permutation-only contract
re-orders a keyword-picked set, so it can never PROMOTE a genuinely
cross-referenced provision the keyword map never saw. R347 makes the rerank
hybrid: under ``REGENOLD_RERANK_KG_CANDIDATES`` (DEFAULT OFF — the A/B
decides) the parse-level rerank ranks the keyword entities TOGETHER with
their 1-hop CROSS_REFERENCES neighbours from the KG taxonomy, and feeds the
classifier's own labels (intent / risk tier / dimension) into the rerank
QUERY so the cross-encoder discriminates on domain terms.

The load-bearing invariants pinned here:

* ``rerank_query_context`` is deterministic, lowercase, and empty when the
  parse has no labels — the bare question stands unchanged in that case;
* ``build_kg_candidate_pool`` is a SUPERSET of its input (a permutation can
  reorder but never lose an entity), deduplicated, capped at ``max_extra``,
  honours the embedded-graph backend when selected and falls back to the
  canonical ``kb_xrefs.cross_refs`` adjacency otherwise, and NEVER raises;
* ``rerank_pool`` exposes an explicit ok-bit so a caller that EXPANDED the
  pool adopts the expansion only on real cross-encoder success (an outage
  never leaks neighbours into the reference set), while the historical
  ``rerank_references`` wrapper keeps the permutation guarantee;
* the parse-level wiring feeds the KG-expanded pool (and the classifier
  labels) into the cross-encoder only when BOTH gates are on — gate-off is
  byte-identical to the R340 behaviour by construction.
"""

from __future__ import annotations

import pytest

from app.engines import cohere_rerank as CR


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """No test here may make a live call."""

    def _boom(*a, **k):  # pragma: no cover
        raise AssertionError("live rerank call attempted in a unit test")

    monkeypatch.setattr(CR, "_get_client", _boom)
    yield


# ---------------------------------------------------------------------------
# rerank_query_context
# ---------------------------------------------------------------------------


def test_query_context_composition(monkeypatch):
    ctx = CR.rerank_query_context(
        intent="PROHIBITED_PRACTICE",
        risk_context="High",
        dimension_hint="obligation_check",
    )
    assert "risk: high" in ctx
    assert "intent: prohibited practice" in ctx
    assert "focus: obligation check" in ctx
    assert ctx.count("; ") == 2


def test_query_context_empty_when_no_labels():
    assert CR.rerank_query_context() == ""
    assert CR.rerank_query_context(intent="") == ""
    assert CR.rerank_query_context(risk_context=None) == ""


# ---------------------------------------------------------------------------
# build_kg_candidate_pool
# ---------------------------------------------------------------------------


def test_pool_is_superset_deduped_and_capped(monkeypatch):
    from app.graph import embedded_graph

    monkeypatch.setattr(embedded_graph, "embedded_backend_selected", lambda: False)
    from app.data import kb_xrefs

    monkeypatch.setattr(kb_xrefs, "cross_refs", lambda ref, limit=3: [])
    base = ["Art. 6", "Art. 50"]
    out = CR.build_kg_candidate_pool(base, max_extra=8, per_ref=3)
    assert sorted(out) == sorted(base)  # empty adjacency -> pool == input


def test_pool_uses_embedded_graph_when_selected(monkeypatch):
    class _FakeGraph:
        enabled = True

        def neighbors(self, ref, *, hops=1):  # noqa: ARG002
            return {"Art. 6": ["Art. 5", "Art. 7"], "Art. 50": ["Art. 49"]}[ref]

    from app.graph import embedded_graph

    monkeypatch.setattr(embedded_graph, "embedded_backend_selected", lambda: True)
    monkeypatch.setattr(embedded_graph, "get_embedded_graph", lambda: _FakeGraph())
    base = ["Art. 6"]
    out = CR.build_kg_candidate_pool(base, max_extra=8, per_ref=3)
    assert set(out) == {"Art. 6", "Art. 5", "Art. 7"}
    # Dedup: a neighbour that already IS an anchor must not be appended twice.
    base2 = ["Art. 6", "Art. 7"]
    out2 = CR.build_kg_candidate_pool(base2, max_extra=8, per_ref=3)
    assert out2.count("Art. 7") == 1
    assert len(out2) == len(set(out2))


def test_pool_falls_back_to_kb_xrefs(monkeypatch):
    from app.data import kb_xrefs
    from app.graph import embedded_graph

    monkeypatch.setattr(embedded_graph, "embedded_backend_selected", lambda: False)
    monkeypatch.setattr(
        kb_xrefs,
        "cross_refs",
        lambda ref, limit=3: ("Art. 5",) if ref == "Art. 6" else (),
    )
    out = CR.build_kg_candidate_pool(["Art. 6"])
    assert set(out) == {"Art. 6", "Art. 5"}


def test_pool_caps_extra_neighbours(monkeypatch):
    class _FakeGraph:
        enabled = True

        def neighbors(self, ref, *, hops=1):  # noqa: ARG002
            return [f"Art. {i}" for i in range(100)]

    from app.graph import embedded_graph

    monkeypatch.setattr(embedded_graph, "embedded_backend_selected", lambda: True)
    monkeypatch.setattr(embedded_graph, "get_embedded_graph", lambda: _FakeGraph())
    # max_extra=5 → hop-1 budget 3, hop-2 budget 2 → the cap is exactly
    # 1 anchor + 5 extras, split across the hops.
    out = CR.build_kg_candidate_pool(["Art. 6"], max_extra=5, per_ref=3, hops=2)
    assert len(out) == 6  # 1 anchor + 5 extra


def test_pool_never_raises(monkeypatch):
    class _BoomGraph:
        enabled = True

        def neighbors(self, ref, *, hops=1):  # noqa: ARG002
            raise RuntimeError("kg down")

    from app.graph import embedded_graph

    monkeypatch.setattr(embedded_graph, "embedded_backend_selected", lambda: True)
    monkeypatch.setattr(embedded_graph, "get_embedded_graph", lambda: _BoomGraph())
    assert CR.build_kg_candidate_pool(["Art. 6"]) == ["Art. 6"]
    # And a malformed input never crashes either.
    assert CR.build_kg_candidate_pool(None) == []
    assert CR.build_kg_candidate_pool(["Art. 6", "Art. 6"]) == ["Art. 6", "Art. 6"]


# ---------------------------------------------------------------------------
# rerank_pool — the ok-bit
# ---------------------------------------------------------------------------


def test_pool_ok_false_when_gate_off(monkeypatch):
    monkeypatch.delenv("REGENOLD_COHERE_RERANK", raising=False)
    refs = ["Art. 6", "Art. 43"]
    out, ok = CR.rerank_pool("q", refs, text_for=lambda r: f"text of {r}")
    assert out == refs
    assert ok is False


def test_pool_ok_false_when_fewer_than_two(monkeypatch):
    monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")
    monkeypatch.setenv("COHERE_API_KEY", "x")
    out, ok = CR.rerank_pool("q", ["Art. 6"])
    assert out == ["Art. 6"]
    assert ok is False


def test_pool_ok_true_on_success_and_noop(monkeypatch):
    monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")
    monkeypatch.setenv("COHERE_API_KEY", "x")
    refs = ["Art. 6", "Art. 43"]
    monkeypatch.setattr(
        CR, "rerank_documents", lambda q, d, top_n=None: [(i, 1.0) for i in range(len(d))]
    )
    out, ok = CR.rerank_pool("q", refs, text_for=lambda r: f"text of {r}")
    assert out == refs  # successful noop — the order equals the input order
    assert ok is True


def test_pool_ok_false_on_api_failure(monkeypatch):
    monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")
    monkeypatch.setenv("COHERE_API_KEY", "x")

    def _fail(q, d, top_n=None):  # noqa: ARG001
        return None

    monkeypatch.setattr(CR, "rerank_documents", _fail)
    refs = ["Art. 6", "Art. 43"]
    out, ok = CR.rerank_pool("q", refs, text_for=lambda r: f"text of {r}")
    assert out == refs
    assert ok is False


def test_pool_passes_query_context_into_query(monkeypatch):
    monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")
    monkeypatch.setenv("COHERE_API_KEY", "x")
    seen: dict = {}

    def _capture(q, d, top_n=None):  # noqa: ARG001
        seen["q"] = q
        return [(0, 1.0), (1, 0.9)]

    monkeypatch.setattr(CR, "rerank_documents", _capture)
    CR.rerank_pool(
        "What does the law require?",
        ["Art. 6", "Art. 43"],
        query_context="risk: high; intent: obligation check",
        text_for=lambda r: f"text of {r}",
    )
    assert "risk: high" in seen["q"]
    assert "intent: obligation check" in seen["q"]
    assert "What does the law require?" in seen["q"]


def test_wrapper_keeps_permutation_guarantee(monkeypatch):
    """The historical signature still returns exactly a permutation."""
    monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")
    monkeypatch.setenv("COHERE_API_KEY", "x")
    refs = ["Art. 6", "Art. 43", "Annex I"]
    monkeypatch.setattr(
        CR,
        "rerank_documents",
        lambda q, d, top_n=None: [(i, 1.0) for i in range(len(d) - 1, -1, -1)],
    )
    out = CR.rerank_references("q", refs, text_for=lambda r: f"text of {r}")
    assert sorted(out) == sorted(refs)
    assert out != refs


# ---------------------------------------------------------------------------
# parse-level wiring — the KG-expanded pool reaches the cross-encoder
# ---------------------------------------------------------------------------


def test_parse_feeds_kg_pool_and_context_when_gates_on(monkeypatch):
    """Both gates on → the cross-encoder sees the expanded pool + labels."""
    monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")
    monkeypatch.setenv("COHERE_API_KEY", "x")
    monkeypatch.setenv("REGENOLD_RERANK_KG_CANDIDATES", "1")
    captured: dict = {}

    def _fake_pool(references, **kw):  # noqa: ARG002
        return list(references) + ["Art. 5"]

    def _fake_enabled():
        return True

    def _fake_kg_enabled():
        return True

    def _fake_rerank_pool(question, pool, **kw):
        captured["pool"] = list(pool)
        captured["ctx"] = kw.get("query_context", "")
        return pool, True

    # R348 — the wiring tries the reason-aware builder FIRST; make it return
    # nothing so the plain-pool fallback (the R347 path) runs and its pool
    # reaches the reranker.
    monkeypatch.setattr(CR, "build_kg_candidate_pool_with_reasons", lambda refs, **kw: [])
    monkeypatch.setattr(CR, "build_kg_candidate_pool", _fake_pool)
    monkeypatch.setattr(CR, "rerank_enabled", _fake_enabled)
    monkeypatch.setattr(CR, "rerank_kg_candidates_enabled", _fake_kg_enabled)
    monkeypatch.setattr(CR, "rerank_pool", _fake_rerank_pool)

    from app.engines._graph_rag_impl import _deterministic_parse

    # Explicit article mentions → keyword-map entities, NOT the BM25 fallback
    # (which would skip the R347 block by the ``not _bm25_fallback_used`` guard).
    q = _deterministic_parse(
        "What does Article 9 and Article 10 require for high risk AI?"
    )
    assert "Art. 5" in captured["pool"]  # the KG neighbour reached the reranker
    assert any(a in captured["pool"] for a in q.entities)
    assert "risk: high" in captured["ctx"]


# ---------------------------------------------------------------------------
# R348 — semantic edge reasons + 2-hop depth
# ---------------------------------------------------------------------------


def test_hops_env_defaults_to_one_and_clamps(monkeypatch):
    monkeypatch.delenv("REGENOLD_RERANK_KG_HOPS", raising=False)
    assert CR.rerank_kg_hops() == 1
    monkeypatch.setenv("REGENOLD_RERANK_KG_HOPS", "2")
    assert CR.rerank_kg_hops() == 2
    monkeypatch.setenv("REGENOLD_RERANK_KG_HOPS", "9")
    assert CR.rerank_kg_hops() == 2  # clamped, never 9
    monkeypatch.setenv("REGENOLD_RERANK_KG_HOPS", "junk")
    assert CR.rerank_kg_hops() == 1  # malformed -> safe default


def test_two_hop_budget_split(monkeypatch):
    """Hop-2 must not starve hop-1: budget splits ~2:1."""
    from app.graph import embedded_graph

    class _FakeGraph:
        enabled = True

        def neighbors(self, ref, *, hops=1):  # noqa: ARG002
            if ref == "Art. 6":
                return ["Art. 5", "Art. 7"]  # hop-1
            if ref in ("Art. 5", "Art. 7"):
                return ["Art. 13", "Art. 14"]  # hop-2
            return []

    monkeypatch.setattr(embedded_graph, "embedded_backend_selected", lambda: True)
    monkeypatch.setattr(embedded_graph, "get_embedded_graph", lambda: _FakeGraph())
    # 1-hop: only the direct neighbours, even though 2 more exist deeper.
    one = CR.build_kg_candidate_pool(["Art. 6"], max_extra=8, hops=1)
    assert set(one) == {"Art. 6", "Art. 5", "Art. 7"}
    # 2-hop: deeper neighbours appear, but capped by the hop-2 budget.
    two = CR.build_kg_candidate_pool(["Art. 6"], max_extra=6, hops=2)
    assert set(two) == {"Art. 6", "Art. 5", "Art. 7", "Art. 13", "Art. 14"}
    # max_extra=3: hop-1 gets budget 2 (Art. 5, Art. 7), hop-2 gets budget 1
    # (Art. 13) — 3 extras total, the direct neighbours outnumber the deeper ones.
    three = CR.build_kg_candidate_pool(["Art. 6"], max_extra=3, hops=2)
    assert three[:2] == ["Art. 6", "Art. 5"]
    assert len(three) == 4  # 1 anchor + 3 extras (2 hop-1, 1 hop-2)


def test_pool_with_reasons_superset_and_reasons(monkeypatch):
    from app.data import kb_xrefs

    def _with_reason(ref, *, limit=5):  # noqa: ARG002
        return {
            "Art. 6": (("Art. 13", "deployer reads provider's transparency schema"),),
            "Art. 50": (),
        }[ref]

    monkeypatch.setattr(kb_xrefs, "cross_refs_with_reason", _with_reason)
    pairs = CR.build_kg_candidate_pool_with_reasons(["Art. 6", "Art. 50"])
    assert pairs == [("Art. 13", "deployer reads provider's transparency schema")]


def test_pool_with_reasons_never_raises(monkeypatch):
    from app.data import kb_xrefs

    def _boom(*a, **k):  # pragma: no cover
        raise RuntimeError("semantic layer down")

    monkeypatch.setattr(kb_xrefs, "cross_refs_with_reason", _boom)
    assert CR.build_kg_candidate_pool_with_reasons(["Art. 6"]) == []
    assert CR.build_kg_candidate_pool_with_reasons(None) == []


def test_rerank_pool_annotates_docs_with_reasons(monkeypatch):
    monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")
    monkeypatch.setenv("COHERE_API_KEY", "x")
    seen: dict = {}

    def _capture(q, d, top_n=None):  # noqa: ARG001
        seen["docs"] = list(d)
        return [(0, 1.0), (1, 0.9)]

    monkeypatch.setattr(CR, "rerank_documents", _capture)
    CR.rerank_pool(
        "q",
        ["Art. 6", "Art. 13"],
        doc_reasons={"Art. 13": "deployer reads provider's transparency schema"},
        text_for=lambda r: f"text of {r}",
    )
    assert "text of Art. 6" in seen["docs"][0]
    assert "deployer reads provider's transparency schema" in seen["docs"][1]
    assert seen["docs"][1].startswith("text of Art. 13")


def test_parse_feeds_reasons_and_anchors_when_kg_on(monkeypatch):
    """KG gate on → the pool is anchors + reason-annotated neighbours."""
    monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")
    monkeypatch.setenv("COHERE_API_KEY", "x")
    monkeypatch.setenv("REGENOLD_RERANK_KG_CANDIDATES", "1")
    captured: dict = {}

    def _fake_reasons(refs, **kw):  # noqa: ARG002
        return [("Art. 5", "prohibited practices are defined first")]

    def _fake_rerank_pool(question, pool, **kw):  # noqa: ARG002
        captured["pool"] = list(pool)
        captured["reasons"] = kw.get("doc_reasons")
        return pool, True

    monkeypatch.setattr(CR, "build_kg_candidate_pool_with_reasons", _fake_reasons)
    monkeypatch.setattr(CR, "rerank_pool", _fake_rerank_pool)

    from app.engines._graph_rag_impl import _deterministic_parse

    q = _deterministic_parse(
        "What does Article 9 and Article 10 require for high risk AI?"
    )
    assert captured["pool"][: len(q.entities)] == list(q.entities)  # anchors first
    assert "Art. 5" in captured["pool"]  # neighbour appended
    assert captured["reasons"] == {"Art. 5": "prohibited practices are defined first"}


def test_parse_reason_builder_failure_falls_back_to_plain_pool(monkeypatch):
    """Reasons unavailable → plain KG pool (anchors + neighbours, no reasons)."""
    monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")
    monkeypatch.setenv("COHERE_API_KEY", "x")
    monkeypatch.setenv("REGENOLD_RERANK_KG_CANDIDATES", "1")
    captured: dict = {}

    def _fake_reasons(refs, **kw):  # noqa: ARG002
        return []  # semantic layer gave nothing

    def _fake_rerank_pool(question, pool, **kw):  # noqa: ARG002
        captured["pool"] = list(pool)
        captured["reasons"] = kw.get("doc_reasons")
        return pool, True

    monkeypatch.setattr(CR, "build_kg_candidate_pool_with_reasons", _fake_reasons)
    monkeypatch.setattr(CR, "build_kg_candidate_pool", lambda refs, **kw: list(refs))
    monkeypatch.setattr(CR, "rerank_pool", _fake_rerank_pool)

    from app.engines._graph_rag_impl import _deterministic_parse

    q = _deterministic_parse(
        "What does Article 9 and Article 10 require for high risk AI?"
    )
    assert captured["pool"] == list(q.entities)  # plain pool, no neighbours
    assert captured["reasons"] is None


def test_parse_kg_off_is_pure_r340_permutation(monkeypatch):
    """KG gate off → the pool handed to the reranker is exactly the entities."""
    monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")
    monkeypatch.setenv("COHERE_API_KEY", "x")
    monkeypatch.setenv("REGENOLD_RERANK_KG_CANDIDATES", "0")
    captured: dict = {}

    def _fake_rerank_pool(question, pool, **kw):  # noqa: ARG002
        captured["pool"] = list(pool)
        return pool, True

    monkeypatch.setattr(CR, "rerank_pool", _fake_rerank_pool)
    monkeypatch.setattr(CR, "rerank_query_context", lambda **k: "")

    from app.engines._graph_rag_impl import _deterministic_parse

    q = _deterministic_parse("What does Article 9 require for high risk AI?")
    assert captured["pool"] == q.entities  # no KG supplementation
