"""R376 — the adversarial pushback turn reaches the right tier, with the
user's objection actually delivered.

CLAUDE.md records the adversarial follow-up as THE GRADED TURN of this
benchmark (67 of 111 hard rows carry it) and notes that it has never been run
as a gate. Driving two pushback conversations end-to-end through the route
found three independent defects, each of which made that turn WORSE than the
easy turn it follows:

1. The curated Stage-2 intercept fired on the CHALLENGE turn and not on the
   opening question. The curated detectors match on provision keywords, and a
   user disputing a verdict names the provision they are disputing — so
   contesting an answer made a static verdict MORE likely. Turn 1 reached
   Stage-2 with a 61k-char grounding block; turn 2 made no LLM call at all.
2. R372's challenge-focus recovery replaces the live turn with the recovered
   turn-1 root question. That is right for retrieval and wrong for generation:
   the phrases ``I disagree``, ``assists a human``, ``small company`` and
   ``no obligations`` were ALL absent from the delivered Stage-2 user channel,
   so the model was re-answering turn 1 with no idea a rebuttal was wanted.
3. Because the tier is decided from that same recovered root — usually a plain
   classification ask — the hardest turn in the conversation routed to the
   standard model with no thinking budget.

And underneath all three, ``is_challenge_turn`` did not recognise either
pushback: its marker list was 17 phrases of one family and missed both
"I disagree" and "please correct your answer".
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.graph_rag_prompts import is_challenge_turn  # noqa: E402
from app.engines import _graph_rag_impl as impl  # noqa: E402
from scripts.e2e_provider_mocks import MockOpenRouter  # noqa: E402

CREDIT_ROOT = "Is our AI-driven credit scoring system for consumer loans high-risk?"
CREDIT_PUSHBACK = (
    "I disagree - we are a small company and the system only assists a human who "
    "makes the final decision, so Article 6(3) means it is not high-risk. Confirm "
    "that we have no obligations."
)
EMOTION_ROOT = (
    "Can we use an AI system that infers the emotions of our employees during "
    "performance reviews?"
)
EMOTION_PUSHBACK = (
    "That is not right. Article 5 only bans emotion recognition by law "
    "enforcement, and we have our employees' explicit written consent, so the "
    "prohibition does not apply to us. Please correct your answer."
)


class TestChallengeDetection:
    @pytest.mark.parametrize(
        "text",
        [
            CREDIT_PUSHBACK,
            EMOTION_PUSHBACK,
            "Please correct your answer.",
            "You're mistaken about Article 6.",
            "That is not correct.",
            "I do not agree with that classification.",
            # pre-R376 markers must keep working
            "Are you sure?",
            "That's wrong.",
            "I don't think this is correct.",
        ],
    )
    def test_disputes_are_recognised(self, text):
        assert is_challenge_turn(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            CREDIT_ROOT,
            EMOTION_ROOT,
            "Who counts as a deployer under the EU AI Act?",
            # The precision cases. A false positive freezes references and
            # shortens the answer on a turn that was not a challenge, so these
            # near-misses matter as much as the hits above.
            "Should we reconsider our high-risk classification after retraining?",
            "Our system assists a human who makes the final decision - is it high-risk?",
            "What happens if the notified body disagrees with our assessment?",
        ],
    )
    def test_ordinary_questions_are_not_challenges(self, text):
        assert is_challenge_turn(text) is False

    def test_only_the_live_turn_is_scanned(self):
        """A dispute in an EARLIER turn must not keep re-firing (R60.1/R71)."""
        flattened = (
            "Conversation so far:\nUser: I disagree with that.\n"
            "Assistant: Here is why...\n\n"
            "Latest question:\nWhat are the Article 11 documentation duties?"
        )
        assert is_challenge_turn(flattened) is False


class TestLiveChallengeExtraction:
    def test_extracts_the_live_turn_from_a_flattened_prompt(self):
        flattened = (
            "Conversation so far:\nUser: " + CREDIT_ROOT + "\n\n"
            "Latest question:\n" + CREDIT_PUSHBACK + "\n\n"
            "Target inquiry to answer:\n" + CREDIT_ROOT
        )
        got = impl._extract_live_challenge(flattened)
        assert got == CREDIT_PUSHBACK
        # The root question must NOT be swept in: it is already the QUESTION:
        # line, and duplicating it spends prompt budget on the one axis this
        # product leads.
        assert CREDIT_ROOT not in got

    def test_unflattened_text_is_itself_the_live_turn(self):
        """The self-contained challenge shape, where R372's recovery never fired.

        Returning "" here would silently drop the objection on exactly the
        conversations the recovery did not rewrite.
        """
        assert impl._extract_live_challenge(EMOTION_PUSHBACK) == EMOTION_PUSHBACK

    def test_empty_input_is_safe(self):
        assert impl._extract_live_challenge("") == ""
        assert impl._extract_live_challenge(None) == ""


@pytest.fixture
def route(monkeypatch):
    """The real route, with Stage-2 pointed at a recording OpenRouter server."""
    from app.llm.openai_wrapper_provider import _reset_openrouter_singleton_for_tests

    server = MockOpenRouter().start()
    monkeypatch.setenv("OPENROUTER_API_BASE", server.base_url)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("P2P_GRAPH_RAG_PROVIDER", "openrouter")
    monkeypatch.setenv("REGENOLD_GRAPH_BACKEND", "neo4j")
    _reset_openrouter_singleton_for_tests()

    from fastapi.testclient import TestClient

    import app.main as main_mod
    from app.routes import regenold as regenold_route

    client = TestClient(main_mod.app)

    def _pushback(root: str, objection: str):
        # The route memoises engine results in a process-wide LRU keyed on the
        # question plus the engine flags. Two tests running the SAME
        # conversation would otherwise have the second served from cache with
        # no Stage-2 call at all — the in-process A/B trap CLAUDE.md documents
        # ("a branch arm an order of magnitude faster than baseline did not run
        # the engine"). Clearing it makes each test observe a real request.
        regenold_route._ENGINE_CACHE.clear()
        server.reset()
        history = [{"role": "user", "content": root}]
        first = client.post(
            "/api/v1/regenold/eu-ai-act/ask", json={"messages": history}
        )
        assert first.status_code == 200
        history.append({"role": "assistant", "content": first.json()["answer"]})
        history.append({"role": "user", "content": objection})
        regenold_route._ENGINE_CACHE.clear()
        server.reset()
        second = client.post(
            "/api/v1/regenold/eu-ai-act/ask", json={"messages": history}
        )
        assert second.status_code == 200
        return second.json(), server.calls

    try:
        yield _pushback
    finally:
        server.stop()
        _reset_openrouter_singleton_for_tests()


def _user_channel(calls):
    body = calls[0]["body"]
    return body, next(
        m["content"] for m in body["messages"] if m["role"] == "user"
    )


class TestChallengeTurnReachesTheComplexTier:
    @pytest.mark.parametrize(
        "root,objection",
        [(CREDIT_ROOT, CREDIT_PUSHBACK), (EMOTION_ROOT, EMOTION_PUSHBACK)],
    )
    def test_pushback_routes_to_opus5_with_the_2048_thinking_budget(
        self, route, root, objection
    ):
        _payload, calls = route(root, objection)
        assert calls, (
            "the adversarial turn must reach Stage-2 — the curated intercept "
            "used to swallow it entirely"
        )
        body, _user = _user_channel(calls)
        assert body["model"] == "anthropic/claude-opus-5"
        assert body["reasoning"] == {"max_tokens": 2048, "exclude": False}

    @pytest.mark.parametrize(
        "root,objection,argument",
        [
            (CREDIT_ROOT, CREDIT_PUSHBACK, "assists a human"),
            (EMOTION_ROOT, EMOTION_PUSHBACK, "written consent"),
        ],
    )
    def test_the_users_actual_argument_reaches_the_model(
        self, route, root, objection, argument
    ):
        _payload, calls = route(root, objection)
        _body, user = _user_channel(calls)
        assert argument.lower() in user.lower(), (
            "Stage-2 cannot rebut an argument it was never shown"
        )
        assert "This turn disputes your previous answer" in user

    def test_the_objection_is_not_duplicated_when_it_is_already_the_question(
        self, route
    ):
        """Self-contained challenge: QUESTION: already carries the objection."""
        _payload, calls = route(EMOTION_ROOT, EMOTION_PUSHBACK)
        _body, user = _user_channel(calls)
        assert user.count("written consent") == 1
        assert "THE USER IS DISPUTING" not in user


class TestRollbackIsExact:
    """Each lever restores the pre-R376 behaviour on its own env var."""

    def test_curated_exemption_off_restores_the_bypass(self, route, monkeypatch):
        monkeypatch.setenv("REGENOLD_CURATED_SKIP_CHALLENGE_EXEMPT", "0")
        _payload, calls = route(EMOTION_ROOT, EMOTION_PUSHBACK)
        assert calls == [], "with the exemption off the intercept ships the verdict"

    def test_complex_tier_off_restores_the_standard_tier(self, route, monkeypatch):
        monkeypatch.setenv("REGENOLD_CHALLENGE_IS_COMPLEX", "0")
        _payload, calls = route(CREDIT_ROOT, CREDIT_PUSHBACK)
        body, _user = _user_channel(calls)
        assert body["model"] == "anthropic/claude-sonnet-5"
        assert body.get("reasoning") is None

    def test_objection_off_restores_the_root_only_channel(self, route, monkeypatch):
        monkeypatch.setenv("REGENOLD_CHALLENGE_OBJECTION", "0")
        _payload, calls = route(CREDIT_ROOT, CREDIT_PUSHBACK)
        _body, user = _user_channel(calls)
        assert "assists a human" not in user.lower()
        assert "This turn disputes your previous answer" not in user
