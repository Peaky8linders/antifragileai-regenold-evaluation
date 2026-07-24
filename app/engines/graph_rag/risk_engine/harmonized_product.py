"""Article 6(1) Harmonized Product Safety (MDR/IVDR, SaMD, Annex I) risk rules."""

from __future__ import annotations

import re


def is_harmonized_product_inquiry(question: str) -> bool:
    """Detect if a question relates to Art 6(1) / Annex I harmonized product safety rules."""
    q_low = question.lower()
    keywords = (
        "annex i", "article 6(1)", "article 6.1", "mdr", "ivdr",
        "medical device", "samd", "safety component", "ce marking", "ce-marking"
    )
    return any(kw in q_low for kw in keywords)
