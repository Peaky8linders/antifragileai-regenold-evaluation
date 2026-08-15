# R338 — live evaluation on Opus 4.8, with the Stage-2 system prompt delivered for the first time

**Date** 2026-08-15 · **Code** `r338-gemini-review-fixes` (= `4d72ff3` + R338) ·
**Path** local app on `:8100` → `provider=openai_wrapper` → cloudflared tunnel
(`wrapper.antifragile-ai.net`) → Claude Max → **`claude-opus-4-8`** ·
**Graph** Neo4j Aura live, seed `2026-08-08-r323-annex-sections`, 1786 nodes / 2076 edges,
`NEO4J_AUTO_SEED=0` (hard rule #12) · **Artifacts** `.evalout/r118/live_r338-opus48.json`,
`evals/bench/results/graphrag-bench-r338-opus48-graphrag.json`

## 0. The configuration change that made this run different

`WRAPPER_FORWARD_SYSTEM_PROMPT=1` is now set on the wrapper service, so the Stage-2 **system**
prompt reaches the model for the first time. Root cause of the long-standing drop:
`claude_agent_sdk 0.2.82` types `ClaudeAgentOptions.system_prompt` as
`str | SystemPromptPreset | SystemPromptFile | None`, and the wrapper was passing
`{"type": "text", "text": ...}` — not a valid `SystemPromptPreset` — so the SDK discarded it
silently. A plain `str` is honoured.

Verified end-to-end with a sentinel probe on `claude-opus-4-8`:

| path | system slot obeyed |
| --- | --- |
| `127.0.0.1:8000` before the change | **False** |
| `127.0.0.1:8000` after `.env` + `nssm restart` | **True** |
| `https://wrapper.antifragile-ai.net/v1` (through the tunnel) | **True** |

⚠ This is **answer-changing**: `ANSWER_GENERATE_SYSTEM` (~12.8K tokens) is now delivered on every
Stage-2 call. Its effect is **not** isolated in this run — see §4 for why an A/B here would have
been nearly powerless anyway.

---

## 1. The headline finding: Stage-2 reaches ~15% of answers

`stage2_polish` landed on **3 of 20** Antifragile rows and **1 of 10** medtech multi-turn rows.
Cache hits were **0/20** and **0/10**, so this is real behaviour and not a warm `_ENGINE_CACHE`.

| row band | n | what served the answer |
| --- | --- | --- |
| < 150 ms | 5 | pure deterministic assembly — no LLM call at all |
| 150 ms – 1.5 s | 5 | deterministic + light work |
| > 1.5 s | 10 | LLM ran; **only 3 kept a Stage-2 polish** |

The cause is **deliberate and evidence-backed**, not a defect. Two gates bypass Stage-2:

* `_graph_rag_impl.py:8222` — `_curated_stage2_skip_enabled()` (`REGENOLD_CURATED_STAGE2_SKIP`,
  default **ON**) × `_is_curated_authoritative_intercept(resolved_q)`, recording
  `stage2_skipped_curated_authoritative`.
* `_graph_rag_impl.py:8232` — the R275 Article 3 definitional skip, whose own comment records the
  measurement: *"live Stage-2 (Opus) paraphrases it and non-deterministically drops the operative
  clause (the expert failed Q8 for dropping the AI-system …)"*.

**So the answer to "are all stages used as intended?" is: yes — and the intent is that Stage-2 does
not run on most of this suite.** The consequence matters more than the number:

> The Antifragile suite is **structurally near-blind to any Stage-2 change** — model tier, system
> prompt, grounding block, prompt wording. Measuring an Opus-4.8 or prompt change against it can
> move at most 3 of 20 rows. This is the same instrument-trap shape CLAUDE.md retired davidath for,
> arriving from the other direction: not a harness that disables Stage-2, but a *product* that
> bypasses it.

Evidence that the deterministic path is often the *better* answer: the graded question `rg_001`
("does technical documentation require hardware specifications?") is served in **1.7 s with no LLM**
and returns the correct answer citing **Annex IV point 1(e)** and **2(c)** — the exact sub-points the
reverted Gemini prompt sentence omitted.

---

## 2. Antifragile expert-review suite (20 rows, 38 flagged mistakes)

| axis | R318 (2026-08-07) | R338 Opus 4.8 | Δ |
| --- | --- | --- | --- |
| ans_loose | 0.3885 | 0.3888 | +0.0003 |
| ans_strict | 0.7187 | 0.6285 | −0.0902 |
| ans_conciseness | 0.4296 | **0.5321** | **+0.1025** |
| ref_loose | 0.9417 | 0.9292 | −0.0125 |
| ref_strict | 0.9042 | 0.8674 | −0.0368 |
| ref_conciseness | 0.8558 | 0.7535 | −0.1023 |
| **ref_subpoint_loose** | 0.5500 | **0.6875** | **+0.1375** |
| **ref_subpoint_strict** | 0.5141 | **0.6019** | **+0.0878** |
| keyword_recall | 0.8252 | 0.7583 | −0.0669 |
| regulatory_tone | 1.0000 | 1.0000 | 0 |
| mistakes resolved | 32/37 | 28/38 | see below |
| latency p50 | 7064 ms | **3221 ms** | **−54%** |

⚠ **This is NOT a controlled A/B.** R318 → R338 spans ~20 rounds of code change *plus* the
system-prompt flip *plus* an unknown R318 provider config. Read it as "the system on 2026-08-07 vs
the system today", never as the effect of any one change.

**Sub-point precision is the clear win** (+0.1375 / +0.0878), consistent with what R333/R337 were
built to do, and measured here on gold that actually carries sub-points — which
`dynamic_ab`'s probe pool (0% leaf-grained) structurally cannot show.

### The mistake regression is real, and it is on the deterministic path

Re-scoring **R318's stored answers with today's resolver** puts both runs on one ruler:

```
R318 answers, TODAY resolver : 33 / 38   (0.8684)
R338 answers, TODAY resolver : 28 / 38   (0.7368)
```

So −5 is a genuine regression, not a ruler artefact. It localises to exactly three rows, **none of
which runs Stage-2**:

| row | R318 | R338 | what was lost |
| --- | --- | --- | --- |
| `q03` "definition of high risk" | 3/3 | 1/3 | stopped stating the Art 6(1)(b) third-party conformity route and the Art 6(3) carve-outs. **Refs identical** — the answer text lost content. |
| `q04` "which sectors are high-risk" | 2/2 | 1/2 | stopped covering the Annex I product-safety route. **Refs identical.** |
| `q14` X-ray medical device | 2/2 | 0/2 | refs went `[Art 6, Art 43, Annex I, **Art 31, Annex VII**]` → `[Art 6, Art 43, Annex I, **Art 5, Art 9, Art 10, Art 11, Art 12, Art 13**]`. It **dropped the two precise refs** (notified bodies; conformity based on QMS) and added a generic Chapter-III dump plus an irrelevant Article 5. |

### Hypothesis tested and REFUTED: it is not the BM25 corpus change

Review finding [I1] predicted exactly this shape — `938933a` grew the BM25 corpus 345 → 373 docs
mid-corpus, shifting IDF and `avg_doc_len` so the whole corpus re-ranks, with 9/110 official-batch
rows losing a previously-retrieved provision. Tested directly by re-running the three regressed rows
against a second app instance with `REGENOLD_ONTOLOGY_RISK_DOCS=0`:

| row | ON (default) | OFF |
| --- | --- | --- |
| q03 | 1/3 | **0/3** (worse; refs also lost `Annex I`) |
| q04 | 1/2 | 1/2 (same) |
| q14 | 0/2 | 0/2 (same) |

**Turning it off does not recover the regression and makes q03 worse.** Two conclusions: the cause
lies elsewhere in the R318→R338 span and needs a bisect; and the owed [I1] gate now has its first
live evidence pointing at **keeping the default ON**.

---

## 3. Medtech and GraphRAG

**Medtech multi-turn** (10 scenarios × 3 turns): ref_loose 0.4204, ref_strict 0.2855,
keyword_recall 0.4444, tone 1.0, **coherence_rate 0.2222**, 1 hard error.

* ⚠ `mt_med_07` failed with **HTTP 422 `regenold_invalid_input` — "Each message content is limited to
  4000 characters"**. A legitimate multi-turn medtech scenario is rejected by an input-validation
  cap. Before R338 this class of failure scored 0.0 across eight axes and read as a quality collapse;
  it is now recorded as an error. The cap itself is unreviewed and should be raised or the runner
  should chunk.
* Coherence at 0.22 across 3-turn scenarios is the weakest number in this report and is not
  explained here.

**GraphRAG benchmark** (40 rows, 0 HTTP failures): Ref Loose 0.8215, Ref Strict 0.6428,
Ref Conciseness 0.5209, keyword recall 0.5371, tone 1.0, refusal 0.0, latency p50 831 ms / p95
7574 ms.

⚠ **The graphrag sidecar records no Stage-2 provenance** — `stage2_model` is absent on all 40 rows —
so the Stage-2 rate is **unmeasurable** from this artefact. The p95 of 7574 ms proves the LLM ran on
some rows. This is the same gap [I7] fixed in the two `evals/bench` runners; `run_graphrag_benchmark`
was out of that scope and needs the same treatment.

### Over-citation dominates the worst rows

| row | gold | predicted |
| --- | --- | --- |
| `gt_06` minimal_risk | *(none — correctly cites nothing)* | Article 5, Article 6, Article 50 |
| `ng_10` bias_mitigation | Article 10, Article 15 | Art 10, **55**, 9, **52**, 13, **93**, **27** |
| `med_2` medtech_qms | Article 17, Article 43 | Article 6.2 *(under-retrieval)* |

`gt_06` is the sharpest: a minimal-risk question whose gold is the **empty set** draws three
citations. This is CLAUDE.md's standing "over-citation is the whole remaining gap" finding,
reproduced live.

---

## 4. Verified legal errors in live output

Both checked against the repo's own pin via `get_provision_text`, never from memory.

1. **Article 27 misattributed.** On a hospital-transcription scenario the system answered
   *"Article 27 requires the deployer to inform the provider of any serious incident or
   malfunction"*. `get_provision_text("Article 27")` is 2,837 chars, is the **Fundamental Rights
   Impact Assessment**, and contains **no** occurrence of "serious incident". The deployer duty is
   **Article 26(5)**: *"Where deployers have identified a serious incident, they shall also
   immediately inform first the provider, and then the importer or distributor and the relevant
   market surveillance authorities"*. Same defect family as review finding [I11].
2. **Article 52 cited where Article 51 belongs.** `q01` ("what risk categories are provided?") cites
   `Article 52` — the *notification procedure* for GPAI with systemic risk — while the classification
   rule the question needs is **Article 51**. Gold expects 51.

Also seen on the Article 27 row: `noise_suppress_dropped=Article 6,Article 6.1` on a question that
asks *"is this high-risk"* — Article 6 is the classification rule. Worth a targeted look.

---

## 5. What to do next, ranked

1. **Bisect the q03/q04/q14 regression** across R318→R338. It is 5 of 38 expert-flagged mistakes,
   on the deterministic path, with refs unchanged on two of the three rows — so it is an
   answer-*assembly* change, not a retrieval change. `REGENOLD_ONTOLOGY_RISK_DOCS` is already
   excluded.
2. **Give `run_graphrag_benchmark` the [I7] treatment** — resolved provider, Stage-2 model and
   per-row `stage2_landed` in the artefact. Right now it cannot answer "did Stage-2 run?".
3. **Stop grading Stage-2 changes on the Antifragile suite.** It can move at most 3 of 20 rows.
   Build (or select) a probe set where the curated intercept does *not* fire, or the next prompt/model
   decision will be made on an instrument that cannot see it.
4. **Attack `gt_06`-class over-citation** — a minimal-risk question whose gold is empty drawing three
   refs is the cleanest available handle on Ref Strict / Ref Conciseness, the two axes that are the
   whole competitive gap.
5. **Raise or chunk the 4000-char per-message cap** that rejects `mt_med_07`.
6. **A/B the system prompt properly**, on a suite where Stage-2 actually fires. Today's flip is
   unmeasured, and on this suite it could only have touched 3 rows.
7. **Investigate medtech multi-turn coherence at 0.22.**

## 6. What this run does NOT establish

* The effect of `WRAPPER_FORWARD_SYSTEM_PROMPT=1`. Unmeasured, and near-unmeasurable here.
* The effect of Opus 4.8 versus any other tier. No comparison arm was run.
* Any causal reading of the R318 → R338 axis table beyond the three localised rows.
* The Stage-2 rate on the GraphRAG benchmark.
