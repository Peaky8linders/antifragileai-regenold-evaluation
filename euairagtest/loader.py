"""Load the EU AI Act corpus into normalized ``Provision`` objects.

Primary source is the Hugging Face dataset ``jeroenherczeg/eu-ai-act`` (plan §3:
verified, 2,607 rows, CC BY 4.0). Its ``structure_path`` uses ``/`` + ``:`` (e.g.
``art:6/par:2``), which we transform into our canonical eid (``art_6__para_2``).

The dataset is granular only to the paragraph / annex-item level, so after mapping
rows we optionally expand paragraphs and annex items into their point / sub-point
children (see ``euaiact.ingest.points``) to reach citation grain.

Heavy dependencies (polars / datasets) are imported lazily so the pure transform
functions — and their tests — run with zero ML/network dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..ids import CELEX
from ..models import Provision
from .points import split_annex_item, split_definitions, split_paragraph

__all__ = [
    "structure_path_to_eid",
    "row_to_provision",
    "load_rows",
    "load_provisions",
    "IngestResult",
    "DEFAULT_HF_GLOB",
]

DEFAULT_HF_GLOB = "hf://datasets/jeroenherczeg/eu-ai-act/**/*.parquet"

# structure_path tag  ->  our eid segment kind
_TAG_MAP = {"art": "art", "par": "para", "anx": "annex", "sec": "point", "rec": "recital"}
# candidate column names for the provision text
_TEXT_KEYS = ("text", "content", "chunk_text", "chunk", "body")


class UnmappableRow(ValueError):
    """A dataset row cannot be deterministically mapped to a provision id."""


def structure_path_to_eid(structure_path: str) -> str:
    """``art:6/par:2`` -> ``art_6__para_2``; ``anx:III/sec:3`` -> ``annex_III__point_3``."""
    if not structure_path or not structure_path.strip():
        raise UnmappableRow("empty structure_path")
    if "?" in structure_path:
        raise UnmappableRow(f"unparsed marker in structure_path: {structure_path!r}")
    parts: list[str] = []
    for seg in structure_path.strip().split("/"):
        tag, sep, num = seg.partition(":")
        if not sep or tag not in _TAG_MAP or not num:
            raise UnmappableRow(f"unrecognised structure_path segment: {seg!r}")
        parts.append(f"{_TAG_MAP[tag]}_{num}")
    return "__".join(parts)


def _as_int(v: object) -> int | None:
    if v is None:
        return None
    s = str(v).strip()
    return int(s) if s.isdigit() else None


def _as_list(v: object) -> list[str]:
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    s = str(v).strip()
    return [s] if s else []


def _pick_text(row: dict) -> str:
    for k in _TEXT_KEYS:
        if row.get(k):
            return str(row[k])
    raise UnmappableRow(f"no text column found (tried {_TEXT_KEYS})")


def _parse_date(v: object) -> date | None:
    if not v:
        return None
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _articles_to_eids(v: object) -> list[str]:
    out: list[str] = []
    for a in _as_list(v):
        num = a.strip()
        out.append(f"art_{num}" if num.isdigit() else num)
    return out


def _lang_from_row(row: dict) -> str:
    lang = row.get("lang") or row.get("language")
    if lang:
        return str(lang)
    rid = str(row.get("id", ""))
    if "-" in rid and rid.rsplit("-", 1)[-1] in {"en", "nl", "fr", "de"}:
        return rid.rsplit("-", 1)[-1]
    return "en"


def row_to_provision(row: dict) -> Provision:
    """Map one raw dataset row to a Provision. Raises UnmappableRow if it can't."""
    eid = structure_path_to_eid(str(row.get("structure_path", "")))
    return Provision(
        provision_id=eid,
        chunk_type=str(row.get("chunk_type", "")) or "unknown",
        text=_pick_text(row),
        chapter=_as_int(row.get("chapter_no")),
        section=str(row["section_no"]).strip() if row.get("section_no") else None,
        defined_terms=_as_list(row.get("defined_terms")),
        references_internal=_articles_to_eids(row.get("references_articles")),
        interprets_articles=_articles_to_eids(row.get("interprets_articles")),
        effective_from=_parse_date(row.get("effective_from")),
        transitional=bool(row.get("transitional")),
        celex=str(row.get("celex") or CELEX),
        lang=_lang_from_row(row),
        source_url=str(row["source_url"]) if row.get("source_url") else None,
    )


@dataclass
class IngestResult:
    """Outcome of an ingestion run."""

    provisions: list[Provision] = field(default_factory=list)
    unmapped: list[tuple[str, str]] = field(default_factory=list)  # (structure_path, reason)

    @property
    def counts(self) -> dict[str, int]:
        by_kind: dict[str, int] = {}
        for p in self.provisions:
            by_kind[p.chunk_type] = by_kind.get(p.chunk_type, 0) + 1
        return by_kind


def load_rows(source: str | None = None) -> list[dict]:
    """Read raw rows from a parquet/json path, an ``hf://`` glob, or the default HF dataset.

    Lazily imports polars. Raises a clear RuntimeError if the source is unreachable
    (e.g. offline / sandbox TLS), so callers can fall back to a local cache.
    """
    src = source or DEFAULT_HF_GLOB
    if src.endswith((".json", ".jsonl")):
        import json

        with open(src) as fh:
            data = json.load(fh) if src.endswith(".json") else [json.loads(li) for li in fh]
        return data if isinstance(data, list) else data.get("rows", data.get("items", []))

    try:
        import polars as pl
    except ModuleNotFoundError as e:  # pragma: no cover - env dependent
        raise RuntimeError(
            "polars is required to read parquet/hf sources. Install with "
            "`uv sync --extra hf` (or `uv pip install polars`)."
        ) from e
    try:
        return pl.read_parquet(src).to_dicts()
    except Exception as e:  # noqa: BLE001 - surface any IO/TLS error as actionable
        raise RuntimeError(
            f"could not read {src!r}: {e}. If offline/sandboxed, download the parquet "
            f"once and pass a local path, e.g. load_provisions('data/eu-ai-act.parquet')."
        ) from e


def load_provisions(
    source: str | None = None, *, expand_points: bool = True, lang: str | None = "en"
) -> IngestResult:
    """Full Phase-1 ingestion: rows -> provisions (+ optional point/sub-point expansion).

    ``lang`` filters to a single language (default English) — the HF dataset ships EN/NL/FR
    rows that share the same ``structure_path``, so without a filter every provision id
    collides across languages and node text becomes last-writer-wins. Pass ``lang=None`` to
    keep every language.
    """
    result = IngestResult()
    for row in load_rows(source):
        if lang is not None and _lang_from_row(row) != lang:
            continue
        try:
            prov = row_to_provision(row)
        except (UnmappableRow, ValueError) as e:
            result.unmapped.append((str(row.get("structure_path", "?")), str(e)))
            continue
        result.provisions.append(prov)
        if expand_points:
            is_paragraph = prov.paragraph is not None and prov.point is None
            if prov.chunk_type == "paragraph" or is_paragraph:
                result.provisions.extend(split_paragraph(prov))
            elif prov.chunk_type == "annex_item" or prov.annex_point is not None:
                result.provisions.extend(split_annex_item(prov))
            elif prov.chunk_type == "article_full":
                result.provisions.extend(split_definitions(prov))
    return result
