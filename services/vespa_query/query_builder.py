#!/usr/bin/env python3
"""
Query builder for constructing Vespa search queries
"""

from typing import Dict, Any, Optional, List
from services.common.logging_config import get_logger
from services.common.telemetry import get_tracer

logger = get_logger(__name__)
tracer = get_tracer(__name__)

class QueryBuilder:
    """Builds Vespa search queries with various options"""
    
    def __init__(self):
        self.default_ranking_profile = "hybrid"
        self.default_max_hits = 10
        self.max_max_hits = 100
        
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
        include_facets: bool = True
    ) -> Dict[str, Any]:
        """Build a complete Vespa search query"""
        with tracer.start_as_current_span("query_builder.build_search_query") as span:
            span.set_attribute("query.user_id", user_id)
            span.set_attribute("query.ranking_profile", ranking_profile)
            span.set_attribute("query.max_hits", max_hits)
            span.set_attribute("query.offset", offset)
            span.set_attribute("query.include_facets", include_facets)
            span.set_attribute("query.source_types", str(source_types) if source_types else "none")
            span.set_attribute("query.providers", str(providers) if providers else "none")
            
            try:
                # Validate inputs
                self._validate_query_inputs(query, user_id, max_hits, offset)
                
                # Build base query
                vespa_query = {
                    "yql": self._build_yql_query(
                        query, user_id, source_types, providers, 
                        date_from, date_to, folders
                    ),
                    "ranking": ranking_profile,
                    "hits": min(max_hits, self.max_max_hits),
                    "offset": offset,
                    "timeout": "10s"
                }
                
                # Add faceting if requested
                if include_facets:
                    vespa_query["presentation.timing"] = True
                    vespa_query["presentation.summary"] = "default"
                    
                logger.info(f"Built search query for user {user_id} with {max_hits} hits")
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
        source_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Build an autocomplete query"""
        try:
            vespa_query = {
                "yql": self._build_autocomplete_yql(query, user_id, source_types),
                "ranking": "bm25",
                "hits": min(max_hits, 20),
                "timeout": "5s"
            }
            
            logger.info(f"Built autocomplete query for user {user_id}")
            return vespa_query
            
        except Exception as e:
            logger.error(f"Error building autocomplete query: {e}")
            raise
    
    def build_similar_documents_query(
        self,
        doc_id: str,
        user_id: str,
        max_hits: int = 10,
        source_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Build a query to find similar documents"""
        try:
            vespa_query = {
                "yql": self._build_similar_docs_yql(doc_id, user_id, source_types),
                "ranking": "semantic",
                "hits": min(max_hits, self.max_max_hits),
                "timeout": "10s"
            }
            
            logger.info(f"Built similar documents query for doc {doc_id}")
            return vespa_query
            
        except Exception as e:
            logger.error(f"Error building similar documents query: {e}")
            raise
    
    def build_facets_query(
        self,
        query: str,
        user_id: str,
        facet_fields: List[str],
        max_hits: int = 0
    ) -> Dict[str, Any]:
        """Build a query for faceted search"""
        try:
            vespa_query = {
                "yql": self._build_facets_yql(query, user_id, facet_fields),
                "ranking": "bm25",
                "hits": max_hits,
                "timeout": "10s"
            }
            
            logger.info(f"Built faceted search query for user {user_id}")
            return vespa_query
            
        except Exception as e:
            logger.error(f"Error building faceted search query: {e}")
            raise
    
    def _build_yql_query(
        self,
        query: str,
        user_id: str,
        source_types: Optional[List[str]] = None,
        providers: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        folders: Optional[List[str]] = None
    ) -> str:
        """Build YQL query string"""
        # Start with base query
        yql_parts = [
            "SELECT * FROM briefly_document",
            f"WHERE user_id = '{user_id}'"
        ]
        
        # Add source type filter
        if source_types:
            source_filter = " OR ".join([f"source_type = '{st}'" for st in source_types])
            yql_parts.append(f"AND ({source_filter})")
        
        # Add provider filter
        if providers:
            provider_filter = " OR ".join([f"provider = '{p}'" for p in providers])
            yql_parts.append(f"AND ({provider_filter})")
        
        # Add date range filter
        if date_from or date_to:
            date_filters = []
            if date_from:
                date_filters.append(f"created_at >= {date_from}")
            if date_to:
                date_filters.append(f"created_at <= {date_to}")
            if date_filters:
                yql_parts.append(f"AND ({' AND '.join(date_filters)})")
        
        # Add folder filter
        if folders:
            folder_filter = " OR ".join([f"folder = '{f}'" for f in folders])
            yql_parts.append(f"AND ({folder_filter})")
        
        # Add text search
        if query.strip():
            yql_parts.append(f"AND ({self._build_text_search(query)})")
        
        # Complete YQL
        yql = " ".join(yql_parts)
        logger.debug(f"Built YQL query: {yql}")
        return yql
    
    def _build_autocomplete_yql(self, query: str, user_id: str, source_types: Optional[List[str]] = None) -> str:
        """Build YQL for autocomplete"""
        yql_parts = [
            "SELECT * FROM briefly_document",
            f"WHERE user_id = '{user_id}'"
        ]
        
        if source_types:
            source_filter = " OR ".join([f"source_type = '{st}'" for st in source_types])
            yql_parts.append(f"AND ({source_filter})")
        
        if query.strip():
            yql_parts.append(f"AND ({self._build_text_search(query, prefix=True)})")
        
        return " ".join(yql_parts)
    
    def _build_similar_docs_yql(self, doc_id: str, user_id: str, source_types: Optional[List[str]] = None) -> str:
        """Build YQL for finding similar documents"""
        yql_parts = [
            "SELECT * FROM briefly_document",
            f"WHERE user_id = '{user_id}'",
            f"AND doc_id != '{doc_id}'"
        ]
        
        if source_types:
            source_filter = " OR ".join([f"source_type = '{st}'" for st in source_types])
            yql_parts.append(f"AND ({source_filter})")
        
        return " ".join(yql_parts)
    
    def _build_facets_yql(self, query: str, user_id: str, facet_fields: List[str]) -> str:
        """Build YQL for faceted search"""
        yql_parts = [
            "SELECT * FROM briefly_document",
            f"WHERE user_id = '{user_id}'"
        ]
        
        if query.strip():
            yql_parts.append(f"AND ({self._build_text_search(query)})")
        
        # Add facet specifications
        for field in facet_fields:
            yql_parts.append(f"FACET {field}")
        
        return " ".join(yql_parts)
    
    def _build_text_search(self, query: str, prefix: bool = False) -> str:
        """Build text search part of YQL"""
        if prefix:
            return f"title CONTAINS '{query}' OR content CONTAINS '{query}'"
        else:
            return f"title CONTAINS '{query}' OR content CONTAINS '{query}' OR search_text CONTAINS '{query}'"
    
    def _validate_query_inputs(self, query: str, user_id: str, max_hits: int, offset: int):
        """Validate query input parameters"""
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required")
        
        if max_hits < 1 or max_hits > self.max_max_hits:
            raise ValueError(f"max_hits must be between 1 and {self.max_max_hits}")
        
        if offset < 0:
            raise ValueError("offset must be non-negative")
        
        if not query or not query.strip():
            logger.warning("Empty query provided")
