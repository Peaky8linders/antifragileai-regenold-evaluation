# Analysis for evals/bench/results/paper-v4-paper-v4-local.json
Total scenarios: 52

### Metrics (Averages)
- ref_loose: 0.85 (from 52)
- ref_strict: 0.49 (from 52)
- keyword_recall: 0.80 (from 52)
- regulatory_tone: 1.00 (from 52)
- Refusals: 1
- Errors: 0

### Mistakes / Low Score Examples (13)
**ID**: st_v4_017
**Q**: An AI spam filter automatically sorts incoming corporate email into junk and inbox folders. How does the EU AI Act classify it?
**Error**: None
**Scores**: Loose=0.5, Recall=1.0
**Reasoning**: ...
**Predicted**: Not high-risk. An AI spam filter that sorts incoming corporate email into junk and inbox folders does not fall within any of the eight Annex III use-case categories (biometrics, critical infrastructur...
---
**ID**: st_v4_019
**Q**: A word processor uses AI to check spelling and grammar as the user types. Does the EU AI Act impose any specific obligations?
**Error**: None
**Scores**: Loose=0.0, Recall=0.6666666666666666
**Reasoning**: ...
**Predicted**: No specific obligations attach. A spelling and grammar checker does not fall within any of the eight high-risk use-case categories of Annex III (biometrics, critical infrastructure, education, employm...
---
**ID**: st_v4_020
**Q**: What is the difference between a minimal-risk and a high-risk AI system under the EU AI Act's risk-based approach?
**Error**: None
**Scores**: Loose=0.5, Recall=0.6666666666666666
**Reasoning**: ...
**Predicted**: A system reaches the high-risk tier on one of two routes under Article 6: the Annex I route (Article 6(1)), where it is, or is a safety component of, a product covered by the listed Union harmonisatio...
---
**ID**: tp_v4_003
**Q**: An AI predicts the likelihood that an individual will commit a crime based solely on profiling their personality traits and background, with no objective facts tied to a specific offence. Prohibited o
**Error**: None
**Scores**: Loose=1.0, Recall=0.3333333333333333
**Reasoning**: ...
**Predicted**: The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed...
---
**ID**: tp_v4_005
**Q**: An online-learning platform uses an AI webcam tool to detect when students look confused so teachers can intervene. The vendor says it is 'just adaptive learning'. How does the EU AI Act treat it?
**Error**: None
**Scores**: Loose=0.0, Recall=0.3333333333333333
**Reasoning**: ...
**Predicted**: The Act's definition of an AI system in Article 3 expressly covers machine-based systems that may be adaptive and that infer from their input how to generate outputs influencing their environment, so ...
---
**ID**: tp_v4_006
**Q**: A photo-gallery app uses AI to automatically tag and group your own private photos by content. No output is shared. Limited-risk (transparency) or minimal-risk under the EU AI Act?
**Error**: None
**Scores**: Loose=0.5, Recall=1.0
**Reasoning**: ...
**Predicted**: Minimal-risk, not limited-risk. The Article 50 transparency tier attaches only to specific deployment patterns: systems that interact directly with natural persons and must disclose their AI nature (A...
---
**ID**: tp_v4_007
**Q**: An email client embeds an AI that translates incoming messages into the user's language. Does the EU AI Act impose any transparency or other obligations?
**Error**: None
**Scores**: Loose=0.5, Recall=1.0
**Reasoning**: ...
**Predicted**: Minimal, and limited to light transparency. Machine translation of incoming email is not one of the eight Annex III high-risk use cases and is not an Annex I product safety component, so the system is...
---
**ID**: tp_v4_018
**Q**: Which articles of the EU AI Act establish AI regulatory sandboxes to support innovation and SMEs?
**Error**: None
**Scores**: Loose=1.0, Recall=0.3333333333333333
**Reasoning**: ...
**Predicted**: Article 57 is the operative provision: it requires each Member State to establish at least one AI regulatory sandbox at national level, providing a controlled environment to develop, train, test, and ...
---
**ID**: tp_v4_020
**Q**: Which EU AI Act articles cover the conformity-assessment procedure, the EU declaration of conformity, and the CE marking for a high-risk AI system?
**Error**: None
**Scores**: Loose=0.6666666666666666, Recall=0.6666666666666666
**Reasoning**: ...
**Predicted**: Article 43 governs the conformity-assessment procedure: providers of Annex-III systems that have applied harmonised standards or common specifications follow the internal-control procedure of Annex VI...
---
**ID**: mt_v4_001
**Q**: 
**Error**: None
**Scores**: Loose=0.0, Recall=0.3333333333333333
**Reasoning**: ...
**Predicted**: Inferring engagement from employees' facial expressions is an emotion-recognition system processing biometric data, and applying it to evaluate workers brings it within two Annex III high-risk categor...
---


# Analysis for evals/bench/results/medtech-lifesci-r136-r136-medls-local.json
Total scenarios: 24

### Metrics (Averages)
- ref_loose: 0.75 (from 24)
- ref_strict: 0.57 (from 24)
- keyword_recall: 0.78 (from 24)
- regulatory_tone: 1.00 (from 24)
- Refusals: 0
- Errors: 0

### Mistakes / Low Score Examples (13)
**ID**: ls_01
**Q**: Is AI software that flags early sepsis risk from ICU vital-sign streams a high-risk AI system under the EU AI Act?
**Error**: None
**Scores**: Loose=0.6666666666666666, Recall=1.0
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"anchors_used":["Art. 6"],"references":["Article 6","Article 6.1","Annex I"],"retrieval_path":"n...
**Predicted**: Likely high-risk, because sepsis-prediction software operating on ICU vital-sign streams will almost always be a safety component of, or itself constitute, a medical device, bringing it within the fir...
---
**ID**: ls_02
**Q**: What is a 'safety component' for the purposes of the EU AI Act?
**Error**: None
**Scores**: Loose=0.0, Recall=0.4
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"references":["Article 10","Article 6","Article 6.1","Article 6.2","Annex I","Annex III"],"retri...
**Predicted**: Its significance is classificatory: under the Annex I route of Article 6(1), an AI system is high-risk where it is a safety component of (or is itself) a product covered by the Union harmonisation leg...
---
**ID**: ls_03
**Q**: A pharmaceutical company uses an AI model solely for internal pre-clinical drug-target discovery and never places it on the market. Does the EU AI Act apply to that model?
**Error**: None
**Scores**: Loose=0.0, Recall=0.25
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"references":["Article 10","Article 11","Article 3","Article 16","Annex IV"],"retrieval_path":"n...
**Predicted**: Generally no on these facts. The Act's obligations attach only once an AI system is placed on the market or put into service in the Union, both defined terms in Article 3, so a model used purely for i...
---
**ID**: ls_06
**Q**: A US medtech firm with no EU establishment wants to make its tumour-segmentation AI available on the EU market. What does the AI Act require of it before doing so?
**Error**: None
**Scores**: Loose=0.5, Recall=1.0
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"anchors_used":["Art. 22"],"references":["Article 22","Article 9","Article 43","Article 11","Art...
**Predicted**: Before placing this high-risk system on the EU market, the US firm, as a provider established outside the Union, must by written mandate appoint an authorised representative established in the Union, ...
---
**ID**: ls_07
**Q**: A biotech firm fine-tunes an open-weight general-purpose AI model on proprietary trial data, adding about 1x10^24 FLOPs of compute. Does it become a provider, and do systemic-risk obligations apply?
**Error**: None
**Scores**: Loose=0.6666666666666666, Recall=0.6
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"anchors_used":["Art. 53","Art. 55"],"references":["Article 25","Article 51","Annex XIII"],"retr...
**Predicted**: Under Article 25, which makes a downstream actor a new provider when it substantially modifies a model, the Commission's one-third fine-tuning benchmark treats a modifier as the new provider only wher...
---
**ID**: ls_11
**Q**: An AI matches patients to experimental clinical trials from their electronic health records. Is this high-risk under Annex III(5)(d) emergency triage?
**Error**: None
**Scores**: Loose=0.5, Recall=0.8
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"Valid EU AI Act reference(s): Annex III(5)(d)"},"anchors_used":["Annex III(5)(d)","Annex III"],"references":["Article 6","Article 6....
**Predicted**: Not high-risk under Annex III(5)(d), because that point captures AI used to evaluate and triage emergency first-response calls and to dispatch emergency services, not the matching of patients to exper...
---
**ID**: ls_14
**Q**: An AI safety component controls instrument motion in real time during robotic surgery. Beyond being high-risk, what specific AI Act obligations are engaged?
**Error**: None
**Scores**: Loose=0.75, Recall=0.6
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"references":["Article 10","Article 11","Article 12","Article 6","Article 6.1","Article 13","Art...
**Predicted**: As a safety component governing real-time instrument motion, this system is high-risk via the Annex I route of Article 6(1), since it is a safety component of a product covered by Union harmonisation ...
---
**ID**: ls_17
**Q**: A continuous glucose monitor's AI insulin-dosing recommendation is retrained weekly on new patient data. Does each retraining trigger a fresh conformity assessment?
**Error**: None
**Scores**: Loose=0.5, Recall=1.0
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"anchors_used":["Art. 43"],"references":["Article 43","Article 10","Article 11","Article 25"],"r...
**Predicted**: Not automatically: each weekly retraining triggers a fresh conformity assessment only where it amounts to a substantial modification of the system. Article 43, which requires high-risk providers to un...
---
**ID**: ls_18
**Q**: How may a provider process patients' genetic and health data specifically to detect and correct demographic bias in a diagnostic AI?
**Error**: None
**Scores**: Loose=1.0, Recall=0.4
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"anchors_used":["Art. 6"],"references":["Article 10"],"retrieval_path":"neo4j","stage2_polish":t...
**Predicted**: Permitted, but only to the extent strictly necessary to detect and correct that bias and subject to safeguards, under the data-governance requirement of Article 10, which both obliges providers to exa...
---
**ID**: ls_21
**Q**: What automatic record-keeping must a high-risk medical AI provide, and how long must the deploying hospital keep those logs?
**Error**: None
**Scores**: Loose=0.5, Recall=0.6
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"anchors_used":["Art. 12"],"references":["Article 12"],"retrieval_path":"neo4j","stage2_polish":...
**Predicted**: A high-risk medical AI system must be designed to automatically record events (logs) over its lifetime to the extent appropriate to its intended purpose, capturing the events relevant to identifying r...
---


# Analysis for evals/bench/results/medtech-graphrag-v124-r124-medgrb-local.json
Total scenarios: 24

### Metrics (Averages)
- ref_loose: 0.75 (from 24)
- ref_strict: 0.66 (from 24)
- keyword_recall: 0.63 (from 24)
- regulatory_tone: 1.00 (from 24)
- Refusals: 0
- Errors: 0

### Mistakes / Low Score Examples (13)
**ID**: grb_01
**Q**: Is AI software that detects melanoma from dermoscopy images a high-risk AI system under the EU AI Act?
**Error**: None
**Scores**: Loose=0.6666666666666666, Recall=0.6666666666666666
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"anchors_used":["Art. 6"],"references":["Article 6","Article 6.1","Annex I"],"retrieval_path":"n...
**Predicted**: The operative provision is Article 6(1), which classifies an AI system as high-risk where it is itself a product, or a safety component of a product, covered by the Union harmonisation legislation lis...
---
**ID**: grb_04
**Q**: What does the EU AI Act require for an AI system that evaluates patients' eligibility for public healthcare benefits?
**Error**: None
**Scores**: Loose=0.5, Recall=1.0
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"references":["Article 10","Annex III"],"retrieval_path":"neo4j","stage2_polish":true,"engine_co...
**Predicted**: High-risk, and therefore subject to the full Chapter III Section 2 regime: an AI system used to evaluate patients' eligibility for public healthcare benefits falls within the Annex III category of sys...
---
**ID**: grb_08
**Q**: What must the provider of a high-risk AI medical diagnostic system put in place before placing it on the market?
**Error**: None
**Scores**: Loose=0.3333333333333333, Recall=0.0
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"references":["Article 9","Article 10","Article 12","Article 15"],"retrieval_path":"neo4j","stag...
**Predicted**: Concretely, it must establish a documented, iterative risk-management system spanning the lifecycle (Article 9); apply data-governance practices ensuring the training, validation, and test datasets ar...
---
**ID**: grb_09
**Q**: What conformity-assessment route applies to an AI system that is a safety component of a CE-marked medical device?
**Error**: None
**Scores**: Loose=0.5, Recall=0.6
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"anchors_used":["Art. 43","Art. 6"],"references":["Article 6","Article 6.1","Annex I"],"retrieva...
**Predicted**: Under the Article 6(1) Annex I classification route, an AI system that is a safety component of a product covered by the Union harmonisation legislation listed in Annex I, and which must itself underg...
---
**ID**: grb_12
**Q**: What logging and record-keeping does a high-risk AI radiology system require, and how long must the deploying hospital keep the logs?
**Error**: None
**Scores**: Loose=0.3333333333333333, Recall=0.5
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"anchors_used":["Art. 12"],"references":["Article 12"],"retrieval_path":"neo4j","stage2_polish":...
**Predicted**: Article 12 requires the high-risk system to be designed and built to automatically record events ("logs") over its lifetime that are relevant for identifying risks, supporting post-market monitoring, ...
---
**ID**: grb_14
**Q**: A pharma company trains a large foundation model for drug discovery whose training compute exceeds 10^25 FLOPs. Which EU AI Act obligations apply?
**Error**: None
**Scores**: Loose=0.6666666666666666, Recall=1.0
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"anchors_used":["Art. 51"],"references":["Article 51","Article 51.2","Article 53","Annex XI","An...
**Predicted**: The model is a general-purpose AI model with systemic risk under Article 51, since its training compute exceeds 10^25 FLOPs. The provider must comply with the Article 53 baseline obligations, technica...
---
**ID**: grb_15
**Q**: If a hospital fine-tunes an open-weight medical language model, when does it become a provider under the EU AI Act?
**Error**: None
**Scores**: Loose=1.0, Recall=0.4
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"references":["Article 25"],"retrieval_path":"neo4j","stage2_polish":true,"engine_confidence":0....
**Predicted**: A hospital becomes a provider at the point its fine-tuning amounts to a substantial modification of the open-weight model, or where it places the system on the market or puts it into service under its...
---
**ID**: grb_17
**Q**: Classify the EU AI Act risk tier of an AI ambient scribe that only transcribes doctor-patient consultations and performs no diagnosis or decision-making.
**Error**: None
**Scores**: Loose=1.0, Recall=0.2
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"anchors_used":["Art. 50"],"references":["Article 50","Article 6","Article 6.2","Article 6.1","A...
**Predicted**: A pure ambient scribe that only transcribes doctor-patient consultations and performs no diagnosis or decision-making does not fall within any of the eight Annex III use cases that trigger the Annex I...
---
**ID**: grb_18
**Q**: Classify the EU AI Act risk tier of a consumer wellness chatbot that gives general lifestyle tips and makes no medical claims.
**Error**: None
**Scores**: Loose=0.0, Recall=0.2
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"anchors_used":["Art. 50"],"references":["Article 10","Article 11","Article 43","Annex IV"],"ret...
**Predicted**: A consumer wellness chatbot offering general lifestyle tips and making no medical claims does not fall within any high-risk use case, so it does not trigger the Chapter III provider regime: the data-g...
---
**ID**: grb_20
**Q**: An AI tool recommends oncology treatment regimens from clinical guidelines. What EU AI Act obligations does its provider face across the lifecycle?
**Error**: None
**Scores**: Loose=0.25, Recall=0.5
**Reasoning**: {"schema_version":"r50.1","scope":{"verdict":"in_scope","evidence":"AI Act anchor keyword(s) present."},"references":["Article 10","Article 11","Article 16","Article 9","Article 15","Article 17","Anne...
**Predicted**: As the provider of a high-risk AI system, this actor carries the full Chapter III Section 2 obligation set throughout the lifecycle, the umbrella duty under Article 16 to ensure conformity and bear it...
---


