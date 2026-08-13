"""End-to-End test: AWS Bedrock EU cross-region RAG generation + LLM-judge scoring.

Exercises the full wire path with ``P2P_GRAPH_RAG_PROVIDER=bedrock``:

  1. ``POST /api/v1/regenold/eu-ai-act/ask`` — Stage-1 + Stage-2 over Bedrock.
  2. ``evals.judge.runner`` — the 4-axis judge, also over Bedrock.

Model targets (operator ask, 2026-08-11):

  * main RAG   — ``eu.anthropic.claude-opus-4-8``
  * LLM judge  — ``eu.anthropic.claude-sonnet-5``

Both are ACTIVE ``SYSTEM_DEFINED`` EU cross-region inference profiles. Whether
this ACCOUNT may invoke them is a separate entitlement, checked by the preflight
below — the catalog listing a profile does NOT imply access to it.

Override either target per-run::

    REGENOLD_BEDROCK_MODEL=eu.anthropic.claude-opus-4-6-v1
    REGENOLD_BEDROCK_JUDGE_MODEL=eu.anthropic.claude-sonnet-4-6

Pass ``--fallback`` to auto-substitute the newest ENTITLED tier when the
requested profiles are denied, so the pipeline can still be proven end-to-end.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Runnable as `py scripts/e2e_...py` as well as `py -m scripts.e2e_...`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

# ── Requested configuration ──────────────────────────────────────────────────
# IMPORTED, never re-declared. A local copy of these constants is how the
# preflight ends up certifying a tier production does not call — it passed on
# opus-4-6 while the engine routed complex questions to opus-5.
from app.engines._graph_rag_impl import (  # noqa: E402
    BEDROCK_COMPLEX_MODEL as COMPLEX_MODEL,
)
from app.engines._graph_rag_impl import (  # noqa: E402
    BEDROCK_RAG_MODEL as RAG_MODEL,
)

REGION = "eu-central-1"
JUDGE_MODEL = os.getenv("REGENOLD_BEDROCK_JUDGE_MODEL", "").strip() or "eu.anthropic.claude-sonnet-5"

# Newest tier this account was measured to be ENTITLED to (2026-08-13). Used
# only with --fallback, to prove the pipeline while entitlement is pending.
RAG_FALLBACK = "eu.anthropic.claude-opus-4-6-v1"
COMPLEX_FALLBACK = "eu.anthropic.claude-opus-4-6-v1"
JUDGE_FALLBACK = "eu.anthropic.claude-sonnet-4-6"

os.environ["P2P_GRAPH_RAG_PROVIDER"] = "bedrock"
os.environ.setdefault("BEDROCK_REGION", REGION)
os.environ.setdefault("REGENOLD_BEDROCK_MODEL", RAG_MODEL)
os.environ.setdefault("REGENOLD_BEDROCK_COMPLEX_MODEL", COMPLEX_MODEL)
os.environ.setdefault("REGENOLD_BEDROCK_JUDGE_MODEL", JUDGE_MODEL)
os.environ["REGENOLD_SKIP_STARTUP_LOG"] = "1"


def _probe(model_id: str) -> tuple[bool, str]:
    """Return ``(invocable, detail)`` for one profile id — a real 5-token call."""
    from app.llm.bedrock_client import BedrockRequest, get_bedrock_provider

    resp = get_bedrock_provider().complete(
        BedrockRequest(user="Reply with exactly: OK", model=model_id,
                       max_tokens=16, temperature=0.0)
    )
    if resp.error:
        return False, resp.error
    return True, f"{resp.elapsed_ms} ms, {resp.output_tokens} out-tokens"


def preflight(allow_fallback: bool) -> bool:
    """Verify credentials, Region and per-model entitlement BEFORE the run.

    Returns True if the run can proceed. Mutates the model env vars when
    ``allow_fallback`` and the requested profile is denied.
    """
    from app.llm.bedrock_client import (
        EU_INFERENCE_REGIONS,
        _resolve_region,
        is_bedrock_provider_enabled,
    )

    print("=" * 82)
    print(" PREFLIGHT — credentials, Region, per-model entitlement")
    print("=" * 82)

    if not is_bedrock_provider_enabled():
        print("  FAIL: no Bedrock credentials. Set AWS_BEARER_TOKEN_BEDROCK "
              "(or AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY).")
        return False

    region = _resolve_region()
    in_eu = region in EU_INFERENCE_REGIONS
    print(f"  region                : {region} "
          f"({'in EU geography' if in_eu else 'NOT in EU geography'})")
    if not in_eu:
        print(f"  FAIL: 'eu.' inference profiles are unresolvable from {region}. "
              f"Set BEDROCK_REGION to one of {sorted(EU_INFERENCE_REGIONS)}.")
        return False

    ok = True
    for label, env_var, requested, fallback in (
        ("main RAG", "REGENOLD_BEDROCK_MODEL", RAG_MODEL, RAG_FALLBACK),
        ("complex tier", "REGENOLD_BEDROCK_COMPLEX_MODEL", COMPLEX_MODEL, COMPLEX_FALLBACK),
        ("LLM judge", "REGENOLD_BEDROCK_JUDGE_MODEL", JUDGE_MODEL, JUDGE_FALLBACK),
    ):
        target = os.environ[env_var]
        invocable, detail = _probe(target)
        if invocable:
            print(f"  {label:<21}: {target}  OK ({detail})")
            continue

        print(f"  {label:<21}: {target}  DENIED — {detail}")
        if not allow_fallback:
            ok = False
            continue

        alt = fallback if target == requested else target
        alt_ok, alt_detail = _probe(alt)
        if alt_ok:
            os.environ[env_var] = alt
            print(f"  {'':<21}  -> falling back to {alt}  OK ({alt_detail})")
        else:
            print(f"  {'':<21}  -> fallback {alt} also DENIED — {alt_detail}")
            ok = False

    if not ok:
        print()
        print("  Requested profiles are ACTIVE in the Region but NOT entitled to this")
        print("  account. Grant access in the Bedrock console (Model access) for the")
        print("  region above, then re-run. Use --fallback to prove the pipeline on the")
        print("  newest entitled tier meanwhile.")
    print()
    return ok


def run_e2e_test(question: str) -> int:
    from fastapi.testclient import TestClient

    from app.main import app
    from evals.judge import runner as judge_runner

    rag_model = os.environ["REGENOLD_BEDROCK_MODEL"]
    judge_model = os.environ["REGENOLD_BEDROCK_JUDGE_MODEL"]

    print("=" * 82)
    print(" AWS BEDROCK EU CROSS-REGION RAG & LLM JUDGE EVALUATION")
    print("=" * 82)
    print(f"  provider     : {os.getenv('P2P_GRAPH_RAG_PROVIDER')}")
    print(f"  region       : {os.getenv('BEDROCK_REGION')}")
    print(f"  RAG model    : {rag_model}")
    print(f"  complex model: {os.environ['REGENOLD_BEDROCK_COMPLEX_MODEL']}")
    print(f"  judge model  : {judge_model}")
    print(f"  question     : {question!r}")
    print("-" * 82)

    # ── 1. RAG ───────────────────────────────────────────────────────────────
    print(f"\n[Step 1/2] Invoking RAG engine via Bedrock ({rag_model})...")
    client = TestClient(app)

    t0 = time.monotonic()
    response = client.post(
        "/api/v1/regenold/eu-ai-act/ask",
        json={"messages": [{"role": "user", "content": question}]},
        headers={"X-Regenold-Api-Key": os.getenv("P2P_REGENOLD_API_KEY", "test-key")},
    )
    rag_elapsed_ms = int((time.monotonic() - t0) * 1000)

    print(f"  HTTP {response.status_code} in {rag_elapsed_ms} ms")
    if response.status_code != 200:
        print(f"  ERROR body: {response.text[:2000]}")
        return 1

    data = response.json()
    answer_text = data.get("answer", "")
    references = data.get("references", [])

    print("\n--- ANSWER ---")
    print(answer_text)
    print("\n--- REFERENCES ---")
    print(json.dumps(references, indent=2))

    if not answer_text.strip():
        print("\n  FAIL: empty answer.")
        return 1

    # A Bedrock Stage-2 that silently fell back to deterministic is the inert-run
    # trap: the wire looks fine and nothing was measured. Latency is the tell.
    print(f"\n  answer chars: {len(answer_text)}  refs: {len(references)}  "
          f"latency: {rag_elapsed_ms} ms")
    if rag_elapsed_ms < 2000:
        print("  ⚠ WARNING: sub-2s latency — Stage-2 likely did NOT reach Bedrock "
              "(deterministic fallback or engine cache hit). Treat as INERT.")

    # ── 2. Judge ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 82)
    print(f"[Step 2/2] LLM judge via Bedrock ({judge_model})...")
    print("=" * 82)

    row = {
        "id": "e2e-bedrock-test-1",
        "question": question,
        "predicted_answer": answer_text,
        "pred_answer": answer_text,
        "answer": answer_text,
        "predicted_refs": references,
        "pred_refs": references,
        "article_refs": references,
    }

    t1 = time.monotonic()
    caller = judge_runner._resolve_caller("bedrock", timeout_s=90.0)
    judged = judge_runner._judge_row(row, {}, caller)
    judge_elapsed_ms = int((time.monotonic() - t1) * 1000)

    print(f"\n  judged in {judge_elapsed_ms} ms")
    print("\n--- SCORECARD ---")
    verdicts = judged.get("judge") or judged.get("verdicts") or {}
    errors: list[str] = []
    passes = 0
    for axis, result in verdicts.items():
        if not isinstance(result, dict):
            continue
        if result.get("judge_error"):
            errors.append(f"{axis}: {result['judge_error']}")
            print(f"  [{axis:<24}] ERROR — {result['judge_error'][:100]}")
            continue
        verdict = str(result.get("verdict", "unknown")).upper()
        if verdict == "PASS":
            passes += 1
        reason = result.get("reason") or result.get("explanation") or ""
        print(f"  [{axis:<24}] {verdict}")
        if reason:
            print(f"      {reason[:160]}")

    print("\nFull judge payload:")
    print(json.dumps(verdicts, indent=2, default=str)[:4000])

    print("\n" + "=" * 82)
    if errors:
        print(f" JUDGE INCOMPLETE — {len(errors)} axis error(s): {errors}")
        return 1
    if not verdicts:
        print(" JUDGE RETURNED NOTHING — no axes scored.")
        return 1
    print(f" E2E COMPLETE — RAG answered over Bedrock, judge scored "
          f"{passes}/{len(verdicts)} axes PASS.")
    print("=" * 82)
    return 0


if __name__ == "__main__":
    argv = [a for a in sys.argv[1:] if a != "--fallback"]
    allow_fallback = "--fallback" in sys.argv[1:]

    if not preflight(allow_fallback):
        sys.exit(2)

    q = " ".join(argv) if argv else (
        "What are the prohibited AI practices under Article 5 of the EU AI Act?"
    )
    sys.exit(run_e2e_test(q))
