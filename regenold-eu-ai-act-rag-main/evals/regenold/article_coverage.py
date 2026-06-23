"""R94 per-article coverage eval set for the EU AI Act RAG surface.

Exports
-------
ARTICLE_COVERAGE_QUESTIONS : list[dict]
    One dict per question with keys:
        id            - unique string identifier
        question      - the question text
        expected_refs - list of "Article N" or "Annex X" strings (gold)
        kind          - "article" | "annex" | "usecase"

CLI
---
    # Print counts by kind (no network)
    python -m evals.regenold.article_coverage

    # Run all questions through the TestClient and print a scorecard
    python -m evals.regenold.article_coverage --run

    # Smoke: cap at 20 rows
    python -m evals.regenold.article_coverage --run --limit 20
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any

# ── Question templates ────────────────────────────────────────────────────
# Rotated across articles to avoid phrasing bias on the eval.

_ARTICLE_TEMPLATES = [
    "What does Article {n} of the EU AI Act require?",
    "What are the obligations under Article {n} of the EU AI Act?",
    "Explain Article {n} of the EU AI Act.",
    "What does Article {n} cover in the EU AI Act?",
]

_ANNEX_TEMPLATES = [
    "What is listed in Annex {r} of the EU AI Act?",
    "What does Annex {r} of the EU AI Act contain?",
    "Explain the content of Annex {r} of the EU AI Act.",
]

# Roman numerals for Annexes I–XIII
_ROMAN = [
    "I", "II", "III", "IV", "V", "VI", "VII",
    "VIII", "IX", "X", "XI", "XII", "XIII",
]


def _article_question(n: int) -> dict:
    tmpl = _ARTICLE_TEMPLATES[(n - 1) % len(_ARTICLE_TEMPLATES)]
    return {
        "id": f"art_{n:03d}",
        "question": tmpl.format(n=n),
        "expected_refs": [f"Article {n}"],
        "kind": "article",
    }


def _annex_question(idx: int) -> dict:
    """idx is 0-based (0 = Annex I)."""
    roman = _ROMAN[idx]
    tmpl = _ANNEX_TEMPLATES[idx % len(_ANNEX_TEMPLATES)]
    return {
        "id": f"annex_{roman}",
        "question": tmpl.format(r=roman),
        "expected_refs": [f"Annex {roman}"],
        "kind": "annex",
    }


# ── Per-article + annex entries ───────────────────────────────────────────

_ARTICLE_ENTRIES: list[dict] = [_article_question(n) for n in range(1, 114)]
_ANNEX_ENTRIES: list[dict] = [_annex_question(i) for i in range(13)]

# ── Use-case entries ──────────────────────────────────────────────────────
# 3 verbatim user MedTech questions + 7 diverse healthcare/general use-cases.

_USECASE_ENTRIES: list[dict] = [
    # ── 3 verbatim user questions ─────────────────────────────────────────
    {
        "id": "uc_art111_medtech_providers_deployers",
        "question": (
            "How would article 111(2) of the EU AI Act apply to MedTech and "
            "Healthcare AI, for both providers and deployers?"
        ),
        "expected_refs": ["Article 111"],
        "kind": "usecase",
    },
    {
        "id": "uc_art111_medtech_transition_grandfathering",
        "question": (
            "Are MedTech high-risk AI systems placed on the market or put into "
            "service before August 2, 2026, sit outside the EU AI Act's "
            "substantive obligations?"
        ),
        "expected_refs": ["Article 111"],
        "kind": "usecase",
    },
    {
        "id": "uc_art6_annex1_medtech_timeline",
        "question": (
            "How does the specific timeline for compliance apply to a Medtech "
            "high risk AI system as stated within article 6(1) of the EU AI Act "
            "and Annex I ?"
        ),
        "expected_refs": ["Article 6", "Annex I"],
        "kind": "usecase",
    },
    # ── 7 diverse healthcare/MedTech + general use-cases ─────────────────
    {
        "id": "uc_art5_emotion_recognition_prohibition",
        "question": (
            "Is the use of AI systems for real-time emotion recognition of "
            "patients in a clinical healthcare setting prohibited under the "
            "EU AI Act?"
        ),
        "expected_refs": ["Article 5"],
        "kind": "usecase",
    },
    {
        "id": "uc_art43_conformity_assessment_diagnostic_ai",
        "question": (
            "What conformity assessment procedure must a provider follow for a "
            "high-risk AI diagnostic imaging system used in radiology before "
            "placing it on the EU market?"
        ),
        "expected_refs": ["Article 43"],
        "kind": "usecase",
    },
    {
        "id": "uc_art13_transparency_patients",
        "question": (
            "What transparency obligations apply to a hospital that deploys a "
            "high-risk AI system that generates clinical recommendations shown "
            "to patients?"
        ),
        "expected_refs": ["Article 13"],
        "kind": "usecase",
    },
    {
        "id": "uc_art10_data_governance_clinical_training",
        "question": (
            "What data governance and data quality requirements must a MedTech "
            "provider satisfy when using clinical patient data to train a "
            "high-risk AI system?"
        ),
        "expected_refs": ["Article 10"],
        "kind": "usecase",
    },
    {
        "id": "uc_art14_human_oversight_triage_ai",
        "question": (
            "What human oversight measures must a hospital deployer implement "
            "when using an AI-powered patient triage system in an emergency "
            "department?"
        ),
        "expected_refs": ["Article 14"],
        "kind": "usecase",
    },
    {
        "id": "uc_art73_serious_incident_medical_ai",
        "question": (
            "What are the obligations of a deployer when a serious incident "
            "occurs involving a high-risk AI system used for medical diagnosis "
            "in a hospital?"
        ),
        "expected_refs": ["Article 73"],
        "kind": "usecase",
    },
    {
        "id": "uc_art27_fria_public_hospital",
        "question": (
            "When must a public hospital that deploys a high-risk AI system "
            "for patient triage conduct a fundamental rights impact assessment "
            "under the EU AI Act?"
        ),
        "expected_refs": ["Article 27"],
        "kind": "usecase",
    },
]

# ── Public export ─────────────────────────────────────────────────────────

ARTICLE_COVERAGE_QUESTIONS: list[dict] = (
    _ARTICLE_ENTRIES + _ANNEX_ENTRIES + _USECASE_ENTRIES
)

# ── Local TestClient runner ───────────────────────────────────────────────

_LOCAL_EVAL_API_KEY = "regenold-eval-key"
_PATH = "/api/v1/regenold/eu-ai-act/ask"


def _ensure_local_auth(api_key: str | None = None) -> str:
    """Provision in-process Regenold API key (mirrors runner_v2._ensure_local_auth)."""
    from pydantic import SecretStr
    from app.config import settings

    key = api_key or _LOCAL_EVAL_API_KEY
    current = settings.regenold.api_key
    if current is None or current.get_secret_value() != key:
        settings.regenold.api_key = SecretStr(key)
    return key


def _ref_base(ref: str) -> str:
    """Strip sub-point suffixes: 'Article 111.2' → 'Article 111'."""
    ref = ref.strip()
    for sep in (".", "("):
        if sep in ref.split(" ", 2)[-1]:
            ref = ref[: ref.index(sep, ref.index(" ") + 1)]
    return ref.strip()


def _passes(expected_refs: list[str], returned_refs: list[str]) -> bool:
    """True iff every expected ref (base-normalised) appears in returned_refs."""
    returned_bases = {_ref_base(r) for r in returned_refs}
    for exp in expected_refs:
        if _ref_base(exp) not in returned_bases:
            return False
    return True


def _run(limit: int | None = None) -> None:
    os.environ.setdefault("REGENOLD_SKIP_STARTUP_LOG", "1")

    from fastapi.testclient import TestClient
    from app.main import app as _app
    # Reset the slowapi partner-tier rate limiter before each request so a
    # 136-row TestClient sweep doesn't trip HTTP 429 (mirrors
    # evals/regenold/runner.py + evals/bench/runner.py).
    from app.rate_limit import limiter

    questions = ARTICLE_COVERAGE_QUESTIONS
    if limit is not None:
        questions = questions[:limit]

    local_key = _ensure_local_auth()
    headers = {"X-Regenold-Api-Key": local_key}

    total = len(questions)
    passed = 0
    kind_total: dict[str, int] = {}
    kind_passed: dict[str, int] = {}
    failures: list[dict] = []

    print(f"\nRunning {total} coverage questions through TestClient...\n")

    with TestClient(_app) as client:
        for entry in questions:
            qid = entry["id"]
            question = entry["question"]
            expected = entry["expected_refs"]
            kind = entry["kind"]

            kind_total[kind] = kind_total.get(kind, 0) + 1

            t0 = time.perf_counter()
            try:
                try:
                    limiter.reset()
                except Exception:  # noqa: BLE001 — best-effort limiter reset
                    pass
                resp = client.post(
                    _PATH,
                    json={"messages": [{"role": "user", "content": question}]},
                    headers=headers,
                    timeout=30,
                )
                elapsed_ms = (time.perf_counter() - t0) * 1000
                if resp.status_code != 200:
                    error = f"HTTP {resp.status_code}"
                    body: dict[str, Any] = {}
                else:
                    body = resp.json()
                    error = None
            except Exception as exc:  # noqa: BLE001
                elapsed_ms = (time.perf_counter() - t0) * 1000
                error = str(exc)[:120]
                body = {}

            returned_refs: list[str] = body.get("references", [])

            if error:
                ok = False
                failures.append({
                    "id": qid,
                    "kind": kind,
                    "expected": expected,
                    "actual": [],
                    "error": error,
                })
            elif _passes(expected, returned_refs):
                ok = True
            else:
                ok = False
                failures.append({
                    "id": qid,
                    "kind": kind,
                    "expected": expected,
                    "actual": returned_refs[:6],
                })

            if ok:
                passed += 1
                kind_passed[kind] = kind_passed.get(kind, 0) + 1

    # ── Scorecard ──────────────────────────────────────────────────────────
    pass_rate = passed / total if total else 0.0
    print("=" * 60)
    print(f"  COVERAGE SCORECARD  (n={total})")
    print("=" * 60)
    print(f"  Overall:  {passed}/{total}  ({pass_rate:.1%})")
    print()
    for kind in ["article", "annex", "usecase"]:
        kt = kind_total.get(kind, 0)
        kp = kind_passed.get(kind, 0)
        if kt:
            print(f"  {kind:<10s}:  {kp}/{kt}  ({kp / kt:.1%})")
    print()

    # First 15 failures
    if failures:
        show = failures[:15]
        print(f"  First {len(show)} failing rows:")
        print("-" * 60)
        for f in show:
            err_part = f"  [ERR: {f['error']}]" if "error" in f else ""
            actual_str = ", ".join(f.get("actual", []))[:60]
            exp_str = ", ".join(f["expected"])
            print(f"  {f['id']} ({f['kind']})")
            print(f"    expected: {exp_str}")
            if not err_part:
                print(f"    actual  : {actual_str}")
            else:
                print(f"    {err_part.strip()}")
        print("-" * 60)
    else:
        print("  All rows passed!")

    print()


# ── __main__ ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="R94 article coverage eval")
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run questions through TestClient and print scorecard",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Cap the number of rows (for smoke runs)",
    )
    args = parser.parse_args()

    if args.run:
        _run(limit=args.limit)
    else:
        # Default: print counts by kind
        kinds: dict[str, int] = {}
        for q in ARTICLE_COVERAGE_QUESTIONS:
            k = q["kind"]
            kinds[k] = kinds.get(k, 0) + 1
        print(f"ARTICLE_COVERAGE_QUESTIONS breakdown (total={len(ARTICLE_COVERAGE_QUESTIONS)}):")
        for k, n in kinds.items():
            print(f"  {k}: {n}")
        sys.exit(0)
