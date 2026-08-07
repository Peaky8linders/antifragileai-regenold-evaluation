"""R313.1 — put the Neo4j Aura knowledge graph back on the answer path.

OPERATOR DIRECTIVE (2026-08-04): *always* use the knowledge graph and Neo4j
Aura. This module is that wiring.

WHAT WAS ACTUALLY WRONG
=======================

The graph was never broken — it was BYPASSED. Measured this round against the
live instance (``151d4e69``, seed ``2026-07-24-r291-fullseed``, kb_version
``2024.1689.v18``):

    Article 113   Annex 13   Paragraph 656   Point 416   Recital 180
    Definition 68   nodes 1746   edges 1838
    rels: HAS_PARAGRAPH, HAS_POINT, HAS_SUBPOINT, HAS_RECITAL_ANCHOR,
          CROSS_REFERENCES, HAS_DEFINITION, HAS_OBLIGATION, ...

Healthy, complete, and contributing NOTHING to an answer, for three independent
reasons found by audit:

  1. ``graph_backend()`` defaulted to ``"embedded"``, so the hosted instance was
     not even selected;
  2. ``_kb_primary_retrieval_enabled()`` (R252, default ON) short-circuits
     ``_retrieve_from_graph`` to ``_retrieve_from_kb`` BEFORE the Neo4j branch,
     so the Cypher obligation/gap/dimension populators are dead by default;
  3. the surviving graph-dependent populators (compliance gaps, the Article 6(3)
     AST evaluation) additionally require ``request.answers``, which the
     Regenold route deliberately never sets — so they no-op even when Neo4j is
     reachable.

Net effect measured on a live request: ``retrieval_path='kb_fallback'`` and a
5037-char Stage-2 block whose every section was computed in-process.

WHY THIS DOES NOT SIMPLY UNDO R252
==================================

R252 demoted the graph from PRIMARY retriever for a good measured reason: the
blunt ``obligations_for_risk_level`` Cypher dumps the generic high-risk chain
(Arts. 9-15) for any risk tier, which buried the operative article on
transparency / role / topic questions (the live symptom was a gold Article 50
question answered with Articles 10/11/12). Re-enabling graph-primary retrieval
would re-break that.

So this module does the opposite of what R252 removed. It never ranks, never
retrieves candidates and never contributes a wire citation. It uses the graph
for the one thing the flat KB genuinely cannot do — walk the PROVISION
HIERARCHY and the RECITAL ANCHORS of the provisions we have already decided to
cite — and renders that as explicitly NON-CITABLE Stage-2 context.

That is also precisely the evidence the R313 faithfulness verifier needs: four
of R312's five citation failures are sub-provision misattribution (Article 6(3)
credited with Article 6(4)'s duty, Article 6(2) mischaracterised, Article 3
cited for a definition Article 3(1) does not contain), and the graph holds 656
Paragraph + 416 Point nodes keyed exactly at that grain.

SAFETY
======

* Additive only: it appends a context section. It cannot displace a BM25
  winner (it never enters ranking) and cannot add a citation (the section is
  labelled non-citable and the wire reference list is built elsewhere).
* Bounded: capped refs, capped paragraphs per ref, capped chars, one query,
  short timeout.
* Fail-soft: any driver error, timeout, missing label or disabled client
  returns ``[]`` and the answer path is byte-identical to before.
* Stage-2 only ⇒ the deterministic davidath bench never reaches it.
"""

from __future__ import annotations

import logging
import os
import re
from contextvars import ContextVar

logger = logging.getLogger(__name__)

__all__ = [
    "kg_context_enabled",
    "fetch_provision_hierarchy",
    "render_kg_context",
    "reset_kg_context_memo",
]

_DEFAULT_MAX_REFS = 8
_DEFAULT_MAX_UNITS = 24
_DEFAULT_UNIT_CHARS = 900
_DEFAULT_MAX_RECITALS = 5


def kg_context_enabled() -> bool:
    """``REGENOLD_KG_CONTEXT`` — DEFAULT ON per the operator directive.

    Fresh env read per call (R263.2). Setting it to ``0`` restores the
    pre-R313.1 behaviour exactly, since every other path is untouched.
    """
    return os.getenv("REGENOLD_KG_CONTEXT", "1").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _provenance_in_prompt_enabled() -> bool:
    """``REGENOLD_PROVENANCE_IN_PROMPT`` — DEFAULT OFF.

    Whether to append the CELEX / ELI provenance block to the Stage-2
    grounding context. Off by default: it is un-A/B'd prompt budget on the
    one rubric axis we lead, and the wire may only cite ``Article N`` /
    ``Annex X`` (hard rule #1). Fresh env read per call (R263.2).
    """
    return os.getenv("REGENOLD_PROVENANCE_IN_PROMPT", "0").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _int_env(name: str, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(os.getenv(name, ""))))
    except (TypeError, ValueError):
        return default


# ── Ref parsing ──────────────────────────────────────────────────────────────
#
# The seeded node ids are ``article_<n>`` / ``annex_<ROMAN>``, and Article.number
# is a STRING property (verified against the live instance), so both are matched
# as strings rather than ints.

_ART_RE = re.compile(r"\bArt(?:s?\.|icles?|s)?\s*(\d{1,3})", re.IGNORECASE)
_ANNEX_RE = re.compile(r"\bAnnexe?s?\s+([IVXLCDM]{1,7})\b", re.IGNORECASE)


def _node_ids(refs: list[str], limit: int) -> list[str]:
    """Map citation strings to seeded node ids, order-preserving + deduped."""
    out: list[str] = []
    seen: set[str] = set()
    for ref in refs or []:
        node_id = None
        m = _ART_RE.search(str(ref))
        if m:
            node_id = f"article_{int(m.group(1))}"
        else:
            m = _ANNEX_RE.search(str(ref))
            if m:
                node_id = f"annex_{m.group(1).upper()}"
        if node_id and node_id not in seen:
            seen.add(node_id)
            out.append(node_id)
        if len(out) >= limit:
            break
    return out


# ── Cypher ───────────────────────────────────────────────────────────────────
#
# One query, one round trip. HAS_PARAGRAPH / HAS_POINT / HAS_SUBPOINT is the
# seeded hierarchy; HAS_RECITAL_ANCHOR is the interpretive anchor. Both verified
# present on the live instance this round.
#
# R318 — THE ORDER BY IS LOAD-BEARING, AND IT WAS WRONG.
#
# ``Paragraph.number`` is a STRING property (measured on the live instance: all
# 656 units reachable as ``(:Article|:Annex)-[:HAS_PARAGRAPH|HAS_POINT]->(u)``
# are ``:Paragraph`` with a numeric-string ``number``; zero non-numeric). A bare
# ``ORDER BY u.number`` is therefore a LEXICOGRAPHIC sort, and because the
# ``collect(...)[..$max_units]`` slice below is applied AFTER it, the cap did not
# take the first N provisions — it took the first N *alphabetically*.
#
# Measured against the live instance, before and after:
#   article_26  before ['1','10','11','12','2','3',...,'9']   after ['1'..'12']
#   article_3   before ['1','10',...,'29','3','30']            after ['1'..'24']
#
# The Article 3 line is the damaging one. 3 has 68 definitions, the only node
# above the 24 cap, so the string sort SILENTLY DROPPED 3(4) 'deployer',
# 3(5) 'authorised representative', 3(6) 'importer', 3(7) 'distributor' and
# 3(8) 'operator' — the role definitions — while presenting 3(10)-3(29) under an
# authoritative "PROVISION STRUCTURE" heading. Verified against the repo's own
# pinned text via ``provision_text.get_provision_text`` (hard rule #4).
#
# Fixing the ORDER alone recovers every dropped role definition, because with a
# numeric sort the first 24 units of Article 3 ARE definitions 1-24. No cap
# change, hence no extra prompt budget on Answer-Conciseness (the one rubric axis
# we lead, i.e. zero headroom).
#
# ``coalesce(..., 2147483647)`` + the ``u.number`` tiebreak keep this correct if a
# future seed ever hangs a letter-numbered unit directly off an Article: those
# sort last, alphabetically, instead of nulling the comparison.
#
# COST: free. PROFILE against the live instance shows the fixed query and the
# old one cost the SAME dbHits for the same ref set. (An earlier draft of this
# comment quoted "172 dbHits both plans" as if 172 were a property of the query;
# it is not — dbHits is strongly parameter-dependent, measured 23 for
# ['article_13'], 68 for ['article_26'], 348 for ['article_3'], 416 for
# ['article_26','article_3']. The load-bearing half — that the rewrite is
# cost-neutral — is what holds.)

_HIERARCHY_CYPHER = """
MATCH (a) WHERE a.id IN $ids AND (a:Article OR a:Annex)
OPTIONAL MATCH (a)-[:HAS_PARAGRAPH|HAS_POINT]->(u)
WITH a, u ORDER BY a.id, coalesce(toInteger(u.number), 2147483647), u.number
WITH a, collect({num: u.number, text: u.text})[..$max_units] AS units
RETURN a.id AS id,
       coalesce(a.strict_citation, a.id) AS cite,
       a.title AS title,
       units AS units
"""

_RECITAL_CYPHER = """
MATCH (a)-[:HAS_RECITAL_ANCHOR]->(r:Recital)
WHERE a.id IN $ids
RETURN a.id AS id, r.number AS num, r.text AS text
ORDER BY a.id, r.number
LIMIT $limit
"""


# ── Per-request memo ────────────────────────────────────────────────────────
#
# R318 — COLLAPSES THE DUPLICATE CYPHER ROUND-TRIPS TO 2 PER REQUEST.
#
# ``render_kg_context`` is reached from ``_build_context_references_block``,
# which is invoked more than once per request with identical arguments:
#   * ``_graph_rag_impl`` guard-allowlist mining (the result is regex-mined and
#     then thrown away),
#   * the real Stage-2 prompt build,
#   * ``logic_rag`` — this third one only when ``REGENOLD_LOGIC_RAG`` is on.
# Each pass issues both queries. Measured on live probes, the per-request render
# count is VARIABLE — 0 (no Stage-2), 2 (typical) or 3 (with logic_rag) — so a
# typical Stage-2 request paid 4 round-trips and a logic_rag one paid 6. The
# memo makes it 2 in every case, which is the true minimum: two distinct
# queries. (An earlier draft of this comment asserted a fixed 6; that was the
# worst case, not the typical one.)
#
# The saving is almost entirely network: measured RTT floor to Aura is 37-48 ms
# and the warm hierarchy query runs in 31-39 ms, so this is round-trips, not
# query work. The module docstring already claimed "One query, one round trip";
# this makes it true per request.
#
# REQUEST-SCOPED ON PURPOSE. A process-wide cache would serve stale hierarchy
# across a re-seed, which is exactly the class of silent staleness the R318
# turboquant guard exists to prevent. A ContextVar is discarded with the
# request context, mirroring the ``ReasoningTrace`` pattern already used here.
#
# The key is the FULL argument set of the Cypher call (kind + node ids + cap),
# never just ``refs`` — a partial key is how the R113 guard/prompt parity fix
# would be silently broken by a memo.
_MEMO: ContextVar[dict | None] = ContextVar("kg_context_memo", default=None)

#: Bound the memo so a pathological caller cannot grow it without limit.
_MEMO_MAX_ENTRIES = 32


def _memo_key(kind: str, ids: list[str], cap: int) -> tuple:
    return (kind, tuple(ids), int(cap))


def _memo_get(kind: str, ids: list[str], cap: int) -> list[dict] | None:
    try:
        store = _MEMO.get()
        if not store:
            return None
        return store.get(_memo_key(kind, ids, cap))
    except Exception:  # noqa: BLE001 — a memo must never break an answer
        return None


def _memo_put(kind: str, ids: list[str], cap: int, rows: list[dict]) -> None:
    try:
        store = _MEMO.get()
        if store is None:
            store = {}
            _MEMO.set(store)
        if len(store) < _MEMO_MAX_ENTRIES:
            store[_memo_key(kind, ids, cap)] = rows
    except Exception:  # noqa: BLE001
        pass


def reset_kg_context_memo() -> None:
    """Drop the per-request memo. Called by tests; harmless in production."""
    try:
        _MEMO.set(None)
    except Exception:  # noqa: BLE001
        pass


#: kg_context's OWN executor. Deliberately NOT shared with
#: ``graph_expand_2hop``.
#:
#: The first cut of this function reused the 2-hop pool ("one place to reason
#: about graph threads"). That was wrong, and the suite caught it: a trivial
#: ``submit(lambda: "ok")`` on the shared pool was MEASURED at 1274 ms under
#: full-suite ordering, so kg_context's own 500 ms budget expired before its
#: query ever started and the graph block silently vanished.
#:
#: The mechanism is not test-specific, which is why this matters in production.
#: R294 documents that a timed-out future KEEPS RUNNING in its worker thread —
#: the budget bounds the caller, not the backend. The 2-hop pool has
#: ``max_workers=2``. So two abandoned 2-hop queries against a slow or degraded
#: Aura occupy both workers for the full driver timeout, and every kg_context
#: read then queues behind them and times out. That is head-of-line blocking
#: that turns a slow graph into NO graph, precisely when the 2-hop is already
#: struggling — and the 2-hop's own refs are discarded at the fusion budget
#: anyway (R295), so it would be starving the one consumer that actually
#: reaches an answer on behalf of one that does not.
_EXECUTOR: object | None = None


def _get_kg_executor():
    """Lazy, module-private single-worker pool.

    Deferred import: ``concurrent.futures`` pulls ``threading`` + ``queue``
    (~40 ms cold), and this module is imported on every request path even when
    the graph is disabled.
    """
    global _EXECUTOR
    if _EXECUTOR is None:
        from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415

        _EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="kgctx")
    return _EXECUTOR


def _bounded_execute_read(cypher: str, params: dict) -> list[dict]:
    """Run one read against the graph under the R294 budget + circuit breaker.

    R318 — CLOSES A REAL AVAILABILITY HOLE. Both fetchers below used to call
    ``client.execute_read(...)`` DIRECTLY, which bypasses everything R294 built:

    * ``app/graph/client.py`` retries with linear backoff on a 5.0 s
      ``connection_timeout`` (``app/graph/config.py``), so a graph that ACCEPTS
      a connection and then hangs can stall for many seconds per call;
    * ``render_kg_context`` is reached 2-3x per request and issues 2 queries
      each, so every one of those stalls is paid several times over;
    * and nothing recorded the failures, so the breaker never opened and EVERY
      subsequent request paid the same cost again.

    HONEST MAGNITUDE. The specific R290 DNS-dead-Aura scenario is CHEAPER than a
    first draft of this docstring claimed: measured against a non-resolving host,
    ``execute_read`` returns in ~1.55 s, because the driver raises a DNS error
    that is NOT ``ServiceUnavailable``, so ``client.py``'s retry branch is
    skipped entirely and it gives up on the first attempt. So a dark-DNS request
    cost ~3-6 s, not the ~99 s originally asserted. The hole is real and worth
    closing — an unbounded, unrecorded, repeated network call on the answer path
    — but it is a seconds-scale regression, not a minute-scale one, and the
    worst case is a graph that accepts connections and then hangs (which the DNS
    path does not exercise). R294 built the breaker precisely so a degraded graph
    could not spend the raised budget on every request; this consumer was wired
    around it.

    Fail-soft by construction: any timeout, breaker-open or driver error returns
    ``[]``, and both callers already treat ``[]`` as "render nothing", so the
    answer path is byte-identical to before on a healthy graph.

    NOTE the R294 caveat, which applies here too: a timed-out future keeps
    running in the worker thread. This bounds the CALLER, not the backend.
    """
    from app.graph.timeouts import (  # noqa: PLC0415
        graph_circuit_open,
        record_graph_failure,
        record_graph_success,
        resolve_graph_timeout_ms,
    )

    if graph_circuit_open():
        logger.debug("kg_context: skipped — graph circuit open")
        return []

    from app.graph.client import get_graph_client  # noqa: PLC0415

    client = get_graph_client()
    if not getattr(client, "enabled", False):
        return []

    def _call() -> list[dict]:
        return list(client.execute_read(cypher, params) or [])

    from concurrent.futures import TimeoutError as _FutTimeout  # noqa: PLC0415

    budget_ms = resolve_graph_timeout_ms()
    try:
        fut = _get_kg_executor().submit(_call)
        rows = fut.result(timeout=max(budget_ms, 1) / 1000.0)
        record_graph_success()
        return rows
    except _FutTimeout:
        record_graph_failure()
        logger.info("kg_context: cypher timeout budget=%dms", budget_ms)
        return []
    except Exception:  # noqa: BLE001 — the graph must never break an answer
        record_graph_failure()
        logger.debug("kg_context: bounded read failed", exc_info=True)
        return []


def _flat(text: object, limit: int) -> str:
    t = " ".join(str(text or "").split())
    if len(t) <= limit:
        return t
    cut = t[:limit]
    for sep in (". ", "; ", ", "):
        idx = cut.rfind(sep)
        if idx > limit // 2:
            return cut[: idx + 1].strip()
    idx = cut.rfind(" ")
    return (cut[:idx] if idx > limit // 2 else cut).strip()


def fetch_provision_hierarchy(refs: list[str]) -> list[dict]:
    """Paragraph/point breakdown of the cited provisions, straight from Aura.

    Returns ``[]`` on ANY failure — disabled gate, no driver, unreachable
    instance, unseeded labels, timeout. Never raises.
    """
    if not kg_context_enabled():
        return []
    ids = _node_ids(refs or [], _int_env("REGENOLD_KG_MAX_REFS", _DEFAULT_MAX_REFS, 1, 10))
    if not ids:
        return []
    # R318 — ceiling raised 30 -> 70. The old clamp made the cap UNTUNABLE for the
    # one node that exceeds it: Article 3 has 68 definitions, so even setting
    # REGENOLD_KG_MAX_UNITS=68 was silently clamped to 30. The DEFAULT is
    # deliberately unchanged at 24 — raising it would add prompt budget on
    # Answer-Conciseness (zero headroom) with no A/B, and the R318 ordering fix
    # already recovers the provisions that actually mattered. Raising a ceiling
    # nobody sets is behaviour-neutral.
    max_units = _int_env("REGENOLD_KG_MAX_UNITS", _DEFAULT_MAX_UNITS, 1, 70)
    cached = _memo_get("hierarchy", ids, max_units)
    if cached is not None:
        return cached
    rows = _bounded_execute_read(_HIERARCHY_CYPHER, {"ids": ids, "max_units": max_units})
    _memo_put("hierarchy", ids, max_units, rows)
    return rows


def fetch_recital_anchors(refs: list[str]) -> list[dict]:
    """Recitals anchored to the cited provisions (interpretive context only)."""
    if not kg_context_enabled():
        return []
    ids = _node_ids(refs or [], _int_env("REGENOLD_KG_MAX_REFS", _DEFAULT_MAX_REFS, 1, 10))
    if not ids:
        return []
    limit = _int_env("REGENOLD_KG_MAX_RECITALS", _DEFAULT_MAX_RECITALS, 0, 10)
    if limit <= 0:
        return []
    cached = _memo_get("recitals", ids, limit)
    if cached is not None:
        return cached
    rows = _bounded_execute_read(_RECITAL_CYPHER, {"ids": ids, "limit": limit})
    _memo_put("recitals", ids, limit, rows)
    return rows


def render_kg_context(refs: list[str]) -> list[str]:
    """Render the graph's contribution as NON-CITABLE Stage-2 context.

    The label matters: it tells the model this is structure and interpretive
    background for provisions ALREADY cited, so it can attribute a duty to the
    right paragraph without treating the graph as licence to cite more. Every
    other non-citable block in the Stage-2 prompt uses the same framing.
    """
    if not kg_context_enabled():
        return []
    parts: list[str] = []
    unit_chars = _int_env("REGENOLD_KG_UNIT_CHARS", _DEFAULT_UNIT_CHARS, 80, 1200)

    try:
        rows = fetch_provision_hierarchy(refs)
    except Exception:  # noqa: BLE001
        rows = []
    lines: list[str] = []
    for row in rows:
        cite = str(row.get("cite") or row.get("id") or "").strip()
        title = str(row.get("title") or "").strip()
        units = [u for u in (row.get("units") or []) if u and u.get("text")]
        if not cite or not units:
            continue
        head = f"- {cite}" + (f" ({title})" if title else "") + ":"
        lines.append(head)
        for unit in units:
            num = str(unit.get("num") or "").strip()
            body = _flat(unit.get("text"), unit_chars)
            if body:
                lines.append(f"    ({num}) {body}" if num else f"    {body}")
    if lines:
        parts.append(
            "\nKNOWLEDGE-GRAPH PROVISION STRUCTURE "
            "(from the seeded EU AI Act graph — the paragraph and point "
            "breakdown of provisions ALREADY listed above. Use it to attribute "
            "a duty to the CORRECT paragraph, and to state a condition or "
            "derogation at the right sub-provision. Do NOT cite anything here "
            "that is not already listed above, and do NOT cite a paragraph "
            "number as a separate provision):\n"
            + "\n".join(lines)
        )

    try:
        recitals = fetch_recital_anchors(refs)
    except Exception:  # noqa: BLE001
        recitals = []
    rec_lines = [
        f"- Recital {r.get('num')}: {_flat(r.get('text'), unit_chars)}"
        for r in recitals
        if r.get("text")
    ]
    if rec_lines:
        parts.append(
            "\nKNOWLEDGE-GRAPH RECITAL ANCHORS "
            "(interpretive context only — recitals are NOT operative provisions "
            "and must NEVER appear as an Article/Annex citation):\n"
            + "\n".join(rec_lines)
        )

    # ── Legal provenance (env-gated, default OFF) ────────────────────────
    #
    # The first cut of this block shipped default-ON, unconditionally, and
    # asserted CELEX 02024R1689-20260727 — the POST-Digital-Omnibus
    # consolidation (69 EUR-Lex M1 markers pointing at CELEX 32026R1744,
    # "Digital Omnibus on AI"). Our corpus is the PRE-Omnibus original,
    # CELEX 32024R1689, so that block asserted a provenance the shipped text
    # does not have — hard rule #4.
    #
    # It is now (a) corrected from the pinned provenance module, (b) gated
    # OFF by default and (c) appended only when there is other graph context.
    # Default OFF because it is un-A/B'd prompt budget on the ONE rubric axis
    # we lead (Answer-Conciseness, zero headroom), and because the wire may
    # only ever cite "Article N" / "Annex X" (hard rule #1) — a CELEX in the
    # model's context is a citation shape it must never emit. Provenance
    # belongs on the graph nodes and in the audit trail, not in the answer
    # prompt. Set REGENOLD_PROVENANCE_IN_PROMPT=1 to A/B it back on.
    if parts and _provenance_in_prompt_enabled():
        try:
            from app.data.lawstronaut_provenance import (  # noqa: PLC0415
                OFFICIAL_CELEX,
                OFFICIAL_ELI,
                OFFICIAL_LEGAL_LINK,
                OFFICIAL_PROVENANCE_LINE,
            )

            parts.append(
                "\nOFFICIAL LEGAL PROVENANCE (context only — NEVER cite a CELEX "
                "or ELI on the wire; citations are 'Article N' / 'Annex X' only):\n"
                f"- Instrument: {OFFICIAL_PROVENANCE_LINE}\n"
                f"- CELEX: {OFFICIAL_CELEX}\n"
                f"- ELI: {OFFICIAL_ELI}\n"
                f"- Source: {OFFICIAL_LEGAL_LINK}\n"
            )
        except Exception:  # noqa: BLE001
            pass

    if parts:
        try:
            from app.integrations.regenold.reasoning_trace import (  # noqa: PLC0415
                record_note,
            )
            record_note(f"kg_context sections={len(parts)} refs={len(refs or [])}")
        except Exception:  # noqa: BLE001
            pass
    return parts
