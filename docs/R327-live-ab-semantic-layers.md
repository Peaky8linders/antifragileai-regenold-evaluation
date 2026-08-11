# R327 — live A/B of the 7-index semantic layers (50 July-7 questions)

**Date:** 2026-08-10
**Path:** local code under test → live Neo4j Aura `0644b854` → Claude Max via the
Cloudflare tunnel `wrapper.antifragile-ai.net` (CF Access service token).
**Sample:** the first 50 of the 110 official July-7 questions, `--mode easy`.
**Arms:** `REGENOLD_GRAPH_SEMANTIC_LAYERS` OFF vs ON, both with
`REGENOLD_KG_MAX_CHARS=REGENOLD_KG_SEMANTIC_MAX_CHARS=26000` so the only
difference is the presence of the three semantic blocks.

Sidecars: `evals/bench/results/official-r327-live-ab-A-easy.ckpt.jsonl` (OFF),
`official-r327-live-layersON-easy.ckpt.jsonl` (ON).

## The first attempt was INERT — and byte-identical output is what that looks like

The first paired run returned **byte-identical answers and byte-identical
reference lists on all 50 rows**. That reads as "safe". It was not a result at
all: the branch arm averaged **1,096 ms** against baseline's **16,642 ms**, i.e.
every row was an `_ENGINE_CACHE` hit and Stage-2 never re-ran.

`REGENOLD_GRAPH_SEMANTIC_LAYERS` was missing from `_engine_cache_key`. So was
R326's `REGENOLD_GRAPH_VECTOR_RECALL` — meaning any in-process A/B of vector
recall also measured nothing. Both are now keyed.

**The latency comparison is the cheap detector.** A branch arm an order of
magnitude faster than baseline did not run the engine.

## The valid run

| | OFF | ON |
| --- | --- | --- |
| non-200 / empty answers | 0 / 0 | 0 / 0 |
| answer chars (mean / median) | 999 / 944 | 1002 / 926 |
| refs per row (mean / median) | 2.62 / 2.5 | 2.64 / 2.0 |
| total refs over 50 rows | 131 | 132 |
| latency ms (mean / median) | 16,642 / 17,049 | 16,786 / 14,983 |
| Stage-2 polish fired | 31 / 50 | 31 / 50 |

**The feature fires:** 31 of 50 answers and 14 of 50 reference lists changed, at
matched latency. Stage-2 ran on the same 31 rows in both arms (the other 19 take
the `stage2_skipped_curated_authoritative` path, where the curated KB answer is
authoritative and no LLM polish happens — so the layers cannot affect them).

Cost is negligible: +144 ms mean (+0.9%), and the two extra bounded graph reads
run inside the existing timeout budget.

## Agreement with the recorded July-7 references (head level)

| | precision | recall | F1 | tp / fp / fn |
| --- | --- | --- | --- | --- |
| OFF | 0.869 | 0.785 | **0.825** | 106 / 16 / 29 |
| ON | 0.837 | 0.763 | **0.798** | 103 / 20 / 32 |

⚠ **This is a similarity measure, not a quality measure.** `jul07_refs` are the
July-7 *system's own predictions*, not gold — that run scored answer correctness
**0.500**. The official batch carries no gold answer and no gold refs at all. So a
drop in agreement with July-7 is not evidence of a regression, and a rise would
not have been evidence of a win.

What it does establish: the layers are **not** a free win on reference precision.
On the only cheap proxy available they are directionally slightly negative
(−0.027 F1, 4 fewer true positives, 4 more false positives).

## The grounded-judge gate (2026-08-10, `claude-sonnet-5` via the tunnel)

Both sidecars judged sequentially, 50 rows × 3 axes each, 861 s and 898 s.
`answer_grounding_source` is `predicted_refs_fallback_circular` on **50/50 rows in
both arms** — uniform, so the two arms are graded on identical footing, and
`gold_coverage = 0.0` means **reference RECALL is unavailable** and was never
inferred from model memory.

| axis | OFF | ON | paired flips (↑/↓) | net | sign test |
| --- | --- | --- | --- | --- | --- |
| answer correctness | 31/50 = 0.620 | 33/50 = **0.660** | 5 / 3 | **+2** | p=0.727 |
| reference correctness | 19/50 = **0.380** | 18/50 = 0.360 | 3 / 4 | **−1** | p=1.000 |
| citation faithfulness | 45/50 = 0.900 | 48/50 = **0.960** | 4 / 1 | **+3** | p=0.375 |

Supporting counts:

| | OFF | ON |
| --- | --- | --- |
| answer: correct / incorrect / unsupported / missing | 306 / **5** / 33 / 4 | 300 / **1** / 44 / 5 |
| refs: predicted / correct / wrong | 131 / 80 / **51** | 132 / 77 / **55** |
| micro reference precision | **0.611** | 0.583 |
| citations: faithful / mismatched | 144 / **5** | 148 / **2** |

**No axis is significant at n=50** (every p ≥ 0.375). But the *shape* is coherent
and points the same way on two independent axes:

* **What the layers demonstrably improve is ATTRIBUTION.** Citation faithfulness
  +3 net (mismatched 5 → 2) and outright *incorrect* answer claims **5 → 1**.
  That is exactly what the constrained sub-provision block feeds the model — the
  right paragraph of a provision it was already citing.
* **What they cost is SELECTION.** Wrong refs 51 → 55 at an essentially unchanged
  reference count (131 → 132), so micro-precision falls 0.611 → 0.583. The refs
  the layers ADD are the regulation's own neighbours: `+Article 4` (rg_010),
  `+Article 27` (rg_017), `+Article 57` (rg_038), `+Article 71` (rg_037),
  `+Article 72` (rg_045). That is the signature of the OPEN-DOMAIN blocks
  (definitions and recitals name other articles constantly), not of the
  constrained one.
* `unsupported` rising 33 → 44 while `incorrect` falls 5 → 1 is the same story:
  more context makes the model say more things it cannot point at, and fewer
  things that are wrong.

⚠ **Reference precision is the only reference axis measurable here.** With
`gold_coverage = 0.0` there is no recall term, and a precision-only measure
systematically rewards citing less — the hard-rule-#8 hazard. It is safe to read
the precision delta here only because the reference COUNT is nearly identical
between arms (131 vs 132); it would not be safe to read it across a change that
alters how many refs ship.

## R327.1 — the third arm: CONSTRAINED ONLY

The gate above split by sign, so the open-domain half was separated behind
`REGENOLD_SEMANTIC_GLOSS` and a third live arm was run and judged identically.

| arm | ans (historical) | ref pass | ref MACRO | ref micro | wrong/total refs | cite |
| --- | --- | --- | --- | --- | --- | --- |
| layers OFF | 0.880 | 0.380 | 0.675 | 0.611 | 51/131 | 0.900 |
| both halves | 0.880 | 0.360 | 0.642 | 0.583 | 55/132 | **0.960** |
| **constrained only** | 0.880 | 0.367 | 0.657 | **0.614** | **49/127** | **0.960** |

Constrained-only keeps the **entire** citation-faithfulness gain (+3 net, 5 up /
2 down, p=0.453) and returns micro reference precision to baseline (+0.003), with
2 fewer wrong refs. Running the open-domain half as well costs 0.028 micro
precision for no additional gain.

**Shipped:** `REGENOLD_GRAPH_SEMANTIC_LAYERS=1`, `REGENOLD_SEMANTIC_GLOSS=0`.

### Two corrections to the earlier reading

1. **Reference correctness never regressed.** CLAUDE.md's documented `0.673` is
   MACRO precision (mean of per-row); the `0.611` reported earlier is MICRO.
   Like-for-like the layers-OFF arm is MACRO **0.675** against the documented
   **0.673**, and ref pass rate 0.380 against 0.333. The judge's own summary
   already prints MACRO.
2. **The "+2 answer correctness" for the layers was a ruler artifact.** An
   uncommitted pass had force-failed a row on any *unsupported* claim under the
   same `verdict` key; the R318 sidecar never applied it, and the rule alone moves
   the pass rate from 0.880 to 0.620. Under the historical rule the layers are net
   **0** on answer correctness (+5/−5). Fixed in R327.1: `verdict` keeps the
   historical meaning and `verdict_unsupported_strict` is emitted alongside.

### The mechanism is generation, not plumbing

The obvious explanation for the open-domain cost — "recitals name other articles,
Stage-2 repeats them, a prose path promotes them" — is **falsified**. Only **1 of
13** added wrong refs is named inside a rendered definition/recital block; 10
appear in the layers-ON prose and in no gloss block.

And the shape is **substitution, not inflation**: 131 → 132 total refs but 4 more
wrong and 3 fewer correct. rg_020 went `['Article 74','Article 16','Article 10']`
→ `['Article 26','Article 16']` — count *down*. So the extra context shifts what
Stage-2 chooses to discuss and `_reconcile_references_to_prose` follows the prose.
That is CLAUDE.md's open item "attack GENERATION, not selection", showing up
directly. It is why the fix is to withhold the block rather than patch a promotion
path — and why no cheap trimmer would have helped.

Separately measured and rejected as a lever: rows whose answer names no
Article/Annex at all (a verbatim Art. 3 definition) account for only **2 rows / 1
wrong ref = 2%** of the 51 wrong refs. The 51 are diffuse, consistent with the
documented "tail padding" finding.

⚠ **`gold_dropped` is unmeasured.** Constrained-only ships 2 fewer judge-correct
refs (80 → 78) at 4 fewer total. With `gold_coverage = 0.0` there is no gold term
on this batch, so hard rule #8 cannot be checked here. `easyhard_ab` is what can
supply it, and that is the top follow-up.

## Verdict (as of the two-arm gate, superseded above)

**`REGENOLD_GRAPH_SEMANTIC_LAYERS` stays OFF.** The decision rule set before the
run was "a citation-faithfulness or answer-correctness win with **no
reference-precision loss**". Two of three conditions are met; the third is not.

The indicated next experiment is to **split the flag**, because the two block
families have opposite-signed effects and one switch currently bundles them:

* the **constrained** block (paragraph / point / subpoint, filtered to
  already-cited provisions) carries the faithfulness and correctness gain and
  cannot introduce a citation by construction;
* the **open-domain** blocks (definitions, recitals) are the plausible source of
  the added wrong refs.

Predicted result of constrained-only: keep +3 faithfulness and the incorrect
5 → 1, without the precision loss. That is a real, falsifiable hypothesis with a
mechanism, and it needs the same two-arm judge run to settle.

`REGENOLD_GRAPH_SEMANTIC_LAYERS` remains live, cheap (+0.9% latency),
answer-affecting, and structurally safe: the sub-provision layers are constrained
to already-cited provisions so they cannot introduce a citation, and definitions
and recitals can never be a wire citation. It is now **measured**, not merely
unmeasured — and the measurement says: helps attribution, costs selection.

Remaining work, in priority order:

1. **Split the flag and re-run this same gate** (see above). One switch currently
   bundles two effects of opposite sign.
2. **Repeat at full n with repeats.** CLAUDE.md records that small-n live A/Bs
   cannot resolve the reference axes: two runs with an *identical* baseline arm
   changed 20/40 rows' refs and sign-flipped all three reference axes. Every p
   here is ≥ 0.375, so nothing above is significant on its own.
3. **`evals.harness.easyhard_ab`** — the only harness that scores reference
   conciseness as a count-ratio against gold carrying sub-point grain, and the
   only one that supplies a recall term this batch structurally cannot.

## Reproducing

```bash
# both arms, sequentially - never two wrapper-bound jobs at once
py -3.12 -m evals.judge.grounded   --sidecar evals/bench/results/official-r327-live-ab-A-easy.ckpt.jsonl   --label r327-layersOFF --model claude-sonnet-5 --provider wrapper   --timeout 120 --concurrency 3
py -3.12 -m evals.judge.grounded   --sidecar evals/bench/results/official-r327-live-layersON-easy.ckpt.jsonl   --label r327-layersON --model claude-sonnet-5 --provider wrapper   --timeout 120 --concurrency 3
```

Keep `GROUNDED_JUDGE_STRICT_GROUNDING` OFF (the default) or answer-correctness
returns `judge_error` on every row: this batch has no gold at all.

Judged sidecars: `evals/bench/results/grounded-r327-layersOFF.json`,
`grounded-r327-layersON.json`.
