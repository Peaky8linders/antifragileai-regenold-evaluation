"""User store for the Lexy sign-up funnel.

Each sign-up to the free Lexy EU AI Act Q&A app gets a fresh, durable
API key (``lexy_sk_<token>``) that authenticates the
``POST /api/v1/regenold/eu-ai-act/ask`` route. This module owns the
persistence + lookup for those users.

Design — mirrors :mod:`app.evidence.store`'s backend-selection pattern so
the same env knobs (``DATABASE_URL``) drive durability everywhere:

* :class:`PostgresUserStore` — when ``REGENOLD_USER_DB_URL`` /
  ``DATABASE_URL`` is a ``postgres(ql)://`` DSN (Railway's add-on
  auto-injects ``DATABASE_URL``). SQLAlchemy + the psycopg v3 driver are
  imported **lazily**; on any import / connect failure we fall back to
  in-memory so the route never 500s at startup over a missing dep.
* :class:`SQLiteUserStore` — when the DSN is ``sqlite://...`` (stdlib
  ``sqlite3``, zero extra deps). Point it at a Railway/Fly persistent
  volume to survive redeploys.
* :class:`InMemoryUserStore` — default (dev / tests). Keys are lost on
  restart; fine for a single-process harness.

Fast-path validation: a process-local ``set`` caches known keys so the
hot Q&A route does O(1) membership checks instead of a DB round-trip per
request. A cache MISS falls back to a single indexed DB lookup (covers
multi-worker deploys where a sign-up landed on a sibling worker), and a
hit there back-fills the cache. Negatives are never cached (a key created
on another worker must be discoverable on the next request).
"""
from __future__ import annotations

import os
import re
import secrets
import sqlite3
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import logging

logger = logging.getLogger(__name__)

__all__ = [
    "UserRecord",
    "InMemoryUserStore",
    "SQLiteUserStore",
    "PostgresUserStore",
    "generate_api_key",
    "normalise_email",
    "is_valid_email",
    "get_user_store",
    "reset_user_store_for_tests",
    "is_registered_user_key",
]

# ── Key format ────────────────────────────────────────────────────────────────
# ``lexy_sk_`` (secret key) + 24 url-safe random bytes (~32 chars). The
# prefix makes a leaked key greppable + identifiable in logs, and keeps it
# visually distinct from the partner ``P2P_REGENOLD_API_KEY``.
_KEY_PREFIX = "lexy_sk_"


def generate_api_key() -> str:
    """Return a fresh, high-entropy Lexy API key."""
    return _KEY_PREFIX + secrets.token_urlsafe(24)


# ── Email helpers ─────────────────────────────────────────────────────────────
# Deliberately permissive: this is a free lead-gen funnel, not an identity
# provider. We only reject obviously-malformed input. The address is the
# user's identifier (idempotent sign-up keys on it), so we normalise to
# lowercase + strip surrounding whitespace before storing / comparing.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalise_email(email: str) -> str:
    return (email or "").strip().lower()


def is_valid_email(email: str) -> bool:
    e = normalise_email(email)
    return bool(e) and len(e) <= 320 and _EMAIL_RE.match(e) is not None


# ── Record ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class UserRecord:
    email: str
    api_key: str
    name: str = ""
    company: str = ""
    created_at: str = ""

    def public_dict(self) -> dict[str, Any]:
        """Serialisable view safe to return over the wire."""
        return asdict(self)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ── Process-local known-key cache (shared across backends) ────────────────────
_KNOWN_KEYS: set[str] = set()
_KNOWN_KEYS_LOCK = threading.Lock()


def _cache_key(api_key: str) -> None:
    if not api_key:
        return
    with _KNOWN_KEYS_LOCK:
        _KNOWN_KEYS.add(api_key)


def _cache_has(api_key: str) -> bool:
    with _KNOWN_KEYS_LOCK:
        return api_key in _KNOWN_KEYS


def _cache_clear() -> None:
    with _KNOWN_KEYS_LOCK:
        _KNOWN_KEYS.clear()


# ── In-memory backend (default) ───────────────────────────────────────────────


class InMemoryUserStore:
    """Dict-backed store. Keys are lost on process restart."""

    def __init__(self) -> None:
        self._by_email: dict[str, UserRecord] = {}
        self._by_key: dict[str, UserRecord] = {}
        self._lock = threading.Lock()

    def create_or_get(
        self, email: str, name: str = "", company: str = ""
    ) -> tuple[UserRecord, bool]:
        norm = normalise_email(email)
        with self._lock:
            existing = self._by_email.get(norm)
            if existing is not None:
                return existing, False
            rec = UserRecord(
                email=norm,
                api_key=generate_api_key(),
                name=(name or "").strip()[:200],
                company=(company or "").strip()[:200],
                created_at=_now_iso(),
            )
            self._by_email[norm] = rec
            self._by_key[rec.api_key] = rec
        _cache_key(rec.api_key)
        return rec, True

    def get_by_email(self, email: str) -> UserRecord | None:
        with self._lock:
            return self._by_email.get(normalise_email(email))

    def get_by_api_key(self, api_key: str) -> UserRecord | None:
        if not api_key:
            return None
        with self._lock:
            return self._by_key.get(api_key)

    def has_api_key(self, api_key: str) -> bool:
        return self.get_by_api_key(api_key) is not None

    def count(self) -> int:
        with self._lock:
            return len(self._by_email)


# ── SQLite backend ────────────────────────────────────────────────────────────


class SQLiteUserStore:
    """Stdlib-sqlite3 store. Point the DSN at a persistent volume."""

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS regenold_users (
        email TEXT PRIMARY KEY,
        api_key TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL DEFAULT '',
        company TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_regenold_users_api_key
        ON regenold_users(api_key);
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path or ":memory:"
        self._lock = threading.Lock()
        # check_same_thread=False — FastAPI serves requests on a thread
        # pool; the lock serialises writes so a single shared connection
        # is safe.
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.executescript(self._SCHEMA)

    def _row_to_record(self, row: sqlite3.Row) -> UserRecord:
        return UserRecord(
            email=row["email"],
            api_key=row["api_key"],
            name=row["name"] or "",
            company=row["company"] or "",
            created_at=row["created_at"] or "",
        )

    def create_or_get(
        self, email: str, name: str = "", company: str = ""
    ) -> tuple[UserRecord, bool]:
        norm = normalise_email(email)
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM regenold_users WHERE email = ?", (norm,)
            )
            row = cur.fetchone()
            if row is not None:
                return self._row_to_record(row), False
            rec = UserRecord(
                email=norm,
                api_key=generate_api_key(),
                name=(name or "").strip()[:200],
                company=(company or "").strip()[:200],
                created_at=_now_iso(),
            )
            with self._conn:
                self._conn.execute(
                    "INSERT INTO regenold_users "
                    "(email, api_key, name, company, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (rec.email, rec.api_key, rec.name, rec.company, rec.created_at),
                )
        _cache_key(rec.api_key)
        return rec, True

    def get_by_email(self, email: str) -> UserRecord | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM regenold_users WHERE email = ?",
                (normalise_email(email),),
            )
            row = cur.fetchone()
        return self._row_to_record(row) if row else None

    def get_by_api_key(self, api_key: str) -> UserRecord | None:
        if not api_key:
            return None
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM regenold_users WHERE api_key = ?", (api_key,)
            )
            row = cur.fetchone()
        return self._row_to_record(row) if row else None

    def has_api_key(self, api_key: str) -> bool:
        return self.get_by_api_key(api_key) is not None

    def count(self) -> int:
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) AS c FROM regenold_users")
            return int(cur.fetchone()["c"])


# ── Postgres backend (lazy SQLAlchemy) ────────────────────────────────────────


class PostgresUserStore:
    """SQLAlchemy-backed store — durable across Railway redeploys.

    SQLAlchemy + the psycopg v3 driver are imported lazily inside
    :meth:`_engine` so importing this module never requires them. Mirrors
    the DSN normalisation in :mod:`app.evidence.store`.
    """

    _SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS regenold_users (
        email TEXT PRIMARY KEY,
        api_key TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL DEFAULT '',
        company TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_regenold_users_api_key
        ON regenold_users(api_key);
    """

    def __init__(self, *, database_url: str) -> None:
        self._database_url = database_url
        self._engine_obj: Any | None = None
        self._lock = threading.Lock()

    def _engine(self) -> Any:
        if self._engine_obj is not None:
            return self._engine_obj
        from sqlalchemy import create_engine, text  # noqa: PLC0415 — lazy

        url = self._database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://") and "+psycopg" not in url.split("://", 1)[0]:
            url = "postgresql+psycopg://" + url[len("postgresql://"):]

        engine = create_engine(
            url, future=True, pool_pre_ping=True, pool_size=5, max_overflow=5
        )
        with engine.begin() as conn:
            for stmt in self._SCHEMA_SQL.strip().split(";"):
                if stmt.strip():
                    conn.execute(text(stmt))
        self._engine_obj = engine
        return engine

    def create_or_get(
        self, email: str, name: str = "", company: str = ""
    ) -> tuple[UserRecord, bool]:
        from sqlalchemy import text  # noqa: PLC0415 — lazy

        norm = normalise_email(email)
        eng = self._engine()
        with self._lock, eng.begin() as conn:
            row = conn.execute(
                text("SELECT * FROM regenold_users WHERE email = :e"),
                {"e": norm},
            ).mappings().first()
            if row is not None:
                return (
                    UserRecord(
                        email=row["email"],
                        api_key=row["api_key"],
                        name=row["name"] or "",
                        company=row["company"] or "",
                        created_at=row["created_at"] or "",
                    ),
                    False,
                )
            rec = UserRecord(
                email=norm,
                api_key=generate_api_key(),
                name=(name or "").strip()[:200],
                company=(company or "").strip()[:200],
                created_at=_now_iso(),
            )
            conn.execute(
                text(
                    "INSERT INTO regenold_users "
                    "(email, api_key, name, company, created_at) "
                    "VALUES (:email, :api_key, :name, :company, :created_at)"
                ),
                rec.public_dict(),
            )
        _cache_key(rec.api_key)
        return rec, True

    def _fetch_one(self, where_sql: str, params: dict[str, Any]) -> UserRecord | None:
        from sqlalchemy import text  # noqa: PLC0415 — lazy

        eng = self._engine()
        with eng.connect() as conn:
            row = conn.execute(
                text(f"SELECT * FROM regenold_users WHERE {where_sql}"), params
            ).mappings().first()
        if row is None:
            return None
        return UserRecord(
            email=row["email"],
            api_key=row["api_key"],
            name=row["name"] or "",
            company=row["company"] or "",
            created_at=row["created_at"] or "",
        )

    def get_by_email(self, email: str) -> UserRecord | None:
        return self._fetch_one("email = :e", {"e": normalise_email(email)})

    def get_by_api_key(self, api_key: str) -> UserRecord | None:
        if not api_key:
            return None
        return self._fetch_one("api_key = :k", {"k": api_key})

    def has_api_key(self, api_key: str) -> bool:
        return self.get_by_api_key(api_key) is not None

    def count(self) -> int:
        from sqlalchemy import text  # noqa: PLC0415 — lazy

        eng = self._engine()
        with eng.connect() as conn:
            return int(conn.execute(text("SELECT COUNT(*) FROM regenold_users")).scalar() or 0)


# ── Backend selection + singleton ─────────────────────────────────────────────

_SINGLETON: Any | None = None
_SINGLETON_LOCK = threading.Lock()


def _sqlite_path_from_url(url: str) -> str:
    if url.startswith("sqlite://"):
        return url[len("sqlite://"):]
    return url


def _select_backend() -> Any:
    """Pick the backend from env. Prefers a dedicated ``REGENOLD_USER_DB_URL``
    over the shared ``DATABASE_URL`` so an operator can isolate the user table
    if they want. Falls back to in-memory on any driver-import failure."""
    dsn = (
        os.getenv("REGENOLD_USER_DB_URL", "").strip()
        or os.getenv("DATABASE_URL", "").strip()
    )
    if dsn.startswith("postgres://") or dsn.startswith("postgresql://"):
        try:
            import sqlalchemy  # noqa: F401, PLC0415 — probe-import only
            return PostgresUserStore(database_url=dsn)
        except ImportError as exc:
            logger.warning(
                "user_store: postgres driver unavailable, falling back to "
                "in-memory (keys will not survive restart): %s",
                exc,
            )
    if dsn.startswith("sqlite://"):
        return SQLiteUserStore(_sqlite_path_from_url(dsn))
    return InMemoryUserStore()


def get_user_store() -> Any:
    """Process-wide user store singleton (latched on first call)."""
    global _SINGLETON
    if _SINGLETON is None:
        with _SINGLETON_LOCK:
            if _SINGLETON is None:
                _SINGLETON = _select_backend()
    return _SINGLETON


def reset_user_store_for_tests() -> Any:
    """Drop the singleton + key cache and rebuild from a fresh env read."""
    global _SINGLETON
    with _SINGLETON_LOCK:
        _SINGLETON = _select_backend()
    _cache_clear()
    return _SINGLETON


def is_registered_user_key(api_key: str | None) -> bool:
    """Fast O(1) check (cache) with a single-DB-lookup fallback on miss.

    Called per Q&A request from the auth dependency + the rate-limit
    key func, so the hot path must stay cheap. Negatives are NOT cached
    (a key minted on a sibling worker must be discoverable next request).
    """
    if not api_key:
        return False
    if _cache_has(api_key):
        return True
    try:
        store = get_user_store()
        if store.has_api_key(api_key):
            _cache_key(api_key)
            return True
    except Exception as exc:  # noqa: BLE001 — never let a DB blip 500 the route
        logger.warning("user_store: key lookup failed (treating as unknown): %s", exc)
    return False
