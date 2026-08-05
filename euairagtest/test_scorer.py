#!/usr/bin/env python3
"""Unit tests for the EU AI Act citation scorer. Pure stdlib: run with

    python3 -m unittest test_scorer
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import scorer  # noqa: F401  (import first: puts euaiact on sys.path)
from euaiact.ids import ProvisionId
from scorer import (
    Citation,
    bootstrap_ci,
    evaluate_item,
    exact_similarity,
    load_predictions,
    oracle_predictions,
    parse_citation,
    provision_similarity,
    score_corpus,
    set_scores,
)


def pid(s: str) -> ProvisionId:
    return ProvisionId.parse(s)


def cits(*ss: str) -> list[Citation]:
    return [parse_citation(s) for s in ss]


class SimilarityKernel(unittest.TestCase):
    def test_identical_is_one(self):
        self.assertEqual(provision_similarity(pid("art_5__para_1__point_a"), pid("art_5__para_1__point_a")), 1.0)

    def test_ancestor_partial_credit(self):
        # article predicted, point wanted: LCP=1, max depth=3 -> 1/3
        self.assertAlmostEqual(provision_similarity(pid("art_5"), pid("art_5__para_1__point_a")), 1 / 3)
        # one level off: LCP=2, max depth=3 -> 2/3
        self.assertAlmostEqual(provision_similarity(pid("art_5__para_1"), pid("art_5__para_1__point_a")), 2 / 3)

    def test_symmetry(self):
        a, b = pid("art_5"), pid("art_5__para_1__point_a")
        self.assertEqual(provision_similarity(a, b), provision_similarity(b, a))

    def test_siblings_score_zero(self):
        self.assertEqual(provision_similarity(pid("art_5__para_1__point_a"), pid("art_5__para_1__point_b")), 0.0)
        self.assertEqual(provision_similarity(pid("art_5__para_1"), pid("art_5__para_2")), 0.0)

    def test_cross_root_zero(self):
        self.assertEqual(provision_similarity(pid("art_5"), pid("annex_III")), 0.0)
        self.assertEqual(provision_similarity(pid("recital_33"), pid("art_5")), 0.0)

    def test_exact_kernel(self):
        self.assertEqual(exact_similarity(pid("art_5"), pid("art_5")), 1.0)
        self.assertEqual(exact_similarity(pid("art_5"), pid("art_5__para_1")), 0.0)


class Parsing(unittest.TestCase):
    def test_human_and_eid_forms_agree(self):
        self.assertEqual(parse_citation("Art. 5(1)(a)").pid.eid, "art_5__para_1__point_a")
        self.assertEqual(parse_citation("art_5__para_1__point_a").pid.eid, "art_5__para_1__point_a")

    def test_unparseable_is_none(self):
        c = parse_citation("Article 35 GDPR")
        self.assertIsNone(c.pid)
        self.assertTrue(c.key.startswith("<unparsed:"))


class SetScores(unittest.TestCase):
    def test_perfect_match(self):
        g = cits("art_5__para_1__point_a", "art_6__para_2")
        self.assertEqual(set_scores(g, g, provision_similarity), (1.0, 1.0, 1.0))
        self.assertEqual(set_scores(g, g, exact_similarity), (1.0, 1.0, 1.0))

    def test_granularity_tax(self):
        gold = cits("art_5__para_1__point_a")
        pred = cits("art_5")  # right article, wrong grain
        p, r, f = set_scores(pred, gold, provision_similarity)
        self.assertAlmostEqual(p, 1 / 3)
        self.assertAlmostEqual(r, 1 / 3)
        self.assertAlmostEqual(f, 1 / 3)
        # exact match gives zero credit -> the "granularity tax"
        self.assertEqual(set_scores(pred, gold, exact_similarity), (0.0, 0.0, 0.0))

    def test_empty_prediction_scores_zero(self):
        self.assertEqual(set_scores([], cits("art_5"), provision_similarity), (0.0, 0.0, 0.0))

    def test_wrong_provision_scores_zero(self):
        self.assertEqual(set_scores(cits("art_99"), cits("art_5"), provision_similarity), (0.0, 0.0, 0.0))


class ItemEvaluation(unittest.TestCase):
    def _item(self, **kw):
        base = dict(
            id="t", gold_citations=[], negative_control=False, hallucination_trap=False
        )
        base.update(kw)
        return base

    def test_answerable_soft_and_exact(self):
        item = self._item(gold_citations=[{"provision_id": "art_5__para_1__point_a"}])
        r = evaluate_item(item, ["art_5"], None)
        self.assertTrue(r.answerable)
        self.assertAlmostEqual(r.soft[2], 1 / 3)
        self.assertEqual(r.exact[2], 0.0)

    def test_negative_control_abstains(self):
        item = self._item(negative_control=True)
        r = evaluate_item(item, [], None)
        self.assertFalse(r.answerable)
        self.assertFalse(r.fp)
        self.assertIsNone(r.soft)

    def test_negative_control_false_positive(self):
        item = self._item(negative_control=True)
        r = evaluate_item(item, ["art_5"], None)
        self.assertTrue(r.fp)

    def test_trap_empty_gold_triggered_by_any_citation(self):
        item = self._item(negative_control=True, hallucination_trap=True)
        r = evaluate_item(item, ["Article 35 GDPR"], None)
        self.assertTrue(r.trap_triggered)
        self.assertEqual(r.off_lineage, ["Article 35 GDPR"])

    def test_trap_answerable_only_wrong_citation_triggers(self):
        item = self._item(
            gold_citations=[{"provision_id": "art_53__para_1__point_a"}],
            hallucination_trap=True,
        )
        # correct-only prediction does not trigger
        self.assertFalse(evaluate_item(item, ["art_53__para_1__point_a"], None).trap_triggered)
        # an extra off-lineage citation does
        r = evaluate_item(item, ["art_53__para_1__point_a", "art_99"], None)
        self.assertTrue(r.trap_triggered)
        self.assertEqual(r.off_lineage, ["art_99"])

    def test_missing_prediction_flagged(self):
        item = self._item(gold_citations=[{"provision_id": "art_5"}])
        r = evaluate_item(item, None, None)
        self.assertFalse(r.predicted)
        self.assertEqual(r.soft, (0.0, 0.0, 0.0))

    def test_known_provisions_flags_unknown(self):
        item = self._item(
            gold_citations=[{"provision_id": "art_53__para_1__point_a"}],
            hallucination_trap=True,
        )
        # art_53__para_1__point_a is on-lineage but absent from the known set ->
        # flagged as a hallucination when --known-provisions is supplied
        r = evaluate_item(item, ["art_53__para_1__point_a"], known={"art_5"})
        self.assertTrue(r.trap_triggered)


class Bootstrap(unittest.TestCase):
    def test_point_is_mean(self):
        vals = [0.0, 0.5, 1.0, 0.25]
        pt, lo, hi = bootstrap_ci(vals, n_boot=500, seed=1)
        self.assertAlmostEqual(pt, sum(vals) / len(vals))
        self.assertLessEqual(lo, pt)
        self.assertLessEqual(pt, hi)

    def test_deterministic_under_seed(self):
        vals = [0.1, 0.9, 0.4, 0.6, 0.2]
        self.assertEqual(bootstrap_ci(vals, 300, seed=7), bootstrap_ci(vals, 300, seed=7))

    def test_zero_boot_collapses_to_point(self):
        pt, lo, hi = bootstrap_ci([0.2, 0.8], n_boot=0, seed=0)
        self.assertEqual((lo, hi), (pt, pt))

    def test_empty_is_nan(self):
        pt, lo, hi = bootstrap_ci([], 100, 0)
        self.assertNotEqual(pt, pt)  # NaN


class Oracles(unittest.TestCase):
    ITEMS = [
        {"id": "a", "gold_citations": [{"provision_id": "art_5__para_1__point_a"}], "negative_control": False, "hallucination_trap": False},
        {"id": "b", "gold_citations": [{"provision_id": "annex_III__point_5"}], "negative_control": False, "hallucination_trap": False},
    ]

    def test_full_oracle_is_perfect(self):
        preds = oracle_predictions(self.ITEMS, "full")
        rep = score_corpus(self.ITEMS, preds, n_boot=0, seed=0)
        self.assertEqual(rep["soft"]["f1"]["point"], 1.0)
        self.assertEqual(rep["exact"]["f1"]["point"], 1.0)

    def test_root_oracle_shows_granularity_gap(self):
        preds = oracle_predictions(self.ITEMS, "root")
        self.assertEqual(preds["a"], ["art_5"])
        self.assertEqual(preds["b"], ["annex_III"])
        rep = score_corpus(self.ITEMS, preds, n_boot=0, seed=0)
        # soft credit stays positive, exact collapses toward zero
        self.assertGreater(rep["soft"]["f1"]["point"], rep["exact"]["f1"]["point"])
        self.assertEqual(rep["exact"]["f1"]["point"], 0.0)


class PredictionLoading(unittest.TestCase):
    def test_list_form(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "preds.json"
            p.write_text(json.dumps({"x": ["art_5", "Art. 6(2)(a)"]}))
            self.assertEqual(load_predictions(p), {"x": ["art_5", "Art. 6(2)(a)"]})

    def test_dict_form_citations_key(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "preds.json"
            p.write_text(json.dumps({"x": {"citations": ["art_5"]}}))
            self.assertEqual(load_predictions(p), {"x": ["art_5"]})

    def test_end_to_end_via_predictions_dict(self):
        # exercise the real --predictions scoring path (not the oracle shortcut)
        items = [{
            "id": "a",
            "gold_citations": [{"provision_id": "art_5__para_1__point_a"}],
            "negative_control": False,
            "hallucination_trap": False,
        }]
        rep = score_corpus(items, {"a": ["art_5__para_1__point_a"]}, n_boot=0, seed=0)
        self.assertEqual(rep["soft"]["f1"]["point"], 1.0)
        self.assertEqual(rep["exact"]["f1"]["point"], 1.0)


class Truncate(unittest.TestCase):
    """_truncate must keep a citation as-is when it is shallower than the target
    grain -- never collapse it to the root (regression: `else: depth = 1`)."""

    def test_point_grain_keeps_para_citation_as_is(self):
        self.assertEqual(scorer._truncate(pid("art_6__para_2"), "point").eid, "art_6__para_2")

    def test_para_grain_keeps_para_citation(self):
        self.assertEqual(scorer._truncate(pid("art_6__para_2"), "para").eid, "art_6__para_2")

    def test_point_grain_keeps_point_citation(self):
        self.assertEqual(scorer._truncate(pid("art_5__para_1__point_a"), "point").eid, "art_5__para_1__point_a")

    def test_para_grain_truncates_point_to_para(self):
        self.assertEqual(scorer._truncate(pid("art_5__para_1__point_a"), "para").eid, "art_5__para_1")

    def test_article_only_stays_article_under_finer_grain(self):
        self.assertEqual(scorer._truncate(pid("art_6"), "point").eid, "art_6")


class OracleMonotonicity(unittest.TestCase):
    """A finer-grain oracle can never score below a coarser one; the buggy
    _truncate made `point` fall below `para` for para-level gold."""

    ITEMS = [
        {"id": "p", "gold_citations": [{"provision_id": "art_6__para_2"}],
         "negative_control": False, "hallucination_trap": False},
        {"id": "q", "gold_citations": [{"provision_id": "art_5__para_1__point_a"}],
         "negative_control": False, "hallucination_trap": False},
    ]

    def test_finer_oracle_never_scores_below_coarser(self):
        f1 = {}
        for g in ("root", "para", "point", "full"):
            rep = score_corpus(self.ITEMS, oracle_predictions(self.ITEMS, g), n_boot=0, seed=0)
            f1[g] = rep["soft"]["f1"]["point"]
        self.assertLessEqual(f1["root"], f1["para"])
        self.assertLessEqual(f1["para"], f1["point"])  # the fix: point >= para
        self.assertLessEqual(f1["point"], f1["full"])
        self.assertEqual(f1["full"], 1.0)


if __name__ == "__main__":
    unittest.main()
