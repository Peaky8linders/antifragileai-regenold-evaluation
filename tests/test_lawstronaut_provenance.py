"""Regression tests for the pinned Lawstronaut legal provenance.

These pin the invariant the first-cut integration violated: the provenance we
stamp on the graph, the ontology and (optionally) the prompt must describe the
text this repo actually ships — the PRE-Digital-Omnibus original.

The superseded ``tests/test_lawstronaut_client.py`` asserted the runtime
client's hardcoded fallback constant against itself, so it was green no matter
what the API said AND it pinned the wrong (post-Omnibus) CELEX as correct.
These tests assert against the KB text instead.
"""
from __future__ import annotations

import json
import pathlib
import re

import pytest

from app.data.lawstronaut_provenance import (
    CORPUS_VALIDATION,
    OFFICIAL_CELEX,
    OFFICIAL_EFFECTIVE_DATE,
    OFFICIAL_ELI,
    OFFICIAL_GUIDELINES,
    OFFICIAL_LEGAL_LINK,
    OMNIBUS_AMENDING_ACT,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Phrases that appear ONLY in the post-Digital-Omnibus consolidation
#: (Regulation (EU) 2026/1744). "2 August 2028" is deliberately NOT here: it
#: occurs in the ORIGINAL Article 112 review clauses too, so it does not
#: discriminate between the versions.
OMNIBUS_ONLY_MARKERS = ("2 December 2027", "small mid-cap", "32026R1744")


class TestPinnedProvenanceIsPreOmnibus:
    def test_celex_is_the_original_act_not_a_consolidation(self) -> None:
        # A CELEX starting "3" is an as-adopted act; "0" prefixes a
        # consolidated version. Our corpus is the as-adopted original.
        assert OFFICIAL_CELEX == "32024R1689"
        assert not OFFICIAL_CELEX.startswith("0"), (
            "a consolidated CELEX would assert amendments our text lacks"
        )

    def test_eli_and_link_point_at_the_same_act(self) -> None:
        assert OFFICIAL_ELI.endswith("/oj")
        assert OFFICIAL_CELEX in OFFICIAL_LEGAL_LINK

    def test_effective_date_is_the_original(self) -> None:
        assert OFFICIAL_EFFECTIVE_DATE == "2024-08-01"

    def test_omnibus_recorded_but_not_incorporated(self) -> None:
        assert OMNIBUS_AMENDING_ACT["celex"] == "32026R1744"
        assert OMNIBUS_AMENDING_ACT["incorporated_in_corpus"] is False


class TestProvenanceMatchesTheShippedText:
    """The load-bearing check: does the KB text match the pinned version?"""

    def test_kb_text_carries_no_omnibus_amendments(self) -> None:
        from app.data.official_eu_ai_act import OFFICIAL_ARTICLE_TEXT

        blob = " ".join(OFFICIAL_ARTICLE_TEXT.values())
        blob = re.sub(r"\s+", " ", blob).lower()
        present = [m for m in OMNIBUS_ONLY_MARKERS if m.lower() in blob]
        assert not present, (
            f"pinned CELEX {OFFICIAL_CELEX} is pre-Omnibus but the KB text "
            f"carries Omnibus markers {present} — provenance and text disagree"
        )

    def test_article_113_states_the_original_application_dates(self) -> None:
        from app.data.provision_text import get_provision_text

        text = re.sub(r"\s+", " ", get_provision_text("Art. 113") or "")
        assert "2 August 2026" in text
        assert "2 August 2027" in text
        assert "2 December 2027" not in text, "that is the Omnibus deferral"

    def test_recorded_validation_shows_the_corpus_matched_the_live_source(self) -> None:
        assert CORPUS_VALIDATION["provisions_compared"] == 126
        assert CORPUS_VALIDATION["missing_in_live"] == []
        assert CORPUS_VALIDATION["missing_in_repo"] == []
        assert float(CORPUS_VALIDATION["median_similarity"]) >= 0.99
        assert float(CORPUS_VALIDATION["mean_similarity"]) >= 0.95


class TestGuidelineRegistry:
    def test_guidelines_are_not_stamped_with_the_regulations_identity(self) -> None:
        # A Commission guideline is soft law interpreting the act. Giving it
        # the act's CELEX as its OWN id conflates the two.
        for g in OFFICIAL_GUIDELINES:
            assert "celex_id" not in g, f"{g['id']} must not claim a CELEX of its own"
            assert g["doc_id"] and g["title"] and g["issuing_authority"]

    def test_every_interpreted_reference_exists(self) -> None:
        from app.data.article_existence import ARTICLE_EXISTENCE

        for g in OFFICIAL_GUIDELINES:
            for ref in g["interprets"]:
                assert ref in ARTICLE_EXISTENCE, f"{g['id']} -> unknown {ref}"


class TestPinSidecar:
    def test_pin_agrees_with_the_generated_module(self) -> None:
        pin_path = REPO_ROOT / "app" / "data" / "_lawstronaut_pin.json"
        pin = json.loads(pin_path.read_text(encoding="utf-8"))
        assert pin["celex"] == OFFICIAL_CELEX
        assert pin["eli"] == OFFICIAL_ELI
        assert pin["pre_omnibus"] is True
        assert pin["omnibus_amending_act"] == OMNIBUS_AMENDING_ACT["celex"]


class TestProvenanceIsNotInThePromptByDefault:
    def test_kg_context_provenance_gate_defaults_off(self, monkeypatch) -> None:
        from app.engines import kg_context

        monkeypatch.delenv("REGENOLD_PROVENANCE_IN_PROMPT", raising=False)
        assert kg_context._provenance_in_prompt_enabled() is False

    def test_empty_refs_still_yield_no_context(self, monkeypatch) -> None:
        """The zero-retrieval sentinel must survive.

        The first cut appended provenance BEFORE the ``if parts`` guard, so
        ``render_kg_context([])`` became non-empty and the "did the graph
        contribute?" signal was destroyed.
        """
        from app.engines import kg_context

        monkeypatch.setenv("REGENOLD_PROVENANCE_IN_PROMPT", "1")
        assert kg_context.render_kg_context([]) == []

    @pytest.mark.parametrize("flag", ["1", "0"])
    def test_gate_is_read_fresh_per_call(self, monkeypatch, flag: str) -> None:
        from app.engines import kg_context

        monkeypatch.setenv("REGENOLD_PROVENANCE_IN_PROMPT", flag)
        assert kg_context._provenance_in_prompt_enabled() is (flag == "1")


class TestTurboquantStalenessGuard:
    """The precomputed dense asset keys documents by BM25 POSITION.

    Positions are not stable ids: a KB edit that adds, removes or reorders a
    document silently repoints every stored vector at a different article, and
    dense retrieval then returns confidently wrong refs with no error. The
    guard must reject a stale map and fall through to the on-the-fly build.
    """

    def test_committed_asset_matches_the_live_corpus(self) -> None:
        import numpy as np

        from app.data.kb_search import _build_index

        assets = REPO_ROOT / "app" / "engines" / "_assets" / "turboquant_precomputed.npz"
        data = np.load(assets, allow_pickle=True)
        stored = list(data["bm25_idx_map"].astype(int))

        bm25 = _build_index()
        live = [i for i in range(len(bm25.docs)) if bm25.sources[i] != "definition"]

        assert stored == live, (
            "turboquant_precomputed.npz is stale — re-run "
            "scripts/build_turboquant_precomputed.py"
        )
        assert data["doc_vecs_dense"].shape[0] == len(stored)

    def test_a_stale_corpus_makes_the_index_reject_the_precomputed_asset(
        self, monkeypatch, caplog
    ) -> None:
        """Actually drive the guard: pretend the KB gained one document.

        This must exercise the load path, not restate the predicate — a test
        written against the code rather than the requirement passes while
        production is broken.
        """
        import logging

        import app.data.kb_search as kb_search
        from app.engines import turboquant_index as tq

        real = kb_search._build_index()

        class _Shifted:
            """Live corpus with one extra non-definition doc at the front.

            Every stored position is now off by one — the silent-corruption
            scenario the guard exists for.
            """

            docs = [["synthetic"], *real.docs]
            sources = ["kb", *real.sources]

        monkeypatch.setattr(kb_search, "_build_index", lambda: _Shifted())

        index = tq._DenseIndex()
        with caplog.at_level(logging.WARNING):
            index._setup()

        # The precomputed asset must NOT be the source of truth here.
        assert any(
            "stale" in rec.message.lower()
            or "failed to load precomputed" in rec.message.lower()
            for rec in caplog.records
        ), f"guard did not reject the stale asset; logs={[r.message for r in caplog.records]}"

    def test_guard_message_names_the_rebuild_command(self) -> None:
        source = (
            REPO_ROOT / "app" / "engines" / "turboquant_index.py"
        ).read_text(encoding="utf-8")
        assert "build_turboquant_precomputed.py" in source, (
            "a staleness error must tell the operator how to fix it"
        )
