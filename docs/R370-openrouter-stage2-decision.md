# R370 — OpenRouter Stage-2 (tunnel-free): model + routing decision

**Date:** 2026-08-17 · **Status:** implementation shipped, 60-row golden live
read in progress

---

## 1. Why OpenRouter

The Stage-2 ANSWER synthesis previously ran either on the Cloudflare-tunnel
Claude-Max wrapper (21–33 s p50 in the live-model test — the tunnel hop is
~99% of the floor) or on Bedrock (10.8 s p50). OpenRouter removes the tunnel
hop, gives per-token model choice (the wrapper is subscription-bound to one
family), and is OpenAI-spec so the existing `_OpenAIWrapperProvider` drives it
unchanged. `OPENROUTER_API_KEY` is live in `.env` + Railway.

## 2. Routing modes — which axis matters here

OpenRouter sorts providers per request by one of three modes:

| mode | axis | relevance to Stage-2 legal synthesis |
|---|---|---|
| **Balanced** (default) | price + speed | the safe default |
| **Nitro** (`:nitro`) | throughput (tokens/s) | the documented **latency lever** — Stage-2 latency is a scored axis |
| **Exacto** (`:exacto`) | quality / **tool-calling** telemetry | **irrelevant** — Stage-2 calls no tools; the tool-call axis is noise for a RAG answer |

**Decision: default `balanced`; `nitro` is the env flip for latency; `exacto`
is not recommended** (its sorting signal is tool-call success, which does not
predict citation-disciplined legal prose).

## 3. Model choice — live probe (2026-08-17, Stage-2-shaped prompt)

A 1 KB Stage-2-shaped prompt (system persona + CITABLE PROVISIONS whitelist +
verbatim text + answer rules) was sent to every candidate at temperature 0;
citation discipline = did the answer cite ONLY whitelisted provisions:

| model | latency | finish | cited | leaked | BLUF |
|---|---|---|---|---|---|
| anthropic/claude-sonnet-4.6 | 4.8 s | stop | Annex III, Article 6 | NONE | ✓ |
| anthropic/claude-opus-4.6 | 3.9 s | stop | Annex III, Article 6 | NONE | ✓ |
| qwen/qwen3-235b-a22b-2507 | 2.3 s | stop | Annex III, Article 6 | NONE | ✓ |
| google/gemini-2.5-pro | 8.2 s | stop | Annex III, Article 6.3 | NONE | ✓ |
| deepseek/deepseek-chat-v3.1 | 2.2 s | stop | Annex III, Article 6 | NONE | ✓ |
| qwen/qwen3-max-thinking | — | 404 | not served for this account | | |
| openai/gpt-5.2 | — | 404 | not served for this account | | |

**Decision: `anthropic/claude-sonnet-4.6` (standard) / `anthropic/claude-opus-4.6`
(complex tier).** Rationale:
* Every working candidate had perfect whitelist discipline on the probe — the
  discriminator is the full ~25–50 KB prompt where instruction-following and
  citation granularity matter; Claude Sonnet 4.6 is the strongest
  instruction-follower of the set and the codebase's documented best reasoner.
* Latency 4.8 s on the probe ≈ the Bedrock opus p50 (10.8 s) halved and ~5–7×
  faster than the tunnel — the user's latency goal.
* The R366.1 Bedrock chain already validated qwen3-235b as the first non-Claude
  tier; it is wired as the OpenRouter rollover tier (same doctrine).

## 4. Implementation

* `app/llm/openai_wrapper_provider.py` — `is_openrouter_provider_enabled()` /
  `get_openrouter_provider()` (pooled singleton, mirror of the Groq one).
* `app/llm/__init__.py` — `resolve_provider` accepts `openrouter`.
* `app/engines/_graph_rag_impl.py` — `_openrouter_complete_for_graph_rag()`
  (guards: finish_reason=length, R102 structural, R142 verdict; internal
  rollover chain primary → qwen3-235b → deepseek-chat; full system prompt —
  no R342 argv cap) + dispatch in `_stage2_complete` and the main
  `_claude_max_enhance_answer` path. The Bedrock opus-4-6 retry is
  **excluded** for openrouter (no cross-provider hop — the R366 live-model-test
  integrity rule).
* `app/routes/regenold.py` — 4 new knobs in `_engine_cache_key` (model /
  complex-model / routing / chain).
* Config: `railway.toml` + `.env.example` documented; env knobs:
  `REGENOLD_STAGE2_MODEL_OPENROUTER`, `REGENOLD_STAGE2_COMPLEX_MODEL_OPENROUTER`,
  `REGENOLD_OPENROUTER_ROUTING`, `REGENOLD_OPENROUTER_FALLBACK_CHAIN`,
  `OPENROUTER_TIMEOUT_SECONDS`.

## 5. Validation

* 18 new unit tests (`tests/test_openrouter_stage2.py`) — provider gating,
  model resolution, routing suffixes, chain rollover, truncation rollover,
  dispatch wiring, cache-key sensitivity. Green.
* Affected suites green (R329 131, R355 cache-key completeness, llm providers).
* Live golden read (60 rows, qwen.qwen3-32b judge via Bedrock — identical to
  the R369 baseline) in progress: `scratch/run_live_r370_golden_openrouter.py`
  → `evals/bench/results/r370-golden-openrouter-7axis.json`, compared against
  `r369-golden-7axis.json`. NOTE: this branch ALSO carries the R329 restore
  (citable block live again) + the R369 collapse/promote passes, so the read
  measures the full branch delta, not OpenRouter in isolation.

## 6. Artifacts

* `scratch/or_probe.py` — the live model probe.
* `scratch/run_live_r370_golden_openrouter.py` / `_judge.py` — the golden read.
* `tests/test_openrouter_stage2.py` — the unit contract.
