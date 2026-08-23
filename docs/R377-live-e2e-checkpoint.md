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
"OpenRouter Opus 5 primary with a Bedrock fallback" is真 for the primary and
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

## The other live defects found (fixes in progress)

**R377-B — the fidelity guard enshrines a WRONG deterministic tier.** On the
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

## Gates run so far

| gate | result |
| --- | --- |
| `pytest -k "truncat or structural or r357 or r328"` | **156 passed**, 0 failed |

Full suite, `evals.regenold.runner`, OOS probe and the owed `dynamic_ab` runs
are pending and recorded here as they complete.
