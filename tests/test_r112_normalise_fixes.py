"""R112 regression tests — answer-normalisation / tone / auth /
grounded-prose coverage fixes.

Pins the uncommitted R112 hunks in ``app/integrations/regenold/``:

8.  ``models._extract_subpoints`` contiguity guard (finding 31 —
    "Art. 13(1)(a) and (b)" must reject the WHOLE chain, never assemble
    the phantom "Article 13.1.a.b").
9.  ``models._KB_STUB_LABEL_RE`` token-bounded Article tail (finding 10 —
    "Article 5(1) prohibits the following: …" must not be amputated).
10. ``models._is_degenerate_sentence`` short-verdict whitelist
    (finding 45 — "Yes." survives, "1." still drops).
11. ``models._normalise_prose_citation_form`` case-sensitive bare form
    (finding 46 — "state of the art 2024" untouched).
12. ``models.normalise_answer_for_regenold`` closing-char-aware
    terminator (finding 44 — a sentence ending '."' gains no stray
    extra period).
13. ``models.normalise_answer_for_regenold`` defensive
    ``REGENOLD_QA_LENGTH_CAP`` env parse (findings 22/29 — malformed
    value falls back to the 400 default instead of raising).
14. ``tone_guard.enforce_tone`` post-positioned participle hedge
    (finding 30 — no garbled "Provided, …").
15. ``auth.validate_regenold_api_key`` non-ASCII key (finding 32 —
    returns False, never raises).
16. ``grounded_prose._answer_covers_ref`` boundary-aware literal cite
    check (finding 28 — "Article 22" does not cover "Art. 2";
    "Annex IX" does not cover "Annex I").
"""
from __future__ import annotations

import pytest
from pydantic import SecretStr

from app.integrations.regenold.models import (
    _extract_subpoints,
    _is_degenerate_sentence,
    _normalise_prose_citation_form,
    _strip_kb_stub_label,
    normalise_answer_for_regenold,
    reference_from_article_ref,
)


# ── 8. _extract_subpoints contiguity ─────────────────────────────────────


class TestExtractSubpointsContiguity:
    """R112 finding 31 — inter-token prose rejects the whole chain."""

    def test_conjunction_tail_rejects_whole_chain(self) -> None:
        # "Art. 13(1)(a) and (b)" → tail "(1)(a) and (b)" → the " and "
        # residue must reject everything (all-or-nothing policy), not
        # assemble the phantom "Article 13.1.a.b".
        assert _extract_subpoints("(1)(a) and (b)") == []

    def test_clean_tail_extracts_proper_chain(self) -> None:
        assert _extract_subpoints("(1)(a)") == ["1", "a"]

    def test_qualifier_prose_between_tokens_rejects(self) -> None:
        # "Art. 13(1) second subparagraph (a)" — swallowing the qualifier
        # would emit a DIFFERENT provision (Article 13.1.a).
        assert _extract_subpoints("(1) second subparagraph (a)") == []

    def test_end_to_end_reference_formatting(self) -> None:
        # Through the public formatter: the conjunction form drops the
        # whole citation; the clean form still formats.
        assert reference_from_article_ref("Art. 13(1)(a) and (b)") is None
        assert reference_from_article_ref("Art. 13(1)(a)") == "Article 13.1.a"


# ── 9. _KB_STUB_LABEL_RE token-bounded tail ──────────────────────────────


class TestKbStubLabelStrip:
    """R112 finding 10 — prose colons no longer amputate the lead clause."""

    def test_prohibits_framing_survives_strip(self) -> None:
        s = "Article 5(1) prohibits the following: (a) subliminal techniques"
        assert _strip_kb_stub_label(s) == s

    def test_prohibits_framing_survives_normalise(self) -> None:
        text = (
            "Article 5(1) prohibits the following: (a) subliminal "
            "techniques beyond a person's consciousness."
        )
        out = normalise_answer_for_regenold(text)
        assert "prohibits the following" in out

    def test_genuine_label_still_stripped(self) -> None:
        out = _strip_kb_stub_label("Art. 13: Providers shall ensure transparency.")
        assert out == "Providers shall ensure transparency."


# ── 10. Short verdict sentences survive ──────────────────────────────────


class TestShortVerdictSurvival:
    """R112 finding 45 — 'Yes.' carries the gold boolean token."""

    def test_yes_is_not_degenerate(self) -> None:
        assert _is_degenerate_sentence("Yes.") is False

    def test_bare_list_marker_is_degenerate(self) -> None:
        assert _is_degenerate_sentence("1.") is True


# ── 11. Prose citation form — case-sensitive bare 'Art' ──────────────────


class TestProseCitationForm:
    """R112 finding 46 — lowercase 'art' before a digit is real English."""

    def test_state_of_the_art_untouched(self) -> None:
        s = "state of the art 2024 benchmarks"
        assert _normalise_prose_citation_form(s) == s

    def test_lowercase_dotted_citation_still_rewritten(self) -> None:
        assert _normalise_prose_citation_form("art. 13 requires") == (
            "Article 13 requires"
        )

    def test_bare_capitalised_art_rewritten(self) -> None:
        assert _normalise_prose_citation_form("Art 13") == "Article 13"


# ── 12. Closing-char-aware terminator ────────────────────────────────────


class TestClosingCharTerminator:
    """R112 finding 44 — '."'-terminated sentences gain no stray period.

    NOTE: a quote-terminated sentence at a LINE end picks up a period
    from ``_strip_markdown``'s line-terminator promotion (a separate,
    pre-existing site), so the R112 branch is exercised via shapes
    where the sentence reaches the final R103c pass ending '."':
    (a) an ellipsis-clipped quote tail (the scrub leaves '."' as the
    last characters), and (b) a mid-line quote sentence followed by
    more prose (never split apart, so no terminator is re-decided).
    """

    def test_quote_then_ellipsis_ships_clean_quote_end(self) -> None:
        text = (
            'The Act defines an AI system as "a machine-based system '
            'designed to operate with varying levels of autonomy."...'
        )
        out = normalise_answer_for_regenold(text)
        assert out.endswith('."'), out
        assert '.".' not in out

    def test_mid_text_quote_period_gains_no_stray_period(self) -> None:
        text = (
            'Article 3 defines an AI system as "a machine-based system '
            'designed to operate with varying levels of autonomy." '
            "Article 4 requires providers to ensure AI literacy."
        )
        out = normalise_answer_for_regenold(text)
        assert '.".' not in out
        assert out.endswith("literacy.")


# ── 13. Defensive REGENOLD_QA_LENGTH_CAP parse ───────────────────────────


class TestQaLengthCapEnvParse:
    """R112 findings 22/29 — malformed env value must not raise; the 400
    default applies instead."""

    # Three sentences: two short cite-anchored + one long non-cite filler.
    # Total > 400 chars → under the 400 default the soft-cap loop drops
    # the long non-cite sentence; under a 2000 cap it survives.
    _LONG_FILLER = (
        "This explanation restates the general background context of the "
        "regulation at considerable length without naming any provision "
        "and continues to elaborate on the surrounding policy debate in "
        "general terms that add no citation-anchored substance whatsoever "
        "to the regulatory answer being given here, while also repeating "
        "the same broad framing once more so the combined answer clearly "
        "exceeds the four-hundred character default budget"
    )
    _TEXT = (
        "Article 13 requires transparency for high-risk systems. "
        + _LONG_FILLER
        + ". Article 14 requires human oversight measures."
    )

    def test_malformed_value_does_not_raise(self, monkeypatch) -> None:
        monkeypatch.setenv("REGENOLD_QA_LENGTH_CAP", "600px")
        out = normalise_answer_for_regenold(self._TEXT)  # must not raise
        assert out

    def test_malformed_value_applies_400_default(self, monkeypatch) -> None:
        monkeypatch.setenv("REGENOLD_QA_LENGTH_CAP", "600px")
        out_malformed = normalise_answer_for_regenold(self._TEXT)
        monkeypatch.setenv("REGENOLD_QA_LENGTH_CAP", "400")
        out_400 = normalise_answer_for_regenold(self._TEXT)
        assert out_malformed == out_400
        # Sanity: the input IS cap-sensitive — a generous cap keeps the
        # long filler sentence the 400 default drops.
        monkeypatch.setenv("REGENOLD_QA_LENGTH_CAP", "2000")
        out_2000 = normalise_answer_for_regenold(self._TEXT)
        assert out_malformed != out_2000


# ── 14. Tone guard — post-positioned participle hedge ────────────────────


def test_based_on_the_information_provided_strips_cleanly() -> None:
    """R112 finding 30 — the whole hedge is consumed; no garbled
    'Provided, …' opener survives."""
    from app.integrations.regenold.tone_guard import enforce_tone

    out = enforce_tone(
        "Based on the information provided, Article 13 requires transparency."
    )
    assert out.startswith("Article 13")
    assert not out.startswith("Provided")


# ── 15. Auth — non-ASCII key never raises ────────────────────────────────


def test_non_ascii_api_key_returns_false_without_exception() -> None:
    """R112 finding 32 — ``secrets.compare_digest`` raises TypeError on
    non-ASCII str input; the validator now compares UTF-8 bytes and
    fails closed."""
    from app.config import settings
    from app.integrations.regenold.auth import validate_regenold_api_key

    previous = settings.regenold.api_key
    settings.regenold.api_key = SecretStr("regenold-test-key")
    try:
        assert validate_regenold_api_key("kéy€") is False
        # The matching key still validates (bytes comparison is faithful).
        assert validate_regenold_api_key("regenold-test-key") is True
    finally:
        settings.regenold.api_key = previous


# ── 16. _answer_covers_ref boundary awareness ────────────────────────────


class TestAnswerCoversRefBoundary:
    """R112 finding 28 — literal cite check requires a numeric / Roman
    boundary. ``answer_tokens=frozenset()`` keeps the BM25 fallback
    silent (0 overlap < threshold) so only the literal signal is
    exercised."""

    def test_article_22_does_not_cover_art_2(self) -> None:
        from app.integrations.regenold.grounded_prose import _answer_covers_ref

        covered = _answer_covers_ref(
            frozenset(),
            "Art. 2",
            answer_text="Article 22 sets out authorised representative duties.",
        )
        assert covered is False

    def test_article_2_covers_art_2(self) -> None:
        from app.integrations.regenold.grounded_prose import _answer_covers_ref

        covered = _answer_covers_ref(
            frozenset(),
            "Art. 2",
            answer_text="Article 2 sets out the scope of the Regulation.",
        )
        assert covered is True

    def test_annex_ix_does_not_cover_annex_i(self) -> None:
        from app.integrations.regenold.grounded_prose import _answer_covers_ref

        covered = _answer_covers_ref(
            frozenset(),
            "Annex I",
            answer_text="Annex IX lists the Union legislation on large-scale IT systems.",
        )
        assert covered is False

    def test_annex_i_covers_annex_i(self) -> None:
        from app.integrations.regenold.grounded_prose import _answer_covers_ref

        covered = _answer_covers_ref(
            frozenset(),
            "Annex I",
            answer_text="Annex I lists the Union harmonisation legislation.",
        )
        assert covered is True
