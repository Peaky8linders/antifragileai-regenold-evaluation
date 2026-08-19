# Deep Code Review: OpenRouter Implementation & Model Routing

**Date:** 2026-08-19 11:05:30
**Branch:** main -> main
**Files changed:** 5 | **Lines changed:** +101 / -105
**Diff size category:** Medium

## Executive Summary

A multi-agent adversarial code review was conducted covering the recent OpenRouter implementation and Stage-2 model routing (Opus 5 with 2048 thinking tokens for complex questions, Sonnet 5 for simple questions). 12 findings were reviewed and verified across 5 specialist domains (Logic, Error Handling, Contract/Integration, Concurrency/State, Security) and confirmed by the Verifier agent. Two Critical issues were uncovered: an erroneous `_is_claude` condition in `openai_wrapper_provider.py` suppressing reasoning payloads on OpenRouter for Anthropic models, and an overly restrictive guard blocking the cross-provider Bedrock fallback when OpenRouter fails.

---

## Critical Issues

### [C1] `_is_claude` check suppresses OpenRouter reasoning payload for Anthropic Claude models
- **File:** `app/llm/openai_wrapper_provider.py:512-516`
- **Bug:** `_OpenAIWrapperProvider.complete()` guards `body["reasoning"] = {"max_tokens": ...}` with `if req.reasoning_max_tokens > 0 and not _is_claude:`. Because `_is_claude` checks `"claude-" in _model_lc`, any Claude model (e.g. `anthropic/claude-opus-5`) evaluates to `True`, silently dropping the `reasoning` payload.
- **Impact:** OpenRouter requests for `anthropic/claude-opus-5` run completely thinking-free (0 thinking tokens), defeating the 2048 extended thinking budget on complex questions.
- **Suggested fix:** Remove `and not _is_claude` when `req.reasoning_max_tokens > 0` (OpenRouter uses unified reasoning for all models), or differentiate between the local Claude CLI wrapper and OpenRouter endpoints.
- **Confidence:** 95%
- **Found by:** Logic & Correctness, Error Handling & Edge Cases, Contract & Integration

### [C2] `and not _use_openrouter` guard blocks cross-provider Bedrock fallback
- **File:** `app/engines/_graph_rag_impl.py:9458`
- **Bug:** In `_claude_max_enhance_answer`, the Bedrock fallback condition is written as `if text_raw is None and not _use_gemini and not _use_openrouter:`. When OpenRouter is enabled and fails or exhausts its fallback chain, this condition evaluates to `False`.
- **Impact:** Failed OpenRouter requests bypass the Bedrock Opus 4.6 safety net and immediately degrade to deterministic Stage-1 output, leaving lines 9495–9496 as unreachable dead code.
- **Suggested fix:** Change line 9458 to `if text_raw is None and not _use_gemini:` so that OpenRouter failures fall through to Bedrock as designed.
- **Confidence:** 98%
- **Found by:** Logic & Correctness, Error Handling & Edge Cases, Security, Contract & Integration, Concurrency & State (5/5 unanimous)

---

## Important Issues

### [I1] Clamping bug forces 1024 thinking tokens when `complex_thinking_tokens=0`
- **File:** `app/engines/_graph_rag_impl.py:1333`
- **Bug:** `_openrouter_complete_for_graph_rag` runs `_reasoning_budget = max(1024, min(_reasoning_budget, 16000))` unconditionally, forcing `0` to `1024`.
- **Impact:** Operators cannot disable extended thinking on OpenRouter complex questions via `complex_thinking_tokens=0`.
- **Suggested fix:** Only clamp when `_reasoning_budget > 0`.
- **Confidence:** 95%
- **Found by:** Logic & Correctness, Error Handling & Edge Cases

### [I2] `_openrouter_complete_for_graph_rag` discards `resp.thinking`
- **File:** `app/engines/_graph_rag_impl.py:1364-1415`
- **Bug:** `_openrouter_complete_for_graph_rag` returns `resp.text` without calling `record_llm_thinking()`.
- **Impact:** Generated reasoning traces from OpenRouter are lost and not surfaced in `?include_reasoning=true` or the UI thinking panel.
- **Suggested fix:** Call `record_llm_thinking(resp.thinking, stage=stage_name)` before returning `resp.text`.
- **Confidence:** 90%
- **Found by:** Logic & Correctness, Contract & Integration

### [I3] Unhandled `TypeError` on null usage token counts
- **File:** `app/llm/openai_wrapper_provider.py:678-679`
- **Bug:** `int(usage.get("prompt_tokens", 0))` raises `TypeError` if `usage` is `{"prompt_tokens": null}`.
- **Impact:** Proxies returning `null` usage fields cause an unhandled crash in `complete()`.
- **Suggested fix:** Use `int(usage.get("prompt_tokens") or 0)` and `int(usage.get("completion_tokens") or 0)`.
- **Confidence:** 85%
- **Found by:** Error Handling & Edge Cases, Contract & Integration

### [I4] `_stage2_provider_enabled()` omits `openrouter` check
- **File:** `app/engines/_graph_rag_impl.py:1725-1766`
- **Bug:** `_stage2_provider_enabled()` omits `openrouter`, falling through to `is_openai_wrapper_enabled()`.
- **Impact:** Returns `True` even if `OPENROUTER_API_KEY` is missing.
- **Suggested fix:** Add explicit `if env_value == "openrouter": return is_openrouter_provider_enabled()`.
- **Confidence:** 92%
- **Found by:** Contract & Integration

### [I5] Missing `_reset_openrouter_singleton_for_tests` in `tests/conftest.py`
- **File:** `tests/conftest.py:432-442`
- **Bug:** The `_reset_llm_provider_singletons` autouse fixture does not reset OpenRouter.
- **Impact:** Cross-test singleton state leakage under mocked environments.
- **Suggested fix:** Add `"_reset_openrouter_singleton_for_tests"` to the reset loop in `conftest.py`.
- **Confidence:** 95%
- **Found by:** Concurrency & State

### [I6] `REGENOLD_OPUS_FOR_ALL` ignored by `_openrouter_model()`
- **File:** `app/engines/_graph_rag_impl.py:1224-1246`
- **Bug:** `_openrouter_model()` does not check `_opus_for_all_enabled()`.
- **Impact:** When `REGENOLD_OPUS_FOR_ALL=1`, OpenRouter still serves `anthropic/claude-sonnet-5` on standard questions instead of the complex model.
- **Suggested fix:** Check `_opus_for_all_enabled()` in `_openrouter_model()`.
- **Confidence:** 90%
- **Found by:** Concurrency & State

---

## Suggestions

- **[S1] Cloudflare Access & API key fallback isolation:** Refine host checking in `_resolve_cf_access_headers` and differentiate `api_key is None` from empty string in `_OpenAIWrapperProvider.__init__`. (`app/llm/openai_wrapper_provider.py:309-320, 413`)
- **[S2] XML boundary delimiters for web search:** Wrap web search snippets in `<web_search_results>` XML boundary tags to defend against indirect prompt injection. (`app/engines/_graph_rag_impl.py:8911-8916`)
- **[S3] Update `CLAUDE.md` documentation:** Update the OpenRouter defaults in `CLAUDE.md:1193-1196` to reference `claude-sonnet-5`, `claude-opus-5`, and `deepseek-v4-flash,gemini-2.5-flash`.
- **[S4] OpenRouter routing suffix formatting:** Normalize leading colons and prevent double suffixes (`:nitro:nitro`). (`app/engines/_graph_rag_impl.py:1216-1221, 1245`)

---

## Review Metadata

- **Agents dispatched:** Logic & Correctness, Error Handling & Edge Cases, Contract & Integration, Concurrency & State, Security, Verifier
- **Scope:** `app/config.py`, `app/engines/_graph_rag_impl.py`, `app/llm/openai_wrapper_provider.py`, `tests/test_complex_model_routing.py`, `tests/test_openrouter_stage2.py`, `tests/test_r138_bluf_verdict_citations.py`
- **Raw findings:** 28 (across 5 specialists)
- **Verified findings:** 12 (after deduplication and verification)
- **Filtered out:** 0 false positives
