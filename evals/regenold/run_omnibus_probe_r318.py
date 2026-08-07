"""R318 — run the adversarial Digital-Omnibus probe against a live wire.

    py -3.12 -m evals.regenold.run_omnibus_probe_r318 \
        --endpoint http://127.0.0.1:8100/api/v1/regenold/eu-ai-act/ask \
        --api-key "$P2P_REGENOLD_API_KEY" --label r318-omnibus

Exit codes:
    0  every probe clean (no forbidden Omnibus content) and the control answered
    1  at least one probe leaked Omnibus content, or the control regressed
    2  transport failure

This is a LIVE check by construction: the thing under test is whether a frontier
model volunteers Digital Omnibus content from its own parametric knowledge, and
the deterministic path never invokes the model at all.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from evals.bench._http_retry import post_json_with_retry  # noqa: E402
from evals.regenold.scenarios_omnibus_probe_r318 import (  # noqa: E402
    GLOBAL_FORBIDDEN,
    OMNIBUS_PROBES,
)

RESULTS = REPO / "evals" / "bench" / "results"


def _messages(probe: dict) -> list[dict]:
    if "messages" in probe:
        return [dict(m) for m in probe["messages"]]
    return [{"role": "user", "content": probe["question"]}]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--api-key", default="")
    ap.add_argument("--label", default="r318-omnibus")
    ap.add_argument("--timeout", type=float, default=150.0)
    args = ap.parse_args()

    rows: list[dict] = []
    leaks = 0
    misses = 0
    errors = 0

    for probe in OMNIBUS_PROBES:
        # Signature is (url, messages, api_key, timeout) — the helper builds the
        # {"messages": [...]} envelope and the X-Regenold-Api-Key header itself.
        body, lat, status, err, *_ = post_json_with_retry(
            args.endpoint,
            _messages(probe),
            args.api_key or None,
            args.timeout,
        )
        if err or status != 200 or not isinstance(body, dict):
            errors += 1
            rows.append({"id": probe["id"], "error": err or f"http {status}"})
            print(f"  [ERR ] {probe['id']}: {err or status}")
            continue

        answer = str(body.get("answer") or "")
        refs = body.get("references") or []
        low = answer.lower()

        hit = [f for f in GLOBAL_FORBIDDEN if f in low]
        want = probe.get("must_contain") or ()
        got_required = (not want) or any(w.lower() in low for w in want)

        if hit:
            leaks += 1
        if not got_required:
            misses += 1

        mark = "LEAK" if hit else ("MISS" if not got_required else "ok  ")
        print(f"  [{mark}] {probe['id']:<28} {lat:6.0f}ms refs={refs}")
        if hit:
            print(f"         FORBIDDEN: {hit}")
        if not got_required:
            print(f"         expected one of: {want}")
        if hit or not got_required:
            print(f"         answer: {answer[:320]}")

        rows.append(
            {
                "id": probe["id"],
                "category": probe["category"],
                "answer": answer,
                "references": refs,
                "forbidden_hits": hit,
                "required_satisfied": got_required,
                "latency_ms": lat,
            }
        )

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"omnibus-probe-{args.label}.json"
    out.write_text(
        json.dumps(
            {
                "label": args.label,
                "endpoint": args.endpoint,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "n": len(OMNIBUS_PROBES),
                "leaks": leaks,
                "required_misses": misses,
                "errors": errors,
                "rows": rows,
            },
            indent=1,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(
        f"OMNIBUS PROBE: n={len(OMNIBUS_PROBES)} leaks={leaks} "
        f"required_misses={misses} errors={errors}"
    )
    print(f"sidecar: {out}")

    if errors and not rows:
        return 2
    return 1 if (leaks or misses) else 0


if __name__ == "__main__":
    raise SystemExit(main())
