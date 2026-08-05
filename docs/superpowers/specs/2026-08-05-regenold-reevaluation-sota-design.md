# R314 — Regenold re-evaluation: design

> **Date**: 2026-08-05
> **Target**: `Peaky8linders/antifragileai-regenold-evaluation`, branch `july7-eval-bugs-fixed`
> **Graded run under analysis**: `REGENOLD_JULY_7_EVALUATOR_BATCH.md` — 333 live requests, 2026-07-07
> **Status**: design approved; implementation plan to follow

---

## 1. The reframe

The brief was "features and rules needed for SOTA, to beat frontier 2026 models such as
Opus 4.8". The evidence says **almost no new features are needed, and adding them is the
failure mode.**

Every fancy retrieval lever has already been measured on this corpus and is dead: RRF,
dense/turboquant, cross-encoder rerank, BGE ONNX, MoA fusion, neural NLI, verbatim-as-default,
`REGENOLD_OPUS_FOR_ALL`, positional reference clamps. Several were refuted three or four times.
The corpus is BM25-saturated.

We do not lose to a frontier model on retrieval — we **beat** a search-less frontier model on
references (+8.3 RefS). We lose on answer composition (−10 kw). And the 7-July run did not
measure answer composition either. It measured a truncation bug.

## 2. What actually decided the 77.5 / 73.0

### 2.1 The batch is a consistency probe, not 333 independent questions

333 requests = ~111 questions replayed at three depths, 111 rows each:

| `history_turns_used` | condition | refs/row | answer len | `anchor_articles` |
| --- | --- | --- | --- | --- |
| 0 | fresh ask | 3.97 | 910 ch | 1.28 |
| 18 | same question, with history | 4.16 | 869 ch | 2.22 |
| 20 | adversarial pushback re-ask | 4.84 | 1114 ch | **9.52** |

Category labels: Multi-Turn Context & Coreference 222 (66.7%), Easy Mode 52 (15.6%),
Complex Decision Boundary 44, GPAI 7, MedTech 5, Two-Article Conflict 2, Borderline 1.

67 of the 222 multi-turn rows are an explicit adversarial template:

> *"I don't think this is correct. Perhaps your answer contains hallucinations. (Briefly reason
> about whether something might indeed be incorrect, using the reasoning field. Then, provide a
> clear answer with the same format as before, as if I had just asked the same question anew:
> without mentioning the previous answer or the pushback.) Let's try again: &lt;original question
> verbatim&gt;"*

Measured on our own logged answers: across questions asked at more than one depth, **82% get a
different answer and 74% get a different reference set** purely from conversation depth.

### 2.2 Defect A — the 2000-char cap shredded the multi-turn prompts *(fixed)*

`GraphRAGRequest.question` carried a self-imposed `max_length=2_000`
(`app/models.py`). It was never a model or provider limit. `_build_question_from_history`
left-truncated to fit, which preserved the `Latest question:\n` marker by design but chopped the
head *past* `Conversation so far:`.

Structure of the 333 flattened questions as the engine received them:

| hist | `Conversation so far:` | `User:` lines | `Latest question:` | anchor | n |
| --- | --- | --- | --- | --- | --- |
| 0 | ✗ | ✗ | ✗ | ✗ | 111 |
| 18 | ✗ | ✗ | ✗ | ✗ | 99 |
| 18 | ✗ | ✗ | ✗ | partial | 8 |
| 18 | ✓ | ✓ | ✓ | ✓ | 4 |
| 20 | ✗ | ✗ | ✗ | partial | 44 |
| 20 | ✗ | ✓ | ✓ | ✗ | **42** |
| 20 | ✗ | ✗ | ✓ | ✗ | 12 |
| 20 | ✓ | ✓ | ✓ | ✓/✗ | 13 |

Only 17 of 222 multi-turn requests arrived structurally intact. 49 began mid-token, inside a
fragment of a prior assistant answer:

```
#117  "proportionality requirements.\nUser: When the intended use of an AI system is listed in Ann…"
#133  "to the extent that is in their control. They must also ensure the system can generate the "
#113  "nex iii]\n\nConversation so far:\nUser: Do providers need to keep logs…"
```

Every detector keyed on `Conversation so far:` / the anchor prefix therefore ran against
corrupted text — `_detect_classification_topic`, `_detect_role_obligation_query`,
`_needs_stage2_enhancement`, the R60.1 complexity gate, `select_best_stub`, the R71 live-turn
scorer. This is exactly the failure the comment at `app/routes/regenold.py` was written to
prevent.

**Resolution (already landed in this branch):** `_MAX_QUESTION_CHARS = 64_000` in
`app/models.py`, resolved at the route by `_max_question_chars()` with the
`REGENOLD_MAX_QUESTION_CHARS` override (set it to `2000` to reproduce pre-R314 behaviour for an
A/B). The marker-preserving truncation logic is retained as a bound against a hostile payload.

Verified: replaying the request-#113 shape reproduces the bug at `cap=2000`
(`'gh-risk]\n\nConversation so far:…'`) and repairs it at the new default
(`'[Context anchors — roles: provider; risk tier: high-risk]…'`).

davidath is byte-identical to the SOTA baseline — Ref Loose 0.5967, Ref Strict 0.4744,
Ref Conciseness 0.4319, Ans Strict 0.3528, Ans Conciseness 0.6144, Tone 1.0, multi-turn 20/20.

### 2.3 Defect B — the graded branch was 92 commits behind `main`

The graded deploy ran `july7-eval-bugs-fixed @ 44f4dad`. `git rev-list --count HEAD..origin/main`
= **92**. Absent from the graded run: R281 (gold-protected adaptive clamp), R298 (user-channel
reference minimality + challenge brevity), R302 (verbatim grounding text default ON), R305
(re-ask focus + routing fixes), R306 (enumeration guard), R310 (`strip_retrieval_meta`), R311
(Annex I route exclusivity).

R298's own A/B (43 requests per arm, both judges): multi-turn reference precision
**0.423 → 0.735 at recall 0.966**, answer correctness **0.471 → 0.647**, citation faithfulness
0.588 → 0.706, pushback inflation **+38.3% → −0.2%**.

### 2.4 Defect C — conversation history contaminates the emitted reference set

A fixed 9-article blob `{Art. 5, 6, 9, 10, 14, 43, 53, 55, Annex III}` — derived from the
evaluator's scripted history (conformity→43, logs→12/13, deepfakes→50, RBI→5, oversight→14) —
is superset-present in **122/333 rows (37%)**, split 0 at turns=0, 12 at turns=18, and
**110 of 111 at turns=20**. The anchor-count histogram is bimodal (0–4, then a gap, then 9–12),
so this is an injected population, not gradual drift.

The in-batch control is decisive. **#2 and #114 are the same question with byte-identical
382-character answers**, yet:

```
#2    references: ["Article 50.4", "Article 50"]
#114  references: ["Article 50.4", "Article 9", "Article 10", "Article 53", "Article 14"]
```

Four irrelevant articles added **and the correct parent Article 50 evicted**, with zero answer
benefit. This is not the R142.1 precision-for-recall trade — it loses on both sides. It lands on
Reference Strict, the highest-leverage axis (+0.163pp Overall per +1pp).

### 2.5 Defect D — we violate the pushback turn's explicit instructions

The evaluator instructs: reason in the `reasoning` field, and answer "as if I had just asked the
same question anew: without mentioning the previous answer or the pushback." We violate both —
**31 of 67 open the `answer` field with `Reasoning:`**, and **25 of 67 explicitly discuss the
prior answer** ("The prior answer was substantively accurate", "My earlier answer got the count
right but described the wrong set"). Pushback answers run +71% longer (median 1320 ch vs 773 ch
at turns=0) with references 3.97 → 4.67.

Per R285, the graded hard answer *is* the post-pushback turn, so this is 100% of what hard mode
scores on those conversations.

### 2.6 Defect E — the graph contributed nothing

`retrieval_path` is `kb_fallback` on **333/333**. Zero `neo4j`. Known and separately tracked;
the graph is additive-only by design, so this is not on the critical path for this round.

---

## 3. Plan

Five levers in dependency order. Lever 0 is already-banked evidence; lever 1 is the largest
unfixed defect; levers 2–4 are correctness-floor repairs.

### Lever 0 — cherry-pick the validated stack

Cherry-pick R281, R298, R302, R305, R306, R310, R311 onto the graded branch (decision: targeted
cherry-pick, not a full rebase, to keep the blast radius attributable).

Blocking sub-task: **fix the three scope misclassifications before the topic filter goes ON.**
The graded run had `REGENOLD_TOPIC_FILTER` off, so three misclassified rows were answered anyway:
`#285` (a legitimate GPAI proportionality question flagged `PROMPT_INJECTION`), `#2` and `#98`
(flagged `CONVERSATIONAL`). `PROMPT_INJECTION` and `CONVERSATIONAL` refuse regardless of the
toggle, so shipping as-is converts three answerable graded rows into branded refusals. Decision
taken: repair the classifier, keep the filter ON, keep the OOS probe at 21/21 with 0 leaks.

### Lever 1 — multi-turn reference isolation

Prior turns may inform retrieval **ranking**. Only the live turn's retrieval and the answer's own
prose may put a reference **on the wire**.

Concretely: gate the `scope.anchor_articles` contribution and the assistant-anchor-inheritance
seeds out of the candidate list on multi-turn rows unless the live turn independently supports
them; extend the R133.1 `self_contained_focus` suppression so it no longer depends on the query
de-noiser having succeeded.

This re-gates existing machinery (`self_contained_focus`, the R88-A protected seeds) rather than
adding architecture.

**Risk:** must not break genuine coreference — R55-E, R57-A, R73 and R88-A exist because bare
follow-ups ("Are these checks continuous?") need prior anchors. Gate on the existing
`_live_turn_is_self_contained` heuristic rather than blanket suppression, and keep the R88-A
protected seeds.

### Lever 2 — flatten hygiene

The cap removal has landed. Remaining:

- Raise `_HISTORY_TURNS_TO_INCLUDE` from 8 (decision taken). Note the unit: the constant slices
  `dialogue[last_user_idx - N : last_user_idx]`, so it counts **messages**, not exchanges — 8
  means 4 user + 4 assistant. The evaluator declares 18–20 "turns" without defining the unit, so
  set **N = 40** (20 user + 20 assistant), which is a superset under either reading. With the
  64 000-char budget this is comfortable: a 20-exchange legal conversation runs ~10–25k chars.
  This is now the binding constraint. It interacts with lever 1 — sequence lever 1 first, or land
  them together.
- Never orphan the `[Context anchors — …]` prefix: when truncation would strand it, drop it
  entirely rather than emit a fragment.

**Verification:** replay all 333 recorded conversations through the flattener and assert zero
mid-token heads and zero orphaned anchor prefixes.

### Lever 3 — pushback instruction compliance

Target is **parity with the identical standalone ask** — same length, same reference set — which
is literally what the evaluator asked for. R305 `REASK_FOCUS` and R298 challenge brevity already
exist and ship default-ON on `main` (arriving via lever 0). Add a deterministic sanitiser that
strips a leading `Reasoning:` block and prior-answer meta sentences from the `answer` field on
challenge turns.

**This is not "shorten answers."** Answer Conciseness (96.0 / 93.4) is the only axis we lead
against both baselines; general shortening is pure downside.

**Control that must not move:** pushback concession rate, measured 0.0000 across three runs
(n=110, 28, 30).

**Caveat:** match the *shape*, not the literal string — the R264 marker guard caught 0 of 4 leaks.

### Lever 4 — five general routing gaps

| Question shape | Correct target | Evidence |
| --- | --- | --- |
| migration and border control | Annex III point 7 | #94, #298 — answers are entirely about real-time RBI, never use the word "migration" |
| "AI regulatory sandbox" definition elements | Article 57 definition | #38 — 207-char answer is the sandbox-list-publication sentence, addresses none of the five requested elements |
| deployer log retention | Article 26(6) | #91 — answered with FLOPs thresholds at confidence 0.5 |
| exclusive GPAI supervision | the AI Office | #62 |
| transitional provisions before 2 Aug 2026 | Articles 111 / 113 | #321 — references are the pure bleed blob, zero Art. 111/113 |

At least 8 confirmed total-miss rows (~2.5% of the batch), each a double zero on answer *and*
reference correctness. Precedent: R252's KB-primary retrieval fixed an identical wrong-article
cluster and measured RefL 0.785 → 0.896, RefS 0.515 → 0.656 on the medtech set.

**Hard rule #3 applies without exception.** These must be general keyword→article routes, each
shown to fire on **0/137 davidath QA and 0/339 scenarios** before shipping — never per-row
curated intercepts keyed to evaluator questions. R305 had to remove three such hardcodes, one of
which returned `False` on its own target question while its test passed against a truncated copy.

---

## 4. Explicitly out of scope

Two things are deliberately **not** proposed: any new retrieval layer, and any general
"write more" / "write less" instruction.

### Stays rejected

Positional / top-N reference clamps (R142.1 lost the live pairwise 11-0 on references, p=0.001;
R298 proved *why* it is untunable — wrong and correct references have no positional separation).
Prose-driven pruners (86–95% of wrong references *are* described, so they are structural no-ops).
The R299/R300 OPERATIVE/BACKGROUND partition (backgrounds the governing provision; with the R72
reconcile it executes a wire deletion). Pushback reference freeze (recall 0.845 → 0.576).
Neural NLI / torch (AUC 0.585 vs the free lexical scorer's 0.749, 235× slower, blows Railway's
image ceiling). RRF, dense/turboquant, cross-encoder rerank, BGE ONNX (BM25-saturated, confirmed
four times). Verbatim-as-default (answer correctness 0.25 — keep it explicit-quote-only).
Mixture-of-Agents fusion. `REGENOLD_OPUS_FOR_ALL` (two runs, dead even).
`REGENOLD_STAGE2_SIMPLE_SKIP` (judge refs 0.75 → 0.47). Forwarding the system prompt to the
wrapper (kw_recall −0.267, off-topic drift). R313 bounded faithfulness verifier as a default (its
own target axis fell 0.800 → 0.775 at 3.6× latency). R284 H1 completeness clause (buys
completeness by over-citing). Fast mode and thinking-budget trims as latency levers (measured
washes; latency is wrapper-floor bound). Neo4j as a primary ranker (it dumps the generic
Articles 9–15 chain and buries the operative article — graph stays additive-only).

### Invariants

1. Reference format is strict — `Article N(.sub)*` / `Annex ROMAN(.sub)*` via `refs.py`.
2. Every emitted citation must resolve in `ARTICLE_EXISTENCE`; new mapping modules need an
   import-time self-check.
3. Any `EC_CHECKER_OBLIGATION_MAP` edit must bump `KB_VERSION` (CI-linted) or the engine LRU and
   the graph seed serve stale prose.
4. KB prose ships faithful regulation, verified verbatim against `provision_text` — a
   confidently-wrong summary loses more than a missing one (R299 shipped Article 5(1)(h)
   law-enforcement carve-outs *as prohibitions* this way).
5. Hard rule #3 — no per-row intercepts keyed to evaluator questions; every new detector proven
   to fire on 0/137 davidath QA + 0/339 scenarios first.
6. Cache-key doctrine — any input that flips engine behaviour must be in `_engine_cache_key`, or
   a same-process A/B silently serves arm A's cache to arm B.
7. Graders score at **sub-point grain**. "Head-level recall is invariant" is not a sufficient
   safety argument (R287 collapsed `Annex III.8.a/.b` to bare `Annex III` and took grounded
   recall 1.0 → 0.0). Local scorers head-collapse and cannot decide a granularity change.
8. The Stage-2 **system** prompt is delivered on 0% of requests. All answer-prompt edits go in
   the **user** message, and the clause must be asserted present in the outgoing request before
   any A/B is trusted.
9. davidath is a regression guard, never a merge gate. Use `easyhard_ab` (gold-bearing, has a
   minimality term) for reference changes, `ab_judge` for answer changes, the grounded judge for
   citation faithfulness — and never quote one judge as the other.
10. `railway.toml [deploy.envs]` has never applied. Every flag must be a **code default** or a
    dashboard variable.

---

## 5. Verification strategy

Decision taken: **deterministic replay + one live confirmation.**

| Gate | Applies to | Cost |
| --- | --- | --- |
| Recorded-batch replay over the 333 rows | every reference and flatten change | variance-free, seconds |
| davidath `--assert-baseline` | all changes (regression guard) | ~2 min |
| 276-runner | all changes | ~1 min |
| OOS probe 21/21, 0 leaks | scope classifier repair (lever 0) | seconds |
| `easyhard_ab` local, gold-bearing | lever 1 reference isolation | minutes |
| One full live pass | the assembled stack, end to end | hours |

Rationale: a 40-row live sample provably cannot resolve reference-axis effects — identical
baseline arms drifted 0.053 and sign-flipped all three reference axes. The replay is where the
evidence actually is for levers 1–4; the single live pass confirms Stage-2 prompt delivery and
model routing, which only manifest live.

Two additional live-only checks before any measurement is trusted: confirm the wire model
post-deploy, and assert the Stage-2 user-channel clause is present in the outgoing request.

---

## 6. Open items

1. **Raw evaluator payload.** The audit stores *our* flattened query, not the raw messages array.
   99 rows declare `history_turns_used: 18` but contain zero embedded turns, and at most 4 prior
   turns ever appear. Railway/server request logs exist and should be pulled to settle whether
   the evaluator sends 18–20 turns and we discard them, or sends fewer than declared. Lever 1's
   exact injection point depends on this; the fix shape is the same either way.
2. **Official gold for the 333.** Absent it, every reference change is validated on our own
   harness against our own gold, and no local scorer is on the official scale.
3. **Speed.** Speed hard is 61.7, −35.6pp behind the 2025 baseline, with roughly the same
   geometric-mean leverage as Answer Strict — but no validated mechanism beyond fewer
   round-trips. Not addressed in this round.
