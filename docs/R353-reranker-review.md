# R353 — deep review of the rerank stack + the R352 surviving hypothesis, shipped

**Date:** 2026-08-16 · **Method:** CR-skill adversarial review of the live
rerank stack (R340/R346/R347/R348/R350/R351), independent replication of the
R352 computation, exact gold-impact computation of the surviving hypothesis
before any engine code · **Status:** lever SHIPPED behind a flag, live A/B
pending quota

---

## 1. What was reviewed

`app/engines/cohere_rerank.py` (the whole module), the parse-level rerank
block in `app/engines/_graph_rag_impl.py` (R340/R350/R351 fork), the
pool-level rerank in `app/data/kb_search.py`, the judge machinery in
`evals/harness/dynamic_ab.py` (R349/R350 axes, fire check, bootstrap CI),
`evals/bench/metrics.py` (gold_dropped_head/exact, head projection), the
R334 cache-key drift guard, and the R352 write-up
(`docs/R352-annex-anchor-gap.md`).

## 2. R352 replicated independently — the numbers hold

The R352 precision table was re-derived from scratch over the current
297-row pool (no LLM, no sampling):

| provision | R352 claimed | replicated |
|---|---|---|
| `Art. 6` | 0% | **0%** (0 gained, 60 non-gold) |
| `Annex III` | 24% | **24%** (16/66) |
| `Annex I` | 10% | **11%** (8/74) |

The xref-only gold gap is real and concentrated in annexes (`Annex III`,
`Annex I`, `Annex IV`, `Annex VI/VII`, `Annex XI/XII`), on the most ordinary
questions in the pool ("Is a customer service chatbot high-risk?").
The broad triad fix is correctly refuted; **`Art. 6` is never gold on a
classification question** — the durable lesson (gold cites the list, not the
rule that points at the list) stays in `CLAUDE.md`'s do-not-re-propose list.

## 3. The surviving hypothesis, computed exactly (this round's lever)

The R352 §4 open candidate — *Annex III on the "is [ordinary software]
high-risk?" shape* — was fitted against the whole pool and its exact gold
impact computed BEFORE writing any engine code (the R352 doctrine):

* **Trigger:** yes/no auxiliary opening + a classification term
  (`high-risk` / `regulated` / `subject to the AI Act` / `fall under the
  high-risk classification`), excluding list/definition questions
  (`what|which|how`), obligation/technical-documentation questions
  (`require|specification|technical documentation`), prohibition questions
  (`prohibit|banned|illegal` — their gold is Art. 5), and the
  Annex-I/sector domains (medical, worker, LE, biometric, credit, GPAI,
  systemic risk, …).
* **Result over 297 rows:** fires on **11**; `Annex III` is
  gold-but-not-anchored on **7** (lr_spam_filter, lr_music_recommender,
  lr_chatbot, lr_translation, lr_image_generator, graphrag:med_6,
  live_answers:la_q46); **0 non-gold additions — 100% precision.** Every
  one of the 7 is a "no, and here is the list it is not on" question where
  the engine today retrieves neither `Annex III` nor the classification
  list.

**Shipped:** `app/engines/risk_classification.py` +
`REGENOLD_RISK_CLASS_ANNEX` (default OFF) wired into `_deterministic_parse`
as a RECALL SUPPLEMENT (appended after the keyword anchors, never prepended;
the R340 cross-encoder rerank decides its final position — the reranker is
the precision guard against an unseen trigger misfire). Multi-turn safe
(live turn extracted past the flatten marker). Registered in
`_engine_cache_key`; the R334 drift guard enforces it. 27 new tests pin the
trigger semantics, the parse wiring, gate-off byte-identity, and the cache
key. Full suite: **6574 passed, 0 failed.**

## 4. Real issues found (ranked, evidence-backed)

**#1 — R350.2's veto attribution is a correlation, not a measurement
(high).** The R350.2 arm differed from baseline in THREE levers at once
(rerank × KG-candidates × expansion); the veto was blamed on the KG pool
from R346's decomposition, which was measured on a different probe. The
KG-pool blame is plausible (it is the only arm with no clean measurement)
but the decisive isolation run — expansion-only, and rerank×expansion (the
composition with positive components) — has never been run. The decision
"KG stays OFF" is defensible as risk management but is not a measured
verdict.

**#2 — wire references are answer-driven; cut-level guarantees cannot close
generation-level vetoes (high — the structural finding).** The engine's
entity order (what R351's anchor tiering and the R340 rerank protect) feeds
the Stage-2 GROUNDING, but the WIRE reference set is
`(engine refs ∩ prose) ∪ Component-D prose refs` — i.e. what the LLM
writes. R350.2's la_q87 shows the chain: `Annex I` was in the branch's KG
pool (verbatim text in the grounding), yet Opus wrote "the Union
harmonisation legislation listed in notably the Medical Devices Regulation"
and `Annex I` never reached the wire. Consequence: any retrieval lever must
be judged at the wire (gold_dropped + judge axes), never at the entity
list; and R351's "additive at the cut" is necessary but not sufficient.

**#3 — `article_heads()` does not normalize short-form `Art.` (medium —
tooling footgun, not a metric bug).** `article_heads(['Art. 5'])` → `set()`;
only long-form `Article 5` resolves. The metrics use it correctly because
wire refs are canonicalized to long form before scoring, but any analysis
that compares raw parse entities (`Art. 5`) against gold (`Article 5`)
silently inflates "missing" — this hit my first R352 pass and likely
inflates every ad-hoc "missing refs" script in the repo. A normalizing
`parse_entity_heads()` alongside `article_heads()` would remove the trap.

**#4 — Cohere rerank is POINTWISE, so the R351 KG lever cannot reorder
anchors (medium — the R347 story oversells the ranking).** Adding neighbour
documents does not change the anchors' scores; the KG lever under R351 is
an ADDITION (neighbours fill slots after anchors), not a re-ranking. The
code documents this correctly in the R350 fork comment; the flag-table
language ("hybrid-RAG KG supplementation … ranks the keyword entities
TOGETHER with their neighbours") should say "addition" so nobody re-derives
a "promotion" A/B expecting a ranking effect.

**#5 — five serial Cohere calls per request when both gates are on
(known, unaddressed).** Counted in the R350 code comment: BM25 fallback per
expanded query + scoped pool exits + the parse-level call = up to 5 serial
calls with 6 s read timeouts, inside one request, against a 10-calls/min
Trial key. The A/B pacing math is off by ~5× at this shape. Needs a
request-scoped call budget before any multi-gate A/B at scale.

**#6 — `_pool_reasons(entities, pairs)` ignores its `references` argument
(low).** Harmless (reasons only ever annotate KG-supplemented docs), but
the signature misleads; the call site passes `entities` for nothing.

## 5. Where the reranker stands after this round

| lever | measurement |
|---|---|
| R340 rerank alone | R346: wash (gold 17→17) |
| Query expansion alone | R346: gold 17→14 (better), UNDERPOWERED at n=60 |
| Rerank × KG × expansion | R350 veto (25→27), R350.2 veto again (46→49) |
| R351 anchor tiering | fixed the cut-level displacement, merged |
| **R353 Annex III anchor** | **exact gold impact 7/0 (100% precision); live A/B pending** |

The reranker's genuinely new performance point this round is R353: the
deterministic trigger is the RECALL side (7 gold refs the parse never
fetches), and the cross-encoder is the PRECISION guard (it ranks `Annex III`
against the question and can demote it on a misfire). That division of
labour is the design the R352 computation validates.

**Scripts:** `scratch/verify_r352.py` (R352 replication), `scratch/verify_r352_final.py`
(trigger fit + exact impact), `scratch/r352_true_gaps.py` (the R353.1 gap
analysis), all reproducible, none needs network.

## 6. R353.1 — the TRUE retrieval gaps, with honest head normalisation

Review finding #3 made concrete: `parse_entity_head(s)` (NEW — `evals/bench/
metrics.py`) canonicalises BOTH the engine's short-form `Art. N` and the wire
long-form `Article N`, so parse-vs-gold comparisons stop reporting the
`Art.`/`Article` form difference as a false gap (`article_head` stays strict
per R327). Re-run of the R352-style missing-ref analysis over the 297-row
pool with the honest normaliser (`scratch/r352_true_gaps.py`):

| gold head | rows where gold-but-not-anchored | reachable via KG pool |
|---|---|---|
| `Article 6` | **31** | 0 |
| `Annex III` | **26** | 15 |
| `Article 50` | **18** | 0 |
| `Article 5` | **15** | 0 |
| `Annex I` | **12** | 4 |
| `Article 55` | **10** | 0 |
| `Article 43` | **9** | 0 |
| `Article 51` | **9** | 0 |
| `Annex IV` | **8** | 6 |

Shapes: `Art. 50` on chatbot/interaction questions (the R353 gain rows still
miss it — R353 closes 1 of their 3 gold heads); `Art. 5` on biometric-
categorisation shapes; `Art. 55` on FLOPs/systemic-risk (incl. a likely
`systemic-risk` hyphen-normalisation miss); `Art. 43` on conformity questions.
R352's refutation covers ADDING Art. 6 on the is/are/does-classification
trigger only — the 31 rows here are OTHER shapes ("what risk level applies",
"does the EU AI Act impose"), and any candidate trigger owes the same exact
gold-impact computation (R352 §5) before code.

## 7. Judge-bias caveat (pre-R350 numbers)

Any judge-axis number (ref_corr / cite_faith / ans_corr / ans_conc) measured
BEFORE the R350 harness fix is biased: the pre-R350 filter tested the verdict
STRING only, so a branch-arm HTTP timeout — which `legal_v2` returns as a real
`{"verdict": "fail", "evaluation_error": "empty_answer"}` — scored as the
branch LOSING the axis, and errored rows could masquerade as passes in the
fire check. Numbers from R346 and earlier on the judge axes are not comparable
to post-R350 numbers; quote them only with the caveat, or re-run. The
R353/R353.1 measurements use the post-R350 harness with the error-aware
`_scorable` filter.
