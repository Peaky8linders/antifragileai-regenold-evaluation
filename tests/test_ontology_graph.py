from unittest.mock import MagicMock, patch
from app.graph.ontology_ingest import ingest_ontology

@patch("app.graph.ontology_ingest.get_graph_client")
def test_ingest_ontology(mock_get_client):
    mock_client = MagicMock()
    mock_client.enabled = True
    mock_get_client.return_value = mock_client
    
    ingest_ontology()
    
    # Assert that batch execute was called with queries
    assert mock_client.execute_write_batch.call_count == 1
    queries = mock_client.execute_write_batch.call_args[0][0]
    
    # Verify that queries is a list of tuples and has significant length
    assert isinstance(queries, list)
    assert len(queries) > 10
