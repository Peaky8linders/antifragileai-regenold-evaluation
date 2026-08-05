"""R281 — offline gold-bearing simulator for reference-precision changes.

WHY THIS EXISTS
---------------
The over-citation defect is a PRECISION defect (measured R281: 97.2% of our
excess refs are entirely non-gold distinct heads). The live pairwise
``evals.harness.ab_judge`` is the project's merge gate for answer-quality
changes (CLAUDE.md hard rule #6) — but its **refs axis cannot see precision**:

    evals/harness/pairwise_prompts.py::render_refs asks
    "which answer's PROSE more faithfully describes the articles it cites ...
     and cites the load-bearing gold articles?"

i.e. faithfulness + RECALL, with no minimality/precision term. Dropping a
non-gold ref earns nothing there; dropping a gold ref is punished. That is
exactly why R142.1's positional clamp lost 11-0 — and why that instrument
would reject ANY precision fix, correct or not.

The competition, by contrast, scores references against gold on axes that DO
reward precision. Verbatim from the official rules PDF
(``docs/2026-eu-ai-act-competition-rules_official.pdf``):

    "references (list[str]): Should contain the minimal set of relevant
     references."
    "Is the answer sufficiently concise? ... Similarly, the amount of
     proposed references is checked against ground-truth ones."

So a ref-count change is scored twice: Ref Correctness Strict (F1 — precision
term) and Ref Conciseness (count ratio). This module scores a candidate
transform against those axes on a gold-bearing live sidecar, deterministically
and with no LLM in the loop.

SCOPE / HONESTY
---------------
* This is the RIGHT instrument for a ref-SET change and the WRONG one for an
  answer-TEXT change (it cannot see prose quality). It does not replace
  ab_judge — it complements it. Ship a ref-precision change on THIS plus an
  ab_judge no-regression check on correctness/tone.
* Ref Correctness Loose (recall) is the GUARD: the R142.1 failure mode is
  dropping gold. Any candidate that reduces recall is rejected regardless of
  its F1/conciseness gain.
* The probe gold here is head-form; regenold's own example gold is sub-point
  form (``["Annex IV.2","Article 3.1"]``). That mismatch does NOT invalidate
  this instrument for the measured defect: 97% of the excess is entirely
  NON-GOLD ARTICLES, and dropping a non-gold article improves precision at
  either granularity.

USAGE
-----
    from evals.bench.ref_precision_sim import simulate, load_sidecar
    rows = load_sidecar("evals/bench/results/easyhard-r279-live.json")
    simulate(rows, my_transform, label="my-fix")

A transform is ``(pred_refs, row) -> new_pred_refs`` and must be pure.

CLI:
    .venv/Scripts/python.exe -m evals.bench.ref_precision_sim --sidecar <path>
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from collections.abc import Callable
from typing import Any

from evals.bench.metrics import (
    article_heads,
    reference_conciseness,
    reference_correctness_loose,
    reference_correctness_strict,
)

Transform = Callable[[list[str], dict[str, Any]], list[str]]

# Marginal leverage of each axis on the official Overall (a plain geometric
# mean of the 8 axes), measured at our official operating point in
# .planning/R276-PLAN.md: pp of Overall per +1pp of the axis.
_LEVERAGE = {"ref_strict": 0.163, "ref_conc": 0.121, "ref_loose": 0.113}


def load_sidecar(path: str) -> dict[str, list[dict[str, Any]]]:
    """Load an easy/hard live sidecar into {"easy": [...], "hard": [...]}."""
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    return {
        "easy": d.get("easy_rows") or [],
        "hard": d.get("hard_rows") or [],
    }


def _score(rows: list[dict[str, Any]], transform: Transform | None) -> dict[str, float]:
    """Score a split on the three gold-bearing reference axes."""
    loose: list[float] = []
    strict: list[float] = []
    conc: list[float] = []
    n_pred = 0
    n_gold = 0
    gold_lost = 0

    for row in rows:
        pred = list(row.get("pred_refs") or [])
        gold = list(row.get("gold_refs") or [])
        new = list(transform(pred, row)) if transform else pred

        # GUARD: gold that we HAD retrieved but the transform removed.
        gold_heads = article_heads(gold)
        had = article_heads(pred) & gold_heads
        kept = article_heads(new) & gold_heads
        gold_lost += len(had - kept)

        loose.append(reference_correctness_loose(new, gold))
        strict.append(reference_correctness_strict(new, gold))
        conc.append(reference_conciseness(new, gold))
        n_pred += len(article_heads(new))
        n_gold += len(gold_heads)

    return {
        "n": len(rows),
        "ref_loose": st.mean(loose) if loose else 0.0,
        "ref_strict": st.mean(strict) if strict else 0.0,
        "ref_conc": st.mean(conc) if conc else 0.0,
        "pred_gold_ratio": (n_pred / n_gold) if n_gold else 0.0,
        "gold_lost": gold_lost,
    }


def simulate(
    splits: dict[str, list[dict[str, Any]]],
    transform: Transform,
    *,
    label: str = "candidate",
    verbose: bool = True,
) -> dict[str, Any]:
    """Score baseline vs `transform` on each split; return the deltas.

    Prints a table and an estimated Overall (geometric-mean) uplift from the
    three reference axes alone.
    """
    out: dict[str, Any] = {"label": label, "splits": {}}
    for split, rows in splits.items():
        if not rows:
            continue
        base = _score(rows, None)
        cand = _score(rows, transform)
        gm_uplift = sum(
            _LEVERAGE[a] * (cand[a] - base[a]) * 100.0
            for a in ("ref_strict", "ref_conc", "ref_loose")
        )
        out["splits"][split] = {
            "baseline": base,
            "candidate": cand,
            "overall_uplift_pp": gm_uplift,
        }
        if verbose:
            print(f"\n=== {label} — {split} (n={base['n']}) ===")
            print(f"  {'axis':<16}{'baseline':>10}{'candidate':>11}{'delta':>10}")
            for a in ("ref_loose", "ref_strict", "ref_conc"):
                d = cand[a] - base[a]
                flag = "  <-- GUARD" if a == "ref_loose" and d < -0.0005 else ""
                print(f"  {a:<16}{base[a]:>10.4f}{cand[a]:>11.4f}{d:>+10.4f}{flag}")
            print(
                f"  {'pred:gold':<16}{base['pred_gold_ratio']:>10.2f}"
                f"{cand['pred_gold_ratio']:>11.2f}"
                f"{cand['pred_gold_ratio']-base['pred_gold_ratio']:>+10.2f}"
            )
            print(f"  GOLD REFS LOST: {cand['gold_lost']}  (R142.1 failure mode; want 0)")
            print(f"  => est. Overall uplift from ref axes: {gm_uplift:+.2f} pp")
    return out


# ── reference transforms (baselines to beat) ─────────────────────────────


def truncate_to(k: int) -> Transform:
    """Naive positional truncation — the R142.1 shape. A BASELINE, not a fix.

    Kept so any real candidate must beat it AND lose less gold than it does.
    """

    def _t(pred: list[str], _row: dict[str, Any]) -> list[str]:
        return list(pred[:k])

    return _t


def _main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--sidecar",
        default="evals/bench/results/easyhard-r279-live.json",
        help="live gold-bearing sidecar (easy_rows / hard_rows)",
    )
    args = ap.parse_args()
    splits = load_sidecar(args.sidecar)
    print(f"loaded {args.sidecar}: " + ", ".join(f"{k}={len(v)}" for k, v in splits.items()))
    for k in (2, 3, 4, 5):
        simulate(splits, truncate_to(k), label=f"BASELINE truncate-to-{k}")


if __name__ == "__main__":
    _main()
