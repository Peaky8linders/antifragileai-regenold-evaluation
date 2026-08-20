"""R377 — end-to-end wiring pins for the OpenRouter Stage-2 configuration.

Validated in-process with the HTTP boundary stubbed, so the real body builder,
model routing, thinking budget, rollover chain and cross-provider fallback all
execute. Live provider calls are NOT possible from CI (no keys, egress denied),
which is exactly why these pins exist.
"""
from __future__ import annotations

import threading

import pytest

import app.engines.cohere_rerank as CR
import app.llm.bedrock_client as B
import app.llm.openai_wrapper_provider as W


# ── OpenRouter body builder: model + thinking routing ──────────────────────
class _Resp:
    status_code = 200
    text = "{}"
    def __init__(self, body): self._b = body
    def json(self): return self._b


def _body_for(model: str, reasoning_budget: int, base: str = "https://openrouter.ai/api/v1") -> dict:
    captured: dict = {}

    class _FakeHTTP:
        def post(self, url, json=None, **kw):
            captured.update(json or {})
            return _Resp({
                "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                "model": model,
            })

    p = W._OpenAIWrapperProvider.__new__(W._OpenAIWrapperProvider)
    p.__dict__.update({"_base_url": base, "_api_key": "k", "_timeout": 10.0,
                       "_client": _FakeHTTP(), "_lock": threading.Lock()})
    p.complete(W.OpenAIWrapperRequest(system="s", user="u", model=model, max_tokens=64,
                                      temperature=0.0, reasoning_max_tokens=reasoning_budget))
    return captured


class TestOpenRouterStage2Routing:
    """Opus 5 + 2048 thinking for complex, Sonnet 5 for simple."""

    def test_the_shipped_model_defaults_are_opus5_and_sonnet5(self) -> None:
        from app.engines._graph_rag_impl import (
            _OPENROUTER_COMPLEX_MODEL_DEFAULT,
            _OPENROUTER_STAGE2_MODEL_DEFAULT,
        )
        assert _OPENROUTER_STAGE2_MODEL_DEFAULT == "anthropic/claude-sonnet-5"
        assert _OPENROUTER_COMPLEX_MODEL_DEFAULT == "anthropic/claude-opus-5"

    def test_complex_thinking_budget_is_2048(self) -> None:
        from app.config import settings
        assert settings.graph_rag.complex_thinking_tokens == 2048
        assert settings.graph_rag.stage2_model == "claude-sonnet-5"
        assert settings.graph_rag.complex_model == "claude-opus-5"

    def test_thinking_is_sent_as_the_unified_reasoning_object(self) -> None:
        body = _body_for("anthropic/claude-opus-5", 2048)
        assert body["reasoning"] == {"max_tokens": 2048, "exclude": False}

    def test_anthropic_thinking_forces_temperature_one(self) -> None:
        """Anthropic rejects temperature != 1 with extended thinking; the repo's
        own Bedrock builder already enforces it (THINK-TEMP-05)."""
        assert _body_for("anthropic/claude-opus-5", 2048)["temperature"] == 1.0

    def test_no_thinking_leaves_temperature_alone(self) -> None:
        body = _body_for("anthropic/claude-sonnet-5", 0)
        assert body["temperature"] == 0.0
        assert "reasoning" not in body

    def test_non_anthropic_models_are_not_temperature_forced(self) -> None:
        assert _body_for("deepseek/deepseek-v4-flash", 2048)["temperature"] == 0.0


class TestBedrockFallbackParity:
    """R377 — Bedrock was the ONE Stage-2 transport with no thinking budget, so a
    cross-provider failover silently downgraded reasoning on complex questions."""

    def _budget(self, *, complex_question: bool, stage_name: str = "Stage 2 (Polishing)") -> int:
        seen: list[int] = []

        def _fake(req, fallbacks=None, **kw):
            seen.append(getattr(req, "thinking_budget", 0))
            return B.BedrockResponse(text="An answer under Article 53(1)(a).",
                                     model=req.model, finish_reason="end_turn")

        import app.engines._graph_rag_impl as G
        orig = B.complete_with_fallback
        orig_enabled = B.is_bedrock_provider_enabled
        B.complete_with_fallback = _fake
        B.is_bedrock_provider_enabled = lambda: True
        try:
            G._bedrock_complete_for_graph_rag(
                system="s", user="u", max_tokens=4096, temperature=0.0,
                complex_question=complex_question, stage_name=stage_name,
            )
        finally:
            B.complete_with_fallback = orig
            B.is_bedrock_provider_enabled = orig_enabled
        return seen[0] if seen else -1

    def test_complex_stage2_gets_the_2048_budget(self) -> None:
        assert self._budget(complex_question=True) == 2048

    def test_simple_stage2_gets_no_thinking(self) -> None:
        assert self._budget(complex_question=False) == 0

    def test_stage1_never_burns_a_thinking_budget(self) -> None:
        assert self._budget(complex_question=True, stage_name="Stage 1 (Parse)") == 0

    def test_the_off_switch_works(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_BEDROCK_STAGE2_THINKING", "0")
        assert self._budget(complex_question=True) == 0

    def test_the_flag_is_cache_keyed(self) -> None:
        """Engine-level: the two arms must be cache-distinct or an in-process
        A/B measures nothing (CLAUDE.md's most expensive recurring bug)."""
        import inspect

        from app.routes import regenold as R
        assert "REGENOLD_BEDROCK_STAGE2_THINKING" in inspect.getsource(R._engine_cache_key)


class TestRerankWiring:
    """The rerank REORDERS the citation set, so it is reference-affecting."""

    def _stub(self, monkeypatch: pytest.MonkeyPatch, n_reverse: bool = True):
        calls: list[dict] = []

        class _FC:
            def post(self, url, json=None, headers=None, **kw):
                p = json or {}
                calls.append(p)
                n = len(p.get("documents") or [])
                order = list(reversed(range(n))) if n_reverse else list(range(n))
                return _Resp({"results": [{"index": i, "relevance_score": 1.0 - k / max(n, 1)}
                                          for k, i in enumerate(order)]})

        monkeypatch.setattr(CR, "_get_client", lambda: _FC())
        monkeypatch.setenv("COHERE_API_KEY", "test")
        monkeypatch.setenv("REGENOLD_COHERE_RERANK", "1")
        return calls

    def test_rerank_applies_a_permutation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._stub(monkeypatch)
        CR.reset_request_budget()
        refs = ["Art. 13", "Art. 26", "Art. 50", "Art. 5"]
        out, ok = CR.rerank_pool("transparency obligations", refs, text_for=lambda r: f"text of {r}")
        assert ok is True
        assert sorted(out) == sorted(refs)   # permutation-safe
        assert out != refs                   # and it actually reordered

    def test_v4_sends_the_larger_per_doc_token_cap(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = self._stub(monkeypatch)
        CR.reset_request_budget()
        CR.rerank_pool("q", ["Art. 13", "Art. 26"], text_for=lambda r: f"text of {r}")
        assert calls[0]["model"] == "rerank-v4.0-pro"
        assert calls[0]["max_tokens_per_doc"] == 16384

    def test_the_per_request_budget_is_enforced(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = self._stub(monkeypatch)
        CR.reset_request_budget()          # default 2
        for _ in range(5):
            CR.rerank_pool("q", ["Art. 13", "Art. 26"], text_for=lambda r: f"text of {r}")
        assert len(calls) == 2, "the 5-call cascade must be capped at the budget"

    def test_rerank_is_recorded_in_the_reasoning_trace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Provenance must reach the durable artifact — nothing in the eval
        pipeline reads logs, which is how a rate-limited reranker reads as a
        clean wash rather than as INERT."""
        self._stub(monkeypatch)
        notes: list[str] = []
        import app.integrations.regenold.reasoning_trace as RT
        monkeypatch.setattr(RT, "record_note", lambda n: notes.append(n))
        CR.reset_request_budget()
        CR.rerank_pool("q", ["Art. 13", "Art. 26"], text_for=lambda r: f"text of {r}")
        assert any(n.startswith("rerank_applied ") for n in notes), notes
        assert any("model=rerank-v4.0-pro" in n for n in notes), notes


class TestGraphBackendDefault:
    """The hosted Aura graph is the DEFAULT backend; an inverted comment here is
    how an audit concludes the graph is inactive when it is serving every
    request (R318 fixed the sibling; R377 fixed this copy)."""

    def test_neo4j_is_the_default_backend(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("REGENOLD_GRAPH_BACKEND", raising=False)
        from app.graph.embedded_graph import graph_backend, neo4j_backend_selected
        assert graph_backend() == "neo4j"
        assert neo4j_backend_selected() is True

    def test_embedded_must_be_explicit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REGENOLD_GRAPH_BACKEND", "embedded")
        from app.graph.embedded_graph import neo4j_backend_selected
        assert neo4j_backend_selected() is False
