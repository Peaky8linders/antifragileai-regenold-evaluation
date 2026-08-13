"""R328.2 — prove the entitlement fallback is WIRED, not just defined.

CLAUDE.md's standing lesson: "Before concluding a fix is safe-because-flat,
prove it FIRES." A `complete_with_fallback` that exists but is never reached
from the RAG path or the judge path is the inert-feature trap — and both call
sites previously called `provider.complete()` directly, so a careless revert
would silently unwire them while every unit test still passed.

These tests assert the CALL EDGE, not the chain logic (that lives in
``test_bedrock_client.py::TestEntitlementFallback``).
"""
from __future__ import annotations

import os

import pytest

@pytest.fixture(scope="module", autouse=True)
def _contain_dotenv_leak():
    """Snapshot the WHOLE environment, let imports pollute it, then restore.

    ``evals.judge.runner`` calls ``load_dotenv()`` at import time, which pulls
    the real ``.env`` into ``os.environ`` for the REST OF THE SESSION. The
    credential tests in ``test_bedrock_client.py`` assert on an unconfigured
    environment, so without this guard importing the judge module here breaks
    five unrelated tests in a different file — order-dependent, and invisible
    until both files run together.

    Restore everything, not an allowlist of AWS keys: ``.env`` also carries
    ``GROQ_API_KEY``, ``P2P_GRAPH_RAG_PROVIDER``, ``OPENAI_API_BASE``, the
    ``NEO4J_*`` set and the answer-cap flags. CLAUDE.md records ``GROQ_API_KEY``
    alone moving this suite between 63 and 92 failures on the same commit, so a
    partial guard is a latent version of the same bug.
    """
    before = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(before)


class _Recorder:
    """Stands in for ``complete_with_fallback`` and records that it was hit."""

    def __init__(self, text: str = "an answer", model: str = "eu.anthropic.claude-opus-4-6-v1"):
        self.hits = 0
        self.last_req = None
        self._text = text
        self._model = model

    def __call__(self, req, **kwargs):
        from app.llm.bedrock_client import BedrockResponse

        self.hits += 1
        self.last_req = req
        return BedrockResponse(text=self._text, model=self._model)


class TestRagPathUsesFallback:
    def test_bedrock_complete_for_graph_rag_routes_through_fallback(
        self, monkeypatch
    ) -> None:
        import app.llm.bedrock_client as bc
        from app.engines import _graph_rag_impl as impl

        rec = _Recorder(text="Social scoring is prohibited under Article 5(1)(c).")
        monkeypatch.setattr(bc, "complete_with_fallback", rec)
        monkeypatch.setattr(bc, "is_bedrock_provider_enabled", lambda: True)

        out = impl._bedrock_complete_for_graph_rag(
            system="sys", user="Is social scoring allowed?",
            max_tokens=256, temperature=0.0, stage_name="Stage 2",
        )

        assert rec.hits == 1, "RAG path bypassed complete_with_fallback"
        assert out == "Social scoring is prohibited under Article 5(1)(c)."

    def test_rag_path_requests_the_pinned_model(self, monkeypatch) -> None:
        """The pin is what we ASK for; the chain decides what answers."""
        import app.llm.bedrock_client as bc
        from app.engines import _graph_rag_impl as impl

        rec = _Recorder()
        monkeypatch.setattr(bc, "complete_with_fallback", rec)
        monkeypatch.setattr(bc, "is_bedrock_provider_enabled", lambda: True)
        monkeypatch.delenv("REGENOLD_BEDROCK_MODEL", raising=False)
        monkeypatch.delenv("REGENOLD_BEDROCK_STAGE1_MODEL", raising=False)

        impl._bedrock_complete_for_graph_rag(
            system="s", user="u", max_tokens=64, temperature=0.0,
            stage_name="Stage 1",
        )

        assert rec.last_req.model == "eu.anthropic.claude-opus-4-8"

    def test_complex_tier_requests_the_complex_pin(self, monkeypatch) -> None:
        import app.llm.bedrock_client as bc
        from app.engines import _graph_rag_impl as impl

        rec = _Recorder()
        monkeypatch.setattr(bc, "complete_with_fallback", rec)
        monkeypatch.setattr(bc, "is_bedrock_provider_enabled", lambda: True)
        monkeypatch.delenv("REGENOLD_BEDROCK_COMPLEX_MODEL", raising=False)

        impl._bedrock_complete_for_graph_rag(
            system="s", user="u", max_tokens=64, temperature=0.0,
            complex_question=True, stage_name="Stage 2",
        )

        assert rec.last_req.model == "eu.anthropic.claude-opus-5"


class TestJudgePathUsesFallback:
    def test_call_judge_bedrock_routes_through_fallback(self, monkeypatch) -> None:
        import app.llm.bedrock_client as bc
        from evals.judge import runner

        rec = _Recorder(
            text='{"score": 1.0, "reason": "ok"}',
            model="eu.anthropic.claude-sonnet-4-6",
        )
        monkeypatch.setattr(bc, "complete_with_fallback", rec)
        monkeypatch.setattr(bc, "is_bedrock_provider_enabled", lambda: True)

        out = runner._call_judge_bedrock("grade this", timeout_s=10.0)

        assert rec.hits == 1, "judge path bypassed complete_with_fallback"
        assert "judge_error" not in out
        assert out["score"] == 1.0

    def test_judge_honours_the_env_model_pin(self, monkeypatch) -> None:
        import app.llm.bedrock_client as bc
        from evals.judge import runner

        rec = _Recorder(text='{"score": 0.5}')
        monkeypatch.setattr(bc, "complete_with_fallback", rec)
        monkeypatch.setattr(bc, "is_bedrock_provider_enabled", lambda: True)
        monkeypatch.setenv(
            "REGENOLD_BEDROCK_JUDGE_MODEL", "eu.anthropic.claude-sonnet-5"
        )

        runner._call_judge_bedrock("grade this", timeout_s=10.0)

        assert rec.last_req.model == "eu.anthropic.claude-sonnet-5"

    def test_judge_surfaces_a_chain_exhaustion_as_judge_error(
        self, monkeypatch
    ) -> None:
        """All-denied must be a VISIBLE error, never a silently unscored axis."""
        import app.llm.bedrock_client as bc
        from evals.judge import runner

        def _all_denied(req, **kwargs):
            return bc.BedrockResponse(
                error="api_access_denied_403", model=req.model
            )

        monkeypatch.setattr(bc, "complete_with_fallback", _all_denied)
        monkeypatch.setattr(bc, "is_bedrock_provider_enabled", lambda: True)

        out = runner._call_judge_bedrock("grade this", timeout_s=10.0)

        assert "judge_error" in out
        assert "api_access_denied_403" in out["judge_error"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
