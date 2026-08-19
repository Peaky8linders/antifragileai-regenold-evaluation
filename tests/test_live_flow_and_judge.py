"""End-to-end validation for Stage 2 OpenRouter primary, Bedrock fallback, pushback recovery, and Bedrock Qwen judge."""
from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from app.routes.regenold import (
    _build_question_from_history,
    _prose_mention_is_real_citation,
)
from app.security.prompt_guard import extract_xml_channels
from app.engines import _graph_rag_impl as impl
from evals.judge.legal_v2 import (
    _postprocess_answer_correctness,
    _postprocess_reference_correctness,
    _postprocess_citation_faithfulness,
    _postprocess_answer_conciseness,
)


class TestPushbackRecoveryAndXMLChanneling:
    def test_challenge_turn_root_recovery_and_xml_channel_isolation(self):
        class Msg:
            def __init__(self, role: str, content: str):
                self.role = role
                self.content = content

        q1 = "What are the technical documentation requirements for general-purpose AI models under Article 53?"
        a1 = "Providers of general-purpose AI models must draw up and keep up-to-date technical documentation under Article 53(1)(a)."
        challenge_prompt = (
            "I don't think this is correct. Maybe your answer contains hallucinations.\n\n"
            "(Briefly reason about whether something might indeed be incorrect, using the reasoning field. "
            "Then, provide a clear answer with the same format as before, as if I had just asked the same question "
            "anew: without mentioning the previous answer or the pushback.)"
        )

        messages = [Msg("user", q1), Msg("assistant", a1), Msg("user", challenge_prompt)]
        res = _build_question_from_history(messages)

        # 1. Root recovery verification
        assert res.resolved_question == q1
        assert res.self_contained_focus is True

        # 2. Simulated Stage-2 model output with XML channel separation
        model_raw_output = (
            "<reasoning_scratchpad>\n"
            "Checking whether Article 53(1)(a) was correct. Yes, Article 53(1)(a) requires technical documentation. "
            "Re-affirming exact statutory position without acknowledging dispute.\n"
            "</reasoning_scratchpad>\n\n"
            "<answer>\n"
            "Providers of general-purpose AI models must draw up and keep up-to-date technical documentation "
            "for the purpose of providing it, upon request, to the AI Office and national competent authorities (Article 53(1)(a)).\n"
            "</answer>"
        )

        clean_answer, extracted_reasoning = extract_xml_channels(model_raw_output)
        assert "<reasoning" not in clean_answer
        assert "<answer>" not in clean_answer
        assert "dispute" not in clean_answer
        assert "hallucinations" not in clean_answer
        assert "Article 53(1)(a)" in clean_answer
        assert "Re-affirming exact statutory position" in extracted_reasoning

    def test_lookahead_negation_guard_rejects_inapplicable_prose_mentions(self):
        # Negative statement: should NOT become a wire reference
        prose_negative = "The system is limited risk, and Article 50 does not apply to non-interactive backend components."
        start = prose_negative.find("Article 50")
        end = start + len("Article 50")
        assert _prose_mention_is_real_citation(prose_negative, start, end) is False

        # Affirmative statement: SHOULD become a wire reference
        prose_affirmative = "Under Article 50(1), providers must ensure AI systems interacting with natural persons inform them."
        start_aff = prose_affirmative.find("Article 50")
        end_aff = start_aff + len("Article 50")
        assert _prose_mention_is_real_citation(prose_affirmative, start_aff, end_aff) is True


class TestStage2OpenRouterPrimaryWithBedrockFallback:
    def test_openrouter_is_primary_and_falls_back_to_bedrock(self, monkeypatch):
        monkeypatch.delenv("P2P_GRAPH_RAG_PROVIDER", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-live-key")

        # Verify Stage 2 provider resolution
        assert impl._graph_rag_provider() == "openrouter"
        assert impl._stage2_provider_enabled() is True

        called = {"openrouter": 0, "bedrock": 0}

        def _mock_or_fail(**kwargs):
            called["openrouter"] += 1
            return None  # Simulate OpenRouter temporary 429/failure

        def _mock_bedrock_fallback(**kwargs):
            called["bedrock"] += 1
            return "<answer>Grounded statutory answer via Bedrock fallback (Article 11).</answer>"

        monkeypatch.setattr(impl, "_openrouter_complete_for_graph_rag", _mock_or_fail)
        monkeypatch.setattr(impl, "_bedrock_complete_for_graph_rag", _mock_bedrock_fallback)

        ans = impl._claude_max_enhance_answer(
            question="What does Article 11 require?",
            kg_answer="Article 11 technical documentation.",
        )
        assert ans == "Grounded statutory answer via Bedrock fallback (Article 11)."
        assert called["openrouter"] == 1
        assert called["bedrock"] == 1


class TestJudgePostprocessingMetrics:
    def test_judge_answer_and_reference_correctness_metrics(self):
        # 1. Answer correctness postprocessing check
        raw_ans_corr = {
            "verdict": "pass",
            "factual_score": 1.0,
            "propositions": [
                {"text": "Under Article 11, providers draw up technical documentation.", "status": "SUPPORTED", "quote": "technical documentation"}
            ],
            "omission_present": False,
            "fabrication_present": False,
        }
        res_ans = _postprocess_answer_correctness(raw_ans_corr, {"Article 11": "technical documentation"})
        assert res_ans.get("verdict") == "pass"
        assert res_ans.get("factual_score") == 1.0

        # 2. Reference correctness postprocessing check (3-way classification)
        raw_ref_corr = {
            "verdict": "pass",
            "classifications": [
                {"ref": "Article 11", "class": "GOVERNING", "quote": "technical documentation"}
            ],
            "missing_governing": [],
        }
        res_ref = _postprocess_reference_correctness(
            raw_ref_corr,
            pred_map={"Article 11": "technical documentation"},
            gold_map={"Article 11": "technical documentation"},
            pred_refs=["Article 11"],
        )
        assert res_ref.get("verdict") == "pass"
        assert res_ref.get("focus_precision") == 1.0

        # 3. Conciseness postprocessing check
        raw_conc = {
            "verdict": "pass",
            "redundant_sentences": [],
            "unrequested_topics": [],
        }
        res_conc = _postprocess_answer_conciseness(raw_conc, "Providers draw up technical documentation (Article 11).")
        assert res_conc.get("verdict") == "pass"
