"""Export a KnowledgeGraph to idempotent Neo4j Cypher scripts (plan §4).

Generates MERGE queries for nodes and edges, dual-labeling Provision nodes as :Article
for backwards-compatibility with production app queries.
"""

from __future__ import annotations

from typing import Any

from app.graph.knowledge_graph import KnowledgeGraph

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
    """Return the load script as a list of statements."""
    statements: list[str] = []

    if include_constraints:
        labels = sorted({n.type.value for n in graph.nodes.values()} | {"Article"})
        for label in labels:
            statements.append(
                f"CREATE CONSTRAINT constraint_{label}_id IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
            )

    for node in graph.nodes.values():
        set_props = dict(node.props)
        if node.label:
            set_props.setdefault("name", node.label)
        
        # Dual label Provision nodes as :Provision:Article for compatibility
        labels_str = node.type.value
        if node.type.value == "Provision":
            labels_str = "Provision:Article"

        stmt = f'MERGE (n:{labels_str} {{id: {_value(node.id)}}})'
        if set_props:
            stmt += f"\n  SET n += {_props_map(set_props)}"
        statements.append(stmt)

    for edge in graph.edges.values():
        src, tgt = graph.get_node(edge.source), graph.get_node(edge.target)
        if src is None or tgt is None:
            continue
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
    """Return the full load script joined with semicolons."""
    stmts = to_cypher_statements(graph, include_constraints=include_constraints)
    return ";\n".join(stmts) + ";\n"
