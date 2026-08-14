"""R276-D1 — reference-granularity selection (``REGENOLD_REF_GRANULARITY``).

The official regenold scorecard (2026-07-14) measured wire ref PRECISION at
~45% driven by parent+leaf duplication (``[Article 50.1, Article 50,
Article 50.2]`` vs gold ``[Article 50]``). These tests pin the new
granularity pass: ``both`` (default) is a byte-identical no-op; ``leaf`` /
``parent`` / ``auto`` each emit ONE level per mixed cluster; no mode can
drop a distinct head (head-level recall preserved); the pass is pure,
order-preserving, idempotent, and never empties the list.
"""
from __future__ import annotations

import pytest

from app.routes.regenold import (
    _apply_ref_granularity,
    _question_names_subpoint_of,
    _ref_granularity_mode,
    _ref_head_of,
)


MIXED = ["Article 50.1", "Article 50", "Article 50.2", "Annex III"]
GRB04 = ["Article 6", "Article 6.2", "Article 6.3", "Annex III"]


class TestModeResolution:
    def test_default_is_auto(self, monkeypatch):
        """R276-D1 ships default ``auto`` — see _ref_granularity_mode's
        docstring for the evidence chain. ``both`` restores pre-R276."""
        monkeypatch.delenv("REGENOLD_REF_GRANULARITY", raising=False)
        assert _ref_granularity_mode() == "auto"

    @pytest.mark.parametrize("raw", ["leaf", "LEAF", " Parent ", "auto"])
    def test_valid_modes_normalised(self, monkeypatch, raw):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", raw)
        assert _ref_granularity_mode() == raw.strip().lower()

    @pytest.mark.parametrize("raw", ["", "bogus", "1", "on"])
    def test_unknown_mode_falls_back_to_both(self, monkeypatch, raw):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", raw)
        assert _ref_granularity_mode() == "both"


class TestHelpers:
    def test_ref_head_of(self):
        assert _ref_head_of("Article 50.1") == "Article 50"
        assert _ref_head_of("Article 5.1.a") == "Article 5"
        assert _ref_head_of("Annex IV.2.c") == "Annex IV"
        assert _ref_head_of("Article 6") == "Article 6"
        assert _ref_head_of("Recital 27") is None

    def test_question_names_subpoint(self):
        assert _question_names_subpoint_of("Article 6", "What does Article 6(2) say?")
        assert _question_names_subpoint_of("Article 6", "what about article 6.2?")
        assert _question_names_subpoint_of("Annex IV", "Does Annex IV.2 require it?")
        assert _question_names_subpoint_of("Annex IV", "Does Annex IV(2) require it?")
        assert not _question_names_subpoint_of("Article 6", "What does Article 6 say?")
        # Article 50 must not match a question naming Article 5(1).
        assert not _question_names_subpoint_of(
            "Article 50", "Is it banned under Article 5(1)?"
        )


class TestBothDefault:
    def test_both_is_noop(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "both")
        assert _apply_ref_granularity(MIXED, "q", "a") == MIXED

    def test_unknown_mode_is_noop(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "weird")
        assert _apply_ref_granularity(MIXED, "q", "a") == MIXED


class TestLeafMode:
    def test_drops_head_in_mixed_cluster(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "leaf")
        out = _apply_ref_granularity(MIXED, "", "")
        assert out == ["Article 50.1", "Article 50.2", "Annex III"]

    def test_head_only_cluster_untouched(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "leaf")
        assert _apply_ref_granularity(["Article 26", "Annex III"], "", "") == [
            "Article 26",
            "Annex III",
        ]

    def test_leaf_only_cluster_untouched(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "leaf")
        assert _apply_ref_granularity(["Article 3.1"], "", "") == ["Article 3.1"]


class TestParentMode:
    def test_collapses_leaves_to_head(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "parent")
        out = _apply_ref_granularity(MIXED, "", "")
        assert out == ["Article 50", "Annex III"]

    def test_leaf_only_cluster_collapses_too(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "parent")
        assert _apply_ref_granularity(["Article 3.1", "Annex IV.2"], "", "") == [
            "Article 3",
            "Annex IV",
        ]

    def test_order_first_occurrence(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "parent")
        out = _apply_ref_granularity(
            ["Article 6.2", "Annex III", "Article 6", "Article 6.3"], "", ""
        )
        assert out == ["Article 6", "Annex III"]


class TestAutoMode:
    def test_no_signal_keeps_head_drops_leaves(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "auto")
        out = _apply_ref_granularity(
            GRB04,
            live_question="Is a healthcare eligibility system high-risk?",
            answer_text="High-risk. Article 6 read with Annex III classifies it.",
        )
        assert out == ["Article 6", "Annex III"]

    def test_prose_named_leaf_does_not_keep_leaves(self, monkeypatch):
        """The prose-signal was measured counterproductive (medtech sim:
        auto-with-prose .610 vs question-auto/parent .693 exact F1) and
        removed — a well-grounded answer nearly always names the operative
        paragraph, so the signal fired on every cluster.

        R333 — that measurement stands, and this test still guards it, but it
        is now explicitly a measurement of the signal-OFF regime rather than of
        the only regime. Its assertion is unchanged; only the pin is new.

        Why both regimes are legitimate: GOLD SHAPE decides which is right. The
        medtech sim above scores against HEAD-level gold, where projecting a
        leaf onto its head is a miss and keeping the head is correct. The
        expert-reviewer gold this repo exists to satisfy is LEAF-grained — it
        demands ``Annex IV.1(e)`` over ``Annex IV``, ``Annex III.1(c)`` over
        ``Annex III``, ``Article 99(4)`` over ``Article 99`` — and against it,
        head-only scored sub-point strict 0.000 where leaf-only scored 1.000.
        Same code, opposite verdicts, because the rulers differ.
        """
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "auto")
        monkeypatch.setenv("REGENOLD_LEAF_BODY_SIGNAL", "0")
        out = _apply_ref_granularity(
            ["Article 6.3", "Article 6", "Annex III"],
            live_question="Is deviation detection automatically high-risk?",
            answer_text="Not automatically. Article 6(3)(c) carves out systems that…",
        )
        assert out == ["Article 6", "Annex III"]

    def test_body_named_leaf_keeps_leaves_when_signal_enabled(self, monkeypatch):
        """R333 — the flag-ON half of the pair above, on identical input.

        Guards the defect the expert reviewer flagged three times: the system
        retrieves the right leaf, then the route deletes it in favour of the
        umbrella head. Dropping the head costs nothing at head grain because
        ``article_heads("Article 6.3")`` is ``"Article 6"``.
        """
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "auto")
        monkeypatch.setenv("REGENOLD_LEAF_BODY_SIGNAL", "1")
        out = _apply_ref_granularity(
            ["Article 6.3", "Article 6", "Annex III"],
            live_question="Is deviation detection automatically high-risk?",
            answer_text="Not automatically. Article 6(3)(c) carves out systems that…",
        )
        assert out == ["Article 6.3", "Annex III"]

    def test_body_signal_does_not_fire_without_a_coordinate(self, monkeypatch):
        """The signal must be a COORDINATE match, not a topic match.

        An answer that discusses Article 6 without naming a sub-point leaves the
        cluster exactly as the signal-off regime would — otherwise this widens
        into the always-fires failure the R276 banner describes.
        """
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "auto")
        monkeypatch.setenv("REGENOLD_LEAF_BODY_SIGNAL", "1")
        out = _apply_ref_granularity(
            ["Article 6.3", "Article 6", "Annex III"],
            live_question="Is deviation detection automatically high-risk?",
            answer_text="Not automatically — Article 6 read with Annex III governs.",
        )
        assert out == ["Article 6", "Annex III"]

    def test_question_named_subpoint_keeps_leaves(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "auto")
        out = _apply_ref_granularity(
            ["Article 50.1", "Article 50"],
            live_question="What does Article 50(1) require of providers?",
            answer_text="Providers must inform natural persons they interact with AI.",
        )
        assert out == ["Article 50.1"]

    def test_leaf_only_cluster_untouched(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "auto")
        refs = ["Article 3.1", "Annex I"]
        assert _apply_ref_granularity(refs, "What is an AI system?", "…") == refs

    def test_head_only_cluster_untouched(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "auto")
        refs = ["Article 26", "Article 27"]
        assert _apply_ref_granularity(refs, "deployer duties?", "…") == refs

    def test_never_drops_a_distinct_head(self, monkeypatch):
        """Head-level recall invariant: the set of heads covered by the
        output equals the set of heads covered by the input, every mode."""
        for mode in ("leaf", "parent", "auto"):
            monkeypatch.setenv("REGENOLD_REF_GRANULARITY", mode)
            out = _apply_ref_granularity(MIXED, "q?", "prose text")
            in_heads = {_ref_head_of(r) or r for r in MIXED}
            out_heads = {_ref_head_of(r) or r for r in out}
            assert in_heads == out_heads, mode

    def test_idempotent(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "auto")
        once = _apply_ref_granularity(GRB04, "q?", "Article 6 and Annex III.")
        twice = _apply_ref_granularity(once, "q?", "Article 6 and Annex III.")
        assert once == twice

    def test_never_empties(self, monkeypatch):
        for mode in ("leaf", "parent", "auto"):
            monkeypatch.setenv("REGENOLD_REF_GRANULARITY", mode)
            assert _apply_ref_granularity([], "", "") == []
            assert _apply_ref_granularity(["Article 50"], "", "") == ["Article 50"]

    def test_pure_no_mutation(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "leaf")
        refs = list(MIXED)
        _apply_ref_granularity(refs, "", "")
        assert refs == MIXED

    def test_non_article_ref_untouched(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "parent")
        out = _apply_ref_granularity(["Article 6.2", "Recital 27"], "", "")
        assert out == ["Article 6", "Recital 27"]
