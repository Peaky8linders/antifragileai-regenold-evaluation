"""Integration tests for SOTA GraphRAG architecture components."""

from __future__ import annotations

import pytest
from app.data.ids import ProvisionId, ProvisionIdError
from app.graph.schema import EdgeType, NodeType
from app.graph.knowledge_graph import KnowledgeGraph, build_graph
from app.graph.cypher_exporter import to_cypher
from app.engines.retrieval_stack import TfidfRetriever, LsaRetriever
from app.engines.graph_expansion_engine import GraphExpansionRetriever, ExpansionWeights
from app.engines.crag_nli_verifier import LexicalEntailmentScorer
from app.integrations.regenold.refs import parse, to_user_facing


def test_provision_id_roundtrip():
    pid = ProvisionId.from_eid("art_6__para_2__point_a")
    assert pid.citation == "Art. 6(2)(a)"
    assert pid.article_no == 6
    assert pid.paragraph_no == 2
    assert pid.point_label == "a"
    assert pid.parent_eid == "art_6__para_2"
    assert pid.eli_uri == "https://eur-lex.europa.eu/eli/reg/2024/1689/oj#art_6__para_2__point_a"

    # From citation
    parsed = ProvisionId.from_citation("Art. 6(2)(a)")
    assert parsed.eid == "art_6__para_2__point_a"


def test_ref_parser_accepts_eid():
    spec = parse("art_6__para_2__point_a")
    assert spec.article_number == 6
    assert spec.subpoints == ("2", "a")
    assert to_user_facing("art_6__para_2__point_a") == "Article 6.2.a"


def test_knowledge_graph_construction():
    provisions = [
        {
            "provision_id": "art_6__para_2",
            "citation": "Art. 6(2)",
            "text": "High-risk AI systems referred to in Annex III shall be considered high-risk.",
        },
        {
            "provision_id": "art_6__para_2__point_a",
            "citation": "Art. 6(2)(a)",
            "text": "the AI system is intended to be used as a safety component.",
        },
    ]
    graph = build_graph(provisions)
    assert len(graph.nodes) >= 2
    assert graph.get_node("art_6__para_2") is not None
    assert graph.get_node("art_6__para_2__point_a") is not None

    # Check parent-child edge
    children = graph.children("art_6__para_2")
    assert "art_6__para_2__point_a" in children

    # Cypher export test
    cypher_script = to_cypher(graph)
    assert "MERGE (n:Provision:Article {id: \"art_6__para_2\"})" in cypher_script


def test_graph_expansion_retrieval():
    provisions = [
        {
            "provision_id": "art_6__para_1",
            "citation": "Art. 6(1)",
            "text": "Classification rules for high-risk AI systems.",
        },
        {
            "provision_id": "art_6__para_2",
            "citation": "Art. 6(2)",
            "text": "High-risk AI systems listed in Annex III are high-risk.",
        },
    ]
    graph = build_graph(provisions)
    retriever = GraphExpansionRetriever(provisions, graph, seed_k=2)
    results = retriever.search("high-risk AI systems Annex III", k=2)
    assert len(results) > 0
    assert "art_6__para_2" in results


def test_lexical_entailment_verifier():
    provisions = [
        {
            "provision_id": "art_5",
            "citation": "Art. 5",
            "text": "Prohibited AI practices: emotion recognition in workplace or education.",
        }
    ]
    scorer = LexicalEntailmentScorer(provisions)
    score = scorer.score(
        claim="Is emotion recognition in the workplace prohibited under the AI Act?",
        premise=provisions[0]["text"],
    )
    assert score > 0.3
