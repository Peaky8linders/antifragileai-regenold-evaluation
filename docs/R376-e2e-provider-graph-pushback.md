# R376 — end-to-end provider routing, the graph layer, and the pushback turn

**Date:** 2026-08-22 · **Branch:** `claude/openrouter-bedrock-neo4j-e2e-26e2um`

## What was asked

Make the end-to-end flow work with the OpenRouter implementation — Opus 5 with
2048 thinking tokens for complex questions, Sonnet 5 for simple ones — with the
Bedrock fallback working; make sure the Aura graph, ontology, semantic layers,
TurboQuant embeddings, retrieval and reranker are wired correctly; run live
tests including adversarial pushback; fix what the logs and answers show.

## The instrument, and its honest limit

**No external provider was reachable from this environment.** The session ran in
a cloud container whose egress policy 403s `openrouter.ai`,
`databases.neo4j.io`, `api.cohere.com`, `api.groq.com`, `railway.com` and the
Railway app domain; AWS hosts resolve but `AWS_ACCESS_KEY_ID` is the placeholder
`proxy-in…` and `ListInferenceProfiles` returns `UnrecognizedClientException`.
There is no `.env` in the container (it is gitignored, and the repo was cloned
fresh).

So the work was done against **local servers speaking the real wire protocols**:

* `scripts/e2e_provider_mocks.py` — `MockOpenRouter` (OpenAI-spec
  `POST /api/v1/chat/completions`) and `MockBedrock` (`POST
  /model/{modelId}/converse`, reachable by botocore through
  `AWS_ENDPOINT_URL_BEDROCK_RUNTIME`). Both stdlib-only, both record every
  request byte-for-byte, both scriptable to error, throttle or truncate.
* `scripts/e2e_route_probe.py` — drives the real FastAPI route over a scenario
  battery and reports, per turn: the complexity gate's verdict, the model on the
  wire, the thinking budget, the Stage-2 grounding blocks and their sizes, the
  references, the answer, and any fallback hop.

**What that measures:** routing, tier selection, thinking budget, grounding
assembly, citation extraction, fallback behaviour — everything between the
question and the model, and between the model and the wire.
**What it does not measure:** answer quality. The mock returns canned text, so
nothing here is a correctness, conciseness or judge number. Answer-level
findings below come from the DETERMINISTIC path (`provider=cli`), which produces
real engine answers.

This matters because the properties above are precisely the ones this repo has
shipped broken and silent, and precisely the ones a live run attributes WORST:
a live answer that is merely mediocre looks the same whether the graph
contributed or not.

## Findings

Every one was invisible to the existing suite for the same structural reason:
those tests mock `provider.complete` and assert on the request OBJECT, which
proves the engine formed the right intent, not that the intent survived
serialisation. All of these live below that seam.

### P1 — a pinned OpenRouter with a lapsed key killed Stage-2 outright

`_stage2_provider_enabled()` returned `False` for
`P2P_GRAPH_RAG_PROVIDER=openrouter` whenever `OPENROUTER_API_KEY` was absent.
That gate sits ABOVE the whole dispatch, so the cross-provider Bedrock net at
the end of `_claude_max_enhance_answer` was never reached.

> Measured end-to-end with a healthy mock Bedrock on the wire: **zero** Bedrock
> calls, the deterministic answer served, `/healthz` green.

A rotated key on Railway would have silently removed Stage-2 from production.
Fixed: the pin is a preference, not an instruction to stop answering — it now
degrades through the same cascade `auto` uses, and logs it.

### P2 — the OpenRouter thinking budget was bound to a URL substring

`complete()` decided "is this OpenRouter?" with `"openrouter.ai" in base_url`.
Any other base — a gateway, an observability proxy, a regional mirror — made an
`anthropic/claude-*` model match the Claude-Code-CLI branch instead, so the
budget was routed to an HTTP header OpenRouter does not read.

> Measured, same code and config, only the host differing:
> off-host `reasoning=None`; on-host `reasoning={'max_tokens': 2048}`.

Fixed: the identity travels with the provider object
(`get_openrouter_provider()` passes `is_openrouter=True`); the URL heuristic
survives only as the default for instances built without the flag.

### P3 — Bedrock Stage-2 never asked for extended thinking

`BedrockRequest.thinking_budget` has existed since R355 and
`_build_converse_kwargs` translates it into
`additionalModelRequestFields.reasoning_config` — but the Stage-2 adapter never
set it, so only the judge ever used it.

> Measured: a complex Stage-2 Converse call carried
> `additionalModelRequestFields: None`.

Fixed, and resolved PER MODEL inside the rollover loop: the R366.1 chain also
carries qwen / nemotron / devstral tiers, which reject the Anthropic-only field.
Sending it there would turn a recoverable throttle into a 400 — breaking the
rollover in exactly the situation it exists for.

### P4 — the Bedrock tier split was honoured on one provider only

`app/config.py` sets `stage2_model=claude-sonnet-5` /
`complex_model=claude-opus-5`, and the OpenRouter path mirrors it. The Bedrock
path routed a SIMPLE Stage-2 answer through `BEDROCK_RAG_MODEL` — the Stage-1
PARSE tier, Opus 4.8.

> Measured: a simple question that had degraded to Bedrock posted
> `eu.anthropic.claude-opus-4-8`.

Fixed with a distinct `BEDROCK_STAGE2_MODEL = eu.anthropic.claude-sonnet-5`.
Two constants because they answer two different questions.

### P5 — the cross-provider fallback collapsed the tier split

The retry pinned `model_override="claude-opus-4-6"` for every row, simple or
complex, at the moment the answer was already degraded. It was redundant as well
as wrong: `complete_with_fallback` degrades within the Claude family on an
entitlement error, so asking for the right tier reaches opus-4-6 anyway on a key
that cannot invoke Opus 5 — and reaches Opus 5 on a key that can. Hard-coding
the degraded tier could only ever prevent the good outcome.

### P6 — the rollover chain left the Anthropic ladder

Default was `deepseek/deepseek-v4-flash,google/gemini-2.5-flash`.

> Measured with the primary 429-ing every call, the wire order was
> `anthropic/claude-opus-5 → deepseek/deepseek-v4-flash →
> google/gemini-2.5-flash` before Bedrock saw a single request.

Every prompt, guard and judge here is calibrated on Claude, and reference
conciseness — the one axis the official scorecard says we lead — is a function
of how the model cites. The chain now degrades within Anthropic and hands off to
Bedrock. It is one entry, which gives it tier-awareness for free through the
existing de-duplication: a complex question degrades opus-5 → sonnet-5, and a
simple one de-dupes to a single attempt, so it can never ESCALATE to a costlier
tier the operator did not choose — the rule `fallback_chain_for` already encodes
for Bedrock.

### P7 — the KG hierarchy layer vanished silently without Aura

Every `kg_context` fetcher fails soft to `[]` and the renderer treats `[]` as
"render nothing". That is the right contract for a graph that might be wrong,
and it makes an ABSENT graph indistinguishable from an empty one.

> Measured on a deploy without Aura credentials: the Stage-2 user message
> contained no PROVISION HIERARCHY, no SUB-POINT and no REGULATORY
> CLASSIFICATION block at all.

The hierarchy in Aura is not independent knowledge — `scripts/seed_neo4j_kb.py`
WRITES it from `provision_hierarchy.build_hierarchy_payload()`. Serving that
same function in-process is the identical structure one step earlier in the
pipeline, and it reproduces the documented live census exactly: **658 paragraph
units, 37 sub-points**. If anything it is fresher (in-repo KB is v21; the
instance is seeded at v18).

Effect on the delivered prompt, same question, before → after: **38,962 →
57,193 chars**, with the new block leading `Annex III (4) Employment, workers'
management and access to self-employment` — the exact sub-provision that answers
"is a CV-screening tool high-risk?".

Deliberately NOT mirrored: recital anchors and the role × risk-class layer.
Those encode curated legal judgements, and CLAUDE.md records prose-mined
recital→article edges as measured and dead (~4 of 32 candidates were genuine AI
Act references). Hard rule #10 is untouched: the block is still non-citable and
still cannot reach the wire.

### P8 — a latent budget overflow the mirror exposed

`faithfulness_verify.build_ground_truth` let graph-sourced additions exceed the
caller's `max_refs` (`len(out) < limit + 4`), so `max_refs=2` returned six
entries once the hierarchy had rows. Each entry costs up to `ref_chars` in the
verify prompt. This has been live on every Aura-connected deploy and invisible
on every other one.

### P9 — `/healthz/graph` answered the wrong question

It reported "can I reach Neo4j?", which is not "is the hierarchy block reaching
Stage-2?" — and only the second one shows up in an answer. A graph can ping
healthy while the layer is dead behind `REGENOLD_KG_CONTEXT=0`, an open circuit
breaker, or an instance seeded without `HAS_PARAGRAPH` edges. CLAUDE.md's own
words for the seed hazard: *"the seeder succeeds, `/healthz/graph` still reports
ok, answers just get worse."* A `kg_context` block now runs the same fetcher the
answer path runs and reports rows, units and `served_by` (graph vs
local_mirror), on every return path.

## The pushback turn — three defects on the graded turn

CLAUDE.md records the adversarial follow-up as THE GRADED TURN (67 of 111 hard
rows carry it) and notes it has never been run as a gate. Two pushback
conversations found three defects, each making that turn worse than the easy
turn it follows.

### P10 — the curated intercept fired on the challenge and not on the opener

The curated detectors match on provision keywords, and a user disputing a
verdict NAMES the provision they are disputing. So contesting an answer made a
static verdict MORE likely.

> Measured: turn 1 reached Stage-2 with a 61,681-char grounding block; turn 2 —
> gated complex, eligible for Opus 5 — made **no LLM call at all**.

### P11 — the model never saw the objection

R372's challenge-focus recovery replaces the live turn with the recovered
turn-1 root question. Right for RETRIEVAL, wrong for GENERATION, and applied to
both.

> Measured on the credit-scoring pushback, the delivered Stage-2 user channel
> contained none of `I disagree`, `assists a human`, `small company`,
> `no obligations`. The model was re-answering turn 1.

### P12 — and it routed to the standard tier

The tier is decided from that same recovered root — usually a plain
classification ask — so the hardest turn routed to `claude-sonnet-5` with
`reasoning=None`, while the identical text asked directly gates complex.

Underneath all three, `is_challenge_turn` recognised neither pushback: 17
marker phrases of one family ("you are wrong"), missing both ordinary ways a
user disputes a legal answer — stating a counter-position and demanding a
correction. So the R372 recovery, the brevity clause and the reference freeze
were all inert on the turn they exist for.

**The consequence was visible in the answers.** On the emotion-recognition
conversation the opening turn correctly led with *"prohibited under Article
5(1)(f)"* for a workplace deployment; the intercepted challenge turn led with
*"not categorically prohibited"*, dropped `Article 5.1.f` from the references,
never engaged the user's consent argument — consent is irrelevant to an Article
5 prohibition — and pointed a prohibited workplace practice at Annex III and
Article 50 transparency duties, which reads as *permitted if you disclose*.

Measured before → after, three conversations:

| conversation | before | after |
| --- | --- | --- |
| credit scoring | sonnet-5 / no thinking / argument invisible | opus-5 / 2048 / visible |
| emotion @ work | **no Stage-2 call at all** | opus-5 / 2048 / visible |
| GPAI threshold | opus-5 / no dispute instruction | opus-5 / 2048 / visible |

This does **not** reopen the R339 bypass decision. That measurement turned the
curated and definitional skips off for EVERY row (11/20 Antifragile) and paid
ans_conciseness −0.163 and 2.4× latency. The bypass stays on for the canonical
first-turn questions it was built for; the exemption is scoped to the turn where
a static answer is structurally the wrong instrument, and it fires on 0 davidath
rows.

## Answer-level findings (deterministic path, real engine output)

### P13 — a denial of a prohibition suppressed the correct verdict

The verdict prepend is gated on `"Article 5" not in answer_text`. A sentence
DENYING the prohibition names Article 5 too, so the curated verdict was
discarded by the sentence contradicting it.

> Measured, `provider=cli`:
> gatekeeper hits `(('Art. 5', 'Art. 5.1.f'),)`; verdict prefix *"Emotion
> recognition in the workplace and education contexts is prohibited under
> Article 5(1)(f)…"*; shipped answer *"The system described is **not** among the
> practices prohibited under Article 5…"*.

A compliance lead acting on that answer would deploy a prohibited system.

The fix is **shape-based, never practice-based** — hard rule #3 forbids new
classification topics for the three PDF example questions and
emotion-recognition prohibition is one of them. Nothing in the guard names a
practice: it matches the GRAMMAR of a denial near an Article 5 anchor, and only
where `scan_for_prohibitions` has independently matched. An answer asserting
both "prohibited" and "not prohibited" would be worse than either, so the denial
is removed rather than argued with — only the sentences carrying it.

| question | guard OFF | guard ON |
| --- | --- | --- |
| emotion @ work | "not among the practices prohibited under Article 5 …" | "Emotion recognition in the workplace and education contexts is prohibited under Article 5(1)(f) …" |
| emotion @ school | same denial | same recovery |
| CV screening (gatekeeper does not fire) | — | byte-identical |

### P14 — a verbatim repeated sentence

> Measured: the GPAI answer ended *"Under Annex III, Eight high-risk use-case
> categories: biometrics, critical infrastructure."* **twice**.

`stitch_grounded_prose` has a near-duplicate guard, but it dedupes on the REF
while the final answer is assembled from several fragments — so two refs
resolving to the same KB stub each contributed the identical sentence through
different paths. A dedup pass now sits in the normaliser, where every path
converges. Exact match only (a near-duplicate can carry a different coordinate
and is a judgement call); first occurrence kept, so a verdict-first lead cannot
be displaced. `evals.regenold.runner` `sentence_cap` improved **140/255 →
146/255**.

## Verified working (fire checks, not assumptions)

* **Routing.** simple → `anthropic/claude-sonnet-5`, no reasoning; complex →
  `anthropic/claude-opus-5` with `reasoning.max_tokens=2048`. On Bedrock:
  `eu.anthropic.claude-sonnet-5` / `eu.anthropic.claude-opus-5` with
  `reasoning_config.budget_tokens=2048`, `temperature=1.0` and
  `maxTokens > budget` (the provider's contract for extended thinking).
* **Fallback.** OpenRouter down → chain → Bedrock serves, with thinking intact
  on the complex tier and dropped on a non-Claude rollover tier.
* **TurboQuant.** 373 BM25 docs (risk-docs ON, matching the documented count),
  corpus identity keyed, **0** stale rebuilds; `Art. 73` for "serious incident
  reporting deadline", `Art. 4` for "AI literacy obligations".
* **Cohere rerank.** Fires on **8/8** rows with the Stage-2 path on, 2 calls per
  request, per-request budget respected, `budget_blocked=0` (no starvation).
  `rerank-v4.0-pro`, `max_tokens_per_doc=16384`.
* **Graph mirror.** 110 nodes indexed, 658 units, 37 sub-points — matching the
  documented live Aura census.

## Gates

| gate | result |
| --- | --- |
| `pytest tests/` | **7005 passed, 17 skipped, 0 failed** (baseline 6935) |
| `evals.regenold.runner` | **255/255**, RISK_F1 macro **1.00**, `sentence_cap` 140→**146**/255 |
| OOS probe (`--oos-suite all`, 51 rows) | **49 pass, 0 scope leaks**, 2 known `adjacent_eu` soft fails |
| `ruff` | new files clean; `app/` unchanged at its pre-existing 200 |

## What is NOT measured, and the command that would measure it

Every answer-affecting change here ships behind an env gate with an exact
rollback, but **none has a `dynamic_ab` verdict**, because no live provider was
reachable. Per the validation policy these are the owed gates:

```bash
py -3.12 -m evals.harness.dynamic_ab --branch-env REGENOLD_CURATED_SKIP_CHALLENGE_EXEMPT=0 --label r376-challenge
py -3.12 -m evals.harness.dynamic_ab --branch-env REGENOLD_CHALLENGE_OBJECTION=0        --label r376-objection
py -3.12 -m evals.harness.dynamic_ab --branch-env REGENOLD_PROHIBITION_CONTRADICTION_GUARD=0 --label r376-prohibition
py -3.12 -m evals.harness.dynamic_ab --branch-env REGENOLD_KG_LOCAL_MIRROR=0            --label r376-mirror
```

Choose the probe pool by the gate's MEASURED FIRE RATE, not by reputation: the
challenge levers fire only on pushback turns, so a pool without them reports a
meaningless NULL — the inert-A/B trap arriving through the probe pool rather
than the harness.

The defaults are ON rather than OFF for the reason CLAUDE.md records:
`railway.toml [deploy.envs]` has never applied, so an env-gated default-OFF flag
never reaches the deployment at all. Each keeps a one-variable off switch.
