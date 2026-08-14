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
        assert len(RISK_SCENARIO_REGISTRY) >= 5
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
        assert len(RISK_CONTROL_REGISTRY) >= 7
        for control in RISK_CONTROL_REGISTRY.values():
            for ref in control.articles:
                assert _is_valid_ref(ref), f"Invalid article ref {ref!r} in control {control.id}"


class TestGPAIGovernance:
    """Verify General-Purpose AI model profiles and exemption logic."""

    def test_gpai_registry_contains_standard_and_systemic(self) -> None:
        assert "standard_gpai_proprietary" in GPAI_REGISTRY
        assert "standard_gpai_open_source" in GPAI_REGISTRY
        assert "systemic_gpai_frontier" in GPAI_REGISTRY

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


class TestConformityRouting:
    """Verify Article 43 conformity assessment path resolver."""

    def test_biometric_without_standards_triggers_notified_body(self) -> None:
        route = resolve_conformity_path("biometrics", uses_harmonised_standards=False, is_biometric=True)
        assert route == ConformityRoute.ANNEX_VII_NOTIFIED_BODY

    def test_biometric_with_standards_uses_internal_control(self) -> None:
        route = resolve_conformity_path("biometrics", uses_harmonised_standards=True, is_biometric=True)
        assert route == ConformityRoute.ANNEX_VI_INTERNAL_CONTROL

    def test_critical_infrastructure_uses_annex_i_sectoral(self) -> None:
        route = resolve_conformity_path("critical_infrastructure")
        assert route == ConformityRoute.ANNEX_I_SECTORAL

    def test_standard_annex_iii_uses_internal_control(self) -> None:
        route = resolve_conformity_path("employment")
        assert route == ConformityRoute.ANNEX_VI_INTERNAL_CONTROL


class TestFRIAAndIncidents:
    """Verify FRIA (Art. 27) and Serious Incident (Art. 73) schemas."""

    def test_fria_has_six_procedural_steps(self) -> None:
        fria = FRIA_REGISTRY["fria_public_and_essential"]
        assert len(fria.required_steps) == 6
        assert "Art. 27" in fria.governing_articles

    def test_serious_incident_deadlines(self) -> None:
        critical = SERIOUS_INCIDENT_REGISTRY["critical_death_or_infrastructure"]
        assert critical.deadline_hours == 72
        assert "Art. 73" in critical.statutory_basis

        general = SERIOUS_INCIDENT_REGISTRY["general_serious_incident"]
        assert general.deadline_hours == 360  # 15 days


class TestAllArticlesReferencedIntegrity:
    """Verify that all_articles_referenced includes all new articles without invalid entries."""

    def test_all_referenced_articles_are_valid(self) -> None:
        all_refs = all_articles_referenced()
        for ref in all_refs:
            assert _is_valid_ref(ref), f"Hallucinated article reference found in ontology: {ref!r}"


class TestSemanticGraphEngine:
    """Verify SemanticGraphEngine query methods."""

    def test_causal_risk_chain_retrieval(self) -> None:
        engine = SemanticGraphEngine()
        result = engine.query_causal_risk_chain("sampling_bias_recruitment")
        assert result["found"] is True
        assert len(result["required_controls"]) == 2
        assert "Art. 10" in result["statutory_violation"]

    def test_conformity_evaluation(self) -> None:
        engine = SemanticGraphEngine()
        eval_result = engine.evaluate_conformity_path("employment")
        assert eval_result["route_type"] == "annex_vi_internal_control"
        assert eval_result["requires_notified_body"] is False


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
