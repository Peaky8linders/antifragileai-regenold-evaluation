"""R329 P2 — ``REGENOLD_SEMANTIC_COORDINATES``: the legal coordinate in the
constrained semantic block.

THE DEFECT. ``graph_semantic._FOCUS_CYPHER`` walks
``(a)-[:HAS_PARAGRAPH|HAS_POINT|HAS_SUBPOINT*1..3]->(node)`` — a path that binds
every node needed to name the coordinate — and then collects only
``{uid, layer, text, score}``, so ``kg_context._render_semantic_layers`` renders

    - Article 12 [paragraph article_12_1]: <text>

The block built to attribute a duty to the right SUB-provision showed
sub-provision text under a HEAD-level cite and never emitted ``Article 12.1``.

THE CRITICAL GUARD IN THIS FILE is the OFF test. The flag ships default OFF and
the R327.1-gated rendering must come back byte-identical, character for
character, when it is off — otherwise the A/B is measuring two changes at once.

SCOPE. The label changes; citability does not. The block's non-citable framing
is asserted unchanged (hard rule #10 — the graph is additive context, never a
wire citation).

Deterministic env; no graph, no LLM. Every row here is a stub.
"""
from __future__ import annotations

import pytest

from app.engines import graph_semantic, kg_context
from app.engines.graph_semantic import (
    _FOCUS_CYPHER,
    _FOCUS_COORD_CYPHER,
    coordinate_for_row,
    semantic_coordinates_enabled,
)
from app.engines.kg_context import _render_semantic_layers


# ── Stub rows in the shape the coordinate query returns ─────────────────────

def _row(cite, layer, uid, text, *, para=None, letter=None, roman=None, score=0.8):
    return {
        "cite": cite,
        "layer": layer,
        "uid": uid,
        "text": text,
        "score": score,
        "para": para,
        "letter": letter,
        "roman": roman,
    }


#: One row per grain, plus an annex — the four shapes P2 has to name.
ROWS = [
    _row("Article 12", "Paragraph", "article_12_1", "High-risk AI systems shall technically allow for the automatic recording of events.", para="1", score=0.891),
    _row("Article 5", "Point", "article_5_1_f", "The placing on the market of AI systems to infer emotions.", para="1", letter="f", score=0.84),
    _row("Article 5", "SubPoint", "article_5_1_h_iii", "The targeted search for a specific suspect.", para="1", letter="h", roman="iii", score=0.79),
    _row("Annex III", "Paragraph", "annex_III_2", "Critical infrastructure.", para="2", score=0.71),
]


@pytest.fixture(autouse=True)
def _deterministic_env(monkeypatch):
    """Master switch ON, gloss OFF — the R327.1 shipped configuration."""
    monkeypatch.setenv("REGENOLD_GRAPH_SEMANTIC_LAYERS", "1")
    monkeypatch.setenv("REGENOLD_SEMANTIC_GLOSS", "0")
    monkeypatch.setenv("REGENOLD_KG_CONTEXT", "1")
    monkeypatch.delenv("REGENOLD_SEMANTIC_COORDINATES", raising=False)
    monkeypatch.delenv("REGENOLD_KG_UNIT_CHARS", raising=False)


@pytest.fixture
def stub_focus(monkeypatch):
    """Feed ``_render_semantic_layers`` fixed rows; silence the gloss fetch."""

    def _install(rows):
        monkeypatch.setattr(
            graph_semantic, "fetch_focused_subprovisions", lambda q, r: list(rows)
        )
        monkeypatch.setattr(
            graph_semantic, "fetch_definition_and_recital_context", lambda q, r: []
        )

    return _install


def _focus_block(parts):
    assert len(parts) == 1, f"expected exactly the focused block, got {len(parts)}"
    return parts[0]


def _focus_lines(parts):
    return [ln for ln in _focus_block(parts).splitlines() if ln.startswith("- ")]


# ── The flag ────────────────────────────────────────────────────────────────

def test_flag_defaults_on():
    """Default ON as of 2026-08-13 (operator decision).

    Railway's ``[deploy.envs]`` has never applied, so a default-OFF flag never
    reaches the deployment — a code default is the only delivery mechanism.
    The flag survives as an off-switch and so ``easyhard_ab`` can still A/B it.
    """
    assert semantic_coordinates_enabled() is True


@pytest.mark.parametrize(
    "value", ["1", "true", "TRUE", "yes", "on", " on ", "", "maybe"]
)
def test_flag_truthy_spellings(monkeypatch, value):
    """Negative-form flag: anything that is not an explicit off-value is ON.

    ``""`` and ``"maybe"`` are ON here, matching the other default-ON engine
    flags (``REGENOLD_KG_CONTEXT``, ``REGENOLD_SUBPARAGRAPH_ATTRIBUTION``).
    """
    monkeypatch.setenv("REGENOLD_SEMANTIC_COORDINATES", value)
    assert semantic_coordinates_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "off", "no", "OFF", " 0 "])
def test_flag_falsy_spellings(monkeypatch, value):
    monkeypatch.setenv("REGENOLD_SEMANTIC_COORDINATES", value)
    assert semantic_coordinates_enabled() is False


def test_flag_is_read_fresh_per_call(monkeypatch):
    """R263.2 — a module-level constant makes the in-process A/B inert."""
    monkeypatch.setenv("REGENOLD_SEMANTIC_COORDINATES", "0")
    assert semantic_coordinates_enabled() is False
    monkeypatch.setenv("REGENOLD_SEMANTIC_COORDINATES", "1")
    assert semantic_coordinates_enabled() is True
    monkeypatch.setenv("REGENOLD_SEMANTIC_COORDINATES", "0")
    assert semantic_coordinates_enabled() is False


# ── OFF — the critical regression guard ─────────────────────────────────────

def test_off_rendering_is_byte_identical(monkeypatch, stub_focus):
    """Flag OFF ⇒ the pre-R329 label, character for character.

    The rows carry ``para``/``letter``/``roman`` precisely so that a renderer
    which quietly used them regardless of the flag would fail here.

    The flag is set explicitly now that the DEFAULT is ON — this is the
    rollback path, and it must still reproduce the pre-R329 wire exactly.
    """
    monkeypatch.setenv("REGENOLD_SEMANTIC_COORDINATES", "0")
    stub_focus(ROWS)
    parts = _render_semantic_layers("who must keep logs?", ["Article 12"])
    assert _focus_lines(parts) == [
        "- Article 12 [paragraph article_12_1]: High-risk AI systems shall technically allow for the automatic recording of events.",
        "- Article 5 [point article_5_1_f]: The placing on the market of AI systems to infer emotions.",
        "- Article 5 [subpoint article_5_1_h_iii]: The targeted search for a specific suspect.",
        "- Annex III [paragraph annex_III_2]: Critical infrastructure.",
    ]


def test_off_uses_the_untouched_cypher(monkeypatch):
    """OFF must issue the exact query R327.1 gated, not the P2 variant."""
    seen: list[str] = []
    monkeypatch.setenv("REGENOLD_SEMANTIC_COORDINATES", "0")
    monkeypatch.setattr(kg_context, "kg_context_enabled", lambda: True)
    monkeypatch.setattr(kg_context, "_node_ids", lambda refs, limit: ["article_12"])
    monkeypatch.setattr(
        kg_context, "_bounded_execute_read", lambda cy, params: seen.append(cy) or []
    )
    monkeypatch.setattr(graph_semantic, "_embed", lambda q: [0.0] * 128)

    graph_semantic.fetch_focused_subprovisions("q", ["Article 12"])
    assert seen == [_FOCUS_CYPHER]

    monkeypatch.setenv("REGENOLD_SEMANTIC_COORDINATES", "1")
    seen.clear()
    graph_semantic.fetch_focused_subprovisions("q", ["Article 12"])
    assert seen == [_FOCUS_COORD_CYPHER]


# ── ON — the coordinate at every grain ──────────────────────────────────────

def test_on_renders_the_legal_coordinate(monkeypatch, stub_focus):
    monkeypatch.setenv("REGENOLD_SEMANTIC_COORDINATES", "1")
    stub_focus(ROWS)
    parts = _render_semantic_layers("who must keep logs?", ["Article 12"])
    assert _focus_lines(parts) == [
        "- Article 12.1: High-risk AI systems shall technically allow for the automatic recording of events.",
        "- Article 5.1.f: The placing on the market of AI systems to infer emotions.",
        "- Article 5.1.h.iii: The targeted search for a specific suspect.",
        "- Annex III.2: Critical infrastructure.",
    ]


@pytest.mark.parametrize(
    "row, expected",
    [
        (_row("Article 12", "Paragraph", "article_12_1", "t", para="1"), "Article 12.1"),
        (_row("Article 5", "Point", "article_5_1_f", "t", para="1", letter="f"), "Article 5.1.f"),
        (_row("Article 5", "SubPoint", "article_5_1_h_iii", "t", para="1", letter="h", roman="iii"), "Article 5.1.h.iii"),
        (_row("Annex III", "Paragraph", "annex_III_2", "t", para="2"), "Annex III.2"),
        (_row("Annex III", "Point", "annex_III_1_a", "t", para="1", letter="a"), "Annex III.1.a"),
        # Art. 3 is a definition catalogue: its Paragraph nodes ARE the definitions.
        (_row("Article 3", "Paragraph", "article_3_4", "t", para="4"), "Article 3.4"),
        # A partially-seeded node falls through ``coalesce`` to the node id.
        (_row("article_12", "Paragraph", "article_12_1", "t", para="1"), "Article 12.1"),
        (_row("annex_III", "Paragraph", "annex_III_2", "t", para="2"), "Annex III.2"),
        # Layer label casing comes straight from ``head(labels(node))``.
        (_row("Article 12", "PARAGRAPH", "article_12_1", "t", para="1"), "Article 12.1"),
    ],
)
def test_coordinate_for_row_all_grains(row, expected):
    assert coordinate_for_row(row) == expected


def test_coordinates_never_use_the_legacy_forms(monkeypatch, stub_focus):
    """Hard rule #1 — no ``Art. 12``, no ``Article 12(1)``, no ``Annex 3``."""
    monkeypatch.setenv("REGENOLD_SEMANTIC_COORDINATES", "1")
    stub_focus(ROWS)
    block = _focus_block(_render_semantic_layers("q", ["Article 12"]))
    for line in [ln for ln in block.splitlines() if ln.startswith("- ")]:
        label = line[2:].split(":", 1)[0]
        assert "(" not in label and ")" not in label
        assert not label.startswith("Art. ")
        assert not label.startswith("Annex ") or not label[len("Annex "):][0].isdigit()


# ── Fallback — never a partial or guessed coordinate ────────────────────────

@pytest.mark.parametrize(
    "row, why",
    [
        (_row("Article 12", "Paragraph", "u", "t", para=None), "no paragraph number"),
        (_row("Article 12", "Paragraph", "u", "t", para=""), "blank paragraph number"),
        (_row("Article 12", "Paragraph", "u", "t", para="one"), "non-numeric paragraph"),
        (_row("Article 12", "Point", "u", "t", para="1"), "Point with no letter"),
        (_row("Article 5", "SubPoint", "u", "t", para="1", letter="h"), "SubPoint with no roman"),
        (_row("Article 5", "SubPoint", "u", "t", para="1", roman="iii"), "SubPoint with no letter"),
        (_row("Article 12", "Recital", "u", "t", para="1"), "layer that has no coordinate"),
        (_row("Article 12", None, "u", "t", para="1"), "no layer at all"),
        (_row("Recital 5", "Paragraph", "u", "t", para="1"), "head is not a provision"),
        (_row("", "Paragraph", "u", "t", para="1"), "no head"),
        (_row(None, "Paragraph", "u", "t", para="1"), "null head"),
        (_row("Article 999", "Paragraph", "u", "t", para="1"), "head outside the catalog"),
        (_row("Annex 3", "Paragraph", "u", "t", para="1"), "Arabic annex is not wire-legal"),
        (_row("Article 12", "Paragraph", "u", "t", para="999"), "paragraph out of range"),
    ],
)
def test_incomplete_numbering_falls_back(row, why):
    assert coordinate_for_row(row) is None, why


@pytest.mark.parametrize("cite, para", [("Article 16", "1"), ("Article 66", "1"), ("Annex XIII", "1")])
def test_synthetic_paragraph_falls_back(cite, para):
    """The 3 measured synthetic Paragraph nodes must never reach the prompt.

    ``provision_hierarchy`` synthesises a Paragraph ``"1"`` for a single-block
    provision carrying a lettered list, so the graph holds
    ``article_16 -> article_16_1 -> article_16_1_a`` although Article 16's list
    is ``16(a)…(n)`` with no paragraph 1. Reconstructing straight off the path
    would print ``Article 16.1.a`` — a coordinate that does not exist.
    """
    assert coordinate_for_row(_row(cite, "Paragraph", "u", "t", para=para)) is None
    assert coordinate_for_row(_row(cite, "Point", "u", "t", para=para, letter="a")) is None


def test_render_falls_back_per_row_not_per_block(monkeypatch, stub_focus):
    """A row that cannot be named keeps the OLD label; its neighbours do not."""
    monkeypatch.setenv("REGENOLD_SEMANTIC_COORDINATES", "1")
    stub_focus(
        [
            _row("Article 12", "Paragraph", "article_12_1", "Logging.", para="1"),
            _row("Article 16", "Point", "article_16_1_a", "Compliance.", para="1", letter="a"),
            _row("Article 5", "Point", "article_5_1_f", "Emotion inference.", para="1", letter="f"),
        ]
    )
    assert _focus_lines(_render_semantic_layers("q", ["Article 12"])) == [
        "- Article 12.1: Logging.",
        "- Article 16 [point article_16_1_a]: Compliance.",
        "- Article 5.1.f: Emotion inference.",
    ]


def test_row_without_the_new_fields_falls_back(monkeypatch, stub_focus):
    """Belt and braces: flag ON but rows from the OLD query shape."""
    monkeypatch.setenv("REGENOLD_SEMANTIC_COORDINATES", "1")
    stub_focus(
        [
            {
                "cite": "Article 12",
                "layer": "Paragraph",
                "uid": "article_12_1",
                "text": "Logging.",
                "score": 0.9,
            }
        ]
    )
    assert _focus_lines(_render_semantic_layers("q", ["Article 12"])) == [
        "- Article 12 [paragraph article_12_1]: Logging."
    ]


# ── Scope limit — the block stays NON-CITABLE (hard rule #10) ───────────────

def test_framing_text_is_unchanged_by_the_flag(monkeypatch, stub_focus):
    stub_focus(ROWS)
    off = _focus_block(_render_semantic_layers("q", ["Article 12"]))
    monkeypatch.setenv("REGENOLD_SEMANTIC_COORDINATES", "1")
    on = _focus_block(_render_semantic_layers("q", ["Article 12"]))

    header_off = off.split("\n- ", 1)[0]
    header_on = on.split("\n- ", 1)[0]
    assert header_on == header_off
    assert "do NOT cite anything new here" in header_on
    assert "They add NO new provision" in header_on


# ── The Cypher ──────────────────────────────────────────────────────────────

#: The R327.1-gated query, pinned verbatim. P2 must add a SECOND query, never
#: edit this one — the default-OFF arm has to keep running exactly what was
#: measured. (``tests/test_ontology_leap_hardening.py`` pins the seeder's MERGE
#: strings the same way.)
_FOCUS_CYPHER_AS_GATED = """
CALL () {
    CALL db.index.vector.queryNodes('v_paragraph_embedding', $fanout, $emb)
    YIELD node, score RETURN node, score
    UNION
    CALL db.index.vector.queryNodes('v_point_embedding', $fanout, $emb)
    YIELD node, score RETURN node, score
    UNION
    CALL db.index.vector.queryNodes('v_subpoint_embedding', $fanout, $emb)
    YIELD node, score RETURN node, score
}
WITH node, score WHERE score >= $min_sim
MATCH (a)-[:HAS_PARAGRAPH|HAS_POINT|HAS_SUBPOINT*1..3]->(node)
WHERE a.id IN $ids AND (a:Article OR a:Annex)
"""


def test_focus_cypher_is_untouched():
    """The default-OFF query must not have acquired the P2 machinery."""
    assert _FOCUS_CYPHER.startswith(_FOCUS_CYPHER_AS_GATED)
    assert "MATCH path" not in _FOCUS_CYPHER
    assert "nodes(path)" not in _FOCUS_CYPHER
    assert "AS para" not in _FOCUS_CYPHER
    assert "AS letter" not in _FOCUS_CYPHER
    assert "AS roman" not in _FOCUS_CYPHER
    assert "toIntegerOrNull" not in _FOCUS_CYPHER
    assert _FOCUS_CYPHER != _FOCUS_COORD_CYPHER


def test_coord_cypher_shape():
    cy = _FOCUS_COORD_CYPHER
    # Non-deprecated subquery form on Aura 5 — a bare ``CALL {`` warns 01N00.
    assert "CALL () {" in cy
    assert "CALL {" not in cy.replace("CALL () {", "")
    # The path must be BOUND, over the same three relationship types.
    assert "MATCH path = (a)-[:HAS_PARAGRAPH|HAS_POINT|HAS_SUBPOINT*1..3]->(node)" in cy
    assert "nodes(path) AS chain" in cy
    # The three numbering properties, read by label off the bound path.
    assert "n:Paragraph | n.number" in cy
    assert "n:Point | n.letter" in cy
    assert "n:SubPoint | n.roman" in cy
    # Article/Paragraph ``number`` is a STRING — any numeric ordering must cast.
    assert "toIntegerOrNull(para)" in cy
    # The constraint to already-cited provisions is intact (hard rule #10).
    assert "WHERE a.id IN $ids AND (a:Article OR a:Annex)" in cy
    # Same five columns as before, plus the numbering.
    for col in ("AS cite", "AS uid", "AS layer", "AS text", "AS score",
                "AS para", "AS letter", "AS roman"):
        assert col in cy
    assert cy.count("{") == cy.count("}")
    assert cy.count("(") == cy.count(")")
    assert cy.count("[") == cy.count("]")


def test_both_cyphers_take_the_same_parameters():
    """``fetch_focused_subprovisions`` binds ONE parameter dict for both."""
    import re

    params = lambda cy: set(re.findall(r"\$(\w+)", cy))
    assert params(_FOCUS_COORD_CYPHER) == params(_FOCUS_CYPHER)
