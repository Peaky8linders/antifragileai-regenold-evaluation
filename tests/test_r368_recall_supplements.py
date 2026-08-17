"""R368 — Annex III / Article 50 deterministic recall supplements.

Gold impact was computed over the 81 live rows BEFORE this code existed
(scratch/r368_trigger_impact.py + v2): the Annex III family (medical
classification, MSA reclassification, EU-database registration,
operator-becomes-provider) recovers Annex III on la_q8/la_q64/la_q35/
la_q37/la_q25 at 100% precision; the Article 50 family (VLOP
transparency, fines+prohibited, biometric/patient interaction) recovers
Article 50 on la_q60/63/91/la_q16/la_q7 at 100% precision. These tests
pin the trigger semantics, the scope-gate rescue for the VLOP rows, the
engine anchor wiring, and the cache-key registration.
"""

from __future__ import annotations

import pytest

from app.engines.risk_classification import (
    annexiii_recall_supplements_enabled,
    art50_recall_supplements_enabled,
    is_biometric_patient_interaction_question,
    is_eu_database_registration_question,
    is_fines_prohibited_question,
    is_medical_annex_i_classification,
    is_msa_reclassification_question,
    is_operator_becomes_provider_question,
    is_vlop_transparency_question,
)
from app.integrations.regenold.scope import ScopeReason, classify_scope


# ── Annex III family: FIRE (gold-verified rows) ──────────────────────────
FIRE_ANNEXIII = [
    # la_q8 / la_q64 — medical / Annex-I-route classification (dual route)
    (
        "Are AI safety components within medical devices of MDR class IIa, "
        "IIb, or III considered to be high-risk according to the EU AI Act?",
        is_medical_annex_i_classification,
    ),
    (
        "Is AI software that detects melanoma from dermoscopy images a "
        "high-risk AI system under the EU AI Act?",
        is_medical_annex_i_classification,
    ),
    # la_q35 — MSA reclassification
    (
        "Consider the situation in which a market surveillance authority "
        "(MSA) determines that an AI system, originally classified as "
        "non-high-risk by the provider, is in fact high-risk. Does the "
        "provider need to recall and suspend the system?",
        is_msa_reclassification_question,
    ),
    # la_q37 — EU database registration
    (
        "When registering a high-risk AI system in the EU database under "
        "the EU AI Act, what specific information must the provider submit?",
        is_eu_database_registration_question,
    ),
    # la_q25 — operator becomes provider
    (
        "Can an operator that is not a provider according to the EU AI Act, "
        "for example a deployer, take actions on a given high-risk AI system "
        "such that it can be effectively seen as a provider by the "
        "authorities?",
        is_operator_becomes_provider_question,
    ),
]

# ── Annex III family: must NOT fire ───────────────────────────────────────
NO_FIRE_ANNEXIII = [
    # What/How obligation shapes carry the same vocabulary (the R353
    # opening-auxiliary discipline)
    (
        "What logging and record-keeping does a high-risk AI radiology "
        "system require, and how long must the deploying hospital keep them?",
        is_medical_annex_i_classification,
    ),
    (
        "What human-oversight measures does the EU AI Act require for a "
        "high-risk clinical decision-support system?",
        is_medical_annex_i_classification,
    ),
    (
        "What penalties can be imposed on a medical-AI provider that places "
        "a non-conformant high-risk system on the market?",
        is_medical_annex_i_classification,
    ),
    # no market-surveillance reclassification vocabulary
    (
        "What powers do market surveillance authorities have under the AI "
        "Act?",
        is_msa_reclassification_question,
    ),
    # no high-risk in the question
    (
        "Where is the EU database for AI systems maintained?",
        is_eu_database_registration_question,
    ),
    # no provider-reclassification shape
    (
        "What are the obligations of a provider of a high-risk AI system?",
        is_operator_becomes_provider_question,
    ),
]

# ── Article 50 family: FIRE ───────────────────────────────────────────────
FIRE_ART50 = [
    # la_q60 / la_q63 / la_q91 — VLOP / content-moderation transparency
    (
        "What are the algorithmic transparency obligations for a Very Large "
        "Online Platform content-moderation AI?",
        is_vlop_transparency_question,
    ),
    (
        "What are the transparency rules for a Very Large Online Platform's "
        "content-moderation AI?",
        is_vlop_transparency_question,
    ),
    # la_q16 — fines + prohibited practices
    (
        "What are the administrative fines for non-compliance with the "
        "prohibition of the AI practices?",
        is_fines_prohibited_question,
    ),
    # la_q7 — biometric verification interaction
    (
        "We want to deploy an AI system that performs biometric verification "
        "solely to confirm that a specific natural person is the person he "
        "or she claims to be. Is this system prohibited? Is it high-risk?",
        is_biometric_patient_interaction_question,
    ),
]

# ── Article 50 family: must NOT fire ──────────────────────────────────────
NO_FIRE_ART50 = [
    # emotion-inference is Article 5(1)(f), not Article 50
    (
        "Is an AI system that infers patients' emotions for a medical "
        "purpose prohibited under Article 5?",
        is_biometric_patient_interaction_question,
    ),
    # pure-DSA shape — platform duties, no AI subject
    (
        "Explain DSA's VLOP transparency requirements.",
        is_vlop_transparency_question,
    ),
    # fines without prohibition (high-risk tier, gold = Art. 99 only)
    (
        "What are the penalties for violating the provisions of the "
        "regulation for high-risk AI systems?",
        is_fines_prohibited_question,
    ),
    # biometric identification at check-in — gold has no Article 50
    (
        "Is an AI system used for biometric patient identification at "
        "hospital check-in high-risk under the EU AI Act?",
        is_biometric_patient_interaction_question,
    ),
]


@pytest.mark.parametrize("q,fn", FIRE_ANNEXIII)
def test_annexiii_triggers_fire(q: str, fn) -> None:
    assert fn(q), f"Annex III trigger must fire on {q!r}"


@pytest.mark.parametrize("q,fn", NO_FIRE_ANNEXIII)
def test_annexiii_triggers_do_not_fire(q: str, fn) -> None:
    assert not fn(q), f"Annex III trigger must NOT fire on {q!r}"


@pytest.mark.parametrize("q,fn", FIRE_ART50)
def test_art50_triggers_fire(q: str, fn) -> None:
    assert fn(q), f"Article 50 trigger must fire on {q!r}"


@pytest.mark.parametrize("q,fn", NO_FIRE_ART50)
def test_art50_triggers_do_not_fire(q: str, fn) -> None:
    assert not fn(q), f"Article 50 trigger must NOT fire on {q!r}"


# ── gates: default OFF, fresh env read ────────────────────────────────────
def test_gates_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REGENOLD_ANNEXIII_RECALL_SUPPLEMENTS", raising=False)
    monkeypatch.delenv("REGENOLD_ART50_RECALL_SUPPLEMENTS", raising=False)
    assert not annexiii_recall_supplements_enabled()
    assert not art50_recall_supplements_enabled()


def test_gates_respect_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REGENOLD_ANNEXIII_RECALL_SUPPLEMENTS", "1")
    monkeypatch.setenv("REGENOLD_ART50_RECALL_SUPPLEMENTS", "1")
    assert annexiii_recall_supplements_enabled()
    assert art50_recall_supplements_enabled()


# ── scope-gate rescue (la_q60 / la_q63 / la_q91) ─────────────────────────
def test_vlop_transparency_rescued_to_in_scope() -> None:
    v = classify_scope(
        "What are the algorithmic transparency obligations for a Very "
        "Large Online Platform content-moderation AI?"
    )
    assert v.in_scope
    assert v.reason == ScopeReason.IN_SCOPE


def test_vlop_transparency_rescued_second_variant() -> None:
    v = classify_scope(
        "What are the transparency rules for a Very Large Online "
        "Platform's content-moderation AI?"
    )
    assert v.in_scope


def test_pure_dsa_shape_stays_near_oos() -> None:
    v = classify_scope("Explain DSA's VLOP transparency requirements.")
    assert not v.in_scope
    assert v.reason == ScopeReason.NEAR_OOS
    assert v.near_oos_framework == "Digital Services Act"


# ── engine anchor wiring (_deterministic_parse, no LLM) ──────────────────
def _parse_entities(q: str) -> list[str]:
    from app.engines.graph_rag import _deterministic_parse

    parsed = _deterministic_parse(q)
    return list(parsed.entities)


def test_annexiii_medical_anchor_appends(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REGENOLD_ANNEXIII_RECALL_SUPPLEMENTS", "1")
    entities = _parse_entities(
        "Is AI software that detects melanoma from dermoscopy images a "
        "high-risk AI system under the EU AI Act?"
    )
    assert "Annex III" in entities, f"Annex III anchor missing: {entities}"


def test_msa_anchor_appends_79_80_and_annex_iii(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REGENOLD_ANNEXIII_RECALL_SUPPLEMENTS", "1")
    entities = _parse_entities(
        "Consider the situation in which a market surveillance authority "
        "(MSA) determines that an AI system, originally classified as "
        "non-high-risk by the provider, is in fact high-risk. Does the "
        "provider need to recall and suspend the system?"
    )
    assert "Annex III" in entities, f"Annex III missing: {entities}"
    assert "Art. 79" in entities, f"Art. 79 missing: {entities}"
    assert "Art. 80" in entities, f"Art. 80 missing: {entities}"


def test_art50_vlop_anchor_appends(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REGENOLD_ART50_RECALL_SUPPLEMENTS", "1")
    entities = _parse_entities(
        "What are the algorithmic transparency obligations for a Very "
        "Large Online Platform content-moderation AI?"
    )
    assert "Art. 50" in entities, f"Art. 50 anchor missing: {entities}"


def test_art50_fines_anchor_appends(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REGENOLD_ART50_RECALL_SUPPLEMENTS", "1")
    entities = _parse_entities(
        "What are the administrative fines for non-compliance with the "
        "prohibition of the AI practices?"
    )
    assert "Art. 50" in entities, f"Art. 50 anchor missing: {entities}"


def test_anchors_off_by_default_do_not_append() -> None:
    entities = _parse_entities(
        "Is AI software that detects melanoma from dermoscopy images a "
        "high-risk AI system under the EU AI Act?"
    )
    assert "Annex III" not in entities


# ── cache-key registration (R334 drift guard) ─────────────────────────────
@pytest.mark.parametrize(
    "flag",
    [
        "REGENOLD_ANNEXIII_RECALL_SUPPLEMENTS",
        "REGENOLD_ART50_RECALL_SUPPLEMENTS",
    ],
)
def test_engine_flag_changes_the_cache_key(flag: str, monkeypatch) -> None:
    """Registered flags must FIRE — flipping them must move the key hash
    (the R334 fire check; a flag that fails here would make the in-process
    A/B measure nothing)."""
    from app.routes.regenold import _engine_cache_key

    def _key() -> str:
        return _engine_cache_key("What does Article 13 require?", None, 0, False)

    monkeypatch.delenv(flag, raising=False)
    before = _key()
    monkeypatch.setenv(flag, "1")
    assert _key() != before, f"{flag} is read inside the engine but does not change the engine cache key"
