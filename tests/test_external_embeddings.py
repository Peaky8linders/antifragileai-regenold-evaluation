"""Unit tests for ``app.engines.external_embeddings``."""
from __future__ import annotations

import pytest

import app.engines.external_embeddings as ee


def test_is_available_logic(monkeypatch):
    """is_available() is True if any of the API keys/bases are set.

    ⚠ This test OWNS its ``REGENOLD_EXTERNAL_EMBEDDINGS`` state. The
    documented deterministic gate
    (``OPENAI_API_BASE=http://127.0.0.1:1/v1 P2P_GRAPH_RAG_PROVIDER=cli
    REGENOLD_EXTERNAL_EMBEDDINGS=0``) exports ``=0``, which the R127
    three-state override reads as "force-disable the module entirely"
    (:func:`ee._get_provider` returns ``None`` ABOVE the ``COHERE_API_KEY``
    check). Inheriting that made sub-case 2 fail and sub-cases 1/3 pass
    VACUOUSLY — every branch short-circuits at the same ``off`` line, so
    the provider-precedence logic under test never ran. Each sub-case now
    sets the mode it means to exercise.
    """
    # 1. All unset, gate in auto mode -> False
    monkeypatch.delenv("REGENOLD_EXTERNAL_EMBEDDINGS", raising=False)
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    assert ee._opt_in_mode() == "auto"
    assert ee.is_available() is False
    assert ee._get_provider() is None

    # 2. Cohere set -> True. A present ``COHERE_API_KEY`` is itself the
    #    opt-in (dedicated canonical embeddings API), so auto mode suffices.
    monkeypatch.setenv("COHERE_API_KEY", "co-testkey")
    assert ee.is_available() is True
    assert ee._get_provider() == "cohere"

    # 2b. R127 kill-switch: ``=0`` force-disables the WHOLE module, and it
    #     beats a present COHERE_API_KEY. This is the branch the documented
    #     deterministic test gate relies on to keep the dense hot path from
    #     paying a network round-trip; nothing covered it before, which is
    #     exactly why the sub-cases above could rot into vacuous passes.
    monkeypatch.setenv("REGENOLD_EXTERNAL_EMBEDDINGS", "0")
    assert ee._opt_in_mode() == "off"
    assert ee.is_available() is False
    assert ee._get_provider() is None
    monkeypatch.delenv("REGENOLD_EXTERNAL_EMBEDDINGS", raising=False)

    # 3. OpenAI key set WITHOUT explicit opt-in -> NOT available (R127).
    #    In this deployment OPENAI_API_KEY / OPENAI_API_BASE are the
    #    Claude-Max chat-wrapper vars (no /embeddings endpoint); the openai
    #    embeddings path must not auto-fire off their mere presence and pay
    #    a doomed network round-trip on the dense hot path.
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    monkeypatch.delenv("REGENOLD_EXTERNAL_EMBEDDINGS", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-testkey")
    assert ee.is_available() is False
    assert ee._get_provider() is None

    # 4. OpenAI key + explicit opt-in -> True
    monkeypatch.setenv("REGENOLD_EXTERNAL_EMBEDDINGS", "1")
    assert ee.is_available() is True
    assert ee._get_provider() == "openai"


def test_get_embedding_cohere_mock(monkeypatch):
    """get_embedding handles Cohere HTTP requests correctly.

    ``REGENOLD_EXTERNAL_EMBEDDINGS`` is dropped so the R127 ``off`` mode
    exported by the deterministic test gate cannot short-circuit
    :func:`ee._get_provider` above the ``COHERE_API_KEY`` check — the cohere
    branch below is the whole point of the test. No network is involved:
    ``httpx.Client.post`` is monkeypatched.
    """
    monkeypatch.delenv("REGENOLD_EXTERNAL_EMBEDDINGS", raising=False)
    monkeypatch.setenv("COHERE_API_KEY", "co-testkey")
    monkeypatch.setenv("REGENOLD_EXTERNAL_EMBEDDING_MODEL", "embed-english-v3.0")

    mock_emb = [[0.1, 0.2, 0.3]]

    class MockResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {"embeddings": mock_emb}

    def mock_post(self, url, headers, json, **kwargs):
        assert url == ee.COHERE_API_URL
        assert headers["Authorization"] == "Bearer co-testkey"
        assert json["texts"] == ["biometric systems"]
        assert json["model"] == "embed-english-v3.0"
        assert json["input_type"] == "search_query"
        return MockResponse()

    monkeypatch.setattr("httpx.Client.post", mock_post)

    emb = ee.get_embedding("biometric systems", is_query=True)
    assert emb is not None
    assert emb.shape == (3,)
    assert emb[0] == pytest.approx(0.1)


def test_get_embedding_openai_mock(monkeypatch):
    """get_embedding handles OpenAI HTTP requests correctly."""
    monkeypatch.delenv("COHERE_API_KEY", raising=False)
    # conftest.py pins ``OPENAI_API_BASE`` to a dead loopback as a no-live-calls
    # guard (R105); the production code honours it
    # (``api_base = os.getenv("OPENAI_API_BASE", OPENAI_API_URL)``), which would
    # make the request URL ``http://127.0.0.1:1/v1/embeddings`` instead of the
    # canonical endpoint this test asserts. Drop it so the code falls back to
    # ``OPENAI_API_URL`` — the test owns the base it verifies against.
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-testkey")
    # R127 — the openai embeddings path is opt-in only.
    monkeypatch.setenv("REGENOLD_EXTERNAL_EMBEDDINGS", "1")
    monkeypatch.setenv("REGENOLD_EXTERNAL_EMBEDDING_MODEL", "text-embedding-3-small")

    mock_emb = [{"index": 0, "embedding": [0.5, 0.6]}]

    class MockResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {"data": mock_emb}

    def mock_post(self, url, headers, json, **kwargs):
        assert url == ee.OPENAI_API_URL
        assert headers["Authorization"] == "Bearer sk-testkey"
        assert json["input"] == ["clinical notes"]
        assert json["model"] == "text-embedding-3-small"
        return MockResponse()

    monkeypatch.setattr("httpx.Client.post", mock_post)

    emb = ee.get_embedding("clinical notes", is_query=False)
    assert emb is not None
    assert emb.shape == (2,)
    assert emb[0] == pytest.approx(0.5)


def test_get_embedding_graceful_fallback(monkeypatch):
    """get_embedding returns None gracefully on any exception.

    ⚠ This test was GREEN BUT VACUOUS under the documented deterministic
    gate (``REGENOLD_EXTERNAL_EMBEDDINGS=0``): R127's ``off`` mode returns
    ``None`` from :func:`ee._get_provider` before any HTTP is attempted, so
    ``emb is None`` held for the wrong reason and the raising mock was never
    reached. Proven by execution — with the gate exported, the ``mock_post``
    counter below stayed at 0. The delenv restores auto mode, and the
    ``calls`` assertion pins that the exception path is the one exercised so
    the test cannot rot back into a tautology.
    """
    monkeypatch.delenv("REGENOLD_EXTERNAL_EMBEDDINGS", raising=False)
    monkeypatch.setenv("COHERE_API_KEY", "co-testkey")

    calls: list[int] = []

    def mock_post(*args, **kwargs):
        calls.append(1)
        raise RuntimeError("Network timeout")

    monkeypatch.setattr("httpx.Client.post", mock_post)

    emb = ee.get_embedding("biometric systems")
    assert emb is None
    assert calls, "graceful-fallback path never reached the HTTP seam"
