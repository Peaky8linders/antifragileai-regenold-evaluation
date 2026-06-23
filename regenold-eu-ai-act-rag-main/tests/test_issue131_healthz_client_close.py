"""Regression tests for issue #131 — Anthropic ``/healthz/llm`` probe leak.

The probe constructed ``anthropic.Anthropic(...)`` per request and called
``client.models.list(limit=1)`` but never closed the client. The SDK is
httpx-backed, so every health check leaked a connection pool + file
descriptors. The fix context-manages the client so it is closed on BOTH
the success and the exception path.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    for k in (
        "P2P_GRAPH_RAG_PROVIDER",
        "P2P_GRAPH_RAG_API_KEY",
        "OPENAI_API_BASE",
        "OPENAI_API_KEY",
        "REGENOLD_HEALTHZ_PROBE_ANTHROPIC",
    ):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("REGENOLD_SKIP_STARTUP_LOG", "1")
    from app.main import app

    return TestClient(app)


def _make_recording_client(created: list, *, fail: bool) -> type:
    class _RecordingClient:
        def __init__(self, *a: object, **k: object) -> None:
            self.closed = False
            created.append(self)

        def __enter__(self) -> "_RecordingClient":
            return self

        def __exit__(self, *exc: object) -> bool:
            self.closed = True
            return False  # don't suppress

        def close(self) -> None:  # belt-and-braces for non-CM callers
            self.closed = True

        class models:  # noqa: N801
            @staticmethod
            def list(*a: object, **k: object) -> object:
                if fail:
                    raise RuntimeError("boom")
                return {"data": []}

    return _RecordingClient


def test_anthropic_healthz_probe_closes_client(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    anthropic = pytest.importorskip("anthropic")
    monkeypatch.setenv("P2P_GRAPH_RAG_PROVIDER", "anthropic")
    monkeypatch.setenv("P2P_GRAPH_RAG_API_KEY", "sk-ant-fake")
    from app.config import settings
    from pydantic import SecretStr

    monkeypatch.setattr(
        settings.graph_rag, "api_key", SecretStr("sk-ant-fake"), raising=True
    )

    created: list = []
    monkeypatch.setattr(
        anthropic, "Anthropic", _make_recording_client(created, fail=False)
    )

    r = client.get("/healthz/llm")
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "anthropic"
    assert body["llm_ok"] is True
    assert body["detail"] == "ok"
    assert created, "probe never constructed the Anthropic client"
    assert created[0].closed is True, (
        "Issue #131 — the /healthz/llm Anthropic client must be closed "
        "after the probe (context-managed), not leaked per request."
    )
    monkeypatch.setattr(settings.graph_rag, "api_key", None, raising=True)


def test_anthropic_healthz_probe_closes_client_on_failure(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even when ``models.list()`` raises, the client must still be closed."""
    anthropic = pytest.importorskip("anthropic")
    monkeypatch.setenv("P2P_GRAPH_RAG_PROVIDER", "anthropic")
    monkeypatch.setenv("P2P_GRAPH_RAG_API_KEY", "sk-ant-fake")
    from app.config import settings
    from pydantic import SecretStr

    monkeypatch.setattr(
        settings.graph_rag, "api_key", SecretStr("sk-ant-fake"), raising=True
    )

    created: list = []
    monkeypatch.setattr(
        anthropic, "Anthropic", _make_recording_client(created, fail=True)
    )

    r = client.get("/healthz/llm")
    assert r.status_code == 200  # health probe never raises
    body = r.json()
    assert body["llm_ok"] is False
    assert "anthropic_probe_failed" in body["detail"]
    assert created and created[0].closed is True, (
        "client must be closed even when the probe call raises"
    )
    monkeypatch.setattr(settings.graph_rag, "api_key", None, raising=True)
