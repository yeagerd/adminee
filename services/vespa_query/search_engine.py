#!/usr/bin/env python3
"""
Core search engine for hybrid search capabilities using Vespa
"""

import aiohttp
from typing import Dict, Any, Optional, List
import json
from datetime import datetime
import time
from services.common.logging_config import get_logger
from services.common.telemetry import get_tracer

logger = get_logger(__name__)
tracer = get_tracer(__name__)

class SearchEngine:
    """Core search engine for Vespa queries"""
    
    def __init__(self, vespa_endpoint: str):
        self.vespa_endpoint = vespa_endpoint.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def start(self):
        """Start the search engine and create HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        logger.info("Search engine started")
    
    async def close(self):
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
                
                async with self.session.get(f"{self.vespa_endpoint}/application/v2/status") as response:
                    span.set_attribute("vespa.response.status", response.status)
                    
                    if response.status == 200:
                        logger.info("Vespa connection test successful")
                        span.set_attribute("vespa.connection.success", True)
                        return True
                    else:
                        logger.error(f"Vespa connection test failed with status {response.status}")
                        span.set_attribute("vespa.connection.success", False)
                        span.set_attribute("vespa.error.status", response.status)
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
            span.set_attribute("vespa.query.ranking", search_query.get("ranking", "unknown"))
            span.set_attribute("vespa.query.hits", search_query.get("hits", 0))
            
            if not self.session:
                await self.start()
            
            try:
                start_time = time.time()
                
                # Execute search
                url = f"{self.vespa_endpoint}/search/"
                span.set_attribute("vespa.request.url", url)
                
                async with self.session.post(url, json=search_query) as response:
                    span.set_attribute("vespa.response.status", response.status)
                    
                    if response.status == 200:
                        results = await response.json()
                        
                        # Add performance metrics
                        query_time = time.time() - start_time
                        span.set_attribute("vespa.query.time_ms", round(query_time * 1000, 2))
                        
                        results["performance"] = {
                            "query_time_ms": round(query_time * 1000, 2),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
                        logger.info(f"Search query executed in {query_time:.3f}s")
                        span.set_attribute("vespa.search.success", True)
                        return results
                    else:
                        error_text = await response.text()
                        logger.error(f"Search query failed: {response.status} - {error_text}")
                        span.set_attribute("vespa.search.success", False)
                        span.set_attribute("vespa.error.status", response.status)
                        span.set_attribute("vespa.error.message", error_text)
                        raise Exception(f"Search failed: {response.status} - {error_text}")
                        
            except Exception as e:
                logger.error(f"Error executing search query: {e}")
                span.set_attribute("vespa.search.success", False)
                span.set_attribute("vespa.error.message", str(e))
                span.record_exception(e)
                raise
    
    async def autocomplete(self, autocomplete_query: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an autocomplete query"""
        if not self.session:
            await self.start()
        
        try:
            start_time = time.time()
            
            # Execute autocomplete search
            url = f"{self.vespa_endpoint}/search/"
            async with self.session.post(url, json=autocomplete_query) as response:
                if response.status == 200:
                    results = await response.json()
                    
                    # Add performance metrics
                    query_time = time.time() - start_time
                    results["performance"] = {
                        "query_time_ms": round(query_time * 1000, 2),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    logger.info(f"Autocomplete query executed in {query_time:.3f}s")
                    return results
                else:
                    error_text = await response.text()
                    logger.error(f"Autocomplete query failed: {response.status} - {error_text}")
                    raise Exception(f"Autocomplete failed: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error executing autocomplete query: {e}")
            raise
    
    async def find_similar(self, similarity_query: Dict[str, Any]) -> Dict[str, Any]:
        """Find similar documents using vector similarity"""
        if not self.session:
            await self.start()
        
        try:
            start_time = time.time()
            
            # Execute similarity search
            url = f"{self.vespa_endpoint}/search/"
            async with self.session.post(url, json=similarity_query) as response:
                if response.status == 200:
                    results = await response.json()
                    
                    # Add performance metrics
                    query_time = time.time() - start_time
                    results["performance"] = {
                        "query_time_ms": round(query_time * 1000, 2),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    logger.info(f"Similarity search executed in {query_time:.3f}s")
                    return results
                else:
                    error_text = await response.text()
                    logger.error(f"Similarity search failed: {response.status} - {error_text}")
                    raise Exception(f"Similarity search failed: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error executing similarity search: {e}")
            raise
    
    async def get_facets(self, facets_query: Dict[str, Any]) -> Dict[str, Any]:
        """Get faceted search results"""
        if not self.session:
            await self.start()
        
        try:
            start_time = time.time()
            
            # Execute facets search
            url = f"{self.vespa_endpoint}/search/"
            async with self.session.post(url, json=facets_query) as response:
                if response.status == 200:
                    results = await response.json()
                    
                    # Add performance metrics
                    query_time = time.time() - start_time
                    results["performance"] = {
                        "query_time_ms": round(query_time * 1000, 2),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    logger.info(f"Facets search executed in {query_time:.3f}s")
                    return results
                else:
                    error_text = await response.text()
                    logger.error(f"Facets search failed: {response.status} - {error_text}")
                    raise Exception(f"Facets search failed: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error executing facets search: {e}")
            raise
    
    async def get_trending(self, trending_query: Dict[str, Any]) -> Dict[str, Any]:
        """Get trending topics based on recent activity"""
        if not self.session:
            await self.start()
        
        try:
            start_time = time.time()
            
            # Execute trending search
            url = f"{self.vespa_endpoint}/search/"
            async with self.session.post(url, json=trending_query) as response:
                if response.status == 200:
                    results = await response.json()
                    
                    # Add performance metrics
                    query_time = time.time() - start_time
                    results["performance"] = {
                        "query_time_ms": round(query_time * 1000, 2),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    logger.info(f"Trending search executed in {query_time:.3f}s")
                    return results
                else:
                    error_text = await response.text()
                    logger.error(f"Trending search failed: {response.status} - {error_text}")
                    raise Exception(f"Trending search failed: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error executing trending search: {e}")
            raise
    
    async def get_analytics(self, analytics_query: Dict[str, Any]) -> Dict[str, Any]:
        """Get search analytics and insights"""
        if not self.session:
            await self.start()
        
        try:
            start_time = time.time()
            
            # Execute analytics search
            url = f"{self.vespa_endpoint}/search/"
            async with self.session.post(url, json=analytics_query) as response:
                if response.status == 200:
                    results = await response.json()
                    
                    # Add performance metrics
                    query_time = time.time() - start_time
                    results["performance"] = {
                        "query_time_ms": round(query_time * 1000, 2),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    logger.info(f"Analytics search executed in {query_time:.3f}s")
                    return results
                else:
                    error_text = await response.text()
                    logger.error(f"Analytics search failed: {response.status} - {error_text}")
                    raise Exception(f"Analytics search failed: {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"Error executing analytics search: {e}")
            raise
    
    async def batch_search(self, search_queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute multiple search queries in batch"""
        if not self.session:
            await self.start()
        
        try:
            start_time = time.time()
            results = []
            
            # Execute queries concurrently
            import asyncio
            tasks = [self.search(query) for query in search_queries]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch search query {i} failed: {result}")
                    results.append({
                        "error": str(result),
                        "query_index": i
                    })
                else:
                    results.append(result)
            
            # Add batch performance metrics
            batch_time = time.time() - start_time
            for result in results:
                if "performance" in result:
                    result["performance"]["batch_time_ms"] = round(batch_time * 1000, 2)
            
            logger.info(f"Batch search completed in {batch_time:.3f}s for {len(search_queries)} queries")
            return results
            
        except Exception as e:
            logger.error(f"Error executing batch search: {e}")
            raise
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get search engine statistics"""
        return {
            "vespa_endpoint": self.vespa_endpoint,
            "session_active": self.session is not None,
            "timestamp": datetime.utcnow().isoformat()
        }
