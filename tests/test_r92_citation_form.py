"""R92 — wire citation-form enforcement.

The official competition rules require citations as "Article N" (Arabic)
/ "Annex R" (Roman). The answer prose must match that voice — the rules'
own GOOD exemplars write "Article 13", never the "Art. 13" short form
(also CLAUDE.md hard rule #1: never emit "Art. 13" on the wire).

These tests pin the prose-level normaliser
(`_normalise_prose_citation_form`) + its integration into
`normalise_answer_for_regenold`, plus the broader invariant that no
wire answer ships the forbidden "Art. N" form.
"""
from __future__ import annotations

import re

import pytest

from app.integrations.regenold.models import (
    _normalise_prose_citation_form,
    normalise_answer_for_regenold,
)

_FORBIDDEN = re.compile(r"\bArts?\.\s*\d")


class TestProseCitationNormaliser:
    @pytest.mark.parametrize(
        "raw,must_contain",
        [
            ("Under Art. 2 (Scope), providers must comply.", "Article 2"),
            ("Establish a quality-management system (Art. 17).", "(Article 17)"),
            ("Art. 5(5) lets authorities act.", "Article 5(5)"),
            ("Arts. 13 and 14 require transparency.", "Articles 13 and 14"),
            ("Art.13 with no space.", "Article 13"),
            ("art. 26 lowercase form.", "Article 26"),
        ],
    )
    def test_converts_short_form(self, raw: str, must_contain: str) -> None:
        out = _normalise_prose_citation_form(raw)
        assert must_contain in out
        assert not _FORBIDDEN.search(out), out

    @pytest.mark.parametrize(
        "raw",
        [
            "Article 13 requires high-risk AI systems to be transparent.",
            "Annex IV.2 lists the technical documentation contents.",
            "Annex III covers eight high-risk use cases.",
            "This is the best part. 13 reasons exist.",  # 'part. 13' untouched
            "We restart. 5 systems remain.",  # 'restart. 5' untouched
            "",
        ],
    )
    def test_leaves_compliant_or_irrelevant_text_unchanged(self, raw: str) -> None:
        assert _normalise_prose_citation_form(raw) == raw

    def test_idempotent(self) -> None:
        s = "Under Art. 2 and Arts. 13 and 14(2), see Art. 5(5)."
        once = _normalise_prose_citation_form(s)
        assert _normalise_prose_citation_form(once) == once
        assert not _FORBIDDEN.search(once)


class TestNormaliserIntegration:
    def test_normalise_answer_strips_art_form(self) -> None:
        ans = "Under Art. 2 the Regulation applies. Art. 16 binds providers."
        out = normalise_answer_for_regenold(ans)
        assert not _FORBIDDEN.search(out), out
        assert "Article 2" in out
        assert "Article 16" in out

    def test_env_off_switch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_CITATION_FORM", "0")
        ans = "Under Art. 2 the Regulation applies."
        out = normalise_answer_for_regenold(ans)
        # With the enforcer disabled the short form survives.
        assert "Art. 2" in out
