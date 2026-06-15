"""Tests for the Mixture-of-Agents fusion Stage-2 (app/engines/fusion.py).

Hermetic — every test monkeypatches the provider getters so no network /
wrapper / Groq / Mistral call is made. Covers the env gating, the Mistral
provider wiring, panel resolution, and the fail-soft contract of
``fusion_complete`` (≥min drafts → judge fuses; below → None; judge
error/empty/truncated → None; never raises).
"""
from __future__ import annotations

import pytest

from app.engines import fusion
from app.llm import openai_wrapper_provider as owp
from app.llm.openai_wrapper_provider import OpenAIWrapperResponse


# ── env gating ────────────────────────────────────────────────────────────────

def test_fusion_enabled_default_on(monkeypatch):
    monkeypatch.delenv("REGENOLD_FUSION_STAGE2", raising=False)
    assert fusion.fusion_stage2_enabled() is True


@pytest.mark.parametrize("val", ["0", "false", "no", "off", "FALSE", ""])
def test_fusion_disabled_by_env(monkeypatch, val):
    monkeypatch.setenv("REGENOLD_FUSION_STAGE2", val)
    assert fusion.fusion_stage2_enabled() is False


def test_fusion_enabled_explicit_on(monkeypatch):
    monkeypatch.setenv("REGENOLD_FUSION_STAGE2", "1")
    assert fusion.fusion_stage2_enabled() is True


# ── Mistral provider wiring ─────────────────────────────────────────────────────

def test_mistral_provider_gate(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    assert owp.is_mistral_provider_enabled() is False
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-mistral-test")
    assert owp.is_mistral_provider_enabled() is True


def test_mistral_provider_singleton_base_url(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "sk-mistral-test")
    monkeypatch.delenv("MISTRAL_API_BASE", raising=False)
    owp._reset_mistral_singleton_for_tests()
    try:
        prov = owp.get_mistral_provider()
        assert prov is owp.get_mistral_provider()  # pooled singleton
        assert prov._base_url == "https://api.mistral.ai/v1"  # noqa: SLF001
    finally:
        owp._reset_mistral_singleton_for_tests()


# ── panel resolution ─────────────────────────────────────────────────────────

def test_enabled_panel_filters_unavailable(monkeypatch):
    monkeypatch.delenv("REGENOLD_FUSION_PANEL", raising=False)
    monkeypatch.setattr(owp, "is_openai_wrapper_enabled", lambda: True)
    monkeypatch.setattr(owp, "is_groq_provider_enabled", lambda: True)
    monkeypatch.setattr(owp, "is_mistral_provider_enabled", lambda: False)
    panel = fusion._enabled_panel()
    labels = [p[0] for p in panel]
    assert "sonnet" in labels and "groq" in labels
    assert "mistral" not in labels  # transport unavailable -> filtered


def test_enabled_panel_custom_env(monkeypatch):
    monkeypatch.setenv("REGENOLD_FUSION_PANEL", "groq, mistral")
    monkeypatch.setattr(owp, "is_openai_wrapper_enabled", lambda: True)
    monkeypatch.setattr(owp, "is_groq_provider_enabled", lambda: True)
    monkeypatch.setattr(owp, "is_mistral_provider_enabled", lambda: True)
    panel = fusion._enabled_panel()
    labels = [p[0] for p in panel]
    assert labels == ["groq", "mistral"]  # sonnet not requested


# ── fusion_complete fail-soft contract ──────────────────────────────────────────

class _FakeProvider:
    """A pooled-provider stand-in. ``script`` maps model id -> response."""

    def __init__(self, script):
        self._script = script

    def complete(self, req):
        fn = self._script.get(req.model)
        if fn is None:
            return OpenAIWrapperResponse(error="no_script", model=req.model)
        return fn(req)


def _wire_three_transports(monkeypatch, *, wrapper, groq, mistral):
    """Make sonnet/groq/mistral the live panel + route the judge."""
    monkeypatch.delenv("REGENOLD_FUSION_PANEL", raising=False)
    monkeypatch.setattr(owp, "is_openai_wrapper_enabled", lambda: True)
    monkeypatch.setattr(owp, "is_groq_provider_enabled", lambda: True)
    monkeypatch.setattr(owp, "is_mistral_provider_enabled", lambda: True)
    monkeypatch.setattr(owp, "get_openai_wrapper_provider", lambda: wrapper)
    monkeypatch.setattr(owp, "get_groq_provider", lambda: groq)
    monkeypatch.setattr(owp, "get_mistral_provider", lambda: mistral)
    # Avoid the heavy graph_rag import in the truncation check.
    monkeypatch.setattr(fusion, "_looks_truncated", lambda _t: False)


def test_fusion_complete_happy_path(monkeypatch):
    # Sonnet (wrapper) is also the judge transport — keyed by model id.
    wrapper = _FakeProvider({
        "claude-sonnet-4-6": lambda r: OpenAIWrapperResponse(
            text="Article 50 requires the deployer to inform exposed persons."
        ),
        "claude-opus-4-8": lambda r: OpenAIWrapperResponse(
            text="Article 50 obliges the deployer to inform exposed natural "
                 "persons; Article 26 adds high-risk deployer duties."
        ),
    })
    groq = _FakeProvider({
        "llama-3.3-70b-versatile": lambda r: OpenAIWrapperResponse(
            text="Deployers must inform people under Article 50."
        )
    })
    mistral = _FakeProvider({
        "mistral-large-latest": lambda r: OpenAIWrapperResponse(
            text="Article 50 transparency applies to the deployer."
        )
    })
    _wire_three_transports(monkeypatch, wrapper=wrapper, groq=groq, mistral=mistral)

    out = fusion.fusion_complete(
        system="SYS", user="QUESTION: x\n\nEU AI ACT REFERENCES:\n- Article 50",
        max_tokens=512,
    )
    assert out is not None
    assert "Article 50" in out and "Article 26" in out  # judge synthesis text


def test_fusion_complete_insufficient_live_panel_returns_none(monkeypatch):
    # Only the wrapper transport is live -> 1 panel member < min 2 -> None.
    monkeypatch.delenv("REGENOLD_FUSION_PANEL", raising=False)
    monkeypatch.setattr(owp, "is_openai_wrapper_enabled", lambda: True)
    monkeypatch.setattr(owp, "is_groq_provider_enabled", lambda: False)
    monkeypatch.setattr(owp, "is_mistral_provider_enabled", lambda: False)
    out = fusion.fusion_complete(system="SYS", user="QUESTION: x", max_tokens=512)
    assert out is None


def test_fusion_complete_too_few_drafts_returns_none(monkeypatch):
    # Panel is live but every member errors -> 0 drafts < min -> None.
    err = _FakeProvider({})  # every model -> "no_script" error
    _wire_three_transports(monkeypatch, wrapper=err, groq=err, mistral=err)
    out = fusion.fusion_complete(system="SYS", user="QUESTION: x", max_tokens=512)
    assert out is None


def test_fusion_complete_judge_error_returns_none(monkeypatch):
    wrapper = _FakeProvider({
        "claude-sonnet-4-6": lambda r: OpenAIWrapperResponse(text="draft A"),
        "claude-opus-4-8": lambda r: OpenAIWrapperResponse(error="api_status_500"),
    })
    ok = _FakeProvider({
        "llama-3.3-70b-versatile": lambda r: OpenAIWrapperResponse(text="draft B"),
        "mistral-large-latest": lambda r: OpenAIWrapperResponse(text="draft C"),
    })
    _wire_three_transports(monkeypatch, wrapper=wrapper, groq=ok, mistral=ok)
    out = fusion.fusion_complete(system="SYS", user="QUESTION: x", max_tokens=512)
    assert out is None  # judge failed -> fall through to single-provider path


def test_fusion_complete_judge_empty_returns_none(monkeypatch):
    wrapper = _FakeProvider({
        "claude-sonnet-4-6": lambda r: OpenAIWrapperResponse(text="draft A"),
        "claude-opus-4-8": lambda r: OpenAIWrapperResponse(text="   "),
    })
    ok = _FakeProvider({
        "llama-3.3-70b-versatile": lambda r: OpenAIWrapperResponse(text="draft B"),
        "mistral-large-latest": lambda r: OpenAIWrapperResponse(text="draft C"),
    })
    _wire_three_transports(monkeypatch, wrapper=wrapper, groq=ok, mistral=ok)
    assert fusion.fusion_complete(system="SYS", user="Q", max_tokens=512) is None


def test_fusion_complete_judge_truncated_returns_none(monkeypatch):
    wrapper = _FakeProvider({
        "claude-sonnet-4-6": lambda r: OpenAIWrapperResponse(text="draft A"),
        "claude-opus-4-8": lambda r: OpenAIWrapperResponse(
            text="Article 50 requires", finish_reason="length"
        ),
    })
    ok = _FakeProvider({
        "llama-3.3-70b-versatile": lambda r: OpenAIWrapperResponse(text="draft B"),
        "mistral-large-latest": lambda r: OpenAIWrapperResponse(text="draft C"),
    })
    _wire_three_transports(monkeypatch, wrapper=wrapper, groq=ok, mistral=ok)
    assert fusion.fusion_complete(system="SYS", user="Q", max_tokens=512) is None


def test_fusion_complete_never_raises(monkeypatch):
    class _Boom:
        def complete(self, req):
            raise RuntimeError("transport blew up")

    boom = _Boom()
    _wire_three_transports(monkeypatch, wrapper=boom, groq=boom, mistral=boom)
    # Panel members raise -> caught per-member -> 0 drafts -> None, no exception.
    assert fusion.fusion_complete(system="SYS", user="Q", max_tokens=512) is None


# ── cache-key invalidation ──────────────────────────────────────────────────────

def test_engine_cache_key_includes_fusion_flag(monkeypatch):
    from app.routes.regenold import _engine_cache_key

    monkeypatch.setenv("REGENOLD_FUSION_STAGE2", "1")
    k_on = _engine_cache_key("q", None)
    monkeypatch.setenv("REGENOLD_FUSION_STAGE2", "0")
    k_off = _engine_cache_key("q", None)
    assert k_on != k_off  # flipping fusion invalidates the cache identity


def test_engine_cache_key_includes_judge_model(monkeypatch):
    from app.routes.regenold import _engine_cache_key

    monkeypatch.setenv("REGENOLD_FUSION_JUDGE_MODEL", "claude-opus-4-8")
    k_a = _engine_cache_key("q", None)
    monkeypatch.setenv("REGENOLD_FUSION_JUDGE_MODEL", "claude-sonnet-4-6")
    k_b = _engine_cache_key("q", None)
    assert k_a != k_b
