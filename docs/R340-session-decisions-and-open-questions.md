# R338–R340 — the decision record: what was asked, what was measured, what was decided

**Session** 2026-08-15 · **Branches** `r338-gemini-review-fixes` (merged, PR #20),
`r339-stage2-restored` (merged, PR #21), `r340-prompt-rebuild` (open) ·
**Deployed at time of writing** `ba223134d6a7`

This is the durable record. Each entry is a QUESTION that was asked, the EVIDENCE that answered
it, and the DECISION taken — so a future round can re-open a decision on its merits instead of
re-deriving it, and can see which ones are still unresolved.

---

## Q1. Are the six unreviewed "Gemini" commits safe to keep?

**Evidence.** 10 review lenses, 89 agents, every finding put through adversarial refutation
(18 refuted and dropped). 3 Critical / 14 Important / 7 Suggestions.
Full report: `docs/reviews/gemini-changes-2026-08-15-cc47f8b.md`.

Two Criticals shipped wrong law on the Stage-2 **user** channel — the one slot the wrapper never
dropped, delivered on 100% of requests, ungated and unmeasured:
* A sentence instructing the model to cite **EU Charter article numbers**. Charter articles 1-54 all
  resolve in `ARTICLE_EXISTENCE`, so the lint floor is blind by construction, and the
  foreign-instrument guard is adjacency-anchored, so in an enumeration it suppresses only the member
  next to the word "Charter". Executed: 4 of 5 renderings leak onto the wire as AI Act citations.
* An eight-item "Annex IV" component list that is **not Annex IV**. `get_provision_text("Annex IV")`
  is 5,710 chars over nine points and contains no `"ce mark"`; CE marking is Article 48. The list
  omitted point 1 entirely — including **1(e)**, the hardware description graded question `rg_001`
  turns on.

**DECISION — REVERTED** both sentences (`graph_rag_prompts.py:898-903`). The topic-neutral rule four
lines above already covers the intent and stays grounded in supplied text. Shipped in PR #20.

---

## Q2. Does the Claude-Max wrapper drop the Stage-2 system prompt? (operator instruction)

**Evidence.** Probed: system slot ignored, user slot obeyed. Root cause found in the wrapper repo —
`claude_agent_sdk 0.2.82` types `system_prompt` as `str | SystemPromptPreset | SystemPromptFile`,
and the wrapper passed `{"type":"text",...}`, which the SDK silently discards.

**DECISION — ENABLED** `WRAPPER_FORWARD_SYSTEM_PROMPT=1`. **This immediately broke Stage-2
completely**, which is Q3.

---

## Q3. Why did every Stage-2 call fail after that?

**Evidence.** The SDK passes a `str` system prompt **inline into argv**
(`subprocess_cli.py:229`). Windows `CreateProcess` caps a command line at **32,767 chars**.
`ANSWER_GENERATE_SYSTEM` is **51,516**. Bisected, everything else constant:

| system prompt | result |
| --- | --- |
| 32,000 chars | 200 OK, 6.3 s |
| **32,768** | **500, 0.3 s** |
| 40,000 | 500, 0.3 s |

The SDK reported it as `"Claude Code not found at: …claude.exe"` — the binary is present and 265 MB;
the *spawn* failed. That mis-attribution is why it survived two service restarts.

Ruled out by execution: `max_tokens` (6048 fine), total payload (12.5K system + 90K user fine),
the tunnel, the model name.

**DECISION — FIXED at the wrapper**, using the SDK's own escape hatch: `SystemPromptFile` is passed
as `--system-prompt-file <path>` (`subprocess_cli.py:234`), so argv never sees the text. Spills above
`WRAPPER_SYSTEM_PROMPT_ARGV_LIMIT` (default 30,000), unlinks in `finally`.

**Verified by NONCE ECHO, not an obedience sentinel.** A nonce at head *and* tail of a 51.4K prompt
comes back verbatim. At that size an obedience sentinel is not a delivery test — the model reads the
rule and weighs it against the question, so it can be delivered and not obeyed.

---

## Q4. Why was production shipping deterministic answers on hard questions?

**Evidence.** Three independent faults, each hiding the next:
1. `CF_ACCESS_CLIENT_ID/_SECRET` unset on Railway. `_resolve_cf_access_headers` **fail-softs to `{}`**
   on missing credentials, so the tunnel returned **401** and nothing said so.
2. `groq_auto_fallback` then fired — it runs *only* when the Claude-Max call already failed. Groq was
   at its daily token cap (`Limit 200000, Used 198784`), so `complex=True` questions got **429** →
   `stage2_failed_both_providers_deterministic_ship`.
3. The argv bug in Q3, which would have bitten the moment Access started working.

**DECISION — all three fixed.** CF vars set on the service, Groq key rotated, wrapper patched.
Verified live after redeploy: `stage2_polish: True`, `stage2_model=claude-opus-5 complex=True`,
**no fallback note**, and sub-point citations (`Article 26.11`, `26.5`, `6.2`) on the wire.

⚠ **Open:** the trace records only the FALLBACK's outcome, never the primary provider's failure
reason. One `record_note` in the `groq_auto_fallback` branch (`_graph_rag_impl.py` ~:880) would have
made this a five-minute diagnosis. **Not yet done — highest-value single change outstanding.**

---

## Q5. Should the two deliberate Stage-2 bypasses stay?

`REGENOLD_CURATED_STAGE2_SKIP` (R144) and `REGENOLD_DEFINITIONAL_STAGE2_SKIP` (R275), both default
ON, together bypass Stage-2 on 11 of 20 Antifragile rows.

**Evidence — paired arms, Antifragile 20, Stage-2 genuinely working, fire check passed**
(`stage2_polish` 9 → 19, latency 2.4×):

| | A: bypasses ON | B: OFF |
| --- | --- | --- |
| expert mistakes resolved | 34/38 | **34/38 — identical** |
| ans_conciseness | **0.5161** | 0.3535 |
| ref_strict | **0.9028** | 0.8349 |
| judge answer correctness | 0.85 | **0.90** |
| judge reference precision | **0.7935** | 0.7005 |
| judge citation faithfulness | **1.00** | 0.95 |
| latency p50 | **6,985 ms** | 17,067 ms |

**DECISION — KEEP BOTH ON.** Removing them buys a little answer completeness and costs reference
quality, conciseness and 2.4× latency, while resolving *exactly the same* 34 mistakes.
Answer-Conciseness is the one axis we lead with zero headroom.

**Instrument note that generalises:** the gates fire on **2 of 132** `probe_set` rows, so a
`dynamic_ab` run would have moved 2 rows and reported a meaningless NULL — the inert-A/B trap
arriving through the *probe pool*. Antifragile fires 11/20 and was the correct instrument. Also, the
provider gate at `_graph_rag_impl.py:8181` returns **before** both bypass gates, so any
`provider=cli` arm on these flags is inert by construction.

---

## Q6. What are the LLM-judge answer and reference correctness numbers?

**Evidence.** `evals.judge.grounded`, `claude-sonnet-5`, n=20, 0 errors. Grounding provenance is what
makes them trustworthy: `grounded._prepare` falls back to grounding answer-correctness on the
answer's **own** `pred_refs` when a row has no independent gold, which makes the axis self-graded.
`ANTIFRAGILE_GT` carries a synthesized `gold_answer` for all 20 rows, so the sidecar was built with
it — output confirms `answer_grounding_source = gold_refs` on **20/20**.

Shipped config: answer correctness **0.85** (factual 0.7741), reference correctness **0.50**
(precision 0.7935, recall 0.9150, F1 0.8499), citation faithfulness **1.00**.

**9 of the 10 reference failures are OVER-CITATION**, with the wrong ref named per row. Two patterns
sit outside the trimmer/ranker families CLAUDE.md has measured dead:
* **parent cited alongside its own sub-point** (q12) — which is exactly `REGENOLD_PARENT_COLLAPSE`,
  still default OFF, now with independent evidence on sub-point-carrying gold;
* **wrong coordinate inside the right article** (q01 cites 6.3 not 6(1)-(2); q13 cites 6.1 not 6.2) —
  a selection error no trimmer can fix.

---

## Q7. Is Stage-2 getting the full context and the original question? (operator requirement)

**Evidence.** Captured the real payload by spying on the provider: system 51,513 + user 122,828
chars. Original question present **verbatim**; system prompt whole. **But the grounding was cut.**

`app/engines/semantic_layer.py::_clip_clause`, hard-coded `_CROSS_REF_SNIPPET_CHARS = 240`, ending
`return window.rstrip() + "…"` — a raw character cut. Proven render-time, not stored data:

| ref | stored | reached Stage-2 |
| --- | --- | --- |
| Article 40 | 2,770 | **240** |
| Article 41 | 3,842 | **158** (96% loss, **no marker at all**) |
| Article 74 | 6,977 | **241** |

**DECISION — FIXED.** Budget raised above the largest reachable node; `_clip_clause` never cuts
mid-word and always marks. Measured: user payload 122,828 → 135,778, ellipses 2 → 0.
**Annex IV now reaches Stage-2 complete at 5,720 chars** — where Annex IV(1)(e) actually lives.

⚠ Also found: `REGENOLD_CROSS_REF_CONTEXT` has been default-ON and **absent from
`_engine_cache_key` since R69**, so any in-process A/B of this path was served one arm's cached
output. Now registered.

---

## Q8. Are the 56 pytest failures really "a documented provider=cli env artifact"?

CLAUDE.md dismissed them in one line. The operator rejected that framing ("no BS, no bias").

**Evidence.** Triage across all 56 proved by execution that they are **STALE MOCKS, not environment**.
R56/R127 added a provider pre-gate (`_stage2_wrapper_enabled`, `is_openai_wrapper_enabled`) *above*
the seam these tests mock, and it returns False on the literal string `cli`. The mocks are never
reached. Changing only the provider to `openai_wrapper` — dead-port base retained, so **no network
is reachable and every call site is a MagicMock** — turns 65 of them green.

**DECISION — CLAUDE.md's line is WRONG and must be corrected.** These are fixable test bugs. The fix
is an env pin per file (the pattern already exists in-repo at
`tests/test_r133_prose_subpoints.py:132`), with **no assertion weakened**.

---

## Q9. Should the rebuilt Stage-2 prompt ship? — **UNRESOLVED AT TIME OF WRITING**

The V1 system prompt accumulated over many rounds while reaching the model on **0% of requests**, so
none of it ever had behavioural feedback. Measured on delivery: 51,516 chars, 122 lines, 19
paragraphs, 15 numbered rules, **zero structural markup**.

The rebuild (`ANSWER_GENERATE_SYSTEM_V2`, **15,462 chars — a 70% cut**) is XML-sectioned, and its
`<reference_discipline>` block maps directly onto the measured judge failures: RELEVANCE,
DESCRIPTION, COORDINATE (parent+sub-point), CONDITION, DISPOSAL (the empty-gold row), CROSS-REFERENCE,
OTHER INSTRUMENTS (closing the Charter-leak class at the prompt).

**Metric A/B, Antifragile 20, shipped config, fire check passed (system 51,513 → 15,462):**

| axis | V1 | V2 | delta |
| --- | --- | --- | --- |
| ans_f1 | 0.5967 | **0.6230** | **+0.0263** |
| ans_conciseness | 0.5160 | **0.5518** | **+0.0358** |
| ans_loose | 0.4417 | **0.4675** | +0.0258 |
| ans_strict | **0.7157** | 0.7061 | −0.0096 |
| ref_strict | 0.9028 | **0.9061** | +0.0033 |
| ref_loose / ref_conciseness | 0.9458 / 0.8046 | 0.9458 / 0.8046 | 0 |
| ref_subpoint_strict | **0.6309** | 0.6155 | −0.0154 |
| ref_subpoint_conciseness | 0.6267 | **0.6461** | +0.0194 |
| keyword_recall | **0.8724** | 0.8498 | −0.0226 |
| expert mistakes | 33/38 | 33/38 | 0 |
| latency p50 | 7,180 ms | **7,006 ms** | −174 ms |

Judge, V1 arm: answer 0.85 (factual 0.7868), reference 0.50 (P 0.789, R 0.955, F1 0.8641),
citation faithfulness 1.00. **V2 judge run still in flight.**

**STATE: NOT DECIDED.** The metric deltas are small and mixed, and only **9 of 20 rows** reach
Stage-2 in the shipped config, so the effective n is 9. `ans_conciseness +0.036` and `ans_f1 +0.026`
favour V2 on the axes that matter most; `keyword_recall −0.023` and the sub-point pair go the other
way. **This must not be shipped on the metric table alone.** The decision waits on the V2 judge
numbers (reference correctness is the axis the rewrite targets) and on the two adversarial
challengers — one diffing the rule-traceability table against an independent enumeration of the old
prompt to catch concealed drops, one red-teaming the new prompt against the hard cases.

The one certain benefit independent of quality: **70% fewer system-prompt tokens on every Stage-2
call**, and the prompt drops under the 32,767 argv ceiling, so it is safe even on an unpatched
wrapper.

---

## Standing corrections to CLAUDE.md produced by this session

1. "The Stage-2 system prompt is dropped by the wrapper" — **false since 2026-08-15**, and the fix
   has a size ceiling (32,767 argv) that must be respected.
2. "56 pre-existing failures, all the documented provider=cli Stage-2 env artifact" — **false**, they
   are stale mocks (Q8).
3. "A merge to main does not auto-deploy" — **false**, it does, with a lag; read `/healthz.commit`.
4. The deployed provider is a **live service variable**; re-measure, never remember.
5. R338's "−5 mistake regression" — **retracted**; it was measured while Stage-2 was dead.
6. `dynamic_ab` cannot observe the Stage-2 bypasses (2/132 probe rows) — pick the instrument by
   measured fire rate, not by reputation.
