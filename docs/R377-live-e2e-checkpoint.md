# R377 — live end-to-end checkpoint (OpenRouter + restored Aura)

**Date:** 2026-08-23 · **Base:** `f831145` (R376 merged) · **Branch:** `main`

Running record of the live validation session. R376 shipped its whole provider /
graph / pushback change set against **mock** servers, because no external
provider was reachable from that container. This round re-ran it against the
real ones. Everything below was executed, not inferred.

## Instrument — what was actually reachable this time

| surface | status |
| --- | --- |
| OpenRouter | **live**, key valid, 421 models. `anthropic/claude-opus-5` and `anthropic/claude-sonnet-5` both resolve and answer |
| Bedrock (`eu-central-1`) | **live**, key on the OLD entitlement — see below |
| Neo4j Aura | **restored mid-session** to a NEW instance, `368fd9ef` (the previously recorded `0644b854` is NXDOMAIN — deleted, not paused) |
| Cohere | reachable, but the key **429s** on `/v1/embed` |
| Railway app | reachable, serving `6c076bf5c680` — i.e. **R376 is not deployed** |

### Bedrock entitlement, measured

Real 5-token invokes, `eu-central-1`, current `.env` key:

| profile | result |
| --- | --- |
| `eu.anthropic.claude-opus-5` | **DENY 403** (`api_access_denied_403`) |
| `eu.anthropic.claude-sonnet-5` | **DENY 403** |
| `eu.anthropic.claude-opus-4-8` | **DENY 403** |
| `eu.anthropic.claude-opus-4-6-v1` | OK (1409 ms) |
| `eu.anthropic.claude-sonnet-4-6` | OK (1004 ms) |

So the R328.2 picture is unchanged: **the Bedrock fallback cannot serve Opus 5
or Sonnet 5 with this credential.** It degrades within the Claude family to
`opus-4-6-v1` / `sonnet-4-6`, exactly as `complete_with_fallback` is built to.
"OpenRouter Opus 5 primary with a Bedrock fallback" holds for the primary and
**one tier down** for the fallback until the ABSK key is re-minted.

### Aura, after the snapshot restore

`GET /healthz/graph?deep=1` → `graph_ok: true`, `served_by: "graph"` (not the
R376 local mirror), `elapsed_ms` 919.

```
Article 113  Annex 13  Paragraph 658  Point 421  SubPoint 37  Recital 180
Definition 68  Obligation 113  Practice 8  AnnexIIICategory 8  OperatorRole 8
LifecyclePhase 4  RiskLevel 4  RiskScenario 8  RiskControl 9  GPAIModelProfile 4
ConformityRoute 3  FRIAWorkflow 1  SeriousIncidentSLA 3  Dimension 26
Question 94  Guideline 4  LegalInstrument 1  KBMetadata 1
```

1789 nodes / **2156** edges / 24 labels. All **7 VECTOR indexes ONLINE** plus
`ft_provision_prose` FULLTEXT. `seed_version 2026-08-08-r323-annex-sections`,
`kb_version 2024.1689.v18` (repo is v21 — the documented seed gap, unchanged).

⚠ Two deltas against CLAUDE.md's recorded census, both to reconcile:
`HAS_RISK_CLASS_OBLIGATION` is **80** here (R371 wrote 90; R371.6 deleted 16,
which should leave 74), and total edges are **2156** vs the documented 2166.
The snapshot appears to predate part of the R371.6 cleanup.

## The graded turn was completely broken, and now is not

**R377-A — a complete XML-channel answer read as truncated.** Fixed in `0f76fa0`.

The V2 output contract and `USER_CHALLENGE_BREVITY_CLAUSE_V2` instruct the model
to put its clean answer inside an `<answer>` channel when re-deriving under a
challenge. `prompt_guard.split_reasoning_and_answer` unwraps it — but that runs
on the ROUTE side, **after** the provider-level guard, which sees raw text. A
correct answer therefore ends on `>`, which is not in `.!?`, so
`_looks_structurally_truncated` returned True.

Measured on the emotion-recognition pushback turn: a complete, correct Sonnet 5
answer ending *"...remains prohibited regardless of written employee consent."*
plus the closing tag was discarded, and then **every model on both providers
"truncated" identically** — `claude-opus-5`, `claude-sonnet-5`,
`claude-opus-4-6-v1`, `qwen3-235b`, `nemotron-super`, `devstral`. Both chains
exhausted; the route shipped a 2538-char deterministic dump of unrelated
Article 5 carve-outs (real-time RBI, social scoring, biometric categorisation,
minors) that never engaged the consent argument.

Six models failing the same way is a detector fault, not six model faults.

## The complex question was answered wrongly, and now is not

**R377-B — the fidelity guard enshrined a WRONG deterministic tier.** Fixed in
`bc44bfb`. On the
complex CV-screening + GPAI question, Stage-2 (Opus 5, 2048 thinking) produced a
correct 2183-char answer — *"high-risk ... Annex III ... Article 6(2) ...
provider under Article 25(1)(c)"* — with zero citation drift and a complete
final sentence. `stage2_fidelity.guard_cross_tier_polish` returned
`fallback_tier_drop` and replaced it with the deterministic draft, which says
*"classified as limited-risk under the Article 50 transparency obligations"*.
Executed directly: `out == kg_answer` is True, `out == polish` is False. The
R146 guard's doctrine is "the deterministic Stage-1 draft is the CONTENT source
of truth" — which is right when that draft is grounded and catastrophic when it
is a default.

The fix is on the CONTRACT side only: a tier the draft DENIES is not a tier the
polish must preserve. `extract_tier_set` is left byte-identical because "is this
tier ADDRESSED" remains the right question for the POLISH.

## Found and recorded, not yet fixed

**R377-C — Annex III(4) markers are brittle literal substrings.**
`_detect_risk_level("Our AI ranks job applicants for employers.")` → `None`.
`_detect_risk_level("We screen CVs and rank job applicants.")` → `None`.
Only the literal `"cv-screening"` / `"recruitment"` forms hit. Likewise
`_detect_gpai_signal` requires the literal `"general-purpose ai"`, so
*"fine-tune a third-party general-purpose model"* → `False` while
*"...general-purpose AI model"* → `True`.

**R377-D — the unclassified default is `"limited"`** (`scenario_classifier.py`
:1425, described at :1384 as "the conservative 'limited' tier"). In the Act's
pyramid that is the second-**lowest** obligation tier, so an unrecognised
scenario is told a transparency notice suffices. For a compliance product that
is the worst failure direction. A second default at `_graph_rag_impl.py:7273`
and `:7570` (`query.risk_context or risk_level or "high"`) goes the OTHER way —
one concept, two definitions, opposite directions.

**R377-E — richer questions retrieve worse.** The long CV+GPAI question parses
to `entities=['Art. 43']`, `risk_context=None`; its own short sub-question
parses to `['Annex III','Art. 10','Art. 42','Art. 6','Art. 40']` with
`risk_context='high'`.

**R377-F — the risk_context detector is `"high" in q and "risk" in q`**
(`_graph_rag_impl.py:2900`), so *"what risk class applies"* yields `None`.

**R377-G — Cohere 429 on `/v1/embed`** at startup → `turboquant_index: external
embeddings returned None, falling back to SVD path`. The committed `_assets`
and the live query path may therefore be on different embedding bases.

**R377-H — Neo4j deprecation:** `db.index.vector.queryNodes` is deprecated in
favour of `SEARCH` on the restored instance. Not yet breaking.

## Live routing — verified working

Turn 1 of the emotion conversation, uncached, 13 861 ms:

```
stage2_model=anthropic/claude-sonnet-5 provider=openrouter complex=False
kg_context sections=5 refs=16
answer_route=synthesis:synthesis_default
refs = ['Article 5.1.f', 'Article 5']
```

> Prohibited. Article 5(1)(f) bans the placing on the market, putting into
> service, or use of AI systems to infer the emotions of a natural person in the
> workplace, and a performance review meeting falls within that area. ...

Correct, verdict-first, 796 chars, and the graph contributed 5 sections / 16
refs. The simple tier, the model pin and the KG wiring are all doing what the
operator asked for.

The challenge turn correctly gated complex and delivered the objection —
`complex_tier_forced_challenge_turn`, `challenge_objection_delivered
quoted=True chars=173`, `stage2_model=anthropic/claude-opus-5 ... complex=True`,
`openrouter_thinking_budget=2048` — so the three R376 pushback fixes (P10/P11/
P12) are all firing live. It was the truncation detector downstream of them,
not the routing, that destroyed the turn.

## Live re-test after the two fixes

Same conversations, same env, uncached.

| | before | after |
| --- | --- | --- |
| pushback turn latency | 78 047 ms | **14 969 ms** |
| pushback Stage-2 | `False` — both chains exhausted | **`True`**, no fallback hop |
| pushback answer | 2 538 chars of unrelated Article 5 carve-outs | 812 chars rebutting consent directly |
| complex question | 516 chars, **"limited-risk"** (wrong) | 2 466 chars, **"High-risk"** (correct) |

The pushback answer now reads *"Consent of the employees is not a condition of
that prohibition and cannot make the practice lawful ... The deployer
transparency duty ... under Article 50(3) applies only to permitted uses and
does not cure a prohibited practice."* That is precisely the failure mode the
R376 record described as *"reads as permitted if you disclose"*.

The complex question now answers all four of its sub-questions: high-risk via
the Annex III employment use case with the Article 6(3) derogation ruled out on
profiling; provider, including Article 25(1)(c) for the fine-tune and the
Article 25(4) written agreement; the Article 43 internal-control route with no
notified body; and the documentation set (Articles 11, 17, 12, 47, plus 72/73).

The second pushback conversation (CV-screening, "our vendor says we're exempt
… and we're a small company") is also correct on both turns, rebutting the
human-in-the-loop claim on Article 6(3) profiling and the size claim on the
absence of any size threshold, with precise Article 26 sub-paragraphs.

## Gates

| gate | result | baseline |
| --- | --- | --- |
| `pytest tests/` | **7048 passed, 17 skipped, 0 failed** | 7032 (R376) |
| `evals.regenold.runner` | **247/255**, RISK_F1 macro 0.96 | **247/255 at `f831145`** — measured in an isolated worktree with the same `.env`; the change is exactly neutral |
| OOS probe (`--oos-suite all`, 51 rows) | 24 pass / 26 leak | **25 pass / 25 leak at `f831145`** — same env, so ≤1 row, inside observed variance |

⚠ **Neither the runner nor the OOS probe can be read against CLAUDE.md's
documented 255/255 and 49/51 right now.** Both were measured here with the real
`.env`, whose Groq daily token quota is **exhausted** (`api_status_429 ... tokens
per day (TPD): Limit 200000`). CLAUDE.md's own gotcha covers this: the denoiser
/ topic-filter / safety-gate cluster changes behaviour on `GROQ_API_KEY`
(measured 63 vs 92 failures on one commit). That is why both gates were re-run
at the **pre-R377 base in an isolated worktree with the same `.env` copied in**,
which is the only comparison that means anything here. Against that baseline the
two fixes are neutral.

The `sentence_cap` sub-metric ranged 156–159 across runs at BOTH commits, so it
is not a stable discriminator in this environment.

## Owed, not run

Per the validation policy these changes are answer-affecting and owe a
`dynamic_ab` verdict, which was not run: the account's Groq quota is spent and a
judge-graded A/B needs a working judge transport.

```bash
py -3.12 -m evals.harness.dynamic_ab --branch-env REGENOLD_FIDELITY_TIER_NEGATION=0 --label r377-tier-negation
```

There is no env gate for the XML-channel truncation fix, deliberately: a
complete answer being read as truncated is a detector fault, not a policy
choice, and both providers' chains exhausting on it is not a behaviour worth
keeping switchable.

⚠ **Choose the probe pool by measured fire rate.** The tier-negation lever only
fires where a deterministic draft DENIES a tier it also anchors, and the
truncation fix only fires on XML-channel answers, i.e. challenge turns. A pool
without pushback rows reports a meaningless NULL.

## Deployment preconditions — READ BEFORE TRUSTING THE DEPLOY

`railway` CLI is present but unauthenticated here, so the service variables
could not be read or set. Three of them decide whether any of this works live:

1. **`NEO4J_URI` must be repointed to the NEW instance.** The recorded
   `0644b854` is NXDOMAIN. Until Railway's variable is updated, production runs
   with a dead graph and serves the R376 local mirror — hierarchy and sub-points
   only, no semantic layers, no recital anchors.
2. **`P2P_GRAPH_RAG_PROVIDER` must be `openrouter` or `auto`**, with
   `OPENROUTER_API_KEY` set, or Stage-2 does not run on the tier this round
   validated.
3. **The ABSK Bedrock key is on the old entitlement.** The fallback works, but
   one tier down (`opus-4-6-v1` / `sonnet-4-6`), never Opus 5.
