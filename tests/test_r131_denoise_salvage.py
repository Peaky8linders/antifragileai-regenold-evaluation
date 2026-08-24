"""R131 — deterministic de-noiser salvage for a self-contained final turn.

Root cause (production "Intent & Query denoiser skipped (provider_error)"):
a multi-turn conversation whose final, self-contained question ("Does the
technical documentation of a high-risk AI system require to provide
specifications regarding the required hardware?") followed prior turns that
discussed Article 86 / Article 27. The LLM query de-noiser — which rewrites
the follow-up into a standalone query, stripping that prior-turn
contamination — failed (Groq TPD cap / tunnel timeout) with NO fallback, so
the flattened history bled Article 86 / 27 into retrieval, scope anchors, and
the per-reference description pass, and the answer led with those tangential
provisions instead of Article 11 + Annex IV.

R131 salvages the common case deterministically: on LLM-de-noiser FAILURE, if
the final user turn is self-contained, process it as a single-turn question
(clean engine query + scope on the live turn alone + no assistant-anchor
inheritance). Gated so that ``cli`` / no-provider (the davidath bench) and
coreferent follow-ups are byte-identical to the prior behaviour.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.routes import regenold as r


@pytest.fixture(autouse=True)
def _deterministic_denoiser_chain(monkeypatch):
    """R377 — pin the de-noiser CHAIN for this module, order-robust.

    The chain is now ``Groq -> Bedrock`` (operator directive 2026-08-23); the
    Gemini, Mistral and Claude-Max-wrapper candidates are deleted. So R330's pin
    here — ``P2P_GRAPH_RAG_PROVIDER=openai_wrapper``, to un-``cli``
    ``is_openai_wrapper_enabled()`` (R127) — no longer buys anything: neither
    ``is_groq_intent_provider_enabled()`` nor ``is_bedrock_provider_enabled()``
    reads that variable.

    R330's underlying CONCERN still holds, and it is why this fixture stays: the
    tests below are about the *provider-failure salvage* path, and the salvage
    only runs from ``_salvage_on_provider_failure``. A candidate that is not the
    patched one — a ``GROQ_API_KEY`` or an AWS credential leaking in from
    ``.env`` / ``load_dotenv`` / a neighbouring test under pytest-randomly —
    either answers for real or empties the chain to ``fallback_reason=
    "no_provider"``, and in both cases the salvage is never reached. So
    neutralise every selector the new chain reads, and let each test opt its own
    candidate in by patching the GATE FUNCTION directly
    (``force_failing_bedrock`` below), which is credential-independent.
    """
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("REGENOLD_INTENT_PROVIDER", raising=False)
    # `is_bedrock_provider_enabled` is a bare credential-presence check over
    # this family (bearer token first, then the composite key, then the
    # access-key pair) — same class as the conftest's R330 AWS block.
    for _aws_var in (
        "AWS_BEARER_TOKEN_BEDROCK",
        "AWS_BEDROCK_BEARER_TOKEN",
        "BEDROCK_BEARER_TOKEN",
        "AWS_BEDROCK_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
    ):
        monkeypatch.delenv(_aws_var, raising=False)


# ── _live_turn_is_self_contained ─────────────────────────────────────────


def test_self_contained_true_for_techdoc_question() -> None:
    q = (
        "Does the technical documentation of a high-risk AI system require to "
        "provide specifications regarding the required hardware?"
    )
    assert r._live_turn_is_self_contained(q) is True


@pytest.mark.parametrize(
    "q",
    [
        "Are these checks continuous?",            # leading coreference
        "What about deployers?",                   # short coreferent
        "And if it is high-risk?",                 # leading 'and if'
        "Does it still apply to that system?",     # mid coref markers
        "Yes please.",                              # too short
        "Tell me more.",                            # too short, no anchor
    ],
)
def test_self_contained_false_for_coreferent_or_short(q: str) -> None:
    assert r._live_turn_is_self_contained(q) is False


def test_self_contained_false_without_ai_act_anchor() -> None:
    # Long enough + non-coreferent, but carries no AI-Act subject of its own.
    assert (
        r._live_turn_is_self_contained(
            "Please summarise the weather forecast for tomorrow afternoon."
        )
        is False
    )


# ── env gate ─────────────────────────────────────────────────────────────


def test_salvage_enabled_default_on(monkeypatch) -> None:
    monkeypatch.delenv("REGENOLD_DENOISE_SALVAGE", raising=False)
    assert r._is_denoise_salvage_enabled() is True


@pytest.mark.parametrize("val", ["0", "false", "no", "off", "OFF"])
def test_salvage_disabled_by_env(monkeypatch, val: str) -> None:
    monkeypatch.setenv("REGENOLD_DENOISE_SALVAGE", val)
    assert r._is_denoise_salvage_enabled() is False


# ── _rewrite_multiturn_query salvage on provider failure ─────────────────


def _mk_msg(role: str, content: str):
    m = MagicMock()
    m.role = role
    m.content = content
    return m


_SELF_CONTAINED = (
    "Does the technical documentation of a high-risk AI system require to "
    "provide specifications regarding the required hardware?"
)


def _failing_bedrock():
    """A WIRED-but-FAILING candidate — R377 makes that Bedrock, not the wrapper.

    ``BedrockResponse`` already matches the wrapper response shape (``.text`` /
    ``.error`` / ``.finish_reason`` / ``.model``), so the failure the de-noiser
    observes — and therefore the ``provider_error`` reason it salvages on — is
    byte-identical to the pre-R377 wrapper failure this stub used to model.
    """
    resp = MagicMock()
    resp.error = "network_error: timed out"
    resp.text = ""
    # Explicit: a transport failure is not a truncation, so the R377
    # truncation-fall-through must not be what carries this test.
    resp.finish_reason = None
    resp.model = "eu.anthropic.claude-sonnet-4-6"
    prov = MagicMock()
    prov.complete.return_value = resp
    return prov


@pytest.fixture
def force_failing_bedrock(monkeypatch):
    """Pin the de-noiser to a WIRED-but-FAILING Bedrock candidate, order-robust.

    R377 — the chain is ``Groq -> Bedrock``; this fixture used to pin the
    (now-deleted) Claude-Max-wrapper candidate. The SHAPE is unchanged: the
    PRIMARY link is forced off so the FALLBACK link is the sole attempt, and
    that attempt fails — which is the only way to reach
    ``_salvage_on_provider_failure``. Bedrock is simply the fallback that
    Gemini / Mistral / the wrapper used to be.

    The conftest pins ``REGENOLD_QUERY_DENOISER=0``, and pytest-randomly can
    leave ``GROQ_API_KEY`` / ``REGENOLD_INTENT_PROVIDER`` set from a
    neighbouring test — which would steer the de-noiser onto Groq instead of
    the patched Bedrock candidate. Pin every selector so the provider-failure
    path is deterministic regardless of test order.

    Yields the stub provider so a test asserting ``None`` can prove the
    candidate was actually CALLED — R330 recorded that those tests used to pass
    without exercising the salvage at all (``None`` is also what the
    ``no_provider`` exit returns), and a silently-uncalled fake is exactly the
    failure mode the R377 chain change produced here.
    """
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("REGENOLD_INTENT_PROVIDER", raising=False)
    import app.llm.bedrock_client as bc
    import app.llm.openai_wrapper_provider as wp

    monkeypatch.setattr(wp, "is_groq_intent_provider_enabled", lambda: False)
    # The Bedrock candidate is gated TWICE — the R377 env flag (default ON) and
    # the credential presence check. Pin both, so the autouse fixture's
    # credential scrub above cannot silently empty the chain and exit at
    # ``no_provider`` instead of reaching the salvage.
    monkeypatch.setenv("REGENOLD_DENOISER_BEDROCK", "1")
    monkeypatch.setattr(bc, "is_bedrock_provider_enabled", lambda: True)
    prov = _failing_bedrock()
    monkeypatch.setattr(r, "_BedrockDenoiserProvider", lambda: prov)
    return prov


def test_provider_failure_self_contained_salvages(
    monkeypatch, force_failing_bedrock
) -> None:
    monkeypatch.delenv("REGENOLD_DENOISE_SALVAGE", raising=False)
    out = r._rewrite_multiturn_query(
        _SELF_CONTAINED, [_mk_msg("user", "We deploy a high-risk AI system.")]
    )
    # The salvage returns the verbatim live turn.
    assert out == _SELF_CONTAINED


def test_provider_failure_coreferent_does_not_salvage(
    monkeypatch, force_failing_bedrock
) -> None:
    monkeypatch.delenv("REGENOLD_DENOISE_SALVAGE", raising=False)
    out = r._rewrite_multiturn_query(
        "Are these checks continuous?",
        [_mk_msg("user", "We deploy a high-risk AI system.")],
    )
    assert out is None
    # …and it is None because the wired candidate FAILED, not because the chain
    # was empty (which returns None too, at ``fallback_reason="no_provider"``).
    assert force_failing_bedrock.complete.call_count == 1


def test_provider_failure_salvage_disabled_returns_none(
    monkeypatch, force_failing_bedrock
) -> None:
    monkeypatch.setenv("REGENOLD_DENOISE_SALVAGE", "0")
    out = r._rewrite_multiturn_query(
        _SELF_CONTAINED, [_mk_msg("user", "We deploy a high-risk AI system.")]
    )
    assert out is None
    # The env off-switch is what returned None — the candidate still ran.
    assert force_failing_bedrock.complete.call_count == 1


def test_no_provider_does_not_salvage(monkeypatch) -> None:
    # cli / no-provider (the davidath bench): the salvage must NOT fire so the
    # multi-turn flatten stays byte-identical.
    #
    # R377 — the chain is Groq -> Bedrock, so "no provider wired" now means
    # BOTH of those gates are off. It used to mean Groq off + wrapper off.
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
    monkeypatch.delenv("REGENOLD_INTENT_PROVIDER", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    import app.llm.bedrock_client as bc
    import app.llm.openai_wrapper_provider as wp

    monkeypatch.setattr(wp, "is_groq_intent_provider_enabled", lambda: False)
    monkeypatch.setattr(bc, "is_bedrock_provider_enabled", lambda: False)
    out = r._rewrite_multiturn_query(
        _SELF_CONTAINED, [_mk_msg("user", "We deploy a high-risk AI system.")]
    )
    assert out is None


# ── _build_question_from_history salvaged flag ───────────────────────────


def test_flatten_salvaged_flag_on_provider_failure(
    monkeypatch, force_failing_bedrock
) -> None:
    msgs = [
        _mk_msg("user", "We deploy a high-risk AI system affecting individuals."),
        _mk_msg("assistant", "Under Article 86 ... Under Article 27, deployers ..."),
        _mk_msg("user", _SELF_CONTAINED),
    ]
    res = r._build_question_from_history(msgs)
    assert res.salvaged is True
    # The engine question is the clean live turn — no Article 86/27, no
    # "Conversation so far" history block.
    assert res[0] == _SELF_CONTAINED
    assert "Article 86" not in res[0]
    assert "Conversation so far" not in res[0]


def test_flatten_not_salvaged_for_coreferent(
    monkeypatch, force_failing_bedrock
) -> None:
    msgs = [
        _mk_msg("user", "We deploy a high-risk AI system affecting individuals."),
        _mk_msg("assistant", "Under Article 86 ... Under Article 27, deployers ..."),
        _mk_msg("user", "Are these checks continuous?"),
    ]
    res = r._build_question_from_history(msgs)
    assert res.salvaged is False
    # Coreferent follow-up keeps the concatenation path (history preserved).
    assert "Conversation so far" in res[0]
    # …and it is the COREFERENCE that suppressed the salvage, not an empty
    # chain — with no candidate wired this test is indistinguishable from
    # `test_flatten_not_salvaged_in_cli_mode` below. Same fire check as the two
    # `None`-asserting tests above; verified by sabotage (patching the Bedrock
    # gate to False makes this line, and only this line, fail).
    assert force_failing_bedrock.complete.call_count == 1


def test_flatten_not_salvaged_in_cli_mode(monkeypatch) -> None:
    # R377 — "cli mode" = neither link of the Groq -> Bedrock chain is wired.
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
    monkeypatch.delenv("REGENOLD_INTENT_PROVIDER", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    import app.llm.bedrock_client as bc
    import app.llm.openai_wrapper_provider as wp

    monkeypatch.setattr(wp, "is_groq_intent_provider_enabled", lambda: False)
    monkeypatch.setattr(bc, "is_bedrock_provider_enabled", lambda: False)
    msgs = [
        _mk_msg("user", "We deploy a high-risk AI system affecting individuals."),
        _mk_msg("assistant", "Under Article 86 ... Under Article 27, deployers ..."),
        _mk_msg("user", _SELF_CONTAINED),
    ]
    res = r._build_question_from_history(msgs)
    assert res.salvaged is False


def test_questionhistoryresult_salvaged_default_false() -> None:
    res = r.QuestionHistoryResult("q", None, "q")
    assert res.salvaged is False
    res2 = r.QuestionHistoryResult("q", None, "q", True)
    assert res2.salvaged is True


# ── R133.1 — self_contained_focus on the de-noiser-SUCCESS path ───────────
#
# The R131 salvage only fired when the de-noiser FAILED. But a SUCCESSFUL
# de-noiser leaves the engine query clean while `scope.anchor_articles` +
# R88-A assistant-anchor inheritance still ran on the full conversation —
# re-contaminating the wire with prior-turn Articles (Art. 86 / 27). R133.1
# adds `self_contained_focus` (a superset of `salvaged`) that fires on de-noiser
# SUCCESS too, so the route focuses scope + R88-A on the live turn alone.


def _clean_rewrite_denoiser(monkeypatch):
    """Force the de-noiser to SUCCEED with a clean standalone rewrite."""
    monkeypatch.setattr(
        r,
        "_rewrite_multiturn_query",
        lambda live, hist: (
            "Technical documentation hardware specification requirements for a "
            "high-risk AI system under Annex IV"
        ),
    )


def test_questionhistoryresult_focus_default_false() -> None:
    res = r.QuestionHistoryResult("q", None, "q")
    assert res.self_contained_focus is False
    res2 = r.QuestionHistoryResult("q", None, "q", False, True)
    assert res2.self_contained_focus is True


def test_focus_true_on_denoiser_success_self_contained(monkeypatch) -> None:
    monkeypatch.delenv("REGENOLD_DENOISE_SALVAGE", raising=False)
    _clean_rewrite_denoiser(monkeypatch)
    msgs = [
        _mk_msg("user", "We deploy a high-risk AI system affecting individuals."),
        _mk_msg("assistant", "Under Article 86 ... Under Article 27, deployers ..."),
        _mk_msg("user", _SELF_CONTAINED),
    ]
    res = r._build_question_from_history(msgs)
    # De-noiser SUCCEEDED (clean rewrite != live turn) → NOT a salvage, but
    # focus fires because the final turn is self-contained.
    assert res.salvaged is False
    assert res.self_contained_focus is True
    # The prior-turn anchor line is dropped: question is the clean rewrite,
    # with no "Conversation so far" history block and no Article 86/27.
    assert "Conversation so far" not in res[0]
    assert "Article 86" not in res[0]
    assert "Article 27" not in res[0]


def test_focus_false_on_denoiser_success_coreferent(monkeypatch) -> None:
    monkeypatch.delenv("REGENOLD_DENOISE_SALVAGE", raising=False)
    _clean_rewrite_denoiser(monkeypatch)
    msgs = [
        _mk_msg("user", "We deploy a high-risk AI system affecting individuals."),
        _mk_msg("assistant", "Under Article 86 ... Under Article 27, deployers ..."),
        _mk_msg("user", "Are these checks continuous?"),
    ]
    res = r._build_question_from_history(msgs)
    # Coreferent follow-up is NOT self-contained → no focus, keep the
    # multi-turn context (scope coreference rescue must still work).
    assert res.self_contained_focus is False


def test_focus_false_in_cli_mode(monkeypatch) -> None:
    # cli / no-provider (the davidath bench): the real de-noiser returns None,
    # so focus never fires → davidath byte-identical by construction.
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
    monkeypatch.delenv("REGENOLD_INTENT_PROVIDER", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    import app.llm.bedrock_client as bc
    import app.llm.openai_wrapper_provider as wp

    # R377 — the chain is Groq -> Bedrock; both links off is the no-provider
    # state that used to be Groq off + wrapper off.
    monkeypatch.setattr(wp, "is_groq_intent_provider_enabled", lambda: False)
    monkeypatch.setattr(bc, "is_bedrock_provider_enabled", lambda: False)
    msgs = [
        _mk_msg("user", "We deploy a high-risk AI system affecting individuals."),
        _mk_msg("assistant", "Under Article 86 ... Under Article 27, deployers ..."),
        _mk_msg("user", _SELF_CONTAINED),
    ]
    res = r._build_question_from_history(msgs)
    assert res.self_contained_focus is False
    assert res.salvaged is False
    # Multi-turn concatenation preserved (no focus, no salvage).
    assert "Conversation so far" in res[0]


def test_focus_false_when_salvage_disabled(monkeypatch) -> None:
    monkeypatch.setenv("REGENOLD_DENOISE_SALVAGE", "0")
    _clean_rewrite_denoiser(monkeypatch)
    msgs = [
        _mk_msg("user", "We deploy a high-risk AI system affecting individuals."),
        _mk_msg("assistant", "Under Article 86 ... Under Article 27, deployers ..."),
        _mk_msg("user", _SELF_CONTAINED),
    ]
    res = r._build_question_from_history(msgs)
    # The env off-switch disables focus too (it gates on
    # `_is_denoise_salvage_enabled()`). The clean rewrite still replaces the
    # history, but the prior-turn anchor line is retained.
    assert res.self_contained_focus is False
