#!/usr/bin/env python3
"""Validate the per-stratum item files and merge them into the easy/hard
benchmark datasets for the EU AI Act GraphRAG evaluation harness.

Run:  python3 build_dataset.py
Reads _strata/*.json, validates each item against the schema, then writes
eu_ai_act_bench_easy.json and eu_ai_act_bench_hard.json in this directory.
Exits non-zero and prints a report if any item violates the schema.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
STRATA_DIR = HERE / "_strata"

TASK_TYPES = {"risk_classification", "article_retrieval", "obligation_generation", "qa"}
RISK_LEVELS = {"prohibited", "high", "limited", "minimal", "not_applicable"}
CITATION_ROLES = {"primary", "supporting", "definition", "interpretive"}
CONFIDENCE = {"high", "medium"}
REQUIRED_KEYS = {
    "id", "difficulty", "task_type", "stratum", "question", "scenario",
    "gold_answer", "risk_level", "gold_citations", "reasoning_hops",
    "multi_hop", "negative_control", "hallucination_trap", "trap_note",
    "confidence", "annotator_notes",
}

PROVISION_RE = re.compile(
    r"^("
    r"art_\d+(__para_\d+(__point_[a-z]+(__sub_[ivxlcdm]+)?)?)?"
    r"|annex_[IVXLCDM]+(__point_\d+(__point_[a-z]+)?)?"
    r"|recital_\d+"
    r")$"
)


def validate_item(item, errors):
    iid = item.get("id", "<no-id>")

    missing = REQUIRED_KEYS - set(item)
    if missing:
        errors.append(f"{iid}: missing keys {sorted(missing)}")
        return

    if item["difficulty"] not in {"easy", "hard"}:
        errors.append(f"{iid}: bad difficulty {item['difficulty']!r}")
    if item["task_type"] not in TASK_TYPES:
        errors.append(f"{iid}: bad task_type {item['task_type']!r}")
    if item["risk_level"] not in RISK_LEVELS:
        errors.append(f"{iid}: bad risk_level {item['risk_level']!r}")
    if item["confidence"] not in CONFIDENCE:
        errors.append(f"{iid}: bad confidence {item['confidence']!r}")

    if not isinstance(item["reasoning_hops"], int) or item["reasoning_hops"] < 1:
        errors.append(f"{iid}: reasoning_hops must be int >= 1")
    for b in ("multi_hop", "negative_control", "hallucination_trap"):
        if not isinstance(item[b], bool):
            errors.append(f"{iid}: {b} must be bool")

    if not item["id"].startswith(item["difficulty"] + "_"):
        errors.append(f"{iid}: id prefix does not match difficulty")

    cites = item["gold_citations"]
    if not isinstance(cites, list):
        errors.append(f"{iid}: gold_citations must be a list")
        cites = []
    for c in cites:
        if not {"citation", "provision_id", "role"} <= set(c):
            errors.append(f"{iid}: citation missing keys -> {c}")
            continue
        if not PROVISION_RE.match(c["provision_id"]):
            errors.append(f"{iid}: bad provision_id {c['provision_id']!r}")
        if c["role"] not in CITATION_ROLES:
            errors.append(f"{iid}: bad citation role {c['role']!r}")

    # semantic invariants
    if item["negative_control"] and cites:
        errors.append(f"{iid}: negative_control=True but gold_citations not empty")
    if item["hallucination_trap"] and not str(item["trap_note"]).strip():
        errors.append(f"{iid}: hallucination_trap=True but trap_note empty")
    if item["difficulty"] == "easy":
        if item["multi_hop"] or item["negative_control"] or item["hallucination_trap"]:
            errors.append(f"{iid}: easy item must not be multi_hop/negative_control/trap")
        if item["reasoning_hops"] != 1:
            errors.append(f"{iid}: easy item must have reasoning_hops == 1")


def main():
    files = sorted(STRATA_DIR.glob("*.json"))
    if not files:
        sys.exit(f"no strata files in {STRATA_DIR}")

    all_items = []
    errors = []
    seen_ids = {}
    for f in files:
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"{f.name}: invalid JSON - {e}")
            continue
        for item in data.get("items", []):
            validate_item(item, errors)
            iid = item.get("id")
            if iid in seen_ids:
                errors.append(f"duplicate id {iid} ({f.name} and {seen_ids[iid]})")
            seen_ids[iid] = f.name
            all_items.append(item)

    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    easy = [i for i in all_items if i["difficulty"] == "easy"]
    hard = [i for i in all_items if i["difficulty"] == "hard"]

    def stats(items):
        provs = {c["provision_id"] for i in items for c in i["gold_citations"]}
        return {
            "count": len(items),
            "by_stratum": dict(Counter(i["stratum"] for i in items)),
            "by_task_type": dict(Counter(i["task_type"] for i in items)),
            "by_risk_level": dict(Counter(i["risk_level"] for i in items)),
            "negative_controls": sum(i["negative_control"] for i in items),
            "hallucination_traps": sum(i["hallucination_trap"] for i in items),
            "negative_control_and_trap": sum(i["negative_control"] and i["hallucination_trap"] for i in items),
            "multi_hop": sum(i["multi_hop"] for i in items),
            "medium_confidence": sum(i["confidence"] == "medium" for i in items),
            "distinct_provisions": len(provs),
        }

    common_meta = {
        "name": "EU AI Act GraphRAG Citation Benchmark",
        "regulation": "Regulation (EU) 2024/1689 (EU AI Act)",
        "celex": "32024R1689",
        "citation_granularity": "article / paragraph / point / sub-point + annex point + recital",
        "provision_id_scheme": "Akoma Ntoso eId style, e.g. art_6__para_2__point_a, annex_III__point_5, recital_27",
        "methodology": "arXiv:2603.09435 risk-tier + task-category construction, extended with subpoint citation sets, negative controls, and hallucination traps for the GraphRAG eval harness (see eu-ai-act-graphrag-plan.md, section 8).",
        "task_types": sorted(TASK_TYPES),
        "strata": ["prohibited", "high_risk_classification", "high_risk_requirements",
                   "transparency", "gpai", "governance"],
    }

    easy_out = {"metadata": {**common_meta, "split": "easy",
                             "difficulty_definition": "single-hop lookup/classification on clear-boundary provisions; 1-2 citation atoms; no negative controls or traps.",
                             "stats": stats(easy)},
                "items": sorted(easy, key=lambda i: i["id"])}
    hard_out = {"metadata": {**common_meta, "split": "hard",
                             "difficulty_definition": "multi-hop cross-reference resolution and obligation aggregation, ambiguous-tier classification, negative controls (out-of-scope -> cite nothing), and hallucination traps; exhaustive necessary-and-sufficient citation sets.",
                             "stats": stats(hard)},
                "items": sorted(hard, key=lambda i: i["id"])}

    (HERE / "eu_ai_act_bench_easy.json").write_text(json.dumps(easy_out, indent=2, ensure_ascii=False) + "\n")
    (HERE / "eu_ai_act_bench_hard.json").write_text(json.dumps(hard_out, indent=2, ensure_ascii=False) + "\n")

    print("VALIDATION PASSED\n")
    print("EASY:", json.dumps(easy_out["metadata"]["stats"], indent=2))
    print("HARD:", json.dumps(hard_out["metadata"]["stats"], indent=2))


if __name__ == "__main__":
    main()
