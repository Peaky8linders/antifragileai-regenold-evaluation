# R367 — Intent-detection hardening (deep-dive vs hybrid-RAG practice)

## What was reviewed
`app/llm/intent_classifier.py` (884 lines, 60+ intent labels, Groq→wrapper
chain), its route consumers (`boost_for_intent`, `_intent_anchor_set`,
`_prune_non_anchor_refs`, `rerank_sentences`), the query denoiser chain,
and the Stage-0→Stage-1/2 wiring.

## Gaps found (grounded in proven hybrid-RAG routing practice)

1. **Dead bridging key — real bug.** `BRIDGING_NODES` keyed on
   `high_risk_annex_i`, which is NOT an intent label (the taxonomy emits
   `annex_harmonisation_law` for Annex I). The MDR/Machinery cross-framework
   bridging context therefore NEVER fired. Verified: `labels ∩ bridging ==
   {data_governance, quality_management_system}` only.
   **Fix:** remap to `annex_harmonisation_law` with the real sectoral
   legislation (Machinery Regulation, MDR, IVDR, RED). This seeds the
   cross-framework sectoral context into retrieval for Annex-I questions —
   exactly the lever the knowledge-graph/ontology layer is designed for.

2. **Cache key ignored the prompt — stale-intent masking.** `_cache_key`
   hashed question+model only. A prompt edit (e.g. the calibration below)
   would leave 2048 rows of cached intents from the OLD prompt serving.
   **Fix:** key on SHA-256(prompt) + question + model (lazy `_prompt_hash()`).
   A prompt change is now a clean cache invalidation.

3. **Intent provider chain was Groq → wrapper only.** The operator directive
   keeps the intent providers ON (Gemini/Mistral are fast, separately-quota'd
   tiers, 1-2 s). The denoiser already had the richer chain; the intent
   classifier did not.
   **Fix:** `_resolve_intent_provider` + `classify_intent` now walk
   Groq → Gemini → Mistral → wrapper, each gated on its key, on any failure.
   A Groq 429/outage degrades to Gemini/Mistral before the slow wrapper
   instead of dropping intent.

4. **Prompt calibration mismatched the engine gates + reasoning could starve
   the JSON.** The prompt said "use < 0.6 when ambiguous" but the route gates
   at 0.7 (narrow) / 0.85 (promote) — the model was being told to calibrate
   against thresholds the engine doesn't use. And `reasoning` comes FIRST in
   the JSON at a 250-token budget, so a verbose reasoning field can push the
   intent/anchors past the budget and lose the whole parse.
   **Fix:** the prompt now documents the real gates ("< 0.7 your anchors are
   ignored; 0.7-0.85 narrows; ≥ 0.85 promotes") and caps reasoning at one
   short sentence (≤ 20 words).

## Tests
- `tests/test_r367_intent_hardening.py` — 9 new tests (bridging keys valid,
  cache-key prompt versioning incl. prompt-edit invalidation, chain order +
  full-chain fallback, prompt calibration text present).
- Cache-key completeness: `REGENOLD_BEDROCK_FALLBACK_CHAIN` (R366.1) was
  caught unregistered by `test_r355_cache_key_complete` / `test_r334` —
  registered in `_engine_cache_key`.
- Full suite diff vs baseline: **zero regressions** — the only failure-set
  delta is the 9 R367 tests that now pass (46 with changes = 55 baseline − 9).

## Files
- `app/llm/intent_classifier.py` (R367: bridging, cache key, chain, prompt)
- `app/routes/regenold.py` (cache-key registration)
- `tests/test_r367_intent_hardening.py` (new)
