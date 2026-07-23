"""Backend-agnostic in-memory knowledge graph.

Deliberately dependency-light (stdlib + the ``Node``/``Edge`` pydantic models) so the
whole build + query surface is unit-testable offline. Export to a real store is a
separate concern (:mod:`euaiact.graph.cypher`).
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from .schema import Edge, EdgeType, Node, NodeType

__all__ = ["KnowledgeGraph"]


class KnowledgeGraph:
    """Nodes keyed by id, edges keyed by ``(type, source, target)``; both dedup on add."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[tuple[str, str, str], Edge] = {}

    # ---- construction -------------------------------------------------
    def add_node(
        self,
        id: str,
        type: NodeType,
        *,
        label: str = "",
        props: dict[str, Any] | None = None,
    ) -> Node:
        """Insert or merge a node. Re-adding an id fills empty label and merges props."""
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
        """Insert or merge a directed edge (dedup by type+source+target)."""
        edge = Edge(type=type, source=source, target=target, props=dict(props or {}))
        existing = self.edges.get(edge.key)
        if existing is None:
            self.edges[edge.key] = edge
            return edge
        if props:
            existing.props.update({k: v for k, v in props.items() if v is not None})
        return existing

    # ---- iteration / lookup -------------------------------------------
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

    # ---- structural convenience ---------------------------------------
    def children(self, id: str) -> list[str]:
        return self.neighbors(id, EdgeType.HAS_CHILD)

    def parent(self, id: str) -> str | None:
        parents = self.neighbors(id, EdgeType.HAS_CHILD, incoming=True)
        return parents[0] if parents else None

    def referencing(self, target_id: str, *, include_children: bool = False) -> list[str]:
        """Ids of provisions that cross-reference ``target_id`` (the plan's sanity query).

        With ``include_children`` a reference to any descendant of ``target_id`` counts
        (e.g. a ref to ``art_6__para_2__point_a`` also answers "references Art. 6(2)").
        """
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

    # ---- reporting / serialization ------------------------------------
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
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeGraph":
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
