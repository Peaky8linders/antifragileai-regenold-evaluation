"""R268 — widened multi-article / multi-annex entity extraction.

The pre-R268 explicit-reference regex dropped articles/annexes named in a LIST
or with a plural token ("Articles 13 and 50" → captured neither; "Article 13
and 50" → only 13; "Annexes III and IV" → neither). The named provisions then
never became engine entities, so their KB obligation substance never reached
the Stage-2 grounding context and the answer covered only whichever provision
a keyword happened to surface. These tests pin the widened parse, the env-gate
rollback, and the single-reference / definitional invariants.
"""
from __future__ import annotations

import os

import pytest

from app.engines.graph_rag import _deterministic_parse


def _entities(question: str, *, gate: str = "1") -> list[str]:
    prev = os.environ.get("REGENOLD_MULTI_ARTICLE_ENTITIES")
    os.environ["REGENOLD_MULTI_ARTICLE_ENTITIES"] = gate
    try:
        return _deterministic_parse(question).entities
    finally:
        if prev is None:
            os.environ.pop("REGENOLD_MULTI_ARTICLE_ENTITIES", None)
        else:
            os.environ["REGENOLD_MULTI_ARTICLE_ENTITIES"] = prev


# ── Plural / list ARTICLE forms (the discovered defect) ──────────────────────

@pytest.mark.parametrize(
    "question,expected",
    [
        ("obligations under Articles 13 and 50?", ["Art. 13", "Art. 50"]),
        ("What do Articles 9, 10 and 11 require?",
         ["Art. 9", "Art. 10", "Art. 11"]),
        ("Compare Article 13 and 50.", ["Art. 13", "Art. 50"]),
        ("duties in Arts. 16, 17 and 18", ["Art. 16", "Art. 17", "Art. 18"]),
        ("penalties under Articles 99 or 101", ["Art. 99", "Art. 101"]),
    ],
)
def test_article_list_captures_every_named_article(question, expected):
    ents = _entities(question)
    for e in expected:
        assert e in ents, f"{e!r} missing from {ents!r} for {question!r}"


# ── Plural / list ANNEX forms (the symmetric defect) ─────────────────────────

@pytest.mark.parametrize(
    "question,expected",
    [
        ("Compare Annexes III and IV.", ["Annex III", "Annex IV"]),
        ("What is in Annex III and IV?", ["Annex III", "Annex IV"]),
        ("Requirements in Annex IV and Annex VI?", ["Annex IV", "Annex VI"]),
    ],
)
def test_annex_list_captures_every_named_annex(question, expected):
    ents = _entities(question)
    for e in expected:
        assert e in ents, f"{e!r} missing from {ents!r} for {question!r}"


# ── Single-reference + definitional invariants (unchanged) ───────────────────

def test_single_article_unchanged():
    assert "Art. 13" in _entities("Explain Art. 13.")


def test_single_annex_unchanged():
    assert "Annex III" in _entities("What does Annex III say?")


def test_definitional_path_unaffected():
    # No article number in the text → the R127 role-definitional anchor still
    # leads with Art. 3, not a spurious article-list capture.
    assert _entities("What is a provider?") == ["Art. 3"]


# ── Env-gate rollback ────────────────────────────────────────────────────────

def test_gate_off_reverts_to_single_article_regex():
    # Pre-R268 behaviour: the plural "Articles 13 and 50" captured NEITHER
    # explicit number, so neither is a directly-parsed entity.
    off = _entities("obligations under Articles 13 and 50?", gate="0")
    assert "Art. 13" not in off or "Art. 50" not in off, (
        f"gate OFF should not capture both explicit articles, got {off!r}"
    )


def test_regex_no_false_match_inside_words():
    # The token regex must not read "artificial" / "start" / "smart" / "chart"
    # as an "Art" reference (the BM25 fallback may still surface unrelated
    # articles — this pins the REGEX, the surface the fix owns).
    from app.engines.graph_rag import _MULTI_ARTICLE_MENTION_RE
    text = "Does artificial intelligence start under a smart chart of 5 rules?"
    assert _MULTI_ARTICLE_MENTION_RE.findall(text) == [], (
        _MULTI_ARTICLE_MENTION_RE.findall(text)
    )
