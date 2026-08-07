# R318 checkpoint — 2026-08-07

State at the point the July-7 replay was stopped for judge analysis.

## Where the work lives

`Peaky8linders/antifragileai-regenold-evaluation` — the **separate re-evaluation
repo**: the graded July-7 code with bugfixes applied. Verified:

* `origin/july7-eval-bugs-fixed` (`44f4dad`) **is an ancestor of `main`**, so the
  graded lineage is intact.
* The July-7 evaluation surface lives here and **nowhere else** —
  `_official_batch_20260707.json` (110 questions), `evaluator_batch_july7.py`,
  `run_evaluator_batch_july7.py`, `july7_difficulty.py`,
  `tests/test_evaluator_batch_july7.py`, `tests/test_r293_july7_difficulty.py`.
  The RAG repo **deleted all of it** in `4fa91e9`, which is precisely why the two
  repos are separate.
* What sits on top of the July-7 branch is dominated by `fix(...)` commits and
  R-rounds.

**Do NOT propagate this work to `regenold-eu-ai-act-rag`.** That repo deploys to
production, has diverged with its own parallel R318/R319 line (a round-number
collision — its R318 is different work), and has deliberately shed the July-7
evaluation machinery.

## Merged

[PR #2](https://github.com/Peaky8linders/antifragileai-regenold-evaluation/pull/2)
-> `main` at `d53302f`.

* `443a57b` R318 — Aura KG fixes; SPARQL probed and bounded
* `47794a0` R318.1 — adopted-text-only enforced on the delivered channel

### What shipped

| area | change | gate (default) |
| --- | --- | --- |
| kg_context ordering | `toInteger(u.number)` — the string sort was dropping Art. 3(4)-(8) role definitions | none (defect fix) |
| kg_context cap | env ceiling 30 -> 70; **default stays 24** | `REGENOLD_KG_MAX_UNITS` |
| kg_context budget | routed through the R294 budget + circuit breaker it had bypassed | `REGENOLD_GRAPH_TIMEOUT_MS` |
| kg_context round-trips | request-scoped ContextVar memo, 6 -> 2 | none |
| kg_context executor | its OWN pool — sharing the 2-hop's caused 1274 ms head-of-line blocking | none |
| boot warm-up | warms the real kg_context Cypher (cold 2.6 s vs warm 31-39 ms) | none |
| cache key | `REGENOLD_PROVENANCE_IN_PROMPT` added (R263.2) | n/a |
| docstrings | `embedded_graph` / `timeouts` said the opposite of the code | n/a |
| legal-version canary | `scripts/check_legal_version_drift.py`, build-time only, fail-LOUD | n/a |
| adopted-text-only | one sentence ported to `USER_ANSWER_COVERAGE_CLAUSE` | `REGENOLD_ANSWER_COVERAGE` (ON) |
| sub-point floor | degrade unresolvable leaves to the base article | `REGENOLD_SUBPOINT_EXISTENCE_FLOOR` (ON) |

### Gates at merge

* davidath `--qa-only` **byte-identical**: Ans Loose 0.1407 / Ans Strict 0.4072 /
  Ans Conc 0.1961 / Ref Loose 0.8394 / Ref Strict 0.5536 / Ref Conc 0.439 /
  Tone 1.0
* 276-runner **255/255**, 28/28 categories; OOS **0 scope leaks**
* full suite, in-place stash A/B: **0 new failures, 2 fixed**
* Omnibus adversarial probe (12 rows): imports **2 -> 0**, required-misses 2 -> 0

## In flight when stopped

**July-7 graded replay** — `evals.regenold.run_official_batch --mode easy`,
in-process (`_post_local`) with the Claude Max wrapper + live Aura.

* Sidecar: `evals/bench/results/official-r318-july7-easy-easy.ckpt.jsonl`
* **100 of 110 rows captured, zero errors, zero refusals.**
* Stopped deliberately to analyse judge remarks; the remaining 10 rows are not
  expected to change the picture, and the runner resumes from the checkpoint.

Observed while running, worth following up:

* **Component D grounding guard fires often** — repeated
  `Prose cited <X> which was missing from reference_bases ... Dynamically
  augmenting references list` for Annex I / Annex III / Annex XI / Annex XII /
  Article 16 / Article 73. That is the route ADDING references because the prose
  named them. Given reference PRECISION (not recall) is the measured weak axis,
  this is a candidate over-citation source and deserves its own measurement.
* **One transient Aura socket drop** mid-run
  (`Failed to read from defunct connection ... OSError('No data')`), recovered
  with no row error — the kind of degradation the R318 breaker work now bounds.
* Latency is bimodal: many rows 4-15 s, a tail at 40-58 s (the Opus complex
  path).

## Next

1. Grounded judge on the 100 rows (`evals.judge.grounded`, Sonnet-5, running) —
   analyse `failure_mode` remarks.
2. Optional: finish the last 10 rows and the `--mode hard` arm (the pushback
   turn is the graded one).
3. Deferred and NOT done: a live `ab_judge` pass on the kg_context change. It is
   answer-affecting, and davidath is byte-identical here by construction, so the
   bench proves nothing about its quality. The Article 3 ordering fix is
   unambiguous on direction; its magnitude is unmeasured.
