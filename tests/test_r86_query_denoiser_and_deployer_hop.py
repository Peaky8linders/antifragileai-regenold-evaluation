"""R86 — Query De-Noiser + Deployer Graph-Hop regression tests.

Covers the three invariants for the two R86 surfaces:

R86 Query De-Noiser (multi-turn search-query rewriter)
------------------------------------------------------
1. Disabled when ``REGENOLD_QUERY_DENOISER=0`` — returns ``None``
   without touching any provider.
2. Returns ``None`` on empty history (single-turn questions need no
   rewrite, the caller falls back to the live question directly).
3. Returns ``None`` on every LLM-failure path: import failure, no
   provider configured, the response's ``.error`` non-empty,
   empty text, length out of sanity bounds (< 10 or > 500 chars).
   Each ``None`` means the caller falls back to the existing
   concatenation path — the de-noiser is strictly opportunistic.

   ⚠ R377 — these are asserted through the CURRENT provider chain,
   which is ``groq -> bedrock`` (operator directive 2026-08-23). It
   used to be ``groq -> gemini -> mistral -> claude-max wrapper`` and
   every test below drove the WRAPPER link, because that was the one
   the bench env left configured. The wrapper candidate is deleted, so
   the fallback link these tests exercise is now Bedrock. The property
   under test is unchanged: a provider that fails, returns blank, or
   returns an out-of-bounds rewrite must yield ``None``.
4. The cache-key sees ``REGENOLD_QUERY_DENOISER`` + the model
   override env vars it registers — flipping the de-noiser on or off
   without a process restart cannot serve a stale answer (R30/R56/R79
   cache-poisoning doctrine).

   ⚠ R377 — ``REGENOLD_DENOISER_MODEL_BEDROCK`` is READ by the chain
   but is NOT in ``_engine_cache_key``. That is a production gap, not
   a test gap, so it is not asserted here; instead
   :func:`test_denoiser_bedrock_link_model_default_and_override` pins
   the read directly, which is the only guard that variable has today.

R86-D Deployer Graph-Hop (deterministic 1-hop expansion)
--------------------------------------------------------
1. Disabled when ``REGENOLD_DEPLOYER_HOP=0`` — returns the input
   list unchanged.
2. Trigger fires on ``intent`` containing "deployer" OR ``intent ==
   "role_obligations"`` OR the question's literal substring contains
   "deployer". All three are independent triggers.
3. Hop targets are APPENDED — never displaces a BM25 winner. Cap of
   3 new refs per call (over-citation guard, mirrors R47 trade-off).
4. Hop targets are deduped against both existing candidates AND
   against each other.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.routes.regenold import (
    _ONTOLOGY_HOP_MAP,
    _ONTOLOGY_HOP_MAX_INJECT,
    _apply_ontology_hops,
    _engine_cache_key,
    _is_query_denoiser_enabled,
    _rewrite_multiturn_query,
)


# ─── R86 Query De-Noiser ───────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _denoiser_chain_isolated(monkeypatch):
    """R377 — no AMBIENT provider may join the ``groq -> bedrock`` chain.

    Was ``_wrapper_provider_available`` (R330), which pinned
    ``P2P_GRAPH_RAG_PROVIDER=openai_wrapper`` so the cli gate env could not
    switch the WRAPPER candidate off. That candidate is gone — the chain is
    Groq -> Bedrock now and neither link reads ``P2P_GRAPH_RAG_PROVIDER`` — so
    the un-pin decides nothing here and is retired.

    ⚠ The hazard R330 was really about is unchanged, and is why this fixture
    survives in a new form: a candidate the test did NOT install makes the
    ``returns_none`` tests pass for the WRONG REASON — they assert ``None``,
    and ``no_provider`` also returns ``None``, so they go green while
    exercising nothing. Both links are therefore left UNCONFIGURED here (the
    real gate functions still run and resolve to False on an empty key), and
    each test installs exactly the one link it is about via
    :func:`_install_groq_denoiser` / :func:`_install_bedrock_denoiser`.
    """
    for _var in (
        # Primary link.
        "GROQ_API_KEY",
        "REGENOLD_INTENT_PROVIDER",
        # Fallback link — `is_bedrock_provider_enabled()` is a bare
        # key-presence check over this whole family (bearer token first).
        "AWS_BEARER_TOKEN_BEDROCK",
        "AWS_BEDROCK_BEARER_TOKEN",
        "BEDROCK_BEARER_TOKEN",
        "AWS_BEDROCK_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
    ):
        monkeypatch.setenv(_var, "")


def _install_groq_denoiser(monkeypatch, provider) -> None:
    """Wire ``provider`` as the PRIMARY (Groq) link of the R377 chain.

    ``_rewrite_multiturn_query`` re-imports both names from
    ``app.llm.openai_wrapper_provider`` on every call, so patching the module
    attributes is what the function actually sees.
    """
    from app.llm import openai_wrapper_provider as owp

    monkeypatch.setattr(owp, "is_groq_intent_provider_enabled", lambda: True)
    monkeypatch.setattr(owp, "get_groq_intent_provider", lambda: provider)


def _install_bedrock_denoiser(monkeypatch, provider) -> None:
    """Wire ``provider`` as the FALLBACK (Bedrock) link of the R377 chain.

    Bedrock is the candidate that replaced the Claude-Max wrapper, i.e. the
    link every de-noiser failure test in this file used to drive. The route
    imports ``is_bedrock_provider_enabled`` inside the function and looks up
    ``_BedrockDenoiserProvider`` as a module global, so both are patched at
    their definition sites.
    """
    from app.llm import bedrock_client as bc
    from app.routes import regenold as R

    monkeypatch.setattr(bc, "is_bedrock_provider_enabled", lambda: True)
    monkeypatch.setattr(R, "_BedrockDenoiserProvider", lambda: provider)


def _mk_msg(role: str, content: str):
    """Mirror the route's expected message shape (has .role + .content)."""
    m = MagicMock()
    m.role = role
    m.content = content
    return m


def test_denoiser_disabled_returns_none(monkeypatch) -> None:
    """REGENOLD_QUERY_DENOISER=0 → bail before any provider work."""
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "0")
    assert _is_query_denoiser_enabled() is False
    out = _rewrite_multiturn_query(
        "What else?", [_mk_msg("user", "What is Article 13?")]
    )
    assert out is None


def test_denoiser_default_is_enabled(monkeypatch) -> None:
    """Unset env → default ON (per the R86 ship-default-ON brief)."""
    monkeypatch.delenv("REGENOLD_QUERY_DENOISER", raising=False)
    assert _is_query_denoiser_enabled() is True


def test_denoiser_no_history_returns_none(monkeypatch) -> None:
    """Empty history is the single-turn path — no rewrite needed."""
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
    assert _rewrite_multiturn_query("What is Article 13?", []) is None


def test_denoiser_no_provider_returns_none(monkeypatch) -> None:
    """No Groq + no Bedrock configured → return None (caller falls back).

    R377 — the second half of this premise used to be "no wrapper". The
    wrapper candidate is deleted, so the OTHER link that must be absent is
    Bedrock. Deliberately driven through the REAL gate functions (only the
    credentials are cleared), because "no provider configured" is a statement
    about env resolution, not about a patched boolean.
    """
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
    monkeypatch.delenv("REGENOLD_INTENT_PROVIDER", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    for _aws in (
        "AWS_BEARER_TOKEN_BEDROCK",
        "AWS_BEDROCK_BEARER_TOKEN",
        "BEDROCK_BEARER_TOKEN",
        "AWS_BEDROCK_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
    ):
        monkeypatch.delenv(_aws, raising=False)

    out = _rewrite_multiturn_query(
        "What about deployers?",
        [_mk_msg("user", "What is Article 13?")],
    )
    assert out is None


def test_denoiser_returns_none_on_provider_error(monkeypatch) -> None:
    """LLM call returns error → de-noiser returns None.

    R377 — driven through the BEDROCK link (the chain's fallback, which
    replaced the Claude-Max wrapper this test used to drive). It is the only
    candidate installed, so an ``.error`` response exhausts the chain exactly
    as the wrapper's did.
    """
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")

    fake_resp = MagicMock()
    fake_resp.error = "network_error: timed out"
    fake_resp.text = ""
    fake_provider = MagicMock()
    fake_provider.complete.return_value = fake_resp
    _install_bedrock_denoiser(monkeypatch, fake_provider)

    out = _rewrite_multiturn_query(
        "What about deployers?",
        [_mk_msg("user", "What is Article 13?")],
    )
    assert out is None
    # Guard against the R330 false-green: the mock must actually be consulted.
    assert fake_provider.complete.call_count == 1


def test_denoiser_returns_none_on_empty_text(monkeypatch) -> None:
    """LLM returns empty .text → bail rather than ship blank query."""
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")

    fake_resp = MagicMock()
    fake_resp.error = None
    fake_resp.text = "   "  # all whitespace
    fake_provider = MagicMock()
    fake_provider.complete.return_value = fake_resp
    # R377 — Bedrock is the chain's fallback link (was the wrapper).
    _install_bedrock_denoiser(monkeypatch, fake_provider)

    out = _rewrite_multiturn_query(
        "What about deployers?",
        [_mk_msg("user", "What is Article 13?")],
    )
    assert out is None
    assert fake_provider.complete.call_count == 1


def test_denoiser_returns_none_when_too_short(monkeypatch) -> None:
    """< 10-char rewrites are suspicious — bail to fallback path."""
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")

    fake_resp = MagicMock()
    fake_resp.error = None
    fake_resp.text = "Art. 13?"  # 8 chars
    fake_provider = MagicMock()
    fake_provider.complete.return_value = fake_resp
    # R377 — Bedrock is the chain's fallback link (was the wrapper).
    _install_bedrock_denoiser(monkeypatch, fake_provider)

    out = _rewrite_multiturn_query(
        "What about deployers?",
        [_mk_msg("user", "What is Article 13?")],
    )
    assert out is None
    assert fake_provider.complete.call_count == 1


def test_denoiser_returns_none_when_too_long(monkeypatch) -> None:
    """> 500-char rewrites mean the LLM ignored the rule — bail."""
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")

    fake_resp = MagicMock()
    fake_resp.error = None
    fake_resp.text = "x" * 600
    fake_provider = MagicMock()
    fake_provider.complete.return_value = fake_resp
    # R377 — Bedrock is the chain's fallback link (was the wrapper).
    _install_bedrock_denoiser(monkeypatch, fake_provider)

    out = _rewrite_multiturn_query(
        "What about deployers?",
        [_mk_msg("user", "What is Article 13?")],
    )
    assert out is None
    assert fake_provider.complete.call_count == 1


def test_denoiser_returns_rewritten_text_on_happy_path(monkeypatch) -> None:
    """Valid LLM response → returns the cleaned rewrite (strips quotes).

    R377 — driven through the BEDROCK link. The adapter returns a
    ``BedrockResponse``, which carries the same ``.text`` / ``.error`` /
    ``.finish_reason`` surface the wrapper response did, so the post-response
    cleaning under test is unchanged by the chain swap.
    """
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")

    fake_resp = MagicMock()
    fake_resp.error = None
    fake_resp.finish_reason = "stop"
    fake_resp.text = '"deployer transparency obligations Art. 26"'
    fake_provider = MagicMock()
    fake_provider.complete.return_value = fake_resp
    _install_bedrock_denoiser(monkeypatch, fake_provider)

    out = _rewrite_multiturn_query(
        "What about deployers?",
        [_mk_msg("user", "What is Article 13?")],
    )
    # Quotes stripped, content preserved
    assert out == "deployer transparency obligations Art. 26"


def test_denoiser_uses_three_second_timeout(monkeypatch) -> None:
    """Timeout MUST be 3.0s — openai/gpt-oss-120b needs headroom for system overhead.

    R377 — driven through the GROQ link, which is the one this test is about:
    the budget is sized against the Groq Stage-0 model, and Groq is still the
    chain's PRIMARY candidate. The per-provider fail-fast applies to every
    link, so asserting it on the head of the chain is the same property.
    """
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
    monkeypatch.delenv("REGENOLD_INTENT_PROVIDER", raising=False)

    fake_resp = MagicMock()
    fake_resp.error = None
    fake_resp.finish_reason = "stop"
    fake_resp.text = "deployer obligations under Art. 26"
    fake_provider = MagicMock()
    fake_provider.complete.return_value = fake_resp
    _install_groq_denoiser(monkeypatch, fake_provider)

    _rewrite_multiturn_query(
        "What about deployers?",
        [_mk_msg("user", "What is Article 13?")],
    )
    # The request object passed to provider.complete carries timeout_seconds
    sent_req = fake_provider.complete.call_args.args[0]
    assert sent_req.timeout_seconds == 3.0, (
        "Denoiser timeout must be 3.0s — Groq model system "
        "overhead routinely exceeds 1.0s; 3.0s gives headroom while still "
        "being negligible against the ~28s multi-turn p50."
    )


def test_denoiser_bedrock_link_model_default_and_override(monkeypatch) -> None:
    """Bedrock link sends sonnet-4-6 by default and honours its override.

    ⚠ REVIEWER ADDITION (R377). The wrapper link this file used to drive was
    at least named by its patch target; the Bedrock link that replaced it is
    named by :func:`_install_bedrock_denoiser` — but NOTHING on either side of
    the swap ever pinned the MODEL that link sends. Two things make that blind
    spot load-bearing now in a way it was not in the wrapper era:

      * a Stage-0 query rewrite must not silently drift up to the frontier
        tier — it is a utility task, and sonnet-4-6 also avoids paying an
        entitlement-403 round-trip on a key minted before sonnet-5 shipped
        (the reason the route comments give for this exact default); and
      * ``REGENOLD_DENOISER_MODEL_BEDROCK`` is absent from
        ``_engine_cache_key`` (see the module docstring's invariant 4), so
        the R30/R56/R79 cache-poisoning guard cannot see it move. Until that
        production gap is closed, this is the only assertion in the tree that
        proves the override is read at all.

    Mirrors :func:`test_denoiser_uses_three_second_timeout`: deref the request
    object handed to ``provider.complete``.
    """
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
    monkeypatch.delenv("REGENOLD_DENOISER_MODEL_BEDROCK", raising=False)

    fake_resp = MagicMock()
    fake_resp.error = None
    fake_resp.finish_reason = "stop"
    fake_resp.text = "deployer obligations under Art. 26"
    fake_provider = MagicMock()
    fake_provider.complete.return_value = fake_resp
    _install_bedrock_denoiser(monkeypatch, fake_provider)

    _rewrite_multiturn_query(
        "What about deployers?",
        [_mk_msg("user", "What is Article 13?")],
    )
    assert fake_provider.complete.call_args.args[0].model == (
        "eu.anthropic.claude-sonnet-4-6"
    ), (
        "Bedrock de-noiser link must default to the Stage-0 utility tier — a "
        "100-token rewrite does not buy the frontier model, and this pin is "
        "what keeps the default from drifting silently."
    )

    # The override must actually be read (it is unkeyed in the cache key).
    fake_provider.complete.reset_mock()
    monkeypatch.setenv(
        "REGENOLD_DENOISER_MODEL_BEDROCK", "eu.anthropic.claude-opus-5"
    )
    _rewrite_multiturn_query(
        "What about deployers?",
        [_mk_msg("user", "What is Article 13?")],
    )
    assert (
        fake_provider.complete.call_args.args[0].model
        == "eu.anthropic.claude-opus-5"
    ), "REGENOLD_DENOISER_MODEL_BEDROCK must override the Bedrock link model."


def test_denoiser_env_vars_in_cache_key(monkeypatch) -> None:
    """REGENOLD_QUERY_DENOISER + model overrides must be in cache identity.

    R30/R56/R79 cache-poisoning doctrine: any env var that flips engine
    or pre-engine behaviour must be folded into the cache key, otherwise
    a runtime flip serves stale entries.
    """
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
    key_on = _engine_cache_key("test question", None)
    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "0")
    key_off = _engine_cache_key("test question", None)
    assert key_on != key_off

    monkeypatch.setenv("REGENOLD_QUERY_DENOISER", "1")
    monkeypatch.setenv("REGENOLD_DENOISER_MODEL", "claude-haiku-4-5-20251001")
    key_haiku = _engine_cache_key("test question", None)
    monkeypatch.setenv("REGENOLD_DENOISER_MODEL", "claude-sonnet-4-6")
    key_sonnet = _engine_cache_key("test question", None)
    assert key_haiku != key_sonnet

    # R377 — the model override that the CURRENT chain actually reads on its
    # primary link. ``REGENOLD_DENOISER_MODEL`` above is the pre-R377
    # wrapper-era override and is no longer read by
    # ``_rewrite_multiturn_query``; the two live overrides are
    # ``REGENOLD_DENOISER_MODEL_GROQ`` (asserted here) and
    # ``REGENOLD_DENOISER_MODEL_BEDROCK``.
    # ⚠ Only the Groq one is in the cache key today — see the report note on
    # the unkeyed Bedrock override; not asserted here because that is a
    # production-side gap, not a test-side one.
    monkeypatch.setenv("REGENOLD_DENOISER_MODEL_GROQ", "openai/gpt-oss-120b")
    key_groq_a = _engine_cache_key("test question", None)
    monkeypatch.setenv("REGENOLD_DENOISER_MODEL_GROQ", "llama-3.3-70b-versatile")
    key_groq_b = _engine_cache_key("test question", None)
    assert key_groq_a != key_groq_b


# ─── R86-D Deployer Graph-Hop ─────────────────────────────────────────────


def test_deployer_hop_disabled_returns_input_unchanged(monkeypatch) -> None:
    """REGENOLD_ONTOLOGY_HOP=0 → no-op, returns the list verbatim."""
    monkeypatch.setenv("REGENOLD_ONTOLOGY_HOP", "0")
    cands = ["Article 26", "Article 50"]
    out = _apply_ontology_hops(cands, "role_obligations", "deployer obligations?")
    assert out == cands


def test_deployer_hop_fires_on_role_obligations_intent(monkeypatch) -> None:
    """``intent == 'role_obligations'`` is an independent trigger."""
    monkeypatch.delenv("REGENOLD_ONTOLOGY_HOP", raising=False)
    cands = ["Article 26"]
    out = _apply_ontology_hops(cands, "role_obligations", "What about Art. 26?")
    # BM25 winner preserved at position 0
    assert out[0] == "Article 26"
    # Hop targets appended
    assert "Article 13" in out
    # Capped at MAX_INJECT
    assert len(out) - len(cands) <= _ONTOLOGY_HOP_MAX_INJECT


def test_deployer_hop_fires_on_deployer_in_intent_label(monkeypatch) -> None:
    """Any intent label containing 'deployer' fires the hop."""
    monkeypatch.delenv("REGENOLD_ONTOLOGY_HOP", raising=False)
    out = _apply_ontology_hops(
        ["Article 26"], "deployer_transparency", "Art. 26 obligations?"
    )
    assert "Article 13" in out or "Article 14" in out


def test_deployer_hop_fires_on_definitional_question(monkeypatch) -> None:
    """Definitional Wh-shape mentioning 'deployer' fires (Rule 3).

    R86 calibration: literal-substring trigger alone over-cited 339
    davidath scenario rows (Ref Loose −0.008). Restricting to Wh-shape
    definitional questions (not scenario openers) preserves the QA lift
    without polluting scenario precision.
    """
    monkeypatch.delenv("REGENOLD_ONTOLOGY_HOP", raising=False)
    out = _apply_ontology_hops(
        ["Article 26"], "", "What are deployer obligations?"
    )
    assert any(r in out for r in ("Article 13", "Article 14", "Article 9"))


def test_deployer_hop_skips_scenario_opener_with_deployer(monkeypatch) -> None:
    """Scenario opener 'We are a deployer ...' must NOT fire the hop.

    R86 calibration — scenario gold is single-anchor (Art. 26 alone);
    injecting provider-side hops adds non-gold tokens that drag Ref
    Loose Jaccard. Verified against davidath A/B (Ref Loose 0.5696 →
    0.5776 after this gate was added).
    """
    monkeypatch.delenv("REGENOLD_ONTOLOGY_HOP", raising=False)
    cands = ["Article 26"]
    out = _apply_ontology_hops(
        cands,
        "",  # no intent label (TestClient bench has no LLM provider)
        "We are a deployer of a high-risk CV-screening AI system.",
    )
    assert out == cands, (
        "Scenario opener should NOT trigger deployer hop — "
        "single-anchor gold gets polluted."
    )


def test_deployer_hop_skips_non_wh_statement_with_deployer(monkeypatch) -> None:
    """A bare statement mentioning 'deployer' is NOT a definitional Q."""
    monkeypatch.delenv("REGENOLD_ONTOLOGY_HOP", raising=False)
    cands = ["Article 26"]
    # No Wh-start, no '?'; not a scenario opener but not a question either
    out = _apply_ontology_hops(
        cands, "", "The deployer must keep logs.",
    )
    assert out == cands


def test_deployer_hop_skips_when_neither_signal_present(monkeypatch) -> None:
    """No deployer signal → no hop expansion."""
    monkeypatch.delenv("REGENOLD_ONTOLOGY_HOP", raising=False)
    cands = ["Article 26"]
    out = _apply_ontology_hops(cands, "definition", "What is an AI system?")
    assert out == cands  # unchanged


def test_deployer_hop_never_displaces_bm25_winner(monkeypatch) -> None:
    """Hop targets APPEND — original BM25 order at the top stays intact."""
    monkeypatch.delenv("REGENOLD_ONTOLOGY_HOP", raising=False)
    cands = ["Article 26", "Article 27", "Article 50"]
    out = _apply_ontology_hops(cands, "role_obligations", "deployer Q?")
    # First 3 positions = original BM25 winners
    assert out[:3] == cands


def test_deployer_hop_dedupes_against_existing_candidates(monkeypatch) -> None:
    """Article 13 already in candidates → not re-injected."""
    monkeypatch.delenv("REGENOLD_ONTOLOGY_HOP", raising=False)
    cands = ["Article 26", "Article 13"]  # Art. 13 already there
    out = _apply_ontology_hops(cands, "role_obligations", "deployer Q?")
    # Art. 13 not duplicated
    assert out.count("Article 13") == 1


def test_deployer_hop_dedupes_against_self(monkeypatch) -> None:
    """Art 26 → [13/14/9] and Art 26.5 → [13/14/9] — no dup-13/14/9."""
    monkeypatch.delenv("REGENOLD_ONTOLOGY_HOP", raising=False)
    cands = ["Article 26", "Article 26.5"]
    out = _apply_ontology_hops(cands, "role_obligations", "deployer Q?")
    # Each hop target appears at most once
    for r in ("Article 13", "Article 14", "Article 9"):
        assert out.count(r) <= 1


def test_deployer_hop_capped_at_max_inject(monkeypatch) -> None:
    """Cap protects against over-citation; mirrors R47 budget trade-off."""
    monkeypatch.delenv("REGENOLD_ONTOLOGY_HOP", raising=False)
    # All 3 deployer roots present → 6 unique hop targets available,
    # but the cap holds the total injection to MAX_INJECT (3).
    cands = ["Article 26", "Article 27", "Article 50"]
    out = _apply_ontology_hops(cands, "role_obligations", "deployer Q?")
    added = len(out) - len(cands)
    assert added <= _ONTOLOGY_HOP_MAX_INJECT


def test_deployer_hop_returns_new_list_not_mutated(monkeypatch) -> None:
    """Must not mutate the input list — downstream callers may iterate it."""
    monkeypatch.delenv("REGENOLD_ONTOLOGY_HOP", raising=False)
    cands = ["Article 26"]
    cands_id_before = id(cands)
    cands_snapshot = list(cands)
    out = _apply_ontology_hops(cands, "role_obligations", "deployer Q?")
    assert cands == cands_snapshot          # unchanged
    assert id(out) != cands_id_before        # genuinely a new list


def test_deployer_hop_env_var_in_cache_key(monkeypatch) -> None:
    """Flipping REGENOLD_ONTOLOGY_HOP must produce a distinct cache key."""
    monkeypatch.setenv("REGENOLD_ONTOLOGY_HOP", "1")
    key_on = _engine_cache_key("deployer obligations?", None)
    monkeypatch.setenv("REGENOLD_ONTOLOGY_HOP", "0")
    key_off = _engine_cache_key("deployer obligations?", None)
    assert key_on != key_off


def test_deployer_hop_map_endpoints_are_well_shaped() -> None:
    """Every source key + target value matches the AI-Act ref shape.

    Cheap structural check that prevents typos like 'Article  26' (two
    spaces) or 'Art. 26' (wire-internal canonical) from polluting the
    map. Wire-facing format is ``Article N`` / ``Annex <Roman>``.
    """
    import re
    art_re = re.compile(r"^Article\s+\d+(\.\d+)?$")
    annex_re = re.compile(r"^Annex\s+[IVXLCDM]+(?:\.\d+)?$")
    for src, targets in _ONTOLOGY_HOP_MAP.items():
        assert art_re.match(src) or annex_re.match(src), f"bad source key {src!r}"
        assert isinstance(targets, list) and targets, f"empty targets for {src!r}"
        for t in targets:
            assert art_re.match(t) or annex_re.match(t), f"bad target {t!r}"
