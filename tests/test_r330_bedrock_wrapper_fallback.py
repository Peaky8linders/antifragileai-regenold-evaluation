"""R330 — the cross-PROVIDER last resort ported from `regenold-eu-ai-act-rag`.

The sibling repo hops to the Claude-Max wrapper when Bedrock errors. Ported here
into ``complete_with_fallback`` (one definition of "Bedrock is exhausted") rather
than into ``BedrockProvider.complete``'s exception handlers.

The tests that matter are the ORDERING one and the PROVENANCE one:

* ordering — the hop must not pre-empt a working lower tier in the entitlement
  chain. The sibling's placement can fire on the FIRST model's throttle while an
  invocable tier sits further down; that is the defect this port fixes.
* provenance — the wrapper DROPS the system prompt (verified live 2026-08-14),
  so a silent hop changes ~12.8K tokens of delivered instruction. In a repo whose
  product is the measurement, the swap must reach the durable artifact, not just
  a log line. The ``wrapper:`` prefix on ``model`` is what makes the EXISTING
  provenance in ``_bedrock_complete_for_graph_rag`` fire unchanged.
"""
from __future__ import annotations

import pytest

from app.llm import bedrock_client as bc


@pytest.fixture(autouse=True)
def _clean_entitlement_cache():
    bc.reset_bedrock_entitlement_cache()
    yield
    bc.reset_bedrock_entitlement_cache()


class _FakeWrapperResp:
    def __init__(self, text="wrapper answer", error=None, model="claude-sonnet-4-6"):
        self.text = text
        self.error = error
        self.model = model
        self.prompt_tokens = 11
        self.completion_tokens = 22
        self.elapsed_ms = 33
        self.finish_reason = "stop"


def _install_wrapper(monkeypatch, resp=None, enabled=True, spy=None):
    """Stub `app.llm.openai_wrapper_provider` as imported INSIDE the fallback."""
    import app.llm.openai_wrapper_provider as owp

    monkeypatch.setattr(owp, "is_openai_wrapper_enabled", lambda: enabled)

    class _Prov:
        def complete(self, req):
            if spy is not None:
                spy.append(req)
            return resp if resp is not None else _FakeWrapperResp()

    monkeypatch.setattr(owp, "get_openai_wrapper_provider", lambda: _Prov())


def _install_bedrock(monkeypatch, behaviour):
    """`behaviour` maps resolved model id -> BedrockResponse."""
    calls: list[str] = []

    class _Prov:
        def complete(self, req):
            calls.append(req.model)
            return behaviour(req.model)

    monkeypatch.setattr(bc, "get_bedrock_provider", lambda: _Prov())
    return calls


# ── ordering: the hop is a LAST resort, never a first one ────────────────────

def test_working_lower_tier_wins_over_the_wrapper_hop(monkeypatch):
    """A 403 on the head must degrade WITHIN Bedrock, not jump to the wrapper.

    This is the regression the sibling's placement would allow.
    """
    ok_tier = "eu.anthropic.claude-opus-4-6-v1"

    def behaviour(model_id):
        if model_id == ok_tier:
            return bc.BedrockResponse(text="bedrock answer", model=model_id)
        return bc.BedrockResponse(error="api_access_denied_403", model=model_id)

    calls = _install_bedrock(monkeypatch, behaviour)
    spy: list = []
    _install_wrapper(monkeypatch, spy=spy)

    resp = bc.complete_with_fallback(
        bc.BedrockRequest(user="q", model="eu.anthropic.claude-opus-4-8")
    )

    assert resp.error is None
    assert resp.text == "bedrock answer"
    assert resp.model == ok_tier
    assert not resp.model.startswith("wrapper:")
    assert spy == [], "wrapper must NOT be called while a Bedrock tier still works"
    assert ok_tier in calls


def test_hop_fires_only_after_the_whole_chain_is_spent(monkeypatch):
    """Every chain member denied -> the wrapper serves, and says so."""
    calls = _install_bedrock(
        monkeypatch,
        lambda m: bc.BedrockResponse(error="api_access_denied_403", model=m),
    )
    spy: list = []
    _install_wrapper(monkeypatch, spy=spy)

    resp = bc.complete_with_fallback(
        bc.BedrockRequest(user="q", model="eu.anthropic.claude-opus-4-8")
    )

    assert resp.error is None
    assert resp.text == "wrapper answer"
    assert len(spy) == 1
    # the whole opus chain was probed before the hop
    assert len(calls) >= 3


# ── provenance: the swap must be visible in the durable artifact ─────────────

def test_served_model_is_prefixed_so_existing_provenance_fires(monkeypatch):
    """`_bedrock_complete_for_graph_rag` records when `resp.model != model_id`.

    The prefix is what makes a cross-provider hop indistinguishable-from-nothing
    impossible: `stage2_models` in the sidecar shows `wrapper:...`, not the pin.
    """
    _install_bedrock(
        monkeypatch,
        lambda m: bc.BedrockResponse(error="api_access_denied_403", model=m),
    )
    _install_wrapper(monkeypatch, resp=_FakeWrapperResp(model="claude-opus-4-6"))

    resp = bc.complete_with_fallback(
        bc.BedrockRequest(user="q", model="eu.anthropic.claude-opus-4-8")
    )

    assert resp.model == "wrapper:claude-opus-4-6"
    assert resp.model != "eu.anthropic.claude-opus-4-8"
    assert resp.prompt_tokens == 11 and resp.completion_tokens == 22


def test_model_mapping_prefers_the_specific_tier(monkeypatch):
    """A bare `opus` entry must not swallow `opus-4-6` — ordering in the table."""
    assert bc.wrapper_model_for("eu.anthropic.claude-opus-4-6-v1") == "claude-opus-4-6"
    assert bc.wrapper_model_for("eu.anthropic.claude-sonnet-4-6") == "claude-sonnet-4-6"
    assert bc.wrapper_model_for("eu.anthropic.claude-opus-4-8") == "claude-opus-4-8"
    assert bc.wrapper_model_for("eu.anthropic.claude-sonnet-5") == "claude-sonnet-4-6"
    assert bc.wrapper_model_for("") == "claude-sonnet-4-6"


# ── the off-switch, and fail-soft ────────────────────────────────────────────

def test_off_switch_keeps_bedrocks_real_error(monkeypatch):
    """`=0` must restore the pre-port behaviour byte-for-byte."""
    monkeypatch.setenv("REGENOLD_BEDROCK_WRAPPER_FALLBACK", "0")
    _install_bedrock(
        monkeypatch,
        lambda m: bc.BedrockResponse(error="api_access_denied_403", model=m),
    )
    spy: list = []
    _install_wrapper(monkeypatch, spy=spy)

    resp = bc.complete_with_fallback(
        bc.BedrockRequest(user="q", model="eu.anthropic.claude-opus-4-8")
    )

    assert spy == []
    assert resp.error == "api_access_denied_403"


def test_flag_is_read_fresh_per_call(monkeypatch):
    """A module-level constant would make an in-process A/B arm inert (R263.2)."""
    monkeypatch.setenv("REGENOLD_BEDROCK_WRAPPER_FALLBACK", "0")
    assert bc.wrapper_fallback_enabled() is False
    monkeypatch.setenv("REGENOLD_BEDROCK_WRAPPER_FALLBACK", "1")
    assert bc.wrapper_fallback_enabled() is True
    monkeypatch.delenv("REGENOLD_BEDROCK_WRAPPER_FALLBACK", raising=False)
    assert bc.wrapper_fallback_enabled() is True, "default must be ON"


def test_wrapper_failure_returns_bedrocks_error_not_a_synthetic_one(monkeypatch):
    _install_bedrock(
        monkeypatch,
        lambda m: bc.BedrockResponse(error="api_access_denied_403", model=m),
    )
    _install_wrapper(monkeypatch, resp=_FakeWrapperResp(text="", error="wrapper down"))

    resp = bc.complete_with_fallback(
        bc.BedrockRequest(user="q", model="eu.anthropic.claude-opus-4-8")
    )
    assert resp.error == "api_access_denied_403"


def test_wrapper_not_wired_is_a_clean_no_op(monkeypatch):
    _install_bedrock(
        monkeypatch,
        lambda m: bc.BedrockResponse(error="api_access_denied_403", model=m),
    )
    spy: list = []
    _install_wrapper(monkeypatch, enabled=False, spy=spy)

    resp = bc.complete_with_fallback(
        bc.BedrockRequest(user="q", model="eu.anthropic.claude-opus-4-8")
    )
    assert spy == []
    assert resp.error == "api_access_denied_403"


def test_hop_forwards_the_system_prompt_even_though_the_wrapper_drops_it(monkeypatch):
    """We still SEND it. The drop is the wrapper's, and it is why we mark the row.

    If we stopped sending it, flipping `WRAPPER_FORWARD_SYSTEM_PROMPT` on in the
    wrapper would silently change nothing here — an inert-feature trap one layer
    down.
    """
    _install_bedrock(
        monkeypatch,
        lambda m: bc.BedrockResponse(error="api_access_denied_403", model=m),
    )
    spy: list = []
    _install_wrapper(monkeypatch, spy=spy)

    bc.complete_with_fallback(
        bc.BedrockRequest(user="q", system="SYSTEM RULES", model="eu.anthropic.claude-opus-5")
    )
    assert spy and spy[0].system == "SYSTEM RULES"
    assert spy[0].user == "q"
