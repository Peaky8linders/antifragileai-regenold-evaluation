# Citation Verification Report: stratum_transparency + stratum_gpai

**Verified against:** EU AI Act (Regulation (EU) 2024/1689, CELEX 32024R1689)  
**Primary sources used:**
- https://artificialintelligenceact.eu/article/<N>/ for Arts. 3, 6, 50, 51, 52, 53, 54, 55
- https://artificialintelligenceact.eu/recital/<N>/ for Recitals 132, 133, 134
- https://artificialintelligenceact.eu/annex/11/ and /annex/12/ for Annexes XI and XII
- Verification date: 2026-07-22

---

## CORRECTIONS NEEDED

No corrections required. All 36 distinct provision_ids verified against the primary text are accurate in existence, numbering, and substance.

| item_id | provision_id (as-is) | issue | correct value | source URL |
|---|---|---|---|---|
| — | — | No errors found | — | — |

---

## CONFIRMED

The following 36 distinct provision_ids were verified correct (existence, paragraph/sub-point numbering, and on-topic substance):

### Transparency (Art. 50 + Art. 3 definitions + Recitals)

- **`art_50__para_1`** — Provider obligation to inform natural persons they are interacting with an AI system (unless obvious from context). Art. 50 has 7 paragraphs total; para_1 confirmed. Source: https://artificialintelligenceact.eu/article/50/

- **`art_50__para_2`** — Provider obligation to mark AI-generated/manipulated audio, image, video, and text outputs in machine-readable format; carve-out for assistive/standard-editing functions. Source: https://artificialintelligenceact.eu/article/50/

- **`art_50__para_3`** — Deployer obligation to inform persons exposed to emotion-recognition or biometric-categorisation systems of their operation; GDPR compliance. Source: https://artificialintelligenceact.eu/article/50/

- **`art_50__para_4`** — Deployer obligation to disclose deep-fake content (sub-para 1) and AI-generated public-interest text (sub-para 2); carve-outs for law enforcement and artistic/editorial use. Source: https://artificialintelligenceact.eu/article/50/

- **`art_50__para_6`** — Paragraphs 1–4 shall not affect Chapter III requirements or other transparency obligations; confirms the Art. 50 and high-risk regimes are independent and additive. Para_6 EXISTS (Art. 50 has 7 paragraphs; para_5 = timing/accessibility; para_6 = Chapter III non-derogation; para_7 = codes of practice). Source: https://artificialintelligenceact.eu/article/50/

- **`art_3__para_39`** — Definition: "emotion recognition system" — AI system identifying or inferring emotions or intentions of natural persons on the basis of biometric data. Source: https://artificialintelligenceact.eu/article/3/

- **`art_3__para_40`** — Definition: "biometric categorisation system" — AI system assigning natural persons to specific categories on the basis of biometric data. Source: https://artificialintelligenceact.eu/article/3/

- **`art_3__para_60`** — Definition: "deep fake" — AI-generated or manipulated image, audio, or video content resembling existing persons, objects, places, entities, or events that would falsely appear authentic. Source: https://artificialintelligenceact.eu/article/3/

- **`art_6`** / **`art_6__para_2`** — High-risk AI system classification; Art. 6(2) states AI systems listed in Annex III shall be considered high-risk. Source: https://artificialintelligenceact.eu/article/6/

- **`recital_132`** — Interpretive rationale for Art. 50(1)/(3): AI systems interacting with persons or inferring emotions/biometric categories pose impersonation/deception risk; notification obligations justified regardless of high-risk status; accessibility for vulnerable groups. Source: https://artificialintelligenceact.eu/recital/132/

- **`recital_133`** — Interpretive rationale for Art. 50(2): providers of content-generating AI systems must embed machine-readable marking techniques (watermarks, metadata, cryptographic methods, fingerprints) to protect information ecosystem integrity; carve-out for assistive/standard-editing tools confirmed here too. Source: https://artificialintelligenceact.eu/recital/133/

- **`recital_134`** — Interpretive rationale for Art. 50(4) artistic carve-out: deployers of deep-fake systems must label artificially generated content; for satirical/artistic/creative works the obligation is narrowed to disclosure in a manner that does not hamper display or enjoyment; also confirms the AI-generated public-interest text sub-obligation. Source: https://artificialintelligenceact.eu/recital/134/

### GPAI (Arts. 51–55 + Art. 3 definitions + Annexes)

- **`art_3__para_63`** — Definition: "general-purpose AI model" — AI model trained with large amounts of data using self-supervision at scale, displaying significant generality and capable of competently performing a wide range of distinct tasks, integrable into downstream systems. Source: https://artificialintelligenceact.eu/article/3/

- **`art_3__para_66`** — Definition: "general-purpose AI system" — AI system based on a general-purpose AI model that can serve a variety of purposes, for direct use and integration into other AI systems. Distinct from the model (Art. 3(63)). Source: https://artificialintelligenceact.eu/article/3/

- **`art_51__para_1`** / **`art_51__para_1__point_a`** — Classification of GPAI models with systemic risk; Art. 51(1)(a) = classification where the model has high-impact capabilities evaluated by technical tools and benchmarks. Source: https://artificialintelligenceact.eu/article/51/

- **`art_51__para_2`** — Rebuttable presumption of systemic risk where cumulative training compute exceeds **10^25** floating-point operations (FLOP). Exponent confirmed as 10^25, NOT 10^24. Source: https://artificialintelligenceact.eu/article/51/

- **`art_51__para_3`** — Commission may revise the 10^25 FLOP threshold and update benchmarks via delegated acts. Source: https://artificialintelligenceact.eu/article/51/

- **`art_52__para_1`** — Notification obligation: provider must notify the Commission without delay, within two weeks of meeting the systemic-risk criterion, with supporting information. Source: https://artificialintelligenceact.eu/article/52/

- **`art_52__para_2`** — Provider rebuttal: provider may submit sufficiently substantiated arguments to demonstrate that, exceptionally, the model does not present systemic risks despite meeting the threshold. Source: https://artificialintelligenceact.eu/article/52/

- **`art_52__para_3`** — Commission rejection: if rebuttal arguments are insufficiently substantiated and provider cannot demonstrate absence of systemic risk, the Commission rejects them and the model is designated as systemic-risk. Source: https://artificialintelligenceact.eu/article/52/

- **`art_53__para_1`** — Base obligations applying to ALL GPAI model providers (regardless of systemic risk). Source: https://artificialintelligenceact.eu/article/53/

- **`art_53__para_1__point_a`** — Technical documentation: draw up and maintain documentation per Annex XI. Source: https://artificialintelligenceact.eu/article/53/

- **`art_53__para_1__point_b`** — Downstream information: make available information and documentation for downstream AI-system providers per Annex XII. Source: https://artificialintelligenceact.eu/article/53/

- **`art_53__para_1__point_c`** — Copyright policy: put in place a policy to comply with Union copyright and related-rights law, including respecting TDM opt-outs under Directive (EU) 2019/790 Art. 4(3). Source: https://artificialintelligenceact.eu/article/53/

- **`art_53__para_1__point_d`** — Training-content summary: draw up and make publicly available a sufficiently detailed summary of training content, using AI Office template. Source: https://artificialintelligenceact.eu/article/53/

- **`art_53__para_2`** — Open-source partial exemption: obligations at 53(1)(a) and (b) do not apply to GPAI models released under a free and open-source licence with publicly available parameters — BUT the exemption is disapplied for GPAI models with systemic risk. Note: 53(1)(c) and (d) remain applicable even for open-source releases. Source: https://artificialintelligenceact.eu/article/53/

- **`art_54__para_1`** — Authorised representative: third-country GPAI model providers must appoint an EU-established authorised representative before placing the model on the EU market. Source: https://artificialintelligenceact.eu/article/54/

- **`art_54__para_6`** — Open-source exemption from authorised-representative requirement for GPAI models released under free and open-source licences — with systemic-risk carve-out (exemption disapplied if model has systemic risk). Paragraph EXISTS; Art. 54 has exactly 6 paragraphs. Source: https://artificialintelligenceact.eu/article/54/

- **`art_55__para_1`** — Systemic-risk obligations applying exclusively to GPAI model providers whose models have been classified as presenting systemic risk. Source: https://artificialintelligenceact.eu/article/55/

- **`art_55__para_1__point_a`** — Model evaluation including adversarial testing (red teaming) in accordance with standardised protocols reflecting state of the art. Source: https://artificialintelligenceact.eu/article/55/

- **`art_55__para_1__point_b`** — Assessment and mitigation of possible systemic risks at Union level, including their sources. Source: https://artificialintelligenceact.eu/article/55/

- **`art_55__para_1__point_c`** — Track, document, and report serious incidents without undue delay to the AI Office (primary recipient) and, as appropriate, to national competent authorities. Source: https://artificialintelligenceact.eu/article/55/

- **`art_55__para_1__point_d`** — Cybersecurity: ensure adequate protection for the GPAI model and physical infrastructure. Source: https://artificialintelligenceact.eu/article/55/

- **`annex_XI`** — Technical documentation for GPAI model providers (referenced by Art. 53(1)(a)); Section 1 applies to all GPAI providers; Section 2 (evaluation, adversarial testing, architecture) applies only to systemic-risk models. Source: https://artificialintelligenceact.eu/annex/11/

- **`annex_XII`** — Transparency information for downstream providers of GPAI models (referenced by Art. 53(1)(b)); covers model descriptions, development processes, technical specifications, training data information, and integration requirements. Source: https://artificialintelligenceact.eu/annex/12/

---

## Hallucination Trap Integrity

Both hallucination-trap items were verified as correctly constructed:

- **`hard_transp_006`** (trap: Art. 43 conformity assessment): Art. 43 applies only to high-risk AI systems under Chapter III; it does not apply to Art. 50-only systems. The trap note's secondary claim — that Art. 50(5) concerns timing of information delivery, not registration — is accurate (Art. 50(5) verbatim: "...shall be provided to the natural persons concerned in a clear and distinguishable manner at the latest at the time of the first interaction or exposure..."). The non-existent "Art. 50(5) registration" obligation is correctly flagged as a hallucination trap.

- **`hard_gpai_006`** (trap: Art. 43 conformity assessment for GPAI providers): Confirmed that Art. 43 does not apply to GPAI model providers; their obligations are governed by Arts. 53–55.

---

## Notes on Structural Facts Verified

- Art. 50 has **7 paragraphs** (para_1 through para_7). The dataset cites up to para_6; para_7 (codes of practice) is not cited but exists. No dataset item incorrectly claims Art. 50 has only 5 or 6 paragraphs.
- Art. 51(2) threshold is **10^25 FLOP** — verified. The 10^24 figure (cited in `hard_gpai_004` gold answer as the lower/wrong threshold) is correctly identified as below the presumption threshold.
- Art. 54 has exactly **6 paragraphs**; `art_54__para_6` exists and is the open-source exemption.
- Art. 55 has **3 paragraphs**; sub-points (a)–(d) are under para_1 only.
- Art. 3(63) = general-purpose AI **model**; Art. 3(66) = general-purpose AI **system** — both confirmed at these exact index numbers.
