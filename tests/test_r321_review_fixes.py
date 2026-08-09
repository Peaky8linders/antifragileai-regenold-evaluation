"""R321 — regression tests for the review fixes.

Every test here pins a defect that was MEASURED on the live code, not inferred.
Each docstring records the measurement so a future round can tell a real
regression from a contract change.
"""
from __future__ import annotations

import os

import pytest


# ── Foreign-instrument citation leak (Critical) ─────────────────────────────


class TestForeignInstrumentRefLeak:
    """`GDPR Art. 5` must never be promoted to AI Act `Article 5`.

    MEASURED before the fix::

        _add_prose_named_refs(["Article 27"],
            "...under EU Charter Art. 21 and on personal data under GDPR
             Art. 5, complementing GDPR Art. 35 DPIA duties.")
        -> ['Article 27', 'Article 21', 'Article 5', 'Article 35']

    Article 5 is the prohibited-practices article, so that is a confidently
    wrong legal claim in a wire-legal shape. The pre-existing guard only
    looked AHEAD ("Article 50 of the GDPR"); this covers the PREFIX form,
    which is exactly what ``kg_context`` injects into the Stage-2 context.
    """

    @pytest.mark.parametrize(
        "prose",
        [
            "The assessment evaluates non-discrimination under EU Charter Art. 21.",
            "Personal data processing is governed by GDPR Art. 5.",
            "This complements GDPR Art. 35 DPIA duties.",
            "Conformity follows MDR Article 52 for class IIb devices.",
            "See Directive Article 9 for the sectoral rule.",
        ],
    )
    def test_foreign_instrument_prefix_never_leaks(self, prose: str) -> None:
        from app.routes.regenold import _add_prose_named_refs

        base = ["Article 27"]
        out = _add_prose_named_refs(list(base), prose, cap=4)
        assert out == base, f"foreign-instrument number leaked onto the wire: {out}"

    def test_real_ai_act_mentions_are_still_promoted(self) -> None:
        """The guard must not make the whole pass inert."""
        from app.routes.regenold import _add_prose_named_refs

        prose = (
            "Under Article 13 the provider must ensure transparency, and "
            "Article 14 requires human oversight."
        )
        out = _add_prose_named_refs(["Article 26"], prose, cap=4)
        assert "Article 13" in out and "Article 14" in out

    def test_ai_act_mention_after_a_gdpr_sentence_still_promoted(self) -> None:
        """Only an IMMEDIATELY preceding qualifier suppresses (24-char window)."""
        from app.routes.regenold import _add_prose_named_refs

        prose = (
            "The GDPR governs personal data. Separately, Article 10 of this "
            "Regulation governs data governance."
        )
        out = _add_prose_named_refs(["Article 26"], prose, cap=4)
        assert "Article 10" in out


# ── Sections removed in R325 — they pin PARENT-ONLY features ────────────────
#
# This file arrived with the R321 foreign-citation cherry-pick, which is why
# the two classes below are here and green. Three further classes came with it
# and were REMOVED, not "fixed" and not left red:
#
#   TestFRIAArticle27Trigger        needs app/engines/fria_evaluator.py
#   TestDerogationAndExemptionScope needs the art6_3_derogated risk level
#   TestLiveSentenceCapFailsClosed  needs REGENOLD_LIVE_SENTENCE_CAP
#
# None of those three exists in this repo, and R325 deliberately did NOT port
# them (correctness-only sync; and the Art 6(3) derogation is a feature whose
# absence means the wrong-law defect its fix repairs cannot occur here —
# verified live: "Is an AI system that screens and ranks job applicants
# high-risk?" already answers "high-risk ... Annex III, point 4(a)").
#
# Ten permanently-red tests would mask a real regression in the failure-set
# A/B that is this repo's only reliable full-suite gate, which is worse than
# not having them. If any of those three features is ever ported, restore the
# matching class from the RAG repo at 6d7a3e1 / 777e0f4 / 2568bb3.

# ── Deploy safety (Critical) ────────────────────────────────────────────────


class TestDeploySafety:
    def test_healthz_does_no_llm_call_by_default(self) -> None:
        """/healthz is Railway's healthcheckPath under a 30 s timeout. As
        shipped it fired a live Groq completion whose budget fell back to the
        60 s singleton default."""
        from app.main import _healthz_probe_enabled

        assert _healthz_probe_enabled() is False

    @pytest.mark.parametrize("val,expected", [("1", True), ("true", True),
                                              ("0", False), ("", False)])
    def test_healthz_probe_is_opt_in(self, val: str, expected: bool, monkeypatch) -> None:
        from app.main import _healthz_probe_enabled

        monkeypatch.setenv("REGENOLD_HEALTHZ_PROBE", val)
        assert _healthz_probe_enabled() is expected
