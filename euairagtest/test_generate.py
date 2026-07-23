"""Tests for Phase-4 grounded generation + citation-verification layer.

All tests are fully offline -- no network, no API key, no `anthropic` package.
The LLM client is dependency-injected via a stub.
"""

from __future__ import annotations

import json
import os
import unittest

from euaiact.baselines.generate import CitationGuard, CitedGenerationBaseline
from euaiact.baselines.retrieval import Retriever
from euaiact.graph.model import KnowledgeGraph
from euaiact.graph.schema import EdgeType, NodeType
from euaiact.models import Provision


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _build_graph() -> KnowledgeGraph:
    """Tiny KG: art_6 -> art_6__para_2 -> {art_6__para_2__point_a, art_6__para_2__point_b}
    art_6__para_2 cross-refs art_50__para_1 (structural link for coherence tests).
    art_99 is completely unrelated (island node).
    """
    g = KnowledgeGraph()
    for pid in (
        "art_6",
        "art_6__para_2",
        "art_6__para_2__point_a",
        "art_6__para_2__point_b",
        "art_50__para_1",
        "art_99",
    ):
        g.add_node(pid, NodeType.PROVISION)
    g.add_edge(EdgeType.HAS_CHILD, "art_6", "art_6__para_2")
    g.add_edge(EdgeType.HAS_CHILD, "art_6__para_2", "art_6__para_2__point_a")
    g.add_edge(EdgeType.HAS_CHILD, "art_6__para_2", "art_6__para_2__point_b")
    g.add_edge(EdgeType.CROSS_REFERENCES_INTERNAL, "art_6__para_2", "art_50__para_1")
    return g


def _build_provisions() -> list[Provision]:
    return [
        Provision(provision_id="art_6", chunk_type="p", text="high risk classification rules"),
        Provision(provision_id="art_6__para_2", chunk_type="p", text="classification criteria annex derogation"),
        Provision(provision_id="art_6__para_2__point_a", chunk_type="p", text="point a conditions"),
        Provision(provision_id="art_50__para_1", chunk_type="p", text="transparency chatbot disclosure"),
    ]


# ---------------------------------------------------------------------------
# Stub LLM client
# ---------------------------------------------------------------------------


class _Block:
    def __init__(self, text: str, type: str = "text") -> None:
        self.text = text
        self.type = type


class _Resp:
    def __init__(self, citations: list[str]) -> None:
        payload = json.dumps({"answer": "stub answer", "citations": citations})
        self.content = [_Block(payload)]


class _FakeMessages:
    def __init__(self, citations: list[str]) -> None:
        self._citations = citations
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _Resp(self._citations)


class _FakeClient:
    def __init__(self, citations: list[str]) -> None:
        self.messages = _FakeMessages(citations)


class _StubRetriever(Retriever):
    def __init__(self, ids: list[str]) -> None:
        self._ids = ids

    def search(self, query: str, k: int) -> list[str]:
        return self._ids[:k]


# ---------------------------------------------------------------------------
# CitationGuard: is_real_node
# ---------------------------------------------------------------------------


class TestIsRealNode(unittest.TestCase):
    def setUp(self) -> None:
        self.guard = CitationGuard(_build_graph())

    def test_real_eid_returns_true(self) -> None:
        self.assertTrue(self.guard.is_real_node("art_6__para_2"))

    def test_fabricated_eid_returns_false(self) -> None:
        self.assertFalse(self.guard.is_real_node("art_999"))
        self.assertFalse(self.guard.is_real_node("art_6__para_99__point_z"))

    def test_human_form_resolving_to_real_node_returns_true(self) -> None:
        # "Article 6(2)" -> art_6__para_2 which is in the graph
        self.assertTrue(self.guard.is_real_node("Art. 6(2)"))

    def test_human_form_resolving_to_absent_node_returns_false(self) -> None:
        # Art. 6(3) -> art_6__para_3 which is NOT in the graph
        self.assertFalse(self.guard.is_real_node("Art. 6(3)"))

    def test_completely_unparseable_string_returns_false(self) -> None:
        self.assertFalse(self.guard.is_real_node("not a provision at all"))
        self.assertFalse(self.guard.is_real_node(""))


# ---------------------------------------------------------------------------
# CitationGuard: filter
# ---------------------------------------------------------------------------


class TestFilter(unittest.TestCase):
    def setUp(self) -> None:
        self.guard = CitationGuard(_build_graph())

    def test_valid_in_candidate_survives(self) -> None:
        result = self.guard.filter(
            ["art_6__para_2"],
            {"art_6__para_2"},
        )
        self.assertEqual(result, ["art_6__para_2"])

    def test_real_node_not_in_candidate_is_dropped(self) -> None:
        # art_50__para_1 is a real node but NOT in the candidate set
        result = self.guard.filter(
            ["art_6__para_2", "art_50__para_1"],
            {"art_6__para_2"},
        )
        self.assertEqual(result, ["art_6__para_2"])

    def test_fabricated_citation_is_dropped(self) -> None:
        # art_999 does not exist in the graph at all
        result = self.guard.filter(
            ["art_6__para_2", "art_999"],
            {"art_6__para_2", "art_999"},
        )
        self.assertEqual(result, ["art_6__para_2"])

    def test_hallucination_zeroing_three_way(self) -> None:
        """The spec's core scenario: valid-in-candidate, real-but-not-in-candidate,
        fabricated.  Only the first survives; order is preserved."""
        emitted = ["art_6__para_2", "art_50__para_1", "art_999"]
        candidates = {"art_6__para_2"}
        result = self.guard.filter(emitted, candidates)
        self.assertEqual(result, ["art_6__para_2"])

    def test_order_preserved(self) -> None:
        emitted = ["art_6__para_2__point_b", "art_6__para_2__point_a"]
        candidates = {"art_6__para_2__point_a", "art_6__para_2__point_b"}
        result = self.guard.filter(emitted, candidates)
        self.assertEqual(result, ["art_6__para_2__point_b", "art_6__para_2__point_a"])

    def test_empty_emitted_returns_empty(self) -> None:
        self.assertEqual(self.guard.filter([], {"art_6"}), [])

    def test_empty_candidates_drops_everything(self) -> None:
        self.assertEqual(self.guard.filter(["art_6__para_2"], set()), [])

    def test_human_form_candidate_is_canonicalised(self) -> None:
        # The candidate set uses human form; the emitted citation uses eid form.
        # Both must canonicalise to art_6__para_2 for the match to succeed.
        result = self.guard.filter(["art_6__para_2"], {"Art. 6(2)"})
        self.assertEqual(result, ["art_6__para_2"])


# ---------------------------------------------------------------------------
# CitationGuard: coherence / incoherent
# ---------------------------------------------------------------------------


class TestCoherence(unittest.TestCase):
    def setUp(self) -> None:
        self.guard = CitationGuard(_build_graph())

    def test_zero_citations_is_one(self) -> None:
        self.assertEqual(self.guard.coherence([]), 1.0)

    def test_one_citation_is_one(self) -> None:
        self.assertEqual(self.guard.coherence(["art_6"]), 1.0)

    def test_parent_and_child_are_coherent(self) -> None:
        # art_6 is the parent of art_6__para_2 via HAS_CHILD; they form one
        # connected component.
        c = self.guard.coherence(["art_6", "art_6__para_2"])
        self.assertAlmostEqual(c, 1.0)
        self.assertEqual(self.guard.incoherent(["art_6", "art_6__para_2"]), [])

    def test_cross_ref_links_are_coherent(self) -> None:
        # art_6__para_2 CROSS_REFERENCES_INTERNAL art_50__para_1
        c = self.guard.coherence(["art_6__para_2", "art_50__para_1"])
        self.assertAlmostEqual(c, 1.0)
        self.assertEqual(self.guard.incoherent(["art_6__para_2", "art_50__para_1"]), [])

    def test_full_connected_cluster_is_fully_coherent(self) -> None:
        # art_6, art_6__para_2, art_6__para_2__point_a all ancestor/descendant;
        # art_50__para_1 linked via cross-ref from art_6__para_2.
        cluster = [
            "art_6",
            "art_6__para_2",
            "art_6__para_2__point_a",
            "art_50__para_1",
        ]
        self.assertAlmostEqual(self.guard.coherence(cluster), 1.0)
        self.assertEqual(self.guard.incoherent(cluster), [])

    def test_island_node_drops_coherence(self) -> None:
        # art_99 shares no edges with the cluster above.
        cluster_with_island = [
            "art_6",
            "art_6__para_2",
            "art_6__para_2__point_a",
            "art_99",
        ]
        c = self.guard.coherence(cluster_with_island)
        # 3 out of 4 in the largest component
        self.assertAlmostEqual(c, 3 / 4)
        incoherent = self.guard.incoherent(cluster_with_island)
        self.assertIn("art_99", incoherent)
        self.assertNotIn("art_6", incoherent)

    def test_two_islands_coherence_is_half(self) -> None:
        # art_6__para_2__point_a and art_6__para_2__point_b are siblings (both
        # children of art_6__para_2), so they ARE connected through their common
        # parent... but their common parent art_6__para_2 is not in this list.
        # Without art_6__para_2 in the set, there is no direct edge between the
        # two points, and no cross-reference.  So they form two isolated nodes.
        c = self.guard.coherence(["art_6__para_2__point_a", "art_6__para_2__point_b"])
        # Neither is an ancestor of the other; no cross-ref between them.
        self.assertAlmostEqual(c, 1 / 2)
        incoherent = self.guard.incoherent(["art_6__para_2__point_a", "art_6__para_2__point_b"])
        self.assertEqual(len(incoherent), 1)

    def test_incoherent_with_one_citation_is_empty(self) -> None:
        self.assertEqual(self.guard.incoherent(["art_6"]), [])

    def test_incoherent_empty_is_empty(self) -> None:
        self.assertEqual(self.guard.incoherent([]), [])


# ---------------------------------------------------------------------------
# CitedGenerationBaseline
# ---------------------------------------------------------------------------


class TestCitedGenerationBaseline(unittest.TestCase):
    def _baseline(self, llm_citations: list[str], retriever_ids: list[str] | None = None) -> CitedGenerationBaseline:
        if retriever_ids is None:
            retriever_ids = ["art_6__para_2", "art_6__para_2__point_a"]
        return CitedGenerationBaseline(
            provisions=_build_provisions(),
            graph=_build_graph(),
            retriever=_StubRetriever(retriever_ids),
            k=5,
            model="test-model",
            client=_FakeClient(llm_citations),
        )

    def test_valid_candidate_eid_survives(self) -> None:
        b = self._baseline(["art_6__para_2"])
        out = b.predict({"id": "q1", "question": "high risk classification", "scenario": None})
        self.assertEqual(out, ["art_6__para_2"])

    def test_fabricated_eid_is_zeroed(self) -> None:
        # art_999 is not in the graph; guard must drop it.
        b = self._baseline(["art_6__para_2", "art_999"])
        out = b.predict({"id": "q1", "question": "high risk classification", "scenario": None})
        self.assertNotIn("art_999", out)
        self.assertIn("art_6__para_2", out)

    def test_real_node_outside_candidate_set_is_dropped(self) -> None:
        # art_50__para_1 is in the graph but NOT in the retriever's returned ids.
        b = self._baseline(
            llm_citations=["art_6__para_2", "art_50__para_1"],
            retriever_ids=["art_6__para_2"],
        )
        out = b.predict({"id": "q1", "question": "q", "scenario": None})
        self.assertIn("art_6__para_2", out)
        self.assertNotIn("art_50__para_1", out)

    def test_no_citations_returns_empty(self) -> None:
        b = self._baseline([])
        out = b.predict({"id": "q1", "question": "something", "scenario": None})
        self.assertEqual(out, [])

    def test_temperature_zero_passed_to_client(self) -> None:
        b = self._baseline(["art_6__para_2"])
        b.predict({"id": "q1", "question": "q", "scenario": None})
        call = b.client.messages.calls[0]
        self.assertEqual(call["temperature"], 0)

    def test_model_passed_to_client(self) -> None:
        b = self._baseline(["art_6__para_2"])
        b.predict({"id": "q1", "question": "q", "scenario": None})
        self.assertEqual(b.client.messages.calls[0]["model"], "test-model")

    def test_no_client_no_key_raises_runtime_error(self) -> None:
        # Ensure ANTHROPIC_API_KEY is absent.
        saved = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with self.assertRaises(RuntimeError):
                CitedGenerationBaseline(
                    provisions=_build_provisions(),
                    graph=_build_graph(),
                    retriever=_StubRetriever([]),
                )
        finally:
            if saved is not None:
                os.environ["ANTHROPIC_API_KEY"] = saved

    def test_empty_retriever_returns_empty_without_calling_llm(self) -> None:
        b = self._baseline(["art_6__para_2"], retriever_ids=[])
        out = b.predict({"id": "q1", "question": "q", "scenario": None})
        self.assertEqual(out, [])
        self.assertEqual(b.client.messages.calls, [])

    def test_malformed_json_from_llm_returns_empty(self) -> None:
        """A response that isn't valid JSON should not crash; guard returns []."""

        class _BadResp:
            content = [_Block("this is not json at all")]

        class _BadMessages:
            calls: list = []

            def create(self, **kwargs):
                self.calls.append(kwargs)
                return _BadResp()

        class _BadClient:
            messages = _BadMessages()

        b = CitedGenerationBaseline(
            provisions=_build_provisions(),
            graph=_build_graph(),
            retriever=_StubRetriever(["art_6__para_2"]),
            k=5,
            model="test-model",
            client=_BadClient(),
        )
        out = b.predict({"id": "q1", "question": "q", "scenario": None})
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()
