# Deep Code Review: six unreviewed "Gemini" commits pushed direct to `main`

**Date:** 2026-08-15
**Branch:** `main` (no PR, no review on any of the six commits)
**Commits reviewed:** `3af98af`, `938933a`, `d7be457`, `bb793ca`, `ee61cfd`, `cc47f8b`
**Tree verified against:** `4d72ff3` (HEAD at review time)
**Files changed:** 25 | **Lines changed:** +3,341 / -110
**Diff size category:** Large

---

## Executive Summary

Three defects are Critical and two of them ship to users. `cc47f8b` inserted two topic-specific
paragraphs into `USER_ANSWER_COVERAGE_CLAUSE` — the **Stage-2 USER message**, the one channel the
Claude-Max wrapper does *not* drop — that (a) instruct the model to cite **EU Charter article
numbers** inside AI Act answers, which Component D then promotes onto the wire as AI Act citations,
and (b) dictate an eight-item "Annex IV" component list that is **not Annex IV** (CE marking is
Article 48; three real Annex IV points are missing). Both are code defaults with no env gate, no
`dynamic_ab` run, and no live probe, and a merge to `main` in this repo ships to a real Railway
service. The third Critical is in the new eval harness: `evaluate_mistake_resolution` honours 2 of
the 5 constraint kinds in `ANTIFRAGILE_GT`, so **11 of 38 expert-flagged mistakes score RESOLVED for
every possible answer** — and the inflated 0.7895 is already committed to
`evals/bench/results/live_deep_eval_results.json`.

Beneath that sits a dense cluster of the repo's own signature defect class. The new Cappelli
threshold curve derives its ground-truth labels from the score it thresholds, so precision is
1.0000 by construction. Both new "live"/"deep" benchmark runners default to `--provider cli`, the
no-Stage-2 path CLAUDE.md just retired davidath for — and one of them is the instrument shipped to
justify the Stage-2 prompt edit in the same commit, whose gold keywords are copied verbatim from
that prompt. A char-trigram cosine is registered and printed as "Sentence-BERT". `ab_judge`'s new
swap-consistency metric counts judge *errors* as judge *agreement*. `938933a` silently re-ranked the
whole BM25 corpus (345 → 373 docs) with no gate run, and the one documented rollback A/B for it is
corrupted by a stale dense-index singleton. Confidence in the findings is high: every Critical and
Important item below survived an adversarial refutation pass, and most were reproduced by execution
against the current tree.

**Verdict: not safe to ship as-is.** See the FIX PLAN at the end.

---

## Critical Issues

### [C1] Live user-channel prompt orders the model to cite EU Charter articles; Component D promotes them onto the wire as AI Act citations

- **File:** `app/data/graph_rag_prompts.py:902-903` (leak path `app/routes/regenold.py:4306`, `:9419-9472`)
- **Bug:** `cc47f8b` appended to `USER_ANSWER_COVERAGE_CLAUSE`:
  *"When answering about Fundamental Rights Impact Assessment (Article 27), name the assessed rights
  and deployer mitigations under the relevant Charter articles."*
  The constant is appended to the Stage-2 **user** message at `app/engines/_graph_rag_impl.py:7827`
  under `answer_coverage_enabled()`, which defaults to `"1"` — so it is delivered on 100% of live
  requests on **every** provider, wrapper included. Article 27 contains no Charter reference at all
  (`'charter' in get_provision_text("Article 27").lower()` is `False`), so the instruction directs
  the model at a foreign instrument from parametric memory.
  The foreign-instrument guard in `_prose_citation_bases` is **adjacency-anchored** —
  `_CROSS_INSTRUMENT_RE` / `_FOREIGN_INSTRUMENT_AHEAD_RE` / `_BEHIND` only suppress a number sitting
  next to the token "Charter" — so in an *enumeration* of Charter articles only the adjacent member
  is suppressed. Charter article numbers 1-54 all resolve in `ARTICLE_EXISTENCE`, so the lint floor
  is blind by construction (hard rule #5's documented collision), and Component D's scoping guard
  `REGENOLD_COMPONENT_D_CITABLE_ONLY` is **default OFF**, so the `continue` at `regenold.py:9465`
  never fires and control reaches `references.append(cite)` at `:9472`.
  `_reconcile_references_to_prose` then *protects* them, because the prose names them.
- **Failure scenario (executed against the current tree):**
  ```
  >>> from app.routes.regenold import _prose_citation_bases
  >>> _prose_citation_bases("The FRIA must assess impacts on Charter rights: human dignity "
  ...   "(Article 1), non-discrimination (Article 21) and effective remedy (Article 47).")
  ['Article 1', 'Article 21', 'Article 47']
  >>> _prose_citation_bases("Relevant Charter articles include Article 21 (non-discrimination) "
  ...   "and Article 8 (data protection).")
  ['Article 21', 'Article 8']
  ```
  4 of 5 plausible renderings leak. A user asking *"Does our recruitment AI need a fundamental
  rights impact assessment?"* receives `references = [Article 27, Article 1, Article 21, Article 47]`
  — where AI Act Article 21 is *Cooperation with competent authorities*, Article 1 is *Subject
  matter* and Article 47 is the *EU declaration of conformity*. Wire-legal, and wrong.
  The guard also fails in the **opposite** direction on the same sentence:
  `_prose_citation_bases("Under Article 27 the deployer assesses rights under Articles 21, 8 and 47 "
  "of the Charter.")` returns `[]` — the genuine Article 27 is suppressed because "of the Charter"
  lands in its ahead-window. That is a hard-rule-#8 gold drop of the very provision the question is about.
- **Impact:** Wrong citations on a default-ON live path, on **Ref Strict / Ref Conciseness** —
  the two axes CLAUDE.md names as the entire remaining competitive gap. `938933a` independently
  seeded the literal strings `"Charter Art. 21"`, `"Charter Art. 34"`, `"Charter Art. 47"` into the
  BM25 corpus (`app/data/ontology.py:667/721/757/791` + `app/data/kb_search.py:367`), supplying the
  model the exact numbers.
- **Suggested fix:** Delete the Charter sentence. If Charter context is wanted, forbid numbers
  explicitly: *"name the affected rights in words — human dignity, non-discrimination, privacy,
  effective remedy — and never cite a Charter article number."* Independently, make a
  Charter/GDPR/MDR marker **anywhere in the enclosing clause** suppress every bare `Article N` in
  that clause, and prove the fix FIRES on **both** prose→citation paths (hard rule #11) — do not
  accept a byte-identical A/B as evidence; that is what inert looks like here.
- **Confidence:** High (88-92). Guard hole and instruction proven by execution; the model's actual
  emission *rate* is unmeasured — the fix is a one-sentence deletion with no measurable cost.
- **Found by:** logic-runtime, instrument (agreed)

---

### [C2] The injected "Annex IV" component list is not Annex IV — CE marking is Article 48, and the accurate rule sits on the dead system channel

- **File:** `app/data/graph_rag_prompts.py:898-901` (delivery `app/engines/_graph_rag_impl.py:7822-7827`)
- **Bug:** The same insertion adds:
  *"When answering about technical documentation (Article 11 / Annex IV), name the required
  components in one compact list (technical file, risk management file, data governance records,
  human oversight protocol, logging mechanism, post-market monitoring plan, declaration of
  conformity, CE marking)."*
  Verified against the repo's own pin — `get_provision_text("Annex IV")` returns 5,710 chars across
  **nine** numbered points:
  - `'ce mark' in text.lower()` → **False**. CE marking is **Article 48**, an affixing obligation.
    Annex IV(8) requires only *"a copy of the EU declaration of conformity referred to in Article 47"*.
  - `'technical file'`, `'data governance'`, `'logging'` → all **False** as Annex IV item names.
  - The list **omits** points 4 (appropriateness of the performance metrics), 6 (relevant changes
    through the lifecycle) and 7 (list of harmonised standards applied), and omits **point 1
    entirely** — whose sub-item **1(e) is "the description of the hardware on which the AI system is
    intended to run"**, the exact element graded question `rg_001` turns on
    (`evals/regenold/_official_batch_20260707.json` row 0; recorded refs
    `["Article 11","Annex IV.1.e","Annex IV.2.c","Annex IV","Annex IV.2"]`).
  - The paraphrases contradict rule 12 CANONICAL TERMINOLOGY (`graph_rag_prompts.py:80`) and the
    clause's own *"Assert only what the supplied text states"* four lines above.
- **The channel inversion (this is the sharp part):** the **correct** rule already exists at
  `app/data/graph_rag_prompts.py:118` — *"in particular Annex IV(1)(e) (the description of the
  hardware…) and Annex IV(2)(c) (the computational resources…)"* — but it lives inside
  `ANSWER_GENERATE_SYSTEM`, which the file's own comment (`:842`) records as reaching the model on
  **ZERO** live wrapper requests. So `cc47f8b` put the fabricated list on the live channel and left
  the accurate rule on the dead one. On Bedrock the model receives **both**, and they contradict.
- **Failure scenario:** POST the PDF example question *"Does the technical documentation of a
  high-risk AI system require specifications regarding the required hardware?"* on the default
  (wrapper) path. The system rule at `:118` is dropped. The surviving user clause makes Stage-2 emit
  the eight-item checklist ending in "CE marking", never states Annex IV(1)(e), and asserts an
  Article 48 obligation as a technical-documentation component. The answer is wrong on content *and*
  misses the sub-point citation the system rule was written to produce.
- **Impact:** A false statement of EU law delivered to compliance users on a deployed service (hard
  rule #4), on one of the three PDF example questions (hard rule #3's anti-overfit rationale), with
  an eight-item enumeration inflating **Answer-Conciseness** — the only axis the official scorecard
  says we lead, zero headroom (hard rule #2's rationale). It shipped with no dedicated flag
  (`REGENOLD_ANSWER_COVERAGE=0` is not a targeted rollback: it also deletes the R318 no-Omnibus
  LEGAL VERSION sentence from the same constant), no A/B and no live probe.
- **Suggested fix:** Delete lines 898-903 (both sentences — C1 and C2 are the same hunk). The
  topic-neutral rule already present at `:885-889` ("where the question's subject IS an enumerated
  statutory set, name every member **the supplied text states**") covers the intent and stays
  grounded. If a technical-documentation nudge is still wanted, move the accurate `:118` rule onto
  the user channel, gate it, and run `dynamic_ab` with a live `rg_001` probe.
- **Confidence:** High (85-92). Legal claim verified programmatically against the pin, not from
  memory. One dissenting verifier rated this Important on the narrower ground that the *benchmark
  contamination* half is currently inert (see [I7]); all others rated it Critical on the delivered
  wrong-law ground, which is what the severity here reflects.
- **Found by:** logic-runtime, contract, legal, hardrules, engmgr (5 lenses agreed)

---

### [C3] `evaluate_mistake_resolution` ignores 3 of 5 constraint kinds — 11 of 38 expert-flagged mistakes are RESOLVED for any answer, and the inflated number is already committed

- **File:** `evals/bench/run_live_deep_eval.py:128-157` (call site `:208`, aggregate `:301`)
- **Bug:** `cc47f8b` reimplements mistake verification from scratch, reading only `verify.present`
  and `verify.absent`. `ANTIFRAGILE_GT` records carry three more kinds that the canonical resolver
  `evals/regenold/antifragile_live.py:146 _mistake_resolved` honours: `verify.present_any`,
  `mistake['ref_present']` and `mistake['ref_absent']`. The new function **does not accept
  `pred_refs` at all**, so the reference constraints are structurally unevaluable — and `pred_refs`
  is in scope at the call site (bound `:207`, used `:199-201`) and simply not passed. When both
  `present` and `absent` are empty, lines 140-141 (`... if present_needed else True`) make `is_fixed`
  unconditionally `True`.
- **Failure scenario (executed):** Feeding the **empty string** as the predicted answer over all 20
  GT rows returns `resolved=14/38`, `mistake_resolution_rate=0.3684`. The structurally
  unfalsifiable set — RESOLVED for *every possible* answer — is **11 of 38 (28.9%)**: `q02_m3`,
  `q03_m3`, `q04_m2`, `q06_m1`, `q07_m2`, `q10_m1`, `q10_m2`, `q13_m1`, `q14_m2`, `q15_m1`, `q18_m3`.
  Handed the string *"This system is governed by Annex II and Article 27, and also Article 5 and
  Annex III apply."*, `q02_m3` (`ref_absent=['Annex II','Article 27']`) and `q14_m2`
  (`ref_absent=['Article 5','Annex III']`) both return `fixed=True` — the metric certifies the
  mistake as resolved while the mistake is being made in the text it was handed.
- **Impact:** The headline metric of the "Live Deep Evaluation" reports that expert-flagged
  regressions were fixed when they were never tested. **The inflated number is already on disk**:
  `evals/bench/results/live_deep_eval_results.json:14` records `"mistake_resolution_rate": 0.7895`
  (30/38), at least 11 of which are constants. `docs/PROPOSAL_GENAI_EU_AI_ACT_COMPLIANCE_EVAL.md`
  landed in the same commit. This also re-introduces, in a parallel copy, the exact defect class
  R333 fixed in the canonical resolver — minus its head-normalised ref matching.
- **Suggested fix:** Delete `evaluate_mistake_resolution` and call
  `evals.regenold.antifragile_live._mistake_resolved(answer_low, pred_refs, mistake)`, threading the
  wire `references` list from `:207`. If a local copy is kept it must **fail closed** — a mistake
  with zero evaluable constraints must not count as resolved. Regenerate or delete
  `live_deep_eval_results.json`; 0.7895 is currently a false record.
- **Confidence:** High (95). Reproduced by execution; the always-true set enumerated row by row.
- **Found by:** errors

---

## Important Issues

### [I1] `938933a` silently re-ranked the whole BM25 corpus (345 → 373 docs); 9 of 110 official-batch questions lose a previously-retrieved provision, with no gate run

- **File:** `app/data/kb_search.py:355-450` (flag default `:233`; gate note `:328-350`)
- **Bug:** Six new loops emit 28 virtual BM25 documents from `RISK_SCENARIO_REGISTRY`,
  `RISK_CONTROL_REGISTRY`, `GPAI_REGISTRY`, `CONFORMITY_ROUTE_REGISTRY`, `FRIA_REGISTRY` and
  `SERIOUS_INCIDENT_REGISTRY`. Each is anchored on the **first element of an arbitrarily-ordered
  citation tuple** (`scenario.statutory_violation[0]`, `control.articles[0]`,
  `fria.governing_articles[0]`) and several duplicate their keyword tuple for 2× term weight. This
  is not additive: `n_docs` 345→373 and `avg_doc_len` 94.5→91.7 change IDF and length normalisation
  for **every** pre-existing document, so the whole corpus re-ranks.
- **Failure scenario (measured in-process, `_build_index_cached.cache_clear()` between arms):**
  `_index_stats()` = `{'total': 345, 'kb': 131, 'ontology': 20}` OFF vs
  `{'total': 373, 'kb': 131, 'ontology': 48}` ON. Over the 110 rows of
  `evals/regenold/_official_batch_20260707.json`, `_deterministic_parse` changes its entity set on
  **9 rows and all 9 LOSE a provision**:
  - *"…can an AI system intended to be used as a toy qualify as high-risk?"* loses **Annex III**
  - *"…which specific AI systems are explicitly listed as high-risk…"* loses **Art. 6 and Art. 7**
    (the classification articles)
  - the QMS question loses **Art. 11** and the Annex IV xref
  `kb-transparency-Art. 27` is **gained on 5 rows**, because the FRIA document dumps all six generic
  `required_steps` ("high-risk AI use", "natural persons", "vulnerable groups", "risk of harm",
  "human oversight", "mitigation measures") plus 2× keywords into a single Art. 27 anchor, so Art. 27
  now fires on any high-risk question.
- **Impact:** Bounded but real: an end-to-end run of all 110 rows through `ask_compliance_question`
  in both arms produced **byte-identical reference lists on 110/110** on the deterministic path, so
  no citation change is demonstrated there. The blast radius is the **Stage-2 grounding context** —
  9 rows now hand the model a worse context, and on the live path references are a function of the
  answer. `REGENOLD_ONTOLOGY_RISK_DOCS` was retro-fitted by the later reviewed R331/R332 and is
  keyed into `_engine_cache_key` (`app/routes/regenold.py:1434`), with an in-tree note stating it is
  **"STILL UNMEASURED"**. That is the residual defect: a default-ON, live-shipping retrieval change
  with no fire-checked `dynamic_ab` verdict and no `gold_dropped` reading.
- **Suggested fix:** **Run the gate** —
  `py -3.12 -m evals.harness.dynamic_ab --branch-env REGENOLD_ONTOLOGY_RISK_DOCS=0` — against a
  gold-carrying set (July-7 has `gold_coverage=0.0`, so hard rule #8 cannot be read off it). Fix the
  two authoring defects regardless of the verdict: stop keying documents on `tuple[0]` (add an
  explicit `primary_anchor` field), and drop the generic `required_steps` prose plus the 2× keyword
  weighting from the FRIA document. **Do not simply flip the default OFF** — that is an equally
  unmeasured change in the other direction and it de-aligns the committed TurboQuant assets, which
  were rebuilt for the 373-doc corpus (see [I2]).
- **Confidence:** High (90)
- **Found by:** logic-runtime

---

### [I2] The dense index is a process singleton holding raw BM25 positions — flipping `REGENOLD_ONTOLOGY_RISK_DOCS` in-process silently relabels dense hits, so the documented A/B for [I1] measures a system that does not exist

- **File:** `app/engines/turboquant_index.py:492` (singleton), `:523-531` (the stale join), `:243-256` (guard that runs once)
- **Bug:** `_INDEX = _DenseIndex()` is a module singleton with a `_loaded` latch; its
  `_bm25_idx_map` stores **raw positions** into whatever corpus existed at first build. `dense_top_k`
  reads a **live, gate-resolved** `bm25 = _build_index()` at `:523` but a **frozen** `idx_map` at
  `:524`, and dereferences `bm25.article_refs[orig_idx]` at `:531` with a bounds check only against
  `len(idx_map)`. Because `_build_ontology_docs` is emitted in the **middle** of the corpus
  (`kb_search.py:520`: kb → ontology → corpus → definitions), the gate shifts every later document
  by 28. The build-time staleness guard exists for exactly this hazard but runs once per process.
- **Failure scenario (reproduced):** one process, `REGENOLD_ONTOLOGY_RISK_DOCS=1`:
  ```
  dense_top_k('serious incident reporting deadline', k=5)
  -> [('Art. 73',0.8224), ('Art. 17',0.3746), ('Art. 76',0.3703), ('Art. 87',0.3359), ('Art. 53',0.2162)]
  os.environ['REGENOLD_ONTOLOGY_RISK_DOCS'] = '0'   # what dynamic_ab --branch-env does
  -> [('Art. 111',0.8224), ('Art. 11',0.8123), ('Art. 110',0.7656), ('Art. 73',0.7358), ('Art. 99',0.5380)]
  ```
  Identical scores, different labels: Article 111 (Union safeguard / transitional) is now the top hit
  for a serious-incident question. `Annex XII` and `Annex V` appear in neither real configuration. No
  `IndexError`, no log line. `evals/harness/dynamic_ab.py:293-336` mutates `os.environ` in-process,
  runs the **baseline arm first** every batch, and nothing anywhere resets `_INDEX`.
- **Impact:** The one A/B CLAUDE.md prescribes for this flag (`--branch-env
  REGENOLD_ONTOLOGY_RISK_DOCS=0`, the literal example command) does **not** compare ON against OFF;
  it compares ON against a third, index-shifted system. Because the flag *is* in `_engine_cache_key`,
  the arms genuinely diverge and the **fire check passes**, so `dynamic_ab` prints a confident axis
  table for a configuration that does not exist. Measured on the real 132-row `probe_set`,
  `top_articles_by_relevance` differs from fresh-process ground truth on **2 of 132 rows** — small,
  because `additive_dense_fill` only fills slots BM25 left empty, but it is exactly the rollback A/B
  that [I1] needs. Production is unaffected (env is fixed per process); a gate-OFF cold boot trips
  the build-time guard correctly and rebuilds, at the cost of a full in-process SVD build.
- **Suggested fix:** Key the `_DenseIndex` build on corpus identity — store the resolved gate plus
  `len(bm25.article_refs)` (or a hash) on the instance and rebuild on mismatch, or hold `_INDEX` in a
  small dict keyed on that identity, mirroring `kb_search._build_index_cached(maxsize=2)`. At
  minimum, re-verify the identity at the top of `dense_top_k` and return `[]` on mismatch so the
  failure is loud and empty rather than silently mislabelled. Separately, ship or select a gate-OFF
  precomputed asset so the rollback path is not a cold SVD build.
- **Confidence:** High (78-95)
- **Found by:** logic-runtime, state (agreed — state lens found the relabelling, logic-runtime found the asset staleness)

---

### [I3] `legal_v2` answer-correctness grounds on the answer's own citations, defeating `GROUNDED_JUDGE_STRICT_GROUNDING` and dropping the circularity label

- **File:** `evals/judge/legal_v2.py:520-527` (`_prepare`), `:1010-1015` (`_judge_row` guard)
- **Bug:** `d7be457` rewrote the `answer_correctness` branch. When a row has no independent
  grounding it builds the evidence block from `gold_refs + pred_refs` via `_resolve_provision_texts`
  — and since the `if` above proves `gold_refs` is empty, that resolves **`pred_refs` only**. The
  same commit widened the unscorable guard with `or bool(r.get("pred_refs"))`. Neither consults
  `_strict_independent_grounding_required()` (grep: **0 hits** in `legal_v2.py`).
  The canonical helper `grounded._answer_grounding_block` (`evals/judge/grounded.py:145-159`) does
  the identical fallback but ships three guards `legal_v2` now lacks: (a) an in-prompt
  `[NOTE] The provisions below were selected by the answer's OWN citations`; (b) a per-row
  `answer_grounding_source = "predicted_refs_fallback_circular"` stamp (`grounded.py:176-187, 435`);
  (c) the `GROUNDED_JUDGE_STRICT_GROUNDING` off-switch (`grounded.py:391`). `grounded.py:388-391`
  gets the unscorable guard right; `legal_v2` does not — so **fixing `_prepare` alone leaves the axis
  running**.
- **Failure scenario (executed with `GROUNDED_JUDGE_STRICT_GROUNDING=1`):**
  row `{answer: "Article 5(1)(f) prohibits emotion recognition in the workplace.",
  pred_refs: ["Article 5.1.f"], gold_refs: [], gold_answer: ""}`.
  `grounded._answer_grounding_block(r)` correctly returns `''` and `_answer_grounding_source` returns
  `'none'` — but `legal_v2._prepare` returns `union_map = {'Article 5.1.f': <313 chars of real text>}`,
  the prompt contains **no `[NOTE]`**, and it is rendered under the header *"VERBATIM EU AI ACT TEXT
  (the provisions relevant to this question)"* with STEP 2 instructing *"using ONLY the verbatim text
  above"*. `_judge_row` returns `verdict='pass'`, `factual_score=1.0`, and the row dict carries **no**
  `answer_grounding_source`. STEP 3's omission check is neutered the same way: an omission is only
  findable if the answer already cited the provision that establishes it.
- **Impact:** The documented integrity flag is silently inert on this judge, and nothing in
  `legalv2-<label>.json` distinguishes a self-grounded row from an independently-grounded one, so a
  mixed run cannot be audited after the fact. All 110 rows of
  `evals/regenold/_official_batch_20260707.json` carry zero gold, so **every** row of that batch takes
  this branch. Worse for provenance: R331 (`e66577d`, a *reviewed* commit) landed **after** `d7be457`
  and removed the truthy `"  (none)"` sentinel from `grounded._answer_grounding_block` for the express
  purpose of reviving this guard — the `or bool(r.get("pred_refs"))` clause silently cancels that repair
  for every row carrying predicted refs. Bounded to Important because `legal_v2` is a standalone CLI,
  not the merge gate, and CLAUDE.md's July-7 figures come from `grounded.py`, whose default already
  performs this fallback *by documented, labelled design*.
- **Suggested fix:** In `_prepare`, use `gold_map = {"answer_context": _answer_grounding_block(r)}`
  unconditionally and treat an empty block as unscorable; revert `or bool(r.get("pred_refs"))` in
  `_judge_row` to `grounded.py:388-391`'s form; and emit `answer_grounding_source` on every
  `legal_v2` answer-correctness verdict so a prediction-derived run can never be aggregated with an
  independently-grounded one.
- **Confidence:** High (85-95)
- **Found by:** logic-judge, errors, contract, hardrules (4 lenses agreed)

---

### [I4] The new NON_EXISTENT_PROVISION gate uses head-lax `provision_exists`, so it fires on nothing real — and the fabricated leaf it misses is scored SUPPORTING

- **File:** `evals/judge/legal_v2.py:657-663`
- **Bug:** `3af98af` added `if not provision_exists(ref): wrong.append(ref); continue`. CLAUDE.md
  hard rule #5 states in as many words that `provision_exists` is **head-level LAX** and only
  `get_provision_text(...) is not None` validates a leaf. `app/data/provision_text.py:384-392`
  confirms: it tests `f"Art. {n}"` / `f"Annex {roman}"` and **discards the sub-point tail**.
  So the gate can only reject a fabricated *head* — precisely the class the wire already blocks at
  `app/routes/regenold.py:2687/3312/3319/4440/9439` and `_graph_rag_impl.py:7292/7300`.
- **Failure scenario (measured across every recorded result artifact — 24 sidecars, 2,244-24,370
  predicted refs depending on the scan):** the gate's condition is `False` on **zero** refs. It has
  never fired. Meanwhile refs that pass it while `get_provision_text` returns `None` are real and in
  the repo's own output: **`Article 3.14a`** appears as `rows[4].references[0]` in
  `evals/bench/results/omnibus-probe-r318-guard-ON.json` — a Digital-Omnibus definition the legal pin
  forbids — plus `Annex III.4.employment`, `Article 4.2` (×11), `Annex IX.99`, `Article 47.z.99`,
  `Annex IV.99`. Each is then stored in `pred_map` as `""`, rendered to the judge as
  `[Article 3.14a] (no verbatim text resolved — likely not a real provision)`, and because
  `_quote_substantiated(quote, "")` is `False` by construction, the judge's *correct* `WRONG` verdict
  is overturned at `:666-671` into `supporting`. Executed:
  `verdict='pass'`, `wrong_refs=[]`, `supporting_refs=['Article 3.14a']`,
  `legal_soundness_precision=1.0`. The other branches (`GOVERNING`, unclassified) route it to
  `governing`/`supporting` too — the ghost is scored sound on **every** path.
  `tests/test_judge_adversarial_remedies.py:50` pins the gate with `"Article 999"`, the one shape
  that measurably cannot reach a sidecar.
- **Impact:** A guard that reads as protection and provides none, on the axis CLAUDE.md names as the
  whole remaining gap. Note the quote-or-retract inversion itself is **pre-existing (R305)**, not
  introduced here — `3af98af` attempted to close it and used the wrong validator.
- **Suggested fix:** `if get_provision_text(ref) is None:` (hoist the import out of the loop).
  **Do not** use `pred_map.get(ref)` emptiness as the test — `pred_map` is truncated to
  `_MAX_PRED_REFS = 8` while the loop walks every ref, so scenario rows carrying a mean 9.88 refs
  would have legitimate 9th+ refs branded `NON_EXISTENT_PROVISION`. Change the test fixture from
  `Article 999` to a fabricated **leaf** (`Article 4.2`, `Annex III.4.employment`) — the case that
  currently fails. Empirically the fix drops no legitimate citation (0 real leaves lack verbatim text).
- **Confidence:** High (82-92)
- **Found by:** logic-judge, errors, instrument, engmgr, hardrules (5 lenses agreed)

---

### [I5] `ab_judge` swap-consistency counts judge ERRORS as judge agreement — the reliability metric rises with instrument breakage

- **File:** `evals/harness/ab_judge.py:149-157` (`_judge_one`), `:187` (`agreed`), `:370-371`, `:237-238`, `:222-228`
- **Bug:** `_judge_one` collapses **every** failure — transport error, auth failure, unparseable
  JSON, missing `winner` — into the same `"tie"` string a genuine tie uses (pre-existing since R139).
  `3af98af` then layered two **new** aggregates on top without adding an error channel:
  `swap_consistency_rate = swap_agreements / total_rows` and
  `effective_win_rate_b = (wins_b + 0.5*ties) / total_rows`. Two errored calls compare equal, so the
  pair is recorded as a position-swap **agreement**. `AxisResult` has no error field, `run_ab` never
  inspects `judge_error`, and `_format` prints neither metric — they exist only in the durable
  sidecar `evals/bench/results/ab-judge-<label>.json`.
- **Failure scenario (reproduced with `_call_judge_with_retry` stubbed to return
  `{'judge_error': ...}`, 20 rows):** `swap_consistency_rate: 1.0`, `effective_win_rate_branch: 0.5`,
  `ties: 20`, `wins_branch: 0`, `wins_baseline: 0`. Reachable configurations: `--judge-provider
  bedrock` (a choice `3af98af` itself added at `:439`) with the wrapper up but no AWS credential —
  `evals/judge/runner.py:262-263` returns a **non-retryable** `bedrock_not_configured` on every call,
  and `evals/harness/` loads no dotenv. Note a *total* outage partly self-flags
  (`win_rate_branch: null`, `verdict: "no-decisive-pairs"`).
- **Impact:** The **partial**-failure case is the merge-relevant one and nothing contradicts it: if
  k of N pairs error, each errored pair simultaneously inflates `swap_consistency_rate` toward 1.0
  *and* drags `effective_win_rate_branch` toward 0.5, so a genuine branch win reads as "even" beside
  a reassuringly high self-consistency score, with `verdict` and `p_value` looking entirely normal.
  This is the repo's own instrument trap embedded in the metric built to detect it. Bounded because
  `dynamic_ab`, not `ab_judge`, is the merge gate, and nothing consumes `swap_consistency_rate`
  outside its own sidecar.
- **Suggested fix:** Give `_judge_one` a distinguishable failure sentinel; have `_pairwise_verdict`
  return a tri-state `agreed` (`True`/`False`/`None` when either ordering errored); count
  `swap_agreements` only over pairs where both orderings produced a real verdict and divide by that
  count; exclude errored pairs from `effective_win_rate_branch`'s denominator; add a
  `judge_errors` counter to the per-axis dict **and** to `_format`.
- **Confidence:** High (78-88)
- **Found by:** logic-judge, errors, contract, state, instrument, hardrules (6 lenses agreed — the
  single most-corroborated finding in this review)

---

### [I6] Cappelli threshold-sensitivity curve derives its ground truth from the score it thresholds — precision is 1.0000 by construction

- **File:** `evals/bench/run_cappelli_bench.py:117-118`, `:149`, `:192-199`; scorer `evals/bench/metrics.py:610-642`
- **Bug:** `all_sim_scores.append(sem_sim)` is immediately followed by
  `all_relevance.append(sem_sim >= 0.25)` — the label vector **is** the score vector, thresholded at
  a constant. Both are passed to `threshold_precision_recall_curve`. Substituting `g := (s >= 0.25)`
  into `fp = #{s >= t and not g}` makes fp **unsatisfiable** for every `t >= 0.25`, so precision is
  identically 1.0; symmetrically `fn = 0` for every `t <= 0.25`, so recall is identically 1.0; at
  `t == 0.25` all three are exactly 1.0000. The docstring claims it detects *"when loose similarity
  thresholds mask missing statutory precision"* — which is precisely what it cannot do.
  A second, independent defect compounds it: `metrics.py:633` returns `prec = 1.0` when
  `tp + fp == 0`, i.e. **perfect precision on an empty prediction set**.
- **Failure scenario (the committed artifact already shows the fingerprint):**
  `evals/bench/results/cappelli_bench_results.json:56-118` records precision **1.0000 at all eight
  thresholds ≥ 0.25** (0.25/0.30/0.35/0.40/0.50/0.60/0.70/0.80) with F1 exactly 1.0000 at 0.25, while
  varying only below the cut (0.6000 / 0.6316 / 0.7059 at 0.10 / 0.15 / 0.20) — and while
  `overall_averages.semantic_similarity` is **0.2885**, `jaccard_loose` 0.0936, `rouge_l` 0.1193.
  Rows 0.50-0.80 print `precision 1.0 / recall 0.0`: perfect precision from zero predictions.
  A content-free boilerplate paragraph substituted for every answer reproduces the pinned 1.0
  precision column exactly. (An *all-empty* engine instead trips the `total_pos == 0` guard at
  `:624-625` and prints all zeros — so the curve's only two reachable shapes are "all zeros" and
  "precision pinned at 1.0"; neither observes the engine.)
- **Impact:** `docs/PROPOSAL_GENAI_EU_AI_ACT_COMPLIANCE_EVAL.md:52-54` already narrates this as an
  empirical **"Crucial Finding"** ("precision remained 1.0") in a document framed as a head-to-head
  against Cappelli et al. Table 8. A published, self-confirming number. The primitive itself is
  sound and correctly unit-tested with independent labels
  (`tests/test_cappelli_metrics.py:42-50` → precision 0.75), which is exactly why the suite is blind
  to this — the defect is entirely at the caller.
- **Suggested fix:** Label relevance from a gold-side signal the score cannot author — an explicit
  per-row `is_relevant` in `evals/bench/data/cappelli_compliance_2026.json`, or
  `reference_correctness_loose(pred_refs, expected_refs) > 0`. If no independent label exists, delete
  the curve, the `print_scorecard` block, the `threshold_analysis` entry in `METRIC_PROVENANCE`
  (`metrics.py:128-130`) and the proposal paragraph. Separately return `None`/`0.0` with an explicit
  `n_predicted` at `metrics.py:633` rather than 1.0. Also drop the dead import at
  `evals/bench/run_live_deep_eval.py:36`.
- **Confidence:** Very high (90-96)
- **Found by:** logic-bench, errors, contract, instrument, engmgr, hardrules (6 lenses agreed)

---

### [I7] Both new benchmark runners default to `provider=cli` — the no-Stage-2 path — and one of them grades a Stage-2 prompt change shipped in the same commit against gold copied from that prompt

- **File:** `evals/bench/run_live_deep_eval.py:344` + `:160`; `evals/bench/run_cappelli_bench.py:204` + `:51`
- **Bug:** Both runners default `--provider` to `"cli"`, both *assign*
  `os.environ["P2P_GRAPH_RAG_PROVIDER"] = provider` (overwriting an operator's exported
  `openai_wrapper`), and both module docstrings document `--provider cli` as **the** invocation —
  while `run_live_deep_eval.py:1` calls itself a *"Live Deep Evaluation Runner"* and prints
  `RUNNING LIVE EVALUATION` at `:170`/`:235`. `app/engines/_graph_rag_impl.py:1324-1328` short-circuits
  Stage-2 on the literal `"cli"`, so `USER_ANSWER_COVERAGE_CLAUSE` — whose only consumer is
  `_graph_rag_impl.py:7827` — is never in any prompt. This is verbatim the ground on which CLAUDE.md
  retired `evals.bench.runner`.
- **It was actually run inert.** `evals/bench/results/cappelli_bench_results.json` (session
  timestamp 2026-08-14T20:14:34Z) carries per-row `latency_ms` of **14.5-440 ms** across all 20 rows
  — CLAUDE.md's own cheapest inert-arm detector fires on every one — yet it reports a full
  5-dimension scorecard **including a `technical_documentation` bucket**, the exact dimension the
  prompt hunk targets. `run_live_deep_eval` measured a mean 91.8 ms/row against a ~16 s live baseline.
  Neither `grand_summary` (`run_live_deep_eval.py:315-333`) nor `summary`
  (`run_cappelli_bench.py:150-166`) records the resolved provider, so the archived artifact cannot be
  re-attributed later.
- **Second half — circular gold.** `evals/bench/data/cappelli_compliance_2026.json` row
  `cappelli_cs1_q5_technical_documentation` has
  `expected_keywords = ["technical file","risk management file","data governance record","human
  oversight protocol","logging","declaration of conformity","CE marking","Annex IV"]` — **7 of 8
  verbatim** from the checklist the same commit shipped in
  `docs/PROPOSAL_GENAI_EU_AI_ACT_COMPLIANCE_EVAL.md:140` and injected into the live prompt ([C2]).
  `cappelli_cs4_q4/q5` mirror it for the Article 27 FRIA clause. So at `--provider cli` the benchmark
  cannot see the change; at `--provider openai_wrapper` it measures the **prompt echo**. Either way no
  number it produces can support a decision about the prompt.
- **Third — `run_live_deep_eval` is not the hard turn.** `HARD_JULY7_SCENARIOS` is ten hand-authored
  **single-turn** rows POSTed as `[{"role":"user","content":q}]` (`:246`) with self-written gold.
  CLAUDE.md open item #2 defines the hard turn as the adversarial pushback carried by 67 of 111 rows
  in `run_official_batch --mode hard`, and records that it has **never been run**. A file named
  `run_live_deep_eval` that is neither live nor the hard turn invites the belief that item #2 is closed.
- **Also:** `cli` leaves `stage2_landed` False, so `set_answer_no_cap` (`app/routes/regenold.py:7505-7506`)
  never fires and `MAX_ANSWER_SENTENCES=3` plus the soft char cap stay **armed** — the runner scores
  ≤3-sentence capped answers against multi-sentence gold and understates the product against the paper.
- **Suggested fix:** Default both `--provider` to `openai_wrapper` (or make it required and refuse to
  print a scorecard when it resolves to `cli`); write the resolved provider, `stage2_enabled` and the
  per-row `stage2_model=` note into both summaries; print a loud banner and abort when mean row
  latency is under ~2 s or zero rows recorded a Stage-2 note. Re-derive `cs1_q5` / `cs4_q4` / `cs4_q5`
  `expected_keywords` from `get_provision_text` rather than from the prompt string. Rename
  `run_live_deep_eval` or post the real two-turn `--mode hard` rows.
- **Confidence:** High (80-88)
- **Found by:** logic-bench, contract, instrument, hardrules, engmgr (5 lenses agreed)

---

### [I8] The new ROUGE-L / keyword tokeniser cannot represent single-digit article numbers or percentages — `answer_rouge_l("Article 5 …", "Article 9 …") == 1.0`

- **File:** `evals/bench/metrics.py:525-530` (`_token_sequence`), `:552-571` (`answer_rouge_l`), tokeniser `:166`
- **Bug:** The LCS DP and the Lin-2004 F-measure are correct; the **tokeniser** feeding them is not.
  `_TOKEN_RE_V2 = [A-Za-z0-9][A-Za-z0-9'\-]+` requires ≥2 characters, and `len(t) >= 2` is applied on
  top, so every one-character token is unrepresentable. On EU AI Act text that deletes article numbers
  **5, 6, 9** and the percentages **7%, 3%, 1.5%**. (Two-digit numbers survive — `_tokens("Article 99")
  == {'99','articl'}` — so the blindness is specific and easy to miss.) The tokeniser itself is
  pre-existing (R82-A, `f124923`); what `ee61cfd`/`cc47f8b` added is the pair that makes it bite: a new
  order-sensitive "structural sequence completeness" metric built on it, plus new gold datasets keyed
  on precisely those unrepresentable tokens.
- **Failure scenario (measured on real rows, not toys):** taking the verbatim `gold_answer` of
  `hard_july7_01_emotion_workplace` and substituting Article **5**(1)(f) → Article **9**(1)(f):
  `answer_rouge_l(wrong, gold) == 1.0` — a perfect structural match for a wrong statute — and
  `answer_keyword_recall(wrong, expected_keywords) == 0.833`. A decoy answer naming **no article at
  all** scores `answer_keyword_recall == 1.0` on that row. On
  `hard_july7_10_penalties_tier_ceiling` — the row whose entire purpose is the fine tiers — `"7%"`,
  `"3%"` and `"1.5%"` tokenise to the **empty set** and vanish from the gold, so an answer stating no
  percentage tier scores 1.0; `"7 500 000"` additionally collapses to `{'500','000'}`, losing the 7.
  Dataset audit: **11 of 182** new `expected_keywords` are degenerate — 8 collapse to the bare token
  `{articl}` (a token every RAG answer contains unconditionally, i.e. guaranteed free credit) and 3
  tokenise to nothing.
- **Impact:** Confined to the two new runners' headline scorecards and the proposal doc numbers
  derived from them. The merge gate is unaffected: `evals/harness/dynamic_ab.py:107-108` computes its
  own `kw_recall` with a plain substring test and never calls either function, so hard rule #8 gating
  is intact.
- **Suggested fix:** Keep length-1 tokens when they are digits and normalise `N%` / `N,N%` to a single
  token — **behind a NEW tokeniser name**, so the historical `_tokens`-based axes stay byte-reproducible
  (house rule: change the formula, change the name). Independently, replace the 8 bare `"Article N"`
  keywords with discriminative phrases — article identity is already scored by
  `reference_correctness_*` against `expected_refs` and does not belong in the keyword axis.
- **Confidence:** High (90)
- **Found by:** logic-bench

---

### [I9] A char-trigram/Jaccard lexical score is registered as "Sentence-BERT" and printed as `SBERT`, and the false attribution is stamped into every eval sidecar

- **File:** `evals/bench/metrics.py:574-609` (implementation), `:124-127` (`METRIC_PROVENANCE`), `evals/bench/run_live_deep_eval.py:231`, `:286`
- **Bug:** `answer_semantic_similarity_proxy` is `0.70 * cosine(char-3grams) + 0.30 * word-token
  Jaccard`. There is no embedding model anywhere on the path (`grep sentence_transformers|MiniLM|
  SentenceTransformer` → no hits). `METRIC_PROVENANCE["cappelli_2026_diagnostics"]
  ["answer_semantic_similarity"]` nonetheless reads *"Semantic similarity proxy (Sentence-BERT /
  character-ngram cosine vector proxy) capturing conceptual equivalence **decoupled from surface
  lexical form**"*, and both runners print the bare column header `SBERT:` with no qualifier.
  `docs/PROPOSAL_GENAI_EU_AI_ACT_COMPLIANCE_EVAL.md:111-112,159` presents `all-MiniLM-L6-v2` as
  implemented.
- **Failure scenario (measured):** against gold *"Emotion recognition in the workplace is prohibited
  under Article 5(1)(f) except for medical or safety reasons."*, a conceptually **equivalent**
  low-lexical paraphrase — *"Employers may not deploy affect-inference AI on staff; the ban carves
  out health and security use cases."* — scores **0.043**. A real `all-MiniLM-L6-v2` scores that pair
  ≈0.85. The metric returns near-zero on precisely the case that "decoupled from surface lexical
  form" is defined by. An operator reading `SBERT: 0.658` concludes an embedding model found
  conceptual overlap when a trigram counter found string overlap.
  (Note: the length-penalty story is **not** supported — at the +41% answer inflation CLAUDE.md
  records, a verbatim superset scores 0.80, *above* a near-verbatim paraphrase's 0.76.)
- **Impact:** `METRIC_PROVENANCE` is the repo's own defence against ruler drift, and it is serialised
  wholesale into durable sidecars by `evals/bench/runner.py:365`,
  `evals/regenold/run_official_batch.py:519`, `evals/harness/easyhard_ab.py:167` and `:570`,
  `evals/regenold/run_evaluator_batch_july7.py:492`, `evals/regenold/r326_live_acceptance.py:470` and
  `scripts/rescore_sidecars.py:137` — so the "Sentence-BERT" claim is written into artifacts of runs
  that **never call the function**. `tests/test_cappelli_metrics.py:35` only asserts
  `0.5 <= score <= 1.0` on a high-overlap pair, so it cannot catch the mislabel.
- **Suggested fix:** Rename the function to `answer_char3gram_lexical_proxy` (or
  `answer_lexical_similarity_proxy`), change the console header to `LexSim`, and rewrite the
  provenance entry to *"character-trigram count cosine + word-token Jaccard; surface-overlap only;
  NOT an embedding model; near-zero on low-lexical paraphrase"*. Correct
  `docs/PROPOSAL_GENAI_EU_AI_ACT_COMPLIANCE_EVAL.md:112,159`. If a genuine semantic axis is wanted,
  drive it from the existing SVD-128 index in `app/engines/_assets/`.
- **Confidence:** High (85-90)
- **Found by:** logic-bench, instrument (agreed)

---

### [I10] `bb793ca` loosened the Answer-Conciseness judge prompt **in place**, ungated, on the one axis with zero headroom

- **File:** `evals/judge/legal_v2.py:488-514` (renderer), cf. gated postprocess half at `:811-830`
- **Bug:** `bb793ca` rewrote the UNREQUESTED TOPIC definition. The old rule flagged any sentence that
  *"addresses a legal topic the question did not ask about and that is not necessary context"*. The
  new rule requires *"a substantial detour into an unrelated legal regime"* and then **explicitly
  exempts** *"Direct statutory conditions, exemptions, or immediate legal consequences of the primary
  rule"*. REDUNDANT was narrowed in the same hunk. Both edits are strictly subtractive — every
  sentence the new prompt flags, the old one also flagged; the converse is false.
  R331.1 gated the **post-processing** half of the same loosening behind
  `REGENOLD_JUDGE_CONCISENESS_LENIENCY` (default OFF) and annotated it with R327's *"if you change a
  formula, change its NAME"*. The **prompt** half — where the axis is actually defined — was left
  outside that gate, under the unchanged canonical name `answer_conciseness`. The same commit also
  deleted the docstring warning that argued against the edit, and the module docstring at `:39-44`
  still documents the **old** definition, so the file now contradicts its own prompt.
- **Failure scenario:** `docs/reviews/R309-hard-batch-live-opus5-sonnet5-judge.md:230` pins a
  pre-change baseline measured with this exact judge: `answer_conciseness 27/72 = 0.375`, with **13 of
  those failures** clustered at `:260` as *"drifts from risk-classification question into unrequested
  conformity-assessment-procedure mechanics"* and a further 22 as "redundant restatement". Conformity
  assessment (Art. 43) **is** the immediate legal consequence of a high-risk classification under
  Art. 6 — i.e. exactly what `:507-508` now declares permissible. Re-run the same 72 rows, same
  answers, same sonnet-5 judge: the pass rate rises with **no product change**.
- **Impact:** Every conciseness number produced after `bb793ca` sits on a different ruler from every
  number before it, with nothing in the artifact recording the switch — on the axis CLAUDE.md flags
  as pure-downside risk. Bounded because `legal_v2` is not the merge gate.
- **Suggested fix:** Put `:488-514` behind `REGENOLD_JUDGE_CONCISENESS_LENIENCY` so both halves flip
  together, **or** emit the loosened axis under a new name (`answer_conciseness_detour`) and keep
  `answer_conciseness` on the pre-`bb793ca` wording until an A/B justifies the move. Re-sync the
  module docstring at `:39-44` either way.
- **Confidence:** Medium-High (82)
- **Found by:** hardrules

---

### [I11] Cappelli cs4 gold demands an Article 27 FRIA from a deployer Article 27(1) does not reach — and the wrong ref is already the sole source of two rows' scores

- **File:** `evals/bench/data/cappelli_compliance_2026.json:185-186`, `:207-208`, `:218-219`
- **Bug:** Three `cs4_retail_facial_recognition` rows require `Article 27`. Pinned
  `get_provision_text("Article 27.1")` confines the FRIA duty to (i) bodies governed by public law,
  (ii) private entities providing public services, and (iii) deployers of **Annex III 5(b)/(c)**
  systems. The case study is an in-store retail chain — a private commercial entity — and the
  dataset's own `annex_iii_category` at `:181` puts the system in **Annex III point 1** (biometrics).
  It fails all three limbs. Line `:207` additionally says *"conduct and **register**"*; Article 27(3)
  is a **notification** to the market surveillance authority.
- **Failure scenario:** the harm is already recorded, not hypothetical. In
  `evals/bench/results/cappelli_bench_results.json`, `cappelli_cs4_q2_obligations` predicted
  `["Article 12","Article 13","Article 27"]` (ref_loose 0.2) and `cappelli_cs4_q4_compliance_gaps`
  predicted `["Annex III","Article 27"]` (ref_loose 0.25). On **both** rows `Article 27` is the
  **only** predicted ref intersecting gold — the entire recorded score is carried by a citation
  Article 27(1) does not authorise, and the recorded q2 answer asserts the FRIA duty applies to this
  deployer. Conversely a legally correct answer that declines Article 27 scores
  `reference_correctness_loose` 0.80 instead of 1.00, `_strict` 0.889 instead of 1.00, and
  `answer_keyword_recall` 0.6.
- **Impact:** The ruler is wrong in the direction that **launders an actual over-citation into the
  score**, on the axis CLAUDE.md identifies as the whole remaining gap.
  `docs/PROPOSAL_GENAI_EU_AI_ACT_COMPLIANCE_EVAL.md:130-132,165` already proposes shipping an
  unconditional *"Structured Art. 27 FRIA Generator"* for high-risk deployers on this premise — which
  would make it Critical.
- **Suggested fix:** Restate the cs4 gold to say Article 27 does **not** apply, with the Article 27(1)
  limb test; drop `"Article 27"` from the three `expected_refs`; drop the FRIA keywords at `:187/209/220`;
  drop "register" from `:207`. Alternatively change the case study's deployer — but that changes the
  Annex III classification and the rest of the cs4 gold.
- **Confidence:** High (88)
- **Found by:** legal

---

### [I12] Four `technical_documentation` gold answers misstate Annex IV — "the 8 mandatory Annex IV files", CE marking as a component, a FRIA report inside Annex IV

- **File:** `evals/bench/data/cappelli_compliance_2026.json:53`, `:108`, `:163`, `:218`
- **Bug:** Verified against the pin — `Annex IV.1` … `Annex IV.9` all resolve, `Annex IV.10` is
  `None`: Annex IV has **nine** points, not 8. `'ce marking'` does not occur in its 5,710 chars
  (Annex IV(8) is *a copy of the EU declaration of conformity*, Art. 47; CE marking is Art. 48).
  Line `:218` places a *"Fundamental Rights Impact Assessment report (Article 27)"* inside the Annex
  IV list; the FRIA appears in none of the nine points. Six of the eight listed items **do** trace to
  real Annex IV content (risk management = 5, declaration of conformity = 8, post-market monitoring =
  9, human oversight = 2(e), data governance = 2(d), system architecture = 2(c)), so the defects are
  the count and the two fabricated entries.
- **Failure scenario (measured):** `answer_keyword_recall` flattens keywords into one stemmed token
  set. A legally correct answer enumerating all **nine** Annex IV points scores **0.75** (missing
  tokens `ce`, `mark`, `file`) while the fabricated gold scores **1.00**. The correct answer is
  penalised for declining to claim CE marking is part of the technical file.
- **Impact:** This is the **ruler half** of the pair whose behaviour half is [C2] — the identical
  fabricated list is on both sides of the measurement, introduced in one unreviewed commit. That is
  the R327 trap: a ruler built to like the change it grades. Fixing the gold without reverting the
  prompt clause leaves the wrong law shipping to users.
- **Suggested fix:** Rebuild the four gold answers from `get_provision_text("Annex IV")` points 1-9;
  state nine, not eight; move CE marking (Art. 48) and the FRIA (Art. 27) into a separate "related
  obligations" clause; drop `"CE marking"` from those rows' `expected_keywords`; and revert
  `app/data/graph_rag_prompts.py:898-903` in the same change.
- **Confidence:** High (85)
- **Found by:** legal, engmgr, contract (agreed — three lenses reached this from different directions)

---

### [I13] Cappelli gold attributes the six-month log-retention floor to Article 12, which contains no retention period

- **File:** `evals/bench/data/cappelli_compliance_2026.json:163`, `:218`
- **Bug:** `"6-month minimum logging mechanism (Article 12)"` / `"6-month log retention mechanism
  (Article 12)"`. Pinned Article 12(1)-(3) states only that systems *"shall technically allow for the
  automatic recording of events (logs) over the lifetime of the system"* — no retention period
  anywhere. The six-month floor is **Article 19(1)** for providers and **Article 26(6)** for
  deployers. Both rows ask about *provider* technical documentation, so Article 19 governs. The same
  dataset gets it right at `:185` for the deployer case (`Article 26(6)`), so it contradicts itself.
- **Failure scenario:** the repo's own engine already gets this right — a live `cli` probe of *"How
  long must a provider keep the automatically generated logs?"* returns `Article 19` and quotes 19(1)
  verbatim. Adding the actually-governing `Article 19` to the `cs3_q5` prediction moves
  `reference_correctness_strict` **1.0 → 0.9231** and `reference_conciseness` **1.0 → 0.7347** (the
  latter via unique-head cardinality, not precision). The correct citation is the penalised one.
- **Impact:** The benchmark's ground truth contradicts the system it grades, and the false prose is
  written verbatim into `evals/bench/results/` under the label `gold_answer`.
- **Suggested fix:** Attribute the mechanism and the floor separately — *"automatic event logging
  (Article 12) with provider log retention of at least six months (Article 19)"*. Leave `:185`'s
  Article 26(6) alone.
  **Adjacent, out of scope for these six commits but the same error in a SHIPPING module:**
  `app/data/article_requirements_full.py:154` and `:549` both file the Article 19(1) sentence under
  Article 12(3), and that module is imported by `app/engines/_graph_rag_impl.py:6009`, so it can reach
  a Stage-2 answer. It predates these commits (R109, `45b0135`) and needs its own ticket.
- **Confidence:** High (90)
- **Found by:** legal

---

### [I14] Cappelli cs4 gold labels Article 5(1)(c) "mass surveillance" and applies the law-enforcement-only 5(1)(h) to a shop

- **File:** `evals/bench/data/cappelli_compliance_2026.json:196`, keywords `:198`
- **Bug:** `cappelli_cs4_q3_legal_risks` gold reads *"(1) unlawful biometric categorization or
  prohibited mass surveillance (Article 5(1)(h) and Article 5(1)(c))"*. Pinned Article 5(1)(c) is
  **social scoring**; Article 5(1)(h) is real-time remote biometric identification *"for the purposes
  of law enforcement"*, which a retail chain is not. The same file's line `:174` **does** carry the
  hedge (*"prohibited under Article 5(1)(h) when conducted by law enforcement"*), so the dataset
  contradicts itself. The Act's own "mass surveillance" language is Recital 43 / **Article 5(1)(e)**
  (untargeted scraping of facial images from CCTV), which binds any operator. (Article 5(1)(g) —
  proposed in the original filing — is *not* clearly engaged: the scenario never describes inferring
  race, political opinion, religion or sexual orientation.)
- **Failure scenario (measured):** `expected_keywords` at `:198` contains the literal
  `"mass surveillance"`, pooled into a 9-token target set. An answer that correctly declines the
  mass-surveillance framing forfeits 2/9 = **22.2 pp** of that row's keyword recall (0.7778 vs 1.0),
  plus ROUGE-L 0.447 vs 1.0 and semantic 0.593 vs 0.984. That row is 1 of 4 in the `legal_risks`
  dimension average.
- **Suggested fix:** Replace item (1) with *"prohibited creation or expansion of facial recognition
  databases through untargeted scraping of CCTV footage (Article 5(1)(e))"*; drop 5(1)(h) or carry
  `:174`'s hedge; if 5(1)(c) is meant for the behaviour-based-pricing limb, say **"social scoring"**
  in those words. Update `expected_keywords` in step — leaving `"mass surveillance"` while fixing the
  citation keeps the metric rewarding the wrong framing.
- **Confidence:** High (85)
- **Found by:** legal

---

## Suggestions

One line each. Confirmed real, but none produces a wrong number that drives a merge decision today.

- **`app/engines/neo4j_semantic_graph.py:492`** — 492 lines with **zero production importers** (only
  `tests/test_airo_ontology.py:19`; `app/engines/__init__.py` is empty, no dynamic import reaches it).
  Delete it, or wire it behind a default-OFF flag registered in `_engine_cache_key` and prove it fires
  with a call counter. Its sibling `cohere_reranker.py` from the same commit was already deleted for
  exactly this reason (`app/engines/_graph_rag_impl.py:6544-6547`); only one half was cleaned up. A
  future `dynamic_ab` over anything in this module returns `+0.0000` / INERT. Do **not** seed its
  `RiskScenario`/`RiskControl` labels into the shared Aura instance from this repo (hard rule #12).
  *[logic-runtime, contract, engmgr agreed]*
- **`evals/bench/run_live_deep_eval.py:121`, `:123`** — `hard_july7_10` gold says Article 99(5) is
  **1.5 %**; the pin says **1 %** (Art. 99(3)/(4) at 7 %/3 % are correct, so this is an isolated
  fabrication). Currently scoring-inert because `_tokens("1.5%")` is the empty set, but it is
  persisted verbatim as `gold_answer` into `live_deep_eval_results.json` — a latent trap for any
  future judge. *[logic-bench, engmgr agreed]*
- **`evals/bench/run_live_deep_eval.py:105`** — `hard_july7_08` gold attaches Article 73(4)'s 10-day
  clock to *"death of a person **or serious harm to a person's health**"*. Pinned 73(4) is death only;
  serious harm falls under 73(2)'s 15-day general rule. (The phrase is borrowed from Art. 3(49)(a).)
  Do **not** add the proposed build-time numeric-substring assertion — the tokeniser makes it unsound.
- **`evals/bench/data/cappelli_compliance_2026.json:120`** — `Annex III.2.a` is a fabricated
  coordinate (`get_provision_text` → `None`; Annex III point 2 is one unlettered paragraph), passed by
  the head-lax `provision_exists`. Scoring-inert today because the runner uses head-level ref
  formulas, but it becomes a silent gold-shrink the moment anyone switches this bench to the
  `*_exact_coord` variants its sub-point-grain `expected_refs` would justify.
- **`evals/bench/data/cappelli_compliance_2026.json:6,9,17,28,39,50`** — all five `cs1` rows put CV
  pre-screening under `Annex III.4.b`; the pin puts recruitment and candidate evaluation in **4(a)**
  (4(b) is in-employment terms/promotion/termination). Scoring-inert (`annex_iii_category` is read by
  no code; head-level refs collapse 4(a) and 4(b)), but republished in
  `docs/PROPOSAL_GENAI_EU_AI_ACT_COMPLIANCE_EVAL.md:18`.
- **`docs/ontology/AIRO_EU_AI_ACT_ONTOLOGY_DEEPDIVE.md:197`** — still asserts the fabricated
  **"72h / 15d"** serious-incident SLA that R331 removed from `app/data/ontology.py` and the TTL. 72
  hours is the GDPR Art. 33 window; Article 73 is 15 d / 2 d / 10 d. The doc is read by no code, but
  it is the narrative rationale for the registry it now contradicts.
- **`evals/bench/run_live_deep_eval.py:161-164, 186-195, 247-256` and `run_cappelli_bench.py:57-60,
  88-97`** — both new runners call `limiter.reset()` **once before the loop** (every other runner in
  the repo resets per request: `evals/bench/runner.py:42-59`, `evals/regenold/runner.py:465-472`) and
  never inspect `resp.status_code`, converting any non-200 body into `answer=""`/`references=[]`
  scored 0.0 on eight axes. `run_live_deep_eval` issues exactly **30** requests against a 30/min
  anon bucket — request 31 is a 429, measured — so it passes today with a margin of exactly one
  request. A 21st GT row or an 11th hard scenario makes it fire silently.

---

## CLAUDE.md drift

These commits made the following lines of `CLAUDE.md` wrong or incomplete. Correct them — the file is
load-bearing, and several of these are the exact claims a future round would rely on.

| CLAUDE.md content | What is now wrong |
| --- | --- |
| Knowledge surface table: `app/data/kb_search.py` — "BM25 index — **345 docs**" | Default corpus is now **373** (131 kb / 48 ontology / 126 corpus / 68 definition). 345 is the `REGENOLD_ONTOLOGY_RISK_DOCS=0` arm. See [I1]. |
| Knowledge surface table: `app/data/ontology.py` — "`PRACTICE_REGISTRY` ×8, `ANNEX_III_REGISTRY` ×8, `PHASE_REGISTRY` ×4" | `938933a` added six unlisted registries: `RISK_SCENARIO_REGISTRY`, `RISK_CONTROL_REGISTRY`, `GPAI_REGISTRY`, `CONFORMITY_ROUTE_REGISTRY`, `FRIA_REGISTRY`, `SERIOUS_INCIDENT_REGISTRY` — all six now feed the BM25 index. |
| Graph section: "This repo ships `SEED_VERSION = 2026-07-24-r291-fullseed`" | Now **`2026-08-14-sota-airo-fullseed`** (`scripts/seed_neo4j_kb.py:136`). The hard-rule-#12 hazard is unchanged (it still mismatches the live `2026-08-08-r323-annex-sections`), but the version string in the doc is stale — and the seeder now also writes `RiskScenario` / `RiskControl` / `GPAIModelProfile` / `ConformityRoute` / `FRIAWorkflow` / `SeriousIncidentSLA`, so the "18 labels" census is stale too. |
| Env-flags table | Missing entirely: **`REGENOLD_ONTOLOGY_RISK_DOCS`** (default **ON**, unmeasured — [I1]), **`REGENOLD_ANSWER_COVERAGE`** (default **ON**, delivers the clause behind [C1]/[C2] and is not a targeted rollback because it also drops the R318 no-Omnibus sentence), **`REGENOLD_JUDGE_CONCISENESS_LENIENCY`** (default OFF — but its prompt half is ungated, [I10]), **`REGENOLD_JUDGE_FACTUAL_THRESHOLD`**, **`REGENOLD_COHERE_RERANK`**. |
| `GROUNDED_JUDGE_STRICT_GROUNDING` row: "ON makes answer-correctness unscorable on the July-7 batch" | True for `evals/judge/grounded.py`; **silently false for `evals/judge/legal_v2.py`** since `d7be457` ([I3]). Since open item #7 nominates `legal_v2` as the replacement judge, the row must say which judge it applies to. |
| Hard rule #5's `provision_exists` caveat | Still correct, and now **violated in-tree**: `evals/judge/legal_v2.py:660` uses `provision_exists` as a coordinate validator ([I4]). Worth naming the line so the caveat has a concrete referent. |
| "Do not re-propose — measured and dead": *"The Cappelli et al. (2026) paper's 7 optimisations — none buildable"* | Contradicted by `cc47f8b`, which implements at least optimisation #2 (FRIA generator) and #3 (Annex IV checklist injector) as live prompt injections ([C1]/[C2]). Either amend the line **with the reason it is back in scope**, or revert the commits — do not leave the doc silently contradicted. |
| Testing / Validation policy section | Does not mention `evals.bench.run_cappelli_bench` or `evals.bench.run_live_deep_eval`, both of which default to `provider=cli` — the exact instrument the davidath retirement paragraph above them warns about. Add them to that warning explicitly ([I7]). |
| Gotcha: "The Stage-2 SYSTEM prompt is dropped by the Claude Max wrapper" | Now has a concrete **inversion** worth recording: the *accurate* Annex IV(1)(e)/(2)(c) rule sits in `ANSWER_GENERATE_SYSTEM` (`graph_rag_prompts.py:118`, dropped on 100% of wrapper requests) while the *fabricated* component list sits in the user clause (`:898`, delivered on 100%) — [C2]. |
| Gotcha: "`evals/harness/` does not load dotenv" | Applies equally to `evals/bench/` — and worse, the two new runners **assign** `P2P_GRAPH_RAG_PROVIDER`, overwriting an operator's exported value rather than defaulting to it ([I7]). |
| `docs/ROUNDS.md` | Contains **no entry** for any of the six commits (`grep -ci cappelli|airo|judgebench` → 0). The round log is incomplete for ~3,300 lines of change, including a live prompt edit and a retrieval-corpus change. |

---

## Safe to ship as-is?

**No.** Two Critical defects are on the live default path and one is in a published measurement.
`app/data/graph_rag_prompts.py:898-903` ships a false statement of EU law to compliance users on
every provider — CE marking is not an Annex IV component — and instructs the model to emit Charter
article numbers that the adjacency-anchored foreign-instrument guard cannot suppress in an
enumeration and that `ARTICLE_EXISTENCE` is structurally blind to, so they land on the wire as AI Act
citations on the two axes CLAUDE.md names as the entire remaining competitive gap. Because a merge to
`main` in this repo reaches a real Railway service and both defects are **code defaults** rather than
env-gated flags, `railway.toml`'s inert `[deploy.envs]` offers no protection. Separately,
`evals/bench/run_live_deep_eval.py:128` reports that 11 of 38 expert-flagged regressions were fixed
without testing them, and that inflated 0.7895 is already committed to a results file cited by a
proposal document. Neither of the two prompt changes has an A/B, a live probe, or a `dynamic_ab`
verdict, and none of the six commits has a `docs/ROUNDS.md` entry — so the repo currently cannot say
what any of them did. The Important tier compounds this: the benchmark shipped to justify the prompt
change defaults to `provider=cli` and therefore cannot observe it, its gold keywords were copied from
that same prompt, its threshold curve is a tautology, its "SBERT" column is a trigram counter, and
the retrieval corpus was re-ranked with the one documented rollback A/B corrupted by a stale index
singleton. The measurement layer is a large part of this product; right now it would confirm the
prompt change no matter what the prompt change did.

---

## FIX PLAN

### Before merging (blocking)

1. **Revert `app/data/graph_rag_prompts.py:898-903`** — both added sentences, as one hunk. This
   closes [C1] and [C2] and removes the behaviour half of [I12]'s ruler/behaviour pair. Zero
   measurable cost; the topic-neutral enumeration rule at `:885-889` already covers the intent.
2. **Fix `evaluate_mistake_resolution`** ([C3]) — call
   `evals.regenold.antifragile_live._mistake_resolved(answer_low, pred_refs, mistake)` and thread
   `pred_refs` from `run_live_deep_eval.py:207`. Then **regenerate or delete**
   `evals/bench/results/live_deep_eval_results.json`; `0.7895` is a false record on disk.
3. **Fix the two instruments that will otherwise validate the reverts** — default both runners to
   `openai_wrapper` and record the resolved provider + `stage2_landed` in both summaries ([I7]); and
   fix the `_DenseIndex` corpus-identity check ([I2]) so the `REGENOLD_ONTOLOGY_RISK_DOCS` A/B
   measures a real configuration. Doing (4) before (3) produces a number for a system that does not
   exist.
4. **Run the missing gate for [I1]** —
   `py -3.12 -m evals.harness.dynamic_ab --branch-env REGENOLD_ONTOLOGY_RISK_DOCS=0` against a
   gold-carrying set, with the `gold_dropped` veto. This is a default-ON, live-shipping retrieval
   change with 9/110 measured context regressions and no verdict. Fix the `tuple[0]` anchoring and the
   FRIA `required_steps` boilerplate regardless of the outcome. Do **not** simply flip the default OFF
   (it de-aligns the committed TurboQuant assets).
5. **Delete or gate the threshold curve** ([I6]) and correct the `METRIC_PROVENANCE` "Sentence-BERT"
   string ([I9]) before `docs/PROPOSAL_GENAI_EU_AI_ACT_COMPLIANCE_EVAL.md` goes anywhere — both are
   already narrated in it as empirical findings.
6. **Add a `docs/ROUNDS.md` entry** for the six commits and apply the CLAUDE.md drift table above.

### After merging (next round)

7. `legal_v2` grounding provenance and the strict-flag bypass ([I3]) — fix `_prepare` **and** the
   `_judge_row` guard together; fixing one leaves the axis running.
8. `legal_v2` ghost-citation gate → `get_provision_text(ref) is None`, and re-point
   `TestGhostCitationGate` at a fabricated **leaf** ([I4]).
9. `ab_judge` error channel: `judge_errors` per axis, excluded from both new metrics' numerator and
   denominator, surfaced in `_format` ([I5]).
10. Tokeniser fix behind a **new name** ([I8]), plus replacing the 11 degenerate `expected_keywords`.
11. Conciseness prompt: gate it or rename the axis ([I10]), and re-sync the `legal_v2` module docstring.
12. Gold legal corrections in dataset order: cs4 Article 27 ([I11]), the four Annex IV rows ([I12]),
    Article 12 → Article 19 log retention ([I13]), Article 5(1)(c)/(h) → 5(1)(e) ([I14]), then the
    Suggestion-tier `Annex III.4.b` / `Annex III.2.a` / `1.5 %` / `73(4)` corrections. Add a dataset
    test asserting `get_provision_text(ref) is not None` for every `expected_refs` entry —
    `provision_exists` cannot catch these.
13. Open a separate ticket for `app/data/article_requirements_full.py:154,549` (Article 19(1)
    retention filed under Article 12(3)) — pre-existing, but it is in a **shipping** module reachable
    from Stage-2.

### Leave alone

- `app/engines/neo4j_semantic_graph.py` — delete it in a cleanup pass, but it has zero runtime blast
  radius (no production importer), so it blocks nothing. Just record it as dead so a future round does
  not grade against it and read the resulting `INERT` as "safe".
- The `limiter.reset()` / status-code hardening in the two runners — zero-margin latent trap, not a
  live defect (30 requests, 30/min budget, request 31 is the 429). Fix it whenever those runners are
  next touched.
- `docs/ontology/AIRO_EU_AI_ACT_ONTOLOGY_DEEPDIVE.md:197` — one-line doc correction, no code path
  reads it.

---

## Review Metadata

- **Lenses dispatched:** logic-judge, logic-bench, logic-runtime, errors, contract, state, instrument,
  legal, hardrules, engmgr (10 specialist passes)
- **Scope:** the 6 unreviewed commits (25 files, +3,341 / −110), plus callers/callees one level deep,
  plus the current tree at `4d72ff3` (later reviewed commits R331-R337 moved several of the changed
  lines; all anchors above are re-verified against HEAD)
- **Verification:** every finding passed an adversarial refutation pass that read the current code and,
  in most cases, executed it; 18 findings were refuted outright and are excluded
- **Verified findings:** 3 Critical, 14 Important, 7 Suggestions
- **Most-corroborated defect:** `ab_judge` swap-consistency (6 independent lenses), tied with the
  Cappelli threshold tautology (6)
- **Steering files consulted:** `CLAUDE.md`, `docs/ROUNDS.md`, `.planning/NEXT-SESSION.md`,
  `CR-SKILL.md`
- **Legal claims:** all resolved against the repo's own pinned CELEX 32024R1689 via
  `app.data.provision_text.get_provision_text`, never from memory
