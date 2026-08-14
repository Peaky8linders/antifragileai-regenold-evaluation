"""Unit tests for the Cohere Reranker module."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.engines.cohere_reranker import (
    cohere_rerank_status,
    is_cohere_rerank_available,
    rerank_article_candidates,
    rerank_documents,
    reset_cohere_probe_cache_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    reset_cohere_probe_cache_for_tests()


class TestCohereRerankerStatus:
    """Test environment gating and status reporting."""

    def test_status_when_no_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("COHERE_API_KEY", raising=False)
        status = cohere_rerank_status()
        assert status["has_api_key"] is False
        assert status["available"] is False
        assert is_cohere_rerank_available() is False

    def test_status_when_key_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COHERE_API_KEY", "test-cohere-key-12345678")
        monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")
        status = cohere_rerank_status()
        assert status["has_api_key"] is True
        assert status["available"] is True
        assert is_cohere_rerank_available() is True

    def test_status_when_disabled_via_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COHERE_API_KEY", "test-cohere-key-12345678")
        monkeypatch.setenv("REGENOLD_COHERE_RERANK", "0")
        assert is_cohere_rerank_available() is False


class TestCohereRerankerFallback:
    """Test fallback behavior when Cohere is not available or encounters errors."""

    def test_rerank_documents_fallback_preserves_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("COHERE_API_KEY", raising=False)
        docs = ["Doc Alpha on Art 5", "Doc Beta on Art 10", "Doc Gamma on Art 15"]
        results = rerank_documents(query="AI risk management", documents=docs, top_n=3)
        assert len(results) == 3
        assert results[0]["document"] == docs[0]
        assert results[1]["document"] == docs[1]
        assert results[2]["document"] == docs[2]
        assert results[0]["relevance_score"] >= results[1]["relevance_score"]

    def test_rerank_article_candidates_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("COHERE_API_KEY", raising=False)
        candidates = [("Art. 5", 10.5), ("Art. 10", 8.2), ("Art. 15", 5.1)]
        res = rerank_article_candidates("risk governance", candidates, top_n=2)
        assert len(res) == 2
        assert res[0][0] == "Art. 5"
        assert res[1][0] == "Art. 10"


class TestCohereRerankerMockedExecution:
    """Test reranking with mocked HTTP responses."""

    def test_successful_cohere_rerank(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COHERE_API_KEY", "test-key-mock")
        monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [
                {"index": 2, "relevance_score": 0.98},
                {"index": 0, "relevance_score": 0.75},
                {"index": 1, "relevance_score": 0.32},
            ]
        }

        with patch("httpx.Client.post", return_value=mock_resp):
            docs = ["Doc 0 (low)", "Doc 1 (lowest)", "Doc 2 (best match)"]
            results = rerank_documents(query="high accuracy requirements", documents=docs, top_n=3)
            
            assert len(results) == 3
            assert results[0]["index"] == 2
            assert results[0]["document"] == "Doc 2 (best match)"
            assert results[0]["relevance_score"] == 0.98

    def test_auth_error_triggers_negative_probe(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("COHERE_API_KEY", "invalid-key")
        monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        import httpx
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_resp
        )

        with patch("httpx.Client.post", return_value=mock_resp):
            docs = ["Doc A", "Doc B"]
            res = rerank_documents(query="test", documents=docs)
            assert len(res) == 2
            # Verify negative cache was activated
            status = cohere_rerank_status()
            assert status["negative_probe_failed"] is True
            assert is_cohere_rerank_available() is False
