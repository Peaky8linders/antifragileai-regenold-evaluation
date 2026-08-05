# R300 — deep review of R299 + the two untagged truncation commits, and a 71-request live hard-eval

**Range reviewed:** `3b2d37d..757f0cb` — R299 (`6467c09` partition + completeness
verifier, `392979d` hardening) plus the two untagged 2026-07-30 commits
`8eb34e4` and `757f0cb`, both authored directly on `main` with no round entry.
15 files, +963/-268.

**Method:** an 8-lane specialist review workflow (logic x2, error-handling,
contract, silently-inert/env-drift, concurrency, EU-AI-Act domain, hybrid-RAG
architecture, eng-manager) over the diff, then an adversarial verifier per
finding whose default was REFUTED and which had to confirm by reading HEAD.
68 raw findings -> 18 verified, **18/18 survived**. Every load-bearing claim in
this document was additionally re-proved here by direct measurement, not
accepted on the reviewers' assertion.

---

## What was actually wrong

### P0-1 — the R299 partition silently dropped 5 Stage-2 context sections  *(FIXED)*

`_build_context_references_block` has two renderers. The unpartitioned one
emits obligations, COMPLIANCE GAPS, DIMENSION DETAILS, CROSS-REGULATORY
BRIDGING CONTEXT, SYNTHESIZED MULTI-HOP ANALYSIS and LEGAL AST LOGICAL
EVALUATIONS. The R299 Move-1 partitioned renderer was built solely from
obligations + grounding text and emitted **none of the last five**.

`REGENOLD_REF_PARTITION` ships default-ON, so this was live. Measured:

| | chars | sections |
| --- | --- | --- |
| partition OFF | 852 | 5/5 |
| partition ON (production) | **330** | **0/5** |

**61% context loss.** The costliest is CROSS-REGULATORY BRIDGING CONTEXT — the
GDPR / MDR bridges the cross-framework and MedTech answers depend on — then the
LogicRAG synthesis. R299 measured a real reference-precision win; that
measurement could not see this, because what it removed grounds the ANSWER, not
the citations.

Fixed by extracting `_render_supplementary_sections()` and calling it from both
renderers; in the partitioned one the sections go under BACKGROUND CONTEXT,
which is exactly what they are (non-citable supporting context), so R299's
citation discipline is preserved. After: **1065 chars, 5/5 sections**, OPERATIVE
+ BACKGROUND intact, OFF path unchanged at 852.

### P0-2 — hardcoded model downgrade in the wrapper transport  *(FIXED)*

`757f0cb` added, inline in `complete()` and unmentioned in its commit message:

```python
if model.lower() in ("claude-opus-5", ..., "claude-opus-4-8"):
    model = "claude-opus-4-6"
```

No env gate, no log, no test. It silently reverted R292's shipped Opus 5
Stage-2 **and made the `?include_reasoning=true` trace lie** — the trace
reported `stage2_model=claude-opus-5` while `claude-opus-4-6` was on the wire,
which would silently invalidate any future model A/B read off the trace (the
R263.2 class of measurement bug).

Measured against the live wrapper: `claude-opus-4-8`, `claude-opus-5` **and**
`claude-opus-4-6` all return HTTP 200 — so it repairs no wrapper error.

Kept as the default (flipping it is answer-affecting and needs the hard-rule-#6
live `ab_judge` gate) but now an env-gated, logged `resolve_wrapper_model()`
(`REGENOLD_WRAPPER_MODEL_ALIAS`, default ON = zero answer change), with the
trace reporting the model actually sent. `=0` is the arm a future A/B measures.

### P0-3 — the completeness verifier stated the regulation backwards  *(FIXED)*

Two independent legal-correctness defects in R299 Move 2, both live:

1. **Cross-article conflation.** For an answer citing Article 16 *and* Article
   17 it emitted one flat blob — `[including points (d)..., (g)...; including
   points (h)..., (m)...]` — reading as a single list, repeating letters
   (i)/(j) for different provisions, and presenting Article 17's points as if
   they continued Article 16's list, which stops at (l). **Article 16 has no
   point (m).** Now attributed per article ("Article 16 also requires ...").

2. **Nested romans flattened into the top level.** `provision_text._subpoints`
   returns a FLAT dict, so for Article 5(1) it yields
   `['a'..'h', 'i', 'ii', 'iii']` where the three romans are **5(1)(h)'s
   law-enforcement carve-outs**. Listing them as missing "requirements" states
   the regulation backwards — they are the conditions under which real-time
   remote biometric identification is *permitted*. `_drop_nested_romans` fixes
   it, and resolves the genuine ambiguity of `(i)` by context: a
   multi-character roman (`ii`) can never be a letter key, so its presence
   proves a nested block and `i` belongs to it. Verified: Article 5(1) ->
   `(a)-(h)`; Article 16 keeps its genuine lettered `(i)` in `(a)-(l)`.

Labels were also a keyword bag ("draw declaration conformity" for "draw up the
EU declaration of conformity"); they now carry the verbatim opening clause, cut
on a clause/word boundary with trailing function words trimmed.

### P1 — cache-key omission  *(FIXED)*

`REGENOLD_REF_PARTITION` and `REGENOLD_COMPLETENESS_VERIFIER` ship default-ON
but were never added to `_engine_cache_key`, though both flip
`GraphRAGResponse.answer`. The verifier correctly downgraded the reported
severity: production runs a single consistent arm, so this is an
**eval-integrity** defect, not a production-answer one — an in-process two-arm
`ab_judge` run would serve arm A's cached answer to arm B and measure nothing
(R263.2). Added, with `REGENOLD_WRAPPER_MODEL_ALIAS`.

---

## Claims that did NOT survive contact with measurement

Recorded because the reviewers were confident about them and they are wrong:

* **"`REGENOLD_QA_LENGTH_CAP` 1200->400 truncates production."** It does not.
  `railway.toml` pins `REGENOLD_MAX_ANSWER_SENTENCES="0"`, so `_no_cap` is True
  and both the sentence cap and the soft char cap are bypassed in production.
  The drift is real but **local-eval-only** — and the dominant term is the
  sentence cap (code 3 vs railway 0), not the char cap. Decomposed:

  | env | output |
  | --- | --- |
  | code defaults (local evals) | 3 sentences / 286 chars |
  | only `MAX_SENTENCES=0` | **12 sentences / 994 chars** |
  | only `QA_CAP=1200` | 3 sentences / 286 chars (no effect) |

* **"`_hard_truncate_at_clause`'s rewrite is a production truncation fix."**
  It is unreachable on both call sites — `REGENOLD_HARD_CHAR_CAP="0"` in
  `railway.toml`. The headline change of `757f0cb` is inert in production.

* **"The `max_tokens` 384->1536 bump is inert."** My own first check said this
  and was wrong — it added the answer headroom when `eff_thinking` is 0, which
  the real code guards against. Corrected: with `thinking_tokens=0` and
  `complex_thinking_tokens=4000`, the bump is **BINDING on simple Stage-2**
  (1024 -> 1536, +50% output ceiling — the ~80% majority path) and inert only
  on the complex path. It shipped un-A/B'd.

---

## Live measurement — 71 requests, 25.3% of the official hard population

Stratified sample (`run_hard_sample_r297 --frac 0.25`) against deployed
production: 28 multi-turn questions x 2 turns + 15 single-turn hard.
**0 HTTP errors, 0 refusals.**

| | multi-turn (n=28) | single-turn hard (n=15) |
| --- | --- | --- |
| refusal rate | 0.000 | 0.000 |
| regulatory tone | **1.000** | **1.000** |
| **pushback concession** | **0.0000** | n/a |
| refs / row (median) | 2.9 | 2.7 |
| p50 latency | 72.8 s (HARD) / 67.0 s (EASY) | 42.3 s |

Overall: **p50 60.7 s, p95 115.2 s, max 137.7 s**; answers median 785 chars,
p90 1440, max 2483.

**Two things this surfaced that are NOT yet fixed:**

1. **Citation instability under challenge.** 0% of rows concede the substance
   under the evaluator's adversarial "I think this contains hallucinations"
   pushback — the system holds its answer, which is the headline good news —
   but **36% (10/28) change their citation set** on that turn, in both
   directions: `rg_021` narrowed `[15,16,17,20] -> [15]`, `rg_041` dropped
   `Annex IV`, `rg_053` widened `[55] -> [51, Annex XIII, 55, 56]`. The graded
   hard answer is the POST-pushback one, and references-vs-gold is a scored
   axis, so a pushback turn that drops a gold ref costs directly. This is the
   single best-evidenced lever for the next round.

2. **Latency.** 60.7 s p50 is high against a scored axis. Stated honestly: this
   sample is hard-weighted and multi-turn-heavy, so it is **not** directly
   comparable to R286's mixed easy/hard p50 of 23.8 s / 37.4 s. Treat it as an
   absolute reading, not a measured regression.

---

## Gates (all green)

| gate | result |
| --- | --- |
| davidath QA (137) | **byte-identical to a same-env baseline run at `757f0cb`** — Ans Loose 0.1402 / Ans Strict 0.4032 / Ans Conc 0.198 / Ref Loose 0.8394 / Ref Strict 0.5543 / Ref Conc 0.4395 / Tone 1.0 |
| `evals.regenold.runner` (276) | **255/255**, RISK_F1 macro 1.00 |
| OOS probe (`--oos-suite all`, 51) | **49 PASS, 0 scope leaks** — the 2 wrong-reason soft-fails are the documented pre-existing ones |
| new tests | `tests/test_r300_review_fixes.py` — 39, plus the R299 / R288 suites pass unmodified |

Note on the baseline: CLAUDE.md records Ans Strict 0.4037, measured without the
`REGENOLD_EXTERNAL_EMBEDDINGS=0` neutraliser for the documented role-noun
non-determinism. Rather than assume, `757f0cb` was re-run under the identical
env and produced 0.4032 — so the branch is byte-identical, not -0.0005.

Every fix is Stage-2-only or transport-only, unreachable under `provider=cli`,
which is why davidath is byte-identical *by construction* as well as by
measurement.

---

## Deferred, with the measurement each needs first

* **`partition_context_references` demotes gold provisions to BACKGROUND**
  (2 lanes, verified CRITICAL). The all-operative escape hatch requires three
  conditions simultaneously, so whenever any target is derived, gold can land
  under a "do NOT cite" instruction. This is the R142.1 gold-drop class and it
  sits at the core of R299's design — it needs a live pairwise `ab_judge`, not
  a blind edit.
* **`_is_incomplete_trailing_sentence` deletes complete sentences** (verified
  IMPORTANT, live on every answer). It decides truncation from the last word
  alone, so a sentence legitimately ending in a listed function word is popped,
  and the loop can cascade. Needs a corpus check of real answers before
  tightening.
* **The `max_tokens` +50% simple-path bump** — shipped un-A/B'd, and answer
  length now runs median 785 / max 2483 chars against an axis (conciseness)
  the official scorecard says is the ONLY one we lead, i.e. the one with zero
  headroom. A/B it rather than revert it blind.
* **Fusion `claude-opus-5 -> claude-opus-4-8`** (`8eb34e4`, undisclosed rider):
  production-inert (`REGENOLD_FUSION_STAGE2="0"`) but it broke two tests in
  `tests/test_fusion_stage2.py`.
