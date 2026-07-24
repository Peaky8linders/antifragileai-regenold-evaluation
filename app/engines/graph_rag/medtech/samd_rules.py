"""Software as a Medical Device (SaMD) and IVD regulatory rules."""

from __future__ import annotations

import re


def is_medtech_inquiry(question: str) -> bool:
    """Detect if question relates to medical devices, SaMD, IVD, or clinical software."""
    q_low = question.lower()
    keywords = (
        "medical", "samd", "surgery", "patient", "diagnostic", "ivd",
        "hospital", "clinical", "oncology", "triage", "in vitro"
    )
    return any(kw in q_low for kw in keywords)
