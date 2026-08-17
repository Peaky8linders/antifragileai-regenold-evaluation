"""R369 — wire-level leaf+head collapse (_collapse_leaf_to_head) and
leaf-only head promotion (_promote_leaf_to_head).

MEASURED BASIS — the legal_v2 judge reads the RAW reference list, NOT a
head-projection:

* REDUNDANT-CITATION (collapse): a sub-point is flagged WRONG when its bare
  head is also on the wire — xr_12 shipped ``Article 5, Article 50.3,
  Article 5.1.f, Annex III.1.c, Article 50``; the deterministic head set
  {5, 50, III} matched gold exactly, yet the judge flagged ``Article 5.1.f``
  as WRONG solely because ``Article 5`` was present.
* MISSING-HEAD (promotion): gold ``Annex III`` was counted MISSING while the
  wire carried only ``Annex III.1.c`` — the judge does NOT head-project for
  gold matching and wants the bare head present.

Live qwen 7-axis measurement on the 60-row R369 golden pool (same answers,
same judge, only refs differ):

    baseline          21/60 ref_corr pass (0.3500), cite_faith 0.9322
    collapse only     21/60 (0.3500) — clears redundant flags, misses recall
    promotion only    24/60 (0.4000) — fixes recall, leaves redundancy
    collapse+promote  26/60 (0.4333) — both halves; 0 pass->fail flips

Deterministic metrics are untouched by construction (``article_heads``
projects leaves to heads, so the head set is identical); the effect exists
only for a consumer that scores at sub-point grain — the judge.

EXEMPTION — the R274 load-bearing pair ``Article 6`` + ``Article 6.3`` (the
general high-risk rule beside its own derogation) must survive together;
R274 pins it in ``test_article_6_and_6_3_cited`` and R325's measurement found
it the only 1-in-273 correct loss.
"""

from __future__ import annotations

import pytest

from app.routes.regenold import (
    _collapse_leaf_to_head,
    _promote_leaf_to_head,
    _ref_collapse_leaf_to_head_enabled,
    _ref_promote_leaf_to_head_enabled,
)


# ── unit: collapse semantics ──────────────────────────────────────────────
@pytest.mark.parametrize(
    ("refs", "expected"),
    [
        # the measured golden-read case (xr_12): leaf+head pairs collapse to
        # the head; a lone leaf whose head is absent stays.
        (
            ["Article 5", "Article 50.3", "Article 5.1.f", "Annex III.1.c",
             "Article 50"],
            ["Article 5", "Annex III.1.c", "Article 50"],
        ),
        (["Article 50.3", "Article 50"], ["Article 50"]),
        (["Article 5", "Article 5.1.f"], ["Article 5"]),
        (["Annex III", "Annex III.1.c"], ["Annex III"]),
        # multiple leaves of the same head all collapse to the single head.
        (["Article 50.1", "Article 50.3", "Article 50"], ["Article 50"]),
        # order of the KEPT refs is preserved.
        (["Article 50", "Article 99", "Article 50.3"], ["Article 50", "Article 99"]),
        # lone leaves (no head present) are untouched — dropping them would
        # lose the coordinate entirely.
        (["Article 3.1"], ["Article 3.1"]),
        (["Article 50.3"], ["Article 50.3"]),
        # degenerate inputs.
        (["Article 5"], ["Article 5"]),
        ([], []),
        (["not a citation"], ["not a citation"]),
    ],
)
def test_collapse_leaf_to_head(refs: list[str], expected: list[str]) -> None:
    assert _collapse_leaf_to_head(list(refs)) == expected


# ── unit: promotion semantics ────────────────────────────────────────────
@pytest.mark.parametrize(
    ("refs", "expected"),
    [
        # the measured golden-read case (xr_12): the head is added right
        # after the first leaf that implies it.
        (
            ["Article 5", "Annex III.1.c", "Article 50"],
            ["Article 5", "Annex III.1.c", "Annex III", "Article 50"],
        ),
        (["Article 5.1.f", "Article 50.3"],
         ["Article 5.1.f", "Article 5", "Article 50.3", "Article 50"]),
        # head already present -> no addition.
        (["Article 5.1.f", "Article 5"], ["Article 5.1.f", "Article 5"]),
        # R274 leaf alone -> the head is added (that is the point of the
        # pass: the judge counts bare Article 6 as missing otherwise).
        (["Article 6.3"], ["Article 6.3", "Article 6"]),
        # recitals are not article/annex refs — untouched.
        (["Recital 53"], ["Recital 53"]),
        # degenerate inputs.
        (["Article 5"], ["Article 5"]),
        ([], []),
        (["not a citation"], ["not a citation"]),
    ],
)
def test_promote_leaf_to_head(refs: list[str], expected: list[str]) -> None:
    assert _promote_leaf_to_head(list(refs)) == expected


def test_head_set_unchanged_by_promotion() -> None:
    """Promotion only ADDS heads implied by existing leaves — the head set
    is mathematically unchanged, so deterministic metrics and the gold veto
    cannot move."""
    from evals.bench.metrics import article_heads

    before = ["Article 5.1.g", "Article 6.2", "Annex III.1.b"]
    after = _promote_leaf_to_head(list(before))
    assert article_heads(before) == article_heads(after)


# ── combined: collapse then promote ──────────────────────────────────────
def test_combined_collapse_then_promote() -> None:
    """The measured winning configuration: collapse first (drop leaves whose
    head is present), then promote (add heads for remaining leaf-only refs).
    On xr_12 this converts the wire to exactly the gold heads plus the
    leaf-level Annex coordinate."""
    refs = ["Article 5", "Article 50.3", "Article 5.1.f", "Annex III.1.c",
            "Article 50"]
    collapsed = _collapse_leaf_to_head(refs)
    combined = _promote_leaf_to_head(collapsed)
    assert combined == ["Article 5", "Annex III.1.c", "Annex III", "Article 50"]
    assert "Article 5.1.f" not in combined  # redundant flag cleared
    assert "Annex III" in combined  # missing head recovered


# ── exemption: R274 load-bearing pair ────────────────────────────────────
def test_r274_article_6_and_6_3_pair_survives() -> None:
    """Article 6 (general rule) + Article 6.3 (its derogation) are BOTH
    load-bearing — R274 pins the pair, R325 measured it the single correct
    loss in 273. The collapse must never remove 6.3 when 6 is present."""
    assert _collapse_leaf_to_head(["Article 6", "Article 6.3"]) == [
        "Article 6", "Article 6.3",
    ]


def test_other_article_6_leaves_still_collapse() -> None:
    """Only the 6.3 derogation is exempt — a different 6.x leaf alongside
    Article 6 is a genuine duplicate and must collapse."""
    assert _collapse_leaf_to_head(["Article 6", "Article 6.1"]) == ["Article 6"]


def test_article_6_3_without_head_stays() -> None:
    """6.3 with no bare Article 6 on the wire is a lone leaf — untouched."""
    assert _collapse_leaf_to_head(["Article 6.3"]) == ["Article 6.3"]


# ── deterministic head-set invariance ────────────────────────────────────
def test_head_set_unchanged_by_collapse() -> None:
    """Collapse must never change the HEAD set — the deterministic metrics
    (reference_correctness_loose/strict, gold_dropped_head) all project
    through article_heads, so a collapse that changed the head set would
    break hard rules #7/#8. This is the mathematical safety guarantee."""
    from evals.bench.metrics import article_heads

    before = ["Article 5", "Article 50.3", "Article 5.1.f", "Annex III.1.c",
              "Article 50"]
    after = _collapse_leaf_to_head(list(before))
    assert article_heads(before) == article_heads(after)


# ── gate ─────────────────────────────────────────────────────────────────
def test_gate_default_on() -> None:
    """R369 doctrine: shipped ON after the golden-read measurement; ``0``
    restores the pre-R369 wire."""
    assert _ref_collapse_leaf_to_head_enabled() is True


def test_gate_respects_env_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REGENOLD_REF_COLLAPSE_LEAF_TO_HEAD", "0")
    assert _ref_collapse_leaf_to_head_enabled() is False


def test_promote_gate_default_on() -> None:
    """Promotion ships ON with the collapse — the combined configuration is
    the measured winner (ref_corr 21 -> 26 of 60 on the golden pool)."""
    assert _ref_promote_leaf_to_head_enabled() is True


def test_promote_gate_respects_env_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REGENOLD_REF_PROMOTE_LEAF_TO_HEAD", "0")
    assert _ref_promote_leaf_to_head_enabled() is False


# ── route-level: the pass runs last, after the R368 wire guard ───────────
def test_route_runs_collapse_last(monkeypatch: pytest.MonkeyPatch) -> None:
    """The collapse must run AFTER the R368 wire guard so guard-appended
    heads are seen. Probe the wire order via the R368 medical row: the guard
    appends Annex III (head) and the collapse must then leave the head set
    stable while removing any leaf duplicates."""
    import os

    from pydantic import SecretStr
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.main import app

    monkeypatch.delenv("REGENOLD_R368_WIRE_GUARD", raising=False)
    monkeypatch.delenv("REGENOLD_REF_COLLAPSE_LEAF_TO_HEAD", raising=False)
    settings.regenold.api_key = SecretStr("r369-collapse-test-key")
    c = TestClient(app)
    r = c.post(
        "/api/v1/regenold/eu-ai-act/ask",
        headers={"X-Regenold-Api-Key": "r369-collapse-test-key"},
        json=[{"role": "user", "content":
               "Is AI software that detects melanoma from dermoscopy images a "
               "high-risk AI system under the EU AI Act?"}],
    )
    assert r.status_code == 200, r.json()
    refs = r.json().get("references", [])
    # The wire must not carry a leaf whose head is also present.
    from app.integrations.regenold.refs import parse

    heads = {
        (spec.article_number, spec.annex_roman)
        for ref in refs
        for spec in [parse(ref)]
        if not spec.subpoints
    }
    for ref in refs:
        spec = parse(ref)
        if spec.subpoints:
            key = (spec.article_number, spec.annex_roman)
            if key in heads and not (
                key == (6, None) and spec.subpoints == ("3",)
            ):
                raise AssertionError(
                    f"leaf {ref!r} survived with its head on the wire: {refs}"
                )
