"""R91 — LLM truncation guard regression tests.

Three call sites silently shipped length-truncated LLM output as
"successful" before R91:

1. ``OpenAIWrapperResponse`` had no ``finish_reason`` field, so the
   chat-completion ``finish_reason="length"`` signal never crossed
   the provider boundary.
2. ``_rewrite_multiturn_query`` (``max_tokens=100``) accepted any
   non-empty rewrite passing the ``10 < len <= 500`` sanity bounds
   — a mid-sentence cut became the retrieval query.
3. ``_claude_max_enhance_answer`` returned the polished text on a
   non-empty ``validate_llm_output`` result, setting
   ``stage2_landed=True`` even when the polish was truncated. That
   in turn triggered the R72 ``_reconcile_references_to_prose``
   pass to PRUNE references not described in the (truncated, partial)
   prose — silently dropping valid citations.

R91 captures ``finish_reason`` on the response model, treats
``"length"`` as a soft failure in the wrapper graph-RAG helper +
denoiser, and mirrors the signal via the Anthropic SDK's
``stop_reason="max_tokens"`` on the SDK direct path.

These tests lock in the contract — the fail-soft envelope is
preserved (no exception raised; the caller falls back to the
deterministic path).

⚠ R377 (operator directive 2026-08-23) rewired the denoiser chain from
``Groq -> Gemini -> Mistral -> Claude-Max wrapper`` to ``Groq ->
Bedrock``, so the section-2 rows below now drive the denoiser through
the GROQ (primary) and BEDROCK (fallback) links instead of the deleted
wrapper candidate. R377 also made the truncation bail NON-TERMINAL: a
``finish_reason="length"`` response falls through to the next candidate
instead of ending the chain. **R91's property is unchanged and is what
these rows still pin — a truncated rewrite is never USED.** When every
candidate truncates the end state is byte-identical to R91's terminal
bail. Sections 1, 3 and 4 are untouched: they exercise the wrapper
response model and the ``graph_rag`` Stage-2 helpers, neither of which
the denoiser chain change touches.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest


# ─── 1. Wrapper response carries finish_reason ────────────────────────────


class TestOpenAIWrapperFinishReasonCaptured:
    def test_finish_reason_length_propagated(self) -> None:
        """The chat-completion ``finish_reason`` lands on the response."""
        from app.llm.openai_wrapper_provider import (
            OpenAIWrapperRequest,
            _OpenAIWrapperProvider,
        )

        def _handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "model": "claude-sonnet-4-6",
                    "choices": [
                        {
                            "message": {"content": "Partial text…"},
                            "finish_reason": "length",
                        }
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 100},
                },
            )

        provider = _OpenAIWrapperProvider()
        provider._client = httpx.Client(
            transport=httpx.MockTransport(_handler),
            base_url="https://api.wrapper.test",
        )
        result = provider.complete(OpenAIWrapperRequest(user="ping"))
        assert result.error is None
        assert result.text == "Partial text…"
        assert result.finish_reason == "length"

    def test_finish_reason_stop_propagated(self) -> None:
        """Natural completion returns ``finish_reason="stop"``."""
        from app.llm.openai_wrapper_provider import (
            OpenAIWrapperRequest,
            _OpenAIWrapperProvider,
        )

        def _handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "model": "claude-sonnet-4-6",
                    "choices": [
                        {
                            "message": {"content": "Done."},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                },
            )

        provider = _OpenAIWrapperProvider()
        provider._client = httpx.Client(
            transport=httpx.MockTransport(_handler),
            base_url="https://api.wrapper.test",
        )
        result = provider.complete(OpenAIWrapperRequest(user="ping"))
        assert result.finish_reason == "stop"

    def test_finish_reason_missing_is_none(self) -> None:
        """When upstream omits ``finish_reason`` it stays None."""
        from app.llm.openai_wrapper_provider import (
            OpenAIWrapperRequest,
            _OpenAIWrapperProvider,
        )

        def _handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "model": "claude-sonnet-4-6",
                    "choices": [{"message": {"content": "ok"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                },
            )

        provider = _OpenAIWrapperProvider()
        provider._client = httpx.Client(
            transport=httpx.MockTransport(_handler),
            base_url="https://api.wrapper.test",
        )
        result = provider.complete(OpenAIWrapperRequest(user="ping"))
        assert result.finish_reason is None


# ─── 2. _rewrite_multiturn_query bails on truncation ──────────────────────


def _mk_msg(role: str, content: str):
    """Mirror the route's message shape (has .role + .content attrs)."""
    m = MagicMock()
    m.role = role
    m.content = content
    return m


def _mk_resp(text: str, finish_reason: str | None):
    """A provider response carrying just what the denoiser reads."""
    resp = MagicMock()
    resp.error = None
    resp.text = text
    resp.finish_reason = finish_reason
    return resp


def _wire_groq_candidate(monkeypatch: pytest.MonkeyPatch, provider) -> None:
    """R377 — make ``provider`` the chain's PRIMARY (Groq) link.

    ``_rewrite_multiturn_query`` imports both names function-locally from
    ``app.llm.openai_wrapper_provider``, so the module attribute is the
    seam. Patching the ENABLE gate as well as the getter is deliberate:
    ``conftest`` scrubs ``GROQ_API_KEY``, so patching only the getter
    would leave the candidate off the chain and the mock unconsulted —
    the vacuity the R339 note below is about.
    """
    monkeypatch.setattr(
        "app.llm.openai_wrapper_provider.is_groq_intent_provider_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "app.llm.openai_wrapper_provider.get_groq_intent_provider",
        lambda: provider,
    )


def _wire_bedrock_candidate(monkeypatch: pytest.MonkeyPatch, provider) -> None:
    """R377 — make ``provider`` the chain's FALLBACK (Bedrock) link.

    Two seams, mirroring the route: the credential gate
    (``app.llm.bedrock_client.is_bedrock_provider_enabled``, imported
    function-locally) and the adapter class itself, which the route
    instantiates by name off its own module.
    """
    monkeypatch.setenv("REGENOLD_DENOISER_BEDROCK", "1")
    monkeypatch.setattr(
        "app.llm.bedrock_client.is_bedrock_provider_enabled", lambda: True
    )
    monkeypatch.setattr(
        "app.routes.regenold._BedrockDenoiserProvider", lambda: provider
    )


@pytest.fixture
def denoiser_trace():
    """Activate a fresh ReasoningTrace so ``record_query_denoiser`` lands.

    R87-A wires every de-noiser exit path through the trace; without an
    active trace ``record_query_denoiser`` is a no-op, so a row that wants
    to read ``fallback_reason`` must activate one.
    """
    from app.integrations.regenold import reasoning_trace as rt

    t = rt.activate()
    yield t
    rt.deactivate()


class TestRewriteMultiturnQueryTruncation:
    @pytest.fixture(autouse=True)
    def _denoiser_candidate_reachable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """R339 — pin the chain shape ABOVE the mocked seam these rows patch.

        ``_rewrite_multiturn_query`` (``app/routes/regenold.py``) builds a
        provider CHAIN and only appends a candidate when that candidate's
        ENABLE gate says so. These rows used to patch only
        ``get_openai_wrapper_provider``, one layer BELOW
        ``is_openai_wrapper_enabled()``, so under the documented
        deterministic gate the chain came back empty,
        ``_rewrite_multiturn_query`` bailed with ``fallback_reason=
        "no_provider"`` and the mock was never consulted.

        That made ``test_truncated_response_returns_none`` pass VACUOUSLY —
        it asserts ``out is None``, which the empty chain satisfies without
        ever reaching the truncation guard it exists to pin. Hence the
        ``complete.assert_called_once()`` guards below: the rows must fail
        if they ever regress to the vacuous path again. ``_wire_groq_
        candidate`` / ``_wire_bedrock_candidate`` patch the gate AND the
        getter for exactly that reason.

        ⚠ R377 — the chain is now ``Groq -> Bedrock``; the Gemini, Mistral
        and Claude-Max-wrapper candidates were DELETED, so the old
        ``P2P_GRAPH_RAG_PROVIDER=openai_wrapper`` pin no longer makes any
        candidate reachable. The rows below drive the PRIMARY link
        (Groq) — the same single-candidate shape the wrapper row had, so
        R91's contract is pinned unchanged — and one row drives the
        truncation guard across BOTH links.

        Bedrock is pinned OFF here so the default is a one-candidate
        chain; the fall-through row re-enables it explicitly. The
        truncation fall-through is pinned to its CODE default (ON) so an
        exported ``REGENOLD_DENOISER_TRUNCATION_FALLTHROUGH=0`` — the
        documented R91 rollback — cannot silently change what these rows
        measure. ⚠ Pinning a gate ON is only safe if something still
        exercises it OFF, or the rollback branch becomes dead code that no
        mutation can fail: ``test_fallthrough_disabled_restores_r91_
        terminal_bail`` overrides this setenv and owns that branch.
        Nothing reaches the network — ``conftest`` scrubs every provider
        credential and the providers themselves are ``MagicMock``s.
        """
        monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
        monkeypatch.delenv("REGENOLD_INTENT_PROVIDER", raising=False)
        monkeypatch.setenv("REGENOLD_DENOISER_BEDROCK", "0")
        monkeypatch.setenv("REGENOLD_DENOISER_TRUNCATION_FALLTHROUGH", "1")

    def test_truncated_response_returns_none(self, monkeypatch) -> None:
        """``finish_reason="length"`` with non-empty text → return None
        even though the text would otherwise pass the ``10 < len <= 500``
        sanity gate.

        R377 — with Bedrock pinned off (class fixture) Groq is the sole
        candidate, so the end state is byte-identical to R91's terminal
        bail. The truncated text is never used either way; what R377
        changed is only whether the CHAIN continues.
        """
        # Long enough to pass the 10 < len <= 500 sanity check.
        fake_resp = _mk_resp(
            "deployer transparency obligations under Article 26 of", "length"
        )
        fake_provider = MagicMock()
        fake_provider.complete.return_value = fake_resp
        _wire_groq_candidate(monkeypatch, fake_provider)

        from app.routes.regenold import _rewrite_multiturn_query

        out = _rewrite_multiturn_query(
            "What about deployers?",
            [_mk_msg("user", "What is Article 13?")],
        )
        assert out is None
        # R339 non-vacuity guard — prove the None came from the truncation
        # bail and not from an empty provider chain (see the class fixture).
        fake_provider.complete.assert_called_once()

    def test_truncated_primary_never_ships_the_fallbacks_rewrite_untouched(
        self, monkeypatch
    ) -> None:
        """R377 — the truncated rewrite is still never USED, across the
        WHOLE chain.

        The old chain's fallback link (Gemini/Mistral/wrapper) is now
        Bedrock, so this is the retargeted form of "a truncated response
        does not become the retrieval query": Groq truncates, Bedrock
        answers cleanly, and the caller gets BEDROCK's text — never the
        truncated Groq fragment, and never ``None`` while a healthy
        candidate remains.
        """
        groq_resp = _mk_resp(
            "deployer transparency obligations under Article 26 of", "length"
        )
        groq_provider = MagicMock()
        groq_provider.complete.return_value = groq_resp
        bedrock_resp = _mk_resp("deployer obligations Art. 26", "stop")
        bedrock_provider = MagicMock()
        bedrock_provider.complete.return_value = bedrock_resp
        _wire_groq_candidate(monkeypatch, groq_provider)
        _wire_bedrock_candidate(monkeypatch, bedrock_provider)

        from app.routes.regenold import _rewrite_multiturn_query

        out = _rewrite_multiturn_query(
            "What about deployers?",
            [_mk_msg("user", "What is Article 13?")],
        )
        assert out == "deployer obligations Art. 26"
        groq_provider.complete.assert_called_once()
        bedrock_provider.complete.assert_called_once()

    def test_every_candidate_truncating_returns_none(
        self, monkeypatch, denoiser_trace
    ) -> None:
        """R377 — when the FALLBACK truncates too, the end state is
        byte-identical to R91's terminal bail: no rewrite reaches the
        caller. Pins that the fall-through is a chain change, not a
        loosening of the guard.

        The trace assertion is what makes "byte-identical" a MEASUREMENT
        rather than an assertion: R91's terminal bail recorded
        ``fallback_reason="truncated"``, so the exhausted chain must record
        it too. Without this the fall-through could quietly downgrade the
        outcome to the generic ``"provider_error"`` and every ``out is
        None`` row would still be green — the reason string is the only
        thing that tells R87-A's attribution WHY the rewrite was dropped.
        """
        groq_provider = MagicMock()
        groq_provider.complete.return_value = _mk_resp(
            "deployer transparency obligations under Article 26 of", "length"
        )
        bedrock_provider = MagicMock()
        bedrock_provider.complete.return_value = _mk_resp(
            "deployer transparency obligations under Article 26 of", "length"
        )
        _wire_groq_candidate(monkeypatch, groq_provider)
        _wire_bedrock_candidate(monkeypatch, bedrock_provider)

        from app.routes.regenold import _rewrite_multiturn_query

        out = _rewrite_multiturn_query(
            "What about deployers?",
            [_mk_msg("user", "What is Article 13?")],
        )
        assert out is None
        groq_provider.complete.assert_called_once()
        bedrock_provider.complete.assert_called_once()
        qd = denoiser_trace.query_denoiser
        assert qd["fired"] is False
        assert qd["fallback_reason"] == "truncated"
        # The LAST candidate to truncate is the one attributed.
        assert qd["provider"] == "bedrock"

    def test_fallthrough_disabled_restores_r91_terminal_bail(
        self, monkeypatch, denoiser_trace
    ) -> None:
        """``REGENOLD_DENOISER_TRUNCATION_FALLTHROUGH=0`` → truncation is
        TERMINAL again, exactly as R91 shipped it.

        This is the code path the pre-R377 form of
        ``test_truncated_response_returns_none`` exercised: the truncation
        branch RETURNS via ``_salvage_on_provider_failure("truncated", …)``
        instead of continuing the loop. R377 kept that branch behind a
        documented off-switch, so it is still live production behaviour and
        still needs a row — the class fixture pins the gate ON for every
        other row here, which would otherwise leave the rollback branch
        unexecuted by the whole suite (``test_r377_live_fixes`` covers it
        only with ``inspect.getsource`` string assertions).

        The discriminator is the FALLBACK provider: under the terminal bail
        Bedrock must never be consulted, even though it is wired and would
        have answered cleanly. That is the difference the gate controls, so
        it is what this row asserts.
        """
        monkeypatch.setenv("REGENOLD_DENOISER_TRUNCATION_FALLTHROUGH", "0")

        groq_provider = MagicMock()
        groq_provider.complete.return_value = _mk_resp(
            "deployer transparency obligations under Article 26 of", "length"
        )
        # Healthy fallback — if the chain continued, this text would ship.
        bedrock_provider = MagicMock()
        bedrock_provider.complete.return_value = _mk_resp(
            "deployer obligations Art. 26", "stop"
        )
        _wire_groq_candidate(monkeypatch, groq_provider)
        _wire_bedrock_candidate(monkeypatch, bedrock_provider)

        from app.routes.regenold import _rewrite_multiturn_query

        out = _rewrite_multiturn_query(
            "What about deployers?",
            [_mk_msg("user", "What is Article 13?")],
        )
        assert out is None
        groq_provider.complete.assert_called_once()
        # THE ROLLBACK'S DEFINING PROPERTY — the bail ended the chain.
        bedrock_provider.complete.assert_not_called()
        qd = denoiser_trace.query_denoiser
        assert qd["fired"] is False
        assert qd["fallback_reason"] == "truncated"
        assert qd["provider"] == "groq"

    def test_natural_stop_returns_rewritten_text(self, monkeypatch) -> None:
        """``finish_reason="stop"`` + valid text → caller gets the rewrite."""
        fake_resp = _mk_resp("deployer obligations Art. 26", "stop")
        fake_provider = MagicMock()
        fake_provider.complete.return_value = fake_resp
        _wire_groq_candidate(monkeypatch, fake_provider)

        from app.routes.regenold import _rewrite_multiturn_query

        out = _rewrite_multiturn_query(
            "What about deployers?",
            [_mk_msg("user", "What is Article 13?")],
        )
        assert out == "deployer obligations Art. 26"
        fake_provider.complete.assert_called_once()

    def test_missing_finish_reason_returns_rewritten_text(self, monkeypatch) -> None:
        """Backwards compatibility — when ``finish_reason`` is None
        (legacy responses, mocked tests without the field) the rewrite
        still flows through. Only an explicit ``"length"`` bails."""
        fake_resp = _mk_resp("deployer obligations Art. 26", None)
        fake_provider = MagicMock()
        fake_provider.complete.return_value = fake_resp
        _wire_groq_candidate(monkeypatch, fake_provider)

        from app.routes.regenold import _rewrite_multiturn_query

        out = _rewrite_multiturn_query(
            "What about deployers?",
            [_mk_msg("user", "What is Article 13?")],
        )
        assert out == "deployer obligations Art. 26"
        fake_provider.complete.assert_called_once()


# ─── 3. Wrapper graph-RAG helper bails on truncation ──────────────────────


class TestOpenAIWrapperCompleteForGraphRagTruncation:
    def test_wrapper_truncated_returns_none(self, monkeypatch) -> None:
        """``_openai_wrapper_complete_for_graph_rag`` raises RuntimeError when
        the underlying wrapper response carries ``finish_reason="length"``.
        The exception propagates to ``_claude_max_enhance_answer`` →
        ``_two_stage_generate`` falls back to the deterministic KG draft
        → ``stage2_landed=False`` → R72 reconcile no-op → valid cites
        stay on the wire."""
        monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "dummy")

        fake_resp = MagicMock()
        fake_resp.error = None
        fake_resp.text = "Article 13 requires transparency to deployers"
        fake_resp.model = "claude-sonnet-4-6"
        fake_resp.completion_tokens = 512
        fake_resp.finish_reason = "length"
        fake_provider = MagicMock()
        fake_provider.complete.return_value = fake_resp

        with patch(
            "app.llm.openai_wrapper_provider.get_openai_wrapper_provider",
            return_value=fake_provider,
        ):
            from app.engines.graph_rag import (
                _openai_wrapper_complete_for_graph_rag,
            )
            with pytest.raises(RuntimeError, match="truncated"):
                _openai_wrapper_complete_for_graph_rag(
                    system="s", user="u", max_tokens=512, temperature=0.0,
                )

    def test_wrapper_natural_stop_returns_text(self, monkeypatch) -> None:
        """``finish_reason="stop"`` (or absent) returns the text as before."""
        monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "dummy")

        fake_resp = MagicMock()
        fake_resp.error = None
        fake_resp.text = "Polished prose."
        fake_resp.model = "claude-sonnet-4-6"
        fake_resp.completion_tokens = 10
        fake_resp.finish_reason = "stop"
        fake_provider = MagicMock()
        fake_provider.complete.return_value = fake_resp

        with patch(
            "app.llm.openai_wrapper_provider.get_openai_wrapper_provider",
            return_value=fake_provider,
        ):
            from app.engines.graph_rag import (
                _openai_wrapper_complete_for_graph_rag,
            )
            result = _openai_wrapper_complete_for_graph_rag(
                system="s", user="u", max_tokens=512, temperature=0.0,
            )
        assert result == "Polished prose."

    def test_wrapper_midword_truncation_with_stop_returns_none(
        self, monkeypatch
    ) -> None:
        """ROOT-CAUSE REGRESSION (live bug: ``...safety component of a produc.``).

        The Claude-Max ``claude-code-openai-wrapper`` ignores ``max_tokens``
        and reports ``finish_reason="stop"`` EVEN when the underlying Claude
        CLI/SSE stream truncates the answer mid-word. The R91 guard only
        checked ``finish_reason == "length"``, so the mid-word fragment shipped
        as ``stage2_landed=True``. The structural guard must detect that the
        text ends without sentence-terminal punctuation and bail so the caller
        falls back to the complete deterministic answer.
        """
        monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "dummy")

        fake_resp = MagicMock()
        fake_resp.error = None
        # Mid-word cut, finish_reason="stop" (the actual wrapper behaviour).
        fake_resp.text = (
            "Under Article 11, providers must draw up technical documentation "
            "before placing a high-risk AI system on the market. Article 6 "
            "classifies an AI system as high-risk when it is intended as a "
            "safety component of a produc"
        )
        fake_resp.model = "claude-sonnet-4-6"
        fake_resp.completion_tokens = 95
        fake_resp.finish_reason = "stop"
        fake_provider = MagicMock()
        fake_provider.complete.return_value = fake_resp

        with patch(
            "app.llm.openai_wrapper_provider.get_openai_wrapper_provider",
            return_value=fake_provider,
        ):
            from app.engines.graph_rag import (
                _openai_wrapper_complete_for_graph_rag,
            )
            with pytest.raises(RuntimeError, match="truncated"):
                _openai_wrapper_complete_for_graph_rag(
                    system="s", user="u", max_tokens=512, temperature=0.0,
                )

    def test_wrapper_complete_answer_with_trailing_paren_returns_text(
        self, monkeypatch
    ) -> None:
        """Guard must NOT false-positive on legitimate complete answers whose
        final char is ``)`` / ``”`` after the terminator, or a bare
        sentence end."""
        monkeypatch.setenv("OPENAI_API_BASE", "http://127.0.0.1:8000/v1")
        monkeypatch.setenv("OPENAI_API_KEY", "dummy")

        for complete_text in (
            "Article 13 requires transparency (see Annex IV).",
            "Providers must keep logs under Article 12.",
            "Is this prohibited under Article 5?",
            'The Act calls this a "high-risk system."',
        ):
            fake_resp = MagicMock()
            fake_resp.error = None
            fake_resp.text = complete_text
            fake_resp.model = "claude-sonnet-4-6"
            fake_resp.completion_tokens = 30
            fake_resp.finish_reason = "stop"
            fake_provider = MagicMock()
            fake_provider.complete.return_value = fake_resp

            with patch(
                "app.llm.openai_wrapper_provider.get_openai_wrapper_provider",
                return_value=fake_provider,
            ):
                from app.engines.graph_rag import (
                    _openai_wrapper_complete_for_graph_rag,
                )
                result = _openai_wrapper_complete_for_graph_rag(
                    system="s", user="u", max_tokens=512, temperature=0.0,
                )
            assert result == complete_text, f"false-positive on: {complete_text!r}"


# ─── 4. Anthropic SDK path bails on max_tokens stop_reason ────────────────


class TestAnthropicCompleteForGraphRagTruncation:
    """The Anthropic SDK response carries ``stop_reason`` rather than
    ``finish_reason``; ``"max_tokens"`` is the equivalent truncation
    signal to the wrapper's ``"length"``.
    """

    def test_anthropic_max_tokens_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pytest.importorskip("anthropic")
        # Clean env, mirror tests/test_anthropic_provider.py setup.
        for k in (
            "P2P_GRAPH_RAG_PROVIDER",
            "OPENAI_API_BASE",
            "OPENAI_API_KEY",
            "GROQ_API_KEY",
            "REGENOLD_INTENT_PROVIDER",
        ):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv("REGENOLD_SKIP_STARTUP_LOG", "1")
        monkeypatch.setenv("P2P_GRAPH_RAG_PROVIDER", "anthropic")

        from pydantic import SecretStr
        from app.config import settings
        monkeypatch.setattr(
            settings.graph_rag, "api_key", SecretStr("sk-ant-fake"),
            raising=True,
        )

        class _Block:
            text = "Partial Article 13 prose…"

        class _Resp:
            content = [_Block()]
            stop_reason = "max_tokens"

        class _Anthropic:
            def __init__(self, *a, **kw): pass

            class _Messages:
                @staticmethod
                def create(*a, **kw):
                    return _Resp()

            messages = _Messages()

        import anthropic as _ant
        monkeypatch.setattr(_ant, "Anthropic", _Anthropic)

        from app.engines.graph_rag import _anthropic_complete_for_graph_rag
        result = _anthropic_complete_for_graph_rag(
            system="s", user="u", max_tokens=10, temperature=0.0,
        )
        assert result is None

    def test_anthropic_end_turn_returns_text(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pytest.importorskip("anthropic")
        for k in (
            "P2P_GRAPH_RAG_PROVIDER",
            "OPENAI_API_BASE",
            "OPENAI_API_KEY",
            "GROQ_API_KEY",
            "REGENOLD_INTENT_PROVIDER",
        ):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv("REGENOLD_SKIP_STARTUP_LOG", "1")
        monkeypatch.setenv("P2P_GRAPH_RAG_PROVIDER", "anthropic")

        from pydantic import SecretStr
        from app.config import settings
        monkeypatch.setattr(
            settings.graph_rag, "api_key", SecretStr("sk-ant-fake"),
            raising=True,
        )

        class _Block:
            text = "Article 13 requires logs."

        class _Resp:
            content = [_Block()]
            stop_reason = "end_turn"

        class _Anthropic:
            def __init__(self, *a, **kw): pass

            class _Messages:
                @staticmethod
                def create(*a, **kw):
                    return _Resp()

            messages = _Messages()

        import anthropic as _ant
        monkeypatch.setattr(_ant, "Anthropic", _Anthropic)

        from app.engines.graph_rag import _anthropic_complete_for_graph_rag
        result = _anthropic_complete_for_graph_rag(
            system="s", user="u", max_tokens=10, temperature=0.0,
        )
        assert result == "Article 13 requires logs."


# ─── R378. The Bedrock link, driven through the REAL producer ─────────────
#
# Every truncation row above hand-builds a MagicMock and sets
# ``finish_reason`` itself (``_mk_resp``, :152) — always ``"length"``. That is
# the OpenAI/Groq spelling. The Bedrock link added by R377 speaks Converse,
# whose token-cap value is ``"max_tokens"``, so the suite asserted against a
# value the real adapter cannot emit and 87 tests stayed green over a dead
# guard.
#
# CLAUDE.md's R338 doctrine: "A test fixture that builds its own input is not a
# test of the producer — make the test call the producer." These rows do.


def _converse_reply(text: str, stop_reason: str) -> dict:
    """A Converse reply shaped exactly as botocore returns it."""
    return {
        "output": {"message": {"content": [{"text": text}]}},
        "stopReason": stop_reason,
        "usage": {"inputTokens": 120, "outputTokens": 100},
    }


def _wire_real_bedrock_adapter(
    monkeypatch: pytest.MonkeyPatch, *, text: str, stop_reason: str
) -> list:
    """Wire the REAL ``_BedrockDenoiserProvider`` over a stubbed transport.

    Only ``complete_with_fallback`` is replaced, and its return value is built
    by the REAL ``_parse_converse_response``. So the adapter, the parser and the
    denoiser's guard all execute — the seam is at the network, not above it.
    """
    from app.llm.bedrock_client import _parse_converse_response

    seen: list = []

    def _fake_cwf(req, **kwargs):  # noqa: ANN001
        seen.append((req, kwargs))
        return _parse_converse_response(
            _converse_reply(text, stop_reason),
            "eu.anthropic.claude-sonnet-4-6",
            1234,
        )

    monkeypatch.setenv("REGENOLD_DENOISER_BEDROCK", "1")
    monkeypatch.setattr(
        "app.llm.bedrock_client.is_bedrock_provider_enabled", lambda: True
    )
    monkeypatch.setattr("app.llm.bedrock_client.complete_with_fallback", _fake_cwf)
    return seen


_TRUNCATED = "deployer transparency obligations under Article 26 of the"


class TestR378BedrockTruncationVocabulary:
    """The vocabulary gap, and the gate that closes it."""

    @pytest.fixture(autouse=True)
    def _chain_reachable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``conftest`` sets ``REGENOLD_QUERY_DENOISER=0`` (:152).

        Without re-enabling it these rows bail at
        ``fallback_reason="disabled"`` before any candidate is built, and every
        assertion below would pass VACUOUSLY — the same trap the R339 note on
        the sibling class documents. The ``seen`` / ``complete`` guards in these
        rows exist to fail loudly if they ever regress to that path.
        """
        monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
        monkeypatch.delenv("REGENOLD_INTENT_PROVIDER", raising=False)
        monkeypatch.setenv("REGENOLD_DENOISER_TRUNCATION_FALLTHROUGH", "1")

    def test_the_real_parser_emits_max_tokens_not_length(self) -> None:
        """The premise, stated as a measurement rather than an assumption."""
        from app.llm.bedrock_client import _parse_converse_response

        resp = _parse_converse_response(
            _converse_reply(_TRUNCATED, "max_tokens"), "m", 1
        )
        assert resp.finish_reason == "max_tokens"
        assert resp.finish_reason != "length"
        # And the character bound cannot backstop it: a 100-token cut is far
        # inside the 10 < len <= 500 window the denoiser sanity-checks.
        assert 10 < len(resp.text) <= 500

    def test_gate_off_is_the_shipped_behaviour_truncation_flows_through(
        self, monkeypatch: pytest.MonkeyPatch, denoiser_trace
    ) -> None:
        """DEFAULT OFF: the fragment still becomes the retrieval query.

        Pinned deliberately. R91's denoiser guard is NO-RECORD (no Round 91
        entry, no A/B), and with R377's fall-through a caught truncation on the
        last candidate routes to salvage -> concatenation, which is measurably
        not always better. This row documents what ships today so that flipping
        the gate is a visible, reviewable change rather than a silent one.
        """
        monkeypatch.delenv("REGENOLD_DENOISER_TRUNCATION_VOCAB", raising=False)
        groq = MagicMock()
        groq.complete.return_value = _mk_resp("", None)  # empty -> next link
        _wire_groq_candidate(monkeypatch, groq)
        _wire_real_bedrock_adapter(
            monkeypatch, text=_TRUNCATED, stop_reason="max_tokens"
        )

        from app.routes.regenold import _rewrite_multiturn_query

        out = _rewrite_multiturn_query(
            "What about deployers?", [_mk_msg("user", "What is Article 13?")]
        )
        assert out == _TRUNCATED

    def test_gate_on_recognises_the_converse_truncation(
        self, monkeypatch: pytest.MonkeyPatch, denoiser_trace
    ) -> None:
        """GATE ON: the R91 guard fires on the Bedrock link.

        This is the row that FAILS without the adapter's vocabulary translation
        and passes with it.
        """
        monkeypatch.setenv("REGENOLD_DENOISER_TRUNCATION_VOCAB", "1")
        groq = MagicMock()
        groq.complete.return_value = _mk_resp("", None)
        _wire_groq_candidate(monkeypatch, groq)
        _wire_real_bedrock_adapter(
            monkeypatch, text=_TRUNCATED, stop_reason="max_tokens"
        )

        from app.routes.regenold import _rewrite_multiturn_query

        out = _rewrite_multiturn_query(
            "What about deployers?", [_mk_msg("user", "What is Article 13?")]
        )
        assert out is None
        assert denoiser_trace.query_denoiser["fallback_reason"] == "truncated"

    def test_a_clean_converse_stop_is_untouched_by_the_gate(
        self, monkeypatch: pytest.MonkeyPatch, denoiser_trace
    ) -> None:
        """``end_turn`` must not be mistaken for truncation when the gate is on."""
        monkeypatch.setenv("REGENOLD_DENOISER_TRUNCATION_VOCAB", "1")
        groq = MagicMock()
        groq.complete.return_value = _mk_resp("", None)
        _wire_groq_candidate(monkeypatch, groq)
        _wire_real_bedrock_adapter(
            monkeypatch, text="deployer obligations under Article 26",
            stop_reason="end_turn",
        )

        from app.routes.regenold import _rewrite_multiturn_query

        out = _rewrite_multiturn_query(
            "What about deployers?", [_mk_msg("user", "What is Article 13?")]
        )
        assert out == "deployer obligations under Article 26"

    def test_the_denoiser_never_re_enters_the_untimed_wrapper_hop(
        self, monkeypatch: pytest.MonkeyPatch, denoiser_trace
    ) -> None:
        """R378 — the adapter must pass ``allow_wrapper_hop=False``.

        ``_try_wrapper_fallback`` builds its request with no ``timeout_seconds``
        (60 s singleton default), and R377 deleted the wrapper CANDIDATE from
        this chain precisely because the tunnel cannot answer inside the 3 s
        fail-fast. Reaching it one layer down would reinstate the hop.
        """
        groq = MagicMock()
        groq.complete.return_value = _mk_resp("", None)
        _wire_groq_candidate(monkeypatch, groq)
        seen = _wire_real_bedrock_adapter(
            monkeypatch, text="deployer obligations under Article 26",
            stop_reason="end_turn",
        )

        from app.routes.regenold import _rewrite_multiturn_query

        _rewrite_multiturn_query(
            "What about deployers?", [_mk_msg("user", "What is Article 13?")]
        )
        assert seen, "the Bedrock adapter was never reached"
        _req, kwargs = seen[0]
        assert kwargs.get("allow_wrapper_hop") is False
