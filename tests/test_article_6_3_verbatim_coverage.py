from unittest.mock import MagicMock, patch
from app.engines.legal_ast import ingest_legal_ast
from app.data.provision_text import get_provision_text

def test_article_6_3_verbatim_text_coverage():
    # 1. Assert get_provision_text resolves Article 6(3) paragraphs and subpoints exactly
    p3 = get_provision_text("Article 6(3)")
    assert p3 is not None
    assert p3.startswith("By derogation from paragraph 2")
    assert "narrow procedural task" in p3
    assert "preparatory task" in p3
    assert "profiling of natural persons" in p3

    p3a = get_provision_text("Article 6(3)(a)")
    assert p3a == "the AI system is intended to perform a narrow procedural task"

    p3b = get_provision_text("Article 6(3)(b)")
    assert p3b == "the AI system is intended to improve the result of a previously completed human activity"

    p3c = get_provision_text("Article 6(3)(c)")
    assert p3c == "the AI system is intended to detect decision-making patterns or deviations from prior decision-making patterns and is not meant to replace or influence the previously completed human assessment, without proper human review"

    p3d = get_provision_text("Article 6(3)(d)")
    assert p3d is not None
    assert p3d.startswith("the AI system is intended to perform a preparatory task")
    assert "profiling of natural persons" in p3d

@patch("app.graph.client.get_graph_client")
def test_ingest_legal_ast_queries(mock_get_client):
    mock_client = MagicMock()
    mock_client.enabled = True
    mock_get_client.return_value = mock_client

    ingest_legal_ast()

    assert mock_client.execute_write_batch.call_count >= 1
    
    # Combine queries from all batches
    queries = []
    for call in mock_client.execute_write_batch.call_args_list:
        queries.extend(call[0][0])

    # Verify that the parsed Article 6(3) queries are in the batch
    # We should have MERGE queries for Article 6, Paragraph 6(3), and points a, b, c, d
    q_texts = [q[0] for q in queries]
    q_params = [q[1] for q in queries]

    assert any("MERGE (a:Article {id: $id})" in qt for qt in q_texts)
    assert any("MERGE (p:Paragraph {id: $id})" in qt for qt in q_texts)
    
    # Check that Article 6 was created
    assert any(qp.get("id") == "article_6" for qp in q_params)

    # Check paragraph 3 parameters contains the actual text
    p3_params = [qp for qp in q_params if qp.get("id") == "article_6_3" and "By derogation" in qp.get("text", "")]
    assert len(p3_params) == 1

    # Check points a, b, c, d are present
    letters = {"a", "b", "c", "d"}
    found_letters = set()
    for qp in q_params:
        if qp.get("para_id") == "article_6_3" and "letter" in qp:
            found_letters.add(qp["letter"])
            if qp["letter"] == "a":
                assert "narrow procedural task" in qp["text"]
            elif qp["letter"] == "d":
                assert "preparatory task" in qp["text"]

    assert found_letters == letters
