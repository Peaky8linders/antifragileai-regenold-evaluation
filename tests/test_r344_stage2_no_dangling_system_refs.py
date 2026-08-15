"""R344 — the delivered Stage-2 user message must be self-contained.

The wrapper drops the Stage-2 SYSTEM slot on 100% of wrapper requests
(CLAUDE.md, measured with a French-instruction probe; root cause found and
fixed 2026-08-15 but the forward is default OFF, and R282 measured whole-
prompt forwarding as rubric-negative). So every rule that lands in the USER
message must be self-contained — a delivered clause that says "when rule
12b closed-set completeness requires…" or "the BLUF format from your
system prompt" points the model at rules it has never seen.

R344 made three delivered clauses self-contained:

1. the default-ON style/cohesion clause: "or when rule 12b closed-set
   completeness requires naming every member of a set" -> "...or when the
   question asks for an exhaustively enumerated statutory set (closed-set
   completeness), which requires naming every member of that set";
2. the classification branch: "the BOTTOM-LINE UP FRONT (BLUF)
   DIRECT-ANSWER-FIRST format from your system prompt" -> "...format
   defined here" (the format IS defined inline in the next sentences);
3. ``USER_SUBPARAGRAPH_ATTRIBUTION_CLAUSE``: "This never overrides the
   closed-set completeness rule above: …" -> "This never overrides
   closed-set completeness: …" (nothing is "above" in the delivered
   message).

These tests pin the invariant: the delivered user message never references
a system-rule by number or points at "the system prompt".
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.data.graph_rag_prompts import USER_SUBPARAGRAPH_ATTRIBUTION_CLAUSE
from app.engines import _graph_rag_impl as G

#: Phrases that only make sense if the model can see the (dead) system
#: prompt — any of them in the delivered USER message is a dangling pointer.
_DANGLING = (
    "rule 12b",
    "rules 12b",
    "rule 7",
    "from your system prompt",
    "closed-set completeness rule above",
    "system prompt",
)


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch):
    monkeypatch.setenv("REGENOLD_EMBEDDINGS_DIM", "8")
    monkeypatch.setenv("REGENOLD_SKIP_MODEL_LOAD", "1")
    monkeypatch.setenv("REGENOLD_EMBEDDINGS_HTTP_MODE", "1")
    monkeypatch.setenv("REGENOLD_EMBEDDINGS_INDEX", "0")


def _captured_user(question: str, *, is_classification: bool) -> str:
    captured: dict = {}

    def _fake_wrapper(system, user, max_tokens, temperature, **kwargs):
        captured["user"] = user
        return "A polished answer."

    with patch.object(G, "_openai_wrapper_complete_for_graph_rag", _fake_wrapper):
        out = G._claude_max_enhance_answer(
            question=question,
            kg_answer="The system is high-risk under Article 6.",
            is_general_classification=is_classification,
            force_provider="openai_wrapper",
        )
    assert out  # the polish path ran
    assert captured["user"]
    return captured["user"]


@pytest.mark.parametrize(
    ("question", "is_classification"),
    [
        # The classification branch carries the BLUF clause.
        ("Is a weight-tracking medtech system high-risk?", True),
        # The refine branch carries the style/cohesion clause.
        ("What are the risk categories in the AI Act?", False),
        # The sub-paragraph attribution clause is default ON everywhere.
        ("What does Article 5(1)(f) require?", False),
    ],
)
def test_delivered_user_message_has_no_dangling_system_refs(
    question: str, is_classification: bool
) -> None:
    user = _captured_user(question, is_classification=is_classification)
    for phrase in _DANGLING:
        assert phrase not in user, (
            f"delivered Stage-2 user message references a rule the wrapper "
            f"drops: {phrase!r} (in the answer for {question!r}). R344: make "
            f"the clause self-contained — the system slot reaches the model "
            f"on ZERO wrapper requests."
        )
    # The self-contained replacement wording is present on each branch:
    # the refine branch carries the closed-set sentence, the classification
    # branch carries the inline-defined BLUF format.
    if is_classification:
        assert "BLUF) DIRECT-ANSWER-FIRST format defined here" in user
    else:
        assert "exhaustively enumerated statutory set (closed-set completeness)" in user


def test_subparagraph_attribution_clause_is_self_contained() -> None:
    """BOTH prompt generations' default-ON clauses must not point at a 'rule
    above' that nothing in the delivered message defines.

    R345 extends the R344 invariant to the V2 prompt set (#24, live by
    default via ``REGENOLD_PROMPT_V2``): the V2 sub-paragraph clause carried
    the same dangling "closed-set completeness rule above" reference, which
    the R344 test (written pre-#24) only caught on the V1 constant.
    """
    from app.data.graph_rag_prompts import (  # noqa: PLC0415
        USER_SUBPARAGRAPH_ATTRIBUTION_CLAUSE_V2,
    )

    for clause in (USER_SUBPARAGRAPH_ATTRIBUTION_CLAUSE, USER_SUBPARAGRAPH_ATTRIBUTION_CLAUSE_V2):
        assert "rule above" not in clause
        assert "closed-set completeness rule above" not in clause
        assert "system prompt" not in clause
        # It carries its own self-contained definition of the carve-out.
        assert "enumerated statutory set, name every member of it" in clause
