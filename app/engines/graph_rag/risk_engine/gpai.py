"""General Purpose AI (Arts. 51-56, Annex XI-XIII) risk rules."""

from __future__ import annotations


def is_gpai_inquiry(question: str) -> bool:
    """Detect if question relates to GPAI models or systemic risk thresholds."""
    q_low = question.lower()
    keywords = ("gpai", "general purpose ai", "general-purpose ai", "systemic risk", "10^25", "10²⁵", "flops")
    return any(kw in q_low for kw in keywords)

