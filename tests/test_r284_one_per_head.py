import pytest
import os
from app.routes.regenold import adaptive_ref_clamp

def test_adaptive_ref_clamp_one_per_head_disabled(monkeypatch) -> None:
    monkeypatch.setenv("REGENOLD_ONE_PER_HEAD_CAP", "0")
    monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
    
    # Check that duplicates under the same head are not capped when the env-var is "0"
    refs = ["Article 6.1", "Article 6.2", "Annex III.1", "Annex III.2"]
    res = adaptive_ref_clamp(
        refs,
        budget=10,
        is_scenario_budget=False,
        live_question="Is this system high-risk under Article 6?",
        stage2_landed=True,
        curated_intercept=False,
        retrieval_path="standard",
    )
    assert res == refs

def test_adaptive_ref_clamp_one_per_head_enabled(monkeypatch) -> None:
    monkeypatch.setenv("REGENOLD_ONE_PER_HEAD_CAP", "1")
    monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
    
    # Capping keeps only the first occurrence for each unique head
    refs = ["Article 6.1", "Article 6.2", "Annex III.1", "Annex III.2", "Article 50", "Article 50.1"]
    res = adaptive_ref_clamp(
        refs,
        budget=10,
        is_scenario_budget=False,
        live_question="Is this system high-risk under Article 6?",
        stage2_landed=True,
        curated_intercept=False,
        retrieval_path="standard",
    )
    assert res == ["Article 6.1", "Annex III.1", "Article 50"]

def test_adaptive_ref_clamp_one_per_head_no_head_fallback(monkeypatch) -> None:
    monkeypatch.setenv("REGENOLD_ONE_PER_HEAD_CAP", "1")
    monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
    
    # If head is None, the ref itself is the head
    refs = ["Recital 27", "Recital 27", "Article 6.1"]
    res = adaptive_ref_clamp(
        refs,
        budget=10,
        is_scenario_budget=False,
        live_question="Is this system high-risk under Article 6?",
        stage2_landed=True,
        curated_intercept=False,
        retrieval_path="standard",
    )
    assert res == ["Recital 27", "Article 6.1"]

def test_adaptive_ref_clamp_one_per_head_respects_stage2_landed(monkeypatch) -> None:
    monkeypatch.setenv("REGENOLD_ONE_PER_HEAD_CAP", "1")
    monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
    
    # Capping is skipped if stage2_landed is False
    refs = ["Article 6.1", "Article 6.2"]
    res = adaptive_ref_clamp(
        refs,
        budget=10,
        is_scenario_budget=False,
        live_question="Is this system high-risk under Article 6?",
        stage2_landed=False,
        curated_intercept=False,
        retrieval_path="standard",
    )
    assert res == refs


def test_adaptive_ref_clamp_one_per_head_unbiased_prefixes(monkeypatch) -> None:
    monkeypatch.setenv("REGENOLD_ONE_PER_HEAD_CAP", "1")
    monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
    
    # Capping works across different prefix styles (Art., Article, Ann., Annex, Recital)
    refs = [
        "Art. 6.1", "Art. 6.2",
        "Ann. III.1", "Ann. III.2",
        "Recital 27.1", "Recital 27.2",
        "Article 50.1", "Article 50.2"
    ]
    res = adaptive_ref_clamp(
        refs,
        budget=10,
        is_scenario_budget=False,
        live_question="Is this system high-risk?",
        stage2_landed=True,
        curated_intercept=False,
        retrieval_path="standard",
    )
    assert res == ["Art. 6.1", "Ann. III.1", "Recital 27.1", "Article 50.1"]

