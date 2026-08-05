"""R281 — ``adaptive_ref_clamp`` contract + the default-ON flip.

The clamp is the reference-PRECISION win the gold-bearing ``easyhard_ab`` A/B
confirmed (hard split n=37: Ref Strict F1 +0.032, Ref Conciseness +0.067, recall
guard -0.0135, est. Overall +1.17pp; easy offline sim +1.9pp). These tests pin:
  * the default-ON flip (was OFF pending the A/B),
  * the stage2-gate that makes davidath / 276 / OOS byte-identical BY CONSTRUCTION
    (the deterministic bench runs provider=cli → stage2_landed False → no-op),
  * the R142.1-safe behaviour (never adds a ref; question-named heads rescued past
    budget; curated intercepts exempt; floor; fail-soft),
  * the deliberate ABSENCE from the engine cache key (R79 — it re-runs post-cache).
"""
from __future__ import annotations

import pytest

from app.routes.regenold import (
    _CLAMP_FLOOR,
    _adaptive_clamp_enabled,
    _clamp_ref_head,
    _question_named_heads,
    _scenario_clamp_budget,
    adaptive_ref_clamp,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REGENOLD_ADAPTIVE_REF_CLAMP", raising=False)
    monkeypatch.delenv("REGENOLD_REF_CLAMP_SCENARIO_BUDGET", raising=False)


def _clamp(refs, *, budget=3, is_scenario_budget=False, live_question="",
           stage2_landed=True, curated_intercept=False, retrieval_path="neo4j"):
    return adaptive_ref_clamp(
        refs,
        budget=budget,
        is_scenario_budget=is_scenario_budget,
        live_question=live_question,
        stage2_landed=stage2_landed,
        curated_intercept=curated_intercept,
        retrieval_path=retrieval_path,
    )


class TestGateDefaultOn:
    def test_enabled_by_default(self) -> None:
        # R281 flip: OFF -> ON once the gold-bearing A/B confirmed +1.17pp.
        assert _adaptive_clamp_enabled() is True

    @pytest.mark.parametrize("val", ["0", "false", "no", "off", ""])
    def test_env_off_disables(self, monkeypatch: pytest.MonkeyPatch, val: str) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", val)
        assert _adaptive_clamp_enabled() is False
        # And the clamp is a strict no-op when disabled.
        refs = [f"Article {i}" for i in (1, 2, 3, 4, 5, 6, 7)]
        assert _clamp(refs, budget=3) == refs

    @pytest.mark.parametrize("val", ["1", "true", "TRUE", "yes", "on", " on "])
    def test_truthy_values_enable(self, monkeypatch: pytest.MonkeyPatch, val: str) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", val)
        assert _adaptive_clamp_enabled() is True


class TestStage2Gate:
    """The davidath / 276 / OOS byte-identical guarantee lives here."""

    def test_no_op_when_stage2_did_not_land(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
        refs = [f"Article {i}" for i in (5, 6, 9, 10, 11, 13, 15)]
        # provider=cli (no wrapper) => stage2_landed False => clamp inert, whatever
        # the default. This is why flipping the default cannot move davidath.
        assert _clamp(refs, budget=3, stage2_landed=False) == refs


class TestExemptions:
    def test_curated_intercept_exempt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
        refs = [f"Article {i}" for i in (5, 6, 9, 10, 11)]
        assert _clamp(refs, budget=3, curated_intercept=True) == refs

    @pytest.mark.parametrize("path", ["no_match", "verbatim_exact_text"])
    def test_no_match_and_verbatim_exempt(self, monkeypatch: pytest.MonkeyPatch, path: str) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
        refs = [f"Article {i}" for i in (5, 6, 9, 10, 11)]
        assert _clamp(refs, budget=3, retrieval_path=path) == refs


class TestClampBehaviour:
    def test_under_or_at_budget_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
        refs = ["Article 13", "Article 50"]
        assert _clamp(refs, budget=3) == refs

    def test_over_budget_keeps_head(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
        refs = ["Article 6", "Annex III", "Article 9", "Article 10", "Article 11"]
        out = _clamp(refs, budget=3, live_question="What obligations apply?")
        assert out == ["Article 6", "Annex III", "Article 9"]

    def test_question_named_head_rescued_past_budget(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
        # The R142.1 fix: a ref the user explicitly named survives the budget cap.
        refs = ["Article 6", "Article 9", "Article 10", "Article 13", "Article 99"]
        out = _clamp(refs, budget=3, live_question="What does Article 99 penalise?")
        assert out == ["Article 6", "Article 9", "Article 10", "Article 99"]

    def test_subpoint_named_head_rescued(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
        # A sub-point past budget whose HEAD the question names is rescued.
        refs = ["Article 6", "Article 9", "Article 10", "Annex IV.2"]
        out = _clamp(refs, budget=3, live_question="What must Annex IV contain?")
        assert "Annex IV.2" in out and out[:3] == ["Article 6", "Article 9", "Article 10"]

    def test_only_live_turn_named_refs_rescued(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
        # A PRIOR turn naming Article 99 must NOT rescue it (R60.1/R71 doctrine).
        refs = ["Article 6", "Article 9", "Article 10", "Article 99"]
        q = "Earlier we discussed Article 99.\nLatest question:\nWhat about deployers?"
        out = _clamp(refs, budget=3, live_question=q)
        assert "Article 99" not in out
        assert out == ["Article 6", "Article 9", "Article 10"]

    def test_never_adds_a_ref(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
        refs = ["Article 6", "Annex III", "Article 9", "Article 10", "Article 11"]
        out = _clamp(refs, budget=3, live_question="What about Article 27 and Article 43?")
        assert set(out) <= set(refs)  # never invents a ref, even if the question names one

    def test_idempotent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
        refs = ["Article 6", "Annex III", "Article 9", "Article 10", "Article 11", "Article 13"]
        once = _clamp(refs, budget=3, live_question="What about Article 13?")
        twice = _clamp(once, budget=3, live_question="What about Article 13?")
        assert once == twice

    def test_output_never_empty_for_nonempty_input(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
        refs = ["Article 6", "Article 9", "Article 10", "Article 11"]
        out = _clamp(refs, budget=2)
        assert len(out) >= _CLAMP_FLOOR

    def test_fail_soft_returns_input(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
        # Pathological refs (a non-str) must not raise — the route is never broken.
        refs = ["Article 6", None, "Article 9", "Article 10", "Article 11"]  # type: ignore[list-item]
        out = _clamp(refs, budget=3)  # must not raise
        assert isinstance(out, list)


class TestScenarioBudget:
    def test_scenario_budget_overrides_arg(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
        assert _scenario_clamp_budget() == 5  # default
        refs = [f"Article {i}" for i in (6, 9, 10, 11, 13, 15, 26)]  # 7 refs
        # is_scenario_budget True => uses _scenario_clamp_budget() (5), NOT budget (3)
        out = _clamp(refs, budget=3, is_scenario_budget=True, live_question="scenario")
        assert len(out) == 5

    def test_scenario_budget_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
        monkeypatch.setenv("REGENOLD_REF_CLAMP_SCENARIO_BUDGET", "4")
        assert _scenario_clamp_budget() == 4
        refs = [f"Article {i}" for i in (6, 9, 10, 11, 13, 15, 26)]
        out = _clamp(refs, budget=3, is_scenario_budget=True, live_question="scenario")
        assert len(out) == 4


class TestHelpers:
    def test_clamp_ref_head(self) -> None:
        assert _clamp_ref_head("Article 50.1") == "Article 50"
        assert _clamp_ref_head("Annex IV.2.c") == "Annex IV"
        assert _clamp_ref_head("Article 6") == "Article 6"
        assert _clamp_ref_head("gibberish") is None

    def test_question_named_heads_multi_article(self) -> None:
        named = _question_named_heads("What do Articles 13 and 50 require?")
        assert named == {"Article 13", "Article 50"}

    def test_question_named_heads_scopes_to_live_turn(self) -> None:
        q = "We discussed Article 99.\nLatest question:\nWhat about Annex IV?"
        assert _question_named_heads(q) == {"Annex IV"}


class TestCacheKeyDeliberatelyAbsent:
    """R79 — the clamp is route post-processing over the CACHED engine output, so
    it must NOT be in the engine cache key (it re-runs on every cache hit). This is
    the exact INVERSE of REGENOLD_REF_MINIMALITY (a Stage-2 prompt flag, which MUST
    be in the key). Pinning this keeps the shared-cache in-process A/B valid: both
    arms reuse the SAME cached Stage-2 answer so the clamp is the only variable.
    """

    def test_flag_absent_from_engine_cache_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.routes.regenold import _engine_cache_key

        monkeypatch.delenv("REGENOLD_ADAPTIVE_REF_CLAMP", raising=False)
        off = _engine_cache_key("What must importers do?", None)
        monkeypatch.setenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")
        on = _engine_cache_key("What must importers do?", None)
        assert off == on, (
            "REGENOLD_ADAPTIVE_REF_CLAMP is a route post-process (R79) and must "
            "stay OUT of the engine cache key so the shared-cache A/B is valid."
        )
