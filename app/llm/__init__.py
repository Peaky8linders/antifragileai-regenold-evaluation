"""LLM provider helpers — provider resolution.

Extracted from CodexAI's ``app/llm/``. The bundle supports three LLM
paths: the deterministic-fallback (``cli``), the Anthropic SDK direct
path, and the local ``openai_wrapper`` (Claude Max via the
``claude-code-openai-wrapper`` facade).
"""
from __future__ import annotations

from typing import Literal


def resolve_provider(
    env_value: str | None,
    *,
    default_when_auto: Literal[
        "openrouter", "bedrock", "anthropic", "cli", "openai_wrapper"
    ] = "openrouter",
) -> str:
    """Resolve the LLM provider for a feature.

    Honours an explicit ``openrouter`` / ``bedrock`` / ``anthropic`` /
    ``cli`` / ``openai_wrapper`` setting. On unset / empty / ``auto``,
    falls back to ``default_when_auto`` (``openrouter`` by default).
    """
    value = (env_value or "").strip().lower()
    if value in {
        "anthropic", "cli", "openai_wrapper", "groq", "gemini", "bedrock", "openrouter",
    }:
        return value
    if value in {"", "auto"}:
        return default_when_auto
    raise ValueError(f"Unsupported provider value: {value!r}")


__all__ = [
    "resolve_provider",
]
