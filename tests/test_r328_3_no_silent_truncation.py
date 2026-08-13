"""R328.3 — truncation must be impossible-or-loud, never silent.

Three independent surfaces cut content on the live Bedrock path, and each cut
without leaving evidence:

  1. Stage-2 hit Bedrock's HARD ``maxTokens`` ceiling (Bedrock honours it; the
     Claude-Max wrapper does not), and the returned ``stopReason`` — the one
     precise truncation signal available — was never read. Measured 2026-08-13
     at the then-ceiling of 1536: 3 of 4 enumerative questions came back
     ``stopReason=max_tokens``, cut mid-word.
  2. A KG context block that could not fit its budget was replaced by ``""``,
     so the whole provision hierarchy could vanish with no marker.
  3. The reasoning trace stopped recording at 32 notes — and every clamp in the
     pipeline reports itself ONLY via a note, so the audit trail truncated
     before the thing it audits.
"""
from __future__ import annotations

import os

import pytest


class _Resp:
    """Minimal BedrockResponse stand-in."""

    def __init__(self, text: str, finish_reason: str | None, out: int = 100):
        self.text = text
        self.finish_reason = finish_reason
        self.error = None
        self.model = "eu.anthropic.claude-opus-4-6-v1"
        self.output_tokens = out
        self.input_tokens = 10


@pytest.fixture()
def _bedrock_on(monkeypatch):
    import app.llm.bedrock_client as bc

    monkeypatch.setattr(bc, "is_bedrock_provider_enabled", lambda: True)
    return bc


class TestStopReasonIsRead:
    def test_max_tokens_stop_reason_rejects_the_answer(self, monkeypatch, _bedrock_on):
        """A cut answer must be rejected even when it ends in punctuation.

        This is the case the prose heuristics CANNOT catch: Bedrock stopped at
        the ceiling, but the last emitted token happened to be a full stop, so
        `_looks_structurally_truncated` sees a well-formed tail.
        """
        from app.engines import _graph_rag_impl as impl

        monkeypatch.setattr(
            _bedrock_on, "complete_with_fallback",
            lambda req, **kw: _Resp(
                "Two exceptions apply. The first is Article 50(2).",
                "max_tokens", out=4096,
            ),
        )

        out = impl._bedrock_complete_for_graph_rag(
            system="s", user="u", max_tokens=1536, temperature=0.0,
            stage_name="Stage 2 (Polishing)",
        )

        assert out is None, "a maxTokens cut shipped as a complete answer"

    def test_end_turn_answer_is_kept(self, monkeypatch, _bedrock_on):
        from app.engines import _graph_rag_impl as impl

        monkeypatch.setattr(
            _bedrock_on, "complete_with_fallback",
            lambda req, **kw: _Resp(
                "No. Social scoring is prohibited under Article 5(1)(c).",
                "end_turn",
            ),
        )

        out = impl._bedrock_complete_for_graph_rag(
            system="s", user="u", max_tokens=1536, temperature=0.0,
            stage_name="Stage 2 (Polishing)",
        )

        assert out and "Article 5(1)(c)" in out

    def test_truncation_is_recorded_in_the_trace(self, monkeypatch, _bedrock_on):
        """The cut must leave evidence where the eval pipeline can see it."""
        from app.engines import _graph_rag_impl as impl
        from app.integrations.regenold import reasoning_trace as rt

        monkeypatch.setattr(
            _bedrock_on, "complete_with_fallback",
            lambda req, **kw: _Resp("cut.", "max_tokens", out=4096),
        )

        trace = rt.activate()
        try:
            impl._bedrock_complete_for_graph_rag(
                system="s", user="u", max_tokens=1536, temperature=0.0,
                stage_name="Stage 2 (Polishing)",
            )
            notes = list(trace.notes)
        finally:
            rt.deactivate()

        assert any("stage2_truncated_max_tokens" in n for n in notes), notes

    def test_ceiling_is_raised_above_the_callers_advisory_budget(
        self, monkeypatch, _bedrock_on
    ):
        """1536 is advisory on the wrapper and a hard cut on Bedrock."""
        from app.engines import _graph_rag_impl as impl

        seen = {}

        def _capture(req, **kw):
            seen["max_tokens"] = req.max_tokens
            seen["timeout"] = req.timeout_seconds
            return _Resp("fine.", "end_turn")

        monkeypatch.setattr(_bedrock_on, "complete_with_fallback", _capture)
        monkeypatch.delenv("REGENOLD_BEDROCK_MAX_TOKENS", raising=False)
        monkeypatch.delenv("REGENOLD_BEDROCK_STAGE2_TIMEOUT_S", raising=False)

        impl._bedrock_complete_for_graph_rag(
            system="s", user="u", max_tokens=1536, temperature=0.0,
            stage_name="Stage 2 (Polishing)",
        )

        assert seen["max_tokens"] >= 4096, "Bedrock kept the advisory 1536 ceiling"
        # A bigger ceiling without a bigger read budget just relocates the cut
        # to the socket: the worst measured case took 70 s against a 60 s default.
        assert seen["timeout"] and seen["timeout"] > 60.0

    def test_ceiling_is_env_overridable(self, monkeypatch, _bedrock_on):
        from app.engines import _graph_rag_impl as impl

        seen = {}
        monkeypatch.setattr(
            _bedrock_on, "complete_with_fallback",
            lambda req, **kw: (seen.update(m=req.max_tokens), _Resp("ok.", "end_turn"))[1],
        )
        monkeypatch.setenv("REGENOLD_BEDROCK_MAX_TOKENS", "8192")

        impl._bedrock_complete_for_graph_rag(
            system="s", user="u", max_tokens=1536, temperature=0.0,
            stage_name="Stage 2 (Polishing)",
        )

        assert seen["m"] == 8192


class TestTruncationDetectorDoesNotEatMarkdown:
    """A formatting character is not a truncation.

    Measured live on Bedrock: a COMPLETE answer (stopReason=end_turn, 2215 of
    4096 tokens) ending ``*Sources: … Recitals 46-59.*`` was judged truncated on
    its closing ``*`` and discarded — which cost the polish AND re-armed the
    3-sentence cap, because ``set_answer_no_cap`` is gated on Stage-2 landing.
    """

    @pytest.mark.parametrize(
        "text,why",
        [
            ("*Sources: Regulation (EU) 2024/1689, Annex III; Recitals 46-59.*",
             "markdown italic footer — the live false positive"),
            ("The system is high-risk under **Article 6(2)**.", "bold then period"),
            ("| Role | Obligation |\n| Provider | Art. 16 |", "complete table row"),
            ("Answer is `Article 5(1)(c)`.", "inline code then period"),
            ("It is prohibited under Article 5.", "plain complete sentence"),
            ("(see Annex IV.)", "closing paren after the terminator"),
        ],
    )
    def test_complete_answers_are_not_flagged(self, text, why):
        from app.engines._graph_rag_impl import _looks_structurally_truncated

        assert not _looks_structurally_truncated(text), why

    @pytest.mark.parametrize(
        "text,why",
        [
            ("The provider must ensure the system is", "genuine mid-clause cut"),
            ("Two exceptions remove this obligation, namely", "cut after a comma"),
            ("**The operative provision is", "cut inside bold"),
            ("Assistive", "single-word cut — the live 1536-ceiling symptom"),
            ("| Role | Obligation |\n| Provider | Art. 16 and the deployer must",
             "cut mid-row, not at a row boundary"),
        ],
    )
    def test_real_cuts_are_still_caught(self, text, why):
        from app.engines._graph_rag_impl import _looks_structurally_truncated

        assert _looks_structurally_truncated(text), why


class TestKgBlockIsMarkedNotAnnihilated:
    def _block(self, units: int = 40) -> str:
        return "\n".join(
            ["- Article 5: prohibited practices"]
            + [f"  - 5(1)({chr(97 + i % 26)}): operative text {i}" for i in range(units)]
        )

    def test_tiny_budget_marks_instead_of_vanishing(self):
        from app.engines.kg_context import _fit_complete_lines

        out = _fit_complete_lines(self._block(), 40)

        assert out != "", "the whole block vanished with no marker"
        assert "[...]" in out
        assert len(out) <= 40

    def test_partial_fit_is_marked(self):
        from app.engines.kg_context import _fit_complete_lines

        block = self._block()
        out = _fit_complete_lines(block, 400)

        assert "[...]" in out, "content was dropped with no marker"
        assert len(out) <= 400

    def test_complete_fit_carries_no_marker(self):
        from app.engines.kg_context import _fit_complete_lines

        block = self._block(units=2)
        out = _fit_complete_lines(block, 100_000)

        assert out == block
        assert "[...]" not in out

    @pytest.mark.parametrize("budget", [1, 7, 8, 12, 39, 41, 250, 999, 5000])
    def test_never_exceeds_budget(self, budget):
        from app.engines.kg_context import _fit_complete_lines

        assert len(_fit_complete_lines(self._block(), budget)) <= budget


class TestTraceNoteCap:
    def test_cap_raised_and_overflow_is_announced(self):
        from app.integrations.regenold import reasoning_trace as rt

        trace = rt.activate()
        try:
            for i in range(200):
                rt.record_note(f"n{i}")
            notes = list(trace.notes)
        finally:
            rt.deactivate()

        assert len(notes) == 129, "old 32-note cap still in force"
        assert "truncated" in notes[-1]

    def test_a_realistic_note_volume_is_fully_retained(self):
        """The clamp notes a single live request emits must all survive."""
        from app.integrations.regenold import reasoning_trace as rt

        trace = rt.activate()
        try:
            for i in range(40):
                rt.record_note(f"clamp_event_{i}")
            notes = list(trace.notes)
        finally:
            rt.deactivate()

        assert len(notes) == 40
        assert all("truncated" not in n for n in notes)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
