"""R275 — Antifragile report fixes (Q8 def-skip, Q10 role-diff, Q14 MDR class).

The Antifragile expert review flagged three defects:
  * Q8 (FAIL): the AI-system definition truncated — dropped the operative
    "infers, from the input it receives, how to generate outputs" clause.
  * Q10 (FAIL): missed the Article 25 deployer->provider role transitions.
  * Q14 (PARTIAL): correct conformity routes but missed the MDR risk class.

Root causes + fixes verified deterministic + live in R275. These tests pin
the detectors, the curated verdict, the Stage-2-skip wiring, the prompt
guards, and the davidath 0-trigger / byte-identity guarantees.
"""

from __future__ import annotations

import re

from app.engines.graph_rag import (
    _definitional_stage2_skip_enabled,
    _detect_pure_definitional_inquiry,
    _detect_role_difference_inquiry,
    _is_curated_authoritative_intercept,
    _is_role_contrast_obligation,
)
from app.integrations.regenold.answer_normaliser import strip_meta_commentary


# ── Q10 — role-difference detector ───────────────────────────────────────────
class TestRoleDifferenceDetector:
    def test_fires_on_the_antifragile_q10(self):
        assert _detect_role_difference_inquiry(
            "What is the difference between the deployer and the provider?"
        )

    def test_fires_on_paraphrases(self):
        for q in (
            "How does a provider differ from a deployer?",
            "Provider versus deployer: what's the distinction?",
            "Compare the provider and the deployer roles.",
        ):
            assert _detect_role_difference_inquiry(q), q

    def test_does_not_fire_on_obligation_contrast_r137(self):
        # An obligation-CONTRAST stays on the R137 path (Art. 16/26 handling),
        # NOT the R275 curated verdict.
        q = "What is the difference between the obligations of a provider and a deployer?"
        assert not _detect_role_difference_inquiry(q)
        assert _is_role_contrast_obligation(q.lower())

    def test_does_not_fire_on_single_role(self):
        assert not _detect_role_difference_inquiry("What is a deployer?")
        assert not _detect_role_difference_inquiry(
            "What are the obligations of a deployer?"
        )

    def test_wired_into_curated_intercept_for_stage2_skip(self):
        # Q10 must be a curated authoritative intercept so Stage-2 is skipped
        # (deterministic complete verdict ships) + R274 curated-ref-protect.
        assert _is_curated_authoritative_intercept(
            "What is the difference between the deployer and the provider?"
        )

    def test_scans_live_turn_only(self):
        # A prior turn naming one role must not combine with the live turn's
        # other role to false-fire.
        flattened = (
            "Conversation so far:\nUser: Tell me about providers.\n"
            "Latest question:\nWhat is a distributor?"
        )
        assert not _detect_role_difference_inquiry(flattened)


# ── Q8 — pure-definitional detector ──────────────────────────────────────────
class TestPureDefinitionalDetector:
    def test_fires_on_the_antifragile_q8(self):
        assert _detect_pure_definitional_inquiry(
            'What is the definition of a "system of artificial intelligence"?'
        )

    def test_fires_on_art3_term_definitions(self):
        for q in (
            "What is an AI system?",
            "What is a deployer?",
            "What is a deep fake according to the EU AI Act?",
            "How is risk defined?",
        ):
            assert _detect_pure_definitional_inquiry(q), q

    def test_excludes_classification_shapes(self):
        # "risk categories" is a classification set, not a single Art. 3 term.
        assert not _detect_pure_definitional_inquiry(
            "What are the risk categories under the AI Act?"
        )
        assert not _detect_pure_definitional_inquiry(
            "What practices are prohibited?"
        )

    def test_excludes_two_role_contrast(self):
        # A provider-vs-deployer contrast is owned by the role-difference path.
        assert not _detect_pure_definitional_inquiry(
            "What is the difference between the deployer and the provider?"
        )

    def test_not_in_curated_intercept_gate(self):
        # CRITICAL: the pure-definitional detector must NOT be wired into
        # _is_curated_authoritative_intercept (that gate is also read by the
        # route's extractive-override / anchor-prune / reconcile passes, and
        # firing on davidath definitional rows would perturb them). The
        # Stage-2 skip lives directly in _two_stage_generate instead.
        assert not _is_curated_authoritative_intercept("What is an AI system?")

    def test_env_gate_default_on(self):
        assert _definitional_stage2_skip_enabled() is True


# ── davidath 0-trigger / byte-identity guarantees ────────────────────────────
class TestDavidathSafety:
    def test_role_diff_zero_trigger_on_davidath(self):
        from evals.bench.dataset import load_qa_pairs, load_scenarios

        def qtext(r: dict) -> str:
            return str(r.get("question") or r.get("prompt") or r.get("query") or "")

        qa = load_qa_pairs()
        sc = load_scenarios()
        rd_qa = [q for r in qa if _detect_role_difference_inquiry(q := qtext(r))]
        rd_sc = [q for r in sc if _detect_role_difference_inquiry(q := qtext(r))]
        assert rd_qa == [], rd_qa
        assert rd_sc == [], rd_sc


# ── Q14 — MDR-class prompt guards (davidath byte-identical) ───────────────────
class TestMdrClassPromptGuard:
    def test_prompt_carries_mdr_class_dependency(self):
        from app.data.graph_rag_prompts import ANSWER_GENERATE_SYSTEM as P

        low = P.lower()
        # The class dependency must appear in the prompt (FACTUAL GUARD +
        # REFERENCE SELECTION conformity bullet).
        assert "class iib" in low
        assert "self-certify" in low or "self-certif" in low
        assert "notified-body conformity assessment" in low or (
            "notified body" in low and "conformity assessment" in low
        )

    def test_r275_additions_are_dash_free(self):
        # R108 — a prompt addition must not MODEL forbidden punctuation. The
        # prompt carries 17 PRE-EXISTING em-dashes (R108's de-dash was
        # incomplete; the output `strip_dash_separators` backstop still cleans
        # the wire). R275 must not add to that count: verify the MDR-class
        # sentences R275 inserted contain no em/en dash or ellipsis.
        from app.data.graph_rag_prompts import ANSWER_GENERATE_SYSTEM as P

        for marker in (
            "That third-party-assessment requirement in turn flows",
            "You MUST also state the device's likely MDR",
        ):
            i = P.find(marker)
            assert i >= 0, marker
            segment = P[i : i + 320]
            assert "—" not in segment, marker
            assert "–" not in segment, marker
            assert "…" not in segment, marker


# ── R275 meta-leak strip (internal reference-tag echo) ───────────────────────
class TestWireReferenceLeakStrip:
    def test_strips_wire_references_tag_leak(self):
        leaked = (
            "An AI system that analyzes X-rays to detect tumours is high-risk "
            "under Article 6(1) because it is a regulated medical device. The "
            "conformity assessment runs through Article 43(3) via the MDR "
            "notified-body route. Wire references: "
            "[classification-annex_i_safety_component-Article 6], "
            "[classification-annex_i_safety_component-Article 43]."
        )
        out = strip_meta_commentary(leaked)
        assert "wire references:" not in out.lower()
        assert "[classification-" not in out
        # The substantive answer survives.
        assert "high-risk" in out.lower()
        assert "article 43" in out.lower()

    def test_no_op_on_clean_answer(self):
        clean = (
            "A deployer uses an AI system under its authority in the course of "
            "a professional activity under Article 3(4). The provider bears the "
            "design duties of Article 16."
        )
        assert strip_meta_commentary(clean) == clean

    def test_never_empties(self):
        only_leak = "Wire references: [classification-x-Article 6]."
        # Below the substance floor -> returns input unchanged (never empty).
        assert strip_meta_commentary(only_leak) == only_leak
