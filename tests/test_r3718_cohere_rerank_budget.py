"""R371.8 — Cohere rerank: request-budget enforcement + v4.0 wiring.

The R350 review counted FIVE serial Cohere calls inside one request (BM25
fallback per expanded query + parse-level pool rerank + kg-context rerank).
R362 documented a per-request budget (``REGENOLD_RERANK_REQUEST_BUDGET``,
default 2) but the enforcement was never written — ``reset_request_budget``
was imported at ``_graph_rag_impl.py:10167`` and the ImportError was swallowed
by the fail-soft wrapper, so the cascade stayed unbounded and the Trial key
(10 calls/min, 1,000/month) could 429 into a false INERT A/B. These tests pin
the real enforcement + the model-aware document sizing (rerank-v4.0-pro /
-fast, 32,768-token context).
"""
from __future__ import annotations

import pytest

import app.engines.cohere_rerank as cr


class _FakeResponse:
    status_code = 200

    def json(self) -> dict:
        return {"results": [{"index": 0, "relevance_score": 0.9},
                            {"index": 1, "relevance_score": 0.8}]}


class _FakeClient:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    def post(self, url: str, json: dict, headers: dict) -> _FakeResponse:
        self.payloads.append({"url": url, "json": json, "headers": headers})
        return _FakeResponse()


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch):
    """Restore the module's pristine state after every test.

    The budget is module-level per-request state; a test that exhausts it
    (or arms it) must not bleed into later test files — that turned the
    r340 parse-level rerank tests into order-dependent failures.
    """
    yield
    cr._budget_remaining = None
    cr.reset_rerank_stats()


@pytest.fixture()
def fake(monkeypatch) -> _FakeClient:
    client = _FakeClient()
    monkeypatch.setattr(cr, "_get_client", lambda: client)
    monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")
    monkeypatch.setenv("COHERE_API_KEY", "test-key")
    cr._budget_remaining = None
    cr.reset_rerank_stats()
    return client


DOCS = ["alpha beta gamma delta epsilon", "zeta eta theta iota kappa"]


def test_default_model_is_v4_pro() -> None:
    assert cr._DEFAULT_MODEL == "rerank-v4.0-pro"
    assert cr._effective_model() == "rerank-v4.0-pro"
    assert cr._is_v4(cr._effective_model())


def test_v4_doc_cap_uses_larger_context(monkeypatch) -> None:
    monkeypatch.setenv("REGENOLD_COHERE_RERANK_MODEL", "rerank-v4.0-pro")
    assert cr._max_doc_chars() == cr._MAX_RERANK_DOC_CHARS_V4


def test_v3_doc_cap_keeps_old_budget(monkeypatch) -> None:
    monkeypatch.setenv("REGENOLD_COHERE_RERANK_MODEL", "rerank-v3.5")
    assert cr._max_doc_chars() == cr._MAX_RERANK_DOC_CHARS_V3


def test_request_budget_blocks_third_call(fake: _FakeClient) -> None:
    cr.reset_rerank_stats()
    cr.reset_request_budget()  # default 2 calls/request
    assert cr.rerank_documents("q", DOCS) is not None
    assert cr.rerank_documents("q", DOCS) is not None
    assert cr.rerank_documents("q", DOCS) is None  # budget exhausted
    stats = cr.rerank_stats()
    assert stats["attempts"] == 2
    assert stats["budget_blocked"] == 1


def test_budget_env_override(fake: _FakeClient, monkeypatch) -> None:
    monkeypatch.setenv("REGENOLD_RERANK_REQUEST_BUDGET", "1")
    cr.reset_request_budget()
    assert cr.rerank_documents("q", DOCS) is not None
    assert cr.rerank_documents("q", DOCS) is None
    assert cr.rerank_stats()["budget_blocked"] == 1


def test_budget_reset_restores_calls(fake: _FakeClient) -> None:
    cr.reset_request_budget()
    cr.rerank_documents("q", DOCS)
    cr.rerank_documents("q", DOCS)
    assert cr.rerank_documents("q", DOCS) is None
    cr.reset_request_budget()  # next request gets a fresh budget
    assert cr.rerank_documents("q", DOCS) is not None


def test_unarmed_budget_allows(fake: _FakeClient) -> None:
    """A caller that never resets (no request boundary) keeps the historical
    behaviour — ``None`` budget means 'allow', not 'refuse'."""
    cr._budget_remaining = None
    assert cr.rerank_documents("q", DOCS) is not None
    assert cr.rerank_documents("q", DOCS) is not None


def test_v4_payload_sends_max_tokens_per_doc(fake: _FakeClient) -> None:
    cr.reset_request_budget()
    cr.rerank_documents("query text", DOCS)
    payload = fake.payloads[-1]["json"]
    assert payload["model"] == "rerank-v4.0-pro"
    assert payload["max_tokens_per_doc"] == cr._MAX_TOKENS_PER_DOC_V4


def test_v3_payload_omits_max_tokens_per_doc(
    fake: _FakeClient, monkeypatch
) -> None:
    monkeypatch.setenv("REGENOLD_COHERE_RERANK_MODEL", "rerank-v3.5")
    cr.reset_request_budget()
    cr.rerank_documents("query text", DOCS)
    payload = fake.payloads[-1]["json"]
    assert payload["model"] == "rerank-v3.5"
    assert "max_tokens_per_doc" not in payload


def test_client_name_header(fake: _FakeClient) -> None:
    cr.reset_request_budget()
    cr.rerank_documents("query text", DOCS)
    assert fake.payloads[-1]["headers"]["X-Client-Name"] == "regenold-rag"
