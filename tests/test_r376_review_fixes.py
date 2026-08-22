"""R376 review — regression tests for the defects an adversarial pass found.

Each test below pins a defect that shipped in R376's own first cut and was
caught by reviewing that change rather than by a failing test. They are grouped
here rather than scattered so the review's findings stay traceable to the code
that answers them.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engines import _graph_rag_impl as impl  # noqa: E402
from scripts.e2e_provider_mocks import MockBedrock, MockOpenRouter  # noqa: E402


class TestThinkingBudgetDoesNotEatTheAnswer:
    """The budget counts INSIDE max_tokens, so it must be added on top.

    R328.3 records the worst measured enumerative Stage-2 answer at 3411
    tokens. The first cut of the Bedrock thinking wiring left the answer 2048 —
    those would return ``stopReason=max_tokens``, be rejected by the R328.3
    guard, roll through every tier, and drop Stage-2 entirely, re-arming
    ``MAX_ANSWER_SENTENCES = 3``. A false truncation costs the answer twice.

    The same shape was wrong on the OpenRouter path since R373: both compute a
    ``max(...)`` against a ceiling that is already 4096, so ``2048 + 2048``
    changed nothing. Asserting ``maxTokens > budget`` cannot catch it — the
    assertion is on the ENVELOPE.
    """

    WORST_MEASURED_ANSWER_TOKENS = 3411

    def test_bedrock_complex_answer_keeps_its_full_envelope(self, monkeypatch):
        from app.llm.bedrock_client import _reset_bedrock_singletons_for_tests

        server = MockBedrock().start()
        try:
            monkeypatch.setenv("AWS_ENDPOINT_URL_BEDROCK_RUNTIME", server.endpoint_url)
            monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATESTTESTTEST")
            monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
            monkeypatch.delenv("AWS_BEARER_TOKEN_BEDROCK", raising=False)
            monkeypatch.setenv("AWS_REGION", "eu-central-1")
            monkeypatch.setenv("BEDROCK_REGION", "eu-central-1")
            _reset_bedrock_singletons_for_tests()

            assert impl._bedrock_complete_for_graph_rag(
                system="s", user="u", max_tokens=1536, temperature=0.0,
                complex_question=True, stage_name="Stage 2 (Polishing)",
            )
            body = server.calls[0]["body"]
            budget = body["additionalModelRequestFields"]["reasoning_config"][
                "budget_tokens"
            ]
            envelope = body["inferenceConfig"]["maxTokens"] - budget
            assert envelope >= self.WORST_MEASURED_ANSWER_TOKENS, (
                f"answer envelope {envelope} < worst measured answer "
                f"{self.WORST_MEASURED_ANSWER_TOKENS}"
            )
        finally:
            server.stop()
            _reset_bedrock_singletons_for_tests()

    def test_openrouter_complex_answer_keeps_its_full_envelope(self, monkeypatch):
        from app.llm.openai_wrapper_provider import (
            _reset_openrouter_singleton_for_tests,
        )

        server = MockOpenRouter().start()
        try:
            monkeypatch.setenv("OPENROUTER_API_BASE", server.base_url)
            monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
            _reset_openrouter_singleton_for_tests()

            assert impl._openrouter_complete_for_graph_rag(
                system="s", user="u", max_tokens=1536, temperature=0.0,
                complex_question=True, stage_name="Stage 2 (Polishing)",
            )
            body = server.calls[0]["body"]
            budget = (body.get("reasoning") or {}).get("max_tokens", 0)
            assert budget == 2048
            envelope = body["max_tokens"] - budget
            assert envelope >= self.WORST_MEASURED_ANSWER_TOKENS
        finally:
            server.stop()
            _reset_openrouter_singleton_for_tests()

    def test_the_two_providers_give_the_same_question_the_same_room(
        self, monkeypatch
    ):
        """A cross-provider fallback must not silently halve the answer budget."""
        from app.llm.bedrock_client import _reset_bedrock_singletons_for_tests
        from app.llm.openai_wrapper_provider import (
            _reset_openrouter_singleton_for_tests,
        )

        br, orm = MockBedrock().start(), MockOpenRouter().start()
        try:
            monkeypatch.setenv("AWS_ENDPOINT_URL_BEDROCK_RUNTIME", br.endpoint_url)
            monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATESTTESTTEST")
            monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
            monkeypatch.delenv("AWS_BEARER_TOKEN_BEDROCK", raising=False)
            monkeypatch.setenv("AWS_REGION", "eu-central-1")
            monkeypatch.setenv("BEDROCK_REGION", "eu-central-1")
            monkeypatch.setenv("OPENROUTER_API_BASE", orm.base_url)
            monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
            _reset_bedrock_singletons_for_tests()
            _reset_openrouter_singleton_for_tests()

            kw = dict(system="s", user="u", max_tokens=1536, temperature=0.0,
                      complex_question=True, stage_name="Stage 2 (Polishing)")
            impl._bedrock_complete_for_graph_rag(**kw)
            impl._openrouter_complete_for_graph_rag(**kw)

            b = br.calls[0]["body"]
            b_env = b["inferenceConfig"]["maxTokens"] - b[
                "additionalModelRequestFields"]["reasoning_config"]["budget_tokens"]
            o = orm.calls[0]["body"]
            o_env = o["max_tokens"] - (o.get("reasoning") or {})["max_tokens"]
            assert b_env == o_env
        finally:
            br.stop()
            orm.stop()
            _reset_bedrock_singletons_for_tests()
            _reset_openrouter_singleton_for_tests()


class TestGatekeeperQualifierPrecision:
    """Article 5(1)(h) prohibits REAL-TIME remote biometric identification.

    Post (ex-post) RBI is not an Article 5 prohibition — it is governed by
    Article 26(10). The keyword "remote biometric identification" matches both,
    so the scan produced the real-time verdict for a question about post RBI.
    Harmless while any mention of "Article 5" suppressed the verdict; the R376
    contradiction guard removes that accidental suppression, which would have
    promoted the wrong verdict to the answer's lead.
    """

    @pytest.mark.parametrize(
        "question",
        [
            "Can law enforcement use post-remote biometric identification for a targeted search?",
            "Is ex-post remote biometric identification allowed?",
            "Can we do retrospective remote biometric identification of CCTV footage?",
            "Is post-hoc remote biometric identification permitted?",
        ],
    )
    def test_post_rbi_does_not_match_the_realtime_prohibition(self, question):
        from app.engines.prohibited_gatekeeper import scan_for_prohibitions

        subs = [sub for _parent, sub in scan_for_prohibitions(question)]
        assert "Art. 5.1.h" not in subs

    @pytest.mark.parametrize(
        "question",
        [
            "Can police use real-time remote biometric identification in public spaces?",
            # A question COMPARING the two regimes is asking about both, so the
            # Article 5 anchor is kept.
            "How does real-time remote biometric identification differ from post-remote use?",
        ],
    )
    def test_realtime_rbi_still_matches(self, question):
        from app.engines.prohibited_gatekeeper import scan_for_prohibitions

        subs = [sub for _parent, sub in scan_for_prohibitions(question)]
        assert "Art. 5.1.h" in subs

    @pytest.mark.parametrize(
        "question",
        [
            "Can we use emotion recognition on employees?",
            "Is social scoring by a public authority allowed?",
        ],
    )
    def test_other_practices_are_untouched(self, question):
        from app.engines.prohibited_gatekeeper import scan_for_prohibitions

        assert scan_for_prohibitions(question)


class TestChallengeNeedsAPreviousAnswer:
    """A first turn cannot be disputing anything.

    The widened marker set improved recall on real pushback and, with it, a
    first turn merely CONTAINING "I disagree" matched — which would have told
    the model it was disputing a previous answer that does not exist and forced
    the complex tier on an ordinary opening question.
    """

    FIRST_TURN = (
        "Our vendor says the model is exempt and I disagree - is our "
        "CV-screening tool high-risk under the AI Act?"
    )

    def test_marker_still_matches_the_raw_text(self):
        """The detector is unchanged; the TURN COUNT is what gates it."""
        from app.data.graph_rag_prompts import is_challenge_turn

        assert is_challenge_turn(self.FIRST_TURN) is True

    def test_first_turn_is_not_treated_as_a_challenge(self, monkeypatch):
        from app.llm.openai_wrapper_provider import (
            _reset_openrouter_singleton_for_tests,
        )

        server = MockOpenRouter().start()
        try:
            monkeypatch.setenv("OPENROUTER_API_BASE", server.base_url)
            monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
            monkeypatch.setenv("P2P_GRAPH_RAG_PROVIDER", "openrouter")
            monkeypatch.setenv("REGENOLD_GRAPH_BACKEND", "neo4j")
            _reset_openrouter_singleton_for_tests()

            from fastapi.testclient import TestClient

            import app.main as main_mod
            from app.routes import regenold as regenold_route

            regenold_route._ENGINE_CACHE.clear()
            client = TestClient(main_mod.app)
            resp = client.post(
                "/api/v1/regenold/eu-ai-act/ask",
                json={"messages": [{"role": "user", "content": self.FIRST_TURN}]},
            )
            assert resp.status_code == 200
            assert server.calls
            body = server.calls[0]["body"]
            user = next(
                m["content"] for m in body["messages"] if m["role"] == "user"
            )
            assert "This turn disputes your previous answer" not in user
            assert "THE USER IS DISPUTING" not in user
            # An ordinary opening question must not be forced to the complex
            # tier by a stray marker.
            assert body["model"] == "anthropic/claude-sonnet-5"
            assert body.get("reasoning") is None
        finally:
            server.stop()
            _reset_openrouter_singleton_for_tests()


class TestFallbackProbeNamesAReachableProvider:
    """``is_openai_wrapper_enabled()`` is not a readiness check.

    It returns True for every provider except ``cli``, so using it made the
    "no fallback configured" branch unreachable and a keyless, providerless
    deploy POST to the wrapper's default host on every request.
    """

    def test_no_configured_provider_reports_none(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_BASE", raising=False)
        monkeypatch.setattr(
            "app.llm.bedrock_client.is_bedrock_provider_enabled", lambda: False
        )
        assert impl._stage2_fallback_provider_available() is None

    def test_bedrock_is_reported_when_configured(self, monkeypatch):
        monkeypatch.setattr(
            "app.llm.bedrock_client.is_bedrock_provider_enabled", lambda: True
        )
        assert impl._stage2_fallback_provider_available() == "bedrock"

    def test_wrapper_needs_an_explicit_endpoint(self, monkeypatch):
        monkeypatch.setattr(
            "app.llm.bedrock_client.is_bedrock_provider_enabled", lambda: False
        )
        monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")
        monkeypatch.setenv("P2P_GRAPH_RAG_PROVIDER", "openrouter")
        assert impl._stage2_fallback_provider_available() == "openai_wrapper"

    def test_stage2_is_off_when_nothing_can_serve(self, monkeypatch):
        monkeypatch.setenv("P2P_GRAPH_RAG_PROVIDER", "openrouter")
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_BASE", raising=False)
        monkeypatch.setattr(
            "app.llm.bedrock_client.is_bedrock_provider_enabled", lambda: False
        )
        assert impl._stage2_provider_enabled() is False


class TestMirrorProvenanceIsReadNotInferred:
    def test_source_reflects_where_the_rows_came_from(self, monkeypatch):
        """A reachable instance with no HAS_PARAGRAPH edges must NOT read as "graph"."""
        from app.engines import kg_context as kg

        class ReachableButUnseeded:
            enabled = True

            def execute_read_strict(self, cypher, params=None):
                return []

            def execute_read(self, *_a, **_kw):
                return []

        monkeypatch.setattr(
            "app.graph.client.get_graph_client", lambda: ReachableButUnseeded()
        )
        monkeypatch.setattr("app.graph.timeouts.graph_circuit_open", lambda: False)
        monkeypatch.setattr("app.graph.timeouts.record_graph_failure", lambda: None)
        monkeypatch.setattr("app.graph.timeouts.record_graph_success", lambda: None)
        monkeypatch.setenv("REGENOLD_KG_LOCAL_MIRROR", "1")
        monkeypatch.setenv("REGENOLD_GRAPH_BACKEND", "neo4j")
        kg.reset_kg_context_memo()

        assert kg.fetch_provision_hierarchy(["Art. 9"])
        assert kg.last_hierarchy_source() == "local_mirror"
