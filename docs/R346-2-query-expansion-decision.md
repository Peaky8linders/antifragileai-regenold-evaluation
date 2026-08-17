# R346.2 — Query-Expansion A/B: decision (Bedrock-only, recital-aware judge)

**Decision: `REGENOLD_QUERY_EXPANSION` stays default OFF.** The A/B does not support
flipping it ON. Deltas are inside the null band on every axis; the gold-drop count
moves against the branch.

## Method

- **Harness:** `evals/harness/dynamic_ab.py` (live path, in-process engine, fire
  check, adaptive stop, checkpoint-per-batch).
- **Judge:** the R351/R360 legal_v2 axes (answer correctness, ref precision,
  conciseness, keyword recall) on **claude-sonnet-4-6 via AWS Bedrock** — the
  recital-aware judge, never the Cloudflare tunnel.
- **Arms:** baseline (flag OFF) vs branch (`REGENOLD_QUERY_EXPANSION=1`), 60 paired
  rows stratified across graphrag / medtech / expert_review / live_answers.
- **Engine:** `P2P_GRAPH_RAG_PROVIDER=bedrock` (Opus 4.6 Stage-2), embedded graph,
  external embeddings OFF.
- **Completed:** 60/60 pairs, all judge axes scored, **0 errored rows**.
  Checkpoints: `evals/bench/results/dynamic-ab-r346-2-expansion.{ckpt-intermediate-12rows,
  ckpt-intermediate-24rows, ckpt-intermediate-36rows, ckpt-intermediate-48rows,
  FINAL-60rows}.json`.

## Results (official `_analyse`, null band ±0.01)

| axis       | baseline | branch  | delta     | CI            | verdict       |
|------------|----------|---------|-----------|---------------|---------------|
| ref_loose  | 0.8847   | 0.8778  | −0.0069   | −0.029…+0.011 | UNDERPOWERED  |
| ref_strict | 0.7830   | 0.7830  | +0.0000   | −0.031…+0.032 | UNDERPOWERED  |
| ref_conc   | 0.6733   | 0.6785  | +0.0052   | −0.040…+0.056 | UNDERPOWERED  |
| kw_recall  | 0.7293   | 0.7307  | +0.0014   | −0.026…+0.029 | UNDERPOWERED  |

**Gold drops:** baseline 20 head-ref drops vs branch **23** (delta +3, i.e. the
branch *loses* gold head refs the baseline keeps). Rows where the branch dropped a
gold head ref the baseline kept: `live_answers:la_q73` (IVDR annex question — the
branch surfaced Annex VI/VII and lost Annex I) and `live_answers:la_q84`
(high-risk obligations — the branch kept fewer of the gold's 8 head refs).

## Why this is a NO

1. **Direction is not reliably positive.** R346's earlier n=60 (pre-recital judge)
   showed +0.039 ref_loose / −3 gold drops; this re-run with the improved judge on
   the same 60-row pool shows −0.007 ref_loose / **+3 gold drops**. The sign flipped
   once the judge could see recital and full-ref grounding — the earlier "win" was
   partly a judge blind spot.
2. **The failure mode is concrete and recurring.** The expansion misfires on
   annex-heavy questions (`la_q73`: Annex VI/VII for a question whose gold is
   Annex I). That is the exact class of question the engine must not degrade on.
3. **No axis clears the null band.** Flipping a default on a null result would be
   cargo-culting the earlier positive run.

## Also fixed (tunnel hygiene)

The first full run leaked Cloudflare-tunnel calls despite `P2P_GRAPH_RAG_PROVIDER=
bedrock`: `is_openai_wrapper_enabled()` is True for every provider except the
literal string `cli`, so wrapper-gated sub-pipelines (intent-classifier fallback,
ambiguous-OOS gate) bound to `OPENAI_API_BASE` — which `.env` sets to the tunnel
URL. The launcher now dead-ends it:

- `OPENAI_API_BASE=http://127.0.0.1:1/v1` (connection refused in ms, never the
  tunnel)
- `REGENOLD_INTENT_PROVIDER=groq` (Groq key is in `.env`; intent never falls
  through to the wrapper)
- `REGENOLD_BEDROCK_WRAPPER_FALLBACK=0` (unchanged)

The run that produced the FINAL-60rows checkpoint completed under the pre-fix
launcher; the branch's small gold-drop penalty is a retrieval effect of the
expansion feature, not of the tunnel leak (both arms ran the same sub-pipeline
transport).

## R364.1 — the annex mis-expansion fix (re-run)

The failure the first run exposed (la_q73: Annex VI/VII invention displacing
Annex I) is now fixed in ``app/engines/query_expansion.py``:

- **Deterministic reference-grounding guard** — a paraphrase is kept only if
  every Article/Annex it cites appears in the question OR in the
  caller-supplied seed refs (the engine's keyword-map entities, passed via
  the new ``seed_refs`` parameter). Phantom annexes are dropped and counted
  in a new ``ref_filtered`` stat. Prompt-level rule added as a soft layer.
- **Grounded**: Annex VII is the AI Act's notified-body conformity procedure
  (ontology ``HIGH_RISK_ANNEX_I``), so Annex VI/VII are *plausible but wrong*
  for the MDR-route question — exactly the class the guard kills.

**Re-run (same 60-row pool, same seed, same Bedrock judge):**

| axis | PRE-FIX delta | GUARDED delta |
|---|---|---|
| ref_loose   | −0.007 | −0.008 |
| ref_strict  | +0.000 | −0.001 |
| ref_conc    | +0.005 | **+0.025** |
| kw_recall   | +0.001 | **+0.004** |
| gold_dropped_head | **+3** | **+1** |

The guard removed the la_q73 failure (branch keeps Annex I; Annex VI/VII
never surface) and improved ref_conc 5x. All axes remain UNDERPOWERED
(deltas inside the ±0.01 null band), so the decision is UNCHANGED:
**REGENOLD_QUERY_EXPANSION stays default OFF.** The guard is a correctness
fix (the feature no longer *loses* gold refs it used to lose), not a win
that justifies enabling the feature. Checkpoints:
``dynamic-ab-r346-2-expansion-guard.{ckpt-24,ckpt-48,FINAL-60rows}.json``.

## R364.2/R364.3 — LLM-judge answer-quality measurements (Bedrock, slim axes)

The retrieval axes above are deterministic. The answer-level judge axes were
NOT run on these checkpoints before, so two lean Bedrock judge runs filled the
gap (ref correctness + conciseness stay deterministic; the judge only measured
what deterministic metrics cannot).

**R364.2 — slim 3-axis judge, union of rows where the arms differ (25 rows):**

| run    | ans_corr  | cite_faith | ans_rel |
|--------|-----------|------------|---------|
| PRE-FIX  | +0.200 (2→7/25) | −0.040 (17→16/25) | −0.040 (25→24/25) |
| GUARDED  | −0.042 (5→4/24) | −0.040 (17→16/25) | +0.000 (25→25/25) |

All verdicts UNDERPOWERED. The +0.200 on the changed rows is real in
direction but not resolved: base 0.08→0.28 at n=25 puts the bootstrap CI
roughly in [−0.01, +0.41], straddling the null band.

**R364.3 — decisive full-pool answer_correctness (1 axis, all 60 rows):**

| run    | base    | branch  | delta   | CI               | pairs |
|--------|---------|---------|---------|------------------|-------|
| PRE-FIX  | 0.293   | 0.397   | **+0.103** | [0.000, 0.207]   | 58    |
| GUARDED  | 0.316   | 0.333   | **+0.018** | [−0.053, 0.088]  | 57    |

**Reading:** the unconstrained expansion's answer-correctness advantage is
reproduced at full pool (+0.103, CI just touching 0) — the earlier +0.200 was
not a fluke. But on the CURRENT code (guard active) the advantage collapses to
+0.018, CI crossing zero. The guard removed the phantom-annex ref failure and
halved the gold-drop penalty, but it also removed most of the answer-quality
signal — either by constraining the paraphrase, or because the live Stage-2
answers/judge add run-to-run noise (baseline itself bounced 0.293↔0.316). The
two deltas are within ~1 SE of each other, so at this n the guarded branch is
statistically indistinguishable from baseline on EVERY axis.

**Decision is UNCHANGED: `REGENOLD_QUERY_EXPANSION` stays default OFF.** The
guarded branch's best case is ref_conc +0.025 / kw_recall +0.004 / gold-drop
+1 (all underpowered) against ref_loose −0.008 and a null answer-quality
delta. Flipping a default on that would be the bias the A/B exists to prevent.
The +0.103 pre-fix signal is the motivation for ONE more targeted experiment —
a narrower guard that only strips invented *annex* numbers (the la_q73 class)
while leaving the rest of the paraphrase free — not for an enablement flip.
Results: `evals/bench/results/r364-2-slim-judge.json`,
`evals/bench/results/r364-3-anscorr-fullpool.json`.

## R364.4 — weighted composite (final decision basis)

Every axis is individually UNDERPOWERED, so a single metric cannot carry the
decision. The weighted composite pulls all measured metrics together (per-arm
means from the checkpoints + LLM-judge results from
r364-2-slim-judge.json / r364-3-anscorr-fullpool.json), across four
weight schemes so no arbitrary weighting drives the call:

| scheme      | weights (ans\_corr, cite\_faith, ref\_loose, ref\_strict, ref\_conc, kw\_recall) | PRE\_FIX Δ | GUARDED Δ |
|-------------|-------------------------------------------------------------------------------|---------------|---------------|
| primary     | .30 .15 .25 .10 .10 .10                                                       | +0.0240       | −0.0001       |
| equal5      | .20 .00 .20 .20 .20 .20                                                       | +0.0206       | +0.0074       |
| ref\_heavy   | .20 .10 .30 .15 .15 .10                                                       | +0.0155       | +0.0010       |
| trust\_heavy | .35 .20 .20 .05 .10 .10                                                       | +0.0275       | −0.0007       |

Gold-drop veto (branch vs baseline head-ref drops): PRE\_FIX +0.050, GUARDED +0.017.

**Reading.** The unconstrained expansion was net-positive on the composite
(+0.016…+0.028) but carried a real gold-drop veto (+0.050). The guard halved the
veto (+0.017) but the composite collapsed to null (−0.0007…+0.0074) — the
annex-guard traded away the answer-quality upside it was meant to protect. For
the SHIPPED config every scheme lands inside (or below) the ±0.01 null band, and
the veto is still positive.

**FINAL DECISION: the REGENOLD_QUERY_EXPANSION flag stays default OFF.** The weighted
composite confirms the per-axis read: the guarded branch is statistically
indistinguishable from baseline on every metric, with a residual gold-drop
penalty. The composite script is scratch/r364n_weighted_decision.py.

## If we revisit

Enablement is still not the lever. With the invention bug fixed, expansion
is now recall-neutral-to-positive but adds an LLM round-trip and latency
per request for no measurable gain — the remaining question is a cost/benefit
one, not a correctness one.



Enablement is not the lever — the annex mis-expansion is. A targeted fix would
constrain the expansion prompt to never introduce annex numbers that are not in the
question or the seed refs (the la_q73 failure introduced Annex VI/VII from nowhere),
then re-A/B. That is a separate change to `app/engines/query_expansion.py`, gated
behind the same flag, and does not require flipping the default.
