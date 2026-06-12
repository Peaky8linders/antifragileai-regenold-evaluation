"""R114 — Antifragile deep-review wire fixes.

Regression tests for the six fixes landed after the persona-based
re-review of the 20-question Antifragile dataset against the live +
deterministic wire (probe evidence: .evalout/antifragile_probe_*.json):

1. q07 — the guiding-principles enumeration sentence is cite-anchored so
   the 600-char soft cap can never drop it (it was the longest
   non-cite-anchored sentence, exactly what the cap targets first).
2. q05 — the Art. 50 KB stub attributes each paragraph to the correct
   actor (50(1)/(2) provider, 50(3)/(4) deployer). The old actor-less
   stub invited "providers" as the default subject for the deployer
   paragraphs in polished prose.
3. q19 — the prohibited gatekeeper catches verb-first emotion-recognition
   phrasings ("monitor the emotions and stress levels of workers") via
   GENERAL verb-stem x emotional-state-noun proximity patterns.
4. q08 — definition-shaped questions whose term resolves in the Art. 3
   registry anchor Art. 3 directly instead of falling through to BM25,
   where the amendment articles (Arts 102-110) win on the literal
   "artificial intelligence system" tokens.
5. q16 — the bare "obligations apply" scope keyword no longer anchors
   Art. 113 (applicability dates) onto substantive obligation questions;
   the temporal forms still do.
6. q16 — the Art. 53 stub names the Art. 51 systemic-risk gating so any
   GPAI-obligations answer can surface whether the Art. 55 tier attaches.

Every fix is general (paraphrase-tested) — none is keyed to the
reviewer's exact question text.
"""
from __future__ import annotations

import pytest


# ── 1. q07 — guiding principles survive the soft cap ─────────────────────


class TestR114GuidingPrinciplesSurviveNormalise:
    def _wire_answer(self, question: str) -> str:
        from app.engines.graph_rag import GraphContext, _deterministic_answer
        from app.integrations.regenold.models import (
            normalise_answer_for_regenold,
        )

        raw = _deterministic_answer(question, GraphContext())
        return normalise_answer_for_regenold(raw)

    @pytest.mark.parametrize(
        "q",
        [
            "What are the guiding principles established by the AI Act?",
            "What are the guiding principles of the AI Act?",
        ],
    )
    def test_all_seven_principles_survive_normalisation(self, q):
        norm = self._wire_answer(q).lower()
        for principle in (
            "human agency",
            "technical robustness",
            "privacy and data governance",
            "transparency",
            "non-discrimination",
            "social and environmental",
            "accountability",
        ):
            assert principle in norm, f"{principle!r} dropped from wire answer"

    def test_enumeration_sentence_is_cite_anchored(self):
        # The load-bearing invariant: the sentence carrying the seven
        # principles must contain an Article anchor, otherwise the
        # 600-char soft cap (drop longest non-cite-anchored sentence
        # first) targets exactly that sentence.
        from app.engines.graph_rag import GraphContext, _deterministic_answer

        raw = _deterministic_answer(
            "What are the guiding principles established by the AI Act?",
            GraphContext(),
        )
        for sentence in raw.split(". "):
            if "accountability" in sentence.lower():
                assert "article" in sentence.lower(), (
                    "principles sentence lost its cite anchor — the soft "
                    "cap will drop it again"
                )
                break
        else:
            pytest.fail("principles sentence not found in curated answer")


# ── 2. q05 — Art. 50 stub role attribution ───────────────────────────────


class TestR114Art50RoleAttribution:
    def _stub(self) -> str:
        from app.data.kb import EC_CHECKER_OBLIGATION_MAP

        entry = EC_CHECKER_OBLIGATION_MAP["Art. 50"]
        return str(entry)

    def test_deployer_owns_exposed_persons_duty(self):
        text = self._stub().lower()
        # The 50(3) duty sentence must attribute deployers, and the old
        # actor-less shape must be gone.
        assert "deployers must inform exposed persons" in text

    def test_provider_owns_interaction_and_marking(self):
        text = self._stub().lower()
        assert "providers" in text
        assert "art. 50(1)" in text
        assert "art. 50(2)" in text

    def test_deployer_owns_deepfake_labelling(self):
        text = self._stub().lower()
        assert "art. 50(4)" in text
        # the deepfake clause sits in the deployer half of the stub
        deployer_half = text.split("deployers", 1)[1]
        assert "deepfake" in deployer_half


# ── 3. q19 — gatekeeper verb-object emotion patterns ─────────────────────


class TestR114GatekeeperVerbPatterns:
    @pytest.mark.parametrize(
        "q",
        [
            # Antifragile q19 shape
            "A pharmaceutical company wants to use an AI system to monitor "
            "the emotions and stress levels of their manufacturing line "
            "workers to improve efficiency. Is this allowed?",
            # paraphrases — verb-stem generality, not q19's words
            "Can we track our employees emotional state with AI cameras?",
            "Our HR tool analyses the mental state of call-centre staff.",
            "We measure worker stress levels via webcam AI.",
            "The system detects emotions of students during exams.",
        ],
    )
    def test_verb_first_emotion_phrasings_fire(self, q):
        from app.engines.prohibited_gatekeeper import scan_for_prohibitions

        hits = scan_for_prohibitions(q)
        assert any(sub == "Art. 5.1.f" for _, sub in hits), q

    @pytest.mark.parametrize(
        "q",
        [
            "What does Article 13 require for transparency?",
            "We are a provider of a credit-scoring AI system.",
            "Our chatbot answers customer questions about insurance.",
            "Does the AI Act regulate recommender systems?",
            # "emotional" alone (no recognition verb) must NOT fire
            "Is emotional support from a wellness app regulated?",
        ],
    )
    def test_no_false_positives(self, q):
        from app.engines.prohibited_gatekeeper import scan_for_prohibitions

        hits = scan_for_prohibitions(q)
        assert not any(sub == "Art. 5.1.f" for _, sub in hits), q


# ── 4. q08 — definitional Art. 3 anchor before BM25 ──────────────────────


class TestR114DefinitionalAnchor:
    @pytest.mark.parametrize(
        "q",
        [
            'What is the definition of a "system of artificial intelligence"?',
            "What is the definition of an AI system?",
            "How is a deployer defined?",
            "What does substantial modification mean?",
        ],
    )
    def test_definition_questions_anchor_art3(self, q):
        from app.engines.graph_rag import _deterministic_parse

        entities = _deterministic_parse(q).entities
        assert "Art. 3" in entities, f"{q!r} -> {entities}"

    def test_inverted_phrase_does_not_surface_amendment_articles(self):
        # Pre-R114: BM25 ranked Arts 65/107/108/110 (their EUR-Lex prose
        # repeats "artificial intelligence system") for the inverted
        # phrasing, polluting grounding + citations.
        from app.engines.graph_rag import _deterministic_parse

        q = 'What is the definition of a "system of artificial intelligence"?'
        entities = _deterministic_parse(q).entities
        for spurious in ("Art. 65", "Art. 107", "Art. 108", "Art. 110"):
            assert spurious not in entities, entities

    def test_non_definition_question_unaffected(self):
        # The anchor only fires for definition-shaped questions whose
        # term resolves in the Art. 3 registry — obligation questions
        # keep their existing routing.
        from app.engines.graph_rag import _deterministic_parse

        q = "What are the obligations of importers of high-risk AI systems?"
        entities = _deterministic_parse(q).entities
        assert "Art. 23" in entities


# ── 5. q16 — "obligations apply" needs a temporal marker for Art. 113 ────


class TestR114ObligationsApplyTemporal:
    def _anchors(self, q: str):
        from app.integrations.regenold.scope import classify_conversation

        v = classify_conversation([{"role": "user", "content": q}])
        return getattr(v, "anchor_articles", ()) or ()

    @pytest.mark.parametrize(
        "q",
        [
            "Our life sciences startup developed a general-purpose AI model "
            "trained on massive amounts of genomic data. What transparency "
            "obligations apply to us?",
            "What obligations apply to deployers of high-risk AI?",
        ],
    )
    def test_substantive_obligation_questions_do_not_anchor_113(self, q):
        assert "Art. 113" not in self._anchors(q)

    @pytest.mark.parametrize(
        "q",
        [
            "When do the obligations apply for high-risk systems?",
            "When do obligations apply under the AI Act?",
        ],
    )
    def test_temporal_forms_still_anchor_113(self, q):
        assert "Art. 113" in self._anchors(q)


# ── 6. q16 — Art. 53 stub names the systemic-risk gate ───────────────────


class TestR114Art53SystemicGate:
    def test_stub_names_art51_threshold_and_art55(self):
        from app.data.kb import EC_CHECKER_OBLIGATION_MAP

        text = str(EC_CHECKER_OBLIGATION_MAP["Art. 53"])
        assert "Art. 51" in text
        assert "Art. 55" in text
        assert "10^25" in text


# ── 7. generalization audit — minimal-risk detector paraphrases ──────────


class TestR114MinimalRiskDetectorGeneralization:
    """The R111 detector only fired on Wh-prefix shapes (the reviewer's
    exact phrasing) — classification-predicate paraphrases fell through
    to the QA dump, which BM25-retrieves HIGH-RISK content for a
    minimal-risk question (generalization-audit HIGH finding)."""

    @pytest.mark.parametrize(
        "q",
        [
            "Which AI applications are considered minimal risk?",
            "What counts as low-risk under the Act?",
            "Which systems fall under the minimal-risk tier?",
            "Is a chatbot classified as minimal risk or limited risk?",
        ],
    )
    def test_predicate_shapes_fire(self, q):
        from app.engines.graph_rag import _detect_minimal_risk_inquiry

        assert _detect_minimal_risk_inquiry(q) is True

    @pytest.mark.parametrize(
        "q",
        [
            # scenario shapes stay on the scenario-classifier path
            "We are a provider of a spam filter. Is our system considered "
            "minimal risk?",
            "Our company builds chatbots. Are they deemed low-risk?",
            # risk-management noun family still excluded
            "What minimal risk management measures does Article 9 require?",
        ],
    )
    def test_guards_hold(self, q):
        from app.engines.graph_rag import _detect_minimal_risk_inquiry

        assert _detect_minimal_risk_inquiry(q) is False


# ── 8. generalization audit — Art. 111 anchors cannot flip scope alone ───


class TestR114GrandfatheringAnchorsScopeWeak:
    """The R94 grandfathering anchors are generic EU product-law phrases;
    they must anchor Art. 111 for retrieval WITHOUT flipping the scope
    gate on non-AI product questions (generalization-audit HIGH finding)."""

    def _in_scope(self, q: str) -> bool:
        from app.integrations.regenold.scope import classify_conversation

        return bool(
            classify_conversation([{"role": "user", "content": q}]).in_scope
        )

    @pytest.mark.parametrize(
        "q",
        [
            "Was my washing machine placed on the market before 2020?",
            "Our toys were already placed on the market last year. Any new "
            "rules?",
        ],
    )
    def test_non_ai_product_questions_refuse(self, q):
        assert self._in_scope(q) is False

    @pytest.mark.parametrize(
        "q",
        [
            "Our AI system was placed on the market before 2 August 2026. "
            "Do the high-risk obligations apply retroactively?",
            "A medical-device AI put into service before 2026, is it "
            "grandfathered under the AI Act?",
        ],
    )
    def test_ai_transition_questions_stay_in_scope(self, q):
        assert self._in_scope(q) is True
