"""R264 — regression pins for the Sonnet-5-judge-driven fixes.

All fixes are Stage-2/route/prompt/sub-point surfaces → davidath byte-identical
or neutral by construction (verified: QA 0-trigger on the new retrieval keys /
sub-point regexes; the win lands on the live ab_judge). These tests pin the
surfaces so a future edit is loud.
"""

from __future__ import annotations

import re

import pytest

from app.integrations.regenold.answer_normaliser import strip_meta_commentary


# ── C1: meta-commentary strip ────────────────────────────────────────────


class TestStripMetaCommentary:
    def test_drops_current_retrieval_sentence_keeps_substance(self):
        a = (
            "Deployers must use the high-risk AI system in accordance with the "
            "provider's instructions and assign competent human oversight under "
            "Article 26. The current retrieval surfaces Article 9 as generic "
            "high-risk context that is not directly responsive."
        )
        out = strip_meta_commentary(a)
        assert "current retrieval" not in out.lower()
        assert "Article 26" in out

    def test_drops_references_supplied_above(self):
        a = (
            "Article 7(2) sets the criteria the Commission weighs when amending "
            "Annex III to add or remove a high-risk use case. The references "
            "supplied above do not fully cover Article 97 delegation."
        )
        out = strip_meta_commentary(a)
        assert "references supplied above" not in out.lower()
        assert "Article 7(2)" in out

    def test_noop_on_clean_answer(self):
        a = "Article 26 requires deployers to assign human oversight and monitor operation."
        assert strip_meta_commentary(a) == a

    def test_never_empties_when_only_sentence_leaks(self):
        # remainder < 80 chars → fail-soft keeps the original
        a = "Article 9 applies. The current retrieval is thin."
        assert strip_meta_commentary(a) == a

    def test_idempotent(self):
        a = (
            "Deployers must follow provider instructions and ensure human "
            "oversight under Article 26 across the system lifecycle. Based on "
            "the retrieval, Article 9 is generic context."
        )
        once = strip_meta_commentary(a)
        assert strip_meta_commentary(once) == once

    def test_env_off(self, monkeypatch):
        monkeypatch.setenv("REGENOLD_STRIP_META", "0")
        a = (
            "Deployers must follow provider instructions and ensure human "
            "oversight under Article 26. The current retrieval is generic."
        )
        assert strip_meta_commentary(a) == a

    def test_fail_soft_on_non_string(self):
        assert strip_meta_commentary("") == ""
        assert strip_meta_commentary(None) is None  # type: ignore[arg-type]


# ── C1: meta-refusal markers route to grounded prose ─────────────────────


class TestRefusalMarkers:
    def test_r264_markers_present(self):
        from app.engines.graph_rag import _STAGE2_REFUSAL_MARKERS

        for m in (
            "not substantiated in the applicable references",
            "does not appear in the eu ai act references",
        ):
            assert m in _STAGE2_REFUSAL_MARKERS


# ── C4: sub-point emitter leaves ─────────────────────────────────────────


class TestSubpointLeaves:
    def test_emergency_dispatch_emits_annex_iii_5_d(self):
        from app.data import subpoint_emitter as se

        q = "Which AI systems for emergency dispatch and patient triage are explicitly listed as high-risk?"
        leaves = _leaves_for(se, q)
        assert "Annex III.5.d" in leaves

    def test_rbi_exception_emits_5_1_h_iii(self):
        q = (
            "What is the exception to the real-time remote biometric "
            "identification prohibition, the four-year custodial threshold?"
        )
        from app.data import subpoint_emitter as se

        leaves = _leaves_for(se, q)
        assert "Article 5.1.h.iii" in leaves

    def test_base_rbi_question_does_not_emit_iii_leaf(self):
        # A plain "is real-time RBI prohibited?" must stay on the base 5.1.h,
        # NOT surface the exception (iii) leaf.
        from app.data import subpoint_emitter as se

        q = "Is real-time remote biometric identification prohibited under the EU AI Act?"
        leaves = _leaves_for(se, q)
        assert "Article 5.1.h.iii" not in leaves


def _leaves_for(se, question: str) -> set[str]:
    """Collect leaf refs the SUBPOINT_TOPIC_MAP regexes emit for a question."""
    out: set[str] = set()
    for pat, refs in se.SUBPOINT_TOPIC_MAP:
        if isinstance(pat, re.Pattern):
            m = pat.search(question)
        else:
            m = re.search(re.escape(pat), question, re.I)
        if m:
            for ref, _conf in refs:
                out.add(ref)
    return out


# ── C3: keyword maps (reclassification / explainability) ─────────────────


class TestKeywordMaps:
    def test_engine_map_reclassification_and_explainability(self):
        from app.engines._graph_rag_data import _KEYWORD_ENTITY_MAP

        d = dict(_KEYWORD_ENTITY_MAP)
        assert d.get("deemed a provider") == "Art. 25"
        assert d.get("treated as a provider") == "Art. 25"
        assert d.get("explainable ai") == "Art. 13"

    def test_scope_map_reclassification_and_explainability(self):
        from app.integrations.regenold.scope import KEYWORD_TO_ARTICLE

        assert KEYWORD_TO_ARTICLE.get("deemed a provider") == "Art. 25"
        assert KEYWORD_TO_ARTICLE.get("explainable ai") == "Art. 13"

    def test_reclassification_keys_distinct_from_art3_definitional(self):
        # "who is considered a provider" is definitional → Art. 3; the R264
        # reclassification keys must NOT collide with it.
        from app.engines._graph_rag_data import _KEYWORD_ENTITY_MAP

        d = dict(_KEYWORD_ENTITY_MAP)
        assert d.get("who is considered a provider") == "Art. 3"


# ── C2: prompt guards ────────────────────────────────────────────────────


class TestPromptGuards:
    def test_art6_3_apply_on_match_and_chapterv_and_explainability(self):
        from app.data.graph_rag_prompts import ANSWER_GENERATE_SYSTEM

        p = ANSWER_GENERATE_SYSTEM
        assert "APPLY Article 6(3) to the fact pattern" in p
        assert "Articles 51 TO 56" in p
        assert "TECHNIQUE-AGNOSTIC on explainability" in p
        assert "LIME" in p and "SHAP" in p


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
