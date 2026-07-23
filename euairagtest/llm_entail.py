"""LLM-as-NLI judge entailment scorer -- the API route around local torch.

This is the neural NLI slot filled via Anthropic's hosted API rather than a
local sentence-transformers CrossEncoder. ``LLMEntailmentScorer`` implements
the same :class:`~euaiact.baselines.verify.EntailmentScorer` ABC that
``NLIEntailmentScorer`` does; it is a drop-in for any code that consumes that
interface (``VerifiedBaseline``, etc.).

Honesty gating (same discipline as ``FrontierLLMBaseline``):
  * ``anthropic`` is imported lazily -- only this scorer needs it.
  * If the package or ``ANTHROPIC_API_KEY`` is missing we raise a clear
    ``RuntimeError``. We never fabricate a score.
  * A ``client`` can be injected (dependency injection) so the prompt-build and
    response-parse logic is unit-tested with no package, key, or network.

Model tiering: the default reuses ``DEFAULT_MODEL`` from ``llm.py`` (the
correctness-compounding Opus tier). Override with ``model`` if a faster/cheaper
tier is acceptable for your verification pass.

Verdict parsing: the model is instructed to reply with a strict JSON object
``{"supports": true|false, "confidence": 0.0-1.0}``. Mapping:
  * ``supports=true``  → ``confidence`` (clamped to [0, 1])
  * ``supports=false`` → ``0.0``
  * unparseable / missing keys → ``0.0``  (the safe, abstaining direction --
    an ambiguous or malformed response is treated as no-support so a citation is
    not *promoted* on a bad parse; the caller can always fall back to the lexical
    scorer).
"""

from __future__ import annotations

import json
import os
from typing import Any

from .llm import DEFAULT_MODEL
from .verify import EntailmentScorer

__all__ = ["LLMEntailmentScorer"]

_SYSTEM = (
    "You are an NLI (Natural Language Inference) judge for EU AI Act legal text.\n"
    "Given a PREMISE (a provision from the EU AI Act) and a CLAIM (a question or "
    "statement about the Act), decide whether the PREMISE entails or directly "
    "answers the CLAIM.\n"
    "Reply with ONLY a JSON object on a single line, no prose, no markdown:\n"
    '{"supports": true, "confidence": 0.95}\n'
    "Rules:\n"
    "- \"supports\" is true if the premise directly entails or answers the claim, "
    "false otherwise.\n"
    "- \"confidence\" is a float in [0.0, 1.0] expressing your certainty.\n"
    "- Output ONLY the JSON object. Nothing else."
)

_USER_TEMPLATE = "PREMISE:\n{premise}\n\nCLAIM:\n{claim}"


def _parse_verdict(text: str) -> float:
    """Parse a model verdict string into a support score in [0, 1].

    Returns ``confidence`` when ``supports`` is true, ``0.0`` when false, and
    ``0.0`` for any unparseable/malformed response (safe, abstaining direction).
    """
    text = text.strip()
    # Tolerate a single code-fence wrapper even though we asked for none
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(l for l in lines if not l.startswith("```")).strip()
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return 0.0
    if not isinstance(obj, dict):
        return 0.0
    supports = obj.get("supports")
    if not isinstance(supports, bool):
        return 0.0
    if not supports:
        return 0.0
    confidence = obj.get("confidence", 1.0)
    try:
        score = float(confidence)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))


class LLMEntailmentScorer(EntailmentScorer):
    """Anthropic LLM used as an NLI judge, implementing the ``EntailmentScorer``
    ABC (the API route around local torch / sentence-transformers).

    ``score(claim, premise)`` returns P(support) in [0, 1] by asking the model
    whether the EU AI Act provision (``premise``) entails/answers the ``claim``
    and parsing the structured JSON verdict. Unparseable responses yield 0.0
    (the abstaining direction -- never fabricates a score). ``score_batch`` loops
    one API call per premise; batching is left to a future optimisation.

    Inject ``client`` to unit-test all prompt/parse logic offline with no
    ``anthropic`` package, key, or network required.
    """

    name: str = "llm-nli"

    def __init__(
        self,
        model: str | None = None,
        client: Any | None = None,
        max_tokens: int = 64,
    ) -> None:
        if client is None:
            client = self._make_client()
        self.client = client
        self.model = model or DEFAULT_MODEL
        self.max_tokens = max_tokens
        self.name = f"llm-nli:{self.model}"

    @staticmethod
    def _make_client() -> Any:
        """Construct a real Anthropic client, or raise a clean error.

        Never silently degrades: if the dep or key is absent the scorer raises
        rather than fabricating a verdict.
        """
        try:
            import anthropic
        except ModuleNotFoundError as e:
            raise RuntimeError(
                "LLMEntailmentScorer needs the `anthropic` package -- "
                "install it with `uv sync --extra baselines` (or inject a client)."
            ) from e
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "LLMEntailmentScorer needs ANTHROPIC_API_KEY in the environment "
                "(or inject a client)."
            )
        return anthropic.Anthropic()

    def score(self, claim: str, premise: str) -> float:
        return self.score_batch(claim, [premise])[0]

    def score_batch(self, claim: str, premises: list[str]) -> list[float]:
        """One claim vs many premises. One API call per premise (simple, correct).

        Each call instructs the model to emit a strict JSON verdict; the score is
        parsed from that verdict. An unparseable response returns 0.0 (safe
        abstaining direction -- a citation is never promoted on a bad parse).
        """
        if not premises:
            return []
        out: list[float] = []
        for premise in premises:
            user_msg = _USER_TEMPLATE.format(premise=premise, claim=claim)
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0,
                system=_SYSTEM,
                messages=[{"role": "user", "content": user_msg}],
            )
            text = "".join(
                b.text for b in resp.content if getattr(b, "type", None) == "text"
            )
            out.append(_parse_verdict(text))
        return out
