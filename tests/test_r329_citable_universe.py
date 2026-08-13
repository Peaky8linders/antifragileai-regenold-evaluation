"""R329 Wave 3 — the Stage-2 user-channel prompt changes (P3a / P3b / P3c).

Three independently-gated edits to the ONE channel the Claude Max wrapper
actually delivers (the Stage-2 SYSTEM prompt is dropped 100% — measured
2026-08-03), pinned here:

**P3a — ``REGENOLD_CITABLE_UNIVERSE_BLOCK`` (default OFF).**
The delivered citation instruction said "cite only ... the EU AI ACT REFERENCES
block", but ``_build_context_references_block`` renders seven kinds of
explicitly NON-citable material inside that same block (cross-regulatory
bridging, synthesized multi-hop analysis, legal-AST evaluations, three
knowledge-graph sections, the semantic layers, verbatim provision text,
referenced annexes/recitals) — each with its own "do NOT cite" clause. So the
model had to resolve one permissive scope statement against a stack of
prohibitions. ON, the prompt names an explicit enumerated list instead, derived
from the provisions the engine actually retrieved.

**P3b — ``REGENOLD_REF_UNCERTAINTY`` (default OFF).**
One sentence adding the CRAG asymmetry (uncertainty), which
``USER_REF_MINIMALITY_CLAUSE`` — default ON since R298 and measured — does not
state; it argues relevance instead.

**P3c — the duplicated ``USER_ANSWER_COVERAGE_CLAUSE``.**
It was appended TWICE (two verbatim ``try/except`` pairs on the same flag), so
~2.1 KB of ANSWER COVERAGE landed twice in every live prompt. Now once.

⚠ BOTH FLAGS WERE FLIPPED TO DEFAULT **ON** on 2026-08-13 by operator decision,
UNGATED. Railway's ``[deploy.envs]`` has never applied, so a default-OFF flag is
dead code in the deployment — a code default is the only delivery mechanism.
The docstring paragraphs above describe the ORIGINAL defaults.

THE LOAD-BEARING TEST IS STILL THE BYTE-IDENTITY ONE, but it now pins the
ROLLBACK path rather than the default: with both flags explicitly ``=0`` the
assembled Stage-2 user message must be byte-for-byte what it was before R329.
Note the corollary — the historical baselines in CLAUDE.md were measured with
these OFF, so they no longer describe the default-configuration system and must
be re-measured.
"""

from __future__ import annotations

import os
import re
from unittest.mock import patch

import pytest

import app.engines._graph_rag_impl as impl
from app.data.graph_rag_prompts import (
    USER_ANSWER_COVERAGE_CLAUSE,
    USER_REF_UNCERTAINTY_CLAUSE,
    user_ref_uncertainty_enabled,
)
from app.engines._graph_rag_impl import GraphContext

# ---------------------------------------------------------------------------
# The exact pre-R329 wording. If a future round edits either of these strings
# it must edit them here too — that is the point.
# ---------------------------------------------------------------------------
_LEGACY_SCOPE_REFINE = "obligations that appear in the EU AI ACT REFERENCES block, "
_LEGACY_SCOPE_CLASSIFY = (
    "Cite only articles and annexes from the EU AI ACT REFERENCES block.\n"
)
_NEW_SCOPE_REFINE = "obligations that appear in the CITABLE PROVISIONS list above, "
_NEW_SCOPE_CLASSIFY = (
    "Cite only articles and annexes from the CITABLE PROVISIONS list above.\n"
)
_CITABLE_HEADER = (
    "CITABLE PROVISIONS (the ONLY values that may appear in a citation):\n"
)

_Q = "Is our CV-screening tool high-risk, and what must the deployer do?"
_KG_ANSWER = "Deployers of high-risk AI systems must comply with Article 26."


def _context() -> GraphContext:
    """A GraphContext shaped exactly like a real retrieval.

    ``article`` values are the KB entity keys the engine really stores —
    ``Art. N`` short form, ``Annex R``, and a sub-point tail — so the test
    exercises the normalisation to the wire format, not a pre-normalised
    fixture. Deliberately out of numeric order.
    """
    return GraphContext(
        obligations=[
            {"id": "kb-a", "text": "Prohibited practices.", "article": "Art. 6"},
            {"id": "kb-b", "text": "High-risk classification.", "article": "Annex III"},
            {"id": "kb-c", "text": "Prohibitions.", "article": "Art. 5"},
        ],
        article_info=[
            {"id": "kb-d", "text": "Deployer duties.", "article": "Art. 26"},
            # sub-point tail — must collapse to its head, not leak "Art. 50(2)"
            {"id": "kb-e", "text": "Transparency.", "article": "Art. 50(2)"},
            # duplicate of an obligation entry — must not appear twice
            {"id": "kb-f", "text": "Prohibitions again.", "article": "Art. 5"},
        ],
        question=_Q,
    )


@pytest.fixture(autouse=True)
def _isolate_env():
    """Full env isolation. Every flag this prompt path reads is reset.

    The R263.2 doctrine means each flag is read FRESH per call, so leaving one
    set would silently contaminate every later test in the session.
    """
    keys = (
        "REGENOLD_CITABLE_UNIVERSE_BLOCK",
        "REGENOLD_REF_UNCERTAINTY",
        "REGENOLD_ANSWER_COVERAGE",
        "REGENOLD_ANSWER_FIRST",
        "REGENOLD_REF_PARTITION",
        "REGENOLD_FUSION_STAGE2",
        "GEMINI_API_KEY",
        "OPENAI_API_BASE",
        "P2P_GRAPH_RAG_PROVIDER",
    )
    saved = {k: os.environ.get(k) for k in keys}
    for k in keys:
        os.environ.pop(k, None)
    # Deterministic dispatch: 'cli' lands in the openai_wrapper branch, which the
    # spy below intercepts, so no network call is ever made.
    os.environ["P2P_GRAPH_RAG_PROVIDER"] = "cli"
    os.environ["OPENAI_API_BASE"] = "http://127.0.0.1:1/v1"
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def _capture(*, is_general_classification: bool = False) -> str:
    """Assemble a real Stage-2 user message and return it verbatim."""
    captured: dict = {}

    def _spy(**kwargs):
        captured.update(kwargs)
        return None

    with patch.object(
        impl, "_openai_wrapper_complete_for_graph_rag", side_effect=_spy
    ):
        impl._claude_max_enhance_answer(
            question=_Q,
            kg_answer=_KG_ANSWER,
            context=_context(),
            is_general_classification=is_general_classification,
        )
    user = captured.get("user", "")
    assert user, "the Stage-2 user message was never assembled"
    return user


# ---------------------------------------------------------------------------
# 0. The regression guard — both flags OFF is byte-identical to pre-R329.
# ---------------------------------------------------------------------------


def test_defaults_are_on_for_both_new_flags():
    """Default ON as of 2026-08-13 (operator decision, ungated).

    Railway's ``[deploy.envs]`` has never applied, so a default-OFF flag never
    reaches the deployment — a code default is the only delivery mechanism.
    Both keep an explicit ``=0`` off-switch for instant rollback, and both stay
    flags so ``ab_judge`` / ``easyhard_ab`` can still A/B them OFF↔ON.
    """
    assert impl._citable_universe_enabled() is True
    assert user_ref_uncertainty_enabled() is True


@pytest.mark.parametrize(
    "value", ["0", "false", "off", "no", "OFF", " 0 "]
)
def test_off_switch_spellings(monkeypatch, value):
    """Negative-form flags: only an explicit off-value disables."""
    monkeypatch.setenv("REGENOLD_CITABLE_UNIVERSE_BLOCK", value)
    monkeypatch.setenv("REGENOLD_REF_UNCERTAINTY", value)
    assert impl._citable_universe_enabled() is False
    assert user_ref_uncertainty_enabled() is False


class TestFlagsOffAreByteIdentical:
    """The ROLLBACK path. With both flags explicitly OFF the assembled Stage-2
    user message must be byte-for-byte the pre-R329 prompt — otherwise every
    historical baseline in CLAUDE.md is graded against a different prompt."""

    @pytest.fixture(autouse=True)
    def _force_flags_off(self, monkeypatch):
        # Explicit now that the DEFAULT is ON; this class tests the off-switch.
        monkeypatch.setenv("REGENOLD_CITABLE_UNIVERSE_BLOCK", "0")
        monkeypatch.setenv("REGENOLD_REF_UNCERTAINTY", "0")

    @pytest.mark.parametrize("classify", [False, True])
    def test_no_new_text_leaks_when_off(self, classify: bool):
        user = _capture(is_general_classification=classify)
        assert _CITABLE_HEADER not in user
        assert "CITABLE PROVISIONS" not in user
        assert USER_REF_UNCERTAINTY_CLAUSE not in user
        assert "REFERENCE UNCERTAINTY" not in user

    def test_legacy_scope_wording_is_untouched_refine_branch(self):
        user = _capture(is_general_classification=False)
        assert _LEGACY_SCOPE_REFINE in user
        assert _NEW_SCOPE_REFINE not in user

    def test_legacy_scope_wording_is_untouched_classification_branch(self):
        user = _capture(is_general_classification=True)
        assert _LEGACY_SCOPE_CLASSIFY in user
        assert _NEW_SCOPE_CLASSIFY not in user

    @pytest.mark.parametrize("classify", [False, True])
    def test_on_minus_the_addition_reconstructs_the_off_prompt_exactly(
        self, classify: bool
    ):
        """The strongest form of the guard.

        Take the flag-ON prompt, delete the CITABLE PROVISIONS block and revert
        the scope phrase, and the result must equal the flag-OFF prompt BYTE FOR
        BYTE. That proves P3a changes nothing else anywhere in the assembly.
        """
        off = _capture(is_general_classification=classify)
        os.environ["REGENOLD_CITABLE_UNIVERSE_BLOCK"] = "1"
        on = _capture(is_general_classification=classify)
        assert on != off

        block = impl._citable_universe_block(_context())
        assert block and block in on
        rebuilt = on.replace(block, "", 1)
        if classify:
            rebuilt = rebuilt.replace(_NEW_SCOPE_CLASSIFY, _LEGACY_SCOPE_CLASSIFY, 1)
        else:
            rebuilt = rebuilt.replace(_NEW_SCOPE_REFINE, _LEGACY_SCOPE_REFINE, 1)
        assert rebuilt == off

    def test_p3b_on_minus_the_sentence_reconstructs_the_off_prompt_exactly(self):
        off = _capture()
        os.environ["REGENOLD_REF_UNCERTAINTY"] = "1"
        on = _capture()
        assert on != off
        assert on.replace(USER_REF_UNCERTAINTY_CLAUSE, "", 1) == off


# ---------------------------------------------------------------------------
# 1. P3a — the CITABLE PROVISIONS list
# ---------------------------------------------------------------------------


class TestCitableUniverseDerivation:
    def test_refs_are_exactly_the_retrieved_provisions(self):
        """obligations + article_info, deduped, heads only, sorted."""
        assert impl._citable_universe_refs(_context()) == [
            "Article 5",
            "Article 6",
            "Article 26",
            "Article 50",
            "Annex III",
        ]

    def test_format_obeys_hard_rule_1(self):
        """``Article N`` Arabic / ``Annex R`` Roman uppercase. Never ``Art.``."""
        refs = impl._citable_universe_refs(_context())
        pattern = re.compile(r"^(?:Article \d{1,3}|Annex [IVXLCDM]+)$")
        for ref in refs:
            assert pattern.match(ref), ref
        assert not any("Art." in r for r in refs)

    def test_annexes_sort_by_roman_value_not_lexicographically(self):
        ctx = GraphContext(
            obligations=[
                {"id": "a", "text": "", "article": "Annex IX"},
                {"id": "b", "text": "", "article": "Annex III"},
                {"id": "c", "text": "", "article": "Annex IV"},
            ]
        )
        assert impl._citable_universe_refs(ctx) == [
            "Annex III",
            "Annex IV",
            "Annex IX",
        ]

    def test_articles_sort_numerically_not_lexicographically(self):
        ctx = GraphContext(
            obligations=[
                {"id": str(n), "text": "", "article": f"Art. {n}"}
                for n in (3, 30, 5, 113)
            ]
        )
        assert impl._citable_universe_refs(ctx) == [
            "Article 3",
            "Article 5",
            "Article 30",
            "Article 113",
        ]

    def test_only_the_rendered_slices_are_named(self):
        """Never promise a provision whose stub was cut out of the block.

        ``_build_context_references_block`` renders ``obligations[:20]`` and
        ``article_info[:15]``; the citable list mirrors those caps, so it is
        always a subset of what the model can actually read.
        """
        ctx = GraphContext(
            obligations=[
                {"id": str(n), "text": "", "article": f"Art. {n}"}
                for n in range(1, 31)
            ],
            article_info=[
                {"id": str(n), "text": "", "article": f"Art. {n}"}
                for n in range(40, 80)
            ],
        )
        refs = impl._citable_universe_refs(ctx)
        assert "Article 20" in refs
        assert "Article 21" not in refs  # obligations[20:] never rendered
        assert "Article 54" in refs
        assert "Article 55" not in refs  # article_info[15:] never rendered

    def test_empty_context_yields_no_block(self):
        assert impl._citable_universe_refs(None) == []
        assert impl._citable_universe_block(None) == ""
        assert impl._citable_universe_block(GraphContext()) == ""

    def test_empty_context_keeps_the_legacy_wording_even_with_the_flag_on(self):
        """No list to point at => do not point at a list. Graceful degradation."""
        os.environ["REGENOLD_CITABLE_UNIVERSE_BLOCK"] = "1"
        captured: dict = {}

        def _spy(**kwargs):
            captured.update(kwargs)
            return None

        with patch.object(
            impl, "_openai_wrapper_complete_for_graph_rag", side_effect=_spy
        ):
            impl._claude_max_enhance_answer(
                question=_Q, kg_answer=_KG_ANSWER, context=GraphContext()
            )
        user = captured.get("user", "")
        assert "CITABLE PROVISIONS" not in user
        assert _LEGACY_SCOPE_REFINE in user


class TestCitableUniverseInThePrompt:
    def test_block_appears_once_and_lists_the_retrieved_refs(self):
        os.environ["REGENOLD_CITABLE_UNIVERSE_BLOCK"] = "1"
        user = _capture()
        assert user.count(_CITABLE_HEADER) == 1
        assert (
            "Article 5, Article 6, Article 26, Article 50, Annex III" in user
        )

    @pytest.mark.parametrize(
        "classify,new_scope,legacy_scope",
        [
            (False, _NEW_SCOPE_REFINE, _LEGACY_SCOPE_REFINE),
            (True, _NEW_SCOPE_CLASSIFY, _LEGACY_SCOPE_CLASSIFY),
        ],
    )
    def test_instruction_points_at_the_list_not_the_references_block(
        self, classify: bool, new_scope: str, legacy_scope: str
    ):
        os.environ["REGENOLD_CITABLE_UNIVERSE_BLOCK"] = "1"
        user = _capture(is_general_classification=classify)
        assert new_scope in user
        assert legacy_scope not in user

    @pytest.mark.parametrize("classify", [False, True])
    def test_block_precedes_the_citation_instruction(self, classify: bool):
        os.environ["REGENOLD_CITABLE_UNIVERSE_BLOCK"] = "1"
        user = _capture(is_general_classification=classify)
        scope = _NEW_SCOPE_CLASSIFY if classify else _NEW_SCOPE_REFINE
        assert user.index(_CITABLE_HEADER) < user.index(scope), (
            "the instruction says 'the CITABLE PROVISIONS list above' — the list "
            "must actually be above it"
        )

    def test_block_closes_the_stack_of_per_block_prohibitions(self):
        """The defect P3a fixes: a permissive scope statement over a block that
        also holds non-citable material. The list must say so explicitly."""
        os.environ["REGENOLD_CITABLE_UNIVERSE_BLOCK"] = "1"
        user = _capture()
        assert "Nothing outside this list may be cited" in user

    def test_sub_paragraph_grain_stays_permitted(self):
        """Sub-point refs are the most accurate shape the system emits (85%
        correct), and ``REGENOLD_SUBPARAGRAPH_ATTRIBUTION`` is default ON. A
        head-level permission list must not be read as banning them."""
        os.environ["REGENOLD_CITABLE_UNIVERSE_BLOCK"] = "1"
        user = _capture()
        assert (
            "A sub-paragraph of a listed provision (for example Article 5(1)(f)) "
            "counts as that provision." in user
        )

    def test_env_is_read_fresh_per_call(self):
        """R263.2 — a module-level constant makes an in-process A/B inert."""
        os.environ["REGENOLD_CITABLE_UNIVERSE_BLOCK"] = "0"
        assert impl._citable_universe_enabled() is False
        os.environ["REGENOLD_CITABLE_UNIVERSE_BLOCK"] = "1"
        assert impl._citable_universe_enabled() is True
        os.environ["REGENOLD_CITABLE_UNIVERSE_BLOCK"] = "0"
        assert impl._citable_universe_enabled() is False


# ---------------------------------------------------------------------------
# 2. P3b — the CRAG uncertainty sentence
# ---------------------------------------------------------------------------


class TestRefUncertaintyClause:
    def test_clause_is_one_sentence_about_uncertainty_not_relevance(self):
        assert USER_REF_UNCERTAINTY_CLAUSE == (
            " REFERENCE UNCERTAINTY: If you are not certain a provision is on "
            "point, omit it: an incorrect citation costs more than a missing "
            "one.\n"
        )

    def test_clause_appears_exactly_once_when_on(self):
        os.environ["REGENOLD_REF_UNCERTAINTY"] = "1"
        user = _capture()
        assert user.count(USER_REF_UNCERTAINTY_CLAUSE) == 1
        assert user.count("REFERENCE UNCERTAINTY:") == 1

    def test_clause_also_reaches_the_classification_branch(self):
        os.environ["REGENOLD_REF_UNCERTAINTY"] = "1"
        user = _capture(is_general_classification=True)
        assert user.count(USER_REF_UNCERTAINTY_CLAUSE) == 1

    def test_env_is_read_fresh_per_call(self):
        os.environ["REGENOLD_REF_UNCERTAINTY"] = "0"
        assert user_ref_uncertainty_enabled() is False
        os.environ["REGENOLD_REF_UNCERTAINTY"] = "1"
        assert user_ref_uncertainty_enabled() is True
        os.environ["REGENOLD_REF_UNCERTAINTY"] = "off"
        assert user_ref_uncertainty_enabled() is False

    def test_it_does_not_replace_the_measured_minimality_clause(self):
        """R298's minimality clause is default ON and measured (multi-turn ref
        precision 0.423 -> 0.735). P3b is additive to it, never a swap."""
        from app.data.graph_rag_prompts import USER_REF_MINIMALITY_CLAUSE

        os.environ["REGENOLD_REF_UNCERTAINTY"] = "1"
        user = _capture()
        assert USER_REF_MINIMALITY_CLAUSE in user
        assert USER_REF_UNCERTAINTY_CLAUSE in user


# ---------------------------------------------------------------------------
# 3. P3c — the de-duplicated ANSWER COVERAGE clause
# ---------------------------------------------------------------------------


class TestAnswerCoverageAppendedOnce:
    def test_coverage_clause_lands_exactly_once_when_enabled(self):
        os.environ["REGENOLD_ANSWER_COVERAGE"] = "1"
        user = _capture()
        assert user.count(USER_ANSWER_COVERAGE_CLAUSE) == 1
        assert user.count("ANSWER COVERAGE:") == 1

    def test_coverage_clause_lands_once_on_the_classification_branch_too(self):
        os.environ["REGENOLD_ANSWER_COVERAGE"] = "1"
        user = _capture(is_general_classification=True)
        assert user.count(USER_ANSWER_COVERAGE_CLAUSE) == 1

    def test_coverage_clause_is_absent_when_disabled(self):
        os.environ["REGENOLD_ANSWER_COVERAGE"] = "0"
        user = _capture()
        assert "ANSWER COVERAGE:" not in user

    def test_the_legal_version_tail_still_lands(self):
        """The clause carries the R318 LEGAL VERSION sentence — the only place
        the 'no Digital Omnibus' policy reaches the model. Deleting the wrong
        copy would have deleted it."""
        os.environ["REGENOLD_ANSWER_COVERAGE"] = "1"
        user = _capture()
        assert user.count("LEGAL VERSION: apply Regulation (EU) 2024/1689") == 1
