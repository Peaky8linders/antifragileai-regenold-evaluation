"""Fresh MedTech / life-sciences eval set V4.

This dataset tests the intersection of the EU AI Act and Medical Device Regulation (MDR),
In Vitro Diagnostic Regulation (IVDR), General-Purpose AI (GPAI), and clinical use.
"""
from __future__ import annotations

MEDTECH_SCENARIOS_V4: list[dict] = [
    {
        "id": "mv4_01",
        "question": (
            "We are developing an AI-driven robotic surgical assistant designed to execute "
            "autonomous tissue suturing under surgeon supervision. The host robotic platform is a "
            "Class III medical device requiring a notified body conformity assessment under the MDR. "
            "How does the AI Act classify this AI module, and which conformity route applies?"
        ),
        "expected_refs": ["Article 6", "Article 43", "Annex I"],
        "expected_keywords": [
            "high-risk", "safety component", "MDR", "notified body", "conformity assessment"
        ],
        "category": "surgical_robotics_conformity",
    },
    {
        "id": "mv4_02",
        "question": (
            "Our digital health platform uses a machine learning algorithm to analyze smartwatch "
            "ECG data for real-time arrhythmia detection, and is CE-marked as a Class IIb device "
            "under the MDR. Under which AI Act risk tier does this model fall?"
        ),
        "expected_refs": ["Article 6", "Annex I"],
        "expected_keywords": [
            "high-risk", "safety component", "Annex I"
        ],
        "category": "ecg_arrhythmia_samd",
    },
    {
        "id": "mv4_03",
        "question": (
            "We build an AI tool that scans electronic health records to automatically match "
            "patients to active clinical trials based on inclusion criteria. It does not perform "
            "any diagnosis or treatment recommendations. Does this qualify as high-risk per Annex III?"
        ),
        "expected_refs": ["Annex III"],
        "expected_keywords": [
            "not high-risk", "clinical trial"
        ],
        "category": "clinical_trial_matching",
    },
    {
        "id": "mv4_04",
        "question": (
            "Our system is a high-risk medical AI that acts as a safety component for an MDR-regulated "
            "product. Are we required to undergo a separate AI Act conformity assessment in addition to "
            "our MDR assessment?"
        ),
        "expected_refs": ["Article 43"],
        "expected_keywords": [
            "not separate", "integrated", "Article 43"
        ],
        "category": "conformity_integration",
    },
    {
        "id": "mv4_05",
        "question": (
            "We are launching a software-as-a-medical-device (SaMD) that analyzes digital "
            "pathology slides of biopsy tissue to assist pathologists in grading breast cancer. "
            "It requires a Class III certificate under the IVDR. How is this AI categorized "
            "under the AI Act?"
        ),
        "expected_refs": ["Article 6", "Annex I"],
        "expected_keywords": [
            "high-risk", "IVDR", "safety component"
        ],
        "category": "pathology_samd_oncology",
    },
    {
        "id": "mv4_06",
        "question": (
            "A metropolitan hospital deploys a third-party AI software to prioritize "
            "radiology scans in the emergency department, moving critical cases to the top. "
            "Is this considered a high-risk system?"
        ),
        "expected_refs": ["Annex III", "Article 6"],
        "expected_keywords": [
            "high-risk", "emergency", "triage", "Annex III"
        ],
        "category": "emergency_triage",
    },
    {
        "id": "mv4_07",
        "question": (
            "We are developing an AI system for general hospital operations scheduling, managing "
            "staff shifts and optimizing room utilization. Does this system fall under high-risk?"
        ),
        "expected_refs": ["Article 6", "Annex III"],
        "expected_keywords": [
            "not high-risk", "minimal"
        ],
        "category": "hospital_scheduling",
    },
    {
        "id": "mv4_08",
        "question": (
            "We use a biometric emotion recognition system in our workplace to assess employee "
            "engagement during meetings. Is this allowed under the AI Act?"
        ),
        "expected_refs": ["Article 5"],
        "expected_keywords": [
            "prohibited", "banned", "emotion recognition", "workplace"
        ],
        "category": "workplace_emotion_recognition",
    },
    {
        "id": "mv4_09",
        "question": (
            "We want to use an AI model in a psychiatric clinic that infers patients' emotional "
            "states from facial micro-expressions to assist in diagnosing clinical depression. "
            "Is this prohibited?"
        ),
        "expected_refs": ["Article 5", "Article 50", "Annex III"],
        "expected_keywords": [
            "not prohibited", "medical", "safety", "transparency", "Article 50"
        ],
        "category": "clinical_emotion_recognition",
    },
    {
        "id": "mv4_10",
        "question": (
            "We developed a large biology foundation model trained on 10^26 FLOPs of genomic "
            "and proteomic sequence data to predict protein folding. "
            "What obligations apply to us under the GPAI regime?"
        ),
        "expected_refs": ["Article 51", "Article 53", "Article 55"],
        "expected_keywords": [
            "general-purpose", "systemic risk", "10^25", "FLOPs", "Article 55"
        ],
        "category": "gpai_biology_foundation",
    },
    {
        "id": "mv4_11",
        "question": (
            "We act as the EU importer for a US-developed high-risk medical AI system designed "
            "for oncology treatment planning. What are our key obligations before placing it on the market?"
        ),
        "expected_refs": ["Article 23"],
        "expected_keywords": [
            "importer", "CE marking", "conformity assessment", "Article 23"
        ],
        "category": "importer_medtech_obligations",
    },
    {
        "id": "mv4_12",
        "question": (
            "A hospital that has deployed a high-risk cardiac monitoring AI retrains the "
            "neural network on its local patient population, significantly modifying its "
            "clinical performance. Who is responsible for compliance now?"
        ),
        "expected_refs": ["Article 25", "Article 43"],
        "expected_keywords": [
            "substantial modification", "new provider", "Article 25"
        ],
        "category": "substantial_modification_clinical",
    },
]
