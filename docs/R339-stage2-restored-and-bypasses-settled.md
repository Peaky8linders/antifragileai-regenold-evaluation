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
