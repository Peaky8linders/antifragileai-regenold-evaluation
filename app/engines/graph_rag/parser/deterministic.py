"""Deterministic query parser for Graph RAG Engine."""

from __future__ import annotations

import re
from app.engines.graph_rag.models import GraphQuery
from app.engines.graph_rag.config import config

_MULTI_ARTICLE_MENTION_RE = re.compile(
    r"\b(?:Articles?|Arts?\.?)\s*((?:\d{1,3}(?:\s*[\(,\&/]\s*\d+[\)]*)*(?:\s*(?:and|or)\s*\d{1,3})?)+)",
    re.IGNORECASE,
)
_MULTI_ANNEX_MENTION_RE = re.compile(
    r"\b(?:Annexes?|Annex)\s*((?:[IVXLC]+(?:\s*[\(,\&/]\s*[IVXLC]+[\)]*)*(?:\s*(?:and|or)\s*[IVXLC]+)?)+)",
    re.IGNORECASE,
)


def deterministic_parse(question: str) -> GraphQuery:
    """Parse a question into a :class:`GraphQuery` (keyword + regex matching).

    R290 — DELEGATES to the live engine parser
    (``_graph_rag_impl._deterministic_parse``) rather than keeping a second
    implementation. The stand-alone version below had already drifted: its
    multi-article separator was a SINGLE optional connector
    ``(?:\\s*(?:and|or)\\s*\\d{1,3})?`` where the live one uses R268.1's
    repeated form ``(?:\\s*(?:,|&|/|and|or)\\s*)+``, so it silently dropped
    the trailing item of an Oxford-comma list — "Articles 9, 10, and 15"
    parsed to ``[Art. 9, Art. 10]``, losing Article 15. It also lacked the
    R63-A topic extensions and the R79 Unicode/self-dedup handling.

    Delegating removes the divergence class entirely instead of re-fixing
    each drift by hand. The import is LAZY: ``_graph_rag_impl`` imports
    ``app.engines.graph_rag.models``, so a module-level import here would
    create a cycle when this submodule is imported first. On any failure we
    fall back to the local implementation so this module keeps working
    stand-alone.
    """
    try:
        from app.engines._graph_rag_impl import _deterministic_parse

        return _deterministic_parse(question)
    except Exception:  # noqa: BLE001 — fall through to the local parser
        pass
    return _local_deterministic_parse(question)


def _local_deterministic_parse(question: str) -> GraphQuery:
    """Stand-alone fallback parser. Prefer :func:`deterministic_parse`."""
    try:
        from app.engines.scenario_classifier import _normalise
        q_lower = _normalise(question).lower()
    except Exception:
        q_lower = question.lower()

    # Detect intent (evaluating specific domain intents before broad article lookup)
    intent = "general_compliance"
    if re.search(r'\b(?:gap|missing|lacking)\b', q_lower):
        intent = "gap_analysis"
    elif re.search(r'\b(?:obligation|require|must|need to)\b', q_lower):
        intent = "obligation_check"
    elif re.search(r'\b(?:risk|classify|classification)\b', q_lower):
        intent = "risk_assessment"
    elif re.search(r'\b(?:nist|iso|framework|cross)\b', q_lower):
        intent = "cross_framework"
    elif re.search(r'\b(?:definition|define|what is a|what is an)\b', q_lower):
        intent = "article_lookup"
    elif re.search(r'\b(?:article|art\.)\b', q_lower):
        intent = "article_lookup"

    # Extract article + annex references
    if config.multi_article_entities_enabled:
        article_nums = [
            n
            for m in _MULTI_ARTICLE_MENTION_RE.finditer(question)
            for n in re.findall(r"\d{1,3}", re.sub(r"\(\d+\)", "", m.group(1)))
        ]
        annex_romans = [
            r
            for m in _MULTI_ANNEX_MENTION_RE.finditer(question)
            for r in re.findall(r"\b[IVXLC]+\b", m.group(1).upper())
        ]
    else:
        article_nums = re.findall(
            r"\b(?:Arts?\.?|Articles?)\s*(\d{1,3})\b", question, re.IGNORECASE,
        )
        annex_romans = re.findall(
            r"\bAnnexes?\s+([IVXLC]+)\b", question, re.IGNORECASE,
        )

    entities: list[str] = []
    seen: set[str] = set()
    for n in article_nums:
        ent = f"Art. {n}"
        if ent not in seen:
            seen.add(ent)
            entities.append(ent)
    for r in annex_romans:
        ent = f"Annex {r.upper()}"
        if ent not in seen:
            seen.add(ent)
            entities.append(ent)

    # Detect risk context
    risk_context = None
    if "high" in q_lower and "risk" in q_lower:
        risk_context = "high"
    elif "limited" in q_lower:
        risk_context = "limited"
    elif "minimal" in q_lower:
        risk_context = "minimal"
    elif "unacceptable" in q_lower or "prohibited" in q_lower:
        risk_context = "unacceptable"

    # Detect dimension hints (using canonical keys)
    dimension_hint = None
    if "risk management" in q_lower or re.search(r'\b(?:art(?:icle)?\.?\s*(?:8|9))\b', q_lower):
        dimension_hint = "risk_mgmt"
    elif "data governance" in q_lower or "training data" in q_lower or re.search(r'\b(?:art(?:icle)?\.?\s*10)\b', q_lower):
        dimension_hint = "data_gov"
    elif "technical documentation" in q_lower or re.search(r'\b(?:art(?:icle)?\.?\s*11)\b', q_lower):
        dimension_hint = "tech_docs"
    elif "record keeping" in q_lower or "record-keeping" in q_lower or "logging" in q_lower or re.search(r'\b(?:art(?:icle)?\.?\s*12)\b', q_lower):
        dimension_hint = "logging"
    elif "transparency" in q_lower or re.search(r'\b(?:art(?:icle)?\.?\s*(?:13|50))\b', q_lower):
        dimension_hint = "transparency"
    elif "human oversight" in q_lower or re.search(r'\b(?:art(?:icle)?\.?\s*14)\b', q_lower):
        dimension_hint = "human_oversight"
    elif "accuracy" in q_lower or "cybersecurity" in q_lower or "robustness" in q_lower or re.search(r'\b(?:art(?:icle)?\.?\s*15)\b', q_lower):
        dimension_hint = "security"

    return GraphQuery(
        intent=intent,
        entities=entities,
        risk_context=risk_context,
        dimension_hint=dimension_hint,
        keywords=[],
        raw_question=question,
    )

