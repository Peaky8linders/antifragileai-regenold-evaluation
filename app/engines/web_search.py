"""Web search integration for complex queries.

R112 (finding 13) hardening:

* **Env-gated, default OFF** — ``REGENOLD_STAGE2_WEB_SEARCH`` must be
  explicitly set to ``1`` / ``true`` / ``yes`` / ``on`` for the search to
  fire. A synchronous third-party scrape on the request thread is an
  unmeasured latency knob; per the project's R69/R78 discipline those ship
  default-OFF. (The route owner folds this flag into
  ``_engine_cache_key`` so flipping it cannot serve stale cache entries.)
* **Short timeout** — ``DDGS(timeout=...)`` caps each underlying HTTP
  request (the library default is ~10 s; a complex-question row already
  pays the Stage-2 LLM round-trip, so the search budget must be small).
* **Lazy import** — ``duckduckgo_search`` is imported inside the call so
  module import never fails / slows when the dependency is absent and the
  gate is off (the default path).
* Exception wrapping preserved — the search can never break the route.
"""
import logging
import os

logger = logging.getLogger(__name__)

# Per-HTTP-request timeout (seconds) passed to DDGS. Kept deliberately
# small: the search runs synchronously on the request thread.
_DDGS_TIMEOUT_SECONDS = 2


def is_web_search_enabled() -> bool:
    """True when the operator explicitly enabled the Stage-2 web search."""
    return os.getenv("REGENOLD_STAGE2_WEB_SEARCH", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def perform_web_search(query: str, max_results: int = 3) -> list[str]:
    """Perform a web search using DuckDuckGo to supplement GraphRAG context.

    Returns a list of snippet strings combining the title, snippet, and URL.
    Returns an empty list when the env gate is off (the default), or if the
    search fails or returns no results.
    """
    results_list: list[str] = []
    if not is_web_search_enabled():
        return results_list
    try:
        from duckduckgo_search import DDGS  # noqa: PLC0415 — lazy heavy dep

        # DDGS().text returns an iterator of dictionaries:
        # {'title': '...', 'href': '...', 'body': '...'}
        results = DDGS(timeout=_DDGS_TIMEOUT_SECONDS).text(
            query, max_results=max_results
        )
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
