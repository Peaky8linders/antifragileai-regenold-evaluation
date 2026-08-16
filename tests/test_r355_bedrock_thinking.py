"""R355 — Bedrock extended thinking for the judge.

``BedrockRequest.thinking_budget > 0`` must emit the SNAKE_CASE Claude
thinking config inside ``additionalModelRequestFields`` (camelCase is
rejected by Bedrock), force ``temperature=1`` (Claude requirement when
thinking is enabled), and raise ``maxTokens`` above the budget (equal is
a validation 400). The judge caller in ``evals.judge.runner`` must read
``REGENOLD_BEDROCK_JUDGE_THINKING_TOKENS`` into the request.
"""
from __future__ import annotations

import pytest

from app.llm.bedrock_client import BedrockRequest, _build_converse_kwargs


def test_thinking_budget_zero_sends_no_thinking_config() -> None:
    kw = _build_converse_kwargs(BedrockRequest(model="claude-opus-4-6",
                                               user="hi",
                                               max_tokens=500))
    assert "additionalModelRequestFields" not in kw
    assert kw["inferenceConfig"]["temperature"] == 0.0


def test_thinking_budget_emits_snake_case_config() -> None:
    kw = _build_converse_kwargs(BedrockRequest(model="claude-opus-4-6",
                                               user="hi",
                                               max_tokens=2000,
                                               thinking_budget=1024))
    amrf = kw["additionalModelRequestFields"]
    assert amrf["reasoning_config"] == {
        "type": "enabled",
        "budget_tokens": 1024,
    }
    # camelCase must NOT be present — Bedrock rejects it ("Extra inputs").
    assert "reasoningConfig" not in amrf
    # Claude requires temperature == 1 when thinking is enabled.
    assert kw["inferenceConfig"]["temperature"] == 1.0


def test_thinking_budget_raises_max_tokens_above_budget() -> None:
    kw = _build_converse_kwargs(BedrockRequest(model="claude-opus-4-6",
                                               user="hi",
                                               max_tokens=500,
                                               thinking_budget=1024))
    # maxTokens must EXCEED the thinking budget or Bedrock 400s.
    assert kw["inferenceConfig"]["maxTokens"] > 1024


def test_thinking_budget_floored() -> None:
    kw = _build_converse_kwargs(BedrockRequest(model="claude-opus-4-6",
                                               user="hi",
                                               max_tokens=2000,
                                               thinking_budget=64))
    assert kw["additionalModelRequestFields"]["reasoning_config"][
        "budget_tokens"] == 256


def test_throttle_classified_retryable() -> None:
    """R355 — a Bedrock 429 must be retryable so the judge rides out
    rate-limit windows instead of erroring the row immediately."""
    from evals.judge.runner import is_retryable_judge_error

    assert is_retryable_judge_error("bedrock_error: api_throttled_429")
    assert is_retryable_judge_error("bedrock_error: something_429_boom")
    # Deterministic failures must stay non-retryable.
    assert not is_retryable_judge_error("bedrock_error: no_json")
    assert not is_retryable_judge_error("bedrock_error: authentication_failed")


@pytest.mark.parametrize("raw", ["", "0", "1024", " 512 ", "junk"])
def test_judge_caller_thinking_env(raw: str, monkeypatch) -> None:
    """REGENOLD_BEDROCK_JUDGE_THINKING_TOKENS lands on the request."""
    import evals.judge.runner as runner

    captured: dict[str, int] = {}

    class _FakeProvider:
        def complete(self, req: BedrockRequest):
            captured["budget"] = req.thinking_budget
            from app.llm.bedrock_client import BedrockResponse
            return BedrockResponse(text='{"verdict": "pass"}')

    # runner._call_judge_bedrock imports these inside the function body;
    # patch at the module-of-origin so the lazy import picks them up.
    monkeypatch.setattr("app.llm.bedrock_client.complete_with_fallback",
                        lambda req: _FakeProvider().complete(req))
    monkeypatch.setattr("app.llm.bedrock_client.is_bedrock_provider_enabled",
                        lambda: True)
    monkeypatch.setattr("app.llm.bedrock_client.resolve_bedrock_model",
                        lambda m: f"eu.{m}")
    monkeypatch.setenv("REGENOLD_BEDROCK_JUDGE_THINKING_TOKENS", raw)

    expected = 0
    if raw.strip().isdigit() and raw.strip():
        expected = int(raw.strip())
    runner._JUDGE_MODEL = "claude-opus-4-6"
    out = runner._call_judge_bedrock("judge me", timeout_s=30.0)
    assert out.get("verdict") == "pass" or "judge_error" in out
    assert captured["budget"] == expected
