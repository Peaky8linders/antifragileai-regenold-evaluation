"""Verbatim expert-reviewer remarks for the 20 Antifragile review questions.

Source: "Antifragile AI Review Questions and Answers.docx" — an EU AI Act legal
expert graded 20 answers produced by an earlier build ("Lexy") and wrote, per
question, the original answer, its citation list, and a Review/Analysis giving
the verdict and the SPECIFIC legal corrections.

This module holds those remarks VERBATIM, extracted mechanically from the docx
(no paraphrase, no summarisation). It exists because the derived encodings —
antifragile_groundtruth.ANTIFRAGILE_GT (synthesized gold answers + machine
checkable mistakes) and antifragile_subpoint_gold (exact sub-point refs)
— are INTERPRETATIONS of this text. When the two disagree, this file wins, and a
judge grading a new answer should be shown the expert's own words rather than a
downstream paraphrase of them.

Fields per qid:
  question        the question as put to the system
  lexy_answer     the graded answer from the earlier build
  lexy_citations  that answer's citation list, as printed in the docx
  review          the expert's verdict and corrections, verbatim

Do NOT edit the review strings. They are evidence.
"""
from __future__ import annotations

# qid -> {question, lexy_answer, lexy_citations, review}
ANTIFRAGILE_REVIEWER_REMARKS: dict[str, dict[str, str]] = {
    'q01': {
        'question': 'What risk categories are provided for AI systems?',
        'lexy_answer': 'At the top, Article 5 (prohibited practices) creates an unacceptable-risk tier that bans eight AI practices outright, including subliminal/manipulative techniques causing significant harm, exploitation of vulnerabilities based on age or disability, social scoring by public authorities, biometric categorisation by sensitive attributes, and real-time remote biometric identification in public spaces by law enforcement — each with narrow, exhaustively-defined carve-outs.',
        'lexy_citations': 'Article 6, Annex III, Annex I, Article 5',
        'review': 'The answer is partially wrong and incomplete, plus an error. The question asks about risk categories, the AI Act establishes a tiered framework: unacceptable (Art. 5), high-risk (Art. 6 via Annex I and Annex III), plus GPAI Art. 51-55 as a parallel regime. The answer addresses only the unacceptable tier.\nThe error:  Art. 5(1)(c) prohibits social scoring without exclusion for public authorities.\nAlso citations list four sources (Art. 5, 6, Annex I, Annex III), but only Art. 5 is addressed in the body.\nThe enumeration also lists only five of the eight Art. 5(1) prohibitions, missing (d, e, f ).',
    },
    'q02': {
        'question': 'What types of AI systems or practices are explicitly prohibited by the AI Act?',
        'lexy_answer': 'Article 5 of the EU AI Act prohibits eight categories of AI practice outright: (a) subliminal, manipulative, or deceptive techniques that cause significant harm; (b) exploitation of vulnerabilities linked to age, disability, or socio-economic situation; (c) social scoring by public authorities producing unjustified detrimental treatment across unrelated contexts.',
        'lexy_citations': 'Article 5, Annex II, Article 27',
        'review': 'Half-right / partial enumeration, repeated error. Correctly identifies Art. 5 and the total count of eight. Then lists only three.\nThe "by public authorities" on social scoring is the same as Q1 error.\nCitations include Annex II (the list of serious criminal offences, relevant only to the Art. 5(1)(h) tangential) and Art. 27 (FRIA, irrelevant to prohibitions).',
    },
    'q03': {
        'question': 'What is the definition of high risk?',
        'lexy_answer': 'Under Article 6, which sets the classification criteria, an AI system is high-risk in two scenarios: it is intended as a safety component of a product governed by Union harmonisation legislation covering machinery, toys, radio equipment, medical devices, lifts, civil aviation, motor vehicles, marine equipment, rail, and agricultural vehicles — or it falls within one of the eight use-case categories enumerated in Annex III.',
        'lexy_citations': 'Article 6, Annex III',
        'review': "Mostly correct, with two material omissions. The two-route framework is right and the Annex I legislation list is a reasonable abbreviation (omitting IVDR, pressure equipment, recreational craft, equipment for explosive atmospheres, and gas appliances).\nFirst omission: the Annex I route requires the underlying product to undergo third-party conformity assessment under the sectoral legislation. This is Art 6(1)(b) and it is substantive for MedTech, a Class I medical device under MDR that doesn't need notified-body assessment doesn't automatically trigger AI Act high-risk via Art 6(1). It could potentially trigger it via Art. 6(2) and Annex III.\nSecond omission: Art. 6(3). An Annex III system is not considered high-risk if it performs (a) a narrow procedural task; (b) improvement of a previously completed human activity; (c) detection of decision-making patterns without replacing human review; or (d) a preparatory task, unless it profiles natural persons. The provider must document the self-assessment and register under Art. 49(2).\nOmitting this overstates the high-risk perimeter materially. The answer provides a general frame\nCitations list Art. 6 and Annex III but not Annex I, despite the answer targeting mostly the Annex I route.",
    },
    'q04': {
        'question': 'Which sectors or applications are considered high-risk under the regulation?',
        'lexy_answer': "Under Article 6 read with Annex III, an AI system is high-risk when it falls into one of eight use-case categories: biometrics, critical infrastructure, education and vocational training, employment and worker management (covering recruitment, task allocation, promotion, termination, and performance evaluation affecting workers' fundamental rights), essential private and public services, law enforcement, migration/asylum/border control, and administration of justice and democratic processes.",
        'lexy_citations': 'Article 6, Annex I, Article 25, Annex III',
        'review': 'Half-right, and one structural omission. The eight Annex III areas are listed correctly. But "sectors or applications" means the Annex I as well and the answer omits this route entirely.\nCitations include Article 25 (value-chain responsibilities). Art. 25  has no connection to which sectors are high-risk.',
    },
    'q05': {
        'question': 'How should users be informed when interacting with AI systems?',
        'lexy_answer': 'Under Article 50(1), which requires AI systems intended to interact directly with natural persons to disclose their AI nature, users must be informed they are communicating with an AI system — unless this is obvious from context. Broader Article 50 transparency obligations extend further: providers of emotion-recognition or biometric-categorisation systems must inform exposed persons, and AI-generated or manipulated content (deepfakes) must be labelled as such.',
        'lexy_citations': 'Article 50.1, Article 50',
        'review': 'Mostly right, with a provider/deployer role error. Art. 50(1) interaction disclosure is correctly stated and correctly attributed to providers.\nThe role error: Art. 50(3) the obligation is on deployers, not providers. Lexy puts it on providers. The deepfake clause also conflates two distinct obligations: Art. 50(2) (providers of AI systems generating synthetic content must mark outputs in machine-readable format) and Art. 50(4) (deployers of deepfakes must disclose artificial generation). Lexy collapses the roles and obligations.',
    },
    'q06': {
        'question': 'What are AI systems with minimal risks?',
        'lexy_answer': 'AI systems with minimal risks are those that fall outside the eight high-risk use-case categories enumerated in biometrics, critical infrastructure, education and vocational training, employment and worker management (including recruitment, performance evaluation, and termination), essential public and private services, law enforcement, migration and asylum, and administration of justice — since it is membership in those categories that triggers the full compliance burden.',
        'lexy_citations': 'Annex III, Article 14, Article 13, Article 27, Article 12, Article 9',
        'review': 'Half-right, partial definition and entirely irrelevant citations. Minimal-risk in the AI Act framework is the residual category, meaning systems that are neither prohibited under Art. 5, nor high-risk via Annex I, nor high-risk via Annex III, nor subject to Art. 50 transparency obligations, nor GPAI.\nAll  citations attach to high-risk systems.',
    },
    'q07': {
        'question': 'What are the guiding principles established by the AI Act?',
        'lexy_answer': 'Prior to placing a general-purpose AI model on the Union market, providers established in third countries shall, by written mandate, appoint an authorised representative which is established in the Union.',
        'lexy_citations': 'Article 54, Article 22, Article 3, Article 53, Article 47, Article 11',
        'review': 'Wrong and topic-shift. The question asks about guiding principles. The answer has no relationship to the question.\nThe correct response would draw on Recital 27, which articulates seven principles for trustworthy AI: human agency and oversight; technical robustness and safety; privacy and data governance; transparency; diversity, non-discrimination and fairness; social and environmental well-being; accountability.',
    },
    'q08': {
        'question': 'What is the definition of a "system of artificial intelligence"?',
        'lexy_answer': 'A machine-based system that is designed to operate with varying levels of autonomy and that may exhibit adaptiveness after deployment, and that, for explicit or implicit objectives, infers, from the input it receives, how to generate outputs such as predictions, content, recommendations, or decisions that can influence physical or virtual environments.',
        'lexy_citations': 'Article 3, Article 2',
        'review': 'Correct.',
    },
    'q09': {
        'question': 'What are the penalties for violating the provisions of the regulation for high-risk AI systems?',
        'lexy_answer': 'In accordance with the terms and conditions laid down in this Regulation, Member States shall lay down the rules on penalties and other enforcement measures, which may also include warnings and non-monetary measures, applicable to infringements of this Regulation by operators, and shall take all measures necessary to ensure that they are properly and effectively implemented, thereby taking into account the guidelines issued by the Commission pursuant to Article 96. The penalties provided for shall be effective, proportionate and dissuasive.',
        'lexy_citations': 'Article 99',
        'review': 'Wrong by omission. The question asks specifically about high-risk penalties. The substantively correct answer is Art. 99(4). SMEs benefit from a lower-of-two-amounts rule under Art 99(6).\nLexy recites Art. 99(1), the generic Member State obligation to establish effective, proportionate and dissuasive penalties. The overall art.99 cited is right.',
    },
    'q10': {
        'question': 'What is the difference between the deployer and the provider?',
        'lexy_answer': 'Under Article 3, a provider is any natural or legal person who develops an AI system (or has one developed) and puts it into service or places it on the market under their own name, while a deployer is any person who uses that system under their own authority — except for personal, non-professional use.',
        'lexy_citations': 'Article 3, Article 19, Article 17, Article 16',
        'review': 'Correct on substance.\nA more complete answer would point on Art. 25 role transitions, a deployer becomes a provider with full Art. 16 obligations when they put their name on a high-risk system, substantially modify it, or change its intended purpose so it becomes high-risk.\nCitations: Art. 17 (quality management) and 19 (automatic logs), are provider duties, not definitions.',
    },
    'q11': {
        'question': 'Does the technical documentation of a high-risk AI system require to provide specifications regarding the required hardware?',
        'lexy_answer': 'Under Article 11(1)–(2), providers must draw up technical documentation before placing a high-risk AI system on the market and keep it up to date, with content meeting at minimum the requirements of which mandates system description, design specifications, and system architecture, all of which encompass the hardware infrastructure on which the system operates and depends. Hardware specifications thus fall squarely within the Annex IV scope as part of the architectural and design record needed to demonstrate conformity.',
        'lexy_citations': 'Annex IV, Article 11, Annex IV.2.a',
        'review': "Correct on substance, wrong sub-citation.\nHardware specification is required in Annex IV, point 1(e). Lexy's Annex IV.2.a points to methods and steps for development, which is unrelated to hardware.\nA complete answer would also reference Annex IV.2(c), the computational resources used to develop, train, test and validate the AI system, part of the technical documentation file under Art 11.",
    },
    'q12': {
        'question': 'Are AI systems intended for emotion recognition from biometric data always prohibited?',
        'lexy_answer': 'Emotion recognition is not categorically prohibited under the AI Act; the prohibition in Article 5 only applies in workplaces and educational institutions, with a narrow medical/safety exception. Elsewhere the system is high-risk under Annex III and triggers Article 50 transparency duties toward exposed persons.',
        'lexy_citations': 'Article 5.1.f, Article 50, Annex III.5, Article 5, Annex III',
        'review': 'Correct on substance, partly wrong sub-citation. The three-layer reasoning is right: the Article 5(1)(f).\nCitation of  Annex III.5 is wrong. Emotion recognition is at Annex III.1(c)\nFor Art. 50, the precise reference is 50(3).',
    },
    'q13': {
        'question': 'Is an AI that transcribes doctor–patient conversations prohibited? Or is it high-risk as per the use cases of Annex III of the AI Act?',
        'lexy_answer': 'Transcribing doctor–patient conversations is not categorically prohibited under Article 5 nor listed in Annex III as a high-risk use case. It becomes high-risk under Article 6 only if deployed as a safety component of a medical device covered by Annex I (e.g. MDR or IVDR). Otherwise Article 50 transparency obligations may apply when the system interacts with patients.',
        'lexy_citations': 'Annex III.5, Annex III, Article 6, Article 5, Annex I',
        'review': 'Correct.\nInaccurate citation:  Annex III.5 among the references despite the answer saying the system is not in Annex III.',
    },
    'q14': {
        'question': 'We are a medical device manufacturer building an AI system to analyze X-rays to detect tumors. Is this system classified as high-risk, and what conformity assessment is required?',
        'lexy_answer': 'An AI system used as a safety component of a product covered by EU harmonisation legislation in Annex I (medical devices under MDR/IVDR, machinery, toys, lifts, civil aviation, motor vehicles, etc.), or which constitutes such a product itself, is high-risk under Article 6.1 when the product requires a third-party conformity assessment. The full Chapter III Section 2 obligations stack on top of the sectoral requirements.',
        'lexy_citations': 'Article 6, Article 43, Annex I, Annex III, Article 5, Article 9, Article 10, Article 11, Article 12, Article 13',
        'review': "Correct on the rule, but generic on the specific case application. Meaning that the answer doesn't apply the rule to the X-ray scenario, doesn’t identify device class under MDR, to confirm high-risk under Art. 6(1) and reference Art. 43(3), for conformity assessment to be integrated into the MDR notified body assessment, one unified procedure for the manufacturer.\nCitations: Art. 5 and Annex III, not relevant to Art. 6(1)/Annex I scenario.",
    },
    'q15': {
        'question': 'Can a hospital use an AI system to sort patients based on their biometric data to determine priority for an experimental clinical trial?',
        'lexy_answer': 'Using AI to triage or prioritise patients (e.g. for a clinical trial or emergency dispatch) is high-risk under Annex III(5)(d) (essential services). If the system also uses biometric categorisation to infer sensitive attributes, it is prohibited under Article 5(1)(g).',
        'lexy_citations': 'Article 5.1.g, Article 6, Annex III, Article 5, Annex I',
        'review': 'Half-right.\nThe Annex III.5(d) citation itself is correctly identified, and it covers emergency calls, triage, dispatch.\nBut the question is about clinical trial selection, not emergency response. A clinical-trial selection process doesn\'t sit there. Depending on the trial\'s structure, it might fall under Annex III.5(a) (eligibility for essential public assistance benefits and services including healthcare services, where the trial offers public-funded access to healthcare), or it might fall outside Annex III entirely and be governed instead by MDR and the Clinical Trials Regulation.\nThe Art 5(1)(g) conditional is right, but loose on specificity. The prohibition triggers only when biometric categorisation infers from a closed list: race, political opinions, trade union membership, religious or philosophical beliefs, sex life, sexual orientation. Biometric data to determine priority doesn\'t automatically infer those attributes, it depends entirely on what\'s being inferred from what. The "if the system also uses biometric categorisation to infer sensitive attributes" framing is correct as a conditional but doesn\'t name the closed-list rule.',
    },
    'q16': {
        'question': 'Our life sciences startup developed a general-purpose AI model trained on massive amounts of genomic data. What transparency obligations apply to us?',
        'lexy_answer': 'GPAI provider obligations: maintain technical documentation per Annex XI, supply downstream-provider information per Annex XII, implement a copyright policy, and publish a sufficiently detailed training-data summary. Under Article 113, Entry into force + application (Regulation 2024/1689): in force 1 August 2024.',
        'lexy_citations': 'Article 53, Article 113, Article 53.1, Article 51, Article 55',
        'review': "Correct on substance. All four Article 53(1) GPAI provider obligations are correctly identified.\nThe sentence about Art 113 is unrelated to the question.\nA thorough answer would also refer to Art. 55 systemic-risk obligations. Also Art. 51, if the model meets the systemic-risk threshold (currently 10^25 FLOPs in cumulative training compute). For a startup model, this typically won't apply, but it should be named as the gating question, as the question mentions “massive amounts of genomic data”.",
    },
    'q17': {
        'question': 'We are a university lab developing an AI model exclusively for scientific research and development into new life science drugs. Does the AI Act apply to our model before it is released to the market?',
        'lexy_answer': "Article 2's scope expressly excludes scientific research and development activity, so an AI model developed by the operator's lab solely for life-science drug R&D falls outside the AI Act for as long as it is used only for that purpose and not placed on the EU market or put into service. That exclusion ends at the point of release: once you place the system on the EU market or put it into service, Article 2's scope attaches and you become a provider subject to the Act's obligations according to the model's risk classification.",
        'lexy_citations': 'Article 2',
        'review': 'Correct.\nA more precise citation Art 2(6). The answer could also reference Art 2(8) on pre-market testing in real-world conditions, which is related but distinct for the testing phase between R&D and market placement.',
    },
    'q18': {
        'question': 'We are developing a generative AI chatbot that will be deployed on a hospital website to answer general patient queries. What transparency obligations apply?',
        'lexy_answer': "Under Article 50, limited-risk transparency duties under Article 50 apply cumulatively with Article 13 high-risk transparency duties — both apply to the same system, not in the alternative. Article 50 transparency applies regardless of risk tier: because the operator's chatbot interacts directly with patients, the operator must design it so each user is informed they are dealing with an AI system (Article 50(1)), and because it is generative, any synthetic content it produces must be marked in a machine-readable, detectable format (Article 50(2)).",
        'lexy_citations': 'Article 13, Article 50, Annex III, Annex I, Article 6',
        'review': 'Half-right. The horizontal principle, that Art. 50 transparency obligations apply regardless of risk tier and apply cumulatively on Art 13 where both apply, is conceptually correct.\nThe classification question within the answer is missing: is this chatbot high-risk? A general patient-query chatbot on a hospital website probably isn\'t. It\'s not Annex III.5(d) emergency triage. It\'s not Annex III.5(a) eligibility-for-benefits unless it determines eligibility. Most likely it\'s limited-risk, Art. 50 alone, not high-risk plus Art. 50. The answer asserts the cumulative framework without doing the classification analysis that determines whether Art. 13 applies at all.\nProvider/deployer role unclear. It uses "operator" for both Art. 50(1) (provider obligation) and Art. 50(2) (provider-of-synthetic-content obligation). For a hospital deploying a third-party chatbot, the hospital is the deployer, Art. 50(4) (deepfake disclosure where applicable) would attach to the hospital.\nCitations include Annex I and Art. 6, but are not addressed in the body.\nCitations: Article 13, Article 50, Annex III, Annex I, Article 6',
    },
    'q19': {
        'question': 'A pharmaceutical company wants to use an AI system to monitor the emotions and stress levels of their manufacturing line workers to improve efficiency. Is this allowed?',
        'lexy_answer': 'Article 5(1)(f) expressly bans AI systems that infer the emotions or mental states of workers in workplace settings, and deploying such a system to improve manufacturing efficiency falls squarely within that prohibition with no applicable exception. The only carve-out is narrow: systems placed on the market strictly for medical or safety reasons (e.g., fatigue detection to prevent industrial accidents) are not prohibited under Article 5(1)(f), but that primary purpose must be established at the point of market-placement and cannot be retrofitted — "efficiency improvement" does not qualify.',
        'lexy_citations': 'Article 5',
        'review': 'Correct.',
    },
    'q20': {
        'question': 'Is an AI system intended to be used as a safety component in robotic surgery considered high-risk under the AI Act?',
        'lexy_answer': 'An AI system used as a safety component of a product covered by EU harmonisation legislation in Annex I (medical devices under MDR/IVDR, machinery, toys, lifts, civil aviation, motor vehicles, etc.), or which constitutes such a product itself, is high-risk under Article 6.1 when the product requires a third-party conformity assessment. The full Chapter III Section 2 obligations stack on top of the sectoral requirements.',
        'lexy_citations': 'Article 6, Annex I',
        'review': "Correct on the rule. Generic on application.\nRobotic surgery devices are typically Class IIb or III under MDR (Rule 12 or Rule 22), which require notified-body conformity assessment, so AI components are high-risk under Article 6(1). Correct.\nThe answer doesn’t engage with what's specifically at stake in robotic surgery: real-time AI involvement in the control loop, the Art. 14 human-oversight design requirements and the layered post-market surveillance under both MDR Art 83 and AI Act Art 72.\nThe answer refers to any medical-device scenario without further analysis.",
    },
}


def remarks_for(qid: str) -> dict[str, str]:
    return ANTIFRAGILE_REVIEWER_REMARKS.get(qid, {})
