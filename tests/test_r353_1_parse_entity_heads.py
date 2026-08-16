"""R353.1 — the analysis-side head normaliser (review finding #3).

``article_head`` only accepts the WIRE long-form (``Article 13``), because
the scoring paths feed it already-canonicalised refs (R327: change the
formula, change its NAME). But the engine's parse emits short-form
``Art. N``, so R352-style analyses comparing parse entities to gold saw
every article as a false gap. ``parse_entity_head(s)`` canonicalises BOTH
forms; these tests pin that semantics.
"""

from __future__ import annotations

import pytest

from evals.bench.metrics import article_head, parse_entity_head, parse_entity_heads


def test_short_form_article_normalised():
    assert parse_entity_head("Art. 5") == "Article 5"
    assert parse_entity_head("Art 5") == "Article 5"
    assert parse_entity_head("art. 5") == "Article 5"


def test_long_form_article_unchanged():
    assert parse_entity_head("Article 5") == "Article 5"
    assert parse_entity_head("Article 13.1.a") == "Article 13"


def test_annex_forms():
    assert parse_entity_head("Annex III") == "Annex III"
    assert parse_entity_head("Annex III.1") == "Annex III"
    assert parse_entity_head("Annex iii") == "Annex III"


def test_non_entity_inputs_return_none():
    assert parse_entity_head("") is None
    assert parse_entity_head(None) is None
    assert parse_entity_head("AI Act") is None
    assert parse_entity_head("Recital 27") is None
    assert parse_entity_head(12345) is None


def test_parse_entity_heads_joins_mixed_forms():
    """The exact R352-analysis shape: engine entities + gold refs together."""
    entities = ["Art. 6", "Art. 13", "Annex III"]
    gold = ["Article 6", "Article 50.4", "Annex III.1"]
    heads = parse_entity_heads(entities + gold)
    assert heads == {"Article 6", "Article 13", "Article 50", "Annex III"}


def test_short_form_still_invisible_to_wire_scorer():
    """The R327 discipline: article_head must NOT silently widen."""
    assert article_head("Art. 5") is None
    assert article_head("Article 5") == "Article 5"
