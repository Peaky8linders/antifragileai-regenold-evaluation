# Round 76 — Coverage audit + retrieval-bug fixes + representative-100 LLM-judge benchmark

Autonomous deep-dive against the six Regenold competition axes
(correctness, references, conciseness, tone, latency, multi-turn),
a full retrieval-surface coverage audit, a multi-agent deep-code-review,
and a new stratified LLM-judged top-100 benchmark over the real-world
davidath dataset.

## 1. Retrieval-surface coverage audit — PASS

`scripts/audit_coverage.py` (new) audits every retrieval surface against
the canonical 113-article + 13-annex catalog (`ARTICLE_EXISTENCE`).

| Surface | Articles | Annexes | Verdict |
| ------- | -------- | ------- | ------- |
| KB obligation map | 113/113 | 13/13 | COMPLETE |
| BM25 index (349 docs) | 113/113 | 13/13 | COMPLETE |
| sentence_index (949 sentences) | 113/113 | 13/13 | COMPLETE |
| turboquant dense index | 113/113 | 13/13 | COMPLETE |
| embeddings_index (919 sentences) | 113/113 | 13/13 | COMPLETE — SHA-verified, **not stale** |
| eu_ai_act_tree (1,426 nodes) | 113/113 | 13/13 | COMPLETE |
| semantic_layer | 113/113 | 13/13 | COMPLETE |
| corpus (eu_ai_act_corpus) | 113/113 | 13/13 | COMPLETE (180 recitals, 68 defs) |
| Neo4j seeder (dry-run) | 113 | 13 | COMPLETE (180 recitals, 68 defs) |

All four embeddings asset SHA-256 hashes match the manifest; the live
sentence count (919) equals the manifest — **no refresh needed**. The
only finding is the xref full graph carries 16 fixable article orphans
(zero outgoing edges) — left as-is per the R47 core/full reconciliation
(xref edges are davidath-precision-sensitive; the orphan rescue
deliberately lands only on the production Neo4j 2-hop path).

## 2. Six-axis conformance audit

5 of 6 axes CONFORM (verified end-to-end against the official rules
PDF): answer correctness, reference format (no code path can emit a
malformed `Art. 13` / `Annex 3` / `Article III` form), latency
(fail-soft, cached, no blocking hot-path call), tone, multi-turn.

The QA Answer-Conciseness "gap" (davidath QA score 0.20 — predicted
answers ~3.4× the ~140-char gold) was triaged as a **known-accepted
tradeoff, not a fix target**: CLAUDE.md documents 5+ rounds
(R26/R31/R34/R69) where truncating QA answers regressed correctness
more than it lifted conciseness. The real LLM-judge conciseness axis
(1-4 sentences, non-boilerplate) is already satisfied at
`MAX_ANSWER_SENTENCES = 3`.

## 3. High-impact retrieval fixes — qa_042 + qa_080

Two davidath QA rows were the only failing tests on `main`
(`TestR67UnicodeHyphenScopeRescue`) — both answered (HTTP 200) but
retrieving the **wrong articles**:

- **qa_042** "What labeling requirement exists for deep‑fake content?"
  → gold Art. 50, returned Art. 11/29/47/28/31. The engine's
  `_KEYWORD_ENTITY_MAP` does literal substring matching with no hyphen
  normalisation, so the existing `deepfake` / `deep fake` entries both
  missed the hyphenated `deep-fake`.
- **qa_080** "confidentiality obligations for market‑surveillance
  authorities" → gold Art. 78, returned Art. 74/22/28/36/26. There was
  no `confidentiality → Art. 78` keyword anchor anywhere.

Fix: added `deep-fake → Art. 50` and `confidentiality → Art. 78` to the
engine `_KEYWORD_ENTITY_MAP` and scope `KEYWORD_TO_ARTICLE`;
`confidentiality` also added to `_SCOPE_WEAK_KEYWORDS` so it anchors
retrieval without flipping the scope gate alone (OOS-safe — verified
"confidentiality policy of my bank?" still refuses).

Generalising fixes, not davidath overfit: `deep-fake` is a real
spelling variant; Art. 78 *is* titled "Confidentiality".

## 4. Representative-100 LLM-judge benchmark — new

`evals/bench/representative_100.py` (new) builds a stratified,
LLM-categorised representative top-100 over the **real-world**
davidath dataset (137 QA + 339 scenarios + 50 constructed multi-turn
chains = 526-item pool, CC-BY-4.0, paper arXiv:2603.09435):

- Sonnet categorises every pool item into a 10-category taxonomy +
  a 1-10 representativeness rating — blind to our system's output
  ("no bias"); cached + reproducible.
- Largest-remainder stratified-proportional selection mirrors the true
  category distribution, with a guaranteed 20-row multi-turn quota.
- Order-based deterministic selection (no RNG).
- Judge-compatible sidecar consumed by `evals/judge/runner.py`.

The selected 100 spans all 11 categories (definition,
risk_classification, prohibited_practice, provider/deployer
obligation, gpai, transparency, governance_enforcement,
scope_applicability, procedural, multi_turn).

## 5. Deep-code-review (CR skill)

`deep-code-review` skill — 5 parallel specialists + verifier on the
R76 diff. 6 findings confirmed (2 Important, 4 Suggestion), 5 false
positives / non-issues dropped. All 6 fixed:

- **A** multi-turn items inherited representativeness from the wrong
  scenario (build stride vs `mt_→sc_` id mapping) — added
  `source_scenario_id`.
- **D** `_parse_json_array` hard-stopped at the first `[` — a bracket
  in LLM preamble dropped a whole batch; now scans every `[`.
- **B** `_ask` now returns + records HTTP status (was a silent zero
  row on a non-200).
- **C** categorisation cache write is now atomic (temp file + replace).
- **E** removed the unused `_SEED` (selection is order-based).
- **H** extracted `scenario_to_question` to `evals/bench/dataset.py`;
  the davidath runner + representative-100 share one canonical form.

Report: `docs/reviews/round76-2026-05-22-18-35-16-d4b9da7.md`.

## 6. Top-100 results

### Deterministic-engine scorecard (n=100)

| Axis | Value |
| ---- | ----- |
| Answer Correctness (Loose) | 0.167 |
| Answer Correctness (Strict) | 0.307 |
| Answer Conciseness | 0.412 |
| Reference Correctness (Loose) | 0.655 |
| Reference Correctness (Strict) | 0.490 |
| Reference Conciseness | 0.370 |
| Regulatory Tone | 1.000 |
| Latency p50 / p95 | 31 ms / 103 ms |

### LLM-as-judge scorecard (Sonnet 4.6, 4 axes × 100 rows)

The LLM-as-judge run (`evals/judge/runner.py` — 4 single-axis Sonnet
prompts per row: correctness / refs-faithfulness / conciseness / tone)
is run separately over the `representative-100-r76.json` sidecar. The
local Max wrapper degraded under the 400-call volume, so the judge is
re-run via the Anthropic SDK direct path (`--provider anthropic`).
Judge results are reported as a follow-up to this PR.

Reproduce:
```
py -3.12 -m evals.judge.runner \
  --bench-sidecar evals/bench/results/representative-100-r76.json \
  --label r76-rep100 --provider anthropic --concurrency 6
```

## 7. Verification gates

| Gate | Baseline (R75) | R76 | Result |
| ---- | -------------- | --- | ------ |
| pytest | 2352 pass / 2 fail / 1 skip | **2354 pass / 0 fail / 1 skip** | 2 davidath bugs fixed ✓ |
| davidath Ans Strict | 0.3013 | 0.3023 | +0.001 ✓ |
| davidath Ref Loose | 0.5776 | **0.5818** | +0.0042 ✓ |
| davidath Ref Strict | 0.4471 | **0.4506** | +0.0035 ✓ |
| davidath Tone | 1.0 | 1.0 | flat ✓ |
| davidath Multi-turn | 20/20 | 20/20 | flat ✓ |
| 276 local scenarios | 276/276 | 276/276 | flat ✓ |
| Retrieval-surface coverage | — | 113/113 + 13/13 all surfaces | COMPLETE ✓ |

The two retrieval fixes are net-positive on davidath (Ref Loose +0.0042,
Ref Strict +0.0035, no regressions); the benchmark + CR work is
eval-side and davidath-byte-neutral.
