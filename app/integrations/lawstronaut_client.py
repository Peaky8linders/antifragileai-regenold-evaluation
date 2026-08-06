"""Lawstronaut REST v2 & MCP Protocol Client.

Provides structured access to Lawstronaut legal corpus, CELEX/ELI identifiers,
official EU AI Act markdown content, and Commission guidelines.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

LAWSTRONAUT_REST_URL = "https://api.lawstronaut.com/v2"
LAWSTRONAUT_MCP_URL = "https://mcp.lawstronaut.com"

# Official EU AI Act & Guidelines Document IDs in Lawstronaut
EU_AI_ACT_CONSOLIDATED_DOC_ID = 47256354
PROHIBITED_PRACTICES_GUIDELINES_DOC_ID = 47041422
GPAI_OBLIGATIONS_GUIDELINES_DOC_ID = 47037650

# Fallback Offline Metadata
OFFICIAL_PROVENANCE_FALLBACK = {
    "celex_id": "02024R1689-20260727",
    "eli_uri": "http://data.europa.eu/eli/reg/2024/1689/2026-07-27",
    "legal_link": "https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX:02024R1689-20260727",
    "title": "Regulation (EU) 2024/1689 of the European Parliament and of the Council (Artificial Intelligence Act)",
    "portal_name": "Euro Lex Europa",
    "jurisdiction": "EU",
}


class LawstronautClient:
    """Client for Lawstronaut API v2 and MCP server."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("LAWSTRONAUT_TOKEN", "")
        self.rest_url = LAWSTRONAUT_REST_URL
        self.mcp_url = LAWSTRONAUT_MCP_URL

    @property
    def _headers(self) -> Dict[str, str]:
        hdrs = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Antigravity-EU-AI-Act-RAG/1.0",
        }
        if self.token:
            hdrs["Authorization"] = f"Bearer {self.token}"
        return hdrs

    def get_document_metadata(self, doc_id: int = EU_AI_ACT_CONSOLIDATED_DOC_ID) -> Dict[str, Any]:
        """Fetch document metadata from Lawstronaut REST v2."""
        if not self.token:
            logger.warning("LAWSTRONAUT_TOKEN not set; using local fallback provenance.")
            return OFFICIAL_PROVENANCE_FALLBACK

        url = f"{self.rest_url}/contents"
        params = {"iso": "EU", "document_id": doc_id}
        try:
            r = requests.get(url, headers=self._headers, params=params, timeout=5)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    return data[0]
            logger.warning(f"Lawstronaut REST returned status {r.status_code}; using fallback provenance.")
        except Exception as e:
            logger.warning(f"Exception connecting to Lawstronaut API: {e}; using fallback.")

        return OFFICIAL_PROVENANCE_FALLBACK

    def get_document_markdown(self, doc_id: int = EU_AI_ACT_CONSOLIDATED_DOC_ID) -> Optional[str]:
        """Fetch full clean markdown of legal document."""
        if not self.token:
            return None

        url = f"{self.rest_url}/contents/markdown"
        params = {"iso": "EU", "document_id": doc_id}
        try:
            r = requests.get(url, headers=self._headers, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    return data[0].get("content_markdown")
        except Exception as e:
            logger.warning(f"Failed to fetch markdown for doc_id {doc_id}: {e}")

        return None

    def search_documents_by_title(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search EU documents by title query."""
        if not self.token:
            return []

        url = f"{self.rest_url}/contents"
        params = {"iso": "EU", "title": query, "limit": limit}
        try:
            r = requests.get(url, headers=self._headers, params=params, timeout=5)
            if r.status_code == 200:
                return r.json().get("data", [])
        except Exception as e:
            logger.warning(f"Search failed for query '{query}': {e}")

        return []
