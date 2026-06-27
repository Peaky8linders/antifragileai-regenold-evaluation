"""Web UI routing + API-key non-leak guard.

After the Lexy sign-up funnel landed (R-signup), the funnel owns ``/``
and the interactive chat UI moved to ``/app``. This module verifies:
* ``/`` serves the funnel HTML and never leaks the partner key;
* ``/app`` serves the chat UI with an EMPTY key field (no leak);
* ``/info`` still serves the JSON descriptor (ui="/" + chat_ui="/app");
* the wire contract ``POST /api/v1/regenold/eu-ai-act/ask`` is undisturbed.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

_SENTINEL_KEY = "regenold-secret-key-DO-NOT-LEAK-12345"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_root_serves_funnel(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert "<!DOCTYPE html>" in body
    assert "Lexy" in body  # the funnel is branded Lexy
    assert 'id="signup-form"' in body  # it's the sign-up funnel, not the chat


def test_root_does_not_leak_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """The funnel HTML must NEVER contain the partner API key."""
    monkeypatch.setenv("P2P_REGENOLD_API_KEY", _SENTINEL_KEY)
    local_client = TestClient(app)
    body = local_client.get("/").text
    assert _SENTINEL_KEY not in body
    assert "{{API_KEY}}" not in body


def test_app_serves_chat_ui(client: TestClient) -> None:
    resp = client.get("/app")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert "<!DOCTYPE html>" in body
    assert "Lexy" in body
    # The chat ships an EMPTY key field (no leak); the funnel-issued key
    # arrives via the #key= fragment into localStorage.
    assert 'id="cfg-api-key" class="form-input" value=""' in body


def test_app_does_not_leak_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("P2P_REGENOLD_API_KEY", _SENTINEL_KEY)
    local_client = TestClient(app)
    body = local_client.get("/app").text
    assert _SENTINEL_KEY not in body
    assert "{{API_KEY}}" not in body


def test_info_endpoint_serves_json(client: TestClient) -> None:
    resp = client.get("/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "regenold-eu-ai-act-rag"
    assert data["ask_endpoint"] == "/api/v1/regenold/eu-ai-act/ask"
    assert data["ui"] == "/"
    assert data["chat_ui"] == "/app"
    assert data["signup_endpoint"] == "/api/v1/regenold/auth/signup"


def test_avatar_route_registered(client: TestClient) -> None:
    # The avatar PNG may or may not be present on disk in CI, but the
    # route must be registered (not a 404 from a missing handler).
    resp = client.get("/lexy_avatar.png")
    assert resp.status_code != 404


def test_ask_contract_unchanged(client: TestClient) -> None:
    """The wire contract must still return {answer, references, reasoning}."""
    from pydantic import SecretStr

    from app.config import settings

    settings.regenold.api_key = SecretStr("regenold-test-key")
    resp = client.post(
        "/api/v1/regenold/eu-ai-act/ask",
        headers={"X-Regenold-Api-Key": "regenold-test-key"},
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "What are the obligations of providers of high-risk AI systems?",
                }
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "references" in data
    assert "reasoning" in data
