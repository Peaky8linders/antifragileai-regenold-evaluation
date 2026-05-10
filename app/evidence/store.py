"""Audit-chain store — in-memory recorder.

The Regenold route writes a best-effort evidence entry per request via
``get_evidence_store().record(...)``. The full CodexAI store backs this
with a hash-chained SQLite/Postgres table; this bundle records into an
in-process list so the wire shape is preserved and tests don't need a
database.

API surface preserved:
* ``record(entry_type, payload, article_ref, created_by, tenant_id)``
* ``get_chain(tenant_id=None, limit=...)`` — newest-first.

Partners who want durable audit can plug their own backend in by
replacing this file (the wire shape is the only contract callers
depend on).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterator

logger = logging.getLogger(__name__)


@dataclass
class _RecordedEntry:
    entry_type: str
    payload: dict[str, Any]
    article_ref: str
    created_by: str
    tenant_id: str | None


@dataclass
class _NoOpStore:
    records: list[_RecordedEntry] = field(default_factory=list)

    def record(
        self,
        *,
        entry_type: Any,
        payload: dict[str, Any],
        article_ref: str = "",
        created_by: str = "",
        tenant_id: str | None = None,
    ) -> None:
        et = entry_type.value if hasattr(entry_type, "value") else str(entry_type)
        self.records.append(
            _RecordedEntry(
                entry_type=et,
                payload=dict(payload),
                article_ref=article_ref,
                created_by=created_by,
                tenant_id=tenant_id,
            )
        )
        logger.debug(
            "evidence.record entry_type=%s tenant_id=%s article_ref=%s",
            et,
            tenant_id,
            article_ref,
        )

    def get_chain(
        self,
        *,
        tenant_id: str | None = None,
        limit: int = 100,
    ) -> Iterator[_RecordedEntry]:
        """Return entries (newest-first), optionally filtered by tenant.

        Mirrors the CodexAI ``AuditStore.get_chain`` contract: when
        ``tenant_id`` is ``None`` the caller receives every row;
        otherwise rows with a matching ``tenant_id`` only. Capped at
        ``limit``.
        """
        rows = reversed(self.records)
        filtered: list[_RecordedEntry] = []
        for row in rows:
            if tenant_id is not None and row.tenant_id != tenant_id:
                continue
            filtered.append(row)
            if len(filtered) >= limit:
                break
        return iter(filtered)


_SINGLETON: _NoOpStore | None = None


def get_evidence_store() -> _NoOpStore:
    """Return the process-wide in-memory store."""
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = _NoOpStore()
    return _SINGLETON


def reset_evidence_store_for_tests() -> _NoOpStore:
    """Tests + eval runners call this between batches to keep the
    in-process list bounded."""
    global _SINGLETON
    _SINGLETON = _NoOpStore()
    return _SINGLETON
