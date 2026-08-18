"""Focused regression tests for exact-ref, judge, and replay remediation.

The July-7 batch replay tests (BatchRow/Conversation/OfficialRow/_run_hard)
lived here until the July-7 batch surface was archived to
``scratch/archive_july7_batch/`` (keep-local cleanup) — they now travel with
the archived modules as ``scratch/archive_july7_batch/test_eval_remediation_july7_replay.py``.
This file keeps the judge/grounding remediation tests, which are generic.
"""
from __future__ import annotations

from evals.harness.easyhard_ab import _score_row
from evals.judge import grounded, legal_v2


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


# ── R327.1 — the answer-correctness verdict rule must stay comparable ────────


def _ac_verdicts(monkeypatch, counts: dict) -> dict:
    """Drive grounded._judge_row's answer-correctness post-processing."""
    from evals.judge import grounded

    row = {
        "id": "x",
        "category": None,
        "question": "q",
        "answer": "a",
        "pred_refs": ["Article 5"],
        "gold_refs": [],
        "gold_answer": "",
        "independent_gold_context": "",
    }

    def fake_caller(_prompt, **_kw):
        return dict(counts)

    monkeypatch.setattr(
        grounded, "_call_judge_with_retry",
        lambda caller, prompt: (dict(counts), 1, False),
    )
    monkeypatch.setattr(grounded, "_provision_block", lambda *a, **k: "text")
    out = grounded._judge_row(row, fake_caller)
    return out["verdicts"]["answer_correctness"]


def test_unsupported_claim_does_not_fail_the_row_by_default(monkeypatch) -> None:
    """R327.1 — an uncommitted pass force-failed on `unsupported`, IN PLACE.

    Measured: the rule alone moves the answer-correctness pass rate from 0.880 to
    0.620 on the R327 rows, and the R318 sidecar that produced the documented
    "0.500 -> 0.780" never applied it. Redefining an axis under its own name is
    the instrument trap, so `verdict` keeps the historical meaning.
    """
    v = _ac_verdicts(
        monkeypatch,
        {"correct": 3, "incorrect": 0, "unsupported": 2, "missing": 0},
    )
    assert v["verdict"] == "pass"
    assert v["verdict_hard_only"] == "pass"
    assert v["verdict_unsupported_strict"] == "fail"
    assert v["unsupported_enforced"] is False


def test_incorrect_claim_still_fails_the_row(monkeypatch) -> None:
    v = _ac_verdicts(
        monkeypatch,
        {"correct": 1, "incorrect": 1, "unsupported": 0, "missing": 0},
    )
    assert v["verdict"] == "fail"
    assert v["verdict_hard_only"] == "fail"


def test_strict_rule_is_opt_in(monkeypatch) -> None:
    monkeypatch.setenv("GROUNDED_JUDGE_UNSUPPORTED_FAILS", "1")
    v = _ac_verdicts(
        monkeypatch,
        {"correct": 3, "incorrect": 0, "unsupported": 2, "missing": 0},
    )
    assert v["verdict"] == "fail"
    assert v["unsupported_enforced"] is True
