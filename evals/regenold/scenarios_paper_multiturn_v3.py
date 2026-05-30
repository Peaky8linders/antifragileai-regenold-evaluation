"""Paper-grounded multi-turn eval set (V3).

Source: Davvetas et al. arXiv:2603.09435 "AI Act Evaluation Benchmark".
These scenarios chain 3-5 turns simulating real compliance conversations
grounded in the paper's four tasks (risk classification, article retrieval,
obligation generation, QA) and its four risk tiers.

Themes:
* Risk re-classification across turns (system gains/loses features)
* Provider ↔ deployer role flip mid-conversation
* Obligation-generation chain building across turns
* Cross-tier escalation (minimal → limited → high-risk → prohibited)
* GPAI / limited / minimal confusion following the paper's hard boundary

Schema (identical to scenarios_multiturn_v2.SCENARIOS):

    {
        "id": str,
        "turns": list[{"role": "user"|"assistant", "content": str}],
        "expected_final_refs": list[str],     # "Article N" / "Annex N" form
        "expected_final_keywords": list[str], # substring markers in final answer
        "notes": str,
    }

The runner_v2.run_multiturn() sends ``turns`` as the full history,
scores the FINAL assistant turn against ``expected_final_refs`` and
``expected_final_keywords``, and computes multi-turn coherence.
"""
from __future__ import annotations

SCENARIOS: list[dict] = [
    # ─────────────────────────────────────────────────────────────────────
    # 1 — Minimal → Limited escalation (chatbot disclosure trigger)
    # Paper hypothesis 3: limited-risk grounded in Art. 50
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "mt_v3_001",
        "turns": [
            {
                "role": "user",
                "content": (
                    "We're building an AI writing assistant for internal employee "
                    "use — autocompletes text in our internal wiki. What AI Act "
                    "obligations apply?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "An internal writing tool with no external users and no high-risk "
                    "domain is minimal-risk under the AI Act. No specific obligations "
                    "apply beyond the general good-practice provisions."
                ),
            },
            {
                "role": "user",
                "content": (
                    "We're now exposing the same AI via a chat widget on our public "
                    "website so customers can ask questions about our products."
                ),
            },
        ],
        "expected_final_refs": ["Article 50"],
        "expected_final_keywords": ["chatbot", "disclosure", "AI"],
        "notes": (
            "Cross-turn escalation: internal minimal → public chatbot limited. "
            "Art. 50(1) chatbot disclosure applies once natural persons can "
            "interact with it. Engine must update its prior verdict."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # 2 — Limited → High-risk escalation (credit advice + chatbot)
    # Paper §4.2 / §5 confusion: limited vs high-risk
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "mt_v3_002",
        "turns": [
            {
                "role": "user",
                "content": (
                    "We run a chatbot that gives general financial tips to users "
                    "— things like 'save 10% of your salary'. What risk level?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "General financial wellness tips with no individualised credit "
                    "assessment are limited-risk under Article 50 (chatbot disclosure "
                    "obligation applies)."
                ),
            },
            {
                "role": "user",
                "content": (
                    "We're extending the chatbot to evaluate individual loan applications "
                    "and produce credit scores that lenders actually rely on."
                ),
            },
        ],
        "expected_final_refs": ["Annex III", "Article 6"],
        "expected_final_keywords": ["high-risk", "credit", "Annex III"],
        "notes": (
            "Limited → high-risk escalation. Adding individualised credit-scoring "
            "to a chatbot flips it to Annex III(5)(b) high-risk. Engine must "
            "update its prior verdict and explain the Art. 6 + Annex III gateway."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # 3 — High-risk obligation chain building turn by turn
    # Paper §3.1 + §4.1: obligation-generation task over multiple turns
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "mt_v3_003",
        "turns": [
            {
                "role": "user",
                "content": (
                    "We are a provider of an AI system that scores candidates in "
                    "our recruitment process. What is the first obligation we need "
                    "to fulfil?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "Recruitment AI is Annex III(4)(a) high-risk. Your first "
                    "obligation is to establish and implement a risk-management "
                    "system under Article 9."
                ),
            },
            {
                "role": "user",
                "content": "What comes next after risk management?",
            },
            {
                "role": "assistant",
                "content": (
                    "Article 10 data-governance requirements: training, validation, "
                    "and testing data must be relevant, representative, and free from "
                    "errors."
                ),
            },
            {
                "role": "user",
                "content": (
                    "We've done both. What are the remaining pre-market obligations "
                    "before we can place this on the EU market?"
                ),
            },
        ],
        "expected_final_refs": [
            "Article 11", "Article 12", "Article 13",
            "Article 14", "Article 15", "Article 43",
        ],
        "expected_final_keywords": [
            "technical documentation", "logging", "transparency", "conformity"
        ],
        "notes": (
            "Obligation-generation chain across 5 turns. After Arts. 9 and 10, "
            "the remaining pre-market stack is Arts. 11-15 + Art. 43 conformity. "
            "Engine must hold the 'we are a recruitment AI provider' context "
            "and complete the list from where it left off."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # 4 — Risk re-classification: high-risk → prohibited escalation
    # Paper §4.2: "AI that manipulates social media to influence voting"
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "mt_v3_004",
        "turns": [
            {
                "role": "user",
                "content": (
                    "We operate an AI content-personalisation system for a news "
                    "platform. It ranks articles to maximise time-on-site. "
                    "What risk level?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "A general news recommendation system that maximises engagement "
                    "is minimal-risk — no Annex III category applies and no Art. 50 "
                    "chatbot interaction with natural persons."
                ),
            },
            {
                "role": "user",
                "content": (
                    "We've now discovered our A/B testing shows the system "
                    "systematically amplifies politically polarising content "
                    "in the weeks before elections, and we continue running it."
                ),
            },
        ],
        "expected_final_refs": ["Article 5"],
        "expected_final_keywords": ["prohibited", "manipulation", "democratic"],
        "notes": (
            "Minimal → prohibited flip on discovering the system manipulates "
            "democratic processes (Art. 5(1)(b)). Paper §4.2 explicit edge case. "
            "Engine must escalate all the way to prohibited, not stop at high-risk."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # 5 — Provider → Deployer role transition
    # Paper scenario template: Role = Provider or Deployer; role flip is key
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "mt_v3_005",
        "turns": [
            {
                "role": "user",
                "content": (
                    "We are a hospital that purchased a CE-marked AI triage system "
                    "from MedAI Ltd. Who is the provider?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "MedAI Ltd is the provider under Article 3 of the AI Act. "
                    "You are the deployer under Article 26."
                ),
            },
            {
                "role": "user",
                "content": (
                    "We customised the training data with 18 months of our own "
                    "patient records to improve triage accuracy for our population."
                ),
            },
        ],
        "expected_final_refs": ["Article 25", "Article 16"],
        "expected_final_keywords": ["provider", "substantial modification", "obligations"],
        "notes": (
            "Deployer → provider flip via substantial modification (Art. 25). "
            "Retraining on own data changes the system's intended purpose/performance "
            "characteristics. Paper scenarios require distinguishing provider vs "
            "deployer as a mandatory field."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # 6 — GPAI classification + obligation chain
    # Paper §3.1 mentions GPAI as an emerging challenge
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "mt_v3_006",
        "turns": [
            {
                "role": "user",
                "content": (
                    "We are training a foundation model at 8×10²² FLOPs. "
                    "Are we a GPAI provider under the AI Act?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "At 8×10²² FLOPs you are below the 10²³ FLOPs threshold from "
                    "the Commission's July 2025 Guidelines, so you are not yet "
                    "classified as a GPAI provider under Article 51."
                ),
            },
            {
                "role": "user",
                "content": "We scaled up to 2×10²³ FLOPs in our next training run.",
            },
        ],
        "expected_final_refs": ["Article 51", "Article 53"],
        "expected_final_keywords": ["GPAI", "general-purpose", "obligations"],
        "notes": (
            "GPAI threshold crossing (10²³ FLOPs from the Commission Guidelines). "
            "Engine must update the prior verdict and surface GPAI provider "
            "obligations (Art. 53 transparency + training-data summary)."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # 7 — Obligation generation: deployer side over 4 turns
    # Paper §4.1: obligation generation for deployer role
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "mt_v3_007",
        "turns": [
            {
                "role": "user",
                "content": (
                    "We are a bank using an AI from FinTech Corp to evaluate "
                    "loan applications. The AI is already CE-marked. What must WE "
                    "do as deployer before we start using it?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "As deployer of a high-risk AI (Annex III(5)(b) credit scoring), "
                    "you must verify the provider's CE marking and conformity "
                    "documentation per Article 26."
                ),
            },
            {
                "role": "user",
                "content": "What ongoing obligations apply after we start using it?",
            },
            {
                "role": "assistant",
                "content": (
                    "You must monitor the system's operation, ensure human oversight "
                    "under Article 14, and report serious incidents to authorities "
                    "under Article 73."
                ),
            },
            {
                "role": "user",
                "content": (
                    "A customer whose loan was denied asks why. What does the AI Act "
                    "require us to tell them?"
                ),
            },
        ],
        "expected_final_refs": ["Article 86"],
        "expected_final_keywords": ["explanation", "individual", "right"],
        "notes": (
            "Art. 86 right to explanation for affected persons. Deployer obligation "
            "chain concludes with the individual-rights obligation. Engine must hold "
            "'we are a deployer' context across 5 turns."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # 8 — Borderline-prohibition carve-out + obligation
    # Paper §3.1: Art. 5 prohibitions with internal conditionalities
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "mt_v3_008",
        "turns": [
            {
                "role": "user",
                "content": (
                    "We deploy a real-time biometric identification system in public "
                    "spaces for law enforcement. Is this always prohibited?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "Real-time RBI by law enforcement is prohibited under Article 5 "
                    "with narrow exceptions: (i) searching for missing persons or "
                    "victims, (ii) preventing imminent terrorist attacks, (iii) "
                    "identifying suspects of serious crimes."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Our use case is preventing imminent terrorist attacks. "
                    "Can we deploy without prior authorisation?"
                ),
            },
        ],
        "expected_final_refs": ["Article 5"],
        "expected_final_keywords": ["authorisation", "prior", "judicial"],
        "notes": (
            "Art. 5(2) requires prior judicial or independent administrative "
            "authorisation even for the terrorist-attack carve-out. "
            "Engine must not grant blanket permission just because the carve-out "
            "category applies — the conditionalities matter."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # 9 — Conformity assessment route selection (3 turns)
    # Paper §4.1 obligation-generation task applied to conformity
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "mt_v3_009",
        "turns": [
            {
                "role": "user",
                "content": (
                    "We are a provider of a high-risk AI for fraud detection in "
                    "banking. Which conformity assessment route applies?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "Banking fraud-detection AI is Annex III(5)(b). Most Annex III "
                    "high-risk AI — except biometric systems under Annex III(1) — "
                    "uses the internal control route under Annex VI, not a notified body."
                ),
            },
            {
                "role": "user",
                "content": (
                    "We added biometric voice-authentication to verify caller "
                    "identity before presenting the fraud score. Does that change "
                    "the conformity route?"
                ),
            },
        ],
        "expected_final_refs": ["Article 43", "Annex VII"],
        "expected_final_keywords": ["notified body", "biometric", "Annex VII"],
        "notes": (
            "Adding biometric identification (Annex III(1)) requires a notified "
            "body (Annex VII), overriding the internal-control route. "
            "Engine must update its prior conformity-route verdict."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # 10 — Article retrieval across risk tiers in one conversation
    # Paper §4.1: relevant-article extraction task
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "mt_v3_010",
        "turns": [
            {
                "role": "user",
                "content": (
                    "Which articles apply to our AI that monitors employee "
                    "social media for security clearance assessments?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "Employment AI for security clearance = Annex III(4) high-risk. "
                    "Core articles: Art. 9 (risk management), Art. 10 (data governance), "
                    "Art. 13 (transparency to deployer), Art. 14 (human oversight)."
                ),
            },
            {
                "role": "user",
                "content": (
                    "The system now also infers political opinions from social "
                    "media posts to flag 'loyalty risks'. Does that change anything?"
                ),
            },
        ],
        "expected_final_refs": ["Article 5"],
        "expected_final_keywords": ["prohibited", "political", "biometric categorisation"],
        "notes": (
            "High-risk → prohibited escalation. Inferring political opinions from "
            "biometric/behavioural data = Art. 5(1)(g) prohibited categorisation. "
            "Engine must escalate from its prior high-risk verdict. "
            "Paper §4.2 explains how proximity to prohibited practices makes "
            "classification hard at decision boundaries."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # 11 — Limited-risk obligation chain: data governance + transparency
    # Paper hypothesis 3: limited-risk grounded in Art. 50 and Art. 10
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "mt_v3_011",
        "turns": [
            {
                "role": "user",
                "content": (
                    "We run a customer service chatbot that is NOT high-risk. "
                    "What transparency must we show users under the AI Act?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "Article 50(1) requires you to disclose to users that they are "
                    "interacting with an AI system, unless it is obvious from context."
                ),
            },
            {
                "role": "user",
                "content": (
                    "We also use the conversation data to train the model. "
                    "What data obligations apply to that?"
                ),
            },
        ],
        "expected_final_refs": ["Article 10"],
        "expected_final_keywords": ["training data", "data governance", "quality"],
        "notes": (
            "Paper hypothesis 3: limited-risk is grounded in Art. 50 AND Art. 10. "
            "Turn 3 shifts from transparency (Art. 50) to data governance (Art. 10). "
            "Engine must surface Art. 10 even though the chatbot is not high-risk "
            "(Art. 10 applies to training data used for any AI system in the Act's scope)."
        ),
    },
    # ─────────────────────────────────────────────────────────────────────
    # 12 — Minimal risk stability under domain pressure
    # Paper §5: minimal recall 0.29 — engine systematically under-predicts minimal
    # ─────────────────────────────────────────────────────────────────────
    {
        "id": "mt_v3_012",
        "turns": [
            {
                "role": "user",
                "content": (
                    "We have an AI that recommends movies on our streaming platform. "
                    "What AI Act obligations apply?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "A movie recommendation system is minimal-risk — no specific "
                    "AI Act obligations apply. You should follow general AI best "
                    "practices voluntarily."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Our platform also has a children's section. Does serving "
                    "recommendations to minors change the risk classification?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "Serving recommendations to minors does not by itself move the "
                    "system into a higher risk tier. There is no specific AI Act "
                    "provision elevating entertainment recommendations to high-risk "
                    "solely because of the audience's age. Applicable minor-specific "
                    "obligations come from GDPR (Art. 8) and the DSA, not the AI Act."
                ),
            },
            {
                "role": "user",
                "content": (
                    "We profile children's viewing to infer their emotional state "
                    "and present content calibrated to that inferred emotional state. "
                    "Still minimal-risk?"
                ),
            },
        ],
        "expected_final_refs": ["Article 5"],
        "expected_final_keywords": ["prohibited", "vulnerable", "exploitation"],
        "notes": (
            "Minimal → prohibited escalation via children's vulnerability. "
            "Inferring emotional state of minors and exploiting it = "
            "Art. 5(1)(b) exploitation of vulnerability. "
            "Paper §5: minimal recall is 0.29 — engine under-predicts minimal "
            "AND may also under-predict prohibited when the path starts minimal. "
            "Tests stable cross-tier escalation across 5 turns."
        ),
    },
]


if __name__ == "__main__":
    print(f"Total: {len(SCENARIOS)}")
    for i, s in enumerate(SCENARIOS):
        turns = len(s.get("turns", []))
        refs = s.get("expected_final_refs", [])
        kws = s.get("expected_final_keywords", [])
        print(f"  {s['id']}  turns={turns}  refs={refs}  kws={kws}")
