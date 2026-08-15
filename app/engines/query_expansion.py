"""RAG-Fusion query expansion + reciprocal rank fusion (R39 / B8).

When a paraphrase provider is available and the intent suggests a
single-anchor question, ask Sonnet 4.6 (the frontier tier — no Haiku,
R346.2) for 3 paraphrases. Each paraphrase runs through the existing
retrieval stack independently; reciprocal rank fusion (RRF) combines the
result lists.

R346 — the paraphrase transport follows the ACTIVE Stage-2 provider:
under ``P2P_GRAPH_RAG_PROVIDER=bedrock`` the call goes to Bedrock's own
Sonnet 4.6, NOT the Claude-Max wrapper — the operator keeps the tunnel
for the live re-evaluation, and mixing transports mid-A/B contaminates
both arms. Every other provider keeps the historical wrapper path.

Fail-soft: no provider / circuit open / any exception → return
[original] only.
"""
from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Iterable
from typing import Any

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

_TIMEOUT = 2.0  # short budget — paraphrase is opportunistic (wrapper)

# R346 — Bedrock's first call carries cold-start latency the local wrapper
# does not; a 2 s budget there would fail every paraphrase and read as an
# inert lever (attempts>0, expanded=0, branch == baseline on the wire).
_BEDROCK_TIMEOUT = float(os.getenv(
    "REGENOLD_QUERY_EXPANSION_BEDROCK_TIMEOUT", "8.0"
))

# R346.2 — NO Haiku on the live path: paraphrases use the frontier tier like
# every other Stage-2 call. Sonnet 4.6 is the default (the judge tier — a
# paraphrase is a light task, Opus would buy nothing), pinned up with
# ``REGENOLD_QUERY_EXPANSION_MODEL=claude-opus-4-6`` if the operator wants
# the generation tier. Fresh read per call (R263.2).
_DEFAULT_PARAPHRASE_MODEL = "claude-sonnet-4-6"


def _paraphrase_model() -> str:
    return (
        os.getenv("REGENOLD_QUERY_EXPANSION_MODEL", "").strip()
        or _DEFAULT_PARAPHRASE_MODEL
    )

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


def _paraphrase_provider_available() -> bool:
    """True when SOME provider can serve the paraphrase call.

    R346 — the historical gate (``is_openai_wrapper_enabled``) silently
    disables expansion on a Bedrock-only run, where the wrapper is not the
    transport by design. Bedrock counts as available when selected AND
    its credentials are present.
    """
    if is_openai_wrapper_enabled():
        return True
    if os.getenv("P2P_GRAPH_RAG_PROVIDER", "").strip().lower() == "bedrock":
        try:
            from app.llm.bedrock_client import (  # noqa: PLC0415
                is_bedrock_provider_enabled,
            )
            return is_bedrock_provider_enabled()
        except Exception:  # noqa: BLE001 — boto3 is an optional wheel
            return False
    return False


def _complete_paraphrase(user: str) -> Any:
    """One paraphrase completion through the ACTIVE provider.

    Returns an object carrying ``.text`` / ``.error`` — both the wrapper's
    ``OpenAIWrapperResponse`` and ``BedrockResponse`` satisfy that shape,
    so the caller never branches on transport.
    """
    if os.getenv("P2P_GRAPH_RAG_PROVIDER", "").strip().lower() == "bedrock":
        try:
            from app.llm.bedrock_client import (  # noqa: PLC0415
                BedrockRequest,
                complete_with_fallback,
                is_bedrock_provider_enabled,
            )
            if is_bedrock_provider_enabled():
                return complete_with_fallback(BedrockRequest(
                    system=_SYSTEM_PROMPT,
                    user=user,
                    # R346.2 — frontier tier: alias -> eu.anthropic.claude-sonnet-4-6.
                    model=_paraphrase_model(),
                    max_tokens=200,
                    temperature=0.3,
                    timeout_seconds=_BEDROCK_TIMEOUT,
                ))
        except Exception as exc:  # noqa: BLE001 — fail-soft
            logger.debug(
                "query_expansion_bedrock_unavailable: %s", str(exc)[:160]
            )
    # Historical path: Claude Max via the wrapper (OPENAI_API_BASE).
    return get_openai_wrapper_provider().complete(OpenAIWrapperRequest(
        system=_SYSTEM_PROMPT,
        user=user,
        # R346.2 — frontier tier, same env override as the Bedrock path.
        model=_paraphrase_model(),
        max_tokens=200,
        temperature=0.3,
        timeout_seconds=_TIMEOUT,
    ))


def expand_query(question: str, *, intent_label: str = "") -> list[str]:
    """Return list of queries (original first, then paraphrases).

    Always includes the original. Returns [original] on any failure
    path (no provider, circuit open, parse error, timeout).
    """
    queries = [question.strip()]
    if not queries[0]:
        return queries
    if not _paraphrase_provider_available():
        return queries
    _bump("attempts")
    try:
        start = time.perf_counter()
        resp = _complete_paraphrase(_USER_TEMPLATE.format(q=queries[0][:1000]))
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
