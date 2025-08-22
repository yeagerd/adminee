"""
Vespa-based search tools for user data with pre-authenticated user context.
"""

import logging
from typing import Any, Dict, List, Optional

from services.vespa_query.search_engine import SearchEngine

logger = logging.getLogger(__name__)


class VespaSearchTool:
    """Tool for searching user data using Vespa"""

    def __init__(self, vespa_endpoint: str, user_id: str):
        self.search_engine = SearchEngine(vespa_endpoint)
        self.user_id = user_id
        self.tool_name = "vespa_search"
        self.description = "Search through user's emails, calendar events, contacts, and files using semantic and keyword search"

    async def search(
        self,
        query: str,
        max_results: int = 10,
        source_types: Optional[List[str]] = None,
        ranking_profile: str = "hybrid",
    ) -> Dict[str, Any]:
        """Search user data using Vespa"""
        try:
            # Build search query
            yql_query = self._build_yql_query(query, source_types)
            search_query = {
                "yql": yql_query,
                "hits": max_results,
                "ranking": ranking_profile,
                "timeout": "5.0s",
                "streaming.groupname": self.user_id,  # Add streaming mode support for user isolation
            }

            # Debug logging
            logger.info(f"Search query: {search_query}")

            # Execute search
            results = await self.search_engine.search(search_query)

            # Process results
            processed_results = self._process_search_results(results, query)

            return {
                "status": "success",
                "query": query,
                "results": processed_results,
                "total_found": results.get("root", {})
                .get("fields", {})
                .get("totalCount", 0),
                "search_time_ms": results.get("performance", {}).get(
                    "query_time_ms", 0
                ),
            }

        except Exception as e:
            logger.error(f"Vespa search failed: {e}")
            return {"status": "error", "query": query, "error": str(e), "results": []}

    def _build_yql_query(
        self, query: str, source_types: Optional[List[str]] = None
    ) -> str:
        """Build YQL query for Vespa"""
        # Base query - use streaming group for user isolation instead of user_id filter
        yql = "select * from briefly_document where true"

        # Add source type filtering
        if source_types:
            source_types_str = '", "'.join(source_types)
            yql += f' and source_type in ("{source_types_str}")'

        # Parse and enhance the query for better search results
        enhanced_query = self._parse_and_enhance_query(query)
        yql += enhanced_query

        return yql

    def _parse_and_enhance_query(self, query: str) -> str:
        """Parse the query and create enhanced search conditions"""
        import re

        query_lower = query.lower().strip()

        # Pattern: "emails from [sender]" or "email from [sender]"
        email_from_pattern = r"\b(?:emails?|email)\s+from\s+(.+?)(?:\s|$)"
        match = re.search(email_from_pattern, query_lower)
        if match:
            sender = match.group(1).strip()
            # Search in sender field and also in general content for the sender name
            return f' and (sender contains "{sender}" or search_text contains "{sender}" or title contains "{sender}" or content contains "{sender}")'

        # Pattern: "find [anything] from [sender]"
        find_from_pattern = r"\bfind\s+.+?\s+from\s+(.+?)(?:\s|$)"
        match = re.search(find_from_pattern, query_lower)
        if match:
            sender = match.group(1).strip()
            return f' and (sender contains "{sender}" or search_text contains "{sender}" or title contains "{sender}" or content contains "{sender}")'

        # Default: search across all text fields
        return f' and (search_text contains "{query}" or title contains "{query}" or content contains "{query}")'

    def _process_search_results(
        self, results: Dict[str, Any], query: str
    ) -> List[Dict[str, Any]]:
        """Process and format search results with enhanced metadata"""
        processed = []

        try:
            root = results.get("root", {})
            children = root.get("children", [])

            for child in children:
                fields = child.get("fields", {})

                # Determine search method based on relevance score and content analysis
                search_method = self._determine_search_method(child, fields, query)

                # Extract relevant fields
                result = {
                    "id": fields.get("doc_id"),
                    "type": fields.get("source_type"),
                    "provider": fields.get("provider"),
                    "title": fields.get("title", ""),
                    "content": fields.get("content", ""),
                    "search_text": fields.get("search_text", ""),
                    "created_at": fields.get("created_at"),
                    "updated_at": fields.get("updated_at"),
                    "relevance_score": child.get("relevance", 0.0),
                    "snippet": self._generate_snippet(
                        fields.get("search_text", ""), query
                    ),
                    "search_method": search_method,
                    "match_confidence": self._calculate_match_confidence(
                        child, fields, query
                    ),
                    "vector_similarity": fields.get("embedding_similarity", None),
                    "keyword_matches": self._count_keyword_matches(
                        fields.get("search_text", ""), query
                    ),
                    "content_length": len(fields.get("content", "")),
                    "search_text_length": len(fields.get("search_text", "")),
                }

                # Add type-specific fields
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
                            "has_attachments": fields.get("metadata", {}).get(
                                "has_attachments", False
                            ),
                            "attachment_count": fields.get("metadata", {}).get(
                                "attachment_count", 0
                            ),
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

            # Sort by relevance score
            processed.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)

        except Exception as e:
            logger.error(f"Error processing search results: {e}")

        return processed

    def _determine_search_method(
        self, child: Dict[str, Any], fields: Dict[str, Any], query: str
    ) -> str:
        """Determine whether result came from vector similarity or keyword matching"""
        relevance = child.get("relevance", 0.0)
        search_text = fields.get("search_text", "").lower()
        query_lower = query.lower()

        # Check for exact keyword matches
        exact_matches = query_lower in search_text
        word_matches = any(word in search_text for word in query_lower.split())

        # Check if we have vector similarity data
        has_vector = fields.get("embedding") is not None

        if has_vector and relevance > 0.5:
            if exact_matches or word_matches:
                return "Hybrid (Vector + Keyword)"
            else:
                return "Vector Similarity"
        elif exact_matches or word_matches:
            return "Keyword Matching"
        else:
            return "Semantic/Contextual"

    def _calculate_match_confidence(
        self, child: Dict[str, Any], fields: Dict[str, Any], query: str
    ) -> str:
        """Calculate confidence level of the match"""
        relevance = child.get("relevance", 0.0)
        search_text = fields.get("search_text", "").lower()
        query_lower = query.lower()

        # Count keyword matches
        query_words = query_lower.split()
        matches = sum(1 for word in query_words if word in search_text)
        match_ratio = matches / len(query_words) if query_words else 0

        if relevance > 0.8 and match_ratio > 0.8:
            return "Very High"
        elif relevance > 0.6 and match_ratio > 0.6:
            return "High"
        elif relevance > 0.4 and match_ratio > 0.4:
            return "Medium"
        elif relevance > 0.2:
            return "Low"
        else:
            return "Very Low"

    def _count_keyword_matches(self, search_text: str, query: str) -> Dict[str, Any]:
        """Count keyword matches and their positions"""
        if not search_text or not query:
            return {"count": 0, "words": [], "positions": []}

        search_lower = search_text.lower()
        query_lower = query.lower()
        query_words = query_lower.split()

        matches = []
        positions = []

        for word in query_words:
            if word in search_lower:
                matches.append(word)
                # Find all positions of this word
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
        """Generate a snippet highlighting the search query"""
        if not text or not query:
            return text[:max_length] if text else ""

        # Find query position in text
        query_lower = query.lower()
        text_lower = text.lower()

        pos = text_lower.find(query_lower)
        if pos == -1:
            # Query not found, return beginning of text
            return text[:max_length] + "..." if len(text) > max_length else text

        # Calculate snippet boundaries
        start = max(0, pos - max_length // 2)
        end = min(len(text), start + max_length)

        # Adjust boundaries to avoid cutting words
        while start > 0 and text[start] != " ":
            start -= 1
        while end < len(text) and text[end] != " ":
            end += 1

        snippet = text[start:end].strip()

        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet


class UserDataSearchTool:
    """Enhanced tool for searching user data with mixed result types"""

    def __init__(self, vespa_endpoint: str, user_id: str):
        self.vespa_search = VespaSearchTool(vespa_endpoint, user_id)
        self.tool_name = "user_data_search"
        self.description = "Search across all user data types (emails, calendar, contacts, files) with intelligent result grouping and relevance scoring"

    async def search_all_data(
        self, query: str, max_results: int = 20
    ) -> Dict[str, Any]:
        """Search across all data types with intelligent grouping"""
        try:
            # Search across all source types
            results = await self.vespa_search.search(
                query=query, max_results=max_results, ranking_profile="hybrid"
            )

            if results["status"] != "success":
                return results

            # Group results by type
            grouped_results = self._group_results_by_type(results["results"])

            # Add summary statistics
            summary = self._generate_search_summary(grouped_results, query)

            return {
                "status": "success",
                "query": query,
                "summary": summary,
                "grouped_results": grouped_results,
                "total_found": results["total_found"],
                "search_time_ms": results["search_time_ms"],
            }

        except Exception as e:
            logger.error(f"User data search failed: {e}")
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "grouped_results": {},
            }

    def _group_results_by_type(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group search results by data type"""
        grouped: Dict[str, List[Dict[str, Any]]] = {
            "emails": [],
            "calendar": [],
            "contacts": [],
            "files": [],
            "other": [],
        }

        for result in results:
            result_type = result.get("type", "other")

            if result_type == "email":
                grouped["emails"].append(result)
            elif result_type == "calendar":
                grouped["calendar"].append(result)
            elif result_type == "contact":
                grouped["contacts"].append(result)
            elif result_type == "file":
                grouped["files"].append(result)
            else:
                grouped["other"].append(result)

        return grouped

    def _generate_search_summary(
        self, grouped_results: Dict[str, List[Dict[str, Any]]], query: str
    ) -> Dict[str, Any]:
        """Generate a summary of search results"""
        total_results = sum(len(results) for results in grouped_results.values())

        summary = {
            "query": query,
            "total_results": total_results,
            "result_types": {
                "emails": len(grouped_results["emails"]),
                "calendar_events": len(grouped_results["calendar"]),
                "contacts": len(grouped_results["contacts"]),
                "files": len(grouped_results["files"]),
                "other": len(grouped_results["other"]),
            },
            "top_results": [],
            "insights": [],
        }

        # Get top results across all types
        all_results = []
        for results in grouped_results.values():
            all_results.extend(results)

        # Sort by relevance and take top 5
        all_results.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
        summary["top_results"] = all_results[:5]

        # Generate insights
        insights = []
        if grouped_results["emails"]:
            insights.append(f"Found {len(grouped_results['emails'])} relevant emails")
        if grouped_results["calendar"]:
            insights.append(f"Found {len(grouped_results['calendar'])} calendar events")
        if grouped_results["contacts"]:
            insights.append(f"Found {len(grouped_results['contacts'])} contacts")

        if insights:
            summary["insights"] = insights

        return summary


class SemanticSearchTool:
    """Tool for semantic search using vector embeddings"""

    def __init__(self, vespa_endpoint: str, user_id: str):
        self.search_engine = SearchEngine(vespa_endpoint)
        self.user_id = user_id
        self.tool_name = "semantic_search"
        self.description = "Perform semantic search using vector embeddings for finding conceptually similar content"

    async def semantic_search(
        self, query: str, max_results: int = 10
    ) -> Dict[str, Any]:
        """Perform semantic search using vector similarity"""
        try:
            # Build semantic search query
            search_query = {
                "yql": f'select * from briefly_document where user_id contains "{self.user_id}"',
                "hits": max_results,
                "ranking": "semantic",
                "timeout": "5.0s",
                "streaming.groupname": self.user_id,  # Add streaming mode support for user isolation
            }

            # Execute search
            results = await self.search_engine.search(search_query)

            # Process results
            processed_results = self._process_semantic_results(results, query)

            return {
                "status": "success",
                "query": query,
                "search_type": "semantic",
                "results": processed_results,
                "total_found": results.get("root", {})
                .get("fields", {})
                .get("totalCount", 0),
                "search_time_ms": results.get("performance", {}).get(
                    "query_time_ms", 0
                ),
            }

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return {"status": "error", "query": query, "error": str(e), "results": []}

    def _process_semantic_results(
        self, results: Dict[str, Any], query: str
    ) -> List[Dict[str, Any]]:
        """Process semantic search results"""
        processed = []

        try:
            root = results.get("root", {})
            children = root.get("children", [])

            for child in children:
                fields = child.get("fields", {})

                result = {
                    "id": fields.get("doc_id"),
                    "type": fields.get("source_type"),
                    "title": fields.get("title", ""),
                    "content": fields.get("content", ""),
                    "semantic_score": child.get("relevance", 0.0),
                    "snippet": self._generate_snippet(
                        fields.get("search_text", ""), query
                    ),
                }

                processed.append(result)

            # Sort by semantic score
            processed.sort(key=lambda x: x.get("semantic_score", 0.0), reverse=True)

        except Exception as e:
            logger.error(f"Error processing semantic results: {e}")

        return processed

    def _generate_snippet(self, text: str, query: str, max_length: int = 200) -> str:
        """Generate a snippet for semantic search results"""
        if not text:
            return ""

        # For semantic search, just return the beginning of the text
        # since we're not looking for exact keyword matches
        if len(text) <= max_length:
            return text

        return text[:max_length] + "..."


class SearchTools:
    """Collection of search tools with pre-authenticated user context."""

    def __init__(self, vespa_endpoint: str, user_id: str):
        self.vespa_endpoint = vespa_endpoint
        self.user_id = user_id
        self.vespa_search = VespaSearchTool(vespa_endpoint, user_id)
        self.user_data_search = UserDataSearchTool(vespa_endpoint, user_id)
        self.semantic_search = SemanticSearchTool(vespa_endpoint, user_id)
