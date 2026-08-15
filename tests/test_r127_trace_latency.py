"""R127 — live-trace-driven latency + observability + routing fixes.

Pins the nine R127 changes that close the R125 live-reasoning-trace findings:

* #1 fusion-panel gate tightening (``is_fusion_worthy``) — multi-turn +
  merely-multi-phrase questions skip the 2-call MoA panel.
* #2 multi-turn never fuses (subsumed by #1's multi-turn guard).
* #3 sufficient-context single-clause over-fire — the deterministic decomposer
  gates the LLM planner so a one-clause question never decomposes.
* #4 reword the misleading "extended thinking is disabled" Stage-2 message.
* #5 populate the fusion-path Stage-2 observability ("thinking") field.
* #6 ``_compute_confidence`` differentiates (a reachable 0.85 richness tier).
* #7 role-definitional questions surface the Art. 3 definition, not obligations.
* #9 med_05 scenario-to-QA demote + gt_07 guiding-principles keywords.

Every change is davidath byte-identical (verified by the bench A/B in the
PR); these unit tests pin the behaviour so a future revert is loud.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.engines import fusion
from app.engines.question_complexity import is_complex_question, is_fusion_worthy
from app.llm import openai_wrapper_provider as owp
from app.llm.openai_wrapper_provider import OpenAIWrapperResponse


# ── #1 / #2 — is_fusion_worthy ─────────────────────────────────────────────


class TestR127FusionWorthy:
    HARD_SINGLE_TURN = [
        "Does the one-third fine-tune rule make us a new provider?",          # gpai
        "Is a system that is both provider and deployer treated differently?",  # role
        "Is emotion recognition in the workplace always prohibited?",          # borderline
        "Does our GDPR DPIA satisfy the Article 27 FRIA or do both apply?",     # conflict
        "How does the MDR interact with Article 6 of the AI Act?",             # cross-framework
    ]

    @pytest.mark.parametrize("q", HARD_SINGLE_TURN)
    def test_hard_single_turn_fires_panel(self, monkeypatch, q):
        monkeypatch.delenv("REGENOLD_FUSION_WORTHY_STRICT", raising=False)
        assert is_fusion_worthy(q, history_turn_count=1) is True

    def test_multi_turn_never_fuses_via_marker(self, monkeypatch):
        # Even with a hard category in the live turn, a flattened multi-turn
        # prompt skips the panel (timeout safety, R125 trace #2).
        monkeypatch.delenv("REGENOLD_FUSION_WORTHY_STRICT", raising=False)
        q = (
            "Conversation so far:\nuser: We use a GPAI model.\n"
            "Latest question:\nDoes the one-third fine-tune rule apply?"
        )
        assert is_fusion_worthy(q, history_turn_count=3) is False

    def test_multi_turn_never_fuses_via_depth(self, monkeypatch):
        monkeypatch.delenv("REGENOLD_FUSION_WORTHY_STRICT", raising=False)
        assert is_fusion_worthy("Does systemic risk apply?", history_turn_count=2) is False

    def test_merely_multi_phrase_skips_panel(self, monkeypatch):
        # Two substantive sentences (is_complex_question True via _is_multi_phrase)
        # but no hard category → not fusion-worthy (single-Opus path instead).
        monkeypatch.delenv("REGENOLD_FUSION_WORTHY_STRICT", raising=False)
        q = "Article 13 applies to high-risk systems. It requires detailed logging and record-keeping."
        assert is_complex_question(q) is True
        assert is_fusion_worthy(q) is False

    def test_simple_definitional_skips_panel(self, monkeypatch):
        monkeypatch.delenv("REGENOLD_FUSION_WORTHY_STRICT", raising=False)
        assert is_fusion_worthy("What is a deployer?") is False

    def test_empty_input(self):
        assert is_fusion_worthy("") is False
        assert is_fusion_worthy(None) is False  # type: ignore[arg-type]

    def test_strict_off_restores_r124(self, monkeypatch):
        # =0 → fire the panel on every complex question (R124).
        monkeypatch.setenv("REGENOLD_FUSION_WORTHY_STRICT", "0")
        q = "Article 13 applies to high-risk systems. It requires detailed logging and record-keeping."
        assert is_complex_question(q) is True
        assert is_fusion_worthy(q) is True  # multi-phrase complex now fuses

    @pytest.mark.parametrize("val", ["1", "true", "on", "yes"])
    def test_strict_on_values(self, monkeypatch, val):
        monkeypatch.setenv("REGENOLD_FUSION_WORTHY_STRICT", val)
        # multi-phrase complex still skips the panel when strict
        q = "Article 13 applies to high-risk systems. It requires detailed logging and record-keeping."
        assert is_fusion_worthy(q) is False


# ── #3 — sufficient-context single-clause over-fire ────────────────────────


class TestR127SufficientContextGate:
    SINGLE_CLAUSE = [
        "Is real-time RBI in public spaces prohibited?",  # the R125 trace #3 question
        "What is a deployer?",
        "Are emotion recognition systems prohibited?",
        "Is a credit-scoring AI high-risk under the Act?",
    ]

    @pytest.mark.parametrize("q", SINGLE_CLAUSE)
    def test_single_clause_never_decomposes_even_if_llm_would(self, monkeypatch, q):
        import app.engines.sufficient_context as sc

        # Force the LLM planner to (wrongly) over-split; the deterministic gate
        # must still veto the hop before the LLM is consulted.
        monkeypatch.setattr(
            "app.engines.frames_planner.decompose_question_llm",
            lambda question: [question, "spurious second sub-query"],
        )
        v = sc.assess_sufficiency(q, covered_articles={"Art. 5"})
        assert v.sufficient is True
        assert v.reason == "sufficient"
        assert v.sub_queries == ()

    def test_genuine_multipart_still_decomposes(self, monkeypatch):
        import app.engines.sufficient_context as sc

        monkeypatch.setattr(
            "app.engines.frames_planner.decompose_question_llm",
            lambda question: ["importer obligations", "distributor obligations"],
        )
        q = "What are the obligations of importers and what must distributors do?"
        v = sc.assess_sufficiency(q, covered_articles={"Art. 23"})
        assert v.sufficient is False
        assert v.reason == "multi_phrase_decompose"
        assert v.sub_queries == ("importer obligations", "distributor obligations")

    def test_multipart_falls_back_to_deterministic_when_llm_collapses(self, monkeypatch):
        import app.engines.sufficient_context as sc

        monkeypatch.setattr(
            "app.engines.frames_planner.decompose_question_llm",
            lambda question: ["only one clause"],
        )
        q = "What are the obligations of importers and what must distributors do?"
        v = sc.assess_sufficiency(q, covered_articles={"Art. 23"})
        assert v.sufficient is False
        assert v.reason == "multi_phrase_decompose"
        assert len(v.sub_queries) == 2  # the deterministic clauses

    def test_explicit_ref_gap_unaffected(self, monkeypatch):
        import app.engines.sufficient_context as sc

        # A named-but-missing ref is a gap on a single clause — step (1) is
        # independent of the step (2) gate change.
        monkeypatch.setattr(
            "app.engines.frames_planner.decompose_question_llm",
            lambda question: [question],
        )
        v = sc.assess_sufficiency("Tell me about Annex IV.", covered_articles=set())
        assert v.sufficient is False
        assert v.reason == "uncovered_explicit_refs"

    def test_single_clause_skips_llm_call(self, monkeypatch):
        """The early return on a single clause must NOT invoke the LLM planner
        (the latency win)."""
        import app.engines.sufficient_context as sc

        calls = {"n": 0}

        def _spy(question):
            calls["n"] += 1
            return [question, "x"]

        monkeypatch.setattr("app.engines.frames_planner.decompose_question_llm", _spy)
        sc.assess_sufficiency("Is real-time RBI prohibited?", covered_articles={"Art. 5"})
        assert calls["n"] == 0


# ── #4 — Stage-2 thinking message reword ───────────────────────────────────


class TestR127ThinkingMessage:
    def test_old_misleading_string_removed_from_source(self):
        # R290 — the engine source moved to _graph_rag_impl.py when
        # app/engines/graph_rag became a package; the old path is now a
        # directory, so this guard raised FileNotFoundError.
        gr = Path("app/engines/_graph_rag_impl.py").read_text(encoding="utf-8")
        assert "extended thinking is disabled by configuration" not in gr
        assert "Single-pass synthesis (no extended thinking on this call)." in gr


# ── #6 — _compute_confidence tiers ─────────────────────────────────────────


class TestR127ComputeConfidence:
    def _ctx(self, **kw):
        from app.engines.graph_rag import GraphContext

        c = GraphContext()
        for k, v in kw.items():
            setattr(c, k, v)
        return c

    def test_degraded(self):
        from app.engines.graph_rag import _compute_confidence

        assert _compute_confidence(self._ctx(degraded=True)) == 0.2

    def test_zero_retrieval(self):
        from app.engines.graph_rag import _compute_confidence

        assert _compute_confidence(self._ctx()) == 0.3

    def test_sparse(self):
        from app.engines.graph_rag import _compute_confidence

        assert _compute_confidence(self._ctx(nodes_traversed=3)) == 0.5

    def test_moderate(self):
        from app.engines.graph_rag import _compute_confidence

        assert _compute_confidence(self._ctx(nodes_traversed=7)) == 0.7

    def test_rich_obligations_reaches_85(self):
        from app.engines.graph_rag import _compute_confidence

        c = self._ctx(nodes_traversed=7, obligations=[{"id": f"o{i}"} for i in range(3)])
        assert _compute_confidence(c) == 0.85


# ── #7 — role-definitional routing ─────────────────────────────────────────


class TestR127RoleDefinitional:
    POSITIVE = [
        "What is a deployer?",
        "What is an importer?",
        "Who is a distributor?",
        "Who is considered a 'provider' of an AI system?",
        "Definition of an operator",
        "Who is an authorised representative?",
    ]
    NEGATIVE = [
        "What is the maximum fine for a provider that supplies incorrect information?",
        "What is the maximum period for which a provider must keep technical documentation?",
        "What are the obligations of deployers of high-risk AI systems?",
        "We are a deployer of an Annex III hiring tool, what are our duties?",
    ]

    @pytest.mark.parametrize("q", POSITIVE)
    def test_positive(self, q):
        from app.engines.entity_extractor import role_definitional_term

        assert role_definitional_term(q) is not None

    @pytest.mark.parametrize("q", NEGATIVE)
    def test_negative(self, q):
        from app.engines.entity_extractor import role_definitional_term

        assert role_definitional_term(q) is None

    def test_multiturn_live_section_scanned(self):
        from app.engines.entity_extractor import role_definitional_term

        q = "Conversation so far:\nuser: hi\nLatest question:\nWhat is a deployer?"
        assert role_definitional_term(q) is not None

    @pytest.mark.parametrize("q,role_art", [
        ("What is a deployer?", "Art. 26"),
        ("What is an importer?", "Art. 23"),
        ("Who is considered a provider?", "Art. 16"),
    ])
    def test_engine_anchors_art3_first(self, q, role_art):
        from app.engines.graph_rag import _deterministic_parse

        gq = _deterministic_parse(q)
        assert gq.entities, f"no entities for {q}"
        assert gq.entities[0] == "Art. 3"

    def test_injection_suppressed_for_role_definitional(self):
        from app.engines.entity_extractor import is_qa_shape_with_single_role

        # The R81-N.1 role-Article injection must NOT fire for a definitional
        # role question (else Art. 26 lands ahead of Art. 3 on the wire).
        assert is_qa_shape_with_single_role("What is a deployer?") is False

    def test_obligation_question_still_injects(self):
        from app.engines.entity_extractor import is_qa_shape_with_single_role

        # A genuine single-role obligation QA still fires the injection.
        assert (
            is_qa_shape_with_single_role("What are the obligations of deployers?") is True
        )


# ── #9 — med_05 scenario demote + gt_07 keywords ───────────────────────────


class TestR127ScenarioDemote:
    def test_risk_ask_regex_matches_davidath_template(self):
        from app.routes.regenold import _RISK_CLASSIFICATION_ASK_RE

        davidath = (
            "We are a provider, offering X, intended to do Y. Under the EU AI "
            "Act, what is the risk classification of this system and what are "
            "the key obligations on us as provider?"
        )
        assert _RISK_CLASSIFICATION_ASK_RE.search(davidath) is not None

    def test_med05_has_no_risk_ask(self):
        from app.routes.regenold import _RISK_CLASSIFICATION_ASK_RE

        med05 = (
            "We are developing a generative AI chatbot that will be deployed on "
            "a hospital website to answer general patient queries. What "
            "transparency obligations apply?"
        )
        assert _RISK_CLASSIFICATION_ASK_RE.search(med05) is None

    def test_demote_enabled_default(self, monkeypatch):
        from app.routes.regenold import _scenario_qa_demote_enabled

        monkeypatch.delenv("REGENOLD_SCENARIO_QA_DEMOTE", raising=False)
        assert _scenario_qa_demote_enabled() is True
        monkeypatch.setenv("REGENOLD_SCENARIO_QA_DEMOTE", "0")
        assert _scenario_qa_demote_enabled() is False


class TestR127GuidingPrinciplesKeywords:
    def test_gt07_keywords_in_curated_answer(self):
        from app.engines.graph_rag import _deterministic_answer
        from app.engines.graph_rag import GraphContext

        ans = _deterministic_answer(
            "What are the guiding principles established by the AI Act?",
            GraphContext(),
        )
        low = ans.lower()
        # R285 — this test previously asserted "fundamental rights" / "democracy"
        # / "rule of law". Those are Article 1(1) PURPOSE words, and the answer
        # was deliberately re-anchored (R253) onto the actual guiding principles,
        # which live in Recital 27. The assertions below pin that Recital-27
        # enumeration, so this is still a content-regression guard — it just
        # guards the right content.
        assert "recital 27" in low
        assert "human agency and oversight" in low
        assert "technical robustness and safety" in low
        assert "privacy and data governance" in low
        assert "transparency" in low
        assert "non-discrimination" in low
        assert "accountability" in low
        # Article 4 (AI literacy) is what operationalises them.
        assert "article 4" in low


# ── #5 — fusion-path Stage-2 observability ─────────────────────────────────


class _FakeProvider:
    """Strict per-model script dispatch, with a call log.

    ⚠ Script keys MUST be derived from the same single sources of truth the
    product reads (``fusion._panel_registry()`` / ``fusion._judge_model()``),
    never written here as model-id literals. Two literals in this fixture went
    stale and the test could not tell you which:

    * R289 migrated the Groq default off ``qwen/qwen3.6-27b`` to
      ``openai/gpt-oss-120b`` (``owp._GROQ_LIVE_VALIDATED_MODEL``).
    * ``_DEFAULT_JUDGE_MODEL`` moved to ``claude-opus-4-8`` while the fixture
      still scripted the wrapper on ``claude-sonnet-4-6`` only.

    An unscripted model returns ``error='no_script'``, which
    ``_one_candidate`` swallows as a dead transport — so the Groq panel member
    had been silently absent (``fusion.judge_failed panel=[sonnet,mistral]``)
    and, because ``_min_candidates()`` is 2, the panel half of this test would
    have kept passing on the two survivors. Only the judge miss was loud. The
    call log below is what makes that silent half assertable.
    """

    def __init__(self, script):
        self._script = script
        self.calls: list[str] = []

    def complete(self, req):
        self.calls.append(req.model)
        fn = self._script.get(req.model)
        if fn is None:
            return OpenAIWrapperResponse(error="no_script", model=req.model)
        return fn(req)


def _sonnet_script(*, panel_text, judge_text):
    def _fn(req):
        if "FUSION JUDGE" in (req.user or ""):
            return OpenAIWrapperResponse(text=judge_text)
        return OpenAIWrapperResponse(text=panel_text)

    return _fn


class TestR127FusionObservability:
    def test_fusion_records_thinking_on_success(self, monkeypatch):
        from app.integrations.regenold import reasoning_trace as rt

        # Bind the script to the models PRODUCTION resolves, not to literals —
        # both the Groq default and the judge model have migrated since this
        # test was written. See _FakeProvider's docstring.
        registry = fusion._panel_registry()
        panel_sonnet_model = registry["sonnet"][0]
        panel_groq_model = registry["groq"][0]
        panel_mistral_model = registry["mistral"][0]
        judge_model = fusion._judge_model()

        judge_text = "Article 50 requires the deployer to inform exposed persons."
        # One handler, two keys: it already branches on the "FUSION JUDGE"
        # marker in ``req.user``, and it stays correct if an operator collapses
        # the judge onto the panel model (the dict simply has one key then).
        _wrapper_script = _sonnet_script(
            panel_text="Article 50 applies to the deployer.",
            judge_text=judge_text,
        )
        wrapper = _FakeProvider({
            panel_sonnet_model: _wrapper_script,
            judge_model: _wrapper_script,
        })
        groq = _FakeProvider({
            panel_groq_model: lambda r: OpenAIWrapperResponse(
                text="Deployers must inform people under Article 50."
            )
        })
        mistral = _FakeProvider({
            panel_mistral_model: lambda r: OpenAIWrapperResponse(
                text="Article 50 transparency applies."
            )
        })
        monkeypatch.setenv("REGENOLD_FUSION_GATE", "all")
        # R129 — the fusion judge defaults to DETERMINISTIC (no LLM call, so no
        # llm_thinking to record). This test verifies the LLM-judge thinking
        # capture, so opt into the llm judge mode.
        monkeypatch.setenv("REGENOLD_FUSION_JUDGE", "llm")
        monkeypatch.delenv("REGENOLD_FUSION_PANEL", raising=False)
        monkeypatch.setattr(owp, "is_openai_wrapper_enabled", lambda: True)
        monkeypatch.setattr(owp, "is_groq_provider_enabled", lambda: True)
        monkeypatch.setattr(owp, "is_mistral_provider_enabled", lambda: True)
        monkeypatch.setattr(owp, "get_openai_wrapper_provider", lambda: wrapper)
        monkeypatch.setattr(owp, "get_groq_provider", lambda: groq)
        monkeypatch.setattr(owp, "get_mistral_provider", lambda: mistral)
        monkeypatch.setattr(fusion, "_looks_truncated", lambda _t: False)

        trace = rt.activate()
        try:
            out = fusion.fusion_complete(
                system="SYS",
                user="QUESTION: x\n\nEU AI ACT REFERENCES:\n- Article 50",
                max_tokens=512,
            )
        finally:
            rt.deactivate()
        assert out is not None
        # The JUDGE branch of the wrapper script served the final answer (not
        # the panel branch) — pins that the judge call really landed.
        assert out == judge_text
        # #5 — the LLM fusion judge populates the Stage-2 thinking field.
        assert "Stage 2 (Fusion judge)" in trace.llm_thinking
        thinking = trace.llm_thinking["Stage 2 (Fusion judge)"]
        assert "fusion" in thinking.lower()
        # NON-VACUITY. The recorded thinking names the panel members whose
        # drafts the judge weighed, so it is the product's own record of who
        # answered. All three must be present: a member whose script key goes
        # stale drops out silently and ``_min_candidates() == 2`` lets the run
        # succeed on the survivors — which is exactly how the stale Groq model
        # id sat here undetected.
        for _member in ("sonnet", "groq", "mistral"):
            assert _member in thinking, f"panel member {_member} missing: {thinking}"
        # And the models actually requested are the ones production resolves.
        assert wrapper.calls == [panel_sonnet_model, judge_model]
        assert groq.calls == [panel_groq_model]
        assert mistral.calls == [panel_mistral_model]


# ── cache key ──────────────────────────────────────────────────────────────


class TestR127CacheKey:
    def test_fusion_worthy_strict_in_cache_key(self, monkeypatch):
        from app.routes.regenold import _engine_cache_key

        monkeypatch.setenv("REGENOLD_FUSION_WORTHY_STRICT", "1")
        k_on = _engine_cache_key("q", None)
        monkeypatch.setenv("REGENOLD_FUSION_WORTHY_STRICT", "0")
        k_off = _engine_cache_key("q", None)
        assert k_on != k_off
