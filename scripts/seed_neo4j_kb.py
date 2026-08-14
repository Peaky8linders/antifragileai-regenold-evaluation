"""Neo4j KB seeder for the Regenold EU AI Act RAG bundle.

Pushes the bundle's deterministic KB surface (articles, annexes, recitals,
definitions, obligations, Annex III categories, risk levels, operator
roles) and the cross-reference / classification edges that connect them
into a Neo4j graph. Designed for the optional Layer-1 graph path that
``app.graph.reasoning`` queries against — when the graph is empty the
engine silently falls back to its in-process KB; once seeded, the same
queries gain typed multi-hop reasoning.

The script is route-safe under any environment:

* No ``NEO4J_URI`` set → ``GraphClient.enabled`` is False and we either
  refuse to write (default) or stay in ``--dry-run`` mode (prints the
  Cypher payload counts and exits 0). Tests rely on the dry-run path
  always working offline.
* ``NEO4J_URI`` set but ``neo4j`` driver missing → same disabled path,
  same dry-run availability.
* ``NEO4J_URI`` + driver live → batched, idempotent ``MERGE``-based
  writes. Re-running is a no-op against the same KB ``KB_VERSION``.

CLI:

    py -3.12 -m scripts.seed_neo4j_kb --dry-run
    py -3.12 -m scripts.seed_neo4j_kb --neo4j-uri bolt://localhost:7687
    py -3.12 -m scripts.seed_neo4j_kb --clear --verbose

Pure stdlib + existing project imports. Never adds Cypher injection
vectors — every parameter goes through driver-side parameter binding.
"""
from __future__ import annotations

import argparse
import dataclasses
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Iterable

from app.data.article_existence import ARTICLE_EXISTENCE
from app.data.definitions import _DEFINITIONS
from app.data.eu_ai_act_corpus import (
    ARTICLE_FULL_TEXT,
    ARTICLE_TITLE,
    RECITALS,
    ARTICLE_CHAPTER as _ARTICLE_CHAPTER,
)
from app.data.kb import EC_CHECKER_OBLIGATION_MAP, KB_VERSION, MATURITY_DIMENSIONS
from app.data.article_requirements_full import DIMENSION_TO_ARTICLES
from app.data.kb_xrefs import MANUAL_XREFS, _build_xref_graph
# R291 — clean, SHA-pinned verbatim source (replaces the NBSP-laden Ansvar
# corpus for node prose) + the nesting-aware hierarchy builder + the ontology
# deontic layer.
from app.data.official_eu_ai_act import (
    OFFICIAL_ARTICLE_TITLES,
    OFFICIAL_ANNEX_TITLES,
    OFFICIAL_RECITAL_TEXT,
)
from app.data.lawstronaut_provenance import (
    OFFICIAL_CELEX as _OFFICIAL_CELEX,
    OFFICIAL_EFFECTIVE_DATE as _OFFICIAL_EFFECTIVE_DATE,
    OFFICIAL_ELI as _OFFICIAL_ELI,
    OFFICIAL_GUIDELINES as _OFFICIAL_GUIDELINES,
    OFFICIAL_LEGAL_LINK as _OFFICIAL_LEGAL_LINK,
    OFFICIAL_PORTAL as _OFFICIAL_PORTAL,
    OFFICIAL_TITLE as _OFFICIAL_TITLE,
)
from app.data.provision_text import article_body as _article_body
from app.data.provision_text import get_provision_text as _get_provision_text
from app.data.provision_hierarchy import (
    HierarchyPayload,
    build_hierarchy_payload,
)
from app.data.ontology import (
    ANNEX_III_REGISTRY,
    CONFORMITY_ROUTE_REGISTRY,
    FRIA_REGISTRY,
    GPAI_REGISTRY,
    PHASE_REGISTRY,
    PRACTICE_REGISTRY,
    RISK_CONTROL_REGISTRY,
    RISK_SCENARIO_REGISTRY,
    SERIOUS_INCIDENT_REGISTRY,
)

# ── SEED-02 fix: reconcile MATURITY_DIMENSIONS ids vs DIMENSION_TO_ARTICLES keys ──
# The upstream module uses 'conformity_assessment' but MATURITY_DIMENSIONS uses 'conformity'.
# The upstream module uses 'gpai' but MATURITY_DIMENSIONS uses 'gpai_specific'.
# We patch aliases into the imported dict so .get(dim.id, []) resolves correctly.
if "conformity_assessment" in DIMENSION_TO_ARTICLES:
    DIMENSION_TO_ARTICLES["conformity"] = DIMENSION_TO_ARTICLES["conformity_assessment"]
if "gpai" in DIMENSION_TO_ARTICLES:
    DIMENSION_TO_ARTICLES["gpai_specific"] = DIMENSION_TO_ARTICLES["gpai"]

# Dimensions that are genuinely cross-cutting and NOT pinned to specific articles —
# intentionally omitted from DIMENSION_TO_ARTICLES.
_INTENTIONALLY_UNMAPPED_DIMENSIONS: frozenset[str] = frozenset({
    "agent_inventory",      # cross-cutting inventory practice
    "chain_transparency",   # supply-chain transparency (no single article anchor)
    "governance",           # enterprise AI governance (cross-cutting)
    "post_market",          # post-market monitoring (cross-cutting Arts 72-75)
    "regulatory_perimeter", # scope determination (cross-cutting)
    "runtime_drift",        # MLOps/drift detection (cross-cutting)
    "tool_governance",      # tool and agent governance (cross-cutting)
})

# Import-time guard: every MATURITY_DIMENSIONS id must either appear in
# DIMENSION_TO_ARTICLES OR be declared intentionally unmapped.  If this
# assertion fires, add the new id to DIMENSION_TO_ARTICLES (preferred) or
# to _INTENTIONALLY_UNMAPPED_DIMENSIONS (if genuinely cross-cutting).
_unmapped_dims = {
    d.id
    for d in MATURITY_DIMENSIONS
    if d.id not in DIMENSION_TO_ARTICLES
    and d.id not in _INTENTIONALLY_UNMAPPED_DIMENSIONS
}
assert not _unmapped_dims, (
    f"DIMENSION_TO_ARTICLES is missing entries for MATURITY_DIMENSIONS ids: "
    f"{sorted(_unmapped_dims)}.  Add entries to DIMENSION_TO_ARTICLES or to "
    "_INTENTIONALLY_UNMAPPED_DIMENSIONS in scripts/seed_neo4j_kb.py."
)
from app.data.role_obligations import ROLE_OBLIGATIONS
from app.integrations.regenold.refs import to_user_facing as _ref_to_user_facing

logger = logging.getLogger(__name__)


# ─── Seed pin ─────────────────────────────────────────────────────────────

#: Bumped on each material change to the seeded shape (added node label,
#: new edge type, removed source, etc.). Surfaces in the ``KBMetadata``
#: node so consumers can detect a graph that's stale relative to the
#: currently-running code.
SEED_VERSION = "2026-08-14-sota-airo-fullseed"

#: Cap on per-transaction batch size to stay well clear of the Neo4j
#: 4194304-byte default transaction limit. The shape of our payloads
#: (short string properties, no embedded blobs) means 500 rows is well
#: under any realistic cap.
BATCH_SIZE = 500


# ─── Risk levels (closed taxonomy used by the engine) ─────────────────────

RISK_LEVELS: tuple[dict[str, str], ...] = (
    {
        "id": "risk_prohibited",
        "label": "prohibited",
        "description": (
            "Art. 5 prohibited AI practices. No conformity-assessment path "
            "exists; placement on the market or putting into service is "
            "outright banned."
        ),
    },
    {
        "id": "risk_high",
        "label": "high-risk",
        "description": (
            "Annex I safety-component + Annex III use-case high-risk "
            "systems per Art. 6. Trigger Arts. 9-15 essential requirements, "
            "Art. 43 conformity assessment, Art. 47 EU declaration, Art. 49 "
            "database registration."
        ),
    },
    {
        "id": "risk_limited",
        "label": "limited",
        "description": (
            "Transparency-only obligations under Art. 50 (chatbots, "
            "deepfakes, biometric categorisation, emotion recognition where "
            "permitted, AI-generated content disclosure)."
        ),
    },
    {
        "id": "risk_minimal",
        "label": "minimal",
        "description": (
            "Out-of-scope systems carrying voluntary code-of-conduct "
            "obligations only (Art. 95). Art. 4 AI literacy still applies "
            "to providers / deployers."
        ),
    },
)


# ─── Helpers ─────────────────────────────────────────────────────────────


_ART_NUMBER_RE = re.compile(r"^Art\.\s*(\d{1,3})$")
_ANNEX_NUMBER_RE = re.compile(r"^Annex\s+([IVXLC]+)$", re.IGNORECASE)


def _slug_term(term: str) -> str:
    """Normalise an Art. 3 term into a deterministic ID slug."""
    s = term.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s or "anon"


def _article_id(ref: str) -> str:
    """Map ``"Art. 5"`` → ``"article_5"``, ``"Annex III"`` → ``"annex_III"``."""
    m = _ART_NUMBER_RE.match(ref)
    if m:
        return f"article_{m.group(1)}"
    m = _ANNEX_NUMBER_RE.match(ref)
    if m:
        return f"annex_{m.group(1).upper()}"
    # Defensive: pass through untouched so a bad caller crashes loud.
    return ref.replace(" ", "_").replace(".", "")


def _article_number(ref: str) -> str:
    """Return the bare number / roman from a reference."""
    m = _ART_NUMBER_RE.match(ref)
    if m:
        return m.group(1)
    m = _ANNEX_NUMBER_RE.match(ref)
    if m:
        return m.group(1).upper()
    return ref


def _is_annex(ref: str) -> bool:
    return bool(_ANNEX_NUMBER_RE.match(ref))


def _short_title(ref: str) -> str:
    """Pull a usable title for an article / annex."""
    title = ARTICLE_TITLE.get(ref)
    if title:
        # Strip the NBSP runs the corpus is dotted with so the property
        # stays readable in Neo4j Browser. Pure cleanup, no semantic change.
        return title.replace("\xa0", " ").strip()
    # Fall back to first sentence of the full text, capped.
    body = ARTICLE_FULL_TEXT.get(ref, "")
    if body:
        first = re.split(r"(?<=[.!?])\s", body, maxsplit=1)[0]
        first = first.replace("\xa0", " ").strip()
        return first[:200]
    return ref


def _official_title(long_key: str) -> str:
    """Clean official title for ``Article N`` / ``Annex X``, else ``""``.

    Prefers the SHA-pinned ``OFFICIAL_*_TITLES``; strips the stray trailing
    backtick a couple of pinned entries carry (e.g. ``"Subject matter`"``)
    and NBSP runs so the node property is readable.
    """
    title = OFFICIAL_ARTICLE_TITLES.get(long_key) or OFFICIAL_ANNEX_TITLES.get(long_key)
    if not title:
        return ""
    return title.replace("\xa0", " ").strip().rstrip("`").strip()


def _classify_risk_for_article(num: str) -> str | None:
    """Return the RiskLevel ID an obligation under article ``num`` applies at.

    Closed mapping per the brief: Art. 5 → prohibited, Arts. 6-49 (the
    high-risk obligation cluster) → high-risk, Art. 50 → limited, Art. 4
    → minimal. Outside that band we return ``None`` and skip the edge —
    silence beats over-claiming.
    """
    try:
        n = int(num)
    except (TypeError, ValueError):
        return None
    if n == 5:
        return "risk_prohibited"
    if n == 4:
        return "risk_minimal"
    if n == 50:
        return "risk_limited"
    if 6 <= n <= 49:
        return "risk_high"
    return None


# ─── Seed-payload builder (pure, side-effect-free) ────────────────────────


@dataclasses.dataclass(frozen=True)
class SeedPayload:
    """Everything we want to push, grouped by Cypher template.

    Each entry is ``(label/relType, list[dict] of parameters)``. The
    runner translates these into ``MERGE`` Cypher and batches the writes;
    the dry-run path counts them and returns.
    """

    article_nodes: list[dict]
    annex_nodes: list[dict]
    recital_nodes: list[dict]
    definition_nodes: list[dict]
    obligation_nodes: list[dict]
    annex_iii_nodes: list[dict]
    risk_level_nodes: list[dict]
    operator_role_nodes: list[dict]
    metadata_node: dict

    has_obligation_edges: list[dict]
    has_definition_edges: list[dict]
    cross_reference_edges: list[dict]
    has_recital_anchor_edges: list[dict]
    triggers_high_risk_edges: list[dict]
    applies_at_edges: list[dict]
    # Fields added in d4a8fb3 (maturity Dimensions + Questions).
    # Default to empty list so existing direct SeedPayload() constructors
    # (e.g. in tests) that don't supply them continue to work.
    dimension_nodes: list[dict] = dataclasses.field(default_factory=list)
    question_nodes: list[dict] = dataclasses.field(default_factory=list)
    belongs_to_edges: list[dict] = dataclasses.field(default_factory=list)
    assesses_edges: list[dict] = dataclasses.field(default_factory=list)
    # R291 — ontology deontic layer + provision hierarchy. All default-empty
    # so pre-R291 direct SeedPayload() constructors keep working.
    practice_nodes: list[dict] = dataclasses.field(default_factory=list)
    phase_nodes: list[dict] = dataclasses.field(default_factory=list)
    legal_instrument_nodes: list[dict] = dataclasses.field(default_factory=list)
    guideline_nodes: list[dict] = dataclasses.field(default_factory=list)
    prohibited_under_edges: list[dict] = dataclasses.field(default_factory=list)
    applies_to_phase_edges: list[dict] = dataclasses.field(default_factory=list)
    has_obligation_article_edges: list[dict] = dataclasses.field(default_factory=list)
    has_provenance_edges: list[dict] = dataclasses.field(default_factory=list)
    interprets_edges: list[dict] = dataclasses.field(default_factory=list)
    # SOTA AIRO & EU AI Act Governance layers
    risk_scenario_nodes: list[dict] = dataclasses.field(default_factory=list)
    risk_control_nodes: list[dict] = dataclasses.field(default_factory=list)
    gpai_profile_nodes: list[dict] = dataclasses.field(default_factory=list)
    conformity_route_nodes: list[dict] = dataclasses.field(default_factory=list)
    fria_workflow_nodes: list[dict] = dataclasses.field(default_factory=list)
    serious_incident_nodes: list[dict] = dataclasses.field(default_factory=list)
    requires_control_edges: list[dict] = dataclasses.field(default_factory=list)
    violates_edges: list[dict] = dataclasses.field(default_factory=list)
    governed_by_edges: list[dict] = dataclasses.field(default_factory=list)
    hierarchy: "HierarchyPayload | None" = None

    def _hier_counts(self) -> dict[str, int]:
        if self.hierarchy is None:
            return {
                "Paragraph": 0, "Point": 0, "SubPoint": 0,
                "HAS_PARAGRAPH": 0, "HAS_POINT": 0, "HAS_SUBPOINT": 0,
            }
        return self.hierarchy.counts()

    @property
    def total_nodes(self) -> int:
        h = self._hier_counts()
        return (
            len(self.article_nodes)
            + len(self.annex_nodes)
            + len(self.recital_nodes)
            + len(self.definition_nodes)
            + len(self.obligation_nodes)
            + len(self.annex_iii_nodes)
            + len(self.risk_level_nodes)
            + len(self.operator_role_nodes)
            + len(self.dimension_nodes)
            + len(self.question_nodes)
            + len(self.practice_nodes)
            + len(self.phase_nodes)
            + len(self.legal_instrument_nodes)
            + len(self.guideline_nodes)
            + len(self.risk_scenario_nodes)
            + len(self.risk_control_nodes)
            + len(self.gpai_profile_nodes)
            + len(self.conformity_route_nodes)
            + len(self.fria_workflow_nodes)
            + len(self.serious_incident_nodes)
            + h["Paragraph"] + h["Point"] + h["SubPoint"]
            + 1  # metadata
        )

    @property
    def total_edges(self) -> int:
        h = self._hier_counts()
        return (
            len(self.has_obligation_edges)
            + len(self.has_definition_edges)
            + len(self.cross_reference_edges)
            + len(self.has_recital_anchor_edges)
            + len(self.triggers_high_risk_edges)
            + len(self.applies_at_edges)
            + len(self.belongs_to_edges)
            + len(self.assesses_edges)
            + len(self.prohibited_under_edges)
            + len(self.applies_to_phase_edges)
            + len(self.has_obligation_article_edges)
            + len(self.has_provenance_edges)
            + len(self.interprets_edges)
            + len(self.requires_control_edges)
            + len(self.violates_edges)
            + len(self.governed_by_edges)
            + h["HAS_PARAGRAPH"] + h["HAS_POINT"] + h["HAS_SUBPOINT"]
        )

    def counts(self) -> dict[str, int]:
        out = {
            "Article": len(self.article_nodes),
            "Annex": len(self.annex_nodes),
            "Recital": len(self.recital_nodes),
            "Definition": len(self.definition_nodes),
            "Obligation": len(self.obligation_nodes),
            "AnnexIIICategory": len(self.annex_iii_nodes),
            "RiskLevel": len(self.risk_level_nodes),
            "OperatorRole": len(self.operator_role_nodes),
            "Dimension": len(self.dimension_nodes),
            "Question": len(self.question_nodes),
            "Practice": len(self.practice_nodes),
            "LifecyclePhase": len(self.phase_nodes),
            "LegalInstrument": len(self.legal_instrument_nodes),
            "Guideline": len(self.guideline_nodes),
            "RiskScenario": len(self.risk_scenario_nodes),
            "RiskControl": len(self.risk_control_nodes),
            "GPAIModelProfile": len(self.gpai_profile_nodes),
            "ConformityRoute": len(self.conformity_route_nodes),
            "FRIAWorkflow": len(self.fria_workflow_nodes),
            "SeriousIncidentSLA": len(self.serious_incident_nodes),
            "KBMetadata": 1,
            "HAS_OBLIGATION": len(self.has_obligation_edges),
            "HAS_DEFINITION": len(self.has_definition_edges),
            "CROSS_REFERENCES": len(self.cross_reference_edges),
            "HAS_RECITAL_ANCHOR": len(self.has_recital_anchor_edges),
            "TRIGGERS_HIGH_RISK_UNDER": len(self.triggers_high_risk_edges),
            "APPLIES_AT": len(self.applies_at_edges),
            "BELONGS_TO": len(self.belongs_to_edges),
            "ASSESSES": len(self.assesses_edges),
            "PROHIBITED_UNDER": len(self.prohibited_under_edges),
            "APPLIES_TO": len(self.applies_to_phase_edges),
            "HAS_OBLIGATION_ARTICLE": len(self.has_obligation_article_edges),
            "HAS_PROVENANCE": len(self.has_provenance_edges),
            "INTERPRETS": len(self.interprets_edges),
            "REQUIRES_CONTROL": len(self.requires_control_edges),
            "VIOLATES": len(self.violates_edges),
            "GOVERNED_BY": len(self.governed_by_edges),
        }
        # NOTE: the Paragraph/Point/SubPoint hierarchy is intentionally NOT in
        # ``counts()`` — that dict is the per-label write ledger ``seed_graph``
        # returns and ``test_seed_graph_writes_every_payload_row`` pins to it.
        # The hierarchy is written by the fail-soft ``_ingest_legal_ast_hierarchy``
        # step (so a hierarchy hiccup can't abort the base seed) and is counted
        # separately (see ``hierarchy_counts`` + the dry-run print). It IS folded
        # into ``total_nodes`` / ``total_edges`` for the KBMetadata totals.
        return out

    def hierarchy_counts(self) -> dict[str, int]:
        """Paragraph/Point/SubPoint counts — the separate hierarchy ledger."""
        return self._hier_counts()


def build_payload() -> SeedPayload:
    """Build the full seed payload from the in-process KB modules.

    Pure function — no I/O, no driver use. Suitable for tests and for the
    ``--dry-run`` accounting pass.
    """
    # ── Articles (113) ────────────────────────────────────────────────
    # R84-C: every Article node carries ``legal_type="Article"`` + the
    # ``strict_citation`` shape ``"Article N"`` per the CLAUDE.md hard
    # rule #1. Derived from the canonical internal form via the single-
    # source-of-truth converter at ``refs.to_user_facing``. Sub-point
    # nodes (``Art. 13(2)(a)``) are NOT seeded today — base nodes only,
    # so ``strict_citation`` is always the bare ``"Article N"`` form.
    article_nodes: list[dict] = []
    for ref in sorted(
        (r for r in ARTICLE_EXISTENCE if r.startswith("Art. ")),
        key=lambda r: int(_article_number(r)),
    ):
        num = _article_number(ref)
        long_key = f"Article {num}"
        # R291 — FULL, untruncated, CLEAN verbatim body from the SHA-pinned
        # official source (was ``ARTICLE_FULL_TEXT[ref][:2000]`` — Ansvar
        # NBSP-laden + truncated at 2000, dropping ~145K chars of statute).
        full_text = _article_body(long_key) or ARTICLE_FULL_TEXT.get(ref, "")
        article_nodes.append(
            {
                "id": _article_id(ref),
                "number": num,
                "title": _official_title(long_key) or _short_title(ref),
                # ``text`` is the first-class full-body property; ``description``
                # kept (now also full + clean) for any legacy reader.
                "text": full_text,
                "description": full_text,
                "chapter": _ARTICLE_CHAPTER.get(ref) or "",
                "vector_chunk_ids": [],
                "legal_type": "Article",
                "strict_citation": _ref_to_user_facing(f"Art. {num}"),
                "celex_id": _OFFICIAL_CELEX,
                "eli_uri": _OFFICIAL_ELI,
                "legal_link": _OFFICIAL_LEGAL_LINK,
            }
        )

    # ── Annexes (13) ──────────────────────────────────────────────────
    # R84-C: every Annex node carries ``legal_type="Annex"`` + the
    # ``strict_citation`` shape ``"Annex X"`` (Roman uppercased) per the
    # CLAUDE.md hard rule #1.
    annex_nodes: list[dict] = []
    for ref in sorted(r for r in ARTICLE_EXISTENCE if r.startswith("Annex ")):
        roman = _article_number(ref)
        long_key = f"Annex {roman}"
        full_text = _article_body(long_key) or ARTICLE_FULL_TEXT.get(ref, "")
        annex_nodes.append(
            {
                "id": _article_id(ref),
                "number": roman,
                "title": _official_title(long_key) or _short_title(ref),
                "text": full_text,
                "description": full_text,
                "legal_type": "Annex",
                "strict_citation": _ref_to_user_facing(f"Annex {roman}"),
                "celex_id": _OFFICIAL_CELEX,
                "eli_uri": _OFFICIAL_ELI,
                "legal_link": _OFFICIAL_LEGAL_LINK,
            }
        )

    # ── Recitals (180) ────────────────────────────────────────────────
    recital_nodes: list[dict] = []
    for n in sorted(RECITALS.keys()):
        # R291 — full, untruncated recital from the SHA-pinned official source
        # (was ``RECITALS[n][:3000]``). Fall back to the Ansvar corpus text.
        raw = OFFICIAL_RECITAL_TEXT.get(n) or RECITALS[n]
        text = raw.replace("\xa0", " ").strip()
        recital_nodes.append(
            {
                "id": f"recital_{n}",
                "number": str(n),
                "text": text,
            }
        )

    # ── Definitions (Art. 3 catalogue) ────────────────────────────────
    definition_nodes: list[dict] = []
    has_definition_edges: list[dict] = []
    for defn in _DEFINITIONS:
        slug = _slug_term(defn.term)
        def_id = f"def_{slug}"
        # R291 — verbatim Art. 3 wording (matches the graph_aware
        # ``lookup_definition_by_term`` "canonical Art. 3 wording verbatim"
        # contract). ``defn.citation`` is ``Art. 3.N``; resolve it to the
        # official text, falling back to the hand-curated description.
        verbatim = _get_provision_text(defn.citation) or defn.description
        definition_nodes.append(
            {
                "id": def_id,
                "kind": "Definition",
                "term": defn.term,
                "citation": defn.citation,
                "text": verbatim,
            }
        )
        has_definition_edges.append(
            {
                "source_id": _article_id("Art. 3"),
                "target_id": def_id,
            }
        )

    # ── Obligations (one per KB stub row) ─────────────────────────────
    obligation_nodes: list[dict] = []
    has_obligation_edges: list[dict] = []
    applies_at_edges: list[dict] = []
    for ref, entry in EC_CHECKER_OBLIGATION_MAP.items():
        # Skip annex rows — those land as Annex nodes already and don't
        # carry an article-style obligation in the graph schema.
        if _is_annex(ref):
            continue
        if ref not in ARTICLE_EXISTENCE:
            # Defensive — the lint floor should already catch this.
            continue
        num = _article_number(ref)
        obl_id = f"obl_{num}"
        obligation_nodes.append(
            {
                "id": obl_id,
                "article_ref": num,
                "text": entry.get("summary", "")[:3000],
                "mandatory": True,
                "paragraph_ref": "",
                "dimension": entry.get("dimension", ""),
            }
        )
        has_obligation_edges.append(
            {
                "source_id": _article_id(ref),
                "target_id": obl_id,
            }
        )
        risk_id = _classify_risk_for_article(num)
        if risk_id is not None:
            applies_at_edges.append(
                {
                    "source_id": obl_id,
                    "target_id": risk_id,
                }
            )

    # ── Annex III categories (8) ──────────────────────────────────────
    annex_iii_nodes: list[dict] = []
    triggers_high_risk_edges: list[dict] = []
    for cat_id, cat in ANNEX_III_REGISTRY.items():
        node_id = f"annex_iii_{cat_id}"
        annex_iii_nodes.append(
            {
                "id": node_id,
                "label": cat.short_name,
                "number": cat.number,
                "description": cat.description[:2000],
            }
        )
        triggers_high_risk_edges.append(
            {
                "source_id": node_id,
                "target_id": _article_id("Art. 6"),
            }
        )

    # ── Risk levels (4) ───────────────────────────────────────────────
    risk_level_nodes: list[dict] = [dict(row) for row in RISK_LEVELS]

    # ── Operator roles (canonical 5 — provider/deployer/importer/
    # distributor/authorised_representative). The role_obligations table
    # carries additional modifier roles (GPAI, extraterritorial,
    # small_mid_cap) that aren't part of the closed Layer-1 NLF role set.
    operator_role_nodes: list[dict] = []
    canonical = {
        "provider",
        "deployer",
        "importer",
        "distributor",
        "authorized_representative",
    }
    for row in ROLE_OBLIGATIONS:
        if row.get("id") not in canonical:
            continue
        operator_role_nodes.append(
            {
                "id": f"role_{row['id']}",
                "label": row.get("label", row["id"]),
                "art_3_definition": row.get("art_3_definition", ""),
                "summary": row.get("summary", "")[:1500],
            }
        )

    # ── Dimensions and Questions ──────────────────────────────────────
    dimension_nodes: list[dict] = []
    question_nodes: list[dict] = []
    belongs_to_edges: list[dict] = []
    assesses_edges: list[dict] = []

    for dim in MATURITY_DIMENSIONS:
        dimension_nodes.append({
            "id": dim.id,
            "name": dim.label,
        })
        for i, q_text in enumerate(dim.questions):
            q_id = f"q_{dim.id}_{i}"
            question_nodes.append({
                "id": q_id,
                "text": q_text,
                "weight": 1.0,
            })
            belongs_to_edges.append({
                "source_id": q_id,
                "target_id": dim.id,
            })
            
            # Map question to obligations via articles
            articles = DIMENSION_TO_ARTICLES.get(dim.id, [])
            for art_ref in articles:
                if art_ref in ARTICLE_EXISTENCE:
                    num = _article_number(art_ref)
                    obl_id = f"obl_{num}"
                    if art_ref in EC_CHECKER_OBLIGATION_MAP and not _is_annex(art_ref):
                        assesses_edges.append({
                            "source_id": q_id,
                            "target_id": obl_id,
                        })

    # ── Cross-reference edges (regex + manual). Build directly off the
    # merged xref graph so the seeder picks up future edge additions
    # automatically. We tag the source — regex vs manual — for forensic
    # traceability.
    xref_graph = _build_xref_graph()
    manual_pairs: set[tuple[str, str]] = {
        (s, t) for s, t, _ in MANUAL_XREFS
    }
    cross_reference_edges: list[dict] = []
    for source_ref, targets in xref_graph.items():
        if source_ref not in ARTICLE_EXISTENCE:
            continue
        for target_ref in targets:
            if target_ref not in ARTICLE_EXISTENCE:
                continue
            if source_ref == target_ref:
                continue
            cross_reference_edges.append(
                {
                    "source_id": _article_id(source_ref),
                    "target_id": _article_id(target_ref),
                    "edge_source": (
                        "manual" if (source_ref, target_ref) in manual_pairs
                        else "regex"
                    ),
                }
            )

    # ── Recital-anchor edges: pull explicit "Recital N" mentions out of
    # the obligation summaries. Cheap regex pass — the corpus uses the
    # form ``Recital 85`` consistently when it refers back to a recital.
    recital_re = re.compile(r"\bRecital\s+(\d{1,3})\b", re.IGNORECASE)
    has_recital_anchor_edges: list[dict] = []
    seen_recital_edges: set[tuple[str, str]] = set()
    for ref, entry in EC_CHECKER_OBLIGATION_MAP.items():
        if ref not in ARTICLE_EXISTENCE:
            continue
        summary = entry.get("summary", "")
        if not summary:
            continue
        for match in recital_re.finditer(summary):
            n = int(match.group(1))
            if n not in RECITALS:
                continue
            edge_key = (_article_id(ref), f"recital_{n}")
            if edge_key in seen_recital_edges:
                continue
            seen_recital_edges.add(edge_key)
            has_recital_anchor_edges.append(
                {
                    "source_id": edge_key[0],
                    "target_id": edge_key[1],
                }
            )

    # ── Ontology deontic layer (R291) — the semantic-layer mirror ─────
    #
    # The high-risk half of the risk pyramid was already seeded
    # (AnnexIIICategory -[:TRIGGERS_HIGH_RISK_UNDER]-> Art. 6). R291 adds the
    # prohibited half + the operator-role obligation edges + the applicability
    # timeline, so the graph is a faithful mirror of ``app/data/ontology.py``
    # and ``app/data/role_obligations.py`` rather than a fraction of them.
    # Every edge endpoint is a BASE Article node (never a sub-point) so
    # ``validate_payload`` keeps a flat, checkable node set.

    def _existing_article_id(short_ref: str) -> str | None:
        base = short_ref.split("(")[0].strip()
        if not base.startswith("Art. "):
            return None
        # Normalise ``Art. 5.1.a`` → ``Art. 5``.
        base = "Art. " + base[len("Art. "):].split(".")[0].strip()
        return _article_id(base) if base in ARTICLE_EXISTENCE else None

    # Practice nodes (the 8 Art. 5 prohibited practices) + PROHIBITED_UNDER.
    practice_nodes: list[dict] = []
    prohibited_under_edges: list[dict] = []
    for pid, practice in PRACTICE_REGISTRY.items():
        node_id = f"practice_{pid}"
        practice_nodes.append(
            {
                "id": node_id,
                "short_name": getattr(practice, "short_name", pid),
                "sub_paragraph": getattr(practice, "sub_paragraph", ""),
                "description": (getattr(practice, "description", "") or ""),
            }
        )
        # ``practice.citation`` is ``('Art. 5', 'Art. 5.1.a')`` — anchor the
        # base article (Art. 5).
        citation = getattr(practice, "citation", ()) or ()
        base_ref = citation[0] if citation else "Art. 5"
        target = _existing_article_id(base_ref)
        if target is not None:
            prohibited_under_edges.append(
                {"source_id": node_id, "target_id": target}
            )

    # LifecyclePhase nodes (applicability timeline) + APPLIES_TO.
    phase_nodes: list[dict] = []
    applies_to_phase_edges: list[dict] = []
    for pid, phase in PHASE_REGISTRY.items():
        node_id = f"phase_{pid}" if not pid.startswith("phase_") else pid
        eff = getattr(phase, "effective_date", None)
        phase_nodes.append(
            {
                "id": node_id,
                "label": getattr(phase, "label", pid),
                "effective_date": eff.isoformat() if eff else "",
                "superseded_by": getattr(phase, "superseded_by", None) or "",
            }
        )
        for art_ref in getattr(phase, "articles", ()) or ():
            target = _existing_article_id(art_ref)
            if target is not None:
                applies_to_phase_edges.append(
                    {"source_id": node_id, "target_id": target}
                )

    # OperatorRole -[:HAS_OBLIGATION_ARTICLE {tier}]-> Article. Connects the
    # currently-orphan role nodes to their obligation articles. Only the 5
    # canonical roles were seeded as nodes (see above), so only those get
    # edges.
    seeded_role_ids = {n["id"] for n in operator_role_nodes}
    has_obligation_article_edges: list[dict] = []
    seen_role_edges: set[tuple[str, str, str]] = set()
    for row in ROLE_OBLIGATIONS:
        role_node = f"role_{row['id']}"
        if role_node not in seeded_role_ids:
            continue
        for tier, key in (("primary", "primary_articles"), ("secondary", "secondary_articles")):
            for art_ref in row.get(key, []) or []:
                target = _existing_article_id(art_ref)
                if target is None:
                    continue
                ek = (role_node, target, tier)
                if ek in seen_role_edges:
                    continue
                seen_role_edges.add(ek)
                has_obligation_article_edges.append(
                    {"source_id": role_node, "target_id": target, "tier": tier}
                )

    # ── Legal provenance & official guidance (Lawstronaut, pinned) ────
    #
    # Every value below comes from ``app.data.lawstronaut_provenance``, which
    # ``scripts/fetch_lawstronaut_provenance.py`` live-fetches and pins. The
    # first cut hardcoded CELEX 02024R1689-20260727 — the POST-Digital-Omnibus
    # consolidation — onto all 126 Article/Annex nodes while the seeded TEXT is
    # the pre-Omnibus original. Sourcing from the pin makes the stamp match the
    # text and makes a future version bump a single re-fetch.
    legal_instrument_nodes = [
        {
            "id": "legal_instrument_eu_ai_act",
            "celex_id": _OFFICIAL_CELEX,
            "eli_uri": _OFFICIAL_ELI,
            "title": _OFFICIAL_TITLE,
            "portal_name": _OFFICIAL_PORTAL,
            "effective_date": _OFFICIAL_EFFECTIVE_DATE,
            "legal_link": _OFFICIAL_LEGAL_LINK,
        }
    ]

    # A Commission guideline is soft law interpreting the act — NOT the act.
    # It therefore carries its own identity plus the CELEX of what it
    # interprets, never the act's CELEX as its own identifier.
    guideline_nodes = [
        {
            "id": str(g["id"]),
            "title": str(g["title"]),
            "issuing_authority": str(g["issuing_authority"]),
            "doc_id": int(g["doc_id"]),
            "legal_link": str(g["legal_link"]),
            "interprets_celex": _OFFICIAL_CELEX,
        }
        for g in _OFFICIAL_GUIDELINES
    ]

    has_provenance_edges = [
        {"source_id": node["id"], "target_id": "legal_instrument_eu_ai_act"}
        for node in (*article_nodes, *annex_nodes)
    ]

    # Guideline → Article edges, derived from the pinned registry rather than
    # hand-listed, and existence-gated so a stale doc registry cannot seed an
    # edge into a provision that does not exist.
    _article_ids = {node["id"] for node in article_nodes}
    interprets_edges = []
    for g in _OFFICIAL_GUIDELINES:
        for ref in g["interprets"]:
            num = str(ref).replace("Art.", "").strip()
            target = f"article_{num}"
            if target in _article_ids:
                interprets_edges.append(
                    {"source_id": str(g["id"]), "target_id": target}
                )

    # ── SOTA AIRO & EU AI Act Governance Entities ──────────────────────
    def _existing_target_id(short_ref: str) -> str | None:
        raw = short_ref.split("(")[0].strip()
        if raw.startswith("Art. "):
            base = "Art. " + raw[len("Art. "):].split(".")[0].strip()
            return _article_id(base) if base in ARTICLE_EXISTENCE else None
        elif raw.startswith("Annex "):
            m = _ANNEX_NUMBER_RE.match(raw)
            if m:
                annex_ref = f"Annex {m.group(1).upper()}"
                return _article_id(annex_ref) if annex_ref in ARTICLE_EXISTENCE else None
        return None

    # RiskScenario nodes
    risk_scenario_nodes = [
        {
            "id": s.id,
            "short_name": s.short_name,
            "hazard_or_threat": s.hazard_or_threat,
            "vulnerability": s.vulnerability,
            "risk_event": s.risk_event,
            "impact_area": s.impact_area,
            "severity_level": s.severity_level,
            "statutory_violation": list(s.statutory_violation),
            "description": s.description,
            "keywords": list(s.keywords),
        }
        for s in RISK_SCENARIO_REGISTRY.values()
    ]

    # RiskControl nodes
    risk_control_nodes = [
        {
            "id": c.id,
            "name": c.name,
            "control_type": c.control_type,
            "lifecycle_phase": c.lifecycle_phase,
            "mitigates_risk_id": c.mitigates_risk_id,
            "evidenced_by": list(c.evidenced_by),
            "standards_ref": list(c.standards_ref),
            "articles": list(c.articles),
            "description": c.description,
            "keywords": list(c.keywords),
        }
        for c in RISK_CONTROL_REGISTRY.values()
    ]

    # GPAIModelProfile nodes
    gpai_profile_nodes = [
        {
            "id": g.id,
            "model_name": g.model_name,
            "training_compute_flops": float(g.training_compute_flops),
            "is_open_source": bool(g.is_open_source),
            "has_systemic_risk": bool(g.has_systemic_risk),
            "mandatory_obligations": list(g.mandatory_obligations),
            "technical_doc_annex": g.technical_doc_annex,
            "downstream_info_annex": g.downstream_info_annex,
            "description": g.description,
            "keywords": list(g.keywords),
        }
        for g in GPAI_REGISTRY.values()
    ]

    # ConformityRoute nodes
    conformity_route_nodes = [
        {
            "id": cr.id,
            "route_type": cr.route_type.value if hasattr(cr.route_type, "value") else str(cr.route_type),
            "governing_articles": list(cr.governing_articles),
            "applicable_annex": cr.applicable_annex,
            "requires_notified_body": bool(cr.requires_notified_body),
            "description": cr.description,
            "keywords": list(cr.keywords),
        }
        for cr in CONFORMITY_ROUTE_REGISTRY.values()
    ]

    # FRIAWorkflow nodes
    fria_workflow_nodes = [
        {
            "id": f.id,
            "deployer_category": f.deployer_category,
            "governing_articles": list(f.governing_articles),
            "required_steps": list(f.required_steps),
            "mandatory_reporting_authority": f.mandatory_reporting_authority,
            "description": f.description,
            "keywords": list(f.keywords),
        }
        for f in FRIA_REGISTRY.values()
    ]

    # SeriousIncidentSLA nodes
    serious_incident_nodes = [
        {
            "id": i.id,
            "incident_type": i.incident_type,
            "deadline_hours": int(i.deadline_hours),
            "statutory_basis": list(i.statutory_basis),
            "qms_update_required": bool(i.qms_update_required),
            "description": i.description,
            "keywords": list(i.keywords),
        }
        for i in SERIOUS_INCIDENT_REGISTRY.values()
    ]

    # REQUIRES_CONTROL edges (RiskScenario -> RiskControl)
    requires_control_edges: list[dict] = []
    for s in RISK_SCENARIO_REGISTRY.values():
        for ctrl_id in s.required_controls:
            if ctrl_id in RISK_CONTROL_REGISTRY:
                requires_control_edges.append({
                    "source_id": s.id,
                    "target_id": ctrl_id,
                })

    # VIOLATES edges (RiskScenario -> Article/Annex)
    violates_edges: list[dict] = []
    seen_violates: set[tuple[str, str]] = set()
    for s in RISK_SCENARIO_REGISTRY.values():
        for ref in s.statutory_violation:
            target = _existing_target_id(ref)
            if target is not None:
                pair = (s.id, target)
                if pair not in seen_violates:
                    seen_violates.add(pair)
                    violates_edges.append({
                        "source_id": s.id,
                        "target_id": target,
                    })

    # GOVERNED_BY edges (RiskControl/GPAI/Conformity/FRIA/Incident -> Article/Annex)
    governed_by_edges: list[dict] = []
    seen_governed: set[tuple[str, str]] = set()

    for c in RISK_CONTROL_REGISTRY.values():
        for ref in c.articles:
            target = _existing_target_id(ref)
            if target is not None:
                pair = (c.id, target)
                if pair not in seen_governed:
                    seen_governed.add(pair)
                    governed_by_edges.append({
                        "source_id": c.id,
                        "target_id": target,
                    })

    for g in GPAI_REGISTRY.values():
        for ref in g.mandatory_obligations:
            target = _existing_target_id(ref)
            if target is not None:
                pair = (g.id, target)
                if pair not in seen_governed:
                    seen_governed.add(pair)
                    governed_by_edges.append({
                        "source_id": g.id,
                        "target_id": target,
                    })

    for cr in CONFORMITY_ROUTE_REGISTRY.values():
        for ref in cr.governing_articles:
            target = _existing_target_id(ref)
            if target is not None:
                pair = (cr.id, target)
                if pair not in seen_governed:
                    seen_governed.add(pair)
                    governed_by_edges.append({
                        "source_id": cr.id,
                        "target_id": target,
                    })

    for f in FRIA_REGISTRY.values():
        for ref in f.governing_articles:
            target = _existing_target_id(ref)
            if target is not None:
                pair = (f.id, target)
                if pair not in seen_governed:
                    seen_governed.add(pair)
                    governed_by_edges.append({
                        "source_id": f.id,
                        "target_id": target,
                    })

    for i in SERIOUS_INCIDENT_REGISTRY.values():
        for ref in i.statutory_basis:
            target = _existing_target_id(ref)
            if target is not None:
                pair = (i.id, target)
                if pair not in seen_governed:
                    seen_governed.add(pair)
                    governed_by_edges.append({
                        "source_id": i.id,
                        "target_id": target,
                    })

    # ── Provision hierarchy (Article/Annex → Paragraph → Point → SubPoint) ─
    # Folded into the payload so ``--dry-run`` accounts for the FULL graph
    # (the R290 audit's G4 gap: the hierarchy previously wrote ~⅓ of the
    # nodes only in the live branch, so dry-run under-reported).
    hierarchy = build_hierarchy_payload()

    # ── KBMetadata ────────────────────────────────────────────────────
    metadata_node = {
        "id": "kb_metadata",
        "seed_version": SEED_VERSION,
        "kb_version": KB_VERSION,
        "seeded_at": datetime.now(timezone.utc).isoformat(),
        # total_nodes / total_edges are filled in after the SeedPayload
        # is built (chicken-and-egg) — see ``_finalise_metadata`` below.
        "total_nodes": 0,
        "total_edges": 0,
    }

    payload = SeedPayload(
        article_nodes=article_nodes,
        annex_nodes=annex_nodes,
        recital_nodes=recital_nodes,
        definition_nodes=definition_nodes,
        obligation_nodes=obligation_nodes,
        annex_iii_nodes=annex_iii_nodes,
        risk_level_nodes=risk_level_nodes,
        operator_role_nodes=operator_role_nodes,
        dimension_nodes=dimension_nodes,
        question_nodes=question_nodes,
        practice_nodes=practice_nodes,
        phase_nodes=phase_nodes,
        legal_instrument_nodes=legal_instrument_nodes,
        guideline_nodes=guideline_nodes,
        risk_scenario_nodes=risk_scenario_nodes,
        risk_control_nodes=risk_control_nodes,
        gpai_profile_nodes=gpai_profile_nodes,
        conformity_route_nodes=conformity_route_nodes,
        fria_workflow_nodes=fria_workflow_nodes,
        serious_incident_nodes=serious_incident_nodes,
        metadata_node=metadata_node,
        has_obligation_edges=has_obligation_edges,
        has_definition_edges=has_definition_edges,
        cross_reference_edges=cross_reference_edges,
        has_recital_anchor_edges=has_recital_anchor_edges,
        triggers_high_risk_edges=triggers_high_risk_edges,
        applies_at_edges=applies_at_edges,
        belongs_to_edges=belongs_to_edges,
        assesses_edges=assesses_edges,
        prohibited_under_edges=prohibited_under_edges,
        has_provenance_edges=has_provenance_edges,
        interprets_edges=interprets_edges,
        applies_to_phase_edges=applies_to_phase_edges,
        has_obligation_article_edges=has_obligation_article_edges,
        requires_control_edges=requires_control_edges,
        violates_edges=violates_edges,
        governed_by_edges=governed_by_edges,
        hierarchy=hierarchy,
    )
    # Backfill the counts now that everything else is settled.
    metadata_node["total_nodes"] = payload.total_nodes
    metadata_node["total_edges"] = payload.total_edges
    return payload


# ─── Cypher templates (parametrised MERGE statements) ─────────────────────
#
# Every template is idempotent: re-running with the same parameters
# produces no new graph elements. ``MERGE`` matches on the keyed
# properties (``id`` for nodes, ``source_id`` + ``target_id`` for edges);
# subsequent ``SET`` updates mutable fields so a re-seed against a newer
# KB_VERSION refreshes property values without duplicating nodes.

_CYPHER_ARTICLE = """
MERGE (a:Article {id: $id})
SET a.number = $number,
    a.title = $title,
    a.text = $text,
    a.description = $description,
    a.chapter = $chapter,
    a.vector_chunk_ids = $vector_chunk_ids,
    a.legal_type = $legal_type,
    a.strict_citation = $strict_citation,
    a.celex_id = $celex_id,
    a.eli_uri = $eli_uri,
    a.legal_link = $legal_link
"""

_CYPHER_ANNEX = """
MERGE (a:Annex {id: $id})
SET a.number = $number,
    a.title = $title,
    a.text = $text,
    a.description = $description,
    a.legal_type = $legal_type,
    a.strict_citation = $strict_citation,
    a.celex_id = $celex_id,
    a.eli_uri = $eli_uri,
    a.legal_link = $legal_link
"""

_CYPHER_RECITAL = """
MERGE (r:Recital {id: $id})
SET r.number = $number,
    r.text = $text
"""

_CYPHER_DEFINITION = """
MERGE (d:Definition {id: $id})
SET d.kind = $kind,
    d.term = $term,
    d.citation = $citation,
    d.text = $text
"""

_MERGE_PARAGRAPH = """
MERGE (p:Paragraph {id: $id})
SET p.number = $number,
    p.text = $text
"""

_MERGE_POINT = """
MERGE (pt:Point {id: $id})
SET pt.letter = $letter,
    pt.text = $text
"""

_CYPHER_OBLIGATION = """
MERGE (o:Obligation {id: $id})
SET o.article_ref = $article_ref,
    o.text = $text,
    o.mandatory = $mandatory,
    o.paragraph_ref = $paragraph_ref,
    o.dimension = $dimension
"""

_CYPHER_ANNEX_III = """
MERGE (c:AnnexIIICategory {id: $id})
SET c.label = $label,
    c.number = $number,
    c.description = $description
"""

_CYPHER_RISK_LEVEL = """
MERGE (rl:RiskLevel {id: $id})
SET rl.label = $label,
    rl.description = $description
"""

_CYPHER_OPERATOR_ROLE = """
MERGE (role:OperatorRole {id: $id})
SET role.label = $label,
    role.art_3_definition = $art_3_definition,
    role.summary = $summary
"""

_CYPHER_METADATA = """
MERGE (m:KBMetadata {id: $id})
SET m.seed_version = $seed_version,
    m.kb_version = $kb_version,
    m.seeded_at = $seeded_at,
    m.total_nodes = $total_nodes,
    m.total_edges = $total_edges
"""

_CYPHER_DIMENSION = """
MERGE (d:Dimension {id: $id})
SET d.name = $name
"""

_CYPHER_QUESTION = """
MERGE (q:Question {id: $id})
SET q.text = $text,
    q.weight = $weight
"""

_CYPHER_HAS_OBLIGATION = """
MATCH (a:Article {id: $source_id})
MATCH (o:Obligation {id: $target_id})
MERGE (a)-[:HAS_OBLIGATION]->(o)
"""

_CYPHER_HAS_DEFINITION = """
MATCH (a:Article {id: $source_id})
MATCH (d:Definition {id: $target_id})
MERGE (a)-[:HAS_DEFINITION]->(d)
"""

_CYPHER_CROSS_REFERENCES = """
MATCH (s {id: $source_id})
MATCH (t {id: $target_id})
MERGE (s)-[r:CROSS_REFERENCES]->(t)
SET r.source = $edge_source
"""

_CYPHER_HAS_RECITAL_ANCHOR = """
MATCH (a:Article {id: $source_id})
MATCH (r:Recital {id: $target_id})
MERGE (a)-[:HAS_RECITAL_ANCHOR]->(r)
"""

_MERGE_HAS_PARAGRAPH = """
MATCH (a:Article {id: $source_id})
MATCH (p:Paragraph {id: $target_id})
MERGE (a)-[:HAS_PARAGRAPH]->(p)
"""

_MERGE_HAS_POINT = """
MATCH (p:Paragraph {id: $source_id})
MATCH (pt:Point {id: $target_id})
MERGE (p)-[:HAS_POINT]->(pt)
"""


_CYPHER_TRIGGERS_HIGH_RISK = """
MATCH (c:AnnexIIICategory {id: $source_id})
MATCH (a:Article {id: $target_id})
MERGE (c)-[:TRIGGERS_HIGH_RISK_UNDER]->(a)
"""

_CYPHER_APPLIES_AT = """
MATCH (o:Obligation {id: $source_id})
MATCH (rl:RiskLevel {id: $target_id})
MERGE (o)-[:APPLIES_AT]->(rl)
"""

_CYPHER_BELONGS_TO = """
MATCH (q:Question {id: $source_id})
MATCH (d:Dimension {id: $target_id})
MERGE (q)-[:BELONGS_TO]->(d)
"""

_CYPHER_ASSESSES = """
MATCH (q:Question {id: $source_id})
MATCH (o:Obligation {id: $target_id})
MERGE (q)-[:ASSESSES]->(o)
"""

# ── R291 ontology deontic layer ────────────────────────────────────────────

_CYPHER_PRACTICE = """
MERGE (p:Practice {id: $id})
SET p.short_name = $short_name,
    p.sub_paragraph = $sub_paragraph,
    p.description = $description
"""

_CYPHER_PHASE = """
MERGE (ph:LifecyclePhase {id: $id})
SET ph.label = $label,
    ph.effective_date = $effective_date,
    ph.superseded_by = $superseded_by
"""

# ``REMOVE`` clears properties written by the superseded first cut. MERGE+SET
# only overwrites the keys it names, so a renamed or dropped property would
# otherwise survive re-seeding and leave the POST-Omnibus consolidation date /
# CELEX sitting on a node whose text is pre-Omnibus.
_CYPHER_LEGAL_INSTRUMENT = """
MERGE (l:LegalInstrument {id: $id})
SET l.celex_id = $celex_id,
    l.eli_uri = $eli_uri,
    l.title = $title,
    l.portal_name = $portal_name,
    l.effective_date = $effective_date,
    l.legal_link = $legal_link
REMOVE l.consolidated_date
"""

_CYPHER_GUIDELINE = """
MERGE (g:Guideline {id: $id})
SET g.title = $title,
    g.issuing_authority = $issuing_authority,
    g.doc_id = $doc_id,
    g.interprets_celex = $interprets_celex,
    g.legal_link = $legal_link
REMOVE g.celex_id
"""

# NOTE both statements label BOTH endpoints. A label-free ``MATCH (a {id: ...})``
# is an AllNodesScan over a graph that also holds 656 Paragraph / 416 Point /
# 37 SubPoint / 180 Recital nodes — measured at ~3,500 dbHits per row against 4
# with the label — and it would happily bind a non-Article node that happened to
# share an id. Articles and Annexes are separate labels, so provenance is
# written as two label-scoped passes.
_CYPHER_HAS_PROVENANCE_ARTICLE = """
MATCH (a:Article {id: $source_id})
MATCH (l:LegalInstrument {id: $target_id})
MERGE (a)-[:HAS_PROVENANCE]->(l)
"""

_CYPHER_HAS_PROVENANCE_ANNEX = """
MATCH (a:Annex {id: $source_id})
MATCH (l:LegalInstrument {id: $target_id})
MERGE (a)-[:HAS_PROVENANCE]->(l)
"""

_CYPHER_INTERPRETS = """
MATCH (g:Guideline {id: $source_id})
MATCH (t:Article {id: $target_id})
MERGE (g)-[:INTERPRETS]->(t)
"""

_CYPHER_PROHIBITED_UNDER = """
MATCH (p:Practice {id: $source_id})
MATCH (a:Article {id: $target_id})
MERGE (p)-[:PROHIBITED_UNDER]->(a)
"""

_CYPHER_APPLIES_TO = """
MATCH (ph:LifecyclePhase {id: $source_id})
MATCH (a:Article {id: $target_id})
MERGE (ph)-[:APPLIES_TO]->(a)
"""

_CYPHER_HAS_OBLIGATION_ARTICLE = """
MATCH (role:OperatorRole {id: $source_id})
MATCH (a:Article {id: $target_id})
MERGE (role)-[r:HAS_OBLIGATION_ARTICLE]->(a)
SET r.tier = $tier
"""

# ── SOTA AIRO & EU AI Act Governance Templates ────────────────────────────

_CYPHER_RISK_SCENARIO = """
MERGE (s:RiskScenario {id: $id})
SET s.short_name = $short_name,
    s.hazard_or_threat = $hazard_or_threat,
    s.vulnerability = $vulnerability,
    s.risk_event = $risk_event,
    s.impact_area = $impact_area,
    s.severity_level = $severity_level,
    s.statutory_violation = $statutory_violation,
    s.description = $description,
    s.keywords = $keywords
"""

_CYPHER_RISK_CONTROL = """
MERGE (c:RiskControl {id: $id})
SET c.name = $name,
    c.control_type = $control_type,
    c.lifecycle_phase = $lifecycle_phase,
    c.mitigates_risk_id = $mitigates_risk_id,
    c.evidenced_by = $evidenced_by,
    c.standards_ref = $standards_ref,
    c.articles = $articles,
    c.description = $description,
    c.keywords = $keywords
"""

_CYPHER_GPAI_MODEL_PROFILE = """
MERGE (g:GPAIModelProfile {id: $id})
SET g.model_name = $model_name,
    g.training_compute_flops = $training_compute_flops,
    g.is_open_source = $is_open_source,
    g.has_systemic_risk = $has_systemic_risk,
    g.mandatory_obligations = $mandatory_obligations,
    g.technical_doc_annex = $technical_doc_annex,
    g.downstream_info_annex = $downstream_info_annex,
    g.description = $description,
    g.keywords = $keywords
"""

_CYPHER_CONFORMITY_ROUTE = """
MERGE (cr:ConformityRoute {id: $id})
SET cr.route_type = $route_type,
    cr.governing_articles = $governing_articles,
    cr.applicable_annex = $applicable_annex,
    cr.requires_notified_body = $requires_notified_body,
    cr.description = $description,
    cr.keywords = $keywords
"""

_CYPHER_FRIA_WORKFLOW = """
MERGE (f:FRIAWorkflow {id: $id})
SET f.deployer_category = $deployer_category,
    f.governing_articles = $governing_articles,
    f.required_steps = $required_steps,
    f.mandatory_reporting_authority = $mandatory_reporting_authority,
    f.description = $description,
    f.keywords = $keywords
"""

_CYPHER_SERIOUS_INCIDENT = """
MERGE (i:SeriousIncidentSLA {id: $id})
SET i.incident_type = $incident_type,
    i.deadline_hours = $deadline_hours,
    i.statutory_basis = $statutory_basis,
    i.qms_update_required = $qms_update_required,
    i.description = $description,
    i.keywords = $keywords
"""

_CYPHER_REQUIRES_CONTROL = """
MATCH (s:RiskScenario {id: $source_id})
MATCH (c:RiskControl {id: $target_id})
MERGE (s)-[:REQUIRES_CONTROL]->(c)
"""

_CYPHER_VIOLATES_ARTICLE = """
MATCH (s:RiskScenario {id: $source_id})
MATCH (a:Article {id: $target_id})
MERGE (s)-[:VIOLATES]->(a)
"""

_CYPHER_VIOLATES_ANNEX = """
MATCH (s:RiskScenario {id: $source_id})
MATCH (a:Annex {id: $target_id})
MERGE (s)-[:VIOLATES]->(a)
"""

_CYPHER_GOVERNED_BY_ARTICLE = """
MATCH (s {id: $source_id})
WHERE s:RiskControl OR s:GPAIModelProfile OR s:ConformityRoute OR s:FRIAWorkflow OR s:SeriousIncidentSLA
MATCH (a:Article {id: $target_id})
MERGE (s)-[:GOVERNED_BY]->(a)
"""

_CYPHER_GOVERNED_BY_ANNEX = """
MATCH (s {id: $source_id})
WHERE s:RiskControl OR s:GPAIModelProfile OR s:ConformityRoute OR s:FRIAWorkflow OR s:SeriousIncidentSLA
MATCH (a:Annex {id: $target_id})
MERGE (s)-[:GOVERNED_BY]->(a)
"""


# ─── Runner ──────────────────────────────────────────────────────────────


def _batched(rows: list[dict], size: int) -> Iterable[list[dict]]:
    """Yield successive ``size``-row windows."""
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def _write_rows(
    client: Any,
    cypher: str,
    rows: list[dict],
    *,
    batch_size: int,
    label: str,
    verbose: bool,
) -> int:
    """Push ``rows`` through ``cypher`` in batches via ``execute_write_batch``.

    Returns the total row count written. Each batch is one transaction;
    individual ``execute_write_batch`` calls are atomic, so a mid-batch
    failure rolls back the offending batch only (earlier batches stay).
    """
    written = 0
    for chunk in _batched(rows, batch_size):
        queries: list[tuple[str, dict]] = [(cypher, row) for row in chunk]
        client.execute_write_batch(queries)
        written += len(chunk)
        if verbose:
            logger.info("seeded %s batch=%d total=%d", label, len(chunk), written)
    return written


def seed_graph(
    client: Any,
    payload: SeedPayload,
    *,
    batch_size: int = BATCH_SIZE,
    verbose: bool = False,
) -> dict[str, int]:
    """Run the full seed against ``client``.

    The grouping mirrors the dependency graph: nodes first (so edge
    ``MATCH``es resolve), then edges. Per-label batches keep individual
    transactions small.
    """
    counts: dict[str, int] = {}

    # ── Nodes ─────────────────────────────────────────────────────────
    counts["Article"] = _write_rows(
        client, _CYPHER_ARTICLE, payload.article_nodes,
        batch_size=batch_size, label="Article", verbose=verbose,
    )
    counts["Annex"] = _write_rows(
        client, _CYPHER_ANNEX, payload.annex_nodes,
        batch_size=batch_size, label="Annex", verbose=verbose,
    )
    counts["Recital"] = _write_rows(
        client, _CYPHER_RECITAL, payload.recital_nodes,
        batch_size=batch_size, label="Recital", verbose=verbose,
    )
    counts["Definition"] = _write_rows(
        client, _CYPHER_DEFINITION, payload.definition_nodes,
        batch_size=batch_size, label="Definition", verbose=verbose,
    )
    counts["Obligation"] = _write_rows(
        client, _CYPHER_OBLIGATION, payload.obligation_nodes,
        batch_size=batch_size, label="Obligation", verbose=verbose,
    )
    counts["AnnexIIICategory"] = _write_rows(
        client, _CYPHER_ANNEX_III, payload.annex_iii_nodes,
        batch_size=batch_size, label="AnnexIIICategory", verbose=verbose,
    )
    counts["RiskLevel"] = _write_rows(
        client, _CYPHER_RISK_LEVEL, payload.risk_level_nodes,
        batch_size=batch_size, label="RiskLevel", verbose=verbose,
    )
    counts["OperatorRole"] = _write_rows(
        client, _CYPHER_OPERATOR_ROLE, payload.operator_role_nodes,
        batch_size=batch_size, label="OperatorRole", verbose=verbose,
    )
    counts["Dimension"] = _write_rows(
        client, _CYPHER_DIMENSION, payload.dimension_nodes,
        batch_size=batch_size, label="Dimension", verbose=verbose,
    )
    counts["Question"] = _write_rows(
        client, _CYPHER_QUESTION, payload.question_nodes,
        batch_size=batch_size, label="Question", verbose=verbose,
    )
    counts["KBMetadata"] = _write_rows(
        client, _CYPHER_METADATA, [payload.metadata_node],
        batch_size=batch_size, label="KBMetadata", verbose=verbose,
    )
    # R291 ontology nodes.
    counts["Practice"] = _write_rows(
        client, _CYPHER_PRACTICE, payload.practice_nodes,
        batch_size=batch_size, label="Practice", verbose=verbose,
    )
    counts["LifecyclePhase"] = _write_rows(
        client, _CYPHER_PHASE, payload.phase_nodes,
        batch_size=batch_size, label="LifecyclePhase", verbose=verbose,
    )
    counts["LegalInstrument"] = _write_rows(
        client, _CYPHER_LEGAL_INSTRUMENT, payload.legal_instrument_nodes,
        batch_size=batch_size, label="LegalInstrument", verbose=verbose,
    )
    counts["Guideline"] = _write_rows(
        client, _CYPHER_GUIDELINE, payload.guideline_nodes,
        batch_size=batch_size, label="Guideline", verbose=verbose,
    )
    # SOTA AIRO & Governance nodes
    counts["RiskScenario"] = _write_rows(
        client, _CYPHER_RISK_SCENARIO, payload.risk_scenario_nodes,
        batch_size=batch_size, label="RiskScenario", verbose=verbose,
    )
    counts["RiskControl"] = _write_rows(
        client, _CYPHER_RISK_CONTROL, payload.risk_control_nodes,
        batch_size=batch_size, label="RiskControl", verbose=verbose,
    )
    counts["GPAIModelProfile"] = _write_rows(
        client, _CYPHER_GPAI_MODEL_PROFILE, payload.gpai_profile_nodes,
        batch_size=batch_size, label="GPAIModelProfile", verbose=verbose,
    )
    counts["ConformityRoute"] = _write_rows(
        client, _CYPHER_CONFORMITY_ROUTE, payload.conformity_route_nodes,
        batch_size=batch_size, label="ConformityRoute", verbose=verbose,
    )
    counts["FRIAWorkflow"] = _write_rows(
        client, _CYPHER_FRIA_WORKFLOW, payload.fria_workflow_nodes,
        batch_size=batch_size, label="FRIAWorkflow", verbose=verbose,
    )
    counts["SeriousIncidentSLA"] = _write_rows(
        client, _CYPHER_SERIOUS_INCIDENT, payload.serious_incident_nodes,
        batch_size=batch_size, label="SeriousIncidentSLA", verbose=verbose,
    )

    # ── Edges ─────────────────────────────────────────────────────────
    counts["HAS_OBLIGATION"] = _write_rows(
        client, _CYPHER_HAS_OBLIGATION, payload.has_obligation_edges,
        batch_size=batch_size, label="HAS_OBLIGATION", verbose=verbose,
    )
    counts["HAS_DEFINITION"] = _write_rows(
        client, _CYPHER_HAS_DEFINITION, payload.has_definition_edges,
        batch_size=batch_size, label="HAS_DEFINITION", verbose=verbose,
    )
    counts["CROSS_REFERENCES"] = _write_rows(
        client, _CYPHER_CROSS_REFERENCES, payload.cross_reference_edges,
        batch_size=batch_size, label="CROSS_REFERENCES", verbose=verbose,
    )
    counts["HAS_RECITAL_ANCHOR"] = _write_rows(
        client, _CYPHER_HAS_RECITAL_ANCHOR, payload.has_recital_anchor_edges,
        batch_size=batch_size, label="HAS_RECITAL_ANCHOR", verbose=verbose,
    )
    counts["TRIGGERS_HIGH_RISK_UNDER"] = _write_rows(
        client, _CYPHER_TRIGGERS_HIGH_RISK, payload.triggers_high_risk_edges,
        batch_size=batch_size, label="TRIGGERS_HIGH_RISK_UNDER", verbose=verbose,
    )
    counts["APPLIES_AT"] = _write_rows(
        client, _CYPHER_APPLIES_AT, payload.applies_at_edges,
        batch_size=batch_size, label="APPLIES_AT", verbose=verbose,
    )
    counts["BELONGS_TO"] = _write_rows(
        client, _CYPHER_BELONGS_TO, payload.belongs_to_edges,
        batch_size=batch_size, label="BELONGS_TO", verbose=verbose,
    )
    counts["ASSESSES"] = _write_rows(
        client, _CYPHER_ASSESSES, payload.assesses_edges,
        batch_size=batch_size, label="ASSESSES", verbose=verbose,
    )
    # R291 ontology-layer edges.
    counts["PROHIBITED_UNDER"] = _write_rows(
        client, _CYPHER_PROHIBITED_UNDER, payload.prohibited_under_edges,
        batch_size=batch_size, label="PROHIBITED_UNDER", verbose=verbose,
    )
    counts["APPLIES_TO"] = _write_rows(
        client, _CYPHER_APPLIES_TO, payload.applies_to_phase_edges,
        batch_size=batch_size, label="APPLIES_TO", verbose=verbose,
    )
    counts["HAS_OBLIGATION_ARTICLE"] = _write_rows(
        client, _CYPHER_HAS_OBLIGATION_ARTICLE, payload.has_obligation_article_edges,
        batch_size=batch_size, label="HAS_OBLIGATION_ARTICLE", verbose=verbose,
    )
    # Provenance is written per source label (see the Cypher note above).
    _article_ids = {row["id"] for row in payload.article_nodes}
    counts["HAS_PROVENANCE"] = _write_rows(
        client, _CYPHER_HAS_PROVENANCE_ARTICLE,
        [e for e in payload.has_provenance_edges if e["source_id"] in _article_ids],
        batch_size=batch_size, label="HAS_PROVENANCE(Article)", verbose=verbose,
    ) + _write_rows(
        client, _CYPHER_HAS_PROVENANCE_ANNEX,
        [e for e in payload.has_provenance_edges if e["source_id"] not in _article_ids],
        batch_size=batch_size, label="HAS_PROVENANCE(Annex)", verbose=verbose,
    )
    counts["INTERPRETS"] = _write_rows(
        client, _CYPHER_INTERPRETS, payload.interprets_edges,
        batch_size=batch_size, label="INTERPRETS", verbose=verbose,
    )
    # SOTA AIRO & Governance edges
    counts["REQUIRES_CONTROL"] = _write_rows(
        client, _CYPHER_REQUIRES_CONTROL, payload.requires_control_edges,
        batch_size=batch_size, label="REQUIRES_CONTROL", verbose=verbose,
    )
    counts["VIOLATES"] = _write_rows(
        client, _CYPHER_VIOLATES_ARTICLE,
        [e for e in payload.violates_edges if e["target_id"] in _article_ids],
        batch_size=batch_size, label="VIOLATES(Article)", verbose=verbose,
    ) + _write_rows(
        client, _CYPHER_VIOLATES_ANNEX,
        [e for e in payload.violates_edges if e["target_id"] not in _article_ids],
        batch_size=batch_size, label="VIOLATES(Annex)", verbose=verbose,
    )
    counts["GOVERNED_BY"] = _write_rows(
        client, _CYPHER_GOVERNED_BY_ARTICLE,
        [e for e in payload.governed_by_edges if e["target_id"] in _article_ids],
        batch_size=batch_size, label="GOVERNED_BY(Article)", verbose=verbose,
    ) + _write_rows(
        client, _CYPHER_GOVERNED_BY_ANNEX,
        [e for e in payload.governed_by_edges if e["target_id"] not in _article_ids],
        batch_size=batch_size, label="GOVERNED_BY(Annex)", verbose=verbose,
    )

    return counts


def validate_payload(payload: SeedPayload) -> list[str]:
    """Return a list of error strings; empty list means the payload is sane.

    Catches dangling edges (source / target IDs that don't appear in any
    node bucket). Pure check — does not raise. The runner exits non-zero
    when this returns a non-empty list under ``--dry-run`` or live mode.
    """
    node_ids: set[str] = set()
    for bucket in (
        payload.article_nodes,
        payload.annex_nodes,
        payload.recital_nodes,
        payload.definition_nodes,
        payload.obligation_nodes,
        payload.annex_iii_nodes,
        payload.risk_level_nodes,
        payload.operator_role_nodes,
        payload.dimension_nodes,
        payload.question_nodes,
        payload.practice_nodes,
        payload.phase_nodes,
        payload.legal_instrument_nodes,
        payload.guideline_nodes,
        payload.risk_scenario_nodes,
        payload.risk_control_nodes,
        payload.gpai_profile_nodes,
        payload.conformity_route_nodes,
        payload.fria_workflow_nodes,
        payload.serious_incident_nodes,
    ):
        for row in bucket:
            node_ids.add(row["id"])
    node_ids.add(payload.metadata_node["id"])

    errors: list[str] = []
    edge_buckets = (
        ("HAS_OBLIGATION", payload.has_obligation_edges),
        ("HAS_DEFINITION", payload.has_definition_edges),
        ("CROSS_REFERENCES", payload.cross_reference_edges),
        ("HAS_RECITAL_ANCHOR", payload.has_recital_anchor_edges),
        ("TRIGGERS_HIGH_RISK_UNDER", payload.triggers_high_risk_edges),
        ("APPLIES_AT", payload.applies_at_edges),
        ("BELONGS_TO", payload.belongs_to_edges),
        ("ASSESSES", payload.assesses_edges),
        ("PROHIBITED_UNDER", payload.prohibited_under_edges),
        ("APPLIES_TO", payload.applies_to_phase_edges),
        ("HAS_OBLIGATION_ARTICLE", payload.has_obligation_article_edges),
        ("HAS_PROVENANCE", payload.has_provenance_edges),
        ("INTERPRETS", payload.interprets_edges),
        ("REQUIRES_CONTROL", payload.requires_control_edges),
        ("VIOLATES", payload.violates_edges),
        ("GOVERNED_BY", payload.governed_by_edges),
    )
    for name, edges in edge_buckets:
        for row in edges:
            if row["source_id"] not in node_ids:
                errors.append(
                    f"{name}: dangling source_id={row['source_id']!r}"
                )
            if row["target_id"] not in node_ids:
                errors.append(
                    f"{name}: dangling target_id={row['target_id']!r}"
                )
    return errors


# ─── CLI ─────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="seed_neo4j_kb",
        description=(
            "Seed the Regenold EU AI Act KB (articles, annexes, recitals, "
            "definitions, obligations, ontology, role × risk edges) into "
            "Neo4j. Idempotent — MERGE-based."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print payload counts and exit without writing to Neo4j.",
    )
    p.add_argument(
        "--clear",
        action="store_true",
        help="DETACH DELETE every node before seeding (DESTRUCTIVE).",
    )
    p.add_argument(
        "--neo4j-uri",
        default=None,
        help="Override the NEO4J_URI env var.",
    )
    p.add_argument(
        "--neo4j-user",
        default=None,
        help="Override the NEO4J_USER env var.",
    )
    p.add_argument(
        "--neo4j-password",
        default=None,
        help="Override the NEO4J_PASSWORD env var.",
    )
    p.add_argument(
        "--neo4j-database",
        default=None,
        help="Override the NEO4J_DATABASE env var.",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Rows per write transaction (default {BATCH_SIZE}).",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Log per-batch progress.",
    )
    return p


def _apply_env_overrides(args: argparse.Namespace) -> None:
    """Map CLI overrides into env vars before GraphSettings reads them."""
    if args.neo4j_uri:
        os.environ["NEO4J_URI"] = args.neo4j_uri
    if args.neo4j_user:
        os.environ["NEO4J_USER"] = args.neo4j_user
    if args.neo4j_password:
        os.environ["NEO4J_PASSWORD"] = args.neo4j_password
    if args.neo4j_database:
        os.environ["NEO4J_DATABASE"] = args.neo4j_database


# ── R291 schema (constraints + indexes + full-text + vector) ───────────────
#
# The seeder created ZERO constraints/indexes before R291 — MERGE-on-{id}
# without a backing uniqueness constraint is not race-safe and is the
# structural precondition for the R98 ~20x node duplication. These run FIRST,
# before any MERGE. Every statement is ``IF NOT EXISTS`` (idempotent) and
# fail-soft (a Community-edition graph without vector/full-text support logs
# and continues rather than aborting the seed).

#: Labels that carry embeddable verbatim prose (for the vector index).
_EMBEDDING_LABELS: tuple[str, ...] = (
    "Article", "Annex", "Paragraph", "Point", "SubPoint", "Definition", "Recital",
)
_EMBEDDING_DIM = 128  # matches app.engines.embeddings_index (TF-IDF -> SVD-128)


def _schema_statements() -> list[str]:
    """The ordered DDL: uniqueness constraints, range indexes, full-text, vector."""
    from app.graph.schema import SEEDED_NODE_LABELS

    stmts: list[str] = []
    # Uniqueness constraints on {id} — driven off the single source of truth
    # so the list can never drift from what the seeder writes.
    for label in sorted(SEEDED_NODE_LABELS):
        cname = "c_" + re.sub(r"[^a-z0-9]", "_", label.lower()) + "_id"
        stmts.append(
            f"CREATE CONSTRAINT {cname} IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
        )
    # Range indexes on the hot lookup keys the live consumers filter on.
    stmts.extend([
        "CREATE INDEX i_article_number IF NOT EXISTS FOR (n:Article) ON (n.number)",
        "CREATE INDEX i_annex_number IF NOT EXISTS FOR (n:Annex) ON (n.number)",
        "CREATE INDEX i_obligation_art IF NOT EXISTS FOR (n:Obligation) ON (n.article_ref)",
        "CREATE INDEX i_recital_number IF NOT EXISTS FOR (n:Recital) ON (n.number)",
    ])
    # Full-text index over the verbatim prose (graph-native keyword search).
    ft_labels = "|".join(("Article", "Annex", "Paragraph", "Point", "SubPoint", "Definition", "Recital"))
    stmts.append(
        "CREATE FULLTEXT INDEX ft_provision_prose IF NOT EXISTS "
        f"FOR (n:{ft_labels}) ON EACH [n.text]"
    )
    # Vector index per embeddable label (Neo4j vector indexes are per-label).
    for label in _EMBEDDING_LABELS:
        idx = "v_" + label.lower() + "_embedding"
        stmts.append(
            f"CREATE VECTOR INDEX {idx} IF NOT EXISTS "
            f"FOR (n:{label}) ON (n.embedding) "
            f"OPTIONS {{indexConfig: {{`vector.dimensions`: {_EMBEDDING_DIM}, "
            f"`vector.similarity_function`: 'cosine'}}}}"
        )
    return stmts


def _ensure_schema(client, *, verbose: bool = False) -> dict[str, int]:
    """Create constraints + indexes (idempotent, fail-soft). Returns a tally."""
    logger = logging.getLogger(__name__)
    ok = 0
    failed = 0
    for stmt in _schema_statements():
        try:
            client.execute_write_batch([(stmt, {})])
            ok += 1
            if verbose:
                logger.info("schema ok: %s", stmt.split(" IF NOT EXISTS")[0])
        except Exception as exc:  # pragma: no cover - edition-dependent
            failed += 1
            logger.warning("schema statement skipped (%s): %s", exc, stmt[:60])
    return {"schema_ok": ok, "schema_failed": failed}


def _embed_and_index(client, payload: SeedPayload, *, verbose: bool = False) -> int:
    """Compute + write 128-D embeddings for the verbatim-prose nodes.

    Reuses :func:`app.engines.embeddings_index._embed_query` (the same TF-IDF ->
    SVD-128 projection the live retrieval uses), so the graph vectors live in
    the SAME subspace as the in-process embeddings index. Fail-soft: returns 0
    when the embeddings assets are unavailable (no numpy assets on disk) or on
    any error — the seed's structure is unaffected.
    """
    logger = logging.getLogger(__name__)
    try:
        from app.engines.embeddings_index import _embed_query, is_available
    except Exception:  # pragma: no cover - defensive
        return 0
    if not is_available():
        logger.warning("embeddings assets unavailable; skipping vector embedding.")
        return 0

    # (label, {id: text}) for every embeddable node.
    buckets: list[tuple[str, list[dict]]] = [
        ("Article", payload.article_nodes),
        ("Annex", payload.annex_nodes),
        ("Definition", payload.definition_nodes),
        ("Recital", payload.recital_nodes),
    ]
    if payload.hierarchy is not None:
        buckets.append(("Paragraph", payload.hierarchy.paragraph_nodes))
        buckets.append(("Point", payload.hierarchy.point_nodes))
        buckets.append(("SubPoint", payload.hierarchy.subpoint_nodes))

    written = 0
    for label, nodes in buckets:
        rows: list[tuple[str, dict]] = []
        cypher = (
            f"MATCH (n:{label} {{id: $id}}) SET n.embedding = $embedding"
        )
        for node in nodes:
            text = node.get("text") or node.get("description") or ""
            if not text:
                continue
            vec = _embed_query(text)
            if vec is None:
                continue
            rows.append((cypher, {"id": node["id"], "embedding": [float(x) for x in vec]}))
        for i in range(0, len(rows), 200):
            client.execute_write_batch(rows[i:i + 200])
        written += len(rows)
        if verbose:
            logger.info("embedded %d :%s nodes", len(rows), label)
    logger.info("R291 vector embeddings: %d nodes embedded", written)
    return written


def _ingest_legal_ast_hierarchy(client) -> int:
    """Build the Article/Annex -> Paragraph -> Point hierarchy on ``client``.

    Reuses the single :func:`app.engines.legal_ast.ingest_legal_ast` builder
    (so there is ONE source of the Paragraph/Point hierarchy, no seeder vs
    legal_ast drift) against the already-open seed client. Fail-soft: returns
    ``0`` and logs on any error so a hierarchy hiccup never aborts an
    otherwise-successful base seed. Returns ``1`` on success (a coarse marker;
    the detailed node count is logged by ``ingest_legal_ast`` itself).
    """
    try:
        from app.engines.legal_ast import ingest_legal_ast

        ingest_legal_ast(client)
        return 1
    except Exception as exc:  # pragma: no cover - defensive
        logging.getLogger(__name__).warning(
            "Legal AST hierarchy ingestion failed (base seed unaffected): %s", exc
        )
        return 0


def run_seed(
    *,
    dry_run: bool = False,
    clear: bool = False,
    verbose: bool = False,
    batch_size: int = BATCH_SIZE,
) -> dict[str, Any]:
    """Programmatic entrypoint — same body as ``main()`` minus argparse / prints.

    Returns a dict with shape::

        {
            "status": "ok" | "dangling_edges" | "graph_disabled" | "dry_run",
            "seed_version": SEED_VERSION,
            "kb_version": KB_VERSION,
            "total_nodes": int,
            "total_edges": int,
            "counts": dict[str, int],   # only when status == "ok"
            "errors": list[str],        # only when status == "dangling_edges"
        }

    Designed to be called from the FastAPI startup hook (see
    ``app/main.py::_maybe_auto_seed_neo4j``). Never raises — every error
    state is captured in the return dict so the caller can decide whether
    to log + continue or fail loud.
    """
    payload = build_payload()
    result: dict[str, Any] = {
        "seed_version": SEED_VERSION,
        "kb_version": KB_VERSION,
        "total_nodes": payload.total_nodes,
        "total_edges": payload.total_edges,
    }

    errors = validate_payload(payload)
    if errors:
        result["status"] = "dangling_edges"
        result["errors"] = errors
        return result

    if dry_run:
        result["status"] = "dry_run"
        result["counts"] = {**payload.counts(), **payload.hierarchy_counts()}
        return result

    # Deferred import — keeps the offline / dry-run path free of the
    # optional ``neo4j`` driver.
    from app.graph.client import GraphClient
    from app.graph.config import GraphSettings

    client = GraphClient(GraphSettings())
    if not client.enabled:
        result["status"] = "graph_disabled"
        return result

    try:
        if clear:
            client.clear_graph()
        # R291 — constraints + range/full-text/vector indexes FIRST (idempotent,
        # fail-soft) so every subsequent MERGE is index-backed + race-safe.
        _ensure_schema(client, verbose=verbose)
        counts = seed_graph(
            client, payload, batch_size=batch_size, verbose=verbose
        )
        counts.update(payload.hierarchy_counts())
        # Ontology Leap — build the Article/Annex -> Paragraph -> Point ->
        # SubPoint hierarchy (full EU AI Act coverage) on top of the base seed
        # so the deterministic Article 6(3) Cypher (and sub-point traversal)
        # has nodes to traverse. Fail-soft: a hierarchy-ingest error must NOT
        # abort an otherwise-successful base seed.
        counts["legal_ast_hierarchy"] = _ingest_legal_ast_hierarchy(client)
        # R291 — 128-D vector embeddings for graph-native semantic search
        # (fail-soft; no-op when the embeddings assets are unavailable).
        counts["embeddings"] = _embed_and_index(client, payload, verbose=verbose)
    finally:
        client.close()

    result["status"] = "ok"
    result["counts"] = counts
    return result


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    payload = build_payload()

    # Sanity-check before we touch the driver. Dangling edges should fail
    # loud — they indicate the source modules have drifted out of sync.
    errors = validate_payload(payload)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        print(
            f"Payload validation failed with {len(errors)} dangling edges; "
            "fix source modules before seeding.",
            file=sys.stderr,
        )
        return 2

    counts = {**payload.counts(), **payload.hierarchy_counts()}
    print("---- Regenold KB seed payload ----")
    print(f"  seed_version : {SEED_VERSION}")
    print(f"  kb_version   : {KB_VERSION}")
    print(f"  total_nodes  : {payload.total_nodes}")
    print(f"  total_edges  : {payload.total_edges}")
    for label, count in counts.items():
        print(f"    {label:<28} = {count}")

    if args.dry_run:
        print("\n--dry-run: no writes performed. Exiting 0.")
        return 0

    # ⚠ DO NOT ADD load_dotenv() HERE. Reverted 2026-08-14.
    #
    # An uncommitted change had put `load_dotenv()` on this line, one statement
    # before the driver is constructed. It reads as a convenience. It is not:
    # it removes the only barrier standing between a casual `py -3.12
    # scripts/seed_neo4j_kb.py` and a MERGE-write against the SHARED production
    # Aura instance.
    #
    # The chain, each link verified:
    #   * `.env` (gitignored, present on developer machines) carries
    #     NEO4J_URI = the live Aura host, plus NEO4J_PASSWORD.
    #   * `app/graph/config.py` GraphSettings has NO `env_file` — it reads
    #     os.environ only, so `load_dotenv()` is precisely what activates it.
    #   * `app/graph/client.py` gates activation on `os.environ["NEO4J_URI"]`
    #     being present — nothing else.
    #   * this script accepts `--clear`, which DETACH DELETEs every node.
    #   * the seeder never reads NEO4J_AUTO_SEED (its only consumer is
    #     app/main.py), so hard rule #12's pin gives ZERO protection here.
    #
    # CLAUDE.md files "Scripts don't load .env" under gotchas, as an
    # annoyance. It is not an annoyance — it is the ENFORCEMENT MECHANISM for
    # hard rule #12. Before this line existed, a bare run from a clean shell
    # exited with "GraphClient is disabled — set NEO4J_URI". After it, the
    # identical command silently authenticates against production and writes.
    # The failure is silent by construction: the seed succeeds, /healthz/graph
    # stays green, and answers just get worse.
    #
    # If the ergonomics are genuinely wanted, they must be UNREACHABLE BY
    # ACCIDENT: an explicit `--load-dotenv` flag, plus a refusal to write when
    # the resolved URI is the shared Aura host without a second explicit
    # opt-in. Credentials for a real seed are exported deliberately, per run.
    _apply_env_overrides(args)

    # Deferred import so the offline / dry-run paths don't drag the
    # graph client (and its optional neo4j driver) into module import.
    from app.graph.client import GraphClient
    from app.graph.config import GraphSettings

    client = GraphClient(GraphSettings())
    if not client.enabled:
        print(
            "ERROR: GraphClient is disabled — set NEO4J_URI (and install "
            "the 'neo4j' driver) before seeding. Use --dry-run to inspect "
            "the payload offline.",
            file=sys.stderr,
        )
        return 1

    if args.clear:
        print("[--clear] Wiping graph (DETACH DELETE every node)...")
        client.clear_graph()

    # R291 — constraints + range/full-text/vector indexes first (idempotent).
    schema_tally = _ensure_schema(client, verbose=args.verbose)
    written = seed_graph(
        client, payload, batch_size=args.batch_size, verbose=args.verbose
    )
    written.update(payload.hierarchy_counts())
    # Ontology Leap — Article/Annex -> Paragraph -> Point -> SubPoint hierarchy.
    _ingest_legal_ast_hierarchy(client)
    # R291 — 128-D vector embeddings for graph-native semantic search.
    n_embedded = _embed_and_index(client, payload, verbose=args.verbose)
    print("\n---- Seed complete ----")
    for label, count in written.items():
        print(f"    {label:<28} = {count}")
    print(f"    legal_ast_hierarchy          = ingested (Article/Annex -> Paragraph -> Point -> SubPoint)")
    print(f"    schema (constraints+indexes) = {schema_tally['schema_ok']} ok, {schema_tally['schema_failed']} skipped")
    print(f"    vector_embeddings            = {n_embedded} nodes")
    client.close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
