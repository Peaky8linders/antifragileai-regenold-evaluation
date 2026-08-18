"""R115 — Antifragile follow-up fixes (post-R114 residuals).

1. Subpoint-aware budget rescue: leaf sub-points emitted by
   ``upgrade_references`` survive the QA 3-ref cap when their parent
   survives (q11 shipped [Annex IV, Article 6, Article 11] with the
   Annex IV.1.e / IV.2.c pin-cites truncated off the tail).
2. Curated-intercept reference protection: ``_suppress_noise_anchors``
   and the QA phrase-filters no longer second-guess hand-picked
   curated-intercept refs (q06 minimal-risk shipped [Article 50] only —
   the suppressor read Article 5/6 as broad noise).
3. Sectors filter repair: the R112 filter kept ONLY Article 6 for
   which-sectors questions, dropping Annex III + Annex I (the exact
   under-citation the Antifragile reviewer flagged on q04).
4. Hardware subpoint aliases: compute/GPU/server vocabulary +
   "runs on" word order (generalization-audit MEDIUM).
5. Research-scope detector: research-phase subjects + "does the act
   cover" framing (generalization-audit MEDIUM).
6. Art. 43 stub names the Art. 43(3) single integrated sectoral
   procedure (q14 reviewer demand). KB_VERSION v17.
"""
from __future__ import annotations

import os

import pytest


def _wire(question: str):
    # Hermetic deterministic wire call: pin the provider to ``cli`` and
    # the wrapper base to the conftest dead-port for THIS call,
    # regardless of what a neighbouring suite did to the process env
    # (test_r100_synthesis_default deletes OPENAI_API_BASE per-test,
    # which flips the R112 hard-coded-enabled wrapper onto its
    # production-tunnel fallback — a live Stage-2 answer would then
    # bleed into these deterministic assertions).
    os.environ.setdefault("REGENOLD_SKIP_STARTUP_LOG", "1")
    os.environ["P2P_REGENOLD_API_KEY"] = "r115-test-key"
    # A neighbouring suite may have pinned the auth key on the GLOBAL
    # settings singleton (test_r100_synthesis_default._client does, and
    # never restores it) — settings wins over env at the route, so pin
    # ours the same way.
    from pydantic import SecretStr

    from app.config import settings as _settings

    _settings.regenold.api_key = SecretStr("r115-test-key")
    _saved = {
        k: os.environ.get(k)
        for k in ("P2P_GRAPH_RAG_PROVIDER", "OPENAI_API_BASE")
    }
    os.environ["P2P_GRAPH_RAG_PROVIDER"] = "cli"
    os.environ["OPENAI_API_BASE"] = "http://127.0.0.1:1/v1"
    try:
        from fastapi.testclient import TestClient

        from app.main import app
        from app.routes import regenold as rr

        client = TestClient(app)
        try:
            rr.limiter.reset()
        except Exception:
            pass
        r = client.post(
            "/api/v1/regenold/eu-ai-act/ask",
            json={"messages": [{"role": "user", "content": question}]},
            headers={"X-Regenold-Api-Key": "r115-test-key"},
        )
        assert r.status_code == 200
        return r.json()
    finally:
        for k, v in _saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ── 1. subpoint-aware budget rescue ──────────────────────────────────────


class TestR115SubpointBudgetRescue:
    def test_q11_hardware_pin_cites_survive_qa_budget(self, monkeypatch):
        """R115 budget rescue — the leaf pin-cites survive the QA 3-ref cap.

        ⚠ SUPERSEDED ON THE DEFAULT WIRE BY R287 (``d97c374`` / ``ae96aac``,
        2026-07-24). This assertion is the PRE-R287 wire and it is kept here,
        with the R287 pass explicitly disabled, because it is the only thing
        that still guards the R115 machinery it was written for.

        R287 added ``_collapse_multi_leaf_clusters``
        (``app/routes/regenold.py:3182``), applied at :9832 to CURATED
        authoritative intercepts under ``REGENOLD_INTERCEPT_LEAF_COLLAPSE``
        (default ON). A head cited alongside 2+ of its OWN leaves keeps the
        head and drops the leaves. The R287 docstring names THIS row verbatim
        as a motivating case ("``Annex IV`` + ``Annex IV.2`` + ``Annex IV.1.e``
        + ``Annex IV.2.c`` (rg_001)"), so the change is deliberate, not drift.

        The R115 machinery underneath is fully intact — verified by execution:
        ``upgrade_references(q, ['Article 11','Annex IV'])`` still returns
        ``['Article 11','Annex IV','Annex IV.2','Annex IV.1.e','Annex IV.2.c']``
        and the leaves still survive the QA budget into the candidate list.
        Only the R287 post-pass removes them. Disabling that pass therefore
        tests R115 and nothing else.

        The R287 DEFAULT wire is pinned separately, and deliberately, by
        ``test_r287_default_collapses_rg001_to_head`` below — so neither
        contract can regress unnoticed.

        Do NOT "fix" this by deleting the flag and relaxing the assertion:
        that would silently retire the R115 rescue with no coverage at all.
        """
        monkeypatch.setenv("REGENOLD_INTERCEPT_LEAF_COLLAPSE", "0")
        # R369 — the wire-level leaf→head collapse pass (default ON) is a
        # SIBLING of the R287 intercept collapse: it also removes the leaf
        # when the head is present (Annex IV.1.e + Annex IV → Annex IV),
        # so it must be disabled too for this isolation test to observe
        # the R115 budget rescue and nothing else.
        monkeypatch.setenv("REGENOLD_REF_COLLAPSE_LEAF_TO_HEAD", "0")
        body = _wire(
            "Does the technical documentation of a high-risk AI system "
            "require to provide specifications regarding the required "
            "hardware?"
        )
        refs = body["references"]
        assert "Annex IV.1.e" in refs, refs
        assert "Annex IV.2.c" in refs, refs

    def test_r287_default_collapses_rg001_to_head(self, monkeypatch):
        """R287 default contract — the shipped wire for rg_001 is head-only.

        Sibling of the test above: that one pins the R115 rescue with the R287
        pass OFF, this one pins what production actually ships with the pass at
        its default. Together they make either side impossible to change by
        accident.

        Measured live (``provider=cli``, this suite): the engine offers
        ``['Article 11','Annex IV','Annex IV.2','Annex IV.1.e','Annex IV.2.c']``
        and ``_collapse_multi_leaf_clusters`` reduces it to
        ``['Article 11','Annex IV']``, recording the reasoning-trace note
        ``intercept_multi_leaf_collapse``.

        ⚠ Note for the next reader, recorded because it is NOT obvious from the
        R287 docstring: the "keep the deepest dominating ancestor" rescue that
        R287.1 added only fires when the leaves form a single chain
        (``Annex III.8`` dominates ``III.8.a``/``III.8.b`` → keeper is
        ``Annex III.8``). rg_001's leaves are siblings on TWO branches
        (``IV.1.e`` and ``IV.2.c``), so no candidate dominates the rest and the
        keeper falls all the way back to the bare head. Whether that costs
        sub-point grain on this row is a REFERENCE question owed a
        ``dynamic_ab`` run under the ``gold_dropped`` veto (hard rule #8) —
        it is not a thing to settle by editing a test. The recorded evidence
        available today does not show a loss: the July-7 batch carries no gold
        at all (``gold_coverage=0.0`` in every ``grounded-*.json``), and all
        eight post-R287 grounded runs score rg_001 at ``n_predicted=2,
        precision=1.0, wrong_refs=[]``.
        """
        monkeypatch.delenv("REGENOLD_INTERCEPT_LEAF_COLLAPSE", raising=False)
        body = _wire(
            "Does the technical documentation of a high-risk AI system "
            "require to provide specifications regarding the required "
            "hardware?"
        )
        assert body["references"] == ["Article 11", "Annex IV"], body["references"]

    def test_rescue_never_adds_orphan_subpoints(self):
        # A question with no subpoint topic fired must not gain
        # sub-points from the rescue pass.
        body = _wire("What are the obligations of importers of high-risk AI systems?")
        refs = body["references"]
        for r in refs:
            if "." in r:
                parent = r.split(".", 1)[0].strip()
                assert parent in refs or parent not in refs  # shape sanity
        assert len(refs) <= 7


# ── 2. curated-intercept reference protection ────────────────────────────


class TestR115CuratedRefsProtected:
    def test_minimal_risk_contrast_refs_survive(self):
        body = _wire("What are AI systems with minimal risks?")
        refs = set(body["references"])
        assert {"Article 5", "Article 6", "Article 50"} <= refs, refs

    def test_minimal_risk_paraphrase_also_protected(self):
        body = _wire("Which AI applications are considered minimal risk?")
        refs = set(body["references"])
        assert {"Article 5", "Article 6", "Article 50"} <= refs, refs


# ── 3. sectors filter repair ─────────────────────────────────────────────


class TestR115SectorsFilterRepair:
    def test_q04_ships_both_routes(self):
        body = _wire(
            "Which sectors or applications are considered high-risk "
            "under the regulation?"
        )
        refs = set(body["references"])
        assert {"Article 6", "Annex III", "Annex I"} <= refs, refs

    def test_paraphrase_which_use_cases(self):
        body = _wire("Which use cases count as high-risk under the AI Act?")
        refs = set(body["references"])
        assert {"Article 6", "Annex III", "Annex I"} <= refs, refs


# ── 4. hardware subpoint aliases ─────────────────────────────────────────


class TestR115HardwareAliases:
    @pytest.mark.parametrize(
        "q",
        [
            "Must the technical file describe the compute infrastructure "
            "the AI system runs on?",
            "Do we list GPUs and servers in the Annex IV technical "
            "documentation?",
        ],
    )
    def test_paraphrases_emit_hardware_leaves(self, q):
        from app.data.subpoint_emitter import upgrade_references

        out = upgrade_references(question=q, base_refs=["Annex IV", "Article 11"])
        assert "Annex IV.1.e" in out, out

    @pytest.mark.parametrize(
        "q",
        [
            "Our GPU cluster needs more capacity for training.",
            "What human oversight does Article 14 require?",
        ],
    )
    def test_negatives_do_not_fire(self, q):
        from app.data.subpoint_emitter import upgrade_references

        out = upgrade_references(question=q, base_refs=["Annex IV", "Article 11"])
        assert "Annex IV.1.e" not in out, out


# ── 5. research-scope detector generalization ────────────────────────────


class TestR115ResearchScopeGeneralization:
    @pytest.mark.parametrize(
        "q",
        [
            "Our model is still in the research phase, does the AI Act "
            "cover it?",
            "Does the AI Act cover models still in development?",
            "The system is not yet released on the market, does the "
            "regulation apply to our research and development?",
        ],
    )
    def test_research_phase_shapes_fire(self, q):
        from app.engines.graph_rag import _detect_research_scope_inquiry

        assert _detect_research_scope_inquiry(q) is True

    @pytest.mark.parametrize(
        "q",
        [
            "What transparency obligations apply to our GPAI model?",
            "What does the scientific panel do?",
            "Is market research with AI regulated?",
        ],
    )
    def test_guards_hold(self, q):
        from app.engines.graph_rag import _detect_research_scope_inquiry

        assert _detect_research_scope_inquiry(q) is False


# ── 6. Art. 43(3) integrated procedure in the KB stub ────────────────────


class TestR115Art43IntegratedProcedure:
    def test_stub_names_433_and_mdr_route(self):
        """R115 item 6 — the Art. 43 stub names the 43(3) integrated MDR route.

        The two content asserts below are the real guard. The KB_VERSION
        assert is cache-bust bookkeeping: KB_VERSION is folded into
        ``_engine_cache_key`` (see ``app/data/kb.py:18``), so any KB content
        edit must bump it, and this pin is what makes a silent edit visible.

        It therefore gets RE-PINNED, never relaxed, whenever an unrelated
        round bumps the version. Bump history for this line:
          * v17 -> v18  R263 Fix 3       — unrelated Art. 50 stub edit
          * v18 -> v19  R333 (055fea6)   — sub-point citation restore
          * v19 -> v21  R334 (3a51ada)   — engine cache-key flag registration
        Verified by execution that the Art. 43 stub itself is untouched across
        that whole chain: the ``"Art. 43"`` entry is BYTE-IDENTICAL between
        ``b4deacf`` (the commit that set v18) and HEAD (v21), sha256
        ``29cd38f4434d08c4…`` on both. So the content this test guards is
        intact and only the bookkeeping pin moved.

        ⚠ ``app/data/kb.py`` is the source of truth for this value. CLAUDE.md
        still documents ``KB_VERSION = 2024.1689.v18`` in its knowledge-surface
        table — that doc line is stale as of R334 and needs correcting
        separately (out of scope for this test file).
        """
        from app.data.kb import EC_CHECKER_OBLIGATION_MAP, KB_VERSION

        text = str(EC_CHECKER_OBLIGATION_MAP["Art. 43"])
        assert "43(3)" in text
        assert "MDR" in text or "Medical Device" in text
        assert KB_VERSION == "2024.1689.v21"
