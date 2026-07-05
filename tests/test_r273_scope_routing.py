"""R273 — wrong-framework scope routing tests.

Pin the R273 routing invariant: queries about adjacent frameworks
(NEAR_OOS = DSA / NIS2 / CRA / PLD) and OTHER_REGULATION (GDPR / HIPAA
etc.) must NOT be routed to the ungrounded general assistant — doing so
caused hallucinated AI Act provisions (live: "Article 52a" on a VLOP
question).  These queries get the branded framework-pointer refusal instead.

Gap 1 from code_review_report_r268_r273.
"""
from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.config import settings
from app.integrations.regenold.scope import (
    ScopeReason,
    classify_scope,
)


# ── unit: classify_scope → NEAR_OOS / OTHER_REGULATION ──────────────────


@pytest.mark.parametrize(
    "question,expected_reason,expected_framework",
    [
        # DSA / VLOP → NEAR_OOS
        (
            "What are the transparency obligations for Very Large Online Platforms?",
            ScopeReason.NEAR_OOS,
            "Digital Services Act",
        ),
        # PLD → NEAR_OOS
        (
            "If AI causes property damage to a consumer, what is the AI-Act liability?",
            ScopeReason.NEAR_OOS,
            "Product Liability Directive",
        ),
        # NIS2 → NEAR_OOS
        (
            "What are the NIS2 cybersecurity obligations for essential entities?",
            ScopeReason.NEAR_OOS,
            "NIS2 Directive",
        ),
    ],
    ids=["dsa_vlop", "pld_liability", "nis2_essential"],
)
def test_near_oos_classify(
    question: str,
    expected_reason: ScopeReason,
    expected_framework: str,
) -> None:
    v = classify_scope(question)
    assert v.in_scope is False, f"Expected out-of-scope, got in_scope for: {question}"
    assert v.reason == expected_reason
    assert v.near_oos_framework == expected_framework


@pytest.mark.parametrize(
    "question",
    [
        "What does GDPR Article 17 say about the right to be forgotten?",
        "How does HIPAA apply to AI-powered medical devices?",
    ],
    ids=["gdpr", "hipaa"],
)
def test_other_regulation_classify(question: str) -> None:
    v = classify_scope(question)
    assert v.in_scope is False
    assert v.reason == ScopeReason.OTHER_REGULATION


# ── unit: _general_answer_reason_ok gate ─────────────────────────────────


def test_general_answer_reason_ok_blocks_near_oos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NEAR_OOS must be blocked from the general assistant by default."""
    monkeypatch.delenv("REGENOLD_WRONG_FRAMEWORK_GENERAL", raising=False)
    import app.routes.regenold as route_mod

    assert route_mod._general_answer_reason_ok(ScopeReason.NEAR_OOS) is False


def test_general_answer_reason_ok_blocks_other_regulation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OTHER_REGULATION must be blocked from the general assistant by default."""
    monkeypatch.delenv("REGENOLD_WRONG_FRAMEWORK_GENERAL", raising=False)
    import app.routes.regenold as route_mod

    assert route_mod._general_answer_reason_ok(ScopeReason.OTHER_REGULATION) is False


def test_general_answer_reason_ok_allows_conversational() -> None:
    """CONVERSATIONAL (benign off-topic) IS allowed to the general assistant."""
    import app.routes.regenold as route_mod

    assert route_mod._general_answer_reason_ok(ScopeReason.CONVERSATIONAL) is True


def test_override_env_restores_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REGENOLD_WRONG_FRAMEWORK_GENERAL=1 re-enables the pre-R273 routing."""
    monkeypatch.setenv("REGENOLD_WRONG_FRAMEWORK_GENERAL", "1")
    import app.routes.regenold as route_mod

    assert route_mod._general_answer_reason_ok(ScopeReason.NEAR_OOS) is True
    assert route_mod._general_answer_reason_ok(ScopeReason.OTHER_REGULATION) is True


# ── route-level: wrong-framework gets branded refusal, not general_assistant ─


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("REGENOLD_GRAPH_BACKEND", "embedded")
    monkeypatch.setenv("REGENOLD_SKIP_STARTUP_LOG", "1")
    # Ensure general-answer is ON so the test proves the routing block works
    # (if the gate weren't blocking, the general LLM would answer instead).
    monkeypatch.setenv("REGENOLD_GENERAL_ANSWER", "1")
    monkeypatch.delenv("REGENOLD_WRONG_FRAMEWORK_GENERAL", raising=False)
    settings.regenold.api_key = SecretStr("test-key")
    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


def _ask(client, question: str) -> dict:
    resp = client.post(
        "/api/v1/regenold/eu-ai-act/ask?include_reasoning=true",
        json=[{"role": "user", "content": question}],
        headers={"X-Regenold-Api-Key": "test-key"},
    )
    assert resp.status_code == 200
    return resp.json()


def test_route_near_oos_gets_branded_refusal(client) -> None:
    """A DSA/VLOP question must get the branded framework-pointer refusal,
    NOT the general assistant answer (which would hallucinate AI Act articles)."""
    body = _ask(client, "What are the transparency obligations for Very Large Online Platforms?")
    answer = body.get("answer", "")
    # Must mention the correct framework, not hallucinate AI Act content.
    assert "Digital Services Act" in answer
    # Must NOT have been routed to the general assistant.
    reasoning = body.get("reasoning", "")
    rpath = ""
    if isinstance(reasoning, str):
        try:
            rpath = json.loads(reasoning).get("retrieval_path", "")
        except (json.JSONDecodeError, TypeError):
            pass
    assert rpath != "general_assistant", (
        "NEAR_OOS query was routed to general_assistant — R273 routing block failed"
    )


def test_route_other_regulation_gets_branded_refusal(client) -> None:
    """A GDPR question must get the branded refusal, not the general assistant."""
    body = _ask(client, "What does GDPR Article 17 say about the right to be forgotten?")
    answer = body.get("answer", "")
    assert "outside the EU AI Act" in answer or "regulation outside" in answer.lower()
    # Must NOT have been routed to the general assistant.
    reasoning = body.get("reasoning", "")
    rpath = ""
    if isinstance(reasoning, str):
        try:
            rpath = json.loads(reasoning).get("retrieval_path", "")
        except (json.JSONDecodeError, TypeError):
            pass
    assert rpath != "general_assistant", (
        "OTHER_REGULATION query was routed to general_assistant — R273 routing block failed"
    )
