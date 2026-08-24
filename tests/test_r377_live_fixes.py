"""R377 — regression pins for the two defects the LIVE run surfaced.

Both were invisible to the suite for the same structural reason the R376 record
gives: the existing tests exercise these guards on hand-written strings that
look like what the authors expected a model to emit. Neither defect is about a
model behaving badly — in both cases the model produced a CORRECT answer and a
guard downstream threw it away.

R377-A — ``_looks_structurally_truncated`` and the XML answer channel.
R377-B — ``guard_cross_tier_polish`` and a DENIED tier counted as an ASSERTED one.
"""

from __future__ import annotations

import pytest

from app.engines._graph_rag_impl import _looks_structurally_truncated
from app.engines.stage2_fidelity import (
    extract_asserted_tier_set,
    extract_tier_set,
    guard_cross_tier_polish,
)

# ─── R377-A ──────────────────────────────────────────────────────────────────

#: The exact Sonnet 5 tail measured live on the emotion-recognition pushback
#: turn, which was discarded as truncated.
_LIVE_XML_ANSWER = (
    "No. Article 5(1)(f) prohibits the use of AI systems to infer emotions of a "
    "natural person in the areas of workplace and education institutions. "
    "Consent of the employees is not a condition of that prohibition and cannot "
    "make the practice lawful.\n</answer>"
)


class TestR377AXmlChannelIsNotTruncation:
    """A closing XML channel tag WRAPS the answer; it does not cut it."""

    def test_live_xml_wrapped_answer_is_not_truncated(self) -> None:
        assert _looks_structurally_truncated(_LIVE_XML_ANSWER) is False

    def test_nested_closing_channels_are_peeled(self) -> None:
        text = "The system is prohibited under Article 5(1)(f).</answer>\n</reasoning_scratchpad>"
        assert _looks_structurally_truncated(text) is False

    @pytest.mark.parametrize(
        "text",
        [
            "The provider must",
            "the deployer shall, in accordance with",
            "under Article 26(1),",
        ],
    )
    def test_genuine_truncation_still_detected(self, text: str) -> None:
        assert _looks_structurally_truncated(text) is True

    def test_bare_angle_bracket_is_not_peeled(self) -> None:
        """Only a WELL-FORMED closing tag is a wrapper. A dangling ``>`` is a cut."""
        assert _looks_structurally_truncated("training compute greater than 10^25 >") is True

    def test_tag_without_terminator_inside_is_still_truncated(self) -> None:
        """Peeling the tag must expose the REAL final character, not excuse it."""
        assert _looks_structurally_truncated("remains prohibited</answer>") is True

    def test_r328_3_markdown_peel_preserved(self) -> None:
        assert _looks_structurally_truncated("*Sources: see Recitals 46-59.*") is False
        assert _looks_structurally_truncated("| Article 9 | risk management |") is False

    def test_r357_ellipsis_cut_preserved(self) -> None:
        assert _looks_structurally_truncated("The provider must…") is True


# ─── R377-B ──────────────────────────────────────────────────────────────────

#: The deterministic draft measured live on the CV-screening + GPAI question.
#: It asserts ONE tier (limited) and DENIES another (high-risk) — but the denial
#: carries an ``Article 6`` anchor, so the anchor-only probe read two tiers.
_LIVE_DETERMINISTIC_DRAFT = (
    "This system is classified as limited-risk under the Article 50 transparency "
    "obligations. The provider must provide AI literacy training to all staff "
    "involved in development, deployment and operation of the system, and document "
    "a classification assessment confirming the system is not high-risk under "
    "Article 6 (Article 4). A clear notice must be displayed to users at the first "
    "interaction informing them they are interacting with an AI system, and "
    "AI-generated content must be clearly labelled as such (Article 50)."
)

#: The CORRECT Opus 5 polish that the guard discarded.
_LIVE_POLISH = (
    "A CV-screening and applicant-ranking system placed on the market for employers "
    "is high-risk, because recruitment and selection of natural persons is an Annex "
    "III use case that Article 6(2) classifies as high-risk. The company is the "
    "provider under Article 25(1)(c)."
)

_CLASSIFICATION_Q = (
    "Our company is building an AI system that screens CVs and ranks job applicants. "
    "What risk class applies, which role are we in, what conformity assessment route, "
    "and what documentation must we hold?"
)

#: The R146 fixture: a QUALIFIED denial that still asserts the tier elsewhere.
_CROSS_TIER_DRAFT = (
    "The system is not categorically prohibited under Article 5. "
    "In workplaces or education it is banned, but elsewhere it is high-risk "
    "under Annex III and Article 6. It also triggers Article 50 transparency "
    "duties toward exposed persons."
)


class TestR377BDeniedTierIsNotAssertedTier:
    def test_denied_tier_excluded_from_contract(self) -> None:
        assert extract_asserted_tier_set(_LIVE_DETERMINISTIC_DRAFT) == {"limited"}

    def test_anchor_probe_is_left_byte_identical(self) -> None:
        """The POLISH side must keep asking "is this tier ADDRESSED"."""
        assert extract_tier_set(_LIVE_DETERMINISTIC_DRAFT) == {"limited", "high_risk"}

    def test_qualified_denial_still_asserts_the_tier(self) -> None:
        """R146's own fixture: denied in one sentence, asserted in the next."""
        assert extract_asserted_tier_set(_CROSS_TIER_DRAFT) == {
            "prohibited",
            "high_risk",
            "limited",
        }

    def test_negation_elsewhere_is_not_a_tier_denial(self) -> None:
        """"does not remove this classification" must not suppress high-risk."""
        text = (
            "The Article 6(3) derogation does not remove this classification, because "
            "ranking candidates materially influences the outcome of the decision."
        )
        assert extract_asserted_tier_set(text) == {"high_risk"}

    def test_single_asserted_tier_lets_the_polish_ship(self) -> None:
        out, action = guard_cross_tier_polish(
            _LIVE_DETERMINISTIC_DRAFT, _LIVE_POLISH, _CLASSIFICATION_Q
        )
        assert action == "not_cross_tier"
        assert out == _LIVE_POLISH

    def test_env_gate_restores_the_pre_r377_reading(self, monkeypatch) -> None:
        monkeypatch.setenv("REGENOLD_FIDELITY_TIER_NEGATION", "0")
        assert extract_asserted_tier_set(_LIVE_DETERMINISTIC_DRAFT) == {
            "limited",
            "high_risk",
        }

    def test_gate_is_read_fresh_per_call(self, monkeypatch) -> None:
        """R334 drift guard — a flag read at import is worse than an unkeyed one."""
        monkeypatch.setenv("REGENOLD_FIDELITY_TIER_NEGATION", "0")
        legacy = extract_asserted_tier_set(_LIVE_DETERMINISTIC_DRAFT)
        monkeypatch.setenv("REGENOLD_FIDELITY_TIER_NEGATION", "1")
        fixed = extract_asserted_tier_set(_LIVE_DETERMINISTIC_DRAFT)
        assert legacy != fixed


# ─── R377-C ──────────────────────────────────────────────────────────────────


class TestR377CFramesRewriterBreaker:
    """The hot-path sub-query rewrite must not re-pay a timeout forever.

    Measured live: 3690 / 3052 / 3026 ms for three sub-queries, every one
    returning the sub-query UNCHANGED, because the hop is hard-bound to the
    wrapper tunnel regardless of ``P2P_GRAPH_RAG_PROVIDER``.
    """

    def _stub_failure(self, monkeypatch):
        import app.engines.frames_rewriter as fr

        calls = {"n": 0}

        def boom(*_a, **_k):
            calls["n"] += 1
            raise TimeoutError("read timed out")

        monkeypatch.setattr(fr, "is_openai_wrapper_enabled", lambda: True)
        monkeypatch.setattr(fr, "get_openai_wrapper_provider", boom)
        fr._reset_frames_breaker_for_tests()
        return fr, calls

    def test_breaker_opens_and_stops_calling(self, monkeypatch) -> None:
        fr, calls = self._stub_failure(monkeypatch)
        for _ in range(6):
            assert fr.rewrite_sub_query_llm("sub", "orig") == "sub"
        # Threshold is 2, so only the first two attempts reach the provider.
        assert calls["n"] == 2

    def test_off_switch_restores_unbounded_calling(self, monkeypatch) -> None:
        monkeypatch.setenv("REGENOLD_FRAMES_REWRITER_BREAKER", "0")
        fr, calls = self._stub_failure(monkeypatch)
        for _ in range(5):
            fr.rewrite_sub_query_llm("sub", "orig")
        assert calls["n"] == 5

    def test_a_success_resets_the_breaker(self, monkeypatch) -> None:
        import app.engines.frames_rewriter as fr

        fr._reset_frames_breaker_for_tests()
        fr._breaker_record_failure()
        fr._breaker_record_failure()
        assert fr._breaker_is_open() is True
        fr._breaker_record_success()
        assert fr._breaker_is_open() is False

    def test_the_hop_still_runs_when_the_provider_works(self, monkeypatch) -> None:
        """The breaker must be invisible whenever the rewrite actually works."""
        import app.engines.frames_rewriter as fr

        class _Resp:
            error = None
            text = "provider obligations for CV screening"

        class _P:
            def complete(self, _req):
                return _Resp()

        monkeypatch.setattr(fr, "is_openai_wrapper_enabled", lambda: True)
        monkeypatch.setattr(fr, "get_openai_wrapper_provider", lambda: _P())
        fr._reset_frames_breaker_for_tests()
        for _ in range(5):
            assert (
                fr.rewrite_sub_query_llm("sub", "orig")
                == "provider obligations for CV screening"
            )


# ─── R377-D ──────────────────────────────────────────────────────────────────


class TestR377DWorkplaceEmotionRecognition:
    """A call centre is a workplace, so Article 5(1)(f) bites.

    MEASURED LIVE against the deployed service:

        "We deploy an emotion recognition system in our call centre to monitor
         agent stress. Is that permitted in the EU?"
        -> "Emotion recognition is not categorically prohibited under the AI
            Act ... Elsewhere the system is high-risk"          (WRONG)

        "Can we use emotion recognition on our employees in the office?"
        -> "Prohibited. Article 5 bans ..."                     (CORRECT)

    The only difference was the vocabulary: the workplace token list carried
    ``employee`` but not ``staff`` / ``worker`` / ``call centre``. Under-warning
    on a prohibited practice is the worst direction this product can fail in.
    """

    def _match(self, question: str) -> str | None:
        from app.engines._graph_rag_data import _CLASSIFICATION_TOPICS

        for entry in _CLASSIFICATION_TOPICS:
            if "emotion" not in entry.get("name", ""):
                continue
            if any(p.search(question) for p in entry["patterns"]):
                return entry["name"]
        return None

    @pytest.mark.parametrize(
        "question",
        [
            "We deploy an emotion recognition system in our call centre to monitor agent stress.",
            "We monitor the stress of our call-centre agents with an emotion recognition AI.",
            "Can we use emotion recognition on our employees in the office?",
            "Emotion recognition used on our staff during shifts",
            "Emotion detection applied to our workforce",
            "Emotion recognition on personnel in the plant",
        ],
    )
    def test_workplace_shapes_reach_the_prohibition_entry(self, question: str) -> None:
        assert self._match(question) == "emotion_recognition_workplace"

    @pytest.mark.parametrize(
        "question",
        [
            "Emotion recognition in our retail stores to measure customer satisfaction",
            "Emotion detection on viewers of our advertising",
            "Emotion recognition for driver drowsiness in consumer cars",
        ],
    )
    def test_non_workplace_shapes_stay_general(self, question: str) -> None:
        """The widening must not sweep in deployments Article 5(1)(f) does not reach."""
        assert self._match(question) == "emotion_recognition_general"

    def test_agent_alone_is_not_a_workplace_token(self) -> None:
        """"agent" collides with "AI agent" and is deliberately excluded."""
        assert self._match("Emotion recognition inside our AI agent product") == (
            "emotion_recognition_general"
        )

    def test_rescue_path_prefers_the_narrow_workplace_entry(self) -> None:
        """R377 — the R330 emotion rescue used to hard-code the general entry.

        The two questions below describe the SAME deployment and differ only in
        their closing clause. Measured live, the first was not classification-
        SHAPED, took the rescue, and got "not categorically prohibited"; the
        second was, took the main loop, and got the Article 5 prohibition.
        """
        from app.engines._graph_rag_impl import _detect_classification_topic

        not_verdict_shaped = (
            "We deploy an emotion recognition system in our call centre to "
            "monitor agent stress. Is that permitted in the EU?"
        )
        verdict_shaped = (
            "We monitor the stress levels of our call-centre agents with an "
            "emotion recognition AI. Is that allowed?"
        )
        for q in (not_verdict_shaped, verdict_shaped):
            topic = _detect_classification_topic(q)
            assert topic is not None
            assert topic["name"] == "emotion_recognition_workplace"

    @pytest.mark.parametrize(
        "question",
        [
            "Emotion recognition in our retail stores to measure customer satisfaction. Is that permitted?",
            "Is emotion detection on viewers of our advertising permitted?",
            "Is emotion recognition for driver drowsiness in consumer cars allowed?",
        ],
    )
    def test_rescue_path_still_serves_general_off_workplace(self, question: str) -> None:
        """The rescue's original job is unchanged for non-workplace traffic."""
        from app.engines._graph_rag_impl import _detect_classification_topic

        topic = _detect_classification_topic(question)
        assert topic is not None
        assert topic["name"] == "emotion_recognition_general"


# ─── R377-E ──────────────────────────────────────────────────────────────────


class TestR377EChallengeTurnDetection:
    """A pushback does not have to say "you are wrong" to be a pushback.

    MEASURED: against ten realistic pushback turns written the way a compliance
    lead actually pushes back, the pre-R377 detector scored 0/10. Every marker
    it carried was an explicit dispute phrase; none of these disputes anything
    explicitly -- they assert a conclusion and ask the assistant to ratify it.
    """

    #: The exact turn measured live, which produced
    #: ``stage2_skipped_curated_authoritative``, no Stage-2 and eleven refs.
    LIVE_DEROGATION_PUSHBACK = (
        "But Article 6(3) says a system is not high-risk if it performs a narrow "
        "procedural task. Ours only sorts CVs into a preliminary order for a human "
        "recruiter. So the derogation applies and we are exempt, correct?"
    )

    GENUINE_PUSHBACKS = [
        LIVE_DEROGATION_PUSHBACK,
        "Our vendor says we're exempt because the tool only assists a human recruiter. "
        "So we have no obligations, correct?",
        "We are a US company and the model is hosted in Virginia. The AI Act is EU law, "
        "so it does not reach us. Agreed?",
        "So we are out of scope then?",
        "That means we do not need a conformity assessment, right?",
        "Just confirm that a loyalty programme is fine so we can move on.",
        "So we don't need technical documentation for this, correct?",
        "We're exempt under Article 2(6) because this is research, right?",
        "Then we have no obligations under Chapter III, correct?",
        "So it is not covered by Annex III, agreed?",
    ]

    #: Ordinary turn-2 follow-ups. A false positive here freezes references,
    #: shortens the answer and bypasses the curated intercept on a turn that was
    #: not a challenge, so precision is the binding constraint.
    ORDINARY_FOLLOW_UPS = [
        "Thanks. What about the deployer's obligations?",
        "Can you also explain the conformity assessment route?",
        "Is that correct for Annex I products too?",
        "Which article covers the logging requirement?",
        "How long must we retain the logs?",
        "What happens if we modify the intended purpose later?",
        "Does the same apply to our importer?",
        "Could you list the Annex IV contents?",
        "And for a general-purpose model, is the threshold different?",
        "What is the deadline for compliance?",
        "Should we reconsider our classification if we add profiling?",
        "Is the fine calculated on group turnover or entity turnover?",
        "Please confirm the article number you cited.",
        "Can you confirm whether Annex III point 4 applies?",
        "We want to be sure we are compliant. What else is needed?",
    ]

    @pytest.mark.parametrize("question", GENUINE_PUSHBACKS)
    def test_leading_confirmation_pushback_is_a_challenge(self, question: str) -> None:
        from app.data.graph_rag_prompts import is_challenge_turn

        assert is_challenge_turn(question) is True

    @pytest.mark.parametrize("question", ORDINARY_FOLLOW_UPS)
    def test_ordinary_follow_ups_are_not_challenges(self, question: str) -> None:
        """Precision guard: none of these asserts a conclusion."""
        from app.data.graph_rag_prompts import is_challenge_turn

        assert is_challenge_turn(question) is False

    def test_bare_verification_request_is_not_a_challenge(self) -> None:
        """The punctuation before the tag is load-bearing.

        "Is that correct?" asks; "..., correct?" asserts.
        """
        from app.data.graph_rag_prompts import is_challenge_turn

        assert is_challenge_turn("Is that correct?") is False
        assert is_challenge_turn("We are exempt, correct?") is True

    def test_live_turn_doctrine_preserved(self) -> None:
        """Only the text after the flatten marker is scanned (R60.1 / R71)."""
        from app.data.graph_rag_prompts import is_challenge_turn

        flattened = (
            "Conversation so far:\nUser: So we are exempt, correct?\n"
            "Assistant: No.\n\nLatest question:\nWhat are the logging duties?"
        )
        assert is_challenge_turn(flattened) is False

    def test_every_call_site_is_turn_gated(self) -> None:
        """R377 closed the last ungated call.

        A challenge needs a previous answer to dispute. R376 review finding #4
        gated the Stage-2 request builder after the widened markers were shown to
        fire on a FIRST turn; the curated-skip exemption was left behind, so route
        and engine could disagree about whether a turn is a challenge.
        """
        import inspect

        from app.engines import _graph_rag_impl as impl

        src = inspect.getsource(impl._two_stage_generate)
        assert "_challenge_exempt = is_challenge_turn(question)" not in src
        assert "(history_turn_count or 1) > 1" in src


# ─── R377-F ──────────────────────────────────────────────────────────────────


class TestR377FJudgeReasoningEnvelope:
    """A reasoning judge's hidden tokens are billed inside ``max_tokens``.

    MEASURED LIVE, anthropic/claude-sonnet-5 on OpenRouter, one realistic judge
    prompt::

        max_tokens= 400  reasoning=322  content= 249  -> unbalanced_json
        max_tokens= 800  reasoning=799  content=   0  -> empty_response
        max_tokens=1600  reasoning=728  content=1301  -> ok, barely

    A 30-row x 4-axis run at the shipped 1600 produced 8 ``empty_response`` and
    1 ``unbalanced_json`` on the correctness axis. ``pass_rate`` divides by TOTAL
    rows, so those nine unscored rows read as nine non-passes: 0.600 reported
    against a usable 18/21 = 0.857. Re-run with the additive envelope: errors
    9 -> 1, correctness 0.600 -> 0.800.
    """

    def test_headroom_default_is_additive(self) -> None:
        from evals.judge.runner import _judge_max_tokens, _judge_reasoning_headroom

        assert _judge_reasoning_headroom() == 2048
        assert _judge_max_tokens() + _judge_reasoning_headroom() > _judge_max_tokens()

    def test_headroom_clears_the_measured_reasoning_range(self) -> None:
        """Measured reasoning on real judge prompts ranged 265-799 tokens."""
        from evals.judge.runner import _judge_reasoning_headroom

        assert _judge_reasoning_headroom() >= 800

    def test_off_switch_restores_the_pre_r377_envelope(self, monkeypatch) -> None:
        from evals.judge.runner import _judge_max_tokens, _judge_reasoning_headroom

        monkeypatch.setenv("REGENOLD_JUDGE_REASONING_HEADROOM", "0")
        assert _judge_reasoning_headroom() == 0
        assert _judge_max_tokens() + _judge_reasoning_headroom() == _judge_max_tokens()

    def test_malformed_value_falls_back_to_the_default(self, monkeypatch) -> None:
        from evals.judge.runner import _judge_reasoning_headroom

        monkeypatch.setenv("REGENOLD_JUDGE_REASONING_HEADROOM", "not-a-number")
        assert _judge_reasoning_headroom() == 2048

    def test_only_the_openrouter_path_is_topped_up(self) -> None:
        """The wrapper / anthropic / groq / gemini paths keep the plain ceiling.

        Bedrock has its own budget (``REGENOLD_BEDROCK_JUDGE_MAX_TOKENS``) and
        sends no thinking by default, so it never spent the envelope on hidden
        reasoning.
        """
        import inspect

        from evals.judge import runner as JR

        assert "_judge_reasoning_headroom()" in inspect.getsource(JR._call_judge_openrouter)
        for fn in (JR._call_judge_sonnet, JR._call_judge_anthropic, JR._call_judge_bedrock):
            assert "_judge_reasoning_headroom()" not in inspect.getsource(fn)


# ─── R377-G ──────────────────────────────────────────────────────────────────


class TestR377GDenoiserFallbackChain:
    """The multi-turn query denoiser must survive a Groq quota exhaustion.

    MEASURED LIVE with the Groq daily cap spent: Groq 429s, Gemini 2.5 Flash
    spends the 100-token rewrite budget on a hidden reasoning trace and returns
    ``finish_reason=length``, and R91 treated that as TERMINAL -- so Mistral,
    Bedrock and the wrapper never got a turn::

        {"fired": false, "fallback_reason": "truncated", "provider": "gemini"}

    The elliptical live turn then reached ``_deterministic_parse`` unresolved,
    scanned to ZERO curated keywords, and BM25 on six anaphoric words returned
    the GPAI cluster instead of Article 73.
    """

    def test_chain_is_exactly_groq_then_bedrock(self) -> None:
        """Operator directive 2026-08-23: Groq primary, Bedrock fallback.

        Gemini 2.5 Flash is a reasoning model that truncated the 100-token
        rewrite on every measured call, and under R91 truncation was TERMINAL --
        so it did not merely fail, it starved every provider behind it. The
        wrapper candidate is the ~10 s Claude Max tunnel, which the 3 s
        per-provider fail-fast can never beat.
        """
        import inspect

        from app.routes import regenold as R

        src = inspect.getsource(R._rewrite_multiturn_query)
        assert '"groq",' in src
        assert '"bedrock",' in src
        assert src.index('"groq",') < src.index('"bedrock",')
        for dropped in ('"gemini",', '"mistral",', '"wrapper",'):
            assert dropped not in src, f"{dropped} is back in the denoiser chain"

    def test_bedrock_adapter_maps_the_request_and_uses_fallback(self) -> None:
        """It must call complete_with_fallback so a 403 is paid once per TTL."""
        import inspect

        from app.routes.regenold import _BedrockDenoiserProvider

        src = inspect.getsource(_BedrockDenoiserProvider)
        assert "complete_with_fallback" in src
        assert "BedrockRequest" in src

    def test_truncation_falls_through_instead_of_ending_the_chain(self) -> None:
        import inspect

        from app.routes import regenold as R

        src = inspect.getsource(R._rewrite_multiturn_query)
        trunc = src.index('finish_reason", None) == "length"')
        tail = src[trunc:trunc + 2600]
        # The fall-through must precede the terminal salvage.
        assert "_denoiser_truncation_fallthrough_enabled()" in tail
        assert tail.index("continue") < tail.index('_salvage_on_provider_failure(\n                    "truncated"')

    def test_gates_default_on_and_are_read_fresh(self, monkeypatch) -> None:
        from app.routes.regenold import (
            _denoiser_bedrock_enabled,
            _denoiser_truncation_fallthrough_enabled,
        )

        assert _denoiser_bedrock_enabled() is True
        assert _denoiser_truncation_fallthrough_enabled() is True
        monkeypatch.setenv("REGENOLD_DENOISER_BEDROCK", "0")
        monkeypatch.setenv("REGENOLD_DENOISER_TRUNCATION_FALLTHROUGH", "0")
        assert _denoiser_bedrock_enabled() is False
        assert _denoiser_truncation_fallthrough_enabled() is False

    def test_r91_intent_preserved_a_truncated_rewrite_is_never_used(self) -> None:
        """Falling through must not make a truncated rewrite usable."""
        import inspect

        from app.routes import regenold as R

        src = inspect.getsource(R._rewrite_multiturn_query)
        trunc = src.index('finish_reason", None) == "length"')
        # `rewritten` is only computed AFTER the truncation branch.
        assert src.index("rewritten = resp.text.strip()") > trunc
