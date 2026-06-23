"""LLM-driven Planner Agent for FramesQA multi-hop decomposition.

This implements the Planner Agent from the Google FramesQA Agentic RAG methodology.
It uses the existing LLM provider wrapper to intelligently decompose complex
compliance questions into actionable sub-queries. It falls back to the
deterministic `sufficient_context.decompose_question` on any failure.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.engines.sufficient_context import decompose_question as deterministic_decompose
from app.llm.intent_classifier import _resolve_intent_provider, is_intent_enabled
from app.llm.openai_wrapper_provider import OpenAIWrapperRequest
from app.security.prompt_guard import sanitize_for_llm

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a Planner Agent for an EU AI Act RAG system.
Your task is to decompose a complex compliance question into simpler, self-contained sub-queries that can be run against a search engine.
Ensure that the sub-queries strictly respect and enforce the official professional tone and wording of the EU AI Act:
1. Use official terminology: "provider" (not "developer" or "creator"), "deployer" (not "user" or "customer"), "importer", "distributor", "authorised representative", "operator".
2. Refer to AI systems and risk tiers using official classifications: "unacceptable risk / prohibited AI practices", "high-risk AI systems", "limited-risk AI systems" (transparency-only), "minimal-risk", and "general-purpose AI models" (GPAI models).
3. Do not address the reader as "you" or use informal phrasing. All sub-queries must be phrased in a neutral, professional, and precise regulatory compliance register.
4. Keep the queries concise and focused on regulatory facts.

CRITICAL RULE: If the question is simple, asks for a specific fact (e.g., a deadline, a fine amount), or is focused on a single topic (e.g., whether credit-scoring is high-risk, whether FRIA is voluntary, or general incident reporting), DO NOT decompose it. Output a list containing ONLY the original question. Decomposition is reserved for multi-hop questions with distinct roles or multiple independent clauses.

If the question is already simple and doesn't need decomposition, output a list with just the original question.
Otherwise, break it down into 2 to 4 actionable sub-queries.

Emit ONLY a JSON array of strings. No prose, no markdown fences.
Example:
["What are the obligations for providers of high-risk AI systems?", "Are there specific transparency requirements for providers?"]"""

_USER_TEMPLATE = "Question: {q}\n\nJSON:"


def decompose_question_llm(question: str) -> list[str]:
    """Decompose a complex question into sub-queries using the LLM.
    
    Falls back to the deterministic decomposition if the LLM call fails,
    returns an invalid format, or if the intent provider is disabled.
    """
    fallback = deterministic_decompose(question)
    
    if not question or not is_intent_enabled():
        return fallback
        
    sanitised = sanitize_for_llm(question.strip(), context_type="query")
    if not sanitised:
        return fallback
        
    try:
        selection = _resolve_intent_provider()
    except Exception as exc:  # noqa: BLE001
        logger.debug("frames_planner_provider_resolve_exception: %s", str(exc)[:200])
        return fallback
        
    if selection is None:
        return fallback
        
    provider, model = selection
    
    try:
        response = provider.complete(
            OpenAIWrapperRequest(
                system=_SYSTEM_PROMPT,
                user=_USER_TEMPLATE.format(q=sanitised),
                model=model,
                max_tokens=256,
                temperature=0.0,
                timeout_seconds=5.0,
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("frames_planner_exception: %s", str(exc)[:200])
        return fallback
        
    if response.error:
        logger.debug("frames_planner_failure: %s", response.error[:120])
        return fallback
        
    text = response.text or ""
    start = text.find("[")
    end = text.rfind("]")
    if start < 0 or end < 0 or end <= start:
        return fallback
        
    blob = text[start:end + 1]
    try:
        data = json.loads(blob)
        if isinstance(data, list) and all(isinstance(x, str) for x in data):
            if len(data) > 0:
                return data
    except (json.JSONDecodeError, ValueError):
        pass
        
    return fallback
