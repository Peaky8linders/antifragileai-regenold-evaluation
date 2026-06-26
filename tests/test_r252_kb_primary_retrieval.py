"""R252 — KB-primary retrieval regression guards.

The live Neo4j PRIMARY retrieval (``obligations_for_risk_level``) is a blunt
risk-tier DUMP: for a topic / role / transparency question it returns the
ENTIRE high-risk obligation chain (Arts 9-15) regardless of the question's
actual subject, and because that result is non-empty the R99 empty-success
fallback never fires — so the wire ships the wrong cluster. Live proof:
"How should users be informed when interacting with AI systems?" (gold
Article 50) shipped [10, 11, 12] via ``retrieval_path=neo4j``.

R252 fix: when ``_kb_primary_retrieval_enabled()`` is True (default) AND the
graph is enabled, ``_retrieve_from_graph`` uses the in-memory KB path
(``_retrieve_from_kb`` — the byte-identical bench path) as PRIMARY and skips
the blunt Cypher dump entirely. The precision-safe additive 2-hop graph
expansion still fires INSIDE ``_retrieve_from_kb`` → ``top_articles_by_relevance``.

These tests pin:

1. the env-gate semantics (default ON; explicit falsy values OFF);
2. that a DISABLED graph client still takes the unchanged KB path
   (davidath byte-identity-by-construction — the bench has no Neo4j);
3. that an ENABLED graph client with the gate ON bypasses the Cypher dump
   and serves the KB context, un-polluted by the wrong-cluster dump;
4. that the gate OFF still enters the legacy Neo4j Cypher path;
5. that the engine cache key folds in ``REGENOLD_KB_PRIMARY_RETRIEVAL``.

The mock pattern mirrors ``test_graph_rag_bugfixes.py::TestGraphEmptyResultFallback``
(R99.1) — an ``enabled=True`` client whose ``execute_read`` returns a
controlled value, patched via ``app.graph.client.get_graph_client``.
"""
from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from app.engines.graph_rag import (
    GraphQuery,
    _kb_primary_retrieval_enabled,
    _retrieve_from_graph,
)

# A topic-shaped question that the legacy risk-tier dump would mis-answer
# with the high-risk obligation chain (Arts 9-15) instead of the gold
# Article 50 (transparency to natural persons interacting with AI).
_TOPIC_QUESTION = "How should users be informed when interacting with AI systems?"


def _topic_query() -> GraphQuery:
    """Minimal valid GraphQuery for the topic question.

    GraphQuery fields all carry defaults; ``intent`` / ``entities`` /
    ``risk_context`` / ``raw_question`` are the load-bearing ones for the
    retrieval paths exercised here. ``risk_context="high"`` mirrors the
    risk tier a topic question resolves to (so the legacy path would dump
    the high-risk obligation chain).
    """
    return GraphQuery(
        intent="general_compliance",
        entities=[],
        risk_context="high",
        raw_question=_TOPIC_QUESTION,
    )


# ─── 1. Gate default ON ──────────────────────────────────────────────────────


def test_gate_default_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """With REGENOLD_KB_PRIMARY_RETRIEVAL UNSET, the gate is ON (default)."""
    monkeypatch.delenv("REGENOLD_KB_PRIMARY_RETRIEVAL", raising=False)
    assert _kb_primary_retrieval_enabled() is True


# ─── 2. Gate OFF / ON for explicit values ────────────────────────────────────


def test_gate_off_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit falsy values disable the gate; truthy values enable it."""
    for falsy in ("0", "false", "no", "off", "False", "OFF", "No"):
        monkeypatch.setenv("REGENOLD_KB_PRIMARY_RETRIEVAL", falsy)
        assert _kb_primary_retrieval_enabled() is False, falsy

    for truthy in ("1", "true", "on", "yes", "True", "ON", "Yes"):
        monkeypatch.setenv("REGENOLD_KB_PRIMARY_RETRIEVAL", truthy)
        assert _kb_primary_retrieval_enabled() is True, truthy


# ─── 3. Disabled client → unchanged KB path (davidath byte-identity) ─────────


def test_client_disabled_is_unchanged_kb_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """A DISABLED graph client takes the existing ``_retrieve_from_kb``
    early-return path — the new R252 gate branch is never reached, and
    ``execute_read`` is never called.

    This is the davidath byte-identity-by-construction proof: the bench has
    no Neo4j, so ``client.enabled`` is False and R252 cannot move the
    deterministic local scorecard.
    """
    monkeypatch.delenv("REGENOLD_KB_PRIMARY_RETRIEVAL", raising=False)

    disabled_client = Mock()
    disabled_client.enabled = False
    disabled_client.execute_read = Mock(return_value=[])

    with patch(
        "app.graph.client.get_graph_client",
        return_value=disabled_client,
    ):
        ctx = _retrieve_from_graph(_topic_query(), "high")

    # ``_retrieve_from_kb`` stamps the path as "kb_fallback".
    assert ctx.retrieval_path == "kb_fallback"
    # The disabled-client early return must never touch the graph.
    assert disabled_client.execute_read.call_count == 0


# ─── 4. Gate ON + enabled client → bypass the blunt Neo4j dump ───────────────


def test_kb_primary_bypasses_neo4j_dump_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gate ON + an ENABLED client whose Cypher dump would return the WRONG
    high-risk obligation chain (Arts 10/11/12). R252 must bypass that dump,
    serve the KB context (its own obligations), and never call
    ``execute_read``.
    """
    monkeypatch.delenv("REGENOLD_KB_PRIMARY_RETRIEVAL", raising=False)

    # The blunt risk-tier dump the gate must NOT use.
    wrong_dump = [
        {"id": "art10", "article": "Art. 10", "text": "data governance"},
        {"id": "art11", "article": "Art. 11", "text": "tech doc"},
        {"id": "art12", "article": "Art. 12", "text": "logs"},
    ]
    enabled_client = Mock()
    enabled_client.enabled = True
    enabled_client.execute_read = Mock(return_value=list(wrong_dump))

    with patch(
        "app.graph.client.get_graph_client",
        return_value=enabled_client,
    ):
        ctx = _retrieve_from_graph(_topic_query(), "high")

    # (a) The KB context was served.
    assert ctx.retrieval_path == "kb_fallback", (
        "Gate ON + enabled graph must serve the KB context, not the "
        f"Neo4j dump (got retrieval_path={ctx.retrieval_path!r})"
    )
    # (b) The wrong dump did NOT pollute the obligations — the KB path
    # produced its own, and none of the mock's Art. 10/11/12 rows leaked in.
    polluted = {
        o.get("article")
        for o in ctx.obligations
        if o.get("article") in {"Art. 10", "Art. 11", "Art. 12"}
        and o.get("id") in {"art10", "art11", "art12"}
    }
    assert not polluted, (
        f"Neo4j risk-tier dump leaked into the KB context: {polluted}"
    )
    # (c) The blunt dump was bypassed entirely — Cypher never ran.
    assert enabled_client.execute_read.call_count == 0, (
        "Gate ON must skip the blunt obligations_for_risk_level Cypher dump"
    )


# ─── 5. Gate OFF + enabled client → legacy Neo4j Cypher path ─────────────────


def test_gate_off_uses_legacy_neo4j_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gate OFF + an ENABLED client whose ``execute_read`` returns ``[]``
    for every call. The legacy Neo4j Cypher path must be ENTERED (i.e.
    ``execute_read`` is called at least once). With empty results the R99
    empty-success KB fallback then fires — that's fine; the assertion is
    just that the legacy path ran.
    """
    monkeypatch.setenv("REGENOLD_KB_PRIMARY_RETRIEVAL", "0")

    enabled_client = Mock()
    enabled_client.enabled = True
    enabled_client.execute_read = Mock(return_value=[])

    with patch(
        "app.graph.client.get_graph_client",
        return_value=enabled_client,
    ):
        _retrieve_from_graph(_topic_query(), "high")

    assert enabled_client.execute_read.call_count >= 1, (
        "Gate OFF must enter the legacy Neo4j Cypher retrieval path"
    )


# ─── 6. Cache key folds in the gate flag ─────────────────────────────────────


def test_cache_key_includes_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_engine_cache_key`` must produce DIFFERENT keys for the same
    (question, system_context) under REGENOLD_KB_PRIMARY_RETRIEVAL=1 vs =0
    — the flag flips the engine's retrieved articles (R30/R56/R79
    cache-poisoning doctrine).
    """
    from app.routes.regenold import _engine_cache_key

    question = _TOPIC_QUESTION
    system_context = "EU AI Act compliance"

    monkeypatch.setenv("REGENOLD_KB_PRIMARY_RETRIEVAL", "1")
    key_on = _engine_cache_key(question, system_context)

    monkeypatch.setenv("REGENOLD_KB_PRIMARY_RETRIEVAL", "0")
    key_off = _engine_cache_key(question, system_context)

    assert key_on != key_off, (
        "REGENOLD_KB_PRIMARY_RETRIEVAL flips engine retrieval but is not in "
        "the cache key — a mid-deploy flip would serve stale articles"
    )
