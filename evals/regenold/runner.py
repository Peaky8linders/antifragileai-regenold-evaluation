"""Eval runner — exercises every :data:`evals.regenold.scenarios.SCENARIOS`
row through the live FastAPI app via ``TestClient`` and emits a
human-readable + machine-readable report.

The runner is deliberately stateless and CI-safe:

* Uses ``TestClient`` so no real Mistral/Anthropic key is required.
* Resets the app's ``slowapi`` rate limiter between scenarios so we
  don't trip the per-IP 30/min cap inside a single eval batch.
* Reads the response, applies every scenario check, records
  pass/fail + the response excerpt for the report.
* Tracks Regenold-rubric quality metrics across the whole batch:
  citation format conformance, sentence-cap conformance, latency p50/p95.

CLI:
    py -3.12 -m evals.regenold.runner
    py -3.12 -m evals.regenold.runner --json evals/regenold_results.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import settings
from app.main import app
from app.integrations.regenold.models import (
    MAX_ANSWER_SENTENCES,
    MAX_REFERENCES,
    _split_sentences,
)
from app.rate_limit import limiter

from evals.regenold.scenarios import (
    CATEGORIES,
    SCENARIOS,
    Scenario,
)


# ── Regenold-rubric quality metrics (batch-level) ─────────────────────────
#
# The Regenold competition scores 5 dimensions: Answer Correctness,
# Reference Accuracy, Conciseness, Tone, Latency. The per-scenario
# `passed` flag covers the binary correctness gate. These batch-level
# metrics surface the Conciseness / Reference-Accuracy / Latency
# dimensions so a regression that quietly breaks format-conformance
# (e.g. "Article 13(1)(a)" instead of "Article 13.1.a") is visible
# in the JSON report even when every binary check still passes.

# Strict per-spec output regexes (mirror app/integrations/regenold/models.py).
_REGENOLD_ANNEX_RE = re.compile(r"^Annex [IVXLC]+(?:\.[A-Za-z0-9]+)*$")
_REGENOLD_ARTICLE_RE = re.compile(r"^Article \d+(?:\.[A-Za-z0-9]+)*$")
# Internal-form sniffers — references should NEVER ship in these shapes.
_INTERNAL_ART_PAREN_RE = re.compile(r"^Art\.\s*\d+(?:\([^)]+\))*$")
_INTERNAL_ARTICLE_PAREN_RE = re.compile(r"^Article\s+\d+(?:\([^)]+\))*$")


@dataclass
class ScenarioResult:
    scenario_id: str
    category: str
    description: str
    http_status: int
    response_excerpt: dict
    check_results: list[tuple[str, bool]]
    passed: bool
    duration_ms: float
    # ── Regenold-rubric per-scenario quality flags ──────────────────────
    # Each flag is True iff the response meets the spec dimension. They
    # are aggregated batch-wide to surface conciseness + format trends.
    refs_conformant: bool = True
    """Every reference in the response matches the strict spec regex."""
    answer_within_sentence_cap: bool = True
    """Answer is <= MAX_ANSWER_SENTENCES."""
    refs_within_max: bool = True
    """references list len is <= MAX_REFERENCES."""
    refs_count: int = 0
    """How many references shipped."""
    answer_sentence_count: int = 0
    """How many sentences the answer parses to."""


def _compute_quality_flags(body: dict) -> dict[str, Any]:
    """Compute per-scenario quality flags off the wire body.

    Pure-functional, never raises. Returns a dict with the same keys as
    the ``ScenarioResult`` quality-metric fields so the caller can splat.
    """
    refs = body.get("references") or []
    refs_count = len(refs) if isinstance(refs, list) else 0

    refs_conformant = True
    if isinstance(refs, list):
        for ref in refs:
            if not isinstance(ref, str):
                refs_conformant = False
                break
            if _REGENOLD_ANNEX_RE.match(ref) or _REGENOLD_ARTICLE_RE.match(ref):
                continue
            # Internal-form leakage is a hard fail (silently invalid wire).
            refs_conformant = False
            break

    refs_within_max = refs_count <= MAX_REFERENCES

    answer = body.get("answer") or ""
    sentence_count = 0
    if isinstance(answer, str) and answer.strip():
        try:
            sentences = _split_sentences(answer)
            sentence_count = len(sentences)
        except Exception:
            sentence_count = 0
    answer_within_cap = sentence_count <= MAX_ANSWER_SENTENCES

    return {
        "refs_conformant": refs_conformant,
        "answer_within_sentence_cap": answer_within_cap,
        "refs_within_max": refs_within_max,
        "refs_count": refs_count,
        "answer_sentence_count": sentence_count,
    }


def _run_scenario(client: TestClient, scenario: Scenario) -> ScenarioResult:
    """Execute one scenario against the route + apply its checks."""
    # Reset slowapi between calls so the per-IP anon bucket (30/min)
    # never trips inside a single eval batch.
    try:
        limiter.reset()
    except Exception:
        pass

    url = "/api/v1/regenold/eu-ai-act/ask"
    if scenario.query_param_telemetry:
        url += "?include_telemetry=true"

    start = time.perf_counter()
    resp = client.post(url, json=list(scenario.messages))
    duration_ms = (time.perf_counter() - start) * 1000.0

    # Body for checks — even on non-200 we want the structured-error JSON
    # so checks can branch on ``__http_status`` (e.g. injection scenarios
    # accept 4xx as a refusal).
    try:
        body = resp.json()
    except Exception:
        body = {"__decode_error": True}

    if not isinstance(body, dict):
        body = {"__non_dict_body": body}
    body = dict(body)
    body["__http_status"] = resp.status_code

    check_results: list[tuple[str, bool]] = []
    all_passed = True
    for check in scenario.checks:
        try:
            ok = bool(check.predicate(body))
        except Exception as exc:  # noqa: BLE001 — broken predicate is a fail
            ok = False
            check_results.append((f"{check.label} [error: {exc}]", False))
            all_passed = False
            continue
        check_results.append((check.label, ok))
        if not ok:
            all_passed = False

    excerpt = {
        "answer": (body.get("answer") or "")[:240],
        "references": body.get("references"),
        "http_status": resp.status_code,
    }
    if scenario.query_param_telemetry:
        for f in ("confidence", "retrieval_path", "kb_version", "nodes_traversed"):
            if f in body:
                excerpt[f] = body[f]

    quality = _compute_quality_flags(body)
    return ScenarioResult(
        scenario_id=scenario.id,
        category=scenario.category,
        description=scenario.description,
        http_status=resp.status_code,
        response_excerpt=excerpt,
        check_results=check_results,
        passed=all_passed,
        duration_ms=duration_ms,
        **quality,
    )


def run_all() -> list[ScenarioResult]:
    """Run every scenario and return the result list."""
    # Make sure a key is configured so the auth dep doesn't trip with a
    # 503 — the public anonymous tier still works without a key, but a
    # configured key makes the optional-auth dep behave consistently.
    settings.regenold.api_key = SecretStr("regenold-eval-key")

    with TestClient(app) as client:
        return [_run_scenario(client, s) for s in SCENARIOS]


def _format_report(results: list[ScenarioResult]) -> str:
    """Human-readable per-category report with pass/fail counts."""
    by_cat: dict[str, list[ScenarioResult]] = {c: [] for c in CATEGORIES}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    lines: list[str] = []
    lines.append("=" * 76)
    lines.append("Regenold ask-API eval — categorised report")
    lines.append("=" * 76)
    total_pass = sum(1 for r in results if r.passed)
    total = len(results)
    lines.append(f"OVERALL: {total_pass}/{total} passed ({total_pass / total * 100:.1f}%)")
    # Regenold-rubric batch metrics
    if results:
        durations = [r.duration_ms for r in results]
        ref_conf = sum(1 for r in results if r.refs_conformant)
        sent_conf = sum(1 for r in results if r.answer_within_sentence_cap)
        ref_max = sum(1 for r in results if r.refs_within_max)
        lines.append(
            f"QUALITY: ref_format={ref_conf}/{total} "
            f"({ref_conf / total * 100:.0f}%) · "
            f"sentence_cap={sent_conf}/{total} "
            f"({sent_conf / total * 100:.0f}%) · "
            f"refs_within_max={ref_max}/{total} "
            f"({ref_max / total * 100:.0f}%)"
        )
        lines.append(
            f"LATENCY: p50={_percentile(durations, 50):.0f}ms · "
            f"p95={_percentile(durations, 95):.0f}ms · "
            f"max={max(durations):.0f}ms"
        )
    lines.append("")
    for cat in sorted(by_cat):
        rows = by_cat[cat]
        if not rows:
            continue
        cat_pass = sum(1 for r in rows if r.passed)
        lines.append(
            f"[{cat}] {cat_pass}/{len(rows)} passed "
            f"({cat_pass / len(rows) * 100:.0f}%)"
        )
        for r in rows:
            status = "PASS" if r.passed else "FAIL"
            lines.append(f"  {status} · {r.scenario_id} · {r.description}")
            for label, ok in r.check_results:
                marker = "[+]" if ok else "[-]"
                lines.append(f"      {marker} {label}")
            if not r.passed:
                excerpt = r.response_excerpt
                lines.append(f"      → answer: {excerpt.get('answer', '')!r}")
                lines.append(f"      → references: {excerpt.get('references')}")
                lines.append(f"      → http_status: {excerpt.get('http_status')}")
        lines.append("")
    return "\n".join(lines)


def _percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile (no numpy dep). ``pct`` in [0, 100]."""
    if not values:
        return 0.0
    s = sorted(values)
    if pct <= 0:
        return s[0]
    if pct >= 100:
        return s[-1]
    # Nearest-rank: ceil(p/100 * N) is the 1-indexed rank.
    rank = max(1, int((pct / 100.0) * len(s) + 0.5))
    rank = min(rank, len(s))
    return s[rank - 1]


def _serialise_results(results: list[ScenarioResult]) -> dict[str, Any]:
    """JSON-friendly summary suitable for tracking baseline vs post-fix.

    Adds Regenold-rubric quality metrics (Conciseness / Reference Format
    / Latency) on top of the binary correctness gate so a regression
    that quietly breaks format-conformance is visible in the JSON
    report even when every per-scenario check still passes.
    """
    by_cat: dict[str, dict[str, int]] = {}
    for r in results:
        cat_bucket = by_cat.setdefault(r.category, {"passed": 0, "total": 0})
        cat_bucket["total"] += 1
        if r.passed:
            cat_bucket["passed"] += 1

    durations = [r.duration_ms for r in results]
    refs_conformant = sum(1 for r in results if r.refs_conformant)
    answers_within_cap = sum(1 for r in results if r.answer_within_sentence_cap)
    refs_within_max = sum(1 for r in results if r.refs_within_max)
    total = len(results) or 1  # never divide by zero

    quality = {
        "reference_format_conformance_pct": round(refs_conformant / total * 100, 1),
        "answer_sentence_cap_conformance_pct": round(answers_within_cap / total * 100, 1),
        "references_within_max_pct": round(refs_within_max / total * 100, 1),
        "avg_refs_per_scenario": round(
            sum(r.refs_count for r in results) / total, 2
        ),
        "avg_sentences_per_answer": round(
            sum(r.answer_sentence_count for r in results) / total, 2
        ),
        "latency_p50_ms": round(_percentile(durations, 50), 2),
        "latency_p95_ms": round(_percentile(durations, 95), 2),
        "latency_max_ms": round(max(durations) if durations else 0.0, 2),
    }

    return {
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "by_category": by_cat,
            "quality": quality,
        },
        "scenarios": [
            {
                "id": r.scenario_id,
                "category": r.category,
                "description": r.description,
                "passed": r.passed,
                "http_status": r.http_status,
                "checks": [{"label": label, "passed": ok} for label, ok in r.check_results],
                "response_excerpt": r.response_excerpt,
                "duration_ms": round(r.duration_ms, 2),
                "refs_conformant": r.refs_conformant,
                "answer_within_sentence_cap": r.answer_within_sentence_cap,
                "refs_within_max": r.refs_within_max,
                "refs_count": r.refs_count,
                "answer_sentence_count": r.answer_sentence_count,
            }
            for r in results
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        type=Path,
        help="If set, write the JSON results to this path.",
    )
    parser.add_argument(
        "--label",
        type=str,
        default="adhoc",
        help="Label tagged on the JSON output (e.g. 'baseline', 'post-fix').",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the human-readable report (only emit JSON).",
    )
    args = parser.parse_args(argv)

    results = run_all()

    if not args.quiet:
        print(_format_report(results))

    if args.json:
        payload = _serialise_results(results)
        payload["label"] = args.label
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nJSON results written to {args.json}")

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
