"""R337 — the `gold_dropped` veto must know the gold's GRAIN before it fires.

`gold_dropped` is a VETO (hard rule #8): a non-zero drop is a rejection, no
argument. That makes a false positive unusually expensive — it rejects correct
work, and it is designed to be read without scepticism.

`gold_dropped_exact` compares full coordinates. Against HEAD-level gold, a MORE
precise citation therefore scores as a dropped head:

    gold_dropped_exact(["Article 6.1"], gold=["Article 6"]) -> dropped 1
    gold_dropped_head (["Article 6.1"], gold=["Article 6"]) -> dropped 0

`dynamic_ab`'s probe set is 208 gold refs over 129 gold-carrying rows (132 rows
total) with **zero** carrying a sub-point, so on that pool the exact veto
measures "did we get more precise", sign inverted. Measured live on R333's
sub-point fix: exact said 10 -> 5 while head said +0 and every axis was exactly
0.0000 — i.e. the veto would have rejected a change that dropped nothing.

The danger of the fix is the mirror image: silencing a REAL veto. So both
directions are asserted here.

R337.1 — WHY THIS FILE WAS REWRITTEN
====================================

The first cut of the guard passed 5/5 while being completely dead, because this
file's `_rows()` helper injected a ``"row"`` key that ``_run_rows`` has never
produced. The guard read the gold from that key, so on the real path
``gold_refs`` was always empty, ``applicable`` always False, and — since
``_report``'s rejection test filters on ``applicable`` — an exact-grain gold
drop could NEVER print REJECTED. Half of hard rule #8's veto was dead on the
repo's designated merge gate, and the tests said it was fine.

    A test whose fixture constructs a data shape the production code never
    produces is worthless: it passes while the integration is broken.

So every row in this file is now built by the REAL producer,
``dynamic_ab._row_record`` — the single function ``_run_rows`` calls — and
:func:`test_run_rows_itself_emits_the_gold` drives ``_run_rows`` end to end with
only the HTTP poster stubbed, so the producer and the guard are asserted against
each other rather than against a hand-written dict.

Every citation used below resolves against the repo's pinned CELEX 32024R1689
text via ``get_provision_text`` (verified: Article 6.1/6.2/6.3, Annex IV.1/IV.2,
Annex IV.1.e all return real verbatim text; ``provision_exists`` is head-level
LAX and is deliberately not relied on).
"""
from __future__ import annotations

from evals.bench import metrics as M
from evals.harness import dynamic_ab as D
from evals.harness.probe_set import ProbeRow, load_probe_set

# Gold shapes. Leaf-grained ones are real coordinates with verbatim text in the
# pinned Regulation; head-level ones are the shape the live probe set actually
# carries.
GOLD_LEAF_ART = ("Article 6.1", "Article 6.2", "Article 6.3")
GOLD_LEAF_ANNEX = ("Annex IV.1", "Annex IV.2")
GOLD_HEAD = ("Article 6",)


def _probe_row(rid: str, gold: tuple[str, ...]) -> ProbeRow:
    """A real :class:`ProbeRow` — the same type `load_probe_set` yields."""
    return ProbeRow(
        id=rid, source="s", category="c", is_multiturn=False,
        messages=({"role": "user", "content": "q"},),
        expected_refs=gold, expected_keywords=(),
    )


def _arm(*pairs: tuple[str, tuple[str, ...], list[str]]) -> list[dict]:
    """One arm's rows, built by THE producer `_run_rows` uses.

    `pairs` is ``(row_id, gold, predicted_refs)``. Nothing here hand-writes a
    key: if `_row_record` stops carrying the gold, every grain assertion below
    fails, which is the property the previous version of this file lacked.
    """
    return [
        D._row_record(_probe_row(rid, gold), "a", refs,
                      latency_ms=1.0, http_status=200, error=None)
        for rid, gold, refs in pairs
    ]


# ── the underlying asymmetry this all rests on ───────────────────────────


def test_exact_grain_counts_a_more_precise_citation_as_a_drop():
    """The measured fact that motivates the whole guard."""
    assert M.gold_dropped_exact(["Article 6.1"], ["Article 6"])["dropped_count"] == 1
    assert M.gold_dropped_head(["Article 6.1"], ["Article 6"])["dropped_count"] == 0


# ── the producer actually carries the gold (the dead-veto regression) ────


def test_the_producer_carries_the_gold_into_the_row():
    """`_analyse` can only read a grain the producer wrote down."""
    row = D._row_record(_probe_row("r1", GOLD_LEAF_ART), "a", ["Article 6"])
    assert row["gold_refs"] == list(GOLD_LEAF_ART)


def test_run_rows_itself_emits_the_gold(monkeypatch):
    """Drive the REAL `_run_rows`, stubbing only the HTTP poster.

    This is the test the first cut needed and did not have. It asserts against
    what the production path emits — not against a fixture — so a guard reading
    a key nobody writes cannot pass again. No network and no engine: the poster
    is replaced, which is the only boundary being faked.
    """
    import evals.regenold.runner_v2 as rv2

    def _fake_post(url, api_key, history, timeout):
        return ({"answer": "an answer", "references": ["Article 6"]},
                12.5, 200, None, 1, [])

    monkeypatch.setattr(rv2, "_post_local", _fake_post)

    rows = D._run_rows(
        [_probe_row("r1", GOLD_LEAF_ART)], {},
        local=True, endpoint=None, api_key=None, timeout=1.0,
    )
    assert len(rows) == 1
    emitted = rows[0]
    # The gold must survive the trip, in the same shape `_analyse` reads.
    assert emitted["gold_refs"] == list(GOLD_LEAF_ART)
    # And the fixture helper must emit the IDENTICAL key set, so a test built on
    # `_row_record` is a test built on the production shape.
    assert set(emitted) == set(_arm(("r1", GOLD_LEAF_ART, ["Article 6"]))[0])


# ── applicability ────────────────────────────────────────────────────────


def test_exact_veto_is_marked_INAPPLICABLE_on_head_level_gold():
    base = _arm(("r1", GOLD_HEAD, ["Article 6"]))
    brch = _arm(("r1", GOLD_HEAD, ["Article 6.1"]))
    res = D._analyse(base, brch, null_band=0.01)
    ex = res["gold"]["gold_dropped_exact_leaf_rows"]
    assert ex["applicable"] is False
    assert ex["gold_refs_total"] == 1
    assert ex["gold_leaf_grained"] == 0
    assert ex["rows_counted"] == 0
    # head grain remains authoritative and shows NO drop for the precise cite
    assert res["gold"]["gold_dropped_head"]["applicable"] is True
    assert res["gold"]["gold_dropped_head"]["delta"] == 0


def test_exact_veto_STAYS_APPLICABLE_when_gold_carries_sub_points():
    """The guard must not silence the veto on gold that can actually support it —
    otherwise it converts a safety rail into a blindfold."""
    gold = ("Article 6.1", "Annex IV.1.e")
    base = _arm(("r1", gold, ["Article 6.1", "Annex IV.1.e"]))
    brch = _arm(("r1", gold, ["Article 6.1"]))
    res = D._analyse(base, brch, null_band=0.01)
    ex = res["gold"]["gold_dropped_exact_leaf_rows"]
    assert ex["applicable"] is True
    assert ex["gold_leaf_grained"] == 2
    assert ex["delta"] > 0, "a genuine leaf-grain gold drop must still veto"


def test_grain_is_decided_PER_ROW_not_globally():
    """R337.1 — one leaf-grained row must not re-arm the veto for head-level ones.

    Mixed pool: r1 genuinely loses 3 coordinates; r2's gold is head-level and
    the branch merely got MORE precise there (``Article 6`` -> ``Article 6.1``).
    The all-or-nothing switch charged r2 for that precision gain the moment r1
    made the veto applicable — measured +4 under the global switch versus +3
    per row — reinstating the exact false rejection the guard exists to prevent.
    """
    base = _arm(("r1", GOLD_LEAF_ART, list(GOLD_LEAF_ART)),
                ("r2", GOLD_HEAD, ["Article 6"]))
    brch = _arm(("r1", GOLD_LEAF_ART, ["Article 6"]),
                ("r2", GOLD_HEAD, ["Article 6.1"]))
    ex = D._analyse(base, brch, null_band=0.01)["gold"]["gold_dropped_exact_leaf_rows"]
    assert ex["applicable"] is True
    assert ex["rows_counted"] == 1 and ex["rows_scored"] == 2
    assert ex["delta"] == 3, "only r1's real drops may count"
    # The historical all-rows figure is kept as a DIAGNOSTIC and is the number
    # the global switch would have vetoed on. It must not equal the veto.
    assert ex["all_rows_delta"] == 4
    assert ex["population"] == "1 of 2 rows with leaf-grained gold"


# ── the grain test itself ────────────────────────────────────────────────


def test_grain_test_matches_the_citation_grammar_not_a_bare_dot():
    """`"." in ref` is wrong on forms this repo emits, in the unsafe direction.

    `Art. 5` is the INTERNAL-form head — no sub-point — but it contains a dot,
    so the shorthand would call it leaf-grained and switch the exact veto ON
    over gold that cannot support it. `_carries_sub_point` delegates to the
    repo's canonical parser instead (one concept, one definition).
    """
    for head in ("Article 5", "Annex IV", "Art. 5", "Annex IV", "Art. 5 "):
        assert D._carries_sub_point(head) is False, head
    for leaf in ("Article 5.1", "Article 5.1.f", "Annex IV.1.e",
                 "Art. 5(1)(a)", "Annex IV(1)"):
        assert D._carries_sub_point(leaf) is True, leaf
    # Non-citations must never count as grain.
    for junk in ("Recital 27.", "", "GDPR Art. 22", None, 5):
        assert D._carries_sub_point(junk) is False, junk


def test_live_probe_gold_is_head_level_so_the_exact_veto_is_n_a_today():
    """Measured against the real corpus, not a fixture.

    2026-08-15: 132 rows, 208 gold refs, **0** leaf-grained. That is precisely
    why the exact veto must report inapplicable rather than a number on this
    gate — and why the dead `applicable` flag went unnoticed: on this pool the
    correct output and the broken output look the same.
    """
    probe = load_probe_set()
    gold = [g for r in probe for g in (r.expected_refs or ())]
    assert gold, "probe set carries no gold at all — the guard would be untested"
    assert sum(map(D._carries_sub_point, gold)) == 0, (
        "the probe gold has gained sub-point grain — the exact veto now has a "
        "population; re-read the R337 note in dynamic_ab._analyse before "
        "changing this assertion"
    )


def test_a_precision_gain_on_the_REAL_probe_gold_is_not_a_veto():
    """End-to-end on real rows: appending a sub-point must not read as a drop."""
    rows = [r for r in load_probe_set() if r.expected_refs][:12]
    base = [D._row_record(r, "a", list(r.expected_refs)) for r in rows]
    brch = [D._row_record(r, "a", [f"{g}.1" for g in r.expected_refs])
            for r in rows]
    res = D._analyse(base, brch, null_band=0.01)
    assert res["gold"]["gold_dropped_exact_leaf_rows"]["applicable"] is False
    assert res["gold"]["gold_dropped_head"]["delta"] == 0
    assert "REJECTED" not in _render(res)


# ── the printed report ───────────────────────────────────────────────────


def _render(res) -> str:
    lines: list[str] = []
    res = {**res, "label": "t", "n_scored": res.get("n_scored", 1),
           "stop_reason": "resolved", "fire": {"any_changed": 1, "common": 1}}
    D._report(res, emit=lines.append)
    return "\n".join(lines)


def test_report_prints_a_reason_not_a_number_when_inapplicable():
    res = D._analyse(_arm(("r1", GOLD_HEAD, ["Article 6"])),
                     _arm(("r1", GOLD_HEAD, ["Article 6.1"])), null_band=0.01)
    out = _render(res)
    assert "leaf-grained gold" in out
    assert "head grain above is authoritative" in out
    assert "HARD RULE #8 VETO" not in out, "must not veto on an inapplicable grain"
    assert "REJECTED" not in out


def test_report_still_REJECTS_on_a_real_leaf_grain_drop():
    """THE dead-veto regression test.

    Rows built exactly as `_run_rows` builds them; branch drops 5 real gold
    coordinates. Before R337.1 this printed no REJECTED line at all, because
    `applicable` was hard-stuck False on the production row shape.
    """
    res = D._analyse(
        _arm(("r1", GOLD_LEAF_ART, list(GOLD_LEAF_ART)),
             ("r2", GOLD_LEAF_ANNEX, list(GOLD_LEAF_ANNEX))),
        _arm(("r1", GOLD_LEAF_ART, ["Article 6"]),
             ("r2", GOLD_LEAF_ANNEX, ["Annex IV"])),
        null_band=0.01)
    assert res["gold"]["gold_dropped_exact_leaf_rows"]["delta"] == 5
    out = _render(res)
    assert "HARD RULE #8 VETO" in out
    assert "REJECTED" in out


def test_report_names_the_population_it_summed_over():
    """A veto number is unreadable without the rows it was summed over."""
    out = _render(D._analyse(
        _arm(("r1", GOLD_LEAF_ART, list(GOLD_LEAF_ART)),
             ("r2", GOLD_HEAD, ["Article 6"])),
        _arm(("r1", GOLD_LEAF_ART, ["Article 6"]),
             ("r2", GOLD_HEAD, ["Article 6"])),
        null_band=0.01))
    assert "over 1 of 2 rows with leaf-grained gold" in out
    assert "over all 2 scored rows" in out
