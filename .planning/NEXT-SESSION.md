# Next session — handoff

## R378 — what the R377 review left OWED (2026-08-24)

Record: [`docs/reviews/r377-pr82-deep-review-2026-08-24.md`](../docs/reviews/r377-pr82-deep-review-2026-08-24.md).
Ordered by what each unblocks. **(0) is a prerequisite for all of them.**

0. **PERSIST THE DENOISER TRACE.** `record_query_denoiser` writes `fired` /
   `fallback_reason` / `provider` / `model` only into the per-request
   `ReasoningTrace`, which is never serialised. Three audits independently
   grepped every JSON artefact in the repo — **137 sidecars under
   `evals/bench/results/`** — for `fallback_reason` and got **zero hits**. So NO
   denoiser question is answerable today at any n: not the fire rate, not the
   truncation rate, not the provider mix. Emit it into the run sidecar alongside
   `stage2_models` / `stage2_landed`, which already prove the pattern.
   Non-behavioural, ungated.
1. **THE BEDROCK-LINK TRUNCATION RATE** — decides whether
   `REGENOLD_DENOISER_TRUNCATION_VOCAB` matters at all. Bedrock is candidate 2,
   so force it: unset `GROQ_API_KEY`, set an AWS credential, run
   `evals.regenold.runner`, and count rows whose served Bedrock response carried
   `stopReason=max_tokens`. **0 ⇒ the flag is latent and owes only its test;
   non-zero ⇒ (2) is mandatory.** Mind the ABSK 30-day expiry before blaming a
   403 on entitlement.
2. **THE A/B FOR THE VOCABULARY FIX**, if (1) is non-zero. Reference-affecting:
   with fall-through ON, a caught truncation routes to salvage → concatenation.
   `gold_dropped` on both grains is the veto (hard rule #8).
   ⚠ **Choose the pool by MEASURED fire rate.** `probe_set` is 297 rows of which
   only **37** are multi-turn (`mt_v2` 25, `paper_mt_v4` 12); everything else
   records `single_turn` and the denoiser never fires. A default run reports a
   meaningless NULL — the inert-A/B trap arriving through the probe pool.
   ```
   py -3.12 -m evals.harness.dynamic_ab --branch-env REGENOLD_DENOISER_TRUNCATION_VOCAB=1 \
     --probe-sources mt_v2,paper_mt_v4 --label r378-vocab --judge-model claude-sonnet-4-6
   ```
3. **THE `REGENOLD_DENOISER_BEDROCK` VERDICT R377 ITSELF SAID IT OWED.**
   Disclosed and measured at merge: `=0` → runner OVERALL 251/255,
   `refs_within_max` **231/255**; `=1` → 250/255, **196/255**. That is 35 rows on
   the one axis the official scorecard says we lead. Same pool caveat as (2).
4. **THE GUARD ITSELF** — the question R91 never answered. Low priority; nobody
   is proposing to delete it. ⚠ `REGENOLD_DENOISER_TRUNCATION_FALLTHROUGH=0`
   measures TERMINALITY, not the guard, so it is the wrong lever.

### Referred out — a defect in R127 itself, currently unfiled

`is_intent_enabled()` (`app/llm/intent_classifier.py:770-787`) reads
`if not (is_groq_intent_provider_enabled() or is_openai_wrapper_enabled())`.
R127-E's docstring claims it disables Stage-0 intent classification under `cli`;
it closed **one operand of two**, so with `GROQ_API_KEY` set intent
classification still fires a live call under `cli` — then and now. The honest
statement of the contract: **`P2P_GRAPH_RAG_PROVIDER=cli` is a PROVIDER SELECTOR,
not an LLM kill-switch**, and only two surfaces in the app enforce it. If that
contract should be real, the fix is a central chokepoint, not another per-call-site
guard — a design decision to be measured before it is built, not a review finding.

### Closed by R378 — do not re-open

* "R377 broke the `cli` deterministic contract" — **REFUTED by execution**
  against `58c9831` (the commit that ADDED R127's guard): the denoiser called
  Groq under `cli` 25 days before the guard existed, and R377 cut unguarded
  candidates 3 → 2. Residue was documentation only, and is fixed.
* Three new denoiser flags "missing from `_engine_cache_key` poisons the A/B" —
  refuted on mechanism (the key hashes the QUESTION, and the denoiser's output
  IS the question). The flags were registered anyway, and the dead
  `REGENOLD_DENOISER_MODEL` deregistered.
* "The empty-chain exit should route through the R131 salvage" — **wrong**, and
  three tests say so: `tests/test_r131_denoise_salvage.py` pins
  *"cli / no-provider (the davidath bench): the salvage must NOT fire so the
  multi-turn flatten stays byte-identical."*

---

# Earlier handoff (2026-08-16, after R354 Fix A)

## Where we are

**R354 deep-dive committed** (`docs/R354-veto-rows-deep-dive.md`): the six
live-answers veto rows (la_q87/20/51/73/84/52) are THREE distinct mechanisms,
not one bug:

1. **la_q73 — a real pipeline bug (fixed, R354 Fix A #48):** the R138
   final citation-consistency pass was Stage-2-gated, so a Stage-2-failed
   row shipped raw retrieval candidates even when the answer prose named a
   gold ref the wire lacked. la_q73's branch answer names "Annex I" TWICE,
   wire shipped `[Article 43, Article 6, Article 27, Article 49]` (Article
   43 never named in the prose, Annex I missing).
2. **la_q20 — a gold-coverage gap:** the branch is legally MORE correct
   (Article 74(12) genuinely requires market-surveillance remote access);
   the graded gold `[16, 26]` penalizes it. Gold edit, NOT a code edit.
3. **la_q87 / la_q51 / la_q84 / la_q52 — generation/topic drift from the
   KG-pool lever:** the candidate pool changes what Stage-2 writes; the wire
   follows the prose. The decisive isolation A/B (rerank × expansion with
   `REGENOLD_RERANK_KG_CANDIDATES` OFF) is still unrun.

**R354 Fix A shipped (#48, merged):** `REGENOLD_DETERMINISTIC_PROSE_CONSISTENCY`
(default OFF) extends the R138 add-pass to the deterministic path. Measured
BEFORE code on the 81-row checkpoint: **11 rows, 11 gold heads restorable**
(la_q73 fully closed, la_q51 4→3, la_q84 9→8). 7 tests, 6591 suite green.
Route-level (NOT in `_engine_cache_key` — the R79 doctrine), fresh read per
call.

## Running now

```
scratch/run_ab_r354.py   (PID was 509736)
label r354-fix-a, 81 rows (live_answers), batch=8 (checkpoint every 8),
min-rows=48, gen sonnet-4-6, judge opus-4-6 (both healthy),
REGENOLD_STAGE2_HARD_FAIL=1 (throttle errors the row, never silent fallback)
```

Check: `evals/bench/results/dynamic-ab-r354-fix-a.json` (every ~8 rows) and
`scratch/r354-fix-a.log`. Kill at the first `regenold_stage2_fallback_served`
or `api_throttled_429` — a throttled Stage-2 must NOT serve the judge.

## The decision this A/B resolves

Gate: gold_dropped is a veto (hard rule #8). If the branch does NOT drop gold
and the judge axes are positive/neutral → flip `REGENOLD_DETERMINISTIC_PROSE_CONSISTENCY`
default to ON in `app/routes/regenold.py` + CLAUDE.md. If it drops gold →
keep OFF and revisit.

**Caveat:** the flag only fires on rows where Stage-2 does NOT land. In this
A/B, gen tier is healthy sonnet-4-6, so most rows WILL land Stage-2 → the
deterministic arm may barely fire → expect mostly-identical arms (that is
still a valid null, but the la_q73 class only shows when Stage-2 fails).
If the arm is too quiet, the honest measurement is the replay harness with
`REGENOLD_STAGE2_HARD_FAIL=1` forcing the deterministic path.

## Next highest-value items (ranked)

1. **The decisive KG-off isolation A/B** (R354 Fix C): rerun the 81-row
   live-answers probe with `REGENOLD_COHERE_RERANK=1
   REGENOLD_QUERY_EXPANSION=1` and `REGENOLD_RERANK_KG_CANDIDATES=0`
   (or unset). Expansion alone had the only positive live evidence (R346:
   gold 17→14). If the veto clears without the KG pool, the pool gets the
   R352 deletion treatment (flag + branch + tests).
2. **Judge the 81-row live-answers checkpoint** (`scratch/judge_live_answers.py`
   — uses Opus 4.6 now, resume-aware, one arm at a time). The previous
   attempt was 503-contaminated (13 clean base rows only).
3. **Annotate la_q20's gold** in `evals/regenold/scenarios_live_answers.py`
   as a known coverage gap (Article 74(12) is the correct provision) so the
   veto book stops penalizing the legally-correct answer.

## Bedrock recipe

- `.env` in the MAIN project folder (`D:/Claude Projects/antifragileai-regenold-evaluation/.env`);
  this worktree's scratch loads it via `scratch/live_ab_env.py`.
- Tiers (2026-08-16): 4.6 both healthy. 5-series + 4.7/4.8 = 403-denied.
- 503s are AWS-side outages (transient); probe with 2s spacing before a run.
- Per-model daily quota: Opus 4.6 exhausts before Sonnet 4.6; the A/B is
  within-model per arm so deltas stay unbiased even when the tier degrades.
