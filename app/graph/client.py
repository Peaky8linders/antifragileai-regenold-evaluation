"""Neo4j graph client — disabled stub.

The full CodexAI engine uses Neo4j as a cache layer over the KB-projected
compliance graph. The stub returns a client with ``enabled=False`` so
``graph_rag.py`` takes its built-in KB-fallback path. Restoring real
Neo4j is a one-file swap: drop the ``neo4j`` SDK into the venv and
replace this file with the parent-repo version.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _DisabledClient:
    enabled: bool = False

    def execute_read(self, *_args: object, **_kwargs: object) -> list[dict]:
        return []

    def close(self) -> None:
        return None


_SINGLETON: _DisabledClient | None = None


def get_graph_client() -> _DisabledClient:
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = _DisabledClient()
    return _SINGLETON
