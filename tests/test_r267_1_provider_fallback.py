"""R267.1 — provider fallback chain for the general assistant and the
multi-turn de-noiser.

Root cause fixed: Groq ``qwen/qwen3.6-27b`` has a daily tokens-per-day cap
(``api_status_429``, ``Limit 200000``). When it is exhausted the Groq-only
general assistant returned ``None`` (branded decline for every benign
off-topic question) and the de-noiser's Groq->wrapper chain fell to the
~10 s Claude Max wrapper, which the fail-fast timeout always tripped into a
``provider_error``. Both now fall through to a separately-quota'd fallback.

⚠ ``qwen/qwen3.6-27b`` above is the R267.1-era Groq model and is HISTORY, not
the current pin. R289 moved the Groq default to ``openai/gpt-oss-120b`` and put
it behind a single ``default_groq_model()``; the fallback-chain behaviour these
tests cover is model-agnostic and unchanged. Do not re-pin a Groq literal here —
see ``test_candidate_order_is_groq_then_gemini_then_mistral``.

⚠ THE TWO CHAINS DIVERGED AT R377 — read the section header before editing.
The GENERAL ASSISTANT chain is still ``groq -> gemini -> mistral`` and those
tests are unchanged. The DE-NOISER chain is now ``groq -> bedrock`` by operator
directive 2026-08-23: Gemini 2.5 Flash is a reasoning model that burns the
100-token rewrite budget on a hidden trace and returns ``finish_reason=length``
(terminal under R91, so it starved everything behind it), and the wrapper
candidate is the ~10 s Claude Max tunnel the 3 s fail-fast can never beat. The
de-noiser tests below therefore assert the SAME fallback property against
Bedrock, which now occupies the slot Gemini/Mistral/the wrapper used to.

These tests mock the providers so they run in the no-API-key test env.
"""
from __future__ import annotations

import pytest

import app.llm.bedrock_client as bedrock_client
import app.llm.openai_wrapper_provider as owp
import app.routes.regenold as route


class _Resp:
    def __init__(self, text: str = "", error: str | None = None,
                 finish_reason: str | None = "stop") -> None:
        self.text = text
        self.error = error
        self.finish_reason = finish_reason
        self.model = "fake"
        self.elapsed_ms = 5
        self.thinking = None


class _Prov:
    """Records every request it receives and returns a canned response."""

    def __init__(self, text: str = "", error: str | None = None,
                 finish_reason: str | None = "stop") -> None:
        self._resp = _Resp(text, error, finish_reason)
        self.calls: list = []

    def complete(self, req):  # noqa: ANN001
        self.calls.append(req)
        return self._resp


def _wire(monkeypatch, *, groq=None, gemini=None, mistral=None) -> None:
    """Enable/disable each general-assistant provider on the owp module."""
    monkeypatch.setattr(owp, "is_groq_provider_enabled", lambda: groq is not None)
    if groq is not None:
        monkeypatch.setattr(owp, "get_groq_provider", lambda: groq)
    monkeypatch.setattr(owp, "is_gemini_provider_enabled", lambda: gemini is not None)
    if gemini is not None:
        monkeypatch.setattr(owp, "get_gemini_provider", lambda: gemini)
    monkeypatch.setattr(owp, "is_mistral_provider_enabled", lambda: mistral is not None)
    if mistral is not None:
        monkeypatch.setattr(owp, "get_mistral_provider", lambda: mistral)


# ── general assistant ────────────────────────────────────────────────────────

def test_groq_tpd_429_falls_through_to_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    groq = _Prov(error="api_status_429: tokens per day (TPD): Limit 200000")
    gemini = _Prov(text="Try Da Enzo al 29 in Trastevere for classic Roman food.")
    _wire(monkeypatch, groq=groq, gemini=gemini)
    out = route._general_assistant_answer("recommend a restaurant in Rome")
    assert out is not None and "Trastevere" in out
    assert len(groq.calls) == 1  # Groq tried first
    assert len(gemini.calls) == 1  # then fell through to Gemini


def test_groq_and_gemini_fail_falls_through_to_mistral(monkeypatch: pytest.MonkeyPatch) -> None:
    groq = _Prov(error="api_status_429")
    gemini = _Prov(error="api_status_500")
    mistral = _Prov(text="The capital of France is Paris.")
    _wire(monkeypatch, groq=groq, gemini=gemini, mistral=mistral)
    out = route._general_assistant_answer("what is the capital of France?")
    assert out is not None and "Paris" in out
    assert len(groq.calls) == len(gemini.calls) == len(mistral.calls) == 1


def test_first_success_short_circuits_the_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    groq = _Prov(text="Paris.")
    gemini = _Prov(text="SHOULD NOT BE CALLED")
    _wire(monkeypatch, groq=groq, gemini=gemini)
    out = route._general_assistant_answer("capital of France?")
    assert out is not None and "Paris" in out
    assert len(groq.calls) == 1
    assert gemini.calls == []  # Groq succeeded → Gemini never reached


def test_all_providers_fail_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    groq = _Prov(error="api_status_429")
    gemini = _Prov(error="api_status_500")
    mistral = _Prov(error="timeout")
    _wire(monkeypatch, groq=groq, gemini=gemini, mistral=mistral)
    assert route._general_assistant_answer("recommend a restaurant in Rome") is None


def test_no_provider_wired_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _wire(monkeypatch)  # nothing enabled
    assert route._general_assistant_answer("hello there general") is None


def test_candidate_order_is_groq_then_gemini_then_mistral(monkeypatch: pytest.MonkeyPatch) -> None:
    """The chain is groq -> gemini -> mistral, on each slot's DEFAULT model.

    ⚠ Superseded expectation: this asserted the Groq literal
    ``"qwen/qwen3.6-27b"`` until R289. That round consolidated the Groq model
    id into ONE source of truth — ``_GROQ_LIVE_VALIDATED_MODEL`` behind
    ``default_groq_model()`` (``app/llm/openai_wrapper_provider.py``) — after a
    controlled live before/after on the same ``/healthz`` probe:
    ``62ca878`` qwen -> ok, ``8145be2`` groq/compound -> 413 request_too_large
    (it took every Groq path down), ``5869eec`` openai/gpt-oss-120b -> ok. The
    literal here was one of the nine hard-coded copies that migration existed
    to delete, so it kept asserting a model that live traffic has invalidated.

    Do NOT re-pin a literal. Assert against ``default_groq_model()`` — the same
    function ``_general_llm_candidates`` calls — so the next one-line migration
    stays one line. The assertion stays an order-strict full equality: the
    ORDER is the actual contract under test and must not be relaxed to a
    subset/``in`` check.
    """
    from app.llm.openai_wrapper_provider import default_groq_model

    # Pin the DEFAULT chain: each slot takes an ``os.getenv(env_key, default)``
    # override in production, so an ambient override would otherwise silently
    # change what this test measures.
    for env_key in (
        "REGENOLD_GENERAL_MODEL_GROQ",
        "REGENOLD_GENERAL_MODEL_GEMINI",
        "REGENOLD_GENERAL_MODEL_MISTRAL",
    ):
        monkeypatch.delenv(env_key, raising=False)

    g, ge, mi = _Prov(), _Prov(), _Prov()
    _wire(monkeypatch, groq=g, gemini=ge, mistral=mi)
    cands = route._general_llm_candidates()
    models = [m for _, m in cands]
    assert models == [default_groq_model(), "gemini-2.5-flash", "mistral-large-latest"]

    # And prove the groq slot really is bound to that source of truth rather
    # than to some other model constant that merely happens to match today
    # (there are several Groq-ish ids in-tree). ``default_groq_model`` is
    # documented as read per-call, never at import, so an in-process A/B arm
    # can move it — assert that end to end through the route.
    monkeypatch.setenv("REGENOLD_GROQ_DEFAULT_MODEL", "sentinel/ab-arm-model")
    assert [m for _, m in route._general_llm_candidates()] == [
        "sentinel/ab-arm-model",
        "gemini-2.5-flash",
        "mistral-large-latest",
    ]


def test_think_block_stripped_then_still_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    # Qwen leaks a <think> block; validate_llm_output strips it, real answer stays.
    groq = _Prov(text="<think>let me reason</think>The capital of France is Paris.")
    _wire(monkeypatch, groq=groq)
    out = route._general_assistant_answer("capital of France?")
    assert out is not None and "Paris" in out and "<think>" not in out


# ── multi-turn de-noiser ─────────────────────────────────────────────────────

class _Msg:
    def __init__(self, role: str, content: str) -> None:
        self.role = role
        self.content = content


def _wire_denoiser(monkeypatch, *, groq=None, bedrock=None, gemini=None,
                   mistral=None, wrapper=None, stub_bedrock_env_gate=True) -> None:
    """Enable/disable each DE-NOISER link.

    ⚠ R377 — the de-noiser chain is ``groq -> bedrock``; the gemini / mistral /
    wrapper candidate blocks were DELETED from ``_rewrite_multiturn_query``.
    They stay wireable here on purpose: the tests below wire them and assert
    they are never CALLED, which is what proves the blocks are actually gone
    rather than merely reordered behind the new fallback.

    ``stub_bedrock_env_gate=False`` leaves ``_denoiser_bedrock_enabled`` REAL so
    a test can drive the ``REGENOLD_DENOISER_BEDROCK`` off-switch through the
    actual env read. With the gate stubbed (the default, which is what the
    chain-shape tests want) a production regression that deleted the env gate
    while keeping the candidate would still pass — see the two gate tests at the
    bottom of this file, which close exactly that hole.
    """
    monkeypatch.setattr(owp, "is_groq_intent_provider_enabled", lambda: groq is not None)
    if groq is not None:
        monkeypatch.setattr(owp, "get_groq_intent_provider", lambda: groq)
    # The Bedrock link is gated TWICE — the R377 env gate on the route module,
    # then the client's own credential check (imported function-locally inside
    # the route, so patch it on its home module) — so both must agree.
    if stub_bedrock_env_gate:
        monkeypatch.setattr(
            route, "_denoiser_bedrock_enabled", lambda: bedrock is not None
        )
    monkeypatch.setattr(
        bedrock_client, "is_bedrock_provider_enabled", lambda: bedrock is not None
    )
    if bedrock is not None:
        # The route constructs the adapter (``_BedrockDenoiserProvider()``), so
        # the stub is a zero-arg factory returning the recorder.
        monkeypatch.setattr(route, "_BedrockDenoiserProvider", lambda: bedrock)
    monkeypatch.setattr(owp, "is_gemini_provider_enabled", lambda: gemini is not None)
    if gemini is not None:
        monkeypatch.setattr(owp, "get_gemini_provider", lambda: gemini)
    monkeypatch.setattr(owp, "is_mistral_provider_enabled", lambda: mistral is not None)
    if mistral is not None:
        monkeypatch.setattr(owp, "get_mistral_provider", lambda: mistral)
    monkeypatch.setattr(owp, "is_openai_wrapper_enabled", lambda: wrapper is not None)
    if wrapper is not None:
        monkeypatch.setattr(owp, "get_openai_wrapper_provider", lambda: wrapper)


def test_denoiser_groq_429_falls_through_to_bedrock(monkeypatch: pytest.MonkeyPatch) -> None:
    """A Groq TPD 429 degrades to the fallback link instead of losing the rewrite.

    ⚠ Retargeted at R377 — was ``..._falls_through_to_gemini``. The PROPERTY is
    unchanged and is the whole point of R267.1: Groq is tried FIRST, its 429
    falls THROUGH rather than ending the chain, and the fallback link produces
    the standalone rewrite. Only the identity of that fallback moved (gemini ->
    bedrock), so the assertions moved with it.
    """
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
    groq = _Prov(error="api_status_429: tokens per day (TPD)")
    bedrock = _Prov(text="What are the transparency obligations for high-risk AI deployers?")
    gemini = _Prov(text="SHOULD NOT BE REACHED")
    wrapper = _Prov(text="SHOULD NOT BE REACHED")
    _wire_denoiser(
        monkeypatch, groq=groq, bedrock=bedrock, gemini=gemini, wrapper=wrapper,
    )
    history = [
        _Msg("user", "Tell me about high-risk AI transparency."),
        _Msg("assistant", "Article 13 governs transparency for high-risk AI systems."),
    ]
    out = route._rewrite_multiturn_query("And what about the deployers of those?", history)
    assert out is not None and "deployers" in out.lower()
    assert len(groq.calls) == 1  # Groq tried first (429)
    assert len(bedrock.calls) == 1  # then fell through to Bedrock, which rewrote it
    assert wrapper.calls == []  # the ~10 s wrapper candidate is GONE, not merely last
    assert gemini.calls == []  # and so is the truncating Gemini candidate


def test_denoiser_bedrock_is_the_chain_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """The de-noiser chain is exactly ``groq -> bedrock``, walked in order.

    ⚠ Retargeted at R377 — was ``test_denoiser_gemini_and_mistral_are_in_the_chain``.
    That test's premise (Gemini + Mistral occupy the fallback slots) no longer
    exists in the code: both candidate blocks were deleted, and Bedrock is now
    the separately-quota'd fallback they used to be. The property retained is
    CHAIN MEMBERSHIP AND ORDER — every configured link is tried exactly once, in
    order, until one succeeds — asserted here through the model each slot is
    bound to, so a future slot swap cannot pass by accident.
    """
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
    # Pin the DEFAULT chain: each de-noiser slot takes an ``os.environ.get``
    # override in production, so an ambient override would otherwise silently
    # change what this test measures (same guard as the general-assistant
    # order test above).
    for env_key in (
        "REGENOLD_DENOISER_MODEL_GROQ",
        "REGENOLD_DENOISER_MODEL_BEDROCK",
    ):
        monkeypatch.delenv(env_key, raising=False)
    from app.llm.openai_wrapper_provider import default_groq_model

    groq = _Prov(error="api_status_429")
    bedrock = _Prov(text="What incident-reporting duties apply to high-risk AI providers?")
    gemini = _Prov(error="api_status_500")
    mistral = _Prov(text="SHOULD NOT BE REACHED")
    wrapper = _Prov(text="SHOULD NOT BE REACHED")
    _wire_denoiser(
        monkeypatch, groq=groq, bedrock=bedrock, gemini=gemini, mistral=mistral,
        wrapper=wrapper,
    )
    history = [
        _Msg("user", "What are the post-market monitoring duties?"),
        _Msg("assistant", "Article 72 sets out post-market monitoring for providers."),
    ]
    out = route._rewrite_multiturn_query("And the reporting duties for those providers?", history)
    # ⚠ Reviewer strengthening (R377): the old test asserted only ``out is not
    # None``, which the R131 deterministic salvage can also satisfy on a broken
    # chain. Pin the FALLBACK's own text so "bedrock rewrote it" is what is
    # measured, not "something returned a string".
    assert out is not None and "incident-reporting" in out
    assert len(groq.calls) == len(bedrock.calls) == 1  # full chain walked
    # The deleted candidates are wired and STILL never consulted — this is the
    # half of the old test that survives verbatim in meaning: it pins which
    # providers are (and are not) in the chain.
    assert gemini.calls == mistral.calls == wrapper.calls == []
    # Each slot on its own default model, in order. Groq asserts against
    # ``default_groq_model()`` rather than a literal for the R289 reason
    # documented on the general-assistant order test above.
    assert groq.calls[0].model == default_groq_model()
    assert bedrock.calls[0].model == "eu.anthropic.claude-sonnet-4-6"


# ── R377 env gate on the Bedrock link ────────────────────────────────────────
#
# ⚠ Reviewer addition. The two tests above stub BOTH Bedrock gates
# (``route._denoiser_bedrock_enabled`` and the client's credential check), which
# is right for measuring chain SHAPE but leaves a mutation hole: a production
# change that deleted the ``REGENOLD_DENOISER_BEDROCK`` env gate while keeping
# the candidate would keep them green. These two drive the REAL gate — one per
# direction — so the flag's documented default-ON and its ``=0`` rollback are
# both pinned. This is the de-noiser's equivalent of the general-assistant
# tests' "which providers are configured decides which are called".

def test_denoiser_bedrock_gate_defaults_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """With ``REGENOLD_DENOISER_BEDROCK`` UNSET the Bedrock link is in the chain."""
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
    monkeypatch.delenv("REGENOLD_DENOISER_BEDROCK", raising=False)
    groq = _Prov(error="api_status_429")
    bedrock = _Prov(text="What incident-reporting duties apply to high-risk AI providers?")
    _wire_denoiser(
        monkeypatch, groq=groq, bedrock=bedrock, stub_bedrock_env_gate=False,
    )
    history = [
        _Msg("user", "What are the post-market monitoring duties?"),
        _Msg("assistant", "Article 72 sets out post-market monitoring for providers."),
    ]
    out = route._rewrite_multiturn_query("And the reporting duties for those providers?", history)
    assert out is not None and "incident-reporting" in out
    assert len(groq.calls) == 1
    assert len(bedrock.calls) == 1  # the gate's CODE default is ON


def test_denoiser_bedrock_off_switch_restores_the_groq_only_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``REGENOLD_DENOISER_BEDROCK=0`` is the documented R377 rollback.

    The credential check and the adapter factory are both wired to succeed, so
    the ONLY thing that can keep Bedrock out of the chain is the env gate — if
    it stopped being read, ``bedrock.calls`` would be non-empty here.
    """
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
    monkeypatch.setenv("REGENOLD_DENOISER_BEDROCK", "0")
    groq = _Prov(error="api_status_429")
    bedrock = _Prov(text="SHOULD NOT BE REACHED")
    _wire_denoiser(
        monkeypatch, groq=groq, bedrock=bedrock, stub_bedrock_env_gate=False,
    )
    history = [
        _Msg("user", "What are the post-market monitoring duties?"),
        _Msg("assistant", "Article 72 sets out post-market monitoring for providers."),
    ]
    route._rewrite_multiturn_query("And the reporting duties for those providers?", history)
    assert len(groq.calls) == 1  # Groq is still the primary link
    assert bedrock.calls == []  # and the fallback is switched off
