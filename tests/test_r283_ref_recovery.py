"""R283 — reference-recovery bundle (PROTECT / ADD, never DROP).

Four gold-recovery levers, all env-gated behind the master
``REGENOLD_REF_RECOVERY`` (default ON) with per-fix sub-flags:

* Fix #1 — R72 reconcile named-head protection.
* Fix #2 — R72 reconcile tier-asserted-gateway protection.
* Fix #3 — lead-ref promotion to the R281 clamp head.
* Fix #4 — engine keyword-map additions (verified 0 davidath hits).

The bundle can only PROTECT a ref from a drop or REORDER toward the clamp
head, so recall can only rise (the R142.1 guard is satisfied by
construction). Fixes #1/#2/#3 are stage2-gated → davidath byte-identical;
Fix #4 is 0-davidath-hit → byte-identical.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import app.engines._graph_rag_data as gdata
import app.engines.graph_rag as graph_rag
import app.routes.regenold as regenold


# ── Fix #4 — keyword additions ────────────────────────────────────────────
def test_fix4_additions_present_and_well_formed():
    adds = dict(gdata._R283_KEYWORD_ADDITIONS)
    assert adds["incident-reporting"] == "Art. 73"
    assert adds["fines directly on a gpai"] == "Art. 101"
    assert adds["impose fines directly on a gpai"] == "Art. 101"
    assert adds["prohibited-ai deadline"] == "Art. 113"
    assert adds["obligations actually start applying"] == "Art. 113"
    # every phrase lowercased, multi-word / hyphenated (never a bare word)
    for kw, ref in gdata._R283_KEYWORD_ADDITIONS:
        assert kw == kw.lower(), kw
        assert (" " in kw) or ("-" in kw), f"too-generic single word: {kw!r}"
        assert ref.startswith(("Art. ", "Annex ")), ref


def test_fix4_additions_resolve_in_catalog():
    """Every addition's target article/annex must exist — a typo'd ref would
    silently fail retrieval (the R125 'confidently-wrong taxonomy' hazard)."""
    from app.data.article_existence import ARTICLE_EXISTENCE

    for kw, ref in gdata._R283_KEYWORD_ADDITIONS:
        assert ref in ARTICLE_EXISTENCE, f"{kw!r} -> {ref!r} not in ARTICLE_EXISTENCE"


def test_fix4_zero_davidath_hits():
    """The byte-identity guarantee for the one non-stage2-gated fix: every
    addition must appear in 0 davidath questions (else it would change the
    deterministic bench)."""
    data_dir = Path(__file__).resolve().parents[1] / "evals" / "bench" / "data"
    qa_path = data_dir / "qa_pairs.json"
    sc_path = data_dir / "scenarios.json"
    if not qa_path.exists() or not sc_path.exists():
        pytest.skip("davidath dataset not cached")

    def all_strings(obj):
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, dict):
            for v in obj.values():
                yield from all_strings(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from all_strings(v)

    qa = json.loads(qa_path.read_text(encoding="utf-8")).get("data") or []
    sc = json.loads(sc_path.read_text(encoding="utf-8")).get("data") or []
    corpus = " || ".join(s.lower() for s in all_strings(qa)) + " || " + " || ".join(
        s.lower() for s in all_strings(sc)
    )
    for kw, _ref in gdata._R283_KEYWORD_ADDITIONS:
        assert corpus.count(kw) == 0, f"R283 keyword {kw!r} HITS davidath — not byte-identical"


@pytest.mark.parametrize(
    "question,gold",
    [
        (
            "Is the EU AI Office allowed to impose fines directly on a GPAI "
            "provider, or only national authorities?",
            "Art. 101",
        ),
        (
            "We already report incidents under NIS2. Do AI Act "
            "incident-reporting obligations still apply?",
            "Art. 73",
        ),
        ("Did the Digital Omnibus push back the prohibited-AI deadline?", "Art. 113"),
        (
            "When do Annex III high-risk obligations actually start applying?",
            "Art. 113",
        ),
    ],
)
def test_fix4_surfaces_gold_on(monkeypatch, question, gold):
    monkeypatch.setenv("REGENOLD_REF_RECOVERY", "1")
    monkeypatch.delenv("REGENOLD_REF_RECOVERY_KW", raising=False)
    ents = list(graph_rag._deterministic_parse(question).entities)
    assert gold in ents, f"{gold} not surfaced for {question!r}: {ents}"


@pytest.mark.parametrize(
    "question,gold",
    [
        (
            "Is the EU AI Office allowed to impose fines directly on a GPAI "
            "provider, or only national authorities?",
            "Art. 101",
        ),
        ("Did the Digital Omnibus push back the prohibited-AI deadline?", "Art. 113"),
    ],
)
def test_fix4_gone_off(monkeypatch, question, gold):
    monkeypatch.setenv("REGENOLD_REF_RECOVERY", "0")
    monkeypatch.delenv("REGENOLD_REF_RECOVERY_KW", raising=False)
    ents = list(graph_rag._deterministic_parse(question).entities)
    assert gold not in ents


def test_fix4_kw_subflag_overrides_master(monkeypatch):
    q = "Did the Digital Omnibus push back the prohibited-AI deadline?"
    # master OFF but KW sub explicitly ON → addition active
    monkeypatch.setenv("REGENOLD_REF_RECOVERY", "0")
    monkeypatch.setenv("REGENOLD_REF_RECOVERY_KW", "1")
    assert "Art. 113" in list(graph_rag._deterministic_parse(q).entities)
    # master ON but KW sub explicitly OFF → addition inactive
    monkeypatch.setenv("REGENOLD_REF_RECOVERY", "1")
    monkeypatch.setenv("REGENOLD_REF_RECOVERY_KW", "0")
    assert "Art. 113" not in list(graph_rag._deterministic_parse(q).entities)


# ── Fix #1 — named-head protection ────────────────────────────────────────
def test_fix1_named_head_refs():
    q = "What do Articles 16, 17 and 18 require of a provider of a high-risk AI system?"
    got = regenold._question_named_head_refs(q, ["Article 16", "Article 17", "Article 18"])
    assert got == {"Article 16", "Article 17", "Article 18"}


def test_fix1_excludes_unnamed_and_matches_subpoint_head():
    q = "Which requirements do Articles 9, 10 and 11 set?"
    # a sub-point ref counts via its base head; an unnamed article is excluded
    got = regenold._question_named_head_refs(q, ["Article 9.1", "Article 43", "Annex IV"])
    assert got == {"Article 9.1"}


def test_fix1_empty_when_no_named_articles():
    assert regenold._question_named_head_refs("Is my chatbot high-risk?", ["Article 6"]) == set()


# ── Fix #2 — tier-asserted gateway protection ─────────────────────────────
def test_fix2_positive_verdict_protects_gateway():
    refs = ["Article 5", "Article 6", "Article 50"]
    assert regenold._tier_asserted_gateway_refs(
        "This system is classified as high-risk under Annex III.", refs
    ) == {"Article 6"}
    assert "Article 5" in regenold._tier_asserted_gateway_refs(
        "The practice is prohibited under Article 5.", refs
    )


def test_fix2_negation_vetoes():
    refs = ["Article 5", "Article 6"]
    assert regenold._tier_asserted_gateway_refs(
        "This system is not high-risk; it is minimal-risk.", refs
    ) == set()


def test_fix2_incidental_mention_not_protected():
    # a duty-describing "high-risk AI systems must…" is NOT a verdict
    refs = ["Article 6"]
    assert regenold._tier_asserted_gateway_refs(
        "Providers of high-risk AI systems must keep logs.", refs
    ) == set()


def test_fix2_gateway_absent_from_refs_no_op():
    assert regenold._tier_asserted_gateway_refs("It is high-risk.", ["Article 13"]) == set()


def test_fix2_is_opt_in_default_off(monkeypatch):
    """r283-smoke demoted Fix #2 to OPT-IN — it protects a NON-gold gateway
    on prohibited-practice questions (precision leak). It must NOT inherit the
    master, so the default bundle (#1/#3/#4) never fires it."""
    monkeypatch.delenv("REGENOLD_REF_RECOVERY_TIER", raising=False)
    monkeypatch.setenv("REGENOLD_REF_RECOVERY", "1")  # master ON
    assert regenold._ref_recovery_tier_enabled() is False  # still OFF by default
    monkeypatch.setenv("REGENOLD_REF_RECOVERY_TIER", "1")  # explicit opt-in
    assert regenold._ref_recovery_tier_enabled() is True


def test_default_bundle_protects_named_not_tier(monkeypatch):
    """With the DEFAULT bundle (master ON, tier unset), a tier-asserted but
    NON-question-named gateway is NOT protected (the leak is gone), while a
    question-named ref IS protected."""
    monkeypatch.setenv("REGENOLD_REF_RECOVERY", "1")
    monkeypatch.delenv("REGENOLD_REF_RECOVERY_TIER", raising=False)
    monkeypatch.delenv("REGENOLD_REF_RECOVERY_NAMED", raising=False)
    q = "We run a social-scoring system. What risk level?"  # names no article
    prot = regenold._reconcile_protected_set(
        q, "This is prohibited, and would otherwise be high-risk.",
        ["Article 5", "Article 6"], stage2_landed=True,
    )
    assert "Article 6" not in prot  # tier off → the smoke leak cannot recur
    # a question-named article IS protected via Fix #1
    q2 = "What do Articles 16 and 17 require?"
    prot2 = regenold._reconcile_protected_set(
        q2, "Article 16 sets duties.", ["Article 16", "Article 17"], stage2_landed=True,
    )
    assert {"Article 16", "Article 17"} <= prot2


# ── Fix #3 — lead-ref promotion ───────────────────────────────────────────
def test_fix3_promotes_lead_named_article():
    out = regenold._promote_lead_ref(
        ["Article 72", "Article 26", "Article 73"],
        "Article 73 requires reporting the serious incident. Article 72 monitoring continues.",
    )
    assert out[0] == "Article 73"
    assert set(out) == {"Article 72", "Article 26", "Article 73"}  # set unchanged


def test_fix3_no_article_in_lead_is_noop():
    refs = ["Article 9", "Article 10"]
    assert regenold._promote_lead_ref(refs, "The system needs a risk-management process.") == refs


def test_fix3_only_first_sentence_counts():
    # Article 43 named only in the SECOND sentence → not promoted
    out = regenold._promote_lead_ref(
        ["Article 9", "Article 43"],
        "The provider set up risk management. Then Article 43 conformity assessment applies.",
    )
    assert out == ["Article 9", "Article 43"]


def test_fix3_empty_inputs_fail_soft():
    assert regenold._promote_lead_ref([], "Article 5 …") == []
    assert regenold._promote_lead_ref(["Article 5"], "") == ["Article 5"]


# ── Gating — stage2 + sub-flag inheritance ────────────────────────────────
def test_protected_set_is_stage2_gated(monkeypatch):
    monkeypatch.setenv("REGENOLD_REF_RECOVERY", "1")
    q = "What do Articles 16, 17 and 18 require?"
    refs = ["Article 16", "Article 17", "Article 18"]
    off = regenold._reconcile_protected_set(q, "Article 16 sets duties.", refs, stage2_landed=False)
    on = regenold._reconcile_protected_set(q, "Article 16 sets duties.", refs, stage2_landed=True)
    # stage2=False → only the R137 definitional base (no named additions here)
    assert "Article 17" not in off
    # stage2=True → named heads protected
    assert {"Article 16", "Article 17", "Article 18"} <= on


def test_subflag_inherits_master(monkeypatch):
    monkeypatch.delenv("REGENOLD_REF_RECOVERY_NAMED", raising=False)
    monkeypatch.setenv("REGENOLD_REF_RECOVERY", "1")
    assert regenold._ref_recovery_named_enabled() is True
    monkeypatch.setenv("REGENOLD_REF_RECOVERY", "0")
    assert regenold._ref_recovery_named_enabled() is False
    # explicit sub-flag overrides the master
    monkeypatch.setenv("REGENOLD_REF_RECOVERY_NAMED", "1")
    assert regenold._ref_recovery_named_enabled() is True


def test_named_protection_gated_off_by_subflag(monkeypatch):
    monkeypatch.setenv("REGENOLD_REF_RECOVERY", "1")
    monkeypatch.setenv("REGENOLD_REF_RECOVERY_NAMED", "0")
    monkeypatch.setenv("REGENOLD_REF_RECOVERY_TIER", "0")
    q = "What do Articles 16, 17 and 18 require?"
    refs = ["Article 16", "Article 17", "Article 18"]
    on = regenold._reconcile_protected_set(q, "Article 16 sets duties.", refs, stage2_landed=True)
    assert "Article 17" not in on  # named + tier both off → base only


# ── Cache-key discipline (R263.2) ─────────────────────────────────────────
def test_cache_key_includes_ref_recovery_flags(monkeypatch):
    monkeypatch.delenv("REGENOLD_REF_RECOVERY", raising=False)
    monkeypatch.delenv("REGENOLD_REF_RECOVERY_KW", raising=False)
    base = regenold._engine_cache_key("q", None)
    monkeypatch.setenv("REGENOLD_REF_RECOVERY", "0")
    assert regenold._engine_cache_key("q", None) != base
    monkeypatch.setenv("REGENOLD_REF_RECOVERY", "1")
    monkeypatch.setenv("REGENOLD_REF_RECOVERY_KW", "0")
    assert regenold._engine_cache_key("q", None) != base
