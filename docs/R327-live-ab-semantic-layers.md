# R327 — live A/B of the 7-index semantic layers (50 July-7 questions)

**Date:** 2026-08-10
**Path:** local code under test → live Neo4j Aura `0644b854` → Claude Max via the
Cloudflare tunnel `wrapper.antifragile-ai.net` (CF Access service token).
**Sample:** the first 50 of the 110 official July-7 questions, `--mode easy`.
**Arms:** `REGENOLD_GRAPH_SEMANTIC_LAYERS` OFF vs ON, both with
`REGENOLD_KG_MAX_CHARS=REGENOLD_KG_SEMANTIC_MAX_CHARS=26000` so the only
difference is the presence of the three semantic blocks.

Sidecars: `evals/bench/results/official-r327-live-ab-A-easy.ckpt.jsonl` (OFF),
`official-r327-live-layersON-easy.ckpt.jsonl` (ON).

## The first attempt was INERT — and byte-identical output is what that looks like

The first paired run returned **byte-identical answers and byte-identical
reference lists on all 50 rows**. That reads as "safe". It was not a result at
all: the branch arm averaged **1,096 ms** against baseline's **16,642 ms**, i.e.
every row was an `_ENGINE_CACHE` hit and Stage-2 never re-ran.

`REGENOLD_GRAPH_SEMANTIC_LAYERS` was missing from `_engine_cache_key`. So was
R326's `REGENOLD_GRAPH_VECTOR_RECALL` — meaning any in-process A/B of vector
recall also measured nothing. Both are now keyed.

**The latency comparison is the cheap detector.** A branch arm an order of
magnitude faster than baseline did not run the engine.

## The valid run

| | OFF | ON |
| --- | --- | --- |
| non-200 / empty answers | 0 / 0 | 0 / 0 |
| answer chars (mean / median) | 999 / 944 | 1002 / 926 |
| refs per row (mean / median) | 2.62 / 2.5 | 2.64 / 2.0 |
| total refs over 50 rows | 131 | 132 |
| latency ms (mean / median) | 16,642 / 17,049 | 16,786 / 14,983 |
| Stage-2 polish fired | 31 / 50 | 31 / 50 |

**The feature fires:** 31 of 50 answers and 14 of 50 reference lists changed, at
matched latency. Stage-2 ran on the same 31 rows in both arms (the other 19 take
the `stage2_skipped_curated_authoritative` path, where the curated KB answer is
authoritative and no LLM polish happens — so the layers cannot affect them).

Cost is negligible: +144 ms mean (+0.9%), and the two extra bounded graph reads
run inside the existing timeout budget.

## Agreement with the recorded July-7 references (head level)

| | precision | recall | F1 | tp / fp / fn |
| --- | --- | --- | --- | --- |
| OFF | 0.869 | 0.785 | **0.825** | 106 / 16 / 29 |
| ON | 0.837 | 0.763 | **0.798** | 103 / 20 / 32 |

⚠ **This is a similarity measure, not a quality measure.** `jul07_refs` are the
July-7 *system's own predictions*, not gold — that run scored answer correctness
**0.500**. The official batch carries no gold answer and no gold refs at all. So a
drop in agreement with July-7 is not evidence of a regression, and a rise would
not have been evidence of a win.

What it does establish: the layers are **not** a free win on reference precision.
On the only cheap proxy available they are directionally slightly negative
(−0.027 F1, 4 fewer true positives, 4 more false positives).

## Verdict

`REGENOLD_GRAPH_SEMANTIC_LAYERS` stays **default OFF**. It is live, cheap,
answer-affecting, and structurally safe (the sub-provision layers are constrained
to already-cited provisions, so they cannot introduce a citation; definitions and
recitals can never be a wire citation). But "answer-affecting and unmeasured" is
exactly what the validation policy requires a gate for, and the proxy available
here leans mildly against it.

To actually gate it, in priority order:

1. `evals.judge.grounded` over both sidecars — the axes that matter
   (answer correctness, citation faithfulness, reference precision) rather than
   agreement with a superseded run. Note `GROUNDED_JUDGE_STRICT_GROUNDING` must
   stay OFF for this batch or answer-correctness is unscorable (no gold).
2. `evals.harness.easyhard_ab` — it is the only harness that scores reference
   conciseness as a count-ratio against gold that carries sub-point grain.
3. Repeat at full n. CLAUDE.md records that small-n live A/Bs cannot resolve the
   reference axes: two runs with an *identical* baseline arm changed 20/40 rows'
   refs and sign-flipped all three reference axes.

## Sample rows where the layers changed the references

```
rg_007  biometric verification
  OFF ['Article 6', 'Article 50', 'Annex III', 'Annex I']
  ON  ['Article 5', 'Article 6', 'Article 50', 'Annex III', 'Annex I']

rg_017  How does Annex II relate to prohibited uses?
  OFF ['Annex II', 'Article 5']
  ON  ['Annex II', 'Article 5', 'Article 27']

rg_020  remote access to documentation for market surveillance
  OFF ['Article 74', 'Article 16', 'Article 10']
  ON  ['Article 26', 'Article 16']
```

`rg_007` adding Article 5 to a biometric-verification question is plausibly
right (the prohibition boundary is the live issue). `rg_017` adding Article 27
(FRIA) to a question about Annex II is plausibly wrong. `rg_020` swapping
Article 74 for Article 26 loses the market-surveillance article. That spread —
one better, one worse, one mixed — is why this needs the grounded judge and not
a head-overlap count.
