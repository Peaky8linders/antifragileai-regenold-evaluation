"""R268 — multi-article-list obligation probe (ab_judge weakness set).

The discovered defect: a question that names two-or-more articles in a LIST
("...obligations under Articles 13 and 50?") had only ONE article grounded in
the Stage-2 context — the engine's pre-R268 explicit-article regex dropped the
plural "Articles" + the trailing list item. No existing benchmark (davidath,
paper-V4, V2, medtech-graphrag, graphrag-bench) asks a question of this shape,
so the fix fires on 0 of their rows and cannot be measured there. This module
supplies a diverse, gold-bearing set of the real-world shape so the R139
``ab_judge`` position-swapped pairwise judge can decide OFF (`REGENOLD_MULTI_
ARTICLE_ENTITIES=0`) vs ON (`=1`) live.

Faithful gold (each named article verified operative for the question);
diverse article pairs + triples + an annex list; phrasings deliberately avoid
the topic-keyword that would let the OLD path surface the article anyway — so
each row genuinely exercises the explicit-list parse.
"""
from __future__ import annotations

SCENARIOS: list[dict] = [
    {
        "id": "ma_01",
        "question": "What transparency obligations apply to a provider of a "
                    "high-risk AI system under Articles 13 and 50?",
        "expected_refs": ["Article 13", "Article 50"],
        "expected_keywords": ["transparency", "deployers", "interpret",
                              "informed", "AI system", "synthetic content",
                              "machine-readable"],
        "gold_answer": "Article 13 requires the provider to design the "
                       "high-risk system so its operation is transparent enough "
                       "for deployers to interpret and use the output, with "
                       "instructions for use; Article 50 adds that a system "
                       "interacting with natural persons must inform them they "
                       "are dealing with an AI system, and synthetic output "
                       "must be marked in a machine-readable, detectable form.",
        "category": "multi_article",
    },
    {
        "id": "ma_02",
        "question": "What must a provider of a high-risk AI system do under "
                    "Articles 9 and 10?",
        "expected_refs": ["Article 9", "Article 10"],
        "expected_keywords": ["risk management", "data governance",
                              "training", "validation", "testing", "bias"],
        "gold_answer": "Article 9 requires a documented risk-management system "
                       "run across the lifecycle; Article 10 requires "
                       "data-governance practices for the training, validation "
                       "and testing datasets, including examination for bias.",
        "category": "multi_article",
    },
    {
        "id": "ma_03",
        "question": "What do Articles 14 and 15 require for high-risk AI "
                    "systems?",
        "expected_refs": ["Article 14", "Article 15"],
        "expected_keywords": ["human oversight", "accuracy", "robustness",
                              "cybersecurity"],
        "gold_answer": "Article 14 requires effective human oversight of the "
                       "high-risk system; Article 15 requires an appropriate "
                       "level of accuracy, robustness and cybersecurity.",
        "category": "multi_article",
    },
    {
        "id": "ma_04",
        "question": "What steps are required under Articles 43 and 49 before a "
                    "high-risk AI system is placed on the market?",
        "expected_refs": ["Article 43", "Article 49"],
        "expected_keywords": ["conformity assessment", "registration",
                              "EU database", "notified body"],
        "gold_answer": "Article 43 requires the applicable conformity "
                       "assessment procedure (internal control or notified "
                       "body); Article 49 requires registration of the system "
                       "in the EU database before it is placed on the market.",
        "category": "multi_article",
    },
    {
        "id": "ma_05",
        "question": "What ongoing duties fall on a provider under Articles 72 "
                    "and 73?",
        "expected_refs": ["Article 72", "Article 73"],
        "expected_keywords": ["post-market monitoring", "serious incident",
                              "reporting", "market surveillance"],
        "gold_answer": "Article 72 requires a post-market monitoring system; "
                       "Article 73 requires reporting of serious incidents to "
                       "the market-surveillance authorities within set "
                       "deadlines.",
        "category": "multi_article",
    },
    {
        "id": "ma_06",
        "question": "What penalties are set out in Articles 99 and 101?",
        "expected_refs": ["Article 99", "Article 101"],
        "expected_keywords": ["fines", "administrative", "GPAI",
                              "AI Office", "turnover"],
        "gold_answer": "Article 99 sets the administrative fines for infringing "
                       "operators (up to fixed ceilings or a percentage of "
                       "worldwide turnover); Article 101 empowers the "
                       "Commission, through the AI Office, to fine "
                       "general-purpose AI model providers.",
        "category": "multi_article",
    },
    {
        "id": "ma_07",
        "question": "What are the respective duties set out in Articles 16 and "
                    "26?",
        "expected_refs": ["Article 16", "Article 26"],
        "expected_keywords": ["provider", "deployer", "instructions for use",
                              "human oversight", "monitoring"],
        "gold_answer": "Article 16 lists the provider obligations for a "
                       "high-risk system; Article 26 lists the deployer "
                       "obligations, including using the system per the "
                       "instructions for use, assigning human oversight and "
                       "monitoring operation.",
        "category": "multi_article",
    },
    {
        "id": "ma_08",
        "question": "What do Articles 16, 17 and 18 require of a provider of a "
                    "high-risk AI system?",
        "expected_refs": ["Article 16", "Article 17", "Article 18"],
        "expected_keywords": ["quality management system", "documentation",
                              "record-keeping", "ten years", "provider"],
        "gold_answer": "Article 16 sets the general provider obligations; "
                       "Article 17 requires a quality-management system; "
                       "Article 18 requires the provider to keep the technical "
                       "documentation for ten years after the system is placed "
                       "on the market.",
        "category": "multi_article",
    },
    {
        "id": "ma_09",
        "question": "Which requirements do Articles 9, 10 and 11 set for a "
                    "high-risk AI system?",
        "expected_refs": ["Article 9", "Article 10", "Article 11"],
        "expected_keywords": ["risk management", "data governance",
                              "technical documentation", "Annex IV"],
        "gold_answer": "Article 9 requires a risk-management system; Article 10 "
                       "requires data-governance practices for the datasets; "
                       "Article 11 requires technical documentation drawn up per "
                       "Annex IV before the system is placed on the market.",
        "category": "multi_article",
    },
    {
        "id": "ma_10",
        "question": "What obligations apply to a general-purpose AI model "
                    "provider under Articles 53 and 55?",
        "expected_refs": ["Article 53", "Article 55"],
        "expected_keywords": ["general-purpose", "technical documentation",
                              "systemic risk", "model evaluation",
                              "serious incidents"],
        "gold_answer": "Article 53 sets the baseline GPAI-provider duties "
                       "(technical documentation, information to downstream "
                       "providers, copyright policy, training-data summary); "
                       "Article 55 adds duties for models with systemic risk, "
                       "including model evaluation, systemic-risk mitigation and "
                       "serious-incident tracking.",
        "category": "multi_article",
    },
    {
        "id": "ma_11",
        "question": "What is the difference between Annexes I and III for "
                    "classifying a high-risk AI system?",
        "expected_refs": ["Annex I", "Annex III"],
        "expected_keywords": ["safety component", "product", "harmonisation",
                              "use case", "high-risk"],
        "gold_answer": "Annex I lists the Union harmonisation legislation under "
                       "which an AI system that is a safety component of, or is "
                       "itself, a regulated product is high-risk; Annex III "
                       "lists the stand-alone high-risk use cases such as "
                       "biometrics, critical infrastructure and employment.",
        "category": "multi_annex",
    },
    {
        "id": "ma_12",
        "question": "How do Articles 5 and 6 classify AI systems differently?",
        "expected_refs": ["Article 5", "Article 6"],
        "expected_keywords": ["prohibited", "high-risk", "Annex III",
                              "classification"],
        "gold_answer": "Article 5 lists the AI practices that are prohibited "
                       "outright; Article 6 sets the criteria under which an AI "
                       "system is classified as high-risk, via Annex I products "
                       "or the Annex III use cases.",
        "category": "multi_article",
    },
]
