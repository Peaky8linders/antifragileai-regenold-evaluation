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
