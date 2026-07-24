"""Citation verification and extraction helper for Graph RAG Engine."""

from __future__ import annotations

from app.models import CitationNode
from app.engines.graph_rag.models import GraphContext


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
        oid = obl.get("id") or obl.get("obligation_id") or obl.get("article") or obl.get("text", "")[:30]
        if oid and oid not in seen_ids:
            seen_ids.add(oid)
            raw_art = str(obl.get("article", "") or "")
            if raw_art.isdigit():
                raw_art = f"Article {raw_art}"
            elif raw_art.startswith("Art. "):
                raw_art = raw_art.replace("Art. ", "Article ")
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
        gid = gap.get("obligation_id") or gap.get("id") or gap.get("article") or gap.get("text", "")[:30]
        if gid and gid not in seen_ids:
            seen_ids.add(gid)
            raw_art = str(gap.get("article", "") or "")
            if raw_art.isdigit():
                raw_art = f"Article {raw_art}"
            elif raw_art.startswith("Art. "):
                raw_art = raw_art.replace("Art. ", "Article ")
            citations.append(CitationNode(
                node_type="Gap",
                node_id=gid,
                text=gap.get("text", ""),
                article_ref=raw_art,
            ))
            _gap_added += 1

    return citations
