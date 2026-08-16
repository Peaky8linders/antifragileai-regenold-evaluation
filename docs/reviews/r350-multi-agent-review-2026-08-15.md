# Deep Code Review: R350 — the R341→R349 change set

**Date:** 2026-08-15
**Branch:** `r350-review-and-fix` → `main`
**Base reviewed:** `ba22313` (R339) → `6fdedcb` (R349)
**Scope:** 1,342 lines of production code across 10 files (Large)
**Method:** CR-SKILL — 6 parallel specialists → skeptical verifier → outside voice

## Executive summary

Twenty-three findings survived verification. **Nothing here is broken in the shipped
default configuration** — every rerank and expansion lever is default-OFF — but the
merge gate itself was defective on its default path, and the levers about to be A/B'd
carried defects that would have made those A/Bs report confident, wrong answers.

The single most important finding: **R347's KG candidate pool put graph-sourced
provisions on the wire as citations.** Measured with an identity rerank stub (the
cross-encoder expressing no preference at all), a chatbot-transparency question gained
`Art. 98` — *Committee procedure*, comitology — and a FRIA question went from 3
references to 11. That is the over-citation axis this project has left to win, moving
3.7× in the wrong direction, via a mechanism hard rule #10 forbids on the embedded
backend.

The second: **the merge gate crashed before printing its own hard-rule-#8 veto.** A
U+2500 box-drawing character in R349's judge-provenance line is unencodable in cp1252,
which is `sys.stdout.encoding` on the documented platform. It sits between the axis
table and the `gold_dropped` block, and `_write_sidecar` ran after `_report` — so a
multi-hour live A/B printed its axis table, raised `UnicodeEncodeError`, and lost both
its verdict and every row of its data.

## Critical

### [C1] KG candidate pool admitted graph-sourced provisions to the wire
- **File:** `app/engines/_graph_rag_impl.py:2649`
- **Bug:** `pool = list(entities) + [e for e, _ in pairs]` is a superset;
  `entities = reranked` adopted all of it. `entities` → obligation
  (`"article": entity`) → `CitationNode` → wire `references`. The in-file comment
  certified "a permutation can reorder but never lose them" — true about losing,
  silent about adding. Amplified by `rerank_pool` returning `ok=True` for a
  successful NOOP, so the expansion landed even with no ranking opinion.
- **Impact:** On the default `neo4j` backend, an over-citation amplifier (source is
  `kb_xrefs`, already a legitimate retrieval input). On
  `REGENOLD_GRAPH_BACKEND=embedded`, a genuine hard-rule-#10 violation: `Art. 98`
  yields zero xref pairs, so the builder falls through to
  `get_embedded_graph().neighbors()` and six graph-sourced refs enter the adoptable
  pool.
- **Fix applied:** reranked ORDER projected back onto the original membership. KG
  neighbours inform ranking, never citation. Genuine KG recall stays a live idea but
  owes hard rule #8 a `gold_dropped` reading.
- **Found by:** Logic (95), Security (80), verifier CONFIRMED

### [C2] `_report` crash destroyed the gold veto and the sidecar
- **File:** `evals/harness/dynamic_ab.py:986`
- **Bug:** `emit(f"  ── ans_corr …")` — U+2500 is absent from cp1252.
  `sys.stdout.encoding` is `cp1252` here (verified). Judge axes are ON by default, so
  this is the default path.
- **Impact:** `UnicodeEncodeError` between the axis table and the veto block; no
  `gold_dropped` line, no `REJECTED`, and `_write_sidecar` — called after `_report` —
  never ran. `—` (U+2014) survives because cp1252 has it at 0x97, which is why it was
  easy to miss.
- **Fix applied:** ASCII prefix; `_write_sidecar` moved into a `finally`. Pinned by a
  test that cp1252-encodes every `emit(`/`print(` line.
- **Found by:** Measurement (95), reproduced independently during review

### [C3] Judge axes scored a transport timeout as the branch losing
- **File:** `evals/harness/dynamic_ab.py:791`, `865`
- **Bug:** the error filter applied to the BASELINE arm only; branch rows were selected
  by id membership. An errored branch row carries `pred_answer=""`, and
  `legal_v2._judge_row` returns a real `{"verdict": "fail", "evaluation_error":
  "empty_answer"}`. The pair filter tested the verdict STRING only.
- **Impact:** measured — one branch timeout in 3 rows produced
  `ref_corr −0.3333, n_skipped=0` on all four judge axes. A network blip reported as
  the branch losing answer quality, on the gate that decides shipping.
- **Fix applied:** symmetric error filter matching `_analyse`; `_scorable()` is now the
  single definition of "is this a real measurement", rejecting any verdict carrying an
  error marker however the string reads.
- **Found by:** Measurement (90), Concurrency (92)

### [C4] Judge silently converted `fail` → `pass` on two axes
- **File:** `evals/judge/legal_v2.py:726`, `635`
- **Bug:** `citations = raw.get("citations") or []` then `verdict = "pass" if not
  mismatched`, with no check that the array was present. `_parse_judge_json` accepts
  any balanced object carrying ANY key from a union set, not this axis's key.
- **Impact:** verified end-to-end — `{"verdict":"fail","failure_mode":"…"}` parsed
  cleanly and postprocessed to **pass** on both `citation_faithfulness` and
  `reference_correctness`, then entered the aggregate as a genuine 1.0. This is the
  **shipped grading path with no flag guarding it**, so every reference-correctness and
  citation-faithfulness number is biased upward by an unknown amount.
  (`answer_correctness` fails closed — refuted for that axis.)
- **Fix applied:** `_missing_axis_array` guard on all four postprocessors. Absent ≠
  empty: `[]` remains a legitimate finding, a MISSING key is unscorable.
- **Found by:** Measurement (65) → verifier PARTIAL/CONFIRMED, priority #1

## Important

### [I1] `REGENOLD_RERANK_KG_HOPS` was inert from the day it shipped
`app/engines/cohere_rerank.py:407`. `rerank_kg_hops()` reached only
`build_kg_candidate_pool`, used solely in the `else` of `if pairs:` — and
`cross_refs_with_reason` resolves a pair for essentially every entity. Measured: 5/5
questions byte-identical at hops=1 vs hops=2. Because the flag **was** in
`_engine_cache_key`, both arms were cache-distinct and genuinely re-ran, so the fire
check would have PASSED on Stage-2 noise and printed an axis table for a depth change
that never happened — the inert-feature trap arriving through the guard built to catch
it. Fixed: `hops` threaded into the with-reasons builder; hop-2 reasons labelled
`via <ref>:`; the 2:1 budget split now applies only at hops≥2 (it was unconditional, so
hops=1 silently capped the pool at 5 of 8). *Found by four independent specialists.*

### [I2] `fire_check` counted a transport error as the lever firing
`evals/harness/dynamic_ab.py:379`. No error filter, while `_analyse` drops rows that
errored in either arm. An errored row always differs from a healthy baseline, so a
branch timeout read as `fired=True` — and the rows that "proved" it fired were then
excluded from every axis. The harness's defining property inverted: the instrument
breaking made a dead lever look alive. Fixed; errored rows are excluded and reported as
`errored=N`.

### [I3] A 1-pair judge axis printed a resolved verdict
`evals/harness/dynamic_ab.py:339`. `_bootstrap_ci` special-cased `len==1` to `(d, d)` —
zero width — which `_verdict` read as WIN or as a "tight, useful NULL", under a header
advertising the much larger deterministic n. Fixed: unbounded interval,
`_MIN_PAIRS_FOR_VERDICT = 3` floor, and per-axis `n` printed in the table.

### [I4] Two flags were KEYED BUT FROZEN — worse than unkeyed
`app/engines/query_expansion.py:55`, `app/llm/intent_classifier.py:349`. Both read at
import while `_engine_cache_key` registered them (one with a comment asserting "read
fresh per call"). The key makes the arms cache-distinct so the engine genuinely re-runs,
live Stage-2 is non-deterministic so outputs differ, the fire check therefore PASSES —
and the harness prints a confident table for a value identical in both arms. An unkeyed
frozen flag at least reports INERT. Both made fresh-read;
`REGENOLD_INTENT_MODEL` added to the cache key.

### [I5] Uncapped conversation egress to Cohere
`app/engines/cohere_rerank.py:544`. The 600-char cap lived inside `if ctx:`, and
`rerank_references` passes no context — so a 2,334-char flattened conversation
(every prior user AND assistant turn) went to `api.cohere.com` verbatim, bounded only by
`_MAX_QUESTION_CHARS = 64,000`. The module's data-protection note disclosed "the user's
question". Fixed: `_rerank_query` bounds every path; the note now states exactly what
egresses.

### [I6] Rerank ranked against prior turns, not the live question
`app/engines/cohere_rerank.py:544`. `f"{query} — {ctx}"[:600]` sliced from the HEAD while
the live turn sits at the TAIL of the flattened multi-turn question. Measured: the 600
chars sent began `"Conversation so far: User: In turn 0 …"` and contained the live
question **not at all** — and because `ctx` is appended last and is always non-empty at
the parse-level call site, the entire R347 enrichment was cut off the end on any
question over 600 chars: the feature silently removing itself. Fixed.

### [I7] Bedrock paraphrases silently served by the wrapper
`app/engines/query_expansion.py:131`. `is_openai_wrapper_enabled()` returns False only
for the literal `"cli"`, so under `provider=bedrock` it returned True and short-circuited
before the Bedrock check — making R346's whole branch dead code. `_complete_paraphrase`
then fell through to the wrapper, which this module's own docstring forbids ("mixing
transports mid-A/B contaminates both arms"), recorded only by a `logger.debug` that
never emits. Fixed: the selected provider is asked first; a missing transport is an
error the counters can see, not a silent substitution.

### [I8] Counters that could not distinguish the failures they exist to detect
`app/engines/query_expansion.py:80`. `failed` collapsed five outcomes — including
"transport died" and "ran fine, found nothing", measured byte-identical. `expanded`
was documented as a paraphrase count but did `+1` per call (a 3× under-report of the
union surface the lever buys). `_bump` was an unlocked read-modify-write on a
process-global dict mutated from FastAPI's worker threadpool: under contention it lost
337,986–370,146 of 480,000 counts, while `cohere_rerank`'s identically-shaped counter
lost zero because it has a lock. Fixed: seven distinct counters, locked.

### [I9] Non-atomic checkpoint destroyed the previous good checkpoint
`evals/harness/dynamic_ab.py:965`. Bare `write_text` truncates before writing; an
interrupt left unparseable JSON and took the prior checkpoint with it. It is called
after every batch precisely so a killed multi-hour run keeps its rows. Fixed: temp file
+ `os.replace`.

### [I10] `--endpoint` was silently dead
`evals/harness/dynamic_ab.py:1028`. `action="store_true", default=True` can only ever
produce True, so `--endpoint` was parsed, threaded through, and ignored — an operator
aiming the merge gate at the deployed Railway service measured their local working tree.
Fixed: `BooleanOptionalAction`, `--endpoint` implies `--no-local`, and the resolved
system under test is printed.

### [I11] Rerank flags probed at the wrong control layer
`evals/harness/dynamic_ab.py:445`. `REGENOLD_RERANK_KG_*` contain `KG_`, so they inferred
`layer=graph` and probed with `REGENOLD_KG_CONTEXT=0` — a Stage-2 context switch that
cannot exercise the rerank pool. This is the R345 defect, on the flags added immediately
after R345 fixed it. Getting it wrong flips the diagnosis between "fix the feature"
(exit 2) and "fix the rows" (exit 3). Fixed, and an unmatched flag now says so out loud
instead of defaulting silently.

### [I12] Startup log advertised a model the process cannot call
`app/main.py:102` re-derived the intent-model default as
`claude-haiku-4-5-20251001`. R346.2 moved the real default to Sonnet 4.6 ("no Haiku on
the live path") and left the log. With the variable unset — the deployed configuration —
the boot line named the wrong model. Same false-attribution class as the
`METRIC_PROVENANCE` "Sentence-BERT" label. Fixed: the log asks the owner.

### [I13] `_TIMEOUT = 2.0` — the slower transport had the smaller budget
`app/engines/query_expansion.py:50`. Hard-coded, no override, while the Bedrock sibling
was 8.0 s AND overridable. R102 measured the wrapper at a **12–17 s floor for a
five-token request**; R328.2's Bedrock invokes returned in 275–1595 ms. R341 sized 2.0 s
against Haiku; R346.2 swapped in Sonnet 4.6 and left it. Fixed:
`REGENOLD_QUERY_EXPANSION_TIMEOUT`, default 20 s, fresh read, malformed values warn
instead of raising at import.

### [I14] `Infinity` in the durable sidecar — *introduced by this round's own fix*
`evals/harness/dynamic_ab.py:965`. The `(-inf, +inf)` CI from [I3] serialises via
`json.dumps` as bare `Infinity`, which Python round-trips but RFC 8259 does not define —
`jq`, browsers and every strict parser reject the whole file. Caught by the outside-voice
prompt and confirmed by execution. Fixed: `_json_safe` maps non-finite floats to `null`.
**A fix that breaks the evidence file is not a fix.**

## Suggestions

- `app/engines/_graph_rag_impl.py:2593` — the comment claimed "one Cohere call per
  request, never two". Measured with both flags ON: **4 calls in one
  `_deterministic_parse`** (docs 50/43/40/37) plus the kg-context rerank = **5 serial
  calls**, each 6 s timeout, on a scored latency axis. Comment corrected with the
  measured number; the fan-out is **not bounded** — a request-scoped call budget is a
  larger change than this round should make untested. Also means
  `--min-call-gap 6.5` paces at ~5× the Cohere Trial budget it was sized for.
- `app/engines/_graph_rag_impl.py:2404` — the R114 definitional gate is still
  `if not entities:` while its twin at `:2445` is `_original_lanes_empty`. Reported as a
  gold-drop; the **verifier REFUTED the harm** — `Art. 3` is recovered by the scoped BM25
  pre-filter on 5/5 constructed cases. Real effect is +1–3 over-citation, not a gold
  drop. Left unchanged deliberately: changing retrieval without an A/B is the thing the
  validation policy exists to prevent.
- `app/engines/cohere_rerank.py:448` — `_pool_reasons` had zero callers while its
  consumer reimplemented it inline without the 240-char clamp. Now called. Impact was
  latent, not live: max curated reason is 142 chars (0 of 147 over 240).

## Refuted / non-findings

- **Gold drop from the expansion gate asymmetry** — REFUTED by execution (above).
- **R342 annex/recital dedup** — clean. Key correct for both types, genuinely
  idempotent, every caller covered.
- **R343 tokenizer alignment** — clean, verified by object identity:
  `embeddings_index._tokenize is kb_search._tokenize` → True. The removed vendored copy
  HAD drifted (digit rule and stopword set), so the fix is real.
- **R346.1 dead-key classification** — correct, and correctly anchored on the `api_`
  prefix rather than a bare substring. Verified by execution: a dead key does not cache
  per-model and does not tunnel-hop.
- **Credential leakage** — none. No key or fragment reaches a log, trace, sidecar or
  response body.
- **Injection** — none. No Cypher/shell/path/URL is built from user text in the new code.

## Review metadata

- **Specialists:** Logic & Correctness, Error Handling & Edge Cases, Contract &
  Integration, Concurrency & State, Security & Data Egress, Measurement Integrity
- **Verifier:** 10 single-source findings; 7 confirmed, 2 partial, **1 refuted**
- **Outside voice:** Codex errored (model-refresh bug); independent Claude subagent ran
- **Raw findings:** 31 → **23 verified** → 8 dropped or downgraded
- **Cross-confirmed:** the dead hops flag by 4 specialists; the judge error handling by 2
- **Tests:** 6,491 → 6,525+ passing, 0 failures throughout
- **Steering files consulted:** `CLAUDE.md` (3 stale numbers corrected, see the R350
  doctor pass), `.planning/NEXT-SESSION.md` (3 rounds stale at review time)
