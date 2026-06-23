"""Regression tests for issue #150 — GraphRAG cache key omits history depth.

The route computes ``_history_turn_count`` from the prior conversation and
forwards it into the engine via ``GraphRAGRequest(history_turn_count=...)``,
where it gates the Stage-2 complex-question routing
(``app.engines.question_complexity.is_complex_question`` —  the
``history_turn_count >= 3`` short-coreferent branch swaps the polish model /
extended-thinking budget, which changes ``GraphRAGResponse.answer``).

But the LRU cache identity was built from
``_engine_cache_key(question, system_context)`` only — ``history_turn_count``
was never folded in. So a multi-turn follow-up whose rewritten ``question``
text collides with a cached single-turn entry (exactly what the R86 query
de-noiser produces — a standalone Wh-style query that can match a prior
single-turn ask) would serve the single-turn, non-complex-routed answer and
never re-run the engine for the multi-turn context.

Per this repo's cache-poisoning doctrine (R30 / R56 / R79): ANY input that
flips engine behaviour MUST be part of the cache key.
"""
from __future__ import annotations

import app.routes.regenold as rg
from app.config import settings
from app.routes.regenold import _engine_cache_key

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.main import app


def test_cache_key_distinguishes_history_depth() -> None:
    """Same (question, system_context), different history depth → distinct keys.

    A depth-0 (single-turn) and a depth-4 (multi-turn) request must NOT
    collide — the engine routes them differently via ``is_complex_question``.
    """
    q = "What are the obligations of deployers of high-risk AI systems?"
    k_single = _engine_cache_key(q, None, history_turn_count=0)
    k_multi = _engine_cache_key(q, None, history_turn_count=4)
    assert k_single != k_multi


def test_cache_key_stable_for_same_history_depth() -> None:
    """Same inputs incl. depth → identical key (cache must still hit)."""
    q = "What does Article 13 require?"
    a = _engine_cache_key(q, "ctx", history_turn_count=3)
    b = _engine_cache_key(q, "ctx", history_turn_count=3)
    assert a == b


def test_cache_key_two_arg_call_defaults_to_single_turn() -> None:
    """Backward-compat: the legacy 2-arg call equals an explicit depth-0 call."""
    assert _engine_cache_key("q", None) == _engine_cache_key(
        "q", None, history_turn_count=0
    )


def test_route_passes_history_depth_into_cache_key(monkeypatch) -> None:
    """The call site must forward the conversation depth, not the default 0.

    Spies on ``_engine_cache_key`` to capture the history-depth argument the
    route hands it for a 3-message (user/assistant/user) conversation. The
    route counts ``user+assistant`` turns minus one, so the expected depth is
    2. Before the fix the call site passed only ``(question, system_context)``
    so the captured depth would be 0 — the assertion fails (red).
    """
    settings.regenold.api_key = SecretStr("regenold-test-key")
    captured: dict[str, object] = {}
    real = rg._engine_cache_key

    def _spy(question, system_context, *args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = dict(kwargs)
        return real(question, system_context, *args, **kwargs)

    monkeypatch.setattr(rg, "_engine_cache_key", _spy)

    messages = [
        {"role": "user", "content": "We deploy a high-risk AI system for hiring."},
        {
            "role": "assistant",
            "content": "Article 26 sets out the obligations of deployers.",
        },
        {
            "role": "user",
            "content": (
                "What are the obligations of deployers of high-risk AI systems?"
            ),
        },
    ]
    c = TestClient(app)
    r = c.post(
        "/api/v1/regenold/eu-ai-act/ask",
        headers={"X-Regenold-Api-Key": "regenold-test-key"},
        json=messages,
    )
    assert r.status_code == 200, r.text

    def _captured_depth() -> int:
        if captured.get("args"):
            return int(captured["args"][0])  # type: ignore[index]
        kw = captured.get("kwargs") or {}
        return int(kw.get("history_turn_count", 0))  # type: ignore[union-attr]

    # 2 prior user+assistant turns precede the final question (3 - 1 = 2).
    assert _captured_depth() == 2
