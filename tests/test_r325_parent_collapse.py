"""R325 — drop a bare head when its own sub-point is already cited.

The grounded judge's most frequent reference remark, implemented and gated.
Measured on the 100 recorded July-7 rows: precision +0.0285, F1 +0.0177,
5 rows flip fail->pass, 0 flip pass->fail, at the cost of ONE correct
reference across 273.

These tests pin three things, in order of what would actually bite:

  1. DEFAULT OFF. It is a reference-dropping change; hard rule #6 makes
     easyhard_ab the merge gate, so the default must not move ahead of it.
  2. The head-grain invariant. davidath scores through ``article_heads()``,
     so the collapse MUST be a no-op there. If that ever stops being true,
     this is silently an R142.1-class clamp.
  3. It only fires on a head whose OWN leaf is present — not on a head that
     merely shares a number with an unrelated annex, and not on a bare list.
"""

from __future__ import annotations

import pytest

from evals.bench.metrics import article_heads

from app.routes.regenold import (
    _collapse_parent_when_subpoint_cited as collapse,
    _parent_collapse_enabled,
)


class TestDefaultOff:
    def test_default_is_off(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("REGENOLD_PARENT_COLLAPSE", raising=False)
        assert _parent_collapse_enabled() is False

    @pytest.mark.parametrize("v", ["1", "true", "yes", "on", "TRUE", "On"])
    def test_opt_in_values(self, monkeypatch: pytest.MonkeyPatch, v: str) -> None:
        monkeypatch.setenv("REGENOLD_PARENT_COLLAPSE", v)
        assert _parent_collapse_enabled() is True

    @pytest.mark.parametrize("v", ["0", "false", "no", "off", ""])
    def test_off_values(self, monkeypatch: pytest.MonkeyPatch, v: str) -> None:
        monkeypatch.setenv("REGENOLD_PARENT_COLLAPSE", v)
        assert _parent_collapse_enabled() is False


class TestCollapse:
    def test_drops_the_parent_of_a_cited_subpoint(self) -> None:
        assert collapse(["Article 50", "Article 50.4"]) == ["Article 50.4"]

    def test_keeps_order(self) -> None:
        assert collapse(
            ["Article 11", "Article 11.1", "Annex IV", "Annex IV.2", "Article 26"]
        ) == ["Article 11.1", "Annex IV.2", "Article 26"]

    def test_deep_subpoint(self) -> None:
        assert collapse(["Article 5", "Article 5.1.f"]) == ["Article 5.1.f"]

    def test_annex_roman_head(self) -> None:
        assert collapse(["Annex IV", "Annex IV.2"]) == ["Annex IV.2"]

    def test_multiple_leaves_of_one_head(self) -> None:
        assert collapse(
            ["Annex IV", "Annex IV.1.e", "Annex IV.2.c"]
        ) == ["Annex IV.1.e", "Annex IV.2.c"]

    def test_unrelated_head_survives(self) -> None:
        """Article 26 has no cited sub-point of its OWN — it must stay."""
        assert collapse(["Article 50.4", "Article 26"]) == ["Article 50.4", "Article 26"]

    def test_annex_iv_is_not_the_parent_of_article_4(self) -> None:
        """Same digit, different kind. A naive number match would eat one."""
        assert collapse(["Annex IV", "Article 4.1"]) == ["Annex IV", "Article 4.1"]

    def test_bare_heads_untouched(self) -> None:
        refs = ["Article 6", "Annex III", "Article 26"]
        assert collapse(refs) == refs

    def test_all_subpoints_untouched(self) -> None:
        refs = ["Article 6.3", "Article 50.4"]
        assert collapse(refs) == refs

    @pytest.mark.parametrize("refs", [[], ["Article 6"]])
    def test_short_lists_are_returned_unchanged(self, refs: list[str]) -> None:
        assert collapse(refs) == refs

    def test_never_returns_empty(self) -> None:
        """A pathological all-parent list must not be emptied."""
        assert collapse(["Article 6", "Article 6.3"]) == ["Article 6.3"]
        assert collapse(["Article 6.3"]) == ["Article 6.3"]

    def test_idempotent(self) -> None:
        once = collapse(["Article 50", "Article 50.4", "Article 26"])
        assert collapse(once) == once


class TestHeadGrainInvariant:
    """davidath scores through ``article_heads()`` — the collapse must be a
    no-op there. If this breaks, the change silently becomes a gold-dropping
    clamp on the 476."""

    @pytest.mark.parametrize(
        "refs",
        [
            ["Article 50", "Article 50.4"],
            ["Article 6", "Article 6.3", "Annex III"],
            ["Annex IV", "Annex IV.1.e", "Annex IV.2.c", "Article 11", "Article 11.1"],
            ["Article 5", "Article 5.1.f", "Article 50", "Article 50.3"],
        ],
    )
    def test_head_set_is_identical(self, refs: list[str]) -> None:
        assert article_heads(collapse(refs)) == article_heads(refs)


class TestKnownTradeIsPinned:
    """The one measured loss, recorded so it is a deliberate trade and not a
    surprise. R274 pins Article 6 + Article 6.3 as BOTH load-bearing (the
    general high-risk rule beside its own derogation); the collapse drops the
    head anyway, because no cheap signal separates it from the nine wins."""

    def test_article_6_pair_is_collapsed_and_that_is_known(self) -> None:
        assert collapse(["Article 6.3", "Article 6", "Annex III"]) == [
            "Article 6.3",
            "Annex III",
        ]

    def test_but_the_head_grain_still_carries_article_6(self) -> None:
        """Which is why davidath and any head-grain gold are unaffected."""
        out = collapse(["Article 6.3", "Article 6", "Annex III"])
        assert "Article 6" in article_heads(out)
