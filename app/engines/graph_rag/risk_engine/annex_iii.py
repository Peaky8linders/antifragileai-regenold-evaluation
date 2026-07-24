"""Annex III High-Risk Categories (Article 6(2)) risk rules."""

from __future__ import annotations


def is_annex_iii_inquiry(question: str) -> bool:
    """Detect if a question relates to Annex III high-risk use cases."""
    q_low = question.lower()
    keywords = (
        "annex iii", "high risk", "high-risk", "article 6(2)", "article 6.2",
        "triage", "biometric identification", "critical infrastructure", "employment",
        "recruitment", "cv screening", "education grading", "student assessment",
        "credit scoring", "creditworthiness", "insurance pricing", "law enforcement",
        "migration", "asylum", "border control", "judicial", "assist judges"
    )
    return any(kw in q_low for kw in keywords)
