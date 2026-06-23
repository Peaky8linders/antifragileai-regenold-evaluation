"""Validate the fresh R116 MedTech / life-sciences V2 eval set.

Pure-data checks (no wire call): every expected_ref resolves in
ARTICLE_EXISTENCE, ids are unique, keywords non-empty, multi-turn rows are
well-formed, and the set is genuinely DISTINCT from both the R109
``MEDTECH_SCENARIOS`` and the GraphRAG-benchmark ``med_01..07`` rows.
"""
from __future__ import annotations

import re

from app.data.article_existence import ARTICLE_EXISTENCE
from evals.regenold.scenarios_medtech_lifesci import MEDTECH_SCENARIOS
from evals.regenold.scenarios_medtech_lifesci_v2 import MEDTECH_SCENARIOS_V2
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
    assert len(MEDTECH_SCENARIOS_V2) >= 24


def test_unique_ids():
    ids = [s["id"] for s in MEDTECH_SCENARIOS_V2]
    assert len(ids) == len(set(ids))


def test_every_expected_ref_resolves():
    for s in MEDTECH_SCENARIOS_V2:
        assert s["expected_refs"], f"{s['id']} has no expected_refs"
        for ref in s["expected_refs"]:
            assert _resolves(ref), (
                f"{s['id']} expected_ref {ref!r} does not resolve in ARTICLE_EXISTENCE"
            )


def test_keywords_and_category_present():
    for s in MEDTECH_SCENARIOS_V2:
        assert s["expected_keywords"], f"{s['id']} has no keywords"
        assert s["category"], f"{s['id']} has no category"
        assert s["question"].strip()


def test_distinct_from_prior_sets():
    """No V2 question may duplicate an R109 medtech row or a GraphRAG
    med_* ground-truth row (graded on memorised phrasing would be biased)."""
    prior = {g["question"].strip().lower() for g in GROUND_TRUTH}
    prior |= {s["question"].strip().lower() for s in MEDTECH_SCENARIOS}
    for s in MEDTECH_SCENARIOS_V2:
        assert s["question"].strip().lower() not in prior, (
            f"{s['id']} duplicates a prior medtech/benchmark question"
        )


def test_unique_ids_vs_prior():
    prior_ids = {s["id"] for s in MEDTECH_SCENARIOS}
    v2_ids = {s["id"] for s in MEDTECH_SCENARIOS_V2}
    assert not (prior_ids & v2_ids), "V2 ids collide with the R109 set"


def test_multiturn_messages_well_formed():
    multiturn = [s for s in MEDTECH_SCENARIOS_V2 if "messages" in s]
    assert len(multiturn) >= 2, "expected >= 2 multi-turn V2 scenarios"
    for s in multiturn:
        msgs = s["messages"]
        assert len(msgs) >= 3, f"{s['id']}: multi-turn needs >= 3 messages"
        for i, m in enumerate(msgs):
            expected_role = "user" if i % 2 == 0 else "assistant"
            assert m["role"] == expected_role, (
                f"{s['id']} message {i}: role {m['role']!r}, expected {expected_role!r}"
            )
            assert m["content"].strip(), f"{s['id']} message {i} is empty"
        assert msgs[-1]["role"] == "user", f"{s['id']} must end on a user turn"
        assert msgs[-1]["content"].strip() == s["question"].strip(), (
            f"{s['id']}: final user turn must equal the 'question' field"
        )


def test_risk_pyramid_and_value_chain_coverage():
    """The V2 set must span the pyramid + value chain Regenold serves."""
    cats = {s["category"] for s in MEDTECH_SCENARIOS_V2}
    required = {
        "clinical_scribe_transparency",      # R116 transcription vocab tie-in
        "importer_obligations",
        "authorised_representative",
        "distributor_obligations",
        "gpai_standard",
        "gpai_systemic",
        "prohibited_social_scoring",
        "borderline_emotion_recognition",
        "research_carveout",
        "penalties",
    }
    missing = required - cats
    assert not missing, f"missing V2 coverage categories: {sorted(missing)}"
