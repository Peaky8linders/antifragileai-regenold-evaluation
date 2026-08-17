# R364.5 — Query expansion guard: market research + surgical-strip relaxation

**Date:** 2026-08-17 · **Status:** implementation + tests shipped; 60-row
Bedrock A/B in progress

---

## 1. Market research — rerankers for legal RAG (what is proven)

External evidence (all sources cited; no tunnel quota used — Bedrock only):

| approach | evidence | real-world read |
|---|---|---|
| **Cross-encoder two-stage retrieval** | Pinecone rerankers guide (two-stage retrieval is the standard first fix for suboptimal RAG) | The family is proven; the open question is model + wiring |
| **ModernBERT-based cross-encoder for statutory retrieval** | Springer *Artificial Intelligence and Law* 2026 — "Neural reranking for UK statutory retrieval": ModernBERT cross-encoder **outperforms other open rerankers** on 100 expert-validated UK statutory queries | Most recent domain-specific evidence: **domain-tuned cross-encoders win on legal/statutory text** |
| **Cross-encoder reranker on legal RAG benchmarks** | arXiv 2504.01840 (legal RAG evaluation tool): cross-encoder reranker = best on civil/public legal subtasks | Cross-encoders > bi-encoders/lexical on legal retrieval |
| **General reranker leaderboard** | Cohere Rerank 3.5/4, BGE-Reranker-v2-M3, Qwen3-Reranker, MonoT5 (2025-2026 benchmarks) | Cohere is the top proprietary API; BGE-v2-M3 the top open-weight |
| **LLM listwise reranking (RankGPT)** | Strong on general benchmarks but 10-100x the latency/cost of cross-encoders | Not justified for a p50-latency-weighted legal endpoint |

**Our own measured evidence on THIS corpus (stronger than any external
benchmark for this decision):**

* R340 rerank alone — wash (gold 17→17)
* R346 live-rerank A/B (rerank-v3.5, n=60) — ref_loose −0.008, ref_conc +0.017,
  all UNDERPOWERED
* R350/R350.2 rerank × KG × expansion — gold-drop vetoes
* R353 deep review — **Cohere rerank is POINTWISE**: it cannot reorder the
  engine's anchors against each other, so on top of an already-strong
  deterministic rank its only role is as a PRECISION guard over deterministic
  RECALL supplements (the R353 Annex III anchor, 7/0 exact gold impact).
* R353.1 true-gap analysis — the real reference-correctness levers are
  gold-but-not-anchored heads (Article 6 ×31, Annex III ×26, Article 50 ×18,
  Article 5 ×15, Annex I ×12…), which are RECALL-side deterministic problems,
  not reranker-model problems.

**Decision on the reranker: no model churn.** The current wiring (R347/R348:
KG-candidate pool + intent/risk query context + R351 anchor tiering) is already
the proven architecture. Flipping `REGENOLD_COHERE_RERANK` ON is not supported
by our own A/B data; switching to a different cross-encoder would not change
the pointwise limitation the review identified. The reranker stays OFF by
default, reserved as the precision guard for recall supplements.

## 2. Market research — query expansion for legal RAG

| approach | evidence | read for this system |
|---|---|---|
| **Corpus-steered QE with LLMs** | EACL 2024 (Mackie et al.) — expansion grounded in corpus statistics beats free-form | Expansion must be grounded in what the corpus supports, not invented |
| **Retrieval-feedback-grounded multi-query expansion (RFG)** | SciTePress 2025 — PRF-grounded LLM expansion | Retrieval feedback (the seed refs) should constrain the expansion |
| **HyDE / Query2doc** | Consistent gains on dense retrieval; HyDE improves semantic alignment, not recall | Not needed — the engine already has dense + graph + BM25 lanes; the gap is REF invention |
| **LLM multi-query + RRF (RAG-Fusion)** | Standard production practice | Already implemented (R341) |

The consistent lesson: **expansion quality is a grounding problem, not a
generation problem.** The R364.1 guard (whole-paraphrase drop) over-corrected:
it grounded expansion by throwing away paraphrases. The surgical strip (this
round) keeps the grounding (the deterministic allowlist = question ∪ seed refs,
itself sourced from the KG keyword map + ontology taxonomy) while preserving
the expansion surface.

## 3. The guard relaxation — design (evidence-based, not la_q73-biased)

**R364.1 behaviour (shipped):** a paraphrase citing ANY Article/Annex absent
from question ∪ seed was DROPPED whole (`ref_filtered` counted dropped
paraphrases).

**Measured cost (R364.2/R364.3, n=60, Bedrock judge):** the guarded branch's
answer-correctness collapsed to +0.018 (CI [−0.053, +0.088]) from the
unconstrained +0.103 (CI [0.000, +0.207]), while the gold-drop veto only
halved (+3 → +1). The guard was trading answer quality for ref safety at a
bad rate.

**R364.5 behaviour (this round):** ungrounded Article/Annex refs are
**SURGICALLY STRIPPED** from the paraphrase; the rest of the text is kept and
used for retrieval. A paraphrase stripped below 4 words is dropped. The
allowlist, the deterministic regexes, and the `ref_filtered` counter all stay
(the counter now counts stripped refs — the guard-firing proof). No bias
toward any single row: article refs and annex refs get identical treatment.

**Why this design:** it attacks the la_q73 failure mechanism (phantom annex
tokens entering the retrieval surface and out-ranking the gold chunk) without
destroying the expansion's recall value — the mechanism that delivered the
+0.103 answer-correctness. The strip is deterministic, prompt-independent, and
grounded in the same allowlist as before.

**Tests:** 6 guard tests updated/added in the eval worktree
(`test_r341_query_expansion.py`, 24 passing), covering the la_q73 shape,
compounds ("Annexes I and VI", "Articles 5 and 6"), the "or" span shape, the
too-short drop, and grounded-member preservation. Module byte-identical in
both repos; main-repo engine net 71 passing.

## 4. A/B — results (completed; same-judge Qwen numbers)

60-row pool, seed 20260814, bedrock Stage-2, wrapper dead-ended, label
`r364-5-strip` (60/60 rows, 0 errors; checkpoint saved). The judge was
switched to **Qwen3-32B** (`qwen.qwen3-32b-v1:0`) after the Claude judge
key started 429-throttling — this required fixing `resolve_bedrock_model`
in `app/llm/bedrock_client.py`: non-Anthropic Bedrock IDs (`qwen.`,
`nvidia.`, `mistral.`, `cohere.`, `ai21.`, `deepseek.`) were not recognised
as full model IDs and were silently mapped to the Claude default. BOTH the
STRIP and GUARDED checkpoints were re-judged on the same Qwen model so the
comparison is apples-to-apples (`r364-5-judge-qwen.json`).

**Deterministic axes (per-arm means, 60 rows):**

| run | ref_loose | ref_strict | ref_conc | kw_recall | veto (gold_dropped) |
|---|---|---|---|---|---|
| GUARDED | −0.008 | −0.001 | +0.025 | +0.004 | +0.017 |
| STRIP | −0.024 | −0.013 | −0.003 | −0.057 | **0.000** |

**Qwen judge (same grader both runs):**

| axis | GUARDED | STRIP |
|---|---|---|
| ans_corr (full pool) | +0.077 [−0.019, +0.173] | −0.094 [−0.208, +0.019] |
| cite_faith (changed rows) | −0.133 | −0.143 |
| ans_rel (changed rows) | −0.062 | −0.227 (LOSS) |

**Weighted composite (R364.4 method, same-judge):**

| scheme | GUARDED | STRIP |
|---|---|---|
| primary | +0.0038 | −0.0629 |
| equal5 | +0.0192 | −0.0381 |
| ref_heavy | +0.0035 | −0.0483 |
| trust_heavy | +0.0014 | −0.0729 |

## 5. Verdict — the +0.02 composite does NOT return

1. **The surgical strip is negative under every weighting.** The one thing it
   fixes — the gold-drop veto (0.000 vs +0.017) — comes at the price of
   worse retrieval and worse judged answers: the stripped paraphrases keep
   mangled connector text ("...procedure in or is...") that adds NOISE to the
   RRF surface instead of signal (kw_recall −0.057, ans_rel −0.227 LOSS,
   ans_corr −0.094).
2. **The earlier +0.02/+0.103 was judge-specific.** The Qwen judge (quote-
   level proposition substantiation) does not reproduce the Claude judge's
   answer-correctness reading even for the SAME guarded config. The only
   axis that was ever consistently positive for the branch was ref_conc
   (+0.025 guarded) — a small, underpowered win.
3. **The whole-drop guard (R364.1) is the better of the two expansion
   variants** (composite +0.001…+0.019 vs −0.038…−0.073), and even it is
   neutral-vs-baseline, not positive.

**Decision: the `REGENOLD_QUERY_EXPANSION` flag stays default OFF — closed.**
The surgical strip remains in the code (both repos, byte-identical, 24 tests
passing) because it provides the deterministic guarantee that no ungrounded
Article/Annex ref can ever reach the retrieval surface (veto 0.000) — a
correctness invariant for the flag-ON path — but the A/B data does not
support enabling the feature in any variant. The `resolve_bedrock_model`
fix stays (it is a genuine bug for non-Anthropic Bedrock models, usable by
any future model pin).
