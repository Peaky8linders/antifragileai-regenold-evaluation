"""Export a :class:`KnowledgeGraph` to idempotent Neo4j Cypher.

Neo4j (2026.x) remains the primary store (verified 2026-07-22). The emitter is pure
string-building — no driver dependency — so it stays offline-testable; the ``neo4j``
Python driver only enters at load time. Output is idempotent (``MERGE`` on ``id`` +
``SET``), so re-running the script converges rather than duplicating.
"""

from __future__ import annotations

from typing import Any

from .model import KnowledgeGraph

__all__ = ["to_cypher", "to_cypher_statements"]


def _escape(s: str) -> str:
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def _value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_value(x) for x in v) + "]"
    if v is None:
        return "null"
    return f'"{_escape(str(v))}"'


def _props_map(props: dict[str, Any]) -> str:
    return "{" + ", ".join(f"{k}: {_value(v)}" for k, v in props.items()) + "}"


def to_cypher_statements(graph: KnowledgeGraph, *, include_constraints: bool = True) -> list[str]:
    """Return the load script as a list of statements (no trailing semicolons)."""
    statements: list[str] = []

    if include_constraints:
        for label in sorted({n.type.value for n in graph.nodes.values()}):
            statements.append(
                f"CREATE CONSTRAINT constraint_{label}_id IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
            )

    for node in graph.nodes.values():
        set_props = dict(node.props)
        if node.label:
            set_props.setdefault("name", node.label)
        stmt = f'MERGE (n:{node.type.value} {{id: {_value(node.id)}}})'
        if set_props:
            stmt += f"\n  SET n += {_props_map(set_props)}"
        statements.append(stmt)

    for edge in graph.edges.values():
        src, tgt = graph.get_node(edge.source), graph.get_node(edge.target)
        if src is None or tgt is None:
            continue  # dangling edge — skip rather than emit an unmatchable MATCH
        stmt = (
            f"MATCH (a:{src.type.value} {{id: {_value(edge.source)}}}), "
            f"(b:{tgt.type.value} {{id: {_value(edge.target)}}})\n"
            f"  MERGE (a)-[r:{edge.type.value}]->(b)"
        )
        if edge.props:
            stmt += f"\n  SET r += {_props_map(edge.props)}"
        statements.append(stmt)

    return statements


def to_cypher(graph: KnowledgeGraph, *, include_constraints: bool = True) -> str:
    """Return the full load script (statements joined with ``;``)."""
    stmts = to_cypher_statements(graph, include_constraints=include_constraints)
    return ";\n".join(stmts) + ";\n"
