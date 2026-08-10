# Next session — start here

Self-contained handoff. Written 2026-08-10 at `136fac3` (R327 merged, PR #3).
Assumes no memory of the session that produced it. Read
[`CLAUDE.md`](../CLAUDE.md) first — it is the load-bearing context and it is
current as of this commit.

---

## 0. Which repo you are in

`antifragileai-regenold-evaluation` — the **re-evaluation surface**. It deploys
nowhere. The sibling `regenold-eu-ai-act-rag` (`D:/Claude Projects/…`) is what
deploys to production and runs its own rounds. Round numbers COLLIDE between the
two; prefix any shared reference with the repo name. Sync by **cherry-pick** —
`git merge parent/main` silently DELETES 29 files including the entire July-7
machinery, which exists only here.

**⚠ Never let this repo write to the shared Aura instance.** Pin
`NEO4J_AUTO_SEED=0`. As of R327 auto-seed is opt-IN and only ever seeds a graph
proven to have 0 nodes, so the hazard is much reduced — but the seeder here is
still OLDER than the live graph.

---

## 1. What R327 just did, in one paragraph

Audited ~2.5k lines of uncommitted agent work and found it had shipped an
unauthorised "semantic minimality" change (every scenario reference budget
collapsed to 5, ungated) **while rewriting the eval scorer in the same batch**, so
the bench would have confirmed the clamp with a ruler built to like it. All
measured defaults restored, each behind a default-OFF opt-in. Separately, all
**seven** Neo4j vector indexes are now read (R326 read 2 of 7) via the new
`app/engines/graph_semantic.py`, default OFF behind
`REGENOLD_GRAPH_SEMANTIC_LAYERS`. Full detail in the merge commit and
[`docs/R327-live-ab-semantic-layers.md`](../docs/R327-live-ab-semantic-layers.md).

**State: nothing is enabled that wasn't enabled before.** R327 restored defaults
and added OFF-by-default capability. The scoreboard has not moved.

---

## 2. Ranked next steps

### 1. Gate the semantic layers with the grounded judge — the sidecars ALREADY EXIST

Highest value per minute available right now. Two 50-row live sidecars are on
disk from R327's A/B; the judge run is the only missing piece.

```bash
py -3.12 -m evals.judge.grounded --sidecar evals/bench/results/official-r327-live-ab-A-easy.ckpt.jsonl --label r327-layersOFF --model claude-sonnet-5 --provider wrapper --timeout 120 --concurrency 3
```

then the same for `official-r327-live-layersON-easy.ckpt.jsonl`
(`--label r327-layersON`). **Sequentially — never two wrapper-bound jobs at once.**

* Keep `GROUNDED_JUDGE_STRICT_GROUNDING` **OFF** (the default) or
  answer-correctness returns `judge_error` on 100% of rows: the July-7 batch has
  **no gold answer and no gold refs at all**, only `jul07_*` (the July-7 system's
  own predictions, which scored 0.500).
* Every row now records `answer_grounding_source`. Expect
  `predicted_refs_fallback_circular` — that grounding can catch "the answer
  misreads the provision it cites" but cannot catch "a better provision was never
  cited". Reference-correctness is scored against the Act, so that axis covers it.
* R327's cheap proxy (agreement with July-7 refs) went **F1 0.825 → 0.798**. That
  is a similarity measure, not quality. The judge is what decides.

Decision rule: enable `REGENOLD_GRAPH_SEMANTIC_LAYERS` only on a citation-
faithfulness or answer-correctness win with no reference-precision loss.

### 2. Run `--mode hard` — still never run, and it is THE graded turn

Unchanged from the last three handoffs and still the biggest blind spot. 67 of
111 hard rows carry the adversarial pushback, and **every** optimisation decision
on the table has been made on the easy turn. That is the instrument trap.

```bash
py -3.12 -m evals.regenold.run_official_batch --label r328-hard --mode hard --timeout 240
```

Free, ~40–70 min. Score the Omnibus probe with `classify_hit()` (IMPORT vs
REJECTION) — a bare substring match counts a correct rejection as a leak.

### 3. Re-verify the baseline is reproducible

R327 rebound the canonical axis names back to the historical formulas, so the
authoritative CLAUDE.md block should be measurable again. Confirm before grading
anything against it:

```bash
OPENAI_API_BASE=http://127.0.0.1:1/v1 P2P_GRAPH_RAG_PROVIDER=cli REGENOLD_EXTERNAL_EMBEDDINGS=0 py -3.12 -m evals.bench.runner
```

Expect OVERALL (476) `0.1884 / 0.3545 / 0.6143 / 0.5971 / 0.4748 / 0.4319`. If it
does not reproduce, STOP and find out why before any other measurement — a moved
ruler invalidates everything downstream. `--assert-baseline` also works again.

### 4. Gate the parent-collapse with `easyhard_ab`

`REGENOLD_PARENT_COLLAPSE`, still OFF. +0.018 F1 / +5 rows flipped fail→pass
offline, price is 1 gold ref — which is why it does not satisfy hard rule #8 as
written and needs the count-ratio gate davidath structurally cannot provide.
Note `easyhard_ab` now uses the `*_exact_coord` reference formulas deliberately
(its gold carries sub-point grain; davidath's is head-level).

### 5. Attack GENERATION, not selection

The standing strategic item. R325 closed the ranker (no signal beats the engine's
own `rank`, AUC 0.703), so ~90% of the over-citation gap is upstream. The shape:
1 ref → 0.88 pass, 2 → 0.54, **3 → 0.05**, 4+ → 0.06, with 41 of 100 rows sitting
at exactly 3 (the QA budget). Why does a 3-ref answer name a wrong provision 53%
of the time at rank 3? That is a retrieval / grounding question.

R327's constrained sub-provision layer is the first real instrument aimed here —
which is another reason to finish step 1.

### 6. B.9 backlinks — the best unshipped graph idea

`CROSS_REFERENCES` has **248 edges** and is never read as context. Incoming edges
are real legal signal:

```
article_50 <- [Article 13, Article 26, Article 5, Article 96]
article_11 <- [Annex IV, Article 18, Article 22, Article 23, Article 97]
```

Measured-dead only as a *citation* path (fuse slack destroyed gold; R295 discards
its refs at the fusion budget). As **non-citable context** it is unexplored. Add
it as a fourth block in `graph_semantic.py` behind its own flag — but only after
step 1, because prompt budget competes with Answer-Conciseness, the one axis we
lead.

### 7. Watch conciseness

Answers are **+41% longer** than the graded July-7 ones (868 → 1223 chars) on the
one axis the official scorecard says we lead. R327 restored
`REGENOLD_ANSWER_NO_CAP=1` because turning it off re-enables the soft CHAR cap
that hard rule #2 forbids — but if a bound is wanted, make it **sentence-only**
via `REGENOLD_MAX_ANSWER_SENTENCES` and gate it with `ab_judge`.

---

## 3. Closed — do not re-open

* **R326 code-review finding I1 (`_ENUM_OPENER_RE` truncates (b)–(h))** is a
  **non-finding**. The regex is searched over the unit's first `limit` chars and
  an enumerated unit begins at `(a)`: verified Article 5(1), 10(2) and 13(3) all
  match; 26(1) does not but is 228 chars, well under the 900 cap, so nothing is
  truncated. A unit cannot begin mid-list in this schema.
* Findings I2–I5 of that review (executor lock, Arabic annex normalisation in
  `vector_recall` and Component D, parent-collapse regex) are **done**.
* The audit's claim that `_DEONTIC_CYPHER` "does not parse on Neo4j 5" is
  **false** — verified live, it returns 3 rows. Do not "fix" it.
* The judge's article-level parent-text fallback was deliberately removed and
  must stay removed: measured 0 of 60 real leaf coordinates lack verbatim text, so
  the fallback only ever fires for a FABRICATED coordinate, dressing a
  hallucination in its parent's words.

---

## 4. Environment for a live run

`run_official_batch` and `evals/harness/` **do not load dotenv** — export
explicitly or the run silently falls to the deterministic path (the inert-feature
trap). Do **not** copy the RAG repo's `.env` wholesale: it carries
`P2P_GRAPH_RAG_API_KEY=sk-ant-…`, which enables an Anthropic Stage-2 path a test
expects disabled. Build a scratch env with only:

```
NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD      # from the sibling repo's .env
CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET    # same
OPENAI_API_BASE=https://wrapper.antifragile-ai.net/v1
OPENAI_API_KEY=dummy
P2P_GRAPH_RAG_PROVIDER=openai_wrapper
NEO4J_AUTO_SEED=0
```

The tunnel returns 401 without the CF Access pair; the repo sends them
automatically when both are set. Verify with a real POST — `/healthz/llm` lies.

**Warm the graph client before timing or grading anything.** The first query in a
fresh process measured a MISS against the 750 ms budget (cold TLS + driver
handshake) and 40–68 ms on every query after, so row 1 of a batch silently loses
its graph context.

---

## 5. Two traps that bit this round

* **Check the branch arm's LATENCY on every A/B.** R327's first 50-row A/B was
  byte-identical on all 50 answers AND all 50 reference lists — which reads as
  "safe" and was actually inert: arm B averaged 1,096 ms vs baseline's 16,642 ms,
  i.e. every row was an `_ENGINE_CACHE` hit and Stage-2 never re-ran. Any
  engine-level flag missing from `_engine_cache_key` makes an in-process A/B
  measure nothing. Route-level post-processing flags must stay OUT of the key.
* **`grep` silently stops printing when it decides a stream is binary.** The
  cp1252 curly quotes in provision text make `grep -v` emit
  `Binary file (standard input) matches` and drop every remaining line. It
  produced two wrong conclusions this round ("definitions never fire" — they
  always did). Write to a file and read it, or use `grep -a`.
