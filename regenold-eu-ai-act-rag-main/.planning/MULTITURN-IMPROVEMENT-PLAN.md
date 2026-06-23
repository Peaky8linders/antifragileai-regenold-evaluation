# Multi-turn Improvement Plan (grounded in the R106 live failure rows)

## Why now
Live R106 (Sonnet via tunnel) multi-turn coherence ≈ **0.42**, refL ≈ **0.42** —
the weakest axis on every set, while single-turn refL is 0.62–0.78 and tone is
1.0 everywhere. The fix surface is multi-turn, not retrieval-in-general.

## Diagnosis — what actually failed (24 multi-turn rows, PV3+PV4)

| Bucket | Rows | Signature | Root cause |
| ------ | ---- | --------- | ---------- |
| **A. Scope-gate over-refusal** | 6 (mt_v4_001/002/007/010/012, mt_v3_010) — **~25%** | `is_refusal=True`, pred=`None`, refL=0, kw=0 | Final turn is an in-scope follow-up with **no AI-Act anchor keyword**; the existing coreference rescues don't fire → hard refuse |
| **B. Retrieval drift / wrong-anchor** | ~5 (mt_v3_011 Art10→50, mt_v4_009 Art73→72, mt_v3_007 Art86→26/14, mt_v3_001 Art50→4/113, mt_v3_004 Art5→6) | answered, but cites a topic-neighbor not the target | Final turn resolved against the wrong article; no fact-state carry-forward |
| **C. Over-citation** | ~4 (mt_v4_004 8 refs/1 gold, mt_v3_006/009 10 refs/2 gold) | refL=1.0 but ref_strict/conciseness low | HRAIS chain-expand + 2-hop fire on multi-turn finals where gold is 1–2 articles |
| **D. Keyword shortfall** | ~2 (mt_v4_008, mt_v3_009) | refL=1.0, kw<0.5 → `coherent=False` | Right refs, but the answer doesn't surface the gold key-points |

Bucket A is the prize: 6 rows at a hard zero. Fixing them lifts multi-turn
refL ~0.42→~0.60 and coherence ~0.42→~0.65 on its own.

## Root cause of bucket A (the dominant one)
`scope.classify_conversation` only rescues a coreferent final turn when:
- a prior **USER** turn established an explicit article anchor (R55-E/R57-A), **or**
- a prior **assistant** turn literally cited an article (R73), **or**
- the final turn is a short "borrow-the-anchor" shape (`_live_question_borrows_anchor`).

It does **not** rescue when prior turns established in-scope-ness via *topic/facts*
without ever naming an Article (e.g. mt_v4_001: turns 1–2 = "internal meeting-summary
tool → minimal-risk", turn 3 = "now it reads employees' facial expressions to score
engagement — does anything change?"). No prior anchor, no anchor keyword in the final
turn → refuse. But this is plainly in-scope (and should re-classify to Art 5(1)(f)).

## Interventions (ranked by leverage)

### P1 — Conversation-level scope "stickiness" (fixes bucket A) ⭐ highest
Once any **prior user turn** in the conversation was classified **in-scope**, treat the
conversation as established-in-scope: subsequent turns are **not hard-refused** — they
pass to retrieval — UNLESS the final turn is a clear hard-switch to another framework
(the R49-B `near_oos` DSA/NIS2/PLD detectors still refuse) or an off-domain topic.
- Mechanism: add `prior_user_in_scope` (derived from prior USER turns' own scope verdicts,
  **not** assistant content — preserves the R34-P1 history-injection hardening) as a rescue
  signal alongside `prior_anchors`.
- Guardrails: keep `near_oos` refusals; re-run the 21/21 OOS probe + the injection-spoof
  tests; the rescue is gated on a prior **in-scope user turn**, so a fresh off-topic
  conversation is unaffected.
- Expected: 6 refusal rows → answered; multi-turn refL +~0.18, coherence +~0.23.
- Risk: medium (scope is security-sensitive). Env-gate `REGENOLD_MT_SCOPE_STICKY`.
  **davidath-neutral** (single-turn QA never hits the multi-turn rescue).

### P2 — Re-classify the *resolved* final turn (fixes A's risk-flip + part of B)
Run the prohibited-gatekeeper + scenario-classifier + general-verdict on the **R86
denoised/standalone** final turn, not the raw flattened blob (where an earlier
"minimal-risk" assistant turn dilutes the new Art-5 signal).
- Prereq (code-confirm): trace whether the gatekeeper/classifier currently run on the
  flattened question or the live turn, and where the R86 denoiser output is available.
- Verify the gatekeeper's Art-5 keyword set covers "emotion recognition / facial
  expressions / engagement scoring / workplace" and "biometric categorisation".
- Expected: the Art-5 fact-pattern-shift rows (mt_v4_001/012, mt_v3_004/010/012) resolve
  to Art 5; lifts both refL and kw. Env-gate `REGENOLD_MT_RECLASSIFY`.

### P3 — Fact-state carry-forward (fixes bucket B drift)
Accumulate a lightweight per-conversation state — `{role, risk_tier, domain,
named_articles}` — across turns and seed it into retrieval on the final turn. R88-A
inherits prior *cited articles*; this also inherits prior *facts* (role/risk/domain)
when no article was cited.
- Example: mt_v4_002 turns establish "high-risk CV-sorting provider, risk-mgmt + data-gov
  done" → final "what conformity procedure?" should seed Art 43 from (high-risk + provider
  + pre-market) even though "Article 43" was never said.
- Expected: recovers the obligation-continuation + drift rows. Env-gate `REGENOLD_MT_FACTSTATE`.

### P4 — Multi-turn precision: cap chain-expansion (fixes bucket C)
Gate the HRAIS chain-expander + Neo4j 2-hop **OFF** for multi-turn finals unless the final
turn has explicit listing intent ("which articles…"). On multi-turn the gold is usually
1–2 articles; the R87-B budget=22 over-cites.
- Expected: ref_strict/conciseness up on mt_v4_004 / mt_v3_006 / mt_v3_009. Low risk.

### P5 — Keyword surfacing on multi-turn finals (fixes bucket D, cheap)
Force the describe-every-cite augmenter ON for multi-turn (`REGENOLD_R89A_FORCE_APPEND`
already exists) so a correctly-cited article carries its gold-keyword tokens into the
answer. Coherence is keyword-bound (≥50% gold keywords) — this flips refL=1/kw<0.5 rows.

### Cross-cutting note
R97 already routes multi-turn → Sonnet. Sonnet cannot cite an article retrieval never
surfaced, so **P1–P3 (retrieval/scope) are the real levers**; P5 is answer-side. Order
matters: scope first (P1), else the other fixes never run on the refused rows.

## Sequencing & measurement
1. **P1** (scope stickiness) — biggest cluster, ship + measure first.
2. **P5** (keyword force-append) — cheap, compounds.
3. **P2** (re-classify resolved turn) — needs the denoiser/gatekeeper code-confirm.
4. **P3** (fact-state) — larger build.
5. **P4** (precision cap) — last, tunes ref_strict once recall is up.

- **Eval surface:** the 49 multi-turn convos (PV3 12 + PV4 12 + V2 25), run **live**
  (Sonnet via tunnel) — A/B each intervention; the deterministic bench can't score
  Stage-2 coherence.
- **Targets:** multi-turn coherence 0.42 → **0.65+**, refL 0.42 → **0.60+**, tone held at 1.0.
- **Regression guard:** every intervention env-gated + **davidath byte-identical**
  (single-turn QA never enters the multi-turn paths) + **OOS 21/21** + the
  history-injection spoof tests (P1 is scope-touching).

## Prerequisite code-confirm steps (before coding)
1. Where do gatekeeper / scenario-classifier / general-verdict run — flattened blob vs
   resolved/denoised final turn? (drives P2)
2. Exact current rescue conditions in `scope.classify_conversation` + how `prior_anchors`
   is built (drives P1).
3. Is the R86 query-denoiser output reused downstream, or only for retrieval scoring?
4. Confirm the 6 bucket-A final turns are genuinely anchor-less (vs a keyword the map
   simply lacks — some may be a cheap `KEYWORD_TO_ARTICLE` add instead of P1).
