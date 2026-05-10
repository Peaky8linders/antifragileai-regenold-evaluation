"""LLM provider helpers — provider resolution + Mistral facade.

Extracted from CodexAI's ``app/llm/``. The Mistral provider is a stub
shape-only adapter — the partner is expected to plug in their own
credentials or run the engine through the deterministic-fallback path
which doesn't require any LLM key.
"""
from __future__ import annotations

import os
from typing import Literal

from app.llm.mistral_provider import (
    MistralRequest,
    MistralResponse,
    get_mistral_provider,
    is_mistral_enabled,
)


def resolve_provider(
    env_value: str | None,
    *,
    default_when_auto: Literal["anthropic", "mistral", "cli"] = "anthropic",
) -> str:
    """Resolve the LLM provider for a feature.

    Honours an explicit ``mistral`` / ``anthropic`` / ``cli`` /
    ``openai_wrapper`` setting. On unset / empty / ``auto``, picks
    ``mistral`` if ``MISTRAL_API_KEY`` is set, otherwise falls back
    to ``default_when_auto``.

    ``openai_wrapper`` routes through ``OPENAI_API_BASE`` (default
    ``http://127.0.0.1:8000/v1``) — used by the partner bundle to A/B
    Sonnet 4.6 against Mistral via the local
    ``claude-code-openai-wrapper`` (or any OpenAI-compatible facade).
    """
    value = (env_value or "").strip().lower()
    if value in {"mistral", "anthropic", "cli", "openai_wrapper"}:
        return value
    if value in {"", "auto"}:
        if os.getenv("MISTRAL_API_KEY"):
            return "mistral"
        return default_when_auto
    raise ValueError(f"Unsupported provider value: {value!r}")


__all__ = [
    "resolve_provider",
    "MistralRequest",
    "MistralResponse",
    "get_mistral_provider",
    "is_mistral_enabled",
]
