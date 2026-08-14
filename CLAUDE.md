# CLAUDE.md — Regenold EU AI Act RAG (re-evaluation repo)

Load-bearing context for an LLM coding assistant. Read top-to-bottom before
making changes. Every number here was re-measured in R326 (2026-08-10) against **this**
repo; the per-round engineering log lives in
**[`docs/ROUNDS.md`](docs/ROUNDS.md)** — search it, don't read it.

## ⚠ Which repo you are in

There are **two** sibling repos of the same FastAPI service. Getting this wrong
wastes hours.

| repo | role |
| --- | --- |
| `antifragileai-regenold-evaluation` (**this one**) | the **re-evaluation surface**: the graded 2026-07-07 code lineage with bugfixes applied. **Deploys to its own Railway service** — see below. |
| `regenold-eu-ai-act-rag` (`D:/Claude Projects/regenold-eu-ai-act-rag`) | **deploys to production.** Runs its own rounds. |

⚠ **CORRECTED 2026-08-13.** This table used to say this repo "Deploys nowhere",
and the bullet below used to say "nothing merged here is live". **Both were
wrong**, and the file contradicted itself in three other places while saying so:
`railway.toml` + `Procfile` are committed here, `R328.1` was a *Railway boot
fix* landed here, and `railway.toml`'s own R306 note records probing **"the
deployed endpoint"** live on 2026-08-03. Merging to `main` here reaches a real
service:

⚠ **One leg of that argument was retracted 2026-08-14.** This paragraph used to
also cite "the provider table below says the Bedrock path *is what Railway
runs*". That claim was never verified and has been removed from the table — see
the provider section. The conclusion (**a merge here ships**) is unaffected; it
rests on the three remaining items. But *which provider* the deployed service
runs is a separate, still-open question, and the two must not be conflated
again.

```
project      e19dc6ef-b463-4a54-9662-4a5085ae00c9
service      0086ff18-f642-46c8-8127-57c913ca1c53
environment  2f6298dd-881c-4848-81eb-5017a8a64c32
```

Treat a merge to `main` in this repo as **shipping**, not as a bench artefact.
That is exactly the reason `railway.toml [deploy.envs]` being inert matters so
much (see the gotchas): config here must be a CODE default or it never arrives.

* The July-7 machinery exists **only here** —
  `evals/regenold/_official_batch_20260707.json` (110 questions),
  `evaluator_batch_july7.py`, `run_official_batch.py`, `july7_difficulty.py`
  and their tests. **The RAG repo deleted all of it.** That is the concrete
  reason the repos are separate.
* **A `git merge parent/main` silently DELETES 29 files**, including every one
  of those. They existed at the merge base `c0799df` and the RAG repo deleted
  them afterwards, so the merge is a clean delete — no conflict, no marker, no
  warning. Verified by materialising the merge tree. Sync by **cherry-pick**.
* **Round numbers collide.** Both repos have an "R318"/"R319" and they are
  different work. Prefix a shared reference with the repo name.
* The RAG repo runs the **production** deployment; this repo runs its **own**
  Railway service (IDs above). So the two deploy independently — a change here
  is live on this service and is NOT live on production until cherry-picked,
  and vice versa. ⚠ The older claim that "nothing merged here is live" was
  wrong; do not rely on it when judging blast radius.

## What this repo is

A standalone EU AI Act grounded Q&A surface, extracted from the parent
`legit-ai` (CodexAI) codebase as a transparency bundle for the Regenold
competition. The wire contract is a single
`POST /api/v1/regenold/eu-ai-act/ask` that accepts an OpenAI-style messages
array and returns `{answer, references, reasoning}`.

Scored on six axes: correctness, references-vs-gold, conciseness-vs-gold, tone,
latency, multi-turn coherence.

## Architecture

```
POST /api/v1/regenold/eu-ai-act/ask
        │
        ▼
app/routes/regenold.py
   ├── _build_question_from_history       — flatten recent turns
   ├── classify_conversation              — scope gate (refusal or in-scope)
   │      └── app/integrations/regenold/scope.py
   ├── ask_compliance_question            — engine entry
   │      └── app/engines/_graph_rag_impl.py  ← imported as `app.engines.graph_rag`
   │           (`graph_rag` is a PACKAGE proxy; there is no graph_rag.py file)
   │             ├── _deterministic_parse — keyword→entities + BM25 fallback
   │             │      └── app/engines/vector_recall.py  ← additive vector recall (R326)
   │             ├── _retrieve_from_kb    — KB + ontology + xrefs
   │             ├── _deterministic_answer — verdict / role×risk / obligations
   │             └── _two_stage_generate  — Stage-2 LLM polish (live only)
   ├── _surface_anchor_citations          — keyword-derived anchors
   ├── _collapse_parent_refs              — smallest-cover citation pass (R325.1)
   ├── Component D                        — a SECOND prose→citation pass (see rule #11)
   ├── normalise_answer_for_regenold      — sentence + char caps
   └── RegenoldAskResponse
```

The Neo4j graph contributes **non-citable Stage-2 context** via
`app/engines/kg_context.py` — provision hierarchy, recital anchors, subpoint carve-outs,
and deontic classifications (Practice, OperatorRole, AnnexIIICategory, LifecyclePhase).
It is additive: never a ranker, never a wire citation (hard rule #10).

## Knowledge surface — measured 2026-08-09

| Module | Content |
| ------ | ------- |
| `app/data/article_existence.py` | **126** canonical refs = 113 articles + 13 annexes. The lint floor. |
| `app/data/kb.py` | `EC_CHECKER_OBLIGATION_MAP` — **131 entries** covering all 126 provisions (some articles carry multiple stubs). `KB_VERSION = 2024.1689.v18`. |
| `app/data/ontology.py` | `PRACTICE_REGISTRY` **×8**, `ANNEX_III_REGISTRY` **×8**, `PHASE_REGISTRY` **×4**. 0 dangling citations (normalise the sub-point tail before resolving — `Art. 5.1.a` keys as `Art. 5`). |
| `app/data/definitions.py` | **68** Art. 3 definitions. |
| `app/data/provision_text.py` | Verbatim resolver: article / paragraph / point / sub-point / annex item, section-aware. |
| `app/data/official_eu_ai_act.py` | Pinned EUR-Lex text, CELEX `32024R1689` (**pre-Omnibus**), 180 recitals. |
| `app/data/kb_search.py` | BM25 index — **345 docs**. |
| `app/data/kb_xrefs.py` | Cross-reference graph: **149 core** edges, **249 full**. |
| `app/data/eu_ai_act_tree.py` | **1,412**-node document tree. |
| `app/engines/_assets/` | Embeddings index — `is_available()` True, **0** asset SHA mismatches vs the manifest. TurboQuant precomputed — enabled, staleness guard present and passing. |

⚠ Older round entries quote `~165` / `348` / `347` BM25 docs, `Practice ×9`,
`Phase ×6`, and a `1,426`-node tree. **All four are stale** — the table above is
measured.

⚠ `PHASE_REGISTRY` has **0** `superseded_by` entries and `ROLE_SMALL_MID_CAP`
**does not exist**. Both are CORRECT for the pre-Omnibus pin. Older notes
(R25/R70/R98) claim Omnibus additions there — **do not "fix" the code to match
them**.

## Persistence / graph / LLM surfaces

| Module | Content |
| ------ | ------- |
| `app/evidence/store.py` | `get_evidence_store()` singleton. In-memory (default) / Postgres / SQLite. Hash-chained tamper-evident audit. |
| `app/graph/client.py` | Neo4j client (lazy import; disabled without a driver / DSN). |
| `app/graph/embedded_graph.py` | In-process SQLite property graph — the no-external-service backend. |
| `app/graph/timeouts.py` | `resolve_graph_timeout_ms` — one budget + circuit breaker for every graph read. |
| `app/engines/kg_context.py` | The graph's contribution: provision hierarchy + recital anchors. Non-citable, request-memoised, **3 Cypher shapes**. |
| `scripts/seed_neo4j_kb.py` | The seeder. `SEED_VERSION` gates the boot auto-seed — see hard rule #12. |
| `scripts/check_legal_version_drift.py` | Build-time canary: 3 Cellar SPARQL queries diffed against the pinned CELEX. ~2 s, fail-LOUD, **0 importers under `app/`**. |
| `app/llm/intent_classifier.py` | Stage-0 intent narrowing (wrapper or Groq). |

## Hard rules — don't break these

1. **Reference format is strict.** Only `Article N(.subpoint)*` (Arabic) or
   `Annex X(.subpoint)*` (Roman, uppercase). Never `Art. 13`, `Annex 3`, or
   `Article III` on the wire.
   ⚠ The *validator* is laxer than this rule: `_ANNEX_OUTPUT_RE` /
   `_ARTICLE_OUTPUT_RE` in `models.py` accept any alphanumeric sub-token, so
   `Annex III.foo.bar` passes. Treat the rule as the contract, not the regex.
2. **Answer length is capped**, but the effective cap is env-dependent:
   `MAX_ANSWER_SENTENCES = 3` in code, `REGENOLD_MAX_ANSWER_SENTENCES`
   overrides it, and `REGENOLD_ANSWER_NO_CAP` (default ON) removes both the
   sentence and soft-char caps on the live Stage-2 path. The RAG repo measured
   the uncap costing **−1.1 to −2.2 pp Overall** on Answer-Conciseness — the
   ONE axis we lead. Any cap must be SENTENCE-only: the char cap deletes
   verdict-first leads.
3. **No new classification topics for the 3 PDF example questions**
   (technical-doc hardware / emotion-recognition prohibition / doctor-patient
   transcription). The rubric measures generalisation; topic-specific overfit
   is penalised.
4. **KB stubs ship faithful regulatory prose, never speculation.** A
   confidently-wrong summary loses more than a missing one.
5. **`ARTICLE_EXISTENCE` is the lint floor** — every emitted citation must
   resolve there. `tests/test_kb_consistency.py` enforces it.
   ⚠ It cannot catch a *wire-legal* fabrication: a foreign instrument's
   Article 5 collides with AI Act Article 5 and passes the lint. See rule #11.
6. **A/B (`ab_judge`) IS THE MERGE GATE — davidath is NOT.** See Validation
   policy. Never ship an answer / Stage-2 / prompt / reference / scope change
   on "davidath byte-identical" alone.
7. **`--qa-only` is NOT a gate for a reference change — use the FULL 476.**
   davidath QA gold is single-article (mean 1.00 refs/row) and structurally
   cannot show a chain-dropping defect; scenarios carry mean **9.88**. A top-5
   cap measured FREE on a 132-row probe and destroyed **421 gold** on scenarios.
8. **RECALL GUARD — a reference change must drop ZERO gold.** R142.1's
   positional clamp lost a live pairwise judge **11-0 (p=0.001)**. Measure
   `gold_dropped` FIRST; non-zero is a rejection, not a trade-off.
   "Head-level recall is invariant" is NOT sufficient — gold and the grounded
   judge both score at SUB-POINT grain.
9. **ABSENT IS NOT ZERO.** Pre-R302 judged runs emit `wrong_refs: []` even when
   the row's prose names the over-citation — **349 of 547 rows (63.8%)** lack
   the field. Filter to usable runs before computing any rate.
10. **The graph is ADDITIVE context only** — never a ranker, never a wire
    citation. Graph-primary retrieval was demoted because the blunt
    `obligations_for_risk_level` dump buried the operative article.
11. **There are TWO prose→citation paths, and both need the guard.**
    `_add_prose_named_refs` AND Component D (the second extraction pass in
    `regenold_eu_ai_act_ask`). Component D was unguarded until R325 and
    re-added whatever the guard dropped — which is why widening the guard's
    regex measured *byte-identical on the wire*. If you touch
    `_prose_mention_is_real_citation`, assert BOTH paths.
12. **⚠ NEVER let this repo write to the shared Aura instance.** Pin
    `NEO4J_AUTO_SEED=0`. See the Graph section — the boot hook re-seeds on any
    `SEED_VERSION` mismatch without checking which side is newer, and this
    repo's seeder is OLDER than the live graph.

## Validation policy — `ab_judge`, not davidath, is the merge gate

Ship on the live pairwise `evals.harness.ab_judge`. davidath is a **regression
guard only** — it runs `provider=cli` with no Stage-2 and token-overlap metrics
that measurably *diverge* from the live judge. "davidath byte-identical" means
**inert on the bench**, not "no regression" and never "a win".

Gate for any change that can move an answer, a reference, the tone, or a scope
decision:

1. **Live verification first** — probe the real failing case. A reference /
   Stage-2 / scope change MUST be seen working LIVE.
2. **`evals.harness.ab_judge`** — position-swapped pairwise, baseline-OFF vs
   branch-ON, per-axis win-rate + sign test. **This is the merge gate.**
   For a reference change prefer **`evals.harness.easyhard_ab`**: it scores ref
   conciseness as a count-ratio against gold, which `ab_judge` lacks — that gap
   is how R142.1 slipped through.
3. davidath + 276-runner + OOS probe — cheap regression guards only.

Env-gate every such change (default-ON in code) so `ab_judge` can A/B OFF↔ON,
and keep the off-switch for instant rollback.

## Current baseline — the single authoritative source

Measured at `c6db579` (2026-08-09), deterministic env
`OPENAI_API_BASE=http://127.0.0.1:1/v1 P2P_GRAPH_RAG_PROVIDER=cli REGENOLD_EXTERNAL_EMBEDDINGS=0`.

**Grade every run against THIS block, never against a number in `docs/ROUNDS.md`.**

| davidath | Ans Loose | Ans Strict | Ans Conc | Ref Loose | Ref Strict | Ref Conc | Tone |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **OVERALL (476)** | 0.1884 | **0.3545** | 0.6143 | **0.5971** | **0.4748** | 0.4319 | 1.0 |
| QA (137) | 0.1407 | 0.4072 | 0.1961 | 0.8394 | 0.5536 | 0.4390 | 1.0 |
| Scenarios (339) | 0.2076 | 0.3332 | 0.7833 | 0.4992 | 0.4429 | 0.4290 | 1.0 |

Multi-turn **20/20 coherent**.

Other gates: `evals.regenold.runner` **255/255**, RISK_F1 macro **1.00**, 28/28
categories · OOS probe (`--oos-suite all`, 51 rows) **49 pass, 0 scope leaks**
(2 known `adjacent_eu` soft fails) · full `pytest` **55 pre-existing failures**,
all the documented `provider=cli` Stage-2 env artifact.

⚠ **R327 — this block is measurable again.** An uncommitted pass had rebound the
canonical axis names to new formulas, so any run graded against this table was
comparing two different rulers. Canonical names are back on the historical
formulas; `--assert-baseline` also works again (per-row `metric_provenance` inside
`scores` had made it permanently red).

⚠ An older pin of **0.4079 / 0.5543** appears in the log — it is stale.
⚠ **Judge the full suite by the failure SET, never the count**, and diff it
against a baseline checked out **in place** (`git stash`), never in a
`git worktree` — a worktree carries no `.env`, and the denoiser /
topic-filter / safety-gate cluster changes behaviour on `GROQ_API_KEY`
(measured 63 vs 92 failures on the same commit).

## The graph — live, and read-only from here

Aura **`0644b854`**, seed `2026-08-08-r323-annex-sections`, kb `2024.1689.v18`,
**1758 nodes / 1979 edges** across 18 labels. Measured 2026-08-09.

```
Article 113   Annex 13    Paragraph 658   Point 421   SubPoint 37
Recital 180   Definition 68   Obligation 113   Practice 8
AnnexIIICategory 8   OperatorRole 5   LifecyclePhase 4   RiskLevel 4
```

7 VECTOR indexes, all ONLINE and fully populated (**1,490 embeddings**), plus a
`ft_provision_prose` FULLTEXT index. Dimensions **128** (TF-IDF → SVD), cosine.
The seeder writes them with `embeddings_index._embed_query`, the same function the
query path uses, so query and node vectors share one subspace — verified.

**R326 lit up 2 of the 7**; **R327 reads all 7**, each at a different layer:

| index | nodes | how it is read | can it reach the wire? |
| --- | --- | --- | --- |
| `v_article_embedding` | 113 | open-domain additive candidate recall — `app/engines/vector_recall.py`, `REGENOLD_GRAPH_VECTOR_RECALL` (OFF) | yes, gated |
| `v_annex_embedding` | 13 | same | yes, gated |
| `v_paragraph_embedding` | 658 | ANN then **constrained to already-cited provisions** — `app/engines/graph_semantic.py` | no |
| `v_point_embedding` | 421 | same | no |
| `v_subpoint_embedding` | 37 | same | no |
| `v_definition_embedding` | 68 | open-domain, non-citable definitional context | no |
| `v_recital_embedding` | 180 | open-domain, non-citable interpretive context | no |

⚠ **The embedding is a WEAK open-domain retriever and the access mode is the
whole point.** Measured on the live instance, scores cluster in 0.5–0.88 whether
the hit is right or wrong — there is no discriminative margin:

* *"Is social scoring by a public authority allowed?"* → `v_article_embedding`
  rank 1 = **Article 77** (0.73). The answer is Art. 5(1)(c).
* *"Our hospital wants to transcribe doctor-patient conversations"* → Article 19,
  then 21. Both wrong.
* *"Who counts as a deployer?"* → `v_definition_embedding` ranks `def_provider`
  (0.629) **above** `def_deployer` (0.615).

Which is the same result as the R325 lexical re-ranker (best AUC 0.641 vs
`rank`'s 0.703) and the three dense-rerank washes. So the sub-provision layers
are queried by ANN and then **filtered to units of provisions already cited** —
that converts a weak open-domain retrieval into a strong within-provision
selection (Art. 12 → 12(1) at 0.891; Art. 50 → 50(3)) and makes citation drift
structurally impossible, because every candidate already belongs to a cited
provision. Definitions and recitals stay open-domain but can never be a wire
citation, so their weak precision costs context budget, never a reference.

⚠ **`HAS_RECITAL_ANCHOR` has 5 edges in the ENTIRE graph** (article_5 → recitals
18/30/31/44, article_52 → recital 112). So `fetch_recital_anchors` is dead for
111 of 113 articles while 180 embedded recitals sat unread. That is why the
recital layer is semantic rather than structural.

⚠ **`CROSS_REFERENCES` (248 edges) is never read as CONTEXT.** Incoming edges are
real legal signal — `article_50 <- [Article 13, Article 26, Article 5, Article 96]`
— and the backlink direction is unexplored. It is measured-dead only as a
*citation* path (fuse slack, R295). Next candidate; needs its own gate.

**Article node `number` is a STRING.** `MATCH (a:Article {number: 3})` returns
nothing; `{number: '3'}` and `{id: 'article_3'}` work. `ORDER BY` on it sorts
lexicographically — Article 3 ordered 1, 10-19, 2, 20-29, 3 … and at a 24-unit
cap dropped definitions 3(4)-(8) (deployer / authrep / importer / distributor /
operator). Every ordering must cast: `toIntegerOrNull(u.number)`.

**⚠ The seed hazard (hard rule #12).** This repo ships
`SEED_VERSION = 2026-07-24-r291-fullseed`; the live graph is
`2026-08-08-r323-annex-sections`, seeded by the RAG repo. The boot hook
re-seeds on ANY mismatch — it does not check which is newer — so booting this
repo with auto-seed ON **downgrades production's graph**, losing the
section-aware annex items and the SubPoint layer. The failure is silent: the
seeder succeeds, `/healthz/graph` still reports ok, answers just get worse.
`.env.example` pins `NEO4J_AUTO_SEED=0`; keep it.

## Where we stand

* **Three separate scorecards. Never conflate them.** (a) The OFFICIAL regenold
  report — we beat 0 baselines, `Overall` is a **geometric mean** so the worst
  axis dominates, and **Answer-Conciseness is the only axis we lead** (zero
  headroom). (b) **davidath = regression guard**. (c) The **frontier
  head-to-head** = the "are we SOTA?" measure.
* **Frontier standing** (132 paired rows): we win Ref Loose and keyword recall;
  we lose **Ref Strict and Ref Conciseness — the same defect, over-citation**.
* **Over-citation is the whole remaining gap.** An oracle dropping every
  non-gold ref gains Ref Strict **+0.215** / Ref Conciseness **+0.229** at
  unchanged recall. Nothing has captured any of it.
* **The July-7 re-evaluation** (100 of 110 graded questions, grounded Sonnet-5
  judge): answer correctness 0.500 → **0.780** (**~0.86 corrected**), factual
  0.806 → **0.950**, citation faithfulness 0.764 → **0.900**, ref precision
  0.615 → **0.673**, recall 0.893. Refs/row **3.94 → 2.73 (−31%)**, answer
  length **868 → 1223 chars (+41%)**.
* **The judge cannot read the tail of long answers.** 8 of 22 answer failures
  are labelled "truncated" and **all 8 are false positives** — the content
  called missing is the answer's last sentence. Zero of 100 answers lack
  terminal punctuation, and fail rows median **1698** chars vs pass **1096**.
  Correctness is understated; any long-answer verdict from that judge is
  suspect. **Do not tune against the truncation cluster — it does not exist.**
* **Reference correctness is TAIL PADDING.** Wrong-rate by rank: 1 → **0.22**,
  2 → 0.45, 3 → **0.60**, 5 → 0.88. Retrieval is fine; the first ref is right
  78% of the time. Capping at 2 destroys **33 correct refs to remove 49 wrong**
  — the R142.1 trade. **All the headroom is in identifying WHICH tail reference
  is wrong.** Quote **F1 0.768** alongside the 0.31 conjunctive pass rate.

## Do not re-propose — measured and dead

**Over-citation trimming (five families):**
* Article-**identity blocklists** — the same head is gold on one question and
  wrong on another (`Article 6` wrong 21 / gold 22; here, Annex III 5 wrong /
  2 missing).
* **Positional / top-N clamps** — top-2 drops 23 gold. R142.1 lost a live
  pairwise **11-0, p=0.001**.
* **Prose-driven pruning** — a structural no-op: **86%** of wrong refs ARE
  described in the prose.
* **Ask-type × role exclusivity** — classifier-fragile; two competent
  implementations disagreed on 30% of rows.
* **Chapter-III tier exclusivity** — clean on five gates, then dropped **67
  gold across 40 scenarios** on the full 476.
* **A cheap LEXICAL re-ranker (R325).** "Work the ranker, not the trimmer" was
  the standing lesson; measured, it is also closed. AUC for separating CORRECT
  from WRONG refs over the 273 predicted refs in the 100 graded rows:

  | signal | AUC | | signal | AUC |
  | --- | --- | --- | --- | --- |
  | **rank** (engine's own order) | **0.703** | | described_chars | 0.613 |
  | lex_ans (IDF coverage) | 0.641 | | q_kb_overlap | 0.608 |
  | n_mentions | 0.625 | | is_subpoint | 0.554 |

  **No combination beats `rank` alone** (all-features 0.696, rank+lex+desc
  0.701) — the signals are correlated, not complementary. Same instrument that
  killed neural NLI. Rank-1 is already **86%** right.
* Lesson, updated: **selection is close to exhausted.** The engine already
  orders well and nothing cheap re-orders it better, so the remaining
  over-citation gap must be attacked at **GENERATION** — retrieval and the
  Stage-2 grounding block — not by another trimmer or ranker.
* The ONE structural exception that survived: **parent-collapse** (drop a bare
  head when its own sub-point is cited) — 9 wrong removed : 1 correct lost,
  F1 +0.0177, 5 rows flip fail→pass, 0 flip pass→fail. Shipped
  `REGENOLD_PARENT_COLLAPSE`, **default OFF**, because that 1 loss means it
  does not satisfy hard rule #8 as written. Note it is a **provable no-op on
  davidath** (`article_heads()` projection), so only `easyhard_ab` or the
  grounded judge can gate it.

**Retrieval / graph:**
* **Graph-primary retrieval** — the blunt risk-tier dump buries the operative
  article.
* **`REGENOLD_GRAPH_FUSE_SLACK > 0`** — slack=2 destroyed gold.
* **Prose-mined recital→article edges** — only ~4 of 32 candidates are genuine
  AI Act refs; the rest point at GDPR/MDR/TFEU. Hallucination.
* **RRF fusion / dense rerank / paragraph extraction** — measured washes three
  times. davidath is BM25-saturated.
* **Neural NLI citation verification** — ROC-AUC **0.585** vs the free lexical
  scorer's **0.749**, and 235× slower. Do not add torch.
* **A live SPARQL retrieval path.** Cellar's RDF is document-level only: 55
  predicates, no article resources, no Akoma Ntoso manifestation, ELI is a
  literal not a node. The one worthwhile slice already ships as the build-time
  drift canary. (Do *not* repeat the error of probing only OUTGOING edges —
  `act_consolidated_consolidates_resource_legal` is incoming.)
* **External vector DBs / GPU rerankers / LangChain** — Railway is CPU-only and
  torch-free by design.

**Model / latency:**
* **Fast mode** and **extended-thinking budget** are NOT latency levers — both
  measured washes. ~half of live latency is a fixed CLI-wrapper floor (a
  5-token request costs 12-17 s).
* **Opus-for-all Stage-2** — a wash; trades a 1-row correctness lean for a lean
  against conciseness and tone.
* **`REGENOLD_STAGE2_SIMPLE_SKIP`** — refs 0.75 → 0.47.

**Method:**
* **R277's "minimal composer" result is a NULL EXPERIMENT** — both arms were
  identical at the model, because the swap was inside the system prompt the
  wrapper drops. Do not cite it as evidence that prompt volume is harmless.
* **The Cappelli et al. (2026) paper's 7 optimisations** — none buildable; the
  authors built no retrieval system and their failure mode is UNDER-citation,
  the inverse of ours.

## Gotchas that have each cost a session

* **The Stage-2 SYSTEM prompt is dropped by the Claude Max wrapper — 0% of
  requests see it.** Prompt fixes MUST go in the Stage-2 **user** message.
  Proven with a French-instruction probe: system slot ignored, user slot obeyed.
* **`railway.toml [deploy.envs]` has NEVER applied** — Railway's `[deploy]`
  schema has no `envs` key. Bake config as **code defaults**.
* **Scripts don't load `.env`.** `scripts/seed_neo4j_kb.py` and
  `scripts/fetch_lawstronaut_provenance.py` are pure-stdlib — export the vars
  or they exit 1. The seeder prints its error at the TOP, so **never `tail` it**
  (and don't pipe a runner through `tail` either: `evals.regenold.runner` puts
  its summary on line 4).
* **`evals/harness/` does not load dotenv.** Export explicitly or it silently
  falls to the deterministic path — the inert-feature trap.
* **Do NOT copy the RAG repo's `.env` here.** It carries
  `P2P_GRAPH_RAG_API_KEY=sk-ant-…`, which enables the Anthropic Stage-2 path a
  test expects disabled. Build a scratch env instead, and override its
  `OPENAI_API_BASE` (it points at the Cloudflare tunnel, which needs CF Access
  headers) to the local wrapper.
* **A code fix to `provision_text` is not live until you re-seed AND bump
  `SEED_VERSION`** — otherwise the boot hook hits `skip-current`. But see hard
  rule #12 before re-seeding anything from here.
* **`load_dotenv()` resolves relative to the calling script** — a probe outside
  the repo silently measures a DISABLED graph. Assert
  `get_graph_client().enabled` before drawing conclusions.
* **Check the key form before reporting a missing surface.** Annex node ids are
  `annex_IV` (uppercase Roman); `ARTICLE_EXISTENCE` keys articles as **`Art. N`**,
  not `Article N`; ontology citations carry a sub-point tail (`Art. 5.1.a`) that
  must be normalised before resolving. Each has faked an "empty surface" alarm.
* **Console `?` on Windows is cp1252 rendering, never data.** Verify by codepoint.
* **`/healthz/llm` lies** — verify the wrapper with a real POST.
* **Never run two wrapper-bound jobs concurrently.**
* **The instrument trap.** Repeatedly, an authoritative-looking instrument was
  structurally blind to the decision: davidath is BM25-saturated, so a gate
  reads byte-identical *because* it is a no-op there; a deterministic reference
  measurement is not a valid proxy once Stage-2 makes refs a function of the
  answer; a judge that renders `answer[:1400]` cannot see a 1413-char answer.
  **Before trusting a measurement, ask: can this instrument physically observe
  the thing I am deciding?**
* **Small-n live A/Bs cannot resolve reference axes.** Two runs with an
  IDENTICAL baseline arm changed 20/40 rows' refs and sign-flipped all three
  reference axes. Use full n with repeats, or a deterministic offline sim.
* **CHECK THE BRANCH ARM'S LATENCY — it is the cheapest inert-A/B detector.**
  R327 ran a 50-row paired live A/B of `REGENOLD_GRAPH_SEMANTIC_LAYERS` and got
  byte-identical answers AND byte-identical reference lists on all 50 rows. That
  reads as "safe". It was inert: arm B averaged **1,096 ms** against arm A's
  **16,642 ms**, i.e. every row was an `_ENGINE_CACHE` hit and Stage-2 never
  re-ran. A branch arm an order of magnitude faster than baseline did not run the
  engine. **Any engine-level flag missing from `_engine_cache_key` makes an
  in-process A/B measure nothing** — R326's `REGENOLD_GRAPH_VECTOR_RECALL` had
  the same defect. Route-level post-processing flags must stay OUT of the key
  (that asymmetry is what makes the paired A/B possible); engine-level ones must
  be in it.
* **"Byte-identical" is also what INERT looks like.** A foreign-citation guard
  was widened, measured no wire change, and that was read as *safe* — it was
  also consistent with *not working*, because Component D was re-adding
  whatever the guard dropped. Before concluding a fix is safe-because-flat,
  prove it FIRES: assert the intended behaviour directly.
* **One concept, one definition.** The same guard had TWO regexes for "a
  numbered EU Regulation id" and only one was ever widened, so the other branch
  had never fired at all. When you widen a pattern, grep for its siblings.
* **A ceiling that falls back to a smaller limit is a switch, not a ceiling.**
  Cut AT the ceiling and mark it.
* **Budget the thing you just added.** A new context block competes with the
  existing one; if the old block is budgeted against the full ceiling and the
  tail-drop pops from the end, the new block is the first thing deleted — i.e.
  the feature silently removes itself.
* **A background job that does `git checkout` will collide with your edits.**
  Commit first, or don't edit while it runs.
* **R327 — the instrument trap, in its most dangerous form yet: the ruler was
  rewritten in the SAME change as the behaviour it grades.** An uncommitted pass
  redefined `ans_correctness_*` and `ref_correctness_strict` / `ref_conciseness`
  **in place**, under the canonical axis names, while also collapsing every
  reference budget to 5. Had it been graded, the bench would have "confirmed" the
  clamp using a scorer built to like it. Canonical axis names are now pinned to
  the historical formulas; new formulas live under `*_polarity_adj` /
  `*_exact_coord`. **If you change a formula, change its NAME.**
* **Gold shape decides which reference formula is valid.** davidath's
  `relevant_article` gold is HEAD-level, so scoring exact coordinates against it
  marks a MORE precise citation (`Article 5.1.f` vs gold `Article 5`) as 0.0.
  easyhard's `expected_refs` DO carry sub-point grain, so it uses the
  `*_exact_coord` variants. Same axis name, two datasets, two correct formulas.
* **The first graph query in a fresh process can blow the 750 ms budget.** Cold
  TLS + driver handshake to Aura measured a MISS on query 1 and 40-68 ms on every
  query after. So the first row of a batch silently loses its graph context.
  Warm the client before timing or grading anything.
* **`provision_exists` is head-level LAX.** `provision_exists("Article 3.999")`
  is **True**. It cannot be used to validate a leaf coordinate; only
  `get_provision_text` returning non-None can. (Measured: 0 of 60 real leaf
  coordinates in the July-7 gold lack verbatim text, so a "real coordinate with no
  text" fallback is dead code that only ever dresses a FABRICATED coordinate in
  its parent's words.)
* **`grep` silently stops printing when it decides the stream is binary.** The
  cp1252 curly quotes in provision text make `grep -v` emit
  `Binary file (standard input) matches` and drop every remaining line. It cost a
  wrong conclusion twice this round ("definitions never fire" — they always did).
  Write to a file and read it, or `grep -a`.
* **A non-blocking admission gate is a graph OFF switch under load.**
  `_KG_ADMISSION.acquire(blocking=False)` with 2 slots hard-dropped every
  concurrent read past the second. One request issues up to six kg_context reads
  and the harness runs at concurrency 3, so the graph vanished exactly when it was
  most in use — while every health probe stayed green.

## Env flags that matter

Defaults are the CODE default, re-measured 2026-08-09.

| Flag | Default | Effect |
| --- | --- | --- |
| `P2P_GRAPH_RAG_PROVIDER` | `auto` | `cli` (deterministic) / `anthropic` / `openai_wrapper` |
| `P2P_GRAPH_RAG_ENABLE_STAGE2` | **ON** | Stage-2 polish master gate |
| `REGENOLD_ANSWER_NO_CAP` | **ON** | removes sentence + char caps live (hard rule #2) |
| `REGENOLD_KG_CONTEXT` | **ON** | graph context into Stage-2 |
| `REGENOLD_KG_MAX_CHARS` | 16000 | total graph-context ceiling |
| `REGENOLD_KG_MAX_UNITS` | 24 (env ceiling 70) | units per provision |
| `REGENOLD_KG_UNIT_CHARS` | 900 | per-unit budget; `_UNIT_HARD_CEILING` 2600 for enumerations |
| `REGENOLD_GRAPH_BACKEND` | `neo4j` | `embedded` = in-process SQLite, no external service |
| `REGENOLD_GRAPH_TIMEOUT_MS` | **750** | one budget + breaker for every graph read |
| `REGENOLD_GROUNDING_TEXT` | ON | verbatim paragraphs of cited refs into Stage-2 |
| `REGENOLD_SUFFICIENT_CONTEXT` | ON | bounded multi-hop |
| `REGENOLD_REF_PARTITION` | **OFF** | it deleted gold references |
| `REGENOLD_COMPLETENESS_VERIFIER` | **OFF** | it appended inverted law |
| `REGENOLD_FINAL_REF_CLAMP` | **OFF** | R142.1 — lost the pairwise judge 11-0 |
| `REGENOLD_PARENT_COLLAPSE` | **OFF** | R325 — drop a head when its own sub-point is cited. F1 +0.018 on the graded batch but loses 1 gold, so it awaits `easyhard_ab` |
| `REGENOLD_GRAPH_VECTOR_RECALL` | **OFF** | R326 — additive Neo4j native vector recall (article + annex) + local SVD fallback |
| `REGENOLD_VECTOR_MIN_SIM` | 0.35 | R326 — similarity floor for vector recall hits |
| `REGENOLD_GRAPH_SEMANTIC_LAYERS` | **ON** | R327.1 — reads the other 5 vector indexes as non-citable Stage-2 context. **GATED ON**: constrained-only measured citation faithfulness 0.900→**0.960** at baseline reference precision (micro 0.611→0.614, wrong refs 51→49). Off-switch `=0` |
| `REGENOLD_SEMANTIC_GLOSS` | **OFF** | R327.1 — the OPEN-DOMAIN half (definitions + recitals). Running it too cost micro precision 0.614→0.583 for NO extra gain, so it is off. `=1` restores the both-halves arm |
| `REGENOLD_KG_SEMANTIC_MAX_CHARS` | 26000 | R327 — total KG ceiling used ONLY when the semantic layers contribute. See the budget note below |
| `REGENOLD_SEMANTIC_UNITS` / `_UNITS_PER_PROVISION` | 6 / 2 | R327 — focused sub-provision block size, and the per-provision cap |
| `REGENOLD_SEMANTIC_DEFINITIONS` / `_RECITALS` | 3 / 3 | R327 — per-layer quotas. They must be SEPARATE: recitals score ~0.70 vs definitions ~0.62, so a shared LIMIT returned **zero** definitions |
| `REGENOLD_KG_MAX_INFLIGHT` | 4 | R327 — graph worker slots. Was 2 with a NON-BLOCKING acquire, which hard-dropped every concurrent read past the second |
| `REGENOLD_MINIMAL_REF_BUDGET` | **OFF** | R327 — collapses every scenario budget to 5. This is the top-N clamp family; awaits `easyhard_ab` + `gold_dropped` |
| `REGENOLD_COMPONENT_D_CITABLE_ONLY` | **OFF** | R327 — Component D promotes only retrieval-grounded refs |
| `REGENOLD_CITABLE_BASE_GUARD` | ON | R327 — restricts prose-promotion to the retrieved citation universe (only ever REMOVES an ungrounded promotion) |
| `REGENOLD_SEMANTIC_COORDINATES` | **ON** | R329 P2 — the constrained sub-provision block renders the legal coordinate (`Article 12.2.a`) instead of the internal node label (`[paragraph para_12_1]`). LABEL only: the block stays non-citable, so hard rule #10 holds. Guards a real fabrication — `build_hierarchy_payload` synthesises a Paragraph `1` for single-block lettered provisions, so naive reconstruction emitted `Article 16.1.a`, which does not exist (3 of 658 nodes; those fall back head-level via `get_provision_text`, NOT the head-lax `provision_exists`). Off-switch `=0` |
| `REGENOLD_CITABLE_UNIVERSE_BLOCK` | **ON** | R329 P3a — emits an explicit `CITABLE PROVISIONS:` list and repoints the citation instruction at it. Fixes a scope statement that named a block also containing GDPR/MDR bridging, multi-hop synthesis, legal-AST output, three KG sections, verbatim text and recitals, each with its own "do NOT cite" clause. Sub-points of a listed provision stay permitted. Off-switch `=0` |
| `REGENOLD_REF_UNCERTAINTY` | **ON** | R329 P3b — one user-channel sentence on the UNCERTAINTY axis, which `USER_REF_MINIMALITY_CLAUSE` (ON since R298) does not state; it argues relevance. Pulls against system rule 10 ("Unmentioned citations are severely penalized") — read the reconcile drop rate in any arm that moves it. Off-switch `=0` |

⚠ **The three R329 flags were flipped to default-ON on 2026-08-13 by operator
decision and are UNGATED.** The reason they are code defaults rather than env
opt-ins is the standing `railway.toml [deploy.envs]` finding: an env-gated
default-OFF flag never reaches the deployment at all. Each keeps a `=0`
off-switch and remains a flag so `ab_judge` / `easyhard_ab` can still A/B it.
**Consequence: the "Current baseline" block above was measured with all three
OFF and no longer describes the default-configuration system.** Re-measure
before grading anything against it. This is the R327 shape (an ungated change
shipped ON) entered deliberately and with the risk recorded, not by accident.
| `GROUNDED_JUDGE_STRICT_GROUNDING` | **OFF** | R327 — ON makes answer-correctness unscorable on the July-7 batch (it has no gold at all) |
| `NEO4J_AUTO_SEED` | **OFF unless `1`** | R327 — now opt-IN, and even then only seeds a graph proven to have 0 nodes. Hard rule #12 |
| `BEDROCK_REGION` | **`eu-central-1`** | R328 — Bedrock source Region. Also reads `AWS_DEFAULT_REGION` / `AWS_REGION`. NOT `us-east-1`: an `eu.` profile is unresolvable there |
| `REGENOLD_BEDROCK_MODEL` | `eu.anthropic.claude-opus-4-8` | R328 — Stage-1 + Stage-2 main RAG tier. 403 on the current key; R328.2 degrades to `opus-4-6-v1` |
| `REGENOLD_BEDROCK_COMPLEX_MODEL` | `eu.anthropic.claude-opus-5` | R328 — the `complex_question` tier. Also 403; same chain |
| `REGENOLD_BEDROCK_JUDGE_MODEL` | `eu.anthropic.claude-sonnet-5` | R328 — judge. Precedence: this env > the CLI `--model` flag > the default. Also 403; degrades to `sonnet-4-6` |
| `REGENOLD_STAGE2_VERDICT_GUARD` | **ON** | Rejects a Stage-2 answer that stops mid-verdict, on BOTH the wrapper and (since 2026-08-13) the Bedrock path. `=0` disables. ⚠ Never measured on `ab_judge` — davidath cannot see it (Stage-2 only) |
| `REGENOLD_BEDROCK_MAX_TOKENS` | **4096** | R328.3 — the Stage-2 answer ceiling on Bedrock. NOT `settings.graph_rag.max_tokens` (1536), which is advisory on the wrapper and a HARD mid-word cut here. Worst measured enumerative answer used 3411 |
| `REGENOLD_BEDROCK_STAGE2_TIMEOUT_S` | **180** | R328.3 — per-call read budget for Stage-2. The 60 s default turned a bigger token ceiling into `ReadTimeoutError` (the worst case emits 3411 tokens in ~70 s) — the same truncation, one layer down |
| `REGENOLD_BEDROCK_JUDGE_MAX_TOKENS` | **1600** | R328 — NOT the wrapper's 400. Bedrock honours the system prompt (the wrapper drops it), so the judge reasons in prose before its JSON; at 400 it truncates and the axis returns `no_json` — a SILENTLY UNSCORED axis, not a visible failure |
| `REGENOLD_BEDROCK_WRAPPER_FALLBACK` | **ON** | R330 — cross-PROVIDER last resort ported from the RAG repo: when the WHOLE Bedrock entitlement chain is spent, serve from the Claude-Max wrapper instead of dropping Stage-2. Placed at the END of `complete_with_fallback`, not inside `BedrockProvider.complete` as upstream has it — upstream's placement can hop on the FIRST model's throttle while an invocable tier sits further down the chain. ⚠ **The two providers are not interchangeable: Bedrock honours the system prompt, the wrapper drops it 100%**, so a hop silently changes ~12.8K tokens of delivered instruction. It therefore returns `model="wrapper:<name>"`, which makes the existing `_bedrock_complete_for_graph_rag` provenance fire unchanged — `stage2_models` in the sidecar shows `wrapper:…`, never the pin. Alert on `served_by=wrapper:`. Off-switch `=0` |

Stage-2 models (`app/config.py`): parse `claude-sonnet-5`, Stage-2
`claude-opus-5`, complex `claude-opus-5`, complex thinking 4000, max_tokens
1536. ⚠ `_model_alias_enabled()` in `openai_wrapper_provider.py` can silently
rewrite an Opus model name on the way to the wire — check it before trusting a
model A/B, and note the trace reports the model actually sent.

## LLM provider story

`P2P_GRAPH_RAG_PROVIDER` selects one of four mutually exclusive paths:

| Value | Behaviour | Setup |
| --- | --- | --- |
| `cli` | Pure deterministic, no LLM, sub-10 ms. **This is what davidath runs.** | none |
| `anthropic` | Stage-1 + Stage-2 via Anthropic SDK (per-token billing) | `P2P_GRAPH_RAG_API_KEY=sk-ant-…` |
| `openai_wrapper` / `auto`* | Stage-1 + Stage-2 + Stage-0 intent via the Claude Code Max wrapper | wrapper on `127.0.0.1:8000` or the tunnel + `OPENAI_API_BASE` |
| `bedrock` | Stage-1 + Stage-2 + judge via AWS Bedrock **EU cross-region inference** (R328). | `AWS_BEARER_TOKEN_BEDROCK` (or `AWS_ACCESS_KEY_ID`/`_SECRET_ACCESS_KEY`) |

⚠ **CORRECTED 2026-08-14.** `* auto` (and unset, and empty) resolves to
**`openai_wrapper`**, NOT to "`anthropic` when a key is set, else `cli`" as this
table claimed for months. `resolve_provider` defaults `default_when_auto="openai_wrapper"`
(`app/llm/__init__.py:16,32`) and **every** call site passes that value explicitly
(`_graph_rag_impl.py:217`, `main.py:34,90,1025`). An AWS credential alone never
selects Bedrock: every dispatch site is an equality test on the literal string
`"bedrock"`, and `is_bedrock_provider_enabled()` is consulted only *inside* that
branch. Every sub-pipeline falls back to a deterministic equivalent on error, so
the route never 500s on a downed LLM.

⚠ **"Bedrock is what Railway runs" was an UNVERIFIED claim and has been removed
from the table.** Nothing in this repo establishes the deployed provider:

* the code default with no env var set is `openai_wrapper` (above);
* `railway.toml [deploy.envs]` **has never applied** (its own header says so),
  and the string `bedrock` appears nowhere in `railway.toml` — what that inert
  block actually assigns is `P2P_GRAPH_RAG_PROVIDER = "openai_wrapper"`;
* `.env` is gitignored, so the deployed container ships no dotenv;
* `Procfile` / `railpack.json` set only the uvicorn command.

So production is on Bedrock **only if** a Railway *service variable* was set from
the dashboard/CLI, which is not in the repo and cannot be verified from it.
`.kiro/steering/railway-redeploy.md` does not even record this service's public
domain — it sends you to the dashboard. **Treat the deployed provider as UNKNOWN
until someone runs `railway variables` against service
`0086ff18-f642-46c8-8127-57c913ca1c53`, or POSTs the live endpoint and reads the
`stage2_model=` note in the reasoning trace.** Any argument of the shape
"Bedrock honours the system prompt ⇒ production has the four-sentence cap" is
unsupported until then, because its middle link is this unverified claim.

### Bedrock — the EU cross-region path (R328)

Region and model geography are **ONE decision, not two**. An `eu.` inference
profile does not exist outside the EU geography's Regions, so calling one from
`us-east-1` fails with `ValidationException: The provided model identifier is
invalid` — which reads like a bad model name and is really a bad Region. The
code default is `eu-central-1` precisely because the default model is an `eu.`
profile; `_warn_on_geography_mismatch` logs loudly if the two disagree.

⚠ **Two ID SHAPES coexist and neither is guessable — read the catalog, never
extrapolate.** Sonnet 4.6 / Opus 4.7 onward carry a BARE id
(`eu.anthropic.claude-sonnet-5`); older ones keep the dated tail
(`eu.anthropic.claude-sonnet-4-5-20250929-v1:0`); Opus 4.6 is a third shape
again (`eu.anthropic.claude-opus-4-6-v1`). Verify with
`list_inference_profiles(typeEquals='SYSTEM_DEFINED')`.

⚠ **Listed-and-ACTIVE is NOT invocable, and `GetFoundationModelAvailability`
cannot tell you which is which.** Measured 2026-08-11: it returned
`AUTHORIZED / entitlement AVAILABLE / region AVAILABLE` for `claude-opus-4-8`
(which returned `AccessDeniedException` on every invoke) *and* for
`claude-opus-4-6-v1` (which invoked fine) — identical output, opposite reality.
The only instrument that answers "can I invoke this?" is an actual invoke. That
is why `scripts/e2e_bedrock_rag_judge_test.py` preflights each model with a real
5-token call instead of trusting the availability API.

⚠ **A Bedrock API key (`ABSK…`) carries its own IAM policy, fixed at creation.**
Granting model access in the console afterwards does NOT widen an existing key.
A key minted before a model shipped can deny exactly that model while allowing
older ones on the identical code path — which is indistinguishable from an
account-level block unless you swap the credential.

Model targets are **code defaults**, not env (`railway.toml [deploy.envs]` has
never applied — hard-won; see the gotchas):
`REGENOLD_BEDROCK_MODEL` = `eu.anthropic.claude-opus-4-8` (Stage-1 + Stage-2),
`REGENOLD_BEDROCK_COMPLEX_MODEL` = `eu.anthropic.claude-opus-5`,
`REGENOLD_BEDROCK_JUDGE_MODEL` = `eu.anthropic.claude-sonnet-5`.

### R328.2 — the pins are the ASPIRATION; a fallback chain is what ships

⚠ **Measured live 2026-08-13 with the current `ABSK…` key, ALL THREE pinned
targets are `AccessDeniedException`** — not just `opus-4-8` as R328 recorded:

| profile | invoke |
| --- | --- |
| `eu.anthropic.claude-opus-4-8` | **DENY 403** |
| `eu.anthropic.claude-opus-5` | **DENY 403** |
| `eu.anthropic.claude-sonnet-5` | **DENY 403** |
| `eu.anthropic.claude-opus-4-6-v1` | OK |
| `eu.anthropic.claude-sonnet-4-6` | OK |
| `eu.anthropic.claude-sonnet-4-5-20250929-v1:0` | OK |

✅ **RE-VERIFIED LIVE 2026-08-14 — unchanged, all six rows reproduce exactly.**
Real 5-token invokes against each profile with the current `.env` key: the three
pins return `api_access_denied_403` (1595 / 275 / 292 ms), the three older tiers
return `OK` (1370 / 1042 / 1529 ms). `fallback_chain_for` returns the correct
SUFFIX for each pin (opus-4-8 → opus-5 → opus-4-6-v1; opus-5 → opus-4-6-v1;
sonnet-5 → sonnet-4-6 → sonnet-4-5). A full `scripts/e2e_bedrock_rag_judge_test.py
--fallback` run passed **4/4 judge axes** with `_judge_model_served =
eu.anthropic.claude-sonnet-4-6`. So the degraded tier is healthy and the R328.2
failover is doing exactly what it was built to do — but note the judge served is
`sonnet-4-6`, i.e. `judge_model_comparable` is FALSE against the sonnet-5-graded
July-7 baseline.

Per the key-vintage note above this is a **credential** boundary, not an account
block, so the pins stay put and `complete_with_fallback`
(`app/llm/bedrock_client.py`) degrades **within the family** per call:
`BEDROCK_FALLBACK_CHAINS` = opus-4-8 → opus-5 → opus-4-6-v1, and sonnet-5 →
sonnet-4-6 → sonnet-4-5. Re-mint the key and the pinned tier resumes with **zero
code change**; leave it and every request still succeeds one tier down.

Both the RAG path (`_bedrock_complete_for_graph_rag`) and the judge path
(`_call_judge_bedrock`) call the SAME function — one concept, one definition.

* **It degrades, never escalates.** `fallback_chain_for` returns the chain
  SUFFIX below the requested model, not the whole chain. Returning the whole
  chain meant pinning `sonnet-4-6` retried on `sonnet-5` — silently promoting
  to a costlier tier the operator specifically did not choose. A model in a
  known family but absent from its chain has unknown rank and gets **no**
  fallback; we never guess a substitute we have not verified.
* Failover advances **only** on an entitlement error. Two classes, and the
  difference matters:
  * `api_access_denied` / `api_resource_not_found` — **durable per-model**;
    skipped AND remembered.
  * `api_validation` — **skipped but NEVER remembered.** `ValidationException`
    is overloaded: it covers "profile unresolvable in this Region" (per-model)
    *and* "input too long / bad maxTokens" (per-request). Caching the
    per-request case as a model denial let ONE oversized prompt evict the only
    invocable model for the whole TTL — a single long row poisoning the rest of
    a judge batch.
  * A throttle or timeout returns immediately: the next model would hit the
    same wall, so burning the chain turns one blip into N failed calls.
* ⚠ Markers are anchored on the `api_` prefix that `_classify_client_error`
  emits, NOT bare substrings. The blanket `except Exception` formats errors as
  `unexpected_error: {TypeName}: {msg}`, so a bare `"validation"` match made a
  botocore `ParamValidationError` — a *code bug*, identical on every model —
  read as an entitlement failure and burn the chain.
* When the whole chain is cached-denied it re-probes the **tail**, not the
  head: the head is 403 by construction, so re-probing it just burns the
  round-trip the cache exists to avoid.
* A denied model is remembered for **15 min** (`_DENIED_TTL_SECONDS`), so the
  403 round-trip is paid once per TTL, not once per request. Measured live:
  first call 7,485 ms, second **2,297 ms**. The TTL is bounded on purpose — an
  unbounded memo would pin the degraded tier until redeploy.
* Watch `bedrock_entitlement_fallback_used primary=… served_by=…` in the logs.
  If that line is absent, the pinned tier is working again.

⚠ **Do NOT "fix" the 403 by lowering the defaults.** The 2026-08-13 working tree
did exactly that *and* added a fallback pointing at the new default, so
`fallback_id == model_id` and the failover was unreachable on the tier it
guarded — the inert-feature trap, in the one place it costs production. The
regression test is `test_fallback_target_differs_from_pinned_default`.

### ⚠ A silent model swap is a MEASUREMENT bug before it is a cost bug

The chain changes which model answers. In a repo whose product IS the
measurement, that must reach the **durable artifact**, not just a log line —
nothing in the eval pipeline reads logs.

* **Stage-2 / RAG.** `_bedrock_complete_for_graph_rag` records
  `stage2_model=<served>` into the reasoning trace, the same note the wrapper
  and Anthropic paths emit, because `run_official_batch._provenance` scrapes
  exactly that string and aggregates `stage2_models` *specifically* to catch a
  silently degraded Stage-2 provider. It also records
  `bedrock_fallback requested=… served_by=…` when the chain moved. Without
  this the sidecar asserted the PINNED model for every row.
* **Judge.** `_call_judge_bedrock` returns `_judge_model_served`;
  `evals/judge/grounded.py` aggregates it into `judge_model_served` +
  `judge_model_comparable` and prints a loud `judge model DEGRADED` line.
  `judge_model` alone records what was REQUESTED — on a degraded run that is an
  *active false attribution*, which is worse than no record.

⚠ **The July-7 baseline is graded by `sonnet-5` via the wrapper.** A Bedrock
re-run degrades the grader to `sonnet-4-6` — which is also `_DEFAULT_JUDGE_MODEL`,
so the two configurations are trivially confusable. **Check
`judge_model_comparable` before grading anything against the baseline block.**

⚠ **A model A/B over `REGENOLD_BEDROCK_MODEL` is currently INERT** while the
pins are 403: distinct cache keys, distinct arms, but the chain serves
`opus-4-6-v1` for all of them. Read `stage2_models` in the aggregate before
believing any model-tier comparison.

### R328.3 — truncation must be impossible-or-loud, never silent

Operator directive (2026-08-13): **no truncation at any stage**, so context
stays intact until the answer is delivered. Four surfaces were cutting content
and none left evidence. Measured live, enumerative answers surviving Stage-2
went from **1/4 to 4/4**.

**⚠ `maxTokens` means something DIFFERENT on Bedrock than on the wrapper.**
The Claude-Max wrapper IGNORES it (R102: `max_tokens=24` returned
`completion_tokens=1742`). Bedrock HONOURS it. So the shared
`settings.graph_rag.max_tokens = 1536` — merely advisory upstream — was a hard
mid-word cut here. Measured at 1536: **3 of 4** enumerative questions returned
`stopReason=max_tokens`, ending mid-word (`"…Assistive"`). The ceiling must
never be the thing that stops the model; verbosity is the prompt's job.
Now `REGENOLD_BEDROCK_MAX_TOKENS` (4096).

**⚠ Raising a ceiling relocates the cut — it does not remove it.** At 4096 the
worst case took ~70 s against the 60 s default `read_timeout` and came back
`ReadTimeoutError`: the same truncation one layer down, and *more* expensive
because it yields nothing at all. Any token-budget change must move
`REGENOLD_BEDROCK_STAGE2_TIMEOUT_S` with it.

**`stopReason` is the precise signal and it was never read.** The wrapper,
Anthropic and Gemini branches each check their equivalent; the Bedrock branch
checked neither, leaving the one honest signal unused while a prose heuristic
carried the load. A cut that happens to land on a period now fails loudly and
records `stage2_truncated_max_tokens` in the trace.

**⚠ A false truncation costs the answer TWICE.** `set_answer_no_cap` is gated on
Stage-2 landing (`regenold.py`), so discarding a polish also **re-arms
`MAX_ANSWER_SENTENCES = 3`** and the char cap. Measured on the recorded Bedrock
run: Stage-2-off rows max **785 chars** and ≤3 sentences; Stage-2-landed rows
reach 2061 chars and 8 sentences. So `_looks_structurally_truncated` is not a
cheap guard — every false positive is a two-stage downgrade.

And it *was* false-positiving: an answer with `stopReason=end_turn` using 2215
of 4096 tokens, ending `*Sources: … Recitals 46-59.*`, was judged truncated on
its closing `*`. **Markdown emphasis/code markers (`*_`` ~`) now peel like
quotes and brackets already did, and a complete table row (`| … |`) is a
structural ending.** Long role×obligation matrices legitimately end on one.

**Two silent-loss fixes from the R328.3 audit:**

* `kg_context._fit_complete_lines` returned `""` when a block could not fit its
  budget — an entire provision hierarchy vanishing with no marker, which is
  CLAUDE.md's own "a ceiling that falls back to a smaller limit is a switch,
  not a ceiling". It now cuts AT the ceiling and marks ` [...]`, which is what
  `_flat` had been doing correctly all along.
* `reasoning_trace.record_note` stopped at **32** notes. Every clamp in the
  pipeline reports itself ONLY via a note (`stage2_model=`,
  `adaptive_ref_clamp_to=`, `stage2_truncated_max_tokens`,
  `dropped_over_budget`), so the audit trail truncated before the thing it
  audits — silently. Raised to 128, and the overflow now says so.

⚠ **Latency is a scored axis and this moves it.** Complete enumerative answers
now take 38–62 s (a short verdict is ~13 s). Before, those questions burned the
same time and *then* discarded the answer, so this is strictly better — but the
lever for shortening them is the PROMPT, never the ceiling.

⚠ **Still unfixed, from the same audit — these silently drop content today:**
`REGENOLD_ADAPTIVE_REF_CLAMP` (**default ON**, undocumented, cuts scenarios to 5
refs and is `stage2_landed`-gated so davidath cannot see it); judge
`max_tokens=400` hard-coded on the wrapper/Anthropic paths with no env (only
Bedrock got 1600); the judge prompt caps (`_GOLD_TEXT_CAP` 12000,
`_PRED_TEXT_CAP` 6000, `_MAX_PRED_REFS` 8) which make `legal_v2`'s
quote-or-retract gate *invert* — an unquotable provision downgrades WRONG to
SUPPORTING, so truncation inflates the pass rate; and `REGENOLD_KG_MAX_UNITS=24`
rendering Article 3 as 24 of its 68 definitions under a heading that reads
"PROVISION STRUCTURE".

The wrapper lives at `D:\Claude Projects\claude-code-openai-wrapper` (not this
repo) and bills the flat Max subscription. Evals MUST use it, not SDK-direct.

```bash
$env:OPENAI_API_BASE = "http://127.0.0.1:8000/v1"
$env:OPENAI_API_KEY = "dummy"
$env:P2P_GRAPH_RAG_PROVIDER = "openai_wrapper"
```

## Testing

```bash
# deterministic env for every gate
OPENAI_API_BASE=http://127.0.0.1:1/v1 P2P_GRAPH_RAG_PROVIDER=cli REGENOLD_EXTERNAL_EMBEDDINGS=0

py -3.12 -m pytest tests/ -q -p no:cacheprovider          # full suite (judge the SET)
py -3.12 -m evals.bench.runner                            # davidath 476
py -3.12 -m evals.regenold.runner                         # 276 scenarios
py -3.12 -m evals.regenold.runner_v2 --local --probe-oos --oos-suite all --label X
py -3.12 scripts/check_legal_version_drift.py             # exit 0 = no legal drift
py -3.12 -m evals.harness.ab_judge                        # THE MERGE GATE
```

The July-7 re-evaluation (this repo's reason to exist):

```bash
py -3.12 -m evals.regenold.run_official_batch --label <L> --mode easy   # and --mode hard
py -3.12 -m evals.judge.grounded --sidecar evals/bench/results/official-<L>-easy.ckpt.jsonl \
    --label <L> --model claude-sonnet-5 --provider wrapper --timeout 120 --concurrency 3
```

`--mode hard` is **the graded turn** (the adversarial pushback) and has never
been run. Score the Omnibus probe with `classify_hit()` (IMPORT vs REJECTION) —
a bare substring match counts a correct rejection as a leak.

## Legal-version constraint (operator, 2026-08-07)

Use the **original** Regulation (EU) 2024/1689 as adopted (in force 1 Aug 2024).
**No Digital Omnibus.** Audited clean: Article 113 carries only the adopted
dates (2 Aug 2026 / 2 Aug 2027), Article 51 only 10^25, 113 articles with zero
lettered entries, 68 definitions with no 3(14a)/(14b).

Enforcement is on the delivered **user** channel, because the old rule sat only
in the Stage-2 system prompt the wrapper drops.

**Kept by operator decision:** the Commission GPAI Guidelines content (10^23
threshold, one-third fine-tune rule). It is 18 July 2025 soft law, correctly
attributed, not Omnibus — and `tests/test_kb_stubs_filled.py` pins it.

## Open, ranked

Full handoff: [`.planning/NEXT-SESSION.md`](.planning/NEXT-SESSION.md).

1. **DONE — the semantic layers are gated ON, constrained-only.** Three arms,
   grounded judge, 50 live July-7 rows each
   ([`docs/R327-live-ab-semantic-layers.md`](docs/R327-live-ab-semantic-layers.md)):

   | arm | ans (hist.) | ref pass | ref MACRO | ref micro | wrong/total | cite |
   | --- | --- | --- | --- | --- | --- | --- |
   | layers OFF | 0.880 | 0.380 | 0.675 | 0.611 | 51/131 | 0.900 |
   | both halves | 0.880 | 0.360 | 0.642 | 0.583 | 55/132 | **0.960** |
   | **constrained only** | 0.880 | 0.367 | 0.657 | **0.614** | **49/127** | **0.960** |

   Shipped `REGENOLD_GRAPH_SEMANTIC_LAYERS=1` + `REGENOLD_SEMANTIC_GLOSS=0`.
   ⚠ Not significant at n=50 (p=0.453) and it ships 2 fewer judge-correct refs, and
   `gold_coverage=0.0` here means hard rule #8's `gold_dropped` is **unmeasured** —
   `easyhard_ab` is what can supply it. **That is now the top follow-up.**
2. **Run `--mode hard`.** It is **the graded turn** (the adversarial pushback;
   67 of 111 hard rows carry it) and it has NEVER been run. Every optimisation
   decision on the table is being made on the *easy* turn — that is the
   instrument trap. Free, ~40-70 min.
3. **Re-verify the baseline reproduces** before grading anything against it.
   R327 rebound the canonical axis names to the historical formulas, so the block
   above should be measurable again; if it does not reproduce, stop and find out
   why.
4. **Gate the parent-collapse** with `easyhard_ab` (davidath cannot see it).
   +0.018 F1 / +5 rows measured offline; one gold ref is the price.
5. **Attack GENERATION, not selection.** R325 closed the ranker, so the
   remaining ~90% of the over-citation gap is upstream: why does a 3-ref answer
   name a wrong provision **53% of the time at rank 3**? The refs-per-row cliff
   is the shape of it — 1 ref → 0.88 pass, 2 → 0.54, **3 → 0.05**, 4+ → 0.06,
   with 41 of 100 rows sitting at exactly 3 (the QA budget). R327's constrained
   sub-provision layer is the first instrument aimed here.
6. **`CROSS_REFERENCES` backlinks as non-citable context** — 248 edges, never
   read as context, real legal signal. The best unshipped graph idea; needs its
   own gate, and prompt budget competes with Answer-Conciseness.
7. **Fix the judge** before trusting any further answer number — the length
   artefact above. `evals/judge/legal_v2.py` already implements the
   quote-or-retract rule that catches it.
8. **Watch conciseness** — answers are **+41% longer** than the graded July-7
   ones, on the one axis the official scorecard says we lead. Any bound must be
   SENTENCE-only (hard rule #2).

**Closed — do not re-open:** R326 review finding I1 (`_ENUM_OPENER_RE`) is a
non-finding (enumerated units begin at `(a)`; verified 5(1)/10(2)/13(3) match,
26(1) is 228 chars so nothing truncates). I2-I5 are done. `_DEONTIC_CYPHER` parses
fine on Aura. The judge's parent-text fallback must stay removed.

---

**History:** [`docs/ROUNDS.md`](docs/ROUNDS.md) — every round entry, verbatim.
**Handoff:** [`.planning/NEXT-SESSION.md`](.planning/NEXT-SESSION.md).
