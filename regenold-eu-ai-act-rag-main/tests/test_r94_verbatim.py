"""R94 — verbatim exact-text output + sub-point coverage + Art. 111 mapping.

Covers:
* ``app/data/official_text_patches.py`` — Article 113 verbatim repair.
* ``app/data/provision_text.py`` — sub-point-resolved verbatim extraction.
* ``app/engines/verbatim_answer.py`` — answer assembly.
* The Article 111 grandfathering keyword mapping (scope + engine).
"""
from __future__ import annotations

import re

import pytest

from app.data import provision_text as pt
from app.data.article_existence import ARTICLE_EXISTENCE
from app.data.official_text_patches import OFFICIAL_TEXT_PATCHES
from app.data.provision_text import select_relevant_paragraphs
from app.engines.verbatim_answer import build_verbatim_answer


# ── official_text_patches ─────────────────────────────────────────────────


def test_patch_keys_resolve_in_existence() -> None:
    for key in OFFICIAL_TEXT_PATCHES:
        assert key.startswith("Article ") or key.startswith("Annex ")
        short = key.replace("Article ", "Art. ")
        assert short in ARTICLE_EXISTENCE or key in ARTICLE_EXISTENCE


def test_article_113_patch_restores_numbering_and_binding_clause() -> None:
    text = OFFICIAL_TEXT_PATCHES["Article 113"]
    # paragraph numbers restored
    assert "1. This Regulation shall enter into force" in text
    assert "2. It shall apply from 2 August 2026" in text
    assert "3. However:" in text
    # the (a)(b)(c) points + the Art. 101 exception
    assert "with the exception of Article 101" in text
    assert "Article 6(1) and the corresponding obligations" in text
    # closing binding clause (was dropped pre-R94)
    assert "binding in its entirety and directly applicable" in text


# ── provision_text — article + annex level ────────────────────────────────


def test_all_113_articles_resolve_article_level() -> None:
    missing = [n for n in range(1, 114) if not pt.get_provision_text(f"Article {n}")]
    assert missing == []


def test_all_13_annexes_resolve_article_level() -> None:
    romans = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
              "XI", "XII", "XIII"]
    missing = [r for r in romans if not pt.get_provision_text(f"Annex {r}")]
    assert missing == []


# ── provision_text — sub-point resolution (the user's examples) ────────────


def test_article_111_2_verbatim() -> None:
    t = pt.get_provision_text("Article 111(2)")
    assert t is not None
    assert "operators of high-risk AI systems" in t
    assert "before 2 August 2026" in t
    assert "2 August 2030" in t
    # paragraph 2 must NOT carry paragraph 1's Annex X / 31 December 2030 text
    assert "31 December 2030" not in t


def test_article_111_2_dotform_equals_parenform() -> None:
    assert pt.get_provision_text("Article 111.2") == pt.get_provision_text("Article 111(2)")
    assert pt.get_provision_text("Art. 111(2)") == pt.get_provision_text("Article 111(2)")


def test_article_6_1_verbatim() -> None:
    t = pt.get_provision_text("Article 6(1)")
    assert t is not None
    assert "safety component" in t
    assert "Annex I" in t


def test_article_113_3_resolves_after_patch() -> None:
    t = pt.get_provision_text("Article 113(3)")
    assert t is not None
    assert t.startswith("However:")
    # nested point under 113(3)
    sub = pt.get_provision_text("Article 113.3.a")
    assert sub is not None
    assert "2 February 2025" in sub


def test_article_5_1_a_subpoint() -> None:
    t = pt.get_provision_text("Article 5(1)(a)")
    assert t is not None
    assert "subliminal" in t.lower()


def test_article_3_definitions_resolve() -> None:
    # Art. 3 uses parenthesised (1)..(68) numbering, not "N." paragraphs.
    d1 = pt.get_provision_text("Article 3(1)")
    assert d1 is not None and "AI system" in d1
    d68 = pt.get_provision_text("Article 3(68)")
    assert d68 is not None
    # all 68 definitions resolve
    missing = [k for k in range(1, 69) if not pt.get_provision_text(f"Article 3({k})")]
    assert missing == []


def test_unresolvable_subpoint_returns_none() -> None:
    # Article 4 (AI literacy) is a single block — no paragraph 9.
    assert pt.get_provision_text("Article 4(9)") is None


def test_garbage_ref_returns_none() -> None:
    assert pt.get_provision_text("not a ref") is None
    assert pt.get_provision_text("") is None


# ── verbatim_answer assembly ───────────────────────────────────────────────


def test_build_verbatim_prefers_question_subpoint_over_article_ref() -> None:
    # Question names 111(2); references only carry the article-level "Article 111".
    out = build_verbatim_answer(
        ["Article 111"],
        question="How would Article 111(2) apply to MedTech providers and deployers?",
    )
    assert out is not None
    assert out.startswith("Article 111(2):")
    # parent Article 111 is suppressed (redundant with the sub-point)
    assert "\n\nArticle 111:" not in out


def test_build_verbatim_quotes_each_reference(monkeypatch) -> None:
    # With a generous budget both cited provisions are quoted.
    monkeypatch.setenv("REGENOLD_VERBATIM_MAX_CHARS", "4000")
    out = build_verbatim_answer(["Article 6.1", "Article 4"], question="")
    assert out is not None
    assert "Article 6(1):" in out
    assert "Article 4:" in out


def test_build_verbatim_relevance_bounds_huge_annex() -> None:
    # R94.1 — Annex I is ~5.8k chars; relevance-selection bounds it so the
    # primary stays exact and the annex is quoted bounded (not dumped whole).
    out = build_verbatim_answer(["Article 6.1", "Annex I"], question="")
    assert out is not None
    assert out.startswith("Article 6(1):")
    # the whole 5.8k annex is never dumped
    assert len(out) <= 1400


def test_build_verbatim_empty_when_no_refs() -> None:
    assert build_verbatim_answer([], question="What is AI literacy?") is None


def test_build_verbatim_falls_back_to_article_when_subpoint_unresolvable() -> None:
    # Article 4 has no paragraph 9 → fall back to the full article body.
    out = build_verbatim_answer(["Article 4.9"], question="")
    assert out is not None
    assert out.startswith("Article 4:")


def test_build_verbatim_respects_max_provisions(monkeypatch) -> None:
    monkeypatch.setenv("REGENOLD_VERBATIM_MAX_PROVISIONS", "1")
    out = build_verbatim_answer(["Article 6", "Article 13", "Article 50"], question="")
    assert out is not None
    # only the first provision quoted
    assert out.count("Article 6:") == 1
    assert "Article 13:" not in out


# ── R94.1 relevance-selected paragraph extraction (conciseness fix) ────────


def test_select_relevant_paragraphs_drills_to_emotion_subpoint() -> None:
    # Art. 5(1) is one ~5k-char enumeration; an emotion-recognition question
    # must drill to point (f), not dump the whole list.
    out = select_relevant_paragraphs(
        "Article 5", "Is emotion recognition in the workplace prohibited?", 500
    )
    assert out is not None
    assert len(out) <= 700  # bounded, not the 5k full paragraph
    assert "infer emotions" in out  # the (f) text
    assert "(f)" in out


def test_select_relevant_paragraphs_drills_to_biometric_subpoint() -> None:
    out = select_relevant_paragraphs(
        "Article 5",
        "Is real-time remote biometric identification in public spaces for "
        "law enforcement prohibited?",
        500,
    )
    assert out is not None
    assert "real-time" in out.lower() and "remote biometric" in out.lower()


def test_select_relevant_paragraphs_bounds_length() -> None:
    # Every article/annex, with an empty question, stays bounded (no
    # multi-page dumps) — the conciseness fix invariant.
    for ref in ("Article 5", "Article 6", "Article 16", "Annex III", "Article 99"):
        out = select_relevant_paragraphs(ref, "", 500)
        assert out is not None
        assert len(out) <= 1200, f"{ref} too long: {len(out)}"


def test_verbatim_answer_is_bounded_on_huge_article() -> None:
    # The R94 regression: Article 5 produced an 11k-char wire answer.
    out = build_verbatim_answer(
        ["Article 5"], question="Is emotion recognition in the workplace prohibited?"
    )
    assert out is not None
    assert len(out) <= 900
    assert "(f)" in out


# ── Article 111 grandfathering mapping ─────────────────────────────────────


def test_scope_maps_placed_before_to_article_111() -> None:
    from app.integrations.regenold.scope import KEYWORD_TO_ARTICLE
    for kw in (
        "placed on the market before",
        "put into service before",
        "already placed on the market",
        "before 2 august 2026",
    ):
        assert KEYWORD_TO_ARTICLE.get(kw) == "Art. 111"


def test_engine_entity_map_maps_placed_before_to_article_111() -> None:
    from app.engines.graph_rag import _KEYWORD_ENTITY_MAP
    pairs = dict(_KEYWORD_ENTITY_MAP)
    assert pairs.get("placed on the market before") == "Art. 111"
    assert pairs.get("put into service before") == "Art. 111"
