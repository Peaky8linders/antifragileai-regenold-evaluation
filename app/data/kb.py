"""Knowledge-base stub — only what the Regenold + Graph-RAG path needs.

The full CodexAI KB ships 24 compliance dimensions × 139 questions plus
risk-level mappings, dimension crosswalks, and an EC-Checker obligation
map. This bundle ships just enough scaffolding for ``graph_rag.py``'s
KB-fallback path to resolve cleanly.

If a partner wants to exercise the full graph-projection path they
should restore CodexAI's full KB module (and the Neo4j client).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Version pin surfaced on every Regenold response (telemetry mode).
KB_VERSION = "2024.1689.v2"


@dataclass(frozen=True)
class MaturityDimension:
    """A compliance dimension. Stubbed shape — only ``id`` / ``label`` /
    ``questions`` are read by the graph-RAG engine."""

    id: str
    label: str
    questions: tuple[str, ...] = field(default_factory=tuple)


# Minimal 4-dimension set covering the dimensions the engine surfaces
# when the question doesn't carry an explicit article anchor. This is a
# DELIBERATE skeleton — the engine's deterministic-fallback prose only
# names dimensions in the closed-world refusal branch.
MATURITY_DIMENSIONS: tuple[MaturityDimension, ...] = (
    MaturityDimension(
        id="risk_mgmt",
        label="Risk management system (Art. 9)",
        questions=("Risk management process established?", "Foreseeable misuse mapped?"),
    ),
    MaturityDimension(
        id="data_gov",
        label="Data governance (Art. 10)",
        questions=("Training data provenance recorded?", "Bias examination performed?"),
    ),
    MaturityDimension(
        id="tech_docs",
        label="Technical documentation (Art. 11 + Annex IV)",
        questions=("Annex IV pack drafted?", "Documentation kept up to date?"),
    ),
    MaturityDimension(
        id="transparency",
        label="Transparency to deployers (Art. 13)",
        questions=("Instructions for use shipped?", "Capabilities + limitations documented?"),
    ),
)


def get_dimensions_for_risk_level(risk_level: str | None) -> tuple[MaturityDimension, ...]:
    """Return dimensions in scope for ``risk_level``.

    The minimal bundle returns the full 4-dimension stub for every risk
    level. The full CodexAI implementation maps each level to a subset.
    """
    if risk_level not in {"high", "limited", "minimal", "unacceptable", None}:
        raise ValueError(f"Unknown risk level: {risk_level!r}")
    return MATURITY_DIMENSIONS


# EC-Checker → KB-dimension surface. Used by the engine when a question
# explicitly mentions an Art. ref so it can look up a synthetic
# obligation row. The bundle ships minimal entries for the 12 most-cited
# high-risk articles so the deterministic-fallback path produces a
# tight answer instead of dumping the dimension catalog. Full CodexAI
# coverage is 113 articles × per-paragraph rows.
EC_CHECKER_OBLIGATION_MAP: dict[str, dict[str, str]] = {
    "Art. 5": {
        "dimension": "risk_mgmt",
        "summary": (
            "Prohibits eight categories of AI practice (subliminal manipulation, "
            "exploitation of vulnerabilities, social scoring, predictive policing of "
            "individuals, untargeted facial-image scraping, emotion recognition in "
            "workplaces and education, biometric categorisation by protected "
            "attribute, and real-time remote biometric identification in public spaces)."
        ),
    },
    "Art. 6": {
        "dimension": "risk_mgmt",
        "summary": (
            "Classifies an AI system as high-risk when it is intended as a safety "
            "component of a product covered by Annex I, or falls into one of the "
            "eight Annex III use cases."
        ),
    },
    "Art. 9": {
        "dimension": "risk_mgmt",
        "summary": (
            "Requires a documented, iterative risk-management system across the AI "
            "system's lifecycle covering known + foreseeable risks, residual-risk "
            "acceptability, and targeted testing for risk-control verification."
        ),
    },
    "Art. 10": {
        "dimension": "data_gov",
        "summary": (
            "Requires training, validation, and test datasets to be relevant, "
            "representative, free of errors, and complete; covers data-governance "
            "practices including provenance, preparation, bias examination + "
            "mitigation, and special-category personal data handling."
        ),
    },
    "Art. 11": {
        "dimension": "tech_docs",
        "summary": (
            "Requires technical documentation drawn up before placement on the "
            "market, kept up to date, demonstrating conformity to the essential "
            "requirements, with content per Annex IV. SMEs may use the simplified "
            "form supplied by the Commission."
        ),
    },
    "Art. 12": {
        "dimension": "tech_docs",
        "summary": (
            "Requires automatic logs of events relevant to identifying risks, "
            "post-market monitoring, and substantial modifications — retained at "
            "minimum 6 months."
        ),
    },
    "Art. 13": {
        "dimension": "transparency",
        "summary": (
            "Requires high-risk AI systems to be designed for sufficient operational "
            "transparency to deployers, accompanied by instructions for use covering "
            "provider identity, intended purpose, capabilities + limitations, "
            "expected lifetime, human-oversight measures, and required maintenance."
        ),
    },
    "Art. 14": {
        "dimension": "transparency",
        "summary": (
            "Requires effective human oversight by natural persons during system use "
            "— capability + limitation awareness, automation-bias safeguards, ability "
            "to interpret output, disregard / override / intervene, and (for biometric "
            "identification) a two-person verification rule."
        ),
    },
    "Art. 15": {
        "dimension": "risk_mgmt",
        "summary": (
            "Requires appropriate levels of accuracy, robustness, and cybersecurity "
            "across the lifecycle — accuracy metrics declared in instructions for "
            "use, resilience against errors, and resistance to data-poisoning, "
            "evasion, model-confidentiality, and adversarial attacks."
        ),
    },
    "Art. 17": {
        "dimension": "tech_docs",
        "summary": (
            "Requires providers of high-risk AI systems to operate a quality "
            "management system covering regulatory-compliance strategy, design "
            "verification, examination + test procedures, post-market monitoring, "
            "and incident-reporting workflows."
        ),
    },
    "Art. 26": {
        "dimension": "transparency",
        "summary": (
            "Deployer obligations: use the system per the instructions, assign "
            "human oversight to competent + trained natural persons, monitor "
            "operation, retain automatically generated logs, inform affected workers "
            "(for workplace use), and cooperate with market-surveillance authorities."
        ),
    },
    "Art. 27": {
        "dimension": "transparency",
        "summary": (
            "Deployers of certain high-risk AI systems (Annex III + public-sector "
            "deployers) must perform a Fundamental Rights Impact Assessment before "
            "first use, covering deployment process, affected persons, specific risks, "
            "human-oversight measures, and complaints workflows."
        ),
    },
    "Art. 50": {
        "dimension": "transparency",
        "summary": (
            "Transparency obligations: AI systems interacting with natural persons "
            "must disclose their AI nature; emotion-recognition + biometric-"
            "categorisation systems must inform exposed persons; deepfakes and "
            "AI-generated content must be labelled."
        ),
    },
    "Art. 53": {
        "dimension": "tech_docs",
        "summary": (
            "GPAI provider obligations: maintain technical documentation per "
            "Annex XI, supply downstream-provider information per Annex XII, "
            "implement a copyright policy, and publish a sufficiently detailed "
            "training-data summary."
        ),
    },
    "Art. 55": {
        "dimension": "risk_mgmt",
        "summary": (
            "GPAI systemic-risk provider obligations: model evaluation including "
            "adversarial testing, systemic-risk assessment + mitigation, serious-"
            "incident reporting to the AI Office, and adequate cybersecurity."
        ),
    },
    "Art. 72": {
        "dimension": "tech_docs",
        "summary": (
            "Requires a post-market monitoring plan + system documenting AI-system "
            "performance throughout its lifetime, with data collection, analysis, "
            "corrective-action workflows, and feedback into the risk-management "
            "system."
        ),
    },
    "Art. 99": {
        "dimension": "risk_mgmt",
        "summary": (
            "Penalty regime: up to EUR 35M or 7% of worldwide annual turnover for "
            "Article 5 prohibited-practice violations; up to EUR 15M / 3% for other "
            "obligations breaches; up to EUR 7.5M / 1% for incorrect or misleading "
            "information to authorities."
        ),
    },
    "Annex IV": {
        "dimension": "tech_docs",
        "summary": (
            "Technical documentation contents covering system description, design "
            "specifications, system architecture, data + training methodology, "
            "human oversight, risk-management measures, validation + testing "
            "procedures, and post-market monitoring system."
        ),
    },
    "Annex III": {
        "dimension": "risk_mgmt",
        "summary": (
            "Eight high-risk use-case categories: biometrics, critical infrastructure, "
            "education + vocational training, employment + worker management, "
            "essential private + public services, law enforcement, migration + asylum "
            "+ border control, and administration of justice + democratic processes."
        ),
    },
}
