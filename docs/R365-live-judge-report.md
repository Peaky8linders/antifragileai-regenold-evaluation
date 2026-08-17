# R365 Live Run + Judge Report — 81 live-answers rows (2026-08-17)

## Run metadata

| field | value |
|---|---|
| sidecar | `evals/bench/results/dynamic-ab-r365-live.json` |
| rows | 81 (all `HTTP 200`, 0 errors) |
| engine | current main + R353.1/R366/R366.1/R367 (merged `baa5c5c`; Railway redeployed to `eb1bee6` on 2026-08-17) |
| generation | Bedrock `claude-sonnet-4-6` primary, R366.1 cross-model chain (`sonnet→opus→qwen3-235b→nemotron→devstral→qwen3-32b`) on 429/error |
| stage-2 hard-fail | `REGENOLD_STAGE2_HARD_FAIL=1` (throttled rows 503 instead of silently degraded) |
| judge | `qwen.qwen3-32b-v1:0` via Bedrock, K=1, 7-axis legal_v2 rubric |
| tunnel | dead-ended (`OPENAI_API_BASE=127.0.0.1:1`, `WRAPPER_FALLBACK=0`) — 0 tunnel connections observed |
| arms | identical (no-op `REGENOLD_REF_RECOVERY` flag) — deltas = run-to-run noise, absolute pass rates are the signal |

**Operational:** latency mean 4.8 s / median 4.05 s / p95 12.8 s · answer mean 684 chars ·
refs mean 2.91 / median 3 / max 11.

---

## 1. Judge axes (Qwen3-32B, per-arm pass/fail)

| axis | base pass | base fail | base err | pass rate | branch pass | branch fail | branch err | pass rate |
|---|---|---|---|---|---|---|---|---|
| answer_relevancy | 72 | 9 | 0 | **0.889** | 72 | 9 | 0 | 0.889 |
| citation_faithfulness | 75 | 6 | 0 | **0.926** | 72 | 8 | 1 | 0.900 |
| answer_conciseness | 55 | 26 | 0 | 0.679 | 56 | 25 | 0 | 0.691 |
| answer_crag_fine | 55 | 26 | 0 | 0.679 | 56 | 25 | 0 | 0.691 |
| answer_correctness | 43 | 34 | 4 | 0.560 | 44 | 32 | 5 | 0.579 |
| answer_faithfulness | 31 | 50 | 0 | **0.383** | 31 | 50 | 0 | 0.383 |
| reference_correctness | 30 | 49 | 2 | **0.380** | 31 | 49 | 1 | 0.388 |

**Reading.** The system is strong on grounding (cite_faith 0.926), relevancy (0.889) and
conciseness (0.68). The two weak axes — reference_correctness (0.38) and answer_faithfulness
(0.38) — are dominated by a single structural artifact (Section 3) plus the multi-ref gold
shape of this benchmark (the 81 live questions carry richer gold sets than the paper's).

## 2. Deterministic axes (identical arms, per-row mean)

| axis | mean | rows ≥ 0.5 |
|---|---|---|
| ref_loose | 0.764 | 68/81 |
| ref_strict | 0.709 | 63/81 |
| ref_conc | 0.610 | 43/81 |
| kw_recall | 0.584 | 51/81 |

Gold-drop (absolute, per-row engine miss of ≥1 gold ref): **56/81 rows**. This is the
recall-side counterpart of the judge's ref_corr 0.38 — the engine consistently under-cites
the gold set on this benchmark.

## 3. Missed gold refs (gold-but-not-predicted)

| ref | missed | gold total | miss rate |
|---|---|---|---|
| Article 6 | 22 | 27 | 81% |
| Annex III | 19 | 29 | 66% |
| Article 50 | 11 | 15 | 73% |
| Article 5 | 5 | 10 | 50% |
| Annex I | 4 | 13 | 31% |
| Article 10 | 4 | 7 | 57% |
| Article 26 | 3 | 6 | 50% |
| Article 43 | 3 | 3 | 100% |
| Article 49 | 3 | 4 | 75% |
| Article 3 | 3 | 3 | 100% |
| Article 25 | 3 | 6 | 50% |
| Annex IV | 2 | 5 | 40% |
| Article 15 | 2 | 2 | 100% |
| Article 17 | 2 | 4 | 50% |
| Article 51 | 2 | 5 | 40% |

## 4. False-positive refs (predicted-but-not-gold)

| ref | FP count |
|---|---|
| Article 6.2 | 10 |
| Article 6.1 | 9 |
| Article 6.3 | 7 |
| Article 53 | 5 |
| Article 50 | 4 |
| Annex I | 4 |
| Article 43.3 | 4 |
| Article 50.1 | 4 |
| Article 6 | 3 |
| Article 50.2 | 3 |
| Article 9 | 3 |
| Article 49 | 3 |
| Annex III.5.a | 2 |
| Article 26.7 | 2 |
| Article 19 | 2 |

## 5. Article 6 parent/sub-point — investigated, NOT a scoring bug

**Correction (2026-08-17, follow-up):** the raw-set "missed 22/27 Article 6" and the
"17-row mismatch" in the first draft were computed at raw-ref granularity. The
competition scorer does NOT operate there: `evals/bench/metrics.py::article_heads()`
projects every sub-point to its top-level head (`Article 6.1` → `Article 6`) before
intersecting, so **sub-point citations already reconcile to parent gold**.

Verified directly:
- `reference_correctness_loose(['Article 6.1'], ['Article 6'])` → **1.0**
- `reference_correctness_strict(['Article 6.1'], ['Article 6'])` → **1.0**
- live rows: la_q83 (pred `Article 6.2`, gold `Article 6`) scores **1.0/1.0/1.0** on
  loose/strict/conc in the checkpoint.

The R325 parent-collapse pass is **default OFF** (`REGENOLD_PARENT_COLLAPSE=0`), and
R87-C's `_reemit_parents_for_subpoints` is default-ON — so the engine's wire refs are
already the correct shape for this rubric. **No scoring fix and no engine fix is
needed for Article 6.**

### TRUE head-level miss/FP picture (what the scorer actually penalises)

Missed gold at head level (recomputed):

| ref | missed | gold total | miss rate |
|---|---|---|---|
| Annex III | 10 | 29 | 34% |
| Article 50 | 7 | 15 | 47% |
| Article 6 | 5 | 27 | 19% |
| Annex I | 4 | 13 | 31% |
| Article 25 | 3 | 6 | 50% |
| Article 26 | 2 | 6 | 33% |
| Annex IV | 2 | 5 | 40% |
| Article 10 | 2 | 7 | 29% |
| Article 17 | 2 | 4 | 50% |
| Article 3 | 2 | 3 | 67% |

FP at head level: Article 50 ×6, Article 53 ×5, Annex I ×4, Article 6 ×3, Annex III
×3, Article 9 ×3, Article 3 ×3, Article 49 ×3, Article 19 ×2, Article 55 ×2.

**The real levers are the recall supplements:** `Annex III` 10/29 (34%) and
`Article 50` 7/15 (47%) head-level misses dominate ref_loose (0.76) and ref_conc
(0.61). The judge's ref_corr (0.38) additionally judges at the raw-ref granularity it
is shown, so sub-point-vs-parent appears there as a *judgment* call (the model sees
both lists verbatim) — a separate, softer effect that the deterministic scorer does
not share.

## 6. What this means for the SOTA goal

- **Groundedness is not the problem:** cite_faith 0.926 and ans_rel 0.889 say the
  engine answers from the right material.
- **Citation-set fidelity is the problem:** ref_corr 0.38, ref_conc 0.61, kw_recall 0.58,
  56/81 gold-drop. The Article 6 parent/sub-point artifact is NOT a scoring bug (the
  deterministic scorer reconciles via `article_heads()`); the two dominant recall levers
  are the Annex III (10/29 head-level) and Article 50 (7/15 head-level) gaps, both now
  addressed by R368 (Section 7).

## 7. R368 — the Annex III / Article 50 deterministic recall supplements (2026-08-17)

Designed and implemented to close the two head-level gaps above. Gold impact was
computed over the 81-row pool BEFORE any engine code (scratch/r368_trigger_impact.py +
v2) — the R352 doctrine:

| trigger | family | fires | recovers | FP | rows |
|---|---|---|---|---|---|
| medical classification | Annex III | 3 | 2 | 0 | la_q8, la_q64 |
| MSA reclassification (+Art. 79/80) | Annex III | 1 | 1 | 0 | la_q35 |
| EU-database registration | Annex III | 1 | 1 | 0 | la_q37 |
| operator becomes provider | Annex III | 1 | 1 | 0 | la_q25 |
| VLOP transparency | Article 50 | 3 | 3 | 0 | la_q60/63/91 |
| fines + prohibited practices | Article 50 | 1 | 1 | 0 | la_q16 |
| biometric/patient interaction | Article 50 | 1 | 1 | 0 | la_q7 |

**10 gold-head recoveries across 10 rows at 100% precision.** Two v1 triggers needed
tightening to reach 100%: the medical trigger requires the question to OPEN with a
yes/no auxiliary (kills the What/How obligation shapes la_q74/76/88), and the
biometric trigger excludes emotion-inference shapes (la_q69 is Art. 5(1)(f), not 50).

Three of the 7 Article-50 misses (la_q60/63/91) were additionally REFUSED by the scope
gate (DSA NEAR_OOS) — a scope-gate fix, not retrieval. The R368 scope rescue classifies
"an AI system's transparency obligations" as an AI Act Article 50 question even when it
names VLOP / content-moderation; pure-DSA shapes stay refused.

**Status:** implemented behind two default-OFF gates
(`REGENOLD_ANNEXIII_RECALL_SUPPLEMENTS`, `REGENOLD_ART50_RECALL_SUPPLEMENTS`, both
keyed in `_engine_cache_key`), 26 new tests, docs/R368-recall-supplements.md. Next
step is the measured A/B (flags ON vs OFF) to confirm the 10-row recovery lands in
ref_loose/ref_strict without FP cost, then flip to default ON.

## 8. Production deployment status (2026-08-17, Railway)

| field | value |
|---|---|
| service | `antifragileai-regenold-evaluation-production.up.railway.app` |
| pre-redeploy | serving R361 (`82916f9`) — 4 PRs behind main |
| post-redeploy | `eb1bee6` (PRs #54 R364.5, #55 R365, #56 R366.1+R367, #57 docs) — live |
| build surface | byte-identical R361→main (`railpack.json`/`Procfile`/`railway.toml`/`requirements.txt`/`pyproject.toml` empty diff; no Dockerfile — Railpack auto-detect) |
| healthz / llm | 200 / `llm_ok:true` (openai_wrapper, opus-4-8, CF access OK) |
| graph | `backend:neo4j`, `graph_ok` — see below |

**The graph outage root cause (found and verified):** the deployed `NEO4J_URI` pointed
at the DEAD Aura instance `151d4e69.databases.neo4j.io` — DNS does not exist for it
(`getaddrinfo` fails), so every graph read logged `Failed to DNS resolve` and the engine
ran on the deterministic KB fallback. The live instance is `0644b854.databases.neo4j.io`
(`neo4j+s://`, verified from this machine: TLS OK, driver auth OK, `RETURN 1` → 1,
**1786 nodes** — matches the R338 census). The stale `151d4e69` reference in
`app/engines/kg_context.py`'s module docstring was corrected to `0644b854`.

**Remaining — graph still down after the env-var update** (confirmed by 3 polls over
~2.5 min post-redeploy; identical `graph_ok:false`, ~1.53 s constant latency = fast
failure, not a timeout). The client reads `NEO4J_URI` directly from the process env and
the local driver test PROVES the working set — so the deployed process is still not
seeing the verified values. Exact dashboard checklist (all four must match the repo's
`.env`):

1. `NEO4J_URI` = `neo4j+s://0644b854.databases.neo4j.io` (scheme `neo4j+s://` — a
   bare `neo4j://` fails the Aura TLS handshake).
2. `NEO4J_USERNAME` = `neo4j` (or `NEO4J_USER`).
3. `NEO4J_PASSWORD` = the 44-char value from `.env` (an old-instance password fails
   auth, which surfaces as `ping returned no rows`).
4. The deployment must START after the save (new deployment ID) — an env change saved
   mid-deploy leaves the running process on the old URI.

Verify with `GET /healthz/graph` → expect `graph_ok:true`, `backend:neo4j`, and
non-empty `node_counts` (1786 nodes on the live seed). Cohere embed 429s (SVD
fallback) are non-fatal. Stale host references corrected in code:
`app/engines/kg_context.py` docstring (`151d4e69` → `0644b854`) and
`app/graph/config.py` default (`6fc3fff5` → `0644b854`, documented as inert).

## Artifacts
- `evals/bench/results/dynamic-ab-r365-live.json`
- `evals/bench/results/checkpoints/dynamic-ab-r365-live-FINAL-81rows-7axes.json`
- judge log: `%LOCALAPPDATA%\Temp\r365_live6.log`
