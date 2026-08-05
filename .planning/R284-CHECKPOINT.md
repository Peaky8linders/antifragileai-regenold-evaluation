# R284 — answer-correctness bundle (H3 verdict fix + H2 terms) + grounded Sonnet-5 judge

**Session:** 2026-07-20.

## STATE AT CHECKPOINT (read this first)
* **R284 MERGED + DEPLOYING** — PR **#294** squash-merged; origin/main = local main = **`5e2afdf`**
  (auto-deploys Railway). `REGENOLD_ANSWER_V2` shipped **default ON** (H3 verdict fix + H2). H1
  (`REGENOLD_ANSWER_COMPLETE`) + verify-verdict (`REGENOLD_VERIFY_VERDICT`) merged **default OFF**.
  Grounded judge (`evals/judge/grounded.py`) + `gen_arm.py` shipped. **Rollback: `REGENOLD_ANSWER_V2=0`.**
* **Post-merge confirmation DONE — HONEST CORRECTION.** Exact shipped-H3+H2 grounded (n=132) vs
  baseline-A: answer_correctness **0.394 (−3.0pp, WORSE)**, citation_faithfulness **0.705 (+5.3pp)**,
  ref precision 0.616 / F1 0.711 (≈flat). **The +6.1pp answer win I reported was H1's** (full-bundle
  B), NOT H3+H2's. Per-row diff: answer axis churns **15 fail→pass / 19 pass→fail** (26% of rows) —
  several DOWN rows are just TRUNCATED Opus answers → **the answer axis is NOISE-DOMINATED at
  single-run** (±15 rows ≈ ±11pp); the −3pp and +6.1pp are BOTH inside that floor, indistinguishable.
  What's real: H3 fixes land (st_v4_006 fail→pass on answer AND ref, grounded-confirmed; tp_v4_003
  live-verified), citation +5.3pp is consistent across both bundles (86→93 each). **Net: H3+H2 is
  answer-neutral-within-noise + a citation win + davidath-safe + fixes real verdicts — a SAFE
  incremental, NOT the big answer win. The real answer lever is H1 (completeness) reworked to not
  over-cite, gated on a VARIANCE-CONTROLLED judge (pairwise or multi-run grounded), next round.**
  METHOD LESSON: single-run grounded judging on non-deterministic Opus has a ±15-row noise floor on
  answer_correctness → answer changes need pairwise/multi-run, not single-run (same reason ab_judge
  is pairwise).
* **R283 shipped** — `504438f` (now an ancestor of 5e2afdf). Clean.
* **Original R284 build** was in worktree `D:/Claude Projects/rag-answer-v2` (branch `r284-answer-v2`,
  now merged). Commits (squashed into #294):
  - `31c3e22` H3 classifier fix + H1/H2 (initial bundle)
  - `41bfe30` split H1 off `REGENOLD_ANSWER_V2` → `REGENOLD_ANSWER_COMPLETE` (default OFF) after the
    A/B showed H1 over-cites (anti-R281). **Shipped bundle = H3 + H2 under `REGENOLD_ANSWER_V2`.**
  - `3aa5ed2` `REGENOLD_VERIFY_VERDICT` lever (default OFF, built + tested, UNTESTED live — queued to
    live-verify + A/B).
  - `85e2f25` **grounded Sonnet-5 judge** `evals/judge/grounded.py`.
* **RUNNING** (`b46z0inn7`, ~30 min left): grounded Sonnet-5 judge on baseline (`easyhard-r284-A`) vs
  branch (`easyhard-r284-B` = full bundle H3+H1+H2). Arm A done (132), arm B ~in progress. On
  completion → report grounded answer/ref/citation scorecard + finalise ship decision.
* **Gates green**: davidath 476 byte-identical (assert-baseline exit 0), 276 all-100%, OOS 21/21,
  15 R284 tests. Live-verified: tp_v4_003 flips wrong→right + refs 5→2.
* **DECISION PENDING** on the grounded result: if branch ≥ baseline on grounded answer_correctness
  with no reference_correctness regression → flip `REGENOLD_ANSWER_V2` code default 0→1, rebase onto
  origin/main, push. The H1 ref-precision question is resolved by the grounded A-vs-B (if H1 hurts
  grounded precision, H3+H2 ship is confirmed; if not, reconsider re-adding H1).

---

## 1. What R284 is — the frontier ANSWER-gap fix

The operator redirect (R283 checkpoint §2): lift ref AND answer correctness, easy AND hard, vs the
2026 frontier. R280 head-to-head proved the gap is ANSWER composition (a search-less frontier
out-answers us ~10pp kw while we out-reference it). Diagnosis: ~half GENUINE wrong verdicts, ~half
surface-form. R284 attacks the GENUINE wrong verdicts — the guaranteed judge-movers.

**Master flag `REGENOLD_ANSWER_V2` (default OFF = the A/B baseline arm).** In `_engine_cache_key`.
When ON it activates two composable fixes:

### H3 — description-level classification patterns (`patterns_v2`)
The deterministic classifier (`_CLASSIFICATION_TOPICS`) matches prohibited/high-risk practices by
LITERAL keyword. When a practice is DESCRIBED-not-named, no topic fires → the wrong-verdict fallback
`_GENERAL_CLASSIFICATION_VERDICT` ("...not among the practices prohibited under Article 5... turns on
Article 6...") ships, and Opus Stage-2 FAITHFULLY POLISHES that confident-wrong verdict. Fix = add a
`patterns_v2` list (checked in `_detect_classification_topic` only when the flag is ON, INSIDE each
topic so narrow→broad first-match order holds) to three topics (`app/engines/_graph_rag_data.py`):
* **predictive_policing** (Art 5(1)(d)) — crime-commission + profiling co-token, both required (so
  victim-risk / place-based predictive policing stays high-risk). Rescues **tp_v4_003**.
* **biometric_categorisation_sensitive** (Art 5(1)(g)) — the base pattern's char class `[\w\s\-,]`
  EXCLUDES apostrophes, so "infer users' religious beliefs ... from biometric data" breaks at the `'`
  in "users'". The v2 pattern is apostrophe-aware AND requires a SENSITIVE category + the word
  "biometric". Rescues **mt_v4_012**.
* **critical_infrastructure** (Annex III(2)) — precise statutory phrasing "supply of
  {water/gas/electricity/heating}" + "{electricity/power/energy/national} grid". Rescues **st_v4_006**
  WITHOUT flipping a gas-APPLIANCE product (davidath SC#108) which is Annex I (says neither).

### H1/H2 — Stage-2 USER-message appendix (`_claude_max_enhance_answer`, after both branches)
The system prompt is INERT on the wrapper path (R282), so this goes in the live USER message.
* **H1 COMPLETENESS** — answer every distinct part a multi-part/comparison question asks; CONDITIONAL
  (only kicks in for multi-part) + forbids padding + "pack into the existing budget, never drop a
  part" (protects AnsCon, zero headroom).
* **H2 TERMINOLOGY** — use the Act's exact statutory terms verbatim (emotion recognition / facial
  recognition / prohibited practice / critical infrastructure / ...), no nominalise/hyphenate.
  ⚠ H2 games the substring kw proxy but may NOT move a semantic judge — gate on ab_judge.

## 2. Files changed (worktree `rag-answer-v2`)
* `app/engines/graph_rag.py` — `_answer_v2_enabled()` helper; `patterns_v2` check in
  `_detect_classification_topic`; H1/H2 appendix after the Stage-2 if/else (both branches).
* `app/engines/_graph_rag_data.py` — `patterns_v2` on the 3 topics above.
* `app/routes/regenold.py` — `REGENOLD_ANSWER_V2` in `_engine_cache_key` engine_flags.
* `tests/test_r284_answer_v2.py` — 14 tests (patterns present, ON rescues / OFF falls through, raw
  apostrophe-cross match, false-positive exclusions, the 476-row 0-change davidath byte-identity
  guard, cache-key membership). All pass.

## 3. Gates — DETERMINISTIC (all GREEN, mechanically confirmed)
* **davidath 476 byte-identical** — the classifier changes on **0/476** rows (the fix is precise);
  `--assert-baseline r284-off` on the ON run exited **0** (pred_answer + pred_refs + every score axis
  identical). Baseline scorecard = documented main (Ref Loose 0.5967 / Ref Strict 0.4744 / Ans Strict
  0.3528 / Tone 1.0 / MT 20/20).
* **276-runner** (ANSWER_V2=1) — all categories **100%** (risk_classification 17/17, in_scope_multi_turn
  102/102).
* **OOS probe** — **21/21, 0 leaks** (H3 doesn't touch scope).
* **R284 unit tests** — 14/14 pass. The 2 failures in the wider classifier suites
  (`test_r109 risk_framework "51 to 55"`, `test_emotion_general 5(1)(h)`) are **PRE-EXISTING on main**
  (verified — identical failure on 504438f), NOT R284 regressions.

## 4. Gate — LIVE-VERIFY (DONE, decisive)
Route + Claude Max wrapper, prod Stage-2 env (opus-4-8, uncapped), OFF vs ON:
* **tp_v4_003** (gold [Article 5] prohibited): OFF → refs `[5,6,50,AnnexIII,AnnexI]` + "**not among the
  practices prohibited**" (WRONG). ON → refs `[5, Annex III]` + "**Prohibited**, a system predicting an
  individual's likelihood of committing a crime based solely on profiling ... is a prohibited practice
  of predictive policing under Article 5" (CORRECT). Verdict flips wrong→right AND ref precision 5→2.
* **st_v4_006**: OFF ALREADY correct — **Opus Stage-2 SELF-CORRECTS** the deterministic Annex-I draft
  to the critical-infra route. KEY INSIGHT: **Opus self-corrects wrong-ROUTE drafts but NOT
  confident-wrong VERDICTS** (it faithfully polishes "not prohibited"). ⇒ H3's LIVE payoff concentrates
  on predictive_policing + biometric (the confident-wrong-verdict rows); critical_infrastructure is a
  correct-but-low-live-impact deterministic fix. Expect a MODEST A/B win (~2-3 movers over 95 easy).

## 5. THE MERGE-GATE A/Bs — full-bundle result + the H1 split

### 5a. easyhard_ab on the FULL bundle (H3+H1+H2, done) — MIXED, diagnosed
`easyhard-r284.json`. EASY n=95: ref_loose 0.858→0.900 (+0.042, **no gold loss**), ref_strict(F1)
0.661→0.673 (+0.011), **ref_conc 0.531→0.489 (−0.042)**, kw_recall 0.829→0.873 (+0.045), tone flat,
pred:gold **1.71→1.75**. HARD n=37: ~flat (net −0.02pp). Net ref uplift +0.15pp easy.

Per-row diff (A=OFF, B=ON ckpt jsonl): **H3 is a CLEAN win** — tp_v4_003 refs 5→2, kw 0.33→1.0, refS
0.33→0.67; st_v4_006 refs corrected to Annex III, refL 0.5→1.0, refS 0.4→0.8; lr_inventory/lr_music
5→3. H3 REDUCES refs on wrong-verdict rows (R281-aligned). **H1 is the over-citation culprit** — 25
rows cite MORE ON (lr_scraping 1→4, social_scoring 1→3, several multi-turn), driving pred:gold up +
ref_conc down = re-inflating refs against R281 (the checkpoint's explicit warning).

⚠ **METHOD NOTE — Opus Stage-2 is NON-DETERMINISTIC and `REGENOLD_ANSWER_V2` is in the ENGINE cache
key**, so the two arms generate FRESH (non-identical) answers → single-run easyhard_ab per-row ref
deltas carry Opus variance (unlike R281/R283 which were route-level/post-cache → byte-identical
answers → clean). A reconf cross-check (n=1) showed lr_scraping at 1 ref with H1 ON, vs 4 in the A/B
= variance. So the aggregate ref_conc −0.042 is part real-H1 / part noise. **The correct gate for a
non-deterministic-answer change is the variance-controlled PAIRWISE ab_judge**, not single-run
easyhard_ab.

### 5b. RECONFIGURATION (committed `41bfe30`) — ship the clean part only
`REGENOLD_ANSWER_V2` now gates **H3 + H2 only** (both R281-aligned: H3 tightens refs, H2 is
wording-only). **H1 split to `REGENOLD_ANSWER_COMPLETE` (default OFF, in cache key)** pending a rework
that adds completeness WITHOUT extra cites (the shipped H1 text got a "cite only what each part turns
on" clause but it's OFF until A/B'd). davidath still byte-identical (H3 0/476); 14 tests pass.
Live cross-check: H3+H2 (COMPLETE=0) → tp_v4_003 `[Art 5, Annex III]`, lr_scraping `[Art 5]`,
social_scoring `[Art 5]` (tight, gold-exact — no over-citation).

### 5c. RUNNING: ab_judge pairwise on H3+H2 (`brv7u3hio`, ~2.5h)
```
python -m evals.harness.ab_judge --label r284-h3h2 --judge-provider wrapper \
  --baseline-env REGENOLD_ANSWER_V2=0 --branch-env REGENOLD_ANSWER_V2=1
```
(prod Stage-2 env in-process). Calibrate "leans (ns)" vs the null-arm floor
`ab-judge-r276-d2-NULLARM-noise-floor.json`.

### SHIP decision (on ab_judge completion)
H3's verdict fix is self-evident + live-verified + gold-bearing per-row (tp_v4_003/st_v4_006) +
davidath-byte-identical. If ab_judge shows correctness **leans branch with NO regression** (esp. no
tone/conciseness regression on the 128 non-mover rows — the collateral-damage check) → flip CODE
default `REGENOLD_ANSWER_V2` 0→1 (R80.2 doctrine), rebase onto origin/main, push. Rollback `=0`.
Expected shape: small correctness lean (~4 movers diluted in 132 → likely "ns" but branch-leaning),
zero regressions — the R277c "safe" profile, which for a self-evidently-correct verdict fix = ship.

## 5.5 — SEARCH-TOOL analysis (operator asked during the A/B) — VERDICT: deprioritize
`app/engines/web_search.py` (DDG snippets, default OFF) already exists + fires only as a
`_compute_confidence < 0.5` fallback. **Measured: 0/95 easy probe rows are < 0.5** (83% at 0.85) →
the existing search addresses **0%** of our questions. Deeper: (1) our bottleneck is answer
COMPOSITION not retrieval — a SEARCH-LESS frontier already out-answers us +10pp (R280) → search can't
fix composition; (2) we already OUT-retrieve the 2025 SEARCH-integrated baseline (RefL 85.2 vs 79.9)
→ search adds ~0 retrieval value on the official distribution; (3) axis costs — search HURTS Speed
(scored, we're weak at 61.7 hard) via a synchronous scrape, RISKS RefCon (our only lead) + precision
(our ref problem) + tone. **Recommendation: fix composition first (R284 + compose-correct); search is
at best a later NARROW, AUTHORITATIVE (EUR-Lex not DDG), ASYNC low-conf fallback — not a headline
lever.** Full memo in the session transcript.

## 5.7 — GROUNDED Sonnet-5 judge (operator request) — BUILT + running
Operator: "use a Claude Sonnet 5 unbiased independent judge grounded in the EU AI Act text to
determine ref and answer correctness and citations for proper measurements."

Built **`evals/judge/grounded.py`** (committed `85e2f25`): an INDEPENDENT absolute judge scoring
against **verbatim `app.data.provision_text`** (not the incomplete gold labels):
* **answer_correctness** — LDP decomposition vs the verbatim text of the gold∪predicted provisions
  (full Article 5 ~11k fed UNCUT so 5(1)(f)/(g)/(h) citations verify).
* **reference_correctness** — precision = cited-and-governing / cited; recall vs provisions the TEXT
  shows govern the question (so an incomplete gold can't penalise a correct broader cite nor reward a
  wrong omitted one) → the grounded ref-precision measure the operator wants.
* **citation_faithfulness** — cite-and-mismatch vs verbatim.
Default `claude-sonnet-5`; reuses the runner provider/retry/parse plumbing; label-blind.

Why this over the existing judges: `evals/judge/runner.py` correctness grades vs GOLD KEYWORDS + refs
vs KB SUMMARIES; `ab_judge` was sonnet-4-6 + KB-summary grounding + **does NOT persist answers**
(so its run couldn't be re-judged — I stopped it). The old ab_judge partial (60/132, sonnet-4-6)
showed tp_v4_003/tp_v4_020/mt_v4_004 branch correctness wins, 0 baseline wins — a positive but
superseded cross-check.

Smoke (sonnet-5) verified it catches REAL grounded findings: over-citation (Art 6/Art 2 not governing
→ precision 0.67) and a subtle factual over-reach ("ethnicity" is not a verbatim Art 5(1)(g)
category). **RUNNING** (`b46z0inn7`): grades baseline (`easyhard-r284-A`) vs the R284 branch
(`easyhard-r284-B` = the FULL bundle H3+H1+H2 — the answers I have stored). Sidecars
`grounded-r284-{A-baseline,B-branch}-grounded.json`. ⚠ B = full bundle (incl. H1); to grade the SHIPPED
H3+H2 exactly, generate H3+H2 answers (V2=1, COMPLETE=0) + grade — the A-vs-B run resolves the H1
ref-precision question first (grounded), which decides whether the H3+H2 ship is confirmed.

### GROUNDED RESULT — baseline (A) vs full bundle (B = H3+H1+H2), Sonnet-5, n=132, 0 errors
| grounded axis | A baseline | B branch | Δ |
| --- | --- | --- | --- |
| answer_correctness pass | 0.424 | **0.485** | **+6.1pp** |
| citation_faithfulness pass | 0.652 | **0.705** | **+5.3pp** |
| reference precision | 0.625 | 0.597 | **−2.8pp** (H1 over-cite, grounded-confirmed) |
| reference recall | 0.860 | 0.884 | +2.4pp |
| reference F1 | 0.724 | 0.712 | −1.2pp (flat) |

R284 clearly improves ANSWER correctness + CITATION faithfulness vs the verbatim Act (not
token-gaming). The judge's ref failure modes name the H1 cost exactly ("over-cited Article 6 / Article
2 … not governing"). **Confound:** B includes H1, which may drive PART of the answer/citation gain AND
the precision loss — so the shipped H3+H2 numbers must be measured, not inferred. **RUNNING**
(`byiqzuf81`, ~2h): `evals/harness/gen_arm.py` generates the shipped H3+H2 answers
(`easyhard-r284-H3H2.ckpt.jsonl`) then grades them grounded (`grounded-r284-H3H2-grounded.json`) vs the
reused baseline-A-grounded. Ship iff H3+H2 holds the answer/citation gains AND reference precision ≥
baseline (H1 dropped should recover it).

Re-judge / measure ANY sidecar going forward:
```
python -m evals.judge.grounded --sidecar <ckpt.jsonl|sidecar.json> --label X \
  --model claude-sonnet-5 --provider wrapper --timeout 120 --concurrency 3
```
Generate one arm's answers for grounded re-judging (arms don't persist answers):
```
python -m evals.harness.gen_arm --label X --env REGENOLD_ANSWER_V2=1 --env REGENOLD_ANSWER_COMPLETE=0
```

## 6. NEXT radical levers (queued — need the wrapper, so after the A/Bs)
* **Compose-correct / let-Opus-override-wrong-drafts** — the systemic answer lever the st_v4_006
  self-correction implies. A Stage-2 instruction telling Opus to independently verify the verdict and
  override a misclassifying draft (esp. the confident-wrong "not prohibited"). Davidath-safe
  (Stage-2-only). UNTESTED — build it WHEN the wrapper frees (prompt levers need the live loop) then
  live-verify + A/B (separate flag). Could be higher-ceiling than H3's targeted patterns.
* **General-fallback softening** — the fallback asserts a confident "NOT prohibited"; softening it to a
  neutral "evaluate against Art 5 / Art 6-Annex III" lets Opus self-judge. Fires on 0 davidath rows
  (byte-identical) but risky on minimal-risk rows (lr_inventory / lr_music) — A/B before ship.
* **Broader H3 patterns** — ONLY for EVIDENCED wrong-verdict rows (avoid overfitting; social_scoring /
  rbi are literal-only but have no failing probe row yet).

## 7. GOTCHAS carried from R283
* Run any answer A/B with PROD answer-length env in BOTH arms (local harness uses CODE defaults — cap
  3/400 — which does NOT match prod uncapped).
* Worktree runs: MAIN venv abs-path (`D:/Claude Projects/regenold-eu-ai-act-rag/.venv/Scripts/python.exe`)
  + `PYTHONPATH=D:/Claude Projects/rag-answer-v2` + cwd=worktree. `REGENOLD_EXTERNAL_EMBEDDINGS=0` +
  dead-port `OPENAI_API_BASE=http://127.0.0.1:1/v1` for the deterministic bench.
* Never run two wrapper-bound jobs concurrently (single local Claude Max; prod hairpins here too).
* Auto-commit hazard: work in the worktree; `git fetch` + rebase origin/main before pushing.
