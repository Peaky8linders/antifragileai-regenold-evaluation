"""R353 — the R352 surviving hypothesis: Annex III on the yes/no
"is X high-risk / regulated under the AI Act?" shape.

The trigger was FITTED against the whole 297-row probe pool before any
engine code existed (see ``app/engines/risk_classification.py`` module
docstring and ``scratch/verify_r352_final.py``): 13 fired rows, Annex III
gold-but-missing on 7, zero non-gold additions after the prohibition
exclusion. These tests pin that semantics and the parse wiring.
"""

from __future__ import annotations

import pytest

from app.engines.risk_classification import (
    annex_iii_risk_class_anchor_enabled,
    is_yes_no_risk_classification,
)

# ── trigger semantics ────────────────────────────────────────────────────
# The 7 rows where Annex III is gold-but-not-anchored (verified fit).
FIRE = [
    "Is an AI spam filter regulated under the AI Act?",
    "Is a music recommendation AI high-risk under the AI Act?",
    "Is a customer service chatbot high-risk under the AI Act?",
    "Is a translation AI high-risk under the AI Act?",
    "Is an AI image generator high-risk under the AI Act?",
    "Is an AI system used to schedule administrative appointments in a clinic "
    "fall under the high-risk classification?",
    "Is an AI system that recommends recipes high risk?",
]

# Shapes the trigger must NOT fire on (the R352 refutation's edge classes).
NO_FIRE = [
    # prohibition questions — gold is Art. 5, never Annex III (R352 §3)
    "Are subliminal or manipulative AI techniques prohibited?",
    "Are deceptive or manipulative AI systems prohibited under the AI Act?",
    "Is untargeted scraping or harvesting of facial images prohibited?",
    "Is social scoring prohibited or high-risk under the AI Act?",
    # technical-documentation questions — "high-risk" describes the system
    "Does the technical documentation of a high-risk AI system require to "
    "provide specifications regarding the required hardware?",
    "Does the EU AI Act explicitly requires to use explainable AI techniques "
    "such as LIME or SHAP to increase the trustworthiness of high-risk AI "
    "systems?",
    # medical-device route — Annex I, not Annex III
    "Is AI software that detects melanoma from dermoscopy images a high-risk "
    "AI system under the EU AI Act?",
    "Are AI safety components within medical devices of MDR class IIa, IIb, "
    "or III considered to be high-risk according to the EU AI Act?",
    # list/definition shapes
    "Which AI systems used in education or vocational training should be "
    "classified as high-risk according to the EU AI Act?",
    "What risk categories are provided for AI systems?",
    "What is the definition of high risk?",
    # already-anchored rows (Annex III in the question text — the regex
    # anchor handles them; the supplement must not double-add)
    "Is a recruitment or hiring AI high-risk under the AI Act?",
]


@pytest.mark.parametrize("q", FIRE)
def test_trigger_fires_on_gold_shapes(q):
    assert is_yes_no_risk_classification(q)


@pytest.mark.parametrize("q", NO_FIRE)
def test_trigger_does_not_fire_on_noise_shapes(q):
    assert not is_yes_no_risk_classification(q)


def test_trigger_never_raises_on_garbage():
    assert not is_yes_no_risk_classification("")
    assert not is_yes_no_risk_classification(None)
    assert not is_yes_no_risk_classification("   ")
    assert not is_yes_no_risk_classification(12345)


def test_gate_default_off(monkeypatch):
    monkeypatch.delenv("REGENOLD_RISK_CLASS_ANNEX", raising=False)
    assert not annex_iii_risk_class_anchor_enabled()
    monkeypatch.setenv("REGENOLD_RISK_CLASS_ANNEX", "1")
    assert annex_iii_risk_class_anchor_enabled()
    monkeypatch.setenv("REGENOLD_RISK_CLASS_ANNEX", "0")
    assert not annex_iii_risk_class_anchor_enabled()


# ── parse wiring ─────────────────────────────────────────────────────────


def test_parse_appends_annex_iii_when_gate_on(monkeypatch):
    monkeypatch.setenv("REGENOLD_RISK_CLASS_ANNEX", "1")
    from app.engines._graph_rag_impl import _deterministic_parse

    q = _deterministic_parse("Is a customer service chatbot high-risk under the AI Act?")
    assert "Annex III" in q.entities
    # RECALL SUPPLEMENT — appended, never prepended (nothing can be displaced).
    assert q.entities[-1] == "Annex III"


def test_parse_gate_off_is_byte_identical(monkeypatch):
    monkeypatch.delenv("REGENOLD_RISK_CLASS_ANNEX", raising=False)
    from app.engines._graph_rag_impl import _deterministic_parse

    q = _deterministic_parse("Is a customer service chatbot high-risk under the AI Act?")
    assert "Annex III" not in q.entities


def test_parse_does_not_append_on_noise_shape(monkeypatch):
    monkeypatch.setenv("REGENOLD_RISK_CLASS_ANNEX", "1")
    from app.engines._graph_rag_impl import _deterministic_parse

    q = _deterministic_parse(
        "Are deceptive or manipulative AI systems prohibited under the AI Act?"
    )
    assert "Annex III" not in q.entities


def test_parse_does_not_double_add_when_question_names_annex_iii(monkeypatch):
    monkeypatch.setenv("REGENOLD_RISK_CLASS_ANNEX", "1")
    from app.engines._graph_rag_impl import _deterministic_parse

    q = _deterministic_parse(
        "Is a recruitment or hiring AI high-risk under the AI Act?"
    )
    assert q.entities.count("Annex III") == 1


def test_parse_multi_turn_live_turn_extraction(monkeypatch):
    monkeypatch.setenv("REGENOLD_RISK_CLASS_ANNEX", "1")
    from app.engines._graph_rag_impl import _deterministic_parse

    # Flattened multi-turn: the preamble must not mask the yes/no live turn.
    multi = (
        "Conversation so far:\nUser: What is a general-purpose AI model?\n"
        "Assistant: A model trained on broad data...\n\n"
        "Latest question:\nIs a customer service chatbot high-risk under the AI Act?"
    )
    q = _deterministic_parse(multi)
    assert "Annex III" in q.entities


# ── cache-key registration (the R334 drift guard is the enforcer) ────────


def test_flag_registered_in_engine_cache_key():
    """Flipping the gate must change the engine cache identity (R263.2)."""
    from app.routes.regenold import _engine_cache_key

    _Q = "Is a customer service chatbot high-risk under the AI Act?"
    import os

    os.environ.pop("REGENOLD_RISK_CLASS_ANNEX", None)
    k_off = _engine_cache_key(_Q, None, 0, False)
    os.environ["REGENOLD_RISK_CLASS_ANNEX"] = "1"
    k_on = _engine_cache_key(_Q, None, 0, False)
    os.environ.pop("REGENOLD_RISK_CLASS_ANNEX", None)
    assert k_off != k_on
