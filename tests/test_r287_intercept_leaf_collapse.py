"""R287 — multi-leaf collapse for curated authoritative intercepts.

Motivated by the r286 live easy batch (110 production rows) graded by the
grounded Sonnet-5 judge: reference precision 0.615 against recall 0.913 — we
over-cite rather than under-retrieve — with pass rate collapsing by ref count
(1 ref: 12/14; 3 refs: 5/38; 5 refs: 0/17). The judge's most repeated
``failure_mode`` was redundant parent/leaf citations of a single provision.

The collapse is deliberately the NARROW half of the R276-D1 granularity pass:
it fires only on a head carrying TWO OR MORE of its own leaves (the
enumeration-dump shape), so a deliberate 1-parent + 1-leaf pairing such as the
R274 deviation intercept's ``Article 6`` + ``Article 6.3`` survives untouched.
"""

from __future__ import annotations

import pytest

from app.routes.regenold import _collapse_multi_leaf_clusters


class TestRecallSafety:
    """Every head in the input must survive — the R142.1 non-negotiable."""

    @pytest.mark.parametrize(
        "refs",
        [
            ["Article 11", "Annex IV.1.e", "Annex IV.2.c", "Annex IV", "Annex IV.2"],
            ["Article 65.3", "Article 65.4", "Article 65.5", "Article 65.7", "Article 65"],
            ["Annex III.8.a", "Annex III.8.b", "Annex III.8", "Annex III"],
            ["Article 5", "Article 6", "Annex III.8.b", "Annex III.8", "Annex III"],
            ["Article 6", "Article 6.3"],
            ["Article 13"],
            [],
        ],
    )
    def test_no_head_is_ever_lost(self, refs: list[str]) -> None:
        def heads(rs: list[str]) -> set[str]:
            out = set()
            for r in rs:
                for p in ("Article ", "Annex "):
                    if r.startswith(p):
                        out.add(p + r[len(p) :].split(".")[0])
            return out

        assert heads(_collapse_multi_leaf_clusters(refs)) == heads(refs)

    def test_never_empties(self) -> None:
        assert _collapse_multi_leaf_clusters(["Annex IV.1", "Annex IV.2"]) != []

    def test_pure_does_not_mutate_input(self) -> None:
        refs = ["Article 65", "Article 65.3", "Article 65.4"]
        snapshot = list(refs)
        _collapse_multi_leaf_clusters(refs)
        assert refs == snapshot

    def test_idempotent(self) -> None:
        refs = ["Article 65", "Article 65.3", "Article 65.4", "Article 65.5"]
        once = _collapse_multi_leaf_clusters(refs)
        assert _collapse_multi_leaf_clusters(once) == once


class TestCollapsesEnumerationDumps:
    """The 4-5-ref rows the judge scored 0/17."""

    def test_rg_001_annex_iv_dump(self) -> None:
        # Live wire shipped 5 refs; the judge called it
        # "over-citation with redundant parent-annex".
        out = _collapse_multi_leaf_clusters(
            ["Article 11", "Annex IV.1.e", "Annex IV.2.c", "Annex IV", "Annex IV.2"]
        )
        assert out == ["Article 11", "Annex IV"]

    def test_rg_033_article_65_dump(self) -> None:
        out = _collapse_multi_leaf_clusters(
            ["Article 65.3", "Article 65.4", "Article 65.5", "Article 65.7", "Article 65"]
        )
        assert out == ["Article 65"]

    def test_rg_027_partial_collapse_keeps_distinct_articles(self) -> None:
        out = _collapse_multi_leaf_clusters(
            ["Article 5", "Article 6", "Annex III.8.b", "Annex III.8", "Annex III"]
        )
        assert out == ["Article 5", "Article 6", "Annex III.8"]


class TestKeepsDeepestDominatingAncestor:
    """r287 measured regression: collapsing to the bare head loses sub-point grain.

    rg_012 shipped Annex III + Annex III.8 + Annex III.8.a + Annex III.8.b.
    Collapsing to ``Annex III`` scored recall 1.0 -> 0.0 ("overbroad - cited
    entire Annex III instead of the specific point 8"). The gold IS the
    sub-point, so head-level invariance is not sufficient.
    """

    def test_rg_012_keeps_point_8_not_bare_annex(self) -> None:
        out = _collapse_multi_leaf_clusters(
            ["Annex III.8.a", "Annex III.8.b", "Annex III.8", "Annex III"]
        )
        assert out == ["Annex III.8"]

    def test_multi_branch_falls_back_to_head(self) -> None:
        # IV.1.e and IV.2.c live on different branches, so no single leaf
        # dominates -> the head is the only correct common ancestor.
        out = _collapse_multi_leaf_clusters(
            ["Article 11", "Annex IV.1.e", "Annex IV.2.c", "Annex IV", "Annex IV.2"]
        )
        assert out == ["Article 11", "Annex IV"]

    def test_flat_sibling_leaves_keep_head(self) -> None:
        out = _collapse_multi_leaf_clusters(
            ["Article 65.3", "Article 65.4", "Article 65.5", "Article 65"]
        )
        assert out == ["Article 65"]

    def test_order_is_preserved(self) -> None:
        out = _collapse_multi_leaf_clusters(
            ["Annex IV", "Article 11", "Annex IV.1", "Annex IV.2"]
        )
        assert out == ["Annex IV", "Article 11"]


class TestPreservesDeliberatePairings:
    """A single leaf beside its parent is a general-rule + carve-out pair."""

    def test_r274_article_6_and_6_3_survive(self) -> None:
        refs = ["Article 6", "Article 6.3", "Annex III"]
        assert _collapse_multi_leaf_clusters(refs) == refs

    def test_single_leaf_pair_untouched(self) -> None:
        refs = ["Article 11.1", "Article 11", "Annex IV", "Annex IV.2"]
        assert _collapse_multi_leaf_clusters(refs) == refs

    def test_leaf_only_cluster_untouched(self) -> None:
        # Parent absent -> nothing to collapse against.
        refs = ["Annex IV.1.e", "Annex IV.2.c"]
        assert _collapse_multi_leaf_clusters(refs) == refs

    def test_distinct_articles_untouched(self) -> None:
        refs = ["Article 26", "Article 79", "Article 72", "Article 73"]
        assert _collapse_multi_leaf_clusters(refs) == refs

    def test_short_lists_are_noops(self) -> None:
        assert _collapse_multi_leaf_clusters(["Article 6", "Article 6.3"]) == [
            "Article 6",
            "Article 6.3",
        ]
