# Next session — start here

Self-contained handoff. Written 2026-08-15 at the R346.2 line (`574a88b`,
PR #32 merged). Assumes no memory of the sessions that produced it. Read
[`CLAUDE.md`](../CLAUDE.md) first — it is the load-bearing context and is
current as of this commit.

---

## 0. Which repo you are in

`antifragileai-regenold-evaluation` — the **re-evaluation surface**. The
sibling `regenold-eu-ai-act-rag` (`D:/Claude Projects/…`) is what deploys to
production. Round numbers COLLIDE between the two; prefix any shared reference
with the repo name. Sync by **cherry-pick** — `git merge parent/main` silently
DELETES files that exist only here.

**⚠ Never let this repo write to the shared Aura instance.** Pin
`NEO4J_AUTO_SEED=0` (default).

## 1. Current state — what merged since the R327-era handoff

The line of work this session: **R340 → R346.2**, all merged to `main`
(PRs #22–#32), full hermetic suite green after every PR, zero new ruff errors.

| PR | What | Key fact |
| --- | --- | --- |
| #22 | R340+R341 retrieval quality | Cohere rerank wired at the **parse level** (the placement that reaches live traffic) + multi-query expansion (RAG-Fusion). Both default-OFF, byte-identical off, cache-keyed |
| #23 | R342 annex/recital dedup | Default KB-primary path expanded annexes/recitals **twice** into the Stage-2 prompt (Art. 43: 1→2, Art. 5: 5→10). Now idempotent |
| #24 | R340 prompt rebuild | V2 system prompt (16.1 K chars) shipped default-ON; test suite taken to zero |
| #25 | R343 tokenizer + audit guard | Dense-lane query tokenizer was a vendored copy that had DRIFTED (digit rule AND stopwords) from the build tokenizer — now uses the canonical function. `evidence=None` was silently dropping the whole audit record — guarded |
| #26 | R344 self-contained clauses | Three default-ON Stage-2 USER clauses pointed at system rules the model never sees (rule 12b, "from your system prompt", "rule above") — made self-contained on BOTH prompt generations |
| #27 | R345 V2 dangling fix | The live V2 sub-paragraph clause still carried the dangling "closed-set completeness rule above" ref — fixed and pinned on both arms |
| #28 | R345 harness control layer | `dynamic_ab._infer_control_layer` classified `REGENOLD_PROMPT_V2` as *retrieval* — the V1-vs-V2 A/B would have probed the wrong layer. Now stage2 |
| #29 | R346 transport + harness | Query-expansion paraphrases follow the ACTIVE provider (Bedrock under `provider=bedrock`, never the tunnel). `dynamic_ab`: batch-level checkpoint sidecars + `--min-call-gap` pacing |
| #30 | R346.1 dead-key diagnosis | A rejected ABSK key is `api_key_invalid_403`: fails fast, never caches per-model, **never tunnel-hops**; `check_connectivity_and_permissions` returns `status=key_invalid` with re-mint steps |
| #31 | R346 results doc | The three live A/B results below |
| #32 | R346.2 no-Haiku | Paraphrase tier = frontier `claude-sonnet-4-6` (was Haiku 4.5), `REGENOLD_QUERY_EXPANSION_MODEL` override; intent-classifier fallback default also off Haiku |

Evidence doc: [`docs/R346-live-bedrock-ab.md`](../docs/R346-live-bedrock-ab.md).
Sidecars (gitignored): `evals/bench/results/dynamic-ab-r346-*.json`.

## 2. The three live A/Bs — n=60, Bedrock Opus 4.6 Stage-2, re-minted key, 0 HTTP errors per arm

All ran `provider=bedrock`, `REGENOLD_BEDROCK_*=claude-opus-4-6`, wrapper
fallback OFF, embedded graph. All three levers **FIRED** (13–49/60 rows
changed). No axis resolved at n=60 — every CI spans zero (UNDERPOWERED) — so
the decisive signals are the veto and direction:

| A/B | fired | ref_loose Δ | kw_recall Δ | gold_dropped | latency |
| --- | --- | --- | --- | --- | --- |
| Cohere rerank (paced 6.5 s) | 49/60 | −0.0083 | −0.0106 | 17→17 (+0) | 10.4 → 11.4 s mean |
| Query expansion (Haiku tier) | 37/60 | **+0.0389** | **+0.0292** | 17→14 (−3, better) | 11.1 → 10.4 s |
| V1 prompt vs V2 default | 13/60 | −0.0083 | +0.0014 | 15→16 (**+1, VETO**) | 5.7 → 5.0 s |

Read: rerank is a wash inside noise (+1.0 s latency, ref_conc the only
positive). Expansion is directionally the strongest arm (recall up, gold drops
DOWN, flat latency) but unresolved at this n. **V1 is REJECTED by hard rule
#8 — V2 stays the live default** (closes the R340 confirmatory question).

⚠ The expansion numbers above used the **Haiku** paraphrase tier. R346.2
switched paraphrases to frontier **Sonnet 4.6**; the confirmatory re-run was
launched but interrupted. Re-run before trusting the Haiku-tier numbers.

## 3. Ranked next steps

1. **Resolve the query-expansion A/B on the frontier tier.** Run the full
   probe (`--max-rows 137`) or the moved-row subset to converge the CI; the
   gold veto is the gate. Commands in §4.
2. **Ground the R346 sidecars** with `evals.judge.grounded`
   (`claude-sonnet-4-6` via Bedrock — the frontier judge the operator
   specified) so the retrieval levers get a quality verdict beyond the
   heuristic axes. Verify sidecar-format compatibility with `grounded.py`
   first.
3. **Run `--mode hard`** — the graded turn (adversarial pushback on 67/111
   rows), never run; every decision so far is on the *easy* turn.
4. **Record the PRIMARY provider's failure in the reasoning trace**
   (`_graph_rag_impl.py` ~:880, `groq_auto_fallback` branch) — R339's outage
   cost hours because only the fallback's outcome was written.
5. **Gate the parent-collapse** (`REGENOLD_PARENT_COLLAPSE`) with `easyhard_ab`
   — +0.018 F1 offline, 1 gold ref is the price.
6. **Attack GENERATION, not selection** — the ~90% over-citation gap is
   upstream of the ranker (wrong ref 53% of the time at rank 3).
7. **`CROSS_REFERENCES` backlinks (248 edges) as non-citable context** — best
   unshipped graph idea.
8. **Fix the judge** (`legal_v2.py`: `GROUNDED_JUDGE_STRICT_GROUNDING` bypass,
   head-lax `provision_exists` ghost-citation gate at `:660`, ungated
   conciseness loosening at `:488-514`) before trusting further answer numbers.
9. **Watch conciseness** — answers are +41% longer than graded July-7.
10. **Gate `REGENOLD_ONTOLOGY_RISK_DOCS`** — default-ON, live-shipping, 9/110
    measured context regressions, no verdict. Do NOT flip the default off —
    re-aligns the committed TurboQuant assets.
11. **`ab_judge` swap-consistency counts judge errors as agreement** — add an
    error channel before reading either number.

## 4. Environment for a live Bedrock A/B

`evals/harness/` does **not** load dotenv. The working recipe (this session's
`scratch/live_ab_env.py` + `scratch/run_ab.py`, gitignored) loads the
operator `.env` from the main folder then forces:

```
P2P_GRAPH_RAG_PROVIDER=bedrock
REGENOLD_BEDROCK_WRAPPER_FALLBACK=0      # a dead key must not hop to the tunnel
REGENOLD_GRAPH_BACKEND=embedded          # deterministic local graph, both arms equal
REGENOLD_EXTERNAL_EMBEDDINGS=0           # COHERE_API_KEY would auto-switch the dense lane to the external embed API
REGENOLD_BEDROCK_MODEL=claude-opus-4-6   # + _STAGE2_ / _COMPLEX_ / _STAGE1_
```

```bash
PYTHONPATH=. py -3.12 scratch/run_ab.py --flag REGENOLD_QUERY_EXPANSION \
    --label r346.2-live-expansion-frontier --max-rows 137 --batch 12
```

Rerank A/B needs `--min-call-gap 6.5` (Cohere Trial key). V1-vs-V2 uses
`--branch-env REGENOLD_PROMPT_V2=0`. Long runs: launch detached
(`nohup … &`), the harness now writes a checkpoint sidecar after every batch.

**Verify the key before a run**: `check_connectivity_and_permissions('claude-opus-4-6')`
must say `status: ok` — ABSK keys expire after 30 days (see §6).

## 5. Judge

`claude-sonnet-4-6` via Bedrock is the specified judge tier (verify it
invokes on the current key: R328.2 measured sonnet-5 403 on the old key,
sonnet-4-6 fine). `REGENOLD_BEDROCK_JUDGE_MODEL` env wins over `--model`.

## 6. Gotchas that cost a session (each is in CLAUDE.md, both are new)

* **ABSK Bedrock keys: 30-day life, shown ONCE.** Both repos' `.env` share
  one key. Expiry looks like `Authentication failed: Please make sure your
  API Key is valid.` on EVERY model — verified raw-HTTP against the official
  AWS contract before concluding the key was dead; the code was right, the key
  had expired (authenticated 08-13, dead 08-15). Re-mint in the AWS Bedrock
  console → API keys; the client picks it up fresh per call, no restart.
* **Cohere Trial key (10 calls/min): unpaced rerank A/B = false INERT.**
  Every call 429s → fail-soft → entities unchanged → INERT verdict for a
  working feature. `--min-call-gap 6.5` or a production key.

## 7. Closed — do not re-open

* **V1-vs-V2 prompt**: V1 REJECTED by the gold veto (live A/B, §2). V2 default
  confirmed. (The R327-era handoff's "confirm V2" item is DONE.)
* R326 I1 non-finding; I2–I5 done. `_DEONTIC_CYPHER` parses fine on Aura. The
  judge's parent-text fallback stays removed. Haiku is gone from the live
  path (R346.2).

---

**History:** [`docs/ROUNDS.md`](../docs/ROUNDS.md) — every round entry, verbatim.
