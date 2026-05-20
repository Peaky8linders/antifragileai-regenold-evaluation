"""R67 — Unicode punctuation normalisation regression tests.

Pins the fix for the six davidath QA rows (qa_030 / 033 / 042 / 064 /
068 / 080) that were wrongly refused as out-of-scope because the
question text carried U+2011 non-breaking hyphens the ASCII-literal
scope-anchor matcher couldn't see.
"""
from __future__ import annotations

import pytest

from app.integrations.regenold.text_normalize import normalize_unicode_punctuation as N


class TestDashFolding:
    def test_non_breaking_hyphen_folds_to_ascii(self) -> None:
        # U+2011 — the davidath culprit.
        assert N("deep‑fake content") == "deep-fake content"

    def test_all_dash_variants_fold(self) -> None:
        for cp in ("‐", "‑", "‒", "–", "—", "−"):
            assert N(f"market{cp}surveillance") == "market-surveillance"

    def test_ascii_hyphen_untouched(self) -> None:
        assert N("post-market monitoring") == "post-market monitoring"


class TestSpaceFolding:
    def test_narrow_no_break_space_folds(self) -> None:
        # U+202F — 17 occurrences in the davidath set.
        assert N("Article 13") == "Article 13"

    def test_no_break_space_folds(self) -> None:
        assert N("Annex IV") == "Annex IV"

    def test_thin_space_folds(self) -> None:
        assert N("35 %") == "35 %"


class TestQuoteFolding:
    def test_smart_single_quotes_fold(self) -> None:
        assert N("‘AI system’") == "'AI system'"

    def test_smart_double_quotes_fold(self) -> None:
        assert N("“provider”") == '"provider"'


class TestInvariants:
    def test_empty_and_falsy_passthrough(self) -> None:
        assert N("") == ""
        assert N(None) is None  # type: ignore[arg-type]

    def test_length_preserving(self) -> None:
        # Every mapping is 1 code point -> 1 code point, so the engine's
        # 2 000-char question cap + 4 000-char message cap are unaffected.
        src = "deep‑fake ‘test’ market–surveillance now"
        assert len(N(src)) == len(src)

    def test_idempotent(self) -> None:
        src = "conformity‑assessment body “notification”"
        once = N(src)
        assert N(once) == once

    def test_ascii_only_input_unchanged(self) -> None:
        src = "What does Article 13 require for high-risk AI systems?"
        assert N(src) == src

    def test_pure_ascii_punctuation_preserved(self) -> None:
        assert N("a-b 'c' \"d\"") == "a-b 'c' \"d\""


class TestDavidathRefusalShapes:
    """The exact six davidath QA questions whose U+2011 / missing-anchor
    shapes R67 traced. After normalisation each must carry the ASCII
    anchor token the scope gate needs."""

    @pytest.mark.parametrize(
        "raw,expected_substr",
        [
            (
                "What must a conformity‑assessment body submit "
                "when applying for notification?",
                "conformity-assessment",
            ),
            (
                "What labeling requirement exists for deep‑fake content?",
                "deep-fake",
            ),
            (
                "When can a market‑surveillance authority suspend or "
                "withdraw a certificate?",
                "market-surveillance",
            ),
            (
                "What is the purpose of the post‑market monitoring plan "
                "template to be adopted by the Commission?",
                "post-market",
            ),
            (
                "What are the confidentiality obligations for "
                "market‑surveillance authorities?",
                "market-surveillance",
            ),
        ],
    )
    def test_davidath_u2011_questions_normalise(
        self, raw: str, expected_substr: str
    ) -> None:
        out = N(raw)
        assert "‑" not in out
        assert expected_substr in out
