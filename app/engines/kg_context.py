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
import threading
from contextvars import ContextVar

logger = logging.getLogger(__name__)

__all__ = [
    "kg_context_enabled",
    "fetch_provision_hierarchy",
    "fetch_recital_anchors",
    "fetch_subpoint_detail",
    "fetch_deontic_context",
    "render_kg_context",
    "reset_kg_context_memo",
]

_DEFAULT_MAX_REFS = 8
_DEFAULT_MAX_UNITS = 24
_DEFAULT_UNIT_CHARS = 900
_DEFAULT_MAX_RECITALS = 5
#: Total ceiling across every block ``render_kg_context`` returns (R323, ported
#: from the RAG repo in R325). Without it a 12-ref scenario can inject an
#: unbounded wall of provision text that crowds the rest of the Stage-2 prompt.
_DEFAULT_MAX_CHARS = 16000
#: R327 — ceiling used only when the semantic vector layers contribute a block.
#:
#: Sized from measurement, not taste. At 5 refs the layers need ~8.4k while the
#: pre-existing blocks need ~15.6k, so a shared 16,000 ceiling forced the layers
#: to evict 3,545 chars — 2,600 of it out of PROVISION STRUCTURE, the most
#: load-bearing block. 24,000 still clipped the hierarchy by 52 chars (12,139
#: needed vs 12,087 available), which ``_fit_complete_lines`` rounds down to a
#: 768-char loss at the line boundary. 26,000 leaves every pre-existing block
#: intact, so the layers-ON arm is a strict superset of the layers-OFF arm and
#: any A/B delta is attributable to the added context alone.
#: Override with ``REGENOLD_KG_SEMANTIC_MAX_CHARS``.
_DEFAULT_SEMANTIC_MAX_CHARS = 26000


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
        for m in _ART_RE.finditer(str(ref)):
            node_id = f"article_{int(m.group(1))}"
            if node_id not in seen:
                seen.add(node_id)
                out.append(node_id)
                if len(out) >= limit:
                    return out
        for m in _ANNEX_RE.finditer(str(ref)):
            node_id = f"annex_{m.group(1).upper()}"
            if node_id not in seen:
                seen.add(node_id)
                out.append(node_id)
                if len(out) >= limit:
                    return out
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

# R327 — THE PROVISION-LEVEL ORDER WAS ALSO WRONG, for the same reason.
#
# R318 (above) fixed the ordering of units WITHIN a provision. The ordering OF
# the provisions was still ``ORDER BY a.id``, i.e. lexicographic over node ids,
# and ``_node_ids`` receives the refs in RETRIEVAL-RANK order. Measured live:
#
#   in  ['Article 50', 'Article 5', 'Annex III', 'Article 26', 'Article 6']
#   out ['Annex III',  'Article 26', 'Article 5', 'Article 50', 'Article 6']
#
# so the top-ranked provision came back 4th of 5. That is load-bearing because
# ``_fit_complete_lines`` truncates this block at a line boundary when it exceeds
# the ceiling: the tail is dropped, and the tail was whatever sorted last
# alphabetically rather than whatever mattered least.
#
# The index-preserving idiom (UNWIND the positions, carry ``i``, ORDER BY ``i``)
# is taken from the Cypher appendix of "Reducing Hallucinations in Complex
# Question Answering using Simple Graph-based RAG" (query B.6), which uses it to
# return sections in caller-supplied order. Cost-neutral: same node lookups by
# id, one extra integer carried through.
_HIERARCHY_CYPHER = """
UNWIND range(0, size($ids) - 1) AS i
WITH i, $ids[i] AS aid
MATCH (a) WHERE a.id = aid AND (a:Article OR a:Annex)
OPTIONAL MATCH (a)-[:HAS_PARAGRAPH|HAS_POINT]->(u)
WITH i, a, u ORDER BY i, coalesce(toInteger(u.number), 2147483647), u.number
WITH i, a, collect({num: u.number, text: u.text})[..$max_units] AS units
RETURN a.id AS id,
       coalesce(a.strict_citation, a.id) AS cite,
       a.title AS title,
       units AS units
ORDER BY i
"""

# R327 — same index-preserving fix (B.6). ``LIMIT $limit`` truncates this result,
# so ordering it alphabetically meant the recitals kept were the ones anchored to
# the alphabetically-first provision, not the highest-ranked one.
_RECITAL_CYPHER = """
UNWIND range(0, size($ids) - 1) AS i
WITH i, $ids[i] AS aid
MATCH (a)-[:HAS_RECITAL_ANCHOR]->(r:Recital)
WHERE a.id = aid
RETURN a.id AS id, r.number AS num, r.text AS text
ORDER BY i, coalesce(toInteger(r.number), 2147483647), r.number
LIMIT $limit
"""

# R327 — same index-preserving fix (B.6); ``LIMIT $limit`` applies here too.
_SUBPOINT_CYPHER = """
UNWIND range(0, size($ids) - 1) AS i
WITH i, $ids[i] AS aid
MATCH (a) WHERE a.id = aid AND (a:Article OR a:Annex)
MATCH (a)-[:HAS_PARAGRAPH]->(p)-[:HAS_POINT]->(pt)-[:HAS_SUBPOINT]->(s:SubPoint)
RETURN coalesce(a.strict_citation, a.id) AS cite,
       p.number AS para, pt.letter AS letter, s.roman AS roman,
       s.id AS sid, s.text AS text
ORDER BY i, coalesce(toInteger(p.number), 2147483647), p.number, pt.letter, s.id
LIMIT $limit
"""

#: R327 — ``CALL () { ... }``, not a bare ``CALL { ... }``.
#:
#: The bare form parses and returns correct rows on Aura 0644b854 (verified live:
#: 3 rows for ['article_5','article_6','annex_III'], including the Annex III
#: UNION branch), but the server answers with
#: ``01N00 CALL subquery without a variable scope clause is deprecated``. The
#: explicit empty scope clause is the supported spelling and imports nothing —
#: parameters like ``$ids`` are always in scope inside a subquery, which is why
#: the aliased importing ``WITH $ids AS ids`` was legal here too.
_DEONTIC_CYPHER = """
CALL () {
    MATCH (a:Article) WHERE a.id IN $ids
    OPTIONAL MATCH (pr:Practice)-[:PROHIBITED_UNDER]->(a)
    OPTIONAL MATCH (cat:AnnexIIICategory)-[:TRIGGERS_HIGH_RISK_UNDER]->(a)
    OPTIONAL MATCH (ro:OperatorRole)-[hoa:HAS_OBLIGATION_ARTICLE]->(a)
    OPTIONAL MATCH (ph:LifecyclePhase)-[:APPLIES_TO]->(a)
    RETURN coalesce(a.strict_citation, a.id) AS cite,
           collect(DISTINCT coalesce(pr.short_name, pr.id)) AS practices,
           collect(DISTINCT coalesce(cat.label, cat.id)) AS annex_iii,
           collect(DISTINCT coalesce(ro.label, ro.id) + ' (' + coalesce(hoa.tier,'') + ')') AS roles,
           collect(DISTINCT coalesce(ph.label, ph.id) + ' from ' + coalesce(ph.effective_date,'')) AS phases
    UNION
    MATCH (cat:AnnexIIICategory)
    WHERE 'annex_III' IN $ids
    RETURN 'Annex III' AS cite,
           [] AS practices,
           collect(DISTINCT coalesce(cat.label, cat.id)) AS annex_iii,
           [] AS roles,
           [] AS phases
}
RETURN cite, practices, annex_iii, roles, phases
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
_EXECUTOR_LOCK = threading.Lock()
#: R327 — 4, not 2. One request now issues up to six bounded reads (hierarchy,
#: sub-points, deontic, recital anchors, and the two R327 semantic-layer reads),
#: and the eval harness runs at concurrency 3. Two slots made the pool the
#: bottleneck for the graph's own contribution. Still small enough to bound the
#: number of abandoned driver calls a degraded Aura can accumulate.
_KG_MAX_INFLIGHT = _int_env("REGENOLD_KG_MAX_INFLIGHT", 4, 1, 8)
_KG_ADMISSION = threading.BoundedSemaphore(_KG_MAX_INFLIGHT)


class _ReadRows(list):
    """List-compatible result that distinguishes errors from empty matches."""

    def __init__(self, rows=(), *, failed: bool = False):
        super().__init__(rows)
        self.failed = failed


def _get_kg_executor():
    """Lazy, module-private bounded worker pool.

    Deferred import: ``concurrent.futures`` pulls ``threading`` + ``queue``
    (~40 ms cold), and this module is imported on every request path even when
    the graph is disabled.
    """
    global _EXECUTOR
    if _EXECUTOR is None:
        with _EXECUTOR_LOCK:
            if _EXECUTOR is None:
                from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415

                _EXECUTOR = ThreadPoolExecutor(
                    max_workers=_KG_MAX_INFLIGHT,
                    thread_name_prefix="kgctx",
                )
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
        return _ReadRows(failed=True)

    from app.graph.client import get_graph_client  # noqa: PLC0415

    client = get_graph_client()
    if not getattr(client, "enabled", False):
        return _ReadRows(failed=True)

    def _call() -> list[dict]:
        strict_read = getattr(client, "execute_read_strict", None)
        if callable(strict_read):
            return list(strict_read(cypher, params) or [])
        # Compatibility for graph test doubles and older embedders. Production
        # GraphClient exposes the strict method so backend errors cannot be
        # mistaken for a successful query with no matches.
        return list(client.execute_read(cypher, params) or [])

    from concurrent.futures import TimeoutError as _FutTimeout  # noqa: PLC0415

    budget_ms = resolve_graph_timeout_ms()
    # R327 — WAIT for a slot instead of dropping the read.
    #
    # The admission gate arrived as ``acquire(blocking=False)``, which turns
    # every concurrent read beyond the second into an immediate failure. One
    # request issues several kg_context reads, and the eval harness runs at
    # concurrency 3, so under exactly the load the graph exists to serve, a large
    # share of reads returned "failed" and the graph context silently vanished —
    # the opposite of what the admission gate was for. The gate's real job is to
    # stop an UNBOUNDED queue of abandoned driver calls piling up behind the
    # workers, and a bounded wait does that just as well.
    #
    # The wait is charged against the SAME budget as the query, so the total
    # caller-visible cost is still bounded by ``resolve_graph_timeout_ms`` and a
    # saturated pool degrades to the timeout path rather than to a hard drop.
    _admit_budget_s = max(budget_ms, 1) / 1000.0
    if not _KG_ADMISSION.acquire(timeout=_admit_budget_s):
        record_graph_failure()
        logger.info(
            "kg_context: graph worker admission saturated after %.0fms",
            _admit_budget_s * 1000.0,
        )
        return _ReadRows(failed=True)

    fut = None
    try:
        fut = _get_kg_executor().submit(_call)
        # A timeout only bounds the caller. Keep the admission slot occupied
        # until the backend task really stops, preventing an unbounded queue of
        # abandoned driver calls behind the two workers.
        fut.add_done_callback(lambda _done: _KG_ADMISSION.release())
        rows = fut.result(timeout=max(budget_ms, 1) / 1000.0)
        record_graph_success()
        return _ReadRows(rows)
    except _FutTimeout:
        if fut is not None:
            fut.cancel()
        record_graph_failure()
        logger.info("kg_context: cypher timeout budget=%dms", budget_ms)
        return _ReadRows(failed=True)
    except Exception:  # noqa: BLE001 — the graph must never break an answer
        if fut is None:
            _KG_ADMISSION.release()
        record_graph_failure()
        logger.debug("kg_context: bounded read failed", exc_info=True)
        return _ReadRows(failed=True)


#: An enumeration opening inside the budget means the LIST is the obligation.
_ENUM_OPENER_RE = re.compile(r"(?:\(?a\)\s|\(?1\)\s|1\.\s)")

#: Hard ceiling for a single unit once the enumeration guard has extended it.
#: Bounds the worst case so one pathological provision cannot dominate the
#: Stage-2 budget.
_UNIT_HARD_CEILING = 2600


def _flat(text: object, limit: int) -> str:
    """Flatten a provision to at most ``limit`` chars, losing as little as possible.

    R325 — ported from the RAG repo's R323 + R324. Measured HERE before the
    port: ``render_kg_context(['Article 5'])`` delivered only **3 of the 8**
    Article 5(1) prohibited practices. (a) subliminal, (b) vulnerability,
    (d) criminal-risk profiling, (e) facial scraping and (h) real-time RBI were
    all cut away, with nothing marking the truncation — a prohibition shipped
    without its scope reads as if the list were complete.

    Two distinct amputations are fixed:

    1. BACKTRACK COULD DISCARD HALF THE BUDGET. The sentence-boundary search
       accepted any break past ``limit // 2``, so a 1421-char provision at a
       900 budget was delivered at ~470 chars (33%). The accepted break must
       now fall in the last QUARTER of the budget; a nearer one loses too much
       and we fall through to a clause, then a word boundary.

    2. IT CUT MID-ENUMERATION WITHOUT SAYING SO. When an enumeration opens
       inside the budget the whole unit is delivered up to
       ``_UNIT_HARD_CEILING``; beyond that the text is explicitly marked
       ``[...]`` rather than ending mid-clause as if it were complete.

    ``_UNIT_HARD_CEILING`` is a CEILING, not a switch. The RAG repo's first cut
    fell straight back to ``limit`` past the ceiling, so a 2599-char
    enumeration was delivered whole and a 2601-char one was cut at 900 — the
    cliff landing on the LONGEST enumerations, exactly the "duty defined by its
    list" cases the guard exists for. Cut AT the ceiling and mark it.
    """
    t = " ".join(str(text or "").split())
    if len(t) <= limit:
        return t

    if _ENUM_OPENER_RE.search(t[:limit]):
        if len(t) <= _UNIT_HARD_CEILING:
            return t
        limit = _UNIT_HARD_CEILING

    cut = t[:limit]
    floor = (limit * 3) // 4
    for sep in (". ", "; ", ", "):
        idx = cut.rfind(sep)
        if idx > floor:
            return cut[: idx + 1].strip() + " [...]"
    idx = cut.rfind(" ")
    return ((cut[:idx] if idx > floor else cut).strip()) + " [...]"


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
    if not getattr(rows, "failed", False):
        _memo_put("hierarchy", ids, max_units, list(rows))
    return list(rows)


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
    if not getattr(rows, "failed", False):
        _memo_put("recitals", ids, limit, list(rows))
    return list(rows)


def fetch_subpoint_detail(refs: list[str]) -> list[dict]:
    """Sub-point leaves of cited provisions, without inferring legal effect."""
    if not kg_context_enabled():
        return []
    ids = _node_ids(refs or [], _int_env("REGENOLD_KG_MAX_REFS", _DEFAULT_MAX_REFS, 1, 10))
    if not ids:
        return []
    cached = _memo_get("subpoint", ids, 24)
    if cached is not None:
        return cached
    rows: list[dict] = _ReadRows(failed=True)
    try:
        rows = _bounded_execute_read(_SUBPOINT_CYPHER, {"ids": ids, "limit": 24})
        result = list(rows or [])
    except Exception:  # noqa: BLE001
        logger.debug("kg_context: subpoint fetch failed", exc_info=True)
        result = []
    if not getattr(rows, "failed", False):
        _memo_put("subpoint", ids, 24, result)
    return result


def fetch_deontic_context(refs: list[str]) -> list[dict]:
    """Prohibited practices / Annex III categories / role duties / phases."""
    if not kg_context_enabled():
        return []
    ids = _node_ids(refs or [], _int_env("REGENOLD_KG_MAX_REFS", _DEFAULT_MAX_REFS, 1, 10))
    if not ids:
        return []
    cached = _memo_get("deontic", ids, 12)
    if cached is not None:
        return cached
    rows: list[dict] = _ReadRows(failed=True)
    try:
        rows = _bounded_execute_read(_DEONTIC_CYPHER, {"ids": ids, "limit": 12})
        result = list(rows or [])
    except Exception:  # noqa: BLE001
        logger.debug("kg_context: deontic fetch failed", exc_info=True)
        result = []
    if not getattr(rows, "failed", False):
        _memo_put("deontic", ids, 12, result)
    return result


_R326_RESERVED_MARKERS = (
    "KNOWLEDGE-GRAPH SUB-POINT DETAIL",
    "KNOWLEDGE-GRAPH REGULATORY CLASSIFICATION",
    # R327 — the semantic layers need reserved capacity for the same reason the
    # R326 blocks do: they render AFTER the hierarchy block, and a large
    # hierarchy would otherwise consume the whole ceiling and delete them. That
    # is the "budget the thing you just added" failure — a new context block
    # that silently removes itself.
    "KNOWLEDGE-GRAPH QUESTION-FOCUSED SUB-PROVISIONS",
    "KNOWLEDGE-GRAPH DEFINITIONS",
    "KNOWLEDGE-GRAPH RECITAL CONTEXT",
)


def _fit_complete_lines(block: str, budget: int) -> str:
    """Fit a block without cutting a rendered hierarchy/deontic row."""
    if not block or budget <= 0:
        return ""
    if len(block) <= budget:
        return block

    kept: list[str] = []
    used = 0
    for line in block.splitlines():
        cost = len(line) + (1 if kept else 0)
        if used + cost > budget:
            break
        kept.append(line)
        used += cost

    # A hierarchy article heading is not useful without at least one unit and
    # looks complete if stranded at the boundary. Drop such dangling headings.
    while kept and kept[-1].lstrip().startswith("- ") and kept[-1].rstrip().endswith(":"):
        kept.pop()
    if len([line for line in kept if line.strip()]) < 2:
        return ""
    return "\n".join(kept)


def _budget_context_parts(parts: list[str], max_chars: int) -> tuple[list[str], int]:
    """Apply a hard total cap while reserving half for present R326 blocks."""
    if not parts:
        return [], 0

    reserved_indexes = [
        idx for idx, part in enumerate(parts)
        if any(marker in part for marker in _R326_RESERVED_MARKERS)
    ]
    fitted: dict[int, str] = {}
    used = 0

    # Fit the new graph shapes first inside a reserved half-budget. They are
    # otherwise always the first sections discarded by a large hierarchy.
    #
    # R327 — allocate SMALLEST-NEED-FIRST (max-min fair), not in index order with
    # an equal split. With an equal split, a reserved block whose need exceeds its
    # 1/N share gets trimmed below two lines and is then dropped outright, while
    # blocks that needed less than their share leave their remainder unused.
    # MEASURED: at 5 refs that dropped the QUESTION-FOCUSED SUB-PROVISIONS block
    # — the highest-precision block of the set — i.e. the feature deleted itself.
    # Taking the smallest need first lets each small block claim exactly what it
    # needs and rolls the surplus forward to the larger ones.
    reserve_left = max_chars // 2
    ordered_reserved = sorted(reserved_indexes, key=lambda i: len(parts[i]))
    for pos, idx in enumerate(ordered_reserved):
        slots_left = len(ordered_reserved) - pos
        allocation = max(reserve_left // max(slots_left, 1), 0)
        # Never hand a block more than it needs; the surplus benefits the rest.
        allocation = min(allocation, len(parts[idx]) + 1)
        block = _fit_complete_lines(parts[idx], max(0, allocation - 1))
        if block:
            fitted[idx] = block
            cost = len(block) + 1  # caller joins returned parts with a newline
            used += cost
            reserve_left -= cost

    # Hierarchy remains first in output, followed by lower-priority recitals
    # and provenance when room remains. No individual block can defeat the cap.
    for idx, part in enumerate(parts):
        if idx in reserved_indexes:
            continue
        block = _fit_complete_lines(part, max(0, max_chars - used - 1))
        if not block:
            continue
        fitted[idx] = block
        used += len(block) + 1
        if used >= max_chars:
            break

    ordered = [fitted[idx] for idx in range(len(parts)) if idx in fitted]
    trimmed_or_dropped = sum(
        1 for idx, part in enumerate(parts) if fitted.get(idx) != part
    )
    return ordered, trimmed_or_dropped


def _render_semantic_layers(question: str, refs: list[str]) -> list[str]:
    """R327 — the five previously-dark vector indexes, as non-citable context.

    See :mod:`app.engines.graph_semantic` for why paragraph/point/subpoint are
    provision-constrained while definitions/recitals are open-domain. Default
    OFF behind ``REGENOLD_GRAPH_SEMANTIC_LAYERS``.

    R329 P2 — with ``REGENOLD_SEMANTIC_COORDINATES`` on (default OFF) each
    focused line is labelled with its LEGAL COORDINATE (``- Article 12.1: …``)
    instead of the head-level cite plus an internal node id
    (``- Article 12 [paragraph para_12_1]: …``). LABEL ONLY: the block's
    non-citable framing below is unchanged, per hard rule #10.
    """
    if not question:
        return []
    try:
        from app.engines.graph_semantic import (  # noqa: PLC0415
            coordinate_for_row,
            fetch_definition_and_recital_context,
            fetch_focused_subprovisions,
            semantic_coordinates_enabled,
            semantic_layers_enabled,
        )

        if not semantic_layers_enabled():
            return []
        coordinates_on = semantic_coordinates_enabled()
    except Exception:  # noqa: BLE001
        return []

    parts: list[str] = []
    unit_chars = _int_env("REGENOLD_KG_UNIT_CHARS", _DEFAULT_UNIT_CHARS, 80, 1200)

    try:
        focused = fetch_focused_subprovisions(question, refs)
    except Exception:  # noqa: BLE001
        focused = []
    focus_lines: list[str] = []
    for row in focused:
        text = _flat(row.get("text"), unit_chars)
        if not text:
            continue
        # A row whose coordinate cannot be rebuilt IN FULL keeps the existing
        # label. Falling back is the point: a partial coordinate would relabel a
        # sub-point's text as its parent's, which is worse than no coordinate.
        coord = coordinate_for_row(row) if coordinates_on else None
        if coord:
            focus_lines.append(f"- {coord}: {text}")
            continue
        layer = str(row.get("layer") or "unit").lower()
        focus_lines.append(
            f"- {row.get('cite')} [{layer} {row.get('uid')}]: {text}"
        )
    if focus_lines:
        parts.append(
            "\nKNOWLEDGE-GRAPH QUESTION-FOCUSED SUB-PROVISIONS "
            "(the paragraphs, points and sub-points OF THE PROVISIONS ALREADY "
            "LISTED ABOVE that are closest to this question, ranked by the "
            "graph's own vector indexes. Use them to attribute the duty to the "
            "right sub-provision. They add NO new provision — every one belongs "
            "to a provision already cited — so do NOT cite anything new here):\n"
            + "\n".join(focus_lines)
        )

    try:
        gloss = fetch_definition_and_recital_context(question, refs)
    except Exception:  # noqa: BLE001
        gloss = []
    def_lines: list[str] = []
    rec_lines: list[str] = []
    for row in gloss:
        text = _flat(row.get("text"), unit_chars)
        if not text:
            continue
        if str(row.get("layer")) == "Definition":
            cite = str(row.get("cite") or "").strip()
            suffix = f" ({cite})" if cite else ""
            def_lines.append(f"- '{row.get('label')}'{suffix}: {text}")
        else:
            rec_lines.append(f"- Recital {row.get('label')}: {text}")
    if def_lines:
        parts.append(
            "\nKNOWLEDGE-GRAPH DEFINITIONS "
            "(Article 3 definitions semantically closest to this question — "
            "use them for the correct legal meaning of a term. Definitional "
            "background only: do NOT add a citation just because a definition "
            "appears here):\n"
            + "\n".join(def_lines)
        )
    if rec_lines:
        parts.append(
            "\nKNOWLEDGE-GRAPH RECITAL CONTEXT "
            "(interpretive background retrieved semantically. Recitals are NOT "
            "operative provisions and must NEVER appear as an Article/Annex "
            "citation):\n"
            + "\n".join(rec_lines)
        )
    return parts


def render_kg_context(refs: list[str], question: str = "") -> list[str]:
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
        subpoints = fetch_subpoint_detail(refs)
    except Exception:  # noqa: BLE001
        subpoints = []
    sp_lines = []
    for sp in subpoints:
        text = _flat(sp.get("text"), unit_chars)
        if text:
            roman = str(sp.get("roman") or "").strip().lower()
            if not roman:
                sid = str(sp.get("sid") or "").strip()
                match = re.search(r"(?:^|[_\-.])([ivxlcdm]+)$", sid, re.IGNORECASE)
                roman = match.group(1).lower() if match else ""
            coordinate = (
                f"{sp.get('cite')}, paragraph {sp.get('para')}, "
                f"point ({sp.get('letter')})"
            )
            if roman:
                coordinate += f", subpoint ({roman})"
            sp_lines.append(f"- {coordinate}: {text}")
    if sp_lines:
        parts.append(
            "\nKNOWLEDGE-GRAPH SUB-POINT DETAIL "
            "(nested enumerated text attached to the provisions above; use the "
            "full paragraph/point/subpoint coordinate when interpreting it. "
            "This structural label does not itself assert a condition, exception "
            "or legal effect):\n"
            + "\n".join(sp_lines)
        )

    try:
        deontics = fetch_deontic_context(refs)
    except Exception:  # noqa: BLE001
        deontics = []
    deontic_lines = []
    for d in deontics:
        cite = str(d.get('cite') or "").strip()
        pieces = []
        if d.get('practices') and any(x for x in d['practices'] if x):
            pieces.append(f"Prohibited practices: {', '.join(x for x in d['practices'] if x)}")
        if d.get('annex_iii') and any(x for x in d['annex_iii'] if x):
            pieces.append(f"Annex III categories: {', '.join(x for x in d['annex_iii'] if x)}")
        if d.get('roles') and any(x for x in d['roles'] if x):
            pieces.append(f"Operator roles: {', '.join(x for x in d['roles'] if x)}")
        if d.get('phases') and any(x for x in d['phases'] if x):
            pieces.append(f"Lifecycle phases: {', '.join(x for x in d['phases'] if x)}")
        if pieces:
            deontic_lines.append(f"- {cite}: " + "; ".join(pieces))
    if deontic_lines:
        parts.append(
            "\nKNOWLEDGE-GRAPH REGULATORY CLASSIFICATION "
            "(role duties, risk categories and lifecycle phases attached to the "
            "provisions above — non-citable structural context):\n"
            + "\n".join(deontic_lines)
        )

    # R327 — the five previously-dark vector indexes. Placed before the
    # structural HAS_RECITAL_ANCHOR block because that edge type exists only 5
    # times in the whole graph, so it contributes nothing for 111 of 113
    # articles, whereas these layers are populated for every provision.
    try:
        parts.extend(_render_semantic_layers(question, refs))
    except Exception:  # noqa: BLE001 — the graph must never break an answer
        logger.debug("kg_context: semantic layer render failed", exc_info=True)

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

    # R326 — hard total ceiling with reserved capacity for the new structural
    # layers. Truncation is only at rendered line boundaries, never mid-row.
    #
    # R327 — when the semantic layers contribute, the ceiling rises.
    #
    # MEASURED at 5 refs with one shared 16,000 ceiling: the new blocks displaced
    # 3,545 chars of existing context, 2,600 of it out of PROVISION STRUCTURE —
    # the most load-bearing block there is. A "purely additive" layer that
    # silently deletes the hierarchy is not additive. Raising the ceiling only in
    # the layers-ON arm ALSO keeps the layers-OFF arm byte-identical, which the
    # ab_judge / easyhard_ab A/B needs in order to attribute any delta.
    if any(
        marker in part
        for part in parts
        for marker in (
            "KNOWLEDGE-GRAPH QUESTION-FOCUSED SUB-PROVISIONS",
            "KNOWLEDGE-GRAPH DEFINITIONS",
            "KNOWLEDGE-GRAPH RECITAL CONTEXT",
        )
    ):
        max_chars = _int_env(
            "REGENOLD_KG_SEMANTIC_MAX_CHARS", _DEFAULT_SEMANTIC_MAX_CHARS, 1200, 60000
        )
    else:
        max_chars = _int_env("REGENOLD_KG_MAX_CHARS", _DEFAULT_MAX_CHARS, 1200, 60000)
    parts, dropped = _budget_context_parts(parts, max_chars)

    if parts:
        try:
            from app.integrations.regenold.reasoning_trace import (  # noqa: PLC0415
                record_note,
            )
            note = f"kg_context sections={len(parts)} refs={len(refs or [])}"
            if dropped:
                note += f" dropped_over_budget={dropped}"
            record_note(note)
        except Exception:  # noqa: BLE001
            pass
    return parts
