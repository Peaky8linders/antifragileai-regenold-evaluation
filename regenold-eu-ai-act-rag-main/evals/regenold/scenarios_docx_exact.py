from __future__ import annotations

GROUND_TRUTH = [
    {
        "id": "docx_exact_q15",
        "question": "Can a hospital use an AI system to sort patients based on their biometric data to determine priority for an experimental clinical trial?",
        "expected_refs": ["Article 5", "Article 6", "Annex III"],
        "expected_keywords": [
            "biometric categorisation", "race", "political opinions", "religious", "philosophical beliefs",
            "sexual orientation", "Annex III", "MDR", "Clinical Trials Regulation"
        ],
        "category": "medtech_triage",
        "notes": "Must evaluate Art 5(1)(g) closed list and whether clinical trials fall under Annex III or just MDR.",
        "paper_refs": [],
        "recital_only": False
    },
    {
        "id": "docx_exact_q16",
        "question": "Our life sciences startup developed a general-purpose AI model trained on massive amounts of genomic data. What transparency obligations apply to us?",
        "expected_refs": ["Article 51", "Article 53", "Article 55"],
        "expected_keywords": [
            "systemic risk", "10^25", "FLOPs", "training data summary", "technical documentation", "copyright policy"
        ],
        "category": "medtech_gpai",
        "notes": "Must include systemic risk checks (Art 51, Art 55).",
        "paper_refs": [],
        "recital_only": False
    },
    {
        "id": "docx_exact_q17",
        "question": "We are a university lab developing an AI model exclusively for scientific research and development into new life science drugs. Does the AI Act apply to our model before it is released to the market?",
        "expected_refs": ["Article 2"],
        "expected_keywords": ["Article 2", "scientific research", "real-world conditions", "testing"],
        "category": "medtech_research",
        "notes": "Must refer to Article 2(6) and 2(8).",
        "paper_refs": [],
        "recital_only": False
    },
    {
        "id": "docx_exact_q18",
        "question": "We are developing a generative AI chatbot that will be deployed on a hospital website to answer general patient queries. What transparency obligations apply?",
        "expected_refs": ["Article 50"],
        "expected_keywords": ["Article 50", "deployer", "provider", "limited risk", "deepfake"],
        "category": "medtech_chatbot",
        "notes": "Must determine it is limited-risk (not high-risk) and identify hospital as deployer.",
        "paper_refs": [],
        "recital_only": False
    },
    {
        "id": "docx_exact_q19",
        "question": "A pharmaceutical company wants to use an AI system to monitor the emotions and stress levels of their manufacturing line workers to improve efficiency. Is this allowed?",
        "expected_refs": ["Article 5"],
        "expected_keywords": ["Article 5", "emotions", "workplace", "medical", "safety", "prohibited"],
        "category": "medtech_emotion",
        "notes": "Must identify Art 5(1)(f) and the medical/safety exception.",
        "paper_refs": [],
        "recital_only": False
    },
    {
        "id": "docx_exact_q20",
        "question": "Is an AI system intended to be used as a safety component in robotic surgery considered high-risk under the AI Act?",
        "expected_refs": ["Article 6", "Article 14", "Article 72", "Annex I"],
        "expected_keywords": ["Article 14", "human oversight", "Article 72", "post-market surveillance", "MDR", "Article 83", "Class IIb", "Class III"],
        "category": "medtech_robotic_surgery",
        "notes": "Must include Art 14 oversight and Art 72 / MDR Art 83 post-market surveillance.",
        "paper_refs": [],
        "recital_only": False
    }
]

NO_GROUND_TRUTH = []
