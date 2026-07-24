"""Deterministic query parser for Graph RAG Engine."""

from __future__ import annotations

import re
from app.engines.graph_rag.models import GraphQuery
from app.engines.graph_rag.config import config

_MULTI_ARTICLE_MENTION_RE = re.compile(
    r"\b(?:Articles?|Arts?\.?)\s+((?:\d{1,3}(?:\s*[\(,\&/]\s*\d+[\)]*)*(?:\s*(?:and|or)\s*\d{1,3})?)+)",
    re.IGNORECASE,
)
_MULTI_ANNEX_MENTION_RE = re.compile(
    r"\b(?:Annexes?|Annex)\s+((?:[IVXLC]+(?:\s*[\(,\&/]\s*[IVXLC]+[\)]*)*(?:\s*(?:and|or)\s*[IVXLC]+)?)+)",
    re.IGNORECASE,
)


def deterministic_parse(question: str) -> GraphQuery:
    """Parse question using keyword and regular expression matching."""
    try:
        from app.engines.scenario_classifier import _normalise
        q_lower = _normalise(question).lower()
    except Exception:
        q_lower = question.lower()

    # Detect intent
    intent = "general_compliance"
    if re.search(r'\b(?:gap|missing|lacking)\b', q_lower):
        intent = "gap_analysis"
    elif re.search(r'\b(?:obligation|require|must|need to)\b', q_lower):
        intent = "obligation_check"
    elif re.search(r'\b(?:definition|define|what is a|what is an)\b', q_lower):
        intent = "article_lookup"
    elif re.search(r'\b(?:article|art\.)\b', q_lower):
        intent = "article_lookup"
    elif re.search(r'\b(?:risk|classify|classification)\b', q_lower):
        intent = "risk_assessment"
    elif re.search(r'\b(?:nist|iso|framework|cross)\b', q_lower):
        intent = "cross_framework"

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
            for r in re.findall(r"[IVXLC]+", m.group(1).upper())
        ]
    else:
        article_nums = re.findall(
            r"\b(?:Art\.?|Article)\s*(\d{1,3})\b", question, re.IGNORECASE,
        )
        annex_romans = re.findall(
            r"\bAnnex\s+([IVXLC]+)\b", question, re.IGNORECASE,
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
    if "risk management" in q_lower or "article 9" in q_lower:
        dimension_hint = "risk_mgmt"
    elif "data governance" in q_lower or "training data" in q_lower or "article 10" in q_lower:
        dimension_hint = "data_gov"
    elif "technical documentation" in q_lower or "article 11" in q_lower:
        dimension_hint = "tech_docs"
    elif "record keeping" in q_lower or "logging" in q_lower or "article 12" in q_lower:
        dimension_hint = "logging"
    elif "transparency" in q_lower or "article 13" in q_lower or "article 50" in q_lower:
        dimension_hint = "transparency"
    elif "human oversight" in q_lower or "article 14" in q_lower:
        dimension_hint = "human_oversight"
    elif "accuracy" in q_lower or "cybersecurity" in q_lower or "robustness" in q_lower or "article 15" in q_lower:
        dimension_hint = "security"

    return GraphQuery(
        intent=intent,
        entities=entities,
        risk_context=risk_context,
        dimension_hint=dimension_hint,
        keywords=[],
        raw_question=question,
    )
