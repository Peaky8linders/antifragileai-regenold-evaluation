# R325 — correctness sync, CLAUDE.md doctor, and the frontier analysis

**2026-08-09 · `ca59ad8` (pushed to `origin/main`)**

Collated report for the session. Three deliverables: bring the sibling RAG
repo's correctness fixes across without losing this repo's reason to exist,
adapt its `/doctor` CLAUDE.md honestly, and then attack the frontier gap with
measurement rather than intuition.

Companion checkpoint (reproduction steps, env, handoff):
[`.planning/R325-CHECKPOINT.md`](../../.planning/R325-CHECKPOINT.md).

---

## Executive summary

| | |
| --- | --- |
| **Shipped** | 9 foreign-citation leak shapes closed · kg_context enumeration fix · seed-downgrade hazard closed · CLAUDE.md 764 KB → 28.6 KB · parent-collapse (default OFF) |
| **Critical defect found and fixed** | GDPR Article 5 was reaching the wire as **AI Act Article 5** (prohibited practices) — wire-legal, so no validator could catch it |
| **Most valuable output** | A **negative** result: a cheap lexical re-ranker is dead. No feature combination beats the engine's own emission order (AUC 0.703). Selection is close to exhausted. |
| **Regression cost** | Zero. Every gate byte-identical; full-suite failure SET 55 = 55. |
| **Open #1** | The graded **pushback turn** — never measured. In flight as a 43-request stratified sample. |

---

## 1. Repo topology (the thing that makes this round non-obvious)

| repo | role |
| --- | --- |
| `antifragileai-regenold-evaluation` (**this**) | re-evaluation surface, the graded July-7 lineage. Deploys nowhere. |
| `regenold-eu-ai-act-rag` | deploys to production. Its own round line. |

Merge base `c0799df`; the RAG repo is 47 commits ahead (R319→R324).

> **`git merge parent/main` silently DELETES 29 files** — including the entire
> July-7 graded batch (`_official_batch_20260707.json`, 110 questions,
> `evaluator_batch_july7.py`, `run_official_batch.py`, `july7_difficulty.py`)
> and `query_expansion.py`.

Not a hypothesis: the files existed at the merge base and the RAG repo deleted
them afterwards, so git applies a **clean delete** — no conflict, no marker, no
warning. Verified by materialising the merge tree and counting survivors (0).
Hence the operator's call to **cherry-pick**, which is what shipped.

Round numbers also collide — both repos have an "R318"/"R319" and they are
different work.

---

## 2. Correctness fixes

### 2.1 Foreign-citation leak — nine shapes, all closed

Reproduced **here first**, on this repo's own extractor:

```python
_add_prose_named_refs(['Article 27'],
    "...EU Charter Art. 21 ... GDPR Art. 5 ... GDPR Art. 35 DPIA...")
# -> ['Article 27', 'Article 21', 'Article 5']
```

GDPR Article 5 promoted onto the wire as **AI Act Article 5 — prohibited
practices**. This is the worst defect class the codebase can ship: a
confidently-wrong legal claim (hard rule #4) in a wire-legal shape (hard rule
#1), so the `ARTICLE_EXISTENCE` lint (hard rule #5) *provably* cannot catch it
— Articles 5, 21, 22, 30 and 35 all exist in the Act.

| shape | before | after |
| --- | --- | --- |
| `GDPR Art. 5` (prefix) | leaks | guarded |
| `EU Charter Art. 21` | leaks | guarded |
| `Article 35 GDPR` (bare postpositive) | leaks | guarded |
| `Article 22 GDPR` | leaks | guarded |
| `Article 10, …clause…, of Regulation (EU) No 1025/2012` | leaks | guarded |
| `Article 6(1), …clause…, of Regulation (EU) 2016/679` | leaks | guarded |
| `Article 5 of Regulation 2016/679` (bare, no parenthetical) | leaks | guarded |
| `Regulation (EU) No 1025/2012, Article 10` (behind) | leaks | guarded |
| `Article 30 of Regulation (EC) No 765/2008` (pre-2015 OJ) | leaks | guarded |

**Four controls preserved** — including the R142.1 shape (an AI Act sentence
*followed* by a GDPR sentence must keep its genuine Article 13).

The load-bearing half was not the regex. **Component D** — a second,
entirely unguarded prose→citation path in the route — re-added whatever the
guard dropped. That is why widening the guard measures *byte-identical on the
wire*: the fix was real and this path undid it. Now hard rule **#11**: there
are TWO prose→citation paths and both need the guard.

Supporting fixes: `_REG_NUMBER_FRAGMENT` as ONE shared definition of "a
numbered EU Regulation id" (two regexes for one concept, only one ever widened,
so the behind branch had **never fired**); behind window 24 → 48 chars (at 24
its own branch was structurally unreachable against a 30-char prefix form);
ahead window **bounded then widened** 56 → 160 (widening alone was measured to
suppress a genuine Article 13 — the R142.1 failure mode).

### 2.2 The graph was serving prohibitions without their scope

Measured against the live Aura instance **before** the fix:

```
render_kg_context(['Article 5'])
  ->  3 of the 8 Article 5(1) prohibited practices
      LOST: (a) subliminal  (b) vulnerability  (d) criminal-risk
            (e) facial scraping  (h) real-time RBI
      and NOTHING marked the truncation — the list read as complete
```

Article 5(1) is **4,701 chars** against a 900-char unit cap.

After: **7 of 8**, and the cut is explicitly marked `[...]`. (e) remains beyond
the 2,600-char ceiling — that is the bounded-budget design, and it now says so
rather than pretending the enumeration ended.

Also fixed: a total context ceiling (16,000 chars, enforced by dropping *whole*
trailing blocks — a half-rendered block reads as complete), and
`toIntegerOrNull` on the recital ordering, which was a lexicographic string
sort.

### 2.3 The seed-downgrade hazard

This repo ships `SEED_VERSION = 2026-07-24-r291-fullseed`. The live Aura graph
is `2026-08-08-r323-annex-sections`, seeded by the RAG repo, which production
uses.

**The boot hook re-seeds on ANY mismatch — it does not check which side is
newer.** So booting this repo with auto-seed on would have silently
*downgraded* production's graph, losing the section-aware annex items and the
SubPoint layer. The failure mode is invisible: the seeder succeeds,
`/healthz/graph` still reports ok, answers just quietly get worse.

`.env.example` now pins `NEO4J_AUTO_SEED=0` with the measurement that motivates
it; hard rule **#12**.

### 2.4 Deliberately NOT ported

* **Article 6(3) both-limbs (`777e0f4`), Art 53(2) narrowing (`1b0c8b4`).**
  This repo has **zero** Art 6(3) derogation code, so the wrong-law defect
  those fix cannot occur here — porting them would **add** the buggy feature.
  Verified live: *"Is an AI system that screens and ranks job applicants
  high-risk?"* already answers *"high-risk … Annex III, point 4(a)"*.
* `fria_evaluator.py`; the Cappelli `retrieval_stack` role-boosting (the audit
  found it legally inverted — provider and importer both return 1.25); and
  `a692ffb` "wire the unread graph layers" (a feature, out of scope).
* **The RAG repo's `kg_context.py` wholesale.** This repo's version is *safer*
  in two respects a "take theirs" resolution would silently revert: it routes
  both fetchers through `_bounded_execute_read` (the R294 budget + breaker,
  which the RAG version bypasses at four direct `execute_read` sites), and it
  raises `REGENOLD_KG_MAX_UNITS` to 70 — the R318 fix for Article 3's 68
  definitions.

---

## 3. CLAUDE.md — adapted, not copied

764 KB → **28.6 KB**. Round log moved verbatim to
[`docs/ROUNDS.md`](../ROUNDS.md): **114/114 headings**, word accounting
106,651 → 4,065 + 105,586.

The RAG repo's `/doctor` rewrite was the starting structure, but every
load-bearing claim was re-measured **here**, because the repos have diverged and
a verbatim copy would have documented code that does not exist.

**Transferred** (measured identical): 126 canonical refs · 131 KB entries ·
`KB_VERSION 2024.1689.v18` · Practice ×8 / AnnexIII ×8 / Phase ×4 · 68
definitions · BM25 345 docs · xrefs 149 core / 249 full · tree 1,412 nodes ·
and the **full 476 davidath baseline byte-identical**.

**Corrected for this repo:**

| claim | RAG repo | here |
| --- | --- | --- |
| kg_context Cypher shapes | 14 ("reads SubPoint / Practice / OperatorRole / LifecyclePhase") | **3** — that sentence is FALSE here |
| Stage-2 models | sonnet-4-6 / opus-4-8 | **sonnet-5 / opus-5** |
| `PHASE_REGISTRY` superseded / `ROLE_SMALL_MID_CAP` | — | **0 / absent**, and CORRECT for the pre-Omnibus pin. The R25/R70/R98 notes claiming Omnibus additions are STALE — do not "fix" the code to match them. |

**Added** (none of it in the RAG version): the two-repo topology + the silent
29-file deletion · hard rule #11 (two citation paths) · hard rule #12 + a Graph
section (seed hazard, the string-typed `number` trap, 1,490 embeddings with
zero consumers) · the July-7 result and the judge's length artefact · the
tail-padding analysis.

---

## 4. Live infrastructure — verified

| surface | state |
| --- | --- |
| Aura `0644b854` | connects; seed `2026-08-08-r323-annex-sections`, kb `v18`; **1758 nodes / 1979 edges**, 18 labels (Article 113, Annex 13, Paragraph 658, Point 421, SubPoint 37, Recital 180, Definition 68, …) |
| Vector layer | **7 VECTOR indexes, ONLINE, fully populated — 1,490 embeddings.** `grep -rn 'db.index.vector' app/` → **0 consumers**. Largest built-but-unwired capability. |
| Fulltext | `ft_provision_prose` ONLINE |
| Wrapper | `127.0.0.1:8000` authenticated; Stage-2 lands on **`claude-opus-5`** |
| Semantic layer | embeddings `is_available()` True, **0** asset SHA mismatches; turboquant enabled, staleness guard passing |
| Legal-version canary | exit 0, no drift from the pinned pre-Omnibus CELEX |

⚠ `Article.number` is a **STRING**. `MATCH (a:Article {number: 3})` returns
nothing; `{number: '3'}` and `{id: 'article_3'}` work. Any `ORDER BY` must cast
— an uncast sort ordered Article 3 as 1, 10-19, 2, 20-29, 3 … and at a 24-unit
cap dropped definitions 3(4)–3(8) (deployer / authrep / importer / distributor
/ operator).

### 4.1 What actually contributes — measured, not configured

"Configured" ≠ "consulted" ≠ "contributes". Measured on four representative
questions, deterministic path, live graph:

**Contributing**

| subsystem | contribution per request |
| --- | --- |
| **BM25** (345 docs) | the primary ranker; §5.2 shows its ordering is the best signal in the system (AUC 0.703) |
| **kg_context → Aura** | fires every request — **5,122–14,102 chars** of provision structure into Stage-2 |
| **embeddings index** (SVD, 919 sentences) | 5 hits/query, additive candidates |
| **turboquant dense** (277 docs) | 5 hits/query via `dense_top_k`; running the uncompressed NumPy fallback (`turboquant_available: False`, expected on Windows) |

**Built, seeded, and never read**

| dark surface | evidence |
| --- | --- |
| **7 Neo4j VECTOR indexes, 1,490 embeddings** | `grep -rn 'db.index.vector' app/` → **0 files** |
| **`ft_provision_prose` FULLTEXT index** | `grep -rn 'db.index.fulltext' app/` → **0 files** |
| **2-hop graph expand** | `REGENOLD_GRAPH_2HOP` **OFF by code default**. Forced on it works — 29 hop-1 + 5 hop-2 articles in **51 ms** — but R295 measured the fusion cap admitting ~**4 of 660** surfaced refs even when enabled. |
| **SubPoint / Practice / AnnexIIICategory / OperatorRole / LifecyclePhase** | seeded (37 / 8 / 8 / 5 / 4) but kg_context's 3 Cypher shapes read only Article/Annex → Paragraph/Point + Recital anchors. The RAG repo reads them via 14 shapes; this repo does not. |

The graph therefore serves as **Stage-2 context only, never retrieval** — the
deliberate R252 decision after graph-primary retrieval buried the operative
article behind a blunt risk-tier dump.

**Why this is the interesting finding, not trivia.** §5.2 shows selection is
exhausted: nothing re-orders BM25's output better than BM25 does. The dark
surfaces are *generation-side* levers, not more candidates to rank — the vector
and fulltext indexes would retrieve **different** provisions rather than
re-order the same ones, and the unread node layers (Practice, OperatorRole,
AnnexIIICategory) are precisely the structured context that would let Stage-2
attribute a duty to the right actor instead of over-citing. The largest
built-but-unused capability in the system points at the only remaining
direction.

⚠ **Method note.** First pass I recorded `hop2 = 0` and `turboquant = 0` and
nearly wrote both off as dead. Both were my error — the 2-hop result field is
`hop2_articles` (I read `refs`), and turboquant exposes `dense_top_k`, not
`query`. The "zero consumers" claims above are `grep` over `app/` and are
solid; a "returns nothing" claim needs the API checked first. This is the same
key-form trap CLAUDE.md already warns about, in a new costume.

---

## 5. The frontier analysis

The gap to frontier is **over-citation** — we win Ref Loose and keyword recall,
we lose Ref Strict and Ref Conciseness. An oracle dropping every non-gold ref
gains **Ref Strict +0.215 / Ref Conciseness +0.229** at unchanged recall.
Nothing had captured any of it, and five trimming families were already
measured dead.

### 5.1 Attribution — which mechanism puts wrong refs on the wire

All 97 judged-wrong refs across the 100 recorded July-7 rows, attributed to a
structural cause, with the counterfactual for each:

| cause | wrong removed | correct lost | ratio |
| --- | --- | --- | --- |
| **parent alongside its own sub-point** | **9** | **1** | **9.0 : 1** |
| everything at rank 4+ | 17 | 14 | 1.2 : 1 |
| ref named in the prose (Component D shape) | 79 | 145 | 0.5 : 1 |
| the ref is itself a sub-point | 5 | 28 | 0.2 : 1 |

Only the first is positive. The third is **prose-driven pruning measuring dead
for the third time** — R298/R302 found 86% of wrong refs are described in the
prose; here 81%.

```
wrong-rate by rank:      1 → 0.14   2 → 0.42   3 → 0.53   5 → 0.88
refs-per-row vs pass:    1 → 0.88   2 → 0.54   3 → 0.05   4+ → 0.06
```

41 of 100 rows sit at exactly 3 refs — the QA budget — and supply the bulk of
the failures.

### 5.2 ⭐ The ranker is dead — the most reusable result

"Work the RANKER, not the trimmer" has been the standing lesson since the five
trimming families died. Measured, it is also closed. AUC for separating CORRECT
from WRONG refs (n=273; 0.5 = coin flip):

| signal | AUC | | signal | AUC |
| --- | --- | --- | --- | --- |
| **rank** (engine's own order) | **0.703** | | described_chars | 0.613 |
| lex_ans (IDF coverage) | 0.641 | | q_kb_overlap | 0.608 |
| n_mentions | 0.625 | | is_subpoint | 0.554 |
| | | | parent_of_cited_sub | 0.544 |

**No combination beats rank alone** — all-features 0.696, rank+lex+desc 0.701,
rank+lex 0.692. The signals are correlated, not complementary. This is the same
instrument that killed neural NLI (0.585 against the free lexical scorer's
0.749), applied to the successor idea.

**Rank-1 is already 86% right.** So the engine orders well and nothing cheap
re-orders it better.

> **Selection is close to exhausted.** The remaining over-citation gap is not
> reachable by choosing better among what is generated. It has to be attacked
> at **GENERATION** — retrieval and the Stage-2 grounding block.

### 5.3 Parent-collapse — shipped, default OFF

`REGENOLD_PARENT_COLLAPSE`. Drops a bare head when one of its own sub-points is
already cited (`Article 50` + `Article 50.4` → `Article 50.4`). Runs **last** in
the reference pipeline, because `_reemit_parents_for_subpoints` and Component D
both *add* heads.

```
precision  0.6960 → 0.7245   (+0.0285)
recall     0.9007 → 0.8973   (−0.0033)
F1         0.7579 → 0.7756   (+0.0177)
passing    41 → 46           8 rows change · 0 flip pass→fail
```

**Why default OFF, stated plainly.** Hard rule #8 says a reference change must
drop **zero** gold and calls non-zero *"a rejection, not a trade-off"*. This
drops one across 273 — `rg_032`, `Article 6` beside `Article 6.3`: the general
high-risk rule next to its own derogation, where both are load-bearing and
which R274 already pins in `test_article_6_and_6_3_cited`. I tried to spare it
and could not: a solo-mention heuristic scores it **inverted** against the nine
wins, and §5.2 says no cheap feature decides the parent-vs-leaf question. So it
is a trade, and `easyhard_ab` decides it — not a bench number.

⚠ **davidath cannot gate this, structurally.** `evals/bench/metrics.py`
projects predictions through `article_heads()`, so `{Article 6.3, Article 6}`
and `{Article 6.3}` are the **same head set**. Confirmed empirically — the full
476 is byte-identical with the flag ON. That is also why it is safe under hard
rule #7 by construction, and why R87-C was free to add the head in the first
place. The effect exists only for a consumer scoring at **sub-point** grain:
the grounded judge, and the regenold gold.

---

## 6. Gates at `ca59ad8`

| gate | result |
| --- | --- |
| davidath 476 | Ans Loose 0.1884 · **Ans Strict 0.3545** · Ans Conc 0.6143 · **Ref Loose 0.5971** · **Ref Strict 0.4748** · Ref Conc 0.4319 · Tone 1.0 · multi-turn 20/20 |
| davidath 476 with `PARENT_COLLAPSE=1` | **byte-identical** (head-grain invariant) |
| davidath QA 137 | 0.1407 / 0.4072 / 0.1961 / 0.8394 / 0.5536 / 0.4390 / 1.0 |
| `evals.regenold.runner` | **255/255**, RISK_F1 macro 1.00, 28/28 categories |
| OOS probe (`--oos-suite all`) | **49/51, 0 scope leaks** (2 known `adjacent_eu` soft fails) |
| full suite, failure **SET** in place | **55 = 55**, 0 introduced, 0 fixed |
| recall guard | **0 refs dropped / 0 added** across 100 real recorded answers |
| new tests | +55 (24 foreign-citation, mutation-tested 14-red; 31 parent-collapse) |
| drift canary | exit 0 |
| live E2E | 5/5 answered, wrapper + Aura healthy, Stage-2 landing |

---

## 7. Method notes worth keeping

* **Two false alarms I generated, both caught by the repo's own rule.** I twice
  read a truncated `tail` as a regression — "10 new failures" (all in one
  cherry-picked test file, later removed as parent-only) and "3 caused by the
  flag" (the set diff showed 3 = 3). *Judge by the failure SET, never the
  count* exists for exactly this.
* **A `--limit 3` timing probe is not an extrapolation.** It predicted ~20 s/row;
  the real rate is ~72 s/row once Groq starts 429-ing the denoiser.
* **A background job that runs `git checkout` will collide with your edits.**
  One stashed an uncommitted file mid-session. Commit first.
* **A monitor whose grep matches the job's own header fires instantly.** Match
  a terminal marker, not a banner.
* **`ABSENT IS NOT ZERO` earned its place again** — `wrong_refs` looked empty
  at row level; it lives under `verdicts.reference_correctness`. A row-level
  `.get()` would have concluded there was no data to analyse.

---

## 8. Open, ranked

1. **The graded pushback turn.** In flight as a 43-request stratified sample
   (`run_hard_sample_r297 --frac 0.15` — 15.3% of the 281 HARD requests, 17
   multi-turn × 2 turns + 9 single-turn, all 5 difficulty categories). Then
   grade with `evals.judge.grounded`, and apply the parent-collapse **offline**
   to the same sidecar — one run answers both questions with zero generation
   variance.
2. **Attack generation — and the lever is already built and idle.** §5.2 closed
   selection; §4.1 shows **1,490 Neo4j embeddings across 7 VECTOR indexes and a
   FULLTEXT index with literally zero consumers**, plus five seeded node layers
   kg_context never reads. Cheapest decisive probe: measure what the vector
   layer retrieves that BM25 **misses** — if it surfaces gold BM25 never had,
   that is the generation-side fix; if it only re-orders the same set, it is
   another wash and should be recorded as one. Why does a 3-ref answer name a
   wrong provision **53% of the time at rank 3**?
3. **Fix the judge** before trusting any further answer number — 8 of 22 answer
   failures on the easy batch are labelled "truncated" and **all 8 are false
   positives** (the content called missing is the answer's last sentence; zero
   of 100 answers lack terminal punctuation; fail rows median 1,698 chars vs
   pass 1,096). `evals/judge/legal_v2.py` already has the quote-or-retract rule.
4. **The Neo4j vector layer** — 1,490 embeddings, zero consumers.
5. **Watch conciseness** — answers are +41% longer than the graded July-7 ones,
   on the one axis the official scorecard says we lead.

## 9. Do not re-propose

Everything in CLAUDE.md's list, plus this round's additions: a **cheap lexical
re-ranker** (§5.2), **prose-driven ref pruning** (third measurement, 0.5:1),
and **positional / top-N clamps** (1.2:1 here; R142.1 lost a live pairwise
11-0, p=0.001).
