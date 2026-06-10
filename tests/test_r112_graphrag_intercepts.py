"""R112 — graph_rag curated-intercept gating regressions.

Deep-review findings 0 (CRITICAL), 1/26, 17, 34 + the graph_rag half of
16. The R111 intercept regexes were unbounded: ``fine`` matched inside
``defined`` / ``fine-tune`` (so definition and GPAI fine-tune questions
shipped the Article 99 penalties answer, uncorrectable downstream
because curated intercepts skip Stage-2 AND the extractive rescue), and
the guiding-principles regex hijacked any "principles" question
including explicit Article 10 data-governance asks. The minimal-risk
intercept fired on "minimal risk management" (an Article 9 shape).

The date intercept additionally mis-anchored the 2 Aug 2026 general
application date to "Article 113(b)" (the 2 Aug 2025 list) and shipped
Digital Omnibus prose contrary to the project policy (commit 2a755d7 +
graph_rag_prompts rule 2b: official dates only).
"""
from __future__ import annotations

import pytest

from app.engines.graph_rag import (
    _detect_guiding_principles_inquiry,
    _detect_high_risk_penalty_inquiry,
    _detect_minimal_risk_inquiry,
    _is_curated_authoritative_intercept,
    ask_compliance_question,
)
from app.models import GraphRAGRequest


class TestPenaltyInterceptGating:
    """Finding 0 (CRITICAL) — word-bounded penalty trigger."""

    @pytest.mark.parametrize(
        "question",
        [
            "How is a high-risk AI system defined under the EU AI Act?",
            "If we fine-tune a GPAI model for a high-risk use case, do we become the provider?",
            "Which obligations are defined for high-risk AI providers?",
            "What requirements are defined in Article 9 for high-risk systems?",
            "Our refined screening tool is high-risk — what applies?",
        ],
    )
    def test_non_penalty_shapes_do_not_fire(self, question: str) -> None:
        assert not _detect_high_risk_penalty_inquiry(question)

    @pytest.mark.parametrize(
        "question",
        [
            "What penalties apply to high-risk AI violations?",
            "How much can we be fined for non-compliance with high-risk obligations?",
            "What sanctions do providers of high-risk AI face?",
            "What administrative fines apply to high-risk AI systems?",
        ],
    )
    def test_genuine_penalty_shapes_still_fire(self, question: str) -> None:
        assert _detect_high_risk_penalty_inquiry(question)

    def test_fine_tune_question_does_not_ship_penalties_on_the_wire(self) -> None:
        """End-to-end: the GPAI fine-tune shape must not collapse to the
        Article 99 penalties verdict (the pre-R112 wire repro)."""
        res = ask_compliance_question(
            GraphRAGRequest(
                question=(
                    "If we fine-tune a GPAI model for a high-risk use case, "
                    "do we become the provider?"
                )
            )
        )
        answer = (res.answer or "").lower()
        assert "penalty ceiling" not in answer
        assert "article 99(4)" not in answer

    def test_definition_question_does_not_ship_penalties_on_the_wire(self) -> None:
        res = ask_compliance_question(
            GraphRAGRequest(
                question="How is a high-risk AI system defined under the EU AI Act?"
            )
        )
        answer = (res.answer or "").lower()
        assert "penalty ceiling" not in answer
        refs = [c.article_ref for c in (res.citations or [])]
        assert refs != ["Art. 99"]
        # The definitional gold anchor must be present.
        assert "Art. 6" in refs


class TestGuidingPrinciplesGating:
    """Findings 1 + 26 — principles must bind to the Act itself."""

    @pytest.mark.parametrize(
        "question",
        [
            "What are the data governance principles laid down in Article 10 for high-risk AI systems?",
            "What general principles apply to the use of biometric data?",
        ],
    )
    def test_topical_principles_questions_do_not_fire(self, question: str) -> None:
        assert not _detect_guiding_principles_inquiry(question)

    @pytest.mark.parametrize(
        "question",
        [
            "What are the guiding principles of the AI Act?",
            "What principles underpin the regulation?",
            "What are the core principles of the EU AI Act?",
        ],
    )
    def test_act_level_principles_questions_still_fire(self, question: str) -> None:
        assert _detect_guiding_principles_inquiry(question)


class TestMinimalRiskGating:
    """Finding 17 — 'minimal risk management' is an Article 9 shape."""

    def test_minimal_risk_tier_question_fires(self) -> None:
        assert _detect_minimal_risk_inquiry("What are AI systems with minimal risks?")

    def test_risk_management_question_does_not_fire(self) -> None:
        assert not _detect_minimal_risk_inquiry(
            "What minimal risk management measures does Article 9 require?"
        )


class TestCuratedInterceptPredicateAlignment:
    """The route-level extractive-override guard keys on
    ``_is_curated_authoritative_intercept`` — it must mirror the
    detector gating (a False detector must not be re-flagged True)."""

    @pytest.mark.parametrize(
        "question",
        [
            "How is a high-risk AI system defined under the EU AI Act?",
            "What are the data governance principles laid down in Article 10 for high-risk AI systems?",
            "What minimal risk management measures does Article 9 require?",
        ],
    )
    def test_fixed_shapes_are_not_curated_intercepts(self, question: str) -> None:
        assert not _is_curated_authoritative_intercept(question)


class TestDateInterceptOfficialDatesOnly:
    """Findings 34 + 16 — Article 113 anchor + Omnibus policy."""

    def test_deadline_answer_official_dates_no_omnibus(self) -> None:
        res = ask_compliance_question(
            GraphRAGRequest(question="When do high-risk AI obligations apply?")
        )
        answer = res.answer or ""
        low = answer.lower()
        assert "omnibus" not in low
        assert "2 december 2027" not in low
        assert "article 113(b)" not in low
        # The official general-application date must survive.
        assert "2 august 2026" in low
