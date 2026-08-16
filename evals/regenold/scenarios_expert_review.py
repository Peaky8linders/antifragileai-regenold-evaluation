"""Expert-review probe set — the 20 questions from the Antifragile AI live
review, gold derived from the EU AI Act expert's critique.

Source: "Antifragile AI Review (live answers + expert EU AI Act critique)" —
20 questions (Q1-Q20) each carrying a live answer, its citations, and an
expert EU AI Act lawyer's verdict on what was wrong, missing, or mis-cited.
The gold here is NOT the live answer (which the review shows is often wrong);
it is the EXPERT'S correct answer, condensed:

* ``expected_refs`` — the provisions the CORRECT answer must engage with,
  taken from the review's "correct on substance / correct response would
  draw on / the substantively correct answer is" lines. Where the review
  says a citation was IRRELEVANT (e.g. Q2's Annex II / Art. 27; Q4's Art.
  25), it is deliberately excluded from gold — an answer that repeats the
  review's flagged error must score as wrong.
* ``gold_answer`` — the regulator-voice correct answer per the expert,
  grounded in the review's critique.

Two rows are article-less by the Act's own structure and flagged in
``notes``: Q6 minimal-risk is the residual category (the correct answer
names the boundaries rather than a governing article), and Q7 guiding
principles live in Recital 27 (recital-only gold — the wire never cites
recitals, so these rows carry keyword gold + gold_answer and the
answer_correctness judge axis grounds on the gold_answer).

Schema matches ``_norm_single`` (probe_set): id, question, expected_refs,
expected_keywords, gold_answer, category.
"""

from __future__ import annotations

GROUND_TRUTH: list[dict] = [
    {
        "id": "xr_01",
        "question": "What risk categories are provided for AI systems?",
        "expected_refs": ["Article 5", "Article 6", "Annex I", "Annex III", "Article 51"],
        "expected_keywords": ["risk categories", "unacceptable", "high-risk"],
        "category": "expert_review",
        "gold_answer": (
            "The AI Act establishes a tiered risk framework: an unacceptable-risk tier of "
            "prohibited practices under Article 5 (which bans eight practices outright, "
            "including subliminal manipulation causing significant harm, exploitation of "
            "vulnerabilities, social scoring, biometric categorisation by sensitive "
            "attributes, and real-time remote biometric identification in public spaces), "
            "a high-risk tier under Article 6 via Annex I (safety components of products "
            "under harmonisation legislation) and Annex III (listed use cases), a limited-risk "
            "tier under Article 50 transparency, a minimal-risk residual, and a parallel "
            "GPAI regime under Articles 51-55."
        ),
    },
    {
        "id": "xr_02",
        "question": "What types of AI systems or practices are explicitly prohibited by the AI Act?",
        "expected_refs": ["Article 5"],
        "expected_keywords": ["prohibited", "subliminal", "social scoring"],
        "category": "expert_review",
        "gold_answer": (
            "Article 5(1) prohibits eight categories of AI practice: (a) subliminal, "
            "manipulative or deceptive techniques causing significant harm; (b) exploitation "
            "of vulnerabilities due to age, disability or socio-economic situation; (c) social "
            "scoring by public authorities (no public-authority exclusion — the prohibition "
            "is unqualified); (d) individual criminal-risk assessment based solely on "
            "profiling; (e) indiscriminate scraping of facial images from the internet or "
            "CCTV; (f) emotion recognition in workplaces and educational institutions, with a "
            "narrow medical/safety carve-out; (g) biometric categorisation inferring sensitive "
            "attributes (race, political opinions, religious beliefs, sexual orientation, "
            "etc.) from a closed list; (h) real-time remote biometric identification in "
            "publicly accessible spaces for law enforcement, within exhaustively defined "
            "exceptions."
        ),
    },
    {
        "id": "xr_03",
        "question": "What is the definition of high risk?",
        "expected_refs": ["Article 6", "Annex I", "Annex III"],
        "expected_keywords": ["high-risk", "safety component", "Annex III"],
        "category": "expert_review",
        "gold_answer": (
            "Under Article 6 an AI system is high-risk by two routes: (1) it is intended as a "
            "safety component of a product covered by the Union harmonisation legislation in "
            "Annex I (machinery, toys, medical devices, lifts, civil aviation, motor vehicles, "
            "rail, marine, etc.) — and under Article 6(1)(b) only where that product itself "
            "requires a third-party conformity assessment under the sectoral legislation; or "
            "(2) it falls within one of the eight use-case categories in Annex III. Annex III "
            "systems are NOT high-risk if they perform a narrow procedural task, improve a "
            "previously completed human activity, detect decision-making patterns without "
            "replacing human review, or perform a preparatory task — unless they profile "
            "natural persons (Article 6(3)); the provider must document that assessment."
        ),
    },
    {
        "id": "xr_04",
        "question": "Which sectors or applications are considered high-risk under the regulation?",
        "expected_refs": ["Article 6", "Annex I", "Annex III"],
        "expected_keywords": ["biometrics", "critical infrastructure", "essential services"],
        "category": "expert_review",
        "gold_answer": (
            "Two routes: the Annex I route — safety components of products under Union "
            "harmonisation legislation (machinery, toys, medical devices, lifts, civil "
            "aviation, motor vehicles, marine equipment, rail, agricultural vehicles, etc.); "
            "and the Annex III route — eight listed use-case categories: biometric "
            "identification/categorisation, critical infrastructure, education and vocational "
            "training, employment and worker management, essential private and public services, "
            "law enforcement, migration/asylum/border control, and administration of justice "
            "and democratic processes."
        ),
    },
    {
        "id": "xr_05",
        "question": "How should users be informed when interacting with AI systems?",
        "expected_refs": ["Article 50"],
        "expected_keywords": ["transparency", "disclose", "deepfake"],
        "category": "expert_review",
        "gold_answer": (
            "Article 50(1): providers must ensure systems intended to interact directly with "
            "natural persons are designed so the person is informed they are interacting with "
            "an AI system, unless obvious from context. Article 50(2): providers of systems "
            "generating synthetic audio, image, video or text content must mark outputs in a "
            "machine-readable format and detectable as artificially generated. Article 50(3): "
            "DEPLOYERS (not providers) of emotion-recognition or biometric-categorisation "
            "systems must inform exposed persons. Article 50(4): deployers of deepfakes must "
            "disclose that the content was artificially generated or manipulated."
        ),
    },
    {
        "id": "xr_06",
        "question": "What are AI systems with minimal risks?",
        "expected_refs": ["Article 5", "Article 6", "Article 50"],
        "expected_keywords": ["minimal risk", "residual"],
        "category": "expert_review",
        "gold_answer": (
            "Minimal-risk systems are the RESIDUAL category: AI systems that are neither "
            "prohibited under Article 5, nor high-risk via Annex I or Annex III under Article "
            "6, nor subject to Article 50 transparency obligations, nor general-purpose AI "
            "models under Articles 51-55. They are not burdened with the Act's compliance "
            "obligations (beyond Article 4 AI-literacy measures); the definition is by "
            "exclusion, not by any affirmative criterion."
        ),
    },
    {
        "id": "xr_07",
        "question": "What are the guiding principles established by the AI Act?",
        "expected_refs": [],
        "expected_keywords": ["human agency", "technical robustness", "privacy", "transparency",
                              "non-discrimination", "accountability", "well-being"],
        "category": "expert_review",
        "gold_answer": (
            "Recital 27 articulates seven principles for trustworthy AI: human agency and "
            "oversight; technical robustness and safety; privacy and data governance; "
            "transparency; diversity, non-discrimination and fairness; social and environmental "
            "well-being; and accountability. These principles guide the Act's risk-based "
            "framework and the fundamental-rights-centred application of its obligations."
        ),
    },
    {
        "id": "xr_08",
        "question": "What is the definition of a \"system of artificial intelligence\"?",
        "expected_refs": ["Article 3"],
        "expected_keywords": ["machine-based", "autonomy", "infer"],
        "category": "expert_review",
        "gold_answer": (
            "Article 3(1) defines an AI system as a machine-based system designed to operate "
            "with varying levels of autonomy and that may exhibit adaptiveness after "
            "deployment, and that, for explicit or implicit objectives, infers, from the input "
            "it receives, how to generate outputs such as predictions, content, "
            "recommendations, or decisions that can influence physical or virtual environments."
        ),
    },
    {
        "id": "xr_09",
        "question": "What are the penalties for violating the provisions of the regulation for high-risk AI systems?",
        "expected_refs": ["Article 99"],
        "expected_keywords": ["penalties", "administrative fines", "high-risk"],
        "category": "expert_review",
        "gold_answer": (
            "For high-risk systems specifically, Article 99(4) sets the penalty: administrative "
            "fines of up to 15,000,000 EUR or, if the infringer is a company, up to 3% of total "
            "worldwide annual turnover of the preceding financial year, whichever is higher. "
            "SMEs benefit from a lower-of-two-amounts rule under Article 99(6). Article 99(1) "
            "also obliges Member States to lay down effective, proportionate and dissuasive "
            "penalties for all other infringements."
        ),
    },
    {
        "id": "xr_10",
        "question": "What is the difference between the deployer and the provider?",
        "expected_refs": ["Article 3", "Article 25"],
        "expected_keywords": ["provider", "deployer", "market"],
        "category": "expert_review",
        "gold_answer": (
            "Under Article 3, a provider is any natural or legal person who develops an AI "
            "system, or has one developed, and places it on the market or puts it into service "
            "under their own name or trademark; a deployer is any person who uses an AI system "
            "under their own authority, except for personal, non-professional use. Article 25 "
            "adds the role transition: a deployer becomes a provider with full Article 16 "
            "obligations when they place the system on the market under their own name, "
            "substantially modify it, or change its intended purpose so it becomes high-risk."
        ),
    },
    {
        "id": "xr_11",
        "question": "Does the technical documentation of a high-risk AI system require specifications regarding the required hardware?",
        "expected_refs": ["Article 11", "Annex IV"],
        "expected_keywords": ["technical documentation", "hardware", "architecture"],
        "category": "expert_review",
        "gold_answer": (
            "Yes. Article 11 requires providers to draw up and keep up to date technical "
            "documentation meeting at minimum Annex IV's content, and Annex IV point 1(e) "
            "expressly requires the hardware specifications — the system's architecture and "
            "the hardware on which it operates. Annex IV point 2(c) also covers the "
            "computational resources used to develop, train, test and validate the system. "
            "Hardware specifications are therefore squarely part of the conformity "
            "documentation file."
        ),
    },
    {
        "id": "xr_12",
        "question": "Are AI systems intended for emotion recognition from biometric data always prohibited?",
        "expected_refs": ["Article 5", "Annex III", "Article 50"],
        "expected_keywords": ["emotion recognition", "workplace", "prohibited"],
        "category": "expert_review",
        "gold_answer": (
            "No. Article 5(1)(f) prohibits emotion recognition in workplaces and educational "
            "institutions (with a narrow carve-out for systems placed on the market for medical "
            "or safety reasons). Outside those settings an emotion-recognition system is not "
            "prohibited but is high-risk under Annex III (biometric categorisation of natural "
            "persons), and Article 50(3) requires DEPLOYERS of such systems to inform exposed "
            "persons that they are subject to the system."
        ),
    },
    {
        "id": "xr_13",
        "question": "Is an AI that transcribes doctor-patient conversations prohibited? Or is it high-risk as per the use cases of Annex III of the AI Act?",
        "expected_refs": ["Article 5", "Article 6", "Annex I", "Article 50"],
        "expected_keywords": ["transcription", "medical device", "not high-risk"],
        "category": "expert_review",
        "gold_answer": (
            "Transcribing doctor-patient conversations is not prohibited under Article 5 and is "
            "not listed as a high-risk use case in Annex III (so it does not become high-risk "
            "via the Annex III route). It becomes high-risk under Article 6(1) only if deployed "
            "as a safety component of a medical device covered by Annex I harmonisation "
            "legislation (e.g. MDR or IVDR) whose product requires third-party conformity "
            "assessment. Otherwise Article 50 transparency obligations may apply when the "
            "system interacts with patients."
        ),
    },
    {
        "id": "xr_14",
        "question": "We are a medical device manufacturer building an AI system to analyze X-rays to detect tumors. Is this system classified as high-risk, and what conformity assessment is required?",
        "expected_refs": ["Article 6", "Annex I", "Article 43"],
        "expected_keywords": ["X-ray", "medical device", "conformity assessment", "notified body"],
        "category": "expert_review",
        "gold_answer": (
            "Yes — an AI system used as a safety component of an X-ray/radiology medical "
            "device is high-risk under Article 6(1) via Annex I (MDR/IVDR). Concretely: "
            "classify the device under MDR (diagnostic imaging devices are typically Class IIb "
            "or III, requiring notified-body assessment), and per Article 43(3) the AI Act "
            "conformity assessment is integrated into the MDR notified-body procedure — one "
            "unified assessment for the manufacturer, covering the Annex III (AI Act) "
            "documentation requirements."
        ),
    },
    {
        "id": "xr_15",
        "question": "Can a hospital use an AI system to sort patients based on their biometric data to determine priority for an experimental clinical trial?",
        "expected_refs": ["Article 5", "Annex III"],
        "expected_keywords": ["clinical trial", "biometric categorisation", "eligibility"],
        "category": "expert_review",
        "gold_answer": (
            "It depends on what the system infers and what the trial offers. A clinical-trial "
            "selection process is not Annex III(5)(d) emergency triage; it may fall under "
            "Annex III(5)(a) eligibility for essential public assistance benefits and services "
            "including healthcare (where the trial offers public-funded access to healthcare), "
            "or may fall outside Annex III entirely and be governed by the MDR and the "
            "Clinical Trials Regulation. Separately, Article 5(1)(g) prohibits biometric "
            "categorisation that infers sensitive attributes from a closed list (race, "
            "political opinions, trade union membership, religious or philosophical beliefs, "
            "sex life, sexual orientation) — using biometric data for priority does not "
            "automatically trigger that unless such attributes are inferred."
        ),
    },
    {
        "id": "xr_16",
        "question": "Our life sciences startup developed a general-purpose AI model trained on massive amounts of genomic data. What transparency obligations apply to us?",
        "expected_refs": ["Article 53", "Article 55", "Article 51"],
        "expected_keywords": ["general-purpose", "transparency", "training data"],
        "category": "expert_review",
        "gold_answer": (
            "As a GPAI provider under Article 53(1) you must: draw up and keep up to date "
            "technical documentation per Annex XI; supply information and documentation to "
            "downstream providers per Annex XII; establish a copyright policy (including for "
            "text and data mining); and publish a sufficiently detailed summary of training "
            "content. The gating question is Article 51: if cumulative training compute reaches "
            "the systemic-risk threshold (currently 10^25 FLOPs) you are a systemic-risk GPAI "
            "model subject to the additional Article 55 obligations — a startup model trained "
            "on genomic data will typically NOT meet that threshold, but it must be assessed."
        ),
    },
    {
        "id": "xr_17",
        "question": "We are a university lab developing an AI model exclusively for scientific research and development into new life science drugs. Does the AI Act apply to our model before it is released to the market?",
        "expected_refs": ["Article 2"],
        "expected_keywords": ["research", "scientific", "R&D", "exclusion"],
        "category": "expert_review",
        "gold_answer": (
            "No — Article 2(6) excludes AI systems developed and put into service exclusively "
            "for scientific research and development, so a model used only for life-science "
            "drug R&D inside the lab falls outside the Act's scope while it is used only for "
            "that purpose. The exclusion ends at release: once the system is placed on the EU "
            "market or put into service, scope attaches and the provider obligations apply "
            "according to its risk classification. Article 2(8) separately covers pre-market "
            "real-world-condition testing, which is a distinct phase between R&D and market "
            "placement."
        ),
    },
    {
        "id": "xr_18",
        "question": "We are developing a generative AI chatbot that will be deployed on a hospital website to answer general patient queries. What transparency obligations apply?",
        "expected_refs": ["Article 50", "Article 13"],
        "expected_keywords": ["chatbot", "transparency", "deployer", "synthetic content"],
        "category": "expert_review",
        "gold_answer": (
            "First classify: a general patient-query chatbot is probably NOT high-risk (not "
            "Annex III emergency triage, not eligibility determination), so it is limited-risk "
            "and Article 50 applies ALONE — Article 13 high-risk transparency does not attach "
            "unless the system is high-risk. As the provider you must ensure users are informed "
            "they interact with an AI system (Article 50(1)) and generative outputs are marked "
            "in a machine-readable detectable format (Article 50(2)). Where the hospital "
            "deploys your chatbot, the HOSPITAL is the deployer: Article 50(4) deepfake "
            "disclosure would attach to the hospital for AI-generated content presented to "
            "patients."
        ),
    },
    {
        "id": "xr_19",
        "question": "A pharmaceutical company wants to use an AI system to monitor the emotions and stress levels of their manufacturing line workers to improve efficiency. Is this allowed?",
        "expected_refs": ["Article 5"],
        "expected_keywords": ["emotion", "workplace", "prohibited", "efficiency"],
        "category": "expert_review",
        "gold_answer": (
            "No. Article 5(1)(f) prohibits AI systems that infer the emotions or mental states "
            "of workers in workplace settings, and using one to improve manufacturing "
            "efficiency falls squarely within that prohibition with no applicable exception. "
            "The only carve-out is narrow: systems placed on the market strictly for medical "
            "or safety reasons (e.g. fatigue detection to prevent industrial accidents) are "
            "not prohibited, but that primary purpose must be established at market placement "
            "and cannot be retrofitted — efficiency improvement does not qualify."
        ),
    },
    {
        "id": "xr_20",
        "question": "Is an AI system intended to be used as a safety component in robotic surgery considered high-risk under the AI Act?",
        "expected_refs": ["Article 6", "Annex I", "Article 14", "Article 72"],
        "expected_keywords": ["robotic surgery", "safety component", "high-risk", "human oversight"],
        "category": "expert_review",
        "gold_answer": (
            "Yes — robotic-surgery systems are typically Class IIb or III medical devices "
            "under MDR (Rule 12 or 22) requiring notified-body assessment, so the AI safety "
            "component is high-risk under Article 6(1) via Annex I. The consequences matter "
            "specifically for surgery: real-time AI involvement in the control loop engages "
            "the Article 14 human-oversight design requirements, and the device is subject to "
            "layered post-market surveillance under both MDR Article 83 and AI Act Article 72."
        ),
    },
]

NO_GROUND_TRUTH: list[dict] = []

__all__ = ["GROUND_TRUTH", "NO_GROUND_TRUTH"]
