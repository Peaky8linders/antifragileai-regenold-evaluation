"""R112 — wrapper CLI-error sentinel detection.

Live incident 2026-06-10: the local claude-code-openai-wrapper relayed
the Claude Code CLI error "There's an issue with the selected model
(fable-5). It may not exist or you may not have access to it. Run
--model to pick a different model." as an HTTP 200 chat completion.
The pre-R112 provider only recognised the "Not logged in" sentinel, so
Stage-2 polish replaced the good deterministic answer with the CLI
error text and shipped it on the wire (339/339 bench scenario rows).

Two guard layers under test here:

1. ``_WRAPPER_CLI_ERROR_SENTINELS`` in ``openai_wrapper_provider`` —
   the primary guard: completion text matching any CLI failure shape
   surfaces as ``error="wrapper_cli_error: ..."`` so every consumer
   (Stage-0/1/2, de-noiser, judge) falls back deterministically.
2. ``_STAGE2_REFUSAL_MARKERS`` in ``graph_rag`` — defence-in-depth:
   the route's consistency guard substitutes grounded prose if CLI
   error vocabulary ever reaches the polished answer via another path.
"""
from __future__ import annotations

import httpx

from app.llm.openai_wrapper_provider import (
    OpenAIWrapperRequest,
    _OpenAIWrapperProvider,
    _WRAPPER_CLI_ERROR_SENTINELS,
)

_FABLE5_ERROR = (
    "There's an issue with the selected model (fable-5). It may not "
    "exist or you may not have access to it. Run --model to pick a "
    "different model."
)


def _provider_returning(text: str) -> _OpenAIWrapperProvider:
    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "claude-sonnet-4-6",
                "choices": [{"message": {"content": text}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 30},
            },
        )

    provider = _OpenAIWrapperProvider()
    provider._client = httpx.Client(
        transport=httpx.MockTransport(_handler),
        base_url="https://api.wrapper.test",
    )
    return provider


class TestWrapperCliErrorSentinel:
    def test_fable5_model_error_surfaces_as_error(self) -> None:
        result = _provider_returning(_FABLE5_ERROR).complete(
            OpenAIWrapperRequest(user="ping")
        )
        assert result.error is not None
        assert result.error.startswith("wrapper_cli_error:")
        assert result.text == ""

    def test_detection_is_case_insensitive(self) -> None:
        result = _provider_returning(_FABLE5_ERROR.upper()).complete(
            OpenAIWrapperRequest(user="ping")
        )
        assert result.error is not None
        assert result.error.startswith("wrapper_cli_error:")

    def test_no_response_from_claude_code_surfaces_as_error(self) -> None:
        result = _provider_returning(
            "No response from Claude Code"
        ).complete(OpenAIWrapperRequest(user="ping"))
        assert result.error is not None
        assert result.error.startswith("wrapper_cli_error:")

    def test_legitimate_answer_passes_through(self) -> None:
        answer = (
            "Article 13 requires providers of high-risk AI systems to "
            "design them so deployers can interpret the output and use "
            "it appropriately, with instructions for use per Annex IV."
        )
        result = _provider_returning(answer).complete(
            OpenAIWrapperRequest(user="ping")
        )
        assert result.error is None
        assert result.text == answer

    def test_sentinels_use_cli_vocabulary_only(self) -> None:
        """Every sentinel must be tooling vocabulary, never plausible
        regulator prose — a false positive silently downgrades a good
        Sonnet answer to the deterministic fallback."""
        regulator_sample = (
            "the provider must ensure the high-risk ai system complies "
            "with the requirements of chapter iii before placing it on "
            "the union market or putting it into service. the technical "
            "documentation shall be drawn up per article 11 and annex iv "
            "and kept for ten years. deployers of emotion recognition "
            "systems shall inform exposed persons per article 50."
        )
        for marker in _WRAPPER_CLI_ERROR_SENTINELS:
            assert marker == marker.lower(), marker
            assert marker not in regulator_sample, marker


class TestStage2MarkerDefenceInDepth:
    def test_cli_error_shapes_in_stage2_markers(self) -> None:
        from app.engines.graph_rag import _STAGE2_REFUSAL_MARKERS

        markers = set(_STAGE2_REFUSAL_MARKERS)
        assert "issue with the selected model" in markers
        assert "run --model to pick a different model" in markers
        assert "no response from claude code" in markers

    def test_fable5_error_trips_contradiction_guard(self) -> None:
        from app.engines.graph_rag import _STAGE2_REFUSAL_MARKERS

        lowered = _FABLE5_ERROR.lower()
        assert any(m in lowered for m in _STAGE2_REFUSAL_MARKERS)
