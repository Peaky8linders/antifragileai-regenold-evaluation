"""In-memory Knowledge Graph for the EU AI Act (plan §4).

Includes the `KnowledgeGraph` data structure, deterministic in-text citation extractor,
and `build_graph()` builder.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable

from app.data.ids import ProvisionId, ProvisionIdError
from app.graph.schema import (
    ACTOR_VOCAB,
    RISK_CLASS_VOCAB,
    Edge,
    EdgeType,
    Node,
    NodeType,
)
from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "KnowledgeGraph",
    "extract_citations",
    "extract_reference_eids",
    "build_graph",
]


class ProvisionModel(BaseModel):
    """Structure-preserving provision chunk model."""

    model_config = ConfigDict(extra="allow")

    provision_id: str
    chunk_type: str = "article"
    text: str = ""
    citation: str = ""
    eli_uri: str = ""
    root_kind: str = ""
    parent_id: str | None = None
    article: int | None = None
    paragraph: int | None = None
    point: str | None = None
    subpoint: str | None = None
    annex: str | None = None
    annex_point: int | None = None
    recital: int | None = None
    chapter: int | None = None
    section: str | None = None
    parent_text: str | None = None
    defined_terms: list[str] = Field(default_factory=list)
    references_internal: list[str] = Field(default_factory=list)
    references_external: list[str] = Field(default_factory=list)
    interprets_articles: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Citation Extractor
# ---------------------------------------------------------------------------
_ARTICLE_RE = re.compile(r"Articles?\s+(\d+)((?:\s*\([0-9a-z]+\))*)")
_ANNEX_RE = re.compile(
    r"Annex\s+([IVXLCDM]+)(?:\s*,?\s*point\s+(\d+))?((?:\s*\([a-z]+\))*)", re.IGNORECASE
)
_RECITAL_RE = re.compile(r"[Rr]ecital\s+\(?(\d+)\)?")
_PAREN_RE = re.compile(r"\(([0-9a-z]+)\)")

_EXTERNAL_QUALIFIER_RE = re.compile(
    r"^\s*(?:of\s+)?(?:the\s+)?"
    r"(?:(?:Council|Commission|European\s+Parliament|Framework|Implementing|Delegated)\s+){0,3}"
    r"(GDPR|Charter|TFEU|TEU|Treaty|Regulation\s*\(?EU\)?|Regulation\s+No|Regulation\s+\d"
    r"|Directive|Decision\s+\d|Decision\s+No)",
    re.IGNORECASE,
)


def _is_external(text: str, end: int) -> bool:
    return bool(_EXTERNAL_QUALIFIER_RE.match(text[end : end + 48]))


def _from_citation_safe(citation: str) -> ProvisionId | None:
    try:
        return ProvisionId.from_citation(citation)
    except ProvisionIdError:
        return None


def extract_citations(text: str) -> list[ProvisionId]:
    """Return distinct provision ids cited in text, in first-seen order."""
    found: dict[str, ProvisionId] = {}

    def keep(pid: ProvisionId | None) -> None:
        if pid is not None and pid.eid not in found:
            found[pid.eid] = pid

    for m in _ARTICLE_RE.finditer(text):
        if _is_external(text, m.end()):
            continue
        num, tail = m.group(1), m.group(2)
        groups = _PAREN_RE.findall(tail)
        keep(_from_citation_safe(f"Art. {num}" + "".join(f"({g})" for g in groups)))

    for roman, point, tail in _ANNEX_RE.findall(text):
        citation = f"Annex {roman.upper()}"
        if point:
            citation += f" point {point}"
        citation += "".join(f"({g})" for g in _PAREN_RE.findall(tail))
        keep(_from_citation_safe(citation))

    for num in _RECITAL_RE.findall(text):
        keep(_from_citation_safe(f"Recital ({num})"))

    return list(found.values())


def extract_reference_eids(text: str, *, exclude: str | None = None) -> list[str]:
    return [pid.eid for pid in extract_citations(text) if pid.eid != exclude]


# ---------------------------------------------------------------------------
# KnowledgeGraph Data Structure
# ---------------------------------------------------------------------------
class KnowledgeGraph:
    """Nodes keyed by id, edges keyed by (type, source, target); both dedup on add."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[tuple[str, str, str], Edge] = {}

    def add_node(
        self,
        id: str,
        type: NodeType,
        *,
        label: str = "",
        props: dict[str, Any] | None = None,
    ) -> Node:
        existing = self.nodes.get(id)
        if existing is None:
            node = Node(id=id, type=type, label=label, props=dict(props or {}))
            self.nodes[id] = node
            return node
        if existing.type != type:
            raise ValueError(f"node {id!r} already exists as {existing.type} != {type}")
        if label and not existing.label:
            existing.label = label
        if props:
            existing.props.update({k: v for k, v in props.items() if v is not None})
        return existing

    def add_edge(
        self,
        type: EdgeType,
        source: str,
        target: str,
        *,
        props: dict[str, Any] | None = None,
    ) -> Edge:
        edge = Edge(type=type, source=source, target=target, props=dict(props or {}))
        existing = self.edges.get(edge.key)
        if existing is None:
            self.edges[edge.key] = edge
            return edge
        if props:
            existing.props.update({k: v for k, v in props.items() if v is not None})
        return existing

    def get_node(self, id: str) -> Node | None:
        return self.nodes.get(id)

    def nodes_of_type(self, type: NodeType) -> list[Node]:
        return [n for n in self.nodes.values() if n.type == type]

    def edges_of_type(self, type: EdgeType) -> list[Edge]:
        return [e for e in self.edges.values() if e.type == type]

    def out_edges(self, id: str, type: EdgeType | None = None) -> list[Edge]:
        return [e for e in self.edges.values() if e.source == id and (type is None or e.type == type)]

    def in_edges(self, id: str, type: EdgeType | None = None) -> list[Edge]:
        return [e for e in self.edges.values() if e.target == id and (type is None or e.type == type)]

    def neighbors(
        self, id: str, type: EdgeType | None = None, *, incoming: bool = False
    ) -> list[str]:
        edges = self.in_edges(id, type) if incoming else self.out_edges(id, type)
        return [e.source if incoming else e.target for e in edges]

    def children(self, id: str) -> list[str]:
        return self.neighbors(id, EdgeType.HAS_CHILD)

    def parent(self, id: str) -> str | None:
        parents = self.neighbors(id, EdgeType.HAS_CHILD, incoming=True)
        return parents[0] if parents else None

    def referencing(self, target_id: str, *, include_children: bool = False) -> list[str]:
        targets = {target_id}
        if include_children:
            targets |= set(self._descendants(target_id))
        out: set[str] = set()
        for e in self.edges.values():
            if e.type == EdgeType.CROSS_REFERENCES_INTERNAL and e.target in targets:
                out.add(e.source)
        return sorted(out)

    def _descendants(self, id: str) -> Iterable[str]:
        stack = list(self.children(id))
        while stack:
            cur = stack.pop()
            yield cur
            stack.extend(self.children(cur))

    def stats(self) -> dict[str, dict[str, int]]:
        return {
            "nodes": dict(sorted(Counter(n.type.value for n in self.nodes.values()).items())),
            "edges": dict(sorted(Counter(e.type.value for e in self.edges.values()).items())),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.model_dump() for n in self.nodes.values()],
            "edges": [e.model_dump() for e in self.edges.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeGraph:
        g = cls()
        for n in data.get("nodes", []):
            node = Node.model_validate(n)
            g.nodes[node.id] = node
        for e in data.get("edges", []):
            edge = Edge.model_validate(e)
            g.edges[edge.key] = edge
        return g

    def __len__(self) -> int:
        return len(self.nodes)

    def __repr__(self) -> str:
        return f"KnowledgeGraph(nodes={len(self.nodes)}, edges={len(self.edges)})"


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------
_VALID_ARTICLES = frozenset(range(1, 114))
_VALID_RECITALS = frozenset(range(1, 181))
_VALID_ANNEXES = frozenset(["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"])


def _is_valid_internal_ref(eid: str) -> bool:
    try:
        pid = ProvisionId.from_eid(eid)
    except ProvisionIdError:
        return False
    root = pid.root_kind
    val = pid.segments[0].value
    if root == "article":
        return val.isdigit() and int(val) in _VALID_ARTICLES
    if root == "recital":
        return val.isdigit() and int(val) in _VALID_RECITALS
    if root == "annex":
        return val.upper() in _VALID_ANNEXES
    return True


def _node_type_for(pid: ProvisionId) -> NodeType:
    if pid.root_kind == "recital":
        return NodeType.RECITAL
    if pid.root_kind == "annex":
        if pid.point_label is None:
            return NodeType.ANNEX
        return NodeType.ANNEX_POINT
    return NodeType.PROVISION


def _ensure_provision_node(g: KnowledgeGraph, eid: str) -> bool:
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
        props={"eid": eid, "citation": pid.citation, "synthesized": True},
    )
    return True


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
    provisions: Iterable[Any],
    *,
    extract_text_citations: bool = True,
    seed_vocab: bool = True,
) -> KnowledgeGraph:
    """Build the deterministic knowledge-graph backbone from provisions."""
    g = KnowledgeGraph()
    prov_list = list(provisions)

    if seed_vocab:
        _seed_controlled_vocabulary(g)

    # Pass 1 — add nodes
    for prov in prov_list:
        eid = getattr(prov, "provision_id", None) or str(prov.get("provision_id"))
        citation = getattr(prov, "citation", None) or str(prov.get("citation", eid))
        try:
            pid = ProvisionId.from_eid(eid)
            ntype = _node_type_for(pid)
        except ProvisionIdError:
            ntype = NodeType.PROVISION

        text = getattr(prov, "text", None) or str(prov.get("text", ""))
        g.add_node(eid, ntype, label=citation, props={"eid": eid, "citation": citation, "text": text})

    # Pass 2 — structural hierarchy and cross-references
    for prov in prov_list:
        eid = getattr(prov, "provision_id", None) or str(prov.get("provision_id"))
        try:
            pid = ProvisionId.from_eid(eid)
            p_eid = pid.parent_eid
            if p_eid:
                _ensure_provision_node(g, p_eid)
                g.add_edge(EdgeType.HAS_CHILD, p_eid, eid)
        except ProvisionIdError:
            pass

        text = getattr(prov, "text", None) or str(prov.get("text", ""))
        if extract_text_citations and text:
            for ref_eid in extract_reference_eids(text, exclude=eid):
                if _is_valid_internal_ref(ref_eid) and _ensure_provision_node(g, ref_eid):
                    g.add_edge(
                        EdgeType.CROSS_REFERENCES_INTERNAL,
                        eid,
                        ref_eid,
                        props={"provenance": "text"},
                    )

    return g
