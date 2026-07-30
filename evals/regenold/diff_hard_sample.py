"""R301 — per-row diff of two hard-sample runs of the SAME deterministic sample.

WHY THIS EXISTS
---------------
``run_hard_sample_r297`` draws a deterministic, evenly-spaced sample, so two runs
at different commits replay the IDENTICAL request set. That makes a per-row diff
a real A/B — but only if you diff the rows, not the aggregate means. R80 is the
cautionary case: an unchanged aggregate hid per-row divergence, and the project
has since standardised on row-level byte comparison (``--assert-baseline``).

This module is the hard-sample equivalent. It answers the question a mean cannot:
*which* rows moved, in *which* direction, and were they the rows the fix was
supposed to touch?

THE STRATIFICATION THAT MATTERS
-------------------------------
For a Stage-2-gated change (the R299 reference partition, the R300 context
restore) only rows where **Stage-2 actually landed** are in the treatment
population. Rows that took a curated-intercept / deterministic path are
byte-identical by construction and, if pooled into one mean, dilute the effect
toward zero. So every table here splits on ``provenance.stage2_polish``.

MULTI-TURN SEMANTICS
--------------------
``run_official_batch`` sets ``pred_answer``/``pred_refs`` to the POST-PUSHBACK
turn (``ans2 or ans1``) — the turn the official batch grades. ``turn1_*`` and
``pushback_*`` are kept separately so citation instability under challenge
(R300's open finding: 36% of rows changed their citation set on the pushback
turn) can be diffed on its own.

USAGE
-----
    .venv/Scripts/python.exe -m evals.regenold.diff_hard_sample \\
        --pre  r300-live --post r301-postfix

    # single arm
    ... --pre r300-live --post r301-postfix --only mt
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

_RESULTS = Path(__file__).resolve().parents[2] / "evals" / "bench" / "results"

_ARMS = {"mt": "mt-hard", "st": "st-easy"}


# ── loading ─────────────────────────────────────────────────────────────


def _load(label: str, arm: str) -> dict[str, dict[str, Any]]:
    path = _RESULTS / f"official-{label}-{_ARMS[arm]}.ckpt.jsonl"
    if not path.exists():
        raise SystemExit(f"missing sidecar: {path}")
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            out[str(row.get("id"))] = row
    return out


# ── ref helpers ─────────────────────────────────────────────────────────


def _heads(refs: list[str] | None) -> set[str]:
    """Collapse sub-points to their parent head (``Annex IV.2`` -> ``Annex IV``).

    Head-level is the grain the local scorers use, but it is deliberately NOT
    the only grain reported: R287.1 measured a case where head-level recall was
    invariant while SUB-POINT recall collapsed (rg_012 1.0 -> 0.0), because the
    grounded judge scores at sub-point grain. So both grains are reported.
    """
    out: set[str] = set()
    for r in refs or []:
        s = str(r).strip()
        if not s:
            continue
        out.add(s.split(".")[0].split("(")[0].strip())
    return out


def _exact(refs: list[str] | None) -> set[str]:
    return {str(r).strip() for r in (refs or []) if str(r).strip()}


def _jacc(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    u = a | b
    return len(a & b) / len(u) if u else 1.0


def _stage2(row: dict[str, Any]) -> bool:
    return bool((row.get("provenance") or {}).get("stage2_polish"))


# ── diffing ─────────────────────────────────────────────────────────────


def diff_arm(pre: dict[str, Any], post: dict[str, Any], arm: str) -> dict[str, Any]:
    ids = sorted(set(pre) & set(post))
    missing = sorted((set(pre) ^ set(post)))
    rows: list[dict[str, Any]] = []

    for rid in ids:
        a, b = pre[rid], post[rid]
        pa, pb = _exact(a.get("pred_refs")), _exact(b.get("pred_refs"))
        ha, hb = _heads(a.get("pred_refs")), _heads(b.get("pred_refs"))
        rec = {
            "id": rid,
            "difficulty": b.get("difficulty"),
            "category": b.get("difficulty_category"),
            "stage2_pre": _stage2(a),
            "stage2_post": _stage2(b),
            "model_pre": (a.get("provenance") or {}).get("stage2_model") or "",
            "model_post": (b.get("provenance") or {}).get("stage2_model") or "",
            "refs_pre": sorted(pa),
            "refs_post": sorted(pb),
            "refs_added": sorted(pb - pa),
            "refs_dropped": sorted(pa - pb),
            "n_refs_pre": len(pa),
            "n_refs_post": len(pb),
            "heads_added": sorted(hb - ha),
            "heads_dropped": sorted(ha - hb),
            "refs_changed": pa != pb,
            "heads_changed": ha != hb,
            "ref_jaccard": round(_jacc(pa, pb), 4),
            "answer_changed": (a.get("pred_answer") or "") != (b.get("pred_answer") or ""),
            "chars_pre": len(a.get("pred_answer") or ""),
            "chars_post": len(b.get("pred_answer") or ""),
            "lat_pre_s": round((a.get("latency_ms") or 0) / 1000, 1),
            "lat_post_s": round((b.get("latency_ms") or 0) / 1000, 1),
        }
        if arm == "mt":
            rec["pushback_flip_pre"] = bool((a.get("pushback") or {}).get("ref_heads_changed"))
            rec["pushback_flip_post"] = bool((b.get("pushback") or {}).get("ref_heads_changed"))
            rec["turn1_refs_post"] = sorted(_exact(b.get("turn1_refs")))
            rec["pushback_refs_post"] = sorted(_exact(b.get("pushback_refs")))
        rows.append(rec)

    def _agg(sel: list[dict[str, Any]], name: str) -> dict[str, Any]:
        if not sel:
            return {"stratum": name, "n": 0}
        out = {
            "stratum": name,
            "n": len(sel),
            "rows_refs_changed": sum(r["refs_changed"] for r in sel),
            "rows_heads_changed": sum(r["heads_changed"] for r in sel),
            "rows_answer_changed": sum(r["answer_changed"] for r in sel),
            "refs_added_total": sum(len(r["refs_added"]) for r in sel),
            "refs_dropped_total": sum(len(r["refs_dropped"]) for r in sel),
            "n_refs_pre_mean": round(statistics.mean(r["n_refs_pre"] for r in sel), 3),
            "n_refs_post_mean": round(statistics.mean(r["n_refs_post"] for r in sel), 3),
            "chars_pre_median": round(statistics.median(r["chars_pre"] for r in sel), 1),
            "chars_post_median": round(statistics.median(r["chars_post"] for r in sel), 1),
            "lat_pre_p50_s": round(statistics.median(r["lat_pre_s"] for r in sel), 1),
            "lat_post_p50_s": round(statistics.median(r["lat_post_s"] for r in sel), 1),
        }
        if arm == "mt":
            out["pushback_flip_pre"] = round(
                sum(r["pushback_flip_pre"] for r in sel) / len(sel), 4)
            out["pushback_flip_post"] = round(
                sum(r["pushback_flip_post"] for r in sel) / len(sel), 4)
        return out

    treat = [r for r in rows if r["stage2_pre"] or r["stage2_post"]]
    control = [r for r in rows if not (r["stage2_pre"] or r["stage2_post"])]

    return {
        "arm": arm,
        "n_common": len(ids),
        "ids_only_in_one_run": missing,
        "strata": [
            _agg(rows, "ALL"),
            _agg(treat, "STAGE2 LANDED (treatment)"),
            _agg(control, "deterministic / curated (control)"),
        ],
        "rows": rows,
    }


# ── reporting ───────────────────────────────────────────────────────────


def _print(res: dict[str, Any]) -> None:
    arm = res["arm"]
    print(f"\n{'=' * 78}")
    print(f"ARM {arm}  —  {res['n_common']} rows in both runs")
    if res["ids_only_in_one_run"]:
        print(f"  !! ids present in only one run: {res['ids_only_in_one_run']}")
    print("=" * 78)

    for s in res["strata"]:
        if not s.get("n"):
            continue
        print(f"\n-- {s['stratum']}  (n={s['n']})")
        print(f"   rows with refs changed   : {s['rows_refs_changed']}/{s['n']}"
              f"   (heads {s['rows_heads_changed']}/{s['n']})")
        print(f"   rows with answer changed : {s['rows_answer_changed']}/{s['n']}")
        print(f"   refs added / dropped     : +{s['refs_added_total']} / -{s['refs_dropped_total']}")
        print(f"   refs per row  pre -> post: {s['n_refs_pre_mean']} -> {s['n_refs_post_mean']}")
        print(f"   answer chars (median)    : {s['chars_pre_median']} -> {s['chars_post_median']}")
        print(f"   latency p50 (s)          : {s['lat_pre_p50_s']} -> {s['lat_post_p50_s']}")
        if "pushback_flip_pre" in s:
            print(f"   pushback ref-flip rate   : {s['pushback_flip_pre']} -> {s['pushback_flip_post']}")

    changed = [r for r in res["rows"] if r["refs_changed"]]
    if changed:
        print(f"\n-- PER-ROW REFERENCE CHANGES ({len(changed)})")
        for r in changed:
            tag = "S2" if (r["stage2_pre"] or r["stage2_post"]) else "det"
            print(f"   [{tag}] {r['id']}  ({r['difficulty']})  jaccard={r['ref_jaccard']}")
            if r["refs_added"]:
                print(f"          + {r['refs_added']}")
            if r["refs_dropped"]:
                print(f"          - {r['refs_dropped']}")
    else:
        print("\n-- PER-ROW REFERENCE CHANGES: none (arms byte-identical on refs)")

    mdl = {(r["model_pre"], r["model_post"]) for r in res["rows"]
           if r["model_pre"] or r["model_post"]}
    if mdl:
        print("\n-- stage2_model reported in trace (pre -> post)")
        for a, b in sorted(mdl):
            print(f"   {a or '(none)'!r:26} -> {b or '(none)'!r}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pre", required=True, help="baseline label, e.g. r300-live")
    ap.add_argument("--post", required=True, help="branch label, e.g. r301-postfix")
    ap.add_argument("--only", choices=("mt", "st", "both"), default="both")
    ap.add_argument("--out", default=None, help="write the full diff JSON here")
    args = ap.parse_args()

    arms = ["mt", "st"] if args.only == "both" else [args.only]
    payload: dict[str, Any] = {"pre": args.pre, "post": args.post, "arms": {}}
    for arm in arms:
        res = diff_arm(_load(args.pre, arm), _load(args.post, arm), arm)
        _print(res)
        payload["arms"][arm] = res

    out = Path(args.out) if args.out else _RESULTS / f"diff-{args.pre}-vs-{args.post}.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":  # pragma: no cover
    main()
