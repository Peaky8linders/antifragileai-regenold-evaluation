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
# ``[^>]*`` was unbounded, so a "<" ... ">" span whose first token happened to
# be one of these keywords swallowed every word between them: measured,
# sanitize_for_llm("Compare a < answer and b > answer thresholds") deleted four
# words of the user question. Attributes cannot contain "<".
_XML_CHANNEL_TAGS = re.compile(
    r"</?(?:answer|reasoning|reasoning_scratchpad|scratchpad|think)(?:\s+[^<>]{0,200})?>",
    re.IGNORECASE,
)

# Qwen 3 (and similar open-reasoning models) can leak their chain-of-thought
# as a literal <think>…</think> block at the start of the generated text when
# reasoning is not fully disabled server-side.  Strip it defensively here so
# every call-site that goes through validate_llm_output() is protected.
_THINK_BLOCK_RE = re.compile(r"<\s*think(?:\s+[^>]*)?>.*?</\s*think\s*>\s*", re.DOTALL | re.IGNORECASE)
# Anchored to the START: a leaked CoT block is a PREFIX phenomenon (see the
# note above). Unanchored, this deleted everything from the first literal
# "<think" onward — so a legitimate answer that merely MENTIONS the tag
# ("We reject the <think> convention. Article 50 applies.") shipped as
# "We reject the", non-empty and therefore past the empty-answer guard.
_UNCLOSED_THINK_RE = re.compile(r"^\s*<\s*think(?:\s+[^>]*)?>.*$", re.DOTALL | re.IGNORECASE)
# The SHIPPED V2 prompt asks for private reasoning in <reasoning_scratchpad>
# (graph_rag_prompts.py, ANSWER_GENERATE_SYSTEM_V2 + USER_CHALLENGE_BREVITY_CLAUSE_V2),
# so a max_tokens cut mid-scratchpad leaves that block UNCLOSED. Only <think>
# had an unclosed-case guard, so the model's raw deliberation — "The user
# disputes the prior answer..." — was returned verbatim as the user-facing
# legal answer, non-empty and therefore past the empty-answer guard.
_UNCLOSED_REASONING_RE = re.compile(
    r"^\s*<\s*(?:reasoning|reasoning_scratchpad|scratchpad)(?:\s+[^>]*)?>.*$",
    re.DOTALL | re.IGNORECASE,
)

_REASONING_BLOCK_RE = re.compile(
    r"<\s*(?:reasoning|reasoning_scratchpad|scratchpad)(?:\s+[^>]*)?>(.*?)<\s*/\s*(?:reasoning|reasoning_scratchpad|scratchpad)\s*>",
    re.DOTALL | re.IGNORECASE,
)
_ANSWER_BLOCK_RE = re.compile(
    r"<\s*answer(?:\s+[^>]*)?>(.*?)<\s*/\s*answer\s*>",
    re.DOTALL | re.IGNORECASE,
)
_XML_CHANNELS_STRIP_RE = re.compile(
    r"<\s*/?\s*(?:answer|reasoning|reasoning_scratchpad|scratchpad|think)(?:\s+[^>]*)?>",
    re.IGNORECASE,
)


def extract_xml_channels(text: str | None) -> tuple[str, str]:
    """Extract (clean_answer, extracted_reasoning) from model output.

    Supports <reasoning> / <reasoning_scratchpad> / <scratchpad> / <think> and <answer>.
    If <answer> tags are present, extracts their inner content as the answer.
    If omitted or unclosed, strips any reasoning / think blocks to isolate the clean answer.
    """
    if text is None or not text:
        return "", ""

    reasoning_parts: list[str] = []
    for m in _REASONING_BLOCK_RE.finditer(text):
        content = m.group(1).strip()
        if content:
            reasoning_parts.append(content)
    # Also extract completed <think>...</think> blocks from open-reasoning models
    think_inner_re = re.compile(r"<\s*think(?:\s+[^>]*)?>(.*?)<\s*/\s*think\s*>", re.DOTALL | re.IGNORECASE)
    for m in think_inner_re.finditer(text):
        content = m.group(1).strip()
        if content:
            reasoning_parts.append(content)
    extracted_reasoning = "\n\n".join(reasoning_parts)

    # 1. Strip reasoning and think blocks first so inner <answer> quotes inside reasoning scratchpads do not hijack the answer
    text_without_reasoning = _THINK_BLOCK_RE.sub("", _REASONING_BLOCK_RE.sub("", text)).strip()
    text_without_reasoning = _UNCLOSED_THINK_RE.sub("", text_without_reasoning).strip()
    text_without_reasoning = _UNCLOSED_REASONING_RE.sub("", text_without_reasoning).strip()

    answer_matches = list(_ANSWER_BLOCK_RE.finditer(text_without_reasoning))
    if answer_matches:
        raw_ans = answer_matches[-1].group(1).strip()
        clean_answer = _XML_CHANNELS_STRIP_RE.sub("", _THINK_BLOCK_RE.sub("", raw_ans)).strip()
    else:
        # Fallback when model omitted full <answer>...</answer> tags:
        cleaned = _XML_CHANNELS_STRIP_RE.sub("", text_without_reasoning).strip()
        clean_answer = cleaned

    return clean_answer, extracted_reasoning


_THINK_BLOCK_KEEP_WS_RE = re.compile(
    r"<\s*think(?:\s+[^>]*)?>.*?<\s*/\s*think\s*>", re.DOTALL | re.IGNORECASE
)


def strip_reasoning_keep_boundary(text: str | None) -> str:
    """Remove reasoning / think channels WITHOUT touching surrounding whitespace.

    :func:`validate_llm_output` ``.strip()``s its result, which is right for a
    whole answer and WRONG for a fragment whose LEADING WHITESPACE carries
    meaning. The R357 Stage-2 tail repair encodes the word boundary exactly
    that way (a leading space means "the cut landed between words"), so it
    needs the channels gone and the whitespace kept.
    """
    if not text:
        return ""
    out = _REASONING_BLOCK_RE.sub("", text)
    out = _THINK_BLOCK_KEEP_WS_RE.sub("", out)
    out = _UNCLOSED_THINK_RE.sub("", out)
    out = _UNCLOSED_REASONING_RE.sub("", out)
    return out


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
    out = _XML_CHANNEL_TAGS.sub(" ", out)
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
    stripped = _UNCLOSED_THINK_RE.sub("", stripped).strip()
    stripped = _UNCLOSED_REASONING_RE.sub("", stripped).strip()
    _low = text.lower()
    if not stripped and (
        "<think" in _low or "<reasoning" in _low or "<scratchpad" in _low
    ):
        return ""
    return stripped or text

