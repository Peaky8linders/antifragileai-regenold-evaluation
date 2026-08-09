# R326 — light up the dark capability

**Written 2026-08-09 at `031c4b2`. Self-contained: assumes no memory of R325.**

R325 established two things that together define this round:

1. **Selection is exhausted.** No feature combination re-orders references
   better than BM25's own emission order (AUC **0.703**; all-features 0.696).
   Five trimming families and now a lexical re-ranker are all measured dead.
   The remaining over-citation gap — oracle **+0.215 Ref Strict / +0.229 Ref
   Conciseness** — cannot be closed by choosing better among current candidates.
2. **Roughly half the built retrieval capability never executes**, and it is
   the half that would change *what* gets retrieved rather than *how it is
   ordered*.

So: the only remaining direction is generation-side, and the lever for it is
already built, seeded, paid for, and idle.

Full evidence: [`docs/reviews/R325-sync-and-frontier-analysis.md`](../docs/reviews/R325-sync-and-frontier-analysis.md).
State/env/repro: [`.planning/R325-CHECKPOINT.md`](R325-CHECKPOINT.md).

---

## 0. The one measurement that makes this round possible

**The Neo4j vector layer is queryable RIGHT NOW with zero new dependencies.**
Proven, not assumed:

```
Article 5's own text
  -> encoded with the LOCAL encoder  embeddings_index._embed_query()
  -> queried against the graph index v_article_embedding
  -> article_5 FIRST, score 0.7991   (then 3: 0.777, 14: 0.777, 26: 0.715)
  SPACES COMPATIBLE: True
```

Both sides are 128-dim, **and** — the part that actually matters, since two
different 128-d encoders would be incompatible — a round-trip through the local
encoder lands on the right node. No torch. No API. No re-embedding. The 1,490
embeddings across 7 indexes are a working retrieval surface that nothing calls.

⚠ `db.index.vector.queryNodes` is **deprecated** on this Aura version
(replaced by `SEARCH`). It still works; use the new form in new code.

⚠ Tempering the enthusiasm: that top-5 is **flat** (0.799 → 0.689 across five
unrelated articles). A retrieval surface that scores everything ~0.7 may not
discriminate. **Step 1 exists to test exactly that, before any wiring.**

---

## 1. What is dark — measured, not inferred

| surface | state | evidence |
| --- | --- | --- |
| **7 Neo4j VECTOR indexes, 1,490 embeddings** | ONLINE, fully populated, **0 consumers** | `grep -rn 'db.index.vector' app/` → **0 files** |
| **`ft_provision_prose` FULLTEXT index** | ONLINE, **0 consumers** | `grep -rn 'db.index.fulltext' app/` → **0 files** |
| **2-hop graph expand** | works, but **OFF by code default** | forced on: 29 hop-1 + 5 hop-2 articles in **51 ms**. R295 measured the fusion cap admitting ~**4 of 660** even when enabled. |
| **5 seeded node layers** | never read | SubPoint 37 / Practice 8 / AnnexIIICategory 8 / OperatorRole 5 / LifecyclePhase 4. `kg_context` runs **3** Cypher shapes (Article/Annex → Paragraph/Point + recital anchors); the RAG repo runs 14. |

Corroborated end-to-end: the graded hard sample ran `retrieval_path =
kb_fallback` on **17/17** multi-turn rows. The graph contributed **zero
retrieval** on every graded row — Stage-2 context only (the deliberate R252
decision).

---

## 2. Why this is the SOTA lever

The frontier gap is over-citation: we win Ref Loose and keyword recall, we lose
Ref Strict and Ref Conciseness. From the 100 graded easy rows:

```
wrong-rate by rank    1 → 0.14   2 → 0.42   3 → 0.53   5 → 0.88
refs-per-row vs pass  1 → 0.88   2 → 0.54   3 → 0.05   4+ → 0.06
```

41 of 100 rows sit at exactly 3 refs (the QA budget) and supply most failures.
Rank-1 is already 86% right — **the engine's ordering is good; its candidate
set is the problem.** A ranker cannot fix a candidate set. A different
retriever can.

The dark surfaces are precisely that:

* **vector + fulltext** retrieve *different* provisions, not a re-order;
* **the node layers** (Practice, OperatorRole, AnnexIIICategory) are the
  structured legal context that would let Stage-2 attribute a duty to the right
  actor instead of hedging across three.

---

## 3. Steps, ranked — each with its gate and its kill criterion

Every step is **offline-first on recorded rows** (zero generation variance,
free) before anything touches the wire. Env-gate everything, default OFF.

### Step 1 — Does the vector layer find gold that BM25 misses? *(half a day, decides the round)*

The whole round hinges on this, so measure before building.

For each of the 100 recorded rows in
`evals/bench/results/official-r318-july7-easy-easy.ckpt.jsonl`:

1. BM25 top-k → set **B**.
2. Local `embeddings_index._embed_query(question)` → query
   `v_article_embedding` / `v_paragraph_embedding` / `v_point_embedding` →
   set **V**.
3. Judge-derived gold ≈ `pred_refs − wrong_refs` (plus `missing_refs`) from
   `grounded-r318-july7-grounded.json`
   (⚠ they live under `verdicts.reference_correctness`, **not** at row level —
   a row-level `.get()` returns nothing and looks like "no data").

Report: `|V ∩ gold \ B|` — **gold the vector layer finds that BM25 never had**.

* **PROCEED** if it recovers gold on ≥10% of rows.
* **KILL** if <5%, or if the retrieved set is ~the same articles re-ordered.
  Record it as a measured wash in CLAUDE.md's do-not-repropose and stop — that
  is a real result, not a failure.
* Also compute AUC of vector similarity for correct-vs-wrong. If it beats
  **0.703** it is the first signal ever to do so; if not, it is a *recall*
  play only, never a ranker.

Do the same for `ft_provision_prose` in the same pass — one extra query, and
it is the cheaper of the two.

### Step 2 — Wire it as ADDITIVE recall, behind a flag *(if Step 1 proceeds)*

`REGENOLD_GRAPH_VECTOR_RECALL`, default OFF. Append vector hits **behind** the
BM25 winners — never displace one (the R31/R35/R110 additive doctrine, and
R252 exists because graph-primary retrieval buried the operative article).

⚠ **The fusion cap is what killed 2-hop, and it will kill this too.**
R295 measured `fuse_with_kb_xrefs` called with `winners == budget == 5`, so
`remaining = budget − len(out)` is **0** and every graph candidate is discarded
before it can reach `query.entities`: **660 surfaced, 4 admitted (~99.4%
discarded)**. Wiring a new recall source without addressing the cap reproduces
that exactly — a feature that measures byte-identical because it is inert.
But note `REGENOLD_GRAPH_FUSE_SLACK > 0` is already measured as **destroying
gold** (slack=2 turned a perfect `['Article 5']` into three wrong refs). So the
cap must be widened *selectively* — e.g. only for a vector hit that is
question-term-grounded — not globally.

### Step 3 — Read the unread node layers in `kg_context` *(independent of 1–2)*

Add Cypher shapes for **Practice**, **OperatorRole**, **AnnexIIICategory** to
the Stage-2 context. This is **context-only, never a citation** (hard rule
#10), so it cannot move a reference axis and cannot drop gold — the safest item
here, and it targets the answer-side gap (`AnsL − RefL = −13.1`) that nothing
has touched.

Port the shapes from the RAG repo's `kg_context.py` (14 shapes) but **do not
take that file wholesale**: this repo's version is safer in two respects a
"take theirs" resolution silently reverts — it routes fetchers through
`_bounded_execute_read` (the R294 budget + breaker, which the RAG version
bypasses at 4 direct `execute_read` sites) and it raises
`REGENOLD_KG_MAX_UNITS` to 70 (the R318 fix for Article 3's 68 definitions).

⚠ **Budget the thing you add.** `REGENOLD_KG_MAX_CHARS` is 16,000 and the
tail-drop pops from the end, so a new block appended last is the first thing
deleted — the feature silently removes itself. Reserve for it explicitly.

### Step 4 — Finish the R325 measurement *(cheap, already half-done)*

* Grade the hard sample: sidecars
  `official-r325-hard-sample-mt-hard.ckpt.jsonl` (17 multi-turn × 2 turns — the
  **graded pushback turn**) and `-st-easy.ckpt.jsonl` (9 single-turn). The
  judge run was **started and stopped**; nothing is lost, just re-run:

  ```bash
  py -3.12 -m evals.judge.grounded \
     --sidecar evals/bench/results/official-r325-hard-sample-mt-hard.ckpt.jsonl \
     --label r325-hard-mt --model claude-sonnet-5 --provider wrapper \
     --timeout 120 --concurrency 3
  ```
* Then apply the **parent-collapse** offline to those same rows —
  `REGENOLD_PARENT_COLLAPSE` is shipped default OFF and owes its gate. On the
  easy batch it measured F1 **+0.0177**, 5 rows fail→pass, 0 pass→fail, at the
  cost of one gold ref.

Raw sample numbers already in hand (n=17 multi-turn, 0 errors): tone **1.0**,
refusals **0**, **`pushback_conceded_rate 0.0000`** — it never folds under "I
think you're hallucinating" — but **`pushback_ref_flip_rate 0.4118`**: 41% of
rows reshuffle citations on the turn that is actually graded. Whether that is
correction or degradation is exactly what the judge answers.

---

## 4. Gates

| gate | command | expected |
| --- | --- | --- |
| davidath 476 | `py -3.12 -m evals.bench.runner` | Ans Strict 0.3545 · Ref Loose 0.5971 · Ref Strict 0.4748 · Tone 1.0 · mt 20/20 |
| 276-runner | `py -3.12 -m evals.regenold.runner` | 255/255, RISK_F1 1.00 |
| OOS | `py -3.12 -m evals.regenold.runner_v2 --local --probe-oos --oos-suite all --label X` | 49/51, 0 leaks |
| full suite | `py -3.12 -m pytest tests/ -q -p no:cacheprovider` | failure **SET** == 55, diffed **in place** |
| **merge gate** | `evals.harness.easyhard_ab` | for any reference change — it scores ref conciseness as a count-ratio against gold, which `ab_judge` lacks, and that gap is how R142.1 slipped through |

⚠ **davidath cannot validate graph work.** It is BM25-saturated, and it
projects predictions through `article_heads()` — a gate can read byte-identical
*because it is a no-op there*. Byte-identical is also what INERT looks like:
**prove the feature FIRES** (assert the behaviour directly), never infer safety
from flatness.

---

## 5. Traps specific to this work

* **Check the API before declaring something dead.** In R325 I recorded
  `hop2 = 0` and `turboquant = 0` and nearly wrote both off. Both were wrong:
  the 2-hop result field is `hop2_articles` (not `refs`), and turboquant
  exposes `dense_top_k` (not `query`). `grep`-based "zero consumers" claims are
  solid; "returns nothing" needs the signature checked.
* **Judge fields are nested** — `wrong_refs` / `missing_refs` live under
  `verdicts.reference_correctness`. ABSENT IS NOT ZERO.
* **`NEO4J_AUTO_SEED=0` before any app import.** This repo's `SEED_VERSION`
  (`2026-07-24-r291-fullseed`) is OLDER than the live graph
  (`2026-08-08-r323-annex-sections`) and the boot hook re-seeds on ANY mismatch
  without checking which is newer — it would downgrade production's graph,
  silently.
* **`evals/` does not load dotenv**, and the RAG repo's `.env` must not be
  copied here (its `P2P_GRAPH_RAG_API_KEY` enables an Anthropic path a test
  expects off). Use the launcher pattern in
  `.planning/R325-CHECKPOINT.md` §6.
* **Never run two wrapper-bound jobs concurrently.**
* **Don't extrapolate from `--limit N`** — a 3-row probe predicted 20 s/row;
  the real rate was 72 s/row once Groq started 429-ing the denoiser. Use
  `run_hard_sample_r297 --frac F` (stratified, RNG-free) for a representative
  sample; `--dry-run` prints the composition free.
* **A background job that runs `git checkout` will collide with your edits.**
* Don't add torch — neural NLI measured ROC-AUC **0.585** against the free
  lexical scorer's 0.749, and 235× slower.

---

## 6. Honest expected value

Step 3 is low-risk and probably a modest answer-side gain. Step 1 is the one
that matters, and it is genuinely uncertain: the flat similarity profile in §0
is a real warning sign, and this codebase has measured dense retrieval as a
wash **three times** (R31, R69, R99 — davidath is BM25-saturated).

What is different this time is the *question*. Those three rounds asked "does
dense re-rank better?" — and R325 has now closed re-ranking definitively. Step
1 asks "does dense retrieve **gold that BM25 never had**?", which none of them
measured, and which is the only mechanism left that can move the candidate set.

If Step 1 kills it, that is a valuable, publishable-internally result: it would
mean the candidate set is not the bottleneck either, and the gap is in Stage-2
generation from an already-adequate context — which points at prompt and
grounding work, not retrieval. **Either outcome ends a direction**, which is
the point.
