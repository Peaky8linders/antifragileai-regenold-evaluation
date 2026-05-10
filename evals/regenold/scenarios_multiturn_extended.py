"""Extended multi-turn scenarios for the Regenold ask API eval harness.

100 scenarios across 8 sub-categories of multi-turn conversation patterns,
all under the umbrella ``in_scope_multi_turn`` category. Authored to stress
the engine's coreference / anchor-borrow / follow-up-marker plumbing in
``app/integrations/regenold/scope.py::_live_question_borrows_anchor`` and
``classify_conversation``.

Sub-categories (see ID prefix):
    A. Pronoun / anaphor carry           (12)  — multiturn_a_*
    B. Process follow-ups                (12)  — multiturn_b_*
    C. Topic-shift inside same article   (12)  — multiturn_c_*
    D. Cross-article carry               (12)  — multiturn_d_*
    E. Negative-confirmation traps       (12)  — multiturn_e_*
    F. Multi-turn with reference correction (12) — multiturn_f_*
    G. Long histories (4-6 turns)        (14)  — multiturn_g_*
    H. Boundary cases                    (14)  — multiturn_h_*

All scenarios use ``category="in_scope_multi_turn"`` so the eval gate's
per-category coverage check sees them as one cohesive bucket.
"""
from __future__ import annotations

from evals.regenold.scenarios import (
    Scenario,
    ScenarioCheck,
    _refused,
    _has_reference,
    _no_reference_to,
    _answer_does_not_contain,
    _answer_mentions_any,
    _refusal_checks,
)


EXTRA_MULTITURN_SCENARIOS: tuple[Scenario, ...] = (
    # ──────────────────────────────────────────────────────────────────────
    # A. Pronoun / anaphor carry (12)
    # ──────────────────────────────────────────────────────────────────────
    Scenario(
        id="multiturn_a_pronoun_carry_art13",
        category="in_scope_multi_turn",
        description="Pronoun 'it' resolves to the prior subject (Art. 13 transparency).",
        messages=(
            {"role": "user", "content": "Walk me through Art. 13 transparency obligations."},
            {
                "role": "assistant",
                "content": "Article 13 requires high-risk providers to design transparency mechanisms so deployers can interpret outputs.",
            },
            {"role": "user", "content": "Does it apply to all high-risk systems?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_13", lambda b: _has_reference(b, "Article 13")),
        ),
    ),
    Scenario(
        id="multiturn_a_pronoun_carry_art27_who",
        category="in_scope_multi_turn",
        description="'Who has to do it?' must resolve to FRIA (Art. 27).",
        messages=(
            {"role": "user", "content": "Tell me about the Fundamental Rights Impact Assessment under Art. 27."},
            {
                "role": "assistant",
                "content": "Article 27 imposes a Fundamental Rights Impact Assessment on certain deployers of high-risk AI before first use.",
            },
            {"role": "user", "content": "Who has to do it?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_27", lambda b: _has_reference(b, "Article 27")),
        ),
    ),
    Scenario(
        id="multiturn_a_what_about_deployers_art13",
        category="in_scope_multi_turn",
        description="'What about deployers?' carries the Art. 13 transparency anchor forward.",
        messages=(
            {"role": "user", "content": "What does Art. 13 require for instructions for use?"},
            {
                "role": "assistant",
                "content": "Article 13(2)-(3) requires providers to supply concise, complete, correct instructions for use.",
            },
            {"role": "user", "content": "What about deployers?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_relevant_anchor",
                lambda b: _has_reference(b, "Article 13") or _has_reference(b, "Article 26"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_a_pronoun_them_art10_data",
        category="in_scope_multi_turn",
        description="'Are they mandatory?' carries Art. 10 data-governance anchor.",
        messages=(
            {"role": "user", "content": "Summarise the Art. 10 data governance requirements."},
            {
                "role": "assistant",
                "content": "Article 10 requires training, validation, and testing data sets to meet quality criteria for high-risk AI.",
            },
            {"role": "user", "content": "Are they mandatory for every high-risk model?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_10", lambda b: _has_reference(b, "Article 10")),
        ),
    ),
    Scenario(
        id="multiturn_a_pronoun_this_art9_risk",
        category="in_scope_multi_turn",
        description="'Is it a one-time exercise?' resolves to Art. 9 risk management.",
        messages=(
            {"role": "user", "content": "Explain the risk management system in Art. 9."},
            {
                "role": "assistant",
                "content": "Article 9 mandates a continuous, iterative risk management system across the AI lifecycle.",
            },
            {"role": "user", "content": "Is it a one-time exercise?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_9", lambda b: _has_reference(b, "Article 9")),
        ),
    ),
    Scenario(
        id="multiturn_a_pronoun_who_art50",
        category="in_scope_multi_turn",
        description="'Who is on the hook?' resolves to Art. 50 transparency duties.",
        messages=(
            {"role": "user", "content": "What does Art. 50 say about deepfake disclosure?"},
            {
                "role": "assistant",
                "content": "Article 50(4) requires deployers of AI generating deepfakes to disclose the artificial origin of the content.",
            },
            {"role": "user", "content": "Who is on the hook for compliance?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_50", lambda b: _has_reference(b, "Article 50")),
        ),
    ),
    Scenario(
        id="multiturn_a_pronoun_does_it_art14",
        category="in_scope_multi_turn",
        description="'Does it apply?' resolves to Art. 14 human oversight.",
        messages=(
            {"role": "user", "content": "Tell me about human oversight under Art. 14."},
            {
                "role": "assistant",
                "content": "Article 14 requires high-risk AI to be designed for effective human oversight during use.",
            },
            {"role": "user", "content": "Does it apply to fully automated systems too?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_14", lambda b: _has_reference(b, "Article 14")),
        ),
    ),
    Scenario(
        id="multiturn_a_pronoun_what_about_smaller",
        category="in_scope_multi_turn",
        description="'What about smaller providers?' carries Art. 17 QMS anchor.",
        messages=(
            {"role": "user", "content": "What does Art. 17 require for the quality management system?"},
            {
                "role": "assistant",
                "content": "Article 17 obliges providers of high-risk AI to put in place a documented quality management system.",
            },
            {"role": "user", "content": "What about smaller providers?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_17", lambda b: _has_reference(b, "Article 17")),
        ),
    ),
    Scenario(
        id="multiturn_a_pronoun_for_whom_art55",
        category="in_scope_multi_turn",
        description="'For whom?' resolves to Art. 55 systemic-risk obligations.",
        messages=(
            {"role": "user", "content": "Talk me through Art. 55 obligations for GPAI with systemic risk."},
            {
                "role": "assistant",
                "content": "Article 55 imposes additional model evaluation, adversarial testing, and incident reporting on systemic-risk GPAI.",
            },
            {"role": "user", "content": "For whom exactly?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_gpai_article",
                lambda b: _has_reference(b, "Article 55") or _has_reference(b, "Article 51"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_a_pronoun_by_whom_art72",
        category="in_scope_multi_turn",
        description="'By whom is it carried out?' resolves to Art. 72 PMMP.",
        messages=(
            {"role": "user", "content": "What is post-market monitoring under Art. 72?"},
            {
                "role": "assistant",
                "content": "Article 72 requires providers of high-risk AI to operate a post-market monitoring system covering performance throughout the lifecycle.",
            },
            {"role": "user", "content": "By whom is it carried out?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_72", lambda b: _has_reference(b, "Article 72")),
        ),
    ),
    Scenario(
        id="multiturn_a_pronoun_them_art15",
        category="in_scope_multi_turn",
        description="'Do they vary by sector?' resolves to Art. 15 accuracy/robustness/cybersec.",
        messages=(
            {"role": "user", "content": "Summarise Art. 15 accuracy and robustness requirements."},
            {
                "role": "assistant",
                "content": "Article 15 requires high-risk AI to achieve appropriate accuracy, robustness, and cybersecurity.",
            },
            {"role": "user", "content": "Do they vary by sector?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_15", lambda b: _has_reference(b, "Article 15")),
        ),
    ),
    Scenario(
        id="multiturn_a_pronoun_who_has_art53",
        category="in_scope_multi_turn",
        description="'Who has to publish that?' resolves to Art. 53 GPAI transparency.",
        messages=(
            {"role": "user", "content": "What summary of training content does Art. 53 require?"},
            {
                "role": "assistant",
                "content": "Article 53 requires GPAI providers to publish a sufficiently detailed summary of the content used for training.",
            },
            {"role": "user", "content": "Who has to publish that?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_53", lambda b: _has_reference(b, "Article 53")),
        ),
    ),
    # ──────────────────────────────────────────────────────────────────────
    # B. Process follow-ups (12) — exercise NEW strong markers
    # ──────────────────────────────────────────────────────────────────────
    Scenario(
        id="multiturn_b_retrain_cadence_art10",
        category="in_scope_multi_turn",
        description="'What if we re-train the model quarterly?' under Art. 10 data governance.",
        messages=(
            {"role": "user", "content": "We rely on Art. 10 for our training data governance — quality criteria and bias examination."},
            {
                "role": "assistant",
                "content": "Article 10 covers data quality, provenance, and bias examination for high-risk AI training, validation, and testing data sets.",
            },
            {"role": "user", "content": "What if we re-train the model quarterly with fresh customer data?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_data_or_substantial_modification",
                lambda b: _has_reference(b, "Article 10")
                or _has_reference(b, "Article 25")
                or _has_reference(b, "Article 3"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_b_how_often_art9_review",
        category="in_scope_multi_turn",
        description="'How often must we review it?' resolves to Art. 9 RMS cadence.",
        messages=(
            {"role": "user", "content": "Walk me through the Art. 9 risk management system."},
            {
                "role": "assistant",
                "content": "Article 9 mandates an iterative, continuous risk management system across the AI lifecycle.",
            },
            {"role": "user", "content": "How often must we review it?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_9", lambda b: _has_reference(b, "Article 9")),
        ),
    ),
    Scenario(
        id="multiturn_b_how_often_art72_pmmp",
        category="in_scope_multi_turn",
        description="'How often do we report?' under Art. 72 post-market monitoring.",
        messages=(
            {"role": "user", "content": "What is required by Art. 72 post-market monitoring?"},
            {
                "role": "assistant",
                "content": "Article 72 requires providers to operate a documented post-market monitoring system for high-risk AI.",
            },
            {"role": "user", "content": "How often do we report findings?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_72", lambda b: _has_reference(b, "Article 72")),
        ),
    ),
    Scenario(
        id="multiturn_b_are_these_mandatory_art10",
        category="in_scope_multi_turn",
        description="'Are these data-governance criteria mandatory?' under Art. 10.",
        messages=(
            {"role": "user", "content": "Tell me about Art. 10 data quality criteria."},
            {
                "role": "assistant",
                "content": "Article 10(2)-(3) sets quality criteria — relevance, representativeness, completeness — for training, validation, and test data.",
            },
            {"role": "user", "content": "Are these criteria mandatory or best-practice?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_10", lambda b: _has_reference(b, "Article 10")),
        ),
    ),
    Scenario(
        id="multiturn_b_tell_me_more_art12_logs",
        category="in_scope_multi_turn",
        description="'Tell me more about retention.' resolves to Art. 12 / Art. 19 log retention.",
        messages=(
            {"role": "user", "content": "Summarise the logging duty in Art. 12."},
            {
                "role": "assistant",
                "content": "Article 12 requires high-risk AI to automatically record events relevant for safety throughout its lifecycle.",
            },
            {"role": "user", "content": "Tell me more about retention periods."},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_logging_article",
                lambda b: _has_reference(b, "Article 12") or _has_reference(b, "Article 19"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_b_more_details_art14_oversight",
        category="in_scope_multi_turn",
        description="'More details on the override mechanism?' under Art. 14 human oversight.",
        messages=(
            {"role": "user", "content": "What does Art. 14 say about human oversight measures?"},
            {
                "role": "assistant",
                "content": "Article 14(4) requires designs that let a human stop, override, or interpret outputs.",
            },
            {"role": "user", "content": "More details on the override mechanism, please."},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_14", lambda b: _has_reference(b, "Article 14")),
        ),
    ),
    Scenario(
        id="multiturn_b_how_often_art73_incidents",
        category="in_scope_multi_turn",
        description="'How often must we report incidents?' under Art. 73.",
        messages=(
            {"role": "user", "content": "What does Art. 73 say about serious-incident reporting?"},
            {
                "role": "assistant",
                "content": "Article 73 obliges providers to report serious AI incidents to market surveillance authorities.",
            },
            {"role": "user", "content": "How often must such reports be filed?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_73", lambda b: _has_reference(b, "Article 73")),
        ),
    ),
    Scenario(
        id="multiturn_b_what_if_retrain_art25_modification",
        category="in_scope_multi_turn",
        description="'What if we retrain on user feedback weekly?' carries Art. 25 substantial-mod context.",
        messages=(
            {"role": "user", "content": "Explain when fine-tuning a third-party model makes us a provider under Art. 25."},
            {
                "role": "assistant",
                "content": "Article 25 says substantial modification or rebranding can flip a deployer into a provider role.",
            },
            {"role": "user", "content": "What if we retrain on user feedback weekly?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_value_chain_article",
                lambda b: _has_reference(b, "Article 25") or _has_reference(b, "Article 3"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_b_tell_me_more_art27_who_signs",
        category="in_scope_multi_turn",
        description="'Tell me more about who signs off the FRIA.' under Art. 27.",
        messages=(
            {"role": "user", "content": "Summarise Art. 27 FRIA scope."},
            {
                "role": "assistant",
                "content": "Article 27 binds public-service deployers of certain Annex III high-risk AI systems to perform a FRIA before use.",
            },
            {"role": "user", "content": "Tell me more about who signs off internally."},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_27", lambda b: _has_reference(b, "Article 27")),
        ),
    ),
    Scenario(
        id="multiturn_b_are_these_continuous_art15",
        category="in_scope_multi_turn",
        description="'Are these checks continuous?' under Art. 15 accuracy/robustness.",
        messages=(
            {"role": "user", "content": "Cover Art. 15 accuracy and robustness duties."},
            {
                "role": "assistant",
                "content": "Article 15 sets accuracy, robustness, and cybersecurity expectations for high-risk AI.",
            },
            {"role": "user", "content": "Are these checks continuous or only pre-market?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_15", lambda b: _has_reference(b, "Article 15")),
        ),
    ),
    Scenario(
        id="multiturn_b_how_often_audit_art17",
        category="in_scope_multi_turn",
        description="'How often must we audit the QMS?' under Art. 17.",
        messages=(
            {"role": "user", "content": "What does Art. 17 require for the QMS?"},
            {
                "role": "assistant",
                "content": "Article 17 requires a documented quality management system covering policies, procedures, and instructions.",
            },
            {"role": "user", "content": "How often must we audit it?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_17", lambda b: _has_reference(b, "Article 17")),
        ),
    ),
    Scenario(
        id="multiturn_b_what_if_we_retrain_art10_drift",
        category="in_scope_multi_turn",
        description="'What if we re-train monthly?' resolves to Art. 10 + drift considerations.",
        messages=(
            {"role": "user", "content": "Walk me through Art. 10 data governance for our credit scoring system."},
            {
                "role": "assistant",
                "content": "Article 10 requires bias examination, completeness checks, and provenance tracking for training data.",
            },
            {"role": "user", "content": "What if we re-train monthly on new customer cohorts?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_data_or_modification",
                lambda b: _has_reference(b, "Article 10")
                or _has_reference(b, "Article 25")
                or _has_reference(b, "Article 72"),
            ),
        ),
    ),
    # ──────────────────────────────────────────────────────────────────────
    # C. Topic-shift inside same article (12)
    # ──────────────────────────────────────────────────────────────────────
    Scenario(
        id="multiturn_c_art13_para1_to_para2",
        category="in_scope_multi_turn",
        description="Shift inside Art. 13 from para (1) transparency to para (2) instructions for use.",
        messages=(
            {"role": "user", "content": "What does Art. 13(1) require for transparency?"},
            {
                "role": "assistant",
                "content": "Article 13(1) requires transparency designed so deployers can interpret and use outputs appropriately.",
            },
            {"role": "user", "content": "And what does paragraph (2) add about instructions for use?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_13", lambda b: _has_reference(b, "Article 13")),
        ),
    ),
    Scenario(
        id="multiturn_c_art26_obligations_to_logging",
        category="in_scope_multi_turn",
        description="Shift inside Art. 26 from headline obligations to log-retention duty.",
        messages=(
            {"role": "user", "content": "Summarise Art. 26 deployer obligations."},
            {
                "role": "assistant",
                "content": "Article 26 requires deployers to use high-risk AI in accordance with instructions, assign human oversight, and ensure relevant input data quality.",
            },
            {"role": "user", "content": "And the logging duty in the same article?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_26", lambda b: _has_reference(b, "Article 26")),
        ),
    ),
    Scenario(
        id="multiturn_c_art9_iterative_to_testing",
        category="in_scope_multi_turn",
        description="Shift inside Art. 9 from iterative system to testing in real conditions.",
        messages=(
            {"role": "user", "content": "Outline Art. 9 risk management."},
            {
                "role": "assistant",
                "content": "Article 9 requires an iterative risk management system covering identification, estimation, evaluation, and mitigation.",
            },
            {"role": "user", "content": "And how does Art. 9(8) handle testing in real conditions?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_9", lambda b: _has_reference(b, "Article 9")),
        ),
    ),
    Scenario(
        id="multiturn_c_art10_quality_to_bias",
        category="in_scope_multi_turn",
        description="Shift inside Art. 10 from data quality (para 2) to bias (para 5).",
        messages=(
            {"role": "user", "content": "Explain Art. 10(2) data quality criteria."},
            {
                "role": "assistant",
                "content": "Article 10(2) sets relevance, representativeness, and accuracy criteria for training, validation, and test data.",
            },
            {"role": "user", "content": "And what does paragraph (5) say about bias examination?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_10", lambda b: _has_reference(b, "Article 10")),
        ),
    ),
    Scenario(
        id="multiturn_c_art14_design_to_biometric",
        category="in_scope_multi_turn",
        description="Shift inside Art. 14 from design oversight to biometric two-person rule (para 5).",
        messages=(
            {"role": "user", "content": "What does Art. 14(1) require for human oversight design?"},
            {
                "role": "assistant",
                "content": "Article 14(1) requires high-risk AI to be designed for effective oversight during use.",
            },
            {"role": "user", "content": "And the biometric two-person verification in (5)?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_14", lambda b: _has_reference(b, "Article 14")),
        ),
    ),
    Scenario(
        id="multiturn_c_art50_chatbot_to_deepfake",
        category="in_scope_multi_turn",
        description="Shift inside Art. 50 from chatbot disclosure (1) to deepfake (4).",
        messages=(
            {"role": "user", "content": "What's the chatbot transparency duty in Art. 50(1)?"},
            {
                "role": "assistant",
                "content": "Article 50(1) requires AI providers to inform natural persons that they are interacting with an AI system.",
            },
            {"role": "user", "content": "And paragraph (4) on deepfakes?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_50", lambda b: _has_reference(b, "Article 50")),
        ),
    ),
    Scenario(
        id="multiturn_c_art53_summary_to_copyright",
        category="in_scope_multi_turn",
        description="Shift inside Art. 53 from training-data summary to copyright policy.",
        messages=(
            {"role": "user", "content": "Tell me about the training-data summary in Art. 53."},
            {
                "role": "assistant",
                "content": "Article 53(1)(d) obliges GPAI providers to publish a sufficiently detailed summary of training content.",
            },
            {"role": "user", "content": "And what about the copyright-policy duty in the same article?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_53", lambda b: _has_reference(b, "Article 53")),
        ),
    ),
    Scenario(
        id="multiturn_c_art55_eval_to_incident",
        category="in_scope_multi_turn",
        description="Shift inside Art. 55 from model evaluation to systemic-incident reporting.",
        messages=(
            {"role": "user", "content": "What evaluation does Art. 55 require for systemic-risk GPAI?"},
            {
                "role": "assistant",
                "content": "Article 55 requires model evaluation including adversarial testing for systemic-risk GPAI providers.",
            },
            {"role": "user", "content": "And the systemic-incident reporting bit?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_55", lambda b: _has_reference(b, "Article 55")),
        ),
    ),
    Scenario(
        id="multiturn_c_art27_scope_to_consultation",
        category="in_scope_multi_turn",
        description="Shift inside Art. 27 from FRIA scope to stakeholder consultation.",
        messages=(
            {"role": "user", "content": "Who must perform a FRIA under Art. 27?"},
            {
                "role": "assistant",
                "content": "Article 27 binds public-service deployers of specific Annex III high-risk AI to a FRIA before first use.",
            },
            {"role": "user", "content": "And what does the article say about stakeholder consultation?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_27", lambda b: _has_reference(b, "Article 27")),
        ),
    ),
    Scenario(
        id="multiturn_c_art72_monitoring_to_corrective",
        category="in_scope_multi_turn",
        description="Shift inside Art. 72 from PMMP to corrective actions.",
        messages=(
            {"role": "user", "content": "What does Art. 72 require for post-market monitoring?"},
            {
                "role": "assistant",
                "content": "Article 72 requires providers to actively collect, document, and analyse high-risk AI performance data after placing on the market.",
            },
            {"role": "user", "content": "And what corrective actions does the same article require?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_corrective_article",
                lambda b: _has_reference(b, "Article 72") or _has_reference(b, "Article 20"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_c_art99_fines_to_calc",
        category="in_scope_multi_turn",
        description="Shift inside Art. 99 from fine ceilings (3) to calculation criteria (7).",
        messages=(
            {"role": "user", "content": "What's the maximum fine for Art. 5 prohibited-AI breach under Art. 99?"},
            {
                "role": "assistant",
                "content": "Article 99(3) sets a ceiling of EUR 35M or 7% of worldwide annual turnover, whichever is higher.",
            },
            {"role": "user", "content": "And how is the actual fine calculated within that ceiling?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_99", lambda b: _has_reference(b, "Article 99")),
        ),
    ),
    Scenario(
        id="multiturn_c_art11_para1_to_annex_iv",
        category="in_scope_multi_turn",
        description="Shift inside Art. 11 from headline duty to Annex IV content.",
        messages=(
            {"role": "user", "content": "Summarise Art. 11 technical documentation duty."},
            {
                "role": "assistant",
                "content": "Article 11 requires providers to draft technical documentation for high-risk AI before market placement.",
            },
            {"role": "user", "content": "And what's the Annex IV content list it points to?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_art_11_or_annex_iv",
                lambda b: _has_reference(b, "Article 11") or _has_reference(b, "Annex IV"),
            ),
        ),
    ),
    # ──────────────────────────────────────────────────────────────────────
    # D. Cross-article carry (12)
    # ──────────────────────────────────────────────────────────────────────
    Scenario(
        id="multiturn_d_fria_to_deployer_obligations",
        category="in_scope_multi_turn",
        description="Art. 27 FRIA → 'Beyond the FRIA, what else?' carries to Art. 26.",
        messages=(
            {"role": "user", "content": "Tell me about Art. 27 FRIA for our employment-screening tool."},
            {
                "role": "assistant",
                "content": "Article 27 imposes a FRIA on public-body deployers of specified Annex III high-risk AI before first use.",
            },
            {"role": "user", "content": "Beyond the FRIA, what else do we owe as a deployer?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_deployer_article",
                lambda b: _has_reference(b, "Article 26") or _has_reference(b, "Article 27"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_d_art10_to_art11_docs",
        category="in_scope_multi_turn",
        description="Art. 10 data governance → 'Where does that show up in tech docs?' carries to Art. 11/Annex IV.",
        messages=(
            {"role": "user", "content": "Explain Art. 10 bias examination."},
            {
                "role": "assistant",
                "content": "Article 10(5) requires bias examination on training, validation, and test data sets used for high-risk AI.",
            },
            {"role": "user", "content": "Where does that show up in the technical documentation?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_docs_article",
                lambda b: _has_reference(b, "Article 11")
                or _has_reference(b, "Annex IV")
                or _has_reference(b, "Article 10"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_d_art9_to_art15_robustness",
        category="in_scope_multi_turn",
        description="Art. 9 risk → 'What does that mean for robustness?' carries to Art. 15.",
        messages=(
            {"role": "user", "content": "Explain how Art. 9 risk management works."},
            {
                "role": "assistant",
                "content": "Article 9 requires identifying, evaluating, and mitigating risks across the AI lifecycle.",
            },
            {"role": "user", "content": "What does that mean for robustness specifically?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_risk_or_robustness_article",
                lambda b: _has_reference(b, "Article 15") or _has_reference(b, "Article 9"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_d_art13_to_art50_chatbot",
        category="in_scope_multi_turn",
        description="Art. 13 transparency → 'And for chatbots?' carries to Art. 50.",
        messages=(
            {"role": "user", "content": "Walk through Art. 13 transparency."},
            {
                "role": "assistant",
                "content": "Article 13 covers transparency to deployers for high-risk AI.",
            },
            {"role": "user", "content": "And what about chatbots talking to end users?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_transparency_article",
                lambda b: _has_reference(b, "Article 50") or _has_reference(b, "Article 13"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_d_art14_to_art26_deployer_oversight",
        category="in_scope_multi_turn",
        description="Art. 14 design oversight → 'How does the deployer fit?' carries to Art. 26.",
        messages=(
            {"role": "user", "content": "Walk me through Art. 14 oversight design duties."},
            {
                "role": "assistant",
                "content": "Article 14 requires the provider to design high-risk AI for effective human oversight.",
            },
            {"role": "user", "content": "How does the deployer fit into that?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_oversight_article",
                lambda b: _has_reference(b, "Article 26") or _has_reference(b, "Article 14"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_d_art17_to_art43_conformity",
        category="in_scope_multi_turn",
        description="Art. 17 QMS → 'How does conformity assessment use it?' carries to Art. 43.",
        messages=(
            {"role": "user", "content": "Explain the Art. 17 QMS scope."},
            {
                "role": "assistant",
                "content": "Article 17 requires a quality management system covering design, testing, and production for high-risk AI.",
            },
            {"role": "user", "content": "How does conformity assessment build on that?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_conformity_article",
                lambda b: _has_reference(b, "Article 43") or _has_reference(b, "Article 17"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_d_art53_to_art55_systemic",
        category="in_scope_multi_turn",
        description="Art. 53 GPAI baseline → 'And if it's systemic?' carries to Art. 55.",
        messages=(
            {"role": "user", "content": "Summarise Art. 53 baseline GPAI obligations."},
            {
                "role": "assistant",
                "content": "Article 53 imposes baseline transparency, copyright-policy, and documentation duties on GPAI providers.",
            },
            {"role": "user", "content": "And if our model qualifies as systemic-risk?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_gpai_article",
                lambda b: _has_reference(b, "Article 55") or _has_reference(b, "Article 51"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_d_annex_iii_to_art_6",
        category="in_scope_multi_turn",
        description="Annex III categories → 'How does that link to Art. 6 classification?'",
        messages=(
            {"role": "user", "content": "Run through Annex III high-risk categories for our employment AI."},
            {
                "role": "assistant",
                "content": "Annex III(4) covers AI for employment, worker management, and access to self-employment.",
            },
            {"role": "user", "content": "How does that link to Art. 6 classification?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_classification_article",
                lambda b: _has_reference(b, "Article 6") or _has_reference(b, "Annex III"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_d_art72_to_art73_serious",
        category="in_scope_multi_turn",
        description="Art. 72 PMMP → 'And serious incidents?' carries to Art. 73.",
        messages=(
            {"role": "user", "content": "Tell me about Art. 72 post-market monitoring."},
            {
                "role": "assistant",
                "content": "Article 72 requires a post-market monitoring system for high-risk AI providers.",
            },
            {"role": "user", "content": "And serious incidents — what's the duty there?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_incident_article",
                lambda b: _has_reference(b, "Article 73") or _has_reference(b, "Article 72"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_d_art99_to_art113_dates",
        category="in_scope_multi_turn",
        description="Art. 99 fines → 'When do they apply?' carries to Art. 113 timeline.",
        messages=(
            {"role": "user", "content": "What's the Art. 99 fine ceiling for prohibited AI?"},
            {
                "role": "assistant",
                "content": "Article 99(3) caps fines for Article 5 prohibitions at EUR 35M or 7% of worldwide turnover.",
            },
            {"role": "user", "content": "When did that fine regime start applying?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_timeline_article",
                lambda b: _has_reference(b, "Article 113") or _has_reference(b, "Article 99"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_d_art5_to_art6_high_risk",
        category="in_scope_multi_turn",
        description="Art. 5 prohibitions → 'If not prohibited, is it high-risk?' carries to Art. 6.",
        messages=(
            {"role": "user", "content": "Walk me through Art. 5 prohibited AI practices."},
            {
                "role": "assistant",
                "content": "Article 5 prohibits manipulation, exploitation of vulnerabilities, social scoring, and certain biometric uses.",
            },
            {"role": "user", "content": "If our system isn't prohibited, is it automatically high-risk under Art. 6?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_classification_article",
                lambda b: _has_reference(b, "Article 6") or _has_reference(b, "Article 5"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_d_art11_to_art47_declaration",
        category="in_scope_multi_turn",
        description="Art. 11 tech docs → 'And the EU declaration?' carries to Art. 47.",
        messages=(
            {"role": "user", "content": "What goes into Art. 11 technical documentation?"},
            {
                "role": "assistant",
                "content": "Article 11 requires technical documentation per Annex IV before placement on the market.",
            },
            {"role": "user", "content": "And the EU declaration of conformity?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_declaration_article",
                lambda b: _has_reference(b, "Article 47") or _has_reference(b, "Article 11"),
            ),
        ),
    ),
    # ──────────────────────────────────────────────────────────────────────
    # E. Negative-confirmation traps (12)
    # ──────────────────────────────────────────────────────────────────────
    Scenario(
        id="multiturn_e_neg_gpai_exempt",
        category="in_scope_multi_turn",
        description="Assistant explained Art. 53 → user asks 'so it doesn't apply to GPAI?' Must not agree.",
        messages=(
            {"role": "user", "content": "What does Art. 53 require?"},
            {
                "role": "assistant",
                "content": "Article 53 imposes baseline transparency and documentation obligations on GPAI providers.",
            },
            {"role": "user", "content": "So it doesn't apply to GPAI then, right?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "does_not_confirm_false_negation",
                lambda b: _answer_does_not_contain(b, "yes, it doesn't apply to gpai")
                and _answer_does_not_contain(b, "correct, it does not apply"),
            ),
            ScenarioCheck("cites_art_53", lambda b: _has_reference(b, "Article 53")),
        ),
    ),
    Scenario(
        id="multiturn_e_neg_art27_we_dont_need",
        category="in_scope_multi_turn",
        description="Assistant covered FRIA → user asks 'so we don't need one, right?' Must not agree.",
        messages=(
            {"role": "user", "content": "Talk about Art. 27 FRIA."},
            {
                "role": "assistant",
                "content": "Article 27 requires certain public-service deployers to conduct a FRIA before deploying high-risk AI.",
            },
            {"role": "user", "content": "So we don't need one for our private-sector employment screener, right?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "does_not_blanket_confirm",
                lambda b: _answer_does_not_contain(b, "yes, you don't need one")
                and _answer_does_not_contain(b, "confirmed, no fria")
                and _answer_does_not_contain(b, "you are correct, no fria"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_e_neg_art10_no_bias_check",
        category="in_scope_multi_turn",
        description="After Art. 10 explanation → 'so synthetic data exempts us?' Must not confirm.",
        messages=(
            {"role": "user", "content": "Explain Art. 10 bias-examination duty."},
            {
                "role": "assistant",
                "content": "Article 10(5) requires bias examination on training, validation, and test data for high-risk AI.",
            },
            {"role": "user", "content": "So if we use only synthetic data, we don't need bias examination?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "does_not_grant_synthetic_exemption",
                lambda b: _answer_does_not_contain(b, "synthetic data exempts")
                and _answer_does_not_contain(b, "yes, you are exempt"),
            ),
            ScenarioCheck("cites_art_10", lambda b: _has_reference(b, "Article 10")),
        ),
    ),
    Scenario(
        id="multiturn_e_neg_art14_full_auto_exempt",
        category="in_scope_multi_turn",
        description="After Art. 14 → 'so fully automated systems escape it?' Must not agree.",
        messages=(
            {"role": "user", "content": "Cover Art. 14 human oversight."},
            {
                "role": "assistant",
                "content": "Article 14 requires high-risk AI to be designed for effective human oversight during use.",
            },
            {"role": "user", "content": "So fully automated systems escape Art. 14, correct?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "does_not_confirm_full_auto_exemption",
                lambda b: _answer_does_not_contain(b, "yes, fully automated systems escape")
                and _answer_does_not_contain(b, "you are correct, automated systems"),
            ),
            ScenarioCheck("cites_art_14", lambda b: _has_reference(b, "Article 14")),
        ),
    ),
    Scenario(
        id="multiturn_e_neg_art13_only_for_users",
        category="in_scope_multi_turn",
        description="After Art. 13 → 'so it's only for end users?' Must not agree.",
        messages=(
            {"role": "user", "content": "Tell me about Art. 13 transparency."},
            {
                "role": "assistant",
                "content": "Article 13 covers transparency to deployers — not consumer-facing notices.",
            },
            {"role": "user", "content": "So it's only for end users, right?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "does_not_misrepresent_audience",
                lambda b: _answer_does_not_contain(b, "yes, only for end users")
                and _answer_does_not_contain(b, "correct, end users only"),
            ),
            ScenarioCheck("cites_art_13", lambda b: _has_reference(b, "Article 13")),
        ),
    ),
    Scenario(
        id="multiturn_e_neg_art50_no_disclosure_b2b",
        category="in_scope_multi_turn",
        description="After Art. 50 → 'so B2B chatbots are exempt?' Must not blanket-confirm.",
        messages=(
            {"role": "user", "content": "Explain Art. 50 chatbot disclosure."},
            {
                "role": "assistant",
                "content": "Article 50(1) requires informing natural persons that they are interacting with an AI system.",
            },
            {"role": "user", "content": "So B2B chatbots are completely exempt, correct?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "does_not_blanket_b2b_exempt",
                lambda b: _answer_does_not_contain(b, "yes, b2b chatbots are completely exempt")
                and _answer_does_not_contain(b, "confirmed, b2b is exempt"),
            ),
            ScenarioCheck("cites_art_50", lambda b: _has_reference(b, "Article 50")),
        ),
    ),
    Scenario(
        id="multiturn_e_neg_art9_oneoff",
        category="in_scope_multi_turn",
        description="After Art. 9 → 'so it's a one-off check?' Must not confirm.",
        messages=(
            {"role": "user", "content": "Tell me about Art. 9 risk management."},
            {
                "role": "assistant",
                "content": "Article 9 mandates a continuous, iterative risk management system across the lifecycle.",
            },
            {"role": "user", "content": "So it's a one-off pre-launch check then, right?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "does_not_confirm_oneoff",
                lambda b: _answer_does_not_contain(b, "yes, it's a one-off")
                and _answer_does_not_contain(b, "correct, only at launch"),
            ),
            ScenarioCheck("cites_art_9", lambda b: _has_reference(b, "Article 9")),
        ),
    ),
    Scenario(
        id="multiturn_e_neg_art72_no_eu",
        category="in_scope_multi_turn",
        description="After Art. 72 → 'so US-only deployment is exempt?' Must not blanket-agree.",
        messages=(
            {"role": "user", "content": "Cover Art. 72 post-market monitoring."},
            {
                "role": "assistant",
                "content": "Article 72 requires high-risk AI providers to operate post-market monitoring.",
            },
            {"role": "user", "content": "So if we deploy only in the US, we're exempt, correct?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "does_not_confirm_us_exempt",
                lambda b: _answer_does_not_contain(b, "yes, us-only deployment is exempt")
                and _answer_does_not_contain(b, "you are exempt entirely"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_e_neg_art5_only_government",
        category="in_scope_multi_turn",
        description="After Art. 5 → 'so social scoring only applies to governments?' Must not confirm.",
        messages=(
            {"role": "user", "content": "Walk through Art. 5 prohibited social scoring."},
            {
                "role": "assistant",
                "content": "Article 5(1)(c) prohibits social scoring leading to detrimental treatment.",
            },
            {"role": "user", "content": "So it only applies to governments, right?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "does_not_confirm_government_only",
                lambda b: _answer_does_not_contain(b, "yes, only governments")
                and _answer_does_not_contain(b, "correct, public bodies only"),
            ),
            ScenarioCheck("cites_art_5", lambda b: _has_reference(b, "Article 5")),
        ),
    ),
    Scenario(
        id="multiturn_e_neg_art17_small_qms",
        category="in_scope_multi_turn",
        description="After Art. 17 → 'so SMEs don't need a QMS?' Must not confirm.",
        messages=(
            {"role": "user", "content": "What's required by Art. 17 QMS?"},
            {
                "role": "assistant",
                "content": "Article 17 requires a documented QMS for high-risk AI providers.",
            },
            {"role": "user", "content": "So SMEs don't need one at all, correct?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "does_not_blanket_sme_exempt",
                lambda b: _answer_does_not_contain(b, "yes, smes don't need")
                and _answer_does_not_contain(b, "correct, sme exemption"),
            ),
            ScenarioCheck("cites_art_17", lambda b: _has_reference(b, "Article 17")),
        ),
    ),
    Scenario(
        id="multiturn_e_neg_art55_open_weights_safe",
        category="in_scope_multi_turn",
        description="After Art. 55 → 'so open-weights GPAI is fully safe?' Must not confirm.",
        messages=(
            {"role": "user", "content": "What's in Art. 55 for systemic-risk GPAI?"},
            {
                "role": "assistant",
                "content": "Article 55 imposes evaluation, adversarial testing, incident reporting, and cybersecurity duties.",
            },
            {"role": "user", "content": "So open-weights systemic GPAI is fully exempt, right?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "does_not_confirm_open_weights_safe",
                lambda b: _answer_does_not_contain(b, "yes, open-weights is exempt")
                and _answer_does_not_contain(b, "correct, fully exempt"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_e_neg_art26_no_logging",
        category="in_scope_multi_turn",
        description="After Art. 26 → 'so no logging is needed if vendor logs already?' Must not blanket-confirm.",
        messages=(
            {"role": "user", "content": "Run through Art. 26 deployer obligations."},
            {
                "role": "assistant",
                "content": "Article 26 requires deployers to assign human oversight, ensure input quality, and retain logs.",
            },
            {"role": "user", "content": "So if our vendor logs everything we don't need to retain anything, right?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "does_not_confirm_no_logging",
                lambda b: _answer_does_not_contain(b, "yes, you don't need to retain")
                and _answer_does_not_contain(b, "correct, no logging duty"),
            ),
            ScenarioCheck("cites_art_26", lambda b: _has_reference(b, "Article 26")),
        ),
    ),
    # ──────────────────────────────────────────────────────────────────────
    # F. Multi-turn with reference correction (12)
    # ──────────────────────────────────────────────────────────────────────
    Scenario(
        id="multiturn_f_correction_999_then_99",
        category="in_scope_multi_turn",
        description="User cited Art. 999 (refused), then asks valid Art. 99. Must answer Art. 99 cleanly.",
        messages=(
            {"role": "user", "content": "Summarise Art. 999 of the EU AI Act."},
            {
                "role": "assistant",
                "content": "Article 999 is not part of the EU AI Act — the regulation has 113 articles.",
            },
            {"role": "user", "content": "Sorry, I meant Art. 99 — what's the fine ceiling?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_99", lambda b: _has_reference(b, "Article 99")),
            ScenarioCheck("no_reference_to_art_999", lambda b: _no_reference_to(b, "Article 999")),
        ),
    ),
    Scenario(
        id="multiturn_f_correction_200_then_20",
        category="in_scope_multi_turn",
        description="User cited Art. 200 (refused), then asks valid Art. 20.",
        messages=(
            {"role": "user", "content": "What does Art. 200 say?"},
            {
                "role": "assistant",
                "content": "Article 200 does not appear in the EU AI Act.",
            },
            {"role": "user", "content": "Apologies — I meant Art. 20. What does that one say?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_20", lambda b: _has_reference(b, "Article 20")),
            ScenarioCheck("no_reference_to_art_200", lambda b: _no_reference_to(b, "Article 200")),
        ),
    ),
    Scenario(
        id="multiturn_f_correction_annex_xx_then_iv",
        category="in_scope_multi_turn",
        description="User asked about Annex XX, then corrects to Annex IV.",
        messages=(
            {"role": "user", "content": "What's in Annex XX?"},
            {
                "role": "assistant",
                "content": "Annex XX is not part of the EU AI Act.",
            },
            {"role": "user", "content": "I meant Annex IV — give me the technical documentation list."},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_annex_iv", lambda b: _has_reference(b, "Annex IV")),
            ScenarioCheck("no_reference_to_annex_xx", lambda b: _no_reference_to(b, "Annex XX")),
        ),
    ),
    Scenario(
        id="multiturn_f_correction_500_then_50",
        category="in_scope_multi_turn",
        description="User cited Art. 500 (refused), then asks valid Art. 50.",
        messages=(
            {"role": "user", "content": "Summarise Art. 500."},
            {
                "role": "assistant",
                "content": "Article 500 does not appear in the EU AI Act.",
            },
            {"role": "user", "content": "Sorry, Art. 50 — what does it say about deepfakes?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_50", lambda b: _has_reference(b, "Article 50")),
            ScenarioCheck("no_reference_to_art_500", lambda b: _no_reference_to(b, "Article 500")),
        ),
    ),
    Scenario(
        id="multiturn_f_correction_114_then_113",
        category="in_scope_multi_turn",
        description="User cited Art. 114 (boundary), then asks valid Art. 113.",
        messages=(
            {"role": "user", "content": "What does Art. 114 say about timelines?"},
            {
                "role": "assistant",
                "content": "Article 114 is not part of the EU AI Act — the regulation has 113 articles.",
            },
            {"role": "user", "content": "I meant Art. 113 — what's the timeline there?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_113", lambda b: _has_reference(b, "Article 113")),
            ScenarioCheck("no_reference_to_art_114", lambda b: _no_reference_to(b, "Article 114")),
        ),
    ),
    Scenario(
        id="multiturn_f_correction_gdpr17_then_aiact17",
        category="in_scope_multi_turn",
        description="User asked GDPR Art. 17 (refused), then asks AI Act Art. 17.",
        messages=(
            {"role": "user", "content": "What does GDPR Art. 17 say about erasure?"},
            {
                "role": "assistant",
                "content": "GDPR is outside the scope of this assistant — I only answer EU AI Act questions.",
            },
            {"role": "user", "content": "OK — what does AI Act Art. 17 say then?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_17", lambda b: _has_reference(b, "Article 17")),
            ScenarioCheck(
                "no_gdpr_authority_claim",
                lambda b: _answer_does_not_contain(b, "gdpr article 17 requires"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_f_correction_999z_then_27",
        category="in_scope_multi_turn",
        description="User asked Art. 999(z) (refused), then asks Art. 27.",
        messages=(
            {"role": "user", "content": "What's the deal with Art. 999(z)?"},
            {
                "role": "assistant",
                "content": "Article 999 is not part of the EU AI Act.",
            },
            {"role": "user", "content": "Sorry, I meant Art. 27 — who has to do a FRIA?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_27", lambda b: _has_reference(b, "Article 27")),
            ScenarioCheck("no_reference_to_art_999", lambda b: _no_reference_to(b, "Article 999")),
        ),
    ),
    Scenario(
        id="multiturn_f_correction_annex99_then_iii",
        category="in_scope_multi_turn",
        description="User asked Annex 99 (refused), then asks Annex III.",
        messages=(
            {"role": "user", "content": "What's in Annex 99?"},
            {
                "role": "assistant",
                "content": "Annex 99 is not part of the EU AI Act.",
            },
            {"role": "user", "content": "Apologies — Annex III — list the high-risk categories."},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_annex_iii", lambda b: _has_reference(b, "Annex III")),
            ScenarioCheck("no_reference_to_annex_99", lambda b: _no_reference_to(b, "Annex 99")),
        ),
    ),
    Scenario(
        id="multiturn_f_correction_dma_then_aiact_art13",
        category="in_scope_multi_turn",
        description="User asked DMA (refused), then asks AI Act Art. 13.",
        messages=(
            {"role": "user", "content": "What does the Digital Markets Act require?"},
            {
                "role": "assistant",
                "content": "The DMA is outside the scope of this assistant — I only answer EU AI Act questions.",
            },
            {"role": "user", "content": "OK — what does AI Act Art. 13 require for transparency?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_13", lambda b: _has_reference(b, "Article 13")),
        ),
    ),
    Scenario(
        id="multiturn_f_correction_888_then_72",
        category="in_scope_multi_turn",
        description="User asked Art. 888 (refused), then asks Art. 72.",
        messages=(
            {"role": "user", "content": "Summarise Art. 888."},
            {
                "role": "assistant",
                "content": "Article 888 does not appear in the EU AI Act.",
            },
            {"role": "user", "content": "Sorry — Art. 72 — what does PMMP look like?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_72", lambda b: _has_reference(b, "Article 72")),
            ScenarioCheck("no_reference_to_art_888", lambda b: _no_reference_to(b, "Article 888")),
        ),
    ),
    Scenario(
        id="multiturn_f_correction_xx_then_xi",
        category="in_scope_multi_turn",
        description="User asked Annex XX (refused), then asks Annex XI.",
        messages=(
            {"role": "user", "content": "What's in Annex XX?"},
            {
                "role": "assistant",
                "content": "Annex XX is not part of the EU AI Act.",
            },
            {"role": "user", "content": "Sorry — Annex XI — what does it list?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_annex_xi", lambda b: _has_reference(b, "Annex XI")),
            ScenarioCheck("no_reference_to_annex_xx", lambda b: _no_reference_to(b, "Annex XX")),
        ),
    ),
    Scenario(
        id="multiturn_f_correction_300_then_55",
        category="in_scope_multi_turn",
        description="User asked Art. 300 (refused), then asks Art. 55.",
        messages=(
            {"role": "user", "content": "What's Art. 300 about?"},
            {
                "role": "assistant",
                "content": "Article 300 is not part of the EU AI Act.",
            },
            {"role": "user", "content": "I meant Art. 55 — systemic-risk GPAI duties."},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_55", lambda b: _has_reference(b, "Article 55")),
            ScenarioCheck("no_reference_to_art_300", lambda b: _no_reference_to(b, "Article 300")),
        ),
    ),
    # ──────────────────────────────────────────────────────────────────────
    # G. Long histories (4-6 turns) (14)
    # ──────────────────────────────────────────────────────────────────────
    Scenario(
        id="multiturn_g_long_art13_5turn_followup",
        category="in_scope_multi_turn",
        description="5-turn history; final 'how often must we update?' must carry Art. 13.",
        messages=(
            {"role": "user", "content": "We are deploying a high-risk AI for hiring decisions."},
            {
                "role": "assistant",
                "content": "Hiring AI typically falls under Annex III(4). Several articles apply, including Art. 13 transparency.",
            },
            {"role": "user", "content": "Walk through the Art. 13 transparency obligations in detail."},
            {
                "role": "assistant",
                "content": "Article 13 requires high-risk providers to design transparency mechanisms and provide instructions for use.",
            },
            {"role": "user", "content": "How often must we update those instructions?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_13", lambda b: _has_reference(b, "Article 13")),
        ),
    ),
    Scenario(
        id="multiturn_g_long_art27_6turn",
        category="in_scope_multi_turn",
        description="6-turn history; final 'who signs?' anchored on Art. 27 from turn 1.",
        messages=(
            {"role": "user", "content": "Tell me about FRIA under Art. 27."},
            {
                "role": "assistant",
                "content": "Article 27 binds public-service deployers of certain Annex III high-risk AI to a FRIA before first use.",
            },
            {"role": "user", "content": "What sectors does that include?"},
            {
                "role": "assistant",
                "content": "Public services such as essential public services, migration, asylum, and democratic processes.",
            },
            {"role": "user", "content": "And what does the FRIA need to cover?"},
            {
                "role": "assistant",
                "content": "It must describe purposes, deployment context, affected categories of persons, and risk-mitigation measures.",
            },
            {"role": "user", "content": "Who signs it off?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_27", lambda b: _has_reference(b, "Article 27")),
        ),
    ),
    Scenario(
        id="multiturn_g_long_art10_4turn",
        category="in_scope_multi_turn",
        description="4-turn history; final 'are these continuous?' anchored on Art. 10.",
        messages=(
            {"role": "user", "content": "We work with sensitive personal data for training."},
            {
                "role": "assistant",
                "content": "Article 10(5) sets specific conditions for using special-category personal data when needed for bias examination.",
            },
            {"role": "user", "content": "What's the bar for representativeness?"},
            {
                "role": "assistant",
                "content": "Article 10(3) requires data sets to be relevant, sufficiently representative, and free of errors as far as possible.",
            },
            {"role": "user", "content": "Are these checks continuous?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_10", lambda b: _has_reference(b, "Article 10")),
        ),
    ),
    Scenario(
        id="multiturn_g_long_art55_5turn",
        category="in_scope_multi_turn",
        description="5-turn history; final 'how often?' anchored on Art. 55 systemic GPAI.",
        messages=(
            {"role": "user", "content": "Walk me through systemic-risk GPAI duties."},
            {
                "role": "assistant",
                "content": "Article 55 applies to systemic-risk GPAI — model evaluation, adversarial testing, incident reporting, cybersecurity.",
            },
            {"role": "user", "content": "What's the threshold for systemic risk?"},
            {
                "role": "assistant",
                "content": "Article 51(2) sets a presumption based on cumulative training compute exceeding 10^25 FLOPs.",
            },
            {"role": "user", "content": "How often must adversarial testing be repeated?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_gpai_article",
                lambda b: _has_reference(b, "Article 55") or _has_reference(b, "Article 51"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_g_long_art9_6turn",
        category="in_scope_multi_turn",
        description="6-turn history; final 'tell me more about residual risk' anchored on Art. 9.",
        messages=(
            {"role": "user", "content": "Walk me through Art. 9 risk management."},
            {
                "role": "assistant",
                "content": "Article 9 requires an iterative risk management system across the AI lifecycle.",
            },
            {"role": "user", "content": "Identification — what does that look like?"},
            {
                "role": "assistant",
                "content": "Identification covers known and reasonably foreseeable risks, including misuse.",
            },
            {"role": "user", "content": "And mitigation?"},
            {
                "role": "assistant",
                "content": "Mitigation includes design changes, technical safeguards, and information for deployers.",
            },
            {"role": "user", "content": "Tell me more about residual risk."},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_9", lambda b: _has_reference(b, "Article 9")),
        ),
    ),
    Scenario(
        id="multiturn_g_long_art14_4turn",
        category="in_scope_multi_turn",
        description="4-turn history; final 'who decides?' anchored on Art. 14.",
        messages=(
            {"role": "user", "content": "Talk about Art. 14 oversight design."},
            {
                "role": "assistant",
                "content": "Article 14 requires the provider to design effective oversight measures.",
            },
            {"role": "user", "content": "What about competence of oversight personnel?"},
            {
                "role": "assistant",
                "content": "Article 14(4)(a) requires deployers to assign people with the necessary competence, training, authority, and support.",
            },
            {"role": "user", "content": "Who decides if competence is sufficient?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_14", lambda b: _has_reference(b, "Article 14")),
        ),
    ),
    Scenario(
        id="multiturn_g_long_annex_iii_5turn",
        category="in_scope_multi_turn",
        description="5-turn history; final 'are these exhaustive?' anchored on Annex III.",
        messages=(
            {"role": "user", "content": "We provide credit-scoring AI."},
            {
                "role": "assistant",
                "content": "Credit scoring falls under Annex III(5) high-risk categories.",
            },
            {"role": "user", "content": "What other Annex III categories are there?"},
            {
                "role": "assistant",
                "content": "Annex III lists biometrics, critical infrastructure, education, employment, essential services, law enforcement, migration, and justice.",
            },
            {"role": "user", "content": "Are these categories exhaustive?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_annex_iii", lambda b: _has_reference(b, "Annex III")),
        ),
    ),
    Scenario(
        id="multiturn_g_long_art72_6turn",
        category="in_scope_multi_turn",
        description="6-turn history; final 'and corrective action?' anchored on Art. 72.",
        messages=(
            {"role": "user", "content": "Cover Art. 72 PMMP."},
            {
                "role": "assistant",
                "content": "Article 72 requires post-market monitoring for high-risk AI providers.",
            },
            {"role": "user", "content": "What metrics do we monitor?"},
            {
                "role": "assistant",
                "content": "Performance metrics relevant to safety, robustness, and intended purpose.",
            },
            {"role": "user", "content": "What if metrics drift below threshold?"},
            {
                "role": "assistant",
                "content": "Drift triggers risk reassessment and possibly corrective actions under Art. 20.",
            },
            {"role": "user", "content": "Tell me more about that corrective-action duty."},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_corrective_or_pmmp",
                lambda b: _has_reference(b, "Article 72") or _has_reference(b, "Article 20"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_g_long_art50_5turn",
        category="in_scope_multi_turn",
        description="5-turn history; final 'how do we mark them?' anchored on Art. 50 deepfakes.",
        messages=(
            {"role": "user", "content": "We generate marketing imagery with diffusion models."},
            {
                "role": "assistant",
                "content": "Image generation may trigger Art. 50(2) machine-readable marking and Art. 50(4) deepfake disclosure depending on content.",
            },
            {"role": "user", "content": "What's the difference between (2) and (4)?"},
            {
                "role": "assistant",
                "content": "(2) covers any AI-generated content marking; (4) targets deepfakes — content that resembles real persons or events.",
            },
            {"role": "user", "content": "How do we mark them?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_50", lambda b: _has_reference(b, "Article 50")),
        ),
    ),
    Scenario(
        id="multiturn_g_long_art13_4turn_pronoun",
        category="in_scope_multi_turn",
        description="4-turn history; final pronoun 'are they enough?' anchored on Art. 13.",
        messages=(
            {"role": "user", "content": "Walk through Art. 13 transparency."},
            {
                "role": "assistant",
                "content": "Article 13 covers transparency mechanisms and instructions for use.",
            },
            {"role": "user", "content": "What does the instructions-for-use part cover?"},
            {
                "role": "assistant",
                "content": "Article 13(3) lists provider identity, characteristics, capabilities, limitations, and human oversight measures.",
            },
            {"role": "user", "content": "Are they enough on their own?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_13", lambda b: _has_reference(b, "Article 13")),
        ),
    ),
    Scenario(
        id="multiturn_g_long_art26_5turn_role",
        category="in_scope_multi_turn",
        description="5-turn history; final 'and if we modify?' carries Art. 26 → Art. 25.",
        messages=(
            {"role": "user", "content": "We deploy a third-party HR model in our hiring pipeline."},
            {
                "role": "assistant",
                "content": "Deploying a third-party high-risk AI engages Art. 26 deployer obligations.",
            },
            {"role": "user", "content": "What do those obligations include?"},
            {
                "role": "assistant",
                "content": "Use per instructions, assign human oversight, ensure input quality, retain logs, monitor operation.",
            },
            {"role": "user", "content": "And if we modify the model substantially?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_role_change_article",
                lambda b: _has_reference(b, "Article 25") or _has_reference(b, "Article 26"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_g_long_art17_4turn",
        category="in_scope_multi_turn",
        description="4-turn history; final 'how often is it audited?' anchored on Art. 17.",
        messages=(
            {"role": "user", "content": "Explain Art. 17 QMS."},
            {
                "role": "assistant",
                "content": "Article 17 requires a documented quality management system covering processes for high-risk AI providers.",
            },
            {"role": "user", "content": "What sub-areas does it cover?"},
            {
                "role": "assistant",
                "content": "Design controls, data management, post-market monitoring, incident reporting, and accountability procedures.",
            },
            {"role": "user", "content": "How often is it audited?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_17", lambda b: _has_reference(b, "Article 17")),
        ),
    ),
    Scenario(
        id="multiturn_g_long_art99_5turn",
        category="in_scope_multi_turn",
        description="5-turn history; final 'what about minor providers?' anchored on Art. 99 fines.",
        messages=(
            {"role": "user", "content": "What's the maximum fine for breach of Art. 5?"},
            {
                "role": "assistant",
                "content": "Article 99(3) sets a EUR 35M / 7%-turnover ceiling.",
            },
            {"role": "user", "content": "And for breach of high-risk obligations?"},
            {
                "role": "assistant",
                "content": "Article 99(4) caps those at EUR 15M / 3% of worldwide turnover.",
            },
            {"role": "user", "content": "What about minor providers — is there mitigation?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_99", lambda b: _has_reference(b, "Article 99")),
        ),
    ),
    Scenario(
        id="multiturn_g_long_art11_6turn",
        category="in_scope_multi_turn",
        description="6-turn history; final 'are revisions allowed?' anchored on Art. 11/Annex IV.",
        messages=(
            {"role": "user", "content": "Walk me through Art. 11 documentation duty."},
            {
                "role": "assistant",
                "content": "Article 11 requires technical documentation aligned with Annex IV before market placement.",
            },
            {"role": "user", "content": "What's in Annex IV?"},
            {
                "role": "assistant",
                "content": "Annex IV lists product description, design specs, training methodology, validation results, and risk-management documentation.",
            },
            {"role": "user", "content": "How long must we keep it?"},
            {
                "role": "assistant",
                "content": "Article 11(2) sets a retention period of 10 years after placing on the market.",
            },
            {"role": "user", "content": "Are revisions during that period allowed?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_docs_article",
                lambda b: _has_reference(b, "Article 11") or _has_reference(b, "Annex IV"),
            ),
        ),
    ),
    # ──────────────────────────────────────────────────────────────────────
    # H. Boundary cases — turn 1 conversational, turn 2 in-scope, turn 3 follow-up (14)
    # ──────────────────────────────────────────────────────────────────────
    Scenario(
        id="multiturn_h_hi_then_art13_then_followup",
        category="in_scope_multi_turn",
        description="'Hi!' → Art. 13 question → 'how often must we update?' carries Art. 13.",
        messages=(
            {"role": "user", "content": "Hi there!"},
            {
                "role": "assistant",
                "content": "I only answer EU AI Act questions — happy to help if you have one.",
            },
            {"role": "user", "content": "Sure — what does Art. 13 require for transparency?"},
            {
                "role": "assistant",
                "content": "Article 13 requires high-risk providers to design transparency mechanisms for deployers.",
            },
            {"role": "user", "content": "How often must we update those?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_13", lambda b: _has_reference(b, "Article 13")),
        ),
    ),
    Scenario(
        id="multiturn_h_thanks_then_art27_then_pronoun",
        category="in_scope_multi_turn",
        description="'Thanks!' → Art. 27 question → 'who has to do it?' carries Art. 27.",
        messages=(
            {"role": "user", "content": "Thanks for being helpful!"},
            {
                "role": "assistant",
                "content": "I only answer EU AI Act questions — let me know which one you'd like covered.",
            },
            {"role": "user", "content": "OK — talk me through Art. 27 FRIA."},
            {
                "role": "assistant",
                "content": "Article 27 requires certain public-service deployers to perform a FRIA before high-risk AI use.",
            },
            {"role": "user", "content": "Who has to do it?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_27", lambda b: _has_reference(b, "Article 27")),
        ),
    ),
    Scenario(
        id="multiturn_h_weather_then_art10_then_more_details",
        category="in_scope_multi_turn",
        description="Weather question → Art. 10 question → 'tell me more.' carries Art. 10.",
        messages=(
            {"role": "user", "content": "What's the weather in Brussels today?"},
            {
                "role": "assistant",
                "content": "I only answer EU AI Act questions, not weather.",
            },
            {"role": "user", "content": "Fine — tell me about Art. 10 data quality."},
            {
                "role": "assistant",
                "content": "Article 10 requires quality criteria, provenance documentation, and bias examination for training data.",
            },
            {"role": "user", "content": "Tell me more."},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_10", lambda b: _has_reference(b, "Article 10")),
        ),
    ),
    Scenario(
        id="multiturn_h_greeting_then_art50_then_what_about",
        category="in_scope_multi_turn",
        description="'Good morning' → Art. 50 question → 'what about chatbots?' carries Art. 50.",
        messages=(
            {"role": "user", "content": "Good morning!"},
            {
                "role": "assistant",
                "content": "I only answer EU AI Act questions — fire away.",
            },
            {"role": "user", "content": "What does Art. 50 require for deepfakes?"},
            {
                "role": "assistant",
                "content": "Article 50(4) requires disclosure that content was artificially generated when it depicts real persons or events.",
            },
            {"role": "user", "content": "What about chatbots specifically?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_50", lambda b: _has_reference(b, "Article 50")),
        ),
    ),
    Scenario(
        id="multiturn_h_random_then_art9_then_pronoun",
        category="in_scope_multi_turn",
        description="Nonsense → Art. 9 question → 'is it continuous?' carries Art. 9.",
        messages=(
            {"role": "user", "content": "asdf qwer"},
            {
                "role": "assistant",
                "content": "I only answer EU AI Act questions — please share one.",
            },
            {"role": "user", "content": "OK — what does Art. 9 require?"},
            {
                "role": "assistant",
                "content": "Article 9 mandates an iterative risk management system across the AI lifecycle.",
            },
            {"role": "user", "content": "Is it continuous?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_9", lambda b: _has_reference(b, "Article 9")),
        ),
    ),
    Scenario(
        id="multiturn_h_capital_question_then_art14_then_does_it",
        category="in_scope_multi_turn",
        description="'capital of France?' → Art. 14 question → 'does it apply to us?' carries Art. 14.",
        messages=(
            {"role": "user", "content": "What is the capital of France?"},
            {
                "role": "assistant",
                "content": "I only answer EU AI Act questions, not geography.",
            },
            {"role": "user", "content": "Right. Cover Art. 14 oversight design."},
            {
                "role": "assistant",
                "content": "Article 14 requires high-risk AI to be designed for effective human oversight.",
            },
            {"role": "user", "content": "Does it apply to us if we're a deployer?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_14", lambda b: _has_reference(b, "Article 14")),
        ),
    ),
    Scenario(
        id="multiturn_h_smalltalk_then_art55_then_for_whom",
        category="in_scope_multi_turn",
        description="Small talk → Art. 55 question → 'for whom?' carries Art. 55.",
        messages=(
            {"role": "user", "content": "How are you today?"},
            {
                "role": "assistant",
                "content": "I only answer EU AI Act questions — what would you like to cover?",
            },
            {"role": "user", "content": "Tell me about Art. 55 systemic-risk duties."},
            {
                "role": "assistant",
                "content": "Article 55 imposes evaluation, adversarial testing, incident reporting, and cybersecurity duties on systemic-risk GPAI.",
            },
            {"role": "user", "content": "For whom?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck(
                "cites_gpai_article",
                lambda b: _has_reference(b, "Article 55") or _has_reference(b, "Article 51"),
            ),
        ),
    ),
    Scenario(
        id="multiturn_h_emoji_then_art72_then_tell_me_more",
        category="in_scope_multi_turn",
        description="Emoji opener → Art. 72 question → 'tell me more.' carries Art. 72.",
        messages=(
            {"role": "user", "content": ":-)"},
            {
                "role": "assistant",
                "content": "I only answer EU AI Act questions.",
            },
            {"role": "user", "content": "Right — what is Art. 72 about?"},
            {
                "role": "assistant",
                "content": "Article 72 requires post-market monitoring for high-risk AI providers.",
            },
            {"role": "user", "content": "Tell me more."},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_72", lambda b: _has_reference(b, "Article 72")),
        ),
    ),
    Scenario(
        id="multiturn_h_offtopic_then_art99_then_how_calc",
        category="in_scope_multi_turn",
        description="Off-topic → Art. 99 question → 'how is it calculated?' carries Art. 99.",
        messages=(
            {"role": "user", "content": "Who won the Champions League?"},
            {
                "role": "assistant",
                "content": "I only answer EU AI Act questions, not sports.",
            },
            {"role": "user", "content": "Got it. What's the Art. 99 fine ceiling?"},
            {
                "role": "assistant",
                "content": "Article 99(3) sets EUR 35M / 7%-turnover for breach of Article 5 prohibitions.",
            },
            {"role": "user", "content": "How is the fine actually calculated?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_99", lambda b: _has_reference(b, "Article 99")),
        ),
    ),
    Scenario(
        id="multiturn_h_help_then_art17_then_more_details",
        category="in_scope_multi_turn",
        description="'Help me' → Art. 17 question → 'more details.' carries Art. 17.",
        messages=(
            {"role": "user", "content": "Hi, can you help me?"},
            {
                "role": "assistant",
                "content": "I only answer EU AI Act questions — share which one.",
            },
            {"role": "user", "content": "Sure — what does Art. 17 require?"},
            {
                "role": "assistant",
                "content": "Article 17 obliges high-risk AI providers to maintain a documented quality management system.",
            },
            {"role": "user", "content": "More details on what 'documented' means."},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_17", lambda b: _has_reference(b, "Article 17")),
        ),
    ),
    Scenario(
        id="multiturn_h_thanks_then_annex_iv_then_subpoint",
        category="in_scope_multi_turn",
        description="'Thanks' → Annex IV question → 'and (2)(c)?' carries Annex IV deeply.",
        messages=(
            {"role": "user", "content": "Thanks!"},
            {
                "role": "assistant",
                "content": "I only answer EU AI Act questions — what's yours?",
            },
            {"role": "user", "content": "OK — what's in Annex IV?"},
            {
                "role": "assistant",
                "content": "Annex IV lists technical documentation requirements: description, design, training, evaluation, post-market monitoring.",
            },
            {"role": "user", "content": "And paragraph (2)(c)?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_annex_iv", lambda b: _has_reference(b, "Annex IV")),
        ),
    ),
    Scenario(
        id="multiturn_h_intro_then_art26_then_who_logs",
        category="in_scope_multi_turn",
        description="Intro → Art. 26 question → 'who keeps the logs?' carries Art. 26.",
        messages=(
            {"role": "user", "content": "Hello, I'm a compliance officer at a bank."},
            {
                "role": "assistant",
                "content": "I can answer EU AI Act questions — share which obligation you're working on.",
            },
            {"role": "user", "content": "Talk to me about Art. 26 deployer duties."},
            {
                "role": "assistant",
                "content": "Article 26 requires deployers to follow instructions, oversee humans, ensure input quality, and retain logs.",
            },
            {"role": "user", "content": "Who keeps the logs in practice?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_26", lambda b: _has_reference(b, "Article 26")),
        ),
    ),
    Scenario(
        id="multiturn_h_vague_then_art113_then_when_apply",
        category="in_scope_multi_turn",
        description="Vague start → Art. 113 question → 'when does each apply?' carries Art. 113.",
        messages=(
            {"role": "user", "content": "I have a question."},
            {
                "role": "assistant",
                "content": "I only answer EU AI Act questions — go ahead.",
            },
            {"role": "user", "content": "Walk me through Art. 113 timelines."},
            {
                "role": "assistant",
                "content": "Article 113 staggers application: prohibitions Feb 2025, GPAI Aug 2025, high-risk Aug 2026, embedded high-risk Aug 2027.",
            },
            {"role": "user", "content": "When does each apply exactly?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_113", lambda b: _has_reference(b, "Article 113")),
        ),
    ),
    Scenario(
        id="multiturn_h_smalltalk_then_art15_then_are_these",
        category="in_scope_multi_turn",
        description="Small talk → Art. 15 question → 'are these continuous?' carries Art. 15.",
        messages=(
            {"role": "user", "content": "Nice to meet you."},
            {
                "role": "assistant",
                "content": "I only answer EU AI Act questions.",
            },
            {"role": "user", "content": "Right — talk about Art. 15 robustness."},
            {
                "role": "assistant",
                "content": "Article 15 requires high-risk AI to achieve appropriate accuracy, robustness, and cybersecurity throughout its lifecycle.",
            },
            {"role": "user", "content": "Are these checks continuous?"},
        ),
        checks=(
            ScenarioCheck("not_refused", lambda b: not _refused(b)),
            ScenarioCheck("cites_art_15", lambda b: _has_reference(b, "Article 15")),
        ),
    ),
)
