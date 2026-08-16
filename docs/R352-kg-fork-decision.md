# R352 — KG-citability fork: DECIDED (R351 anchor-tiering survives)

**Verdict: the R350 projection arm (`REGENOLD_RERANK_KG_NONCITABLE=1`) is
rejected on hard rule #8 (gold_dropped is a veto). Flag, cache-key entry and
the projection branch are deleted. R351 anchor-tiering is the only path.**

## The two fixes

One defect: `entities = reranked` adopted the whole KG-expanded pool, so a
`CROSS_REFERENCES` neighbour (graph adjacency, 1.2% precise at the candidate
level) could become a wire citation. Two independent fixes shipped as flags:

| arm | behaviour |
| --- | --- |
| **A — R351 anchor-tiering (default, survivor)** | Neighbours stay citable, but every keyword anchor precedes every neighbour (`stabilize_anchor_tier`), so supplementation is strictly ADDITIVE — fills unused slots, never displaces a gold anchor. |
| **B — R350 projection (deleted)** | Neighbours inform the cross-encoder ranking and never enter the citation set at all. |

## The A/B (deterministic gate — no judge calls needed)

Sidecar: `evals/bench/results/dynamic-ab-r352-kg-citability-full.json`
(gitignored, on disk). 100 rows stratified across all 11 probe sources, both
arms, 0 errors, fire check FIRED (84 changed rows: 55 ref-different,
83 answer-different).

Computed from the sidecar with `evals.bench.metrics.gold_dropped_head` /
`gold_dropped_exact` (identical formulas the harness scores with):

```
                       A (anchor-tier)   B (projection)   delta (B - A)
gold_dropped_head                26                27              +1
gold_dropped_exact               89                91              +2
rows where A drops more           3                 —               —
rows where B drops more           4                 —               —
```

**Hard rule #8: non-zero gold_dropped is a VETO, not an axis.** The branch
nets +1 gold HEAD drop and +2 exact-coordinate drops against the baseline, so
the branch is rejected regardless of any other number. This is exactly what
the gate exists to catch — the candidate-level precision argument (1.2%)
understated A's cost, and the deterministic gate saw what the 15-slot cap
allowed through to the wire.

## The four regressed rows (head grain)

| row | gold | A cites | B cites | B loses |
| --- | --- | --- | --- | --- |
| `mt_v2:mt_v2_008` | Art 25, Art 51 | 25, 51.2, 53.2, 55 | 25.1 only | **Article 51 entirely** |
| `paper_st_v4:st_v4_017` | Art 5, Art 6 | 16, Annex III, 6 | 49, 25, Annex III | **Article 6** |
| `mt_v2:mt_v2_020` | Art 5, Art 113 | 113, 4, 5.1 | 50.4, 5 | **Article 113** |
| `live_answers:la_q13` | Annex XI, XII, 51, 53, 55 | 53, 55, 51, XI | 53, 51, 55 | **Annex XI AND XII** |

(The projection removes the neighbour supplements; on these rows the
neighbours happened to be carrying gold that the anchors did not re-cover —
a real, answer-visible regression.)

## What was deleted

- `app/engines/cohere_rerank.py` — `_RERANK_KG_NONCITABLE_ENV` +
  `rerank_kg_noncitable()` + the `__all__` entry.
- `app/engines/_graph_rag_impl.py` — the import and the
  `if rerank_kg_noncitable(): entities = [r for r in reranked if r in set(entities)]`
  projection branch; the comment now records the verdict.
- `app/routes/regenold.py` — the `REGENOLD_RERANK_KG_NONCITABLE` entry in
  `_engine_cache_key`.
- `tests/test_r350_review_fixes.py` — the projection-arm test and the
  two-arms-differ test (the tiering test remains, as the only path).
- `CLAUDE.md` — the flag-table row and open item #1 (now #1 DECIDED).

## Why no judge calls

The handoff's own decision rule: "`gold_dropped` is a VETO, not an axis.
Non-zero is a rejection regardless of every other number. Read it from the
deterministic sidecar; it does not need the judge." The judge axes
(ref_corr / ans_corr / cite_faith / ans_conc) decide only between arms that
both PASS the gate. B fails it deterministically, so 672 judge calls (the
handoff's estimate) were not spent. The candidate-level 1.2% precision note
stands as the WHY this fork existed; the veto is the WHAT settled it.

## Related

- `docs/R352-annex-anchor-gap.md` — the retrieval gap that started this line
  of investigation, and why the obvious fix (`Art. 6` always) is refuted.
- `docs/R352-kg-fork-judge-handoff.md` (main project folder) — the original
  handoff this decision resolves.
