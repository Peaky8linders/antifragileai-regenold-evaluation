"""R268 (2026-07-03) — cite-anchor the AI-Board intercept impartiality sentence.

Follow-up to the R265 European-AI-Board governance intercept + the R267.3
"every substantive intercept sentence must be cite-anchored" doctrine.

The R265 verdict (``_deterministic_answer`` → ``ai_board_governance``) had four
substantive sentences, but sentence 3 (the impartiality / single-contact-point
point, the operative content of Article 65(4)) was the ONLY one NOT
cite-anchored. Under any config where the soft cap in
``normalise_answer_for_regenold`` fires (it drops the longest NON-cite-anchored
sentence first), that sentence was the preferential drop target — the
R266.1-flagged intermittent q033 governance-detail drop. R268 anchors it to
Article 65(4) (65(4)(b): representatives "are designated as a single contact
point vis-a-vis the Board") and adds ``Art. 65.4`` to the refs — both closing
the drop-target AND surfacing the correct citation the r264 Sonnet-5 judge
dinged (q033 cite=50).

davidath byte-identical by construction: ``_detect_ai_board_governance_inquiry``
fires on 0 of the 476 davidath rows (verified — the governance-detail cue the
davidath "What is the Board?" / standing-sub-group rows lack), so the edited
answer text + refs never reach a scored row.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import settings
from app.engines.graph_rag import (
    _detect_ai_board_governance_inquiry,
    _is_curated_authoritative_intercept,
)
from app.main import app
from app.rate_limit import limiter


Q_BOARD = (
    "Regarding the European Artificial Intelligence Board: (1) Who designates "
    "its members? (2) How long is the term and how many times is it renewable? "
    "(3) must members represent stakeholder interests or act impartially? "
    "(4) what voting threshold adopts the Board's rules of procedure?"
)


@pytest.fixture
def client():
    """TestClient with the test partner key seeded (deterministic wire)."""
    prev = settings.regenold.api_key
    settings.regenold.api_key = SecretStr("test")
    try:
        limiter.reset()
    except Exception:
        pass
    with TestClient(app, headers={"X-Regenold-Api-Key": "test"}) as c:
        yield c
    settings.regenold.api_key = prev


class TestBoard65_4Detector:
    def test_intercept_fires(self):
        assert _detect_ai_board_governance_inquiry(Q_BOARD)

    def test_intercept_is_curated_stage2_skip(self):
        # It must stay a curated authoritative intercept so Stage-2 (Opus)
        # cannot regenerate + re-drop the impartiality sentence.
        assert _is_curated_authoritative_intercept(Q_BOARD)


class TestBoard65_4Wire:
    def test_impartiality_sentence_is_cite_anchored_to_65_4(
        self, client: TestClient
    ) -> None:
        r = client.post(
            "/api/v1/regenold/eu-ai-act/ask",
            json=[{"role": "user", "content": Q_BOARD}],
        )
        assert r.status_code == 200
        body = r.json()
        answer = body.get("answer", "")
        low = answer.lower()
        # The impartiality / single-contact-point sentence now carries its
        # Article 65(4) anchor (the R268 fix) — the substance survives AND
        # is cite-anchored so the soft cap can never single it out.
        assert "65(4)" in low, f"Article 65(4) anchor missing; got: {answer!r}"
        assert "single contact point" in low, (
            f"impartiality/contact-point substance missing; got: {answer!r}"
        )
        # The two-thirds sub-part (R266.1's reported drop) must still ship.
        assert "two-thirds" in low, (
            f"two-thirds voting-threshold sub-part dropped; got: {answer!r}"
        )

    def test_references_carry_article_65_4(
        self, client: TestClient, monkeypatch
    ) -> None:
        """R268 — the 65(4) sub-point reaches the references.

        ⚠ SUPERSEDED ON THE DEFAULT WIRE BY R287 (``d97c374`` / ``ae96aac``,
        2026-07-24). Kept, with the R287 pass explicitly disabled, because it
        is the only coverage of the R268 sub-point EMISSION it was written for.

        R287 added ``_collapse_multi_leaf_clusters``
        (``app/routes/regenold.py:3182``), applied at :9832 to CURATED
        authoritative intercepts under ``REGENOLD_INTERCEPT_LEAF_COLLAPSE``
        (default ON): a head cited alongside 2+ of its own leaves keeps the
        head and drops the leaves. The R287 docstring names THIS row verbatim
        ("``Article 65`` + 65.3/.4/.5/.7 (rg_033)"), and the r286 grounded
        judge's quoted failure_mode for it was "over-cited redundant/
        non-governing provisions (65.4, whole Art. 65)". So the drop is the
        deliberate, measured intent of R287 (110-row sim: 12 redundant refs
        dropped across 4 rows, 0 rows losing a head), not a regression.

        The R268 emission underneath is intact — verified by execution: with
        the R287 pass off the wire still ships 65.3/65.4/65.5/65.7 alongside
        the head. Only the post-pass removes them.

        The R287 DEFAULT wire is pinned separately by
        ``test_r287_default_collapses_board_refs_to_head`` below.

        Note the companion test ``test_impartiality_sentence_is_cite_anchored_
        to_65_4`` needs no flag: R287 touches REFERENCES only, so the ANSWER
        text keeps its "Article 65(4)" anchor either way — which is what R268
        was actually protecting against the soft cap.
        """
        monkeypatch.setenv("REGENOLD_INTERCEPT_LEAF_COLLAPSE", "0")
        r = client.post(
            "/api/v1/regenold/eu-ai-act/ask",
            json=[{"role": "user", "content": Q_BOARD}],
        )
        assert r.status_code == 200
        refs = r.json().get("references", [])
        assert "Article 65.4" in refs, (
            f"Article 65.4 (the impartiality/contact-point basis) missing from "
            f"the wire references; got {refs}"
        )
        # The other governance sub-points must still ship alongside it.
        assert "Article 65.3" in refs and "Article 65.5" in refs, (
            f"Expected 65.3 (term) + 65.5 (two-thirds) alongside 65.4; got {refs}"
        )

    def test_r287_default_collapses_board_refs_to_head(
        self, client: TestClient, monkeypatch
    ) -> None:
        """R287 default contract — the shipped wire for rg_033 is head-only.

        Sibling of the test above: that one pins R268's sub-point emission with
        the R287 pass OFF, this one pins what production actually ships at the
        default, so neither side can move unnoticed.

        Measured live (``provider=cli``, this suite): the engine offers
        ``['Article 65','Article 65.3','Article 65.4','Article 65.5',
        'Article 65.7']`` and ``_collapse_multi_leaf_clusters`` reduces it to
        ``['Article 65']``, recording the reasoning-trace note
        ``intercept_multi_leaf_collapse``.

        ⚠ Recorded because it is not obvious from the R287 docstring: the
        R287.1 "keep the deepest dominating ancestor" rescue only fires when
        the leaves form a single chain. Here the four leaves are siblings, so
        no candidate dominates the rest and the keeper falls back to the bare
        head. Changing that is a REFERENCE change owed a ``dynamic_ab`` run
        under the ``gold_dropped`` veto (hard rule #8) — not a test edit.
        """
        monkeypatch.delenv("REGENOLD_INTERCEPT_LEAF_COLLAPSE", raising=False)
        r = client.post(
            "/api/v1/regenold/eu-ai-act/ask",
            json=[{"role": "user", "content": Q_BOARD}],
        )
        assert r.status_code == 200
        assert r.json().get("references", []) == ["Article 65"], r.json().get(
            "references", []
        )
