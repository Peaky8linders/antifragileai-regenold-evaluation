"""Dynamic A/B — the merge gate that replaces the davidath regression run.

WHY THIS EXISTS
===============

``evals.bench.runner`` (davidath, 476 rows) was the habitual "did I break
anything" run. It is the wrong instrument and it kept producing confident,
useless numbers:

* It runs ``P2P_GRAPH_RAG_PROVIDER=cli`` — **no Stage-2 at all**. Every prompt
  change, every judge change, the Cohere reranker and the whole KG-context block
  are invisible to it by construction. R331 measured "baseline reproduces,
  deltas <= 0.0007" on a change set containing four judge fixes and a reranker,
  because it could not see any of them.
* Its gold is head-level and single-article (mean 1.00 refs/row), so it
  structurally cannot show a chain-dropping defect (hard rule #7).
* It is BM25-saturated, so retrieval levers read byte-identical *because the
  instrument is blind*, not because the lever is safe.

That is CLAUDE.md's "instrument trap" in its purest form: **before trusting a
measurement, ask whether the instrument can physically observe the thing you are
deciding.** davidath usually cannot, so it has been retired as a gate.

WHAT "DYNAMIC" MEANS HERE
=========================

Three things, in order of importance:

1. **FIRE CHECK FIRST — no number is reported until the lever is proven to have
   fired.** Every previous inert A/B in this repo (R326 vector recall, R327
   semantic layers, three R329 reranker placements) reported a clean +0.0000 on
   every axis while the feature never executed. A flat result and a dead feature
   are the same picture. This harness runs a small probe, asserts the two arms
   actually diverge, and **ABORTS with verdict INERT** if they do not. It will
   not print an axis table for a lever that did nothing.

2. **Sample size is driven by observed variance, not by a constant.** Rows are
   run in batches; after each batch the paired deltas get a bootstrap CI. It
   stops early when the CI excludes zero (a real effect) or when it is tight
   enough around zero to call a null with confidence. A 0.003 delta on 9
   effective rows — R331's retrieval result — is reported as UNDERPOWERED rather
   than dressed up as a finding.

3. **It runs the LIVE path** (Stage-2 on) by default, because that is where the
   product lives. `--deterministic` exists for a quick smoke, and says so in the
   verdict.

WHAT IT REPORTS
===============

Per axis: paired delta, bootstrap 95% CI, and a verdict. Plus ``gold_dropped``
on both grains — hard rule #8 is a VETO, not an axis: a non-zero gold drop is a
rejection regardless of every other number.

USAGE
=====

    py -3.12 -m evals.harness.dynamic_ab --flag REGENOLD_COHERE_RERANK \\
        --label r331-rerank --max-rows 60

    py -3.12 -m evals.harness.dynamic_ab \\
        --branch-env REGENOLD_ONTOLOGY_RISK_DOCS=0 --label onto-off

⚠ In-process env flips only work for flags read fresh per call AND absent from
any memo that outlives the flip. ``_engine_cache_key`` covers the answer cache;
a module-level ``lru_cache`` does NOT. The fire check catches both, which is the
entire point of running it before anything else.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics as st
import sys
import time
from pathlib import Path
from typing import Any, Callable

from evals.bench import metrics as bench_metrics
from evals.harness.probe_set import ProbeRow, load_probe_set

_RESULTS = Path(__file__).resolve().parents[1] / "bench" / "results"

#: Axes that are DIRECTIONAL (higher is better). gold_dropped is deliberately
#: not here — it is a veto, not a score.
_AXES = ("ref_loose", "ref_strict", "ref_conc", "kw_recall")

_BOOTSTRAP_N = 2000
_SEED = 20260814


# ── scoring ──────────────────────────────────────────────────────────────


def _score(row: ProbeRow, answer: str, refs: list[str]) -> dict[str, Any]:
    gold = list(getattr(row, "expected_refs", ()) or ())
    kws = list(getattr(row, "expected_keywords", ()) or ())
    gd_head = bench_metrics.gold_dropped_head(refs, gold)
    gd_exact = bench_metrics.gold_dropped_exact(refs, gold)
    low = (answer or "").lower()
    return {
        "ref_loose": bench_metrics.reference_correctness_loose(refs, gold),
        "ref_strict": bench_metrics.reference_correctness_strict(refs, gold),
        "ref_conc": bench_metrics.reference_conciseness(refs, gold),
        "kw_recall": (
            sum(1 for k in kws if k.lower() in low) / len(kws) if kws else 0.0
        ),
        "gold_dropped_head": float(gd_head["dropped_count"]),
        "gold_dropped_exact": float(gd_exact["dropped_count"]),
        "answer_chars": float(len(answer or "")),
        "n_refs": float(len(refs or [])),
    }


# ── statistics ───────────────────────────────────────────────────────────


def _bootstrap_ci(
    deltas: list[float], *, n: int = _BOOTSTRAP_N, alpha: float = 0.05
) -> tuple[float, float]:
    """Percentile bootstrap CI of the MEAN paired delta.

    Paired deltas, so the resample unit is the row — which is what makes this
    valid on a small n where a t-test's normality assumption is not credible.
    """
    if not deltas:
        return (0.0, 0.0)
    if len(deltas) == 1:
        return (deltas[0], deltas[0])
    rng = random.Random(_SEED)
    means: list[float] = []
    k = len(deltas)
    for _ in range(n):
        means.append(st.fmean(deltas[rng.randrange(k)] for _ in range(k)))
    means.sort()
    lo = means[int((alpha / 2) * n)]
    hi = means[min(n - 1, int((1 - alpha / 2) * n))]
    return (lo, hi)


def _verdict(delta: float, lo: float, hi: float, *, null_band: float) -> str:
    """Classify an axis result honestly, including 'not enough data'."""
    if lo > 0:
        return "WIN"
    if hi < 0:
        return "LOSS"
    if (hi - lo) <= 2 * null_band:
        return "NULL"          # tight around zero — a real, useful null
    return "UNDERPOWERED"      # CI spans zero AND is wide — say so


# ── the fire check ───────────────────────────────────────────────────────


def fire_check(
    baseline_rows: list[dict[str, Any]], branch_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """Did the lever actually change anything? Run BEFORE scoring.

    Returns counts of rows whose answer or reference list differ. A lever that
    changes NOTHING is not "safe" — it is UNMEASURED, and the axis table that
    would follow is meaningless. This is the check every inert A/B in this
    repo's history was missing.
    """
    b = {r["id"]: r for r in baseline_rows}
    c = {r["id"]: r for r in branch_rows}
    common = [i for i in b if i in c]
    refs_diff = [
        i for i in common if b[i].get("pred_refs") != c[i].get("pred_refs")
    ]
    ans_diff = [
        i for i in common
        if (b[i].get("pred_answer") or "") != (c[i].get("pred_answer") or "")
    ]
    changed = sorted(set(refs_diff) | set(ans_diff))
    return {
        "common": len(common),
        "refs_changed": len(refs_diff),
        "answers_changed": len(ans_diff),
        "any_changed": len(changed),
        "changed_ids": changed[:20],
        "fired": bool(changed),
    }


# ── the probe sensitivity control ────────────────────────────────────────
#
# R336. The fire check answers "did the lever move anything?". It does NOT
# answer "could these rows have shown me if it had?" — and those are different
# questions with opposite remedies.
#
# Measured 2026-08-14, same process, one flag, two questions:
#
#   REGENOLD_BM25_FALLBACK_K=2   FIRES   on "if a logistics firm retrofits a
#                                        third-party vision model…"  (15 refs)
#   REGENOLD_BM25_FALLBACK_K=2   inert   on "what is the definition of an AI
#                                        system?"                    (1 ref)
#
# The definitional row resolves through a direct KB obligation lookup
# (`kb-governance-Art. 3`, 378 chars) and never reaches BM25 ranking, graph
# expansion or the answer router. So a probe pool dominated by curated and
# definitional rows is BLIND to every retrieval lever — and the A/B would have
# reported INERT while the lever was fine and the rows simply could not see it.
#
# That mattered: three separate wrong diagnoses were made off exactly this
# confusion before it was pinned down, each one sending the reader to debug a
# feature that was not broken.
#
# So: before declaring INERT, flip a control flag KNOWN to be live at the same
# layer over the SAME rows. If the control moves them, the probe can see that
# layer and INERT is a real finding about the lever. If the control cannot move
# them either, the instrument is blind and the verdict is BLIND_PROBE — fix the
# probe set, not the feature.

_CONTROL_FLAGS: dict[str, tuple[str, str]] = {
    # layer -> (env var, value) for a lever measured to change engine output.
    "retrieval": ("REGENOLD_BM25_FALLBACK_K", "2"),
    "stage2": ("P2P_GRAPH_RAG_ENABLE_STAGE2", "0"),
    "graph": ("REGENOLD_KG_CONTEXT", "0"),
}

# Substring -> layer. Ordered; first match wins. Crude on purpose: a wrong guess
# is corrected by `--control-layer`, and the fallback is the retrieval control,
# which is the layer every row must traverse to produce a reference at all.
_LAYER_HINTS: tuple[tuple[str, str], ...] = (
    ("STAGE2", "stage2"), ("COMPLEX", "stage2"), ("OPUS", "stage2"),
    ("MINIMAL_COMPOSER", "stage2"), ("REF_MINIMALITY", "stage2"),
    ("ANSWER_FIRST", "stage2"), ("CURATED", "stage2"),
    ("KG_", "graph"), ("GRAPH", "graph"), ("SEMANTIC", "graph"),
    ("PPR", "graph"), ("VECTOR", "graph"), ("ONTOLOGY", "graph"),
)


def _infer_control_layer(branch_env: dict[str, str]) -> str:
    for name in branch_env:
        upper = name.upper()
        for frag, layer in _LAYER_HINTS:
            if frag in upper:
                return layer
    return "retrieval"


def resolve_control(
    branch_env: dict[str, str], override: str | None = None
) -> tuple[str, dict[str, str]] | None:
    """Pick a control flag for this A/B, or None if none is usable.

    Never returns a control the branch itself is manipulating — flipping the
    same var in both arms would make the control trivially "fire" (or trivially
    not) for reasons that have nothing to do with probe sensitivity.
    """
    layer = override or _infer_control_layer(branch_env)
    candidates = [layer] + [k for k in _CONTROL_FLAGS if k != layer]
    for cand in candidates:
        env, val = _CONTROL_FLAGS[cand]
        if env not in branch_env:
            return cand, {env: val}
    return None


def probe_sensitivity_check(
    rows: list[ProbeRow],
    baseline_rows: list[dict[str, Any]],
    control_env: dict[str, str],
    *,
    local: bool,
    endpoint: str | None,
    api_key: str | None,
    timeout: float,
) -> dict[str, Any]:
    """Can these rows observe ANY change at this layer?

    Re-runs the rows already used, under a known-live control flag, and reuses
    :func:`fire_check` so "changed" means exactly what it means everywhere else.
    """
    control_rows = _run_rows(rows, control_env, local=local, endpoint=endpoint,
                             api_key=api_key, timeout=timeout)
    fired = fire_check(baseline_rows, control_rows)
    return {
        "control_env": control_env,
        "sensitive": fired["fired"],
        "rows_moved": fired["any_changed"],
        "rows_compared": fired["common"],
        "moved_ids": fired["changed_ids"],
    }


# ── the run ──────────────────────────────────────────────────────────────


def _run_rows(
    rows: list[ProbeRow],
    arm_env: dict[str, str],
    *,
    local: bool,
    endpoint: str | None,
    api_key: str | None,
    timeout: float,
) -> list[dict[str, Any]]:
    saved: dict[str, str | None] = {}
    for k, v in arm_env.items():
        saved[k] = os.environ.get(k)
        os.environ[k] = v
    try:
        from evals.regenold.runner_v2 import _post, _post_local

        poster = _post_local if local else _post
        url = (
            "local://app.main:app/api/v1/regenold/eu-ai-act/ask"
            if local else str(endpoint)
        )
        out: list[dict[str, Any]] = []
        for pr in rows:
            history = [dict(m) for m in pr.messages]
            body, latency_ms, status, err, attempts, _ = poster(
                url, api_key, history, timeout
            )
            answer = (body or {}).get("answer") or ""
            refs = list((body or {}).get("references") or [])
            out.append({
                "id": pr.id,
                "source": pr.source,
                "pred_answer": answer,
                "pred_refs": refs,
                "latency_ms": latency_ms,
                "http_status": status,
                "error": err,
                "scores": _score(pr, answer, refs),
            })
        return out
    finally:
        for k, old in saved.items():
            if old is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = old


def _stratified(probe: list[ProbeRow], n: int, seed: int) -> list[ProbeRow]:
    """Proportional sample across sources — NOT a head slice.

    `probe_set` is ordered by source, so `[:n]` (what the previous runs used,
    and called "stratified") takes whole sources and drops others entirely.
    """
    by_src: dict[str, list[ProbeRow]] = {}
    for r in probe:
        by_src.setdefault(r.source, []).append(r)
    rng = random.Random(seed)
    for v in by_src.values():
        rng.shuffle(v)
    out: list[ProbeRow] = []
    srcs = sorted(by_src)
    i = 0
    while len(out) < n and any(by_src[s] for s in srcs):
        s = srcs[i % len(srcs)]
        if by_src[s]:
            out.append(by_src[s].pop())
        i += 1
    return out


def run(
    *,
    branch_env: dict[str, str],
    label: str,
    max_rows: int,
    batch: int,
    local: bool,
    endpoint: str | None,
    api_key: str | None,
    timeout: float,
    null_band: float,
    seed: int,
    control_layer: str | None = None,
    emit: Callable[[str], None] = print,
) -> dict[str, Any]:
    probe = load_probe_set()
    pool = _stratified(probe, min(max_rows, len(probe)), seed)
    emit(f"probe pool: {len(pool)} rows (stratified across "
         f"{len({r.source for r in pool})} sources)")
    emit(f"branch env: {branch_env}")

    base_rows: list[dict[str, Any]] = []
    brch_rows: list[dict[str, Any]] = []
    stop_reason = "max_rows"
    fired: dict[str, Any] = {}

    for start in range(0, len(pool), batch):
        chunk = pool[start:start + batch]
        base_rows += _run_rows(chunk, {}, local=local, endpoint=endpoint,
                               api_key=api_key, timeout=timeout)
        brch_rows += _run_rows(chunk, branch_env, local=local, endpoint=endpoint,
                               api_key=api_key, timeout=timeout)

        fired = fire_check(base_rows, brch_rows)
        emit(f"  n={len(base_rows):3d}  changed={fired['any_changed']:3d} "
             f"(refs {fired['refs_changed']}, answers {fired['answers_changed']})")

        # ── THE GATE: a lever that never fired gets no axis table ──────────
        if not fired["fired"] and len(base_rows) >= min(batch * 2, len(pool)):
            # R336 — do NOT call it INERT until the probe has proven it could
            # have seen the change. Paid only here, on the rows already run, so
            # a firing A/B never carries the cost.
            ran = pool[:len(base_rows)]
            sens: dict[str, Any] | None = None
            control = resolve_control(branch_env, control_layer)
            if control is None:
                emit("")
                emit("  (no control flag available — every candidate is being "
                     "manipulated by this A/B; sensitivity unproven)")
            else:
                layer, control_env = control
                emit("")
                emit(f"  lever flat — checking the PROBE with a known-live "
                     f"{layer} control: {control_env}")
                sens = probe_sensitivity_check(
                    ran, base_rows, control_env, local=local,
                    endpoint=endpoint, api_key=api_key, timeout=timeout)
                sens["layer"] = layer
                emit(f"  control moved {sens['rows_moved']}/"
                     f"{sens['rows_compared']} of the same rows")

            if sens is not None and not sens["sensitive"]:
                emit("")
                emit("  VERDICT: BLIND_PROBE — these rows cannot observe this "
                     "layer AT ALL.")
                emit("  A known-live control flag failed to move them either, "
                     "so the flat")
                emit("  result says nothing about your lever. Curated and "
                     "definitional rows")
                emit("  short-circuit to a direct KB lookup and never reach "
                     "retrieval, the")
                emit("  graph, or Stage-2 — a pool of them is blind by "
                     "construction.")
                emit("  FIX THE PROBE SET, not the feature: raise --max-rows, "
                     "or select rows")
                emit("  that exercise this layer, then re-run.")
                return {
                    "label": label, "verdict": "BLIND_PROBE", "fire": fired,
                    "sensitivity": sens, "branch_env": branch_env,
                    "n": len(base_rows), "baseline_rows": base_rows,
                    "branch_rows": brch_rows,
                }

            emit("")
            emit("  VERDICT: INERT — the two arms are identical on every row "
                 "run so far,")
            if sens is not None:
                emit(f"  and the probe is NOT blind: the {sens['layer']} "
                     f"control moved "
                     f"{sens['rows_moved']}/{sens['rows_compared']} of these "
                     f"same rows.")
                emit("  So this is a real finding about the lever, not about "
                     "the rows.")
            emit("  No axis numbers will be reported. A flat result and a dead "
                 "feature are")
            emit("  indistinguishable, so reporting +0.0000 here would be a "
                 "false negative,")
            emit("  not a null result. Fix the lever (fresh env read? memo "
                 "outliving the flip?")
            emit("  flag missing from _engine_cache_key? gate never reached?) "
                 "then re-run.")
            return {
                "label": label, "verdict": "INERT", "fire": fired,
                "sensitivity": sens, "branch_env": branch_env,
                "n": len(base_rows), "baseline_rows": base_rows,
                "branch_rows": brch_rows,
            }

        # ── adaptive stop: every axis resolved? ────────────────────────────
        if len(base_rows) >= batch * 2:
            res = _analyse(base_rows, brch_rows, null_band=null_band)
            if all(v["verdict"] in ("WIN", "LOSS", "NULL")
                   for v in res["axes"].values()):
                stop_reason = "resolved"
                break

    res = _analyse(base_rows, brch_rows, null_band=null_band)
    res.update({
        "label": label, "branch_env": branch_env, "fire": fired,
        "stop_reason": stop_reason, "n": len(base_rows),
        "baseline_rows": base_rows, "branch_rows": brch_rows,
    })
    return res


def _analyse(
    base_rows: list[dict[str, Any]],
    brch_rows: list[dict[str, Any]],
    *,
    null_band: float,
) -> dict[str, Any]:
    b = {r["id"]: r for r in base_rows}
    c = {r["id"]: r for r in brch_rows}
    common = [i for i in b if i in c and not b[i].get("error")
              and not c[i].get("error")]
    axes: dict[str, Any] = {}
    for ax in _AXES:
        deltas = [c[i]["scores"][ax] - b[i]["scores"][ax] for i in common]
        if not deltas:
            continue
        mean = st.fmean(deltas)
        lo, hi = _bootstrap_ci(deltas)
        axes[ax] = {
            "baseline": st.fmean(b[i]["scores"][ax] for i in common),
            "branch": st.fmean(c[i]["scores"][ax] for i in common),
            "delta": mean, "ci_lo": lo, "ci_hi": hi,
            "n_changed": sum(1 for d in deltas if d != 0),
            "verdict": _verdict(mean, lo, hi, null_band=null_band),
        }
    gold = {
        g: {
            "baseline": sum(b[i]["scores"][g] for i in common),
            "branch": sum(c[i]["scores"][g] for i in common),
        }
        for g in ("gold_dropped_head", "gold_dropped_exact")
    }
    for g in gold:
        gold[g]["delta"] = gold[g]["branch"] - gold[g]["baseline"]
    return {"axes": axes, "gold": gold, "n_scored": len(common)}


def _report(res: dict[str, Any], emit: Callable[[str], None] = print) -> None:
    if res.get("verdict") in ("INERT", "BLIND_PROBE"):
        return
    f = res.get("fire") or {}
    emit("")
    emit(f"=== {res['label']} — n={res['n_scored']} paired "
         f"(stop: {res.get('stop_reason')}) ===")
    emit(f"  lever FIRED on {f.get('any_changed', 0)}/{f.get('common', 0)} rows "
         f"— numbers below are about a change that actually happened")
    emit("")
    emit(f"  {'axis':<12} {'baseline':>9} {'branch':>9} {'delta':>9} "
         f"{'95% CI':>20}  verdict")
    for ax, v in res["axes"].items():
        ci = f"[{v['ci_lo']:+.4f},{v['ci_hi']:+.4f}]"
        emit(f"  {ax:<12} {v['baseline']:>9.4f} {v['branch']:>9.4f} "
             f"{v['delta']:>+9.4f} {ci:>20}  {v['verdict']}")
    emit("")
    for g, v in res["gold"].items():
        flag = "  <-- HARD RULE #8 VETO" if v["delta"] > 0 else ""
        emit(f"  {g:<20} {v['baseline']:>6.0f} -> {v['branch']:>6.0f} "
             f"({v['delta']:+.0f}){flag}")
    if any(v["delta"] > 0 for v in res["gold"].values()):
        emit("")
        emit("  REJECTED: the branch drops gold references. Hard rule #8 is a "
             "veto, not a")
        emit("  trade-off — do not weigh this against a win on another axis.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--flag", help="shorthand for --branch-env FLAG=1")
    ap.add_argument("--branch-env", action="append", default=[],
                    help="KEY=VALUE applied to the branch arm only")
    ap.add_argument("--label", default="dynamic-ab")
    ap.add_argument("--max-rows", type=int, default=60)
    ap.add_argument("--batch", type=int, default=12)
    ap.add_argument("--local", action="store_true", default=True)
    ap.add_argument("--endpoint")
    ap.add_argument("--api-key", default=os.getenv("REGENOLD_API_KEY", ""))
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--null-band", type=float, default=0.01,
                    help="half-width under which a zero-spanning CI is a NULL")
    ap.add_argument("--seed", type=int, default=_SEED)
    ap.add_argument("--control-layer", choices=("retrieval", "stage2", "graph"),
                    default=None,
                    help="force the probe-sensitivity control layer "
                         "(default: inferred from the branch flag name)")
    args = ap.parse_args()

    branch_env: dict[str, str] = {}
    if args.flag:
        branch_env[args.flag] = "1"
    for kv in args.branch_env:
        k, _, v = kv.partition("=")
        branch_env[k.strip()] = v.strip()
    if not branch_env:
        ap.error("nothing to A/B — pass --flag or --branch-env")

    res = run(
        branch_env=branch_env, label=args.label, max_rows=args.max_rows,
        batch=args.batch, local=bool(args.local), endpoint=args.endpoint,
        api_key=args.api_key or None, timeout=args.timeout,
        null_band=args.null_band, seed=args.seed,
        control_layer=args.control_layer,
    )
    _report(res)

    _RESULTS.mkdir(parents=True, exist_ok=True)
    out = _RESULTS / f"dynamic-ab-{args.label}.json"
    slim = {k: v for k, v in res.items()
            if k not in ("baseline_rows", "branch_rows")}
    slim["baseline_rows"] = res.get("baseline_rows", [])
    slim["branch_rows"] = res.get("branch_rows", [])
    out.write_text(json.dumps(slim, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")
    # 0 = measured, 2 = lever inert (fix the feature),
    # 3 = probe blind (fix the rows) — a different action, so a different code.
    sys.exit({"INERT": 2, "BLIND_PROBE": 3}.get(res.get("verdict"), 0))


if __name__ == "__main__":
    main()
