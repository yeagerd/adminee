#!/usr/bin/env python3
"""
Result processor for handling and formatting Vespa search results
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from services.common.logging_config import get_logger
from services.common.telemetry import get_tracer

logger = get_logger(__name__)
tracer = get_tracer(__name__)

class ResultProcessor:
    """Processes and formats Vespa search results"""
    
    def __init__(self):
        self.default_max_snippet_length = 200
        self.max_title_length = 100
        
    def process_search_results(
        self,
        vespa_results: Dict[str, Any],
        query: str,
        user_id: str,
        include_highlights: bool = True,
        include_facets: bool = True
    ) -> Dict[str, Any]:
        """Process raw Vespa search results into formatted output"""
        with tracer.start_as_current_span("result_processor.process_search_results") as span:
            span.set_attribute("result.query", query)
            span.set_attribute("result.user_id", user_id)
            span.set_attribute("result.include_highlights", include_highlights)
            span.set_attribute("result.include_facets", include_facets)
            
            try:
                if not vespa_results:
                    logger.warning("Empty Vespa results received")
                    span.set_attribute("result.empty", True)
                    return self._create_empty_results(query, user_id)
                
                # Extract basic result info
                total_hits = vespa_results.get("root", {}).get("fields", {}).get("totalCount", 0)
                coverage = vespa_results.get("root", {}).get("coverage", {})
                span.set_attribute("result.total_hits", total_hits)
                
                # Process documents
                documents = self._process_documents(
                    vespa_results.get("root", {}).get("children", []),
                    include_highlights
                )
                span.set_attribute("result.documents_processed", len(documents))
                
                # Process facets if available
                facets = {}
                if include_facets:
                    facets = self._process_facets(vespa_results.get("root", {}).get("children", []))
                    span.set_attribute("result.facets_count", len(facets))
                
                # Process performance metrics
                performance = self._extract_performance_metrics(vespa_results)
                
                # Create processed results
                processed_results = {
                    "query": query,
                    "user_id": user_id,
                    "total_hits": total_hits,
                    "documents": documents,
                    "facets": facets,
                    "performance": performance,
                    "coverage": coverage,
                    "processed_at": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Processed {len(documents)} results for query '{query}'")
                span.set_attribute("result.processing.success", True)
                return processed_results
                
            except Exception as e:
                logger.error(f"Error processing search results: {e}")
                span.set_attribute("result.processing.success", False)
                span.set_attribute("result.error.message", str(e))
                span.record_exception(e)
                return self._create_error_results(query, user_id, str(e))
    
    def process_autocomplete_results(
        self,
        vespa_results: Dict[str, Any],
        query: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Process autocomplete results"""
        try:
            documents = self._process_documents(
                vespa_results.get("root", {}).get("children", []),
                include_highlights=False
            )
            
            # Extract suggestions from titles and content
            suggestions = self._extract_autocomplete_suggestions(documents, query)
            
            return {
                "query": query,
                "user_id": user_id,
                "suggestions": suggestions,
                "total_suggestions": len(suggestions),
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing autocomplete results: {e}")
            return {"suggestions": [], "error": str(e)}
    
    def process_similar_documents_results(
        self,
        vespa_results: Dict[str, Any],
        original_doc_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Process similar documents results"""
        try:
            documents = self._process_documents(
                vespa_results.get("root", {}).get("children", []),
                include_highlights=False
            )
            
            # Add similarity scores if available
            for doc in documents:
                if "relevance" in doc:
                    doc["similarity_score"] = doc.pop("relevance")
            
            return {
                "original_doc_id": original_doc_id,
                "user_id": user_id,
                "similar_documents": documents,
                "total_similar": len(documents),
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing similar documents results: {e}")
            return {"similar_documents": [], "error": str(e)}
    
    def _process_documents(self, vespa_docs: List[Dict[str, Any]], include_highlights: bool) -> List[Dict[str, Any]]:
        """Process individual Vespa documents"""
        processed_docs = []
        
        for doc in vespa_docs:
            try:
                fields = doc.get("fields", {})
                
                processed_doc = {
                    "id": fields.get("doc_id"),
                    "title": self._truncate_text(fields.get("title", ""), self.max_title_length),
                    "content": fields.get("content", ""),
                    "source_type": fields.get("source_type"),
                    "provider": fields.get("provider"),
                    "user_id": fields.get("user_id"),
                    "created_at": fields.get("created_at"),
                    "updated_at": fields.get("updated_at"),
                    "relevance": doc.get("relevance", 0.0),
                    "metadata": {}
                }
                
                # Add highlights if requested
                if include_highlights and "highlights" in doc:
                    processed_doc["highlights"] = self._process_highlights(doc["highlights"])
                
                # Add metadata fields
                metadata_fields = ["sender", "recipients", "thread_id", "folder", "location", "attendees"]
                for field in metadata_fields:
                    if field in fields:
                        processed_doc["metadata"][field] = fields[field]
                
                # Add snippet if content is long
                if len(fields.get("content", "")) > self.default_max_snippet_length:
                    processed_doc["snippet"] = self._create_snippet(
                        fields.get("content", ""),
                        self.default_max_snippet_length
                    )
                
                processed_docs.append(processed_doc)
                
            except Exception as e:
                logger.warning(f"Error processing document: {e}")
                continue
        
        return processed_docs
    
    def _process_highlights(self, highlights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process Vespa highlights"""
        processed_highlights = []
        
        for highlight in highlights:
            try:
                processed_highlight = {
                    "field": highlight.get("field"),
                    "snippet": highlight.get("snippet"),
                    "matches": highlight.get("matches", [])
                }
                processed_highlights.append(processed_highlight)
            except Exception as e:
                logger.warning(f"Error processing highlight: {e}")
                continue
        
        return processed_highlights
    
    def _process_facets(self, vespa_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process Vespa facets"""
        facets = {}
        
        # Look for facet information in the results
        # This is a simplified implementation - actual facets would come from Vespa
        source_types = {}
        providers = {}
        folders = {}
        
        for doc in vespa_docs:
            fields = doc.get("fields", {})
            
            # Count source types
            source_type = fields.get("source_type")
            if source_type:
                source_types[source_type] = source_types.get(source_type, 0) + 1
            
            # Count providers
            provider = fields.get("provider")
            if provider:
                providers[provider] = providers.get(provider, 0) + 1
            
            # Count folders
            folder = fields.get("folder")
            if folder:
                folders[folder] = folders.get(folder, 0) + 1
        
        if source_types:
            facets["source_type"] = [
                {"value": k, "count": v} for k, v in source_types.items()
            ]
        
        if providers:
            facets["provider"] = [
                {"value": k, "count": v} for k, v in providers.items()
            ]
        
        if folders:
            facets["folder"] = [
                {"value": k, "count": v} for k, v in folders.items()
            ]
        
        return facets
    
    def _extract_performance_metrics(self, vespa_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract performance metrics from Vespa results"""
        performance = {}
        
        # Extract timing information if available
        timing = vespa_results.get("timing", {})
        if timing:
            performance["query_time_ms"] = timing.get("queryTime", 0)
            performance["summary_time_ms"] = timing.get("summaryTime", 0)
        
        # Extract coverage information
        coverage = vespa_results.get("root", {}).get("coverage", {})
        if coverage:
            performance["coverage"] = coverage.get("coverage", 0)
            performance["documents"] = coverage.get("documents", 0)
        
        return performance
    
    def _extract_autocomplete_suggestions(self, documents: List[Dict[str, Any]], query: str) -> List[str]:
        """Extract autocomplete suggestions from documents"""
        suggestions = set()
        query_lower = query.lower()
        
        for doc in documents:
            title = doc.get("title", "").lower()
            content = doc.get("content", "").lower()
            
            # Look for query prefix matches
            if title.startswith(query_lower):
                suggestions.add(doc["title"])
            
            if content.startswith(query_lower):
                # Extract sentence or phrase starting with query
                content_start = content.find(query_lower)
                if content_start >= 0:
                    sentence_end = content.find(".", content_start)
                    if sentence_end > 0:
                        suggestion = content[content_start:sentence_end].strip()
                        if len(suggestion) < 100:  # Limit suggestion length
                            suggestions.add(suggestion)
        
        return list(suggestions)[:10]  # Limit to 10 suggestions
    
    def _create_snippet(self, content: str, max_length: int) -> str:
        """Create a text snippet from content"""
        if len(content) <= max_length:
            return content
        
        # Try to break at sentence boundary
        snippet = content[:max_length]
        last_period = snippet.rfind(".")
        
        if last_period > max_length * 0.7:  # If period is in last 30%
            return snippet[:last_period + 1]
        
        return snippet + "..."
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length"""
        if not text or len(text) <= max_length:
            return text
        
        return text[:max_length - 3] + "..."
    
    def _create_empty_results(self, query: str, user_id: str) -> Dict[str, Any]:
        """Create empty results structure"""
        return {
            "query": query,
            "user_id": user_id,
            "total_hits": 0,
            "documents": [],
            "facets": {},
            "performance": {},
            "coverage": {},
            "processed_at": datetime.utcnow().isoformat()
        }
    
    def _create_error_results(self, query: str, user_id: str, error: str) -> Dict[str, Any]:
        """Create error results structure"""
        return {
            "query": query,
            "user_id": user_id,
            "total_hits": 0,
            "documents": [],
            "facets": {},
            "performance": {},
            "coverage": {},
            "error": error,
            "processed_at": datetime.utcnow().isoformat()
        }
