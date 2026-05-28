"""R91 — plural article + per-item sub-point attribution.

Pins the fix for two misparse bugs in
``app.integrations.regenold.scope.extract_referenced_articles``:

1. ``Articles 13 and 14(2)`` previously attributed ``(2)`` to the head
   article (Art. 13), not Art. 14.
2. ``Art. 13(1) and 14`` previously dropped Art. 14 entirely because
   the plural-tail regex didn't tolerate a sub-point chain between
   numbers.

The fix widens ``_ARTICLE_REF_RE`` to allow ``(N)`` sub-points after
each number AND replaces the head-only sub-chain attribution with a
per-item walker (``_parse_article_items``).
"""
from __future__ import annotations

from app.integrations.regenold.scope import extract_referenced_articles


class TestR91PluralArticleSubpoints:
    def test_subpoint_attaches_to_tail_article(self) -> None:
        # R91 bug #1 — (2) MUST attach to 14, not 13.
        known, unknown = extract_referenced_articles("Compare Articles 13 and 14(2).")
        assert known == ("Art. 13", "Art. 14(2)")
        assert unknown == ()

    def test_head_subpoint_does_not_drop_tail(self) -> None:
        # R91 bug #2 — (1) between 13 and 14 must not stop the regex
        # from consuming "and 14".
        known, unknown = extract_referenced_articles("Compare Art. 13(1) and 14.")
        assert known == ("Art. 13(1)", "Art. 14")
        assert unknown == ()

    def test_both_articles_carry_own_subpoint(self) -> None:
        known, unknown = extract_referenced_articles("Compare Art. 13(1)(a) and 14(2).")
        assert known == ("Art. 13(1)(a)", "Art. 14(2)")
        assert unknown == ()

    def test_single_article_unchanged(self) -> None:
        # Regression guard — the single-article path is byte-identical.
        known, unknown = extract_referenced_articles("What does Art. 13 require?")
        assert known == ("Art. 13",)
        assert unknown == ()

    def test_three_bare_articles_via_comma_and(self) -> None:
        known, unknown = extract_referenced_articles("Articles 13, 14, and 15")
        assert known == ("Art. 13", "Art. 14", "Art. 15")
        assert unknown == ()

    def test_three_articles_each_with_own_subpoint(self) -> None:
        known, unknown = extract_referenced_articles(
            "Articles 13(1), 14(2), and 15(3)"
        )
        assert known == ("Art. 13(1)", "Art. 14(2)", "Art. 15(3)")
        assert unknown == ()

    def test_gdpr_prefix_claim_wins(self) -> None:
        # The other-regulation claimed-span filter must still skip the
        # whole ``GDPR Articles 13 and 14(2)`` span.
        known, unknown = extract_referenced_articles("GDPR Articles 13 and 14(2)")
        assert known == ()
        assert unknown == ()
