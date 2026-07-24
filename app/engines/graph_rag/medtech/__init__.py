"""MedTech & Life Sciences regulatory extension sub-package."""

from app.engines.graph_rag.medtech.standards_map import MEDTECH_STANDARD_MAP
from app.engines.graph_rag.medtech.samd_rules import is_medtech_inquiry

__all__ = [
    "MEDTECH_STANDARD_MAP",
    "is_medtech_inquiry",
]
