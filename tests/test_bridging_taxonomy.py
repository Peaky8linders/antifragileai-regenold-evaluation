import pytest
from unittest.mock import MagicMock, patch
from app.llm import intent_classifier as ic
from app.llm.openai_wrapper_provider import OpenAIWrapperResponse
from app.engines.graph_rag import GraphRAGRequest, ask_compliance_question

@pytest.fixture(autouse=True)
def _reset() -> None:
    ic._reset_for_tests()
    yield
    ic._reset_for_tests()

def test_intent_classifier_attaches_bridging_context(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    class FakeProvider:
        def complete(self, _req):
            return OpenAIWrapperResponse(
                text=(
                    '{"intent": "data_governance", "primary_anchor": "Art. 10", '
                    '"alternate_anchors": [], "confidence": 0.95}'
                ),
                model="claude-haiku-4-5",
                elapsed_ms=180,
            )

    with patch.object(ic, "get_openai_wrapper_provider", return_value=FakeProvider()):
        result = ic.classify_intent("Tell me about data governance rules under the Act.")
        assert result is not None
        assert result.intent == "data_governance"
        assert "GDPR Art. 9 (Special Categories of Data)" in result.bridging_context

def test_graph_rag_injects_bridging_context(monkeypatch) -> None:
    # Test that when request has bridging_context, it is appended to context and appears in prompt context
    req = GraphRAGRequest(
        question="How does data governance work?",
        bridging_context=["GDPR Art. 9 (Special Categories of Data)"]
    )
    
    # We mock _retrieve_from_graph to avoid hitting actual DB/index, returning a mock context
    from app.engines.graph_rag import GraphContext
    mock_context = GraphContext()
    
    with patch("app.engines.graph_rag._retrieve_from_graph", return_value=mock_context):
        with patch("app.engines.graph_rag._deterministic_answer", return_value="Deterministic answer"):
            with patch("app.engines.graph_rag._two_stage_generate", return_value=("Generated answer", False)):
                res = ask_compliance_question(req)
                assert res is not None
                # Check that bridging context was added to mock_context
                assert "GDPR Art. 9 (Special Categories of Data)" in mock_context.bridging_context
                
                # Check that context references block contains the bridging context
                from app.engines.graph_rag import _build_context_references_block
                block = _build_context_references_block(mock_context)
                assert "CROSS-REGULATORY BRIDGING CONTEXT" in block
                assert "- GDPR Art. 9 (Special Categories of Data)" in block

def test_graph_rag_evaluates_legal_ast() -> None:
    from app.models import AssessmentAnswer
    req = GraphRAGRequest(
        question="What does Art. 5 say?",
        answers={
            "subliminal": AssessmentAnswer.YES,
            "medical_exception": AssessmentAnswer.NO
        }
    )
    
    from app.engines.graph_rag import GraphContext
    mock_context = GraphContext()
    
    with patch("app.engines.graph_rag._retrieve_from_graph", return_value=mock_context):
        with patch("app.engines.graph_rag._deterministic_answer", return_value="Deterministic answer"):
            with patch("app.engines.graph_rag._two_stage_generate", return_value=("Generated answer", False)):
                res = ask_compliance_question(req)
                assert res is not None
                
                # Check that AST evaluation was performed and added to context
                assert hasattr(mock_context, "ast_evaluations")
                assert len(mock_context.ast_evaluations) > 0
                assert "Article/Annex Art. 5 logical evaluation: Practice prohibited / Condition met" in mock_context.ast_evaluations[0]
                
                # Check that context references block contains the AST evaluations
                from app.engines.graph_rag import _build_context_references_block
                block = _build_context_references_block(mock_context)
                assert "LEGAL AST LOGICAL EVALUATIONS" in block
                assert "- Article/Annex Art. 5 logical evaluation: Practice prohibited / Condition met" in block
