"""LLM query parser and robust JSON extraction helpers for Graph RAG Engine."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.engines.graph_rag.models import GraphQuery

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(
    r"```(?:json5?|jsonc)?\s*\n?(.*?)\n?```",
    re.IGNORECASE | re.DOTALL,
)
_TRAILING_COMMA_RE = re.compile(r",\s*(?=[}\]])")
_QUERY_SCHEMA_KEYS = frozenset(
    {"intent", "entities", "risk_context", "dimension_hint", "keywords"}
)


def _strip_trailing_commas(text: str) -> str:
    """Strip trailing commas Sonnet sometimes emits despite a strict JSON ask."""
    return _TRAILING_COMMA_RE.sub("", text)


def _try_parse(candidate: str) -> dict | None:
    """Best-effort json.loads; return None on any failure (incl. non-dict)."""
    candidate = candidate.strip()
    if not candidate:
        return None
    try:
        result = json.loads(candidate)
    except (ValueError, TypeError):
        try:
            result = json.loads(_strip_trailing_commas(candidate))
        except (ValueError, TypeError):
            return None
    return result if isinstance(result, dict) else None


def _balanced_brace_spans(text: str) -> list[str]:
    """Yield every balanced {...} span in the text in document order."""
    spans: list[str] = []
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    spans.append(text[start:i + 1])
                    start = -1
    return spans


def _score_query_dict(parsed: dict) -> int:
    """Score a candidate parsed dict by how many query-schema keys it has."""
    return len(_QUERY_SCHEMA_KEYS & set(parsed.keys()))


def extract_json_object(text: str) -> dict | None:
    """Extract a parseable JSON object from an arbitrary LLM response."""
    if not text:
        return None
    cleaned = text.strip()

    # 1. Direct parse
    direct = _try_parse(cleaned)
    if direct is not None:
        return direct

    # 2. Fenced-block extraction
    fenced_candidates: list[tuple[int, int, dict]] = []
    for idx, match in enumerate(_JSON_FENCE_RE.finditer(cleaned)):
        result = _try_parse(match.group(1))
        if result is not None:
            fenced_candidates.append((_score_query_dict(result), idx, result))
    if fenced_candidates:
        fenced_candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
        return fenced_candidates[0][2]

    # 3. Balanced-brace fallback
    brace_candidates: list[tuple[int, int, dict]] = []
    for idx, span in enumerate(_balanced_brace_spans(cleaned)):
        result = _try_parse(span)
        if result is not None:
            brace_candidates.append((_score_query_dict(result), idx, result))
    if brace_candidates:
        brace_candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
        return brace_candidates[0][2]

    return None


def llm_parse_query(question: str) -> GraphQuery:
    """Parse question into GraphQuery using LLM, with fallback to extract_json_object."""
    # Stub / facade for LLM parse query; delegates to deterministic parse if provider disabled
    from app.engines.graph_rag.parser.deterministic import deterministic_parse
    return deterministic_parse(question)
