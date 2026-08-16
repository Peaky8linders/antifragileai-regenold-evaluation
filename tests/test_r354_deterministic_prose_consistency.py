"""R354 — deterministic-path prose consistency (Fix A).

The R138 final citation-consistency pass (every article/annex the SHIPPED
answer names must appear in the wire references) is Stage-2-gated, so the
deterministic path (Stage-2 throttled/failed/skipped) shipped raw retrieval
candidates even when the answer prose named a gold ref the wire lacked —
the la_q73 defect: branch answer names "Annex I" twice, wire ships
[Article 43, Article 6, Article 27, Article 49] with no Annex I (and
Article 43, which the prose never names, riding along).

Fix A extends the R138 add-pass to the deterministic path behind
``REGENOLD_DETERMINISTIC_PROSE_CONSISTENCY`` (default OFF — answer-affecting,
so it ships behind an off-switch until the live A/B measures the veto).
Measured over the 81-row live-answers checkpoint: 11 rows, 11 gold heads
restorable (la_q73 fully closed).

The add is strictly existence-gated + cross-instrument-guarded + capped:
it cannot invent a reference, and a deterministic answer is still a real
answer whose prose must be consistent with its citations.
"""
from __future__ import annotations

from app.routes.regenold import (
    _add_prose_named_refs,
    _deterministic_prose_consistency_enabled,
)

# The la_q73 branch arm, verbatim from the R350.2 live-answers checkpoint.
_LA_Q73_PROSE = (
    "Under Article 27, in addition to Article 26 baseline duties, deployers of "
    "certain Annex III high-risk AI systems must perform a Fundamental Rights "
    "Impact Assessment (FRIA) covering affected persons and specific "
    "fundamental rights risks. Annex I route (Article 6(1)): the system is a "
    "safety component of, or is itself, a product covered by the Union "
    "harmonisation legislation listed in Annex I AND that product must undergo "
    "a third-party conformity assessment under that sectoral legislation. "
    "Article 49 requires providers (and deployers that are public authorities) "
    "to register themselves and their high-risk AI system in the EU database "
    "(Article 71) before placing the system on the market or putting it into "
    "service."
)
# The wire refs the branch actually shipped — Annex I lost, Article 43
# (never named in the prose) present.
_LA_Q73_WIRE = ["Article 43", "Article 6", "Article 27", "Article 49"]
# What the engine retrieval actually surfaced (Annex I IS retrieved).
_LA_Q73_CITABLE = frozenset({
    "Article 6", "Annex I", "Annex III", "Article 43",
    "Article 27", "Article 49", "Article 71",
})


def test_flag_default_on(monkeypatch):
    """The flag defaults ON after the live deterministic-path A/B
    (r354-fix-a-det: gold_dropped_head base 72 → branch 60, delta −12,
    zero regressions, FIRED 30 rows). The off-switch still exists for
    rollback."""
    monkeypatch.delenv("REGENOLD_DETERMINISTIC_PROSE_CONSISTENCY", raising=False)
    assert _deterministic_prose_consistency_enabled() is True


def test_flag_explicitly_off_restores_old_behavior(monkeypatch):
    """The off-switch must still disable the deterministic arm."""
    monkeypatch.setenv("REGENOLD_DETERMINISTIC_PROSE_CONSISTENCY", "0")
    assert _deterministic_prose_consistency_enabled() is False


def test_flag_on_restores_prose_named_gold_ref(monkeypatch):
    """la_q73's exact shape: prose names Annex I twice, the wire lacks it.
    With the flag ON (and the R138 pass applied with the retrieval-derived
    citable universe), Annex I is restored to the wire."""
    monkeypatch.setenv("REGENOLD_DETERMINISTIC_PROSE_CONSISTENCY", "1")
    assert _deterministic_prose_consistency_enabled() is True
    out = _add_prose_named_refs(
        _LA_Q73_WIRE, _LA_Q73_PROSE,
        citable_bases=_LA_Q73_CITABLE, cap=8,
    )
    assert "Annex I" in out
    # The gold ref (Annex I) is restored WITHOUT dropping the existing wire.
    for ref in _LA_Q73_WIRE:
        assert ref in out


def test_flag_on_restores_from_prose_only_citable_universe(monkeypatch):
    """The restoration must respect the citable-base guard: a ref the prose
    names but the retrieval never surfaced is NOT promoted (the R327
    grounding stance — promotion only ever adds retrieval-grounded refs)."""
    monkeypatch.setenv("REGENOLD_DETERMINISTIC_PROSE_CONSISTENCY", "1")
    # Article 71 IS named in the prose but NOT in this restricted universe.
    citable = frozenset({"Article 6", "Annex I", "Annex III",
                         "Article 43", "Article 27", "Article 49"})
    out = _add_prose_named_refs(
        _LA_Q73_WIRE, _LA_Q73_PROSE, citable_bases=citable, cap=8,
    )
    assert "Article 71" not in out
    assert "Annex I" in out


def test_no_citable_universe_uses_references_and_prose(monkeypatch):
    """With the citable-base guard OFF (citable_bases=None), the allowed
    source is references ∪ prose citations — the refs + everything the prose
    names — so Annex I still restores and Article 71 now qualifies too."""
    monkeypatch.setenv("REGENOLD_DETERMINISTIC_PROSE_CONSISTENCY", "1")
    out = _add_prose_named_refs(_LA_Q73_WIRE, _LA_Q73_PROSE, citable_bases=None, cap=8)
    assert "Annex I" in out
    assert "Annex III" in out


def test_flag_off_leaves_wire_untouched(monkeypatch):
    """Flag OFF: the route gate is inert, so a deterministic row ships its
    raw candidates byte-identically — the pre-R354 behaviour is one env
    flip away (the off-switch). The helper itself returns False; the route
    gate short-circuits on it."""
    monkeypatch.setenv("REGENOLD_DETERMINISTIC_PROSE_CONSISTENCY", "0")
    assert _deterministic_prose_consistency_enabled() is False


def test_does_not_invent_non_existent_refs(monkeypatch):
    """The add is existence-gated: a prose mention of a non-existent
    coordinate (e.g. Article 999) must never be promoted."""
    monkeypatch.setenv("REGENOLD_DETERMINISTIC_PROSE_CONSISTENCY", "1")
    prose = _LA_Q73_PROSE + " Article 999 applies here."
    out = _add_prose_named_refs(_LA_Q73_WIRE, prose, citable_bases=None, cap=8)
    assert "Article 999" not in out


def test_foreign_instrument_refs_never_promoted(monkeypatch):
    """Cross-instrument mentions (GDPR / a Directive) are context-guarded
    and must never be added as AI-Act refs — the R325 guard applies on the
    deterministic arm exactly as on the Stage-2 arm."""
    monkeypatch.setenv("REGENOLD_DETERMINISTIC_PROSE_CONSISTENCY", "1")
    prose = _LA_Q73_PROSE + " The GDPR's Article 5 governs processing."
    out = _add_prose_named_refs(_LA_Q73_WIRE, prose, citable_bases=None, cap=8)
    assert "Article 5" not in out
