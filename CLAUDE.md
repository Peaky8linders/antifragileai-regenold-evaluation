# CLAUDE.md — Regenold EU AI Act RAG (re-evaluation repo)

Load-bearing context for an LLM coding assistant. Read top-to-bottom before
making changes. Numbers were re-measured across R338-R340 (2026-08-15); the
decision record for that session — question, evidence, decision — is
[`docs/R340-session-decisions-and-open-questions.md`](docs/R340-session-decisions-and-open-questions.md),
its measurements are in [`docs/R339-stage2-restored-and-bypasses-settled.md`](docs/R339-stage2-restored-and-bypasses-settled.md).
The per-round log is **[`docs/ROUNDS.md`](docs/ROUNDS.md)** — search it, don't read it.

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

⚠ **One leg of that argument was retracted 2026-08-14** — "the provider table
says Bedrock is what Railway runs" was never verified. The conclusion (**a merge
here ships**) is now MEASURED independently: on 2026-08-15 the service's
`/healthz` reported the deployed commit tracking `main` (see below). *Which
provider* it runs is a separate question, answered by probe and not durable —
see the provider section. Do not conflate the two again.

```
project      e19dc6ef-b463-4a54-9662-4a5085ae00c9
service      0086ff18-f642-46c8-8127-57c913ca1c53
environment  2f6298dd-881c-4848-81eb-5017a8a64c32
domain       https://antifragileai-regenold-evaluation-production.up.railway.app
```

⚠ **The domain is RECORDED now (2026-08-15, R338).** `CLAUDE.md` and
`.kiro/steering/railway-redeploy.md:60` both used to say it was unrecorded and
send the reader to the dashboard; `.kiro` still does. `GET /healthz` returns
`{"status":"ok","version":"1.2.3","commit":"<sha12>",…}` — **the `commit` field
is the instrument for "did my merge actually ship?"**, and it is cheap. Two
eval runners had been defaulting `--endpoint` to the **sibling** repo's service
(`regenold-eu-ai-act-rag-production`), i.e. measuring a codebase that does not
contain the change under test; R338 repointed
`evals/regenold/antifragile_live.LIVE_ENDPOINT` and `runner_oob.py --endpoint`
here and kept the sibling one flag away as `SIBLING_ENDPOINT`.

⚠ **Railway's GitHub integration DOES auto-deploy a merge to `main` — with a
lag.** Measured 2026-08-15: the service served a commit five behind `main`, then
HEAD hours later. So a merge and a live probe in the same session will disagree.
**Read `/healthz.commit` before believing a merge shipped, and before attributing
any live measurement to a commit.** Treat a merge here as **shipping**, not as a
bench artefact — which is exactly why `railway.toml [deploy.envs]` being inert
matters (see the gotchas): config must be a CODE default or it never arrives.

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
| `app/data/ontology.py` | `PRACTICE_REGISTRY` **×8**, `ANNEX_III_REGISTRY` **×8**, `PHASE_REGISTRY` **×4**, plus the six AIRO registries `938933a` added: `RISK_SCENARIO_REGISTRY` **×8**, `RISK_CONTROL_REGISTRY` **×9**, `GPAI_REGISTRY` **×4**, `CONFORMITY_ROUTE_REGISTRY` **×3**, `FRIA_REGISTRY` **×1**, `SERIOUS_INCIDENT_REGISTRY` **×3**. **All six feed the BM25 index.** 0 dangling citations (normalise the sub-point tail before resolving — `Art. 5.1.a` keys as `Art. 5`). |
| `app/data/definitions.py` | **68** Art. 3 definitions. |
| `app/data/provision_text.py` | Verbatim resolver: article / paragraph / point / sub-point / annex item, section-aware. |
| `app/data/official_eu_ai_act.py` | Pinned EUR-Lex text, CELEX `32024R1689` (**pre-Omnibus**), 180 recitals. |
| `app/data/kb_search.py` | BM25 index — **373 docs** by default (131 kb / 48 ontology / 126 corpus / 68 definition), measured 2026-08-15. **345** is the `REGENOLD_ONTOLOGY_RISK_DOCS=0` arm, i.e. the pre-`938933a` corpus. |
| `app/data/kb_xrefs.py` | Cross-reference graph: **149 core** edges, **249 full**. |
| `app/data/eu_ai_act_tree.py` | **1,412**-node document tree. |
| `app/engines/_assets/` | Embeddings index — `is_available()` True, **0** asset SHA mismatches vs the manifest. TurboQuant precomputed — enabled, staleness guard present and passing. |

⚠ Older round entries quote `~165` / `348` / `347` BM25 docs, `Practice ×9`,
`Phase ×6`, and a `1,426`-node tree. **All four are stale** — the table above is
measured. **A BM25 doc count is meaningless without its gate value**: quote it
as `373 (risk-docs ON)` or `345 (risk-docs OFF)`, never bare.

⚠ **The six AIRO registries are NOT an additive corpus extension.** Their 28
virtual documents land in the MIDDLE of the corpus, so `n_docs` 345→373 and
`avg_doc_len` 94.5→91.7 move IDF and length normalisation for **every**
pre-existing document — the whole corpus re-ranks. Measured over the 110
official-batch rows, `_deterministic_parse` changes its entity set on **9 rows
and all 9 LOSE a provision** (the toy question loses Annex III; "which systems
are high-risk" loses Art. 6 and Art. 7; the QMS question loses Art. 11 and the
Annex IV xref), while `Art. 27` is GAINED on 5 because the FRIA document dumps
six generic `required_steps` into one anchor. Wire references were
byte-identical on 110/110 under `provider=cli`, so the blast radius is the
**Stage-2 grounding context** — which that arm cannot observe. Two authoring
defects to fix whatever the gate says: documents are keyed on the first element
of an arbitrarily-ordered citation tuple (`scenario.statutory_violation[0]`,
`control.articles[0]`, `fria.governing_articles[0]`), and several duplicate
their keyword tuple for 2× term weight.

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
   ⚠ Nor can `provision_exists`, which is head-level LAX (see the gotchas) —
   and it is **violated in-tree today at `evals/judge/legal_v2.py:660`**, where
   `if not provision_exists(ref)` is the `NON_EXISTENT_PROVISION` gate. Measured
   across every recorded sidecar it has fired on **zero** refs, while the
   fabricated leaves it passes (`Article 3.14a`, `Annex III.4.employment`,
   `Article 4.2` ×11, `Annex IX.99`) are then scored SUPPORTING, because an
   unquotable provision downgrades WRONG → SUPPORTING. Only
   `get_provision_text(ref) is not None` validates a leaf; R338 pinned that for
   the Cappelli gold in `tests/test_cappelli_dataset_legal.py`, the judge is
   still unfixed.
6. **`dynamic_ab` IS THE MERGE GATE. davidath is RETIRED — do not run it.**
   See Validation policy. Never ship on "davidath byte-identical": it runs
   `provider=cli` with no Stage-2, so for most changes it is not a weak signal,
   it is *no signal*. And never accept `+0.0000` as "safe" without a FIRE
   CHECK — a flat A/B and a dead feature are the same picture.
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

## Validation policy — `dynamic_ab` is the gate. **davidath is RETIRED.**

⚠ **RETIRED 2026-08-14 (operator directive). Do NOT run `evals.bench.runner`
(davidath 476) as a gate, and do NOT report its numbers as evidence.** It gets
in the way: it produces a confident, precise, *irrelevant* answer, and reading
it costs more than it informs.

Why it is worse than useless rather than merely weak:

* It runs `P2P_GRAPH_RAG_PROVIDER=cli` — **no Stage-2 at all**. Every prompt
  change, every judge change, the Cohere reranker and the whole KG-context block
  are invisible to it *by construction*.
* R331 is the case in point: davidath reported "baseline reproduces, all deltas
  ≤ 0.0007, Scenarios byte-identical" on a change set containing four judge
  fixes, a reranker and three legal corrections. Every one of those was outside
  what the instrument can observe. A green davidath there is not reassurance —
  it is the instrument trap, and quoting it invites the reader to believe the
  change was measured when it was not.
* Its gold is head-level and single-article (mean 1.00 refs/row), so it
  structurally cannot show a chain-dropping defect (hard rule #7), and it is
  BM25-saturated, so retrieval levers read flat *because it is blind*.

⚠ **The same trap shipped twice more, in modules whose NAMES deny it.**
`evals.bench.run_cappelli_bench` and `evals.bench.run_live_deep_eval` (`cc47f8b`)
both defaulted `--provider` to **`cli`** and both *assigned*
`P2P_GRAPH_RAG_PROVIDER`, overwriting an operator's exported value — so a file
printing `RUNNING LIVE EVALUATION` ran the no-Stage-2 path, and it was the
instrument shipped in the same commit to justify a Stage-2 **prompt** change.
Both ran inert unnoticed: `cappelli_bench_results.json` carries per-row
latencies of **14.5-440 ms** across all 20 rows (this repo's own cheapest inert
detector) and still printed a full 5-dimension scorecard; `run_live_deep_eval`
averaged **91.8 ms/row** against a ~16 s live baseline; and neither artefact
recorded the resolved provider, so neither can be re-attributed afterwards.
`cli` also leaves `stage2_landed` False, re-arming `MAX_ANSWER_SENTENCES = 3`,
so both scored ≤3-sentence capped answers against multi-sentence gold. R338
defaults both to `openai_wrapper`, honours an exported value, and writes the
resolved provider + Stage-2 model + per-row `stage2_landed` into the artefact.

**Use `evals.harness.dynamic_ab`.** It is built around the one property every
inert A/B in this repo's history lacked:

1. **FIRE CHECK BEFORE ANY NUMBER.** It runs both arms, asserts they actually
   diverge, and **ABORTS with `INERT`** — printing no axis table at all — when
   they do not. A flat result and a dead feature are the same picture, so
   `+0.0000` is reported as *unmeasured*, never as *safe*. R326, R327 and three
   R329 reranker placements all shipped clean `+0.0000` runs on features that
   never executed; this is the fix for that class.
2. **Sample size follows observed variance, not a constant.** Rows run in
   batches; each axis gets a bootstrap CI, and the run stops when every axis is
   resolved. Verdicts distinguish **NULL** (tight CI around zero — a real null)
   from **UNDERPOWERED** (CI spans zero and is wide — say so). A 0.003 delta on
   9 effective rows is UNDERPOWERED, not a finding.
3. **Live path by default** (Stage-2 on), because that is where the product is.
4. **`gold_dropped` on both grains, as a VETO** — hard rule #8 is not an axis to
   trade against. ⚠ **The exact-grain half of that veto was DEAD until R338.**
   R337's grain guard read each row's gold from a `"row"` key that `_run_arm`
   has never written, so `applicable` was ALWAYS False: a branch dropping 5 gold
   coordinates at exact grain printed `n/a` and **no REJECTED line**. Its tests
   passed 5/5 the whole time because the fixture hand-built a dict *with* that
   key — a data shape production never produced. Gold is now carried out of
   `_run_arm` by one `_row_record()` definition the tests also call, and the
   grain is decided PER ROW (head-level gold cannot support an exact-grain veto;
   there a MORE precise citation reads as a loss). **A test fixture that builds
   its own input is not a test of the producer** — make the test call the
   producer.
5. **Genuinely stratified sampling.** `probe_set` is ordered by source, so the
   `[:n]` slice earlier runs called "stratified" took whole sources and dropped
   others; `_stratified()` round-robins across sources instead.

```bash
py -3.12 -m evals.harness.dynamic_ab --flag REGENOLD_COHERE_RERANK --label x
py -3.12 -m evals.harness.dynamic_ab --branch-env REGENOLD_ONTOLOGY_RISK_DOCS=0 --label y
```

⚠ **But choose the instrument by the gate's MEASURED FIRE RATE on the actual
probe rows, not by reputation — `dynamic_ab` included.** R339 counted where the
two Stage-2 bypass gates fire: Antifragile **11/20**, GraphRAG 14/40, official
batch 22/110, and `probe_set` **2/132**. A `dynamic_ab` run there moves 2 rows
and reports a meaningless NULL — the inert-A/B trap arriving through the PROBE
POOL rather than the harness. Antifragile 20 was the correct instrument and is
what settled them. Check the provider too: `_stage2_provider_enabled`
(`_graph_rag_impl.py:1302`) returns at `:8181`, **before** both bypass gates at
`:8222` / `:8241`, so any `provider=cli` arm on them is inert by construction.

Gate for any change that can move an answer, a reference, the tone, or a scope
decision:

1. **Live verification first** — probe the real failing case. A reference /
   Stage-2 / scope change MUST be seen working LIVE.
2. **`evals.harness.dynamic_ab`** — fire-checked, adaptively sized, with the
   `gold_dropped` veto. **This is the merge gate.**
3. `evals.harness.ab_judge` when you specifically want a pairwise LLM judgement
   on answer quality (it has a conciseness axis and is length-aware, though
   `_ab_block` truncates at 1400 chars so it is tail-blind).
4. 276-runner + OOS probe — cheap regression guards.

Env-gate every such change (default-ON in code) so the A/B can flip OFF↔ON, and
keep the off-switch for instant rollback. ⚠ An env gate is necessary but not
sufficient: a module-level `lru_cache` outliving the flip makes the A/B inert
even with the flag in `_engine_cache_key` (measured on
`REGENOLD_ONTOLOGY_RISK_DOCS`, R332 — the index memo had to be keyed on the gate
before the arms differed at all). The fire check is what catches this.

## Current baseline — HISTORICAL ONLY, not a grading target

⚠ **RETIRED 2026-08-14 with davidath itself. Do NOT grade a change against this
table.** It is a `provider=cli` measurement — no Stage-2, head-level
single-article gold, BM25-saturated — so reproducing it says the deterministic
retrieval/answer-assembly path is unchanged and **nothing else**: not the
prompts, not Stage-2, not the judge, not the reranker, not the graph context.
R331 reproduced it to ≤0.0007 while changing four things it cannot see. Grade
with `evals.harness.dynamic_ab` instead. Kept only because older rounds cite it.

<details><summary>historical davidath numbers at <code>c6db579</code> (2026-08-09)</summary>

| davidath | Ans Loose | Ans Strict | Ans Conc | Ref Loose | Ref Strict | Ref Conc | Tone |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **OVERALL (476)** | 0.1884 | **0.3545** | 0.6143 | **0.5971** | **0.4748** | 0.4319 | 1.0 |
| QA (137) | 0.1407 | 0.4072 | 0.1961 | 0.8394 | 0.5536 | 0.4390 | 1.0 |
| Scenarios (339) | 0.2076 | 0.3332 | 0.7833 | 0.4992 | 0.4429 | 0.4290 | 1.0 |

Re-measured 2026-08-14 at R331 (`e66577d`): OVERALL 0.1885 / 0.3552 / 0.6148 /
0.5971 / 0.4747 / 0.4319 / 1.0; Scenarios byte-identical; multi-turn 20/20. So
it still reproduces — and that fact carried no information about the change.

</details>

Multi-turn coherence and the OOS probe remain useful cheap guards.

Other gates: `evals.regenold.runner` **255/255**, RISK_F1 macro **1.00**, 28/28
categories · OOS probe (`--oos-suite all`, 51 rows) **49 pass, 0 scope leaks**
(2 known `adjacent_eu` soft fails).

⚠ **"56 pre-existing `pytest` failures, the documented `provider=cli` env
artifact" was FALSE — they are STALE MOCKS.** R340 triaged all 56 by execution:
R56/R127 put a provider pre-gate ABOVE the seam these tests mock
(`_stage2_provider_enabled`, `_graph_rag_impl.py:1302`;
`is_openai_wrapper_enabled`, `openai_wrapper_provider.py:367`) and it returns
False on the literal string `cli`, so the mock is never reached. Pinning the
file's provider to `openai_wrapper` — dead-port base retained, so no network is
reachable and every call site is a MagicMock — turned **65** green with no
assertion weakened; R340 landed that pin per file and the suite is at **~0
pre-existing failures**. Re-measure the count; do not quote this one, and do not
dismiss a failure as environmental again without executing the seam.

⚠ **R327 — this block is measurable again.** An uncommitted pass had rebound the
canonical axis names to new formulas, so any run graded against this table was
comparing two different rulers. Canonical names are back on the historical
formulas; `--assert-baseline` also works again (per-row `metric_provenance` inside
`scores` had made it permanently red).

⚠ An older pin of **0.4079 / 0.5543** appears in the log — it is stale. Diff a
suite result against a baseline checked out **in place** (`git stash`), never in
a `git worktree` — a worktree carries no `.env`, and the denoiser / topic-filter
/ safety-gate cluster changes behaviour on `GROQ_API_KEY` (measured 63 vs 92
failures on the same commit).

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

**⚠ The seed hazard (hard rule #12) — WORSE since `938933a`.** This repo ships
`SEED_VERSION = 2026-08-14-sota-airo-fullseed`
(`scripts/seed_neo4j_kb.py:136`); the live graph is
`2026-08-08-r323-annex-sections`, seeded by the RAG repo. The boot hook
re-seeds on ANY mismatch — it does not check which is newer — so booting this
repo with auto-seed ON **downgrades production's graph**, losing the
section-aware annex items and the SubPoint layer. The failure is silent: the
seeder succeeds, `/healthz/graph` still reports ok, answers just get worse.
`.env.example` pins `NEO4J_AUTO_SEED=0`; keep it.
⚠ The version STRING changed but the hazard did not: the two still mismatch, so
the re-seed still triggers. What changed is the blast radius — this repo's
seeder now also writes `RiskScenario` / `RiskControl` / `GPAIModelProfile` /
`ConformityRoute` / `FRIAWorkflow` / `SeriousIncidentSLA`, so a stray boot would
not only delete the annex/SubPoint work but inject six unreviewed label families
into the shared instance. The **18-label / 1758-node census above is still
correct for the LIVE graph** — this repo has never written to it — and stays
correct only for exactly as long as that remains true.

## Where we stand

* **Three separate scorecards. Never conflate them.** (a) The OFFICIAL regenold
  report — we beat 0 baselines, `Overall` is a **geometric mean** so the worst
  axis dominates, and **Answer-Conciseness is the only axis we lead** (zero
  headroom). (b) **`dynamic_ab` = the change gate** (davidath, which used to sit
  here as "regression guard", is RETIRED — see Validation policy). (c) The
  **frontier head-to-head** = the "are we SOTA?" measure.
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
* **LLM-judge baseline, shipped config** (`evals.judge.grounded`,
  `claude-sonnet-5`, Antifragile n=20, 0 errors, `answer_grounding_source =
  gold_refs` on 20/20 because `ANTIFRAGILE_GT` supplies a `gold_answer`): answer
  correctness **0.85**, reference correctness **0.50** (P 0.789 / R 0.955 / F1
  0.864), citation faithfulness **1.00** — and **9 of the 10 reference failures
  are OVER-CITATION**. ⚠ Without a `gold_answer`, `grounded._prepare` grounds
  the answer axis on the answer's OWN `pred_refs`, i.e. self-graded; check
  `answer_grounding_source` before quoting any answer number.
* **R340 — the rebuilt Stage-2 system prompt ships default-ON**
  (`REGENOLD_PROMPT_V2`, 51,516 → 16,146 chars). Judge reference precision
  0.7890 → **0.8385**, F1 0.8641 → **0.8859**, recall 0.9550 → 0.9389; answer
  correctness and citation faithfulness FLAT; ans_conciseness 0.5160 →
  **0.5518**; latency p50 −174 ms. ⚠ **Effective n is 9**, not 20 — only 9 rows
  reach Stage-2 — so this is a signal CONSISTENT across two instruments, not a
  RESOLVED one. **The confirmatory V1-vs-V2 A/B ran live (R346, n=60, Bedrock)
  and V1 was REJECTED by the gold veto (gold_dropped 15→16, +1) — V2 is
  confirmed as the live default.** The shipped V2 is a strict SUPERSET of the
  arm measured (4 more system sentences, 3 more user-clause sentences, all
  targeted judge fixes), so the measured delta understates it.
* **R346 — three live Bedrock A/Bs (n=60, Opus 4.6 Stage-2, re-minted ABSK
  key, 0 HTTP errors in every arm).** Rerank (R340.1) FIRED **49/60** rows but
  is a wash (every axis UNDERPOWERED, gold 17→17, +1.0 s latency). Query
  expansion (R341) FIRED **37/60** and is the arm to push: ref_loose **+0.039**,
  kw_recall **+0.029** (CIs mostly above zero), gold **17→14** (branch BETTER),
  flat latency — UNDERPOWERED at n=60, so it needs more rows to resolve.
  V1-vs-V2: FIRED 13/60, **V1 REJECTED by the gold veto** (see above). Sidecars:
  `evals/bench/results/dynamic-ab-r346-*.json`; evidence in
  `docs/R346-live-bedrock-ab.md`. ⚠ The expansion run used the Haiku
  paraphrase tier; R346.2 switched paraphrases to the frontier Sonnet 4.6 tier
  and the confirmatory re-run was interrupted — re-run before trusting those
  numbers.
* ⚠ **R338's "−5 expert-mistake regression" (q03/q04/q14) is RETRACTED** — it was
  measured while Stage-2 was dead (the argv ceiling). With Stage-2 restored the
  same resolver gives **34/38**, above the R318 baseline's 33/38. Do not quote
  that report's R318↔R338 table.
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
  identical at the model, because the swap sat inside the system prompt the
  wrapper *then* dropped. Do not cite it as evidence that prompt volume is
  harmless; R340 re-opened that question on a delivered prompt (see below).
* **The Cappelli et al. (2026) paper's 7 optimisations** — none buildable; the
  authors built no retrieval system and their failure mode is UNDER-citation,
  the inverse of ours. ⚠ **The line now has EVIDENCE, not just an argument.**
  `cc47f8b` built two of them anyway — #2 (an Art. 27 FRIA generator) and #3 (an
  Annex IV checklist injector) — as two sentences on
  `USER_ANSWER_COVERAGE_CLAUSE`, the Stage-2 **user** channel, delivered on 100%
  of requests on every provider, ungated and unmeasured. Both were WRONG against
  the pin; R338 reverted them (`graph_rag_prompts.py:898-903`). The checklist
  named an eight-item "Annex IV" that is not Annex IV —
  `get_provision_text("Annex IV")` is 5,710 chars over **nine** points, `'ce
  mark'` does not occur in it (CE marking is Article 48), and it omitted point 1
  entirely, including **1(e)**, the hardware description graded question `rg_001`
  turns on. The FRIA sentence told the model to name rights *"under the relevant
  Charter articles"*: Charter articles 1-54 all resolve in `ARTICLE_EXISTENCE`
  so the lint floor is blind by construction, and the foreign-instrument guard is
  adjacency-anchored so an enumeration suppresses only the member next to the
  token "Charter" — executed, `_prose_citation_bases` returns
  `['Article 1','Article 21','Article 47']`, which Component D then puts on the
  wire as AI Act citations. **An optimisation from that paper is a claim about
  law: it must clear `get_provision_text` before it clears an A/B.**

## Gotchas that have each cost a session

* **The Stage-2 SYSTEM prompt IS delivered — since 2026-08-15 — and it now
  carries a HARD 32,767-char ceiling.** The old gotcha ("the Claude Max wrapper
  drops it, 0% of requests see it") is DEAD: the wrapper passed
  `{"type":"text",…}`, not a valid `SystemPromptPreset` in
  `claude_agent_sdk 0.2.82`, so the SDK silently discarded it; a plain `str` is
  honoured and `WRAPPER_FORWARD_SYSTEM_PROMPT=1` is on. ⚠ **But the SDK passes a
  `str` system prompt INLINE INTO ARGV** (`subprocess_cli.py:229`), and Windows
  `CreateProcess` caps a command line at **32,767 chars**. Bisected on the
  running wrapper, everything else constant: 32,000 → **200 OK**; **32,768 →
  500 in 0.3 s**; 40,000 → 500. V1's `ANSWER_GENERATE_SYSTEM` is 51,516 chars, so
  enabling the flag killed Stage-2 on **every** request — and the SDK misreports
  the spawn failure as `"Claude Code not found at: …claude.exe"` (the binary is
  present, 265 MB), which is why it survived two service restarts. **A 500 with a
  "not found" message means the SPAWN failed, not the binary.** The wrapper now
  spills above `WRAPPER_SYSTEM_PROMPT_ARGV_LIMIT` (30,000) to
  `--system-prompt-file`; verified by NONCE ECHO at head *and* tail of a 51.4K
  prompt, because at that size an obedience sentinel tests behaviour, not
  delivery. **Keep any Stage-2 system prompt under 32,767 chars regardless** —
  V2 is 16,146 (`REGENOLD_PROMPT_V2`) and is therefore safe on an unpatched
  wrapper.
* **ABSK Bedrock keys live exactly 30 days and are shown ONCE at creation.**
  Both repos' `.env` share one key; when it lapses AWS answers EVERY model and
  the catalog with the cryptic `AccessDeniedException: Authentication failed:
  Please make sure your API Key is valid.` — which R346.1 now classifies as
  `api_key_invalid_403` (fails fast, never caches per-model, never tunnel-hops).
  Verified raw-HTTP against the official AWS contract before concluding the key
  was dead; the code was correct, the key had expired (R328.2 measured it
  authenticating 08-13, it failed 08-15). Re-mint in the AWS Bedrock console →
  API keys; the client reads the new value fresh per call, no restart.
* **Cohere rerank against a Trial key (10 calls/min): UNPACED = false INERT.**
  Every rerank 429s, fails soft, entities keep retrieval order, and the A/B
  reports INERT for a working feature (measured live). Pass
  `--min-call-gap 6.5` to `dynamic_ab` (R346), or use a production key.
* **When you write a legal rule into a prompt, ask WHICH SLOT it lands in, then
  check what the other slot already says about the same provision.** The accurate
  Annex IV(1)(e) / IV(2)(c) technical-documentation rule sat in
  `ANSWER_GENERATE_SYSTEM` (then unheard) while `cc47f8b` put a FABRICATED
  eight-item "Annex IV" on the always-delivered user clause — right law where
  nothing heard it, wrong law where everything did, and mutually contradictory on
  any provider honouring both. R338 reverted the fabrication; both slots are live
  now, so a contradiction between them reaches the model on every request.
* **`railway.toml [deploy.envs]` has NEVER applied** — Railway's `[deploy]`
  schema has no `envs` key. Bake config as **code defaults**.
* **Scripts don't load `.env`.** `scripts/seed_neo4j_kb.py` and
  `scripts/fetch_lawstronaut_provenance.py` are pure-stdlib — export the vars
  or they exit 1. The seeder prints its error at the TOP, so **never `tail` it**
  (and don't pipe a runner through `tail` either: `evals.regenold.runner` puts
  its summary on line 4).
* **`evals/harness/` does not load dotenv — and neither does `evals/bench/`.**
  Export explicitly or a runner silently falls to the deterministic path — the
  inert-feature trap. (The one exception is
  `evals/bench/representative_json.py`; every other module under both trees
  reads a bare environment.) ⚠ Worse than *not defaulting*: until R338 the two
  new bench runners **assigned** `P2P_GRAPH_RAG_PROVIDER`, so an operator who
  had correctly exported `openai_wrapper` was silently overwritten with `cli`.
  A runner may set an UNSET variable; it must never overwrite a set one.
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
* **A PROCESS SINGLETON holding raw corpus positions turns an in-process A/B
  into a mislabelling machine.** `app/engines/turboquant_index.py` kept
  `_INDEX = _DenseIndex()` with a `_loaded` latch and a `_bm25_idx_map` of RAW
  positions into whatever corpus existed at first build, then dereferenced a
  **live, gate-resolved** `_build_index()` through that **frozen** map. The
  ontology docs sit in the MIDDLE of the corpus, so flipping
  `REGENOLD_ONTOLOGY_RISK_DOCS` shifts every later document by 28. Measured in
  one process, `dense_top_k('serious incident reporting deadline')` returned
  `Art. 73 @ 0.8224` before the flip and `Art. 111 @ 0.8224` after — **identical
  scores, different labels**, no `IndexError`, no log line. So the literal
  rollback command in this file compared ON against a THIRD, index-shifted
  system that exists nowhere, and the **fire check PASSED**, because the arms did
  genuinely differ. R338 keyed the index on a corpus identity and rebuilds on
  mismatch. The build-time staleness guard was already there and ran once per
  process — **a guard that runs at construction cannot see a mutation after
  it.**
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
* **The corollary: a NAME must describe what the code COMPUTES.**
  `evals/bench/metrics.py` registered a `0.70 × char-trigram cosine + 0.30 ×
  word-Jaccard` score in `METRIC_PROVENANCE` as *"Sentence-BERT … decoupled from
  surface lexical form"* and printed it `SBERT:`. No embedding model exists on
  that path; measured, a conceptually equivalent low-lexical paraphrase scores
  **0.043** — near-zero on exactly the case the label names. `METRIC_PROVENANCE`
  is serialised into sidecars by seven writers, so the false attribution was
  stamped into artefacts of runs that never call the function. R338 renamed it
  `answer_trigram_jaccard`.
* **A curve whose labels come from the score it thresholds measures nothing.**
  The Cappelli threshold analysis did `all_sim_scores.append(sem_sim)` then
  `all_relevance.append(sem_sim >= 0.25)` and fed both to one function, so false
  positives were unsatisfiable for every `t >= 0.25` and **precision was
  identically 1.0000 by construction** — duly published as an empirical
  *"Crucial Finding"*. The primitive was fine and unit-tested with independent
  labels; the defect was entirely at the caller, which is why the suite was
  blind. R338 withdrew `threshold_precision_recall_curve` (it raises now) for a
  label-free `score_threshold_retention_curve`. **Ask where the ground truth
  came from, every time.**
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
| `REGENOLD_PROMPT_V2` | **ON** | R340 — selects `ANSWER_GENERATE_SYSTEM_V2` (**16,146** chars, XML-sectioned) over V1's **51,516** (−69%), inside `resolve_answer_system()` (`graph_rag_prompts.py:440`) — one selector, one concept. Under the 32,767 argv ceiling, so it is safe on an unpatched wrapper. `=0` is a byte-identical rollback to V1. **Live A/B (R346, n=60, Bedrock): V1 REJECTED by the gold veto (gold_dropped 15→16, +1) — V2 is confirmed as the live default** |
| `REGENOLD_CURATED_STAGE2_SKIP` | **ON** | R144, **settled by measurement R339 — keep ON**. Ships the curated deterministic answer without Stage-2; fires on 10/20 Antifragile rows |
| `REGENOLD_DEFINITIONAL_STAGE2_SKIP` | **ON** | R275, same verdict; fires on 1/20. Together the two bypass Stage-2 on **11/20** rows (9/20 reach it). Turning both OFF resolves the SAME 34/38 expert mistakes and costs ans_conciseness **−0.163**, ref_conciseness −0.099, ref_strict −0.068, judge reference precision −0.093, one citation-faithfulness failure and **2.4× latency**. Fire check passed (`stage2_polish` 9→19) |
| `REGENOLD_CROSS_REF_CONTEXT` | **ON** | the `CROSS-REFERENCED PROVISIONS` block in the Stage-2 user message. ⚠ Default-ON and **absent from `_engine_cache_key` since R69**, so every in-process A/B of this path was served one arm's cached output; registered R339 |
| `REGENOLD_CROSS_REF_SNIPPET_CHARS` | **20000** | R339 — per-node ceiling, clamped `[240, 60000]`. Was a hard-coded 240 that cut MID-WORD, and clipped Article 41 to 158 of 3,873 chars (96% loss) with **no marker at all**. Set above the largest reachable node (`art_3`, 17,079) so nothing truncates by default; `_clip_clause` now cuts on a clause/word boundary and always marks ` [...]`. Measured: Stage-2 user payload 122,828 → **135,778** chars, ellipses 2 → **0**, and **Annex IV now arrives complete at 5,720 chars** — where Annex IV(1)(e) lives |
| `REGENOLD_ANSWER_NO_CAP` | **ON** | removes sentence + char caps live (hard rule #2) |
| `REGENOLD_KG_CONTEXT` | **ON** | graph context into Stage-2 |
| `REGENOLD_KG_MAX_CHARS` | **48000** | total graph-context ceiling. R328.4 — was 16000 |
| `REGENOLD_KG_MAX_UNITS` | **70** | units per provision. R328.4 — was 24, which rendered Article 3 as 24 of its 68 definitions with 3(4)-3(8) (the five OPERATOR ROLE definitions) absent and unmarked |
| `REGENOLD_KG_UNIT_CHARS` | **2000** | per-unit budget; `_UNIT_HARD_CEILING` **9000** for enumerations. R328.4 — were 900 / 2600 |
| `REGENOLD_ANSWER_COVERAGE` | **ON** | delivers `USER_ANSWER_COVERAGE_CLAUSE` (2,241 chars) on the Stage-2 USER channel — delivered on every provider. ⚠ **`=0` is NOT a targeted rollback of anything inside it**: it also deletes the R318 `LEGAL VERSION` sentence, which is the ONLY place the no-Digital-Omnibus rule reaches the model. If you need to remove one sentence, remove that sentence |
| `REGENOLD_ONTOLOGY_RISK_DOCS` | **ON** | `938933a` — emits 28 virtual BM25 documents from the six AIRO registries (345 → **373** docs). Shipped default-ON with **no `dynamic_ab` verdict and no `gold_dropped` reading**; 9 of 110 official-batch rows lose a provision from their entity set. `=0` restores the pre-`938933a` corpus. In `_engine_cache_key` (`regenold.py:1434`) since R331/R332 |
| `REGENOLD_COHERE_RERANK` | **OFF** | R331/R340.1 — cross-encoder rerank via Cohere at the parse-level entity list (the placement that reaches live traffic; the pool-level placement only fires on the rare no-entity BM25 fallback) and the retrieval candidate pool. Needs `COHERE_API_KEY`; fresh env read per call. **Live A/B (R346, n=60, Bedrock): FIRED 49/60 rows, all axes UNDERPOWERED (wash inside noise), gold 17→17 (+0), latency +1.0 s.** ⚠ Trial key = 10 calls/min: unpaced every call 429s and the lever reads INERT — pass `--min-call-gap 6.5` |
| `REGENOLD_QUERY_EXPANSION` | **OFF** | R341 — multi-query expansion (RAG-Fusion) in `_deterministic_parse`: frontier-tier paraphrases scanned through the SAME high-precision keyword map (union capped at 3 new refs) plus the BM25 fallback RRF-combined across queries at the single-query budget. Skips explicit-anchor and multi-turn shapes; the fallback gate asks about the ORIGINAL lanes only (a lone paraphrase hit must not starve BM25). **Live A/B (R346, n=60, Bedrock, Haiku tier): FIRED 37/60, ref_loose +0.039 / kw_recall +0.029 (CIs mostly above zero), gold 17→14 (branch BETTER), latency flat — directionally positive, UNDERPOWERED at n=60; the R346.2 frontier-tier re-run is the open measurement** |
| `REGENOLD_QUERY_EXPANSION_MODEL` | `claude-sonnet-4-6` | R346.2 — the paraphrase tier. **No Haiku on the live path**: frontier 4.6 by default (the judge tier — a paraphrase is a light task), pin `claude-opus-4-6` for the generation tier. Fresh read per call; in `_engine_cache_key` |
| `REGENOLD_QUERY_EXPANSION_BEDROCK_TIMEOUT` | **8 s** | R346 — paraphrase read budget on the Bedrock transport (cold-start + frontier model). The wrapper's 2 s budget would fail every paraphrase and read as an inert lever (attempts>0, expanded=0, branch == baseline) |
| `REGENOLD_JUDGE_CONCISENESS_LENIENCY` | **OFF** | R331.1 — the POST-PROCESSING half of `bb793ca`'s conciseness loosening (`legal_v2.py:821`). ⚠ **Its PROMPT half is UNGATED** (`legal_v2.py:488-514`, the UNREQUESTED-TOPIC / REDUNDANT definitions), and that is where the axis is actually defined — so `answer_conciseness` already sits on a different, strictly more permissive ruler than every pre-`bb793ca` number, under the same canonical name. Violates R327's "change the formula, change its NAME" |
| `REGENOLD_JUDGE_FACTUAL_THRESHOLD` | **0.70** | `d7be457` — `legal_v2` factual-correctness pass floor (`legal_v2.py:607`). Was an implicit 1.0 ("every proposition addressed"); `=1.0` restores it. Same ruler-swap caution as the row above |
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
| `REGENOLD_KG_SEMANTIC_MAX_CHARS` | **80000** | R327 — total KG ceiling used ONLY when the semantic layers contribute. R328.4 — was 26000, sized at 5 refs; measured 98.1% full at 8 refs and 100% at 12, dropping whole sections |
| `REGENOLD_SEMANTIC_UNITS` / `_UNITS_PER_PROVISION` | **16** / 2 | R327 — focused sub-provision block size, and the per-provision cap. R328.4 — was 6, so a global `LIMIT 6` let at most 3 of 8 cited provisions receive a sub-provision, defeating the per-provision cap directly above it |
| `REGENOLD_KG_MAX_REFS` | **12** | R328.4 — was 8; scenarios carry a mean 9.88 gold refs. ⚠ Four call sites clamped it to 10, so a raised default read as 10 — a clamp below its own default silently coerces the default down |
| `REGENOLD_GROUNDING_MAX_REFS` / `_REF_CHARS` | **12** / **3000** | R328.4 — were 8 / 1200; the 9th cited provision got no verbatim text at all while the prompt demanded exact statutory terminology |
| `REGENOLD_JUDGE_MAX_TOKENS` | **1600** | R328.4 — ONE judge output budget for every transport. Was 400 hard-coded on wrapper/Anthropic, 800 Groq, 1000 Gemini, env-overridable on Bedrock alone; a truncated judge reply becomes `unbalanced_json`, which is non-retryable, and `pass_rate` divides by total rows — a SILENT ZERO |
| `REGENOLD_SEMANTIC_DEFINITIONS` / `_RECITALS` | 3 / 3 | R327 — per-layer quotas. They must be SEPARATE: recitals score ~0.70 vs definitions ~0.62, so a shared LIMIT returned **zero** definitions |
| `REGENOLD_KG_MAX_INFLIGHT` | 4 | R327 — graph worker slots. Was 2 with a NON-BLOCKING acquire, which hard-dropped every concurrent read past the second |
| `REGENOLD_MINIMAL_REF_BUDGET` | **OFF** | R327 — collapses every scenario budget to 5. This is the top-N clamp family; awaits `easyhard_ab` + `gold_dropped` |
| `REGENOLD_COMPONENT_D_CITABLE_ONLY` | **OFF** | R327 — Component D promotes only retrieval-grounded refs |
| `REGENOLD_CITABLE_BASE_GUARD` | ON | R327 — restricts prose-promotion to the retrieved citation universe (only ever REMOVES an ungrounded promotion) |
| `REGENOLD_SEMANTIC_COORDINATES` | **ON** | R329 P2 — the constrained sub-provision block renders the legal coordinate (`Article 12.2.a`) instead of the internal node label (`[paragraph para_12_1]`). LABEL only: the block stays non-citable, so hard rule #10 holds. Guards a real fabrication — `build_hierarchy_payload` synthesises a Paragraph `1` for single-block lettered provisions, so naive reconstruction emitted `Article 16.1.a`, which does not exist (3 of 658 nodes; those fall back head-level via `get_provision_text`, NOT the head-lax `provision_exists`). Off-switch `=0` |
| `REGENOLD_CITABLE_UNIVERSE_BLOCK` | **ON** | R329 P3a — emits an explicit `CITABLE PROVISIONS:` list and repoints the citation instruction at it. Fixes a scope statement that named a block also containing GDPR/MDR bridging, multi-hop synthesis, legal-AST output, three KG sections, verbatim text and recitals, each with its own "do NOT cite" clause. Sub-points of a listed provision stay permitted. Off-switch `=0` |
| `REGENOLD_REF_UNCERTAINTY` | **ON** | R329 P3b — one user-channel sentence on the UNCERTAINTY axis, which `USER_REF_MINIMALITY_CLAUSE` (ON since R298) does not state; it argues relevance. Pulls against system rule 10 ("Unmentioned citations are severely penalized") — read the reconcile drop rate in any arm that moves it. Off-switch `=0` |
| `GROUNDED_JUDGE_STRICT_GROUNDING` | **OFF** | R327 — ON makes answer-correctness unscorable on the July-7 batch (it has no gold at all). ⚠ **It governs `evals/judge/grounded.py` ONLY.** Since `d7be457` it is SILENTLY INERT on `evals/judge/legal_v2.py` — grep for the flag there returns **0 hits** — whose `_prepare` builds the evidence block from `gold_refs + pred_refs`, i.e. from `pred_refs` alone on a gold-free row, with no `[NOTE]`, no `answer_grounding_source` stamp and no off-switch. All 110 July-7 rows take that branch, so a `legal_v2` answer-correctness number there grades the answer against the answer's own citations. Open item #7 nominates `legal_v2` as the replacement judge — fix `_prepare` AND the `_judge_row` guard together, or the axis keeps running |
| `NEO4J_AUTO_SEED` | **OFF unless `1`** | R327 — now opt-IN, and even then only seeds a graph proven to have 0 nodes. Hard rule #12 |
| `BEDROCK_REGION` | **`eu-central-1`** | R328 — Bedrock source Region. Also reads `AWS_DEFAULT_REGION` / `AWS_REGION`. NOT `us-east-1`: an `eu.` profile is unresolvable there |
| `REGENOLD_BEDROCK_MODEL` | `eu.anthropic.claude-opus-4-8` | R328 — Stage-1 + Stage-2 main RAG tier. 403 on the 08-13 key vintage; the 08-15 re-mint invokes `opus-4-6-v1` (the live A/Bs pinned `claude-opus-4-6`). R328.2 degrades within the family. ABSK entitlement is fixed at key creation — see the expiry gotcha |
| `REGENOLD_BEDROCK_COMPLEX_MODEL` | `eu.anthropic.claude-opus-5` | R328 — the `complex_question` tier. 403 on the 08-13 key vintage; same family chain, re-mint restores the pin |
| `REGENOLD_BEDROCK_JUDGE_MODEL` | `eu.anthropic.claude-sonnet-5` | R328 — judge. Precedence: this env > the CLI `--model` flag > the default. 403 on the 08-13 key vintage; the 08-15 re-mint invokes `sonnet-4-6`, the tier used for judging |
| `REGENOLD_STAGE2_VERDICT_GUARD` | **ON** | Rejects a Stage-2 answer that stops mid-verdict, on BOTH the wrapper and (since 2026-08-13) the Bedrock path. `=0` disables. ⚠ Never measured on `ab_judge` — davidath cannot see it (Stage-2 only) |
| `REGENOLD_BEDROCK_MAX_TOKENS` | **4096** | R328.3 — the Stage-2 answer ceiling on Bedrock. NOT `settings.graph_rag.max_tokens` (1536), which is advisory on the wrapper and a HARD mid-word cut here. Worst measured enumerative answer used 3411 |
| `REGENOLD_BEDROCK_STAGE2_TIMEOUT_S` | **180** | R328.3 — per-call read budget for Stage-2. The 60 s default turned a bigger token ceiling into `ReadTimeoutError` (the worst case emits 3411 tokens in ~70 s) — the same truncation, one layer down |
| `REGENOLD_BEDROCK_JUDGE_MAX_TOKENS` | **1600** | R328 — NOT the wrapper's 400. Bedrock honours the system prompt, so the judge reasons in prose before its JSON; at 400 it truncates and the axis returns `no_json` — a SILENTLY UNSCORED axis, not a visible failure |
| `REGENOLD_BEDROCK_WRAPPER_FALLBACK` | **ON** | R330 — cross-PROVIDER last resort ported from the RAG repo: when the WHOLE Bedrock entitlement chain is spent, serve from the Claude-Max wrapper instead of dropping Stage-2. Placed at the END of `complete_with_fallback`, not inside `BedrockProvider.complete` as upstream has it — upstream's placement can hop on the FIRST model's throttle while an invocable tier sits further down the chain. ⚠ **The two providers were not interchangeable while the wrapper dropped the system prompt; since 2026-08-15 both deliver it** (subject to the 32,767 argv ceiling — see the gotchas), so re-measure before assuming a hop changes the delivered instruction. It returns `model="wrapper:<name>"`, which makes the existing `_bedrock_complete_for_graph_rag` provenance fire unchanged — `stage2_models` in the sidecar shows `wrapper:…`, never the pin. Alert on `served_by=wrapper:`. **R346.1 — a DEAD/EXPIRED key (`api_key_invalid_403`) fails fast and NEVER reaches this hop**: it is classified distinctly from entitlement, never cached per-model (a re-mint heals the next request), and the tunnel stays reserved for the operator's live runs. Off-switch `=0` |

⚠ **This table was BROKEN in the middle until 2026-08-15** — the R329 paragraph
below sat between two rows, so everything from `GROUNDED_JUDGE_STRICT_GROUNDING`
down rendered outside the table. It is moved here; no row changed.

⚠ **The three R329 flags were flipped to default-ON on 2026-08-13 by operator
decision and are UNGATED.** The reason they are code defaults rather than env
opt-ins is the standing `railway.toml [deploy.envs]` finding: an env-gated
default-OFF flag never reaches the deployment at all. Each keeps a `=0`
off-switch and remains a flag so `ab_judge` / `easyhard_ab` can still A/B it.
**Consequence: the "Current baseline" block above was measured with all three
OFF and no longer describes the default-configuration system.** Re-measure
before grading anything against it. This is the R327 shape (an ungated change
shipped ON) entered deliberately and with the risk recorded, not by accident.

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

⚠ **The deployed provider is NOT derivable from the repo, and it is NOT
STABLE.** Nothing checked in establishes it — the code default with no env var
is `openai_wrapper`; `railway.toml [deploy.envs]` has never applied and in any
case assigns `openai_wrapper`, with the string `bedrock` appearing nowhere in
it; `.env` is gitignored so the container ships no dotenv; `Procfile` /
`railpack.json` set only the uvicorn command. A Railway **service variable** set
from the dashboard/CLI is invisible here and overrides all of that.

**But it IS observable.** POST the live endpoint with `?include_reasoning=true`
and read the `stage2_model=` note — one probe, and it is the standing method.
Run on 2026-08-15 it gave three different answers on the same URL: an early
probe served `eu.anthropic.claude-opus-4-6-v1` with a `bedrock_fallback` note
(bedrock, on the R328.2 degraded tier, failing over every request); a later one
`claude-opus-5 complex=True` with `groq_auto_fallback_success` and **no**
`bedrock_fallback` note (NOT bedrock — that note shape is the wrapper/Anthropic
branch at `_graph_rag_impl.py:780`; a Bedrock answer always carries the full
`eu.anthropic.…` profile id); and after the R339/R340 fixes, **`stage2_polish:
True`, `stage2_model=claude-opus-5 complex=True`, no fallback note** — the
primary healthy. The honest statement is neither "production is on Bedrock" nor
"on the wrapper": **the deployed provider is a live service variable that can
change without a commit, so it must be RE-MEASURED, not remembered.** Everything
downstream (which model answered, is the entitlement chain firing, is the system
slot delivered) inherits that same expiry date.

`railway variables` against service `0086ff18-f642-46c8-8127-57c913ca1c53` is
the other instrument, and the only one that shows the variable itself rather
than its effect.

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
refs and is `stage2_landed`-gated so davidath cannot see it); and the judge
prompt caps (`_GOLD_TEXT_CAP` 12000, `_PRED_TEXT_CAP` 6000, `_MAX_PRED_REFS` 8)
which make `legal_v2`'s quote-or-retract gate *invert* — an unquotable provision
downgrades WRONG to SUPPORTING, so truncation inflates the pass rate. (This
list's judge `max_tokens=400` and `REGENOLD_KG_MAX_UNITS=24` items were fixed by
R328.4 — see the flag table.)

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

py -3.12 -m pytest tests/ -q -p no:cacheprovider          # full suite (~0 failures since R340)

# THE MERGE GATE — fire-checked, adaptively sized, gold_dropped veto.
py -3.12 -m evals.harness.dynamic_ab --flag <FLAG> --label <L>
py -3.12 -m evals.harness.dynamic_ab --branch-env <K>=<V> --label <L>

py -3.12 -m evals.regenold.runner                         # 276 scenarios
py -3.12 -m evals.regenold.runner_v2 --local --probe-oos --oos-suite all --label X
py -3.12 scripts/check_legal_version_drift.py             # exit 0 = no legal drift
py -3.12 -m evals.harness.ab_judge                        # pairwise LLM judgement
```

⚠ `evals.bench.runner` (davidath 476) is **RETIRED** — see Validation policy. It
is `provider=cli`, so it cannot observe Stage-2, prompts, the judge or the
reranker, and a green run on such a change is the instrument trap, not a pass.

⚠ `evals.bench.run_cappelli_bench` and `evals.bench.run_live_deep_eval` are the
same trap wearing a different name — both defaulted to `provider=cli` until R338
and both ran inert (14.5-440 ms/row, 91.8 ms/row) while printing full
scorecards. They now default to `openai_wrapper` and record
`stage2_landed_rate` + `stage2_models` in their artefacts. **Read those two
fields first; a scorecard without them is unattributable.** Neither is a merge
gate. `run_live_deep_eval` is also **not** the hard turn: its
`HARD_JULY7_SCENARIOS` is ten hand-authored SINGLE-turn rows with self-written
gold, not the adversarial pushback of `run_official_batch --mode hard` (open
item #2, still never run).

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

Enforcement is on the **user** channel — historically because the system slot was
dropped; it stays there because that channel is delivered on every provider.

**Kept by operator decision:** the Commission GPAI Guidelines content (10^23
threshold, one-third fine-tune rule). It is 18 July 2025 soft law, correctly
attributed, not Omnibus — and `tests/test_kb_stubs_filled.py` pins it.

## Open, ranked

Full handoff: [`.planning/NEXT-SESSION.md`](.planning/NEXT-SESSION.md).

1. **Resolve the query-expansion A/B on the frontier paraphrase tier** (R346.2
   made the lever Haiku-free; the confirmatory live run was interrupted).
   Directionally positive on the Haiku tier (ref_loose +0.039, kw_recall
   +0.029, gold 17→14, flat latency) but UNDERPOWERED at n=60 — run the full
   probe (`--max-rows 137`) or the moved-row subset to converge the CI. The
   gold veto is the gate.
2. **Ground the R346 sidecars with `evals.judge.grounded`** (`claude-sonnet-4-6`
   via Bedrock — the frontier judge the operator specified) so the retrieval
   levers get a quality verdict beyond the heuristic axes. Verify
   sidecar-format compatibility with `grounded.py` first.
3. **Run `--mode hard`.** It is **the graded turn** (the adversarial pushback;
   67 of 111 hard rows carry it) and it has NEVER been run. Every optimisation
   decision on the table is being made on the *easy* turn — that is the
   instrument trap. Free, ~40-70 min.
4. **Record the PRIMARY provider's failure in the reasoning trace.** Only the
   fallback's outcome is written today (`groq_auto_fallback_success` /
   `groq_fallback_failed`), so a reader sees Groq succeeding and cannot tell
   Claude was never reached — that is what turned R339's total Stage-2 outage
   into a multi-hour diagnosis. One `record_note` in the `groq_auto_fallback`
   branch (`_graph_rag_impl.py` ~:880). Highest-value single change outstanding.
5. **Gate the parent-collapse** with `easyhard_ab` (davidath cannot see it).
   +0.018 F1 / +5 rows offline; one gold ref is the price. R339's judge adds
   independent evidence on sub-point-carrying gold: q12 fails reference
   correctness for citing a parent alongside its own sub-provision.
6. **Attack GENERATION, not selection.** R325 closed the ranker, so the
   remaining ~90% of the over-citation gap is upstream: why does a 3-ref answer
   name a wrong provision **53% of the time at rank 3**? The refs-per-row cliff
   is the shape of it — 1 ref → 0.88 pass, 2 → 0.54, **3 → 0.05**, 4+ → 0.06,
   with 41 of 100 rows sitting at exactly 3 (the QA budget). R327's constrained
   sub-provision layer is the first instrument aimed here.
7. **`CROSS_REFERENCES` backlinks as non-citable context** — 248 edges, never
   read as context, real legal signal. The best unshipped graph idea; needs its
   own gate, and prompt budget competes with Answer-Conciseness.
8. **Fix the judge** before trusting any further answer number — the length
   artefact above. `evals/judge/legal_v2.py` already implements the
   quote-or-retract rule that catches it. ⚠ It also carries three defects of its
   own, all from the unreviewed commits and all still open: the
   `GROUNDED_JUDGE_STRICT_GROUNDING` bypass (fix `_prepare` AND the `_judge_row`
   guard together — fixing one leaves the axis running), the head-lax
   `provision_exists` ghost-citation gate at `:660`, and the ungated conciseness
   prompt loosening at `:488-514`. **Fix these before nominating it.**
9. **Watch conciseness** — answers are **+41% longer** than the graded July-7
   ones, on the one axis the official scorecard says we lead. Any bound must be
   SENTENCE-only (hard rule #2).
10. **Run the owed gate on `REGENOLD_ONTOLOGY_RISK_DOCS`** — *ranks with #3*.
    `py -3.12 -m evals.harness.dynamic_ab --branch-env REGENOLD_ONTOLOGY_RISK_DOCS=0`
    against a **gold-carrying** set (July-7 has `gold_coverage=0.0`, so hard rule
    #8 cannot be read off it). This is a default-ON, live-shipping retrieval
    change with 9/110 measured context regressions and no verdict at all. R338
    fixed the dense-index singleton that would otherwise have corrupted this
    exact A/B, so the instrument is ready. **Do not just flip the default OFF** —
    that is an equally unmeasured change in the other direction and it de-aligns
    the committed TurboQuant assets, which were rebuilt for the 373-doc corpus.
11. **`ab_judge`'s new swap-consistency metric counts judge ERRORS as
    agreement** — `_judge_one` collapses every transport/parse failure into the
    same `"tie"` a real tie uses, so each errored pair simultaneously pushes
    `swap_consistency_rate` toward 1.0 and `effective_win_rate_b` toward 0.5:
    the reliability score RISES as the instrument breaks. Reachable today with
    `--judge-provider bedrock` and no AWS credential. Give it an error channel
    before reading either number.

**Closed — do not re-open:** R326 review finding I1 (`_ENUM_OPENER_RE`) is a
non-finding (enumerated units begin at `(a)`; verified 5(1)/10(2)/13(3) match,
26(1) is 228 chars so nothing truncates). I2-I5 are done. `_DEONTIC_CYPHER` parses
fine on Aura. The judge's parent-text fallback must stay removed.

---

**History:** [`docs/ROUNDS.md`](docs/ROUNDS.md) — every round entry, verbatim.
**Handoff:** [`.planning/NEXT-SESSION.md`](.planning/NEXT-SESSION.md).
