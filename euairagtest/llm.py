"""§8 baseline #1: a frontier LLM with (optionally) the full Act in context.

This is the strong baseline the GraphRAG design has to beat. A single frontier
model is given the question (and, with ``--full-act``, the entire provision
corpus as context), answers in prose, and we extract citations from that prose
with :func:`euaiact.baselines.extract.extract_citations` -- so it is scored by
the exact same harness, on the exact same footing, as every other baseline.

Honesty gating (the whole point of §8 is *honest* numbers):
  * ``anthropic`` is imported lazily -- only this baseline needs it; the naive
    retrieval baseline and the scorer run with zero extra deps.
  * If the package, the ``ANTHROPIC_API_KEY``, or (for ``--full-act``) the
    corpus is missing, we raise a clear ``RuntimeError``. We never fabricate an
    answer, a citation, or a score.
  * A ``client`` can be injected (dependency injection) so the prompt-build and
    response-parse logic is unit-tested with **no** package, key, or network.

Model tiering: the default is Opus -- the correctness-compounding tier reserved
for final, citation-bearing answers, which is exactly what this produces.
Override with ``--model``.

Prompt caching: with ``--full-act`` the corpus is a large, static block reused
across every item, so it is sent as a ``cache_control=ephemeral`` system block
-- one cache write, then cache reads for the rest of the run.
"""

from __future__ import annotations

import os

from .base import Baseline, question_text
from .extract import extract_citations

__all__ = [
    "FrontierLLMBaseline",
    "DEFAULT_MODEL",
    "SYSTEM_INSTRUCTIONS",
    "format_provisions",
    "build_system_blocks",
    "build_user_message",
    "response_text",
]

# Correctness-compounding tier per the project's model-tiering constraint
# ("Opus for the final citation-bearing answer"). The exact ID string may advance
# and is NOT verified here against a live models endpoint -- override with
# ``--model`` if it has moved on.
DEFAULT_MODEL = "claude-opus-4-8"

SYSTEM_INSTRUCTIONS = (
    "You are a legal analyst answering questions strictly about the EU AI Act "
    "(Regulation (EU) 2024/1689).\n"
    "Cite the most specific provisions that apply -- article, paragraph, point, "
    "and sub-point where possible (e.g. \"Article 5(1)(a)\"), plus any relevant "
    "Annexes (e.g. \"Annex III point 5\") and Recitals (e.g. \"Recital 33\").\n"
    "Rules:\n"
    "- Cite ONLY the EU AI Act. If the answer turns on another instrument (the "
    "GDPR, another Regulation or Directive, the Charter, the TFEU), name that "
    "instrument explicitly -- never present its articles as AI Act articles.\n"
    "- If the AI Act does not address the question, say so plainly and cite "
    "nothing rather than guessing.\n"
    "- Prefer the specific paragraph over the bare article when it applies "
    "(Article 6(2), not Article 6)."
)


def format_provisions(provisions) -> str:
    """Render the corpus as a compact, citation-labelled context block.

    Each line is ``[<citation>] <text>`` -- the bracketed label is exactly what
    we ask the model to echo and what ``extract_citations`` parses back, so the
    model's citations round-trip cleanly to canonical ids."""
    return "\n".join(f"[{p.citation}] {p.text}" for p in provisions)


def build_system_blocks(provisions=None) -> list[dict]:
    """Build the ``system`` argument as a list of content blocks.

    Instructions always come first. With ``provisions`` the Act follows as a
    second block carrying ``cache_control=ephemeral`` -- that breakpoint caches
    the whole static prefix (instructions + Act), which is reused verbatim on
    every item in the run."""
    blocks: list[dict] = [{"type": "text", "text": SYSTEM_INSTRUCTIONS}]
    if provisions:
        blocks.append(
            {
                "type": "text",
                "text": (
                    "EU AI Act provisions -- cite by the bracketed label:\n\n"
                    + format_provisions(provisions)
                ),
                "cache_control": {"type": "ephemeral"},
            }
        )
    return blocks


def build_user_message(item: dict) -> str:
    """The per-item user turn: flattened question/scenario + a fixed answer format
    whose trailing ``Citations:`` line makes references easy to extract."""
    return (
        f"{question_text(item)}\n\n"
        "Answer in 2-4 sentences. Then, on a final line, list every EU AI Act "
        "provision you relied on, for example:\n"
        "Citations: Article 5(1)(a), Annex III point 5, Recital 33"
    )


def response_text(response) -> str:
    """Concatenate the text blocks of an Anthropic Messages response.

    Kept tiny and duck-typed so tests can pass a stub response with ``.content``
    blocks that expose ``.type`` and ``.text``."""
    return "\n".join(
        b.text for b in response.content if getattr(b, "type", None) == "text"
    )


class FrontierLLMBaseline(Baseline):
    """Frontier LLM baseline. Pass ``provisions`` for the full-Act-in-context
    variant, or leave it ``None`` for the closed-book variant."""

    name = "frontier-llm"

    def __init__(
        self,
        provisions=None,
        model: str | None = None,
        max_tokens: int = 1024,
        client=None,
    ) -> None:
        if client is None:
            client = self._make_client()
        self.client = client
        self.model = model or DEFAULT_MODEL
        self.max_tokens = max_tokens
        self._system = build_system_blocks(provisions)
        self.name = f"frontier-llm{'-fullact' if provisions else ''}:{self.model}"

    @staticmethod
    def _make_client():
        """Construct a real Anthropic client, or raise a clear error explaining
        exactly what is missing. Never silently degrades."""
        try:
            import anthropic
        except ModuleNotFoundError as e:  # optional dep not installed
            raise RuntimeError(
                "the frontier-LLM baseline needs the `anthropic` package -- "
                "install it with `uv sync --extra baselines` (or inject a client)."
            ) from e
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "the frontier-LLM baseline needs ANTHROPIC_API_KEY in the "
                "environment (or inject a client)."
            )
        return anthropic.Anthropic()

    def predict(self, item: dict) -> list[str]:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self._system,
            messages=[{"role": "user", "content": build_user_message(item)}],
        )
        return extract_citations(response_text(resp))
