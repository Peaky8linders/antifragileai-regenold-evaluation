# Deep Code Review + End-to-End System Review: Regenold EU AI Act RAG

**Date:** 2026-08-15 18:08:03
**Branch:** freebuff/use-cr-skill-md-and-deep-code-review-and-do-also-a-eb3a82ef-3d41-464d-a0ea-fc002329f6fe -> main
**Commit:** 8008d6a
**Files reviewed:** ~140 app modules (~93,700 lines) — full request path, retrieval stack, engine, graph layer, LLM providers, evidence store, auth/rate-limit, plus the 305-file test suite (6364 passed / 35 skipped hermetic)
**Diff size category:** N/A — full-system review per request (not branch-diff-scoped)

## Executive Summary

The system is in genuinely good shape: the hermetic test suite is green (6364 passed), the fail-soft discipline is consistent, the cache-key doctrine is documented, and the empirical note-keeping (R-numbers with measurements) is unusually honest. The dominant risks are **not** crashes — they are (1) one confirmed duplication bug on the default retrieval path, (2) the accretion of ~100 env-gated heuristic passes in a 10k-line route that increasingly fight each other, and (3) RAG-modernisation gaps (no real dense embeddings, no active cross-encoder rerank, an unwired query-expansion module) that cap the retrieval ceiling the benchmark numbers already hint at. One finding is confirmed empirically; the rest are verified by code reading. No Critical issues found; 2 Important; 7 Suggestions.

---

## Important Issues

### [I1] Duplicate annex/recital grounding entries on the default KB-primary retrieval path

- **File:** `app/engines/_graph_rag_impl.py:5620-5622` (+ `:6039`, `:5734`, `:5696`)
- **Bug:** `_retrieve_from_graph`'s KB-primary branch (default ON) calls `_retrieve_from_kb(...)`, which **already** runs `_expand_referenced_annexes_and_recitals(context)` at line 6039, and then calls it **again** at line 5622. `_expand_referenced_annexes_and_recitals` (lines 5810-5876) dedupes only against per-call local lists (`extracted_annexes` / `extracted_recitals`) — it never checks `context.referenced_annexes_and_recitals` — so every annex/recital referenced in the retrieved text is appended twice. The same double-call pattern exists on the graph-failure fallback path (line 5696 → 6039, then 5734) and the R99 empty-success path.
- **Verified empirically:** `Art. 43` query → 1 entry becomes 2 after the second call; `Art. 5` query → 5 entries become 10 (all five duplicated: recitals 18/31/44, Annex II, Annex III).
- **Impact:** every live request whose retrieved context references an annex/recital ships duplicated verbatim text into the Stage-2 grounding block (rendered at line 6303), wasting prompt budget and risking duplicated recital prose in answers; the route's own recital-append path had to add a separate `_seen_rec` dedupe (line ~8800) to survive this class. No test covers the double-call because tests exercise `_retrieve_from_kb` directly.
- **Suggested fix:** delete the redundant calls at 5621-5622 (and the 5734 one), or — more defensively — add a membership check against `context.referenced_annexes_and_recitals` inside `_expand_referenced_annexes_and_recitals` so the function is idempotent regardless of call site. Add a regression test asserting `len(ctx.referenced_annexes_and_recitals) == len({r['id'] ...})` after `_retrieve_from_graph` with a KB containing an annex/recital mention.
- **Confidence:** High (code reading + runtime reproduction).
- **Found by:** Logic & Correctness / Contract & Integration (duplicate-work + missing idempotency).

### [I2] The Stage-2 system prompt is dead on the live path — every rule there is inert, and the codebase keeps paying to maintain it

- **File:** `app/engines/_graph_rag_impl.py:7787-7791` (measured evidence), `app/data/graph_rag_prompts.py` (`ANSWER_GENERATE_SYSTEM`, 988-line file), `app/engines/_graph_rag_impl.py:7455` (`_claude_max_enhance_answer` import).
- **Bug/issue:** The Claude Max wrapper drops the `system` slot 100% (measured: French-instruction test obeyed only in the user slot). `ANSWER_GENERATE_SYSTEM` + `PROMPT_HARDENING_PREFIX` reach the model on **zero** live requests — its only real consumer is `_llm_generate_answer` (line 1619/1710), which the code itself documents as having "no production caller". The route and the engine have already had to hand-port rules into the user channel (`USER_REF_MINIMALITY_CLAUSE`, `USER_ANSWER_COVERAGE_CLAUSE`, `USER_SUBPARAGRAPH_ATTRIBUTION_CLAUSE`, …) and still ship dangling pointers ("the BLUF format from your system prompt", "rule 12b") that were only repaired for the delivered clauses.
- **Impact:** maintainers keep writing rules into `ANSWER_GENERATE_SYSTEM` (R122/R143/R145/R147/R265/R266/R275 "prompt-only, the win lands live" — it landed on nothing), a ~1000-line maintenance surface that cannot affect output; every new rule must be duplicated into the user message or silently lost.
- **Suggested fix:** (a) audit `graph_rag_prompts.py` and delete or migrate every rule that only exists in `ANSWER_GENERATE_SYSTEM` into a single canonical `USER_*` assembly; (b) delete `_llm_generate_answer`'s production-dead path or wire it, so the "second consumer" illusion disappears; (c) add a boot-time or test-time assertion that no rule that changes answer behaviour lives exclusively in the system slot. Do **not** forward the system prompt (R282 measured it rubric-negative).
- **Confidence:** High (explicitly measured in-repo at 7787-7791).
- **Found by:** Contract & Integration (dead code + duplicate logic divergence).

---

## Suggestions

- **S1 — Tokenizer divergence between index-time and query-time embedding vectors.** `app/engines/embeddings_index.py:120-124` keeps digits `len <= 4`; `app/data/kb_search.py:170` keeps digits only `len == 4`. `scripts/build_embeddings_index.py:55` builds the SVD assets with `kb_search._tokenize`, so the runtime query tokenizer is *not* "the same shape" as its docstring claims. A query containing e.g. `10000` (present in vocab, dropped at query time) silently never matches. Fix: import the canonical `_tokenize` in `embeddings_index.py` (drop the vendored copy) and rebuild assets.
- **S2 — Contradictory X-Forwarded-For documentation.** `app/routes/regenold.py:2158-2162` reads the **rightmost** hop (correct — the immediate client of a trusted proxy); `_regenold_rate_key`'s docstring (line ~2176) says "leftmost". Fix the docstring; wrong operator reading of the trust boundary is a rate-limit bypass risk.
- **S3 — `classify_scenario_query` and the "is scenario" predicate are computed multiple times per request with two different definitions.** `_is_scenario` (line ~7130, `classify_scenario_query(...) is not None`) vs `_is_scenario_question` (line ~7650, `should_expand_for_question(question)` — a different regex) — near-identical names, different semantics, and `classify_scenario_query` runs again for the budget at line ~7400. This is exactly the R281 class of bug (clamp keyed on a different predicate than the budget). Consolidate to one computed value.
- **S4 — `query_expansion.py` is unwired dead code (an untapped SOTA lever).** Only its own test references it. Either wire multi-query / synonym-expansion into `top_articles_by_relevance` behind the existing env-gate + A/B discipline, or delete it.
- **S5 — Duplicated embedding queries per request.** `top_articles_by_relevance` (kb_search.py:887) and `_populate_semantic_statements` (_graph_rag_impl.py:5762) both run the same SVD sentence query. Sub-ms each, but it is the same redundancy pattern as I1 — centralise so the query runs once and the result is shared.
- **S6 — `_engine_cache_key` is a hand-maintained whitelist.** Every new engine-behaviour env flag (there are ~40 folded in) must be manually added; the codebase has hit the resulting stale-cache A/B failure repeatedly (R263.2 class). Consider hashing the sorted `{k: v}` of all `REGENOLD_*`/`P2P_GRAPH_RAG_*` vars the engine reads, or generating the list from a single registry decorator on the `_env_enabled` helpers.
- **S7 — `scope.verdict.evidence[:200]` in the audit payload** (`app/routes/regenold.py:10130`) raises `TypeError` when `evidence` is `None`, silently skipping the whole audit write (it is inside the broad `except`). Guard with `(scope.verdict.evidence or "")[:200]`.

---

## End-to-End System Walk (what works, and where the headroom is)

**Request → scope gate:** the layered gate (deterministic regex → safety-intent LLM → general assistant → ambiguous-OOS rescue) is the strongest part of the system; the "regex prior + LLM authority + fail-soft" design is sound, and the R271 refusal-only-on-dangerous policy is the right product call. Watch item: every LLM gate adds a serial round-trip on the cold path; the ContextVar intent-cache (R84) correctly collapses the three `classify_intent` sites.

**Query de-noiser:** multi-turn rewrite with deterministic salvage is a correct RAG pattern. The re-ask focus (R305) and self-contained-focus (R133.1) gates show the "flattened-prompt bleed" bug class is understood and defended.

**Retrieval:** BM25 over KB stubs + ontology virtual docs + full EUR-Lex prose is a legitimately good lexical layer for a 347-doc corpus. The additive-only discipline (dense/graph can never displace a lexical winner) is the right call for citation precision. **The gap is semantic recall:** the "dense" layer is TF-IDF + SVD (LSA), which cannot bridge paraphrase/synonym gaps; the graph layers (2-hop/PPR/PathRAG) are gated OFF by default and, per the code's own R295 measurement, contribute ~4 refs in 132 calls due to zero fusion slack. So live retrieval is ~99% pure BM25.

**Engine:** the deterministic Stage-1 + curated intercepts + CLARA + gatekeeper stack is genuinely novel and is what wins the benchmark's precision axes. Stage-2's verbatim grounding (R288) is the measured factual-score win and is default ON — the right call. The integrity guards (drift scrub, self-contradiction, fidelity, grounding-guard fallback) are layered correctly with fail-soft.

**Post-engine:** 20+ sequential reference passes in the route are each individually defensible, but the composition is the system's biggest fragility: passes routinely re-add what an earlier pass dropped (R87-C re-emit vs R142 clamp vs R138 re-add vs R251 collapse vs R317 exclusivity — each with an env gate and a trace note). This is where future regressions will come from, not from the engine.

**Evidence/audit:** the hash chain (in-memory eviction-anchor + Postgres advisory-lock serialisation) is correct and unusually well-thought-out (genesis-fork + truncation-attack cases are handled).

---

## Optimisations & Simplifications (per layer)

### Simplification — highest value first
1. **Consolidate the route's reference passes.** The 10k-line `regenold.py` handler is one linear sequence of ~60 transformations. Group the reference pipeline into a small set of composable stages (surface → expand → reconcile → clamp) with a single ordering, and convert the per-pass env flags into one `REGENOLD_REF_PIPELINE` mode enum. This kills the R142/R281/R311/R317 "which pass runs last" whack-a-mole.
2. **Delete provably-dead paths:** `query_expansion.py` (S4), `_llm_generate_answer` (I2), the `_ORPHAN_ENFORCEMENT_ENABLED=False` block, `embeddings_index` docstring claims (S1).
3. **Unify the two sentence splitters** (`models._split_sentences` vs `sentence_index.split_legal_sentences`) — the R307 comment already admits they drift and caused a live bug; make one import the other.
4. **One `_is_multiturn`/scenario predicate** (S3).

### Optimisation — latency (a scored axis)
- `REGENOLD_STAGE2_SIMPLE_SKIP=1` is the single biggest lever: p50 15-22s → sub-second on the simple-question majority, with the R127 gate conservative by construction. It needs the live A/B the comment prescribes, but it is the clear next win.
- The answer LRU cache already works; extend TTL-sensitive eviction only if a question rotates across Omnibus updates (KB_VERSION already busts it on redeploy).
- `_ENGINE_CACHE` stores the full `GraphRAGResponse`; consider storing the final wire shape to also skip the 20 post-passes on hits (they re-run per request today by design).

### Optimisation — retrieval (the SOTA ceiling)
1. **Real dense embeddings.** Replace/augment SVD-LSA with a hosted embedding API through the existing wrapper (e.g. `text-embedding-3-small`-class; corpus is 919 sentences → trivial cost, ~5-10 ms). Keep BM25 primary; fuse via **weighted RRF** (`REGENOLD_RRF_FUSION`, k=60, BM25 2.0 / dense 1.0) instead of additive fill — RRF is the proven practice for exactly this hybrid setup.
2. **Cross-encoder rerank on the candidate pool, then cut.** Cohere rerank already exists (R329) and measured the right failure (precision 0.653 vs recall 0.879 — ~1.1 wrong refs inside an otherwise-right set). The proven pipeline is: BM25+dense top-50 → cross-encoder rerank → top-k → the existing budget clamp. R329's own placement analysis (three inert placements, `rerank_stats()["attempts"]==0`) is the trap to avoid — instrument the placement and assert attempts > 0 in the A/B.
3. **Multi-query / synonym expansion** via the existing `query_expansion.py` (S4): legal corpora respond best to term/abbreviation expansion ("GPAI"↔"general-purpose AI", "AI Act"↔"Regulation (EU) 2024/1689", "high-risk"↔"Annex III") and one LLM-rewritten query variant, RRF-merged.
4. **Grant the graph layers real fusion slack** (`REGENOLD_GRAPH_FUSE_SLACK`) and A/B it — the R295 measurement (4 refs added in 132 calls) is a fixable plumbing problem, and the architecture's 2-hop/PPR/PathRAG investment is otherwise wasted.

### Optimisation — generation (beating frontier baselines)
1. The R280 head-to-head already shows the RAG *beats* the raw frontier model on references and *loses* on answer composition — so the remaining wins are: (a) complete the user-channel prompt consolidation (I2), (b) extend verbatim grounding breadth (`REGENOLD_GROUNDING_MAX_REFS` beyond 3; the code flags this as the next lever), (c) keep Stage-2 answer-first (R312) which measured +0.100 answer_correctness.
2. **Self-consistency for the verdict:** for classification-shaped questions, sample the Stage-2 verdict at k=3 (temperature 0.3), majority-vote the tier, and pin the wire citations to the winning tier's provisions. This is the proven technique for legal-classification accuracy and costs nothing when the answer cache is hot.
3. **Structured citation output:** have Stage-2 emit its citations as JSON in the user-message contract (already feasible through the wrapper) and validate against `ARTICLE_EXISTENCE` before prose assembly — replaces the regex-mined Component-D path.

### Evaluation (keep, and one addition)
- The 4-axis LLM-judge + gold-drop guard (hard rule #6) is the correct discipline and should be preserved. Add a **retrieval-only** diagnostic (Recall@5 at article level vs gold) to the scorecard so retrieval regressions are visible before they hit the answer axes, and record `rerank_stats()["attempts"]` in every A/B artifact so inert levers are impossible.

---

## Plan Alignment

`.planning/` contains extensive per-round checkpoints; no single plan was in scope for this review. Notable deviation candidates: R329's Cohere rerank and R313's faithfulness verifier both remain default-OFF against their own plan deadlines, and the graph expansion layers (2-hop/PPR/PathRAG) are built but effectively inert at the fusion step (R295) — flagging as status, not defect.

## Review Metadata

- **Agents dispatched:** Logic & Correctness; Error Handling & Edge Cases; Contract & Integration; Concurrency & State; Security (performed sequentially in-thread; findings verified by reading current code + runtime reproduction)
- **Scope:** full request path (`app/routes/regenold.py`, `app/engines/_graph_rag_impl.py`), retrieval stack (`kb_search`, `sentence_index`, `embeddings_index`, `entity_extractor`, `turboquant_index`, `cohere_rerank`, graph 2-hop/PPR/PathRAG), generation (`_two_stage_generate`, `_claude_max_enhance_answer`, `graph_rag_prompts`), post-processing (`models`, `answer_normaliser`, `grounded_prose`, `reasoning_trace`, `tone_guard`), infra (`main`, `config`, `evidence/store`, `rate_limit`, `openai_wrapper_provider`), tests (full hermetic suite)
- **Raw findings:** 13 → **Verified findings:** 9 (2 Important, 7 Suggestions)
- **Filtered out:** 4 (style/duplication nits without actionable anchor)
- **Test evidence:** 6364 passed, 35 skipped (hermetic run, `--timeout=45`, xdist=4)
- **Steering files consulted:** CLAUDE.md, README.md (noted: README claims "919-sentence index, sub-ms warm queries" — accurate; README's Neo4j "505 seeded nodes" reflects the Neo4j layout, not the default embedded/KB path)
