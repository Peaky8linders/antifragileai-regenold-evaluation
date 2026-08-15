# R339 adversarial audit — raw agent output (preserved verbatim)

Source workflow: r339-adversarial-audit (7 lenses + challengers; 2 lenses died on API errors).
Preserved because the harness transcript lives in a temp directory.


==========================================================================================
## agent result #1  (len 15436)
==========================================================================================

All verified. Here is the report.

---

# JUDGE-PLUMBING REPORT — R338 live answers, at `f7f85ad`

**Method note:** every claim below was produced by executing code, offline, under `OPENAI_API_BASE=http://127.0.0.1:1/v1 P2P_GRAPH_RAG_PROVIDER=cli REGENOLD_EXTERNAL_EMBEDDINGS=0`. **No LLM calls were made** — neither judge was run. Wrapper/tunnel untouched.

⚠ **Incidental credential exposure:** my env-presence probe printed `AWS_BEARER_TOKEN_BEDROCK` in full (my mask matched `_KEY`/`_TOKEN` suffixes; this var ends `_BEDROCK`). The value is now in this session's transcript. Rotate it if these logs leave your machine. I have not reproduced it here.

## 1. PLUMBING

Both judges share one loader and one row-normaliser: `evals/judge/legal_v2.py:136-145` imports `_load_rows`, `_norm`, `_answer_grounding_block`, `_has_independent_answer_grounding` and all four caps **from `grounded.py`**. So there is one plumbing contract, not two. `legal_v2` adds a 4th axis (`answer_conciseness`) and quote-or-retract post-processing.

**The live artifact does not load at all — silently.**

```
_load_rows('.evalout/r118/live_r338-opus48.json')                     -> 0 rows
_load_rows('evals/bench/results/graphrag-bench-r338-opus48...json')   -> 40 rows
```

`grounded.py:461` scans only `("rows","qa","scenarios","tricky","multiturn","ground_truth")`. The live file's top keys are `antifragile_rows` / `medtech_rows`, so it matches nothing, and `grounded.py:467` returns `[]` because the payload is a dict. This does **not** raise — `_aggregate([])` returns a complete scorecard:

```
{'n': 0, 'pass': 0, 'fail': 0, 'error': 0, 'pass_rate': 0.0, ...}
```

A **silent zero**, exactly the class this repo keeps getting burned by. The graphrag file loads natively (its `ground_truth.rows` matches) — but its sibling `no_ground_truth` key is *not* in the tuple and is silently dropped (0 rows today, so harmless now).

**Three further traps, each measured:**

| # | Trap | Evidence |
|---|---|---|
| T1 | The supplied-context key is **`gold_context`**, not `independent_gold_context`. Writing the intuitive name is ignored and the row falls through to `predicted_refs_fallback_circular` — the exact self-grading you're trying to avoid. | `grounded.py:110-113`; measured: `independent_gold_context -> passed=False, src=predicted_refs_fallback_circular` vs `gold_context -> passed=True, src=independent_gold_context` |
| T2 | Medtech rows key the question as **`final_question`**; `_norm` reads `question`/`live_question` (`grounded.py:126`). All 10 medtech questions arrive **empty** (`q_len=0`). | measured on raw rows |
| T3 | `answer_preview` is a 400-char truncation. Harmless *here* because `_norm` prefers `predicted_answer` (`grounded.py:127-128`), but it is third in the same fallback chain. | `predicted_answer len=5498`, `answer_preview len=400`, preview is a prefix |

**Converter written** (the one file I wrote):
`C:\Users\th3un\AppData\Local\Temp\claude\D--Claude-Projects-antifragileai-regenold-evaluation\d254734a-e2ba-44bb-a77e-6c0df1c3a35e\scratchpad\r338_to_judge_sidecar.py`

It emits **`.jsonl`**, which `_load_rows` reads line-by-line with no key-name dependency — sidestepping the whole failure class. It self-verifies through the judge's own `_load_rows`/`_norm`/`_answer_grounding_source`. Measured output:

```
antifragile: 20 rows  src={'independent_gold_context': 20}  recall 20/20  CIRCULAR=0
medtech    : 10 rows  src={'independent_gold_context': 10}  recall 10/10  CIRCULAR=0  (1 empty answer)
graphrag   : 40 rows  src={'independent_gold_context': 38, 'predicted_refs_fallback_circular': 2}
```

Outputs in `.../scratchpad/sidecars/r338-{antifragile,medtech,graphrag}.judge.jsonl`.

The 2 residual circular rows are `gt_06` (minimal_risk) and `gt_07` (guiding_principles) — **their gold is the empty set**, so nothing exists to ground on. Note `gt_06` is the R338 report's showcase over-citation row (§3): the one row you most want judged is the one the judge would self-grade. Exclude it from answer-correctness or report it separately.

## 2. KNOWN DEFECTS — ALL FOUR STILL PRESENT AT `f7f85ad`

### (a) `legal_v2._prepare` circular grounding + inert strict flag — **CONFIRMED, with an important scope limit**

`legal_v2.py:525-526`:
```python
candidate_refs = list(dict.fromkeys((r.get("gold_refs") or []) + (r.get("pred_refs") or [])))
gold_map = _resolve_provision_texts(candidate_refs, _GOLD_TEXT_CAP, _MAX_GOLD_REFS)
```
`grep -c GROUNDED_JUDGE_STRICT_GROUNDING evals/judge/legal_v2.py` → **0 hits** (grounded.py: 2). Executed with the flag set to `1`:

```
strict flag active in grounded.py: True
grounded.py -> answer_correctness UNSCORABLE (skipped)? True
legal_v2    -> answer_correctness UNSCORABLE (skipped)? False   <- flag has NO effect
legal_v2 _prepare grounding keys: ['Article 5']                 <- built from pred_refs
```

The `_judge_row` guard at `legal_v2.py:1010-1015` OR-s in `bool(r.get("pred_refs"))`, so any row with predictions is scorable regardless of the flag. **There is no off-switch on `legal_v2`.**

**Scope limit that matters for your decision:** line 522 branches on `_has_independent_answer_grounding(r)` *first*, which is true when `gold_refs` is non-empty (`grounded.py:189-194`). The Antifragile rows **have** gold_refs, so they take line 523 (`_answer_grounding_block` → verbatim gold text), **not** the circular branch. Measured on raw rows before any conversion: `src=gold_refs` on all 20. So this defect does **not** corrupt Antifragile answer-correctness — it bites only on gold-free rows (`gt_06`, `gt_07`).

### (b) `NON_EXISTENT_PROVISION` gate is head-lax — **CONFIRMED, and it inverts**

`legal_v2.py:658-663` gates on `provision_exists`. Executed:

| ref | `provision_exists` | `get_provision_text` |
|---|---|---|
| `Article 3.999` | **True** | None |
| `Article 3.14a` | **True** | None |
| `Annex III.4.employment` | **True** | None |
| `Article 999` | False | None |

Only a bad *head* is caught. Then the substantiation gate actively rewards the fabrication — executed:

```
pred=['Article 3.14a','Article 9'];  judge classifies 3.14a as WRONG
-> wrong_refs: []
-> supporting_refs: ['Article 3.14a']
-> legal_soundness_precision = 1.0
```

A non-existent provision scores a **perfect** legal-soundness precision, because there is no text to quote from, so `WRONG` is downgraded to `SUPPORTING` (`legal_v2.py:666-671`).

**Honest scope limit:** I scanned all 231 predicted refs in the R338 artifacts — **0 unresolvable** (antifragile 61/61, medtech 47/47, graphrag 123/123 resolve to verbatim text). So this defect is **latent on this dataset, not active**. It would not corrupt your R338 numbers. Fix it before running on data with fabrications.

### (c) Conciseness prompt loosening ungated — **CONFIRMED**

`grep -n REGENOLD_JUDGE_CONCISENESS_LENIENCY evals/judge/legal_v2.py` → exactly **one** hit, line **821**, in post-processing. The prompt half at `legal_v2.py:498-508` contains **0** `getenv` calls. `git blame` attributes those lines to **`bb793cae` (2026-08-14)**. So `answer_conciseness` runs on a strictly more permissive ruler than any pre-`bb793ca` number, under the same axis name — R327's "change the formula, change its NAME" violated. **Do not compare a new `answer_conciseness` figure to any historical one.**

### (d) `REGENOLD_JUDGE_MAX_TOKENS=1600` — **CLAUDE.md is CORRECT here; unification verified**

All five transports call `_judge_max_tokens()`: `runner.py:213` (wrapper/sonnet), `:295` (bedrock), `:388` (groq), `:447` (gemini), `:507` (anthropic). Executed: default `1600`; `REGENOLD_JUDGE_MAX_TOKENS=3000` → `3000`; clamped to `[200, 8000]` (`runner.py:238-249`). Bedrock still lets `REGENOLD_BEDROCK_JUDGE_MAX_TOKENS` win (`:285-290`) — documented, intentional.

**The silent-zero mechanism is real but mitigated.** Executed: `is_retryable_judge_error('unbalanced_json')` → **False** (also `no_json`, `empty_response`). So a truncated reply is terminal. And `pass_rate` does divide by total rows (`grounded.py:526`). Demonstrated on 6 pass / 2 fail / 2 truncated:

```
pass_rate             = 0.6    <- divides by TOTAL incl. errors
pass_rate_over_non_error = 0.75 <- the honest one
```

Both are emitted, and `_fmt` prints both (`grounded.py:663-664`). **Read `pass_rate_over_non_error` and the `err=` count; never quote `pass_rate` alone.** My rendered prompts max at **42,340 chars (~10.6K tokens)** input — output at 1600 is the real risk, and 20 predicted refs × JSON is comfortably inside it.

## 3. NEW DEFECT FOUND (not in your list)

**A predicted ref beyond `_MAX_PRED_REFS=8` is never shown to the judge, yet is booked as SUPPORTING.**

`_prepare` builds `pred_map` capped at 8 (`legal_v2.py:529`), but `_postprocess_reference_correctness` iterates the **full** `pred_refs` list (`legal_v2.py:649`). An unseen ref has no classification, falls to the `else` at `:676-680`, and is appended to `supporting`. Executed on **q14** (9 refs — the row the R338 report flags as regressed):

```
pred_map shown to judge (8): [Art 6, 43, Annex I, 5, 9, 10, 11, 12]
NEVER SHOWN TO JUDGE:        ['Article 13']
-> supporting: ['Article 13']
-> legal_soundness_precision: 0.0 -> 0.1111
```

1 of 20 Antifragile rows is affected today. The converter **warns** rather than hiding it. Raise `_MAX_PRED_REFS` to ≥12 before quoting reference precision.

## 4. ITEM 3 — CAN ANSWER-CORRECTNESS BE SCORED? **YES, non-circularly. A gold answer exists.**

The premise "no gold ANSWER" is **false at the repo level** — the live artifact simply doesn't propagate it. `evals/regenold/antifragile_groundtruth.ANTIFRAGILE_GT` carries a `gold_answer` per qid. Measured join:

```
live ids n=20;  ANTIFRAGILE_GT join 20/20;  reviewer-remarks join 20/20
gold_answer chars: min 320  median 449  max 692   zero-length: 0
review      chars: min 8    median 392  max 1250  zero-length: 0
```

And the gold refs are fully resolvable against the pin:
```
gold_refs         47/47 resolve to verbatim text
gold_subpoint_refs 50/50 resolve to verbatim text
```

So the recommended grounding is a three-part independent block, none of it prediction-derived:
1. verbatim `get_provision_text` of gold + gold-subpoint refs,
2. the `ANTIFRAGILE_GT.gold_answer`,
3. *(opt-in)* the expert reviewer's verbatim `review`.

⚠ **Two authoring cautions the converter encodes.**

- **`gold_subpoint_refs` is NOT a superset of `gold_refs`** — 13 of 20 rows differ, and q13/q15 carry sub-points whose heads the subpoint list *drops* (q13 subpoint `['Article 6.1']` vs gold `['Article 5','Article 50','Article 6']`). Use the **union**, or you lose gold in one direction or the other. Union never exceeds `_MAX_GOLD_REFS=6` on any row (measured 0/20 over), and building the context ourselves bypasses that cap anyway.
- **The reviewer remarks describe a *different* answer.** They critique the earlier "Lexy" build (`antifragile_reviewer_remarks.py:1-22`). Handed to a judge un-disclaimed, "the answer addresses only the unacceptable tier" reads as a finding about the answer under review. That is a contamination risk, so remarks are **opt-in** (`--grounding remarks`) and wrapped in an explicit scope disclaimer.

**Medtech: answer-correctness is grounded on gold-ref text only** — there is no gold answer anywhere in the repo for those 10 rows. It is meaningful (non-circular) but weaker. `mt_med_07` has an empty answer (the HTTP 422) and scores a deterministic fail on every axis while staying in the denominator (`grounded.py:376-385`).

**graphrag `gt_06`/`gt_07`: answer-correctness genuinely cannot be scored.** Empty gold, no independent grounding possible. Report them as excluded, not as failures.

## 5. RECOMMENDED RUN

Use **`legal_v2`** — it has the quote-or-retract gate that catches the cite-and-mismatch class, plus the conciseness axis. Its known defects are either scope-limited (a), latent on this data (b), or a comparability caveat (c).

```bash
# 1. convert (offline, no LLM)
cd "D:/Claude Projects/antifragileai-regenold-evaluation"
py -3.12 "C:/Users/th3un/AppData/Local/Temp/claude/D--Claude-Projects-antifragileai-regenold-evaluation/d254734a-e2ba-44bb-a77e-6c0df1c3a35e/scratchpad/r338_to_judge_sidecar.py" \
    --out "C:/Users/th3un/AppData/Local/Temp/claude/.../scratchpad/sidecars"

# 2. judge — ONE AT A TIME, after the orchestrator's live eval has finished
$env:PYTHONIOENCODING="utf-8"
$env:REGENOLD_JUDGE_MAX_TOKENS="2400"          # headroom; 1600 is tight for 9-ref rows
$env:REGENOLD_JUDGE_CONCISENESS_LENIENCY="0"   # keep the post-proc half OFF (default)

py -3.12 -m evals.judge.legal_v2 \
    --sidecar "<scratchpad>/sidecars/r338-antifragile.judge.jsonl" \
    --label r338-antifragile-legalv2 \
    --model claude-sonnet-5 --provider wrapper \
    --timeout 120 --concurrency 2 --samples 3 --max-retries 5
```

Then repeat for `r338-medtech.judge.jsonl` and `r338-graphrag.judge.jsonl`.

**Parameter rationale (all measured):**
- **model `claude-sonnet-5`** — the default (`legal_v2.py:148`) and the model the July-7 baseline was graded with, so numbers stay comparable. **Do not use `--provider bedrock`**: CLAUDE.md records sonnet-5 as 403 there, degrading to `sonnet-4-6`, which sets `judge_model_comparable=False`.
- **provider `wrapper`** — the only transport whose model matches the baseline. `ANTHROPIC_API_KEY` is UNSET, so `--provider anthropic` is unavailable. `GROQ_API_KEY`/`GEMINI_API_KEY` are set but are different graders.
- **concurrency 2** — the default; CLAUDE.md records the tunnel failing in bursts under load, and `.env` `OPENAI_API_BASE` points at `wrapper.antifragile-ai.net`, i.e. **this run goes through the tunnel**. ⚠ **Serialize it** — this repo's rule is never two wrapper-bound jobs at once.
- **timeout 120** — above the 90 default; prompts reach ~10.6K tokens.
- **`--samples 3`** — the in-file recommendation (`legal_v2.py:1356-1360`); majority verdict damps judge noise. Budget: 70 rows × 4 axes × 3 = **840 calls**, so run the three sidecars separately.
- **`--max-retries 5`** — the default (`legal_v2.py:951`), sized for the measured ~60% transient `api_status_500` rate on this path. Note it will **not** rescue `unbalanced_json`.

**Before quoting any number:** read `err=` per axis and use **`pass_rate_over_non_error`**; check `judge_model_served` / `judge_model_comparable`; and treat `answer_conciseness` as non-comparable to history (defect c).

## 6. WHAT I COULD NOT DETERMINE

- **Whether the judge produces good numbers.** I did not run it — no LLM calls permitted. Everything above is plumbing and post-processing verified offline; the model's actual behaviour on these prompts is untested.
- **Transport reliability right now.** I could not probe the wrapper or tunnel, so the ~60% transient-failure figure in `legal_v2.py:1367-1370` is quoted from the source, **not** re-measured this session.
- **Whether `REGENOLD_JUDGE_MAX_TOKENS=2400` is sufficient.** I measured input size (42K chars max) but cannot measure output length without running the judge. 1600 is the unverified risk; 2400 is a reasoned margin, not a measurement.
- **Defect (b)'s real-world impact.** Zero unresolvable refs in this data means I proved the mechanism but could not observe it firing on R338 output.
- **CLAUDE.md staleness re: the deployed provider** — outside my lens; I made no live endpoint probes, so I neither confirm nor dispute the orchestrator's `stage2_model=claude-opus-5` finding.

==========================================================================================
## agent result #2  (len 28166)
==========================================================================================

I've completed the analysis. All findings below are backed by output I ran.

---

# R338 remaining ranked items — mechanics and exact fixes

**Repo state verified:** `git log` → `f7f85ad` HEAD. `GET /healthz` on the Railway service → `{"status":"ok","version":"1.2.3","commit":"f7f85ad6f6de","deployment_id":"2d916ba1-...","is_groq_enabled":true}` — **the deployed commit is HEAD**, so everything below describes what is live.

---

## ITEM 1 — `run_graphrag_benchmark.py` records no Stage-2 provenance

### 1.1 Root cause: it is a *missing query param*, not a missing scraper

Measured on the R338 artefact `evals/bench/results/graphrag-bench-r338-opus48-graphrag.json`:

```
label=r338-opus48-graphrag  mode=graphrag-benchmark-live
endpoint: http://127.0.0.1:8100/api/v1/regenold/eu-ai-act/ask     <-- NO query string
n gt 40  n ng 0
reasoning present count gt: 0      (all 40 rows carry reasoning == "")
```

The runner *does* store `"reasoning": body.get("reasoning")` (`evals/regenold/run_graphrag_benchmark.py:102` for GT rows, `:140` for NG rows) — the field is simply always empty, because the route only serialises the trace when asked. Proven by execution (deterministic, `provider=cli`, TestClient):

```
/api/v1/regenold/eu-ai-act/ask                        200 reasoning= ''
/api/v1/regenold/eu-ai-act/ask?include_reasoning=true 200 reasoning= '{"schema_version":"r50.1",...'
```

Mechanism: `app/routes/regenold.py:5627 _maybe_serialize_reasoning()` returns `None` when `include_reasoning` is False. So the sidecar's `stage2_model` gap is **entirely** a URL problem on the `--endpoint` path.

`--local` is *already fine*: `run_graphrag_benchmark.py:251` calls `_local_endpoint_url("include_reasoning=true")`. Only the live path is blind.

### 1.2 Is the query param an observer effect? — measured, NO (under shipped defaults)

This is a live CLAUDE.md-adjacent staleness finding. Two in-tree comments assert `?include_reasoning=true` **forces Stage-2**:

* `app/routes/regenold.py:1963-1970` (R104): *"activates the per-request reasoning trace, which ... forces Stage-2 polish + the Opus complex-model path AND bypasses the confidence floor"*
* `evals/harness/easyhard_ab.py:37` (R112): *"NO `?include_reasoning=true` — it forces Stage-2 and distorts an eval comparison"*

Measured: `app/engines/_graph_rag_impl.py:8160-8166` sets `force_stage2 = True` when a trace is active, and `force_stage2` has **exactly two consumers** (`grep -n force_stage2` → 8152, 8156, 8160, 8164, 8175, 8186, 8195, 8277):

| consumer | gate | measured default |
| --- | --- | --- |
| `:8195` suppresses the simple-question skip | `REGENOLD_STAGE2_SIMPLE_SKIP` (`_graph_rag_impl.py:1455`, `getenv(..., "0")`) | `_stage2_simple_skip_enabled() = False` |
| `:8277-8289` supplemental DuckDuckGo search | `app/engines/web_search.py:47 is_web_search_enabled()` | `is_web_search_enabled() = False` |

So under shipped defaults **the param is behaviourally inert** and `run_live_deep_eval.py:260-289`'s account is the correct one; the R104 and R112 comments are stale. It does still fold `reasoning:{0|1}` into `_engine_cache_key` (`regenold.py:1968`), so a reasoning run and a plain run never share a cache entry — correct, but it means you cannot mix the two in one A/B.

### 1.3 Exact fix for `evals/regenold/run_graphrag_benchmark.py`

Copy the canonical treatment. The canonical scraper is `evals/regenold/run_official_batch.py:79 _provenance()` (already imported this way by `evals/bench/run_cappelli_bench.py:52`). The canonical URL-append is `run_official_batch.py:509-510`.

**(a) Append the query param on the live path.** `run_graphrag_benchmark.py:250-256`, in `main()`, immediately after `endpoint = args.endpoint`:

```python
if "include_reasoning" not in endpoint:
    endpoint = f"{endpoint}{'&' if '?' in endpoint else '?'}include_reasoning=true"
```

Verbatim the pattern at `run_official_batch.py:509-510` and `evals/regenold/antifragile_live.py:404-405`. `evals/bench/_http_retry.py:348 post_json_with_retry` passes `url` through unmodified, so nothing strips it.

**(b) Import the canonical scraper.** After `run_graphrag_benchmark.py:46`:

```python
from evals.regenold.run_official_batch import _provenance
```

Do **not** write a second scraper — `run_cappelli_bench.py:46-52` carries the note explaining why.

**(c) Per-row provenance.** In the GT row dict (`:90-110`, next to `:102`) and the NG row dict (`:133-145`, next to `:140`), add:

```python
"http_status": status,
"stage2_landed": bool(_provenance(body).get("stage2_polish")),
"stage2_model": (_provenance(body).get("stage2_model") or ""),
"retrieval_path": _provenance(body).get("retrieval_path"),
```

(compute `prov = _provenance(body)` once above the dict, as `run_cappelli_bench.py:224-225` does).

**(d) Run-level provenance block.** In `payload` (`:179-186`), add a `run_provenance` key mirroring `run_cappelli_bench.py:319-333` / `run_live_deep_eval.py:598-611`:

```python
"run_provenance": {
    "endpoint_resolved": endpoint,            # shows the ?include_reasoning=true
    "transport": "local" if use_local else "http",
    "resolved_provider": <see note>,
    "stage2_landed_rate": <landed / n_ok>,
    "stage2_models": sorted({r["stage2_model"] for r in all_rows if r["stage2_model"]}),
    "mean_latency_ms": <mean over non-error rows>,
    "looks_deterministic": <bool>,
    "deterministic_reasons": [...],
},
```

⚠ **`resolved_provider` differs from the two R338 runners and this is the catch.** `run_cappelli_bench` and `run_live_deep_eval` drive an **in-process** `TestClient`, so `resolve_run_provider()` (`run_cappelli_bench.py:104-128`) genuinely determines what runs. `run_graphrag_benchmark` with `--endpoint` posts to a **separate process** (the R338 run used `http://127.0.0.1:8100`), so the runner's own env decides nothing. Therefore:

* `--local`: adopt `run_cappelli_bench.resolve_run_provider` verbatim (read-with-default, never assign over an exported value) and record `resolved_provider`.
* `--endpoint`: record `"resolved_provider": "remote:unknown"` and rely on the **observed** `stage2_models` set from the traces. Recording a locally-resolved provider for a remote server would be an active false attribution — exactly the failure `run_official_batch._provenance`'s docstring (`:82-88`) was written against.

**(e) Print it above the numbers.** `_format()` (`:196-230`) — add the provider/`stage2_landed_rate`/`stage2_models`/`mean_latency` line before `[GROUND TRUTH]`, matching `run_cappelli_bench.py:363-379`, and the `INSTRUMENT WARNING` when `looks_deterministic`.

**Detector calibration for this suite:** the 2-second mean-latency heuristic from `run_cappelli_bench.py:312` is **wrong here**. Measured per-row latencies on the R338 sidecar are bimodal — 5 rows under 100 ms and 12 rows over 3 s (`[3843, 4870, ..., 83, 422, 407, 341, 115, 56, 74, ...]`) — because the curated intercepts genuinely ship deterministic answers on this corpus. Use `stage2_landed_rate == 0.0` as the alarm and report `mean_latency_ms` as data, not as a second trigger.

### 1.4 Other runners with the same gap

Audited every module with an `--endpoint` argument (`grep -rl 'add_argument("--endpoint"' evals/`), checking for the auto-append pattern and for any Stage-2 provenance:

| file | appends `include_reasoning` on `--endpoint`? | records Stage-2 provenance? |
| --- | --- | --- |
| `evals/regenold/run_official_batch.py:509` | ✅ | ✅ `_provenance` |
| `evals/regenold/run_evaluator_batch_july7.py:448` | ✅ | ✅ |
| `evals/regenold/antifragile_live.py:404` | ✅ | ✅ `_parse_reasoning` |
| `evals/regenold/run_medtech_subpoint_eval.py:79` | ✅ (`"?" in endpoint` form) | partial |
| `evals/regenold/runner_oob.py:303` | ✅ (baked into the default URL) | ✗ |
| **`evals/regenold/run_graphrag_benchmark.py`** | **✗ (`:251` local only)** | **✗** |
| **`evals/harness/dynamic_ab.py`** | **✗ — zero mentions of `include_reasoning`, zero of `stage2_polish`** | **✗** |
| **`evals/harness/easyhard_ab.py:37`** | **✗ by deliberate policy, on the now-falsified R112 claim** | **✗** |
| `evals/regenold/run_medtech.py:232`, `run_public_graphrag_bench.py:201`, `run_paper_v3.py`, `run_paper_v4.py:346`, `run_docx_exact.py`, `run_hard_sample_r297.py`, `run_june_batch.py`, `run_medtech_graphrag_v124.py`, `runner_r89_probe.py` | ✗ (local-only append, same shape as graphrag) | ✗ |
| `evals/bench/run_live_benchmark.py`, `evals/regenold/run_omnibus_probe_r318.py`, `evals/regenold/run_medtech_lifesci_r136.py` | ✗ (no mention at all) | ✗ |

**Rank the fixes:** `dynamic_ab` first (it is the designated merge gate and it records nothing — see Item 4), then `run_graphrag_benchmark`, then `easyhard_ab` (whose docstring rationale is now measured false), then the long tail.

Note on `dynamic_ab`: its `--local` path is accidentally saved — `_run_rows` (`dynamic_ab.py:399-402`) builds `"local://app.main:app/api/v1/regenold/eu-ai-act/ask"` with no `?`, and `runner_v2._post_local:210` defaults `qs = "include_reasoning=true"` when the endpoint has no `?`. So the trace *is* returned; `_row_record` (`dynamic_ab.py:366-379`) just never reads `body["reasoning"]`. The `--endpoint` path gets nothing.

---

## ITEM 2 — the 4 000-char per-message cap that 422'd `mt_med_07`

### 2.1 The validator

`app/integrations/regenold/models.py:49`

```python
content: str = Field(min_length=0, max_length=4_000)
```

with the recorded rationale at `:36-40` (P0 #5, *"cap at 4K (was 20K). 4K covers any realistic regulatory Q&A while keeping token cost + retrieval-bloat bounded; a 20K prompt-injection would still be quietly accepted at the validation layer pre-fix"*) and the companion `messages: list[...] = Field(min_length=1, max_length=64)` at `:61`, whose comment (`:55-60`) states the DoS arithmetic explicitly: **64 × 4 KB ≈ 256 KB upper bound on the request body**. The 422 is raised at `app/routes/regenold.py:7094-7105`.

### 2.2 The cap is not hit by user input — it is hit by *our own answer*

Measured turn lengths of every medtech scenario (`evals/regenold/scenarios_medtech_multiturn_r118.py`):

```
mt_med_07 [235, 163, 182] max= 235      <-- every USER turn is tiny
```

`mt_med_07`'s longest user turn is **235 characters**. The 422 came from the *assistant* turn: `evals/regenold/antifragile_live.py:299` echoes each answer back into history (`history.append({"role": "assistant", "content": ans})`), and the R338 artefact records `mt_med_07`'s turn-1 answer at **4 301 chars**.

Reproduced deterministically (`provider=cli`, TestClient, exact recorded answer):

```
mt_med_07 turn-1 ANSWER chars = 4301
per-message chars = [235, 4301, 163]
status 422
{"detail": {"code": "regenold_invalid_input", ...,
 "errors": [{"loc": ["messages", 1, "content"], "type": "string_too_long",
             "msg": "String should have at most 4000 characters"}]}}
```

`loc: ["messages", 1, ...]` — index 1, the **assistant** message. This is a self-inconsistent contract: `REGENOLD_ANSWER_NO_CAP` (default ON, hard rule #2) removes the answer-length cap, so the service emits answers it will then reject on the next turn.

**How close is the rest of the suite?** Over all 48 recorded answers in `.evalout/r118/live_r338-opus48.json`: `max 5498, p95 3991, p50 766.5, over-4000: 3, over-3000: 5`. `mt_med_10` turn-3 landed at **3 991 chars** — nine characters from the same 422.

### 2.3 The downstream already tolerates far more, which decides the fix

`app/routes/regenold.py:2061-2084 _max_question_chars()` defaults to **64 000** (`app/models.py:54 _MAX_QUESTION_CHARS`), with `_HISTORY_TURNS_TO_INCLUDE = 40` at `:2058`, and the flattener left-truncates when it overflows (`:6934-6960`). So the pipeline's own budget for the *flattened* conversation is 16× the per-message cap. The 4 000 cap is not protecting anything downstream — it is an isolated validation-layer bound.

There is **no body-size middleware** (`grep -rn "content_length|max_body|BodySizeLimit|request_size" app/` → no hits), so the Pydantic caps are the only bound on request size. That is the real security argument and it must be preserved: the rate limit is `60/minute` keyed / `30/minute` anonymous (`app/routes/regenold.py:2183-2191`).

### 2.4 Recommended fix: **role-asymmetric cap, in the model — and chunking is the wrong lever**

Chunking in the runner is wrong: it would mean the eval harness edits the model's own prior answer before feeding it back, which changes the thing being measured and papers over a contract defect that a real multi-turn partner client will hit in production the same way.

Raising the cap uniformly is also wrong: it multiplies the worst-case body by the raise factor on an anonymous 30/min tier.

**Split the cap by role.** `app/integrations/regenold/models.py:27-49` — replace the single `content` field with a `model_validator(mode="after")` on `RegenoldChatMessage` (or two message subtypes) enforcing:

* `role in ("user", "system")` → **4 000** (unchanged — this is the untrusted-input surface the P0 #5 rationale is actually about, and it keeps both pinning tests green)
* `role == "assistant"` → **16 000** (covers the measured max 5 498 with ~3× headroom; assistant content is prior *model output* being replayed, and `_build_question_from_history` already left-truncates the flattened result at 64 000)

Then update the DoS arithmetic comment at `:55-60` and consider lowering `messages` `max_length` from 64 to keep the worst case bounded: 64 × 16 000 = 1 MB. If you want to hold the current 256 KB envelope exactly, pair the assistant raise with `max_length=24` on `messages` (24 turns is 12 exchanges; `_HISTORY_TURNS_TO_INCLUDE` is 40, so this would newly bind — decide deliberately, don't do it by accident).

Also update the 422 message at `app/routes/regenold.py:7098-7102`, which hard-codes the literal "4000 characters" and would become wrong.

**Tests that pin the current cap** (both use `role="user"`, so a role-asymmetric fix leaves them green — verified: `tests/test_regenold_integration.py:15-16 _messages()` builds a user message):

* `tests/test_regenold_integration.py:155-163` — 5 000-char user question must 400/422
* `tests/test_regenold_integration.py:166-179 test_p0_question_at_4k_boundary_accepted` — exactly 4 000 must return 200

Add a new test: a 6 000-char **assistant** turn between two short user turns must return 200.

**Blast radius of the model change** (`grep -rn RegenoldChatMessage app/ tests/`): `app/integrations/regenold/models.py:27,61`, `app/integrations/regenold/scope.py:3754` (duck-typed on `.role`/`.content`), and three test files (`test_issue151_system_role_injection.py`, `test_multiturn_coherence.py`, `test_regenold_integration.py`). Small.

---

## ITEM 3 — medtech multi-turn "coherence" 0.2222

### 3.1 How `coherent` is computed — it is not a coherence metric

`evals/regenold/antifragile_live.py:324-325`:

```python
"coherent": (refm["loose"] >= 0.5 and kw >= 0.5
             and not any(m in answer_low for m in REFUSAL_MARKERS)),
```

aggregated at `:383` as `coherence_rate = sum(coherent) / len(ok)`.

`refm` and `kw` are computed at `:308-309` from `final_body` only (`:305-306`). **The metric never reads turn 1 or turn 2.** It checks no cross-turn consistency, no contradiction, no anaphora resolution, no topic persistence. It is a conjunction of two thresholded single-answer accuracy proxies applied to the last turn — the same `ref_loose` and `keyword_recall` already reported one line above it in the same summary. Calling it "coherence" violates R327's standing rule in CLAUDE.md ("a NAME must describe what the code COMPUTES").

The scenario module supports nothing better today: `scenarios_medtech_multiturn_r118.MEDTECH_MULTITURN[0].keys() = ['domain','expected_keywords','expected_refs','id','notes','turns']` — **there is no per-turn gold**, only final-turn gold. `evals/bench/mtrag.py:53-107` implements a per-turn variant (`pred_bases & gold_bases` on every turn), but it requires `turn["gold_refs"]`, which this dataset does not carry.

### 3.2 Decomposing the 0.2222

`coherence_rate = 2/9` (n=10, n_ok=9 after `mt_med_07`'s 422). Per row:

```
id          refL    kw refuse   coh  which_gate_failed
mt_med_01  0.500 0.400  False False  ['kw']
mt_med_02  0.333 0.200  False False  ['ref_loose', 'kw']
mt_med_03  0.250 0.600  False False  ['ref_loose']
mt_med_04  1.000 0.600  False  True  []
mt_med_05  0.000 0.000  False False  ['ref_loose', 'kw']
mt_med_06  1.000 0.400  False False  ['kw']
mt_med_07 ERROR
mt_med_08  0.000 0.600  False False  ['ref_loose']
mt_med_09  0.200 0.600  False False  ['ref_loose']
mt_med_10  0.500 0.600  False  True  []
```

Two rows (`mt_med_01`, `mt_med_06`) fail on **keyword recall alone at 0.400 against a 0.5 threshold on a 5-keyword list** — i.e. 2 hits out of 5 vs a threshold needing 3. `mt_med_01` cites `[Article 6, Article 14, Article 16, Article 11, Article 13, Article 17, Article 18]` against gold `[Article 6, Article 14, Article 43, Annex I]` — 2 of 4 gold recovered, and the answer is on-topic. Those two are threshold artefacts of a conjunctive gate, not incoherence.

### 3.3 …but the rest is a real answer defect, and a severe one

Marker scan of the 9 final answers:

```
mt_med_02  coh=False  opens='Under Article 53, GPAI providers must maintai'  gpai_markers=[Annex XI, training-data summary, GPAI, Article 53]
mt_med_03  coh=False  opens='Under Article 53, GPAI providers must maintai'  gpai_markers=[...]
mt_med_05  coh=False  opens='GPAI provider obligations: maintain technical'  gpai_markers=[...]
mt_med_06  coh=False  opens='Under Article 50, limited-risk transparency: '  gpai_markers=[...]
mt_med_08  coh=False  opens='Under Article 53, GPAI providers must maintai'  gpai_markers=[..., Codes of Practice]
mt_med_04  coh=True   opens='Under Article 51, a GPAI model has systemic r'  (legitimately a GPAI scenario)
```

**5 of 9 medical-device answers open with general-purpose-AI-model boilerplate.** `mt_med_05`'s final question is *"a limited pre-market technical validation on 500 patients before full CE marking — does the Act apply during that validation phase?"* and the answer is entirely Article 53(2) open-source carve-outs and Annex XI/XII. That is a genuine catastrophic topic failure, not a metric artefact.

**Verdict: both, and the answer problem dominates.** ~2 of 7 failures are threshold artefacts; ~5 are real.

### 3.4 The real defect is deterministic and reproducible offline

Every medtech row shows `retrieval_path: kb_fallback` and `stage2_polish: false` (**1 of 10** medtech rows landed Stage-2; **3 of 20** antifragile rows). So these answers are deterministic KB-stub concatenation, and can be debugged with no LLM at all.

`mt_med_08` turn 1 — *"a wearable for hospital staff that monitors physiological indicators of cognitive fatigue and stress during shifts, with the aim of alerting managers when a clinician may be impaired. Does the AI Act prohibit this?"* — textbook Article 5(1)(f) emotion recognition in the workplace. I reproduced its turn-1 answer with **no history and `provider=cli`**:

```
mt_med_08 T1 SINGLE-TURN refs= ['Article 68', 'Article 56', 'Article 57']
    ans: Establishes a Scientific Panel of independent experts to support enforcement of Chapter V (GPAI)...
```

and the entity parse shows exactly where it goes wrong:

```
_deterministic_parse(q).entities =
  ['Art. 68', 'Art. 56', 'Art. 57', 'Art. 5', 'Art. 4', 'Art. 3', 'Art. 9', 'Art. 10']
```

**`Art. 5` IS retrieved — at rank 4 — and never reaches the wire.** The three refs that do are the Scientific Panel (68), Codes of Practice (56) and Scientific Panel of experts (57). This is a *ranking* defect on the deterministic path, isolated to a single-turn question, no Stage-2 involved.

Turns 2 and 3 then compound it: `mt_med_08`'s turn-2 and turn-3 refs are `['Article 53','Article 55','Article 56','Article 57','Article 68']` and `['Article 55','Article 56','Article 57','Annex XI','Article 53.1.a','Article 53.2']` — the wrong turn-1 answer is echoed into history at `antifragile_live.py:299`, flattened into the retrieval question, and locks the conversation onto GPAI for the rest of the scenario. Same shape in `mt_med_03` (turn 1 answers Article 50 limited-risk transparency for a hospital that rebranded a high-risk diagnostic system).

### 3.5 Fix instructions

1. **Rename the metric.** `evals/regenold/antifragile_live.py:324` `"coherent"` → `"final_turn_pass"`, and `:383` `"coherence_rate"` → `"final_turn_pass_rate"`. Nothing else in `evals/` reads the medtech key (`grep -rn coheren evals/` → only `bench/compare.py:80-87`, which reads a `multiturn_coherence` sub-dict this runner never writes, and `bench/mtrag.py` / `bench/prod_runner.py:447`, both independent). Do not silently keep the name — CLAUDE.md's R327 rule.
2. **If a real coherence number is wanted**, the dataset needs per-turn gold. Add `expected_refs_per_turn: [[...], [...], [...]]` to `evals/regenold/scenarios_medtech_multiturn_r118.py` (the `notes` field already carries the legal reasoning for each turn), then score with the existing `evals/bench/mtrag.py:45-107` scorer rather than writing a third definition.
3. **The real bug to fix is the ranking**, and it needs no LLM: `mt_med_08` turn 1, `provider=cli`, must put `Art. 5` on the wire. Debug from `_deterministic_parse` → `_retrieve_from_kb` in `app/engines/_graph_rag_impl.py`. It is a clean deterministic repro and a candidate for `dynamic_ab` with the `gold_dropped` veto.

---

## ITEM 4 — a probe set where the curated Stage-2 intercept does not fire

### 4.1 Headline: **the probe set is already almost entirely clean — 130 of 132 rows survive**

Measured with the two live predicates (`_curated_stage2_skip_enabled() = True`, `_definitional_stage2_skip_enabled() = True`), first on `ProbeRow.live_question`, then re-measured faithfully by running each row's messages through `app.routes.regenold._build_question_from_history` and testing the **`resolved_question`** — which is what `_graph_rag_impl.py:8222` and `:8241` actually gate on (R305). Both passes give the same answer:

```
total rows 132
curated hits 2 | definitional hits 0
SURVIVORS 130

  paper_st_v4          total= 20 skipped=  0 survive= 20
  paper_tricky_v4      total= 20 skipped=  0 survive= 20
  paper_mt_v4          total= 12 skipped=  0 survive= 12
  tricky_v2            total= 31 skipped=  2 survive= 29
  mt_v2                total= 25 skipped=  0 survive= 25
  lower_risk_v149      total= 12 skipped=  0 survive= 12
  multiarticle_r268    total= 12 skipped=  0 survive= 12

--- curated intercept hits:
    tricky_v2:tr_v2_009 | An importer rebrands a high-risk AI under its own name before selling it on...
    tricky_v2:tr_v2_017 | We use emotion recognition in a medical-device AI to monitor pain in non-verbal...
```

**This contradicts the framing of R338 §5.3.** The intercept problem is specific to the *Antifragile* suite, not to `probe_set`. On the Antifragile 20, the same predicates hit **11 of 20**:

```
q02 q05 q06 q07 q09 q10 q11 q12 q17 q20  -> curated (10)
q08                                       -> definitional (1)
```

and Stage-2 landed on 3 (`q01`, `q13`, `q18`). So on that suite the intercepts explain 11 of the 17 non-landings — and the **remaining 6 rows (`q03`, `q04`, `q14`, `q15`, `q16`, `q19`) passed every intercept, reached `_claude_max_enhance_answer`, and Stage-2 still did not land.** That second population is unexplained by the R338 report and is worth its own investigation; note `q03`, `q04` and `q14` are exactly the three regressed rows in R338 §2.

### 4.2 The build/filter recipe

Because the curated gate is nearly inert on `probe_set`, the work is **not** filtering — it is **instrumentation**. `dynamic_ab` cannot currently report whether Stage-2 fired on any row.

**Step 1 — make `dynamic_ab` observe Stage-2.** `evals/harness/dynamic_ab.py`:

* `_run_rows:399-402` — when `local`, the URL has no `?` so `runner_v2._post_local:210` already sends `include_reasoning=true`. When `--endpoint`, append it with the `run_official_batch.py:509-510` pattern.
* `_row_record:366-379` — add `"stage2_landed"`, `"stage2_model"`, `"retrieval_path"` from `run_official_batch._provenance(body)`. `_run_rows` must thread `body` into `_row_record` (currently it passes only `answer`/`refs` at `:411-414`). Keep it inside `_row_record` — that function's own docstring (`:343-364`) is the record of what happens when the producer and the consumer of a row shape drift apart.
* Report `stage2_landed_rate` per arm in the sidecar, and make the **fire check** consult it: an arm on a Stage-2 flag with `stage2_landed_rate == 0.0` is `INERT` regardless of whether the answers differ.

**Step 2 — add the filter to `probe_set`.** `evals/harness/probe_set.py:120-157 load_probe_set()` — add a keyword-only parameter:

```python
def load_probe_set(*, sources=None, categories=None, multiturn=None,
                   stage2_reachable: bool | None = None, limit=None):
```

Implemented after the `categories` filter at `:152-153`:

```python
if stage2_reachable is not None:
    from app.engines._graph_rag_impl import (
        _is_curated_authoritative_intercept, _detect_pure_definitional_inquiry,
    )
    q = pr.live_question
    reachable = not (_is_curated_authoritative_intercept(q)
                     or _detect_pure_definitional_inquiry(q))
    if reachable != stage2_reachable:
        continue
```

Two caveats a fixer must not skip:

* `probe_set.py`'s docstring promises *"Pure stdlib + the existing scenario modules. No I/O at import time."* Keep the `app.engines` import **inside** the function body so importing `probe_set` still costs nothing.
* The gates run on `resolved_question`, not on the raw final turn. For the 37 multi-turn rows (`paper_mt_v4` 12 + `mt_v2` 25) `live_question` is an approximation — though I verified against the real `_build_question_from_history` resolver and both give **2 hits**, so it makes no difference on today's corpus. If you want it exact, resolve via `_build_question_from_history` inside the filter; the cost is pulling `app.routes.regenold` into the loader.

**Step 3 — expose it.** Add `--stage2-reachable` to `dynamic_ab`'s argparse (near `:750`) and thread it into `load_probe_set()` at `dynamic_ab.py:462`. With `_stratified()` at `:424-444` unchanged, a 130-row pool still round-robins across all seven sources.

### 4.3 What this does *not* buy you

Surviving the curated intercept is necessary, not sufficient. Two further gates sit between a probe row and a landed Stage-2 polish, neither observable from the predicate:

* `_graph_rag_impl.py:8177 _stage2_polish_enabled()` and `:8181 _stage2_provider_enabled()` — a downed wrapper returns `(kg_answer, False)` and the row is silently deterministic.
* the `_claude_max_enhance_answer` call at `:8291` itself, which can fail and fall back — the 6 unexplained Antifragile rows above.

Only the `stage2_landed_rate` from Step 1 answers "did Stage-2 run?". Build Step 1 first; the filter is cosmetic without it.

---

## What I could NOT determine

* **Whether the 130 surviving probe rows actually land Stage-2.** That requires a live wrapper run, which I was forbidden from making. The 130 figure is an upper bound on Stage-2-observable rows, not a measurement of them.
* **Why `q03`, `q04`, `q14`, `q15`, `q16`, `q19` did not land Stage-2** despite passing both intercepts. The recorded artefact carries `stage2_polish: false` but no note distinguishing "provider disabled" from "enhance call failed". Adding a `record_note` at the `_graph_rag_impl.py:8177` / `:8181` early returns would close this — currently only the *skip* branches (`:8202`, `:8227`, `:8246`) leave a trace, so the two most likely causes of a silent deterministic ship are the two that record nothing.
* **The provider actually serving the R338 graphrag run.** The sidecar carries no provenance at all — that is the whole of Item 1 — and the endpoint (`127.0.0.1:8100`) is a process that no longer exists. It cannot be recovered.
* **Whether the medtech ranking defect (Item 3.4) also affects the 132-row probe set.** I did not run it; the `mt_med_08` repro is single-row.

==========================================================================================
## agent result #3  (len 29420)
==========================================================================================

## bypass-mechanics — adversarial audit + experiment design

Everything below was executed. Env for all offline runs: `PYTHONIOENCODING=utf-8 OPENAI_API_BASE=http://127.0.0.1:1/v1 P2P_GRAPH_RAG_PROVIDER=cli REGENOLD_EXTERNAL_EMBEDDINGS=0`, `py -3.12`. Scratch scripts under the session scratchpad (`gatefire.py`, `af_power.py`, `fidelity.py`, `det_def.py`).

---

## 1. MECHANICS

### 1.1 The gate ladder in `_two_stage_generate` (`app/engines/_graph_rag_impl.py:8125-8249`)

Order matters and settles part of the experiment design:

| line | gate | env | true default |
|---|---|---|---|
| `:8177` | `_stage2_polish_enabled()` | `P2P_GRAPH_RAG_ENABLE_STAGE2` | ON (`:1371`) |
| `:8181` | `_stage2_provider_enabled()` | `P2P_GRAPH_RAG_PROVIDER` | `cli` ⇒ **returns here** (`:1302-1324`) |
| `:8193` | `_stage2_simple_skip_enabled()` × `not force_stage2` × `not _needs_stage2_enhancement` | `REGENOLD_STAGE2_SIMPLE_SKIP` | **OFF** (`:1455`, `"0"` default) |
| **`:8222`** | **gate A** `_curated_stage2_skip_enabled()` × `_is_curated_authoritative_intercept(resolved_q)` | **`REGENOLD_CURATED_STAGE2_SKIP`** | **ON** (`:4473-4480`, `"1"` default) |
| **`:8241`** | **gate B** `_definitional_stage2_skip_enabled()` × `_detect_pure_definitional_inquiry(resolved_q)` | **`REGENOLD_DEFINITIONAL_STAGE2_SKIP`** | **ON** (`:4435-4441`, `"1"` default) |

**Load-bearing consequence:** the provider gate at `:8181` returns *before* both gates. Under `provider=cli` neither flag is reachable, so any `--deterministic` / cli-arm A/B on these flags is **inert by construction**. (R338's doc cites the gates as `~:8222` and `~:8232`; `:8232` is the start of gate B's comment, the `if` is `:8241`.)

`resolved_q = resolved_question or question` (`:8149`), sourced from `request.resolved_question or request.question` (`:8908`) — the **live turn**, not the flattened history (R305 fix, comment `:8217-8221`).

### 1.2 What makes a question "curated authoritative"

`_is_curated_authoritative_intercept` (`:4516-4570`) is a **flat disjunction of 27 hand-written detectors** — no scoring, no threshold, any one match wins:

```
 1 guiding_principles      2 minimal_risk            3 article_6_3
 4 research_scope          5 high_risk_penalty       6 emotion_classification
 7 systems_or_models       8 annex_iii_8_admin_justice  9 annex_iii_8_election
10 explainability         11 reclassification       12 ai_board_governance
13 sme_simplified_doc     14 workplace_worker_notification
15 art50_text_public_interest  16 risk_framework    17 prohibited_practices
18 deepfake_criminal_exception 19 testing_data_definition
20 retention_docs         21 special_data_bias      22 tech_doc_certificate
23 hardware_techdoc       24 deviation_detection    25 role_difference
26 user_information       27 robotic_surgery
```

Each is a regex/keyword predicate over the latest turn (each strips a `"Latest question:\n"` prefix first, e.g. `:4276-4281`), paired with a hardcoded verdict inside `_deterministic_answer` (`:4664+`). The semantic claim is "this question's answer is a curated closed-set/scope verdict that Stage-2 must not rewrite."

The same predicate is *also* read at the route (`app/routes/regenold.py:7400`) for the R111.1/R274 curated-ref-protect. **Flipping `REGENOLD_CURATED_STAGE2_SKIP` does not disable that** — it isolates the Stage-2 skip only. Good for the A/B.

Gate B (`_detect_pure_definitional_inquiry`, `:4412-4432`): `select_definition_sentence(q) is not None AND definition_citation_for_question(q) is not None`, minus a provider∧deployer guard. Deliberately **not** wired into the curated predicate (`:4406-4411`).

### 1.3 Fire rates — RUN, all four datasets

```
ANTIFRAGILE (expert-review 20)   CUR 10/20   DEF 1/20   EITHER 11/20  (55.0%)
GRAPHRAG BENCHMARK       n=40    CUR 11/40   DEF 3/40   EITHER 14/40  (35.0%)
OFFICIAL BATCH (July-7)  n=110   CUR 19/110  DEF 4/110  EITHER 22/110 (20.0%)
PROBE_SET (dynamic_ab)   n=132   CUR  2/132  DEF 0/132  EITHER  2/132 ( 1.5%)
```

Antifragile per-row table:

```
id    CUR   DEF   question
q01   False False What risk categories are provided for AI systems?
q02   True  False What types of AI systems or practices are explicitly prohibited by the AI Act?
q03   False False What is the definition of high risk?
q04   False False Which sectors or applications are considered high-risk under the regulation?
q05   True  False How should users be informed when interacting with AI systems?
q06   True  False What are AI systems with minimal risks?
q07   True  False What are the guiding principles established by the AI Act?
q08   False True  What is the definition of a "system of artificial intelligence"?
q09   True  False What are the penalties ... for high-risk AI systems?
q10   True  False What is the difference between the deployer and the provider?
q11   True  False Does the technical documentation ... require ... hardware?
q12   True  False Are AI systems intended for emotion recognition ... always prohibited?
q13   False False Is an AI that transcribes doctor–patient conversations prohibited? ...
q14   False False We are a medical device manufacturer ... X-rays ...
q15   False False Can a hospital use an AI system to sort patients ...
q16   False False Our life sciences startup developed a general-purpose AI model ...
q17   True  False We are a university lab developing an AI model exclusively for research ...
q18   False False We are developing a generative AI chatbot ... hospital website ...
q19   False False A pharmaceutical company ... monitor the emotions and stress ...
q20   True  False Is an AI system ... safety component in robotic surgery ...?
```

probe_set hits are exactly two, both `tricky_v2`: `tr_v2_009` (importer rebrand → `_detect_reclassification_inquiry`), `tr_v2_017` (emotion recognition in medical device). By source: `lower_risk_v149 0/12`, `mt_v2 0/25`, `multiarticle_r268 0/12`, `paper_mt_v4 0/12`, `paper_st_v4 0/20`, `paper_tricky_v4 0/20`, `tricky_v2 2/31`.

**Caveat I could not eliminate:** I evaluated the predicates on the raw final user turn (`ProbeRow.live_question`). Live, the route passes a coref/de-noiser-resolved string. For the 37 multi-turn probe rows the resolved text may differ; all of them scored False and none is near a detector's surface, so the direction of any error is toward *more* False, not fewer.

### 1.4 The R338 artefact validates the predicate exactly — and corrects R338's own diagnosis

Cross-tabulating my offline prediction against `.evalout/r118/live_r338-opus48.json`:

```
id    CUR   DEF   stage2_polish  stage2_model      complex  answer_route                    ms   mistakes
q01   F     F     True           claude-opus-4-8   False    synthesis:synthesis_default    5255   3/4
q02   T     F     False          None              None     None                           3643   3/3
q03   F     F     False          claude-opus-4-8   False    synthesis:synthesis_default   10903   1/3
q04   F     F     False          claude-opus-4-8   False    synthesis:synthesis_default    7307   1/2
q05   T     F     False          None              None     None                            835   1/2
q06   T     F     False          None              None     None                            598   2/2
q07   T     F     False          None              None     None                            378   2/2
q08   F     T     False          None              None     None                           3221   0/0
q09   T     F     False          None              None     None                            101   2/2
q10   T     F     False          None              None     None                            104   2/2
q11   T     F     False          None              None     None                             86   2/2
q12   T     F     False          None              None     None                             88   2/2
q13   F     F     True           claude-opus-4-8   True     synthesis:complex_question     3499   1/1
q14   F     F     False          claude-opus-4-8   True     synthesis:complex_question     3802   0/2
q15   F     F     False          claude-opus-4-8   False    synthesis:synthesis_default     941   0/2
q16   F     F     False          claude-opus-4-8   True     synthesis:complex_question     3688   2/2
q17   T     F     False          None              None     None                           3597   1/1
q18   F     F     True           claude-opus-4-8   True     synthesis:complex_question     6073   2/3
q19   F     F     False          claude-opus-4-8   False    synthesis:synthesis_default     926   0/0
q20   T     F     False          None              None     None                            128   1/1

gate fires: 11   stage2_polish TRUE: 3
gate fires AND stage2 ran (contradictions): []   →  predicate agreement 20/20
```

Two things follow that R338's write-up does **not** say:

1. **The two gates explain 11 of the 17 non-polished rows, not all 17.** The other **6 rows (q03, q04, q14, q15, q16, q19) called Opus 4.8 and threw the answer away.** `stage2_model=` is recorded at model-selection time (`:776-780`), *before* the wrapper call, so its presence proves an attempt; `answer_route=synthesis:…` is only recorded at `:8265`, i.e. downstream of both gates, so its presence independently proves the gates did not fire. On the 9 non-gated rows the discard rate is **6/9 = 67%** — a larger loss channel than either gate, and undocumented.
2. **R338 §2 says the q03/q04/q14 regression is on rows "none of which runs Stage-2."** That is true of *polish landing* and false of *Stage-2 executing*: all three carry `stage2_model=claude-opus-4-8`. The correct diagnosis for those rows is "Opus ran and its output was rejected," which is a different bisect target from "answer-assembly change."

**Gap I could not close:** which rejection channel dropped each of the 6. The candidates are `:8301` `stage2_failed_both_providers_deterministic_ship`, `:8360` `stage2_drift_guard_dropped_polish`, `:8386` `stage2_contradiction_guard_dropped_polish`, `guard_cross_tier_polish` (`:8415`), `verify_and_repair` (`:8468`), and the verdict guard. `antifragile_live._parse_reasoning` (`antifragile_live.py:135-159`) keeps only 7 scalar fields and **discards the raw `notes` list** — `grep -c "stage2_failed_both_providers\|drift_guard_dropped\|contradiction_guard_dropped" .evalout/r118/live_r338-opus48.json` → **0**. Persisting `notes` verbatim is a one-line instrumentation fix and is a prerequisite for any of the experiments below.

---

## 2. ENV FLAGS AND TRUE DEFAULTS

| gate | env var | default in code | off-switch |
|---|---|---|---|
| A (curated) | `REGENOLD_CURATED_STAGE2_SKIP` | **ON** — `os.getenv(..., "1") not in ("0","false","no","off")`, `_graph_rag_impl.py:4478-4480` | `=0` |
| B (definitional) | `REGENOLD_DEFINITIONAL_STAGE2_SKIP` | **ON** — same shape, `_graph_rag_impl.py:4439-4441` | `=0` |

Neither appears in the CLAUDE.md flag table. Both **are** in `_engine_cache_key` (`app/routes/regenold.py:1928-1929`), so an in-process arm flip is not cache-poisoned — proven by execution:

```
base             f4cb390dbddd4a3f718377ea
CURATED=0        a5be0a1c0c62fe0d3375c4c0 DIFFERS
DEFINITIONAL=0   f5c4fb1b7373324a169a9c4d DIFFERS
```

---

## 3. THE R275 EVIDENCE — **FALSIFIED against the repo's own primary source**

### The claim

`_graph_rag_impl.py:8232-8237`:
> *"live Stage-2 (Opus) paraphrases it and non-deterministically drops the operative clause (the expert failed Q8 for dropping the AI-system 'infers … how to generate outputs' clause)."*

`docs/ROUNDS.md:9605-9607` (Round 275, 2026-07-05):
> *"live Stage-2 (Opus) paraphrased it and **non-deterministically dropped the inference clause** (the expert failed the exact sample that dropped it)."*

Repeated at `docs/R338-live-opus48-antifragile-graphrag.md:49-51`.

### The primary source says the opposite

`Antifragile AI Review Questions and Answers.docx` (repo root) — extracted from `word/document.xml`, 115 paragraphs, 20 `Q` lines, **exactly one Q8 block**:

```
Q8: What is the definition of a "system of artificial intelligence"?
A: A machine-based system that is designed to operate with varying levels of autonomy and that may
   exhibit adaptiveness after deployment, and that, for explicit or implicit objectives, infers,
   from the input it receives, how to generate outputs such as predictions, content,
   recommendations, or decisions that can influence physical or virtual environments.
Citations: Article 3, Article 2
Review: Correct.
```

The reviewed sample **contains the operative clause in full**, and the expert's verdict is **"Correct."** Both derived encodings agree:

- `evals/regenold/antifragile_reviewer_remarks.py` → `q08.review == "Correct."`
- `evals/regenold/antifragile_groundtruth.py` → `q08.verdict == "correct"`, `q08.mistakes == []`

**So the load-bearing premise "the expert failed Q8 for exactly this" is false.** I searched `docs/ROUNDS.md`, `docs/reviews/`, `.planning/` and the R118 artefacts and found **no recorded before/after sample, sidecar, or trace of the alleged Opus paraphrase**. The underlying phenomenon may well have been observed in an unrecorded live probe — but there is no artefact, and the one piece of evidence that *is* recorded contradicts the attribution. Gate B's justification is, on the record, an anecdote plus a misattribution.

### Was the model/prompt configuration different? — measured

| | R111 (2026-06-09) | R144 (2026-06-21) | R275 (2026-07-05) | today (`f7f85ad`) |
|---|---|---|---|---|
| Stage-2 model (`app/config.py`) | `model = claude-sonnet-4-6`, **no `stage2_model` field** | `stage2_model = claude-opus-4-8` | `stage2_model = claude-opus-4-8` (`31881df:app/config.py:33`) | `claude-opus-5` (`:33`); R338 local run served `claude-opus-4-8` |
| wrapper model alias | none (table landed `757f0cb`, 2026-07-30) | none | **none** — `grep -ci alias` on `31881df:app/llm/openai_wrapper_provider.py` → **0** | table exists, default **OFF** since R308 |
| `USER_*` clauses in `graph_rag_prompts.py` | **0** | 0 | **0** | **5** |
| prompt module size | — | — | **260 lines** | **988 lines** |
| system slot delivered? | **no** | **no** | **no** — wrapper forwarding did not exist until `54e919e` (2026-07-19), and shipped default OFF | **yes** — `claude-code-openai-wrapper/.env:101 WRAPPER_FORWARD_SYSTEM_PROMPT=1` |

**Verdict on expiry, split by axis:**

- **Model axis: the evidence has NOT expired.** R275 and R144 both ran on `claude-opus-4-8` with no alias rewriting it — the same tier R338 measured. "It was a weaker model back then" is not available as an argument. (R111 *is* Sonnet-4.6-era and that half is genuinely stale.)
- **Prompt axis: the evidence HAS expired.** At R275 the Opus that allegedly paraphrased the definition received **zero** system-prompt instruction and **zero** user-channel clauses. Today it receives `ANSWER_GENERATE_SYSTEM` (~12.8K tokens) plus 5 user clauses, including `USER_SUBPARAGRAPH_ATTRIBUTION_CLAUSE` and rule **12b CLOSED-SET COMPLETENESS** (`app/data/graph_rag_prompts.py:81`) — the rule that directly targets R111's "Sonnet deleted the 7-principle list." Until 2026-08-15 that rule reached the model 0% of the time; `USER_SUBPARAGRAPH_ATTRIBUTION_CLAUSE` (`:607`) still points at it as *"the closed-set completeness rule above"* — a dangling pointer documented in-tree at `docs/ROUNDS.md:10802-10807`.
- **Attribution axis: FALSIFIED**, per the docx.

### The R111/R144 evidence, audited the same way

- **R111** (`ROUNDS.md:6031-6035`): *"a `_is_curated_authoritative_intercept` short-circuit … so Stage-2 polish can no longer DROP the closed-set enumeration (live: **Sonnet** had shortened it to just the Art 1 / Art 4 framing)."* — n=1, Sonnet 4.6, no artefact, no prompt.
- **R144** (`ROUNDS.md:7810-7842`) is the **strongest** of the three: it records an actual live re-probe with references — degenerate `[Article 5, 5.1.f]`, `stage2=True`, 21.2 s → correct cross-tier `[Article 5, 5.1.f, 50.3, Annex III.1.c, Article 50]`, `stage2=False`, 4.1 s. Still n=1 question, Opus 4.8, system prompt dropped.

**But R144's failure mode is now structurally guarded by a non-binary mechanism that the skip pre-empts.** `app/engines/stage2_fidelity.py` (R146) says so in its own docstring: *"R144's fix for the curated set was a binary SKIP … This module is the intelligent combine … generalising the R144 emotion fix to EVERY cross-tier classification."* Executed, with the R144 degraded polish as input:

```
REGENOLD_STAGE2_FIDELITY enabled: True   mode: fallback     (stage2_fidelity.py:145-152)

q12 emotion (R144)          det tiers=[high_risk, limited, prohibited]  polish tiers=[prohibited]
                            cross_tier_ask=True   action='fallback_verdict_flip'  restored_deterministic=True
q06 minimal risk (R111)     cross_tier_ask=False  action='not_classification_ask'  restored=False
q07 guiding principles      cross_tier_ask=False  action='not_classification_ask'  restored=False
q09 penalties               cross_tier_ask=False  action='not_classification_ask'  restored=False
q17 R&D scope               cross_tier_ask=False  action='not_classification_ask'  restored=False
q02 prohibited              cross_tier_ask=False  action='not_classification_ask'  restored=False
q10 role difference         cross_tier_ask=False  action='not_classification_ask'  restored=False
```

So: **gate A's R144 justification is redundant today** (R146 catches it and returns the complete deterministic verdict anyway). Gate A's **R111 justifications are NOT redundant** — R146's question gate excludes all of them, and their only protection is now rule 12b on a channel that has been live for one day.

And the deterministic side of gate B's claim still holds, measured:

```
definition_citation_for_question(Q8) -> Art. 3.1
select_definition_sentence(Q8)       -> "...infers, from the input it receives, how to generate outputs..."
get_provision_text("Article 3.1")     -> 372 chars, contains 'infers'   (leaf-validated, not provision_exists)
```

### One more thing the operator should see before flipping anything

`app/engines/_graph_rag_impl.py:7790-7791`, in the delivered-channel comment:

> *"**Do NOT "fix" this by forwarding the system prompt**: R282 already measured that as rubric-NEGATIVE (kw_recall -0.267, off-topic drift)."*

The corrected account at `app/data/graph_rag_prompts.py:521-533` confirms the measurement is real and well-powered: *"easyhard_ab n=40/arm, plus a pairwise sweep 8/8, p~0.008"*, root cause "12.8K tokens OVERWHELM the question." The wrapper's own commit `54e919e` carries the same warning. `WRAPPER_FORWARD_SYSTEM_PROMPT=1` is now set anyway, and R338's headline `keyword_recall 0.8252 → 0.7583` is directionally consistent with it. **The Stage-2 bypass question is now confounded with an un-A/B'd system-prompt flip that a prior n=40 A/B called harmful.** Any arm you run must record which state the wrapper was in.

---

## 4. EXPERIMENT DESIGN

### 4.1 `evals.harness.dynamic_ab` is **structurally blind** to both flags. Do not run it.

Three independent reasons, all verified:

1. **Population.** `run()` calls `load_probe_set()` then `_stratified(...)` (`dynamic_ab.py:462-463`) and exposes **no row-selection hook** (`main()` argparse, `:735-751`, has `--max-rows/--batch/--seed` only). Only **2 of 132** rows fire either gate. At the default `--max-rows 60`, stratified round-robin gives `tricky_v2` ~9 of its 31 rows, so **E[gate-firing rows] ≈ 2 × 9/31 ≈ 0.6**. Even at the full 132 the maximum n is **2**. `easyhard_ab` shares the pool (`easyhard_ab.py:519`) and is equally blind.
2. **The sensitivity control will not catch it — it will actively mislead.** `_LAYER_HINTS` maps `"CURATED"` → `stage2` (`:271`), so `resolve_control` picks `P2P_GRAPH_RAG_ENABLE_STAGE2=0` (`:261`). That control *will* move most probe rows, so `probe_sensitivity_check` reports `sensitive=True`, the harness does **not** emit `BLIND_PROBE`, and the run prints a clean **`INERT`** — read by any human as "this flag does nothing." The control tests the *layer*, not the *gate*; a gate that fires on 1.5% of rows is invisible to it.
3. **Gold grain.** probe_set: **208 gold refs, 0 leaf-grained** (`_carries_sub_point` over all 132 rows). The exact-grain half of the hard-rule-#8 veto is `applicable=False` for every row, so the veto that matters for a Stage-2-vs-deterministic comparison cannot be read.

Corollary: a `--deterministic` arm is impossible anyway — the provider gate at `:8181` returns before either flag.

### 4.2 The right instrument: `evals.regenold.antifragile_live`, two server instances

It is the only harness in-tree whose rows actually fire the gates and whose gold is rich enough:

| | probe_set (dynamic_ab) | Antifragile 20 |
|---|---|---|
| rows where a gate fires | **2 / 132** | **11 / 20** |
| gold refs on firing rows | 3 | **25** |
| leaf-grained gold on firing rows | **0** | **14** (`Article 50.1-.4`, `Article 99.4/.6`, `Annex IV.1.e`, `Annex IV.2.c`, `Article 5.1.f`, `Annex III.1.c`, `Article 50.3`, `Article 3.1`, `Article 2.6`, `Article 6.1`) |
| expert-flagged mistakes on firing rows | 0 | **19 of 38** (`_mistake_resolved`, `antifragile_live.py:162-200`) |
| built-in negative control | none | **9 non-firing rows must be byte-identical across arms** |

Per-row measured breakdown of the firing set:

```
q02 3 mistakes, 1 head gold, 1 subpoint ref, 0 leaf     q11 2 / 2 / 3 / 2
q05 2 / 1 / 4 / 4                                       q12 2 / 3 / 3 / 3
q06 2 / 3 / 3 / 0                                       q17 1 / 1 / 1 / 1
q07 2 / 1 / 1 / 0                                       q20 1 / 4 / 4 / 1
q08 0 / 1 / 1 / 1   (gate B — carries ZERO mistakes)    q09 2 / 1 / 2 / 2
q10 2 / 2 / 2 / 0
```

`antifragile_live` POSTs an HTTP endpoint (`_post`, `antifragile_live.py:260`; `LIVE_ENDPOINT` at `:78`), and `run_antifragile` runs **all 20 rows** regardless of `--limit`. The flags are read server-side, so the arms are **two app processes with different env**, not an in-process flip.

### 4.3 Experiment A — gate A, `REGENOLD_CURATED_STAGE2_SKIP`

- **Rows:** all 20 Antifragile (11 treatment + 9 negative control) ∪ 14 GraphRAG-benchmark firing rows ∪ 22 official-batch firing rows = **47 treatment rows** across three suites.
  - GraphRAG firing: `med_10, gt_02, gt_05, gt_06, gt_07, gt_09, gt_10, gt_11, gt_12, med_04, med_07` (CUR) + `gt_08, ng_07, ng_08` (DEF).
  - Official firing (CUR): `rg_001, rg_002, rg_005, rg_006, rg_009, rg_011, rg_012, rg_022, rg_025, rg_027, rg_032, rg_033, rg_039, rg_040, rg_041, rg_042, rg_043, rg_074, rg_103`.
- **Repeats:** **k = 3 per arm.** The R275/R144 claim is *literally about non-determinism* ("non-deterministically drops"). One sample per arm cannot test a variance claim — it is the single largest design error available here.
- **Axes:** `ans_strict`, `ans_conciseness`, `keyword_recall`, `ref_strict`, `ref_conciseness`, **`ref_subpoint_strict` / `ref_subpoint_loose`** (`_subpoint_metrics`, `antifragile_live.py:42-68`), **`mistakes_resolved` /38**, `regulatory_tone`, latency p50/p95.
- **VETO (hard rule #8):** zero gold dropped at head grain **and** at exact grain on the 14 leaf-grained coordinates. Any coordinate lost by the ON→OFF flip is a rejection irrespective of every other number.
- **FIRE CHECK, run before any number:** the 11 firing rows must show `stage2_polish=True` in arm OFF and `False` in arm ON; the 9 non-firing rows must be unchanged. If arm OFF still shows `stage2_polish=False` on a firing row, the flip did not fire and the run is void.
- **Decision rule to flip the default to OFF (Stage-2 allowed to run):** on the 47 treatment rows, `mistakes_resolved` **non-inferior** (delta ≥ 0 with a bootstrap 95% CI lower bound > −1 mistake), `gold_dropped == 0` on both grains, **and** at least one of `ans_strict` / `ref_subpoint_strict` improving with a CI excluding zero. Anything else keeps the default ON. If the variance across the 3 repeats in arm OFF exceeds the ON arm's on the same row, that alone re-validates the original stability argument and the gate stays.

**Commands** (do not run — orchestrator only; the wrapper is serialized):

```bash
# arm A = baseline (gate ON, current default)
cd "D:/Claude Projects/antifragileai-regenold-evaluation"
OPENAI_API_BASE=http://127.0.0.1:8000/v1 OPENAI_API_KEY=dummy \
P2P_GRAPH_RAG_PROVIDER=openai_wrapper NEO4J_AUTO_SEED=0 \
REGENOLD_CURATED_STAGE2_SKIP=1 \
py -3.12 -m uvicorn app.main:app --host 127.0.0.1 --port 8100 --log-level warning

# arm B = branch (gate OFF, Stage-2 allowed on curated rows) — SECOND, never concurrent
...same env... REGENOLD_CURATED_STAGE2_SKIP=0 ... --port 8101

# 3 repeats per arm, per suite
for k in 1 2 3; do
  py -3.12 -m evals.regenold.antifragile_live --label curON-r$k  --set both \
      --endpoint http://127.0.0.1:8100/api/v1/regenold/eu-ai-act/ask --throttle 1.5
done
for k in 1 2 3; do
  py -3.12 -m evals.regenold.antifragile_live --label curOFF-r$k --set both \
      --endpoint http://127.0.0.1:8101/api/v1/regenold/eu-ai-act/ask --throttle 1.5
done

# the graded turn, on the 22 official firing rows (also closes open item #2)
py -3.12 -m evals.regenold.run_official_batch --label curON  --mode hard
py -3.12 -m evals.regenold.run_official_batch --label curOFF --mode hard
py -3.12 -m evals.judge.grounded --sidecar evals/bench/results/official-curON-hard.ckpt.jsonl \
    --label curON --model claude-sonnet-5 --provider wrapper --timeout 120 --concurrency 3
```

**Prerequisite before any of this:** persist the raw `notes` list in `antifragile_live._parse_reasoning` (`:135-159`). Without it a discarded polish is indistinguishable from a skipped one, which is precisely the ambiguity that made the 6 discarded R338 rows unattributable.

### 4.4 Experiment B — gate B, `REGENOLD_DEFINITIONAL_STAGE2_SKIP`

Must be run **separately**; folding it into Experiment A confounds two levers.

- **The problem:** gate B fires on **8 rows total** across all three suites — Antifragile `q08`; GraphRAG `gt_08, ng_07, ng_08`; official `rg_011, rg_019, rg_038, rg_076` — and **`q08` carries 0 of the 38 expert mistakes**. So the mistake axis is dead on the Antifragile row and the only usable outcome is a text-level one.
- **The right axis is a direct assertion, not a rubric.** The claim is "Opus drops the operative clause." Test it as such: for each of the 8 rows, resolve the gold definition leaf via `get_provision_text` (never `provision_exists` — `provision_exists("Article 3.999")` is True) and check whether every operative sub-clause survives in the answer. For `q08`/`gt_08` that is the three tokens `infers` / `from the input it receives` / `how to generate outputs`, all three of which I verified are present in the deterministic sentence today.
- **Power:** 8 rows × **k = 5 repeats** per arm (40 samples/arm). The claim is about *non-deterministic* dropping; a drop rate of even 10% needs ~30 samples/arm to be distinguishable from zero.
- **Decision rule:** if arm OFF drops an operative clause on **0 of 40** samples, gate B is unnecessary at the current prompt configuration and should be defaulted OFF (with the flag kept). Any non-zero drop rate keeps it ON, and *that* result — with an artefact — is the evidence R275 never recorded.
- **Same wrapper caveat:** record `WRAPPER_FORWARD_SYSTEM_PROMPT` state in both arms.

```bash
# arm A: REGENOLD_DEFINITIONAL_STAGE2_SKIP=1 (default) on :8100
# arm B: REGENOLD_DEFINITIONAL_STAGE2_SKIP=0            on :8101
for k in 1 2 3 4 5; do
  py -3.12 -m evals.regenold.antifragile_live --label defON-r$k  --set antifragile \
      --endpoint http://127.0.0.1:8100/api/v1/regenold/eu-ai-act/ask
  py -3.12 -m evals.regenold.antifragile_live --label defOFF-r$k --set antifragile \
      --endpoint http://127.0.0.1:8101/api/v1/regenold/eu-ai-act/ask
done
```

### 4.5 Experiment C — the bigger loss channel, which nobody has scoped

6 of 9 non-gated Antifragile rows ran Opus 4.8 and discarded it. That is a larger effect than either gate on the population that reaches Stage-2 at all, and it is a **pure instrumentation problem today** — persist `notes`, re-run the 20 rows once, and the rejection channel becomes readable with no A/B at all. Do this **first**; it is one run and it may reframe both gate experiments.

---

## What I could NOT determine

- **Which rejection guard** discarded Stage-2 on q03/q04/q14/q15/q16/q19. Raw trace notes are not persisted.
- **Whether the alleged R275 Opus paraphrase ever happened.** No artefact exists anywhere I searched (`docs/ROUNDS.md`, `docs/reviews/`, `.planning/`, `.evalout/`). What I *can* state is that the expert-failure attribution used to justify it is contradicted by the docx.
- **The current production provider / wrapper state at the moment any future arm runs.** I made no LLM calls and no live probes per the constraints; CLAUDE.md's own guidance is that this is a service variable that must be re-measured per session, and the R338 doc plus the operator brief already disagree with each other about it.
- **Whether `WRAPPER_FORWARD_SYSTEM_PROMPT=1` helps or hurts on this repo's rubric.** R282's −0.267 kw_recall was measured on the **sibling** repo (`DEPLOY_SYSTEM_PROMPT_FIX.md` points at `../regenold-eu-ai-act-rag`); R338's −0.0669 is uncontrolled. Neither settles it, and both gate experiments above inherit that confound unless the wrapper state is pinned and recorded.

==========================================================================================
## agent result #4  (len 15044)
==========================================================================================

## R338 follow-up — over-citation handle (A) and the q03/q04/q14 regression (B)

Everything below was produced by execution. Deployed `/healthz.commit` = `1d55a94ac238` = local `HEAD` (probed this session). Offline env: `P2P_GRAPH_RAG_PROVIDER=cli REGENOLD_EXTERNAL_EMBEDDINGS=0 REGENOLD_GRAPH_BACKEND=embedded`, `py -3.12`, FastAPI `TestClient`.

---

# PART B FIRST — it overturns the R338 report's own diagnosis

## B1. The regression is NOT on the deterministic path. Stage-2 stopped landing.

The R338 report (`docs/R338-live-opus48-antifragile-graphrag.md:94,107,189`) says the −5 mistake regression is "on the deterministic (non-Stage-2) path" and "an answer-*assembly* change". **Both artefacts refute that.** Paired `reasoning` from the two runs:

```
id    R318 s2 R318 model          lat  | R338 s2 R338 model          lat
q03   True    claude-opus-5     22597  | False   claude-opus-4-8   10903
q04   True    claude-opus-5     16946  | False   claude-opus-4-8    7307
q14   True    claude-opus-5     21603  | False   claude-opus-4-8    3802
q15   True    claude-opus-5     24578  | False   claude-opus-4-8     941
q16   True    claude-opus-5     40357  | False   claude-opus-4-8    3688
q19   True    claude-opus-5     11014  | False   claude-opus-4-8     926
stage2_polish TRUE: R318 9/20   R338 3/20
```

**In R318 all three regressed rows ran Stage-2 and shipped the Opus-5 polish.** In R338 they attempted it and discarded it. Routing is byte-identical between runs — the same 9 rows carry `answer_route=synthesis:*` and the same 11 carry `None`:

```
q01 R318 route=synthesis:synthesis_default | R338 route=synthesis:synthesis_default
q03 R318 route=synthesis:synthesis_default | R338 route=synthesis:synthesis_default
q14 R318 route=synthesis:complex_question  | R338 route=synthesis:complex_question
... (all 20 identical)
```

`answer_route=` is recorded at `app/engines/_graph_rag_impl.py:8265`, which is **after** all three Stage-2 skip gates (`:8205` simple-skip, `:8230` curated, `:8249` definitional). So none of the skips fired on q03/q04/q14 — the report's §1 explanation ("two gates bypass Stage-2") does not apply to the regressed rows. The polish was generated and then thrown away at one of `_graph_rag_impl.py:8319 / :8372 / :8398 / :8434`.

## B2. What "disappeared" was never in the code — so `git log -S` finds nothing

R338's shipped answers ARE the current deterministic assembly, verified byte-for-byte offline:

```
q03  CLI answer == R338 predicted_answer : True
q14  CLI answer == R338 predicted_answer : True
q04  near-identical (same refs; live run prepends one Art. 25 value-chain sentence)
```

q03's entire R338 answer is `get_provision_text("Article 6.2")` — 140 chars, the raw sub-provision:
> "In addition to the high-risk AI systems referred to in paragraph 1, AI systems referred to in Annex III shall be considered to be high-risk."

The R318 content that "disappeared" (the Art. 6(1) third-party-conformity route, the Art. 6(3) carve-outs, the Annex I product list, the Art. 31/Annex VII notified-body detail) is **Opus-5 Stage-2 prose**. Grep proves it is not authored anywhere in the tree:

```
### by either of two routes                  -> 0 hits in app/
### Two routes make an AI system high-risk   -> 0 hits in app/
### single assessment and a single CE marking-> 0 hits in app/
### is not a separate AI Act procedure       -> 0 hits in app/
```

**There is no removal commit. `git log -S` on the missing phrases is the wrong instrument for this defect** — nothing was removed from source.

## B3. Named cause (high confidence, one confound): `WRAPPER_FORWARD_SYSTEM_PROMPT=1`

R338's §0 config flip is the change R282 already measured and **rejected**. `.planning/R282-CHECKPOINT.md:58-100`, two wrapper instances, `easyhard_ab` n=40/arm, 0 errors:

| axis | OFF (=R318) | ON (=R338) | R282 Δ | **R338 Δ (R318→R338)** |
| --- | --- | --- | --- | --- |
| kw_recall | 0.8750 | 0.6083 | −0.267 | **−0.0669** |
| ref_loose | 0.8542 | 0.7500 | −0.104 | **−0.0125** |
| ref_strict | 0.6455 | 0.4901 | −0.155 | **−0.0368** |
| ref_conc | 0.5391 | 0.3876 | −0.152 | **−0.1023** |
| latency p50 | 22.1 s | 5.4 s | −16.7 s | see below |
| pred:gold | 1.83 | 2.50 | +0.67 | **1.11 → 1.20** |

All six move in the same direction, attenuated exactly as expected (only 9 of 20 rows attempt Stage-2). The latency and length fingerprints match to the second:

```
synthesis-routed rows (identical set both runs): q01 q03 q04 q13 q14 q15 q16 q18 q19
R318 latency: median 21603 ms   R338 latency: median 3802 ms
answer chars: R318 median 1853  R338 median 765
```

R282's recorded root cause: *"the 12.8K-token ANSWER_GENERATE_SYSTEM OVERWHELMS the specific question — answers drift off-topic, get terser (median 830c vs 1107c, 31/40 rows <8s), and over-cite generically."* `docs/ROUNDS.md:10809` states it as a standing prohibition: **"Do NOT respond to this by forwarding the system prompt to the model — R282 already measured that path as rubric-negative."**

**⚠ CLAUDE.md is stale here and it is load-bearing.** `CLAUDE.md:601-608` presents the flag as merely *"answer-CHANGING and owes its own A/B"*. `grep -n R282 CLAUDE.md` returns **0 hits**. The A/B exists, it is in the repo, and it rejected the flip. R338 turned it on anyway.

**The confound I cannot remove:** R318 ran `claude-opus-5`, R338 ran `claude-opus-4-8`. Two uncontrolled variables. I could not separate them — I am barred from calling the wrapper this session.

**Decisive next probe (cheap, ~20 rows):** re-run `evals.regenold.antifragile_live` with `WRAPPER_FORWARD_SYSTEM_PROMPT=0` on the wrapper and `claude-opus-4-8` held fixed. If `stage2_polish` returns to 9/20 and q03/q04/q14 recover, the flip is the cause and the model is not.

## B4. Instrument gap that hid this — fix before the next run

`evals/regenold/antifragile_live.py:135-160` `_parse_reasoning` keeps only `stage2_polish`, `retrieval_path`, `engine_confidence`, `cache_hit`, plus two regex-scraped notes. **It discards the raw `notes` list.** All eight Stage-2 exit points in `_two_stage_generate` collapse into one boolean, so `stage2_failed_both_providers_deterministic_ship` (`:8315`), `stage2_drift_guard_dropped_polish` (`:8368`), `stage2_contradiction_guard_dropped_polish` (`:8393`) and `stage2_fidelity=fallback*` (`:8427`) are indistinguishable in the artefact. **This is why the round could not name the discard site, and why the report reached for "deterministic path" instead.** Persist `notes` verbatim.

Latency splits the six lost rows into two classes worth separating: q15 941 ms / q19 926 ms are too fast for an Opus round-trip (likely `enhanced is None` at `:8301`), while q03 10.9 s / q04 7.3 s burned a full call and rejected it. I could not confirm which gate — honest gap.

---

# PART A — over-citation across all 40 GraphRAG rows

## A1. Distribution

`|pred| − |gold|`, head-normalised, from `evals/bench/results/graphrag-bench-r338-opus48-graphrag.json`:

```
delta:  0 ×14 | +2 ×12 | +1 ×3 | +3 ×3 | +5 ×2 | +4 ×1 | −1 ×3 | −2 ×2
mean delta +1.075          26/40 rows over-cite or match; 5 under-cite

wrong-rate by rank position          mean delta by band
  rank 1:  8/40 = 0.200              latency <1500ms (no LLM), n=24: +0.88
  rank 2: 18/30 = 0.600              latency >=1500ms (LLM ran), n=16: +1.38
  rank 3: 15/25 = 0.600
  rank 4: 11/14 = 0.786
  rank 5+: 9/9  = 1.000
```

Reproduces CLAUDE.md's tail-padding shape (rank-1 80% right, everything past rank 3 is mostly wrong). Over-citation is **not** a Stage-2 artefact: it is present at +0.88 on rows that never called an LLM.

**Most-added non-gold refs:** `Article 6` ×6, `Article 9` ×5, `Article 50` ×4, `Annex I` ×4, `Annex III` ×4, `Article 10/13/14` ×3 each.

## A2. gt_06 traced — the three refs are HARD-CODED, and empty gold is unreachable

Instrumented the whole route (`_seed_classification_obligations` → `_surface_anchor_citations` → `_collapse_parent_refs` → Component D). Offline output is byte-identical to live:

```
--- _seed_classification_obligations   IN: minimal_risk   OUT: ['Art. 5', 'Art. 6', 'Art. 50']
--- _surface_anchor_citations          IN: ['Article 5','Article 6','Article 50'] OUT: (same)
--- _collapse_parent_refs              IN: (same) OUT: (same)
FINAL REFS: ['Article 5', 'Article 6', 'Article 50']
reasoning notes: ["curated_ref_protect: prune skipped"]   stage2_polish: false
```

`_add_prose_named_refs` and Component D were **never called**. The refs enter at a single site:

> **`app/engines/_graph_rag_impl.py:4755-4771`** — the `_detect_minimal_risk_inquiry` curated intercept, whose literal `"refs": ["Art. 5", "Art. 6", "Art. 50"]` is seeded by `_seed_classification_obligations` (`:2964`), which **replaces** `context.obligations` and clears `context.article_info`. The code comment states the intent: *"seed the three contrast refs so the wire ships exactly those."*

`gt_07` (guiding_principles, also empty gold, +2) is the same shape at `:4744` with `["Art. 1", "Art. 4"]`.

**Second component, and it is the blocker:** an empty reference list is structurally impossible on this route. Counterfactual — stripping the curated refs at the seed:

```
Q: What are AI systems with minimal risks?
  _surface_anchor_citations: IN [] -> OUT []
  FINAL REFS: ['Article 1', 'Article 2', 'Article 3.1']
  ANSWER:  "Article 1 lays down harmonised rules for placing on the market..."   <-- prose replaced too
```

> **`app/routes/regenold.py:8645`** — the R47-E zero-retrieval fallback fires on `if not references:` and substitutes 3-5 canonical citations *and* its own prose. So `gt_06` cannot score its empty gold without changing this gate too.

**Component to fix: the curated intercept's `refs` list at `_graph_rag_impl.py:4770` + an explicit "curated verdict may ship zero references" escape in `regenold.py:8645`.** Neither is a trimmer, a blocklist, a clamp, a prose-prune, or a re-ranker.

## A3. The bigger handle: `_apply_ontology_hops` — it is the single largest over-citation source

Traced `ng_03` and `ng_10` the same way. `_apply_ontology_hops` (`app/routes/regenold.py:8543`, defined `:372`) is the only stage that adds references on either row.

**ng_03** — gold `[Art 26, Art 27]`:
```
** _apply_ontology_hops
   IN : ['Article 26','Article 27','Article 25','Annex III']
   OUT: ['Article 26','Article 27','Article 25','Annex III','Article 13','Article 14','Article 9','Article 6']
FINAL: [...,'Article 13','Article 14','Article 9']       <- all 3 injections are wrong
```

**ng_10** — gold `[Art 10, Art 15]`. This one is a mechanism bug, not a tuning problem:
```
** _apply_ontology_hops
   IN : [Art 10,55,9,52,13,93,27,57,53,56,90,26,50,94]   (14)
   OUT: [... , 'Article 15','Article 11','Article 14','Article 6']   (18)
FINAL: ['Article 10','Article 55','Article 9','Article 52','Article 13','Article 93','Article 27']
```
The hop injected **Article 15 — the missing gold** — and it never shipped. Cause:
* `regenold.py:442` — `return list(candidates) + injected` appends injections at the **tail**.
* `regenold.py:8564` — the budget bump raises `_effective_max_refs` by `_ontology_hop_injected` (capped 7).
* `regenold.py:8584` — `references = candidates[:_effective_max_refs]` slices from the **head**.
* `regenold.py:8595` — the R115 rescue only recovers refs containing `"."` (sub-points), so head-level injections are never rescued.

**Net on ng_10: the hop spends 4 extra reference slots, delivers 0 of its own targets, and the 4 slots are filled by BM25 tail junk — Article 52 (GPAI systemic-risk notification), Article 93 (Commission request powers) and Article 27 (FRIA), all verified irrelevant against the pin via `get_provision_text`.**

### Measured, offline, all 40 rows, `REGENOLD_ONTOLOGY_HOP` ON vs OFF

Fire check passed — 11/40 rows diverge. `provider=cli` reproduces the live `pred_refs` on **32/40** rows (the 8 mismatches are exactly the Stage-2 rows: med_1..4, med_7, gt_04, ng_05, med_01), so this is an offline *simulation* of the deterministic half, not the live system.

```
rows changed: 11/40   wrong refs removed: 23   GOLD DROPPED: 5
axis (head-grain)      ref_loose / recall / precision
  HOP ON  :            1.0000 / 0.8750 / 0.5699
  HOP OFF :            1.0000 / 0.8368 / 0.6200      (+0.050 precision, −0.038 recall)
```

Gold dropped: `gt_13` ×3 (Art 6, Art 5, Annex I), `med_9` ×1 (Annex I), `ng_04` ×1 (Art 13).

**Hard rule #8 verdict: a blanket `REGENOLD_ONTOLOGY_HOP=0` is a REJECTION** — 5 gold coordinates lost. Do not flip it. But the hop is where 23 of the wrong refs live, and **27 of the 61 non-gold reference instances in the live artefact (44%) are members of `_ONTOLOGY_HOP_MAP`'s 13-ref target set** — a 4.4× enrichment over that set's 10% share of the 126-provision surface.

### The three sub-fixes that are not on the "do not re-propose" list

1. **Insert injections next to their source candidate, not at the tail** (`regenold.py:442`), so the hop's own targets survive the `[:budget]` slice instead of donating their slots to BM25 tail junk. On ng_10 alone this converts 4 wrong refs into 1 gold.
2. **Drop the unconditional budget bump** (`regenold.py:8564`) once (1) lands — the bump exists only to make room for injections that currently never survive.
3. **Narrow the `is_medical` trigger** (`regenold.py:388,415`): any question containing `medical|doctor|patient|clinical|surgery` hops unconditionally, with no requirement that the question ask about requirements or classification. That is why every medtech row over-cites (med_3 +2, med_5 +3, med_8 +3, med_9 +2).

Each is A/B-able offline against these 40 rows with `gold_dropped` readable, then gateable through `evals.harness.dynamic_ab`.

---

## What I could NOT determine

* **Which of the four discard gates rejected the Stage-2 polish on q03/q04/q16.** The artefact does not carry `notes` (`antifragile_live.py:135`) and I am barred from calling the wrapper.
* **Whether `WRAPPER_FORWARD_SYSTEM_PROMPT=1` or the `opus-5 → opus-4-8` model change caused the lost landings.** Both changed between R318 and R338. The R282 fingerprint match (latency, length, all four axes, pred:gold) is strong circumstantial evidence for the flag, not proof.
* **Whether the deterministic assembly for q03/q04 itself changed between R318 and R338.** R318 never shipped it, so there is no R318 baseline to diff against, and I could not `git checkout` to regenerate one.
* **The live Stage-2 rate on the GraphRAG benchmark.** `reasoning` is the empty string on all 40 rows in that artefact — the runner never requested `include_reasoning`. My latency-band split (<1500 ms = no LLM) is a proxy, not a measurement.
* **Offline runs are not perfectly reproducible.** Two identical `HOP=1` passes disagreed on `med_5` (`Article 50` vs `Article 50.1`). Treat single-row offline deltas as noisy; the 11-row aggregate reproduced.

Scratch files (safe to delete): `…/scratchpad/{overcite,trace_gt06,stage_trace,stage_trace2,counterfactual,hop_ab,hop_report}.py`, `hop_{0,1}.json`. No repo file was modified.

==========================================================================================
## agent result #5  (len 18335)
==========================================================================================

# ADVERSARIAL CHALLENGE — judge-plumbing report, at `1d55a94` (deployed)

All evidence below was produced this session by executing code under `OPENAI_API_BASE=http://127.0.0.1:1/v1 P2P_GRAPH_RAG_PROVIDER=cli REGENOLD_EXTERNAL_EMBEDDINGS=0`, `py -3.12`, `PYTHONPATH` = repo root. No wrapper or tunnel LLM calls. One read-only Railway probe. Scratch scripts under `.../scratchpad/chal_0*.py`.

---

## VERDICT SUMMARY

| | count |
|---|---|
| CONFIRMED (reproduced exactly) | 12 |
| CORRECTED (true core, wrong mechanism/number/scope) | 5 |
| UNSUPPORTED (drop) | 2 |
| NEW defects the report missed | 4 |

The report's four "known defects" all survive. Its **new defect is misdiagnosed**, its **prompt-size number is 2.2× low**, its **medtech fix is structurally broken**, and its **provider rationale rests on two unverified claims, one of which is false**.

---

## 1. CONFIRMED — reproduced with my own execution

**C1 — Silent zero on the live artifact.** `evals/judge/grounded.py:455-467`; key tuple at `:461`; dict fall-through at `:467`.
```
live top keys: ['antifragile_rows', 'antifragile_summary', 'endpoint', 'label', 'medtech_rows', 'medtech_summary']
_load_rows(live) -> 0
graphrag top keys: [... 'ground_truth', 'no_ground_truth' ...]   ground_truth.rows: 40, no_ground_truth.rows: 0
_load_rows(graphrag) -> 40
_aggregate([]) -> {"answer_correctness": {"n": 0, "pass": 0, ..., "pass_rate": 0.0, ...}}   # no raise
```

**C2 — T2 medtech empty questions.** `grounded.py:126` reads `question`/`live_question`; medtech rows key it `final_question`.
```
RAW medtech _norm q_len all rows: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

**C3 — T3 `answer_preview` is a 400-char prefix**, third in the `grounded.py:127-128` chain.
```
predicted_answer len: 5498  answer_preview len: 400  preview is prefix: True
distinct answer_preview lengths across 20 rows: [140, 321, 354, 387, 400]
```

**C4 — Defect (a), `legal_v2._prepare` circular grounding + inert strict flag.** `grep -c GROUNDED_JUDGE_STRICT_GROUNDING evals/judge/legal_v2.py` → **0**. Executed on a gold-free row:
```
flag=0  strict_required=False  grounded_src='predicted_refs_fallback_circular'  block_len=11275  legal_v2_union_map_keys=['Article 5']
flag=1  strict_required=True   grounded_src='none'                              block_len=0      legal_v2_union_map_keys=['Article 5']
```
The flag flips `grounded.py` and does nothing to `legal_v2`. Guard is at `legal_v2.py:1010-1015` (report said 1010-1015 — correct).

**C5 — Defect (a)'s scope limit is right.** All 20 antifragile rows take `gold_refs`, not the circular branch:
```
grounded src counts: {'gold_refs': 20} | legal_v2 rows taking the CIRCULAR branch: 0
```

**C6 — Defect (b), head-lax gate at `legal_v2.py:658-663`, and it inverts.**
```
Article 3.999            exists=True   text=None
Article 3.14a            exists=True   text=None
Annex III.4.employment   exists=True   text=None
Article 999              exists=False  text=None
```
Executed with pred=`['Article 3.14a','Article 9']`, judge classifies 3.14a WRONG with a genuine 12-word Article 9 quote:
```
wrong_refs: [] | supporting_refs: ['Article 3.14a'] | legal_soundness_precision: 1.0 | verdict: pass
```

**C7 — Defect (b) is latent, not active, on this data.** My independent scan agrees with the report exactly:
```
antifragile pred_refs n=61  unresolvable=0
medtech     pred_refs n=47  unresolvable=0
graphrag    pred_refs n=123 unresolvable=0     TOTAL 231, unresolvable 0
gold_refs:  47 / 29 / 75    unresolvable 0
```

**C8 — Defect (c), conciseness prompt ungated.** `render_answer_conciseness` at `legal_v2.py:488`; **0** `getenv` calls in lines 488-514; `REGENOLD_JUDGE_CONCISENESS_LENIENCY` appears at exactly **one** line, `:821`, in post-processing.

**C9 — Defect (d), unified token budget.**
```
env=None    -> 1600
env='3000'  -> 3000
env='50'    -> 200      env='99999' -> 8000     (clamped [200,8000])
is_retryable_judge_error: unbalanced_json=False  no_json=False  empty_response=False
                          api_status_500=True    api_status_429=True   timeout=True
```

**C10 — §4 gold answers exist and join.**
```
live ids n=20 | ANTIFRAGILE_GT dict len 20 | join 20/20
gold_answer chars: min 320 median 449 max 692 zero: 0
GT fields: ['expected_keywords','gold_answer','gold_refs','lexy_refs','mistakes','question','verdict']
```

**C11 — `gold_subpoint_refs` is not a superset, and drops heads on exactly q13/q15.**
```
rows where gold_refs != gold_subpoint_refs: 13/20
rows where subpoint list DROPS a gold head: 2
   q13 gold ['Annex I','Article 5','Article 50','Article 6'] sub ['Annex I','Article 6.1'] lost ['Article 50','Article 5']
   q15 gold ['Annex III','Article 5','Article 6']            sub ['Article 5.1.g','Article 6'] lost ['Annex III']
union size per row max: 6 | rows over _MAX_GOLD_REFS=6: 0
```

**C12 — `gt_06`/`gt_07` gold is genuinely empty.**
```
gt_06 expected_refs=[] pred_refs=['Article 5','Article 6','Article 50'] category=minimal_risk
gt_07 expected_refs=[] pred_refs=['Article 1','Article 4']              category=guiding_principles
```
The R338 report's §4 legal claims also re-verify against the pin: `Article 27` = 2,837 chars, `"serious incident" in text = False`, FRIA text present; `Article 26.5` = 1,359 chars, contains the deployer serious-incident duty; `Article 51` classification / `Article 52` notification both confirmed.

---

## 2. CORRECTED

### X1 — The "NEW DEFECT" is misdiagnosed. `Article 13` **IS** shown to the judge.

Report: *"NEVER SHOWN TO JUDGE: ['Article 13'] → falls to the `else` at `:676-680` → supporting."*

`render_reference_correctness` prints the **full, uncapped** ref list at `legal_v2.py:431` (`PREDICTED CITATIONS: {r['pred_refs']}`). Only the *verbatim-text block* is capped. Measured on q14:
```
beyond cap: ['Article 13']
  'Article 13' occurs in rendered prompt? True  count=2
PREDICTED CITATIONS: ['Article 6','Article 43','Annex I','Article 5','Article 9','Article 10','Article 11','Article 12','Article 13']
```
**The accurate defect is worse than the report's version.** The ref is named, the prompt says *"Classify EVERY predicted citation"*, so the judge *will* rule on it — but `_quote_substantiated(quote, pred_map.get(ref,""))` at `:667` runs against an **empty string**, so a correctly-substantiated WRONG is force-downgraded. Executed with a real 14-word verbatim Article 13 quote:
```
B) judge says WRONG w/ real Art13 quote -> wrong_refs: []  | supporting has 13: True
   verdict: pass   legal_soundness_precision: 1.0   unsubstantiated: ['Article 13']
```
A ref past the 8th is **unfalsifiable**, not unseen. The report's `else`-branch path is only the sub-case where the judge stays silent.

**The report also missed that `citation_faithfulness` has the identical cap** (`legal_v2.py:540`):
```
C) MISMATCHED on Article 13 (beyond cap) -> mismatched: []  | faithful count: 9
```
So the 9th ref cannot be MISMATCHED either. That is two axes, not one. Affected rows confirmed: **q14 only** (9 refs); 0 rows in medtech and graphrag.

### X2 — Prompt-size figure is 2.2× low. "42,340 chars max" is one axis on one sidecar.

Report: *"My rendered prompts max at 42,340 chars (~10.6K tokens) input."* That number is exactly the `answer_correctness` max on its own antifragile sidecar. Full measurement across every row × every axis:
```
SIDECAR r338-graphrag.judge   reference_correctness  max 92057 chars (~23014 tok)  row=gt_01
SIDECAR r338-antifragile.judge reference_correctness max 84280 chars (~21070 tok)  row=q01
SIDECAR r338-medtech.judge    reference_correctness  max 63477 chars (~15869 tok)  row=mt_med_03
SIDECAR r338-antifragile.judge answer_correctness    max 42340 chars (~10585 tok)  row=q01   <- the quoted number
RAW graphrag                  reference_correctness  max 55212 chars (~13803 tok)  row=gt_01
```
**True max on its own recommended sidecars: 92,057 chars (~23K tokens)** — and the report's own converter is what inflated it (see X3).

### X3 — The converter nearly doubles the reference_correctness prompt by duplicating gold text.

`legal_v2.py:531-533` **appends** the supplied `gold_context` to a `gold_map` that `:530` already filled by resolving `gold_refs`. Measured on q01:
```
gold_map keys: ['Article 5','Article 6','Annex I','Annex III','Article 50','Article 51','independent_gold_context']
gold provisions whose text ALSO appears inside independent_gold_context: 6/6
supplied ctx chars: 34101 | sum of separate gold texts: 33907
q01 ref prompt chars: 84280   (raw, unconverted: 51794)
```
Every gold provision is in the prompt **twice**. The report's self-verification checked the grounding *source*, not the prompt it produces — it verified the label and not the payload.

### X4 — Field name is wrong for the recommended run. `legal_v2` does not emit `pass_rate`.

Report: *"`pass_rate` does divide by total rows (`grounded.py:526`) ... `_fmt` prints both (`grounded.py:663-664`)"* — those are `grounded.py` cites for a run the report recommends on **`legal_v2`**. Executed on `legal_v2._aggregate` with 6 pass / 2 fail / 2 `unbalanced_json`:
```
legal_v2 keys: ['error','fail','n','pass','pass_rate_over_non_error','pass_rate_raw']
pass_rate_raw= 0.6   over_non_error= 0.75
does legal_v2 emit a bare 'pass_rate' key? False
```
The advice is right; the name and file:line are from the wrong module. Read **`pass_rate_raw`** (`legal_v2.py:1087`, printed at `:1302`).

### X5 — T1 is over-claimed.

*"Writing `independent_gold_context` is ignored and the row falls through to `predicted_refs_fallback_circular`."* Only when `gold_refs` is **also** empty:
```
key=independent_gold_context  gold_refs=[]            -> ctx_len=  0  src=predicted_refs_fallback_circular
key=independent_gold_context  gold_refs=['Article 5'] -> ctx_len=  0  src=gold_refs                 <- NOT circular
key=gold_context              gold_refs=[]            -> ctx_len= 51  src=independent_gold_context
key=gold_context              gold_refs=['Article 5'] -> ctx_len= 51  src=independent_gold_context
```
The key really is ignored (real trap, `grounded.py:110-113`). The *consequence* is dataset-dependent, and on every R338 antifragile/medtech row it would have been `gold_refs`, not circular.

---

## 3. UNSUPPORTED — drop these

### U1 — "`ANTHROPIC_API_KEY` is UNSET, so `--provider anthropic` is unavailable." **False.**

`_call_judge_anthropic` (`evals/judge/runner.py:483-486`) reads **`P2P_GRAPH_RAG_API_KEY` first**, then `ANTHROPIC_API_KEY`. The repo `.env` has `P2P_GRAPH_RAG_API_KEY` set (len 108), and `legal_v2.main()` calls `load_dotenv()` at `legal_v2.py:1339-1341`. So `--provider anthropic` **is** available. (Whether you *want* it is a separate question — CLAUDE.md flags that key as per-token-billed. But the stated reason for excluding it is wrong.)

### U2 — "concurrency 2 — the default; CLAUDE.md records the tunnel failing in bursts under load."

Taken from CLAUDE.md and from the `--max-retries` help text (`legal_v2.py:1364-1370`, the *"measured ~60% of calls"* string). The report itself admits it did not re-measure. It is worse than stale — see N3: the wrapper's configuration changed on 2026-08-15, so that figure was measured on a materially different transport.

---

## 4. NEW — defects the report missed

### N1 — The judge's own system prompt is now delivered. Comparability to the July-7 baseline is broken.

Report §5: *"model `claude-sonnet-5` — the model the July-7 baseline was graded with, so numbers stay comparable."*

Every judge transport passes `system=_JUDGE_SYSTEM` (`runner.py:210, 292, 385, 444`), and `_JUDGE_SYSTEM` (`runner.py:98-102`) is precisely the JSON-discipline instruction:
> "Respond with ONE JSON object only — no preamble, no markdown fences, no explanation outside the JSON."

Measured this session:
```
D:/Claude Projects/claude-code-openai-wrapper/.env:101:WRAPPER_FORWARD_SYSTEM_PROMPT=1
```
Every previously-recorded wrapper-graded number was produced with that instruction **dropped**. It is now delivered. That plausibly changes the `no_json` / `unbalanced_json` rate — the exact failure the report's max-tokens analysis is built around — and it changes the judge's behaviour under the *same* `--model claude-sonnet-5 --provider wrapper` invocation. The report's comparability argument is a model-identity argument that ignores a same-week transport change. **Any new wrapper-judged number is not directly comparable to a pre-2026-08-15 one, regardless of model.**

### N2 — `P2P_GRAPH_RAG_PROVIDER=bedrock` silently overrides `--provider wrapper`.

`runner.py:783`: `if provider == "bedrock" or os.getenv("P2P_GRAPH_RAG_PROVIDER","").lower() == "bedrock"`. Executed:
```
P2P_GRAPH_RAG_PROVIDER=''               --provider=wrapper -> ['_call_judge_sonnet']
P2P_GRAPH_RAG_PROVIDER='openai_wrapper' --provider=wrapper -> ['_call_judge_sonnet']
P2P_GRAPH_RAG_PROVIDER='bedrock'        --provider=wrapper -> ['_call_judge_bedrock']
```
The report spends a paragraph warning against `--provider bedrock` (on a CLAUDE.md-sourced 403 claim) while an env var can route there behind the flag's back. Safe today — repo `.env` has `P2P_GRAPH_RAG_PROVIDER=openai_wrapper` — but unverified by the report, and this repo's orchestration exports that variable routinely.

### N3 — The recommended transport is the one production is currently failing on.

Read-only probe, this session:
```
GET /healthz      -> {"status":"ok","version":"1.2.3","commit":"1d55a94ac238", ...}
GET /healthz/llm  -> {"provider":"openai_wrapper","llm_ok":true,"detail":"ok",
                      "cf_access":{"client_id_set":true,"client_secret_set":true,"headers_attached":true},
                      "elapsed_ms":5076,"model":"claude-sonnet-5",
                      "prompt_tokens":2,"completion_tokens":0}
```
Three things follow. (a) **The deployed commit is `1d55a94`, not `f7f85ad`** — the brief is already one commit stale; a docs commit auto-deployed. (b) **The deployed provider is `openai_wrapper`, re-measured** — CLAUDE.md's Bedrock reading is stale, as the operator suspected. (c) `llm_ok:true` with **`completion_tokens: 0`** is exactly CLAUDE.md's *"`/healthz/llm` lies"* gotcha firing, and it is consistent with the operator's measured `stage2_failed_both_providers_deterministic_ship`. The report recommends `--provider wrapper` over `wrapper.antifragile-ai.net` (repo `.env` `OPENAI_API_BASE = https://wrapper.antifragile-ai.net/v1`) — the same tunnel→Claude-Max path production Stage-2 is currently dying on — at `--samples 3` × 4 axes × 70 rows = **840 calls**, and never flags that risk.

### N4 — STRUCTURAL: the medtech fix populates the question with an unresolvable anaphor. The judge cannot observe what it is asked to score.

The converter sets `question` = `final_question` (turn 3 only) and reduces the turn history to the **integer** `_turns: 3`:
```
sidecar mt_med_01 _turns value: 3
sidecar mt_med_01 question: 'Given that integrated procedure, which specific human-oversight obligations
                             must we meet as the provider of this system?'
```
Turns 1-2, which define "that integrated procedure" and "this system", are dropped:
```
turn 1: We are developing an AI model that analyses MRI scans and flags potential tumour regions...
turn 2: It is currently being CE-marked under MDR as a Class IIb medical device. How does that interact...
turn 3: Given that integrated procedure, which specific human-oversight obligations must we meet...
```
Measured across the suite:
```
medtech rows whose final_question contains an anaphor (that/this/these/it): 8 / 10
```
Samples: `mt_med_02` *"if we deploy that extended version"*; `mt_med_04` *"Given the systemic-risk designation"*; `mt_med_07` *"The second system also infers…"*. The referent is never in the prompt.

This is the repo's signature failure in its exact canonical shape. T2 was diagnosed as "the question arrives empty"; the fix made it non-empty and **left it unanswerable**. `answer_correctness` and `answer_conciseness` on all 10 medtech rows would be scored against an underspecified question, and the resulting numbers would look normal. **The converter must carry the full turn transcript into `question`, or medtech answer-axis numbers must not be reported.**

---

## 5. WHAT I COULD NOT DETERMINE

* **Bedrock entitlement, re-measured.** I attempted a 5-token invoke against `eu.anthropic.claude-sonnet-5` and `…-sonnet-4-6`; the sandbox classifier **blocked the command**. So CLAUDE.md's "sonnet-5 is 403, degrades to sonnet-4-6" remains a 2026-08-14 record I could not re-verify. The report's `--provider bedrock` warning is therefore neither confirmed nor refuted — treat it as unverified, not as fact.
* **Whether N1 actually changes the judge's output.** I proved the system prompt is now forwarded (`.env:101`) and that the judge sends one (`runner.py:210`). I did not make a judge call, so the *magnitude* of the effect on `no_json` / verdicts is unmeasured.
* **Whether `REGENOLD_JUDGE_MAX_TOKENS=2400` suffices.** Same gap the report admits — but the input side is now known to be ~23K tokens, not ~10.6K (X2), so the margin is thinner than it argued.
* **Whether production's Stage-2 wrapper failures share a root cause with a judge run over the same tunnel.** `/healthz/llm` is suggestive (`completion_tokens: 0`), not conclusive. I did not POST `/ask`, to avoid a wrapper-bound call colliding with the orchestrator's serialized live eval.
* **The report's credential-exposure warning is real** — `AWS_BEARER_TOKEN_BEDROCK` exists in `.env` (len 132). I masked every value; I did not reproduce it. The rotation advice stands.

---

## 6. NET RECOMMENDATION CHANGES

1. **Do not run medtech answer-axis judging** until the converter carries all 3 turns into `question` (N4). Reference axes are unaffected.
2. **Raise `_MAX_PRED_REFS` to ≥12 on BOTH `legal_v2.py:529` and `:540`** — the report named only the first, and only one of the two affected axes (X1).
3. **Strip `gold_context` when `gold_refs` already resolve**, or accept a 2× prompt bill and ~23K-token inputs (X2/X3).
4. **Assert `P2P_GRAPH_RAG_PROVIDER` before the run** — `--provider wrapper` is not authoritative (N2).
5. **Stop claiming July-7 comparability** for any wrapper-judged number produced after 2026-08-15 (N1).
6. Read **`pass_rate_raw`**, not `pass_rate` (X4).

==========================================================================================
## agent result #6  (len 23164)
==========================================================================================

CLAUDE.md STALENESS AUDIT — measured 2026-08-15 against deployed `f7f85ad6f6de` and working tree `1d55a94`

## 0. THE FINDING THAT SHOULD STOP THE ROUND

**The `WRAPPER_FORWARD_SYSTEM_PROMPT=1` flip the operator just made was already A/B'd by this repo, and it lost, decisively.** CLAUDE.md's gotcha says the flip "owes its own A/B". It does not — it owes a *re-run*, because the A/B exists and CLAUDE.md omits it entirely.

`.planning/R282-CHECKPOINT.md:60-95` (verbatim table, two wrapper instances, prod:8000 system DROPPED vs patched:8001 with `WRAPPER_FORWARD_SYSTEM_PROMPT` FORWARDED, `easyhard_ab` n=40/arm, 0 errors):

| axis | OFF (=prod) | ON (=the flip) | delta |
| --- | --- | --- | --- |
| kw_recall | 0.8750 | 0.6083 | **−0.267** |
| ref_loose | 0.8542 | 0.7500 | −0.104 |
| ref_strict (F1) | 0.6455 | 0.4901 | −0.155 |
| ref_conc | 0.5391 | 0.3876 | −0.152 |
| pred:gold | 1.83 | 2.50 | +0.67 |

Pairwise judge, position-swapped: **baseline/OFF wins all 4 axes 8/8 rows, sign-test p≈0.008**. File's own verdict, quoted: *"Decision: keep OFF — do NOT activate."* Root cause recorded there: `ANSWER_GENERATE_SYSTEM` **overwhelms** the question — measured just now at **51,516 chars** (`py -3.12 -c "len(graph_rag_prompts.ANSWER_GENERATE_SYSTEM)"`).

Corroborating, not proving: `docs/R338-live-opus48-antifragile-graphrag.md:71-84` measures, on the first suite run with the flip live, `keyword_recall −0.0669`, `ans_strict −0.0902`, `ref_conciseness −0.1023`, and a −5 mistake regression that survives re-scoring on one ruler. R338 localises 3 of those rows to the deterministic path, so this is a **hypothesis with the right sign**, not an attribution. It is exactly the direction R282 predicted.

The two code comments telling the next reader not to do this are also still in the tree, still citing a number CLAUDE.md never mentions: `app/data/graph_rag_prompts.py:843`, `:964`, and `app/engines/_graph_rag_impl.py:7787-7792`.

## 1. WHAT IS NOW FALSE — correction table

| # | CLAUDE.md claim (line) | Measured reality (how) | Suggested replacement |
| --- | --- | --- | --- |
| **F1** | `:129` "`KB_VERSION = 2024.1689.v18`" | **`2024.1689.v21`**. `app/data/kb.py:33`; changed by `3a51ada` (R334, 2026-08-14). `tests/test_r115_followups.py:217` still pins v18 and **FAILS**: `assert '2024.1689.v21' == '2024.1689.v18'` | `KB_VERSION = 2024.1689.v21` (code). ⚠ **The live Aura graph's stamp is a DIFFERENT number** — `/healthz/graph` returns the graph's `m.kb_version` when reachable (`app/main.py:1335-1337`) and falls back to the code constant when not (`:1234`). Code v21 vs graph v18 is the seeder-drift signal of hard rule #12, not a contradiction. Also: fix or delete the v18 pin at `tests/test_r115_followups.py:217` |
| **F2** | `:135` "Cross-reference graph: **149 core** edges, **249 full**" | core **149** ✓, full **248** ✗. `kb_xrefs._build_xref_graph()` summed = 248; `all_edges()` len = 248 | "**149 core**, **248 full**" |
| **F3** | `:391` "Aura `0644b854` … **1758 nodes / 1979 edges** … Measured 2026-08-09" | **UNVERIFIABLE from here and superseded.** `docs/R338-live-opus48-antifragile-graphrag.md:6` measured **1786 nodes / 2076 edges** on 2026-08-15. And live probe: `/healthz/graph` → `{"graph_ok":false,"detail":"unhealthy: ping returned no rows (instance unreachable or read failed)","node_counts":{},"edge_counts":{}}` | Replace the census with the R338 numbers **and add**: "⚠ The deployed service could not reach Aura on 2026-08-15 (`graph_ok:false`). Every claim in this section describes the graph, not the product: with the graph down, `kg_context`, `graph_semantic` and Neo4j vector recall contribute **nothing** to a production answer. Probe `/healthz/graph` before reasoning about graph context." |
| **F4** | `:1122` "`py -3.12 -m evals.regenold.runner` # 276 scenarios" and `:377` "4. 276-runner" | **255**. Ran it: `OVERALL: 255/255 passed (100.0%)`, 28 category blocks, `RISK_F1 macro=1.00` | "# 255 scenarios, 28 categories". The `:369` line already says 255/255 — the file contradicts itself twice |
| **F5** | `:371` "full `pytest` **56 pre-existing failures** … **all** the documented `provider=cli` Stage-2 env artifact" | Count ✓ (`56 failed, 6342 passed, 35 skipped in 333.15s`). **"all" is FALSE.** At least 4 have other causes: `test_external_embeddings.py::test_is_available_logic`, `::test_get_embedding_cohere_mock` and `test_turboquant_index.py::test_turboquant_index_with_external_embeddings` fail on the documented `REGENOLD_EXTERNAL_EMBEDDINGS=0` half of the env, not Stage-2; `test_r115_followups.py::test_stub_names_433_and_mdr_route` is the stale KB_VERSION pin (F1) | "**56 failures** in three named families: `provider=cli` Stage-2 absence (majority), `REGENOLD_EXTERNAL_EMBEDDINGS=0` (3 rows), and one stale constant pin. Judge the SET; a new failure outside these three families is a regression." |
| **F6** | Env table, `REGENOLD_GRAPH_VECTOR_RECALL` \| **OFF** | Code default OFF ✓ (`app/engines/vector_recall.py:68` — `is_enabled()` returns False unless the var is literally `"1"`). **But the deployed service runs it ON.** Live trace note `vector_recall source=svd added=2`, emitted at `_graph_rag_impl.py:2465` inside `if _vr_is_enabled()` (`:2436`). Only a Railway service variable can produce that | Add a banner above the table: "⚠ **This table is CODE defaults. The deployed service overrides them via Railway service variables, which are invisible in this repo.** Measured 2026-08-15: production runs `REGENOLD_GRAPH_VECTOR_RECALL=1` against a code default of OFF. Read the reasoning trace or `railway variables`, not this table, when reasoning about production." |
| **F7** | Gotchas: "The Stage-2 SYSTEM prompt is dropped by the Claude Max wrapper — 0% of requests see it" (already carries an R338 ⚠) | Correction is right but **incomplete in the one way that matters** — see §0. Also the in-tree comments still assert the dead claim: `graph_rag_prompts.py:842`, `_graph_rag_impl.py:7787` | Rewrite the ⚠ to lead with R282: "The wrapper CAN now forward it (`WRAPPER_FORWARD_SYSTEM_PROMPT`). **Do not turn it on without re-running R282's A/B: that exact flip measured kw_recall −0.267, ref_strict −0.155, and lost a position-swapped pairwise judge 8/8 at p≈0.008** (`.planning/R282-CHECKPOINT.md:69-95`). The cause is size — `ANSWER_GENERATE_SYSTEM` is 51,516 chars. Forwarding it is not 'delivering the rules at last'; it is a 51 KB context dump that measurably crowds out the question." |
| **F8** | Gotchas: "The channel inversion — the CORRECT law is on the dead channel" | **Both halves resolved.** The wrong law is gone (`graph_rag_prompts.py:899-907` is now an R338 tombstone comment recording the reverted text); the correct Annex IV(1)(e)/(2)(c) rule is intact in `ANSWER_GENERATE_SYSTEM` (`:118`) and is deliverable now | Cut the incident narrative to two lines; keep only the transferable rule: "When you write a legal rule into a prompt, decide WHICH SLOT it lands in, then check what the other slot says about the same provision." |
| **F9** | Provider story: "four mutually exclusive paths" | **Incomplete — the omitted path is the one serving production.** `/healthz` reports `"is_groq_enabled":true`; `_graph_rag_impl.py:870-889` auto-falls-back to Groq `openai/gpt-oss-120b` whenever the wrapper fails for any reason; `openai_wrapper_provider.py` also carries full GEMINI_* and MISTRAL_* transports | "Four values of `P2P_GRAPH_RAG_PROVIDER` — **plus an in-band Groq fallback that is not a provider value and is not in this table.** `openai_wrapper` silently becomes Groq `gpt-oss-120b` (`_graph_rag_impl.py:880`) on any wrapper failure. Read `stage2_model=` AND the presence of `groq_auto_fallback_success` in the trace; the first alone will name a Claude model that never answered." |
| **F10** | Provider story: the two-row deployed-provider table (bedrock / not-bedrock) | **Third measurement, new answer.** `/healthz/llm` → `{"provider":"openai_wrapper","llm_ok":false,"detail":"api_status_401: Forbidden…","cf_access":{"client_id_set":false,"client_secret_set":false,"headers_attached":false}}` | Replace the two-row history with the standing method and today's reading. Add the cheap instrument the file currently disparages (F11) |
| **F11** | Gotchas: "**`/healthz/llm` lies** — verify the wrapper with a real POST" | Overstated in the direction that cost a session. It reported `llm_ok:false` with the exact failing status, and a live POST reproduced it (`groq_fallback_failed: api_status_429`, `stage2_failed_both_providers_deterministic_ship`) | "`/healthz/llm` is authoritative for **which provider resolved** and **whether CF Access headers are attached**, and its failures are real. It is not proof of success — a green `llm_ok` does not mean Stage-2 lands, because two skip gates and a verdict guard sit downstream. Read it first; confirm success with a POST." |

## 2. WHAT PRODUCTION IS ACTUALLY DOING (new, not in CLAUDE.md at all)

Three live probes, deployed `commit=f7f85ad6f6de` (`origin/main` is one docs commit ahead at `1d55a94` — so the auto-deploy lag claim holds):

```
/healthz      {"status":"ok","version":"1.2.3","commit":"f7f85ad6f6de","is_groq_enabled":true}
/healthz/graph {"graph_ok":false,"detail":"unhealthy: ping returned no rows",
                "kb_version":"2024.1689.v21","node_counts":{},"edge_counts":{}}
/healthz/llm  {"provider":"openai_wrapper","llm_ok":false,
               "detail":"api_status_401: Forbidden. You don't have permission to view this…",
               "cf_access":{"client_id_set":false,"client_secret_set":false,"headers_attached":false}}
```

POST `/api/v1/regenold/eu-ai-act/ask?include_reasoning=true`, *"Who counts as a deployer under the AI Act?"*:
```
stage2_polish: false
notes: ["vector_recall source=svd added=2", "answer_route=synthesis:synthesis_default",
        "stage2_model=claude-opus-5 complex=False",
        "groq_fallback_failed: api_status_429: … `openai/gpt-oss-120b` …",
        "stage2_failed_both_providers_deterministic_ship"]
references: ['Article 26','Article 6','Article 99','Article 35','Article 98','Article 39','Article 42']
```

**The orchestrator's "CONCLUSION TO TEST" is confirmed, with a named root cause.** Production resolves `openai_wrapper`, points at the CF-Access-protected tunnel, and ships **no CF Access service token** (`client_id_set:false`) → every wrapper call is a 401 → Groq rescue → Groq is rate-limited → Stage-2 dies. `cf_access` is a first-class field of `/healthz/llm` and it is the diagnostic; `app/llm/openai_wrapper_provider.py:294-304` shows the headers attach only when `CF_ACCESS_CLIENT_ID` **and** `CF_ACCESS_CLIENT_SECRET` are both set.

Two compounding consequences CLAUDE.md does not connect:
* `stage2_polish:false` → `set_answer_no_cap(_stage2_landed_for_answer and …)` at `app/routes/regenold.py:7505-7508` is False → **`MAX_ANSWER_SENTENCES = 3` and the char cap are re-armed on every production answer.** Hard rule #2's "default ON removes the caps" is true of the code and false of the deployment.
* Graph down + Stage-2 down means production is running near-pure deterministic assembly. Every graded number in "Where we stand" was produced on a different machine than the one that is live.

## 3. WHAT I VERIFIED AND FOUND STILL TRUE — do not touch these

Knowledge surface (all reproduce exactly): `ARTICLE_EXISTENCE` **126** = 113 articles + 13 annexes · `EC_CHECKER_OBLIGATION_MAP` **131** · `DEFINITION_REGISTRY` **68** · Practice **8** / AnnexIII **8** / Phase **4** / RiskScenario **8** / RiskControl **9** / GPAI **4** / ConformityRoute **3** / FRIA **1** / SeriousIncident **3** · tree **1412** nodes (508 para / 367 subpoint / 180 recital / 163 annex_point / 113 article / 68 definition / 13 annex) · BM25 **373** docs @ `avg_doc_len 91.69` unset-or-`=1`, **345** @ `avg_doc_len 94.47` with `=0`, source split `kb 131 / corpus 126 / definition 68 / ontology 48→20` — matches the file byte for byte · embeddings `is_available()` True, **0/4** SHA mismatches vs `embeddings_manifest.json`, TurboQuant enabled.

Env table code defaults — **every single row I could execute matches.** `_DEFAULT_MAX_CHARS 48000` · `_DEFAULT_SEMANTIC_MAX_CHARS 80000` · `_DEFAULT_MAX_UNITS 70` · `_DEFAULT_UNIT_CHARS 2000` / `_UNIT_HARD_CEILING 9000` · `_DEFAULT_MAX_REFS 12` · `_KG_MAX_INFLIGHT 4` · `_DEFAULT_UNITS_KEPT 16` / `_PER_PROVISION 2` · definitions 3 / recitals 3 · `resolve_graph_timeout_ms() 750` · `_GROUNDING_MAX_REFS 12` / `_GROUNDING_REF_CHARS 3000` · `_judge_max_tokens 1600` · `REGENOLD_BEDROCK_MAX_TOKENS 4096` (`_graph_rag_impl.py:585`) · `_STAGE2_TIMEOUT_S 180` (`:593`) · `BEDROCK_RAG_MODEL eu.anthropic.claude-opus-4-8`, complex `opus-5`, `_DENIED_TTL_SECONDS 900.0`, `BEDROCK_FALLBACK_CHAINS` chains exactly as documented · every ON/OFF gate default as printed. **This table is the healthiest part of the file.**

⚠ One live sub-clamp CLAUDE.md flags as fixed is only *half* fixed: `app/engines/graph_semantic.py:549` still reads `_int_env("REGENOLD_KG_MAX_REFS", 8, 1, 10)` — default **8**, ceiling **10** — while `kg_context.py:642/666` uses `_DEFAULT_MAX_REFS=12` with ceiling 24. The documented default of 12 is unreachable on the semantic path. The table's ⚠ ("Four call sites clamped it to 10") should say "one call site still does, at `graph_semantic.py:549`".

Hard rules 1-12, mechanism-by-mechanism:

| rule | still true? | enforcement verified |
| --- | --- | --- |
| 1 format | ✓ and its ⚠ still exact | `_ANNEX_OUTPUT_RE = ^Annex [IVXLC]+(?:\.[A-Za-z0-9]+)*$` — `Annex III.foo.bar` passes; `Art. 13`/`Annex 3`/`Article III` all rejected |
| 2 length cap | ✓ in code | `models.py:247 MAX_ANSWER_SENTENCES = 3`; uncap gated on Stage-2 at `regenold.py:7505` — **inoperative in production today**, see §2 |
| 3 no PDF-topic overfit | policy only | **no automated enforcement found.** Say so, or drop the "rule" framing |
| 4 faithful KB stubs | ✓ | `tests/test_kb_stubs_filled.py` present and green |
| 5 lint floor | ✓ **and its ⚠ is still unfixed** | `tests/test_kb_consistency.py` green. `provision_exists` head-laxity reproduces exactly: `Article 3.999`, `Article 3.14a`, `Annex III.4.employment`, `Article 4.2`, `Annex IX.99` → all `provision_exists=True`, all `get_provision_text=None`. `evals/judge/legal_v2.py:660` **still** gates `NON_EXISTENT_PROVISION` on `provision_exists`. Not stale — still owed |
| 6 dynamic_ab is the gate | ✓ | `evals/harness/dynamic_ab.py` present, `fire_check()` at `:198`, `_row_record()` at `:334` called by `:411` (the R337 dead-veto fix) |
| 7 `--qa-only` not a gate | ✓ | flag still exists at `evals/bench/runner.py:519` |
| 8 recall guard | ✓ | `tests/test_r329_ref_crag_and_gold_dropped.py`, `tests/test_r332_dynamic_ab.py` |
| 9 absent ≠ zero | not re-measurable here | historical sidecar statistic; keep |
| 10 graph additive | ✓ | `graph_semantic` constrained-only; not re-checkable live (graph down) |
| 11 two prose paths | ✓ | `_prose_mention_is_real_citation` at `regenold.py:4306`, applied inside `_add_prose_named_refs` (`:4369`), which is the SHARED function called by path A (`:9356`) and Component D (`:9683`). **Executed the guard**: foreign lead *"Regulation (EU) 2017/745 Article 10"* → `[]`; genuine *"Article 13 requires transparency"* → `['Article 13']`. `tests/test_r325_foreign_citation_guard.py` + `test_citation_guard.py` green |
| 12 never write to Aura | ✓ | `scripts/seed_neo4j_kb.py` `SEED_VERSION = 2026-08-14-sota-airo-fullseed` — still mismatched against the live `2026-08-08-r323-annex-sections`, hazard intact |

Provider resolution: `resolve_provider(None|""|"auto", default_when_auto="openai_wrapper")` → **`openai_wrapper`** on all three; `cli`/`bedrock`/`anthropic` pass through. Signature `Literal['anthropic','cli','openai_wrapper']`. ✓

Legal pin (checked with `get_provision_text`, never memory): `Annex IV` **5,710 chars**, `'ce mark'` absent, `Annex IV.1.e` resolves (73 chars), `Annex IV.2.c` resolves (237) · Article 113 carries both 2026 and 2027 dates · Article 51 has 10^25, not 10^23 · **0** lettered article entries · 68 definitions, no 3(14a)/(14b) · Charter Articles 1/21/47 all resolve in `ARTICLE_EXISTENCE` (the blind-lint-floor claim reproduces). ✓ Cappelli revert in place at `graph_rag_prompts.py:899-907`.

Gates: `runner` **255/255**, 28 categories, RISK_F1 macro **1.00** · OOS `--oos-suite all` **n=51 pass=49 leak=0 wrong=2**, both `adjacent_eu` (DMA, PLD) — matches the file exactly · pytest **56/6342/35**.

All R338 fixes present: `answer_trigram_jaccard` renamed (`metrics.py:142,618`), `threshold_precision_recall_curve` is a raising tombstone (`:721`), `record_note` `_cap = 128`, `turboquant_index._corpus_identity()` (`:100`) + `self._corpus_id` (`:219`), `LIVE_ENDPOINT`/`SIBLING_ENDPOINT` (`antifragile_live.py:78,84`), both bench runners `--provider default=None` honouring an export and resolving to `openai_wrapper` (`run_cappelli_bench.py:409`, `run_live_deep_eval.py:661`, `_resolve_run_provider` at `:336-362`). `USER_ANSWER_COVERAGE_CLAUSE` = **2,241 chars** and still contains the `LEGAL VERSION` sentence. `evals/harness/` + `evals/bench/` load no dotenv except `representative_json.py` — verified by grep, exactly one hit.

## 4. FLAGS THE TABLE OMITS — ranked by how badly they'd change a decision

| flag | site | default | why it belongs in the table |
| --- | --- | --- | --- |
| `REGENOLD_CURATED_STAGE2_SKIP` | `_graph_rag_impl.py:4478`, fires `:8222` | **ON** | With `REGENOLD_DEFINITIONAL_STAGE2_SKIP` it is why Stage-2 lands on **3/20** Antifragile rows (R338 §1). Any Stage-2/prompt/model decision graded on that suite is graded by a blind instrument. This is the single most important undocumented flag in the repo |
| `REGENOLD_DEFINITIONAL_STAGE2_SKIP` | `:4439`, fires `:8241` | **ON** | ditto |
| `REGENOLD_ADAPTIVE_REF_CLAMP` | `regenold.py:4549` | **ON** | CLAUDE.md's R328.3 prose already calls it "default ON, **undocumented**, cuts scenarios to 5 refs" — then leaves it undocumented. Move it into the table |
| `RegenoldChatMessage.content max_length` | `models.py:49` | **4,000, hard-coded, no env** | Rejected a legitimate medtech multi-turn row with 422 `regenold_invalid_input` (R338 §3). A ceiling with no off-switch |
| `CF_ACCESS_CLIENT_ID` / `_CLIENT_SECRET` / `_HOSTNAME` | `openai_wrapper_provider.py:263-265,294-304` | unset | **This is the production outage.** Without both, no headers attach and the tunnel 401s |
| `GROQ_API_KEY` / `REGENOLD_GROQ_DEFAULT_MODEL` | `openai_wrapper_provider.py:766,756` | key-gated | the actual Stage-2 provider in production |
| `REGENOLD_NOISE_SUPPRESS` | `regenold.py:2874` | **ON** | R338 §4 saw it drop `Article 6` on a *"is this high-risk"* question |
| `REGENOLD_MAX_QUESTION_CHARS` | `regenold.py:2075` | `_MODEL_MAX_QUESTION_CHARS` | context truncation lever |
| `REGENOLD_STAGE2_CHAR_CAP` | `regenold.py:9571` | **600** | a second char cap, undocumented |
| `REGENOLD_BEDROCK_STAGE1_MODEL` / `_STAGE2_MODEL` | `_graph_rag_impl.py:567,569` | unset → `REGENOLD_BEDROCK_MODEL` | the table documents only `REGENOLD_BEDROCK_MODEL`; two finer overrides exist and shadow it |

## 5. THE davidath BLOCK — recommendation

The current framing (retired + `<details>` + "HISTORICAL ONLY") is **not sufficient**, for a reason the file itself supplies: those numbers were re-measured *again* at R331 and printed in full inside the collapsed block, which is an invitation to quote them. A retired instrument that keeps publishing fresh readings is not retired.

The numbers also have no remaining use. They cannot gate (retired), cannot compare (they predate the three ungated R329 default-ON flips, by the file's own ⚠), and cannot be reproduced meaningfully now that the running system differs from the code defaults (F6). "Kept because older round entries reference it" is served by `docs/ROUNDS.md`, which is where round history lives.

**Delete the table. Replace the whole "Current baseline" section with:**

> ## Current baseline — THERE IS NONE. This is deliberate.
>
> There is no standing scorecard to grade a change against. davidath (`evals.bench.runner`, 476 rows) was retired 2026-08-14 by operator directive and its numbers are removed from this file rather than archived, because a retired instrument that still publishes readings gets quoted. If you need them, `git log -S "0.3545" -- CLAUDE.md` and `docs/ROUNDS.md`.
>
> Grade a change with `evals.harness.dynamic_ab`: it fire-checks (aborts `INERT` rather than reporting `+0.0000` as safe), sizes itself to observed variance, distinguishes NULL from UNDERPOWERED, and vetoes on `gold_dropped`.
>
> Cheap regression guards that still mean something, re-measured 2026-08-15: `evals.regenold.runner` **255/255**, 28 categories, RISK_F1 macro **1.00** · OOS `--oos-suite all` **51 rows, 49 pass, 0 scope leaks**, 2 known `adjacent_eu` soft fails · `pytest` **56 known failures** in three named families (see Testing).

And under Validation policy, add the rule the round actually taught:

> **Before running any instrument, ask what fraction of rows it can move.** davidath was retired for running `provider=cli`. The Antifragile suite has the same blindness from the product side: two default-ON skip gates (`REGENOLD_CURATED_STAGE2_SKIP`, `REGENOLD_DEFINITIONAL_STAGE2_SKIP`) mean Stage-2 lands on **3 of 20** rows, so it can move at most 15% of the suite on any Stage-2, prompt or model change. Report the reachable fraction alongside the delta, or the delta is uninterpretable.

## 6. WHAT I COULD NOT DETERMINE

* **Which Railway service variables are set.** I have no `railway` CLI auth and there is no config endpoint (`/openapi.json` exposes only `/`, `/app`, `/healthz`, `/healthz/{email,graph,llm}`, `/info`). `REGENOLD_GRAPH_VECTOR_RECALL=1` is *inferred* from a trace note that is unreachable when the gate is off — solid, but it is one variable out of an unknown set. Every other env-table row could be overridden in production and I would not see it.
* **The live graph census.** Aura is unreachable from the deployment and I have no credentials, so I could neither confirm 1758/1979 nor 1786/2076, nor read the graph's own `kb_version`/`seed_version` (both came back empty).
* **Whether the graph outage is credential drift, an Aura pause, or a network block.** `/healthz/graph` says only "ping returned no rows".
* **Whether the R338 answer regression is caused by the system-prompt flip.** The sign matches R282 and the magnitude is smaller, but R338 localises 3 of 3 regressed rows to the deterministic path, where the system prompt cannot reach. Resolving it needs an A/B on a suite where Stage-2 actually fires — which, per §5, the Antifragile suite is not.
* **Every number in "Where we stand" and "Do not re-propose"** (frontier standing, the oracle +0.215/+0.229, wrong-rate-by-rank, the R325 AUC table, the July-7 0.780/0.950/0.900). These are LLM-judge measurements; re-running any of them requires wrapper calls, which this assignment forbids. I did not verify a single one and this report should not be read as endorsing them.
* **`scripts/check_legal_version_drift.py`** — needs Cellar SPARQL network access; not run.

==========================================================================================
## agent result #7  (len 15526)
==========================================================================================

# ADVERSARIAL CHALLENGE — R338 ranked-items audit

Everything below was executed this session. Repo HEAD is **`1d55a94`** (not `f7f85ad` as the brief states — a docs-only commit landed on top).

---

## CONFIRMED (reproduced from scratch)

**Item 1 mechanics.** `evals/bench/results/graphrag-bench-r338-opus48-graphrag.json` → 40 GT rows, 0 NG rows, `endpoint: http://127.0.0.1:8100/...ask` with no query string, `reasoning` present on all 40 and `''` on all 40. `run_graphrag_benchmark.py:101` (GT) and `:140` (NG) store `body.get("reasoning")` — the report cites `:102`, it is `:101`. `--local` already appends at `:251`. `_maybe_serialize_reasoning` at `app/routes/regenold.py:5627` returns `None` when the param is absent. I verified the param on the **deployed** service, not just locally:

```
POST .../ask                        -> "reasoning":""
POST .../ask?include_reasoning=true -> "reasoning":"{\"schema_version\":\"r50.1\",...
   notes: ['vector_recall source=svd added=2', 'stage2_skipped_pure_definitional']
```

**Item 1.2 observer effect — confirmed, and with better evidence than the report gave.** `grep -n force_stage2` returns exactly `8152, 8156, 8160, 8164, 8175, 8186, 8195, 8277`. Executed under shipped defaults: `_stage2_simple_skip_enabled() False`, `is_web_search_enabled() False`, `_curated_stage2_skip_enabled() True`, `_definitional_stage2_skip_enabled() True`. I then ran all 132 probe rows twice (plain vs `?include_reasoning=true`) with `_claude_max_enhance_answer` replaced by a sentinel:

```
SIMPLE_SKIP=0: stage2 landed plain=125/132  reasoning=125/132  ROWS THAT DIFFER=0
```

**Item 2 — fully confirmed, byte-exact.** `app/integrations/regenold/models.py:49` `content: str = Field(min_length=0, max_length=4_000)`; `:61` `messages: ... max_length=64`. `mt_med_07` user turns are `[235, 163, 182]`. Deterministic repro (`provider=cli`, TestClient, the recorded 4301-char turn-1 answer):

```
per-message chars = [235, 4301, 163]   -> status 422
loc ["messages", 1, "content"]  type string_too_long
control (assistant truncated to 4000) -> status 200
```

`_MAX_QUESTION_CHARS = 64_000` (`app/models.py:54`), `_HISTORY_TURNS_TO_INCLUDE = 40` (`routes/regenold.py:2058`), and `grep -rn "content_length|max_body|BodySizeLimit|request_size" app/` returns **0 hits** — no body-size middleware. `tests/test_regenold_integration.py:15-16 _messages()` builds `role="user"`, so both pinning tests (`:150-163`, `:166-179`) do survive a role-asymmetric cap. Blast radius as stated.

**Item 3 — the metric analysis is correct.** `antifragile_live.py:324-325` computes `coherent` from `refm`/`kw`, which are computed at `:308-309` from `final_body` only (`:305-306`); `:383` aggregates it; `:299` echoes the answer into history. It never reads turn 1 or 2. `MEDTECH_MULTITURN[0].keys()` = exactly the 6 keys listed, no per-turn gold. `compare.py:80-87` reads a `multiturn_coherence` sub-dict this runner never writes. The 0.2222 decomposition reproduced **row-for-row, all 9 rows and every failing gate**.

**Item 3.4 — the `mt_med_08` repro is exact.** Single-turn, no history, `provider=cli`:

```
refs = ['Article 68', 'Article 56', 'Article 57']
_deterministic_parse(q).entities = ['Art. 68','Art. 56','Art. 57','Art. 5','Art. 4','Art. 3','Art. 9','Art. 10']
live turn2 refs ['Article 53','Article 55','Article 56','Article 57','Article 68']
live turn3 refs ['Article 55','Article 56','Article 57','Annex XI','Article 53.1.a','Article 53.2']
```

Gold is `expected_refs: ['Art. 5']`, so "Art. 5 is retrieved at rank 4 and never reaches the wire" is dataset-backed, not the auditor's opinion.

**Item 4.1 — the probe-set numbers are exact.** 132 rows, 2 curated, 0 definitional, and the seven-source table reproduces line for line. Antifragile: 10 curated (`q02 q05 q06 q07 q09 q10 q11 q12 q17 q20`) + 1 definitional (`q08`) = 11; `stage2_polish` true on `q01 q13 q18`; the 6 unexplained are `q03 q04 q14 q15 q16 q19`. I went further and proved by execution that all 6 **do** reach `_claude_max_enhance_answer`, so the population is real.

**`dynamic_ab` gap confirmed.** Zero mentions of `include_reasoning`. `_row_record` (`:334-379`) never receives `body`; `_run_rows` (`:382`) builds `local://...` at `:399-401` with no `?`; `runner_v2._post_local:210` defaults `qs = "include_reasoning=true"`. `_http_retry.py:348 post_json_with_retry` passes `url` through unmodified (`:344`).

---

## CORRECTED

**C1 — the deployment sha moved within the day.** `GET /healthz` now returns `commit: 1d55a94ac238`, not `f7f85ad6f6de`. `1d55a94` is docs-only (`git show --stat`: 1 file, `docs/BENCHMARK_QA_GROUND_TRUTH_ANALYSIS.md`), so the code claim survives — but "the deployed commit is HEAD, so everything below describes what is live" is a sha-pinned assertion with a half-day shelf life. State the property (deployment tracks `main`), not the sha.

**C2 — the latency calibration is wrong in both directions.** Measured over the 40 rows: **6** under 100 ms (report: 5), **15** over 3000 ms (report: 12), **mean 2220.6 ms**. The `run_cappelli_bench.py:312` rule is `mean_latency_ms < 2000.0` — at 2220.6 it **would not have fired**. So "the 2-second mean-latency heuristic is wrong here" is unsupported by the artefact cited. The defensible version: the distribution is bimodal, so the mean is uninformative *even when it passes*; use `stage2_landed_rate == 0.0` as the alarm and report per-row latency, not the mean, as the secondary signal.

**C3 — "48 recorded answers … p50 766.5" is 50 answers, p50 765.0.** max 5498, p95 3991, >4000 = 3, >3000 = 5 are all correct; the count and median are not.

**C4 — "`mt_med_10` turn-3 landed at 3991 chars — nine characters from the same 422" is FALSE.** A turn-3 answer is terminal: the scenario ends, so it is never appended as an assistant message. Of the **20 answers the runner actually replays**, only one exceeds 4000 (`mt_med_07` turn 1, 4301) and the runner-up is `mt_med_05` turn 2 at **3051**. Real headroom is ~950 chars, not 9:

```
REPLAYED (assistant msgs actually re-sent) n=20  max 4301
  >4000: [('mt_med_07',1,4301)]
  >3000: [('mt_med_05',2,3051), ('mt_med_07',1,4301)]
```

This also undercuts the fix sizing: 16 000 was justified as "covers the measured max 5498 with ~3× headroom", but 5498 is `q01`, a **single-turn antifragile** answer that can never be replayed. Size the assistant cap off the replayed distribution (max 4301), not off the global max.

**C5 — "5 of 9 medical-device answers open with GPAI boilerplate" is 4.** Openers measured:

```
mt_med_02 'Under Article 53, GPAI providers...'   gold ['Art. 6','Art. 50','Annex III']  -> real failure
mt_med_03 'Under Article 53, GPAI providers...'   gold ['Art. 16','Art. 25','Art. 26','Annex IV'] -> real
mt_med_05 'GPAI provider obligations: ...'        gold ['Art. 2','Art. 6','Annex I']     -> real
mt_med_08 'Under Article 53, GPAI providers...'   gold ['Art. 5']                        -> real
mt_med_06 'Under Article 50, limited-risk...'     gold ['Art. 50']   ref_loose=1.000     -> NOT a GPAI failure
```

`mt_med_06` opens on its own gold article and scores `ref_loose 1.000`; it fails on keyword recall alone. The report counted it **twice** — once as a threshold artefact in §3.2 and again as a GPAI failure in §3.3. Meanwhile `mt_med_09` (refs = `['Article 11']` alone against 5 gold refs — severe under-retrieval) is a genuine failure the report never mentions. The headline "~2 artefacts, ~5 real" survives by coincidence; the composition is wrong, and a fixer chasing "GPAI drift" on `mt_med_06` would be chasing nothing.

**C6 — two rows of the Item 1.4 runner table are wrong.**
- `evals/regenold/run_hard_sample_r297.py:286-287` carries the canonical auto-append (`if "include_reasoning" not in url: url = f"{url}{'&' if '?' in url else '?'}include_reasoning=true"`). It belongs in the ✅ column, not the "local-only append" long tail.
- `evals/regenold/runner_r89_probe.py`'s only mention is at `:9`, inside a docstring usage example. There is no append at all, local or remote.

**C7 — two ✅ rows hide live defects.** `run_medtech_subpoint_eval.py:79` is `args.endpoint if "?" in args.endpoint else args.endpoint + "?include_reasoning=true"` — any endpoint carrying *any other* query param silently loses the trace. `runner_oob.py:303` bakes the param into the **default string only**; an operator-supplied `--endpoint` (the normal way to point it at the sibling service) drops it. Both are the same bug class the item is about.

**C8 — the proposed `stage2_reachable` filter is over-inclusive by 3 rows, and blind to why.** The two predicates give 130 survivors. End-to-end (real route, `_claude_max_enhance_answer` instrumented) only **127 of 132** reach the Stage-2 call site:

```
TOTAL 132  REACHED stage2 call site 127  NOT 5
reasons: 2  stage2_skipped_curated_authoritative
         3  <no stage2 note>
  tr_v2_029 (DSA)  tr_v2_030 (PLD)  tr_v2_031 (NIS2/CRA)  -> refs [], scope-gate refusal, NO note
```

Those three are intercepted by `classify_conversation` **before the engine**, so a filter built on the two Stage-2 predicates cannot see them by construction. This is the repo's signature failure inside the proposed fix for the repo's signature failure. The filter must be built on observed reachability (Step 1) or on a third predicate, not on the two Stage-2 gates alone.

**C9 — "the R104 and R112 comments are stale" is an overreach.** Executed, same 132 rows, one variable changed:

```
SIMPLE_SKIP=0: plain=125/132  reasoning=125/132  ROWS THAT DIFFER=0
SIMPLE_SKIP=1: plain=105/132  reasoning=125/132  ROWS THAT DIFFER=20
```

The comments are **conditionally correct**, and the condition is `REGENOLD_STAGE2_SIMPLE_SKIP`, read fresh per call (`_graph_rag_impl.py:1455`, `getenv(..., "0")`) and therefore settable as a Railway service variable that is invisible from this repo — CLAUDE.md's own standing finding about deployed config. Ranking `easyhard_ab` as a fix target "whose docstring rationale is now measured false" is **UNSUPPORTED until `railway variables` is read** for service `0086ff18-…`. I could not run that (no CLI auth in scope) — flagged as a gap, not a conclusion.

**C10 — §1.2 is largely a restatement of an existing in-tree comment.** `evals/bench/run_live_deep_eval.py:260-289` already states the two consumers, the two default-OFF gates, the byte-identical `provider=cli` verification and the `_engine_cache_key` split. The report cites it once in passing but presents the content as "Measured:", and drops that comment's closing caveat — *"Re-check both gates before quoting a number."* C9 is exactly why that caveat matters.

---

## UNSUPPORTED — drop these

1. "the 2-second mean-latency heuristic from `run_cappelli_bench.py:312` is **wrong here**" — mean is 2220.6 ms, it would not have fired.
2. "`mt_med_10` turn-3 … nine characters from the same 422" — turn-3 answers are never replayed.
3. "5 of 9 medical-device answers open with GPAI boilerplate" — 4; `mt_med_06` is double-counted.
4. "130 of 132 rows survive" as a Stage-2-reachable count — 127.
5. "the R104 and R112 comments are stale" as an unconditional claim.
6. assistant cap sized to "cover the measured max 5498" — that answer is single-turn and unreplayable.

---

## NEW — defects the report missed, each executed

**N1 — `stage2_skipped_simple_question_deterministic_ship` (`_graph_rag_impl.py:8202`) is unrecordable by construction.** The branch guard is `_stage2_simple_skip_enabled() and not force_stage2 and …` (`:8193-8196`), while `:8160-8165` sets `force_stage2 = True` whenever `reasoning_trace.current() is not None` — and `record_note` only writes when a trace is active. Trace on ⇒ branch not taken; trace off ⇒ note discarded. Grep over every `*.json` / `*.jsonl` in the repo: **zero occurrences, ever**. Consequences: (a) the report's Step-1 "make `dynamic_ab` observe Stage-2" plan can never diagnose a simple-skip; (b) the deployed value of `REGENOLD_STAGE2_SIMPLE_SKIP` is not inferable from *any* trace, which is what makes C9 unresolvable by probing. Fix by moving the note above the `not force_stage2` term, or by recording the resolved gate values unconditionally.

**N2 — `antifragile_live._parse_reasoning` (`:135-157`) discards `notes`.** It keeps 7 derived fields and scrapes only `answer_route=` and `stage2_model=…complex=…` out of the note list. So even though that runner *does* request the trace (`:404-405`), the R338 artefact structurally cannot say **why** a row skipped Stage-2 — confirmed: every row's `reasoning` dict in `.evalout/r118/live_r338-opus48.json` has the same 7 keys and no `notes`. This is a second, independent and cheaper cause of the report's own "what I could NOT determine" item than adding `record_note` calls at `:8177`/`:8181`.

**N3 — the two R338 templates disagree on the block name.** `run_cappelli_bench.py:319` writes `"run_provenance"`; `run_live_deep_eval.py:598` writes `"run_config"`. A fix told to "mirror both" will pick one and drift from the other — this repo's "one concept, one definition" rule, violated in the very commit that codified it.

**N4 — the mtrag proposal needs an adapter it doesn't mention.** `evals/bench/mtrag.py:53-107` consumes `turn["question"]` and `turn["gold_refs"]` on **dict** turns via an `agent(turn, history)` callback. `MEDTECH_MULTITURN[*]["turns"]` are plain **strings**. Adding `expected_refs_per_turn: [[...], [...], [...]]` produces a shape `mtrag` cannot read.

**N5 — legal check on the one contested characterisation.** `get_provision_text("Article 5.1.f")` resolves to 313 chars and reads, verbatim from the pin: *"…to infer emotions of a natural person in the areas of workplace and education institutions, except where the use of the AI system is intended to be put in place or into the market for medical or safety reasons"*. `mt_med_08` is a hospital-staff fatigue monitor and its turn 2 raises exactly that carve-out, so "textbook Article 5(1)(f)" overstates a genuinely contested case. The dataset's own `notes` field says the carve-out is narrow and "does not clearly qualify", and gold is `['Art. 5']` — so the **conclusion** (Art. 5 belongs on the wire, and the deterministic ranker drops it) stands. Also verified against the pin: `Article 27` = 2837 chars, FRIA; `Article 26.5` = the deployer serious-incident duty; `Article 51` = GPAI systemic-risk classification; `Article 52` = notification procedure; `Annex IV.1.e` (73 chars, hardware) and `Annex IV.2.c` (237 chars) both resolve — i.e. the legal claims the report inherits from R338 §4 all check out.

---

## What I could NOT determine

* **The deployed value of `REGENOLD_STAGE2_SIMPLE_SKIP`** — no `railway variables` access, and N1 makes it unobservable from a trace. Until it is read, C9 stands as "conditionally correct", not resolved either way.
* **Whether the 127 reachable probe rows land Stage-2 live.** Forbidden from calling the wrapper. My sentinel run gave 125/132 keeping the polish on the wire vs 127 reaching the call site; the 2-row gap is almost certainly `REGENOLD_STAGE2_VERDICT_GUARD` rejecting a bare sentinel string, i.e. an artefact of my probe, not a finding. Treat **127** as the reachability number and 125 as noise.
* **Why `q03 q04 q14 q15 q16 q19` did not land Stage-2 live.** I confirmed all six reach `_claude_max_enhance_answer`; N2 explains why the artefact cannot say more.
* **The provider that served the R338 graphrag run.** Unrecoverable, as the report says — `127.0.0.1:8100` is gone and the sidecar has no provenance.

==========================================================================================
## agent result #8  (len 17187)
==========================================================================================

# ADVERSARIAL CHALLENGE — bypass-mechanics audit

Everything below was executed. Offline env: `PYTHONIOENCODING=utf-8 OPENAI_API_BASE=http://127.0.0.1:1/v1 P2P_GRAPH_RAG_PROVIDER=cli REGENOLD_EXTERNAL_EMBEDDINGS=0`, `py -3.12`. Live probes: 4 read-only POSTs to the deployed Railway service (no wrapper calls). Repo HEAD `1d55a94` (one docs commit past `f7f85ad`).

---

## HEADLINE: the experiment it designed already ran today, and returned nothing

`.evalout/r118/live_r339-armA-bypass-on.json` (mtime **2026-08-15 15:55:21**) and `live_r339-armB-bypass-off.json` (**15:57:56**) are exactly Experiment A on the Antifragile 20, k=1, two servers (`:8110` / `:8111`).

```
armA (CURATED_SKIP=1)  stage2_polish TRUE on  0/20
armB (CURATED_SKIP=0)  stage2_polish TRUE on  0/20
answer text differs on rows: []          refs differ on rows: []
total answer chars  armA 13889   armB 13889
summary identical to 4dp: ans_strict 0.6403 / ref_strict 0.8288 / ref_subpoint_strict 0.6006
                          keyword_recall 0.7981 / mistakes 28/38 in BOTH arms
```

The **flag did fire** — armB records `stage2_model=claude-opus-4-8` on all 20 rows including the 11 gated ones (armA records it on 0 of the 11) and their latency rises (q07 583→696 ms, q06 353→941 ms, q20 176→1691 ms). But **no polish survived on any row in either arm**, so the outcome is byte-identical. The report's own FIRE CHECK correctly voids this run — but its stated premise ("the 11 firing rows must show `stage2_polish=True` in arm OFF") is empirically false under today's provider state.

---

## CONFIRMED (I reproduced it)

| claim | my reproduction |
|---|---|
| Gate ladder `:8177` polish → `:8181` provider → `:8193` simple-skip → `:8222` gate A → `:8241` gate B; provider gate returns first | line-exact. Executed the consequence: same question, `REGENOLD_CURATED_STAGE2_SKIP=1` vs `=0` under `provider=cli` → refs `('Article 1','Article 4')` both, `answer_len 504` both, `IDENTICAL: True` |
| Defaults ON, off-switch `=0` | `_graph_rag_impl.py:4478-4480` and `:4439-4441`, `os.getenv(...,"1") not in ("0","false","no","off")` |
| `_is_curated_authoritative_intercept` = flat disjunction of **27** detectors, `:4516-4570` | exact, order matches |
| "each strips a `Latest question:\n` prefix" | I checked **all 27**, not one: `27/27` strip it |
| Fire rates | **exact match, all four datasets**: AF 10 CUR / 1 DEF / 11 EITHER (55.0%); GraphRAG 11/3/14 (35.0%); official 19/4/22 (20.0%); probe_set 2/0/2 (1.5%). Per-row Antifragile table, GraphRAG hit ids, official CUR/DEF id lists, and the by-source probe breakdown all reproduce byte-for-byte |
| R338 cross-tab, 20/20 predicate agreement | exact: 11 fires, 3 polish, `contradictions []`, and `['q03','q04','q14','q15','q16','q19']` carry `stage2_model` with `polish False` |
| Cache-key hashes | **byte-identical**: `f4cb390dbddd4a3f718377ea` / `a5be0a1c0c62fe0d3375c4c0` / `f5c4fb1b7373324a169a9c4d` |
| Route `_is_curated_authoritative_intercept` at `regenold.py:7400` is NOT gated by the flag; both flags in `_engine_cache_key` at `:1928-1929` | confirmed |
| Raw `notes` discarded by `antifragile_live._parse_reasoning:135-159` | `stage2_failed_both_providers` 0, `drift_guard_dropped` 0, `contradiction_guard_dropped` 0, `stage2_fidelity` 0, **`notes` 0** in the r338 artefact |
| probe_set 208 gold refs, **0** leaf-grained | exact |
| Antifragile firing rows: 25 subpoint refs, **14** leaf, 19/38 mistakes | exact, and the 14-item leaf list matches item for item |
| **The docx** | 20 `Q` lines, **exactly one** Q8 block (para 88-95). A: contains *"infers, from the input it receives, how to generate outputs"* in full. **`Review: Correct.`** `antifragile_reviewer_remarks['q08']['review'] == 'Correct.'`; `ANTIFRAGILE_GT['q08']` verdict `correct`, `mistakes []` |
| Legal (resolved against the pin, not memory) | `definition_citation_for_question(Q8) -> Art. 3.1`; `get_provision_text("Article 3.1")` = **372 chars**; all three tokens `infers` / `from the input it receives` / `how to generate outputs` present in BOTH the pin and `select_definition_sentence(Q8)` |
| Config-drift table | `31881df` = *"R275: Antifragile fixes"*, **2026-07-05**. `31881df:app/config.py:33` = `stage2_model: str = "claude-opus-4-8"`. `31881df:app/llm/openai_wrapper_provider.py` → **0** case-insensitive `alias` hits (689 lines). `31881df:app/data/graph_rag_prompts.py` → 261 lines, **0** `USER_*` clauses. Today: 989 lines, **5** (`REF_MINIMALITY`, `REF_UNCERTAINTY`, `CHALLENGE_BREVITY`, `SUBPARAGRAPH_ATTRIBUTION`, `ANSWER_COVERAGE`) |
| stage2_fidelity | `enabled True mode fallback`; q12 with the R144 degraded polish → det tiers `['high_risk','limited','prohibited']`, polish `['prohibited']`, `cross_tier_ask True`, **`action=fallback_verdict_flip`, `restored_deterministic=True`**; q06/q07/q09/q17/q02/q10 all `cross_tier_ask False`. Wired at `:8410-8435` |
| R282 confound | `_graph_rag_impl.py:7790-7791` warning verbatim; corrected account `graph_rag_prompts.py:521-533`, `:528` = *"easyhard_ab n=40/arm, plus a pairwise sweep 8/8, p~0.008"*. `:531-533` says R282 supports **exactly one** claim: do not newly deliver the accreted system prompt on any channel — which is precisely what `WRAPPER_FORWARD_SYSTEM_PROMPT=1` does. **Confound stands.** |
| `--limit` is inert | declared `antifragile_live.py:396`, `grep args.limit` → **0 hits**; `run_antifragile:258` iterates all of `ANTIFRAGILE_GT` |

**Strengthened, not merely confirmed — the dynamic_ab blindness is deterministic, not probabilistic.** `_stratified` is seed-fixed, so there is no expectation to take:

```
max_rows= 24  pool=24  tricky_v2=3   gate-firing rows in pool = 0  []
max_rows= 60  pool=60  tricky_v2=8   gate-firing rows in pool = 1  ['tricky_v2:tr_v2_009']
max_rows=132  pool=132 tricky_v2=31  gate-firing rows in pool = 2
```

The INERT gate at `dynamic_ab.py:485` triggers at `len(base_rows) >= min(batch*2, len(pool))` = **24** by default. At that checkpoint **zero** gate-firing rows have been run. So with defaults the harness aborts before it has ever executed a row that can fire the lever.

---

## CORRECTED

### C1 — "6 rows called Opus 4.8 and threw the answer away" is wrong about the mechanism. **This is the report's central novel claim.**

`stage2_model=` is recorded at `_graph_rag_impl.py:765-782`, **before** the HTTP call at `:811`. The report says this "proves an attempt" (true) and then asserts "Opus ran and its output was rejected" (not established). I measured the actual channel — live, on the deployed service, on two of those exact six rows:

```
== q03 "What is the definition of high risk?"       7537 ms  polish=False
   - stage2_model=claude-opus-5 complex=False
   - groq_fallback_failed: api_status_429 ... `openai/gpt-oss-120b` rate limit
   - stage2_failed_both_providers_deterministic_ship
== q15 "Can a hospital use an AI system to sort patients ..."  6773 ms  polish=False
   - stage2_model=claude-opus-5 complex=False
   - groq_fallback_failed: api_status_429 ...
   - stage2_failed_both_providers_deterministic_ship
```

The channel is `:8315` — the `enhanced is None` branch at `:8301`, i.e. **the call never returned**. Not the drift guard, not the contradiction guard, not the verdict guard. Corroborating evidence inside the report's own artefact: q15 = **941 ms** and q19 = **926 ms** total request time in `live_r338-opus48.json`. No Opus completion fits in that. Correct statement: *Stage-2 was attempted on 6 of 9 non-gated rows and never returned an answer.* That is a provider-availability failure, already instrumented, not an undocumented "rejection" channel.

**Consequence:** the report's re-diagnosis of R338 §2 ("the correct diagnosis for q03/q04/q14 is 'Opus ran and its output was rejected', a different bisect target") collapses. R338's original wording ("none of which runs Stage-2") is closer to right than the correction.

**And it closes the report's declared gap #1 without the prerequisite it names.** The notes are in the trace today; `antifragile_live._parse_reasoning:135-159` is the only thing dropping them. Persisting them is a good fix, but it is *not* a prerequisite for the experiments — the live endpoint hands them over on request, and I read them.

### C2 — "the sensitivity control will actively mislead → clean INERT" is unsupported and probably backwards

`grep P2P_GRAPH_RAG_PROVIDER evals/harness/dynamic_ab.py` → one hit, `:10`, inside the docstring about davidath. **dynamic_ab never sets the provider**; it inherits the ambient env. So the control `P2P_GRAPH_RAG_ENABLE_STAGE2=0` (`:261`) moves rows only if Stage-2 currently lands. Under the repo's documented deterministic env it cannot (provider gate returns at `:8181`), and under today's measured live state Stage-2 lands on **0/20** rows. In both cases the control moves zero rows → `fire_check` False → **`BLIND_PROBE`** at `:508-528`, whose text at `:516-519` names this exact failure: *"Curated and definitional rows short-circuit to a direct KB lookup and never reach retrieval, the graph, or Stage-2 — a pool of them is blind by construction."* The harness is more honest than the report credits. The report also missed `--control-layer` at `:750-753` (its "argparse `:735-751` has `--max-rows/--batch/--seed` only" is short by two lines and one flag).

### C3 — the fire check the report specifies is the wrong one

It specifies `stage2_polish=True` in arm OFF. That conflates *the flag fired* with *Stage-2 succeeded*, and it is why the r339 run reads as void rather than as informative. The correct pair:
- **Lever fire check:** `stage2_model` note **present** on the 11 gated rows in arm OFF and **absent** in arm ON. (r339 passes this: 11/11 vs 0/11.)
- **Experiment precondition, checked before spending an arm:** `stage2_polish` > 0 somewhere in the baseline arm. (r339 fails this: 0/20. Abort before running arm B.)

### C4 — `mistakes_resolved` is saturated on the treatment population

Measured on `live_r339-armA`:

```
firing rows (11): mistakes 18 / 19    non-firing rows (9): 10 / 19
```

The 11 gate-firing rows already resolve **18 of 19** expert mistakes deterministically. Maximum detectable *benefit* from letting Stage-2 run there is **+1 mistake** (q05, 1/2). The axis the report sells the Antifragile suite on can detect harm, not gain. Its comparison-table row "expert-flagged mistakes on firing rows: **19 of 38**" is arithmetically right and analytically misleading — the available headroom is 1.

### C5 — model mismatch between the arms and both the motivating run and production

`app/config.py:33` → `stage2_model = "claude-opus-5"`; `complex_model = "claude-opus-5"`; `model = "claude-sonnet-5"`. Alias rewriting is **default OFF** (`_model_alias_enabled` reads `REGENOLD_WRAPPER_MODEL_ALIAS`, default `"0"`; `resolve_wrapper_model('claude-opus-5') -> 'claude-opus-5'` — identity). Production today reports `stage2_model=claude-opus-5`. R338 and R339 both ran `claude-opus-4-8`, i.e. an operator env override. The report's command blocks pin neither model nor `WRAPPER_FORWARD_SYSTEM_PROMPT`, so as written the arms would run a **different model** from the run that motivated them and from the R338 baseline they'd be compared against.

### C6 — `--mode hard` changes the firing set, so the "22 official firing rows" do not carry over

The graded turn in hard mode is the **pushback**, not the original question:

```
gate fires on EASY final turn      : 22 / 110
gate fires on PUSHBACK final turn  : 20 / 110
lost on the graded turn: ['rg_012', 'rg_027']    gained: []
```

And that is before the route's coref resolution (`resolved_question or question`, `_graph_rag_impl.py:8149`), which the report flagged as a caveat for probe_set but not here.

### C7 — the R275 falsification is right about the code comment, over-broad about ROUNDS.md

- `_graph_rag_impl.py:8235`: *"the expert failed Q8 for dropping the AI-system 'infers … how to generate outputs' clause"* — **false**, contradicted by the docx (Q8 has the clause, verdict "Correct.").
- `ROUNDS.md:9607`: *"the expert failed **the exact sample that dropped it**"* — points at a sample not in the docx. **Unevidenced, not contradicted.** One is a false statement; the other is unfalsifiable. Merge them and you overclaim.

### C8 — line/label slips

- `:8360` / `:8386` are the comment/log lines; the `record_note` calls are **`:8368`** (`stage2_drift_guard_dropped_polish`) and **`:8394`** (`stage2_contradiction_guard_dropped_polish`). `:8301` is the `if enhanced is None:` branch head; the note is `:8315`.
- Comparison table "gold refs on firing rows: **25**" is the *sub-point* gold count. Head-level `gold_refs` on those rows is **20**. Two different columns, one label.
- `graph_rag_prompts.py` is **989** lines today / **261** at R275 (report: 988 / 260). docx has **245** `<w:p>` elements (report: 115 paragraphs — presumably non-empty only; I did not confirm that filter).

---

## UNSUPPORTED — drop these

1. *"The other 6 rows called Opus 4.8 and threw the answer away."* → C1.
2. *"the discard rate is 6/9 = 67% — a larger loss channel than either gate, and undocumented."* → C1. It is a provider outage, and it is documented as `stage2_failed_both_providers_deterministic_ship`.
3. *"The correct diagnosis for those rows is 'Opus ran and its output was rejected'."* → C1.
4. *"That control will move most probe rows … the run prints a clean INERT."* → C2. Asserted, never executed; the measured Stage-2 landing rate of 0 makes `BLIND_PROBE` the likelier verdict.
5. *"E[gate-firing rows] ≈ 2 × 9/31 ≈ 0.6."* → `_stratified` is seeded and deterministic: exactly **1** at `--max-rows 60`, exactly **0** at the 24-row INERT checkpoint. Replace the expectation with the number.
6. *"Persisting `notes` … is a prerequisite for any of the experiments below."* → C1. Useful, not blocking.
7. *"a drop rate of even 10% needs ~30 samples/arm"* (Experiment B power) — no calculation shown, and with Stage-2 landing 0% arm B currently produces **0** polished samples at any k.
8. *"gate A's R144 justification is redundant today"* — the R146 mechanism reproduces exactly as claimed, but `guard_cross_tier_polish` runs at `:8415`, i.e. **only on a polish that exists**. With polish landing 0%, redundancy is untested in the live system. The offline reproduction is a construction, not a measurement.

---

## What I measured about production, since the brief says re-measure

```
GET  /healthz  ->  {"status":"ok","version":"1.2.3","commit":"1d55a94ac238",
                    "deployment_id":"5e013dc2-...","is_groq_enabled":true}
```
Deployed commit tracks HEAD. The **curated gate is live in production** — probing q07 returned `stage2_skipped_curated_authoritative` + `curated_ref_protect: prune skipped`, refs `['Article 1','Article 4']`, 6259 ms, `stage2_polish False`. Non-gated rows q03/q15 (`complex=False`, the class the brief said Groq was rescuing) now **also fail**: `groq_fallback_failed: api_status_429` → `stage2_failed_both_providers_deterministic_ship`. So as of this probe, production serves **100% deterministic** answers on all four rows I tested, gated and non-gated alike. That is one step worse than the brief's finding.

---

## What I could NOT determine

- **Whether the R338 09:49 run's 6 discarded rows failed the same way.** Notes are not persisted in that artefact; I have only latency (q15 941 ms, q19 926 ms — implausible for an Opus completion) and today's live reproduction on the same two questions. The other four (q03 10903 ms, q04 7307 ms, q14 3802 ms, q16 3688 ms) are long enough that a completed-then-rejected polish is *not* excluded.
- **Whether the local wrapper / tunnel is healthy right now.** Forbidden to probe. Every Stage-2 conclusion here is about the deployed service plus the two r339 arms, which used `:8110`/`:8111` against whatever the wrapper was doing at 15:55.
- **What `probe_sensitivity_check` would return under a healthy wrapper.** Needs a wrapper-bound run. My C2 correction is proven for the deterministic env and for today's live state, not for all states.
- **Which rejection guard would dominate if the wrapper were healthy** — the report's open question is still open; my measurement only shows that *today* it is not a guard at all.
- Whether the docx "115 paragraphs" figure used a non-empty filter (I measured 245 `<w:p>` elements and did not chase the discrepancy).

---

## Net

The audit's **mechanics section is solid** — every fire rate, line number, hash, gold count, docx quote and legal resolution reproduced exactly, and its dynamic_ab blindness argument is if anything understated. Its **diagnostic section (§1.4 point 1-2) is wrong** in a way that matters: the "6 discarded Opus answers" are 6 failed calls, which changes the bisect target back to R338's original. Its **experiment design has already been executed today and returned an inert result**, for a reason the design did not anticipate and its own fire check would have caught only after both arms were spent. Before any re-run: probe the wrapper for a landing polish, pin the model and `WRAPPER_FORWARD_SYSTEM_PROMPT`, and move the fire check from `stage2_polish` to `stage2_model`-note presence.

==========================================================================================
## agent result #9  (len 19321)
==========================================================================================

Read-only challenge complete. All evidence below was executed this session; nothing was written outside the scratchpad (the one repo artefact, `evals/bench/results/probe-oos-challenge.json`, is gitignored at `.gitignore:40`).

---

# ADVERSARIAL CHALLENGE — "claudemd-truth" audit

Deployed commit moved during this session: the report probed `f7f85ad6f6de`; I probed `1d55a94ac238` (= `origin/main` HEAD). Same `deployment_id 5e013dc2-f67c-4d45-9881-0d8b40cf52ea`.

---

## A. CORRECTED — claims that are wrong *now*

### C1. §2 "WHAT PRODUCTION IS ACTUALLY DOING" is dead. Its named root cause is falsified.

Report: `/healthz/llm` → `llm_ok:false`, `api_status_401`, `cf_access:{client_id_set:false, client_secret_set:false, headers_attached:false}` → "**This is the production outage.**"

Re-measured `13:30:37Z`:
```
{"commit":"1d55a94ac238","provider":"openai_wrapper","llm_ok":true,"detail":"ok",
 "cf_access":{"client_id_set":true,"client_secret_set":true,"headers_attached":true},
 "elapsed_ms":4475,"model":"claude-sonnet-5","prompt_tokens":2,"completion_tokens":1}
```
The CF Access service token **is** set and headers **are** attached. The report's entire root-cause chain (no token → 401 → Groq → 429 → Stage-2 dies) no longer describes the system.

### C2. Production DOES reach Opus for Stage-2 — on complex questions, which is the exact case the orchestrator's "CONCLUSION TO TEST" said always fails.

POST `13:31:02Z → 13:31:24Z` (22 s), *"We deploy an AI system that screens job applicants for a bank in Germany… deployer obligations… financial-services carve-out?"*:
```
stage2_polish: True   cache_hit: False
NOTE: answer_route=synthesis:complex_question
NOTE: stage2_model=claude-opus-5 complex=True
NOTE: noise_suppress_dropped=Article 51
NOTE: vector_recall source=svd added=1
refs: ['Article 26','Article 27']   answer: 1257 chars, 4 sentences
```
**No `groq_*` note at all** — the Claude Max wrapper answered directly. 4 sentences > `MAX_ANSWER_SENTENCES = 3`, so the uncap fired too.

The `13:2x` probe minutes earlier (*"Who counts as a deployer?"*, complex=False) still gave `stage2_polish:false` + `groq_fallback_failed: api_status_429` + `stage2_failed_both_providers_deterministic_ship`.

**Accurate statement: production Stage-2 is INTERMITTENT, not down.** Two POSTs, ~2 minutes apart, same deployment, opposite outcomes. Both the report's §2 and the orchestrator's conclusion generalise from a single sample. The likely mechanism is the wrapper's per-minute rate limit (R282 recorded a 10/min ceiling), not a credential.

### C3. F11 is backwards — `/healthz/llm` lies in exactly the direction CLAUDE.md warned about. **Keep the gotcha.**

The report proposes: *"`/healthz/llm` is authoritative … and its failures are real."* At `13:30:37Z` it returned `llm_ok:true, detail:"ok"` — with `completion_tokens: 1` (and `0` on the probe minutes before, `text:null`). On that same deployment, in the same window, a real Stage-2 call fell to Groq and died. A 2-prompt-token / 0-completion-token round trip declared `ok` is precisely a green health probe over a broken Stage-2 path. **UNSUPPORTED → keep CLAUDE.md's "`/healthz/llm` lies — verify with a real POST" as written.**

### C4. The Stage-2 reachability numbers are wrong, and the causal attribution is wrong. This is the report's most consequential error, because it is the basis of its proposed Validation-policy rule.

Report (inherited verbatim from `docs/R338-…md:35,195`): *"two default-ON skip gates … mean Stage-2 lands on 3 of 20 rows, so it can move at most 15% of the suite."*

Executed the two predicates against the real questions (`evals/regenold/antifragile_groundtruth.py::ANTIFRAGILE_GT`, 20 rows):
```
curated=['q02','q05','q06','q07','q09','q10','q11','q12','q17','q20']  (10)
definitional=['q08']                                                    (1)
Stage-2 REACHABLE: 9/20 = 45%
```
**The two gates account for 11 skips, not 17.** R338's own latency table is consistent with mine (10 rows never called an LLM), which means **~6–7 further rows attempted Stage-2 and lost it for a different reason** — provider failure or a post-hoc guard. R338 named only the gates; the report repeated that attribution without checking it. Turning both gates off would raise reachability to 20/20 but landing to ~13/20 at best.

And there are not two bypass sites — there are **nine**, `app/engines/_graph_rag_impl.py`:
| line | guard |
| --- | --- |
| 8178 | `not _stage2_polish_enabled()` |
| 8182 | `not _stage2_provider_enabled()` |
| 8205 | `_stage2_simple_skip_enabled()` (`REGENOLD_STAGE2_SIMPLE_SKIP`, default **OFF** — executed: `False`, gate at `:1455`) |
| 8230 | `_curated_stage2_skip_enabled()` × `_is_curated_authoritative_intercept` |
| 8249 | `_definitional_stage2_skip_enabled()` × `_detect_pure_definitional_inquiry` |
| **8319** | `stage2_failed_both_providers_deterministic_ship` ← **what production hit on my first probe** |
| 8372, 8398 | drift guard / silent-drop |
| 8434 | verdict-guard fallback to deterministic |

### C5. The proposed rule is right in spirit but wrong about the merge gate. The `dynamic_ab` probe set is NOT blinded.

Executed over `evals.harness.probe_set.load_probe_set()` — the set `dynamic_ab` and `easyhard_ab` both draw from:
```
probe rows: 132
sources: {paper_st_v4:20, paper_tricky_v4:20, paper_mt_v4:12, tricky_v2:31, mt_v2:25,
          lower_risk_v149:12, multiarticle_r268:12}
curated skip fires: 0   definitional skip fires: 0
Stage-2 REACHABLE: 132/132 = 100.0%
```
So the skip gates are an **Antifragile-suite** problem, not a repo-wide instrument problem. Two consequences the report gets wrong by omission: (a) the merge gate is fine; (b) **R282's `easyhard_ab` A/B was not skip-blinded either** — which strengthens §0's evidence, and the report never checked it.

### C6. `app/models.py:49` is the wrong file for the 4,000-char cap.

```
app/integrations/regenold/models.py:49:    content: str = Field(min_length=0, max_length=4_000)
app/models.py:49:                                # (a comment inside the _MAX_QUESTION_CHARS = 64_000 block)
```
Two modules named `models.py`. The report also cites `models.py:247 MAX_ANSWER_SENTENCES = 3`, which is correct — but that one is in `app/integrations/regenold/models.py`, i.e. the report used one bare basename for two different files.

### C7. Two of §5's three reasons for deleting the davidath table do not hold.

* *"cannot be reproduced meaningfully now that the running system differs from the code defaults (F6)"* — **non sequitur.** davidath runs `provider=cli` in-process, locally, entirely off code defaults. Railway service variables cannot touch it. F6 is irrelevant to this argument.
* *"they predate the three ungated R329 default-ON flips, by the file's own ⚠"* — **factually false for the number it objects to.** `git log`: R329 = `01d1215` **2026-08-13**; the R331 re-measurement = `e66577d` **2026-08-14**. The re-measurement postdates the flips. (The *conclusion* survives on the correct reason: `cli` cannot observe three Stage-2 prompt flags, so the reproduction carried no information — the instrument trap, not chronology.)

The deletion recommendation may still be right; two of its three legs are not.

### C8. Minor citation errors (each one I re-ran)

| report says | actual |
| --- | --- |
| `tests/test_r115_followups.py::test_stub_names_433_and_mdr_route` | node id needs the class: `::TestR115Art43IntegratedProcedure::test_stub_names_433_and_mdr_route` — the report's id errors with `ERROR: not found`, so it was not executed as printed |
| `REGENOLD_BEDROCK_STAGE1_MODEL / _STAGE2_MODEL (_graph_rag_impl.py:567,569)` | reversed — `:567` is `_STAGE2_MODEL`, `:569` is `_STAGE1_MODEL` |
| `REGENOLD_CURATED_STAGE2_SKIP … fires :8222` | gate at `:8230`; comment at `:8215` |
| `graph_rag_prompts.py:842` | the comment runs `:836-845`; `:842` is *"So ANSWER_GENERATE_SYSTEM above reaches the model on ZERO live requests."* — content correct, line off by one |

---

## B. §0 — the "finding that should stop the round". CONFIRMED as a document, WEAKENED as a decision.

The A/B exists. `.planning/R282-CHECKPOINT.md:69-95` carries the table verbatim (kw_recall 0.8750→0.6083, ref_strict 0.6455→0.4901, pred:gold 1.83→2.50), the pairwise sweep (8/8, p≈0.008), and the literal verdict *"Decision: keep OFF — do NOT activate."* It is corroborated across the tree: `docs/ROUNDS.md:10809`, `.planning/R283-CHECKPOINT.md:105,149`, `R284:73`, `R299-PLAN.md:99,272`, `R304-PLAN:113`, plus live comments at `app/data/graph_rag_prompts.py:843`, `:964`, `app/engines/_graph_rag_impl.py:7790-7792`. CLAUDE.md genuinely omits all of it. **That part stands.**

Four things the report asserted or skipped that I measured:

**1. The size argument holds — and I checked it at both dates.** Executed: `len(ANSWER_GENERATE_SYSTEM)` = **51,516** at HEAD; **51,110** at `8ff406e` (2026-07-17, the last prompt commit before R282). Line-level diff: **122 → 122 lines, similarity 0.9918, 1 line added / 1 removed** (rule 12b CLOSED-SET COMPLETENESS reworded). So the system prompt R282 rejected is, to within one line, the system prompt on disk today.

**2. But the ON arm today is NOT the ON arm R282 measured — the *other* channel changed underneath it.** AST-extracted top-level string constants:
```
R282 (8ff406e): ANSWER_GENERATE_SYSTEM 51110, MINIMAL_COMPOSER_SYSTEM 3181, QUERY_PARSE_SYSTEM 3186, _REF_MINIMALITY_RULE 1070
HEAD (f7f85ad): … + USER_ANSWER_COVERAGE_CLAUSE 2241, USER_CHALLENGE_BREVITY_CLAUSE 546,
                    USER_REF_MINIMALITY_CLAUSE 701, USER_SUBPARAGRAPH_ATTRIBUTION_CLAUSE 469
```
**3,957 chars of user-channel instruction exist today that existed in neither R282 arm** (added by R298 `3b2d37d` 2026-07-26, R310, R318.1 — all *after* R282 on 2026-07-19). R282's diagnosed failure mode was drift + over-citation (`pred:gold 1.83→2.50`); `USER_REF_MINIMALITY_CLAUSE` and `USER_ANSWER_COVERAGE_CLAUSE` are the counters later built for exactly that. R282 is a **strong prior on a materially different configuration**, not a settled result. The report's "it owes a *re-run*, not an A/B" is the right verb for the wrong reason — it owes a re-run because the treatment changed, not merely because time passed.

**3. The evidence is unreproducible.** `easyhard-t1-sysprompt-{off,on}.json` are **not in the tree** (`find . -name "easyhard-t1-sysprompt*"` → nothing; `evals/bench/results/` has no `sysprompt` entry). §0 rests on a hand-written markdown table in a repo whose signature failure is instruments that print confident tables. Worth stating in the same breath as the p-value.

**4. Unexamined confound the report should have flagged: the branch arm was 4× FASTER.** R282's own table: latency p50 **22.1 s OFF → 5.4 s ON**, "31/40 rows <8s". CLAUDE.md's cheapest inert-A/B detector is *"CHECK THE BRANCH ARM'S LATENCY"*. Here the arms did diverge, so it is not inert — but a 4× speedup on a **larger** payload, across **two separate wrapper processes on two ports**, is unexplained, and the model each instance served is nowhere recorded. Given the operator has since moved to `claude-opus-4-8`, "which model produced these numbers" is unanswerable from the artefacts.

**5. Configuration attack (#3), the decisive one: the flip is currently INERT for production.** Production resolves `openai_wrapper` and, when the wrapper 429s, ships deterministic — and when Stage-2 *is* skipped, no prompt of either slot reaches any model. On my first probe production received **neither** channel. So §0's framing ("the finding that should stop the round") overstates urgency for the deployment and understates it for local evals, which is where the flip actually bites.

---

## C. CONFIRMED — reproduced with my own execution

| # | claim | my evidence |
| --- | --- | --- |
| F1 | `KB_VERSION = 2024.1689.v21` (`app/data/kb.py:33`), stale v18 pin fails | executed: `KB_VERSION: 2024.1689.v21`; `tests/test_r115_followups.py:217: assert KB_VERSION == "2024.1689.v18"` → `1 failed` |
| F2 | xrefs 149 core / **248** full (CLAUDE.md says 249) | `_build_xref_graph_core()` summed = **149**; `_build_xref_graph()` summed = **248**; `all_edges()` = **248** |
| F4 | runner is 255, not 276 | `OVERALL: 255/255 passed (100.0%)`, `RISK_F1 … macro=1.00` |
| F5 | "all 56 are the Stage-2 artefact" is false | **stronger than the report proved it**: with `REGENOLD_EXTERNAL_EMBEDDINGS=0` → 4 failed; **removing that one var → `34 passed`**. Causation demonstrated, not asserted |
| F6 | prod runs `REGENOLD_GRAPH_VECTOR_RECALL=1` against a code default of OFF | `vector_recall source=svd added=2` and `added=1` on **both** live probes; gate `app/engines/vector_recall.py:68` requires the var `== "1"` |
| F8 | Cappelli revert landed | `graph_rag_prompts.py:899` = `# R338 — REVERTED cc47f8b's two topic-specific sentences.`; `:118` still carries the Annex IV(1)(e)/(2)(c) rule |
| F9 | Groq is a 5th path absent from the provider table | `/healthz "is_groq_enabled":true`; `_graph_rag_impl.py:877-880` fires on any wrapper failure; live note `groq_fallback_failed: api_status_429 … openai/gpt-oss-120b` |
| — | `graph_semantic.py:549` sub-clamp | `_int_env("REGENOLD_KG_MAX_REFS", 8, 1, 10)` vs `kg_context.py:642/666/685/707` `_DEFAULT_MAX_REFS=12, ceiling 24`. **Report is right and CLAUDE.md's "four call sites" is wrong — it is one, at `graph_semantic.py:549`** |
| — | `provision_exists` head-laxity | all five fabricated leaves `exists=True, text=None`; `evals/judge/legal_v2.py:660: if not provision_exists(ref)` still the gate |
| — | OOS | `probe_oos.summary.n=51, pass=49`, `leak=0` every suite, 2 `adjacent_eu` wrong (DMA `hoos_adjacent_01`, PLD `hoos_adjacent_03`) |
| — | BM25 | `avg_doc_len 91.69` default / **94.47** at `REGENOLD_ONTOLOGY_RISK_DOCS=0` — matches to the hundredth |
| — | prompt sizes | `USER_ANSWER_COVERAGE_CLAUSE` = **2,241**; `EC_CHECKER_OBLIGATION_MAP` = **131** |
| — | line citations | 27 of 29 spot-checked `file:line` land within ±2 of the named symbol (exceptions in C6/C8) |

### Legal claims — every one resolved through `get_provision_text`
```
Annex IV                5710 chars | 'ce mark' present: False
Annex IV.1.e            73 chars   Annex IV.2.c   237 chars
Article 113             2026: True   2027: True
ARTICLE_EXISTENCE 126 = 113 articles + 13 annexes | lettered entries: []
definitions 68 | 3(14a): absent
Charter Art. 1 / 21 / 47 all present in ARTICLE_EXISTENCE  (lint floor blind — reproduces)
```
Also verified the **live** answer's one contestable legal statement: the production answer says the bank must do an Article 27 FRIA *"if it is a body governed by public law or a private entity providing public services."* Against the pin, `get_provision_text("Article 27.1")` reads *"deployers that are bodies governed by public law, or are private entities providing public services, and deployers … referred to in points 5 (b) and (c) of Annex III"* — and the scenario is Annex III **point 4** (employment). The conditional is **correct**, and an unconditional Art. 27 assertion would have been wrong. No legal error.

---

## D. UNSUPPORTED — drop or restate

1. **"Article 51 has 10^25, not 10^23"** (§3). Not verifiable as written and it hides a defect. `'10^25' in get_provision_text("Article 51")` → **False**. The pinned verbatim text reads: *"…measured in floating point operations is greater than **1025**."* (codepoints `0x31 0x30 0x32 0x35`). The exponent is flattened to ASCII. `'10^23' in …` → also False. **New finding the report missed:** the KB stubs carry it correctly (`Art. 51`, `Art. 53`, `Art. 56` all contain `10^25`), but `REGENOLD_GROUNDING_TEXT` (default ON) injects the **verbatim** text — so Stage-2's grounding block states the GPAI systemic-risk threshold as "greater than 1025 FLOP". Restate the claim as: *"Article 51(2) sets the threshold at 10²⁵; the pinned verbatim text flattens it to `1025` and that is what reaches Stage-2."*
2. **F11's rewrite** — see C3. Falsified within the hour.
3. **§2's causal chain and §5's "at most 15%"** — see C1, C4.
4. **Two of §5's three deletion arguments** — see C7.

---

## E. NEW — defects neither CLAUDE.md nor the report records

1. **The trace records the Groq outcome but never the wrapper failure that triggered it.** `grep -n record_note app/engines/_graph_rag_impl.py` in 820–1000 yields exactly `:937 groq_auto_fallback_success`, `:949 groq_fallback_failed`, `:956 groq_fallback_exception`. The wrapper's own error is `logger.warning` only (`:866-869`, `:880`). Nothing in the eval pipeline reads logs. **You cannot tell from a reasoning trace why the wrapper failed** — the exact gap R328's "a silent model swap is a MEASUREMENT bug" section exists to close, still open on the wrapper branch.
2. **`app/routes/regenold.py:9873` — stale comment contradicting live behaviour:** `# exempt (R274). Default OFF (REGENOLD_ADAPTIVE_REF_CLAMP) so prod stays…` while `:4549` reads `os.getenv("REGENOLD_ADAPTIVE_REF_CLAMP", "1")`, i.e. **default ON**. The report flagged this flag as undocumented; it did not notice the in-tree comment asserts the opposite of the code.
3. **`app/engines/kg_context.py:645-651` — stale comment:** *"The DEFAULT is deliberately unchanged at 24"* against `:103 _DEFAULT_MAX_UNITS = 70`. And `:652` clamps to `(1, 70)` — **default equals ceiling**, so `REGENOLD_KG_MAX_UNITS` cannot be raised at all. That is CLAUDE.md's "a clamp at its own default" hazard, in the upward direction.
4. **The `deployer` probe answer does not answer the question.** *"Who counts as a deployer under the AI Act?"* returned Article 26(5)/(6) carve-outs and Article 99 penalty ceilings — 847 chars, 3 sentences (the re-armed cap), 7 references, zero definitional content, while `Art. 3(4)` defines "deployer". Worth a row in any Stage-2-outage assessment: the deterministic fallback is not merely terser, it is off-question here.

---

## F. What I could NOT determine

* **Which Railway service variables are set.** No CLI auth; `/openapi.json` exposes no config route. `REGENOLD_GRAPH_VECTOR_RECALL=1` is inferred from a trace note unreachable when the gate is off (solid); the CF Access variables are inferred from `/healthz/llm` booleans (solid). Everything else in the env table could be overridden invisibly. Same gap the report declared.
* **Why the wrapper failed on probe 1 and succeeded on probe 2.** No trace note exists (see E1). Rate limit is the hypothesis, not the measurement.
* **The live Aura census.** `/healthz/graph` still `graph_ok:false, "ping returned no rows"`, `seed_version:""`, `kb_version:"2024.1689.v21"` (code fallback), empty counts. Cannot confirm 1758/1979 or 1786/2076. The report's F3 stands unresolved.
* **Which model served either R282 arm.** Sidecars absent from the tree; the checkpoint does not name it.
* **Whether the R338 answer regression is the system-prompt flip.** Unchanged from the report — but note my C4/C5 result narrows it: the Antifragile suite is 45% Stage-2-reachable, not 15%, so a re-run there is less blind than the report claims, though still the wrong instrument versus the 132-row probe set at 100%.
* **The full 56-failure pytest set.** I ran only the four named tests plus targeted modules, not the 333 s suite. The count is the report's, not mine; the three named causes are mine and reproduce.

==========================================================================================
## agent result #10  (len 16159)
==========================================================================================

# ADVERSARIAL CHALLENGE — "overcite-regression" audit

Deployed `/healthz` re-probed this session: `{"status":"ok","commit":"1d55a94ac238","is_groq_enabled":true}` = local `HEAD` `1d55a94`. Offline env: `.env` loaded with all LLM keys **blocked**, `P2P_GRAPH_RAG_PROVIDER=cli`, `OPENAI_API_BASE=http://127.0.0.1:1/v1`, `REGENOLD_GRAPH_BACKEND=neo4j`, `py -3.12`, FastAPI `TestClient`. Two live read-only probes of the Railway endpoint. **No wrapper/tunnel calls.** No repo file modified.

---

## CONFIRMED (reproduced by execution)

**C1 — B1's Stage-2 table is exact.** Parsed both artefacts:
```
id  | R318 s2 model          lat   route                      | R338 s2 model          lat   route
q03 | True  claude-opus-5   22597 synthesis:synthesis_default | False claude-opus-4-8 10903 synthesis:synthesis_default
q04 | True  claude-opus-5   16946 synthesis:synthesis_default | False claude-opus-4-8  7307 synthesis:synthesis_default
q14 | True  claude-opus-5   21603 synthesis:complex_question  | False claude-opus-4-8  3802 synthesis:complex_question
stage2_polish TRUE  R318= 9  R338= 3      identical answer_route rows: 20 / 20
```
`record_note(f"answer_route=synthesis:...")` is at `_graph_rag_impl.py:8265`, after all three skip exits (`:8205`, `:8230`, `:8249`). Verified by reading `:8190-8270`. The R338 report's §1 gate explanation genuinely does not apply to q03/q04/q14.

**C2 — B2 is CONFIRMED and *stronger* than claimed.** All three rows, `provider=cli`, byte-identical to what R338 shipped — including q04, which the report hedged as only "near-identical":
```
q03 refs identical, answers byte-identical: True (140c / 140c)
q04 refs identical, answers byte-identical: True (734c / 734c)
q14 refs identical, answers byte-identical: True (765c / 765c)
```
q03's 140 chars == `get_provision_text("Article 6.2")` verbatim. All four "missing" phrases: **0 hits** in `app/`.

**C3 — every B3 documentary claim.** `.planning/R282-CHECKPOINT.md:58-104` carries the exact table (kw_recall 0.8750→0.6083, ref_loose 0.8542→0.7500, ref_strict 0.6455→0.4901, ref_conc 0.5391→0.3876, pred:gold 1.83→2.50, p50 22.1s→5.4s) and the verdict "**Decision: keep OFF — do NOT activate.**" `docs/ROUNDS.md:10809` carries the standing prohibition verbatim. `grep -c R282 CLAUDE.md` = **0**. `CLAUDE.md:601-608` frames the flag as merely owing an A/B. The A/B exists and rejected the flip.

**C4 — B4's instrument gap.** `evals/regenold/antifragile_live.py:135-159` `_parse_reasoning` keeps 7 scalars and discards `notes`. Confirmed by reading.

**C5 — every A1 number.** Exact reproduction: histogram `{-2:2,-1:3,0:14,1:3,2:12,3:3,4:1,5:2}`, mean delta **+1.0750**, rank wrong-rates `1:0.20 2:0.60 3:0.60 4:0.79 5+:1.00`, most-added `Article 6 ×6, 9 ×5, 50 ×4, Annex I ×4, Annex III ×4`, latency bands `<1500ms +0.88 / ≥1500ms +1.38`. Hop-target enrichment: **27/62 = 43.5%** of non-gold instances in a 13-ref set that is 13/126 = **10.3%** of the surface.

**C6 — A2's gt_06 trace, offline AND live.** Instrumented trace reproduces the report exactly, and the **deployed** service returns the same thing:
```
offline: _surface_anchor_citations IN ['Article 5','Article 6','Article 50'] OUT (same)
         _collapse_parent_refs no-op ×2 ; _add_prose_named_refs NEVER CALLED
         FINAL ['Article 5','Article 6','Article 50']  notes ['curated_ref_protect: prune skipped']
LIVE (1d55a94): refs ['Article 5','Article 6','Article 50'] stage2_polish False
                notes ['stage2_skipped_curated_authoritative','curated_ref_protect: prune skipped']
```
Code sites verified: literal `"refs": ["Art. 5", "Art. 6", "Art. 50"]` at `_graph_rag_impl.py:4768`, intercept `:4755-4771`; gt_07's `["Art. 1","Art. 4"]` at `:4741`. `regenold.py:8645` `if not references:` → `regenold.py:8707` `answer_text = _fb_prose` — prose **is** replaced.

**C7 — A3's ng_10 mechanism, byte-for-byte.** Instrumented `_apply_ontology_hops`:
```
IN : ['Article 10','Article 55','Article 9','Article 52','Article 13','Article 93','Article 27',
      'Article 57','Article 53','Article 56','Article 90','Article 26','Article 50','Article 94']   (14)
OUT: ... + ['Article 15','Article 11','Article 14','Article 6']                                      (18)
FINAL: ['Article 10','Article 55','Article 9','Article 52','Article 13','Article 93','Article 27']
```
Article 15 (gold) injected, never shipped. Code sites all correct: `regenold.py:372` def, `:388` `is_medical`, `:415` trigger, `:442` `return list(candidates) + injected`, `:8564` bump `max(eff, min(7, eff+injected))`, `:8584` `candidates[:_effective_max_refs]`, `:8595` R115 sub-point-only rescue.

**C8 — A3's A/B result, once decontaminated (see X6).** Paced 40-row run, both arms 0 HTTP errors:
```
FIRE CHECK rows changed = 12/40
GOLD DROPPED = 5  {gt_13:[Annex I, Article 5, Article 6], med_9:[Annex I], ng_04:[Article 13]}
WRONG REMOVED = 26
HOP ON : ref_loose 1.0000 / recall 0.8697 / precision 0.5868 (n=38)
HOP OFF: ref_loose 1.0000 / recall 0.8316 / precision 0.6439
```
Report: 11/40, 23 removed, gold 5 with the identical attribution, precision +0.050 / recall −0.038. **Hard rule #8 verdict — blanket `REGENOLD_ONTOLOGY_HOP=0` is a REJECTION — stands.**

**C9 — legal characterisations, against `get_provision_text`.** `Article 6.2` 140c (verbatim as quoted); `Article 52` 2960c = GPAI systemic-risk **notification** to the Commission under Art 51(1)(a); `Article 93` 913c = "the Commission may request providers to…"; `Article 27` 2837c = FRIA, and `'serious incident'` / `'bias'` / `'discriminat'` each **0** occurrences.

---

## CORRECTED

**X1 — A2 is structurally incapable of moving the axes it targets. This is the headline.**
`evals/regenold/run_graphrag_benchmark.py:154`:
```python
scored = [r for r in gt_rows if not r["recital_only"] and r["error"] is None]
```
`gt_06` and `gt_07` are the only two `recital_only` rows. The artefact records it in its own summary: `"n": 40, "n_scored_refs": 38, "n_recital_only_excluded": 2`. **Fixing gt_06's three refs changes `ref_loose` / `ref_strict` / `ref_conciseness` by exactly 0.0000 on this benchmark.** A2 proposes a two-site behaviour change (`_graph_rag_impl.py:4768` + a new escape at `regenold.py:8645`) whose measured payoff on the instrument it cites is zero — the repo's signature failure mode. This also invalidates the R338 report's ranked item #4 ("gt_06 … the cleanest available handle on Ref Strict / Ref Conciseness").
Secondary: gt_06's gold is **not** "correctly cites nothing". The scenario carries `paper_refs: "Recitals: 53"` and `recital_only: True` — the gold is a recital, deliberately excluded because the wire emits Articles/Annexes only. "A minimal-risk question whose gold is the empty set draws three citations" is a misreading of an exclusion flag.

**X2 — Sub-fix #2's premise is false; the injections *do* survive, and they carry gold.** Instrumented `gt_13`:
```
_apply_ontology_hops IN : ['Annex III']
                     OUT: ['Annex III','Article 6','Article 5','Annex I']
FINAL refs: ['Annex III','Article 6','Article 5','Annex I']
gold:       ['Article 5','Article 6','Annex I','Annex III']    -> 4/4
```
All three injections ship and all three are gold. So of the 5 gold coordinates `HOP=0` loses, **3 come from surviving injections** (gt_13) and 2 from the budget bump admitting existing candidates (`med_9` — traced: the injection there is `Article 5`, which does **not** ship; the gold `Annex I` was candidate #4). "The bump exists only to make room for injections that currently never survive" is refuted on both halves. I did **not** instrument `_effective_max_refs`, so whether removing the bump specifically costs gt_13 gold depends on its base budget — honest gap — but the stated rationale is dead either way.

**X3 — Sub-fix #1 is a 4× overstatement.** Simulated the report's own proposal on the measured ng_10 candidate list at the observed budget of 7:
```
CURRENT (tail append) : ['Article 10','Article 55','Article 9','Article 52','Article 13','Article 93','Article 27']
                        gold=1  wrong=6
SUB-FIX #1 (inline)   : ['Article 10','Article 15','Article 55','Article 9','Article 11','Article 14','Article 52']
                        gold=2  wrong=5
```
It converts **1** wrong ref into 1 gold, not "4 wrong refs into 1 gold".

**X4 — "attenuated exactly as expected" is false, and three axes were omitted.** Ratio of the observed R318→R338 delta to R282's delta, against the 9/20 ≈ 0.45 the report predicts:
```
axis          R282 d    R338 d   ratio
kw_recall    -0.2667   -0.0669    0.25
ref_loose    -0.1042   -0.0125    0.12
ref_strict   -0.1554   -0.0368    0.24
ref_conc     -0.1515   -0.1023    0.68
pred:gold    +0.6700   +0.0900    0.13
```
A **5.7× spread**, and the rank order inverts: R282's largest hit was `kw_recall`; R338's is `ref_conc`. Four numbers sharing a sign is not a fingerprint. Omitted from the comparison: `ans_conciseness` **+0.1025**, `ref_subpoint_loose` **+0.1375**, `ref_subpoint_strict` **+0.0878** — all positive.

**X5 — B1's "generated and then thrown away" is wrong for one of the four sites.** `:8301` is `if enhanced is None:` → `:8315` `stage2_failed_both_providers_deterministic_ship` → `:8319`. That is *both providers failed*; nothing was generated. And `stage2_model=` is recorded at `_graph_rag_impl.py:780`, **before** the HTTP call — so its presence proves the code reached the call site, not that a call completed. q15 (941 ms) and q19 (926 ms) carry `stage2_model=claude-opus-4-8` and cannot have made an Opus round-trip.

**X6 — A3 is rate-limit-fragile and the report states no per-arm error count.** My first two attempts at the identical measurement silently 429'd 10 of 40 rows (`regenold.py:2184`, 30/minute anon tier) and produced a *different verdict from the same code*: fire check 8/40, **GOLD DROPPED = 2**, gt_13 never diverging. Only after pacing did I get 12/40 and gold 5. The report's own caveat ("two identical HOP=1 passes disagreed on med_5") is the same symptom described as inherent noise; my two unpaced HOP=1 passes were byte-identical, so it is contamination, not noise. **Any A3 rerun must assert 0 non-200 per arm.** (Likely co-cause: `load_dotenv()` resolves to the *calling script's* directory — my first `.env` attempt from the scratchpad silently produced `backend=None`, exactly CLAUDE.md's documented gotcha.)

**X7 — "the 8 mismatches are exactly the Stage-2 rows" is unfalsifiable from that artefact.** `reasoning` is `""` on **all 40 rows** (verified). Which rows ran Stage-2 is unknowable there — the report says so in "What I could NOT determine", then asserts it in A3. My paced run matched live on **33/40** with mismatch set `{gt_04, med_01, med_1, med_2, med_3, med_4, med_7}` — 7 rows, not the 8 named.

**X8 — A1 arithmetic.** "26/40 rows over-cite or match" → measured **21 over-cite, 14 match, 5 under-cite**. Excluding the two unscored recital-only rows: 19 / 14 / 5, mean delta **+1.000**, rank-1 wrong-rate 0.16.

**X9 — "the 4 slots are filled by BM25 tail junk" — outcome right, causal wording wrong.** The trace shows Article 52/13/93/27 were already candidates **4-7 before the hop ran**. The bump widens the head slice; it does not free slots that junk then fills.

---

## UNSUPPORTED (drop, or re-derive)

**U1 — B3's causal attribution to `WRAPPER_FORWARD_SYSTEM_PROMPT=1`. There is a competing hypothesis the report never raises, and the artefact cannot exclude it: the Groq fallback.**

- `is_groq_provider_enabled()` is `bool(os.getenv("GROQ_API_KEY",""))` — `openai_wrapper_provider.py:761-766`. `GROQ_API_KEY` **is present in `.env`**, and deployed `/healthz` reports `"is_groq_enabled":true`.
- The Groq success path records **only** `groq_auto_fallback_success` (`_graph_rag_impl.py:936-937`). It emits **no** `stage2_model=` note.
- It returns from the **same function** that already recorded `stage2_model=claude-opus-4-8` at `:780` — `_openai_wrapper_complete_for_graph_rag`, lines 683-1042 (confirmed by AST).
- `_parse_reasoning` discards `notes` (C4).

⇒ **A Groq-gpt-oss-120b-served polish is byte-indistinguishable from an Opus-4.8-served polish in `live_r338-opus48.json`.** It would appear as `stage2_polish=True, stage2_model=claude-opus-4-8`.

Corroborating: R338's three *landed* rows ran **3.5 s / 5.3 s / 6.1 s** (q13/q01/q18) against R318's **15.6 / 27.9 / 21.0 s** on the same rows — below CLAUDE.md's measured Claude-Max floor of 12-17 s for a *5-token* request. And `stage2_polish=False` via `:8319` means wrapper **and** Groq both failed — precisely the pattern the operator measured on production this session. So R338's 6 lost landings + 3 fast landings are fully consistent with wrapper degradation + partial Groq rescue, with no reference to the system-prompt flip. The report's proposed decisive probe (`WRAPPER_FORWARD_SYSTEM_PROMPT=0`, model held fixed) **cannot separate these two either** unless it also persists `notes` and records which provider served each row. Settling it requires a wrapper call — barred this session.

**U2 — "Article 52, 93, 27, all verified irrelevant against the pin via `get_provision_text`."** `get_provision_text` establishes what a provision *is*, not that it is irrelevant to a question. Art 27 carries `fundamental rights` ×3 and `risks of harm` ×1 (0 for bias/discrimination) — the irrelevance call is a defensible judgement, but it is a judgement, and CLAUDE.md's own memory records LLM-judged `legal_errors` at ~77% false-positive. Downgrade to "characterisation verified; relevance asserted".

**U3 — A3's generalisation to the live system, on the one row it rests on.** Live probe of ng_10 against deployed `1d55a94`, today:
```
refs: ['Article 10','Article 55.1.a','Article 55.1.b','Article 9.1','Article 56']
stage2_polish: True   notes: [vector_recall source=svd added=1, answer_route=synthesis:synthesis_default,
  semantic_contract: chain_completeness, stage2_model=claude-opus-5 complex=False,
  noise_suppress_dropped=Article 51, ref_granularity_auto]   (20.2 s)
```
Neither the artefact's 7-ref list nor my offline sim describes what ng_10 ships live. Article 52/93/27 — the "tail junk" the whole sub-fix argument targets — **do not appear**. The A3 mechanism is real in the deterministic layer; its scoring consequences on the live product are unmeasured.

---

## Re-measured CLAUDE.md / orchestrator claims

| claim | status |
| --- | --- |
| deployed `commit` = local HEAD | **TRUE** — `1d55a94ac238` |
| "production never reaches Claude/Opus for Stage-2 at all" (orchestrator's stated hypothesis) | **FALSE as stated.** My complex=False probe: `stage2_model=claude-opus-5`, `stage2_polish True`, **no groq note**, 20.2 s — it reached Claude. It is intermittent, not absolute. |
| deployed Stage-2 model | `claude-opus-5` today — **not** the `claude-opus-4-8` of the R338 local run. Two different systems. |
| `railway.toml [deploy.envs]` inert / `is_groq_enabled` | `/healthz` exposes `"is_groq_enabled":true` on the live service |
| `load_dotenv()` resolves to the calling script's dir | **TRUE, reproduced** — cost me one silently-wrong arm |

---

## What I could NOT determine

- **Whether the system-prompt flip or a Groq/wrapper failure caused R338's lost landings.** Barred from wrapper calls; the artefact cannot answer it (U1). This is the single highest-value fix: persist `notes` verbatim **and** record the *serving* provider, not just the requested model.
- **gt_13's base `_effective_max_refs`**, so I cannot say whether sub-fix #2 alone would drop its 3 gold — only that #2's stated rationale is false.
- **Whether R282's own ON arm was itself Groq/wrapper-degraded.** Its p50 of 5.4 s is below the documented Claude-Max floor, the same anomaly I flag against R338. R282 is being used as the load-bearing evidence and it was measured on a different wrapper build and a different model tier.
- **Live Stage-2 rate on the GraphRAG benchmark** — `reasoning` is `""` on all 40 rows.

Scratch files (safe to delete): `…/scratchpad/{chk_a1,hop_run,hop_run3,hop_cmp,hop_cmp2,b2,trace}.py`, `{chk_hop0,chk_hop1,chk_hop1b,dot_hop0,dot_hop1,pace_hop0,pace_hop1,live_ng10,live_gt06}.json`.