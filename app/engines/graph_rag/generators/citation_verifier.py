"""Citation verification and extraction helper for Graph RAG Engine."""

from __future__ import annotations

import re
from app.models import CitationNode
from app.engines.graph_rag.models import GraphContext


def _format_article_ref(raw_art: str) -> str:
    if not raw_art:
        return ""
    raw_art = raw_art.strip()
    if raw_art.isdigit() or re.match(r"^\d+([.(]\d+)*\)?$", raw_art):
        return f"Article {raw_art}"
    if raw_art.startswith("Art. "):
        return raw_art.replace("Art. ", "Article ")
    if raw_art.startswith("Art "):
        return raw_art.replace("Art ", "Article ")
    return raw_art


def extract_citations(context: GraphContext) -> list[CitationNode]:
    """Extract and deduplicate citation nodes from context obligations and gaps."""
    citations: list[CitationNode] = []
    seen_ids: set[str] = set()

    obls = (getattr(context, "obligations", None) or []) + (getattr(context, "article_info", None) or [])
    _obl_slot_cap = 15
    for obl in obls:
        if len(citations) >= _obl_slot_cap:
            break
        if not isinstance(obl, dict):
            continue
        oid = (
            obl.get("id")
            or obl.get("obligation_id")
            or (f"{obl.get('article')}:{obl.get('text', '')[:30]}" if obl.get("article") else obl.get("text", "")[:30])
        )
        if oid and oid not in seen_ids:
            seen_ids.add(oid)
            raw_art = _format_article_ref(str(obl.get("article", "") or ""))
            citations.append(CitationNode(
                node_type="Obligation",
                node_id=oid,
                text=obl.get("text", ""),
                article_ref=raw_art,
            ))

    gaps = getattr(context, "gaps", None) or []
    _gap_slot_cap = 10
    _gap_added = 0
    for gap in gaps:
        if _gap_added >= _gap_slot_cap:
            break
        if not isinstance(gap, dict):
            continue
        gid = (
            gap.get("id")
            or gap.get("obligation_id")
            or (f"{gap.get('article')}:{gap.get('text', '')[:30]}" if gap.get("article") else gap.get("text", "")[:30])
        )
        if gid and gid not in seen_ids:
            seen_ids.add(gid)
            raw_art = _format_article_ref(str(gap.get("article", "") or ""))
            citations.append(CitationNode(
                node_type="Gap",
                node_id=gid,
                text=gap.get("text", ""),
                article_ref=raw_art,
            ))
            _gap_added += 1

    return citations

