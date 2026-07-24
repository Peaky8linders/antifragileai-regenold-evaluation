"""R290 — assemble every answered batch question into one markdown report.

Reads the checkpoint sidecars written by
:mod:`evals.regenold.run_official_batch` (easy + hard) and
:mod:`evals.regenold.run_june_batch`, and emits a single markdown file
containing every question with its live answer and references.

Reads the ``.ckpt.jsonl`` checkpoints rather than the final ``.json``
summaries, so a partially-completed or interrupted run still produces a
complete report of everything answered so far.

Usage
-----
    python -m evals.regenold.build_batch_report \\
        --label r290-live \\
        --out docs/reviews/R290-live-batch-answers.md
"""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_RESULTS = _REPO / "evals" / "bench" / "results"


def _read_ckpt(path: Path) -> list[dict[str, Any]]:
    """Read a checkpoint jsonl, keeping the LAST record per id (re-runs win)."""
    if not path.exists():
        return []
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid = str(rec.get("id") or len(by_id))
        if rid not in by_id:
            order.append(rid)
        by_id[rid] = rec
    return [by_id[r] for r in order]


def _fmt_refs(refs: list[str]) -> str:
    return ", ".join(str(r) for r in refs) if refs else "_(none)_"


def _section(title: str, note: str, rows: list[dict[str, Any]]) -> list[str]:
    out: list[str] = [f"\n---\n\n# {title}\n", f"{note}\n"]
    ok = [r for r in rows if not r.get("error")]
    errs = [r for r in rows if r.get("error")]

    if rows:
        lats = [r["latency_ms"] for r in ok if r.get("latency_ms")]
        refcounts = [len(r.get("pred_refs") or []) for r in ok]
        out.append(
            f"**{len(ok)} answered** · {len(errs)} errored · "
            f"mean refs {statistics.mean(refcounts):.2f} · "
            f"p50 latency {statistics.median(lats) / 1000:.1f}s\n"
            if ok
            else f"**0 answered** · {len(errs)} errored\n"
        )

    for i, rec in enumerate(rows, 1):
        qid = rec.get("id", f"row_{i}")
        out.append(f"\n## {i}. `{qid}`\n")
        out.append(f"**Q:** {rec.get('question', '').strip()}\n")
        if rec.get("error"):
            out.append(f"\n**ERROR:** `{rec['error']}` (HTTP {rec.get('http_status')})\n")
            continue
        answer = (rec.get("pred_answer") or "").strip()
        out.append(f"\n**A:** {answer}\n")
        out.append(f"\n**References:** {_fmt_refs(rec.get('pred_refs') or [])}\n")

        # Hard mode records both turns. ``pred_answer`` above is already the
        # post-pushback answer (the graded one); show turn 1 for the diff.
        if rec.get("pushback_answer"):
            turn1 = (rec.get("turn1_answer") or "").strip()
            if turn1 and turn1 != answer:
                out.append(f"\n<details><summary>Turn 1 (pre-pushback)</summary>\n\n{turn1}\n\n")
                out.append(f"References: {_fmt_refs(rec.get('turn1_refs') or [])}\n\n</details>\n")
            pb = rec.get("pushback") or {}
            conceded = pb.get("conceded")
            if conceded is not None:
                out.append(f"\n**Conceded to pushback:** `{conceded}`\n")

        meta = []
        if rec.get("latency_ms"):
            meta.append(f"{rec['latency_ms'] / 1000:.1f}s")
        vs = rec.get("vs_june") or rec.get("vs_jul07")
        if vs:
            added = vs.get("ref_head_added") or []
            dropped = vs.get("ref_head_dropped") or []
            if added:
                meta.append(f"refs added vs prior: {', '.join(added)}")
            if dropped:
                meta.append(f"refs dropped vs prior: {', '.join(dropped)}")
        if meta:
            out.append(f"\n<sub>{' · '.join(meta)}</sub>\n")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--endpoint", default="(live production wire)")
    args = ap.parse_args()

    sources = [
        (
            _RESULTS / f"official-{args.label}-easy.ckpt.jsonl",
            "Batch 1 — Regenold official set, EASY mode",
            "Each question asked standalone (single turn), exactly as the "
            "graded 2026-07-07 run posed it.",
        ),
        (
            _RESULTS / f"official-{args.label}-hard.ckpt.jsonl",
            "Batch 2 — Regenold official set, HARD mode",
            "The same questions inside a growing multi-turn conversation, "
            "followed by the adversarial pushback turn "
            "(*\"I don't think this is correct. Perhaps your answer contains "
            "hallucinations...\"*). The graded answer is the post-pushback one.",
        ),
        (
            _RESULTS / f"june-{args.label}.ckpt.jsonl",
            "Batch 3 — end-of-June set (2026-06-29 production audit + Antifragile review)",
            "The question set captured in `regenold_questions_and_live_answers.md`, "
            "re-asked against the current deployment so June and now can be diffed.",
        ),
    ]

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    doc: list[str] = [
        f"# Regenold live batch answers — `{args.label}`\n",
        f"\nGenerated {stamp} · endpoint: {args.endpoint}\n",
        "\nEvery question below was asked against the live wire and the answer "
        "recorded verbatim, including its reference list.\n",
    ]

    totals: list[str] = []
    all_sections: list[str] = []
    for path, title, note in sources:
        rows = _read_ckpt(path)
        if not rows:
            totals.append(f"- {title}: _no checkpoint found ({path.name})_")
            continue
        ok = sum(1 for r in rows if not r.get("error"))
        totals.append(f"- {title}: **{ok} answered** / {len(rows)} rows")
        all_sections.extend(_section(title, note, rows))

    doc.append("\n## Contents\n\n" + "\n".join(totals) + "\n")
    doc.extend(all_sections)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = _REPO / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(doc), encoding="utf-8")
    print(f"wrote {out_path}  ({out_path.stat().st_size / 1024:.0f} KB)")
    for t in totals:
        print("  " + t)


if __name__ == "__main__":
    main()
