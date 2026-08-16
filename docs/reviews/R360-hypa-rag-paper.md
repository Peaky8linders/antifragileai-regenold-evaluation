# R360 — HyPA-RAG paper deep-dive: cross-reference, gaps, and fixes

**Source paper:** HyPA-RAG: A Hybrid Parameter-Adaptive Retrieval-Augmented
Generation System for AI Legal (Kalra et al.; LL144 / Law 144 corpus).
**Engine repos:** regenold-eu-ai-act-rag (main) + antifragileai-regenold-evaluation (eval).

---

## 1. The paper's methodology (distilled, from the full 19-page text)

HyPA-RAG classifies each query into 2- or 3 complexity classes and maps the
class to four adaptive parameters:

| Param | Meaning |
|---|---|
| `k` | top-k chunks retrieved |
| `Q` | number of query rewrites |
| `K` | max keywords for knowledge-graph retrieval |
| `S` | max knowledge-graph sequence/depth |

Two retrieval lanes (vector + knowledge graph) are fused, and an optional
cross-encoder reranker (`bge-reranker-large`) reorders the fusion output.
Evaluation metrics: **Faithfulness (#1)**, **Answer Relevancy (#2)**,
Absolute Correctness (1-5), Correctness (threshold 4.0).

### The paper's own headline numbers (Table 2 + ablation Tables 8/9)

| Config | Faithfulness | Answer Relevancy | Correctness (≥4.0) |
|---|---|---|---|
| LLM only (GPT-4o-mini) | 0.3463 | 0.6319 | 0.4572 |
| Fixed k=10 (best fixed) | 0.8480 | 0.7917 | 0.7658 |
| **PA: k,Q (2-class)** | **0.9044** | 0.7910 | 0.8104 |
| HyPA: k,Q,K,S (2-class) | 0.8328 | 0.7800 | 0.7770 |
| HyPA: k,Q,K,S (3-class) | 0.8465 | 0.7734 | 0.7918 |
| **k,Q + reranker** (ablation) | **0.9098** | — | 0.8178 |
| **HyPA k,K,S,Q + reranker** | — | — | **0.8402** |

**Three facts that matter for this repo:**

1. **The knowledge-graph parameters (K, S) do NOT drive faithfulness.**
   Adding them to the adaptive router *hurts* it: PA k,Q = 0.9044 vs
   HyPA k,Q,K,S = 0.8328. The paper's own "Hy" is the *weakest* part of the
   recipe on the headline metric.
2. **The reranker is the star.** `k,Q + reranker` = 0.9098 faithfulness
   (highest in the paper) and `HyPA + reranker` = 0.8402 correctness
   (highest). Every top config in the ablation includes the reranker.
3. **Adaptivity beats fixed-k on faithfulness**, but the win is in `k,Q`
   (retrieval depth + rewrite count), not in KG depth/keywords.

---

## 2. Cross-reference vs the current implementation

### What already matches the paper

- **The HyPA parameter table is ported** — `app/engines/query_complexity_router.py`
  carries the 2-/3-class mappings for `k, Q, K, S` and is **wired** into the
  live path (`_graph_rag_impl.py:9431` HyPA integration; consumed by
  `sufficient_context.py` for `query_rewrites`, `kg_context.py` for `kg_depth`,
  `graph_semantic.py` for ANN fanout). Post-R329-review fixes landed; the
  integration is covered by `tests/test_hypa_rag_integration.py` (end-to-end)
  and `tests/test_r329_adaptive_param_wiring.py`.
- **Hybrid RRF fusion exists** — `hybrid_rrf_retriever.py`
  (`REGENOLD_HYPA_RRF_RETRIEVAL`).
- **A reranker module exists** — `cohere_rerank.py`
  (`REGENOLD_COHERE_RERANK`).

### The gaps (adversarial, grounded)

**GAP-1 — the paper's metrics #1/#2 did not exist at the answer level
(eval side).** The judge had no reference-free Faithfulness axis and no
Answer Relevancy axis. Every prior axis (`answer_correctness`,
`reference_correctness`, `citation_faithfulness`, `answer_conciseness`,
`answer_crag_fine`) needs gold refs or a gold answer. The **no-gold half of a
benchmark was unscorable** — exactly the half the paper's metric #1/#2 exist
to score. **Fix (shipped):** two new opt-in axes in `evals/judge/legal_v2.py`
— `answer_faithfulness` (Ragas faithfulness = supported/total, grounded only
on the cited provisions' verbatim text; pass iff 1.0) and `answer_relevancy`
(Ragas relevancy on the 0-1 continuum, question+answer only; pass iff ≥0.5).
Both are reference-free by construction (the `_prepare` contract asserts the
gold answer never leaks into the prompt — tested).

**GAP-2 — the paper's winning component (the reranker) is default OFF and
has never been measured with a cross-encoder.** `REGENOLD_COHERE_RERANK`
defaults OFF for three documented reasons: (a) R325 measured a *lexical*
reranker that did not beat the engine's own rank (the module itself flags
this as "a genuinely different arm" from a cross-encoder); (b) external
egress of partner questions to Cohere; (c) R329's ungated default-ON change
damage (Ref Conciseness −0.209). The paper used **bge-reranker-large, a
cross-encoder** — the exact arm R325 never tested. Per Table 8/9, the
reranker is the single highest-value component (0.9098 faithfulness, 0.8402
correctness). The R329 measurement (router *without* the reranker) is
consistent with the paper's own Table 2 — HyPA's KG parameters alone
underperform — so R329 does **not** refute the reranker arm.

**GAP-3 — no judge-vs-expert validation.** The paper validates its judge
against human judgments (Appendix A.8, Spearman). The attached 20-row
expert review (`Antifragile AI expert review.txt`) is exactly that
validation set, and it had never been run through the judge. **Fix
(shipped):** the R360 validation run scores the 20 expert rows on
faithfulness + relevancy (+ crag_fine where gold exists) and reports
judge-vs-expert agreement.

---

## 3. What shipped

### Eval side (this worktree)

1. **`evals/judge/legal_v2.py`** — two new opt-in reference-free axes:
   - `answer_faithfulness` — HyPA metric #1. Decompose the answer into
     claims; each claim SUPPORTED/UNSUPPORTED against the verbatim text of
     the *predicted* refs only (never gold — asserted by test). faithfulness
     = supported/total; pass iff 1.0 (Ragas default threshold; one
     unsupported claim is a hallucination-risk flag).
   - `answer_relevancy` — HyPA metric #2. Question + answer only; relevancy
     on the 0-1 continuum; pass iff ≥0.5 (Ragas default).
   - Both wired into `_prepare`, `_AXIS_KEYS` (structured-carrier-only —
     a failure_mode-only reply is unscorable, never a silent pass),
     `_postprocess`, `_NUMERIC_FIELDS`, `_aggregate`
     (`mean_faithfulness`, `unsupported_rows`, `mean_relevancy`), `_fmt`.
   - Kept **out of the default `AXES`** — standard 4-axis runs are
     byte-identical.
2. **`tests/test_r360_hypa_ref_free_axes.py`** (16 tests) + the R350
   `_AXIS_KEYS` completeness gate updated for the two new axes.
3. **`scratch/r360_build_validation.py`** — parses the two attached txt
   files into a 40-row sidecar:
   - 20 expert rows (live Lexy answers + human expert verdict),
     10 of which carry gold_answer from `graphrag_evals_dataset.txt` B.2.1
     (making crag_fine scorable);
   - 20 no-gold rows — **two** GraphReader outputs over the same 10
     questions (B.3.1 `base` vs B.3.2 `af_only` — a built-in A/B the
     reference-free axes can now score).
4. **`scratch/judge_r360_hypa.py`** — Bedrock-only judge
   (sonnet-4-6, no thinking), `P2P_GRAPH_RAG_PROVIDER=bedrock`,
   `REGENOLD_BEDROCK_WRAPPER_FALLBACK=0` via `live_ab_env` — the
   Claude-Max cloudflared tunnel is never touched. Resume-aware.

### Engine side (main repo) — analysis only, no default flips

The repo's own measured history + the paper's data converge on one
recommendation: **the reranker is the highest-value unmeasured arm, and the
measurement instrument it needs is exactly the reference-free axes shipped
here.** No defaults were flipped this round — R329's lesson is that an
ungated default-ON retrieval change without a measured win is how the bench
regresses. The next live A/B should be:

1. `REGENOLD_COHERE_RERANK=1` alone, on the 81-row live bench + the
   no-gold half, graded with `answer_faithfulness` / `answer_relevancy`
   (the paper's metrics #1/#2 — now available) plus the gold-bound axes.
   This is the paper's faithfulness-champion config (k,Q + reranker analog).
2. Only if that nets positive: add `REGENOLD_HYPA_ADAPTIVE_ROUTER=1`
   (the paper's 0.8402-correctness config). The paper itself shows the KG
   parameters don't drive faithfulness, and R329 measured the router-alone
   ref-axis regression — so the router is A/B'd *after* the reranker win is
   banked, never before.
3. The Cohere egress residency question is real but orthogonal to
   *measurement*: the A/B can run on the public 81-row bench without
   partner PII.

---

## 4. Live results (Bedrock only)

Judge: claude-sonnet-4-6 via Bedrock, no thinking, 40 rows, 90 axis calls,
zero errors (9 first-pass `unbalanced_json` on long no-gold answers were
fixed by raising the judge output budget 700 -> 2000 tokens; re-judged
clean). Full per-row report: `docs/R360-hypa-ref-free-judge-report.md`.

### 4.1 Judge-vs-expert (GAP-3 — the 20 expert rows)

| Axis | n | agreement | both-pass | both-fail | judge-pass / expert-fail | judge-fail / expert-pass |
|---|---|---|---|---|---|---|
| answer_faithfulness | 20 | 0.55 | 1 | 10 | 2 | 7 |
| answer_relevancy | 20 | 0.50 | 8 | 2 | 10 | 0 |
| answer_crag_fine | 10 | 0.60 | 2 | 4 | 4 | 0 |

What the agreement matrix reveals (and why it is honest, not a bug):

* **Relevancy is a weak discriminator of expert fails** — the expert fails
  answers that are *relevant but incomplete or legally wrong* (10 rows the
  judge passes). That is by design: relevancy measures "did it address the
  question", not correctness — completeness/wrongness is graded on
  crag_fine/faithfulness. The GAP-3 run quantifies this instead of
  assuming it.
* **Faithfulness is stricter than the expert** (7 judge-fail / expert-pass)
  because it is grounded ONLY on the cited provisions' verbatim text: an
  answer the expert reads as "correct on substance" can still contain
  claims its own citations do not entail.
* **crag_fine (gold-bound) tracks the expert best of the three (0.60)** on
  the 10 rows where gold exists — the gold-answer rubric is the closest
  proxy for the human expert, but it is blind to errors the gold answer
  does not mention (e.g. expert_q02's "by public authorities" social-
  scoring misstatement is not in the B.2.1 gold, so crag_fine scores +0.5
  PARTIAL_CLEAN while the expert fails it).

### 4.2 GraphReader base vs af_only (no-gold half — GAP-1 closed)

| Metric | base | af_only | delta |
|---|---|---|---|
| Faithfulness (mean) | 0.505 | 0.592 | **+0.087** |
| Relevancy (mean) | 0.900 | 0.890 | −0.010 |

Both variants score 0/10 on the strict pass gate (faithfulness == 1.0). The
means are far below the paper's reported 0.85-0.91 because (a) these are the
paper's *baseline* GraphReader outputs, not its adaptive systems, and (b)
faithfulness here is judged against the answer's **inline-cited provisions
only** (the Ragas definition: claims must be entailed by the retrieved
context), which is stricter than the paper's full-KB-context grounding.

**Documented limitation:** the judge's provision-text resolver covers
Articles and Annexes only — recital text is not resolvable (`provision_exists('Recital 110') == False`, consistent with every prior axis).
Answers whose claims rest on recitals (the B.3 outputs cite Recitals 12/27/55/110
text) get those claims judged unsupported, which lowers the absolute
faithfulness numbers conservatively. The base-vs-af_only delta is unbiased
(identical treatment on both arms), and the direction of the bias is
known and one-sided.

### 4.3 What this buys the engine loop

1. The no-gold half of a benchmark is now scorable (the R360 run is the
   first to score it) — this is the metric the paper uses to drive its
   parameter search.
2. The expert-vs-judge matrix calibrates the axes: crag_fine for gold rows,
   faithfulness for hallucination-risk detection, relevancy only as a
   coarse screen.
3. The concrete next measurement is the engine A/B recommended in §3:
   `REGENOLD_COHERE_RERANK=1` alone, graded with these axes (plus the
   gold-bound ones) on the 81-row bench — the paper's faithfulness
   champion (k,Q + reranker = 0.9098) vs the current default-OFF state.

## 5. Regressions

- `tests/test_r360_hypa_ref_free_axes.py` + `test_r359_crag_fine_axis.py`:
  33/33 pass.
- `test_legal_v2_judge.py` + `test_r350_review_fixes.py` (with the
  `_AXIS_KEYS` gate updated): 70/71 → all green after the gate update.
- Full eval `tests/` sweep: 6631 passed, 35 skipped, 6 failed — every
  failure is a pre-existing untracked main-repo test copy running against
  the older eval-worktree engine / dead wrapper (confirmed at HEAD; none
  reference `legal_v2`). Standard 4-axis judge runs are byte-identical
  (new axes are opt-in).
