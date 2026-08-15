# Next session — start here

Self-contained handoff. Written 2026-08-15 at the **R350** line. Assumes no memory
of the sessions that produced it. Read [`CLAUDE.md`](../CLAUDE.md) first — it is the
load-bearing context and is current as of this commit.

---

## 0. Which repo you are in

`antifragileai-regenold-evaluation` — the **re-evaluation surface**. The sibling
`regenold-eu-ai-act-rag` deploys to production. Round numbers COLLIDE between the
two; prefix any shared reference with the repo name. Sync by **cherry-pick** —
`git merge parent/main` silently DELETES files that exist only here.

⚠ **Never let this repo write to the shared Aura instance.** Pin
`NEO4J_AUTO_SEED=0` (default).

⚠ **A merge to `main` here SHIPS** to
`antifragileai-regenold-evaluation-production.up.railway.app`. Read
`/healthz.commit` before believing a merge went live — Railway's auto-deploy lags.

## 1. What merged since the R346.2 handoff

| PR | What |
| --- | --- |
| #33 | R346.2 docs |
| #34 | **R347** — hybrid-RAG KG supplementation for the Cohere rerank pool |
| #35 | **R348** — semantic edge reasons + 2-hop depth in the KG rerank pool |
| #36 | **R349** — legal_v2 judge axes join every `dynamic_ab` run (ans + ref correctness) |

Then **R350** (this session): a six-specialist code review of R341→R349, a skeptical
verifier pass, and the fixes. Evidence:
[`docs/reviews/r350-multi-agent-review-2026-08-15.md`](../docs/reviews/r350-multi-agent-review-2026-08-15.md).

## 2. What R350 changed, and why it matters before a graded run

**Nothing was broken in the shipped default configuration** — every rerank and
expansion lever is default-OFF. But the *merge gate itself* was defective on its
default path, and the levers about to be A/B'd would have produced confident wrong
answers. Four things to know:

1. **The merge gate crashed before printing its own hard-rule-#8 veto.** A U+2500 box
   character in R349's judge line is unencodable in cp1252 (this platform's
   `sys.stdout.encoding`), and it sat between the axis table and the `gold_dropped`
   block — with `_write_sidecar` called *after* `_report`. A multi-hour live A/B lost
   both its verdict and its data. **Any A/B you ran between R349 and R350 with judge
   axes on lost its sidecar; re-run it.**
2. **The judge silently turned `fail` into `pass`** on `citation_faithfulness` and
   `reference_correctness` when a reply omitted its own array. That is the **shipped
   grading path with no flag** — so reference-correctness and citation-faithfulness
   numbers from before R350 are biased upward by an unknown amount. Treat pre-R350
   judge numbers on those two axes as suspect.
3. **`REGENOLD_RERANK_KG_CANDIDATES` put graph-sourced provisions on the wire.**
   Measured: a chatbot question gained `Art. 98` (comitology); a FRIA row went 3 refs →
   11. Now ordering-only.
4. **`REGENOLD_RERANK_KG_HOPS` was inert** and would have reported a clean delta for a
   depth change that never happened, because the flag *was* cache-keyed so the fire
   check passed on Stage-2 noise. Now live.

## 3. Ranked next steps

1. **Re-run the three R346 live A/Bs.** Their sidecars were written by the pre-R350
   gate: the judge axes could score a timeout as a loss, `fire_check` could count a
   transport error as the lever firing, and any run whose report crashed left no file
   at all. The levers are unchanged; the instrument is not.
2. **Resolve the query-expansion A/B on the frontier paraphrase tier.** Directionally
   the strongest arm (ref_loose +0.039, kw_recall +0.029, gold 17→14 — branch BETTER,
   flat latency) but UNDERPOWERED at n=60, and the measured run used the retired Haiku
   tier. Note R350 raised the wrapper paraphrase budget from a hard-coded 2.0 s to 20 s
   — on the wrapper's measured 12–17 s floor the old budget would have failed every
   call and read as INERT. The gold veto is the gate.
3. **A/B the rerank KG pool now that both defects are fixed** — `REGENOLD_COHERE_RERANK`
   × `REGENOLD_RERANK_KG_CANDIDATES` × `REGENOLD_RERANK_KG_HOPS`. Pace it:
   `--min-call-gap 6.5` on a Trial key, and note the fan-out is **up to 5 serial Cohere
   calls per request** (measured), so that gap is ~5× optimistic. Unpaced = false INERT.
4. **Run `--mode hard`.** The graded turn (adversarial pushback, 67/111 rows). Still
   never run. Every decision so far is on the *easy* turn — that is the instrument trap.
5. **Record the PRIMARY provider's failure in the reasoning trace**
   (`_graph_rag_impl.py` ~:880). Only the fallback's outcome is written, which is what
   turned R339's outage into a multi-hour diagnosis. Cheapest high-value change left.
6. **Bound the Cohere fan-out** (see §2 / the review's Suggestions). Needs a
   request-scoped call budget; deliberately not attempted untested in R350.
7. **Gate the parent-collapse** with `easyhard_ab` — +0.018 F1 offline, one gold ref is
   the price.
8. **Attack GENERATION, not selection** — the ~90% over-citation gap is upstream of the
   ranker (wrong ref 53% of the time at rank 3).
9. **`CROSS_REFERENCES` backlinks (248 edges) as non-citable context** — best unshipped
   graph idea. Note: **248**, not 249; CLAUDE.md said both.
10. **Finish the judge audit.** R350 fixed the missing-array guard, but the
    `GROUNDED_JUDGE_STRICT_GROUNDING` bypass and the head-lax `provision_exists`
    ghost-citation gate at `legal_v2.py:660` are still open.
11. **Gate `REGENOLD_ONTOLOGY_RISK_DOCS`** — default-ON, live-shipping, 9/110 measured
    context regressions, no verdict. Do NOT just flip the default off.

## 4. Environment for a live Bedrock A/B

`evals/harness/` does **not** load dotenv. Force:

```
P2P_GRAPH_RAG_PROVIDER=bedrock
REGENOLD_BEDROCK_WRAPPER_FALLBACK=0      # a dead key must not hop to the tunnel
REGENOLD_GRAPH_BACKEND=embedded          # deterministic local graph, both arms equal
REGENOLD_EXTERNAL_EMBEDDINGS=0           # COHERE_API_KEY would switch the dense lane
REGENOLD_BEDROCK_MODEL=claude-opus-4-6   # + _STAGE2_ / _COMPLEX_ / _STAGE1_
```

```bash
py -3.12 -m evals.harness.dynamic_ab --flag REGENOLD_QUERY_EXPANSION --label x --max-rows 137
```

⚠ **New in R350:** `--endpoint` now actually works and implies `--no-local`; the run
prints which system is under test. Before R350 `--local` was `store_true, default=True`,
so `--endpoint` was silently ignored and you measured your working tree.

**Verify the key first**: `check_connectivity_and_permissions('claude-opus-4-6')` must
say `status: ok` — ABSK keys expire after 30 days.

## 5. Gotchas that cost a session

* **ABSK Bedrock keys: 30-day life, shown ONCE.** Expiry looks like
  `Authentication failed` on EVERY model. Re-mint in the AWS console; picked up per
  call, no restart.
* **Cohere Trial key (10 calls/min): unpaced rerank A/B = false INERT.**
* **cp1252 is the console encoding.** An unencodable character in an output line is an
  exception, not a rendering artefact. `—` (U+2014) is fine, `─` (U+2500) is fatal.
* **Keyed-but-frozen is worse than unkeyed.** A flag in `_engine_cache_key` but read at
  import makes the fire check PASS on noise. Two shipped that way; both fixed R350.

## 6. Closed — do not re-open

* **V1-vs-V2 prompt**: V1 REJECTED by the gold veto (live A/B, R346). V2 is the default.
* R326 I1 non-finding; I2–I5 done. `_DEONTIC_CYPHER` parses fine on Aura. The judge's
  parent-text fallback stays removed. Haiku is gone from the live path (R346.2 + the
  R350 startup-log fix).
* **The expansion gate asymmetry at `_graph_rag_impl.py:2404` is NOT a gold drop** —
  reported as one, refuted by execution (`Art. 3` is recovered by the scoped BM25
  pre-filter on 5/5 cases). Real effect is +1–3 over-citation. Left unchanged on
  purpose: changing retrieval without an A/B is what the validation policy forbids.

---

**History:** [`docs/ROUNDS.md`](../docs/ROUNDS.md) — every round entry, verbatim.
**This round:** [`docs/reviews/r350-multi-agent-review-2026-08-15.md`](../docs/reviews/r350-multi-agent-review-2026-08-15.md).
**Flag inventory:** [`docs/ENV-FLAGS.md`](../docs/ENV-FLAGS.md) — regenerate with
`py -3.12 scripts/generate_env_flag_inventory.py`.
