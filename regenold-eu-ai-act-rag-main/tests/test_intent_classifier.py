"""Tests for the intent classifier — wrapper mocked, no network.

The classifier MUST be a no-op when the wrapper is unconfigured or
unreachable (that's the production safety contract — the engine falls
through to the deterministic path on any failure). These tests pin
that invariant and exercise the JSON-parsing, caching, and
circuit-breaker paths.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from app.llm import intent_classifier as ic
from app.llm.openai_wrapper_provider import OpenAIWrapperResponse


@pytest.fixture(autouse=True)
def _reset() -> None:
    """Wipe cache + breaker between tests."""
    ic._reset_for_tests()
    yield
    ic._reset_for_tests()


# ── Disabled paths ───────────────────────────────────────────────────────────


def test_classifier_returns_none_when_wrapper_disabled(monkeypatch) -> None:
    """Wrapper explicitly disabled -> instant None."""
    import app.llm.intent_classifier
    monkeypatch.setattr(app.llm.intent_classifier, "is_openai_wrapper_enabled", lambda: False)
    assert not ic.is_intent_enabled()
    assert ic.classify_intent("What does Art. 13 require?") is None


def test_classifier_returns_none_on_empty_question() -> None:
    """Empty input short-circuits without touching the wrapper."""
    assert ic.classify_intent("") is None
    assert ic.classify_intent("   ") is None


def test_classifier_returns_none_on_wrapper_error(monkeypatch) -> None:
    """Wrapper error → classifier returns None (engine falls through)."""
    monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    class FakeProvider:
        def complete(self, _req):
            return OpenAIWrapperResponse(
                error="network_error: connection refused",
                model="claude-haiku-4-5",
                elapsed_ms=42,
            )

    with patch.object(ic, "get_openai_wrapper_provider", return_value=FakeProvider()):
        assert ic.classify_intent("What's the max penalty?") is None


def test_classifier_returns_none_on_not_logged_in(monkeypatch) -> None:
    """Wrapper sentinel ``Not logged in`` already maps to ``error`` in
    the provider — classifier path treats it as a failure.
    """
    monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")

    class FakeProvider:
        def complete(self, _req):
            return OpenAIWrapperResponse(
                error="wrapper_not_logged_in: Please run /login",
                model="claude-haiku-4-5",
                elapsed_ms=10,
            )

    with patch.object(ic, "get_openai_wrapper_provider", return_value=FakeProvider()):
        assert ic.classify_intent("Test") is None


# ── Happy path ───────────────────────────────────────────────────────────────


def test_classifier_parses_valid_json_response(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")

    class FakeProvider:
        def complete(self, _req):
            return OpenAIWrapperResponse(
                text=(
                    '{"intent": "penalty_inquiry", "primary_anchor": "Art. 99", '
                    '"alternate_anchors": [], "confidence": 0.95}'
                ),
                model="claude-haiku-4-5",
                elapsed_ms=180,
            )

    with patch.object(ic, "get_openai_wrapper_provider", return_value=FakeProvider()):
        result = ic.classify_intent("What's the maximum fine for prohibited AI?")

    assert result is not None
    assert result.intent == "penalty_inquiry"
    assert result.primary_anchor == "Art. 99"
    assert result.confidence == pytest.approx(0.95)
    assert result.cache_hit is False
    assert result.elapsed_ms >= 0  # mock provider may return in 0ms


def test_classifier_handles_prose_preamble(monkeypatch) -> None:
    """Haiku occasionally prefixes the JSON with ``Here is the JSON:``
    — the parser strips it.
    """
    monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")

    class FakeProvider:
        def complete(self, _req):
            return OpenAIWrapperResponse(
                text=(
                    "Here is the JSON:\n"
                    '{"intent": "fria", "primary_anchor": "Art. 27", '
                    '"alternate_anchors": [], "confidence": 0.88}\n'
                    "Hope that helps!"
                ),
                model="claude-haiku-4-5",
                elapsed_ms=200,
            )

    with patch.object(ic, "get_openai_wrapper_provider", return_value=FakeProvider()):
        result = ic.classify_intent("Who has to do a FRIA?")

    assert result is not None
    assert result.intent == "fria"
    assert result.primary_anchor == "Art. 27"


def test_classifier_injects_default_anchor_when_missing(monkeypatch) -> None:
    """Model returns intent but no primary_anchor → taxonomy default fills in."""
    monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")

    class FakeProvider:
        def complete(self, _req):
            return OpenAIWrapperResponse(
                text='{"intent": "penalty_inquiry", "primary_anchor": "", "alternate_anchors": [], "confidence": 0.8}',
                model="claude-haiku-4-5",
                elapsed_ms=150,
            )

    with patch.object(ic, "get_openai_wrapper_provider", return_value=FakeProvider()):
        result = ic.classify_intent("Max fine?")

    assert result is not None
    assert result.primary_anchor == "Art. 99"  # Filled from INTENT_PRIMARY_ANCHOR


# ── Error / malformed paths ──────────────────────────────────────────────────


def test_classifier_rejects_unknown_intent_label(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")

    class FakeProvider:
        def complete(self, _req):
            return OpenAIWrapperResponse(
                text='{"intent": "rocket_science", "primary_anchor": "Art. 99", "alternate_anchors": [], "confidence": 0.9}',
                model="claude-haiku-4-5",
            )

    with patch.object(ic, "get_openai_wrapper_provider", return_value=FakeProvider()):
        assert ic.classify_intent("Test") is None


def test_classifier_rejects_malformed_anchor(monkeypatch) -> None:
    """``primary_anchor`` must match the strict shape regex; otherwise
    it falls back to the taxonomy default (or empty)."""
    monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")

    class FakeProvider:
        def complete(self, _req):
            return OpenAIWrapperResponse(
                text='{"intent": "fria", "primary_anchor": "Article 27(1)(a)", "alternate_anchors": [], "confidence": 0.9}',
                model="claude-haiku-4-5",
            )

    with patch.object(ic, "get_openai_wrapper_provider", return_value=FakeProvider()):
        result = ic.classify_intent("Test")

    assert result is not None
    # Malformed primary → fall back to taxonomy default for "fria" → Art. 27
    assert result.primary_anchor == "Art. 27"


def test_classifier_handles_unparseable_response(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")

    class FakeProvider:
        def complete(self, _req):
            return OpenAIWrapperResponse(
                text="I don't think I can classify this.",
                model="claude-haiku-4-5",
            )

    with patch.object(ic, "get_openai_wrapper_provider", return_value=FakeProvider()):
        assert ic.classify_intent("Test") is None


# ── Cache ────────────────────────────────────────────────────────────────────


def test_classifier_caches_repeated_questions(monkeypatch) -> None:
    """A repeated question hits the cache; the provider is called once."""
    monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")

    call_count = {"n": 0}

    class FakeProvider:
        def complete(self, _req):
            call_count["n"] += 1
            return OpenAIWrapperResponse(
                text='{"intent": "definition", "primary_anchor": "Art. 3", "alternate_anchors": [], "confidence": 0.92}',
                model="claude-haiku-4-5",
                elapsed_ms=180,
            )

    with patch.object(ic, "get_openai_wrapper_provider", return_value=FakeProvider()):
        first = ic.classify_intent("What is an AI system?")
        second = ic.classify_intent("What is an AI system?")
        third = ic.classify_intent("WHAT IS AN AI SYSTEM?")  # case-insensitive cache key

    assert first is not None and not first.cache_hit
    assert second is not None and second.cache_hit
    assert third is not None and third.cache_hit
    assert call_count["n"] == 1


# ── Circuit breaker ──────────────────────────────────────────────────────────


def test_breaker_opens_after_threshold_failures(monkeypatch) -> None:
    """N consecutive failures → ``is_intent_enabled()`` returns False
    even though the wrapper env is set — protects latency budget.
    """
    monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")

    class FailingProvider:
        def complete(self, _req):
            return OpenAIWrapperResponse(
                error="network_error: refused",
                model="claude-haiku-4-5",
                elapsed_ms=5,
            )

    with patch.object(ic, "get_openai_wrapper_provider", return_value=FailingProvider()):
        # Each unique question triggers a wrapper call.
        for i in range(ic._FAILURE_THRESHOLD):
            assert ic.classify_intent(f"unique question {i}") is None

    # Breaker should now be open — subsequent calls don't even probe.
    assert not ic.is_intent_enabled()
    assert ic.classify_intent("anything else") is None


def test_breaker_resets_on_success(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")

    responses = [
        OpenAIWrapperResponse(error="net err", model="haiku"),
        OpenAIWrapperResponse(error="net err", model="haiku"),
        OpenAIWrapperResponse(
            text='{"intent": "fria", "primary_anchor": "Art. 27", "alternate_anchors": [], "confidence": 0.9}',
            model="haiku",
        ),
    ]

    class StatefulProvider:
        def __init__(self):
            self.idx = 0

        def complete(self, _req):
            resp = responses[self.idx]
            self.idx += 1
            return resp

    with patch.object(ic, "get_openai_wrapper_provider", return_value=StatefulProvider()):
        assert ic.classify_intent("q1") is None  # fail
        assert ic.classify_intent("q2") is None  # fail
        result = ic.classify_intent("q3")        # succeeds → breaker resets
        assert result is not None
        assert ic._BREAKER.failures == 0


# ── R66-D — newly-mapped primary anchors ─────────────────────────────────────


class TestR66DPrimaryAnchorMap:
    """Round 66-D — the three new INTENT_PRIMARY_ANCHOR mappings cover
    intent labels where the LLM previously emitted a clean label but no
    anchor, costing precision in the deterministic fallback. Test that
    each new entry is present + that the default-injection path uses it
    when the model omits ``primary_anchor``.
    """

    def test_taxonomy_includes_three_new_anchors(self) -> None:
        # New mappings must be exactly what the engine downstream relies on.
        assert ic.INTENT_PRIMARY_ANCHOR["risk_classification"] == "Art. 6"
        assert ic.INTENT_PRIMARY_ANCHOR["compliance_checklist"] == "Art. 9"
        assert ic.INTENT_PRIMARY_ANCHOR["comparative"] == "Art. 2"

    def test_every_anchor_resolves_in_article_existence(self) -> None:
        """No primary_anchor in the taxonomy can be a phantom article —
        every default must resolve in :data:`ARTICLE_EXISTENCE` or the
        engine's anchor-narrowing would inject a citation that fails the
        wire-level validator.
        """
        from app.data.article_existence import ARTICLE_EXISTENCE  # noqa: PLC0415
        for label, anchor in ic.INTENT_PRIMARY_ANCHOR.items():
            assert anchor in ARTICLE_EXISTENCE, (
                f"intent={label!r} primary_anchor={anchor!r} not in ARTICLE_EXISTENCE"
            )

    def test_risk_classification_default_injection(self, monkeypatch) -> None:
        """Model returns ``risk_classification`` with empty primary →
        taxonomy default ``Art. 6`` fills in.
        """
        monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")

        class FakeProvider:
            def complete(self, _req):
                return OpenAIWrapperResponse(
                    text=(
                        '{"intent": "risk_classification", "primary_anchor": "", '
                        '"alternate_anchors": [], "confidence": 0.85}'
                    ),
                    model="claude-haiku-4-5",
                )

        with patch.object(ic, "get_openai_wrapper_provider", return_value=FakeProvider()):
            result = ic.classify_intent("Is my CV-screening AI high-risk?")
        assert result is not None
        assert result.intent == "risk_classification"
        assert result.primary_anchor == "Art. 6"

    def test_compliance_checklist_default_injection(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")

        class FakeProvider:
            def complete(self, _req):
                return OpenAIWrapperResponse(
                    text=(
                        '{"intent": "compliance_checklist", "primary_anchor": "", '
                        '"alternate_anchors": [], "confidence": 0.75}'
                    ),
                    model="claude-haiku-4-5",
                )

        with patch.object(ic, "get_openai_wrapper_provider", return_value=FakeProvider()):
            result = ic.classify_intent("What do I need to do to comply as a provider?")
        assert result is not None
        assert result.primary_anchor == "Art. 9"

    def test_comparative_default_injection(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")

        class FakeProvider:
            def complete(self, _req):
                return OpenAIWrapperResponse(
                    text=(
                        '{"intent": "comparative", "primary_anchor": "", '
                        '"alternate_anchors": [], "confidence": 0.70}'
                    ),
                    model="claude-haiku-4-5",
                )

        with patch.object(ic, "get_openai_wrapper_provider", return_value=FakeProvider()):
            result = ic.classify_intent("AI Act vs GDPR for FRIA?")
        assert result is not None
        assert result.primary_anchor == "Art. 2"

    def test_prohibition_path_keeps_explicit_anchor(self, monkeypatch) -> None:
        """The system prompt now nudges Sonnet/Haiku/Llama toward
        ``primary_anchor=Art. 5`` when the question implies prohibition.
        If the model honours this, the explicit anchor wins over the
        default Art. 6 injection.
        """
        monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")

        class FakeProvider:
            def complete(self, _req):
                return OpenAIWrapperResponse(
                    text=(
                        '{"intent": "risk_classification", "primary_anchor": "Art. 5", '
                        '"alternate_anchors": ["Art. 99"], "confidence": 0.92}'
                    ),
                    model="claude-haiku-4-5",
                )

        with patch.object(ic, "get_openai_wrapper_provider", return_value=FakeProvider()):
            result = ic.classify_intent("Is emotion-recognition in workplaces prohibited?")
        assert result is not None
        assert result.intent == "risk_classification"
        # Explicit Art. 5 from the model is preserved — NOT overwritten by
        # the Art. 6 taxonomy default.
        assert result.primary_anchor == "Art. 5"
        assert "Art. 99" in result.alternate_anchors


class TestIntentTaxonomyValidation:
    """Regression guard for the reviewed intent-classifier extension bundle.

    The incoming bundle proposed a broad article/annex label expansion,
    including several legally-wrong role/article anchors. The production
    classifier stays deliberately coarse; these tests pin the fail-fast
    invariants that make future taxonomy drift loud.
    """

    def test_curated_taxonomy_does_not_import_unreviewed_expansion_labels(self) -> None:
        rejected_labels = {
            "deployer_obligations",      # deployer duties are Art. 26, not Art. 24
            "distributor_obligations",   # distributor duties are Art. 24, not Art. 28
            "registration_obligations",  # high-risk registration is Art. 49/71, not Art. 22
            "post_market_monitoring",    # post-market monitoring is Art. 72, not Art. 21
            "conformity_assessment",     # principal conformity route is Art. 43, not Art. 19
            "ce_marking",                # CE marking is Art. 48, not Art. 20
        }
        assert rejected_labels.isdisjoint(ic.INTENT_LABELS)
        assert rejected_labels.isdisjoint(ic.INTENT_PRIMARY_ANCHOR)

    def test_validate_intent_taxonomy_rejects_anchor_for_unknown_label(self, monkeypatch) -> None:
        monkeypatch.setattr(
            ic,
            "INTENT_PRIMARY_ANCHOR",
            {**ic.INTENT_PRIMARY_ANCHOR, "deployer_obligations": "Art. 26"},
        )
        with pytest.raises(RuntimeError, match="labels not present"):
            ic._validate_intent_taxonomy()

    def test_validate_intent_taxonomy_rejects_phantom_reference(self, monkeypatch) -> None:
        monkeypatch.setattr(
            ic,
            "INTENT_PRIMARY_ANCHOR",
            {**ic.INTENT_PRIMARY_ANCHOR, "definition": "Art. 114"},
        )
        with pytest.raises(RuntimeError, match="invalid EU AI Act refs"):
            ic._validate_intent_taxonomy()
