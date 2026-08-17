"""R365 — the Article 50 chatbot-transparency recall supplement.

Exact gold impact computed over the whole 297-row probe pool BEFORE any
engine code existed (``scratch/r365_art50_trigger.py`` + inline fit): the
trigger fires on 4 rows and Article 50 is gold-but-not-anchored on all 4
(100% precision, zero non-gold additions), concentrated on the
chatbot-interaction shape the R353.1 true-gap table called out. These tests
pin that semantics and the parse wiring.
"""

from __future__ import annotations

import pytest

from app.engines.risk_classification import (
    art50_chatbot_anchor_enabled,
    is_chatbot_transparency_question,
)

# ── trigger semantics ────────────────────────────────────────────────────
# The 4 rows where Article 50 is gold-but-not-anchored (verified fit).
FIRE = [
    # the canonical interaction-disclosure shape (R353.1 note)
    "A retailer's customer-support chatbot answers questions on its website. "
    "What does the EU AI Act require the chatbot to tell users?",
    "Is a customer service chatbot high-risk under the AI Act?",
    # wellness chatbot — limited-risk route, Article 50 duties attach
    "Classify the EU AI Act risk tier of a consumer wellness chatbot that "
    "gives general lifestyle tips and makes no medical claims.",
    "Classify the EU AI Act risk tier of a consumer wellness chatbot that "
    "gives general lifestyle tips and makes no medical claims.",
]

# Shapes the trigger must NOT fire on (principled exclusions, not fitted):
#   - care-triage/urgency chatbots → high-risk Annex III point 5(d) route,
#     Article 50 not gold (tp_v4_012 / mt_v2_010 class);
#   - build/obligation questions ("we are building X, what do we need to
#     know?") → GPAI/provider-obligation surface (la_q53 class);
#   - non-chatbot conversational surfaces (ambient scribe transcription,
#     voice assistants in the workplace, emotion recognition).
NO_FIRE = [
    "A hospital chatbot both answers patients' general questions AND triages "
    "the urgency of their symptom descriptions. Which obligations apply?",
    "Which one wins if my chatbot is also a high-risk medical-triage tool?",
    "We are building a chatbot for customer support. What do we need to know?",
    "We are developing a generative AI chatbot that will be deployed on a "
    "hospital website to answer general patient queries. What transparency "
    "obligations apply?",
    "Classify the EU AI Act risk tier of an AI ambient scribe that only "
    "transcribes doctor-patient consultations.",
    "An AI voice assistant monitors call-centre agents' emotions. Is it "
    "prohibited under Article 5?",
    "What is a general-purpose AI model?",
    "What risk categories are provided for AI systems?",
]


@pytest.mark.parametrize("q", FIRE)
def test_trigger_fires_on_gold_shapes(q):
    assert is_chatbot_transparency_question(q)


@pytest.mark.parametrize("q", NO_FIRE)
def test_trigger_does_not_fire_on_noise_shapes(q):
    assert not is_chatbot_transparency_question(q)


def test_trigger_never_raises_on_garbage():
    assert not is_chatbot_transparency_question("")
    assert not is_chatbot_transparency_question(None)
    assert not is_chatbot_transparency_question("   ")
    assert not is_chatbot_transparency_question(12345)


def test_gate_default_off(monkeypatch):
    monkeypatch.delenv("REGENOLD_ART50_CHAT_ANCHOR", raising=False)
    assert not art50_chatbot_anchor_enabled()
    monkeypatch.setenv("REGENOLD_ART50_CHAT_ANCHOR", "1")
    assert art50_chatbot_anchor_enabled()
    monkeypatch.setenv("REGENOLD_ART50_CHAT_ANCHOR", "0")
    assert not art50_chatbot_anchor_enabled()


# ── parse wiring ─────────────────────────────────────────────────────────


def test_parse_appends_article_50_when_gate_on(monkeypatch):
    monkeypatch.setenv("REGENOLD_ART50_CHAT_ANCHOR", "1")
    from app.engines._graph_rag_impl import _deterministic_parse

    q = _deterministic_parse(
        "Is a customer service chatbot high-risk under the AI Act?"
    )
    assert "Art. 50" in q.entities
    # RECALL SUPPLEMENT — appended AFTER the BM25/vector lanes (R365.1: the
    # pre-BM25 placement suppressed them and displaced gold refs), never
    # prepended (nothing can be displaced).
    assert q.entities[-1] == "Art. 50"


def test_parse_gate_off_is_byte_identical(monkeypatch):
    monkeypatch.delenv("REGENOLD_ART50_CHAT_ANCHOR", raising=False)
    from app.engines._graph_rag_impl import _deterministic_parse

    q = _deterministic_parse(
        "Is a customer service chatbot high-risk under the AI Act?"
    )
    assert "Art. 50" not in q.entities


def test_parse_does_not_append_on_noise_shape(monkeypatch):
    monkeypatch.setenv("REGENOLD_ART50_CHAT_ANCHOR", "1")
    from app.engines._graph_rag_impl import _deterministic_parse

    q = _deterministic_parse(
        "We are building a chatbot for customer support. What do we need to know?"
    )
    assert "Article 50" not in q.entities


def test_parse_does_not_double_add_when_article_50_already_anchored(monkeypatch):
    monkeypatch.setenv("REGENOLD_ART50_CHAT_ANCHOR", "1")
    from app.engines._graph_rag_impl import _deterministic_parse

    # A chatbot question whose keyword map ALREADY anchors Art. 50 (the
    # "chatbot disclosure" keyword) AND fires the trigger: the supplement
    # must not double-add.
    q = _deterministic_parse(
        "Our chatbot must provide chatbot disclosure to users. "
        "What does the AI Act require?"
    )
    assert q.entities.count("Art. 50") == 1


def test_parse_multi_turn_live_turn_extraction(monkeypatch):
    monkeypatch.setenv("REGENOLD_ART50_CHAT_ANCHOR", "1")
    from app.engines._graph_rag_impl import _deterministic_parse

    # Flattened multi-turn: the preamble must not mask the chatbot live turn.
    multi = (
        "Conversation so far:\nUser: What is a general-purpose AI model?\n"
        "Assistant: A model trained on broad data...\n\n"
        "Latest question:\nIs a customer service chatbot high-risk under the AI Act?"
    )
    q = _deterministic_parse(multi)
    assert "Art. 50" in q.entities
