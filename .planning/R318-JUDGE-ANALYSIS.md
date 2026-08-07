# R318 — grounded-judge analysis, July-7 graded batch

100 of the 110 graded questions, replayed in-process on the July-7 lineage +
bugfixes (Claude Max wrapper + live Aura), graded by `evals.judge.grounded`
(Sonnet-5, scored against the verbatim Act text — no gold labels needed).

Sidecars: `official-r318-july7-easy-easy.ckpt.jsonl`,
`grounded-r318-july7-grounded.json`.

## Headline

| axis | R285/R287 (same batch, same judge) | now | |
| --- | --- | --- | --- |
| answer correctness | 0.500 | **0.780** | **+0.28** |
| mean factual score | 0.806 | **0.950** | **+0.144** |
| citation faithfulness | 0.764 | **0.900** | **+0.136** |
| reference correctness | 0.318 | 0.310 | flat |
| ref precision | 0.615 | **0.673** | +0.058 |
| ref recall | 0.913 | 0.893 | −0.020 |

Tone **1.000**, refusals **0**, HTTP errors **0**.

Objective churn vs the answers actually graded on 2026-07-07: refs/row
**3.94 → 2.73 (−31%)**, answer length **868 → 1223 chars (+41%)**, ref-head
Jaccard 0.698, 80% of answers changed.

## Finding 1 — the judge cannot read the tail of long answers

**8 of the 22 answer failures are labelled "truncated". All 8 are false
positives.** Checked every one against the answer text; the content the judge
says is missing is present, usually in the closing sentences.

| row | judge remark | reality |
| --- | --- | --- |
| rg_066 | "truncated before stating the Commission is the controller of the EU database" | the answer's **final sentence** is "The Commission is the controller of the EU database." |
| rg_065 | "truncated before stating tier (c) EUR 7,500,000/1% fine" | states "up to EUR 7 500 000 or 1 % of total worldwide annual turnover" |
| rg_095 | "omits Art.72(2) 'analysis of interaction with other AI systems'" | quotes it near-verbatim |
| rg_099 | "never addresses adversarial images or prompt injection sub-questions" | addresses adversarial attacks |
| rg_085 | "never addresses the toy-drone questions" | addresses drones |
| rg_037, rg_046, rg_059 | same shape | content present |

Two independent confirmations that this is an instrument artefact, not a defect:

* **Zero of 100 answers lack terminal punctuation.** Nothing is cut
  mid-sentence. "Truncated" is the judge's word for *incomplete*, and here it is
  simply wrong about what the answer contains.
* **Length predicts failure.** Answer-FAIL rows have median length **1698**
  chars; answer-PASS rows **1096**. All 8 flagged rows are 1681-2294 chars, the
  top of the distribution.

**Consequence: answer correctness 0.78 is understated. Corrected for these 8 it
is ~0.86.** This is the R305 lesson repeating (3 of 13 judge remarks were judge
false positives there) — do not tune anything against the "truncation" cluster;
there is no truncation bug.

It also means any *other* long-answer verdict from this judge is suspect,
including some of the reference "wrong" counts, since the same recency artefact
would apply.

## Finding 2 — references fail on PRECISION, and identity-based fixes cannot work

Decomposition over 253 predicted references:

```
WRONG 97      MISSING 19
rows failing with >=1 wrong    59
rows failing with >=1 missing  18
rows failing on MISSING ONLY    3
```

Pass-rate by reference count, reproducing R287 on this same batch almost exactly:

| refs | now | R287 |
| --- | --- | --- |
| 1 | 0.93 | 0.86 |
| 2 | 0.56 | 0.55 |
| 3 | 0.05 | 0.13 |
| 4 | 0.14 | 0.11 |
| 5 | 0.00 | 0.00 |

**Do NOT read that as "cut references".** R302 established it is the arithmetic
signature of a per-reference error rate under a zero-tolerance conjunctive gate,
and removing references only helps if you remove the *wrong* ones. This run
supplies fresh proof that you cannot identify them by article identity — **the
same articles appear in both the wrong and the missing lists**:

| article | wrong | missing |
| --- | --- | --- |
| Annex III | 5 | 2 |
| Article 26 | 3 | 2 |

Most-cited wrong: Article 50 (6), Article 49 (6), Article 53 (6), Article 6 (5),
Annex III (5), Annex I (4), Article 5 (4).

And we are **already dropping exactly these** relative to July-7 — most-dropped
heads were Annex III (9), Annex I (8), Article 5 (6) — yet they remain the most
frequently wrong. So the current pruning is dropping them on rows where they
were right and keeping them where they are wrong. That is R311's finding
restated (9 of 11 drift-target articles are governing somewhere).

Every reference `failure_mode` in the top cluster is over-citation:
"over-citation of parent article alongside the specific governing paragraph",
"over-citation of tangential registration provision", "over-cited
conformity-assessment-procedure article irrelevant to the classification".

The first of those is worth a look on its own: emitting the parent *alongside*
the governing paragraph is what `_reemit_parents_for_subpoints` (R87-C) does
deliberately, to fix a scoring artefact. Against this judge it costs precision.
Those two goals are in direct tension and the trade has never been measured.

### 2b. What is actually wrong — tail padding, not bad retrieval

Two measurements settle the mechanism.

**The wrong references are positionally concentrated.** Wrong-rate by position in
the emitted list:

| rank | wrong / total | rate |
| --- | --- | --- |
| 1 | 20 / 93 | **0.22** |
| 2 | 35 / 78 | 0.45 |
| 3 | 32 / 53 | **0.60** |
| 4 | 6 / 15 | 0.40 |
| 5 | 7 / 8 | 0.88 |

Retrieval is not the problem: the FIRST reference is right 78% of the time. The
THIRD is wrong 60% of the time.

**The collapse is a cliff, not arithmetic.** Against an independent per-reference
error rate of 0.327:

| refs | observed | independence predicts |
| --- | --- | --- |
| 1 | **0.93** | 0.67 |
| 2 | 0.56 | 0.45 |
| 3 | **0.05** | 0.30 |
| 5 | 0.00 | 0.14 |

1- and 2-reference rows beat independence; 3-reference rows are six times worse
than it predicts. That discontinuity lands exactly on the R77-I6 QA budget of
**3**, and 38 of 100 rows sit at exactly 3 references — the modal bucket, passing
at 0.05, and supplying **36 of the 62 reference failures (58%)**.

So the system locates the governing provision well and then fills the remaining
budget with tangential material, and a zero-tolerance gate turns each filler into
a failed row. 34 of the 62 failing rows have **exactly one** wrong reference.

**But truncation is NOT the fix, and this is where R142.1 went wrong.**
Deterministic counterfactual over the recorded rows (zero generation variance):

| cap | pass rate | correct kept | wrong kept |
| --- | --- | --- | --- |
| none | 0.37 | 149 | 104 |
| 3 | 0.40 | 137 | 87 |
| 2 | **0.55** | **116** | 55 |
| 1 | 0.78 | 73 | 20 |
| oracle (drop only wrong) | **1.00** | **149** | **0** |

Capping at 2 destroys **33 correct references to remove 49 wrong ones**. That is
precisely the trade R142.1's positional clamp made when it lost a live pairwise
11-0 (p=0.001) — it buys a binary gate at the cost of recall, and recall is
scored.

The oracle row is the important one: **all of the headroom is in identifying
which tail reference is wrong, not in cutting the tail.** And the two known
approaches are already refuted — a prose-driven pruner is a structural no-op
(R298: 86% of wrong refs ARE described in the prose) and identity blocklists
fail (R311, and Finding 2 above: the same articles appear in both lists).

### 2c. The 0.31 headline overstates the damage

The judge's reference gate is zero-tolerance conjunctive: one wrong reference
fails the row. The competition does not score that way — it uses
`reference_correctness_loose` (Jaccard) and `_strict` (F1), both graded.

The continuous measures here are **precision 0.673 / recall 0.893 / F1 0.768**.
Quote F1 alongside the pass rate; 0.31 alone reads as broken when the reference
set is mostly right. R302 made this same correction (0.349 -> 0.717 under partial
credit).

## Finding 3 — Component D is adding references from prose

Observed repeatedly during the replay:

```
Component D Grounding Guard: Prose cited <X> which was missing from
reference_bases, but exists in ARTICLE_EXISTENCE. Dynamically augmenting
references list.
```

for Annex I, Annex III, Annex XI, Annex XII, Article 16, Article 73. This is the
route **adding** references because the prose named them — on the axis whose
measured weakness is precision, not recall. It is a live candidate for the
over-citation above and deserves its own A/B.

## Finding 4 — the real answer-side failure is omission, not error

Claim-level across 100 rows: **missing 38, unsupported 25, incorrect 8.**
12 of the 22 answer failures are missing-only; 6 involve anything incorrect.
Mean factual score **0.950**. The system is accurate and incomplete, which is
the same shape R308 recorded (omission 24 rows vs fabrication 5).

## What NOT to do next

* Do not chase the truncation cluster. It does not exist (Finding 1).
* Do not add an identity blocklist for Annex III / Annex I / Article 5 / Article
  50. They are governing on other rows in this very batch (Finding 2).
* Do not apply a positional or top-N reference clamp. R142.1 lost a live
  pairwise 11-0 (p=0.001) doing exactly that.
* Do not read the ref-count collapse as licence to cut references (R302).

## Ranked next levers

1. **Re-grade with a judge that reads long answers.** Everything downstream of
   the 0.78 is uncertain until the length artefact is removed — chunk the answer,
   or assert the quoted-missing content is genuinely absent before failing a row
   (the `legal_v2` quote-or-retract rule exists for exactly this).
2. **A/B the Component D grounding augmenter** (Finding 3). It is a concrete,
   env-gated, precision-affecting mechanism, and nobody has measured it against
   this judge.
3. **Measure the `_reemit_parents_for_subpoints` trade** (Finding 2) — parent
   plus governing paragraph is a deliberate choice that this judge penalises.
4. Answer-side: target omission, not correctness. The factual score is already
   0.950.

## Caveats

* 100 of 110 rows; the batch was stopped deliberately.
* The comparison against R285/R287 is same-batch and same-judge, but the judge
  is non-deterministic and this run is 100 rows against their 110.
* `gold_coverage = 0.0` — regenold's official gold was never published, so
  reference *precision* here is text-grounded while *recall* is the judge model's
  reading. Do not compare this recall figure across datasets.
* The +41% answer length is **not** attributable to R318; it spans the whole
  bugfix stack since July 7, and R315 explicitly uncapped truncation levers.
  Conciseness is the one axis the official scorecard says we lead.
