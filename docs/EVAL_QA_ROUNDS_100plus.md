# EU AI Act RAG — Eval Questions & Gold/Expected Answers (Rounds 100+)

Compiled from the evaluation fixtures in `evals/regenold/` — the question
sets the recent rounds (R98–R105) measured against. Generated directly from
the fixture modules so every question and answer is exact.

**What "answer" means per set:**

- **GraphRAG paper benchmark** — carries a full lawyer-reviewed *reference
  answer* (`REFERENCE_ANSWERS`) plus the expected Articles/Annexes.
- **Paper-V3 / Paper-V4 / V2 sets** — carry the expected Articles/Annexes +
  expected *key points* (keyword targets). These fixtures intentionally hold
  no full gold prose; the eval grades reference-correctness + keyword recall
  + regulator tone (multi-turn also scores coherence). So the "answer" shown
  is the reference set + key points the answer must surface.

> Wire-citation note: the Regenold API emits only `Article N` / `Annex N`
> (never Recitals). Where a paper's gold cited Recitals, the recital string
> is preserved under *paper refs* for provenance but is not wire-scored.

## Contents

- GraphRAG paper benchmark — **30** questions
- Paper-V4 — single-turn (R99, davidath-paper four-tier pyramid) — **20** questions
- Paper-V4 — tricky / decision-boundary (R99) — **20** questions
- Paper-V3 — single-turn (R98) — **20** questions
- Paper-V3 — tricky / decision-boundary (R98) — **20** questions
- V2 — tricky single-turn (7 categories: omnibus / role_ambiguity / conflict / borderline_prohibition / gpai / cross_framework / near_oos) — **31** questions
- Paper-V4 — multi-turn (R99, 3-turn conversations) — **12** questions
- Paper-V3 — multi-turn (R98) — **12** questions
- V2 — multi-turn (3-5 turn coreference / role-flip / framework probes) — **25** questions

**Total: 190 questions across 9 sets.**

---

## 1. GraphRAG paper benchmark

Source: a related EU AI Act GraphRAG-system paper (Appendix B.2). Used
directly in R100's verbatim-vs-synthesis A/B (`graphrag_ab.py`) and the
R102–R104 live judge runs. The reference answers below are the paper's
lawyer-reviewed gold.

### gt_01 — risk_taxonomy

**Q:** What risk categories are provided for AI systems?

**Gold answer:** The AI Act establishes a risk-based framework, categorising AI systems based on their potential for harm. Here are the risk categories: Unacceptable Risk, High Risk, Limited Risk and Minimal Risk.

**Expected references:** Article 3, Article 5, Article 6, Article 50

**Key points:** unacceptable risk, limited risk, minimal risk

*Paper refs (provenance):* Articles: 3(39),3(40),3(41),5(1),6(1),6(2),50(1),50(2); Recitals: 26,50,52,54,55,56,57,58,59,61,64,66,132,165

*Notes:* Four-tier risk pyramid. Gold spans Art. 3/5/6/50.

### gt_02 — prohibited

**Q:** What types of AI systems or practices are explicitly prohibited by the AI Act?

**Gold answer:** Subliminal techniques beyond a person's consciousness to materially distort behaviour in a way that causes harm. Exploiting vulnerabilities of specific groups (e.g., age, disability) to materially distort behaviour and cause harm. Social scoring systems can lead to detrimental treatment in unrelated social contexts or disproportionate treatment. Real-time remote biometric identification systems in publicly accessible spaces for law enforcement purposes, except for specific exceptions. AI systems used by or on behalf of law enforcement to make risk assessments for predicting criminal offenses based solely on profiling or personality traits.

**Expected references:** Article 5

**Key points:** subliminal, social scoring, biometric

*Paper refs (provenance):* Articles: 5

*Notes:* Art. 5 prohibited practices.

### gt_03 — high_risk_definition

**Q:** What is the definition of high risk?

**Gold answer:** The AI Act defines 'high risk' in the context of AI systems that pose significant risks to the health and safety or the fundamental rights of persons. This determination considers both the severity of the possible harm and the probability of its occurrence. The Act specifically outlines two main categories of high-risk AI systems: AI Systems Integrated into Products and Stand-alone High-Risk AI Systems. See Annex III.

**Expected references:** Article 6

**Key points:** health, safety, fundamental rights

*Paper refs (provenance):* Articles: 6

*Notes:* Art. 6 high-risk classification; answer also cites Annex III.

### gt_04 — high_risk_sectors

**Q:** Which sectors or applications are considered high-risk under the regulation?

**Gold answer:** An AI system shall be considered high-risk where both of the following conditions are fulfilled: (a) the AI system is intended to be used as a safety component of a product, or is itself a product, covered by the Union harmonisation legislation listed in Annex I; (b) the product is required to undergo a third-party conformity assessment before being placed on the market or put into service under that Annex I legislation. In addition, AI systems referred to in Annex III shall be considered high-risk.

**Expected references:** Article 6

**Key points:** safety component, annex i, conformity assessment

*Paper refs (provenance):* Articles: 6

*Notes:* Art. 6(1) Annex I safety-component path + Art. 6(2) Annex III.

### gt_05 — transparency

**Q:** How should users be informed when interacting with AI systems?

**Gold answer:** When interacting with an AI system, natural persons should be informed that they are interacting with an AI system unless it is obvious. Deployers of emotion recognition or biometric categorisation systems should inform natural persons exposed to the system of its operation. Deployers of an AI system that generates or manipulates text published to inform the public on matters of public interest shall disclose that the text has been artificially generated or manipulated. Information should be provided in a clear and distinguishable manner at the latest at the time of the first interaction or exposure.

**Expected references:** Article 50

**Key points:** informed, interacting, disclose

*Paper refs (provenance):* Articles: 50

*Notes:* Art. 50 transparency / interaction disclosure.

### gt_06 — minimal_risk

**Q:** What are AI systems with minimal risks?

**Gold answer:** AI systems may be developed for purposes that do not pose significant risks to health, safety, or fundamental rights. These include: a system that transforms unstructured data into structured data; one that classifies incoming documents into categories; one used to detect duplicates among many applications; one that improves the language used in documents without changing their substance; one that detects decision-making patterns or deviations; and one that performs tasks preparatory to an assessment.

**Expected references:** —

**Key points:** structured data, duplicates, minimal

*Paper refs (provenance):* Recitals: 53

*(recital-only gold — excluded from wire reference scoring)*

*Notes:* Recital-only gold — wire emits Articles/Annexes only, so this row is excluded from the reference-correctness aggregate.

### gt_07 — guiding_principles

**Q:** What are the guiding principles established by the AI Act?

**Gold answer:** Protection of fundamental rights, including democracy, the rule of law, environmental protection, health, and safety.

**Expected references:** —

**Key points:** fundamental rights, democracy, rule of law

*Paper refs (provenance):* Recitals: 1,7,48

*(recital-only gold — excluded from wire reference scoring)*

*Notes:* Recital-only gold — excluded from the reference-correctness aggregate (keyword recall + tone still scored).

### gt_08 — definition

**Q:** What is the definition of a "system of artificial intelligence"?

**Gold answer:** A machine-based system that is designed to operate with varying levels of autonomy and that may exhibit adaptiveness after deployment, and that, for explicit or implicit objectives, infers, from the input it receives, how to generate outputs such as predictions, content, recommendations, or decisions that can influence physical or virtual environments.

**Expected references:** Article 3

**Key points:** machine-based, autonomy, infers

*Paper refs (provenance):* Articles: 3(1)

*Notes:* Art. 3(1) definition of an AI system.

### gt_09 — penalties

**Q:** What are the penalties for violating the provisions of the regulation for high-risk AI systems?

**Gold answer:** Breaches of provisions concerning high-risk AI systems, including transparency obligations for providers and deployers, can result in administrative fines of up to 15,000,000 EUR or 3% of the offender's total worldwide annual turnover, whichever is higher.

**Expected references:** Article 99

**Key points:** administrative, fine, turnover

*Paper refs (provenance):* Articles: 99

*Notes:* Art. 99 penalties (up to EUR 15m or 3% worldwide turnover).

### gt_10 — roles

**Q:** What is the difference between the deployer and the provider?

**Gold answer:** The Provider is a natural or legal person, public authority, agency or other body that develops an AI system or a general-purpose AI model (or has one developed) and places it on the market or puts it into service under its own name or trademark. The Deployer is a natural or legal person, public authority, agency or other body using an AI system under its authority, except for personal non-professional activity. The provider bears primary responsibility for AI Act compliance, especially for high-risk systems; the deployer uses the system for its intended purpose.

**Expected references:** Article 3, Article 16

**Key points:** provider, deployer, trademark

*Paper refs (provenance):* Articles: 3(3),3(4),16

*Notes:* Art. 3(3)/(4) definitions + Art. 16 provider responsibility.

### ng_01 — risk_assessment

**Q:** What criteria exist for assessing the risk of an AI system?

**Gold answer:** The criteria for assessing the risk of an AI system under the AI Act include: intended purpose, context and extent of use, nature and amount of data processed, system autonomy, likelihood and severity of harm to health/fundamental rights, risks to vulnerable groups (like children), and availability of legal redress.

**Expected references:** Article 7, Article 9

**Key points:** intended purpose, likelihood of harm, vulnerable groups, fundamental rights

*Paper refs (provenance):* Articles: 7(2),9(9)

*Notes:* Assessment criteria under Article 7(2) and Article 9(9).

### ng_02 — sanctions

**Q:** What are the sanctions for violating the provisions of the regulation for transparency risk systems?

**Gold answer:** Sanctions for violating transparency obligations under Article 50 include administrative fines of up to 15,000,000 EUR or 3% of the offender's total worldwide annual turnover for the preceding financial year, whichever is higher. Penalties must be effective, proportionate, and dissuasive, considering SMEs.

**Expected references:** Article 99

**Key points:** administrative fine, turnover, preceding financial year, effectiveness

*Paper refs (provenance):* Articles: 99(4)

*Notes:* Transparency system sanctions under Article 99(4) (up to 15M EUR or 3% turnover).

### ng_03 — deployer_obligations

**Q:** What obligations exist for deployers of high-risk AI systems?

**Gold answer:** Obligations for deployers of high-risk AI systems include: taking appropriate technical and organizational measures, using systems in accordance with provided instructions, monitoring system operation, keeping automatically generated logs for at least six months, performing a Fundamental Rights Impact Assessment (FRIA), and informing natural persons exposed to the system.

**Expected references:** Article 26, Article 27

**Key points:** impact assessment, inform, monitor, log, instructions for use

*Paper refs (provenance):* Articles: 26,27(1)

*Notes:* Deployer obligations under Articles 26 and 27 (FRIA).

### ng_04 — high_risk_requirements

**Q:** What requirements must AI systems classified as high-risk meet?

**Gold answer:** High-risk AI systems must meet mandatory requirements: establishing a comprehensive risk management system; ensuring high data quality and governance standards; preparing detailed technical documentation; maintaining automatic record-keeping (logs); ensuring transparency and clear instructions; enabling human oversight; and achieving high robustness, accuracy, and cybersecurity.

**Expected references:** Article 9, Article 11, Article 13, Article 14, Article 15

**Key points:** risk management, technical documentation, transparency, human oversight, robustness

*Paper refs (provenance):* Articles: 9,11,13,14,15

*Notes:* High-risk mandatory requirements under Chapter III, Section 2.

### ng_05 — provider_obligations

**Q:** What obligations do providers of high-risk AI systems have in terms of transparency and technical documentation?

**Gold answer:** Providers of high-risk AI systems must prepare comprehensive technical documentation before market placement, keep it up-to-date for 10 years, design systems to ensure transparency, provide clear instructions for use (identity, capabilities, and risks), and supply all necessary documentation to competent authorities upon a reasoned request.

**Expected references:** Article 11, Article 13, Article 18, Article 21, Article 23

**Key points:** technical documentation, conformity, 10 years, instructions for use

*Paper refs (provenance):* Articles: 11,13,18,21,23

*Notes:* Provider transparency and documentation obligations under Chapter III, Section 3.

### ng_06 — conformity_assessment

**Q:** What does a conformity assessment consist of?

**Gold answer:** A conformity assessment consists of procedures to verify and demonstrate compliance with high-risk requirements. Providers can choose between internal control (Annex VI) or a quality management system and technical documentation assessment by a notified body (Annex VII), resulting in a certificate of conformity or assessment certificate.

**Expected references:** Article 43, Annex VI, Annex VII

**Key points:** internal control, notified body, quality management system, certificate

*Paper refs (provenance):* Articles: 43; Annexes: VI,VII

*Notes:* Conformity assessment mechanisms under Article 43 and Annexes VI/VII.

### ng_07 — systemic_risk

**Q:** What does systemic-risk mean?

**Gold answer:** Systemic risk is a risk specific to the high-impact capabilities of general-purpose AI models that can propagate at scale across the value chain, causing actual or foreseeable negative effects on public health, safety, public security, fundamental rights, or society as a whole.

**Expected references:** Article 3, Article 55

**Key points:** high-impact capabilities, general-purpose, propagate, negative effects

*Paper refs (provenance):* Articles: 3(65),55

*Notes:* Systemic risk definitions and assessment under Article 3(65) and Article 55.

### ng_08 — gpai_definition

**Q:** What is the definition of General-purpose AI?

**Gold answer:** A general-purpose AI model is an AI model that exhibits significant generality, is capable of competently performing a wide range of distinct tasks, and can be integrated into various downstream applications. A general-purpose AI system is built on such a model and serves a variety of purposes.

**Expected references:** Article 3

**Key points:** general-purpose ai model, generality, distinct tasks, self-supervision

*Paper refs (provenance):* Articles: 3(63),3(66)

*Notes:* Definition of General-Purpose AI model/system under Article 3.

### ng_09 — qms

**Q:** What are the components of a quality management system?

**Gold answer:** A quality management system must include: regulatory compliance strategy; design control and verification; testing and validation procedures; data management systems (acquisition, collection, labeling); technical specifications/standards; risk management; post-market monitoring; and serious incident reporting.

**Expected references:** Article 17

**Key points:** design control, data management, testing, post-market monitoring

*Paper refs (provenance):* Articles: 17(1)

*Notes:* QMS requirements under Article 17.

### ng_10 — bias_mitigation

**Q:** What are the requirements for documenting bias mitigation measures in AI models?

**Gold answer:** document bias mitigation, providers must ensure data sets are subject to high governance, including assessing and mitigating biases affecting health, safety, or fundamental rights. Targeted measures must be documented, and continuous-learning models must mitigate loops of biased feedback.

**Expected references:** Article 10, Article 15

**Key points:** bias detection, data governance, training, validation, mitigate

*Paper refs (provenance):* Articles: 10(2),15(4)

*Notes:* Bias mitigation requirements under Article 10(2) and Article 15(4).

### gt_11 — hardware_specs

**Q:** Does the technical documentation of a high-risk AI system require to provide specifications regarding the required hardware?

**Gold answer:** Yes. Article 11 requires high-risk systems to have technical documentation. Annex IV specifies that this documentation must include a general description of the system, including its architecture and the specifications of required hardware and computing resources.

**Expected references:** Article 11, Annex IV

**Key points:** technical documentation, hardware, computing resources, architecture

*Paper refs (provenance):* Articles: 11; Annexes: IV

*Notes:* PDF Example 1. Art. 11 + Annex IV hardware specs.

### gt_12 — emotion_recognition

**Q:** Are AI systems intended for emotion recognition from biometric data always prohibited?

**Gold answer:** No, they are not always prohibited. Under Article 5, they are specifically prohibited when used in the workplace or educational institutions, unless they are installed or used for medical or safety reasons.

**Expected references:** Article 5

**Key points:** workplace, educational, medical, safety, not always prohibited

*Paper refs (provenance):* Articles: 5

*Notes:* PDF Example 2. Art. 5 prohibitions and exceptions.

### gt_13 — transcription_classification

**Q:** Is an AI that transcribes doctor–patient conversations prohibited? Or is it high-risk as per the use cases of Annex III of the AI Act?

**Gold answer:** It is not inherently prohibited under Article 5. Whether it is high-risk depends on its exact classification. While it is not explicitly listed in Annex III as high-risk, if the transcription system is intended to be used as a medical device (or a safety component of one) covered by EU harmonisation legislation (Annex I, e.g., the Medical Device Regulation) and requires a third-party conformity assessment, it is classified as high-risk under Article 6. Otherwise, basic transcription is minimal/limited risk.

**Expected references:** Article 5, Article 6, Annex I, Annex III

**Key points:** not prohibited, medical device, safety component, MDR, general purpose

*Paper refs (provenance):* Articles: 5,6; Annexes: I,III

*Notes:* PDF Example 3. Not prohibited under Art. 5; high-risk under Art. 6/Annex I if medical device.

### med_01 — medtech_high_risk

**Q:** We are a medical device manufacturer building an AI system to analyze X-rays to detect tumors. Is this system classified as high-risk, and what conformity assessment is required?

**Gold answer:** Yes, it is high-risk under Article 6 because it is a safety component of a product covered by Annex I (Medical Devices) and requires third-party conformity assessment. The conformity assessment must follow the requirements under Article 43.

**Expected references:** Article 6, Article 43, Annex I

**Key points:** medical device, safety component, Annex I, third-party, conformity assessment

*Paper refs (provenance):* Articles: 6,43; Annexes: I

*Notes:* Medical Imaging Device classification and conformity.

### med_02 — medtech_triage

**Q:** Can a hospital use an AI system to sort patients based on their biometric data to determine priority for an experimental clinical trial?

**Gold answer:** It is not explicitly prohibited unless it uses biometric categorization to deduce protected traits (Article 5). However, systems used to evaluate or classify natural persons for access to essential healthcare services or triage are classified as high-risk under Annex III.

**Expected references:** Article 5, Article 6, Annex III

**Key points:** healthcare, essential services, biometric categorization, high-risk, triage

*Paper refs (provenance):* Articles: 5,6; Annexes: III

*Notes:* Clinical Trial Patient Triage.

### med_03 — lifesciences_gpai

**Q:** Our life sciences startup developed a general-purpose AI model trained on massive amounts of genomic data. What transparency obligations apply to us?

**Gold answer:** As a provider of a general-purpose AI model, you must fulfill Article 53 obligations, which include providing technical documentation, honoring EU copyright law, and publishing a sufficiently detailed summary of the content used for training the model.

**Expected references:** Article 50, Article 53

**Key points:** general-purpose AI model, transparency, copyright, summary of training data, technical documentation

*Paper refs (provenance):* Articles: 50,53

*Notes:* Genomic LLM transparency obligations.

### med_04 — lifesciences_research

**Q:** We are a university lab developing an AI model exclusively for scientific research and development into new life science drugs. Does the AI Act apply to our model before it is released to the market?

**Gold answer:** Under Article 2, the AI Act does not apply to AI systems or models specifically developed and put into service for the sole purpose of scientific research and development. Therefore, pre-market research activities are generally exempt.

**Expected references:** Article 2

**Key points:** scientific research, development, exempt, does not apply

*Paper refs (provenance):* Articles: 2

*Notes:* AI in Medical Research (Exemption).

### med_05 — medtech_chatbot

**Q:** We are developing a generative AI chatbot that will be deployed on a hospital website to answer general patient queries. What transparency obligations apply?

**Expected references:** Article 50

**Key points:** interact, natural persons, informed, chatbot, transparency

*Paper refs (provenance):* Articles: 50

*Notes:* Patient chatbot transparency.

### med_06 — medtech_emotion_workplace

**Q:** A pharmaceutical company wants to use an AI system to monitor the emotions and stress levels of their manufacturing line workers to improve efficiency. Is this allowed?

**Expected references:** Article 5

**Key points:** emotion recognition, workplace, prohibited, employees

*Paper refs (provenance):* Articles: 5

*Notes:* Emotion recognition in workplace prohibition.

### med_07 — medtech_robotic_surgery

**Q:** Is an AI system intended to be used as a safety component in robotic surgery considered high-risk under the AI Act?

**Expected references:** Article 6, Annex I

**Key points:** safety component, medical device, Annex I, high-risk

*Paper refs (provenance):* Articles: 6; Annexes: I

*Notes:* Robotic surgery safety component (MDR).

---

## 2. Paper-V4 — single-turn (R99, davidath-paper four-tier pyramid)

### st_v4_001 — prohibited

**Q:** A company deploys an AI system that recognises employees' emotions from webcam feeds during work to flag who seems disengaged. Is this permitted under the EU AI Act?

**Expected references:** Article 5

**Key points:** emotion recognition, workplace, prohibited

*Notes:* Art. 5(1)(f) — emotion recognition in the workplace is a prohibited practice (paper §3.1 ban list). Distinct from V3's online-learning emotion-recognition tricky row.

### st_v4_002 — prohibited

**Q:** An AI system categorises people by inferring their race, political opinions and sexual orientation from their facial images. Which EU AI Act article does this violate?

**Expected references:** Article 5

**Key points:** biometric categorisation, prohibited, political

*Notes:* Art. 5(1)(g) — biometric categorisation inferring protected characteristics. Paper §3.1 ban list.

### st_v4_003 — prohibited

**Q:** A vendor builds a facial-recognition database by indiscriminately scraping images from the internet and CCTV footage. Is this a prohibited practice under the EU AI Act?

**Expected references:** Article 5

**Key points:** facial recognition, scraping, prohibited

*Notes:* Art. 5(1)(e) — untargeted scraping of facial images to build recognition databases. Paper §3.1 ban list.

### st_v4_004 — prohibited

**Q:** An AI app targets elderly users with cognitive decline, exploiting their condition to push them toward expensive subscriptions. Does the EU AI Act prohibit this?

**Expected references:** Article 5

**Key points:** exploit, vulnerabilities, prohibited

*Notes:* Art. 5(1)(b) — exploitation of vulnerabilities due to age or disability. Paper §3.1 ban list.

### st_v4_005 — prohibited

**Q:** Law enforcement wants to run real-time remote facial identification across cameras in a city square to scan all passers-by. What does the EU AI Act say about this?

**Expected references:** Article 5

**Key points:** real-time, biometric identification, law enforcement

*Notes:* Art. 5(1)(h) — real-time remote biometric identification in publicly accessible spaces by law enforcement (prohibited save narrow exceptions). Paper §3.1 ban list.

### st_v4_006 — high_risk

**Q:** An AI system is used as a safety component to manage the supply of electricity on a national grid. How is it classified and under which article?

**Expected references:** Article 6, Annex III

**Key points:** high-risk, critical infrastructure, Annex III

*Notes:* Annex III(2) — critical infrastructure (electricity supply). Art. 6 classification gateway. Risk-classification task.

### st_v4_007 — high_risk

**Q:** Before placing a high-risk AI system on the EU market, what conformity-assessment obligation must its provider complete under the EU AI Act?

**Expected references:** Article 43

**Key points:** conformity assessment, high-risk, provider

*Notes:* Art. 43 — conformity assessment procedure for high-risk AI. Obligation-generation task.

### st_v4_008 — high_risk

**Q:** What accuracy, robustness and cybersecurity requirements does the EU AI Act impose on a high-risk AI system?

**Expected references:** Article 15

**Key points:** accuracy, robustness, cybersecurity

*Notes:* Art. 15 — accuracy, robustness and cybersecurity for high-risk AI. Obligation-generation task.

### st_v4_009 — high_risk

**Q:** Does a provider of a stand-alone high-risk AI system have to register it anywhere before putting it into service in the EU, and under which article?

**Expected references:** Article 49

**Key points:** registration, EU database, high-risk

*Notes:* Art. 49 — registration of high-risk AI systems in the EU database. Obligation / article-retrieval task.

### st_v4_010 — high_risk

**Q:** An AI system verifies travellers' identities using biometrics at a border crossing for migration control. How does the EU AI Act classify it?

**Expected references:** Article 6, Annex III

**Key points:** high-risk, migration, Annex III

*Notes:* Annex III(7) — migration, asylum and border-control management. Art. 6 gateway. Risk-classification task.

### st_v4_011 — high_risk

**Q:** A public authority intends to deploy a high-risk AI system that affects access to social benefits. What assessment must it carry out before deployment under the EU AI Act?

**Expected references:** Article 27

**Key points:** fundamental rights, impact assessment, deployer

*Notes:* Art. 27 — fundamental rights impact assessment (FRIA) for deployers of certain high-risk AI. Obligation-generation task.

### st_v4_012 — limited

**Q:** A media company publishes an AI-generated deepfake video of a public figure. What transparency obligation does the EU AI Act impose?

**Expected references:** Article 50

**Key points:** deep fake, disclose, artificially generated

*Notes:* Art. 50(4) — deep-fake disclosure obligation. Limited-risk transparency. Obligation-generation task.

### st_v4_013 — limited

**Q:** An AI system generates synthetic audio and text content that is published online. How must this output be marked under the EU AI Act?

**Expected references:** Article 50

**Key points:** artificially generated, machine-readable, marked

*Notes:* Art. 50(2) — providers of generative AI must mark outputs as artificially generated in a machine-readable format. Limited-risk transparency.

### st_v4_014 — limited

**Q:** What does Article 10 of the EU AI Act require regarding the training, validation and testing datasets used by a high-risk AI system?

**Expected references:** Article 10

**Key points:** data governance, training, bias

*Notes:* Art. 10 — data and data governance (the paper grounds limited-risk data obligations here). Article-retrieval / QA task.

### st_v4_015 — limited

**Q:** A retailer's customer-support chatbot answers questions on its website. What does the EU AI Act require the chatbot to tell users?

**Expected references:** Article 50

**Key points:** inform, interacting, AI system

*Notes:* Art. 50(1) — natural persons must be informed they are interacting with an AI system. Limited-risk transparency.

### st_v4_016 — limited

**Q:** An emotion-recognition AI is used in a market-research focus group (not a workplace or school). What obligation does the EU AI Act impose on its deployer?

**Expected references:** Article 50

**Key points:** emotion recognition, inform, exposed

*Notes:* Art. 50(3) — outside the Art. 5(1)(f) workplace/education ban, an emotion-recognition system triggers a transparency duty to inform exposed persons. Limited-risk.

### st_v4_017 — minimal

**Q:** An AI spam filter automatically sorts incoming corporate email into junk and inbox folders. How does the EU AI Act classify it?

**Expected references:** Article 5, Article 6

**Key points:** minimal, spam, risk

*Notes:* Paper §3.1 explicit minimal-risk example (spam filter). Residual bucket: not prohibited (Art. 5), not high-risk (Art. 6).

### st_v4_018 — minimal

**Q:** A warehouse uses an AI tool to forecast inventory demand and re-order stock. What risk level applies under the EU AI Act?

**Expected references:** Article 5, Article 6

**Key points:** minimal, risk, obligations

*Notes:* Operational forecasting with no impact on fundamental rights — minimal-risk residual bucket. Risk-classification task.

### st_v4_019 — minimal

**Q:** A word processor uses AI to check spelling and grammar as the user types. Does the EU AI Act impose any specific obligations?

**Expected references:** Article 5, Article 6

**Key points:** minimal, risk, no specific

*Notes:* Productivity aid, no high-risk domain — minimal-risk residual bucket. Risk-classification task.

### st_v4_020 — minimal

**Q:** What is the difference between a minimal-risk and a high-risk AI system under the EU AI Act's risk-based approach?

**Expected references:** Article 5, Article 6

**Key points:** high-risk, minimal, risk

*Notes:* Conceptual QA on the paper's four-tier risk pyramid. Minimal is the residual after Art. 5 / Art. 6 checks.

---

## 3. Paper-V4 — tricky / decision-boundary (R99)

### tp_v4_001 — borderline_prohibition

**Q:** A retail app fires brief haptic buzzes on the phone, timed by AI to moments of hesitation, to nudge users into completing in-app purchases they were about to abandon. Is this a prohibited subliminal technique or merely aggressive marketing?

**Expected references:** Article 5

**Key points:** subliminal, prohibited, manipulat

*Notes:* Paper §4.2 'subliminal' decision-boundary edge case in a new modality (haptic). Art. 5(1)(a) subliminal/manipulative techniques.

### tp_v4_002 — borderline_prohibition

**Q:** A private insurance company runs an AI that aggregates customers' social-media activity into a general 'trustworthiness' score that limits their access to products. Does Article 5's social-scoring ban apply to a private actor like this?

**Expected references:** Article 5

**Key points:** social scoring, prohibited, detrimental

*Notes:* Art. 5(1)(c) social scoring applies to public AND private actors — tests whether the engine confines the ban to governments.

### tp_v4_003 — borderline_prohibition

**Q:** An AI predicts the likelihood that an individual will commit a crime based solely on profiling their personality traits and background, with no objective facts tied to a specific offence. Prohibited or high-risk law-enforcement use?

**Expected references:** Article 5

**Key points:** predict, profiling, prohibited

*Notes:* Art. 5(1)(d) — predictive policing based solely on profiling is prohibited; the engine must not down-grade it to Annex III(6) high-risk law enforcement.

### tp_v4_004 — borderline_prohibition

**Q:** Police want to use real-time facial recognition in a public square, but only to search for a suspect in an imminent terrorist threat. Is this allowed under the EU AI Act?

**Expected references:** Article 5

**Key points:** real-time, law enforcement, exception

*Notes:* Art. 5(1)(h) carve-out — real-time RBI is prohibited save narrow law-enforcement exceptions (imminent terrorist threat). Tests the exception, not a flat ban.

### tp_v4_005 — borderline_prohibition

**Q:** An online-learning platform uses an AI webcam tool to detect when students look confused so teachers can intervene. The vendor says it is 'just adaptive learning'. How does the EU AI Act treat it?

**Expected references:** Article 5

**Key points:** emotion recognition, education, prohibited

*Notes:* Art. 5(1)(f) — emotion recognition in education is prohibited; tests the 'adaptive learning' euphemism against the ban.

### tp_v4_006 — limited_vs_minimal

**Q:** A photo-gallery app uses AI to automatically tag and group your own private photos by content. No output is shared. Limited-risk (transparency) or minimal-risk under the EU AI Act?

**Expected references:** Article 5, Article 6

**Key points:** minimal, risk, transparency

*Notes:* Paper §5 limited-vs-minimal confusion. Private on-device tagging with no interaction/disclosure trigger → minimal residual.

### tp_v4_007 — limited_vs_minimal

**Q:** An email client embeds an AI that translates incoming messages into the user's language. Does the EU AI Act impose any transparency or other obligations?

**Expected references:** Article 5, Article 6

**Key points:** minimal, risk, obligations

*Notes:* Machine translation as a feature — minimal-risk residual; tests over-prediction of limited-risk on any 'AI feature'.

### tp_v4_008 — limited_vs_minimal

**Q:** A marketing team uses generative AI to draft promotional copy that is then published. The drafts are AI-generated text shown to the public. Is a transparency obligation triggered, and which one?

**Expected references:** Article 50

**Key points:** artificially generated, marked, text

*Notes:* Art. 50(2) — published AI-generated text must be marked; tests under-prediction (treating it as minimal).

### tp_v4_009 — limited_vs_minimal

**Q:** A voice assistant on a smart speaker always announces 'I am a virtual assistant' before responding. Has it already satisfied its EU AI Act transparency duty, and under which article?

**Expected references:** Article 50

**Key points:** inform, interacting, AI system

*Notes:* Art. 50(1) — interaction-disclosure already met; tests that the engine identifies the right limited-risk article rather than minimal.

### tp_v4_010 — high_risk_vs_limited

**Q:** A university uses an AI to score and rank applicants for admission. The vendor markets it as 'just a recommendation tool'. Is it high-risk under the EU AI Act, and on what basis?

**Expected references:** Annex III, Article 6

**Key points:** high-risk, education, Annex III

*Notes:* Annex III(3) — education/admissions scoring is high-risk; tests the 'recommendation tool' down-grade.

### tp_v4_011 — high_risk_vs_limited

**Q:** A bank uses an AI to pre-screen which loan applicants its staff should contact, calling it a 'marketing prioritisation' tool. Does the creditworthiness use make it high-risk?

**Expected references:** Annex III, Article 6

**Key points:** high-risk, creditworthiness, Annex III

*Notes:* Annex III(5)(b) — creditworthiness/credit-scoring is high-risk; tests the 'marketing' euphemism.

### tp_v4_012 — high_risk_vs_limited

**Q:** A hospital chatbot both answers patients' general questions AND triages the urgency of their symptoms to route care. Is the EU AI Act obligation a mere chatbot disclosure, or full high-risk treatment?

**Expected references:** Annex III, Article 6

**Key points:** high-risk, Annex III, health

*Notes:* Dual nature: Art. 50(1) chatbot disclosure AND Annex III/Art. 6 high-risk for the medical-triage function. Tests that the engine does not stop at limited-risk.

### tp_v4_013 — obligation_generation

**Q:** We import a high-risk AI system made by a US company and place it on the EU market under our own brand. What are our obligations as the importer under the EU AI Act?

**Expected references:** Article 23

**Key points:** importer, conformity, obligations

*Notes:* Art. 23 — importer obligations. Value-chain role the V3 tricky set did not cover.

### tp_v4_014 — obligation_generation

**Q:** We are a distributor that makes a high-risk AI system available on the EU market without modifying it. What does the EU AI Act require of us?

**Expected references:** Article 24

**Key points:** distributor, verify, obligations

*Notes:* Art. 24 — distributor obligations. Value-chain role new to V4.

### tp_v4_015 — obligation_generation

**Q:** We provide a general-purpose AI model trained with more than 10^25 FLOPs of compute. What additional obligations does the EU AI Act impose because of systemic risk?

**Expected references:** Article 55, Article 51

**Key points:** systemic risk, general-purpose, model

*Notes:* Art. 51 systemic-risk classification (10^25 FLOPs) + Art. 55 systemic-risk GPAI obligations. GPAI path.

### tp_v4_016 — obligation_generation

**Q:** A provider established outside the EU offers a high-risk AI system to EU users. What must it appoint inside the Union, and under which article?

**Expected references:** Article 22

**Key points:** authorised representative, established, Union

*Notes:* Art. 22 — authorised representative for non-EU providers of high-risk AI.

### tp_v4_017 — article_retrieval

**Q:** Which EU AI Act article governs the reporting of serious incidents involving a high-risk AI system?

**Expected references:** Article 73

**Key points:** serious incident, report, authorities

*Notes:* Art. 73 — reporting of serious incidents.

### tp_v4_018 — article_retrieval

**Q:** Which articles of the EU AI Act establish AI regulatory sandboxes to support innovation and SMEs?

**Expected references:** Article 57

**Key points:** sandbox, innovation, competent

*Notes:* Art. 57 — establishment of AI regulatory sandboxes.

### tp_v4_019 — article_retrieval

**Q:** Which EU AI Act article sets out the administrative fines and penalties for non-compliance?

**Expected references:** Article 99

**Key points:** penalties, fines, infringement

*Notes:* Art. 99 — penalties.

### tp_v4_020 — article_retrieval

**Q:** Which EU AI Act articles cover the conformity-assessment procedure, the EU declaration of conformity, and the CE marking for a high-risk AI system?

**Expected references:** Article 43, Article 47, Article 48

**Key points:** conformity, CE marking, declaration

*Notes:* Art. 43 conformity assessment + Art. 47 EU declaration of conformity + Art. 48 CE marking. Multi-article retrieval.

---

## 4. Paper-V3 — single-turn (R98)

### st_v3_001 — qa_task

**Q:** What is the primary purpose of the AI Act according to Article 1?

**Expected references:** Article 1

**Key points:** internal market, trustworthy, fundamental rights

*Notes:* Direct mapping from QA pairs file, Table 3 example. Art. 1 purpose statement; classic QA task.

### st_v3_002 — prohibited

**Q:** An AI system shows 'barely perceptible visual prompts' to increase subscription upgrades without users being aware. Is this prohibited under Article 5 of the EU AI Act?

**Expected references:** Article 5

**Key points:** subliminal, prohibited, consciousness

*Notes:* Paper §4.2 canonical edge-case example: 'barely perceptible visual prompt' subliminal-technique boundary. The paper explicitly flags this as an edge case testing the 'subliminal' decision boundary.

### st_v3_003 — prohibited

**Q:** An AI system assigns social credit scores to citizens based on their online behaviour, restricting access to public services for those with low scores. Which article prohibits this?

**Expected references:** Article 5

**Key points:** social scoring, prohibited, public services

*Notes:* Paper Table 2 canonical prohibited scenario: social scoring. Art. 5(1)(c) prohibited practice.

### st_v3_004 — prohibited

**Q:** An AI platform subtly nudges shoppers to purchase high-margin products through hidden audio cues without their conscious awareness. Is this an EU AI Act prohibited practice?

**Expected references:** Article 5

**Key points:** subliminal, prohibited, subconscious

*Notes:* Paper Table 2 verbatim example: 'hidden-audio influence platform'. Art. 5(1)(a) subliminal-technique prohibition.

### st_v3_005 — prohibited

**Q:** An AI system manipulates social media content to influence voting behaviour in an election. Is this prohibited or merely high-risk?

**Expected references:** Article 5

**Key points:** prohibited, manipulation, democratic

*Notes:* Paper §4.2 explicit edge case: 'AI that manipulates social media to influence voting' — paper notes it could look high-risk on the surface but is prohibited because it undermines democratic processes (Art. 5(1)(b) manipulation of elections context).

### st_v3_006 — high_risk

**Q:** Under what article and conditions does an AI system become classified as high-risk in the EU AI Act?

**Expected references:** Article 6, Annex III

**Key points:** high-risk, classification, Annex III

*Notes:* Paper hypothesis 2: 'high-risk category is analogous to Art. 6 + Annex III'. Article-retrieval task for the fundamental classification rule.

### st_v3_007 — high_risk

**Q:** A provider deploys an AI-based medical-imaging triage system in a hospital. What risk-management obligation does the EU AI Act impose on the provider?

**Expected references:** Article 9, Annex III

**Key points:** risk management, system, provider

*Notes:* Obligation-generation task (paper §4.1). Medical-imaging AI = Annex III(1) — provider must establish a risk-management system per Art. 9.

### st_v3_008 — high_risk

**Q:** What must a provider of a high-risk AI system include in the technical documentation required by the EU AI Act?

**Expected references:** Article 11, Annex IV

**Key points:** technical documentation, Annex IV, provider

*Notes:* Obligation-generation task. Art. 11 mandates technical documentation per Annex IV for all high-risk AI providers.

### st_v3_009 — high_risk

**Q:** What logging obligations apply to a provider of a high-risk AI system under the EU AI Act?

**Expected references:** Article 12

**Key points:** logging, automatically, traceability

*Notes:* Obligation-generation task: Art. 12 automatic event logging for high-risk AI systems.

### st_v3_010 — high_risk

**Q:** An AI system is used in employment to evaluate worker performance and determine terminations. Which Annex III category covers it?

**Expected references:** Annex III, Article 6

**Key points:** employment, performance, high-risk

*Notes:* Relevant-article retrieval task (paper §4.1). Employment-decision AI maps to Annex III(4)(b). Paper generates 86 high-risk scenarios; employment is a key domain.

### st_v3_011 — high_risk

**Q:** What human-oversight obligations does the EU AI Act require for high-risk AI systems under Article 14?

**Expected references:** Article 14

**Key points:** human oversight, natural persons, monitor

*Notes:* Obligation-generation task. Art. 14 human-oversight requirement for high-risk AI — key obligation the paper's 339 scenarios test.

### st_v3_012 — limited

**Q:** Which articles of the EU AI Act ground the 'limited-risk' category, and what do they require?

**Expected references:** Article 50, Article 10

**Key points:** transparency, data governance, limited

*Notes:* Paper hypothesis 3 verbatim: 'limited-risk is grounded in Art. 50 and Art. 10'. Risk-level classification + article retrieval combined.

### st_v3_013 — limited

**Q:** A chatbot interacts with consumers without disclosing it is AI. What EU AI Act obligation applies?

**Expected references:** Article 50

**Key points:** chatbot, disclosure, artificial intelligence

*Notes:* Art. 50(1) chatbot-disclosure obligation. Paper's 84 limited-risk scenarios focus on transparency obligations; chatbots are the canonical limited-risk use case.

### st_v3_014 — limited

**Q:** An AI system generates synthetic images. What AI Act transparency obligation applies to the provider?

**Expected references:** Article 50

**Key points:** synthetic, label, generated

*Notes:* Art. 50(2) deep-fake / synthetic content labelling obligation. Limited-risk transparency task.

### st_v3_015 — limited

**Q:** What data-governance obligations does Article 10 of the EU AI Act impose on providers of high-risk AI?

**Expected references:** Article 10

**Key points:** training data, data governance, quality

*Notes:* Art. 10 data-governance requirement. Paper hypothesis 3 explicitly lists Art. 10 as a grounding article for limited-risk alongside Art. 50.

### st_v3_016 — limited

**Q:** A recommendation system operates on an online platform and is not classified as high-risk. Does the EU AI Act impose any transparency obligations on it?

**Expected references:** Article 50

**Key points:** transparency, not high-risk, information

*Notes:* Art. 50(3) — limited-risk recommendation systems must signal their AI nature. Paper's limited category explicitly covers 'operates in or adjacent to critical domains but does not pose significant harm'.

### st_v3_017 — minimal

**Q:** An AI-powered spam filter classifies emails for individual users. What risk level is this under the EU AI Act and what obligations apply?

**Expected references:** Article 5, Article 6

**Key points:** minimal, no specific, residual

*Notes:* Paper hypothesis 4: 'minimal = residual if not prohibited, not high-risk, not triggering Art. 50/10'. The paper uses spam filters as a canonical minimal-risk example (§3.1). Engine should state minimal risk / no specific AI Act obligations.

### st_v3_018 — minimal

**Q:** A video game uses an AI to adapt difficulty in real time. What EU AI Act classification and obligations apply?

**Expected references:** Article 5, Article 6

**Key points:** minimal, exempt, no significant

*Notes:* Paper §3.1 verbatim: 'video games' as a minimal-risk example. Residual bucket — no prohibited practice, not Annex III, no Art. 50 chatbot interaction.

### st_v3_019 — minimal

**Q:** What distinguishes a 'minimal-risk' AI system from a 'limited-risk' one under the EU AI Act risk pyramid?

**Expected references:** Article 5, Article 6, Article 50

**Key points:** minimal, limited, transparency

*Notes:* Paper §5 / Table 4 discussion: limited/minimal boundary is the hardest classification (limited F1 0.65, minimal F1 0.45). Tests the engine's ability to explain the decision boundary between residual and limited tiers.

### st_v3_020 — minimal

**Q:** An AI model recommends playlists on a music streaming service with no user profiling for protected characteristics. What AI Act category applies?

**Expected references:** Article 5, Article 6

**Key points:** minimal, no significant, residual

*Notes:* Paper §5 result discussion: minimal scenarios are 'underpredicted' (recall 0.29, precision 0.97) because keyword overlap with limited is high. Tests the engine on a clean minimal case.

---

## 5. Paper-V3 — tricky / decision-boundary (R98)

### tp_v3_001 — borderline_prohibition

**Q:** An AI displays product banners at 50 ms — below the average human conscious perception threshold — to nudge purchases. Is this prohibited under Article 5 as a subliminal technique?

**Expected references:** Article 5

**Key points:** subliminal, prohibited, consciousness

*Notes:* Paper §4.2 canonical edge case: 'barely perceptible visual prompt' that 'may be so rapid that the user is not influenced or affected'. Engine must apply the subliminal-technique test from Art. 5(1)(a) and NOT simply look at display duration.

### tp_v3_002 — borderline_prohibition

**Q:** An AI recommendation engine uses micro-targeted messages exploiting a user's documented cognitive fatigue (measured via engagement dips) to push premium upgrades during low-awareness moments. Prohibited or merely high-risk?

**Expected references:** Article 5

**Key points:** vulnerability, prohibited, exploitation

*Notes:* Art. 5(1)(b) exploitation-of-vulnerabilities prohibition. Paper §3.1 explicitly lists this as a prohibited practice. Engine must classify as prohibited, not just high-risk, because the vulnerability is deliberately exploited.

### tp_v3_003 — borderline_prohibition

**Q:** An AI curates news feeds using techniques shown in A/B tests to increase political polarisation in order to maximise engagement. Is this a prohibited manipulation or a high-risk system?

**Expected references:** Article 5

**Key points:** manipulation, democratic, prohibited

*Notes:* Paper §4.2: 'AI that manipulates social media to influence voting behaviour — on high-level observation this appears high-risk, however independently voting could be considered a fundamental right.' Manipulation of democratic discourse → Art. 5(1)(b) / (1)(a).

### tp_v3_004 — borderline_prohibition

**Q:** A debt-collection firm's AI infers which debtors are financially desperate (from location, purchase history, late payments) and times calls to maximise psychological pressure. Is this prohibited?

**Expected references:** Article 5

**Key points:** vulnerability, exploitation, prohibited

*Notes:* Art. 5(1)(b) exploitation of vulnerability (financial distress). Paper's prohibited scenarios include exploitation of vulnerability; financial context makes this a decision-boundary test.

### tp_v3_005 — borderline_prohibition

**Q:** An AI system predicts individual criminal offence risk scores from social behaviour data and passes them to court clerks as 'advisory' information. Does the advisory framing make it permissible?

**Expected references:** Article 5, Annex III

**Key points:** criminal, prohibited, prediction

*Notes:* Paper §3.1: 'individual criminal-offence risk prediction' is listed as one of the eight prohibited practices. The 'advisory' framing does not alter the prohibition if the AI actually makes individual predictions not based on objective facts (Art. 5(1)(d)).

### tp_v3_006 — limited_vs_minimal

**Q:** An AI content moderator on a small niche forum flags posts that violate community guidelines, with no emotion recognition or biometric data. Which risk tier applies and why?

**Expected references:** Article 5, Article 6, Article 50

**Key points:** minimal, no significant, residual

*Notes:* Paper §5 confusion: content moderation AI could look limited (adjacent to critical domain: free expression) but on a small forum with no protected-characteristic inference it is minimal. Precision=0.97 on minimal means engine should strongly say minimal only when truly residual.

### tp_v3_007 — limited_vs_minimal

**Q:** An AI chatbot answers FAQ questions for a municipality's website about road closures. Is it limited-risk (Art. 50 disclosure) or minimal-risk?

**Expected references:** Article 50

**Key points:** chatbot, disclosure, limited

*Notes:* Paper hypothesis 3 vs hypothesis 4 boundary. The chatbot interacts with natural persons (Art. 50(1) trigger) → limited-risk, NOT minimal. Engine must apply the chatbot-disclosure test even for trivial FAQ use cases.

### tp_v3_008 — limited_vs_minimal

**Q:** An AI writing assistant autocompletes sentences for a law firm's internal documents — not customer-facing, no emotion recognition. Limited or minimal risk?

**Expected references:** Article 5, Article 6

**Key points:** minimal, internal, residual

*Notes:* Paper recall=0.29 on minimal → engine systematically mislabels minimal as limited. This case: internal writing tool with no customer interaction → minimal, not limited (no Art. 50 chatbot interaction with natural persons, not Art. 10 high-risk data).

### tp_v3_009 — limited_vs_minimal

**Q:** A fitness app uses AI to generate personalised workout plans based on user-logged activity data. It does not make medical diagnoses or interact with health providers. What risk level and obligations?

**Expected references:** Article 5, Article 6

**Key points:** minimal, no significant, wellness

*Notes:* Paper §5 boundary: wellness apps are minimal, not high-risk (no Annex III(1) medical diagnosis) and not limited (no chatbot interaction, no Art. 10 training-data obligations). Tests the 'adjacent to medical domain but not high-risk' boundary.

### tp_v3_010 — high_risk_vs_limited

**Q:** An AI system provides personalised credit-rating advice to retail customers via a chatbot interface. Is it high-risk (Annex III credit scoring) or only limited-risk (Art. 50 chatbot disclosure)?

**Expected references:** Annex III, Article 50

**Key points:** high-risk, Annex III, credit

*Notes:* Credit-rating AI = Annex III(5)(b) high-risk. Being delivered via a chatbot does NOT reduce it to Art. 50 limited-risk — the chatbot disclosure obligation is cumulative, not a substitute for Annex III classification. Paper §4.2 discusses similar layering.

### tp_v3_011 — high_risk_vs_limited

**Q:** An AI emotion-recognition tool deployed by an online learning platform monitors whether students are paying attention. Is this prohibited (Art. 5), high-risk (Annex III), or limited?

**Expected references:** Article 5

**Key points:** education, prohibited, emotion recognition

*Notes:* Art. 5(1)(f) prohibits emotion recognition in education contexts. Paper §3.1 lists this as a prohibited practice. Engine must NOT classify as high-risk or limited — the prohibition applies regardless of the 'just monitoring attention' framing.

### tp_v3_012 — high_risk_vs_limited

**Q:** An AI system evaluates and ranks job applicants in the hiring process using a recommendation score. The provider says it only 'assists' recruiters, not replaces them. High-risk or limited?

**Expected references:** Annex III, Article 6

**Key points:** employment, high-risk, Annex III

*Notes:* Annex III(4)(a) — AI for recruitment and candidate selection is high-risk regardless of whether it 'assists' or 'replaces' a human. Paper generates 86 high-risk scenarios, employment is a key domain. Engine must resist the 'it's just advisory' framing.

### tp_v3_013 — obligation_generation

**Q:** We are a deployer of a high-risk AI system for credit scoring. What are our key obligations under the EU AI Act, distinct from the provider's obligations?

**Expected references:** Article 26, Annex III

**Key points:** deployer, instructions, monitoring

*Notes:* Paper §4.1 obligation-generation task. Deployer obligations under Art. 26 — distinct from provider obligations (Art. 16). Engine must not conflate the two. Paper scenario template distinguishes role (Provider/Deployer) as a required field.

### tp_v3_014 — obligation_generation

**Q:** We are a provider of a high-risk AI for critical infrastructure monitoring. List the pre-market obligations before we can place the system on the EU market.

**Expected references:** Article 9, Article 10, Article 11, Article 12, Article 13, Article 14, Article 15, Article 43

**Key points:** risk management, technical documentation, conformity

*Notes:* Paper §3.1 lists the pre-market obligation stack verbatim: 'risk management, high-quality datasets, activity logging, extensive technical documentation, clear information for deployers, human oversight, accuracy/robustness/cybersecurity'. Engine must surface the full obligation chain (Arts. 9-15 + Art. 43 conformity).

### tp_v3_015 — obligation_generation

**Q:** A provider of an AI system that performs real-time biometric identification has satisfied Article 43 conformity assessment. What registration obligations remain before market placement?

**Expected references:** Article 49, Article 51

**Key points:** registration, EU database, notified body

*Notes:* Art. 49 EU-database registration obligation post-conformity. Real-time RBI is Annex III(1) — must register in the EU AI database. Tests the post-conformity obligation chain.

### tp_v3_016 — obligation_generation

**Q:** We are a provider deploying an AI-based patient-triage system in a hospital. The hospital is the deployer. What accuracy and robustness obligations does the EU AI Act impose on us?

**Expected references:** Article 15, Annex III

**Key points:** accuracy, robustness, cybersecurity

*Notes:* Paper §3.1 obligation list item: 'strong standards of accuracy, robustness, and cybersecurity'. Art. 15 covers these for high-risk providers. Medical-imaging = Annex III(1).

### tp_v3_017 — article_retrieval

**Q:** Which articles of the EU AI Act apply to a provider that places a high-risk AI system on the market in the EU with no EU establishment?

**Expected references:** Article 22, Article 16

**Key points:** authorised representative, no establishment, provider

*Notes:* Relevant-article retrieval task. Non-EU provider must appoint an authorised representative (Art. 22) before market placement and satisfies provider obligations via Art. 16.

### tp_v3_018 — article_retrieval

**Q:** What articles govern the relationship between accuracy requirements and post-market monitoring for high-risk AI systems?

**Expected references:** Article 15, Article 72

**Key points:** accuracy, post-market, monitoring

*Notes:* Multi-article retrieval: Art. 15 (accuracy/robustness) + Art. 72 (post-market monitoring). Paper's 339 scenarios link an average of 9.8 articles per scenario; multi-article retrieval is the core task.

### tp_v3_019 — article_retrieval

**Q:** Which articles does the EU AI Act reference when regulating AI use in migration, border control, and asylum procedures?

**Expected references:** Annex III, Article 6

**Key points:** migration, border, Annex III

*Notes:* Annex III(7) covers migration/border/asylum AI as high-risk. Art. 6 is the classification gateway. Multi-article retrieval task testing a domain the paper's 86 high-risk scenarios cover.

### tp_v3_020 — article_retrieval

**Q:** What EU AI Act articles regulate AI systems used by law enforcement for individual criminal-risk profiling?

**Expected references:** Article 5, Annex III

**Key points:** law enforcement, criminal, prohibited

*Notes:* Dual-regime question: Art. 5(1)(d) prohibits predictive-policing AI based on profiling; Annex III(6) makes law-enforcement high-risk AI subject to the full obligation stack for non-prohibited uses. Tests multi-article retrieval across the prohibited/high-risk boundary.

---

## 6. V2 — tricky single-turn (7 categories: omnibus / role_ambiguity / conflict / borderline_prohibition / gpai / cross_framework / near_oos)

### tr_v2_001 — omnibus

**Q:** After the 7 May 2026 Digital Omnibus agreement, when do Annex III high-risk obligations actually start applying?

**Expected references:** Article 113

**Key points:** 2 December 2027, Annex III

*Notes:* Post-Omnibus Annex III date is 2 Dec 2027 (was 2 Aug 2026). Engine must NOT cite the older date.

### tr_v2_002 — omnibus

**Q:** Did the Digital Omnibus push back the prohibited-AI deadline?

**Expected references:** Article 5, Article 113

**Key points:** 2 February 2025, still, applies

*Notes:* Art. 5 prohibitions were NOT deferred. Engine must reject the implicit deferral framing.

### tr_v2_003 — omnibus

**Q:** What's the new GPAI compute threshold from the Commission's July 2025 Guidelines?

**Expected references:** Article 51

**Key points:** 10, FLOPs, general-purpose

*Notes:* Post-Guidelines threshold: 10²³ FLOPs to qualify as GPAI under Art. 51, 10²⁵ for systemic risk. Engine must surface 10²³.

### tr_v2_004 — omnibus

**Q:** Is the EU AI Office allowed to impose fines directly on a GPAI provider, or only national authorities?

**Expected references:** Article 101

**Key points:** Commission, fines, directly

*Notes:* Art. 101 — Commission imposes fines on GPAI providers. Different from Art. 99 national-authority route.

### tr_v2_005 — omnibus

**Q:** We grew from a 30-employee SME to a 220-employee company last quarter. Do we lose AI Act SME privileges?

**Expected references:** Article 62, Article 63

**Key points:** small mid-cap, preserve, extended

*Notes:* Digital Omnibus extended SME privileges to small mid-caps (Art. 62/63). Engine must NOT say privileges are lost on graduation from SME.

### tr_v2_006 — omnibus

**Q:** We're a GPAI provider that fine-tuned another model with 35% of the base model's compute. Did we become the new provider?

**Expected references:** Article 25, Article 51

**Key points:** one-third, modifier, provider

*Notes:* Digital Omnibus 1/3 fine-tune rule. 35% > 1/3 → modifier becomes new provider. Engine must apply the rule.

### tr_v2_007 — role_ambiguity

**Q:** We built an internal AI for our own HR use — never released externally. Are we a provider or just a deployer?

**Expected references:** Article 3, Article 16, Article 26

**Key points:** both, provider, deployer

*Notes:* Internal-only builder is BOTH provider (because they built it) AND deployer (because they use it). Engine must address both stacks.

### tr_v2_008 — role_ambiguity

**Q:** A non-EU company sells AI to EU customers but has no EU establishment. Who is liable on the EU side?

**Expected references:** Article 22

**Key points:** authorised representative, established, mandate

*Notes:* Art. 22 forces non-EU providers to appoint an authorised representative — that representative carries EU-side obligations.

### tr_v2_009 — role_ambiguity

**Q:** An importer rebrands a high-risk AI under its own name before selling it on. Do they become the provider?

**Expected references:** Article 25

**Key points:** name, trademark, provider

*Notes:* Art. 25(1)(a) — putting name/trademark on a high-risk AI flips importer/distributor into provider.

### tr_v2_010 — role_ambiguity

**Q:** Our SaaS lets enterprise customers configure a CV-screening AI for their hiring. Are we the provider or are they?

**Expected references:** Article 3, Article 25

**Key points:** provider, configure, intended purpose

*Notes:* If customer significantly configures intended purpose, they become the provider via Art. 25 substantial-modification path. Engine must surface that the role is not pre-determined.

### tr_v2_011 — role_ambiguity

**Q:** We resell a CE-marked high-risk biometric AI without modifying it. What are our obligations as distributor?

**Expected references:** Article 24

**Key points:** distributor, verify, CE marking

*Notes:* Art. 24 distributor obligations. Engine must NOT confuse with importer (Art. 23) or provider (Art. 16).

### tr_v2_012 — conflict

**Q:** If my chatbot is also a high-risk medical-triage AI, does Article 13 transparency or Article 50 chatbot-disclosure apply?

**Expected references:** Article 13, Article 50

**Key points:** both, cumulative, apply

*Notes:* Both apply cumulatively. Art. 13 (provider→deployer) and Art. 50 (provider→user) target different stakeholders.

### tr_v2_013 — conflict

**Q:** Our Annex IV technical documentation contains trade secrets. Article 78 says authorities must keep them confidential — can we refuse to share them under Article 11?

**Expected references:** Article 11, Article 78

**Key points:** confidentiality, obligation, still required

*Notes:* Confidentiality under Art. 78 does NOT relieve the documentation obligation under Art. 11. Engine must reject the false choice.

### tr_v2_014 — conflict

**Q:** A FRIA under Article 27 and a conformity assessment under Article 43 cover overlapping fundamental-rights checks. Can we skip one?

**Expected references:** Article 27, Article 43

**Key points:** distinct, both, deployer

*Notes:* FRIA is deployer-side, conformity assessment is provider-side. Engine must not let the user collapse them.

### tr_v2_015 — conflict

**Q:** Article 13 says transparency, Article 86 says right to explanation. Aren't they the same thing?

**Expected references:** Article 13, Article 86

**Key points:** different, provider, individual

*Notes:* Art. 13 is structural (provider designs transparency mechanism); Art. 86 is individual-rights (affected person gets per-decision explanation). Engine must distinguish.

### tr_v2_016 — borderline_prohibition

**Q:** Is biometric categorization for age detection in a retail store prohibited under Article 5(1)(g)?

**Expected references:** Article 5

**Key points:** age, not, permitted

*Notes:* Age categorization is NOT in the Art. 5(1)(g) prohibited list (race, political opinion, trade-union, religion, sex life, sexual orientation). Engine must NOT over-prohibit.

### tr_v2_017 — borderline_prohibition

**Q:** We use emotion recognition in a medical-device AI to monitor pain in non-verbal patients. Is that prohibited?

**Expected references:** Article 5

**Key points:** medical, carve-out, permitted

*Notes:* Art. 5(1)(f) prohibits emotion recognition in workplace/education, but carves out medical and safety reasons. Engine must surface the carve-out.

### tr_v2_018 — borderline_prohibition

**Q:** Is real-time RBI in public spaces prohibited for police investigating ongoing terrorist attacks?

**Expected references:** Article 5

**Key points:** terrorist, exception, authorisation

*Notes:* Art. 5(1)(h)(iii) — imminent threat / terrorist attack carve-out, subject to prior authorisation. Engine must apply the exception.

### tr_v2_019 — borderline_prohibition

**Q:** We scrape facial images from publicly available CCTV footage to build a recognition database. Is that prohibited?

**Expected references:** Article 5

**Key points:** untargeted, scraping, prohibited

*Notes:* Art. 5(1)(e) prohibits untargeted scraping of facial images from internet OR CCTV for facial-recognition databases. Engine must NOT miss the CCTV branch (commonly overlooked vs. the internet-scraping branch).

### tr_v2_020 — borderline_prohibition

**Q:** We use AI to score creditworthiness on a 1-10 scale used internally only — not shared, not affecting public services. Is that social scoring?

**Expected references:** Article 5, Annex III

**Key points:** credit, not, Annex III

*Notes:* Credit scoring is Annex III(5)(b) high-risk, NOT social scoring (Art. 5(1)(c)). The distinction: social scoring uses unrelated context to disadvantage. Engine must NOT mis-route to Art. 5 prohibition.

### tr_v2_021 — gpai

**Q:** Our GPAI is open-weights but we trained at exactly 1×10²⁵ FLOPs. Do we still get the Article 53(2) open-weights carve-out?

**Expected references:** Article 53, Article 55

**Key points:** systemic, carve-out, not apply

*Notes:* Art. 53(2) open-weights carve-out does NOT apply to systemic-risk GPAI. At 10²⁵ FLOPs, the model is systemic-risk per Art. 51(2). Engine must rebut.

### tr_v2_022 — gpai

**Q:** We fine-tune a third-party GPAI with 30% of the base compute. Are we now the provider?

**Expected references:** Article 25, Article 51

**Key points:** one-third, below, not

*Notes:* 30% is BELOW the 1/3 fine-tune threshold per Commission Guidelines + Digital Omnibus. Modifier does NOT become provider. Boundary opposite of tr_v2_006.

### tr_v2_023 — gpai

**Q:** Does the AI Act require GPAI providers to disclose training data sources?

**Expected references:** Article 53

**Key points:** training data, summary, sufficiently detailed

*Notes:* Art. 53(1)(d) — sufficiently detailed summary of training content. Distinct from the 'list all data sources' framing the user may carry.

### tr_v2_024 — gpai

**Q:** If we use a GPAI as a component in our high-risk AI, do GPAI obligations transfer to us?

**Expected references:** Article 25, Article 53

**Key points:** value chain, cooperation, provider

*Notes:* Art. 25 + Art. 53(3) — value-chain cooperation obligation. The integrating provider takes on its own obligations but the GPAI provider's obligations remain with the GPAI provider.

### tr_v2_025 — gpai

**Q:** We're a GPAI provider with no EU establishment. Can we appoint our European customer as our authorised representative?

**Expected references:** Article 54

**Key points:** GPAI, authorised representative, established

*Notes:* Art. 54 — GPAI authorised representative is a SEPARATE provision from Art. 22 (high-risk authorised rep). Engine must cite the GPAI-specific Article 54.

### tr_v2_026 — cross_framework

**Q:** Our medical-device AI is already CE-marked under MDR. Do we still need a separate AI Act conformity assessment?

**Expected references:** Article 43, Annex I

**Key points:** integrated, MDR, Annex I

*Notes:* Art. 43(3) + Annex I — for Annex I product safety AI, AI Act conformity assessment integrates with existing sectoral conformity (e.g., MDR). Engine must explain the integration, not duplicate.

### tr_v2_027 — cross_framework

**Q:** Does our existing GDPR Article 35 DPIA satisfy the Article 27 FRIA requirement?

**Expected references:** Article 27

**Key points:** does not, FRIA, in addition

*Notes:* A DPIA does NOT replace a FRIA. The FRIA can build on the DPIA but Art. 27 requires its own deliverable. Engine must reject the substitution.

### tr_v2_028 — cross_framework

**Q:** Our high-risk AI provides cybersecurity for critical infrastructure. We already report incidents under NIS2. Do AI Act incident-reporting obligations still apply?

**Expected references:** Article 73

**Key points:** serious incident, in addition, AI Act

*Notes:* NIS2 + AI Act incident reporting are PARALLEL, not substitutive. Art. 73 is AI-specific serious-incident reporting. Engine must keep them distinct.

### tr_v2_029 — near_oos

**Q:** What are the algorithmic transparency obligations for a Very Large Online Platform's content-moderation AI?

**Expected references:** —

**Key points:** Digital Services Act, DSA, not the EU AI Act

*Notes:* VLOP algorithmic-transparency is DSA (Art. 27, Art. 39 DSA), NOT AI Act. Engine should refuse-with-pointer rather than answer with AI Act citations.

### tr_v2_030 — near_oos

**Q:** If a high-risk AI causes property damage to a customer, what AI-Act liability rules apply?

**Expected references:** —

**Key points:** Product Liability, PLD, not the EU AI Act

*Notes:* AI civil liability is governed by the revised Product Liability Directive + (eventually) the AI Liability Directive, NOT the AI Act itself. The AI Act regulates compliance, not damages.

### tr_v2_031 — near_oos

**Q:** We're a designated essential-services entity using AI for SOC operations. What cyber-resilience obligations apply to the AI itself?

**Expected references:** —

**Key points:** NIS2, Cyber Resilience Act, not the EU AI Act

*Notes:* Cyber-resilience for essential-services SOCs is NIS2 / CRA territory. AI Act covers AI-specific risks but not entity-level cyber resilience. Engine should refuse-with-pointer.

---

## 7. Paper-V4 — multi-turn (R99, 3-turn conversations)

### mt_v4_001

**Conversation:**

1. **user:** We run an internal AI tool that summarises team meeting notes for our own staff. What risk level under the AI Act?
2. **assistant:** An internal meeting-summary tool with no high-risk domain and no public interaction is minimal-risk; no specific obligations apply.
3. **user:** We're adding a feature that reads employees' facial expressions during the meeting to score their engagement. Does anything change?

**Expected final references:** Article 5

**Expected final key points:** emotion recognition, workplace, prohibited

*Notes:* Minimal → prohibited. Adding workplace emotion recognition flips it to an Art. 5(1)(f) prohibited practice. Engine must update its prior minimal verdict.

### mt_v4_002

**Conversation:**

1. **user:** We provide a high-risk AI system for sorting CVs in hiring. We've already set up a risk-management system and data governance. What's the next obligation?
2. **assistant:** With risk management (Article 9) and data governance (Article 10) in place, you next prepare technical documentation and ensure logging and human oversight.
3. **user:** Documentation and oversight are done. Before we put it on the market, what procedure must we pass and how is conformity demonstrated?

**Expected final references:** Article 43

**Expected final key points:** conformity assessment, high-risk, market

*Notes:* Obligation-chain build to the conformity-assessment step (Art. 43) before placing a high-risk AI on the market.

### mt_v4_003

**Conversation:**

1. **user:** We train a general-purpose AI model. What baseline AI Act obligations apply to us as the model provider?
2. **assistant:** Providers of general-purpose AI models have transparency and documentation obligations under Article 53, including technical documentation and a training-data summary.
3. **user:** Our next training run used 3x10^25 FLOPs of compute. Does that change our classification and obligations?

**Expected final references:** Article 51, Article 55

**Expected final key points:** systemic risk, 10^25, general-purpose

*Notes:* GPAI standard → systemic-risk. 10^25 FLOPs crosses the Art. 51 systemic-risk threshold, adding Art. 55 obligations.

### mt_v4_004

**Conversation:**

1. **user:** We are a deployer of a third-party high-risk AI system for credit scoring. What are our duties as a deployer?
2. **assistant:** As a deployer you must use the system per its instructions, ensure human oversight and monitor its operation under Article 26.
3. **user:** We've now substantially modified the model and put our own brand on it. Does our legal role change?

**Expected final references:** Article 25

**Expected final key points:** provider, substantial modification, obligations

*Notes:* Role flip: substantial modification + rebrand makes the deployer a provider under Art. 25(1), inheriting provider obligations.

### mt_v4_005

**Conversation:**

1. **user:** We offer an AI tutoring chatbot that helps students study. It tells users it's an AI. What risk level?
2. **assistant:** An educational chatbot that discloses it is AI is limited-risk under Article 50(1).
3. **user:** We're extending it to score students' final exams and decide who passes the course. Does the classification change?

**Expected final references:** Annex III, Article 6

**Expected final key points:** high-risk, education, Annex III

*Notes:* Limited → high-risk. Exam scoring that determines access to education is Annex III(3) high-risk via the Art. 6 gateway.

### mt_v4_006

**Conversation:**

1. **user:** A high-risk AI system is built by a company in Japan with no EU presence. We buy it and bring it into the EU market. Who is responsible for AI Act compliance?
2. **assistant:** Bringing a third-country high-risk AI system onto the EU market makes you the importer, with verification duties.
3. **user:** What exactly must we, as the importer, verify before placing it on the market?

**Expected final references:** Article 23

**Expected final key points:** importer, conformity assessment, verify

*Notes:* Importer obligations (Art. 23): verify conformity assessment, CE marking, documentation before market placement.

### mt_v4_007

**Conversation:**

1. **user:** We are a municipal authority planning to deploy a high-risk AI system that decides eligibility for housing benefit. What's our headline obligation as a deployer?
2. **assistant:** As a public-body deployer of a high-risk AI affecting access to essential services, you have Article 26 deployer duties.
3. **user:** Is there a specific assessment we must run before we start, given we are a public authority?

**Expected final references:** Article 27

**Expected final key points:** fundamental rights, impact assessment, deployer

*Notes:* Public-body deployer of Annex III high-risk AI must run a fundamental-rights impact assessment (Art. 27).

### mt_v4_008

**Conversation:**

1. **user:** Our high-risk recruitment AI is trained on historical hiring data. We're worried it could be biased. Which AI Act article governs the training data?
2. **assistant:** Article 10 governs data and data governance, including examining datasets for bias and ensuring they are relevant and representative.
3. **user:** Concretely, what data-quality and bias steps does that article require us to take?

**Expected final references:** Article 10

**Expected final key points:** data governance, bias, representative

*Notes:* Art. 10 data-governance obligations: bias examination, relevance/representativeness of training/validation/testing sets.

### mt_v4_009

**Conversation:**

1. **user:** Our high-risk AI medical-triage system is now live in hospitals. What ongoing duty do we have after deployment?
2. **assistant:** Providers must operate a post-market monitoring system under Article 72 to track the system's performance in use.
3. **user:** Last week the system caused a patient to be mis-triaged and harmed. What must we do now under the AI Act?

**Expected final references:** Article 73

**Expected final key points:** serious incident, report, authorities

*Notes:* Post-market monitoring (Art. 72) → a serious incident triggers the Art. 73 reporting duty to market-surveillance authorities.

### mt_v4_010

**Conversation:**

1. **user:** We deploy a high-risk AI that decides who gets a loan. An applicant was refused. What does the AI Act say we owe them?
2. **assistant:** Affected persons subject to high-risk AI decisions have rights to information about the system's role in the decision.
3. **user:** The applicant now formally demands to know why the AI denied them. Which article gives them that right?

**Expected final references:** Article 86

**Expected final key points:** explanation, decision, affected

*Notes:* Art. 86 — right to explanation of individual decision-making for persons affected by high-risk AI.

### mt_v4_011

**Conversation:**

1. **user:** We sell an AI spam filter that sorts junk email for businesses. What AI Act obligations apply?
2. **assistant:** A spam filter is a textbook minimal-risk system; no specific AI Act obligations apply beyond voluntary good practice.
3. **user:** We added an AI that auto-suggests canned replies. Still minimal, or have we crossed into a regulated tier?

**Expected final references:** Article 5, Article 6

**Expected final key points:** minimal, risk, obligations

*Notes:* Minimal stays minimal — a reply-suggestion feature does not trigger Art. 5 / Art. 6 / Art. 50. Tests over-escalation.

### mt_v4_012

**Conversation:**

1. **user:** We run an ad-targeting AI that groups users by their stated interests for marketing. What risk level?
2. **assistant:** Interest-based ad targeting that does not infer protected characteristics is generally limited or minimal-risk.
3. **user:** To sharpen targeting we now infer users' religious beliefs and political opinions from their biometric data. Is that a problem?

**Expected final references:** Article 5

**Expected final key points:** biometric categorisation, prohibited, political

*Notes:* Limited/minimal → prohibited. Inferring protected characteristics from biometric data is an Art. 5(1)(g) prohibited practice.

---

## 8. Paper-V3 — multi-turn (R98)

### mt_v3_001

**Conversation:**

1. **user:** We're building an AI writing assistant for internal employee use — autocompletes text in our internal wiki. What AI Act obligations apply?
2. **assistant:** An internal writing tool with no external users and no high-risk domain is minimal-risk under the AI Act. No specific obligations apply beyond the general good-practice provisions.
3. **user:** We're now exposing the same AI via a chat widget on our public website so customers can ask questions about our products.

**Expected final references:** Article 50

**Expected final key points:** chatbot, disclosure, AI

*Notes:* Cross-turn escalation: internal minimal → public chatbot limited. Art. 50(1) chatbot disclosure applies once natural persons can interact with it. Engine must update its prior verdict.

### mt_v3_002

**Conversation:**

1. **user:** We run a chatbot that gives general financial tips to users — things like 'save 10% of your salary'. What risk level?
2. **assistant:** General financial wellness tips with no individualised credit assessment are limited-risk under Article 50 (chatbot disclosure obligation applies).
3. **user:** We're extending the chatbot to evaluate individual loan applications and produce credit scores that lenders actually rely on.

**Expected final references:** Annex III, Article 6

**Expected final key points:** high-risk, credit, Annex III

*Notes:* Limited → high-risk escalation. Adding individualised credit-scoring to a chatbot flips it to Annex III(5)(b) high-risk. Engine must update its prior verdict and explain the Art. 6 + Annex III gateway.

### mt_v3_003

**Conversation:**

1. **user:** We are a provider of an AI system that scores candidates in our recruitment process. What is the first obligation we need to fulfil?
2. **assistant:** Recruitment AI is Annex III(4)(a) high-risk. Your first obligation is to establish and implement a risk-management system under Article 9.
3. **user:** What comes next after risk management?
4. **assistant:** Article 10 data-governance requirements: training, validation, and testing data must be relevant, representative, and free from errors.
5. **user:** We've done both. What are the remaining pre-market obligations before we can place this on the EU market?

**Expected final references:** Article 11, Article 12, Article 13, Article 14, Article 15, Article 43

**Expected final key points:** technical documentation, logging, transparency, conformity

*Notes:* Obligation-generation chain across 5 turns. After Arts. 9 and 10, the remaining pre-market stack is Arts. 11-15 + Art. 43 conformity. Engine must hold the 'we are a recruitment AI provider' context and complete the list from where it left off.

### mt_v3_004

**Conversation:**

1. **user:** We operate an AI content-personalisation system for a news platform. It ranks articles to maximise time-on-site. What risk level?
2. **assistant:** A general news recommendation system that maximises engagement is minimal-risk — no Annex III category applies and no Art. 50 chatbot interaction with natural persons.
3. **user:** We've now discovered our A/B testing shows the system systematically amplifies politically polarising content in the weeks before elections, and we continue running it.

**Expected final references:** Article 5

**Expected final key points:** prohibited, manipulation, democratic

*Notes:* Minimal → prohibited flip on discovering the system manipulates democratic processes (Art. 5(1)(b)). Paper §4.2 explicit edge case. Engine must escalate all the way to prohibited, not stop at high-risk.

### mt_v3_005

**Conversation:**

1. **user:** We are a hospital that purchased a CE-marked AI triage system from MedAI Ltd. Who is the provider?
2. **assistant:** MedAI Ltd is the provider under Article 3 of the AI Act. You are the deployer under Article 26.
3. **user:** We customised the training data with 18 months of our own patient records to improve triage accuracy for our population.

**Expected final references:** Article 25, Article 16

**Expected final key points:** provider, substantial modification, obligations

*Notes:* Deployer → provider flip via substantial modification (Art. 25). Retraining on own data changes the system's intended purpose/performance characteristics. Paper scenarios require distinguishing provider vs deployer as a mandatory field.

### mt_v3_006

**Conversation:**

1. **user:** We are training a foundation model at 8×10²² FLOPs. Are we a GPAI provider under the AI Act?
2. **assistant:** At 8×10²² FLOPs you are below the 10²³ FLOPs threshold from the Commission's July 2025 Guidelines, so you are not yet classified as a GPAI provider under Article 51.
3. **user:** We scaled up to 2×10²³ FLOPs in our next training run.

**Expected final references:** Article 51, Article 53

**Expected final key points:** GPAI, general-purpose, obligations

*Notes:* GPAI threshold crossing (10²³ FLOPs from the Commission Guidelines). Engine must update the prior verdict and surface GPAI provider obligations (Art. 53 transparency + training-data summary).

### mt_v3_007

**Conversation:**

1. **user:** We are a bank using an AI from FinTech Corp to evaluate loan applications. The AI is already CE-marked. What must WE do as deployer before we start using it?
2. **assistant:** As deployer of a high-risk AI (Annex III(5)(b) credit scoring), you must verify the provider's CE marking and conformity documentation per Article 26.
3. **user:** What ongoing obligations apply after we start using it?
4. **assistant:** You must monitor the system's operation, ensure human oversight under Article 14, and report serious incidents to authorities under Article 73.
5. **user:** A customer whose loan was denied asks why. What does the AI Act require us to tell them?

**Expected final references:** Article 86

**Expected final key points:** explanation, individual, right

*Notes:* Art. 86 right to explanation for affected persons. Deployer obligation chain concludes with the individual-rights obligation. Engine must hold 'we are a deployer' context across 5 turns.

### mt_v3_008

**Conversation:**

1. **user:** We deploy a real-time biometric identification system in public spaces for law enforcement. Is this always prohibited?
2. **assistant:** Real-time RBI by law enforcement is prohibited under Article 5 with narrow exceptions: (i) searching for missing persons or victims, (ii) preventing imminent terrorist attacks, (iii) identifying suspects of serious crimes.
3. **user:** Our use case is preventing imminent terrorist attacks. Can we deploy without prior authorisation?

**Expected final references:** Article 5

**Expected final key points:** authorisation, prior, judicial

*Notes:* Art. 5(2) requires prior judicial or independent administrative authorisation even for the terrorist-attack carve-out. Engine must not grant blanket permission just because the carve-out category applies — the conditionalities matter.

### mt_v3_009

**Conversation:**

1. **user:** We are a provider of a high-risk AI for fraud detection in banking. Which conformity assessment route applies?
2. **assistant:** Banking fraud-detection AI is Annex III(5)(b). Most Annex III high-risk AI — except biometric systems under Annex III(1) — uses the internal control route under Annex VI, not a notified body.
3. **user:** We added biometric voice-authentication to verify caller identity before presenting the fraud score. Does that change the conformity route?

**Expected final references:** Article 43, Annex VII

**Expected final key points:** notified body, biometric, Annex VII

*Notes:* Adding biometric identification (Annex III(1)) requires a notified body (Annex VII), overriding the internal-control route. Engine must update its prior conformity-route verdict.

### mt_v3_010

**Conversation:**

1. **user:** Which articles apply to our AI that monitors employee social media for security clearance assessments?
2. **assistant:** Employment AI for security clearance = Annex III(4) high-risk. Core articles: Art. 9 (risk management), Art. 10 (data governance), Art. 13 (transparency to deployer), Art. 14 (human oversight).
3. **user:** The system now also infers political opinions from social media posts to flag 'loyalty risks'. Does that change anything?

**Expected final references:** Article 5

**Expected final key points:** prohibited, political, biometric categorisation

*Notes:* High-risk → prohibited escalation. Inferring political opinions from biometric/behavioural data = Art. 5(1)(g) prohibited categorisation. Engine must escalate from its prior high-risk verdict. Paper §4.2 explains how proximity to prohibited practices makes classification hard at decision boundaries.

### mt_v3_011

**Conversation:**

1. **user:** We run a customer service chatbot that is NOT high-risk. What transparency must we show users under the AI Act?
2. **assistant:** Article 50(1) requires you to disclose to users that they are interacting with an AI system, unless it is obvious from context.
3. **user:** We also use the conversation data to train the model. What data obligations apply to that?

**Expected final references:** Article 10

**Expected final key points:** training data, data governance, quality

*Notes:* Paper hypothesis 3: limited-risk is grounded in Art. 50 AND Art. 10. Turn 3 shifts from transparency (Art. 50) to data governance (Art. 10). Engine must surface Art. 10 even though the chatbot is not high-risk (Art. 10 applies to training data used for any AI system in the Act's scope).

### mt_v3_012

**Conversation:**

1. **user:** We have an AI that recommends movies on our streaming platform. What AI Act obligations apply?
2. **assistant:** A movie recommendation system is minimal-risk — no specific AI Act obligations apply. You should follow general AI best practices voluntarily.
3. **user:** Our platform also has a children's section. Does serving recommendations to minors change the risk classification?
4. **assistant:** Serving recommendations to minors does not by itself move the system into a higher risk tier. There is no specific AI Act provision elevating entertainment recommendations to high-risk solely because of the audience's age. Applicable minor-specific obligations come from GDPR (Art. 8) and the DSA, not the AI Act.
5. **user:** We profile children's viewing to infer their emotional state and present content calibrated to that inferred emotional state. Still minimal-risk?

**Expected final references:** Article 5

**Expected final key points:** prohibited, vulnerable, exploitation

*Notes:* Minimal → prohibited escalation via children's vulnerability. Inferring emotional state of minors and exploiting it = Art. 5(1)(b) exploitation of vulnerability. Paper §5: minimal recall is 0.29 — engine under-predicts minimal AND may also under-predict prohibited when the path starts minimal. Tests stable cross-tier escalation across 5 turns.

---

## 9. V2 — multi-turn (3-5 turn coreference / role-flip / framework probes)

### mt_v2_001

**Conversation:**

1. **user:** We are a hospital deploying an AI-based medical-imaging triage system from a CE-marked vendor.
2. **assistant:** Understood — that system is regulated as a medical device under the MDR and, since it is safety-related AI listed in Annex I, is also high-risk under Article 6(1) of the AI Act.
3. **user:** Which regulator do we register with under the AI Act side?

**Expected final references:** Article 49, Article 26, Article 70

**Expected final key points:** EU database, deployer, competent

*Notes:* Cross-framework coref: turn 1 fixes 'hospital' = deployer of high-risk medical-device AI. Turn 3 'we' must resolve to deployer, AI Act registration is Art. 49 (EU database), not MDR side.

### mt_v2_002

**Conversation:**

1. **user:** Our bank's anti-money-laundering AI uses customer transaction histories — partly third-country data.
2. **assistant:** Credit-institution AML AI falls under Annex III(5)(b) high-risk if it influences access to essential services.
3. **user:** Does our DPO's existing GDPR Art. 35 DPIA cover the AI Act obligations too, or do we still need the FRIA?

**Expected final references:** Article 27, Annex III

**Expected final key points:** FRIA, fundamental rights, in addition

*Notes:* Multi-framework: user attempts to substitute GDPR DPIA for AI Act FRIA. Engine must hold 'we are a deployer of Annex III high-risk' from turn 1 and route to Art. 27 FRIA — DPIA does not replace it.

### mt_v2_003

**Conversation:**

1. **user:** We provide an AI-driven SOC platform that detects cyber-attacks on critical infrastructure.
2. **assistant:** Critical-infrastructure AI safety components are high-risk under Annex III(2).
3. **user:** How does that interact with our NIS2 incident-reporting timeline?
4. **assistant:** NIS2 governs the cyber incident itself; AI Act adds AI-specific serious incident reporting.
5. **user:** What's the AI Act window then?

**Expected final references:** Article 73

**Expected final key points:** serious incident, 15 days, market surveillance

*Notes:* Turn 5 'window' resolves to Art. 73 AI-Act incident reporting after multi-framework establishing context. Tricky because NIS2 has its own timelines that could pollute the answer.

### mt_v2_004

**Conversation:**

1. **user:** We bought a CV-screening AI from Vendor X and use it for shortlisting our hires.
2. **assistant:** You are a deployer of an Annex III(4) high-risk AI; Vendor X is the provider.
3. **user:** We fine-tuned it on our 5-year hiring history dataset to match our culture.
4. **assistant:** Fine-tuning that changes intended purpose can flip the deployer into a provider under Article 25.
5. **user:** What new obligations does that flip impose on us?

**Expected final references:** Article 25, Article 16

**Expected final key points:** provider, obligations, substantial modification

*Notes:* Role flip across 5 turns. Final answer must enumerate provider obligations under Art. 16, triggered by Art. 25 substantial-modification path. Engine must remember the fine-tune fact from turn 3.

### mt_v2_005

**Conversation:**

1. **user:** We're an enterprise running our own GPT-style model internally for HR — never released externally.
2. **assistant:** Internal-only deployment still falls under the AI Act when used for an Annex III purpose like HR.
3. **user:** But we built it, so are we provider or deployer? We're both.

**Expected final references:** Article 3, Article 16, Article 26

**Expected final key points:** both, provider, deployer

*Notes:* Ambiguous role: user is provider AND deployer simultaneously. Engine must address both stacks of obligations without picking one and dropping the other.

### mt_v2_006

**Conversation:**

1. **user:** We import a high-risk biometric ID system from a US vendor.
2. **assistant:** You're an importer under Article 23.
3. **user:** Now we're rebranding it under our own name before selling it on.

**Expected final references:** Article 25, Article 16

**Expected final key points:** provider, name, trademark

*Notes:* Importer → provider flip under Art. 25(1)(a) (putting one's name/trademark on a high-risk system). Engine must catch the role transition implicit in 'rebranding'.

### mt_v2_007

**Conversation:**

1. **user:** We're pre-training a foundation model at around 5×10²³ FLOPs.
2. **assistant:** Above the 10²³ FLOPs threshold from the July 2025 Commission Guidelines, you're a GPAI provider under Article 51.
3. **user:** What if we keep training and hit 1×10²⁵?

**Expected final references:** Article 51, Article 55

**Expected final key points:** systemic risk, 10²⁵, notify

*Notes:* Digital Omnibus threshold ladder: 10²³ → standard GPAI (Art. 51), 10²⁵ → systemic-risk GPAI (Art. 55). Engine must hold the 'pre-training a GPAI' context from turn 1.

### mt_v2_008

**Conversation:**

1. **user:** We took an open-weights model trained on 9×10²⁴ FLOPs and fine-tuned it on legal-domain data.
2. **assistant:** Fine-tuning of a GPAI can flip you into a provider role if the additional compute exceeds one-third of base compute (Article 25 + Commission Guidelines).
3. **user:** Our fine-tune used 3.3×10²⁴ FLOPs — exactly the 1/3 threshold. Are we now a provider?

**Expected final references:** Article 25, Article 51

**Expected final key points:** one-third, modifier, provider

*Notes:* Boundary case at the Digital Omnibus 1/3 fine-tune rule. Engine must explain the rule deterministically — at exactly 1/3, the modifier becomes provider.

### mt_v2_009

**Conversation:**

1. **user:** Our GPAI is open-weights, released on HuggingFace under Apache 2.0.
2. **assistant:** Article 53(2) carves out most documentation obligations for non-systemic open-weights GPAI.
3. **user:** We also train it on 2×10²⁵ FLOPs.

**Expected final references:** Article 55, Article 53

**Expected final key points:** systemic, carve-out, does not apply

*Notes:* Open-weights carve-out is GONE when the systemic-risk threshold (10²⁵) is hit. Engine must update its prior answer with the contradicting fact from turn 3.

### mt_v2_010

**Conversation:**

1. **user:** What are the transparency obligations for high-risk AI?
2. **assistant:** Article 13 requires providers to design transparency mechanisms for deployers.
3. **user:** And for chatbots that talk to consumers?
4. **assistant:** Article 50(1) requires AI-chatbot interactions with natural persons to be disclosed.
5. **user:** Which one wins if my chatbot is also a high-risk medical-triage tool?

**Expected final references:** Article 13, Article 50

**Expected final key points:** both, cumulative, apply

*Notes:* Cross-article conflict resolution. Both Art. 13 (high-risk provider transparency) and Art. 50 (chatbot user disclosure) apply cumulatively — engine must not pick one and drop the other.

### mt_v2_011

**Conversation:**

1. **user:** We're a SaaS startup with 40 employees and €8M annual turnover.
2. **assistant:** You qualify as an SME under Article 62.
3. **user:** We just raised Series B and grew to 250 employees, €60M turnover.
4. **assistant:** You're now a small mid-cap — the Digital Omnibus extended SME privileges to small mid-caps under Article 62.
5. **user:** Does our priority sandbox access carry over?

**Expected final references:** Article 62, Article 57

**Expected final key points:** small mid-cap, sandbox, priority

*Notes:* Digital Omnibus small_mid_cap modifier role + sandbox priority. Engine must hold the size transition fact from turn 3 and apply the post-Omnibus rule.

### mt_v2_012

**Conversation:**

1. **user:** Is our emotion-recognition tool prohibited?
2. **assistant:** Emotion recognition is not categorically prohibited; Article 5(1)(f) only bans it in workplace and education contexts (with a medical/safety carve-out).
3. **user:** We sell it to call centres for monitoring agent stress levels.

**Expected final references:** Article 5

**Expected final key points:** workplace, prohibited, call centre

*Notes:* Refinement reveals workplace deployment, flipping the verdict from 'not categorically prohibited' to 'prohibited under Art. 5(1)(f)'. Engine must update.

### mt_v2_013

**Conversation:**

1. **user:** We're building a biometric categorization tool for retail analytics — categorizing shoppers by age range.
2. **assistant:** Age-based biometric categorization is allowed; Article 5(1)(g) only prohibits inferring race, political opinions, trade-union membership, religion, sex life, or sexual orientation.
3. **user:** What if we add ethnicity inference for marketing personalisation?

**Expected final references:** Article 5

**Expected final key points:** prohibited, race, ethnicity

*Notes:* Borderline prohibition. Turn 1 is OK (age), turn 3 crosses into Art. 5(1)(g) prohibited territory. Engine must flip the verdict.

### mt_v2_014

**Conversation:**

1. **user:** Real-time RBI in public spaces — we're a police force investigating a missing-child case.
2. **assistant:** Article 5(1)(h)(i) carves out a missing-children exception to the real-time RBI prohibition, subject to safeguards.
3. **user:** Do we still need judicial pre-authorization?

**Expected final references:** Article 5

**Expected final key points:** judicial, authorization, prior

*Notes:* Carve-out with conditions. The missing-children exception requires prior judicial/independent administrative authorization per Art. 5(2)–(3).

### mt_v2_015

**Conversation:**

1. **user:** Our HR analytics scores employee performance using AI.
2. **assistant:** Annex III(4)(b) makes performance-evaluation AI in employment high-risk.
3. **user:** Now we use it to decide who to lay off in a restructuring.

**Expected final references:** Annex III, Article 5

**Expected final key points:** termination, high-risk, fundamental

*Notes:* Stays high-risk (Annex III(4)(b) covers termination decisions). Engine should NOT slip into 'prohibited' since this is not social scoring — but must keep high-risk classification firm.

### mt_v2_016

**Conversation:**

1. **user:** We're testing a high-risk hiring AI in the Spanish regulatory sandbox.
2. **assistant:** Article 57 permits high-risk AI testing in an approved sandbox under supervision.
3. **user:** We want to deploy it to a real client during the sandbox phase.

**Expected final references:** Article 60, Article 57

**Expected final key points:** real-world, testing, conditions

*Notes:* Sandbox vs real-world testing distinction. Art. 60 governs real-world testing outside sandboxes; combining the two needs care. Engine must surface Art. 60 conditions.

### mt_v2_017

**Conversation:**

1. **user:** We knowingly deployed an AI Act prohibited practice for 6 months in our HR product.
2. **assistant:** That's an Article 5 violation; Article 99(3) caps fines at €35M or 7% of worldwide turnover.
3. **user:** We're a 25-employee startup — does the €35M cap actually hit us?

**Expected final references:** Article 99

**Expected final key points:** proportionate, SME, lower

*Notes:* Art. 99(6) requires fines to be proportionate, with SME/start-up carve-out for proportionality. Engine must not just quote the €35M ceiling.

### mt_v2_018

**Conversation:**

1. **user:** Our high-risk AI uses Annex IV technical documentation.
2. **assistant:** Article 11 + Annex IV mandate the technical documentation contents for high-risk AI.
3. **user:** Internal conformity assessment or third-party notified body?
4. **assistant:** Article 43 routes most high-risk AI to internal control (Annex VI); biometric systems under Annex III(1) need a notified body (Annex VII).
5. **user:** We're under Annex III(4) (employment). Which route?

**Expected final references:** Article 43, Annex VI

**Expected final key points:** internal, control, Annex VI

*Notes:* Conformity-assessment routing question across 5 turns. Annex III(4) employment AI uses internal control (Annex VI), not notified-body (Annex VII).

### mt_v2_019

**Conversation:**

1. **user:** When do high-risk Annex III obligations apply?
2. **assistant:** Per the May 2026 Digital Omnibus political agreement, Annex III high-risk obligations apply from 2 December 2027.
3. **user:** And for Annex I (medical devices etc.) embedded systems?

**Expected final references:** Article 113

**Expected final key points:** 2 August 2028, Annex I

*Notes:* Digital Omnibus deferred timeline. Annex I embedded path moves to 2 Aug 2028 (Art. 113 as amended).

### mt_v2_020

**Conversation:**

1. **user:** Our prohibited-practice deadline was 2 Feb 2025, correct?
2. **assistant:** Yes — Article 5 prohibitions have applied since 2 February 2025.
3. **user:** Did the Digital Omnibus push that back?

**Expected final references:** Article 5, Article 113

**Expected final key points:** no, applies, still

*Notes:* Digital Omnibus did NOT defer Art. 5 prohibitions. Engine must reject the false-deferral premise.

### mt_v2_021

**Conversation:**

1. **user:** We're a GPAI provider considering signing the Code of Practice.
2. **assistant:** Article 56 establishes Codes of Practice for GPAI providers; adherence is voluntary but creates a presumption of conformity.
3. **user:** If we don't sign, what's the alternative path to demonstrate compliance?

**Expected final references:** Article 56, Article 55

**Expected final key points:** adequate means, alternative, demonstrate

*Notes:* Art. 55(2) lets non-signatories demonstrate compliance by 'other adequate means.' Engine must surface that alternative path rather than imply signing is mandatory.

### mt_v2_022

**Conversation:**

1. **user:** The AI Office contacted us about our GPAI.
2. **assistant:** The AI Office sits within the Commission and oversees GPAI providers under Article 88+.
3. **user:** Can they fine us directly?

**Expected final references:** Article 101

**Expected final key points:** Commission, fines, GPAI

*Notes:* Art. 101 — fines for GPAI providers are imposed by the Commission, not Member State authorities. Distinct from Art. 99 fines route.

### mt_v2_023

**Conversation:**

1. **user:** Our high-risk AI was placed on the market in March 2026 — before the Annex III deadline.
2. **assistant:** Article 111 covers transitional provisions for systems already on the market.
3. **user:** Do we have to retrofit conformity, or are we grandfathered?

**Expected final references:** Article 111

**Expected final key points:** substantial change, transitional, grandfather

*Notes:* Art. 111 grandfathering applies UNLESS the system undergoes substantial change after the applicability date. Engine must surface the carve-out condition.

### mt_v2_024

**Conversation:**

1. **user:** We deploy a high-risk AI that makes loan denials.
2. **assistant:** Loan denial is Annex III(5)(b) — high-risk.
3. **user:** A customer wants to know why their loan was rejected by our AI.

**Expected final references:** Article 86

**Expected final key points:** explanation, individual, right

*Notes:* Art. 86 right to explanation of individual decisions — newer obligation, often missed. Engine must surface this and not regress to Art. 13 (which is about provider→deployer transparency, not deployer→affected-person).

### mt_v2_025

**Conversation:**

1. **user:** We are an EU subsidiary of a US AI company; our parent is the provider, we just distribute.
2. **assistant:** As distributor in the Union, Article 24 obligations apply to you.
3. **user:** If the US parent has no EU establishment, who plays the authorized-representative role?

**Expected final references:** Article 22, Article 24

**Expected final key points:** authorised representative, written mandate, established

*Notes:* Art. 22 — non-EU providers MUST appoint an authorised representative established in the Union. Engine must surface Art. 22, not just Art. 24 distributor obligations.

