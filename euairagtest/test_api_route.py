"""Tests for the API-route neural components: LLMEntailmentScorer and DenseRetriever.

Everything here is deterministic and offline: all API calls go through injected
stubs -- no anthropic package, no API key, no network, no torch required.
"""

from __future__ import annotations

import math
import os
import types
import unittest

from euaiact.baselines.dense import DenseRetriever
from euaiact.baselines.llm_entail import LLMEntailmentScorer, _parse_verdict
from euaiact.models import Provision


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prov(pid: str, text: str) -> Provision:
    return Provision(provision_id=pid, chunk_type="p", text=text)


# ---------------------------------------------------------------------------
# Fake Anthropic client/response stubs
# ---------------------------------------------------------------------------

class _TextBlock:
    """Mimics an Anthropic text content block: .type and .text attributes."""
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _FakeResponse:
    """Mimics an Anthropic Messages response object (.content list of blocks)."""

    def __init__(self, text: str) -> None:
        self.content = [_TextBlock(text)]


class _FakeMessages:
    """Mimics anthropic.Anthropic().messages, recording the last call."""

    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.last_call: dict | None = None

    def create(self, **kwargs) -> _FakeResponse:
        self.last_call = kwargs
        return _FakeResponse(self._response_text)


class _FakeClient:
    """Minimal Anthropic client stub: .messages.create(**kwargs) -> response."""

    def __init__(self, response_text: str) -> None:
        self.messages = _FakeMessages(response_text)


# ---------------------------------------------------------------------------
# _parse_verdict unit tests
# ---------------------------------------------------------------------------

class ParseVerdictTests(unittest.TestCase):
    def test_supports_true_returns_confidence(self):
        self.assertAlmostEqual(_parse_verdict('{"supports": true, "confidence": 0.9}'), 0.9)

    def test_supports_false_returns_zero(self):
        self.assertAlmostEqual(_parse_verdict('{"supports": false, "confidence": 0.9}'), 0.0)

    def test_supports_false_no_confidence_returns_zero(self):
        self.assertAlmostEqual(_parse_verdict('{"supports": false}'), 0.0)

    def test_supports_true_no_confidence_defaults_to_one(self):
        self.assertAlmostEqual(_parse_verdict('{"supports": true}'), 1.0)

    def test_garbage_input_returns_zero(self):
        self.assertAlmostEqual(_parse_verdict("I think it supports the claim."), 0.0)

    def test_empty_string_returns_zero(self):
        self.assertAlmostEqual(_parse_verdict(""), 0.0)

    def test_confidence_clamped_above_one(self):
        self.assertAlmostEqual(_parse_verdict('{"supports": true, "confidence": 1.5}'), 1.0)

    def test_confidence_clamped_below_zero(self):
        self.assertAlmostEqual(_parse_verdict('{"supports": true, "confidence": -0.1}'), 0.0)

    def test_codefence_wrapper_tolerated(self):
        text = '```json\n{"supports": true, "confidence": 0.7}\n```'
        self.assertAlmostEqual(_parse_verdict(text), 0.7)


# ---------------------------------------------------------------------------
# LLMEntailmentScorer tests
# ---------------------------------------------------------------------------

class LLMEntailmentScorerTests(unittest.TestCase):
    def _scorer(self, response_text: str) -> LLMEntailmentScorer:
        return LLMEntailmentScorer(client=_FakeClient(response_text))

    def test_supports_true_confidence_090(self):
        scorer = self._scorer('{"supports": true, "confidence": 0.9}')
        self.assertAlmostEqual(scorer.score("claim", "premise"), 0.9)

    def test_supports_false_returns_zero(self):
        scorer = self._scorer('{"supports": false}')
        self.assertAlmostEqual(scorer.score("claim", "premise"), 0.0)

    def test_garbage_response_returns_zero(self):
        scorer = self._scorer("I am unable to determine this.")
        self.assertAlmostEqual(scorer.score("claim", "premise"), 0.0)

    def test_score_batch_two_premises(self):
        """score_batch loops; fake client always returns the same response."""
        scorer = self._scorer('{"supports": true, "confidence": 0.75}')
        results = scorer.score_batch("a question", ["premise A", "premise B"])
        self.assertEqual(len(results), 2)
        self.assertAlmostEqual(results[0], 0.75)
        self.assertAlmostEqual(results[1], 0.75)

    def test_score_batch_empty_returns_empty(self):
        scorer = self._scorer('{"supports": true, "confidence": 0.9}')
        self.assertEqual(scorer.score_batch("claim", []), [])

    def test_score_delegates_to_score_batch(self):
        """score(claim, premise) == score_batch(claim, [premise])[0]."""
        scorer = self._scorer('{"supports": true, "confidence": 0.6}')
        self.assertAlmostEqual(
            scorer.score("q", "p"),
            scorer.score_batch("q", ["p"])[0],
        )

    def test_name_contains_model(self):
        scorer = self._scorer("")
        self.assertIn("llm-nli", scorer.name)

    def test_messages_create_called_with_temperature_zero(self):
        scorer = self._scorer('{"supports": true, "confidence": 0.8}')
        scorer.score("claim", "premise")
        call = scorer.client.messages.last_call
        self.assertEqual(call["temperature"], 0)

    def test_missing_client_and_no_env_key_raises_runtime_error(self):
        """Constructing with no client and no ANTHROPIC_API_KEY must raise."""
        original = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with self.assertRaises(RuntimeError):
                LLMEntailmentScorer()  # no client, no key -> gate fires
        finally:
            if original is not None:
                os.environ["ANTHROPIC_API_KEY"] = original

    def test_injected_client_bypasses_key_check(self):
        """An injected client must work even without ANTHROPIC_API_KEY set."""
        original = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            scorer = LLMEntailmentScorer(client=_FakeClient('{"supports": true, "confidence": 0.5}'))
            self.assertAlmostEqual(scorer.score("claim", "premise"), 0.5)
        finally:
            if original is not None:
                os.environ["ANTHROPIC_API_KEY"] = original


# ---------------------------------------------------------------------------
# Fake embedder for DenseRetriever tests
# ---------------------------------------------------------------------------

def _hash_embed(text: str, dim: int = 8) -> list[float]:
    """Deterministic test embedder: maps text tokens to a fixed-dim vector by
    hashing each token to a bucket and incrementing that bucket's count.
    Reproducible, non-random, no third-party deps."""
    vec = [0.0] * dim
    for token in text.lower().split():
        idx = hash(token) % dim
        vec[idx] += 1.0
    return vec


class _FakeEmbedder:
    """Deterministic embedder stub using _hash_embed. Tracks call count."""

    def __init__(self, dim: int = 8) -> None:
        self.dim = dim
        self.call_count = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        return [_hash_embed(t, self.dim) for t in texts]


# ---------------------------------------------------------------------------
# DenseRetriever tests
# ---------------------------------------------------------------------------

PROVISIONS = [
    _prov("art_1", "high risk classification criteria provider obligations"),
    _prov("art_2", "transparency obligations chatbot disclosure requirements"),
    _prov("art_3", "prohibited practices subliminal manipulation deception"),
]


class DenseRetrieverTests(unittest.TestCase):
    def _retriever(self) -> DenseRetriever:
        return DenseRetriever(PROVISIONS, embedder=_FakeEmbedder())

    def test_embedder_none_raises_runtime_error(self):
        with self.assertRaises(RuntimeError):
            DenseRetriever(PROVISIONS, embedder=None)

    def test_search_returns_provision_ids(self):
        dr = self._retriever()
        results = dr.search("risk classification", k=2)
        self.assertEqual(len(results), 2)
        for pid in results:
            self.assertIn(pid, [p.provision_id for p in PROVISIONS])

    def test_query_nearest_to_matching_provision(self):
        """A query whose tokens overlap most with art_1 should rank art_1 first."""
        dr = self._retriever()
        results = dr.search("high risk classification criteria", k=3)
        self.assertEqual(results[0], "art_1")

    def test_search_scored_returns_scores_in_desc_order(self):
        dr = self._retriever()
        scored = dr.search_scored("chatbot transparency disclosure", k=3)
        scores = [s for _, s in scored]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_search_scored_top_result_is_art_2(self):
        dr = self._retriever()
        scored = dr.search_scored("chatbot transparency disclosure", k=3)
        self.assertGreater(len(scored), 0)
        self.assertEqual(scored[0][0], "art_2")

    def test_determinism(self):
        """Two retrievers with same embedder type and corpus must agree."""
        dr1 = DenseRetriever(PROVISIONS, embedder=_FakeEmbedder())
        dr2 = DenseRetriever(PROVISIONS, embedder=_FakeEmbedder())
        q = "subliminal manipulation prohibited"
        self.assertEqual(dr1.search_scored(q, k=3), dr2.search_scored(q, k=3))

    def test_corpus_embedded_once_at_construction(self):
        """The embedder must be called exactly once at construction for the corpus,
        then once per query call."""
        emb = _FakeEmbedder()
        dr = DenseRetriever(PROVISIONS, embedder=emb)
        corpus_calls = emb.call_count  # should be 1
        dr.search("anything", k=1)
        self.assertEqual(emb.call_count, corpus_calls + 1)

    def test_empty_corpus_returns_empty(self):
        dr = DenseRetriever([], embedder=_FakeEmbedder())
        self.assertEqual(dr.search("query", k=5), [])
        self.assertEqual(dr.search_scored("query", k=5), [])

    def test_empty_query_returns_empty(self):
        dr = self._retriever()
        self.assertEqual(dr.search("", k=5), [])
        self.assertEqual(dr.search_scored("", k=5), [])

    def test_k_limits_results(self):
        dr = self._retriever()
        scored = dr.search_scored("risk chatbot prohibited", k=2)
        self.assertLessEqual(len(scored), 2)

    def test_search_and_search_scored_consistent(self):
        dr = self._retriever()
        q = "chatbot transparency"
        ids_from_search = dr.search(q, k=3)
        ids_from_scored = [pid for pid, _ in dr.search_scored(q, k=3)]
        self.assertEqual(ids_from_search, ids_from_scored)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
