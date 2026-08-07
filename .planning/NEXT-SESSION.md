# Next session — start here

Self-contained handoff. Written 2026-08-07 at `93f7738`. Assumes no memory of the
session that produced it.

---

## 0. Which repo you are in, and why it matters

There are **two** sibling repos of the same FastAPI EU AI Act RAG service. Getting
this wrong wastes hours.

| repo | role |
| --- | --- |
| `antifragileai-regenold-evaluation` (**this one**) | the **re-evaluation surface**: the graded 2026-07-07 code lineage with bugfixes applied. Does **not** deploy anywhere. |
| `regenold-eu-ai-act-rag` (`D:/Claude Projects/regenold-eu-ai-act-rag`) | **deploys to production.** Its own ongoing rounds. |

Verified facts, not assumptions:

* `origin/july7-eval-bugs-fixed` (`44f4dad`) **is an ancestor of `main` here**, so
  the graded lineage is intact.
* The July-7 evaluation machinery exists **only here** —
  `evals/regenold/_official_batch_20260707.json` (110 questions),
  `evaluator_batch_july7.py`, `run_evaluator_batch_july7.py`,
  `july7_difficulty.py`, `tests/test_evaluator_batch_july7.py`,
  `tests/test_r293_july7_difficulty.py`. **The RAG repo deleted all of it** in
  `4fa91e9`. That is the concrete reason the repos are separate.
* Production runs the RAG repo (`/healthz/llm` reported commit `98ad373`), so
  **nothing merged here is live**.

**DO NOT propagate this work to the RAG repo.** It has diverged with its own
parallel line and a **round-number collision** — its `0293789 "R318 — restore the
downed regression guard"` and `87c89c9 "R319 …"` are *different work* from the
R318 here. Operator directive (2026-08-07): this repo is the one to use.

---

## 1. State

`main` == `origin/main` == `93f7738`. Nothing unpushed, no open PRs.

* `d53302f` — merge of [PR #2](https://github.com/Peaky8linders/antifragileai-regenold-evaluation/pull/2)
  * `443a57b` R318 — Aura KG fixes; SPARQL probed and bounded
  * `47794a0` R318.1 — adopted-text-only enforced on the delivered channel
* `1528949` / `d14fcc3` / `93f7738` — checkpoint + judge analysis docs

Read `.planning/R318-CHECKPOINT.md` and `.planning/R318-JUDGE-ANALYSIS.md`.

### What R318 shipped

| area | change | gate (default) |
| --- | --- | --- |
| kg_context ordering | `toInteger(u.number)` — a STRING sort was dropping Art. 3(4)-(8) role definitions | none (defect fix) |
| kg_context cap | env ceiling 30 -> 70; **default stays 24** | `REGENOLD_KG_MAX_UNITS` |
| kg_context budget | routed through the R294 budget + breaker it had bypassed | `REGENOLD_GRAPH_TIMEOUT_MS` |
| kg_context round-trips | request-scoped ContextVar memo, 6 -> 2 | none |
| kg_context executor | its OWN pool (sharing the 2-hop's caused 1274 ms head-of-line blocking) | none |
| boot warm-up | warms the real kg_context Cypher | none |
| cache key | `REGENOLD_PROVENANCE_IN_PROMPT` added (R263.2) | n/a |
| legal-version canary | `scripts/check_legal_version_drift.py`, build-time only, fail-LOUD | n/a |
| adopted-text-only | one sentence in `USER_ANSWER_COVERAGE_CLAUSE` | `REGENOLD_ANSWER_COVERAGE` (ON) |
| sub-point floor | degrade unresolvable leaves to the base article | `REGENOLD_SUBPOINT_EXISTENCE_FLOOR` (ON) |

---

## 2. Environment — get this right or you will chase ghosts

**Deterministic / regression-guard env (3 vars, no secrets):**

```bash
OPENAI_API_BASE=http://127.0.0.1:1/v1 P2P_GRAPH_RAG_PROVIDER=cli REGENOLD_EXTERNAL_EMBEDDINGS=0
```

`env -u OPENAI_API_BASE` is the documented **WRONG** form. The dead port is the
no-live-calls guard; `REGENOLD_EXTERNAL_EMBEDDINGS=0` neutralises a ~6.5 s/row
stall on role-noun queries.

**Live env (Claude Max wrapper + Aura).** This repo has **no `.env`**; the RAG
repo does. Build a scratch one — and note the RAG `.env`'s `OPENAI_API_BASE`
points at the Cloudflare tunnel, which needs CF Access headers, so **override it
to the local wrapper**:

```bash
# from the RAG repo .env keep: NEO4J_URI NEO4J_USERNAME NEO4J_PASSWORD
#   P2P_REGENOLD_API_KEY GROQ_API_KEY GEMINI_API_KEY MISTRAL_API_KEY
# then override:
OPENAI_API_BASE=http://127.0.0.1:8000/v1
OPENAI_API_KEY=dummy
P2P_GRAPH_RAG_PROVIDER=openai_wrapper
REGENOLD_GRAPH_BACKEND=neo4j
```

Wrapper health: `curl http://127.0.0.1:8000/v1/auth/status`.

### Traps that cost time in the last session

* **Do NOT copy the RAG `.env` into this repo.** It carries
  `P2P_GRAPH_RAG_API_KEY=sk-ant-…`, which enables the Anthropic Stage-2 path a
  test expects disabled — it silently broke `test_anthropic_provider.py`. Confirmed
  by A/B: 21 pass without it.
* **Full-suite failure A/B must be run IN PLACE** (`git stash`), never in a
  `git worktree`. A worktree carries no untracked files, so it has no `.env`, and
  the denoiser / topic-filter / safety-gate cluster changes behaviour on
  `GROQ_API_KEY`. Measured elsewhere: 63 vs 92 failures on the same commit.
* `evals/harness/` does **not** load dotenv. Export explicitly or it silently
  falls to the deterministic path (the R256 inert-feature trap).

---

## 3. Baselines to gate against

All measured at `93f7738` under the deterministic env.

| gate | command | expected |
| --- | --- | --- |
| davidath QA | `py -3.12 -m evals.bench.runner --qa-only --label X` | Ans Loose **0.1407** / Ans Strict **0.4072** / Ans Conc **0.1961** / Ref Loose **0.8394** / Ref Strict **0.5536** / Ref Conc **0.439** / Tone **1.0** |
| 276-runner | `py -3.12 -m evals.regenold.runner` | **255/255**, 28/28 categories |
| OOS probe | `py -3.12 -m evals.regenold.runner_v2 --local --probe-oos --oos-suite all --label X` | **49/51, 0 scope leaks** (the 2 soft fails `hoos_adjacent_01/03` are pre-existing) |
| full suite | `py -3.12 -m pytest tests/ -q -p no:cacheprovider` | **55 failed / ~5750 passed**. The 55 are the documented `provider=cli` Stage-2 cluster. **Always diff the failure SET against a stash baseline; never judge by count.** |

Live (local server + Aura + wrapper), for reference:

* Antifragile-20: Ref Loose 0.942 / Ref Strict 0.904 / Tone 1.0 / 32 of 37 expert mistakes resolved
* paper-v4 (52 rows): single-turn Ref Loose 0.90, tricky 0.975, multi-turn coherence 0.917, Tone 1.0
* Omnibus adversarial probe (12 rows): imports **0**, required-misses **0**

---

## 4. The July-7 re-evaluation — what it showed

100 of 110 graded questions replayed on the bugfixed code, graded by
`evals.judge.grounded` (Sonnet-5, verbatim-text-grounded; regenold's own gold was
never published, so `gold_coverage = 0.0`).

Reproduce:

```bash
py -3.12 -m evals.regenold.run_official_batch --label <L> --mode easy
py -3.12 -m evals.judge.grounded --sidecar evals/bench/results/official-<L>-easy.ckpt.jsonl \
    --label <L> --model claude-sonnet-5 --provider wrapper --timeout 120 --concurrency 3
```

Sidecars kept: `official-r318-july7-easy-easy.ckpt.jsonl`,
`grounded-r318-july7-grounded.json`.

**vs R285/R287 — same batch, same judge:**

| axis | before | now |
| --- | --- | --- |
| answer correctness | 0.500 | **0.780** (**~0.86 corrected**, see below) |
| mean factual score | 0.806 | **0.950** |
| citation faithfulness | 0.764 | **0.900** |
| ref precision | 0.615 | **0.673** |
| ref recall | 0.913 | 0.893 |

Objective churn vs the answers actually graded on 2026-07-07: refs/row
**3.94 -> 2.73 (-31%)**, answer length **868 -> 1223 chars (+41%)**.

---

## 5. Findings that must shape what you do next

### 5a. The judge cannot read the tail of long answers

**8 of the 22 answer failures are labelled "truncated". ALL 8 are false
positives.** `rg_066`'s remark says the answer is *"truncated before stating the
Commission is the controller of the EU database"* — that sentence is the answer's
**last one**. Verified all 8; the content called missing is present.

Two independent confirmations it is the instrument, not the system:

* **Zero of 100 answers lack terminal punctuation.** Nothing is cut mid-sentence.
* **Length predicts failure**: answer-FAIL rows median **1698** chars,
  answer-PASS rows **1096**. All 8 flagged rows are 1681-2294.

So answer correctness is **understated — ~0.86, not 0.78** — and any other
long-answer verdict from this judge is suspect, including some reference "wrong"
counts. Same class as R305's judge false positives.

### 5b. Reference correctness — tail padding, and truncation is NOT the fix

Wrong-rate by position in the emitted list:

| rank | rate |
| --- | --- |
| 1 | **0.22** |
| 2 | 0.45 |
| 3 | **0.60** |
| 5 | 0.88 |

Retrieval is fine — the first reference is right 78% of the time. The collapse is
a **cliff, not arithmetic**: against an independent per-ref error rate of 0.327,
1- and 2-ref rows BEAT independence (0.93 vs 0.67; 0.56 vs 0.45) while 3-ref rows
are six times WORSE (0.05 vs 0.30). That lands exactly on the R77-I6 QA budget of
**3**; 38 of 100 rows sit there and supply **36 of 62 failures**. 34 failing rows
have exactly ONE wrong reference.

**Counterfactual (deterministic, over recorded rows):**

| cap | pass | correct kept | wrong kept |
| --- | --- | --- | --- |
| none | 0.37 | 149 | 104 |
| 2 | 0.55 | **116** | 55 |
| 1 | 0.78 | 73 | 20 |
| oracle (drop only wrong) | **1.00** | **149** | **0** |

Capping at 2 destroys **33 correct references to remove 49 wrong**. That is the
trade R142.1's positional clamp made when it lost a live pairwise 11-0
(p=0.001). **All the headroom is in identifying WHICH tail reference is wrong.**

Also: the 0.31 pass rate overstates the damage — that gate is zero-tolerance
conjunctive while the competition scores Jaccard/F1. Quote **F1 0.768**
(precision 0.673 / recall 0.893) alongside it.

---

## 6. Next steps, ranked

### 1. A/B the two mechanisms that ADD tail references
The concrete suspects, both live, both env-gated, both never measured:

* **Component D grounding augmenter** — logs
  `Prose cited <X> which was missing from reference_bases … Dynamically
  augmenting references list` constantly during the replay (Annex I / III / XI /
  XII, Article 16, Article 73). It adds references because the prose named them,
  on the axis whose weakness is precision.
* **`_reemit_parents_for_subpoints`** (R87-C) — emits the parent alongside the
  governing paragraph. The judge's most common reference remark is literally
  *"over-citation of parent article alongside the specific governing paragraph"*.

**Do it offline first**, on the recorded rows — zero generation variance, free,
and it cannot be confounded by Opus sampling. Pattern:
`evals/bench/ref_precision_sim.py`. Only then run a live gate.

### 2. Fix the judge before trusting any further answer number
Everything downstream of 0.78 is uncertain until the length artefact is removed.
Either chunk the answer, or require the judge to quote the allegedly-missing text
and verify it is genuinely absent — `evals/judge/legal_v2.py` already implements
that quote-or-retract rule.

### 3. Finish the measurement
* the remaining 10 easy rows (`--limit`/resume from the ckpt)
* `--mode hard` — **the pushback turn is the graded one**, and it was never run
  this session

### 4. The kg_context change still owes its merge gate
It is answer-affecting. davidath is byte-identical here **by construction**
(Stage-2 never fires under `provider=cli`), so the bench proves nothing about its
quality. Run `evals.harness.ab_judge`, weighted to Article 3 / 26 / 6 questions
where the ordering defect actually bit; a generic set will mostly tie.

### 5. Watch conciseness
Answers are **+41% longer** than the graded July-7 ones. That is **not** from
R318 — it spans the whole bugfix stack, and R315 explicitly uncapped truncation
levers. Conciseness is the one axis the official scorecard says we lead, i.e.
zero headroom.

---

## 7. Do NOT re-propose

* **Chasing the truncation cluster** — it does not exist (§5a).
* **Identity blocklists** for Annex III / Annex I / Article 5 / Article 50. The
  same articles appear in BOTH the wrong and missing lists here (Annex III 5
  wrong / 2 missing; Article 26 3 wrong / 2 missing), and we already drop exactly
  those hardest vs July-7 while they remain the most-often wrong.
* **Positional / top-N reference clamps** — R142.1, 11-0, p=0.001, and §5b
  quantifies the cost on this very data.
* **Prose-driven ref pruners** — structural no-op; 86% of wrong refs ARE
  described in the prose (R298/R302).
* **Reading the ref-count collapse as licence to cut references** (R302).
* **`REGENOLD_GRAPH_FUSE_SLACK > 0`** — R295 measured it destroying gold.
* **A live SPARQL retrieval path.** Cellar's RDF is document-level only: 55
  predicates, no article resources, no Akoma Ntoso manifestation, ELI is a
  literal not a node. It cannot answer "what does Article 26 require". The one
  worthwhile slice is already shipped as the build-time drift canary. (Do *not*
  repeat the error of only probing OUTGOING edges — `act_consolidated_consolidates_resource_legal`
  is incoming and surfaces the post-Omnibus consolidation.)
* **External vector DBs / GPU rerankers / LangChain** — Railway is CPU-only and
  torch-free by design.

---

## 8. Legal-version constraint (operator, 2026-08-07)

Use the **original** Regulation (EU) 2024/1689 as adopted (in force 1 Aug 2024).
**No Digital Omnibus.**

Audited and clean: pinned text carries only the adopted Article 113 dates
(2 Aug 2026 / 2 Aug 2027), Article 51 only 10^25, Article 75 the original text,
113 articles with **zero** lettered entries, 68 definitions with no 3(14a)/(14b).
`PHASE_REGISTRY` and `ROLE_SMALL_MID_CAP` are clean — CLAUDE.md's R70/R98/R25
notes claiming Omnibus additions there are **STALE**.

Enforcement is now on the delivered user channel, because the old rule sat only
in the Stage-2 **system** prompt, which R308 measured the wrapper drops 100% of
the time. Regression probe:

```bash
py -3.12 -m evals.regenold.run_omnibus_probe_r318 \
    --endpoint <url> --api-key $P2P_REGENOLD_API_KEY --label X
```

Score it with `classify_hit()` (IMPORT vs REJECTION) — a bare substring match
counts a correct rejection as a leak and made the guard look *worse*.

**Kept by operator decision:** the Commission GPAI Guidelines content (10^23
threshold, one-third fine-tune rule). It is 18 July 2025 soft law, correctly
attributed, not Omnibus — and `tests/test_kb_stubs_filled.py` pins it
deliberately.

Corpus drift check (offline, ~2 s):

```bash
py -3.12 scripts/check_legal_version_drift.py     # exit 0 = no drift
```
