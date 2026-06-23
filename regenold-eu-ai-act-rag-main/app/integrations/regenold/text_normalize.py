"""Unicode punctuation normalisation for inbound question text.

## Why this module exists (R67)

The davidath competition benchmark — and, by extension, real partner
traffic copy-pasted from PDFs / Word — ships question text with
**Unicode punctuation** instead of ASCII:

* ``U+2011`` NON-BREAKING HYPHEN — 90 occurrences across the 476-item
  davidath set (``deep‑fake``, ``market‑surveillance``, ``post‑market``,
  ``conformity‑assessment``).
* ``U+2018`` / ``U+2019`` smart single quotes — 23 occurrences.
* ``U+202F`` NARROW NO-BREAK SPACE — 17 occurrences.

Every scope-gate anchor (:data:`app.integrations.regenold.scope._AI_ACT_ANCHORS`)
and every engine keyword-anchor map (``_KEYWORD_ENTITY_MAP`` in
:mod:`app.engines.graph_rag`, ``KEYWORD_TO_ARTICLE`` in
:mod:`app.integrations.regenold.scope`) does **ASCII-literal substring
matching**. A question worded ``"What labeling requirement exists for
deep‑fake content?"`` (U+2011) fails to match the ``deep-fake`` anchor
(U+002D), so the scope gate finds *no* anchor and wrongly refuses the
whole question as out-of-scope ("conversational"). R67 traced six
davidath QA rows (qa_030 / 042 / 064 / 068 / 080 — U+2011; qa_033 — a
separate missing-anchor bug) to exactly this failure.

:mod:`app.engines.scenario_classifier` already carried a private
``_NORMALISE_MAP`` for the same reason — but the scope gate and the
deterministic engine parse never got the same treatment. That
duplication-with-a-gap *is* the bug. This module is the single source
of truth; ``scenario_classifier`` now imports from here.

The normaliser runs ONCE at the route boundary
(:func:`app.routes.regenold.regenold_eu_ai_act_ask`) so every
downstream consumer — scope gate, deterministic parse, BM25 retrieval,
intent classifier — sees ASCII punctuation.

## Safety

Every mapping is semantics-preserving for keyword matching:

* The four dash code points (U+2010-2014) + U+2212 minus all collapse
  to ``-``. A non-breaking hyphen *is* a hyphen; an en-dash inside a
  compound or a range renders identically once matched against ASCII
  anchors. Date ranges like ``2024–2026`` become ``2024-2026`` — still
  a valid range, and the engine's date regexes use ASCII ``-`` anyway.
* The no-break / narrow / thin spaces collapse to a regular space.
* Smart quotes collapse to their ASCII equivalents.

No code point is *dropped*; the string length is preserved 1:1, so
downstream length caps (the 4 000-char message cap, the 2 000-char
engine question cap) are unaffected.
"""
from __future__ import annotations

# Single source of truth for Unicode → ASCII punctuation folding.
# Keep this in sync with NOTHING — every consumer imports from here.
_PUNCT_MAP = str.maketrans(
    {
        "‐": "-",  # HYPHEN
        "‑": "-",  # NON-BREAKING HYPHEN  ← the davidath culprit
        "‒": "-",  # FIGURE DASH
        "–": "-",  # EN DASH
        "—": "-",  # EM DASH
        "−": "-",  # MINUS SIGN
        " ": " ",  # NO-BREAK SPACE
        " ": " ",  # THIN SPACE
        " ": " ",  # NARROW NO-BREAK SPACE
        "‘": "'",  # LEFT SINGLE QUOTATION MARK
        "’": "'",  # RIGHT SINGLE QUOTATION MARK
        "‚": "'",  # SINGLE LOW-9 QUOTATION MARK
        "“": '"',  # LEFT DOUBLE QUOTATION MARK
        "”": '"',  # RIGHT DOUBLE QUOTATION MARK
        "„": '"',  # DOUBLE LOW-9 QUOTATION MARK
    }
)


def normalize_unicode_punctuation(text: str) -> str:
    """Fold Unicode dashes / spaces / quotes to their ASCII equivalents.

    Length-preserving and idempotent. Returns the input unchanged for
    empty / falsy input. Safe to call on any string — it only touches
    the 15 code points in :data:`_PUNCT_MAP`.
    """
    if not text:
        return text
    return text.translate(_PUNCT_MAP)


__all__ = ["normalize_unicode_punctuation"]
