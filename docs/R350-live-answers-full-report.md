# Live-answers A/B — full results (81 rows)

Run: R350.2 full stack (Cohere rerank + KG candidates + query expansion + V2 prompt)
Checkpoint: dynamic-ab-r350-live-answers.json
Judge axes: NOT run on this population (judge sidecars cover the 84-row expert/graphrag/medtech set only)

Gold refs dropped (head-normalized): base 103 vs branch 110 across 57 rows

## 1. live_answers:la_q44

**Q:** What does Article 13 require for transparency?

- **gold refs**: Article 13
- **base refs**: Article 13
- **branch refs**: Article 13
- **base scores**: {"answer_chars": 844.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 1.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 844.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 1.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
Article 13 requires high-risk AI systems to be designed and developed so that their operation is sufficiently transparent to enable deployers to interpret the system's output and use it appropriately. An appropriate type and degree of transparency must be ensured with a view to achieving compliance with the relevant obligations of both the provider and the deployer set out in the Regulation (Article 13(1)). High-risk AI systems must be accompanied by instructions for use in an appropriate digital format that include concise, complete, correct and clear information that is relevant, accessible and comprehensible to deployers, covering matters such as known or foreseeable circumstances that may lead to risks to health, safety or fundamental rights, and the level of accuracy, robustness and cybersecurity (Article 13(2), Article 13(3)).
```

**Branch answer:**

```
Article 13 requires high-risk AI systems to be designed and developed so that their operation is sufficiently transparent to enable deployers to interpret the system's output and use it appropriately. An appropriate type and degree of transparency must be ensured with a view to achieving compliance with the relevant obligations of both the provider and the deployer set out in the Regulation (Article 13(1)). High-risk AI systems must be accompanied by instructions for use in an appropriate digital format that include concise, complete, correct and clear information that is relevant, accessible and comprehensible to deployers, covering matters such as known or foreseeable circumstances that may lead to risks to health, safety or fundamental rights, and the level of accuracy, robustness and cybersecurity (Article 13(2), Article 13(3)).
```

## 2. live_answers:la_q87 🚫 VETO

**Q:** A clinical-trial sponsor uses AI to select and recruit eligible patients. Is this automatically high-risk under the EU AI Act?

- **gold refs**: Annex I, Annex III, Article 5, Article 50, Article 6
- **base refs**: Article 6.1, Article 50.1, Annex III.4.a, Annex I  — DROPPED: Annex III, Article 5, Article 50, Article 6
- **branch refs**: Article 6.1, Article 6.2, Annex III.4.a, Annex I  — DROPPED: Annex III, Article 5, Article 50, Article 6
- **base scores**: {"answer_chars": 944.0, "gold_dropped_exact": 4.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 4.0, "ref_conc": 0.6400000000000001, "ref_loose": 0.8, "ref_strict": 0.888888888888889}
- **branch scores**: {"answer_chars": 1242.0, "gold_dropped_exact": 4.0, "gold_dropped_head": 2.0, "kw_recall": 0.6666666666666666, "n_refs": 4.0, "ref_conc": 0.36, "ref_loose": 0.6, "ref_strict": 0.7499999999999999}

**Base answer:**

```
Not automatically high-risk. An AI system used by a clinical-trial sponsor to select and recruit eligible patients is not listed in Annex III(4)(a), which covers recruitment or selection of natural persons specifically in the employment context, not clinical-trial participant recruitment. The system would be high-risk under Article 6(1) only where it is itself a product, or a safety component of a product, covered by the Union harmonisation legislation listed in Annex I and that product is required to undergo third-party conformity assessment under that legislation, which could arise if the system qualifies as a medical device under the Medical Devices Regulation (the analysis of that instrument falls outside this scope). Absent either route, the system carries the Article 50(1) transparency obligation where it interacts directly with natural persons, requiring that those persons be informed they are interacting with an AI system.
```

**Branch answer:**

```
Not automatically high-risk. An AI system used by a clinical-trial sponsor to select and recruit eligible patients is high-risk only where it falls within one of the two classification routes in Article 6. Under Article 6(1), the system would be high-risk if it is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I (such as a medical device under the MDR) and that product must undergo third-party conformity assessment. Under Article 6(2), the system would be high-risk if it falls within an Annex III use case; Annex III(4)(a) covers AI systems intended to be used for the recruitment or selection of natural persons, but that category addresses employment recruitment, not the selection of research participants for a clinical trial, which is a distinct activity. Because clinical-trial patient recruitment is neither an employment relationship nor one of the other listed Annex III use cases, the system does not engage Article 6(2) on its face. If, however, the system qualifies as a medical device requiring third-party conformity assessment under the MDR (which falls outside the scope of this answer to interpret), it would be high-risk via Article 6(1) read with Annex I.
```

## 3. live_answers:la_q76 🚫 VETO

**Q:** What logging and record-keeping does a high-risk AI radiology system require, and how long must the deploying hospital keep the logs?

- **gold refs**: Article 12, Article 26
- **base refs**: Article 12.3, Article 19, Article 18  — DROPPED: Article 12, Article 26
- **branch refs**: Article 12, Article 26.6, Article 19  — DROPPED: Article 26
- **base scores**: {"answer_chars": 1267.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.5, "ref_strict": 0.4}
- **branch scores**: {"answer_chars": 839.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 1.0, "ref_strict": 0.8}

**Base answer:**

```
The provider must design the high-risk system so that it technically allows automatic recording of events (logs) over its lifetime, with logging capabilities that enable recording of events relevant to identifying situations presenting a risk or a substantial modification, facilitating post-market monitoring, and monitoring operation, as required by Article 12. The provider must keep those automatically generated logs for a period appropriate to the intended purpose, of at least six months unless Union or national law provides otherwise (Article 19). The deploying hospital, as deployer, must likewise keep the logs automatically generated by the system, to the extent such logs are under its control, for a period appropriate to the intended purpose of at least six months unless applicable Union or national law, in particular Union law on the protection of personal data, provides otherwise (Article 26(6) supplies this deployer-side duty, but as it is not in the citable list, the obligation is stated here from the provider-facing Article 12(3) minimum). The provider must also retain the technical documentation, quality management system documentation, and EU declaration of conformity for ten years after the system is placed on the market (Article 18).
```

**Branch answer:**

```
The provider must design the high-risk radiology system to allow automatic recording of events (logs) over its lifetime, with logging capabilities that enable recording of events relevant to identifying risks, facilitating post-market monitoring, and monitoring operation, at a level of traceability appropriate to the intended purpose (Article 12). The provider must keep those automatically generated logs for a period appropriate to the intended purpose, at a minimum of six months, unless Union or national law provides otherwise (Article 19). The deploying hospital, as deployer, must keep the logs automatically generated by the system, to the extent such logs are under its control, for a period appropriate to the intended purpose, of at least six months, unless applicable Union or national law provides otherwise (Article 26(6)).
```

## 4. live_answers:la_q5

**Q:** Does the EU AI Act explicitly requires to use explainable AI techniques such as LIME or SHAP to increase the trustworthiness of high-risk AI systems?

- **gold refs**: Article 13
- **base refs**: Article 13, Article 14, Article 15
- **branch refs**: Article 13, Article 14, Article 15
- **base scores**: {"answer_chars": 441.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 3.0, "ref_conc": 0.1111111111111111, "ref_loose": 1.0, "ref_strict": 0.5}
- **branch scores**: {"answer_chars": 441.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 3.0, "ref_conc": 0.1111111111111111, "ref_loose": 1.0, "ref_strict": 0.5}

**Base answer:**

```
No, the EU AI Act mandates no specific explainable-AI technique such as LIME or SHAP, and Article 13 instead requires only that high-risk AI systems be sufficiently transparent for deployers to interpret their output. Article 14 requires effective human oversight, and Article 15 requires appropriate accuracy, robustness and cybersecurity. The Act is technique-agnostic, so the choice of any interpretability method is left to the provider.
```

**Branch answer:**

```
No, the EU AI Act mandates no specific explainable-AI technique such as LIME or SHAP, and Article 13 instead requires only that high-risk AI systems be sufficiently transparent for deployers to interpret their output. Article 14 requires effective human oversight, and Article 15 requires appropriate accuracy, robustness and cybersecurity. The Act is technique-agnostic, so the choice of any interpretability method is left to the provider.
```

## 5. live_answers:la_q47

**Q:** Explain the risk categories in the EU AI Act

- **gold refs**: Article 5
- **base refs**: Article 6, Article 5, Article 50, Article 51, Article 52, Annex I, Annex III, Article 53, Article 54, Article 55, Article 56
- **branch refs**: Article 6, Article 5, Article 50, Article 51, Article 52, Annex I, Annex III, Article 53, Article 54, Article 55, Article 56
- **base scores**: {"answer_chars": 621.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 11.0, "ref_conc": 0.008264462809917356, "ref_loose": 1.0, "ref_strict": 0.16666666666666669}
- **branch scores**: {"answer_chars": 621.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 11.0, "ref_conc": 0.008264462809917356, "ref_loose": 1.0, "ref_strict": 0.16666666666666669}

**Base answer:**

```
The EU AI Act sets four risk tiers plus a separate regime for general-purpose AI models: unacceptable-risk practices are prohibited under Article 5; and high-risk systems are classified under Article 6 (an Annex I product safety component, or an Annex III use case) and carry the Chapter III Section 2 obligations. Limited-risk systems carry the Article 50 transparency duties, minimal-risk systems have no mandatory duties under the Act, and general-purpose AI models are governed separately under Articles 51 to 56, with added obligations under Article 55 for models classified as having systemic risk under Article 51.
```

**Branch answer:**

```
The EU AI Act sets four risk tiers plus a separate regime for general-purpose AI models: unacceptable-risk practices are prohibited under Article 5; and high-risk systems are classified under Article 6 (an Annex I product safety component, or an Annex III use case) and carry the Chapter III Section 2 obligations. Limited-risk systems carry the Article 50 transparency duties, minimal-risk systems have no mandatory duties under the Act, and general-purpose AI models are governed separately under Articles 51 to 56, with added obligations under Article 55 for models classified as having systemic risk under Article 51.
```

## 6. live_answers:la_q74 🚫 VETO

**Q:** What human-oversight measures does the EU AI Act require for a high-risk clinical decision-support system?

- **gold refs**: Article 13, Article 14
- **base refs**: Article 14.3, Article 14.4, Article 26.2  — DROPPED: Article 13, Article 14
- **branch refs**: Article 14.4, Article 14.2, Article 26  — DROPPED: Article 13, Article 14
- **base scores**: {"answer_chars": 1462.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 0.5, "ref_strict": 0.5}
- **branch scores**: {"answer_chars": 1942.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 0.5, "ref_strict": 0.5}

**Base answer:**

```
Article 14 is the operative provision. It requires that a high-risk clinical decision-support system be designed so that natural persons can effectively oversee it during use, through measures identified and built into the system by the provider before placing it on the market, or measures appropriate to be implemented by the deployer, or both (Article 14(3)). Specifically, the oversight measures must enable the assigned persons to properly understand the system's capacities and limitations and monitor its operation including detecting anomalies, to remain aware of automation bias (particularly relevant where the system provides information or recommendations for clinical decisions), to correctly interpret the system's output using available interpretation tools, to decide not to use the system or to disregard, override or reverse its output in any particular situation, and to intervene in or interrupt the system through a stop button or similar procedure allowing it to halt safely (Article 14(4)). The deployer must assign human oversight to natural persons who have the necessary competence, training and authority (Article 26(2)). The provider must document the human oversight measures in the instructions for use, including the technical measures put in place to facilitate interpretation of outputs by deployers (Article 13(3)(d)), and the technical documentation must contain an assessment of the human oversight measures needed (Annex IV).
```

**Branch answer:**

```
Article 14 requires that a high-risk clinical decision-support system be designed so that natural persons can effectively oversee it during use, with oversight measures commensurate with the risks, level of autonomy and context of use, ensured through measures built into the system by the provider, measures to be implemented by the deployer, or both. Specifically, Article 14(4) requires that the oversight persons be enabled to properly understand the system's capacities and limitations and monitor its operation including detecting anomalies, to remain aware of automation bias (particularly relevant where the system provides information or recommendations for decisions taken by natural persons), to correctly interpret the system's output using available interpretation tools and methods, to decide not to use the system or to disregard, override or reverse its output in any particular situation, and to intervene in or interrupt the system through a stop button or similar procedure allowing it to halt safely. Article 14(2) specifies that human oversight shall aim to prevent or minimise risks to health, safety or fundamental rights, including where such risks persist despite other requirements being met. On the deployer side, Article 26(2) requires the deployer to assign human oversight to natural persons who have the necessary competence, training and authority, as well as the necessary support. Article 26(1) requires the deployer to take appropriate technical and organisational measures to use the system in accordance with the instructions for use. Article 26(5) requires the deployer to monitor the system's operation on the basis of those instructions and to inform the provider of serious incidents. Article 13(3)(d) requires the provider's instructions for use to describe the human oversight measures, including the technical measures put in place to facilitate interpretation of the system's outputs by deployers.
```

## 7. live_answers:la_q83 🚫 VETO

**Q:** Is an AI system used for biometric patient identification at hospital check-in high-risk under the EU AI Act?

- **gold refs**: Annex III, Article 6
- **base refs**: Article 6.2, Article 6.1, Article 50.1, Annex III, Annex I  — DROPPED: Article 6
- **branch refs**: Annex I, Article 6.2, Article 6.1, Article 50.1, Annex III  — DROPPED: Article 6
- **base scores**: {"answer_chars": 1174.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 5.0, "ref_conc": 0.25, "ref_loose": 1.0, "ref_strict": 0.6666666666666666}
- **branch scores**: {"answer_chars": 938.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 5.0, "ref_conc": 0.25, "ref_loose": 1.0, "ref_strict": 0.6666666666666666}

**Base answer:**

```
Not high-risk unless the system qualifies as a remote biometric identification system or falls within the medical-device route. Annex III(1)(a) lists remote biometric identification systems as high-risk under Article 6(2), but expressly excludes biometric verification whose sole purpose is to confirm that a specific natural person is the person he or she claims to be. A hospital check-in system that merely verifies a patient's claimed identity against their own enrolled template is biometric verification and falls outside that listing. If, however, the system identifies patients from a database without prior claim of identity, it is a remote biometric identification system and is high-risk under Article 6(2) read with Annex III(1)(a). Separately, where the system is itself a medical device or a safety component of one that must undergo third-party conformity assessment under the Medical Devices Regulation listed in Annex I, it is high-risk under Article 6(1). Where neither route applies, the system carries only the Article 50(1) transparency obligation requiring the provider to design it so that patients are informed they are interacting with an AI system.
```

**Branch answer:**

```
Not high-risk unless the system qualifies as a product, or is a safety component of a product, covered by the Union harmonisation legislation listed in Annex I that must undergo third-party conformity assessment. A biometric system used solely to confirm that a patient is the person they claim to be is biometric verification, which Annex III(1)(a) explicitly excludes from the remote biometric identification use case listed there. The system therefore does not fall within Annex III and is not high-risk under Article 6(2). It could be high-risk under Article 6(1) if it is itself a medical device, or a safety component of one, that requires third-party conformity assessment under the Medical Devices Regulation listed in Annex I, but absent that condition it remains outside the high-risk tier and carries only the Article 50(1) provider obligation to ensure that natural persons are informed they are interacting with an AI system.
```

## 8. live_answers:la_q8 🚫 VETO

**Q:** Are AI safety components within medical devices of MDR class IIa, IIb, or III considered to be high-risk according to the EU AI Act? Why?

- **gold refs**: Annex I, Annex III, Article 43, Article 6
- **base refs**: Article 6.1, Annex I  — DROPPED: Annex III, Article 43, Article 6
- **branch refs**: Article 6.1, Annex I  — DROPPED: Annex III, Article 43, Article 6
- **base scores**: {"answer_chars": 921.0, "gold_dropped_exact": 3.0, "gold_dropped_head": 2.0, "kw_recall": 1.0, "n_refs": 2.0, "ref_conc": 0.25, "ref_loose": 0.5, "ref_strict": 0.6666666666666666}
- **branch scores**: {"answer_chars": 891.0, "gold_dropped_exact": 3.0, "gold_dropped_head": 2.0, "kw_recall": 1.0, "n_refs": 2.0, "ref_conc": 0.25, "ref_loose": 0.5, "ref_strict": 0.6666666666666666}

**Base answer:**

```
AI safety components within medical devices of MDR class IIa, IIb or III are high-risk. Article 6(1) classifies an AI system as high-risk where two cumulative conditions are met: the AI system is intended to be used as a safety component of a product, or is itself a product, covered by the Union harmonisation legislation listed in Annex I, and that product is required to undergo a third-party conformity assessment under that legislation. Annex I lists Regulation (EU) 2017/745 on medical devices, and under that Regulation medical devices of classes IIa, IIb and III must undergo third-party conformity assessment involving a notified body, so both conditions are fulfilled. For such systems, Article 43(3) requires the provider to follow the conformity assessment procedure laid down in the Medical Devices Regulation itself, with the Chapter III Section 2 requirements of the AI Act forming part of that assessment.
```

**Branch answer:**

```
AI safety components within medical devices of MDR class IIa, IIb or III are high-risk. Article 6(1) classifies an AI system as high-risk where two cumulative conditions are met: the AI system is intended to be used as a safety component of a product, or is itself a product, covered by the Union harmonisation legislation listed in Annex I, and that product is required to undergo a third-party conformity assessment under that legislation. Annex I lists Regulation (EU) 2017/745 on medical devices, and under that Regulation medical devices of classes IIa, IIb and III must undergo third-party conformity assessment involving a notified body, so both conditions are fulfilled. For such systems, Article 43(3) requires the provider to follow the conformity assessment procedure of the sectoral legislation itself, with the Chapter III Section 2 requirements forming part of that assessment.
```

## 9. live_answers:la_q64 🚫 VETO

**Q:** Is AI software that detects melanoma from dermoscopy images a high-risk AI system under the EU AI Act?

- **gold refs**: Annex I, Annex III, Article 6
- **base refs**: Article 6.1, Annex I, Article 43.3  — DROPPED: Annex III, Article 6
- **branch refs**: Article 6.1, Annex I, Article 43.3  — DROPPED: Annex III, Article 6
- **base scores**: {"answer_chars": 705.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 1.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 0.6666666666666666, "ref_strict": 0.6666666666666666}
- **branch scores**: {"answer_chars": 705.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 1.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 0.6666666666666666, "ref_strict": 0.6666666666666666}

**Base answer:**

```
High-risk where the software qualifies as a medical device that must undergo third-party conformity assessment. AI software that detects melanoma from dermoscopy images is itself a product covered by Regulation (EU) 2017/745 on medical devices, which is listed in Annex I, and such diagnostic software is typically classified as a higher-risk medical device requiring third-party conformity assessment by a notified body under that regulation, thereby satisfying both cumulative conditions of Article 6(1). Under Article 43(3), the provider follows the conformity assessment procedure required by the medical devices regulation, with the Chapter III Section 2 requirements forming part of that assessment.
```

**Branch answer:**

```
High-risk where the software qualifies as a medical device that must undergo third-party conformity assessment. AI software that detects melanoma from dermoscopy images is itself a product covered by Regulation (EU) 2017/745 on medical devices, which is listed in Annex I, and such diagnostic software is typically classified as a higher-risk medical device requiring third-party conformity assessment by a notified body under that regulation, thereby satisfying both cumulative conditions of Article 6(1). Under Article 43(3), the provider follows the conformity assessment procedure required by the medical devices regulation, with the Chapter III Section 2 requirements forming part of that assessment.
```

## 10. live_answers:la_q88

**Q:** What penalties can be imposed on a medical-AI provider that places a non-conformant high-risk system on the market?

- **gold refs**: Article 99
- **base refs**: Article 99
- **branch refs**: Article 99
- **base scores**: {"answer_chars": 612.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 1.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 612.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 1.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
For high-risk AI systems the applicable penalty ceiling is set by Article 99(4): administrative fines of up to EUR 15 000 000 or, for an undertaking, up to 3 % of total worldwide annual turnover, whichever is higher, for non-compliance with the obligations on providers, deployers, importers and distributors (every obligation other than the Article 5 prohibitions, which carry the higher Article 99(3) ceiling of EUR 35 000 000 or 7 %). Under Article 99(6), for SMEs and start-ups each fine is capped at the lower of the percentage or the fixed amount. Penalties must be effective, proportionate and dissuasive.
```

**Branch answer:**

```
For high-risk AI systems the applicable penalty ceiling is set by Article 99(4): administrative fines of up to EUR 15 000 000 or, for an undertaking, up to 3 % of total worldwide annual turnover, whichever is higher, for non-compliance with the obligations on providers, deployers, importers and distributors (every obligation other than the Article 5 prohibitions, which carry the higher Article 99(3) ceiling of EUR 35 000 000 or 7 %). Under Article 99(6), for SMEs and start-ups each fine is capped at the lower of the percentage or the fixed amount. Penalties must be effective, proportionate and dissuasive.
```

## 11. live_answers:la_q16 🚫 VETO

**Q:** What are the administrative fines for non-compliance with the prohibition of the AI practices?

- **gold refs**: Article 5, Article 50, Article 99
- **base refs**: Article 99, Article 5  — DROPPED: Article 50
- **branch refs**: Article 99.3, Article 99.6, Article 5  — DROPPED: Article 50, Article 99
- **base scores**: {"answer_chars": 481.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 1.0, "n_refs": 2.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.6666666666666666, "ref_strict": 0.8}
- **branch scores**: {"answer_chars": 466.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 1.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.6666666666666666, "ref_strict": 0.8}

**Base answer:**

```
Non-compliance with the prohibited AI practices listed in Article 5 is subject to administrative fines of up to EUR 35 000 000 or, if the offender is an undertaking, up to 7 % of its total worldwide annual turnover for the preceding financial year, whichever is higher (Article 99(3)). For SMEs including start-ups, the applicable ceiling is the lower of the percentage or the fixed amount (Article 99(6)). Penalties must be effective, proportionate and dissuasive (Article 99(1)).
```

**Branch answer:**

```
Non-compliance with the prohibited AI practices listed in Article 5 is subject to administrative fines of up to EUR 35 000 000 or, if the offender is an undertaking, up to 7 % of its total worldwide annual turnover for the preceding financial year, whichever is higher (Article 99(3)). Penalties must be effective, proportionate and dissuasive. For SMEs, including start-ups, the applicable ceiling is the lower of the percentage or the fixed amount (Article 99(6)).
```

## 12. live_answers:la_q14 🚫 VETO

**Q:** Which AI systems used in education or vocational training should be classified as high-risk according to the EU AI Act?

- **gold refs**: Annex III, Article 49, Article 6
- **base refs**: Annex III.3, Article 6.2, Article 6.3  — DROPPED: Annex III, Article 49, Article 6
- **branch refs**: Annex III.3, Article 6.2, Article 6.3  — DROPPED: Annex III, Article 49, Article 6
- **base scores**: {"answer_chars": 1104.0, "gold_dropped_exact": 3.0, "gold_dropped_head": 1.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.6666666666666666, "ref_strict": 0.8}
- **branch scores**: {"answer_chars": 1110.0, "gold_dropped_exact": 3.0, "gold_dropped_head": 1.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.6666666666666666, "ref_strict": 0.8}

**Base answer:**

```
Under Annex III(3), AI systems in education and vocational training are classified as high-risk where they are intended to be used to determine access or admission or to assign natural persons to educational and vocational training institutions at all levels, to evaluate learning outcomes including when those outcomes steer the learning process, to assess the appropriate level of education an individual will receive or be able to access, or to monitor and detect prohibited behaviour of students during tests. Article 6(2) is the operative classification rule making all Annex III use cases high-risk. Under Article 6(3), an Annex III education system is not high-risk where it does not pose a significant risk of harm to health, safety or fundamental rights and performs one of four tasks (a narrow procedural task, improving the result of a previously completed human activity, detecting decision-making patterns without replacing or influencing the human assessment, or a preparatory task), but a system that performs profiling of natural persons is always high-risk regardless of that derogation.
```

**Branch answer:**

```
Under Annex III(3), AI systems in education and vocational training are classified as high-risk where they are intended to be used to determine access or admission or to assign natural persons to educational and vocational training institutions at all levels, to evaluate learning outcomes including when those outcomes steer the learning process, to assess the appropriate level of education an individual will receive or be able to access, or to monitor and detect prohibited behaviour of students during tests. Article 6(2) is the provision that classifies systems falling within Annex III as high-risk. Under Article 6(3), an Annex III education system is nevertheless not high-risk where it does not pose a significant risk of harm to health, safety or fundamental rights and performs only a narrow procedural task, improves the result of a previously completed human activity, detects decision-making patterns without replacing or influencing the human assessment, or performs a preparatory task, but a system that performs profiling of natural persons is always high-risk regardless of those conditions.
```

## 13. live_answers:la_q20 🚫 VETO

**Q:** Should market surveilance authorities be provided with remote access to documentations and data sets used to develop a high-risk AI system?

- **gold refs**: Article 16, Article 26
- **base refs**: Article 74, Article 16, Article 26
- **branch refs**: Article 74.12, Article 78  — DROPPED: Article 16, Article 26
- **base scores**: {"answer_chars": 666.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 1.0, "ref_strict": 0.8}
- **branch scores**: {"answer_chars": 760.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.6666666666666666, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 0.0, "ref_strict": 0.0}

**Base answer:**

```
Yes. Under Article 16(k), the provider of a high-risk AI system must, upon a reasoned request of a national competent authority, demonstrate the conformity of the system with the Chapter III Section 2 requirements. Article 26 further obliges deployers to cooperate with market surveillance authorities. The Regulation does not, however, expressly mandate that providers grant market surveillance authorities standing remote access to documentation and data sets as a matter of system design. What it requires is that the provider keep the technical documentation (Article 16(d)) and make it available to demonstrate conformity when a competent authority requests it.
```

**Branch answer:**

```
Yes. Article 74(12) requires that market surveillance authorities be granted full access by providers to the documentation as well as the training, validation and testing data sets used for the development of high-risk AI systems, including, where appropriate and subject to security safeguards, through application programming interfaces or other relevant technical means and tools enabling remote access. This power is limited to what is necessary to fulfil their tasks. Article 78 imposes a confidentiality obligation on market surveillance authorities regarding the information and data so obtained, requiring them to protect intellectual property rights, confidential business information and trade secrets, and to delete data once it is no longer needed.
```

## 14. live_answers:la_q34 🚫 VETO

**Q:** Under the EU AI Act, what jurisdiction does the Court of Justice of the European Union have over Commission decisions fixing fines on providers of general-purpose AI models, and what can the Court do with the fine?

- **gold refs**: Article 101, Article 64, Article 99
- **base refs**: Article 101.5  — DROPPED: Article 101, Article 64, Article 99
- **branch refs**: Article 101.5  — DROPPED: Article 101, Article 64, Article 99
- **base scores**: {"answer_chars": 240.0, "gold_dropped_exact": 3.0, "gold_dropped_head": 2.0, "kw_recall": 1.0, "n_refs": 1.0, "ref_conc": 0.1111111111111111, "ref_loose": 0.3333333333333333, "ref_strict": 0.5}
- **branch scores**: {"answer_chars": 238.0, "gold_dropped_exact": 3.0, "gold_dropped_head": 2.0, "kw_recall": 1.0, "n_refs": 1.0, "ref_conc": 0.1111111111111111, "ref_loose": 0.3333333333333333, "ref_strict": 0.5}

**Base answer:**

```
Under Article 101(5), the Court of Justice of the European Union has unlimited jurisdiction to review Commission decisions fixing a fine on a provider of a general-purpose AI model. The Court may cancel, reduce or increase the fine imposed.
```

**Branch answer:**

```
Under Article 101(5), the Court of Justice of the European Union has unlimited jurisdiction to review Commission decisions fixing a fine on providers of general-purpose AI models. The Court may cancel, reduce or increase the fine imposed.
```

## 15. live_answers:la_q6 🚫 VETO

**Q:** Does the EU AI Act apply to AI systems or AI models or both?

- **gold refs**: Article 2, Article 3, Article 51
- **base refs**: Article 2, Article 3.1, Article 51  — DROPPED: Article 3
- **branch refs**: Article 2, Article 3.1, Article 51  — DROPPED: Article 3
- **base scores**: {"answer_chars": 594.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 594.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
The EU AI Act's core regime governs AI systems, defined in Article 3(1) and brought within scope by Article 2, through the risk-based tiers (prohibited practices under Article 5, high-risk systems under Article 6, and limited-risk transparency duties under Article 50). General-purpose AI models are regulated separately under Chapter V (Articles 51 to 56), are defined in Article 3(63), and carry their own provider obligations with additional duties for models posing systemic risk. The Regulation therefore applies to both AI systems and general-purpose AI models under two parallel regimes.
```

**Branch answer:**

```
The EU AI Act's core regime governs AI systems, defined in Article 3(1) and brought within scope by Article 2, through the risk-based tiers (prohibited practices under Article 5, high-risk systems under Article 6, and limited-risk transparency duties under Article 50). General-purpose AI models are regulated separately under Chapter V (Articles 51 to 56), are defined in Article 3(63), and carry their own provider obligations with additional duties for models posing systemic risk. The Regulation therefore applies to both AI systems and general-purpose AI models under two parallel regimes.
```

## 16. live_answers:la_q26 🚫 VETO

**Q:** If I have an AI system that is high-risk because listed in the use cases of Annex III, and change it to a different use case that is not in Annex I or III, does it stay high-risk due to its historical provenance?

- **gold refs**: Annex I, Annex III, Article 6
- **base refs**: Annex III, Annex I, Article 6.2  — DROPPED: Article 6
- **branch refs**: Annex III, Annex I, Article 6.2  — DROPPED: Article 6
- **base scores**: {"answer_chars": 701.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 701.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
No, the system does not remain high-risk by historical provenance. Under Article 6(2), an AI system is high-risk because it falls within one of the use cases listed in Annex III; if the system's intended purpose is changed to a use case that does not appear in Annex III and the system is also not a safety component of, or itself, a product requiring third-party conformity assessment under Annex I legislation per Article 6(1), neither classification route is satisfied and the system is not high-risk. The classification is determined by the system's current intended purpose at the time it is placed on the market or put into service, not by a prior classification under a former intended purpose.
```

**Branch answer:**

```
No, the system does not remain high-risk by historical provenance. Under Article 6(2), an AI system is high-risk because it falls within one of the use cases listed in Annex III; if the system's intended purpose is changed to a use case that does not appear in Annex III and the system is also not a safety component of, or itself, a product requiring third-party conformity assessment under Annex I legislation per Article 6(1), neither classification route is satisfied and the system is not high-risk. The classification is determined by the system's current intended purpose at the time it is placed on the market or put into service, not by a prior classification under a former intended purpose.
```

## 17. live_answers:la_q18 🚫 VETO

**Q:** Can the European Commission amend Annex III of the EU AI Act to add or modify use-cases classified as high-risk AI systems? Under what conditions?

- **gold refs**: Annex I, Annex III, Article 6, Article 7
- **base refs**: Article 6, Annex III  — DROPPED: Annex I, Article 7
- **branch refs**: Annex III, Article 6.6, Article 6.3, Article 97, Article 7  — DROPPED: Annex I, Article 6
- **base scores**: {"answer_chars": 1111.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.6666666666666666, "n_refs": 2.0, "ref_conc": 0.25, "ref_loose": 0.5, "ref_strict": 0.6666666666666666}
- **branch scores**: {"answer_chars": 1015.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 1.0, "kw_recall": 1.0, "n_refs": 5.0, "ref_conc": 1.0, "ref_loose": 0.75, "ref_strict": 0.75}

**Base answer:**

```
Yes, the Commission is empowered to amend Annex III by adding new high-risk use cases or modifying existing ones through delegated acts, under the conditions set out in Article 6(7). The Commission may adopt such a delegated act only where it identifies AI systems that present a risk of harm to health, safety or fundamental rights that is equivalent to or greater than the risk posed by the use cases already listed in Annex III, and it must take into account a set of criteria including the intended purpose of the system, the extent to which it has been used or is likely to be used, the nature and amount of data processed, the extent of autonomy of action, the severity and irreversibility of harm, and whether existing Union legislation provides effective redress. The Commission must consult the Board before adopting such a delegated act. Article 6(6) separately empowers the Commission to amend the derogation conditions in Article 6(3) by adding new conditions or modifying existing ones, where there is concrete and reliable evidence of Annex III systems that do not pose a significant risk of harm.
```

**Branch answer:**

```
Yes, the Commission is empowered to amend Annex III by adding new high-risk use cases or modifying existing ones through delegated acts, subject to specific substantive conditions. Article 6(6) grants the Commission the power to adopt delegated acts in accordance with Article 97 to amend the conditions under which an Annex III system may escape high-risk classification, but the power to amend Annex III itself, adding or removing use cases, is conferred separately by Article 7 (which is not among the citable provisions here but is the operative mechanism). Within the citable provisions, Article 6(6) empowers the Commission to adopt delegated acts to amend the derogation conditions in Article 6(3) by adding new conditions or modifying them, where there is concrete and reliable evidence that AI systems falling under Annex III do not pose a significant risk of harm to health, safety or fundamental rights. The Commission must consult the European Artificial Intelligence Board before exercising this power.
```

## 18. live_answers:la_q3 🚫 VETO

**Q:** When the intended use of an AI system is listed in Annex III of the EU AI Act, the AI system is automatically high-risk, isn't it? If not, can you explain when that is not the case?

- **gold refs**: Annex III, Article 49, Article 6
- **base refs**: Annex III, Article 6  — DROPPED: Article 49
- **branch refs**: Annex III, Article 6  — DROPPED: Article 49
- **base scores**: {"answer_chars": 946.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 2.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.6666666666666666, "ref_strict": 0.8}
- **branch scores**: {"answer_chars": 946.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 2.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.6666666666666666, "ref_strict": 0.8}

**Base answer:**

```
Not automatically. Article 6(2) provides that AI systems referred to in Annex III shall be considered high-risk, but Article 6(3) derogates from that rule where the system does not pose a significant risk of harm to health, safety or fundamental rights, including by not materially influencing the outcome of decision making, AND the system is intended to perform one of four tasks: a narrow procedural task, improving the result of a previously completed human activity, detecting decision-making patterns or deviations from prior patterns without replacing or influencing the previously completed human assessment, or a preparatory task to an assessment relevant for the Annex III use cases. However, a system that performs profiling of natural persons is always high-risk regardless of those conditions. A provider relying on this derogation must document its assessment before placing the system on the market and register under Article 6(4).
```

**Branch answer:**

```
Not automatically. Article 6(2) provides that AI systems referred to in Annex III shall be considered high-risk, but Article 6(3) derogates from that rule where the system does not pose a significant risk of harm to health, safety or fundamental rights, including by not materially influencing the outcome of decision making, AND the system is intended to perform one of four tasks: a narrow procedural task, improving the result of a previously completed human activity, detecting decision-making patterns or deviations from prior patterns without replacing or influencing the previously completed human assessment, or a preparatory task to an assessment relevant for the Annex III use cases. However, a system that performs profiling of natural persons is always high-risk regardless of those conditions. A provider relying on this derogation must document its assessment before placing the system on the market and register under Article 6(4).
```

## 19. live_answers:la_q15 🚫 VETO

**Q:** What obligations, if any, does the EU AI Act set in place for AI systems that interact directly with natural persons? What exceptions, if any, apply?

- **gold refs**: Article 50
- **base refs**: Article 50.1, Article 50.3  — DROPPED: Article 50
- **branch refs**: Article 50.1, Article 50.3  — DROPPED: Article 50
- **base scores**: {"answer_chars": 949.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 2434.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
Article 50(1) imposes the primary obligation: providers must design AI systems intended to interact directly with natural persons so that those persons are informed they are interacting with an AI system, unless this is obvious from the point of view of a reasonably well-informed, observant and circumspect natural person taking into account the circumstances and context of use. Two exceptions apply under Article 50(1): the obligation does not apply to AI systems authorised by law to detect, prevent, investigate or prosecute criminal offences, subject to appropriate safeguards for the rights and freedoms of third parties, but this exception is itself reversed where the system is available for the public to report a criminal offence. Article 50(5) further requires that the information be provided in a clear and distinguishable manner no later than the time of first interaction and in conformity with applicable accessibility requirements.
```

**Branch answer:**

```
The principal obligation for AI systems that interact directly with natural persons is set out in Article 50(1): the provider must design the system so that the natural person concerned is informed they are interacting with an AI system, unless this is obvious from the point of view of a reasonably well-informed, observant and circumspect person taking into account the circumstances and context of use. Article 50(2) adds that providers of AI systems generating synthetic audio, image, video or text content must ensure the outputs are marked in a machine-readable format as artificially generated or manipulated. On the deployer side, Article 50(3) requires deployers of emotion recognition or biometric categorisation systems to inform exposed natural persons of the system's operation, and Article 50(4) requires deployers of systems that generate deepfakes to disclose that the content is artificially generated or manipulated, and deployers of systems that generate or manipulate text published to inform the public on matters of public interest to disclose its artificial origin. Three categories of exception apply. First, the Article 50(1) provider disclosure duty does not apply to AI systems authorised by law to detect, prevent, investigate or prosecute criminal offences, subject to appropriate safeguards for the rights and freedoms of third parties, but this exception is itself reversed where the system is available to the public to report a criminal offence. Second, the Article 50(3) deployer duty does not apply to emotion recognition or biometric categorisation systems permitted by law to detect, prevent or investigate criminal offences, subject to appropriate safeguards and in accordance with Union law. Third, the Article 50(4) deepfake disclosure duty does not apply where the use is authorised by law for criminal-offence detection, prevention, investigation or prosecution, and where the content forms part of an evidently artistic, creative, satirical, fictional or analogous work the obligation is limited to a disclosure that does not hamper display or enjoyment of the work. The separate Article 50(4) duty on AI-generated text published on matters of public interest does not apply where the use is authorised by law for criminal-offence purposes, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for its publication.
```

## 20. live_answers:la_q12 🚫 VETO

**Q:** What are the high-risk uses of AI systems listed under 'Administration of justice and democratic processes' cited in the EU AI Act?

- **gold refs**: Annex III, Article 6
- **base refs**: Annex III.8  — DROPPED: Annex III, Article 6
- **branch refs**: Annex III.8  — DROPPED: Annex III, Article 6
- **base scores**: {"answer_chars": 691.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 1.0, "ref_conc": 0.25, "ref_loose": 0.5, "ref_strict": 0.6666666666666666}
- **branch scores**: {"answer_chars": 691.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 1.0, "ref_conc": 0.25, "ref_loose": 0.5, "ref_strict": 0.6666666666666666}

**Base answer:**

```
Annex III point 8 lists two high-risk use cases under administration of justice and democratic processes. Annex III point 8(a) covers AI systems intended to be used by a judicial authority, or on its behalf, to assist in researching and interpreting facts and the law and in applying the law to a concrete set of facts, or to be used similarly in alternative dispute resolution. Annex III point 8(b) covers AI systems intended to influence the outcome of an election or referendum, or the voting behaviour of natural persons in exercising their vote, with a carve-out for tools that only organise, optimise or structure political campaigns from an administrative or logistical point of view.
```

**Branch answer:**

```
Annex III point 8 lists two high-risk use cases under administration of justice and democratic processes. Annex III point 8(a) covers AI systems intended to be used by a judicial authority, or on its behalf, to assist in researching and interpreting facts and the law and in applying the law to a concrete set of facts, or to be used similarly in alternative dispute resolution. Annex III point 8(b) covers AI systems intended to influence the outcome of an election or referendum, or the voting behaviour of natural persons in exercising their vote, with a carve-out for tools that only organise, optimise or structure political campaigns from an administrative or logistical point of view.
```

## 21. live_answers:la_q41

**Q:** Under the EU AI Act, is there a simplified way for SMEs (including startups) to provide the technical documentation for high-risk AI systems, and who must accept it for conformity assessment?

- **gold refs**: Annex IV, Article 11
- **base refs**: Article 11.1, Article 11, Annex IV, Annex IV.2
- **branch refs**: Article 11.1, Article 11, Annex IV, Annex IV.2
- **base scores**: {"answer_chars": 362.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 4.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 362.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 4.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
Yes. Under Article 11(1), SMEs, including start-ups, may provide the technical documentation elements set out in Annex IV in a simplified manner, using a simplified form the Commission is required to establish for the needs of small and micro enterprises. Where an SME opts to use that form, the notified body performing the conformity assessment must accept it.
```

**Branch answer:**

```
Yes. Under Article 11(1), SMEs, including start-ups, may provide the technical documentation elements set out in Annex IV in a simplified manner, using a simplified form the Commission is required to establish for the needs of small and micro enterprises. Where an SME opts to use that form, the notified body performing the conformity assessment must accept it.
```

## 22. live_answers:la_q45 🚫 VETO

**Q:** What are the obligations of deployers of high-risk AI systems?

- **gold refs**: Annex III, Article 13, Article 26, Article 27
- **base refs**: Article 26, Article 27, Article 86, Annex III  — DROPPED: Article 13
- **branch refs**: Article 26, Article 27, Article 86, Annex III  — DROPPED: Article 13
- **base scores**: {"answer_chars": 1478.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 4.0, "ref_conc": 1.0, "ref_loose": 0.75, "ref_strict": 0.75}
- **branch scores**: {"answer_chars": 1395.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 4.0, "ref_conc": 1.0, "ref_loose": 0.75, "ref_strict": 0.75}

**Base answer:**

```
Deployers of high-risk AI systems must use the system in accordance with the provider's instructions for use, assign human oversight to natural persons who have the necessary competence and training, monitor the system's operation and inform the provider where a risk is identified, suspend use where the system may present a risk within the meaning of the Regulation, report serious incidents, ensure input data relevance and representativeness to the extent they control the input data, retain automatically generated logs, and inform affected natural persons that they are subject to the use of the system (Article 26). Deployers that are bodies governed by public law, private entities providing public services, or deployers of systems under Annex III points 5(b) and (c) must perform a fundamental rights impact assessment before first use, covering the deployment process, categories of affected persons, specific risks of harm, human oversight measures and mitigation arrangements, and must notify the market surveillance authority of the results (Article 27). Where the deployer makes decisions on the basis of output from an Annex III high-risk system that produce legal effects or similarly significantly affect a person adversely in their health, safety or fundamental rights, the affected person has the right to obtain clear and meaningful explanations of the system's role in the decision-making procedure and the main elements of the decision taken (Article 86).
```

**Branch answer:**

```
Deployers of high-risk AI systems must use the system in accordance with the provider's instructions for use, assign human oversight to natural persons who have the necessary competence and training, monitor the system's operation and inform the provider where relevant, ensure input data relevance and representativeness to the extent the deployer controls the input data, retain automatically generated logs, inform affected natural persons that they are subject to the use of the system, and inform workers and their representatives where the system is used in the workplace (Article 26). Where the deployer is a body governed by public law, a private entity providing public services, or a deployer of systems under Annex III points 5(b) and (c), it must perform a fundamental rights impact assessment before first use covering its processes, affected categories of persons, specific risks, human oversight measures and remedial arrangements, and notify the result to the market surveillance authority (Article 27). Any affected person subject to a deployer decision based on the output of an Annex III high-risk system, where that decision produces legal effects or similarly significantly affects health, safety or fundamental rights, has the right to obtain from the deployer clear and meaningful explanations of the system's role and the main elements of the decision taken (Article 86).
```

## 23. live_answers:la_q42

**Q:** Under the EU AI Act, must an employer inform affected workers and workers' representatives before putting into service or using a high-risk AI system in the workplace? If so, should possibly specific rules or procedures be followed to provide this information?

- **gold refs**: Article 26
- **base refs**: Article 26.7, Article 26
- **branch refs**: Article 26.7, Article 26
- **base scores**: {"answer_chars": 493.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 493.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
Yes. Under Article 26(7), a deployer that is an employer must, before putting a high-risk AI system into service or using it at the workplace, inform the workers' representatives and the affected workers that they will be subject to the use of that high-risk AI system. Under Article 26(7), that information must be provided, where applicable, in accordance with the rules and procedures laid down in Union and national law and practice on the information of workers and their representatives.
```

**Branch answer:**

```
Yes. Under Article 26(7), a deployer that is an employer must, before putting a high-risk AI system into service or using it at the workplace, inform the workers' representatives and the affected workers that they will be subject to the use of that high-risk AI system. Under Article 26(7), that information must be provided, where applicable, in accordance with the rules and procedures laid down in Union and national law and practice on the information of workers and their representatives.
```

## 24. live_answers:la_q33 🚫 VETO

**Q:** Regarding the European Artificial Intelligence Board: (1) Who designates its members? (2) How long is the term? How many times is the term renewable? (3) must members represent stakeholder interests or act impartially/objectively? (4) what voting threshold is required to adopt the Board's rules of procedure (is a simple 50%+1 majority enough)?

- **gold refs**: Article 65, Article 67, Article 68
- **base refs**: Article 65  — DROPPED: Article 67, Article 68
- **branch refs**: Article 65  — DROPPED: Article 67, Article 68
- **base scores**: {"answer_chars": 508.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.6666666666666666, "n_refs": 1.0, "ref_conc": 0.1111111111111111, "ref_loose": 0.3333333333333333, "ref_strict": 0.5}
- **branch scores**: {"answer_chars": 508.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.6666666666666666, "n_refs": 1.0, "ref_conc": 0.1111111111111111, "ref_loose": 0.3333333333333333, "ref_strict": 0.5}

**Base answer:**

```
The European Artificial Intelligence Board (Article 65) has one representative per Member State, each serving a three-year term renewable once under Article 65(3). Under Article 65(4) each is their Member State's single contact point rather than an independent stakeholder appointee, while Article 65(7) requires the Board to safeguard the objectivity and impartiality of its activities. Its rules of procedure are adopted by a two-thirds majority under Article 65(5), so a simple majority is not sufficient.
```

**Branch answer:**

```
The European Artificial Intelligence Board (Article 65) has one representative per Member State, each serving a three-year term renewable once under Article 65(3). Under Article 65(4) each is their Member State's single contact point rather than an independent stakeholder appointee, while Article 65(7) requires the Board to safeguard the objectivity and impartiality of its activities. Its rules of procedure are adopted by a two-thirds majority under Article 65(5), so a simple majority is not sufficient.
```

## 25. live_answers:la_q79 🚫 VETO

**Q:** If a hospital fine-tunes an open-weight medical language model, when does it become a provider under the EU AI Act?

- **gold refs**: Article 25, Article 4, Article 50
- **base refs**: Article 25.1.b, Article 25.1.c, Article 6  — DROPPED: Article 25, Article 4, Article 50
- **branch refs**: Article 25.1, Article 25.3, Article 50, Article 4, Article 6.1  — DROPPED: Article 25
- **base scores**: {"answer_chars": 746.0, "gold_dropped_exact": 3.0, "gold_dropped_head": 2.0, "kw_recall": 0.3333333333333333, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.3333333333333333, "ref_strict": 0.4}
- **branch scores**: {"answer_chars": 1155.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 5.0, "ref_conc": 0.5625, "ref_loose": 1.0, "ref_strict": 0.8571428571428571}

**Base answer:**

```
A hospital becomes a provider when it makes a substantial modification to a high-risk AI system already placed on the market, or when it modifies the intended purpose of a system that was not high-risk so that it becomes high-risk. Under Article 25(1)(b), making a substantial modification to a high-risk AI system that has already been placed on the market triggers provider status. Under Article 25(1)(c), modifying the intended purpose of a non-high-risk system so that it becomes high-risk under Article 6 likewise triggers provider status. A fine-tune that does not amount to a substantial modification and does not change the intended purpose into a high-risk use case does not, by itself, make the hospital a provider under the Regulation.
```

**Branch answer:**

```
A hospital becomes a provider under Article 25(1) in any of three circumstances: it puts its name or trademark on a high-risk AI system already placed on the market, it makes a substantial modification to such a system so that it remains high-risk, or it modifies the intended purpose of a non-high-risk system so that it becomes high-risk. Fine-tuning an open-weight medical language model therefore triggers provider status where the fine-tuning constitutes a substantial modification to a high-risk system, or where it changes the intended purpose of a system that was not high-risk into one that is high-risk under Article 6. If the resulting system qualifies as a medical device requiring third-party conformity assessment under the Medical Device Regulation (listed in Annex I), it is high-risk under Article 6(1), and the hospital as product manufacturer assumes provider obligations under Article 25(3). Once provider status attaches, the hospital bears all provider obligations under Article 16, including the Article 50 transparency duties where the system interacts directly with natural persons, and the AI literacy obligation under Article 4.
```

## 26. live_answers:la_q30 🚫 VETO

**Q:** Under Regulation (EU) 2024/1689, as part of their supervisory role for an AI regulatory sandbox, compliance with which specific Article must the market surveillance authority verify?

- **gold refs**: Article 57, Article 74
- **base refs**: Article 57.7, Article 74  — DROPPED: Article 57
- **branch refs**: Article 78, Article 57, Article 74.14  — DROPPED: Article 74
- **base scores**: {"answer_chars": 948.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 1075.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 1.0, "ref_strict": 0.8}

**Base answer:**

```
The market surveillance authority, when acting in its supervisory role within an AI regulatory sandbox, must verify compliance with the requirements and obligations set out in the Regulation as a whole, since Article 57(7) states that competent authorities provide participants with guidance on how to fulfil "the requirements and obligations set out in this Regulation" and that exit reports and written proof are taken positively into account by market surveillance authorities with a view to accelerating conformity assessment procedures. Article 57 does not single out one specific Article for verification; rather, it frames the sandbox as a controlled environment in which the national competent authority supervises participants' adherence to the Regulation's applicable requirements generally, and Article 74 designates the market surveillance authorities with full investigation and corrective-measure powers to enforce those requirements.
```

**Branch answer:**

```
As part of their supervisory role for an AI regulatory sandbox, the market surveillance authority must verify compliance with Article 78, which requires market surveillance authorities to respect the confidentiality of information and data obtained in carrying out their tasks, protecting in particular intellectual property rights, confidential business information and trade secrets including source code, the effective implementation of the Regulation, public and national security interests, and the integrity of criminal or administrative proceedings. Article 74(14) confirms that any information or documentation obtained by market surveillance authorities shall be treated in accordance with the confidentiality obligations set out in Article 78. Article 57 establishes the sandbox framework within which the market surveillance authority operates, providing that exit reports and written proof from the national competent authority shall be taken positively into account by market surveillance authorities with a view to accelerating conformity assessment procedures.
```

## 27. live_answers:la_q25 🚫 VETO

**Q:** Can an operator that is not a provider according to the EU AI Act, for example a deployer, take actions on a given high-risk AI system such that it can be effectively seen as a provider by the authorities? If yes, what kind of action would result in such an outcome?

- **gold refs**: Annex III, Article 25, Article 26, Article 6
- **base refs**: Article 25.1, Article 25, Article 16  — DROPPED: Annex III, Article 26, Article 6
- **branch refs**: Article 25.1, Article 25, Article 16  — DROPPED: Annex III, Article 26, Article 6
- **base scores**: {"answer_chars": 785.0, "gold_dropped_exact": 3.0, "gold_dropped_head": 3.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 0.25, "ref_loose": 0.25, "ref_strict": 0.3333333333333333}
- **branch scores**: {"answer_chars": 785.0, "gold_dropped_exact": 3.0, "gold_dropped_head": 3.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 0.25, "ref_loose": 0.25, "ref_strict": 0.3333333333333333}

**Base answer:**

```
Yes. Under Article 25(1), a distributor, importer, deployer or other third party is deemed to be the provider of a high-risk AI system, and takes on the provider obligations in Article 16, in any of three cases. First, if it puts its name or trademark on a high-risk AI system already placed on the market (Article 25(1)(a)). Second, if it makes a substantial modification to a high-risk AI system that remains high-risk (Article 25(1)(b)). Third, if it modifies the intended purpose of an AI system, including a general-purpose AI system, so that it becomes high-risk (Article 25(1)(c)). In each of these three cases the operator assumes the provider obligations in Article 16, and the initial provider is no longer considered the provider of that specific system under Article 25(2).
```

**Branch answer:**

```
Yes. Under Article 25(1), a distributor, importer, deployer or other third party is deemed to be the provider of a high-risk AI system, and takes on the provider obligations in Article 16, in any of three cases. First, if it puts its name or trademark on a high-risk AI system already placed on the market (Article 25(1)(a)). Second, if it makes a substantial modification to a high-risk AI system that remains high-risk (Article 25(1)(b)). Third, if it modifies the intended purpose of an AI system, including a general-purpose AI system, so that it becomes high-risk (Article 25(1)(c)). In each of these three cases the operator assumes the provider obligations in Article 16, and the initial provider is no longer considered the provider of that specific system under Article 25(2).
```

## 28. live_answers:la_q39

**Q:** Under the EU AI Act, what transparency obligation applies to deployers when they use an AI system to generate or manipulate text for the purpose of informing the public on matters of public interest, and what are the two exceptions where this obligation does not apply?

- **gold refs**: Article 50
- **base refs**: Article 50.4, Article 50
- **branch refs**: Article 50.4, Article 50
- **base scores**: {"answer_chars": 600.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.0, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 600.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.0, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
Under Article 50(4), a deployer that uses an AI system to generate or manipulate text published to inform the public on matters of public interest must disclose that the text has been artificially generated or manipulated. Under Article 50(4), that disclosure duty does not apply in two cases: first, where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences; and second, where the AI-generated content has undergone a process of human review or editorial control and a natural or legal person holds editorial responsibility for the publication of the content.
```

**Branch answer:**

```
Under Article 50(4), a deployer that uses an AI system to generate or manipulate text published to inform the public on matters of public interest must disclose that the text has been artificially generated or manipulated. Under Article 50(4), that disclosure duty does not apply in two cases: first, where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences; and second, where the AI-generated content has undergone a process of human review or editorial control and a natural or legal person holds editorial responsibility for the publication of the content.
```

## 29. live_answers:la_q66 🚫 VETO

**Q:** Under the EU AI Act, is an AI system used to dispatch and triage emergency-room patients high-risk?

- **gold refs**: Annex III, Article 5, Article 6
- **base refs**: Article 5, Article 6.2, Annex III.5.d  — DROPPED: Annex III, Article 6
- **branch refs**: Article 5, Article 6.2, Annex III.5.d  — DROPPED: Annex III, Article 6
- **base scores**: {"answer_chars": 485.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 468.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
High-risk. An AI system used to dispatch and triage emergency-room patients falls squarely within Annex III(5)(d), which lists AI systems intended to evaluate and classify emergency calls, to dispatch or establish priority in the dispatching of emergency first response services, and emergency healthcare patient triage systems; Article 6(2) classifies all Annex III systems as high-risk. No prohibited practice under Article 5 is engaged by a triage or dispatch function of this kind.
```

**Branch answer:**

```
High-risk. An AI system used to dispatch and triage emergency-room patients falls within Annex III(5)(d), which covers AI systems intended to evaluate and classify emergency calls, to dispatch or establish priority in the dispatching of emergency first response services, and emergency healthcare patient triage systems; Article 6(2) classifies all Annex III systems as high-risk. No prohibited practice under Article 5 is engaged by this use case on its stated facts.
```

## 30. live_answers:la_q40 🚫 VETO

**Q:** Under the EU AI Act, when a high-risk AI system is found to conform with the requirements, what information must the Union technical documentation assessment certificate contain?

- **gold refs**: Annex IV, Article 11
- **base refs**: Annex VII  — DROPPED: Annex IV, Article 11
- **branch refs**: Annex VII  — DROPPED: Annex IV, Article 11
- **base scores**: {"answer_chars": 436.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.6666666666666666, "n_refs": 1.0, "ref_conc": 0.25, "ref_loose": 0.0, "ref_strict": 0.0}
- **branch scores**: {"answer_chars": 436.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.6666666666666666, "n_refs": 1.0, "ref_conc": 0.25, "ref_loose": 0.0, "ref_strict": 0.0}

**Base answer:**

```
Under Annex VII point 4.6, where the notified body finds the high-risk AI system conforms with the Chapter III Section 2 requirements, it issues a Union technical documentation assessment certificate. Per Annex VII point 4.6, that certificate must indicate the name and address of the provider, the conclusions of the examination, the conditions (if any) for its validity, and the data necessary for the identification of the AI system.
```

**Branch answer:**

```
Under Annex VII point 4.6, where the notified body finds the high-risk AI system conforms with the Chapter III Section 2 requirements, it issues a Union technical documentation assessment certificate. Per Annex VII point 4.6, that certificate must indicate the name and address of the provider, the conclusions of the examination, the conditions (if any) for its validity, and the data necessary for the identification of the AI system.
```

## 31. live_answers:la_q4 🚫 VETO

**Q:** I have a medical device that has an AI system as a safety component. The medical device is classified "medium-risk" and undergoes a 3rd party conformity assessment. Is the AI system "medium risk" too? If yes, why? If not, why not?

- **gold refs**: Annex I, Article 43, Article 6
- **base refs**: Article 6.1, Article 43.3, Annex I  — DROPPED: Article 43, Article 6
- **branch refs**: Article 6.1, Article 43.3, Annex I  — DROPPED: Article 43, Article 6
- **base scores**: {"answer_chars": 1106.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 980.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
The AI system is classified as high-risk under the EU AI Act, not "medium-risk." The Regulation does not use a "medium-risk" category. Under Article 6(1), an AI system is high-risk where both conditions are met: it is a safety component of a product covered by the Union harmonisation legislation listed in Annex I, and that product is required to undergo a third-party conformity assessment. The Medical Devices Regulation is listed in Annex I, and the facts state the device undergoes third-party conformity assessment, so both conditions are satisfied and the AI system is high-risk regardless of the device's own risk class under sectoral law. As to conformity assessment, Article 43(3) provides that for high-risk AI systems covered by the legislation in Section A of Annex I, the provider follows the relevant conformity assessment procedure required under that sectoral legislation, and the Chapter III Section 2 requirements of the AI Act form part of that same assessment. The result is a single integrated procedure conducted by the medical-device notified body, not a separate AI Act assessment.
```

**Branch answer:**

```
The AI system is high-risk, not "medium-risk." The EU AI Act does not use a "medium-risk" category. Under Article 6(1), an AI system is classified as high-risk where it is intended to be used as a safety component of a product covered by the Union harmonisation legislation listed in Annex I and that product is required to undergo a third-party conformity assessment. Medical devices are listed in Annex I, so an AI safety component of a medical device that undergoes third-party conformity assessment is high-risk regardless of the device's own risk class under sectoral legislation. As to conformity assessment, Article 43(3) provides that for high-risk AI systems covered by Section A of Annex I, the provider follows the relevant conformity assessment procedure required under that sectoral legislation, and the Chapter III Section 2 requirements of the AI Act form part of that same assessment, yielding a single integrated procedure conducted by the sectoral notified body.
```

## 32. live_answers:la_q68 🚫 VETO

**Q:** Are AI systems used solely for scientific biomedical research and not placed on the market subject to the EU AI Act?

- **gold refs**: Article 2
- **base refs**: Article 2.6, Article 2.1  — DROPPED: Article 2
- **branch refs**: Article 2.6  — DROPPED: Article 2
- **base scores**: {"answer_chars": 615.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 664.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 1.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
AI systems developed and put into service for the sole purpose of scientific research and development are not subject to the EU AI Act, as Article 2(6) explicitly excludes them from the Regulation's scope. This exclusion covers AI systems used solely for scientific biomedical research that are not placed on the market or put into service for any purpose beyond that research. The exclusion ceases to apply if the system is subsequently placed on the market or put into service for a non-research purpose, at which point the full Regulation applies according to the system's risk classification under Article 2(1).
```

**Branch answer:**

```
Article 2(6) excludes from the Regulation AI systems or AI models specifically developed and put into service for the sole purpose of scientific research and development. An AI system used solely for scientific biomedical research that is not placed on the market or put into service for any purpose beyond that research therefore falls outside the scope of the EU AI Act. The exclusion requires that the system be developed and used exclusively for scientific research and development; if the system were subsequently placed on the market or put into service for a non-research purpose, the exclusion would no longer apply and the full Regulation would govern it.
```

## 33. live_answers:la_q56

**Q:** What's the best restaurant in Rome?

- **gold refs**: (none)
- **base refs**: (none)
- **branch refs**: (none)
- **base scores**: {"answer_chars": 403.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.5, "n_refs": 0.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 280.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.5, "n_refs": 0.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
Rome has many incredible restaurants, but one consistently top-rated option is Roscioli, known for its exceptional Roman cuisine, high-quality ingredients, and a fantastic wine selection. For a more traditional experience, Trattoria Da Enzo al 29 in Trastevere is also highly recommended. Both offer authentic flavors in a charming setting. Would you like recommendations for a specific type of cuisine?
```

**Branch answer:**

```
One of the most highly praised restaurants in Rome is Roscioli, a historic deli‑restaurant near Campo de’ Fiori that blends traditional Roman dishes (like carbonara and cacio e pepe) with a superb wine list and upscale service. Reservations are recommended, especially for dinner.
```

## 34. live_answers:la_q24 🚫 VETO

**Q:** Are AI systems that fall under one of the areas of Annex III, but not falling within a use-case within such areas, considered high-risk?

- **gold refs**: Annex III, Article 6
- **base refs**: Annex III, Article 6.2, Article 6.3  — DROPPED: Article 6
- **branch refs**: Annex III, Article 6.2, Article 6.3  — DROPPED: Article 6
- **base scores**: {"answer_chars": 945.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 949.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
Not necessarily. Article 6(2) classifies as high-risk only AI systems "referred to in Annex III," meaning those that fall within one of the specific use cases enumerated under each of the eight areas. An AI system that operates in a domain covered by one of the eight Annex III areas but does not match any of the particular use cases listed within that area is not classified as high-risk under Article 6(2). Even where a system does fall within a listed use case, Article 6(3) provides that it is not high-risk where it does not pose a significant risk of harm to health, safety or fundamental rights and performs one of four tasks: a narrow procedural task, improving the result of a previously completed human activity, detecting decision-making patterns or deviations without replacing or influencing the human assessment, or a preparatory task, unless the system performs profiling of natural persons, in which case it is always high-risk.
```

**Branch answer:**

```
Not necessarily. Article 6(2) classifies as high-risk only AI systems "referred to in Annex III," meaning those that match a specific use case listed within one of the eight areas. An AI system that operates in a domain covered by one of the eight Annex III areas but does not fall within any of the particular use cases described therein is not classified as high-risk under Article 6(2). Additionally, even a system that does fall within an Annex III use case may escape high-risk classification under Article 6(3) where it does not pose a significant risk of harm to health, safety or fundamental rights and performs one of four tasks: a narrow procedural task, improving the result of a previously completed human activity, detecting decision-making patterns or deviations without replacing or influencing the human assessment, or a preparatory task, unless the system performs profiling of natural persons, in which case it is always high-risk.
```

## 35. live_answers:la_q85 🚫 VETO

**Q:** How does the EU AI Act interact with the Medical Device Regulation for AI medical-device software - which conformity route and timeline applies?

- **gold refs**: Annex I, Annex III, Annex VI, Annex VII, Article 43, Article 6
- **base refs**: Article 6.1, Annex I, Article 43.3  — DROPPED: Annex III, Annex VI, Annex VII, Article 43, Article 6
- **branch refs**: Article 6.1, Article 43.3, Annex I  — DROPPED: Annex III, Annex VI, Annex VII, Article 43, Article 6
- **base scores**: {"answer_chars": 872.0, "gold_dropped_exact": 5.0, "gold_dropped_head": 3.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 0.25, "ref_loose": 0.5, "ref_strict": 0.6666666666666666}
- **branch scores**: {"answer_chars": 1266.0, "gold_dropped_exact": 5.0, "gold_dropped_head": 3.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 0.25, "ref_loose": 0.5, "ref_strict": 0.6666666666666666}

**Base answer:**

```
AI software that is itself a medical device, or that serves as a safety component of one, is classified high-risk under Article 6(1) where the device must undergo third-party conformity assessment under the Medical Device Regulation (listed at point 11 of Annex I, Section A). Under Article 43(3), the provider follows the conformity assessment procedure required by the Medical Device Regulation rather than the internal-control route, and the Chapter III Section 2 requirements of the EU AI Act are integrated into that single sectoral assessment carried out by the notified body designated under that legislation. The result is one procedure and one CE marking covering both regimes. The Medical Device Regulation itself falls outside the scope of this answer, so its specific procedural steps and timelines are governed by that instrument rather than by the EU AI Act.
```

**Branch answer:**

```
AI software that is itself a medical device, or is a safety component of one, is classified as high-risk under Article 6(1) where the Medical Device Regulation requires that product to undergo a third-party conformity assessment, which it does for devices in risk class IIa and above. The conformity route is set by Article 43(3): the provider follows the Medical Device Regulation's own notified-body conformity assessment procedure, and the Chapter III Section 2 requirements of the AI Act (risk management, data governance, technical documentation, logging, transparency, human oversight, accuracy and cybersecurity) form part of that single assessment, yielding one CE marking. The notified body conducting the MDR assessment is entitled to control compliance with those AI Act requirements provided it meets the competence conditions in Article 43(3). The Medical Device Regulation itself falls outside the scope of this answer, but Annex I lists it as Union harmonisation legislation triggering the Article 6(1) route. As to timeline, the obligations for high-risk AI systems under the AI Act apply from 2 August 2026, so providers of AI medical-device software must integrate the AI Act requirements into their MDR conformity assessment from that date onward.
```

## 36. live_answers:la_q38 🚫 VETO

**Q:** Under the EU AI Act, what is an "AI regulatory sandbox"? Provide the definition elements (what it is, who sets it up, for whom it is intended, to do what, for how long).

- **gold refs**: Article 57, Article 62
- **base refs**: Article 3.55, Article 57, Article 1  — DROPPED: Article 62
- **branch refs**: Article 3.55, Article 57, Article 2  — DROPPED: Article 62
- **base scores**: {"answer_chars": 315.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.5, "ref_strict": 0.4}
- **branch scores**: {"answer_chars": 315.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.5, "ref_strict": 0.4}

**Base answer:**

```
A controlled framework set up by a competent authority which offers providers or prospective providers of AI systems the possibility to develop, train, validate and test, where appropriate in real-world conditions, an innovative AI system, pursuant to a sandbox plan for a limited time under regulatory supervision.
```

**Branch answer:**

```
A controlled framework set up by a competent authority which offers providers or prospective providers of AI systems the possibility to develop, train, validate and test, where appropriate in real-world conditions, an innovative AI system, pursuant to a sandbox plan for a limited time under regulatory supervision.
```

## 37. live_answers:la_q9 🚫 VETO

**Q:** What documentation does a provider of a high-risk AI system needs to keep available for the national competent authorities, and for how long?

- **gold refs**: Annex IV, Article 11, Article 17, Article 18, Article 47
- **base refs**: Article 18, Article 11, Article 17, Article 47, Article 19  — DROPPED: Annex IV
- **branch refs**: Article 18, Article 11, Article 17, Article 47, Article 19  — DROPPED: Annex IV
- **base scores**: {"answer_chars": 606.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 1.0, "n_refs": 5.0, "ref_conc": 1.0, "ref_loose": 0.8, "ref_strict": 0.8000000000000002}
- **branch scores**: {"answer_chars": 606.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 1.0, "n_refs": 5.0, "ref_conc": 1.0, "ref_loose": 0.8, "ref_strict": 0.8000000000000002}

**Base answer:**

```
Under Article 18, for ten years after the high-risk AI system is placed on the market or put into service, the provider must keep at the disposal of the national competent authorities the technical documentation (Article 11), the quality-management-system documentation (Article 17), the documentation of any changes approved by notified bodies, the decisions and other documents issued by notified bodies, and the EU declaration of conformity (Article 47). Separately, under Article 19 the automatically generated logs must be kept for a period appropriate to the intended purpose, of at least six months.
```

**Branch answer:**

```
Under Article 18, for ten years after the high-risk AI system is placed on the market or put into service, the provider must keep at the disposal of the national competent authorities the technical documentation (Article 11), the quality-management-system documentation (Article 17), the documentation of any changes approved by notified bodies, the decisions and other documents issued by notified bodies, and the EU declaration of conformity (Article 47). Separately, under Article 19 the automatically generated logs must be kept for a period appropriate to the intended purpose, of at least six months.
```

## 38. live_answers:la_q91 🚫 VETO

**Q:** What are the transparency rules for a Very Large Online Platform's content-moderation AI?

- **gold refs**: Article 50
- **base refs**: (none)  — DROPPED: Article 50
- **branch refs**: (none)  — DROPPED: Article 50
- **base scores**: {"answer_chars": 209.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.3333333333333333, "n_refs": 0.0, "ref_conc": 0.0, "ref_loose": 0.0, "ref_strict": 0.0}
- **branch scores**: {"answer_chars": 209.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.3333333333333333, "n_refs": 0.0, "ref_conc": 0.0, "ref_loose": 0.0, "ref_strict": 0.0}

**Base answer:**

```
This question is about the Digital Services Act (DSA), not the EU AI Act (Regulation 2024/1689). This assistant only covers EU AI Act questions; consult the Digital Services Act (DSA) for the applicable rules.
```

**Branch answer:**

```
This question is about the Digital Services Act (DSA), not the EU AI Act (Regulation 2024/1689). This assistant only covers EU AI Act questions; consult the Digital Services Act (DSA) for the applicable rules.
```

## 39. live_answers:la_q23 🚫 VETO

**Q:** Does "systemic risk" apply to AI systems or general purpose AI models or both?

- **gold refs**: Annex XIII, Article 51, Article 55
- **base refs**: Article 55, Article 51  — DROPPED: Annex XIII
- **branch refs**: Article 55, Article 53, Article 51  — DROPPED: Annex XIII
- **base scores**: {"answer_chars": 654.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 1.0, "n_refs": 2.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.6666666666666666, "ref_strict": 0.8}
- **branch scores**: {"answer_chars": 1293.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 0.6666666666666666, "ref_strict": 0.6666666666666666}

**Base answer:**

```
Systemic risk applies exclusively to general-purpose AI models, not to AI systems as such. Article 51 classifies a general-purpose AI model as having systemic risk where it has high-impact capabilities, presumed when cumulative training compute exceeds 10²⁵ floating-point operations, or where the Commission so designates it. Article 55 then imposes additional obligations on providers of such models, including model evaluation with adversarial testing, assessment and mitigation of possible systemic risks at Union level, serious incident reporting to the AI Office, and adequate cybersecurity protection for the model and its physical infrastructure.
```

**Branch answer:**

```
Under Article 53, GPAI providers must maintain Annex XI documentation, supply downstream-provider information, and publish a training-data summary; the Article 53(2) carve-out means each documentation obligation does not apply to free and open-source models below the systemic threshold. Under Article 51, a GPAI model has systemic risk when cumulative training compute exceeds 10²⁵ FLOPs (10^25); providers must notify the Commission within two weeks of meeting the threshold. Article 53(2) free / open-source carve-out: the Annex XI technical-documentation obligation and the Annex XII downstream-provider information obligation under Article 53(1)(a)-(b) do NOT apply to GPAI models released under a free and open-source licence permitting access, use, modification and distribution, with publicly available parameters (weights, architecture and usage information). The carve-out does NOT apply to GPAI models designated as systemic-risk under Article 51, once systemic-risk designation lands, the open-source carve-out is gone and the full Article 53 obligations plus the Article 55 systemic-risk obligations apply regardless of licence. The Article 53(1)(c) copyright policy and the Article 53(1)(d) public training-data summary apply to ALL GPAI providers including open-source releases.
```

## 40. live_answers:la_q28 🚫 VETO

**Q:** According to Article 1, what is the objective of the EU AI Act?

- **gold refs**: Article 1
- **base refs**: Article 1.2  — DROPPED: Article 1
- **branch refs**: Article 1
- **base scores**: {"answer_chars": 956.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 1.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 304.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.0, "n_refs": 1.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
Article 1 states that the purpose of the Regulation is to improve the functioning of the internal market and promote the uptake of human-centric and trustworthy AI, while ensuring a high level of protection of health, safety, and fundamental rights enshrined in the Charter, including democracy, the rule of law and environmental protection, against the harmful effects of AI systems in the Union, and supporting innovation. To that end, Article 1(2) lays down harmonised rules for the placing on the market, putting into service and use of AI systems, prohibitions of certain AI practices, specific requirements for high-risk AI systems and obligations for their operators, harmonised transparency rules for certain AI systems, harmonised rules for placing general-purpose AI models on the market, rules on market monitoring, surveillance, governance and enforcement, and measures to support innovation with a particular focus on SMEs including start-ups.
```

**Branch answer:**

```
Lays down harmonised rules for placing on the market, putting into service, and use of AI systems in the Union; sets prohibitions, high-risk requirements, transparency obligations, GPAI rules, and innovation-support measures to ensure a high level of protection of health, safety, and fundamental rights.
```

## 41. live_answers:la_q81 🚫 VETO

**Q:** Classify the EU AI Act risk tier of an AI ambient scribe that only transcribes doctor-patient consultations and performs no diagnosis or decision-making.

- **gold refs**: Annex III, Article 6
- **base refs**: Article 50, Article 6.1, Annex I  — DROPPED: Annex III, Article 6
- **branch refs**: Article 50, Article 6.1, Article 42, Article 49  — DROPPED: Annex III, Article 6
- **base scores**: {"answer_chars": 1150.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.5, "ref_strict": 0.4}
- **branch scores**: {"answer_chars": 559.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 1.0, "kw_recall": 0.3333333333333333, "n_refs": 4.0, "ref_conc": 0.25, "ref_loose": 0.5, "ref_strict": 0.3333333333333333}

**Base answer:**

```
Not high-risk, provided the system's intended purpose is limited to transcription with no diagnostic, triage or decision-making function. A pure ambient scribe does not fall within any Annex III use case because it neither evaluates eligibility for healthcare services on behalf of a public authority nor performs emergency patient triage, and it is not itself a medical device requiring third-party conformity assessment under the Medical Devices Regulation listed in Annex I. Even if the transcription were characterised as a preparatory task to a clinical assessment, Article 6(3) would apply to exclude it from high-risk classification, because a system that only transcribes does not materially influence the outcome of decision making, does not profile natural persons, and performs a preparatory task to a previously completed human activity. The provider relying on that derogation must document the assessment before placing the system on the market under Article 6(3). The system therefore falls in the minimal-risk tier, subject only to the general transparency obligation under Article 50 where it interacts directly with natural persons.
```

**Branch answer:**

```
Under Article 50, limited-risk transparency: AI systems interacting with natural persons must disclose AI nature; emotion-recognition and biometric-categorisation systems must inform exposed persons; deepfakes and AI-generated content must be labelled. Classifies an AI system as high-risk on two routes. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation.
```

## 42. live_answers:la_q51 🚫 VETO

**Q:** What should my company do to comply with AI rules in Europe?

- **gold refs**: Article 1, Article 10, Article 8, Article 9
- **base refs**: Article 1, Article 42, Article 8  — DROPPED: Article 10, Article 9
- **branch refs**: Article 42, Article 55, Article 16  — DROPPED: Article 1, Article 10, Article 8, Article 9
- **base scores**: {"answer_chars": 827.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 0.5625, "ref_loose": 0.5, "ref_strict": 0.5714285714285715}
- **branch scores**: {"answer_chars": 1628.0, "gold_dropped_exact": 4.0, "gold_dropped_head": 4.0, "kw_recall": 0.3333333333333333, "n_refs": 3.0, "ref_conc": 0.5625, "ref_loose": 0.0, "ref_strict": 0.0}

**Base answer:**

```
Adds two further presumptions of conformity beyond Articles 40-41: Article 42(1), high-risk AI systems trained and tested on data reflecting the specific geographical, behavioural, contextual, or functional setting in which they are intended to be used are presumed to comply with the relevant data-governance requirements of Article 10(4); Article 42(2), high-risk AI systems certified or for which a statement of conformity has been issued under a cybersecurity scheme under Regulation (EU) 2019/881 (the Cybersecurity Act) and whose references are published in the Official Journal are presumed to comply with the cybersecurity requirements of Article 15 to the extent the cybersecurity certificate or statement covers those requirements. Article 1 lays down harmonised rules for placing on the market, putting into service.
```

**Branch answer:**

```
Adds two further presumptions of conformity beyond Articles 40-41: Article 42(1), high-risk AI systems trained and tested on data reflecting the specific geographical, behavioural, contextual, or functional setting in which they are intended to be used are presumed to comply with the relevant data-governance requirements of Article 10(4); Article 42(2), high-risk AI systems certified or for which a statement of conformity has been issued under a cybersecurity scheme under Regulation (EU) 2019/881 (the Cybersecurity Act) and whose references are published in the Official Journal are presumed to comply with the cybersecurity requirements of Article 15 to the extent the cybersecurity certificate or statement covers those requirements. Article 55 adds four obligations on top of Article 53 for GPAI providers with systemic risk: (a) model evaluation in accordance with standardised protocols and tools reflecting the state of the art, including conducting and documenting adversarial testing to identify and mitigate systemic risks; (b) assess and mitigate possible systemic risks at Union level, including their sources, that may stem from development, market-placement, or use of the model; (c) keep track of, document, and report without undue delay to the AI Office (and national competent authorities where appropriate) information about serious incidents and possible corrective measures; (d) ensure an adequate level of cybersecurity protection for both the model AND its physical infrastructure. Providers may rely on Article 56 codes of practice to demonstrate compliance until a harmonised standard is published.
```

## 43. live_answers:la_q54 🚫 VETO

**Q:** Tell me about emotion recognition rules

- **gold refs**: Article 5
- **base refs**: Article 5.1.f  — DROPPED: Article 5
- **branch refs**: Article 5.1.f  — DROPPED: Article 5
- **base scores**: {"answer_chars": 850.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 1.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 1242.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 1.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
Under Article 5.1.f, emotion recognition in the workplace and in educational institutions is prohibited, including monitoring employees or call-centre agents, with a narrow medical/safety carve-out for systems placed on the market for therapeutic or accident-prevention purposes. Real-time remote biometric identification by law enforcement is prohibited under Article 5 save for narrow, exhaustively-listed law-enforcement exceptions that each require prior judicial or administrative authorisation; under Article 5(5) Member States may enable those exceptions in national law and may set stricter national rules. Article 5(1)(c) carve-out: the social-scoring prohibition does not affect lawful evaluation practices of natural persons that are carried out for a specific purpose in accordance with Union and national law (Recital 31 final sentence).
```

**Branch answer:**

```
Under Article 5.1.f, emotion recognition in the workplace and in educational institutions is prohibited, including monitoring employees or call-centre agents, with a narrow medical/safety carve-out for systems placed on the market for therapeutic or accident-prevention purposes. Transparency obligations split by actor: providers must ensure AI systems interacting with natural persons disclose their AI nature (Article 50(1)) and must mark synthetic AI-generated content in a machine-readable, detectable format (Article 50(2)); deployers must inform exposed persons when operating emotion-recognition or biometric-categorisation systems (Article 50(3)) and must label deepfakes as artificially generated or manipulated (Article 50(4)). Article 50(4) also requires deployers who use an AI system to generate or manipulate text published to inform the public on matters of public interest to disclose that the text was artificially generated or manipulated; this disclosure duty does not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for publishing it.
```

## 44. live_answers:la_q73 🚫 VETO

**Q:** What conformity-assessment route applies to an AI system that is a safety component of a CE-marked medical device?

- **gold refs**: Annex I, Article 6
- **base refs**: Article 43, Article 6, Annex I
- **branch refs**: Article 43, Article 6, Article 27, Article 49  — DROPPED: Annex I
- **base scores**: {"answer_chars": 345.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 1.0, "ref_strict": 0.8}
- **branch scores**: {"answer_chars": 718.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 4.0, "ref_conc": 0.25, "ref_loose": 0.5, "ref_strict": 0.3333333333333333}

**Base answer:**

```
Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation. Under Annex III, Eight high-risk use-case categories: biometrics, critical infrastructure.
```

**Branch answer:**

```
Under Article 27, in addition to Article 26 baseline duties, deployers of certain Annex III high-risk AI systems must perform a Fundamental Rights Impact Assessment (FRIA) covering affected persons and specific fundamental rights risks. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation. Article 49 requires providers (and deployers that are public authorities) to register themselves and their high-risk AI system in the EU database (Article 71) before placing the system on the market or putting it into service.
```

## 45. live_answers:la_q84 🚫 VETO

**Q:** An AI tool recommends oncology treatment regimens from clinical guidelines. What EU AI Act obligations does its provider face across the lifecycle?

- **gold refs**: Annex I, Annex III, Article 10, Article 13, Article 15, Article 16, Article 17, Article 19, Article 25, Article 49, Article 6, Article 9
- **base refs**: Article 15, Article 9, Article 16, Article 54, Article 96, Article 10, Article 13  — DROPPED: Annex I, Annex III, Article 17, Article 19, Article 25, Article 49, Article 6
- **branch refs**: Article 47, Article 16, Article 94, Article 71, Article 49, Article 80, Article 17  — DROPPED: Annex I, Annex III, Article 10, Article 13, Article 15, Article 19, Article 25, Article 6, Article 9
- **base scores**: {"answer_chars": 1398.0, "gold_dropped_exact": 7.0, "gold_dropped_head": 7.0, "kw_recall": 0.0, "n_refs": 7.0, "ref_conc": 0.34027777777777785, "ref_loose": 0.4166666666666667, "ref_strict": 0.5263157894736842}
- **branch scores**: {"answer_chars": 1675.0, "gold_dropped_exact": 9.0, "gold_dropped_head": 9.0, "kw_recall": 0.3333333333333333, "n_refs": 7.0, "ref_conc": 0.34027777777777785, "ref_loose": 0.25, "ref_strict": 0.3157894736842105}

**Base answer:**

```
Requires providers of GPAI models established outside the EU to appoint, by written mandate, an authorised representative established in the Union before placing the GPAI model on the market. Article 54 is the GPAI-specific authorised-representative regime and is distinct from Article 22, Article 22 applies to high-risk AI SYSTEMS, Article 54 applies to GPAI MODELS. The Article 54(3) mandate must empower the representative to (a) verify that the Article 53(1)(a) technical documentation and Annex XI information are drawn up and that Article 53 obligations have been complied with; (b) keep the documentation and contact details available for the AI Office and national competent authorities for 10 years; (c) provide the AI Office on reasoned request with all information and documentation necessary to demonstrate compliance with Chapter V; (d) cooperate with the AI Office and competent authorities. The representative must terminate the mandate and inform the AI Office where it has reason to believe the provider is acting contrary to its obligations. GPAI-with-systemic-risk providers face the same Article 54 obligation plus Article 55 systemic obligations regardless of where they are established. Article 10 requires training, validation, and test datasets to be relevant, representative. Article 13 requires high-risk AI systems to be designed for sufficient operational transparency.
```

**Branch answer:**

```
Article 25(2) requires the initial provider and the new provider to cooperate along the value chain: the initial provider must make available the necessary information and provide the reasonably expected technical access and other assistance so that the new provider can meet its obligations, in particular the conformity assessment of high-risk AI systems. Article 25(4) is a separate duty: the high-risk provider and third-party suppliers of AI systems, tools, services, components or processes used in or integrated into a high-risk AI system must specify, by written agreement, the necessary information, capabilities, technical access and other assistance, except for third parties making tools, services, processes or components (other than general-purpose AI models) accessible to the public under a free and open-source licence. For general-purpose AI models, the one-third fine-tune rule (per the Commission's 18 July 2025 GPAI Guidelines, anchored on Article 51) makes the downstream modifier a new provider when additional training compute exceeds 1/3 of the base model's compute, or 1/3 of the 10^25 FLOPs systemic threshold (~3.3×10^24 FLOPs) when base compute is unknown. Requires the provider to draw up a written, machine-readable, signed and dated EU declaration of conformity for each high-risk AI system, containing the information in Annex V, kept at the disposal of national competent authorities for 10 years. Article 17 requires providers of high-risk AI systems to operate a quality management system covering regulatory-compliance strategy, design verification, examination + test procedures, post-market monitoring, and incident-reporting workflows.
```

## 46. live_answers:la_q37 🚫 VETO

**Q:** When registering a high-risk AI system in the EU database under the EU AI Act, what specific information must the provider submit? List the required items.

- **gold refs**: Annex III, Annex VIII, Article 49, Article 71
- **base refs**: Article 6, Article 71, Article 16, Article 35, Article 112, Article 109, Article 77  — DROPPED: Annex III, Annex VIII, Article 49
- **branch refs**: Article 6, Article 71, Article 49, Article 26, Article 83, Article 66, Article 16  — DROPPED: Annex III, Annex VIII
- **base scores**: {"answer_chars": 657.0, "gold_dropped_exact": 3.0, "gold_dropped_head": 3.0, "kw_recall": 0.6666666666666666, "n_refs": 7.0, "ref_conc": 0.32653061224489793, "ref_loose": 0.25, "ref_strict": 0.18181818181818182}
- **branch scores**: {"answer_chars": 657.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.6666666666666666, "n_refs": 7.0, "ref_conc": 0.32653061224489793, "ref_loose": 0.5, "ref_strict": 0.36363636363636365}

**Base answer:**

```
The Commission shall, in collaboration with the Member States, set up and maintain an EU database containing information referred to in paragraphs 2 and 3 of this Article concerning high-risk AI systems referred to in Article 6(2) which are registered in accordance with Articles 49 and 60 and AI systems that are not considered as high-risk pursuant to Article 6(3) and which are registered in accordance with Article 6(4) and Article 49. When setting the functional specifications of such database, the Commission shall consult the relevant experts, and when updating the functional specifications of such database, the Commission shall consult the Board.
```

**Branch answer:**

```
The Commission shall, in collaboration with the Member States, set up and maintain an EU database containing information referred to in paragraphs 2 and 3 of this Article concerning high-risk AI systems referred to in Article 6(2) which are registered in accordance with Articles 49 and 60 and AI systems that are not considered as high-risk pursuant to Article 6(3) and which are registered in accordance with Article 6(4) and Article 49. When setting the functional specifications of such database, the Commission shall consult the relevant experts, and when updating the functional specifications of such database, the Commission shall consult the Board.
```

## 47. live_answers:la_q7

**Q:** We want to deploy an AI system that performs biometric verification solely to confirm that a specific natural person is the person he or she claims to be. Is this system prohibited? Is it high-risk?

- **gold refs**: Annex I, Annex III, Article 5, Article 50, Article 6
- **base refs**: Article 5, Article 6, Article 50, Annex III, Annex I
- **branch refs**: Article 5, Article 6, Article 50, Annex III, Annex I
- **base scores**: {"answer_chars": 574.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 5.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 574.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 5.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.
```

**Branch answer:**

```
The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.
```

## 48. live_answers:la_q35 🚫 VETO

**Q:** Consider the situation in which a market surveillance authority (MSA) determines that an AI system, originally classified as non-high-risk by the provider, is in fact high-risk. Does the provider need to recall and suspend the use of the system without undue delay, or does the MSA provide a timeframe within which the provider can take corrective actions? Or does this depend on the gravity of the situation?

- **gold refs**: Annex III, Article 79, Article 80
- **base refs**: Article 74, Article 16, Article 6, Article 50, Annex III, Annex I, Article 11  — DROPPED: Article 79, Article 80
- **branch refs**: Article 74, Article 16, Article 6, Article 50, Annex III, Annex I, Article 11  — DROPPED: Article 79, Article 80
- **base scores**: {"answer_chars": 574.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.0, "n_refs": 7.0, "ref_conc": 0.18367346938775508, "ref_loose": 0.3333333333333333, "ref_strict": 0.2}
- **branch scores**: {"answer_chars": 574.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.0, "n_refs": 7.0, "ref_conc": 0.18367346938775508, "ref_loose": 0.3333333333333333, "ref_strict": 0.2}

**Base answer:**

```
The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.
```

**Branch answer:**

```
The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.
```

## 49. live_answers:la_q2

**Q:** Does the obligation to indicate that deep-fakes are artificially generated apply when prosecuting a criminal offence?

- **gold refs**: Article 50
- **base refs**: Article 50.4, Article 50
- **branch refs**: Article 50.4, Article 50
- **base scores**: {"answer_chars": 382.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.0, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 382.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.0, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
No. Under Article 50(4), the deployer's duty to disclose that image, audio, or video content constituting a deep fake has been artificially generated or manipulated does not apply where the use is authorised by law to detect, prevent, investigate, or prosecute criminal offences. Absent that law-enforcement authorisation, the deployer must disclose that the content is a deep fake.
```

**Branch answer:**

```
No. Under Article 50(4), the deployer's duty to disclose that image, audio, or video content constituting a deep fake has been artificially generated or manipulated does not apply where the use is authorised by law to detect, prevent, investigate, or prosecute criminal offences. Absent that law-enforcement authorisation, the deployer must disclose that the content is a deep fake.
```

## 50. live_answers:la_q52 🚫 VETO

**Q:** Can you help me understand AI compliance?

- **gold refs**: Article 17, Article 56
- **base refs**: Article 63, Article 56, Article 83  — DROPPED: Article 17
- **branch refs**: Article 111, Article 8, Article 86  — DROPPED: Article 17, Article 56
- **base scores**: {"answer_chars": 735.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.3333333333333333, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.5, "ref_strict": 0.4}
- **branch scores**: {"answer_chars": 890.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.3333333333333333, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.0, "ref_strict": 0.0}

**Base answer:**

```
Under Article 56, Codes of Practice by the AI Office offer a route for GPAI providers to demonstrate Article 53 and 55 compliance; signing is voluntary, and providers may use any alternative adequate means to demonstrate compliance. Derogations for SMEs: simplified compliance with Article 17 quality-management-system obligations in a manner appropriate to size + market stage, without compromising the level of protection or compliance with the Section-2 requirements. AI Office encourages and facilitates voluntary codes of practice at Union level to contribute to proper application of the Regulation, particularly for GPAI obligations; codes may serve as a means to demonstrate compliance until harmonised standards are published.
```

**Branch answer:**

```
Under Article 111, transitional provisions grandfather pre-existing AI systems and GPAI models on the market before key dates unless they undergo a substantial change in design; high-risk systems for public-authority use comply from 2 August 2030. Under Article 86, any affected person subject to a decision based on output from an Annex III high-risk AI system has the individual right to obtain a clear and meaningful explanation of the AI system's role in the decision-making procedure. Transitional provisions for AI systems and GPAI models already on the market / in service: high-risk AI for public-authority use placed on the market before 2 August 2026 must comply from 2 August 2030 (only if significant design change); pre-2 August 2025 GPAI models brought into compliance by 2 August 2027; large-scale IT systems listed in Annex X covered by the Regulation from 31 December 2030.
```

## 51. live_answers:la_q13 🚫 VETO

**Q:** Under what conditions should providers of general-purpose AI models be subject to exceptions regarding transparency-related requirements, if any? And what do those exceptions not cover?

- **gold refs**: Annex XI, Annex XII, Article 51, Article 53, Article 55
- **base refs**: Article 53, Article 50.3, Article 50.4, Article 50.1, Article 16, Article 51, Article 55  — DROPPED: Annex XI, Annex XII
- **branch refs**: Article 53, Article 50.1, Article 16, Article 55, Article 51, Article 56, Article 25  — DROPPED: Annex XI, Annex XII
- **base scores**: {"answer_chars": 80.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.3333333333333333, "n_refs": 7.0, "ref_conc": 1.0, "ref_loose": 0.6, "ref_strict": 0.6}
- **branch scores**: {"answer_chars": 80.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.3333333333333333, "n_refs": 7.0, "ref_conc": 0.5102040816326531, "ref_loose": 0.6, "ref_strict": 0.5}

**Base answer:**

```
This exception shall not apply to general-purpose AI models with systemic risks.
```

**Branch answer:**

```
This exception shall not apply to general-purpose AI models with systemic risks.
```

## 52. live_answers:la_q82 🚫 VETO

**Q:** Classify the EU AI Act risk tier of a consumer wellness chatbot that gives general lifestyle tips and makes no medical claims.

- **gold refs**: Annex I, Article 50, Article 6
- **base refs**: Article 50, Article 9, Article 25, Article 6, Article 10, Article 13, Article 53  — DROPPED: Annex I
- **branch refs**: Article 50, Article 6, Article 42, Article 49  — DROPPED: Annex I
- **base scores**: {"answer_chars": 1025.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.3333333333333333, "n_refs": 7.0, "ref_conc": 0.18367346938775508, "ref_loose": 0.6666666666666666, "ref_strict": 0.4}
- **branch scores**: {"answer_chars": 722.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.3333333333333333, "n_refs": 4.0, "ref_conc": 0.5625, "ref_loose": 0.6666666666666666, "ref_strict": 0.5714285714285715}

**Base answer:**

```
Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties; both apply to the same system, not in the alternative. Article 25(2) requires the initial provider and the new provider to cooperate along the value chain: the initial provider must make available the necessary information and provide the reasonably expected technical access and other assistance so that the new provider can meet its obligations, in particular the conformity assessment of high-risk AI systems. Article 25(4) is a separate duty: the high-risk provider and third-party suppliers of AI systems, tools, services, components or processes used in or integrated into a high-risk AI system must specify, by written agreement, the necessary information, capabilities, technical access and other assistance, except for third parties making tools, services, processes or components (other than general-purpose AI models) accessible to the public under a free and open-source licence.
```

**Branch answer:**

```
Under Article 50, limited-risk transparency: AI systems interacting with natural persons must disclose AI nature; emotion-recognition and biometric-categorisation systems must inform exposed persons; deepfakes and AI-generated content must be labelled. Eight high-risk use-case categories: biometrics, critical infrastructure, education + vocational training, employment + worker management (recruitment, task allocation, promotion and termination decisions, and performance evaluation affecting workers' fundamental rights), essential private + public services, law enforcement, migration + asylum + border control, and administration of justice + democratic processes. Classifies an AI system as high-risk on two routes.
```

## 53. live_answers:la_q72 🚫 VETO

**Q:** What must the provider of a high-risk AI medical diagnostic system put in place before placing it on the market?

- **gold refs**: Annex IV, Article 10, Article 11, Article 16, Article 8, Article 9
- **base refs**: Article 6, Article 16, Article 43, Article 8, Article 9, Article 10, Article 11  — DROPPED: Annex IV
- **branch refs**: Article 6, Article 16, Article 43, Article 8, Article 9, Article 10, Article 11  — DROPPED: Annex IV
- **base scores**: {"answer_chars": 467.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 7.0, "ref_conc": 0.7346938775510203, "ref_loose": 0.8333333333333334, "ref_strict": 0.7692307692307692}
- **branch scores**: {"answer_chars": 467.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 7.0, "ref_conc": 0.7346938775510203, "ref_loose": 0.8333333333333334, "ref_strict": 0.7692307692307692}

**Base answer:**

```
Providers of a high-risk AI system listed in Annex III are bound by Article 6, Article 8, and Article 9 (plus follow-on obligations summarised in the references list). Under Article 16, Providers of high-risk AI systems must ensure the system meets the Chapter III Section 2. Article 43 requires providers of high-risk AI to undergo a conformity assessment: internal-control. Article 10 requires training, validation, and test datasets to be relevant, representative.
```

**Branch answer:**

```
Providers of a high-risk AI system listed in Annex III are bound by Article 6, Article 8, and Article 9 (plus follow-on obligations summarised in the references list). Under Article 16, Providers of high-risk AI systems must ensure the system meets the Chapter III Section 2. Article 43 requires providers of high-risk AI to undergo a conformity assessment: internal-control. Article 10 requires training, validation, and test datasets to be relevant, representative.
```

## 54. live_answers:la_q11

**Q:** What is the meaning and purpose of 'testing data' in the context of AI systems, and why is it important that it is not leaked during the training process?

- **gold refs**: Article 10
- **base refs**: Article 3.32, Article 10
- **branch refs**: Article 3.32, Article 10
- **base scores**: {"answer_chars": 589.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 2.0, "ref_conc": 0.25, "ref_loose": 1.0, "ref_strict": 0.6666666666666666}
- **branch scores**: {"answer_chars": 589.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 2.0, "ref_conc": 0.25, "ref_loose": 1.0, "ref_strict": 0.6666666666666666}

**Base answer:**

```
Testing data is defined in Article 3(32) as data used to provide an independent evaluation of the AI system, in order to confirm its expected performance before it is placed on the market or put into service. It must be kept separate from the training and validation data so that this evaluation is genuinely independent. If testing data leaks into the training process, the system is in effect assessed on data it has already seen, which inflates its apparent performance and defeats the purpose of the independent check that Article 10 requires for the datasets of a high-risk AI system.
```

**Branch answer:**

```
Testing data is defined in Article 3(32) as data used to provide an independent evaluation of the AI system, in order to confirm its expected performance before it is placed on the market or put into service. It must be kept separate from the training and validation data so that this evaluation is genuinely independent. If testing data leaks into the training process, the system is in effect assessed on data it has already seen, which inflates its apparent performance and defeats the purpose of the independent check that Article 10 requires for the datasets of a high-risk AI system.
```

## 55. live_answers:la_q10 ✏️

**Q:** Which article of the EU AI Act governs human oversight measures?

- **gold refs**: Article 14
- **base refs**: Article 14, Article 4, Article 1
- **branch refs**: Article 14, Article 2, Article 1
- **base scores**: {"answer_chars": 960.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 0.1111111111111111, "ref_loose": 1.0, "ref_strict": 0.5}
- **branch scores**: {"answer_chars": 768.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.0, "n_refs": 3.0, "ref_conc": 0.1111111111111111, "ref_loose": 1.0, "ref_strict": 0.5}

**Base answer:**

```
Defines 68 terms used in the Regulation, including 'AI system' (machine-based, varying autonomy, possibly adaptive, inferring from input how to generate output influencing physical/virtual environments), 'provider', 'deployer', 'placing on the market', 'putting into service', 'substantial modification', 'general-purpose AI model', 'general-purpose AI system', 'systemic risk'. Requires providers and deployers to take measures to ensure, to their best extent, a sufficient level of AI literacy among their staff and other persons dealing with the operation and use of AI systems on their behalf, considering technical knowledge, experience, education, training, and context of use. Article 14 requires effective human oversight by natural persons during system use, capability + limitation awareness, automation-bias safeguards, ability to interpret output, disregard / override / intervene, and (for biometric identification) a two-person verification rule.
```

**Branch answer:**

```
Defines 68 terms used in the Regulation, including 'AI system' (machine-based, varying autonomy, possibly adaptive, inferring from input how to generate output influencing physical/virtual environments), 'provider', 'deployer', 'placing on the market', 'putting into service', 'substantial modification', 'general-purpose AI model', 'general-purpose AI system', 'systemic risk'. Scope: applies to providers placing AI systems on the EU market regardless of establishment, deployers established in the EU, providers/deployers in third countries whose output is used in the EU. Excludes military/defence/national-security uses, scientific R&D, purely personal non-professional use, and free/open-source AI systems outside the high-risk + prohibited + transparency scope.
```

## 56. live_answers:la_q67

**Q:** What does the EU AI Act require for an AI system that evaluates patients' eligibility for public healthcare benefits?

- **gold refs**: Annex III, Article 6
- **base refs**: Article 6, Annex III, Article 5, Annex I
- **branch refs**: Article 6, Annex III, Article 5, Annex I
- **base scores**: {"answer_chars": 724.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 4.0, "ref_conc": 0.25, "ref_loose": 1.0, "ref_strict": 0.6666666666666666}
- **branch scores**: {"answer_chars": 724.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 4.0, "ref_conc": 0.25, "ref_loose": 1.0, "ref_strict": 0.6666666666666666}

**Base answer:**

```
Eight high-risk use-case categories: biometrics, critical infrastructure, education + vocational training, employment + worker management (recruitment, task allocation, promotion and termination decisions, and performance evaluation affecting workers' fundamental rights), essential private + public services, law enforcement, migration + asylum + border control, and administration of justice + democratic processes. Classifies an AI system as high-risk on two routes. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation.
```

**Branch answer:**

```
Eight high-risk use-case categories: biometrics, critical infrastructure, education + vocational training, employment + worker management (recruitment, task allocation, promotion and termination decisions, and performance evaluation affecting workers' fundamental rights), essential private + public services, law enforcement, migration + asylum + border control, and administration of justice + democratic processes. Classifies an AI system as high-risk on two routes. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation.
```

## 57. live_answers:la_q53 🚫 VETO

**Q:** We are building a chatbot for customer support. What do we need to know?

- **gold refs**: Annex I, Annex III, Annex XI, Annex XII, Article 25, Article 51, Article 53, Article 55, Article 6
- **base refs**: Article 50, Article 29, Article 25  — DROPPED: Annex I, Annex III, Annex XI, Annex XII, Article 51, Article 53, Article 55, Article 6
- **branch refs**: Article 50, Article 25, Article 29  — DROPPED: Annex I, Annex III, Annex XI, Annex XII, Article 51, Article 53, Article 55, Article 6
- **base scores**: {"answer_chars": 1266.0, "gold_dropped_exact": 8.0, "gold_dropped_head": 8.0, "kw_recall": 0.0, "n_refs": 3.0, "ref_conc": 0.1111111111111111, "ref_loose": 0.1111111111111111, "ref_strict": 0.16666666666666666}
- **branch scores**: {"answer_chars": 1543.0, "gold_dropped_exact": 8.0, "gold_dropped_head": 8.0, "kw_recall": 0.0, "n_refs": 3.0, "ref_conc": 0.1111111111111111, "ref_loose": 0.1111111111111111, "ref_strict": 0.16666666666666666}

**Base answer:**

```
Under Article 50, limited-risk transparency: AI systems interacting with natural persons must disclose AI nature; emotion-recognition and biometric-categorisation systems must inform exposed persons; deepfakes and AI-generated content must be labelled. Eight high-risk use-case categories: biometrics, critical infrastructure, education + vocational training, employment + worker management (recruitment, task allocation, promotion and termination decisions, and performance evaluation affecting workers' fundamental rights), essential private + public services, law enforcement, migration + asylum + border control, and administration of justice + democratic processes. Sets the application procedure for conformity-assessment bodies seeking notification under Article 28(1)(b): the body must submit the application to the notifying authority of the Member State in which it is established, together with a description of the conformity-assessment activities, modules, AI technologies, and evidence of compliance with the Article 31 requirements. Per Article 29(2)-(3) an accreditation certificate from a national accreditation body may serve as such evidence. Under Article 50, Transparency obligations split by actor: providers must ensure AI systems interacting.
```

**Branch answer:**

```
Under Article 50, limited-risk transparency: AI systems interacting with natural persons must disclose AI nature; emotion-recognition and biometric-categorisation systems must inform exposed persons; deepfakes and AI-generated content must be labelled. Article 25(2) requires the initial provider and the new provider to cooperate along the value chain: the initial provider must make available the necessary information and provide the reasonably expected technical access and other assistance so that the new provider can meet its obligations, in particular the conformity assessment of high-risk AI systems. Article 25(4) is a separate duty: the high-risk provider and third-party suppliers of AI systems, tools, services, components or processes used in or integrated into a high-risk AI system must specify, by written agreement, the necessary information, capabilities, technical access and other assistance, except for third parties making tools, services, processes or components (other than general-purpose AI models) accessible to the public under a free and open-source licence. For general-purpose AI models, the one-third fine-tune rule (per the Commission's 18 July 2025 GPAI Guidelines, anchored on Article 51) makes the downstream modifier a new provider when additional training compute exceeds 1/3 of the base model's compute, or 1/3 of the 10^25 FLOPs systemic threshold (~3.3×10^24 FLOPs) when base compute is unknown. Under Article 50, Transparency obligations split by actor: providers must ensure AI systems interacting.
```

## 58. live_answers:la_q1

**Q:** Does the technical documentation of a high-risk AI system require to provide specifications regarding the required hardware?

- **gold refs**: Annex IV, Article 11
- **base refs**: Article 11, Annex IV
- **branch refs**: Article 11, Annex IV
- **base scores**: {"answer_chars": 387.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 387.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
Yes. Under Article 11, a provider must draw up technical documentation containing the information set out in Annex IV, which expressly requires a description of the hardware on which the AI system is intended to run (Annex IV point 1(e)) and, as part of the system's development description, the computational resources used to develop, train, test and validate it (Annex IV point 2(c)).
```

**Branch answer:**

```
Yes. Under Article 11, a provider must draw up technical documentation containing the information set out in Annex IV, which expressly requires a description of the hardware on which the AI system is intended to run (Annex IV point 1(e)) and, as part of the system's development description, the computational resources used to develop, train, test and validate it (Annex IV point 2(c)).
```

## 59. live_answers:la_q46 🚫 VETO

**Q:** Is an AI system that recommends recipes high risk?

- **gold refs**: Annex I, Annex III, Article 5, Article 6
- **base refs**: Article 6, Article 50.1, Annex III, Annex I  — DROPPED: Article 5
- **branch refs**: Article 6, Article 50, Annex III, Annex I  — DROPPED: Article 5
- **base scores**: {"answer_chars": 528.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.3333333333333333, "n_refs": 4.0, "ref_conc": 1.0, "ref_loose": 0.75, "ref_strict": 0.75}
- **branch scores**: {"answer_chars": 574.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.3333333333333333, "n_refs": 4.0, "ref_conc": 1.0, "ref_loose": 0.75, "ref_strict": 0.75}

**Base answer:**

```
Not high-risk. A recipe-recommendation system does not fall within any of the eight use-case areas listed in Annex III, nor is it a safety component of, or itself, a product covered by the Union harmonisation legislation listed in Annex I requiring third-party conformity assessment, so neither route to high-risk classification under Article 6 is satisfied. Where the system interacts directly with natural persons, the provider must ensure those persons are informed they are interacting with an AI system under Article 50(1).
```

**Branch answer:**

```
The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.
```

## 60. live_answers:la_q19

**Q:** What is a deep fake according to the EU AI Act?

- **gold refs**: Article 50
- **base refs**: Article 3.60, Article 50
- **branch refs**: Article 3.60, Article 50
- **base scores**: {"answer_chars": 192.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.0, "n_refs": 2.0, "ref_conc": 0.25, "ref_loose": 1.0, "ref_strict": 0.6666666666666666}
- **branch scores**: {"answer_chars": 192.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.0, "n_refs": 2.0, "ref_conc": 0.25, "ref_loose": 1.0, "ref_strict": 0.6666666666666666}

**Base answer:**

```
AI-generated or manipulated image, audio or video content that resembles existing persons, objects, places, entities or events and would falsely appear to a person to be authentic or truthful.
```

**Branch answer:**

```
AI-generated or manipulated image, audio or video content that resembles existing persons, objects, places, entities or events and would falsely appear to a person to be authentic or truthful.
```

## 61. live_answers:la_q78 🚫 VETO

**Q:** A pharma company trains a large foundation model for drug discovery whose training compute exceeds 10^25 FLOPs. Which EU AI Act obligations apply?

- **gold refs**: Annex III, Article 25, Article 3, Article 51, Article 6
- **base refs**: Article 51, Article 25  — DROPPED: Annex III, Article 3, Article 6
- **branch refs**: Article 51, Article 25  — DROPPED: Annex III, Article 3, Article 6
- **base scores**: {"answer_chars": 1255.0, "gold_dropped_exact": 3.0, "gold_dropped_head": 3.0, "kw_recall": 0.0, "n_refs": 2.0, "ref_conc": 0.16000000000000003, "ref_loose": 0.4, "ref_strict": 0.5714285714285715}
- **branch scores**: {"answer_chars": 1255.0, "gold_dropped_exact": 3.0, "gold_dropped_head": 3.0, "kw_recall": 0.0, "n_refs": 2.0, "ref_conc": 0.16000000000000003, "ref_loose": 0.4, "ref_strict": 0.5714285714285715}

**Base answer:**

```
Under Article 51, a GPAI model has systemic risk when cumulative training compute exceeds 10²⁵ FLOPs (10^25); providers must notify the Commission within two weeks of meeting the threshold. Classifies a general-purpose AI model as having 'systemic risk' when it has high-impact capabilities (presumed when cumulative training compute exceeds 10^25 FLOPs) or when so designated by the Commission based on Annex XIII criteria. Commission's 18 July 2025 GPAI Guidelines presume a model is general-purpose (Article 3(63)) when training compute exceeds 10^23 FLOPs and the model can generate language, image, audio, or video output. Fine-tuned or modified models become new providers under Article 25 when their additional training compute exceeds one-third of the base model's compute (or one-third of the 10^25 systemic threshold, ~3.3×10^24 FLOPs, when base compute is unknown). Defines 68 terms used in the Regulation, including 'AI system' (machine-based, varying autonomy, possibly adaptive, inferring from input how to generate output influencing physical/virtual environments), 'provider', 'deployer', 'placing on the market', 'putting into service', 'substantial modification', 'general-purpose AI model', 'general-purpose AI system', 'systemic risk'.
```

**Branch answer:**

```
Under Article 51, a GPAI model has systemic risk when cumulative training compute exceeds 10²⁵ FLOPs (10^25); providers must notify the Commission within two weeks of meeting the threshold. Classifies a general-purpose AI model as having 'systemic risk' when it has high-impact capabilities (presumed when cumulative training compute exceeds 10^25 FLOPs) or when so designated by the Commission based on Annex XIII criteria. Commission's 18 July 2025 GPAI Guidelines presume a model is general-purpose (Article 3(63)) when training compute exceeds 10^23 FLOPs and the model can generate language, image, audio, or video output. Fine-tuned or modified models become new providers under Article 25 when their additional training compute exceeds one-third of the base model's compute (or one-third of the 10^25 systemic threshold, ~3.3×10^24 FLOPs, when base compute is unknown). Defines 68 terms used in the Regulation, including 'AI system' (machine-based, varying autonomy, possibly adaptive, inferring from input how to generate output influencing physical/virtual environments), 'provider', 'deployer', 'placing on the market', 'putting into service', 'substantial modification', 'general-purpose AI model', 'general-purpose AI system', 'systemic risk'.
```

## 62. live_answers:la_q21 ✏️

**Q:** If a provider of a high-risk AI system confirms that the system achieves an appropriate level of accuracy, robustness, and cybersecurity at the time of development, then no further action is required by the provider on these aspects in the future. Correct?

- **gold refs**: Article 15
- **base refs**: Article 6, Article 15, Article 16, Article 13, Article 42, Article 9, Article 17
- **branch refs**: Article 6, Article 15, Article 13, Article 16, Article 17, Article 43, Article 50
- **base scores**: {"answer_chars": 1022.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 7.0, "ref_conc": 0.02040816326530612, "ref_loose": 1.0, "ref_strict": 0.25}
- **branch scores**: {"answer_chars": 730.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 7.0, "ref_conc": 0.02040816326530612, "ref_loose": 1.0, "ref_strict": 0.25}

**Base answer:**

```
Providers of high-risk AI systems must ensure the system meets the Chapter III Section 2 requirements and bears their identity, operate a quality-management system (Article 17 requires providers of high-risk AI systems to operate a quality management system covering regulatory-compliance strategy, design verification, examination + test procedures, post-market monitoring, and incident-reporting workflows.), keep the technical documentation (Articles 11 and 18) and automatically generated logs (Article 19), have the system undergo conformity assessment (Article 43), draw up the EU declaration of conformity (Article 47), affix the CE marking (Article 48), register the system in the EU database (Article 49), take corrective action where it is not in conformity (Article 20), and demonstrate compliance to competent authorities on request (Article 21). Article 15 requires appropriate levels of accuracy, robustness. Article 9 requires a documented, iterative risk-management system across the AI system's lifecycle.
```

**Branch answer:**

```
Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties; both apply to the same system, not in the alternative. Requires appropriate levels of accuracy, robustness, and cybersecurity across the lifecycle, accuracy metrics declared in instructions for use, resilience against errors, and resistance to data-poisoning, evasion, model-confidentiality, and adversarial attacks. Requires high-risk AI systems to be designed for sufficient operational transparency to deployers, accompanied by instructions for use covering provider identity, intended purpose, capabilities + limitations, expected lifetime, human-oversight measures, and required maintenance.
```

## 63. live_answers:la_q29 🚫 VETO

**Q:** Under the EU AI Act, which specific AI systems are explicitly listed as high-risk because they make decisions in critical life- and health-related situations involving emergency calls and triage?

- **gold refs**: Article 6, Annex III
- **base refs**: Article 9, Article 27, Article 46  — DROPPED: Annex III, Article 6
- **branch refs**: Article 9, Article 27, Article 46  — DROPPED: Annex III, Article 6
- **base scores**: {"answer_chars": 806.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.0, "ref_strict": 0.0}
- **branch scores**: {"answer_chars": 806.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.0, "ref_strict": 0.0}

**Base answer:**

```
Under Article 27, in addition to Article 26 baseline duties, deployers of certain Annex III high-risk AI systems must perform a Fundamental Rights Impact Assessment (FRIA) covering affected persons and specific fundamental rights risks. Derogation from the conformity-assessment procedure: by way of derogation from Article 43, a market-surveillance authority may authorise the placing on the market or putting into service of specific high-risk AI systems within the territory of the Member State concerned, for exceptional reasons of public security or the protection of life and health of persons, environmental protection, or the protection of key industrial and infrastructural assets (Article 46(1)). Article 9 requires a documented, iterative risk-management system across the AI system's lifecycle.
```

**Branch answer:**

```
Under Article 27, in addition to Article 26 baseline duties, deployers of certain Annex III high-risk AI systems must perform a Fundamental Rights Impact Assessment (FRIA) covering affected persons and specific fundamental rights risks. Derogation from the conformity-assessment procedure: by way of derogation from Article 43, a market-surveillance authority may authorise the placing on the market or putting into service of specific high-risk AI systems within the territory of the Member State concerned, for exceptional reasons of public security or the protection of life and health of persons, environmental protection, or the protection of key industrial and infrastructural assets (Article 46(1)). Article 9 requires a documented, iterative risk-management system across the AI system's lifecycle.
```

## 64. live_answers:la_q36

**Q:** Under the EU AI Act, what presumption applies when a high-risk AI system is trained and tested on data that reflects the specific geographical, behavioural, contextual or functional setting in which it is intended to be used?

- **gold refs**: Article 10, Article 42
- **base refs**: Article 6, Article 42, Article 10
- **branch refs**: Article 6, Article 42, Article 10
- **base scores**: {"answer_chars": 741.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 1.0, "ref_strict": 0.8}
- **branch scores**: {"answer_chars": 741.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 1.0, "ref_strict": 0.8}

**Base answer:**

```
Adds two further presumptions of conformity beyond Articles 40-41: Article 42(1), high-risk AI systems trained and tested on data reflecting the specific geographical, behavioural, contextual, or functional setting in which they are intended to be used are presumed to comply with the relevant data-governance requirements of Article 10(4); Article 42(2), high-risk AI systems certified or for which a statement of conformity has been issued under a cybersecurity scheme under Regulation (EU) 2019/881 (the Cybersecurity Act) and whose references are published in the Official Journal are presumed to comply with the cybersecurity requirements of Article 15 to the extent the cybersecurity certificate or statement covers those requirements.
```

**Branch answer:**

```
Adds two further presumptions of conformity beyond Articles 40-41: Article 42(1), high-risk AI systems trained and tested on data reflecting the specific geographical, behavioural, contextual, or functional setting in which they are intended to be used are presumed to comply with the relevant data-governance requirements of Article 10(4); Article 42(2), high-risk AI systems certified or for which a statement of conformity has been issued under a cybersecurity scheme under Regulation (EU) 2019/881 (the Cybersecurity Act) and whose references are published in the Official Journal are presumed to comply with the cybersecurity requirements of Article 15 to the extent the cybersecurity certificate or statement covers those requirements.
```

## 65. live_answers:la_q43

**Q:** Under Article 10(5) of the EU AI Act, when may a provider of a high-risk AI system process special categories of personal data for bias detection and correction, and what key safeguards/conditions must be met?

- **gold refs**: Article 10
- **base refs**: Article 10.5, Article 10
- **branch refs**: Article 10.5, Article 10
- **base scores**: {"answer_chars": 722.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 722.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
Under Article 10(5), a provider of a high-risk AI system may exceptionally process special categories of personal data only to the extent strictly necessary to ensure bias detection and correction, subject to appropriate safeguards. Article 10(5) requires all of the following: the bias work cannot be done with other data, including synthetic or anonymised data (a); technical limits on re-use plus state-of-the-art security and pseudonymisation (b); strict, documented access controls to prevent misuse (c); no transmission or transfer to other parties (d); deletion once the bias is corrected or the retention period ends, whichever is first (e); and records of processing documenting why it was strictly necessary (f).
```

**Branch answer:**

```
Under Article 10(5), a provider of a high-risk AI system may exceptionally process special categories of personal data only to the extent strictly necessary to ensure bias detection and correction, subject to appropriate safeguards. Article 10(5) requires all of the following: the bias work cannot be done with other data, including synthetic or anonymised data (a); technical limits on re-use plus state-of-the-art security and pseudonymisation (b); strict, documented access controls to prevent misuse (c); no transmission or transfer to other parties (d); deletion once the bias is corrected or the retention period ends, whichever is first (e); and records of processing documenting why it was strictly necessary (f).
```

## 66. live_answers:la_q17 🚫 VETO

**Q:** How does Annex II relate to prohibited uses of AI systems?

- **gold refs**: Annex II, Article 5
- **base refs**: Annex II  — DROPPED: Article 5
- **branch refs**: Annex II  — DROPPED: Article 5
- **base scores**: {"answer_chars": 500.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.0, "n_refs": 1.0, "ref_conc": 0.25, "ref_loose": 0.5, "ref_strict": 0.6666666666666666}
- **branch scores**: {"answer_chars": 500.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.0, "n_refs": 1.0, "ref_conc": 0.25, "ref_loose": 0.5, "ref_strict": 0.6666666666666666}

**Base answer:**

```
List of criminal offences referred to in Article 5(1)(h) permitting real-time remote biometric identification by law enforcement: terrorism, trafficking in human beings, sexual exploitation of children, illicit trafficking in narcotic drugs / weapons / nuclear material, murder, kidnapping, rape, armed robbery, organised crime, participation in a criminal organisation, environmental crime, provided the offence is punishable in the relevant Member State by a custodial sentence of at least 4 years.
```

**Branch answer:**

```
List of criminal offences referred to in Article 5(1)(h) permitting real-time remote biometric identification by law enforcement: terrorism, trafficking in human beings, sexual exploitation of children, illicit trafficking in narcotic drugs / weapons / nuclear material, murder, kidnapping, rape, armed robbery, organised crime, participation in a criminal organisation, environmental crime, provided the offence is punishable in the relevant Member State by a custodial sentence of at least 4 years.
```

## 67. live_answers:la_q22

**Q:** What are all the risk categories in the EU AI Act?

- **gold refs**: Article 5
- **base refs**: Article 5, Article 6, Article 50, Article 51, Article 52, Annex I, Annex III, Article 53, Article 54, Article 55, Article 56
- **branch refs**: Article 5, Article 6, Article 50, Article 51, Article 52, Annex I, Annex III, Article 53, Article 54, Article 55, Article 56
- **base scores**: {"answer_chars": 621.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.5, "n_refs": 11.0, "ref_conc": 0.008264462809917356, "ref_loose": 1.0, "ref_strict": 0.16666666666666669}
- **branch scores**: {"answer_chars": 621.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.5, "n_refs": 11.0, "ref_conc": 0.008264462809917356, "ref_loose": 1.0, "ref_strict": 0.16666666666666669}

**Base answer:**

```
The EU AI Act sets four risk tiers plus a separate regime for general-purpose AI models: unacceptable-risk practices are prohibited under Article 5; and high-risk systems are classified under Article 6 (an Annex I product safety component, or an Annex III use case) and carry the Chapter III Section 2 obligations. Limited-risk systems carry the Article 50 transparency duties, minimal-risk systems have no mandatory duties under the Act, and general-purpose AI models are governed separately under Articles 51 to 56, with added obligations under Article 55 for models classified as having systemic risk under Article 51.
```

**Branch answer:**

```
The EU AI Act sets four risk tiers plus a separate regime for general-purpose AI models: unacceptable-risk practices are prohibited under Article 5; and high-risk systems are classified under Article 6 (an Annex I product safety component, or an Annex III use case) and carry the Chapter III Section 2 obligations. Limited-risk systems carry the Article 50 transparency duties, minimal-risk systems have no mandatory duties under the Act, and general-purpose AI models are governed separately under Articles 51 to 56, with added obligations under Article 55 for models classified as having systemic risk under Article 51.
```

## 68. live_answers:la_q65 🚫 VETO

**Q:** Which EU AI Act article sets the transparency obligation for a patient-facing medical chatbot?

- **gold refs**: Article 50
- **base refs**: Article 50.1, Article 13  — DROPPED: Article 50
- **branch refs**: Article 50.1, Article 13  — DROPPED: Article 50
- **base scores**: {"answer_chars": 1151.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 2.0, "ref_conc": 0.25, "ref_loose": 1.0, "ref_strict": 0.6666666666666666}
- **branch scores**: {"answer_chars": 1151.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 2.0, "ref_conc": 0.25, "ref_loose": 1.0, "ref_strict": 0.6666666666666666}

**Base answer:**

```
Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties; both apply to the same system, not in the alternative. Transparency obligations split by actor: providers must ensure AI systems interacting with natural persons disclose their AI nature (Article 50(1)) and must mark synthetic AI-generated content in a machine-readable, detectable format (Article 50(2)); deployers must inform exposed persons when operating emotion-recognition or biometric-categorisation systems (Article 50(3)) and must label deepfakes as artificially generated or manipulated (Article 50(4)). Article 50(4) also requires deployers who use an AI system to generate or manipulate text published to inform the public on matters of public interest to disclose that the text was artificially generated or manipulated; this disclosure duty does not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for publishing it.
```

**Branch answer:**

```
Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties; both apply to the same system, not in the alternative. Transparency obligations split by actor: providers must ensure AI systems interacting with natural persons disclose their AI nature (Article 50(1)) and must mark synthetic AI-generated content in a machine-readable, detectable format (Article 50(2)); deployers must inform exposed persons when operating emotion-recognition or biometric-categorisation systems (Article 50(3)) and must label deepfakes as artificially generated or manipulated (Article 50(4)). Article 50(4) also requires deployers who use an AI system to generate or manipulate text published to inform the public on matters of public interest to disclose that the text was artificially generated or manipulated; this disclosure duty does not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for publishing it.
```

## 69. live_answers:la_q71 🚫 VETO

**Q:** A hospital deploys a high-risk AI diagnostic system. What are its obligations as a deployer under the EU AI Act?

- **gold refs**: Annex III, Article 13, Article 25, Article 26, Article 27, Article 86
- **base refs**: Article 26, Article 27, Article 13, Article 86, Article 14, Article 9, Article 6  — DROPPED: Annex III, Article 25
- **branch refs**: Article 26, Article 27, Article 13, Article 86, Article 14, Article 9, Article 6  — DROPPED: Annex III, Article 25
- **base scores**: {"answer_chars": 926.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.3333333333333333, "n_refs": 7.0, "ref_conc": 0.7346938775510203, "ref_loose": 0.6666666666666666, "ref_strict": 0.6153846153846153}
- **branch scores**: {"answer_chars": 926.0, "gold_dropped_exact": 2.0, "gold_dropped_head": 2.0, "kw_recall": 0.3333333333333333, "n_refs": 7.0, "ref_conc": 0.7346938775510203, "ref_loose": 0.6666666666666666, "ref_strict": 0.6153846153846153}

**Base answer:**

```
Under Article 27, in addition to Article 26 baseline duties, deployers of certain Annex III high-risk AI systems must perform a Fundamental Rights Impact Assessment (FRIA) covering affected persons and specific fundamental rights risks. Under Article 86, any affected person subject to a decision based on output from an Annex III high-risk AI system has the individual right to obtain a clear and meaningful explanation of the AI system's role in the decision-making procedure. Deployers of a high-risk AI system listed in Annex III are bound by Article 26, Article 27, and Article 13 (plus follow-on obligations summarised in the references list). Article 14 requires effective human oversight by natural persons during system use, capability + limitation awareness, automation-bias safeguards, ability to interpret output, disregard / override / intervene, and (for biometric identification) a two-person verification rule.
```

**Branch answer:**

```
Under Article 27, in addition to Article 26 baseline duties, deployers of certain Annex III high-risk AI systems must perform a Fundamental Rights Impact Assessment (FRIA) covering affected persons and specific fundamental rights risks. Under Article 86, any affected person subject to a decision based on output from an Annex III high-risk AI system has the individual right to obtain a clear and meaningful explanation of the AI system's role in the decision-making procedure. Deployers of a high-risk AI system listed in Annex III are bound by Article 26, Article 27, and Article 13 (plus follow-on obligations summarised in the references list). Article 14 requires effective human oversight by natural persons during system use, capability + limitation awareness, automation-bias safeguards, ability to interpret output, disregard / override / intervene, and (for biometric identification) a two-person verification rule.
```

## 70. live_answers:la_q32

**Q:** Is an AI system used to detect decision-making patterns or deviations for a use case listed in Annex III considered high-risk?

- **gold refs**: Annex III, Article 6
- **base refs**: Article 6.3, Article 6, Annex III
- **branch refs**: Article 6.3, Article 6, Annex III
- **base scores**: {"answer_chars": 477.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 477.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.6666666666666666, "n_refs": 3.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
Not automatically. Even within an Annex III use case, Article 6(3)(c) provides that an AI system intended to detect decision-making patterns or deviations from prior decision-making patterns is not high-risk where it does not pose a significant risk of harm and is not meant to replace or influence a previously completed human assessment without proper human review. However, under Article 6(3) such a system is always high-risk where it performs profiling of natural persons.
```

**Branch answer:**

```
Not automatically. Even within an Annex III use case, Article 6(3)(c) provides that an AI system intended to detect decision-making patterns or deviations from prior decision-making patterns is not high-risk where it does not pose a significant risk of harm and is not meant to replace or influence a previously completed human assessment without proper human review. However, under Article 6(3) such a system is always high-risk where it performs profiling of natural persons.
```

## 71. live_answers:la_q55

**Q:** hi, what can you do?

- **gold refs**: (none)
- **base refs**: (none)
- **branch refs**: (none)
- **base scores**: {"answer_chars": 158.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 0.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 158.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 0.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
I am Lexy, a Compliance assistant that can answer your questions related to the EU AI Act, based on my Knowledge Graph and ontology. What can I help you with?
```

**Branch answer:**

```
I am Lexy, a Compliance assistant that can answer your questions related to the EU AI Act, based on my Knowledge Graph and ontology. What can I help you with?
```

## 72. live_answers:la_q77 🚫 VETO

**Q:** Does the EU AI Act require post-market monitoring and serious-incident reporting for an AI-based patient-monitoring device, and under which articles?

- **gold refs**: Article 72, Article 73, Article 3
- **base refs**: Article 72, Article 73  — DROPPED: Article 3
- **branch refs**: Article 72.1, Article 72.4, Article 73.9, Article 73.1  — DROPPED: Article 3, Article 72, Article 73
- **base scores**: {"answer_chars": 641.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 1.0, "n_refs": 2.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.6666666666666666, "ref_strict": 0.8}
- **branch scores**: {"answer_chars": 1343.0, "gold_dropped_exact": 3.0, "gold_dropped_head": 1.0, "kw_recall": 1.0, "n_refs": 4.0, "ref_conc": 0.4444444444444444, "ref_loose": 0.6666666666666666, "ref_strict": 0.8}

**Base answer:**

```
Under Article 73, providers of high-risk AI systems must report any serious incident to the market surveillance authority within 15 days of becoming aware. Requires providers of high-risk AI systems to establish and document a post-market monitoring system proportionate to the nature and risks of the AI system (Article 72(1)). The system actively collects, documents, and analyses performance data throughout the system's lifetime to evaluate continuous compliance with Chapter III Section 2 requirements (Article 72(2)), based on a post-market monitoring plan that forms part of the technical documentation under Annex IV (Article 72(3)).
```

**Branch answer:**

```
Yes. An AI-based patient-monitoring device is high-risk under Article 6(1) where it is a safety component of, or is itself, a medical device covered by the Medical Devices Regulation listed in Annex I Section A and that device must undergo third-party conformity assessment. As a high-risk system, the provider must establish and document a post-market monitoring system that actively collects and analyses performance data throughout the system's lifetime to evaluate continuous compliance, based on a post-market monitoring plan forming part of the technical documentation (Article 72(1) to (3), Annex IV). Article 72(4) permits the provider to integrate those elements into the post-market surveillance system already required under the Medical Devices Regulation rather than maintaining a parallel one. For serious incident reporting, Article 73 applies, but Article 73(9) narrows the AI Act reporting duty for high-risk systems covered by Union legislation with equivalent reporting obligations: notification is limited to serious incidents consisting of an infringement of Union law protecting fundamental rights, reported to the market surveillance authority of the Member State where the incident occurred, while incidents involving death or serious deterioration of health route through the medical-device vigilance framework instead.
```

## 73. live_answers:la_q86 🚫 VETO

**Q:** What does the EU AI Act require for an AI system used for risk assessment and pricing in health insurance?

- **gold refs**: Annex III, Article 6
- **base refs**: Article 6, Annex III
- **branch refs**: Article 6, Annex III.5, Annex I  — DROPPED: Annex III
- **base scores**: {"answer_chars": 400.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 2.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 400.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 3.0, "ref_conc": 0.4444444444444444, "ref_loose": 1.0, "ref_strict": 0.8}

**Base answer:**

```
Classifies an AI system as high-risk on two routes. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation. Annex III route (Article 6(2)): the system falls within one of the eight Annex III use cases.
```

**Branch answer:**

```
Classifies an AI system as high-risk on two routes. Annex I route (Article 6(1)): the system is a safety component of, or is itself, a product covered by the Union harmonisation legislation listed in Annex I AND that product must undergo a third-party conformity assessment under that sectoral legislation. Annex III route (Article 6(2)): the system falls within one of the eight Annex III use cases.
```

## 74. live_answers:la_q27 🚫 VETO

**Q:** How are AI systems intended to influence the outcome of an election or referendum classified, and what exception is given for certain campaign-related tools?

- **gold refs**: Annex III
- **base refs**: Article 6, Annex III.8  — DROPPED: Annex III
- **branch refs**: Article 6, Annex III.8  — DROPPED: Annex III
- **base scores**: {"answer_chars": 493.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 2.0, "ref_conc": 0.25, "ref_loose": 1.0, "ref_strict": 0.6666666666666666}
- **branch scores**: {"answer_chars": 493.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 2.0, "ref_conc": 0.25, "ref_loose": 1.0, "ref_strict": 0.6666666666666666}

**Base answer:**

```
Under Annex III point 8(b), AI systems intended to influence the outcome of an election or referendum, or the voting behaviour of natural persons in exercising their vote, are high-risk under Article 6(2). Annex III point 8(b) itself excludes systems to whose output natural persons are not directly exposed, such as tools used only to organise, optimise or structure political campaigns from an administrative or logistical point of view, which therefore fall outside this high-risk category.
```

**Branch answer:**

```
Under Annex III point 8(b), AI systems intended to influence the outcome of an election or referendum, or the voting behaviour of natural persons in exercising their vote, are high-risk under Article 6(2). Annex III point 8(b) itself excludes systems to whose output natural persons are not directly exposed, such as tools used only to organise, optimise or structure political campaigns from an administrative or logistical point of view, which therefore fall outside this high-risk category.
```

## 75. live_answers:la_q63 🚫 VETO

**Q:** What are the algorithmic transparency obligations for a Very Large Online Platform content-moderation AI?

- **gold refs**: Article 50
- **base refs**: (none)  — DROPPED: Article 50
- **branch refs**: (none)  — DROPPED: Article 50
- **base scores**: {"answer_chars": 209.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.0, "n_refs": 0.0, "ref_conc": 0.0, "ref_loose": 0.0, "ref_strict": 0.0}
- **branch scores**: {"answer_chars": 209.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.0, "n_refs": 0.0, "ref_conc": 0.0, "ref_loose": 0.0, "ref_strict": 0.0}

**Base answer:**

```
This question is about the Digital Services Act (DSA), not the EU AI Act (Regulation 2024/1689). This assistant only covers EU AI Act questions; consult the Digital Services Act (DSA) for the applicable rules.
```

**Branch answer:**

```
This question is about the Digital Services Act (DSA), not the EU AI Act (Regulation 2024/1689). This assistant only covers EU AI Act questions; consult the Digital Services Act (DSA) for the applicable rules.
```

## 76. live_answers:la_q92 🚫 VETO

**Q:** What does GDPR Article 17 say about the right to erasure?

- **gold refs**: Article 17
- **base refs**: (none)  — DROPPED: Article 17
- **branch refs**: (none)  — DROPPED: Article 17
- **base scores**: {"answer_chars": 225.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 0.0, "ref_conc": 0.0, "ref_loose": 0.0, "ref_strict": 0.0}
- **branch scores**: {"answer_chars": 225.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.6666666666666666, "n_refs": 0.0, "ref_conc": 0.0, "ref_loose": 0.0, "ref_strict": 0.0}

**Base answer:**

```
This question is about a regulation outside the EU AI Act. This assistant answers EU AI Act questions only (Regulation 2024/1689). Please rephrase with a specific Article reference (e.g. "Article 13") or compliance dimension.
```

**Branch answer:**

```
This question is about a regulation outside the EU AI Act. This assistant answers EU AI Act questions only (Regulation 2024/1689). Please rephrase with a specific Article reference (e.g. "Article 13") or compliance dimension.
```

## 77. live_answers:la_q60 🚫 VETO

**Q:** What are the algorithmic transparency obligations for a Very Large Online Platform content-moderation AI?

- **gold refs**: Article 50
- **base refs**: (none)  — DROPPED: Article 50
- **branch refs**: (none)  — DROPPED: Article 50
- **base scores**: {"answer_chars": 209.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.0, "n_refs": 0.0, "ref_conc": 0.0, "ref_loose": 0.0, "ref_strict": 0.0}
- **branch scores**: {"answer_chars": 209.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 1.0, "kw_recall": 0.0, "n_refs": 0.0, "ref_conc": 0.0, "ref_loose": 0.0, "ref_strict": 0.0}

**Base answer:**

```
This question is about the Digital Services Act (DSA), not the EU AI Act (Regulation 2024/1689). This assistant only covers EU AI Act questions; consult the Digital Services Act (DSA) for the applicable rules.
```

**Branch answer:**

```
This question is about the Digital Services Act (DSA), not the EU AI Act (Regulation 2024/1689). This assistant only covers EU AI Act questions; consult the Digital Services Act (DSA) for the applicable rules.
```

## 78. live_answers:la_q75

**Q:** What data-governance obligations apply to the training data of a high-risk AI sepsis-prediction model?

- **gold refs**: Article 10
- **base refs**: Article 10, Article 42, Article 26
- **branch refs**: Article 10, Article 26, Article 13
- **base scores**: {"answer_chars": 894.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 3.0, "ref_conc": 0.1111111111111111, "ref_loose": 1.0, "ref_strict": 0.5}
- **branch scores**: {"answer_chars": 894.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 3.0, "ref_conc": 0.1111111111111111, "ref_loose": 1.0, "ref_strict": 0.5}

**Base answer:**

```
Deployer obligations: use the system per the instructions, assign human oversight to competent + trained natural persons, monitor operation, retain automatically generated logs, inform affected workers (for workplace use), and cooperate with market-surveillance authorities. Article 26 carve-outs: deployers that are financial institutions subject to Union financial-services internal-governance requirements fulfil the Article 26(5) monitoring obligation and the Article 26(6) log-retention obligation by complying with the governance arrangements under that financial-services law (Article 26(5) second subparagraph; Article 26(6) second subparagraph). Workplace deployers who are employers must inform workers' representatives and the affected workers BEFORE putting the high-risk system into service (Article 26(7)); applicable Union and national worker-information rules continue to apply.
```

**Branch answer:**

```
Deployer obligations: use the system per the instructions, assign human oversight to competent + trained natural persons, monitor operation, retain automatically generated logs, inform affected workers (for workplace use), and cooperate with market-surveillance authorities. Article 26 carve-outs: deployers that are financial institutions subject to Union financial-services internal-governance requirements fulfil the Article 26(5) monitoring obligation and the Article 26(6) log-retention obligation by complying with the governance arrangements under that financial-services law (Article 26(5) second subparagraph; Article 26(6) second subparagraph). Workplace deployers who are employers must inform workers' representatives and the affected workers BEFORE putting the high-risk system into service (Article 26(7)); applicable Union and national worker-information rules continue to apply.
```

## 79. live_answers:la_q31

**Q:** Is an AI system used to structure or deduplicate information for a use case listed in Annex III considered high-risk?

- **gold refs**: Annex III, Article 50, Article 6
- **base refs**: Article 6, Article 50, Annex III, Annex I
- **branch refs**: Article 6, Article 50, Annex III, Annex I
- **base scores**: {"answer_chars": 574.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 4.0, "ref_conc": 0.5625, "ref_loose": 1.0, "ref_strict": 0.8571428571428571}
- **branch scores**: {"answer_chars": 574.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 4.0, "ref_conc": 0.5625, "ref_loose": 1.0, "ref_strict": 0.8571428571428571}

**Base answer:**

```
The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.
```

**Branch answer:**

```
The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.
```

## 80. live_answers:la_q69 🚫 VETO

**Q:** Is an AI system that infers patients' emotions for a medical purpose prohibited under Article 5 of the EU AI Act?

- **gold refs**: Article 5
- **base refs**: Article 5.1.f  — DROPPED: Article 5
- **branch refs**: Article 5.1.f  — DROPPED: Article 5
- **base scores**: {"answer_chars": 850.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 1.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}
- **branch scores**: {"answer_chars": 850.0, "gold_dropped_exact": 1.0, "gold_dropped_head": 0.0, "kw_recall": 0.3333333333333333, "n_refs": 1.0, "ref_conc": 1.0, "ref_loose": 1.0, "ref_strict": 1.0}

**Base answer:**

```
Under Article 5.1.f, emotion recognition in the workplace and in educational institutions is prohibited, including monitoring employees or call-centre agents, with a narrow medical/safety carve-out for systems placed on the market for therapeutic or accident-prevention purposes. Real-time remote biometric identification by law enforcement is prohibited under Article 5 save for narrow, exhaustively-listed law-enforcement exceptions that each require prior judicial or administrative authorisation; under Article 5(5) Member States may enable those exceptions in national law and may set stricter national rules. Article 5(1)(c) carve-out: the social-scoring prohibition does not affect lawful evaluation practices of natural persons that are carried out for a specific purpose in accordance with Union and national law (Recital 31 final sentence).
```

**Branch answer:**

```
Under Article 5.1.f, emotion recognition in the workplace and in educational institutions is prohibited, including monitoring employees or call-centre agents, with a narrow medical/safety carve-out for systems placed on the market for therapeutic or accident-prevention purposes. Real-time remote biometric identification by law enforcement is prohibited under Article 5 save for narrow, exhaustively-listed law-enforcement exceptions that each require prior judicial or administrative authorisation; under Article 5(5) Member States may enable those exceptions in national law and may set stricter national rules. Article 5(1)(c) carve-out: the social-scoring prohibition does not affect lawful evaluation practices of natural persons that are carried out for a specific purpose in accordance with Union and national law (Recital 31 final sentence).
```

## 81. live_answers:la_q80

**Q:** What transparency obligation applies to AI-generated synthetic medical images used to augment a training dataset?

- **gold refs**: Article 50
- **base refs**: Article 50, Article 13
- **branch refs**: Article 50, Article 13
- **base scores**: {"answer_chars": 1151.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 2.0, "ref_conc": 0.25, "ref_loose": 1.0, "ref_strict": 0.6666666666666666}
- **branch scores**: {"answer_chars": 1151.0, "gold_dropped_exact": 0.0, "gold_dropped_head": 0.0, "kw_recall": 1.0, "n_refs": 2.0, "ref_conc": 0.25, "ref_loose": 1.0, "ref_strict": 0.6666666666666666}

**Base answer:**

```
Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties; both apply to the same system, not in the alternative. Transparency obligations split by actor: providers must ensure AI systems interacting with natural persons disclose their AI nature (Article 50(1)) and must mark synthetic AI-generated content in a machine-readable, detectable format (Article 50(2)); deployers must inform exposed persons when operating emotion-recognition or biometric-categorisation systems (Article 50(3)) and must label deepfakes as artificially generated or manipulated (Article 50(4)). Article 50(4) also requires deployers who use an AI system to generate or manipulate text published to inform the public on matters of public interest to disclose that the text was artificially generated or manipulated; this disclosure duty does not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for publishing it.
```

**Branch answer:**

```
Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties; both apply to the same system, not in the alternative. Transparency obligations split by actor: providers must ensure AI systems interacting with natural persons disclose their AI nature (Article 50(1)) and must mark synthetic AI-generated content in a machine-readable, detectable format (Article 50(2)); deployers must inform exposed persons when operating emotion-recognition or biometric-categorisation systems (Article 50(3)) and must label deepfakes as artificially generated or manipulated (Article 50(4)). Article 50(4) also requires deployers who use an AI system to generate or manipulate text published to inform the public on matters of public interest to disclose that the text was artificially generated or manipulated; this disclosure duty does not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for publishing it.
```

