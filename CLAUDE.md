# CLAUDE.md — Regenold EU AI Act RAG

This file gives an LLM coding assistant the load-bearing context for this
repo. Read top-to-bottom before making changes.

## What this repo is

A standalone EU AI Act grounded Q&A surface — extracted from the parent
`legit-ai` (CodexAI) codebase as a transparency bundle for the Regenold
competition. The wire contract is a single `POST /api/v1/regenold/eu-ai-act/ask`
endpoint that accepts an OpenAI-style messages array and returns
`{answer, references, reasoning}` per the Regenold rubric.

The system is built to win on six axes the competition scores against:
correctness, references-vs-gold, conciseness-vs-gold, tone, latency, and
multi-turn coherence.

## Architecture (single source of truth)

```
POST /api/v1/regenold/eu-ai-act/ask
        │
        ▼
app/routes/regenold.py
   ├── _build_question_from_history       — flatten last 4 turns
   ├── classify_conversation              — scope gate (refusal or in-scope)
   │      └── app/integrations/regenold/scope.py
   ├── ask_compliance_question            — engine entry
   │      └── app/engines/graph_rag.py
   │             ├── _deterministic_parse — keyword→entities + BM25 fallback
   │             ├── _retrieve_from_kb    — KB + ontology + xrefs
   │             └── _deterministic_answer
   │                    ├── classification verdict (~17 topics)
   │                    ├── role × risk matrix    ← longest-match required
   │                    └── obligation dump
   ├── _surface_anchor_citations          — keyword-derived anchors
   ├── _collapse_parent_refs              — smallest-cover citation pass
   ├── normalise_answer_for_regenold      — 3-sentence + 600-char cap
   └── RegenoldAskResponse
```

## Knowledge surface

| Module                                | Content                                                       |
| ------------------------------------- | ------------------------------------------------------------- |
| `app/data/article_existence.py`       | 113 articles + 13 annexes canonical catalog.                  |
| `app/data/kb.py`                      | `EC_CHECKER_OBLIGATION_MAP` — 94 articles/annexes covered.    |
| `app/data/ontology.py`                | Typed registries: Practice ×9, AnnexIIICategory ×8, Phase ×6. |
| `app/data/definitions.py`             | Art. 3 definitions — 30 high-impact terms.                    |
| `app/data/kb_search.py`               | BM25 index over KB + ontology — 133 docs (96 KB + 23 ontology + …). |
| `app/data/kb_xrefs.py`                | Cross-reference graph: regex-extracted + 20 manual edges.     |
| `app/data/graph_rag_prompts.py`       | Stage-1 / Stage-2 system prompts.                             |

## Hard rules — don't break these

1. **Reference format is strict.** Only `Article N(.subpoint)*` (Arabic) or
   `Annex X(.subpoint)*` (Roman, uppercased). Validated by
   `_ARTICLE_OUTPUT_RE` / `_ANNEX_OUTPUT_RE` in
   `app/integrations/regenold/models.py`. Never emit `Art. 13`, `Annex 3`,
   `Article 13(1)`, `Annex III(2)`, or `Article III` on the wire.
2. **`MAX_ANSWER_SENTENCES = 3`**, plus a soft 600-char cap that drops the
   longest non-cite-anchored sentence first. Don't relax this without
   measuring conciseness delta.
3. **No new classification topics for the 3 PDF example questions**
   (technical-doc hardware / emotion-recognition prohibition / doctor-
   patient transcription). The competition rubric measures generalisation;
   topic-specific overfit will be penalised. Add new topics only when
   they don't track the example list.
4. **KB stubs ship faithful regulatory prose, never speculation.** A
   confidently-wrong summary loses more than a missing one.
5. **`ARTICLE_EXISTENCE` is the lint floor** — every emitted citation
   must resolve here. The `tests/test_kb_consistency.py` suite enforces
   this across `EC_CHECKER_OBLIGATION_MAP`, `_KEYWORD_ENTITY_MAP`,
   `KEYWORD_TO_ARTICLE`, `_CLASSIFICATION_TOPICS`, the ontology
   registries, the xref graph (both regex and manual), and the
   definitions registry.

## Recent code changes (2026-05-12 — round 18 optimization)

### Paper-aligned IR metrics (`evals/regenold/runner.py`)
- Eval harness extended to align with Davvetas et al. (arXiv:2603.09435v1).
- Added **risk-level classification F1** per class (prohibited/high_risk/refusal).
- Added **article retrieval weighted precision/recall/F1** against gold sets.
- Current baseline: **Article-retrieval F1=0.64 (P=0.52 R=1.00)**. Precision is the primary optimization target.

### Round 17 structural optimizations
- **`app/integrations/regenold/models.py`**: `MAX_ANSWER_SENTENCES`: 4 → 3; `_MAX_ANSWER_CHARS_SOFT = 600` sentence-dropping logic; unified single-sweep regex for sub-points.
- **`app/routes/regenold.py`**: `_collapse_parent_refs` smallest-cover pass; `_surface_anchor_citations` penalty-pruning logic.
- **`app/engines/graph_rag.py`**: Longest-match role/risk detection; matrix-lookup path for role-obligations.
- **`app/data/`**: BM25 extended to ontology (133 docs); 12 new KB stubs; 30 Art. 3 definitions; 20 manual xrefs.

## Eval scorecard (deterministic-fallback)

| Round  | Pass     | p50    | p95    | avg refs | avg sentences | Retrieval F1 | Notes |
| ------ | -------- | ------ | ------ | -------- | ------------- | ------------ | ----- |
| 15     | 276/276  | 3.04ms | 4.41ms | 2.12     | 2.29          | —            | Baseline. |
| 17     | 276/276  | 4.31ms | 7.30ms | 2.12     | 2.04          | —            | Structural upgrades. |
| 18     | 276/276  | 6.29ms | 9.08ms | 2.12     | 2.04          | 0.64         | Paper-aligned metrics. |
| 18.1   | 276/276  | 6.61ms | 10.07ms| 2.12     | 2.04          | 0.64         | Fixes: Art. 113 protect, BM25 tokenizer. |

Δ on the local rubric is modest (-11% sentences, +12% p50 latency) because
the local harness is binary substring-matched and already saturated. The
upgrades target the **competition rubric** axes the local harness can't
score against (citation precision-vs-gold, conciseness-vs-gold-length,
multi-turn coherence). The structural improvements (ontology in BM25, 12
new KB stubs, definitions index, manual xrefs, longest-match role
detection, smallest-cover pass) are de-overfitted from the 3 PDF example
questions.

## Non-goals / things to skip

- Vector embeddings / dense retrieval — the corpus is small and
  deterministic; BM25 + curated keyword + ontology covers it.
- Memory / RAG over user history — the API is stateless per turn,
  scope.py handles coref via anchor borrowing.
- Cross-encoder reranker — overkill for 133 docs; BM25 ranks well enough
  and the top-k cap is small.
- Streaming responses — out of competition scope; the wire returns one
  JSON.

## Testing

```
.venv\Scripts\python.exe -m pytest -q             # 430 tests
.venv\Scripts\python.exe -m evals.regenold.runner # 276 scenarios
```

Both must pass clean before any PR. Test files are organised so each
upgrade has its own regression module (`test_reference_parser_fixes.py`,
`test_kb_search_ontology.py`, `test_kb_stubs_filled.py`,
`test_definitions.py`).
