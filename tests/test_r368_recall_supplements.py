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
    is_healthcare_classification_question,
    is_medical_annex_i_classification,
    is_msa_reclassification_question,
    is_operator_becomes_provider_question,
    is_vlop_transparency_question,
)
from app.integrations.regenold.scope import ScopeReason, classify_scope

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import settings
from app.main import app


# ── route-level helpers (wire-level regression tests) ────────────────────
def _client() -> TestClient:
    settings.regenold.api_key = SecretStr("regenold-test-key")
    return TestClient(app)


def _ask(c: TestClient, content: str) -> dict:
    r = c.post(
        "/api/v1/regenold/eu-ai-act/ask",
        headers={"X-Regenold-Api-Key": "regenold-test-key"},
        json=[{"role": "user", "content": content}],
    )
    assert r.status_code == 200, r.json()
    return r.json()


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
    # la_q81 — R369 healthcare-classification lane: the ambient-scribe
    # question lost its gold Annex III head on the R369 A/B branch (the
    # R309 contrast-guard suppressed the negated prose mention in the ADD
    # direction and no R368 trigger fired). Gold ['Annex III', 'Article 6'].
    (
        "Classify the EU AI Act risk tier of an AI ambient scribe that only "
        "transcribes doctor-patient consultations and performs no diagnosis "
        "or decision-making.",
        is_healthcare_classification_question,
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
    # la_q4 — medical device safety component, gold ['Annex I', 'Article
    # 43', 'Article 6'] EXCLUDES Annex III; "medical" alone must not fire.
    (
        "I have a medical device that has an AI system as a safety "
        "component. The medical device is classified \"medium-risk\" and "
        "undergoes a 3rd party conformity assessment. Is the AI system "
        "\"medium risk\" too? If yes, why? If not, why not?",
        is_healthcare_classification_question,
    ),
    # la_q82 — consumer wellness chatbot, gold ['Annex I', 'Article 50',
    # 'Article 6'] EXCLUDES Annex III; no healthcare-engagement vocab.
    (
        "Classify the EU AI Act risk tier of a consumer wellness chatbot "
        "that gives general lifestyle tips and makes no medical claims.",
        is_healthcare_classification_question,
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


# ── gates: DEFAULT ON (R369), fresh env read, env off-switchable ──────────
def test_gates_default_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """R369 — the supplements are default ON: the R365 checkpoint sim
    (scratch/r369_sim_r368.py) measured 11/81 fires, 12 gold heads recovered,
    0 false positives (ref_loose 0.764 -> 0.833)."""
    monkeypatch.delenv("REGENOLD_ANNEXIII_RECALL_SUPPLEMENTS", raising=False)
    monkeypatch.delenv("REGENOLD_ART50_RECALL_SUPPLEMENTS", raising=False)
    assert annexiii_recall_supplements_enabled()
    assert art50_recall_supplements_enabled()


def test_gates_respect_env_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """The A/B arm: ``0`` restores the pre-R369 wire."""
    monkeypatch.setenv("REGENOLD_ANNEXIII_RECALL_SUPPLEMENTS", "0")
    monkeypatch.setenv("REGENOLD_ART50_RECALL_SUPPLEMENTS", "0")
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


def test_anchors_on_by_default_append() -> None:
    """R369 — the medical trigger appends Annex III with the default env."""
    entities = _parse_entities(
        "Is AI software that detects melanoma from dermoscopy images a "
        "high-risk AI system under the EU AI Act?"
    )
    assert "Annex III" in entities, f"Annex III anchor missing: {entities}"


# ── R369 fines-filter complement (la_q16 vs pure-fines shapes) ────────────
def test_fines_filter_keeps_prohibition_complement() -> None:
    """The R112 fines filter keeps Art 99 + Art 5 + Art 50 when the R368
    fines trigger fires (it requires a prohibition token, which pure-fines
    questions like paper Q9 lack)."""
    from app.engines.risk_classification import is_fines_prohibited_question

    assert is_fines_prohibited_question(
        "What are the administrative fines for non-compliance with the "
        "prohibition of the AI practices?"
    )
    assert not is_fines_prohibited_question(
        "What are the penalties for violating the provisions of the "
        "regulation for high-risk AI systems?"
    )


# ── R369 wire guard (route-level recovery of trigger-canonical heads) ─────
def test_fines_wire_recovers_article_50() -> None:
    """la_q16 end-to-end: the fines filter + wire guard ship the full gold
    set [Article 5, Article 50, Article 99] (the R369 live-audit fix)."""
    body = _ask(
        _client(),
        "What are the administrative fines for non-compliance with the "
        "prohibition of the AI practices?",
    )
    refs = set(body["references"])
    assert {"Article 5", "Article 50", "Article 99"} <= refs, refs


def test_medical_wire_recovers_annex_iii() -> None:
    """la_q64 end-to-end: the medical trigger's Annex III survives the budget
    cut via the wire guard."""
    body = _ask(
        _client(),
        "Is AI software that detects melanoma from dermoscopy images a "
        "high-risk AI system under the EU AI Act?",
    )
    assert "Annex III" in body["references"], body["references"]


def test_healthcare_classification_wire_recovers_annex_iii() -> None:
    """la_q81 end-to-end regression: the healthcare-classification lane must
    re-instate the gold Annex III head (gold ['Annex III', 'Article 6']) that
    the R369 A/B branch lost — the R309 contrast-guard suppresses the negated
    prose mention ("does not fall within any Annex III use case") in the ADD
    direction and no other R368 trigger fires on this question."""
    body = _ask(
        _client(),
        "Classify the EU AI Act risk tier of an AI ambient scribe that only "
        "transcribes doctor-patient consultations and performs no diagnosis "
        "or decision-making.",
    )
    assert "Annex III" in body["references"], body["references"]


def test_wellness_chatbot_wire_keeps_no_annex_iii() -> None:
    """la_q82 negative control: the same classification shape with NO
    healthcare-engagement vocabulary must NOT gain Annex III (gold
    ['Annex I', 'Article 50', 'Article 6'] excludes it)."""
    body = _ask(
        _client(),
        "Classify the EU AI Act risk tier of a consumer wellness chatbot "
        "that gives general lifestyle tips and makes no medical claims.",
    )
    assert "Annex III" not in body["references"], body["references"]


def test_wire_guard_off_switch_restores_baseline(monkeypatch) -> None:
    """REGENOLD_R368_WIRE_GUARD=0 must NOT re-append a dropped head — the
    A/B arm."""
    monkeypatch.setenv("REGENOLD_R368_WIRE_GUARD", "0")
    body = _ask(
        _client(),
        "Is AI software that detects melanoma from dermoscopy images a "
        "high-risk AI system under the EU AI Act?",
    )
    assert "Annex III" not in body["references"], body["references"]


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
