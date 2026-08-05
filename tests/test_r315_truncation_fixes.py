"""R315 — truncations that silently starved the model of EU AI Act grounding.

Three defects found by the grounding/truncation audit against the settled
rebased base, each verified in code and reproduced here:

1. ``_shrink_user_for_groq`` — the Groq fallback sliced the user message
   head+tail, deleting the MIDDLE, which is exactly where the
   ``EU AI ACT REFERENCES`` and ``VERBATIM PROVISION TEXT`` blocks sit.
2. ``system_context`` was tail-sliced, deleting the opening sentence that
   says what the system does — the text that decides the risk tier.
3. The conversation-history window was the binding constraint on
   multi-turn once R314 lifted the character cap.
"""

from __future__ import annotations

from app.engines._graph_rag_impl import _shrink_user_for_groq
from app.integrations.regenold.models import RegenoldChatMessage
from app.routes.regenold import _build_question_from_history


def _stage2_user_message(history_chars: int = 20_000) -> str:
    """A user message shaped like the real Stage-2 payload."""
    hist = "Conversation so far:\n" + (
        "User: earlier turn about logs.\nAssistant: a long regulatory answer. "
        * (history_chars // 68)
    )
    refs = "EU AI ACT REFERENCES\n" + "".join(
        f"Article {n} - summary stub for article {n}. " * 12 for n in (11, 18, 23)
    )
    verbatim = (
        "VERBATIM PROVISION TEXT (supporting context)\n"
        "[Annex IV point 1(e)] SENTINEL_HARDWARE a description of the hardware "
        "on which the AI system is intended to run. "
        + ("filler statutory prose. " * 120)
    )
    return (
        f"{hist}Latest question:\nDoes Annex IV require hardware specs?\n\n"
        f"{refs}\n\n{verbatim}\n"
    )


class TestGroqShrinkPreservesGrounding:
    def test_grounding_survives_the_shrink(self) -> None:
        out = _shrink_user_for_groq(_stage2_user_message(), budget=10_000)
        assert "Latest question:" in out
        assert "EU AI ACT REFERENCES" in out
        assert "VERBATIM PROVISION TEXT" in out
        assert "SENTINEL_HARDWARE" in out

    def test_old_head_tail_slice_would_have_lost_it(self) -> None:
        """Pins WHY this helper exists — the previous behaviour, reproduced."""
        user = _stage2_user_message()
        old = user[:8000] + "\n...TRUNC...\n" + user[-2000:]
        # Every one of these was lost on the Groq fallback path.
        assert "EU AI ACT REFERENCES" not in old
        assert "VERBATIM PROVISION TEXT" not in old
        assert "SENTINEL_HARDWARE" not in old

    def test_short_input_passes_through_unchanged(self) -> None:
        assert _shrink_user_for_groq("short message", 10_000) == "short message"

    def test_oversized_tail_keeps_the_front_of_the_block(self) -> None:
        """Question + references precede verbatim text, so keep the front."""
        tail = "Latest question:\nQ?\n\nEU AI ACT REFERENCES\n" + ("x" * 30_000)
        out = _shrink_user_for_groq("Conversation so far:\nold\n" + tail, budget=5_000)
        assert out.startswith("Latest question:")
        assert "EU AI ACT REFERENCES" in out
        assert len(out) <= 5_000


class TestSystemContextKeepsTheHead:
    def test_head_survives_not_the_tail(self) -> None:
        opening = "SENTINEL_OPENING We screen job applicants with an AI system."
        trailing = "SENTINEL_TRAILING boilerplate about our office locations."
        desc = opening + (" padding sentence." * 200) + trailing
        assert len(desc) > 1000

        msgs = [
            RegenoldChatMessage(role="system", content=desc),
            RegenoldChatMessage(role="user", content="Is this high-risk?"),
        ]
        _, system_context = _build_question_from_history(msgs)
        assert system_context is not None
        # The opening — which decides the risk tier — must survive.
        assert "SENTINEL_OPENING" in system_context
        assert len(system_context) <= 1000
