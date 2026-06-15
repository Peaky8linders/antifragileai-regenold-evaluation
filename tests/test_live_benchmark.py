import pytest
from unittest.mock import patch, MagicMock

from evals.bench.run_live_benchmark import (
    load_aireg_bench,
    load_air_bench_2024,
    load_davidath_subset,
    run
)
from evals.regenold.scenarios_medtech_lifesci_v4 import MEDTECH_SCENARIOS_V4


def test_load_aireg_bench():
    items = load_aireg_bench()
    assert len(items) == 10
    assert "expected_keywords" in items[0]


def test_load_air_bench_2024():
    items = load_air_bench_2024()
    assert len(items) == 15
    assert "expected_keywords" in items[0]


def test_load_davidath_subset():
    qa = [{"question": "q", "answer": "a", "relevant_article": 5}] * 20
    sc = [{"role": "Provider", "risk_level": "high-risk", "related_articles": [6]}] * 20
    
    sub_qa, sub_sc = load_davidath_subset(qa, sc)
    assert len(sub_qa) == 10
    assert len(sub_sc) == 10


@patch("evals.bench.run_live_benchmark._run_qa_http")
@patch("evals.bench.run_live_benchmark._persist_prod")
def test_run_benchmark(mock_persist, mock_run_qa):
    # Mock HTTP run
    mock_run_qa.return_value = [
        {
            "item_id": "test_01",
            "passed": True,
            "http_status": 200,
            "_row_score": MagicMock()
        }
    ]
    
    # Mock persistence
    mock_persist.return_value = {
        "summary": {},
        "label": "test",
        "endpoint": "http://test",
    }
    
    # Run the benchmark offline
    with patch("evals.bench.dataset.ensure_dataset"):
        with patch("evals.bench.dataset.load_qa_pairs", return_value=[{"question": "Q1", "answer": "A1", "relevant_article": 1}]):
            with patch("evals.bench.dataset.load_scenarios", return_value=[{"role": "Provider"}]):
                result = run(
                    endpoint="http://dummy",
                    api_key="dummy_key",
                    label="test",
                    limit=2
                )
    
    assert result is not None
    mock_run_qa.assert_called_once()
    mock_persist.assert_called_once()
