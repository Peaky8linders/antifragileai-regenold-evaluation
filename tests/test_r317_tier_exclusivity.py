"""R317 — Chapter III tier-exclusivity pass.

Every assertion here is pinned to a MEASURED counterexample from the round, so a
future edit that re-breaks one fails loudly instead of silently shipping the
R142.1 failure mode again. The comments name what each guard cost when it was
missing.
"""
from __future__ import annotations

import pytest

from app.routes.regenold import (
    _apply_tier_exclusivity,
    _r317_verdict,
)


# ── verdict detection ───────────────────────────────────────────────────────
class TestVerdictDetection:
    def test_plain_prohibited(self):
        assert _r317_verdict("No, this is prohibited. Article 5(1)(f) bans it.") == "PROHIBITED"

    def test_high_risk(self):
        assert _r317_verdict("This system is classified as high-risk under Annex III.") == "HIGH_RISK"

    def test_not_high_risk(self):
        assert _r317_verdict("The system is not high-risk; it is minimal risk.") == "NOT_HIGH_RISK"

    def test_empty_is_unknown(self):
        assert _r317_verdict("") == "UNKNOWN"

    def test_unrecognised_is_unknown_keep_by_default(self):
        assert _r317_verdict("Article 43 requires a conformity assessment.") == "UNKNOWN"

    def test_negated_prohibition_is_not_a_prohibited_verdict(self):
        """The exact deterministic opener that broke two 276-suite rows.

        "The system described is NOT among the practices prohibited under
        Article 5 ..." read naively as PROHIBITED, which then stripped the
        rank-0 governing article (Article 13 / Article 10).
        """
        ans = ("The system described is not among the practices prohibited under "
               "Article 5 (social scoring, untargeted facial-image scraping, "
               "manipulative or exploitative techniques, and the other "
               "exhaustively-listed bans).")
        assert _r317_verdict(ans) != "PROHIBITED"

    def test_not_prohibited_but_high_risk_reads_high_risk(self):
        ans = "This is not a prohibited practice, but it is high-risk under Annex III."
        assert _r317_verdict(ans) == "HIGH_RISK"

    def test_verdict_read_from_the_lead_only(self):
        """A later hypothetical must not flip the verdict."""
        ans = ("This system is classified as high-risk under Annex III. " + "x " * 200 +
               " It would not be high-risk if it were purely a spam filter.")
        assert _r317_verdict(ans) == "HIGH_RISK"


# ── the pass ────────────────────────────────────────────────────────────────
PROHIBITED = "No, this is prohibited. Article 5(1)(f) bans emotion inference at work."
NOT_HR = "The system is not high-risk; it is minimal risk."
HIGH_RISK = "This system is classified as high-risk under Annex III."


class TestTierExclusivity:
    """Pass MECHANICS. R317 measured that this pass drops 67 davidath GOLD refs
    (Ref Loose -0.0160), so its production default is now OFF; these tests
    opt in explicitly so the mechanics stay covered for a future re-A/B. The
    default itself is pinned in test_r317_annex_iii_infra_guard.py.
    """

    @pytest.fixture(autouse=True)
    def _enable(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_TIER_EXCLUSIVITY", "1")

    def test_drops_chapter_iii_on_prohibited(self):
        out = _apply_tier_exclusivity(
            ["Article 5", "Article 27", "Article 49", "Article 6"],
            "Is this permitted?", PROHIBITED)
        assert out == ["Article 5", "Article 6"]

    def test_drops_chapter_iii_on_not_high_risk(self):
        out = _apply_tier_exclusivity(
            ["Article 6", "Annex III", "Article 9", "Annex I"],
            "What risk level applies?", NOT_HR)
        assert "Article 9" not in out

    def test_noop_on_high_risk_verdict(self):
        refs = ["Article 6", "Annex III", "Article 9", "Article 43"]
        assert _apply_tier_exclusivity(list(refs), "Is it high-risk?", HIGH_RISK) == refs

    def test_noop_on_unknown_verdict(self):
        refs = ["Article 43", "Article 47"]
        assert _apply_tier_exclusivity(list(refs), "What does Article 43 require?", "") == refs

    def test_never_drops_the_classification_tests(self):
        """Article 5/6 and Annex I/III are the TESTS, not machinery.

        Measured: an earlier cut that treated Annex I/III as machinery dropped
        6 GOLD refs on the 132-row probe set, whose minimal-risk gold is
        literally ["Annex III", "Article 50", "Article 6"].
        """
        refs = ["Article 5", "Article 6", "Annex I", "Annex III"]
        assert _apply_tier_exclusivity(list(refs), "Is it high-risk?", NOT_HR) == refs

    def test_never_drops_the_machinery_annexes(self):
        """Annex IV-VIII are NOT in the drop set.

        Measured: including them was the ONLY thing that destroyed governing
        refs on the independent judged hold-out (Annex VII on rg_106, Annex
        VIII on rg_066). Ablating them took the hold-out to 0 destroyed.
        """
        refs = ["Article 5", "Annex VII", "Annex VIII", "Annex IV"]
        out = _apply_tier_exclusivity(list(refs), "Is it permitted?", PROHIBITED)
        for a in ("Annex VII", "Annex VIII", "Annex IV"):
            assert a in out

    def test_never_drops_the_lead_reference(self):
        """63.5% of gold sits at rank 0 (measured, 132-row gold probe set).

        This is what protects the role-transition rows whose deterministic
        answer opens with the R33 default-limited FALLBACK template while
        Article 25 / Article 26 legitimately lead.
        """
        out = _apply_tier_exclusivity(
            ["Article 25", "Article 50", "Article 9"],
            "Does our legal role change?", NOT_HR)
        assert out[0] == "Article 25"

    def test_never_drops_a_question_named_provision(self):
        out = _apply_tier_exclusivity(
            ["Article 5", "Article 9"],
            "What does Article 9 require here?", PROHIBITED)
        assert "Article 9" in out

    def test_never_empties(self):
        assert _apply_tier_exclusivity(["Article 9"], "Is it allowed?", PROHIBITED) == ["Article 9"]

    def test_empty_input_is_returned_unchanged(self):
        assert _apply_tier_exclusivity([], "q", PROHIBITED) == []

    def test_is_idempotent(self):
        refs = ["Article 5", "Article 27", "Article 49", "Article 6"]
        once = _apply_tier_exclusivity(list(refs), "Is this permitted?", PROHIBITED)
        twice = _apply_tier_exclusivity(list(once), "Is this permitted?", PROHIBITED)
        assert once == twice

    def test_env_off_switch(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_TIER_EXCLUSIVITY", "0")
        refs = ["Article 5", "Article 9"]
        assert _apply_tier_exclusivity(list(refs), "Is it allowed?", PROHIBITED) == refs

    def test_default_is_off_so_the_pass_is_a_noop(self, monkeypatch):
        """R317: default flipped ON -> OFF after davidath measured 67 gold drops."""
        monkeypatch.delenv("REGENOLD_TIER_EXCLUSIVITY", raising=False)
        refs = ["Article 5", "Article 27"]
        assert _apply_tier_exclusivity(list(refs), "Is it allowed?", PROHIBITED) == refs

    def test_scans_only_the_live_turn_for_named_provisions(self):
        """R71: a PRIOR turn's article must not rescue a ref the live turn never named."""
        q = ("Conversation so far:\nuser: What does Article 27 require?\n\n"
             "Latest question:\nIs this permitted at all?")
        out = _apply_tier_exclusivity(["Article 5", "Article 27"], q, PROHIBITED)
        assert "Article 27" not in out

    @pytest.mark.parametrize("bad", [None, 12345])
    def test_fail_soft_on_bad_answer_type(self, bad):
        refs = ["Article 5", "Article 9"]
        try:
            out = _apply_tier_exclusivity(list(refs), "q", bad)  # type: ignore[arg-type]
        except Exception:  # the route wraps this in try/except, but prefer no raise
            pytest.fail("pass must not raise on a malformed answer")
        assert isinstance(out, list)
