"""Validate the fresh R109 MedTech / life-sciences eval set.

Pure-data checks (no wire call): every expected_ref resolves in
ARTICLE_EXISTENCE, ids are unique, keywords non-empty, and the set is
genuinely distinct from the existing med_01..07 GraphRAG-benchmark rows.
"""
from __future__ import annotations

import re

from app.data.article_existence import ARTICLE_EXISTENCE
from evals.regenold.scenarios_medtech_lifesci import MEDTECH_SCENARIOS
from evals.regenold.scenarios_graphrag_benchmark import GROUND_TRUTH

_ART_RE = re.compile(r"^Article\s+(\d+)$")
_ANNEX_RE = re.compile(r"^Annex\s+([IVXLC]+)$")


def _resolves(ref: str) -> bool:
    m = _ART_RE.match(ref)
    if m:
        return f"Art. {m.group(1)}" in ARTICLE_EXISTENCE
    m = _ANNEX_RE.match(ref)
    if m:
        return f"Annex {m.group(1)}" in ARTICLE_EXISTENCE
    return False


def test_nonempty_set():
    assert len(MEDTECH_SCENARIOS) >= 15


def test_unique_ids():
    ids = [s["id"] for s in MEDTECH_SCENARIOS]
    assert len(ids) == len(set(ids))


def test_every_expected_ref_resolves():
    for s in MEDTECH_SCENARIOS:
        assert s["expected_refs"], f"{s['id']} has no expected_refs"
        for ref in s["expected_refs"]:
            assert _resolves(ref), f"{s['id']} expected_ref {ref!r} does not resolve"


def test_keywords_and_category_present():
    for s in MEDTECH_SCENARIOS:
        assert s["expected_keywords"], f"{s['id']} has no keywords"
        assert s["category"], f"{s['id']} has no category"
        assert s["question"].strip()


def test_distinct_from_graphrag_medtech_rows():
    existing = {g["question"].strip().lower() for g in GROUND_TRUTH}
    for s in MEDTECH_SCENARIOS:
        assert s["question"].strip().lower() not in existing, (
            f"{s['id']} duplicates an existing GraphRAG-benchmark question"
        )


# ── Regenold consultant augmentation (rgn_*) ─────────────────────────────


def _rgn_rows() -> list[dict]:
    return [s for s in MEDTECH_SCENARIOS if s["id"].startswith("rgn_")]


def test_rgn_augmentation_present():
    rows = _rgn_rows()
    assert len(rows) >= 18, f"expected >= 18 rgn_ rows, got {len(rows)}"
    # No collision with the original mt_ ids.
    mt_ids = {s["id"] for s in MEDTECH_SCENARIOS if not s["id"].startswith("rgn_")}
    assert not mt_ids & {r["id"] for r in rows}


def test_rgn_every_expected_ref_resolves():
    """Mirror of test_every_expected_ref_resolves, pinned to the new ids."""
    for s in _rgn_rows():
        assert s["expected_refs"], f"{s['id']} has no expected_refs"
        for ref in s["expected_refs"]:
            assert _resolves(ref), (
                f"{s['id']} expected_ref {ref!r} does not resolve in "
                "ARTICLE_EXISTENCE"
            )


def test_rgn_multiturn_messages_well_formed():
    """Multi-turn rows carry a valid alternating history ending on the
    user turn that equals ``question`` (the runner posts ``messages``
    verbatim as the wire history)."""
    multiturn = [s for s in _rgn_rows() if "messages" in s]
    assert len(multiturn) >= 3, "expected >= 3 multi-turn rgn_ scenarios"
    for s in multiturn:
        msgs = s["messages"]
        assert len(msgs) >= 3, f"{s['id']}: multi-turn needs >= 3 messages"
        for i, m in enumerate(msgs):
            expected_role = "user" if i % 2 == 0 else "assistant"
            assert m["role"] == expected_role, (
                f"{s['id']} message {i}: role {m['role']!r}, "
                f"expected {expected_role!r}"
            )
            assert m["content"].strip(), f"{s['id']} message {i} is empty"
        assert msgs[-1]["role"] == "user", f"{s['id']} must end on a user turn"
        assert msgs[-1]["content"].strip() == s["question"].strip(), (
            f"{s['id']}: final user turn must equal the 'question' field"
        )


def test_rgn_required_coverage_categories():
    """The augmentation must cover the Regenold life-sciences portfolio
    surface: MDR interplay, IVDR, wellness boundary, clinical research,
    combination products, hospital deployment, post-market, legacy/QMS,
    registration, penalties, and multi-turn consultations."""
    cats = {s["category"] for s in _rgn_rows()}
    required = {
        "aiact_mdr_interplay",
        "ivd_diagnostics",
        "wellness_boundary",
        "research_carveout",
        "clinical_research",
        "combination_product",
        "hospital_deployment",
        "postmarket_vigilance",
        "legacy_transition",
        "qms_integration",
        "registration",
        "penalties_authorities",
    }
    missing = required - cats
    assert not missing, f"missing rgn_ coverage categories: {sorted(missing)}"
    multiturn_cats = {
        s["category"] for s in _rgn_rows() if "messages" in s
    }
    assert len(multiturn_cats) >= 3
