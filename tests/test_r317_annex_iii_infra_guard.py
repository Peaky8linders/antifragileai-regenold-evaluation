"""R317 — Annex III point-2 guard on the R311 gate.

"safety component" appears VERBATIM in both high-risk routes:
  * Article 6(1)(a) — the Annex I product route;
  * Annex III point 2 — "AI systems intended to be used as safety components
    in the management and operation of critical digital infrastructure, road
    traffic, or in the supply of water, gas, heating or electricity".

R311's gate reuses the ``annex_i_safety_component`` topic, whose third pattern
is a bare ``\\bsafety\\s+component``, so it fired on the Annex III route and
then dropped ``Annex III`` — the governing reference there.

Every question below is used VERBATIM. R305 shipped a detector that returned
False on its own target question because its test asserted on a truncated copy.
"""

from __future__ import annotations

import pytest

from app.routes.regenold import (
    _annex_i_product_route_question,
    _apply_annex_i_route_exclusivity,
    _r317_is_annex_iii_critical_infrastructure,
)

# The verbatim question from the adversarial counterexample (probe row
# paper_st_v4:st_v4_006, gold = Article 6 + Annex III).
Q_GRID = (
    "An AI system is used as a safety component to manage the supply of "
    "electricity on a national grid. How is it classified and under which "
    "article?"
)
Q_WATER = (
    "Our AI acts as a safety component in the management of the municipal "
    "water supply. Is it high-risk?"
)
Q_TRAFFIC = (
    "Is an AI system used as a safety component for road traffic management "
    "high-risk?"
)
# Genuine Annex I product-route asks — R311 MUST still fire on these.
Q_MACHINERY = (
    "Our AI is a safety component of machinery placed on the market under "
    "Union harmonisation legislation. Is it high-risk?"
)
Q_MEDICAL = (
    "Is an AI system that acts as a safety component of a medical device "
    "high-risk?"
)


class TestCriticalInfrastructureDetection:
    @pytest.mark.parametrize("q", [Q_GRID, Q_WATER, Q_TRAFFIC])
    def test_annex_iii_point_2_objects_detected(self, q: str) -> None:
        assert _r317_is_annex_iii_critical_infrastructure(q) is True

    @pytest.mark.parametrize("q", [Q_MACHINERY, Q_MEDICAL])
    def test_annex_i_product_markers_veto_the_guard(self, q: str) -> None:
        """A mixed question keeps the Annex I reading, so R311 still fires."""
        assert _r317_is_annex_iii_critical_infrastructure(q) is False

    def test_empty_is_false(self) -> None:
        assert _r317_is_annex_iii_critical_infrastructure("") is False

    @pytest.mark.parametrize(
        "word",
        [
            # The trailing-\b-after-a-truncated-stem bug: a `\b(machiner)\b`
            # guard is DEAD for every natural inflection. Each of these must
            # register as an Annex I product marker.
            "machinery",
            "machines",
            "toys",
            "medical devices",
            "notified bodies",
            "CE marking",
            "gas appliances",
            "explosive atmospheres",
            "manufacturing",
            "lifts",
            "aircraft",
        ],
    )
    def test_product_markers_match_natural_inflections(self, word: str) -> None:
        q = (
            f"Our AI is a safety component in {word} regulating the municipal "
            "water supply. Is it high-risk?"
        )
        assert _r317_is_annex_iii_critical_infrastructure(q) is False


class TestGateNarrowing:
    @pytest.mark.parametrize("q", [Q_GRID, Q_WATER, Q_TRAFFIC])
    def test_gate_refuses_annex_iii_route(self, q: str) -> None:
        assert _annex_i_product_route_question(q) is False

    @pytest.mark.parametrize("q", [Q_MACHINERY, Q_MEDICAL])
    def test_gate_still_fires_on_genuine_annex_i(self, q: str) -> None:
        assert _annex_i_product_route_question(q) is True

    def test_scans_only_the_live_turn(self) -> None:
        """R71 — a prior turn's grid talk must not gate the live product ask."""
        flat = (
            "Conversation so far:\nuser: Tell me about the national grid.\n"
            f"Latest question:\n{Q_MEDICAL}"
        )
        assert _annex_i_product_route_question(flat) is True


class TestGoldIsPreserved:
    @pytest.mark.parametrize("q", [Q_GRID, Q_WATER, Q_TRAFFIC])
    def test_annex_iii_survives_r311(self, q: str) -> None:
        refs = ["Article 6", "Annex III", "Article 26"]
        assert "Annex III" in _apply_annex_i_route_exclusivity(list(refs), q)

    def test_r311_win_is_untouched_on_genuine_annex_i(self) -> None:
        """The measured R311 MedTech win must survive the narrowing."""
        refs = ["Article 6", "Annex III", "Annex I"]
        out = _apply_annex_i_route_exclusivity(list(refs), Q_MEDICAL)
        assert out == ["Article 6", "Annex I"]

    def test_guard_only_ever_prevents_a_removal(self) -> None:
        """It can never itself drop a reference — recall is the guard."""
        refs = ["Article 6", "Annex III", "Article 26", "Annex I"]
        assert set(_apply_annex_i_route_exclusivity(list(refs), Q_GRID)) >= set(refs)


class TestEnvGate:
    def test_default_is_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("REGENOLD_ANNEX_III_INFRA_GUARD", raising=False)
        assert _annex_i_product_route_question(Q_GRID) is False

    def test_off_switch_restores_pre_r317_behaviour(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("REGENOLD_ANNEX_III_INFRA_GUARD", "0")
        assert _annex_i_product_route_question(Q_GRID) is True
        refs = ["Article 6", "Annex III", "Article 26"]
        assert "Annex III" not in _apply_annex_i_route_exclusivity(list(refs), Q_GRID)


class TestTierExclusivityDefaultOff:
    """R317 tier exclusivity drops 67 davidath GOLD refs -> must default OFF."""

    def test_default_is_off(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.routes.regenold import _tier_exclusivity_enabled

        monkeypatch.delenv("REGENOLD_TIER_EXCLUSIVITY", raising=False)
        assert _tier_exclusivity_enabled() is False

    def test_can_be_re_enabled_for_a_future_ab(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.routes.regenold import _tier_exclusivity_enabled

        monkeypatch.setenv("REGENOLD_TIER_EXCLUSIVITY", "1")
        assert _tier_exclusivity_enabled() is True

    def test_pass_is_a_noop_by_default_on_a_prohibited_verdict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The exact davidath sc_002 shape must keep its Chapter III gold."""
        from app.routes.regenold import _apply_tier_exclusivity

        monkeypatch.delenv("REGENOLD_TIER_EXCLUSIVITY", raising=False)
        refs = ["Article 5", "Article 9", "Article 10", "Article 16", "Article 49"]
        answer = (
            "This system is classified as a prohibited AI practice under "
            "Article 5 and may not be placed on the market or put into service."
        )
        assert _apply_tier_exclusivity(list(refs), "is this high-risk?", answer) == refs
