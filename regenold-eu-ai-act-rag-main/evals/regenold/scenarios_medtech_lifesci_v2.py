"""Fresh MedTech / life-sciences eval set V2 (R116).

A second, fully-distinct probe set for the domain Regenold actually serves.
Every row is NEW wording AND a NEW fact pattern relative to:
  * ``scenarios_medtech_lifesci.MEDTECH_SCENARIOS`` (R109, 40 rows), and
  * the ``med_01..07`` rows in ``scenarios_graphrag_benchmark.py``.

Coverage spans the full risk pyramid (prohibited / borderline / high-risk /
limited / minimal), the value chain Regenold's existing medtech set under-probed
(importer Art. 23, authorised representative Art. 22, distributor Art. 24), the
GPAI regime for life-sciences foundation models (Art. 51/53/55), cross-framework
overlap (GDPR special-category data Art. 10, cybersecurity Art. 15 with NIS2/CRA),
and the core HRAIS obligations under fresh clinical scenarios. ``mv2_03`` exercises
the R116 medical-transcription vocab (ambient clinical documentation / AI scribe).

Each row's ``expected_refs`` are wire-form ("Article N" / "Annex R") and every one
resolves in ``app.data.article_existence.ARTICLE_EXISTENCE`` (validated by
``tests/test_medtech_lifesci_v2_eval.py``). ``expected_keywords`` are the
substantive gold tokens a faithful answer should surface.

Run:
    # Local deterministic (TestClient, no wrapper):
    .venv\\Scripts\\python.exe -m evals.regenold.run_medtech --local --v2 \\
        --label r116-medtech-v2-local --verbose
    # Live (Claude Max Stage-2 via the production endpoint — the eval rule):
    .venv\\Scripts\\python.exe -m evals.regenold.run_medtech --v2 \\
        --endpoint https://<railway>.up.railway.app/api/v1/regenold/eu-ai-act/ask \\
        --api-key $env:P2P_REGENOLD_API_KEY --label r116-medtech-v2-live --verbose
"""
from __future__ import annotations

MEDTECH_SCENARIOS_V2: list[dict] = [
    # ── High-risk software-as-a-medical-device (SaMD) ────────────────────
    {
        "id": "mv2_01",
        "question": (
            "We build computer-aided detection AI that flags suspicious lung "
            "nodules on CT scans for radiologists; it is a Class IIb medical "
            "device under the MDR. How does the AI Act classify it?"
        ),
        "expected_refs": ["Article 6", "Annex I"],
        "expected_keywords": [
            "high-risk", "safety component", "Annex I", "Medical Device Regulation",
            "third-party conformity assessment",
        ],
        "category": "samd_radiology_cade",
    },
    {
        "id": "mv2_02",
        "question": (
            "Our prescription digital therapeutic treats major depression and is "
            "CE-marked as a Class IIa medical device. Is the AI inside it high-risk "
            "under the AI Act, and what conformity route applies?"
        ),
        "expected_refs": ["Article 6", "Annex I", "Article 43"],
        "expected_keywords": [
            "high-risk", "safety component", "Annex I", "Article 43",
            "notified body", "conformity assessment",
        ],
        "category": "digital_therapeutic",
    },
    {
        "id": "mv2_03",
        "question": (
            "Our ambient clinical documentation tool is an AI medical scribe that "
            "transcribes the doctor-patient consultation into draft notes, with no "
            "diagnostic or treatment function. How is it classified and what "
            "transparency duty applies?"
        ),
        "expected_refs": ["Article 50"],
        "expected_keywords": [
            "not high-risk", "safety component", "transparency", "Article 50",
            "inform",
        ],
        "category": "clinical_scribe_transparency",
    },
    {
        "id": "mv2_04",
        "question": (
            "Our smartwatch app detects atrial fibrillation from PPG and is "
            "regulated as a medical device with a notified-body certificate. Which "
            "AI Act risk tier does the arrhythmia-detection model fall into?"
        ),
        "expected_refs": ["Article 6", "Annex I"],
        "expected_keywords": [
            "high-risk", "safety component", "Annex I", "medical device",
            "conformity assessment",
        ],
        "category": "wearable_samd",
    },
    {
        "id": "mv2_05",
        "question": (
            "Our AI ranks IVF embryos by predicted implantation potential and is "
            "placed on the market as an in-vitro diagnostic device under the IVDR. "
            "Is it high-risk under the AI Act?"
        ),
        "expected_refs": ["Article 6", "Annex I"],
        "expected_keywords": [
            "high-risk", "in-vitro diagnostic", "safety component", "Annex I",
        ],
        "category": "ivd_embryo_selection",
    },
    {
        "id": "mv2_06",
        "question": (
            "Our pharmacovigilance AI mines real-world reports to surface possible "
            "adverse drug reactions for our pharmacovigilance team; it is not a "
            "medical device and makes no clinical decision. Where does it sit in "
            "the AI Act risk pyramid?"
        ),
        "expected_refs": ["Article 6", "Annex III"],
        "expected_keywords": [
            "not high-risk", "Annex III", "not listed", "minimal", "intended purpose",
        ],
        "category": "pharmacovigilance_boundary",
    },
    # ── Value chain — importer / authorised representative / distributor ─
    {
        "id": "mv2_07",
        "question": (
            "We import a US manufacturer's CE-marked high-risk diagnostic AI into "
            "the EU and place it on the Union market. What must we verify before "
            "doing so, as the importer?"
        ),
        "expected_refs": ["Article 23"],
        "expected_keywords": [
            "importer", "conformity assessment", "technical documentation",
            "CE marking", "instructions for use",
        ],
        "category": "importer_obligations",
    },
    {
        "id": "mv2_08",
        "question": (
            "A Japanese manufacturer of a high-risk surgical-planning AI has no EU "
            "establishment. Must it appoint someone in the Union before placing the "
            "system on the market, and what is that party's role?"
        ),
        "expected_refs": ["Article 22"],
        "expected_keywords": [
            "authorised representative", "established", "mandate",
            "technical documentation", "before",
        ],
        "category": "authorised_representative",
    },
    {
        "id": "mv2_09",
        "question": (
            "As a distributor reselling a CE-marked high-risk AI radiology tool to "
            "EU hospitals, what compliance checks must we make before making it "
            "available on the market?"
        ),
        "expected_refs": ["Article 24"],
        "expected_keywords": [
            "distributor", "CE marking", "instructions for use",
            "before making it available", "conformity",
        ],
        "category": "distributor_obligations",
    },
    # ── GPAI in life sciences ────────────────────────────────────────────
    {
        "id": "mv2_10",
        "question": (
            "We release an open-weights general-purpose protein-structure-"
            "prediction model trained well below 10^25 FLOPs of compute. What "
            "general-purpose AI obligations apply to us as its provider?"
        ),
        "expected_refs": ["Article 53"],
        "expected_keywords": [
            "general-purpose", "technical documentation", "training-data summary",
            "Article 53", "copyright",
        ],
        "category": "gpai_standard",
    },
    {
        "id": "mv2_11",
        "question": (
            "Our general-purpose drug-discovery foundation model was trained with "
            "more than 10^25 FLOPs and is licensed broadly to pharma. What "
            "systemic-risk obligations attach to it?"
        ),
        "expected_refs": ["Article 51", "Article 55"],
        "expected_keywords": [
            "systemic risk", "10^25", "FLOPs", "Article 55", "model evaluation",
            "adversarial testing", "serious incident",
        ],
        "category": "gpai_systemic",
    },
    # ── Cross-framework overlap ──────────────────────────────────────────
    {
        "id": "mv2_12",
        "question": (
            "We train a high-risk diagnostic AI on patients' genetic and health "
            "data, which are special categories of personal data. What does the AI "
            "Act allow and require for processing such data to detect and correct "
            "bias?"
        ),
        "expected_refs": ["Article 10"],
        "expected_keywords": [
            "data governance", "Article 10", "special categories",
            "bias", "strictly necessary",
        ],
        "category": "special_category_data",
    },
    {
        "id": "mv2_13",
        "question": (
            "For our high-risk AI infusion-management system, what does the AI Act "
            "require on accuracy, robustness and cybersecurity, and how does that "
            "sit alongside the Cyber Resilience Act?"
        ),
        "expected_refs": ["Article 15"],
        "expected_keywords": [
            "accuracy", "robustness", "cybersecurity", "Article 15",
            "resilience",
        ],
        "category": "accuracy_robustness_security",
    },
    # ── Prohibited / borderline prohibition ──────────────────────────────
    {
        "id": "mv2_14",
        "question": (
            "A hospital wants AI cameras to read patients' emotions in the waiting "
            "room and bump distressed-looking people up the queue. Is emotion "
            "recognition in a healthcare setting outright prohibited, or something "
            "else?"
        ),
        "expected_refs": ["Article 5", "Annex III", "Article 50"],
        "expected_keywords": [
            "emotion recognition", "not", "workplace", "education",
            "not prohibited", "Article 50",
        ],
        "category": "borderline_emotion_recognition",
    },
    {
        "id": "mv2_15",
        "question": (
            "A regional health authority proposes scoring patients on their "
            "general social behaviour and lifestyle to decide who gets scarce "
            "treatment first. Is that allowed under the AI Act?"
        ),
        "expected_refs": ["Article 5"],
        "expected_keywords": [
            "prohibited", "social scoring", "Article 5", "unfavourable treatment",
        ],
        "category": "prohibited_social_scoring",
    },
    # ── HRAIS obligation depth — fresh clinical scenarios ────────────────
    {
        "id": "mv2_16",
        "question": (
            "When clinicians rely on our high-risk AI sepsis-prediction tool, what "
            "human-oversight measures must be designed in so a doctor can "
            "understand, override or disregard its output?"
        ),
        "expected_refs": ["Article 14"],
        "expected_keywords": [
            "human oversight", "Article 14", "override", "disregard",
            "automation bias",
        ],
        "category": "human_oversight",
    },
    {
        "id": "mv2_17",
        "question": (
            "Our high-risk AI for image-guided surgery records automatic event "
            "logs. What does the AI Act require about generating and keeping those "
            "logs?"
        ),
        "expected_refs": ["Article 12", "Article 19"],
        "expected_keywords": [
            "logs", "automatically", "record-keeping", "Article 12",
            "Article 19", "traceability",
        ],
        "category": "logging_recordkeeping",
    },
    {
        "id": "mv2_18",
        "question": (
            "What technical documentation must we draw up and keep for a high-risk "
            "AI diagnostic before placing it on the market, and where is that set "
            "out?"
        ),
        "expected_refs": ["Article 11", "Annex IV"],
        "expected_keywords": [
            "technical documentation", "Article 11", "Annex IV",
            "before", "drawn up",
        ],
        "category": "technical_documentation",
    },
    {
        "id": "mv2_19",
        "question": (
            "Once our high-risk AI radiology product is in clinical use across "
            "hospitals, what does the AI Act require us to do to keep watching its "
            "performance and to report serious incidents?"
        ),
        "expected_refs": ["Article 72", "Article 73"],
        "expected_keywords": [
            "post-market monitoring", "Article 72", "serious incident",
            "Article 73", "report", "market surveillance",
        ],
        "category": "postmarket_incident",
    },
    {
        "id": "mv2_20",
        "question": (
            "A hospital changes the intended purpose of a CE-marked AI tool from "
            "triage support to autonomous diagnosis. Does that make the hospital a "
            "provider and require a fresh conformity assessment?"
        ),
        "expected_refs": ["Article 25", "Article 43"],
        "expected_keywords": [
            "substantial modification", "intended purpose", "Article 25",
            "new provider", "conformity assessment", "Article 43",
        ],
        "category": "substantial_modification",
    },
    {
        "id": "mv2_21",
        "question": (
            "Our lab trains an AI model purely to investigate a disease mechanism "
            "for publication, and we never place it on the market or put it into "
            "service. Does the AI Act apply to that activity?"
        ),
        "expected_refs": ["Article 2"],
        "expected_keywords": [
            "scientific research and development", "sole purpose", "Article 2",
            "does not apply", "placed on the market",
        ],
        "category": "research_carveout",
    },
    {
        "id": "mv2_22",
        "question": (
            "What is the maximum administrative fine if a provider of a high-risk "
            "medical AI breaches its obligations, and how does that compare with "
            "deploying a prohibited practice?"
        ),
        "expected_refs": ["Article 99"],
        "expected_keywords": [
            "Article 99", "15", "3%", "35", "7%", "worldwide annual turnover",
        ],
        "category": "penalties",
    },
    {
        "id": "mv2_23",
        "question": (
            "Before we place our high-risk AI diagnostic on the EU market, must we "
            "register it anywhere, and in which database?"
        ),
        "expected_refs": ["Article 49", "Article 71"],
        "expected_keywords": [
            "register", "EU database", "Article 49", "Article 71",
            "before placing on the market",
        ],
        "category": "eu_database_registration",
    },
    {
        "id": "mv2_24",
        "question": (
            "A private clinic that provides publicly-funded healthcare services "
            "plans to deploy a high-risk AI triage system. Must it carry out a "
            "fundamental-rights impact assessment, and what else falls on it as "
            "deployer?"
        ),
        "expected_refs": ["Article 27", "Article 26"],
        "expected_keywords": [
            "fundamental rights impact assessment", "Article 27", "deployer",
            "Article 26", "before",
        ],
        "category": "fria_deployer",
    },
    # ── Multi-turn consultations (final user turn == ``question``) ────────
    {
        "id": "mv2_mt_01",
        "question": (
            "If we then fine-tune that model on our own clinical corpus and ship "
            "it under our own brand, do we become its provider?"
        ),
        "messages": [
            {
                "role": "user",
                "content": (
                    "We license a third party's general-purpose medical language "
                    "model and run it unchanged inside our hospital. Are we a "
                    "GPAI provider?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "No. Running a general-purpose AI model unchanged makes you a "
                    "deployer, not its provider; the original developer remains the "
                    "GPAI provider under Articles 51 to 55."
                ),
            },
            {
                "role": "user",
                "content": (
                    "If we then fine-tune that model on our own clinical corpus and "
                    "ship it under our own brand, do we become its provider?"
                ),
            },
        ],
        "expected_refs": ["Article 25", "Article 53"],
        "expected_keywords": [
            "new provider", "Article 25", "Article 53", "one-third",
            "training compute", "substantial modification",
        ],
        "category": "multiturn_gpai_value_chain",
    },
    {
        "id": "mv2_mt_02",
        "question": (
            "Concretely, may our radiologist override or ignore the AI's output, "
            "and what must we put in place to make that real?"
        ),
        "messages": [
            {
                "role": "user",
                "content": (
                    "Our hospital is deploying a third-party CE-marked high-risk AI "
                    "that prioritises radiology worklists. What are our duties as "
                    "the deployer?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "As deployer you must use the system per its instructions for "
                    "use, ensure human oversight by competent staff, keep the "
                    "automatically generated logs, and monitor its operation under "
                    "Article 26."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Concretely, may our radiologist override or ignore the AI's "
                    "output, and what must we put in place to make that real?"
                ),
            },
        ],
        "expected_refs": ["Article 14", "Article 26"],
        "expected_keywords": [
            "human oversight", "Article 14", "override", "deployer", "Article 26",
        ],
        "category": "multiturn_human_oversight",
    },
]
