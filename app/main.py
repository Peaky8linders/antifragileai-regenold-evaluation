"""FastAPI app — mounts the Regenold partner endpoint and a /healthz probe.

Stripped-down extract — only the surface needed to exercise
``POST /api/v1/regenold/eu-ai-act/ask`` end-to-end via TestClient or
``uvicorn app.main:app``.
"""
from __future__ import annotations

import logging
import os
import threading as _threading
from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException, Request, status
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.llm import resolve_provider
from app.rate_limit import limiter, rate_limit_handler
from app.routes.auth import auth_router
from app.routes.regenold import regenold_router

logger = logging.getLogger(__name__)

# Fail-loud at module-import on a typo in P2P_GRAPH_RAG_PROVIDER. Without
# this, a typo like "anthropc" silently degrades every request to the
# deterministic-fallback path with no operator-visible signal — the eval
# snapshot would "complete normally" but every scenario took the non-LLM
# path. Boot-time validation surfaces the typo before any traffic hits.
try:
    resolve_provider(
        os.getenv("P2P_GRAPH_RAG_PROVIDER"),
        default_when_auto="openrouter",
    )
except ValueError as _exc:
    raise RuntimeError(
        f"P2P_GRAPH_RAG_PROVIDER is misconfigured: {_exc}. "
        "Valid values: openrouter / bedrock / anthropic / cli / openai_wrapper / auto / "
        "(unset = auto). See app/llm/__init__.py::resolve_provider."
    ) from _exc


app = FastAPI(
    title="Regenold EU AI Act RAG",
    version=settings.version,
    description=(
        "Standalone bundle extracted from CodexAI / legit-ai for partner "
        "transparency review. Exposes the same Regenold grounded Q&A "
        "surface as the parent repo."
    ),
)


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)


api_v1 = FastAPI(
    title="Regenold EU AI Act RAG — API v1",
    version=settings.version,
)
api_v1.state.limiter = limiter
api_v1.add_exception_handler(RateLimitExceeded, rate_limit_handler)
api_v1.add_middleware(SlowAPIMiddleware)
api_v1.include_router(regenold_router)
api_v1.include_router(auth_router)


app.mount("/api/v1", api_v1)


@app.on_event("startup")
def _log_llm_provider_status() -> None:
    """Log the resolved LLM provider once at boot.

    Operator-visible signal that the wrapper / Anthropic knobs took
    effect. We deliberately do NOT probe the wrapper live
    here — a long boot-time probe (the Claude CLI subprocess takes
    several seconds to spin up) would block uvicorn's startup and
    delay the first /healthz return. Operators who need a live probe
    hit /healthz/llm instead. Skip when REGENOLD_SKIP_STARTUP_LOG=1
    (test harness uses this to keep TestClient output clean).
    """
    if os.getenv("REGENOLD_SKIP_STARTUP_LOG") == "1":
        return

    def _intent_model_for_log() -> str:
        """Ask the intent classifier which model it will actually use.

        ⚠ R350 — this line used to re-derive the default itself, as
        ``os.getenv("REGENOLD_INTENT_MODEL", "claude-haiku-4-5-20251001")``.
        R346.2 moved the real default to Sonnet 4.6 ("no Haiku on the live
        path") and did not update the log, so with the variable unset — the
        DEPLOYED configuration, since ``railway.toml [deploy.envs]`` has never
        applied — the boot line advertised a model the process would never
        call. A provenance surface asserting the wrong model is the same
        false-attribution class as the ``METRIC_PROVENANCE`` "Sentence-BERT"
        label: worse than no record, because it is confidently wrong. One
        concept, one definition — ask the owner.
        """
        try:
            from app.llm.intent_classifier import intent_model

            return intent_model()
        except Exception:  # noqa: BLE001 — a log line must never break boot
            return "unknown"

    provider_label = resolve_provider(
        os.getenv("P2P_GRAPH_RAG_PROVIDER"),
        default_when_auto="openrouter",
    )
    if provider_label == "openai_wrapper":
        base = (
            os.getenv("OPENAI_API_BASE", "").strip()
            or "https://wrapper.antifragile-ai.net/v1"
        )
        logger.info(
            "regenold.startup provider=openai_wrapper endpoint=%s "
            "intent_model=%s graph_rag_model=%s — hit /healthz/llm for a "
            "live probe",
            base,
            _intent_model_for_log(),
            settings.graph_rag.model,
        )
    elif provider_label == "anthropic":
        configured = settings.graph_rag.api_key is not None
        logger.info(
            "regenold.startup provider=anthropic api_key_configured=%s model=%s",
            configured,
            settings.graph_rag.model,
        )
    elif provider_label == "openrouter":
        from app.llm.openai_wrapper_provider import is_openrouter_provider_enabled
        configured = is_openrouter_provider_enabled()
        logger.info(
            "regenold.startup provider=openrouter api_key_configured=%s model=%s "
            "intent_model=%s graph_rag_model=%s",
            configured,
            settings.graph_rag.model,
            _intent_model_for_log(),
            settings.graph_rag.model,
        )
    elif provider_label == "bedrock":
        try:
            from app.llm.bedrock_client import is_bedrock_provider_enabled, _resolve_region, _resolve_default_model
            configured = is_bedrock_provider_enabled()
            region = _resolve_region()
            default_m = _resolve_default_model()
        except Exception:
            configured = False
            region = "unknown"
            default_m = "unknown"
        logger.info(
            "regenold.startup provider=bedrock configured=%s region=%s model=%s",
            configured,
            region,
            default_m,
        )
    else:
        logger.info(
            "regenold.startup provider=%s (deterministic path; no LLM calls)",
            provider_label,
        )

    # ─── Embedded-graph boot-time status (R129 default backend) ───────────
    # When ``REGENOLD_GRAPH_BACKEND=embedded`` (the R129 default) the live
    # 2-hop backend is the in-process SQLite property graph, NOT Neo4j. The
    # Neo4j probe below would report it as "did not activate" (the driver is
    # gated OFF), so surface the embedded graph's real build status here and
    # SKIP the misleading Neo4j warning. Read-only, sub-ms, never raises.
    try:
        from app.graph.embedded_graph import (
            embedded_backend_selected,
            get_embedded_graph,
        )

        _embedded_selected = embedded_backend_selected()
    except Exception:  # noqa: BLE001 — boot log must never block startup
        _embedded_selected = False
    if _embedded_selected:
        try:
            _eg = get_embedded_graph()
            if _eg.enabled:
                logger.info(
                    "regenold.startup graph_backend=embedded enabled=True "
                    "node_count=%d edge_count=%d",
                    _eg.node_count(),
                    _eg.edge_count(),
                )
            else:
                logger.warning(
                    "regenold.startup graph_backend=embedded enabled=False — "
                    "the in-process graph build FAILED. 2-hop expansion is a "
                    "no-op; the engine still serves via the deterministic KB "
                    "path. Check earlier 'embedded_graph build failed' logs."
                )
        except Exception as _eexc:  # noqa: BLE001
            logger.warning(
                "regenold.startup graph_backend=embedded probe failed: %s",
                _eexc,
            )
        return

    # ─── Neo4j boot-time status ────────────────────────────────────────────
    # Mirror the LLM startup log. Operators who set ``NEO4J_URI`` want a
    # single boot-log line confirming the graph is reachable AND seeded,
    # without having to curl ``/healthz/graph`` from inside the cluster.
    # We deliberately keep the failure path quiet (one warning, no traceback)
    # so a misconfigured Neo4j never blocks startup — the engine just falls
    # back to its deterministic KB path.
    # R321 — the probe below runs on a BOUNDED budget in a worker thread.
    #
    # This is a SYNC ``@app.on_event("startup")`` handler, so uvicorn finishes
    # it before it serves anything. `config.py` sets connection_timeout=5.0 /
    # max_retries=2 / retry_backoff=0.5, and client.py passes no
    # ``connection_acquisition_timeout`` (driver default 60 s), so against a
    # HUNG host — a paused or stale Aura instance, exactly the case that keeps
    # recurring here — health_check + get_stats measured 16.5 s + 49.6 s =
    # 66.1 s, versus railway.toml's healthcheckTimeout = 30. Boot would miss
    # the window and the release would fail. A fast-failing host (DNS
    # NXDOMAIN, ~1.6 s) was always fine; the hang is the deploy-blocking case.
    #
    # This is a LOG LINE. It must never be able to cost more than its own
    # information is worth, so it is capped and the timeout is swallowed —
    # the engine's deterministic KB path serves regardless (R99.1).
    if os.getenv("NEO4J_URI"):
        try:
            import concurrent.futures as _cf  # noqa: PLC0415

            from app.graph.client import get_graph_client
            _gc = get_graph_client()
            if _gc.enabled:
                _probe_budget_s = 3.0
                try:
                    _probe_budget_s = max(
                        0.5, min(15.0, float(os.getenv("REGENOLD_GRAPH_BOOT_PROBE_S", "3")))
                    )
                except ValueError:
                    _probe_budget_s = 3.0
                _pool = _cf.ThreadPoolExecutor(max_workers=1)
                try:
                    _hc = _pool.submit(_gc.health_check).result(timeout=_probe_budget_s)
                except _cf.TimeoutError:
                    # Same discipline as the auto-seed probe below: only the
                    # BUDGET case is swallowed here. A driver exception falls
                    # through to the outer handler, which already logs
                    # "graph probe failed".
                    logger.warning(
                        "regenold.startup graph_boot_probe_timeout budget_s=%s "
                        "— skipping the boot graph line",
                        _probe_budget_s,
                    )
                    _hc = {"status": "unknown"}
                finally:
                    # Do NOT join a hung driver call — that would re-introduce
                    # the block this fix exists to remove.
                    _pool.shutdown(wait=False)
                if _hc.get("status") == "healthy":
                    try:
                        # R321 — get_stats() measured 49.6 s alone against a
                        # hung host; bound it on the same budget as the probe
                        # above (it is the larger half of the 66 s).
                        _spool = _cf.ThreadPoolExecutor(max_workers=1)
                        try:
                            _stats = _spool.submit(_gc.get_stats).result(
                                timeout=_probe_budget_s
                            )
                        finally:
                            _spool.shutdown(wait=False)
                        logger.info(
                            "regenold.startup graph_enabled=True "
                            "seed_version=%s node_count=%d edge_count=%d",
                            _stats.seed_version or "<unset>",
                            _stats.total_nodes,
                            _stats.total_edges,
                        )
                    except Exception as _se:  # noqa: BLE001
                        logger.warning(
                            "regenold.startup graph_enabled=True "
                            "stats_unavailable=%s",
                            _se,
                        )
                else:
                    logger.warning(
                        "regenold.startup graph_enabled=True but health_check "
                        "returned status=%s — engine will use deterministic "
                        "fallback. Hit /healthz/graph for details.",
                        _hc.get("status"),
                    )
            else:
                logger.warning(
                    "regenold.startup NEO4J_URI is set but the graph client "
                    "did not activate (driver missing or connect failed). "
                    "Engine will use deterministic fallback."
                )
        except Exception as _exc:  # noqa: BLE001 — boot log must never block startup
            logger.warning(
                "regenold.startup graph probe failed: %s — engine will use "
                "deterministic fallback",
                _exc,
            )


# ─── Auto-seed on startup ────────────────────────────────────────────────
#
# Production Aura is a shared, durable knowledge graph.  Startup therefore
# treats it as read-only unless an operator explicitly opts in with
# ``NEO4J_AUTO_SEED=1``.  Even with that opt-in, the boot path seeds only a
# graph proven to contain zero nodes; version drift is migration work, not a
# reason for an application worker to rewrite a non-empty graph.  The thread
# is fire-and-forget
# — uvicorn's startup never blocks on graph I/O. Multi-worker safety is
# handled by a process-local lock plus an opt-in Postgres advisory lock
# (when ``DATABASE_URL`` is set, only ONE worker actually performs the
# write; the others observe the seeded graph on their next health probe).


# Module-level guard so even within a single process two startup hooks
# can't both fire the seeder. ``daemon=True`` is critical — uvicorn
# exits cleanly even if the seed thread is mid-write.
_AUTO_SEED_LOCK = _threading.Lock()
_AUTO_SEED_STARTED = False


def _auto_seed_disabled_by_env() -> bool:
    """Return True unless ``NEO4J_AUTO_SEED`` explicitly opts in.

    Aura is shared production state, so an unset, blank, malformed, or false
    value is disabled.  Only ``1`` / ``true`` / ``yes`` / ``on`` enables the
    empty-graph bootstrap path.
    """
    raw = os.getenv("NEO4J_AUTO_SEED")
    return raw is None or raw.strip().lower() not in {"1", "true", "yes", "on"}


def _acquire_postgres_advisory_lock() -> object | None:
    """Best-effort Postgres advisory lock — returns a context handle or None.

    When ``DATABASE_URL`` points at a real Postgres, we grab a
    session-scoped advisory lock so only ONE uvicorn worker actually
    runs the seed. The lock is released when the returned handle's
    ``release()`` is called (or when the connection closes).

    Returns ``None`` when:

    * ``DATABASE_URL`` is unset / non-Postgres (sqlite://, in-memory).
    * The ``psycopg`` driver is not importable.
    * The lock could not be acquired (another worker holds it — that's
      the GOOD path; the caller should skip seeding).
    * Any other error — we fall back to the process-local
      ``_AUTO_SEED_LOCK``, which is enough because ``MERGE``-based
      seeding is idempotent.

    The advisory lock key is a fixed 64-bit constant derived from
    ``"regenold_neo4j_auto_seed"`` — picked once and never collides
    with other Postgres advisory-lock users in the database.
    """
    dsn = os.getenv("DATABASE_URL", "").strip()
    if not dsn or not dsn.startswith("postgres"):
        return None

    try:
        import psycopg  # type: ignore[import-not-found]
    except ImportError:
        return None

    try:
        # The seeder needs maybe 5-10 s total; a 30 s lock timeout is
        # plenty. Normalise the DSN the same way evidence store does.
        conn_dsn = dsn
        if conn_dsn.startswith("postgresql+psycopg://"):
            conn_dsn = "postgresql://" + conn_dsn[len("postgresql+psycopg://"):]
        conn = psycopg.connect(conn_dsn, connect_timeout=10)
    except Exception as exc:  # noqa: BLE001
        logger.debug("auto-seed advisory-lock connect failed: %s", exc)
        return None

    # Fixed 64-bit advisory lock key. Hand-picked so it's deterministic
    # and stable across deploys; pg_try_advisory_lock returns False
    # when another session already holds the lock.
    LOCK_KEY = 7340518364729403841  # arbitrary, fixed
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,))
            row = cur.fetchone()
            acquired = bool(row and row[0])
        if not acquired:
            conn.close()
            return False
    except Exception as exc:  # noqa: BLE001
        logger.debug("auto-seed advisory-lock acquire failed: %s", exc)
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass
        return None

    class _AdvisoryLockHandle:
        """Releases the lock + closes the connection."""

        def __init__(self, _conn: Any, _key: int) -> None:
            self._conn = _conn
            self._key = _key
            self._released = False

        def release(self) -> None:
            if self._released:
                return
            self._released = True
            try:
                with self._conn.cursor() as cur:
                    cur.execute("SELECT pg_advisory_unlock(%s)", (self._key,))
            except Exception as exc:  # noqa: BLE001
                logger.debug("auto-seed advisory-unlock failed: %s", exc)
            try:
                self._conn.close()
            except Exception:  # noqa: BLE001
                pass

    return _AdvisoryLockHandle(conn, LOCK_KEY)


def _run_auto_seed_in_thread(reason: str) -> None:
    """Seed body — runs inside the daemon thread.

    Captures every exception so a misconfigured Neo4j (auth refused,
    schema drift, etc.) never escapes the thread and never affects
    request serving.
    """
    import time as _time

    started = _time.perf_counter()
    lock_handle = _acquire_postgres_advisory_lock()
    # If DATABASE_URL was set + we couldn't acquire the lock, another
    # worker is seeding. Skip + log. If DATABASE_URL was unset or the
    # driver is missing, ``lock_handle`` is None and we fall back to the
    # process-local lock — that's fine because MERGE is idempotent so
    # two workers racing is benign (just wasteful).
    if (
        lock_handle is False
        and os.getenv("DATABASE_URL", "").strip().startswith("postgres")
    ):
        logger.info(
            "regenold.startup auto_seed_skipped reason=advisory_lock_held "
            "(another worker is seeding)"
        )
        return

    try:
        from scripts.seed_neo4j_kb import run_seed

        result = run_seed(dry_run=False, clear=False, verbose=False)
        elapsed = _time.perf_counter() - started
        if result.get("status") == "ok":
            logger.info(
                "regenold.startup auto_seed_completed reason=%s nodes=%d "
                "edges=%d seed_version=%s elapsed_s=%.2f",
                reason,
                result.get("total_nodes", 0),
                result.get("total_edges", 0),
                result.get("seed_version", "<unset>"),
                elapsed,
            )
        else:
            logger.warning(
                "regenold.startup auto_seed_failed reason=%s status=%s "
                "elapsed_s=%.2f",
                reason,
                result.get("status"),
                elapsed,
            )
    except Exception as exc:  # noqa: BLE001 — best-effort, must never crash uvicorn
        logger.warning(
            "regenold.startup auto_seed_exception reason=%s err=%s — engine "
            "will use deterministic fallback",
            reason,
            exc,
        )
    finally:
        if lock_handle is not None:
            try:
                lock_handle.release()
            except Exception:  # noqa: BLE001
                pass


@app.on_event("startup")
def _maybe_auto_seed_neo4j() -> None:
    """Optionally seed Neo4j on boot — non-blocking, env-gated.

    Runs after :func:`_log_llm_provider_status` (registration order).
    Decision tree:

    1. No ``NEO4J_URI`` → log ``action=disabled-no-uri`` and return.
    2. Unless ``NEO4J_AUTO_SEED=1/true/yes/on`` → log
       ``action=disabled-by-env``.  Startup is read-only by default.
    3. ``REGENOLD_AUTO_SEED_LEADER_ONLY=1`` (default) AND uvicorn passes
       a worker index env var > 0 → log ``action=skip-non-leader``.
    4. ``GraphClient`` disabled → log ``action=skip-graph-disabled``.
    5. Strictly query metadata and total node count.  A timeout or read error
       is fail-closed and never authorises a write.
    6. If the graph is current, skip.  If it is non-empty but drifted, report
       the mismatch and skip.  Only a graph proven empty is seeded.

    Skip entirely when ``REGENOLD_SKIP_STARTUP_LOG=1`` — tests use this
    to keep TestClient output clean (and to avoid spinning up the seeder
    background thread during fixture-heavy test runs).
    """
    global _AUTO_SEED_STARTED

    if os.getenv("REGENOLD_SKIP_STARTUP_LOG") == "1":
        return

    if not os.environ.get("NEO4J_URI"):
        logger.info(
            "regenold.startup auto_seed_check action=disabled-no-uri"
        )
        return

    if _auto_seed_disabled_by_env():
        logger.info(
            "regenold.startup auto_seed_check action=disabled-by-env "
            "NEO4J_AUTO_SEED=%s",
            os.getenv("NEO4J_AUTO_SEED", ""),
        )
        return

    # ── Leader-only gate ─────────────────────────────────────────────────
    # When uvicorn is launched with ``--workers N`` it forks N child
    # processes; each one runs the startup hook independently. Without
    # coordination, every worker would try to seed in parallel — wasteful
    # but ultimately safe (MERGE is idempotent). We still try to filter
    # down to the leader using whichever signal is available:
    #
    #   * Uvicorn doesn't expose worker index by default. Operators who
    #     want strict leader-only can set REGENOLD_WORKER_INDEX=0 on
    #     worker 0 and a non-zero value on the rest via gunicorn's
    #     post_fork hook.
    #
    # If the index is unset (the default), the Postgres advisory lock
    # acquired inside ``_run_auto_seed_in_thread`` handles the race.
    if os.getenv("REGENOLD_AUTO_SEED_LEADER_ONLY", "1").strip() == "1":
        worker_idx = os.getenv("REGENOLD_WORKER_INDEX", "").strip()
        if worker_idx and worker_idx != "0":
            logger.info(
                "regenold.startup auto_seed_check action=skip-non-leader "
                "worker_idx=%s",
                worker_idx,
            )
            return

    # ── Decide: seed or skip based on KBMetadata ────────────────────────
    try:
        from app.data.kb import KB_VERSION
        from app.graph.client import get_graph_client
        from scripts.seed_neo4j_kb import SEED_VERSION

        client = get_graph_client()
        if not client.enabled:
            logger.info(
                "regenold.startup auto_seed_check action=skip-graph-disabled "
                "(NEO4J_URI set but driver/connection unavailable)"
            )
            return

        # R321 — bounded, for the same reason as the boot probe above: this
        # runs SYNCHRONOUSLY in the startup hook, BEFORE the seeder thread is
        # spawned, so a hung NEO4J_URI blocks uvicorn from serving and the
        # Railway healthcheck (30 s) fails the release. Measured 35 s of boot
        # remaining after the probe fix until this call was bounded too.
        # Timing out here must be fail-closed: inability to read shared Aura
        # state is not evidence that the graph is empty and never authorises a
        # background write.
        import concurrent.futures as _cf  # noqa: PLC0415

        _meta_budget_s = 3.0
        try:
            _meta_budget_s = max(
                0.5, min(15.0, float(os.getenv("REGENOLD_GRAPH_BOOT_PROBE_S", "3")))
            )
        except ValueError:
            _meta_budget_s = 3.0
        _mpool = _cf.ThreadPoolExecutor(max_workers=1)
        try:
            strict_read = getattr(client, "execute_read_strict", client.execute_read)
            meta_rows = _mpool.submit(
                strict_read,
                "CALL { OPTIONAL MATCH (m:KBMetadata) "
                "  RETURN head(collect(m)) AS meta } "
                "CALL { MATCH (n) RETURN count(n) AS node_count } "
                "RETURN meta.seed_version AS v, meta.kb_version AS kv, "
                "node_count",
            ).result(timeout=_meta_budget_s)
        except _cf.TimeoutError:
            # ONLY the budget case is swallowed here. A genuine exception from
            # execute_read still propagates to the top-level handler below, so
            # it is reported as ``auto_seed_check action=error`` exactly as
            # before — a hung host and a broken query are different facts and
            # must not be logged as the same one.
            logger.warning(
                "regenold.startup auto_seed_check meta_probe_timeout "
                "budget_s=%s action=skip-unverified",
                _meta_budget_s,
            )
            return
        finally:
            _mpool.shutdown(wait=False)
        current_seed = (meta_rows[0].get("v") if meta_rows else "") or ""
        current_kb = (meta_rows[0].get("kv") if meta_rows else "") or ""
        node_count_raw = meta_rows[0].get("node_count") if meta_rows else None
        try:
            node_count = int(node_count_raw)
        except (TypeError, ValueError):
            logger.warning(
                "regenold.startup auto_seed_check action=skip-unverified "
                "reason=missing-node-count"
            )
            return

        if (
            current_seed == SEED_VERSION
            and current_kb == KB_VERSION
        ):
            logger.info(
                "regenold.startup neo4j_seed_current "
                "auto_seed_check action=skip-current seed_version=%s "
                "kb_version=%s",
                current_seed,
                current_kb,
            )
            return

        if node_count != 0:
            logger.warning(
                "regenold.startup auto_seed_check action=skip-nonempty-drift "
                "node_count=%d current_seed=%s want_seed=%s current_kb=%s "
                "want_kb=%s",
                node_count,
                current_seed or "<missing>",
                SEED_VERSION,
                current_kb or "<missing>",
                KB_VERSION,
            )
            return

        # Mark started under the process-local lock so two competing
        # startup hooks (rare — testharness reloads, dev reloads) don't
        # both spawn threads.
        with _AUTO_SEED_LOCK:
            if _AUTO_SEED_STARTED:
                logger.info(
                    "regenold.startup auto_seed_check "
                    "action=skip-already-started"
                )
                return
            _AUTO_SEED_STARTED = True

        reason = "graph_empty_verified node_count=0"

        logger.info(
            "regenold.startup auto_seed_check action=seed-started "
            "reason=%s",
            reason,
        )
        thread = _threading.Thread(
            target=_run_auto_seed_in_thread,
            args=(reason,),
            name="regenold-auto-seed",
            daemon=True,
        )
        thread.start()
    except Exception as exc:  # noqa: BLE001 — boot must never block on this
        logger.warning(
            "regenold.startup auto_seed_check action=error err=%s — engine "
            "will use deterministic fallback",
            exc,
        )



# ─── Startup index warm-up (R112, perf finding #12) ──────────────────────
#
# Every retrieval index in the engine is a lazy first-use builder
# (``kb_search._build_index`` lru_cache, ``sentence_index._all_sentence_
# indexes`` lru_cache, ``embeddings_index`` asset load, the turboquant
# dense build, ``eu_ai_act_tree.build_tree``). Without a warm hook the
# first ~5 distinct partner requests after every Railway deploy / worker
# recycle each paid 0.8-6 s of index building (measured: 5,222 / 4,483 /
# 2,034 / 2,049 / 4,011 ms cold vs 9-15 ms warm p50) — latency is a
# scored competition axis. CLAUDE.md R78.1 recommended exactly this hook
# and deferred it; R112 ships it. Mirrors ``_maybe_auto_seed_neo4j``'s
# pattern: daemon thread, never blocks uvicorn boot, every step
# exception-swallowed, honours ``REGENOLD_SKIP_STARTUP_LOG=1`` (tests).
# Env-gate ``REGENOLD_INDEX_WARMUP`` — default ON; ``0/false/no/off``
# disables. Zero wire-behaviour change: the warm thread only populates
# the same caches the first request would.

_INDEX_WARMUP_LOCK = _threading.Lock()
_INDEX_WARMUP_STARTED = False


def _index_warmup_disabled_by_env() -> bool:
    """True when ``REGENOLD_INDEX_WARMUP`` is explicitly off.

    Default is ON. Unlike graph auto-seeding, this operation only populates
    process-local read caches, so a blank value retains the enabled default.
    """
    raw = os.getenv("REGENOLD_INDEX_WARMUP")
    if raw is None:
        return False
    return raw.strip().lower() in {"0", "false", "no", "off"}


def _run_index_warmup_in_thread() -> None:
    """Warm-up body — runs inside the daemon thread.

    Each step is individually exception-swallowed so one missing asset
    (e.g. turboquant npz on a stripped install) never stops the rest.
    Imports stay inside the steps — module import order at boot is
    unchanged and a broken optional dependency can't break startup.
    """
    import time as _time

    t_start = _time.perf_counter()
    timings: list[str] = []

    def _step(name: str, fn: Any) -> None:
        t0 = _time.perf_counter()
        try:
            fn()
            timings.append(f"{name}={int((_time.perf_counter() - t0) * 1000)}ms")
        except Exception as exc:  # noqa: BLE001 — warm-up is best-effort
            timings.append(f"{name}=failed")
            logger.debug(
                "regenold.startup index_warmup step=%s failed: %s", name, exc
            )

    def _warm_kb_search() -> None:
        # BM25 index + the R28 xref-in-degree confidence-boost table.
        from app.data.kb_search import _build_index, _xref_in_degree

        _build_index()
        _xref_in_degree()

    def _warm_sentence_index() -> None:
        # Per-article sentence BM25 (extractive-QA path), ~0.5 s cold.
        from app.engines.sentence_index import _all_sentence_indexes

        _all_sentence_indexes()

    def _warm_embeddings_index() -> None:
        # R32 NumPy-SVD sentence embeddings asset load (~135 ms cold).
        from app.engines.embeddings_index import warm_up

        warm_up()

    def _warm_turboquant() -> None:
        # The dense build was the largest cold cost (3.8 s measured).
        # ``dense_top_k`` triggers the full lazy ``_setup`` + one probe
        # query; respect the env gate so a disabled dense path stays
        # zero-cost.
        from app.engines.turboquant_index import dense_top_k, is_enabled

        if is_enabled():
            dense_top_k("warm up probe", k=1)

    def _warm_tree() -> None:
        # Layer-A document tree (~25 ms cold).
        from app.data.eu_ai_act_tree import build_tree

        build_tree()

    def _warm_embedded_graph() -> None:
        # R129 — when the embedded backend is the live 2-hop graph, build it
        # at boot so the build cost (and any build FAILURE) surfaces in the
        # warm-up log rather than on the first user request. No-op when a
        # different backend is selected. Sub-ms build (~126 nodes).
        from app.graph.embedded_graph import (
            embedded_backend_selected,
            get_embedded_graph,
        )

        if embedded_backend_selected():
            get_embedded_graph()

    def _warm_neo4j_graph() -> None:
        # R294 — the hosted-Neo4j counterpart of ``_warm_embedded_graph``.
        #
        # Measured against the live Aura instance, the production 2-hop
        # CROSS_REFERENCES Cypher costs ~703 ms COLD but only ~64 ms once
        # the driver connection + query-plan cache are hot. Without this
        # step the cold cost lands on the first user request, blows the
        # per-query wall-clock budget, and that request silently loses the
        # whole graph contribution.
        #
        # No-op unless the neo4j backend is actually selected AND the
        # client is enabled, so an embedded / graph-less deploy pays
        # nothing. Fail-soft: ``_step`` already logs and swallows.
        from app.graph.embedded_graph import embedded_backend_selected

        if embedded_backend_selected():
            return
        from app.graph.client import get_graph_client

        client = get_graph_client()
        if not client.enabled:
            return
        # Open the connection pool.
        client.execute_read("RETURN 1 AS ok", {})

        # R303 — ``RETURN 1`` warms the POOL but NOT the query-plan cache, and
        # the plan is where the cold cost actually is. Measured against the
        # live Aura instance (R291 full seed) through ``expand_2hop`` itself:
        #
        #     call 1 (cold)   1356 ms  -> EXCEEDS the 250 ms budget -> 0 refs
        #     call 2           202 ms  -> works (hop1=10, hop2=5)
        #     calls 3-6      43-48 ms  -> works
        #
        # So the first REAL 2-hop of each connection lifetime silently lost the
        # entire graph contribution, and with the R294 breaker three such cold
        # failures open it for 60 s. Warming the actual Cypher (not a trivial
        # probe) compiles the plan here, at boot, so the first user request
        # lands on the ~45 ms warm path.
        #
        # Uses a real seed so the planner sees the real pattern. Fail-soft via
        # ``_step``; a graph-less or embedded deploy already returned above.
        try:
            from app.engines.graph_expand_2hop import _CYPHER_2HOP

            client.execute_read(_CYPHER_2HOP, {"seed_nums": ["6"], "cap": 8})
        except Exception:  # noqa: BLE001 — plan warm is best-effort
            logger.debug("neo4j 2-hop plan warm-up failed", exc_info=True)

        # R318 — warm the kg_context hierarchy plan too, for the SAME reason and
        # by the same R303 doctrine ("warm the REAL Cypher, not a trivial probe").
        #
        # This one matters MORE than the 2-hop in practice: measured, the 2-hop's
        # refs are discarded downstream at the fusion budget (R295), whereas
        # ``kg_context`` is the ONE graph path that actually reaches the Stage-2
        # prompt on every polished answer. R318 put it under the R294 budget +
        # breaker, which is correct but means a cold plan compile now FAILS SOFT
        # (the block silently renders nothing) instead of stalling. Measured on
        # this query against the live instance: cold ~2.6 s, warm 31-39 ms
        # against a 500 ms budget — so without this warm-up the first request of
        # each connection lifetime would lose the graph block, and three such
        # failures open the breaker for 60 s.
        try:
            from app.engines.kg_context import _HIERARCHY_CYPHER

            client.execute_read(
                _HIERARCHY_CYPHER, {"ids": ["article_6"], "max_units": 24}
            )
        except Exception:  # noqa: BLE001 — plan warm is best-effort
            logger.debug("neo4j kg_context plan warm-up failed", exc_info=True)

    _step("kb_search_bm25", _warm_kb_search)
    _step("sentence_index", _warm_sentence_index)
    _step("embeddings_index", _warm_embeddings_index)
    _step("turboquant_dense", _warm_turboquant)
    _step("eu_ai_act_tree", _warm_tree)
    _step("embedded_graph", _warm_embedded_graph)
    _step("neo4j_graph", _warm_neo4j_graph)

    logger.info(
        "regenold.startup index_warmup_completed elapsed_s=%.2f %s",
        _time.perf_counter() - t_start,
        " ".join(timings),
    )


@app.on_event("startup")
def _maybe_warm_indexes() -> None:
    """Warm the lazy retrieval indexes on boot — non-blocking, env-gated.

    Decision tree:

    1. ``REGENOLD_SKIP_STARTUP_LOG=1`` → bail (tests).
    2. ``REGENOLD_INDEX_WARMUP=0/false/no/off`` → log + bail.
    3. Already started (dev-reload double hook) → bail.
    4. Otherwise → fire the daemon warm-up thread.
    """
    global _INDEX_WARMUP_STARTED

    if os.getenv("REGENOLD_SKIP_STARTUP_LOG") == "1":
        return

    if _index_warmup_disabled_by_env():
        logger.info(
            "regenold.startup index_warmup action=disabled-by-env "
            "REGENOLD_INDEX_WARMUP=%s",
            os.getenv("REGENOLD_INDEX_WARMUP", ""),
        )
        return

    with _INDEX_WARMUP_LOCK:
        if _INDEX_WARMUP_STARTED:
            return
        _INDEX_WARMUP_STARTED = True

    try:
        thread = _threading.Thread(
            target=_run_index_warmup_in_thread,
            name="regenold-index-warmup",
            daemon=True,
        )
        thread.start()
        logger.info("regenold.startup index_warmup action=started")
    except Exception as exc:  # noqa: BLE001 — boot must never block on this
        logger.warning(
            "regenold.startup index_warmup action=error err=%s — first "
            "requests will build the indexes lazily",
            exc,
        )


def _deploy_identity() -> dict[str, str]:
    """Which COMMIT is actually serving this request.

    ``settings.version`` is a hand-bumped literal, so it cannot answer the one
    question a deploy check must answer: did the container actually roll? A
    merge that never rolled and a merge that rolled report the same
    ``version``, and Railway is known to report deploy SUCCESS without
    replacing the container — so "the workflow went green" is not evidence.

    Railway injects these into the container. Both fall back to ``"unknown"``
    (unset OR empty) so local dev, tests and non-Railway hosts stay green
    rather than leaking a stray empty string.

    ``commit`` is the first 12 chars of the SHA. To verify a deploy, compare
    against a 12-char prefix — NOT ``git rev-parse --short HEAD``, which
    defaults to 7 and will never be equal::

        curl -s .../healthz | jq -r .commit          # e.g. e495f0c1a2b3
        git rev-parse origin/main | cut -c1-12       # same 12 chars

    Neither value is a secret: the SHA is public in the repo, and the
    deployment id is an opaque Railway handle with no credential in it.
    """
    sha = (os.getenv("RAILWAY_GIT_COMMIT_SHA") or "").strip()
    deployment = (os.getenv("RAILWAY_DEPLOYMENT_ID") or "").strip()
    return {
        "commit": sha[:12] if sha else "unknown",
        "deployment_id": deployment or "unknown",
    }


#: R321 — the live Groq probe on ``/healthz`` is OPT-IN and default OFF.
#:
#: ``railway.toml`` sets ``healthcheckPath = "/healthz"`` with
#: ``healthcheckTimeout = 30``. As shipped this handler fired a real Groq
#: completion with ``max_tokens=1024`` and NO ``timeout_seconds``, so the
#: budget fell back to the provider singleton's ``GROQ_TIMEOUT_SECONDS``
#: default of 60 s — twice the healthcheck budget — and the 429 arm adds a
#: sleep plus a SECOND POST inside that same deadline. A slow or rate-limited
#: Groq could therefore hold the deploy healthcheck past its timeout and fail
#: the release. Observed live on 2026-08-07: ``/healthz`` returned
#: ``fallback_test.error = "api_status_429 ... TPD Limit 200000, Used 199382"``,
#: i.e. the probe was really running against a rate-limited account on the
#: deploy path.
#:
#: A deploy healthcheck must answer one question — is this process serving? —
#: cheaply and deterministically. Live provider probing already has a purpose
#: -built endpoint (``/healthz/llm``), which is where it belongs. Set
#: ``REGENOLD_HEALTHZ_PROBE=1`` to re-enable it here for debugging; even then
#: it is bounded well inside the healthcheck budget.
_HEALTHZ_PROBE_TIMEOUT_S = 5.0
_HEALTHZ_PROBE_MAX_TOKENS = 16


def _healthz_probe_enabled() -> bool:
    return os.getenv("REGENOLD_HEALTHZ_PROBE", "0").strip().lower() in {
        "1", "true", "yes", "on",
    }


@app.get("/healthz")
def healthz() -> dict[str, object]:
    from app.llm.openai_wrapper_provider import is_groq_provider_enabled, get_groq_provider, OpenAIWrapperRequest, default_groq_model
    fallback_status = None
    fallback_error = None
    fallback_text = None
    fallback_finish_reason = None
    fallback_model = None

    if _healthz_probe_enabled() and is_groq_provider_enabled():
        try:
            prov = get_groq_provider()
            resp = prov.complete(
                OpenAIWrapperRequest(
                    system="You are a regulation expert. Answer concisely.",
                    user="What is a general purpose AI model under the AI Act?",
                    model=default_groq_model(),
                    max_tokens=_HEALTHZ_PROBE_MAX_TOKENS,
                    temperature=0.0,
                    timeout_seconds=_HEALTHZ_PROBE_TIMEOUT_S,
                )
            )
            fallback_model = resp.model
            fallback_finish_reason = resp.finish_reason
            if resp.error:
                fallback_status = "error"
                fallback_error = resp.error
            else:
                fallback_status = "ok"
                fallback_text = resp.text
        except Exception as e:
            fallback_status = "exception"
            fallback_error = str(e)
            
    return {
        "status": "ok",
        "version": settings.version,
        **_deploy_identity(),
        "is_groq_enabled": is_groq_provider_enabled(),
        "fallback_test": {
            "status": fallback_status,
            "error": fallback_error,
            "finish_reason": fallback_finish_reason,
            "model": fallback_model,
            "text": fallback_text[:500] if fallback_text else None,
        }
    }


_HEALTHZ_TRUTHY = ("1", "true", "yes", "on")


def _probe_bedrock_leg() -> dict[str, object]:
    """R365 — call the purpose-built Bedrock diagnostic and return it, redacted.

    ``check_connectivity_and_permissions`` has existed since the Bedrock port
    and answers exactly the question an operator has when leg 2 is dark — it
    returns the AWS status (``key_invalid`` / ``error`` / ``ok``), the
    classified error (``api_access_denied_403``, ``api_validation_400``, …)
    and, for the expired-key case, the remediation hint. It had **zero call
    sites in ``app/``**: the only caller was ``scripts/test_bedrock_client.py``,
    which requires shell access to the container. This is its first wiring
    into a surface reachable from outside.

    Never raises — a health probe that 500s is worse than one that reports a
    failure, so every path returns a dict.
    """
    try:
        from app.llm.bedrock_client import (
            check_connectivity_and_permissions,
            is_bedrock_provider_enabled,
            redact_credential_like,
        )
    except Exception as exc:  # noqa: BLE001 — a probe must never 500
        return {
            "status": "unavailable",
            "error": f"import_failed: {type(exc).__name__}",
            "hint": "app.llm.bedrock_client could not be imported (boto3 missing?)",
        }

    try:
        if not is_bedrock_provider_enabled():
            return {
                "status": "no_credentials",
                "error": None,
                "hint": (
                    "no Bedrock credential is wired — set AWS_BEARER_TOKEN_BEDROCK "
                    "or AWS_BEDROCK_API_KEY or AWS_ACCESS_KEY_ID+AWS_SECRET_ACCESS_KEY. "
                    "Stage-2 has no fallback leg until one is present."
                ),
            }
        raw = check_connectivity_and_permissions()
    except Exception as exc:  # noqa: BLE001 — a probe must never 500
        return {
            "status": "probe_raised",
            "error": redact_credential_like(f"{type(exc).__name__}: {exc}"),
            "hint": "check_connectivity_and_permissions raised; see container logs",
        }

    if not isinstance(raw, dict):
        return {
            "status": "probe_malformed",
            "error": f"expected dict, got {type(raw).__name__}",
            "hint": None,
        }

    out: dict[str, object] = {}
    for key in (
        "status", "model", "error", "hint", "elapsed_ms",
        "response_text", "input_tokens", "output_tokens",
    ):
        if key in raw:
            value = raw[key]
            out[key] = redact_credential_like(value) if isinstance(value, str) else value
    # ``status`` / ``error`` are surfaced VERBATIM (post-redaction) — that is
    # the whole point. Only supply a hint when AWS gave us none.
    out.setdefault("error", None)
    if not out.get("hint") and str(out.get("status", "")) not in {"ok", ""}:
        out["hint"] = (
            "Bedrock refused the call. Compare the error code against the "
            "account's model entitlements and BEDROCK_REGION — "
            "api_access_denied_403 is an entitlement/region problem, "
            "api_key_invalid_403 is a dead credential."
        )
    out.setdefault("hint", None)
    # R365 — forward the per-model chain. The probe walks
    # ``BEDROCK_FALLBACK_PROBE_MODELS`` and this is the only place an operator
    # can see WHICH chain models answered: a partial entitlement (235b denied,
    # 32b ok) is a very different situation from a dead credential, and the
    # top-level status alone cannot distinguish them. Redacted per entry, and
    # defensively typed because it comes from the same dict as everything else.
    _chain = raw.get("chain")
    if isinstance(_chain, list):
        out["chain"] = [
            {
                k: (redact_credential_like(v) if isinstance(v, str) else v)
                for k, v in entry.items()
            }
            for entry in _chain
            if isinstance(entry, dict)
        ]
    return out


def _healthz_email_probe(
    probe: int = 0, to: str = "lexy-health-probe@example.com"
) -> dict[str, object]:
    """Lexy welcome-email (Resend) health probe.

    Config-only by default (no token cost, no send) — reports whether the
    ``resend`` package is installed, the ``RESEND_API_KEY`` is present, and
    the from-address. With ``?probe=1`` it fires ONE real Resend send to
    ``to`` and returns the exact success id or the failure reason (so an
    operator can tell 'resend not installed' / 'key missing' / 'domain not
    verified' apart). Always HTTP 200 — alert on ``configured=false`` or
    ``send_ok=false``.
    """
    from app.integrations.regenold import email as lexy_email

    payload: dict[str, object] = {"version": settings.version}
    payload.update(lexy_email.diagnostics())
    if probe:
        ok, detail = lexy_email.probe_send(to)
        payload["send_ok"] = ok
        payload["send_detail"] = detail
    return payload


def _healthz_llm_probe(probe_bedrock: str = "0") -> dict[str, object]:
    """Live LLM-path probe — verifies the configured provider can actually answer.

    Without this, an operator who sets ``P2P_GRAPH_RAG_PROVIDER=openai_wrapper``
    has no way to know whether the wrapper is up + logged-in + actually
    returning tokens, vs. silently falling back to deterministic on every
    request. This endpoint fires a single ~5-token "reply OK" probe against
    the configured provider and returns the structured result.

    Always returns HTTP 200 (so an uptime monitor on /healthz/llm doesn't
    flap when the wrapper is down). The shape includes a ``llm_ok`` bool —
    consumers can alert on that instead.
    """
    from app.llm.openai_wrapper_provider import (
        OpenAIWrapperRequest,
        get_openai_wrapper_provider,
        is_openai_wrapper_enabled,
    )

    provider_label = resolve_provider(
        os.getenv("P2P_GRAPH_RAG_PROVIDER"),
        default_when_auto="openrouter",
    )

    base: dict[str, object] = {
        "version": settings.version,
        **_deploy_identity(),
        "provider": provider_label,
        "llm_ok": False,
        "detail": "",
    }

    # R365 — OPT-IN live Bedrock probe. Placed BEFORE the provider branches so
    # it survives every return path below. Default OFF: no AWS call is
    # made unless the caller asks for one.
    if str(probe_bedrock).strip().lower() in _HEALTHZ_TRUTHY:
        base["bedrock_probe"] = _probe_bedrock_leg()

    # R277 — Cloudflare Access diagnostic. When an Access application fronts
    # the wrapper hostname, an unauthenticated backend gets an HTML login page
    # + HTTP 401 and the engine silently serves deterministic-only answers.
    # Distinguishing "the service token isn't configured" from "the token IS
    # configured but Cloudflare rejects it (not an Include principal on the
    # policy)" is otherwise impossible from outside the container — both look
    # like api_status_401. BOOLEANS ONLY: never echo the id or the secret.
    if provider_label == "openai_wrapper":
        try:
            from app.llm.openai_wrapper_provider import _resolve_cf_access_headers

            _wrapper_base = (
                os.getenv("OPENAI_API_BASE", "").strip()
                or "https://wrapper.antifragile-ai.net/v1"
            )
            base["cf_access"] = {
                "client_id_set": bool(os.getenv("CF_ACCESS_CLIENT_ID", "").strip()),
                "client_secret_set": bool(
                    os.getenv("CF_ACCESS_CLIENT_SECRET", "").strip()
                ),
                # True => the provider WILL send CF-Access-* to the wrapper host.
                # If this is True and llm_ok is still false with a 401, the token
                # is not an Include -> Service Auth principal on the Access policy.
                "headers_attached": bool(_resolve_cf_access_headers(_wrapper_base)),
            }
        except Exception as exc:  # noqa: BLE001 — a probe must never 500
            base["cf_access"] = {"error": type(exc).__name__}

    # The probe is provider-specific because each path has its own
    # failure surface. The openai_wrapper probe is fully live; the
    # anthropic probe uses ``client.models.list()`` which authenticates
    # the API key without burning a billable token.
    if provider_label == "openai_wrapper":
        if not is_openai_wrapper_enabled():
            base["detail"] = (
                "P2P_GRAPH_RAG_PROVIDER=openai_wrapper but neither "
                "OPENAI_API_BASE nor OPENAI_API_KEY is set"
            )
            return base
        # Probe with the SAME model used for Stage-2 polish (the
        # load-bearing call) — the Haiku-only probe we shipped in
        # round 29 could pass while Sonnet was broken (different rate
        # limit pool, model-scoped auth scopes on some providers,
        # tunnel routing rules, etc.). Operators can still pin a
        # cheaper probe via REGENOLD_HEALTHZ_PROBE_MODEL.
        probe_model = (
            os.getenv("REGENOLD_HEALTHZ_PROBE_MODEL", "").strip()
            or settings.graph_rag.model
            or "claude-opus-5"
        )
        # Probe timeout. The warm wrapper round-trip is ~4 s, but a
        # cold Railway container's first call after a deploy stacks cold
        # DNS + TLS + connection-pool warm-up (and possibly a cold
        # claude.exe spawn on the wrapper) and can exceed 10 s — which
        # false-negatived llm_ok on every post-deploy canary even though
        # the wrapper was healthy. 30 s covers cold-start while still
        # bounding a genuinely hung wrapper; real Stage-2 polish uses the
        # singleton's 60 s. Override via REGENOLD_HEALTHZ_PROBE_TIMEOUT.
        try:
            probe_timeout = float(
                os.getenv("REGENOLD_HEALTHZ_PROBE_TIMEOUT", "").strip() or "30"
            )
        except ValueError:
            probe_timeout = 30.0
        try:
            prov = get_openai_wrapper_provider()
            response = prov.complete(
                OpenAIWrapperRequest(
                    system="Reply with the exact word OK and nothing else.",
                    user="ping",
                    model=probe_model,
                    max_tokens=8,
                    temperature=0.0,
                    timeout_seconds=probe_timeout,
                )
            )
        except Exception as exc:  # noqa: BLE001 — health probe must never raise
            base["detail"] = f"probe_exception: {exc!s}"[:200]
            return base
        if response.error:
            # Check if an active fallback provider is enabled before declaring total failure
            from app.llm.openai_wrapper_provider import is_openrouter_provider_enabled  # noqa: PLC0415
            from app.llm.bedrock_client import is_bedrock_provider_enabled  # noqa: PLC0415

            if is_openrouter_provider_enabled():
                base["llm_ok"] = True
                base["provider"] = "openrouter (fallback)"
                base["detail"] = f"primary (openai_wrapper) offline ({response.error[:60]}); openrouter fallback active"
                base["elapsed_ms"] = response.elapsed_ms
                return base
            if is_bedrock_provider_enabled():
                base["llm_ok"] = True
                base["provider"] = "bedrock (fallback)"
                base["detail"] = f"primary (openai_wrapper) offline ({response.error[:60]}); bedrock fallback active"
                base["elapsed_ms"] = response.elapsed_ms
                return base

            base["detail"] = response.error[:200]
            base["elapsed_ms"] = response.elapsed_ms
            return base
        base["llm_ok"] = bool((response.text or "").strip())
        base["detail"] = "ok" if base["llm_ok"] else "empty_response"
        base["elapsed_ms"] = response.elapsed_ms
        base["model"] = response.model
        base["prompt_tokens"] = response.prompt_tokens
        base["completion_tokens"] = response.completion_tokens
        return base

    if provider_label == "anthropic":
        api_key = settings.graph_rag.api_key
        if not api_key:
            base["detail"] = "P2P_GRAPH_RAG_API_KEY not set"
            return base
        try:
            import anthropic
        except ImportError:
            base["detail"] = "anthropic SDK not installed (pip install anthropic)"
            return base
        # Live probe — round-29 shipped a configured-only probe that
        # said llm_ok=True whenever the key was set, even if revoked /
        # malformed / pointed at the wrong tenant. We now call
        # ``models.list()`` which authenticates the key against the
        # Anthropic API but does NOT consume any input/output tokens
        # (it's a metadata endpoint, free per the pricing page). The
        # 10-second timeout caps the probe latency. Operators who want
        # the old "don't touch the network at health-check time"
        # behaviour can set REGENOLD_HEALTHZ_PROBE_ANTHROPIC=0.
        if os.getenv("REGENOLD_HEALTHZ_PROBE_ANTHROPIC", "1").strip() == "0":
            base["llm_ok"] = True
            base["detail"] = (
                "anthropic SDK installed + API key configured "
                "(REGENOLD_HEALTHZ_PROBE_ANTHROPIC=0, not probed live)"
            )
            return base
        import time as _time
        start = _time.perf_counter()
        client = None
        try:
            # Issue #131 — close the client after the probe. The Anthropic
            # SDK is httpx-backed; constructing one per ``/healthz/llm``
            # request without closing leaks the connection pool + file
            # descriptors on every health check. The ``finally`` below
            # guarantees ``close()`` on both the success and exception
            # paths; the guarded call keeps the probe robust if a client
            # (mock / older SDK) lacks ``close()``.
            client = anthropic.Anthropic(
                api_key=api_key.get_secret_value(),
                timeout=10.0,
            )
            client.models.list(limit=1)
        except Exception as exc:  # noqa: BLE001 — health probe must never raise
            # Anthropic raises typed exceptions (AuthenticationError,
            # APIConnectionError, etc.) but we don't want to depend on
            # the SDK's class hierarchy in main.py — the string is
            # enough for an operator to diagnose.
            base["detail"] = (
                f"anthropic_probe_failed: {type(exc).__name__}: {exc!s}"
            )[:200]
            base["elapsed_ms"] = int((_time.perf_counter() - start) * 1000)
            return base
        finally:
            # Issue #131 — always release the httpx-backed connection pool.
            if client is not None:
                try:
                    client.close()
                except Exception:  # noqa: BLE001 — cleanup must never raise
                    pass
        base["llm_ok"] = True
        base["detail"] = "ok"
        base["elapsed_ms"] = int((_time.perf_counter() - start) * 1000)
        base["model"] = settings.graph_rag.model
        return base

    if provider_label == "openrouter":
        from app.llm.openai_wrapper_provider import is_openrouter_provider_enabled
        if not is_openrouter_provider_enabled():
            base["detail"] = "OPENROUTER_API_KEY is not set"
            return base
        base["llm_ok"] = True
        base["detail"] = "openrouter_configured"
        return base

    if provider_label == "bedrock":
        from app.llm.bedrock_client import is_bedrock_provider_enabled
        if not is_bedrock_provider_enabled():
            base["detail"] = "AWS Bedrock credentials or region not configured"
            return base
        base["llm_ok"] = True
        base["detail"] = "bedrock_configured"
        return base

    # cli / deterministic path
    base["llm_ok"] = True
    base["detail"] = "deterministic-only path — no LLM call required"
    return base


def _kg_contribution_probe(deep: bool = False) -> dict[str, object]:
    """Is the graph layer actually CONTRIBUTING to answers right now?

    R376 — ``/healthz/graph`` answers "can I reach Neo4j?", which is a different
    question from "is the provision-hierarchy block reaching Stage-2?", and only
    the second one shows up in an answer. A graph can ping healthy while the
    layer is dead: ``REGENOLD_KG_CONTEXT=0``, an open circuit breaker after a
    burst of timeouts, a seeded instance missing the HAS_PARAGRAPH edges, or a
    saturated worker pool. Every one of those degrades silently — CLAUDE.md's
    own words for the seed hazard are "the seeder succeeds, /healthz/graph still
    reports ok, answers just get worse".

    So this runs the real fetcher on a fixed provision and reports what came
    back and WHERE FROM. It is the same call the answer path makes, which is the
    point: a probe that exercises a different code path can agree with a broken
    one.

    Read-only, bounded by the standard graph timeout, and never raises.
    """
    out: dict[str, object] = {
        "kg_context_enabled": False,
        "circuit_open": False,
        "local_mirror_enabled": False,
        "local_mirror_nodes": 0,
        "hierarchy_rows": 0,
        "hierarchy_units": 0,
        "served_by": "none",
    }
    try:
        from app.engines.kg_context import (
            _mirror_hierarchy,
            _mirror_index,
            fetch_provision_hierarchy,
            kg_context_enabled,
            kg_local_mirror_enabled,
            last_hierarchy_source,
        )

        out["kg_context_enabled"] = bool(kg_context_enabled())
        mirror_on = bool(kg_local_mirror_enabled())
        out["local_mirror_enabled"] = mirror_on
        try:
            out["local_mirror_nodes"] = len(_mirror_index())
        except Exception:  # noqa: BLE001
            out["local_mirror_nodes"] = 0
    except Exception as exc:  # noqa: BLE001 — a probe must never break /healthz
        out["detail"] = f"kg_context_import_failed: {exc!s}"[:160]
        return out

    try:
        from app.graph.timeouts import graph_circuit_open

        out["circuit_open"] = bool(graph_circuit_open())
    except Exception:  # noqa: BLE001
        pass

    # R376 review — A DIAGNOSTIC MUST NOT MUTATE THE THING IT DIAGNOSES.
    #
    # The live read goes through ``_bounded_execute_read``, which takes one of
    # the four ``REGENOLD_KG_MAX_INFLIGHT`` worker slots and calls
    # ``record_graph_failure()`` on a timeout or a saturated pool. An uptime
    # monitor polling this endpoint against a degraded Aura would therefore
    # vote in the circuit breaker (3 consecutive failures opens it for 60 s of
    # real traffic) and, under the harness's concurrency-3 load, steal a slot
    # from a live request. CLAUDE.md already records the shape: "a non-blocking
    # admission gate is a graph OFF switch under load."
    #
    # So the default is a NON-MUTATING report built from the in-process mirror,
    # which needs no network and no admission slot, and ``?deep=1`` opts into
    # the real fetch for an operator who wants the live path exercised.
    if not deep:
        mirrored = _mirror_hierarchy(["article_9"], 70) if mirror_on else []
        out["hierarchy_rows"] = len(mirrored)
        out["hierarchy_units"] = sum(len(r.get("units") or []) for r in mirrored)
        out["served_by"] = "local_mirror (probe: mirror-only)" if mirrored else "none"
        out["detail"] = (
            "mirror-only probe — pass ?deep=1 to exercise the live graph read "
            "(that path consumes a graph worker slot and votes in the circuit "
            "breaker, so it is opt-in)"
        )
        return out

    # Article 9 is a stable choice: it carries numbered paragraphs in both the
    # seeded graph and the in-repo hierarchy, so zero rows here means the layer
    # is genuinely not contributing rather than that the probe picked a
    # single-block provision.
    try:
        rows = fetch_provision_hierarchy(["Art. 9"]) or []
        out["hierarchy_rows"] = len(rows)
        out["hierarchy_units"] = sum(len(r.get("units") or []) for r in rows)
    except Exception as exc:  # noqa: BLE001
        out["detail"] = f"hierarchy_probe_failed: {exc!s}"[:160]
        return out

    if not out["hierarchy_rows"]:
        out["served_by"] = "none"
        out["detail"] = (
            "the provision-hierarchy layer is contributing NOTHING to Stage-2 — "
            "check REGENOLD_KG_CONTEXT, the circuit breaker, and whether the "
            "instance carries HAS_PARAGRAPH edges"
        )
        return out

    # R376 review — READ THE PROVENANCE, DO NOT INFER IT.
    #
    # This used to derive ``served_by`` from "client enabled and breaker
    # closed", which reports "graph" in exactly the case the probe exists to
    # catch: a reachable instance seeded WITHOUT HAS_PARAGRAPH edges answers
    # empty-but-successfully, the mirror serves, and the operator concludes
    # Aura is contributing when it is not. ``fetch_provision_hierarchy`` now
    # records which source actually produced the rows.
    out["served_by"] = last_hierarchy_source() or "none"
    return out


def _healthz_graph_probe(deep: bool = False) -> dict[str, object]:
    """Probe Neo4j connectivity + KB seed status.

    Returns HTTP 200 always — uptime monitors should alert on
    ``graph_ok=False`` (not on HTTP status), so a downed graph doesn't
    flap the uptime page when the engine's deterministic fallback is
    still serving requests fine.

    Three paths:

    * **disabled** — ``NEO4J_URI`` is unset, or the ``neo4j`` driver is
      not importable. Returns ``graph_enabled=False`` with a clear hint.
    * **unhealthy** — driver imports + connects but ``RETURN 1 AS ping``
      fails. Returns ``graph_ok=False`` with a truncated error.
    * **healthy** — full status: ping, seed_version, kb_version,
      per-label node counts, edge-type counts, total elapsed_ms.

    The probe runs read-only Cypher only. It never writes. All read
    queries inherit the driver's ``connection_timeout`` (5 s by default,
    see :class:`app.graph.config.GraphSettings`).
    """
    import time as _time

    from app.data.kb import KB_VERSION
    from app.graph.client import _STATS_LABELS, get_graph_client

    start = _time.perf_counter()
    base: dict[str, object] = {
        "version": settings.version,
        "backend": "neo4j",
        "graph_enabled": False,
        "graph_ok": False,
        "detail": "",
        "elapsed_ms": 0,
        "seed_version": "",
        "kb_version": KB_VERSION,
        "node_counts": {},
        "edge_counts": {},
    }

    # ─── Embedded backend path (R129 default) ─────────────────────────────
    # When ``REGENOLD_GRAPH_BACKEND=embedded`` the live 2-hop backend is the
    # in-process SQLite property graph, NOT Neo4j. The Neo4j-only paths below
    # would report ``graph_enabled=false`` / "driver not installed" even
    # though the embedded graph is healthy and serving — a false alarm for
    # any uptime monitor that alerts on ``graph_ok=false``. Report the
    # embedded graph's real build status instead. Read-only, sub-ms.
    try:
        from app.graph.embedded_graph import (
            embedded_backend_selected,
            get_embedded_graph,
        )

        _embedded_selected = embedded_backend_selected()
    except Exception as exc:  # noqa: BLE001 — health probe must never raise
        _embedded_selected = False
        base["detail"] = f"embedded_backend_probe_failed: {exc!s}"[:200]
    if _embedded_selected:
        base["backend"] = "embedded"
        try:
            graph = get_embedded_graph()
            ok = bool(graph.enabled)
            base["graph_enabled"] = ok
            base["graph_ok"] = ok
            if ok:
                base["detail"] = "ok (embedded)"
                base["node_counts"] = {"Article+Annex": graph.node_count()}
                base["edge_counts"] = {"CROSS_REFERENCES": graph.edge_count()}
            else:
                base["detail"] = (
                    "embedded_graph build failed — 2-hop expansion is a no-op; "
                    "engine serves via the deterministic KB path"
                )
        except Exception as exc:  # noqa: BLE001 — health probe must never raise
            base["detail"] = f"embedded_graph_probe_failed: {exc!s}"[:200]
        base["kg_context"] = _kg_contribution_probe(deep)
        base["elapsed_ms"] = int((_time.perf_counter() - start) * 1000)
        return base

    # ─── Disabled path ────────────────────────────────────────────────────
    if not os.environ.get("NEO4J_URI"):
        base["detail"] = "NEO4J_URI not set"
        # R376 — report the contribution probe even here. "NEO4J_URI not set"
        # used to be the end of the story, which left the operator unable to
        # tell a deploy that is degrading silently from one where the local
        # mirror is carrying the layer correctly.
        base["kg_context"] = _kg_contribution_probe(deep)
        return base

    start = _time.perf_counter()
    try:
        client = get_graph_client()
    except Exception as exc:  # noqa: BLE001 — health probe must never raise
        base["detail"] = f"graph_client_init_failed: {exc!s}"[:200]
        base["kg_context"] = _kg_contribution_probe(deep)
        base["elapsed_ms"] = int((_time.perf_counter() - start) * 1000)
        return base

    if not client.enabled:
        # NEO4J_URI was set but the client didn't activate (driver missing
        # or connection refused at __init__ time).
        base["detail"] = (
            "graph_disabled: NEO4J_URI is set but the neo4j driver is not "
            "installed or the connection was refused at init. Install with "
            "`pip install neo4j>=5.0` and verify the URI."
        )
        base["kg_context"] = _kg_contribution_probe(deep)
        base["elapsed_ms"] = int((_time.perf_counter() - start) * 1000)
        return base

    base["graph_enabled"] = True

    # ─── Unhealthy path — ping fails ──────────────────────────────────────
    try:
        hc = client.health_check()
    except Exception as exc:  # noqa: BLE001 — health probe must never raise
        base["detail"] = f"health_check_exception: {exc!s}"[:200]
        base["kg_context"] = _kg_contribution_probe(deep)
        base["elapsed_ms"] = int((_time.perf_counter() - start) * 1000)
        return base

    status = hc.get("status")
    if status != "healthy":
        err = hc.get("error") or hc.get("message") or "unknown"
        base["detail"] = f"unhealthy: {err}"[:200]
        base["kg_context"] = _kg_contribution_probe(deep)
        base["elapsed_ms"] = int((_time.perf_counter() - start) * 1000)
        return base

    # ─── Healthy path — collect seed info + counts ────────────────────────
    # Each individual Cypher is wrapped: a single label-count failure must
    # not break the overall probe. ``client.execute_read`` already swallows
    # driver-level errors and returns ``[]``.
    seed_version = ""
    try:
        meta = client.execute_read(
            "MATCH (m:KBMetadata) "
            "RETURN m.seed_version AS seed_version, m.kb_version AS kb_version "
            "LIMIT 1"
        )
        if meta:
            row = meta[0]
            seed_version = row.get("seed_version") or ""
            # Prefer the seed's recorded kb_version when present; falls back
            # to the in-process KB_VERSION (the seed and the code can drift
            # — that's exactly the kind of state an operator wants visible).
            kb_v = row.get("kb_version")
            if kb_v:
                base["kb_version"] = kb_v
    except Exception as exc:  # noqa: BLE001
        logger.debug("healthz_graph seed_version probe failed: %s", exc)

    # R63-F / R64 — only count labels that actually exist in the graph.
    # ``client.existing_labels`` probes ``db.labels()`` once and
    # intersects with the allowlist; on probe failure it falls back to a
    # SAFE subset (Article / Obligation / KBMetadata / RiskLevel /
    # AnnexIIICategory — all guaranteed by ``scripts/seed_neo4j_kb.py``)
    # so the f-string ``MATCH (n:LABEL)`` queries below never hit a
    # missing label and re-introduce the R63-F warning storm for the 5
    # orphan parent-CodexAI labels (Dimension / Question / RoadmapTask /
    # NISTSubcategory / ISOClause).
    existing_labels = client.existing_labels(_STATS_LABELS)

    node_counts: dict[str, int] = {}
    for label in sorted(existing_labels):
        try:
            rows = client.execute_read(
                f"MATCH (n:{label}) RETURN count(n) AS cnt"
            )
            if rows:
                cnt = int(rows[0].get("cnt") or 0)
                if cnt > 0:
                    # Skip empty labels — keeps the response readable.
                    node_counts[label] = cnt
        except Exception as exc:  # noqa: BLE001
            logger.debug("healthz_graph label=%s count failed: %s", label, exc)

    edge_counts: dict[str, int] = {}
    try:
        edge_rows = client.execute_read(
            "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS cnt"
        )
        for row in edge_rows:
            rt = row.get("rel_type")
            cnt = int(row.get("cnt") or 0)
            if rt and cnt > 0:
                edge_counts[rt] = cnt
    except Exception as exc:  # noqa: BLE001
        logger.debug("healthz_graph edge count probe failed: %s", exc)

    base["graph_ok"] = True
    base["detail"] = "ok"
    base["seed_version"] = seed_version
    base["node_counts"] = node_counts
    base["edge_counts"] = edge_counts
    # R376 — a healthy ping is not a contributing graph. This is the field to
    # read when an answer looks under-grounded: ``served_by`` says whether the
    # hierarchy came from Aura or from the in-process mirror, and
    # ``hierarchy_rows == 0`` says the layer is dead regardless of the ping.
    base["kg_context"] = _kg_contribution_probe(deep)
    base["elapsed_ms"] = int((_time.perf_counter() - start) * 1000)
    return base


# ══════════════════════════════════════════════════════════════════════════
# R370 — operator-only live probes
# ══════════════════════════════════════════════════════════════════════════
#
# Three health endpoints spent real money, real quota, or real sending
# reputation on behalf of an ANONYMOUS caller, and leaked deployment detail
# while doing it. All three were publicly reachable on production; verified
# with an unauthenticated request that returned HTTP 200 with the model id,
# token counts, deployment id, pid, CF Access booleans and the Stage-2
# transport chain.
#
#   * ``/healthz/llm``                  — one LIVE Claude Max completion per
#                                         request through the tunnel.
#   * ``/healthz/llm?probe_bedrock=1``  — walks BEDROCK_FALLBACK_PROBE_MODELS
#                                         and issues real AWS Bedrock Converse
#                                         calls. BILLABLE by a stranger.
#   * ``/healthz/email?probe=1&to=…``   — fires ONE real Resend send to an
#                                         ARBITRARY address. An open relay:
#                                         the abuse target is the sending
#                                         domain's reputation, not the spend.
#
# Only the app-wide slowapi ``100/minute`` per-IP default applied, and it is
# per IP, so the ceiling was ~100 invocations/minute/IP from any number of IPs.
#
# THE FIX IS TIERED, NOT A BLANKET 401, because two consumers must keep
# working:
#   1. Railway's deploy healthcheck (``railway.toml`` healthcheckPath) hits
#      ``GET /healthz``. That route is untouched — it stays public, cheap and
#      probe-free.
#   2. The in-app diagnostics panel (``app/web_ui.py::checkSystemHealth``)
#      fetches ``/healthz/llm`` and ``/healthz/graph`` FROM THE BROWSER and
#      reads only ``llm_ok`` / ``graph_ok`` / ``provider`` / ``detail``. It
#      cannot hold the partner key, so a blanket 401 would break the panel
#      that exists to tell an operator the tunnel is down.
#
# So: anonymous callers keep the badge fields and lose everything else; the
# SPENDING branches require the partner key outright; and both probe routes
# carry a tighter per-route limit than the app default.
#
# ⚠ ``/healthz`` still reports ``commit`` and ``deployment_id`` to anonymous
# callers. Left as-is deliberately — it is the Railway healthcheck path and
# the web UI reads ``version`` from it — but it is the same information-leak
# class and worth a separate decision.

# ⚠ NO PAYLOAD REDACTION, deliberately. An earlier draft of R370 projected the
# anonymous response down to the badge fields. It was dropped, because it is
# THEATRE while ``/healthz`` exists: that route must stay public for Railway's
# deploy healthcheck and it already serves ``commit`` and ``deployment_id`` to
# anonymous callers. Hiding the same two values one route over buys nothing,
# and the residue (pid, CF Access booleans, the Stage-2 counters, the model id)
# is low-grade operational detail — not worth re-pointing 22 existing probe
# tests at an authenticated client, which would also mean mutating the
# ``settings.regenold.api_key`` singleton in five more files right after #363
# landed a fixture to stop exactly that leaking across tests.
#
# What R370 actually closes is SPEND and SENDING, which is where the real
# exposure was. If the information leak is worth closing later, close it at
# ``/healthz`` first or the rest is decoration.


def _probe_caller_is_operator(api_key: str | None) -> bool:
    """True only for the CONFIGURED PARTNER KEY.

    Deliberately ``validate_regenold_api_key`` and not ``is_known_regenold_key``:
    the latter also accepts any ``lexy_sk_…`` minted by the public sign-up
    funnel, and a self-service signup must not be able to trigger AWS spend or
    a Resend send. Fail-closed on any error — an unreadable key is not an
    operator.
    """
    if not api_key:
        return False
    try:
        from app.integrations.regenold.auth import validate_regenold_api_key

        return validate_regenold_api_key(api_key)
    except Exception:  # noqa: BLE001 — fail closed, never 500 a health route
        return False


def _redact_probe_payload(
    payload: dict[str, object], allowed: tuple[str, ...]
) -> dict[str, object]:
    """Allowlist projection — additive keys can never leak by default."""
    return {k: payload[k] for k in allowed if k in payload}


def _require_operator_for_spend(api_key: str | None, reason: str) -> None:
    """401/403 for the branches that spend money or send mail.

    Mirrors ``require_regenold_api_key``'s status semantics so a client sees
    the same shapes it already handles: 401 when no key was presented, 403
    when one was presented and did not match.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "probe_requires_operator_key",
                "message": (
                    f"{reason} Provide the operator key via X-Regenold-Api-Key."
                ),
            },
        )
    if not _probe_caller_is_operator(api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "regenold_api_key_invalid",
                "message": "Invalid API key.",
            },
        )


# ⚠ NO ANONYMOUS RESULT CACHE either, and for the same reason the redaction
# was dropped. A 30 s TTL cache was drafted here: it cut five anonymous
# requests to one live completion, which is real. But ``/healthz/llm`` is a
# PROBE, and ~20 existing tests patch the provider and then assert on the
# reading — a cached reply serves them the previous test's answer, so the
# cache turned a deterministic diagnostic into an order-dependent one. Making
# it testable would mean a reset fixture in five more files.
#
# The per-route limit below carries this instead: 100/min -> 10/min per IP is a
# 10x cut, and the leg that costs actual MONEY (Bedrock) is hard-gated, not
# merely slowed. What remains is Claude Max subscription quota under a flat
# subscription. If that needs closing, the right fix is an auth requirement on
# the base route plus a cheap non-probing signal on ``/healthz`` for the web
# UI badge — a deliberate product decision, not something to smuggle in behind
# a cache.


@app.get("/healthz/llm")
@limiter.limit("10/minute")
def healthz_llm(
    request: Request,
    probe_bedrock: str = "0",
    x_regenold_api_key: Annotated[str | None, Header()] = None,
) -> dict[str, object]:
    """Live LLM-path probe.

    ``probe_bedrock=1`` is operator-only (it spends). The base reading stays
    public because ``app/web_ui.py::checkSystemHealth`` renders it from the
    browser and cannot hold the key — but anonymous callers share one cached
    reading, so a flood cannot multiply live completions.
    """
    operator = _probe_caller_is_operator(x_regenold_api_key)
    wants_bedrock = str(probe_bedrock).strip().lower() in _HEALTHZ_TRUTHY
    if wants_bedrock:
        _require_operator_for_spend(
            x_regenold_api_key,
            "probe_bedrock=1 issues billable AWS Bedrock Converse calls.",
        )
    return _healthz_llm_probe(probe_bedrock if operator else "0")


@app.get("/healthz/graph")
@limiter.limit("30/minute")
def healthz_graph(
    request: Request,
    deep: bool = False,
) -> dict[str, object]:
    """Neo4j connectivity + seed status. Public; carries a tighter per-route limit.

    No third-party spend here — the probe hits the project's own Neo4j — so
    this wrapper exists only to replace the app-wide 100/min default.
    """
    return _healthz_graph_probe(deep=deep)


@app.get("/healthz/email")
@limiter.limit("10/minute")
def healthz_email(
    request: Request,
    probe: int = 0,
    to: str = "lexy-health-probe@example.com",
    x_regenold_api_key: Annotated[str | None, Header()] = None,
) -> dict[str, object]:
    """Resend config snapshot. ``?probe=1`` sends real mail and needs the key.

    The ``to`` parameter is caller-controlled, so the ungated version was an
    open relay against the verified sending domain.
    """
    if probe:
        _require_operator_for_spend(
            x_regenold_api_key,
            "probe=1 sends real mail to a caller-supplied address.",
        )
    return _healthz_email_probe(probe=probe, to=to)


@app.get("/info")
def info() -> dict[str, str]:
    """Machine-readable service descriptor.

    Moved from ``/`` to ``/info`` so the interactive Lexy chat UI
    (registered by :func:`app.web_ui.register_web_routes`) can own the
    root path as the human-facing competition landing page. Programmatic
    consumers that previously hit ``/`` for the JSON descriptor use
    ``/info``; the wire contract ``POST /api/v1/regenold/eu-ai-act/ask``
    is unchanged.
    """
    return {
        "service": "regenold-eu-ai-act-rag",
        "version": settings.version,
        "docs": "/docs",
        "ui": "/",
        "chat_ui": "/app",
        "signup_endpoint": "/api/v1/regenold/auth/signup",
        "ask_endpoint": "/api/v1/regenold/eu-ai-act/ask",
    }


# ─── Sign-up funnel (/) + interactive Lexy chat (/app) ───────────────────
# Registered LAST so they mount on the root app after ``/api/v1`` and the
# ``/healthz*`` probes are already bound — no path collision. Both are
# static, self-contained HTML pages that inject NO server-side secret
# (keys are minted by the API at runtime; the user's key rides the URL
# fragment into the chat). Funnel owns ``/``; chat owns ``/app``.
# Failure to register the UI must never block the API, so it is
# best-effort.
try:
    from app.funnel_ui import register_funnel_routes
    from app.web_ui import register_web_routes

    register_web_routes(app)        # /app + /lexy_avatar.png
    register_funnel_routes(app)     # /
except Exception as _ui_exc:  # noqa: BLE001 — UI is optional; never block the API
    logger.warning(
        "regenold.startup web/funnel UI registration skipped: %s — API unaffected",
        _ui_exc,
    )
