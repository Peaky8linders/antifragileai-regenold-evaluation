"""Deterministic graph builder: ``list[Provision]`` -> :class:`KnowledgeGraph`.

Every edge here is derived with zero hallucination — from the provision hierarchy
(encoded in the eid), from Phase-1 metadata (``references_internal`` etc.), or from the
deterministic in-text citation parser. The deontic/actor/risk layer is *not* built here;
it is enrichment (see :mod:`euaiact.graph.enrich`). We do seed the closed controlled
vocabularies (Actor roles, risk tiers) because those are definitional, not extracted.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

try:
    from .ids import ProvisionId, ProvisionIdError
    from .models import Provision
except (ImportError, ValueError):
    from ..ids import ProvisionId, ProvisionIdError
    from ..models import Provision
from .citations import extract_reference_eids
from .model import KnowledgeGraph
from .schema import ACTOR_VOCAB, RISK_CLASS_VOCAB, EdgeType, NodeType

__all__ = ["build_graph"]

_SLUG_RE = re.compile(r"[^a-z0-9]+")

# ---------------------------------------------------------------------------
# Authoritative registry — loaded once at import time if present; otherwise
# falls back to hardcoded ceilings so the build is correct offline.
# ---------------------------------------------------------------------------
_REGISTRY_PATH = Path(__file__).resolve().parents[3] / "data" / "authoritative_registry.json"

def _load_registry() -> dict[str, Any] | None:
    if _REGISTRY_PATH.exists():
        try:
            return json.loads(_REGISTRY_PATH.read_text())
        except Exception:
            return None
    return None

_REGISTRY = _load_registry()

# Hardcoded fallbacks (correct per the Act; used when registry file is absent).
_MAX_ARTICLE: int = _REGISTRY["counts"]["articles"] if _REGISTRY else 113
_VALID_ARTICLES: frozenset[int] = (
    frozenset(_REGISTRY["articles"]) if _REGISTRY else frozenset(range(1, 114))
)
_VALID_RECITALS: frozenset[int] = (
    frozenset(_REGISTRY["recitals"]) if _REGISTRY else frozenset(range(1, 181))
)
_VALID_ANNEXES: frozenset[str] = (
    frozenset(_REGISTRY["annexes"])
    if _REGISTRY
    else frozenset(["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"])
)


def _is_valid_internal_ref(eid: str) -> bool:
    """Return False for any eid whose provision number falls outside the authoritative set.

    Accepts article eids (art_N…), recital eids (recital_N), and annex eids (annex_R…).
    All other eid roots pass through unchecked (hierarchy nodes, etc.).
    """
    try:
        pid = ProvisionId.from_eid(eid)
    except ProvisionIdError:
        return False

    root = pid.root_kind  # "article", "annex", "recital", "chapter", "section"
    seg0_value = pid.segments[0].value

    if root == "article":
        if not seg0_value.isdigit():
            return True  # unusual format — let it pass
        return int(seg0_value) in _VALID_ARTICLES
    if root == "recital":
        if not seg0_value.isdigit():
            return True
        return int(seg0_value) in _VALID_RECITALS
    if root == "annex":
        return seg0_value.upper() in _VALID_ANNEXES
    # chapter, section, etc. — not validated against registry
    return True


def _slug(text: str) -> str:
    return _SLUG_RE.sub("_", text.lower()).strip("_")


def _node_type_for(pid: ProvisionId) -> NodeType:
    if pid.root_kind == "recital":
        return NodeType.RECITAL
    if pid.root_kind == "annex":
        if pid.annex_point is None and pid.point is None:
            return NodeType.ANNEX
        return NodeType.ANNEX_POINT
    return NodeType.PROVISION


def _provision_props(prov: Provision) -> dict[str, Any]:
    pid = ProvisionId.from_eid(prov.provision_id)
    raw = {
        "eid": prov.provision_id,
        "citation": prov.citation,
        "eli_uri": prov.eli_uri,
        "chunk_type": prov.chunk_type,
        "level": pid.level,
        "text": prov.text,
        "article": prov.article,
        "paragraph": prov.paragraph,
        "point": prov.point,
        "subpoint": prov.subpoint,
        "annex": prov.annex,
        "annex_point": prov.annex_point,
        "recital": prov.recital,
        "chapter": prov.chapter,
        "section": prov.section,
        "celex": prov.celex,
        "lang": prov.lang,
        "effective_from": prov.effective_from.isoformat() if prov.effective_from else None,
        "transitional": prov.transitional or None,
    }
    return {k: v for k, v in raw.items() if v is not None and v != ""}


def _ensure_provision_node(g: KnowledgeGraph, eid: str) -> bool:
    """Create a minimal (synthesized) provision node if ``eid`` is not already present.

    Returns True if the eid is a well-formed provision id (node ensured), False otherwise.
    """
    if g.get_node(eid) is not None:
        return True
    try:
        pid = ProvisionId.from_eid(eid)
    except ProvisionIdError:
        return False
    g.add_node(
        eid,
        _node_type_for(pid),
        label=pid.citation,
        props={"eid": eid, "citation": pid.citation, "level": pid.level, "synthesized": True},
    )
    return True


def _link_hierarchy(g: KnowledgeGraph, pid: ProvisionId) -> None:
    chain = list(reversed(pid.ancestors())) + [pid]  # root -> ... -> leaf
    for parent, child in zip(chain, chain[1:]):
        _ensure_provision_node(g, parent.eid)
        g.add_edge(EdgeType.HAS_CHILD, parent.eid, child.eid)


def _seed_controlled_vocabulary(g: KnowledgeGraph) -> None:
    for key, meta in ACTOR_VOCAB.items():
        g.add_node(
            f"actor_{key}",
            NodeType.ACTOR,
            label=meta["label"],
            props={"key": key, "defined_at": meta["anchor"]} if meta["anchor"] else {"key": key},
        )
    for key, meta in RISK_CLASS_VOCAB.items():
        props: dict[str, Any] = {"key": key}
        if meta["anchor"]:
            props["governing_provision"] = meta["anchor"]
        g.add_node(f"risk_{key}", NodeType.RISK_CLASS, label=meta["label"], props=props)


def build_graph(
    provisions: Iterable[Provision],
    *,
    extract_text_citations: bool = True,
    seed_vocab: bool = True,
) -> KnowledgeGraph:
    """Build the deterministic knowledge-graph backbone from Phase-1 provisions."""
    g = KnowledgeGraph()
    provisions = list(provisions)

    # Pass 1 — every real provision becomes a node (so pass 2/3 never mislabels a real
    # node as synthesized).
    for prov in provisions:
        pid = ProvisionId.from_eid(prov.provision_id)
        g.add_node(
            prov.provision_id,
            _node_type_for(pid),
            label=prov.citation,
            props=_provision_props(prov),
        )

    # Pass 2 — hierarchy (synthesizing any missing structural ancestors).
    for prov in provisions:
        _link_hierarchy(g, ProvisionId.from_eid(prov.provision_id))

    # Pass 3 — semantic / provenance edges from metadata + in-text citations.
    for prov in provisions:
        eid = prov.provision_id

        for ref in prov.references_internal:
            if _is_valid_internal_ref(ref) and _ensure_provision_node(g, ref):
                g.add_edge(
                    EdgeType.CROSS_REFERENCES_INTERNAL, eid, ref, props={"provenance": "metadata"}
                )

        if extract_text_citations:
            for ref in extract_reference_eids(prov.text, exclude=eid):
                if _is_valid_internal_ref(ref) and _ensure_provision_node(g, ref):
                    g.add_edge(
                        EdgeType.CROSS_REFERENCES_INTERNAL, eid, ref, props={"provenance": "text"}
                    )

        for ref in prov.references_external:
            celex = ref.split("__", 1)[0]
            g.add_node(f"ext_{celex}", NodeType.EXTERNAL_REGULATION, label=celex, props={"celex": celex})
            g.add_edge(
                EdgeType.CROSS_REFERENCES_EXTERNAL, eid, f"ext_{celex}", props={"reference": ref}
            )

        for term in prov.defined_terms:
            term_id = f"term_{_slug(term)}"
            g.add_node(term_id, NodeType.DEFINED_TERM, label=term, props={"term": term})
            g.add_edge(EdgeType.USES_TERM, eid, term_id)

        # A recital that interprets articles: Article --INTERPRETED_BY--> Recital.
        for article_eid in prov.interprets_articles:
            if _is_valid_internal_ref(article_eid) and _ensure_provision_node(g, article_eid):
                g.add_edge(EdgeType.INTERPRETED_BY, article_eid, eid)

        if prov.effective_from is not None:
            iso = prov.effective_from.isoformat()
            g.add_node(
                f"date_{iso}",
                NodeType.DATE_MILESTONE,
                label=iso,
                props={"date": iso, "transitional": prov.transitional or None},
            )
            g.add_edge(EdgeType.APPLIES_FROM, eid, f"date_{iso}")

    if seed_vocab:
        _seed_controlled_vocabulary(g)

    return g
