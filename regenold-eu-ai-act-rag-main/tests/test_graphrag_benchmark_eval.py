"""Regression tests for scenarios_graphrag_benchmark.py — EVAL-01 guard.

These tests enforce benchmark-integrity invariants so that duplicate rows,
unresolvable citations, and dangling REFERENCE_ANSWERS keys are caught at
test-collection time rather than silently skewing live evaluation scores.
"""
import re

import pytest

from evals.regenold.scenarios_graphrag_benchmark import GROUND_TRUTH, REFERENCE_ANSWERS
from app.data.article_existence import ARTICLE_EXISTENCE

_ART_RE = re.compile(r"^Article\s+(\d+)$")
_ANNEX_RE = re.compile(r"^Annex\s+([IVXLC]+)$")


def _resolves(ref: str) -> bool:
    """Return True iff *ref* resolves in the canonical article/annex catalog."""
    m = _ART_RE.match(ref)
    if m:
        return f"Art. {m.group(1)}" in ARTICLE_EXISTENCE
    m = _ANNEX_RE.match(ref)
    if m:
        return f"Annex {m.group(1)}" in ARTICLE_EXISTENCE
    return False


def test_unique_ids() -> None:
    """All GROUND_TRUTH ids must be unique (no duplicate rows by id)."""
    ids = [row["id"] for row in GROUND_TRUTH]
    duplicates = {i for i in ids if ids.count(i) > 1}
    assert not duplicates, f"Duplicate ids found in GROUND_TRUTH: {sorted(duplicates)}"


def test_unique_question_texts() -> None:
    """EVAL-01 regression guard: all GROUND_TRUTH question strings must be unique.

    Six docx_q* rows were verbatim duplicates of med_0N rows; this test
    prevents that class of copy-paste error from silently re-entering the file.
    """
    questions = [row["question"] for row in GROUND_TRUTH]
    seen: set[str] = set()
    duplicates: list[str] = []
    for q in questions:
        if q in seen:
            duplicates.append(q)
        seen.add(q)
    assert not duplicates, (
        f"Duplicate question texts found in GROUND_TRUTH "
        f"(first 3 shown): {duplicates[:3]}"
    )


def test_every_expected_ref_resolves() -> None:
    """Every expected_ref in non-recital-only rows must resolve in ARTICLE_EXISTENCE."""
    bad: list[tuple[str, str]] = []
    for row in GROUND_TRUTH:
        if row.get("recital_only"):
            continue
        for ref in row.get("expected_refs", []):
            if not _resolves(ref):
                bad.append((row["id"], ref))
    assert not bad, (
        f"Unresolvable expected_refs found (id, ref): {bad}"
    )


def test_reference_answers_keys_valid() -> None:
    """Every key in REFERENCE_ANSWERS must correspond to a GROUND_TRUTH id."""
    valid_ids = {row["id"] for row in GROUND_TRUTH}
    dangling = [k for k in REFERENCE_ANSWERS if k not in valid_ids]
    assert not dangling, (
        f"REFERENCE_ANSWERS keys not present in GROUND_TRUTH ids: {dangling}"
    )
