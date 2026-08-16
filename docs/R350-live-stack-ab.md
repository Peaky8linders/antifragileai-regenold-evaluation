# R350 — the full optimised stack, measured live (and the R351 fix)

## What was measured

The FIRST live measurement of the full optimised stack — Cohere rerank ×
KG-candidate supplementation (R347/R348) × query expansion (R346) — as a
within-model A/B on **84 rows** drawn from the three-source pool:

* `graphrag` — GraphRAG paper benchmark, 40 rows (GROUND_TRUTH)
* `medtech` — fresh medical/healthcare/life-sciences benchmark, 24 rows
* `expert_review` — 20 questions from the Antifragile AI expert review, gold
  derived from the EU AI Act expert's critique

Branch env: `REGENOLD_COHERE_RERANK=1 REGENOLD_RERANK_KG_CANDIDATES=1
REGENOLD_QUERY_EXPANSION=1`. Generation tier: `claude-sonnet-4-6` via Bedrock
(Opus 4.6 daily quota was exhausted by the R346 A/Bs; within-model A/B keeps
the deltas unbiased). All 8 metrics per arm: the four retrieval axes + the
four `legal_v2` judge axes (`ans_corr` / `ref_corr` / `cite_faith` /
`ans_conc`), plus the hard-rule-#8 gold veto.

Checkpoint: `evals/bench/results/dynamic-ab-r350-full.json` (310 KB, per-row
answers/refs/latency for both arms; per-row judge verdicts in the
`-judge-base` / `-judge-branch` sidecars).

## Results — 84 rows, lever FIRED on 57/84

| axis | baseline | branch | delta | 95% CI | verdict |
|---|---|---|---|---|---|
| ref_loose | 0.8579 | 0.8478 | −0.0101 | [−0.038, +0.015] | UNDERPOWERED |
| ref_strict | 0.7407 | 0.7211 | −0.0196 | [−0.054, +0.013] | UNDERPOWERED |
| ref_conc | 0.6110 | 0.5968 | −0.0142 | [−0.080, +0.050] | UNDERPOWERED |
| kw_recall | 0.7586 | 0.7497 | −0.0089 | [−0.034, +0.017] | UNDERPOWERED |
| ans_corr | 0.3830 | 0.4043 | +0.0213 | [−0.064, +0.106] | UNDERPOWERED |
| ref_corr | 0.5918 | 0.5306 | −0.0612 | [−0.143, +0.020] | UNDERPOWERED |
| cite_faith | 0.6667 | 0.7292 | +0.0625 | [−0.063, +0.188] | UNDERPOWERED |
| ans_conc | 0.6667 | 0.5833 | −0.0833 | [−0.208, +0.021] | UNDERPOWERED |
| **gold_dropped_head** | **25** | **27** | **+2** | — | **🚫 HARD RULE #8 VETO** |

Judge axes: paired over the rows where BOTH arms scored cleanly (n_pairs
≈ 47-49 of 84; the branch judge pass was throttled by the account's daily
quota, so ~38 branch rows lack a clean verdict — errors are skipped, never
counted as passes). The retrieval axes and the gold veto are full-population.

## The finding: the veto was a KG-displacement bug, not a stack failure

All 5 gold-dropped rows share ONE mechanism — a KG-supplemented neighbour
out-scored a gold anchor and DISPLACED it from the citation cut:

| row | gold lost | displaced by |
|---|---|---|
| expert_review:xr_16 / graphrag:med_03 | Article 51 (GPAI systemic risk) | Annex XI (KG neighbour of Art. 53) |
| expert_review:xr_03 | Annex III (high-risk route) | Article 49.2 (KG neighbour of Art. 6) |
| medtech:grb_20 | Article 9 (risk management) | Annex V / Art. 25 / Art. 47 / Art. 71 |
| graphrag:ng_06 | Annex VI + Annex VII (conformity routes) | Article 17 / Art. 43.2 |

The R347 design promised "a permutation can reorder but never lose an
entity" — but that guarantee held only for the POOL. The citation budget cut
(`_effective_max_refs`) runs on the REORDERED entity list, so a neighbour
that scores above an anchor pushes the anchor out of the budget.

## R351 — the fix: `stabilize_anchor_tier`

`app/engines/cohere_rerank.py::stabilize_anchor_tier` restores the superset
guarantee AT THE CUT: after the rerank, every keyword anchor precedes every
KG-supplemented neighbour, with rerank order preserved WITHIN each tier. KG
supplementation becomes strictly ADDITIVE — it can only fill slots the
anchors did not take, never remove a gold anchor. Wired into the parse-level
rerank block in `_graph_rag_impl.py` (only when the pool was actually
expanded). 7 new tests pin the tier invariant, permutation safety, and the
parse-level wiring.

The reference-correctness direction (−0.061) and the gold veto are the SAME
signal at two resolutions — the wrong-ref displacement the fix removes.

## R350.2 — the live-answers probe (81 rows)

`evals/regenold/scenarios_live_answers.py` — 81 questions from the attached
"Regenold — Questions & Live Answers" file: question + live answer as
gold_answer + References as expected_refs (HEAD-projected per the R337
corpus invariant). Seven gold corrections applied where the file's own
references were provably wrong for the question (verified against the Act
text): Q5 (Art. 49 dropped), Q6 (Art. 108 cached mis-answer → scope refs),
Q11 (Art. 52 → Art. 10), Q27 (Art. 50.1 dropped), Q29 (Art. 46 dropped),
Q42 (irrelevant refs dropped → Art. 26), Q77 (Art. 3.25 → Art. 3). Q55/Q56
are out-of-scope probes (refusal gold) measuring the OOS guard. All 81
expected refs resolve in the provision text.

## R350.2 — the re-measurement on the live-answers probe: the veto persists

Re-ran the SAME full stack (rerank × KG-candidates × expansion, now WITH the
R351 anchor-tier fix) on the 81-row live-answers probe. Result at n=48 clean
rows (before the account's daily Bedrock quota closed the window):

**gold_dropped_head 46 → 49 (+3) — hard-rule-#8 veto again.**

Regressions (branch dropped more gold): la_q87 (+1), la_q20 (+2), la_q51
(+2), la_q73 (+1), la_q84 (+2). Improvements: la_q76, la_q18, la_q79, la_q37
(4 rows). The lever fired on 29/48 rows.

### The new mechanism: generation-level citation drift (R351 cannot fix it)

The R350 drops were KG neighbours displacing anchors AT THE CUT — R351 fixed
that. The R350.2 drops are different: the wire references are ANSWER-DRIVEN
(Component D extracts citations from the Stage-2 prose), and the KG pool
changes what Opus WRITES. Measured on la_q87: the branch answer said *"the
Union harmonisation legislation listed in notably the Medical Devices
Regulation"* instead of *"listed in Annex I"* — the literal ``Annex I`` never
reached the prose, so Component D never extracted it, so the gold reference
dropped. On la_q20 / la_q51 / la_q84 the branch's ENTIRE citation sets
shifted (la_q84: base cited {10, 13, 15, 16, 54, 9, 96}; branch cited {16,
17, 47, 49, 71, 80, 94}) — a wholesale generation-level rerouting, not a
single displacement. No anchor-tier protection at the parse can force an LLM
to write a phrase the context led it away from.

### The R346 decomposition still points at the culprit

R346 measured the levers SEPARATELY: rerank alone gold 17→17 (wash), query
expansion alone 17→14 (**better**, no veto). Every combination that INCLUDES
the KG-candidates arm has vetoed (R350 25→27, R350.2 46→49). Expansion is
the only arm with positive live evidence; the KG pool is the only arm that
has never shipped a clean live measurement.

### Decision

The full optimised stack (rerank × KG-candidates × expansion) does NOT clear
the hard-rule-#8 gate. The KG-candidates arm is the prime suspect and should
stay OFF (its default). The decisive isolation run — query-expansion ONLY
(no rerank, no KG) on the live-answers probe — is the next measurement, and
it is one command away when the account quota window reopens:

```
PYTHONPATH=. py -3.12 scratch/run_ab_r351.py --branch-env REGENOLD_QUERY_EXPANSION=1 \
    --label r350-live-expansion --max-rows 81 --batch 6 --min-call-gap 15 \
    --probe-sources live_answers --no-judge
```

Checkpoint of the clean 48 rows: `evals/bench/results/dynamic-ab-r350-live-answers.json`
(partial:true — the throttle stopped the run before row 81; rows after the
window closed are NOT in the checkpoint because the harness was killed before
the next batch checkpoint).
