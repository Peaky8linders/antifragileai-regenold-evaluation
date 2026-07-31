# R304+ — getting ready for a regenold re-run, and closing the frontier gap

Handoff for fresh sessions. Read `CLAUDE.md` `## Round 302` and `## Round 301`
first; this plan assumes them.

---

## 0. The strategic picture — read this before choosing any work

The official 2026-07-14 scorecard (the only externally-graded number we have):

| | us | 2025 baselines | frontier |
| --- | --- | --- | --- |
| easy | **77.5** | 80.9 | 88.1 |
| hard | **73.0** | 83.2 | 87.4 |

Overall is a plain **geometric mean** of the axes, which has two consequences
that should drive every decision:

1. **A geometric mean is dominated by your WORST axis.** Lifting a 0.30 axis to
   0.40 is worth far more than lifting a 0.85 axis to 0.90. Rank work by the
   axis's current level, not by how big the delta looks.
2. **Answer-Conciseness is the ONLY axis we lead — so it has ZERO headroom and
   is pure downside risk.** Any change that lengthens answers can only cost us.
   Guard it on every A/B even when it is not the target.

**The gap is ANSWER quality, not retrieval.** `AnsLoose − RefLoose` is **−13.1**
for us versus **+3.9** for the 2025 baselines: we retrieve *better* than they do
and answer *worse*. R301/R302 confirmed it internally — reference **recall
0.941**, only 6 missing refs across 43 rows, **zero rows failing on
missing-only**. We do not have a retrieval problem. Stop trying to fix one.

⚠ **Do not compare our local Ans metrics to the report.** See
`project_ans_metrics_not_comparable` — Jaccard ≤ recall is an identity, and the
official AnsL > AnsS on all 6 published systems, which our local scorer cannot
reproduce. No official formula was ever disclosed for ANY axis. Reference is
*partially* comparable but blind to sub-points. **The only valid frontier test is
a head-to-head on the same questions.**

---

## 1. First session: re-measure, because the baseline is now stale

Three things shipped since the last live scorecard and none has been measured
end-to-end together:

* **R302 grounding text default ON** — the biggest expected answer-side lift
  (mean factual 0.827 → 0.929 on the A/B). Never measured on a full run.
* **R303 Neo4j plan warm-up** — the graph now actually answers (41 ms vs a
  1356 ms timeout). Expected wire impact ~zero (see §4) but confirm.
* **R300 partition OFF / context restore** — still only one paired run.

Run, in this order:

```bash
# 1. full official batch, both modes, against deployed prod
python -m evals.regenold.run_official_batch --label r304-base --mode both \
    --endpoint https://<prod>/api/v1/regenold/eu-ai-act/ask --api-key $P2P_REGENOLD_API_KEY

# 2. grade with the grounded judge (regenold gold was never published)
python -m evals.judge.grounded --sidecar evals/bench/results/official-r304-base-*.ckpt.jsonl \
    --label r304-base --model claude-sonnet-5 --provider wrapper
```

**Report `stage2_polish` splits in the scorecard.** R302 measured three
populations that behave completely differently — curated intercept (86% answer
pass), un-curated deterministic (**0%**), Stage-2 (32%). Pooling them is how a
working Stage-2 fix gets scored on 12 rows it cannot move and reads as a false
negative.

**Quote both the binary and the graded number.** Same verdicts, partial credit:
answer 0.372 → **0.733**, reference 0.349 → **0.717**. About half the apparent
badness is the zero-tolerance AND gate. `mean_factual_score` and `mean_f1` are
already in the sidecar.

---

## 2. Ranked work, highest expected value first

### A. Un-curated deterministic rows — 0/5 answer pass, and they answer a *different question*

The worst-performing bucket by far, and it fails for a **nameable** reason:
`rg_018` (can the Commission amend Annex III → **Article 7**) gets the
`_GENERAL_CLASSIFICATION_VERDICT` fallback about "The system described…" when no
system was described; `rg_038` (what is a sandbox) gets one unrelated AI-Office
sentence; `rg_093` (irregular migration) gets RBI/social-scoring prose.

Curated intercepts are the only mechanism on this surface with a demonstrated
above-chance pass rate (**6/7 answer pass, 0.00 incorrect/row, 19% wrong-ref**),
because they skip Stage-2 and so leave the fabrication population entirely.

* Surface: `_deterministic_answer` detectors + `_is_curated_authoritative_intercept`.
* ⚠ **This is the davidath path** (`provider=cli` scores exactly it), so it needs
  a real davidath A/B — made cheap by the R120 0-hit method (prove the new gate
  fires on 0/476 rows → byte-identical by construction).
* Cite-anchor every sentence or the soft-cap drops it (R111 recipe).
* Curated content fixes ANSWERS, not citations — `rg_005`/`rg_009`/`rg_074` are
  curated rows that still fail the ref axis. Author the ref set tight.

### B. Stage-2 sub-paragraph attribution discipline (anti-fabrication)

At ROW level, **incorrect (16 rows) outranks pure omission (11)**, and incorrect
is a Stage-2 phenomenon (0.97/row vs 0.33 deterministic). R302's grounding-text
flip attacks this from the data side; this attacks it from the instruction side.

Clause shape: when attributing a duty to a lettered/numbered sub-paragraph, that
sub-paragraph's verbatim text must be present in the references block; if only
the parent article's text is supplied, cite the article without inventing a
sub-paragraph designation. Never name a member of a statutory list that is not in
the supplied text.

* **Must go in the Stage-2 USER message** — the system prompt is 0%-delivered
  (R282: forwarding it actually craters quality). **Assert the clause is present
  in the outgoing `req.user` before trusting any A/B.**
* Stage-2-only → davidath byte-identical by construction.
* Gate on `citation_faithfulness` (0.558, i.e. 44% headroom, and it *is* the
  misattribution axis) and the `incorrect` count. Kill it if `missing` rises.
* Cannot drop a reference → no gold risk.

### C. Repeat-run the two single-run results before building on them

Both R302 grounding-ON and R300's context restore rest on **one paired run**, and
this project has measured that n≤40 sign-flips all three reference axes on
*identical* arms. Run ≥3 repeats per arm and report mean ± spread. If grounding
holds, it is the anchor of the next scorecard; if it does not, the R302 default
flip should be revisited (`REGENOLD_GROUNDING_TEXT=0`).

### D. Latency — a scored axis we are ignoring

p50 ~60 s on the hard sample. The wrapper round-trip dominates (context tokens do
not move it — R302 measured grounding as latency-neutral). Levers not yet tried
against the *current* stack: the R52 Groq Stage-0 path, and narrowing which rows
take the Opus complex path. Measure before assuming.

---

## 3. Explicitly rejected — do not re-propose (each was MEASURED)

* **Any positional / top-N / budget reference clamp.** R142.1 lost a live
  pairwise **11-0 (p=0.001)**. R301's monotonic ref-count collapse (80% → 0% at
  1 → 5 refs) *survives difficulty stratification* and still is **not** evidence
  for a clamp: it is the arithmetic signature of a 40%-per-ref error rate under a
  conjunctive gate (independence predicts 59/35/21/13/7%). **This curve is the
  single most effective trap in the codebase — it has now tempted three rounds.**
* **The pushback-turn reference freeze** (R302 fix 1). Built and refuted: recall
  0.845 → 0.576, three rows to 0.0. Turn 2's additions are often the *governing*
  provisions. Code is gated OFF at `REGENOLD_PUSHBACK_REF_FREEZE`.
* **Prose-driven "drop cited-but-undescribed" pruners.** 86% of wrong refs are
  already described; R72 is already ON. Upside bounded at ~2%.
* **A completeness instruction to close the missing holdings.** R284 measured it
  INCREASING over-citation (pred:gold 1.71 → 1.75), and it adds fabrication
  pressure to exactly the rows already fabricating.
* **Answer length caps / re-sentencers.** The length signal is a difficulty
  confound — flat on HARD (33% vs 30%), predictive only on EASY.
* **Article-identity blocklists.** Annex III runs 75% gold, Article 6 67% — both
  above the 60% corpus baseline.
* **Graph fusion slack / "fix the graph".** R296 measured across 92 gold rows
  that graph slack **never adds a single gold ref**; 4 rows move, churning
  non-gold tail refs and sometimes evicting a gold anchor. See §4.

---

## 4. The graph: three layers, and only one was ever a bug

`retrieval_path=kb_fallback` is **by design**, not an outage symptom:

1. **R252** made the in-memory KB the PRIMARY retriever and demoted Neo4j to
   additive-only, because the old `obligations_for_risk_level` Cypher dumped the
   generic Arts 9-15 chain for any risk tier and anchored wrong articles.
2. **R303 (fixed)** — cold-start query-plan compilation blew the 250 ms budget, so
   the first 2-hop of every connection lifetime returned nothing, and the R294
   breaker turned three cold failures into 60 s of no graph. Now warmed at boot.
3. **R295/R296** — `fuse_with_kb_xrefs` runs with `winners == budget`, so hop2
   candidates have nowhere to go. `REGENOLD_GRAPH_FUSE_SLACK` stays **0**, and
   the reason is stronger than "risky": slack never adds gold.

So a resumed, healthy, fully-seeded Aura changes nothing at the wire on its own.
**Do not spend a session re-seeding or tuning the graph** expecting a score move.

---

## 5. Measurement discipline (the part that keeps being violated)

Before ANY A/B, four pre-flight checks:

1. The knob is **actually read** on the live path (`P2P_GRAPH_RAG_MODEL` and
   `P2P_GRAPH_RAG_STAGE2_MODEL` are both no-ops — Stage-2 is hard-floored to Opus).
2. It is in `_engine_cache_key` **iff** it is an engine flag — otherwise arm B is
   served arm A's cached answers and the run measures nothing (R263.2 has silently
   nulled at least four A/Bs).
3. It is **not inert** — measure the artefact it changes.
4. Define a **control that must not move**, and check it. R302's grounding A/B is
   the template: all 10 deterministic-path rows came back byte-identical between
   arms, which is what proved the flag was Stage-2-only.

And: **`--env` only applies in-process.** An A/B of an env flag against
`--endpoint <remote>` measures NOTHING. Use `run_hard_sample_r297` *without*
`--endpoint` (TestClient + the live wrapper).

Instrument choice: reference change → `easyhard_ab` (gold-bearing) or the
grounded judge; **never `ab_judge`** (no minimality term — it structurally prefers
the superset). Answer change → `ab_judge` or the grounded judge.

The grounded judge now emits **`wrong_refs` / `missing_refs`** (R302), so a
precision fix can finally be aimed at named provisions instead of guessing at
rank — which is how the clamp kept getting reinvented. Use it.

---

## 6. Standing gates for every PR

* davidath (`--qa-only` is enough for a fast loop; `--assert-baseline` for byte-diff)
* `evals.regenold.runner` — 276 rows, expect 0 failures
* `evals.regenold.runner_v2 --local --probe-oos --oos-suite all` — 49/51, **0 leaks**
* Deterministic env: `OPENAI_API_BASE=http://127.0.0.1:1/v1 P2P_GRAPH_RAG_PROVIDER=cli
  REGENOLD_EXTERNAL_EMBEDDINGS=0` (the last one neutralises the documented
  role-noun non-determinism)

## 7. Open operator items (not code)

* `GEMINI_API_KEY` is unset on Railway, so the Stage-2 Groq→Gemini→Mistral
  fallback collapses and a wrapper failure ships a raw deterministic KB dump.
  One variable; cheapest reliability win on the hard surface.
* `REGENOLD_GRAPH_BACKEND` is pinned to `neo4j` on the Railway dashboard while
  both `railway.toml` and the code default say `embedded` (the R80.2 override
  phenomenon). Decide which you want.
