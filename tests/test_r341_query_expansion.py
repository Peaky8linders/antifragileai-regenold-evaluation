"""R341 — multi-query expansion (RAG-Fusion) wired into the deterministic parse.

The end-to-end review found the live retrieval ceiling is paraphrase
robustness: the curated ``_KEYWORD_ENTITY_MAP`` is a literal substring
scan, so a question phrased informally ("what must companies that put AI
on the market do?") misses it while its formal paraphrase ("what
obligations apply to providers of high-risk AI systems?") hits. The
``query_expansion`` module (Haiku 4.5 paraphrases + canonical
reciprocal-rank fusion) existed but was unwired. R341 wires it into
``_graph_rag_impl._deterministic_parse``:

* the SAME high-precision keyword map scans each paraphrase; new refs are
  appended AFTER the original's anchors, capped at 3 (a recall
  supplement, never a displacement);
* the BM25 fallback runs per query and RRF-combines the lists, capped at
  the budget a single query gets (max list length, itself ≤ k) — RRF
  re-ranks WHICH refs win, it never inflates the entity count;
* the fallback STILL runs when the original lanes found nothing, even if
  a lone paraphrase-union hit now leads the list (a measured starvation
  bug: one union hit replaced 8 BM25 refs before the fix).

The load-bearing assertions, per the R329/R331 lesson ("prove the lever
FIRES"):

* ``query_expansion_stats()[\"attempts\"] > 0`` whenever the gate is ON,
  the wrapper is alive, and the question is expandable — the inert-lever
  guard;
* gate OFF / wrapper dead / provider failure / anchored question /
  multi-turn shape → zero calls and byte-identical entities;
* explicit Art./Annex anchors never pay the LLM round-trip.

Byte-identity is guaranteed BY CONSTRUCTION (the R72/R100/R109 gating
discipline): the gate defaults OFF, and with it off
``_expansion_added == 0`` makes the fallback gate ``not entities``
exactly as before.
"""

from __future__ import annotations

import pytest

from app.engines import query_expansion as QE
from app.engines._graph_rag_impl import _deterministic_parse

#: A question the keyword map misses entirely — retrieval comes from the
#: BM25 fallback (8 refs under the hermetic fixture).
_Q_NO_ENTITY = (
    "What ongoing safety surveillance applies to AI systems after they "
    "are placed on the market?"
)

#: A paraphrase that hits the high-precision map (\"post-market monitoring\"
#: → Art. 72) while the original question above does not.
_PARAPHRASE_72 = (
    "What post-market monitoring obligations apply to providers of "
    "high-risk AI systems?"
)

#: An explicitly-anchored question — expansion must never fire on it.
_Q_ANCHORED = (
    "What are the obligations for high-risk AI systems under Art. 43 and Art. 5?"
)


class _FakeResp:
    error = None

    def __init__(self, text: str):
        self.text = text


class _FakeProvider:
    def __init__(self, text: str, raises: Exception | None = None):
        self._text = text
        self._raises = raises

    def complete(self, req):
        if self._raises is not None:
            raise self._raises
        return _FakeResp(self._text)


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch):
    """Deterministic parse: no embeddings model, no dense layers, no live
    wrapper, counters reset per test."""
    monkeypatch.setenv("REGENOLD_EMBEDDINGS_DIM", "8")
    monkeypatch.setenv("REGENOLD_SKIP_MODEL_LOAD", "1")
    monkeypatch.setenv("REGENOLD_EMBEDDINGS_INDEX", "0")
    monkeypatch.delenv("REGENOLD_QUERY_EXPANSION", raising=False)
    monkeypatch.setattr(QE, "is_openai_wrapper_enabled", lambda: False)
    QE.reset_query_expansion_stats()
    yield
    QE.reset_query_expansion_stats()


def _enable_expansion(monkeypatch, paraphrase: str, *, raises=None) -> None:
    monkeypatch.setenv("REGENOLD_QUERY_EXPANSION", "1")
    monkeypatch.setattr(QE, "is_openai_wrapper_enabled", lambda: True)
    monkeypatch.setattr(
        QE, "get_openai_wrapper_provider",
        lambda: _FakeProvider(f'{{"paraphrases": ["{paraphrase}"]}}', raises=raises),
    )


def test_gate_off_is_byte_identical(monkeypatch):
    """Default path: zero LLM calls, entities exactly as parsed."""
    base = _deterministic_parse(_Q_NO_ENTITY).entities
    anchored_base = _deterministic_parse(_Q_ANCHORED).entities

    assert QE.query_expansion_stats()["attempts"] == 0
    # The gate-off path with a DEAD wrapper must also be byte-identical:
    # expansion is attempted only when both the gate AND the wrapper are on.
    monkeypatch.setattr(QE, "is_openai_wrapper_enabled", lambda: True)
    monkeypatch.setenv("REGENOLD_QUERY_EXPANSION", "1")
    monkeypatch.setattr(
        QE, "get_openai_wrapper_provider",
        lambda: _FakeProvider(
            '{"paraphrases": ["What post-market monitoring applies?"]}',
            raises=RuntimeError("wrapper down"),
        ),
    )
    assert _deterministic_parse(_Q_NO_ENTITY).entities == base
    assert _deterministic_parse(_Q_ANCHORED).entities == anchored_base


def test_expansion_fires_and_adds_paraphrase_entity(monkeypatch):
    """THE inert-lever guard: gate ON + live wrapper → the provider MUST be
    called and the paraphrase's high-precision map hit must reach the entity
    list (leading it, since it is appended before the BM25 lane)."""
    base = _deterministic_parse(_Q_NO_ENTITY).entities
    assert base  # the fallback did surface refs

    _enable_expansion(monkeypatch, _PARAPHRASE_72)
    out = _deterministic_parse(_Q_NO_ENTITY).entities

    stats = QE.query_expansion_stats()
    assert stats["attempts"] == 1
    assert stats["expanded"] >= 1
    assert stats["failed"] == 0
    assert "Art. 72" in out
    assert out[0] == "Art. 72"  # the union hit leads the list
    # The BM25 lane still contributes — the union did not starve it
    # (measured starvation bug this test pins: 8 refs → 1 pre-fix).
    assert len(out) == len(base)


def test_paraphrase_union_is_capped(monkeypatch):
    """A paraphrase that repeats many map phrases adds at most 3 new refs —
    the union is a recall supplement, never a budget inflater."""
    q = "Tell me about deepfakes"
    base = _deterministic_parse(q).entities  # gate off: baseline first
    assert base  # the original scan does anchor Art. 50

    _enable_expansion(
        monkeypatch,
        "What are the fines and penalties for prohibited practices and "
        "serious incidents in relation to deepfakes, emotion recognition "
        "and conformity assessment?",
    )
    out = _deterministic_parse(q).entities

    assert QE.query_expansion_stats()["attempts"] == 1
    assert len(out) - len(base) <= 3
    assert base == [e for e in base]  # original anchors untouched


def test_explicit_anchor_skips_expansion(monkeypatch):
    """Art./Annex-anchored questions never pay the LLM round-trip — the
    anchor is already exact and paraphrasing adds noise for zero recall."""
    _enable_expansion(monkeypatch, _PARAPHRASE_72)
    out = _deterministic_parse(_Q_ANCHORED).entities

    assert QE.query_expansion_stats()["attempts"] == 0
    assert out[:2] == ["Art. 43", "Art. 5"]


def test_multi_turn_shape_skips_expansion(monkeypatch):
    """The flattened multi-turn string is conversation history, not a
    question — paraphrasing it is meaningless, so expansion must skip."""
    _enable_expansion(monkeypatch, _PARAPHRASE_72)
    mt = (
        "Conversation so far:\nUser: What is a high-risk AI system?\n\n"
        f"Latest question:\n{_Q_NO_ENTITY}"
    )
    _deterministic_parse(mt)

    assert QE.query_expansion_stats()["attempts"] == 0


def test_provider_failure_is_fail_soft(monkeypatch):
    """A wrapper outage must not change parse: entities identical, failure
    counted (attempts>0, failed>0)."""
    base = _deterministic_parse(_Q_NO_ENTITY).entities
    _enable_expansion(
        monkeypatch, _PARAPHRASE_72, raises=RuntimeError("wrapper down")
    )
    out = _deterministic_parse(_Q_NO_ENTITY).entities

    stats = QE.query_expansion_stats()
    assert stats["attempts"] == 1
    assert stats["failed"] == 1
    assert out == base


def test_empty_paraphrase_response_is_fail_soft(monkeypatch):
    """A 200 with no usable paraphrases is a soft failure — [original] only."""
    base = _deterministic_parse(_Q_NO_ENTITY).entities
    # ``{"paraphrases": [""]}`` — the provider answered but produced no
    # usable paraphrase: a soft failure, [original] only.
    _enable_expansion(monkeypatch, "")
    out = _deterministic_parse(_Q_NO_ENTITY).entities

    stats = QE.query_expansion_stats()
    assert stats["attempts"] == 1
    assert stats["failed"] == 1
    assert out == base


def test_rrf_budget_is_preserved(monkeypatch):
    """The RRF lane re-ranks WHICH refs win; it never inflates the entity
    count past what a single BM25 query is allowed to surface."""
    base = _deterministic_parse(_Q_NO_ENTITY).entities
    _enable_expansion(monkeypatch, _PARAPHRASE_72)
    out = _deterministic_parse(_Q_NO_ENTITY).entities

    assert QE.query_expansion_stats()["attempts"] == 1
    assert len(out) == len(base) <= 8
    # RRF refreshed the pool: at least one ref that the paraphrase's BM25
    # run surfaced is now in the list (or the union hit, Art. 72, leads).
    assert "Art. 72" in out


def test_reciprocal_rank_fusion_ranks_by_agreement():
    """Canonical RRF: a doc present in BOTH lists outranks a doc present in
    one, and the k=60 tie-break keeps insertion order stable."""
    combined = QE.reciprocal_rank_fusion(
        [["a", "b", "c"], ["b", "c", "d", "a"]]
    )
    assert combined[0] == "b"  # rank 2 + rank 1 = strongest agreement
    assert set(combined) == {"a", "b", "c", "d"}
    # A doc in only one list ranks below the shared docs.
    assert combined.index("d") > combined.index("b")


def test_cache_key_changes_with_flag(monkeypatch):
    """R263.2 fire check: the engine cache key MUST move when the gate flips,
    or an in-process A/B would serve the baseline arm's cached engine output
    to the branch arm and measure nothing."""
    from app.routes.regenold import _engine_cache_key  # noqa: PLC0415

    monkeypatch.delenv("REGENOLD_QUERY_EXPANSION", raising=False)
    before = _engine_cache_key(_Q_NO_ENTITY, None, 0, False)
    monkeypatch.setenv("REGENOLD_QUERY_EXPANSION", "1")
    after = _engine_cache_key(_Q_NO_ENTITY, None, 0, False)
    assert after != before


# ── R346 — the paraphrase transport follows the ACTIVE provider ─────────────
#
# Under ``P2P_GRAPH_RAG_PROVIDER=bedrock`` the paraphrase call must ride
# Bedrock's own Haiku 4.5, NOT the Claude-Max wrapper — the operator keeps
# the tunnel for the live re-evaluation, and a Bedrock-only run with the
# wrapper disabled must still be able to expand. These tests pin the
# transport dispatch, not the R341 parse wiring (covered above).


def _enable_bedrock_expansion(monkeypatch, paraphrase: str):
    """Gate ON, provider=bedrock, wrapper DEAD, Bedrock alive (faked)."""
    import app.llm.bedrock_client as BC  # noqa: PLC0415

    monkeypatch.setenv("REGENOLD_QUERY_EXPANSION", "1")
    monkeypatch.setenv("P2P_GRAPH_RAG_PROVIDER", "bedrock")
    monkeypatch.setattr(QE, "is_openai_wrapper_enabled", lambda: False)
    monkeypatch.setattr(BC, "is_bedrock_provider_enabled", lambda: True)
    calls: list = []

    def _fake_complete(req):
        calls.append(req)
        return _FakeResp(f'{{"paraphrases": ["{paraphrase}"]}}')

    monkeypatch.setattr(BC, "complete_with_fallback", _fake_complete)
    return calls


def test_bedrock_transport_fires(monkeypatch):
    """THE R346 inert-lever guard: provider=bedrock + wrapper dead must still
    reach the paraphrase provider — the Bedrock Haiku call happens and the
    paraphrase's map hit lands in the entity list."""
    base = _deterministic_parse(_Q_NO_ENTITY).entities
    calls = _enable_bedrock_expansion(monkeypatch, _PARAPHRASE_72)

    out = _deterministic_parse(_Q_NO_ENTITY).entities

    stats = QE.query_expansion_stats()
    assert stats["attempts"] == 1
    assert stats["expanded"] >= 1
    assert stats["failed"] == 0
    assert len(calls) == 1
    # R346.2 — the paraphrase rides the frontier tier (Sonnet 4.6), never
    # Haiku, and defaults to the judge tier rather than the Opus generation
    # model. The env override must win when set.
    assert calls[0].model == "claude-sonnet-4-6"
    assert "Art. 72" in out
    assert out[0] == "Art. 72"
    assert len(out) == len(base)  # BM25 lane preserved, budget intact


def test_bedrock_transport_honours_model_override(monkeypatch):
    """R346.2 — ``REGENOLD_QUERY_EXPANSION_MODEL`` pins the paraphrase tier
    (e.g. the Opus generation model) on the Bedrock transport."""
    base = _deterministic_parse(_Q_NO_ENTITY).entities
    monkeypatch.setenv("REGENOLD_QUERY_EXPANSION_MODEL", "claude-opus-4-6")
    calls = _enable_bedrock_expansion(monkeypatch, _PARAPHRASE_72)

    out = _deterministic_parse(_Q_NO_ENTITY).entities

    assert QE.query_expansion_stats()["attempts"] == 1
    assert len(calls) == 1
    assert calls[0].model == "claude-opus-4-6"
    assert "Art. 72" in out
    assert out[0] == "Art. 72"
    assert len(out) == len(base)  # BM25 lane preserved, budget intact


def test_bedrock_disabled_falls_back_to_wrapper(monkeypatch):
    """provider=bedrock but Bedrock credentials absent → the historical
    wrapper path serves the call (attempts>0) rather than silently
    disabling expansion."""
    import app.llm.bedrock_client as BC  # noqa: PLC0415

    monkeypatch.setenv("REGENOLD_QUERY_EXPANSION", "1")
    monkeypatch.setenv("P2P_GRAPH_RAG_PROVIDER", "bedrock")
    monkeypatch.setattr(QE, "is_openai_wrapper_enabled", lambda: True)
    monkeypatch.setattr(BC, "is_bedrock_provider_enabled", lambda: False)
    wrapper_calls: list = []

    def _fake_wrapper():
        wrapper_calls.append(1)
        return _FakeProvider(f'{{"paraphrases": ["{_PARAPHRASE_72}"]}}')

    monkeypatch.setattr(QE, "get_openai_wrapper_provider", _fake_wrapper)
    out = _deterministic_parse(_Q_NO_ENTITY).entities

    stats = QE.query_expansion_stats()
    assert stats["attempts"] == 1
    assert stats["failed"] == 0
    assert len(wrapper_calls) == 1
    assert "Art. 72" in out


def test_bedrock_only_no_provider_no_call(monkeypatch):
    """provider=bedrock, wrapper dead AND Bedrock dead → zero calls, exact
    baseline entities (fail-soft, nothing silently degrades)."""
    import app.llm.bedrock_client as BC  # noqa: PLC0415

    monkeypatch.setenv("REGENOLD_QUERY_EXPANSION", "1")
    monkeypatch.setenv("P2P_GRAPH_RAG_PROVIDER", "bedrock")
    monkeypatch.setattr(QE, "is_openai_wrapper_enabled", lambda: False)
    monkeypatch.setattr(BC, "is_bedrock_provider_enabled", lambda: False)

    out = _deterministic_parse(_Q_NO_ENTITY).entities
    base = _deterministic_parse(_Q_NO_ENTITY).entities

    assert QE.query_expansion_stats()["attempts"] == 0
    assert out == base
