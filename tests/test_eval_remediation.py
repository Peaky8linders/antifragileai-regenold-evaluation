"""Focused regression tests for exact-ref, judge, and replay remediation."""
from __future__ import annotations

import io

from evals.harness.easyhard_ab import _score_row
from evals.judge import grounded, legal_v2
from evals.regenold.evaluator_batch_july7 import BatchRow, Conversation
from evals.regenold.official_batch import OfficialRow
from evals.regenold.run_official_batch import _run_hard as run_official_hard


def _batch_row(seq: int, question: str) -> BatchRow:
    return BatchRow(
        seq=seq,
        request_id=f"req-{seq}",
        question=question,
        difficulty="HARD",
        category="Multi-Turn Context & Coreference",
        history_turns=18 if seq == 1 else 20,
        question_hash=f"hash-{seq}",
        timestamp="2026-07-07T00:00:00Z",
        july7_answer="old",
        july7_refs=("Article 9",),
        july7_confidence=1.0,
        july7_retrieval_path="kb",
        july7_scope_reason="in_scope",
    )


def test_ordinary_followup_replays_actual_second_user_turn() -> None:
    convo = Conversation(
        turn1=_batch_row(1, "What risk tier applies?"),
        turn2=_batch_row(2, "Which records must the deployer keep?"),
        pairing_method="positional",
        has_pushback_marker=False,
    )
    messages = convo.turn2_messages("It is high-risk.")
    assert convo.turn2_kind == "ordinary_followup"
    assert convo.graded_question_text == "Which records must the deployer keep?"
    assert messages[-1] == {
        "role": "user", "content": "Which records must the deployer keep?"
    }
    assert "I don't think this is correct" not in messages[-1]["content"]


def test_grounded_answer_prompt_uses_gold_not_prediction_selected_refs() -> None:
    row = grounded._norm(
        {
            "question": "What risk-management system is required?",
            "pred_answer": "x" * 1800 + "END_MARKER",
            "pred_refs": ["Article 99"],
            "gold_refs": ["Article 9"],
        }
    )
    prompt = grounded.render_answer_correctness(row)
    assert "[Article 9]" in prompt
    assert "[Article 99]" not in prompt
    assert "END_MARKER" in prompt


def test_exact_leaf_does_not_fall_back_to_parent_text() -> None:
    block = grounded._provision_block(["Article 3.999"], 2000, 2)
    assert "no verbatim text resolved" in block
    assert "provider" not in block.lower()


def test_empty_answer_is_kept_as_deterministic_failure() -> None:
    row = grounded._norm({"id": "empty", "pred_answer": ""})

    def should_not_call(_: str):  # pragma: no cover - failure explains itself
        raise AssertionError("judge must not be called for an empty answer")

    judged = grounded._judge_row(row, should_not_call)
    assert all(v["verdict"] == "fail" for v in judged["verdicts"].values())
    assert grounded._aggregate([judged])["answer_correctness"]["n"] == 1


def test_legal_v2_unsupported_proposition_fails_correctness() -> None:
    out = legal_v2._postprocess_answer_correctness(
        {
            "propositions": [
                {"text": "An unsupported claim", "status": "NOT-ADDRESSED", "quote": ""}
            ],
            "omission_present": False,
        },
        {"gold": "independent context"},
    )
    assert out["unsupported_present"] is True
    assert out["verdict"] == "fail"
    assert out["factual_score"] == 0.0


def test_easyhard_strict_axis_observes_subpoint_mismatch() -> None:
    class Probe:
        expected_refs = ["Article 3.1"]
        expected_keywords: list[str] = []

    scores = _score_row(Probe(), "Answer.", ["Article 3.999"])
    assert scores["ref_strict"] == 0.0
    assert scores["ref_strict_head_f1_proxy"] == 1.0
    assert scores["invalid_ref_count"] == 1.0


def test_official_replay_selects_turn2_answer_and_empty_refs_atomically() -> None:
    row = OfficialRow(
        id="official-1",
        question="What applies?",
        question_hash="h",
        jul07_answer="old",
        jul07_refs=("Article 9",),
        jul07_confidence=1.0,
        jul07_retrieval_path="kb",
        jul07_scope_reason="in_scope",
    )
    calls = 0

    def poster(url, api_key, messages, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            body = {"answer": "turn one", "references": ["Article 9"]}
        else:
            body = {"answer": "turn two", "references": []}
        return body, 1.0, 200, None, 1, False

    rec = run_official_hard(
        [row], poster, "local", None, 1.0, io.StringIO()
    )[0]
    assert rec["selected_turn"] == "pushback"
    assert rec["pred_answer"] == "turn two"
    assert rec["pred_refs"] == []
