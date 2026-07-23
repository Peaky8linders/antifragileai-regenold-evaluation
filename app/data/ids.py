"""Provision identifiers for the EU AI Act (Regulation (EU) 2024/1689).

A ``ProvisionId`` is the stable join key between vector index and graph.
Its canonical string form (the ``eid``) follows Akoma Ntoso conventions:
    art_6__para_2__point_a          -> "Art. 6(2)(a)"
    art_5__para_1__point_h__sub_i   -> "Art. 5(1)(h)(i)"
    annex_III__point_4__point_a     -> "Annex III point 4(a)"
    recital_132                     -> "Recital (132)"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = [
    "ProvisionId",
    "Segment",
    "ProvisionIdError",
    "ELI_WORK_URI",
    "CELEX",
]

CELEX = "32024R1689"
ELI_WORK_URI = "https://eur-lex.europa.eu/eli/reg/2024/1689/oj"

_ROOT_KINDS = {"art", "annex", "recital", "chapter", "section"}
_ARTICLE_NEST = ("para", "point", "sub")

_ROMAN_RE = re.compile(r"^[IVXLCDM]+$", re.IGNORECASE)
_EID_SEGMENT_RE = re.compile(r"^(art|annex|recital|chapter|section|para|point|sub)_(.+)$")

_CIT_ARTICLE_RE = re.compile(r"^Art\.\s+(\d+)\s*((?:\([^)]+\))*)$")
_CIT_ANNEX_RE = re.compile(r"^Annex\s+([IVXLCDM]+)(?:\s+point\s+(\d+))?\s*((?:\([^)]+\))*)$")
_CIT_RECITAL_RE = re.compile(r"^Recital\s+\((\d+)\)$")
_PAREN_GROUP_RE = re.compile(r"\(([^)]+)\)")

_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


class ProvisionIdError(ValueError):
    """Raised when an eid or citation cannot be parsed into a ProvisionId."""


def _is_roman(value: str) -> bool:
    return bool(_ROMAN_RE.match(value))


def roman_to_int(roman: str) -> int:
    """Convert a Roman numeral to int (used for ordering annexes/sub-points)."""
    s = roman.upper()
    if not _is_roman(s):
        raise ProvisionIdError(f"not a Roman numeral: {roman!r}")
    total = 0
    prev = 0
    for ch in reversed(s):
        val = _ROMAN_VALUES[ch]
        total += -val if val < prev else val
        prev = max(prev, val)
    return total


@dataclass(frozen=True)
class Segment:
    """One level of a provision address, e.g. ``point`` / ``a``."""

    kind: str
    value: str

    def __str__(self) -> str:
        return f"{self.kind}_{self.value}"


@dataclass(frozen=True)
class ProvisionId:
    """A structure-preserving, stable identifier for one EU AI Act provision."""

    segments: tuple[Segment, ...] = field()

    def __post_init__(self) -> None:
        if not self.segments:
            raise ProvisionIdError("a ProvisionId needs at least one segment")
        root = self.segments[0].kind
        if root not in _ROOT_KINDS:
            raise ProvisionIdError(f"eid must start with one of {_ROOT_KINDS}, got {root!r}")

    @classmethod
    def from_eid(cls, eid: str) -> ProvisionId:
        """Parse a canonical eid string like ``art_6__para_2__point_a``."""
        if not eid or not eid.strip():
            raise ProvisionIdError("empty eid")
        segs: list[Segment] = []
        for raw in eid.strip().split("__"):
            m = _EID_SEGMENT_RE.match(raw)
            if not m:
                raise ProvisionIdError(f"unparseable eid segment: {raw!r} (in {eid!r})")
            segs.append(Segment(m.group(1), m.group(2)))
        return cls(tuple(segs))

    @classmethod
    def from_citation(cls, citation: str) -> ProvisionId:
        """Parse a human citation like ``Art. 6(2)(a)`` or ``Annex III point 4(a)``."""
        text = citation.strip()

        m = _CIT_RECITAL_RE.match(text)
        if m:
            return cls((Segment("recital", m.group(1)),))

        m = _CIT_ARTICLE_RE.match(text)
        if m:
            segs = [Segment("art", m.group(1))]
            groups = _PAREN_GROUP_RE.findall(m.group(2))
            for depth, val in enumerate(groups):
                if depth >= len(_ARTICLE_NEST):
                    raise ProvisionIdError(f"article citation nested too deep: {citation!r}")
                segs.append(Segment(_ARTICLE_NEST[depth], val))
            return cls(tuple(segs))

        m = _CIT_ANNEX_RE.match(text)
        if m:
            segs = [Segment("annex", m.group(1))]
            if m.group(2):
                segs.append(Segment("point", m.group(2)))
            for val in _PAREN_GROUP_RE.findall(m.group(3)):
                segs.append(Segment("point", val))
            return cls(tuple(segs))

        raise ProvisionIdError(f"unrecognised citation format: {citation!r}")

    @classmethod
    def parse(cls, text: str) -> ProvisionId:
        """Best-effort parse: try eid form first, then citation form."""
        try:
            return cls.from_eid(text)
        except ProvisionIdError:
            return cls.from_citation(text)

    @property
    def eid(self) -> str:
        return "__".join(str(s) for s in self.segments)

    @property
    def citation(self) -> str:
        """Render the canonical human citation."""
        head, *rest = self.segments
        if head.kind == "art":
            out = f"Art. {head.value}"
        elif head.kind == "annex":
            out = f"Annex {head.value}"
        elif head.kind == "recital":
            return f"Recital ({head.value})"
        elif head.kind == "chapter":
            out = f"Chapter {head.value}"
        else:
            out = f"Section {head.value}"
        for seg in rest:
            if seg.kind == "point" and seg.value.isdigit():
                out += f" point {seg.value}"
            else:
                out += f"({seg.value})"
        return out

    @property
    def eli_uri(self) -> str:
        return f"{ELI_WORK_URI}#{self.eid}"

    @property
    def root_kind(self) -> str:
        return {
            "art": "article",
            "annex": "annex",
            "recital": "recital",
            "chapter": "chapter",
            "section": "section",
        }[self.segments[0].kind]

    def _first(self, kind: str) -> str | None:
        for s in self.segments:
            if s.kind == kind:
                return s.value
        return None

    @property
    def article_no(self) -> int | None:
        val = self._first("art")
        return int(val) if val and val.isdigit() else None

    @property
    def paragraph_no(self) -> int | None:
        val = self._first("para")
        return int(val) if val and val.isdigit() else None

    @property
    def point_label(self) -> str | None:
        return self._first("point")

    @property
    def recital_no(self) -> int | None:
        val = self._first("recital")
        return int(val) if val and val.isdigit() else None

    @property
    def parent_eid(self) -> str | None:
        if len(self.segments) <= 1:
            return None
        return "__".join(str(s) for s in self.segments[:-1])
