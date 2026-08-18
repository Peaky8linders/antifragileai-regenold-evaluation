"""Typed ontology for the EU AI Act knowledge base.

Promotes the previously-implicit entity model (scattered across
``EC_CHECKER_OBLIGATION_MAP`` in :mod:`app.data.kb`,
``_KEYWORD_ENTITY_MAP`` / ``_CLASSIFICATION_TOPICS`` in
:mod:`app.engines.graph_rag`, and ``KEYWORD_TO_ARTICLE`` /
``_AI_ACT_ANCHORS`` in :mod:`app.integrations.regenold.scope`) into a
single typed source of truth.

## Entity types

* :class:`ActorRole` — provider / deployer / importer / distributor /
  authorised representative / downstream provider / notified body /
  affected person. The "role" the user takes in the value chain.
* :class:`RiskClass` — prohibited / high_risk_annex_i / high_risk_annex_iii /
  limited_risk / minimal_risk / gpai / gpai_systemic. The taxonomy
  the regulation uses to gate obligations.
* :class:`Practice` — each Art. 5(1)(a)..(h) prohibited practice.
* :class:`AnnexIIICategory` — each of the 8 high-risk use-case
  categories from Annex III.
* :class:`Phase` — applicability timeline phases (2 Feb 2025, 2 Aug
  2025, 2 Aug 2026, 2 Aug 2027).

## Relationship types

Relationships are typed pointers between entities, modelled as tuple
fields on the dataclasses (each side knows its peers). The route's
retrieval engine can traverse these without a graph DB.

* ``Practice → Article`` (primary anchor — typically Art. 5 + sub-paragraph)
* ``Practice → ExemptionContext`` (workplace-only, medical-safety, narrow
  judicial authorisation, etc.)
* ``AnnexIIICategory → Article`` (Art. 6.2 + Annex III + Chapter III Section 2)
* ``RiskClass → Article`` (which articles enumerate the class)
* ``ActorRole → Article`` (which obligations apply to the role)
* ``Phase → Article`` (which obligations come into force at the phase)

## Why this exists

Three reasons (from the May 2026 audit triple):

1. **Eliminates duplication** between the four lookup maps. Each
   entry now exists in one place; the legacy maps become derived
   views in a later refactor pass.
2. **Enables role × system_type → obligations matrix queries** without
   adding more regex topics. Today's `_CLASSIFICATION_TOPICS` has 18
   hand-curated entries; a typed query against this ontology can
   answer arbitrarily many compositional questions.
3. **Surfaces the schema** so an outside reviewer (regulator, partner,
   future engineer) can audit "what does the system believe about the
   EU AI Act?" by reading one file. See ``docs/ontology/ONTOLOGY.md``
   for the human-readable schema.

The ontology is intentionally additive — existing
``EC_CHECKER_OBLIGATION_MAP`` rows and ``_CLASSIFICATION_TOPICS`` entries
stay live and the engine prefers them when they fire. The ontology
is the new source-of-truth for everything we add from here on, and
the legacy maps will be migrated into derived views in a follow-up.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

# ── Actor roles (Art. 3 definitions, AI Act value chain) ─────────────────


class ActorRole(str, Enum):
    """The eight operator roles defined by the AI Act value chain.

    Each role carries a discrete obligation profile. ``user`` is the
    natural person being affected by an AI output — useful for remedies
    (Arts. 85-86) even though they're not an obligation-bearer.
    """

    PROVIDER = "provider"  # Art. 3(3), primary obligation-bearer
    DEPLOYER = "deployer"  # Art. 3(4), end-user organisation
    IMPORTER = "importer"  # Art. 3(6)
    DISTRIBUTOR = "distributor"  # Art. 3(7)
    AUTHORISED_REPRESENTATIVE = "authorised_representative"  # Art. 3(5)
    DOWNSTREAM_PROVIDER = "downstream_provider"  # Recital 85 + Art. 89
    NOTIFIED_BODY = "notified_body"  # Art. 29 + Annex VII
    AFFECTED_PERSON = "affected_person"  # Arts. 85-86 — not an obligation-bearer


# ── Risk classes (Arts. 5/6 + GPAI dichotomy) ────────────────────────────


class RiskClass(str, Enum):
    """The seven mutually-exclusive risk classes the AI Act enumerates.

    The two high-risk subclasses are kept separate because they trigger
    different conformity-assessment routes (third-party for Annex I
    safety components vs. internal control + optional notified-body
    for Annex III). GPAI is orthogonal to the AI-system risk class —
    a model can be GPAI AND, when integrated into a system, be
    high-risk-by-use-case.
    """

    PROHIBITED = "prohibited"  # Art. 5 — unacceptable risk
    HIGH_RISK_ANNEX_I = "high_risk_annex_i"  # Art. 6.1 — safety component
    HIGH_RISK_ANNEX_III = "high_risk_annex_iii"  # Art. 6.2 — listed use case
    LIMITED_RISK = "limited_risk"  # Art. 50 transparency-only
    MINIMAL_RISK = "minimal_risk"  # No specific obligations (Art. 4 literacy only)
    GPAI = "gpai"  # Art. 51-55 — general-purpose AI model
    GPAI_SYSTEMIC = "gpai_systemic"  # Art. 55 — GPAI with systemic risk


# ── Applicability phases (Art. 113) ────────────────────


@dataclass(frozen=True)
class Phase:
    """One applicability date in the AI Act rollout.

    We encode the original date plus a ``superseded_by``
    pointer to the deferred phase so date-shaped queries can resolve
    "what applies on date X?" deterministically.
    """

    id: str
    label: str
    effective_date: date
    articles: tuple[str, ...]
    description: str
    superseded_by: str | None = None  # id of a later Phase


PHASE_REGISTRY: dict[str, Phase] = {
    "phase_2025_02_02": Phase(
        id="phase_2025_02_02",
        label="Article 5 prohibitions + Article 4 AI literacy",
        effective_date=date(2025, 2, 2),
        articles=("Art. 5", "Art. 4"),
        description=(
            "Prohibitions on the eight unacceptable practices (subliminal "
            "manipulation, vulnerability exploitation, social scoring, "
            "profiling-based criminal-risk prediction, untargeted facial-image "
            "scraping, workplace/education emotion recognition, biometric "
            "categorisation by sensitive attributes, real-time RBI in public "
            "spaces). AI literacy obligation also takes effect."
        ),
    ),
    "phase_2025_08_02": Phase(
        id="phase_2025_08_02",
        label="GPAI provider obligations + governance + penalties",
        effective_date=date(2025, 8, 2),
        articles=("Art. 53", "Art. 55", "Art. 99", "Art. 64", "Art. 65"),
        description=(
            "GPAI provider obligations (technical documentation per Annex XI, "
            "downstream-provider information per Annex XII, copyright policy, "
            "training-data summary). Systemic-risk obligations for designated "
            "GPAIs. AI Office and Board operational. Penalty regime for the "
            "prohibitions takes effect."
        ),
    ),
    "phase_2026_08_02": Phase(
        id="phase_2026_08_02",
        label="High-risk AI obligations (Annex III + most other obligations)",
        effective_date=date(2026, 8, 2),
        articles=("Art. 6", "Art. 8", "Art. 9", "Art. 10", "Art. 11", "Art. 13",
                  "Art. 14", "Art. 15", "Art. 16", "Art. 17", "Art. 26", "Art. 27",
                  "Annex III"),
        description=(
            "Full Chapter III Section 2 obligations for Annex III high-risk AI "
            "systems take effect. Deployer obligations under Art. 26, FRIA "
            "under Art. 27, transparency under Arts. 13/50."
        ),
        # R112 — Digital Omnibus phases removed (split-brain fix). Project
        # policy (commit 2a755d7 + graph_rag_prompts rule 2b) is OFFICIAL
        # DATES ONLY: the Omnibus political agreement is not part of the
        # consolidated EUR-Lex text this KB pins, and the R98 re-add left
        # date-shaped retrieval surfacing deferred dates the rest of the
        # wire is forbidden to mention.
    ),
    "phase_2027_08_02": Phase(
        id="phase_2027_08_02",
        label="High-risk AI obligations (Annex I safety-component path)",
        effective_date=date(2027, 8, 2),
        articles=("Art. 6", "Annex I"),
        description=(
            "Full high-risk obligations for AI as a safety component of a "
            "product regulated by Annex I harmonisation legislation (MDR, "
            "IVDR, machinery, toys, etc.). The longer runway lets sectoral "
            "conformity-assessment bodies update procedures."
        ),
    ),
}


# ── Practices (Art. 5 prohibited practices) ──────────


@dataclass(frozen=True)
class Practice:
    """One prohibited practice under Art. 5.

    Each instance is addressable as a sub-paragraph node (Art. 5(1)(a)
    through (h)). Carries
    the practice description, the exact citation chain, exception
    contexts (workplace-only narrowing, medical-safety carve-out, etc.),
    and the verdict-template prose used by the classification path.
    """

    id: str
    sub_paragraph: str  # e.g. "5.1.a"
    short_name: str
    description: str
    citation: tuple[str, ...]  # e.g. ("Art. 5", "Art. 5.1.a") — internal form
    exceptions: tuple[str, ...] = ()
    related_high_risk_anchor: str | None = None  # e.g. "Annex III" if the
    # exempted variant falls into high-risk
    effective_phase: str = "phase_2025_02_02"
    keywords: tuple[str, ...] = ()  # phrases that anchor a question to this Practice


PRACTICE_REGISTRY: dict[str, Practice] = {
    "subliminal_manipulation": Practice(
        id="subliminal_manipulation",
        sub_paragraph="5.1.a",
        short_name="Subliminal / manipulative / deceptive techniques",
        description=(
            "AI systems that deploy subliminal techniques beyond a person's "
            "consciousness, or purposefully manipulative or deceptive "
            "techniques, with the objective or effect of materially distorting "
            "a person's behaviour in a manner that causes or is reasonably "
            "likely to cause significant harm."
        ),
        citation=("Art. 5", "Art. 5.1.a"),
        exceptions=(
            "Lawful and persuasive advertising or commercial practice that the "
            "individual is aware of and can freely consent to (Recital 29).",
            "Lawful medical treatment for an established mental condition, "
            "with the patient's consent.",
        ),
        keywords=("subliminal", "manipulative technique", "deceptive technique",
                  "subliminal manipulation", "neural data"),
    ),
    "vulnerability_exploitation": Practice(
        id="vulnerability_exploitation",
        sub_paragraph="5.1.b",
        short_name="Exploitation of vulnerabilities",
        description=(
            "AI systems that exploit any of the vulnerabilities of a natural "
            "person or specific group of persons due to age, disability, or a "
            "specific social or economic situation, with the objective or effect "
            "of materially distorting their behaviour in a manner that causes or "
            "is reasonably likely to cause significant harm."
        ),
        citation=("Art. 5", "Art. 5.1.b"),
        exceptions=(
            "Incidental impact on disadvantaged groups via biased training data "
            "is regulated under Art. 10 data governance, not under this "
            "prohibition (Commission Guidelines on Prohibited Practices, "
            "Feb 2025).",
        ),
        keywords=("exploit vulnerabilities", "exploit the vulnerabilities",
                  "exploiting vulnerabilities", "vulnerable groups",
                  "elderly", "exploits the vulnerabilities"),
    ),
    "social_scoring": Practice(
        id="social_scoring",
        sub_paragraph="5.1.c",
        short_name="Social scoring",
        description=(
            "AI systems that evaluate or classify natural persons or groups "
            "based on social behaviour or known/inferred/predicted personal "
            "characteristics, with the social score leading to detrimental or "
            "unfavourable treatment in unrelated social contexts, or to "
            "treatment that is unjustified or disproportionate to their social "
            "behaviour or its gravity."
        ),
        citation=("Art. 5", "Art. 5.1.c"),
        # Art. 5(1)(c) prohibits scoring that LEADS TO detrimental treatment
        # in UNRELATED contexts. Lawful credit/risk scoring in financial
        # services isn't an "exception" to the prohibition — it's a
        # separate use case that's high-risk under Annex III(5)(b), not
        # prohibited under Art. 5(1)(c). Reworded from "exception" to
        # "boundary clarification" per the May 2026 ontology audit.
        exceptions=(
            "Credit-scoring and creditworthiness assessment of natural persons "
            "is NOT an Art. 5(1)(c) prohibition (the data is used in its "
            "original context) but instead falls into the high-risk regime "
            "under Annex III(5)(b) with Chapter III Section 2 obligations.",
        ),
        related_high_risk_anchor="Annex III",
        keywords=("social scoring", "social score"),
    ),
    "profiling_for_criminal_risk": Practice(
        id="profiling_for_criminal_risk",
        sub_paragraph="5.1.d",
        short_name="Predictive policing by personality profiling",
        description=(
            "AI systems that make risk assessments of natural persons in order "
            "to assess or predict the risk of committing a criminal offence, "
            "based solely on profiling of the person or on assessing personality "
            "traits and characteristics."
        ),
        citation=("Art. 5", "Art. 5.1.d"),
        exceptions=(
            "AI systems that support the human assessment of a person's "
            "involvement in a criminal activity based on objective and "
            "verifiable facts directly linked to the activity. These remain "
            "permitted but qualify as high-risk under Annex III(6)(d).",
        ),
        related_high_risk_anchor="Annex III",
        keywords=("predictive policing", "predicting criminality",
                  "criminal-risk profiling", "criminal risk", "criminal-risk"),
    ),
    "facial_recognition_database": Practice(
        id="facial_recognition_database",
        sub_paragraph="5.1.e",
        short_name="Untargeted facial-image scraping",
        description=(
            "AI systems that create or expand facial-recognition databases "
            "through the untargeted scraping of facial images from the "
            "internet or CCTV footage. Applies regardless of whether the "
            "database is temporary, centralised, or decentralised."
        ),
        citation=("Art. 5", "Art. 5.1.e"),
        exceptions=(
            "Targeted scraping for a specific individual (e.g. reverse image "
            "search for a missing person) remains permitted.",
            "Untargeted scraping of non-facial biometric data (voice samples) "
            "or scraping for purposes other than facial-recognition database "
            "building falls outside this prohibition.",
        ),
        keywords=("facial recognition database", "scraping facial",
                  "scraping of facial", "scraping facial images",
                  "untargeted scraping"),
    ),
    "emotion_recognition_workplace": Practice(
        id="emotion_recognition_workplace",
        sub_paragraph="5.1.f",
        short_name="Emotion recognition in workplace or education",
        description=(
            "AI systems that infer emotions of a natural person in the areas of "
            "workplace and education institutions. The Commission's guidelines "
            "interpret both contexts broadly — workplace includes selection and "
            "hiring phases; education includes vocational training."
        ),
        citation=("Art. 5", "Art. 5.1.f"),
        exceptions=(
            "Narrow medical or safety purposes (e.g. detecting pilot or driver "
            "fatigue to prevent accidents) — interpreted narrowly per "
            "Commission Guidelines.",
            "Outside workplace/education contexts the system is high-risk "
            "under Annex III(1)(c), not prohibited.",
        ),
        related_high_risk_anchor="Annex III",
        keywords=("emotion recognition", "emotion inference", "emotion detection",
                  "infer emotions"),
    ),
    "biometric_categorisation_sensitive": Practice(
        id="biometric_categorisation_sensitive",
        sub_paragraph="5.1.g",
        short_name="Biometric categorisation by sensitive attributes",
        description=(
            "Biometric categorisation systems that categorise natural persons "
            "based on their biometric data to deduce or infer race, political "
            "opinion, trade-union membership, religious or philosophical "
            "beliefs, sex life, or sexual orientation."
        ),
        citation=("Art. 5", "Art. 5.1.g"),
        exceptions=(
            "Labelling or filtering of lawfully acquired biometric datasets is "
            "permitted.",
            "Inferences of ethnic origin, health, or genetic data fall outside "
            "this prohibition but are high-risk under Annex III(1)(b).",
        ),
        related_high_risk_anchor="Annex III",
        keywords=("biometric categorisation", "biometric categorization",
                  "biometric sorting", "patient sorting", "sort patients"),
    ),
    "real_time_rbi": Practice(
        id="real_time_rbi",
        sub_paragraph="5.1.h",
        short_name="Real-time remote biometric ID in public spaces",
        description=(
            "Real-time remote biometric identification of natural persons in "
            "publicly accessible spaces by law enforcement, where the "
            "identification is made without the individual's involvement and "
            "the biometric capture-and-match has minimal delay."
        ),
        citation=("Art. 5", "Art. 5.1.h"),
        exceptions=(
            "Narrow law-enforcement exceptions with prior judicial or "
            "administrative authorisation: search for missing persons or "
            "victims of trafficking; prevention of a specific, substantial, "
            "imminent threat to life or terrorist attack; localisation of "
            "suspects in serious crimes listed in Annex II.",
            "Biometric verification (e.g. unlocking your phone) is "
            "distinguished from identification and not prohibited.",
        ),
        keywords=("real-time biometric", "real time biometric",
                  "real-time remote biometric", "biometric identification",
                  "rbi in public", "remote biometric identification"),
    ),
}


# R46 B6 — single compliance-vocabulary source of truth. Every keyword
# in the per-Practice tuples above must also appear in the canonical
# union exported by :mod:`app.data.compliance_vocab`. The check fires
# once at module import (free at request time) and fails loudly if a
# per-Practice edit drifts from the canonical surface. The canonical
# surface in turn carries the same keywords for compliance_vocab's
# :data:`PRACTICE_KEYWORDS` derived set, so the three consumers
# (compliance_verdict, scope, ontology) can never silently diverge.
def _validate_practice_keywords_against_canonical() -> None:
    from app.data.compliance_vocab import PRACTICE_KEYWORDS as _CANONICAL

    actual = frozenset(
        kw
        for practice in PRACTICE_REGISTRY.values()
        for kw in practice.keywords
    )
    missing_from_canonical = actual - _CANONICAL
    if missing_from_canonical:
        raise AssertionError(
            "PRACTICE_REGISTRY keywords drifted from "
            "app.data.compliance_vocab.PRACTICE_KEYWORDS — add "
            f"{sorted(missing_from_canonical)!r} to _PRACTICE_NOUNS"
        )


_validate_practice_keywords_against_canonical()


# ── Annex III categories (the 8 high-risk use cases) ─────────────────────


@dataclass(frozen=True)
class AnnexIIICategory:
    """One of the eight high-risk use-case categories enumerated in Annex III.

    Each category triggers the full Chapter III Section 2 obligations
    on providers (Arts. 8-15), the deployer duties of Art. 26, and —
    for public-sector deployers and selected private deployers — the
    Fundamental Rights Impact Assessment of Art. 27. Some categories
    also relate to specific Art. 5 prohibitions (e.g. category (1)
    biometrics borders on Art. 5(1)(g)/(h), category (6) law
    enforcement borders on Art. 5(1)(d)/(h)).
    """

    id: str
    number: int  # 1-8
    short_name: str
    description: str
    sub_points: tuple[str, ...] = ()  # sub-categories within the high-risk row
    related_prohibitions: tuple[str, ...] = ()  # Practice ids that border this category
    keywords: tuple[str, ...] = ()


ANNEX_III_REGISTRY: dict[str, AnnexIIICategory] = {
    "biometrics": AnnexIIICategory(
        id="biometrics",
        number=1,
        short_name="Biometric systems (non-prohibited variants)",
        description=(
            "AI systems intended to be used for remote biometric identification "
            "of natural persons (post-incident or not in public spaces — "
            "real-time RBI in public spaces is PROHIBITED under Art. 5(1)(h)), "
            "biometric categorisation according to sensitive or protected "
            "attributes or characteristics, or emotion "
            "recognition outside workplaces and educational institutions."
        ),
        # ⚠ CORRECTED 2026-08-14 — (1)(b) previously read "biometric
        # categorisation by NON-SENSITIVE attributes", which negates the Act.
        # Annex III(1)(b) verbatim: "AI systems intended to be used for
        # biometric categorisation, according to SENSITIVE OR PROTECTED
        # attributes or characteristics based on the inference of those
        # attributes or characteristics."
        #
        # The old wording did not merely lose nuance, it inverted the test a
        # reader applies: it implied a system categorising on sensitive traits
        # falls OUTSIDE Annex III(1)(b), when that is exactly what puts it in.
        # The genuine boundary is against Art. 5(1)(g), which PROHIBITS
        # categorisation inferring a narrower closed set (race, political
        # opinions, trade-union membership, religious or philosophical beliefs,
        # sex life, sexual orientation). Annex III(1)(b) is the broader
        # high-risk tier beneath that prohibition — not its complement.
        sub_points=("(1)(a) Remote biometric ID (non-real-time / not public-space)",
                    "(1)(b) Biometric categorisation according to sensitive or "
                    "protected attributes (Art. 5(1)(g) prohibits the narrower "
                    "inferred-trait set outright)",
                    "(1)(c) Emotion recognition outside workplace/education"),
        related_prohibitions=("real_time_rbi", "biometric_categorisation_sensitive",
                              "emotion_recognition_workplace"),
        keywords=("biometric identification", "post-remote biometric",
                  "emotion recognition"),
    ),
    "critical_infrastructure": AnnexIIICategory(
        id="critical_infrastructure",
        number=2,
        short_name="Critical infrastructure",
        description=(
            "AI systems intended to be used as safety components in the "
            "management and operation of critical digital infrastructure, road "
            "traffic, or the supply of water, gas, heating, or electricity."
        ),
        keywords=("critical infrastructure", "critical digital infrastructure",
                  "road traffic", "water supply", "electricity grid",
                  "energy grid", "gas supply"),
    ),
    "education_grading": AnnexIIICategory(
        id="education_grading",
        number=3,
        short_name="Education and vocational training",
        description=(
            "AI systems intended to be used for determining access or admission, "
            "evaluating learning outcomes, assessing the appropriate level of "
            "education, or monitoring prohibited behaviour during tests."
        ),
        sub_points=("(3)(a) Access / admission decisions",
                    "(3)(b) Evaluation of learning outcomes",
                    "(3)(c) Level-of-education assessment",
                    "(3)(d) Test-behaviour monitoring"),
        keywords=("education grading", "student grading", "essay grading",
                  "student assessment", "exam monitoring", "admission decisions"),
    ),
    "employment": AnnexIIICategory(
        id="employment",
        number=4,
        short_name="Employment and worker management",
        description=(
            "AI systems intended to be used for recruitment or selection of "
            "candidates (including targeted job advertisements, screening, "
            "filtering, and evaluation), or for taking employment-related "
            "decisions affecting terms, promotion, termination, task "
            "allocation, or monitoring."
        ),
        sub_points=("(4)(a) Recruitment / selection",
                    "(4)(b) Decisions affecting work relationships"),
        keywords=("cv screening", "resume screening", "hr screening",
                  "hiring decision", "candidate screening", "applicant screening",
                  "worker monitoring", "employment ai"),
    ),
    "essential_services": AnnexIIICategory(
        id="essential_services",
        number=5,
        short_name="Essential private and public services",
        description=(
            "AI systems intended to be used for: (a) eligibility for essential "
            "public assistance benefits and services (welfare, healthcare, "
            "education); (b) evaluating creditworthiness of natural persons or "
            "establishing credit scores (except detection of financial fraud); "
            "(c) risk assessment and pricing in life and health insurance for "
            "natural persons; (d) emergency-response dispatch and triage."
        ),
        sub_points=("(5)(a) Public benefit eligibility",
                    "(5)(b) Creditworthiness / credit score",
                    "(5)(c) Life/health insurance pricing",
                    "(5)(d) Emergency-response triage"),
        keywords=("credit scoring", "creditworthiness", "credit score",
                  "welfare eligibility", "insurance pricing",
                  "emergency dispatch", "medical triage", "clinical triage",
                  "patient triage", "patient prioritization",
                  "determine priority"),
    ),
    "law_enforcement": AnnexIIICategory(
        id="law_enforcement",
        number=6,
        short_name="Law enforcement (non-prohibited variants)",
        description=(
            "AI systems intended for use by or on behalf of law-enforcement "
            "authorities for: (a) individual risk assessment as victim of "
            "criminal offence; (b) polygraph-like tools; (c) reliability of "
            "evidence; (d) profiling of natural persons in the context of "
            "detection, investigation or prosecution; (e) crime analytics. "
            "Profiling-based criminal-risk prediction of a person is "
            "PROHIBITED under Art. 5(1)(d); real-time RBI is PROHIBITED under "
            "Art. 5(1)(h)."
        ),
        related_prohibitions=("profiling_for_criminal_risk", "real_time_rbi"),
        keywords=("law enforcement", "police risk assessment", "crime analytics",
                  "evidence reliability", "criminal investigation"),
    ),
    "migration_asylum": AnnexIIICategory(
        id="migration_asylum",
        number=7,
        short_name="Migration, asylum, and border control",
        description=(
            "AI systems intended for use by or on behalf of competent public "
            "authorities for: (a) polygraph-like tools at border crossings; "
            "(b) risk assessment of irregular migrants; (c) examination of "
            "asylum, visa, or residence-permit applications; (d) detection, "
            "recognition, or identification of natural persons in migration / "
            "asylum / border-control contexts (excluding travel-document "
            "authenticity checks)."
        ),
        keywords=("asylum application", "asylum applications", "migration risk",
                  "visa application", "border control", "migrant"),
    ),
    "justice_democracy": AnnexIIICategory(
        id="justice_democracy",
        number=8,
        short_name="Administration of justice and democratic processes",
        description=(
            "AI systems intended for use by judicial authorities (or alternative "
            "dispute resolution bodies) to assist in researching and "
            "interpreting facts and law and applying the law to a specific set "
            "of facts; or AI systems intended to influence the outcome of an "
            "election or referendum, or the voting behaviour of natural persons "
            "(excluding outputs not directed at people, like administrative or "
            "logistical tools)."
        ),
        keywords=("judicial authority", "assist judges", "legal interpretation",
                  "election outcome", "voting behaviour", "voting behavior",
                  "judiciary ai"),
    ),
}


# ── AIRO Causal Risk Entities (ISO 31000 / ISO/IEC 23894 / AIRO) ─────────


@dataclass(frozen=True)
class RiskScenario:
    """Represents an AIRO-aligned causal risk chain.

    Maps Hazard/Threat → Vulnerability → Risk Event → Impact/Harm →
    Protected Legal Interest (AreaOfImpact) → Statutory Articles.
    """

    id: str
    short_name: str
    hazard_or_threat: str  # e.g. "Sampling bias / demographic underrepresentation"
    vulnerability: str     # e.g. "Uncalibrated classification boundary across protected groups"
    risk_event: str        # e.g. "Disparate false rejection rate in automated recruitment"
    impact_area: str       # e.g. "Fundamental rights: Non-discrimination (EU Charter Art. 21)"
    severity_level: str    # "low" | "medium" | "high" | "critical"
    statutory_violation: tuple[str, ...]  # Canonical article refs
    required_controls: tuple[str, ...]    # Pointers to RiskControl ids
    description: str
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class RiskControl:
    """A technical or organizational measure modifying AI risk (AIRO/CodexAI).

    Connects risk mitigation to engineering telemetry, verification
    artifacts (evidenced_by), and harmonised standards.
    """

    id: str
    name: str
    control_type: str      # "technical" | "organizational"
    lifecycle_phase: str   # "development" | "validation" | "deployment" | "operation"
    mitigates_risk_id: str
    evidenced_by: tuple[str, ...]   # Required test reports / logs
    standards_ref: tuple[str, ...]  # e.g. ("ISO/IEC 42001:2023 §A.6", "ISO/IEC 23894:2023 §8")
    articles: tuple[str, ...] = ()
    description: str = ""
    keywords: tuple[str, ...] = ()


RISK_SCENARIO_REGISTRY: dict[str, RiskScenario] = {
    "sampling_bias_recruitment": RiskScenario(
        id="sampling_bias_recruitment",
        short_name="Sampling bias in candidate screening",
        hazard_or_threat="Demographic underrepresentation and historical bias in training corpus",
        vulnerability="Feature correlation with protected characteristics (gender, ethnicity)",
        risk_event="Automated rejection or ranking penalty for underrepresented applicants",
        impact_area="Fundamental Rights: Non-discrimination (Charter Art. 21) & Equal Treatment",
        severity_level="high",
        statutory_violation=("Art. 10", "Art. 15", "Annex III"),
        required_controls=("demographic_parity_regularization", "counterfactual_fairness_audit"),
        description=(
            "AI systems for recruitment or candidate selection that exhibit "
            "demographic disparities due to unrepresentative training data, "
            "violating Article 10 data governance and Article 15 accuracy standards."
        ),
        keywords=("recruitment bias", "hiring disparity", "cv screening bias",
                  "sampling bias", "demographic disparity", "resume bias"),
    ),
    "prompt_injection_safety_bypass": RiskScenario(
        id="prompt_injection_safety_bypass",
        short_name="Adversarial prompt injection and guardrail bypass",
        hazard_or_threat="Malicious user prompt crafting or indirect data poisoning",
        vulnerability="Inadequate system-prompt isolation and unconstrained tool execution",
        risk_event="Unauthorized output generation, data exfiltration, or safety guardrail bypass",
        impact_area="Health, Safety & Cybersecurity Integrity",
        severity_level="critical",
        statutory_violation=("Art. 15", "Art. 55"),
        required_controls=("adversarial_red_teaming_guardrail", "runtime_drift_telemetry_monitoring"),
        description=(
            "Adversarial threats against GPAI or conversational AI systems where "
            "crafted inputs bypass alignment filters or trigger unauthorized actions, "
            "violating Article 15 cybersecurity and Article 55 systemic mitigation requirements."
        ),
        keywords=("prompt injection", "jailbreak", "adversarial attack",
                  "guardrail bypass", "indirect prompt injection", "model extraction"),
    ),
    "unmonitored_drift_clinical_triage": RiskScenario(
        id="unmonitored_drift_clinical_triage",
        short_name="Clinical distribution drift in triage AI",
        hazard_or_threat="Covariate shift between training population and operational clinical setting",
        vulnerability="Lack of continuous telemetry and automated calibration drift alerting",
        risk_event="Misclassification of patient urgency in emergency medical triage",
        impact_area="Health and Safety & Life Integrity",
        severity_level="critical",
        statutory_violation=("Art. 9", "Art. 14", "Art. 72", "Annex III"),
        required_controls=("runtime_drift_telemetry_monitoring", "human_in_the_loop_override_gate"),
        description=(
            "AI systems used in emergency dispatch or clinical patient triage that suffer "
            "performance degradation due to patient demographic shift without post-market monitoring, "
            "violating Article 9 risk management, Article 14 human oversight, and Article 72 post-market monitoring."
        ),
        keywords=("clinical triage drift", "patient triage failure", "distribution drift",
                  "covariate shift", "emergency dispatch error", "medical triage failure"),
    ),
    "opaque_credit_scoring_discrimination": RiskScenario(
        id="opaque_credit_scoring_discrimination",
        short_name="Opaque discriminatory credit scoring",
        hazard_or_threat="Complex non-linear proxy variables for socioeconomic vulnerability",
        vulnerability="Black-box decision boundaries lacking interpretability and explanation telemetry",
        risk_event="Unjustified credit denial without meaningful explanation to affected person",
        impact_area="Fundamental Rights & Access to Essential Private Services (Charter Art. 34)",
        severity_level="high",
        statutory_violation=("Art. 13", "Art. 86", "Annex III"),
        required_controls=("human_in_the_loop_override_gate", "prov_o_audit_logging"),
        description=(
            "Credit-scoring AI systems using opaque proxy variables that result in discriminatory "
            "credit denial, violating Article 13 transparency, Article 86 right to explanation, "
            "and Annex III(5)(b) high-risk requirements."
        ),
        keywords=("credit scoring discrimination", "loan denial explanation",
                  "credit score opacity", "creditworthiness bias", "credit denial"),
    ),
    "deepfake_election_disinformation": RiskScenario(
        id="deepfake_election_disinformation",
        short_name="Synthetic media election manipulation",
        hazard_or_threat="Generative synthesis of realistic audiovisual content of political figures",
        vulnerability="Missing machine-readable watermarking and provenance metadata",
        risk_event="Voter deception and democratic process distortion via undetected synthetic media",
        impact_area="Democracy and Rule of Law & Electoral Integrity",
        severity_level="critical",
        statutory_violation=("Art. 50", "Art. 55", "Annex III"),
        required_controls=("output_watermarking_verification", "prov_o_audit_logging"),
        description=(
            "Generation and dissemination of synthetic audio/visual content intended to influence "
            "elections without transparent labeling, violating Article 50 transparency obligations "
            "and Annex III(8) democratic process protections."
        ),
        keywords=("deepfake election", "synthetic media politics", "voter deception",
                  "ai disinformation", "election manipulation", "synthetic audio deepfake"),
    ),
    "biometric_categorisation_discrimination": RiskScenario(
        id="biometric_categorisation_discrimination",
        short_name="Sensitive attribute inference from biometric data",
        hazard_or_threat="Inferring protected sensitive attributes (race, beliefs, sexual orientation) from facial or acoustic features",
        vulnerability="Latent feature correlation and lack of attribute disentanglement in embedding space",
        risk_event="Unlawful demographic categorization or sorting in violation of Article 5(1)(g) and Annex III(1)(b)",
        impact_area="Fundamental Rights: Human Dignity, Non-discrimination (Charter Art. 21) & Privacy",
        severity_level="critical",
        statutory_violation=("Art. 5", "Art. 10", "Annex III"),
        required_controls=("biometric_attribute_sanitization", "counterfactual_fairness_audit"),
        description=(
            "AI systems deducing sensitive traits (political views, religious beliefs, race, sexual orientation) "
            "from biometric data, triggering the Article 5(1)(g) prohibition or Annex III(1)(b) high-risk controls."
        ),
        keywords=("biometric categorization", "sensitive attribute inference", "biometric discrimination",
                  "facial trait inference", "prohibited categorization"),
    ),
    "critical_infrastructure_cps_failure": RiskScenario(
        id="critical_infrastructure_cps_failure",
        short_name="Cyber-physical critical infrastructure failure",
        hazard_or_threat="Adversarial perturbation or telemetry timing drift in physical grid/traffic safety control components",
        vulnerability="Lack of deterministic fail-safe override and physical sensor cross-validation",
        risk_event="Uncontrolled shutdown or dangerous actuation in electricity grid, water supply, or road traffic control",
        impact_area="Health and Safety & Critical Public Infrastructure Resilience",
        severity_level="critical",
        statutory_violation=("Art. 9", "Art. 15", "Annex III"),
        required_controls=("fail_safe_redundant_fallback", "runtime_drift_telemetry_monitoring"),
        description=(
            "Safety components in critical digital infrastructure, electricity, water, or traffic management "
            "failing under unexpected operating regimes, violating Article 9 risk management and Article 15 robustness."
        ),
        keywords=("critical infrastructure failure", "cps safety failure", "grid control ai",
                  "water supply ai failure", "traffic control safety component"),
    ),
    "unlogged_automated_decision_forensics": RiskScenario(
        id="unlogged_automated_decision_forensics",
        short_name="Opaque unlogged high-risk automated decision",
        hazard_or_threat="Autonomous model decision execution without tamper-evident audit trail",
        vulnerability="Ephemeral in-memory logging lacking cryptographically verifiable provenance",
        risk_event="Inability to audit post-incident causality or fulfill Article 86 right to explanation requests",
        impact_area="Rule of Law & Right to an Effective Remedy (Charter Art. 47 / AI Act Arts. 85-86)",
        severity_level="high",
        statutory_violation=("Art. 12", "Art. 73", "Art. 86"),
        required_controls=("prov_o_audit_logging",),
        description=(
            "Failure to automatically record event logs throughout the lifecycle of high-risk AI systems, "
            "violating Article 12 record-keeping, Article 73 incident reporting, and Article 86 explanation rights."
        ),
        keywords=("unlogged decision", "missing audit log", "article 12 failure",
                  "logging violation", "forensic audit failure"),
    ),
}

RISK_CONTROL_REGISTRY: dict[str, RiskControl] = {
    "demographic_parity_regularization": RiskControl(
        id="demographic_parity_regularization",
        name="Demographic Parity Loss Regularization",
        control_type="technical",
        lifecycle_phase="development",
        mitigates_risk_id="sampling_bias_recruitment",
        evidenced_by=("disparate_impact_ratio_report", "fairness_metrics_log"),
        standards_ref=("ISO/IEC 23894:2023 §8.2", "ISO/IEC 42001:2023 §A.6.2"),
        articles=("Art. 10", "Art. 15"),
        description="Algorithmic penalty enforcing statistical parity across protected demographic groups during model training.",
        keywords=("demographic parity", "fairness regularization", "debiasing loss", "fairness loss"),
    ),
    "counterfactual_fairness_audit": RiskControl(
        id="counterfactual_fairness_audit",
        name="Counterfactual Fairness Auditing & Perturbation Testing",
        control_type="technical",
        lifecycle_phase="validation",
        mitigates_risk_id="sampling_bias_recruitment",
        evidenced_by=("counterfactual_testing_log", "bias_audit_certificate"),
        standards_ref=("ISO/IEC 23894:2023 §8.4", "CEN/CENELEC JTC 21 WG4"),
        articles=("Art. 10", "Art. 15"),
        description="Systematic perturbation of sensitive attributes to verify output invariance across counterfactual twins.",
        keywords=("counterfactual audit", "fairness testing", "bias audit", "counterfactual test"),
    ),
    "adversarial_red_teaming_guardrail": RiskControl(
        id="adversarial_red_teaming_guardrail",
        name="Adversarial Red-Teaming & Input Guardrails",
        control_type="technical",
        lifecycle_phase="validation",
        mitigates_risk_id="prompt_injection_safety_bypass",
        evidenced_by=("red_teaming_report", "guardrail_coverage_matrix"),
        standards_ref=("ISO/IEC 23894:2023 §9.1", "NIST AI 100-2 §4"),
        articles=("Art. 15", "Art. 55"),
        description="Structured red-teaming and input sanitization layers preventing prompt injection and adversarial jailbreaks.",
        keywords=("red teaming", "adversarial testing", "input guardrail", "jailbreak defense"),
    ),
    "runtime_drift_telemetry_monitoring": RiskControl(
        id="runtime_drift_telemetry_monitoring",
        name="Runtime Covariate Drift & Telemetry Monitoring",
        control_type="technical",
        lifecycle_phase="operation",
        mitigates_risk_id="unmonitored_drift_clinical_triage",
        evidenced_by=("drift_telemetry_dashboard", "ks_test_drift_alerts"),
        standards_ref=("ISO/IEC 42001:2023 §A.9.3", "ISO/IEC 23894:2023 §10"),
        articles=("Art. 9", "Art. 72"),
        description="Continuous statistical monitoring of input distributions and accuracy degradation with automated alert triggers.",
        keywords=("drift monitoring", "runtime telemetry", "covariate drift alert", "telemetry monitoring"),
    ),
    "human_in_the_loop_override_gate": RiskControl(
        id="human_in_the_loop_override_gate",
        name="Human-in-the-Loop Override & Escalation Protocol",
        control_type="organizational",
        lifecycle_phase="operation",
        mitigates_risk_id="unmonitored_drift_clinical_triage",
        evidenced_by=("human_override_audit_trail", "operator_competency_record"),
        standards_ref=("ISO/IEC 22989:2022 §5.5", "ISO/IEC 42001:2023 §A.8"),
        articles=("Art. 14", "Art. 26"),
        description="Formal procedures enabling human overseers to intervene, halt, or override automated high-risk decisions.",
        keywords=("human in the loop", "human oversight", "override protocol", "hitl gate", "human escalation"),
    ),
    "output_watermarking_verification": RiskControl(
        id="output_watermarking_verification",
        name="Cryptographic Watermarking & Provenance Tagging",
        control_type="technical",
        lifecycle_phase="deployment",
        mitigates_risk_id="deepfake_election_disinformation",
        evidenced_by=("c2pa_metadata_manifest", "watermark_detection_log"),
        standards_ref=("C2PA Technical Specification v1.3", "ISO/IEC 23894:2023 §8.6"),
        articles=("Art. 50", "Art. 55"),
        description="Machine-readable, cryptographically verifiable watermarking of AI-generated audiovisual content per Article 50.",
        keywords=("watermarking", "synthetic content marking", "c2pa", "provenance metadata", "ai watermark"),
    ),
    "prov_o_audit_logging": RiskControl(
        id="prov_o_audit_logging",
        name="Tamper-Evident PROV-O Activity & Decision Logging",
        control_type="technical",
        lifecycle_phase="operation",
        mitigates_risk_id="opaque_credit_scoring_discrimination",
        evidenced_by=("tamper_evident_event_log", "prov_o_activity_graph"),
        standards_ref=("W3C PROV-O Recommendation", "ISO/IEC 42001:2023 §A.9.2"),
        articles=("Art. 12", "Art. 86"),
        description="Automated logging of inputs, outputs, timestamps, and operator identity matching Article 12 record-keeping requirements.",
        keywords=("audit logging", "record keeping", "prov-o logging", "tamper evident log", "decision log"),
    ),
    "biometric_attribute_sanitization": RiskControl(
        id="biometric_attribute_sanitization",
        name="Biometric Attribute Disentanglement & Latent Sanitization",
        control_type="technical",
        lifecycle_phase="development",
        mitigates_risk_id="biometric_categorisation_discrimination",
        evidenced_by=("attribute_orthogonalization_report", "embedding_leakage_audit"),
        standards_ref=("ISO/IEC 23894:2023 §8.5", "ISO/IEC 42001:2023 §A.6"),
        articles=("Art. 10", "Art. 15"),
        description="Disentanglement filters and orthogonal subspace projections removing sensitive attribute proxies from biometric embeddings.",
        keywords=("biometric sanitization", "attribute disentanglement", "latent sanitization", "sensitive attribute removal"),
    ),
    "fail_safe_redundant_fallback": RiskControl(
        id="fail_safe_redundant_fallback",
        name="Deterministic Fail-Safe & Redundant Fallback Architecture",
        control_type="technical",
        lifecycle_phase="operation",
        mitigates_risk_id="critical_infrastructure_cps_failure",
        evidenced_by=("failover_verification_report", "safety_instrumented_system_audit"),
        standards_ref=("IEC 61508 SIL-3", "ISO/IEC 42001:2023 §A.7"),
        articles=("Art. 9", "Art. 15"),
        description="Hardware-level and deterministic software interlocks ensuring graceful degradation and fail-safe shutdown in critical infrastructure.",
        keywords=("fail safe", "redundant fallback", "deterministic fallback", "cps failover"),
    ),
}


# ── General-Purpose AI (GPAI) Governance (Articles 51–56) ────────────────

@dataclass(frozen=True)
class GPAIModelProfile:
    """Specialized governance profile for General-Purpose AI models.

    Models compute FLOP thresholds (≥10^25 FLOPs triggers systemic designation
    under Art. 51(2)), open-source carve-outs (Art. 53(2)), and documentation bindings.
    """

    id: str
    model_name: str
    training_compute_flops: float        # e.g. 1.0e25
    is_open_source: bool                 # Triggers Art. 53(2) exemptions
    has_systemic_risk: bool              # Art. 51 systemic designation
    mandatory_obligations: tuple[str, ...]
    technical_doc_annex: str             # "Annex XI"
    downstream_info_annex: str           # "Annex XII"
    description: str
    keywords: tuple[str, ...] = ()


GPAI_REGISTRY: dict[str, GPAIModelProfile] = {
    "standard_gpai_proprietary": GPAIModelProfile(
        id="standard_gpai_proprietary",
        model_name="Standard Proprietary GPAI Model (<10^25 FLOPs)",
        training_compute_flops=1.0e24,
        is_open_source=False,
        has_systemic_risk=False,
        mandatory_obligations=("Art. 53", "Annex XI", "Annex XII"),
        technical_doc_annex="Annex XI",
        downstream_info_annex="Annex XII",
        description=(
            "General-purpose AI model developed under proprietary license with training compute "
            "below 10^25 FLOPs. Requires technical documentation per Annex XI, downstream provider "
            "information per Annex XII, copyright compliance policy (Art. 53(1)(c)), and public "
            "training data summary (Art. 53(1)(d))."
        ),
        keywords=("standard gpai", "proprietary gpai", "gpai technical documentation",
                  "annex xi", "annex xii", "training data summary", "copyright policy"),
    ),
    "standard_gpai_open_source": GPAIModelProfile(
        id="standard_gpai_open_source",
        model_name="Open-Source / Free & Open License GPAI Model (<10^25 FLOPs)",
        training_compute_flops=1.0e24,
        is_open_source=True,
        has_systemic_risk=False,
        # Art. 53(2) carve-out: open-source GPAI without systemic risk is EXEMPT from
        # Annex XI technical documentation and Annex XII downstream provider information,
        # but MUST still provide the copyright policy and training-data summary.
        mandatory_obligations=("Art. 53",),
        technical_doc_annex="",
        downstream_info_annex="",
        description=(
            "General-purpose AI model released under a free and open-source license without "
            "systemic risk. Benefits from Article 53(2) carve-out: exempt from Annex XI technical "
            "documentation and Annex XII downstream information, but still subject to Article "
            "53(1)(c) copyright policy and Article 53(1)(d) training content summary."
        ),
        keywords=("open source gpai", "open-source exemption", "article 53(2)",
                  "free and open license", "open weights gpai"),
    ),
    "systemic_gpai_frontier": GPAIModelProfile(
        id="systemic_gpai_frontier",
        model_name="Frontier GPAI Model with Systemic Risk (≥10^25 FLOPs)",
        training_compute_flops=1.0e26,
        is_open_source=False,
        has_systemic_risk=True,
        mandatory_obligations=("Art. 53", "Art. 55", "Annex XI", "Annex XII", "Annex XIII"),
        technical_doc_annex="Annex XI",
        downstream_info_annex="Annex XII",
        description=(
            "Frontier GPAI model with cumulative training compute exceeding 10^25 FLOPs or designated "
            "by the Commission under Article 51. Subject to all standard GPAI obligations plus Article 55 "
            "systemic duties: model evaluations, adversarial red-teaming, tracking and reporting serious "
            "incidents to AI Office, cybersecurity protections, and energy consumption reporting per Annex XI/XIII."
        ),
        keywords=("systemic gpai", "systemic risk", "10^25 flops", "frontier model",
                  "article 55", "adversarial red teaming", "systemic model evaluation"),
    ),
    "systemic_gpai_open_weights": GPAIModelProfile(
        id="systemic_gpai_open_weights",
        model_name="Open-Weights Frontier GPAI Model with Systemic Risk (≥10^25 FLOPs)",
        training_compute_flops=1.0e26,
        is_open_source=True,
        has_systemic_risk=True,
        mandatory_obligations=("Art. 53", "Art. 55", "Annex XI", "Annex XII", "Annex XIII"),
        technical_doc_annex="Annex XI",
        downstream_info_annex="Annex XII",
        description=(
            "Frontier open-weights/open-source GPAI model with cumulative training compute exceeding 10^25 FLOPs. "
            "Per Article 53(2) proviso, open-source carve-outs DO NOT apply to models with systemic risk. "
            "Subject to all Article 53 technical documentation and Article 55 systemic risk duties."
        ),
        keywords=("open weights systemic", "open source systemic gpai", "frontier open weights",
                  "article 53(2) systemic exception", "open source frontier model"),
    ),
}


# ── Conformity Assessment Routes (Articles 43, 47, 48 & Annexes VI/VII) ──

class ConformityRoute(str, Enum):
    """The three statutory conformity assessment routes under Article 43."""

    ANNEX_VI_INTERNAL_CONTROL = "annex_vi_internal_control"
    ANNEX_VII_NOTIFIED_BODY = "annex_vii_notified_body"
    ANNEX_I_SECTORAL = "annex_i_sectoral_harmonisation"


@dataclass(frozen=True)
class ConformityAssessmentRoute:
    """Detailed specifications for an EU AI Act conformity assessment pathway."""

    id: str
    route_type: ConformityRoute
    governing_articles: tuple[str, ...]
    applicable_annex: str
    requires_notified_body: bool
    description: str
    keywords: tuple[str, ...] = ()


CONFORMITY_ROUTE_REGISTRY: dict[str, ConformityAssessmentRoute] = {
    "annex_vi_internal_control": ConformityAssessmentRoute(
        id="annex_vi_internal_control",
        route_type=ConformityRoute.ANNEX_VI_INTERNAL_CONTROL,
        governing_articles=("Art. 43", "Art. 47", "Art. 48", "Annex VI"),
        applicable_annex="Annex VI",
        requires_notified_body=False,
        description=(
            "Conformity assessment based on internal control (Annex VI). The provider verifies "
            "and documents compliance of the quality management system, technical documentation, "
            "and post-market monitoring without mandatory third-party notified body involvement. "
            "Applies to most Annex III high-risk systems (points 2 through 8), and biometric systems "
            "where harmonised standards are fully applied."
        ),
        keywords=("internal control", "annex vi", "self assessment",
                  "conformity assessment internal", "declaration of conformity"),
    ),
    "annex_vii_notified_body": ConformityAssessmentRoute(
        id="annex_vii_notified_body",
        route_type=ConformityRoute.ANNEX_VII_NOTIFIED_BODY,
        governing_articles=("Art. 43", "Art. 31", "Art. 33", "Art. 34", "Art. 47", "Art. 48", "Annex VII"),
        applicable_annex="Annex VII",
        requires_notified_body=True,
        description=(
            "Conformity assessment based on quality management system assessment and technical "
            "documentation assessment involving a third-party Notified Body (Annex VII). Mandatory "
            "for Annex III(1) biometric systems where harmonised standards do not exist or have "
            "not been fully applied."
        ),
        keywords=("notified body", "annex vii", "third party conformity",
                  "notified body assessment", "notified body audit"),
    ),
    "annex_i_sectoral": ConformityAssessmentRoute(
        id="annex_i_sectoral",
        route_type=ConformityRoute.ANNEX_I_SECTORAL,
        governing_articles=("Art. 6", "Art. 43", "Annex I"),
        applicable_annex="Annex I",
        requires_notified_body=True,
        description=(
            "Conformity assessment for AI systems that are safety components of products covered by "
            "Union harmonisation legislation listed in Annex I (e.g. Medical Devices MDR/IVDR, Machinery, "
            "Civil Aviation, Vehicles). Follows the specific conformity assessment procedures defined "
            "under the corresponding sectoral directive/regulation."
        ),
        keywords=("annex i conformity", "sectoral conformity", "mdr conformity",
                  "machinery directive ai", "medical device ai conformity"),
    ),
}


def resolve_conformity_path(
    category_id: str,
    uses_harmonised_standards: bool = True,
    is_biometric: bool = False,
) -> ConformityRoute:
    """Determine the conformity assessment pathway under Article 43.

    Verified against the pinned CELEX 32024R1689 text:

    * **Art. 43(3)** — a system covered by the Union harmonisation legislation
      in Annex I Section A follows THAT act's procedure (``ANNEX_I_SECTORAL``).
    * **Art. 43(1)** — Annex III **point 1** (biometrics): where harmonised
      standards were applied the provider MAY choose Annex VI or Annex VII;
      where they do not exist or were not applied, Annex VII is MANDATORY.
    * **Art. 43(2)** — Annex III **points 2 to 8**: internal control under
      Annex VI, "which does not provide for the involvement of a notified body".

    ⚠ CORRECTED 2026-08-14. The previous implementation opened with::

        if category_id == "critical_infrastructure" or category_id == "annex_i":
            return ConformityRoute.ANNEX_I_SECTORAL

    ``critical_infrastructure`` is **Annex III point 2**
    (``ANNEX_III_REGISTRY["critical_infrastructure"].number == 2``) — an Annex III
    USE CASE, not an Annex I product-safety case. Article 43(2) names points 2
    to 8 explicitly and rules out a notified body, yet the registry entry this
    returned carries ``requires_notified_body=True``. So the function told a
    critical-infrastructure provider it needed third-party assessment when the
    Act says the opposite: legally inverted, and inverted in the costly
    direction. The confusion is understandable — Annex III(2) is about safety
    components, and so is Annex I — but they are different regimes.

    The route is now derived from ``ANNEX_III_REGISTRY[...].number`` rather than
    a hardcoded id, so adding or renaming a category cannot silently re-route it.
    An Annex I system is signalled by the explicit ``"annex_i"`` id, because it
    is not an Annex III category at all.
    """
    if category_id == "annex_i":
        return ConformityRoute.ANNEX_I_SECTORAL

    category = ANNEX_III_REGISTRY.get(category_id)
    point = category.number if category is not None else None

    # Annex III point 1 — biometrics. Art. 43(1).
    if point == 1 or (point is None and is_biometric):
        if uses_harmonised_standards:
            # The provider MAY opt for either; Annex VI is the lighter default.
            return ConformityRoute.ANNEX_VI_INTERNAL_CONTROL
        return ConformityRoute.ANNEX_VII_NOTIFIED_BODY

    # Annex III points 2-8 — Art. 43(2), internal control, no notified body.
    return ConformityRoute.ANNEX_VI_INTERNAL_CONTROL


# ── Fundamental Rights Impact Assessment (FRIA - Article 27) ─────────────

@dataclass(frozen=True)
class FRIAWorkflow:
    """Six-step procedural FRIA requirements binding deployers under Article 27."""

    id: str
    deployer_category: str
    governing_articles: tuple[str, ...]
    required_steps: tuple[str, ...]
    mandatory_reporting_authority: str
    description: str
    keywords: tuple[str, ...] = ()


FRIA_REGISTRY: dict[str, FRIAWorkflow] = {
    "fria_public_and_essential": FRIAWorkflow(
        id="fria_public_and_essential",
        deployer_category="Public bodies, banking, credit, and life/health insurance deployers",
        governing_articles=("Art. 27", "Art. 26", "Art. 14"),
        required_steps=(
            "1. Description of deployer's processes and intended purpose of high-risk AI use (Art. 27(1)(a))",
            "2. Period of time and operational frequency of high-risk AI system deployment (Art. 27(1)(b))",
            "3. Identification of specific categories of natural persons and vulnerable groups affected (Art. 27(1)(c))",
            "4. Assessment of specific risks of harm to fundamental rights in the concrete context of use (Art. 27(1)(d))",
            "5. Description of human oversight implementation per provider instructions and Article 14 (Art. 27(1)(e))",
            "6. Detailed mitigation measures, internal governance, complaints, and redress mechanisms upon risk materialisation (Art. 27(1)(f))",
        ),
        mandatory_reporting_authority="National Market Surveillance Authority & AI Office",
        description=(
            "Mandatory 6-step Fundamental Rights Impact Assessment under Article 27 that public "
            "authorities and deployers of high-risk AI in banking, creditworthiness, and life/health "
            "insurance must complete and notify prior to putting a high-risk AI system into service."
        ),
        keywords=("fria", "fundamental rights impact assessment", "article 27 fria",
                  "fria steps", "fria deployer", "fria questionnaire"),
    ),
}


# ── Serious Incident Reporting SLAs (Article 73) ─────────────────────────

@dataclass(frozen=True)
class SeriousIncidentSLA:
    """Statutory incident reporting deadlines and triage obligations under Article 73."""

    id: str
    incident_type: str
    deadline_hours: int
    statutory_basis: tuple[str, ...]
    qms_update_required: bool
    description: str
    keywords: tuple[str, ...] = ()


# ⚠ CORRECTED 2026-08-14 — every entry below was wrong, and the errors were
# mutually reinforcing. Verified verbatim against the pinned CELEX 32024R1689
# text via ``app.data.provision_text.get_provision_text("Article 73.N")``:
#
#   73(2)  general — "not later than 15 days"                        -> 360 h
#   73(3)  widespread infringement OR a serious incident as defined
#          in Article 3(49)(b) [irreversible disruption of critical
#          infrastructure] — "not later than two days"               ->  48 h
#   73(4)  death of a person — "not later than 10 days"              -> 240 h
#
# What the previous version asserted, and why each is a hard-rule-#4 breach
# ("KB stubs ship faithful regulatory prose, never speculation — a confidently
# wrong summary loses more than a missing one"):
#
#  1. DEATH carried a 72-hour deadline citing "Article 73(3)". No 72-hour
#     period appears anywhere in Article 73, or anywhere in the Act. 72 hours
#     is the GDPR Article 33 personal-data-breach window — a DIFFERENT
#     instrument. That is cross-regulation contamination stated as AI Act law.
#  2. The death and critical-infrastructure deadlines were SWAPPED: death got
#     the infrastructure paragraph's treatment and infrastructure got 10 days,
#     which is the death deadline. Both were therefore wrong even ignoring (1).
#  3. Every paragraph attribution was shifted by one — 73(3)/(4)/(5) where the
#     Act has 73(4)/(3)/(2). 73(5) is the incomplete-initial-report rule and
#     carries no deadline at all.
#
# The lint floor could not catch any of this: `ARTICLE_EXISTENCE` resolves
# "Art. 73" fine, so the citations were wire-legal while the CONTENT was false
# — exactly the caveat recorded under hard rule #5.
#
# These records are indexed into BM25 by ``kb_search._build_ontology_docs`` and
# seeded into Neo4j as node properties, so a wrong value here propagates into
# retrieval AND outlives the code fix in any graph seeded from it.
SERIOUS_INCIDENT_REGISTRY: dict[str, SeriousIncidentSLA] = {
    "death_of_a_person": SeriousIncidentSLA(
        id="death_of_a_person",
        incident_type="Serious incident resulting in the death of a person",
        deadline_hours=240,  # 10 days — Art. 73(4)
        statutory_basis=("Art. 73", "Art. 72", "Art. 17"),
        qms_update_required=True,
        description=(
            "Under Article 73(4), in the event of the death of a person the report must be provided "
            "immediately after the provider or deployer has established, or as soon as it suspects, a "
            "causal relationship between the high-risk AI system and the serious incident, and in any "
            "event not later than 10 days after the date on which it became aware of the incident."
        ),
        keywords=("death reporting ai", "article 73 death", "incident death 10 days",
                  "fatality incident report", "serious incident death deadline"),
    ),
    "widespread_infringement_or_infrastructure": SeriousIncidentSLA(
        id="widespread_infringement_or_infrastructure",
        incident_type=(
            "Widespread infringement, or a serious and irreversible disruption of the management "
            "or operation of critical infrastructure (Article 3(49)(b))"
        ),
        deadline_hours=48,  # 2 days — Art. 73(3)
        statutory_basis=("Art. 73", "Art. 72", "Art. 17"),
        qms_update_required=True,
        description=(
            "Under Article 73(3), in the event of a widespread infringement or a serious incident as "
            "defined in Article 3, point (49)(b) — a serious and irreversible disruption of the "
            "management or operation of critical infrastructure — the report must be provided "
            "immediately, and not later than two days after the provider or deployer becomes aware "
            "of that incident."
        ),
        keywords=("critical infrastructure incident", "article 73 two days",
                  "widespread infringement reporting", "infrastructure disruption 2 days",
                  "incident 48 hours"),
    ),
    "general_serious_incident": SeriousIncidentSLA(
        id="general_serious_incident",
        incident_type="General serious incident (default reporting deadline)",
        deadline_hours=360,  # 15 days — Art. 73(2)
        statutory_basis=("Art. 73", "Art. 72", "Art. 17"),
        qms_update_required=True,
        description=(
            "Under Article 73(2), the report must be made immediately after the provider has "
            "established a causal link between the AI system and the serious incident, or the "
            "reasonable likelihood of such a link, and in any event not later than 15 days after the "
            "provider or, where applicable, the deployer becomes aware of it. The reporting period "
            "takes account of the severity of the serious incident."
        ),
        keywords=("serious incident 15 days", "incident reporting deadline",
                  "article 73 incident", "fundamental rights breach reporting", "article 73 15 days"),
    ),
}


# ── Cross-entity helpers ─────────────────────────────────────────────────


def practice_for_keyword(keyword: str) -> Practice | None:
    """Return the :class:`Practice` whose ``keywords`` contains ``keyword``.

    Substring-aware case-insensitive match (mirrors the scope filter's
    keyword convention). Returns ``None`` if no Practice matches.
    """
    needle = keyword.lower().strip()
    if not needle:
        return None
    for practice in PRACTICE_REGISTRY.values():
        if any(kw in needle or needle in kw for kw in practice.keywords):
            return practice
    return None


def category_for_keyword(keyword: str) -> AnnexIIICategory | None:
    """Return the :class:`AnnexIIICategory` whose ``keywords`` contains ``keyword``."""
    needle = keyword.lower().strip()
    if not needle:
        return None
    for category in ANNEX_III_REGISTRY.values():
        if any(kw in needle or needle in kw for kw in category.keywords):
            return category
    return None


def all_articles_referenced() -> frozenset[str]:
    """Every Art./Annex referenced anywhere in the ontology.

    Used by :mod:`tests.test_kb_consistency` to verify every reference
    in the typed ontology resolves to a real entry in
    :data:`app.data.article_existence.ARTICLE_EXISTENCE`.
    """
    refs: set[str] = set()
    for practice in PRACTICE_REGISTRY.values():
        refs.update(practice.citation)
        if practice.related_high_risk_anchor:
            refs.add(practice.related_high_risk_anchor)
    for _category in ANNEX_III_REGISTRY.values():
        refs.update({"Annex III", "Art. 6"})
    for phase in PHASE_REGISTRY.values():
        refs.update(phase.articles)
    for scenario in RISK_SCENARIO_REGISTRY.values():
        refs.update(scenario.statutory_violation)
    for control in RISK_CONTROL_REGISTRY.values():
        refs.update(control.articles)
    for gpai in GPAI_REGISTRY.values():
        refs.update(gpai.mandatory_obligations)
    for route in CONFORMITY_ROUTE_REGISTRY.values():
        refs.update(route.governing_articles)
    for fria in FRIA_REGISTRY.values():
        refs.update(fria.governing_articles)
    for incident in SERIOUS_INCIDENT_REGISTRY.values():
        refs.update(incident.statutory_basis)
    return frozenset(refs)



# ── Role → obligation matrix ─────────────────────────────────────────────


# Static role-obligation matrix: which articles bind each operator role
# regardless of system risk class. This is the "you don't need to ask
# what risk class — you're a deployer so Art. 26 always applies to your
# high-risk system uses" lookup. The matrix is intentionally static —
# every entry is grounded in a specific article in the Regulation, so
# the system can answer "I'm an X, what do I owe?" without LLM cost.
ROLE_OBLIGATIONS: dict[ActorRole, dict[RiskClass, tuple[str, ...]]] = {
    ActorRole.PROVIDER: {
        RiskClass.PROHIBITED: (
            "Art. 5",  # Cannot place on market — no obligations, just a ban.
        ),
        # Chapter III Section 2 = Arts. 8–15 (Section-2 requirements:
        # risk management, data governance, technical documentation,
        # record-keeping/logging, transparency, human oversight,
        # accuracy/robustness/cybersecurity). Art. 12 (record-keeping)
        # was previously missing from this list — fixed in the May 2026
        # ontology review per the senior-engineer audit.
        RiskClass.HIGH_RISK_ANNEX_I: (
            "Art. 6", "Art. 8", "Art. 9", "Art. 10", "Art. 11", "Art. 12",
            "Art. 13", "Art. 14", "Art. 15", "Art. 16", "Art. 17",
            "Art. 43", "Art. 47", "Art. 48", "Art. 49", "Art. 72",
            "Annex I", "Annex IV", "Annex VI",
        ),
        RiskClass.HIGH_RISK_ANNEX_III: (
            "Art. 6", "Art. 8", "Art. 9", "Art. 10", "Art. 11", "Art. 12",
            "Art. 13", "Art. 14", "Art. 15", "Art. 16", "Art. 17",
            "Art. 43", "Art. 47", "Art. 48", "Art. 49", "Art. 72",
            "Annex III", "Annex IV", "Annex VI",
        ),
        RiskClass.LIMITED_RISK: (
            "Art. 50",  # Transparency obligations only
        ),
        RiskClass.MINIMAL_RISK: (
            "Art. 4",  # AI literacy
        ),
        # GPAI provider obligations are Art. 53 (technical documentation
        # + downstream-provider info + copyright policy + training-data
        # summary) plus Annex XI / XII content schemas. Art. 54 is the
        # AUTHORISED-REPRESENTATIVE article for GPAI providers in third
        # countries — it does NOT bind GPAI providers in general. The
        # May 2026 audit caught Art. 54 incorrectly listed here; moved
        # to AUTHORISED_REPRESENTATIVE × GPAI where it correctly sits.
        RiskClass.GPAI: (
            "Art. 53",
            "Annex XI", "Annex XII",  # Technical doc + downstream-provider info
        ),
        # Art. 56 is "Codes of practice" — the AI OFFICE's facilitation duty,
        # not an obligation on providers (R371.6 audit). Art. 55 is the
        # systemic-risk provider obligation.
        RiskClass.GPAI_SYSTEMIC: (
            "Art. 53", "Art. 55",
            "Annex XI", "Annex XII", "Annex XIII",
        ),
    },
    ActorRole.DEPLOYER: {
        RiskClass.PROHIBITED: ("Art. 5",),
        # Annex I (safety-component) deployers DON'T owe Art. 27 FRIA —
        # Art. 27(1) limits the FRIA obligation to deployers of certain
        # Annex III high-risk systems (public-sector + Annex III(5)(a)/(b)
        # selected categories). Annex I medical-device deployers operate
        # under MDR/IVDR oversight, not the FRIA regime. Fixed in the
        # May 2026 ontology audit.
        # Art. 13 (transparency + instructions for use) is a PROVIDER duty;
        # the deployer's mirror obligation is Art. 26(1) (use in accordance
        # with the instructions). R371.6 audit removed it from the deployer
        # sets — the live deontic block already labels it "Provider (primary),
        # Deployer (secondary)", so the matrix contradicted the graph.
        # Art. 86 (right to explanation) sits only under ANNEX_III: Art.
        # 86(1) limits the explanation duty to Annex III systems (excluding
        # point 2).
        RiskClass.HIGH_RISK_ANNEX_I: (
            "Art. 26",  # General deployer obligations
        ),
        RiskClass.HIGH_RISK_ANNEX_III: (
            "Art. 26", "Art. 27", "Art. 86",  # right to explanation (deployer duty)
        ),
        RiskClass.LIMITED_RISK: ("Art. 50",),
        RiskClass.MINIMAL_RISK: ("Art. 4",),
        RiskClass.GPAI: (),  # Deployer obligations attach to the AI SYSTEM, not the model
        RiskClass.GPAI_SYSTEMIC: (),
    },
    ActorRole.IMPORTER: {
        RiskClass.PROHIBITED: ("Art. 5",),
        RiskClass.HIGH_RISK_ANNEX_I: ("Art. 23",),
        RiskClass.HIGH_RISK_ANNEX_III: ("Art. 23",),
        # Art. 23 importer duties apply to HIGH-RISK systems only (Art. 23(1)
        # "Before placing a high-risk AI system on the market..."); there is no
        # importer obligation at limited risk. R371.6 audit removed the
        # limited-risk binding.
        RiskClass.LIMITED_RISK: (),
        RiskClass.MINIMAL_RISK: (),
        RiskClass.GPAI: (),
        RiskClass.GPAI_SYSTEMIC: (),
    },
    ActorRole.DISTRIBUTOR: {
        RiskClass.PROHIBITED: ("Art. 5",),
        RiskClass.HIGH_RISK_ANNEX_I: ("Art. 24",),
        RiskClass.HIGH_RISK_ANNEX_III: ("Art. 24",),
        # Art. 24 distributor duties apply to HIGH-RISK systems only (Art.
        # 24(1) "Before making a high-risk AI system available on the
        # market..."). R371.6 audit removed the limited-risk binding.
        RiskClass.LIMITED_RISK: (),
        RiskClass.MINIMAL_RISK: (),
        RiskClass.GPAI: (),
        RiskClass.GPAI_SYSTEMIC: (),
    },
    ActorRole.AUTHORISED_REPRESENTATIVE: {
        RiskClass.HIGH_RISK_ANNEX_I: ("Art. 22",),
        RiskClass.HIGH_RISK_ANNEX_III: ("Art. 22",),
        RiskClass.GPAI: ("Art. 54",),
        RiskClass.GPAI_SYSTEMIC: ("Art. 54",),
    },
    # Downstream providers (Art. 3(2)) hold no Chapter V obligations qua
    # downstream provider: Art. 53/Annex XII are the GPAI MODEL provider's
    # supply duties (Art. 53(1)(b)), Art. 55 binds the systemic-risk model
    # provider, and Art. 89 is the AI Office's monitoring duty (downstream
    # providers merely hold a complaint RIGHT under Art. 89(2)). R371.6
    # audit removed all four bindings — the matrix renders "binds the
    # downstream provider", which was direction-inverted.
    ActorRole.DOWNSTREAM_PROVIDER: {
        RiskClass.GPAI: (),
        RiskClass.GPAI_SYSTEMIC: (),
    },
    # Notified-body obligations live across Arts. 31 (notification),
    # 33 (requirements relating to notified bodies), and 34 (operational
    # obligations of notified bodies), with conformity-assessment
    # procedures referenced through Annex VII. The May 2026 audit
    # caught the earlier "Art. 29" entry — that's actually a deployer
    # article in the AI Act, not notified-body.
    ActorRole.NOTIFIED_BODY: {
        RiskClass.HIGH_RISK_ANNEX_I: ("Art. 31", "Art. 33", "Art. 34", "Annex VII"),
        RiskClass.HIGH_RISK_ANNEX_III: ("Art. 31", "Art. 33", "Art. 34", "Annex VII"),
    },
    # Art. 85 (right to lodge a complaint) and Art. 86 (right to explanation)
    # are RIGHTS of the affected person, not obligations ON them — the matrix
    # renders "binds the affected person", which is direction-inverted. The
    # explanation DUTY sits on the deployer (Art. 86(1), already bound under
    # DEPLOYER x HIGH_RISK_ANNEX_III). R371.6 audit emptied this role.
    ActorRole.AFFECTED_PERSON: {
        RiskClass.HIGH_RISK_ANNEX_III: (),
        RiskClass.HIGH_RISK_ANNEX_I: (),
    },
}


def obligations_for(role: ActorRole, risk_class: RiskClass) -> tuple[str, ...]:
    """Return the article/annex references that bind ``role`` when handling
    a system of ``risk_class``.

    Returns an empty tuple when the combination is structurally empty
    (e.g. deployer of GPAI — deployer obligations attach to the AI
    *system* built on top, not the underlying model).
    """
    return ROLE_OBLIGATIONS.get(role, {}).get(risk_class, ())


def validate_legal_triple(
    article: str, role: ActorRole, risk_class: RiskClass
) -> bool:
    """Return True iff ``(article, role, risk_class)`` is a LEGAL triple.

    R138 — the ontology-constraint validation predicate the "semantic
    layer" post calls for ("a triple that violates the schema is caught
    before it reaches the LLM"). A triple is legal iff ``article`` is in
    the obligation set the ontology binds to ``(role, risk_class)``.

    This is the queryable form of :func:`obligations_for`. Its main job is
    as a CI guardrail (see ``tests/test_kb_consistency.py``): it lets a
    lint assert that no provider-only duty (conformity assessment Art. 43,
    EU declaration Art. 47, CE marking Art. 48) is cross-wired onto a
    non-provider role, and that the GPAI authorised-representative article
    (Art. 54) sits only under :data:`ActorRole.AUTHORISED_REPRESENTATIVE`
    — the exact class of silent bug the May-2026 ontology audit caught by
    hand. Pure lookup; never raises.
    """
    return article in ROLE_OBLIGATIONS.get(role, {}).get(risk_class, ())


# ── R371.3 — requirement-name → article anchors (retrieval-facing) ───────


#: Narrow, unambiguous Chapter-III requirement-name anchors for the R329
#: citable-universe seed. Values are WIRE form ("Article N" / "Annex X",
#: hard rule #1).
#:
#: These are DELIBERATELY narrow — the general ``KEYWORD_TO_ARTICLE`` map
#: (app/integrations/regenold/scope.py) measures only 7% gold precision as a
#: citable-universe seed over the 297-row probe pool (Art. 6 / 50 / 5 / 53 /
#: 43 fire on questions whose gold cites the answer list, not the rule), so
#: blindly unioning it would re-open the over-citation hole R329 closed.
#: This set is the measured exception: requirement NAMES that map 1:1 to the
#: article that imposes them. Measured R352-doctrine (offline, before any
#: engine change): 41 anchors fired over 36/297 rows, **38 gold, 3 contextual
#: misses, 93% precision** — the three misses are conformity-route
#: classification questions where the gold cites Art. 6/Annex I (the route)
#: rather than Art. 43 (the general procedure); as a PERMISSION SET the model
#: still only cites what its prose discusses.
REQUIREMENT_ARTICLE_ANCHORS: dict[str, str] = {
    "quality management system": "Article 17",
    "quality management": "Article 17",
    "technical documentation": "Article 11",
    "record-keeping": "Article 12",
    "record keeping": "Article 12",
    "human oversight": "Article 14",
    "risk management system": "Article 9",
    "risk management": "Article 9",
    "data governance": "Article 10",
    "conformity assessment": "Article 43",
    "post-market monitoring": "Article 72",
    "post market monitoring": "Article 72",
    "serious incident": "Article 73",
    "fundamental rights impact assessment": "Article 27",
    "fria": "Article 27",
    "eu declaration of conformity": "Article 47",
    "transparency to deployers": "Article 13",
    "accuracy robustness": "Article 15",
    "robustness accuracy": "Article 15",
    "cybersecurity": "Article 15",
}


# ── Public API ───────────────────────────────────────────────────────────


__all__ = [
    # Enums
    "ActorRole",
    "RiskClass",
    "ConformityRoute",
    # Dataclasses
    "Practice",
    "AnnexIIICategory",
    "Phase",
    "RiskScenario",
    "RiskControl",
    "GPAIModelProfile",
    "ConformityAssessmentRoute",
    "FRIAWorkflow",
    "SeriousIncidentSLA",
    # Registries
    "PRACTICE_REGISTRY",
    "ANNEX_III_REGISTRY",
    "PHASE_REGISTRY",
    "ROLE_OBLIGATIONS",
    "REQUIREMENT_ARTICLE_ANCHORS",
    "RISK_SCENARIO_REGISTRY",
    "RISK_CONTROL_REGISTRY",
    "GPAI_REGISTRY",
    "CONFORMITY_ROUTE_REGISTRY",
    "FRIA_REGISTRY",
    "SERIOUS_INCIDENT_REGISTRY",
    # Helpers
    "practice_for_keyword",
    "category_for_keyword",
    "all_articles_referenced",
    "obligations_for",
    "validate_legal_triple",
    "resolve_conformity_path",
]

