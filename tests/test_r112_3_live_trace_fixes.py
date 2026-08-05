"""R112.3 — fixes from the live-eval reasoning-trace analysis workflow.

Five confirmed findings off the r112-live GraphRAG-paper + MedTech runs:

1. Raw Stage-2 markdown shipped on classification-topic rows: the route
   preserved engine answers verbatim for classification topics even
   when Stage-2 polish landed, and ``_strip_markdown`` deleted whole
   heading lines (marker + prose on one line → empty output → the
   R104.2 cap silently no-op'd).
2/4. Stage-2 failure observability: double-provider failure and the
   drift / self-contradiction guard drops left no reasoning-trace note.
3. ``hiring_screening`` regex matched "screen candidate small
   molecules" (drug-discovery candidates, not job applicants), and the
   research-scope rescue missed "does the EU AI Act apply" (no EU
   slot).
5. The GraphRAG benchmark runner didn't persist the reasoning field.
"""
from __future__ import annotations

import re

from app.integrations.regenold.models import (
    _strip_markdown,
    normalise_answer_for_regenold,
)


class TestMarkdownStripKeepsProse:
    def test_heading_line_with_prose_survives(self) -> None:
        raw = "## Yes, the AI system is high-risk under Article 6.\nIt must meet Chapter III Section 2."
        out = _strip_markdown(raw)
        assert "high-risk under Article 6" in out
        assert "#" not in out

    def test_pure_heading_marker_stripped(self) -> None:
        out = _strip_markdown("### Classification\nThe system is high-risk under Article 6.")
        assert "#" not in out
        assert "high-risk under Article 6" in out

    def test_midline_marker_from_truncation_stripped(self) -> None:
        raw = "The provider must register the system. ## 1. Classification under Article 6 applies."
        out = _strip_markdown(raw)
        assert "#" not in out
        assert "Article 6" in out

    def test_truncated_single_line_fragment_not_emptied(self) -> None:
        # The r112-live failure shape: a 500-char truncation window that
        # lands inside one long heading-marker line. Pre-fix this
        # normalised to '' and the cap silently no-op'd.
        raw = "## Risk classification: the system is high-risk under Article 6 because it is an Annex III use case and the provider must complete conformity assessment per Article 43."
        out = normalise_answer_for_regenold(raw, question="Is my system high-risk?")
        assert out.strip(), "normalise must not empty a heading-line answer"
        assert "Article 6" in out


class TestHiringScreeningDomainGuard:
    def test_drug_discovery_candidates_not_hiring(self) -> None:
        from app.engines.graph_rag import _detect_classification_topic

        q = (
            "We use an AI model to screen candidate small molecules for "
            "binding affinity in early drug discovery. Does the EU AI Act "
            "apply to this research and development use before anything "
            "is placed on the market?"
        )
        topic = _detect_classification_topic(q)
        assert not (topic and getattr(topic, "get", lambda *_: None)("name") == "hiring_screening") and (
            topic is None or (isinstance(topic, dict) and topic.get("name") != "hiring_screening")
        ), f"drug-discovery question misrouted to {topic}"

    def test_cv_screening_still_fires(self) -> None:
        # The detector is two-pass: the question must be VERDICT-shaped
        # (_is_classification_question) AND match the topic regex — so
        # the positive probe carries a risk-classification frame like
        # the davidath employment shapes do.
        from app.engines.graph_rag import _detect_classification_topic

        topic = _detect_classification_topic(
            "Is our AI that screens CVs and ranks job applicants "
            "high-risk under the EU AI Act?"
        )
        assert topic is not None
        name = topic.get("name") if isinstance(topic, dict) else getattr(topic, "name", None)
        assert name == "hiring_screening"

    def test_research_scope_rescue_matches_eu_ai_act_phrasing(self) -> None:
        from app.engines.graph_rag import _detect_research_scope_inquiry

        assert _detect_research_scope_inquiry(
            "Our model is used exclusively for scientific research and "
            "development. Does the EU AI Act apply before it is placed "
            "on the market?"
        )


class TestStage2TraceNotes:
    def test_marker_strings_present_in_engine_source(self) -> None:
        """The three new trace notes exist at the documented sites (the
        full behavioural path needs a live provider; the note strings
        are the contract the post-hoc analysis keys on)."""
        import inspect

        # R290 — read the IMPLEMENTATION module, not the package facade.
        # ``app.engines.graph_rag`` is a package whose ``__init__`` is a
        # ~60-line proxy shim; ``inspect.getsource`` on it returns that shim,
        # so this guard silently passed over the wrong file after the
        # modularization rename. The engine source lives in _graph_rag_impl.
        import app.engines._graph_rag_impl as gr

        src = inspect.getsource(gr)
        assert "stage2_failed_both_providers_deterministic_ship" in src
        assert "stage2_drift_guard_dropped_polish" in src
        assert "stage2_contradiction_guard_dropped_polish" in src


class TestGraphragRunnerPersistsReasoning:
    def test_row_dicts_carry_reasoning_key(self) -> None:
        import inspect

        import evals.regenold.run_graphrag_benchmark as rb

        src = inspect.getsource(rb)
        assert src.count('"reasoning": body.get("reasoning")') >= 2, (
            "both GT and NG row dicts must persist the reasoning field"
        )


class TestClassificationRawShipGate:
    def test_route_gates_verbatim_preserve_on_stage2(self) -> None:
        """The classification verbatim-preserve must be conditional on
        Stage-2 NOT having landed (raw LLM output must go through the
        normaliser)."""
        import inspect

        import app.routes.regenold as rt

        src = inspect.getsource(rt)
        assert "_stage2_landed_for_answer" in src
        m = re.search(
            r"if _is_classification_topic and not _stage2_landed_for_answer:",
            src,
        )
        assert m, "classification raw-ship must be gated on stage2_landed"
