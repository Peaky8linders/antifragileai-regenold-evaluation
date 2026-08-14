# R337 — A/B of the R333 sub-point leaf signal, and the veto that would have rejected it

**Date** 2026-08-15 · **Harness** `evals.harness.dynamic_ab` · **Path** live, wrapper
(`openai_wrapper`, Stage-2 on) · **Lever** `REGENOLD_LEAF_BODY_SIGNAL`
(baseline = shipped default ON, branch = OFF) · **Artifact**
`evals/bench/results/dynamic-ab-r333-leafsignal.json`

## Result

```
probe pool: 32 rows (stratified across 7 sources)
  n=  8  changed=  3 (refs 3, answers 0)
  n= 16  changed=  5 (refs 5, answers 0)

=== r333-leafsignal — n=16 paired (stop: resolved) ===
  lever FIRED on 5/16 rows

  axis          baseline    branch     delta               95% CI  verdict
  ref_loose       0.8438    0.8438   +0.0000    [+0.0000,+0.0000]  NULL
  ref_strict      0.7275    0.7275   +0.0000    [+0.0000,+0.0000]  NULL
  ref_conc        0.6184    0.6184   +0.0000    [+0.0000,+0.0000]  NULL
  kw_recall       0.8452    0.8452   +0.0000    [+0.0000,+0.0000]  NULL

  gold_dropped_head         5 ->      5 (+0)
  gold_dropped_exact       10 ->      5 (-5)
```

The lever is **not** inert and the probe is **not** blind: refs changed on 5 of 16
rows, so R336's sensitivity control was never reached. Every scored axis is
exactly `+0.0000` with a CI of `[0, 0]`.

## What actually changed on those 5 rows

| row | gold (head-level) | ON — shipped | OFF |
| --- | --- | --- | --- |
| `multiarticle_r268:ma_01` | Article 13, Article 50 | Article 13, **Article 50.1, 50.2** | Article 13, Article 50 |
| `paper_tricky_v4:tp_v4_008` | Article 50 | **Article 50.2, 50.4** | Article 50 |
| `lower_risk_v149:lr_ctrl_recruitment…` | Article 6, Annex III | Article 6, Annex III, **Article 5.1.f** | …, Article 5 |
| `mt_v2:mt_v2_012` | Article 5 | **Article 5.1.f** | Article 5 |
| `lower_risk_v149:lr_video_game` | Article 5, 6, 50 | **Article 50.2**, …, **Article 5.1** | Article 50, …, Article 5 |

Every diff is the fix doing precisely its job: the leaf survives instead of being
collapsed into its umbrella head.

## ⚠ The veto that would have rejected a correct change

`gold_dropped_exact` went **10 → 5**, i.e. the shipped default appears to drop
**twice** the gold. Hard rule #8 makes `gold_dropped` a **VETO**, not an axis — so
read at face value this number rejects the change outright.

It is an artifact. Measured directly:

```
gold_dropped_exact(["Article 6.1"], gold=["Article 6"]) -> dropped_count 1
gold_dropped_head (["Article 6.1"], gold=["Article 6"]) -> dropped_count 0
```

The probe set's gold is **208 refs across 129 rows, 0 of them leaf-grained (0%)**.
Against head-level gold, exact-grain scoring counts a *more precise* citation as a
dropped head. So `gold_dropped_exact` does not measure "did we lose gold"; on this
probe set it measures "did we get more precise", with the sign inverted.

`gold_dropped_head` — the grain that is valid for this gold shape — is **+0**.
**Hard rule #8 is satisfied: zero gold dropped.**

This is CLAUDE.md's own rule biting in a new place: *"Gold shape decides which
reference formula is valid… scoring exact coordinates against head-level gold marks
a MORE precise citation as 0.0."* The rule was recorded about answer axes; it applies
to the **veto** too, and there it is more dangerous, because a veto is meant to be
read without argument.

**R337 closes this**: `dynamic_ab` now measures the gold's grain and, when no gold
ref carries a sub-point, labels the exact-grain veto `n/a (head-level gold)` instead
of printing a number that invites a wrong rejection.

## Remarks

**1. The A/B proves SAFETY, and cannot prove BENEFIT.** Both facts matter and they
are separate:

* *Safe* — 0 gold dropped at the valid grain, 0.0000 movement on all four axes with
  a degenerate CI, and no answer text changed (`answers 0` on every batch). The
  change is purely a reference-shape change, exactly as designed.
* *Unmeasurable here* — the four axes head-project via `article_heads`, so
  `Article 50.1` and `Article 50` are the same token to them. A harness whose gold
  has no sub-points and whose axes collapse sub-points is **structurally incapable**
  of scoring sub-point precision. The `+0.0000 / CI [0,0]` is not a null result
  about the lever; it is the instrument reporting a distinction it cannot represent.

The benefit was measured where the gold carries sub-points — the Antifragile expert
review, whose corrected gold demands `Annex IV.1(e)`, `Annex III.1(c)`,
`Article 99(4)`: **imprecise sub-point citations 11 → 3, citation precision
0.786 → 0.862**.

**2. Fired-but-flat is a distinct, useful state.** R336 taught this harness to
separate "the lever did nothing" from "the rows can't see it". This run adds a third:
*the lever fired, the rows saw it, and every axis is still exactly zero* — which
means the axes themselves cannot represent the change. The fire check confirms that
honestly rather than dressing `+0.0000` up as a null.

**3. `dynamic_ab` should not be the sole gate for a sub-point change.** Its probe
gold is 0% leaf-grained, so it will report NULL for any precision work while
correctly vetoing regressions. Pair it with the Antifragile run
(`evals.regenold.antifragile_bedrock`) whenever the change is about citation grain.

**4. Cheap and correct.** 16 rows, adaptive stop at `resolved`. The branch arm reuses
the cached `GraphRAGResponse` because the lever is **route-level** and deliberately
absent from `_engine_cache_key` — the asymmetry that makes a paired A/B possible at
all. Engine-level flags must be in the key; route-level flags must not.
