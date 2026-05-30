"""Shared RushDB connection settings (Hybrid RAG Guide §2)."""
from __future__ import annotations

import os
from typing import Any

DEFAULT_RUSHDB_BASE_URL = "https://api.rushdb.com/api/v1"


def graph_backend() -> str:
    """Resolve the active graph backend.

    R98 switch-back: **Neo4j Aura is the default again.** The 2026-05-25
    RushDB migration hit RushDB's free-trial limits, so the durable graph
    path reverts to the Neo4j Aura instance whose ``NEO4J_URI`` /
    ``NEO4J_USERNAME`` / ``NEO4J_PASSWORD`` live in Railway. RushDB is now
    strictly opt-in via ``REGENOLD_GRAPH_BACKEND=rushdb``.

    Accepted values (case-insensitive): ``neo4j`` (default), ``rushdb``.
    Anything unrecognised falls back to ``neo4j`` — the safe default that
    keeps the deterministic + Neo4j path active.
    """
    raw = (os.environ.get("REGENOLD_GRAPH_BACKEND") or "neo4j").strip().lower()
    return raw if raw in {"neo4j", "rushdb"} else "neo4j"


def rushdb_backend_selected() -> bool:
    """True only when RushDB is the explicitly-selected graph backend.

    This is the master kill-switch for the RushDB dual-path. When it
    returns ``False`` (the default), every RushDB surface — 2-hop expand,
    definition/recital lookup, hybrid retrieval, boot auto-seed, and the
    ``/healthz/graph`` RushDB-first probe — goes inert regardless of
    whether ``RUSHDB_AUTH_TOKEN`` is still present in the environment, and
    the engine uses the Neo4j Aura path instead.
    """
    return graph_backend() == "rushdb"


def resolve_auth_token() -> str | None:
    """Return ``RUSHDB_AUTH_TOKEN`` or ``RUSHDB_API_KEY`` (either works)."""
    token = os.environ.get("RUSHDB_AUTH_TOKEN") or os.environ.get("RUSHDB_API_KEY")
    if not token:
        return None
    token = token.strip()
    return token or None


def resolve_base_url() -> str:
    """Base URL for the RushDB API (``RUSHDB_BASE_URL`` or legacy ``RUSHDB_URL``)."""
    raw = os.environ.get("RUSHDB_BASE_URL") or os.environ.get("RUSHDB_URL")
    return (raw or DEFAULT_RUSHDB_BASE_URL).strip()


def create_rushdb_client() -> Any | None:
    """Construct a RushDB client or return ``None`` when auth is missing."""
    token = resolve_auth_token()
    if not token:
        return None

    import rushdb

    base_url = resolve_base_url()
    try:
        return rushdb.RushDB(api_key=token, base_url=base_url)
    except TypeError:
        # Older rushdb wheels use positional auth_token + url= keyword.
        return rushdb.RushDB(token, url=base_url)


def is_configured() -> bool:
    """True when an auth env var is set (does not verify connectivity)."""
    return resolve_auth_token() is not None
