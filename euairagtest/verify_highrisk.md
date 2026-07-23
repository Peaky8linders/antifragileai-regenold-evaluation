# Citation Verification Report — High-Risk Strata
**Files checked:** `stratum_highrisk_classification.json`, `stratum_highrisk_requirements.json`  
**Verifier stance:** adversarial — every citation treated as potentially wrong until confirmed  
**Primary sources:** https://artificialintelligenceact.eu/ (article and annex pages), EUR-Lex CELEX 32024R1689  
**Verification date:** 2026-07-22

---

## CORRECTIONS NEEDED

| item_id | provision_id (as-is) | issue | correct value | source URL |
|---|---|---|---|---|
| easy_hrclass_006 | `art_3__para_41` (citation text: "Art. 3(41)") | The gold_answer **prose** says "Art. 3(40) defines biometric identification" but the provision_id and citation string both say Art. 3(41). Art. 3(40) = "biometric categorisation system"; Art. 3(41) = "remote biometric identification system". For this item (remote biometric identification systems), Art. 3(41) is the correct definition. The prose is wrong but the provision_id is correct. No change needed to provision_id. **Flag the gold_answer text** — it contains a factual error in the prose: change "Art. 3(40)" to "Art. 3(41)" in the gold_answer string. | No change to provision_id `art_3__para_41` — it is correct. Fix prose only. | https://artificialintelligenceact.eu/article/3/ |
| hard_hrreq_002 | `art_26__para_5` | Art. 26(5) = monitoring and reporting serious incidents obligation (correct). However, the gold_answer describes a separate obligation — "maintain automatically generated logs for at least 6 months" — which is **Art. 26(6)**, not Art. 26(5). Art. 26(6) is entirely absent from gold_citations. This is an under-citation: the 6-month log-retention obligation is unanchored. | Add missing citation `art_26__para_6` (role: supporting) | https://artificialintelligenceact.eu/article/26/ |

---

## CONFIRMED

Distinct provision_ids verified correct against primary text (with the term/topic each denotes):

- **`art_6__para_1`** — Art. 6(1): the safety-component + Annex I product + third-party conformity assessment classification route (Art. 6(1)(a) and (b)). Used in hard_hrclass_001 and hard_hrclass_007.
- **`art_6__para_2`** — Art. 6(2): operative rule that AI systems listed in Annex III are high-risk. Appears across nearly all classification items.
- **`art_6__para_3`** — Art. 6(3): the derogation provision allowing Annex III systems to escape high-risk classification when conditions (a)–(d) are met, subject to the profiling override. Confirmed to have exactly four sub-points (a)–(d).
- **`art_6__para_3__point_a`** — Art. 6(3)(a): "the AI system is intended to perform a narrow procedural task". Cited in hard_hrclass_003 for CV data extraction. Correct.
- **`art_6__para_3__point_c`** — Art. 6(3)(c): "the AI system is intended to detect decision-making patterns or deviations from prior decision-making patterns and is not meant to replace or influence the previously completed human assessment, without proper human review". Cited in hard_hrclass_002 for judicial pattern detection. Correct.
- **`art_6__para_3__point_d`** — Art. 6(3)(d): "the AI system is intended to perform a preparatory task to an assessment relevant for the purposes of the use cases listed in Annex III". Cited in hard_hrclass_003 for CV data extraction as preparatory task. Correct.
- **`annex_III__point_1__point_a`** — Annex III point 1(a): remote biometric identification systems (with exception for biometric verification). Confirmed present and correctly used.
- **`annex_III__point_3__point_a`** — Annex III point 3(a): AI systems determining access/admission to educational and vocational training institutions. Point 3 = education and vocational training. Correct for university admissions (easy_hrclass_005).
- **`annex_III__point_4__point_a`** — Annex III point 4(a): AI systems for recruitment — job advertising, application screening/filtering, candidate evaluation. Point 4 = employment, workers management. Correct for CV screening (easy_hrclass_001) and CV data extraction (hard_hrclass_003).
- **`annex_III__point_5__point_a`** — Annex III point 5(a): AI systems for evaluating eligibility for public assistance benefits and services (including healthcare, housing, education/professional training). Point 5 = access to essential private and public services. Correct for social housing eligibility (easy_hrclass_004) and healthcare benefits (hard_hrclass_007).
- **`annex_III__point_5__point_b`** — Annex III point 5(b): AI systems assessing creditworthiness or establishing credit scores (excluding fraud detection). Point 5(b) correctly mapped to financial services / credit scoring (easy_hrclass_002).
- **`annex_III__point_5__point_c`** — Annex III point 5(c): AI systems for risk assessment and pricing in life and health insurance. Point 5(c) correctly mapped to insurance risk/premium assessment (easy_hrclass_007).
- **`annex_III__point_7__point_b`** — Annex III point 7(b): AI systems assessing risk (security, irregular migration, or health risk) posed by persons at borders. Point 7 = migration, asylum, border control. Correct for border security risk assessment (easy_hrclass_003).
- **`annex_III__point_8__point_a`** — Annex III point 8(a): AI systems assisting judicial authorities in researching and applying law to facts. Point 8 = administration of justice and democratic processes. Correct for judicial pattern anomaly detection (hard_hrclass_002).
- **`annex_III__point_8__point_b`** — Annex III point 8(b): AI systems intended to influence election/referendum outcomes or voting behaviour (excluding back-office administrative campaign tools). Correct for political messaging tool (hard_hrclass_005).
- **`annex_I`** — Annex I: Union harmonisation legislation (Section A = New Legislative Framework; Section B = other). Annex I Section A point 11 = Regulation (EU) 2017/745 (MDR medical devices). Used in hard_hrclass_001 and hard_hrclass_007 for the Art. 6(1) safety-component route. Confirmed correct.
- **`art_3__para_14`** — Art. 3(14): definition of "safety component" — a component fulfilling a safety function or whose failure endangers health/safety of persons or property. Confirmed correct (earlier fetch erroneously suggested Art. 3(14) = "instructions for use"; that is actually Art. 3(15) — the correct definition is safety component at (14)).
- **`art_3__para_41`** — Art. 3(41): definition of "remote biometric identification system" — an AI system identifying natural persons without active involvement, typically at a distance. Cited in easy_hrclass_006. Correct. (Art. 3(40) = biometric categorisation system, not biometric identification — the gold_answer prose conflates these but the provision_id is correct.)
- **`art_3__para_52`** — Art. 3(52): definition of "profiling" — cross-referenced to GDPR Art. 4(4). Cited in hard_hrclass_002. Correct.
- **`recital_47`** — Recital (47): addresses AI safety risks in products and health sector — AI as safety components, autonomous robots, medical diagnostic systems. Used for interpretive context in hard_hrclass_001 (safety-component classification) and hard_hrclass_007 (healthcare AI). Content confirmed on-topic.
- **`recital_51`** — Recital (51): clarifies that classifying an AI system as high-risk under the AI Act does NOT automatically mean the product is high-risk under MDR or other harmonisation legislation. Used in hard_hrclass_001 for the MDR interaction. Content confirmed exactly correct.
- **`recital_53`** — Recital (53): addresses conditions excluding Annex III systems from high-risk classification under Art. 6(3). Explicitly gives examples including "transforms unstructured data into structured data", a teacher grading anomaly detection example, and confirms the profiling override. Cited in hard_hrclass_002 and hard_hrclass_003. Content confirmed correct and on-topic.
- **`art_9`** / **`art_9__para_1`** / **`art_9__para_2`** — Art. 9: risk management system obligation. Art. 9(1) imposes the obligation; Art. 9(2) defines the four-step iterative process. All correct.
- **`art_10`** / **`art_10__para_1`** / **`art_10__para_2`** / **`art_10__para_3`** / **`art_10__para_5`** — Art. 10: data and data governance. Art. 10(1) establishes scope; Art. 10(2) governance practices; Art. 10(3) qualitative data quality standard (no numeric minimum dataset size); Art. 10(5) narrow exception for processing special categories of personal data for bias detection. All confirmed.
- **`art_11`** / **`art_11__para_1`** — Art. 11: technical documentation. Art. 11(1) requires documentation before market placement, with content specified in Annex IV. Correct.
- **`art_12`** / **`art_12__para_1`** / **`art_12__para_2`** — Art. 12: record-keeping / logging. Art. 12(1) imposes the logging obligation; Art. 12(2) specifies what events must be captured. Correct.
- **`art_13`** / **`art_13__para_1`** / **`art_13__para_2`** / **`art_13__para_3`** — Art. 13: transparency and provision of information to deployers. Art. 13(1) transparency obligation; Art. 13(2) instructions for use mandate; Art. 13(3) content of instructions. Correct.
- **`art_14`** / **`art_14__para_1`** / **`art_14__para_4`** / **`art_14__para_5`** — Art. 14: human oversight. Art. 14(4) = oversight capabilities including automation-bias awareness; Art. 14(5) = two-person independent verification, scoped ONLY to Annex III point 1(a) (remote biometric identification), not a general requirement. All confirmed correct.
- **`art_15`** / **`art_15__para_1`** / **`art_15__para_3`** / **`art_15__para_5`** — Art. 15: accuracy, robustness, cybersecurity. Art. 15(1) general obligation; Art. 15(3) = accuracy levels must be declared in instructions for use (transparency to deployers, NOT certification to authority); Art. 15(5) = cybersecurity/resilience against adversarial manipulation (data poisoning, model poisoning, adversarial examples) — NOT an accuracy certification requirement. Hallucination trap integrity confirmed.
- **`art_16`** — Art. 16: provider obligations enumeration (sub-points (a)–(l)), cross-referencing Arts 9–15, 17, 18, 19, 20, 43, 47, 48, 49. Correct.
- **`art_17`** — Art. 17: quality management system obligation. Confirmed (referenced by Art. 16(c)).
- **`art_18`** — Art. 18: documentation maintenance. Confirmed (referenced by Art. 16(d)).
- **`art_19`** — Art. 19: log retention by provider when under provider's control. Confirmed (referenced by Art. 16(e)).
- **`art_20`** — Art. 20: corrective actions and information to authorities. Confirmed (referenced by Art. 16(j)).
- **`art_26`** / **`art_26__para_1`** / **`art_26__para_2`** / **`art_26__para_5`** — Art. 26: deployer obligations. Art. 26(1) = use according to instructions; Art. 26(2) = assign human oversight to competent persons; Art. 26(5) = monitoring operations and reporting serious incidents. All confirmed. Note: Art. 26(6) (6-month log retention) is the missing citation — see CORRECTIONS NEEDED.
- **`art_27`** / **`art_27__para_1`** — Art. 27: fundamental rights impact assessment (FRIA). Art. 27(1) requires FRIA from deployers that are public bodies OR private entities providing public services. The dataset's gold_answer correctly states it applies "specifically because the deployer is a public entity" — technically the scope is slightly broader (also private entities providing public services) but the hospital scenario is correctly classified. Confirmed.
- **`art_43`** — Art. 43: conformity assessment. For Annex III points 2–8: internal control only, no notified body (Art. 43(2) / Annex VI). For point 1 systems: notified body may be required. Confirmed correct.
- **`art_47`** — Art. 47: EU declaration of conformity. Confirmed (referenced by Art. 16(g)).
- **`art_48`** — Art. 48: CE marking. Confirmed (referenced by Art. 16(h)).
- **`art_49__para_1`** — Art. 49(1): pre-market registration of confirmed high-risk systems in EU database. Art. 49(2) = registration of self-assessed non-high-risk systems. Confirmed that (1) applies to the provider obligation context used in hard_hrreq_001.
- **`art_8`** — Art. 8: general requirement for high-risk AI systems to comply with Section 2 requirements (Arts 9–15). Confirmed.

---

## TRAP INTEGRITY CHECKS

- **hard_hrclass_007** (`hallucination_trap=true`): trap_note asserts there is no "Annex III point 9" and no blanket healthcare classification. **Confirmed correct** — Annex III has exactly 8 points; no point 9 exists.
- **hard_hrreq_004** (`hallucination_trap=true`): trap_note asserts Art. 10 does NOT mandate minimum dataset size or split ratio. **Confirmed correct** — Art. 10(3) uses purely qualitative language.
- **hard_hrreq_007** (`hallucination_trap=true`): trap_note asserts Art. 15(5) is cybersecurity/adversarial resilience, not accuracy certification. **Confirmed correct** — Art. 15(5) explicitly covers data poisoning, model poisoning, adversarial examples, confidentiality attacks, model flaws. Art. 15(3) (accuracy declaration in instructions) is correctly identified as the transparency obligation directed at deployers.

---

## STRUCTURAL CHECK — Annex III Point Mapping

The following table confirms the subject-matter of each Annex III point as used in the dataset:

| Point | Subject | Dataset use | Correct? |
|---|---|---|---|
| 1 | Biometrics (sub-points a/b/c) | easy_hrclass_006 (1(a) remote biometric ID) | Yes |
| 2 | Critical infrastructure | Not cited in these strata | N/A |
| 3 | Education and vocational training | easy_hrclass_005 (3(a) admissions) | Yes |
| 4 | Employment, workers management | easy_hrclass_001, hard_hrclass_003 (4(a) recruitment) | Yes |
| 5 | Access to essential private and public services | easy_hrclass_002 (5(b)), easy_hrclass_004 (5(a)), easy_hrclass_007 (5(c)), hard_hrreq_001/002 (general point 5) | Yes |
| 6 | Law enforcement | Not cited in these strata | N/A |
| 7 | Migration, asylum, border control | easy_hrclass_003 (7(b)) | Yes |
| 8 | Administration of justice and democratic processes | hard_hrclass_002 (8(a)), hard_hrclass_005 (8(b)) | Yes |
| 9 | Does not exist | hard_hrclass_007 trap confirms this | Trap integrity confirmed |

---

## SUMMARY

- **Total distinct provision_ids across both files:** 49
- **CONFIRMED correct:** 47
- **CORRECTIONS NEEDED:** 2 (one prose-only error in easy_hrclass_006 gold_answer text; one missing citation art_26__para_6 in hard_hrreq_002)
- **No provision_id points to a non-existent provision**
- **No provision_id is mapped to the wrong article duty (numbering correct throughout)**
- **All hallucination trap assertions verified as correct**
