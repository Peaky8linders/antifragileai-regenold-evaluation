# R361 — Graph-Enhanced LLM QA paper deep-dive: cross-reference, gaps, fixes

**Source paper:** "A Graph-Enhanced LLM-Based Question Answering System for
the AI Act" (Aggio, De Lazzari, Scantamburlo — LARUS/AKOS/UniTri,
LLAIS workshop @ ECAI 2025). Full 33-page text extracted to
`scratch/graph-qa-paper-text.md`.
**Repos:** regenold-eu-ai-act-rag (main) + antifragileai-regenold-evaluation (eval).

---

## 1. The paper's methodology (distilled)

A GraphReader-inspired agent over a Neo4j graph of the AI Act:

**Schema** — Article/Annex/Recital/Chapter/Section hierarchy
(HAS_ARTICLE, HAS_SECTION); **Chunk** (783) = paragraph (Article/Annex) or
sentence (Recital), ordered by NEXT; **AtomicFact** (3,287) = LLM-extracted
standalone factual statements from Chunks; **KeyElement** (2,601) =
nouns/verbs/adjectives (core legal concepts) from AtomicFacts; curated
cross-refs **HAS_REFERENCE** (435, via the AI Act Explorer) and
**HAS_RELATED_RECITAL** (329); embeddings on AtomicFact + KeyElement.

**Agent** (2 variants): (1) rational plan → **Initial Node Selection**
(extract KeyElements from the question, match to graph, cosine ≥0.5) →
AtomicFact exploration (cosine ≥0.6 vs question, threshold lowered
incrementally) → Chunk exploration with **annex detection** (HAS_REFERENCE
→ queue) + **related-recital retrieval** (HAS_RELATED_RECITAL → queue),
reading ALL queued nodes before terminating → neighbor exploration → answer
from the notebook. (2) **af_only**: skips Initial Node Selection, queries
the vector index directly for k AtomicFacts.

**Evaluation** — their own dataset (the same 10 gold + 10 no-gold questions
in `graphrag_evals_dataset.txt` — this repo's attached txt files ARE the
paper's supplementary material). Automatic: BERTScore F1 + SentenceBERT
sentence-level cosine. Human: 3 legal experts, 1-5 Likert on
Accuracy/Relevance/Transparency, confidence-weighted, final = 0.3×auto +
0.7×human.

**Results:**

| Model | Automatic | Human | Final |
|---|---|---|---|
| BM25 | 0.169 | 1.148 | 0.211 |
| GraphReader-base | 0.595 | 3.712 | **0.698** |
| GraphReader-af_only | **0.617** | 3.086 | 0.617 |
| SBERTGPT | 0.555 | 2.518 | 0.519 |
| CLaiRk | 0.628 | 3.450 | 0.671 |

**The paper's own headline finding:** af_only wins the automatic metrics but
loses badly on human judgment — "bypassing the initial use of KeyElement
nodes reduces the perceived relevance, accuracy and transparency… the limits
of relying solely on vector similarity among entire sentences in Legal QA."
The KeyElement-grounded entry point is what humans reward.

---

## 2. Cross-reference vs the current implementation

### Already implemented (verified in main)

| Paper mechanism | Our analog | Status |
|---|---|---|
| Graph schema (Chunk/AtomicFact/KeyElement) | `provision_hierarchy.py` (1,412-node tree), `eu_ai_act_tree.py`, `semantic_layer.py` | live |
| Initial Node Selection (KeyElement entry) | `entity_extractor.py` (8 roles × 24 concepts), `REGENOLD_ENTITY_BOOST` default ON, BM25 boost | **live** — R81-N measured it as the largest QA Ref Strict lift since R34 |
| Annex/recital expansion while exploring | `_expand_referenced_annexes_and_recitals` (`_graph_rag_impl.py:6070`), `fetch_recital_anchors` (`kg_context.py`, `REGENOLD_KG_MAX_RECITALS`), `fetch_definition_and_recital_context` (`graph_semantic.py`) | live |
| Rational plan | `query_complexity_router.py` + `question_complexity.py` + `query_structure.py` (R69-C structured payload) | live |
| Related-recital edges (HAS_RELATED_RECITAL) | recital anchors via the embedded graph / KB (`graph_aware_retrieval.py` HAS_RECITAL_ANCHOR) | live |
| The dataset | the attached `graphrag_evals_dataset.txt` (B.2.1/B.2.2/B.3) — already parsed into the R360 validation sidecar | done |

### Real gaps (adversarial, grounded)

**GAP-1 — the judge could not ground recital citations.** The paper's
related-recital retrieval makes recital-grounded answers first-class; the
engine already retrieves recitals, but the judge's provision resolver only
covered Articles/Annexes (`provision_exists('Recital 27') == False`), so
every recital-grounded claim was scored unsupported/not-addressed — R360
documented this as a one-sided conservative bias. The official recital text
exists in-repo (`OFFICIAL_RECITAL_TEXT`, all 180 recitals). **Fix
(shipped):** `legal_v2` resolves `Recital N` refs from
`OFFICIAL_RECITAL_TEXT`, and the NON_EXISTENT gate is now resolution-based.

**GAP-2 — the NON_EXISTENT gate used the head-lax `provision_exists`.**
`provision_exists('Article 3.999') is True` (a documented open finding in
the R339 audit), so the gate fired on nothing real and let fabricated
leaves through. **Fix (shipped):** the gate is now `_ref_exists` — a ref
exists iff its verbatim text actually resolves (Articles/Annexes via the
provision resolver, Recitals via the official corpus). Strictly more
correct; closes the audit's "still owed" item.

**GAP-3 — no validation of our judge against the paper's published
numbers.** The paper's B.3 outputs (GraphReader-base / af_only answers over
the 10 no-gold questions) are in the R360 sidecar, and the R360 run already
showed the reference-free axes reproduce the paper's AUTOMATIC ordering
(af_only +0.087 faithfulness over base) while the paper's HUMAN evaluation
preferred base — the same automatic-vs-human divergence the paper itself
reports. The R361 re-run (with recital grounding) re-measures this and
quantifies how much of the B.3 answers' unsupported claims were
recital-grounding artifacts vs real over-claims.

**Non-gap (checked):** the paper's exhaustive queue-read (read ALL annexed
annexes/recitals) trades exhaustiveness for over-inclusion — the paper
notes it and STILL won on human judgment. Our repo's measured #1 gap is
over-citation at the *reference* level, already addressed by the citation
budget + R72 reconcile. No new change warranted; the paper's base-variant
win on human judgment is a *content*-exhaustiveness result, not a citation
result.

**Non-gap (checked):** Initial Node Selection. The engine's entity boost is
the KeyElement-entry analog and is already default ON with a measured win
— the paper's headline finding is confirmatory, not a new lever.

---

## 3. What shipped (this worktree)

1. **`evals/judge/legal_v2.py`**
   - `_resolve_ref_text(ref)` — Articles/Annexes via `get_provision_text`,
     `Recital N` via `OFFICIAL_RECITAL_TEXT` (all 180 recitals; unknown
     numbers → "").
   - `_ref_exists(ref)` — resolution-based existence, replacing the
     head-lax `provision_exists` in `_postprocess_reference_correctness`
     (the NON_EXISTENT_PROVISION gate now actually fires on fabricated
     leaves like `Article 3.999`, and real Recital refs are judged on
     their merits instead of being flagged non-existent).
   - `_resolve_provision_texts` uses the fallback — every axis' grounding
     (answer_correctness, reference_correctness, citation_faithfulness,
     crag_fine, faithfulness) now carries recital text where cited.
   - Standard runs are byte-identical: the live wire never emits Recital
     refs in `pred_refs`/`gold_refs` (recitals are non-citable on the wire
     per hard rule #10), so only runs carrying Recital refs change.
2. **`tests/test_r361_recital_grounding.py`** (9 tests) — recital
   resolution, unknown-recital rejection, fabricated-leaf NON_EXISTENT,
   real-recital-not-WRONG, faithfulness prompt carries recital text.
3. **`scratch/r360_build_validation.py`** — now extracts `Recital N` refs
   from the B.3 answers so recital-grounded claims are judgeable.
4. **R360 validation re-run** (40 rows, Bedrock sonnet-4-6, no thinking,
   tunnel untouched) with the new grounding — see §4.

### Engine side (main repo) — no changes, two grounded non-gaps

The paper's two headline lessons are already implemented and measured in
main: the KeyElement entry (entity boost, default ON, R81-N's largest QA
lift) and the recital/annex expansion (`_expand_referenced_annexes_and_
recitals`, `fetch_recital_anchors`). The genuinely missing piece was the
judge's ability to verify recital-grounded claims — which is what shipped.

---

## 4. Live results (Bedrock only, 40 rows re-run with recital grounding)

Judge: claude-sonnet-4-6 via Bedrock, no thinking, 40 rows / ~90 axis calls,
**0 errors** (the first-pass truncation class stayed gone — output budget
2000). Tunnel quota untouched (`P2P_GRAPH_RAG_PROVIDER=bedrock`,
`REGENOLD_BEDROCK_WRAPPER_FALLBACK=0`).

### 4.1 The recital-grounding effect (R360 → R361)

| Metric (no-gold B.3 half) | R360 (recitals unresolved) | R361 (recitals grounded) | delta |
|---|---|---|---|
| base faithfulness (mean) | 0.505 | **0.663** | +0.158 |
| af_only faithfulness (mean) | 0.592 | **0.724** | +0.132 |
| base vs af_only delta | +0.087 | **+0.061** | −0.026 |

Both arms lifted ~+0.13-0.16, confirming the R360-documented one-sided
bias was real (recital-grounded claims were scored unsupported when the
judge could not resolve them). The base-vs-af_only ordering is **robust**
to the fix — af_only still leads on faithfulness, reproducing the paper's
AUTOMATIC ordering (0.617 vs 0.595). Relevancy unchanged (0.890 both),
judge-vs-expert agreement unchanged (0.55/0.50/0.60 — expert rows cite
articles only).

### 4.2 What the residual unsupported claims are (spot-checked)

The claims still flagged after grounding are **real catches, not
artifacts** — e.g. `nogold_af_only_q07` claims "Article 3(66) is the
source for the definition of systemic risk", but the Act defines systemic
risk at Article 3(65); the cited 3(66) text cannot entail the claim, so
it is correctly UNSUPPORTED. This is precisely the traceability the
paper's design promises — and the judge now enforces it at recital
granularity too.

### 4.3 The paper's automatic-vs-human divergence, reproduced

The paper reports af_only winning automatic metrics but losing human
judgment (3.086 vs base 3.712). Our reference-free axes reproduce the
automatic half (af_only > base on faithfulness); the human half needs the
KeyElement-entry quality our axes cannot see — consistent with the R360
finding that relevancy/faithfulness track automatic-style measures, not
legal-interpretation quality. This is now a documented, quantified
boundary of the judge, not an assumption.

## 5. Regressions

- `test_r361_recital_grounding.py` + `test_legal_v2_judge.py` +
  `test_r350_review_fixes.py` + `test_r360_hypa_ref_free_axes.py`:
  98/98 pass.
- Standard 4-axis judge runs byte-identical (recital resolution only
  activates when a ref matches `Recital N`; the live wire never emits
  Recital refs, so no standard sidecar changes).
- The NON_EXISTENT gate change (`_ref_exists`) is strictly more correct
  and closes the R339-audit "still owed" item; covered by tests.
