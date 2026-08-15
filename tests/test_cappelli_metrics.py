"""Unit tests for Cappelli et al. (2026) diagnostic evaluation metrics."""
import pytest

from evals.bench.metrics import (
    METRIC_PROVENANCE,
    answer_rouge_l,
    answer_trigram_jaccard,
    score_threshold_retention_curve,
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


def test_answer_trigram_jaccard():
    gold = "Mandatory technical documentation must include risk management files and data governance records."
    pred = "Required technical files include risk management protocols and dataset documentation."
    score = answer_trigram_jaccard(pred, gold)
    assert 0.5 <= score <= 1.0


# ── R338 [I9] — the name is the contract ─────────────────────────────────


def test_lexical_proxy_provenance_claims_no_embedding_model():
    """The provenance string must not attribute this metric to an embedder.

    This is the test that would have caught R338 [I9]. METRIC_PROVENANCE is
    serialised wholesale into every durable eval sidecar (evals/bench/runner.py,
    run_official_batch.py, easyhard_ab.py, rescore_sidecars.py, ...), so a false
    attribution here is written into artifacts of runs that never even call the
    function. The previous string read "Semantic similarity proxy (Sentence-BERT
    / character-ngram cosine vector proxy) ... decoupled from surface lexical
    form" for a metric that is 0.70 * char-3gram cosine + 0.30 * word Jaccard.
    """
    diag = METRIC_PROVENANCE["cappelli_2026_diagnostics"]
    assert "answer_trigram_jaccard" in diag, (
        "the lexical proxy must be registered under a name that states what it "
        "computes, not under answer_semantic_similarity"
    )
    # `runner_field_alias` is exempt: it exists precisely to warn that the two
    # runner scripts still PRINT the header `SBERT:` for this metric. Naming a
    # string the reader will actually see is a warning, not an attribution.
    # Every other entry must be free of any embedder name.
    scored = " ".join(v for k, v in diag.items() if k != "runner_field_alias").lower()
    for banned in ("sentence-bert", "sentence_bert", "sbert", "minilm", "sentencetransformer"):
        assert banned not in scored, f"provenance must not attribute this metric to {banned!r}"
    assert "not an embedding model" in diag["answer_trigram_jaccard"].lower()


def test_lexical_proxy_is_near_zero_on_a_low_lexical_paraphrase():
    """Pin the behaviour the old name denied — this is a string counter.

    A genuine all-MiniLM-L6-v2 scores this pair ~0.85. If a real embedding
    model is ever wired in, this test SHOULD fail — and the fix is a new
    function under a new name, not a loosened assertion here.
    """
    gold = (
        "Emotion recognition in the workplace is prohibited under Article 5(1)(f) "
        "except for medical or safety reasons."
    )
    paraphrase = (
        "Employers may not deploy affect-inference AI on staff; the ban carves "
        "out health and security use cases."
    )
    near_verbatim = (
        "Emotion recognition in the workplace is prohibited under Article 5(1)(f) "
        "except for medical or safety reasons, per the AI Act."
    )
    assert answer_trigram_jaccard(paraphrase, gold) < 0.10
    assert answer_trigram_jaccard(near_verbatim, gold) > 0.80


def test_old_lexical_proxy_name_is_the_same_object():
    """The back-compat alias must be a rebinding, never a second copy."""
    from evals.bench.metrics import answer_semantic_similarity_proxy

    assert answer_semantic_similarity_proxy is answer_trigram_jaccard


# ── R338 [I6] — no precision without an independent label ────────────────


def test_threshold_precision_recall_curve_is_withdrawn():
    """The self-labelled precision curve must refuse to produce a number."""
    sim_scores = [0.85, 0.72, 0.45, 0.25, 0.12]
    gold_relevance = [True, True, True, False, False]
    with pytest.raises(NotImplementedError) as exc:
        threshold_precision_recall_curve(sim_scores, gold_relevance)
    msg = str(exc.value)
    assert "score_threshold_retention_curve" in msg
    assert "1.0" in msg


def test_score_threshold_retention_curve_emits_no_precision():
    """The surviving diagnostic reports distribution shape only.

    Fed the shape run_cappelli_bench.py produced — a distribution whose mass
    sits near the 0.2885 batch mean — it reports the honest fact the precision
    curve was hiding: raising the cut to 0.50 throws away 8 of 10 rows. The old
    curve called that same column "precision 1.0".
    """
    sim_scores = [0.9012, 0.6, 0.41, 0.2885, 0.26, 0.24, 0.19, 0.1, 0.05, 0.0]
    curve = score_threshold_retention_curve(sim_scores, thresholds=[0.20, 0.25, 0.50])
    assert len(curve) == 3
    for row in curve:
        assert "precision" not in row
        assert "recall" not in row
        assert "f1" not in row
        assert row["n_total"] == 10
    assert curve[0]["threshold"] == 0.20
    assert curve[0]["n_at_or_above"] == 6
    assert curve[0]["retention"] == 0.6
    assert curve[2]["threshold"] == 0.50
    assert curve[2]["n_at_or_above"] == 2
    assert curve[2]["retention"] == 0.2


def test_score_threshold_retention_curve_handles_empty_input():
    """No rows must not become a 1.0 anything — the old curve's second defect."""
    curve = score_threshold_retention_curve([], thresholds=[0.25])
    assert curve == [
        {"threshold": 0.25, "n_at_or_above": 0, "n_total": 0, "retention": 0.0}
    ]


def test_threshold_analysis_provenance_entry_is_gone():
    """No sidecar may keep advertising a precision curve that cannot exist."""
    diag = METRIC_PROVENANCE["cappelli_2026_diagnostics"]
    assert "threshold_analysis" not in diag
    assert "score_threshold_retention" in diag
    assert "not a precision curve" in diag["score_threshold_retention"].lower()
