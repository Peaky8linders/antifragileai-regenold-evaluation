"""R301 — unit tests for the hard-sample per-run diff helpers.

The diff is a measurement instrument, so its failure mode is silent: a bug here
does not break a request, it produces a WRONG scorecard that a round then acts
on. These tests pin the three properties the R301 read depended on:

1. sub-point refs collapse to the right head (and BOTH grains are reported —
   R287.1 measured head-level recall staying flat while sub-point recall
   collapsed, so a head-only diff would have hidden it);
2. the treatment/control split keys on ``provenance.stage2_polish``, because a
   Stage-2-gated change only moves Stage-2 rows and pooling dilutes it;
3. a byte-identical pair reports zero change (no false positives).
"""
from __future__ import annotations

import pytest

from evals.regenold.diff_hard_sample import _exact, _heads, _jacc, _stage2, diff_arm


def _row(rid, refs, *, stage2=True, answer="a", lat=1000.0, pushback=None):
    r = {
        "id": rid,
        "pred_refs": list(refs),
        "pred_answer": answer,
        "latency_ms": lat,
        "difficulty": "HARD",
        "difficulty_category": "Complex Decision Boundary",
        "provenance": {"stage2_polish": stage2, "stage2_model": "m" if stage2 else ""},
    }
    if pushback is not None:
        r["pushback"] = pushback
    return r


class TestRefGrain:
    def test_heads_collapse_subpoints(self):
        assert _heads(["Annex IV.2", "Annex IV.1.e", "Article 6.3"]) == {"Annex IV", "Article 6"}

    def test_heads_collapse_parenthesised_form(self):
        assert _heads(["Article 5(1)(a)"]) == {"Article 5"}

    def test_exact_preserves_subpoint_grain(self):
        # The grain the grounded judge scores at — must NOT be collapsed.
        assert _exact(["Annex IV", "Annex IV.2"]) == {"Annex IV", "Annex IV.2"}

    def test_blank_and_none_are_dropped(self):
        assert _heads(None) == set()
        assert _exact(["", "  "]) == set()

    @pytest.mark.parametrize(
        "a,b,expected",
        [(set(), set(), 1.0), ({"A"}, {"A"}, 1.0), ({"A"}, {"B"}, 0.0), ({"A", "B"}, {"A"}, 0.5)],
    )
    def test_jaccard(self, a, b, expected):
        assert _jacc(a, b) == expected


class TestStratification:
    def test_stage2_flag_read_from_provenance(self):
        assert _stage2(_row("x", [], stage2=True)) is True
        assert _stage2(_row("x", [], stage2=False)) is False
        assert _stage2({"id": "x"}) is False

    def test_treatment_and_control_are_split_on_stage2(self):
        pre = {
            "s": _row("s", ["Article 6"], stage2=True),
            "d": _row("d", ["Article 11"], stage2=False),
        }
        post = {
            "s": _row("s", ["Article 6", "Article 9"], stage2=True),
            "d": _row("d", ["Article 11"], stage2=False),
        }
        res = diff_arm(pre, post, "st")
        strata = {s["stratum"]: s for s in res["strata"]}
        treat = strata["STAGE2 LANDED (treatment)"]
        control = strata["deterministic / curated (control)"]

        assert treat["n"] == 1 and control["n"] == 1
        # the added ref is attributed to the treatment stratum only
        assert treat["refs_added_total"] == 1
        assert control["refs_added_total"] == 0
        assert control["rows_refs_changed"] == 0


class TestNoFalsePositives:
    def test_identical_runs_report_zero_change(self):
        rows = {"a": _row("a", ["Article 6", "Annex IV.2"]), "b": _row("b", ["Article 11"])}
        res = diff_arm(dict(rows), dict(rows), "st")
        all_stratum = res["strata"][0]
        assert all_stratum["rows_refs_changed"] == 0
        assert all_stratum["rows_answer_changed"] == 0
        assert all_stratum["refs_added_total"] == 0
        assert all_stratum["refs_dropped_total"] == 0
        assert all(r["ref_jaccard"] == 1.0 for r in res["rows"])

    def test_added_and_dropped_are_reported_separately(self):
        pre = {"a": _row("a", ["Article 6", "Article 51"])}
        post = {"a": _row("a", ["Article 6", "Article 53"])}
        res = diff_arm(pre, post, "st")
        row = res["rows"][0]
        assert row["refs_added"] == ["Article 53"]
        assert row["refs_dropped"] == ["Article 51"]
        assert row["refs_changed"] is True

    def test_ids_present_in_only_one_run_are_surfaced(self):
        res = diff_arm({"a": _row("a", ["Article 6"])}, {"b": _row("b", ["Article 6"])}, "st")
        assert set(res["ids_only_in_one_run"]) == {"a", "b"}
        assert res["n_common"] == 0


class TestMultiTurnArm:
    def test_mt_arm_records_pushback_flip(self):
        pre = {"a": _row("a", ["Article 6"], pushback={"ref_heads_changed": []})}
        post = {"a": _row("a", ["Article 6"], pushback={"ref_heads_changed": ["Article 9"]})}
        res = diff_arm(pre, post, "mt")
        row = res["rows"][0]
        assert row["pushback_flip_pre"] is False
        assert row["pushback_flip_post"] is True
        assert res["strata"][0]["pushback_flip_pre"] == 0.0
        assert res["strata"][0]["pushback_flip_post"] == 1.0

    def test_st_arm_omits_pushback_fields(self):
        res = diff_arm({"a": _row("a", ["Article 6"])}, {"a": _row("a", ["Article 6"])}, "st")
        assert "pushback_flip_pre" not in res["rows"][0]
