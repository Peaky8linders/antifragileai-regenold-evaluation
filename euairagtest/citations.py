"""Deterministic in-text citation extractor.

Pulls statutory cross-references ("Article 6(2)(a)", "Annex III", "Recital (5)") out of
provision prose and resolves them to :class:`~euaiact.ids.ProvisionId`. It reuses the
Phase-1 citation parser, so anything it emits round-trips to a canonical eid — zero
hallucination. This augments the dataset's ``references_internal`` field with references
that live only in the text.

No maintained EU equivalent of ``eyecite`` (US) / ``Blackstone`` (UK) exists (verified
2026-07-22), so a small focused regex over the Act's own citation grammar is the
pragmatic SOTA. Deeper coverage is deferred:

Limitations (by design):
* Enumerated lists / ranges ("Articles 6 to 8", "Articles 6, 7 and 8") capture only the
  first article — full expansion is left to the ML/Formex pass.
* Uppercase paren groups (e.g. the "(EU)" in "Regulation (EU) 2016/679") are ignored,
  which also correctly prevents mis-parsing external-regulation numbers as points.
"""

from __future__ import annotations

import re

try:
    from .ids import ProvisionId, ProvisionIdError
except (ImportError, ValueError):
    from ..ids import ProvisionId, ProvisionIdError

__all__ = ["extract_citations", "extract_reference_eids"]

# "Article 6", "Article 6(2)", "Article 6(2)(a)(i)"; tolerate a plural "Articles".
_ARTICLE_RE = re.compile(r"Articles?\s+(\d+)((?:\s*\([0-9a-z]+\))*)")
# "Annex III", "Annex III, point 4", "Annex III point 4(a)".
_ANNEX_RE = re.compile(
    r"Annex\s+([IVXLCDM]+)(?:\s*,?\s*point\s+(\d+))?((?:\s*\([a-z]+\))*)", re.IGNORECASE
)
# "Recital (5)" or "recital 5".
_RECITAL_RE = re.compile(r"[Rr]ecital\s+\(?(\d+)\)?")
_PAREN_RE = re.compile(r"\(([0-9a-z]+)\)")

# A reference is "external" (not the AI Act) when a foreign-instrument qualifier
# sits just after the article number (allowing optional whitespace/punctuation).
# Ported from baselines/extract.py EXTERNAL_QUALIFIER_RE — duplicating the small
# regex here is intentional (no shared abstraction needed).
_EXTERNAL_QUALIFIER_RE = re.compile(
    r"^\s*(?:of\s+)?(?:the\s+)?"
    # optional issuer prefix so "Council Directive 2016/680", "Commission Implementing
    # Regulation (EU) 2019/..." are still recognised as external (the instrument keyword
    # need not sit immediately after the article number).
    r"(?:(?:Council|Commission|European\s+Parliament|Framework|Implementing|Delegated)\s+){0,3}"
    r"(GDPR|Charter|TFEU|TEU|Treaty|Regulation\s*\(?EU\)?|Regulation\s+No|Regulation\s+\d"
    r"|Directive|Decision\s+\d|Decision\s+No)",
    re.IGNORECASE,
)


def _is_external(text: str, end: int) -> bool:
    """True if the match ending at *end* is qualified as a foreign instrument."""
    return bool(_EXTERNAL_QUALIFIER_RE.match(text[end : end + 48]))


def _from_citation_safe(citation: str) -> ProvisionId | None:
    try:
        return ProvisionId.from_citation(citation)
    except ProvisionIdError:
        return None


def extract_citations(text: str) -> list[ProvisionId]:
    """Return the distinct provision ids cited in ``text``, in first-seen order."""
    found: dict[str, ProvisionId] = {}

    def keep(pid: ProvisionId | None) -> None:
        if pid is not None and pid.eid not in found:
            found[pid.eid] = pid

    for m in _ARTICLE_RE.finditer(text):
        # Drop references to other legal instruments (TFEU, GDPR, Charter …).
        if _is_external(text, m.end()):
            continue
        num, tail = m.group(1), m.group(2)
        groups = _PAREN_RE.findall(tail)
        keep(_from_citation_safe(f"Art. {num}" + "".join(f"({g})" for g in groups)))

    for roman, point, tail in _ANNEX_RE.findall(text):
        citation = f"Annex {roman.upper()}"
        if point:
            citation += f" point {point}"
        citation += "".join(f"({g})" for g in _PAREN_RE.findall(tail))
        keep(_from_citation_safe(citation))

    for num in _RECITAL_RE.findall(text):
        keep(_from_citation_safe(f"Recital ({num})"))

    return list(found.values())


def extract_reference_eids(text: str, *, exclude: str | None = None) -> list[str]:
    """Convenience: distinct cited eids, optionally dropping ``exclude`` (self-reference)."""
    return [pid.eid for pid in extract_citations(text) if pid.eid != exclude]
