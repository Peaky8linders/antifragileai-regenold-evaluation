"""Unit tests for NLI DeBERTa Cross-Encoder citation verification in regenold router."""

from __future__ import annotations

import os
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from pydantic import SecretStr

client = TestClient(app)

def test_nli_verify_route_integration(monkeypatch):
    """Test that REGENOLD_NLI_VERIFY=1 triggers NLI scoring note in reasoning trace."""
    monkeypatch.setenv("REGENOLD_NLI_VERIFY", "1")
    monkeypatch.setenv("REGENOLD_SKIP_STARTUP_LOG", "1")
    
    # Configure eval auth key if needed
    settings.regenold.api_key = SecretStr("eval-key")

    response = client.post(
        "/api/v1/regenold/eu-ai-act/ask?include_reasoning=true",
        json={"question": "What are the obligations for high-risk AI systems under Article 9?"},
        headers={"X-Regenold-Api-Key": "eval-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "references" in data
    
    reasoning = data.get("reasoning")
    assert reasoning is not None
    assert "nli_verify_scored" in reasoning
