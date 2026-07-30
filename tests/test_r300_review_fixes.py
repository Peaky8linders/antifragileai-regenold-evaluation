"""R300 — regression tests for the deep-review fixes.

Two defects found reviewing the two untagged 2026-07-30 "truncation" commits
(`8eb34e4`, `757f0cb`) plus the R299 range:

1.  A hardcoded model-name rewrite buried in the wrapper transport layer with
    no env gate, no log line, and no mention in its commit message. It
    silently reverted R292's shipped Opus 5 Stage-2 AND made the
    `?include_reasoning=true` trace report a model that was never sent.
2.  The R299 completeness verifier emitted a supplement that conflated the
    sub-points of TWO different articles into one undifferentiated list,
    asserting points that the leading article does not have (Article 16 stops
    at (l); the blob implied an (m)) — a confidently-wrong legal claim, the
    worst defect class per CLAUDE.md hard rule #4. Its labels were also a
    keyword bag ("draw declaration conformity") rather than regulatory prose.
"""

from __future__ import annotations

import pytest

from app.engines.completeness_verifier import (
    _extract_subpoint_label,
    verify_and_enrich_enumerated_completeness,
)
from app.llm.openai_wrapper_provider import resolve_wrapper_model


# --------------------------------------------------------------------------
# 1. Wrapper model alias — env-gated, honest, non-Opus untouched
# --------------------------------------------------------------------------
class TestWrapperModelAlias:
    def test_default_preserves_pre_r300_behaviour(self, monkeypatch):
        """Default ON => the 757f0cb rewrite still applies (zero answer change)."""
        monkeypatch.delenv("REGENOLD_WRAPPER_MODEL_ALIAS", raising=False)
        for requested in (
            "claude-opus-5",
            "claude-opus-4-8",
            "opus",
            "claude-5-opus",
            "opus-5",
            "claude-opus-5.0",
        ):
            assert resolve_wrapper_model(requested) == "claude-opus-4-6"

    def test_env_gate_off_sends_requested_model_verbatim(self, monkeypatch):
        """`=0` is the arm a future live ab_judge A/B measures."""
        monkeypatch.setenv("REGENOLD_WRAPPER_MODEL_ALIAS", "0")
        assert resolve_wrapper_model("claude-opus-5") == "claude-opus-5"
        assert resolve_wrapper_model("claude-opus-4-8") == "claude-opus-4-8"

    @pytest.mark.parametrize(
        "model",
        [
            "claude-sonnet-5",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
        ],
    )
    def test_non_opus_models_are_never_rewritten(self, monkeypatch, model):
        """The alias must not touch the Groq / Sonnet / Haiku paths."""
        monkeypatch.delenv("REGENOLD_WRAPPER_MODEL_ALIAS", raising=False)
        assert resolve_wrapper_model(model) == model

    def test_identity_and_empty_are_safe(self, monkeypatch):
        monkeypatch.delenv("REGENOLD_WRAPPER_MODEL_ALIAS", raising=False)
        assert resolve_wrapper_model("claude-opus-4-6") == "claude-opus-4-6"
        assert resolve_wrapper_model("") == ""
        assert resolve_wrapper_model("  claude-opus-5  ") == "claude-opus-4-6"

    def test_complete_routes_through_the_gate_not_an_inline_literal(self):
        """`complete()` must call the resolver.

        The 757f0cb defect was an un-gated `if model in (...): model =
        "claude-opus-4-6"` inline in `complete()`. Pin that it is gone, so a
        future edit cannot silently re-introduce an ungated rewrite that the
        env switch and the reasoning trace would both be blind to.
        """
        import inspect

        from app.llm.openai_wrapper_provider import _OpenAIWrapperProvider

        src = inspect.getsource(_OpenAIWrapperProvider.complete)
        assert "_resolve_wrapper_model" in src or "resolve_wrapper_model" in src
        assert '"claude-opus-4-6"' not in src, (
            "hardcoded model literal back inside complete() — it must go "
            "through the env-gated, logged resolver"
        )


# --------------------------------------------------------------------------
# 2. Completeness verifier — per-article attribution + grammatical labels
# --------------------------------------------------------------------------
_Q = "List every obligation that Article 16 places on a provider of a high-risk AI system."

# The real production answer (uncached live probe, 2026-07-30) that cites BOTH
# Article 16 and Article 17 and therefore triggered the cross-article conflation.
_ANSWER_CITING_16_AND_17 = (
    "Article 16 requires providers of high-risk AI systems to fulfil all of the "
    "following obligations. They must ensure the system complies with the "
    "requirements set out in Chapter III, Section 2 and bears the provider's name "
    "or registered trade mark. They must put in place a quality management system "
    "(Article 17)."
)


class TestCompletenessVerifierAttribution:
    def test_supplement_attributes_points_to_their_own_article(self, monkeypatch):
        monkeypatch.delenv("REGENOLD_COMPLETENESS_VERIFIER", raising=False)
        out = verify_and_enrich_enumerated_completeness(_Q, _ANSWER_CITING_16_AND_17, None)
        assert out != _ANSWER_CITING_16_AND_17, "verifier should fire on this shape"
        # Each cited article names ITSELF before listing its points.
        assert "Article 16 also requires" in out
        assert "Article 17 also requires" in out
        # The pre-R300 undifferentiated blob form must be gone.
        assert "including points" not in out

    def test_article_16_points_never_claim_a_point_m(self, monkeypatch):
        """Article 16 has points (a)-(l). An (m) in its clause is a legal error."""
        monkeypatch.delenv("REGENOLD_COMPLETENESS_VERIFIER", raising=False)
        out = verify_and_enrich_enumerated_completeness(_Q, _ANSWER_CITING_16_AND_17, None)
        a16 = out.split("Article 16 also requires", 1)[1]
        a16_clause = a16.split("Article 17 also requires", 1)[0]
        assert "(m)" not in a16_clause, (
            "Article 16 has no point (m) — it stops at (l). An (m) here means "
            "Article 17's points leaked into Article 16's list."
        )

    def test_labels_are_prose_not_keyword_salad(self, monkeypatch):
        monkeypatch.delenv("REGENOLD_COMPLETENESS_VERIFIER", raising=False)
        out = verify_and_enrich_enumerated_completeness(_Q, _ANSWER_CITING_16_AND_17, None)
        # Pre-R300 output for these exact points.
        for salad in (
            "draw declaration conformity",
            "keep documentation referred",
            "comply registration referred",
            "take necessary corrective",
        ):
            assert salad not in out, f"keyword-salad label regressed: {salad!r}"

    def test_env_gate_off_is_a_strict_noop(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_COMPLETENESS_VERIFIER", "0")
        out = verify_and_enrich_enumerated_completeness(_Q, _ANSWER_CITING_16_AND_17, None)
        assert out == _ANSWER_CITING_16_AND_17

    def test_non_enumerated_question_is_a_noop(self, monkeypatch):
        monkeypatch.delenv("REGENOLD_COMPLETENESS_VERIFIER", raising=False)
        ans = "Article 16 requires a quality management system."
        assert verify_and_enrich_enumerated_completeness(
            "Is a chatbot high-risk?", ans, None
        ) == ans


class TestSubpointLabelQuality:
    def test_verbatim_opening_clause_is_preserved(self):
        text = "draw up the EU declaration of conformity in accordance with Article 47"
        assert _extract_subpoint_label(text).startswith("draw up the EU declaration")

    def test_label_does_not_end_on_a_dangling_function_word(self):
        long_text = (
            "take the necessary corrective actions and provide information as "
            "required by Article 20 concerning the system placed on the market"
        )
        label = _extract_subpoint_label(long_text)
        assert not label.split()[-1].lower().rstrip(".,;:") in {
            "as",
            "of",
            "the",
            "and",
            "to",
            "in",
            "by",
            "with",
        }, f"dangling function word at end of {label!r}"

    def test_short_subpoint_returned_whole(self):
        assert _extract_subpoint_label("resource management") == "resource management"

    def test_early_comma_does_not_truncate_to_a_stub(self):
        """Article 17(h) opens 'the setting-up, implementation and maintenance…'.

        An unguarded first-comma cut would emit the useless 'the setting-up'.
        """
        text = (
            "the setting-up, implementation and maintenance of a post-market "
            "monitoring system"
        )
        label = _extract_subpoint_label(text)
        assert label != "the setting-up"
        assert "implementation" in label

    def test_empty_input_is_safe(self):
        assert _extract_subpoint_label("") == "requirement"
        assert _extract_subpoint_label("   ") == "requirement"
