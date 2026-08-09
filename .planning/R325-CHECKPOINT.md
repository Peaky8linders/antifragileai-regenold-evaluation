# R325 — checkpoint

Written 2026-08-09 at `ca59ad8` (pushed to `origin/main`). Self-contained:
assumes no memory of the session that produced it.

Round scope: sync the correctness fixes from the sibling RAG repo, adapt its
`/doctor` CLAUDE.md, verify the new Aura instance end-to-end, then attack the
frontier gap.

---

## 0. State

`main` == `origin/main` == `ca59ad8`. Working tree clean. Nothing unpushed.

```
ca59ad8 docs(R325.1): record the ranker negative result, and re-rank the open list
809998f R325.1 — parent-collapse (default OFF)
a05f659 Merge R325 — correctness sync + CLAUDE.md doctor
ccc91bc R325 — CLAUDE.md doctor: split the log, cut 96%
c6db579 R325 — close every foreign-citation leak shape + kg_context enumerations
208ecef R323/W2 — graph blocks were disarming the citation-drift guard   ┐
c7b89b3 R323 — graph health probe could never fail                       │ cherry-picked
45331c8 R323 — section-aware annex items                                 │ from the
d53ff2c R323 — foreign-citation leak: pre-2015 OJ numbering              │ RAG repo
8d226ce fix(R321) — only the TIMEOUT is swallowed by boot probes         │
5bfe52b R321 CRITICAL — GDPR/Charter numbers leaking as AI Act citations │
51dbb2a R321 — deploy safety: /healthz no longer calls an LLM            ┘
```

**IN FLIGHT when this was written:** the July-7 `--mode hard` batch
(`--label r325-hard`). ~20 s/row × 111 rows ≈ 37 min. Results go to
`evals/bench/results/official-r325-hard.json` +
`official-r325-hard-hard.ckpt.jsonl`. If it did not finish, just re-run it —
see §6.

---

## 1. The two repos (read this before touching anything)

| repo | role |
| --- | --- |
| `antifragileai-regenold-evaluation` (**this**) | re-evaluation surface, graded July-7 lineage. Deploys nowhere. |
| `regenold-eu-ai-act-rag` | deploys to production. Its own rounds. |

Merge base `c0799df`; the RAG repo is ~47 commits ahead on its own line.

⚠ **`git merge parent/main` silently DELETES 29 files**, including the whole
July-7 batch (`_official_batch_20260707.json`, `evaluator_batch_july7.py`,
`run_official_batch.py`, `july7_difficulty.py`) plus `query_expansion.py`.
They existed at the merge base and the RAG repo deleted them, so git applies a
clean delete — no conflict, no marker. **Verified** by materialising the merge
tree. Sync by cherry-pick only. Round numbers also collide (both repos have an
"R318"/"R319", different work).

---

## 2. What R325 shipped

### 2a. Foreign-citation leak — 9 shapes, all closed

Reproduced HERE first, on this repo's own extractor:

```
_add_prose_named_refs(['Article 27'],
    "...EU Charter Art. 21 ... GDPR Art. 5 ... GDPR Art. 35 DPIA...")
  -> ['Article 27', 'Article 21', 'Article 5']
```

GDPR Article 5 promoted onto the wire as **AI Act Article 5** (prohibited
practices). Wire-legal, so the `ARTICLE_EXISTENCE` lint provably cannot catch
it (Articles 5/21/22/30/35 all exist).

Fixed: Component D routed through the guard (**the load-bearing half** — it was
a second, unguarded prose→citation path that re-added whatever the guard
dropped, which is why widening the regex measures byte-identical);
`_REG_NUMBER_FRAGMENT` as ONE shared definition; behind window 24 → 48 (at 24
its own numbered-regulation branch was unreachable and had never fired); ahead
window bounded-then-widened 56 → 160; `_FOREIGN_INSTRUMENT_AHEAD_RE` for the
bare postpositive form.

Now hard rule **#11**: there are TWO prose→citation paths and both need the
guard.

### 2b. kg_context was serving prohibitions without their scope

Measured against the live Aura instance before the fix:
`render_kg_context(['Article 5'])` delivered **3 of the 8** Article 5(1)
prohibited practices — (a) subliminal, (b) vulnerability, (d) criminal-risk,
(e) facial scraping, (h) real-time RBI all cut, with **nothing marking the
truncation**, so the list read as complete. Article 5(1) is 4,701 chars against
a 900-char unit cap.

After: **7 of 8**, cut explicitly marked `[...]`. (e) is still beyond the
2,600-char ceiling — bounded-budget by design, and it now says so.
Also: total context ceiling (`_DEFAULT_MAX_CHARS` 16000, whole-block drop) and
`toIntegerOrNull` on the recital sort (it was a lexicographic string sort).

### 2c. Seed-downgrade hazard — closed

This repo ships `SEED_VERSION = 2026-07-24-r291-fullseed`; the live Aura graph
is `2026-08-08-r323-annex-sections`, seeded by the RAG repo. **The boot hook
re-seeds on ANY mismatch without checking which side is newer**, so booting
this repo with auto-seed ON would have silently downgraded production's graph
(losing section-aware annex items + the SubPoint layer). The seeder succeeds,
`/healthz/graph` still reports ok, answers just get worse.

`.env.example` now pins `NEO4J_AUTO_SEED=0`; hard rule **#12**.

### 2d. CLAUDE.md — 764 KB → 28.6 KB

Adapted from the RAG repo's `/doctor` rewrite, but **re-verified**, not copied.
Log moved verbatim to `docs/ROUNDS.md`: 114/114 round headings, word accounting
106,651 → 4,065 + 105,586.

Claims that transferred (all re-measured here): 126 refs, 131 KB entries,
KB_VERSION v18, Practice ×8 / AnnexIII ×8 / Phase ×4, 68 definitions, BM25 345
docs, xrefs 149 core / 249 full, tree 1,412 nodes, and the **full 476 davidath
baseline byte-identical**.

Claims CORRECTED for this repo: kg_context runs **3** Cypher shapes not 14 (the
RAG repo's "reads SubPoint / Practice / OperatorRole / LifecyclePhase" is FALSE
here); models are **sonnet-5 / opus-5** not 4-6 / 4-8; `PHASE_REGISTRY` has 0
`superseded_by` and `ROLE_SMALL_MID_CAP` does not exist — both CORRECT for the
pre-Omnibus pin, and the R25/R70/R98 notes claiming otherwise are STALE.

### 2e. Deliberately NOT ported

* **Article 6(3) both-limbs (`777e0f4`) and Art 53(2) narrowing (`1b0c8b4`).**
  This repo has **zero** Art 6(3) derogation code, so the wrong-law defect
  cannot occur — porting the fix would ADD the buggy feature. Verified live:
  "Is an AI system that screens and ranks job applicants high-risk?" already
  answers "high-risk … Annex III, point 4(a)".
* `fria_evaluator.py`, the Cappelli `retrieval_stack` role-boosting (the audit
  found it legally inverted — provider and importer both return 1.25), and
  `a692ffb` "wire the unread graph layers" (a feature, out of a
  correctness-only scope).
* **The RAG repo's `kg_context.py` wholesale.** This repo's is SAFER in two
  respects a "take theirs" resolution silently reverts: it routes both fetchers
  through `_bounded_execute_read` (the R294 budget + breaker, which the RAG
  version bypasses at 4 direct `execute_read` sites) and it raises
  `REGENOLD_KG_MAX_UNITS` to 70 (the R318 fix for Article 3's 68 definitions).
* `tests/test_r321_review_fixes.py` — three classes REMOVED (they pin
  `fria_evaluator`, the `art6_3_derogated` risk level, and
  `REGENOLD_LIVE_SENTENCE_CAP`, none of which exist here). 10 permanently-red
  tests would mask a real regression in the failure-set A/B. Restore from
  `6d7a3e1` / `777e0f4` / `2568bb3` if those features are ever ported.

---

## 3. The frontier analysis (the valuable part)

### 3a. Attribution — which mechanism puts wrong refs on the wire

Every one of the 97 judged-wrong refs across the 100 recorded July-7 **easy**
rows, attributed to a structural cause, counterfactual run for each:

| cause | wrong removed | correct lost | ratio |
| --- | --- | --- | --- |
| **parent alongside its own sub-point** | **9** | **1** | **9.0:1** |
| everything at rank 4+ | 17 | 14 | 1.2:1 |
| ref named in the prose (Component D) | 79 | 145 | 0.5:1 |
| the ref is itself a sub-point | 5 | 28 | 0.2:1 |

Only the first is positive. The third is **prose-driven pruning measuring dead
for the third time** (R298/R302 said 86% of wrong refs are described in the
prose; here 81%).

Wrong-rate by rank: **1 → 0.14, 2 → 0.42, 3 → 0.53, 5 → 0.88.**
Refs-per-row vs pass: **1 → 0.88, 2 → 0.54, 3 → 0.05, 4+ → 0.06**, with 41 of
100 rows at exactly 3 (the QA budget).

### 3b. ⭐ THE RANKER IS DEAD — the most reusable result of the round

"Work the RANKER, not the trimmer" has been the standing lesson since the five
trimming families died. AUC for separating CORRECT from WRONG refs (n=273):

| signal | AUC | | signal | AUC |
| --- | --- | --- | --- | --- |
| **rank** (engine's own order) | **0.703** | | described_chars | 0.613 |
| lex_ans (IDF coverage) | 0.641 | | q_kb_overlap | 0.608 |
| n_mentions | 0.625 | | is_subpoint | 0.554 |
| | | | parent_of_cited_sub | 0.544 |

**No combination beats rank alone** — ALL 0.696, rank+lex+desc 0.701,
rank+lex 0.692. The signals are correlated, not complementary. Same instrument
that killed neural NLI (0.585 vs the free lexical scorer's 0.749). Rank-1 is
already **86%** right.

**Therefore: selection is close to exhausted.** The oracle is +0.215 Ref Strict
/ +0.229 Ref Conciseness; the one surviving lever captures ~8% of it. The rest
is not reachable by choosing better among what is generated — it has to be
attacked at **GENERATION** (retrieval + the Stage-2 grounding block).

### 3c. Parent-collapse — shipped, default OFF

`REGENOLD_PARENT_COLLAPSE`. Drops a bare head when its own sub-point is cited.
Runs LAST (`_reemit_parents_for_subpoints` and Component D both ADD heads).

```
precision 0.6960 -> 0.7245  (+0.0285)
recall    0.9007 -> 0.8973  (-0.0033)
F1        0.7579 -> 0.7756  (+0.0177)
passing   41 -> 46          8 rows change, 0 flip pass->fail
```

**Why OFF:** hard rule #8 says a reference change must drop ZERO gold. This
drops ONE across 273 — `rg_032`, `Article 6` beside `Article 6.3` (general rule
+ its derogation, both load-bearing; R274 pins the pair). I tried to spare it:
a solo-mention heuristic scores it **INVERTED** against the nine wins, and §3b
says no feature decides it. So it is a trade, and `easyhard_ab` decides — not a
bench number.

⚠ **davidath CANNOT gate it.** `evals/bench/metrics.py` projects predictions
through `article_heads()`, so `{Article 6.3, Article 6}` and `{Article 6.3}`
are the SAME head set. Confirmed empirically: the full 476 is byte-identical
with the flag ON. That is also why it is safe under hard rule #7 by
construction, and why R87-C was free to add the head at all.

---

## 4. Live infrastructure — verified working

* **Aura `0644b854`** — DNS resolves, connects, seed
  `2026-08-08-r323-annex-sections`, kb `2024.1689.v18`, **1758 nodes / 1979
  edges** across 18 labels (Article 113, Annex 13, Paragraph 658, Point 421,
  SubPoint 37, Recital 180, Definition 68, …).
* **7 VECTOR indexes, all ONLINE and fully populated (1,490 embeddings)** plus
  `ft_provision_prose` FULLTEXT. `grep -rn 'db.index.vector' app/` → **0
  consumers**. Largest built-but-unwired capability.
* **Local wrapper** `127.0.0.1:8000` up and authenticated. Stage-2 lands on
  **`claude-opus-5`**.
* `Article.number` is a **STRING** — `{number: 3}` matches nothing, `{number:
  '3'}` and `{id: 'article_3'}` work. Any `ORDER BY` must cast.
* Semantic layer current: embeddings `is_available()` True with **0** asset SHA
  mismatches; turboquant enabled with its staleness guard passing.

---

## 5. Gates at `ca59ad8`

| gate | result |
| --- | --- |
| davidath 476 | Ans Loose 0.1884 / **Ans Strict 0.3545** / Ans Conc 0.6143 / **Ref Loose 0.5971** / **Ref Strict 0.4748** / Ref Conc 0.4319 / Tone 1.0 / multi-turn 20/20 |
| davidath 476, `PARENT_COLLAPSE=1` | **byte-identical** (head-grain invariant) |
| davidath QA 137 | 0.1407 / 0.4072 / 0.1961 / 0.8394 / 0.5536 / 0.4390 / 1.0 |
| `evals.regenold.runner` | **255/255**, RISK_F1 macro 1.00, 28/28 categories |
| OOS probe (`--oos-suite all`) | **49/51, 0 scope leaks** (2 known `adjacent_eu` soft fails) |
| full suite, failure SET in place | **55 = 55 vs baseline, 0 introduced, 0 fixed** |
| recall guard | **0 refs dropped / 0 added** across 100 real recorded answers |
| drift canary | exit 0, no legal-version drift |
| live E2E | 5/5 answered, wrapper + Aura healthy |

⚠ Judge the suite by the failure **SET**, never the count, and diff against a
baseline checked out **in place** (`git stash`) — a worktree has no `.env` and
the denoiser / topic-filter / safety-gate cluster changes behaviour on
`GROQ_API_KEY`.

---

## 6. How to reproduce the in-flight hard run

Env launcher (evals do NOT load dotenv; the RAG `.env` must not be copied here):
`scratchpad/run_hard.sh` — or inline:

```bash
export NEO4J_AUTO_SEED=0                 # hard rule #12, MUST come first
export NEO4J_URI=... NEO4J_USERNAME=neo4j NEO4J_PASSWORD=...
export REGENOLD_GRAPH_BACKEND=neo4j
export OPENAI_API_BASE=http://127.0.0.1:8000/v1   # LOCAL, not the CF tunnel
export OPENAI_API_KEY=dummy P2P_GRAPH_RAG_PROVIDER=openai_wrapper
export P2P_REGENOLD_API_KEY=... GROQ_API_KEY=... GEMINI_API_KEY=... MISTRAL_API_KEY=...
unset P2P_GRAPH_RAG_API_KEY               # enables an Anthropic path a test expects off

py -3.12 -m evals.regenold.run_official_batch --label r325-hard --mode hard
py -3.12 -m evals.judge.grounded \
    --sidecar evals/bench/results/official-r325-hard-hard.ckpt.jsonl \
    --label r325-hard --model claude-sonnet-5 --provider wrapper \
    --timeout 120 --concurrency 3
```

Timing probe (3 rows): tone 1.0, refs 2.33/row, **stage2 `claude-opus-5`**,
p50 18.2 s, `pushback_conceded_rate 0.0000`. ~20 s/row ⇒ ~37 min for 111.

**Why one arm and not an A/B:** Stage-2 is non-deterministic and this repo has
measured two runs with an IDENTICAL baseline arm changing 20/40 rows' refs and
sign-flipping all three reference axes. The parent-collapse is a deterministic
post-transform, so measure it OFFLINE on the resulting sidecar (zero variance)
— strictly better than a live A/B.

---

## 7. Open, ranked

1. **Grade the hard run** with `evals.judge.grounded`, then apply the
   parent-collapse offline to the same sidecar. One run answers both: the
   missing graded-turn baseline AND whether the collapse helps where it counts.
2. **Attack GENERATION.** §3b closed selection. Why does a 3-ref answer name a
   wrong provision **53% of the time at rank 3**? Retrieval + the Stage-2
   grounding block.
3. **Fix the judge** before trusting any further answer number — 8 of 22 answer
   failures on the easy batch are labelled "truncated" and **all 8 are false
   positives** (the content called missing is the answer's last sentence; zero
   of 100 answers lack terminal punctuation; fail rows median 1698 chars vs
   pass 1096). `evals/judge/legal_v2.py` already has the quote-or-retract rule.
4. **The Neo4j vector layer** — 1,490 embeddings, 0 consumers.
5. **Watch conciseness** — answers are +41% longer than the graded July-7 ones,
   on the one axis the official scorecard says we lead.

## 8. Do NOT re-propose

Everything in CLAUDE.md's "Do not re-propose", plus this round's additions: a
cheap **lexical re-ranker** (§3b), **prose-driven ref pruning** (third
measurement, 0.5:1), and **positional/top-N clamps** (1.2:1 here, and R142.1
lost a live pairwise 11-0).
