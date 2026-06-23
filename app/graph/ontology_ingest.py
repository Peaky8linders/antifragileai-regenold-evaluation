"""Ontology Ingestion Script for Neo4j.

This script migrates the typed ontology defined in `app.data.ontology`
into the Neo4j knowledge graph using `app.graph.client`.
"""

import logging
from app.data.ontology import (
    ActorRole,
    RiskClass,
    PRACTICE_REGISTRY,
    ANNEX_III_REGISTRY,
    PHASE_REGISTRY,
    ROLE_OBLIGATIONS,
)
from app.graph.client import get_graph_client

logger = logging.getLogger(__name__)

import re

def normalize_article_id(ref: str) -> str:
    """Map 'Art. 5' -> 'article_5', 'Annex III' -> 'annex_III' per seeder convention."""
    ref = ref.strip()
    m_art = re.match(r"^Art\.\s*(\d+)$", ref, re.IGNORECASE)
    if m_art:
        return f"article_{m_art.group(1)}"
    m_annex = re.match(r"^Annex\s+([IVXLCDM]+)$", ref, re.IGNORECASE)
    if m_annex:
        return f"annex_{m_annex.group(1).upper()}"
    return ref.replace(" ", "_").replace(".", "")

def ingest_ontology() -> None:
    """Read the ontology module and ingest it into the Neo4j graph."""
    client = get_graph_client()
    if not client.enabled:
        logger.warning("Graph client disabled; skipping ontology ingestion.")
        return

    queries: list[tuple[str, dict]] = []

    # 1. ActorRoles & RiskClasses mapping from ROLE_OBLIGATIONS
    for role, risk_map in ROLE_OBLIGATIONS.items():
        queries.append((
            "MERGE (r:ActorRole {id: $role})",
            {"role": role.value}
        ))
        for risk_class, articles in risk_map.items():
            queries.append((
                "MERGE (rc:RiskClass {id: $risk_class})",
                {"risk_class": risk_class.value}
            ))
            for article in articles:
                norm_art = normalize_article_id(article)
                # Merge the article root just to ensure relationships can attach
                queries.append((
                    "MERGE (a:Article {id: $article})",
                    {"article": norm_art}
                ))
                queries.append((
                    """
                    MATCH (r:ActorRole {id: $role})
                    MATCH (rc:RiskClass {id: $risk_class})
                    MATCH (a:Article {id: $article})
                    MERGE (r)-[:SUBJECT_TO {risk_class: $risk_class}]->(a)
                    """,
                    {"role": role.value, "risk_class": risk_class.value, "article": norm_art}
                ))

    # 2. Practices (Art 5 prohibitions)
    for p_id, practice in PRACTICE_REGISTRY.items():
        queries.append((
            """
            MERGE (p:Practice {id: $id})
            SET p.short_name = $short_name,
                p.description = $description,
                p.sub_paragraph = $sub_paragraph
            """,
            {
                "id": p_id,
                "short_name": practice.short_name,
                "description": practice.description,
                "sub_paragraph": practice.sub_paragraph,
            }
        ))
        
        for citation in practice.citation:
            norm_cit = normalize_article_id(citation)
            queries.append((
                "MERGE (a:Article {id: $citation})",
                {"citation": norm_cit}
            ))
            queries.append((
                """
                MATCH (p:Practice {id: $id})
                MATCH (a:Article {id: $citation})
                MERGE (p)-[:PROHIBITED_UNDER]->(a)
                """,
                {"id": p_id, "citation": norm_cit}
            ))
            
        for exc in practice.exceptions:
            queries.append((
                """
                MERGE (e:ExemptionContext {id: $exc})
                WITH e
                MATCH (p:Practice {id: $id})
                MERGE (p)-[:EXEMPTION]->(e)
                """,
                {"id": p_id, "exc": exc}
            ))

    # 3. Annex III Categories
    for c_id, cat in ANNEX_III_REGISTRY.items():
        queries.append((
            """
            MERGE (c:AnnexIIICategory {id: $id})
            SET c.number = $number,
                c.short_name = $short_name,
                c.description = $description
            """,
            {
                "id": c_id,
                "number": cat.number,
                "short_name": cat.short_name,
                "description": cat.description
            }
        ))
        # Ensure 'Annex III' and 'Art. 6' roots
        for anchor in ["Annex III", "Art. 6"]:
            norm_anchor = normalize_article_id(anchor)
            queries.append((
                "MERGE (a:Article {id: $anchor})",
                {"anchor": norm_anchor}
            ))
            queries.append((
                """
                MATCH (c:AnnexIIICategory {id: $id})
                MATCH (a:Article {id: $anchor})
                MERGE (c)-[:FALLS_UNDER]->(a)
                """,
                {"id": c_id, "anchor": norm_anchor}
            ))

    # 4. Phases
    for phase_id, phase in PHASE_REGISTRY.items():
        queries.append((
            """
            MERGE (ph:Phase {id: $id})
            SET ph.label = $label,
                ph.effective_date = $effective_date,
                ph.description = $description
            """,
            {
                "id": phase_id,
                "label": phase.label,
                "effective_date": phase.effective_date.isoformat(),
                "description": phase.description
            }
        ))
        for art in phase.articles:
            norm_art = normalize_article_id(art)
            queries.append((
                "MERGE (a:Article {id: $art})",
                {"art": norm_art}
            ))
            queries.append((
                """
                MATCH (ph:Phase {id: $id})
                MATCH (a:Article {id: $art})
                MERGE (ph)-[:APPLIES_TO]->(a)
                """,
                {"id": phase_id, "art": norm_art}
            ))

    client.execute_write_batch(queries)
    logger.info("Successfully ingested ontology into Neo4j graph.")
    
    # 5. Ingest Legal AST (Ontology Leap)
    from app.engines.legal_ast import ingest_legal_ast
    ingest_legal_ast()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingest_ontology()
