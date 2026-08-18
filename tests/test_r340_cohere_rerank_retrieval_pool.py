"""R340 — Cohere cross-encoder rerank wired into the retrieval candidate pool.

The R329/R331 placements either reordered only non-citable Stage-2 prompt
context or never fired at all (three placements read +0.0000 on every axis
because they never issued a call). R340 wires the SAME permutation-safe
reranker into :func:`app.data.kb_search.top_articles_by_relevance` (and its
chapter/section variants): the BM25+dense fused pool is gathered up to
``_RERANK_POOL_SIZE`` (50) and reranked BEFORE the top-k reference cut.

The load-bearing assertions, per the R329 lesson ("prove the lever FIRES"):

* ``rerank_stats()["attempts"] > 0`` whenever the gate is on and the pool has
  >= 2 candidates — the inert-lever guard;
* the gate-OFF path issues zero calls and returns exactly the pre-R340 order;
* a network / malformed-response failure falls back to the BM25 order
  unchanged (never drops, never reorders on outage);
* the rerank genuinely decides the cut: with the API returning reversed
  relevance, the top-k head of the wire list comes from the tail of the pool.

davidath byte-identity is guaranteed BY CONSTRUCTION (same gating discipline
as R72/R100/R109): the gate defaults OFF, and with it off ``_pool_k == k`` so
every internal slice/fill/budget is unchanged.
"""

from __future__ import annotations

import pytest

from app.data.kb_search import (
    top_articles_by_relevance,
    top_articles_by_relevance_in_chapters,
)
from app.engines import cohere_rerank as CR

#: A question with a wide, well-scored BM25 spread — the rerank pool has
#: material to move. (Probed: yields 5+ admitted candidates at min_score=1.0.)
_Q = "What are the technical documentation and risk management requirements for high-risk AI systems?"

#: The gate-OFF result for ``_Q`` at k=5 — pinned so the OFF path can be
#: asserted byte-identical even if a future corpus change moves the rankings
#: (update the pin only with a deliberate corpus/BM25 change).
_BASELINE = ["Art. 11", "Art. 16", "Annex IV", "Art. 43", "Art. 18"]


def _no_network(*_a, **_k):  # pragma: no cover — must never run
    raise AssertionError("live rerank HTTP call attempted in a unit test")


class _FakeResp:
    status_code = 200
    text = ""

    def __init__(self, results: list[dict]):
        self._results = results

    def json(self) -> dict:
        return {"results": self._results}


class _FakeClient:
    """Records the payload, then answers with ``results``.

    ``results`` may be ``None`` to emulate a malformed (no-``results``)
    response; ``raises`` to emulate a network failure.
    """

    captured: dict = {}

    def __init__(self, results, raises: Exception | None = None):
        self._results = results
        self._raises = raises

    def post(self, url: str, *, json: dict, headers: dict):
        self.captured["url"] = url
        self.captured["json"] = json
        if self._raises is not None:
            raise self._raises
        if self._results is None:
            return _FakeResp({})
        return _FakeResp(self._results)


@pytest.fixture(autouse=True)
def _hermetic_retrieval(monkeypatch):
    """Deterministic, hermetic retrieval: no embeddings/graph/dense layers,
    no live rerank network, counters reset per test."""
    monkeypatch.setenv("REGENOLD_EMBEDDINGS_INDEX", "0")
    monkeypatch.delenv("REGENOLD_TURBOQUANT_DENSE", raising=False)
    monkeypatch.delenv("REGENOLD_GRAPH_2HOP", raising=False)
    monkeypatch.delenv("REGENOLD_GRAPH_PPR", raising=False)
    monkeypatch.delenv("REGENOLD_PATH_RAG", raising=False)
    monkeypatch.delenv("REGENOLD_COHERE_RERANK", raising=False)
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    monkeypatch.setattr(CR, "_get_client", _no_network)
    CR.reset_rerank_stats()
    yield
    CR.reset_rerank_stats()


def _enable_gate(monkeypatch) -> None:
    monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")
    monkeypatch.setenv("COHERE_API_KEY", "test-key")


def test_gate_off_is_byte_identical_and_makes_no_call(monkeypatch):
    """The default path: zero rerank calls, output exactly the pre-R340 order."""
    out = top_articles_by_relevance(_Q, k=5, min_score=1.0)
    assert out == _BASELINE
    assert CR.rerank_stats()["attempts"] == 0


def test_rerank_fires_and_decides_the_cut(monkeypatch):
    """THE inert-lever guard: with the gate on, a rerank call MUST happen and
    the reversed API relevance must move the top-k head to the pool's tail."""
    _enable_gate(monkeypatch)

    def _results_for(json_payload: dict) -> list[dict]:
        n = len(json_payload["documents"])
        # Emulate Cohere: best-first results, with the LAST pool doc scored
        # highest, i.e. relevance fully reversed vs BM25 order.
        return [
            {"index": n - 1 - i, "relevance_score": float(n - i)}
            for i in range(n)
        ]

    captured: dict = {}
    fake = _FakeClient(None)
    fake.post = lambda url, *, json, headers: (
        captured.update({"url": url, "json": json}) or _FakeResp(_results_for(json))
    )
    monkeypatch.setattr(CR, "_get_client", lambda: fake)

    out = top_articles_by_relevance(_Q, k=5, min_score=1.0)

    assert CR.rerank_stats()["attempts"] == 1
    assert CR.rerank_stats()["failed"] == 0
    assert len(out) == 5
    # The rerank decided the cut: the wire head is the pool TAIL (the doc the
    # API scored highest), not the BM25 winner.
    assert out != _BASELINE
    pool_docs = captured["json"]["documents"]
    # Provision text is truncated to the model-aware per-doc cap by
    # rerank_references (4,000 chars on rerank-v3.x, 24,000 on
    # rerank-v4.0-pro/-fast — R371.8).
    from app.data.provision_text import get_provision_text  # noqa: PLC0415

    cap = CR._max_doc_chars()
    assert get_provision_text(out[0]).strip()[:cap] == pool_docs[-1]


def test_rerank_pool_is_wider_than_k(monkeypatch):
    """The 'BM25+dense top-50' pool: the API must receive MORE than k docs so
    the rerank can actually move a mid-pool provision across the cut."""
    _enable_gate(monkeypatch)

    captured: dict = {}
    fake = _FakeClient(None)
    fake.post = lambda url, *, json, headers: (
        captured.update({"json": json})
        or _FakeResp(
            [
                {"index": i, "relevance_score": 1.0}
                for i in range(len(json["documents"]))
            ]
        )
    )
    monkeypatch.setattr(CR, "_get_client", lambda: fake)

    top_articles_by_relevance(_Q, k=5, min_score=1.0)
    assert len(captured["json"]["documents"]) > 5
    assert captured["json"]["documents"][0]  # query + docs were actually sent


def test_http_failure_falls_back_to_bm25_order(monkeypatch):
    """A rerank outage must never change retrieval: input order restored,
    failure counted (attempts>0, failed>0)."""
    _enable_gate(monkeypatch)
    fake = _FakeClient(None, raises=RuntimeError("wrapper down"))
    monkeypatch.setattr(CR, "_get_client", lambda: fake)

    out = top_articles_by_relevance(_Q, k=5, min_score=1.0)

    assert CR.rerank_stats()["attempts"] == 1
    assert CR.rerank_stats()["failed"] == 1
    assert out == _BASELINE


def test_malformed_response_falls_back_to_bm25_order(monkeypatch):
    """A 200 with no usable ``results`` is a soft failure — keep BM25 order."""
    _enable_gate(monkeypatch)
    fake = _FakeClient(None)
    fake.post = lambda url, *, json, headers: _FakeResp({})
    monkeypatch.setattr(CR, "_get_client", lambda: fake)

    out = top_articles_by_relevance(_Q, k=5, min_score=1.0)

    assert CR.rerank_stats()["attempts"] == 1
    assert CR.rerank_stats()["failed"] == 1
    assert out == _BASELINE


def test_rerank_exception_is_swallowed(monkeypatch):
    """Even a broken rerank_references import/call must not reach the caller."""
    _enable_gate(monkeypatch)

    def _boom(*_a, **_k):  # pragma: no cover — must never run
        raise RuntimeError("boom")

    monkeypatch.setattr(CR, "rerank_references", _boom)

    out = top_articles_by_relevance(_Q, k=5, min_score=1.0)
    assert out == _BASELINE


def test_scoped_chapter_variant_fires(monkeypatch):
    """The chapter-scoped variant (the one actually reached on the no-entity
    path) must also fire the rerank — R329's first-cut trap was a placement
    that was reachable only on a path nobody hit."""
    _enable_gate(monkeypatch)
    fake = _FakeClient(None)
    fake.post = lambda url, *, json, headers: _FakeResp(
        [
            {"index": i, "relevance_score": 1.0}
            for i in range(len(json["documents"]))
        ]
    )
    monkeypatch.setattr(CR, "_get_client", lambda: fake)

    out = top_articles_by_relevance_in_chapters(_Q, ["III"], k=5, min_score=1.0)

    assert CR.rerank_stats()["attempts"] == 1
    assert len(out) == 5


# ── Parse-level placement (R340.1) ───────────────────────────────────────────
#
# The pool rerank alone would be near-inert on the live path: the keyword map
# extracts an entity for nearly every question, so ``top_articles_by_relevance*``
# only runs on the rare no-entity fallback. The placement that actually fires
# on the COMMON path is the rerank of the FINAL assembled entity list inside
# ``_graph_rag_impl._deterministic_parse`` — entity ORDER is load-bearing
# downstream (obligations are built in entity order; the citation cap of 15
# slots is drawn from that order). These tests pin the placement: it fires
# exactly once per request (never twice — the BM25 fallback skips it because
# its scoped search already reranked the pool), gate-off is byte-identical,
# and a rerank outage leaves the parsed entity order untouched.

#: A question whose keyword map extracts exactly two entities.
_Q_MULTI = "What are the obligations for high-risk AI systems under Art. 43 and Art. 5?"

#: A question with NO keyword-map entity — forces the BM25 fallback branch
#: (scoped chapter search) inside ``_deterministic_parse``.
_Q_NO_ENTITY = "What does the regulation cover generally?"


def _enable_parse_env(monkeypatch) -> None:
    """Deterministic parse without a real embeddings model or live network:
    pure BM25 (the hermetic fixture already turns the dense layer off)."""
    monkeypatch.setenv("REGENOLD_EMBEDDINGS_DIM", "8")
    monkeypatch.setenv("REGENOLD_SKIP_MODEL_LOAD", "1")


def _fake_post_reversed(n_docs: int) -> list[dict]:
    """Emulate Cohere best-first relevance fully reversed vs input order.

    Returns the ``results`` LIST (``_FakeResp.json()`` wraps it)."""
    return [
        {"index": n_docs - 1 - i, "relevance_score": float(n_docs - i)}
        for i in range(n_docs)
    ]


def test_parse_level_rerank_fires_and_moves_entity_order(monkeypatch):
    """THE common-path guard: with the gate on, the FINAL entity list is
    reranked exactly once, and the API's reversed relevance moves Art. 5
    ahead of Art. 43 (the order every downstream citation cap reads)."""
    from app.engines._graph_rag_impl import _deterministic_parse  # noqa: PLC0415

    _enable_parse_env(monkeypatch)
    _enable_gate(monkeypatch)
    fake = _FakeClient(None)
    fake.post = lambda url, *, json, headers: _FakeResp(
        _fake_post_reversed(len(json["documents"]))
    )
    monkeypatch.setattr(CR, "_get_client", lambda: fake)

    gq = _deterministic_parse(_Q_MULTI)

    assert CR.rerank_stats()["attempts"] == 1
    assert CR.rerank_stats()["failed"] == 0
    assert gq.entities[:2] == ["Art. 5", "Art. 43"]  # rerank decided the order


def test_parse_level_gate_off_is_byte_identical(monkeypatch):
    """Default path: zero rerank calls, entity order exactly as parsed."""
    from app.engines._graph_rag_impl import _deterministic_parse  # noqa: PLC0415

    _enable_parse_env(monkeypatch)

    gq = _deterministic_parse(_Q_MULTI)

    assert CR.rerank_stats()["attempts"] == 0
    assert gq.entities[:2] == ["Art. 43", "Art. 5"]


def test_parse_level_no_double_rerank_on_bm25_fallback(monkeypatch):
    """One Cohere call per request, never two: on the no-entity fallback the
    scoped search reranks its pool, so the parse-level rerank must SKIP."""
    import app.engines._graph_rag_impl as G  # noqa: PLC0415

    _enable_parse_env(monkeypatch)
    _enable_gate(monkeypatch)
    fake = _FakeClient(None)
    fake.post = lambda url, *, json, headers: _FakeResp(
        _fake_post_reversed(len(json["documents"]))
    )
    monkeypatch.setattr(CR, "_get_client", lambda: fake)

    search_calls: list[str] = []
    for fn_name in (
        "top_articles_by_relevance_in_chapters",
        "top_articles_by_relevance_in_sections",
        "top_articles_by_relevance",
    ):
        real = getattr(G, fn_name)

        def _spy(q, *args, _real=real, **kwargs):
            search_calls.append(q)
            return _real(q, *args, **kwargs)

        monkeypatch.setattr(G, fn_name, _spy)

    gq = G._deterministic_parse(_Q_NO_ENTITY)

    assert search_calls, "BM25 fallback branch was not exercised"
    # Exactly ONE network call total: the pool rerank inside the fallback
    # search. The parse-level rerank correctly skipped (no double round-trip).
    assert CR.rerank_stats()["attempts"] == 1
    assert gq.entities  # the fallback did surface provisions


def test_parse_level_rerank_exception_is_swallowed(monkeypatch):
    """A broken rerank must never break parsing: entities stay in parsed order."""
    from app.engines._graph_rag_impl import _deterministic_parse  # noqa: PLC0415

    _enable_parse_env(monkeypatch)
    _enable_gate(monkeypatch)

    def _boom(*_a, **_k):  # pragma: no cover — must never run
        raise RuntimeError("boom")

    # R347 — the parse-level wiring now calls ``rerank_pool`` (the ok-bit
    # variant) rather than the ``rerank_references`` wrapper; the
    # swallowed-exception contract is unchanged.
    monkeypatch.setattr(CR, "rerank_pool", _boom)

    gq = _deterministic_parse(_Q_MULTI)

    assert gq.entities[:2] == ["Art. 43", "Art. 5"]
    assert CR.rerank_stats()["attempts"] == 0
