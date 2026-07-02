"""Minimal LLM input/output sanitisation.

Stripped-down extract — preserves the public API used by ``graph_rag.py``
without the full CodexAI defense suite. Partners running this bundle in
production should swap in their own input-validator middleware.
"""
from __future__ import annotations

import re
import unicodedata

# Prefix prepended to every system prompt. Empty string is the safe
# default — kept as a hook so a partner deploy can opt in to a
# hardening preamble without modifying call sites.
PROMPT_HARDENING_PREFIX: str = ""


_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_TAGS_TO_STRIP = re.compile(
    r"<\|(?:im_start|im_end|endoftext|system|user|assistant|"
    r"begin_of_text|end_of_text|start_header_id|end_header_id)\|>",
    re.IGNORECASE,
)
_INSTR_TAGS = re.compile(r"\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>", re.IGNORECASE)
_USER_QUERY_TAGS = re.compile(r"</?user_query>", re.IGNORECASE)

# Qwen 3 (and similar open-reasoning models) can leak their chain-of-thought
# as a literal <think>…</think> block at the start of the generated text when
# reasoning is not fully disabled server-side.  Strip it defensively here so
# every call-site that goes through validate_llm_output() is protected.
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)


def sanitize_for_llm(user_input: str, *, context_type: str = "query") -> str:
    """Strip control chars, model-delimiter sequences, and prompt-tag spans.

    ``context_type`` is accepted for API parity with CodexAI's full
    sanitiser — currently the same path is taken for every value.
    """
    if not user_input:
        return ""
    out = unicodedata.normalize("NFKC", user_input)
    out = _CONTROL_CHARS.sub(" ", out)
    out = _TAGS_TO_STRIP.sub(" ", out)
    out = _INSTR_TAGS.sub(" ", out)
    out = _USER_QUERY_TAGS.sub(" ", out)
    return out.strip()


def validate_llm_output(text: str | None) -> str:
    """Validate engine output. In this minimal bundle we pass through
    unchanged; CodexAI's full version strips system-prompt leakage and
    PII. Override if a partner deploy needs the heavier surface.

    Null-safety: ``None`` and empty input both return ``""``. The caller
    decides whether an empty string means "Stage-2 produced no output"
    (a failure) or "engine wants to short-circuit" (intentional). Issue
    #42 caught the former case being silently treated as a success.

    Defensive strip: Qwen 3 models on Groq can leak raw chain-of-thought
    tokens into ``content`` as a ``<think>…</think>`` block when
    ``reasoning_effort`` is non-zero.  Strip it so callers always receive
    the final answer only.
    """
    if text is None:
        return ""
    if not text:
        return ""
    stripped = _THINK_BLOCK_RE.sub("", text).strip()
    return stripped or text  # fall back to original if stripping emptied it
