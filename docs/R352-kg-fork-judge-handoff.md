# R352 — KG-citability fork: A/B captured, judge NOT yet run

**Status:** 100 rows captured both arms, 0 errors. Judge deferred to another
session. This page is everything needed to run it and decide.

---

## The decision

Two fixes for one defect (`entities = reranked` adopted the whole KG-expanded
pool, so a `CROSS_REFERENCES` neighbour became a wire citation). Both shipped;
a flag picks which runs. This A/B decides which one stays.

| arm | flag | behaviour |
| --- | --- | --- |
| **A — baseline (current default)** | `REGENOLD_RERANK_KG_NONCITABLE=0` | **R351 anchor-tiering.** Neighbours stay citable but every keyword anchor precedes every neighbour, so supplementation is strictly ADDITIVE — fills unused slots, never displaces a gold anchor. |
| **B — branch** | `REGENOLD_RERANK_KG_NONCITABLE=1` | **R350 projection.** Neighbours inform the cross-encoder ranking and never enter the citation set at all. |

Structurally `A = B + neighbours`: `stabilize_anchor_tier` returns
`anchored + supplements`, and `anchored` is character-identical to B's
projection. So the arms differ by exactly the neighbour set.

## What is already captured

`evals/bench/results/dynamic-ab-r352-kg-citability-full.json` (327 KB,
gitignored, on disk). Contains `baseline_rows` and `branch_rows` — full answer
text, emitted refs, gold refs, latency, per-row deterministic scores.

```
rows captured   100      (stratified across all 11 probe sources)
rows CHANGED     84      <- the only rows carrying information
rows identical   16      <- paired delta exactly 0 by construction
rows errored      0
fire check       FIRED   (refs changed 46+, answers changed 66+)
```

Run configuration (already applied, recorded here so a re-run matches):

```
P2P_GRAPH_RAG_PROVIDER=openai_wrapper
OPENAI_API_BASE=http://127.0.0.1:8000/v1     # LOCAL wrapper, not the tunnel
REGENOLD_GRAPH_BACKEND=embedded
REGENOLD_EXTERNAL_EMBEDDINGS=0
REGENOLD_COHERE_RERANK=1                     # SHARED by both arms
REGENOLD_RERANK_KG_CANDIDATES=1              # SHARED by both arms
--min-call-gap 10                            # Cohere key is TRIAL tier: 10/min
```

⚠ Both KG flags must be ON in BOTH arms or the pool never expands and the two
fixes are trivially identical.

## Running the judge

`scratch/judge_r352_ab.py` is ready. It reuses `dynamic_ab`'s own judge plumbing
(`_judge_caller` / `_judge_rows` / `_judge_axes`) — no reimplementation — and
judges only the 84 changed rows.

```bash
py -3.12 scratch/judge_r352_ab.py
```

Needs the local wrapper up on `127.0.0.1:8000`. Cost: **84 rows × 2 arms × 4
axes = 672 calls**, concurrency 4, roughly 45-70 min on the flat Max
subscription. It writes `ab_judged.json` with, per row: the question, gold refs,
both arms' refs and answers, and all four axis verdicts **including the judge's
own `failure_mode` text**.

To judge all 100 rows instead of the 84 changed ones, drop the `changed` filter
— it costs 128 extra calls to add 16 rows whose delta is provably 0.

## How to decide

**Gate — hard rule #8.** `gold_dropped` is a VETO, not an axis. Non-zero is a
rejection regardless of every other number. Read it from the deterministic
sidecar; it does not need the judge.

**Decision — the judge axes.** R349 exists so no A/B is decided on retrieval
axes alone: those measure what was RETRIEVED, the Regenold rubric scores the
ANSWER. Rank by `ref_corr` and `ans_corr` first, then `cite_faith`, then
`ans_conc`.

**Reading the verdicts** (this harness carries the R350 fixes):
* `UNDERPOWERED` below 3 paired observations however narrow the CI — the floor
  is deliberate, do not override it.
* `n/-skip` is per axis. A judge axis routinely scores far fewer pairs than the
  header's n; the skipped count is transport/parse errors, which are excluded
  rather than scored as failures.
* `NO-DATA` means an axis had zero scorable pairs — it is printed rather than
  silently dropped.
* Deltas are over the **84 changed rows**. Multiply by `84/100 = 0.84` for the
  whole captured population.

**Then delete the losing arm.** Shipping both is a fork, not a feature. Remove
the flag, its `_engine_cache_key` entry, and the losing branch in
`_graph_rag_impl.py` (~:2715).

## What is already known without the judge

Computed exactly over the whole 297-row probe pool, no LLM (`scratch/r352_kg_oracle.py`):

```
KG neighbours proposed   1,502
   ...that are gold         18
   ...that are not       1,484
PRECISION                  1.2%
```

`Art. 98` — *Committee procedure*, comitology — is proposed **50 times**.

So arm A's supplement is 1.2% precise at the CANDIDATE level. But the
downstream 15-slot cap and `adaptive_ref_clamp` trim from the TAIL, which is
exactly where A parks the neighbours, so most never reach the wire — a 15-row
realized probe showed the two arms within ~2 refs of each other, inside Stage-2
noise. **That is why the judge is needed: the candidate-level argument
over-states A's cost, and the deterministic axes cannot see the answer-level
effect.**

## Related

* `docs/R352-annex-anchor-gap.md` — the retrieval gap this investigation found,
  and why the obvious fix is refuted (`Art. 6` measured 0% precise).
* `CLAUDE.md` flag table — `REGENOLD_RERANK_KG_NONCITABLE`.
* R353 (`REGENOLD_RISK_CLASS_ANNEX`) shipped the one surviving hypothesis at
  100% precision; its own live A/B is a separate open measurement.
