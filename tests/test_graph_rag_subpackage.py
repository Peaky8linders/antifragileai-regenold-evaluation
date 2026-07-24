"""Unit test suite for app/engines/graph_rag sub-package modules."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from app.engines.graph_rag.models import GraphQuery, GraphContext, CitationNode
from app.engines.graph_rag.config import config, GraphRAGConfig
from app.engines.graph_rag.parser import (
    deterministic_parse,
    extract_json_object,
)
from app.engines.graph_rag.risk_engine import (
    is_prohibited_inquiry,
    is_harmonized_product_inquiry,
    is_annex_iii_inquiry,
    is_article_6_3_inquiry,
    evaluate_ast_exemptions,
    is_gpai_inquiry,
    is_transparency_inquiry,
)
from app.engines.graph_rag.medtech import (
    MEDTECH_STANDARD_MAP,
    is_medtech_inquiry,
)
from app.engines.graph_rag.retrieval import enrich_context
from app.engines.graph_rag.generators import extract_citations
from app.engines.graph_rag.pipeline import compute_confidence


class TestGraphRAGModels:
    def test_graph_query_defaults(self):
        q = GraphQuery()
        assert q.intent == "general_compliance"
        assert q.entities == []
        assert q.risk_context is None
        assert q.dimension_hint is None

    def test_graph_context_defaults(self):
        ctx = GraphContext()
        assert ctx.obligations == []
        assert ctx.gaps == []
        assert ctx.bridging_context == []
        assert ctx.nodes_traversed == 0


class TestGraphRAGConfig:
    def test_config_flags(self):
        cfg = GraphRAGConfig()
        assert isinstance(cfg.logic_rag_enabled, bool)
        assert isinstance(cfg.medtech_enabled, bool)
        assert isinstance(cfg.answer_v2_enabled, bool)


class TestGraphRAGParser:
    def test_deterministic_parse_article_mentions(self):
        q = deterministic_parse("What does Article 9 and Article 10 require for high risk AI?")
        assert q.intent in ("obligation_check", "article_lookup", "general_compliance", "risk_assessment")
        assert "Art. 9" in q.entities
        assert "Art. 10" in q.entities
        assert q.risk_context == "high"
        assert q.dimension_hint == "risk_mgmt"

    def test_deterministic_parse_annex_mentions(self):
        q = deterministic_parse("Explain Annex III biometric identification systems")
        assert "Annex III" in q.entities

    def test_extract_json_object_direct_and_fenced(self):
        raw_json = '{"intent": "gap_analysis", "entities": ["Art. 9"]}'
        fenced_json = f"```json\n{raw_json}\n```"
        assert extract_json_object(raw_json) == {"intent": "gap_analysis", "entities": ["Art. 9"]}
        assert extract_json_object(fenced_json) == {"intent": "gap_analysis", "entities": ["Art. 9"]}


class TestGraphRAGRiskEngine:
    def test_is_prohibited_inquiry(self):
        assert is_prohibited_inquiry("Is social scoring prohibited under Article 5?") is True
        assert is_prohibited_inquiry("What are general risk management requirements?") is False

    def test_is_harmonized_product_inquiry(self):
        assert is_harmonized_product_inquiry("Does MDR 2017/745 software fall under Article 6(1)?") is True

    def test_is_annex_iii_inquiry(self):
        assert is_annex_iii_inquiry("Is biometric identification covered under Annex III?") is True

    def test_is_article_6_3_inquiry(self):
        assert is_article_6_3_inquiry("Can an AI system be exempt under Article 6(3)?") is True

    def test_is_gpai_inquiry(self):
        assert is_gpai_inquiry("What are systemic risk obligations for GPAI models under Article 51?") is True

    def test_is_transparency_inquiry(self):
        assert is_transparency_inquiry("What watermarking rules apply under Article 50?") is True

    def test_evaluate_ast_exemptions_dedup(self):
        q = GraphQuery(entities=["Annex III"], risk_context="high_risk_annex_iii")
        ctx = GraphContext()
        answers = {"narrow_provisional_task": True}

        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.execute_read.return_value = [
            {"point_id": "point_a", "letter": "a", "text": "narrow_provisional_task"}
        ]

        with patch("app.graph.client.get_graph_client", return_value=mock_client):
            evaluate_ast_exemptions(q, ctx, answers)
            assert len(ctx.ast_evaluations) == 1
            assert "Art. 6(3)(a)" in ctx.ast_evaluations[0] or "Article 6(3)(a)" in ctx.ast_evaluations[0]

            # Second call shouldn't duplicate
            evaluate_ast_exemptions(q, ctx, answers)
            assert len(ctx.ast_evaluations) == 1


class TestGraphRAGMedTech:
    def test_is_medtech_inquiry(self):
        assert is_medtech_inquiry("Is a machine learning diagnostic software a medical device under MDR?") is True
        assert is_medtech_inquiry("What is the penalty for non-compliance under Article 99?") is False

    def test_medtech_standard_map_content(self):
        assert "Art. 9" in MEDTECH_STANDARD_MAP
        assert MEDTECH_STANDARD_MAP["Art. 9"]["standard"] == "ISO 14971:2019"


class TestGraphRAGRetrieval:
    def test_enrich_context_dedup(self):
        q = GraphQuery()
        ctx = GraphContext()
        question = "What ISO standards apply to Article 9 risk management for software medical devices?"

        enrich_context(q, ctx, question)
        initial_len = len(ctx.bridging_context)
        assert initial_len > 0
        assert any("ISO 14971" in b for b in ctx.bridging_context)

        # Idempotent call shouldn't duplicate entries
        enrich_context(q, ctx, question)
        assert len(ctx.bridging_context) == initial_len


class TestGraphRAGGenerators:
    def test_extract_citations(self):
        ctx = GraphContext()
        ctx.obligations = [
            {"id": "obl_1", "article": "13", "text": "Provide transparency information to deployers."}
        ]
        ctx.gaps = [
            {"id": "gap_1", "article": "9", "text": "Continuous risk management system."}
        ]

        citations = extract_citations(ctx)
        assert len(citations) == 2
        assert all(isinstance(c, CitationNode) for c in citations)
        assert citations[0].article_ref == "Article 13"
        assert citations[1].article_ref == "Article 9"


class TestGraphRAGPipeline:
    def test_compute_confidence(self):
        ctx = GraphContext()
        ctx.nodes_traversed = 12
        ctx.edges_followed = 8
        ctx.obligations = [{"id": "o1"}]

        conf = compute_confidence(ctx)
        assert 0.0 <= conf <= 1.0
        assert conf > 0.5
