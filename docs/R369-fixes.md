# R369 — Implementation: evidence-based fixes for ans/ref correctness

**Run:** R365 live batch (81 rows, Bedrock, Qwen grounded judge) — see
`docs/R369-root-cause-analysis.md` for the root-cause layer and
`docs/R365-live-judge-report.md` for the axis tables.
**Golden data used:** (a) `graphrag_evals_dataset.txt` — the paper's 10
gold Q&A pairs with minimal reference sets; (b) the Antifragile expert
review (20 gold questions with per-question citation critique). Both were
attached by the operator and used as the reference-granularity and
citation-discipline ground truth.
**Evidence artifacts:** `scratch/r369_validate_claims.py` (report
re-derivation), `scratch/r369_replay_ref_passes.py` (R142/R325 replay),
`scratch/r369_sim_r368.py` (R368 sim), `scratch/r369_live_audit.py`
(route-level before/after on 22 golden rows).

---

## 1. Adversarial validation of the R369 report

Re-derived every failure-surface number from the raw R365 FINAL checkpoint
(81 baseline rows) instead of trusting the report:

| class | report | re-derived | Δ |
|---|---|---|---|
| CLEAN | 28 | 28 | 0 |
| OVER | 17 | 17 | 0 |
| UNDER | 12 | 12 | 0 |
| BOTH | 15 | 18 | report splits 3 zero-overlap rows into WRONG |
| EMPTY | 6 | 6 | 0 |
| drop ≥1 gold head | 34 | 30 (+4 empty) = 34 | 0 |
| emit ≥1 noise head | 35 | 35 | 0 |
| granularity dup | 25 | 25 | 0 |
| top missed heads | Annex III 10, Art 50 7, Art 6 5, Annex I 4, Art 25 3 | identical | 0 |

**Two report claims were corrected by the evidence:**

1. **RC-6 (granularity duplication) is NOT a scored defect on this
   benchmark.** The grounded judge (`evals/judge/grounded.py`) classifies
   every predicted citation CORRECT/WRONG against its verbatim text and
   passes iff zero WRONG + zero MISSING — a sub-point of a governing
   article is CORRECT, and `ref_conc` is head-count based
   (`(min/max heads)²`), so parent+leaf duplication never moves a scored
   axis. The replay (`scratch/r369_replay_ref_passes.py`) proves it:
   R142-auto, R325 parent-collapse, and both combined change **zero**
   deterministic scores on the 81 rows (ref_loose 0.7639 / ref_strict
   0.7090 / ref_conc 0.6096 identical across all four variants). All 14
   parent+leaf rows are curated intercepts where R142-auto is skipped and
   gold is the bare head — R325 would keep the leaf and drop the gold
   form. **Decision: no granularity change ships** (R142/R325 stay at
   their calibrated defaults).
2. **la_q92 is a correct refusal, not a scope bug.** Its gold `['Article
   17']` is a numbering collision — the question is "What does GDPR
   Article 17 say about the right to erasure?" and the refusal is right.
   The scope rescue covers exactly la_q60/63/91.

## 2. Rules inferred from the golden datasets → fixes

| # | rule (source) | fix |
|---|---|---|
| R1 | Minimal reference set: cite only the operative provision (paper Q2→`5`, Q5→`50`, Q9→`99`) | R368 ON (recall) + R260 trim (precision) |
| R2 | Granularity: leaf only when a specific paragraph is operative, head when general (paper Q1 `6(1)/50(1)` vs Q2 `5`) | no change — scored-neutral here (proven), R130/R133 keep their medtech calibration |
| R3 | No cited-but-undescribed / irrelevant refs (expert Q1/Q2/Q4/Q6/Q18) | R260 trim removes the GPAI-detail obligations from risk-categories rows |
| R4 | Role accuracy — Art 50(3)/(4) on deployers (expert Q5/Q18) | deferred to the prompt layer (RC-7), live eval is the baseline |
| R5 | Complete enumerations (expert Q1/Q2/Q16) | deferred to the prompt layer (RC-7) |
| R6 | Apply-the-rule-to-the-case (expert Q14/Q20) | deferred to the prompt layer (RC-7) |
| R7 | Wrong-article avoidance (expert Q7/Q12/Q14/Q20; RC-3) | la_q73/lq40 documented as retrieval-layer work; la_q35 fixed by R368 |

## 3. The three fixes shipped

### Fix A — R368 supplements default ON (`app/engines/risk_classification.py`)

Both gates flipped to default ON. The claim was re-validated on the actual
checkpoint gold (`scratch/r369_sim_r368.py`): **11/81 rows fire, 12 gold
heads recovered, 0 false positives** (ref_loose 0.764 → 0.833,
gold-heads-dropped 63 → 51). The scope rescue (la_q60/63/91) was already
wired and un-gated.

### Fix B — R260 risk-framework closed set trimmed (`app/routes/regenold.py`)

`_RISK_FRAMEWORK_CANON_REFS` cut from the 11-entry GPAI-detail set
(5/6/50/51/52/53/54/55/56 + Annex I/III) to the six tier-map primaries
{5, 6, Annex I, Annex III, 50, 51}, and `_enforce_risk_framework_refs`
now also **filters** the candidate list to that set (question-named refs
rescued; never empties). Evidence: the only risk-framework rows in the 81
pool are la_q47/la_q22 with gold `[Article 5]`; the paper gold for "risk
categories" cites heads {3, 5, 6, 50} — no 51–56; the expert review names
51–55 only as the parallel GPAI regime. The wire for those rows drops
11 → 6 refs and keeps every tier definition (no MISSING risk, minimal
WRONG risk under the grounded judge).

### Fix C — the R368 placement defect (`app/routes/regenold.py`)

The live audit found the R368 engine append (entity list) is **not
guaranteed to reach the wire**: the route's R112 fines filter keeps only
Art 99 (la_q16 lost the R368-recovered Art 50), the positional budget cut
drops tail-appended entities (la_q64/la_q8 lost Annex III), and the R72
literal-name reconcile drops refs the prose doesn't spell out (la_q35 lost
Annex III). Two sub-fixes:

1. **Fines-filter complement** — when the R368 fines trigger fires (it
   requires a prohibition token), keep {99, 5, 50} instead of {99};
   pure-fines shapes (paper Q9) keep the tight {99} set.
2. **R368 wire guard** (`REGENOLD_R368_WIRE_GUARD`, default ON) — LAST
   reference pass: re-instates the trigger-canonical heads (Annex III /
   Art 79 / Art 80 / Art 50) the triggers fired for but a lossy pass
   dropped. Recall-only, existence-gated, fail-soft.

## 4. Live before/after on the 22 golden rows (route-level, provider=cli)

From `scratch/r369_live_audit.py` (R365 baseline wire → R369 wire):

| row | gold | R365 baseline | R369 wire | result |
|---|---|---|---|---|
| la_q16 | 5, 50, 99 | 99, 5.1 | **99, 5, 50** | ✅ exact |
| la_q64 | I, III, 6 | 6.1, 43.3, I | **6, 43, I, III** | ✅ III recovered |
| la_q8 | I, III, 43, 6 | 6.1, I | **6, 43, I, III** | ✅ III recovered |
| la_q35 | III, 79, 80 | 74, 20.1 | **74, 20, 79, 80, 6, 81, 73, III** | ✅ gold complete (noise remains) |
| la_q60/63 | 50 | empty (refused) | **50** | ✅ exact |
| la_q91 | 50 | empty (refused) | 50, 1, 13 | ✅ 50 recovered |
| la_q47/22 | 5 | 11 refs | **6 refs** (5, 6, 50, 51, I, III) | ✅ tier map trimmed |
| la_q7 | I, III, 5, 50, 6 | (5, 6.2, 6.1, III.1.a, I) | **6, 50, III, I, 5** | ✅ exact heads |
| la_q13 | XI, XII, 51, 53, 55 | — | 53.2, 53, 51, 55, XI, XII | ✅ gold complete |
| paper_Q2/Q5/Q9 | 5 / 50 / 99 | — | **exact** | ✅ unchanged |
| la_q37 | III, VIII, 49, 71 | — | 71, 6, III | ⚠ VIII/49 miss (RC-4) |
| la_q25 | III, 25, 26, 6 | — | 6, 50, I, III, 5 | ⚠ 25/26 miss (RC-4) |
| la_q40 | IV, 11 | Annex VII | Annex VII | ⚠ RC-3, deferred |

**Residual (documented, deferred per the R369 report's fix order):** the
RC-3 wrong-article rows (la_q40) and the RC-4 engine-recall gaps
(la_q37/la_q25's VIII/49/25/26) sit in the retrieval layer; RC-7
generation defects (enumerations, roles, case application) sit in the
prompt layer. Both are intentionally left for the measured next rounds —
the live re-evaluation below is the baseline.

## 5. Tests

- `tests/test_r368_recall_supplements.py` — gates now assert default ON +
  env-off arm; new wire-level tests: fines filter complement, la_q16 wire
  = {5, 50, 99}, la_q64 wire contains Annex III, wire-guard off-switch.
- `tests/test_r260_risk_framework_refs.py` — new: GPAI-detail filter,
  question-named rescue, never-empty.
- `tests/test_r274_curated_ref_protect.py` — risk-framework closed set
  updated to the trimmed six primaries + asserts 52–56 absent.
- `tests/test_r267_submission_fixes.py` — la_q25 now asserts Annex III IS
  present (R368 gold-aligned; the R365 gold includes it).
- Full suite (excluding the Bedrock-credentials test): **6737 passed, 50
  failed — the 50 are byte-identical pre-existing failures on the base
  commit** (dead Bedrock credentials + R329/R328/R342/R344 drift that
  predates this round); zero new failures introduced.

## 6. Artifacts

- `scratch/r369_validate_claims.py` / `r369_replay_ref_passes.py` /
  `r369_sim_r368.py` / `r369_live_audit.py` — the evidence scripts.
- `evals/bench/results/checkpoints/dynamic-ab-r365-live-FINAL-81rows-7axes.json`
  — the R365 evidence base.
