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
    
    def __init__(self) -> None:
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
            return {
                "query": query,
                "user_id": user_id,
                "suggestions": [],
                "total_suggestions": 0,
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    def process_similarity_results(
        self,
        vespa_results: Dict[str, Any],
        query: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Process similarity search results"""
        try:
            documents = self._process_documents(
                vespa_results.get("root", {}).get("children", []),
                include_highlights=False
            )
            
            return {
                "query": query,
                "user_id": user_id,
                "similar_documents": documents,
                "total_similar": len(documents),
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing similarity results: {e}")
            return {
                "query": query,
                "user_id": user_id,
                "similar_documents": [],
                "total_similar": 0,
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    def process_facets_results(
        self,
        vespa_results: Dict[str, Any],
        query: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Process facets results"""
        try:
            facets = self._process_facets(vespa_results.get("root", {}).get("children", []))
            
            return {
                "query": query,
                "user_id": user_id,
                "facets": facets,
                "total_facets": len(facets),
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing facets results: {e}")
            return {
                "query": query,
                "user_id": user_id,
                "facets": {},
                "total_facets": 0,
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    def process_trending_results(
        self,
        vespa_results: Dict[str, Any],
        query: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Process trending results"""
        try:
            documents = self._process_documents(
                vespa_results.get("root", {}).get("children", []),
                include_highlights=False
            )
            
            return {
                "query": query,
                "user_id": user_id,
                "trending_documents": documents,
                "total_trending": len(documents),
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing trending results: {e}")
            return {
                "query": query,
                "user_id": user_id,
                "trending_documents": [],
                "total_trending": 0,
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    def process_analytics_results(
        self,
        vespa_results: Dict[str, Any],
        query: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Process analytics results"""
        try:
            # Extract analytics data
            analytics_data = self._extract_analytics_data(vespa_results)
            
            return {
                "query": query,
                "user_id": user_id,
                "analytics": analytics_data,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing analytics results: {e}")
            return {
                "query": query,
                "user_id": user_id,
                "analytics": {},
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    def _process_documents(self, documents: List[Dict[str, Any]], include_highlights: bool) -> List[Dict[str, Any]]:
        """Process individual documents from Vespa results"""
        processed_docs = []
        
        for doc in documents:
            try:
                processed_doc = self._process_single_document(doc, include_highlights)
                processed_docs.append(processed_doc)
            except Exception as e:
                logger.warning(f"Error processing document: {e}")
                continue
        
        return processed_docs
    
    def _process_single_document(self, doc: Dict[str, Any], include_highlights: bool) -> Dict[str, Any]:
        """Process a single document"""
        fields = doc.get("fields", {})
        
        processed_doc = {
            "id": fields.get("id"),
            "user_id": fields.get("user_id"),
            "source_type": fields.get("source_type"),
            "provider": fields.get("provider"),
            "title": fields.get("title", ""),
            "content": fields.get("content", ""),
            "created_at": fields.get("created_at"),
            "updated_at": fields.get("updated_at"),
            "relevance_score": doc.get("relevance", 0.0)
        }
        
        # Add highlights if requested
        if include_highlights and "highlights" in doc:
            processed_doc["highlights"] = self._extract_highlights(doc["highlights"])
        
        # Add metadata
        if "metadata" in fields:
            processed_doc["metadata"] = fields["metadata"]
        
        return processed_doc
    
    def _extract_highlights(self, highlights: List[Dict[str, Any]]) -> List[str]:
        """Extract highlight text from Vespa highlights"""
        highlight_texts = []
        
        for highlight in highlights:
            if "value" in highlight:
                highlight_texts.append(highlight["value"])
        
        return highlight_texts
    
    def _process_facets(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process facets from documents"""
        source_types: Dict[str, int] = {}
        providers: Dict[str, int] = {}
        folders: Dict[str, int] = {}
        
        for doc in documents:
            fields = doc.get("fields", {})
            
            # Count source types
            source_type = fields.get("source_type", "unknown")
            source_types[source_type] = source_types.get(source_type, 0) + 1
            
            # Count providers
            provider = fields.get("provider", "unknown")
            providers[provider] = providers.get(provider, 0) + 1
            
            # Count folders
            folder = fields.get("folder", "unknown")
            folders[folder] = folders.get(folder, 0) + 1
        
        return {
            "source_types": source_types,
            "providers": providers,
            "folders": folders
        }
    
    def _extract_performance_metrics(self, vespa_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract performance metrics from Vespa results"""
        performance = vespa_results.get("performance", {})
        
        return {
            "query_time_ms": performance.get("query_time_ms", 0),
            "timestamp": performance.get("timestamp", ""),
            "vespa_timing": vespa_results.get("timing", {})
        }
    
    def _extract_analytics_data(self, vespa_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract analytics data from Vespa results"""
        analytics = {}
        
        # Extract grouping results if available
        if "root" in vespa_results and "children" in vespa_results["root"]:
            children = vespa_results["root"]["children"]
            for child in children:
                if "id" in child and "relevance" in child:
                    analytics[child["id"]] = child["relevance"]
        
        return analytics
    
    def _extract_autocomplete_suggestions(self, documents: List[Dict[str, Any]], query: str) -> List[str]:
        """Extract autocomplete suggestions from documents"""
        suggestions = set()
        
        for doc in documents:
            # Add title suggestions
            title = doc.get("title", "")
            if title and query.lower() in title.lower():
                suggestions.add(title[:self.max_title_length])
            
            # Add content suggestions
            content = doc.get("content", "")
            if content and query.lower() in content.lower():
                # Extract sentence containing query
                sentences = content.split('.')
                for sentence in sentences:
                    if query.lower() in sentence.lower():
                        clean_sentence = sentence.strip()
                        if len(clean_sentence) <= self.default_max_snippet_length:
                            suggestions.add(clean_sentence)
                        else:
                            # Truncate sentence
                            start = clean_sentence.lower().find(query.lower())
                            end = start + len(query)
                            snippet = clean_sentence[max(0, start-50):end+50]
                            suggestions.add(snippet.strip())
                        break
        
        return list(suggestions)[:10]  # Limit to 10 suggestions
    
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
    
    def _create_error_results(self, query: str, user_id: str, error_message: str) -> Dict[str, Any]:
        """Create error results structure"""
        return {
            "query": query,
            "user_id": user_id,
            "total_hits": 0,
            "documents": [],
            "facets": {},
            "performance": {},
            "coverage": {},
            "error": error_message,
            "processed_at": datetime.utcnow().isoformat()
        }
