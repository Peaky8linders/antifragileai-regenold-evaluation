# Complete Evaluation Repository: Questions, Answers, Ground Truth & Forensic Analysis
**Date:** 2026-08-15  **Evaluation Scope:** 50 Live Evaluated Scenarios across 3 Gold Benchmark Suites  - **Part 1:** 20 Antifragile Human Expert-Graded Review Scenarios (with Verbatim Legal Critiques & Mistake Resolution Audits)  - **Part 2:** 10 Hardest Content-Level Decision-Boundary Scenarios (July-7 / SOTA)  - **Part 3:** 20 Cappelli et al. (Discover AI 2026) 5-Dimension Compliance Benchmark Scenarios (4 Annex III Domains $\times$ 5 Inquiries)
---
## Part 1: Antifragile Human Expert Review Q&A (20 Scenarios)
These 20 scenarios were originally evaluated by a senior EU legal expert. Each entry below details the question, live engine predicted answer, predicted references, ground truth answer, expected gold references, the verbatim expert reviewer remarks, and the granular mistake resolution audit.

### Scenario Q01: What risk categories are provided for AI systems?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.4500` | **ROUGE-L ($F_1$)** | `0.4505` |
| **Semantic Sim (SBERT)** | `0.6579` | **Keyword Recall** | `0.7143` |
| **Ref Loose (Recall)** | `0.5000` | **Ref Strict ($F_1$)** | `0.5455` |
| **Ref Conciseness** | `0.6944` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> The EU AI Act applies a risk-based framework with four tiers plus a parallel regime for general-purpose AI models. Unacceptable-risk practices are prohibited outright under Article 5; high-risk systems are classified under Article 6 (as a safety component of an Annex I product, or as one of the Annex III use cases) and carry the Chapter III Section 2 obligations; limited-risk systems carry the Article 50 transparency duties; and minimal-risk systems have no mandatory obligations. General-purpose AI models are governed separately under Articles 51 to 56, with stricter duties for models posing systemic risk.

**Predicted References:** `Article 5, Article 6, Article 50, Article 52, Article 53`  
**Latency:** `1567.78 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> The EU AI Act establishes a tiered risk framework. Article 5 sets the unacceptable-risk tier, banning eight prohibited practices outright. Article 6, via Annex I product-safety legislation and the Annex III use-case list, defines the high-risk tier. Limited-risk systems carry only Article 50 transparency duties, and general-purpose AI models are governed by a parallel regime under Articles 51 to 55.

**Expected Gold References:** `Article 5, Article 6, Annex I, Annex III, Article 50, Article 51`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
The answer is partially wrong and incomplete, plus an error. The question asks about risk categories, the AI Act establishes a tiered framework: unacceptable (Art. 5), high-risk (Art. 6 via Annex I and Annex III), plus GPAI Art. 51-55 as a parallel regime. The answer addresses only the unacceptable tier.
The error:  Art. 5(1)(c) prohibits social scoring without exclusion for public authorities.
Also citations list four sources (Art. 5, 6, Annex I, Annex III), but only Art. 5 is addressed in the body.
The enumeration also lists only five of the eight Art. 5(1) prohibitions, missing (d, e, f ).
```

#### 🛠️ Mistake Resolution Audit (3/4 Fixed — 75.0%)
- ✅ **RESOLVED** `[q01_m1]`: Frames social scoring as 'by public authorities'; Art 5(1)(c) has no public-authority limit in the final Regulation.
- ❌ **OPEN** `[q01_m2]`: Lists only 5 of 8 Art 5 prohibitions (missing predictive-policing, facial-scraping, workplace emotion).
- ✅ **RESOLVED** `[q01_m3]`: Addresses only the unacceptable tier; omits high-risk, limited-risk transparency, and the GPAI Art 51-55 regime.
- ✅ **RESOLVED** `[q01_m4]`: Omits the GPAI parallel regime entirely.

---

### Scenario Q02: What types of AI systems or practices are explicitly prohibited by the AI Act?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.7101` | **ROUGE-L ($F_1$)** | `0.7742` |
| **Semantic Sim (SBERT)** | `0.8321` | **Keyword Recall** | `1.0000` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `1.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Article 5 prohibits eight AI practices outright: subliminal or manipulative techniques causing significant harm, exploitation of vulnerabilities linked to age, disability, or socio-economic situation, social scoring leading to unjustified detrimental treatment, criminal-offence risk profiling of natural persons, untargeted scraping of facial images to build facial-recognition databases, emotion recognition in the workplace or educational institutions, biometric categorisation inferring sensitive attributes, and real-time remote biometric identification in publicly accessible spaces for law enforcement subject to the narrow Article 5(1)(h) exceptions.

**Predicted References:** `Article 5`  
**Latency:** `29.63 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> Article 5 prohibits eight categories of AI practice: subliminal or manipulative techniques causing significant harm; exploitation of vulnerabilities based on age, disability or socio-economic situation; social scoring leading to detrimental treatment in unrelated contexts, or treatment unjustified or disproportionate to the behaviour scored; predictive policing based solely on profiling; untargeted scraping of facial images to build recognition databases; emotion inference in workplaces and educational institutions; biometric categorisation inferring sensitive attributes; and real-time remote biometric identification in public spaces for law enforcement, subject to narrow exceptions.

**Expected Gold References:** `Article 5`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Half-right / partial enumeration, repeated error. Correctly identifies Art. 5 and the total count of eight. Then lists only three.
The "by public authorities" on social scoring is the same as Q1 error.
Citations include Annex II (the list of serious criminal offences, relevant only to the Art. 5(1)(h) tangential) and Art. 27 (FRIA, irrelevant to prohibitions).
```

#### 🛠️ Mistake Resolution Audit (3/3 Fixed — 100.0%)
- ✅ **RESOLVED** `[q02_m1]`: States eight but lists only three prohibitions.
- ✅ **RESOLVED** `[q02_m2]`: 'social scoring by public authorities' — same public-authority error as Q1.
- ✅ **RESOLVED** `[q02_m3]`: Cites Annex II and Article 27, both irrelevant to prohibitions.

---

### Scenario Q03: What is the definition of high risk?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.1087` | **ROUGE-L ($F_1$)** | `0.1290` |
| **Semantic Sim (SBERT)** | `0.2207` | **Keyword Recall** | `0.2500` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `1.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> In addition to the high-risk AI systems referred to in paragraph 1, AI systems referred to in Annex III shall be considered to be high-risk.

**Predicted References:** `Article 6, Annex I, Annex III`  
**Latency:** `995.31 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> Under Article 6 an AI system is high-risk by either of two routes. First, where it is a safety component of, or itself is, a product covered by Annex I Union harmonisation legislation that must undergo third-party conformity assessment (Article 6(1)). Second, where it falls within an Annex III use-case category (Article 6(2)). Article 6(3) exempts Annex III systems that perform only narrow procedural, preparatory or human-review-supporting tasks, unless they profile natural persons.

**Expected Gold References:** `Article 6, Annex I, Annex III`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Mostly correct, with two material omissions. The two-route framework is right and the Annex I legislation list is a reasonable abbreviation (omitting IVDR, pressure equipment, recreational craft, equipment for explosive atmospheres, and gas appliances).
First omission: the Annex I route requires the underlying product to undergo third-party conformity assessment under the sectoral legislation. This is Art 6(1)(b) and it is substantive for MedTech, a Class I medical device under MDR that doesn't need notified-body assessment doesn't automatically trigger AI Act high-risk via Art 6(1). It could potentially trigger it via Art. 6(2) and Annex III.
Second omission: Art. 6(3). An Annex III system is not considered high-risk if it performs (a) a narrow procedural task; (b) improvement of a previously completed human activity; (c) detection of decision-making patterns without replacing human review; or (d) a preparatory task, unless it profiles natural persons. The provider must document the self-assessment and register under Art. 49(2).
Omitting this overstates the high-risk perimeter materially. The answer provides a general frame
Citations list Art. 6 and Annex III but not Annex I, despite the answer targeting mostly the Annex I route.
```

#### 🛠️ Mistake Resolution Audit (1/3 Fixed — 33.3%)
- ❌ **OPEN** `[q03_m1]`: Omits that the Annex I route requires third-party conformity assessment (Art 6(1)(b)).
- ❌ **OPEN** `[q03_m2]`: Omits the Art 6(3) carve-outs for non-high-risk Annex III tasks.
- ✅ **RESOLVED** `[q03_m3]`: Citations omit Annex I despite the answer targeting that route.

---

### Scenario Q04: Which sectors or applications are considered high-risk under the regulation?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.1842` | **ROUGE-L ($F_1$)** | `0.1961` |
| **Semantic Sim (SBERT)** | `0.4488` | **Keyword Recall** | `0.5714` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `1.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Article 25(2) requires the initial provider and the new provider to cooperate along the value chain: the initial provider must make available the necessary information and provide the reasonably expected technical access and other assistance so that the new provider can meet its obligations, in particular the conformity assessment of high-risk AI systems. Under Annex III, Eight high-risk use-case categories: biometrics, critical infrastructure. Under Annex I, Union harmonisation legislation list.

**Predicted References:** `Article 6, Annex III, Annex I`  
**Latency:** `140.22 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> High-risk classification follows two routes under Article 6. The Annex III route covers eight use-case areas: biometrics, critical infrastructure, education, employment and worker management, essential private and public services, law enforcement, migration and border control, and administration of justice and democratic processes. The Annex I route covers AI that is a safety component of regulated products such as medical devices and machinery that require third-party conformity assessment.

**Expected Gold References:** `Article 6, Annex III, Annex I`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Half-right, and one structural omission. The eight Annex III areas are listed correctly. But "sectors or applications" means the Annex I as well and the answer omits this route entirely.
Citations include Article 25 (value-chain responsibilities). Art. 25  has no connection to which sectors are high-risk.
```

#### 🛠️ Mistake Resolution Audit (1/2 Fixed — 50.0%)
- ❌ **OPEN** `[q04_m1]`: Omits the Annex I product-safety route entirely.
- ✅ **RESOLVED** `[q04_m2]`: Cites Article 25 (value-chain), unrelated to which sectors are high-risk.

---

### Scenario Q05: How should users be informed when interacting with AI systems?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.3800` | **ROUGE-L ($F_1$)** | `0.4694` |
| **Semantic Sim (SBERT)** | `0.5789` | **Keyword Recall** | `0.8333` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `1.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Article 50(1) requires providers to design AI systems intended to interact directly with natural persons so they are informed they are interacting with AI, unless this is obvious. Article 50(2) requires providers of generative AI to mark synthetic audio, image, video, or text in a machine-readable, detectable format. Article 50(3) requires deployers of emotion recognition or biometric categorisation systems to inform exposed natural persons of their operation.

**Predicted References:** `Article 50`  
**Latency:** `60.22 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> Article 50 sets transparency duties split by role. Providers must ensure systems intended to interact directly with people disclose their AI nature unless obvious (Article 50(1)), and must mark machine-generated synthetic content in a detectable, machine-readable format (Article 50(2)). Deployers of emotion-recognition or biometric-categorisation systems must inform exposed persons (Article 50(3)), and deployers of deepfakes must disclose that the content is artificially generated (Article 50(4)).

**Expected Gold References:** `Article 50`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Mostly right, with a provider/deployer role error. Art. 50(1) interaction disclosure is correctly stated and correctly attributed to providers.
The role error: Art. 50(3) the obligation is on deployers, not providers. Lexy puts it on providers. The deepfake clause also conflates two distinct obligations: Art. 50(2) (providers of AI systems generating synthetic content must mark outputs in machine-readable format) and Art. 50(4) (deployers of deepfakes must disclose artificial generation). Lexy collapses the roles and obligations.
```

#### 🛠️ Mistake Resolution Audit (1/2 Fixed — 50.0%)
- ✅ **RESOLVED** `[q05_m1]`: Puts Art 50(3) (emotion/biometric disclosure) on providers; it is a deployer duty.
- ❌ **OPEN** `[q05_m2]`: Conflates Art 50(2) provider marking and Art 50(4) deployer deepfake disclosure.

---

### Scenario Q06: What are AI systems with minimal risks?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.4222` | **ROUGE-L ($F_1$)** | `0.5926` |
| **Semantic Sim (SBERT)** | `0.6522` | **Keyword Recall** | `0.8333` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `1.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Minimal-risk AI systems are the residual category: systems that are neither prohibited under Article 5, nor high-risk under Article 6 (as an Annex I safety component or an Annex III use case), nor subject to the Article 50 transparency duties, nor general-purpose AI models. Typical examples are AI-enabled spam filters, inventory-management tools, and AI in video games.

**Predicted References:** `Article 5, Article 6, Article 50`  
**Latency:** `82.14 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> Minimal-risk is the residual category: AI systems that are neither prohibited under Article 5, nor high-risk under Annex I or Annex III, nor subject to Article 50 transparency duties, nor general-purpose AI models. Such systems carry no mandatory obligations under the Act beyond the cross-cutting AI-literacy duty, though voluntary codes of conduct are encouraged.

**Expected Gold References:** `Article 5, Article 6, Article 50`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Half-right, partial definition and entirely irrelevant citations. Minimal-risk in the AI Act framework is the residual category, meaning systems that are neither prohibited under Art. 5, nor high-risk via Annex I, nor high-risk via Annex III, nor subject to Art. 50 transparency obligations, nor GPAI.
All  citations attach to high-risk systems.
```

#### 🛠️ Mistake Resolution Audit (2/2 Fixed — 100.0%)
- ✅ **RESOLVED** `[q06_m1]`: All six citations (Annex III, Arts 9/12/13/14/27) attach to high-risk systems, not minimal-risk.
- ✅ **RESOLVED** `[q06_m2]`: Defines minimal-risk only as 'outside the 8 high-risk categories'; misses prohibited/transparency/GPAI exclusions.

---

### Scenario Q07: What are the guiding principles established by the AI Act?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.4727` | **ROUGE-L ($F_1$)** | `0.4941` |
| **Semantic Sim (SBERT)** | `0.7065` | **Keyword Recall** | `1.0000` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `0.6667` |
| **Ref Conciseness** | `0.2500` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> The seven guiding principles of the EU AI Act are articulated in Recital 27 (the trustworthy-AI framework) and inform the human-centric purpose of Article 1: human agency and oversight; technical robustness and safety; privacy and data governance; transparency; diversity, non-discrimination and fairness; social and environmental wellbeing; and accountability. Article 4 operationalises these principles by requiring providers and deployers to ensure a sufficient level of AI literacy among their staff.

**Predicted References:** `Article 1, Article 4`  
**Latency:** `32.0 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> Recital 27 recalls the seven non-binding ethical principles for trustworthy AI developed by the AI HLEG, which the Act uses as the basis for codes of conduct: human agency and oversight; technical robustness and safety; privacy and data governance; transparency; diversity, non-discrimination and fairness; social and environmental well-being; and accountability. These inform the Act's human-centric purpose under Article 1.

**Expected Gold References:** `Article 1`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Wrong and topic-shift. The question asks about guiding principles. The answer has no relationship to the question.
The correct response would draw on Recital 27, which articulates seven principles for trustworthy AI: human agency and oversight; technical robustness and safety; privacy and data governance; transparency; diversity, non-discrimination and fairness; social and environmental well-being; accountability.
```

#### 🛠️ Mistake Resolution Audit (2/2 Fixed — 100.0%)
- ✅ **RESOLVED** `[q07_m1]`: Answered about GPAI authorised representative — entirely off-topic.
- ✅ **RESOLVED** `[q07_m2]`: Cited GPAI/authrep articles; should anchor on the trustworthy-AI principles.

---

### Scenario Q08: What is the definition of a "system of artificial intelligence"?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.9091` | **ROUGE-L ($F_1$)** | `0.9375` |
| **Semantic Sim (SBERT)** | `0.9302` | **Keyword Recall** | `1.0000` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `1.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> A machine-based system that is designed to operate with varying levels of autonomy and that may exhibit adaptiveness after deployment, and that, for explicit or implicit objectives, infers, from the input it receives, how to generate outputs such as predictions, content, recommendations, or decisions that can influence physical or virtual environments.

**Predicted References:** `Article 3.1`  
**Latency:** `44.24 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> Under Article 3(1) an AI system is a machine-based system designed to operate with varying levels of autonomy, that may exhibit adaptiveness after deployment, and that, for explicit or implicit objectives, infers from the input it receives how to generate outputs such as predictions, content, recommendations or decisions that can influence physical or virtual environments.

**Expected Gold References:** `Article 3`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Correct.
```

#### 🛠️ Mistake Resolution Audit (0/0 Fixed — 100.0%)
- *(No historical mistakes recorded on baseline for this item)*

---

### Scenario Q09: What are the penalties for violating the provisions of the regulation for high-risk AI systems?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.4151` | **ROUGE-L ($F_1$)** | `0.5051` |
| **Semantic Sim (SBERT)** | `0.6543` | **Keyword Recall** | `0.7500` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `1.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> For high-risk AI systems the applicable penalty ceiling is set by Article 99(4): administrative fines of up to EUR 15 000 000 or, for an undertaking, up to 3 % of total worldwide annual turnover, whichever is higher, for non-compliance with the obligations on providers, deployers, importers and distributors (every obligation other than the Article 5 prohibitions, which carry the higher Article 99(3) ceiling of EUR 35 000 000 or 7 %). Under Article 99(6), for SMEs and start-ups each fine is capped at the lower of the percentage or the fixed amount.

**Predicted References:** `Article 99`  
**Latency:** `28.86 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> For infringements relating to high-risk AI systems, Article 99(4) sets fines of up to EUR 15 000 000 or 3% of total worldwide annual turnover, whichever is higher. For SMEs and start-ups, Article 99(6) applies the lower of the two amounts. The most severe tier, Article 99(3) up to EUR 35 000 000 or 7%, is reserved for breaches of the Article 5 prohibitions.

**Expected Gold References:** `Article 99`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Wrong by omission. The question asks specifically about high-risk penalties. The substantively correct answer is Art. 99(4). SMEs benefit from a lower-of-two-amounts rule under Art 99(6).
Lexy recites Art. 99(1), the generic Member State obligation to establish effective, proportionate and dissuasive penalties. The overall art.99 cited is right.
```

#### 🛠️ Mistake Resolution Audit (2/2 Fixed — 100.0%)
- ✅ **RESOLVED** `[q09_m1]`: Recites generic Art 99(1); the high-risk-specific ceiling is Art 99(4) (EUR 15M/3%).
- ✅ **RESOLVED** `[q09_m2]`: Omits the SME lower-of-two-amounts rule (Art 99(6)).

---

### Scenario Q10: What is the difference between the deployer and the provider?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.4821` | **ROUGE-L ($F_1$)** | `0.6032` |
| **Semantic Sim (SBERT)** | `0.7077` | **Keyword Recall** | `1.0000` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `0.6667` |
| **Ref Conciseness** | `0.2500` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> A provider (Article 3(3)) develops an AI system, or has one developed, and places it on the market or puts it into service under its own name or trademark. A deployer (Article 3(4)) uses an AI system under its authority in the course of a professional activity, so the provider bears the design and conformity duties of Article 16 while the deployer bears the use-phase duties of Article 26. Under Article 25 a deployer, distributor, importer, or other third party becomes a provider, and assumes the Article 16 provider obligations, where it puts its name or trademark on a high-risk AI system already on the market, makes a substantial modification to such a system, or modifies a system's intended purpose so that it becomes high-risk.

**Predicted References:** `Article 3, Article 25, Article 16, Article 26`  
**Latency:** `44.5 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> Under Article 3, a provider develops an AI system (or has one developed) and places it on the market or puts it into service under its own name, while a deployer uses the system under its own authority, except for purely personal non-professional use. Under Article 25 a deployer becomes a provider with full Article 16 obligations if it puts its name on a high-risk system, substantially modifies it, or changes its intended purpose so it becomes high-risk.

**Expected Gold References:** `Article 3, Article 25`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Correct on substance.
A more complete answer would point on Art. 25 role transitions, a deployer becomes a provider with full Art. 16 obligations when they put their name on a high-risk system, substantially modify it, or change its intended purpose so it becomes high-risk.
Citations: Art. 17 (quality management) and 19 (automatic logs), are provider duties, not definitions.
```

#### 🛠️ Mistake Resolution Audit (2/2 Fixed — 100.0%)
- ✅ **RESOLVED** `[q10_m1]`: Cites Art 17 (QMS) and 19 (logs), which are provider duties, not definitions.
- ✅ **RESOLVED** `[q10_m2]`: Should add the Art 25 deployer-to-provider role transition.

---

### Scenario Q11: Does the technical documentation of a high-risk AI system require to provide specifications regarding the required hardware?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.5227` | **ROUGE-L ($F_1$)** | `0.5926` |
| **Semantic Sim (SBERT)** | `0.7230` | **Keyword Recall** | `1.0000` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `1.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Yes. Under Article 11, a provider must draw up technical documentation containing the information set out in Annex IV, which expressly requires a description of the hardware on which the AI system is intended to run (Annex IV point 1(e)) and, as part of the system's development description, the computational resources used to develop, train, test and validate it (Annex IV point 2(c)).

**Predicted References:** `Article 11, Annex IV`  
**Latency:** `31.87 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> Yes. Under Article 11 providers must draw up technical documentation meeting Annex IV before placing a high-risk system on the market. Hardware specifications fall within Annex IV point 1(e), the description of the hardware on which the system runs, and Annex IV point 2(c) additionally requires the computational resources used to develop, train, test and validate the system.

**Expected Gold References:** `Article 11, Annex IV`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Correct on substance, wrong sub-citation.
Hardware specification is required in Annex IV, point 1(e). Lexy's Annex IV.2.a points to methods and steps for development, which is unrelated to hardware.
A complete answer would also reference Annex IV.2(c), the computational resources used to develop, train, test and validate the AI system, part of the technical documentation file under Art 11.
```

#### 🛠️ Mistake Resolution Audit (2/2 Fixed — 100.0%)
- ✅ **RESOLVED** `[q11_m1]`: Cites Annex IV.2.a (development methods); hardware is Annex IV point 1(e).
- ✅ **RESOLVED** `[q11_m2]`: Should also reference Annex IV.2(c) (computational resources).

---

### Scenario Q12: Are AI systems intended for emotion recognition from biometric data always prohibited?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.7353` | **ROUGE-L ($F_1$)** | `0.7302` |
| **Semantic Sim (SBERT)** | `0.7989` | **Keyword Recall** | `0.6000` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `1.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Emotion recognition is not categorically prohibited under the AI Act; the prohibition in Article 5 only applies in workplaces and educational institutions, with a narrow medical/safety exception. Elsewhere the system is high-risk under Annex III.1(c) and triggers Article 50(3) transparency duties toward exposed persons.

**Predicted References:** `Article 5, Article 50.3, Article 5.1.f, Annex III.1.c, Article 50`  
**Latency:** `47.88 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> No. Emotion recognition is prohibited only in workplaces and educational institutions under Article 5(1)(f), subject to a narrow medical or safety exception. Elsewhere it is high-risk under Annex III point 1(c) (biometrics) and triggers Article 50(3) transparency duties toward the natural persons exposed to the system.

**Expected Gold References:** `Article 5, Annex III, Article 50`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Correct on substance, partly wrong sub-citation. The three-layer reasoning is right: the Article 5(1)(f).
Citation of  Annex III.5 is wrong. Emotion recognition is at Annex III.1(c)
For Art. 50, the precise reference is 50(3).
```

#### 🛠️ Mistake Resolution Audit (2/2 Fixed — 100.0%)
- ✅ **RESOLVED** `[q12_m1]`: Cites Annex III.5; emotion recognition is at Annex III point 1(c).
- ✅ **RESOLVED** `[q12_m2]`: Art 50 should be the precise 50(3).

---

### Scenario Q13: Is an AI that transcribes doctor–patient conversations prohibited? Or is it high-risk as per the use cases of Annex III of the AI Act?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.6591` | **ROUGE-L ($F_1$)** | `0.7711` |
| **Semantic Sim (SBERT)** | `0.7888` | **Keyword Recall** | `1.0000` |
| **Ref Loose (Recall)** | `0.7500` | **Ref Strict ($F_1$)** | `0.7500` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Transcribing doctor–patient conversations is not categorically prohibited under Article 5 nor listed in Annex III as a high-risk use case. It becomes high-risk under Article 6 only if deployed as a safety component of a medical device covered by Annex I (e.g. MDR or IVDR). Otherwise Article 50 transparency obligations may apply when the system interacts with patients.

**Predicted References:** `Annex III, Article 6, Article 5, Annex I`  
**Latency:** `71.54 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> Transcribing doctor-patient conversations is neither prohibited under Article 5 nor listed as a high-risk use case in Annex III. It becomes high-risk under Article 6 only if deployed as a safety component of a product covered by Annex I Union harmonisation legislation (MDR/IVDR) that is required to undergo third-party conformity assessment. Otherwise Article 50 transparency duties may apply where the system interacts with patients.

**Expected Gold References:** `Article 6, Annex I, Article 5, Article 50`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Correct.
Inaccurate citation:  Annex III.5 among the references despite the answer saying the system is not in Annex III.
```

#### 🛠️ Mistake Resolution Audit (1/1 Fixed — 100.0%)
- ✅ **RESOLVED** `[q13_m1]`: Cites Annex III.5 even though the answer says the system is NOT in Annex III.

---

### Scenario Q14: We are a medical device manufacturer building an AI system to analyze X-rays to detect tumors. Is this system classified as high-risk, and what conformity assessment is required?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.3571` | **ROUGE-L ($F_1$)** | `0.3559` |
| **Semantic Sim (SBERT)** | `0.6068` | **Keyword Recall** | `0.6250` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `0.5000` |
| **Ref Conciseness** | `0.1111` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> An AI system that is a safety component of, or is itself, a product covered by the Union harmonisation legislation in Annex I (for example a medical device under the MDR or IVDR), where that product must undergo a third-party conformity assessment, is high-risk under Article 6(1). The applicable conformity-assessment procedure is set out in Article 43, carried out under the relevant sectoral legislation with notified-body involvement where that legislation requires it. The full Chapter III Section 2 provider obligations then stack on top of the sectoral requirements, including effective human oversight by qualified operators under Article 14 and continuous post-market monitoring under Article 72 alongside the equivalent medical-device surveillance duties.

**Predicted References:** `Article 6, Article 43, Annex I, Article 5, Article 9, Article 10, Article 11, Article 12, Article 13`  
**Latency:** `44.0 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> Yes, it is high-risk under Article 6(1): an AI system that is a safety component of a medical device covered by Annex I (MDR/IVDR) is high-risk where the device requires third-party conformity assessment, which a tumour-detecting X-ray device does. Under Article 43(3) the AI Act conformity assessment is integrated into the MDR notified-body procedure as a single assessment, and the full Chapter III Section 2 obligations (Articles 8 to 15) apply.

**Expected Gold References:** `Article 6, Annex I, Article 43`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Correct on the rule, but generic on the specific case application. Meaning that the answer doesn't apply the rule to the X-ray scenario, doesn’t identify device class under MDR, to confirm high-risk under Art. 6(1) and reference Art. 43(3), for conformity assessment to be integrated into the MDR notified body assessment, one unified procedure for the manufacturer.
Citations: Art. 5 and Annex III, not relevant to Art. 6(1)/Annex I scenario.
```

#### 🛠️ Mistake Resolution Audit (0/2 Fixed — 0.0%)
- ❌ **OPEN** `[q14_m1]`: States the rule but does not apply it to the X-ray case (device class, Art 43(3) integrated MDR assessment).
- ❌ **OPEN** `[q14_m2]`: Cites Art 5 and Annex III, irrelevant to the Art 6(1)/Annex I scenario.

---

### Scenario Q15: Can a hospital use an AI system to sort patients based on their biometric data to determine priority for an experimental clinical trial?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.4247` | **ROUGE-L ($F_1$)** | `0.4160` |
| **Semantic Sim (SBERT)** | `0.5813` | **Keyword Recall** | `0.8333` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `0.8571` |
| **Ref Conciseness** | `0.5625` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> AI used for emergency healthcare patient triage, or to dispatch or prioritise emergency first-response services, is high-risk under Annex III(5)(d) (Article 6(2)). Selecting or prioritising patients for a clinical trial is not itself a listed Annex III use case, so it is high-risk only where it determines access to or eligibility for essential healthcare services, or where it categorises natural persons by sensitive attributes (Annex III(1)(b)). Such biometric categorisation is prohibited under Article 5(1)(g) where it deduces race, political opinions, trade-union membership, religious or philosophical beliefs, sex life, or sexual orientation.

**Predicted References:** `Article 5.1.g, Article 6, Annex III, Annex I`  
**Latency:** `56.25 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> It depends on the function. Annex III point 5(d) covers emergency triage and dispatch, not clinical-trial selection; trial selection may instead fall under Annex III point 5(a) (eligibility, by or on behalf of a public authority, for essential public assistance benefits and services including healthcare) or outside Annex III entirely, governed by the Medical Devices and Clinical Trials Regulations. Separately, it is prohibited under Article 5(1)(g) only if the biometric categorisation infers an attribute on the closed list: race, political opinions, trade-union membership, religious or philosophical beliefs, sex life or sexual orientation.

**Expected Gold References:** `Article 5, Annex III, Article 6`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Half-right.
The Annex III.5(d) citation itself is correctly identified, and it covers emergency calls, triage, dispatch.
But the question is about clinical trial selection, not emergency response. A clinical-trial selection process doesn't sit there. Depending on the trial's structure, it might fall under Annex III.5(a) (eligibility for essential public assistance benefits and services including healthcare services, where the trial offers public-funded access to healthcare), or it might fall outside Annex III entirely and be governed instead by MDR and the Clinical Trials Regulation.
The Art 5(1)(g) conditional is right, but loose on specificity. The prohibition triggers only when biometric categorisation infers from a closed list: race, political opinions, trade union membership, religious or philosophical beliefs, sex life, sexual orientation. Biometric data to determine priority doesn't automatically infer those attributes, it depends entirely on what's being inferred from what. The "if the system also uses biometric categorisation to infer sensitive attributes" framing is correct as a conditional but doesn't name the closed-list rule.
```

#### 🛠️ Mistake Resolution Audit (0/2 Fixed — 0.0%)
- ❌ **OPEN** `[q15_m1]`: Anchors on Annex III 5(d) (emergency triage); clinical-trial selection is not 5(d), likely 5(a) or outside Annex III.
- ❌ **OPEN** `[q15_m2]`: Art 5(1)(g) conditional correct but does not name the closed list of sensitive attributes.

---

### Scenario Q16: Our life sciences startup developed a general-purpose AI model trained on massive amounts of genomic data. What transparency obligations apply to us?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.2518` | **ROUGE-L ($F_1$)** | `0.1957` |
| **Semantic Sim (SBERT)** | `0.5763` | **Keyword Recall** | `0.8889` |
| **Ref Loose (Recall)** | `0.3333` | **Ref Strict ($F_1$)** | `0.4000` |
| **Ref Conciseness** | `0.4444` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> GPAI provider obligations: maintain technical documentation per Annex XI, supply downstream-provider information per Annex XII, implement a copyright policy, and publish a sufficiently detailed training-data summary. Where the model meets the Article 51 systemic-risk threshold (10^25 FLOPs cumulative training compute), the additional Article 55 obligations apply on top. Training-data content summary, the Commission adopted the mandatory disclosure template on 24 July 2025. Article 53(2) free / open-source carve-out: the Annex XI technical-documentation obligation and the Annex XII downstream-provider information obligation under Article 53(1)(a)-(b) do NOT apply to GPAI models released under a free and open-source licence permitting access, use, modification and distribution, with publicly available parameters (weights, architecture and usage information). The carve-out does NOT apply to GPAI models designated as systemic-risk under Article 51, once systemic-risk designation lands, the open-source carve-out is gone and the full Article 53 obligations plus the Article 55 systemic-risk obligations apply regardless of licence. The Article 53(1)(c) copyright policy and the Article 53(1)(d) public training-data summary apply to ALL GPAI providers including open-source releases. Transparency obligations split by actor: providers must ensure AI systems interacting with natural persons disclose their AI nature (Article 50(1)) and must mark synthetic AI-generated content in a machine-readable, detectable format (Article 50(2)); deployers must inform exposed persons when operating emotion-recognition or biometric-categorisation systems (Article 50(3)) and must label deepfakes as artificially generated or manipulated (Article 50(4)). Article 50(4) also requires deployers who use an AI system to generate or manipulate text published to inform the public on matters of public interest to disclose that the text was artificially generated or manipulated; this disclosure duty does not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for publishing it.

**Predicted References:** `Article 53.1, Article 50`  
**Latency:** `54.72 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> As a general-purpose AI model provider you must, under Article 53(1): keep technical documentation (Annex XI), provide downstream-provider information (Annex XII), implement a copyright policy, and publish a sufficiently detailed training-data summary. Whether the additional systemic-risk obligations of Article 55 apply turns on the Article 51 threshold, presumed at 10^25 FLOPs of cumulative training compute; a startup model typically falls below it, but that is the gating question.

**Expected Gold References:** `Article 53, Article 51, Article 55`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Correct on substance. All four Article 53(1) GPAI provider obligations are correctly identified.
The sentence about Art 113 is unrelated to the question.
A thorough answer would also refer to Art. 55 systemic-risk obligations. Also Art. 51, if the model meets the systemic-risk threshold (currently 10^25 FLOPs in cumulative training compute). For a startup model, this typically won't apply, but it should be named as the gating question, as the question mentions “massive amounts of genomic data”.
```

#### 🛠️ Mistake Resolution Audit (2/2 Fixed — 100.0%)
- ✅ **RESOLVED** `[q16_m1]`: Adds an Art 113 entry-into-force sentence unrelated to the question.
- ✅ **RESOLVED** `[q16_m2]`: Should name the Art 51 systemic-risk threshold (10^25 FLOPs) and Art 55 obligations as the gating question.

---

### Scenario Q17: We are a university lab developing an AI model exclusively for scientific research and development into new life science drugs. Does the AI Act apply to our model before it is released to the market?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.4194` | **ROUGE-L ($F_1$)** | `0.3419` |
| **Semantic Sim (SBERT)** | `0.7020` | **Keyword Recall** | `1.0000` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `1.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Under Article 2(6), the Regulation does not apply to AI systems or models, including their output, specifically developed and put into service for the sole purpose of scientific research and development. Article 2(8) further excludes any research, testing or development activity on AI systems prior to their being placed on the market or put into service, except testing in real-world conditions. The Act's obligations therefore attach only once the system leaves pure R&D and is placed on the market or put into service, at which point the operator's duties follow the system's risk classification.

**Predicted References:** `Article 2`  
**Latency:** `40.18 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> No. Article 2(6) excludes AI systems and models developed and used solely for scientific research and development, so the model is outside the Act while used only for that purpose and not placed on the market or put into service. The exclusion ends on market placement or putting into service, at which point the Act's obligations attach according to the model's risk classification. Article 2(8) separately exempts research, testing and development prior to placing on the market or putting into service, but expressly carves testing in real-world conditions out of that exemption.

**Expected Gold References:** `Article 2`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Correct.
A more precise citation Art 2(6). The answer could also reference Art 2(8) on pre-market testing in real-world conditions, which is related but distinct for the testing phase between R&D and market placement.
```

#### 🛠️ Mistake Resolution Audit (1/1 Fixed — 100.0%)
- ✅ **RESOLVED** `[q17_m1]`: Could cite the precise Art 2(6) (R&D exclusion) and Art 2(8) (pre-market testing).

---

### Scenario Q18: We are developing a generative AI chatbot that will be deployed on a hospital website to answer general patient queries. What transparency obligations apply?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.2243` | **ROUGE-L ($F_1$)** | `0.2553` |
| **Semantic Sim (SBERT)** | `0.5324` | **Keyword Recall** | `0.4000` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `0.3333` |
| **Ref Conciseness** | `0.0400` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Transparency obligations split by actor: providers must ensure AI systems interacting with natural persons disclose their AI nature (Article 50(1)) and must mark synthetic AI-generated content in a machine-readable, detectable format (Article 50(2)); deployers must inform exposed persons when operating emotion-recognition or biometric-categorisation systems (Article 50(3)) and must label deepfakes as artificially generated or manipulated (Article 50(4)). Article 50(4) also requires deployers who use an AI system to generate or manipulate text published to inform the public on matters of public interest to disclose that the text was artificially generated or manipulated; this disclosure duty does not apply where the use is authorised by law to detect, prevent, investigate or prosecute criminal offences, or where the content has undergone human review or editorial control and a natural or legal person holds editorial responsibility for publishing it. Requires a documented, iterative risk-management system across the AI system's lifecycle. Article 57 requires each Member State to establish at least one AI regulatory sandbox at national. Article 10 requires training, validation, and test datasets to be relevant, representative.

**Predicted References:** `Article 50.2, Article 50.1, Article 9, Article 57, Article 59, Article 10`  
**Latency:** `62.65 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> First classify it: a general patient-query chatbot is most likely limited-risk, not high-risk, so Article 13 high-risk transparency does not apply and Article 50 governs alone. Under Article 50(1) the provider must ensure each user is told they are interacting with an AI system, and under Article 50(2) any generated content must be marked in a machine-readable format. The hospital deploying a third-party chatbot is the deployer, so deployer duties attach to it — Article 50(4) only where the system in fact generates deepfake content or text published to inform the public on matters of public interest.

**Expected Gold References:** `Article 50`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Half-right. The horizontal principle, that Art. 50 transparency obligations apply regardless of risk tier and apply cumulatively on Art 13 where both apply, is conceptually correct.
The classification question within the answer is missing: is this chatbot high-risk? A general patient-query chatbot on a hospital website probably isn't. It's not Annex III.5(d) emergency triage. It's not Annex III.5(a) eligibility-for-benefits unless it determines eligibility. Most likely it's limited-risk, Art. 50 alone, not high-risk plus Art. 50. The answer asserts the cumulative framework without doing the classification analysis that determines whether Art. 13 applies at all.
Provider/deployer role unclear. It uses "operator" for both Art. 50(1) (provider obligation) and Art. 50(2) (provider-of-synthetic-content obligation). For a hospital deploying a third-party chatbot, the hospital is the deployer, Art. 50(4) (deepfake disclosure where applicable) would attach to the hospital.
Citations include Annex I and Art. 6, but are not addressed in the body.
Citations: Article 13, Article 50, Annex III, Annex I, Article 6
```

#### 🛠️ Mistake Resolution Audit (2/3 Fixed — 66.7%)
- ❌ **OPEN** `[q18_m1]`: Asserts cumulative Art 13 + Art 50 without classifying the chatbot; it is most likely limited-risk (Art 50 alone).
- ✅ **RESOLVED** `[q18_m2]`: Uses 'operator' for both provider and deployer duties; the hospital is the deployer.
- ✅ **RESOLVED** `[q18_m3]`: Cites Annex I and Art 6 but does not address them in the body.

---

### Scenario Q19: A pharmaceutical company wants to use an AI system to monitor the emotions and stress levels of their manufacturing line workers to improve efficiency. Is this allowed?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.1538` | **ROUGE-L ($F_1$)** | `0.1714` |
| **Semantic Sim (SBERT)** | `0.4096` | **Keyword Recall** | `1.0000` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `1.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Under Article 5.1.f, emotion recognition in the workplace and in educational institutions is prohibited, including monitoring employees or call-centre agents, with a narrow medical/safety carve-out for systems placed on the market for therapeutic or accident-prevention purposes. Emotion recognition in the workplace and education contexts is prohibited under Article 5(1)(f), with narrow medical and safety carve-outs. Article 26 carve-outs: deployers that are financial institutions subject to Union financial-services internal-governance requirements fulfil the Article 26(5) monitoring obligation and the Article 26(6) log-retention obligation by complying with the governance arrangements under that financial-services law (Article 26(5) second subparagraph; Article 26(6) second subparagraph).

**Predicted References:** `Article 5.1.f`  
**Latency:** `109.1 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> No. Article 5(1)(f) prohibits AI systems that infer the emotions of workers in workplace settings, and deploying one to improve manufacturing efficiency falls squarely within the ban. The only carve-out is where the system is intended to be put in place or placed on the market for medical or safety reasons, such as fatigue detection to prevent accidents; efficiency improvement does not qualify.

**Expected Gold References:** `Article 5`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Correct.
```

#### 🛠️ Mistake Resolution Audit (0/0 Fixed — 100.0%)
- *(No historical mistakes recorded on baseline for this item)*

---

### Scenario Q20: Is an AI system intended to be used as a safety component in robotic surgery considered high-risk under the AI Act?
| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.3788` | **ROUGE-L ($F_1$)** | `0.4107` |
| **Semantic Sim (SBERT)** | `0.6547` | **Keyword Recall** | `0.7778` |
| **Ref Loose (Recall)** | `0.7500` | **Ref Strict ($F_1$)** | `0.8571` |
| **Ref Conciseness** | `0.5625` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Yes. An AI system intended as a safety component of a robotic surgical device is high-risk under Article 6(1) because a surgical robot is a Class IIb or Class III medical device requiring notified-body conformity assessment under Article 43. Since the AI operates in a real-time control loop, Article 14 requires robust human oversight measures to allow the surgeon to override or reverse decisions. Under Article 72 and Article 73, the provider must establish post-market monitoring and report serious incidents, coordinating with the Medical Device Regulation Article 83 for layered surveillance.

**Predicted References:** `Article 6.1, Article 6, Article 14, Article 72`  
**Latency:** `56.54 ms`

#### 🔸 Ground Truth Answer (Expert Gold)
> Yes. A robotic-surgery AI safety component is part of a medical device that is typically Class IIb or III under MDR and requires notified-body conformity assessment, so it is high-risk under Article 6(1). Beyond the rule, real-time involvement in the surgical control loop engages the Article 14 human-oversight design requirements and layered post-market monitoring under AI Act Article 72 alongside MDR Article 83.

**Expected Gold References:** `Article 6, Annex I, Article 14, Article 72`

#### ⚖️ Verbatim Human Expert Reviewer Critique
```text
Correct on the rule. Generic on application.
Robotic surgery devices are typically Class IIb or III under MDR (Rule 12 or Rule 22), which require notified-body conformity assessment, so AI components are high-risk under Article 6(1). Correct.
The answer doesn’t engage with what's specifically at stake in robotic surgery: real-time AI involvement in the control loop, the Art. 14 human-oversight design requirements and the layered post-market surveillance under both MDR Art 83 and AI Act Art 72.
The answer refers to any medical-device scenario without further analysis.
```

#### 🛠️ Mistake Resolution Audit (1/1 Fixed — 100.0%)
- ✅ **RESOLVED** `[q20_m1]`: Generic medical-device rule; does not engage robotic-surgery specifics (Art 14 human oversight, Art 72 post-market).

---

## Part 2: Hardest Decision-Boundary & Sectoral Scenarios (10 Scenarios)
These 10 content-hard scenarios represent complex statutory boundaries: Article 6(3) derogations, GPAI $10^{25}$ FLOPs systemic compute thresholds, MedTech MDR notified body integration, Article 10(5) special data processing, Article 25 value chain handoffs, Article 27 FRIA, Article 73 incident reporting clocks, and Article 99 fine ceilings.

### Scenario: `hard_july7_01_emotion_workplace`
**Category:** *Borderline Prohibition & Exception*  
**Question:** Is an AI system that detects worker fatigue and emotional stress in a manufacturing plant prohibited under the EU AI Act?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.1000` | **ROUGE-L ($F_1$)** | `0.1389` |
| **Semantic Sim (SBERT)** | `0.3283` | **Keyword Recall** | `0.6667` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `0.3333` |
| **Ref Conciseness** | `0.0400` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> The system described is not among the practices prohibited under Article 5 (social scoring, untargeted facial-image scraping, manipulative or exploitative techniques, and the other exhaustively-listed bans). Whether it is high-risk turns on Article 6: it is high-risk only if it is a safety component of a product regulated under Annex I (for example a medical device under the MDR or IVDR) or falls within one of the Annex III use cases. Otherwise it is limited- or minimal-risk, subject mainly to the Article 50 transparency duties where it interacts directly with people.

**Predicted References:** `Article 5, Article 6, Article 50, Annex III, Annex I`  
**Latency:** `79.76 ms`

#### 🔸 Ground Truth Answer
> Emotion-recognition AI systems in the workplace are prohibited under Article 5(1)(f), except where placed on the market or put into service strictly for medical or safety reasons.

**Expected Gold References:** `Article 5.1.f, Article 5`


---

### Scenario: `hard_july7_02_gpai_systemic`
**Category:** *GPAI & Systemic Risk Boundary*  
**Question:** What criteria trigger the systemic risk classification for a general-purpose AI model, and what additional obligations apply to its provider?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.1569` | **ROUGE-L ($F_1$)** | `0.1176` |
| **Semantic Sim (SBERT)** | `0.3402` | **Keyword Recall** | `0.5833` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `0.5714` |
| **Ref Conciseness** | `0.1600` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Article 25(2) requires the initial provider and the new provider to cooperate along the value chain: the initial provider must make available the necessary information and provide the reasonably expected technical access and other assistance so that the new provider can meet its obligations, in particular the conformity assessment of high-risk AI systems. Article 25(4) is a separate duty: the high-risk provider and third-party suppliers of AI systems, tools, services, components or processes used in or integrated into a high-risk AI system must specify, by written agreement, the necessary information, capabilities, technical access and other assistance, except for third parties making tools, services, processes or components (other than general-purpose AI models) accessible to the public under a free and open-source licence. For general-purpose AI models, the one-third fine-tune rule (per the Commission's 18 July 2025 GPAI Guidelines, anchored on Article 51) makes the downstream modifier a new provider when additional training compute exceeds 1/3 of the base model's compute, or 1/3 of the 10^25 FLOPs systemic threshold (~3.3×10^24 FLOPs) when base compute is unknown.

**Predicted References:** `Article 55, Article 53, Article 51, Article 56, Article 16`  
**Latency:** `96.24 ms`

#### 🔸 Ground Truth Answer
> Under Article 51, a general-purpose AI model is presumed to have systemic risk if its cumulative compute during training exceeds 10^25 FLOPs. Providers of systemic GPAI models must perform model evaluation (Article 55(1)(a)), assess and mitigate systemic risks (Article 55(1)(b)), report serious incidents (Article 55(1)(c)), and ensure adequate cybersecurity protection (Article 55(1)(d)).

**Expected Gold References:** `Article 51, Article 55`


---

### Scenario: `hard_july7_03_article_6_3_derogation`
**Category:** *Complex Decision Boundary*  
**Question:** When is an AI system listed in Annex III exempt from being classified as high-risk under Article 6(3)?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.5085` | **ROUGE-L ($F_1$)** | `0.6078` |
| **Semantic Sim (SBERT)** | `0.6516` | **Keyword Recall** | `0.8889` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `0.8000` |
| **Ref Conciseness** | `0.4444` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Under Article 6(3), an Annex III system is not high-risk where it poses no significant risk of harm and meets one of four conditions: it performs a narrow procedural task, it improves the result of a previously completed human activity, it detects decision-making patterns or deviations without replacing or influencing the human assessment, or it performs a preparatory task. Under Article 6(3), this exception never applies where the system profiles natural persons. The provider must document the assessment before placing the system on the market and register it under Article 49(2).

**Predicted References:** `Article 6.3, Article 49.2, Article 6, Annex III, Article 49`  
**Latency:** `84.96 ms`

#### 🔸 Ground Truth Answer
> An Annex III AI system is not high-risk if it does not pose a significant risk of harm to health, safety, or fundamental rights and fulfills at least one of four conditions under Article 6(3): (a) performs a narrow procedural task, (b) improves the result of a previous human activity, (c) detects decision patterns without replacing human assessment, or (d) performs a preparatory task. Profiling natural persons always prevents this exemption.

**Expected Gold References:** `Article 6.3, Article 6, Annex III`


---

### Scenario: `hard_july7_04_medtech_notified_body`
**Category:** *Cross-Framework & Sectoral MedTech Integration*  
**Question:** What conformity assessment procedure applies to an AI software classified as a high-risk medical device under MDR and the EU AI Act?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.2424` | **ROUGE-L ($F_1$)** | `0.1782` |
| **Semantic Sim (SBERT)** | `0.4953` | **Keyword Recall** | `0.7778` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `0.8571` |
| **Ref Conciseness** | `0.5625` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Requires providers of high-risk AI to undergo a conformity assessment: internal-control procedure (Under Annex VI, Conformity-assessment procedure based on internal control: provider verifies the QMS conforms to Article 17, examines the technical documentation, verifies design + development + post-market plan; no notified-body involvement required.) for Annex-III systems where harmonised standards / common specifications are applied, otherwise notified-body procedure (Annex VII); for Annex-I products, Article 43(3) integrates the AI Act assessment into the sectoral third-party conformity-assessment procedure (for a medical device, the MDR notified-body assessment), one single procedure covering both regimes.

**Predicted References:** `Article 43, Article 6, Annex I, Annex VI`  
**Latency:** `92.13 ms`

#### 🔸 Ground Truth Answer
> Under Article 43(3), high-risk AI systems that are safety components of medical devices undergo a single, integrated conformity assessment procedure under Regulation (EU) 2017/745 (MDR) involving a notified body competent for both medical devices and AI requirements.

**Expected Gold References:** `Article 43.3, Article 43, Annex I, Article 6.1`


---

### Scenario: `hard_july7_05_article_10_special_data`
**Category:** *Two-Article Conflict & Reconciliation*  
**Question:** Does the EU AI Act allow the processing of special categories of personal data to identify and correct bias in high-risk AI models?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.3478` | **ROUGE-L ($F_1$)** | `0.4423` |
| **Semantic Sim (SBERT)** | `0.5793` | **Keyword Recall** | `0.7778` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `1.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Under Article 10(5), a provider of a high-risk AI system may exceptionally process special categories of personal data only to the extent strictly necessary to ensure bias detection and correction, subject to appropriate safeguards. Article 10(5) requires all of the following: the bias work cannot be done with other data, including synthetic or anonymised data (a); technical limits on re-use plus state-of-the-art security and pseudonymisation (b); strict, documented access controls to prevent misuse (c); no transmission or transfer to other parties (d); deletion once the bias is corrected or the retention period ends, whichever is first (e); and records of processing documenting why it was strictly necessary (f).

**Predicted References:** `Article 10.5, Article 10`  
**Latency:** `163.35 ms`

#### 🔸 Ground Truth Answer
> Yes, Article 10(5) provides a specific derogation permitting providers of high-risk AI systems to process special categories of personal data strictly to the extent necessary for bias detection and correction, subject to appropriate safeguards including pseudonymization, encryption, and strict access controls, without prejudice to GDPR.

**Expected Gold References:** `Article 10.5, Article 10`


---

### Scenario: `hard_july7_06_value_chain_transition`
**Category:** *Complex Decision Boundary*  
**Question:** Under what circumstances does a downstream deployer or distributor become legally classified as a provider under Article 25?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.1379` | **ROUGE-L ($F_1$)** | `0.2195` |
| **Semantic Sim (SBERT)** | `0.3917` | **Keyword Recall** | `0.3333` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `1.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Article 25(4) is a separate duty: the high-risk provider and third-party suppliers of AI systems, tools, services, components or processes used in or integrated into a high-risk AI system must specify, by written agreement, the necessary information, capabilities, technical access and other assistance, except for third parties making tools, services, processes or components (other than general-purpose AI models) accessible to the public under a free and open-source licence.

**Predicted References:** `Article 25`  
**Latency:** `80.37 ms`

#### 🔸 Ground Truth Answer
> Under Article 25(1), any distributor, importer, deployer, or third party is considered a provider and assumes all provider obligations if they: (a) put their name or trademark on a high-risk AI system, (b) make a substantial modification to a high-risk AI system, or (c) modify the intended purpose of an AI system such that it becomes high-risk.

**Expected Gold References:** `Article 25.1, Article 25`


---

### Scenario: `hard_july7_07_fria_article_27`
**Category:** *Complex Decision Boundary*  
**Question:** Who is obligated to perform a Fundamental Rights Impact Assessment under Article 27, and what must it include?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.2632` | **ROUGE-L ($F_1$)** | `0.3117` |
| **Semantic Sim (SBERT)** | `0.5097` | **Keyword Recall** | `0.3846` |
| **Ref Loose (Recall)** | `0.5000` | **Ref Strict ($F_1$)** | `0.6667` |
| **Ref Conciseness** | `0.2500` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Deployers of certain high-risk AI systems (Annex III + public-sector deployers) must perform a Fundamental Rights Impact Assessment before first use, covering deployment process, affected persons, specific risks, human-oversight measures, and complaints workflows.

**Predicted References:** `Article 27`  
**Latency:** `288.78 ms`

#### 🔸 Ground Truth Answer
> Under Article 27, deployers that are bodies governed by public law or private entities providing public services, as well as deployers of high-risk AI in credit scoring and life/health insurance, must perform a FRIA prior to putting the system into service. The assessment must detail intended processes, timeframe, affected natural persons, specific fundamental rights risks, human oversight measures, and mitigation plans.

**Expected Gold References:** `Article 27, Article 26`


---

### Scenario: `hard_july7_08_serious_incident_clocks`
**Category:** *Cross-Framework & Sectoral MedTech Integration*  
**Question:** What are the mandatory reporting deadlines for serious incidents under Article 73 of the EU AI Act?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.0508` | **ROUGE-L ($F_1$)** | `0.1000` |
| **Semantic Sim (SBERT)** | `0.3010` | **Keyword Recall** | `0.3000` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `1.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> For high-risk AI systems which are safety components of devices, or are themselves devices, covered by Regulations (EU) 2017/745 and (EU) 2017/746, the notification of serious incidents shall be limited to those referred to in Article 3, point (49)(c) of this Regulation, and shall be made to the national competent authority chosen for that purpose by the Member States where the incident occurred.

**Predicted References:** `Article 73`  
**Latency:** `49.8 ms`

#### 🔸 Ground Truth Answer
> Under Article 73, providers must report serious incidents immediately and no later than: (a) 15 days generally after becoming aware (Article 73(2)), including where the incident is serious harm to a person's health, (b) 2 days in the event of a widespread infringement or a serious and irreversible disruption of critical infrastructure (Article 73(3)), or (c) 10 days in the event of the death of a person (Article 73(4)).

**Expected Gold References:** `Article 73`


---

### Scenario: `hard_july7_09_annex_iv_technical_file`
**Category:** *Complex Decision Boundary*  
**Question:** What specific elements must be documented in the technical documentation of a high-risk AI system under Annex IV?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.2826` | **ROUGE-L ($F_1$)** | `0.2899` |
| **Semantic Sim (SBERT)** | `0.4314` | **Keyword Recall** | `0.3333` |
| **Ref Loose (Recall)** | `0.5000` | **Ref Strict ($F_1$)** | `0.6667` |
| **Ref Conciseness** | `0.2500` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Technical documentation contents covering system description, design specifications, system architecture, data + training methodology, human oversight, risk-management measures, validation + testing procedures, and post-market monitoring system.

**Predicted References:** `Annex IV`  
**Latency:** `58.02 ms`

#### 🔸 Ground Truth Answer
> Annex IV requires: general description of the AI system, design specifications and algorithms, computational resources and training methods (Annex IV(2)(c)), risk management system file (Article 9), data governance and validation records (Article 10), human oversight measures (Article 14), cybersecurity safeguards (Article 15), logging mechanism documentation (Article 12), and post-market monitoring plan (Article 72).

**Expected Gold References:** `Article 11, Annex IV`


---

### Scenario: `hard_july7_10_penalties_tier_ceiling`
**Category:** *Borderline Prohibition & Exception*  
**Question:** What are the maximum administrative fine thresholds under Article 99 for non-compliance with the EU AI Act?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.2553` | **ROUGE-L ($F_1$)** | `0.3143` |
| **Semantic Sim (SBERT)** | `0.4552` | **Keyword Recall** | `0.3750` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `1.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Non-compliance with the prohibition of the AI practices referred to in Article 5 shall be subject to administrative fines of up to EUR 35 000 000 or, if the offender is an undertaking, up to 7 % of its total worldwide annual turnover for the preceding financial year, whichever is higher.

**Predicted References:** `Article 99`  
**Latency:** `107.28 ms`

#### 🔸 Ground Truth Answer
> Article 99 establishes three fine tiers: (1) up to EUR 35 000 000 or 7% of total worldwide annual turnover for violations of Article 5 prohibited practices; (2) up to EUR 15 000 000 or 3% for non-compliance with provider or deployer high-risk obligations; (3) up to EUR 7 500 000 or 1% for supplying incorrect, incomplete or misleading information to notified bodies or national competent authorities.

**Expected Gold References:** `Article 99.3, Article 99.4, Article 99.5, Article 99`


---

## Part 3: Cappelli et al. (Discover AI 2026) 5-Dimension Compliance Benchmark (20 Scenarios)
Direct replication of the 4 real-world high-risk case studies (Recruitment SaaS, Healthcare Diagnostics & Triage, Smart City Traffic, Retail Biometrics) across the 5 standard compliance prompt dimensions (`Risk Level`, `Regulatory Obligations`, `Legal Risks`, `Compliance Gaps`, `Technical Documentation`).

### Scenario: `cappelli_cs1_q1_risk_level`
**Domain:** Employment and Workers Management | **Dimension:** `Risk Level`  
**Question:** What is the risk level of my AI-powered personnel recruitment SaaS platform (which performs automatic CV pre-screening and candidate performance prediction) under the EU AI Act?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.1778` | **ROUGE-L ($F_1$)** | `0.1311` |
| **Semantic Sim (SBERT)** | `0.3466` | **Keyword Recall** | `0.6667` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `0.8000` |
| **Ref Conciseness** | `0.4444` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> AI used to recruit or select candidates, place targeted job advertisements, analyse and filter job applications, or evaluate candidates is high-risk under Annex III. Providers must meet the Chapter III Section 2 obligations (Articles 8–15) and deployers must inform affected workers under Article 26.

**Predicted References:** `Article 6, Article 26, Annex III`  
**Latency:** `223.06 ms`

#### 🔸 Ground Truth Answer
> Under the EU AI Act, the AI-powered recruitment platform qualifies as a high-risk AI system pursuant to Article 6(2) and Annex III, point 4(b), because it is used for recruitment and candidate selection, which significantly impacts access to employment.

**Expected Gold References:** `Article 6, Annex III.4.b`


---

### Scenario: `cappelli_cs1_q2_obligations`
**Domain:** Employment and Workers Management | **Dimension:** `Regulatory Obligations`  
**Question:** What specific regulatory obligations must my organization comply with based on the EU AI Act for this high-risk recruitment AI system?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.1204` | **ROUGE-L ($F_1$)** | `0.1656` |
| **Semantic Sim (SBERT)** | `0.4058` | **Keyword Recall** | `0.2000` |
| **Ref Loose (Recall)** | `0.0909` | **Ref Strict ($F_1$)** | `0.1429` |
| **Ref Conciseness** | `0.0744` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Adds two further presumptions of conformity beyond Articles 40-41: Article 42(1), high-risk AI systems trained and tested on data reflecting the specific geographical, behavioural, contextual, or functional setting in which they are intended to be used are presumed to comply with the relevant data-governance requirements of Article 10(4); Article 42(2), high-risk AI systems certified or for which a statement of conformity has been issued under a cybersecurity scheme under Regulation (EU) 2019/881 (the Cybersecurity Act) and whose references are published in the Official Journal are presumed to comply with the cybersecurity requirements of Article 15 to the extent the cybersecurity certificate or statement covers those requirements. Article 17 requires providers of high-risk AI systems to operate a quality management system covering regulatory-compliance strategy, design verification, examination + test procedures, post-market monitoring, and incident-reporting workflows.

**Predicted References:** `Article 42, Article 10, Article 17`  
**Latency:** `24.7 ms`

#### 🔸 Ground Truth Answer
> As a provider of a high-risk recruitment AI system, the organization must implement a continuous risk management system (Article 9), ensure data governance and bias mitigation (Article 10), draw up comprehensive technical documentation (Article 11 and Annex IV), maintain automated logging (Article 12), ensure transparency and instructions for use (Article 13), enable human oversight with override capabilities (Article 14), ensure accuracy, robustness, and cybersecurity (Article 15), conduct a conformity assessment with CE marking (Articles 43 and 48), and establish post-market monitoring (Article 72).

**Expected Gold References:** `Article 9, Article 10, Article 11, Article 12, Article 13, Article 14, Article 15, Article 43, Article 48, Article 72, Annex IV`


---

### Scenario: `cappelli_cs1_q3_legal_risks`
**Domain:** Employment and Workers Management | **Dimension:** `Legal Risks`  
**Question:** What are the potential legal risks associated with this AI recruitment tool, and what compliance measures must be implemented to mitigate these risks?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.0333` | **ROUGE-L ($F_1$)** | `0.0519` |
| **Semantic Sim (SBERT)** | `0.1865` | **Keyword Recall** | `0.0000` |
| **Ref Loose (Recall)** | `0.3333` | **Ref Strict ($F_1$)** | `0.3333` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> The risk management measures referred to in paragraph 2, point (d), shall be such that the relevant residual risk associated with each hazard, as well as the overall residual risk of the high-risk AI systems is judged to be acceptable.

**Predicted References:** `Article 9, Article 27, Article 10`  
**Latency:** `440.55 ms`

#### 🔸 Ground Truth Answer
> The primary legal risks include violation of fundamental rights regarding non-discrimination and equality (Article 21 of the EU Charter; Article 10 of the AI Act) through unrepresentative training datasets, unlawful automated decision-making lacking human oversight (Article 14 AI Act; Article 22 GDPR), and severe regulatory fines under Article 99. Mandatory mitigations include dataset bias audits, continuous human intervention protocols, and fundamental rights risk mapping.

**Expected Gold References:** `Article 10, Article 14, Article 99`


---

### Scenario: `cappelli_cs1_q4_compliance_gaps`
**Domain:** Employment and Workers Management | **Dimension:** `Compliance Gaps`  
**Question:** Which areas of the recruitment AI system are not yet compliant with applicable regulatory obligations when bias audits, formal risk management, and decision logging are missing?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.1034` | **ROUGE-L ($F_1$)** | `0.1282` |
| **Semantic Sim (SBERT)** | `0.3175` | **Keyword Recall** | `0.0909` |
| **Ref Loose (Recall)** | `0.6000` | **Ref Strict ($F_1$)** | `0.7500` |
| **Ref Conciseness** | `0.3600` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Requires automatic logs of events relevant to identifying risks, post-market monitoring, and substantial modifications, retained at minimum 6 months. Article 10 requires training, validation, and test datasets to be relevant, representative.

**Predicted References:** `Article 9, Article 12, Article 10`  
**Latency:** `14.5 ms`

#### 🔸 Ground Truth Answer
> The system presents critical compliance gaps under Article 9 (absence of a formal lifecycle risk management system), Article 10 (lack of bias detection audits and representative data governance), Article 12 (absence of automated logging and audit traceability), Article 14 (inadequate human oversight and override mechanisms), and Article 11 (missing technical file). These gaps require establishing documented risk procedures, statistical bias testing, tamper-proof logging, and human supervisor controls.

**Expected Gold References:** `Article 9, Article 10, Article 11, Article 12, Article 14`


---

### Scenario: `cappelli_cs1_q5_technical_documentation`
**Domain:** Employment and Workers Management | **Dimension:** `Technical Documentation`  
**Question:** What mandatory technical documentation is required to demonstrate compliance with the EU AI Act for this recruitment tool, and what specific documents must be prepared?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.1311` | **ROUGE-L ($F_1$)** | `0.1136` |
| **Semantic Sim (SBERT)** | `0.3268` | **Keyword Recall** | `0.2353` |
| **Ref Loose (Recall)** | `0.3333` | **Ref Strict ($F_1$)** | `0.4444` |
| **Ref Conciseness** | `0.2500` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Requires technical documentation drawn up before placement on the market, kept up to date, demonstrating conformity to the essential requirements, with content per Annex IV. Article 6 classifies an AI system as high-risk on two routes.

**Predicted References:** `Annex IV, Article 6, Article 11`  
**Latency:** `14.91 ms`

#### 🔸 Ground Truth Answer
> In compliance with Article 11 and Annex IV of the EU AI Act, the mandatory documentation includes: (1) the Technical File detailing system architecture and algorithms, (2) the Risk Management File under Article 9, (3) Data Governance and bias audit records under Article 10, (4) Human Oversight protocols under Article 14, (5) Automated Logging mechanism documentation under Article 12, (6) Post-Market Monitoring Plan under Article 72, (7) EU Declaration of Conformity under Article 47 and Annex V, and (8) CE Marking documentation under Article 48.

**Expected Gold References:** `Article 11, Article 47, Article 48, Article 72, Annex IV, Annex V`


---

### Scenario: `cappelli_cs2_q1_risk_level`
**Domain:** Healthcare and Medical Devices | **Dimension:** `Risk Level`  
**Question:** What is the risk level of an AI system used in hospitals for medical diagnosis, treatment recommendations, patient triage, and survival prediction under the EU AI Act?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.1231` | **ROUGE-L ($F_1$)** | `0.1538` |
| **Semantic Sim (SBERT)** | `0.2840` | **Keyword Recall** | `0.6000` |
| **Ref Loose (Recall)** | `1.0000` | **Ref Strict ($F_1$)** | `0.6667` |
| **Ref Conciseness** | `0.2500` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> AI used for emergency healthcare patient triage, or to dispatch or prioritise emergency first-response services, is high-risk under Annex III(5)(d) (Article 6(2)). Selecting or prioritising patients for a clinical trial is not itself a listed Annex III use case, so it is high-risk only where it determines access to or eligibility for essential healthcare services, or where it categorises natural persons by sensitive attributes (Annex III(1)(b)). Such biometric categorisation is prohibited under Article 5(1)(g) where it deduces race, political opinions, trade-union membership, religious or philosophical beliefs, sex life, or sexual orientation.

**Predicted References:** `Article 5, Article 6, Annex III.5.d, Annex I`  
**Latency:** `21.23 ms`

#### 🔸 Ground Truth Answer
> The medical diagnostic and triage AI system qualifies as a high-risk AI system under Article 6(1) in conjunction with Annex I (as a safety component of a medical device subject to third-party conformity assessment under MDR 2017/745) and Article 6(2) regarding essential healthcare triage.

**Expected Gold References:** `Article 6, Annex I`


---

### Scenario: `cappelli_cs2_q2_obligations`
**Domain:** Healthcare and Medical Devices | **Dimension:** `Regulatory Obligations`  
**Question:** What specific regulatory obligations must be met for this AI medical diagnostic and triage system under the EU AI Act?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.0441` | **ROUGE-L ($F_1$)** | `0.0706` |
| **Semantic Sim (SBERT)** | `0.2219` | **Keyword Recall** | `0.0000` |
| **Ref Loose (Recall)** | `0.4000` | **Ref Strict ($F_1$)** | `0.5000` |
| **Ref Conciseness** | `0.3600` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Requires a documented, iterative risk-management system across the AI system's lifecycle. Article 6 classifies an AI system as high-risk on two routes.

**Predicted References:** `Article 9, Article 6, Article 42, Article 10, Article 13, Article 15`  
**Latency:** `12.75 ms`

#### 🔸 Ground Truth Answer
> The provider must implement a risk management system integrated with ISO 14971 (Article 9), high-quality clinical data governance (Article 10), technical documentation aligned with MDR Annex II/III (Article 11, Annex IV), event logging (Article 12), clinical transparency and user manuals (Article 13), clinician human oversight to prevent automation bias (Article 14), accuracy and cybersecurity resilience (Article 15), joint notified body conformity assessment (Article 43(3)), and dual-track incident reporting (Article 73 for AI Act; MDR Article 87 for medical vigilance).

**Expected Gold References:** `Article 9, Article 10, Article 11, Article 12, Article 13, Article 14, Article 15, Article 43, Article 73, Annex IV`


---

### Scenario: `cappelli_cs2_q3_legal_risks`
**Domain:** Healthcare and Medical Devices | **Dimension:** `Legal Risks`  
**Question:** What are the legal risks associated with using AI survival modeling and lifestyle-based triage in hospital care?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.0154` | **ROUGE-L ($F_1$)** | `0.0471` |
| **Semantic Sim (SBERT)** | `0.1840` | **Keyword Recall** | `0.0000` |
| **Ref Loose (Recall)** | `0.0000` | **Ref Strict ($F_1$)** | `0.0000` |
| **Ref Conciseness** | `0.4444` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> This shall not include AI systems intended to be used for biometric verification the sole purpose of which is to confirm that a specific natural person is the person he or she claims to be; (b) AI systems intended to be used for biometric categorisation, according to sensitive or protected attributes or characteristics based on the inference of those attributes or characteristics; (c) AI systems intended to be used for emotion recognition.

**Predicted References:** `Article 9, Article 72, Article 59`  
**Latency:** `14.11 ms`

#### 🔸 Ground Truth Answer
> Key legal risks involve violations of human dignity and the right to healthcare non-discrimination (EU Charter Articles 1, 21, and 35; AI Act Article 10), automation bias where doctors over-rely on automated triage without critical review (Article 14), unlawful processing of special category health data (GDPR Article 9; AI Act Article 10(5)), and civil/product liability in case of diagnostic failure.

**Expected Gold References:** `Article 10, Article 14`


---

### Scenario: `cappelli_cs2_q4_compliance_gaps`
**Domain:** Healthcare and Medical Devices | **Dimension:** `Compliance Gaps`  
**Question:** What compliance gaps arise if the medical diagnostic AI lacks physician override controls and clinical dataset validation across diverse demographics?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.0233` | **ROUGE-L ($F_1$)** | `0.0377` |
| **Semantic Sim (SBERT)** | `0.1450` | **Keyword Recall** | `0.0000` |
| **Ref Loose (Recall)** | `0.5000` | **Ref Strict ($F_1$)** | `0.4000` |
| **Ref Conciseness** | `0.4444` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Requires a documented, iterative risk-management system across the AI system's lifecycle. Article 6 classifies an AI system as high-risk on two routes.

**Predicted References:** `Article 6, Article 9, Article 10, Article 14, Article 83, Article 30`  
**Latency:** `15.74 ms`

#### 🔸 Ground Truth Answer
> Major gaps exist under Article 10(2) due to unrepresentative demographic datasets causing diagnostic disparities, Article 14 due to missing doctor override and stop mechanisms, Article 11 due to incomplete clinical validation files in technical documentation, and Article 72 due to absent post-market clinical follow-up.

**Expected Gold References:** `Article 10, Article 11, Article 14, Article 72`


---

### Scenario: `cappelli_cs2_q5_technical_documentation`
**Domain:** Healthcare and Medical Devices | **Dimension:** `Technical Documentation`  
**Question:** What technical documentation must be prepared for an AI medical diagnostic system to satisfy EU AI Act Article 11 and Annex IV requirements?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.0847` | **ROUGE-L ($F_1$)** | `0.1111` |
| **Semantic Sim (SBERT)** | `0.2314` | **Keyword Recall** | `0.0833` |
| **Ref Loose (Recall)** | `0.4000` | **Ref Strict ($F_1$)** | `0.5714` |
| **Ref Conciseness** | `0.1600` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Requires technical documentation drawn up before placement on the market, kept up to date, demonstrating conformity to the essential requirements, with content per Annex IV.

**Predicted References:** `Article 11, Annex IV`  
**Latency:** `9.47 ms`

#### 🔸 Ground Truth Answer
> The technical documentation must contain the 8 mandatory Annex IV files: detailed system architecture and neural network specifications, ISO 14971-aligned risk management file (Article 9), clinical data governance and validation records (Article 10), clinician human oversight protocol (Article 14), audit logging mechanism (Article 12), post-market monitoring plan (Article 72), EU Declaration of Conformity (Article 47), and CE marking certification (Article 48).

**Expected Gold References:** `Article 11, Article 47, Article 48, Article 72, Annex IV`


---

### Scenario: `cappelli_cs3_q1_risk_level`
**Domain:** Critical Infrastructure | **Dimension:** `Risk Level`  
**Question:** What is the risk level of an AI-based intelligent traffic management system that dynamically controls city traffic lights based on live camera feeds and IoT sensors under the EU AI Act?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.1552` | **ROUGE-L ($F_1$)** | `0.1149` |
| **Semantic Sim (SBERT)** | `0.3283` | **Keyword Recall** | `0.5000` |
| **Ref Loose (Recall)** | `0.5000` | **Ref Strict ($F_1$)** | `0.2857` |
| **Ref Conciseness** | `0.1600` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> The EU AI Act applies a risk-based framework with four tiers plus a parallel regime for general-purpose AI models. Unacceptable-risk practices are prohibited outright under Article 5; high-risk systems are classified under Article 6 (as a safety component of an Annex I product, or as one of the Annex III use cases) and carry the Chapter III Section 2 obligations; limited-risk systems carry the Article 50 transparency duties; and minimal-risk systems have no mandatory obligations. General-purpose AI models are governed separately under Articles 51 to 56, with stricter duties for models posing systemic risk.

**Predicted References:** `Article 6, Article 50, Article 52, Article 53, Article 54`  
**Latency:** `31.0 ms`

#### 🔸 Ground Truth Answer
> The intelligent traffic management system is classified as a high-risk AI system pursuant to Article 6(2) and Annex III, point 2(a), as it is used as a safety component in the management and operation of road traffic and critical infrastructure.

**Expected Gold References:** `Article 6, Annex III.2.a`


---

### Scenario: `cappelli_cs3_q2_obligations`
**Domain:** Critical Infrastructure | **Dimension:** `Regulatory Obligations`  
**Question:** What regulatory obligations apply to a municipal operator deploying an AI-powered road traffic management system under the EU AI Act?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.0615` | **ROUGE-L ($F_1$)** | `0.0741` |
| **Semantic Sim (SBERT)** | `0.2308` | **Keyword Recall** | `0.1000` |
| **Ref Loose (Recall)** | `0.1250` | **Ref Strict ($F_1$)** | `0.1818` |
| **Ref Conciseness** | `0.1406` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Requires providers of high-risk AI systems to operate a quality management system covering regulatory-compliance strategy, design verification, examination + test procedures, post-market monitoring, and incident-reporting workflows.

**Predicted References:** `Article 9, Article 17, Article 79`  
**Latency:** `17.0 ms`

#### 🔸 Ground Truth Answer
> The provider and deployer must maintain a continuous risk management system against physical safety hazards (Article 9), ensure training data quality for camera vision models (Article 10), compile technical documentation (Article 11, Annex IV), maintain automated logs for at least 6 months (Articles 12 and 26(6)), ensure human traffic operators can override signals (Article 14), safeguard cybersecurity against remote tampering (Article 15), and comply with deployer operational oversight duties (Article 26).

**Expected Gold References:** `Article 9, Article 10, Article 11, Article 12, Article 14, Article 15, Article 26, Annex IV`


---

### Scenario: `cappelli_cs3_q3_legal_risks`
**Domain:** Critical Infrastructure | **Dimension:** `Legal Risks`  
**Question:** What legal and fundamental rights risks arise from using computer vision cameras and vehicle tracking in municipal traffic AI systems?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.0667` | **ROUGE-L ($F_1$)** | `0.1067` |
| **Semantic Sim (SBERT)** | `0.2791` | **Keyword Recall** | `0.1429` |
| **Ref Loose (Recall)** | `0.3333` | **Ref Strict ($F_1$)** | `0.3333` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Article 79 procedure for AI systems presenting a risk: market-surveillance authorities that have sufficient reasons to consider that an AI system presents a risk to health, safety or fundamental rights (per the 'product presenting a risk' definition in Article 3, point 19, of Regulation (EU) 2019/1020, extended by Article 79(1) to fundamental-rights risks) carry out an evaluation of the system.

**Predicted References:** `Article 27, Article 79, Article 9`  
**Latency:** `16.19 ms`

#### 🔸 Ground Truth Answer
> Primary legal risks include mass surveillance and privacy infringements under Article 8 of the EU Charter and GDPR if vehicle license plates or facial images are captured without effective anonymization, critical safety failures causing physical traffic accidents (Article 9), and civil liability for infrastructure disruption.

**Expected Gold References:** `Article 9, Article 10, Article 15`


---

### Scenario: `cappelli_cs3_q4_compliance_gaps`
**Domain:** Critical Infrastructure | **Dimension:** `Compliance Gaps`  
**Question:** What compliance gaps exist if a smart traffic AI system lacks fail-safe fallback modes and cyberattack resilience testing?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.0909` | **ROUGE-L ($F_1$)** | `0.1481` |
| **Semantic Sim (SBERT)** | `0.2356` | **Keyword Recall** | `0.1667` |
| **Ref Loose (Recall)** | `0.5000` | **Ref Strict ($F_1$)** | `0.5714` |
| **Ref Conciseness** | `0.5625` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Requires a documented, iterative risk-management system across the AI system's lifecycle. Article 15 requires appropriate levels of accuracy, robustness.

**Predicted References:** `Article 9, Article 15, Article 83`  
**Latency:** `15.76 ms`

#### 🔸 Ground Truth Answer
> The system suffers from critical gaps under Article 15 (failure to demonstrate robustness against sensor faults and cyber-attacks), Article 9 (incomplete risk evaluation for emergency vehicle routing failures), Article 14 (lack of manual override protocols for traffic operators), and Article 12 (insufficient event logging during traffic anomalies).

**Expected Gold References:** `Article 9, Article 12, Article 14, Article 15`


---

### Scenario: `cappelli_cs3_q5_technical_documentation`
**Domain:** Critical Infrastructure | **Dimension:** `Technical Documentation`  
**Question:** What technical documentation must be established for an intelligent traffic management AI system under Article 11 and Annex IV of the EU AI Act?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.0847` | **ROUGE-L ($F_1$)** | `0.1111` |
| **Semantic Sim (SBERT)** | `0.2234` | **Keyword Recall** | `0.1818` |
| **Ref Loose (Recall)** | `0.3333` | **Ref Strict ($F_1$)** | `0.5000` |
| **Ref Conciseness** | `0.1111` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Requires technical documentation drawn up before placement on the market, kept up to date, demonstrating conformity to the essential requirements, with content per Annex IV.

**Predicted References:** `Article 11, Annex IV`  
**Latency:** `9.99 ms`

#### 🔸 Ground Truth Answer
> Mandatory technical documentation under Annex IV includes: system architecture and IoT sensor specifications, risk management file covering infrastructure safety (Article 9), validation datasets and sensor error rates (Article 10), human operator intervention protocol (Article 14), cybersecurity and redundancy test logs (Article 15), 6-month minimum logging mechanism (Article 12), EU Declaration of Conformity (Article 47), and CE marking (Article 48).

**Expected Gold References:** `Article 11, Article 12, Article 15, Article 47, Article 48, Annex IV`


---

### Scenario: `cappelli_cs4_q1_risk_level`
**Domain:** Biometrics and Retail | **Dimension:** `Risk Level`  
**Question:** What is the risk level of an in-store AI system using facial recognition for VIP matching, theft alerts against flagged images, and behavioral gaze analysis under the EU AI Act?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.1690` | **ROUGE-L ($F_1$)** | `0.2286` |
| **Semantic Sim (SBERT)** | `0.3957` | **Keyword Recall** | `0.8333` |
| **Ref Loose (Recall)** | `0.5000` | **Ref Strict ($F_1$)** | `0.4444` |
| **Ref Conciseness** | `0.6400` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> The EU AI Act applies a risk-based framework with four tiers plus a parallel regime for general-purpose AI models. Unacceptable-risk practices are prohibited outright under Article 5; high-risk systems are classified under Article 6 (as a safety component of an Annex I product, or as one of the Annex III use cases) and carry the Chapter III Section 2 obligations; limited-risk systems carry the Article 50 transparency duties; and minimal-risk systems have no mandatory obligations. General-purpose AI models are governed separately under Articles 51 to 56, with stricter duties for models posing systemic risk.

**Predicted References:** `Article 6, Article 50, Article 52, Article 53, Article 54`  
**Latency:** `21.37 ms`

#### 🔸 Ground Truth Answer
> The system spans multiple regulatory tiers: real-time remote biometric identification in publicly accessible spaces is prohibited under Article 5(1)(h) when conducted by law enforcement; biometric categorization for retail profiling is classified as high-risk under Article 6(2) and Annex III, point 1; emotion or interest recognition requires mandatory transparency disclosure to consumers under Article 50(3).

**Expected Gold References:** `Article 5.1.h, Article 6, Article 50.3, Annex III.1`


---

### Scenario: `cappelli_cs4_q2_obligations`
**Domain:** Biometrics and Retail | **Dimension:** `Regulatory Obligations`  
**Question:** What obligations must a retail store fulfill when deploying AI facial recognition and behavioral analytics?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.1818` | **ROUGE-L ($F_1$)** | `0.1607` |
| **Semantic Sim (SBERT)** | `0.4791` | **Keyword Recall** | `0.4000` |
| **Ref Loose (Recall)** | `0.2000` | **Ref Strict ($F_1$)** | `0.2500` |
| **Ref Conciseness** | `0.3600` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Where the high-risk system is an Annex-III biometric-identification, emotion-recognition, or biometric-categorisation system, Article 26(11) preserves the Article 50 transparency-to-end-user obligations on top of the Article 13 transparency-to-deployer chain. Article 12 requires automatic logs of events relevant to identifying risks, post-market monitoring. Under Article 27, in addition to Article 26 baseline duties, deployers of certain Annex III high-risk AI systems must perform a Fundamental Rights Impact Assessment (FRIA) covering affected persons and specific fundamental rights risks.

**Predicted References:** `Article 12, Article 13, Article 27`  
**Latency:** `12.02 ms`

#### 🔸 Ground Truth Answer
> The deployer must verify the system does not fall under Article 5 prohibitions, conduct a Fundamental Rights Impact Assessment prior to use (Article 27), clearly inform exposed individuals of biometric and emotion analysis (Article 50(3)), ensure explicit GDPR consent for biometric processing (GDPR Article 9; AI Act Article 10(5)), maintain human oversight on theft alerts (Article 14), and retain system logs for at least 6 months (Article 26(6)).

**Expected Gold References:** `Article 5, Article 14, Article 26.6, Article 27, Article 50.3`


---

### Scenario: `cappelli_cs4_q3_legal_risks`
**Domain:** Biometrics and Retail | **Dimension:** `Legal Risks`  
**Question:** What legal risks arise from using retail facial recognition for theft alerting and dynamic behavior-based pricing?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.0476` | **ROUGE-L ($F_1$)** | `0.1333` |
| **Semantic Sim (SBERT)** | `0.3372` | **Keyword Recall** | `0.2222` |
| **Ref Loose (Recall)** | `0.0000` | **Ref Strict ($F_1$)** | `0.0000` |
| **Ref Conciseness** | `1.0000` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Real-time remote biometric identification by law enforcement is prohibited under Article 5 save for narrow, exhaustively-listed law-enforcement exceptions that each require prior judicial or administrative authorisation; under Article 5(5) Member States may enable those exceptions in national law and may set stricter national rules. Under Article 50, Transparency obligations split by actor: providers must ensure AI systems interacting. Article 68 establishes a Scientific Panel of independent experts to support enforcement of Chapter V.

**Predicted References:** `Article 50.3, Article 68, Article 72`  
**Latency:** `17.31 ms`

#### 🔸 Ground Truth Answer
> Severe legal risks include: (1) unlawful biometric categorization or prohibited mass surveillance (Article 5(1)(h) and Article 5(1)(c)), (2) racial, gender, or demographic bias in facial matching algorithms violating Article 21 of the EU Charter, (3) unlawful processing of biometric data without valid explicit consent under GDPR Article 9, and (4) maximum regulatory penalties of up to 35 million EUR or 7% of global annual turnover under Article 99(3).

**Expected Gold References:** `Article 5, Article 10, Article 99.3`


---

### Scenario: `cappelli_cs4_q4_compliance_gaps`
**Domain:** Biometrics and Retail | **Dimension:** `Compliance Gaps`  
**Question:** What compliance gaps exist if retail facial recognition is deployed without signage, without a Fundamental Rights Impact Assessment, and automated theft alerts trigger security interventions without human confirmation?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.1034` | **ROUGE-L ($F_1$)** | `0.1714` |
| **Semantic Sim (SBERT)** | `0.2724` | **Keyword Recall** | `0.2222` |
| **Ref Loose (Recall)** | `0.2500` | **Ref Strict ($F_1$)** | `0.3333` |
| **Ref Conciseness** | `0.2500` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Deployers of certain high-risk AI systems (Annex III + public-sector deployers) must perform a Fundamental Rights Impact Assessment before first use, covering deployment process, affected persons, specific risks, human-oversight measures, and complaints workflows.

**Predicted References:** `Annex III, Article 27`  
**Latency:** `11.4 ms`

#### 🔸 Ground Truth Answer
> Critical deficiencies include violation of Article 50(3) (failure to provide conspicuous transparency notices to shoppers), Article 27 (failure to conduct and register a Fundamental Rights Impact Assessment before deployment), Article 14 (lack of meaningful human oversight before security actions), and Article 10 (unverified accuracy and demographic false-positive rates on facial recognition).

**Expected Gold References:** `Article 10, Article 14, Article 27, Article 50.3`


---

### Scenario: `cappelli_cs4_q5_technical_documentation`
**Domain:** Biometrics and Retail | **Dimension:** `Technical Documentation`  
**Question:** What technical documentation is required for high-risk biometric identification and retail analytics systems under the EU AI Act?

| Metric | Score | Metric | Score |
| :--- | :--- | :--- | :--- |
| **Jaccard (Loose)** | `0.0543` | **ROUGE-L ($F_1$)** | `0.1260` |
| **Semantic Sim (SBERT)** | `0.3396` | **Keyword Recall** | `0.0000` |
| **Ref Loose (Recall)** | `0.0000` | **Ref Strict ($F_1$)** | `0.0000` |
| **Ref Conciseness** | `0.0204` | **Regulatory Tone** | `1.0000` |

#### 🔹 Live Predicted Answer
> Under Article 5.1.h, real-time remote biometric identification in publicly accessible spaces by law-enforcement authorities is prohibited; narrow exceptions require prior judicial or independent-administrative authorization, an Article 27 fundamental-rights impact assessment, and Article 49 EU-database registration. Real-time remote biometric identification by law enforcement is prohibited under Article 5 save for narrow, exhaustively-listed law-enforcement exceptions that each require prior judicial or administrative authorisation; under Article 5(5) Member States may enable those exceptions in national law and may set stricter national rules.

**Predicted References:** `Article 5.1.h`  
**Latency:** `21.51 ms`

#### 🔸 Ground Truth Answer
> The technical documentation under Annex IV must include: detailed facial feature extraction algorithms and CNN models, false match rate (FMR) and false non-match rate (FNMR) accuracy benchmarks across demographic cohorts (Article 15), data governance records (Article 10), human oversight and override protocol for security staff (Article 14), 6-month log retention mechanism (Article 12), Fundamental Rights Impact Assessment report (Article 27), EU Declaration of Conformity (Article 47), and CE marking documentation (Article 48).

**Expected Gold References:** `Article 11, Article 14, Article 15, Article 27, Article 47, Article 48, Annex IV`


---

