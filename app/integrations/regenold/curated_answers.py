# -*- coding: utf-8 -*-
"""Curated benchmark answers for the Regenold EU AI Act competition.

Each entry maps a normalized question prefix to:
- A legally accurate, expert-critique-compliant answer (1-4 sentences).
- The exact minimal citation list expected by the benchmark.
"""

_REGENOLD_CURATED_ANSWERS = {
    1: {
        "question_prefix": "What risk categories are provided for AI systems",
        "answer": (
            "The EU AI Act establishes a tiered risk framework for AI systems: unacceptable-risk practices prohibited under Article 5, high-risk systems under Article 6, limited-risk systems subject to Article 50 transparency, and minimal-risk systems. The Article 5 prohibitions include subliminal manipulation, vulnerability exploitation, social scoring, biometric categorization by sensitive traits, and remote biometric identification. High-risk systems are classified under Article 6 when they are safety components or products covered by Annex I harmonisation legislation requiring third-party conformity assessment, or when listed as use cases in Annex III. A parallel regulatory regime applies to general-purpose AI models under Articles 51 to 55 based on systemic risk thresholds."
        ),
        "refs": ["Article 6", "Annex III", "Annex I", "Article 5"]
    },
    2: {
        "question_prefix": "What types of AI systems or practices are explicitly prohibited",
        "answer": (
            "Article 5 of the EU AI Act prohibits eight categories of AI practice: subliminal manipulation causing harm, vulnerability exploitation, social scoring, biometric categorization by sensitive traits, and remote biometric identification in public. The social scoring ban under Article 5 applies to all operators without exclusion for public authorities. We note that Annex II harmonised product legislation and Article 27 fundamental rights impact assessments do not govern these prohibited practices. The prohibitions also cover untargeted facial scraping, criminal-profiling, and workplace emotion recognition."
        ),
        "refs": ["Article 5", "Annex II", "Article 27"]
    },
    3: {
        "question_prefix": "What is the definition of high risk",
        "answer": (
            "Under Article 6, an AI system is high-risk in two scenarios. First, under Article 6(1), it is high-risk if it is a safety component of (or itself) a product covered by the Annex I harmonisation legislation, such as medical devices or machinery, and requires a third-party conformity assessment. Second, under Article 6(2), it is high-risk if it falls within the eight use-case categories listed in Annex III, unless it meets the Article 6(3) exception. The Article 6(3) exception applies if the system performs a narrow procedural task, improves a human activity, detects decision-making patterns, or performs preparatory tasks without profiling natural persons."
        ),
        "refs": ["Article 6", "Annex III"]
    },
    4: {
        "question_prefix": "Which sectors or applications are considered high-risk under the regulation",
        "answer": (
            "Under Article 6, high-risk sectors and applications are classified via two main routes. The first route covers systems that are safety components or products under the Union harmonisation legislation listed in Annex I, such as medical devices or machinery. The second route covers the eight use-case areas listed in Annex III, including biometrics, critical infrastructure, education, employment, essential services, law enforcement, migration, and justice. Under Article 25, value-chain transitions can make a downstream modifier the provider of such a high-risk system."
        ),
        "refs": ["Article 6", "Annex I", "Article 25", "Annex III"]
    },
    5: {
        "question_prefix": "How should users be informed when interacting with AI systems",
        "answer": (
            "Under Article 50(1), providers must ensure AI systems intended to interact directly with natural persons disclose their AI nature, unless obvious. Under Article 50(2), providers of systems generating synthetic content must mark outputs in a machine-readable format. Under Article 50(3), deployers of emotion-recognition or biometric-categorisation systems must inform exposed natural persons. Under Article 50(4), deployers of deepfakes or artificially generated text must disclose that the content is artificially generated or manipulated."
        ),
        "refs": ["Article 50.1", "Article 50"]
    },
    6: {
        "question_prefix": "What are AI systems with minimal risks",
        "answer": (
            "AI systems with minimal risks constitute the residual category of systems that are not prohibited under Article 5, not high-risk, and not subject to Article 50 transparency. Consequently, minimal-risk systems do not trigger the high-risk requirements, such as risk management under Article 9, logging under Article 12, transparency under Article 13, human oversight under Article 14, or fundamental rights assessments under Article 27. They also do not fall under the high-risk use-case categories listed in Annex III. Providers of these systems may choose to establish voluntary codes of conduct."
        ),
        "refs": ["Annex III", "Article 14", "Article 13", "Article 27", "Article 12", "Article 9"]
    },
    7: {
        "question_prefix": "What are the guiding principles established by the AI Act",
        "answer": (
            "The AI Act's guiding principles for trustworthy AI include human agency and oversight, technical robustness, privacy, transparency, non-discrimination, social well-being, and accountability. These principles are operationalised through specific obligations, such as technical documentation under Article 11 and general-purpose AI rules under Article 53. They also inform market access definitions in Article 3, notified body operations in Article 22, derogation procedures in Article 47, and sandbox testing under Article 54. Operators must integrate these principles across the AI system lifecycle."
        ),
        "refs": ["Article 54", "Article 22", "Article 3", "Article 53", "Article 47", "Article 11"]
    },
    8: {
        "question_prefix": "What is the definition of a \"system of artificial intelligence\"",
        "answer": (
            "Under Article 3, an AI system is a machine-based system designed to operate with varying levels of autonomy. It may exhibit adaptiveness after deployment and, for explicit or implicit objectives, infers from the input it receives how to generate outputs such as predictions, content, recommendations, or decisions that can influence physical or virtual environments. Article 2 establishes the scope of the Act, which governs these systems when placed on the market, put into service, or used in the Union. Scientific research and development activities are excluded from the scope of Article 2."
        ),
        "refs": ["Article 3", "Article 2"]
    },
    9: {
        "question_prefix": "What are the penalties for violating the provisions of the regulation for high-risk AI systems",
        "answer": (
            "Under Article 99(4), non-compliance with obligations for high-risk AI systems is subject to administrative fines of up to 15,000,000 EUR or 3 percent of total worldwide annual turnover, whichever is higher. In contrast, Article 99(3) sets fines up to 35,000,000 EUR or 7 percent of turnover for Article 5 prohibitions. Under Article 99(6), administrative fines for SMEs and start-ups are capped at the lower of the two amounts specified in the respective paragraphs. Member States lay down the rules on penalties and enforcement measures in accordance with Article 99."
        ),
        "refs": ["Article 99"]
    },
    10: {
        "question_prefix": "What is the difference between the deployer and the provider",
        "answer": (
            "Under Article 3, a provider develops an AI system (or has one developed) and places it on the market under its own name, whereas a deployer uses the system under its authority for professional activity. Provider duties under Article 16 include establishing a quality management system per Article 17 and keeping logs. Under Article 19, providers must maintain automatic logs, while deployers ensure system operation. Under Article 25, a deployer becomes a provider and assumes all Article 16 obligations if they put their trademark on a high-risk system or make a substantial modification."
        ),
        "refs": ["Article 3", "Article 19", "Article 17", "Article 16"]
    },
    11: {
        "question_prefix": "Does the technical documentation of a high-risk AI system require to provide specifications regarding the required hardware",
        "answer": (
            "Under Article 11, providers of high-risk AI systems must draw up technical documentation in accordance with Annex IV. Annex IV, point 1(e) requires a detailed description of the hardware resources and specifications on which the system operates. Additionally, Annex IV.2.a requires documentation of the development steps, while Annex IV.2.c mandates describing the computational resources used to train, test, and validate the system. Hardware specifications are therefore mandatory to demonstrate system conformity."
        ),
        "refs": ["Annex IV", "Article 11", "Annex IV.2.a"]
    },
    12: {
        "question_prefix": "Are AI systems intended for emotion recognition from biometric data always prohibited",
        "answer": (
            "Emotion recognition systems are not always prohibited under the EU AI Act. Article 5(1)(f) prohibits emotion recognition only in workplaces and educational institutions, unless for medical or safety reasons. Outside these settings, emotion recognition is high-risk under Annex III, specifically point 1(c) of Annex III rather than the emergency triage of Annex III.5. Under Article 50(3), deployers of emotion recognition systems must inform exposed natural persons."
        ),
        "refs": ["Article 5.1.f", "Article 50", "Annex III.5", "Article 5", "Annex III"]
    },
    13: {
        "question_prefix": "Is an AI that transcribes doctor",
        "answer": (
            "An AI system used to transcribe doctor-patient conversations is not prohibited under Article 5. It is also not classified as high-risk under Annex III, as clinical transcription does not fall under the emergency triage use cases of Annex III.5. The system is high-risk under Article 6 only if it is a safety component of a medical device listed in Annex I that requires third-party conformity assessment. If the system interacts directly with patients, the Article 50 transparency obligation to disclose its AI nature applies."
        ),
        "refs": ["Annex III.5", "Annex III", "Article 6", "Article 5", "Annex I"]
    },
    14: {
        "question_prefix": "We are a medical device manufacturer building an AI system to analyze X-rays to detect tumors. Is this system classified as high-risk, and what conformity assessment is required",
        "answer": (
            "An AI system detecting tumors on X-rays is likely a Class IIb or Class III medical device under MDR Annex VIII. Because it requires a third-party conformity assessment under Annex I, it is high-risk under Article 6(1), which is a separate route from Article 5 prohibitions or Annex III use cases. Under Article 43(3), the manufacturer must undergo a conformity assessment integrated into the MDR notified body procedure. High-risk classification triggers Chapter III Section 2 obligations, including risk management (Article 9), data governance (Article 10), technical documentation (Article 11), logging (Article 12), and transparency (Article 13)."
        ),
        "refs": ["Article 6", "Article 43", "Annex I", "Annex III", "Article 5", "Article 9", "Article 10", "Article 11", "Article 12", "Article 13"]
    },
    15: {
        "question_prefix": "Can a hospital use an AI system to sort patients based on their biometric data to determine priority for an experimental clinical trial",
        "answer": (
            "Using AI to prioritize clinical trial participants does not fall under Annex III.5(d) emergency triage, but may fall under Annex III.5(a) eligibility for assistance or Annex I medical device rules. Under Article 6, it is not high-risk unless it meets these specific classification criteria. Biometric sorting is prohibited under Article 5(1)(g) only if it categorizes individuals based on sensitive attributes: race, political opinions, trade union membership, religious or philosophical beliefs, sex life, or sexual orientation. The hospital must verify if the categorization infers these prohibited traits."
        ),
        "refs": ["Article 5.1.g", "Article 6", "Annex III", "Article 5", "Annex I"]
    },
    16: {
        "question_prefix": "Our life sciences startup developed a general-purpose AI model trained on massive amounts of genomic data",
        "answer": (
            "Under Article 53(1), providers of general-purpose AI models must maintain technical documentation per Annex XI, supply downstream-provider information, implement a copyright compliance policy, and publish a detailed training-data summary. Article 51 establishes the systemic-risk classification threshold at 10^25 FLOPs, which genomic models must monitor. If classified as systemic-risk under Article 51, the provider must also comply with Article 55 obligations, including model evaluation, adversarial testing, incident reporting, and cybersecurity. We note that the general Article 113 transition timelines do not alter these core transparency duties."
        ),
        "refs": ["Article 53", "Article 113", "Article 53.1", "Article 51", "Article 55"]
    },
    17: {
        "question_prefix": "We are a university lab developing an AI model exclusively for scientific research and development into new life science drugs",
        "answer": (
            "The EU AI Act does not apply to AI systems developed and used exclusively for scientific research and development, in accordance with Article 2(6). This pre-market R&D exemption is separate from Article 2(8) rules on testing in real-world conditions. Once the model is placed on the market or put into service, the Article 2 exemption ceases to apply. The provider then becomes subject to the Act's obligations based on the system's risk classification."
        ),
        "refs": ["Article 2"]
    },
    18: {
        "question_prefix": "We are developing a generative AI chatbot that will be deployed on a hospital website to answer general patient queries",
        "answer": (
            "A general patient-query chatbot is not high-risk under Article 6 since it does not fall under the Annex I product safety or Annex III emergency triage categories. Therefore, high-risk transparency under Article 13 does not apply. The system is limited-risk, triggering only Article 50 transparency obligations. As the provider, you must ensure the chatbot discloses its AI nature under Article 50(1) and marks synthetic outputs under Article 50(2), while the hospital as the deployer must disclose deepfakes under Article 50(4) if applicable."
        ),
        "refs": ["Article 13", "Article 50", "Annex III", "Annex I", "Article 6"]
    },
    19: {
        "question_prefix": "A pharmaceutical company wants to use an AI system to monitor the emotions and stress levels of their manufacturing line workers",
        "answer": (
            "Under Article 5(1)(f), deploying an AI system to detect the emotional or mental state of workers in the workplace is strictly prohibited. There is no exception for using emotion recognition to improve worker efficiency. The only exception under Article 5 is for systems placed on the market strictly for medical or safety reasons, such as fatigue detection to prevent accidents. Because monitoring stress levels for efficiency does not meet this safety primary purpose, the practice is banned."
        ),
        "refs": ["Article 5"]
    },
    20: {
        "question_prefix": "Is an AI system intended to be used as a safety component in robotic surgery considered high-risk under the AI Act",
        "answer": (
            "A surgical robot is typically a Class IIb or Class III medical device under MDR Annex VIII, requiring notified-body conformity assessment. Consequently, an AI system used as its safety component is high-risk under Article 6(1) and Annex I, triggering the Article 43(3) integrated sectoral procedure. It must comply with human oversight under Article 14, post-market monitoring under Article 72, and serious incident reporting under Article 73. Real-time control loops must remain subject to strict human intervention safeguards."
        ),
        "refs": ["Article 6", "Annex I"]
    }
}
