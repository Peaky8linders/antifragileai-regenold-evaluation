"""Unit tests for the BM25F retriever (euaiact.baselines.bm25).

Coverage:
- determinism: identical results on repeated calls;
- content-word ranking: a provision with distinctive body terms ranks first;
- field boost: a provision whose citation matches the queried article number
  outranks a body-only near-match, and zeroing the heading weight reverses
  that outcome, proving the boost does the work;
- empty / all-stopword / OOV queries return [];
- tie-breaking by provision_id ascending.

Run with: .venv/bin/python -m pytest tests/test_bm25.py -q
"""

from __future__ import annotations

import unittest

from euaiact.baselines.bm25 import Bm25Retriever
from euaiact.models import Provision


def _p(pid: str, text: str) -> Provision:
    return Provision(provision_id=pid, chunk_type="paragraph", text=text)


# ---------------------------------------------------------------------------
# Shared corpus for most tests
# ---------------------------------------------------------------------------

# Three provisions.  art_6__para_2's citation auto-derives to "Art. 6(2)".
# art_5__para_1's citation auto-derives to "Art. 5(1)".
# art_50__para_1's citation auto-derives to "Art. 50(1)".

PROV = [
    _p("art_5__para_1",  "prohibited practices subliminal manipulation techniques operators"),
    _p("art_6__para_2",  "high risk classification annex criteria derogation"),
    _p("art_50__para_1", "transparency obligations chatbot disclosure inform users"),
]


class TestDeterminism(unittest.TestCase):
    def test_same_query_same_order(self):
        r = Bm25Retriever(PROV)
        q = "high risk classification annex"
        self.assertEqual(r.search(q, 3), r.search(q, 3))

    def test_same_query_same_scored(self):
        r = Bm25Retriever(PROV)
        q = "transparency chatbot disclosure"
        self.assertEqual(r.search_scored(q, 3), r.search_scored(q, 3))


class TestContentWordRanking(unittest.TestCase):
    def test_body_match_ranks_first(self):
        r = Bm25Retriever(PROV)
        self.assertEqual(r.search("subliminal manipulation", 1), ["art_5__para_1"])

    def test_chatbot_transparency_ranks_first(self):
        r = Bm25Retriever(PROV)
        self.assertEqual(r.search("chatbot transparency disclosure", 1), ["art_50__para_1"])

    def test_high_risk_annex_ranks_first(self):
        r = Bm25Retriever(PROV)
        self.assertEqual(r.search("high risk annex criteria", 1), ["art_6__para_2"])


class TestFieldBoost(unittest.TestCase):
    """The heading field (citation) should lift a provision above a body-richer
    rival when the query explicitly names its article number.

    Setup:
      - art_100__para_1  has a thin body ("classification") but its auto-derived
        citation is "Art. 100(1)", which tokenises to ["art", "100"].  The token
        "100" is unique to this provision.
      - art_113__para_1  has a richer body ("article classification risk obligations
        transparency") but its heading does NOT contain "100".

    The BM25-local tokenizer keeps all-digit tokens regardless of length (see
    ``TestLowArticleNumberBoost`` for the 1-2 digit case that the shared tokenizer
    would have dropped); this test uses a 3-digit number that survives either way.

    With default heading weight 2.0, art_100__para_1 ranks first because its
    heading token "100" picks up the article-number boost from the query.

    With heading weight 0.0, the heading field is suppressed and the body-richer
    art_113__para_1 wins, proving the boost is doing the work.
    """

    # art_100__para_1 citation auto-derives to "Art. 100(1)"; heading tokens: ["art", "100"]
    # art_113__para_1 citation auto-derives to "Art. 113(1)"; heading tokens: ["art", "113"]
    BOOST_PROV = [
        _p("art_100__para_1", "classification"),                                       # thin body
        _p("art_113__para_1", "article classification risk obligations transparency"),  # rich body
    ]

    def test_heading_boost_lifts_cited_provision(self):
        # Query "article 100 classification": token "100" matches art_100__para_1's
        # heading with weight 2.0, lifting it above the body-richer art_113__para_1.
        r = Bm25Retriever(self.BOOST_PROV)
        results = r.search("article 100 classification", 2)
        self.assertEqual(
            results[0], "art_100__para_1",
            "art_100__para_1 should rank first: heading token '100' (weight 2.0) boosts it",
        )

    def test_zeroing_heading_weight_changes_outcome(self):
        # With heading weight 0.0, "100" in the heading carries no weight.
        # art_113__para_1's richer body ("article classification risk obligations
        # transparency") should now outscore art_100__para_1's thin body ("classification").
        r_no_heading = Bm25Retriever(
            self.BOOST_PROV,
            field_weights={"body": 1.0, "heading": 0.0},
        )
        results = r_no_heading.search("article 100 classification", 2)
        self.assertEqual(
            results[0], "art_113__para_1",
            "zeroing heading weight should let the body-richer provision win",
        )


class TestLowArticleNumberBoost(unittest.TestCase):
    """The field boost must fire for the 1-2 digit article numbers (1-99) that
    cover the great majority of the Act. The shared ``retrieval.tokenize`` drops
    tokens of length <= 2, silently discarding "6"/"50"; the BM25-local tokenizer
    keeps them, so a query naming a low article number reaches the heading field.

    Setup mirrors ``TestFieldBoost`` but with a single-digit article number:
      - art_6__para_2  thin body ("classification"), heading "Art. 6(2)" -> "6".
      - art_7__para_1  richer body, heading "Art. 7(1)" (no "6").
    Query "article 6 classification" tokenises to ["article", "6", "classification"]
    only because digit tokens survive; the "6" boosts art_6__para_2 above the
    body-richer art_7__para_1. Under the old shared tokenizer "6" would vanish and
    art_7__para_1 would win, so this test fails without the fix.
    """

    LOW_PROV = [
        _p("art_6__para_2", "classification"),
        _p("art_7__para_1", "article classification risk obligations transparency"),
    ]

    def test_single_digit_article_number_boosts(self):
        r = Bm25Retriever(self.LOW_PROV)
        results = r.search("article 6 classification", 2)
        self.assertEqual(
            results[0], "art_6__para_2",
            "single-digit heading token '6' (weight 2.0) must boost art_6__para_2",
        )

    def test_zeroing_heading_weight_drops_low_number_boost(self):
        r = Bm25Retriever(
            self.LOW_PROV,
            field_weights={"body": 1.0, "heading": 0.0},
        )
        results = r.search("article 6 classification", 2)
        self.assertEqual(
            results[0], "art_7__para_1",
            "with the heading suppressed the body-richer provision must win",
        )

    def test_low_number_query_is_not_empty(self):
        # "6" alone is a valid in-vocabulary term via the heading field.
        r = Bm25Retriever(self.LOW_PROV)
        self.assertEqual(r.search("6", 1), ["art_6__para_2"])


class TestEmptyAndOOV(unittest.TestCase):
    def test_empty_query_returns_empty(self):
        r = Bm25Retriever(PROV)
        self.assertEqual(r.search("", 3), [])

    def test_stopword_only_query_returns_empty(self):
        # All tokens filtered by tokenize() because they are stopwords or too short
        r = Bm25Retriever(PROV)
        self.assertEqual(r.search("the an of to", 3), [])

    def test_oov_query_returns_empty(self):
        r = Bm25Retriever(PROV)
        self.assertEqual(r.search("zzz qqq nonexistenttermxyz", 3), [])

    def test_mixed_oov_and_stop_returns_empty(self):
        r = Bm25Retriever(PROV)
        self.assertEqual(r.search("zzz the qqq", 3), [])


class TestTieBreaking(unittest.TestCase):
    """When two provisions have identical BM25F scores, result order must be
    alphabetically ascending by provision_id (deterministic)."""

    def test_ties_broken_by_provision_id(self):
        # Construct two provisions with the exact same single-word text so they
        # must get the same score for a query matching that word.
        tied = [
            _p("art_9__para_1", "surveillance"),
            _p("art_3__para_1", "surveillance"),
        ]
        r = Bm25Retriever(tied)
        results = r.search("surveillance", 2)
        # art_3__para_1 < art_9__para_1 lexicographically
        self.assertEqual(results, ["art_3__para_1", "art_9__para_1"])


class TestKLimit(unittest.TestCase):
    def test_k_limits_results(self):
        r = Bm25Retriever(PROV)
        self.assertLessEqual(len(r.search("classification disclosure manipulation", 2)), 2)

    def test_k_zero_returns_empty(self):
        r = Bm25Retriever(PROV)
        self.assertEqual(r.search("classification", 0), [])


class TestSearchScored(unittest.TestCase):
    def test_scores_positive_and_descending(self):
        r = Bm25Retriever(PROV)
        scored = r.search_scored("chatbot disclosure transparency", 3)
        self.assertTrue(len(scored) > 0)
        vals = [s for _, s in scored]
        self.assertTrue(all(v > 0 for v in vals))
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_search_is_consistent_with_search_scored(self):
        r = Bm25Retriever(PROV)
        q = "high risk annex criteria"
        self.assertEqual(r.search(q, 3), [pid for pid, _ in r.search_scored(q, 3)])


if __name__ == "__main__":
    unittest.main()
