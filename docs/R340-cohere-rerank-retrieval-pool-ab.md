# R340 — A/B of the Cohere cross-encoder rerank on the RETRIEVAL candidate pool

**Date** 2026-08-15 · **Harness** `evals.harness.dynamic_ab` (live, Stage-2 on) ·
**Lever** `REGENOLD_COHERE_RERANK` (+ `COHERE_API_KEY`; baseline = shipped
default OFF, branch = ON) · **Wiring** `app/data/kb_search.py`
(`_maybe_rerank_fused`, `_RERANK_POOL_SIZE = 50`, all three
`top_articles_by_relevance*` variants) **+ the parse-level entity rerank in
`app/engines/_graph_rag_impl.py` (`_deterministic_parse`)** · **Artifact**
`evals/bench/results/dynamic-ab-r340-rerank-pool.json`

## Two placements, one gate (R340.1)

The gate controls TWO rerank points under the same one-call-per-request
invariant:

1. **Pool rerank (retrieval)**: `top_articles_by_relevance*` gathers the
   fused pool up to `_RERANK_POOL_SIZE` (50) and reranks before the top-k
   cut.
2. **Parse-level rerank (common path)**: `_deterministic_parse` reranks the
   FINAL assembled entity list before it is handed to retrieval. This is the
   placement that actually fires on the LIVE path — the keyword map extracts
   an entity for nearly every question, so `top_articles_by_relevance*` only
   runs on the rare no-entity fallback. Entity ORDER is load-bearing
   downstream (obligations are built in entity order; the 15-slot citation
   cap is drawn from that order), so reranking here decides which provisions
   survive the cap. When the entities came from the BM25 fallback (whose
   scoped search already reranked its pool), the parse-level rerank SKIPS —
   one Cohere call per request, never two (pinned by test).

Both are default OFF, byte-identical when off (the pool path via
`_pool_k == k`, the parse path by not entering the block).

## What changed

The Cohere cross-encoder (`rerank-v3.5` by default, model knob
`REGENOLD_COHERE_RERANK_MODEL`) is now wired into the retrieval candidate
pool, NOT the reference list and NOT the KG-context render:

* `top_articles_by_relevance` gathers the BM25+dense fused pool up to
  `_RERANK_POOL_SIZE` (50) candidates when the gate is on — instead of
  cutting at `k` immediately — reranks that pool against the question via
  :func:`app.engines.cohere_rerank.rerank_references`, then applies the
  top-k reference cut to the RERANKED order.
* The chapter- and section-scoped variants (`top_articles_by_relevance_in_chapters` /
  `_in_sections`) apply the same rerank to their scoped pools.
* Gate OFF (default): `_pool_k == k`, every internal slice/fill/budget is
  unchanged, and `_maybe_rerank_fused` returns `fused[:k]` — byte-identical
  davidath path BY CONSTRUCTION (the R72/R100/R109 gating discipline).

## Why this placement, when R329/R331 tried and measured

* R329's first three placements were **inert** — zero HTTP calls, +0.0000 on
  every axis. Two sat behind gates that never opened; the third reordered a
  list already within budget. The R329 module documents the tell:
  `rerank_stats()["attempts"] == 0` is indistinguishable from "the lever does
  nothing".
* R331's surviving placement reorders the **non-citable KG-context** ref list
  inside the Stage-2 prompt render (Answer Correctness only, never the wire
  references). Its own note says reordering the EMITTED references was
  measured negative (-0.019) in the sibling repo — that measurement was
  against the *final* 3-5 ref list, where a permutation has nowhere to go.
* R340 reranks **before the cut** with a 50-candidate pool. That is the
  ranking problem R329's scorecard identified (precision 0.653 vs recall
  0.879 — ~1.1 wrong refs inside an otherwise-right set, which no count clamp
  can fix because "a cut cannot know which of three refs is wrong"). Reranking
  the pool first means a mid-pool provision CAN move across the cut.

## Safety properties (pinned by `tests/test_r340_cohere_rerank_retrieval_pool.py`)

1. **Permutation-only**: `rerank_references` never adds, drops or rewrites a
   candidate (the R142.1 hard rule). The top-k cut is applied to a permutation
   of the pool, so the wire set is always a subset of the pool.
2. **Fail-soft**: any failure — network, timeout, malformed response, missing
   key, missing provision text — returns the input order unchanged. A rerank
   outage can never alter retrieval.
3. **Inert-lever guard**: the tests assert `rerank_stats()["attempts"] > 0`
   on the gate-ON path (end-to-end through a fake HTTP client), the gate-OFF
   path issues zero calls, and the scoped chapter variant fires too. The
   parse-level tests additionally assert the common path fires EXACTLY once
   (reversed API relevance moves `Art. 5` ahead of `Art. 43`), the BM25
   fallback makes exactly one call total (no double round-trip), and a
   rerank outage leaves the parsed entity order untouched.
4. **Cache hygiene**: `REGENOLD_COHERE_RERANK` and
   `REGENOLD_COHERE_RERANK_MODEL` are already folded into `_engine_cache_key`,
   and `rerank_enabled()` reads env fresh per call (R263.2) — an in-process
   two-arm A/B cannot serve arm A's cached engine result to arm B.
5. **Data-protection note (unchanged from R329)**: gate ON sends the partner
   question + verbatim provision text to Cohere. Default OFF is a deliberate
   residency decision; the Bedrock `amazon.rerank-v1:0` path remains the
   preferred EU-resident destination (see `cohere_rerank.py` docstring).

## How to run the A/B

    py -3.12 -m evals.harness.dynamic_ab --flag REGENOLD_COHERE_RERANK \
        --label r340-rerank-pool --max-rows 60

The harness asserts the arms actually diverge and **aborts with verdict INERT**
if the ON arm issued no rerank calls (its fire check). Additionally assert,
before believing any axis table:

    py -3.12 -c "from app.engines.cohere_rerank import rerank_stats; print(rerank_stats())"
    # attempts must be > 0 on the ON arm (a number read off an unproven
    # placement measures nothing — R331 doctrine).

**Decisions:**

* **REJECT if** `gold_dropped > 0` at either grain (hard rule #8 veto) — a
  rerank that pushes a gold ref out of the top-k cut is a loss even if every
  axis improves.
* **REJECT if** the reference-precision axis does not improve or worsens:
  this lever's entire thesis is that precision 0.653 → higher. An Answer-only
  gain without a refs gain means the reorder is cosmetic.
* **Rollback:** unset `REGENOLD_COHERE_RERANK` (default OFF) or delete the
  `COHERE_API_KEY`; no code revert needed, no cache-key change.

## Honest limits

* **Unmeasured on this corpus so far.** R325 measured a *lexical* reranker at
  AUC 0.703 (below the engine's own rank); a cross-encoder is a genuinely
  different arm and this A/B is its first measurement.
* **Latency:** one bounded HTTP call per request when ON (~300-700 ms for 50
  docs) on the live path — Speed is a scored axis; the A/B must report the
  latency delta, not just quality axes.
* **The scoped variants rerank a BM25-only pool** (they never run the dense
  layers today); the dense layers enter the pool only in the full-corpus
  variant. If the A/B shows the scoped path under-fires, extend the dense
  fills to those variants as a follow-up round.
* **Which placement is moving the axes**: on the live corpus, most questions
  carry explicit article anchors, so the parse-level rerank (placement 2)
  dominates and the pool rerank (placement 1) only sees the no-entity
  fallback questions. Read the per-grain tables with that split in mind; if
  a rejection is close, re-run with the pool placement toggled independently
  (a follow-up lever knob) to attribute the delta before shipping.
