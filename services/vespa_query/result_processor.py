#!/usr/bin/env python3
"""
Result processor for handling and formatting Vespa search results
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from services.api.v1.vespa.search_models import (
    SearchError,
    SearchFacets,
    SearchPerformance,
    SearchResponse,
    SearchResult,
)
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
        include_facets: bool = True,
    ) -> SearchResponse:
        """Process raw Vespa search results into formatted output"""
        with tracer.start_as_current_span(
            "result_processor.process_search_results"
        ) as span:
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
                total_hits = (
                    vespa_results.get("root", {}).get("fields", {}).get("totalCount", 0)
                )
                coverage = vespa_results.get("root", {}).get("coverage", {})
                span.set_attribute("result.total_hits", total_hits)

                # Process documents
                documents = self._process_documents(
                    vespa_results.get("root", {}).get("children", []),
                    include_highlights,
                )
                span.set_attribute("result.documents_processed", len(documents))

                # Process facets if available
                facets = SearchFacets()
                if include_facets:
                    facets = self._process_facets(
                        vespa_results.get("root", {}).get("children", [])
                    )
                    span.set_attribute("result.facets_count", len(facets.source_types))

                # Process performance metrics
                performance = self._extract_performance_metrics(vespa_results)

                # Create processed results
                processed_results = SearchResponse(
                    query=query,
                    user_id=user_id,
                    total_hits=total_hits,
                    documents=documents,
                    facets=facets,
                    performance=performance,
                    coverage=coverage,
                    processed_at=datetime.utcnow().isoformat(),
                )

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
        self, vespa_results: Dict[str, Any], query: str, user_id: str
    ) -> Dict[str, Any]:
        """Process autocomplete results"""
        try:
            documents = self._process_documents(
                vespa_results.get("root", {}).get("children", []),
                include_highlights=False,
            )

            # Extract suggestions from titles and content
            suggestions = self._extract_autocomplete_suggestions(documents, query)

            return {
                "query": query,
                "user_id": user_id,
                "suggestions": suggestions,
                "total_suggestions": len(suggestions),
                "processed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error processing autocomplete results: {e}")
            return {
                "query": query,
                "user_id": user_id,
                "suggestions": [],
                "total_suggestions": 0,
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat(),
            }

    def process_similarity_results(
        self, vespa_results: Dict[str, Any], query: str, user_id: str
    ) -> Dict[str, Any]:
        """Process similarity search results"""
        try:
            documents = self._process_documents(
                vespa_results.get("root", {}).get("children", []),
                include_highlights=False,
            )

            return {
                "query": query,
                "user_id": user_id,
                "similar_documents": documents,
                "total_similar": len(documents),
                "processed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error processing similarity results: {e}")
            return {
                "query": query,
                "user_id": user_id,
                "similar_documents": [],
                "total_similar": 0,
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat(),
            }

    def process_facets_results(
        self, vespa_results: Dict[str, Any], query: str, user_id: str
    ) -> Dict[str, Any]:
        """Process facets results"""
        try:
            facets = self._process_facets(
                vespa_results.get("root", {}).get("children", [])
            )

            return {
                "query": query,
                "user_id": user_id,
                "facets": facets,
                "total_facets": len(facets.source_types),
                "processed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error processing facets results: {e}")
            return {
                "query": query,
                "user_id": user_id,
                "facets": {},
                "total_facets": 0,
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat(),
            }

    def process_trending_results(
        self, vespa_results: Dict[str, Any], query: str, user_id: str
    ) -> Dict[str, Any]:
        """Process trending results"""
        try:
            documents = self._process_documents(
                vespa_results.get("root", {}).get("children", []),
                include_highlights=False,
            )

            return {
                "query": query,
                "user_id": user_id,
                "trending_documents": documents,
                "total_trending": len(documents),
                "processed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error processing trending results: {e}")
            return {
                "query": query,
                "user_id": user_id,
                "trending_documents": [],
                "total_trending": 0,
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat(),
            }

    def process_analytics_results(
        self, vespa_results: Dict[str, Any], query: str, user_id: str
    ) -> Dict[str, Any]:
        """Process analytics results"""
        try:
            # Extract analytics data
            analytics_data = self._extract_analytics_data(vespa_results)

            return {
                "query": query,
                "user_id": user_id,
                "analytics": analytics_data,
                "processed_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error processing analytics results: {e}")
            return {
                "query": query,
                "user_id": user_id,
                "analytics": {},
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat(),
            }

    def _process_documents(
        self, documents: List[Dict[str, Any]], include_highlights: bool
    ) -> List[SearchResult]:
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

    def _process_single_document(
        self, doc: Dict[str, Any], include_highlights: bool
    ) -> SearchResult:
        """Process a single document"""
        fields = doc.get("fields", {})

        # Extract email-specific fields
        sender = fields.get("sender")
        recipients = fields.get("recipients", [])
        thread_id = fields.get("thread_id")
        folder = fields.get("folder")
        quoted_content = fields.get("quoted_content")
        thread_summary = fields.get("thread_summary", {})

        # Extract calendar-specific fields
        start_time = fields.get("start_time")
        end_time = fields.get("end_time")
        attendees = fields.get("attendees", [])
        location = fields.get("location")
        is_all_day = fields.get("is_all_day", False)
        recurring = fields.get("recurring", False)

        # Extract contact-specific fields
        display_name = fields.get("display_name")
        email_addresses = fields.get("email_addresses", [])
        company = fields.get("company")
        job_title = fields.get("job_title")
        phone_numbers = fields.get("phone_numbers", [])
        address = fields.get("address")

        # Extract document-specific fields
        file_name = fields.get("file_name")
        file_size = fields.get("file_size")
        mime_type = fields.get("mime_type")

        # Extract metadata
        metadata = fields.get("metadata", {})

        # Extract highlights if requested
        highlights = []
        if include_highlights and "highlights" in doc:
            highlights = self._extract_highlights(doc["highlights"])

        return SearchResult(
            id=fields.get("doc_id", ""),  # Fixed: Vespa uses 'doc_id' not 'id'
            user_id=fields.get("user_id", ""),
            source_type=fields.get("source_type", ""),
            provider=fields.get("provider", ""),
            title=fields.get("title", ""),
            content=fields.get("content", ""),
            search_text=fields.get("search_text", ""),
            created_at=fields.get("created_at"),
            updated_at=fields.get("updated_at"),
            relevance_score=doc.get("relevance", 0.0),
            sender=sender,
            recipients=recipients,
            thread_id=thread_id,
            folder=folder,
            quoted_content=quoted_content,
            thread_summary=thread_summary,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
            location=location,
            is_all_day=is_all_day,
            recurring=recurring,
            display_name=display_name,
            email_addresses=email_addresses,
            company=company,
            job_title=job_title,
            phone_numbers=phone_numbers,
            address=address,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            metadata=metadata,
            highlights=highlights,
            snippet=None,
            search_method=None,
            match_confidence=None,
            vector_similarity=None,
            keyword_matches=None,
        )

    def _extract_highlights(self, highlights: List[Dict[str, Any]]) -> List[str]:
        """Extract highlight text from Vespa highlights"""
        highlight_texts = []

        for highlight in highlights:
            if "value" in highlight:
                highlight_texts.append(highlight["value"])

        return highlight_texts

    def _process_facets(self, documents: List[Dict[str, Any]]) -> SearchFacets:
        """Process facets from documents"""
        source_types: Dict[str, int] = {}
        providers: Dict[str, int] = {}
        folders: Dict[str, int] = {}
        date_ranges: Dict[str, int] = {}

        for doc in documents:
            fields = doc.get("fields", {})
            source_type = fields.get("source_type", "unknown")
            source_types[source_type] = source_types.get(source_type, 0) + 1

            # Count providers
            provider = fields.get("provider", "unknown")
            providers[provider] = providers.get(provider, 0) + 1

            # Count folders
            folder = fields.get("folder", "unknown")
            folders[folder] = folders.get(folder, 0) + 1

        return SearchFacets(
            source_types=source_types,
            providers=providers,
            folders=folders,
            date_ranges=date_ranges,
        )

    def _extract_performance_metrics(
        self, vespa_results: Dict[str, Any]
    ) -> SearchPerformance:
        """Extract performance metrics from Vespa results"""
        performance = vespa_results.get("performance", {})
        timing = vespa_results.get("timing", {})

        return SearchPerformance(
            query_time_ms=performance.get("query_time_ms", 0.0),
            total_time_ms=performance.get("total_time_ms", 0.0),
            search_time_ms=timing.get("search_time_ms", 0.0),
            match_time_ms=timing.get("match_time_ms", 0.0),
            fetch_time_ms=timing.get("fetch_time_ms", 0.0),
        )

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

    def _extract_autocomplete_suggestions(
        self, documents: List[SearchResult], query: str
    ) -> List[str]:
        """Extract autocomplete suggestions from documents"""
        suggestions = set()

        for doc in documents:
            # Add title suggestions
            title = doc.title or ""
            if title and query.lower() in title.lower():
                suggestions.add(title[: self.max_title_length])

            # Add content suggestions
            content = doc.content or ""
            if content and query.lower() in content.lower():
                # Extract sentence containing query
                sentences = content.split(".")
                for sentence in sentences:
                    if query.lower() in sentence.lower():
                        clean_sentence = sentence.strip()
                        if len(clean_sentence) <= self.default_max_snippet_length:
                            suggestions.add(clean_sentence)
                        else:
                            # Truncate sentence
                            start = clean_sentence.lower().find(query.lower())
                            end = start + len(query)
                            snippet = clean_sentence[max(0, start - 50) : end + 50]
                            suggestions.add(snippet.strip())
                        break

        return list(suggestions)[:10]  # Limit to 10 suggestions

    def _create_empty_results(self, query: str, user_id: str) -> SearchResponse:
        """Create empty results structure"""
        return SearchResponse(
            query=query,
            user_id=user_id,
            total_hits=0,
            documents=[],
            facets=SearchFacets(),
            performance=SearchPerformance(),
            coverage={},
            processed_at=datetime.utcnow().isoformat(),
        )

    def _create_error_results(
        self, query: str, user_id: str, error_message: str
    ) -> SearchResponse:
        """Create error results structure"""
        return SearchResponse(
            query=query,
            user_id=user_id,
            total_hits=0,
            documents=[],
            facets=SearchFacets(),
            performance=SearchPerformance(),
            coverage={},
            processed_at=datetime.utcnow().isoformat(),
        )
