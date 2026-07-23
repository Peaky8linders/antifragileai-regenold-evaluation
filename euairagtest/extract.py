"""Turn an LLM's free-text answer into scorer-ready citation strings.

Both LLM baselines (§8) answer in prose -- "...under Article 5(1)(a) and Annex
III point 5, see Recital (33)..." -- but the citation scorer eats a list of
citation strings per item. This module bridges the two: it scans prose for
provision references and emits canonical citation strings that
``euaiact.ids.ProvisionId`` (and therefore the scorer) understands.

Design choices that matter for honest evaluation:
  * References to *other* instruments (GDPR, another Regulation/Directive, the
    Charter, TFEU) are kept **verbatim, with their qualifier** ("Article 35
    GDPR"). They are intentionally left unparseable so the scorer counts them
    against precision and flags them on hallucination-trap items -- citing GDPR
    as if it were the AI Act is exactly the mistake we want to measure, not
    silently launder into ``art_35``.
  * Everything else is normalised through ProvisionId, so "Article 5(1)(a)",
    "Art 5 (1)(a)", and "art_5__para_1__point_a" all collapse to one canonical
    string and de-duplicate.

Pure standard library.
"""

from __future__ import annotations

import re

from ..ids import ProvisionId, ProvisionIdError

__all__ = ["extract_citations", "EXTERNAL_QUALIFIER_RE"]

# A reference is "external" (not the AI Act) when a foreign-instrument qualifier
# sits just after it: "Article 35 GDPR", "Article 6 of Regulation (EU) 2016/679",
# "Article 8 of the Charter", "Article 16 TFEU".
EXTERNAL_QUALIFIER_RE = re.compile(
    r"^\s*(?:of\s+)?(?:the\s+)?"
    # optional issuer prefix so "Council Directive 2016/680", "Commission Implementing
    # Regulation (EU) 2019/..." are recognised even when the instrument keyword does not
    # sit immediately after the article number.
    r"(?:(?:Council|Commission|European\s+Parliament|Framework|Implementing|Delegated)\s+){0,3}"
    r"(GDPR|Charter|TFEU|TEU|Treaty|Regulation\s*\(?EU\)?|Regulation\s+No|Regulation\s+\d"
    r"|Directive|Decision\s+\d|Decision\s+No)",
    re.IGNORECASE,
)

# Article citations: "Article 5(1)(a)", "Art. 5(1)(a)", "Art 5 (1) (a)".
_ARTICLE_RE = re.compile(
    r"\bArt(?:icle|\.)?\s*(\d+)\s*((?:\(\s*[^)]+\s*\))*)",
    re.IGNORECASE,
)
# Annex citations: "Annex III point 5(a)", "Annex III(5)(a)", "Annex XI".
# The tail is only ever "point <n>" runs or parenthesised groups.
_ANNEX_RE = re.compile(
    r"\bAnnex\s+([IVXLCDM]+)((?:\s*(?:point\s+\d+|\([^)]+\)))*)",
    re.IGNORECASE,
)
_ANNEX_POINT_RE = re.compile(r"point\s+(\d+)|\(\s*(\d+)\s*\)", re.IGNORECASE)
# Recital citations: "Recital (33)", "Recital 33".
_RECITAL_RE = re.compile(r"\bRecital\s*\(?\s*(\d+)\s*\)?", re.IGNORECASE)

_PAREN_GROUP_RE = re.compile(r"\(\s*([^)]+?)\s*\)")


def _is_external(text: str, end: int) -> bool:
    """True if the span ending at ``end`` is qualified as another instrument."""
    return bool(EXTERNAL_QUALIFIER_RE.match(text[end : end + 48]))


def _canonical(citation: str) -> str | None:
    """Round-trip a citation string through ProvisionId; None if unparseable."""
    try:
        return ProvisionId.from_citation(citation).citation
    except ProvisionIdError:
        return None


def extract_citations(text: str) -> list[str]:
    """Extract provision citations from free text, in order of first appearance.

    Returns canonical AI-Act citation strings (e.g. "Art. 5(1)(a)") plus any
    external references kept verbatim with their qualifier (e.g. "Art. 35 GDPR").
    De-duplicated; safe on empty / citation-free text (returns [])."""
    if not text:
        return []

    hits: list[tuple[int, str]] = []  # (position, citation-or-raw)

    for m in _ARTICLE_RE.finditer(text):
        raw = m.group(0)
        if _is_external(text, m.end()):
            qual = EXTERNAL_QUALIFIER_RE.match(text[m.end() : m.end() + 48])
            hits.append((m.start(), f"Art. {m.group(1)}{m.group(2)} {qual.group(1)}".strip()))
            continue
        groups = "".join(f"({g})" for g in _PAREN_GROUP_RE.findall(m.group(2)))
        hits.append((m.start(), _canonical(f"Art. {m.group(1)}{groups}") or raw))

    for m in _RECITAL_RE.finditer(text):
        hits.append((m.start(), _canonical(f"Recital ({m.group(1)})") or m.group(0)))

    for m in _ANNEX_RE.finditer(text):
        raw = m.group(0)
        tail = m.group(2) or ""
        citation = f"Annex {m.group(1)}"
        mp = _ANNEX_POINT_RE.search(tail)  # numbered annex point ("point 5" or "(5)")
        if mp:
            citation += f" point {mp.group(1) or mp.group(2)}"
        for g in _PAREN_GROUP_RE.findall(tail):  # lettered / roman sub-points
            g = g.strip()
            if not g.isdigit():
                citation += f"({g})"
        hits.append((m.start(), _canonical(citation) or raw))

    hits.sort(key=lambda h: h[0])
    seen: set[str] = set()
    out: list[str] = []
    for _, c in hits:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out
