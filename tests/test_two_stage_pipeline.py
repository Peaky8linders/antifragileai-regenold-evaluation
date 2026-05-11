"""Regression guards for the two-stage KG-first answer pipeline.

Stage 1 (always): deterministic ontology/KB parse → Neo4j/KB retrieval →
  citation-exact structured answer.  No LLM cost; always runs.

Stage 2 (when Claude Max proxy available): pass the Stage-1 answer to the
  ``openai_wrapper`` proxy (Claude Max subscription at 127.0.0.1:8000/v1)
  for natural-language polish.  Falls back to Stage-1 answer on any error.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.engines.graph_rag import (
    GraphContext,
    _claude_max_enhance_answer,
    _two_stage_generate,
    ask_compliance_question,
)
from app.models import GraphRAGRequest


# ─── Stage 1: parse is always deterministic ──────────────────────────────────


class TestStage1AlwaysDeterministic:
    """The pipeline must never call _llm_parse_query — Stage 1 parse is always
    ontology/KB-based so there is no LLM cost or latency on the parse path."""

    def test_llm_parse_query_never_called(self) -> None:
        with patch("app.engines.graph_rag._llm_parse_query") as mock_llm:
            req = GraphRAGRequest(question="What does Art. 9 require?")
            ask_compliance_question(req)
        mock_llm.assert_not_called()

    def test_deterministic_parse_always_called(self) -> None:
        with patch(
            "app.engines.graph_rag._deterministic_parse",
            wraps=__import__(
                "app.engines.graph_rag", fromlist=["_deterministic_parse"]
            )._deterministic_parse,
        ) as mock_det:
            req = GraphRAGRequest(question="What obligations does Art. 13 impose?")
            ask_compliance_question(req)
        mock_det.assert_called_once()

    def test_reasoning_trace_has_seven_entries(self) -> None:
        """The trace must include the new Stage-2 indicator entry."""
        req = GraphRAGRequest(question="What does Art. 9 require?")
        result = ask_compliance_question(req)
        assert len(result.reasoning_trace) == 7, result.reasoning_trace

    def test_reasoning_trace_includes_stage2_indicator(self) -> None:
        req = GraphRAGRequest(question="What does Art. 9 require?")
        result = ask_compliance_question(req)
        stage2_entries = [
            t for t in result.reasoning_trace if "Stage 2" in t
        ]
        assert len(stage2_entries) == 1, result.reasoning_trace


# ─── Stage 2: Claude Max proxy engagement ────────────────────────────────────


class TestStage2ClaudeMaxProxy:
    """Stage 2 fires only when is_openai_wrapper_enabled() returns True."""

    def test_stage2_skipped_when_wrapper_disabled(self) -> None:
        with (
            patch(
                "app.engines.graph_rag._two_stage_generate",
                wraps=__import__(
                    "app.engines.graph_rag", fromlist=["_two_stage_generate"]
                )._two_stage_generate,
            ),
            patch(
                "app.llm.openai_wrapper_provider.is_openai_wrapper_enabled",
                return_value=False,
            ),
            patch(
                "app.engines.graph_rag._openai_wrapper_complete_for_graph_rag"
            ) as mock_wrapper,
        ):
            req = GraphRAGRequest(question="What does Art. 9 require?")
            result = ask_compliance_question(req)

        mock_wrapper.assert_not_called()
        # Stage 2 indicator must be False
        stage2_line = next(
            t for t in result.reasoning_trace if "Stage 2" in t
        )
        assert "False" in stage2_line

    def test_stage2_fires_when_wrapper_enabled(self) -> None:
        with (
            patch(
                "app.llm.openai_wrapper_provider.is_openai_wrapper_enabled",
                return_value=True,
            ),
            patch(
                "app.engines.graph_rag._openai_wrapper_complete_for_graph_rag",
                return_value="Enhanced compliance guidance for Art. 9.",
            ) as mock_wrapper,
        ):
            req = GraphRAGRequest(question="What does Art. 9 require?")
            result = ask_compliance_question(req)

        mock_wrapper.assert_called_once()
        assert result.answer == "Enhanced compliance guidance for Art. 9."
        stage2_line = next(
            t for t in result.reasoning_trace if "Stage 2" in t
        )
        assert "True" in stage2_line

    def test_stage2_failure_returns_kg_answer(self) -> None:
        """When the Claude Max call returns None the Stage-1 KG answer is used."""
        with (
            patch(
                "app.llm.openai_wrapper_provider.is_openai_wrapper_enabled",
                return_value=True,
            ),
            patch(
                "app.engines.graph_rag._openai_wrapper_complete_for_graph_rag",
                return_value=None,
            ),
        ):
            req = GraphRAGRequest(question="What does Art. 9 require?")
            result = ask_compliance_question(req)

        # Must still return a non-empty grounded answer
        assert result.answer
        stage2_line = next(
            t for t in result.reasoning_trace if "Stage 2" in t
        )
        assert "False" in stage2_line

    def test_stage2_exception_returns_kg_answer(self) -> None:
        """A hard exception inside the wrapper path must not propagate."""
        with (
            patch(
                "app.llm.openai_wrapper_provider.is_openai_wrapper_enabled",
                return_value=True,
            ),
            patch(
                "app.engines.graph_rag._openai_wrapper_complete_for_graph_rag",
                side_effect=RuntimeError("connection refused"),
            ),
        ):
            req = GraphRAGRequest(question="What does Art. 9 require?")
            result = ask_compliance_question(req)

        assert result.answer


# ─── _two_stage_generate unit tests ──────────────────────────────────────────


class TestTwoStageGenerateUnit:
    """Direct unit tests on the helper without going through the route."""

    def _empty_context(self) -> GraphContext:
        return GraphContext()

    def test_returns_kg_answer_when_wrapper_disabled(self) -> None:
        ctx = self._empty_context()
        with patch(
            "app.llm.openai_wrapper_provider.is_openai_wrapper_enabled",
            return_value=False,
        ):
            answer, used = _two_stage_generate("What is Art. 9?", ctx)

        assert not used
        assert answer  # KG answer is never empty

    def test_returns_enhanced_when_wrapper_enabled(self) -> None:
        ctx = self._empty_context()
        with (
            patch(
                "app.llm.openai_wrapper_provider.is_openai_wrapper_enabled",
                return_value=True,
            ),
            patch(
                "app.engines.graph_rag._openai_wrapper_complete_for_graph_rag",
                return_value="Polished answer.",
            ),
        ):
            answer, used = _two_stage_generate("What is Art. 9?", ctx)

        assert used
        assert answer == "Polished answer."

    def test_returns_kg_answer_when_enhance_returns_none(self) -> None:
        ctx = self._empty_context()
        with (
            patch(
                "app.llm.openai_wrapper_provider.is_openai_wrapper_enabled",
                return_value=True,
            ),
            patch(
                "app.engines.graph_rag._openai_wrapper_complete_for_graph_rag",
                return_value=None,
            ),
        ):
            answer, used = _two_stage_generate("What is Art. 9?", ctx)

        assert not used
        assert answer


# ─── _claude_max_enhance_answer unit tests ───────────────────────────────────


class TestClaudeMaxEnhanceAnswerUnit:
    """_claude_max_enhance_answer must pass the KG answer to the wrapper and
    return the polished result, or None on any failure."""

    def test_passes_kg_answer_in_user_message(self) -> None:
        captured: list[str] = []

        def capture(**kwargs: object) -> str:
            captured.append(str(kwargs.get("user", "")))
            return "Polished answer."

        with patch(
            "app.engines.graph_rag._openai_wrapper_complete_for_graph_rag",
            side_effect=capture,
        ):
            result = _claude_max_enhance_answer(
                question="What does Art. 9 require?",
                kg_answer="Some KG answer text.",
            )

        assert result == "Polished answer."
        assert len(captured) == 1
        assert "Some KG answer text." in captured[0]
        assert "Art. 9" in captured[0]

    def test_returns_none_when_wrapper_returns_none(self) -> None:
        with patch(
            "app.engines.graph_rag._openai_wrapper_complete_for_graph_rag",
            return_value=None,
        ):
            result = _claude_max_enhance_answer(
                question="What does Art. 9 require?",
                kg_answer="KG answer.",
            )
        assert result is None

    def test_returns_none_on_exception(self) -> None:
        with patch(
            "app.engines.graph_rag._openai_wrapper_complete_for_graph_rag",
            side_effect=RuntimeError("boom"),
        ):
            result = _claude_max_enhance_answer(
                question="What does Art. 9 require?",
                kg_answer="KG answer.",
            )
        assert result is None

    def test_includes_system_description_when_provided(self) -> None:
        captured: list[str] = []

        def capture(**kwargs: object) -> str:
            captured.append(str(kwargs.get("user", "")))
            return "Polished."

        with patch(
            "app.engines.graph_rag._openai_wrapper_complete_for_graph_rag",
            side_effect=capture,
        ):
            _claude_max_enhance_answer(
                question="What is Art. 9?",
                kg_answer="KG answer.",
                system_description="HR screening tool at a large bank.",
            )

        assert "HR screening" in captured[0]
