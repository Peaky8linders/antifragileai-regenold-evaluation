# R339 — Stage-2 was dead on every provider, and why; the two bypasses settled by measurement

**Date** 2026-08-15 · **Base** `f7f85ad` (R338 merged + deployed) ·
**Path** local app → `provider=openai_wrapper` → patched wrapper → Claude Max → **`claude-opus-4-8`**,
graph live on seed `2026-08-08-r323-annex-sections` ·
**Artifacts** `.evalout/r118/live_r339-A-bypass-ON.json`, `live_r339-B-bypass-OFF.json`

---

## 1. THE HEADLINE — enabling the system prompt silently killed Stage-2 everywhere

R338 enabled `WRAPPER_FORWARD_SYSTEM_PROMPT=1` on the Claude-Max wrapper so the Stage-2 **system**
prompt would stop being dropped. Verified at the time with a small sentinel probe, which passed.
It was the wrong probe.

**`claude_agent_sdk 0.2.82` passes a `str` system prompt INLINE INTO ARGV**
(`_internal/transport/subprocess_cli.py:229`):

```python
elif isinstance(self._options.system_prompt, str):
    cmd.extend(["--system-prompt", self._options.system_prompt])
```

Windows `CreateProcess` caps a command line at **32,767 characters**. This repo's
`ANSWER_GENERATE_SYSTEM` is **51,513 characters**. So every Stage-2 call failed at spawn — and the
SDK reported it as:

```
Claude Agent SDK error: Claude Code not found at: C:\Users\th3un\.local\bin\claude.exe
```

The binary is present and 265 MB. The *spawn* failed; the message names the wrong cause. That
mis-attribution is why it survived a wrapper restart and two rounds of probing.

**Bisected on the running wrapper, everything else held constant:**

| system prompt | result |
| --- | --- |
| 32,000 chars | **200 OK**, ~6.3 s |
| **32,768 chars** | **500**, ~0.3 s |
| 40,000 chars | 500, ~0.3 s |

Not `max_tokens` (6048 works), not total payload (12.5K system + 90K user works), not the tunnel,
not the model name. Only the system prompt's own length, at exactly the argv boundary.

### The blast radius was total and silent

* Every Stage-2 call → wrapper 500 → `groq_auto_fallback` (which fires **only** when the Claude-Max
  call already failed, `_graph_rag_impl.py:880`).
* Groq is at its **daily token cap** (`Limit 200000, Used 198784`), so `complex=True` questions got
  `429` → `stage2_failed_both_providers_deterministic_ship` → the deterministic answer shipped.
* Simple questions were rescued by Groq `gpt-oss-120b` — i.e. **answered by a different model on a
  compressed prompt** (`_shrink_user_for_groq`, `_get_groq_compressed_system_prompt`), which no
  artefact recorded.

⚠ **The primary provider's failure reason is never written to the reasoning trace.** Only the
fallback's outcome is (`groq_auto_fallback_success` / `groq_fallback_failed`). A reader of the trace
sees Groq succeeding and cannot tell that Claude was never reached. That is the single change that
would have caught this on day one.

### The fix — spill to a file, do not shorten

The SDK's own typed union already has the escape hatch (`subprocess_cli.py:234`):
`SystemPromptFile` is passed as `--system-prompt-file <path>`, by path, so argv never sees the text.
`src/claude_cli.py` now spills above `WRAPPER_SYSTEM_PROMPT_ARGV_LIMIT` (default **30,000**, leaving
~2.7K headroom for the rest of the command line) and unlinks the temp file in `finally`.

**Verified by nonce echo — the operator's "no truncation, no paraphrasing" requirement:**

| wrapper | 51.4K system prompt | nonce at HEAD | nonce at TAIL |
| --- | --- | --- | --- |
| patched | 200 OK ~6 s | **echoed exactly** | **echoed exactly** |
| unpatched | HTTP 500 | — | — |

A nonce placed at both ends is echoed verbatim, so the *entire* 51.4K system prompt reaches the
model. A sentinel that merely asks for obedience is NOT sufficient here — at 51K the model reads the
rule and then weighs it against the user's question, so obedience is a behavioural outcome while the
nonce tests delivery. Use the nonce.

---

## 2. Production was in the same hole, by a different route

Measured on the deployed `f7f85ad`:

```
stage2_model=claude-opus-5 complex=True
groq_fallback_failed: api_status_429 ... openai/gpt-oss-120b
stage2_failed_both_providers_deterministic_ship
```

Two independent causes, both of which must be fixed:

1. **Cloudflare Access.** `OPENAI_API_BASE` is unset on the service, so the code default
   `https://wrapper.antifragile-ai.net/v1` applies — correct. But `CF_ACCESS_CLIENT_ID` /
   `CF_ACCESS_CLIENT_SECRET` were unset, and `_resolve_cf_access_headers`
   (`openai_wrapper_provider.py:279-313`) **fail-softs to `{}`** on missing credentials. Measured:
   the tunnel returns **HTTP 401** (Cloudflare Access) without them. Fail-soft on a credential turns
   a misconfiguration into a total, silent loss of the primary provider.
2. **The argv bug above**, which would have bitten the moment Access started working.

Both are now addressed: the CF variables have been added to the Railway service (needs a container
restart to take effect — `deployment_id` must change), and the wrapper carries the file-spill fix.

---

## 3. THE TWO STAGE-2 BYPASSES — SETTLED, and they STAY ON

R338 found Stage-2 polish landing on only 3/20 Antifragile rows and named two deliberate gates:
`REGENOLD_CURATED_STAGE2_SKIP` (R144) and `REGENOLD_DEFINITIONAL_STAGE2_SKIP` (R275). The operator
asked for them to be settled properly rather than accepted on their own code comments.

They are now settled by **fresh measurement on the current configuration** — Opus 4.8, system prompt
delivered, Stage-2 actually working — not by the R275-era evidence.

Paired arms, Antifragile 20, same code, same wrapper, same graph, 0 errors both arms:

| axis | A: bypasses ON (shipped) | B: bypasses OFF | delta |
| --- | --- | --- | --- |
| **stage2_polish landed** | 9/20 | **19/20** | +10 |
| expert mistakes resolved | **34/38 (0.8947)** | **34/38 (0.8947)** | **0** |
| ans_conciseness | **0.5161** | 0.3535 | **−0.1626** |
| ans_f1 | **0.5927** | 0.5498 | −0.0429 |
| ans_loose | **0.4383** | 0.3940 | −0.0443 |
| ans_strict | 0.7113 | **0.7373** | +0.0260 |
| ref_loose | 0.9458 | 0.9458 | 0 |
| ref_strict | **0.9028** | 0.8349 | **−0.0679** |
| ref_conciseness | **0.8046** | 0.7056 | **−0.0990** |
| ref_subpoint_strict | **0.6152** | 0.5878 | −0.0274 |
| ref_subpoint_conciseness | **0.6461** | 0.5472 | **−0.0989** |
| keyword_recall | 0.8598 | **0.8736** | +0.0138 |
| regulatory_tone | 1.0 | 1.0 | 0 |
| latency p50 | **6,985 ms** | 17,067 ms | **+144%** |

**FIRE CHECK PASSED**: the lever moved `stage2_polish` 9 → 19 and latency p50 2.4×, so this is a
real measurement, not the inert-A/B trap.

**Verdict: keep both bypasses ON.** Turning them off buys `ans_strict +0.026` and
`keyword_recall +0.014`, and pays `ans_conciseness −0.163`, `ref_conciseness −0.099`,
`ref_subpoint_conciseness −0.099`, `ref_strict −0.068`, `ans_f1 −0.043` and **2.4× latency** —
while resolving *exactly the same* 34 of 38 expert-flagged mistakes. Answer-Conciseness is the one
axis the official scorecard says we lead, with zero headroom; arm B destroys it.

So the R275 comment's claim survives re-testing on a configuration it never saw. The deterministic
curated answers are not a shortcut around quality — on this gold they *are* the better answer, and
cheaper.

⚠ **Limitation, stated plainly:** n=20, one run per arm, no confidence interval. The conciseness
deltas (−0.16, −0.099) are large relative to anything seen between valid runs, and every
conciseness-family axis moves the same direction, which is what makes the verdict safe. The
single-axis moves (`ans_strict +0.026`, `keyword_recall +0.014`) are NOT resolved at this n and must
not be quoted as gains.

---

## 4. R338's "−5 mistake regression" was an artefact — RETRACTED

`docs/R338-live-opus48-antifragile-graphrag.md` reported expert-flagged mistakes falling
33/38 → 28/38 and localised it to q03/q04/q14. That measurement was taken while **Stage-2 was
completely dead** (the argv bug), so it compared a working system against a Stage-2-less one.

With Stage-2 restored: **34/38 (0.8947)** — better than the R318 baseline's 33/38 on the same
resolver. There is no regression. The three "regressed" rows were rows that had lost their polish.

Every axis in that report's R318↔R338 table is affected the same way and must not be quoted.
This is the instrument trap once more: the numbers were real, the *system* under measurement was
not the one we thought.

---

## 4b. LLM-JUDGE answer- and reference-correctness (the numbers R338 lacked)

`evals.judge.grounded`, `claude-sonnet-5` via the wrapper, both arms, n=20, 0 errors.

⚠ **Grounding provenance matters more than the numbers.** `grounded._prepare` falls back to
grounding answer-correctness on the answer's **own** `pred_refs` when a row has no independent gold —
which makes the axis self-graded and structurally unable to see "cited the wrong provision entirely".
`ANTIFRAGILE_GT` carries a synthesized `gold_answer` and `gold_refs` for all 20 rows, so the sidecar
was built with them. Verified in the output: `answer_grounding_source = gold_refs` on **20/20 rows**.
These numbers are independently grounded.

| axis | A: bypasses ON | B: bypasses OFF |
| --- | --- | --- |
| **answer_correctness** pass rate | 17/20 = **0.85** | 18/20 = **0.90** |
| mean factual score | 0.7741 | **0.8246** |
| **reference_correctness** pass rate | 10/20 = **0.50** | 7/20 = **0.35** |
| reference precision | **0.7935** | 0.7005 |
| reference recall | **0.9150** | 0.9107 |
| reference F1 | **0.8499** | 0.7919 |
| **citation_faithfulness** | **1.00** (20/20) | 0.95 (19/20) |

**This refines — and does not overturn — the §3 verdict.** Removing the bypasses buys a little
ANSWER completeness (+0.05 pass, +0.05 factual) and costs REFERENCE quality materially
(−0.15 pass, −0.093 precision, −0.058 F1) plus one citation-faithfulness failure. References are
where CLAUDE.md says the entire remaining competitive gap lives, and the metric arms already showed
conciseness and latency going the same way. **Keep the bypasses ON.**

### Judge remarks — arm A, every failing row

**9 of the 10 reference failures are over-citation.** This is CLAUDE.md's standing "over-citation is
the whole remaining gap" finding, now with the specific wrong ref named per row:

| row | axis | judge remark | wrong refs |
| --- | --- | --- | --- |
| q01 | reference | cited narrow derogation 6.3 instead of the operative 6(1)-(2); omitted Article 51 | `Article 6.3` |
| q07 | reference | over-citation of AI literacy as a guiding principle | `Article 4` |
| q10 | reference | over-citation of high-risk obligations beyond the definitional/role-shift provisions | `Article 16`, `Article 26` |
| q12 | reference | redundant parent-article citations alongside their own sub-provisions (not minimal) | `Article 5`, `Article 50` |
| q13 | reference | cited the Art 6(1) Annex I safety-component route instead of 6(2), the clause that actually makes Annex III systems high-risk | `Article 6.1` |
| q14 | reference | over-citation of a substantial-modification provision the question never raised | `Article 43.4` |
| q15 | reference | prohibition applied without evidence of inferring protected-class attributes | `Article 5.1.g` |
| q16 | reference | cited deployer transparency (Art 50) instead of GPAI systemic-risk classification | `Article 50.1/.2`, missing `51`, `55` |
| q18 | reference | over-citation of an inapplicable high-risk Annex III provision | `Annex III` |
| q20 | reference | over-citation of downstream obligations + a redundant duplicate + missing Annex I | `Article 6`, `14`, `72` |
| q02 | answer | misstates the social-scoring prohibition — drops the "unrelated context" prong | — |
| q05 | answer | omits the Article 50(4) deepfake disclosure obligation | — |
| q18 | answer | risk-classification claims unverifiable from the supplied text; omits the 50(4) text-publication limb | — |

Two structural patterns worth acting on, both distinct from the trimmer/ranker families CLAUDE.md
has already measured dead:

1. **Parent + own sub-point cited together** (q12, and q01/q13 in the inverse direction). This is
   exactly what `REGENOLD_PARENT_COLLAPSE` was built for and it is still **default OFF**. The judge
   now supplies independent evidence for it on a gold set that carries sub-points.
2. **Head-vs-sub-point mis-selection** (q01 cites 6.3 not 6(1)-(2); q13 cites 6.1 not 6.2). Not
   over-citation — *wrong* coordinate selection within the right article. A trimmer cannot fix this;
   it is a retrieval/grounding problem, consistent with CLAUDE.md's "attack GENERATION, not
   selection".

## 4c. `dynamic_ab` is the WRONG instrument for these two flags — measured

The audit measured how often each gate actually fires, per dataset:

| dataset | curated gate | definitional gate | either |
| --- | --- | --- | --- |
| Antifragile 20 | 10/20 | 1/20 | **11/20 (55%)** |
| GraphRAG benchmark 40 | 11/40 | 3/40 | 14/40 (35%) |
| Official batch 110 | 19/110 | 4/110 | 22/110 (20%) |
| **`probe_set` (dynamic_ab) 132** | **2/132** | **0/132** | **2/132 (1.5%)** |

So a `dynamic_ab` run on either flag would move ~2 of 132 rows and report a meaningless NULL — the
inert-A/B trap, arriving through the *probe pool* rather than the harness. The Antifragile set at a
55% fire rate is the correct instrument, which is why it was used.

⚠ Worse: the provider gate at `_graph_rag_impl.py:8181` returns **before** both bypass gates, so
under `provider=cli` neither flag is reachable at all. Any deterministic-arm A/B on them is inert by
construction.

## 4d. The Stage-2 grounding block was truncating provision text — FIXED

The operator's requirement is "Stage 2 gets the full context plus original user question, no
truncation or paraphrasing". Captured the real Stage-2 payload by spying on
`_OpenAIWrapperProvider.complete` while running the engine. The original question arrives
**verbatim** and the system prompt arrives **whole** — but the grounding did not.

**Localised:** `app/engines/semantic_layer.py` `_clip_clause`, called from `cross_reference_context`
with a hard-coded `_CROSS_REF_SNIPPET_CHARS = 240`. It renders the `CROSS-REFERENCED PROVISIONS`
block appended to the Stage-2 user message at `_graph_rag_impl.py:7514-7524`. The final line was
`return window.rstrip() + "…"` — a raw character cut whenever no clause boundary sat in the back
half of the window.

**Proven render-time, not stored data:**

| ref | stored (`get_provision_text`) | rendered to Stage-2 | `…` in the store? |
| --- | --- | --- | --- |
| Article 40 | 2,770 | **240** | no |
| Article 41 | 3,842 | **158** | no |
| Article 74 | 6,977 | **241** | no |

**A second, worse defect in the same function:** Article 41 was clipped to **158 of 3,873 chars — a
96% loss — with no marker at all**, ending `"...or, as applicable,"`, indistinguishable from a
complete provision. The mid-word cut was at least visible; this one was silent. It is precisely
CLAUDE.md's own rule: *a ceiling that falls back to a smaller limit is a switch, not a ceiling.*

**Fix:** budget raised to 20,000 (above the largest reachable node, `art_3` at 17,079) so nothing
truncates under the code default; new `REGENOLD_CROSS_REF_SNIPPET_CHARS` clamped `[240, 60000]`;
`_clip_clause` now prefers clause → word boundary, **never** cuts mid-word, **always** marks with
` [...]`, and reserves the marker's cost so the result cannot exceed the ceiling.

⚠ **And the flag was invisible to every A/B.** `REGENOLD_CROSS_REF_CONTEXT` has been default-ON and
**absent from `_engine_cache_key` since R69**, so an in-process A/B of this path would have been
served one arm's cached output — the inert-A/B trap, live for many rounds. Both it and the new
budget flag are now registered (`app/routes/regenold.py:1626-1636`).

**Measured before/after, same question, live:**

| | SYSTEM | USER | `…` in USER |
| --- | --- | --- | --- |
| before | 51,512 | 122,828 | **2** |
| after | 51,512 | **135,778** | **0** |

+12,950 chars of grounding restored (+10.5%). Tests: 629 passed on
`-k "grounding or prose or context or stage2"`, 28 on `test_semantic_layer.py`, 190 on the
cache-key/xref selection.

**The consequence that matters most for the graded batch:** the canonical Article 11 → **Annex IV**
cross-reference was being cut to 240 chars. Annex IV now reaches Stage-2 complete at **5,720 chars**
— which is where **Annex IV(1)(e)**, the hardware description that graded question `rg_001` turns
on, actually lives. Per CLAUDE.md that content was previously reachable only through the system slot
the wrapper dropped. It is now on both channels, in full, for the first time.

## 5. What is still open

1. **The trace must record the primary provider's failure.** One `record_note` in the
   `groq_auto_fallback` branch of `_graph_rag_impl.py` (~:880) would have made this a five-minute
   diagnosis instead of a multi-hour one. Highest-value single change in this document.
2. **Groq is at its daily token cap** (198,784/200,000 TPD). While the primary works this is
   harmless; as a fallback it is currently a no-op, so a primary outage now degrades straight to
   deterministic.
3. Railway service restart so the CF variables take effect; then re-probe and confirm
   `stage2_model=claude-opus-4-8` with **no** `groq_auto_fallback` note.
4. `run_graphrag_benchmark` still records no Stage-2 provenance (R338 item 2).
5. The 4000-char per-message input cap still rejects `mt_med_07` (R338 item 5).
6. Medtech multi-turn coherence 0.2222 still unexplained (R338 item 7).
