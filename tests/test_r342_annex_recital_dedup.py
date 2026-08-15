"""R342 — annex/recital grounding is deduplicated end-to-end.

The CR-skill review's Important finding #1 (confirmed empirically): the
KB-primary default path called ``_expand_referenced_annexes_and_recitals``
once inside ``_retrieve_from_kb`` and again right after in
``_retrieve_from_graph``, and the dedup was call-local — so every
referenced annex/recital was appended TWICE into the Stage-2 prompt
(reproduced live: ``Art. 43`` 1 → 2 entries, ``Art. 5`` 5 → 10). Every
entry is rendered verbatim into the Stage-2 grounding block, so a
duplicate doubles that block and can make the model double-count the
provision.

R342 fixes both layers:

1. ``_expand_referenced_annexes_and_recitals`` is now fully idempotent —
   it dedups against refs already in the queue AND the caps (2 annexes /
   3 recitals) count the QUEUE, not the call, so re-expanding an
   already-expanded context adds exactly nothing;
2. the redundant second call on the KB-primary path is removed.

These tests pin: no duplicate refs on the review's exact repro questions,
re-expansion is a stable no-op, the KB-primary path emits each ref once,
and the graph-empty-fallback path (kb takeover) emits each ref once.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from app.engines._graph_rag_impl import (
    _deterministic_parse,
    _expand_referenced_annexes_and_recitals,
    _retrieve_from_graph,
    _retrieve_from_kb,
)

# The review's exact repro questions.
_Q_ART43 = "What are the obligations under Art. 43?"
_Q_ART5 = "What is prohibited under Art. 5?"


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch):
    """Deterministic retrieval: no embeddings model, no dense layers."""
    monkeypatch.setenv("REGENOLD_EMBEDDINGS_DIM", "8")
    monkeypatch.setenv("REGENOLD_SKIP_MODEL_LOAD", "1")
    monkeypatch.setenv("REGENOLD_EMBEDDINGS_HTTP_MODE", "1")
    monkeypatch.setenv("REGENOLD_EMBEDDINGS_INDEX", "0")
    monkeypatch.delenv("REGENOLD_QUERY_EXPANSION", raising=False)
    monkeypatch.delenv("REGENOLD_COHERE_RERANK", raising=False)
    monkeypatch.delenv("COHERE_API_KEY", raising=False)


def _refs(ctx) -> list[str]:
    return [r.get("ref") for r in ctx.referenced_annexes_and_recitals]


# ─── 1. Idempotent expansion ─────────────────────────────────────────────────


@pytest.mark.parametrize("q", [_Q_ART43, _Q_ART5])
def test_expansion_is_idempotent(q: str) -> None:
    """Re-expanding an already-expanded context adds NOTHING: the caps count
    the queue, and refs already queued are skipped (the pre-fix double-call
    appended every ref a second time)."""
    ctx = _retrieve_from_kb(_deterministic_parse(q))
    first = _refs(ctx)

    assert first  # the question does reference annexes/recitals
    assert len(first) == len(set(first)), f"duplicate refs in {first}"

    _expand_referenced_annexes_and_recitals(ctx)  # old KB-primary double-call
    _expand_referenced_annexes_and_recitals(ctx)  # and a third, for safety

    assert _refs(ctx) == first


@pytest.mark.parametrize("q", [_Q_ART43, _Q_ART5])
def test_kb_primary_path_emits_each_ref_once(q: str) -> None:
    """End-to-end: the KB-primary default path (gate ON, enabled client)
    must emit every referenced annex/recital exactly once — the review's
    exact 1→2 / 5→10 reproduction."""
    monkeypatch_free = pytest.MonkeyPatch()
    monkeypatch_free.delenv("REGENOLD_KB_PRIMARY_RETRIEVAL", raising=False)
    monkeypatch_free.delenv("REGENOLD_GRAPH_AWARE", raising=False)

    enabled_client = Mock()
    enabled_client.enabled = True
    enabled_client.execute_read = Mock(return_value=[])

    with patch(
        "app.graph.client.get_graph_client",
        return_value=enabled_client,
    ):
        ctx = _retrieve_from_graph(_deterministic_parse(q), "high")

    refs = _refs(ctx)
    assert refs  # the question does reference annexes/recitals
    assert len(refs) == len(set(refs)), f"duplicate refs on KB-primary path: {refs}"
    # Each type is bounded by its queue cap (2 annexes / 3 recitals).
    annexes = [r for r in refs if r.startswith("Annex ")]
    recitals = [r for r in refs if r.startswith("Recital ")]
    assert len(annexes) <= 2
    assert len(recitals) <= 3


def test_graph_empty_fallback_emits_each_ref_once() -> None:
    """The graph-empty → KB-takeover path expands internally AND at the end
    of ``_retrieve_from_graph``; idempotency keeps every ref unique."""
    monkeypatch_free = pytest.MonkeyPatch()
    monkeypatch_free.delenv("REGENOLD_KB_PRIMARY_RETRIEVAL", raising=False)

    # Gate OFF so the legacy graph path runs, but its Cypher returns empty
    # → the R99 empty-success fallback takes over with ``_retrieve_from_kb``.
    monkeypatch_free.setenv("REGENOLD_KB_PRIMARY_RETRIEVAL", "0")

    empty_client = Mock()
    empty_client.enabled = True
    empty_client.execute_read = Mock(return_value=[])

    with patch(
        "app.graph.client.get_graph_client",
        return_value=empty_client,
    ):
        ctx = _retrieve_from_graph(_deterministic_parse(_Q_ART5), "high")

    refs = _refs(ctx)
    assert refs  # the kb takeover did surface the Art. 5 annexes/recitals
    assert len(refs) == len(set(refs)), f"duplicate refs on kb-takeover path: {refs}"
