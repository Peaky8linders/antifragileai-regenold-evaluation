"""R94 — tests for the article-coverage eval dataset.

These are pure-data + provision_text tests; no route calls.
Route-call assertions belong in the --run CLI, not pytest, to keep
the suite fast and deterministic.
"""
from __future__ import annotations

import re


# ── Fixtures ──────────────────────────────────────────────────────────────

from evals.regenold.article_coverage import ARTICLE_COVERAGE_QUESTIONS


# ── Helpers ───────────────────────────────────────────────────────────────

# Internal "Art. N" form used by ARTICLE_EXISTENCE
_ART_SHORT_RE = re.compile(r"^Art\.\s*(\d+)$")
# User-facing "Article N" form used by expected_refs
_ARTICLE_RE = re.compile(r"^Article\s+(\d+)$")
# Annex form: "Annex I" … "Annex XIII"
_ANNEX_RE = re.compile(r"^Annex\s+([IVX]+)$")

_ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
    "XI": 11, "XII": 12, "XIII": 13,
}


def _to_existence_key(ref: str) -> str | None:
    """Convert "Article N" / "Annex X" to the 'Art. N' / 'Annex X' form
    used in ARTICLE_EXISTENCE.
    """
    m = _ARTICLE_RE.match(ref.strip())
    if m:
        return f"Art. {m.group(1)}"
    m = _ANNEX_RE.match(ref.strip())
    if m:
        return f"Annex {m.group(1)}"
    return None


def _base_ref(ref: str) -> str:
    """Strip sub-point suffix: 'Article 111.2' → 'Article 111'."""
    ref = ref.strip()
    # find position of first dot or '(' that comes after the first space
    first_space = ref.find(" ")
    if first_space == -1:
        return ref
    after = ref[first_space + 1:]
    for sep in (".", "("):
        if sep in after:
            cut = ref.index(sep, first_space + 1)
            ref = ref[:cut].strip()
            break
    return ref


# ── Test 1 — every expected_ref resolves in ARTICLE_EXISTENCE ────────────


def test_every_expected_ref_resolves_in_existence() -> None:
    from app.data.article_existence import ARTICLE_EXISTENCE

    missing = []
    for entry in ARTICLE_COVERAGE_QUESTIONS:
        for ref in entry["expected_refs"]:
            key = _to_existence_key(_base_ref(ref))
            if key is None or key not in ARTICLE_EXISTENCE:
                missing.append((entry["id"], ref, key))

    assert not missing, (
        f"Expected refs not in ARTICLE_EXISTENCE:\n"
        + "\n".join(f"  [{qid}] {ref!r} → {key!r}" for qid, ref, key in missing)
    )


# ── Test 2 — every expected_ref has non-empty provision_text ─────────────


def test_every_expected_ref_has_verbatim_text() -> None:
    from app.data.provision_text import get_provision_text

    empty = []
    for entry in ARTICLE_COVERAGE_QUESTIONS:
        for ref in entry["expected_refs"]:
            base = _base_ref(ref)
            # provision_text only covers articles (not annexes by the same API)
            if not _ARTICLE_RE.match(base):
                continue
            text = get_provision_text(base)
            if not text:
                empty.append((entry["id"], ref))

    assert not empty, (
        "get_provision_text returned empty/None for:\n"
        + "\n".join(f"  [{qid}] {ref!r}" for qid, ref in empty)
    )


# ── Test 3 — question counts ──────────────────────────────────────────────


def test_question_count() -> None:
    article_entries = [q for q in ARTICLE_COVERAGE_QUESTIONS if q["kind"] == "article"]
    annex_entries = [q for q in ARTICLE_COVERAGE_QUESTIONS if q["kind"] == "annex"]
    usecase_entries = [q for q in ARTICLE_COVERAGE_QUESTIONS if q["kind"] == "usecase"]

    # Exactly 113 article entries
    assert len(article_entries) == 113, (
        f"Expected 113 article entries, got {len(article_entries)}"
    )

    # Exactly 13 annex entries
    assert len(annex_entries) == 13, (
        f"Expected 13 annex entries, got {len(annex_entries)}"
    )

    # At least 10 usecase entries
    assert len(usecase_entries) >= 10, (
        f"Expected ≥10 usecase entries, got {len(usecase_entries)}"
    )

    # One entry per article 1..113
    article_numbers = []
    for entry in article_entries:
        exp = entry["expected_refs"]
        assert len(exp) == 1, f"Article entry {entry['id']} should have 1 expected_ref"
        m = _ARTICLE_RE.match(exp[0])
        assert m, f"Article entry {entry['id']} expected_ref {exp[0]!r} is not 'Article N'"
        article_numbers.append(int(m.group(1)))
    assert sorted(article_numbers) == list(range(1, 114)), (
        "Article entries do not cover exactly 1..113"
    )

    # One entry per annex I..XIII
    annex_romans = []
    for entry in annex_entries:
        exp = entry["expected_refs"]
        assert len(exp) == 1, f"Annex entry {entry['id']} should have 1 expected_ref"
        m = _ANNEX_RE.match(exp[0])
        assert m, f"Annex entry {entry['id']} expected_ref {exp[0]!r} is not 'Annex X'"
        annex_romans.append(m.group(1))
    expected_romans = ["I", "II", "III", "IV", "V", "VI", "VII",
                       "VIII", "IX", "X", "XI", "XII", "XIII"]
    assert sorted(annex_romans, key=lambda r: _ROMAN_TO_INT[r]) == expected_romans, (
        f"Annex entries do not cover exactly Annex I..XIII: got {sorted(annex_romans)}"
    )


# ── Test 4 — all IDs are unique ───────────────────────────────────────────


def test_article_question_ids_unique() -> None:
    ids = [q["id"] for q in ARTICLE_COVERAGE_QUESTIONS]
    seen: dict[str, int] = {}
    dupes = []
    for idx, qid in enumerate(ids):
        if qid in seen:
            dupes.append((qid, seen[qid], idx))
        else:
            seen[qid] = idx
    assert not dupes, (
        "Duplicate question IDs:\n"
        + "\n".join(f"  {qid!r} at positions {a} and {b}" for qid, a, b in dupes)
    )
