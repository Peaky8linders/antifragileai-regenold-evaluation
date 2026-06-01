"""GraphRAG-paper benchmark probe set (R99 add-on).

Source: a related EU AI Act GraphRAG-system paper, Appendix B.2 dataset.
Two groups:

* ``GROUND_TRUTH`` — 20 questions each paired with an expected answer +
  reference list (Articles / Annexes). We score these.
* ``NO_GROUND_TRUTH`` — now empty (all questions have been promoted to GROUND_TRUTH).

Wire-citation note
------------------
The Regenold wire emits only ``Article N`` / ``Annex N`` references (never
Recitals — see CLAUDE.md hard rule #1 + R47-B). The paper's gold reference
lists mix Articles and Recitals; we encode the **Article/Annex heads only**
into ``expected_refs`` and record the full paper reference string in
``paper_refs`` for provenance. Two ground-truth questions (gt_06 minimal
risk → Recital 53; gt_07 guiding principles → Recitals 1/7/48) have
**recital-only** gold with no wire-citable article, flagged ``recital_only``;
the runner excludes them from the reference-correctness aggregate (keyword
recall + tone are still scored).

Schema (GROUND_TRUTH) matches runner_v2 tricky schema + extra provenance:

    {
        "id", "question", "expected_refs", "expected_keywords",
        "category", "notes", "paper_refs", "recital_only" (bool),
    }
"""
from __future__ import annotations

# ── Group 1 — questions WITH ground truth (original 10 + promoted 10) ────────────────────────────────
GROUND_TRUTH: list[dict] = [
    {
        "id": "gt_01",
        "question": "What risk categories are provided for AI systems?",
        "expected_refs": ["Article 3", "Article 5", "Article 6", "Article 50"],
        "expected_keywords": ["unacceptable risk", "limited risk", "minimal risk"],
        "category": "risk_taxonomy",
        "paper_refs": (
            "Articles: 3(39),3(40),3(41),5(1),6(1),6(2),50(1),50(2); "
            "Recitals: 26,50,52,54,55,56,57,58,59,61,64,66,132,165"
        ),
        "recital_only": False,
        "notes": "Four-tier risk pyramid. Gold spans Art. 3/5/6/50.",
    },
    {
        "id": "gt_02",
        "question": (
            "What types of AI systems or practices are explicitly prohibited "
            "by the AI Act?"
        ),
        "expected_refs": ["Article 5"],
        "expected_keywords": ["subliminal", "social scoring", "biometric"],
        "category": "prohibited",
        "paper_refs": "Articles: 5",
        "recital_only": False,
        "notes": "Art. 5 prohibited practices.",
    },
    {
        "id": "gt_03",
        "question": "What is the definition of high risk?",
        "expected_refs": ["Article 6"],
        "expected_keywords": ["health", "safety", "fundamental rights"],
        "category": "high_risk_definition",
        "paper_refs": "Articles: 6",
        "recital_only": False,
        "notes": "Art. 6 high-risk classification; answer also cites Annex III.",
    },
    {
        "id": "gt_04",
        "question": (
            "Which sectors or applications are considered high-risk under the "
            "regulation?"
        ),
        "expected_refs": ["Article 6"],
        "expected_keywords": ["safety component", "annex i", "conformity assessment"],
        "category": "high_risk_sectors",
        "paper_refs": "Articles: 6",
        "recital_only": False,
        "notes": "Art. 6(1) Annex I safety-component path + Art. 6(2) Annex III.",
    },
    {
        "id": "gt_05",
        "question": "How should users be informed when interacting with AI systems?",
        "expected_refs": ["Article 50"],
        "expected_keywords": ["informed", "interacting", "disclose"],
        "category": "transparency",
        "paper_refs": "Articles: 50",
        "recital_only": False,
        "notes": "Art. 50 transparency / interaction disclosure.",
    },
    {
        "id": "gt_06",
        "question": "What are AI systems with minimal risks?",
        "expected_refs": [],  # recital-only gold (Recital 53) — no wire-citable article
        "expected_keywords": ["structured data", "duplicates", "minimal"],
        "category": "minimal_risk",
        "paper_refs": "Recitals: 53",
        "recital_only": True,
        "notes": (
            "Recital-only gold — wire emits Articles/Annexes only, so this row "
            "is excluded from the reference-correctness aggregate."
        ),
    },
    {
        "id": "gt_07",
        "question": "What are the guiding principles established by the AI Act?",
        "expected_refs": [],  # recital-only gold (Recitals 1,7,48)
        "expected_keywords": ["fundamental rights", "democracy", "rule of law"],
        "category": "guiding_principles",
        "paper_refs": "Recitals: 1,7,48",
        "recital_only": True,
        "notes": (
            "Recital-only gold — excluded from the reference-correctness "
            "aggregate (keyword recall + tone still scored)."
        ),
    },
    {
        "id": "gt_08",
        "question": (
            "What is the definition of a \"system of artificial intelligence\"?"
        ),
        "expected_refs": ["Article 3"],
        "expected_keywords": ["machine-based", "autonomy", "infers"],
        "category": "definition",
        "paper_refs": "Articles: 3(1)",
        "recital_only": False,
        "notes": "Art. 3(1) definition of an AI system.",
    },
    {
        "id": "gt_09",
        "question": (
            "What are the penalties for violating the provisions of the "
            "regulation for high-risk AI systems?"
        ),
        "expected_refs": ["Article 99"],
        "expected_keywords": ["administrative", "fine", "turnover"],
        "category": "penalties",
        "paper_refs": "Articles: 99",
        "recital_only": False,
        "notes": "Art. 99 penalties (up to EUR 15m or 3% worldwide turnover).",
    },
    {
        "id": "gt_10",
        "question": "What is the difference between the deployer and the provider?",
        "expected_refs": ["Article 3", "Article 16"],
        "expected_keywords": ["provider", "deployer", "trademark"],
        "category": "roles",
        "paper_refs": "Articles: 3(3),3(4),16",
        "recital_only": False,
        "notes": "Art. 3(3)/(4) definitions + Art. 16 provider responsibility.",
    },
    # Promoted scenarios from Appendix B.2.2 (Group 2)
    {
        "id": "ng_01",
        "question": "What criteria exist for assessing the risk of an AI system?",
        "expected_refs": ["Article 7", "Article 9"],
        "expected_keywords": ["intended purpose", "likelihood of harm", "vulnerable groups", "fundamental rights"],
        "category": "risk_assessment",
        "paper_refs": "Articles: 7(2),9(9)",
        "recital_only": False,
        "notes": "Assessment criteria under Article 7(2) and Article 9(9).",
    },
    {
        "id": "ng_02",
        "question": (
            "What are the sanctions for violating the provisions of the "
            "regulation for transparency risk systems?"
        ),
        "expected_refs": ["Article 99"],
        "expected_keywords": ["administrative fine", "turnover", "preceding financial year", "effectiveness"],
        "category": "sanctions",
        "paper_refs": "Articles: 99(4)",
        "recital_only": False,
        "notes": "Transparency system sanctions under Article 99(4) (up to 15M EUR or 3% turnover).",
    },
    {
        "id": "ng_03",
        "question": "What obligations exist for deployers of high-risk AI systems?",
        "expected_refs": ["Article 26", "Article 27"],
        "expected_keywords": ["impact assessment", "inform", "monitor", "log", "instructions for use"],
        "category": "deployer_obligations",
        "paper_refs": "Articles: 26,27(1)",
        "recital_only": False,
        "notes": "Deployer obligations under Articles 26 and 27 (FRIA).",
    },
    {
        "id": "ng_04",
        "question": "What requirements must AI systems classified as high-risk meet?",
        "expected_refs": ["Article 9", "Article 11", "Article 13", "Article 14", "Article 15"],
        "expected_keywords": ["risk management", "technical documentation", "transparency", "human oversight", "robustness"],
        "category": "high_risk_requirements",
        "paper_refs": "Articles: 9,11,13,14,15",
        "recital_only": False,
        "notes": "High-risk mandatory requirements under Chapter III, Section 2.",
    },
    {
        "id": "ng_05",
        "question": (
            "What obligations do providers of high-risk AI systems have in terms "
            "of transparency and technical documentation?"
        ),
        "expected_refs": ["Article 11", "Article 13", "Article 18", "Article 21", "Article 23"],
        "expected_keywords": ["technical documentation", "conformity", "10 years", "instructions for use"],
        "category": "provider_obligations",
        "paper_refs": "Articles: 11,13,18,21,23",
        "recital_only": False,
        "notes": "Provider transparency and documentation obligations under Chapter III, Section 3.",
    },
    {
        "id": "ng_06",
        "question": "What does a conformity assessment consist of?",
        "expected_refs": ["Article 43", "Annex VI", "Annex VII"],
        "expected_keywords": ["internal control", "notified body", "quality management system", "certificate"],
        "category": "conformity_assessment",
        "paper_refs": "Articles: 43; Annexes: VI,VII",
        "recital_only": False,
        "notes": "Conformity assessment mechanisms under Article 43 and Annexes VI/VII.",
    },
    {
        "id": "ng_07",
        "question": "What does systemic-risk mean?",
        "expected_refs": ["Article 3", "Article 55"],
        "expected_keywords": ["high-impact capabilities", "general-purpose", "propagate", "negative effects"],
        "category": "systemic_risk",
        "paper_refs": "Articles: 3(65),55",
        "recital_only": False,
        "notes": "Systemic risk definitions and assessment under Article 3(65) and Article 55.",
    },
    {
        "id": "ng_08",
        "question": "What is the definition of General-purpose AI?",
        "expected_refs": ["Article 3"],
        "expected_keywords": ["general-purpose ai model", "generality", "distinct tasks", "self-supervision"],
        "category": "gpai_definition",
        "paper_refs": "Articles: 3(63),3(66)",
        "recital_only": False,
        "notes": "Definition of General-Purpose AI model/system under Article 3.",
    },
    {
        "id": "ng_09",
        "question": "What are the components of a quality management system?",
        "expected_refs": ["Article 17"],
        "expected_keywords": ["design control", "data management", "testing", "post-market monitoring"],
        "category": "qms",
        "paper_refs": "Articles: 17(1)",
        "recital_only": False,
        "notes": "QMS requirements under Article 17.",
    },
    {
        "id": "ng_10",
        "question": (
            "What are the requirements for documenting bias mitigation measures "
            "in AI models?"
        ),
        "expected_refs": ["Article 10", "Article 15"],
        "expected_keywords": ["bias detection", "data governance", "training", "validation", "mitigate"],
        "category": "bias_mitigation",
        "paper_refs": "Articles: 10(2),15(4)",
        "recital_only": False,
        "notes": "Bias mitigation requirements under Article 10(2) and Article 15(4).",
    },
    # ── PDF Example Questions ─────────────────────────────
    {
        "id": "gt_11",
        "question": "Does the technical documentation of a high-risk AI system require to provide specifications regarding the required hardware?",
        "expected_refs": ["Article 11", "Annex IV"],
        "expected_keywords": ["technical documentation", "hardware", "computing resources", "architecture"],
        "category": "hardware_specs",
        "paper_refs": "Articles: 11; Annexes: IV",
        "recital_only": False,
        "notes": "PDF Example 1. Art. 11 + Annex IV hardware specs.",
    },
    {
        "id": "gt_12",
        "question": "Are AI systems intended for emotion recognition from biometric data always prohibited?",
        "expected_refs": ["Article 5"],
        "expected_keywords": ["workplace", "educational", "medical", "safety", "not always prohibited"],
        "category": "emotion_recognition",
        "paper_refs": "Articles: 5",
        "recital_only": False,
        "notes": "PDF Example 2. Art. 5 prohibitions and exceptions.",
    },
    {
        "id": "gt_13",
        "question": "Is an AI that transcribes doctor–patient conversations prohibited? Or is it high-risk as per the use cases of Annex III of the AI Act?",
        "expected_refs": ["Article 5", "Article 6", "Annex I", "Annex III"],
        "expected_keywords": ["not prohibited", "medical device", "safety component", "MDR", "general purpose"],
        "category": "transcription_classification",
        "paper_refs": "Articles: 5,6; Annexes: I,III",
        "recital_only": False,
        "notes": "PDF Example 3. Not prohibited under Art. 5; high-risk under Art. 6/Annex I if medical device.",
    },
    # ── MedTech / Life Sciences Scenarios ──────────────────
    {
        "id": "med_01",
        "question": "We are a medical device manufacturer building an AI system to analyze X-rays to detect tumors. Is this system classified as high-risk, and what conformity assessment is required?",
        "expected_refs": ["Article 6", "Article 43", "Annex I"],
        "expected_keywords": ["medical device", "safety component", "Annex I", "third-party", "conformity assessment"],
        "category": "medtech_high_risk",
        "paper_refs": "Articles: 6,43; Annexes: I",
        "recital_only": False,
        "notes": "Medical Imaging Device classification and conformity.",
    },
    {
        "id": "med_02",
        "question": "Can a hospital use an AI system to sort patients based on their biometric data to determine priority for an experimental clinical trial?",
        "expected_refs": ["Article 5", "Article 6", "Annex III"],
        "expected_keywords": ["healthcare", "essential services", "biometric categorization", "high-risk", "triage"],
        "category": "medtech_triage",
        "paper_refs": "Articles: 5,6; Annexes: III",
        "recital_only": False,
        "notes": "Clinical Trial Patient Triage.",
    },
    {
        "id": "med_03",
        "question": "Our life sciences startup developed a general-purpose AI model trained on massive amounts of genomic data. What transparency obligations apply to us?",
        "expected_refs": ["Article 50", "Article 53"],
        "expected_keywords": ["general-purpose AI model", "transparency", "copyright", "summary of training data", "technical documentation"],
        "category": "lifesciences_gpai",
        "paper_refs": "Articles: 50,53",
        "recital_only": False,
        "notes": "Genomic LLM transparency obligations.",
    },
    {
        "id": "med_04",
        "question": "We are a university lab developing an AI model exclusively for scientific research and development into new life science drugs. Does the AI Act apply to our model before it is released to the market?",
        "expected_refs": ["Article 2"],
        "expected_keywords": ["scientific research", "development", "exempt", "does not apply"],
        "category": "lifesciences_research",
        "paper_refs": "Articles: 2",
        "recital_only": False,
        "notes": "AI in Medical Research (Exemption).",
    },
    {
        "id": "med_05",
        "question": "We are developing a generative AI chatbot that will be deployed on a hospital website to answer general patient queries. What transparency obligations apply?",
        "expected_refs": ["Article 50"],
        "expected_keywords": ["interact", "natural persons", "informed", "chatbot", "transparency"],
        "category": "medtech_chatbot",
        "paper_refs": "Articles: 50",
        "recital_only": False,
        "notes": "Patient chatbot transparency.",
    },
    {
        "id": "med_06",
        "question": "A pharmaceutical company wants to use an AI system to monitor the emotions and stress levels of their manufacturing line workers to improve efficiency. Is this allowed?",
        "expected_refs": ["Article 5"],
        "expected_keywords": ["emotion recognition", "workplace", "prohibited", "employees"],
        "category": "medtech_emotion_workplace",
        "paper_refs": "Articles: 5",
        "recital_only": False,
        "notes": "Emotion recognition in workplace prohibition.",
    },
    {
        "id": "med_07",
        "question": "Is an AI system intended to be used as a safety component in robotic surgery considered high-risk under the AI Act?",
        "expected_refs": ["Article 6", "Annex I"],
        "expected_keywords": ["safety component", "medical device", "Annex I", "high-risk"],
        "category": "medtech_robotic_surgery",
        "paper_refs": "Articles: 6; Annexes: I",
        "recital_only": False,
        "notes": "Robotic surgery safety component (MDR).",
    },
]

# ── Group 2 — questions WITHOUT ground truth ──────────────────────────────
# All 10 questions have been enriched and promoted to GROUND_TRUTH to create a wider scored benchmark.
NO_GROUND_TRUTH: list[dict] = []

# ── Paper's lawyer-reviewed reference answers (Appendix B.2.1) ─────────────
# Verbatim from the GraphRAG paper's supplementary material — the gold the
# paper's BERTScore automatic eval compared against. Kept here for provenance
# and to enable a reference-answer-grounded correctness judge.
REFERENCE_ANSWERS: dict[str, str] = {
    "gt_01": (
        "The AI Act establishes a risk-based framework, categorising AI systems "
        "based on their potential for harm. Here are the risk categories: "
        "Unacceptable Risk, High Risk, Limited Risk and Minimal Risk."
    ),
    "gt_02": (
        "Subliminal techniques beyond a person's consciousness to materially "
        "distort behaviour in a way that causes harm. Exploiting vulnerabilities "
        "of specific groups (e.g., age, disability) to materially distort "
        "behaviour and cause harm. Social scoring systems can lead to detrimental "
        "treatment in unrelated social contexts or disproportionate treatment. "
        "Real-time remote biometric identification systems in publicly accessible "
        "spaces for law enforcement purposes, except for specific exceptions. AI "
        "systems used by or on behalf of law enforcement to make risk assessments "
        "for predicting criminal offenses based solely on profiling or personality "
        "traits."
    ),
    "gt_03": (
        "The AI Act defines 'high risk' in the context of AI systems that pose "
        "significant risks to the health and safety or the fundamental rights of "
        "persons. This determination considers both the severity of the possible "
        "harm and the probability of its occurrence. The Act specifically outlines "
        "two main categories of high-risk AI systems: AI Systems Integrated into "
        "Products and Stand-alone High-Risk AI Systems. See Annex III."
    ),
    "gt_04": (
        "An AI system shall be considered high-risk where both of the following "
        "conditions are fulfilled: (a) the AI system is intended to be used as a "
        "safety component of a product, or is itself a product, covered by the "
        "Union harmonisation legislation listed in Annex I; (b) the product is "
        "required to undergo a third-party conformity assessment before being "
        "placed on the market or put into service under that Annex I legislation. "
        "In addition, AI systems referred to in Annex III shall be considered "
        "high-risk."
    ),
    "gt_05": (
        "When interacting with an AI system, natural persons should be informed "
        "that they are interacting with an AI system unless it is obvious. "
        "Deployers of emotion recognition or biometric categorisation systems "
        "should inform natural persons exposed to the system of its operation. "
        "Deployers of an AI system that generates or manipulates text published to "
        "inform the public on matters of public interest shall disclose that the "
        "text has been artificially generated or manipulated. Information should be "
        "provided in a clear and distinguishable manner at the latest at the time "
        "of the first interaction or exposure."
    ),
    "gt_06": (
        "AI systems may be developed for purposes that do not pose significant "
        "risks to health, safety, or fundamental rights. These include: a system "
        "that transforms unstructured data into structured data; one that "
        "classifies incoming documents into categories; one used to detect "
        "duplicates among many applications; one that improves the language used "
        "in documents without changing their substance; one that detects "
        "decision-making patterns or deviations; and one that performs tasks "
        "preparatory to an assessment."
    ),
    "gt_07": (
        "Protection of fundamental rights, including democracy, the rule of law, "
        "environmental protection, health, and safety."
    ),
    "gt_08": (
        "A machine-based system that is designed to operate with varying levels of "
        "autonomy and that may exhibit adaptiveness after deployment, and that, "
        "for explicit or implicit objectives, infers, from the input it receives, "
        "how to generate outputs such as predictions, content, recommendations, or "
        "decisions that can influence physical or virtual environments."
    ),
    "gt_09": (
        "Breaches of provisions concerning high-risk AI systems, including "
        "transparency obligations for providers and deployers, can result in "
        "administrative fines of up to 15,000,000 EUR or 3% of the offender's "
        "total worldwide annual turnover, whichever is higher."
    ),
    "gt_10": (
        "The Provider is a natural or legal person, public authority, agency or "
        "other body that develops an AI system or a general-purpose AI model (or "
        "has one developed) and places it on the market or puts it into service "
        "under its own name or trademark. The Deployer is a natural or legal "
        "person, public authority, agency or other body using an AI system under "
        "its authority, except for personal non-professional activity. The "
        "provider bears primary responsibility for AI Act compliance, especially "
        "for high-risk systems; the deployer uses the system for its intended "
        "purpose."
    ),
    "ng_01": (
        "The criteria for assessing the risk of an AI system under the AI Act include: "
        "intended purpose, context and extent of use, nature and amount of data processed, "
        "system autonomy, likelihood and severity of harm to health/fundamental rights, "
        "risks to vulnerable groups (like children), and availability of legal redress."
    ),
    "ng_02": (
        "Sanctions for violating transparency obligations under Article 50 include "
        "administrative fines of up to 15,000,000 EUR or 3% of the offender's "
        "total worldwide annual turnover for the preceding financial year, whichever is higher. "
        "Penalties must be effective, proportionate, and dissuasive, considering SMEs."
    ),
    "ng_03": (
        "Obligations for deployers of high-risk AI systems include: taking appropriate "
        "technical and organizational measures, using systems in accordance with provided "
        "instructions, monitoring system operation, keeping automatically generated logs for "
        "at least six months, performing a Fundamental Rights Impact Assessment (FRIA), "
        "and informing natural persons exposed to the system."
    ),
    "ng_04": (
        "High-risk AI systems must meet mandatory requirements: establishing a comprehensive "
        "risk management system; ensuring high data quality and governance standards; "
        "preparing detailed technical documentation; maintaining automatic record-keeping (logs); "
        "ensuring transparency and clear instructions; enabling human oversight; and achieving "
        "high robustness, accuracy, and cybersecurity."
    ),
    "ng_05": (
        "Providers of high-risk AI systems must prepare comprehensive technical documentation "
        "before market placement, keep it up-to-date for 10 years, design systems to ensure "
        "transparency, provide clear instructions for use (identity, capabilities, and risks), "
        "and supply all necessary documentation to competent authorities upon a reasoned request."
    ),
    "ng_06": (
        "A conformity assessment consists of procedures to verify and demonstrate compliance "
        "with high-risk requirements. Providers can choose between internal control (Annex VI) "
        "or a quality management system and technical documentation assessment by a notified body "
        "(Annex VII), resulting in a certificate of conformity or assessment certificate."
    ),
    "ng_07": (
        "Systemic risk is a risk specific to the high-impact capabilities of general-purpose "
        "AI models that can propagate at scale across the value chain, causing actual or "
        "foreseeable negative effects on public health, safety, public security, fundamental rights, "
        "or society as a whole."
    ),
    "ng_08": (
        "A general-purpose AI model is an AI model that exhibits significant generality, "
        "is capable of competently performing a wide range of distinct tasks, and can be "
        "integrated into various downstream applications. A general-purpose AI system is built "
        "on such a model and serves a variety of purposes."
    ),
    "ng_09": (
        "A quality management system must include: regulatory compliance strategy; design "
        "control and verification; testing and validation procedures; data management systems "
        "(acquisition, collection, labeling); technical specifications/standards; risk management; "
        "post-market monitoring; and serious incident reporting."
    ),
    "ng_10": (
        " document bias mitigation, providers must ensure data sets are subject to high "
        "governance, including assessing and mitigating biases affecting health, safety, or "
        "fundamental rights. Targeted measures must be documented, and continuous-learning models "
        "must mitigate loops of biased feedback."
    ),
    "gt_11": (
        "Yes. Article 11 requires high-risk systems to have technical documentation. Annex IV "
        "specifies that this documentation must include a general description of the system, "
        "including its architecture and the specifications of required hardware and computing resources."
    ),
    "gt_12": (
        "No, they are not always prohibited. Under Article 5, they are specifically prohibited when "
        "used in the workplace or educational institutions, unless they are installed or used for "
        "medical or safety reasons."
    ),
    "gt_13": (
        "It is not inherently prohibited under Article 5. Whether it is high-risk depends on its "
        "exact classification. While it is not explicitly listed in Annex III as high-risk, if the "
        "transcription system is intended to be used as a medical device (or a safety component of one) "
        "covered by EU harmonisation legislation (Annex I, e.g., the Medical Device Regulation) and "
        "requires a third-party conformity assessment, it is classified as high-risk under Article 6. "
        "Otherwise, basic transcription is minimal/limited risk."
    ),
    "med_01": (
        "Yes, it is high-risk under Article 6 because it is a safety component of a product covered "
        "by Annex I (Medical Devices) and requires third-party conformity assessment. The conformity "
        "assessment must follow the requirements under Article 43."
    ),
    "med_02": (
        "It is not explicitly prohibited unless it uses biometric categorization to deduce protected "
        "traits (Article 5). However, systems used to evaluate or classify natural persons for access "
        "to essential healthcare services or triage are classified as high-risk under Annex III."
    ),
    "med_03": (
        "As a provider of a general-purpose AI model, you must fulfill Article 53 obligations, which "
        "include providing technical documentation, honoring EU copyright law, and publishing a "
        "sufficiently detailed summary of the content used for training the model."
    ),
    "med_04": (
        "Under Article 2, the AI Act does not apply to AI systems or models specifically developed "
        "and put into service for the sole purpose of scientific research and development. Therefore, "
        "pre-market research activities are generally exempt."
    ),
}
