"""Runner for the public GraphRAG-Bench medical Q&A set.

Loads the `medical` configuration from HF `GraphRAG-Bench/GraphRAG-Bench`
and runs a subset of questions against the compliance ask endpoint.
Surfaces the keyword recall (against target answer keywords), refusal rate, and latency.

Usage
-----
    # Local deterministic / LogicRAG:
    .venv\\Scripts\\python.exe -m evals.regenold.run_public_graphrag_bench \\
        --local --label public-graphrag-bench-logicrag --limit 20
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from evals.bench import metrics as bench_metrics
from evals.regenold.runner_v2 import (
    _ensure_local_auth,
    _keyword_recall,
    _local_endpoint_url,
    _post,
    _post_local,
    _REFUSAL_MARKERS,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _pct(values: list[float]) -> dict[str, float]:
    if not values:
        return {"p50": 0.0, "p95": 0.0}
    s = sorted(values)
    p50 = median(s)
    p95 = s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))]
    return {"p50": round(p50, 1), "p95": round(p95, 1)}


def _extract_keywords(text: str) -> list[str]:
    """Helper to extract keywords from expected answers."""
    stop_words = {
        "the", "a", "an", "and", "or", "but", "if", "then", "else", "when", "at", "by", "for", "with",
        "about", "against", "between", "into", "through", "during", "before", "after", "above", "below",
        "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then",
        "once", "here", "there", "all", "any", "both", "each", "few", "more", "most", "other", "some",
        "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "can",
        "will", "just", "should", "now", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "having", "do", "does", "did", "doing", "of", "what"
    }
    words = re.findall(r'[a-zA-Z0-9]+', text.lower())
    keywords = sorted(list(set([w for w in words if w not in stop_words and len(w) > 2])))
    return keywords


def run(
    *,
    endpoint: str,
    api_key: str | None,
    label: str,
    timeout: float,
    use_local: bool,
    limit: int = 20,
) -> dict[str, Any]:
    import datasets

    print(f"Loading GraphRAG-Bench 'medical' config (limit={limit})...")
    ds = datasets.load_dataset("GraphRAG-Bench/GraphRAG-Bench", "medical")
    train_split = ds["train"]
    
    # We sample a deterministic set (the first 'limit' rows)
    scenarios = train_split.select(range(min(limit, len(train_split))))

    transport = _post_local if use_local else _post
    if use_local:
        _ensure_local_auth(api_key)

    rows: list[dict[str, Any]] = []
    for idx, scn in enumerate(scenarios):
        question = scn["question"]
        expected_answer = scn["answer"]
        expected_keywords = _extract_keywords(expected_answer)

        history = [{"role": "user", "content": question}]
        body, lat, status, err, _attempts, _retried = transport(
            endpoint, api_key, history, timeout
        )
        if err is None and not (200 <= status < 300):
            err = f"http_{status}"
        
        answer = body.get("answer") or ""
        refs = body.get("references") or []
        kw = _keyword_recall(answer, expected_keywords)
        tone = bench_metrics.regulatory_tone(answer)
        is_refusal = any(m in answer.lower() for m in _REFUSAL_MARKERS)
        
        row = {
            "id": scn["id"],
            "question": question,
            "expected_answer": expected_answer,
            "expected_keywords": expected_keywords,
            "pred_refs": refs,
            "predicted_answer": answer,
            "answer_preview": answer[:400],
            "reasoning": body.get("reasoning"),
            "keyword_recall": kw,
            "regulatory_tone": tone,
            "is_refusal": is_refusal,
            "latency_ms": lat,
            "error": err,
        }
        rows.append(row)
        print(
            f"[Public GraphRAG-Bench Medical] {scn['id']} "
            f"kw={kw:.2f} tone={tone:.2f} refusal={is_refusal} lat={lat:.0f}ms"
            f"{' ERR=' + err if err else ''}"
        )

    scored = [r for r in rows if r["error"] is None]

    def _avg(key: str) -> float | None:
        return round(mean([r[key] for r in scored]), 4) if scored else None

    overall = {
        "n": len(rows),
        "n_scored": len(scored),
        "http_failures": sum(1 for r in rows if r["error"]),
        "keyword_recall": _avg("keyword_recall"),
        "regulatory_tone": _avg("regulatory_tone"),
        "refusal_rate": round(mean([1.0 if r["is_refusal"] else 0.0 for r in scored]), 4) if scored else None,
        "latency": _pct([r["latency_ms"] for r in scored]),
    }

    payload = {
        "label": label,
        "mode": "public-graphrag-bench-local" if use_local else "public-graphrag-bench-live",
        "endpoint": endpoint,
        "started_at": _now_iso(),
        "overall": overall,
        "rows": rows,
    }

    out_dir = Path("evals/bench/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    sidecar = out_dir / f"public-graphrag-bench-{label}.json"
    sidecar.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    payload["sidecar_path"] = str(sidecar)
    return payload


def _format(payload: dict[str, Any]) -> str:
    o = payload["overall"]
    out = [
        "=" * 78,
        f"Public GraphRAG-Bench Medical — label={payload['label']!r}",
        f"endpoint: {payload['endpoint']}",
        f"mode: {payload['mode']}",
        "=" * 78,
        "",
        f"[OVERALL] n={o['n']} scored={o['n_scored']} http_failures={o['http_failures']}",
        f"    Keyword Recall  : {o['keyword_recall']}",
        f"    Regulatory Tone : {o['regulatory_tone']}",
        f"    Refusal Rate    : {o['refusal_rate']}",
        f"    Latency p50/p95 : {o['latency']['p50']}ms / {o['latency']['p95']}ms",
        "",
        f"sidecar: {payload.get('sidecar_path', '-')}",
    ]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                pass

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--label", required=True)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)

    if args.local:
        endpoint = _local_endpoint_url("include_reasoning=true")
    elif args.endpoint:
        endpoint = args.endpoint
    else:
        parser.error("--endpoint is required unless --local is set")
        return 2

    payload = run(
        endpoint=endpoint,
        api_key=args.api_key,
        label=args.label,
        timeout=args.timeout,
        use_local=args.local,
        limit=args.limit,
    )
    print(_format(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
