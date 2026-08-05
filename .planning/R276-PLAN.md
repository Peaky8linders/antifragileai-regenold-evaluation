# R276 — Reference precision + the `Art.` complexity bug

**Status:** planned, nothing implemented. Fresh-session handoff.
**Origin:** the OFFICIAL regenold scorecard (`docs/Antifragile-Regenold-benchmark-report-preview.pdf`,
2026-07-14) + a full gap analysis (2026-07-16). Analysis write-up:
https://claude.ai/code/artifact/b053533a-dd10-45e8-a7ea-6b28a5c4f172

---

## 0. Read this first — the framing that makes the round make sense

**We beat 0 baselines.** Easy 77.5 / hard 73.0; the 2025 Search-Integrated baseline gets 80.9 / 83.2;
a frontier model + web search gets 88.1 / 87.4.

**Overall is a plain geometric mean of the 8 axes** (verified — reproduces every reported figure to
<0.05pp). Consequence: the LOWEST axes carry the most leverage, and an axis you already lead carries
NONE.

| axis | us (easy) | frontier | 2025 | marginal leverage (pp of Overall per +1pp) |
|---|---|---|---|---|
| Ans Correctness Loose | 72.1 | 94.4 | 83.8 | +0.134 |
| Ans Correctness Strict | 63.6 | 89.1 | 70.9 | +0.151 |
| Ans Conciseness | **96.0** | 89.1 | 90.3 | +0.100 — **WE LEAD. ZERO HEADROOM.** |
| Ref Correctness Loose | 85.2 | 96.1 | 79.9 | +0.113 (we beat 2025) |
| Ref Correctness Strict | 58.8 | 78.5 | 52.0 | **+0.163 — HIGHEST** (we beat 2025) |
| Ref Conciseness | 79.3 | 80.7 | 86.9 | +0.121 |
| Regulatory Tone | 98.5 | 100.0 | 99.1 | +0.098 |
| Speed | 75.1 | 79.7 | 95.5 | +0.128 |

### The paradox, resolved (do not re-derive this)
Conciseness is a **LENGTH-ONLY** metric (rules: *"The **length** of the answer is assessed with
respect to an exemplary ground-truth answer"*). Leading it while trailing correctness = **right size,
wrong content**.

**The "we over-optimised for brevity" hypothesis is FALSIFIED.** Every length cap is already OFF in
prod (`REGENOLD_MAX_ANSWER_SENTENCES=0`, `REGENOLD_HARD_CHAR_CAP=0`) and our live answers are
**1.7-2.25x LONGER than gold** (measured: median 623 vs 373 chars on
`evals/bench/results/medtech-graphrag-v124-main-live.json`; 22/24 rows longer). Real gold ≈ 600 chars
/ 3-4 sentences; we sit inside its tolerance band. **DO NOT SHORTEN ANSWERS** — it wins nothing (zero
headroom) and costs correctness.

### The decomposition that names the defect
`AnsL − RefL` = how well a system turns retrieved law into a correct answer:

| system | easy | hard |
|---|---|---|
| Frontier+Search | −1.7 | −2.6 |
| 2025 Search-Int | **+3.9** | **+4.9** |
| **US** | **−13.1** | **−4.7** |

vs the 2025 baseline (easy): **we RETRIEVE better (RefL 85.2 vs 79.9) and ANSWER worse (AnsL 72.1 vs
83.8)** — a ~17pp swing entirely downstream of retrieval. Same on strict (RefS 58.8 vs 52.0 we win;
AnsS 63.6 vs 70.9 we lose).

**The GraphRAG retrieval is not the problem — it beats a 2025 search-integrated model. The
answer-composition layer on top of it is.** That layer = 29 numbered rules + 34 hard prohibitions in
`ANSWER_GENERATE_SYSTEM`, curated intercepts that bypass the LLM, drift/fidelity/consistency guards,
a tone rewriter, 5 answer normalisers, the refs reconcile — tuned ~150 rounds against davidath, whose
answer-conciseness axis reads **0.196 where the real judge reads 96.0**.

R276 ships the two cheap, verified defects. The answer-composition gap itself is R277+.

---

## 1. D2 — the `Art.` complexity bug (do this FIRST; it is a pure bug fix)

### The bug (reproduced, not inferred)
`app/routes/regenold.py::_extract_conversation_anchors` (~:3985) explicitly normalises anchors to
**`"Art. N"`** form (*"normalise to `Art. N` form so deduplication is reliable"*) and builds
`"[Context anchors — articles: Art. 13, Art. 26; roles: deployer]"` (~:4012), prepended to the live
question. `app/engines/question_complexity.py::_is_multi_phrase` (~:167) then splits with a naive
`re.split(r"[.!?]+", scan_text)` — **no abbreviation guard** — so the period in `Art.` yields 2
segments ≥4 words ⇒ `_is_multi_phrase=True` ⇒ `is_complex_question=True`.

Verified in-proc (`P2P_GRAPH_RAG_PROVIDER=cli`):

| input | `is_complex` |
|---|---|
| plain single-turn Q | `False` |
| same Q + `[Context anchors — Art. 13; Art. 26; …]` | **`True`** ✗ |
| multi-turn flatten, marker present, NO prefix | `False` ✓ (R60.1's `rfind` works) |
| multi-turn flatten, marker present, WITH prefix | **`True`** ✗ |

### Why it is expensive NOW
Per `app/config.py` (R271, verified): `stage2_model` AND `complex_model` are BOTH
`claude-opus-4-8`. The tiers differ **only** by `thinking_tokens=0` vs `complex_thinking_tokens=4000`.
So the bug force-adds a **4000-token extended-thinking budget to every multi-turn request**. R271's
own pairwise measured thinking 2048→0 as **~23% faster** (p50 24.1s vs 31.0s) — the *presence* of
extended thinking costs real latency even though its *size* doesn't (`project_thinking_budget_not_
latency_lever` tested 4000 vs 1024 = wash; 0 vs non-zero is a DIFFERENT question — do not conflate).

⇒ direct cause of hard-mode **Speed 61.7 vs easy 75.1 (−13.4pp)**, the largest single-axis drop.
Leverage: hard Speed 61.7→85 ⇒ **+2.98pp Overall**.

### The fix
Make the complexity scan abbreviation-aware. **The repo already fixed this exact bug class** in
`app/integrations/regenold/tone_guard.py` (R54.1-C1 added negative lookbehinds for `Art.` / `Annex N.`
/ `e.g.` / `i.e.` / `etc.`) and ships an abbreviation-aware
`app/engines/sentence_index.py::split_legal_sentences`. Reuse one of them in `_is_multi_phrase`;
do NOT hand-roll a third splitter.

Alternative/complementary: strip the `[Context anchors — …]` prefix before the complexity scan
(it is metadata we injected, not user text — arguably it should never have been scanned).
**Recommend doing BOTH** — the prefix strip is the root cause, the abbrev-aware splitter is the
defence in depth (a user can legitimately type "Art. 13" themselves).

### Gate it or not?
- It changes the engine output (model/thinking choice) ⇒ if env-gated, the flag **MUST go in
  `_engine_cache_key`** (R30/R56/R79 doctrine; R263.2 is the cautionary tale where an omitted flag
  silently corrupted a same-process ab_judge run).
- Precedent cuts the other way: R54.1-C1 shipped the identical tone_guard fix **ungated** as a
  Critical bug fix.
- **Recommendation:** gate it as `REGENOLD_COMPLEXITY_ABBREV_FIX` **default ON**, add to the cache
  key, run the A/B below to confirm no quality regression, then consider removing the gate. Gating is
  what makes it A/B-able at all.

### A/B (the merge gate — CLAUDE.md hard rule #6)
Requires the Claude Max wrapper up on `127.0.0.1:8000`. D2 only touches multi-turn ⇒ isolate it:

```powershell
$env:OPENAI_API_BASE = "http://127.0.0.1:8000/v1"; $env:OPENAI_API_KEY = "dummy"
.venv\Scripts\python.exe -m evals.harness.ab_judge --label r276-d2 `
  --multiturn only `
  --baseline-env REGENOLD_COMPLEXITY_ABBREV_FIX=0 `
  --branch-env  REGENOLD_COMPLEXITY_ABBREV_FIX=1 `
  --judge-provider wrapper
```
**Pass condition:** no axis loses significantly (this is a latency fix — quality should be a WASH;
a wash is a PASS here, unlike D1). Then confirm the latency win from the run's own p50.

---

## 2. D1 — reference precision (the biggest lever, and the one with a trap)

### The defect
`app/routes/regenold.py`:
* `_collapse_parent_refs` (~:2378) — env `REGENOLD_COLLAPSE_PARENT_REFS`, **DEFAULT OFF**. Its own
  docstring: *"default OFF = keep parents alongside children **to maximise recall against
  human-annotated gold keys**"* — a DELIBERATE recall-over-precision hedge. The same docstring
  concedes the parent *"dilutes the 'minimal set' the spec asks for"* — which is verbatim what the
  rules demand (*"references ... Should contain the **MINIMAL SET** of relevant references"*).
* `_reemit_parents_for_subpoints` (~:2147, R87-C) — **DEFAULT ON**, re-adds the parent alongside the
  leaf. The two passes FIGHT. The re-emitter wins.

Measured on `medtech-graphrag-v124-main-live.json` (24 rows): **16 rows emit parent+leaf clusters**.
Gold `["Article 50"]` → we ship `["Article 50.1","Article 50","Article 50.2"]`. Gold
`["Article 6","Annex III"]` → we ship `["Article 6","Article 6.2","Article 6.3","Annex III"]`.

**Ref precision ≈ 45%** — over half the refs we ship are not gold. Triangulated three ways:
1. Algebra from the reported scores (RefL=recall, RefS=F1 ⇒ `P = f1·R/(2R−f1)`) = **44.9%**;
   implied pred/gold ref-count ratio **1.90x** (frontier 1.45x).
2. Measured exact-string precision on the live sidecar = **37%**.
3. Head-level (generous) = **56%**.

Recall is FINE (85.2, beats the 2025 baseline). **This is purely precision** — and RefS has the
HIGHEST marginal leverage of any axis while RefL has among the lowest. **The hedge is backwards.**

### ⚠️ THE TRAP — do NOT just set `REGENOLD_COLLAPSE_PARENT_REFS=1`
Our own eval gold is **0% sub-points**, so collapsing-to-leaf scores **catastrophically** against it
(simulated RefL 85→48). But that gold is **UNREPRESENTATIVE**: regenold's own example gold is
`["Annex IV.2", "Article 3.1"]` — sub-points. **Local evals cannot decide this question.**

**Our bench is STRUCTURALLY BLIND**: `evals/bench/metrics.py::article_heads` (~:120) collapses
`Article 50.1` → `Article 50`, so the shipped list and a perfectly-deduped list score IDENTICALLY.
(The grb_02 row scores a perfect 1.00/1.00/1.00 internally while shipping 3 refs for 1 gold.)
Simulated under exact-string scoring: shipped RefS **56.1%** vs parent-only **69.3%**.

Remember R142.1: a plausible positional ref clamp lost a live pairwise **11–0, p=0.001** by dropping
gold. Do not repeat it.

### The hedging maths (this is the decision rule)
Per parent+leaf cluster, if gold is one level and we don't know which:
* emit BOTH → precision 0.5, recall 1.0 ⇒ **F1 ≈ 0.667**
* pick ONE, correct with probability p ⇒ **F1 ≈ p**

⇒ **picking beats hedging iff we identify the right granularity >67% of the time.**

So the fix is **granularity SELECTION**, not a mechanical collapse: emit ONE level — the one the
question is actually about (question names a sub-point / the answer turns on a specific paragraph ⇒
leaf; otherwise ⇒ parent). Even without solving selection, capping at **one ref per head** strictly
dominates today's 3-4-per-head rows (e.g. grb_04's `Article 6` + `6.2` + `6.3`).

### Implementation shape
New env `REGENOLD_REF_GRANULARITY` with three values so the A/B can settle it empirically:
* `both` — today's behaviour (default initially, = byte-identical baseline)
* `leaf` — drop the parent when a leaf is present (= `_collapse_parent_refs=1`)
* `parent` — collapse leaves into the head
Plus, orthogonally, a `one-per-head` cap.

Cache key: **NOT required** — `_collapse_parent_refs` is a ROUTE-level pass (called ~:5473, ~:5963)
and per the R79 doctrine the cache stores the ENGINE output while route post-processing re-runs on
every hit. It also reads env **fresh per call**, so ab_judge's in-process toggle works on it. (This
is the opposite of `stage2_model`/`thinking_tokens`, which are import-time and CANNOT be A/B'd
in-proc — the R271 gotcha.) **Verify this still holds before relying on it.**

### Estimated leverage (bounded — RefCon's response is NOT identifiable from 3 data points)
| precision | RefS | RefCon flat | RefCon +5 | RefCon→90 |
|---|---|---|---|---|
| 45→55% | 58.8→66.8 | +1.25pp | +1.86pp | +2.51pp |
| 45→60% | 58.8→70.4 | **+1.76pp** | +2.37pp | **+3.03pp** |
| 45→66% (frontier's) | 58.8→74.6 | +2.33pp | +2.95pp | +3.61pp |

### A/B (the merge gate)
```powershell
.venv\Scripts\python.exe -m evals.harness.ab_judge --label r276-d1-leaf `
  --baseline-env REGENOLD_REF_GRANULARITY=both `
  --branch-env  REGENOLD_REF_GRANULARITY=leaf `
  --judge-provider wrapper
# repeat with --branch-env REGENOLD_REF_GRANULARITY=parent
```
**Pass condition:** the **refs** axis wins (or at minimum does not lose) AND correctness does not
regress. Ship the winning value as the default; keep the others as rollback.

**Caveat the A/B cannot fix:** ab_judge's refs axis is an LLM judge on faithfulness, not an
exact-string match against regenold's gold. It will tell you whether the answer's citations are
*supported*, not whether they match regenold's granularity convention. Treat a refs-axis win as
necessary-but-not-sufficient; the real confirmation is the next live-benchmark submission.

---

## 3. Regression gates (run for BOTH; all must hold)

Deterministic env (per `reference_worktree_eval_runs`): `OPENAI_API_BASE=http://127.0.0.1:1/v1`
`P2P_GRAPH_RAG_PROVIDER=cli` `REGENOLD_LOGIC_RAG=0` `REGENOLD_FUSION_STAGE2=0`
`REGENOLD_QUERY_DENOISER=0` `REGENOLD_EXTERNAL_EMBEDDINGS=0`.

| gate | expected |
|---|---|
| `pytest -q` | no NEW failures (baseline carries ~49 known `provider=cli`-defeats-Stage-2 env artifacts — A/B against a stashed clean tree before blaming yourself) |
| `python -m evals.bench.runner --qa-only --assert-baseline <label>` | **byte-identical**. D1 is byte-identical BY CONSTRUCTION (`article_heads` collapses sub-points ⇒ the metric literally cannot see the change). D2 should be too (davidath is single-turn ⇒ no context-anchor prefix) — **verify, don't assume**. |
| `python -m evals.regenold.runner` | 255/255 |
| `python -m evals.regenold.runner_v2 --local --probe-oos --label <l>` | 21/21, 0 leaks |

**Note the davidath byte-identity is EVIDENCE OF NOTHING here** — it is a regression guard only. Both
fixes are live-only by construction. Per CLAUDE.md hard rule #6: *"Do not ship an answer-quality /
Stage-2 / prompt / reference / scope change on 'davidath byte-identical' alone."*

---

## 4. Gotchas that will bite a fresh session

* **TWO app copies.** The top-level `app/` is LIVE. A nested `regenold-eu-ai-act-rag-main/app/` may
  exist and is STALE but looks canonical (its tests pass). Verify with
  `grep startCommand railway.toml Procfile` before editing. (`project_two_app_copies_live_vs_stale`)
* **Auto-commit hazard.** Automation auto-commits + pushes the SHARED main tree mid-session; main
  advances under you. **Work in an isolated `.worktrees/<name>`; stage only your files (never
  `git add -A`).** (`project_multiagent_autocommit_env`)
* **Agents litter the repo root.** This analysis session's verify agents dropped
  `verify_r*_tmp.py` at the root (removed). Check `git status` before committing.
* **ab_judge needs the wrapper up** (`127.0.0.1:8000`) and is rate-limit-prone — if Anthropic
  throttles, WAIT and retry. Do NOT substitute davidath and merge anyway (hard rule #6).
* **Round is CLOSED** — the rules allow *"a contestant to participate only once"*. There is **no
  deploy deadline**. These fixes target the promised *"live benchmark ... where contestants can
  participate at any time and submit updated systems"*. The only live clock is the **opt-out /
  anonymise window: 10 business days from 2026-07-14 ≈ 2026-07-28** — an operator decision.

---

## 5. What NOT to do (evidence against each)

* **Don't shorten answers.** AnsCon has ZERO headroom (we already lead) and we're already 1.7-2.25x
  LONGER than gold. Cutting moves nothing and costs correctness.
* **Don't chase ref RECALL.** RefL 85.2 already beats the 2025 baseline; recall has LOW leverage
  (+0.113/pp) vs precision-driven RefS (+0.163/pp). The existing hedge is backwards.
* **Don't trim thinking SIZE or enable fast mode for speed.** Measured washes
  (`project_thinking_budget_not_latency_lever`, `project_fast_mode_not_latency_lever`) — latency is
  wrapper-floor bound (~99% of wall-clock is the Claude-Max per-call process-spawn floor).
* **Don't flip `REGENOLD_STAGE2_SIMPLE_SKIP=1`** for speed without an A/B. My MEMORY index records an
  R129 result "refs 0.75→0.47" for it, but that claim is **NOT in CLAUDE.md and NOT in
  `project_r139_opus_always_stage2.md`** — treat as UNVERIFIED and re-A/B before trusting it either
  way. (The `_stage2_simple_skip_enabled` docstring claims the OPPOSITE — that R77 measured the
  deterministic answer net-POSITIVE. Someone should resolve this contradiction.)
* **Don't "fix" the date cutoff.** Already handled — Art. 113 carries the ORIGINAL Regulation dates,
  `ontology.py:170` records the R112 Omnibus removal, and `graph_rag_prompts.py:68` explicitly
  forbids Omnibus content. The residual `10^23`/one-third content is from the **18 July 2025**
  Commission Guidelines, which PREDATE the benchmark's 1 May 2026 cutoff (the rules exclude only
  *"**subsequent** ... interpretations"`). NO ACTION.
* **Don't trust davidath on answers.** Its AnsCon reads 0.196 where the real judge reads 96.0.

---

## 6. Suggested order

1. **D2** — abbrev-aware complexity scan + anchor-prefix strip. Gate `REGENOLD_COMPLEXITY_ABBREV_FIX`
   default ON, add to `_engine_cache_key`. Run the `--multiturn only` A/B. Cheap, low-risk,
   targets the biggest hard-mode lever.
2. **D1** — `REGENOLD_REF_GRANULARITY` {both|leaf|parent} + one-per-head cap, default `both` so the
   baseline is byte-identical. Run both A/B arms. Ship the winner as default.
3. **R277 (the real prize)** — the answer-composition gap (`AnsL−RefL = −13.1`). AnsS alone is
   +3.33pp of Overall. Hypothesis to test: we handcuff Opus 4.8 so hard (29 rules / 34 prohibitions /
   curated intercepts / 5 normalisers) that it underperforms the same model used naively with search.
   The evidence is genuinely mixed — R129 simple-skip and R77's Stage-2-net-negative point opposite
   ways — so this needs its own measurement round, not a guess.

**Bundle ceiling (arithmetic):** D1(P=60) + speed→90 + answer(+8L/+6S) ⇒ easy **84.4** (beats 2025's
80.9, short of frontier's 88.1); hard ⇒ **82.4** (just short of 83.2). Beating the 2025 baseline is
realistic. Beating the frontier requires R277.
