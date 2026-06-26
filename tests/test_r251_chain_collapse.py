"""R251 — HRAIS chain-collapse regression tests.

The live Stage-2 over-citation pattern: on a focused high-risk obligation
question (gold = the operative articles 6/16/9/43 + the triggering Annex),
Opus describes + cites the entire Chapter-III Section-2 design-requirement
chain (Arts 9-15) plus process detail (17-20). ``_collapse_hrais_chain``
drops ONLY the design/process DETAIL padding when the dense-chain DUMP
signature fires (>= 5 of Arts 9-15), keeping the operative / hub / gold
articles. Stage-2-gated -> davidath byte-identical.

Measured on the real fresh prod sidecar (medtech-graphrag-v124, post-R250
reconcile): Ref Strict 0.515 -> 0.533 (+0.018), Ref Conciseness 0.308 ->
0.333 (+0.025), Ref Loose (recall) 0.785 -> 0.785 (FLAT — no gold dropped,
the R142.1 trap avoided).
"""
from __future__ import annotations

from app.routes.regenold import _collapse_hrais_chain

# The grb_08 wire ref list (gold = [16, 9, 43]) — the canonical chain dump.
_CHAIN = [
    "Article 16",
    "Article 9",
    "Article 17",
    "Article 11",
    "Article 13",
    "Article 10",
    "Article 12",
    "Article 14",
    "Article 15",
    "Article 72",
    "Annex IV",
]
_Q = "What must the provider of a high-risk AI medical diagnostic system put in place?"
_ANS = (
    "Before placing it on the market the provider must implement a documented "
    "risk-management system (Article 9), data governance and a conformity "
    "assessment under Article 43."
)


def _fire(refs=None, *, answer=_ANS, question=_Q, stage2=True, scenario=False):
    return _collapse_hrais_chain(
        refs if refs is not None else list(_CHAIN),
        answer_text=answer,
        question=question,
        stage2_landed=stage2,
        scenario_shape=scenario,
    )


# ── davidath safety: every no-op gate ────────────────────────────────────


def test_stage2_off_is_noop():
    """The deterministic davidath bench never runs Stage-2 -> byte-identical."""
    assert _fire(stage2=False) == _CHAIN


def test_scenario_shape_is_noop():
    """Scenario shapes carry curated multi-article gold -> never collapse."""
    assert _fire(scenario=True) == _CHAIN


def test_explicit_enumeration_question_is_noop():
    """'which articles set out the requirements' — gold IS the chain there."""
    assert (
        _fire(question="Which articles set out the high-risk requirements?")
        == _CHAIN
    )
    assert _fire(question="List all the requirement articles for high-risk AI.") == _CHAIN


def test_sub_threshold_chain_is_noop():
    """Fewer than 5 design articles -> not a dump -> untouched."""
    short = ["Article 6", "Article 9", "Article 13", "Annex III"]
    assert _fire(short) == short


def test_empty_or_none_is_noop():
    assert _fire([]) == []
    # multi-turn flatten marker: only the live turn is scanned for enum markers
    flat = "Conversation so far:\n...\n\nLatest question:\n" + _Q
    assert len(_fire(question=flat)) < len(_CHAIN)


# ── the win: drops detail, protects operative / hubs / gold ───────────────


def test_collapse_fires_and_keeps_operative():
    out = _fire()
    assert out != _CHAIN and len(out) < len(_CHAIN)
    # operative / role / hub / classification / penalty refs survive
    for keep in ("Article 16", "Article 9", "Article 13", "Article 72", "Annex IV"):
        assert keep in out, f"dropped operative ref {keep}"
    # design / process detail padding is dropped
    for drop in ("Article 10", "Article 11", "Article 12", "Article 14", "Article 15", "Article 17"):
        assert drop not in out, f"kept detail ref {drop}"


def test_floor_never_below_three():
    out = _fire()
    assert len(out) >= 3


def test_lead_named_detail_is_protected():
    """A detail article the answer LEADS with is foregrounded -> keep it."""
    lead_ans = "Article 10 data governance is the operative duty for this dataset question."
    out = _fire(answer=lead_ans)
    assert "Article 10" in out


def test_question_named_detail_is_protected():
    out = _fire(question="What does Article 14 require for the provider's high-risk system?")
    assert "Article 14" in out


def test_idempotent():
    once = _fire()
    twice = _collapse_hrais_chain(
        once, answer_text=_ANS, question=_Q, stage2_landed=True, scenario_shape=False
    )
    assert once == twice


def test_grb20_recall_preserved():
    """grb_20: gold [6,9,43,Annex III] present in pred stays present."""
    grb20 = [
        "Article 16", "Article 11", "Article 13", "Article 17", "Article 18",
        "Article 9", "Article 10", "Article 12", "Article 14", "Article 15",
        "Article 43", "Article 22", "Article 19", "Article 20", "Article 50",
    ]
    out = _collapse_hrais_chain(
        grb20, answer_text=_ANS, question="What must the provider put in place before market?",
        stage2_landed=True, scenario_shape=False,
    )
    assert "Article 9" in out and "Article 43" in out  # the present gold
    assert len(out) < len(grb20)
