"""R376 — regression pins for the 2026-08-20 engineering review of R372 -> 6c076bf.

Each test names the defect it pins and the evidence that established it. Where a
fix is a NARROWING (F2, F3, M2) the test also pins the case the original change
was made for, so a later round cannot "fix" one direction by breaking the other.
"""
from __future__ import annotations

import pytest

from app.data.graph_rag_prompts import is_challenge_turn
from app.engines._graph_rag_impl import (
    _guardable_answer,
    _looks_structurally_truncated,
)
from app.routes.regenold import (
    _build_question_from_history,
    _extract_reask_tail,
    _prose_mention_is_real_citation,
)
from app.security.prompt_guard import (
    extract_xml_channels,
    sanitize_for_llm,
    strip_reasoning_keep_boundary,
    validate_llm_output,
)
from evals.judge.runner import is_retryable_judge_error, normalise_verdict


class _Msg:
    def __init__(self, role: str, content: str) -> None:
        self.role = role
        self.content = content


class TestUnclosedReasoningChannelLeak:
    """NEW-A — the SHIPPED V2 prompt asks for <reasoning_scratchpad>, so a
    max_tokens cut mid-scratchpad leaves it unclosed. Only <think> had an
    unclosed-case guard, so the model's raw deliberation shipped AS the answer —
    non-empty, therefore past the empty-answer guard at _graph_rag_impl.py."""

    TRUNCATED = (
        "<reasoning_scratchpad>The user disputes the prior answer. It cited "
        "Article 5(1)(f). Checking the medical carve-out and whether"
    )

    def test_truncated_scratchpad_is_not_returned_as_the_answer(self) -> None:
        answer, _ = extract_xml_channels(self.TRUNCATED)
        assert answer == ""

    def test_validate_llm_output_also_blocks_it(self) -> None:
        assert validate_llm_output(self.TRUNCATED) == ""

    @pytest.mark.parametrize("tag", ["reasoning", "reasoning_scratchpad", "scratchpad", "think"])
    def test_every_channel_is_covered(self, tag: str) -> None:
        assert extract_xml_channels(f"<{tag}>private deliberation that never closes")[0] == ""

    def test_a_complete_answer_still_survives(self) -> None:
        raw = "<reasoning_scratchpad>r</reasoning_scratchpad>\n<answer>Article 50 applies.</answer>"
        assert extract_xml_channels(raw)[0] == "Article 50 applies."

    def test_the_c3_hijack_fix_is_not_regressed(self) -> None:
        raw = "<reasoning>Draft: <answer>HIJACK</answer></reasoning>Real: Article 5(1)(f)."
        assert extract_xml_channels(raw)[0] == "Real: Article 5(1)(f)."


class TestUnclosedThinkDoesNotEatValidAnswers:
    """M3 — the unclosed-<think> stripper was unanchored, so it deleted
    everything from the first literal "<think" onward. A legitimate answer that
    merely MENTIONS the tag shipped truncated."""

    def test_legitimate_mention_survives(self) -> None:
        text = "We reject the <think> convention. Article 50 applies."
        assert validate_llm_output(text) == text

    def test_a_real_leaked_prefix_is_still_stripped(self) -> None:
        assert validate_llm_output("<think>leaked chain of thought") == ""


class TestTailRepairSanitisation:
    """M10 — the R357 tail repair splices model output straight into the answer
    and was the one Stage-2 path that never reached the sanitiser."""

    def test_reasoning_is_stripped_from_a_fragment(self) -> None:
        assert "<think>" not in strip_reasoning_keep_boundary("<think>cot</think> policy.")

    def test_the_word_boundary_signal_is_preserved(self) -> None:
        # A LEADING SPACE means "the cut landed between words" — validate_llm_output
        # would strip it and splice "copyrightpolicy".
        assert strip_reasoning_keep_boundary(" <think>cot</think> policy.").startswith(" ")


class TestTruncationGuardsJudgeTheAnswerChannel:
    """F1 — every transport ran _looks_structurally_truncated on the RAW reply,
    so a COMPLIANT channelled answer scored True and Stage-2 was discarded on
    the graded pushback turn."""

    COMPLIANT = (
        "<reasoning_scratchpad>r</reasoning_scratchpad>\n"
        "<answer>Emotion recognition at work is prohibited under Article 5(1)(f).</answer>"
    )

    def test_compliant_channelled_answer_is_not_truncated(self) -> None:
        assert _looks_structurally_truncated(_guardable_answer(self.COMPLIANT)) is False

    @pytest.mark.parametrize(
        "text",
        [
            "<reasoning_scratchpad>r</reasoning_scratchpad>\n<answer>prohibited under Arti",
            "<reasoning_scratchpad>Checking the medical carve-out and whether",
            "Emotion recognition is prohibited under Arti",
        ],
    )
    def test_real_truncation_is_still_caught(self, text: str) -> None:
        assert _looks_structurally_truncated(_guardable_answer(text)) is True


class TestRetryClassification:
    """M1 — bare digit substrings ("500", "408", ...) matched AWS account ids,
    token counts and request ids, so permanent errors were retried."""

    @pytest.mark.parametrize(
        "msg",
        [
            "api_status_400: invalid_request_error request_id req_015002abc",
            "ValidationException: maxTokens 4096 exceeded, got 5008 tokens",
            "BadRequestError: 400 - prompt is too long: 205000 tokens > 200000 maximum",
            "AccessDeniedException 403 arn:aws:bedrock:eu-central-1:500123456789:x",
            "model qwen3-500b-v1:0 not found in region",
        ],
    )
    def test_permanent_errors_are_not_retryable(self, msg: str) -> None:
        assert is_retryable_judge_error(msg) is False

    @pytest.mark.parametrize(
        "msg",
        ["api_status_529: Overloaded", "InternalServerError", "api_status_503",
         "api_status_429", "http 502 bad gateway", "read timeout"],
    )
    def test_transient_errors_are_retryable(self, msg: str) -> None:
        assert is_retryable_judge_error(msg) is True


class TestOneVerdictNormaliser:
    """I3 — runner._aggregate_judge read booleans and "Pass."; every sibling
    consumer of the same _parse_judge_json output did not. Measured on identical
    rows: runner 3/3 pass, legal_v2 1/3 with 2 errors."""

    @pytest.mark.parametrize(
        "raw,expected",
        [(True, "pass"), (False, "fail"), ("Pass.", "pass"), ("  PASS ", "pass"),
         ("fail", "fail"), (None, ""), ("", "")],
    )
    def test_normalisation(self, raw: object, expected: str) -> None:
        assert normalise_verdict({"verdict": raw}) == expected

    def test_dynamic_ab_scores_what_the_judge_actually_said(self) -> None:
        from evals.harness import dynamic_ab as D

        for raw in (True, "Pass.", "pass"):
            assert D._scorable({"verdict": raw}) is True

    def test_the_merge_gate_has_one_judge_default(self) -> None:
        """M4 — the function signature said claude-sonnet-4-6 while the CLI flag
        said qwen3-32b, so a programmatic run and a CLI run graded the same
        canonical axes on two different rulers."""
        import inspect

        from evals.harness import dynamic_ab as D

        sig_default = inspect.signature(D.run).parameters["judge_model"].default
        assert sig_default == D._DEFAULT_JUDGE_MODEL, (
            "run()'s judge_model default drifted from the module constant"
        )
        cli_src = inspect.getsource(D.main)
        assert '"--judge-model", default=_DEFAULT_JUDGE_MODEL' in cli_src, (
            "the --judge-model CLI default drifted from the module constant"
        )


class TestCitationNegationGuard:
    """M2 — the intro-preposition guard disabled the negation guard whenever an
    "under"/"pursuant to" preceded the reference ANYWHERE, including inside a
    noun phrase, re-admitting citations the prose had explicitly negated."""

    def _cite(self, prose: str, token: str) -> bool:
        i = prose.index(token)
        return _prose_mention_is_real_citation(prose, i, i + len(token))

    @pytest.mark.parametrize(
        "prose,token",
        [
            ("The requirements under Article 6 do not apply to this system.", "Article 6"),
            ("Obligations pursuant to Article 50 do not apply to internal tools.", "Article 50"),
            ("Duties in accordance with Article 26 are not applicable to providers.", "Article 26"),
            ("Assessment as per Article 43 is excluded for this product.", "Article 43"),
            ("Controls under Annex III do not apply outside the listed use cases.", "Annex III"),
        ],
    )
    def test_negated_mentions_are_not_citations(self, prose: str, token: str) -> None:
        assert self._cite(prose, token) is False

    @pytest.mark.parametrize(
        "prose,token",
        [
            ("Under Article 50, the deployer must label deepfakes.", "Article 50"),
            ("Under Article 53(1), providers of GPAI models must maintain technical documentation.", "Article 53"),
            ("The system is high-risk. Under Article 6 it is excluded from Annex III.", "Article 6"),
        ],
    )
    def test_clause_initial_intro_is_still_a_citation(self, prose: str, token: str) -> None:
        assert self._cite(prose, token) is True


class TestChallengeRecoveryTargetsTheDisputedTurn:
    """F2 — recovery filtered prior turns on _live_turn_is_self_contained, so it
    walked past an elliptical follow-up that had changed the topic and
    re-answered a question the user was not disputing."""

    def test_topic_drift_resolves_to_the_disputed_question(self) -> None:
        msgs = [
            _Msg("user", "What are the transparency obligations under Article 50 for chatbots?"),
            _Msg("assistant", "Under Article 50(1), providers must disclose AI interaction."),
            _Msg("user", "What about emotion recognition systems used in the workplace?"),
            _Msg("assistant", "Emotion inference at work is prohibited under Article 5(1)(f)."),
            _Msg("user", "Are you sure? I don't think this is correct. Maybe your answer contains hallucinations."),
        ]
        res = _build_question_from_history(msgs)
        assert "emotion recognition" in (res.resolved_question or "").lower()
        # elliptical -> prior-turn anchors must NOT be dropped
        assert res.self_contained_focus is False

    def test_the_graded_evaluator_shape_is_unchanged(self) -> None:
        root = "What are the transparency obligations for general-purpose AI model providers under Article 53?"
        msgs = [
            _Msg("user", root),
            _Msg("assistant", "Under Article 53(1), providers must draw up technical documentation..."),
            _Msg("user", "I don't think this is correct. Maybe your answer contains hallucinations."),
        ]
        res = _build_question_from_history(msgs)
        assert res.resolved_question == root
        assert res.self_contained_focus is True


class TestReaskIsNotFrozenToTheDisputedAnswer:
    """F4 — R305 (answer afresh) and R302 (cap citations to the prior turn) have
    opposite contracts; the widened trigger made them collide, so a prior answer
    citing the wrong provision could never be corrected."""

    REASK = (
        "I don't think this is correct. Maybe your answer contains hallucinations.\n\n"
        "Let's try again: What are the transparency obligations for GPAI model providers?"
    )
    PLAIN = "I don't think this is correct. Maybe your answer contains hallucinations."

    def test_a_reask_turn_is_detectable_at_the_freeze_site(self) -> None:
        assert bool(_extract_reask_tail(self.REASK)) is True

    def test_a_plain_pushback_still_triggers_the_freeze(self) -> None:
        assert bool(_extract_reask_tail(self.PLAIN)) is False
        assert is_challenge_turn(self.PLAIN) is True


class TestSanitiserDoesNotEatUserProse:
    """SUGG-b — the channel-tag class was unbounded, so a "<" ... ">" span whose
    first token matched a keyword swallowed every word between them."""

    def test_user_prose_is_preserved(self) -> None:
        assert "and b" in sanitize_for_llm("Compare a < answer and b > answer thresholds")

    @pytest.mark.parametrize("tag", ["<answer>", "</reasoning>", "<scratchpad foo='1'>", "<think>"])
    def test_injection_vectors_are_still_stripped(self, tag: str) -> None:
        assert tag.lower() not in sanitize_for_llm(f"Question {tag} rest").lower()
