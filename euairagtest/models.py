"""Structure-preserving chunk model for the EU AI Act corpus (plan §3).

``Provision`` is the normalized unit written to Parquet/JSON in Phase 1 and later
indexed (vector store) and mirrored into the knowledge graph. ``provision_id`` is
the single source of truth: the citation, ELI anchor, and every structural field
(article/paragraph/point/…) are derived from it so a row can never disagree with
its own ID.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .ids import ProvisionId

__all__ = ["Provision"]


class Provision(BaseModel):
    """One citable provision (article, paragraph, point, recital, annex item, …)."""

    model_config = ConfigDict(extra="forbid")

    # --- identity (source of truth) ---
    provision_id: str
    chunk_type: str
    text: str

    # --- derived from provision_id (filled by the validator; do not set by hand) ---
    citation: str = ""
    eli_uri: str = ""
    root_kind: str = ""
    parent_id: str | None = None
    article: int | None = None
    paragraph: int | None = None
    point: str | None = None
    subpoint: str | None = None
    annex: str | None = None
    annex_point: int | None = None
    recital: int | None = None

    # --- container context not encoded in the leaf id ---
    chapter: int | None = None
    section: str | None = None
    parent_text: str | None = None

    # --- semantics / cross-references ---
    defined_terms: list[str] = Field(default_factory=list)
    references_internal: list[str] = Field(default_factory=list)  # eids
    references_external: list[str] = Field(default_factory=list)  # e.g. 32016R0679__art_6
    interprets_articles: list[str] = Field(default_factory=list)

    # --- provenance / temporal ---
    effective_from: date | None = None
    transitional: bool = False
    celex: str = "32024R1689"
    lang: str = "en"
    source_url: str | None = None

    @model_validator(mode="after")
    def _derive_from_id(self) -> "Provision":
        pid = ProvisionId.from_eid(self.provision_id)  # raises on malformed ids
        # provision_id is the single source of truth: derive citation/eli_uri
        # unconditionally so a hand-set value can never disagree with the id
        # (matches every other derived field below).
        self.citation = pid.citation
        self.eli_uri = pid.eli_uri
        self.root_kind = pid.root_kind
        self.article = pid.article
        self.paragraph = pid.paragraph
        self.point = pid.point
        self.subpoint = pid.subpoint
        self.annex = pid.annex
        self.annex_point = pid.annex_point
        self.recital = pid.recital
        if self.parent_id is None:
            parent = pid.parent()
            self.parent_id = parent.eid if parent is not None else None
        return self

    def to_row(self) -> dict:
        """Flat, columnar-friendly dict for Parquet/JSON output."""
        d = self.model_dump()
        if self.effective_from is not None:
            d["effective_from"] = self.effective_from.isoformat()
        return d
