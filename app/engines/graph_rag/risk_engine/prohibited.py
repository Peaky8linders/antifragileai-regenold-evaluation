"""Prohibited Practices (Article 5) risk rules and inquiry detection."""

from __future__ import annotations

import re


def is_prohibited_inquiry(question: str) -> bool:
    """Detect if a question is asking about Article 5 Prohibited Practices."""
    q_low = question.lower()
    patterns = [
        r"prohibited\s+practice",
        r"article\s+5\b",
        r"social\s+scor",
        r"subliminal",
        r"biometric\s+categoris",
        r"biometric\s+categoriz",
        r"untargeted\s+scrap",
        r"emotion\s+recognit",
        r"real-time\s+remote\s+biometric",
        r"predictive\s+polic",
        r"criminal\s+risk",
        r"vulnerab.*exploit",
    ]
    return any(re.search(p, q_low) for p in patterns)
