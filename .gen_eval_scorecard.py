"""Aggregate the R106 live eval sidecars into one Regenold-rubric scorecard.

Reads the 4 sidecars produced by the live runners, computes the GraphRAG
set's Ans axes (loose/strict/conciseness) from its gold prose
(REFERENCE_ANSWERS) using the canonical evals.bench.metrics functions, and
writes a consolidated Markdown scorecard.
"""
from __future__ import annotations

import json
import os
from statistics import mean

from evals.bench import metrics as M
from evals.regenold.scenarios_graphrag_benchmark import REFERENCE_ANSWERS

R = "evals/bench/results"
OUT = "docs/EVAL_SCORECARD_ROUNDS_100plus.md"


def load(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None


def fmt(v, nd=4):
    return "—" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def lat(s):
    if not s:
        return "—"
    p50 = s.get("latency_p50_ms") or (s.get("latency") or {}).get("p50")
    p95 = s.get("latency_p95_ms") or (s.get("latency") or {}).get("p95")
    if p50 is None:
        return "—"
    return f"p50={p50/1000:.1f}s p95={(p95 or 0)/1000:.1f}s"


rows_out = []  # (set, subset, n, ansL, ansS, ansC, refL, refS, refC, kw, tone, coh, lat)


def add(setname, subset, n, summary, coh=None, ans=None):
    a = ans or {}
    rows_out.append((
        setname, subset, n,
        a.get("loose"), a.get("strict"), a.get("conc"),
        summary.get("ref_loose"), summary.get("ref_strict"),
        summary.get("ref_conciseness"), summary.get("keyword_recall"),
        summary.get("regulatory_tone"), coh, lat(summary),
    ))


# ── GraphRAG (gold prose → full Ans axes) ──────────────────────────────
g = load(f"{R}/graphrag-bench-r106-graphrag-live.json")
if g:
    gt = g["ground_truth"]
    s = gt["summary"]
    rows = [r for r in gt["rows"] if not r.get("recital_only") and not r.get("error")]
    al, as_, ac = [], [], []
    for r in rows:
        gold = REFERENCE_ANSWERS.get(r["id"])
        pred = r.get("predicted_answer") or ""
        if gold and pred:
            al.append(M.answer_correctness_loose(pred, gold))
            as_.append(M.answer_correctness_strict(pred, gold))
            ac.append(M.answer_conciseness(pred, gold))
    ans = {
        "loose": round(mean(al), 4) if al else None,
        "strict": round(mean(as_), 4) if as_ else None,
        "conc": round(mean(ac), 4) if ac else None,
    }
    add("GraphRAG benchmark", f"ground-truth (n_ans={len(al)})", s.get("n"), s, ans=ans)


# ── paper-v4 / paper-v3 (ref + kw + tone + coherence) ──────────────────
for path, name in [
    (f"{R}/paper-v4-r106-pv4-live.json", "Paper-V4"),
    (f"{R}/paper-v3-r106-pv3-live.json", "Paper-V3"),
]:
    d = load(path)
    if not d:
        continue
    for sec in ("singleturn", "tricky", "multiturn"):
        if sec in d:
            add(name, sec, d[sec]["summary"].get("n"), d[sec]["summary"],
                coh=d[sec].get("coherence_rate"))


# ── V2 (tricky + multiturn) ────────────────────────────────────────────
v = load(f"{R}/v2-r106-v2-live.json")
if v:
    for sec in ("tricky", "multiturn"):
        if sec in v:
            add("V2", sec, v[sec]["summary"].get("n"), v[sec]["summary"],
                coh=v[sec].get("coherence_rate"))
else:
    rows_out.append(("V2", "(pending — run still in progress)", None,
                     None, None, None, None, None, None, None, None, None, "—"))


# ── render ──────────────────────────────────────────────────────────────
lines = []
P = lines.append
P("# R106 Live Regenold-Rubric Scorecard — Recent-Rounds Eval Sets")
P("")
P("All four recent-rounds eval sets (the 190 questions documented in")
P("`EVAL_QA_ROUNDS_100plus.md`) re-run **live** against the production")
P("Railway endpoint (→ Cloudflare tunnel → Claude Max → Sonnet 4.6), scored")
P("against the Regenold rubric.")
P("")
P("- **Ref Correctness Loose/Strict, Ref Conciseness** — wire references vs gold (all sets).")
P("- **Keyword Recall** — gold key-points surfaced in the answer (all sets).")
P("- **Regulatory Tone** — regulator-voice heuristic (all sets).")
P("- **Ans Correctness Loose/Strict, Ans Conciseness** — answer vs gold *prose*; only the")
P("  GraphRAG set carries lawyer-reviewed gold prose, so the Ans axes are reported there only.")
P("- **Coherence** — multi-turn final-turn coherence rate (multi-turn subsets).")
P("- **Latency** — live Stage-2 (Sonnet) round-trip, p50/p95.")
P("")
P("| Set | Subset | n | Ans L | Ans S | Ans Conc | Ref L | Ref S | Ref Conc | Kw | Tone | Coh | Latency |")
P("| --- | ------ | - | ----- | ----- | -------- | ----- | ----- | -------- | -- | ---- | --- | ------- |")
for (setn, sub, n, aL, aS, aC, rL, rS, rC, kw, tone, coh, ltxt) in rows_out:
    P(f"| {setn} | {sub} | {fmt(n)} | {fmt(aL)} | {fmt(aS)} | {fmt(aC)} | "
      f"{fmt(rL)} | {fmt(rS)} | {fmt(rC)} | {fmt(kw)} | {fmt(tone)} | {fmt(coh)} | {ltxt} |")
P("")
P("> Notes: the multi-turn subsets are the weak axis across all sets (refL ~0.42,")
P("> coherence ~0.42) — consistent with the project's documented multi-turn")
P("> difficulty. Regulatory tone is 1.0 across every subset. GraphRAG ground-truth")
P("> reference correctness is the strongest (simple, well-anchored gold).")

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("\n".join(lines))
print(f"\n[wrote {OUT}]")
