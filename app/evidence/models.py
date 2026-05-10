"""Evidence-chain entry-type catalog (minimal).

The full CodexAI catalog covers ~50 entry types across the platform.
This bundle ships only the entry the Regenold route writes.
"""
from __future__ import annotations

from enum import Enum


class EvidenceEntryType(str, Enum):
    regenold_question = "regenold_question"
