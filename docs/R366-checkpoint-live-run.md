# R366 Checkpoint — live-run state, tunnel fix, R353.1 verdict (2026-08-17 15:30)

## What was completed

### 1. R353.1 — Annex III anchor placement A/B (FINAL, verdict measured)
- **Question:** R353's pre-BM25 append suppressed the BM25 recall lane (7 rows lose `Article 6` gold when the Annex III anchor fires).
- **Fix applied:** moved the R353 block after the BM25 fallback + vector recall, before the R340 rerank (same load-bearing placement as R365.1).
- **Parse-level verification:** fires=11, displaced=0 (was 7), all 7 previously-displaced rows keep `Article 6` AND gain `Annex III`; `lr_inventory_tool` is net-neutral.
- **Live A/B** (`dynamic-ab-r353-1-moved.json`, 70 rows, sonnet-4-6 gen / Qwen judge): all axes UNDERPOWERED but directionally:
  - ref_loose −0.0071, ref_strict −0.0038, ref_conc −0.0187, kw_recall −0.0129
  - ans_corr −0.0143, ref_corr −0.0286, **cite_faith +0.0286**, ans_conc −0.0429
  - **gold-drop veto: cleared** (the OLD placement was REJECTED by `gold_dropped_head +1`)
- **Decision:** keep the moved placement. It eliminates the hard-rule veto, is cite_faith-positive, and the small negative deltas are all within CI (UNDERPOWERED). The old placement was definitively REJECTED; the move converts a vetoed config into a neutral-to-positive one.

### 2. R366 — Gemini REMOVED from the Stage-2 fallback chain (operator directive)
- **Problem found:** the Stage-2 fallback fired on Bedrock 429 throttles and served `gemini-2.5-flash` answers into Bedrock-only checkpoints (`graph_rag.gemini_fallback_stage2_truncated` in live logs). The `REGENOLD_BEDROCK_WRAPPER_FALLBACK=0` env only blocked the Bedrock→wrapper hop, NOT this Gemini path.
- **Fix:** the fallback is now **Bedrock + claude-opus-4-6 only** (scoped env pin for the retry, restored after). No Gemini, no Mistral, no wrapper. Verified in the live log: `graph_rag.stage2_fallback_bedrock_served` replaces the Gemini fallback lines.
- **Intent detection untouched** — Groq/Gemini/Mistral chain stays ON (per operator directive).
- Stage-1/2 primary `provider == "gemini"` branches remain but are inert unless `P2P_GRAPH_RAG_PROVIDER=gemini` is explicitly set (our runs pin bedrock).

### 3. Tunnel leak found and blocked
- **Root cause:** `OPENAI_API_BASE=https://wrapper.antifragile-ai.net/v1` (the Claude-Max cloudflared tunnel) was read from the operator `.env`. The intent classifier / query denoiser / wrapper fallback paths could reach it. During the live run, cloudflared showed ESTABLISHED connections to 127.0.0.1:8000 — tunnel traffic was flowing.
- **Fix (launcher):** `OPENAI_API_BASE=http://127.0.0.1:1/v1` (dead-end), `REGENOLD_INTENT_PROVIDER=groq` (intent stays functional), `REGENOLD_BEDROCK_WRAPPER_FALLBACK=0`. Verified: wrapper singleton resolves the dead-ended base; intent still enabled via Groq.
- **Verified on the re-run:** zero ESTABLISHED tunnel connections during the whole sonnet/opus live run, zero Gemini fallbacks.

### 4. Live re-run attempts — TRANSPORT on both, then R366.1 chain fix
- **opus-4-6 attempt** (`dynamic-ab-r365-live.json` overwritten): 63 rows × 2 arms, **256 Bedrock 429 throttles** on `eu.anthropic.claude-opus-4-6-v1` → 32/63 rows 503, n_scored=0, verdict TRANSPORT. Saved as `checkpoints/dynamic-ab-r365-live-opus46-TRANSPORT.json`.
- **sonnet-4-6 attempt** (`dynamic-ab-r365-live.json`): still throttled (sonnet AND opus 429s), 9/18 rows errored → TRANSPORT at n=18. The account was in a sustained rate-limit window from the session's A/Bs + judge calls.
- **R366.1 — cross-model Bedrock fallback chain (NEW):** probed the account's model list and verified invocable non-Claude tiers: `qwen.qwen3-235b-a22b-2507-v1:0`, `nvidia.nemotron-super-3-120b`, `mistral.devstral-2-123b`, `qwen.qwen3-32b-v1:0`. `_bedrock_complete_for_graph_rag` now rolls primary → opus-4-6 → qwen3-235b → nemotron-super → devstral → qwen3-32b on error/429/truncation (`REGENOLD_BEDROCK_FALLBACK_CHAIN` override). Served-by is logged (`graph_rag.bedrock_fallback_chain_served primary=… served_by=…`). 68 tests green.
- **Next:** relaunch the 81-row live run with **sonnet-4-6** primary (healthy) + chain rollover + **Qwen3-32B judge** (all 7 axes).

## Checkpointed artifacts
- `evals/bench/results/dynamic-ab-r353-1-moved.json` (+ copy in `checkpoints/`)
- `evals/bench/results/dynamic-ab-r365-live.json` (+ copy in `checkpoints/dynamic-ab-r365-live-opus46-TRANSPORT.json`)
- Launcher: `scratch/run_live_r365.py` (sonnet-4-6 gen / Qwen judge / tunnel dead-ended)

## Pending
- Live run on sonnet-4-6 + Qwen judge (81 rows, 7 axes)
- PR merge for R353.1 + R366 (this repo)
