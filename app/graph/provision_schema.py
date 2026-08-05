"""Provision-level ontology schema for the EU AI Act knowledge graph.

Ported from the upstream ``euaiact.graph.schema`` (flattened copy at
``euairagtest/schema.py``).

Deliberately a SEPARATE module from :mod:`app.graph.schema`. That module holds
the Neo4j *label / relationship-name string constants* consumed by
``scripts/seed_neo4j_kb.py`` (``NODE_ARTICLE``, ``REL_HAS_OBLIGATION``, ...).
This module holds the pydantic ``Node``/``Edge`` models, the ``NodeType`` /
``EdgeType`` enums and the actor / risk-class vocabularies consumed by
:mod:`app.graph.knowledge_graph`. The two describe different graphs; merging
them would collide on the name ``schema`` and break the seeder.

The original upstream docstring follows.

Ontology schema for the EU AI Act knowledge graph (plan §4).

Node/edge vocabulary composed from the standards that each earn their place:

* **Akoma Ntoso eId** — canonical node id for every provision (``art_6__para_2__point_a``).
* **ELI ontology** — stable work URI + provision anchor (carried on Provision nodes).
* **LegalRuleML v1.0** (OASIS, 2021) — the deontic layer: ``DeonticStatement`` with a
  ``bearer`` Actor, a typed activation ``Condition`` and a ``Sanction`` consequence.
* **LRMoo** (IFLA, 2024) — temporal ``AMENDS`` / ``SUPERSEDED_BY`` versioning.

Two verified deviations from a naive reading of plan §4 (see research 2026-07-22):
* **LKIF-Core is treated as a conceptual reference, not an OWL import** — it is
  unmaintained since ~2009 with no toolchain; the actor/deontic vocabulary here aligns
  in spirit to DPV v2.0 + AIRO instead.
* **``AISystem`` and ``RiskClass`` nodes are added** — the whole obligation structure of
  the Act is conditioned on risk classification, so "what must a provider do?" is not
  answerable without them. ``Condition``/``Sanction`` are modelled as nodes (not string
  literals) to keep activation/enforcement queryable.

Nodes/edges are tagged :data:`DETERMINISTIC` (built offline from Phase-1 data, zero
hallucination) or :data:`ENRICHMENT` (needs the ML cascade in :mod:`euaiact.graph.enrich`).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "NodeType",
    "EdgeType",
    "Node",
    "Edge",
    "PROVISION_NODE_TYPES",
    "DETERMINISTIC_EDGES",
    "ENRICHMENT_EDGES",
    "EDGE_ENDPOINTS",
    "ACTOR_VOCAB",
    "RISK_CLASS_VOCAB",
]


class NodeType(str, Enum):
    """Neo4j node labels."""

    # structural (deterministic)
    PROVISION = "Provision"  # article / paragraph / point / subpoint (see `level` prop)
    RECITAL = "Recital"
    ANNEX = "Annex"
    ANNEX_POINT = "AnnexPoint"
    DEFINED_TERM = "DefinedTerm"
    EXTERNAL_REGULATION = "ExternalRegulation"
    DATE_MILESTONE = "DateMilestone"
    # controlled vocabularies (deterministic seed — closed sets from the Act)
    ACTOR = "Actor"
    RISK_CLASS = "RiskClass"
    # deontic / compliance layer (enrichment)
    DEONTIC_STATEMENT = "DeonticStatement"
    AI_SYSTEM = "AISystem"
    CONDITION = "Condition"
    SANCTION = "Sanction"
    HARMONISED_STANDARD = "HarmonisedStandard"


class EdgeType(str, Enum):
    """Neo4j relationship types (UPPER_SNAKE per convention)."""

    # structural (deterministic)
    HAS_CHILD = "HAS_CHILD"  # parent Provision -> child Provision (hasParent = inverse)
    CROSS_REFERENCES_INTERNAL = "CROSS_REFERENCES_INTERNAL"
    CROSS_REFERENCES_EXTERNAL = "CROSS_REFERENCES_EXTERNAL"
    USES_TERM = "USES_TERM"  # Provision -> DefinedTerm (term appears in the provision)
    DEFINES_TERM = "DEFINES_TERM"  # Provision (Art. 3) -> DefinedTerm
    INTERPRETED_BY = "INTERPRETED_BY"  # Provision -> Recital
    LISTED_IN = "LISTED_IN"  # AnnexPoint -> Provision (article that invokes the annex)
    APPLIES_FROM = "APPLIES_FROM"  # Provision -> DateMilestone
    # temporal (deterministic when the data carries it)
    AMENDS = "AMENDS"
    SUPERSEDED_BY = "SUPERSEDED_BY"
    # deontic / compliance layer (enrichment)
    GROUNDED_IN = "GROUNDED_IN"  # DeonticStatement -> Provision
    BEARER_OF = "BEARER_OF"  # Actor -> DeonticStatement
    HAS_CONDITION = "HAS_CONDITION"  # DeonticStatement -> Condition
    HAS_CONSEQUENCE = "HAS_CONSEQUENCE"  # DeonticStatement -> Sanction
    CLASSIFIED_AS = "CLASSIFIED_AS"  # AISystem -> RiskClass
    PRESUMES_CONFORMITY_WITH = "PRESUMES_CONFORMITY_WITH"  # HarmonisedStandard -> Provision


PROVISION_NODE_TYPES: frozenset[NodeType] = frozenset(
    {NodeType.PROVISION, NodeType.RECITAL, NodeType.ANNEX, NodeType.ANNEX_POINT}
)

DETERMINISTIC_EDGES: frozenset[EdgeType] = frozenset(
    {
        EdgeType.HAS_CHILD,
        EdgeType.CROSS_REFERENCES_INTERNAL,
        EdgeType.CROSS_REFERENCES_EXTERNAL,
        EdgeType.USES_TERM,
        EdgeType.INTERPRETED_BY,
        EdgeType.APPLIES_FROM,
    }
)

ENRICHMENT_EDGES: frozenset[EdgeType] = frozenset(
    {
        EdgeType.DEFINES_TERM,
        EdgeType.LISTED_IN,
        EdgeType.GROUNDED_IN,
        EdgeType.BEARER_OF,
        EdgeType.HAS_CONDITION,
        EdgeType.HAS_CONSEQUENCE,
        EdgeType.CLASSIFIED_AS,
        EdgeType.PRESUMES_CONFORMITY_WITH,
        EdgeType.AMENDS,
        EdgeType.SUPERSEDED_BY,
    }
)

# Allowed (source, target) node types per edge — documents intent and lets the graph
# self-validate. Provision-like endpoints accept any structural provision node.
EDGE_ENDPOINTS: dict[EdgeType, tuple[frozenset[NodeType], frozenset[NodeType]]] = {
    EdgeType.HAS_CHILD: (PROVISION_NODE_TYPES, PROVISION_NODE_TYPES),
    EdgeType.CROSS_REFERENCES_INTERNAL: (PROVISION_NODE_TYPES, PROVISION_NODE_TYPES),
    EdgeType.CROSS_REFERENCES_EXTERNAL: (
        PROVISION_NODE_TYPES,
        frozenset({NodeType.EXTERNAL_REGULATION}),
    ),
    EdgeType.USES_TERM: (PROVISION_NODE_TYPES, frozenset({NodeType.DEFINED_TERM})),
    EdgeType.DEFINES_TERM: (PROVISION_NODE_TYPES, frozenset({NodeType.DEFINED_TERM})),
    EdgeType.INTERPRETED_BY: (PROVISION_NODE_TYPES, frozenset({NodeType.RECITAL})),
    EdgeType.LISTED_IN: (frozenset({NodeType.ANNEX_POINT}), PROVISION_NODE_TYPES),
    EdgeType.APPLIES_FROM: (PROVISION_NODE_TYPES, frozenset({NodeType.DATE_MILESTONE})),
    EdgeType.AMENDS: (PROVISION_NODE_TYPES, PROVISION_NODE_TYPES),
    EdgeType.SUPERSEDED_BY: (PROVISION_NODE_TYPES, PROVISION_NODE_TYPES),
    EdgeType.GROUNDED_IN: (frozenset({NodeType.DEONTIC_STATEMENT}), PROVISION_NODE_TYPES),
    EdgeType.BEARER_OF: (frozenset({NodeType.ACTOR}), frozenset({NodeType.DEONTIC_STATEMENT})),
    EdgeType.HAS_CONDITION: (
        frozenset({NodeType.DEONTIC_STATEMENT}),
        frozenset({NodeType.CONDITION}),
    ),
    EdgeType.HAS_CONSEQUENCE: (
        frozenset({NodeType.DEONTIC_STATEMENT}),
        frozenset({NodeType.SANCTION}),
    ),
    EdgeType.CLASSIFIED_AS: (frozenset({NodeType.AI_SYSTEM}), frozenset({NodeType.RISK_CLASS})),
    EdgeType.PRESUMES_CONFORMITY_WITH: (
        frozenset({NodeType.HARMONISED_STANDARD}),
        PROVISION_NODE_TYPES,
    ),
}

# Closed vocabularies defined by the Act itself (Art. 3 roles; the Act's risk tiers).
# Seeded deterministically — these are definitional, not extracted. ``anchor`` is the
# well-established governing provision, for a "which article governs this?" hop.
ACTOR_VOCAB: dict[str, dict[str, str]] = {
    "provider": {"label": "Provider", "anchor": "art_3__para_3"},
    "deployer": {"label": "Deployer", "anchor": "art_3__para_4"},
    "authorised_representative": {"label": "Authorised representative", "anchor": "art_3__para_5"},
    "importer": {"label": "Importer", "anchor": "art_3__para_6"},
    "distributor": {"label": "Distributor", "anchor": "art_3__para_7"},
    "product_manufacturer": {"label": "Product manufacturer", "anchor": "art_3__para_8"},
    "notified_body": {"label": "Notified body", "anchor": "art_3__para_22"},
}

RISK_CLASS_VOCAB: dict[str, dict[str, str]] = {
    "prohibited": {"label": "Prohibited practice", "anchor": "art_5"},
    "high_risk": {"label": "High-risk AI system", "anchor": "art_6"},
    "limited_risk": {"label": "Limited-risk (transparency)", "anchor": "art_50"},
    "minimal_risk": {"label": "Minimal-risk", "anchor": ""},
    "gpai": {"label": "General-purpose AI model", "anchor": "art_51"},
    "gpai_systemic": {"label": "GPAI with systemic risk", "anchor": "art_51"},
}


class Node(BaseModel):
    """A graph node. ``id`` is unique across the graph and is the Cypher MERGE key."""

    model_config = ConfigDict(extra="forbid")

    id: str
    type: NodeType
    label: str = ""
    props: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    """A directed graph edge keyed by ``(type, source, target)`` for dedup."""

    model_config = ConfigDict(extra="forbid")

    type: EdgeType
    source: str
    target: str
    props: dict[str, Any] = Field(default_factory=dict)

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.type.value, self.source, self.target)
