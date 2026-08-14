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
    def client(self) -> Any:
        """Resolve the active GraphClient instance (custom or singleton)."""
        if self._client is not None:
            return self._client
        try:
            from app.graph.client import get_graph_client
            return get_graph_client()
        except Exception:
            return None

    @property
    def is_neo4j_active(self) -> bool:
        """Return True if a live Neo4j client connection is available and enabled."""
        c = self.client
        if c is None:
            return False
        try:
            return bool(getattr(c, "enabled", False))
        except Exception:
            return False

    def execute_query(self, cypher: str, parameters: dict[str, Any] | None = None) -> list[dict]:
        """Execute a read query against live Neo4j if active, else return empty list."""
        if not self.is_neo4j_active:
            return []
        try:
            return self.client.execute_read(cypher, parameters or {})
        except Exception as exc:
            logger.warning("SemanticGraphEngine Cypher execution failed: %s", exc)
            return []

    # ── 1. Causal Risk Chain Querying ─────────────────────────────────────────

    def query_causal_risk_chain(self, risk_scenario_id: str) -> dict[str, Any]:
        """Retrieve the complete AIRO causal chain for a risk scenario.

        Executes a live Cypher traversal when Neo4j is active, seamlessly falling
        back to the in-process ontology registry when offline.
        """
        if self.is_neo4j_active:
            cypher = """
            MATCH (s:RiskScenario {id: $scenario_id})
            OPTIONAL MATCH (s)-[:REQUIRES_CONTROL]->(c:RiskControl)
            OPTIONAL MATCH (s)-[:VIOLATES]->(v)
            RETURN s.id AS id,
                   s.short_name AS short_name,
                   s.hazard_or_threat AS hazard_or_threat,
                   s.vulnerability AS vulnerability,
                   s.risk_event AS risk_event,
                   s.impact_area AS impact_area,
                   s.severity_level AS severity_level,
                   s.description AS description,
                   s.statutory_violation AS statutory_violation,
                   collect(DISTINCT coalesce(v.strict_citation, v.number, v.id)) AS violated_nodes,
                   collect(DISTINCT {
                       id: c.id,
                       name: c.name,
                       control_type: c.control_type,
                       lifecycle_phase: c.lifecycle_phase,
                       evidenced_by: c.evidenced_by,
                       standards_ref: c.standards_ref,
                       articles: c.articles,
                       description: c.description
                   }) AS controls
            """
            try:
                rows = self.client.execute_read(cypher, {"scenario_id": risk_scenario_id})
                if rows and rows[0].get("id"):
                    row = rows[0]
                    controls = [c for c in row.get("controls", []) if c and c.get("id")]
                    # Reconcile statutory violation references
                    stat_violation = row.get("statutory_violation")
                    if not stat_violation:
                        stat_violation = row.get("violated_nodes", [])
                    if isinstance(stat_violation, list):
                        stat_violation = tuple(stat_violation)

                    # Ensure control properties are clean tuples/lists
                    cleaned_controls = []
                    for c in controls:
                        evidenced_by = c.get("evidenced_by") or ()
                        if isinstance(evidenced_by, list):
                            evidenced_by = tuple(evidenced_by)
                        standards_ref = c.get("standards_ref") or ()
                        if isinstance(standards_ref, list):
                            standards_ref = tuple(standards_ref)
                        articles = c.get("articles") or ()
                        if isinstance(articles, list):
                            articles = tuple(articles)
                        cleaned_controls.append({
                            "id": c["id"],
                            "name": c.get("name", ""),
                            "control_type": c.get("control_type", ""),
                            "lifecycle_phase": c.get("lifecycle_phase", ""),
                            "evidenced_by": evidenced_by,
                            "standards_ref": standards_ref,
                            "articles": articles,
                        })

                    return {
                        "found": True,
                        "id": row["id"],
                        "short_name": row.get("short_name", ""),
                        "hazard_or_threat": row.get("hazard_or_threat", ""),
                        "vulnerability": row.get("vulnerability", ""),
                        "risk_event": row.get("risk_event", ""),
                        "impact_area": row.get("impact_area", ""),
                        "severity_level": row.get("severity_level", ""),
                        "statutory_violation": stat_violation,
                        "required_controls": cleaned_controls,
                        "description": row.get("description", ""),
                    }
            except Exception as exc:
                logger.warning("Graph causal risk chain query failed (%s), falling back to registry", exc)

        # In-memory registry fallback
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

    # ── 2. Conformity Assessment Pathway ─────────────────────────────────────

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
        route_id = route_enum.value

        if self.is_neo4j_active:
            cypher = """
            MATCH (cr:ConformityRoute {id: $route_id})
            RETURN cr.route_type AS route_type,
                   cr.requires_notified_body AS requires_notified_body,
                   cr.governing_articles AS governing_articles,
                   cr.applicable_annex AS applicable_annex,
                   cr.description AS description
            """
            try:
                rows = self.client.execute_read(cypher, {"route_id": route_id})
                if rows and rows[0].get("route_type"):
                    row = rows[0]
                    governing = row.get("governing_articles") or ("Art. 43",)
                    if isinstance(governing, list):
                        governing = tuple(governing)
                    return {
                        "route_type": row["route_type"],
                        "requires_notified_body": bool(row.get("requires_notified_body", False)),
                        "governing_articles": governing,
                        "applicable_annex": row.get("applicable_annex", "Annex VI"),
                        "description": row.get("description", ""),
                    }
            except Exception as exc:
                logger.warning("Graph conformity path query failed (%s), falling back to registry", exc)

        route_details = CONFORMITY_ROUTE_REGISTRY.get(route_id)
        return {
            "route_type": route_enum.value,
            "requires_notified_body": route_details.requires_notified_body if route_details else False,
            "governing_articles": route_details.governing_articles if route_details else ("Art. 43",),
            "applicable_annex": route_details.applicable_annex if route_details else "Annex VI",
            "description": route_details.description if route_details else "",
        }

    # ── 3. General-Purpose AI (GPAI) Governance ──────────────────────────────

    def get_gpai_profile(self, profile_id: str) -> dict[str, Any] | None:
        """Look up a GPAI governance profile with compute and exemption rules."""
        if self.is_neo4j_active:
            cypher = """
            MATCH (g:GPAIModelProfile {id: $profile_id})
            RETURN g.id AS id,
                   g.model_name AS model_name,
                   g.training_compute_flops AS training_compute_flops,
                   g.is_open_source AS is_open_source,
                   g.has_systemic_risk AS has_systemic_risk,
                   g.mandatory_obligations AS mandatory_obligations,
                   g.technical_doc_annex AS technical_doc_annex,
                   g.downstream_info_annex AS downstream_info_annex,
                   g.description AS description
            """
            try:
                rows = self.client.execute_read(cypher, {"profile_id": profile_id})
                if rows and rows[0].get("id"):
                    row = rows[0]
                    mand_obls = row.get("mandatory_obligations") or ()
                    if isinstance(mand_obls, list):
                        mand_obls = tuple(mand_obls)
                    return {
                        "id": row["id"],
                        "model_name": row.get("model_name", ""),
                        "training_compute_flops": float(row.get("training_compute_flops", 0.0)),
                        "is_open_source": bool(row.get("is_open_source", False)),
                        "has_systemic_risk": bool(row.get("has_systemic_risk", False)),
                        "mandatory_obligations": mand_obls,
                        "technical_doc_annex": row.get("technical_doc_annex", ""),
                        "downstream_info_annex": row.get("downstream_info_annex", ""),
                        "description": row.get("description", ""),
                    }
            except Exception as exc:
                logger.warning("Graph GPAI profile query failed (%s), falling back to registry", exc)

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

    # ── 4. FRIA Requirements & Serious Incident SLAs ─────────────────────────

    def get_fria_requirements(self, fria_id: str = "fria_public_and_essential") -> dict[str, Any] | None:
        """Look up Fundamental Rights Impact Assessment requirements (Art. 27)."""
        if self.is_neo4j_active:
            cypher = """
            MATCH (f:FRIAWorkflow {id: $fria_id})
            RETURN f.id AS id,
                   f.deployer_category AS deployer_category,
                   f.governing_articles AS governing_articles,
                   f.required_steps AS required_steps,
                   f.mandatory_reporting_authority AS mandatory_reporting_authority,
                   f.description AS description
            """
            try:
                rows = self.client.execute_read(cypher, {"fria_id": fria_id})
                if rows and rows[0].get("id"):
                    row = rows[0]
                    gov = row.get("governing_articles") or ()
                    if isinstance(gov, list):
                        gov = tuple(gov)
                    steps = row.get("required_steps") or ()
                    if isinstance(steps, list):
                        steps = tuple(steps)
                    return {
                        "id": row["id"],
                        "deployer_category": row.get("deployer_category", ""),
                        "governing_articles": gov,
                        "required_steps": steps,
                        "mandatory_reporting_authority": row.get("mandatory_reporting_authority", ""),
                        "description": row.get("description", ""),
                    }
            except Exception as exc:
                logger.warning("Graph FRIA query failed (%s), falling back to registry", exc)

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
        if self.is_neo4j_active:
            cypher = """
            MATCH (i:SeriousIncidentSLA {id: $incident_id})
            RETURN i.id AS id,
                   i.incident_type AS incident_type,
                   i.deadline_hours AS deadline_hours,
                   i.statutory_basis AS statutory_basis,
                   i.qms_update_required AS qms_update_required,
                   i.description AS description
            """
            try:
                rows = self.client.execute_read(cypher, {"incident_id": incident_id})
                if rows and rows[0].get("id"):
                    row = rows[0]
                    basis = row.get("statutory_basis") or ()
                    if isinstance(basis, list):
                        basis = tuple(basis)
                    return {
                        "id": row["id"],
                        "incident_type": row.get("incident_type", ""),
                        "deadline_hours": int(row.get("deadline_hours", 0)),
                        "statutory_basis": basis,
                        "qms_update_required": bool(row.get("qms_update_required", False)),
                        "description": row.get("description", ""),
                    }
            except Exception as exc:
                logger.warning("Graph incident SLA query failed (%s), falling back to registry", exc)

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

    # ── 5. Multi-Hop Graph Reasoners ──────────────────────────────────────────

    def traverse_risk_controls_by_standard(self, standards_substring: str) -> list[dict[str, Any]]:
        """Find risk controls and the scenarios/articles they govern matching a standard."""
        if self.is_neo4j_active:
            cypher = """
            MATCH (c:RiskControl)
            WHERE any(s IN c.standards_ref WHERE toLower(s) CONTAINS toLower($std))
            OPTIONAL MATCH (s:RiskScenario)-[:REQUIRES_CONTROL]->(c)
            OPTIONAL MATCH (c)-[:GOVERNED_BY]->(a)
            RETURN c.id AS id,
                   c.name AS name,
                   c.standards_ref AS standards_ref,
                   c.control_type AS control_type,
                   c.lifecycle_phase AS lifecycle_phase,
                   c.articles AS articles,
                   collect(DISTINCT s.id) AS mitigates_scenarios,
                   collect(DISTINCT coalesce(a.strict_citation, a.number, a.id)) AS governing_provisions
            """
            try:
                rows = self.client.execute_read(cypher, {"std": standards_substring})
                if rows:
                    return rows
            except Exception as exc:
                logger.warning("Graph standards traversal failed (%s), falling back to registry", exc)

        # In-memory fallback
        results = []
        std_lower = standards_substring.lower()
        for ctrl in RISK_CONTROL_REGISTRY.values():
            if any(std_lower in s.lower() for s in ctrl.standards_ref):
                scenarios = [
                    s.id for s in RISK_SCENARIO_REGISTRY.values()
                    if ctrl.id in s.required_controls or ctrl.mitigates_risk_id == s.id
                ]
                results.append({
                    "id": ctrl.id,
                    "name": ctrl.name,
                    "standards_ref": list(ctrl.standards_ref),
                    "control_type": ctrl.control_type,
                    "lifecycle_phase": ctrl.lifecycle_phase,
                    "articles": list(ctrl.articles),
                    "mitigates_scenarios": scenarios,
                    "governing_provisions": list(ctrl.articles),
                })
        return results

    def traverse_high_risk_causal_pathways(self, category_id: str) -> dict[str, Any]:
        """Traverse Annex III category → Article 6 → Risk Scenarios → Required Controls."""
        if self.is_neo4j_active:
            cypher = """
            MATCH (cat:AnnexIIICategory {id: $cat_id})
            OPTIONAL MATCH (cat)-[:TRIGGERS_HIGH_RISK_UNDER]->(a:Article)
            OPTIONAL MATCH (s:RiskScenario)-[:VIOLATES]->(a)
            OPTIONAL MATCH (s)-[:REQUIRES_CONTROL]->(c:RiskControl)
            RETURN cat.id AS category_id,
                   cat.label AS category_label,
                   collect(DISTINCT coalesce(a.strict_citation, a.number, a.id)) AS triggered_articles,
                   collect(DISTINCT {
                       scenario_id: s.id,
                       scenario_name: s.short_name,
                       severity: s.severity_level,
                       control_id: c.id,
                       control_name: c.name
                   }) AS risk_pathways
            """
            try:
                rows = self.client.execute_read(cypher, {"cat_id": f"annex_iii_{category_id}" if not category_id.startswith("annex_iii_") else category_id})
                if rows and rows[0].get("category_id"):
                    row = rows[0]
                    pathways = [p for p in row.get("risk_pathways", []) if p and p.get("scenario_id")]
                    return {
                        "category_id": row["category_id"],
                        "category_label": row.get("category_label", ""),
                        "triggered_articles": row.get("triggered_articles", []),
                        "risk_pathways": pathways,
                    }
            except Exception as exc:
                logger.warning("Graph causal pathway traversal failed (%s), falling back to registry", exc)

        # In-memory fallback
        from app.data.ontology import ANNEX_III_REGISTRY
        clean_id = category_id.replace("annex_iii_", "")
        cat = ANNEX_III_REGISTRY.get(clean_id)
        if not cat:
            return {"category_id": category_id, "category_label": "", "triggered_articles": [], "risk_pathways": []}

        pathways = []
        for s in RISK_SCENARIO_REGISTRY.values():
            if "Annex III" in s.statutory_violation or "Art. 6" in s.statutory_violation:
                for c_id in s.required_controls:
                    c = RISK_CONTROL_REGISTRY.get(c_id)
                    pathways.append({
                        "scenario_id": s.id,
                        "scenario_name": s.short_name,
                        "severity": s.severity_level,
                        "control_id": c_id,
                        "control_name": c.name if c else c_id,
                    })

        return {
            "category_id": f"annex_iii_{clean_id}",
            "category_label": cat.short_name,
            "triggered_articles": ["Article 6", "Annex III"],
            "risk_pathways": pathways,
        }


# Global singleton instance
semantic_graph = SemanticGraphEngine()
