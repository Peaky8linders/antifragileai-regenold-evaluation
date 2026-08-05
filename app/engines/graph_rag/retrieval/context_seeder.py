"""Context seeder for enriching GraphContext with MedTech and domain bridging context."""

from __future__ import annotations

import re
import logging
from app.engines.graph_rag.models import GraphContext, GraphQuery
from app.engines.graph_rag.medtech import MEDTECH_STANDARD_MAP, is_medtech_inquiry
from app.engines.graph_rag.config import config

logger = logging.getLogger(__name__)


def enrich_context(query: GraphQuery, context: GraphContext, question: str) -> None:
    """Enrich GraphContext with MedTech standards and domain bridging context with deduplication."""
    if not config.medtech_enabled:
        return

    try:
        q_low = question.lower()
        if is_medtech_inquiry(question):
            _ctx_refs = list(getattr(context, "article_info", []) or []) + list(
                getattr(context, "obligations", []) or []
            )
            for article, bridge_data in MEDTECH_STANDARD_MAP.items():
                art_num = article.replace("Art. ", "").strip()
                art_num_esc = re.escape(art_num)
                match_pattern = rf"\b(?:article|art\.?)\s*{art_num_esc}\b"
                
                if (
                    article in (query.entities if query else [])
                    or re.search(match_pattern, q_low)
                    or any(
                        a.get("article", "") == article or a.get("article_ref", "") == article
                        for a in _ctx_refs
                    )
                ):
                    standard = bridge_data.get("standard", "")
                    name = bridge_data.get("name", "")
                    bridge = bridge_data.get("bridge", "")
                    if bridge:
                        bridge_entry = f"Relevant Standard ({standard} - {name}): {bridge}"
                        if bridge_entry not in context.bridging_context:
                            context.bridging_context.append(bridge_entry)
    except Exception as exc:
        logger.debug("medtech bridging injection skipped: %s", exc)

