# R341 — A/B of multi-query expansion (RAG-Fusion) on the deterministic parse

**Date** 2026-08-15 · **Harness** `evals.harness.dynamic_ab` (live, Stage-2 on) ·
**Lever** `REGENOLD_QUERY_EXPANSION` (baseline = shipped default OFF, branch =
ON) · **Wiring** `app/engines/query_expansion.py` (paraphrase + RRF) →
`app/engines/_graph_rag_impl.py` (`_deterministic_parse`) · **Artifact**
`evals/bench/results/dynamic-ab-r341-query-expansion.json`

## What changed

The end-to-end review's headline retrieval finding: the curated
`_KEYWORD_ENTITY_MAP` is a literal substring scan, so a question phrased
informally ("what must companies that put AI on the market do?") misses it
while its formal paraphrase ("what obligations apply to providers of
high-risk AI systems?") hits — and live retrieval is effectively ~99% pure
BM25, which cannot bridge paraphrase either. The `query_expansion` module
(Haiku 4.5 paraphrases + canonical Cormack-2009 RRF) already existed but was
unwired. R341 wires it into `_deterministic_parse` at ONE gate:

1. **Paraphrase keyword-map union (common path)**. When the gate is ON, the
   wrapper is alive, the question carries NO explicit Art./Annex anchor and
   the turn is not the flattened multi-turn shape, ask Haiku 4.5 for 2-3
   paraphrases and run the SAME high-precision keyword map over each. New
   refs are appended AFTER the original question's anchors, **capped at 3**
   (map order) — a recall supplement, never a displacement. Measured with a
   mock provider: uncapped, one paraphrase repeated several map phrases and
   inflated 8 → 22 entities.
2. **RRF-combined BM25 fallback (zero-anchor path)**. When the original
   lanes found nothing, the fallback runs per query (scoped → full-corpus)
   and `reciprocal_rank_fusion` combines the lists. The combined list is
   capped at the budget a single query gets (max list length, itself ≤ k),
   so RRF re-ranks WHICH refs win — it never inflates the entity count.
3. **The fallback still runs when a lone union hit leads.** Without this, one
   high-precision paraphrase hit suppressed the entire BM25 lane (measured
   starvation bug: 8 refs → 1). The fallback gate asks about the ORIGINAL
   lanes only (`len(entities) - _expansion_added == 0`); gate-off that
   degenerates to `not entities` exactly — byte-identical.

Gate OFF (default): `_expansion_added == 0`, no provider call, no RRF —
byte-identical parse BY CONSTRUCTION (the R72/R100/R109 gating discipline).

## Why this placement

* The pool-level rerank (R340) fires only on the no-entity fallback; on the
  common path the keyword map extracts an entity for nearly every question,
  so the parse-level placement is where expansion actually reaches live
  traffic. 122 of the 137 harness benchmark rows are non-anchored, so the
  lever fires on ~89% of an A/B run rather than being INERT on anchored
  rows.
* It is a *recall* lever, deliberately orthogonal to the R340 *ranking*
  lever: expansion repairs WHICH provisions are candidates; the reranker
  reorders them. Both are default-OFF and independently A/B-able.

## Safety properties (pinned by `tests/test_r341_query_expansion.py`)

1. **Additive-only**: paraphrase refs append after the original anchors,
   capped at 3; the RRF list is capped at the single-query budget. The
   original question's anchors always lead.
2. **Fail-soft**: wrapper dead, provider error, unparseable response, empty
   paraphrase set — all return `[original]` and the parse is unchanged
   (asserted byte-identical against the baseline).
3. **Inert-lever guard**: the tests assert
   `query_expansion_stats()["attempts"] > 0` on the gate-ON path (through a
   fake provider), the anchor/multi-turn gates issue zero calls, and the
   cache key moves when the flag flips (the R334 fire check + drift guard
   both pass).
4. **No double LLM round-trip**: one Haiku call per request, only for
   expandable questions (non-anchored, non-multi-turn), bounded at a 2 s
   timeout.
5. **Cache hygiene**: `REGENOLD_QUERY_EXPANSION` is folded into
   `_engine_cache_key` (R263.2) so an in-process two-arm A/B cannot serve
   arm A's cached engine result to arm B.
6. **Data-protection note (unchanged from R340)**: gate ON sends the partner
   question to the paraphrase provider (the Claude-Max wrapper / Haiku). The
   default-OFF posture is a deliberate residency decision; flip ON only on a
   deploy path whose provider is EU-resident.

## How to run the A/B

    py -3.12 -m evals.harness.dynamic_ab --flag REGENOLD_QUERY_EXPANSION \
        --label r341-query-expansion --max-rows 60

The harness aborts with verdict INERT if the arms do not diverge. Additionally
assert, before believing any axis table:

    py -3.12 -c "from app.engines.query_expansion import query_expansion_stats; print(query_expansion_stats())"
    # attempts must be > 0 on the ON arm (a number read off an unproven
    # placement measures nothing — R331 doctrine).

**Decisions:**

* **REJECT if** `gold_dropped > 0` at either grain (hard rule #8 veto) — an
  expanded candidate that pushes a gold ref out of the top-k cut is a loss
  even if every axis improves.
* **REJECT if** the reference-precision axis does not improve: the lever's
  thesis is that paraphrase recall lifts the right refs into the candidate
  set. A Recall-only gain with a precision drop means the added entities are
  noise (the 8 → 22 inflation class) and the cap should be tightened, not
  shipped.
* **Watch Speed**: one Haiku call per non-anchored request (~300-800 ms
  under the 2 s budget) lands on the simple-majority p50. If Speed drops
  more than the Recall gain is worth, pair this lever with
  `REGENOLD_STAGE2_SIMPLE_SKIP=1` and re-measure.
* **Rollback:** unset `REGENOLD_QUERY_EXPANSION` (default OFF); no code
  revert needed, no cache-key change.

## Honest limits

* **Unmeasured on this corpus so far.** The paraphrase quality is
  provider-dependent (Haiku 4.5 via the wrapper); the A/B is the first
  measurement.
* **Mock-provider tests pin the MACHINERY, not the quality.** The tests
  prove the lever fires, stays bounded and fail-softs; whether real
  paraphrases add recall or noise on the 276-scenario surface is exactly
  what the A/B answers.
* **Union cap is a fixed 3.** If the A/B shows the cap is either too tight
  (recall still missing) or too loose (precision drop), promote it to an env
  knob (`REGENOLD_QUERY_EXPANSION_CAP`) and sweep it like the R288.1 budget
  sweeps.
* **RRF k=60 is the canonical Cormack value**, untuned on this corpus; the
  A/B can decide whether a sweep is worth it.
