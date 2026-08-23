# R377 — independent re-verification of the R376 adversarial review

**Date:** 2026-08-23 · **Base:** `f831145` · **Method:** 13 specialist agents,
one per finding, each required to reconstruct the pre-fix state and demonstrate
the defect BY EXECUTION, followed by an adversarial skeptic per finding that
re-ran the claims rather than reading them.

## Why this pass exists

Commit `e1fd2c4` claims to fix 13 findings raised by an adversarial review of the
R376 branch: *"10 reproduced, 2 did not, and 1 was cleanup."* The reviewer and
the author were the SAME model. A same-model review can be right, but it cannot
be treated as independent evidence, and the specific failure it is prone to is
not inventing defects — it is **stopping at the first input that confirms the
verdict**. That is what this pass looked for.

Every agent was told the commit message is a CLAIM, not evidence, and that a
finding it could not demonstrate by running code is at best PLAUSIBLE.

## Verdicts

| # | finding | defect real? | fix correct? |
| --- | --- | --- | --- |
| 1 | thinking budget ate the answer envelope | **CONFIRMED** | **INCOMPLETE** |
| 2 | prohibition guard promoted a post-RBI verdict | **CONFIRMED** | **INTRODUCES NEW DEFECT** |
| 3 | fallback probe used `is_openai_wrapper_enabled` as readiness | **CONFIRMED** | **INCOMPLETE** |
| 4 | widened challenge markers fired on a first turn | **CONFIRMED** | **INCOMPLETE** |
| 5 | `/healthz/graph` inferred `served_by` | **CONFIRMED** | CORRECT |
| 6 | that probe voted in the circuit breaker | **CONFIRMED** | **INCOMPLETE** |
| 7 | `strip_prohibition_denials` total erasure | **CONFIRMED** | CORRECT |
| 8 | Bedrock thinking silently switches to temperature 1.0 | **CONFIRMED** | **INCOMPLETE** |
| 9 | stale `REGENOLD_BEDROCK_MODEL` rows in CLAUDE.md | **CONFIRMED** | CORRECT |
| 10 | ref budget vs sibling repair ordering | **CONFIRMED** | CORRECT |
| 11 | dead `_mirror_index` loop | **CONFIRMED** | CORRECT |
| A | *refuted:* `_BoundedLRUCache.clear()` has no caller | **NOT REAL** | no fix needed |
| B | *refuted:* the `limit` cap starves the sibling repair | **CONFIRMED — the refutation is WRONG** | **INCOMPLETE** |

So: **11 of 11 confirmed findings were real**, none was invented, and the legal
reasoning in finding 2 checks out against the repo's pinned statute. But **six of
the eleven fixes are incomplete**, one introduces a new defect, and **one of the
two refutations does not hold.**

## The refutation that does not hold

Finding B was dismissed with: *"executed, `build_ground_truth(['Art. 6(3)'],
max_refs=6)` still returns `['Art. 6(3)', 'Art. 6(2)', 'Art. 6(4)']` — sub-point
refs are excluded from the graph fetch by `bare = [r for r in refs if "(" not in
r]`, so they never compete."*

That is one input with ONE ref against a cap of SIX. The cap is nowhere near
binding, so it cannot test a claim about a cap. Re-run at the shipped production
default with a realistic six-citation answer, **zero** sibling paragraphs
resolve — including the exact `Art. 6(3)` / `Art. 6(4)` re-attribution the module
exists to enable. `build_ground_truth`'s shared `limit` counter lets the primary
ref loop consume the whole budget, so the sibling repair is starved for every
input where `len(refs) >= limit`.

The original reviewer was right. The refutation generalised from a
non-binding case.

This one is scoped down by the fact that `faithfulness_verify_enabled()` is
**default OFF**, so it is not live behaviour — but it means the module is inert
in the configuration it would ship in.

## The refutation that holds, for the wrong reason

Finding A — *"`_BoundedLRUCache.clear()` has no caller"* — is NOT REAL, so the
refusal to change anything was right. But the stated evidence is wrong in both
numbers: there are **five** test call sites, not four, and there is a **sixth,
non-test** caller the author missed, which is the one that actually wins the
argument.

That non-test caller also carries its own defect: `evals/harness/ab_judge.py:71`
resolves the cache clear through a swallow-all `getattr`, so it silently no-ops
when the method is absent — which it was, for the entire life of the helper
until R376 added it. Every `ab_judge` run before `8cd770b` switched arms with the
engine LRU **un-cleared**. That is a measurement-attribution risk on historical
numbers, not a code defect at HEAD.

## What the fixes still leave open

Ranked by whether they touch shipped behaviour.

1. **Finding 2's fix can suppress a genuine Article 5(1)(h) verdict.** The
   negative qualifier is cancelled only by the literal token `real-time`, so a
   real-time RBI question phrased with "live" plus a contrastive mention of
   post-RBI loses the anchor. A false negative here drops the verdict on a
   genuinely prohibited practice — the opposite direction from the defect being
   fixed, and worse. Separately, `\bnot\s+real[- ]?time\b` at
   `prohibited_gatekeeper.py:145` is provably dead: every string it matches also
   satisfies the positive re-check at `:169`.
2. **Finding 3's fix left the DEFAULT provider path untouched.** The
   `auto`/unset cascade at `_graph_rag_impl.py:2150` still treats an Anthropic
   API key and a bare `is_openai_wrapper_enabled()` as readiness signals — the
   exact pattern the fix rejected, on the path with the wider blast radius.
3. **Finding 4's fix left a second ungated `is_challenge_turn`.** At
   `_graph_rag_impl.py:10392` it drives the curated-Stage-2-skip exemption with
   no turn gate, and the new gate at `:9236` does not match the route's own
   `if history_turns:` condition, so route and engine can disagree about whether
   a turn is a challenge.
4. **Finding 6's fix made `/healthz/graph` a green-always instrument at the
   shipped defaults.** The mirror-only branch derives its verdict from
   `mirror_on`, so it reports a contributing hierarchy layer even when
   `REGENOLD_KG_CONTEXT=0` has switched the layer off, and reports
   `served_by: none` against a perfectly healthy seeded graph when
   `REGENOLD_KG_LOCAL_MIRROR=0`. Both directions are wrong, and the guard test
   moves two variables at once so it proves neither.
5. **Finding 8 fixed the provenance gap on Bedrock only.** The OpenRouter path
   sends `temperature 0.0` together with `reasoning.max_tokens` and records no
   temperature, so sampling on the PRIMARY provider is unattributable. It also
   records `stage2_model=` from the primary model BEFORE the rollover loop, so a
   chain rollover is misattributed — the Bedrock path records the served model.
6. **Finding 1's fix did not reach the judge.** `evals/judge/runner.py:325`
   builds `BedrockRequest(max_tokens=1600, thinking_budget=N)` and relies on the
   unchanged `_build_converse_kwargs` rule: budget 2048 leaves the judge a
   512-token answer envelope. The judge is an instrument, so this is a
   measurement defect.
7. **Finding 5's provenance is not stamped on three return paths** of
   `fetch_provision_hierarchy` (`kg_context.py:952`, `:955`, `:966`), so
   `last_hierarchy_source()` can report a stale source.
8. **A real doc/code mismatch at HEAD, pre-existing and not R376's:**
   `REGENOLD_DETERMINISTIC_PROSE_CONSISTENCY` is documented **OFF** in CLAUDE.md
   while `app/routes/regenold.py:3785` defaults it **ON**. CLAUDE.md's "0
   doc/code default mismatches" claim no longer holds. `docs/ENV-FLAGS.md` is
   also stale — regenerating yields a 384-line diff, 263 → 293 flags.

## Fixed in this round

`topP` was still added to `inferenceConfig` alongside extended thinking
(`bedrock_client.py:520`), which Anthropic rejects the same way it rejects a
non-1 temperature. Latent — no Stage-2 or judge caller sets `top_p` — but landed
in `fb36f8a` because the two constraints are one rule.

The rest are recorded here rather than fixed, because each is an
answer-affecting or instrument-affecting change that owes its own gate, and this
round's live budget went to the two defects that were destroying answers in
production. See `docs/R377-live-e2e-checkpoint.md`.
