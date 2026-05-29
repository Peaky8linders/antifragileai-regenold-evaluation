# R95 — fresh-session handoff (next steps + fixes)

Carries forward from **R94** (branch `r94-citation-faithfulness-bugs`,
committed `32ece83`, merged latest `origin/fix/issue-150-cache-history-depth`
= `f7dbefe` / #151). R94 closed the 3 R93-judge-surfaced bugs; this doc
records the fresh live measurement that followed and the prioritized
next-round work.

## R94 outcome (shipped + validated)

- **Bug 1 spurious Art. 52** — Art. 52 KB summary carried two incidental
  high-IDF tokens ("permitted", "planning") the BM25 fallback false-matched.
  Reworded. **0 residuals / 192 fresh-200 rows + 0 / 122 live rows.**
- **Bug 2 Art. 5 RBI "Member-State opt-in" misframe** — soft-cap dropped the
  non-cite prohibition enumeration, kept the misleading cite-anchored tail.
  Reworded prohibition-first (vs official Art. 5(5)). **0 residuals.**
- **Bug 3 truncated/dangling sentences** — `augment_with_ref_descriptions`
  hard-cut a stub at 90 chars + run-on joins. Abbreviation-aware
  complete-clause path + clause terminators, gated `REGENOLD_CLAUSE_COMPLETE`
  (default OFF → davidath byte-identical; ON in railway.toml). **0 dangling /
  122 live rows.**
- Gates: davidath **byte-identical** (Ans Strict 0.3307, Ref 0.5797/0.4696/
  0.4202, Tone 1.0, MT 20/20), OOS **21/21**, 276 **100%**, pytest **3109
  pass / 1 skip** (post-merge).

## Fresh live judge — representative-100 (122 rows), Claude Max wrapper, Stage-2 ON, production config (`REGENOLD_CLAUSE_COMPLETE=1`)

Sidecar: `evals/bench/results/representative-100-r94-live.json`
Judge:   `evals/bench/results/judge-r94-live-full.json`

| Axis | raw | over-non-error | note |
| ---- | --- | -------------- | ---- |
| Correctness | 0.189 | **0.299** | ⚠ 45/122 rows are wrapper TIMEOUTS, not engine fails (67 retries, 24% recovery) — unreliable, re-measure |
| Refs | 0.352 | **0.371** | weak axis; "cited but never described" over-citation |
| Conciseness | 0.574 | **0.574** | residual >4-sentence / mid-enumeration truncations |
| Tone | 0.918 | **0.918** | strong — R94 truncation + R93 third-person work held |

Token-overlap harness (same run): Ans Strict 0.3734, Ref Loose 0.5464,
Ref Strict 0.3859, Tone 1.0, latency p50 ~10.2 s.

**Comparison caveat (memory `reference_live_wrapper_eval_workflow`):** these
are fresh absolutes, NOT a two-run diff (Sonnet non-determinism confounds
row-level A/B). Against the closest historical rep-100 judge runs in
CLAUDE.md (r80.1-live Stage-2-ON: corr 0.659 / refs 0.305 / tone 0.897 /
conc 0.448), R94 is **refs +0.07, tone +0.02, conciseness +0.13** — but
correctness is not comparable here because of the 45-row timeout deflation.

## R95 prioritized fixes

### P0 — over-citation noise anchors (refs 0.371, dominant weak axis)
Deterministic over-citation analysis (122 live rows, 65 miss ≥1 gold):
non-gold anchors surfaced **Art. 6 ×29, Art. 3 ×13, Art. 51 ×11**, then
Art. 5/15/25/27/55/53. Judge refs failures are overwhelmingly "Article N
cited but never described in prose" (Art. 98, 43, 10, 3, 53, 22, 27…).
- Root: BM25 fallback + R81 entity-boost over-surface topic anchors on
  questions where they are not the gold (the "high-risk AI system" → Art. 6
  bleed; Art. 3 definitions noise; Art. 51 GPAI bleed).
- Approach: **tighten the SOURCE, not post-hoc prune** — R90 proved the
  `cite_describe_guard` prune is −0.21 ref_loose on the competition bench.
  Candidates (each davidath-A/B'd, env-gated):
  - Suppress **Art. 3** from candidates unless the question is definitional
    (qtype DEFINITION / "what is/means/defined").
  - Suppress **Art. 51** unless GPAI signal present (FLOPs / GPAI / systemic).
  - Demote **Art. 6** when a more-specific operator/topic article fires
    (R77 removed the bare "high-risk" keyword; Art. 6 still rides the
    "high-risk AI system" phrase via BM25/entity-boost).

### P1 — transparency_disclosure wrong retrieval (correctness + refs)
Chatbot/disclosure questions ("do we have to tell users they're talking to
an AI?") surface Art. 5/49/51 and lead with the RBI prohibition instead of
**Art. 50** (gold). Judge: "wrong topic cited; Art. 50 transparency
obligation absent". `transparency_disclosure` Ans Strict 0.265.
- Fix: route disclosure/chatbot/deepfake transparency shapes to Art. 50
  (KEYWORD_TO_ARTICLE / scope anchor or a topic-router rule). davidath-A/B.

### P1 — residual conciseness truncation (>600-char Stage-2)
Conciseness fails: "sentence count exceeds 4", "single run-on sentence
truncated mid-…", "truncated incomplete sentence ending mid-enumeration".
R94 fixed the deterministic 90-char augmenter clip; the **>600-char Stage-2**
case (the user's original bug-3 hypothesis) remains.
- Fix: A/B enable **`REGENOLD_HARD_CHAR_CAP`** (R78 knob, default OFF;
  truncates at a clean clause boundary). Live-only win per R78; davidath wash.
  Validate via a fresh live judge conciseness read.

### P2 — clean correctness re-measurement (BLOCKER for a reliable correctness read)
45/122 correctness rows timed out (wrapper rate-limit thrash on the ~1 hr
full-batch run). Correctness 0.299 is on 77 rows and noisy.
- Re-judge correctness with higher concurrency / smaller clean sample, or a
  faster judge provider. Per memory `rule_eval_provider`, evals go through
  the wrapper — so batch in chunks or raise the wrapper `RATE_LIMIT_CHAT_
  PER_MINUTE` for the run.

### P2 — targeted correctness misses (from judge failure modes)
- Registration mis-cited as **Art. 71** instead of **Art. 49** (gold keyword).
- GPAI: omits **notification to the European Commission + timeframe**.
- "which oversight body?" → does not identify the **EU AI Office** (Art. 64).
- Importer liability under **Art. 23** omitted on a liable-party question.
Each is a narrow KB/routing fix; low blast radius, davidath-A/B each.

## Discipline reminders (carry into R95)
- davidath byte-identical or net-positive (`evals.bench.runner`); OOS 21/21
  (`runner_v2 --local --probe-oos`); 276 100% (`evals.regenold.runner`).
- Gate risky changes env-default-OFF, flip ON in railway.toml (R89A).
- KB edits → bump `KB_VERSION` + update `tests/_snapshots/kb_version_signature.txt`
  (CI lint `test_kb_consistency.py::TestKBVersionSnapshot`).
- Live evals via the Claude Max wrapper only (memory `rule_eval_provider`);
  report fresh absolutes, never a two-run diff (Sonnet non-determinism).
- `scenario_classifier.py` is R33 load-bearing — touch with care.
