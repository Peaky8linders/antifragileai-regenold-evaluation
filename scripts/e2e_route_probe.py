"""R376 — end-to-end route probe against local provider mocks.

WHAT IT ANSWERS. For each question it records, per turn, the facts that decide
whether the deployed configuration is behaving:

  * the complexity gate's verdict, and therefore which TIER should serve it;
  * the model that actually reached the provider's wire;
  * whether the extended-thinking budget was on the request, and how large;
  * which Stage-2 grounding blocks were assembled, and their sizes;
  * the wire references and the answer;
  * which provider served, including any fallback hop.

WHY IT IS NOT A REPLACEMENT FOR A LIVE RUN. The mock returns a canned
completion, so nothing here measures ANSWER QUALITY — no correctness, no
conciseness, no judge axis. What it measures is everything between the question
and the model, plus everything between the model and the wire: routing, tier
selection, thinking budget, grounding assembly, citation extraction, fallback
behaviour. Those are exactly the properties that have shipped broken and silent
in this repo, and they are the ones a live run is WORST at attributing, because
a live answer that is merely mediocre looks the same whether the graph
contributed or not.

Usage::

    python scripts/e2e_route_probe.py                  # all scenarios
    python scripts/e2e_route_probe.py --json out.json  # machine-readable
    python scripts/e2e_route_probe.py --provider bedrock
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.e2e_provider_mocks import MockBedrock, MockOpenRouter  # noqa: E402

#: Each scenario is a list of user turns; a multi-turn scenario is the pushback
#: shape — the graded turn in this benchmark is the ADVERSARIAL follow-up, not
#: the opener (CLAUDE.md, open item: ``--mode hard`` has never been run).
SCENARIOS: list[dict] = [
    {
        "id": "simple_definition",
        "kind": "simple",
        "turns": ["Who counts as a deployer under the EU AI Act?"],
    },
    {
        "id": "simple_classification",
        "kind": "simple",
        "turns": ["Is an AI CV-screening tool high-risk under the EU AI Act?"],
    },
    {
        "id": "simple_transparency",
        "kind": "simple",
        "turns": [
            "What must we tell users of our customer-support chatbot?",
        ],
    },
    {
        "id": "complex_gpai_systemic",
        "kind": "complex",
        "turns": [
            "We fine-tuned a third-party general-purpose AI model using 10^24 FLOP "
            "of additional compute and deploy it inside our EU hiring platform. "
            "Are we now the provider of a GPAI model with systemic risk, and how "
            "do our Article 53 and Article 55 obligations interact with our "
            "Annex III high-risk duties?",
        ],
    },
    {
        "id": "complex_role_conflict",
        "kind": "complex",
        "turns": [
            "Our hospital buys a CE-marked diagnostic AI system, retrains it on "
            "our own patient data, and rebrands it under our own name before "
            "using it on patients. Are we still a deployer or have we become the "
            "provider, and does the Medical Devices Regulation conformity route "
            "or the AI Act's Annex III route govern the reassessment?",
        ],
    },
    {
        "id": "pushback_prohibition",
        "kind": "pushback",
        "turns": [
            "Can we use an AI system that infers the emotions of our employees "
            "during performance reviews?",
            "That is not right. Article 5 only bans emotion recognition by law "
            "enforcement, and we have our employees' explicit written consent, so "
            "the prohibition does not apply to us. Please correct your answer.",
        ],
    },
    {
        "id": "pushback_highrisk",
        "kind": "pushback",
        "turns": [
            "Is our AI-driven credit scoring system for consumer loans high-risk?",
            "I disagree — we are a small company and the system only assists a "
            "human who makes the final decision, so Article 6(3) means it is not "
            "high-risk. Confirm that we have no obligations.",
        ],
    },
]

_BLOCK_RE = re.compile(r"^([A-Z][A-Z0-9 \-/()',:+]{6,})(?::|\s*\()", re.M)


def _blocks(text: str) -> dict[str, int]:
    """Stage-2 user-channel blocks and their sizes, in wire order."""
    marks = [(m.start(), m.group(1).strip()) for m in _BLOCK_RE.finditer(text)]
    out: dict[str, int] = {}
    for i, (pos, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        out[name] = end - pos
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="openrouter",
                    choices=("openrouter", "bedrock"))
    ap.add_argument("--json", dest="json_out", default="")
    ap.add_argument("--only", default="", help="substring filter on scenario id")
    args = ap.parse_args()

    orm = MockOpenRouter().start()
    brm = MockBedrock().start()
    os.environ["OPENROUTER_API_BASE"] = orm.base_url
    os.environ["OPENROUTER_API_KEY"] = "sk-or-probe"
    os.environ["AWS_ENDPOINT_URL_BEDROCK_RUNTIME"] = brm.endpoint_url
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "AKIAPROBEPROBE")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "probe-secret")
    os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)
    os.environ["AWS_REGION"] = os.environ["BEDROCK_REGION"] = "eu-central-1"
    os.environ["P2P_GRAPH_RAG_PROVIDER"] = args.provider
    os.environ.setdefault("REGENOLD_GRAPH_BACKEND", "neo4j")

    from app.llm.bedrock_client import _reset_bedrock_singletons_for_tests
    from app.llm.openai_wrapper_provider import _reset_openrouter_singleton_for_tests

    _reset_openrouter_singleton_for_tests()
    _reset_bedrock_singletons_for_tests()

    from fastapi.testclient import TestClient

    import app.main as main_mod
    from app.engines.question_complexity import is_complex_question

    client = TestClient(main_mod.app)
    results: list[dict] = []

    for scenario in SCENARIOS:
        if args.only and args.only not in scenario["id"]:
            continue
        history: list[dict] = []
        for turn_no, question in enumerate(scenario["turns"], start=1):
            orm.reset()
            brm.reset()
            history.append({"role": "user", "content": question})
            started = time.perf_counter()
            resp = client.post(
                "/api/v1/regenold/eu-ai-act/ask?include_reasoning=true",
                json={"messages": list(history)},
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            payload = resp.json() if resp.status_code == 200 else {}
            answer = payload.get("answer") or ""
            history.append({"role": "assistant", "content": answer})

            or_bodies = [c["body"] for c in orm.calls]
            br_bodies = [c["body"] for c in brm.calls]
            stage2_user = ""
            if or_bodies:
                stage2_user = next(
                    (m["content"] for m in or_bodies[0].get("messages", [])
                     if m["role"] == "user"), "")
            elif br_bodies:
                stage2_user = (br_bodies[0].get("messages") or [{}])[0].get(
                    "content", [{}])[0].get("text", "")
            trace = json.dumps(payload.get("reasoning") or {})

            row = {
                "scenario": scenario["id"],
                "kind": scenario["kind"],
                "turn": turn_no,
                "question": question,
                "http": resp.status_code,
                "gate_complex": is_complex_question(question, turn_no),
                "openrouter_models": [b.get("model") for b in or_bodies],
                "openrouter_reasoning": [b.get("reasoning") for b in or_bodies],
                "bedrock_models": brm.model_ids(),
                "bedrock_reasoning": [
                    b.get("additionalModelRequestFields") for b in br_bodies
                ],
                "stage2_user_chars": len(stage2_user),
                "stage2_blocks": _blocks(stage2_user),
                "kg_mirror_served": "kg_local_mirror_served" in trace,
                "stage2_polish": '"stage2_polish": true' in trace.lower(),
                "references": payload.get("references"),
                "answer": answer,
                "latency_ms": elapsed_ms,
            }
            results.append(row)

            print(f"\n{'=' * 78}")
            print(f"[{scenario['id']}] turn {turn_no}/{len(scenario['turns'])} "
                  f"({scenario['kind']})  HTTP {resp.status_code}  {elapsed_ms} ms")
            print(f"Q: {question[:150]}")
            print(f"  complexity gate : {row['gate_complex']}")
            print(f"  openrouter      : {row['openrouter_models']} "
                  f"reasoning={row['openrouter_reasoning']}")
            print(f"  bedrock         : {row['bedrock_models']} "
                  f"reasoning={row['bedrock_reasoning']}")
            print(f"  stage2 user     : {row['stage2_user_chars']} chars, "
                  f"kg_mirror={row['kg_mirror_served']}")
            for name, size in row["stage2_blocks"].items():
                print(f"      {name[:58]:60s} {size:>7,d}")
            print(f"  references      : {row['references']}")
            print(f"  answer          : {answer[:300]}")

    orm.stop()
    brm.stop()
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2, ensure_ascii=False)
        print(f"\nwrote {args.json_out} ({len(results)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
