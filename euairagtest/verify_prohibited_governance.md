# Citation Verification Report: stratum_prohibited + stratum_governance

**Verifier:** Adversarial citation check against Regulation (EU) 2024/1689 (CELEX 32024R1689)  
**Primary sources:** https://artificialintelligenceact.eu/ (article, recital, and annex pages)  
**Date:** 2026-07-22  
**Scope:** All distinct `provision_id` values across `stratum_prohibited.json` and `stratum_governance.json`  
**Total distinct provisions checked:** 40  

---

## CORRECTIONS NEEDED

**Provision IDs — none.** Every distinct provision_id across both files was verified against the primary text. No existence errors, numbering errors, or relevance mismatches were found.

**Prose (non-citation) — one.** `hard_gov_005` is a negative control (empty `gold_citations`), but its `gold_answer` and `annotator_notes` prose mis-numbered the Fundamental Rights Impact Assessment as "Art. 26". The FRIA is **Art. 27**; Art. 26 is the general deployer-obligations article. Corrected in both prose fields. No provision_id is affected (the item cites nothing). This aligns the note with the correct Art. 27 usage in `verify_highrisk.md` and `stratum_highrisk_requirements.json`.

| item_id | field | issue | correct value | source URL |
|---|---|---|---|---|
| hard_gov_005 | gold_answer + annotator_notes (prose) | FRIA labelled "Art. 26" | Art. 27 = FRIA; Art. 26 = deployer obligations | https://artificialintelligenceact.eu/article/27/ |

### Verification notes on potential issues investigated and ruled out

**1. Art. 3 definition index numbers (highest-risk area)**  
All definition paragraph numbers were confirmed against the live Article 3 page:
- Art. 3(39) = "emotion recognition system" — CONFIRMED correct
- Art. 3(40) = "biometric categorisation system" — CONFIRMED correct
- Art. 3(41) = "remote biometric identification system" (not real-time) — cited nowhere in the datasets; consistent with the benchmark only citing 3(42) for the real-time variant
- Art. 3(42) = "real-time remote biometric identification system" — CONFIRMED correct
- Art. 3(44) = "publicly accessible space" — CONFIRMED correct
- Art. 3(1) = "AI system", Art. 3(3) = "provider", Art. 3(4) = "deployer" — all CONFIRMED correct

**2. Art. 5(1) terminal point**  
Confirmed Art. 5(1) contains exactly eight sub-points (a) through (h). There is no Art. 5(1)(i). The hallucination trap in `hard_prohibited_007` is valid.

**3. Art. 5(1)(h) sub-point assignments**  
- (i) = targeted search for trafficking victims and missing persons — CONFIRMED (used in hard_prohibited_002)
- (ii) = prevention of specific, substantial and imminent threat to life or of a terrorist attack — CONFIRMED (used in hard_prohibited_001)
- (iii) = localisation/identification of suspects for Annex II offences punishable by ≥4 years — CONFIRMED (used in hard_prohibited_003)

**4. Recital topic assignments**  
- Recital 29: covers both subliminal techniques and vulnerability exploitation — CONFIRMED (used for Art. 5(1)(a) and 5(1)(b) items)
- Recital 30: biometric categorisation for inferring sensitive attributes — CONFIRMED (used for Art. 5(1)(g) items)
- Recital 31: social scoring — CONFIRMED (used for Art. 5(1)(c) item)
- Recital 33: law enforcement RBI exceptions including trafficking, imminent threats, terrorist attacks, serious crimes and 4-year threshold — CONFIRMED (used for hard_prohibited_001, 002, 003)
- Recital 35: prior authorisation requirement for RBI; urgency exception and post-refusal obligations — CONFIRMED (used for hard_prohibited_001)
- Recital 42: prohibition on predictive criminal profiling based solely on personal characteristics; carve-out for objective factual assessments — CONFIRMED (used for easy_prohibited_005, hard_prohibited_007)
- Recital 44: emotion recognition prohibition in workplace and educational settings; power-imbalance rationale; medical/therapeutic exception — CONFIRMED (used for easy_prohibited_006, hard_prohibited_004, hard_prohibited_006)

**5. Penalty tiers (Art. 99)**  
- Art. 99(3): EUR 35,000,000 or 7% of worldwide annual turnover, whichever higher — for Art. 5 violations — CONFIRMED
- Art. 99(4): EUR 15,000,000 or 3% — for other operator/notified-body obligation violations — CONFIRMED
- Art. 99(5): EUR 7,500,000 or 1% — for inaccurate/incomplete/misleading information to authorities — CONFIRMED

**6. Art. 113 application timeline**  
- 2 Feb 2025: Chapters I and II (including Art. 5 prohibitions) — CONFIRMED
- 2 Aug 2025: Chapter V (GPAI), Chapter VII (governance), Chapter XII (penalties) — CONFIRMED
- 2 Aug 2026: general application date — CONFIRMED
- 2 Aug 2027: Art. 6(1) and corresponding obligations (Annex I safety-component high-risk systems) — CONFIRMED

**7. Art. 2 scope exclusions**  
- Art. 2(3): military, defence, and national-security exclusion — CONFIRMED
- Art. 2(6): AI systems developed solely for scientific R&D — CONFIRMED
- Art. 2(8): pre-market research, testing, and development activity — CONFIRMED
- Art. 2(10): deployers who are natural persons using AI in purely personal non-professional activities — CONFIRMED

**8. Annex II**  
Title confirmed as "List of Criminal Offences Referred to in Article 5(1), First Subparagraph, Point (h)(iii)". The gold_answer for hard_prohibited_003 states the list "is based on the 32 criminal offences in Council Framework Decision 2002/584/JHA" — this is consistent with Recital 33, which uses the exact same language. Annex II itself consolidates these into 16 grouped categories; the "32" figure refers to the source framework, not the annex entry count. This is not a citation error; the cited provision_ids (annex_II and recital_33) are correct and accurately describe the annex's function and legislative lineage.

**9. Hallucination traps — validity confirmed**  
- `hard_prohibited_007` trap: Art. 5(1)(i) does not exist — CONFIRMED VALID
- `hard_gov_005` trap: No DPIA requirement exists in the EU AI Act; Art. 27 covers a fundamental rights impact assessment (not a DPIA) for certain public-body deployers — CONFIRMED VALID
- `hard_gov_007` trap: EUR 20m/4% is the GDPR Art. 83(5) figure, not the AI Act figure; AI Act Art. 99(4) = EUR 15m/3% — CONFIRMED VALID

**10. Art. 6(2) citation in hard_gov_001**  
Used as a supporting citation to establish Annex III classification. Art. 6(2) text: "In addition to the high-risk AI systems referred to in paragraph 1, AI systems referred to in Annex III shall be considered to be high-risk." CONFIRMED correct. The gold_answer correctly states that Annex III Chapter III obligations apply from 2 Aug 2026 (general date), and correctly distinguishes this from the Art. 6(1)/Annex I delayed date of 2 Aug 2027.

---

## CONFIRMED

All 40 distinct provision_ids verified as correct:

- **art_5__para_1__point_a** — Art. 5(1)(a): prohibition on AI systems deploying subliminal techniques beyond the threshold of consciousness to materially distort behaviour
- **art_5__para_1__point_b** — Art. 5(1)(b): prohibition on exploiting vulnerabilities based on age, disability, or socioeconomic situation
- **art_5__para_1__point_c** — Art. 5(1)(c): prohibition on social scoring systems causing detrimental treatment unrelated to original data context
- **art_5__para_1__point_d** — Art. 5(1)(d): prohibition on risk assessments predicting criminal offences based solely on profiling or personality/characteristic traits
- **art_5__para_1__point_e** — Art. 5(1)(e): prohibition on AI systems creating or expanding facial-recognition databases through untargeted scraping
- **art_5__para_1__point_f** — Art. 5(1)(f): prohibition on emotion inference systems in workplaces and educational institutions (medical/safety carve-out applies)
- **art_5__para_1__point_g** — Art. 5(1)(g): prohibition on biometric categorisation systems inferring race, political opinions, trade-union membership, religious beliefs, sex life, or sexual orientation
- **art_5__para_1__point_h** — Art. 5(1)(h): prohibition on real-time remote biometric identification in publicly accessible spaces for law enforcement (with narrowly defined exceptions)
- **art_5__para_1__point_h__sub_i** — Art. 5(1)(h)(i): exception for targeted search for trafficking victims, sexual exploitation victims, and missing persons
- **art_5__para_1__point_h__sub_ii** — Art. 5(1)(h)(ii): exception for prevention of specific, substantial and imminent threat to life or safety or genuine terrorist attack
- **art_5__para_1__point_h__sub_iii** — Art. 5(1)(h)(iii): exception for localising/identifying suspects of Annex II offences punishable by ≥4 years custody
- **art_5__para_2** — Art. 5(2): fundamental rights impact assessment and EU database registration requirements for RBI law enforcement use
- **art_5__para_3** — Art. 5(3): prior judicial or independent administrative authorisation; urgency exception (retroactive within 24 hours); prohibition on sole-output adverse decisions
- **art_5__para_4** — Art. 5(4): notification obligations to market surveillance authority and national data protection authority
- **art_5__para_5** — Art. 5(5): Member State obligation to enact enabling national legislation and notify Commission
- **art_5** — Art. 5 (whole article): the prohibited AI practices chapter
- **art_3__para_1** — Art. 3(1): definition of "AI system"
- **art_3__para_3** — Art. 3(3): definition of "provider"
- **art_3__para_4** — Art. 3(4): definition of "deployer" (personal non-professional use carved out of definition itself)
- **art_3__para_39** — Art. 3(39): definition of "emotion recognition system" — AI system identifying or inferring emotions or intentions from biometric data
- **art_3__para_40** — Art. 3(40): definition of "biometric categorisation system" — AI system assigning persons to categories based on biometric data
- **art_3__para_42** — Art. 3(42): definition of "real-time remote biometric identification system" — capturing, comparison and identification without significant delay
- **art_3__para_44** — Art. 3(44): definition of "publicly accessible space" — any physical place accessible to an undetermined number of persons
- **annex_II** — Annex II: "List of Criminal Offences Referred to in Article 5(1), First Subparagraph, Point (h)(iii)" — 16-category list derived from Council Framework Decision 2002/584/JHA
- **art_2__para_3** — Art. 2(3): scope exclusion for military, defence, and national-security AI systems
- **art_2__para_6** — Art. 2(6): scope exclusion for AI systems developed solely for scientific research and development
- **art_2__para_8** — Art. 2(8): scope exclusion for pre-market research, testing, and development activity
- **art_2__para_10** — Art. 2(10): scope exclusion for deployers using AI in purely personal non-professional activities
- **art_6__para_2** — Art. 6(2): Annex III AI systems classified as high-risk
- **art_99__para_3** — Art. 99(3): maximum fine for Art. 5 prohibition violations — EUR 35,000,000 or 7% of worldwide annual turnover, whichever higher
- **art_99__para_4** — Art. 99(4): maximum fine for other operator/notified-body obligation violations — EUR 15,000,000 or 3% of worldwide annual turnover, whichever higher
- **art_99__para_5** — Art. 99(5): maximum fine for supplying inaccurate, incomplete, or misleading information to authorities — EUR 7,500,000 or 1% of worldwide annual turnover, whichever higher
- **art_113** — Art. 113: staggered application dates — 2 Feb 2025 (Ch. I & II), 2 Aug 2025 (GPAI/governance/penalties), 2 Aug 2026 (general), 2 Aug 2027 (Art. 6(1)/Annex I)
- **recital_29** — Recital (29): subliminal AI techniques and exploitation of vulnerabilities; harm need not be intended; medical/commercial-practice exceptions
- **recital_30** — Recital (30): biometric categorisation prohibition for inferring sensitive attributes; carve-out for neutral sorting (e.g. hair/eye colour) in law enforcement datasets
- **recital_31** — Recital (31): social scoring prohibition; applies to both public and private actors; exception for lawful single-purpose evaluations under Union/national law
- **recital_33** — Recital (33): law enforcement RBI exceptions — trafficking victims, imminent threats, terrorist attacks, serious crimes; references 32-offence Framework Decision 2002/584/JHA as basis for Annex II; 4-year threshold rationale
- **recital_35** — Recital (35): prior authorisation requirement for each RBI deployment; urgency exception; mandatory immediate cessation and data deletion if authorisation refused; no adverse decisions based solely on system output
- **recital_42** — Recital (42): prohibition on predictive criminal-offending risk assessments based solely on profiling or personality/characteristics; carve-out for AI supporting human assessments based on objective facts directly linked to criminal activity
- **recital_44** — Recital (44): emotion recognition prohibition in workplace and educational institutions; power-imbalance rationale; medical/safety exception; limited scientific reliability of emotion detection

---

*Report generated by adversarial citation verifier. Sources: https://artificialintelligenceact.eu/ (articles 2, 3, 5, 6, 99, 113; recitals 29, 30, 31, 33, 35, 42, 44; Annex II).*
