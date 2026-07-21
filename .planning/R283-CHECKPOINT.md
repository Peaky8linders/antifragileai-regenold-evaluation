# R283 — reference-recovery bundle (SHIPPED-but-unpushed) + the ANSWER-correctness pivot

**Session:** 2026-07-20. **Status:** R283 built + A/B-won + committed to `main` locally (NOT pushed).
Then the operator redirected: the round's real goal is to lift **ref AND answer correctness, easy
AND hard**, to close the gap to the 2026 frontier — R283 only lifted **ref-easy**. Full answer-gap
diagnosis done (below); the answer-correctness levers are designed but NOT yet built/measured.
Checkpoint so nothing here is re-derived.

---

## 0. EXACT tree state (read first)

* Local `main` HEAD = **`504438f`** `feat(refs): R283 — reference-recovery bundle (PROTECT/ADD), easy +1.56pp`.
  It is **1 commit ahead of `origin/main`** and **NOT pushed** (push held after the operator redirect).
* `origin/main` = `c464dc4` (R282 #292 + the easyhard_ab paired-subset harness fix #293). The R283
  commit was **rebased onto** this cleanly (no conflicts; re-verified below). Working tree is CLEAN.
* **Decision pending:** push `504438f` to deploy the ref-easy win, OR fold it into the answer work.
  R283 is safe + validated + net-positive; pushing it now locks the ref gain. If `origin/main` moved
  again, `git fetch && git rebase origin/main` (it rebased clean once; touched files: `regenold.py`,
  `graph_rag.py`, `_graph_rag_data.py`, `tests/test_r283_ref_recovery.py`).
* Worktrees still around: `D:/Claude Projects/r283-ref-recovery` (the R283 branch, points at the
  PRE-rebase `29dcfa0` — stale, safe to `git worktree remove`). The R283 A/B sidecar lives there:
  `D:/Claude Projects/r283-ref-recovery/evals/bench/results/easyhard-r283-full.json`.

## 1. R283 — what it is + all gates (DONE, green)

Bundle: **stop LOSING gold** (never DROP refs — the R142.1 trap). Master `REGENOLD_REF_RECOVERY`
(default ON) + per-fix sub-flags; all stage2-gated so davidath is byte-identical.
* **Fix #1** R72 reconcile **named-head protection** (`_question_named_head_refs`) — never drop an
  article the LIVE question names (the `ma_*` multi-article rows).
* **Fix #3** **lead-ref promotion** (`_promote_lead_ref`) — float the article the verdict leads with
  to the R281 clamp head so it isn't tail-clamped. Pure stable reorder.
* **Fix #4** engine **keyword-map additions** (`_R283_KEYWORD_ADDITIONS` in `_graph_rag_data.py`) —
  Art 101/73/113 for 4 tricky rows (tr_v2_004/028/002/001). Verified **0 davidath hits**; folded into
  `_engine_cache_key` (R263.2).
* **Fix #2** tier-asserted-gateway protection — IMPLEMENTED but **OPT-IN, default OFF**
  (`REGENOLD_REF_RECOVERY_TIER=1`): the smoke caught it protecting a NON-gold Art 6 on a
  prohibited-practice question (precision leak). TODO if revisited: "protect only the LEAD verdict's
  gateway".

**Gates:** davidath 476/476 byte-identical vs R282 (0 pred_answer + 0 pred_refs diffs, verified with
an R282 worktree); 276-runner all-100% RISK_F1 1.00; OOS 21/21; 27 unit tests
(`tests/test_r283_ref_recovery.py`); touched-surface 16-module set = 0 new regressions (identical
4 pre-existing `provider=cli` env-artifact failures vs main).

**LIVE easyhard_ab A/B (`--local` + Claude Max wrapper, 132 rows, 0 err):**
* EASY (n=95): ref_loose 0.8105→0.8526 (+0.042), ref_strict 0.6591→0.6969 (+0.038),
  ref_conc 0.5755→0.6141 (+0.039), pred:gold 1.55→1.55 → **+1.56 pp**.
* HARD (n=37): ref_loose 0.7523→0.7658 (+0.014), ref_strict −0.006, ref_conc −0.007 (noise) → −0.02 pp.
* Recall UP both splits, **no GOLD-LOSS flag**, no new over-cite. Clean easy win, hard flat.

## 2. THE REDIRECT — R283 optimized the wrong axis

Operator: *"you were supposed to lift ref AND answer correctness for easy and hard, and compete with
the 2026 frontier, as we had lower scores from the regenold report on those areas."*

R283 lifted **ref-easy** only — the axis where we're already relatively strong. R280's head-to-head
is the tell: a **search-less** frontier model **out-answers us by ~10pp kw** while we out-reference
it. The ref-recovery plan pushed refs (strength), not answers (the frontier gap). The real target is
**answer correctness, easy + hard**.

## 3. FRONTIER ANSWER-GAP DIAGNOSIS (the key deliverable — do NOT re-run the agents)

Compared OUR live answers (`evals/bench/results/easyhard-r279-live.json`, arm A) vs raw `claude-fable-5`
NO-retrieval answers (`evals/bench/results/easyhard-frontier-fable5.easy.ckpt.jsonl`, 33 rows w/ text).
The −10pp answer gap decomposes:

* **~half GENUINE (judge-movers):**
  * **Wrong verdicts** from a deterministic fallback template ("...not among the practices prohibited
    under Article 5 ... turns on Article 6...", fires on **12/95** rows): `tp_v4_003` predictive
    policing on profiling → we said "NOT prohibited"; correct is **Art 5(1)(d) PROHIBITED** (opposite).
    `st_v4_006` grid safety component → we routed **Annex I**; correct is **Annex III(2)** critical
    infrastructure. The classifier misses practices described but not NAMED, and mis-precedences
    "safety component"→Annex I over critical-infra→Annex III.
  * **Incomplete multi-part**: `st_v4_020` "difference between minimal- and high-risk?" → we described
    ONLY minimal (323 chars, our shortest). `tp_v4_007` email-translation → we said limited/Art 50,
    gold = minimal.
* **~half SURFACE-FORM (mostly proxy, ~free to fix):** our composer NOMINALIZES + HYPHENATES statutory
  terms — "emotion-**inference**" vs `emotion recognition`, "facial**-**recognition" vs `facial
  recognition`, "critical **energy** infrastructure" vs `critical infrastructure`, "ban/prohibition"
  vs `prohibited`. ~7/12 misses.
* Frontier answers are **2.6× longer** but the extra is mostly **PADDING** (penalties/GDPR/timing
  tails) we must NOT copy — conciseness is the ONE axis we lead (zero GM headroom).

### The 3 answer levers (ranked)
* **H3 — kill the wrong-verdict fallback** (highest correctness value, guaranteed judge-mover, NOT
  noise). Detect predictive-policing-by-description → Art 5(1)(d); fix safety-component vs
  critical-infra precedence → Annex III(2). Classification/retrieval fix; davidath-safe if narrow
  (0-hit). Audit the 12/95 rows firing the "not among the practices prohibited... turns on Article 6"
  template.
* **H1 — answer EVERY part** of multi-part/comparison questions (scoped to required parts, NOT
  frontier padding). Prompt lever.
* **H2 — use the Act's canonical multi-word terms** verbatim (zero conciseness cost). Prompt lever.
  ⚠ H2 games the substring `kw_recall` proxy but may NOT move a semantic judge — validate with
  `ab_judge`, don't trust kw alone.

## 4. ANSWER-SHAPING MAP (prod config — critical)

**Prod (`railway.toml [deploy.envs]`) ALREADY runs UNCAPPED answers:** `REGENOLD_MAX_ANSWER_SENTENCES=0`,
`REGENOLD_QA_LENGTH_CAP=1200`, `REGENOLD_HARD_CHAR_CAP=0`, Stage-2 ON, `P2P_GRAPH_RAG_STAGE2_MODEL=claude-opus-4-8`,
`REGENOLD_VERBATIM_ANSWER=1`, `REGENOLD_SYNTHESIS_DEFAULT=1`. So the 3-sentence/400-char normaliser cap
does NOT fire in prod — the binding length constraint is the **Stage-2 USER-message prompt** ("1 to 4
concise sentences", `graph_rag.py:6216-6217`) + the model self-limiting. (Frontier has no such rule.)

**⚠ System prompt (`ANSWER_GENERATE_SYSTEM`) is INERT on the wrapper path** (R282: the Claude-Max
wrapper sets `{"type":"text"}` which the SDK drops → 0% delivery). **ALL answer-prompt edits must go
in the Stage-2 USER message** — built in `graph_rag.py::_claude_max_enhance_answer`:
* classification branch: `graph_rag.py:6159-6172` (ends "Cite only articles and annexes..." at 6171).
* general (else) branch: `graph_rag.py:6173-6222`; the "describe every article you CITE" rule is at
  6187-6191; the "1 to 4 concise sentences" rule at 6216-6217.
* H1/H2 slot at 6187-6191 (else) + 6171 (classification). H1 must carve out the sentence budget the
  way the existing "rule 12b closed-set completeness" override does (6220-6222).

**Whole-answer REPLACERS with NO env gate (audit if answers regress):** the R48/R49-A consistency
guard (`regenold.py:7174-7242`, fires on a `_STAGE2_REFUSAL_MARKER` match → ships KB-stub prose) and
Component-D (`regenold.py:7567-7644`, out-of-refs cite → falls back to shorter deterministic Stage-1).
The R94 verbatim overwrite (`regenold.py:7646`) is INERT on simple QA under `SYNTHESIS_DEFAULT=1`.

**Curated Stage-2 skip** (`REGENOLD_CURATED_STAGE2_SKIP`, default ON, 28 intercepts, `graph_rag.py:6566`):
ships FULL hand-written answers; **never A/B'd** (the `=0` arm is the "first-ever measurement" queued in
R277/R280) — but it PROTECTS completeness, so `=0` likely HURTS. Low priority.

## 5. NEXT STEPS (fresh session, ranked)

0. **Decide R283:** push `504438f` (ref-easy win, safe) or hold. If pushing: `git fetch && git rebase
   origin/main` if needed, then `git push origin main` (auto-deploys Railway).
1. **Build H1+H2 as ONE Stage-2 USER-message prompt lever** (env-gated, e.g. `REGENOLD_ANSWER_COMPLETE`,
   default OFF for the A/B). Edit `graph_rag.py:6171` + `6187-6191`. davidath byte-identical
   (Stage-2-only). H1 = "answer every clause/part the question asks (each tier/route it contrasts)";
   H2 = "use the Act's exact statutory terms verbatim (emotion recognition, facial recognition,
   prohibited practice, critical infrastructure) — do not nominalize or hyphenate them".
2. **A/B it** — the gate for an answer change is **`ab_judge` correctness** (not kw alone), with
   **`easyhard_ab` guarding refs** (don't undo R281). ⚠⚠ **RUN THE A/B WITH THE PROD ANSWER-LENGTH
   ENV IN BOTH ARMS** (`REGENOLD_MAX_ANSWER_SENTENCES=0 REGENOLD_QA_LENGTH_CAP=1200 REGENOLD_HARD_CHAR_CAP=0`)
   — the R283 local A/B used CODE defaults (cap 3 / 400) which does NOT match prod (uncapped) and
   under-represents answer length.
3. **Build H3 (the real correctness core, separate PR):** narrow classification fixes for the
   wrong-verdict rows — predictive-policing-by-description → Art 5(1)(d); safety-component vs
   critical-infrastructure precedence → Annex III(2). Verify 0 davidath hits (scan `qa_pairs.json` +
   `scenarios.json` for the new patterns), then A/B `ab_judge` correctness + `easyhard_ab` ref guard.
4. **Hard split:** the frontier-gap rows are all EASY (single-turn). For HARD (multi-turn) answer
   correctness, re-run the same diagnosis on the multi-turn probe (`scenarios_paper_multiturn_v4`,
   `scenarios_multiturn_v2`) — likely the same completeness + coreference issues.

## 6. Methodology GOTCHAS (memory)

* **Local `easyhard_ab` uses CODE defaults, NOT prod env** → set the prod answer-length env for any
  answer A/B (see step 2). This under-counted R283's answer axes too (irrelevant to R283's ref win).
* **System prompt inert on the wrapper path** (R282) → answer-prompt edits go in the Stage-2 USER
  message only.
* **`ab_judge` refs axis has no minimality term** (prefers the superset) → use gold-bearing
  `easyhard_ab` for ref precision; `ab_judge` for answer correctness. (CLAUDE.md rule #6 + memory.)
* **Multi-agent auto-commit hazard is REAL this session** — `origin/main` advanced (R282 #292 + #293)
  while working off `125f6d4`. Work in a worktree; `git fetch` + rebase before pushing; never force-push.
* **Don't re-inflate refs (undo R281)** chasing answer completeness. The R281 adaptive clamp
  (`regenold.py:7654`) runs LAST and keeps refs tight, so longer PROSE ≠ more wire REFS as long as the
  clamp holds. "Describe every RETRIEVED article" = the R281 disease; "describe every NAMED/asked
  article" is safe.
* **H2 (canonical terms) games the substring kw proxy** — a semantic judge may not reward it. Gate on
  `ab_judge`, not `kw_recall` alone.
* Each live A/B (`easyhard_ab` full, or `ab_judge`) is **~2h** (wrapper-bound, ~26s/row × 132 × 2,
  sequential — never run two wrapper jobs concurrently). Checkpoints per row.

## 7. Investigation artifacts (this session, don't re-run)
Three parallel agents produced: (a) the post-Stage-2 answer-shaping map (§4), (b) the frontier
answer-gap diagnosis (§3), (c) the curated-skip + Fix-#5 prompt insertion analysis. Their findings are
captured above in full.
