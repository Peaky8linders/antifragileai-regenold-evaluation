"""Unit and integration tests for AIRO & EU AI Act SOTA ontology models."""
from __future__ import annotations

import pytest

from app.data.article_existence import ARTICLE_EXISTENCE
from app.data.kb_search import top_articles_by_relevance
from app.data.ontology import (
    CONFORMITY_ROUTE_REGISTRY,
    FRIA_REGISTRY,
    GPAI_REGISTRY,
    RISK_CONTROL_REGISTRY,
    RISK_SCENARIO_REGISTRY,
    SERIOUS_INCIDENT_REGISTRY,
    ConformityRoute,
    all_articles_referenced,
    resolve_conformity_path,
)
from app.engines.neo4j_semantic_graph import SemanticGraphEngine, semantic_graph


def _is_valid_ref(ref: str) -> bool:
    if ref in ARTICLE_EXISTENCE:
        return True
    candidate = ref
    while "." in candidate:
        candidate = candidate.rsplit(".", 1)[0].strip()
        if candidate in ARTICLE_EXISTENCE:
            return True
    return False


class TestAiroRiskOntology:
    """Verify AIRO causal risk models, controls, and statutory bindings."""

    def test_risk_scenarios_have_valid_statutory_violations(self) -> None:
        """Every RiskScenario statutory violation must resolve in ARTICLE_EXISTENCE."""
        assert len(RISK_SCENARIO_REGISTRY) >= 8
        for scenario in RISK_SCENARIO_REGISTRY.values():
            assert scenario.statutory_violation, f"{scenario.id} has empty statutory violations"
            for ref in scenario.statutory_violation:
                assert _is_valid_ref(ref), f"Invalid article ref {ref!r} in {scenario.id}"

    def test_risk_scenarios_link_to_existing_controls(self) -> None:
        """Every required_control in a RiskScenario must exist in RISK_CONTROL_REGISTRY."""
        for scenario in RISK_SCENARIO_REGISTRY.values():
            for ctrl_id in scenario.required_controls:
                assert ctrl_id in RISK_CONTROL_REGISTRY, (
                    f"Scenario {scenario.id} points to missing control {ctrl_id!r}"
                )

    def test_risk_controls_have_valid_articles(self) -> None:
        """Every RiskControl article must resolve in ARTICLE_EXISTENCE."""
        assert len(RISK_CONTROL_REGISTRY) >= 9
        for control in RISK_CONTROL_REGISTRY.values():
            for ref in control.articles:
                assert _is_valid_ref(ref), f"Invalid article ref {ref!r} in control {control.id}"


class TestGPAIGovernance:
    """Verify General-Purpose AI model profiles and exemption logic."""

    def test_gpai_registry_contains_standard_and_systemic(self) -> None:
        assert "standard_gpai_proprietary" in GPAI_REGISTRY
        assert "standard_gpai_open_source" in GPAI_REGISTRY
        assert "systemic_gpai_frontier" in GPAI_REGISTRY
        assert "systemic_gpai_open_weights" in GPAI_REGISTRY

    def test_open_source_carve_out_art_53_2(self) -> None:
        """Open-source GPAI is exempt from Annex XI & XII per Art. 53(2)."""
        oss = GPAI_REGISTRY["standard_gpai_open_source"]
        assert oss.is_open_source is True
        assert oss.technical_doc_annex == ""
        assert oss.downstream_info_annex == ""
        assert "Art. 53" in oss.mandatory_obligations

    def test_systemic_gpai_triggers_art_55_and_annex_xiii(self) -> None:
        frontier = GPAI_REGISTRY["systemic_gpai_frontier"]
        assert frontier.has_systemic_risk is True
        assert frontier.training_compute_flops >= 1.0e25
        assert "Art. 55" in frontier.mandatory_obligations
        assert "Annex XIII" in frontier.mandatory_obligations

    def test_open_weights_systemic_gpai_lacks_art_53_2_carveout(self) -> None:
        """Open-source GPAI with systemic risk does not receive Art. 53(2) exemption."""
        open_sys = GPAI_REGISTRY["systemic_gpai_open_weights"]
        assert open_sys.is_open_source is True
        assert open_sys.has_systemic_risk is True
        assert "Art. 53" in open_sys.mandatory_obligations
        assert "Art. 55" in open_sys.mandatory_obligations
        assert open_sys.technical_doc_annex == "Annex XI"


class TestConformityRouting:
    """Verify Article 43 conformity assessment path resolver."""

    def test_biometric_without_standards_triggers_notified_body(self) -> None:
        route = resolve_conformity_path("biometrics", uses_harmonised_standards=False, is_biometric=True)
        assert route == ConformityRoute.ANNEX_VII_NOTIFIED_BODY

    def test_biometric_with_standards_uses_internal_control(self) -> None:
        route = resolve_conformity_path("biometrics", uses_harmonised_standards=True, is_biometric=True)
        assert route == ConformityRoute.ANNEX_VI_INTERNAL_CONTROL

    def test_critical_infrastructure_uses_annex_vi_internal_control(self) -> None:
        """Annex III point 2 is Art. 43(2) territory — Annex VI, NO notified body.

        ⚠ This assertion was inverted. It required
        ``resolve_conformity_path("critical_infrastructure") ==
        ANNEX_I_SECTORAL``, i.e. it pinned the implementation's confusion
        between Annex III(2) (a high-risk USE CASE: safety components in
        critical infrastructure) and Annex I (product-safety harmonisation
        legislation). Article 43(2) names points 2 to 8 explicitly and says the
        procedure "does not provide for the involvement of a notified body",
        while the ANNEX_I_SECTORAL registry entry carries
        ``requires_notified_body=True`` — so the green test was certifying advice
        that would send a provider to a notified body it does not need.
        """
        route = resolve_conformity_path("critical_infrastructure")
        assert route == ConformityRoute.ANNEX_VI_INTERNAL_CONTROL

    def test_annex_i_safety_component_uses_sectoral_route(self) -> None:
        """Art. 43(3) — the genuine Annex I case, kept as its own explicit id."""
        assert resolve_conformity_path("annex_i") == ConformityRoute.ANNEX_I_SECTORAL

    def test_every_annex_iii_point_2_to_8_is_internal_control(self) -> None:
        """Art. 43(2) is a closed rule — assert it over the whole registry."""
        from app.data.ontology import ANNEX_III_REGISTRY

        for cid, cat in ANNEX_III_REGISTRY.items():
            if cat.number and cat.number >= 2:
                assert resolve_conformity_path(cid) == (
                    ConformityRoute.ANNEX_VI_INTERNAL_CONTROL
                ), f"Annex III point {cat.number} ({cid}) must be Annex VI per Art. 43(2)"

    def test_standard_annex_iii_uses_internal_control(self) -> None:
        route = resolve_conformity_path("employment")
        assert route == ConformityRoute.ANNEX_VI_INTERNAL_CONTROL


class TestFRIAAndIncidents:
    """Verify FRIA (Art. 27) and Serious Incident (Art. 73) schemas."""

    def test_fria_has_six_procedural_steps(self) -> None:
        fria = FRIA_REGISTRY["fria_public_and_essential"]
        assert len(fria.required_steps) == 6
        assert "Art. 27" in fria.governing_articles
        assert any("Art. 27(1)(a)" in step for step in fria.required_steps)
        assert any("Art. 27(1)(f)" in step for step in fria.required_steps)

    def test_serious_incident_deadlines(self) -> None:
        """Article 73 deadlines, asserted against the ACT — not against the code.

        ⚠ This test previously pinned the bug. It asserted
        ``critical_death_or_infrastructure.deadline_hours == 72`` and went
        green, which is how a fabricated 72-hour deadline (a GDPR Art. 33
        figure, absent from the AI Act) survived review: the suite was locking
        the error in rather than catching it. A test written by reading the
        implementation can only ever confirm the implementation.

        Each assertion below now carries the paragraph it comes from, and
        ``test_deadlines_match_the_pinned_act_text`` re-derives them from the
        verbatim CELEX text so the two can never drift apart silently.
        """
        death = SERIOUS_INCIDENT_REGISTRY["death_of_a_person"]
        assert death.deadline_hours == 240, "Art. 73(4): death — 10 days"
        assert "Art. 73" in death.statutory_basis

        infra = SERIOUS_INCIDENT_REGISTRY["widespread_infringement_or_infrastructure"]
        assert infra.deadline_hours == 48, "Art. 73(3): infrastructure — 2 days"
        assert "Art. 73" in infra.statutory_basis

        general = SERIOUS_INCIDENT_REGISTRY["general_serious_incident"]
        assert general.deadline_hours == 360, "Art. 73(2): general — 15 days"

        # No entry may reintroduce the GDPR window.
        assert all(
            sla.deadline_hours != 72 for sla in SERIOUS_INCIDENT_REGISTRY.values()
        ), "72h is GDPR Art. 33, not AI Act Art. 73"

    def test_deadlines_match_the_pinned_act_text(self) -> None:
        """Re-derive every deadline from the verbatim Act, not from the code.

        This is the guard the previous test lacked: it reads the pinned CELEX
        32024R1689 text and asserts the registry agrees with it. A future edit
        that changes a number must also change the law to stay green, which it
        cannot.
        """
        from app.data.provision_text import get_provision_text

        expected = {
            "Article 73.2": (360, "15 days"),
            "Article 73.3": (48, "two days"),
            "Article 73.4": (240, "10 days"),
        }
        by_hours = {
            sla.deadline_hours: sla for sla in SERIOUS_INCIDENT_REGISTRY.values()
        }
        for ref, (hours, phrase) in expected.items():
            text = (get_provision_text(ref) or "").lower()
            assert text, f"{ref} has no pinned text"
            assert phrase in text, f"{ref} should contain {phrase!r}; got: {text[:160]}"
            assert hours in by_hours, f"no registry entry with {hours}h for {ref}"


class TestAllArticlesReferencedIntegrity:
    """Verify that all_articles_referenced includes all new articles without invalid entries."""

    def test_all_referenced_articles_are_valid(self) -> None:
        all_refs = all_articles_referenced()
        for ref in all_refs:
            assert _is_valid_ref(ref), f"Hallucinated article reference found in ontology: {ref!r}"


class TestSemanticGraphEngine:
    """Verify SemanticGraphEngine query methods across in-memory and live Neo4j paths."""

    def test_causal_risk_chain_retrieval(self) -> None:
        engine = SemanticGraphEngine()
        result = engine.query_causal_risk_chain("sampling_bias_recruitment")
        assert result["found"] is True
        assert len(result["required_controls"]) >= 2
        assert any(ref in result["statutory_violation"] for ref in ("Art. 10", "Article 10"))

    def test_conformity_evaluation(self) -> None:
        engine = SemanticGraphEngine()
        eval_result = engine.evaluate_conformity_path("employment")
        assert eval_result["route_type"] == "annex_vi_internal_control"
        assert eval_result["requires_notified_body"] is False

    def test_conformity_evaluation_biometric_notified_body(self) -> None:
        engine = SemanticGraphEngine()
        eval_result = engine.evaluate_conformity_path("biometrics", uses_harmonised_standards=False, is_biometric=True)
        assert eval_result["route_type"] == "annex_vii_notified_body"
        assert eval_result["requires_notified_body"] is True

    def test_gpai_profile_retrieval(self) -> None:
        engine = SemanticGraphEngine()
        profile = engine.get_gpai_profile("systemic_gpai_frontier")
        assert profile is not None
        assert profile["has_systemic_risk"] is True
        assert profile["training_compute_flops"] >= 1.0e25

    def test_fria_requirements_retrieval(self) -> None:
        engine = SemanticGraphEngine()
        fria = engine.get_fria_requirements("fria_public_and_essential")
        assert fria is not None
        assert len(fria["required_steps"]) == 6

    def test_incident_sla_retrieval(self) -> None:
        engine = SemanticGraphEngine()
        inc = engine.get_incident_sla("death_of_a_person")
        assert inc is not None
        assert inc["deadline_hours"] == 240  # Art. 73(4) — 10 days
        assert inc["qms_update_required"] is True

    def test_standards_control_traversal(self) -> None:
        engine = SemanticGraphEngine()
        controls = engine.traverse_risk_controls_by_standard("ISO/IEC 23894")
        assert len(controls) >= 1
        assert any("ISO/IEC 23894" in s for c in controls for s in c["standards_ref"])

    def test_high_risk_causal_pathways(self) -> None:
        engine = SemanticGraphEngine()
        pathways = engine.traverse_high_risk_causal_pathways("employment")
        assert pathways["category_id"] == "annex_iii_employment"
        assert len(pathways["risk_pathways"]) >= 1

    def test_offline_fallback_when_client_disabled(self) -> None:
        """Verify seamless fallback when client.enabled is False."""
        class MockDisabledClient:
            enabled = False
            def execute_read(self, q, p=None):
                raise RuntimeError("Should not be called")

        engine = SemanticGraphEngine(neo4j_client=MockDisabledClient())
        assert engine.is_neo4j_active is False
        result = engine.query_causal_risk_chain("prompt_injection_safety_bypass")
        assert result["found"] is True
        assert result["severity_level"] == "critical"
        assert len(result["required_controls"]) >= 2


class TestBM25OntologyRecall:
    """Verify BM25 recall for new AIRO risk terms and GPAI queries."""

    def test_sampling_bias_query_surfaces_art_10(self) -> None:
        hits = top_articles_by_relevance("demographic disparity and sampling bias in recruitment", k=5)
        assert "Art. 10" in hits or "Annex III" in hits

    def test_systemic_flops_query_surfaces_art_53_or_55(self) -> None:
        hits = top_articles_by_relevance("10^25 flops systemic frontier model evaluation", k=5)
        assert "Art. 53" in hits or "Art. 55" in hits

    def test_fria_questionnaire_query_surfaces_art_27(self) -> None:
        hits = top_articles_by_relevance("deployer fundamental rights impact assessment questionnaire", k=5)
        assert "Art. 27" in hits
