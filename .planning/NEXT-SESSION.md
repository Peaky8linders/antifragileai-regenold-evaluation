# Next session — handoff after R353

**State:** main clean at `0a747f2` (+ merge of #42). Full suite: 6574 passed / 0 failed.
Bedrock daily quota is the binding constraint — check `Sonnet`/`Opus` with a spaced probe before any live run.

## PR ledger (latest first)

| PR | what | status |
|---|---|---|
| #42 | **R353 — Annex III anchor** for the yes/no "is X high-risk?" shape (`REGENOLD_RISK_CLASS_ANNEX`, default OFF). Exact gold impact 7/0 over 297 rows (100% precision). Review report: `docs/R353-reranker-review.md` | MERGED |
| #41 | handoff doc | merged |
| #40 | R350/R350.2 full checkpoint (1.28 MB, all live answers + judge remarks) | merged |
| #38 | R351 anchor-tier stabilization | merged |

## The R353 lever — one measurement open

**What it is:** on yes/no "is [ordinary software] high-risk / regulated under
the AI Act?" questions, `_deterministic_parse` appends `Annex III` (the
high-risk use-case list) to the entity list. R352 refuted the broad
risk-classification triad (Art. 6 0% / Annex III 24% / Annex I 11% precise);
this is the surviving narrow shape, computed exactly over the whole pool
before any engine code (`scratch/verify_r352_final.py`): 11 fired rows, 7
gold gains, 0 non-gold.

**Verified so far (zero quota):**
- parse appends Annex III on all 7 gain shapes (tests pin this);
- `_retrieve_from_kb` produces a `kb-risk_mgmt-Annex III` obligation in the
  branch arm, absent in baseline (engine-level half of the wire chain);
- smoke A/B (6 clean rows, no throttle): lever fired 4/6, gold 1.0→1.0, no veto.

**NOT yet measured (needs quota):** the wire half — does Stage-2 prose
mention Annex III so Component D promotes it to the wire refs on the 7 gain
rows? And all judge axes (ans_corr / ref_corr / cite_faith / ans_conc) +
gold veto at full n.

**Relaunch (when a quota window opens — Sonnet tier, within-model):**
```
PYTHONPATH=. py -3.12 scratch/run_ab_r353.py --label r353-annex \
    --branch-env REGENOLD_RISK_CLASS_ANNEX=1 --max-rows 133 --batch 8 \
    --min-call-gap 8 --probe-sources lower_risk_v149,graphrag,live_answers
```
Watch the log for `regenold_stage2_fallback_served` — a throttled run serves
deterministic answers that look healthy on the wire (`err: None`), so kill it
and keep only the rows before the first fallback warning. The 8s pacing on
Sonnet exhausted the daily quota at ~n=16-40; a fresh day should clear 133.

## The veto fork — still undecided (open item #1)

`REGENOLD_RERANK_KG_NONCITABLE` — R351 (default, anchor-tiering) vs R350
(projection). Every combination that INCLUDES KG-candidates has vetoed gold
(R350 25→27, R350.2 46→49); expansion alone measured positive (17→14). The
decisive isolation runs (expansion-only; rerank×expansion, no KG) have never
been run on the live-answers probe. **The R353 review's finding #1:** the
R350.2 blame of the KG pool is correlation (3 levers changed at once), not
measurement.

## Review findings from R353 (docs/R353-reranker-review.md)

1. R350.2 veto attribution = correlation (3-lever arm, one-lever blame).
2. Wire refs are answer-driven (`engine refs ∩ prose`) ∪ Component-D prose
   refs — cut-level guarantees (R351) cannot close generation-level vetoes;
   judge retrieval levers at the WIRE (gold_dropped + judge axes), never the
   entity list.
3. `article_heads()` doesn't normalize short-form `Art.` — ad-hoc analyses
   comparing parse entities vs gold inflate "missing"; a `parse_entity_heads`
   helper would remove the trap.
4. Cohere rerank is POINTWISE — the R351 KG lever ADDS candidates, it cannot
   reorder anchors; flag-table language should say "addition".
5. Up to 5 serial Cohere calls per request when both gates on — needs a
   request-scoped call budget.

## Bedrock recipe

- `.env` lives in the MAIN project folder; `scratch/live_ab_env.py` loads it
  and forces `P2P_GRAPH_RAG_PROVIDER=bedrock`, embedded graph, no external
  embeddings. Override the model envs to the tier with quota.
- Throttle is a **per-model rotating daily window** — when Opus 429s, Sonnet
  may be healthy and vice versa. Probe with 12s spacing before launching.
- A throttled Stage-2 falls back to the deterministic answer with `err: None`
  — the fire check passes on garbage. Grep the run log for
  `regenold_stage2_fallback_served` and cut the run there.

## Do-not-re-propose (keeps growing)

- Anchoring the risk-classification triad (Art. 6 + Annex III + Annex I) —
  R352: 12% precise, Art. 6 exactly 0% (gold cites the list, never the rule).
- R329's first three rerank placements (inert); R142.1's final-ref clamp
  (lost the pairwise judge 11-0); REGENOLD_REF_PARTITION; REGENOLD_COMPLETENESS_VERIFIER;
  REGENOLD_PARENT_COLLAPSE un-gated; the five over-citation trimmer families.
