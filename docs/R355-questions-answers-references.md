# Lexy optimisation round 1 - 81 rows Q&A (EU AI Act before August 2nd - snapshot)

## 1. la_q1

**Q:** Does the technical documentation of a high-risk AI system require to provide specifications regarding the required hardware?

**A:** Yes. Under Article 11, a provider must draw up technical documentation containing the information set out in Annex IV, which expressly requires a description of the hardware on which the AI system is intended to run (Annex IV point 1(e)) and, as part of the system's development description, the computational resources used to develop, train, test and validate it (Annex IV point 2(c)).

- **gold refs**: Annex IV, Article 11
- **branch refs**: Article 11, Annex IV

## 2. la_q2

**Q:** Does the obligation to indicate that deep-fakes are artificially generated apply when prosecuting a criminal offence?

**A:** No. Under Article 50(4), the deployer's duty to disclose that image, audio, or video content constituting a deep fake has been artificially generated or manipulated does not apply where the use is authorised by law to detect, prevent, investigate, or prosecute criminal offences. Absent that law-enforcement authorisation, the deployer must disclose that the content is a deep fake.

- **gold refs**: Article 50
- **branch refs**: Article 50.4, Article 50

## 3. la_q3

**Q:** When the intended use of an AI system is listed in Annex III of the EU AI Act, the AI system is automatically high-risk, isn't it? If not, can you explain when that is not the case?

**A:** Not automatically. Article 6(2) provides that AI systems referred to in Annex III shall be considered high-risk, but Article 6(3) derogates from that rule where the system does not pose a significant risk of harm to health, safety or fundamental rights, including by not materially influencing the outcome of decision making, AND the system is intended to perform one of four tasks: a narrow procedural task, improving the result of a previously completed human activity, detecting decision-making patterns or deviations from prior patterns without replacing or influencing the previously completed human assessment, or a preparatory task to an assessment relevant for the Annex III use cases. However, a system that performs profiling of natural persons is always high-risk regardless of those conditions. A provider relying on this derogation must document its assessment before placing the system on the market and register under Article 6(4).

- **gold refs**: Annex III, Article 49, Article 6
- **branch refs**: Annex III, Article 6

## 4. la_q4

**Q:** I have a medical device that has an AI system as a safety component. The medical device is classified "medium-risk" and undergoes a 3rd party conformity assessment. Is the AI system "medium risk" too? If yes, why? If not, why not?

**A:** The AI system is high-risk, not "medium-risk." The EU AI Act does not use a "medium-risk" category. Under Article 6(1), an AI system is classified as high-risk where it is intended to be used as a safety component of a product covered by the Union harmonisation legislation listed in Annex I and that product is required to undergo a third-party conformity assessment. Medical devices are listed in Annex I, so an AI safety component of a medical device that undergoes third-party conformity assessment is high-risk regardless of the device's own risk class under sectoral legislation. As to conformity assessment, Article 43(3) provides that for high-risk AI systems covered by Section A of Annex I, the provider follows the relevant conformity assessment procedure required under that sectoral legislation, and the Chapter III Section 2 requirements of the AI Act form part of that same assessment, yielding a single integrated procedure conducted by the sectoral notified body.

- **gold refs**: Annex I, Article 43, Article 6
- **branch refs**: Article 6.1, Article 43.3, Annex I

## 5. la_q5

**Q:** Does the EU AI Act explicitly requires to use explainable AI techniques such as LIME or SHAP to increase the trustworthiness of high-risk AI systems?

**A:** No, the EU AI Act mandates no specific explainable-AI technique such as LIME or SHAP, and Article 13 instead requires only that high-risk AI systems be sufficiently transparent for deployers to interpret their output. Article 14 requires effective human oversight, and Article 15 requires appropriate accuracy, robustness and cybersecurity. The Act is technique-agnostic, so the choice of any interpretability method is left to the provider.

- **gold refs**: Article 13
- **branch refs**: Article 13, Article 14, Article 15

## 6. la_q6

**Q:** Does the EU AI Act apply to AI systems or AI models or both?

**A:** The EU AI Act's core regime governs AI systems, defined in Article 3(1) and brought within scope by Article 2, through the risk-based tiers (prohibited practices under Article 5, high-risk systems under Article 6, and limited-risk transparency duties under Article 50). General-purpose AI models are regulated separately under Chapter V (Articles 51 to 56), are defined in Article 3(63), and carry their own provider obligations with additional duties for models posing systemic risk. The Regulation therefore applies to both AI systems and general-purpose AI models under two parallel regimes.

- **gold refs**: Article 2, Article 3, Article 51
- **branch refs**: Article 2, Article 3.1, Article 51

## 7. la_q7

**Q:** We want to deploy an AI system that performs biometric verification solely to confirm that a specific natural person is the person he or she claims to be. Is this system prohibited? Is it high-risk?

**A:** The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.

- **gold refs**: Annex I, Annex III, Article 5, Article 50, Article 6
- **branch refs**: Article 5, Article 6, Article 50, Annex III, Annex I

## 8. la_q8

**Q:** Are AI safety components within medical devices of MDR class IIa, IIb, or III considered to be high-risk according to the EU AI Act? Why?

**A:** AI safety components within medical devices of MDR class IIa, IIb or III are high-risk. Article 6(1) classifies an AI system as high-risk where two cumulative conditions are met: the AI system is intended to be used as a safety component of a product, or is itself a product, covered by the Union harmonisation legislation listed in Annex I, and that product is required to undergo a third-party conformity assessment under that legislation. Annex I lists Regulation (EU) 2017/745 on medical devices, and under that Regulation medical devices of classes IIa, IIb and III must undergo third-party conformity assessment involving a notified body, so both conditions are fulfilled. For such systems, Article 43(3) requires the provider to follow the conformity assessment procedure of the sectoral legislation itself, with the Chapter III Section 2 requirements forming part of that assessment.

- **gold refs**: Annex I, Annex III, Article 43, Article 6
- **branch refs**: Article 6.1, Annex I

## 9. la_q9

**Q:** What documentation does a provider of a high-risk AI system needs to keep available for the national competent authorities, and for how long?

**A:** Under Article 18, for ten years after the high-risk AI system is placed on the market or put into service, the provider must keep at the disposal of the national competent authorities the technical documentation (Article 11), the quality-management-system documentation (Article 17), the documentation of any changes approved by notified bodies, the decisions and other documents issued by notified bodies, and the EU declaration of conformity (Article 47). Separately, under Article 19 the automatically generated logs must be kept for a period appropriate to the intended purpose, of at least six months.

- **gold refs**: Annex IV, Article 11, Article 17, Article 18, Article 47
- **branch refs**: Article 18, Article 11, Article 17, Article 47, Article 19

## 10. la_q10

**Q:** Which article of the EU AI Act governs human oversight measures?

**A:** Defines 68 terms used in the Regulation, including 'AI system' (machine-based, varying autonomy, possibly adaptive, inferring from input how to generate output influencing physical/virtual environments), 'provider', 'deployer', 'placing on the market', 'putting into service', 'substantial modification', 'general-purpose AI model', 'general-purpose AI system', 'systemic risk'. Scope: applies to providers placing AI systems on the EU market regardless of establishment, deployers established in the EU, providers/deployers in third countries whose output is used in the EU. Excludes military/defence/national-security uses, scientific R&D, purely personal non-professional use, and free/open-source AI systems outside the high-risk + prohibited + transparency scope.

- **gold refs**: Article 14
- **branch refs**: Article 14, Article 2, Article 1

## 11. la_q11

**Q:** What is the meaning and purpose of 'testing data' in the context of AI systems, and why is it important that it is not leaked during the training process?

**A:** Testing data is defined in Article 3(32) as data used to provide an independent evaluation of the AI system, in order to confirm its expected performance before it is placed on the market or put into service. It must be kept separate from the training and validation data so that this evaluation is genuinely independent. If testing data leaks into the training process, the system is in effect assessed on data it has already seen, which inflates its apparent performance and defeats the purpose of the independent check that Article 10 requires for the datasets of a high-risk AI system.

- **gold refs**: Article 10
- **branch refs**: Article 3.32, Article 10

## 12. la_q12

**Q:** What are the high-risk uses of AI systems listed under 'Administration of justice and democratic processes' cited in the EU AI Act?

**A:** Annex III point 8 lists two high-risk use cases under administration of justice and democratic processes. Annex III point 8(a) covers AI systems intended to be used by a judicial authority, or on its behalf, to assist in researching and interpreting facts and the law and in applying the law to a concrete set of facts, or to be used similarly in alternative dispute resolution. Annex III point 8(b) covers AI systems intended to influence the outcome of an election or referendum, or the voting behaviour of natural persons in exercising their vote, with a carve-out for tools that only organise, optimise or structure political campaigns from an administrative or logistical point of view.

- **gold refs**: Annex III, Article 6
- **branch refs**: Annex III.8

## 13. la_q13

**Q:** Under what conditions should providers of general-purpose AI models be subject to exceptions regarding transparency-related requirements, if any? And what do those exceptions not cover?

**A:** This exception shall not apply to general-purpose AI models with systemic risks.

- **gold refs**: Annex XI, Annex XII, Article 51, Article 53, Article 55
- **branch refs**: Article 53, Article 50.1, Article 16, Article 55, Article 51, Article 56, Article 25

## 14. la_q14

**Q:** Which AI systems used in education or vocational training should be classified as high-risk according to the EU AI Act?

**A:** Under Annex III(3), AI systems in education and vocational training are classified as high-risk where they are intended to be used to determine access or admission or to assign natural persons to educational and vocational training institutions at all levels, to evaluate learning outcomes including when those outcomes steer the learning process, to assess the appropriate level of education an individual will receive or be able to access, or to monitor and detect prohibited behaviour of students during tests. Article 6(2) is the provision that classifies systems falling within Annex III as high-risk. Under Article 6(3), an Annex III education system is nevertheless not high-risk where it does not pose a significant risk of harm to health, safety or fundamental rights and performs only a narrow procedural task, improves the result of a previously completed human activity, detects decision-making patterns without replacing or influencing the human assessment, or performs a preparatory task, but a system that performs profiling of natural persons is always high-risk regardless of those conditions.

- **gold refs**: Annex III, Article 49, Article 6
- **branch refs**: Annex III.3, Article 6.2, Article 6.3

## 15. la_q15

**Q:** What obligations, if any, does the EU AI Act set in place for AI systems that interact directly with natural persons? What exceptions, if any, apply?

**A:** The principal obligation for AI systems that interact directly with natural persons is set out in Article 50(1): the provider must design the system so that the natural person concerned is informed they are interacting with an AI system, unless this is obvious from the point of view of a reasonably well-informed, observant and circumspect person taking into account the circumstances and context of use. Article 50(2) adds that providers of AI systems generating synthetic audio, image, video or text content must ensure the outputs are marked in a machine-readable format as artificially generated or manipulated. On the deployer side, Article 50(3) requires deployers of emotion recognition or biometric categorisation systems to inform exposed natural persons of the system's operation, and Article 50(4) requires deployers of systems that generate deepfakes to disclose that the content is artificially generated or manipulated, and deployers of systems that generate or manipulate text published to inform the public on matters of public interest to disclose its artificial origin. Three categories of exception apply. First, the Article 50(1) provider disclosure duty does not apply to AI systems authorised by law to detect, prevent, investigate or prosecute criminal offences, subject to appropriate safeguards for the rights and freedoms of third parties, but this exception is itself reversed where the system is available to the public to report a criminal offence. Second, the Article 50(3) deployer duty does not apply to emotion recognition or biometric categorisation systems permitted by law to detect, prevent or investigate criminal offences, subject to appropriate safeguards and in accordance with Union law. Third, the Article 50(4) deepfake disclosure duty does not apply where the use is authorised by law for criminal-offence detection, prevention, investigation or prosecution, and where the content forms part of an evidently artistic, creative, satirical, fictional or analogous work the obligation is limited to a disclosure that does not hamper display or enjoyment of the work. The separate Article 50(4) duty on AI-generated text published on matters of public interest does not apply where the use is authorised by law for criminal-offence purposes, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for its publication.

- **gold refs**: Article 50
- **branch refs**: Article 50.1, Article 50.3

## 16. la_q16

**Q:** What are the administrative fines for non-compliance with the prohibition of the AI practices?

**A:** Non-compliance with the prohibited AI practices listed in Article 5 is subject to administrative fines of up to EUR 35 000 000 or, if the offender is an undertaking, up to 7 % of its total worldwide annual turnover for the preceding financial year, whichever is higher (Article 99(3)). Penalties must be effective, proportionate and dissuasive. For SMEs, including start-ups, the applicable ceiling is the lower of the percentage or the fixed amount (Article 99(6)).

- **gold refs**: Article 5, Article 50, Article 99
- **branch refs**: Article 99.3, Article 99.6, Article 5

## 17. la_q17

**Q:** How does Annex II relate to prohibited uses of AI systems?

**A:** List of criminal offences referred to in Article 5(1)(h) permitting real-time remote biometric identification by law enforcement: terrorism, trafficking in human beings, sexual exploitation of children, illicit trafficking in narcotic drugs / weapons / nuclear material, murder, kidnapping, rape, armed robbery, organised crime, participation in a criminal organisation, environmental crime, provided the offence is punishable in the relevant Member State by a custodial sentence of at least 4 years.

- **gold refs**: Annex II, Article 5
- **branch refs**: Annex II

## 18. la_q18

**Q:** Can the European Commission amend Annex III of the EU AI Act to add or modify use-cases classified as high-risk AI systems? Under what conditions?

**A:** Yes, the Commission is empowered to amend Annex III by adding new high-risk use cases or modifying existing ones through delegated acts, subject to specific substantive conditions. Article 6(6) grants the Commission the power to adopt delegated acts in accordance with Article 97 to amend the conditions under which an Annex III system may escape high-risk classification, but the power to amend Annex III itself, adding or removing use cases, is conferred separately by Article 7 (which is not among the citable provisions here but is the operative mechanism). Within the citable provisions, Article 6(6) empowers the Commission to adopt delegated acts to amend the derogation conditions in Article 6(3) by adding new conditions or modifying them, where there is concrete and reliable evidence that AI systems falling under Annex III do not pose a significant risk of harm to health, safety or fundamental rights. The Commission must consult the European Artificial Intelligence Board before exercising this power.

- **gold refs**: Annex I, Annex III, Article 6, Article 7
- **branch refs**: Annex III, Article 6.6, Article 6.3, Article 97, Article 7

## 19. la_q19

**Q:** What is a deep fake according to the EU AI Act?

**A:** AI-generated or manipulated image, audio or video content that resembles existing persons, objects, places, entities or events and would falsely appear to a person to be authentic or truthful.

- **gold refs**: Article 50
- **branch refs**: Article 3.60, Article 50

## 20. la_q20

**Q:** Should market surveilance authorities be provided with remote access to documentations and data sets used to develop a high-risk AI system?

**A:** Yes. Article 74(12) requires that market surveillance authorities be granted full access by providers to the documentation as well as the training, validation and testing data sets used for the development of high-risk AI systems, including, where appropriate and subject to security safeguards, through application programming interfaces or other relevant technical means and tools enabling remote access. This power is limited to what is necessary to fulfil their tasks. Article 78 imposes a confidentiality obligation on market surveillance authorities regarding the information and data so obtained, requiring them to protect intellectual property rights, confidential business information and trade secrets, and to delete data once it is no longer needed.

- **gold refs**: Article 16, Article 26
- **branch refs**: Article 74.12, Article 78

## 21. la_q21

**Q:** If a provider of a high-risk AI system confirms that the system achieves an appropriate level of accuracy, robustness, and cybersecurity at the time of development, then no further action is required by the provider on these aspects in the future. Correct?

**A:** Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties; both apply to the same system, not in the alternative. Requires appropriate levels of accuracy, robustness, and cybersecurity across the lifecycle, accuracy metrics declared in instructions for use, resilience against errors, and resistance to data-poisoning, evasion, model-confidentiality, and adversarial attacks. Requires high-risk AI systems to be designed for sufficient operational transparency to deployers, accompanied by instructions for use covering provider identity, intended purpose, capabilities + limitations, expected lifetime, human-oversight measures, and required maintenance.

- **gold refs**: Article 15
- **branch refs**: Article 6, Article 15, Article 13, Article 16, Article 17, Article 43, Article 50

## 22. la_q22

**Q:** What are all the risk categories in the EU AI Act?

**A:** The EU AI Act sets four risk tiers plus a separate regime for general-purpose AI models: unacceptable-risk practices are prohibited under Article 5; and high-risk systems are classified under Article 6 (an Annex I product safety component, or an Annex III use case) and carry the Chapter III Section 2 obligations. Limited-risk systems carry the Article 50 transparency duties, minimal-risk systems have no mandatory duties under the Act, and general-purpose AI models are governed separately under Articles 51 to 56, with added obligations under Article 55 for models classified as having systemic risk under Article 51.

- **gold refs**: Article 5
- **branch refs**: Article 5, Article 6, Article 50, Article 51, Article 52, Annex I, Annex III, Article 53, Article 54, Article 55, Article 56

## 23. la_q23

**Q:** Does "systemic risk" apply to AI systems or general purpose AI models or both?

**A:** Under Article 53, GPAI providers must maintain Annex XI documentation, supply downstream-provider information, and publish a training-data summary; the Article 53(2) carve-out means each documentation obligation does not apply to free and open-source models below the systemic threshold. Under Article 51, a GPAI model has systemic risk when cumulative training compute exceeds 10²⁵ FLOPs (10^25); providers must notify the Commission within two weeks of meeting the threshold. Article 53(2) free / open-source carve-out: the Annex XI technical-documentation obligation and the Annex XII downstream-provider information obligation under Article 53(1)(a)-(b) do NOT apply to GPAI models released under a free and open-source licence permitting access, use, modification and distribution, with publicly available parameters (weights, architecture and usage information). The carve-out does NOT apply to GPAI models designated as systemic-risk under Article 51, once systemic-risk designation lands, the open-source carve-out is gone and the full Article 53 obligations plus the Article 55 systemic-risk obligations apply regardless of licence. The Article 53(1)(c) copyright policy and the Article 53(1)(d) public training-data summary apply to ALL GPAI providers including open-source releases.

- **gold refs**: Annex XIII, Article 51, Article 55
- **branch refs**: Article 55, Article 53, Article 51

## 24. la_q24

**Q:** Are AI systems that fall under one of the areas of Annex III, but not falling within a use-case within such areas, considered high-risk?

**A:** Not necessarily. Article 6(2) classifies as high-risk only AI systems "referred to in Annex III," meaning those that match a specific use case listed within one of the eight areas. An AI system that operates in a domain covered by one of the eight Annex III areas but does not fall within any of the particular use cases described therein is not classified as high-risk under Article 6(2). Additionally, even a system that does fall within an Annex III use case may escape high-risk classification under Article 6(3) where it does not pose a significant risk of harm to health, safety or fundamental rights and performs one of four tasks: a narrow procedural task, improving the result of a previously completed human activity, detecting decision-making patterns or deviations without replacing or influencing the human assessment, or a preparatory task, unless the system performs profiling of natural persons, in which case it is always high-risk.

- **gold refs**: Annex III, Article 6
- **branch refs**: Annex III, Article 6.2, Article 6.3

## 25. la_q25

**Q:** Can an operator that is not a provider according to the EU AI Act, for example a deployer, take actions on a given high-risk AI system such that it can be effectively seen as a provider by the authorities? If yes, what kind of action would result in such an outcome?

**A:** Yes. Under Article 25(1), a distributor, importer, deployer or other third party is deemed to be the provider of a high-risk AI system, and takes on the provider obligations in Article 16, in any of three cases. First, if it puts its name or trademark on a high-risk AI system already placed on the market (Article 25(1)(a)). Second, if it makes a substantial modification to a high-risk AI system that remains high-risk (Article 25(1)(b)). Third, if it modifies the intended purpose of an AI system, including a general-purpose AI system, so that it becomes high-risk (Article 25(1)(c)). In each of these three cases the operator assumes the provider obligations in Article 16, and the initial provider is no longer considered the provider of that specific system under Article 25(2).

- **gold refs**: Annex III, Article 25, Article 26, Article 6
- **branch refs**: Article 25.1, Article 25, Article 16

## 26. la_q26

**Q:** If I have an AI system that is high-risk because listed in the use cases of Annex III, and change it to a different use case that is not in Annex I or III, does it stay high-risk due to its historical provenance?

**A:** No, the system does not remain high-risk by historical provenance. Under Article 6(2), an AI system is high-risk because it falls within one of the use cases listed in Annex III; if the system's intended purpose is changed to a use case that does not appear in Annex III and the system is also not a safety component of, or itself, a product requiring third-party conformity assessment under Annex I legislation per Article 6(1), neither classification route is satisfied and the system is not high-risk. The classification is determined by the system's current intended purpose at the time it is placed on the market or put into service, not by a prior classification under a former intended purpose.

- **gold refs**: Annex I, Annex III, Article 6
- **branch refs**: Annex III, Annex I, Article 6.2

## 27. la_q27

**Q:** How are AI systems intended to influence the outcome of an election or referendum classified, and what exception is given for certain campaign-related tools?

**A:** Under Annex III point 8(b), AI systems intended to influence the outcome of an election or referendum, or the voting behaviour of natural persons in exercising their vote, are high-risk under Article 6(2). Annex III point 8(b) itself excludes systems to whose output natural persons are not directly exposed, such as tools used only to organise, optimise or structure political campaigns from an administrative or logistical point of view, which therefore fall outside this high-risk category.

- **gold refs**: Annex III
- **branch refs**: Article 6, Annex III.8

## 28. la_q28

**Q:** According to Article 1, what is the objective of the EU AI Act?

**A:** Lays down harmonised rules for placing on the market, putting into service, and use of AI systems in the Union; sets prohibitions, high-risk requirements, transparency obligations, GPAI rules, and innovation-support measures to ensure a high level of protection of health, safety, and fundamental rights.

- **gold refs**: Article 1
- **branch refs**: Article 1

## 29. la_q29

**Q:** Under the EU AI Act, which specific AI systems are explicitly listed as high-risk because they make decisions in critical life- and health-related situations involving emergency calls and triage?

**A:** Under Article 27, in addition to Article 26 baseline duties, deployers of certain Annex III high-risk AI systems must perform a Fundamental Rights Impact Assessment (FRIA) covering affected persons and specific fundamental rights risks. Derogation from the conformity-assessment procedure: by way of derogation from Article 43, a market-surveillance authority may authorise the placing on the market or putting into service of specific high-risk AI systems within the territory of the Member State concerned, for exceptional reasons of public security or the protection of life and health of persons, environmental protection, or the protection of key industrial and infrastructural assets (Article 46(1)). Article 9 requires a documented, iterative risk-management system across the AI system's lifecycle.

- **gold refs**: Article 6, Annex III
- **branch refs**: Article 9, Article 27, Article 46

## 30. la_q30

**Q:** Under Regulation (EU) 2024/1689, as part of their supervisory role for an AI regulatory sandbox, compliance with which specific Article must the market surveillance authority verify?

**A:** As part of their supervisory role for an AI regulatory sandbox, the market surveillance authority must verify compliance with Article 78, which requires market surveillance authorities to respect the confidentiality of information and data obtained in carrying out their tasks, protecting in particular intellectual property rights, confidential business information and trade secrets including source code, the effective implementation of the Regulation, public and national security interests, and the integrity of criminal or administrative proceedings. Article 74(14) confirms that any information or documentation obtained by market surveillance authorities shall be treated in accordance with the confidentiality obligations set out in Article 78. Article 57 establishes the sandbox framework within which the market surveillance authority operates, providing that exit reports and written proof from the national competent authority shall be taken positively into account by market surveillance authorities with a view to accelerating conformity assessment procedures.

- **gold refs**: Article 57, Article 74
- **branch refs**: Article 78, Article 57, Article 74.14

## 31. la_q31

**Q:** Is an AI system used to structure or deduplicate information for a use case listed in Annex III considered high-risk?

**A:** The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.

- **gold refs**: Annex III, Article 50, Article 6
- **branch refs**: Article 6, Article 50, Annex III, Annex I

## 32. la_q32

**Q:** Is an AI system used to detect decision-making patterns or deviations for a use case listed in Annex III considered high-risk?

**A:** Not automatically. Even within an Annex III use case, Article 6(3)(c) provides that an AI system intended to detect decision-making patterns or deviations from prior decision-making patterns is not high-risk where it does not pose a significant risk of harm and is not meant to replace or influence a previously completed human assessment without proper human review. However, under Article 6(3) such a system is always high-risk where it performs profiling of natural persons.

- **gold refs**: Annex III, Article 6
- **branch refs**: Article 6.3, Article 6, Annex III

## 33. la_q33

**Q:** Regarding the European Artificial Intelligence Board: (1) Who designates its members? (2) How long is the term? How many times is the term renewable? (3) must members represent stakeholder interests or act impartially/objectively? (4) what voting threshold is required to adopt the Board's rules of procedure (is a simple 50%+1 majority enough)?

**A:** The European Artificial Intelligence Board (Article 65) has one representative per Member State, each serving a three-year term renewable once under Article 65(3). Under Article 65(4) each is their Member State's single contact point rather than an independent stakeholder appointee, while Article 65(7) requires the Board to safeguard the objectivity and impartiality of its activities. Its rules of procedure are adopted by a two-thirds majority under Article 65(5), so a simple majority is not sufficient.

- **gold refs**: Article 65, Article 67, Article 68
- **branch refs**: Article 65

## 34. la_q34

**Q:** Under the EU AI Act, what jurisdiction does the Court of Justice of the European Union have over Commission decisions fixing fines on providers of general-purpose AI models, and what can the Court do with the fine?

**A:** Under Article 101(5), the Court of Justice of the European Union has unlimited jurisdiction to review Commission decisions fixing a fine on providers of general-purpose AI models. The Court may cancel, reduce or increase the fine imposed.

- **gold refs**: Article 101, Article 64, Article 99
- **branch refs**: Article 101.5

## 35. la_q35

**Q:** Consider the situation in which a market surveillance authority (MSA) determines that an AI system, originally classified as non-high-risk by the provider, is in fact high-risk. Does the provider need to recall and suspend the use of the system without undue delay, or does the MSA provide a timeframe within which the provider can take corrective actions? Or does this depend on the gravity of the situation?

**A:** The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.

- **gold refs**: Annex III, Article 79, Article 80
- **branch refs**: Article 74, Article 16, Article 6, Article 50, Annex III, Annex I, Article 11

## 36. la_q36

**Q:** Under the EU AI Act, what presumption applies when a high-risk AI system is trained and tested on data that reflects the specific geographical, behavioural, contextual or functional setting in which it is intended to be used?

**A:** Adds two further presumptions of conformity beyond Articles 40-41: Article 42(1), high-risk AI systems trained and tested on data reflecting the specific geographical, behavioural, contextual, or functional setting in which they are intended to be used are presumed to comply with the relevant data-governance requirements of Article 10(4); Article 42(2), high-risk AI systems certified or for which a statement of conformity has been issued under a cybersecurity scheme under Regulation (EU) 2019/881 (the Cybersecurity Act) and whose references are published in the Official Journal are presumed to comply with the cybersecurity requirements of Article 15 to the extent the cybersecurity certificate or statement covers those requirements.

- **gold refs**: Article 10, Article 42
- **branch refs**: Article 6, Article 42, Article 10

## 37. la_q37

**Q:** When registering a high-risk AI system in the EU database under the EU AI Act, what specific information must the provider submit? List the required items.

**A:** The Commission shall, in collaboration with the Member States, set up and maintain an EU database containing information referred to in paragraphs 2 and 3 of this Article concerning high-risk AI systems referred to in Article 6(2) which are registered in accordance with Articles 49 and 60 and AI systems that are not considered as high-risk pursuant to Article 6(3) and which are registered in accordance with Article 6(4) and Article 49. When setting the functional specifications of such database, the Commission shall consult the relevant experts, and when updating the functional specifications of such database, the Commission shall consult the Board.

- **gold refs**: Annex III, Annex VIII, Article 49, Article 71
- **branch refs**: Article 6, Article 71, Article 49, Article 26, Article 83, Article 66, Article 16

## 38. la_q38

**Q:** Under the EU AI Act, what is an "AI regulatory sandbox"? Provide the definition elements (what it is, who sets it up, for whom it is intended, to do what, for how long).

**A:** A controlled framework set up by a competent authority which offers providers or prospective providers of AI systems the possibility to develop, train, validate and test, where appropriate in real-world conditions, an innovative AI system, pursuant to a sandbox plan for a limited time under regulatory supervision.

- **gold refs**: Article 57, Article 62
- **branch refs**: Article 3.55, Article 57, Article 2

## 39. la_q39

**Q:** Under the EU AI Act, what transparency obligation applies to deployers when they use an AI system to generate or manipulate text for the purpose of informing the public on matters of public interest, and what are the two exceptions where this obligation does not apply?

**A:** Under Article 50(4), a deployer that uses an AI system to generate or manipulate text published to inform the public on matters of public interest must disclose that the text has been artificially generated or manipulated. Under Article 50(4), that disclosure duty does not apply in two cases: first, where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences; and second, where the AI-generated content has undergone a process of human review or editorial control and a natural or legal person holds editorial responsibility for the publication of the content.

- **gold refs**: Article 50
- **branch refs**: Article 50.4, Article 50

## 40. la_q40

**Q:** Under the EU AI Act, when a high-risk AI system is found to conform with the requirements, what information must the Union technical documentation assessment certificate contain?

**A:** Under Annex VII point 4.6, where the notified body finds the high-risk AI system conforms with the Chapter III Section 2 requirements, it issues a Union technical documentation assessment certificate. Per Annex VII point 4.6, that certificate must indicate the name and address of the provider, the conclusions of the examination, the conditions (if any) for its validity, and the data necessary for the identification of the AI system.

- **gold refs**: Annex IV, Article 11
- **branch refs**: Annex VII

## 41. la_q41

**Q:** Under the EU AI Act, is there a simplified way for SMEs (including startups) to provide the technical documentation for high-risk AI systems, and who must accept it for conformity assessment?

**A:** Yes. Under Article 11(1), SMEs, including start-ups, may provide the technical documentation elements set out in Annex IV in a simplified manner, using a simplified form the Commission is required to establish for the needs of small and micro enterprises. Where an SME opts to use that form, the notified body performing the conformity assessment must accept it.

- **gold refs**: Annex IV, Article 11
- **branch refs**: Article 11.1, Article 11, Annex IV, Annex IV.2

## 42. la_q42

**Q:** Under the EU AI Act, must an employer inform affected workers and workers' representatives before putting into service or using a high-risk AI system in the workplace? If so, should possibly specific rules or procedures be followed to provide this information?

**A:** Yes. Under Article 26(7), a deployer that is an employer must, before putting a high-risk AI system into service or using it at the workplace, inform the workers' representatives and the affected workers that they will be subject to the use of that high-risk AI system. Under Article 26(7), that information must be provided, where applicable, in accordance with the rules and procedures laid down in Union and national law and practice on the information of workers and their representatives.

- **gold refs**: Article 26
- **branch refs**: Article 26.7, Article 26

## 43. la_q43

**Q:** Under Article 10(5) of the EU AI Act, when may a provider of a high-risk AI system process special categories of personal data for bias detection and correction, and what key safeguards/conditions must be met?

**A:** Under Article 10(5), a provider of a high-risk AI system may exceptionally process special categories of personal data only to the extent strictly necessary to ensure bias detection and correction, subject to appropriate safeguards. Article 10(5) requires all of the following: the bias work cannot be done with other data, including synthetic or anonymised data (a); technical limits on re-use plus state-of-the-art security and pseudonymisation (b); strict, documented access controls to prevent misuse (c); no transmission or transfer to other parties (d); deletion once the bias is corrected or the retention period ends, whichever is first (e); and records of processing documenting why it was strictly necessary (f).

- **gold refs**: Article 10
- **branch refs**: Article 10.5, Article 10

## 44. la_q44

**Q:** What does Article 13 require for transparency?

**A:** Article 13 requires high-risk AI systems to be designed and developed so that their operation is sufficiently transparent to enable deployers to interpret the system's output and use it appropriately. An appropriate type and degree of transparency must be ensured with a view to achieving compliance with the relevant obligations of both the provider and the deployer set out in the Regulation (Article 13(1)). High-risk AI systems must be accompanied by instructions for use in an appropriate digital format that include concise, complete, correct and clear information that is relevant, accessible and comprehensible to deployers, covering matters such as known or foreseeable circumstances that may lead to risks to health, safety or fundamental rights, and the level of accuracy, robustness and cybersecurity (Article 13(2), Article 13(3)).

- **gold refs**: Article 13
- **branch refs**: Article 13

## 45. la_q45

**Q:** What are the obligations of deployers of high-risk AI systems?

**A:** Deployers of high-risk AI systems must use the system in accordance with the provider's instructions for use, assign human oversight to natural persons who have the necessary competence and training, monitor the system's operation and inform the provider where relevant, ensure input data relevance and representativeness to the extent the deployer controls the input data, retain automatically generated logs, inform affected natural persons that they are subject to the use of the system, and inform workers and their representatives where the system is used in the workplace (Article 26). Where the deployer is a body governed by public law, a private entity providing public services, or a deployer of systems under Annex III points 5(b) and (c), it must perform a fundamental rights impact assessment before first use covering its processes, affected categories of persons, specific risks, human oversight measures and remedial arrangements, and notify the result to the market surveillance authority (Article 27). Any affected person subject to a deployer decision based on the output of an Annex III high-risk system, where that decision produces legal effects or similarly significantly affects health, safety or fundamental rights, has the right to obtain from the deployer clear and meaningful explanations of the system's role and the main elements of the decision taken (Article 86).

- **gold refs**: Annex III, Article 13, Article 26, Article 27
- **branch refs**: Article 26, Article 27, Article 86, Annex III

## 46. la_q46

**Q:** Is an AI system that recommends recipes high risk?

**A:** The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.

- **gold refs**: Annex I, Annex III, Article 5, Article 6
- **branch refs**: Article 6, Article 50, Annex III, Annex I

## 47. la_q47

**Q:** Explain the risk categories in the EU AI Act

**A:** The EU AI Act sets four risk tiers plus a separate regime for general-purpose AI models: unacceptable-risk practices are prohibited under Article 5; and high-risk systems are classified under Article 6 (an Annex I product safety component, or an Annex III use case) and carry the Chapter III Section 2 obligations. Limited-risk systems carry the Article 50 transparency duties, minimal-risk systems have no mandatory duties under the Act, and general-purpose AI models are governed separately under Articles 51 to 56, with added obligations under Article 55 for models classified as having systemic risk under Article 51.

- **gold refs**: Article 5
- **branch refs**: Article 6, Article 5, Article 50, Article 51, Article 52, Annex I, Annex III, Article 53, Article 54, Article 55, Article 56

## 48. la_q51

**Q:** What should my company do to comply with AI rules in Europe?

**A:** Adds two further presumptions of conformity beyond Articles 40-41: Article 42(1), high-risk AI systems trained and tested on data reflecting the specific geographical, behavioural, contextual, or functional setting in which they are intended to be used are presumed to comply with the relevant data-governance requirements of Article 10(4); Article 42(2), high-risk AI systems certified or for which a statement of conformity has been issued under a cybersecurity scheme under Regulation (EU) 2019/881 (the Cybersecurity Act) and whose references are published in the Official Journal are presumed to comply with the cybersecurity requirements of Article 15 to the extent the cybersecurity certificate or statement covers those requirements. Article 55 adds four obligations on top of Article 53 for GPAI providers with systemic risk: (a) model evaluation in accordance with standardised protocols and tools reflecting the state of the art, including conducting and documenting adversarial testing to identify and mitigate systemic risks; (b) assess and mitigate possible systemic risks at Union level, including their sources, that may stem from development, market-placement, or use of the model; (c) keep track of, document, and report without undue delay to the AI Office (and national competent authorities where appropriate) information about serious incidents and possible corrective measures; (d) ensure an adequate level of cybersecurity protection for both the model AND its physical infrastructure. Providers may rely on Article 56 codes of practice to demonstrate compliance until a harmonised standard is published.

- **gold refs**: Article 1, Article 10, Article 8, Article 9
- **branch refs**: Article 42, Article 55, Article 16

## 49. la_q52

**Q:** Can you help me understand AI compliance?

**A:** Under Article 111, transitional provisions grandfather pre-existing AI systems and GPAI models on the market before key dates unless they undergo a substantial change in design; high-risk systems for public-authority use comply from 2 August 2030. Under Article 86, any affected person subject to a decision based on output from an Annex III high-risk AI system has the individual right to obtain a clear and meaningful explanation of the AI system's role in the decision-making procedure. Transitional provisions for AI systems and GPAI models already on the market / in service: high-risk AI for public-authority use placed on the market before 2 August 2026 must comply from 2 August 2030 (only if significant design change); pre-2 August 2025 GPAI models brought into compliance by 2 August 2027; large-scale IT systems listed in Annex X covered by the Regulation from 31 December 2030.

- **gold refs**: Article 17, Article 56
- **branch refs**: Article 111, Article 8, Article 86

## 50. la_q53

**Q:** We are building a chatbot for customer support. What do we need to know?

**A:** Under Article 50, limited-risk transparency: AI systems interacting with natural persons must disclose AI nature; emotion-recognition and biometric-categorisation systems must inform exposed persons; deepfakes and AI-generated content must be labelled. Article 25(2) requires the initial provider and the new provider to cooperate along the value chain: the initial provider must make available the necessary information and provide the reasonably expected technical access and other assistance so that the new provider can meet its obligations, in particular the conformity assessment of high-risk AI systems. Article 25(4) is a separate duty: the high-risk provider and third-party suppliers of AI systems, tools, services, components or processes used in or integrated into a high-risk AI system must specify, by written agreement, the necessary information, capabilities, technical access and other assistance, except for third parties making tools, services, processes or components (other than general-purpose AI models) accessible to the public under a free and open-source licence. For general-purpose AI models, the one-third fine-tune rule (per the Commission's 18 July 2025 GPAI Guidelines, anchored on Article 51) makes the downstream modifier a new provider when additional training compute exceeds 1/3 of the base model's compute, or 1/3 of the 10^25 FLOPs systemic threshold (~3.3×10^24 FLOPs) when base compute is unknown. Under Article 50, Transparency obligations split by actor: providers must ensure AI systems interacting.

- **gold refs**: Annex I, Annex III, Annex XI, Annex XII, Article 25, Article 51, Article 53, Article 55, Article 6
- **branch refs**: Article 50, Article 25, Article 29

## 51. la_q54

**Q:** Tell me about emotion recognition rules

**A:** Under Article 5.1.f, emotion recognition in the workplace and in educational institutions is prohibited, including monitoring employees or call-centre agents, with a narrow medical/safety carve-out for systems placed on the market for therapeutic or accident-prevention purposes. Transparency obligations split by actor: providers must ensure AI systems interacting with natural persons disclose their AI nature (Article 50(1)) and must mark synthetic AI-generated content in a machine-readable, detectable format (Article 50(2)); deployers must inform exposed persons when operating emotion-recognition or biometric-categorisation systems (Article 50(3)) and must label deepfakes as artificially generated or manipulated (Article 50(4)). Article 50(4) also requires deployers who use an AI system to generate or manipulate text published to inform the public on matters of public interest to disclose that the text was artificially generated or manipulated; this disclosure duty does not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for publishing it.

- **gold refs**: Article 5
- **branch refs**: Article 5.1.f

## 52. la_q55

**Q:** hi, what can you do?

**A:** I am Lexy, a Compliance assistant that can answer your questions related to the EU AI Act, based on my Knowledge Graph and ontology. What can I help you with?

- **gold refs**: (none)
- **branch refs**: (none)

## 53. la_q56

**Q:** What's the best restaurant in Rome?

**A:** One of the most highly praised restaurants in Rome is Roscioli, a historic deli‑restaurant near Campo de’ Fiori that blends traditional Roman dishes (like carbonara and cacio e pepe) with a superb wine list and upscale service. Reservations are recommended, especially for dinner.

- **gold refs**: (none)
- **branch refs**: (none)

## 54. la_q60

**Q:** What are the algorithmic transparency obligations for a Very Large Online Platform content-moderation AI?

**A:** This question is about the Digital Services Act (DSA), not the EU AI Act (Regulation 2024/1689). This assistant only covers EU AI Act questions; consult the Digital Services Act (DSA) for the applicable rules.

- **gold refs**: Article 50
- **branch refs**: (none)

## 55. la_q63

**Q:** What are the algorithmic transparency obligations for a Very Large Online Platform content-moderation AI?

**A:** This question is about the Digital Services Act (DSA), not the EU AI Act (Regulation 2024/1689). This assistant only covers EU AI Act questions; consult the Digital Services Act (DSA) for the applicable rules.

- **gold refs**: Article 50
- **branch refs**: (none)

## 56. la_q64

**Q:** Is AI software that detects melanoma from dermoscopy images a high-risk AI system under the EU AI Act?

**A:** High-risk where the software qualifies as a medical device that must undergo third-party conformity assessment. AI software that detects melanoma from dermoscopy images is itself a product covered by Regulation (EU) 2017/745 on medical devices, which is listed in Annex I, and such diagnostic software is typically classified as a higher-risk medical device requiring third-party conformity assessment by a notified body under that regulation, thereby satisfying both cumulative conditions of Article 6(1). Under Article 43(3), the provider follows the conformity assessment procedure required by the medical devices regulation, with the Chapter III Section 2 requirements forming part of that assessment.

- **gold refs**: Annex I, Annex III, Article 6
- **branch refs**: Article 6.1, Annex I, Article 43.3

## 57. la_q65

**Q:** Which EU AI Act article sets the transparency obligation for a patient-facing medical chatbot?

**A:** Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties; both apply to the same system, not in the alternative. Transparency obligations split by actor: providers must ensure AI systems interacting with natural persons disclose their AI nature (Article 50(1)) and must mark synthetic AI-generated content in a machine-readable, detectable format (Article 50(2)); deployers must inform exposed persons when operating emotion-recognition or biometric-categorisation systems (Article 50(3)) and must label deepfakes as artificially generated or manipulated (Article 50(4)). Article 50(4) also requires deployers who use an AI system to generate or manipulate text published to inform the public on matters of public interest to disclose that the text was artificially generated or manipulated; this disclosure duty does not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for publishing it.

- **gold refs**: Article 50
- **branch refs**: Article 50.1, Article 13

## 58. la_q66

**Q:** Under the EU AI Act, is an AI system used to dispatch and triage emergency-room patients high-risk?

**A:** High-risk. An AI system used to dispatch and triage emergency-room patients falls within Annex III(5)(d), which covers AI systems intended to evaluate and classify emergency calls, to dispatch or establish priority in the dispatching of emergency first response services, and emergency healthcare patient triage systems; Article 6(2) classifies all Annex III systems as high-risk. No prohibited practice under Article 5 is engaged by this use case on its stated facts.

- **gold refs**: Annex III, Article 5, Article 6
- **branch refs**: Article 5, Article 6.2, Annex III.5.d

## 59. la_q67

**Q:** What does the EU AI Act require for an AI system that evaluates patients' eligibility for public healthcare benefits?

**A:** Eight high-risk use-case categories: biometrics, critical infrastructure, education + vocational training, employment + worker management (recruitment, task allocation, promotion and termination decisions, and performance evaluation affecting workers' fundamental rights), essential private + public services, law enforcement, migration + asylum + border control, and administration of justice + democratic processes. Classifies an AI system as high-risk on two routes. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation.

- **gold refs**: Annex III, Article 6
- **branch refs**: Article 6, Annex III, Article 5, Annex I

## 60. la_q68

**Q:** Are AI systems used solely for scientific biomedical research and not placed on the market subject to the EU AI Act?

**A:** Article 2(6) excludes from the Regulation AI systems or AI models specifically developed and put into service for the sole purpose of scientific research and development. An AI system used solely for scientific biomedical research that is not placed on the market or put into service for any purpose beyond that research therefore falls outside the scope of the EU AI Act. The exclusion requires that the system be developed and used exclusively for scientific research and development; if the system were subsequently placed on the market or put into service for a non-research purpose, the exclusion would no longer apply and the full Regulation would govern it.

- **gold refs**: Article 2
- **branch refs**: Article 2.6

## 61. la_q69

**Q:** Is an AI system that infers patients' emotions for a medical purpose prohibited under Article 5 of the EU AI Act?

**A:** Under Article 5.1.f, emotion recognition in the workplace and in educational institutions is prohibited, including monitoring employees or call-centre agents, with a narrow medical/safety carve-out for systems placed on the market for therapeutic or accident-prevention purposes. Real-time remote biometric identification by law enforcement is prohibited under Article 5 save for narrow, exhaustively-listed law-enforcement exceptions that each require prior judicial or administrative authorisation; under Article 5(5) Member States may enable those exceptions in national law and may set stricter national rules. Article 5(1)(c) carve-out: the social-scoring prohibition does not affect lawful evaluation practices of natural persons that are carried out for a specific purpose in accordance with Union and national law (Recital 31 final sentence).

- **gold refs**: Article 5
- **branch refs**: Article 5.1.f

## 62. la_q71

**Q:** A hospital deploys a high-risk AI diagnostic system. What are its obligations as a deployer under the EU AI Act?

**A:** Under Article 27, in addition to Article 26 baseline duties, deployers of certain Annex III high-risk AI systems must perform a Fundamental Rights Impact Assessment (FRIA) covering affected persons and specific fundamental rights risks. Under Article 86, any affected person subject to a decision based on output from an Annex III high-risk AI system has the individual right to obtain a clear and meaningful explanation of the AI system's role in the decision-making procedure. Deployers of a high-risk AI system listed in Annex III are bound by Article 26, Article 27, and Article 13 (plus follow-on obligations summarised in the references list). Article 14 requires effective human oversight by natural persons during system use, capability + limitation awareness, automation-bias safeguards, ability to interpret output, disregard / override / intervene, and (for biometric identification) a two-person verification rule.

- **gold refs**: Annex III, Article 13, Article 25, Article 26, Article 27, Article 86
- **branch refs**: Article 26, Article 27, Article 13, Article 86, Article 14, Article 9, Article 6

## 63. la_q72

**Q:** What must the provider of a high-risk AI medical diagnostic system put in place before placing it on the market?

**A:** Providers of a high-risk AI system listed in Annex III are bound by Article 6, Article 8, and Article 9 (plus follow-on obligations summarised in the references list). Under Article 16, Providers of high-risk AI systems must ensure the system meets the Chapter III Section 2. Article 43 requires providers of high-risk AI to undergo a conformity assessment: internal-control. Article 10 requires training, validation, and test datasets to be relevant, representative.

- **gold refs**: Annex IV, Article 10, Article 11, Article 16, Article 8, Article 9
- **branch refs**: Article 6, Article 16, Article 43, Article 8, Article 9, Article 10, Article 11

## 64. la_q73

**Q:** What conformity-assessment route applies to an AI system that is a safety component of a CE-marked medical device?

**A:** Under Article 27, in addition to Article 26 baseline duties, deployers of certain Annex III high-risk AI systems must perform a Fundamental Rights Impact Assessment (FRIA) covering affected persons and specific fundamental rights risks. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation. Article 49 requires providers (and deployers that are public authorities) to register themselves and their high-risk AI system in the EU database (Article 71) before placing the system on the market or putting it into service.

- **gold refs**: Annex I, Article 6
- **branch refs**: Article 43, Article 6, Article 27, Article 49

## 65. la_q74

**Q:** What human-oversight measures does the EU AI Act require for a high-risk clinical decision-support system?

**A:** Article 14 requires that a high-risk clinical decision-support system be designed so that natural persons can effectively oversee it during use, with oversight measures commensurate with the risks, level of autonomy and context of use, ensured through measures built into the system by the provider, measures to be implemented by the deployer, or both. Specifically, Article 14(4) requires that the oversight persons be enabled to properly understand the system's capacities and limitations and monitor its operation including detecting anomalies, to remain aware of automation bias (particularly relevant where the system provides information or recommendations for decisions taken by natural persons), to correctly interpret the system's output using available interpretation tools and methods, to decide not to use the system or to disregard, override or reverse its output in any particular situation, and to intervene in or interrupt the system through a stop button or similar procedure allowing it to halt safely. Article 14(2) specifies that human oversight shall aim to prevent or minimise risks to health, safety or fundamental rights, including where such risks persist despite other requirements being met. On the deployer side, Article 26(2) requires the deployer to assign human oversight to natural persons who have the necessary competence, training and authority, as well as the necessary support. Article 26(1) requires the deployer to take appropriate technical and organisational measures to use the system in accordance with the instructions for use. Article 26(5) requires the deployer to monitor the system's operation on the basis of those instructions and to inform the provider of serious incidents. Article 13(3)(d) requires the provider's instructions for use to describe the human oversight measures, including the technical measures put in place to facilitate interpretation of the system's outputs by deployers.

- **gold refs**: Article 13, Article 14
- **branch refs**: Article 14.4, Article 14.2, Article 26

## 66. la_q75

**Q:** What data-governance obligations apply to the training data of a high-risk AI sepsis-prediction model?

**A:** Deployer obligations: use the system per the instructions, assign human oversight to competent + trained natural persons, monitor operation, retain automatically generated logs, inform affected workers (for workplace use), and cooperate with market-surveillance authorities. Article 26 carve-outs: deployers that are financial institutions subject to Union financial-services internal-governance requirements fulfil the Article 26(5) monitoring obligation and the Article 26(6) log-retention obligation by complying with the governance arrangements under that financial-services law (Article 26(5) second subparagraph; Article 26(6) second subparagraph). Workplace deployers who are employers must inform workers' representatives and the affected workers BEFORE putting the high-risk system into service (Article 26(7)); applicable Union and national worker-information rules continue to apply.

- **gold refs**: Article 10
- **branch refs**: Article 10, Article 26, Article 13

## 67. la_q76

**Q:** What logging and record-keeping does a high-risk AI radiology system require, and how long must the deploying hospital keep the logs?

**A:** The provider must design the high-risk radiology system to allow automatic recording of events (logs) over its lifetime, with logging capabilities that enable recording of events relevant to identifying risks, facilitating post-market monitoring, and monitoring operation, at a level of traceability appropriate to the intended purpose (Article 12). The provider must keep those automatically generated logs for a period appropriate to the intended purpose, at a minimum of six months, unless Union or national law provides otherwise (Article 19). The deploying hospital, as deployer, must keep the logs automatically generated by the system, to the extent such logs are under its control, for a period appropriate to the intended purpose, of at least six months, unless applicable Union or national law provides otherwise (Article 26(6)).

- **gold refs**: Article 12, Article 26
- **branch refs**: Article 12, Article 26.6, Article 19

## 68. la_q77

**Q:** Does the EU AI Act require post-market monitoring and serious-incident reporting for an AI-based patient-monitoring device, and under which articles?

**A:** Yes. An AI-based patient-monitoring device is high-risk under Article 6(1) where it is a safety component of, or is itself, a medical device covered by the Medical Devices Regulation listed in Annex I Section A and that device must undergo third-party conformity assessment. As a high-risk system, the provider must establish and document a post-market monitoring system that actively collects and analyses performance data throughout the system's lifetime to evaluate continuous compliance, based on a post-market monitoring plan forming part of the technical documentation (Article 72(1) to (3), Annex IV). Article 72(4) permits the provider to integrate those elements into the post-market surveillance system already required under the Medical Devices Regulation rather than maintaining a parallel one. For serious incident reporting, Article 73 applies, but Article 73(9) narrows the AI Act reporting duty for high-risk systems covered by Union legislation with equivalent reporting obligations: notification is limited to serious incidents consisting of an infringement of Union law protecting fundamental rights, reported to the market surveillance authority of the Member State where the incident occurred, while incidents involving death or serious deterioration of health route through the medical-device vigilance framework instead.

- **gold refs**: Article 72, Article 73, Article 3
- **branch refs**: Article 72.1, Article 72.4, Article 73.9, Article 73.1

## 69. la_q78

**Q:** A pharma company trains a large foundation model for drug discovery whose training compute exceeds 10^25 FLOPs. Which EU AI Act obligations apply?

**A:** Under Article 51, a GPAI model has systemic risk when cumulative training compute exceeds 10²⁵ FLOPs (10^25); providers must notify the Commission within two weeks of meeting the threshold. Classifies a general-purpose AI model as having 'systemic risk' when it has high-impact capabilities (presumed when cumulative training compute exceeds 10^25 FLOPs) or when so designated by the Commission based on Annex XIII criteria. Commission's 18 July 2025 GPAI Guidelines presume a model is general-purpose (Article 3(63)) when training compute exceeds 10^23 FLOPs and the model can generate language, image, audio, or video output. Fine-tuned or modified models become new providers under Article 25 when their additional training compute exceeds one-third of the base model's compute (or one-third of the 10^25 systemic threshold, ~3.3×10^24 FLOPs, when base compute is unknown). Defines 68 terms used in the Regulation, including 'AI system' (machine-based, varying autonomy, possibly adaptive, inferring from input how to generate output influencing physical/virtual environments), 'provider', 'deployer', 'placing on the market', 'putting into service', 'substantial modification', 'general-purpose AI model', 'general-purpose AI system', 'systemic risk'.

- **gold refs**: Annex III, Article 25, Article 3, Article 51, Article 6
- **branch refs**: Article 51, Article 25

## 70. la_q79

**Q:** If a hospital fine-tunes an open-weight medical language model, when does it become a provider under the EU AI Act?

**A:** A hospital becomes a provider under Article 25(1) in any of three circumstances: it puts its name or trademark on a high-risk AI system already placed on the market, it makes a substantial modification to such a system so that it remains high-risk, or it modifies the intended purpose of a non-high-risk system so that it becomes high-risk. Fine-tuning an open-weight medical language model therefore triggers provider status where the fine-tuning constitutes a substantial modification to a high-risk system, or where it changes the intended purpose of a system that was not high-risk into one that is high-risk under Article 6. If the resulting system qualifies as a medical device requiring third-party conformity assessment under the Medical Device Regulation (listed in Annex I), it is high-risk under Article 6(1), and the hospital as product manufacturer assumes provider obligations under Article 25(3). Once provider status attaches, the hospital bears all provider obligations under Article 16, including the Article 50 transparency duties where the system interacts directly with natural persons, and the AI literacy obligation under Article 4.

- **gold refs**: Article 25, Article 4, Article 50
- **branch refs**: Article 25.1, Article 25.3, Article 50, Article 4, Article 6.1

## 71. la_q80

**Q:** What transparency obligation applies to AI-generated synthetic medical images used to augment a training dataset?

**A:** Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties; both apply to the same system, not in the alternative. Transparency obligations split by actor: providers must ensure AI systems interacting with natural persons disclose their AI nature (Article 50(1)) and must mark synthetic AI-generated content in a machine-readable, detectable format (Article 50(2)); deployers must inform exposed persons when operating emotion-recognition or biometric-categorisation systems (Article 50(3)) and must label deepfakes as artificially generated or manipulated (Article 50(4)). Article 50(4) also requires deployers who use an AI system to generate or manipulate text published to inform the public on matters of public interest to disclose that the text was artificially generated or manipulated; this disclosure duty does not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for publishing it.

- **gold refs**: Article 50
- **branch refs**: Article 50, Article 13
## 72. la_q81

**Q:** Classify the EU AI Act risk tier of an AI ambient scribe that only transcribes doctor-patient consultations and performs no diagnosis or decision-making.

**A:** Under Article 50, limited-risk transparency: AI systems interacting with natural persons must disclose AI nature; emotion-recognition and biometric-categorisation systems must inform exposed persons; deepfakes and AI-generated content must be labelled. Classifies an AI system as high-risk on two routes. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation.

- **gold refs**: Annex III, Article 6
- **branch refs**: Article 50, Article 6.1, Article 42, Article 49

## 73. la_q82

**Q:** Classify the EU AI Act risk tier of a consumer wellness chatbot that gives general lifestyle tips and makes no medical claims.

**A:** Under Article 50, limited-risk transparency: AI systems interacting with natural persons must disclose AI nature; emotion-recognition and biometric-categorisation systems must inform exposed persons; deepfakes and AI-generated content must be labelled. Eight high-risk use-case categories: biometrics, critical infrastructure, education + vocational training, employment + worker management (recruitment, task allocation, promotion and termination decisions, and performance evaluation affecting workers' fundamental rights), essential private + public services, law enforcement, migration + asylum + border control, and administration of justice + democratic processes. Classifies an AI system as high-risk on two routes.

- **gold refs**: Annex I, Article 50, Article 6
- **branch refs**: Article 50, Article 6, Article 42, Article 49

## 74. la_q83

**Q:** Is an AI system used for biometric patient identification at hospital check-in high-risk under the EU AI Act?

**A:** Not high-risk unless the system qualifies as a product, or is a safety component of a product, covered by the Union harmonisation legislation listed in Annex I that must undergo third-party conformity assessment. A biometric system used solely to confirm that a patient is the person they claim to be is biometric verification, which Annex III(1)(a) explicitly excludes from the remote biometric identification use case listed there. The system therefore does not fall within Annex III and is not high-risk under Article 6(2). It could be high-risk under Article 6(1) if it is itself a medical device, or a safety component of one, that requires third-party conformity assessment under the Medical Devices Regulation listed in Annex I, but absent that condition it remains outside the high-risk tier and carries only the Article 50(1) provider obligation to ensure that natural persons are informed they are interacting with an AI system.

- **gold refs**: Annex III, Article 6
- **branch refs**: Annex I, Article 6.2, Article 6.1, Article 50.1, Annex III

## 75. la_q84

**Q:** An AI tool recommends oncology treatment regimens from clinical guidelines. What EU AI Act obligations does its provider face across the lifecycle?

**A:** Article 25(2) requires the initial provider and the new provider to cooperate along the value chain: the initial provider must make available the necessary information and provide the reasonably expected technical access and other assistance so that the new provider can meet its obligations, in particular the conformity assessment of high-risk AI systems. Article 25(4) is a separate duty: the high-risk provider and third-party suppliers of AI systems, tools, services, components or processes used in or integrated into a high-risk AI system must specify, by written agreement, the necessary information, capabilities, technical access and other assistance, except for third parties making tools, services, processes or components (other than general-purpose AI models) accessible to the public under a free and open-source licence. For general-purpose AI models, the one-third fine-tune rule (per the Commission's 18 July 2025 GPAI Guidelines, anchored on Article 51) makes the downstream modifier a new provider when additional training compute exceeds 1/3 of the base model's compute, or 1/3 of the 10^25 FLOPs systemic threshold (~3.3×10^24 FLOPs) when base compute is unknown. Requires the provider to draw up a written, machine-readable, signed and dated EU declaration of conformity for each high-risk AI system, containing the information in Annex V, kept at the disposal of national competent authorities for 10 years. Article 17 requires providers of high-risk AI systems to operate a quality management system covering regulatory-compliance strategy, design verification, examination + test procedures, post-market monitoring, and incident-reporting workflows.

- **gold refs**: Annex I, Annex III, Article 10, Article 13, Article 15, Article 16, Article 17, Article 19, Article 25, Article 49, Article 6, Article 9
- **branch refs**: Article 47, Article 16, Article 94, Article 71, Article 49, Article 80, Article 17

## 76. la_q85

**Q:** How does the EU AI Act interact with the Medical Device Regulation for AI medical-device software - which conformity route and timeline applies?

**A:** AI software that is itself a medical device, or is a safety component of one, is classified as high-risk under Article 6(1) where the Medical Device Regulation requires that product to undergo a third-party conformity assessment, which it does for devices in risk class IIa and above. The conformity route is set by Article 43(3): the provider follows the Medical Device Regulation's own notified-body conformity assessment procedure, and the Chapter III Section 2 requirements of the AI Act (risk management, data governance, technical documentation, logging, transparency, human oversight, accuracy and cybersecurity) form part of that single assessment, yielding one CE marking. The notified body conducting the MDR assessment is entitled to control compliance with those AI Act requirements provided it meets the competence conditions in Article 43(3). The Medical Device Regulation itself falls outside the scope of this answer, but Annex I lists it as Union harmonisation legislation triggering the Article 6(1) route. As to timeline, the obligations for high-risk AI systems under the AI Act apply from 2 August 2026, so providers of AI medical-device software must integrate the AI Act requirements into their MDR conformity assessment from that date onward.

- **gold refs**: Annex I, Annex III, Annex VI, Annex VII, Article 43, Article 6
- **branch refs**: Article 6.1, Article 43.3, Annex I

## 77. la_q86

**Q:** What does the EU AI Act require for an AI system used for risk assessment and pricing in health insurance?

**A:** Classifies an AI system as high-risk on two routes. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation. Annex III route (Article 6(2)): the system falls within one of the eight Annex III use cases.

- **gold refs**: Annex III, Article 6
- **branch refs**: Article 6, Annex III.5, Annex I

## 78. la_q87

**Q:** A clinical-trial sponsor uses AI to select and recruit eligible patients. Is this automatically high-risk under the EU AI Act?

**A:** Not automatically high-risk. An AI system used by a clinical-trial sponsor to select and recruit eligible patients is high-risk only where it falls within one of the two classification routes in Article 6. Under Article 6(1), the system would be high-risk if it is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I (such as a medical device under the MDR) and that product must undergo third-party conformity assessment. Under Article 6(2), the system would be high-risk if it falls within an Annex III use case; Annex III(4)(a) covers AI systems intended to be used for the recruitment or selection of natural persons, but that category addresses employment recruitment, not the selection of research participants for a clinical trial, which is a distinct activity. Because clinical-trial patient recruitment is neither an employment relationship nor one of the other listed Annex III use cases, the system does not engage Article 6(2) on its face. If, however, the system qualifies as a medical device requiring third-party conformity assessment under the MDR (which falls outside the scope of this answer to interpret), it would be high-risk via Article 6(1) read with Annex I.

- **gold refs**: Annex I, Annex III, Article 5, Article 50, Article 6
- **branch refs**: Article 6.1, Article 6.2, Annex III.4.a, Annex I

## 79. la_q88

**Q:** What penalties can be imposed on a medical-AI provider that places a non-conformant high-risk system on the market?

**A:** For high-risk AI systems the applicable penalty ceiling is set by Article 99(4): administrative fines of up to EUR 15 000 000 or, for an undertaking, up to 3 % of total worldwide annual turnover, whichever is higher, for non-compliance with the obligations on providers, deployers, importers and distributors (every obligation other than the Article 5 prohibitions, which carry the higher Article 99(3) ceiling of EUR 35 000 000 or 7 %). Under Article 99(6), for SMEs and start-ups each fine is capped at the lower of the percentage or the fixed amount. Penalties must be effective, proportionate and dissuasive.

- **gold refs**: Article 99
- **branch refs**: Article 99

## 80. la_q91

**Q:** What are the transparency rules for a Very Large Online Platform's content-moderation AI?

**A:** This question is about the Digital Services Act (DSA), not the EU AI Act (Regulation 2024/1689). This assistant only covers EU AI Act questions; consult the Digital Services Act (DSA) for the applicable rules.

- **gold refs**: Article 50
- **branch refs**: (none)

## 81. la_q92

**Q:** What does GDPR Article 17 say about the right to erasure?

**A:** This question is about a regulation outside the EU AI Act. This assistant answers EU AI Act questions only (Regulation 2024/1689). Please rephrase with a specific Article reference (e.g. "Article 13") or compliance dimension.

- **gold refs**: Article 17
- **branch refs**: (none)

