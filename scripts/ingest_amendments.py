"""Ingest official EU AI Act amendments into Neo4j.

Creates an `Amendment` node and links it to modified `Article` nodes using
an `AMENDS` edge.

Run:
    py -3.12 scripts/ingest_amendments.py
"""
import logging
import os
import sys
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.graph.client import get_graph_client

logger = logging.getLogger(__name__)

CYPHER_MERGE_AMENDMENT = """
MERGE (am:Amendment {id: $id})
SET am.date = $date,
    am.title = $title,
    am.summary = $summary
"""

CYPHER_LINK_AMENDS = """
MATCH (am:Amendment {id: $am_id})
MATCH (a:Article {number: $art_num})
MERGE (am)-[:AMENDS]->(a)
"""

def ingest_amendment(amendment_id: str, date: str, title: str, summary: str, target_articles: list[str]) -> None:
    client = get_graph_client()
    if not getattr(client, "enabled", False):
        print("Neo4j client not enabled. Ensure NEO4J_URI is set.")
        return

    # 1. Create Amendment Node
    try:
        client.execute_write(
            CYPHER_MERGE_AMENDMENT,
            {"id": amendment_id, "date": date, "title": title, "summary": summary}
        )
        print(f"Created/Merged Amendment: {amendment_id}")
    except Exception as e:
        print(f"Failed to create Amendment node: {e}")
        return

    # 2. Link to Articles
    for art in target_articles:
        # Extract article number. E.g., 'Article 51' -> '51'
        num = art.replace("Article ", "").replace("Art. ", "").strip()
        try:
            client.execute_write(
                CYPHER_LINK_AMENDS,
                {"am_id": amendment_id, "art_num": num}
            )
            print(f"  Linked {amendment_id} -[:AMENDS]-> Article {num}")
        except Exception as e:
            print(f"  Failed to link to Article {num}: {e}")

if __name__ == "__main__":
    try:
        from app.data.official_eu_ai_act import OFFICIAL_UPDATES
    except ImportError:
        print("Could not import OFFICIAL_UPDATES. Run fetch_official_eu_ai_act.py first.")
        sys.exit(1)

    print(f"Found {len(OFFICIAL_UPDATES)} official updates. Ingesting...")
    for idx, update in enumerate(OFFICIAL_UPDATES):
        # We use a simple hash or index for ID since the updates don't have explicit IDs.
        amd_id = f"amd_{update['date'].replace('-', '')}_{idx}"
        
        # Simple heuristic to extract mentioned articles from the summary to link them
        import re
        mentioned_arts = re.findall(r"Art(?:icle|\.)\s*(\d+)", update.get("summary", ""))
        target_articles = [f"Article {a}" for a in mentioned_arts]

        ingest_amendment(
            amendment_id=amd_id,
            date=update["date"],
            title=update["title"],
            summary=update["summary"],
            target_articles=target_articles
        )
    print("Ingestion complete.")
