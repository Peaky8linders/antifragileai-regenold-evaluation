"""FramesQA Query Rewriter Agent (R52 / Agentic RAG).

Dynamically refines search queries based on retrieved context or the
decomposed sub-queries. If a sub-query is vague, the Query Rewriter
expands it using domain knowledge or context from the original question.
"""
from __future__ import annotations

import logging
import os
import threading
import time

from app.llm.openai_wrapper_provider import (
    OpenAIWrapperRequest,
    get_openai_wrapper_provider,
    is_openai_wrapper_enabled,
)

logger = logging.getLogger(__name__)

# ── R377-C: circuit breaker ──────────────────────────────────────────────────
#
# This rewrite is a per-sub-query LLM hop in the HOT PATH, and it is hard-bound
# to ``get_openai_wrapper_provider()`` and the literal model
# ``claude-haiku-4-5-20251001`` regardless of ``P2P_GRAPH_RAG_PROVIDER``. Its
# gate is ``is_openai_wrapper_enabled()``, which returns True for every provider
# except ``cli`` -- so with the operator's pinned ``openrouter`` it still fires,
# still targets the CF-Access tunnel, and when that host is unreachable it pays
# the full ``_TIMEOUT`` per sub-query and returns the sub-query UNCHANGED.
#
# MEASURED LIVE 2026-08-23, P2P_GRAPH_RAG_PROVIDER=openrouter, one decomposed
# question with three sub-queries:
#     3690 ms  unchanged=True
#     3052 ms  unchanged=True
#     3026 ms  unchanged=True
#     TOTAL DEAD TIME 9.8 s, output byte-identical to the input.
# Latency is a scored axis, and the pushback turn decomposes to three
# sub-queries, so this was roughly two thirds of that turn's wall clock spent
# waiting for a host that answers nothing.
#
# The breaker keeps the feature EXACTLY as it is whenever the provider actually
# answers -- it only stops re-paying a timeout that has already failed
# ``_BREAKER_THRESHOLD`` times in a row, and it re-probes after the cooldown so
# a recovered wrapper heals itself. Deleting the hop outright was rejected: when
# the wrapper IS reachable this genuinely rewrites the sub-query, and that is an
# answer-affecting change owing its own gate.
_BREAKER_LOCK = threading.Lock()
_BREAKER_FAILS = 0
_BREAKER_OPEN_UNTIL = 0.0


def _breaker_enabled() -> bool:
    """Fresh env read per call (R263.2/R334). ``=0`` restores unbounded calling."""
    return os.getenv("REGENOLD_FRAMES_REWRITER_BREAKER", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def _breaker_threshold() -> int:
    try:
        return max(1, int(os.getenv("REGENOLD_FRAMES_REWRITER_BREAKER_FAILS", "2")))
    except ValueError:
        return 2


def _breaker_cooldown_s() -> float:
    try:
        return max(1.0, float(os.getenv("REGENOLD_FRAMES_REWRITER_BREAKER_COOLDOWN_S", "300")))
    except ValueError:
        return 300.0


def _breaker_is_open() -> bool:
    if not _breaker_enabled():
        return False
    with _BREAKER_LOCK:
        return time.monotonic() < _BREAKER_OPEN_UNTIL


def _breaker_record_failure() -> None:
    global _BREAKER_FAILS, _BREAKER_OPEN_UNTIL
    if not _breaker_enabled():
        return
    with _BREAKER_LOCK:
        _BREAKER_FAILS += 1
        if _BREAKER_FAILS >= _breaker_threshold():
            _BREAKER_OPEN_UNTIL = time.monotonic() + _breaker_cooldown_s()
            logger.info(
                "frames_rewriter_breaker_open after %d consecutive failures; "
                "skipping the rewrite hop for %.0fs",
                _BREAKER_FAILS,
                _breaker_cooldown_s(),
            )


def _breaker_record_success() -> None:
    global _BREAKER_FAILS, _BREAKER_OPEN_UNTIL
    with _BREAKER_LOCK:
        _BREAKER_FAILS = 0
        _BREAKER_OPEN_UNTIL = 0.0


def _reset_frames_breaker_for_tests() -> None:
    _breaker_record_success()

_SYSTEM_PROMPT = (
    "You are an AI assistant tasked with rewriting a sub-query to make it optimal "
    "for a BM25 and Vector search engine in the context of the EU AI Act.\n\n"
    "Your goal is to rewrite the sub-query to include relevant keywords, entities, "
    "or context from the original question that might have been lost during decomposition. "
    "Make it concise and highly searchable.\n\n"
    "CRITICAL TONE AND WORDING RULES:\n"
    "1. You must strictly respect and enforce the official professional tone and wording of the EU AI Act.\n"
    "2. Always use official terminology: \"provider\" (never developer/creator), \"deployer\" (never user/customer), \"operator\", \"importer\", \"distributor\", \"authorised representative\".\n"
    "3. Use official risk-tier classifications: \"prohibited AI practices\" (unacceptable risk), \"high-risk AI systems\", \"limited-risk AI systems\", \"minimal-risk\", \"general-purpose AI models\" (GPAI models).\n"
    "4. Phrasing must be neutral, objective, and in the third person. Do not address the reader as \"you\" (e.g. rewrite \"what are your duties\" to \"what are the provider's obligations\").\n"
    "5. Ensure citations use standard naming like \"Article N\" or \"Annex X\" where appropriate.\n"
    "6. Strictly preserve any specific regulatory topics, article references, deadlines, values (e.g. 'serious incident', 'reporting window', 'EUR 35M'), and specific use cases or domains from the original question. Do not generalize specific terms into broader categories.\n\n"
    "Return ONLY the rewritten sub-query text, with no preamble, quotes, or additional prose."
)

_USER_TEMPLATE = "Original Question: {original_question}\nSub-query: {sub_query}\n\nRewritten sub-query:"

_TIMEOUT = 3.0  # Allow up to 3 seconds for rewrite


def rewrite_sub_query_llm(sub_query: str, original_question: str) -> str:
    """Rewrite a decomposed sub-query to be optimal for BM25/Vector search.
    
    Adds relevant keywords or context from the original question if they were 
    lost during decomposition. Falls back to the original sub_query on any failure.
    """
    sub_query_clean = sub_query.strip()
    if not sub_query_clean:
        return sub_query

    if not is_openai_wrapper_enabled():
        return sub_query

    # R377-C -- do not re-pay a timeout that has already failed repeatedly.
    if _breaker_is_open():
        return sub_query

    try:
        provider = get_openai_wrapper_provider()
        start = time.perf_counter()
        resp = provider.complete(OpenAIWrapperRequest(
            system=_SYSTEM_PROMPT,
            user=_USER_TEMPLATE.format(
                original_question=original_question[:1000],
                sub_query=sub_query_clean[:500]
            ),
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            temperature=0.1,
            timeout_seconds=_TIMEOUT,
        ))
    except Exception as exc:  # fail-soft
        logger.debug("frames_rewriter_exception: %s", str(exc)[:160])
        _breaker_record_failure()
        return sub_query

    if resp.error:
        logger.debug("frames_rewriter_error: %s", resp.error[:160])
        _breaker_record_failure()
        return sub_query

    text = (resp.text or "").strip()
    # Strip any accidental quotes
    text = text.strip('\"\'').strip()
    
    if not text:
        return sub_query

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.debug("frames_rewriter_ok: rewritten in %d ms", elapsed_ms)
    _breaker_record_success()
    
    return text

