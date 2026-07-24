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


def test_nli_label_index_resolution():
    """Test that _resolve_entail_index dynamically handles MoritzLaurer and standard checkpoints."""
    from app.engines.crag_nli_verifier import NLIEntailmentScorer

    class MockModelMoritzLaurer:
        class Config:
            id2label = {0: "entailment", 1: "neutral", 2: "contradiction"}
        config = Config()

    class MockModelStandard:
        class Config:
            id2label = {0: "contradiction", 1: "entailment", 2: "neutral"}
        config = Config()

    idx_moritz = NLIEntailmentScorer._resolve_entail_index(MockModelMoritzLaurer(), 1)
    assert idx_moritz == 0, f"Expected 0 for MoritzLaurer model, got {idx_moritz}"

    idx_std = NLIEntailmentScorer._resolve_entail_index(MockModelStandard(), 1)
    assert idx_std == 1, f"Expected 1 for standard model, got {idx_std}"


def test_crag_relative_cutoff_and_floor():
    """Test that CragThresholds with relative_cutoff and floor preserves top citations and respects floor."""
    from app.engines.crag_nli_verifier import CragThresholds

    thresh = CragThresholds(keep=0.1, relative_cutoff=0.30, floor=2)
    assert thresh.keep == 0.1
    assert thresh.relative_cutoff == 0.30
    assert thresh.floor == 2

