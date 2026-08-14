"""R337 — the `gold_dropped` veto must know the gold's GRAIN before it fires.

`gold_dropped` is a VETO (hard rule #8): a non-zero drop is a rejection, no
argument. That makes a false positive unusually expensive — it rejects correct
work, and it is designed to be read without scepticism.

`gold_dropped_exact` compares full coordinates. Against HEAD-level gold, a MORE
precise citation therefore scores as a dropped head:

    gold_dropped_exact(["Article 6.1"], gold=["Article 6"]) -> dropped 1
    gold_dropped_head (["Article 6.1"], gold=["Article 6"]) -> dropped 0

`dynamic_ab`'s probe set is 208 gold refs over 129 rows with **zero** carrying a
sub-point, so on that pool the exact veto measures "did we get more precise",
sign inverted. Measured live on R333's sub-point fix: exact said 10 -> 5 while
head said +0 and every axis was exactly 0.0000 — i.e. the veto would have
rejected a change that dropped nothing.

The danger of the fix is the mirror image: silencing a REAL veto. So both
directions are asserted here.
"""
from __future__ import annotations

from evals.bench import metrics as M
from evals.harness import dynamic_ab as D


# ── the underlying asymmetry this all rests on ───────────────────────────


def test_exact_grain_counts_a_more_precise_citation_as_a_drop():
    """The measured fact that motivates the whole guard."""
    assert M.gold_dropped_exact(["Article 6.1"], ["Article 6"])["dropped_count"] == 1
    assert M.gold_dropped_head(["Article 6.1"], ["Article 6"])["dropped_count"] == 0


def _rows(pred_by_id, gold):
    """Two arms over the same ids, with `row.expected_refs` carrying the gold."""
    out = []
    for rid, refs in pred_by_id.items():
        out.append({
            "id": rid,
            "pred_answer": "a",
            "pred_refs": refs,
            "row": {"expected_refs": list(gold)},
            "scores": D._score(
                type("R", (), {"expected_refs": tuple(gold),
                               "expected_keywords": ()})(),
                "a", refs),
        })
    return out


# ── applicability ────────────────────────────────────────────────────────


def test_exact_veto_is_marked_INAPPLICABLE_on_head_level_gold():
    gold = ["Article 6"]
    base = _rows({"r1": ["Article 6"]}, gold)
    brch = _rows({"r1": ["Article 6.1"]}, gold)
    res = D._analyse(base, brch, null_band=0.01)
    ex = res["gold"]["gold_dropped_exact"]
    assert ex["applicable"] is False
    assert ex["gold_leaf_grained"] == 0
    # head grain remains authoritative and shows NO drop for the precise cite
    assert res["gold"]["gold_dropped_head"]["applicable"] is True
    assert res["gold"]["gold_dropped_head"]["delta"] == 0


def test_exact_veto_STAYS_APPLICABLE_when_gold_carries_sub_points():
    """The guard must not silence the veto on gold that can actually support it —
    otherwise it converts a safety rail into a blindfold."""
    gold = ["Article 6.1", "Annex IV.1.e"]
    base = _rows({"r1": ["Article 6.1", "Annex IV.1.e"]}, gold)
    brch = _rows({"r1": ["Article 6.1"]}, gold)
    res = D._analyse(base, brch, null_band=0.01)
    ex = res["gold"]["gold_dropped_exact"]
    assert ex["applicable"] is True
    assert ex["gold_leaf_grained"] == 2
    assert ex["delta"] > 0, "a genuine leaf-grain gold drop must still veto"


# ── the printed report ───────────────────────────────────────────────────


def _render(res) -> str:
    lines: list[str] = []
    res = {**res, "label": "t", "n_scored": 1, "stop_reason": "resolved",
           "fire": {"any_changed": 1, "common": 1}}
    D._report(res, emit=lines.append)
    return "\n".join(lines)


def test_report_prints_a_reason_not_a_number_when_inapplicable():
    gold = ["Article 6"]
    res = D._analyse(_rows({"r1": ["Article 6"]}, gold),
                     _rows({"r1": ["Article 6.1"]}, gold), null_band=0.01)
    out = _render(res)
    assert "head-level" in out
    assert "HARD RULE #8 VETO" not in out, "must not veto on an inapplicable grain"
    assert "REJECTED" not in out


def test_report_still_REJECTS_on_a_real_leaf_grain_drop():
    gold = ["Article 6.1", "Annex IV.1.e"]
    res = D._analyse(_rows({"r1": ["Article 6.1", "Annex IV.1.e"]}, gold),
                     _rows({"r1": ["Article 6.1"]}, gold), null_band=0.01)
    out = _render(res)
    assert "HARD RULE #8 VETO" in out
    assert "REJECTED" in out
