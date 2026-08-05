#!/usr/bin/env python3
"""Hierarchical partial-credit citation scorer for the EU AI Act benchmark.

The gold set deliberately mixes citation grains (``art_10``, ``art_10__para_3``,
``art_5__para_1__point_h__sub_ii``). Naive exact set-matching conflates a
*granularity miss* (predicting the article when a sub-point was wanted) with a
*genuine error* (citing the wrong provision entirely) -- it ends up measuring
granularity, not correctness. This scorer instead awards **partial credit along
the provision tree**: a predicted node that is an ancestor or descendant of a
gold node scores between 0 and 1 by how far apart they sit on the same
root-to-leaf line; a node in a different subtree (a sibling, a different
article/annex/recital) scores zero. See plan §8, "Granularity-matched scoring".

Metrics (all macro-averaged over items, reported with bootstrap 95% CIs):
  * soft  P / R / F1 -- hierarchical partial credit (the headline metric)
  * exact P / R / F1 -- strict eid equality (diagnostic; the gap vs soft is the
    granularity tax)
  * false-positive rate -- over negative-control items (should abstain, i.e.
    cite nothing); the fraction that wrongly cited anything
  * hallucination rate -- over hallucination-trap items; the fraction that
    emitted an off-gold-lineage citation. NOTE: without a registry of every real
    provision in the Act we cannot verify "non-existent"; this is the
    conservative *off-lineage* proxy. Pass --known-provisions to also flag
    citations absent from a known-good id list.

Statistical-power caveat (plan §8 #2/#3): the hard split rests the FP rate on 6
negative controls and the hallucination rate on 8 traps (1 item is both), so
those CIs are very wide -- treat them as a smoke test, not a headline claim.

Predictions file: JSON mapping benchmark item id -> list of citation strings,
each either eid form ("art_6__para_2") or human form ("Art. 6(2)(a)"); a value
may also be an object with a "citations"/"provision_ids" list. Items missing
from the file are scored as an empty (abstaining) prediction.

Pure standard library, except it reuses euaiact.ids.ProvisionId (itself pure
stdlib) from the sibling euaiact-graphrag package for the id algebra.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

# --- reuse the provision-id algebra from the euaiact-graphrag package ---------
# ids.py is deliberately pure-stdlib, so putting its src dir on the path carries
# no install risk and keeps this scorer runnable standalone (no `pip install`).
_GRAPHRAG_SRC = Path(__file__).resolve().parent.parent / "eu-ai-act-graphrag" / "src"
if _GRAPHRAG_SRC.is_dir() and str(_GRAPHRAG_SRC) not in sys.path:
    sys.path.insert(0, str(_GRAPHRAG_SRC))
try:
    from euaiact.ids import ProvisionId, ProvisionIdError
except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        f"cannot import euaiact.ids -- expected the euaiact-graphrag package at "
        f"{_GRAPHRAG_SRC}. Error: {exc}"
    )


# ============================================================================
# Similarity kernel over the provision tree
# ============================================================================
def _common_prefix_len(a: ProvisionId, b: ProvisionId) -> int:
    n = 0
    for sa, sb in zip(a.segments, b.segments):
        if sa.kind == sb.kind and sa.value == sb.value:
            n += 1
        else:
            break
    return n


def provision_similarity(a: ProvisionId, b: ProvisionId) -> float:
    """Tree-overlap partial credit in [0, 1].

    ``1.0`` iff the two ids are identical; ``|LCP| / max(depth_a, depth_b)`` iff
    one is an ancestor of the other (a pure granularity gap -- e.g. ``art_5`` vs
    ``art_5__para_1__point_a`` scores 1/3); ``0.0`` when the paths diverge before
    the shorter one ends (siblings such as ``point_a`` vs ``point_b``) or sit
    under different roots. Symmetric in its arguments.
    """
    da, db = len(a.segments), len(b.segments)
    lcp = _common_prefix_len(a, b)
    if lcp == min(da, db):  # one path is a prefix of the other
        return lcp / max(da, db)
    return 0.0  # divergent subtree -> genuinely different provision


def exact_similarity(a: ProvisionId, b: ProvisionId) -> float:
    return 1.0 if a.eid == b.eid else 0.0


# ============================================================================
# Citation parsing
# ============================================================================
@dataclass(frozen=True)
class Citation:
    """A parsed citation. ``pid`` is None when the string could not be parsed
    (a malformed / fabricated citation -- scores 0 against everything and counts
    against precision and the hallucination proxy)."""

    raw: str
    pid: ProvisionId | None

    @property
    def key(self) -> str:
        return self.pid.eid if self.pid is not None else f"<unparsed:{self.raw}>"


def parse_citation(raw: str) -> Citation:
    try:
        return Citation(raw, ProvisionId.parse(raw.strip()))
    except ProvisionIdError:
        return Citation(raw, None)


def _dedup(cits: list[Citation]) -> list[Citation]:
    seen: set[str] = set()
    out: list[Citation] = []
    for c in cits:
        if c.key not in seen:
            seen.add(c.key)
            out.append(c)
    return out


# ============================================================================
# Set-level scoring
# ============================================================================
def _best(sim_fn, x: Citation, others: list[Citation]) -> float:
    """Best similarity of ``x`` against any citation in ``others`` (0 if either
    side is unparseable or ``others`` is empty)."""
    if x.pid is None:
        return 0.0
    best = 0.0
    for o in others:
        if o.pid is None:
            continue
        s = sim_fn(x.pid, o.pid)
        if s > best:
            best = s
            if best == 1.0:
                break
    return best


def set_scores(
    pred: list[Citation], gold: list[Citation], sim_fn
) -> tuple[float, float, float]:
    """Soft precision / recall / F1 for an *answerable* item (gold non-empty).

    Precision = mean over predictions of best match into gold; recall = mean over
    gold of best match into predictions (max-alignment: a broad prediction may
    partially cover several finer gold nodes -- intentional, it reflects "on the
    right branch but not specific enough" rather than a hard miss). An empty
    prediction on an answerable item scores 0/0/0 (abstaining is not rewarded
    when an answer was required)."""
    if not pred:
        return 0.0, 0.0, 0.0
    precision = mean(_best(sim_fn, p, gold) for p in pred)
    recall = mean(_best(sim_fn, g, pred) for g in gold)
    f1 = 0.0 if (precision + recall) == 0 else 2 * precision * recall / (precision + recall)
    return precision, recall, f1


# ============================================================================
# Per-item evaluation
# ============================================================================
@dataclass
class ItemResult:
    id: str
    answerable: bool  # gold non-empty
    is_negative_control: bool
    is_trap: bool
    n_gold: int
    n_pred: int
    predicted: bool  # a prediction was supplied for this id
    soft: tuple[float, float, float] | None  # (P, R, F1) for answerable items
    exact: tuple[float, float, float] | None
    fp: bool | None  # negative control cited something it should not have
    trap_triggered: bool | None  # trap item emitted an off-lineage citation
    off_lineage: list[str] | None  # the offending raw citations (for the report)


def _off_lineage(pred: list[Citation], gold: list[Citation]) -> list[Citation]:
    """Predicted citations with zero soft-similarity to every gold node -- i.e.
    genuinely wrong provisions (an unparseable citation is always off-lineage).
    For an empty-gold item every prediction is off-lineage by definition."""
    return [p for p in pred if _best(provision_similarity, p, gold) == 0.0]


def evaluate_item(item: dict, pred_raw: list[str] | None, known: set[str] | None) -> ItemResult:
    gold = _dedup([parse_citation(c["provision_id"]) for c in item.get("gold_citations", [])])
    predicted = pred_raw is not None
    pred = _dedup([parse_citation(r) for r in (pred_raw or [])])

    is_nc = bool(item.get("negative_control", False)) or not gold
    is_trap = bool(item.get("hallucination_trap", False))
    answerable = len(gold) > 0

    soft = exact = None
    if answerable:
        soft = set_scores(pred, gold, provision_similarity)
        exact = set_scores(pred, gold, exact_similarity)

    fp = None
    if is_nc:
        fp = len(pred) > 0  # should have abstained

    trap_triggered = off_raw = None
    if is_trap:
        off = _off_lineage(pred, gold)
        if known is not None:
            # additionally treat any citation to a provision absent from the
            # known-good id list as a hallucination (still a proxy: the list is
            # not the full Act, only benchmark-referenced provisions).
            for p in pred:
                if p not in off and (p.pid is None or p.pid.eid not in known):
                    off.append(p)
        trap_triggered = len(off) > 0
        off_raw = [p.raw for p in off]

    return ItemResult(
        id=item["id"],
        answerable=answerable,
        is_negative_control=is_nc,
        is_trap=is_trap,
        n_gold=len(gold),
        n_pred=len(pred),
        predicted=predicted,
        soft=soft,
        exact=exact,
        fp=fp,
        trap_triggered=trap_triggered,
        off_lineage=off_raw,
    )


# ============================================================================
# Bootstrap CIs
# ============================================================================
def bootstrap_ci(
    values: list[float], n_boot: int, seed: int, alpha: float = 0.05
) -> tuple[float, float, float]:
    """Return (point_estimate, lo, hi) where the point estimate is the mean of
    the observed values and lo/hi are the (alpha/2, 1-alpha/2) percentiles of the
    resampled means. Returns NaNs for an empty input."""
    if not values:
        nan = float("nan")
        return nan, nan, nan
    point = mean(values)
    if n_boot <= 0:
        return point, point, point
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return point, lo, hi


# ============================================================================
# Corpus-level report
# ============================================================================
def score_corpus(
    items: list[dict],
    predictions: dict[str, list[str]],
    n_boot: int = 1000,
    seed: int = 0,
    known: set[str] | None = None,
) -> dict:
    results = [
        evaluate_item(it, predictions.get(it["id"]), known)
        for it in items
    ]

    answerable = [r for r in results if r.answerable]
    ncs = [r for r in results if r.is_negative_control]
    traps = [r for r in results if r.is_trap]

    def ci(vals: list[float]) -> dict:
        pt, lo, hi = bootstrap_ci(vals, n_boot, seed)
        return {"point": pt, "ci95": [lo, hi], "n": len(vals)}

    soft_p = [r.soft[0] for r in answerable]
    soft_r = [r.soft[1] for r in answerable]
    soft_f = [r.soft[2] for r in answerable]
    exact_p = [r.exact[0] for r in answerable]
    exact_r = [r.exact[1] for r in answerable]
    exact_f = [r.exact[2] for r in answerable]

    return {
        "n_items": len(items),
        "n_answerable": len(answerable),
        "n_negative_controls": len(ncs),
        "n_traps": len(traps),
        "n_missing_predictions": sum(1 for r in results if not r.predicted),
        "soft": {
            "precision": ci(soft_p),
            "recall": ci(soft_r),
            "f1": ci(soft_f),
        },
        "exact": {
            "precision": ci(exact_p),
            "recall": ci(exact_r),
            "f1": ci(exact_f),
        },
        "false_positive_rate": ci([1.0 if r.fp else 0.0 for r in ncs]),
        "hallucination_rate": ci([1.0 if r.trap_triggered else 0.0 for r in traps]),
        "results": results,
    }


def format_report(report: dict, title: str) -> str:
    def line(name: str, m: dict) -> str:
        pt, (lo, hi), n = m["point"], m["ci95"], m["n"]
        if n == 0 or pt != pt:  # NaN
            return f"  {name:<22} n/a (no items)"
        return f"  {name:<22} {pt:6.3f}   95% CI [{lo:5.3f}, {hi:5.3f}]   (n={n})"

    out = [
        f"== {title} ==",
        f"items={report['n_items']}  answerable={report['n_answerable']}  "
        f"neg_controls={report['n_negative_controls']}  traps={report['n_traps']}  "
        f"missing_preds={report['n_missing_predictions']}",
        "",
        "Soft (hierarchical partial credit) -- headline:",
        line("precision", report["soft"]["precision"]),
        line("recall", report["soft"]["recall"]),
        line("f1", report["soft"]["f1"]),
        "",
        "Exact (strict eid match) -- diagnostic; gap vs soft = granularity tax:",
        line("precision", report["exact"]["precision"]),
        line("recall", report["exact"]["recall"]),
        line("f1", report["exact"]["f1"]),
        "",
        "Abstention / hallucination (smoke test -- tiny n, very wide CIs):",
        line("false_positive_rate", report["false_positive_rate"]),
        line("hallucination_rate", report["hallucination_rate"]),
    ]
    triggered = [r for r in report["results"] if r.trap_triggered]
    if triggered:
        out.append("")
        out.append("Traps triggered:")
        for r in triggered:
            out.append(f"  {r.id}: off-lineage citations {r.off_lineage}")
    return "\n".join(out)


# ============================================================================
# Prediction loading + synthetic oracles
# ============================================================================
def _coerce_pred_value(v) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, dict):
        for key in ("citations", "provision_ids", "provisions"):
            if key in v:
                return [str(x) for x in v[key]]
    raise ValueError(f"unrecognised prediction value: {v!r}")


def load_predictions(path: Path) -> dict[str, list[str]]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("predictions file must be a JSON object mapping item id -> citations")
    return {str(k): _coerce_pred_value(v) for k, v in data.items()}


def _truncate(pid: ProvisionId, grain: str) -> ProvisionId:
    if grain in ("root", "article"):
        return ProvisionId(pid.segments[:1])
    stop = {"para": "para", "point": "point"}.get(grain)
    if stop is None:
        return pid
    depth = len(pid.segments)
    for i, seg in enumerate(pid.segments):
        if seg.kind == stop:
            depth = i + 1
            break
    else:
        depth = len(pid.segments)  # citation shallower than target grain -> keep as-is
    return ProvisionId(pid.segments[:depth])


def oracle_predictions(items: list[dict], grain: str) -> dict[str, list[str]]:
    """Synthesise predictions from the benchmark's own gold, truncated to a
    target grain. ``full`` = perfect oracle (sanity: soft==exact==1.0);
    ``root`` = article/annex/recital only (shows the soft vs exact gap)."""
    preds: dict[str, list[str]] = {}
    for it in items:
        pids = [ProvisionId.parse(c["provision_id"]) for c in it.get("gold_citations", [])]
        if grain != "full":
            pids = [_truncate(p, grain) for p in pids]
        preds[it["id"]] = sorted({p.eid for p in pids})
    return preds


# ============================================================================
# CLI
# ============================================================================
def _load_items(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    return data["items"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("benchmark", type=Path, help="benchmark JSON (eu_ai_act_bench_{easy,hard}.json)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--predictions", type=Path, help="predictions JSON: {item_id: [citation, ...]}")
    src.add_argument(
        "--oracle",
        choices=["full", "root", "para", "point"],
        help="synthesise predictions from gold at a grain (calibration/smoke test)",
    )
    ap.add_argument("--known-provisions", type=Path, help="JSON with a 'pairs' object of known-good eids (e.g. benchmark_ids.json)")
    ap.add_argument("--bootstrap", type=int, default=1000, help="bootstrap resamples (default 1000; 0 disables)")
    ap.add_argument("--seed", type=int, default=0, help="bootstrap RNG seed (default 0)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON instead of a text report")
    args = ap.parse_args(argv)

    items = _load_items(args.benchmark)
    predictions = (
        oracle_predictions(items, args.oracle)
        if args.oracle
        else load_predictions(args.predictions)
    )

    known = None
    if args.known_provisions:
        kp = json.loads(args.known_provisions.read_text())
        known = set(kp.get("pairs", kp).keys())

    report = score_corpus(items, predictions, n_boot=args.bootstrap, seed=args.seed, known=known)

    if args.json:
        report = {k: v for k, v in report.items() if k != "results"}
        print(json.dumps(report, indent=2))
    else:
        title = f"{args.benchmark.name}  ({'oracle:' + args.oracle if args.oracle else args.predictions.name})"
        print(format_report(report, title))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
