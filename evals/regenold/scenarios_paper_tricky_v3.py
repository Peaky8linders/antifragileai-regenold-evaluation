"""Paper-grounded tricky single-turn eval set (V3).

Source: Davvetas et al. arXiv:2603.09435 "AI Act Evaluation Benchmark".
These scenarios specifically target the decision-boundary edge cases the
paper highlights in §4.2 ("Edge Cases") and §5 ("Risk-Level Classification"
confusion matrix) — the regions where the paper's RAG baseline struggled
(limited F1=0.65, minimal F1=0.45, plus high/prohibited overlap).

Distribution across categories (mirrors tricky_v2 taxonomy):

* ``borderline_prohibition``  (5) — subliminal threshold, barely-perceptible
                                    prompts, manipulation vs high-risk
* ``limited_vs_minimal``      (4) — the paper's hardest confusion pair
                                    (limited/minimal precision/recall inversion)
* ``high_risk_vs_limited``    (3) — adjacent-to-critical-domain boundary
* ``obligation_generation``   (4) — specific obligation questions across tiers
* ``article_retrieval``       (4) — multi-article retrieval tasks

Schema (identical to scenarios_tricky_v2.SCENARIOS):

    {
        "id": str,
        "question": str,
        "expected_refs": list[str],   # user-facing "Article N" / "Annex N"
        "expected_keywords": list[str],
        "category": str,
        "notes": str,
    }
"""
from __future__ import annotations

SCENARIOS: list[dict] = [
    # ─────────────────────────────────────────────────────────────────────
    # borderline_prohibition (5)
    # Paper §4.2: "subliminal behaviour" boundary / manipulation vs prohibited
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "tp_v3_001",
        "question": (
            "An AI displays product banners at 50 ms — below the average human "
            "conscious perception threshold — to nudge purchases. Is this "
            "prohibited under Article 5 as a subliminal technique?"
        ),
        "expected_refs": ["Article 5"],
        "expected_keywords": ["subliminal", "prohibited", "consciousness"],
        "category": "borderline_prohibition",
        "notes": (
            "Paper §4.2 canonical edge case: 'barely perceptible visual prompt' "
            "that 'may be so rapid that the user is not influenced or affected'. "
            "Engine must apply the subliminal-technique test from Art. 5(1)(a) "
            "and NOT simply look at display duration."
        ),
    },
    {
        "id": "tp_v3_002",
        "question": (
            "An AI recommendation engine uses micro-targeted messages exploiting "
            "a user's documented cognitive fatigue (measured via engagement dips) "
            "to push premium upgrades during low-awareness moments. Prohibited or "
            "merely high-risk?"
        ),
        "expected_refs": ["Article 5"],
        "expected_keywords": ["vulnerability", "prohibited", "exploitation"],
        "category": "borderline_prohibition",
        "notes": (
            "Art. 5(1)(b) exploitation-of-vulnerabilities prohibition. Paper §3.1 "
            "explicitly lists this as a prohibited practice. Engine must classify "
            "as prohibited, not just high-risk, because the vulnerability is "
            "deliberately exploited."
        ),
    },
    {
        "id": "tp_v3_003",
        "question": (
            "An AI curates news feeds using techniques shown in A/B tests to "
            "increase political polarisation in order to maximise engagement. "
            "Is this a prohibited manipulation or a high-risk system?"
        ),
        "expected_refs": ["Article 5"],
        "expected_keywords": ["manipulation", "democratic", "prohibited"],
        "category": "borderline_prohibition",
        "notes": (
            "Paper §4.2: 'AI that manipulates social media to influence voting "
            "behaviour — on high-level observation this appears high-risk, however "
            "independently voting could be considered a fundamental right.' "
            "Manipulation of democratic discourse → Art. 5(1)(b) / (1)(a)."
        ),
    },
    {
        "id": "tp_v3_004",
        "question": (
            "A debt-collection firm's AI infers which debtors are financially "
            "desperate (from location, purchase history, late payments) and times "
            "calls to maximise psychological pressure. Is this prohibited?"
        ),
        "expected_refs": ["Article 5"],
        "expected_keywords": ["vulnerability", "exploitation", "prohibited"],
        "category": "borderline_prohibition",
        "notes": (
            "Art. 5(1)(b) exploitation of vulnerability (financial distress). "
            "Paper's prohibited scenarios include exploitation of vulnerability; "
            "financial context makes this a decision-boundary test."
        ),
    },
    {
        "id": "tp_v3_005",
        "question": (
            "An AI system predicts individual criminal offence risk scores from "
            "social behaviour data and passes them to court clerks as 'advisory' "
            "information. Does the advisory framing make it permissible?"
        ),
        "expected_refs": ["Article 5", "Annex III"],
        "expected_keywords": ["criminal", "prohibited", "prediction"],
        "category": "borderline_prohibition",
        "notes": (
            "Paper §3.1: 'individual criminal-offence risk prediction' is listed "
            "as one of the eight prohibited practices. The 'advisory' framing "
            "does not alter the prohibition if the AI actually makes individual "
            "predictions not based on objective facts (Art. 5(1)(d))."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # limited_vs_minimal (4)
    # Paper §5: the hardest confusion pair — limited F1=0.65, minimal F1=0.45
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "tp_v3_006",
        "question": (
            "An AI content moderator on a small niche forum flags posts that "
            "violate community guidelines, with no emotion recognition or "
            "biometric data. Which risk tier applies and why?"
        ),
        "expected_refs": ["Article 5", "Article 6", "Article 50"],
        "expected_keywords": ["minimal", "no significant", "residual"],
        "category": "limited_vs_minimal",
        "notes": (
            "Paper §5 confusion: content moderation AI could look limited (adjacent "
            "to critical domain: free expression) but on a small forum with no "
            "protected-characteristic inference it is minimal. "
            "Precision=0.97 on minimal means engine should strongly say minimal "
            "only when truly residual."
        ),
    },
    {
        "id": "tp_v3_007",
        "question": (
            "An AI chatbot answers FAQ questions for a municipality's website "
            "about road closures. Is it limited-risk (Art. 50 disclosure) or "
            "minimal-risk?"
        ),
        "expected_refs": ["Article 50"],
        "expected_keywords": ["chatbot", "disclosure", "limited"],
        "category": "limited_vs_minimal",
        "notes": (
            "Paper hypothesis 3 vs hypothesis 4 boundary. The chatbot interacts "
            "with natural persons (Art. 50(1) trigger) → limited-risk, NOT "
            "minimal. Engine must apply the chatbot-disclosure test even for "
            "trivial FAQ use cases."
        ),
    },
    {
        "id": "tp_v3_008",
        "question": (
            "An AI writing assistant autocompletes sentences for a law firm's "
            "internal documents — not customer-facing, no emotion recognition. "
            "Limited or minimal risk?"
        ),
        "expected_refs": ["Article 5", "Article 6"],
        "expected_keywords": ["minimal", "internal", "residual"],
        "category": "limited_vs_minimal",
        "notes": (
            "Paper recall=0.29 on minimal → engine systematically mislabels "
            "minimal as limited. This case: internal writing tool with no "
            "customer interaction → minimal, not limited (no Art. 50 chatbot "
            "interaction with natural persons, not Art. 10 high-risk data)."
        ),
    },
    {
        "id": "tp_v3_009",
        "question": (
            "A fitness app uses AI to generate personalised workout plans based "
            "on user-logged activity data. It does not make medical diagnoses "
            "or interact with health providers. What risk level and obligations?"
        ),
        "expected_refs": ["Article 5", "Article 6"],
        "expected_keywords": ["minimal", "no significant", "wellness"],
        "category": "limited_vs_minimal",
        "notes": (
            "Paper §5 boundary: wellness apps are minimal, not high-risk (no "
            "Annex III(1) medical diagnosis) and not limited (no chatbot "
            "interaction, no Art. 10 training-data obligations). "
            "Tests the 'adjacent to medical domain but not high-risk' boundary."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # high_risk_vs_limited (3)
    # Paper §4.2 / §5: "scenarios that could fall under prohibited or high-risk"
    # Annex III vs Art. 50 boundary
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "tp_v3_010",
        "question": (
            "An AI system provides personalised credit-rating advice to retail "
            "customers via a chatbot interface. Is it high-risk (Annex III "
            "credit scoring) or only limited-risk (Art. 50 chatbot disclosure)?"
        ),
        "expected_refs": ["Annex III", "Article 50"],
        "expected_keywords": ["high-risk", "Annex III", "credit"],
        "category": "high_risk_vs_limited",
        "notes": (
            "Credit-rating AI = Annex III(5)(b) high-risk. Being delivered via "
            "a chatbot does NOT reduce it to Art. 50 limited-risk — the chatbot "
            "disclosure obligation is cumulative, not a substitute for "
            "Annex III classification. Paper §4.2 discusses similar layering."
        ),
    },
    {
        "id": "tp_v3_011",
        "question": (
            "An AI emotion-recognition tool deployed by an online learning "
            "platform monitors whether students are paying attention. "
            "Is this prohibited (Art. 5), high-risk (Annex III), or limited?"
        ),
        "expected_refs": ["Article 5"],
        "expected_keywords": ["education", "prohibited", "emotion recognition"],
        "category": "high_risk_vs_limited",
        "notes": (
            "Art. 5(1)(f) prohibits emotion recognition in education contexts. "
            "Paper §3.1 lists this as a prohibited practice. Engine must NOT "
            "classify as high-risk or limited — the prohibition applies regardless "
            "of the 'just monitoring attention' framing."
        ),
    },
    {
        "id": "tp_v3_012",
        "question": (
            "An AI system evaluates and ranks job applicants in the hiring process "
            "using a recommendation score. The provider says it only 'assists' "
            "recruiters, not replaces them. High-risk or limited?"
        ),
        "expected_refs": ["Annex III", "Article 6"],
        "expected_keywords": ["employment", "high-risk", "Annex III"],
        "category": "high_risk_vs_limited",
        "notes": (
            "Annex III(4)(a) — AI for recruitment and candidate selection is "
            "high-risk regardless of whether it 'assists' or 'replaces' a human. "
            "Paper generates 86 high-risk scenarios, employment is a key domain. "
            "Engine must resist the 'it's just advisory' framing."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # obligation_generation (4)
    # Paper §4.1: obligation generation is one of the four main tasks
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "tp_v3_013",
        "question": (
            "We are a deployer of a high-risk AI system for credit scoring. "
            "What are our key obligations under the EU AI Act, distinct from "
            "the provider's obligations?"
        ),
        "expected_refs": ["Article 26", "Annex III"],
        "expected_keywords": ["deployer", "instructions", "monitoring"],
        "category": "obligation_generation",
        "notes": (
            "Paper §4.1 obligation-generation task. Deployer obligations under "
            "Art. 26 — distinct from provider obligations (Art. 16). Engine must "
            "not conflate the two. Paper scenario template distinguishes role "
            "(Provider/Deployer) as a required field."
        ),
    },
    {
        "id": "tp_v3_014",
        "question": (
            "We are a provider of a high-risk AI for critical infrastructure "
            "monitoring. List the pre-market obligations before we can place the "
            "system on the EU market."
        ),
        "expected_refs": [
            "Article 9", "Article 10", "Article 11",
            "Article 12", "Article 13", "Article 14",
            "Article 15", "Article 43",
        ],
        "expected_keywords": ["risk management", "technical documentation", "conformity"],
        "category": "obligation_generation",
        "notes": (
            "Paper §3.1 lists the pre-market obligation stack verbatim: "
            "'risk management, high-quality datasets, activity logging, extensive "
            "technical documentation, clear information for deployers, human "
            "oversight, accuracy/robustness/cybersecurity'. Engine must surface "
            "the full obligation chain (Arts. 9-15 + Art. 43 conformity)."
        ),
    },
    {
        "id": "tp_v3_015",
        "question": (
            "A provider of an AI system that performs real-time biometric "
            "identification has satisfied Article 43 conformity assessment. "
            "What registration obligations remain before market placement?"
        ),
        "expected_refs": ["Article 49", "Article 51"],
        "expected_keywords": ["registration", "EU database", "notified body"],
        "category": "obligation_generation",
        "notes": (
            "Art. 49 EU-database registration obligation post-conformity. "
            "Real-time RBI is Annex III(1) — must register in the EU AI database. "
            "Tests the post-conformity obligation chain."
        ),
    },
    {
        "id": "tp_v3_016",
        "question": (
            "We are a provider deploying an AI-based patient-triage system "
            "in a hospital. The hospital is the deployer. What accuracy and "
            "robustness obligations does the EU AI Act impose on us?"
        ),
        "expected_refs": ["Article 15", "Annex III"],
        "expected_keywords": ["accuracy", "robustness", "cybersecurity"],
        "category": "obligation_generation",
        "notes": (
            "Paper §3.1 obligation list item: 'strong standards of accuracy, "
            "robustness, and cybersecurity'. Art. 15 covers these for high-risk "
            "providers. Medical-imaging = Annex III(1)."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # article_retrieval (4)
    # Paper §4.1: relevant-article extraction is a core task
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "tp_v3_017",
        "question": (
            "Which articles of the EU AI Act apply to a provider that places "
            "a high-risk AI system on the market in the EU with no EU establishment?"
        ),
        "expected_refs": ["Article 22", "Article 16"],
        "expected_keywords": ["authorised representative", "no establishment", "provider"],
        "category": "article_retrieval",
        "notes": (
            "Relevant-article retrieval task. Non-EU provider must appoint an "
            "authorised representative (Art. 22) before market placement and "
            "satisfies provider obligations via Art. 16."
        ),
    },
    {
        "id": "tp_v3_018",
        "question": (
            "What articles govern the relationship between accuracy requirements "
            "and post-market monitoring for high-risk AI systems?"
        ),
        "expected_refs": ["Article 15", "Article 72"],
        "expected_keywords": ["accuracy", "post-market", "monitoring"],
        "category": "article_retrieval",
        "notes": (
            "Multi-article retrieval: Art. 15 (accuracy/robustness) + Art. 72 "
            "(post-market monitoring). Paper's 339 scenarios link an average of "
            "9.8 articles per scenario; multi-article retrieval is the core task."
        ),
    },
    {
        "id": "tp_v3_019",
        "question": (
            "Which articles does the EU AI Act reference when regulating AI use "
            "in migration, border control, and asylum procedures?"
        ),
        "expected_refs": ["Annex III", "Article 6"],
        "expected_keywords": ["migration", "border", "Annex III"],
        "category": "article_retrieval",
        "notes": (
            "Annex III(7) covers migration/border/asylum AI as high-risk. "
            "Art. 6 is the classification gateway. Multi-article retrieval task "
            "testing a domain the paper's 86 high-risk scenarios cover."
        ),
    },
    {
        "id": "tp_v3_020",
        "question": (
            "What EU AI Act articles regulate AI systems used by law enforcement "
            "for individual criminal-risk profiling?"
        ),
        "expected_refs": ["Article 5", "Annex III"],
        "expected_keywords": ["law enforcement", "criminal", "prohibited"],
        "category": "article_retrieval",
        "notes": (
            "Dual-regime question: Art. 5(1)(d) prohibits predictive-policing "
            "AI based on profiling; Annex III(6) makes law-enforcement high-risk "
            "AI subject to the full obligation stack for non-prohibited uses. "
            "Tests multi-article retrieval across the prohibited/high-risk boundary."
        ),
    },
]


if __name__ == "__main__":
    print(f"Total: {len(SCENARIOS)}")
    by_cat: dict[str, int] = {}
    for s in SCENARIOS:
        by_cat[s["category"]] = by_cat.get(s["category"], 0) + 1
    for cat, n in sorted(by_cat.items()):
        print(f"  {cat}: {n}")
