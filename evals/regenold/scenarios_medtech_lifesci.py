"""Fresh MedTech / life-sciences eval set (R109).

The domain Regenold actually serves. These 18 scenarios are DISTINCT from the
``med_01..07`` rows already in ``scenarios_graphrag_benchmark.py`` — they probe
the same real-world fact patterns (SaMD / IVD classification + conformity,
clinical decision support, deployer duties, GPAI on biomedical data, emotion /
biometric edges, the research carve-out, post-market + incident reporting,
substantial modification, penalties) with new wording so the engine cannot be
graded on memorised phrasing.

Each row's ``expected_refs`` are wire-form ("Article N" / "Annex R") and every
one resolves in ``app.data.article_existence.ARTICLE_EXISTENCE`` (validated by
``tests/test_medtech_lifesci_eval.py``). ``expected_keywords`` are the
substantive gold tokens a faithful answer should surface.

Run:
    # Local deterministic (TestClient, no wrapper):
    .venv\\Scripts\\python.exe -m evals.regenold.run_medtech --local --label r109-medtech-local --verbose
    # Live (Claude Max Stage-2 via the production endpoint — the eval rule):
    .venv\\Scripts\\python.exe -m evals.regenold.run_medtech \\
        --endpoint https://<railway>.up.railway.app/api/v1/regenold/eu-ai-act/ask \\
        --api-key $env:P2P_REGENOLD_API_KEY --label r109-medtech-live --verbose
"""
from __future__ import annotations

MEDTECH_SCENARIOS: list[dict] = [
    {
        "id": "mt_01",
        "question": (
            "We build the AI that controls insulin dosing inside an implantable "
            "pump that is a Class III medical device under the MDR. Is the AI "
            "high-risk, and which conformity-assessment route applies?"
        ),
        "expected_refs": ["Article 6", "Article 43", "Annex I"],
        "expected_keywords": [
            "high-risk", "safety component", "third-party conformity assessment",
            "Annex I", "MDR", "Article 43", "notified body",
        ],
        "category": "high_risk_medical_device",
    },
    {
        "id": "mt_02",
        "question": (
            "Our software-as-a-medical-device classifies skin lesions as benign "
            "or malignant from photos and is CE-marked Class IIa requiring a "
            "notified body. How does the AI Act classify it and which assessment "
            "applies?"
        ),
        "expected_refs": ["Article 6", "Article 43", "Annex I", "Annex VII"],
        "expected_keywords": [
            "safety component", "Annex I", "Medical Device Regulation",
            "third-party conformity assessment", "notified body", "high-risk",
        ],
        "category": "samd_classification",
    },
    {
        "id": "mt_03",
        "question": (
            "Our AI interprets results from an in-vitro diagnostic blood analyser "
            "regulated under the IVDR. Is it high-risk and how does the IVDR "
            "conformity assessment interact with the AI Act?"
        ),
        "expected_refs": ["Article 6", "Article 43", "Annex I"],
        "expected_keywords": [
            "in-vitro diagnostic", "IVDR", "Annex I", "safety component",
            "third-party conformity assessment", "high-risk",
        ],
        "category": "ivd_diagnostics",
    },
    {
        "id": "mt_04",
        "question": (
            "We supply a clinical decision support AI that recommends drug "
            "dosages to physicians who keep final prescribing authority. As the "
            "provider of a high-risk system, what human-oversight and "
            "transparency-to-deployer duties must we build in?"
        ),
        "expected_refs": ["Article 13", "Article 14", "Article 16"],
        "expected_keywords": [
            "human oversight", "transparency", "instructions for use",
            "provider", "high-risk",
        ],
        "category": "clinical_decision_support",
    },
    {
        "id": "mt_05",
        "question": (
            "A public hospital deploys a third-party CE-marked AI radiology "
            "triage system. Which obligations fall on the hospital as deployer "
            "rather than on the manufacturer?"
        ),
        "expected_refs": ["Article 26", "Article 27"],
        "expected_keywords": [
            "deployer", "Article 26", "human oversight", "instructions for use",
            "logs", "fundamental rights impact assessment", "Article 27",
        ],
        "category": "deployer_obligations",
    },
    {
        "id": "mt_06",
        "question": (
            "A digital-health startup fine-tunes an open-weights general-purpose "
            "model on clinical notes and ships it to other hospitals. When does "
            "the startup itself become a GPAI provider with Article 53 duties?"
        ),
        "expected_refs": ["Article 25", "Article 53"],
        "expected_keywords": [
            "one-third", "training compute", "new provider", "Article 25",
            "Article 53", "technical documentation", "training-data summary",
        ],
        "category": "gpai_value_chain",
    },
    {
        "id": "mt_07",
        "question": (
            "A wellness app infers a user's stress and mood from their voice "
            "during therapy-style chats. Is this emotion recognition prohibited, "
            "high-risk, or limited-risk?"
        ),
        "expected_refs": ["Article 5", "Annex III", "Article 50"],
        "expected_keywords": [
            "emotion recognition", "Article 5(1)(f)", "workplace",
            "not categorically prohibited", "Annex III", "Article 50", "inform",
        ],
        "category": "borderline_prohibition",
    },
    {
        "id": "mt_08",
        "question": (
            "A research consortium develops an AI model solely to study tumour "
            "genetics and never places it on the market. Does the EU AI Act "
            "apply to that model?"
        ),
        "expected_refs": ["Article 2"],
        "expected_keywords": [
            "Article 2", "scientific research and development", "sole purpose",
            "does not apply",
        ],
        "category": "research_exemption",
    },
    {
        "id": "mt_09",
        "question": (
            "What are the maximum administrative fines if a provider of a "
            "high-risk diagnostic AI breaches its Article 16 provider "
            "obligations, compared with deploying a prohibited Article 5 "
            "practice?"
        ),
        "expected_refs": ["Article 99"],
        "expected_keywords": [
            "Article 99(4)", "15", "3%", "high-risk", "Article 99(3)", "35",
            "7%", "worldwide annual turnover",
        ],
        "category": "penalties",
    },
    {
        "id": "mt_10",
        "question": (
            "Our general-purpose biomedical foundation model was trained with "
            "more than 10^25 FLOPs of compute. What systemic-risk obligations "
            "attach?"
        ),
        "expected_refs": ["Article 51", "Article 55"],
        "expected_keywords": [
            "systemic risk", "10^25", "FLOPs", "Article 55", "model evaluation",
            "adversarial testing", "serious incident",
        ],
        "category": "gpai_systemic",
    },
    {
        "id": "mt_11",
        "question": (
            "We generate synthetic patient-education videos that feature an "
            "AI-generated presenter and AI-produced narration. What labelling "
            "duty applies to this content?"
        ),
        "expected_refs": ["Article 50"],
        "expected_keywords": [
            "Article 50", "artificially generated", "marked", "machine-readable",
            "detectable", "AI-generated",
        ],
        "category": "synthetic_content_labelling",
    },
    {
        "id": "mt_12",
        "question": (
            "We are the provider of a high-risk AI diagnostic that is already on "
            "the market. What post-market monitoring and serious-incident "
            "reporting obligations apply?"
        ),
        "expected_refs": ["Article 72", "Article 73"],
        "expected_keywords": [
            "post-market monitoring", "Article 72", "serious incident",
            "Article 73", "report", "market surveillance",
        ],
        "category": "postmarket_incident",
    },
    {
        "id": "mt_13",
        "question": (
            "A hospital retrains and re-purposes a CE-marked diagnostic AI for a "
            "new intended use. Does the hospital become a provider, and is a "
            "fresh conformity assessment required?"
        ),
        "expected_refs": ["Article 25", "Article 43"],
        "expected_keywords": [
            "substantial modification", "Article 25", "new provider",
            "conformity assessment", "Article 43", "intended purpose",
        ],
        "category": "substantial_modification",
    },
    {
        "id": "mt_14",
        "question": (
            "We train a high-risk oncology-staging AI on genomic and imaging "
            "datasets. What data-governance and data-quality obligations apply "
            "to the training, validation and testing data?"
        ),
        "expected_refs": ["Article 10"],
        "expected_keywords": [
            "data governance", "Article 10", "representative", "relevant",
            "errors", "bias", "training, validation",
        ],
        "category": "data_governance",
    },
    {
        "id": "mt_15",
        "question": (
            "An AI tool flags suspicious cells on pathology slides, but a "
            "pathologist always makes the final diagnosis. Could the Article "
            "6(3) derogation make it not high-risk, and what must the provider "
            "do to rely on it?"
        ),
        "expected_refs": ["Article 6", "Annex III", "Article 49"],
        "expected_keywords": [
            "Article 6(3)", "derogation", "does not replace", "human assessment",
            "profiles natural persons", "document", "register", "Article 49(2)",
        ],
        "category": "high_risk_carveout",
    },
    {
        "id": "mt_16",
        "question": (
            "An emergency department uses AI to triage incoming patients and set "
            "treatment priority. Which risk tier applies and why?"
        ),
        "expected_refs": ["Article 6", "Annex III"],
        "expected_keywords": [
            "emergency", "patient triage", "Annex III", "high-risk",
            "Article 6(2)",
        ],
        "category": "emergency_triage",
    },
    {
        "id": "mt_17",
        "question": (
            "A mental-health support chatbot screens patients for suicide risk "
            "and routes high-risk cases to clinicians. How is it classified and "
            "what transparency duty applies toward the patient?"
        ),
        "expected_refs": ["Article 6", "Annex III", "Article 50"],
        "expected_keywords": [
            "high-risk", "Annex III", "essential", "Article 50", "interact",
            "informed",
        ],
        "category": "mental_health_triage",
    },
    {
        "id": "mt_18",
        "question": (
            "Our high-risk medical AI keeps automatically generated logs. How "
            "long must logs be retained and where is that obligation set out?"
        ),
        "expected_refs": ["Article 12", "Article 19"],
        "expected_keywords": [
            "logs", "automatically", "record-keeping", "Article 12",
            "Article 19", "traceability",
        ],
        "category": "logging_retention",
    },
    # ────────────────────────────────────────────────────────────────────
    # Regenold consultant augmentation (rgn_*) — questions a regulatory-
    # affairs consultancy serving the medical-device / life-sciences
    # industry would actually field for its portfolio: AI Act × MDR/IVDR
    # interplay, SaMD boundaries, clinical research, combination products,
    # hospital deployments, post-market / vigilance overlap, legacy
    # transitions, QMS + registration dual-track, penalties + authorities,
    # and multi-turn consultations (classification → modification →
    # incident). Multi-turn rows carry a ``messages`` history whose final
    # user turn equals ``question``.
    # ────────────────────────────────────────────────────────────────────
    {
        "id": "rgn_01",
        "question": (
            "Our Class IIb infusion pump under the MDR embeds an AI module "
            "that computes and adjusts the dose rate. Which AI Act risk class "
            "applies to that module and through which legal route?"
        ),
        "expected_refs": ["Article 6", "Annex I", "Article 43"],
        "expected_keywords": [
            "safety component", "high-risk", "Annex I", "notified body",
            "conformity assessment",
        ],
        "category": "aiact_mdr_interplay",
    },
    {
        "id": "rgn_02",
        "question": (
            "Can the MDR notified body that certifies our Class IIa "
            "diagnostic software also check the AI Act requirements in one "
            "combined conformity-assessment procedure, or do we need a "
            "separate AI Act assessment?"
        ),
        "expected_refs": ["Article 43", "Annex VII"],
        "expected_keywords": [
            "Article 43", "notified body", "conformity assessment",
            "Medical Device Regulation",
        ],
        "category": "aiact_mdr_interplay",
    },
    {
        "id": "rgn_03",
        "question": (
            "Our Class III device already carries an MDR CE marking. Does the "
            "AI Act require a second, separate CE marking for the embedded "
            "high-risk AI system?"
        ),
        "expected_refs": ["Article 48", "Article 43"],
        "expected_keywords": [
            "CE marking", "affixed", "notified body", "conformity",
        ],
        "category": "ce_marking",
    },
    {
        "id": "rgn_04",
        "question": (
            "Our AI analyses digitised pathology slides to detect carcinoma "
            "and is certified as a Class C in-vitro diagnostic under the "
            "IVDR. How does the AI Act classify it and what does that trigger?"
        ),
        "expected_refs": ["Article 6", "Annex I", "Article 43"],
        "expected_keywords": [
            "in-vitro diagnostic", "high-risk", "Annex I", "safety component",
            "conformity assessment",
        ],
        "category": "ivd_diagnostics",
    },
    {
        "id": "rgn_05",
        "question": (
            "We sell software that uses machine learning to rank genomic "
            "variants by pathogenicity for clinical reporting, regulated as "
            "an IVD under the IVDR with notified-body involvement. Is it "
            "high-risk under the AI Act?"
        ),
        "expected_refs": ["Article 6", "Annex I"],
        "expected_keywords": [
            "high-risk", "Annex I", "in-vitro diagnostic", "safety component",
        ],
        "category": "ivd_diagnostics",
    },
    {
        "id": "rgn_06",
        "question": (
            "Our consumer sleep-coaching app gives lifestyle tips from "
            "wearable data and makes no medical claims, so it is not a "
            "medical device. Where does it sit under the EU AI Act risk "
            "pyramid?"
        ),
        "expected_refs": ["Article 6", "Annex III"],
        "expected_keywords": [
            "minimal", "not high-risk", "Annex III", "intended purpose",
        ],
        "category": "wellness_boundary",
    },
    {
        "id": "rgn_07",
        "question": (
            "Our machine-learning models screen candidate small molecules "
            "purely inside our internal drug-discovery R&D pipeline and are "
            "never placed on the market. Does the EU AI Act apply to them?"
        ),
        "expected_refs": ["Article 2"],
        "expected_keywords": [
            "scientific research and development", "does not apply",
            "Article 2", "placed on the market",
        ],
        "category": "research_carveout",
    },
    {
        "id": "rgn_08",
        "question": (
            "Our biology foundation model was trained with more than 10^25 "
            "FLOPs and we now license it commercially to pharma partners for "
            "many downstream tasks. What does the AI Act demand of us as its "
            "provider?"
        ),
        "expected_refs": ["Article 51", "Article 53", "Article 55"],
        "expected_keywords": [
            "general-purpose", "systemic risk", "10^25", "model evaluation",
            "technical documentation",
        ],
        "category": "gpai_lifesciences",
    },
    {
        "id": "rgn_09",
        "question": (
            "We use an AI tool to adjudicate imaging endpoints inside an "
            "ongoing clinical trial, before any marketing authorisation. Does "
            "the AI Act's pre-market testing carve-out cover this, and what "
            "changes if we move to testing in real-world conditions?"
        ),
        "expected_refs": ["Article 2", "Article 60"],
        "expected_keywords": [
            "research", "testing", "real-world", "Article 60",
            "placing on the market",
        ],
        "category": "clinical_research",
    },
    {
        "id": "rgn_10",
        "question": (
            "Our prefilled auto-injector is a drug-device combination product "
            "whose device part is CE-marked under the MDR, and an embedded AI "
            "modulates injection speed for patient comfort and safety. How is "
            "that AI treated under the AI Act?"
        ),
        "expected_refs": ["Article 6", "Annex I", "Article 43"],
        "expected_keywords": [
            "safety component", "high-risk", "Annex I",
            "conformity assessment",
        ],
        "category": "combination_product",
    },
    {
        "id": "rgn_11",
        "question": (
            "A university hospital governed by public law plans to deploy a "
            "high-risk AI sepsis-prediction system on its wards. Must it "
            "complete a fundamental-rights impact assessment before first "
            "use, and what must that assessment cover?"
        ),
        "expected_refs": ["Article 27", "Article 26"],
        "expected_keywords": [
            "fundamental rights impact assessment", "Article 27", "deployer",
            "before", "risks",
        ],
        "category": "hospital_deployment",
    },
    {
        "id": "rgn_12",
        "question": (
            "When our clinicians use a high-risk AI diagnostic-support tool, "
            "what human-oversight arrangements must the hospital put in "
            "place, and may the clinician disregard or override the AI "
            "output?"
        ),
        "expected_refs": ["Article 14", "Article 26"],
        "expected_keywords": [
            "human oversight", "Article 14", "override", "deployer",
        ],
        "category": "hospital_deployment",
    },
    {
        "id": "rgn_13",
        "question": (
            "Our clinic's appointment and symptom-intake chatbot talks to "
            "patients directly. Must patients be told they are interacting "
            "with an AI system rather than a human, and under which provision?"
        ),
        "expected_refs": ["Article 50"],
        "expected_keywords": [
            "Article 50", "inform", "interacting", "AI system",
        ],
        "category": "hospital_deployment",
    },
    {
        "id": "rgn_14",
        "question": (
            "We already file vigilance reports for our CE-marked AI device "
            "under the MDR. Do we additionally owe serious-incident reports "
            "under the AI Act, or does the medical-device reporting regime "
            "cover it?"
        ),
        "expected_refs": ["Article 73"],
        "expected_keywords": [
            "serious incident", "Article 73", "report",
            "market surveillance",
        ],
        "category": "postmarket_vigilance",
    },
    {
        "id": "rgn_15",
        "question": (
            "Can our existing MDR post-market surveillance plan double as the "
            "AI Act post-market monitoring plan for the same high-risk AI "
            "device, or do we maintain two parallel systems?"
        ),
        "expected_refs": ["Article 72"],
        "expected_keywords": [
            "post-market monitoring", "Article 72", "plan", "integrat",
        ],
        "category": "postmarket_vigilance",
    },
    {
        "id": "rgn_16",
        "question": (
            "Our AI-enabled device was already placed on the market before "
            "the AI Act's high-risk obligations start applying. Do we have to "
            "bring it into compliance retroactively, and what changes that?"
        ),
        "expected_refs": ["Article 111"],
        "expected_keywords": [
            "Article 111", "placed on the market", "significant",
            "before",
        ],
        "category": "legacy_transition",
    },
    {
        "id": "rgn_17",
        "question": (
            "We operate an ISO 13485 quality management system for our device "
            "business. Does the AI Act force us to stand up a second, "
            "separate QMS for our high-risk AI, or can the Article 17 "
            "elements be folded into the existing system?"
        ),
        "expected_refs": ["Article 17"],
        "expected_keywords": [
            "quality management system", "Article 17", "high-risk",
            "post-market monitoring",
        ],
        "category": "qms_integration",
    },
    {
        "id": "rgn_18",
        "question": (
            "We register our devices in EUDAMED. Which AI systems must also "
            "be registered in the EU AI database under the AI Act, and does "
            "an Annex I-route medical-device AI need an entry there?"
        ),
        "expected_refs": ["Article 49", "Article 71"],
        "expected_keywords": [
            "EU database", "Article 49", "register", "Annex III",
        ],
        "category": "registration",
    },
    {
        "id": "rgn_19",
        "question": (
            "As a medical-device manufacturer with a high-risk AI system, "
            "which authority polices our AI Act compliance and what is the "
            "maximum fine if we breach our high-risk obligations?"
        ),
        "expected_refs": ["Article 74", "Article 99"],
        "expected_keywords": [
            "market surveillance", "Article 99", "15", "3%",
        ],
        "category": "penalties_authorities",
    },
    {
        "id": "rgn_mt_01",
        "question": (
            "If we retrain the model next year on new patient data and its "
            "behaviour changes materially, what does that trigger under the "
            "AI Act?"
        ),
        "messages": [
            {
                "role": "user",
                "content": (
                    "We manufacture a CE-marked Class IIb ventilator whose AI "
                    "module automatically adjusts pressure support. Is that "
                    "AI module high-risk under the AI Act?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "Yes. As a safety component of a device that undergoes "
                    "third-party conformity assessment under the MDR, the AI "
                    "module is high-risk under Article 6(1) via Annex I."
                ),
            },
            {
                "role": "user",
                "content": (
                    "If we retrain the model next year on new patient data "
                    "and its behaviour changes materially, what does that "
                    "trigger under the AI Act?"
                ),
            },
        ],
        "expected_refs": ["Article 25", "Article 43"],
        "expected_keywords": [
            "substantial modification", "conformity assessment",
            "Article 43", "provider",
        ],
        "category": "multiturn_modification",
    },
    {
        "id": "rgn_mt_02",
        "question": (
            "Before go-live, do we also need a fundamental-rights impact "
            "assessment, and what must it contain?"
        ),
        "messages": [
            {
                "role": "user",
                "content": (
                    "Our public hospital is preparing to deploy an AI system "
                    "that triages incoming emergency-department patients."
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "Emergency patient-triage AI is high-risk under Article "
                    "6(2) via Annex III point 5(d), and the hospital takes on "
                    "deployer obligations under Article 26."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Before go-live, do we also need a fundamental-rights "
                    "impact assessment, and what must it contain?"
                ),
            },
        ],
        "expected_refs": ["Article 27"],
        "expected_keywords": [
            "fundamental rights impact assessment", "Article 27", "deployer",
            "before",
        ],
        "category": "multiturn_hospital",
    },
    {
        "id": "rgn_mt_03",
        "question": (
            "How quickly must we report that incident and to whom?"
        ),
        "messages": [
            {
                "role": "user",
                "content": (
                    "We provide a high-risk AI app, CE-marked as a medical "
                    "device, that titrates insulin doses for diabetic "
                    "patients."
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "Understood. As a safety component of an MDR-regulated "
                    "device, it is high-risk under Article 6(1), and you "
                    "carry the provider obligations of Article 16."
                ),
            },
            {
                "role": "user",
                "content": (
                    "A malfunction last week caused a severe hypoglycaemic "
                    "episode that put a patient in intensive care. Is that a "
                    "serious incident under the AI Act?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "Yes. Harm to a person's health caused by the system "
                    "falls within the serious-incident definition, engaging "
                    "the Article 73 reporting duty."
                ),
            },
            {
                "role": "user",
                "content": (
                    "How quickly must we report that incident and to whom?"
                ),
            },
        ],
        "expected_refs": ["Article 73"],
        "expected_keywords": [
            "serious incident", "Article 73", "report",
            "market surveillance", "15",
        ],
        "category": "multiturn_incident",
    },
]
