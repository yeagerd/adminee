"""
Web search tools for public information retrieval.
"""

import logging
from typing import Any, Dict, List
from urllib.parse import unquote

import requests

logger = logging.getLogger(__name__)


class WebSearchTool:
    """Lightweight web search tool for general web information retrieval."""

    def __init__(self) -> None:
        self.tool_name = "web_search"
        self.description = (
            "Search the public web for information and return a concise list of results"
        )

    async def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the web and return a list of title/url/snippet entries.

        Note: This uses DuckDuckGo's HTML endpoint and simple parsing. It may be brittle
        and should be replaced with a proper search API in production.
        """
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            }
            resp = requests.get(
                "https://duckduckgo.com/html/",
                params={"q": query},
                headers=headers,
                timeout=10,
            )
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HTTP {resp.status_code}",
                    "results": [],
                }

            html = resp.text
            results: List[Dict[str, Any]] = []

            # Very lightweight parsing: look for links shaped like /l/?uddg=...
            # and extract adjacent title text. This is intentionally simple.
            # We avoid heavy dependencies for now.
            anchor_marker = 'href="/l/?uddg='
            pos = 0
            while len(results) < max_results:
                idx = html.find(anchor_marker, pos)
                if idx == -1:
                    break
                # Extract URL
                start = idx + len('href="/l/?uddg=')
                end = html.find('"', start)
                if end == -1:
                    break
                raw = html[start:end]
                url = unquote(raw)
                # Extract a crude title by looking for ">...<" after the anchor
                title_start = html.find(">", end) + 1
                title_end = html.find("<", title_start)
                title = html[title_start:title_end].strip()
                if title and url:
                    results.append({"title": title, "url": url})
                pos = end + 1

            return {"status": "success", "query": query, "results": results}
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {"status": "error", "error": str(e), "results": []}


class WebTools:
    """Collection of web search tools."""

    def __init__(self) -> None:
        self.web_search = WebSearchTool()
