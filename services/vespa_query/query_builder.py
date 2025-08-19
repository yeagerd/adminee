#!/usr/bin/env python3
"""
Query builder for constructing Vespa search queries
"""

from typing import Any, Dict, List, Optional

from services.common.logging_config import get_logger
from services.common.telemetry import get_tracer

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class QueryBuilder:
    """
    Builds Vespa YQL queries with proper escaping and validation
    """

    def __init__(self, max_max_hits: int = 1000):
        self.max_max_hits = max_max_hits

    def _escape_yql_value(self, value: str) -> str:
        """
        Safely escape a value for use in YQL queries to prevent injection attacks.

        YQL uses double quotes for string literals, so we need to escape:
        - Double quotes by doubling them
        - Backslashes by doubling them

        Args:
            value: The string value to escape

        Returns:
            The escaped string safe for YQL interpolation
        """
        if not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value).__name__}")

        # Escape backslashes first, then double quotes
        escaped = value.replace("\\", "\\\\").replace('"', '""')
        return escaped

    def build_search_query(
        self,
        query: str,
        user_id: str,
        ranking_profile: str = "hybrid",
        max_hits: int = 10,
        offset: int = 0,
        source_types: Optional[List[str]] = None,
        providers: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        folders: Optional[List[str]] = None,
        include_facets: bool = True,
    ) -> Dict[str, Any]:
        """Build a complete Vespa search query"""
        with tracer.start_as_current_span("query_builder.build_search_query") as span:
            span.set_attribute("query.user_id", user_id)
            span.set_attribute("query.ranking_profile", ranking_profile)
            span.set_attribute("query.max_hits", max_hits)
            span.set_attribute("query.offset", offset)
            span.set_attribute("query.include_facets", include_facets)
            span.set_attribute(
                "query.source_types", str(source_types) if source_types else "none"
            )
            span.set_attribute(
                "query.providers", str(providers) if providers else "none"
            )

            try:
                # Validate inputs
                self._validate_query_inputs(query, user_id, max_hits, offset)

                # Build base query
                vespa_query = {
                    "yql": self._build_yql_query(
                        query,
                        user_id,
                        source_types,
                        providers,
                        date_from,
                        date_to,
                        folders,
                    ),
                    "ranking": ranking_profile,
                    "hits": min(max_hits, self.max_max_hits),
                    "offset": offset,
                    "timeout": "10s",
                    "streaming.groupname": user_id,  # Add streaming mode support for user isolation
                }

                # Add faceting if requested
                if include_facets:
                    vespa_query["presentation.timing"] = True
                    vespa_query["presentation.summary"] = "default"

                logger.info(
                    f"Built search query for user {user_id} with {max_hits} hits"
                )
                span.set_attribute("query.build.success", True)
                return vespa_query

            except Exception as e:
                logger.error(f"Error building search query: {e}")
                span.set_attribute("query.build.success", False)
                span.set_attribute("query.error.message", str(e))
                span.record_exception(e)
                raise

    def build_autocomplete_query(
        self,
        query: str,
        user_id: str,
        max_hits: int = 5,
        source_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build an autocomplete query"""
        try:
            vespa_query = {
                "yql": self._build_autocomplete_yql(query, user_id, source_types),
                "ranking": "bm25",
                "hits": min(max_hits, 20),
                "timeout": "5s",
                "streaming.groupname": user_id,  # Add streaming mode support for user isolation
                "query": query,  # Add query parameter for userInput(@query) in YQL
            }

            logger.info(f"Built autocomplete query for user {user_id}")
            return vespa_query

        except Exception as e:
            logger.error(f"Error building autocomplete query: {e}")
            raise

    def build_facets_query(
        self,
        user_id: str,
        source_types: Optional[List[str]] = None,
        providers: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a facets query"""
        try:
            vespa_query = {
                "yql": self._build_facets_yql(
                    user_id, source_types, providers, date_from, date_to
                ),
                "hits": 0,  # We only want facets, not documents
                "timeout": "5s",
                "streaming.groupname": user_id,
                "presentation.timing": True,
            }

            # Add facet specifications
            vespa_query["facets"] = {
                "source_type": {"count": 100},
                "provider": {"count": 100},
                "folder": {"count": 100},
            }

            logger.info(f"Built facets query for user {user_id}")
            return vespa_query

        except Exception as e:
            logger.error(f"Error building facets query: {e}")
            raise

    def build_similarity_query(
        self, document_id: str, user_id: str, max_hits: int = 10
    ) -> Dict[str, Any]:
        """Build a similarity search query"""
        try:
            # Safely escape user inputs to prevent YQL injection
            escaped_user_id = self._escape_yql_value(user_id)
            escaped_document_id = self._escape_yql_value(document_id)

            vespa_query = {
                "yql": f'select * from briefly_document where user_id="{escaped_user_id}" and doc_id!="{escaped_document_id}"',
                "ranking": "similarity",
                "hits": min(max_hits, 20),
                "timeout": "5s",
                "streaming.groupname": user_id,
            }

            logger.info(f"Built similarity query for user {user_id}")
            return vespa_query

        except Exception as e:
            logger.error(f"Error building similarity query: {e}")
            raise

    def build_trending_query(
        self, user_id: str, time_range: str = "7d", max_hits: int = 10
    ) -> Dict[str, Any]:
        """Build a trending query"""
        try:
            # Safely escape user inputs to prevent YQL injection
            escaped_user_id = self._escape_yql_value(user_id)

            vespa_query = {
                "yql": f'select * from briefly_document where user_id="{escaped_user_id}"',
                "ranking": "trending",
                "hits": min(max_hits, 20),
                "timeout": "5s",
                "streaming.groupname": user_id,
                "ranking.features.query(timeDecay)": time_range,
            }

            logger.info(f"Built trending query for user {user_id}")
            return vespa_query

        except Exception as e:
            logger.error(f"Error building trending query: {e}")
            raise

    def build_analytics_query(
        self, user_id: str, time_range: str = "30d"
    ) -> Dict[str, Any]:
        """Build an analytics query"""
        try:
            # Safely escape user inputs to prevent YQL injection
            escaped_user_id = self._escape_yql_value(user_id)

            vespa_query = {
                "yql": f'select * from briefly_document where user_id="{escaped_user_id}"',
                "hits": 0,  # We only want analytics, not documents
                "timeout": "10s",
                "streaming.groupname": user_id,
                "presentation.timing": True,
                "grouping": {
                    "source_type": {"count": 100},
                    "provider": {"count": 100},
                    "time_buckets": {"count": 100},
                },
            }

            logger.info(f"Built analytics query for user {user_id}")
            return vespa_query

        except Exception as e:
            logger.error(f"Error building analytics query: {e}")
            raise

    def _validate_query_inputs(
        self, query: str, user_id: str, max_hits: int, offset: int
    ) -> None:
        """Validate query input parameters"""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if not user_id or not user_id.strip():
            raise ValueError("User ID cannot be empty")

        if max_hits <= 0:
            raise ValueError("Max hits must be positive")

        if max_hits > self.max_max_hits:
            raise ValueError(f"Max hits cannot exceed {self.max_max_hits}")

        if offset < 0:
            raise ValueError("Offset cannot be negative")

    def _build_yql_query(
        self,
        query: str,
        user_id: str,
        source_types: Optional[List[str]] = None,
        providers: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        folders: Optional[List[str]] = None,
    ) -> str:
        """Build the YQL query string"""
        # Safely escape user inputs to prevent YQL injection
        escaped_query = self._escape_yql_value(query)
        escaped_user_id = self._escape_yql_value(user_id)

        # Build a more specific query that searches in search_text and content fields
        # Add explicit user_id filtering for consistent user isolation
        yql_parts = [
            f'select * from briefly_document where user_id="{escaped_user_id}" and (search_text contains "{escaped_query}" or content contains "{escaped_query}")'
        ]

        # Add source type filter
        if source_types:
            escaped_source_types = [self._escape_yql_value(st) for st in source_types]
            source_type_filter = " or ".join(
                [f'source_type="{st}"' for st in escaped_source_types]
            )
            yql_parts.append(f"and ({source_type_filter})")

        # Add provider filter
        if providers:
            escaped_providers = [self._escape_yql_value(p) for p in providers]
            provider_filter = " or ".join(
                [f'provider="{p}"' for p in escaped_providers]
            )
            yql_parts.append(f"and ({provider_filter})")

        # Add date range filter
        if date_from or date_to:
            date_filter_parts = []
            if date_from:
                escaped_date_from = self._escape_yql_value(date_from)
                date_filter_parts.append(f'created_at >= "{escaped_date_from}"')
            if date_to:
                escaped_date_to = self._escape_yql_value(date_to)
                date_filter_parts.append(f'created_at <= "{escaped_date_to}"')
            if date_filter_parts:
                yql_parts.append(f'and ({" and ".join(date_filter_parts)})')

        # Add folder filter
        if folders:
            escaped_folders = [self._escape_yql_value(f) for f in folders]
            folder_filter = " or ".join([f'folder="{f}"' for f in escaped_folders])
            yql_parts.append(f"and ({folder_filter})")

        return " ".join(yql_parts)

    def _build_autocomplete_yql(
        self, query: str, user_id: str, source_types: Optional[List[str]] = None
    ) -> str:
        """Build YQL for autocomplete queries"""
        # Safely escape user inputs to prevent YQL injection
        escaped_user_id = self._escape_yql_value(user_id)

        yql_parts = [
            f'select * from briefly_document where user_id="{escaped_user_id}" and userInput(@query)'
        ]

        # Add source type filter for autocomplete
        if source_types:
            escaped_source_types = [self._escape_yql_value(st) for st in source_types]
            source_type_filter = " or ".join(
                [f'source_type="{st}"' for st in escaped_source_types]
            )
            yql_parts.append(f"and ({source_type_filter})")

        return " ".join(yql_parts)

    def _build_facets_yql(
        self,
        user_id: str,
        source_types: Optional[List[str]] = None,
        providers: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> str:
        """Build YQL for facets queries"""
        # Safely escape user inputs to prevent YQL injection
        escaped_user_id = self._escape_yql_value(user_id)

        yql_parts = [
            f'select * from briefly_document where user_id="{escaped_user_id}"'
        ]

        # Add filters for facets
        filters = []

        if source_types:
            escaped_source_types = [self._escape_yql_value(st) for st in source_types]
            source_type_filter = " or ".join(
                [f'source_type="{st}"' for st in escaped_source_types]
            )
            filters.append(f"({source_type_filter})")

        if providers:
            escaped_providers = [self._escape_yql_value(p) for p in providers]
            provider_filter = " or ".join(
                [f'provider="{p}"' for p in escaped_providers]
            )
            filters.append(f"({provider_filter})")

        if date_from or date_to:
            date_filter_parts = []
            if date_from:
                escaped_date_from = self._escape_yql_value(date_from)
                date_filter_parts.append(f'created_at >= "{escaped_date_from}"')
            if date_to:
                escaped_date_to = self._escape_yql_value(date_to)
                date_filter_parts.append(f'created_at <= "{escaped_date_to}"')
            if date_filter_parts:
                filters.append(f'({" and ".join(date_filter_parts)})')

        if filters:
            yql_parts.append("and")
            yql_parts.append(" and ".join(filters))

        return " ".join(yql_parts)
