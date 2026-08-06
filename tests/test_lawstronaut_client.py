"""Unit tests for Lawstronaut client and fallback legal provenance."""

from __future__ import annotations

from app.integrations.lawstronaut_client import LawstronautClient, OFFICIAL_PROVENANCE_FALLBACK


def test_lawstronaut_client_fallback() -> None:
    client = LawstronautClient(token="")
    meta = client.get_document_metadata(47256354)
    assert meta["celex_id"] == "02024R1689-20260727"
    assert meta["eli_uri"] == "http://data.europa.eu/eli/reg/2024/1689/2026-07-27"
    assert "https://eur-lex.europa.eu" in meta["legal_link"]


def test_lawstronaut_search_without_token() -> None:
    client = LawstronautClient(token="")
    results = client.search_documents_by_title("AI Act")
    assert results == []
