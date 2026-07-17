"""R281 — reference-minimality rule: gate, content, and cache-key contract.

Context (measured, see graph_rag_prompts._REF_MINIMALITY_RULE's banner):
97.2% of our excess references are entirely NON-GOLD distinct articles, the
answer prose describes 95% of them (so every prose-driven pruner is a no-op),
and the cause is rule 10's one-directional "describe everything you cite" with
no converse minimality constraint. These tests pin the fix's contract.
"""
from __future__ import annotations

import pytest

from app.data.graph_rag_prompts import (
    ANSWER_GENERATE_SYSTEM,
    MINIMAL_COMPOSER_SYSTEM,
    ref_minimality_enabled,
    resolve_answer_system,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both R277/R281 prompt flags default OFF for every test in this module."""
    monkeypatch.delenv("REGENOLD_REF_MINIMALITY", raising=False)
    monkeypatch.delenv("REGENOLD_MINIMAL_COMPOSER", raising=False)


class TestGateDefaultOff:
    """Default OFF ⇒ production + davidath byte-identical until the A/B decides."""

    def test_disabled_by_default(self) -> None:
        assert ref_minimality_enabled() is False

    def test_default_returns_base_prompt_byte_identical(self) -> None:
        # The load-bearing byte-identity guarantee: with the flag unset the
        # Stage-2 system prompt is EXACTLY the accreted prompt, unchanged.
        assert resolve_answer_system() == ANSWER_GENERATE_SYSTEM

    @pytest.mark.parametrize("val", ["1", "true", "TRUE", "yes", "on", " on "])
    def test_truthy_values_enable(
        self, monkeypatch: pytest.MonkeyPatch, val: str
    ) -> None:
        monkeypatch.setenv("REGENOLD_REF_MINIMALITY", val)
        assert ref_minimality_enabled() is True

    @pytest.mark.parametrize("val", ["0", "false", "no", "off", "", "banana"])
    def test_falsy_and_unknown_values_stay_disabled(
        self, monkeypatch: pytest.MonkeyPatch, val: str
    ) -> None:
        monkeypatch.setenv("REGENOLD_REF_MINIMALITY", val)
        assert ref_minimality_enabled() is False

    def test_env_read_is_fresh_per_call(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The in-process two-arm A/B toggles the flag between arms; a cached
        # read would silently make both arms identical (the R263.2 hazard).
        assert resolve_answer_system() == ANSWER_GENERATE_SYSTEM
        monkeypatch.setenv("REGENOLD_REF_MINIMALITY", "1")
        assert resolve_answer_system() != ANSWER_GENERATE_SYSTEM
        monkeypatch.delenv("REGENOLD_REF_MINIMALITY")
        assert resolve_answer_system() == ANSWER_GENERATE_SYSTEM


class TestRuleContent:
    def test_enabled_appends_rule_and_preserves_base_verbatim(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("REGENOLD_REF_MINIMALITY", "1")
        out = resolve_answer_system()
        # APPEND, never splice — the base prompt survives byte-for-byte and the
        # new rule lands last (highest recency attention).
        assert out.startswith(ANSWER_GENERATE_SYSTEM)
        assert len(out) > len(ANSWER_GENERATE_SYSTEM)

    def test_rule_states_the_competition_requirement(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("REGENOLD_REF_MINIMALITY", "1")
        added = resolve_answer_system()[len(ANSWER_GENERATE_SYSTEM):].lower()
        # The rules PDF's own words — the whole justification for this rule.
        assert "minimal set" in added

    def test_rule_names_the_measured_over_cited_clusters(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("REGENOLD_REF_MINIMALITY", "1")
        added = resolve_answer_system()[len(ANSWER_GENERATE_SYSTEM):]
        # The R281 apportionment named these as the dominant non-gold mass:
        # the classification apparatus + the high-risk requirement chain.
        assert "Article 6" in added
        assert "Annex III" in added
        assert "Articles 9 to 15" in added

    def test_rule_reconciles_with_rule_10_rather_than_contradicting_it(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("REGENOLD_REF_MINIMALITY", "1")
        added = resolve_answer_system()[len(ANSWER_GENERATE_SYSTEM):]
        # Rule 10 (describe-everything-you-cite) must be explicitly scoped, not
        # silently contradicted — a conflicting pair is the documented R277
        # failure mode (rule CONFLICT, not rule count, is what degrades output).
        assert "rule 10" in added.lower()

    def test_rule_is_punctuation_clean(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("REGENOLD_REF_MINIMALITY", "1")
        added = resolve_answer_system()[len(ANSWER_GENERATE_SYSTEM):]
        # R108: the prompt must not MODEL forbidden punctuation to the model.
        assert "—" not in added
        assert "–" not in added
        assert "..." not in added
        assert "…" not in added


class TestMinimalComposerPrecedence:
    def test_minimal_composer_wins_and_is_not_appended_to(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The R277 arm-C composer is a whole-prompt REPLACEMENT whose own rule 3
        # already carries a minimality clause; appending R281 to it would be
        # incoherent. Composer wins outright.
        monkeypatch.setenv("REGENOLD_MINIMAL_COMPOSER", "1")
        monkeypatch.setenv("REGENOLD_REF_MINIMALITY", "1")
        assert resolve_answer_system() == MINIMAL_COMPOSER_SYSTEM


class TestCacheKey:
    """R30/R56/R79/R263.2 — a flag that flips the answer MUST be in the key."""

    def test_flag_changes_the_engine_cache_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.routes.regenold import _engine_cache_key

        monkeypatch.delenv("REGENOLD_REF_MINIMALITY", raising=False)
        off = _engine_cache_key("What must importers do?", None)
        monkeypatch.setenv("REGENOLD_REF_MINIMALITY", "1")
        on = _engine_cache_key("What must importers do?", None)
        assert off != on, (
            "REGENOLD_REF_MINIMALITY flips the Stage-2 answer but is absent "
            "from the engine cache key: a same-process A/B would serve the "
            "baseline arm's cached answer to the branch arm (the R263.2 bug)."
        )

    def test_key_is_stable_for_a_fixed_flag_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.routes.regenold import _engine_cache_key

        monkeypatch.setenv("REGENOLD_REF_MINIMALITY", "1")
        a = _engine_cache_key("What must importers do?", None)
        b = _engine_cache_key("What must importers do?", None)
        assert a == b
