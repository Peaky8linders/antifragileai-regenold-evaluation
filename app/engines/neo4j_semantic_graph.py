"""Neo4j Semantic Graph Engine for AIRO Causal Risk & EU AI Act Reasoning.

Provides graph traversal and Cypher query execution for:
1. **Causal Risk Chains**: Tracing Hazards/Threats → Vulnerabilities →
   Risk Events → Impacts → Harms → Controls → Evidence.
2. **Dynamic Conformity Assessment Routing**: Evaluating system domain,
   harmonised standard status, and biometric triggers to determine
   statutory conformity paths (Annex VI Internal Control vs Annex VII
   Notified Body vs Annex I Sectoral).
3. **GPAI & Value-Chain Lineage**: Tracking upstream model providers,
   training FLOP compute thresholds, open-source carve-outs (Art. 53(2)),
   and downstream fine-tuning obligations.
4. **Fundamental Rights & Incident Traversal**: Linking high-risk use
   cases to Article 27 FRIA steps and Article 73 serious incident SLAs.
"""
from __future__ import annotations

import logging
from typing import Any

from app.data.ontology import (
    CONFORMITY_ROUTE_REGISTRY,
    FRIA_REGISTRY,
    GPAI_REGISTRY,
    RISK_CONTROL_REGISTRY,
    RISK_SCENARIO_REGISTRY,
    SERIOUS_INCIDENT_REGISTRY,
    ConformityRoute,
    resolve_conformity_path,
)

logger = logging.getLogger(__name__)


class SemanticGraphEngine:
    """Semantic graph querying and reasoning interface over Neo4j & in-memory fallbacks."""

    def __init__(self, neo4j_client: Any = None) -> None:
        self._client = neo4j_client

    @property
    def is_neo4j_active(self) -> bool:
        """Return True if a live Neo4j client connection is available."""
        if self._client is None:
            return False
        try:
            return bool(getattr(self._client, "enabled", False))
        except Exception:
            return False

    def query_causal_risk_chain(self, risk_scenario_id: str) -> dict[str, Any]:
        """Retrieve the complete AIRO causal chain for a risk scenario.

        Returns hazard, vulnerability, risk event, impact area, controls,
        evidence artifacts, and governing statutory articles.
        """
        scenario = RISK_SCENARIO_REGISTRY.get(risk_scenario_id)
        if not scenario:
            return {"found": False, "error": f"Risk scenario '{risk_scenario_id}' not found"}

        controls_data = []
        for ctrl_id in scenario.required_controls:
            ctrl = RISK_CONTROL_REGISTRY.get(ctrl_id)
            if ctrl:
                controls_data.append({
                    "id": ctrl.id,
                    "name": ctrl.name,
                    "control_type": ctrl.control_type,
                    "lifecycle_phase": ctrl.lifecycle_phase,
                    "evidenced_by": ctrl.evidenced_by,
                    "standards_ref": ctrl.standards_ref,
                    "articles": ctrl.articles,
                })

        return {
            "found": True,
            "id": scenario.id,
            "short_name": scenario.short_name,
            "hazard_or_threat": scenario.hazard_or_threat,
            "vulnerability": scenario.vulnerability,
            "risk_event": scenario.risk_event,
            "impact_area": scenario.impact_area,
            "severity_level": scenario.severity_level,
            "statutory_violation": scenario.statutory_violation,
            "required_controls": controls_data,
            "description": scenario.description,
        }

    def evaluate_conformity_path(
        self,
        category_id: str,
        uses_harmonised_standards: bool = True,
        is_biometric: bool = False,
    ) -> dict[str, Any]:
        """Evaluate the statutory conformity assessment route under Article 43."""
        route_enum = resolve_conformity_path(
            category_id=category_id,
            uses_harmonised_standards=uses_harmonised_standards,
            is_biometric=is_biometric,
        )
        route_details = CONFORMITY_ROUTE_REGISTRY.get(route_enum.value)
        return {
            "route_type": route_enum.value,
            "requires_notified_body": route_details.requires_notified_body if route_details else False,
            "governing_articles": route_details.governing_articles if route_details else ("Art. 43",),
            "applicable_annex": route_details.applicable_annex if route_details else "Annex VI",
            "description": route_details.description if route_details else "",
        }

    def get_gpai_profile(self, profile_id: str) -> dict[str, Any] | None:
        """Look up a GPAI governance profile with compute and exemption rules."""
        profile = GPAI_REGISTRY.get(profile_id)
        if not profile:
            return None
        return {
            "id": profile.id,
            "model_name": profile.model_name,
            "training_compute_flops": profile.training_compute_flops,
            "is_open_source": profile.is_open_source,
            "has_systemic_risk": profile.has_systemic_risk,
            "mandatory_obligations": profile.mandatory_obligations,
            "technical_doc_annex": profile.technical_doc_annex,
            "downstream_info_annex": profile.downstream_info_annex,
            "description": profile.description,
        }

    def get_fria_requirements(self, fria_id: str = "fria_public_and_essential") -> dict[str, Any] | None:
        """Look up Fundamental Rights Impact Assessment requirements (Art. 27)."""
        fria = FRIA_REGISTRY.get(fria_id)
        if not fria:
            return None
        return {
            "id": fria.id,
            "deployer_category": fria.deployer_category,
            "governing_articles": fria.governing_articles,
            "required_steps": fria.required_steps,
            "mandatory_reporting_authority": fria.mandatory_reporting_authority,
            "description": fria.description,
        }

    def get_incident_sla(self, incident_id: str) -> dict[str, Any] | None:
        """Look up Article 73 incident reporting deadline SLA and QMS duties."""
        incident = SERIOUS_INCIDENT_REGISTRY.get(incident_id)
        if not incident:
            return None
        return {
            "id": incident.id,
            "incident_type": incident.incident_type,
            "deadline_hours": incident.deadline_hours,
            "statutory_basis": incident.statutory_basis,
            "qms_update_required": incident.qms_update_required,
            "description": incident.description,
        }


# Global singleton instance
semantic_graph = SemanticGraphEngine()
