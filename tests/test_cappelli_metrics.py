"""Unit tests for Cappelli et al. (2026) diagnostic evaluation metrics."""
from evals.bench.metrics import (
    answer_rouge_l,
    answer_semantic_similarity_proxy,
    threshold_precision_recall_curve,
    _token_sequence,
    _longest_common_subsequence_length,
)


def test_token_sequence_and_lcs():
    s1 = "High-risk AI systems shall establish a risk management system per Article 9."
    s2 = "A risk management system under Article 9 is required for high-risk AI."
    t1 = _token_sequence(s1)
    t2 = _token_sequence(s2)
    assert len(t1) > 0
    assert len(t2) > 0
    lcs_len = _longest_common_subsequence_length(t1, t2)
    assert lcs_len > 0


def test_answer_rouge_l_identical():
    text = "The AI Act requires technical documentation under Article 11 and Annex IV."
    score = answer_rouge_l(text, text)
    assert round(score, 4) == 1.0


def test_answer_rouge_l_partial():
    gold = "The system is classified as high-risk under Article 6 and Annex III point 4(b)."
    pred = "This AI tool qualifies as a high-risk system under Article 6 and Annex III."
    score = answer_rouge_l(pred, gold)
    assert 0.4 < score < 1.0


def test_answer_semantic_similarity_proxy():
    gold = "Mandatory technical documentation must include risk management files and data governance records."
    pred = "Required technical files include risk management protocols and dataset documentation."
    score = answer_semantic_similarity_proxy(pred, gold)
    assert 0.5 <= score <= 1.0


def test_threshold_precision_recall_curve():
    sim_scores = [0.85, 0.72, 0.45, 0.25, 0.12]
    gold_relevance = [True, True, True, False, False]
    curve = threshold_precision_recall_curve(sim_scores, gold_relevance, thresholds=[0.20, 0.40, 0.70])
    assert len(curve) == 3
    # At 0.20 threshold: 3 TPs (0.85, 0.72, 0.45), 1 FP (0.25) -> Precision = 3/4 = 0.75, Recall = 3/3 = 1.0
    assert curve[0]["threshold"] == 0.20
    assert curve[0]["recall"] == 1.0
    assert curve[0]["precision"] == 0.75
