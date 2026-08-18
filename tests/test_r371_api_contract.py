"""R371 — the competition wire contract must be untouched by the new lever.

The lever renders NON-CITABLE Stage-2 context (hard rule #10). The decisive
property is therefore not "does the block appear" (proved in
``test_role_obligation_context.py``) but **"does the wire stay identical"**.

If turning it on changed ``references``, the graph would have become a citation
source — the exact defect R350/R351 spent two rounds fixing, and the one that
tripped the hard rule #8 gold veto twice.

These run on the deterministic path (``P2P_GRAPH_RAG_PROVIDER=cli``), so they
assert the contract without a live LLM.
"""

from __future__ import annotations

import os
import re

import pytest
from fastapi.testclient import TestClient

from app.integrations.regenold.models import (
    _ANNEX_OUTPUT_RE,
    _ARTICLE_OUTPUT_RE,
)

ENDPOINT = "/api/v1/regenold/eu-ai-act/ask"

QUESTIONS = [
    "Who must carry out the conformity assessment for a high-risk AI system?",
    "What are the obligations of a deployer of a high-risk AI system?",
    "Is an AI system used for CV screening high-risk?",
    "What transparency obligations apply to a customer-service chatbot?",
]


@pytest.fixture(scope="module")
def client() -> TestClient:
    os.environ.setdefault("P2P_GRAPH_RAG_PROVIDER", "cli")
    os.environ.setdefault("OPENAI_API_BASE", "http://127.0.0.1:1/v1")
    from app.main import app

    return TestClient(app)


def _ask(client: TestClient, question: str) -> dict:
    resp = client.post(
        ENDPOINT,
        json={"messages": [{"role": "user", "content": question}]},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── The competition contract ──────────────────────────────────────────────


@pytest.mark.parametrize("question", QUESTIONS)
def test_response_has_exactly_the_three_spec_fields(
    client: TestClient, question: str
) -> None:
    body = _ask(client, question)
    assert set(body) >= {"answer", "references", "reasoning"}
    assert isinstance(body["answer"], str)
    assert isinstance(body["references"], list)
    assert isinstance(body["reasoning"], str)


@pytest.mark.parametrize("question", QUESTIONS)
def test_every_reference_matches_the_strict_spec_shape(
    client: TestClient, question: str
) -> None:
    """Hard rule #1 — only ``Article N`` (Arabic) / ``Annex X`` (Roman)."""
    for ref in _ask(client, question)["references"]:
        assert isinstance(ref, str)
        assert _ARTICLE_OUTPUT_RE.match(ref) or _ANNEX_OUTPUT_RE.match(ref), (
            f"{ref!r} is not a spec-shaped citation"
        )
        assert not re.match(r"^Art\.", ref), f"{ref!r} leaked internal form"
        assert not re.match(r"^Annex \d", ref), f"{ref!r} used an Arabic annex"


@pytest.mark.parametrize("question", QUESTIONS)
def test_answer_is_non_empty(client: TestClient, question: str) -> None:
    assert _ask(client, question)["answer"].strip()


# ── The load-bearing property ─────────────────────────────────────────────


@pytest.mark.parametrize("question", QUESTIONS)
def test_lever_does_not_change_the_wire(
    client: TestClient, question: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Flipping REGENOLD_ROLE_OBLIGATION_CONTEXT must leave ``references``
    byte-identical. It is Stage-2 CONTEXT, never a citation source."""
    monkeypatch.setenv("REGENOLD_ROLE_OBLIGATION_CONTEXT", "0")
    off = _ask(client, question)

    monkeypatch.setenv("REGENOLD_ROLE_OBLIGATION_CONTEXT", "1")
    on = _ask(client, question)

    assert on["references"] == off["references"], (
        "the role x risk-class block changed the WIRE — it must be non-citable "
        f"(hard rule #10). off={off['references']} on={on['references']}"
    )


def test_multi_turn_still_works(client: TestClient) -> None:
    resp = client.post(
        ENDPOINT,
        json={
            "messages": [
                {"role": "user", "content": "Is a CV screening tool high-risk?"},
                {"role": "assistant", "content": "Yes, under Annex III."},
                {"role": "user", "content": "What must the provider do then?"},
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["answer"].strip()
    for ref in body["references"]:
        assert _ARTICLE_OUTPUT_RE.match(ref) or _ANNEX_OUTPUT_RE.match(ref)
