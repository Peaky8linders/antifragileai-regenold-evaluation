# R369 — Root-Cause Analysis: Low Answer & Reference Correctness (81 live rows)

**Run:** R365 live batch (81 rows, bedrock, Qwen judge, base arm = merged R353.1+R366+R366.1+R367 engine, R368 supplements OFF)
**Judge (base arm):** answer_correctness 43/77 pass (**56%**), reference_correctness 30/79 pass (**38%**), answer_faithfulness 31/81 (38%), citation_faithfulness 75/81 (93%), answer_relevancy 72/81 (89%).
**Evidence:** `evals/bench/results/checkpoints/dynamic-ab-r365-live-FINAL-81rows-7axes.json` (per-row answers, refs, deterministic scores) + Antifragile expert review of the 20 gold questions + `scratch/r369_classified.json` (per-row failure classes).

---

## 1. The failure surface, quantified

Per-row classification at **article-head level** (the deterministic scorer's own projection — so these are real, not judge-presentation artifacts):

| Class | Rows | Meaning |
|---|---|---|
| CLEAN (head-exact) | 28 | gold and pred heads match exactly |
| OVER (noise only) | 17 | pred adds non-gold heads |
| UNDER (miss only) | 12 | pred drops gold heads |
| BOTH (miss + noise) | 15 | drops gold **and** adds noise |
| WRONG (zero overlap) | 3 | pred shares no head with gold |
| EMPTY (no refs) | 6 | incl. 2 benign (greeting rows) + 4 scope-gate refusals |

- **34/81 rows drop at least one gold head** (recall side), **35/81 rows emit at least one non-gold head** (precision side), **25/81 rows carry granularity duplication** (same head cited at 2+ granularities, e.g. `Article 26.7` + `Article 26`).
- Top missed gold heads: **Annex III (10), Article 50 (7), Article 6 (5), Annex I (4), Article 25 (3)** — exactly the R368 supplement targets (still flag-OFF).
- Top noise heads: **Article 50 (6), Article 53 (5), Annex I (4), Article 6/Annex III/Article 9/Article 3/Article 49 (3 each)**. Article 50 and Annex III are simultaneously top-miss *and* top-noise — the anchor logic for both is mis-calibrated in both directions.

## 2. Root causes

### RC-1 — Prose-driven citation over-emission (biggest ref_corr lever, ~35 rows)
The answer generator cites **every article its prose mentions**, not the articles the question actually targets. `la_q4` (medical-device high-risk): prose lists the Chapter III §2 stack ("risk management (Article 9), data governance (Article 10), technical documentation (Article 11), transparency (Article 13)") → 7 refs vs gold 3 (Article 6, Annex I, Article 43). The prose is correct; the citation set is inflated. Same shape on `la_q5` (Article 13/14/15 vs gold Article 13), `la_q74`, `la_q21`, `la_q79`, `la_q67`. This is what `ref_conc`<0.5 on 38 rows measures and what the judge's ref_corr fails on.

### RC-2 — Anchor cascade without gating (2 worst rows: la_q47, la_q22)
"Explain the risk categories" fires the Article 5 anchor + the Article 6/Annex III anchor + the Article 50 anchor + the GPAI anchor simultaneously → **11 refs emitted for a 1-ref gold** (`Article 5`). The answer prose is genuinely good (correctly maps all four tiers + GPAI), but the citation set is the union of every anchor that fired. No anchor-conflict resolution exists.

### RC-3 — Wrong-article retrieval (3 zero-overlap rows + several partial)
`la_q40` (technical-documentation/hardware): pred `Annex VII` (conformity certificate, whose text contains "technical documentation assessment certificate") vs gold `Annex IV` + `Article 11`. `la_q35` (MSA reclassification): pred `Article 74`/`20.1` vs gold `Article 79`/`80`/`Annex III`. `la_q73`: pred `Article 43.3` vs gold `Article 6`/`Annex I`. The retriever surfaces lexically-adjacent articles; the R364.5 guard only stops *invented* annex numbers in query expansion, not wrong-article ranking.

### RC-4 — Incomplete citation of own prose (recall side, distinct from RC-1)
The citation emitter misses gold refs the prose itself already covers: `la_q16` (penalties) prose explains Art 99(4) transparency ceilings but never cites `Article 50` (gold has it); `la_q3` (high-risk definition) prose covers the Art 6(3) derogation but never cites `Article 49` (gold: registration duty under Art 49(2)); `la_q87`/`la_q7`/`la_q31`/`la_q81` answer classification but never cite the `Article 50` duties they discuss. Opposite failure mode to RC-1: the citation selector is not coupled to the prose content at all.

### RC-5 — Scope-gate refusals → empty answers (4 rows)
`la_q60`, `la_q63`, `la_q91` (VLOP content-moderation transparency) and `la_q92` are refused by the R49-B DSA scope gate → empty `pred_refs`, gold `Article 50` dropped. The R368 scope rescue fixes these but is **flag-OFF**.

### RC-6 — Granularity duplication at emission (25 rows, judge-visible)
`Article 50.1` + `Article 50.3`, `Article 6.1` + `Article 6.2`, `Article 11.1` + `Article 11`, `Annex IV` + `Annex IV.2`… The deterministic scorer normalizes to heads, so these look clean there — but the judge's ref_corr shows the raw list and counts the second entry as an extra ref. A chunk of the gap between deterministic scores (high) and judge ref_corr (38%) lives here.

### RC-7 — Answer-generation quality (ans_corr 56%)
Four concrete generation defects, confirmed in the live answers and the expert review:
1. **Partial enumerations** — Article 5 prohibitions truncated (expert Q1: 5 of 8; Q2: 3 of 8).
2. **Role attribution errors** — Art 50(3)/(4) obligations placed on providers instead of deployers (expert Q5, Q18).
3. **Narrow single-path answers** — `la_q53` (customer-support chatbot) answers "limited risk + Article 50" while gold expects the full decision tree (Annex I/III high-risk route, GPAI 51/53/55, deployer-modification 25).
4. **Generic rules without case application** — expert Q14/Q20 (X-ray, robotic surgery): states the Article 6(1) rule, never applies it to the device class or names the MDR notified-body route.

### RC-8 — Long, synthesizing answers (faithfulness 38%)
Answers average 684 chars (17/81 > 900). citation_faithfulness is high (93%) but answer_faithfulness is low (38%) — the generator adds policy-level guidance beyond the retrieved chunks (e.g. GDPR pointers, compliance advice). Faith failures are prose-level, not citation-level.

## 3. Impact map → fix order

| Fix | Recoverable | Source |
|---|---|---|
| **R368 supplements ON** (Annex III + Article 50 triggers + scope rescue) | 10 gold-head recoveries on 10 rows (incl. 4 empty rows) — the entire miss list above (RC-4/RC-5 + Annex III/50 misses) | measured pre-implementation, 100% trigger precision |
| **Citation emission rework (RC-1/RC-6)**: dedupe at head level keeping the most-specific form; cap refs to anchors that fired + gold-adjacent; separate "prose mention" from "citation" | recovers most of the 35 noise rows + 25 dup rows → the largest single ref_corr gain | post-processing, no engine change |
| **Anchor conflict resolution (RC-2)**: when the risk-tier intent fires, emit the tier map but only the primary anchor refs | la_q47/la_q22 (2 worst rows: 11→~3 refs) | anchor layer |
| **Retrieval precision on documentation/assessment terms (RC-3)** | la_q40, la_q73, la_q35 + partial-noise rows | retrieval layer |
| **Generation guidance (RC-7)**: full enumerations, role-accurate Art 50, decision-tree structure, apply-the-rule-to-the-case | ans_corr 56% → target 70%+ | prompt layer |

**Bottom line:** the ref_corr 38% is ⅔ precision (over-emission RC-1/RC-2/RC-6) and ⅓ recall (misses RC-4/RC-5); the ans_corr 56% is generation-side (RC-7/RC-8) plus the wrong-article retrieval minority (RC-3). The cheapest, highest-ROI moves are the emission post-processor (RC-1+RC-6 — pure post-processing, zero retrieval risk) and flipping R368 ON (already measured at 100% trigger precision), ahead of any retriever or prompt surgery.
