# R350 live-answers — legal_v2 judge report (all 81 rows, both arms)

Judge: claude-opus-4-5 via Bedrock (grounded in actual provision text)
Population: 81 rows × 2 arms = 162 judged rows

## Axes (paired deltas, bootstrap CI)

| axis | baseline | branch | delta | CI | verdict | n_pairs |
|---|---|---|---|---|---|---|
| ans_corr | 0.4198 | 0.3704 | -0.0494 | [-0.1235, 0.0247] | UNDERPOWERED | 81 |
| ref_corr | 0.4938 | 0.4938 | 0.0 | [-0.0617, 0.0617] | UNDERPOWERED | 81 |
| cite_faith | 0.8519 | 0.8148 | -0.037 | [-0.0988, 0.0123] | UNDERPOWERED | 81 |
| ans_conc | 0.7531 | 0.716 | -0.037 | [-0.0988, 0.0247] | UNDERPOWERED | 81 |

## Per-row verdicts

### live_answers:la_q44

**Q:** What does Article 13 require for transparency?

- **gold refs**: Article 13
- **base refs**: Article 13
- **branch refs**: Article 13

**base — answer (844 chars):**

```
Article 13 requires high-risk AI systems to be designed and developed so that their operation is sufficiently transparent to enable deployers to interpret the system's output and use it appropriately. An appropriate type and degree of transparency must be ensured with a view to achieving compliance with the relevant obligations of both the provider and the deployer set out in the Regulation (Article 13(1)). High-risk AI systems must be accompanied by instructions for use in an appropriate digital format that include concise, complete, correct and clear information that is relevant, accessible and comprehensible to deployers, covering matters such as known or foreseeable circumstances that may lead to risks to health, safety or fundamental rights, and the level of accuracy, robustness and cybersecurity (Article 13(2), Article 13(3)).
```

  - **ans_corr**: fail (minor attribution error (Section 3 vs. the Regulation))
  omission_detail: The predicted answer covers the main requirements of Article 13 including design transparency, instructions for use, and key content requirements. It does not exhaustively list all items in Article 13(3) but captures the essential holdings.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 13']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (844 chars):**

```
Article 13 requires high-risk AI systems to be designed and developed so that their operation is sufficiently transparent to enable deployers to interpret the system's output and use it appropriately. An appropriate type and degree of transparency must be ensured with a view to achieving compliance with the relevant obligations of both the provider and the deployer set out in the Regulation (Article 13(1)). High-risk AI systems must be accompanied by instructions for use in an appropriate digital format that include concise, complete, correct and clear information that is relevant, accessible and comprehensible to deployers, covering matters such as known or foreseeable circumstances that may lead to risks to health, safety or fundamental rights, and the level of accuracy, robustness and cybersecurity (Article 13(2), Article 13(3)).
```

  - **ans_corr**: pass (none)
  omission_detail: The predicted answer covers the main requirements of Article 13 including transparency design, instructions for use, and key content requirements. No significant operative holdings are omitted.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 13']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q87

**Q:** A clinical-trial sponsor uses AI to select and recruit eligible patients. Is this automatically high-risk under the EU AI Act?

- **gold refs**: Annex I, Annex III, Article 5, Article 50, Article 6
- **base refs**: Article 6.1, Article 50.1, Annex III.4.a, Annex I
- **branch refs**: Article 6.1, Article 6.2, Annex III.4.a, Annex I

**base — answer (944 chars):**

```
Not automatically high-risk. An AI system used by a clinical-trial sponsor to select and recruit eligible patients is not listed in Annex III(4)(a), which covers recruitment or selection of natural persons specifically in the employment context, not clinical-trial participant recruitment. The system would be high-risk under Article 6(1) only where it is itself a product, or a safety component of a product, covered by the Union harmonisation legislation listed in Annex I and that product is required to undergo third-party conformity assessment under that legislation, which could arise if the system qualifies as a medical device under the Medical Devices Regulation (the analysis of that instrument falls outside this scope). Absent either route, the system carries the Article 50(1) transparency obligation where it interacts directly with natural persons, requiring that those persons be informed they are interacting with an AI system.
```

  - **ans_corr**: pass (none)
  omission_detail: The predicted answer covers the key holdings: not automatically high-risk, Annex III(4)(a) does not apply, Article 6(1) medical device route could apply, and Article 50 transparency obligations apply otherwise. It also correctly notes the Article 6(3) derogation is not explicitly discussed but the core analysis is complete.
  - **ref_corr**: fail (misidentified applicable Annex III category and cited irrelevant transparency provision)
  wrong_refs: ['Article 50.1', 'Annex III.4.a']
  governing_refs: ['Article 6.1']
  missing_governing_refs: ['Annex III', 'Article 6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (1242 chars):**

```
Not automatically high-risk. An AI system used by a clinical-trial sponsor to select and recruit eligible patients is high-risk only where it falls within one of the two classification routes in Article 6. Under Article 6(1), the system would be high-risk if it is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I (such as a medical device under the MDR) and that product must undergo third-party conformity assessment. Under Article 6(2), the system would be high-risk if it falls within an Annex III use case; Annex III(4)(a) covers AI systems intended to be used for the recruitment or selection of natural persons, but that category addresses employment recruitment, not the selection of research participants for a clinical trial, which is a distinct activity. Because clinical-trial patient recruitment is neither an employment relationship nor one of the other listed Annex III use cases, the system does not engage Article 6(2) on its face. If, however, the system qualifies as a medical device requiring third-party conformity assessment under the MDR (which falls outside the scope of this answer to interpret), it would be high-risk via Article 6(1) read with Annex I.
```

  - **ans_corr**: pass (none)
  omission_detail: The predicted answer addresses both the Article 6(1) and Article 6(2) routes and correctly concludes the system is not automatically high-risk, which aligns with the gold answer's conditional verdict.
  - **ref_corr**: fail (Cited wrong Annex III category (employment recruitment instead of healthcare/medical) and missed Article 6(3) exception)
  wrong_refs: ['Annex III.4.a']
  governing_refs: ['Article 6.1', 'Article 6.2']
  missing_governing_refs: ['Annex III', 'Article 6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q76

**Q:** What logging and record-keeping does a high-risk AI radiology system require, and how long must the deploying hospital keep the logs?

- **gold refs**: Article 12, Article 26
- **base refs**: Article 12.3, Article 19, Article 18
- **branch refs**: Article 12, Article 26.6, Article 19

**base — answer (1267 chars):**

```
The provider must design the high-risk system so that it technically allows automatic recording of events (logs) over its lifetime, with logging capabilities that enable recording of events relevant to identifying situations presenting a risk or a substantial modification, facilitating post-market monitoring, and monitoring operation, as required by Article 12. The provider must keep those automatically generated logs for a period appropriate to the intended purpose, of at least six months unless Union or national law provides otherwise (Article 19). The deploying hospital, as deployer, must likewise keep the logs automatically generated by the system, to the extent such logs are under its control, for a period appropriate to the intended purpose of at least six months unless applicable Union or national law, in particular Union law on the protection of personal data, provides otherwise (Article 26(6) supplies this deployer-side duty, but as it is not in the citable list, the obligation is stated here from the provider-facing Article 12(3) minimum). The provider must also retain the technical documentation, quality management system documentation, and EU declaration of conformity for ten years after the system is placed on the market (Article 18).
```

  - **ans_corr**: fail (citation error and unsupported claims about provider obligations)
  omission_detail: The answer addresses the main logging requirements under Article 12 and the deployer log retention period under Article 26(6), which are the key elements the question asks about.
  - **ref_corr**: fail (cited provider documentation retention instead of deployer log retention obligation)
  wrong_refs: ['Article 18']
  governing_refs: ['Article 12.3']
  missing_governing_refs: ['Article 26']
  - **cite_faith**: pass (Article 12 cited for general logging design requirements but verbatim text specifies biometric identification logging specifics (Annex III point 1(a)), not general radiology system logging)
  - **ans_conc**: pass (none)

**branch — answer (839 chars):**

```
The provider must design the high-risk radiology system to allow automatic recording of events (logs) over its lifetime, with logging capabilities that enable recording of events relevant to identifying risks, facilitating post-market monitoring, and monitoring operation, at a level of traceability appropriate to the intended purpose (Article 12). The provider must keep those automatically generated logs for a period appropriate to the intended purpose, at a minimum of six months, unless Union or national law provides otherwise (Article 19). The deploying hospital, as deployer, must keep the logs automatically generated by the system, to the extent such logs are under its control, for a period appropriate to the intended purpose, of at least six months, unless applicable Union or national law provides otherwise (Article 26(6)).
```

  - **ans_corr**: pass (citation error - Article 19 cited for provider log retention not supported by provided text)
  omission_detail: The answer covers the main logging requirements under Article 12 and the deployer log retention obligation under Article 26(6) with the six-month minimum period
  - **ref_corr**: pass (none)
  governing_refs: ['Article 12', 'Article 26.6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q5

**Q:** Does the EU AI Act explicitly requires to use explainable AI techniques such as LIME or SHAP to increase the trustworthiness of high-risk AI systems?

- **gold refs**: Article 13
- **base refs**: Article 13, Article 14, Article 15
- **branch refs**: Article 13, Article 14, Article 15

**base — answer (441 chars):**

```
No, the EU AI Act mandates no specific explainable-AI technique such as LIME or SHAP, and Article 13 instead requires only that high-risk AI systems be sufficiently transparent for deployers to interpret their output. Article 14 requires effective human oversight, and Article 15 requires appropriate accuracy, robustness and cybersecurity. The Act is technique-agnostic, so the choice of any interpretability method is left to the provider.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 13']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (441 chars):**

```
No, the EU AI Act mandates no specific explainable-AI technique such as LIME or SHAP, and Article 13 instead requires only that high-risk AI systems be sufficiently transparent for deployers to interpret their output. Article 14 requires effective human oversight, and Article 15 requires appropriate accuracy, robustness and cybersecurity. The Act is technique-agnostic, so the choice of any interpretability method is left to the provider.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 13']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q47

**Q:** Explain the risk categories in the EU AI Act

- **gold refs**: Article 5
- **base refs**: Article 6, Article 5, Article 50, Article 51, Article 52, Annex I, Annex III, Article 53, Article 54, Article 55, Article 56
- **branch refs**: Article 6, Article 5, Article 50, Article 51, Article 52, Annex I, Annex III, Article 53, Article 54, Article 55, Article 56

**base — answer (621 chars):**

```
The EU AI Act sets four risk tiers plus a separate regime for general-purpose AI models: unacceptable-risk practices are prohibited under Article 5; and high-risk systems are classified under Article 6 (an Annex I product safety component, or an Annex III use case) and carry the Chapter III Section 2 obligations. Limited-risk systems carry the Article 50 transparency duties, minimal-risk systems have no mandatory duties under the Act, and general-purpose AI models are governed separately under Articles 51 to 56, with added obligations under Article 55 for models classified as having systemic risk under Article 51.
```

  - **ans_corr**: fail (Superficial treatment without substantive detail from provided text)
  omission_detail: The answer fails to explain the specific prohibited practices under Article 5 (subliminal/manipulative techniques, exploitation of vulnerabilities, social scoring, criminal risk profiling, facial recognition database scraping, emotion inference in workplaces/education, biometric categorisation by sensitive attributes, real-time remote biometric identification) which are detailed in the provided text and constitute the core content of the unacceptable risk category.
  - **ref_corr**: pass (inclusion of irrelevant GPAI provider obligation articles)
  governing_refs: ['Article 6', 'Article 5', 'Annex III']
  - **cite_faith**: pass (cited Article 55 for systemic risk obligations but provided text shows Article 53 contains GPAI model obligations, not Article 55)
  - **ans_conc**: pass (none)

**branch — answer (621 chars):**

```
The EU AI Act sets four risk tiers plus a separate regime for general-purpose AI models: unacceptable-risk practices are prohibited under Article 5; and high-risk systems are classified under Article 6 (an Annex I product safety component, or an Annex III use case) and carry the Chapter III Section 2 obligations. Limited-risk systems carry the Article 50 transparency duties, minimal-risk systems have no mandatory duties under the Act, and general-purpose AI models are governed separately under Articles 51 to 56, with added obligations under Article 55 for models classified as having systemic risk under Article 51.
```

  - **ans_corr**: fail (Superficial treatment - failed to detail the prohibited practices that define unacceptable risk despite text providing full Article 5 content)
  omission_detail: The answer fails to explain the specific prohibited practices under Article 5 (subliminal/manipulative techniques, exploitation of vulnerabilities, social scoring, criminal risk profiling, facial recognition database scraping, emotion inference in workplaces/education, biometric categorisation by sensitive attributes, real-time remote biometric identification) which are detailed in the provided text and constitute the core content of the unacceptable risk category.
  - **ref_corr**: fail (included irrelevant GPAI model provisions)
  wrong_refs: ['Article 53']
  governing_refs: ['Article 6', 'Article 5', 'Annex III']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q74

**Q:** What human-oversight measures does the EU AI Act require for a high-risk clinical decision-support system?

- **gold refs**: Article 13, Article 14
- **base refs**: Article 14.3, Article 14.4, Article 26.2
- **branch refs**: Article 14.4, Article 14.2, Article 26

**base — answer (1462 chars):**

```
Article 14 is the operative provision. It requires that a high-risk clinical decision-support system be designed so that natural persons can effectively oversee it during use, through measures identified and built into the system by the provider before placing it on the market, or measures appropriate to be implemented by the deployer, or both (Article 14(3)). Specifically, the oversight measures must enable the assigned persons to properly understand the system's capacities and limitations and monitor its operation including detecting anomalies, to remain aware of automation bias (particularly relevant where the system provides information or recommendations for clinical decisions), to correctly interpret the system's output using available interpretation tools, to decide not to use the system or to disregard, override or reverse its output in any particular situation, and to intervene in or interrupt the system through a stop button or similar procedure allowing it to halt safely (Article 14(4)). The deployer must assign human oversight to natural persons who have the necessary competence, training and authority (Article 26(2)). The provider must document the human oversight measures in the instructions for use, including the technical measures put in place to facilitate interpretation of outputs by deployers (Article 13(3)(d)), and the technical documentation must contain an assessment of the human oversight measures needed (Annex IV).
```

  - **ans_corr**: pass (minor unsupported citations)
  omission_detail: The answer covers the key requirements from Article 14 and Article 13 regarding human oversight measures. While it references Article 26(2) and Annex IV which are not in the provided text, the core holdings are addressed.
  - **ref_corr**: fail (incomplete coverage of Article 14 paragraphs and missing Article 13)
  governing_refs: ['Article 14.3', 'Article 14.4']
  missing_governing_refs: ['Article 13']
  - **cite_faith**: pass (citations to provisions without supplied verbatim text)
  - **ans_conc**: pass (none)

**branch — answer (1942 chars):**

```
Article 14 requires that a high-risk clinical decision-support system be designed so that natural persons can effectively oversee it during use, with oversight measures commensurate with the risks, level of autonomy and context of use, ensured through measures built into the system by the provider, measures to be implemented by the deployer, or both. Specifically, Article 14(4) requires that the oversight persons be enabled to properly understand the system's capacities and limitations and monitor its operation including detecting anomalies, to remain aware of automation bias (particularly relevant where the system provides information or recommendations for decisions taken by natural persons), to correctly interpret the system's output using available interpretation tools and methods, to decide not to use the system or to disregard, override or reverse its output in any particular situation, and to intervene in or interrupt the system through a stop button or similar procedure allowing it to halt safely. Article 14(2) specifies that human oversight shall aim to prevent or minimise risks to health, safety or fundamental rights, including where such risks persist despite other requirements being met. On the deployer side, Article 26(2) requires the deployer to assign human oversight to natural persons who have the necessary competence, training and authority, as well as the necessary support. Article 26(1) requires the deployer to take appropriate technical and organisational measures to use the system in accordance with the instructions for use. Article 26(5) requires the deployer to monitor the system's operation on the basis of those instructions and to inform the provider of serious incidents. Article 13(3)(d) requires the provider's instructions for use to describe the human oversight measures, including the technical measures put in place to facilitate interpretation of the system's outputs by deployers.
```

  - **ans_corr**: pass (none - answer is comprehensive and well-supported)
  omission_detail: The answer covers the key human oversight requirements from Article 14 and the transparency/instructions requirements from Article 13 that are present in the provided text.
  - **ref_corr**: fail (cited subsections but missed parent Article 14 and related Article 13)
  governing_refs: ['Article 14.4', 'Article 14.2']
  missing_governing_refs: ['Article 14', 'Article 13']
  - **cite_faith**: pass (citation to unprovided source text)
  - **ans_conc**: pass (none)

### live_answers:la_q83

**Q:** Is an AI system used for biometric patient identification at hospital check-in high-risk under the EU AI Act?

- **gold refs**: Annex III, Article 6
- **base refs**: Article 6.2, Article 6.1, Article 50.1, Annex III, Annex I
- **branch refs**: Annex I, Article 6.2, Article 6.1, Article 50.1, Annex III

**base — answer (1174 chars):**

```
Not high-risk unless the system qualifies as a remote biometric identification system or falls within the medical-device route. Annex III(1)(a) lists remote biometric identification systems as high-risk under Article 6(2), but expressly excludes biometric verification whose sole purpose is to confirm that a specific natural person is the person he or she claims to be. A hospital check-in system that merely verifies a patient's claimed identity against their own enrolled template is biometric verification and falls outside that listing. If, however, the system identifies patients from a database without prior claim of identity, it is a remote biometric identification system and is high-risk under Article 6(2) read with Annex III(1)(a). Separately, where the system is itself a medical device or a safety component of one that must undergo third-party conformity assessment under the Medical Devices Regulation listed in Annex I, it is high-risk under Article 6(1). Where neither route applies, the system carries only the Article 50(1) transparency obligation requiring the provider to design it so that patients are informed they are interacting with an AI system.
```

  - **ans_corr**: pass (minor unsupported claim about Article 50(1) transparency obligation)
  omission_detail: The answer correctly addresses the key distinction between remote biometric identification (high-risk) and biometric verification (excluded), which is the operative holding established by the verbatim text.
  - **ref_corr**: fail (included irrelevant transparency provision and missed derogation clause)
  wrong_refs: ['Article 50.1']
  governing_refs: ['Article 6.2', 'Annex III']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (938 chars):**

```
Not high-risk unless the system qualifies as a product, or is a safety component of a product, covered by the Union harmonisation legislation listed in Annex I that must undergo third-party conformity assessment. A biometric system used solely to confirm that a patient is the person they claim to be is biometric verification, which Annex III(1)(a) explicitly excludes from the remote biometric identification use case listed there. The system therefore does not fall within Annex III and is not high-risk under Article 6(2). It could be high-risk under Article 6(1) if it is itself a medical device, or a safety component of one, that requires third-party conformity assessment under the Medical Devices Regulation listed in Annex I, but absent that condition it remains outside the high-risk tier and carries only the Article 50(1) provider obligation to ensure that natural persons are informed they are interacting with an AI system.
```

  - **ans_corr**: fail (incomplete analysis of identification vs verification distinction)
  omission_detail: The answer fails to address that if the hospital check-in system performs identification against a database of multiple enrolled persons (rather than one-to-one verification), it would qualify as a remote biometric identification system under Annex III(1)(a) and would be high-risk. The gold answer emphasizes this distinction as the deciding factor.
  - **ref_corr**: fail (included irrelevant transparency provision and cited Article 6 paragraphs separately missing full Article 6 with derogation)
  wrong_refs: ['Article 50.1']
  governing_refs: ['Article 6.2', 'Annex III']
  missing_governing_refs: ['Article 6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q8

**Q:** Are AI safety components within medical devices of MDR class IIa, IIb, or III considered to be high-risk according to the EU AI Act? Why?

- **gold refs**: Annex I, Annex III, Article 43, Article 6
- **base refs**: Article 6.1, Annex I
- **branch refs**: Article 6.1, Annex I

**base — answer (921 chars):**

```
AI safety components within medical devices of MDR class IIa, IIb or III are high-risk. Article 6(1) classifies an AI system as high-risk where two cumulative conditions are met: the AI system is intended to be used as a safety component of a product, or is itself a product, covered by the Union harmonisation legislation listed in Annex I, and that product is required to undergo a third-party conformity assessment under that legislation. Annex I lists Regulation (EU) 2017/745 on medical devices, and under that Regulation medical devices of classes IIa, IIb and III must undergo third-party conformity assessment involving a notified body, so both conditions are fulfilled. For such systems, Article 43(3) requires the provider to follow the conformity assessment procedure laid down in the Medical Devices Regulation itself, with the Chapter III Section 2 requirements of the AI Act forming part of that assessment.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: fail (cited Article 6.1 instead of full Article 6)
  governing_refs: ['Article 6.1', 'Annex I']
  missing_governing_refs: ['Article 6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (891 chars):**

```
AI safety components within medical devices of MDR class IIa, IIb or III are high-risk. Article 6(1) classifies an AI system as high-risk where two cumulative conditions are met: the AI system is intended to be used as a safety component of a product, or is itself a product, covered by the Union harmonisation legislation listed in Annex I, and that product is required to undergo a third-party conformity assessment under that legislation. Annex I lists Regulation (EU) 2017/745 on medical devices, and under that Regulation medical devices of classes IIa, IIb and III must undergo third-party conformity assessment involving a notified body, so both conditions are fulfilled. For such systems, Article 43(3) requires the provider to follow the conformity assessment procedure of the sectoral legislation itself, with the Chapter III Section 2 requirements forming part of that assessment.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: fail (cited Article 6.1 instead of full Article 6)
  governing_refs: ['Article 6.1', 'Annex I']
  missing_governing_refs: ['Article 6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q64

**Q:** Is AI software that detects melanoma from dermoscopy images a high-risk AI system under the EU AI Act?

- **gold refs**: Annex I, Annex III, Article 6
- **base refs**: Article 6.1, Annex I, Article 43.3
- **branch refs**: Article 6.1, Annex I, Article 43.3

**base — answer (705 chars):**

```
High-risk where the software qualifies as a medical device that must undergo third-party conformity assessment. AI software that detects melanoma from dermoscopy images is itself a product covered by Regulation (EU) 2017/745 on medical devices, which is listed in Annex I, and such diagnostic software is typically classified as a higher-risk medical device requiring third-party conformity assessment by a notified body under that regulation, thereby satisfying both cumulative conditions of Article 6(1). Under Article 43(3), the provider follows the conformity assessment procedure required by the medical devices regulation, with the Chapter III Section 2 requirements forming part of that assessment.
```

  - **ans_corr**: fail (none)
  omission_detail: The answer correctly identifies the Article 6(1) pathway and explains that classification runs through Annex I rather than Annex III, which aligns with the gold answer's operative holding.
  - **ref_corr**: fail (cited Article 6.1 but not full Article 6 including paragraph 2)
  governing_refs: ['Article 6.1', 'Annex I']
  missing_governing_refs: ['Article 6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (705 chars):**

```
High-risk where the software qualifies as a medical device that must undergo third-party conformity assessment. AI software that detects melanoma from dermoscopy images is itself a product covered by Regulation (EU) 2017/745 on medical devices, which is listed in Annex I, and such diagnostic software is typically classified as a higher-risk medical device requiring third-party conformity assessment by a notified body under that regulation, thereby satisfying both cumulative conditions of Article 6(1). Under Article 43(3), the provider follows the conformity assessment procedure required by the medical devices regulation, with the Chapter III Section 2 requirements forming part of that assessment.
```

  - **ans_corr**: fail (minor unsupported procedural details)
  omission_detail: The answer correctly identifies the Article 6(1) pathway and explains that the software would be high-risk if it meets both conditions, which aligns with the gold answer's reasoning.
  - **ref_corr**: fail (incomplete Article 6 citation and missing Annex III)
  governing_refs: ['Article 6.1', 'Annex I']
  missing_governing_refs: ['Article 6', 'Annex III']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q88

**Q:** What penalties can be imposed on a medical-AI provider that places a non-conformant high-risk system on the market?

- **gold refs**: Article 99
- **base refs**: Article 99
- **branch refs**: Article 99

**base — answer (612 chars):**

```
For high-risk AI systems the applicable penalty ceiling is set by Article 99(4): administrative fines of up to EUR 15 000 000 or, for an undertaking, up to 3 % of total worldwide annual turnover, whichever is higher, for non-compliance with the obligations on providers, deployers, importers and distributors (every obligation other than the Article 5 prohibitions, which carry the higher Article 99(3) ceiling of EUR 35 000 000 or 7 %). Under Article 99(6), for SMEs and start-ups each fine is capped at the lower of the percentage or the fixed amount. Penalties must be effective, proportionate and dissuasive.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 99']
  - **cite_faith**: pass (Mischaracterized Article 99(6) SME cap mechanism)
  - **ans_conc**: pass (none)

**branch — answer (612 chars):**

```
For high-risk AI systems the applicable penalty ceiling is set by Article 99(4): administrative fines of up to EUR 15 000 000 or, for an undertaking, up to 3 % of total worldwide annual turnover, whichever is higher, for non-compliance with the obligations on providers, deployers, importers and distributors (every obligation other than the Article 5 prohibitions, which carry the higher Article 99(3) ceiling of EUR 35 000 000 or 7 %). Under Article 99(6), for SMEs and start-ups each fine is capped at the lower of the percentage or the fixed amount. Penalties must be effective, proportionate and dissuasive.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 99']
  - **cite_faith**: pass (Mischaracterized Article 99(6) SME cap mechanism)
  - **ans_conc**: pass (none)

### live_answers:la_q16

**Q:** What are the administrative fines for non-compliance with the prohibition of the AI practices?

- **gold refs**: Article 5, Article 50, Article 99
- **base refs**: Article 99, Article 5
- **branch refs**: Article 99.3, Article 99.6, Article 5

**base — answer (481 chars):**

```
Non-compliance with the prohibited AI practices listed in Article 5 is subject to administrative fines of up to EUR 35 000 000 or, if the offender is an undertaking, up to 7 % of its total worldwide annual turnover for the preceding financial year, whichever is higher (Article 99(3)). For SMEs including start-ups, the applicable ceiling is the lower of the percentage or the fixed amount (Article 99(6)). Penalties must be effective, proportionate and dissuasive (Article 99(1)).
```

  - **ans_corr**: pass (none)
  omission_detail: The answer correctly addresses the main fine amounts for Article 5 violations as requested by the question
  - **ref_corr**: pass (none)
  governing_refs: ['Article 99']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (466 chars):**

```
Non-compliance with the prohibited AI practices listed in Article 5 is subject to administrative fines of up to EUR 35 000 000 or, if the offender is an undertaking, up to 7 % of its total worldwide annual turnover for the preceding financial year, whichever is higher (Article 99(3)). Penalties must be effective, proportionate and dissuasive. For SMEs, including start-ups, the applicable ceiling is the lower of the percentage or the fixed amount (Article 99(6)).
```

  - **ans_corr**: pass (none)
  omission_detail: The answer correctly addresses the main fine amounts for Article 5 violations as requested by the question
  - **ref_corr**: pass (none)
  governing_refs: ['Article 99.3']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q14

**Q:** Which AI systems used in education or vocational training should be classified as high-risk according to the EU AI Act?

- **gold refs**: Annex III, Article 49, Article 6
- **base refs**: Annex III.3, Article 6.2, Article 6.3
- **branch refs**: Annex III.3, Article 6.2, Article 6.3

**base — answer (1104 chars):**

```
Under Annex III(3), AI systems in education and vocational training are classified as high-risk where they are intended to be used to determine access or admission or to assign natural persons to educational and vocational training institutions at all levels, to evaluate learning outcomes including when those outcomes steer the learning process, to assess the appropriate level of education an individual will receive or be able to access, or to monitor and detect prohibited behaviour of students during tests. Article 6(2) is the operative classification rule making all Annex III use cases high-risk. Under Article 6(3), an Annex III education system is not high-risk where it does not pose a significant risk of harm to health, safety or fundamental rights and performs one of four tasks (a narrow procedural task, improving the result of a previously completed human activity, detecting decision-making patterns without replacing or influencing the human assessment, or a preparatory task), but a system that performs profiling of natural persons is always high-risk regardless of that derogation.
```

  - **ans_corr**: fail (minor omission of procedural requirements)
  omission_detail: The answer omits the documentation and registration requirements under Article 6(4) and Article 49(2) that apply when a provider relies on the Article 6(3) derogation to conclude a system is not high-risk.
  - **ref_corr**: pass (none)
  governing_refs: ['Annex III.3', 'Article 6.2', 'Article 6.3']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (1110 chars):**

```
Under Annex III(3), AI systems in education and vocational training are classified as high-risk where they are intended to be used to determine access or admission or to assign natural persons to educational and vocational training institutions at all levels, to evaluate learning outcomes including when those outcomes steer the learning process, to assess the appropriate level of education an individual will receive or be able to access, or to monitor and detect prohibited behaviour of students during tests. Article 6(2) is the provision that classifies systems falling within Annex III as high-risk. Under Article 6(3), an Annex III education system is nevertheless not high-risk where it does not pose a significant risk of harm to health, safety or fundamental rights and performs only a narrow procedural task, improves the result of a previously completed human activity, detects decision-making patterns without replacing or influencing the human assessment, or performs a preparatory task, but a system that performs profiling of natural persons is always high-risk regardless of those conditions.
```

  - **ans_corr**: fail (minor omission of procedural requirements)
  omission_detail: The answer omits the documentation and registration requirements under Article 6(4) and Article 49(2) that apply when a provider concludes an Annex III system is not high-risk under the Article 6(3) derogation
  - **ref_corr**: pass (none)
  governing_refs: ['Annex III.3', 'Article 6.2', 'Article 6.3']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q20

**Q:** Should market surveilance authorities be provided with remote access to documentations and data sets used to develop a high-risk AI system?

- **gold refs**: Article 16, Article 26
- **base refs**: Article 74, Article 16, Article 26
- **branch refs**: Article 74.12, Article 78

**base — answer (666 chars):**

```
Yes. Under Article 16(k), the provider of a high-risk AI system must, upon a reasoned request of a national competent authority, demonstrate the conformity of the system with the Chapter III Section 2 requirements. Article 26 further obliges deployers to cooperate with market surveillance authorities. The Regulation does not, however, expressly mandate that providers grant market surveillance authorities standing remote access to documentation and data sets as a matter of system design. What it requires is that the provider keep the technical documentation (Article 16(d)) and make it available to demonstrate conformity when a competent authority requests it.
```

  - **ans_corr**: pass (none)
  omission_detail: The answer addresses both provider obligations under Article 16 and deployer cooperation obligations under Article 26, which aligns with the gold answer's key holdings.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 74']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (760 chars):**

```
Yes. Article 74(12) requires that market surveillance authorities be granted full access by providers to the documentation as well as the training, validation and testing data sets used for the development of high-risk AI systems, including, where appropriate and subject to security safeguards, through application programming interfaces or other relevant technical means and tools enabling remote access. This power is limited to what is necessary to fulfil their tasks. Article 78 imposes a confidentiality obligation on market surveillance authorities regarding the information and data so obtained, requiring them to protect intellectual property rights, confidential business information and trade secrets, and to delete data once it is no longer needed.
```

  - **ans_corr**: fail (Cites articles not present in provided text while omitting relevant provisions that are present)
  omission_detail: The answer fails to mention the obligations actually established in the provided text: Article 16(d) requiring providers to keep documentation, Article 16(k) requiring providers to demonstrate conformity upon reasoned request of national competent authority, and Article 26(12) requiring deployers to cooperate with relevant competent authorities.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 74.12']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q34

**Q:** Under the EU AI Act, what jurisdiction does the Court of Justice of the European Union have over Commission decisions fixing fines on providers of general-purpose AI models, and what can the Court do with the fine?

- **gold refs**: Article 101, Article 64, Article 99
- **base refs**: Article 101.5
- **branch refs**: Article 101.5

**base — answer (240 chars):**

```
Under Article 101(5), the Court of Justice of the European Union has unlimited jurisdiction to review Commission decisions fixing a fine on a provider of a general-purpose AI model. The Court may cancel, reduce or increase the fine imposed.
```

  - **ans_corr**: pass (none)
  omission_detail: The answer directly addresses the question about CJEU jurisdiction and what the Court can do with the fine. While it does not elaborate on the underlying fine provisions, the question specifically asked about jurisdiction and Court powers, which are fully addressed.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 101.5']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (238 chars):**

```
Under Article 101(5), the Court of Justice of the European Union has unlimited jurisdiction to review Commission decisions fixing a fine on providers of general-purpose AI models. The Court may cancel, reduce or increase the fine imposed.
```

  - **ans_corr**: pass (none)
  omission_detail: The answer directly addresses the question about CJEU jurisdiction and what the Court can do with the fine. While it does not elaborate on the underlying fine provisions, the question specifically asked about jurisdiction and Court powers, which are fully addressed.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 101.5']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q6

**Q:** Does the EU AI Act apply to AI systems or AI models or both?

- **gold refs**: Article 2, Article 3, Article 51
- **base refs**: Article 2, Article 3.1, Article 51
- **branch refs**: Article 2, Article 3.1, Article 51

**base — answer (594 chars):**

```
The EU AI Act's core regime governs AI systems, defined in Article 3(1) and brought within scope by Article 2, through the risk-based tiers (prohibited practices under Article 5, high-risk systems under Article 6, and limited-risk transparency duties under Article 50). General-purpose AI models are regulated separately under Chapter V (Articles 51 to 56), are defined in Article 3(63), and carry their own provider obligations with additional duties for models posing systemic risk. The Regulation therefore applies to both AI systems and general-purpose AI models under two parallel regimes.
```

  - **ans_corr**: fail (none)
  omission_detail: The answer correctly identifies that the Act applies to both AI systems and general-purpose AI models, which is the core holding required by the question.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 2', 'Article 3.1']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (594 chars):**

```
The EU AI Act's core regime governs AI systems, defined in Article 3(1) and brought within scope by Article 2, through the risk-based tiers (prohibited practices under Article 5, high-risk systems under Article 6, and limited-risk transparency duties under Article 50). General-purpose AI models are regulated separately under Chapter V (Articles 51 to 56), are defined in Article 3(63), and carry their own provider obligations with additional duties for models posing systemic risk. The Regulation therefore applies to both AI systems and general-purpose AI models under two parallel regimes.
```

  - **ans_corr**: fail (none)
  omission_detail: The answer correctly identifies that the Act applies to both AI systems and general-purpose AI models, which is the core holding required by the question.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 2', 'Article 3.1']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q26

**Q:** If I have an AI system that is high-risk because listed in the use cases of Annex III, and change it to a different use case that is not in Annex I or III, does it stay high-risk due to its historical provenance?

- **gold refs**: Annex I, Annex III, Article 6
- **base refs**: Annex III, Annex I, Article 6.2
- **branch refs**: Annex III, Annex I, Article 6.2

**base — answer (701 chars):**

```
No, the system does not remain high-risk by historical provenance. Under Article 6(2), an AI system is high-risk because it falls within one of the use cases listed in Annex III; if the system's intended purpose is changed to a use case that does not appear in Annex III and the system is also not a safety component of, or itself, a product requiring third-party conformity assessment under Annex I legislation per Article 6(1), neither classification route is satisfied and the system is not high-risk. The classification is determined by the system's current intended purpose at the time it is placed on the market or put into service, not by a prior classification under a former intended purpose.
```

  - **ans_corr**: fail (none)
  omission_detail: The answer correctly addresses that high-risk status depends on current intended use falling within Annex III or Annex I criteria, which aligns with the gold answer's explanation of Article 6(1) and 6(2).
  - **ref_corr**: pass (cited only Article 6.2 instead of full Article 6 which contains derogation provisions)
  governing_refs: ['Annex III', 'Article 6.2']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (701 chars):**

```
No, the system does not remain high-risk by historical provenance. Under Article 6(2), an AI system is high-risk because it falls within one of the use cases listed in Annex III; if the system's intended purpose is changed to a use case that does not appear in Annex III and the system is also not a safety component of, or itself, a product requiring third-party conformity assessment under Annex I legislation per Article 6(1), neither classification route is satisfied and the system is not high-risk. The classification is determined by the system's current intended purpose at the time it is placed on the market or put into service, not by a prior classification under a former intended purpose.
```

  - **ans_corr**: fail (none)
  omission_detail: The answer correctly addresses that high-risk status depends on current intended use falling within Annex III or Annex I criteria, which aligns with the gold answer.
  - **ref_corr**: pass (incomplete citation of Article 6 (cited only 6.2, missing full Article 6 including derogation provisions))
  governing_refs: ['Annex III', 'Article 6.2']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q18

**Q:** Can the European Commission amend Annex III of the EU AI Act to add or modify use-cases classified as high-risk AI systems? Under what conditions?

- **gold refs**: Annex I, Annex III, Article 6, Article 7
- **base refs**: Article 6, Annex III
- **branch refs**: Annex III, Article 6.6, Article 6.3, Article 97, Article 7

**base — answer (1111 chars):**

```
Yes, the Commission is empowered to amend Annex III by adding new high-risk use cases or modifying existing ones through delegated acts, under the conditions set out in Article 6(7). The Commission may adopt such a delegated act only where it identifies AI systems that present a risk of harm to health, safety or fundamental rights that is equivalent to or greater than the risk posed by the use cases already listed in Annex III, and it must take into account a set of criteria including the intended purpose of the system, the extent to which it has been used or is likely to be used, the nature and amount of data processed, the extent of autonomy of action, the severity and irreversibility of harm, and whether existing Union legislation provides effective redress. The Commission must consult the Board before adopting such a delegated act. Article 6(6) separately empowers the Commission to amend the derogation conditions in Article 6(3) by adding new conditions or modifying existing ones, where there is concrete and reliable evidence of Annex III systems that do not pose a significant risk of harm.
```

  - **ans_corr**: fail (incorrect article citation (Article 6(7) instead of Article 7))
  omission_detail: The answer incorrectly cites Article 6(7) instead of Article 7 as the source of the Commission's power to amend Annex III. The answer also fails to mention that the Commission can remove high-risk AI systems from Annex III under Article 7(3).
  - **ref_corr**: fail (missing key governing provision Article 7)
  governing_refs: ['Annex III']
  missing_governing_refs: ['Article 7']
  - **cite_faith**: pass (Conflated Article 6(7) with Article 7 powers to amend Annex III; Article 6(7) only addresses deleting derogation conditions, not adding high-risk use cases to Annex III)
  - **ans_conc**: pass (none)

**branch — answer (1015 chars):**

```
Yes, the Commission is empowered to amend Annex III by adding new high-risk use cases or modifying existing ones through delegated acts, subject to specific substantive conditions. Article 6(6) grants the Commission the power to adopt delegated acts in accordance with Article 97 to amend the conditions under which an Annex III system may escape high-risk classification, but the power to amend Annex III itself, adding or removing use cases, is conferred separately by Article 7 (which is not among the citable provisions here but is the operative mechanism). Within the citable provisions, Article 6(6) empowers the Commission to adopt delegated acts to amend the derogation conditions in Article 6(3) by adding new conditions or modifying them, where there is concrete and reliable evidence that AI systems falling under Annex III do not pose a significant risk of harm to health, safety or fundamental rights. The Commission must consult the European Artificial Intelligence Board before exercising this power.
```

  - **ans_corr**: fail (Incomplete statement of Article 7 conditions and false claim that Article 7 was not provided)
  omission_detail: The answer fails to state the two cumulative conditions required under Article 7(1) for adding/modifying Annex III use-cases: (a) the AI system must be intended for use in areas already listed in Annex III, and (b) the risk must be equivalent to or greater than existing high-risk systems. It also omits the detailed assessment criteria in Article 7(2).
  - **ref_corr**: fail (cited subsections instead of full Article 6)
  governing_refs: ['Annex III', 'Article 7']
  missing_governing_refs: ['Article 6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q3

**Q:** When the intended use of an AI system is listed in Annex III of the EU AI Act, the AI system is automatically high-risk, isn't it? If not, can you explain when that is not the case?

- **gold refs**: Annex III, Article 49, Article 6
- **base refs**: Annex III, Article 6
- **branch refs**: Annex III, Article 6

**base — answer (946 chars):**

```
Not automatically. Article 6(2) provides that AI systems referred to in Annex III shall be considered high-risk, but Article 6(3) derogates from that rule where the system does not pose a significant risk of harm to health, safety or fundamental rights, including by not materially influencing the outcome of decision making, AND the system is intended to perform one of four tasks: a narrow procedural task, improving the result of a previously completed human activity, detecting decision-making patterns or deviations from prior patterns without replacing or influencing the previously completed human assessment, or a preparatory task to an assessment relevant for the Annex III use cases. However, a system that performs profiling of natural persons is always high-risk regardless of those conditions. A provider relying on this derogation must document its assessment before placing the system on the market and register under Article 6(4).
```

  - **ans_corr**: fail (incorrect article citation for registration obligation)
  - **ref_corr**: pass (none)
  governing_refs: ['Annex III', 'Article 6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (946 chars):**

```
Not automatically. Article 6(2) provides that AI systems referred to in Annex III shall be considered high-risk, but Article 6(3) derogates from that rule where the system does not pose a significant risk of harm to health, safety or fundamental rights, including by not materially influencing the outcome of decision making, AND the system is intended to perform one of four tasks: a narrow procedural task, improving the result of a previously completed human activity, detecting decision-making patterns or deviations from prior patterns without replacing or influencing the previously completed human assessment, or a preparatory task to an assessment relevant for the Annex III use cases. However, a system that performs profiling of natural persons is always high-risk regardless of those conditions. A provider relying on this derogation must document its assessment before placing the system on the market and register under Article 6(4).
```

  - **ans_corr**: fail (minor citation error)
  - **ref_corr**: pass (none)
  governing_refs: ['Annex III', 'Article 6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q15

**Q:** What obligations, if any, does the EU AI Act set in place for AI systems that interact directly with natural persons? What exceptions, if any, apply?

- **gold refs**: Article 50
- **base refs**: Article 50.1, Article 50.3
- **branch refs**: Article 50.1, Article 50.3

**base — answer (949 chars):**

```
Article 50(1) imposes the primary obligation: providers must design AI systems intended to interact directly with natural persons so that those persons are informed they are interacting with an AI system, unless this is obvious from the point of view of a reasonably well-informed, observant and circumspect natural person taking into account the circumstances and context of use. Two exceptions apply under Article 50(1): the obligation does not apply to AI systems authorised by law to detect, prevent, investigate or prosecute criminal offences, subject to appropriate safeguards for the rights and freedoms of third parties, but this exception is itself reversed where the system is available for the public to report a criminal offence. Article 50(5) further requires that the information be provided in a clear and distinguishable manner no later than the time of first interaction and in conformity with applicable accessibility requirements.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 50.1']
  - **cite_faith**: pass (fabricated provision - Article 50(5) content not in supplied text)
  - **ans_conc**: pass (none)

**branch — answer (2434 chars):**

```
The principal obligation for AI systems that interact directly with natural persons is set out in Article 50(1): the provider must design the system so that the natural person concerned is informed they are interacting with an AI system, unless this is obvious from the point of view of a reasonably well-informed, observant and circumspect person taking into account the circumstances and context of use. Article 50(2) adds that providers of AI systems generating synthetic audio, image, video or text content must ensure the outputs are marked in a machine-readable format as artificially generated or manipulated. On the deployer side, Article 50(3) requires deployers of emotion recognition or biometric categorisation systems to inform exposed natural persons of the system's operation, and Article 50(4) requires deployers of systems that generate deepfakes to disclose that the content is artificially generated or manipulated, and deployers of systems that generate or manipulate text published to inform the public on matters of public interest to disclose its artificial origin. Three categories of exception apply. First, the Article 50(1) provider disclosure duty does not apply to AI systems authorised by law to detect, prevent, investigate or prosecute criminal offences, subject to appropriate safeguards for the rights and freedoms of third parties, but this exception is itself reversed where the system is available to the public to report a criminal offence. Second, the Article 50(3) deployer duty does not apply to emotion recognition or biometric categorisation systems permitted by law to detect, prevent or investigate criminal offences, subject to appropriate safeguards and in accordance with Union law. Third, the Article 50(4) deepfake disclosure duty does not apply where the use is authorised by law for criminal-offence detection, prevention, investigation or prosecution, and where the content forms part of an evidently artistic, creative, satirical, fictional or analogous work the obligation is limited to a disclosure that does not hamper display or enjoyment of the work. The separate Article 50(4) duty on AI-generated text published on matters of public interest does not apply where the use is authorised by law for criminal-offence purposes, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for its publication.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 50.1']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q12

**Q:** What are the high-risk uses of AI systems listed under 'Administration of justice and democratic processes' cited in the EU AI Act?

- **gold refs**: Annex III, Article 6
- **base refs**: Annex III.8
- **branch refs**: Annex III.8

**base — answer (691 chars):**

```
Annex III point 8 lists two high-risk use cases under administration of justice and democratic processes. Annex III point 8(a) covers AI systems intended to be used by a judicial authority, or on its behalf, to assist in researching and interpreting facts and the law and in applying the law to a concrete set of facts, or to be used similarly in alternative dispute resolution. Annex III point 8(b) covers AI systems intended to influence the outcome of an election or referendum, or the voting behaviour of natural persons in exercising their vote, with a carve-out for tools that only organise, optimise or structure political campaigns from an administrative or logistical point of view.
```

  - **ans_corr**: pass (none)
  omission_detail: The answer fully addresses the specific question about high-risk uses under administration of justice and democratic processes by listing both use cases from Annex III point 8
  - **ref_corr**: fail (incomplete citation of framework provisions)
  governing_refs: ['Annex III.8']
  missing_governing_refs: ['Annex III', 'Article 6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (691 chars):**

```
Annex III point 8 lists two high-risk use cases under administration of justice and democratic processes. Annex III point 8(a) covers AI systems intended to be used by a judicial authority, or on its behalf, to assist in researching and interpreting facts and the law and in applying the law to a concrete set of facts, or to be used similarly in alternative dispute resolution. Annex III point 8(b) covers AI systems intended to influence the outcome of an election or referendum, or the voting behaviour of natural persons in exercising their vote, with a carve-out for tools that only organise, optimise or structure political campaigns from an administrative or logistical point of view.
```

  - **ans_corr**: pass (none)
  omission_detail: The answer fully addresses the specific question about high-risk uses under administration of justice and democratic processes by listing both use cases from Annex III point 8
  - **ref_corr**: fail (missing framework provision linking Annex III to high-risk classification)
  governing_refs: ['Annex III.8']
  missing_governing_refs: ['Article 6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q41

**Q:** Under the EU AI Act, is there a simplified way for SMEs (including startups) to provide the technical documentation for high-risk AI systems, and who must accept it for conformity assessment?

- **gold refs**: Annex IV, Article 11
- **base refs**: Article 11.1, Article 11, Annex IV, Annex IV.2
- **branch refs**: Article 11.1, Article 11, Annex IV, Annex IV.2

**base — answer (362 chars):**

```
Yes. Under Article 11(1), SMEs, including start-ups, may provide the technical documentation elements set out in Annex IV in a simplified manner, using a simplified form the Commission is required to establish for the needs of small and micro enterprises. Where an SME opts to use that form, the notified body performing the conformity assessment must accept it.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 11.1', 'Article 11', 'Annex IV']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (362 chars):**

```
Yes. Under Article 11(1), SMEs, including start-ups, may provide the technical documentation elements set out in Annex IV in a simplified manner, using a simplified form the Commission is required to establish for the needs of small and micro enterprises. Where an SME opts to use that form, the notified body performing the conformity assessment must accept it.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 11.1', 'Article 11', 'Annex IV']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q45

**Q:** What are the obligations of deployers of high-risk AI systems?

- **gold refs**: Annex III, Article 13, Article 26, Article 27
- **base refs**: Article 26, Article 27, Article 86, Annex III
- **branch refs**: Article 26, Article 27, Article 86, Annex III

**base — answer (1478 chars):**

```
Deployers of high-risk AI systems must use the system in accordance with the provider's instructions for use, assign human oversight to natural persons who have the necessary competence and training, monitor the system's operation and inform the provider where a risk is identified, suspend use where the system may present a risk within the meaning of the Regulation, report serious incidents, ensure input data relevance and representativeness to the extent they control the input data, retain automatically generated logs, and inform affected natural persons that they are subject to the use of the system (Article 26). Deployers that are bodies governed by public law, private entities providing public services, or deployers of systems under Annex III points 5(b) and (c) must perform a fundamental rights impact assessment before first use, covering the deployment process, categories of affected persons, specific risks of harm, human oversight measures and mitigation arrangements, and must notify the market surveillance authority of the results (Article 27). Where the deployer makes decisions on the basis of output from an Annex III high-risk system that produce legal effects or similarly significantly affect a person adversely in their health, safety or fundamental rights, the affected person has the right to obtain clear and meaningful explanations of the system's role in the decision-making procedure and the main elements of the decision taken (Article 86).
```

  - **ans_corr**: pass (unsupported addition (Article 86 claim not verifiable from provided text))
  omission_detail: The predicted answer covers the main deployer obligations under Articles 26 and 27, and while it adds a claim about Article 86 that is not addressed in the provided text, it does not omit any operative holdings that the question demands and the verbatim text establishes.
  - **ref_corr**: fail (missing Article 13 which defines transparency obligations referenced by deployer duties)
  governing_refs: ['Article 26', 'Article 27']
  missing_governing_refs: ['Article 13']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (1395 chars):**

```
Deployers of high-risk AI systems must use the system in accordance with the provider's instructions for use, assign human oversight to natural persons who have the necessary competence and training, monitor the system's operation and inform the provider where relevant, ensure input data relevance and representativeness to the extent the deployer controls the input data, retain automatically generated logs, inform affected natural persons that they are subject to the use of the system, and inform workers and their representatives where the system is used in the workplace (Article 26). Where the deployer is a body governed by public law, a private entity providing public services, or a deployer of systems under Annex III points 5(b) and (c), it must perform a fundamental rights impact assessment before first use covering its processes, affected categories of persons, specific risks, human oversight measures and remedial arrangements, and notify the result to the market surveillance authority (Article 27). Any affected person subject to a deployer decision based on the output of an Annex III high-risk system, where that decision produces legal effects or similarly significantly affects health, safety or fundamental rights, has the right to obtain from the deployer clear and meaningful explanations of the system's role and the main elements of the decision taken (Article 86).
```

  - **ans_corr**: pass (unsupported addition)
  omission_detail: The answer covers the main deployer obligations from Articles 26 and 27 as established in the provided text
  - **ref_corr**: fail (missing Article 13 which defines transparency obligations referenced by deployer duties)
  governing_refs: ['Article 26', 'Article 27']
  missing_governing_refs: ['Article 13']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q42

**Q:** Under the EU AI Act, must an employer inform affected workers and workers' representatives before putting into service or using a high-risk AI system in the workplace? If so, should possibly specific rules or procedures be followed to provide this information?

- **gold refs**: Article 26
- **base refs**: Article 26.7, Article 26
- **branch refs**: Article 26.7, Article 26

**base — answer (493 chars):**

```
Yes. Under Article 26(7), a deployer that is an employer must, before putting a high-risk AI system into service or using it at the workplace, inform the workers' representatives and the affected workers that they will be subject to the use of that high-risk AI system. Under Article 26(7), that information must be provided, where applicable, in accordance with the rules and procedures laid down in Union and national law and practice on the information of workers and their representatives.
```

  - **ans_corr**: pass (none)
  omission_detail: The predicted answer covers all operative holdings required by the question: the duty to inform, the timing (before putting into service or using), and the requirement to follow applicable Union and national rules and procedures.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 26.7', 'Article 26']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (493 chars):**

```
Yes. Under Article 26(7), a deployer that is an employer must, before putting a high-risk AI system into service or using it at the workplace, inform the workers' representatives and the affected workers that they will be subject to the use of that high-risk AI system. Under Article 26(7), that information must be provided, where applicable, in accordance with the rules and procedures laid down in Union and national law and practice on the information of workers and their representatives.
```

  - **ans_corr**: pass (none)
  omission_detail: The predicted answer covers all operative holdings required by the question: the duty to inform, the timing (before putting into service or using), and the requirement to follow applicable Union and national rules and procedures.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 26.7', 'Article 26']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q33

**Q:** Regarding the European Artificial Intelligence Board: (1) Who designates its members? (2) How long is the term? How many times is the term renewable? (3) must members represent stakeholder interests or act impartially/objectively? (4) what voting threshold is required to adopt the Board's rules of procedure (is a simple 50%+1 majority enough)?

- **gold refs**: Article 65, Article 67, Article 68
- **base refs**: Article 65
- **branch refs**: Article 65

**base — answer (508 chars):**

```
The European Artificial Intelligence Board (Article 65) has one representative per Member State, each serving a three-year term renewable once under Article 65(3). Under Article 65(4) each is their Member State's single contact point rather than an independent stakeholder appointee, while Article 65(7) requires the Board to safeguard the objectivity and impartiality of its activities. Its rules of procedure are adopted by a two-thirds majority under Article 65(5), so a simple majority is not sufficient.
```

  - **ans_corr**: pass (none)
  omission_detail: The answer addresses all four sub-questions: (1) Member States designate members, (2) three-year term renewable once, (3) members represent Member States not stakeholders, with Board operating objectively/impartially, (4) two-thirds majority required, simple majority insufficient.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 65']
  - **cite_faith**: pass (mischaracterized Article 65(4) as about stakeholder appointees rather than contact point designation)
  - **ans_conc**: pass (none)

**branch — answer (508 chars):**

```
The European Artificial Intelligence Board (Article 65) has one representative per Member State, each serving a three-year term renewable once under Article 65(3). Under Article 65(4) each is their Member State's single contact point rather than an independent stakeholder appointee, while Article 65(7) requires the Board to safeguard the objectivity and impartiality of its activities. Its rules of procedure are adopted by a two-thirds majority under Article 65(5), so a simple majority is not sufficient.
```

  - **ans_corr**: pass (none)
  omission_detail: The answer addresses all four sub-questions: (1) Member States designate members, (2) three-year term renewable once, (3) members represent Member States not stakeholders but Board must safeguard objectivity/impartiality, (4) two-thirds majority required, simple majority not sufficient.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 65']
  - **cite_faith**: pass (mischaracterized Article 65(4) as about stakeholder appointees rather than contact point designation)
  - **ans_conc**: pass (none)

### live_answers:la_q79

**Q:** If a hospital fine-tunes an open-weight medical language model, when does it become a provider under the EU AI Act?

- **gold refs**: Article 25, Article 4, Article 50
- **base refs**: Article 25.1.b, Article 25.1.c, Article 6
- **branch refs**: Article 25.1, Article 25.3, Article 50, Article 4, Article 6.1

**base — answer (746 chars):**

```
A hospital becomes a provider when it makes a substantial modification to a high-risk AI system already placed on the market, or when it modifies the intended purpose of a system that was not high-risk so that it becomes high-risk. Under Article 25(1)(b), making a substantial modification to a high-risk AI system that has already been placed on the market triggers provider status. Under Article 25(1)(c), modifying the intended purpose of a non-high-risk system so that it becomes high-risk under Article 6 likewise triggers provider status. A fine-tune that does not amount to a substantial modification and does not change the intended purpose into a high-risk use case does not, by itself, make the hospital a provider under the Regulation.
```

  - **ans_corr**: fail (incomplete coverage of consequential provider obligations)
  omission_detail: The answer omits the AI literacy obligation under Article 4 and the transparency obligations under Article 50 that attach when provider status is triggered, which the gold answer identifies as relevant duties
  - **ref_corr**: fail (cited sub-provisions but not full Article 25 chapeau)
  governing_refs: ['Article 25.1.b', 'Article 25.1.c']
  missing_governing_refs: ['Article 25']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (1155 chars):**

```
A hospital becomes a provider under Article 25(1) in any of three circumstances: it puts its name or trademark on a high-risk AI system already placed on the market, it makes a substantial modification to such a system so that it remains high-risk, or it modifies the intended purpose of a non-high-risk system so that it becomes high-risk. Fine-tuning an open-weight medical language model therefore triggers provider status where the fine-tuning constitutes a substantial modification to a high-risk system, or where it changes the intended purpose of a system that was not high-risk into one that is high-risk under Article 6. If the resulting system qualifies as a medical device requiring third-party conformity assessment under the Medical Device Regulation (listed in Annex I), it is high-risk under Article 6(1), and the hospital as product manufacturer assumes provider obligations under Article 25(3). Once provider status attaches, the hospital bears all provider obligations under Article 16, including the Article 50 transparency duties where the system interacts directly with natural persons, and the AI literacy obligation under Article 4.
```

  - **ans_corr**: pass (none)
  omission_detail: The predicted answer covers the key triggers for provider status under Article 25, including substantial modification and change of intended purpose, and mentions consequent obligations under Articles 4, 16, and 50, which aligns with the gold answer's key points.
  - **ref_corr**: fail (included irrelevant transparency provision)
  wrong_refs: ['Article 50']
  governing_refs: ['Article 25.1']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q30

**Q:** Under Regulation (EU) 2024/1689, as part of their supervisory role for an AI regulatory sandbox, compliance with which specific Article must the market surveillance authority verify?

- **gold refs**: Article 57, Article 74
- **base refs**: Article 57.7, Article 74
- **branch refs**: Article 78, Article 57, Article 74.14

**base — answer (948 chars):**

```
The market surveillance authority, when acting in its supervisory role within an AI regulatory sandbox, must verify compliance with the requirements and obligations set out in the Regulation as a whole, since Article 57(7) states that competent authorities provide participants with guidance on how to fulfil "the requirements and obligations set out in this Regulation" and that exit reports and written proof are taken positively into account by market surveillance authorities with a view to accelerating conformity assessment procedures. Article 57 does not single out one specific Article for verification; rather, it frames the sandbox as a controlled environment in which the national competent authority supervises participants' adherence to the Regulation's applicable requirements generally, and Article 74 designates the market surveillance authorities with full investigation and corrective-measure powers to enforce those requirements.
```

  - **ans_corr**: fail (Failed to identify Article 57 as the specific article for compliance verification)
  omission_detail: The question asks which specific Article must the market surveillance authority verify compliance with. The gold answer indicates Article 57 is the specific article, but the predicted answer states there is no single specific Article and instead describes general compliance with the Regulation as a whole, failing to directly identify Article 57 as the specific article referenced in the supervisory role context.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 57.7', 'Article 74']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (1075 chars):**

```
As part of their supervisory role for an AI regulatory sandbox, the market surveillance authority must verify compliance with Article 78, which requires market surveillance authorities to respect the confidentiality of information and data obtained in carrying out their tasks, protecting in particular intellectual property rights, confidential business information and trade secrets including source code, the effective implementation of the Regulation, public and national security interests, and the integrity of criminal or administrative proceedings. Article 74(14) confirms that any information or documentation obtained by market surveillance authorities shall be treated in accordance with the confidentiality obligations set out in Article 78. Article 57 establishes the sandbox framework within which the market surveillance authority operates, providing that exit reports and written proof from the national competent authority shall be taken positively into account by market surveillance authorities with a view to accelerating conformity assessment procedures.
```

  - **ans_corr**: fail (Misidentified the specific Article - claimed Article 78 instead of Article 57)
  omission_detail: The question asks which specific Article the market surveillance authority must verify compliance with in their supervisory role for an AI regulatory sandbox. The gold answer indicates this is Article 57 (establishing sandbox requirements). The predicted answer incorrectly identifies Article 78 (confidentiality) as the article to verify compliance with, rather than Article 57 which establishes the substantive sandbox requirements that must be supervised.
  - **ref_corr**: fail (incomplete citation of Article 74)
  governing_refs: ['Article 57']
  missing_governing_refs: ['Article 74']
  - **cite_faith**: fail (Wrong article identified as the one requiring verification - Article 78 is about confidentiality obligations, not what must be verified for sandbox compliance)
  - **ans_conc**: fail (unrequested elaboration on related but unasked provisions)

### live_answers:la_q25

**Q:** Can an operator that is not a provider according to the EU AI Act, for example a deployer, take actions on a given high-risk AI system such that it can be effectively seen as a provider by the authorities? If yes, what kind of action would result in such an outcome?

- **gold refs**: Annex III, Article 25, Article 26, Article 6
- **base refs**: Article 25.1, Article 25, Article 16
- **branch refs**: Article 25.1, Article 25, Article 16

**base — answer (785 chars):**

```
Yes. Under Article 25(1), a distributor, importer, deployer or other third party is deemed to be the provider of a high-risk AI system, and takes on the provider obligations in Article 16, in any of three cases. First, if it puts its name or trademark on a high-risk AI system already placed on the market (Article 25(1)(a)). Second, if it makes a substantial modification to a high-risk AI system that remains high-risk (Article 25(1)(b)). Third, if it modifies the intended purpose of an AI system, including a general-purpose AI system, so that it becomes high-risk (Article 25(1)(c)). In each of these three cases the operator assumes the provider obligations in Article 16, and the initial provider is no longer considered the provider of that specific system under Article 25(2).
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 25.1', 'Article 25']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (785 chars):**

```
Yes. Under Article 25(1), a distributor, importer, deployer or other third party is deemed to be the provider of a high-risk AI system, and takes on the provider obligations in Article 16, in any of three cases. First, if it puts its name or trademark on a high-risk AI system already placed on the market (Article 25(1)(a)). Second, if it makes a substantial modification to a high-risk AI system that remains high-risk (Article 25(1)(b)). Third, if it modifies the intended purpose of an AI system, including a general-purpose AI system, so that it becomes high-risk (Article 25(1)(c)). In each of these three cases the operator assumes the provider obligations in Article 16, and the initial provider is no longer considered the provider of that specific system under Article 25(2).
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 25.1', 'Article 25']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q39

**Q:** Under the EU AI Act, what transparency obligation applies to deployers when they use an AI system to generate or manipulate text for the purpose of informing the public on matters of public interest, and what are the two exceptions where this obligation does not apply?

- **gold refs**: Article 50
- **base refs**: Article 50.4, Article 50
- **branch refs**: Article 50.4, Article 50

**base — answer (600 chars):**

```
Under Article 50(4), a deployer that uses an AI system to generate or manipulate text published to inform the public on matters of public interest must disclose that the text has been artificially generated or manipulated. Under Article 50(4), that disclosure duty does not apply in two cases: first, where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences; and second, where the AI-generated content has undergone a process of human review or editorial control and a natural or legal person holds editorial responsibility for the publication of the content.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 50.4', 'Article 50']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (600 chars):**

```
Under Article 50(4), a deployer that uses an AI system to generate or manipulate text published to inform the public on matters of public interest must disclose that the text has been artificially generated or manipulated. Under Article 50(4), that disclosure duty does not apply in two cases: first, where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences; and second, where the AI-generated content has undergone a process of human review or editorial control and a natural or legal person holds editorial responsibility for the publication of the content.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 50.4', 'Article 50']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q66

**Q:** Under the EU AI Act, is an AI system used to dispatch and triage emergency-room patients high-risk?

- **gold refs**: Annex III, Article 5, Article 6
- **base refs**: Article 5, Article 6.2, Annex III.5.d
- **branch refs**: Article 5, Article 6.2, Annex III.5.d

**base — answer (485 chars):**

```
High-risk. An AI system used to dispatch and triage emergency-room patients falls squarely within Annex III(5)(d), which lists AI systems intended to evaluate and classify emergency calls, to dispatch or establish priority in the dispatching of emergency first response services, and emergency healthcare patient triage systems; Article 6(2) classifies all Annex III systems as high-risk. No prohibited practice under Article 5 is engaged by a triage or dispatch function of this kind.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: fail (incomplete citation of Article 6)
  governing_refs: ['Article 6.2', 'Annex III.5.d']
  missing_governing_refs: ['Article 6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (468 chars):**

```
High-risk. An AI system used to dispatch and triage emergency-room patients falls within Annex III(5)(d), which covers AI systems intended to evaluate and classify emergency calls, to dispatch or establish priority in the dispatching of emergency first response services, and emergency healthcare patient triage systems; Article 6(2) classifies all Annex III systems as high-risk. No prohibited practice under Article 5 is engaged by this use case on its stated facts.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (incomplete citation of Article 6 derogation provisions)
  governing_refs: ['Article 6.2', 'Annex III.5.d']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q40

**Q:** Under the EU AI Act, when a high-risk AI system is found to conform with the requirements, what information must the Union technical documentation assessment certificate contain?

- **gold refs**: Annex IV, Article 11
- **base refs**: Annex VII
- **branch refs**: Annex VII

**base — answer (436 chars):**

```
Under Annex VII point 4.6, where the notified body finds the high-risk AI system conforms with the Chapter III Section 2 requirements, it issues a Union technical documentation assessment certificate. Per Annex VII point 4.6, that certificate must indicate the name and address of the provider, the conclusions of the examination, the conditions (if any) for its validity, and the data necessary for the identification of the AI system.
```

  - **ans_corr**: fail (Cites provisions not in provided text; fails to address relevant Annex IV content)
  omission_detail: The question asks about certificate contents and the provided text contains Annex IV and Article 11 about technical documentation requirements. The predicted answer references Annex VII point 4.6 which is not in the provided text, and fails to address the actual content from Annex IV that describes what technical documentation must contain.
  - **ref_corr**: pass (none)
  governing_refs: ['Annex VII']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (436 chars):**

```
Under Annex VII point 4.6, where the notified body finds the high-risk AI system conforms with the Chapter III Section 2 requirements, it issues a Union technical documentation assessment certificate. Per Annex VII point 4.6, that certificate must indicate the name and address of the provider, the conclusions of the examination, the conditions (if any) for its validity, and the data necessary for the identification of the AI system.
```

  - **ans_corr**: fail (Cites provisions not in provided text; fails to address relevant Annex IV content)
  omission_detail: The question asks about certificate contents and the provided text contains Annex IV detailing technical documentation requirements. The predicted answer references Annex VII point 4.6 which is not in the provided text, and fails to address the Annex IV content that is actually provided.
  - **ref_corr**: pass (none)
  governing_refs: ['Annex VII']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q4

**Q:** I have a medical device that has an AI system as a safety component. The medical device is classified "medium-risk" and undergoes a 3rd party conformity assessment. Is the AI system "medium risk" too? If yes, why? If not, why not?

- **gold refs**: Annex I, Article 43, Article 6
- **base refs**: Article 6.1, Article 43.3, Annex I
- **branch refs**: Article 6.1, Article 43.3, Annex I

**base — answer (1106 chars):**

```
The AI system is classified as high-risk under the EU AI Act, not "medium-risk." The Regulation does not use a "medium-risk" category. Under Article 6(1), an AI system is high-risk where both conditions are met: it is a safety component of a product covered by the Union harmonisation legislation listed in Annex I, and that product is required to undergo a third-party conformity assessment. The Medical Devices Regulation is listed in Annex I, and the facts state the device undergoes third-party conformity assessment, so both conditions are satisfied and the AI system is high-risk regardless of the device's own risk class under sectoral law. As to conformity assessment, Article 43(3) provides that for high-risk AI systems covered by the legislation in Section A of Annex I, the provider follows the relevant conformity assessment procedure required under that sectoral legislation, and the Chapter III Section 2 requirements of the AI Act form part of that same assessment. The result is a single integrated procedure conducted by the medical-device notified body, not a separate AI Act assessment.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 6.1', 'Annex I']
  - **cite_faith**: pass (none)
  - **ans_conc**: fail (unrequested conformity assessment procedure details)

**branch — answer (980 chars):**

```
The AI system is high-risk, not "medium-risk." The EU AI Act does not use a "medium-risk" category. Under Article 6(1), an AI system is classified as high-risk where it is intended to be used as a safety component of a product covered by the Union harmonisation legislation listed in Annex I and that product is required to undergo a third-party conformity assessment. Medical devices are listed in Annex I, so an AI safety component of a medical device that undergoes third-party conformity assessment is high-risk regardless of the device's own risk class under sectoral legislation. As to conformity assessment, Article 43(3) provides that for high-risk AI systems covered by Section A of Annex I, the provider follows the relevant conformity assessment procedure required under that sectoral legislation, and the Chapter III Section 2 requirements of the AI Act form part of that same assessment, yielding a single integrated procedure conducted by the sectoral notified body.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 6.1', 'Annex I']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q68

**Q:** Are AI systems used solely for scientific biomedical research and not placed on the market subject to the EU AI Act?

- **gold refs**: Article 2
- **base refs**: Article 2.6, Article 2.1
- **branch refs**: Article 2.6

**base — answer (615 chars):**

```
AI systems developed and put into service for the sole purpose of scientific research and development are not subject to the EU AI Act, as Article 2(6) explicitly excludes them from the Regulation's scope. This exclusion covers AI systems used solely for scientific biomedical research that are not placed on the market or put into service for any purpose beyond that research. The exclusion ceases to apply if the system is subsequently placed on the market or put into service for a non-research purpose, at which point the full Regulation applies according to the system's risk classification under Article 2(1).
```

  - **ans_corr**: pass (minor imprecision on risk classification reference)
  omission_detail: The answer addresses the core question about exclusion from scope and the conditions under which the Act would apply
  - **ref_corr**: pass (none)
  governing_refs: ['Article 2.6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (664 chars):**

```
Article 2(6) excludes from the Regulation AI systems or AI models specifically developed and put into service for the sole purpose of scientific research and development. An AI system used solely for scientific biomedical research that is not placed on the market or put into service for any purpose beyond that research therefore falls outside the scope of the EU AI Act. The exclusion requires that the system be developed and used exclusively for scientific research and development; if the system were subsequently placed on the market or put into service for a non-research purpose, the exclusion would no longer apply and the full Regulation would govern it.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 2.6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q56

**Q:** What's the best restaurant in Rome?

- **gold refs**: (none)
- **base refs**: (none)
- **branch refs**: (none)

**base — answer (403 chars):**

```
Rome has many incredible restaurants, but one consistently top-rated option is Roscioli, known for its exceptional Roman cuisine, high-quality ingredients, and a fantastic wine selection. For a more traditional experience, Trattoria Da Enzo al 29 in Trastevere is also highly recommended. Both offer authentic flavors in a charming setting. Would you like recommendations for a specific type of cuisine?
```

  - **ans_corr**: fail (Off-topic response - answered non-EU AI Act question instead of redirecting to regulatory scope)
  omission_detail: The question is outside the scope of the EU AI Act. The answer should have indicated that this assistant only answers EU AI Act questions, as shown in the gold answer which states 'This assistant answers EU AI Act questions only (Regulation 2024/1689).'
  - **ref_corr**: pass (out of scope question - not related to EU AI Act)
  - **cite_faith**: pass (off-topic response with no EU AI Act citations)
  - **ans_conc**: fail (entirely off-topic - question unrelated to EU AI Act)

**branch — answer (280 chars):**

```
One of the most highly praised restaurants in Rome is Roscioli, a historic deli‑restaurant near Campo de’ Fiori that blends traditional Roman dishes (like carbonara and cacio e pepe) with a superb wine list and upscale service. Reservations are recommended, especially for dinner.
```

  - **ans_corr**: fail (Off-topic response to out-of-scope question)
  omission_detail: The question is outside the scope of the EU AI Act. The verbatim text indicates this assistant answers EU AI Act questions only and suggests asking regulatory questions instead. The predicted answer fails to acknowledge this scope limitation and instead provides restaurant recommendations.
  - **ref_corr**: pass (out of scope question - not related to EU AI Act)
  - **cite_faith**: pass (off-topic question with no EU AI Act citations)
  - **ans_conc**: fail (entirely off-topic - question unrelated to EU AI Act)

### live_answers:la_q24

**Q:** Are AI systems that fall under one of the areas of Annex III, but not falling within a use-case within such areas, considered high-risk?

- **gold refs**: Annex III, Article 6
- **base refs**: Annex III, Article 6.2, Article 6.3
- **branch refs**: Annex III, Article 6.2, Article 6.3

**base — answer (945 chars):**

```
Not necessarily. Article 6(2) classifies as high-risk only AI systems "referred to in Annex III," meaning those that fall within one of the specific use cases enumerated under each of the eight areas. An AI system that operates in a domain covered by one of the eight Annex III areas but does not match any of the particular use cases listed within that area is not classified as high-risk under Article 6(2). Even where a system does fall within a listed use case, Article 6(3) provides that it is not high-risk where it does not pose a significant risk of harm to health, safety or fundamental rights and performs one of four tasks: a narrow procedural task, improving the result of a previously completed human activity, detecting decision-making patterns or deviations without replacing or influencing the human assessment, or a preparatory task, unless the system performs profiling of natural persons, in which case it is always high-risk.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Annex III', 'Article 6.2', 'Article 6.3']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (949 chars):**

```
Not necessarily. Article 6(2) classifies as high-risk only AI systems "referred to in Annex III," meaning those that match a specific use case listed within one of the eight areas. An AI system that operates in a domain covered by one of the eight Annex III areas but does not fall within any of the particular use cases described therein is not classified as high-risk under Article 6(2). Additionally, even a system that does fall within an Annex III use case may escape high-risk classification under Article 6(3) where it does not pose a significant risk of harm to health, safety or fundamental rights and performs one of four tasks: a narrow procedural task, improving the result of a previously completed human activity, detecting decision-making patterns or deviations without replacing or influencing the human assessment, or a preparatory task, unless the system performs profiling of natural persons, in which case it is always high-risk.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Annex III', 'Article 6.2', 'Article 6.3']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q85

**Q:** How does the EU AI Act interact with the Medical Device Regulation for AI medical-device software - which conformity route and timeline applies?

- **gold refs**: Annex I, Annex III, Annex VI, Annex VII, Article 43, Article 6
- **base refs**: Article 6.1, Annex I, Article 43.3
- **branch refs**: Article 6.1, Article 43.3, Annex I

**base — answer (872 chars):**

```
AI software that is itself a medical device, or that serves as a safety component of one, is classified high-risk under Article 6(1) where the device must undergo third-party conformity assessment under the Medical Device Regulation (listed at point 11 of Annex I, Section A). Under Article 43(3), the provider follows the conformity assessment procedure required by the Medical Device Regulation rather than the internal-control route, and the Chapter III Section 2 requirements of the EU AI Act are integrated into that single sectoral assessment carried out by the notified body designated under that legislation. The result is one procedure and one CE marking covering both regimes. The Medical Device Regulation itself falls outside the scope of this answer, so its specific procedural steps and timelines are governed by that instrument rather than by the EU AI Act.
```

  - **ans_corr**: pass (none)
  omission_detail: The answer correctly identifies the conformity route under Article 43(3) and the integration mechanism, which are the key operative holdings demanded by the question.
  - **ref_corr**: fail (cited subsection instead of full article)
  governing_refs: ['Article 6.1', 'Annex I', 'Article 43.3']
  missing_governing_refs: ['Article 43']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (1266 chars):**

```
AI software that is itself a medical device, or is a safety component of one, is classified as high-risk under Article 6(1) where the Medical Device Regulation requires that product to undergo a third-party conformity assessment, which it does for devices in risk class IIa and above. The conformity route is set by Article 43(3): the provider follows the Medical Device Regulation's own notified-body conformity assessment procedure, and the Chapter III Section 2 requirements of the AI Act (risk management, data governance, technical documentation, logging, transparency, human oversight, accuracy and cybersecurity) form part of that single assessment, yielding one CE marking. The notified body conducting the MDR assessment is entitled to control compliance with those AI Act requirements provided it meets the competence conditions in Article 43(3). The Medical Device Regulation itself falls outside the scope of this answer, but Annex I lists it as Union harmonisation legislation triggering the Article 6(1) route. As to timeline, the obligations for high-risk AI systems under the AI Act apply from 2 August 2026, so providers of AI medical-device software must integrate the AI Act requirements into their MDR conformity assessment from that date onward.
```

  - **ans_corr**: fail (minor unsupported details)
  omission_detail: The answer correctly identifies the Article 43(3) integration mechanism and that MDR is in Annex I, which are the key operative holdings demanded by the question.
  - **ref_corr**: fail (missing conformity assessment procedure annexes)
  governing_refs: ['Article 6.1', 'Article 43.3', 'Annex I']
  missing_governing_refs: ['Annex VI', 'Annex VII']
  - **cite_faith**: pass (none)
  - **ans_conc**: fail (minor meta-commentary about scope)

### live_answers:la_q38

**Q:** Under the EU AI Act, what is an "AI regulatory sandbox"? Provide the definition elements (what it is, who sets it up, for whom it is intended, to do what, for how long).

- **gold refs**: Article 57, Article 62
- **base refs**: Article 3.55, Article 57, Article 1
- **branch refs**: Article 3.55, Article 57, Article 2

**base — answer (315 chars):**

```
A controlled framework set up by a competent authority which offers providers or prospective providers of AI systems the possibility to develop, train, validate and test, where appropriate in real-world conditions, an innovative AI system, pursuant to a sandbox plan for a limited time under regulatory supervision.
```

  - **ans_corr**: fail (incomplete coverage of intended beneficiaries)
  omission_detail: The answer omits that SMEs and start-ups have priority access to AI regulatory sandboxes (Article 62(1)(a)), which was specifically asked about ('for whom it is intended')
  - **ref_corr**: fail (missed Article 62 on SME priority access)
  governing_refs: ['Article 3.55', 'Article 57']
  missing_governing_refs: ['Article 62']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (315 chars):**

```
A controlled framework set up by a competent authority which offers providers or prospective providers of AI systems the possibility to develop, train, validate and test, where appropriate in real-world conditions, an innovative AI system, pursuant to a sandbox plan for a limited time under regulatory supervision.
```

  - **ans_corr**: fail (incomplete coverage of intended beneficiaries and establishment requirements)
  omission_detail: The answer omits that SMEs and start-ups have priority access to AI regulatory sandboxes (Article 62), which was specifically asked about ('for whom it is intended'). It also omits that the sandbox must be established at national level by Member States and operational by 2 August 2026.
  - **ref_corr**: fail (included irrelevant scope article, missed SME priority access provision)
  wrong_refs: ['Article 2']
  governing_refs: ['Article 3.55', 'Article 57']
  missing_governing_refs: ['Article 62']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q9

**Q:** What documentation does a provider of a high-risk AI system needs to keep available for the national competent authorities, and for how long?

- **gold refs**: Annex IV, Article 11, Article 17, Article 18, Article 47
- **base refs**: Article 18, Article 11, Article 17, Article 47, Article 19
- **branch refs**: Article 18, Article 11, Article 17, Article 47, Article 19

**base — answer (606 chars):**

```
Under Article 18, for ten years after the high-risk AI system is placed on the market or put into service, the provider must keep at the disposal of the national competent authorities the technical documentation (Article 11), the quality-management-system documentation (Article 17), the documentation of any changes approved by notified bodies, the decisions and other documents issued by notified bodies, and the EU declaration of conformity (Article 47). Separately, under Article 19 the automatically generated logs must be kept for a period appropriate to the intended purpose, of at least six months.
```

  - **ans_corr**: pass (unsupported claim about Article 19 logs)
  omission_detail: The answer covers the main documentation requirements and retention period as established in the provided text
  - **ref_corr**: fail (missing Annex IV which specifies technical documentation contents)
  governing_refs: ['Article 18', 'Article 11', 'Article 17', 'Article 47']
  missing_governing_refs: ['Annex IV']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (606 chars):**

```
Under Article 18, for ten years after the high-risk AI system is placed on the market or put into service, the provider must keep at the disposal of the national competent authorities the technical documentation (Article 11), the quality-management-system documentation (Article 17), the documentation of any changes approved by notified bodies, the decisions and other documents issued by notified bodies, and the EU declaration of conformity (Article 47). Separately, under Article 19 the automatically generated logs must be kept for a period appropriate to the intended purpose, of at least six months.
```

  - **ans_corr**: pass (unsupported claim about Article 19 logs)
  omission_detail: The answer covers the main documentation requirements and retention period as established in the provided text
  - **ref_corr**: fail (missing Annex IV which specifies technical documentation contents)
  governing_refs: ['Article 18', 'Article 11', 'Article 17', 'Article 47']
  missing_governing_refs: ['Annex IV']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q91

**Q:** What are the transparency rules for a Very Large Online Platform's content-moderation AI?

- **gold refs**: Article 50
- **base refs**: (none)
- **branch refs**: (none)

**base — answer (209 chars):**

```
This question is about the Digital Services Act (DSA), not the EU AI Act (Regulation 2024/1689). This assistant only covers EU AI Act questions; consult the Digital Services Act (DSA) for the applicable rules.
```

  - **ans_corr**: fail (Incorrect refusal to answer - wrongly claims question is outside scope)
  omission_detail: The answer completely fails to address the transparency rules under Article 50 of the EU AI Act that apply to content-moderation AI, including requirements for informing users of AI interaction (50(1)), machine-readable marking of synthetic content (50(2)), emotion recognition disclosure (50(3)), and deepfake disclosure (50(4)).
  - **ref_corr**: fail (no citations provided)
  missing_governing_refs: ['Article 50']
  - **cite_faith**: pass (none - appropriate scope clarification with no citations to verify)
  - **ans_conc**: pass (none)

**branch — answer (209 chars):**

```
This question is about the Digital Services Act (DSA), not the EU AI Act (Regulation 2024/1689). This assistant only covers EU AI Act questions; consult the Digital Services Act (DSA) for the applicable rules.
```

  - **ans_corr**: fail (Incorrect refusal to answer - wrongly claims question is outside scope)
  omission_detail: The answer completely fails to address the transparency obligations under Article 50 that apply to content-moderation AI, including: informing users of AI interaction (50(1)), machine-readable marking of synthetic content (50(2)), emotion recognition/biometric system disclosure (50(3)), and deepfake disclosure requirements (50(4)).
  - **ref_corr**: fail (no citations provided)
  missing_governing_refs: ['Article 50']
  - **cite_faith**: pass (none - appropriate scope clarification with no citations to verify)
  - **ans_conc**: pass (none)

### live_answers:la_q23

**Q:** Does "systemic risk" apply to AI systems or general purpose AI models or both?

- **gold refs**: Annex XIII, Article 51, Article 55
- **base refs**: Article 55, Article 51
- **branch refs**: Article 55, Article 53, Article 51

**base — answer (654 chars):**

```
Systemic risk applies exclusively to general-purpose AI models, not to AI systems as such. Article 51 classifies a general-purpose AI model as having systemic risk where it has high-impact capabilities, presumed when cumulative training compute exceeds 10²⁵ floating-point operations, or where the Commission so designates it. Article 55 then imposes additional obligations on providers of such models, including model evaluation with adversarial testing, assessment and mitigation of possible systemic risks at Union level, serious incident reporting to the AI Office, and adequate cybersecurity protection for the model and its physical infrastructure.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: fail (missing Annex XIII which provides criteria for systemic risk classification)
  governing_refs: ['Article 55', 'Article 51']
  missing_governing_refs: ['Annex XIII']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (1293 chars):**

```
Under Article 53, GPAI providers must maintain Annex XI documentation, supply downstream-provider information, and publish a training-data summary; the Article 53(2) carve-out means each documentation obligation does not apply to free and open-source models below the systemic threshold. Under Article 51, a GPAI model has systemic risk when cumulative training compute exceeds 10²⁵ FLOPs (10^25); providers must notify the Commission within two weeks of meeting the threshold. Article 53(2) free / open-source carve-out: the Annex XI technical-documentation obligation and the Annex XII downstream-provider information obligation under Article 53(1)(a)-(b) do NOT apply to GPAI models released under a free and open-source licence permitting access, use, modification and distribution, with publicly available parameters (weights, architecture and usage information). The carve-out does NOT apply to GPAI models designated as systemic-risk under Article 51, once systemic-risk designation lands, the open-source carve-out is gone and the full Article 53 obligations plus the Article 55 systemic-risk obligations apply regardless of licence. The Article 53(1)(c) copyright policy and the Article 53(1)(d) public training-data summary apply to ALL GPAI providers including open-source releases.
```

  - **ans_corr**: fail (fails to answer the actual question asked)
  omission_detail: The answer fails to directly address the core question: whether systemic risk applies to AI systems, general-purpose AI models, or both. The verbatim text clearly shows systemic risk applies specifically to general-purpose AI models (Article 51: 'A general-purpose AI model shall be classified as a general-purpose AI model with systemic risk'), but the predicted answer never explicitly states this distinction.
  - **ref_corr**: fail (missing Annex XIII)
  governing_refs: ['Article 55', 'Article 51']
  missing_governing_refs: ['Annex XIII']
  - **cite_faith**: pass (none)
  - **ans_conc**: fail (extensive unrequested detail on open-source carve-outs and Article 53 obligations)

### live_answers:la_q28

**Q:** According to Article 1, what is the objective of the EU AI Act?

- **gold refs**: Article 1
- **base refs**: Article 1.2
- **branch refs**: Article 1

**base — answer (956 chars):**

```
Article 1 states that the purpose of the Regulation is to improve the functioning of the internal market and promote the uptake of human-centric and trustworthy AI, while ensuring a high level of protection of health, safety, and fundamental rights enshrined in the Charter, including democracy, the rule of law and environmental protection, against the harmful effects of AI systems in the Union, and supporting innovation. To that end, Article 1(2) lays down harmonised rules for the placing on the market, putting into service and use of AI systems, prohibitions of certain AI practices, specific requirements for high-risk AI systems and obligations for their operators, harmonised transparency rules for certain AI systems, harmonised rules for placing general-purpose AI models on the market, rules on market monitoring, surveillance, governance and enforcement, and measures to support innovation with a particular focus on SMEs including start-ups.
```

  - **ans_corr**: pass (none)
  omission_detail: The answer comprehensively covers all elements of Article 1 as stated in the verbatim text
  - **ref_corr**: fail (cited scope provisions instead of purpose/objective statement)
  missing_governing_refs: ['Article 1']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (304 chars):**

```
Lays down harmonised rules for placing on the market, putting into service, and use of AI systems in the Union; sets prohibitions, high-risk requirements, transparency obligations, GPAI rules, and innovation-support measures to ensure a high level of protection of health, safety, and fundamental rights.
```

  - **ans_corr**: fail (partial omission of overarching objectives)
  omission_detail: The answer omits the overarching purpose stated in Article 1(1) of improving the functioning of the internal market and promoting the uptake of human-centric and trustworthy AI, as well as supporting innovation and protecting democracy, rule of law, and environmental protection.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 1']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q81

**Q:** Classify the EU AI Act risk tier of an AI ambient scribe that only transcribes doctor-patient consultations and performs no diagnosis or decision-making.

- **gold refs**: Annex III, Article 6
- **base refs**: Article 50, Article 6.1, Annex I
- **branch refs**: Article 50, Article 6.1, Article 42, Article 49

**base — answer (1150 chars):**

```
Not high-risk, provided the system's intended purpose is limited to transcription with no diagnostic, triage or decision-making function. A pure ambient scribe does not fall within any Annex III use case because it neither evaluates eligibility for healthcare services on behalf of a public authority nor performs emergency patient triage, and it is not itself a medical device requiring third-party conformity assessment under the Medical Devices Regulation listed in Annex I. Even if the transcription were characterised as a preparatory task to a clinical assessment, Article 6(3) would apply to exclude it from high-risk classification, because a system that only transcribes does not materially influence the outcome of decision making, does not profile natural persons, and performs a preparatory task to a previously completed human activity. The provider relying on that derogation must document the assessment before placing the system on the market under Article 6(3). The system therefore falls in the minimal-risk tier, subject only to the general transparency obligation under Article 50 where it interacts directly with natural persons.
```

  - **ans_corr**: fail (minor mischaracterization of Article 6(3) condition)
  omission_detail: The answer correctly identifies that the system would not be high-risk under Annex III and explains the Article 6(3) derogation mechanism, which addresses the core question about risk tier classification.
  - **ref_corr**: fail (missed Annex III and Article 6(2)-(3) derogation analysis)
  wrong_refs: ['Article 50']
  governing_refs: ['Article 6.1']
  missing_governing_refs: ['Annex III', 'Article 6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (559 chars):**

```
Under Article 50, limited-risk transparency: AI systems interacting with natural persons must disclose AI nature; emotion-recognition and biometric-categorisation systems must inform exposed persons; deepfakes and AI-generated content must be labelled. Classifies an AI system as high-risk on two routes. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation.
```

  - **ans_corr**: fail (Failed to answer the classification question - discussed general framework without applying it to the specific system)
  omission_detail: The answer fails to classify the specific AI ambient scribe system as requested. It does not address that a pure transcription tool performing no diagnosis or decision-making does not fall within Annex III high-risk categories, nor does it mention the Article 6(3) derogation for narrow procedural tasks. The answer never provides the actual risk tier classification for the ambient scribe.
  - **ref_corr**: fail (missing key provisions for risk classification analysis)
  wrong_refs: ['Article 42']
  governing_refs: ['Article 6.1']
  missing_governing_refs: ['Annex III', 'Article 6']
  - **cite_faith**: fail (irrelevant citations and incomplete classification analysis)
  - **ans_conc**: fail (incomplete classification analysis with unrequested Annex I detail)

### live_answers:la_q51

**Q:** What should my company do to comply with AI rules in Europe?

- **gold refs**: Article 1, Article 10, Article 8, Article 9
- **base refs**: Article 1, Article 42, Article 8
- **branch refs**: Article 42, Article 55, Article 16

**base — answer (827 chars):**

```
Adds two further presumptions of conformity beyond Articles 40-41: Article 42(1), high-risk AI systems trained and tested on data reflecting the specific geographical, behavioural, contextual, or functional setting in which they are intended to be used are presumed to comply with the relevant data-governance requirements of Article 10(4); Article 42(2), high-risk AI systems certified or for which a statement of conformity has been issued under a cybersecurity scheme under Regulation (EU) 2019/881 (the Cybersecurity Act) and whose references are published in the Official Journal are presumed to comply with the cybersecurity requirements of Article 15 to the extent the cybersecurity certificate or statement covers those requirements. Article 1 lays down harmonised rules for placing on the market, putting into service.
```

  - **ans_corr**: fail (Incomplete and tangential response citing unverified articles while omitting core compliance obligations)
  omission_detail: The answer fails to provide actionable compliance guidance such as classifying AI systems by risk tier, implementing risk management systems per Article 9, meeting data governance requirements per Article 10, and complying with high-risk system requirements per Article 8 - all of which are established in the verbatim text and directly relevant to the question about compliance.
  - **ref_corr**: fail (missing key compliance requirements for high-risk AI systems)
  governing_refs: ['Article 1', 'Article 8']
  missing_governing_refs: ['Article 9', 'Article 10']
  - **cite_faith**: fail (cited Article 8 but never discussed its content about compliance requirements)
  - **ans_conc**: fail (answer discusses Article 42 presumptions instead of addressing general compliance steps)

**branch — answer (1628 chars):**

```
Adds two further presumptions of conformity beyond Articles 40-41: Article 42(1), high-risk AI systems trained and tested on data reflecting the specific geographical, behavioural, contextual, or functional setting in which they are intended to be used are presumed to comply with the relevant data-governance requirements of Article 10(4); Article 42(2), high-risk AI systems certified or for which a statement of conformity has been issued under a cybersecurity scheme under Regulation (EU) 2019/881 (the Cybersecurity Act) and whose references are published in the Official Journal are presumed to comply with the cybersecurity requirements of Article 15 to the extent the cybersecurity certificate or statement covers those requirements. Article 55 adds four obligations on top of Article 53 for GPAI providers with systemic risk: (a) model evaluation in accordance with standardised protocols and tools reflecting the state of the art, including conducting and documenting adversarial testing to identify and mitigate systemic risks; (b) assess and mitigate possible systemic risks at Union level, including their sources, that may stem from development, market-placement, or use of the model; (c) keep track of, document, and report without undue delay to the AI Office (and national competent authorities where appropriate) information about serious incidents and possible corrective measures; (d) ensure an adequate level of cybersecurity protection for both the model AND its physical infrastructure. Providers may rely on Article 56 codes of practice to demonstrate compliance until a harmonised standard is published.
```

  - **ans_corr**: fail (Off-topic response citing provisions not in provided text while ignoring relevant provisions that are present)
  omission_detail: The answer fails to address the core compliance framework established in the provided text: Article 1's scope (prohibited practices, high-risk requirements, transparency rules), Article 8's requirement for high-risk AI systems to comply with Section requirements, Article 9's risk management system requirements, and Article 10's data governance requirements. Instead, it discusses articles not present in the provided text.
  - **ref_corr**: fail (missing foundational compliance framework articles)
  governing_refs: ['Article 16']
  missing_governing_refs: ['Article 1', 'Article 8', 'Article 9', 'Article 10']
  - **cite_faith**: fail (Answer cites Article 16 in verbatim text but never discusses it in the prose; answer fails to address the actual question about general compliance steps)
  - **ans_conc**: fail (answer addresses unrelated technical provisions instead of general compliance guidance)

### live_answers:la_q54

**Q:** Tell me about emotion recognition rules

- **gold refs**: Article 5
- **base refs**: Article 5.1.f
- **branch refs**: Article 5.1.f

**base — answer (850 chars):**

```
Under Article 5.1.f, emotion recognition in the workplace and in educational institutions is prohibited, including monitoring employees or call-centre agents, with a narrow medical/safety carve-out for systems placed on the market for therapeutic or accident-prevention purposes. Real-time remote biometric identification by law enforcement is prohibited under Article 5 save for narrow, exhaustively-listed law-enforcement exceptions that each require prior judicial or administrative authorisation; under Article 5(5) Member States may enable those exceptions in national law and may set stricter national rules. Article 5(1)(c) carve-out: the social-scoring prohibition does not affect lawful evaluation practices of natural persons that are carried out for a specific purpose in accordance with Union and national law (Recital 31 final sentence).
```

  - **ans_corr**: pass (minor unsupported elaboration)
  omission_detail: The answer covers the main prohibition under Article 5(1)(f) regarding emotion recognition in workplace and educational institutions with the medical/safety exception, which addresses the core question.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 5.1.f']
  - **cite_faith**: pass (none)
  - **ans_conc**: fail (unrequested topics on biometric identification and social scoring)

**branch — answer (1242 chars):**

```
Under Article 5.1.f, emotion recognition in the workplace and in educational institutions is prohibited, including monitoring employees or call-centre agents, with a narrow medical/safety carve-out for systems placed on the market for therapeutic or accident-prevention purposes. Transparency obligations split by actor: providers must ensure AI systems interacting with natural persons disclose their AI nature (Article 50(1)) and must mark synthetic AI-generated content in a machine-readable, detectable format (Article 50(2)); deployers must inform exposed persons when operating emotion-recognition or biometric-categorisation systems (Article 50(3)) and must label deepfakes as artificially generated or manipulated (Article 50(4)). Article 50(4) also requires deployers who use an AI system to generate or manipulate text published to inform the public on matters of public interest to disclose that the text was artificially generated or manipulated; this disclosure duty does not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for publishing it.
```

  - **ans_corr**: fail (unverifiable claims about Article 50 transparency obligations)
  omission_detail: The answer correctly identifies the core prohibition under Article 5(1)(f) and the medical/safety exception, which are the main elements established in the provided text.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 5.1.f']
  - **cite_faith**: pass (none - citations not fully verifiable from provided text)
  - **ans_conc**: pass (none)

### live_answers:la_q73

**Q:** What conformity-assessment route applies to an AI system that is a safety component of a CE-marked medical device?

- **gold refs**: Annex I, Article 6
- **base refs**: Article 43, Article 6, Annex I
- **branch refs**: Article 43, Article 6, Article 27, Article 49

**base — answer (345 chars):**

```
Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation. Under Annex III, Eight high-risk use-case categories: biometrics, critical infrastructure.
```

  - **ans_corr**: fail (incomplete answer - missing explicit high-risk classification and medical device specification)
  omission_detail: The answer fails to explicitly state that medical devices are listed in Annex I (Regulation (EU) 2017/745) and that the AI system would therefore be classified as high-risk, with conformity assessment conducted through the medical device's existing third-party procedure rather than a separate AI Act track.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 43', 'Article 6', 'Annex I']
  - **cite_faith**: fail (Failed to cite Article 43(3) which specifies the actual conformity assessment route for Annex I products)
  - **ans_conc**: fail (partial unrequested topic on Annex III categories)

**branch — answer (718 chars):**

```
Under Article 27, in addition to Article 26 baseline duties, deployers of certain Annex III high-risk AI systems must perform a Fundamental Rights Impact Assessment (FRIA) covering affected persons and specific fundamental rights risks. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation. Article 49 requires providers (and deployers that are public authorities) to register themselves and their high-risk AI system in the EU database (Article 71) before placing the system on the market or putting it into service.
```

  - **ans_corr**: fail (Incomplete answer with irrelevant information)
  omission_detail: The answer fails to explicitly state that an AI system that is a safety component of a CE-marked medical device is classified as high-risk under Article 6(1) and that medical devices (Regulation 2017/745) are listed in Annex I, which is the direct answer to the question asked.
  - **ref_corr**: fail (included irrelevant articles and missed Annex I)
  wrong_refs: ['Article 27', 'Article 49']
  governing_refs: ['Article 43', 'Article 6']
  missing_governing_refs: ['Annex I']
  - **cite_faith**: pass (answer fails to address the specific question about conformity assessment route for safety components of CE-marked medical devices)
  - **ans_conc**: fail (substantial detours into FRIA and registration requirements unrelated to conformity assessment route question)

### live_answers:la_q84

**Q:** An AI tool recommends oncology treatment regimens from clinical guidelines. What EU AI Act obligations does its provider face across the lifecycle?

- **gold refs**: Annex I, Annex III, Article 10, Article 13, Article 15, Article 16, Article 17, Article 19, Article 25, Article 49, Article 6, Article 9
- **base refs**: Article 15, Article 9, Article 16, Article 54, Article 96, Article 10, Article 13
- **branch refs**: Article 47, Article 16, Article 94, Article 71, Article 49, Article 80, Article 17

**base — answer (1398 chars):**

```
Requires providers of GPAI models established outside the EU to appoint, by written mandate, an authorised representative established in the Union before placing the GPAI model on the market. Article 54 is the GPAI-specific authorised-representative regime and is distinct from Article 22, Article 22 applies to high-risk AI SYSTEMS, Article 54 applies to GPAI MODELS. The Article 54(3) mandate must empower the representative to (a) verify that the Article 53(1)(a) technical documentation and Annex XI information are drawn up and that Article 53 obligations have been complied with; (b) keep the documentation and contact details available for the AI Office and national competent authorities for 10 years; (c) provide the AI Office on reasoned request with all information and documentation necessary to demonstrate compliance with Chapter V; (d) cooperate with the AI Office and competent authorities. The representative must terminate the mandate and inform the AI Office where it has reason to believe the provider is acting contrary to its obligations. GPAI-with-systemic-risk providers face the same Article 54 obligation plus Article 55 systemic obligations regardless of where they are established. Article 10 requires training, validation, and test datasets to be relevant, representative. Article 13 requires high-risk AI systems to be designed for sufficient operational transparency.
```

  - **ans_corr**: fail (Off-topic response addressing GPAI models instead of high-risk medical AI system obligations)
  omission_detail: The answer fails to identify that the oncology treatment AI is high-risk under Article 6(1) via Annex I (medical device legislation), fails to mention the core provider obligations under Article 16, fails to address conformity assessment, CE marking, quality management system, registration requirements, risk management, and the full lifecycle obligations that the question specifically asks about.
  - **ref_corr**: fail (included inapplicable GPAI provision and missed classification and procedural articles)
  wrong_refs: ['Article 54']
  governing_refs: ['Article 15', 'Article 9', 'Article 16', 'Article 10', 'Article 13']
  missing_governing_refs: ['Annex III']
  - **cite_faith**: pass (off-topic answer focusing on GPAI representative requirements instead of high-risk AI system lifecycle obligations)
  - **ans_conc**: fail (extensive GPAI model obligations unrelated to high-risk AI system lifecycle question)

**branch — answer (1675 chars):**

```
Article 25(2) requires the initial provider and the new provider to cooperate along the value chain: the initial provider must make available the necessary information and provide the reasonably expected technical access and other assistance so that the new provider can meet its obligations, in particular the conformity assessment of high-risk AI systems. Article 25(4) is a separate duty: the high-risk provider and third-party suppliers of AI systems, tools, services, components or processes used in or integrated into a high-risk AI system must specify, by written agreement, the necessary information, capabilities, technical access and other assistance, except for third parties making tools, services, processes or components (other than general-purpose AI models) accessible to the public under a free and open-source licence. For general-purpose AI models, the one-third fine-tune rule (per the Commission's 18 July 2025 GPAI Guidelines, anchored on Article 51) makes the downstream modifier a new provider when additional training compute exceeds 1/3 of the base model's compute, or 1/3 of the 10^25 FLOPs systemic threshold (~3.3×10^24 FLOPs) when base compute is unknown. Requires the provider to draw up a written, machine-readable, signed and dated EU declaration of conformity for each high-risk AI system, containing the information in Annex V, kept at the disposal of national competent authorities for 10 years. Article 17 requires providers of high-risk AI systems to operate a quality management system covering regulatory-compliance strategy, design verification, examination + test procedures, post-market monitoring, and incident-reporting workflows.
```

  - **ans_corr**: fail (Fails to address classification basis and omits most core provider lifecycle obligations)
  omission_detail: The answer fails to establish that the oncology treatment AI is classified as high-risk via Annex I (medical device legislation), fails to mention core provider obligations under Article 16, and omits key lifecycle requirements including data governance (Article 10), transparency and instructions for use (Article 13), accuracy/robustness/cybersecurity (Article 15), conformity assessment, CE marking, and registration obligations.
  - **ref_corr**: fail (missing core high-risk requirements (Articles 6, 9, 10, 13, 15, Annex III))
  wrong_refs: ['Article 94']
  governing_refs: ['Article 16', 'Article 49', 'Article 17']
  missing_governing_refs: ['Annex III', 'Article 10', 'Article 13', 'Article 15']
  - **cite_faith**: pass (Citations to articles not provided in verbatim text; misattribution of EU declaration requirements to wrong article)
  - **ans_conc**: fail (off-topic focus on provider transfer and GPAI rules instead of oncology AI lifecycle obligations)

### live_answers:la_q37

**Q:** When registering a high-risk AI system in the EU database under the EU AI Act, what specific information must the provider submit? List the required items.

- **gold refs**: Annex III, Annex VIII, Article 49, Article 71
- **base refs**: Article 6, Article 71, Article 16, Article 35, Article 112, Article 109, Article 77
- **branch refs**: Article 6, Article 71, Article 49, Article 26, Article 83, Article 66, Article 16

**base — answer (657 chars):**

```
The Commission shall, in collaboration with the Member States, set up and maintain an EU database containing information referred to in paragraphs 2 and 3 of this Article concerning high-risk AI systems referred to in Article 6(2) which are registered in accordance with Articles 49 and 60 and AI systems that are not considered as high-risk pursuant to Article 6(3) and which are registered in accordance with Article 6(4) and Article 49. When setting the functional specifications of such database, the Commission shall consult the relevant experts, and when updating the functional specifications of such database, the Commission shall consult the Board.
```

  - **ans_corr**: fail (failed to answer the question - listed database setup provisions instead of required registration information items)
  omission_detail: The question asks for the specific information items that providers must submit when registering a high-risk AI system. The answer completely fails to list the required items from Annex VIII Section A (provider name/address/contact details, trade name, intended purpose description, operating logic description, system status, certificate information, Member States, EU declaration of conformity, electronic instructions for use, etc.). Instead, it only quotes Article 71(1) about the database setup.
  - **ref_corr**: fail (failed to cite Annex VIII which lists the specific required information items)
  wrong_refs: ['Article 35', 'Article 112', 'Article 109', 'Article 77']
  governing_refs: ['Article 71']
  missing_governing_refs: ['Annex VIII', 'Article 49', 'Annex III']
  - **cite_faith**: pass (answer does not list required registration items from Annex VIII as asked)
  - **ans_conc**: fail (fails to answer question - describes database setup instead of listing required registration information)

**branch — answer (657 chars):**

```
The Commission shall, in collaboration with the Member States, set up and maintain an EU database containing information referred to in paragraphs 2 and 3 of this Article concerning high-risk AI systems referred to in Article 6(2) which are registered in accordance with Articles 49 and 60 and AI systems that are not considered as high-risk pursuant to Article 6(3) and which are registered in accordance with Article 6(4) and Article 49. When setting the functional specifications of such database, the Commission shall consult the relevant experts, and when updating the functional specifications of such database, the Commission shall consult the Board.
```

  - **ans_corr**: fail (failed to answer the question - listed database setup provisions instead of required registration information items)
  omission_detail: The question asks for the specific information items that providers must submit when registering a high-risk AI system. The answer completely fails to list the required items from Annex VIII Section A (provider name/address/contact details, trade name, intended purpose description, operating logic description, system status, certificate information, Member States, EU declaration of conformity, electronic instructions for use, etc.). Instead, it only quotes Article 71(1) about the database setup.
  - **ref_corr**: fail (missed key annexes specifying required registration information)
  wrong_refs: ['Article 26', 'Article 66']
  governing_refs: ['Article 71', 'Article 49']
  missing_governing_refs: ['Annex VIII', 'Annex III']
  - **cite_faith**: fail (Answer does not list required registration information items; cites irrelevant articles instead of Annex VIII)
  - **ans_conc**: fail (fails to answer question - describes database setup instead of listing required registration information)

### live_answers:la_q7

**Q:** We want to deploy an AI system that performs biometric verification solely to confirm that a specific natural person is the person he or she claims to be. Is this system prohibited? Is it high-risk?

- **gold refs**: Annex I, Annex III, Article 5, Article 50, Article 6
- **base refs**: Article 5, Article 6, Article 50, Annex III, Annex I
- **branch refs**: Article 5, Article 6, Article 50, Annex III, Annex I

**base — answer (574 chars):**

```
The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.
```

  - **ans_corr**: fail (omits explicit Annex III carve-out for biometric verification)
  omission_detail: The answer fails to state the key operative holding that biometric verification systems used solely to confirm identity are explicitly excluded from the high-risk category under Annex III, Section 1(a), which states 'This shall not include AI systems intended to be used for biometric verification the sole purpose of which is to confirm that a specific natural person is the person he or she claims to be'
  - **ref_corr**: pass (none)
  governing_refs: ['Article 5', 'Article 6', 'Annex III']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (574 chars):**

```
The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.
```

  - **ans_corr**: fail (incomplete answer - omits explicit Annex III carve-out for biometric verification)
  omission_detail: The answer fails to state the key operative holding that biometric verification systems used solely to confirm identity are expressly excluded from the high-risk category under Annex III, Section 1(a), which explicitly carves out 'AI systems intended to be used for biometric verification the sole purpose of which is to confirm that a specific natural person is the person he or she claims to be'
  - **ref_corr**: pass (none)
  governing_refs: ['Article 5', 'Article 6', 'Annex III']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q35

**Q:** Consider the situation in which a market surveillance authority (MSA) determines that an AI system, originally classified as non-high-risk by the provider, is in fact high-risk. Does the provider need to recall and suspend the use of the system without undue delay, or does the MSA provide a timeframe within which the provider can take corrective actions? Or does this depend on the gravity of the situation?

- **gold refs**: Annex III, Article 79, Article 80
- **base refs**: Article 74, Article 16, Article 6, Article 50, Annex III, Annex I, Article 11
- **branch refs**: Article 74, Article 16, Article 6, Article 50, Annex III, Annex I, Article 11

**base — answer (574 chars):**

```
The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.
```

  - **ans_corr**: fail (Off-topic response - answers classification question instead of enforcement procedure question)
  omission_detail: The question asks specifically about the MSA procedure when reclassifying a non-high-risk system as high-risk - whether immediate recall is required or a timeframe is given. Article 80 in the provided text clearly establishes that the MSA 'shall without undue delay require the relevant provider to take all necessary actions...within a period the market surveillance authority may prescribe.' The answer completely fails to address this procedural question and instead discusses classification criteria.
  - **ref_corr**: fail (missed key procedural articles 79 and 80 governing MSA corrective action procedures)
  wrong_refs: ['Article 50', 'Article 11']
  governing_refs: ['Article 6', 'Annex III']
  missing_governing_refs: ['Article 79', 'Article 80']
  - **cite_faith**: fail (Answer does not address the question about MSA reclassification and corrective action timeframes)
  - **ans_conc**: fail (answer addresses wrong question entirely - discusses classification criteria instead of MSA corrective action procedures)

**branch — answer (574 chars):**

```
The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.
```

  - **ans_corr**: fail (Off-topic response - answers classification question instead of enforcement procedure question)
  omission_detail: The question asks specifically about the MSA procedure when reclassifying a non-high-risk system as high-risk - whether immediate recall is required or a timeframe is given. Article 80 in the provided text clearly establishes that the MSA 'shall without undue delay require the relevant provider to take all necessary actions...within a period the market surveillance authority may prescribe.' The answer completely fails to address this procedural question and instead discusses classification criteria.
  - **ref_corr**: fail (missed key governing articles on MSA procedures for misclassified systems)
  wrong_refs: ['Article 50']
  governing_refs: ['Annex III']
  missing_governing_refs: ['Article 79', 'Article 80']
  - **cite_faith**: fail (Answer ignores the question about MSA corrective action procedures and discusses unrelated classification criteria)
  - **ans_conc**: fail (answer addresses wrong question entirely - discusses classification criteria instead of MSA corrective action procedures)

### live_answers:la_q2

**Q:** Does the obligation to indicate that deep-fakes are artificially generated apply when prosecuting a criminal offence?

- **gold refs**: Article 50
- **base refs**: Article 50.4, Article 50
- **branch refs**: Article 50.4, Article 50

**base — answer (382 chars):**

```
No. Under Article 50(4), the deployer's duty to disclose that image, audio, or video content constituting a deep fake has been artificially generated or manipulated does not apply where the use is authorised by law to detect, prevent, investigate, or prosecute criminal offences. Absent that law-enforcement authorisation, the deployer must disclose that the content is a deep fake.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 50.4', 'Article 50']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (382 chars):**

```
No. Under Article 50(4), the deployer's duty to disclose that image, audio, or video content constituting a deep fake has been artificially generated or manipulated does not apply where the use is authorised by law to detect, prevent, investigate, or prosecute criminal offences. Absent that law-enforcement authorisation, the deployer must disclose that the content is a deep fake.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 50.4', 'Article 50']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q52

**Q:** Can you help me understand AI compliance?

- **gold refs**: Article 17, Article 56
- **base refs**: Article 63, Article 56, Article 83
- **branch refs**: Article 111, Article 8, Article 86

**base — answer (735 chars):**

```
Under Article 56, Codes of Practice by the AI Office offer a route for GPAI providers to demonstrate Article 53 and 55 compliance; signing is voluntary, and providers may use any alternative adequate means to demonstrate compliance. Derogations for SMEs: simplified compliance with Article 17 quality-management-system obligations in a manner appropriate to size + market stage, without compromising the level of protection or compliance with the Section-2 requirements. AI Office encourages and facilitates voluntary codes of practice at Union level to contribute to proper application of the Regulation, particularly for GPAI obligations; codes may serve as a means to demonstrate compliance until harmonised standards are published.
```

  - **ans_corr**: fail (incomplete coverage of Article 17 high-risk AI compliance obligations)
  omission_detail: The answer fails to explain the core Article 17 quality management system requirements for high-risk AI systems, which is a central compliance obligation established in the provided text.
  - **ref_corr**: fail (missed core compliance article, included irrelevant enforcement provision)
  wrong_refs: ['Article 83']
  governing_refs: ['Article 56']
  missing_governing_refs: ['Article 17']
  - **cite_faith**: fail (Misattributed SME derogations to wrong article and cited irrelevant Article 83)
  - **ans_conc**: pass (none)

**branch — answer (890 chars):**

```
Under Article 111, transitional provisions grandfather pre-existing AI systems and GPAI models on the market before key dates unless they undergo a substantial change in design; high-risk systems for public-authority use comply from 2 August 2030. Under Article 86, any affected person subject to a decision based on output from an Annex III high-risk AI system has the individual right to obtain a clear and meaningful explanation of the AI system's role in the decision-making procedure. Transitional provisions for AI systems and GPAI models already on the market / in service: high-risk AI for public-authority use placed on the market before 2 August 2026 must comply from 2 August 2030 (only if significant design change); pre-2 August 2025 GPAI models brought into compliance by 2 August 2027; large-scale IT systems listed in Annex X covered by the Regulation from 31 December 2030.
```

  - **ans_corr**: fail (Irrelevant content citing articles not in provided text while omitting key compliance provisions)
  omission_detail: The verbatim text establishes Article 17's quality management system requirements for high-risk AI providers and Article 56's codes of practice framework for general-purpose AI models as central compliance mechanisms, but the predicted answer completely omits these operative provisions and instead discusses unrelated articles not present in the provided text.
  - **ref_corr**: fail (missed core compliance provisions Article 17 and Article 56)
  governing_refs: ['Article 8']
  missing_governing_refs: ['Article 17', 'Article 56']
  - **cite_faith**: fail (Article 111 mischaracterizes 'significant changes in their designs' as 'substantial change in design' and incorrectly states grandfathering applies to GPAI models)
  - **ans_conc**: fail (restates transitional provisions already covered in sentence 1)
  redundant_sentences: ['Transitional provisions for AI systems and GPAI models already on the market / in service: high-risk AI for public-authority use placed on the market before 2 August 2026 must comply from 2 August 2030 (only if significant design change); pre-2 August 2025 GPAI models brought into compliance by 2 August 2027; large-scale IT systems listed in Annex X covered by the Regulation from 31 December 2030.']

### live_answers:la_q13

**Q:** Under what conditions should providers of general-purpose AI models be subject to exceptions regarding transparency-related requirements, if any? And what do those exceptions not cover?

- **gold refs**: Annex XI, Annex XII, Article 51, Article 53, Article 55
- **base refs**: Article 53, Article 50.3, Article 50.4, Article 50.1, Article 16, Article 51, Article 55
- **branch refs**: Article 53, Article 50.1, Article 16, Article 55, Article 51, Article 56, Article 25

**base — answer (80 chars):**

```
This exception shall not apply to general-purpose AI models with systemic risks.
```

  - **ans_corr**: fail (incomplete answer - only states systemic risk limitation without explaining the exception conditions or scope)
  omission_detail: The answer fails to explain the conditions under which providers qualify for the exception (free and open-source licence with publicly available parameters), which specific obligations are excepted (Article 53(1)(a) and (b) regarding technical documentation), and what the exceptions do not cover (copyright policy compliance under Article 53(1)(c) and training content summary under Article 53(1)(d)).
  - **ref_corr**: fail (included irrelevant deployer/high-risk provisions, missed Annexes XI and XII)
  wrong_refs: ['Article 50.3', 'Article 50.4', 'Article 50.1', 'Article 16']
  governing_refs: ['Article 53', 'Article 51']
  missing_governing_refs: ['Annex XI', 'Annex XII']
  - **cite_faith**: pass (incomplete answer - only states exception limitation without explaining conditions for exception)
  - **ans_conc**: pass (none)

**branch — answer (80 chars):**

```
This exception shall not apply to general-purpose AI models with systemic risks.
```

  - **ans_corr**: fail (incomplete answer - only states systemic risk limitation without explaining the exception conditions or scope)
  omission_detail: The answer fails to explain the conditions under which providers qualify for the exception (free and open-source licence with publicly available parameters), which specific obligations are excepted (Article 53(1)(a) and (b) regarding technical documentation), and what the exceptions do not cover (copyright policy compliance under Article 53(1)(c) and training content summary under Article 53(1)(d)).
  - **ref_corr**: fail (included irrelevant articles and missed Annexes XI and XII)
  wrong_refs: ['Article 50.1', 'Article 16', 'Article 25']
  governing_refs: ['Article 53', 'Article 55']
  missing_governing_refs: ['Annex XI', 'Annex XII']
  - **cite_faith**: pass (incomplete answer - only states exception limitation without explaining conditions for exception)
  - **ans_conc**: pass (none)

### live_answers:la_q82

**Q:** Classify the EU AI Act risk tier of a consumer wellness chatbot that gives general lifestyle tips and makes no medical claims.

- **gold refs**: Annex I, Article 50, Article 6
- **base refs**: Article 50, Article 9, Article 25, Article 6, Article 10, Article 13, Article 53
- **branch refs**: Article 50, Article 6, Article 42, Article 49

**base — answer (1025 chars):**

```
Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties; both apply to the same system, not in the alternative. Article 25(2) requires the initial provider and the new provider to cooperate along the value chain: the initial provider must make available the necessary information and provide the reasonably expected technical access and other assistance so that the new provider can meet its obligations, in particular the conformity assessment of high-risk AI systems. Article 25(4) is a separate duty: the high-risk provider and third-party suppliers of AI systems, tools, services, components or processes used in or integrated into a high-risk AI system must specify, by written agreement, the necessary information, capabilities, technical access and other assistance, except for third parties making tools, services, processes or components (other than general-purpose AI models) accessible to the public under a free and open-source licence.
```

  - **ans_corr**: fail (Failed to answer the question - did not classify the risk tier)
  omission_detail: The question asks to classify the risk tier of a consumer wellness chatbot. The answer never states the applicable risk tier (minimal/limited risk, not high-risk) nor explains why the chatbot does not meet high-risk criteria under Article 6 or Annex III, which the verbatim text and gold answer establish.
  - **ref_corr**: fail (included high-risk obligations inapplicable to non-high-risk system)
  wrong_refs: ['Article 9', 'Article 25', 'Article 10', 'Article 13']
  governing_refs: ['Article 50', 'Article 6']
  missing_governing_refs: ['Annex I']
  - **cite_faith**: fail (Answer fails to classify the chatbot's risk tier and instead discusses unrelated value-chain cooperation obligations)
  - **ans_conc**: fail (entire answer addresses unrelated topics (high-risk transparency, value chain cooperation) instead of risk classification)

**branch — answer (722 chars):**

```
Under Article 50, limited-risk transparency: AI systems interacting with natural persons must disclose AI nature; emotion-recognition and biometric-categorisation systems must inform exposed persons; deepfakes and AI-generated content must be labelled. Eight high-risk use-case categories: biometrics, critical infrastructure, education + vocational training, employment + worker management (recruitment, task allocation, promotion and termination decisions, and performance evaluation affecting workers' fundamental rights), essential private + public services, law enforcement, migration + asylum + border control, and administration of justice + democratic processes. Classifies an AI system as high-risk on two routes.
```

  - **ans_corr**: fail (failed to answer the specific classification question)
  omission_detail: The answer fails to classify the consumer wellness chatbot itself. The question asks for the risk tier classification of this specific chatbot, and the gold answer establishes it does not meet high-risk criteria under Article 6. The predicted answer only describes general framework categories without stating the chatbot's actual classification.
  - **ref_corr**: fail (included irrelevant Article 42 on presumption of conformity, missed Annex I)
  wrong_refs: ['Article 42']
  governing_refs: ['Article 50', 'Article 6']
  missing_governing_refs: ['Annex I']
  - **cite_faith**: fail (cited irrelevant articles without applying classification to the specific chatbot scenario)
  - **ans_conc**: fail (extensive high-risk enumeration irrelevant to minimal-risk chatbot classification)

### live_answers:la_q72

**Q:** What must the provider of a high-risk AI medical diagnostic system put in place before placing it on the market?

- **gold refs**: Annex IV, Article 10, Article 11, Article 16, Article 8, Article 9
- **base refs**: Article 6, Article 16, Article 43, Article 8, Article 9, Article 10, Article 11
- **branch refs**: Article 6, Article 16, Article 43, Article 8, Article 9, Article 10, Article 11

**base — answer (467 chars):**

```
Providers of a high-risk AI system listed in Annex III are bound by Article 6, Article 8, and Article 9 (plus follow-on obligations summarised in the references list). Under Article 16, Providers of high-risk AI systems must ensure the system meets the Chapter III Section 2. Article 43 requires providers of high-risk AI to undergo a conformity assessment: internal-control. Article 10 requires training, validation, and test datasets to be relevant, representative.
```

  - **ans_corr**: fail (incomplete coverage of pre-market provider obligations)
  omission_detail: The answer omits the requirement under Article 11 that technical documentation must be drawn up before the system is placed on the market, containing the elements set out in Annex IV. It also omits the requirement under Article 16(b) to indicate provider identification details on the system or packaging, Article 16(c) quality management system, Article 16(g) EU declaration of conformity, and Article 16(h) CE marking requirements.
  - **ref_corr**: fail (missing Annex IV)
  governing_refs: ['Article 16', 'Article 8', 'Article 9', 'Article 10', 'Article 11']
  missing_governing_refs: ['Annex IV']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (467 chars):**

```
Providers of a high-risk AI system listed in Annex III are bound by Article 6, Article 8, and Article 9 (plus follow-on obligations summarised in the references list). Under Article 16, Providers of high-risk AI systems must ensure the system meets the Chapter III Section 2. Article 43 requires providers of high-risk AI to undergo a conformity assessment: internal-control. Article 10 requires training, validation, and test datasets to be relevant, representative.
```

  - **ans_corr**: fail (incomplete coverage of pre-market provider obligations)
  omission_detail: The answer omits the requirement under Article 11 that technical documentation must be drawn up before the system is placed on the market, containing the elements set out in Annex IV. It also omits the requirement under Article 16(b) to indicate provider identification details on the system or packaging, Article 16(c) quality management system, Article 16(g) EU declaration of conformity, and Article 16(h) CE marking requirements.
  - **ref_corr**: fail (missing Annex IV)
  governing_refs: ['Article 16', 'Article 8', 'Article 9', 'Article 10', 'Article 11']
  missing_governing_refs: ['Annex IV']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q11

**Q:** What is the meaning and purpose of 'testing data' in the context of AI systems, and why is it important that it is not leaked during the training process?

- **gold refs**: Article 10
- **base refs**: Article 3.32, Article 10
- **branch refs**: Article 3.32, Article 10

**base — answer (589 chars):**

```
Testing data is defined in Article 3(32) as data used to provide an independent evaluation of the AI system, in order to confirm its expected performance before it is placed on the market or put into service. It must be kept separate from the training and validation data so that this evaluation is genuinely independent. If testing data leaks into the training process, the system is in effect assessed on data it has already seen, which inflates its apparent performance and defeats the purpose of the independent check that Article 10 requires for the datasets of a high-risk AI system.
```

  - **ans_corr**: fail (unsupported citation to Article 3(32) definition not in provided text)
  omission_detail: The answer addresses the meaning and purpose of testing data and the importance of separation, though the specific definition cited (Article 3(32)) is not in the provided text. The core concepts about testing data quality requirements are addressed.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 3.32', 'Article 10']
  - **cite_faith**: fail (Article 10 does not explicitly require separation of testing data from training data or address data leakage)
  - **ans_conc**: pass (none)

**branch — answer (589 chars):**

```
Testing data is defined in Article 3(32) as data used to provide an independent evaluation of the AI system, in order to confirm its expected performance before it is placed on the market or put into service. It must be kept separate from the training and validation data so that this evaluation is genuinely independent. If testing data leaks into the training process, the system is in effect assessed on data it has already seen, which inflates its apparent performance and defeats the purpose of the independent check that Article 10 requires for the datasets of a high-risk AI system.
```

  - **ans_corr**: fail (unsupported definitional claims citing Article 3(32) not in provided text)
  omission_detail: The answer addresses the meaning and purpose of testing data and explains why separation from training data matters, which aligns with what the question asks. The verbatim text does not explicitly define testing data or explain data leakage, so no operative holding from the text was omitted.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 3.32', 'Article 10']
  - **cite_faith**: fail (Article 10 does not explicitly require testing data to be kept separate from training data or address data leakage)
  - **ans_conc**: pass (none)

### live_answers:la_q10

**Q:** Which article of the EU AI Act governs human oversight measures?

- **gold refs**: Article 14
- **base refs**: Article 14, Article 4, Article 1
- **branch refs**: Article 14, Article 2, Article 1

**base — answer (960 chars):**

```
Defines 68 terms used in the Regulation, including 'AI system' (machine-based, varying autonomy, possibly adaptive, inferring from input how to generate output influencing physical/virtual environments), 'provider', 'deployer', 'placing on the market', 'putting into service', 'substantial modification', 'general-purpose AI model', 'general-purpose AI system', 'systemic risk'. Requires providers and deployers to take measures to ensure, to their best extent, a sufficient level of AI literacy among their staff and other persons dealing with the operation and use of AI systems on their behalf, considering technical knowledge, experience, education, training, and context of use. Article 14 requires effective human oversight by natural persons during system use, capability + limitation awareness, automation-bias safeguards, ability to interpret output, disregard / override / intervene, and (for biometric identification) a two-person verification rule.
```

  - **ans_corr**: pass (Extraneous irrelevant information included)
  omission_detail: The answer correctly identifies Article 14 as governing human oversight measures, which is the core holding required by the question
  - **ref_corr**: fail (included tangentially related articles)
  wrong_refs: ['Article 4', 'Article 1']
  governing_refs: ['Article 14']
  - **cite_faith**: fail (included irrelevant article and definitions not asked for)
  - **ans_conc**: fail (substantial unrequested content on definitions and AI literacy)

**branch — answer (768 chars):**

```
Defines 68 terms used in the Regulation, including 'AI system' (machine-based, varying autonomy, possibly adaptive, inferring from input how to generate output influencing physical/virtual environments), 'provider', 'deployer', 'placing on the market', 'putting into service', 'substantial modification', 'general-purpose AI model', 'general-purpose AI system', 'systemic risk'. Scope: applies to providers placing AI systems on the EU market regardless of establishment, deployers established in the EU, providers/deployers in third countries whose output is used in the EU. Excludes military/defence/national-security uses, scientific R&D, purely personal non-professional use, and free/open-source AI systems outside the high-risk + prohibited + transparency scope.
```

  - **ans_corr**: fail (completely off-topic response)
  omission_detail: The question asks which article governs human oversight measures. The verbatim text clearly establishes this is Article 14, but the predicted answer completely fails to mention Article 14 or human oversight at all. Instead, it discusses definitions and scope provisions that are entirely irrelevant to the question.
  - **ref_corr**: fail (included irrelevant scope/purpose articles)
  wrong_refs: ['Article 2', 'Article 1']
  governing_refs: ['Article 14']
  - **cite_faith**: fail (Answer describes definitions and scope instead of human oversight measures)
  - **ans_conc**: fail (entirely off-topic response about definitions and scope instead of human oversight)

### live_answers:la_q67

**Q:** What does the EU AI Act require for an AI system that evaluates patients' eligibility for public healthcare benefits?

- **gold refs**: Annex III, Article 6
- **base refs**: Article 6, Annex III, Article 5, Annex I
- **branch refs**: Article 6, Annex III, Article 5, Annex I

**base — answer (724 chars):**

```
Eight high-risk use-case categories: biometrics, critical infrastructure, education + vocational training, employment + worker management (recruitment, task allocation, promotion and termination decisions, and performance evaluation affecting workers' fundamental rights), essential private + public services, law enforcement, migration + asylum + border control, and administration of justice + democratic processes. Classifies an AI system as high-risk on two routes. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation.
```

  - **ans_corr**: fail (Failed to answer the specific question - did not identify applicable classification for healthcare benefits eligibility AI)
  omission_detail: The answer fails to state that an AI system evaluating patients' eligibility for public healthcare benefits is classified as high-risk under Annex III category 5(a), which specifically covers AI systems used to evaluate eligibility for essential public assistance benefits and services including healthcare services. The answer also fails to mention the Annex III route under Article 6(2).
  - **ref_corr**: fail (included inapplicable provisions)
  wrong_refs: ['Article 5', 'Annex I']
  governing_refs: ['Article 6', 'Annex III']
  - **cite_faith**: pass (incomplete answer - fails to directly address the specific question about healthcare eligibility AI systems and their requirements)
  - **ans_conc**: fail (answer discusses general high-risk categories and Annex I route instead of addressing healthcare benefits eligibility specifically)

**branch — answer (724 chars):**

```
Eight high-risk use-case categories: biometrics, critical infrastructure, education + vocational training, employment + worker management (recruitment, task allocation, promotion and termination decisions, and performance evaluation affecting workers' fundamental rights), essential private + public services, law enforcement, migration + asylum + border control, and administration of justice + democratic processes. Classifies an AI system as high-risk on two routes. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation.
```

  - **ans_corr**: fail (Failed to answer the specific question - did not identify applicable classification for healthcare benefits eligibility AI)
  omission_detail: The answer fails to state that an AI system evaluating patients' eligibility for public healthcare benefits is classified as high-risk under Annex III category 5(a), which specifically covers AI systems used to evaluate eligibility for essential public assistance benefits and services including healthcare services. The answer also fails to mention the Annex III route under Article 6(2).
  - **ref_corr**: fail (included inapplicable provisions)
  wrong_refs: ['Article 5', 'Annex I']
  governing_refs: ['Article 6', 'Annex III']
  - **cite_faith**: pass (incomplete answer - fails to directly address the specific question about healthcare eligibility AI systems and their requirements)
  - **ans_conc**: fail (answer discusses general high-risk categories and Annex I route instead of addressing healthcare benefits eligibility specifically)

### live_answers:la_q53

**Q:** We are building a chatbot for customer support. What do we need to know?

- **gold refs**: Annex I, Annex III, Annex XI, Annex XII, Article 25, Article 51, Article 53, Article 55, Article 6
- **base refs**: Article 50, Article 29, Article 25
- **branch refs**: Article 50, Article 25, Article 29

**base — answer (1266 chars):**

```
Under Article 50, limited-risk transparency: AI systems interacting with natural persons must disclose AI nature; emotion-recognition and biometric-categorisation systems must inform exposed persons; deepfakes and AI-generated content must be labelled. Eight high-risk use-case categories: biometrics, critical infrastructure, education + vocational training, employment + worker management (recruitment, task allocation, promotion and termination decisions, and performance evaluation affecting workers' fundamental rights), essential private + public services, law enforcement, migration + asylum + border control, and administration of justice + democratic processes. Sets the application procedure for conformity-assessment bodies seeking notification under Article 28(1)(b): the body must submit the application to the notifying authority of the Member State in which it is established, together with a description of the conformity-assessment activities, modules, AI technologies, and evidence of compliance with the Article 31 requirements. Per Article 29(2)-(3) an accreditation certificate from a national accreditation body may serve as such evidence. Under Article 50, Transparency obligations split by actor: providers must ensure AI systems interacting.
```

  - **ans_corr**: fail (failed to apply classification to chatbot use case)
  omission_detail: The answer fails to state that a standard customer support chatbot does not fall within any Annex III high-risk category and is therefore not high-risk by default, which is the key operative holding for the question asked.
  - **ref_corr**: fail (cited procedural article on conformity assessment bodies instead of substantive classification rules)
  wrong_refs: ['Article 29']
  governing_refs: ['Article 50']
  - **cite_faith**: fail (cited Article 25 but described high-risk use-case categories not found in that article)
  - **ans_conc**: fail (unrequested conformity-assessment body procedures)
  redundant_sentences: ['Under Article 50, Transparency obligations split by actor: providers must ensure AI systems interacting.']

**branch — answer (1543 chars):**

```
Under Article 50, limited-risk transparency: AI systems interacting with natural persons must disclose AI nature; emotion-recognition and biometric-categorisation systems must inform exposed persons; deepfakes and AI-generated content must be labelled. Article 25(2) requires the initial provider and the new provider to cooperate along the value chain: the initial provider must make available the necessary information and provide the reasonably expected technical access and other assistance so that the new provider can meet its obligations, in particular the conformity assessment of high-risk AI systems. Article 25(4) is a separate duty: the high-risk provider and third-party suppliers of AI systems, tools, services, components or processes used in or integrated into a high-risk AI system must specify, by written agreement, the necessary information, capabilities, technical access and other assistance, except for third parties making tools, services, processes or components (other than general-purpose AI models) accessible to the public under a free and open-source licence. For general-purpose AI models, the one-third fine-tune rule (per the Commission's 18 July 2025 GPAI Guidelines, anchored on Article 51) makes the downstream modifier a new provider when additional training compute exceeds 1/3 of the base model's compute, or 1/3 of the 10^25 FLOPs systemic threshold (~3.3×10^24 FLOPs) when base compute is unknown. Under Article 50, Transparency obligations split by actor: providers must ensure AI systems interacting.
```

  - **ans_corr**: fail (Failed to address core classification question - chatbot not high-risk under Annex III)
  omission_detail: The answer fails to address that a customer support chatbot is not high-risk by default because it does not fall within any of the eight high-risk use-case categories in Annex III, which is the central operative holding relevant to the question.
  - **ref_corr**: fail (cited procedural article on conformity assessment bodies instead of risk classification rules)
  wrong_refs: ['Article 29']
  governing_refs: ['Article 50']
  - **cite_faith**: fail (citing unprovided articles and fabricating external guidelines content)
  - **ans_conc**: fail (extensive unrequested topics on value chain and GPAI fine-tuning rules)
  redundant_sentences: ['Under Article 50, Transparency obligations split by actor: providers must ensure AI systems interacting.']

### live_answers:la_q1

**Q:** Does the technical documentation of a high-risk AI system require to provide specifications regarding the required hardware?

- **gold refs**: Annex IV, Article 11
- **base refs**: Article 11, Annex IV
- **branch refs**: Article 11, Annex IV

**base — answer (387 chars):**

```
Yes. Under Article 11, a provider must draw up technical documentation containing the information set out in Annex IV, which expressly requires a description of the hardware on which the AI system is intended to run (Annex IV point 1(e)) and, as part of the system's development description, the computational resources used to develop, train, test and validate it (Annex IV point 2(c)).
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 11', 'Annex IV']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (387 chars):**

```
Yes. Under Article 11, a provider must draw up technical documentation containing the information set out in Annex IV, which expressly requires a description of the hardware on which the AI system is intended to run (Annex IV point 1(e)) and, as part of the system's development description, the computational resources used to develop, train, test and validate it (Annex IV point 2(c)).
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Article 11', 'Annex IV']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q46

**Q:** Is an AI system that recommends recipes high risk?

- **gold refs**: Annex I, Annex III, Article 5, Article 6
- **base refs**: Article 6, Article 50.1, Annex III, Annex I
- **branch refs**: Article 6, Article 50, Annex III, Annex I

**base — answer (528 chars):**

```
Not high-risk. A recipe-recommendation system does not fall within any of the eight use-case areas listed in Annex III, nor is it a safety component of, or itself, a product covered by the Union harmonisation legislation listed in Annex I requiring third-party conformity assessment, so neither route to high-risk classification under Article 6 is satisfied. Where the system interacts directly with natural persons, the provider must ensure those persons are informed they are interacting with an AI system under Article 50(1).
```

  - **ans_corr**: pass (minor unsupported addition)
  omission_detail: The answer correctly addresses both routes to high-risk classification (Article 6(1) via Annex I and Article 6(2) via Annex III) and concludes the system is not high-risk, which aligns with the gold answer.
  - **ref_corr**: fail (included irrelevant transparency provision and missed prohibited practices article)
  wrong_refs: ['Article 50.1']
  governing_refs: ['Article 6', 'Annex III', 'Annex I']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (574 chars):**

```
The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.
```

  - **ans_corr**: pass (none)
  omission_detail: The answer correctly addresses that a recipe recommendation AI is not prohibited under Article 5 and would only be high-risk if it meets Article 6 criteria (Annex I safety component or Annex III use case), which aligns with the gold answer's conclusion that it does not fall into high-risk categories.
  - **ref_corr**: fail (included irrelevant transparency provision (Article 50), missed prohibited practices (Article 5))
  wrong_refs: ['Article 50']
  governing_refs: ['Article 6', 'Annex III']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q19

**Q:** What is a deep fake according to the EU AI Act?

- **gold refs**: Article 50
- **base refs**: Article 3.60, Article 50
- **branch refs**: Article 3.60, Article 50

**base — answer (192 chars):**

```
AI-generated or manipulated image, audio or video content that resembles existing persons, objects, places, entities or events and would falsely appear to a person to be authentic or truthful.
```

  - **ans_corr**: fail (Definition includes elements not in provided text and omits regulatory obligations)
  omission_detail: The answer omits the key regulatory obligations from Article 50: that deployers must disclose that deep fake content has been artificially generated or manipulated (Article 50(4)), and that providers must mark outputs in machine-readable format detectable as artificially generated (Article 50(2)).
  - **ref_corr**: pass (none)
  governing_refs: ['Article 3.60']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (192 chars):**

```
AI-generated or manipulated image, audio or video content that resembles existing persons, objects, places, entities or events and would falsely appear to a person to be authentic or truthful.
```

  - **ans_corr**: fail (Definition includes elements not in provided text and omits transparency obligations)
  omission_detail: The answer omits the key operative obligations from Article 50: that deployers must disclose that deep fake content has been artificially generated or manipulated (Article 50(4)), and that providers must mark outputs in machine-readable format detectable as artificially generated (Article 50(2)).
  - **ref_corr**: pass (none)
  governing_refs: ['Article 3.60']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q78

**Q:** A pharma company trains a large foundation model for drug discovery whose training compute exceeds 10^25 FLOPs. Which EU AI Act obligations apply?

- **gold refs**: Annex III, Article 25, Article 3, Article 51, Article 6
- **base refs**: Article 51, Article 25
- **branch refs**: Article 51, Article 25

**base — answer (1255 chars):**

```
Under Article 51, a GPAI model has systemic risk when cumulative training compute exceeds 10²⁵ FLOPs (10^25); providers must notify the Commission within two weeks of meeting the threshold. Classifies a general-purpose AI model as having 'systemic risk' when it has high-impact capabilities (presumed when cumulative training compute exceeds 10^25 FLOPs) or when so designated by the Commission based on Annex XIII criteria. Commission's 18 July 2025 GPAI Guidelines presume a model is general-purpose (Article 3(63)) when training compute exceeds 10^23 FLOPs and the model can generate language, image, audio, or video output. Fine-tuned or modified models become new providers under Article 25 when their additional training compute exceeds one-third of the base model's compute (or one-third of the 10^25 systemic threshold, ~3.3×10^24 FLOPs, when base compute is unknown). Defines 68 terms used in the Regulation, including 'AI system' (machine-based, varying autonomy, possibly adaptive, inferring from input how to generate output influencing physical/virtual environments), 'provider', 'deployer', 'placing on the market', 'putting into service', 'substantial modification', 'general-purpose AI model', 'general-purpose AI system', 'systemic risk'.
```

  - **ans_corr**: fail (incomplete obligation specification)
  omission_detail: The answer fails to clearly state that the pharma company becomes the provider of a systemic-risk GPAI model and assumes Chapter V general-purpose AI obligations, and that high-risk obligations under Chapter III only apply if the model is integrated into a high-risk system under Article 6/Annex III
  - **ref_corr**: fail (cited inapplicable high-risk provider substitution article instead of core classification provisions)
  wrong_refs: ['Article 25']
  governing_refs: ['Article 51']
  missing_governing_refs: ['Article 6', 'Article 3']
  - **cite_faith**: fail (Article 25 describes high-risk AI system modifications, not GPAI fine-tuning compute thresholds)
  - **ans_conc**: fail (unrequested definitional catalogue)

**branch — answer (1255 chars):**

```
Under Article 51, a GPAI model has systemic risk when cumulative training compute exceeds 10²⁵ FLOPs (10^25); providers must notify the Commission within two weeks of meeting the threshold. Classifies a general-purpose AI model as having 'systemic risk' when it has high-impact capabilities (presumed when cumulative training compute exceeds 10^25 FLOPs) or when so designated by the Commission based on Annex XIII criteria. Commission's 18 July 2025 GPAI Guidelines presume a model is general-purpose (Article 3(63)) when training compute exceeds 10^23 FLOPs and the model can generate language, image, audio, or video output. Fine-tuned or modified models become new providers under Article 25 when their additional training compute exceeds one-third of the base model's compute (or one-third of the 10^25 systemic threshold, ~3.3×10^24 FLOPs, when base compute is unknown). Defines 68 terms used in the Regulation, including 'AI system' (machine-based, varying autonomy, possibly adaptive, inferring from input how to generate output influencing physical/virtual environments), 'provider', 'deployer', 'placing on the market', 'putting into service', 'substantial modification', 'general-purpose AI model', 'general-purpose AI system', 'systemic risk'.
```

  - **ans_corr**: fail (incomplete operative holding - fails to specify applicable obligation tier)
  omission_detail: The answer fails to clearly state that the pharma company becomes a provider of a systemic-risk GPAI model subject to Chapter V obligations, and does not address that high-risk obligations under Chapter III only apply if the model is integrated into an Annex III high-risk use case, which the facts do not establish.
  - **ref_corr**: fail (cited inapplicable high-risk provider reassignment article instead of core classification and definition provisions)
  wrong_refs: ['Article 25']
  governing_refs: ['Article 51']
  missing_governing_refs: ['Article 6', 'Article 3']
  - **cite_faith**: fail (Article 25 mischaracterized as applying to GPAI fine-tuning compute thresholds when it actually addresses high-risk AI system modifications)
  - **ans_conc**: fail (unrequested definitional catalogue)

### live_answers:la_q21

**Q:** If a provider of a high-risk AI system confirms that the system achieves an appropriate level of accuracy, robustness, and cybersecurity at the time of development, then no further action is required by the provider on these aspects in the future. Correct?

- **gold refs**: Article 15
- **base refs**: Article 6, Article 15, Article 16, Article 13, Article 42, Article 9, Article 17
- **branch refs**: Article 6, Article 15, Article 13, Article 16, Article 17, Article 43, Article 50

**base — answer (1022 chars):**

```
Providers of high-risk AI systems must ensure the system meets the Chapter III Section 2 requirements and bears their identity, operate a quality-management system (Article 17 requires providers of high-risk AI systems to operate a quality management system covering regulatory-compliance strategy, design verification, examination + test procedures, post-market monitoring, and incident-reporting workflows.), keep the technical documentation (Articles 11 and 18) and automatically generated logs (Article 19), have the system undergo conformity assessment (Article 43), draw up the EU declaration of conformity (Article 47), affix the CE marking (Article 48), register the system in the EU database (Article 49), take corrective action where it is not in conformity (Article 20), and demonstrate compliance to competent authorities on request (Article 21). Article 15 requires appropriate levels of accuracy, robustness. Article 9 requires a documented, iterative risk-management system across the AI system's lifecycle.
```

  - **ans_corr**: fail (Failed to directly answer the question and omitted the key lifecycle requirement from Article 15(1))
  omission_detail: The answer fails to directly address the question's core premise by not explicitly stating that the statement is incorrect. It does not clearly explain that Article 15(1) requires high-risk AI systems to perform consistently in accuracy, robustness, and cybersecurity 'throughout their lifecycle' - meaning ongoing obligations exist, not just at development time.
  - **ref_corr**: fail (over-citation with irrelevant articles)
  wrong_refs: ['Article 6', 'Article 42']
  governing_refs: ['Article 15']
  - **cite_faith**: pass (none)
  - **ans_conc**: fail (excessive unrequested detail on general provider obligations)

**branch — answer (730 chars):**

```
Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties; both apply to the same system, not in the alternative. Requires appropriate levels of accuracy, robustness, and cybersecurity across the lifecycle, accuracy metrics declared in instructions for use, resilience against errors, and resistance to data-poisoning, evasion, model-confidentiality, and adversarial attacks. Requires high-risk AI systems to be designed for sufficient operational transparency to deployers, accompanied by instructions for use covering provider identity, intended purpose, capabilities + limitations, expected lifetime, human-oversight measures, and required maintenance.
```

  - **ans_corr**: fail (Off-topic response addressing wrong articles and failing to directly answer the question)
  omission_detail: The answer fails to directly address the question's core assertion - it does not explicitly state that the statement is incorrect and that ongoing obligations exist throughout the lifecycle, not just at development time. While it mentions 'across the lifecycle', it does not frame this as a direct refutation of the question's premise.
  - **ref_corr**: fail (included irrelevant articles)
  wrong_refs: ['Article 6', 'Article 50']
  governing_refs: ['Article 15']
  - **cite_faith**: fail (Answer cites Article 50 for cumulative transparency duties but Article 50 addresses limited-risk AI interaction disclosure, not high-risk lifecycle requirements; answer fails to directly address the question about ongoing provider obligations)
  - **ans_conc**: fail (answer addresses wrong topic - discusses transparency instead of lifecycle accuracy/robustness requirements)

### live_answers:la_q29

**Q:** Under the EU AI Act, which specific AI systems are explicitly listed as high-risk because they make decisions in critical life- and health-related situations involving emergency calls and triage?

- **gold refs**: Article 6, Annex III
- **base refs**: Article 9, Article 27, Article 46
- **branch refs**: Article 9, Article 27, Article 46

**base — answer (806 chars):**

```
Under Article 27, in addition to Article 26 baseline duties, deployers of certain Annex III high-risk AI systems must perform a Fundamental Rights Impact Assessment (FRIA) covering affected persons and specific fundamental rights risks. Derogation from the conformity-assessment procedure: by way of derogation from Article 43, a market-surveillance authority may authorise the placing on the market or putting into service of specific high-risk AI systems within the territory of the Member State concerned, for exceptional reasons of public security or the protection of life and health of persons, environmental protection, or the protection of key industrial and infrastructural assets (Article 46(1)). Article 9 requires a documented, iterative risk-management system across the AI system's lifecycle.
```

  - **ans_corr**: fail (Failed to answer the question - did not identify the specific high-risk AI systems for emergency calls and triage listed in Annex III(5)(d))
  omission_detail: The question asks which specific AI systems are explicitly listed as high-risk for emergency calls and triage decisions. The verbatim text in Annex III, section 5(d) explicitly lists 'AI systems intended to evaluate and classify emergency calls by natural persons or to be used to dispatch, or to establish priority in the dispatching of, emergency first response services, including by police, firefighters and medical aid, as well as of emergency healthcare patient triage systems.' The predicted answer completely fails to identify or mention this specific provision.
  - **ref_corr**: fail (cited procedural/derogation articles instead of the definitional provisions listing high-risk AI systems)
  wrong_refs: ['Article 9', 'Article 27', 'Article 46']
  missing_governing_refs: ['Article 6', 'Annex III']
  - **cite_faith**: pass (answer does not address the question about emergency calls and triage AI systems)
  - **ans_conc**: fail (entirely off-topic response about unrelated provisions)

**branch — answer (806 chars):**

```
Under Article 27, in addition to Article 26 baseline duties, deployers of certain Annex III high-risk AI systems must perform a Fundamental Rights Impact Assessment (FRIA) covering affected persons and specific fundamental rights risks. Derogation from the conformity-assessment procedure: by way of derogation from Article 43, a market-surveillance authority may authorise the placing on the market or putting into service of specific high-risk AI systems within the territory of the Member State concerned, for exceptional reasons of public security or the protection of life and health of persons, environmental protection, or the protection of key industrial and infrastructural assets (Article 46(1)). Article 9 requires a documented, iterative risk-management system across the AI system's lifecycle.
```

  - **ans_corr**: fail (Failed to answer the question - did not identify the specific high-risk AI systems for emergency calls and triage listed in Annex III(5)(d))
  omission_detail: The question asks which specific AI systems are explicitly listed as high-risk for emergency calls and triage decisions. The verbatim text in Annex III, section 5(d) explicitly lists 'AI systems intended to evaluate and classify emergency calls by natural persons or to be used to dispatch, or to establish priority in the dispatching of, emergency first response services, including by police, firefighters and medical aid, as well as of emergency healthcare patient triage systems.' The predicted answer completely fails to identify or mention this specific provision.
  - **ref_corr**: fail (cited procedural/derogation articles instead of the definitional provisions listing high-risk AI systems)
  wrong_refs: ['Article 9', 'Article 27', 'Article 46']
  missing_governing_refs: ['Article 6', 'Annex III']
  - **cite_faith**: pass (answer does not address the question about emergency calls and triage AI systems)
  - **ans_conc**: fail (entirely off-topic response about unrelated provisions)

### live_answers:la_q36

**Q:** Under the EU AI Act, what presumption applies when a high-risk AI system is trained and tested on data that reflects the specific geographical, behavioural, contextual or functional setting in which it is intended to be used?

- **gold refs**: Article 10, Article 42
- **base refs**: Article 6, Article 42, Article 10
- **branch refs**: Article 6, Article 42, Article 10

**base — answer (741 chars):**

```
Adds two further presumptions of conformity beyond Articles 40-41: Article 42(1), high-risk AI systems trained and tested on data reflecting the specific geographical, behavioural, contextual, or functional setting in which they are intended to be used are presumed to comply with the relevant data-governance requirements of Article 10(4); Article 42(2), high-risk AI systems certified or for which a statement of conformity has been issued under a cybersecurity scheme under Regulation (EU) 2019/881 (the Cybersecurity Act) and whose references are published in the Official Journal are presumed to comply with the cybersecurity requirements of Article 15 to the extent the cybersecurity certificate or statement covers those requirements.
```

  - **ans_corr**: pass (none)
  omission_detail: The answer correctly identifies the presumption of compliance with Article 10(4) under Article 42(1), which is the core holding the question demands. While it does not explicitly state this is a rebuttable presumption or that it does not exempt from underlying duties, these are not strictly required by the question.
  - **ref_corr**: fail (included irrelevant Article 6)
  wrong_refs: ['Article 6']
  governing_refs: ['Article 42', 'Article 10']
  - **cite_faith**: pass (none)
  - **ans_conc**: fail (unrequested topic on cybersecurity presumption)

**branch — answer (741 chars):**

```
Adds two further presumptions of conformity beyond Articles 40-41: Article 42(1), high-risk AI systems trained and tested on data reflecting the specific geographical, behavioural, contextual, or functional setting in which they are intended to be used are presumed to comply with the relevant data-governance requirements of Article 10(4); Article 42(2), high-risk AI systems certified or for which a statement of conformity has been issued under a cybersecurity scheme under Regulation (EU) 2019/881 (the Cybersecurity Act) and whose references are published in the Official Journal are presumed to comply with the cybersecurity requirements of Article 15 to the extent the cybersecurity certificate or statement covers those requirements.
```

  - **ans_corr**: pass (none)
  omission_detail: The answer correctly identifies the presumption of compliance with Article 10(4) under Article 42(1), which is the core holding the question demands. While it does not explicitly state this is a rebuttable presumption or that it does not exempt from underlying duties, these are not strictly required by the question.
  - **ref_corr**: fail (included irrelevant article)
  wrong_refs: ['Article 6']
  governing_refs: ['Article 42', 'Article 10']
  - **cite_faith**: pass (none)
  - **ans_conc**: fail (unrequested topic on cybersecurity presumption)

### live_answers:la_q43

**Q:** Under Article 10(5) of the EU AI Act, when may a provider of a high-risk AI system process special categories of personal data for bias detection and correction, and what key safeguards/conditions must be met?

- **gold refs**: Article 10
- **base refs**: Article 10.5, Article 10
- **branch refs**: Article 10.5, Article 10

**base — answer (722 chars):**

```
Under Article 10(5), a provider of a high-risk AI system may exceptionally process special categories of personal data only to the extent strictly necessary to ensure bias detection and correction, subject to appropriate safeguards. Article 10(5) requires all of the following: the bias work cannot be done with other data, including synthetic or anonymised data (a); technical limits on re-use plus state-of-the-art security and pseudonymisation (b); strict, documented access controls to prevent misuse (c); no transmission or transfer to other parties (d); deletion once the bias is corrected or the retention period ends, whichever is first (e); and records of processing documenting why it was strictly necessary (f).
```

  - **ans_corr**: pass (none)
  omission_detail: The answer covers the strict necessity requirement, the subsidiary nature of the processing (cannot be achieved with other data), and all six conditions (a)-(f). It also mentions appropriate safeguards. No material operative holding is omitted.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 10.5', 'Article 10']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (722 chars):**

```
Under Article 10(5), a provider of a high-risk AI system may exceptionally process special categories of personal data only to the extent strictly necessary to ensure bias detection and correction, subject to appropriate safeguards. Article 10(5) requires all of the following: the bias work cannot be done with other data, including synthetic or anonymised data (a); technical limits on re-use plus state-of-the-art security and pseudonymisation (b); strict, documented access controls to prevent misuse (c); no transmission or transfer to other parties (d); deletion once the bias is corrected or the retention period ends, whichever is first (e); and records of processing documenting why it was strictly necessary (f).
```

  - **ans_corr**: pass (none)
  omission_detail: The answer covers all key elements including the strict necessity requirement, the subsidiary nature of the processing (cannot be achieved with other data), and all six conditions (a)-(f). The gold answer's emphasis on the wider data-governance regime of Article 10 is implicitly addressed through the reference to Article 10(5).
  - **ref_corr**: pass (none)
  governing_refs: ['Article 10.5', 'Article 10']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q17

**Q:** How does Annex II relate to prohibited uses of AI systems?

- **gold refs**: Annex II, Article 5
- **base refs**: Annex II
- **branch refs**: Annex II

**base — answer (500 chars):**

```
List of criminal offences referred to in Article 5(1)(h) permitting real-time remote biometric identification by law enforcement: terrorism, trafficking in human beings, sexual exploitation of children, illicit trafficking in narcotic drugs / weapons / nuclear material, murder, kidnapping, rape, armed robbery, organised crime, participation in a criminal organisation, environmental crime, provided the offence is punishable in the relevant Member State by a custodial sentence of at least 4 years.
```

  - **ans_corr**: fail (incomplete explanation of Annex II's relationship to prohibited uses)
  omission_detail: The answer fails to explain that Annex II functions as a definitional list narrowing an exception to a prohibited practice, and does not clarify that Article 5 generally prohibits real-time remote biometric identification with Annex II offences being one of the limited exceptions
  - **ref_corr**: fail (missing governing provision Article 5 that establishes the prohibited practices context)
  governing_refs: ['Annex II']
  missing_governing_refs: ['Article 5']
  - **cite_faith**: fail (incomplete list and omits several offences while adding unsupported 4-year sentence requirement)
  - **ans_conc**: pass (none)

**branch — answer (500 chars):**

```
List of criminal offences referred to in Article 5(1)(h) permitting real-time remote biometric identification by law enforcement: terrorism, trafficking in human beings, sexual exploitation of children, illicit trafficking in narcotic drugs / weapons / nuclear material, murder, kidnapping, rape, armed robbery, organised crime, participation in a criminal organisation, environmental crime, provided the offence is punishable in the relevant Member State by a custodial sentence of at least 4 years.
```

  - **ans_corr**: fail (incomplete explanation of relationship to prohibition)
  omission_detail: The answer fails to explain the relationship between Annex II and prohibited uses - specifically that Annex II defines exceptions to a prohibition rather than itself prohibiting anything, and that Article 5 generally prohibits real-time remote biometric identification in publicly accessible spaces for law enforcement purposes.
  - **ref_corr**: fail (missing governing provision Article 5 that establishes the prohibited practices context)
  governing_refs: ['Annex II']
  missing_governing_refs: ['Article 5']
  - **cite_faith**: fail (incomplete list and omits several offences while adding unsupported 4-year sentence requirement)
  - **ans_conc**: pass (none)

### live_answers:la_q22

**Q:** What are all the risk categories in the EU AI Act?

- **gold refs**: Article 5
- **base refs**: Article 5, Article 6, Article 50, Article 51, Article 52, Annex I, Annex III, Article 53, Article 54, Article 55, Article 56
- **branch refs**: Article 5, Article 6, Article 50, Article 51, Article 52, Annex I, Annex III, Article 53, Article 54, Article 55, Article 56

**base — answer (621 chars):**

```
The EU AI Act sets four risk tiers plus a separate regime for general-purpose AI models: unacceptable-risk practices are prohibited under Article 5; and high-risk systems are classified under Article 6 (an Annex I product safety component, or an Annex III use case) and carry the Chapter III Section 2 obligations. Limited-risk systems carry the Article 50 transparency duties, minimal-risk systems have no mandatory duties under the Act, and general-purpose AI models are governed separately under Articles 51 to 56, with added obligations under Article 55 for models classified as having systemic risk under Article 51.
```

  - **ans_corr**: fail (unverifiable claims beyond provided text)
  omission_detail: The answer addresses the question about risk categories. While the provided text only covers Article 5 (prohibited practices), the answer correctly identifies this as the unacceptable risk tier and provides additional context about other tiers that are not contradicted by the provided text.
  - **ref_corr**: fail (included irrelevant articles on GPAI provider obligations)
  wrong_refs: ['Article 53']
  governing_refs: ['Article 5', 'Article 6']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (621 chars):**

```
The EU AI Act sets four risk tiers plus a separate regime for general-purpose AI models: unacceptable-risk practices are prohibited under Article 5; and high-risk systems are classified under Article 6 (an Annex I product safety component, or an Annex III use case) and carry the Chapter III Section 2 obligations. Limited-risk systems carry the Article 50 transparency duties, minimal-risk systems have no mandatory duties under the Act, and general-purpose AI models are governed separately under Articles 51 to 56, with added obligations under Article 55 for models classified as having systemic risk under Article 51.
```

  - **ans_corr**: fail (unverifiable claims beyond provided text)
  omission_detail: The answer addresses the risk categories question comprehensively. The provided text only covers Article 5 (prohibited practices), so the answer's additional detail about other tiers cannot be verified but is not contradicted.
  - **ref_corr**: pass (included inapplicable articles on GPAI provider obligations)
  governing_refs: ['Article 5', 'Article 6', 'Annex III']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q65

**Q:** Which EU AI Act article sets the transparency obligation for a patient-facing medical chatbot?

- **gold refs**: Article 50
- **base refs**: Article 50.1, Article 13
- **branch refs**: Article 50.1, Article 13

**base — answer (1151 chars):**

```
Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties; both apply to the same system, not in the alternative. Transparency obligations split by actor: providers must ensure AI systems interacting with natural persons disclose their AI nature (Article 50(1)) and must mark synthetic AI-generated content in a machine-readable, detectable format (Article 50(2)); deployers must inform exposed persons when operating emotion-recognition or biometric-categorisation systems (Article 50(3)) and must label deepfakes as artificially generated or manipulated (Article 50(4)). Article 50(4) also requires deployers who use an AI system to generate or manipulate text published to inform the public on matters of public interest to disclose that the text was artificially generated or manipulated; this disclosure duty does not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for publishing it.
```

  - **ans_corr**: fail (Fails to directly answer the specific question about which article applies to patient-facing medical chatbot)
  omission_detail: The answer fails to directly state that Article 50(1) is the specific operative provision setting the transparency obligation for a patient-facing medical chatbot, which is the core question asked.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 50.1']
  - **cite_faith**: pass (claims about Article 50 subsections not supported by provided verbatim text)
  - **ans_conc**: fail (unrequested detail on text generation disclosure)

**branch — answer (1151 chars):**

```
Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties; both apply to the same system, not in the alternative. Transparency obligations split by actor: providers must ensure AI systems interacting with natural persons disclose their AI nature (Article 50(1)) and must mark synthetic AI-generated content in a machine-readable, detectable format (Article 50(2)); deployers must inform exposed persons when operating emotion-recognition or biometric-categorisation systems (Article 50(3)) and must label deepfakes as artificially generated or manipulated (Article 50(4)). Article 50(4) also requires deployers who use an AI system to generate or manipulate text published to inform the public on matters of public interest to disclose that the text was artificially generated or manipulated; this disclosure duty does not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for publishing it.
```

  - **ans_corr**: fail (Fails to directly answer the specific question asked)
  omission_detail: The answer fails to directly state that Article 50(1) is the specific operative provision for a patient-facing medical chatbot's transparency obligation, which is the core of what the question asks.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 50.1']
  - **cite_faith**: pass (claims about Article 50 subsections not supported by provided verbatim text)
  - **ans_conc**: fail (unrequested detail on text generation disclosure)

### live_answers:la_q71

**Q:** A hospital deploys a high-risk AI diagnostic system. What are its obligations as a deployer under the EU AI Act?

- **gold refs**: Annex III, Article 13, Article 25, Article 26, Article 27, Article 86
- **base refs**: Article 26, Article 27, Article 13, Article 86, Article 14, Article 9, Article 6
- **branch refs**: Article 26, Article 27, Article 13, Article 86, Article 14, Article 9, Article 6

**base — answer (926 chars):**

```
Under Article 27, in addition to Article 26 baseline duties, deployers of certain Annex III high-risk AI systems must perform a Fundamental Rights Impact Assessment (FRIA) covering affected persons and specific fundamental rights risks. Under Article 86, any affected person subject to a decision based on output from an Annex III high-risk AI system has the individual right to obtain a clear and meaningful explanation of the AI system's role in the decision-making procedure. Deployers of a high-risk AI system listed in Annex III are bound by Article 26, Article 27, and Article 13 (plus follow-on obligations summarised in the references list). Article 14 requires effective human oversight by natural persons during system use, capability + limitation awareness, automation-bias safeguards, ability to interpret output, disregard / override / intervene, and (for biometric identification) a two-person verification rule.
```

  - **ans_corr**: fail (incomplete coverage of core deployer obligations under Article 26)
  omission_detail: The answer omits key Article 26 deployer obligations explicitly stated in the text: using the system in accordance with instructions for use, monitoring the system's operation, keeping automatically generated logs for at least six months, and informing affected natural persons that they are subject to the high-risk AI system.
  - **ref_corr**: fail (included provider obligation (Article 9) instead of deployer-specific provisions)
  wrong_refs: ['Article 9']
  governing_refs: ['Article 26', 'Article 27', 'Article 13', 'Article 86']
  missing_governing_refs: ['Annex III', 'Article 25']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (926 chars):**

```
Under Article 27, in addition to Article 26 baseline duties, deployers of certain Annex III high-risk AI systems must perform a Fundamental Rights Impact Assessment (FRIA) covering affected persons and specific fundamental rights risks. Under Article 86, any affected person subject to a decision based on output from an Annex III high-risk AI system has the individual right to obtain a clear and meaningful explanation of the AI system's role in the decision-making procedure. Deployers of a high-risk AI system listed in Annex III are bound by Article 26, Article 27, and Article 13 (plus follow-on obligations summarised in the references list). Article 14 requires effective human oversight by natural persons during system use, capability + limitation awareness, automation-bias safeguards, ability to interpret output, disregard / override / intervene, and (for biometric identification) a two-person verification rule.
```

  - **ans_corr**: fail (incomplete coverage of core deployer obligations under Article 26)
  omission_detail: The answer omits key Article 26 deployer obligations explicitly stated in the text: using the system in accordance with instructions for use, monitoring the system's operation, keeping automatically generated logs for at least six months, and informing affected natural persons that they are subject to the high-risk AI system.
  - **ref_corr**: fail (included provider obligation (Article 9) instead of deployer-specific provisions)
  wrong_refs: ['Article 9']
  governing_refs: ['Article 26', 'Article 27', 'Article 13', 'Article 86']
  missing_governing_refs: ['Annex III', 'Article 25']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q32

**Q:** Is an AI system used to detect decision-making patterns or deviations for a use case listed in Annex III considered high-risk?

- **gold refs**: Annex III, Article 6
- **base refs**: Article 6.3, Article 6, Annex III
- **branch refs**: Article 6.3, Article 6, Annex III

**base — answer (477 chars):**

```
Not automatically. Even within an Annex III use case, Article 6(3)(c) provides that an AI system intended to detect decision-making patterns or deviations from prior decision-making patterns is not high-risk where it does not pose a significant risk of harm and is not meant to replace or influence a previously completed human assessment without proper human review. However, under Article 6(3) such a system is always high-risk where it performs profiling of natural persons.
```

  - **ans_corr**: pass (none)
  omission_detail: The answer addresses the key elements: the derogation under Article 6(3)(c) for pattern detection systems, the conditions for the derogation, and the profiling exception. The gold answer's point about classification depending on Annex III use-case areas is implicitly addressed by the answer's framing 'within an Annex III use case'.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 6.3', 'Article 6', 'Annex III']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (477 chars):**

```
Not automatically. Even within an Annex III use case, Article 6(3)(c) provides that an AI system intended to detect decision-making patterns or deviations from prior decision-making patterns is not high-risk where it does not pose a significant risk of harm and is not meant to replace or influence a previously completed human assessment without proper human review. However, under Article 6(3) such a system is always high-risk where it performs profiling of natural persons.
```

  - **ans_corr**: pass (none)
  omission_detail: The answer addresses the key elements: the derogation under Article 6(3)(c) for pattern detection systems, the conditions for the derogation, and the profiling exception. The gold answer's point about classification depending on Annex III use-case areas is implicitly addressed by the answer's framing 'within an Annex III use case'.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 6.3', 'Article 6', 'Annex III']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q55

**Q:** hi, what can you do?

- **gold refs**: (none)
- **base refs**: (none)
- **branch refs**: (none)

**base — answer (158 chars):**

```
I am Lexy, a Compliance assistant that can answer your questions related to the EU AI Act, based on my Knowledge Graph and ontology. What can I help you with?
```

  - **ans_corr**: fail (none)
  omission_detail: The question is a general capability inquiry, not a substantive legal question requiring specific regulatory holdings. The predicted answer appropriately indicates it can help with EU AI Act questions, which aligns with the gold answer's guidance.
  - **ref_corr**: pass (none - greeting question requires no citations)
  - **cite_faith**: pass (none - no citations made)
  - **ans_conc**: pass (none)

**branch — answer (158 chars):**

```
I am Lexy, a Compliance assistant that can answer your questions related to the EU AI Act, based on my Knowledge Graph and ontology. What can I help you with?
```

  - **ans_corr**: fail (none)
  omission_detail: The question is a general capability inquiry, not a substantive legal question requiring specific regulatory holdings. The predicted answer appropriately indicates it can help with EU AI Act questions, which aligns with the gold answer's guidance.
  - **ref_corr**: pass (none - greeting question requires no citations)
  - **cite_faith**: pass (none - no citations made)
  - **ans_conc**: pass (none)

### live_answers:la_q77

**Q:** Does the EU AI Act require post-market monitoring and serious-incident reporting for an AI-based patient-monitoring device, and under which articles?

- **gold refs**: Article 72, Article 73, Article 3
- **base refs**: Article 72, Article 73
- **branch refs**: Article 72.1, Article 72.4, Article 73.9, Article 73.1

**base — answer (641 chars):**

```
Under Article 73, providers of high-risk AI systems must report any serious incident to the market surveillance authority within 15 days of becoming aware. Requires providers of high-risk AI systems to establish and document a post-market monitoring system proportionate to the nature and risks of the AI system (Article 72(1)). The system actively collects, documents, and analyses performance data throughout the system's lifetime to evaluate continuous compliance with Chapter III Section 2 requirements (Article 72(2)), based on a post-market monitoring plan that forms part of the technical documentation under Annex IV (Article 72(3)).
```

  - **ans_corr**: fail (incomplete tiered deadline information)
  omission_detail: The answer omits the tiered reporting deadlines: immediately and no later than 2 days for widespread infringement or critical-infrastructure disruption, within 10 days for death, and only states the general 15-day deadline. It also omits the definition of serious incident from Article 3(49).
  - **ref_corr**: fail (missing definition article for serious incident)
  governing_refs: ['Article 72', 'Article 73']
  missing_governing_refs: ['Article 3']
  - **cite_faith**: fail (Oversimplified reporting deadline - Article 73 states 15 days is the outer limit after establishing causal link, not simply after becoming aware)
  - **ans_conc**: pass (none)

**branch — answer (1343 chars):**

```
Yes. An AI-based patient-monitoring device is high-risk under Article 6(1) where it is a safety component of, or is itself, a medical device covered by the Medical Devices Regulation listed in Annex I Section A and that device must undergo third-party conformity assessment. As a high-risk system, the provider must establish and document a post-market monitoring system that actively collects and analyses performance data throughout the system's lifetime to evaluate continuous compliance, based on a post-market monitoring plan forming part of the technical documentation (Article 72(1) to (3), Annex IV). Article 72(4) permits the provider to integrate those elements into the post-market surveillance system already required under the Medical Devices Regulation rather than maintaining a parallel one. For serious incident reporting, Article 73 applies, but Article 73(9) narrows the AI Act reporting duty for high-risk systems covered by Union legislation with equivalent reporting obligations: notification is limited to serious incidents consisting of an infringement of Union law protecting fundamental rights, reported to the market surveillance authority of the Member State where the incident occurred, while incidents involving death or serious deterioration of health route through the medical-device vigilance framework instead.
```

  - **ans_corr**: fail (incomplete coverage of reporting deadlines)
  omission_detail: The answer omits the specific tiered deadlines for serious incident reporting under Article 73: immediately and no later than 2 days for widespread infringement or critical-infrastructure disruption, within 10 days for death, and within 15 days for other serious incidents.
  - **ref_corr**: fail (missing definition of serious incident from Article 3)
  governing_refs: ['Article 72.1', 'Article 73.1']
  missing_governing_refs: ['Article 3']
  - **cite_faith**: fail (Mischaracterized Article 73(9) scope - text limits to Article 3(49)(c) incidents, not fundamental rights infringements specifically)
  - **ans_conc**: pass (none)

### live_answers:la_q86

**Q:** What does the EU AI Act require for an AI system used for risk assessment and pricing in health insurance?

- **gold refs**: Annex III, Article 6
- **base refs**: Article 6, Annex III
- **branch refs**: Article 6, Annex III.5, Annex I

**base — answer (400 chars):**

```
Classifies an AI system as high-risk on two routes. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation. Annex III route (Article 6(2)): the system falls within one of the eight Annex III use cases.
```

  - **ans_corr**: fail (failed to identify specific applicable provision)
  omission_detail: The answer fails to state that AI systems for risk assessment and pricing in health insurance specifically fall under Annex III category 5(c) as high-risk, which is the direct answer to the question. The answer only provides general classification routes without identifying which route applies to the specific use case asked about.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 6', 'Annex III']
  - **cite_faith**: pass (incomplete answer - describes classification but not specific requirements for health insurance AI systems)
  - **ans_conc**: pass (none)

**branch — answer (400 chars):**

```
Classifies an AI system as high-risk on two routes. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation. Annex III route (Article 6(2)): the system falls within one of the eight Annex III use cases.
```

  - **ans_corr**: fail (failed to identify specific applicable provision)
  omission_detail: The answer fails to state that AI systems for risk assessment and pricing in health insurance specifically fall under Annex III category 5(c) as high-risk, which is the direct answer to the question. The answer only provides general classification routes without identifying which route applies to the specific use case asked about.
  - **ref_corr**: fail (included irrelevant citation)
  wrong_refs: ['Annex I']
  governing_refs: ['Article 6', 'Annex III.5']
  - **cite_faith**: pass (incomplete answer - fails to mention specific Annex III.5(c) classification and high-risk obligations)
  - **ans_conc**: pass (none)

### live_answers:la_q27

**Q:** How are AI systems intended to influence the outcome of an election or referendum classified, and what exception is given for certain campaign-related tools?

- **gold refs**: Annex III
- **base refs**: Article 6, Annex III.8
- **branch refs**: Article 6, Annex III.8

**base — answer (493 chars):**

```
Under Annex III point 8(b), AI systems intended to influence the outcome of an election or referendum, or the voting behaviour of natural persons in exercising their vote, are high-risk under Article 6(2). Annex III point 8(b) itself excludes systems to whose output natural persons are not directly exposed, such as tools used only to organise, optimise or structure political campaigns from an administrative or logistical point of view, which therefore fall outside this high-risk category.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Annex III.8']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

**branch — answer (493 chars):**

```
Under Annex III point 8(b), AI systems intended to influence the outcome of an election or referendum, or the voting behaviour of natural persons in exercising their vote, are high-risk under Article 6(2). Annex III point 8(b) itself excludes systems to whose output natural persons are not directly exposed, such as tools used only to organise, optimise or structure political campaigns from an administrative or logistical point of view, which therefore fall outside this high-risk category.
```

  - **ans_corr**: pass (none)
  - **ref_corr**: pass (none)
  governing_refs: ['Annex III.8']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (none)

### live_answers:la_q63

**Q:** What are the algorithmic transparency obligations for a Very Large Online Platform content-moderation AI?

- **gold refs**: Article 50
- **base refs**: (none)
- **branch refs**: (none)

**base — answer (209 chars):**

```
This question is about the Digital Services Act (DSA), not the EU AI Act (Regulation 2024/1689). This assistant only covers EU AI Act questions; consult the Digital Services Act (DSA) for the applicable rules.
```

  - **ans_corr**: fail (Incorrect scope deflection - wrongly claims EU AI Act does not apply)
  omission_detail: The answer completely fails to address the Article 50 transparency obligations that would apply to content-moderation AI systems, including Article 50(1) requirements for AI systems interacting with natural persons and Article 50(2) requirements for systems generating synthetic content. The verbatim text establishes these obligations exist under the EU AI Act.
  - **ref_corr**: fail (no citations provided)
  missing_governing_refs: ['Article 50']
  - **cite_faith**: pass (none - answer correctly identifies question as outside EU AI Act scope)
  - **ans_conc**: pass (none)

**branch — answer (209 chars):**

```
This question is about the Digital Services Act (DSA), not the EU AI Act (Regulation 2024/1689). This assistant only covers EU AI Act questions; consult the Digital Services Act (DSA) for the applicable rules.
```

  - **ans_corr**: fail (Incorrect scope deflection - wrongly claims EU AI Act does not apply)
  omission_detail: The answer completely fails to address the Article 50 transparency obligations that would apply to content-moderation AI systems, including Article 50(1) requirements for AI systems interacting with natural persons and Article 50(2) requirements for systems generating synthetic content. The verbatim text establishes these obligations exist under the EU AI Act.
  - **ref_corr**: fail (no citations provided)
  missing_governing_refs: ['Article 50']
  - **cite_faith**: pass (none - answer correctly identifies question as outside EU AI Act scope)
  - **ans_conc**: pass (none)

### live_answers:la_q92

**Q:** What does GDPR Article 17 say about the right to erasure?

- **gold refs**: Article 17
- **base refs**: (none)
- **branch refs**: (none)

**base — answer (225 chars):**

```
This question is about a regulation outside the EU AI Act. This assistant answers EU AI Act questions only (Regulation 2024/1689). Please rephrase with a specific Article reference (e.g. "Article 13") or compliance dimension.
```

  - **ans_corr**: fail (Refusal to answer when relevant information was available)
  omission_detail: The answer fails to explain that the provided Article 17 text is actually from the EU AI Act (concerning quality management systems for high-risk AI providers), not GDPR Article 17 (right to erasure). The gold answer correctly identifies this distinction and explains what EU AI Act Article 17 actually covers.
  - **ref_corr**: pass (out-of-scope question about GDPR not EU AI Act)
  - **cite_faith**: pass (none - appropriate scope limitation)
  - **ans_conc**: pass (none)

**branch — answer (225 chars):**

```
This question is about a regulation outside the EU AI Act. This assistant answers EU AI Act questions only (Regulation 2024/1689). Please rephrase with a specific Article reference (e.g. "Article 13") or compliance dimension.
```

  - **ans_corr**: fail (Refusal to answer when relevant information was available)
  omission_detail: The answer fails to explain that the provided Article 17 text is actually from the EU AI Act (concerning quality management systems for high-risk AI providers), not GDPR Article 17 (right to erasure). The gold answer correctly identifies this distinction and explains what EU AI Act Article 17 actually covers.
  - **ref_corr**: pass (out-of-scope question about GDPR not EU AI Act)
  - **cite_faith**: pass (none - appropriate scope limitation)
  - **ans_conc**: pass (none)

### live_answers:la_q60

**Q:** What are the algorithmic transparency obligations for a Very Large Online Platform content-moderation AI?

- **gold refs**: Article 50
- **base refs**: (none)
- **branch refs**: (none)

**base — answer (209 chars):**

```
This question is about the Digital Services Act (DSA), not the EU AI Act (Regulation 2024/1689). This assistant only covers EU AI Act questions; consult the Digital Services Act (DSA) for the applicable rules.
```

  - **ans_corr**: fail (Incorrect refusal to answer - wrongly claims question is outside scope of EU AI Act)
  omission_detail: The answer fails to address that Article 50 of the EU AI Act does contain transparency obligations that could apply to content-moderation AI systems, including requirements for informing users when interacting with AI systems (Article 50(1)) and marking synthetic content as artificially generated (Article 50(2)).
  - **ref_corr**: fail (no citations provided)
  missing_governing_refs: ['Article 50']
  - **cite_faith**: pass (none - answer correctly identifies question as outside EU AI Act scope)
  - **ans_conc**: pass (none)

**branch — answer (209 chars):**

```
This question is about the Digital Services Act (DSA), not the EU AI Act (Regulation 2024/1689). This assistant only covers EU AI Act questions; consult the Digital Services Act (DSA) for the applicable rules.
```

  - **ans_corr**: fail (Incorrect scope deflection - wrongly claims question is outside EU AI Act when Article 50 directly addresses it)
  omission_detail: The answer fails to address Article 50's transparency obligations that would apply to content-moderation AI systems, including the requirement to inform users when interacting with AI (Article 50(1)) and marking synthetic content as artificially generated (Article 50(2))
  - **ref_corr**: fail (no citations provided)
  missing_governing_refs: ['Article 50']
  - **cite_faith**: pass (none - answer correctly identifies question as outside EU AI Act scope)
  - **ans_conc**: pass (none)

### live_answers:la_q75

**Q:** What data-governance obligations apply to the training data of a high-risk AI sepsis-prediction model?

- **gold refs**: Article 10
- **base refs**: Article 10, Article 42, Article 26
- **branch refs**: Article 10, Article 26, Article 13

**base — answer (894 chars):**

```
Deployer obligations: use the system per the instructions, assign human oversight to competent + trained natural persons, monitor operation, retain automatically generated logs, inform affected workers (for workplace use), and cooperate with market-surveillance authorities. Article 26 carve-outs: deployers that are financial institutions subject to Union financial-services internal-governance requirements fulfil the Article 26(5) monitoring obligation and the Article 26(6) log-retention obligation by complying with the governance arrangements under that financial-services law (Article 26(5) second subparagraph; Article 26(6) second subparagraph). Workplace deployers who are employers must inform workers' representatives and the affected workers BEFORE putting the high-risk system into service (Article 26(7)); applicable Union and national worker-information rules continue to apply.
```

  - **ans_corr**: fail (Wrong article - answered deployer obligations instead of data governance obligations)
  omission_detail: The question asks about data-governance obligations for training data under Article 10, including requirements for data governance practices (Article 10(2)), data quality criteria (Article 10(3)), bias examination (Article 10(2)(f)-(g)), and special category data processing conditions (Article 10(5)). The predicted answer discusses deployer obligations under Article 26 instead and completely omits all Article 10 data governance requirements.
  - **ref_corr**: fail (included deployer obligations unrelated to training data governance)
  wrong_refs: ['Article 26']
  governing_refs: ['Article 10']
  - **cite_faith**: fail (Answer discusses deployer obligations instead of data governance requirements for training data)
  - **ans_conc**: fail (entire answer addresses deployer obligations instead of data-governance obligations for training data)

**branch — answer (894 chars):**

```
Deployer obligations: use the system per the instructions, assign human oversight to competent + trained natural persons, monitor operation, retain automatically generated logs, inform affected workers (for workplace use), and cooperate with market-surveillance authorities. Article 26 carve-outs: deployers that are financial institutions subject to Union financial-services internal-governance requirements fulfil the Article 26(5) monitoring obligation and the Article 26(6) log-retention obligation by complying with the governance arrangements under that financial-services law (Article 26(5) second subparagraph; Article 26(6) second subparagraph). Workplace deployers who are employers must inform workers' representatives and the affected workers BEFORE putting the high-risk system into service (Article 26(7)); applicable Union and national worker-information rules continue to apply.
```

  - **ans_corr**: fail (completely wrong topic - answered deployer obligations instead of data governance obligations)
  omission_detail: The question asks about data-governance obligations for training data under Article 10, including requirements for data governance practices (Article 10(2)), data quality criteria (Article 10(3)), bias examination (Article 10(2)(f)-(g)), and special category data processing conditions (Article 10(5)). The predicted answer discusses deployer obligations under Article 26 instead and completely omits all Article 10 data governance requirements.
  - **ref_corr**: fail (included deployer and transparency articles unrelated to training data governance)
  wrong_refs: ['Article 26', 'Article 13']
  governing_refs: ['Article 10']
  - **cite_faith**: fail (Answer discusses deployer obligations instead of data governance obligations for training data)
  - **ans_conc**: fail (entire answer addresses deployer obligations instead of data-governance obligations for training data)

### live_answers:la_q31

**Q:** Is an AI system used to structure or deduplicate information for a use case listed in Annex III considered high-risk?

- **gold refs**: Annex III, Article 50, Article 6
- **base refs**: Article 6, Article 50, Annex III, Annex I
- **branch refs**: Article 6, Article 50, Annex III, Annex I

**base — answer (574 chars):**

```
The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.
```

  - **ans_corr**: fail (Omits Article 6(3)(d) preparatory task exception directly relevant to the question)
  omission_detail: The answer fails to address the specific question about AI systems used to structure or deduplicate information for Annex III use cases. Article 6(3)(d) explicitly provides that an AI system 'intended to perform a preparatory task to an assessment relevant for the purposes of the use cases listed in Annex III' may not be considered high-risk under the derogation. The answer does not mention this critical exception for preparatory tasks.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 6', 'Annex III']
  - **cite_faith**: pass (none)
  - **ans_conc**: fail (unnecessary Article 5 prohibition analysis)

**branch — answer (574 chars):**

```
The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.
```

  - **ans_corr**: fail (incomplete analysis - omits Article 6(3) preparatory task exception)
  omission_detail: The answer fails to address the key Article 6(3) derogation which specifies that AI systems intended to perform preparatory tasks to an assessment relevant for Annex III use cases are not considered high-risk, which is the operative holding directly relevant to the question about structuring or deduplicating information.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 6', 'Annex III']
  - **cite_faith**: pass (none)
  - **ans_conc**: fail (unnecessary Article 5 prohibition analysis)

### live_answers:la_q69

**Q:** Is an AI system that infers patients' emotions for a medical purpose prohibited under Article 5 of the EU AI Act?

- **gold refs**: Article 5
- **base refs**: Article 5.1.f
- **branch refs**: Article 5.1.f

**base — answer (850 chars):**

```
Under Article 5.1.f, emotion recognition in the workplace and in educational institutions is prohibited, including monitoring employees or call-centre agents, with a narrow medical/safety carve-out for systems placed on the market for therapeutic or accident-prevention purposes. Real-time remote biometric identification by law enforcement is prohibited under Article 5 save for narrow, exhaustively-listed law-enforcement exceptions that each require prior judicial or administrative authorisation; under Article 5(5) Member States may enable those exceptions in national law and may set stricter national rules. Article 5(1)(c) carve-out: the social-scoring prohibition does not affect lawful evaluation practices of natural persons that are carried out for a specific purpose in accordance with Union and national law (Recital 31 final sentence).
```

  - **ans_corr**: fail (Failed to answer the specific question asked)
  omission_detail: The answer fails to directly address the specific question asked: whether an AI system that infers patients' emotions for a medical purpose is prohibited. The text clearly shows such systems are NOT prohibited due to the medical carve-out in Article 5(1)(f), but the answer never states this conclusion.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 5.1.f']
  - **cite_faith**: pass (none)
  - **ans_conc**: fail (unrequested topics on biometric identification and social scoring)

**branch — answer (850 chars):**

```
Under Article 5.1.f, emotion recognition in the workplace and in educational institutions is prohibited, including monitoring employees or call-centre agents, with a narrow medical/safety carve-out for systems placed on the market for therapeutic or accident-prevention purposes. Real-time remote biometric identification by law enforcement is prohibited under Article 5 save for narrow, exhaustively-listed law-enforcement exceptions that each require prior judicial or administrative authorisation; under Article 5(5) Member States may enable those exceptions in national law and may set stricter national rules. Article 5(1)(c) carve-out: the social-scoring prohibition does not affect lawful evaluation practices of natural persons that are carried out for a specific purpose in accordance with Union and national law (Recital 31 final sentence).
```

  - **ans_corr**: fail (Failed to answer the specific question asked)
  omission_detail: The answer fails to directly address the specific question asked: whether an AI system that infers patients' emotions for a medical purpose is prohibited. The text clearly shows such systems are NOT prohibited due to the medical carve-out in Article 5(1)(f), but the answer never states this conclusion.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 5.1.f']
  - **cite_faith**: pass (none)
  - **ans_conc**: fail (unrequested topics on biometric identification and social scoring)

### live_answers:la_q80

**Q:** What transparency obligation applies to AI-generated synthetic medical images used to augment a training dataset?

- **gold refs**: Article 50
- **base refs**: Article 50, Article 13
- **branch refs**: Article 50, Article 13

**base — answer (1151 chars):**

```
Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties; both apply to the same system, not in the alternative. Transparency obligations split by actor: providers must ensure AI systems interacting with natural persons disclose their AI nature (Article 50(1)) and must mark synthetic AI-generated content in a machine-readable, detectable format (Article 50(2)); deployers must inform exposed persons when operating emotion-recognition or biometric-categorisation systems (Article 50(3)) and must label deepfakes as artificially generated or manipulated (Article 50(4)). Article 50(4) also requires deployers who use an AI system to generate or manipulate text published to inform the public on matters of public interest to disclose that the text was artificially generated or manipulated; this disclosure duty does not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for publishing it.
```

  - **ans_corr**: fail (Failed to answer the specific question asked)
  omission_detail: The answer fails to address the specific question about synthetic medical images used to augment training datasets. It does not explain that Article 50(2) marking obligation applies to the provider of the generative system, nor does it clarify that Article 50(4) deepfake labeling generally does not apply to purely internal training dataset use since it is keyed to content exposed to natural persons.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 50']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (substantial detour into unrelated Article 50 provisions)

**branch — answer (1151 chars):**

```
Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties; both apply to the same system, not in the alternative. Transparency obligations split by actor: providers must ensure AI systems interacting with natural persons disclose their AI nature (Article 50(1)) and must mark synthetic AI-generated content in a machine-readable, detectable format (Article 50(2)); deployers must inform exposed persons when operating emotion-recognition or biometric-categorisation systems (Article 50(3)) and must label deepfakes as artificially generated or manipulated (Article 50(4)). Article 50(4) also requires deployers who use an AI system to generate or manipulate text published to inform the public on matters of public interest to disclose that the text was artificially generated or manipulated; this disclosure duty does not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for publishing it.
```

  - **ans_corr**: fail (Failed to apply provisions to the specific use case asked about)
  omission_detail: The answer fails to address the specific question about synthetic medical images used to augment training datasets. It does not explain that Article 50(2) marking obligation applies to the provider of the generative system, nor does it clarify that Article 50(4) deepfake labeling generally would not apply to purely internal training dataset use since that content is not exposed to natural persons.
  - **ref_corr**: pass (none)
  governing_refs: ['Article 50']
  - **cite_faith**: pass (none)
  - **ans_conc**: pass (substantial detour into unrelated Article 50 provisions)
