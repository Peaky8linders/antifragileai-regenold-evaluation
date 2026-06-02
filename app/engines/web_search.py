"""Web search integration for complex queries."""
import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

def perform_web_search(query: str, max_results: int = 3) -> list[str]:
    """Perform a web search using DuckDuckGo to supplement GraphRAG context.
    
    Returns a list of snippet strings combining the title, snippet, and URL.
    Returns an empty list if the search fails or returns no results.
    """
    results_list = []
    try:
        # DDGS().text returns an iterator of dictionaries:
        # {'title': '...', 'href': '...', 'body': '...'}
        results = DDGS().text(query, max_results=max_results)
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            url = r.get("href", "")
            if body:
                snippet = f"Source: {title} ({url})\nSnippet: {body}"
                results_list.append(snippet)
    except Exception as exc:
        logger.warning("web_search_failed for query %r: %s", query, exc)
    
    return results_list
