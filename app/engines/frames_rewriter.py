"""FramesQA Query Rewriter Agent (R52 / Agentic RAG).

Dynamically refines search queries based on retrieved context or the
decomposed sub-queries. If a sub-query is vague, the Query Rewriter
expands it using domain knowledge or context from the original question.
"""
from __future__ import annotations

import logging
import time

from app.llm.openai_wrapper_provider import (
    OpenAIWrapperRequest,
    get_openai_wrapper_provider,
    is_openai_wrapper_enabled,
)

logger = logging.getLogger(__name__)

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
        return sub_query

    if resp.error:
        logger.debug("frames_rewriter_error: %s", resp.error[:160])
        return sub_query

    text = (resp.text or "").strip()
    # Strip any accidental quotes
    text = text.strip('\"\'').strip()
    
    if not text:
        return sub_query

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.debug("frames_rewriter_ok: rewritten in %d ms", elapsed_ms)
    
    return text

