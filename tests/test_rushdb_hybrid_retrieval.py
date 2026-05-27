"""Tests for RushDB hybrid retrieval env gate and ref mapping."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.engines import rushdb_hybrid_retrieval as rh


class TestHybridEnabled:
    def test_default_off(self, monkeypatch):
        monkeypatch.delenv("REGENOLD_RUSHDB_HYBRID", raising=False)
        assert rh.is_hybrid_enabled() is False

    def test_on_requires_client(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_RUSHDB_HYBRID", "1")
        monkeypatch.setattr(
            "app.graph.rushdb_client.is_enabled",
            lambda: False,
        )
        assert rh.is_hybrid_enabled() is False


class TestRecordToRef:
    def test_article_record(self):
        rec = SimpleNamespace(label="Article", number="13", id="article_13")
        assert rh._record_to_internal_ref(rec) == "Art. 13"

    def test_annex_record(self):
        rec = SimpleNamespace(label="Annex", number="III", id="annex_III")
        assert rh._record_to_internal_ref(rec) == "Annex III"

    def test_id_fallback(self):
        rec = SimpleNamespace(id="article_6")
        assert rh._record_to_internal_ref(rec) == "Art. 6"


class TestClassifyIntent:
    def test_regulatory_lookup(self):
        intent = rh.classify_query_intent("What are deployer obligations under Article 26?")
        assert intent["intent"] == "regulatory_lookup"

    def test_general_fallback(self):
        intent = rh.classify_query_intent("hello world")
        assert intent["intent"] == "general"


class TestRetrieveArticleRefs:
    def test_retrieve_article_refs_fuses_semantic_and_metadata(self, monkeypatch):
        from unittest import mock

        # 1. Enable hybrid retrieval
        monkeypatch.setattr(rh, "is_hybrid_enabled", lambda: True)

        # 2. Setup mock client and mock responses
        mock_client = mock.MagicMock()
        monkeypatch.setattr(
            "app.graph.rushdb_client._get_client",
            lambda: mock_client,
        )

        # Mock semantic search returns
        sem_res = mock.MagicMock()
        sem_res.data = [
            mock.MagicMock(label="Article", number="13", id="article_13"),
            mock.MagicMock(label="Article", number="9", id="article_9"),
        ]
        mock_client.ai.search.return_value = sem_res

        # Mock metadata search returns
        meta_res = mock.MagicMock()
        meta_res.data = [
            mock.MagicMock(label="Article", number="9", id="article_9"),  # duplicate
            mock.MagicMock(label="Annex", number="III", id="annex_III"),
        ]
        mock_client.records.find.return_value = meta_res

        # 3. Retrieve
        refs = rh.retrieve_article_refs("some question", limit=3)

        # 4. Assert
        # Fuses: semantic first, then metadata. Limit = 3.
        # "Art. 13" (sem), "Art. 9" (sem), "Annex III" (meta)
        assert refs == ["Art. 13", "Art. 9", "Annex III"]
        assert len(refs) == 3

        # Confirm client search and find called
        mock_client.ai.search.assert_called_once()
        mock_client.records.find.assert_called_once()

