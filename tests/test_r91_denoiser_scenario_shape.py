"""R91 / Bug 3 — denoiser must not drop the "We are a {role}..." opener.

When a prior turn carries the scenario opener but the LLM rewrite
flattens it into a QA-shape, ``_build_question_from_history`` must
fall back to the concatenation path so the original first-person
prose is preserved in the history block. Otherwise downstream
scenario gates (graphrag_expand.should_expand_for_question, R72
_reconcile_references_to_prose guard) misfire because they only see
the final ``question`` string.
"""

from __future__ import annotations

from unittest.mock import patch

from app.integrations.regenold.models import RegenoldChatMessage
from app.routes.regenold import (
    _build_question_from_history,
    _looks_like_scenario_shape,
)


# ---------------------------------------------------------------------------
# 1. Scenario in prior + denoiser drops shape → fall back to concatenation
# ---------------------------------------------------------------------------


def test_scenario_in_prior_denoiser_drops_shape_falls_back() -> None:
    """Prior turn opens with "We are a deployer...", LLM rewrite drops it.

    The final ``question`` must STILL match ``_looks_like_scenario_shape``
    because the fallback concatenation path keeps the original
    first-person prose in the history block.
    """
    msgs = [
        RegenoldChatMessage(
            role="user",
            content=(
                "We are a deployer offering an HR system that screens "
                "candidates for hiring. How does Article 26 apply to us?"
            ),
        ),
        RegenoldChatMessage(
            role="assistant",
            content="Article 26 obligations apply to deployers.",
        ),
        RegenoldChatMessage(
            role="user",
            content="What about the logging requirements?",
        ),
    ]
    # Denoiser returns a QA-form rewrite that drops the "We are a" opener.
    with patch(
        "app.routes.regenold._rewrite_multiturn_query",
        return_value="What are the logging requirements for Article 26 deployers?",
    ):
        question, _ = _build_question_from_history(msgs)

    # Final question must STILL match scenario shape (it's preserved in
    # the history block via the fallback concatenation path).
    assert _looks_like_scenario_shape(question), (
        f"Scenario shape was dropped by denoiser AND not rescued by "
        f"fallback. Question:\n{question!r}"
    )
    # The denoised rewrite was rejected — verify the rewrite text is NOT
    # the sole content (concatenation path emits "Conversation so far:").
    assert "Conversation so far:" in question


# ---------------------------------------------------------------------------
# 2. Scenario in prior + denoiser preserves shape → accept rewrite
# ---------------------------------------------------------------------------


def test_scenario_in_prior_denoiser_preserves_shape_accepted() -> None:
    """When the denoiser keeps the scenario opener, accept the rewrite.

    The final ``question`` matches ``_looks_like_scenario_shape`` AND
    the denoised text appears verbatim (no fallback concatenation).
    """
    msgs = [
        RegenoldChatMessage(
            role="user",
            content=(
                "We are a deployer offering an HR system. "
                "How does Article 26 apply?"
            ),
        ),
        RegenoldChatMessage(
            role="assistant",
            content="Article 26 sets deployer obligations.",
        ),
        RegenoldChatMessage(
            role="user",
            content="And the logging?",
        ),
    ]
    preserved = "We are a deployer asking about Article 26 logging obligations"
    with patch(
        "app.routes.regenold._rewrite_multiturn_query",
        return_value=preserved,
    ):
        question, _ = _build_question_from_history(msgs)

    assert _looks_like_scenario_shape(question), (
        f"Denoiser preserved the opener but the gate rejected it. "
        f"Question:\n{question!r}"
    )
    assert preserved in question, (
        f"Denoised text not present — fallback fired unexpectedly. "
        f"Question:\n{question!r}"
    )
    # Concatenation path did NOT fire.
    assert "Conversation so far:" not in question


# ---------------------------------------------------------------------------
# 3. No scenario shape anywhere → denoiser rewrite accepted as-is (R86)
# ---------------------------------------------------------------------------


def test_no_scenario_shape_denoiser_accepted_unchanged() -> None:
    """Pure QA multi-turn — denoiser rewrite is accepted (R86 behaviour)."""
    msgs = [
        RegenoldChatMessage(
            role="user",
            content="What does Article 13 require?",
        ),
        RegenoldChatMessage(
            role="assistant",
            content="Article 13 mandates transparency to deployers.",
        ),
        RegenoldChatMessage(
            role="user",
            content="And for what time period must records be kept?",
        ),
    ]
    rewrite = "Article 13 record retention period for transparency requirements"
    with patch(
        "app.routes.regenold._rewrite_multiturn_query",
        return_value=rewrite,
    ):
        question, _ = _build_question_from_history(msgs)

    assert not _looks_like_scenario_shape(question)
    assert rewrite in question
    # The R86 lift on QA-shape rows is preserved — concatenation did
    # NOT fire.
    assert "Conversation so far:" not in question


# ---------------------------------------------------------------------------
# 4. Denoiser returns None → concatenation fallback fires (regression guard)
# ---------------------------------------------------------------------------


def test_denoiser_returns_none_falls_back_to_concatenation() -> None:
    """When the denoiser bails (returns None), the existing R86 fallback
    concatenation path fires unchanged.
    """
    msgs = [
        RegenoldChatMessage(
            role="user",
            content="What does Article 13 require?",
        ),
        RegenoldChatMessage(
            role="assistant",
            content="Article 13 mandates transparency.",
        ),
        RegenoldChatMessage(
            role="user",
            content="And for deployers?",
        ),
    ]
    with patch(
        "app.routes.regenold._rewrite_multiturn_query",
        return_value=None,
    ):
        question, _ = _build_question_from_history(msgs)

    assert "Conversation so far:" in question
    assert "Latest question:" in question
    assert "And for deployers?" in question
