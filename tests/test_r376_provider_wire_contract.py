"""R376 — provider routing asserted on the WIRE, not on a mocked seam.

WHY THIS FILE EXISTS. Every provider-routing defect this repo has shipped was
invisible to the existing tests, and for one structural reason: they mock
``provider.complete`` and assert on the request OBJECT. That proves the engine
built the right intent — it cannot prove the intent survived serialisation.
All four defects R376 fixed live strictly below that seam:

* the OpenRouter extended-thinking budget was dropped from the JSON body
  whenever ``OPENROUTER_API_BASE`` was not literally on ``openrouter.ai``
  (``req.reasoning_max_tokens`` was still 2048 — the seam test passed);
* the Bedrock Stage-2 call never set ``thinking_budget``, so
  ``additionalModelRequestFields`` was absent from the Converse body;
* the Bedrock simple tier posted the Stage-1 parse model
  (``claude-opus-4-8``) instead of Sonnet 5;
* the cross-provider fallback posted a hard-coded ``claude-opus-4-6``
  regardless of question complexity.

So these tests run real HTTP servers speaking the OpenRouter and Bedrock
Converse protocols (``scripts/e2e_provider_mocks``) and assert on the bytes that
arrived. Nothing here needs network access or credentials: both servers bind
``127.0.0.1`` on an ephemeral port.

See also ``tests/test_openrouter_stage2.py`` for the seam-level contracts, which
remain useful for the branching logic they do cover.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engines import _graph_rag_impl as impl  # noqa: E402
from scripts.e2e_provider_mocks import MockBedrock, MockOpenRouter  # noqa: E402


@pytest.fixture
def openrouter_wire(monkeypatch):
    """A live OpenRouter-protocol server wired into the Stage-2 path.

    The base URL deliberately does NOT contain ``openrouter.ai`` — that is the
    configuration under test.
    """
    from app.llm.openai_wrapper_provider import _reset_openrouter_singleton_for_tests

    server = MockOpenRouter().start()
    monkeypatch.setenv("OPENROUTER_API_BASE", server.base_url)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    for var in (
        "REGENOLD_STAGE2_MODEL_OPENROUTER",
        "REGENOLD_STAGE2_COMPLEX_MODEL_OPENROUTER",
        "REGENOLD_OPENROUTER_ROUTING",
        "REGENOLD_OPENROUTER_FALLBACK_CHAIN",
        "REGENOLD_OPUS_FOR_ALL",
    ):
        monkeypatch.delenv(var, raising=False)
    _reset_openrouter_singleton_for_tests()
    try:
        yield server
    finally:
        server.stop()
        _reset_openrouter_singleton_for_tests()


@pytest.fixture
def bedrock_wire(monkeypatch):
    """A live Bedrock Converse server wired in via botocore's endpoint override."""
    from app.llm.bedrock_client import (
        _reset_bedrock_singletons_for_tests,
        reset_bedrock_entitlement_cache,
    )

    server = MockBedrock().start()
    monkeypatch.setenv("AWS_ENDPOINT_URL_BEDROCK_RUNTIME", server.endpoint_url)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATESTTESTTEST")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.delenv("AWS_BEARER_TOKEN_BEDROCK", raising=False)
    monkeypatch.setenv("AWS_REGION", "eu-central-1")
    monkeypatch.setenv("BEDROCK_REGION", "eu-central-1")
    for var in (
        "REGENOLD_BEDROCK_MODEL",
        "REGENOLD_BEDROCK_COMPLEX_MODEL",
        "REGENOLD_BEDROCK_STAGE2_MODEL",
        "REGENOLD_BEDROCK_FALLBACK_CHAIN",
        "REGENOLD_BEDROCK_FALLBACK_MODEL",
        "REGENOLD_OPUS_FOR_ALL",
    ):
        monkeypatch.delenv(var, raising=False)
    _reset_bedrock_singletons_for_tests()
    reset_bedrock_entitlement_cache()
    try:
        yield server
    finally:
        server.stop()
        _reset_bedrock_singletons_for_tests()
        reset_bedrock_entitlement_cache()


def _stage2(**kwargs):
    defaults = dict(
        system="SYSTEM", user="USER", max_tokens=1536, temperature=0.0,
        stage_name="Stage 2 (Polishing)",
    )
    defaults.update(kwargs)
    return defaults


class TestOpenRouterWireBody:
    """The reasoning budget must reach the JSON body, not just the request object."""

    def test_complex_sends_opus5_with_2048_thinking_on_any_base_url(
        self, openrouter_wire
    ):
        out = impl._openrouter_complete_for_graph_rag(
            **_stage2(complex_question=True)
        )
        assert out
        body = openrouter_wire.calls[0]["body"]
        assert body["model"] == "anthropic/claude-opus-5"
        # THE REGRESSION: this was ``None`` whenever the base URL was not
        # literally on openrouter.ai, because an ``anthropic/claude-*`` model
        # then matched the Claude-Code-CLI branch and the budget was routed to
        # an HTTP header OpenRouter does not read.
        assert body.get("reasoning") == {"max_tokens": 2048, "exclude": False}

    def test_simple_sends_sonnet5_without_a_thinking_budget(self, openrouter_wire):
        out = impl._openrouter_complete_for_graph_rag(
            **_stage2(complex_question=False)
        )
        assert out
        body = openrouter_wire.calls[0]["body"]
        assert body["model"] == "anthropic/claude-sonnet-5"
        assert body.get("reasoning") is None
        assert body.get("reasoning_effort") is None

    def test_system_and_user_channels_both_reach_the_wire(self, openrouter_wire):
        impl._openrouter_complete_for_graph_rag(**_stage2(complex_question=False))
        roles = {
            m["role"]: m["content"]
            for m in openrouter_wire.calls[0]["body"]["messages"]
        }
        assert roles["system"] == "SYSTEM"
        assert roles["user"] == "USER"


class TestBedrockWireBody:
    """Tier split and extended thinking must survive into the Converse body."""

    def test_simple_stage2_uses_the_sonnet_tier_not_the_parse_tier(self, bedrock_wire):
        out = impl._bedrock_complete_for_graph_rag(**_stage2(complex_question=False))
        assert out
        assert bedrock_wire.model_ids() == ["eu.anthropic.claude-sonnet-5"]
        body = bedrock_wire.calls[0]["body"]
        assert body.get("additionalModelRequestFields") is None

    def test_complex_stage2_uses_opus5_with_2048_reasoning_config(self, bedrock_wire):
        out = impl._bedrock_complete_for_graph_rag(**_stage2(complex_question=True))
        assert out
        assert bedrock_wire.model_ids() == ["eu.anthropic.claude-opus-5"]
        body = bedrock_wire.calls[0]["body"]
        # THE REGRESSION: absent entirely. The capability existed since R355 and
        # the Stage-2 adapter simply never asked for it, so a complex question
        # that fell over to Bedrock silently lost its deliberation budget.
        assert body["additionalModelRequestFields"] == {
            "reasoning_config": {"type": "enabled", "budget_tokens": 2048}
        }
        # Bedrock rejects extended thinking unless temperature == 1 and
        # maxTokens EXCEEDS the budget; both are the provider's contract, so
        # pin them here rather than rediscovering them from a 400.
        assert body["inferenceConfig"]["temperature"] == 1.0
        assert body["inferenceConfig"]["maxTokens"] > 2048

    def test_rollover_to_a_non_claude_tier_drops_the_reasoning_block(
        self, bedrock_wire, monkeypatch
    ):
        """A thinking-enabled Claude primary must not send ``reasoning_config``
        to the qwen/nemotron tiers below it — that would turn a recoverable
        throttle into a ValidationException, i.e. break the rollover in exactly
        the situation it exists for."""

        def _deny_claude(call, _index):
            if "anthropic" in call["path"]:
                return ("error", "AccessDeniedException", "no entitlement")
            return ("ok", MockBedrock.DEFAULT_TEXT)

        bedrock_wire.behaviour = _deny_claude
        out = impl._bedrock_complete_for_graph_rag(**_stage2(complex_question=True))
        assert out, "the chain must still serve from a non-Claude tier"
        # strict=True: the two lists are the same recorded calls viewed two
        # ways, so a length mismatch would mean the recorder is broken —
        # better to raise than to silently compare a truncated pair set.
        seen = list(zip(bedrock_wire.model_ids(), bedrock_wire.calls, strict=True))
        assert len(seen) >= 2
        for model_id, call in seen:
            has_reasoning = call["body"].get("additionalModelRequestFields") is not None
            assert has_reasoning is impl._supports_extended_thinking(model_id), (
                f"{model_id} sent reasoning_config={has_reasoning}"
            )
        assert not impl._supports_extended_thinking(seen[-1][0])


class TestExtendedThinkingSupportGuard:
    @pytest.mark.parametrize(
        "model_id,expected",
        [
            ("eu.anthropic.claude-opus-5", True),
            ("us.anthropic.claude-opus-4-6-v1", True),
            ("anthropic.claude-sonnet-5", True),
            ("qwen.qwen3-235b-a22b-2507-v1:0", False),
            ("nvidia.nemotron-super-3-120b", False),
            ("mistral.devstral-2-123b", False),
            ("", False),
            # Guards the "bare substring" mistake: matching on ``claude``
            # anywhere would opt a non-Anthropic vendor in.
            ("acme.claude-lookalike-v1", False),
        ],
    )
    def test_only_anthropic_claude_tiers_accept_reasoning_config(
        self, model_id, expected
    ):
        assert impl._supports_extended_thinking(model_id) is expected


class TestCrossProviderFallbackKeepsTheTierSplit:
    """OpenRouter exhausted → Bedrock, at the tier the question deserves."""

    @pytest.fixture(autouse=True)
    def _dead_openrouter(self, openrouter_wire):
        openrouter_wire.behaviour = lambda _call, _i: ("http", 500, "provider down")
        return openrouter_wire

    def test_complex_falls_over_to_opus5_with_thinking(
        self, openrouter_wire, bedrock_wire, monkeypatch
    ):
        monkeypatch.setenv("P2P_GRAPH_RAG_PROVIDER", "openrouter")
        out = impl._openrouter_complete_for_graph_rag(
            **_stage2(complex_question=True)
        )
        assert out is None, "the OpenRouter chain must be exhausted first"
        # The engine's cross-provider net then calls Bedrock with the SAME
        # complexity, rather than the hard-coded opus-4-6 it used to pin.
        served = impl._bedrock_complete_for_graph_rag(
            **_stage2(
                complex_question=True, stage_name="Stage 2 (Polishing) fallback"
            )
        )
        assert served
        assert bedrock_wire.model_ids() == ["eu.anthropic.claude-opus-5"]
        assert bedrock_wire.calls[0]["body"]["additionalModelRequestFields"]

    def test_simple_falls_over_to_sonnet5_not_an_opus_tier(
        self, openrouter_wire, bedrock_wire, monkeypatch
    ):
        monkeypatch.setenv("P2P_GRAPH_RAG_PROVIDER", "openrouter")
        assert (
            impl._openrouter_complete_for_graph_rag(**_stage2(complex_question=False))
            is None
        )
        served = impl._bedrock_complete_for_graph_rag(
            **_stage2(
                complex_question=False, stage_name="Stage 2 (Polishing) fallback"
            )
        )
        assert served
        assert bedrock_wire.model_ids() == ["eu.anthropic.claude-sonnet-5"]

    def test_an_explicit_pin_still_overrides_the_tier(self, bedrock_wire, monkeypatch):
        monkeypatch.setenv("REGENOLD_BEDROCK_FALLBACK_MODEL", "claude-opus-4-6")
        served = impl._bedrock_complete_for_graph_rag(
            **_stage2(
                complex_question=False,
                stage_name="Stage 2 (Polishing) fallback",
                model_override="claude-opus-4-6",
            )
        )
        assert served
        assert bedrock_wire.model_ids()[0].endswith("claude-opus-4-6-v1")
