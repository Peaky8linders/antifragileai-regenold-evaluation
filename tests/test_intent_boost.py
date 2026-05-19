"""R66-E Phase 2b — HippoRAG-style intent confidence boost tests.

Validates the ``boost_for_intent`` helper in :mod:`app.routes.regenold`:

* Confidence >= 0.85 + anchor in candidates → promoted to position 0.
* Confidence >= 0.85 + anchor absent → injected at position 0.
* Confidence < 0.85 → no-op.
* Empty / None intent → no-op.
* Unknown anchor (not in ARTICLE_EXISTENCE) → no-op.
* Never empties the list, never raises.
* ``max_budget`` truncates injected lists but never the promotion path.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.routes.regenold import boost_for_intent


@dataclass
class _FakeIntent:
    """Stand-in for :class:`app.llm.intent_classifier.IntentResult`.

    The helper reads ``primary_anchor`` + ``confidence`` only, so the
    stand-in carries just those two fields.
    """

    intent: str = "definition"
    primary_anchor: str = "Art. 13"
    alternate_anchors: tuple[str, ...] = ()
    confidence: float = 0.95


class TestBoostHighConfidencePromotion:
    """High-confidence + anchor present → promote to position 0."""

    def test_promotes_to_position_zero(self):
        cands = ["Article 99", "Article 13", "Article 5"]
        intent = _FakeIntent(primary_anchor="Art. 13", confidence=0.95)
        out = boost_for_intent(cands, intent)
        assert out[0] == "Article 13"
        assert out == ["Article 13", "Article 99", "Article 5"]

    def test_no_op_when_already_at_zero(self):
        cands = ["Article 13", "Article 99"]
        intent = _FakeIntent(primary_anchor="Art. 13", confidence=0.95)
        out = boost_for_intent(cands, intent)
        # Already-at-zero: should be byte-identical (no churn).
        assert out == ["Article 13", "Article 99"]

    def test_preserves_remaining_order(self):
        cands = ["Article 5", "Article 99", "Article 27", "Article 13"]
        intent = _FakeIntent(primary_anchor="Art. 13", confidence=0.9)
        out = boost_for_intent(cands, intent)
        assert out == ["Article 13", "Article 5", "Article 99", "Article 27"]


class TestBoostHighConfidenceInjection:
    """High-confidence + anchor absent → inject at position 0."""

    def test_injects_at_position_zero(self):
        cands = ["Article 99", "Article 5"]
        intent = _FakeIntent(primary_anchor="Art. 13", confidence=0.95)
        out = boost_for_intent(cands, intent)
        assert out[0] == "Article 13"
        assert out == ["Article 13", "Article 99", "Article 5"]

    def test_injection_respects_max_budget(self):
        """When max_budget caps the list, drop the LAST candidate."""
        cands = ["Article 99", "Article 5", "Article 27"]
        intent = _FakeIntent(primary_anchor="Art. 13", confidence=0.95)
        out = boost_for_intent(cands, intent, max_budget=3)
        assert len(out) == 3
        assert out[0] == "Article 13"
        # The last candidate is dropped to make room — Article 27 falls off.
        assert "Article 27" not in out

    def test_injection_no_budget_grows_list(self):
        """No max_budget → list grows by 1 on injection."""
        cands = ["Article 99", "Article 5"]
        intent = _FakeIntent(primary_anchor="Art. 13", confidence=0.95)
        out = boost_for_intent(cands, intent)
        assert len(out) == 3
        assert out == ["Article 13", "Article 99", "Article 5"]


class TestBoostLowConfidence:
    """Below the confidence floor → no-op."""

    def test_low_confidence_no_op(self):
        cands = ["Article 99", "Article 5"]
        intent = _FakeIntent(primary_anchor="Art. 13", confidence=0.5)
        out = boost_for_intent(cands, intent)
        assert out == ["Article 99", "Article 5"]

    def test_exactly_at_threshold_fires(self):
        cands = ["Article 99", "Article 13"]
        intent = _FakeIntent(primary_anchor="Art. 13", confidence=0.85)
        out = boost_for_intent(cands, intent)
        # 0.85 == min_confidence; should fire (>=).
        assert out[0] == "Article 13"

    def test_just_below_threshold_no_op(self):
        cands = ["Article 99", "Article 13"]
        intent = _FakeIntent(primary_anchor="Art. 13", confidence=0.849)
        out = boost_for_intent(cands, intent)
        # Below threshold — no promotion.
        assert out == ["Article 99", "Article 13"]


class TestBoostEdgeCases:
    """Defensive: never raise, never empty, never inject phantoms."""

    def test_none_intent_no_op(self):
        cands = ["Article 99", "Article 5"]
        out = boost_for_intent(cands, None)
        assert out == ["Article 99", "Article 5"]

    def test_empty_candidates_no_op(self):
        # Never inject onto an empty list — that would invent a citation
        # without the route's empty-candidates floor.
        intent = _FakeIntent(primary_anchor="Art. 13", confidence=0.95)
        out = boost_for_intent([], intent)
        assert out == []

    def test_empty_primary_anchor_no_op(self):
        cands = ["Article 99"]
        intent = _FakeIntent(primary_anchor="", confidence=0.95)
        out = boost_for_intent(cands, intent)
        assert out == ["Article 99"]

    def test_unknown_anchor_no_op(self):
        """Phantom anchor (not in ARTICLE_EXISTENCE) → no-op."""
        cands = ["Article 99"]
        intent = _FakeIntent(primary_anchor="Art. 999", confidence=0.95)
        out = boost_for_intent(cands, intent)
        assert out == ["Article 99"]

    def test_annex_anchor_promotion(self):
        """Annex anchors are valid and promoted."""
        cands = ["Article 99", "Annex IV"]
        intent = _FakeIntent(primary_anchor="Annex IV", confidence=0.95)
        out = boost_for_intent(cands, intent)
        assert out[0] == "Annex IV"

    def test_custom_min_confidence_disables(self):
        """Operator can disable by passing 1.01 as the floor."""
        cands = ["Article 99", "Article 13"]
        intent = _FakeIntent(primary_anchor="Art. 13", confidence=0.99)
        out = boost_for_intent(cands, intent, min_confidence=1.01)
        # 0.99 < 1.01 — no-op.
        assert out == ["Article 99", "Article 13"]


class TestBoostFailSoft:
    """The helper must never raise."""

    def test_intent_missing_attrs_no_op(self):
        """Object with no ``primary_anchor`` / ``confidence`` → no-op,
        no exception."""
        class _Bad:
            pass
        cands = ["Article 99"]
        out = boost_for_intent(cands, _Bad())
        # Default getattr returns "" / 0.0, so no fire — clean no-op.
        assert out == ["Article 99"]

    def test_non_string_anchor_no_op(self):
        """If ``primary_anchor`` is not a string, helper handles gracefully."""
        class _Weird:
            primary_anchor = 13  # int, not str
            confidence = 0.95
        cands = ["Article 99"]
        out = boost_for_intent(cands, _Weird())
        # str(13).strip() == "13"; not in ARTICLE_EXISTENCE; no-op.
        assert out == ["Article 99"]
