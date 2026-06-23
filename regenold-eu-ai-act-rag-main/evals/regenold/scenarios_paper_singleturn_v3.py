"""Paper-grounded single-turn QA eval set (V3).

Source: Davvetas et al. arXiv:2603.09435 "AI Act Evaluation Benchmark".
Dataset tasks covered: risk-level classification, relevant-article retrieval,
obligation generation, and question-answering — all four paper tasks.

Distribution across risk tiers (paper hypothesis mapping):
* prohibited   (5) — Art. 5 cases directly from the paper scenarios
* high_risk    (6) — Art. 6 + Annex III, obligation generation
* limited      (5) — Arts. 50 & 10, transparency obligations
* minimal      (4) — residual bucket, general QA

Schema (matches runner_v2 tricky schema exactly):

    {
        "id": str,
        "question": str,
        "expected_refs": list[str],   # "Article N" / "Annex N" user-facing form
        "expected_keywords": list[str],
        "category": str,              # risk tier or task label
        "notes": str,
    }

References are validated against app.data.article_existence.ARTICLE_EXISTENCE
(Art. 1-113 + Annex I-XIII in "Art. N" / "Annex N" internal form; the
wire emits "Article N" / "Annex N" user-facing form which is what this
file uses in expected_refs).
"""
from __future__ import annotations

SCENARIOS: list[dict] = [
    # ─────────────────────────────────────────────────────────────────────
    # prohibited (5) — Art. 5 cases; paper §3.1 hypothesis 1
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "st_v3_001",
        "question": (
            "What is the primary purpose of the AI Act according to Article 1?"
        ),
        "expected_refs": ["Article 1"],
        "expected_keywords": ["internal market", "trustworthy", "fundamental rights"],
        "category": "qa_task",
        "notes": (
            "Direct mapping from QA pairs file, Table 3 example. "
            "Art. 1 purpose statement; classic QA task."
        ),
    },
    {
        "id": "st_v3_002",
        "question": (
            "An AI system shows 'barely perceptible visual prompts' to increase "
            "subscription upgrades without users being aware. Is this prohibited "
            "under Article 5 of the EU AI Act?"
        ),
        "expected_refs": ["Article 5"],
        "expected_keywords": ["subliminal", "prohibited", "consciousness"],
        "category": "prohibited",
        "notes": (
            "Paper §4.2 canonical edge-case example: 'barely perceptible visual "
            "prompt' subliminal-technique boundary. The paper explicitly flags "
            "this as an edge case testing the 'subliminal' decision boundary."
        ),
    },
    {
        "id": "st_v3_003",
        "question": (
            "An AI system assigns social credit scores to citizens based on their "
            "online behaviour, restricting access to public services for those with "
            "low scores. Which article prohibits this?"
        ),
        "expected_refs": ["Article 5"],
        "expected_keywords": ["social scoring", "prohibited", "public services"],
        "category": "prohibited",
        "notes": (
            "Paper Table 2 canonical prohibited scenario: social scoring. "
            "Art. 5(1)(c) prohibited practice."
        ),
    },
    {
        "id": "st_v3_004",
        "question": (
            "An AI platform subtly nudges shoppers to purchase high-margin products "
            "through hidden audio cues without their conscious awareness. Is this "
            "an EU AI Act prohibited practice?"
        ),
        "expected_refs": ["Article 5"],
        "expected_keywords": ["subliminal", "prohibited", "subconscious"],
        "category": "prohibited",
        "notes": (
            "Paper Table 2 verbatim example: 'hidden-audio influence platform'. "
            "Art. 5(1)(a) subliminal-technique prohibition."
        ),
    },
    {
        "id": "st_v3_005",
        "question": (
            "An AI system manipulates social media content to influence voting "
            "behaviour in an election. Is this prohibited or merely high-risk?"
        ),
        "expected_refs": ["Article 5"],
        "expected_keywords": ["prohibited", "manipulation", "democratic"],
        "category": "prohibited",
        "notes": (
            "Paper §4.2 explicit edge case: 'AI that manipulates social media to "
            "influence voting' — paper notes it could look high-risk on the surface "
            "but is prohibited because it undermines democratic processes "
            "(Art. 5(1)(b) manipulation of elections context)."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # high_risk (6) — Art. 6 + Annex III; paper hypothesis 2
    # Obligation-generation task: what must the provider/deployer do?
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "st_v3_006",
        "question": (
            "Under what article and conditions does an AI system become classified "
            "as high-risk in the EU AI Act?"
        ),
        "expected_refs": ["Article 6", "Annex III"],
        "expected_keywords": ["high-risk", "classification", "Annex III"],
        "category": "high_risk",
        "notes": (
            "Paper hypothesis 2: 'high-risk category is analogous to Art. 6 + Annex III'. "
            "Article-retrieval task for the fundamental classification rule."
        ),
    },
    {
        "id": "st_v3_007",
        "question": (
            "A provider deploys an AI-based medical-imaging triage system in a hospital. "
            "What risk-management obligation does the EU AI Act impose on the provider?"
        ),
        "expected_refs": ["Article 9", "Annex III"],
        "expected_keywords": ["risk management", "system", "provider"],
        "category": "high_risk",
        "notes": (
            "Obligation-generation task (paper §4.1). Medical-imaging AI = "
            "Annex III(1) — provider must establish a risk-management system "
            "per Art. 9."
        ),
    },
    {
        "id": "st_v3_008",
        "question": (
            "What must a provider of a high-risk AI system include in the "
            "technical documentation required by the EU AI Act?"
        ),
        "expected_refs": ["Article 11", "Annex IV"],
        "expected_keywords": ["technical documentation", "Annex IV", "provider"],
        "category": "high_risk",
        "notes": (
            "Obligation-generation task. Art. 11 mandates technical documentation "
            "per Annex IV for all high-risk AI providers."
        ),
    },
    {
        "id": "st_v3_009",
        "question": (
            "What logging obligations apply to a provider of a high-risk AI system "
            "under the EU AI Act?"
        ),
        "expected_refs": ["Article 12"],
        "expected_keywords": ["logging", "automatically", "traceability"],
        "category": "high_risk",
        "notes": (
            "Obligation-generation task: Art. 12 automatic event logging for "
            "high-risk AI systems."
        ),
    },
    {
        "id": "st_v3_010",
        "question": (
            "An AI system is used in employment to evaluate worker performance and "
            "determine terminations. Which Annex III category covers it?"
        ),
        "expected_refs": ["Annex III", "Article 6"],
        "expected_keywords": ["employment", "performance", "high-risk"],
        "category": "high_risk",
        "notes": (
            "Relevant-article retrieval task (paper §4.1). Employment-decision AI "
            "maps to Annex III(4)(b). Paper generates 86 high-risk scenarios; "
            "employment is a key domain."
        ),
    },
    {
        "id": "st_v3_011",
        "question": (
            "What human-oversight obligations does the EU AI Act require for "
            "high-risk AI systems under Article 14?"
        ),
        "expected_refs": ["Article 14"],
        "expected_keywords": ["human oversight", "natural persons", "monitor"],
        "category": "high_risk",
        "notes": (
            "Obligation-generation task. Art. 14 human-oversight requirement "
            "for high-risk AI — key obligation the paper's 339 scenarios test."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # limited (5) — Arts. 50 & 10; paper hypothesis 3
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "st_v3_012",
        "question": (
            "Which articles of the EU AI Act ground the 'limited-risk' category, "
            "and what do they require?"
        ),
        "expected_refs": ["Article 50", "Article 10"],
        "expected_keywords": ["transparency", "data governance", "limited"],
        "category": "limited",
        "notes": (
            "Paper hypothesis 3 verbatim: 'limited-risk is grounded in Art. 50 "
            "and Art. 10'. Risk-level classification + article retrieval combined."
        ),
    },
    {
        "id": "st_v3_013",
        "question": (
            "A chatbot interacts with consumers without disclosing it is AI. "
            "What EU AI Act obligation applies?"
        ),
        "expected_refs": ["Article 50"],
        "expected_keywords": ["chatbot", "disclosure", "artificial intelligence"],
        "category": "limited",
        "notes": (
            "Art. 50(1) chatbot-disclosure obligation. Paper's 84 limited-risk "
            "scenarios focus on transparency obligations; chatbots are the "
            "canonical limited-risk use case."
        ),
    },
    {
        "id": "st_v3_014",
        "question": (
            "An AI system generates synthetic images. What AI Act transparency "
            "obligation applies to the provider?"
        ),
        "expected_refs": ["Article 50"],
        "expected_keywords": ["synthetic", "label", "generated"],
        "category": "limited",
        "notes": (
            "Art. 50(2) deep-fake / synthetic content labelling obligation. "
            "Limited-risk transparency task."
        ),
    },
    {
        "id": "st_v3_015",
        "question": (
            "What data-governance obligations does Article 10 of the EU AI Act "
            "impose on providers of high-risk AI?"
        ),
        "expected_refs": ["Article 10"],
        "expected_keywords": ["training data", "data governance", "quality"],
        "category": "limited",
        "notes": (
            "Art. 10 data-governance requirement. Paper hypothesis 3 explicitly "
            "lists Art. 10 as a grounding article for limited-risk alongside Art. 50."
        ),
    },
    {
        "id": "st_v3_016",
        "question": (
            "A recommendation system operates on an online platform and is not "
            "classified as high-risk. Does the EU AI Act impose any transparency "
            "obligations on it?"
        ),
        "expected_refs": ["Article 50"],
        "expected_keywords": ["transparency", "not high-risk", "information"],
        "category": "limited",
        "notes": (
            "Art. 50(3) — limited-risk recommendation systems must signal their "
            "AI nature. Paper's limited category explicitly covers 'operates in "
            "or adjacent to critical domains but does not pose significant harm'."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # minimal (4) — residual bucket; paper hypothesis 4
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "st_v3_017",
        "question": (
            "An AI-powered spam filter classifies emails for individual users. "
            "What risk level is this under the EU AI Act and what obligations apply?"
        ),
        "expected_refs": ["Article 5", "Article 6"],
        "expected_keywords": ["minimal", "no specific", "residual"],
        "category": "minimal",
        "notes": (
            "Paper hypothesis 4: 'minimal = residual if not prohibited, not "
            "high-risk, not triggering Art. 50/10'. The paper uses spam filters "
            "as a canonical minimal-risk example (§3.1). Engine should state "
            "minimal risk / no specific AI Act obligations."
        ),
    },
    {
        "id": "st_v3_018",
        "question": (
            "A video game uses an AI to adapt difficulty in real time. "
            "What EU AI Act classification and obligations apply?"
        ),
        "expected_refs": ["Article 5", "Article 6"],
        "expected_keywords": ["minimal", "exempt", "no significant"],
        "category": "minimal",
        "notes": (
            "Paper §3.1 verbatim: 'video games' as a minimal-risk example. "
            "Residual bucket — no prohibited practice, not Annex III, "
            "no Art. 50 chatbot interaction."
        ),
    },
    {
        "id": "st_v3_019",
        "question": (
            "What distinguishes a 'minimal-risk' AI system from a 'limited-risk' "
            "one under the EU AI Act risk pyramid?"
        ),
        "expected_refs": ["Article 5", "Article 6", "Article 50"],
        "expected_keywords": ["minimal", "limited", "transparency"],
        "category": "minimal",
        "notes": (
            "Paper §5 / Table 4 discussion: limited/minimal boundary is the "
            "hardest classification (limited F1 0.65, minimal F1 0.45). "
            "Tests the engine's ability to explain the decision boundary "
            "between residual and limited tiers."
        ),
    },
    {
        "id": "st_v3_020",
        "question": (
            "An AI model recommends playlists on a music streaming service "
            "with no user profiling for protected characteristics. "
            "What AI Act category applies?"
        ),
        "expected_refs": ["Article 5", "Article 6"],
        "expected_keywords": ["minimal", "no significant", "residual"],
        "category": "minimal",
        "notes": (
            "Paper §5 result discussion: minimal scenarios are 'underpredicted' "
            "(recall 0.29, precision 0.97) because keyword overlap with limited "
            "is high. Tests the engine on a clean minimal case."
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
