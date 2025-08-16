#!/usr/bin/env python3
"""
LLM Tools for chat workflows - Enhanced with Vespa search capabilities
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from services.chat.service_client import ServiceClient
from services.vespa_query.search_engine import SearchEngine

logger = logging.getLogger(__name__)

class VespaSearchTool:
    """Tool for searching user data using Vespa"""
    
    def __init__(self, vespa_endpoint: str, user_id: str):
        self.search_engine = SearchEngine(vespa_endpoint)
        self.user_id = user_id
        self.tool_name = "vespa_search"
        self.description = "Search through user's emails, calendar events, contacts, and files using semantic and keyword search"
        
    async def search(self, query: str, max_results: int = 10, 
                    source_types: Optional[List[str]] = None,
                    ranking_profile: str = "hybrid") -> Dict[str, Any]:
        """Search user data using Vespa"""
        try:
            # Build search query
            search_query = {
                "yql": self._build_yql_query(query, source_types),
                "hits": max_results,
                "ranking": ranking_profile,
                "timeout": "5.0s"
            }
            
            # Execute search
            results = await self.search_engine.search(search_query)
            
            # Process results
            processed_results = self._process_search_results(results, query)
            
            return {
                "status": "success",
                "query": query,
                "results": processed_results,
                "total_found": results.get("root", {}).get("fields", {}).get("totalCount", 0),
                "search_time_ms": results.get("performance", {}).get("query_time_ms", 0)
            }
            
        except Exception as e:
            logger.error(f"Vespa search failed: {e}")
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "results": []
            }
    
    def _build_yql_query(self, query: str, source_types: Optional[List[str]] = None) -> str:
        """Build YQL query for Vespa"""
        # Base query with user isolation
        yql = f'select * from briefly_document where user_id contains "{self.user_id}"'
        
        # Add source type filtering
        if source_types:
            source_types_str = '", "'.join(source_types)
            yql += f' and source_type in ("{source_types_str}")'
        
        # Add text search
        yql += f' and (search_text contains "{query}" or title contains "{query}")'
        
        return yql
    
    def _process_search_results(self, results: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """Process and format search results"""
        processed = []
        
        try:
            root = results.get("root", {})
            children = root.get("children", [])
            
            for child in children:
                fields = child.get("fields", {})
                
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
                    "snippet": self._generate_snippet(fields.get("search_text", ""), query)
                }
                
                # Add type-specific fields
                if fields.get("source_type") == "email":
                    result.update({
                        "sender": fields.get("sender"),
                        "recipients": fields.get("recipients", []),
                        "thread_id": fields.get("thread_id"),
                        "folder": fields.get("folder")
                    })
                elif fields.get("source_type") == "calendar":
                    result.update({
                        "start_time": fields.get("start_time"),
                        "end_time": fields.get("end_time"),
                        "attendees": fields.get("attendees", []),
                        "location": fields.get("location")
                    })
                elif fields.get("source_type") == "contact":
                    result.update({
                        "display_name": fields.get("title"),
                        "email_addresses": fields.get("email_addresses", []),
                        "company": fields.get("company"),
                        "job_title": fields.get("job_title")
                    })
                
                processed.append(result)
            
            # Sort by relevance score
            processed.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)
            
        except Exception as e:
            logger.error(f"Error processing search results: {e}")
        
        return processed
    
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
        
    async def search_all_data(self, query: str, max_results: int = 20) -> Dict[str, Any]:
        """Search across all data types with intelligent grouping"""
        try:
            # Search across all source types
            results = await self.vespa_search.search(
                query=query,
                max_results=max_results,
                ranking_profile="hybrid"
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
                "search_time_ms": results["search_time_ms"]
            }
            
        except Exception as e:
            logger.error(f"User data search failed: {e}")
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "grouped_results": {}
            }
    
    def _group_results_by_type(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group search results by data type"""
        grouped = {
            "emails": [],
            "calendar": [],
            "contacts": [],
            "files": [],
            "other": []
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
    
    def _generate_search_summary(self, grouped_results: Dict[str, List[Dict[str, Any]]], query: str) -> Dict[str, Any]:
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
                "other": len(grouped_results["other"])
            },
            "top_results": [],
            "insights": []
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
        
    async def semantic_search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Perform semantic search using vector similarity"""
        try:
            # Build semantic search query
            search_query = {
                "yql": f'select * from briefly_document where user_id contains "{self.user_id}"',
                "hits": max_results,
                "ranking": "semantic",
                "timeout": "5.0s"
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
                "total_found": results.get("root", {}).get("fields", {}).get("totalCount", 0),
                "search_time_ms": results.get("performance", {}).get("query_time_ms", 0)
            }
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "results": []
            }
    
    def _process_semantic_results(self, results: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
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
                    "snippet": self._generate_snippet(fields.get("search_text", ""), query)
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

# Register tools with the chat service
def register_vespa_tools(chat_service: ServiceClient, vespa_endpoint: str, user_id: str):
    """Register Vespa search tools with the chat service"""
    tools = {
        "vespa_search": VespaSearchTool(vespa_endpoint, user_id),
        "user_data_search": UserDataSearchTool(vespa_endpoint, user_id),
        "semantic_search": SemanticSearchTool(vespa_endpoint, user_id)
    }
    
    # Add tools to chat service
    for tool_name, tool in tools.items():
        chat_service.add_tool(tool_name, tool)
    
    logger.info(f"Registered {len(tools)} Vespa search tools for user {user_id}")
    return tools
