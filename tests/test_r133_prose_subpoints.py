"""R133 — surface prose-named sub-points into the wire references.

A live Stage-2 (Sonnet) answer to the doctor-patient transcription
question said "Under Article 6(1), a use is high-risk … not high-risk
under Article 6(2)" but the wire ``references`` carried only the bare
parent ``Article 6``. The user flagged the mismatch: the prose names a
sub-point that the citation list does not surface.

``_surface_prose_subpoints(answer, references)`` closes that gap: it
scans the FINAL answer for parenthetical sub-point citations
(``Article 6(1)`` / ``Article 5(1)(a)`` / ``Annex IV(2)``) and, when the
bare parent is already cited but the sub-point form is not, inserts the
sub-point (``Article 6.1``) immediately after the parent. The parent is
kept (the prose cites it standalone too); a parent the answer never
cites is never fabricated. Bounded, deduped, fail-soft.

⚠ "The parent is kept" is a statement about THIS HELPER, not about the
wire. Downstream of it the route runs the **R276-D1 reference-granularity
pass** (``_apply_ref_granularity``, ``REGENOLD_REF_GRANULARITY``, default
``auto``), which emits ONE granularity level per parent+leaf cluster — and
**R333** made the ANSWER BODY a leaf-protecting signal, so on exactly the
answer R133 was written for the pass keeps ``Article 6.1``/``6.2`` and
drops the bare ``Article 6``. See the route-level tests at the bottom of
this file: the default-``auto`` wire and the ``both`` rollback wire are
asserted separately, because parent retention is only observable in
``both``.
"""

from __future__ import annotations

from app.routes.regenold import _surface_prose_subpoints


class TestSurfaceProseSubpoints:
    def test_reported_case_article_6_1_added(self) -> None:
        answer = (
            "The system can attract high-risk status only through Article 6. "
            "Under Article 6(1), a use is high-risk where the AI system is a "
            "safety component of an Annex I product."
        )
        refs = ["Annex III", "Article 6", "Article 5", "Annex I"]
        out = _surface_prose_subpoints(answer, refs)
        assert "Article 6.1" in out
        # parent kept, sub-point right after it
        assert out.index("Article 6.1") == out.index("Article 6") + 1
        # nothing else dropped
        for r in refs:
            assert r in out

    def test_two_subpoints_both_added_after_parent(self) -> None:
        answer = (
            "Under Article 6(1) the system is high-risk as a safety component; "
            "a standalone tool is not high-risk under Article 6(2)."
        )
        refs = ["Article 6", "Article 50"]
        out = _surface_prose_subpoints(answer, refs)
        assert out[:3] == ["Article 6", "Article 6.1", "Article 6.2"]
        assert "Article 50" in out

    def test_parent_not_cited_does_not_fabricate(self) -> None:
        # Prose names Article 6(1) but Article 6 is NOT in references —
        # do not invent a citation the retrieval never surfaced.
        answer = "Under Article 6(1) the system is high-risk."
        refs = ["Annex III", "Article 5"]
        out = _surface_prose_subpoints(answer, refs)
        assert out == refs
        assert "Article 6.1" not in out

    def test_subpoint_already_present_no_duplicate(self) -> None:
        answer = "Under Article 6(1) the system is high-risk."
        refs = ["Article 6", "Article 6.1"]
        out = _surface_prose_subpoints(answer, refs)
        assert out.count("Article 6.1") == 1

    def test_lettered_subpoint(self) -> None:
        answer = "Article 5(1)(a) prohibits subliminal manipulation."
        refs = ["Article 5"]
        out = _surface_prose_subpoints(answer, refs)
        assert "Article 5.1.a" in out

    def test_annex_subpoint(self) -> None:
        answer = "The technical documentation contents are set out in Annex IV(2)."
        refs = ["Article 11", "Annex IV"]
        out = _surface_prose_subpoints(answer, refs)
        assert "Annex IV.2" in out
        assert out.index("Annex IV.2") == out.index("Annex IV") + 1

    def test_no_subpoint_in_prose_is_noop(self) -> None:
        answer = "Article 6 classifies high-risk systems. Article 50 covers transparency."
        refs = ["Article 6", "Article 50"]
        assert _surface_prose_subpoints(answer, refs) == refs

    def test_empty_inputs_failsoft(self) -> None:
        assert _surface_prose_subpoints("", ["Article 6"]) == ["Article 6"]
        assert _surface_prose_subpoints("Article 6(1) applies.", []) == []

    def test_idempotent(self) -> None:
        answer = "Under Article 6(1) the system is high-risk."
        refs = ["Article 6", "Article 5"]
        once = _surface_prose_subpoints(answer, refs)
        twice = _surface_prose_subpoints(answer, once)
        assert once == twice

    def test_bounded_additions(self) -> None:
        # Many distinct sub-points named — additions are capped.
        answer = (
            "Article 6(1) and Article 6(2) and Article 5(1)(a) and "
            "Article 5(1)(b) and Article 5(1)(c)."
        )
        refs = ["Article 6", "Article 5"]
        out = _surface_prose_subpoints(answer, refs)
        added = [r for r in out if r not in refs]
        assert len(added) <= 3


# ── Route end-to-end (Stage-2-landed gate) ───────────────────────────────


_STUB_ANSWER = (
    "Article 5 does not prohibit an AI system that transcribes "
    "doctor-patient conversations. Under Article 6(1), a use is high-risk "
    "where the AI system is a safety component of a product covered by "
    "Annex I; a standalone transcription tool is not high-risk under "
    "Article 6(2). Article 50 transparency obligations apply where the "
    "system interacts with natural persons."
)


_ROUTE_QUESTION = (
    "Is an AI that transcribes doctor-patient conversations prohibited? "
    "Or is it high-risk as per the use cases of Annex III of the AI Act?"
)


def _wire_refs(monkeypatch) -> list[str]:
    """POST the real route with Stage-2 stubbed to ``_STUB_ANSWER`` and
    return the wire ``references``.

    Deliberately goes through the PRODUCTION producer (the FastAPI route),
    not a hand-built reference list: the R276-D1 granularity pass reads the
    live question AND the answer body, so a fixture that fabricated the
    pre-granularity list would be testing a shape production never emits.
    Only the LLM call itself is mocked — no network, no real Stage-2.
    """
    from unittest.mock import patch

    from fastapi.testclient import TestClient
    from pydantic import SecretStr

    from app.config import settings
    from app.main import app

    settings.regenold.api_key = SecretStr("regenold-test-key")
    # Make Stage-2 reachable regardless of the ambient provider env
    # (R127 made the wrapper gate cli-sensitive; R131.1 pattern).
    monkeypatch.delenv("P2P_GRAPH_RAG_PROVIDER", raising=False)
    monkeypatch.setenv("P2P_GRAPH_RAG_ENABLE_STAGE2", "1")
    monkeypatch.setenv("REGENOLD_ANSWER_ROUTER", "1")
    monkeypatch.setenv("REGENOLD_SYNTHESIS_DEFAULT", "1")
    monkeypatch.setenv("REGENOLD_STAGE2_MIN_CONFIDENCE", "0")
    monkeypatch.setenv("REGENOLD_DYNAMIC_GROUNDING", "1")
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "0")
    monkeypatch.setenv("REGENOLD_FUSION_STAGE2", "0")
    monkeypatch.setenv("REGENOLD_SURFACE_PROSE_SUBPOINTS", "1")

    with (
        patch(
            "app.llm.openai_wrapper_provider.is_openai_wrapper_enabled",
            return_value=True,
        ),
        patch(
            "app.engines.graph_rag._stage2_provider_enabled",
            return_value=True,
        ),
        patch(
            "app.engines.graph_rag._openai_wrapper_complete_for_graph_rag",
            return_value=_STUB_ANSWER,
        ),
    ):
        client = TestClient(app)
        r = client.post(
            "/api/v1/regenold/eu-ai-act/ask",
            headers={"X-Regenold-Api-Key": "regenold-test-key"},
            json={"messages": [{"role": "user", "content": _ROUTE_QUESTION}]},
        )
    assert r.status_code == 200
    return r.json()["references"]


def test_route_surfaces_article_6_1_when_stage2_lands(monkeypatch) -> None:
    """End-to-end, DEFAULT config: a Stage-2-landed answer naming
    Article 6(1)/(2) makes the wire references carry Article 6.1 — the
    R133 defect this file exists for.

    ⚠ SUPERSEDED EXPECTATION — do not "fix" this back. This test used to
    also assert ``"Article 6" in refs`` (parent retention, R87-C
    ``_reemit_parents_for_subpoints``). **R276-D1** replaced that wire:
    ``_apply_ref_granularity`` (``REGENOLD_REF_GRANULARITY``, default
    ``auto``) emits ONE granularity level per parent+leaf cluster, and
    **R333** made the ANSWER BODY a leaf-protecting signal — so because
    ``_STUB_ANSWER`` names "Article 6(1)"/"Article 6(2)", ``auto`` keeps
    the LEAVES and drops the bare head. That is the measured ref-precision
    arm (medtech-v124 exact-string F1 both .646 → auto .693), and it is
    recall-safe at head grain: ``article_heads`` of the shipped list still
    contains ``Article 6``, so hard rule #8 sees zero gold dropped.
    Parent retention is now asserted in its own ``both``-mode sibling test
    below. Changing the ``auto`` default is a reference change and owes a
    ``dynamic_ab`` run with ``gold_dropped`` — not a test edit.
    """
    refs = _wire_refs(monkeypatch)
    # The reported defect: prose says "Article 6(1)" — wire must surface it.
    assert "Article 6.1" in refs, refs
    # Pin the R276-D1 ``auto`` contract explicitly rather than leaving the
    # head's absence as an unasserted side effect: one level per cluster,
    # and here the leaves are the level that survives.
    assert "Article 6.2" in refs, refs
    assert "Article 6" not in refs, refs
    # Head-level recall is invariant — the leaf carries the head.
    from evals.bench.metrics import article_heads

    assert "Article 6" in article_heads(refs), refs


def test_route_keeps_bare_parent_under_granularity_both(monkeypatch) -> None:
    """R87-C parent retention, observable ONLY in the documented pre-R276
    rollback arm ``REGENOLD_REF_GRANULARITY=both``.

    ``_ref_granularity_mode``'s own docstring states the contract:
    "Rollback: ``REGENOLD_REF_GRANULARITY=both`` restores the pre-R276 wire
    exactly." This test pins that rollback — the parent AND both leaves
    ship together — so the rollback path stays live and a future change to
    ``_apply_ref_granularity`` cannot silently break the off-switch.
    """
    monkeypatch.setenv("REGENOLD_REF_GRANULARITY", "both")
    refs = _wire_refs(monkeypatch)
    assert "Article 6" in refs, refs
    assert "Article 6.1" in refs, refs
    assert "Article 6.2" in refs, refs
    # The whole point of ``both``: parent and leaf coexist.
    assert refs.index("Article 6") < refs.index("Article 6.1"), refs
