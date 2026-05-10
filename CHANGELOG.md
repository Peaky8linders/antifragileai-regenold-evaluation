# Changelog

## 0.1.0 — Initial extraction + round-5 expansion (2026-05-10)

### Origin

Extracted from `Peaky8linders/legit-ai` (CodexAI EU AI Act Path-to-Production compliance platform) at version **1.2.132**.

Module structure preserved 1:1 so file paths in CodexAI's `CLAUDE.md` verification entries still resolve here.

### What's included

* `app/integrations/regenold/` — auth, models, scope, route (verbatim copies).
* `app/engines/graph_rag.py` — two-stage RAG engine (parse → retrieve → generate) with the LLM-or-deterministic fallback.
* `app/data/article_existence.py` — 113 articles + 13 annexes catalog (verbatim).
* `app/data/graph_rag_prompts.py` — engine system prompts (verbatim).
* `app/data/kb.py` — minimal 4-dimension KB stub + 19-article `EC_CHECKER_OBLIGATION_MAP` so the engine's deterministic-fallback path produces useful prose without the full KB.
* `app/routes/regenold.py` — `POST /api/v1/regenold/eu-ai-act/ask` route (verbatim).
* `evals/regenold/` — eval harness with **51 baseline scenarios + 100 multi-conversation + 100 tricky/misleading** = **251 total scenarios** across 28 categories.
* `tests/test_regenold_*.py` — regression tests (verbatim) + new `test_regenold_followup_fixes.py` pinning the two follow-up fixes.
* `docs/partners/regenold/` — integration guide + partner-side client example + Sonnet wrapper setup.

### Stubbed (vs production)

* `app/evidence/store.py` — in-memory recorder. Wire shape preserved (records `tenant_id` / `payload` / `article_ref` / `created_by`); `get_chain(tenant_id=..., limit=...)` returns newest-first records. No durable storage.
* `app/graph/client.py` — Neo4j stub returning `enabled=False`. Forces KB-fallback path. Restore a real Neo4j client to enable graph traversal.
* `app/llm/mistral_provider.py` — REAL httpx wrapper around `POST /v1/chat/completions`. Requires `MISTRAL_API_KEY` env var.
* `app/llm/openai_wrapper_provider.py` — NEW. Routes through `claude-code-openai-wrapper` for Sonnet 4.6 via Claude Max subscription. Detects "Not logged in" sentinel and surfaces as error.

### Two follow-up engineering fixes shipped on top of the extraction

1. **`app/integrations/regenold/scope.py::_live_question_borrows_anchor`** — restructured so STRONG follow-up markers (`what if we re-train`, `what if we retrain`, `how often`, `are these`, `tell me more`, `more details`) fire regardless of question length. The original gate required the live question to be ≤7 alphabetic tokens AND carry a marker; longer process-question follow-ups like "What if we re-train the model quarterly?" got refused as "no anchor" even when the prior assistant turn established Art. 11 unambiguously. Closes 3 multi-conversation eval refusals.

2. **`app/engines/graph_rag.py::_extract_json_object`** — robust JSON cleanup. The original markdown-fence stripper only handled the case where the entire LLM response was wrapped in ` ```json ... ``` `. Claude Sonnet 4.6 in particular ships markdown-fenced JSON with explanatory prose around it; the new helper walks three strategies (direct parse → fenced-block extraction → balanced brace-span fallback) and tolerates trailing commas + `json5`/`jsonc` language tags. Closes 2 simple-question reference-misses where Sonnet's "parsed intent" prose caused the engine to fall through to deterministic-parse with no entity extraction.

Both fixes carry regression tests in `tests/test_regenold_followup_fixes.py` (28 tests covering happy path + new behaviour + failure modes).

### Eval expansion — round 5 (this release)

Authored under this partner-transparency repo and merged into `evals/regenold/scenarios.py::SCENARIOS` via a lazy-import builder so the runner's existing `from evals.regenold.scenarios import SCENARIOS` import picks them up without changes:

* **100 multi-conversation scenarios** in `evals/regenold/scenarios_multiturn_extended.py` (category `in_scope_multi_turn`):
  - A. Pronoun / anaphor carry (12)
  - B. Process follow-ups that exercise the new `how often` / `are these` / `what if we re-train` markers (12)
  - C. Topic-shift inside the same article (12)
  - D. Cross-article carry (12)
  - E. Negative-confirmation traps (12)
  - F. Multi-turn with reference correction (12)
  - G. Long histories — anchors 3+ turns back (14)
  - H. Boundary cases — turn 1 conversational/refused, turn 2 in-scope, turn 3 follow-up (14)

* **100 tricky/misleading scenarios** in `evals/regenold/scenarios_tricky_extended.py` (10 categories × 10 scenarios):
  - `leading_premise` — "Just confirm X doesn't apply" framings
  - `non_existent_article` — out-of-range references in 10 phrasings (`Art. 1500`, `Annex XX(2)(b)`, `Annex 99`, `Art. 0`, `Art. -5`, etc.)
  - `prompt_injection` — DAN, base64, "educational only", system-prompt dump, Unicode homoglyph
  - `sycophancy` — "I'm pretty sure / surely / agree?" confirmation-seeking
  - `citation_poisoning` — bogus refs in turn-1, valid follow-up
  - `role_play_jailbreak` — persona-flip attacks
  - `mixed` — multi-regulation (NIS2, CRA, PLD, DSA, GDPR Art. 22 vs AI Act Art. 22, etc.)
  - `regulation_confusion` — AI Act anchors used for non-AI-Act content
  - `false_authority` — invented citations (`Annex VII Art. 4(2)`, fake Board guideline IDs)
  - `risk_classification` — tier-extraction traps (HR calc as minimal, satire deepfake exempt, etc.)

### Eval result snapshots

| Snapshot | Path | Pass-rate | Notes |
|----------|------|-----------|-------|
| Round 5 deterministic, 251 scenarios | `evals/regenold_results_round5_deterministic_251.json` | 196 / 251 (78.1%) | No LLM — pure deterministic-fallback path. CI-safe. |
| Round 5 Mistral live, 251 scenarios | `evals/regenold_results_round5_mistral_251.json` | TBD — see file | mistral-large-latest via httpx. |
| Round 5 Sonnet 4.6 via wrapper | `evals/regenold_results_round5_anthropic_wrapper.json` | TBD — see file | Claude Max subscription via `claude-code-openai-wrapper`. Requires interactive `login.bat` setup. See `docs/partners/regenold/SONNET_WRAPPER.md`. |

Round 5 builds on rounds 1-4 (run inside parent `legit-ai` repo):

* Round 1 baseline (deterministic, 25 scenarios): 6 / 25 (25%).
* Round 1 post-fix (after scope-filter v1 + extract-referenced-articles + lattice catalog v1): 24 / 25.
* Round 2 (eval expansion to 51 scenarios + KEYWORD_TO_ARTICLE 80-anchor sweep): 50 / 51 (98%).
* Round 2 final + round 3 (after meta-leak preamble strip + sub-paragraph chain capture + multi-article tail regex + injection regression guards): 51 / 51 (100%).
* Round 5 (this release — adds 200 new scenarios): full deterministic + LLM results above.

Snapshot history from rounds 1-3 is preserved at `evals/regenold_results_baseline.json` / `evals/regenold_results_postfix.json` / `evals/regenold_results_round2_final.json` / `evals/regenold_results_round3_final.json` — copied unchanged from the parent repo.
