"""Regression guards for the two follow-up fixes shipped in this repo.

Fix 1 — ``app/integrations/regenold/scope.py::_live_question_borrows_anchor``
    extended ``follow_markers`` with ``"are these"`` / ``"how often"`` /
    ``"what if we re-train"``. Closes 3 multi-conversation eval refusals
    where the live follow-up plainly inherited an anchor from the prior
    assistant turn but didn't carry one of the original ``what about`` /
    ``and X`` style markers.

Fix 2 — ``app/engines/graph_rag.py::_extract_json_object``
    robust JSON cleanup. The original markdown-fence stripper only handled
    full-response fenced JSON. The new helper tolerates prose-before-JSON,
    prose-after-JSON, multiple fences, language tags after backticks,
    no-fences-at-all (brace-span extraction), and trailing commas.

Both fixes are intentionally narrow — no behaviour change for the happy
path. The tests below pin the new behaviour AND the unchanged happy path.
"""
from __future__ import annotations

import pytest

from app.engines.graph_rag import _extract_json_object
from app.integrations.regenold.scope import (
    _live_question_borrows_anchor,
    classify_conversation,
)

# ─── Fix 1 — follow_markers extension ─────────────────────────────────────


class TestFollowMarkersExtension:
    """Direct unit tests on the helper."""

    @pytest.mark.parametrize(
        "live_text",
        [
            "How often do we update them?",
            "How often must instructions be refreshed?",
            "Are these requirements mandatory?",
            "Are these the only obligations?",
            "What if we re-train the model?",
            "What if we retrain monthly?",
            "What if we re train annually?",
        ],
    )
    def test_new_markers_borrow_anchor(self, live_text: str) -> None:
        anchors = ("Art. 13",)
        assert _live_question_borrows_anchor(live_text, anchors) is True, (
            f"Expected {live_text!r} to borrow the prior-turn anchor"
        )

    def test_anchor_borrow_disabled_when_no_anchors(self) -> None:
        # Even with a follow_marker present, an empty anchors tuple must
        # not yield a positive — the function exists to RESCUE anchored
        # follow-ups, not invent context out of thin air.
        assert _live_question_borrows_anchor("How often?", ()) is False

    def test_conversational_filler_does_not_borrow(self) -> None:
        # The fix must not regress the existing conversational-filler
        # guard — "Thanks!" carries zero compliance content even after a
        # real Q&A turn.
        anchors = ("Art. 13",)
        assert _live_question_borrows_anchor("Thanks!", anchors) is False


class TestMultiTurnAnchorBorrow:
    """End-to-end through ``classify_conversation`` — the route's entry point."""

    def test_how_often_followup_anchors_on_prior_article(self) -> None:
        msgs = [
            {"role": "user", "content": "What does Art. 13 require for transparency?"},
            {
                "role": "assistant",
                "content": (
                    "Article 13(1) requires high-risk providers to design "
                    "transparency mechanisms."
                ),
            },
            {"role": "user", "content": "How often do we update them?"},
        ]
        verdict = classify_conversation(msgs)
        assert verdict.in_scope is True, (
            f"Expected in_scope; got {verdict.reason.value}: {verdict.verdict.evidence}"
        )
        assert "Art. 13" in verdict.anchor_articles

    def test_are_these_followup_anchors_on_prior_article(self) -> None:
        msgs = [
            {"role": "user", "content": "What obligations does Art. 26 impose on deployers?"},
            {
                "role": "assistant",
                "content": "Article 26 imposes a set of obligations on deployers of high-risk AI.",
            },
            {"role": "user", "content": "Are these mandatory for SMEs too?"},
        ]
        verdict = classify_conversation(msgs)
        assert verdict.in_scope is True
        assert "Art. 26" in verdict.anchor_articles

    def test_what_if_we_retrain_followup_anchors(self) -> None:
        msgs = [
            {"role": "user", "content": "Does Art. 11 require updated technical documentation?"},
            {
                "role": "assistant",
                "content": "Article 11(2) requires documentation to be kept up to date.",
            },
            {"role": "user", "content": "What if we re-train the model quarterly?"},
        ]
        verdict = classify_conversation(msgs)
        assert verdict.in_scope is True
        assert "Art. 11" in verdict.anchor_articles


class TestStrongMarkerOrderingHardening:
    """The strong-marker branch must NOT invent context out of thin air.

    Hardening: the docstring on ``_live_question_borrows_anchor`` says
    "exists to RESCUE anchored follow-ups, not invent context". The
    ``if not anchors: return False`` short-circuit must run BEFORE the
    strong-marker check, so a long input with a strong marker but no
    prior anchors stays False. Pinning the order here protects against
    a refactor that reorders the gates.
    """

    def test_strong_marker_with_empty_anchors_returns_false(self) -> None:
        # "how often" is a strong marker, but no prior turn established
        # an anchor — must NOT borrow.
        assert _live_question_borrows_anchor(
            "How often must instructions be refreshed under our framework?",
            (),
        ) is False

    def test_pure_conversational_filler_returns_false(self) -> None:
        # The conversational-filler guard fires before the strong-marker
        # check — pin that ordering. A bare "Thanks!" with no follow-up
        # question shape carries no compliance content.
        assert _live_question_borrows_anchor("Thanks!", ("Art. 13",)) is False
        assert _live_question_borrows_anchor("Bye.", ("Art. 13",)) is False


# ─── Fix 2 — robust JSON extraction ───────────────────────────────────────


class TestExtractJSONObjectHappyPath:
    """The existing happy paths must keep working unchanged."""

    def test_pure_json(self) -> None:
        text = '{"intent": "article_lookup", "entities": ["Art. 13"]}'
        parsed = _extract_json_object(text)
        assert parsed == {"intent": "article_lookup", "entities": ["Art. 13"]}

    def test_full_response_fenced_with_json_tag(self) -> None:
        text = '```json\n{"intent": "article_lookup"}\n```'
        parsed = _extract_json_object(text)
        assert parsed == {"intent": "article_lookup"}

    def test_full_response_fenced_no_lang_tag(self) -> None:
        text = '```\n{"intent": "article_lookup"}\n```'
        parsed = _extract_json_object(text)
        assert parsed == {"intent": "article_lookup"}


class TestExtractJSONObjectSonnetBehaviour:
    """The new behaviour that closes the simple-question ref-misses."""

    def test_prose_before_fenced_json(self) -> None:
        text = (
            "Here is the parsed intent:\n\n"
            "```json\n"
            '{"intent": "article_lookup", "entities": ["Art. 13"]}\n'
            "```"
        )
        parsed = _extract_json_object(text)
        assert parsed is not None
        assert parsed["intent"] == "article_lookup"

    def test_prose_after_fenced_json(self) -> None:
        text = (
            "```json\n"
            '{"intent": "obligation_check", "entities": ["Art. 26"]}\n'
            "```\n\n"
            "Hope that helps!"
        )
        parsed = _extract_json_object(text)
        assert parsed is not None
        assert parsed["intent"] == "obligation_check"

    def test_prose_both_sides(self) -> None:
        text = (
            "Sure — here's the breakdown:\n\n"
            "```JSON\n"
            '{"intent": "gap_analysis", "entities": []}\n'
            "```\n\n"
            "Let me know if you need anything else."
        )
        parsed = _extract_json_object(text)
        assert parsed == {"intent": "gap_analysis", "entities": []}

    def test_multiple_fenced_blocks_picks_first_parsable(self) -> None:
        # Sonnet occasionally emits a second fenced block with prose to
        # explain the first. Picking the first parsable hit is correct.
        text = (
            "```json\n"
            '{"intent": "article_lookup", "entities": ["Art. 9"]}\n'
            "```\n"
            "Some explanation in another fenced block:\n"
            "```\n"
            "not parsable as json — just explanatory text\n"
            "```"
        )
        parsed = _extract_json_object(text)
        assert parsed is not None
        assert parsed["intent"] == "article_lookup"
        assert "Art. 9" in parsed["entities"]

    def test_brace_span_when_no_fences(self) -> None:
        text = (
            "I'll parse this as: {\"intent\": \"general_compliance\", "
            "\"entities\": [\"Art. 5\"]} based on the question."
        )
        parsed = _extract_json_object(text)
        assert parsed is not None
        assert parsed["intent"] == "general_compliance"
        assert "Art. 5" in parsed["entities"]

    def test_trailing_comma_tolerated(self) -> None:
        text = '{"intent": "article_lookup", "entities": ["Art. 13"],}'
        parsed = _extract_json_object(text)
        assert parsed == {"intent": "article_lookup", "entities": ["Art. 13"]}

    def test_fenced_with_jsonc_tag(self) -> None:
        text = '```jsonc\n{"intent": "article_lookup"}\n```'
        parsed = _extract_json_object(text)
        assert parsed == {"intent": "article_lookup"}

    def test_fenced_with_json5_tag(self) -> None:
        text = '```json5\n{"intent": "article_lookup"}\n```'
        parsed = _extract_json_object(text)
        assert parsed == {"intent": "article_lookup"}

    def test_nested_object_greedy_match(self) -> None:
        text = (
            '{"intent": "obligation_check", "entities": ["Art. 26"], '
            '"keywords": ["deployer", "obligations"], '
            '"metadata": {"confidence": 0.85}}'
        )
        parsed = _extract_json_object(text)
        assert parsed is not None
        assert parsed["metadata"]["confidence"] == 0.85


class TestExtractJSONObjectFailureModes:
    """Failure paths return None — caller raises so deterministic fallback fires."""

    def test_empty_string(self) -> None:
        assert _extract_json_object("") is None

    def test_pure_prose(self) -> None:
        assert _extract_json_object("I cannot parse this question.") is None

    def test_malformed_braces(self) -> None:
        # Sonnet rarely emits `{intent: "..."}` (no quotes around keys) —
        # we don't try to JSON5-parse, we just fall through.
        assert _extract_json_object("{intent: article_lookup}") is None

    def test_array_at_top_level_returns_none(self) -> None:
        # The helper returns dicts only (the caller expects a JSON
        # object). An array response is treated as unparseable.
        assert _extract_json_object('["a", "b", "c"]') is None


class TestExtractJSONObjectHardeningRound6:
    """Round-6 hardening — pin the load-bearing failure modes the
    previous greedy/non-greedy fallback silently mishandled."""

    def test_balanced_brace_skips_stray_placeholder(self) -> None:
        # The original greedy regex spans first ``{`` to last ``}``,
        # which fails to parse and falls through to non-greedy that
        # picks the stray placeholder. The balanced-brace walker
        # collects BOTH spans and picks the parsable one.
        text = (
            'Note: format is {placeholder} like so. '
            'Result: {"intent": "article_lookup", "entities": ["Art. 13"]}'
        )
        parsed = _extract_json_object(text)
        assert parsed is not None
        assert parsed["intent"] == "article_lookup"
        assert "Art. 13" in parsed["entities"]

    def test_multiple_balanced_spans_picks_query_schema_match(self) -> None:
        # Sonnet sometimes ships an example {...} BEFORE the real
        # answer. The scorer picks the dict with the most query-schema
        # keys, not just the first balanced span.
        text = (
            'Here is an example: {"example": "this is just a placeholder"}.\n'
            'Actual parse: {"intent": "obligation_check", '
            '"entities": ["Art. 26"], "risk_context": "high", '
            '"dimension_hint": "deployer_obligations", "keywords": []}'
        )
        parsed = _extract_json_object(text)
        assert parsed is not None
        assert parsed["intent"] == "obligation_check"
        assert "Art. 26" in parsed["entities"]

    def test_multiple_fenced_blocks_skips_unparsable_first(self) -> None:
        # First fence is explanatory prose (not parseable JSON); second
        # fence is the real JSON. The scorer must skip the first and
        # pick the second.
        text = (
            "```\n"
            "not parsable as json — explanation block first\n"
            "```\n"
            "```json\n"
            '{"intent": "article_lookup", "entities": ["Art. 26"]}\n'
            "```"
        )
        parsed = _extract_json_object(text)
        assert parsed is not None
        assert parsed["intent"] == "article_lookup"
        assert "Art. 26" in parsed["entities"]

    def test_multiple_fenced_blocks_picks_query_schema_match(self) -> None:
        # Both fences parse, but the first is an example. Picker
        # prefers the one with more query-schema keys.
        text = (
            "Here is an example format I might use:\n"
            "```json\n"
            '{"foo": "bar"}\n'
            "```\n"
            "And the actual answer:\n"
            "```json\n"
            '{"intent": "gap_analysis", "entities": ["Art. 9"], '
            '"risk_context": "high", "dimension_hint": "risk_mgmt", "keywords": []}\n'
            "```"
        )
        parsed = _extract_json_object(text)
        assert parsed is not None
        assert parsed["intent"] == "gap_analysis"
