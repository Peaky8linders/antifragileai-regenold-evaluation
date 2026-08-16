# NEXT SESSION — handoff (2026-08-16, after R350.2 checkpoint)

Repo: `antifragileai-regenold-evaluation` (EU AI Act RAG). Worktree is the
isolated Freebuff worktree on `main`. Run tests with `py -3.12 -m pytest tests/
-q --timeout=45 -p no:cacheprovider` (6490+ pass). Bedrock A/Bs need the env
loader `scratch/live_ab_env.py` and the frontier launcher
`scratch/run_ab_r351.py`.

## Where we are — the story in one paragraph

R349 wired the legal_v2 judge axes (ans_corr / ref_corr / cite_faith /
ans_conc) into every `dynamic_ab` run. R350 measured the full optimised stack
(Cohere rerank × KG-candidates × query expansion) LIVE on 84 rows
(graphrag+medtech+expert-review): fired 57/84, all axes UNDERPOWERED, judge
axes throttled, and a **hard-rule-#8 veto** (gold_dropped_head 25 → 27). R351
diagnosed and fixed the cut-level mechanism (`stabilize_anchor_tier` — a KG
neighbour could out-score and displace a gold anchor at the citation budget
cut). R350.2 re-measured the same stack WITH the R351 fix on the new 81-row
live-answers probe (from the attached "Regenold — Questions & Live Answers"
file): **veto AGAIN — gold 46 → 49 at n=48 clean rows** (the account's daily
Bedrock quota throttled before row 81). The new mechanism is GENERATION-LEVEL:
wire refs are answer-driven (Component D extracts citations from Stage-2
prose), and the KG pool changes what Opus writes — on la_q87 the branch prose
said "listed in notably the Medical Devices Regulation" instead of "listed in
Annex I", so the literal phrase never reached the prose and the gold ref
dropped. Neither R351 (anchor-tier) nor the origin/main R350 fix
(`REGENOLD_RERANK_KG_NONCITABLE` projection) can fully close that.

## The complete evidence (checkpointed, do not re-run)

**`docs/R350-checkpoint.md` (1.28 MB, merged #40)** — machine-generated from
the sidecars by `scratch/checkpoint_r350.py`:

- R350-full: all **84 rows × both arms** — live answers, refs, scores, and the
  full legal_v2 judge verdict remarks (omission_detail / wrong_refs /
  faithful_refs) from the per-row sidecars. 5 veto rows flagged: xr_16, xr_03,
  grb_20, ng_06, med_03.
- R350.2: the **48 CLEAN rows** (6 post-throttle rows excluded), veto 46→49,
  5 regressions (la_q87, la_q20, la_q51, la_q73, la_q84) + 4 improvements
  (la_q76, la_q18, la_q79, la_q37), per-row refs/answers both arms.

Sidecars (gitignored but on disk):
`evals/bench/results/dynamic-ab-r350-full.json` (+ `-judge-base.json`,
`-judge-branch.json`), `dynamic-ab-r350-live-answers.json` (54 rows, 48 clean),
`dynamic-ab-r351-smoke.json`.

**R350-full axis table (n=84, fired 57/84):**

| axis | base | branch | delta | CI | verdict |
|---|---|---|---|---|---|
| ref_loose | 0.8579 | 0.8478 | −0.0101 | [−0.038, +0.015] | UNDERPOWERED |
| ref_strict | 0.7407 | 0.7211 | −0.0196 | [−0.054, +0.013] | UNDERPOWERED |
| ref_conc | 0.6110 | 0.5968 | −0.0142 | [−0.080, +0.050] | UNDERPOWERED |
| kw_recall | 0.7586 | 0.7497 | −0.0089 | [−0.034, +0.017] | UNDERPOWERED |
| ans_corr | 0.3830 | 0.4043 | +0.0213 | [−0.064, +0.106] | UNDERPOWERED |
| ref_corr | 0.5918 | 0.5306 | −0.0612 | [−0.143, +0.020] | UNDERPOWERED |
| cite_faith | 0.6667 | 0.7292 | +0.0625 | [−0.063, +0.188] | UNDERPOWERED |
| ans_conc | 0.6667 | 0.5833 | −0.0833 | [−0.208, +0.021] | UNDERPOWERED |
| **gold_dropped_head** | **25** | **27** | **+2** | — | **🚫 VETO** |

Judge integrity: base 80/84 clean, branch 46/84 clean (throttle). Paired
judge axes over ~47-49 rows where both arms scored; errors skipped, never
counted as passes.

## Merged PRs this session

- #36 R349 — legal_v2 judge axes join every dynamic_ab run.
- #38 R350.2/R351 — live-stack gold veto fixed at the CUT (anchor-tier
  stabilization) + 81-row live-answers probe + probe-sources harness filter.
- #39 docs — R350.2 re-measurement: veto persists via generation-level drift.
- #40 checkpoint — full live data (answers + judge remarks).
- Also merged (origin/main, other session): R350 `REGENOLD_RERANK_KG_NONCITABLE`
  projection fix (#37) — same defect as R351, fixed independently; both shipped.

## Open, ranked

1. **The decisive isolation run: query-expansion ONLY (no rerank, no KG) on
   the 81-row live-answers probe.** R346 measured levers SEPARATELY: rerank
   alone wash (gold 17→17), expansion alone BETTER (17→14), and every combo
   with KG-candidates vetoed (R350 25→27, R350.2 46→49). This run decides
   whether expansion alone clears the gate. One command (when the account
   quota window reopens):
   ```
   PYTHONPATH=. py -3.12 scratch/run_ab_r351.py --branch-env REGENOLD_QUERY_EXPANSION=1 \
       --label r350-live-expansion --max-rows 81 --batch 6 --min-call-gap 15 \
       --probe-sources live_answers --no-judge
   ```
2. **Generation-level citation drift is the real open problem.** The wire refs
   are answer-driven; the KG pool changes what Opus writes; a phrase the model
   never writes can never be extracted (la_q87's "Annex I"). Candidate fix
   directions: constrain Stage-2's citation universe to the retrieval-derived
   set (the `_stage2_citable_reference_bases` R327 machinery exists, gated);
   or a post-Stage-2 anchor-reconciliation that re-adds dropped gold-candidate
   anchors when they ARE in the retrieval context. Gate with dynamic_ab.
3. **R351 vs R350 non-citable — the A/B that decides which fix ships** (open
   item #1 in origin/main's CLAUDE.md). R351 = recall (anchors tiered),
   R350 = precision (neighbours non-citable). Run both against the gold-
   carrying live-answers probe.
4. **Judge on the R350.2 sidecar.** The R350.2 live-answers run had `--no-judge`
   (account quota). Once the sidecar exists with 81 clean rows, run the
   resume-aware judge (`scratch/r350_judge.py --arm base/branch/merge` pattern,
   but for the r350-live-answers label) to get the answer-level axes.
5. Run `--mode hard` (never run — the graded turn). Ground R346 sidecars.
   Fix the judge's three known defects (see CLAUDE.md open list).

## Working Bedrock recipe

- Env: `scratch/live_ab_env.py` loads `D:/Claude Projects/
  antifragileai-regenold-evaluation/.env` (the AWS_BEARER_TOKEN_BEDROCK key the
  operator re-minted) and forces Bedrock-only (no Claude-Max tunnel; kept for
  the live re-evaluation).
- Frontier tier: `scratch/run_ab_r351.py` pins every lane (incl.
  `REGENOLD_QUERY_EXPANSION_MODEL` — the paraphrase defaults to sonnet and
  dies silently if sonnet is throttled) to `claude-opus-4-6`.
- ⚠ **Account quota is daily and rotates per-model.** This session: Opus
  exhausted ~09:00, recovered ~09:45, exhausted again ~09:58. Probe before
  launching: `check_connectivity_and_permissions(model)`. When throttled, the
  harness fails soft and the deterministic fallback SERVES — rows look healthy
  (err None) but are contaminated. Kill the run; do not trust rows after the
  first `regenold_stage2_fallback_served`.
- Checkpoint every batch; resume from the sidecar.

## Gotchas carried in

- ABSK Bedrock keys expire ~30 days (cryptic auth failures); re-mint when
  403/entitlement errors appear. Cohere Trial key: 10 req/min — unpaced runs
  measure INERT.
- The wire references are answer-driven (Component D); a parse-level fix can
  protect the RETRIEVAL set but not the generation prose. Judge axes pair only
  rows where both arms scored (errors skipped, never passes).
- Live-answers probe gold: 81 rows from the attached questions file, with 7
  documented gold corrections (the file's own refs were provably wrong on
  Q5/Q6/Q11/Q27/Q29/Q42/Q77), head-projected per the R337 corpus invariant;
  Q55/Q56 are out-of-scope probes.
