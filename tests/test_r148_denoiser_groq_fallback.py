"""R148 — Query de-noiser Groq→fallback provider chain.

Root cause (reproduced live 2026-06-22): once Groq's free-tier 100K
tokens-per-day budget is exhausted, every ``llama-3.3-70b-versatile``
call returns ``api_status_429`` and the trace shows
``denoiser skipped (provider_error)``. The de-noiser's provider
selection was ``if groq … elif wrapper …``, so a Groq failure dropped the
multi-turn rewrite entirely instead of falling back to the
already-configured second provider — the fallback the intent classifier
(``app/llm/intent_classifier.py``) has always had.

These tests pin the provider chain: Groq first, the fallback provider on a
Groq provider failure, deterministic salvage only when BOTH fail. The
single-provider configurations stay byte-identical to the pre-R148
single-provider behaviour (covered by
``tests/test_r87a_query_denoiser_trace.py``).

⚠ R377 — THE FALLBACK LINK IS BEDROCK NOW, NOT THE CLAUDE-MAX WRAPPER.
Operator directive 2026-08-23 cut the chain from
``Groq → Gemini → Mistral → wrapper`` down to ``Groq → Bedrock``: the
wrapper candidate is the ~10 s Max tunnel, which the 3 s per-provider
fail-fast can never beat, so it could never actually serve the fallback
these tests describe. Every test below still asserts the SAME R148
property — a Groq failure must degrade to the next provider rather than
drop the rewrite — it is simply asserted against the provider that now
occupies that slot. Only the identity of the fallback moved; the chain
semantics under test did not.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import app.routes.regenold as rgn
from app.integrations.regenold import reasoning_trace as rt
from app.routes.regenold import _rewrite_multiturn_query

GROQ_429 = (
    'api_status_429: {"error":{"message":"Rate limit reached for model '
    "`llama-3.3-70b-versatile` in organization `org_x` service tier "
    '`on_demand` on tokens per day (TPD): Limit 100000, Used 100000"}}'
)

# The Bedrock candidate's code default (``REGENOLD_DENOISER_MODEL_BEDROCK``
# overrides it). A query rewrite is a Stage-0 utility task, so the denoiser
# deliberately does not pin the frontier tier.
BEDROCK_DENOISER_MODEL = "eu.anthropic.claude-sonnet-4-6"


@pytest.fixture(autouse=True)
def _both_providers_wired(monkeypatch):
    """Wire BOTH Groq (key present, default intent provider) and Bedrock
    (gate ON, default model) — the production shape where the fallback
    chain matters.

    R377 — ``OPENAI_API_BASE`` is no longer part of this shape: the wrapper
    candidate was deleted from the chain, so setting it would wire nothing.
    """
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
    monkeypatch.delenv("P2P_GRAPH_RAG_PROVIDER", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.delenv("REGENOLD_INTENT_PROVIDER", raising=False)  # → groq default
    monkeypatch.setenv("REGENOLD_DENOISER_BEDROCK", "1")
    # Assert against the code default, not an operator override.
    monkeypatch.delenv("REGENOLD_DENOISER_MODEL_BEDROCK", raising=False)


@pytest.fixture
def trace():
    t = rt.activate()
    yield t
    rt.deactivate()


def _mk_msg(role: str, content: str):
    m = MagicMock()
    m.role = role
    m.content = content
    return m


def _resp(*, error=None, text="", finish_reason="stop"):
    return SimpleNamespace(error=error, text=text, finish_reason=finish_reason)


def _provider(resp):
    p = MagicMock()
    p.complete.return_value = resp
    return p


def _wire(monkeypatch, groq, bedrock):
    """Patch the PRIMARY (Groq) and FALLBACK (Bedrock) links of the chain.

    R377 — the fallback half used to be patched on
    ``openai_wrapper_provider`` alongside Groq. Bedrock is reached through a
    different seam, so it takes three patches: the R377 env gate and the
    adapter class (both module globals on ``app.routes.regenold``, looked up
    at call time) plus ``is_bedrock_provider_enabled``, which the route
    imports lazily from ``app.llm.bedrock_client`` inside the function.
    ``_BedrockDenoiserProvider`` is instantiated by the route, so the stub
    is a zero-arg factory returning our fake provider.
    """
    import app.llm.bedrock_client as bc
    import app.llm.openai_wrapper_provider as owp

    monkeypatch.setattr(owp, "is_groq_intent_provider_enabled", lambda: True)
    monkeypatch.setattr(owp, "get_groq_intent_provider", lambda: groq)
    monkeypatch.setattr(rgn, "_denoiser_bedrock_enabled", lambda: True)
    monkeypatch.setattr(bc, "is_bedrock_provider_enabled", lambda: True)
    monkeypatch.setattr(rgn, "_BedrockDenoiserProvider", lambda: bedrock)


def test_groq_429_falls_back_to_bedrock(monkeypatch, trace):
    """The reported bug: Groq TPD 429 must degrade to the next provider in
    the chain (R377: Bedrock, was the Haiku wrapper), not drop the
    rewrite."""
    groq = _provider(_resp(error=GROQ_429))
    bedrock = _provider(_resp(text="emotion recognition prohibition workplace Article 5"))
    _wire(monkeypatch, groq, bedrock)

    out = _rewrite_multiturn_query(
        "are they always prohibited?",
        [_mk_msg("user", "Tell me about emotion recognition systems.")],
    )

    assert out == "emotion recognition prohibition workplace Article 5"
    groq.complete.assert_called_once()
    bedrock.complete.assert_called_once()
    qd = trace.query_denoiser
    assert qd["fired"] is True
    assert qd["provider"] == "bedrock"
    assert qd["model"] == BEDROCK_DENOISER_MODEL


def test_groq_success_does_not_call_bedrock(monkeypatch, trace):
    """Happy Groq path is unchanged — the fallback provider is never
    touched."""
    groq = _provider(_resp(text="emotion recognition always prohibited Article 5"))
    bedrock = _provider(_resp(text="SHOULD NOT BE USED"))
    _wire(monkeypatch, groq, bedrock)

    out = _rewrite_multiturn_query(
        "are they always prohibited?",
        [_mk_msg("user", "Tell me about emotion recognition systems.")],
    )

    assert out == "emotion recognition always prohibited Article 5"
    groq.complete.assert_called_once()
    bedrock.complete.assert_not_called()
    assert trace.query_denoiser["provider"] == "groq"


def test_groq_exception_falls_back_to_bedrock(monkeypatch, trace):
    """A transport-level Groq exception (not just resp.error) also falls
    through to the fallback provider."""
    groq = MagicMock()
    groq.complete.side_effect = RuntimeError("connection reset by peer")
    bedrock = _provider(_resp(text="deployer transparency obligations Article 26"))
    _wire(monkeypatch, groq, bedrock)

    out = _rewrite_multiturn_query(
        "what about deployers?",
        [_mk_msg("user", "What is Article 13?")],
    )

    assert out == "deployer transparency obligations Article 26"
    bedrock.complete.assert_called_once()
    assert trace.query_denoiser["fired"] is True
    assert trace.query_denoiser["provider"] == "bedrock"


def test_both_providers_fail_records_final_failure(monkeypatch, trace):
    """When Groq 429s AND Bedrock errors, the chain is exhausted →
    the de-noiser records the final provider failure and the caller falls
    back (salvage / concatenation)."""
    groq = _provider(_resp(error=GROQ_429))
    bedrock = _provider(_resp(error="network_error: timed out"))
    _wire(monkeypatch, groq, bedrock)

    _rewrite_multiturn_query(
        "what about deployers?",
        [_mk_msg("user", "What is Article 13?")],
    )

    groq.complete.assert_called_once()
    bedrock.complete.assert_called_once()
    qd = trace.query_denoiser
    assert qd["fired"] is False
    assert qd["fallback_reason"] == "provider_error"
    assert qd["provider"] == "bedrock"  # last provider attempted


def test_groq_empty_then_bedrock_succeeds(monkeypatch, trace):
    """An empty Groq completion is a provider failure → fall through."""
    groq = _provider(_resp(error=None, text="   "))
    bedrock = _provider(_resp(text="high-risk classification Annex III Article 6"))
    _wire(monkeypatch, groq, bedrock)

    out = _rewrite_multiturn_query(
        "is it high-risk?",
        [_mk_msg("user", "We deploy an emotion recognition system.")],
    )

    assert out == "high-risk classification Annex III Article 6"
    assert trace.query_denoiser["provider"] == "bedrock"
    assert trace.query_denoiser["fired"] is True


def test_groq_429_reaches_bedrock_through_the_REAL_adapter(monkeypatch, trace):
    """The fallback link must be a WORKING provider, not just a reachable name.

    R377 — the other tests in this file stub ``_BedrockDenoiserProvider``
    wholesale, which proves the route reaches that *name* but never that the
    adapter behind it maps the denoiser's request onto Bedrock correctly. The
    pre-R377 fallback was ``get_openai_wrapper_provider``, a long-standing,
    independently-tested factory, so stubbing it lost nothing; the R377 adapter
    is new and is exercised nowhere else in the suite. Here the adapter stays
    REAL and only ``complete_with_fallback`` — the Bedrock wire — is stubbed,
    so the OpenAIWrapperRequest → BedrockRequest mapping is asserted on the
    object the client would actually have been handed.
    """
    import app.llm.bedrock_client as bc
    import app.llm.openai_wrapper_provider as owp

    seen: list = []

    def _fake_complete_with_fallback(req, **_kw):
        seen.append(req)
        return bc.BedrockResponse(
            text="serious incident reporting deadline Article 73",
            model=req.model,
            finish_reason="end_turn",
        )

    groq = _provider(_resp(error=GROQ_429))
    monkeypatch.setattr(owp, "is_groq_intent_provider_enabled", lambda: True)
    monkeypatch.setattr(owp, "get_groq_intent_provider", lambda: groq)
    monkeypatch.setattr(rgn, "_denoiser_bedrock_enabled", lambda: True)
    monkeypatch.setattr(bc, "is_bedrock_provider_enabled", lambda: True)
    # NOTE: _BedrockDenoiserProvider is deliberately NOT patched.
    monkeypatch.setattr(bc, "complete_with_fallback", _fake_complete_with_fallback)
    monkeypatch.delenv("REGENOLD_DENOISER_TIMEOUT", raising=False)

    out = _rewrite_multiturn_query(
        "what's the reporting window then?",
        [_mk_msg("user", "Tell me about serious incident reporting.")],
    )

    assert out == "serious incident reporting deadline Article 73"
    groq.complete.assert_called_once()
    assert len(seen) == 1
    req = seen[0]
    assert isinstance(req, bc.BedrockRequest)
    assert req.model == BEDROCK_DENOISER_MODEL
    assert req.max_tokens == 100  # the rewrite budget, not BedrockRequest's 1024
    assert req.temperature == 0.0
    assert req.system == rgn._QUERY_DENOISER_SYSTEM
    assert req.timeout_seconds == 3.0  # R267.1 per-provider fail-fast
    assert "Follow-up question: what's the reporting window then?" in req.user
    qd = trace.query_denoiser
    assert qd["fired"] is True
    assert qd["provider"] == "bedrock"
    assert qd["model"] == BEDROCK_DENOISER_MODEL
