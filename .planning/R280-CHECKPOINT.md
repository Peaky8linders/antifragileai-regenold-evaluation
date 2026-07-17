# R280 — Tunnel restore + R279 finalisation + fresh easy/hard evals + frontier head-to-head

**Session:** 2026-07-17. **Status:** live measurement COMPLETE; minimal-composer A/B IN FLIGHT.
Checkpoint written so nothing here has to be re-derived or re-run.

---

## 1. DONE — Cloudflare tunnel restored (production was serving zero Claude Max)

**Symptom:** `/healthz/llm` → `llm_ok:false`, `api_status_401`. R279 "attempted" fable-5 and fell
back to deterministic on EVERY request.

**Root cause:** a **Cloudflare Access application** on `wrapper.antifragile-ai.net`
(AUD `9bb8182c…`), scoped to that exact hostname (root/www return 403, no `Cf-Access-Domain`).
The tunnel was NEVER broken: `cloudflared` service Running, `config.yml` correct
(`wrapper.antifragile-ai.net → 127.0.0.1:8000`), local wrapper auth `valid:true`. Last known-good
`llm_ok=true` = 2026-06-01 (`~/.cloudflared/harden-run.log`) ⇒ Access was added after.

**Fix (operator):** CF Access **service token** added to `.env` + Railway, redeployed. This is the
R277 design and is BETTER than "as before" — Access stays up (the wrapper has no auth of its own:
`/v1/auth/status` reports `api_key_required:false`, so an open hostname = anyone can burn the Max
quota) AND the backend authenticates through it.

**Verified:** `llm_ok:true`, `detail:"ok"`, `cf_access:{client_id_set,client_secret_set,headers_attached}` all true.

**Credentials state (for the next session):**
* `~/.cloudflared/cert.pem` token = **tunnel-scoped only** → 403 on `/access/apps` +
  `/access/service_tokens`. Cannot manage Access. accountID `e8a9ecdf42f35f2424b182210f827f37`,
  zoneID `4342fa2b1098d9225c59e0f4f4adeafa`.
* `~/.cloudflared/railway-token.txt` = **EXPIRED** (`railway whoami` → Unauthorized under both
  `RAILWAY_TOKEN` and `RAILWAY_API_TOKEN`). Cannot set Railway vars from CLI.
* No admin on this shell (`net session` → no) → cannot restart the `cloudflared` / `regenold-wrapper`
  services.
* `~/.cloudflared/wrapper-api-key.txt` = a 2026-06-08 "wrapper lockdown key" that was **never
  activated** (wrapper still reports `api_key_required:false`). Alternative to Access if ever wanted.
* `.env` is gitignored (`.gitignore:7`) and untracked — CF secrets cannot leak. Verified.

## 2. DONE — R279 finalised (fable-5 LANDS, not just "attempts")

Live probes with `?include_reasoning=true`, all four complex shapes:

| probe | stage2_polish | model note |
|---|---|---|
| conflict (Art 43 vs 27) | True | `stage2_model=claude-fable-5 complex=True` |
| GPAI threshold + fine-tune | True | `stage2_model=claude-fable-5 complex=True` |
| role ambiguity | True | `stage2_model=claude-fable-5 complex=True` |
| multi-turn (hard) | True | `stage2_model=claude-fable-5 complex=True` |

**Standard (non-complex) tier = `claude-opus-4-8 complex=False`** (probed directly; `railway.toml`'s
`P2P_GRAPH_RAG_STAGE2_MODEL="claude-opus-4-8"` IS in effect. `/healthz/llm`'s `model:claude-sonnet-5`
is the *probe* model, not stage2 — do not misread it).

Prod commit `7fc8d045d8e4` = R279. Working tree clean, **0 commits ahead of origin** ⇒ nothing to
redeploy. **There is no Vercel in this repo** (no `vercel.json`/`.vercel`; Railway only via
`Procfile`+`railway.toml`; the Lexy UI is served by Railway at `/app`).

## 3. DONE — Fresh live easy/hard scorecard (132 rows, 0 errors)

Sidecar: `evals/bench/results/easyhard-r279-live.json`. Corpus = `evals/harness/probe_set`
(easy = single-turn n=95, hard = multi-turn n=37). Endpoint = live Railway prod.

| axis | easy (n=95) | hard (n=37) | official (easy) |
|---|---|---|---|
| Ref Correctness Loose | **85.8** | 78.8 | 85.2 |
| Ref Correctness Strict | **60.8** | 47.0 | 58.8 |
| Ref Conciseness | 43.7 | 28.0 | 79.3 |
| Regulatory Tone | 100.0 | 100.0 | 98.5 |
| Keyword recall (answer proxy) | 74.0 | 68.9 | (n/a) |
| Latency p50 | **38.5 s** | **58.4 s** | (Speed 75.1 / 61.7) |

**Ref axes are statistically UNCHANGED vs the official run** (85.8 vs 85.2; 60.8 vs 58.8) ⇒
**R279 did not move correctness.** Expected: it swapped the model on the complex tier only
(~20% of rows) and was A/B-validated as a *conciseness* win — and conciseness is the one axis we
already LEAD (96.0 vs frontier 89.1) ⇒ **zero headroom on a geometric mean**.

### THE defect, measured directly (strongest evidence to date)
| | micro-precision | micro-recall | pred:gold ratio |
|---|---|---|---|
| easy | **37.1%** | 82.7% | **2.23x** |
| hard | **28.6%** | 75.9% | **2.66x** |

Recall is fine; **precision is the defect**. Matches the official's implied 1.90x. RefS has the
HIGHEST marginal GM leverage (+0.163pp/pp).

Worst easy categories (refS): `omnibus` 27.5, `role_ambiguity` 39.7, `cross_framework` 43.3,
`minimal` 45.5, `high_risk` 47.5. Perfect (100): `near_oos`, `prohibited_disjunction`,
`control_prohibited`.
*Note:* `omnibus` rows may be **out of competition scope** — the benchmark pins "state of affairs as
per May 1st 2026" and the Digital Omnibus agreement is 7 May 2026. Do not optimise for them.

## 4. DONE — Frontier head-to-head (the ONLY valid frontier comparison)

64 paired easy rows, same questions, same scorer. A = our RAG (live prod). B = raw `claude-fable-5`,
**no retrieval, no search**. Salvaged sidecar: `evals/bench/results/easyhard-frontier-fable5-salvaged.json`.

| axis | ours | frontier | delta |
|---|---|---|---|
| Ref Correctness Loose | **87.5** | 83.3 | **+4.2** |
| Ref Correctness Strict | **55.1** | 46.8 | **+8.3** |
| **Keyword recall (answer)** | 78.6 | **88.6** | **−10.0** |
| Latency p50 | 39.7 s | 36.9 s | +2.8 s |

Per-row — Ref Strict: **ours 35 / frontier 25 / tie 4**. Keyword recall: **ours 4 / frontier 27 / tie 33**.

**This independently reproduces the official decomposition on fresh data: our retrieval BEATS a
frontier model; our answer layer LOSES to it.** The baseline is *handicapped* (no web search, unlike
regenold's) and still out-answers us ⇒ the finding is stronger, not weaker.

## 5. PROVEN — local Ans metrics are NOT regenold's (do not re-derive)

* `metrics.py:157` loose = `overlap/union` (Jaccard); `:174` strict = `overlap/|gold|` (recall).
  `union >= |gold|` ⇒ **loose <= strict is an IDENTITY**. Ours obey it (0.1404 <= 0.4037).
* Official shows **AnsL > AnsS in 6/6 rows** ⇒ their pair is **not** (Jaccard, recall). QED.
* **`metrics.py:145` is FALSE** ("the competition rubric pins Loose=Jaccard and Strict=Recall").
  **No official formula is disclosed for ANY of the 8 axes.** Rules define Ans correctness as
  "question-specific ground-truth correctness criteria" = a per-question JUDGE.
* Ref axes = PARTIALLY comparable (pass the ordinal test) BUT `article_heads` (`metrics.py:107-127`)
  **collapses sub-points** ⇒ the local Ref scorer is **BLIND** to granularity → never gate R276-D1 on it.
* The `P = f1·R/(2R−f1) = 44.9%` algebra is a **category error** as comparability evidence (it inverts
  OFFICIAL numbers; our scorer never enters) and is non-monotonic vs official RefCon. Survives only
  as an estimate of *regenold's* precision.

## 6. DONE (NEGATIVE RESULT) — R277 arm C minimal composer does NOT ship

**It was already A/B'd earlier today** — `evals/bench/results/ab-judge-r277c-minimal-composer-51row-v2.json`
(n=51, judge claude-sonnet-4-6, arms `REGENOLD_MINIMAL_COMPOSER` 0 vs 1). **CHECK THE RESULTS DIR
BEFORE RUNNING AN A/B** — I nearly burned 90 min duplicating it.

Calibrated against the null-arm noise floor `ab-judge-r276-d2-NULLARM-noise-floor.json` (n=37, an
inert flag A/B'd against itself ⇒ every lean is pure noise):

| axis | NULL ARM (noise) | R277c minimal composer |
|---|---|---|
| correctness | wr 0.29, 30/37 ties, p=0.453 | wr 0.80, **46/51 ties**, p=0.375 |
| refs | wr 0.56, p=0.804 | wr 0.60, p=0.754 |
| conciseness | wr 0.48, 6/37 ties, p=1.000 | wr 0.56, 19/51 ties, p=0.597 |
| tone | wr 0.55, p=1.000 | wr 0.64, p=0.549 |

**VERDICT: NOT distinguishable from noise.** Noise alone yields win-rates 0.29-0.56; arm C's leans
(0.56-0.80) sit inside that band, and its correctness is **90% ties — it changes correctness LESS
often than noise does**. Fails R277's gate (needs p<0.05; got 0.375). All 4 axes lean branch with
**zero regressions**, so it is SAFE — but it is not a correctness fix.

**The real finding:** you can cut `ANSWER_GENERATE_SYSTEM` **51K → 3.2K chars (−94%)** with **no
measurable quality change**. That is a latency/cost lever (prompt tokens are paid on EVERY Stage-2
call, N+1x under fusion), NOT the answer-correctness fix R277 bet on. **R277's core hypothesis —
that prompt accretion causes the AnsL gap — is NOT supported by this lever.** Arms B/D test other
cuts, but the 90%-tie rate suggests the composer prompt is not the binding constraint at all.

**Methodology note for future rounds:** ALWAYS read the null-arm noise floor before believing a
"leans (ns)" verdict. Conciseness verdicts are especially high-variance (null arm: only 6/37 ties,
wr 0.48) — a conciseness "win" near 0.56 is indistinguishable from chance.

## 6b. SHIPPED — R280 revert: complex tier fable-5 → Opus 4.8 (`154f0be`, live)

Operator directive: *"fable 5 is not worth the extra costs and latency"*. Verified live on the fresh
deploy (`commit 154f0beaaa1d`): all 4 complex shapes → `stage2_model=claude-opus-4-8 complex=True`.
Gates: davidath QA byte-identical; 276-runner 100%; OOS 21/21; 50 unit tests.
Rollback: `P2P_GRAPH_RAG_COMPLEX_MODEL=claude-fable-5`.

### ⚠ HONEST CORRECTION — the latency half of the rationale is FALSIFIED
Post-revert probe, SAME 4 questions, SAME wrapper: **Opus 4.8 is 36% SLOWER than fable-5.**

| probe | fable-5 | opus-4.8 | delta |
|---|---|---|---|
| conflict | 18.7s | 28.6s | +9.9 |
| gpai | 28.9s | 43.3s | +14.4 |
| role_ambiguity | 51.1s | 53.6s | +2.5 |
| multi_turn | 33.8s | 54.4s | +20.6 |
| **mean** | **33.1s** | **45.0s** | **+11.9 (+36%)** |

4/4 consistent (n=1 each ⇒ noisy, but the direction is unambiguous). **My earlier "18.7-51.1s vs
12.8-17.7s" figure compared the COMPLEX TIER (fable + 4000 extended thinking) against the STANDARD
TIER (opus, NO thinking) — a TIER comparison misread as a model indictment.** The complex tier's
latency is the **`complex_thinking_tokens=4000` budget**, which Opus pays too. Cost is also not a
differentiator: both bill flat-rate through the Claude Max wrapper.

⇒ **The revert stands on the HEADROOM argument + the operator directive, NOT on latency or cost.**
⇒ **The real latency levers are `complex_thinking_tokens` and the complex gate itself** (which routes
on SENTENCE COUNT, not difficulty). A stored memory claims thinking budget is a latency wash
("~99% wrapper floor") — the measured floor is ~9s vs 38-45s rows (~24%), so **that memory is suspect
at the current config and must be re-measured.** Script ready: `scratchpad/thinking_latency.py`.
**Methodology lesson: hold everything else fixed — a config difference smuggled into a "model" A/B
fabricates a conclusion.**

## 7. NEXT (ranked, evidence-backed)

0. **Only the operator-directed revert shipped.** Arm C is noise (§6); no other change cleared a
   gate. Shipping anything else would violate CLAUDE.md hard rule #6. This is a MEASUREMENT round,
   and the measurement says the two cheap levers are exhausted.
1. **Ref precision is now the best-evidenced target** (2.23x/2.66x over-citation, precision 37%/29%,
   RefS has the highest GM leverage +0.163pp/pp). NOT a positional clamp (R142.1 lost 11-0,
   p=0.001). Must be prose-driven/structural and never drop a gold ref; gate on ab_judge **against
   the null-arm floor**.
2. **Answer composition is confirmed as the bottleneck but its cause is NOT prompt accretion**
   (§6 refutes that). The head-to-head (§4) shows a search-less frontier model out-answers us by
   10pp kw while we out-reference it by 8.3pp ⇒ the deficit is in what we DO with retrieved law.
   Candidates not yet tested: the 28 curated intercepts that bypass the LLM entirely
   (`REGENOLD_CURATED_STAGE2_SKIP=0` arm — never measured), and the consistency guard's
   whole-answer replacement.
3. **Latency** — 38.5s easy / 58.4s hard p50. Standard tier (opus-4-8, no extended thinking) runs
   12.8-17.7s; complex tier (fable-5 + 4000 thinking) ran 18.7-51.1s. A stored memory claims thinking
   budget is a latency wash ("~99% wrapper floor") — the measured floor is ~9s (`/healthz/llm`
   elapsed_ms 9033), i.e. only ~24% of a 38.5s row, so **that memory is suspect at the current config
   and must be re-measured**. Script ready:
   `scratchpad/thinking_latency.py` (sweeps 4000/1024/0 against the local wrapper).

## 8. Harness lessons from this session (fixed / to fix)

* **Runners MUST checkpoint per row.** `run_frontier_baseline.py` was killed at 65/95 and wrote its
  sidecar only at the end → all 65 rows lost from JSON (recovered only by parsing stdout via
  `scratchpad/salvage_frontier.py`). Incremental write added.
* Never run two wrapper-bound jobs concurrently — everything funnels to ONE local Claude Max
  (prod path hairpins Railway→CF→tunnel→this laptop). Contention corrupts latency on both.
* `grep -c ERROR` exits 1 on zero matches → a background waiter using it reports "failed" on success.
