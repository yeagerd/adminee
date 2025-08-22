"""
Unified Vespa-backed search tool for user data with pre-authenticated user context.

This module exposes a single public class `UserDataSearchTool` that provides one
search entry point performing a hybrid search across all user data. The
implementation handles query construction, execution, result processing, and
lightweight grouping/summary.

Downstream callers should use `UserDataSearchTool.search_all_data(...)` as the
single entry point. If specialized search types are needed in the future, they
can be added as optional parameters without changing the agent-side logic.
"""

import logging
from typing import Any, Dict, List, Optional

from services.vespa_query.search_engine import SearchEngine

logger = logging.getLogger(__name__)


class UserDataSearchTool:
    """Unified tool for searching user data with a single hybrid entry point."""

    def __init__(self, vespa_endpoint: str, user_id: str):
        self.search_engine = SearchEngine(vespa_endpoint)
        self.user_id = user_id
        self.tool_name = "user_data_search"
        self.description = (
            "Hybrid search across emails, calendar, contacts, and files with "
            "intelligent result processing, grouping, and summarization"
        )
        # Provide a small shim for legacy code that expects a nested vespa_search
        self.vespa_search = _SearchEngineShim(self.search_engine)

    async def search_all_data(self, query: str, max_results: int = 20) -> Dict[str, Any]:
        """Single entry point: perform a hybrid search across all data types."""
        try:
            yql_query = self._build_yql_query(query)
            search_query = {
                "yql": yql_query,
                "hits": max_results,
                "ranking": "hybrid",
                "timeout": "5.0s",
                "streaming.groupname": self.user_id,
            }

            logger.info(f"Search query: {search_query}")
            results = await self.search_engine.search(search_query)

            processed_results = self._process_search_results(results, query)

            grouped_results = self._group_results_by_type(processed_results)
            summary = self._generate_search_summary(grouped_results, query)

            return {
                "status": "success",
                "query": query,
                "summary": summary,
                "grouped_results": grouped_results,
                "total_found": results.get("root", {}).get("fields", {}).get(
                    "totalCount", 0
                ),
                "search_time_ms": results.get("performance", {}).get(
                    "query_time_ms", 0
                ),
            }
        except Exception as e:
            logger.error(f"User data search failed: {e}")
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "grouped_results": {},
            }

    def _build_yql_query(self, query: str) -> str:
        """Build YQL query for Vespa with optional light parsing."""
        yql = "select * from briefly_document where true"
        enhanced_query = self._parse_and_enhance_query(query)
        yql += enhanced_query
        return yql

    def _parse_and_enhance_query(self, query: str) -> str:
        """Parse the query and create enhanced search conditions."""
        import re

        query_lower = query.lower().strip()

        email_from_pattern = r"\b(?:emails?|email)\s+from\s+(.+?)(?:\s|$)"
        match = re.search(email_from_pattern, query_lower)
        if match:
            sender = match.group(1).strip()
            return (
                f' and (sender contains "{sender}" or search_text contains "{sender}" '
                f'or title contains "{sender}" or content contains "{sender}")'
            )

        find_from_pattern = r"\bfind\s+.+?\s+from\s+(.+?)(?:\s|$)"
        match = re.search(find_from_pattern, query_lower)
        if match:
            sender = match.group(1).strip()
            return (
                f' and (sender contains "{sender}" or search_text contains "{sender}" '
                f'or title contains "{sender}" or content contains "{sender}")'
            )

        return (
            f' and (search_text contains "{query}" or title contains "{query}" '
            f'or content contains "{query}")'
        )

    def _process_search_results(self, results: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """Process and format search results with enhanced metadata."""
        processed: List[Dict[str, Any]] = []

        try:
            root = results.get("root", {})
            children = root.get("children", [])

            for child in children:
                fields = child.get("fields", {})

                search_method = self._determine_search_method(child, fields, query)

                result: Dict[str, Any] = {
                    "id": fields.get("doc_id"),
                    "type": fields.get("source_type"),
                    "provider": fields.get("provider"),
                    "title": fields.get("title", ""),
                    "content": fields.get("content", ""),
                    "search_text": fields.get("search_text", ""),
                    "created_at": fields.get("created_at"),
                    "updated_at": fields.get("updated_at"),
                    "relevance_score": child.get("relevance", 0.0),
                    "snippet": self._generate_snippet(fields.get("search_text", ""), query),
                    "search_method": search_method,
                    "match_confidence": self._calculate_match_confidence(child, fields, query),
                    "vector_similarity": fields.get("embedding_similarity", None),
                    "keyword_matches": self._count_keyword_matches(fields.get("search_text", ""), query),
                    "content_length": len(fields.get("content", "")),
                    "search_text_length": len(fields.get("search_text", "")),
                }

                if fields.get("source_type") == "email":
                    result.update(
                        {
                            "sender": fields.get("sender"),
                            "recipients": fields.get("recipients", []),
                            "thread_id": fields.get("thread_id"),
                            "folder": fields.get("folder"),
                            "quoted_content": fields.get("quoted_content", ""),
                            "thread_summary": fields.get("thread_summary", {}),
                            "is_read": fields.get("metadata", {}).get("is_read", False),
                            "has_attachments": fields.get("metadata", {}).get("has_attachments", False),
                            "attachment_count": fields.get("metadata", {}).get("attachment_count", 0),
                        }
                    )
                elif fields.get("source_type") == "calendar":
                    result.update(
                        {
                            "start_time": fields.get("start_time"),
                            "end_time": fields.get("end_time"),
                            "attendees": fields.get("attendees", []),
                            "location": fields.get("location"),
                            "is_all_day": fields.get("is_all_day", False),
                            "recurring": fields.get("recurring", False),
                        }
                    )
                elif fields.get("source_type") == "contact":
                    result.update(
                        {
                            "display_name": fields.get("title"),
                            "email_addresses": fields.get("email_addresses", []),
                            "company": fields.get("company"),
                            "job_title": fields.get("job_title"),
                            "phone_numbers": fields.get("phone_numbers", []),
                            "address": fields.get("address", ""),
                        }
                    )

                processed.append(result)

            processed.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
        except Exception as e:
            logger.error(f"Error processing search results: {e}")

        return processed

    def _determine_search_method(self, child: Dict[str, Any], fields: Dict[str, Any], query: str) -> str:
        """Heuristic to label origin as vector/keyword/hybrid for explainability."""
        relevance = child.get("relevance", 0.0)
        search_text = fields.get("search_text", "").lower()
        query_lower = query.lower()

        exact_matches = query_lower in search_text
        word_matches = any(word in search_text for word in query_lower.split())
        has_vector = fields.get("embedding") is not None

        if has_vector and relevance > 0.5:
            if exact_matches or word_matches:
                return "Hybrid (Vector + Keyword)"
            return "Vector Similarity"
        if exact_matches or word_matches:
            return "Keyword Matching"
        return "Semantic/Contextual"

    def _calculate_match_confidence(self, child: Dict[str, Any], fields: Dict[str, Any], query: str) -> str:
        relevance = child.get("relevance", 0.0)
        search_text = fields.get("search_text", "").lower()
        query_lower = query.lower()

        query_words = query_lower.split()
        matches = sum(1 for word in query_words if word in search_text)
        match_ratio = matches / len(query_words) if query_words else 0

        if relevance > 0.8 and match_ratio > 0.8:
            return "Very High"
        if relevance > 0.6 and match_ratio > 0.6:
            return "High"
        if relevance > 0.4 and match_ratio > 0.4:
            return "Medium"
        if relevance > 0.2:
            return "Low"
        return "Very Low"

    def _count_keyword_matches(self, search_text: str, query: str) -> Dict[str, Any]:
        if not search_text or not query:
            return {"count": 0, "words": [], "positions": []}

        search_lower = search_text.lower()
        query_lower = query.lower()
        query_words = query_lower.split()

        matches: List[str] = []
        positions: List[int] = []

        for word in query_words:
            if word in search_lower:
                matches.append(word)
                start = 0
                while True:
                    pos = search_lower.find(word, start)
                    if pos == -1:
                        break
                    positions.append(pos)
                    start = pos + 1

        return {
            "count": len(matches),
            "words": list(set(matches)),
            "positions": sorted(positions),
            "match_ratio": len(matches) / len(query_words) if query_words else 0,
        }

    def _generate_snippet(self, text: str, query: str, max_length: int = 200) -> str:
        if not text or not query:
            return text[:max_length] if text else ""

        query_lower = query.lower()
        text_lower = text.lower()
        pos = text_lower.find(query_lower)
        if pos == -1:
            return text[:max_length] + "..." if len(text) > max_length else text

        start = max(0, pos - max_length // 2)
        end = min(len(text), start + max_length)

        while start > 0 and text[start] != " ":
            start -= 1
        while end < len(text) and text[end] != " ":
            end += 1

        snippet = text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return snippet


class SearchTools:
    """Collection exposing the unified search tool with pre-authenticated user context.

    Backwards-compatible attributes `vespa_search` and `semantic_search` are
    provided to preserve existing call sites and registry wiring. They both
    delegate to the unified `UserDataSearchTool.search_all_data` method and
    ignore extra parameters.
    """

    def __init__(self, vespa_endpoint: str, user_id: str):
        self.vespa_endpoint = vespa_endpoint
        self.user_id = user_id
        self.user_data_search = UserDataSearchTool(vespa_endpoint, user_id)
        self.vespa_search = _VespaSearchCompat(self.user_data_search)
        self.semantic_search = _SemanticSearchCompat(self.user_data_search)


class _VespaSearchCompat:
    """Compatibility wrapper that mirrors the old VespaSearchTool API."""

    def __init__(self, uds: UserDataSearchTool):
        self._uds = uds
        self.tool_name = "vespa_search"
        self.description = (
            "Compatibility: delegates to unified hybrid search across user data"
        )

    async def search(
        self,
        query: str,
        max_results: int = 10,
        source_types: Optional[List[str]] = None,  # ignored for now
        ranking_profile: str = "hybrid",  # ignored for now
    ) -> Dict[str, Any]:
        return await self._uds.search_all_data(query=query, max_results=max_results)


class _SemanticSearchCompat:
    """Compatibility wrapper that mirrors the old SemanticSearchTool API."""

    def __init__(self, uds: UserDataSearchTool):
        self._uds = uds
        self.tool_name = "semantic_search"
        self.description = (
            "Compatibility: delegates to unified hybrid search across user data"
        )

    async def semantic_search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        return await self._uds.search_all_data(query=query, max_results=max_results)


class _SearchEngineShim:
    """Shim exposing a search_engine attribute for legacy cleanup code."""

    def __init__(self, search_engine: SearchEngine):
        self.search_engine = search_engine


class VespaSearchTool(_VespaSearchCompat):
    """Public compatibility class to preserve imports and cleanup behavior."""

    def __init__(self, vespa_endpoint: str, user_id: str):
        uds = UserDataSearchTool(vespa_endpoint, user_id)
        super().__init__(uds)
        self.search_engine = uds.search_engine


class SemanticSearchTool(_SemanticSearchCompat):
    """Public compatibility class to preserve imports and calls."""

    def __init__(self, vespa_endpoint: str, user_id: str):
        uds = UserDataSearchTool(vespa_endpoint, user_id)
        super().__init__(uds)
        self.search_engine = uds.search_engine
