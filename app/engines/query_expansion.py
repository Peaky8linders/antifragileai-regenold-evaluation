"""RAG-Fusion query expansion + reciprocal rank fusion (R39 / B8).

When the wrapper is wired and the intent suggests a single-anchor
question, ask Haiku 4.5 for 3 paraphrases. Each paraphrase runs through
the existing retrieval stack independently; reciprocal rank fusion (RRF)
combines the result lists.

Fail-soft: wrapper disabled / circuit open / any exception → return
[original] only.
"""
from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Iterable

from app.llm.openai_wrapper_provider import (
    OpenAIWrapperRequest,
    get_openai_wrapper_provider,
    is_openai_wrapper_enabled,
)

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = (
    "You generate 2-3 paraphrases of EU AI Act questions for retrieval "
    "expansion. Each paraphrase keeps the same factual question but "
    "varies phrasing using professional and precise compliance terminology (focusing on formal legal phrasings, specific regulatory terms, and general compliance concepts).\n\n"
    "CRITICAL TONE AND WORDING RULES:\n"
    "1. Strictly respect and enforce the official professional tone and wording of the EU AI Act. Do not use informal or non-professional language.\n"
    "2. Always use official terminology: \"provider\" (never developer/creator), \"deployer\" (never user/customer), \"operator\", \"importer\", \"distributor\", \"authorised representative\".\n"
    "3. Use official risk-tier classifications: \"prohibited AI practices\" (unacceptable risk), \"high-risk AI systems\", \"limited-risk AI systems\", \"minimal-risk\", \"general-purpose AI models\" (GPAI models).\n"
    "4. Phrasing must be neutral, objective, and in the third person. Do not address the reader as \"you\".\n\n"
    'Respond with STRICT JSON: {"paraphrases": ["...", "..."]}. No prose.'
)

_USER_TEMPLATE = "Question: {q}\n\nReturn 2-3 paraphrases as JSON."

_TIMEOUT = 2.0  # short budget — paraphrase is opportunistic

# ── Call instrumentation (R341, mirroring cohere_rerank's R331 counters) ────
#
# The R329 lesson: a placement that looks right in the diff but never issues
# its call reads +0.0000 on every axis, indistinguishable from "the lever
# does not work". Every A/B of this feature must assert
# ``query_expansion_stats()["attempts"] > 0`` on the ON arm before any
# result is believed.
_STATS: dict[str, int] = {"attempts": 0, "expanded": 0, "failed": 0}


def query_expansion_stats() -> dict[str, int]:
    """Snapshot of the expansion call counters.

    ``attempts`` — LLM calls actually issued to the paraphrase provider.
    ``expanded`` — total paraphrase count returned (the union surface).
    ``failed``   — attempts that produced zero paraphrases.

    ``attempts == 0`` means the feature never ran; treat any downstream
    metric as UNMEASURED, not as evidence of no effect.
    """
    return dict(_STATS)


def reset_query_expansion_stats() -> None:
    """Zero the counters — per-arm reset for an A/B harness."""
    for key in _STATS:
        _STATS[key] = 0


def _bump(field: str) -> None:
    _STATS[field] = _STATS.get(field, 0) + 1


_ENV_GATE = "REGENOLD_QUERY_EXPANSION"


def is_enabled() -> bool:
    """``REGENOLD_QUERY_EXPANSION`` — **DEFAULT OFF**, fresh env read per call.

    Default OFF because it adds an LLM round-trip per request (latency + cost)
    and external egress of the partner question; the A/B decides whether the
    recall it buys beats that price. Fresh read per call (R263.2) so an
    in-process A/B can flip it between arms.
    """
    return (
        os.getenv(_ENV_GATE, "0").strip().lower()
        in ("1", "true", "yes", "on")
    )


def expand_query(question: str, *, intent_label: str = "") -> list[str]:
    """Return list of queries (original first, then paraphrases).

    Always includes the original. Returns [original] on any failure
    path (no wrapper, circuit open, parse error, timeout).
    """
    queries = [question.strip()]
    if not queries[0]:
        return queries
    if not is_openai_wrapper_enabled():
        return queries
    _bump("attempts")
    try:
        provider = get_openai_wrapper_provider()
        start = time.perf_counter()
        resp = provider.complete(OpenAIWrapperRequest(
            system=_SYSTEM_PROMPT,
            user=_USER_TEMPLATE.format(q=queries[0][:1000]),
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            temperature=0.3,
            timeout_seconds=_TIMEOUT,
        ))
    except Exception as exc:  # noqa: BLE001 — fail-soft
        logger.debug("query_expansion_exception: %s", str(exc)[:160])
        _bump("failed")
        return queries
    if resp.error:
        logger.debug("query_expansion_provider_error: %s", resp.error[:160])
        _bump("failed")
        return queries
    try:
        # Extract first JSON object from response text
        text = (resp.text or "").strip()
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx == -1 or end_idx == -1:
            _bump("failed")
            return queries
        data = json.loads(text[start_idx:end_idx + 1])
        for p in (data.get("paraphrases") or [])[:3]:
            p = (p or "").strip()
            if p and p not in queries:
                queries.append(p)
    except (json.JSONDecodeError, ValueError, AttributeError):
        _bump("failed")
        return queries
    if len(queries) == 1:
        # The provider answered but produced no usable paraphrase — an
        # attempt that bought nothing.
        _bump("failed")
        return queries
    _bump("expanded")
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.debug("query_expansion_ok: %d paraphrases in %d ms", len(queries) - 1, elapsed_ms)
    return queries


def reciprocal_rank_fusion(
    ranked_lists: Iterable[Iterable[str]],
    k: int = 60,
) -> list[str]:
    """Combine multiple ranked lists via RRF.

    score(d) = sum_l 1 / (k + rank_l(d)). Default k=60 per the
    canonical Cormack et al. 2009 paper.
    """
    scores: dict[str, float] = {}
    insertion_order: dict[str, int] = {}
    n_inserted = 0
    for lst in ranked_lists:
        for rank, doc in enumerate(lst, start=1):
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank)
            if doc not in insertion_order:
                insertion_order[doc] = n_inserted
                n_inserted += 1
    # Sort by score desc, then by insertion order asc (stable tie-break)
    return sorted(scores.keys(), key=lambda d: (-scores[d], insertion_order[d]))
