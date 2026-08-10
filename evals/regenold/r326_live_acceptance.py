"""Curated R321-R326 live acceptance probes for the Regenold competition.

This is intentionally small and evidence-heavy. It exercises the local code
under review while Stage 2 calls the existing Claude Max OpenAI-compatible
wrapper through Cloudflare Access and retrieval reads the configured Neo4j
Aura graph. Requests are strictly sequential.

The competition publishes its axes and wire contract, but not the numeric
scoring formulas. Scores emitted here are explicitly versioned local proxies;
the full prediction, official-text-derived gold, and diagnostics are retained
for an independent grounded-judge pass.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv


@dataclass(frozen=True)
class LiveCase:
    id: str
    history: tuple[dict[str, str], ...]
    gold_answer: str
    gold_refs: tuple[str, ...]
    criteria: tuple[tuple[str, ...], ...]


CASES: tuple[LiveCase, ...] = (
    LiveCase(
        id="competition_hardware_documentation",
        history=(
            {
                "role": "user",
                "content": (
                    "Does the technical documentation of a high-risk AI system "
                    "have to specify the hardware on which it is intended to run?"
                ),
            },
        ),
        gold_answer=(
            "Yes. The technical documentation must, as applicable, describe the "
            "hardware on which the high-risk AI system is intended to run and how "
            "it interacts with external hardware or software."
        ),
        gold_refs=("Annex IV.1.e",),
        criteria=(("yes", "must"), ("hardware",), ("technical documentation",)),
    ),
    LiveCase(
        id="competition_emotion_recognition_boundary",
        history=(
            {
                "role": "user",
                "content": (
                    "Are AI systems intended to infer emotions from biometric data "
                    "always prohibited under the EU AI Act?"
                ),
            },
        ),
        gold_answer=(
            "No. Emotion inference is prohibited in workplaces and education "
            "institutions, except for medical or safety reasons; permitted emotion-"
            "recognition uses are listed as high-risk in the biometrics category."
        ),
        gold_refs=("Article 5.1.f", "Annex III.1.c"),
        criteria=(
            ("no", "not always"),
            ("workplace",),
            ("education",),
            ("medical", "safety"),
        ),
    ),
    LiveCase(
        id="operator_role_internal_hr_dual_duties",
        history=(
            {
                "role": "user",
                "content": (
                    "We develop an Annex III CV-screening system solely for our own "
                    "HR team and never sell it. Are we only a deployer, or do both "
                    "provider and deployer duty sets apply?"
                ),
            },
        ),
        gold_answer=(
            "Both roles apply: the organisation is a provider because it develops "
            "and puts the system into service under its own authority, and a deployer "
            "because it uses the system. It must therefore satisfy the provider and "
            "deployer duty sets."
        ),
        gold_refs=("Article 3.3", "Article 3.4", "Article 16", "Article 26"),
        criteria=(("both",), ("provider",), ("deployer",)),
    ),
    LiveCase(
        id="multiturn_fria_dpia_non_substitution",
        history=(
            {
                "role": "user",
                "content": (
                    "We are a public body planning to deploy an Annex III high-risk "
                    "system for decisions affecting access to public benefits. What "
                    "assessment is required before first use?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "A fundamental-rights impact assessment is required before the "
                    "first use of that high-risk system."
                ),
            },
            {
                "role": "user",
                "content": (
                    "We already completed a GDPR data-protection impact assessment. "
                    "Does that replace the FRIA, or may one process cover both?"
                ),
            },
        ),
        gold_answer=(
            "The DPIA does not replace the fundamental-rights impact assessment. "
            "Where a DPIA is required, the FRIA complements it and may be conducted "
            "together with it before the high-risk system is first used."
        ),
        gold_refs=("Article 27.4",),
        criteria=(
            ("does not replace", "not replace", "separate", "in addition"),
            ("fundamental-rights impact assessment", "fria"),
            ("dpia", "data-protection impact assessment"),
        ),
    ),
)


def _safe_runtime_metadata() -> dict[str, Any]:
    base = os.getenv("OPENAI_API_BASE", "")
    return {
        "provider": os.getenv("P2P_GRAPH_RAG_PROVIDER", ""),
        "wrapper_host": urlparse(base).hostname or "",
        "neo4j_scheme": urlparse(os.getenv("NEO4J_URI", "")).scheme,
        "auto_seed": os.getenv("NEO4J_AUTO_SEED", ""),
        "feature_flags": {
            name: os.getenv(name, "")
            for name in (
                "REGENOLD_GRAPH_VECTOR_RECALL",
                "REGENOLD_KG_CONTEXT",
                "REGENOLD_PARENT_COLLAPSE",
                "REGENOLD_TURBOQUANT_DENSE",
                "REGENOLD_VECTOR_RERANK",
            )
        },
    }


def _audit_aura() -> dict[str, Any]:
    """Read-only proof of graph version, ontology shapes, and vector indexes."""
    from app.graph.client import get_graph_client

    client = get_graph_client()
    if not client.enabled:
        return {"status": "disabled"}
    try:
        metadata = client.execute_read_strict(
            "MATCH (m:KBMetadata) RETURN m.seed_version AS seed_version, "
            "m.kb_version AS kb_version LIMIT 1"
        )
        counts = client.execute_read_strict(
            "UNWIND $labels AS wanted "
            "OPTIONAL MATCH (n) WHERE wanted IN labels(n) "
            "RETURN wanted AS label, count(n) AS node_count ORDER BY wanted",
            {
                "labels": [
                    "Article",
                    "Annex",
                    "Practice",
                    "OperatorRole",
                    "AnnexIIICategory",
                    "LifecyclePhase",
                    "SubPoint",
                ]
            },
        )
        indexes = client.execute_read_strict(
            "SHOW INDEXES YIELD name, state, type, entityType, labelsOrTypes, "
            "properties WHERE name IN $names "
            "RETURN name, state, type, entityType, labelsOrTypes, properties "
            "ORDER BY name",
            {"names": ["v_article_embedding", "v_annex_embedding"]},
        )
        embeddings = client.execute_read_strict(
            "MATCH (a:Article) WITH count(a) AS articles, "
            "count(a.embedding) AS article_embeddings, "
            "max(size(a.embedding)) AS article_dimensions "
            "MATCH (x:Annex) RETURN articles, article_embeddings, "
            "article_dimensions, count(x) AS annexes, "
            "count(x.embedding) AS annex_embeddings, "
            "max(size(x.embedding)) AS annex_dimensions"
        )
        return {
            "status": "ok",
            "metadata": metadata,
            "ontology_counts": counts,
            "vector_indexes": indexes,
            "embedding_coverage": embeddings,
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error_type": type(exc).__name__}


def _trace_summary(reasoning: str) -> dict[str, Any]:
    try:
        trace = json.loads(reasoning)
    except (TypeError, ValueError):
        return {"parseable": False}
    if not isinstance(trace, dict):
        return {"parseable": False}
    out: dict[str, Any] = {"parseable": True}
    out.update(
        {
            key: trace.get(key)
            for key in (
            "schema_version",
            "scope",
            "references",
            "retrieval_path",
            "compound_roles",
            "guards_fired",
            "stage2_polish",
            "engine_confidence",
            "cache_hit",
            "notes",
        )
            if key in trace
        }
    )
    return out


def _semantic_criteria(answer: str, criteria: tuple[tuple[str, ...], ...]) -> dict:
    lowered = " ".join((answer or "").lower().split())
    groups = [
        {"alternatives": list(group), "matched": [term for term in group if term in lowered]}
        for group in criteria
    ]
    return {"passed": all(group["matched"] for group in groups), "groups": groups}


def _score_case(
    case: LiveCase,
    body: dict[str, Any],
    latency_ms: float,
    status: int,
    error: str | None,
) -> dict[str, Any]:
    from app.integrations.regenold.models import _split_sentences
    from evals.bench import metrics as metrics

    answer = body.get("answer", "")
    refs = body.get("references", [])
    reasoning = body.get("reasoning", "")
    schema = {
        "exact_fields": set(body) == {"reasoning", "answer", "references"},
        "reasoning_is_str": isinstance(reasoning, str),
        "answer_is_str": isinstance(answer, str),
        "references_is_list_str": isinstance(refs, list)
        and all(isinstance(ref, str) for ref in refs),
    }
    sentence_count = len(_split_sentences(answer)) if isinstance(answer, str) else 0
    ref_diag = metrics.canonical_reference_diagnostics(refs)
    semantic = _semantic_criteria(answer, case.criteria)
    return {
        "id": case.id,
        "question": case.history[-1]["content"],
        "history": list(case.history),
        "gold_answer": case.gold_answer,
        "gold_refs": list(case.gold_refs),
        "predicted_answer": answer,
        "pred_refs": refs,
        "http_status": status,
        "error": error,
        "latency_ms": round(latency_ms, 1),
        "wire_schema": schema,
        "sentence_diagnostic": {
            "ordinary_sentence_count": sentence_count,
            "encouraged_1_to_4": 1 <= sentence_count <= 4,
            "is_correctness_gate": False,
        },
        "semantic_criteria": semantic,
        "answer_correctness_loose_proxy": metrics.answer_correctness_loose(
            answer, case.gold_answer
        ),
        "answer_correctness_strict_proxy": metrics.answer_correctness_strict(
            answer, case.gold_answer
        ),
        "answer_conciseness_proxy": metrics.answer_conciseness(
            answer, case.gold_answer
        ),
        "negation_diagnostics": metrics.negation_criterion_diagnostics(
            answer, case.gold_answer
        ),
        "reference_correctness_loose_head_recall_proxy": (
            metrics.reference_correctness_loose_head_recall_proxy(
                refs, list(case.gold_refs)
            )
        ),
        "reference_correctness_strict_full_coordinate_proxy": (
            metrics.reference_correctness_strict(refs, list(case.gold_refs))
        ),
        "reference_conciseness_proxy": metrics.reference_conciseness(
            refs, list(case.gold_refs)
        ),
        "reference_diagnostics": ref_diag,
        "trace": _trace_summary(reasoning),
        "contract_pass": (
            error is None
            and 200 <= status < 300
            and all(schema.values())
            and ref_diag["invalid_count"] == 0
            and ref_diag["duplicate_count"] == 0
            and ref_diag["parent_leaf_pair_count"] == 0
        ),
    }


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def mean(key: str) -> float:
        vals = [float(row[key]) for row in rows]
        return round(statistics.mean(vals), 4) if vals else 0.0

    latencies = sorted(float(row["latency_ms"]) for row in rows)
    return {
        "requests": len(rows),
        "errors": sum(bool(row["error"]) for row in rows),
        "contract_pass_rate": round(
            sum(bool(row["contract_pass"]) for row in rows) / len(rows), 4
        ),
        "semantic_criteria_pass_rate": round(
            sum(bool(row["semantic_criteria"]["passed"]) for row in rows)
            / len(rows),
            4,
        ),
        "answer_correctness_loose_proxy": mean("answer_correctness_loose_proxy"),
        "answer_correctness_strict_proxy": mean("answer_correctness_strict_proxy"),
        "reference_correctness_loose_head_recall_proxy": mean(
            "reference_correctness_loose_head_recall_proxy"
        ),
        "reference_correctness_strict_full_coordinate_proxy": mean(
            "reference_correctness_strict_full_coordinate_proxy"
        ),
        "reference_conciseness_proxy": mean("reference_conciseness_proxy"),
        "sentence_encouragement_rate": round(
            sum(row["sentence_diagnostic"]["encouraged_1_to_4"] for row in rows)
            / len(rows),
            4,
        ),
        "stage2_polish_count": sum(
            row["trace"].get("stage2_polish") is True for row in rows
        ),
        "kg_context_fire_count": sum(
            any(str(note).startswith("kg_context ") for note in row["trace"].get("notes", []))
            for row in rows
        ),
        "vector_recall_fire_count": sum(
            any(
                str(note).startswith("vector_recall ")
                for note in row["trace"].get("notes", [])
            )
            for row in rows
        ),
        "parent_collapse_fire_count": sum(
            any(
                str(note).startswith("parent_collapse ")
                for note in row["trace"].get("notes", [])
            )
            for row in rows
        ),
        "latency_p50_ms": latencies[len(latencies) // 2] if latencies else 0.0,
        "latency_max_ms": max(latencies, default=0.0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--label", default="r326-remediation")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--output-dir", default=".evalout/r326")
    args = parser.parse_args()

    if not load_dotenv(args.env_file, override=True):
        raise SystemExit(f"Could not load env file: {args.env_file}")

    # Hard safety boundary: the live acceptance process is graph read-only.
    os.environ["NEO4J_AUTO_SEED"] = "0"
    os.environ["REGENOLD_GRAPH_VECTOR_RECALL"] = "1"
    os.environ["REGENOLD_KG_CONTEXT"] = "1"
    os.environ["REGENOLD_PARENT_COLLAPSE"] = "1"

    from evals.bench.metrics import METRIC_PROVENANCE, METRICS_VERSION
    from evals.regenold.runner_v2 import _post_local

    endpoint = (
        "local://app.main:app/api/v1/regenold/eu-ai-act/ask?"
        "include_reasoning=true"
    )
    aura = _audit_aura()
    rows: list[dict[str, Any]] = []

    for case in CASES:
        body, latency, status, error, _attempts, _retried = _post_local(
            endpoint, None, list(case.history), args.timeout
        )
        row = _score_case(case, body, latency, status, error)
        rows.append(row)
        print(
            f"[{case.id}] status={status} latency_ms={latency:.1f} "
            f"contract={row['contract_pass']} semantic={row['semantic_criteria']['passed']} "
            f"ref_strict={row['reference_correctness_strict_full_coordinate_proxy']:.3f} "
            f"refs={row['pred_refs']}"
        )

        # A real repeat: append the system's actual answer, then challenge it.
        if case.id == "competition_hardware_documentation" and not error:
            repeat_history = list(case.history)
            repeat_history.append({"role": "assistant", "content": body["answer"]})
            repeat_history.append(
                {
                    "role": "user",
                    "content": (
                        "I do not think that is precise. Recheck the official Act "
                        "and return only the minimal relevant references."
                    ),
                }
            )
            repeat_case = LiveCase(
                id=f"{case.id}_actual_history_repeat",
                history=tuple(repeat_history),
                gold_answer=case.gold_answer,
                gold_refs=case.gold_refs,
                criteria=case.criteria,
            )
            body2, latency2, status2, error2, _attempts2, _retried2 = _post_local(
                endpoint, None, repeat_history, args.timeout
            )
            repeat_row = _score_case(
                repeat_case, body2, latency2, status2, error2
            )
            repeat_row["actual_history_repeat"] = True
            repeat_row["prior_prediction"] = body["answer"]
            rows.append(repeat_row)
            print(
                f"[{repeat_case.id}] status={status2} latency_ms={latency2:.1f} "
                f"contract={repeat_row['contract_pass']} "
                f"semantic={repeat_row['semantic_criteria']['passed']} "
                f"ref_strict={repeat_row['reference_correctness_strict_full_coordinate_proxy']:.3f} "
                f"refs={repeat_row['pred_refs']}"
            )

    payload = {
        "label": args.label,
        "created_at": datetime.now(UTC).isoformat(),
        "metric_provenance": METRIC_PROVENANCE,
        "metrics_version": METRICS_VERSION,
        "runtime": _safe_runtime_metadata(),
        "aura_audit": aura,
        "aggregate": _aggregate(rows),
        "rows": rows,
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"live-{args.label}.json"
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(payload["aggregate"], indent=2))
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
