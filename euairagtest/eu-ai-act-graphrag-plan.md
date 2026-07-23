# EU AI Act — Hybrid GraphRAG Retrieval System: SOTA Deep Dive & Implementation Plan

**Goal:** A specialised retrieval + generation system over the EU AI Act (Regulation (EU) 2024/1689) that beats frontier LLMs on **recall, precision, answer correctness, and citation correctness at the article/subpoint level** (e.g., `Art. 6(2)(a)`, `Annex III point 5`, `Recital 27`).

**Date compiled:** 2026-07-22. **Verification:** every paper, repo, dataset, model, and API claim in this plan was independently fact-checked on 2026-07-22 by skeptical agents tasked to *disprove* each item. Of ~40 checked items, all but one resolved to a primary source (the lone exception is flagged `[unverified]` in §13); API/attribution corrections are folded in inline. Do not rely on anything marked `[unverified]`.

---

## 1. Thesis — why a specialised system beats a frontier LLM here

Frontier LLMs fail at fine-grained legal citation for three structural reasons, and each maps to a component below:

| Failure mode of a raw LLM | Root cause | What fixes it |
|---|---|---|
| Cites plausible-but-wrong provisions (`Art. 5` instead of `Art. 6(2)(a)`) | Parametric memory blurs provision boundaries | Stable provision IDs (ELI URI + Akoma Ntoso `eId`) as the citation atom; citation is a *retrieval join key*, not a generated string |
| Misses cross-referenced obligations (definition in Art. 3, list in Annex III, interpreting Recital) | No structural graph of the law | Knowledge graph with `crossReferences` / `definesTerm` / `groundedIn` edges traversed at query time |
| Fabricates support / low faithfulness | No grounding contract | Citation-constrained generation + NLI verification of every (claim → cited subpoint) pair |

The winning design is therefore **structure-preserving KG + hybrid retrieval + citation-verified generation**, not a bigger model. This is corroborated by *"Beyond Probabilistic Similarity: Structural, Temporal, and Causal Limitations of RAG in the Legal Domain"* `[2026 — verify]` and *"Let's have a Chat with the EU AI Act"* (arXiv:2505.11946), which found graph-based RAG beats naive RAG on multi-hop article references.

---

## 2. Target architecture (6 layers)

```
┌─ L0 INGEST ────────────────────────────────────────────────────────────┐
│ EUR-Lex CELEX 32024R1689 (Formex XML via Cellar SPARQL)                  │
│   └ or HF dataset jeroenherczeg/eu-ai-act (pre-structured Parquet)       │
│ parse → structure-aware chunks (paragraph/point) + stable provision IDs  │
│   ID = ELI work URI + Akoma Ntoso eId  e.g. .../2024/1689/oj#art_6__para_2__point_a
└──────────────────────────────────────────────────────────────────────────┘
           │ chunks + metadata                    │ entities + relations
           ▼                                       ▼
┌─ L2 HYBRID INDEX ──────────────┐   ┌─ L1 KNOWLEDGE GRAPH + ONTOLOGY ─────┐
│ Qdrant                          │   │ Neo4j (property graph)              │
│  • dense  (Qwen3-Embed-8B /     │   │  ontology: LKIF-Core + LegalRuleML  │
│            voyage-law-2)        │◄─►│  + ELI + LRMoo (temporal)           │
│  • sparse (SPLADE-v3 + BM25F)   │   │  Provision / DeonticStatement /     │
│  • late-int (BGE-M3 multivec)   │   │  Concept / Actor / Annex / Recital  │
│  join key = provision_id ───────┼───┼─ same provision_id                  │
└─────────────────────────────────┘   │ (+ optional GraphDB RDF sidecar     │
           ▲                            │  for OWL inference)                │
           │                            └──────────────────────────────────┘
┌─ L3 QUERY / ORCHESTRATION ─────────────────────────────────────────────┐
│ RQ-RAG query decomposition → route (lookup | multi-hop | thematic)      │
│ retrieve: Qdrant hybrid ∥ Neo4j VectorCypherRetriever (graph expansion) │
│ → RRF fuse (k=60) → rerank (Voyage Rerank 2.5 / Qwen3-Reranker-8B)      │
│ → CRAG corrective check (re-retrieve if low relevance)                  │
└──────────────────────────────────────────────────────────────────────────┘
           ▼
┌─ L4 CITATION-CORRECT GENERATION ───────────────────────────────────────┐
│ cite-as-you-generate constrained to retrieved provision_ids            │
│ multi-agent (LegalGraphRAG pattern): Researcher → Auditor(NLI) →       │
│ Adjudicator → answer with Art. X(Y)(z) citations                        │
│ post-hoc NLI verify (nli-deberta-v3-large): each claim ⊨ cited subpoint │
└──────────────────────────────────────────────────────────────────────────┘
           ▼
┌─ L5 EVALUATION HARNESS ────────────────────────────────────────────────┐
│ gold QA set (200–500 Qs, subpoint citations) → citation P/R/F1,        │
│ recall@k/nDCG@k, answer EM/ROUGE/BERTScore, RAGAS/ARES/DeepEval         │
│ baselines: frontier LLM long-context + naive dense RAG                  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Layer 0 — Corpus, structure & ingestion

**The Act:** 113 articles, 180 recitals, 13 annexes (I–XIII), 13 chapters. `Article 3` holds 65 numbered definitions — the densest cross-reference hub. Hierarchy: Chapter → Section → Article → Paragraph (1,2,3) → Point (a,b,c) → Sub-point (i,ii). Recitals `(1)–(180)` precede operative text. Heavy external references to GDPR (Reg. 2016/679, 30+ times), LED 2016/680, Reg. 2018/1725, sectoral NLF regs (Annex I), Cybersecurity Act 2019/881, MDR 2017/745.

**Sources (verified URLs):**
- EUR-Lex canonical: `https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng` — HTML, PDF, **Formex 4 XML** (native), 24 languages (swap `/EN/`→`/FR/` etc.). CELEX **32024R1689**.
- Cellar SPARQL endpoint: `https://publications.europa.eu/webapi/rdf/sparql` (resolve CELEX → work URI → Formex manifestation).
- AKN4EU (Akoma Ntoso) pipeline: `https://op.europa.eu/en/web/eu-vocabularies/akn4eu` (not guaranteed served per-act; check Cellar).
- **Shortcut dataset (verified, recommended):** HF `jeroenherczeg/eu-ai-act` — confirmed: 2,610 Parquet rows, CC BY 4.0, actively maintained. All claimed fields present: `id`, `chunk_type`, `citation_label`, `structure_path`, `article_no`, `paragraph_no`, `recital_no`, `annex_no`, `references_articles`, `defined_terms`, `effective_from` (plus `chapter_no`, `section_no`, `interprets_articles`, `transitional`, `celex`, `source_url`, `parent_structure_path`). Best-in-class for provision-level citation — use as the primary ingestion shortcut; keep Formex-via-Cellar as the authoritative cross-check. For retrieval eval, HF `danielnoumon/eu-ai-act-nl-queries` (2,284 synthetic Dutch query→chunk pairs, CC BY 4.0) is an optional add.
- **Granularity caveat (verified 2026-07-22):** the `jeroenherczeg` dataset is **paragraph-grain only** — its finest article rows are e.g. `art_5__para_1`, with **no** point/sub-point rows. The gold benchmark's citations need `(a)`/`(i)` grain, so Phase-1 ingestion recovers points & sub-points **deterministically** by parsing enumerated markers (`(a) … (b) …`, roman `(i) … (ii) …`) out of paragraph text — no LLM, zero hallucination — while Formex-via-Cellar stays the authoritative cross-check. Its `structure_path` uses `/`+`:` separators (`art:6/par:2` → `art_6__para_2`; `anx:III/sec:3` → `annex_III__point_3`).
- Human reference / URLs per provision: AI Act Explorer (Future of Life Institute) `https://artificialintelligenceact.eu/ai-act-explorer/`.

**Parsers (repos):**
- `noworneverev/eurlex-parser` (Python) — CELEX → structured JSON + Pandas.
- `maastrichtlawtech/eur-lex-visualiser` (JS/TS) — Formex → articles/recitals/annexes + resolves cross-references.
- `ndrplz/eurlex-toolbox` (Python) — bulk Formex download/parse, `EurLexDoc`/`EurLexDataset`.
- `laws-africa/cobalt` + `laws-africa/bluebell` (Python) — Akoma Ntoso parsing + FRBR URI manipulation.

**Chunking rules (structure-preserving):**
- Paragraph-level chunks (<200 tokens); prefix parent context: `"Article 6 | Paragraph 2: …"`.
- Long/enumerated articles (Art. 3, 9, 10) → chunk per point; each carries `article/paragraph/point` metadata.
- One chunk per recital (`interprets_articles[]`); one chunk per annex point.
- **`provision_id` is the stable join key** between the vector index and the graph.

**Chunk metadata schema:**
```json
{
  "provision_id": "art_6__para_2__point_a",
  "eli_uri": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj#art_6__para_2__point_a",
  "citation": "Art. 6(2)(a)",
  "chapter": 3, "article": 6, "paragraph": 2, "point": "a",
  "text": "…point text…",
  "parent_text": "…paragraph 2 text…",
  "defined_terms": ["high-risk AI system"],
  "references_internal": ["art_3__para_1", "annex_III"],
  "references_external": ["32016R0679__art_6"],
  "effective_from": "2026-08-02",
  "celex": "32024R1689",
  "lang": "en"
}
```

---

## 4. Layer 1 — Knowledge graph & ontology

**Standards to combine (each earns its place):**
- **Akoma Ntoso / OASIS LegalDocML** (`eId`/`wId`) — the only standard giving *composable, stable, subpoint-level* IDs (`art_6__para_2__point_a`). Use `eId` as canonical node ID. `[foundational]`
- **ELI (European Legislation Identifier) + ELI ontology** — stable HTTP work URI (`.../eli/reg/2024/1689/oj`); fragment with AKN `eId` for provision URIs. `[foundational]`
- **LKIF-Core** (`github.com/RinkeHoekstra/lkif-core`) — upper ontology: `Norm`, `Actor`, `Role`, `Obligation`. **Verified stale (2026-07-22):** unmaintained, OWL-DL era, no DPV alignment — **reference only**. Borrow the `Norm`/`Role` distinctions conceptually but do **not** import it. For the actor/role + risk vocabulary lean on **DPV v2.0** (W3C Data Privacy Vocabulary, actively maintained) and **AIRO** (AI Risk Ontology, EU-AI-Act-aligned). `[reference]`
- **LegalRuleML** (OASIS Standard v1.0, 2021) — deontic layer: `Obligation`/`Prohibition`/`Permission`/`Right` with `Bearer` + activation condition + violation consequence. Highest-value layer for compliance Q&A (the Act is a web of provider/deployer/importer obligations). `[foundational]`
- **LRMoo** (supersedes FRBRoo) — Work/Expression/Manifestation for temporal versioning as implementing acts accumulate. Refs (both verified, both Brazilian-law case studies — adapt): arXiv:2506.07853 (diachronic norm evolution), arXiv:2508.00827 (URI-addressable abstract works).
- **Skip:** raw FRBR/FRBRoo (subsumed by Cellar CDM/LRMoo), LKIF's rule layer (use LegalRuleML).

**Prior art (read these):**
- TAIR ontology — *"An Open KG-Based Approach for Mapping Concepts and Requirements between the EU AI Act and International Standards"* (arXiv:2408.11925, verified) — EU-AI-Act-specific ontology mapping the Act to ISO management standards; **reusable schema layer**. INTEGRATE.
- **SAT-Graph RAG** — *"An Ontology-Driven Graph RAG for Legal Norms: A Structural, Temporal, and Deterministic Approach"* (arXiv:2505.00039, JURIX 2025, verified) — ontology-grounded KG separating abstract works from versioned instances + legislative-event modelling; deterministic ⇒ auditable citations. Case study is Brazil's Constitution, so adapt the schema. INTEGRATE (core temporal-versioning pattern).
- *"KG Representations for LLM-Based Policy Compliance Reasoning"* (arXiv:2604.27713, verified) — compares ontology schemas over AI-risk policy docs (42 QA tasks). Note: **generic AI-policy, not EU-AI-Act-specific** (that specificity was overstated) — take the schema-comparison methodology, not a ready ontology. OPTIONAL.

**Proposed schema:**

*Nodes (14, as built in `graph/schema.py`):* **structural (deterministic):** `Provision` (Article/Paragraph/Point/Subpoint; props `eId`, `eliUri`, `text`, `level`, `synthesized`), `Recital`, `Annex`, `AnnexPoint`, `DefinedTerm` (Art. 3 entries), `ExternalRegulation`, `DateMilestone`. **controlled vocabulary (seeded):** `Actor` (7 roles: Provider/Deployer/AuthorisedRepresentative/Importer/Distributor/ProductManufacturer/NotifiedBody, each anchored to its Art. 3 definition), `RiskClass` (6: prohibited→Art. 5, high_risk→Art. 6, limited_risk→Art. 50, minimal_risk, gpai/gpai_systemic→Art. 51). **enrichment (ML-populated):** `DeonticStatement` (`deonticType`, `bearer`), `AISystem`, `Condition`, `Sanction`, `HarmonisedStandard`.

*Edges (18, partitioned in `schema.py` into `DETERMINISTIC_EDGES` ∪ `ENRICHMENT_EDGES`, verified total & disjoint by test):* **deterministic (6):** `HAS_CHILD` (hierarchy, w/ synthesized ancestors), `CROSS_REFERENCES_INTERNAL` (metadata + in-text, tagged by `provenance`), `CROSS_REFERENCES_EXTERNAL` (→ExternalRegulation), `USES_TERM` (Provision→DefinedTerm), `INTERPRETED_BY` (Provision→Recital), `APPLIES_FROM` (→DateMilestone). **enrichment (10):** `DEFINES_TERM`, `LISTED_IN` (AnnexPoint→Provision), `AMENDS`/`SUPERSEDED_BY` (temporal), `GROUNDED_IN` (DeonticStatement→Provision), `BEARER_OF` (Actor→DeonticStatement), `HAS_CONDITION`/`HAS_CONSEQUENCE` (→Condition/Sanction), `CLASSIFIED_AS` (AISystem→RiskClass), `PRESUMES_CONFORMITY_WITH` (HarmonisedStandard→Provision). Every edge type declares its endpoint node-types in `EDGE_ENDPOINTS` (also test-enforced total).

**Why this enables subpoint citation:** a query like *"what must a provider of a high-risk AI system do?"* walks `Actor(Provider) —bearerOf→ DeonticStatement —groundedIn→ Provision`, filtered by `bearer=Provider`, returning exact `Provision` nodes with their `eliUri` fragment — a verifiable citation, not a generated guess.

**Extraction tooling (cascade, deterministic-first to minimise hallucination):**
1. **Hand-rolled regex** (`graph/citations.py`, no spaCy dependency) — citation strings (`Article 6(2)(a)`, `Annex III point 4(a)`, `Recital (5)`) and cross-refs, reconstructed into canonical form and round-tripped through `ProvisionId.from_citation`. **Zero hallucination**; deliberately ignores `(EU)`/year parens so `Regulation (EU) 2016/679` is not mis-parsed as an article point. This is the whole deterministic backbone — everything in the six `DETERMINISTIC_EDGES` is derived from Phase-1 `Provision` metadata + this parser, and is fully offline-testable.
2. **GLiNER-Relex v0.5** (`knowledgator/gliner-relex-large-v0.5`, verified May 2026) — joint zero-shot **NER + relation extraction in one encoder pass**; supersedes the plan's original separate GLiNER + ReLiK relation step. Keep `ReLiK` (`github.com/SapienzaNLP/relik`, arXiv:2408.00103) only for entity-linking of external refs to CELEX ids.
3. `LlamaIndex SchemaLLMPathExtractor` — **schema-constrained** LLM second pass: declare allowed node/relation types so the LLM cannot invent relations. Populates the ten `ENRICHMENT_EDGES` (deontic/actor/risk layer).

**Testability split (mirrors Phase 1):** steps 2–3 live behind the optional `enrich` extra and are imported *lazily* — the extractor emits plain `DeonticExtraction` records; `apply_deontic_extractions()` merges them into the graph **deterministically and is fully unit-tested with no models installed**. So the entire build → query → Cypher-export surface is exercised offline; only the model wiring itself needs the heavy deps.

**Store:** Neo4j primary (property graph), verified current release **2026.05**. The offline core is a **hand-rolled `KnowledgeGraph` (dataclasses/Pydantic) + idempotent `MERGE`-based Cypher emitter** (`graph/cypher.py`) — deliberately *not* NetworkX/rdflib/Kùzu (Kùzu was archived Oct 2025). Cypher output is deterministic, string-escaped, and skips dangling edges, so a graph built in-process loads into a live Neo4j with `CREATE CONSTRAINT … REQUIRE n.id IS UNIQUE` + node/edge `MERGE`. Add **GraphDB (Ontotext)** as an RDF/OWL sidecar only if you need inference (`HighRiskSystem ⊑ AISystem`, SHACL conformance).

---

## 5. Layer 2 — Hybrid retrieval stack

| Component | Choice | Why |
|---|---|---|
| Dense (primary) | `Qwen/Qwen3-Embedding-8B` | MTEB-multilingual #1 (~70.6), 32K ctx, 100+ langs — matters for 24 EU languages |
| Dense (legal) | `voyage-law-2` (API) | Trained on 1T legal tokens; +6% avg over `text-embedding-3-large` on legal retrieval (English/German strongest). Optional 2nd retriever |
| Sparse | `naver/splade-v3-doc` + BM25F | Exact article-number & defined-term matching; BM25F upweights the article-number field |
| Late interaction | `BAAI/bge-m3` multi-vector head (or `colbert-ir/colbertv2.0` + PLAID) | MaxSim precision; BGE-M3 emits dense+sparse+ColBERT from one model |
| Graph expansion | Neo4j traversal from seed provisions | Pulls cited articles, Art. 3 definitions, Annex items, interpreting recitals into the candidate set |
| Fusion | Reciprocal Rank Fusion, k=60 | No score calibration needed across dense/sparse/graph |
| Reranker | `Voyage Rerank 2.5` (API) or `Qwen/Qwen3-Reranker-8B` / `BAAI/bge-reranker-v2-m3` (self-host) | Highest NDCG@10 on legal/multilingual |
| Vector store | **Qdrant** | Native hybrid `query_points()` + `prefetch` + `{"rrf":{"k":60}}`; built-in BM25/IDF |

**Key code surface:**
- `BGEM3FlagModel.encode(texts, return_dense=True, return_sparse=True, return_colbert_vecs=True)` (`FlagEmbedding`).
- Qdrant hybrid (corrected API): `client.query_points(coll, prefetch=[Prefetch(query=dense, using="dense"), Prefetch(query=sparse, using="sparse")], query=RrfQuery(rrf=Rrf()))` — RRF is `RrfQuery`/`Rrf`; `FusionQuery(fusion=Fusion.RRF)` is **wrong** (that path selects DBSF).
- Rerank: `CrossEncoder("BAAI/bge-reranker-v2-m3").rank(query, docs)` or `cohere.rerank()` / Voyage `POST /v1/rerank`.
- Verified model refs: Qwen3-Embedding-8B (Apache-2.0; #1 MTEB-multilingual 70.58, Jun 2025), Qwen3-Reranker-8B (arXiv:2506.05176), mxbai-rerank-large-v2 (arXiv:2506.03487; 2B, RL-trained, Apache-2.0), SPLADE-v3 (arXiv:2403.06789), voyage-law-2 (+6.17 pp NDCG@10 vs text-embedding-3-large; Apr-2024), Voyage rerank-2.5 (+7.94% vs Cohere v3.5; Aug-2025). Jina v5: cite the HF model card for the 677M / MTEB-v2 71.7 figures, not the arXiv abstract (which covers the distilled small/nano variants).

**Evidence:** *"Know When to Fuse"* (arXiv:2409.01357, COLING 2025) — the one paper on non-English *legal* hybrid retrieval: **zero-shot hybrid always beats any single model**, but an **in-domain fine-tuned single retriever can match/beat RRF**. → Highest-leverage upgrade: fine-tune BGE-M3 / multilingual-e5 on labelled `(query, relevant-article)` pairs. French legal SPLADE/ColBERT released at `github.com/maastrichtlawtech/fusion`.

---

## 6. Layer 3+4 — Orchestration, generation & citation correctness

**Query understanding:** RQ-RAG (arXiv:2404.00610, `github.com/chanchimin/RQ-RAG`) decomposes/rewrites ambiguous refs ("*the* high-risk systems" → which Annex III category). Route to: (a) factual lookup, (b) multi-hop cross-reference, (c) thematic/global.

**Retrieval loop:** CRAG (arXiv:2401.15884, `github.com/HuskyInSalt/CRAG`) — lightweight evaluator scores retrieved-chunk relevance; re-retrieve/expand when low. Optionally Self-RAG (arXiv:2310.11511) reflection tokens if you fine-tune.

**Generation — cite-as-you-generate:** constrain citations to the retrieved `provision_id` set; system prompt enforces `Art. X(Y)(z)` / `Annex N point M` / `Recital (K)` format. Because IDs come from retrieval, the model *selects* citations rather than *inventing* them.

**Citation training/alignment:**
- **SelfCite** (arXiv:2502.09604, `github.com/facebookresearch/SelfCite`) — self-supervised via context-ablation reward (a citation is *necessary* if removing it changes the answer; *sufficient* if keeping only it preserves it). +5.3 citation F1 on LongBench-Cite. `[foundational]`
- **LongCite** (arXiv:2409.02897) — sentence-level citation on long context; LongCite-45k SFT set. `[foundational]`

**Multi-agent verification (LegalGraphRAG pattern):** Researcher (retrieve) → **Auditor** (NLI-verify each retrieved passage supports the claim) → Adjudicator (synthesize). Repo `github.com/XMUDeepLIT/LegalGraphRAG`, arXiv:2605.28120 `[2026 — verify]`.

**Post-hoc verification (always on):** for each (answer-sentence, cited `provision_id`), run NLI entailment with `cross-encoder/nli-deberta-v3-large`; flag any citation to a provision **not in the retrieved context** or **not entailing** the sentence. This is the ALCE (arXiv:2305.14627) methodology adapted to subpoint granularity. Additionally build a **citation graph** (which provisions cite/are-cited-by which) and cross-check every generated citation against it to catch fabricated or structurally implausible references — the *Citation Grounding* technique (arXiv:2606.00898, verified). Consider *LexPath* (arXiv:2605.30205, verified) multi-path retrieval (lexical + structural + semantic paths) as the L2 retrieval topology, which maps cleanly onto article/subpoint citation.

---

## 7. Which GraphRAG framework? (recommendation)

No single OSS framework is ideal for hierarchical statute + subpoint citation. Recommended composition:

- **Indexing backbone — RAPTOR** (arXiv:2401.18059, `github.com/parthsarthi03/raptor`): force cluster boundaries at article/chapter level so summary nodes = Article/Chapter summaries and leaves = subpoints. Mirrors the Act's hierarchy; enables "retrieve subpoint + parent-article summary." `[foundational]`
- **Structured facts / mutual index — KAG** (arXiv:2409.13731, `github.com/OpenSPG/KAG`): schema-constrained extraction + logical-form multi-hop reasoning; strongest reported in professional/vertical domains (+33.5% F1 on 2WikiMultiHop). Cleaner than LightRAG's OpenIE triples on dense legal syntax. `[foundational]`
- **Cross-reference traversal — PathRAG** (arXiv:2502.14902, `github.com/BUPT-GAMMA/PathRAG`) or **HippoRAG 2** (arXiv:2502.14802, `github.com/OSU-NLP-Group/HippoRAG`): PathRAG's relational *paths* map node→document-location, translating directly into citation chains; HippoRAG 2's Personalized-PageRank follows definitional/exception cascades. `[foundational]`
- **Do NOT** use vanilla Microsoft GraphRAG (arXiv:2404.16130) as the core: Leiden community summaries target *thematic* global queries and collapse the subpoint granularity you need (good only for "summarise the whole GPAI chapter" style questions; keep its *global search* as an optional thematic mode). LightRAG (arXiv:2410.05779) is a fine cheaper baseline.

**Framework selection reference:** *"When to use Graphs in RAG: A Comprehensive Analysis..."* / GraphRAG-Bench (arXiv:2506.05690, verified) — GraphRAG wins on multi-fact aggregation (the legal cross-reference case), vanilla RAG is competitive on single-fact; and *WildGraphBench* (arXiv:2602.02053, verified) warns GraphRAG can *hurt* pure summarization by favouring breadth over specifics — a real risk for recital text, so route thematic/summary queries separately. Build a small comparison harness before committing.

---

## 8. Layer 5 — Evaluation protocol (how you *prove* you beat frontier LLMs)

**Build a gold set (200–500 Qs)**, stratified across: prohibited practices (Art. 5), high-risk classification (Art. 6 + Annex III), high-risk requirements (Art. 8–15), GPAI (Art. 51–55), governance/enforcement, transparency (Art. 50). For each Q: gold answer + **exhaustive necessary-and-sufficient citation set at `(Art, para, point)` granularity**, 2 annotators + adjudication. Include **negative controls** (out-of-scope → cite nothing) and **hallucination traps** (questions where LLMs invent plausible non-existent provisions). Construction follows **arXiv:2603.09435** (Davvetas et al., *AI Act Evaluation Benchmark* — closest prior art: same risk-tier × task-category axes), extended with subpoint-level citation sets, negative controls, and hallucination traps; annotation/citation methodology also mirrors COLIEE Task 3/4 and LongBench-Cite.

**Metrics (priority order):**

| Metric | Tool / method |
|---|---|
| **Citation precision / recall / F1 at subpoint level** (the core claim) | NLI verifier (`cross-encoder/nli-deberta-v3-large`) over (sentence, cited provision) pairs — ALCE style |
| Retrieval recall@k / nDCG@k / MRR (subpoint units) | standard IR |
| Answer correctness | EM / ROUGE-L / BERTScore + LLM-as-judge rubric |
| Faithfulness, context precision/recall | RAGAS `evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_precision, context_recall])` (`github.com/explodinggradients/ragas`) |
| Calibrated relevance/faithfulness | ARES (arXiv:2311.09476, `github.com/stanford-futuredata/ARES`) — PPI confidence intervals |
| Hallucination rate (citations to non-existent provisions) | DeepEval `HallucinationMetric` |

**Baselines to beat:** (1) frontier LLM (GPT-4o / Claude) with the **full Act in long context**; (2) naive dense RAG (no graph). Win condition: higher **citation F1** and lower **hallucination rate** than both, at article+subpoint granularity. Report with bootstrap 95% CIs.

**Measurement hygiene (must hold before any "beats frontier LLMs" claim):**
- **Granularity-matched scoring (#1).** The gold set deliberately mixes citation grains (`art_10`, `art_10__para_3`, `art_50__para_6`). Naïve exact set-matching conflates a *granularity mismatch* with a *real* error — it ends up measuring granularity, not correctness. Score P/R/F1 with **hierarchical / partial credit** over the provision tree: an ancestor/descendant of a gold node earns partial credit (predicting `art_10` when gold is `art_10__para_3` is a granularity miss, not a hallucination), and normalise both sides to a canonical grain before the exact-match pass. Reserve zero credit for genuinely wrong or non-existent provisions.
- **Statistical power (#2).** The false-positive rate currently rests on **6 negative controls** and the hallucination rate on **8 traps** (1 shared — see below). Under the bootstrap 95% CIs above, those CIs are very wide: treat the current set as a **smoke test**, not evidence for a headline claim. When scaling to 200–500, prioritise **more negative controls + traps**, concentrated in the rarest / highest-value cells (obscure sub-points, cross-regulation confusions, non-existent-provision traps).
- **Metric independence (#3).** `hard_gov_005` is simultaneously a negative control *and* a hallucination trap, so it enters **both** denominators — the FP rate and hallucination rate are not statistically independent. `build_dataset.py` now emits `negative_control_and_trap` to make the overlap auditable; report it, and at scale split such items so the two metrics have disjoint support.
- **Contamination (#5).** Because the construction follows the openly-published **arXiv:2603.09435** dataset, frontier baselines may be **contaminated** (trained on it). Our newly-authored items give a cleaner baseline but **inherit its taxonomy**. Its reported **0.87 / 0.85 F1** (prohibited / high-risk scenarios) is a useful *external* reference point, not a like-for-like target (different granularity and scoring).

**Related benchmarks/systems:** **AI Act Evaluation Benchmark** (arXiv:2603.09435, Davvetas et al., verified — closest prior art), LegalBench (arXiv:2308.11462), LexGLUE/EURLEX (arXiv:2110.00976), LEXTREME/MultiLegalPile 24-lang (arXiv:2306.02069), SaulLM-141B legal LLM baseline (arXiv:2407.19584), LexRAG (arXiv:2502.20640).

---

## 9. Recommended tech stack (concrete)

| Concern | Pick | Package / version |
|---|---|---|
| Graph DB | **Neo4j** (Community/AuraDB Free) | `neo4j-graphrag` v1.18.0 |
| RDF/OWL sidecar (optional) | GraphDB Free (Ontotext) | v11.x |
| Vector store | **Qdrant** (single-node Docker) | native hybrid API |
| Orchestration | **LlamaIndex** `PropertyGraphIndex` | `SchemaLLMPathExtractor`, `VectorContextRetriever`, `VectorCypherRetriever` |
| (alt) Orchestration | LangChain/LangGraph | `LLMGraphTransformer`, `Neo4jVector`, `GraphCypherQAChain` |
| Dense embed | Qwen3-Embedding-8B (+ voyage-law-2) | `sentence-transformers` / API |
| Sparse | SPLADE-v3 + BM25F | `naver/splade-v3-doc` |
| Late interaction | BGE-M3 | `FlagEmbedding` |
| Reranker | Voyage Rerank 2.5 / Qwen3-Reranker-8B / bge-reranker-v2-m3 | API / `sentence-transformers` |
| NER/RE | spaCy + GLiNER + ReLiK | `gliner`, `relik` |
| Citation NLI | `cross-encoder/nli-deberta-v3-large` | `sentence-transformers` |
| Eval | RAGAS + ARES + DeepEval | see §8 |

---

## 10. LLM tiering & cost-aware model routing

You'll run a mix of **Opus 4.8** (most capable), **Sonnet 5** (workhorse), and **free-tier / Haiku-class daily-quota** models. Rule of thumb: spend capability where *correctness compounds* (one-time KG extraction; the final citation-bearing answer), use the middle tier for batch reasoning, and push high-volume/latency-sensitive classification to the cheapest tier — or, better, to a **dedicated small model** (cross-encoder / GLiNER) with no LLM at all, which beats any LLM tier on both cost and determinism for classification/NLI/NER.

| Stage | When | Task character | Model tier |
|---|---|---|---|
| KG triple/relation extraction (`SchemaLLMPathExtractor`, LLM enrichment pass) | Offline, once | High-accuracy structured extraction; errors propagate to every future answer | **Opus 4.8** |
| Deterministic NER + relation extraction (spaCy, GLiNER, ReLiK) | Offline, once | Pattern / zero-shot extraction | **No LLM** (dedicated models) |
| Recital/chapter summarization (RAPTOR tree, community reports) | Offline, batch | Summarization at volume | **Sonnet 5** |
| Intent classification / query routing (lookup vs multi-hop vs thematic) | Per query, high volume, latency-critical | Simple label | **Free-tier / Haiku** (or a fine-tuned classifier) |
| Query decomposition / rewrite (RQ-RAG) | Per query | Simple rewrite → free-tier; genuine multi-hop decomposition → Sonnet 5 | **Free-tier → Sonnet 5** |
| Retrieval relevance grading (CRAG) | Per candidate chunk | Binary / graded relevance | **Reranker score threshold (no LLM)**, else free-tier/Haiku |
| Citation entailment check (Auditor: claim ⊨ cited subpoint) | Per claim | NLI | **`cross-encoder/nli-deberta-v3-large` (no LLM)**; escalate ambiguous cases to Sonnet 5 |
| Final answer synthesis with citations (Researcher/Adjudicator) | Per query | High-stakes generation — the whole point | **Opus 4.8** (Sonnet 5 as budget/latency fallback) |
| Eval LLM-as-judge (answer correctness, faithfulness rubric) | Offline | Judgment | **Opus 4.8** — but beware same-family self-preference; ideally judge with a *different* family or anchor to human labels |

**Cross-cutting cost levers:**
- **Prompt-cache the static context.** The AI Act text + system/ontology prompt are fixed — cache them so per-query cost is dominated by the (small) query + retrieved chunks, not the corpus.
- **Structured outputs / tool-calling** for routing, extraction, and citation emission — cheaper, parseable, and lets the free-tier model punch above its weight on classification.
- **Prefer non-LLM components** for classification/NLI/NER (rerankers, GLiNER, NLI cross-encoders): cheaper *and* deterministic, which matters for auditable citations.
- **Budget guard:** the two line items that dominate quality are one-time KG extraction (Opus 4.8, amortized to ~0 per query) and final answer generation (Opus 4.8 / Sonnet 5). Everything else should be free-tier or no-LLM.

## 11. Implementation roadmap

**Phase 1 — Corpus & structure (week 1–2).** Pull CELEX 32024R1689 Formex via Cellar SPARQL (or verify/adopt `jeroenherczeg/eu-ai-act`). Parse with `noworneverev/eurlex-parser`; emit structure-preserving chunks with `provision_id` = ELI+`eId` and full metadata (§3). Deliverable: JSON/Parquet of all provisions + recitals + annex points with stable IDs.

> **Status (2026-07-22): ingested against the live HF corpus, tested.** Working `euaiact-graphrag` package at [`eu-ai-act-graphrag/`](eu-ai-act-graphrag/) — pure-stdlib `ProvisionId` parser (eid ⇄ citation ⇄ ELI, round-trips all 137 gold-benchmark IDs), Pydantic v2 `Provision` model, HF row→`Provision` loader with the `structure_path` transform, and the deterministic point/sub-point splitter (see §3 granularity caveat). CLI `euaiact-ingest` emits JSON + Parquet. **Live pull done:** the real `jeroenherczeg/eu-ai-act` corpus now ingests to **1,318 English provisions** (`data/provisions.json`; annex_item=47, annex_subpoint=60, article_full=113, paragraph=568, point=322, recital=180, subpoint=28; 29 unmapped). Three real bugs the 24-row sample never exposed were fixed on the way: (1) a **language filter** (`--lang`, default `en`) — the corpus ships EN/NL/FR rows sharing one `structure_path`, so without it every id collides across languages (last-writer-wins node text); (2) **parquet schema inference** (`infer_schema_length=None`) so all-None column heads don't mis-type nullable ints as Null; (3) an **Art. 3 definitions splitter** (`split_definitions`) — Art. 3 is one monolithic `article_full` blob of `(N) "term" means …` definitions, split deterministically into `art_3__para_N` to reach the gold set's grain. Coverage of the 137 gold-benchmark provision ids: all **137/137 are reachable graph nodes** (0 missing from the `known_provisions` registry); in the flat text corpus itself **133/137** appear as ingested rows. The 4 exceptions are annex *roots* (`annex_I`, `annex_II`, `annex_XI`, `annex_XII`): the HF dataset ships **no** bare-annex-root rows — annex content exists only at section/point grain — so each root has children in the corpus but no text row of its own, and the graph synthesizes it as an ancestor. That gap is itself a point *for* the thesis: the graph reaches gold nodes a flat retriever over the corpus cannot. Remaining open item: the point/sub-point grain is still recovered heuristically from prose — the Formex-via-Cellar cross-check (done 2026-07-23, see §11) now authoritatively confirms the article/recital/annex layer but not the enumerated sub-provisions.

**Phase 2 — Knowledge graph (week 2–4).** Model ontology (LegalRuleML + ELI + AKN `eId`; DPV/AIRO for the actor/risk vocab) in Neo4j. Extraction cascade: hand-rolled citation regex → GLiNER-Relex v0.5 entities+relations → `SchemaLLMPathExtractor` enrichment. Build `HAS_CHILD`, `CROSS_REFERENCES_*`, `USES_TERM`, `INTERPRETED_BY`, `APPLIES_FROM` deterministically; `GROUNDED_IN`/`BEARER_OF`/etc. via enrichment. Deliverable: queryable KG; sanity Cypher for "all provisions referencing Art. 6(2)."

> **Status (2026-07-22): deterministic backbone built from the full corpus, tested & exporting; ML enrichment stubbed.** `euaiact-graph` sub-package (`src/euaiact/graph/`) with a hand-rolled in-memory `KnowledgeGraph`, 14-node / 16-edge ontology (6 deterministic + 10 enrichment; `schema.py`, edge-partition + endpoint invariants test-enforced), zero-hallucination citation extractor (`citations.py`), deterministic `build_graph()` (synthesizes missing ancestors; tags cross-refs by `provenance=metadata|text`; seeds the Actor/RiskClass controlled vocab), and an idempotent `MERGE`-based Cypher/JSON emitter (`cypher.py`). CLI `euaiact-graph`. **Built from the real 1,318-provision corpus:** `data/graph.json` = **1,387 nodes / 5,899 edges** (edges: APPLIES_FROM=1,318, CROSS_REFERENCES_INTERNAL=1,352, HAS_CHILD=1,025, INTERPRETED_BY=51, USES_TERM=2,153; nodes span every article Art. 1–113, all 180 recitals, all annexes, plus the DefinedTerm/Actor/RiskClass/DateMilestone vocab). ML enrichment (GLiNER-Relex + schema-constrained LLM) is behind the lazy `enrich` extra: the model-free **merge** step (`apply_deontic_extractions`) is complete and unit-tested; the model wiring itself is the follow-up. **594 tests pass** (Phase-1 + graph + baselines) on synthetic fixtures. The earlier data-quality nit (spurious `Art. 261`/`Art. 290` nodes from mis-parsed textual cross-references) is resolved: the builder's article-range guard (≤113) drops all over-range refs, so the graph spans exactly Art. 1–113. Open item: wire the enrichment models.
>
> **§8 baselines wired (2026-07-22).** `src/euaiact/baselines/` emits scorer-ready `{item_id: [citation,…]}` JSON via `euaiact-baseline`: (1) a **naive lexical retriever** (`retrieval.py`, pure-Python TF-IDF cosine behind a `Retriever` ABC so a dense embedder drops in later — labelled honestly as lexical, not dense) feeding the `naive_rag` baseline; (2) a **frontier-LLM** baseline (`llm.py`, optional full-Act-in-context, behind the `baselines` extra + `ANTHROPIC_API_KEY`, lazily imported). First real numbers on the gold set, TF-IDF retrieval @k=5 vs the citation scorer (soft = hierarchical partial credit, exact = strict eid): **easy** soft-F1 **0.28** / exact-F1 0.24 (n=42); **hard** soft-F1 **0.29** / exact-F1 0.23 (answerable n=36). As expected for a retriever that always returns top-k and never abstains, it fails every abstention item — false-positive-rate 1.0 over 6 negative controls, hallucination-rate 1.0 over 8 traps — which is exactly the floor the graph + citation-verified generation has to beat. Scorer sanity holds on the real 1,345-id registry: `--oracle full` → soft=exact=1.00; `--oracle root` (article-only) → soft-F1 0.59 vs exact-F1 0.22, the granularity tax quantified. The LLM baseline is coded but unrun (no API key in-sandbox).

> **First graph-using retriever — honest head-to-head (2026-07-22).** `baselines/graph_rag.py` adds `GraphExpansionRetriever`/`GraphRAGBaseline` (`euaiact-baseline --baseline graphrag`): the first system that actually *uses* the Phase-2 KG for retrieval. TF-IDF lexical **seeds** → deterministic score-propagation along `HAS_CHILD` (parent 0.6 / child 0.5), `CROSS_REFERENCES_INTERNAL` (0.5), `INTERPRETED_BY` (0.4), scores **accumulating** per node (HippoRAG-2 style) so multi-seed convergence bubbles up; only citeable node types emitted; optional lexical-seed **abstention**. Deterministic, no ML/API/network; 10 new unit tests (27 baseline tests pass). Result vs TF-IDF @k=5 (soft = hierarchical partial credit, seed=0): **easy** (n=42, all single-hop) soft-F1 **0.280 → 0.350**, exact 0.242 → 0.260 — a real lift, though 95% CIs overlap ([0.201,0.354] vs [0.275,0.424]); **hard** (answerable n=36) soft-F1 0.291 → 0.302 (flat, +0.011) and exact-F1 **0.225 → 0.184 (worse)**; **hard multi-hop** (n=34), where graph expansion was *supposed* to shine, soft-F1 0.308 → 0.310 (flat) and exact-F1 0.238 → 0.195 (worse). **Two verified negative findings** (disprove-don't-rubber-stamp): (1) *deeper hops strictly hurt* — 2 hops soft 0.302/exact 0.174, 3 hops soft 0.275/exact 0.121 — because at k=5 the decayed distant nodes never outrank close neighbours, so extra hops add precision-diluting noise, not signal; and the mechanism is confirmed structurally: all 32 multi-hop items have every gold node present in the graph, yet only **8%** of required gold-citation *pairs* sit within 1 hop (42% @2, 67% @3) — the benchmark's "multi-hop" is *reasoning*-hops, not citation-graph adjacency. (2) *Lexical-seed abstention can't attack the FP=1.000 floor* — negative-control best-seed cosines (0.138–0.362) are fully interleaved with answerable items (median 0.271, min 0.160), so no threshold abstains on the 6 controls without gutting answerable recall; FP/hallucination stay 1.000. **Takeaway for the thesis:** deterministic structural expansion gives a modest lift on straightforward single-hop lookup but does *not* deliver multi-hop citation gains and costs exact precision — evidence that beating the LLM on hard items needs the *semantic* layers (dense seeds + CRAG re-rank + NLI-verified generation), with the graph better used as a Phase-4 grounding/verification substrate than as a first-stage expander.

> **Semantic-seed upgrade via offline LSA — honest negative (2026-07-22).** Before reaching for a neural dense embedder (unrunnable in-sandbox: no torch/network/key), tested the *runnable-now* semantic proxy: `baselines/lsa.py` `LsaRetriever` — classical latent-semantic analysis, a deterministic randomized truncated-SVD (Halko et al., sklearn's method) over the TF-IDF term-document matrix (V=2,837 @ min_df=2, k=200 components in ~2s), labelled honestly as *classical LSA, not a neural dense embedder*. It plugs behind the same `Retriever` ABC both as a standalone baseline (`--baseline lsa`) and as a graph **seeder** (`--seeder lsa`); 6 new unit tests prove the one property TF-IDF lacks (two provisions sharing *no* surface term still co-rank via shared latent topics) and full determinism (23 → 33 baseline tests pass). **Result: the semantic seeds do not help on this corpus/benchmark, and on the one slice that was winning they hurt.** Head-to-head @k=5 (soft-F1, seed=0, n_boot=2000): **easy** — TF-IDF flat 0.280, LSA flat 0.273 (tied within noise); graphrag+TF-IDF **0.350** but graphrag+**LSA** 0.275, i.e. swapping LSA seeds *erased the entire easy graph-expansion lift* (exact 0.260 → 0.221). **hard** (answerable n=36) — TF-IDF 0.291, LSA 0.279; graphrag+TF-IDF 0.302, graphrag+LSA 0.298 (indistinguishable); **hard multi-hop** — 0.310 both ways. All 95% CIs overlap heavily, so strictly nothing is *significantly* better, but the point estimates are unambiguous: LSA never wins and regresses the one real lift. **Mechanism (verified):** on *easy* questions the query already uses the target provision's surface vocabulary, so TF-IDF gives a sharp, correct top seed; LSA's synonymy-smoothing *blurs* that sharp signal, dropping the right provision's seed rank below topically-related-but-wrong neighbours, which graph expansion then propagates from — semantic recall is a liability exactly where lexical precision was the asset. **Abstention re-checked with LSA seeds (still infeasible):** negative-control best-seed cosines (0.458–0.636) remain fully interleaved with answerable (min 0.441, median 0.554, max 0.798); 24/36 answerable sit at/below the worst control (TF-IDF: 28/36) — no clean threshold exists either way, FP/hallucination stay 1.000. **Takeaway:** classical LSA is *not* the missing semantic layer; a *neural* dense embedder (Qwen3-Embedding / voyage-law-2) trained on real synonymy is the genuine test, and it belongs behind the same ABC + an optional-dep gate — but the honest evidence so far is that neither structural expansion nor offline latent semantics beats sharp lexical retrieval on straightforward lookups, and the hard-item gap will likely need the *generation-side* verification layers (CRAG re-rank + NLI-grounded citation), not a better first-stage retriever alone.

> **CRAG + NLI citation-verification layer — built, reviewed, honest negative on the lexical proxy (2026-07-22).** `baselines/verify.py` implements the corrective-verification layer the two retrieval negatives pointed to: an `EntailmentScorer` ABC + a CRAG controller (`VerifiedBaseline`) that grades each emitted citation's (question, provision) support and then **keeps** (≥`keep`), **drops** weak, or **abstains** entirely (best < `abstain`) — CRAG's "Incorrect→fall back" action becomes *abstention* because our corpus is the closed authoritative Act, and the per-citation keep/drop is ALCE's citation-precision test. Two graders behind the ABC: `LexicalEntailmentScorer` (runnable-now, no deps: idf-weighted *coverage* of the claim's content terms by the provision — honestly labelled a lexical proxy, **not** neural NLI) and `NLIEntailmentScorer` (the real thing: `cross-encoder/nli-deberta-v3-large`, `P(entailment)=softmax(logits)[1]`, entailment index **resolved from the model's own label map** — verified `id2label={0:contradiction,1:entailment,2:neutral}` from its `config.json` — gated behind the `verify` extra, model-injectable for offline tests, clean `RuntimeError` if torch/model absent). CLI: `--verify {none,lexical,nli}` + `--verify-keep/-abstain/--nli-model`. **30 new unit tests (559 total pass); independently code-reviewed by a skeptical subagent** — no CRITICALs; fixed two real WARNINGs it found (a `not_entailment` label would hijack the entailment index via naive substring match; a double-softmax hazard if an injected model returns probabilities — now an explicit `apply_softmax` flag) plus a clean-error guard. Provenance verified against primary sources: CRAG = arXiv:2401.15884 (Yan/Gu/Zhu/Ling 2024; evaluator is a *separate* fine-tuned T5-large); ALCE = arXiv:2305.14627 (Gao et al., EMNLP 2023; TRUE T5-11B NLI, "citation irrelevant if it alone does not entail"). **Empirical result with the lexical proxy = a third verified NEGATIVE on abstention, and the sharpest one.** No-op sanity holds (`keep=abstain=0` reproduces base retrieval exactly). Max lexical-coverage support over the TF-IDF top-5 does **not** separate the 6 hard negative controls from answerable — it is *worse* than cosine/LSA: the single highest-coverage item in the entire hard set (**0.543**) is a *negative control*, above the best answerable item (**0.468**), so **36/36** answerable fall at/below the worst control. The abstain-threshold sweep confirms the mechanism: FP rate falls (1.000→0.500 at τ=0.30) only *in lockstep* with soft-F1 (0.291→0.223) and wrongful answerable-abstentions (0→12/36); on easy (no controls) abstention is pure loss (0.280→0.200). **Mechanism / thesis payoff:** negative controls are lexically on-topic *by construction* (on-domain vocabulary; the Act simply doesn't answer them), so every word-overlap signal — TF-IDF cosine, LSA cosine, and now idf coverage — reads them as relevant. Telling "the Act *mentions* these words" from "the Act *answers* this question" is an entailment / world-knowledge problem, not a lexical one. Three lexical/latent signals now provably fail to dent the FP=halluc=1.000 floor → it needs genuine neural NLI (the built-but-sandbox-unrunnable gated path: no torch/model/network, same honesty gate as the frontier LLM) or the frontier LLM's own judgement. **The corrective machinery is built, correct, and ready: drop a real `NLIEntailmentScorer` behind the same ABC and re-run — no plumbing changes.**

> **BM25F lever + API-route neural slots + Phase-4 citation guard + structural-abstention — built, integrated, three honest offline experiments (2026-07-23).** Landed the runnable-offline levers and the *API-route* neural slots the prior negatives pointed to, all behind the existing `Retriever`/`Baseline`/`EntailmentScorer` ABCs. **New modules (695 tests pass, was 661):** `bm25.py` (`Bm25Retriever`, pure-Python Okapi **BM25F**, body+heading fields, article-number boost); `dense.py` (`DenseRetriever` + `Embedder` Protocol — the *real* neural dense slot around local torch: embeds the corpus via an **injected** API client, pure-Python cosine, **zero import-time deps**); `llm_entail.py` (`LLMEntailmentScorer` — LLM-as-NLI judge implementing the same `EntailmentScorer` ABC as the torch cross-encoder); `generate.py` (Phase-4 `CitationGuard` + `CitedGenerationBaseline`, cite-as-you-generate constrained to the retrieved candidate set); `structural_abstain.py` (`StructuralAbstentionBaseline`, deterministic graph-cohesion gate). CLI gains `--baseline {bm25,dense,cited-gen}`, `--verify llm`, `--structural-abstain <min_cohesion>`; the three API-route paths (dense/cited-gen/verify-llm) **fail clean** in-sandbox (no torch/key/network) with the frontier-LLM honesty gate. **Fixed a real tokenizer bug the field-boost silently depended on:** the shared `tokenize()` drops tokens ≤2 chars, discarding article numbers **1–99** (most of the Act's 113 articles) from the heading field and queries; `bm25._bm25_tokenize` preserves all-digit runs of any length.
>
> **Experiment A — BM25F vs TF-IDF (a real lift, but fully attributed against itself).** @k=5, soft-F1: **easy 0.280 → 0.345** (exact 0.242 → 0.271), **hard 0.291 → 0.331** (exact 0.225 → 0.231). A **heading-weight ablation disproves the naive "field boost helps" reading**: on *easy* the boost adds only **+0.004** (0.341 body-only → 0.345) — BM25's saturation/length-norm does all the work, since easy questions rarely name articles; on *hard* body-only BM25 is **0.282, actually *below* TF-IDF's 0.291**, and the article-number boost is the **entire** margin of victory (**+0.048** → 0.331). The tokenizer fix is **load-bearing**, proven directly: hard BM25 heading=2.0 with the *old* tokenizer = **0.287** (inert, ≈body-only, still below TF-IDF), with the fix = **0.331**; 27/42 hard questions name a 1–2-digit article number. FP = hallucination = **1.000, unchanged** — BM25F is a better *retriever*, never a gate.
>
> **Experiment B — deterministic structural abstention = a fourth verified NEGATIVE, and it points the wrong way.** Hypothesis: an answerable question's top seeds cluster structurally (shared article-root or `CROSS_REFERENCES_INTERNAL`) while out-of-scope controls scatter. **Refuted — the separation is *inverted*:** on the hard split, negative-control cohesion **exceeds** answerable (tfidf seeds 0.400 vs 0.350; bm25 seeds 0.600 vs 0.483). The threshold sweep confirms no operating point exists: at bm25 τ=0.5, FP falls 1.000→0.667 only by abstaining on **16/36** answerable (soft-F1 0.331→0.178); reaching FP 0.333 keeps just **5/36**. **Mechanism:** the controls are lexically on-topic *by construction*, so their seeds are drawn from tightly-related provisions and cluster at least as tightly as real questions — the same "*mentions* vs *answers*" entailment gap that sank TF-IDF cosine, LSA cosine, and idf-coverage, now confirmed structurally too.
>
> **Experiment C — Phase-4 citation guard: the structural guarantee is real, but orthogonal to the benchmark's hallucination metric (stated honestly, not oversold).** `CitationGuard.filter` deterministically strips **100 %** (42/42) of fabricated non-node ids, unparseable junk, and off-candidate real nodes, keeping only real-node-∩-candidate citations — a hard guarantee that *fabricated / off-candidate* citations are impossible. **But that is a different guarantee than the scorer's off-lineage `hallucination_rate`:** **71.7 %** of top-10 BM25 candidates are **off-gold-lineage yet real and retrieved** — a model citing one of those passes the guard freely and still scores as an off-lineage hallucination. The guard closes the *fabrication* channel, not the *wrong-but-real* channel; the latter needs the retriever to stop surfacing off-lineage provisions, or NLI to reject them. **Takeaway across A–C:** a sharper lexical retriever (BM25F, article-aware) is the one genuine runnable-offline win and it is modest; every abstention/hallucination lever that avoids neural entailment (structural expansion, LSA, idf-coverage, and now graph cohesion) fails the *same* way, because the benchmark's negatives are adversarially on-topic. The built-but-sandbox-gated neural slots (`DenseRetriever`, `LLMEntailmentScorer`, `CitedGenerationBaseline`) are now wired behind the ABCs and ready to run the moment an embedder / API key / torch is available — no plumbing changes.

> **Formex-via-Cellar authoritative cross-check — DONE and verified against the live source (2026-07-23).** Ran `euaiact-cellar` against the live EU Publications Office (Cellar; `publications.europa.eu`). SPARQL discovery resolved CELEX 32024R1689 → the English fmx4 manifestation `dc8116a1-…0006.02` (**identical to the hardcoded fallback**, so the fallback is now confirmed rather than merely assumed), then fetched and parsed the real **171 KB Formex ZIP** (16 entries). **Provenance skeptically verified, not trusted:** an independent raw-XML re-parse (bypassing the module's own code) confirms **113 `ARTICLE` identifiers (1–113, gap-free)** and **180 `CONSID` recitals (1–180, gap-free)** genuinely extracted from the enacting-terms body `L_202401689EN.000101.fmx.xml` — *not* a `range()` artifact — and the persisted `data/authoritative_registry.json` is **byte-identical to a fresh fetch**, proving it was a real fetch all along, not hand-synthesized. This closes the long-standing "authoritative cross-check still open" caveat for the article/recital/annex layer. **Fixed a real honesty gap while here:** annexes had been **hardcoded** (`_VALID_ANNEXES`) behind a comment claiming annex parsing is "unreliable" — falsified. The ZIP carries each annex as its own `*.NNNN01.fmx.xml` entry (13 of them, distinct from the `.doc`/`.toc` metadata), each opening with `ANNEX <roman>`; all 13 resolve cleanly and uniquely to **I–XIII**. Replaced the hardcode with an authoritative `_parse_annexes` (the constant survives only as a fallback for an unexpected ZIP layout), so **all three dimensions are now genuinely parsed**; output is unchanged (I–XIII) so the registry stays byte-stable. +6 offline annex tests, live smoke test strengthened to assert the full ordered list; **701 tests pass**. **Honest limit (not oversold):** the registry validates only top-level article/recital/annex *numbers*, and it merely **confirms** the builder's hardcoded fallbacks were already correct — `graph/builder._plausible_eid` behaves identically with or without the fetch (registry articles == `range(1,114)`). Its value is *provenance/confidence*, not new validation power; a true non-existent-*sub-provision* hallucination check (is `Art. 6(7)(z)` real?) still needs a full provision-id registry that top-level Formex parsing does not provide.

**Phase 3 — Hybrid retrieval (week 4–6).** Index chunks in Qdrant (dense Qwen3 + sparse SPLADE/BM25F). Wire Neo4j `VectorCypherRetriever` for graph expansion. RRF fusion + reranker. Deliverable: retriever returning top-N provisions with IDs + graph-expanded context.

**Phase 4 — Generation & citation (week 6–8).** Cite-as-you-generate prompt; multi-agent Researcher/Auditor/Adjudicator; post-hoc NLI verification; optional RQ-RAG + CRAG loop. Deliverable: answers with verified `Art. X(Y)(z)` citations.

**Phase 5 — Eval & iterate (week 8–10).** Build 200–500-Q gold set; run metrics (§8) vs frontier-LLM long-context + naive-RAG baselines. Iterate: if hybrid loses in-domain, fine-tune BGE-M3 on labelled article-relevance pairs (highest-leverage per "Know When to Fuse"). Deliverable: benchmark report with CIs.

---

## 12. Key repos & code-function cheat-sheet

- **microsoft/graphrag** — `api.build_index`, `api.local_search`, `api.global_search`; `--method drift` (LazyGraphRAG).
- **HKUDS/LightRAG** — `rag.ainsert(docs)`, `rag.aquery(q, QueryParam(mode="hybrid"))`.
- **OSU-NLP-Group/HippoRAG** — `hipporag.index(docs=...)`, `hipporag.retrieve(queries, num_to_retrieve=k)`, `hipporag.rag_qa(...)`.
- **OpenSPG/KAG** — schema config → `IndexManager` extractors (`KnowledgeUnit`/`Outline`/`Chunk`) → KAG-Solver Q&A endpoint.
- **parthsarthi03/raptor** — `RetrievalAugmentation()`, `.add_documents(docs)`, `.answer_question(q, top_k)`.
- **BUPT-GAMMA/PathRAG** — `pathrag.query(q, mode="path")`.
- **neo4j/neo4j-graphrag-python** — `SimpleKGPipeline`, `VectorCypherRetriever`, `HybridCypherRetriever`, `Text2CypherRetriever`, `GraphRAG`.
- **run-llama/llama_index** — `PropertyGraphIndex`, `SchemaLLMPathExtractor`, `VectorContextRetriever`, `GraphRAGQueryEngine` (`build_communities`, `custom_query`).
- **FlagEmbedding (BGE-M3)** — `BGEM3FlagModel.encode(..., return_colbert_vecs=True)`.
- **stanford-futuredata/ColBERT** — `Indexer`, `Searcher`.
- **urchade/GLiNER** — `GLiNER.from_pretrained(...).predict_entities(text, labels)`.
- **SapienzaNLP/relik** — `Relik.from_pretrained(...)`, `RelikReaderForTripletExtraction`.
- **princeton-nlp/ALCE** — citation recall/precision eval scripts.
- **facebookresearch/SelfCite**, **explodinggradients/ragas**, **stanford-futuredata/ARES**.

---

## 13. Curated papers

**Foundational (high confidence):**
- GraphRAG — arXiv:2404.16130 · LightRAG — arXiv:2410.05779 · HippoRAG — arXiv:2405.14831 · HippoRAG 2 — arXiv:2502.14802 · KAG — arXiv:2409.13731 · RAPTOR — arXiv:2401.18059 · PathRAG — arXiv:2502.14902 · GraphReader — arXiv:2406.14550
- Self-RAG — arXiv:2310.11511 · CRAG — arXiv:2401.15884 · RQ-RAG — arXiv:2404.00610
- ALCE — arXiv:2305.14627 · LongCite — arXiv:2409.02897 · SelfCite — arXiv:2502.09604 · AttributionBench (ACL 2024)
- ARES — arXiv:2311.09476 · Know When to Fuse — arXiv:2409.01357 · ColPali — arXiv:2407.01449 · MultiLegalPile/LEXTREME — arXiv:2306.02069 · ReLiK — arXiv:2408.00103
- LegalBench — arXiv:2308.11462 · LexGLUE — arXiv:2110.00976 · CUAD — arXiv:2103.06268 · CaseHOLD — arXiv:2104.08671 · MAUD — arXiv:2301.00876 · SaulLM — arXiv:2403.03883, 2407.19584
- Legal KR standards: Akoma Ntoso (OASIS LegalDocML v1.0), ELI ontology (data.europa.eu/eli/ontology), LKIF-Core (CEUR-WS Vol-321), LegalRuleML Core v1.0 (OASIS)

**Verified 2026-07-22 — confirmed against primary sources (INTEGRATE):**
- LegalGraphRAG — arXiv:2605.28120 (repo `XMUDeepLIT/LegalGraphRAG`, ACL 2026) — multi-agent Researcher/Auditor/Adjudicator; closest prior art.
- SAT-Graph / Ontology-Driven Graph RAG for Legal Norms — arXiv:2505.00039 (JURIX 2025) — deterministic, temporally-versioned legal KG.
- GraphRAG-Bench "When to use Graphs in RAG" — arXiv:2506.05690 — framework-selection evidence.
- PathRAG — arXiv:2502.14902 (full title "…Retrieval Augmented Generation with Relational Paths").
- "Let's have a Chat with the EU AI Act" — arXiv:2505.11946 — the one direct EU-AI-Act RAG baseline (graph vs naive).
- EU AI Act TAIR ontology — arXiv:2408.11925 — reusable EU-AI-Act schema.
- Know When to Fuse — arXiv:2409.01357 (repo `maastrichtlawtech/fusion`) — non-English legal hybrid-fusion evidence.
- LexPath — arXiv:2605.30205 — multi-path legal *article* retrieval.
- Citation Grounding via Legal Citation Graphs — arXiv:2606.00898 — detects/reduces legal-citation hallucination via a citation graph (directly attacks the core risk).

**Verified — OPTIONAL / reference-only:**
- E²GraphRAG — arXiv:2505.24226 (indexing-speed baseline) · WildGraphBench — arXiv:2602.02053 (summarization-hurt warning) · "Do We Still Need GraphRAG?" — arXiv:2604.09666 · LRMoo legal KG — arXiv:2506.07853, 2508.00827 (Brazil case studies) · LexRAG — arXiv:2502.20640 (Chinese multi-turn) · GLiNER-Relex — arXiv:2605.10108 · "Beyond Probabilistic Similarity" — arXiv:2606.09724 (position paper) · Jina Embeddings v5 — arXiv:2602.15547.

**Verified but EU-AI-Act specificity was OVERSTATED (use for methodology only):**
- "Navigating Global AI Regulation: A Multi-Jurisdictional RAG System" — arXiv:2604.25448 (242 docs / 68 jurisdictions; the AI Act is just one) · "KG Representations for LLM-Based Policy Compliance Reasoning" — arXiv:2604.27713 (generic AI-risk policies).

**`[unverified]` — could NOT confirm; do not rely on:**
- "Noxtua Voyage Embed" (claimed European/German-law fine-tune of voyage-law-2) — no primary source found on independent search. Treat as non-existent until the vendor publishes docs; use `voyage-law-2` (confirmed) instead.

---

## 14. Risks & open decisions

1. **Dataset & source provenance (now checked).** `jeroenherczeg/eu-ai-act` and all cited GraphRAG/legal papers were confirmed on 2026-07-22; the only unconfirmable claim was "Noxtua Voyage Embed" (excluded). Two papers (arXiv:2604.25448, 2604.27713) are real but *not* EU-AI-Act-specific — use them for method, not content. Keep Formex-via-Cellar as the authoritative text cross-check regardless.
2. **Multilingual scope.** If you must serve all 24 languages, favour Qwen3-Embedding/BGE-M3 over English-centric voyage-law-2; align citations across language expressions via the shared `eId`.
3. **Temporal drift.** The Act phases in through 2027 and will accrue implementing/delegated acts — bake LRMoo Work/Expression versioning + `appliesFrom` date nodes in from Phase 2, not later.
4. **Kuzu — avoid.** Confirmed: Apple's acquisition agreement was 2025-10-09, the GitHub repo was archived (read-only) 2025-10-10 (publicly disclosed Feb 2026 via EU DMA filing). Use Neo4j, not Kuzu, for a new build.
5. **Fine-tuning payoff.** "Know When to Fuse" implies a fine-tuned single retriever may beat your hybrid RRF in-domain — budget a small labelled `(query, article)` set for Phase 5.
6. **Citation NLI cost.** Post-hoc NLI over every (claim, citation) pair adds latency; cache by `provision_id` pair.
