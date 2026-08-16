# R352 — the Annex anchor gap is real; the obvious fix is refuted

**Date:** 2026-08-16 · **Method:** exact computation over the whole 297-row
probe pool, no LLM, no sampling · **Status:** broad remedy REFUTED and not shipped; the one surviving
narrow hypothesis was independently replicated and shipped by R353 as
`REGENOLD_RISK_CLASS_ANNEX` (default OFF)

---

## Summary

Chasing the R350-vs-R351 KG-citability fork turned up a retrieval gap that
looked more valuable than the fork itself: **18 gold references in the probe
pool are reachable only through the cross-reference graph, never through the
keyword map.** They are overwhelmingly annexes — 11 × `Annex III`, 5 × `Annex I`
— on "is X high-risk?" questions, where those annexes *are the operative law*.

The obvious remedy — anchor the risk-classification triad (`Art. 6` +
`Annex III` + `Annex I`) whenever a question asks for a risk classification —
was measured before being written up. **It is 12% precise, and `Art. 6`
specifically is 0% precise.** It does not ship.

This document records the gap, the refutation, and the one narrow candidate
that survives, so the next person does not re-derive the same wrong fix.

## 1. The gap, measured exactly

Computed over all 297 probe rows by resolving each row's keyword anchors
against its gold, then asking which gold refs are reachable only via
`kb_xrefs.cross_refs_with_reason`:

| | |
| --- | --- |
| rows where the KG pool expands | 169 / 297 |
| gold refs reachable ONLY via a KG neighbour | **18**, on 16 rows |
| what they are | `Annex III` ×11, `Annex I` ×5, `Annex XIII` ×1, `Annex IV` ×1 |

The rows are not exotic. They are the most ordinary compliance question there
is:

```
lower_risk_v149:lr_spam_filter        "Is an AI spam filter regulated under the AI Act?"
lower_risk_v149:lr_chatbot            "Is a customer service chatbot high-risk under the AI Act?"
lower_risk_v149:lr_translation        "Is a translation AI high-risk under the AI Act?"
lower_risk_v149:lr_music_recommender  "Is a music recommendation AI high-risk under the AI Act?"
lower_risk_v149:lr_image_generator    "Is an AI image generator high-risk under the AI Act?"
live_answers:la_q46                   "Is an AI system that recommends recipes high risk?"
medtech:grb_01                        "Is AI software that detects melanoma ... high-risk?"
```

On every one of them the engine retrieves neither `Annex III` (the high-risk
use-case list) nor `Art. 6` (the classification rules) nor `Annex I` (the
harmonised-product list). To answer "is my system high-risk", it never fetches
the list of things that are high-risk.

## 2. Why this looked more valuable than the fork it came from

The KG-neighbour supplement that R351 tiers and R350 projects out reaches these
same 18 gold refs — but it reaches them by proposing **1,502 neighbours** across
281 rows. Exactly:

```
KG neighbours proposed   1,502
   ...that are gold         18
   ...that are not       1,484
PRECISION                  1.2%
```

`Art. 98` — *Committee procedure*, comitology — is proposed **50 times**.

So the graph knows the right answer is in there somewhere and pays ~82 wrong
references to say so. Getting the same 18 refs from the anchor layer at high
precision would be strictly better: same recall, none of the noise, and it
attacks retrieval rather than the ranker — which is where `CLAUDE.md` says the
remaining headroom is.

That was the hypothesis. It is wrong.

## 3. The refutation

Trigger: a question asking for a risk classification (`is/are/does … high-risk |
prohibited | regulated | qualify as | classified as …`). Fires on **99 of 297
rows (33%)**. For each triad member, over those rows, counting exactly how often
it is gold and how often it is not:

| provision | gold gained | non-gold added | already had | precision |
| --- | ---: | ---: | ---: | ---: |
| `Art. 6` | **0** | 61 | 0 | **0%** |
| `Annex III` | 17 | 54 | 21 | 24% |
| `Annex I` | 8 | 74 | 9 | 10% |
| **TOTAL** | **25** | **189** | | **12%** |

Three things to take from this:

**`Art. 6` is 0% precise — it is never gold on a classification question.**
This is the most counter-intuitive number in the table and it is the one to
remember. Article 6 *is* the classification rule; a lawyer answering "is this
high-risk?" reasons through it. But the graded gold does not cite it — the gold
cites the *list* (`Annex III`), not the *rule that points at the list*. Anchoring
Art. 6 would add 61 wrong references and gain nothing at all.

**The blanket triad rule is 12% precise.** Better than the KG supplement's 1.2%,
and still ~8 wrong references per right one. On the axis this repo has left to
win — over-citation, where an oracle dropping every non-gold ref gains Ref
Strict +0.215 — a 12%-precise addition is a regression wearing a feature's
clothes.

**The trigger is too broad.** It fires on 99 rows but the gain concentrates in
about 16. Most fired rows "would gain []" — they already have what they need.

## 4. What survives

One narrow candidate, and it is a hypothesis, not a plan:

> `Annex III` anchored **only** on the "is [ordinary consumer software]
> high-risk?" shape — the `lower_risk_v149` family and its live-answers
> equivalents — where the correct answer is *"no, and here is the list it is not
> on."*

At 24% over the broad trigger, `Annex III` is the only member with a signal at
all, and its gains cluster in exactly that shape. A trigger fitted to those rows
could plausibly clear 60-70%.

**UPDATE — R353 did exactly that, and it beat the estimate.** The narrow rule
was independently replicated over the same 297-row pool before any engine code:
it fires on 11 rows, gains `Annex III` where it is gold-but-missing on **7**
(spam filter, music recommender, chatbot, translation, image generator, clinic
scheduling, recipes) and adds **0 non-gold — 100% precision**. Prohibition,
technical-documentation and medical shapes are excluded from the trigger. It
ships as `REGENOLD_RISK_CLASS_ANNEX`, default OFF, appended (never prepended) so
the parse-level rerank decides its final position; the live A/B with all judge
axes is the open measurement. Independent replication put `Annex I` at 11% where
this page measured 10% — a trigger-wording difference, not a contradiction, and
both are far under any shippable bar.

Explicitly NOT recommended:
* anchoring `Art. 6` on classification questions — measured 0%, refuted;
* anchoring `Annex I` — 10%, and its gold rows are medical-device questions
  where the real anchor is the MDR bridge, not the annex;
* widening `cross_refs` admission to catch these — that is the 1.2% path this
  whole investigation came from.

## 5. The lesson, which is the durable part

This is the sixth "obviously right" retrieval fix this repo has measured and
killed (the five over-citation trimmer families are in `CLAUDE.md`'s
do-not-re-propose list). The pattern repeats: a change that is *legally* correct
— of course Article 6 governs high-risk classification — is not necessarily
*gold*-correct, because the gold cites what a practitioner would cite, not what
the statute's logic traverses.

**A retrieval proposal owes its exact gold impact before it owes an A/B**, and
that number is usually computable in seconds without an LLM. This page cost one
script and no API calls; the A/B it replaced would have cost 594 live requests
and ~2.5 hours to answer a question that was never about ranking.

---

**Scripts:** the oracle and blast-radius computations are reproducible from
`evals/harness/probe_set.py` + `app.engines.cohere_rerank.build_kg_candidate_pool_with_reasons`;
neither needs network. **Related:** the R350/R351 fork itself is
`REGENOLD_RERANK_KG_NONCITABLE` (see `CLAUDE.md`'s flag table).
