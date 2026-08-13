"""R329 Wave 1 (P0 / P0b) — `gold_dropped` + `ref_crag_fine`.

Implements `.planning/R329-PLAN-GRAPHRAG-PAPER-INTEGRATION.md`'s "Wave 1: the
instrument. Nothing below can be gated without this."

CLAUDE.md hard rule #8 (RECALL GUARD) reads: "a reference change must drop
ZERO gold. Measure `gold_dropped` FIRST; non-zero is a rejection, not a
trade-off ... 'Head-level recall is invariant' is NOT sufficient — gold and
the grounded judge both score at SUB-POINT grain." Before this round that
field existed nowhere in the repo except prose (CLAUDE.md itself, two route
comments, two test comments, and the R327 write-up, which says outright it
is unmeasured) — the hard rule was unenforceable.

This file pins:
  * `gold_dropped_head` / `gold_dropped_exact` (`evals/bench/metrics.py`) —
    the two gold grains, because the repo has two gold shapes (davidath's
    head-level `relevant_article` vs easyhard's sub-point-grain
    `expected_refs`).
  * `reference_crag_fine` (`evals/bench/metrics.py`) — the NICD paper's
    fine-grained CRAG scale (Appendix C.2.2) applied to the reference set,
    under a brand-new name per R327's lesson ("if you change a formula,
    change its NAME").
  * The `evals/harness/easyhard_ab.py` wiring — `_score_row`, `_aggregate`,
    `_paired` — carries all three alongside the existing canonical axes
    without perturbing them.
"""
from __future__ import annotations

from evals.bench import metrics as bench_metrics
from evals.harness.easyhard_ab import _AXES, _aggregate, _paired, _score_row
from evals.harness.probe_set import ProbeRow

# Real EU AI Act coordinates, matching the convention already used in
# tests/test_bench_metrics.py: "Article 999" / "Article 3.999" are the
# repo's standard FABRICATED-citation fixtures — provision_exists("Article
# 3.999") is True (head-level LAX, see CLAUDE.md) but get_provision_text is
# None, so _canonical_ref correctly rejects both. "Article 5.1.f" / "Article
# 5.1.a" are real prohibited-practice leaves under the same head (5(1)(f)
# and 5(1)(a)); "Article 50.4" / "Article 50" / "Article 6" are real
# provisions used elsewhere in the suite.


# ── gold_dropped_head ─────────────────────────────────────────────────────


class TestGoldDroppedHead:
    def test_more_precise_prediction_is_not_a_drop(self):
        """Gold 'Article 5', predicted 'Article 5.1.f' -> head IS covered.

        This is the exact example in the R329 task spec: the head-grain
        instrument must not punish a MORE precise citation than gold asked
        for.
        """
        d = bench_metrics.gold_dropped_head(["Article 5.1.f"], ["Article 5"])
        assert d == {"gold_count": 1, "dropped_count": 0, "dropped_refs": []}

    def test_missing_head_is_dropped(self):
        d = bench_metrics.gold_dropped_head(
            ["Article 5.1.f"], ["Article 5", "Article 6"]
        )
        assert d["gold_count"] == 2
        assert d["dropped_count"] == 1
        assert d["dropped_refs"] == ["Article 6"]

    def test_empty_prediction_drops_every_gold_head(self):
        d = bench_metrics.gold_dropped_head([], ["Article 5", "Article 6"])
        assert d["dropped_count"] == 2
        assert sorted(d["dropped_refs"]) == ["Article 5", "Article 6"]

    def test_no_gold_nothing_can_be_dropped(self):
        d = bench_metrics.gold_dropped_head(["Article 5"], [])
        assert d == {"gold_count": 0, "dropped_count": 0, "dropped_refs": []}

    def test_davidath_int_shaped_gold_is_accepted(self):
        """davidath's `relevant_article` gold shape is a bare int, not a
        list[str] — `_gold_ref_set` already normalises it; this function
        must too, since it is the grain `evals.bench.runner` would use."""
        d = bench_metrics.gold_dropped_head(["Article 5"], 5)
        assert d == {"gold_count": 1, "dropped_count": 0, "dropped_refs": []}
        d2 = bench_metrics.gold_dropped_head([], 5)
        assert d2["dropped_count"] == 1


# ── gold_dropped_exact ────────────────────────────────────────────────────


class TestGoldDroppedExact:
    def test_sub_point_mismatch_is_a_drop_even_though_the_head_matches(self):
        """The reason the exact grain exists at all: hard rule #8 says gold
        and the grounded judge score at SUB-POINT grain, so a wrong
        sub-point under the correct head must cost something here even
        though `gold_dropped_head` calls the identical row clean — that gap
        is how a positional clamp can look safe on a head-level check while
        still destroying sub-point gold.
        """
        gold = ["Article 5.1.f"]
        pred = ["Article 5.1.a"]  # same head, wrong sub-point
        exact = bench_metrics.gold_dropped_exact(pred, gold)
        head = bench_metrics.gold_dropped_head(pred, gold)
        assert exact["dropped_count"] == 1
        assert exact["dropped_refs"] == ["Article 5.1.f"]
        assert head["dropped_count"] == 0

    def test_exact_match_drops_nothing(self):
        d = bench_metrics.gold_dropped_exact(["Article 50.4"], ["Article 50.4"])
        assert d == {"gold_count": 1, "dropped_count": 0, "dropped_refs": []}

    def test_fabricated_prediction_does_not_satisfy_gold(self):
        """A prediction that only cites a non-existent coordinate must still
        register the real gold as dropped — `_canonical_ref` rejects
        'Article 3.999' (provision_exists lax-True, get_provision_text
        None), so it can never appear in the predicted canonical set."""
        d = bench_metrics.gold_dropped_exact(["Article 3.999"], ["Article 50.4"])
        assert d["dropped_count"] == 1
        assert d["dropped_refs"] == ["Article 50.4"]

    def test_head_level_gold_makes_the_two_grains_coincide(self):
        """CLAUDE.md / the docstring claim: against head-level gold (no
        sub-point in the gold value itself), gold_dropped_exact degenerates
        to gold_dropped_head because `_gold_exact_refs` canonicalises a bare
        head the same way `_gold_ref_set` does."""
        pred, gold = ["Article 6"], ["Article 5"]
        assert bench_metrics.gold_dropped_exact(pred, gold) == (
            bench_metrics.gold_dropped_head(pred, gold)
        )

    def test_returns_actual_refs_not_only_counts(self):
        """Task requirement: a regression must be diagnosable from the
        stored row, not just a number."""
        d = bench_metrics.gold_dropped_exact(
            [], ["Article 5.1.f", "Article 50.4"]
        )
        assert d["dropped_count"] == 2
        assert sorted(d["dropped_refs"]) == ["Article 5.1.f", "Article 50.4"]


# ── reference_crag_fine — every branch of the asymmetric scale ───────────


class TestReferenceCragFine:
    def test_exact_set_match_scores_plus_one(self):
        assert bench_metrics.reference_crag_fine(
            ["Article 5.1.f"], ["Article 5.1.f"]
        ) == 1.0

    def test_exact_set_match_multi_ref(self):
        assert bench_metrics.reference_crag_fine(
            ["Article 5.1.f", "Article 50.4"], ["Article 50.4", "Article 5.1.f"]
        ) == 1.0

    def test_clean_subset_no_extras_scores_plus_half(self):
        # predicted STRICT SUBSET of gold, nothing extra.
        s = bench_metrics.reference_crag_fine(
            ["Article 5.1.f"], ["Article 5.1.f", "Article 6"]
        )
        assert s == 0.5

    def test_no_references_emitted_scores_zero(self):
        assert bench_metrics.reference_crag_fine([], ["Article 5.1.f"]) == 0.0

    def test_no_references_emitted_scores_zero_even_with_no_gold(self):
        # empty==empty must NOT fall into the +1.0 exact-match branch — "no
        # references emitted" is checked first.
        assert bench_metrics.reference_crag_fine([], []) == 0.0

    def test_gold_hit_with_a_valid_extra_scores_minus_half(self):
        s = bench_metrics.reference_crag_fine(
            ["Article 5.1.f", "Article 6"], ["Article 5.1.f"]
        )
        assert s == -0.5

    def test_no_gold_hit_at_all_scores_minus_one(self):
        s = bench_metrics.reference_crag_fine(["Article 6"], ["Article 5.1.f"])
        assert s == -1.0

    def test_citing_when_nothing_was_expected_scores_minus_one(self):
        assert bench_metrics.reference_crag_fine(["Article 6"], []) == -1.0

    def test_all_fabricated_predictions_score_minus_one_not_zero(self):
        """Refs WERE emitted (raw_count > 0) even though every one of them
        is fabricated and therefore absent from the canonical predicted set
        — this must NOT collide with the 'no references emitted' 0.0
        branch, which is reserved for a genuinely empty prediction list."""
        s = bench_metrics.reference_crag_fine(["Article 999"], ["Article 5.1.f"])
        assert s == -1.0

    def test_fabricated_extra_alongside_a_true_exact_match_is_not_plus_one(self):
        """The bug this implementation specifically guards against: a
        hallucinated citation must not be invisible to the score just
        because canonical_reference_diagnostics drops it from the valid
        set. 'One correct hit plus one fabricated extra' must NOT set-equal
        a clean exact match — that would score +1.0, exactly backwards for
        a metric whose entire point is that a wrong reference costs more
        than a missing one (hard rule #4: 'A confidently-wrong summary
        loses more than a missing one')."""
        s = bench_metrics.reference_crag_fine(
            ["Article 5.1.f", "Article 999"], ["Article 5.1.f"]
        )
        assert s == -0.5
        assert s != 1.0

    def test_fabricated_extra_alongside_a_clean_subset_blocks_the_plus_half(self):
        s = bench_metrics.reference_crag_fine(
            ["Article 5.1.f", "Article 999"],
            ["Article 5.1.f", "Article 50.4"],
        )
        assert s == -0.5

    def test_scale_is_bounded(self):
        for pred, gold in (
            (["Article 5.1.f"], ["Article 5.1.f"]),
            (["Article 5.1.f"], ["Article 5.1.f", "Article 6"]),
            ([], ["Article 5.1.f"]),
            (["Article 5.1.f", "Article 6"], ["Article 5.1.f"]),
            (["Article 6"], ["Article 5.1.f"]),
        ):
            s = bench_metrics.reference_crag_fine(pred, gold)
            assert -1.0 <= s <= 1.0


# ── easyhard_ab wiring: per-row + per-arm, canonical axes untouched ──────


def _row_of(id_: str, expected_refs, expected_keywords=()) -> ProbeRow:
    return ProbeRow(
        id=id_,
        source="r329_test",
        category="r329_test",
        is_multiturn=False,
        messages=({"role": "user", "content": "q"},),
        expected_refs=tuple(expected_refs),
        expected_keywords=tuple(expected_keywords),
    )


class TestScoreRowWiring:
    def test_new_fields_present_alongside_canonical_ones(self):
        row = _row_of("t1", ["Article 5.1.f", "Article 6"])
        scores = _score_row(row, "The provider must comply. Article 5.", ["Article 5.1.f"])
        # Canonical axes this harness has always reported (R327/R281) — must
        # still exist and be computed the same way as calling the bench
        # functions directly.
        for axis in _AXES:
            assert axis in scores
        assert scores["ref_loose"] == bench_metrics.reference_correctness_loose(
            ["Article 5.1.f"], ["Article 5.1.f", "Article 6"]
        )
        assert scores[
            "ref_strict"
        ] == bench_metrics.reference_correctness_strict_exact_coord(
            ["Article 5.1.f"], ["Article 5.1.f", "Article 6"]
        )
        assert scores["ref_conc"] == bench_metrics.reference_conciseness_exact_coord(
            ["Article 5.1.f"], ["Article 5.1.f", "Article 6"]
        )
        # New R329 fields.
        assert scores["gold_dropped_head"] == 1.0  # Article 6 head missing
        assert scores["gold_dropped_head_refs"] == ["Article 6"]
        assert scores["gold_dropped_exact"] == 1.0
        assert scores["gold_dropped_exact_refs"] == ["Article 6"]
        assert scores["ref_crag_fine"] == bench_metrics.reference_crag_fine(
            ["Article 5.1.f"], ["Article 5.1.f", "Article 6"]
        )

    def test_adding_r329_fields_does_not_perturb_canonical_scores(self):
        """Direct regression guard: compute the canonical axes BEFORE and
        via `_score_row`, on several rows, and assert byte-identical
        floats. This is the assertion the task explicitly requires — that
        wiring gold_dropped / ref_crag_fine in did not alter any existing
        number.

        Each case is (expected_refs, predicted_refs, answer_text).
        """
        cases = [
            (["Article 5.1.f"], ["Article 5.1.f"], "clean exact-match answer"),
            (["Article 5.1.f"], ["Article 5.1.f", "Article 6"], "over-cited answer"),
            (["Article 5.1.f"], [], "empty prediction answer"),
            (["Article 5.1.f"], ["Article 999"], "fabricated prediction answer"),
        ]
        for expected_refs, predicted_refs, answer in cases:
            row = _row_of("t", expected_refs)
            before = {
                "ref_loose": bench_metrics.reference_correctness_loose(
                    predicted_refs, expected_refs
                ),
                "ref_strict": bench_metrics.reference_correctness_strict_exact_coord(
                    predicted_refs, expected_refs
                ),
                "ref_conc": bench_metrics.reference_conciseness_exact_coord(
                    predicted_refs, expected_refs
                ),
                "tone": bench_metrics.regulatory_tone(answer),
            }
            after = _score_row(row, answer, predicted_refs)
            assert after["ref_loose"] == before["ref_loose"]
            assert after["ref_strict"] == before["ref_strict"]
            assert after["ref_conc"] == before["ref_conc"]
            assert after["tone"] == before["tone"]


class TestAggregateWiring:
    def _rows(self):
        r1 = {
            "scores": _score_row(
                _row_of("a", ["Article 5.1.f", "Article 6"]),
                "answer one", ["Article 5.1.f"],
            ),
            "latency_ms": 100.0,
            "pred_refs": ["Article 5.1.f"],
            "gold_refs": ["Article 5.1.f", "Article 6"],
        }
        r2 = {
            "scores": _score_row(
                _row_of("b", ["Article 50.4"]), "answer two", ["Article 50.4"]
            ),
            "latency_ms": 200.0,
            "pred_refs": ["Article 50.4"],
            "gold_refs": ["Article 50.4"],
        }
        return [r1, r2]

    def test_gold_dropped_is_a_sum_over_rows_not_a_mean(self):
        """CLAUDE.md's own formula for gold_dropped is a Σ over the probe
        set, not an average — a single dropped gold ref in a large arm must
        not be diluted into invisibility."""
        rows = self._rows()
        agg = _aggregate(rows)
        # row a drops 1 gold head/exact ('Article 6'); row b drops 0.
        assert agg["gold_dropped_head"] == 1
        assert agg["gold_dropped_exact"] == 1

    def test_ref_crag_fine_is_a_mean_like_the_other_float_axes(self):
        rows = self._rows()
        agg = _aggregate(rows)
        expected = (rows[0]["scores"]["ref_crag_fine"] + rows[1]["scores"]["ref_crag_fine"]) / 2
        assert abs(agg["ref_crag_fine"] - expected) < 1e-9

    def test_canonical_axes_in_aggregate_are_unperturbed(self):
        """Same regression guard at the aggregate level: the canonical
        _AXES means must equal a hand-computed mean over the same rows."""
        rows = self._rows()
        agg = _aggregate(rows)
        for axis in _AXES:
            expected = sum(
                bench_metrics_axis_value(r["scores"], axis) for r in rows
            ) / len(rows)
            assert abs(agg[axis] - expected) < 1e-9


def bench_metrics_axis_value(scores, axis):
    if axis == "ref_loose_head_recall_proxy":
        return float(scores.get(axis, scores.get("ref_loose", 0.0)))
    return float(scores.get(axis, 0.0))


class TestPairedWiring:
    def _row(self, rid, hard, scores, pred, gold):
        return {
            "id": rid,
            "is_multiturn": hard,
            "pred_refs": pred,
            "gold_refs": gold,
            "scores": scores,
        }

    def test_paired_carries_gold_dropped_and_crag_alongside_canonical_axes(self):
        a_scores = _score_row(
            _row_of("e1", ["Article 5.1.f", "Article 6"]),
            "a", ["Article 5.1.f"],
        )
        b_scores = _score_row(
            _row_of("e1", ["Article 5.1.f", "Article 6"]),
            "b", ["Article 5.1.f", "Article 6"],
        )
        a = [self._row("e1", False, a_scores, ["Article 5.1.f"], ["Article 5.1.f", "Article 6"])]
        b = [
            self._row(
                "e1", False, b_scores,
                ["Article 5.1.f", "Article 6"], ["Article 5.1.f", "Article 6"],
            )
        ]
        paired = _paired(a, b)["easy"]
        assert paired["n"] == 1
        # canonical axis unaffected by our change.
        assert paired["baseline"]["ref_loose"] == a_scores["ref_loose"]
        assert paired["branch"]["ref_loose"] == b_scores["ref_loose"]
        # new fields present in both arms of the paired read.
        assert paired["baseline"]["gold_dropped_head"] == 1
        assert paired["branch"]["gold_dropped_head"] == 0
        assert paired["baseline"]["gold_dropped_exact"] == 1
        assert paired["branch"]["gold_dropped_exact"] == 0
        assert "ref_crag_fine" in paired["baseline"]
        assert "ref_crag_fine" in paired["branch"]

    def test_paired_tolerates_legacy_rows_missing_r329_fields(self):
        """Old checkpoints (pre-R329) won't carry gold_dropped_head /
        gold_dropped_exact / ref_crag_fine in their scores dict — the
        wiring must default to 0 rather than KeyError so historical
        sidecars remain readable."""
        legacy_scores = {
            "ref_loose": 1.0, "ref_loose_head_recall_proxy": 1.0,
            "ref_strict": 0.5, "ref_conc": 0.4, "tone": 1.0, "kw_recall": 1.0,
        }
        a = [self._row("e1", False, legacy_scores, ["Article 6"], ["Article 6"])]
        b = [self._row("e1", False, legacy_scores, ["Article 6"], ["Article 6"])]
        paired = _paired(a, b)["easy"]
        assert paired["baseline"]["gold_dropped_head"] == 0
        assert paired["baseline"]["ref_crag_fine"] == 0.0
