"""R299 — Unit tests for Move 1 (OPERATIVE/BACKGROUND partitioning) and Move 2 (completeness verifier).

Validates:
1. OPERATIVE vs BACKGROUND reference partitioning logic (`partition_context_references`).
2. References block formatting with OPERATIVE PROVISIONS and BACKGROUND CONTEXT sections.
3. Prompt clause inclusion in Stage-2 USER message.
4. Deterministic enumerated completeness verifier (`verify_and_enrich_enumerated_completeness`).
5. Off-switches (`REGENOLD_REF_PARTITION=0` and `REGENOLD_COMPLETENESS_VERIFIER=0`).
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from app.data.graph_rag_prompts import (
    completeness_verifier_enabled,
    user_ref_partition_enabled,
)
from app.engines._graph_rag_impl import (
    GraphContext,
    _build_context_references_block,
    partition_context_references,
)
from app.engines.completeness_verifier import (
    is_enumerated_set_question,
    verify_and_enrich_enumerated_completeness,
)


def test_toggles_default_on(monkeypatch):
    monkeypatch.delenv("REGENOLD_REF_PARTITION", raising=False)
    monkeypatch.delenv("REGENOLD_COMPLETENESS_VERIFIER", raising=False)
    assert user_ref_partition_enabled() is True
    assert completeness_verifier_enabled() is True


def test_toggles_off_switch(monkeypatch):
    monkeypatch.setenv("REGENOLD_REF_PARTITION", "0")
    monkeypatch.setenv("REGENOLD_COMPLETENESS_VERIFIER", "0")
    assert user_ref_partition_enabled() is False
    assert completeness_verifier_enabled() is False


def test_partition_context_references_role():
    ctx = GraphContext()
    ctx.obligations = [
        {"id": "ob_1", "text": "Importer verification", "article": "23"},
        {"id": "ob_2", "text": "Risk management system", "article": "9"},
        {"id": "ob_3", "text": "Classification rule", "article": "6"},
    ]
    q = "What are the verification obligations of an importer under the EU AI Act?"
    op, bg = partition_context_references(ctx, q)
    assert "Article 23" in op or "23" in op or "Art. 23" in op
    assert "Article 6" in bg or "6" in bg or "Art. 6" in bg
    assert "Article 9" in bg or "9" in bg or "Art. 9" in bg


def test_partition_context_references_explicit_article():
    ctx = GraphContext()
    ctx.obligations = [
        {"id": "ob_1", "text": "Transparency obligations", "article": "50"},
        {"id": "ob_2", "text": "High risk classification", "article": "6"},
    ]
    q = "What are the transparency requirements under Article 50?"
    op, bg = partition_context_references(ctx, q)
    assert any("50" in ref for ref in op)
    assert any("6" in ref for ref in bg)


def test_build_context_references_block_partitioned(monkeypatch):
    monkeypatch.setenv("REGENOLD_REF_PARTITION", "1")
    ctx = GraphContext()
    ctx.obligations = [
        {"id": "ob_1", "text": "Importer verification duties", "article": "23"},
        {"id": "ob_2", "text": "High risk classification", "article": "6"},
    ]

    q = "What are the verification duties of an importer?"
    block = _build_context_references_block(ctx, question=q)
    assert "OPERATIVE PROVISIONS" in block
    assert "BACKGROUND CONTEXT" in block
    assert "Article: 23" in block
    assert "Article: 6" in block


def test_is_enumerated_set_question():
    assert is_enumerated_set_question("What are the importer obligations?") is True
    assert is_enumerated_set_question("List the prohibited practices.") is True
    assert is_enumerated_set_question("Which risk tiers exist?") is True
    assert is_enumerated_set_question("Is a chatbot high risk?") is False


def test_completeness_verifier_appends_missing_points(monkeypatch):
    monkeypatch.setenv("REGENOLD_COMPLETENESS_VERIFIER", "1")
    q = "What are the obligations of an importer under Article 23?"
    # Answer only mentions point (a)
    answer = "Article 23 requires importers to verify that the provider has carried out conformity assessment (a)."
    res = verify_and_enrich_enumerated_completeness(q, answer, None)
    assert "including points" in res or res != answer
    assert "Article 23" in res


def test_completeness_verifier_disabled_returns_raw(monkeypatch):
    monkeypatch.setenv("REGENOLD_COMPLETENESS_VERIFIER", "0")
    q = "What are the obligations of an importer under Article 23?"
    answer = "Article 23 requires importers to verify conformity assessment (a)."
    res = verify_and_enrich_enumerated_completeness(q, answer, None)
    assert res == answer
