#!/usr/bin/env python3
"""
Core search engine for hybrid search capabilities using Vespa
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import aiohttp

from services.common.logging_config import get_logger
from services.common.telemetry import get_tracer

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class SearchEngine:
    """Core search engine for Vespa queries"""

    def __init__(self, vespa_endpoint: str) -> None:
        self.vespa_endpoint = vespa_endpoint.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> None:
        """Start the search engine and create HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        logger.info("Search engine started")

    async def close(self) -> None:
        """Close the search engine and HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("Search engine closed")

    async def test_connection(self) -> bool:
        """Test connection to Vespa"""
        with tracer.start_as_current_span("vespa.test_connection") as span:
            span.set_attribute("vespa.endpoint", self.vespa_endpoint)

            try:
                if not self.session:
                    await self.start()

                if self.session:
                    async with self.session.get(
                        f"{self.vespa_endpoint}/application/v2/status"
                    ) as response:
                        span.set_attribute("vespa.response.status", response.status)

                        if response.status == 200:
                            logger.info("Vespa connection test successful")
                            span.set_attribute("vespa.connection.success", True)
                            return True
                        else:
                            logger.error(
                                f"Vespa connection test failed with status {response.status}"
                            )
                            span.set_attribute("vespa.connection.success", False)
                            span.set_attribute("vespa.error.status", response.status)
                            return False
                return False
            except Exception as e:
                logger.error(f"Vespa connection test failed: {e}")
                span.set_attribute("vespa.connection.success", False)
                span.set_attribute("vespa.error.message", str(e))
                span.record_exception(e)
                return False

    async def search(self, search_query: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a search query"""
        with tracer.start_as_current_span("vespa.search") as span:
            span.set_attribute("vespa.query.type", "search")
            span.set_attribute(
                "vespa.query.ranking", search_query.get("ranking", "unknown")
            )
            span.set_attribute("vespa.query.hits", search_query.get("hits", 0))

            if not self.session:
                await self.start()

            try:
                start_time = time.time()

                # Execute search
                url = f"{self.vespa_endpoint}/search/"
                span.set_attribute("vespa.request.url", url)

                if self.session:
                    async with self.session.post(url, json=search_query) as response:
                        span.set_attribute("vespa.response.status", response.status)

                        if response.status == 200:
                            results = await response.json()

                            # Add performance metrics
                            query_time = time.time() - start_time
                            span.set_attribute(
                                "vespa.query.time_ms", round(query_time * 1000, 2)
                            )

                            results["performance"] = {
                                "query_time_ms": round(query_time * 1000, 2),
                                "timestamp": datetime.utcnow().isoformat(),
                            }

                            logger.info(f"Search query executed in {query_time:.3f}s")
                            span.set_attribute("vespa.search.success", True)
                            return results
                        else:
                            error_text = await response.text()
                            logger.error(
                                f"Search query failed: {response.status} - {error_text}"
                            )
                            span.set_attribute("vespa.search.success", False)
                            span.set_attribute("vespa.error.status", response.status)
                            span.set_attribute("vespa.error.message", error_text)
                            raise Exception(
                                f"Search failed: {response.status} - {error_text}"
                            )
                else:
                    raise Exception("No session available")

            except Exception as e:
                logger.error(f"Error executing search query: {e}")
                span.set_attribute("vespa.search.success", False)
                span.record_exception(e)
                raise

    async def autocomplete(self, autocomplete_query: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an autocomplete query"""
        with tracer.start_as_current_span("vespa.autocomplete") as span:
            span.set_attribute("vespa.query.type", "autocomplete")
            span.set_attribute("vespa.query.text", autocomplete_query.get("query", ""))
            span.set_attribute(
                "vespa.query.user_id", autocomplete_query.get("streaming.groupname", "")
            )
            span.set_attribute("vespa.query.limit", autocomplete_query.get("hits", 10))

            if not self.session:
                await self.start()

            try:
                start_time = time.time()

                url = f"{self.vespa_endpoint}/search/"
                span.set_attribute("vespa.request.url", url)

                if self.session:
                    async with self.session.post(
                        url, json=autocomplete_query
                    ) as response:
                        span.set_attribute("vespa.response.status", response.status)

                        if response.status == 200:
                            results = await response.json()

                            # Add performance metrics
                            query_time = time.time() - start_time
                            span.set_attribute(
                                "vespa.query.time_ms", round(query_time * 1000, 2)
                            )

                            results["performance"] = {
                                "query_time_ms": round(query_time * 1000, 2),
                                "timestamp": datetime.utcnow().isoformat(),
                            }

                            logger.info(
                                f"Autocomplete query executed in {query_time:.3f}s"
                            )
                            span.set_attribute("vespa.autocomplete.success", True)
                            return results
                        else:
                            error_text = await response.text()
                            logger.error(
                                f"Autocomplete query failed: {response.status} - {error_text}"
                            )
                            span.set_attribute("vespa.autocomplete.success", False)
                            span.set_attribute("vespa.error.status", response.status)
                            span.set_attribute("vespa.error.message", error_text)
                            raise Exception(
                                f"Autocomplete failed: {response.status} - {error_text}"
                            )
                else:
                    raise Exception("No session available")

            except Exception as e:
                logger.error(f"Error executing autocomplete query: {e}")
                span.set_attribute("vespa.autocomplete.success", False)
                span.record_exception(e)
                raise

    async def find_similar(self, similarity_query: Dict[str, Any]) -> Dict[str, Any]:
        """Find similar documents"""
        with tracer.start_as_current_span("vespa.find_similar") as span:
            span.set_attribute("vespa.query.type", "similarity")
            span.set_attribute(
                "vespa.document.id",
                (
                    similarity_query.get("yql", "").split('id!="')[1].split('"')[0]
                    if 'id!="' in similarity_query.get("yql", "")
                    else ""
                ),
            )
            span.set_attribute(
                "vespa.query.user_id", similarity_query.get("streaming.groupname", "")
            )
            span.set_attribute("vespa.query.limit", similarity_query.get("hits", 10))

            if not self.session:
                await self.start()

            try:
                start_time = time.time()

                url = f"{self.vespa_endpoint}/search/"
                span.set_attribute("vespa.request.url", url)

                if self.session:
                    async with self.session.post(
                        url, json=similarity_query
                    ) as response:
                        span.set_attribute("vespa.response.status", response.status)

                        if response.status == 200:
                            results = await response.json()

                            # Add performance metrics
                            query_time = time.time() - start_time
                            span.set_attribute(
                                "vespa.query.time_ms", round(query_time * 1000, 2)
                            )

                            results["performance"] = {
                                "query_time_ms": round(query_time * 1000, 2),
                                "timestamp": datetime.utcnow().isoformat(),
                            }

                            logger.info(
                                f"Similarity query executed in {query_time:.3f}s"
                            )
                            span.set_attribute("vespa.similarity.success", True)
                            return results
                        else:
                            error_text = await response.text()
                            logger.error(
                                f"Similarity query failed: {response.status} - {error_text}"
                            )
                            span.set_attribute("vespa.similarity.success", False)
                            span.set_attribute("vespa.error.status", response.status)
                            span.set_attribute("vespa.error.message", error_text)
                            raise Exception(
                                f"Similarity search failed: {response.status} - {error_text}"
                            )
                else:
                    raise Exception("No session available")

            except Exception as e:
                logger.error(f"Error executing similarity query: {e}")
                span.set_attribute("vespa.similarity.success", False)
                span.record_exception(e)
                raise

    async def get_facets(self, facets_query: Dict[str, Any]) -> Dict[str, Any]:
        """Get facet information for documents"""
        with tracer.start_as_current_span("vespa.get_facets") as span:
            span.set_attribute("vespa.query.type", "facets")
            span.set_attribute(
                "vespa.query.user_id", facets_query.get("streaming.groupname", "")
            )

            if not self.session:
                await self.start()

            try:
                start_time = time.time()

                url = f"{self.vespa_endpoint}/search/"
                span.set_attribute("vespa.request.url", url)

                if self.session:
                    async with self.session.post(url, json=facets_query) as response:
                        span.set_attribute("vespa.response.status", response.status)

                        if response.status == 200:
                            results = await response.json()

                            # Add performance metrics
                            query_time = time.time() - start_time
                            span.set_attribute(
                                "vespa.query.time_ms", round(query_time * 1000, 2)
                            )

                            results["performance"] = {
                                "query_time_ms": round(query_time * 1000, 2),
                                "timestamp": datetime.utcnow().isoformat(),
                            }

                            logger.info(f"Facets query executed in {query_time:.3f}s")
                            span.set_attribute("vespa.facets.success", True)
                            return results
                        else:
                            error_text = await response.text()
                            logger.error(
                                f"Facets query failed: {response.status} - {error_text}"
                            )
                            span.set_attribute("vespa.facets.success", False)
                            span.set_attribute("vespa.error.status", response.status)
                            span.set_attribute("vespa.error.message", error_text)
                            raise Exception(
                                f"Facets query failed: {response.status} - {error_text}"
                            )
                else:
                    raise Exception("No session available")

            except Exception as e:
                logger.error(f"Error executing facets query: {e}")
                span.set_attribute("vespa.facets.success", False)
                span.record_exception(e)
                raise

    async def get_trending(self, trending_query: Dict[str, Any]) -> Dict[str, Any]:
        """Get trending documents"""
        with tracer.start_as_current_span("vespa.get_trending") as span:
            span.set_attribute("vespa.query.type", "trending")
            span.set_attribute(
                "vespa.query.user_id", trending_query.get("streaming.groupname", "")
            )
            span.set_attribute(
                "vespa.query.time_range",
                trending_query.get("ranking.features.query(timeDecay)", "7d"),
            )
            span.set_attribute("vespa.query.limit", trending_query.get("hits", 10))

            if not self.session:
                await self.start()

            try:
                start_time = time.time()

                url = f"{self.vespa_endpoint}/search/"
                span.set_attribute("vespa.request.url", url)

                if self.session:
                    async with self.session.post(url, json=trending_query) as response:
                        span.set_attribute("vespa.response.status", response.status)

                        if response.status == 200:
                            results = await response.json()

                            # Add performance metrics
                            query_time = time.time() - start_time
                            span.set_attribute(
                                "vespa.query.time_ms", round(query_time * 1000, 2)
                            )

                            results["performance"] = {
                                "query_time_ms": round(query_time * 1000, 2),
                                "timestamp": datetime.utcnow().isoformat(),
                            }

                            logger.info(f"Trending query executed in {query_time:.3f}s")
                            span.set_attribute("vespa.trending.success", True)
                            return results
                        else:
                            error_text = await response.text()
                            logger.error(
                                f"Trending query failed: {response.status} - {error_text}"
                            )
                            span.set_attribute("vespa.trending.success", False)
                            span.set_attribute("vespa.error.status", response.status)
                            span.set_attribute("vespa.error.message", error_text)
                            raise Exception(
                                f"Trending query failed: {response.status} - {error_text}"
                            )
                else:
                    raise Exception("No session available")

            except Exception as e:
                logger.error(f"Error executing trending query: {e}")
                span.set_attribute("vespa.trending.success", False)
                span.record_exception(e)
                raise

    async def get_analytics(self, analytics_query: Dict[str, Any]) -> Dict[str, Any]:
        """Get analytics data for documents"""
        with tracer.start_as_current_span("vespa.get_analytics") as span:
            span.set_attribute("vespa.query.type", "analytics")
            span.set_attribute(
                "vespa.query.user_id", analytics_query.get("streaming.groupname", "")
            )

            if not self.session:
                await self.start()

            try:
                start_time = time.time()

                url = f"{self.vespa_endpoint}/search/"
                span.set_attribute("vespa.request.url", url)

                if self.session:
                    async with self.session.post(url, json=analytics_query) as response:
                        span.set_attribute("vespa.response.status", response.status)

                        if response.status == 200:
                            results = await response.json()

                            # Add performance metrics
                            query_time = time.time() - start_time
                            span.set_attribute(
                                "vespa.query.time_ms", round(query_time * 1000, 2)
                            )

                            results["performance"] = {
                                "query_time_ms": round(query_time * 1000, 2),
                                "timestamp": datetime.utcnow().isoformat(),
                            }

                            logger.info(
                                f"Analytics query executed in {query_time:.3f}s"
                            )
                            span.set_attribute("vespa.analytics.success", True)
                            return results
                        else:
                            error_text = await response.text()
                            logger.error(
                                f"Analytics query failed: {response.status} - {error_text}"
                            )
                            span.set_attribute("vespa.analytics.success", False)
                            span.set_attribute("vespa.error.status", response.status)
                            span.set_attribute("vespa.error.message", error_text)
                            raise Exception(
                                f"Analytics query failed: {response.status} - {error_text}"
                            )
                else:
                    raise Exception("No session available")

            except Exception as e:
                logger.error(f"Error executing analytics query: {e}")
                span.set_attribute("vespa.analytics.success", False)
                span.record_exception(e)
                raise

    async def batch_search(self, queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute multiple search queries in batch"""
        if not queries:
            return []

        try:
            # Execute queries in parallel
            tasks = []
            for query in queries:
                task = self.search(query)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and handle errors
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Query {i} failed: {result}")
                    processed_results.append(
                        {"index": i, "status": "error", "error": str(result)}
                    )
                else:
                    processed_results.append(
                        {"index": i, "status": "success", "result": result}
                    )

            return processed_results

        except Exception as e:
            logger.error(f"Error in batch search: {e}")
            raise

    def get_search_stats(self) -> Dict[str, Any]:
        """Get search engine statistics"""
        return {
            "vespa_endpoint": self.vespa_endpoint,
            "session_active": self.session is not None,
            "timestamp": datetime.utcnow().isoformat(),
        }
