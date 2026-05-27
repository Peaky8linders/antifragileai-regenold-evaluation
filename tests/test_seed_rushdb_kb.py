"""Regression tests for RushDB KB seeder coverage and label mapping."""
from __future__ import annotations

from app.data.article_existence import ARTICLE_EXISTENCE
from app.data.eu_ai_act_corpus import ARTICLE_FULL_TEXT, RECITALS
from scripts.seed_rushdb_kb import (
    RUSHDB_LABEL_MAP,
    SEED_VERSION,
    _EXPECTED_ANNEX_COUNT,
    _EXPECTED_ARTICLE_COUNT,
    _EXPECTED_DEFINITION_COUNT,
    _EXPECTED_OPERATOR_ROLE_COUNT,
    _EXPECTED_RECITAL_COUNT,
    _EXPECTED_RISK_LEVEL_COUNT,
    build_payload,
    rushdb_label_for_bucket,
    run_seed,
    validate_payload,
)


class TestRushdbLabelMap:
    def test_article_maps_to_pascal_case(self):
        assert rushdb_label_for_bucket("ARTICLE") == "Article"

    def test_annex_maps_to_pascal_case(self):
        assert rushdb_label_for_bucket("ANNEX") == "Annex"

    def test_kb_metadata_unchanged(self):
        assert rushdb_label_for_bucket("KB_METADATA") == "KB_METADATA"

    def test_all_buckets_have_client_compatible_labels(self):
        expected = {
            "ARTICLE",
            "ANNEX",
            "RECITAL",
            "DEFINITION",
            "OBLIGATION",
            "ANNEX_III_CATEGORY",
            "RISK_LEVEL",
            "OPERATOR_ROLE",
            "KB_METADATA",
        }
        assert set(RUSHDB_LABEL_MAP.keys()) == expected
        assert RUSHDB_LABEL_MAP["ARTICLE"] == "Article"
        assert RUSHDB_LABEL_MAP["ANNEX"] == "Annex"
        assert RUSHDB_LABEL_MAP["DEFINITION"] == "Definition"


class TestRushdbPayloadCoverage:
    def test_build_payload_counts(self):
        payload = build_payload()
        assert len(payload["ARTICLE"]) == _EXPECTED_ARTICLE_COUNT
        assert len(payload["ANNEX"]) == _EXPECTED_ANNEX_COUNT
        assert len(payload["RECITAL"]) == _EXPECTED_RECITAL_COUNT
        assert len(payload["DEFINITION"]) == _EXPECTED_DEFINITION_COUNT
        assert len(payload["OPERATOR_ROLE"]) == _EXPECTED_OPERATOR_ROLE_COUNT
        assert len(payload["RISK_LEVEL"]) == _EXPECTED_RISK_LEVEL_COUNT

    def test_validate_payload_passes(self):
        payload = build_payload()
        assert validate_payload(payload) == []

    def test_article_content_is_full_prose_not_truncated(self):
        payload = build_payload()
        by_id = {row["id"]: row for row in payload["ARTICLE"]}
        for ref in sorted(
            (r for r in ARTICLE_EXISTENCE if r.startswith("Art. ")),
            key=lambda r: int(r.split(".", 1)[1].strip()),
        ):
            num = ref.split(".", 1)[1].strip()
            art_id = f"article_{num}"
            body = ARTICLE_FULL_TEXT.get(ref, "").replace("\xa0", " ").strip()
            assert by_id[art_id]["content"] == body
            assert len(by_id[art_id]["content"]) == len(body)

    def test_hybrid_metadata_on_articles(self):
        payload = build_payload()
        art = payload["ARTICLE"][0]
        assert art["sourceType"] == "regulation"
        assert art["jurisdiction"] == "EU"
        assert art["framework"] == "EU_AI_ACT"
        assert "CHUNK" in art
        assert len(art["CHUNK"]) >= 1

    def test_dry_run_without_auth_token(self, monkeypatch):
        monkeypatch.delenv("RUSHDB_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("RUSHDB_API_KEY", raising=False)
        result = run_seed(dry_run=True)
        assert result["status"] == "dry_run"
        assert result["seed_version"] == SEED_VERSION
        assert result["counts"]["ARTICLE"] == _EXPECTED_ARTICLE_COUNT
        assert result["total_nodes"] > _EXPECTED_ARTICLE_COUNT

    def test_recital_corpus_matches_recitals_dict(self):
        payload = build_payload()
        assert len(payload["RECITAL"]) == len(RECITALS)


class TestRushdbStrictCitation:
    """Verifies that RushDB payload Articles and Annexes have correct R84-C citation structures."""

    def test_every_article_carries_legal_type(self):
        payload = build_payload()
        for node in payload["ARTICLE"]:
            assert node.get("legal_type") == "Article"

    def test_every_article_carries_strict_citation(self):
        import re
        payload = build_payload()
        for node in payload["ARTICLE"]:
            sc = node.get("strict_citation")
            assert sc is not None
            assert re.match(r"^Article \d+$", sc), f"Malformed strict_citation: {sc!r}"

    def test_every_annex_carries_legal_type(self):
        payload = build_payload()
        for node in payload["ANNEX"]:
            assert node.get("legal_type") == "Annex"

    def test_every_annex_carries_strict_citation(self):
        import re
        payload = build_payload()
        for node in payload["ANNEX"]:
            sc = node.get("strict_citation")
            assert sc is not None
            assert re.match(r"^Annex [IVXLCDM]+$", sc), f"Malformed strict_citation: {sc!r}"

    def test_no_art_dot_prefix(self):
        payload = build_payload()
        for node in payload["ARTICLE"]:
            assert not node["strict_citation"].startswith("Art.")

    def test_no_arabic_annex(self):
        payload = build_payload()
        for node in payload["ANNEX"]:
            sc = node["strict_citation"]
            tail = sc.removeprefix("Annex ").strip()
            assert not tail.isdigit()

    def test_no_article_iii_roman(self):
        payload = build_payload()
        for node in payload["ARTICLE"]:
            sc = node["strict_citation"]
            tail = sc.removeprefix("Article ").strip()
            assert tail.isdigit()

