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

# Global draft storage for in-memory draft management
# This is used by the workflow system to maintain draft state during conversations
_draft_storage: Dict[str, Dict[str, Any]] = {}

# Draft management functions
def create_draft_email(thread_id: str, to: Optional[str], subject: Optional[str], body: Optional[str], **kwargs: Any) -> Dict[str, Any]:
    """Create a draft email for the given thread."""
    try:
        key = f"{thread_id}_email"
        email_data = {
            "to": to or "",
            "subject": subject or "",
            "body": body or "",
            **kwargs
        }
        _draft_storage[key] = email_data
        logger.info(f"📧 Created email draft for thread {thread_id}")
        return {"success": True, "draft_id": key}
    except Exception as e:
        logger.error(f"Failed to create email draft: {e}")
        return {"success": False, "error": str(e)}

def create_draft_calendar_event(thread_id: str, title: Optional[str], start_time: Optional[str], end_time: Optional[str], attendees: Optional[str], location: Optional[str], description: Optional[str], **kwargs: Any) -> Dict[str, Any]:
    """Create a draft calendar event for the given thread."""
    try:
        key = f"{thread_id}_calendar_event"
        event_data = {
            "title": title or "",
            "start_time": start_time or "",
            "end_time": end_time or "",
            "attendees": attendees or "",
            "location": location or "",
            "description": description or "",
            **kwargs
        }
        _draft_storage[key] = event_data
        logger.info(f"📅 Created calendar event draft for thread {thread_id}")
        return {"success": True, "draft_id": key}
    except Exception as e:
        logger.error(f"Failed to create calendar event draft: {e}")
        return {"success": False, "error": str(e)}

def create_draft_calendar_change(thread_id: str, event_id: Optional[str], change_type: Optional[str], new_title: Optional[str], new_start_time: Optional[str], new_end_time: Optional[str], new_attendees: Optional[str], new_location: Optional[str], new_description: Optional[str], **kwargs: Any) -> Dict[str, Any]:
    """Create a draft calendar change for the given thread."""
    try:
        key = f"{thread_id}_calendar_edit"
        change_data = {
            "event_id": event_id or "",
            "change_type": change_type or "",
            "new_title": new_title or "",
            "new_start_time": new_start_time or "",
            "new_end_time": new_end_time or "",
            "new_attendees": new_attendees or "",
            "new_location": new_location or "",
            "new_description": new_description or "",
            **kwargs
        }
        _draft_storage[key] = change_data
        logger.info(f"✏️ Created calendar edit draft for thread {thread_id}")
        return {"success": True, "draft_id": key}
    except Exception as e:
        logger.error(f"Failed to create calendar edit draft: {e}")
        return {"success": False, "error": str(e)}

def get_draft_email(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get the email draft for the given thread."""
    key = f"{thread_id}_email"
    return _draft_storage.get(key)

def get_draft_calendar_event(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get the calendar event draft for the given thread."""
    key = f"{thread_id}_calendar_event"
    return _draft_storage.get(key)

def has_draft_email(thread_id: str) -> Dict[str, Any]:
    """Check if there's an email draft for the given thread."""
    key = f"{thread_id}_email"
    exists = key in _draft_storage
    return {"exists": exists, "draft_id": key if exists else None}

def has_draft_calendar_event(thread_id: str) -> Dict[str, Any]:
    """Check if there's a calendar event draft for the given thread."""
    key = f"{thread_id}_calendar_event"
    exists = key in _draft_storage
    return {"exists": exists, "draft_id": key if exists else None}

def has_draft_calendar_edit(thread_id: str) -> Dict[str, Any]:
    """Check if there's a calendar edit draft for the given thread."""
    key = f"{thread_id}_calendar_edit"
    exists = key in _draft_storage
    return {"exists": exists, "draft_id": key if exists else None}

def delete_draft_email(thread_id: str) -> Dict[str, Any]:
    """Delete the email draft for the given thread."""
    try:
        key = f"{thread_id}_email"
        if key in _draft_storage:
            del _draft_storage[key]
            logger.info(f"🗑️ Deleted email draft for thread {thread_id}")
            return {"success": True, "deleted": True}
        return {"success": True, "deleted": False, "message": "No email draft found"}
    except Exception as e:
        logger.error(f"Failed to delete email draft: {e}")
        return {"success": False, "error": str(e)}

def delete_draft_calendar_event(thread_id: str) -> Dict[str, Any]:
    """Delete the calendar event draft for the given thread."""
    try:
        key = f"{thread_id}_calendar_event"
        if key in _draft_storage:
            del _draft_storage[key]
            logger.info(f"🗑️ Deleted calendar event draft for thread {thread_id}")
            return {"success": True, "deleted": True}
        return {"success": True, "deleted": False, "message": "No calendar event draft found"}
    except Exception as e:
        logger.error(f"Failed to delete calendar event draft: {e}")
        return {"success": False, "error": str(e)}

def delete_draft_calendar_edit(thread_id: str) -> Dict[str, Any]:
    """Delete the calendar edit draft for the given thread."""
    try:
        key = f"{thread_id}_calendar_edit"
        if key in _draft_storage:
            del _draft_storage[key]
            logger.info(f"🗑️ Deleted calendar edit draft for thread {thread_id}")
            return {"success": True, "deleted": True}
        return {"success": True, "deleted": False, "message": "No calendar edit draft found"}
    except Exception as e:
        logger.error(f"Failed to delete calendar edit draft: {e}")
        return {"success": False, "error": str(e)}

def clear_all_drafts(thread_id: str) -> Dict[str, Any]:
    """Clear all drafts for the given thread."""
    try:
        thread_prefix = f"{thread_id}_"
        keys_to_remove = [
            key for key in _draft_storage.keys() if key.startswith(thread_prefix)
        ]
        
        for key in keys_to_remove:
            del _draft_storage[key]
        
        logger.info(f"🗑️ Cleared {len(keys_to_remove)} drafts for thread {thread_id}")
        return {"success": True, "cleared_count": len(keys_to_remove)}
    except Exception as e:
        logger.error(f"Failed to clear drafts: {e}")
        return {"success": False, "error": str(e)}

# Document and note retrieval functions
async def get_documents(
    user_id: str,
    document_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search_query: Optional[str] = None,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get documents from the office service.
    
    Args:
        user_id: User ID to get documents for
        document_type: Type of document to filter by (optional)
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        search_query: Search query to filter documents (optional)
        max_results: Maximum number of results to return (optional)
    
    Returns:
        Dict containing documents or error information
    """
    try:
        # Import here to avoid circular imports
        from services.chat.service_client import ServiceClient
        from services.chat.settings import get_settings
        
        # Create service client
        settings = get_settings()
        client = ServiceClient()
        
        # Build query parameters
        params: Dict[str, Any] = {
            "user_id": user_id,
        }
        
        if document_type:
            params["document_type"] = document_type
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if search_query:
            params["search_query"] = search_query
        if max_results:
            params["limit"] = str(max_results)
        
        # Make request to office service
        async with client as http_client:
            response = await http_client.http_client.get(
                f"{settings.office_service_url}/v1/documents",
                params=params,
                headers=client._get_headers_for_service("office")
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "documents": data.get("data", []),
                    "total_count": len(data.get("data", [])),
                    "user_id": user_id,
                    "query_params": params
                }
            else:
                logger.error(f"Failed to get documents: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "user_id": user_id
                }
            
    except Exception as e:
        logger.error(f"Error getting documents for user {user_id}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id
        }

async def get_notes(
    user_id: str,
    notebook: Optional[str] = None,
    tags: Optional[str] = None,
    search_query: Optional[str] = None,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get notes from the office service.
    
    Args:
        user_id: User ID to get notes for
        notebook: Notebook to filter by (optional)
        tags: Tags to filter by (optional)
        search_query: Search query to filter notes (optional)
        max_results: Maximum number of results to return (optional)
    
    Returns:
        Dict containing notes or error information
    """
    try:
        # Import here to avoid circular imports
        from services.chat.service_client import ServiceClient
        from services.chat.settings import get_settings
        
        # Create service client
        settings = get_settings()
        client = ServiceClient()
        
        # Build query parameters
        params: Dict[str, Any] = {
            "user_id": user_id,
        }
        
        if notebook:
            params["notebook"] = notebook
        if tags:
            params["tags"] = tags
        if search_query:
            params["search_query"] = search_query
        if max_results:
            params["limit"] = str(max_results)
        
        # Make request to office service
        async with client as http_client:
            response = await http_client.http_client.get(
                f"{settings.office_service_url}/v1/notes",
                params=params,
                headers=client._get_headers_for_service("office")
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "notes": data.get("data", []),
                    "total_count": len(data.get("data", [])),
                    "user_id": user_id,
                    "query_params": params
                }
            else:
                logger.error(f"Failed to get notes: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "user_id": user_id
                }
            
    except Exception as e:
        logger.error(f"Error getting notes for user {user_id}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id
        }

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
                "timeout": "5.0s",
                "streaming.groupname": self.user_id  # Add streaming mode support for user isolation
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
        grouped: Dict[str, List[Dict[str, Any]]] = {
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
                "timeout": "5.0s",
                "streaming.groupname": self.user_id  # Add streaming mode support for user isolation
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
def register_vespa_tools(chat_service: ServiceClient, vespa_endpoint: str, user_id: str) -> None:
    """Register Vespa search tools with the chat service"""
    tools = {
        "vespa_search": VespaSearchTool(vespa_endpoint, user_id),
        "user_data_search": UserDataSearchTool(vespa_endpoint, user_id),
        "semantic_search": SemanticSearchTool(vespa_endpoint, user_id)
    }
    
    # Note: ServiceClient doesn't have add_tool method, tools are registered differently
    # This function is kept for compatibility but doesn't actually register tools
    logger.info(f"Vespa search tools created for user {user_id} (registration handled by caller)")


async def get_calendar_events(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    time_zone: str = "UTC",
    providers: Optional[List[str]] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get calendar events for a user from the office service.
    
    Args:
        user_id: User ID to get calendar events for
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        time_zone: Timezone for date filtering (default: UTC)
        providers: List of calendar providers to query (optional)
        limit: Maximum number of events to return (default: 50)
    
    Returns:
        Dict containing calendar events or error information
    """
    try:
        # Import here to avoid circular imports
        from services.chat.service_client import ServiceClient
        from services.chat.settings import get_settings
        
        # Create service client
        settings = get_settings()
        client = ServiceClient()
        
        # Build query parameters
        params: Dict[str, Any] = {
            "user_id": user_id,
            "limit": limit
        }
        
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if time_zone and time_zone != "UTC":
            params["timezone"] = time_zone
        if providers:
            params["providers"] = ",".join(providers)
        
        # Make request to office service
        async with client as http_client:
            response = await http_client.http_client.get(
                f"{settings.office_service_url}/v1/calendar/events",
                params=params,
                headers=client._get_headers_for_service("office")
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "events": data.get("data", []),
                    "total_count": len(data.get("data", [])),
                    "user_id": user_id,
                    "query_params": params
                }
            else:
                logger.error(f"Failed to get calendar events: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "user_id": user_id
                }
            
    except Exception as e:
        logger.error(f"Error getting calendar events for user {user_id}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id
        }

# Email retrieval function
async def get_emails(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    folder: Optional[str] = None,
    unread_only: Optional[bool] = None,
    search_query: Optional[str] = None,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get emails from the office service.
    
    Args:
        user_id: User ID to get emails for
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        folder: Folder to filter by (optional)
        unread_only: Whether to return only unread emails (optional)
        search_query: Search query to filter emails (optional)
        max_results: Maximum number of results to return (optional)
    
    Returns:
        Dict containing emails or error information
    """
    try:
        # Import here to avoid circular imports
        from services.chat.service_client import ServiceClient
        from services.chat.settings import get_settings
        
        # Create service client
        settings = get_settings()
        client = ServiceClient()
        
        # Build query parameters
        params: Dict[str, Any] = {
            "user_id": user_id,
        }
        
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if folder:
            params["folder"] = folder
        if unread_only is not None:
            params["unread_only"] = str(unread_only).lower()
        if search_query:
            params["search_query"] = search_query
        if max_results:
            params["limit"] = str(max_results)
        
        # Make request to office service
        async with client as http_client:
            response = await http_client.http_client.get(
                f"{settings.office_service_url}/v1/emails",
                params=params,
                headers=client._get_headers_for_service("office")
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "emails": data.get("data", []),
                    "total_count": len(data.get("data", [])),
                    "user_id": user_id,
                    "query_params": params
                }
            else:
                logger.error(f"Failed to get emails: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "user_id": user_id
                }
            
    except Exception as e:
        logger.error(f"Error getting emails for user {user_id}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "user_id": user_id
        }

# Tool Registry for executing various tools
class ToolRegistry:
    """Registry for executing various tools and functions."""
    
    def __init__(self) -> None:
        pass
    
    async def execute_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Execute a tool by name with the given arguments."""
        try:
            if tool_name == "get_calendar_events":
                user_id = kwargs.get("user_id")
                if not user_id:
                    return type('ToolOutput', (), {'raw_output': {"error": "user_id is required"}})()
                
                # Import here to avoid circular imports
                from services.chat.agents.llm_tools import get_calendar_events
                result = await get_calendar_events(
                    user_id=user_id,
                    start_date=kwargs.get("start_date"),
                    end_date=kwargs.get("end_date"),
                    time_zone=kwargs.get("time_zone", "UTC"),
                    providers=kwargs.get("providers"),
                    limit=kwargs.get("limit", 50)
                )
                return type('ToolOutput', (), {'raw_output': result})()
                
            elif tool_name == "get_emails":
                user_id = kwargs.get("user_id")
                if not user_id:
                    return type('ToolOutput', (), {'raw_output': {"error": "user_id is required"}})()
                
                # Import here to avoid circular imports
                from services.chat.agents.llm_tools import get_emails
                result = await get_emails(
                    user_id=user_id,
                    start_date=kwargs.get("start_date"),
                    end_date=kwargs.get("end_date"),
                    folder=kwargs.get("folder"),
                    unread_only=kwargs.get("unread_only"),
                    search_query=kwargs.get("search_query"),
                    max_results=kwargs.get("max_results")
                )
                return type('ToolOutput', (), {'raw_output': result})()
                
            else:
                return type('ToolOutput', (), {'raw_output': {"error": f"Unknown tool: {tool_name}"}})()
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return type('ToolOutput', (), {'raw_output': {"error": str(e)}})()

# Global tool registry instance
_tool_registry_instance = None

def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance (singleton)."""
    global _tool_registry_instance
    if _tool_registry_instance is None:
        _tool_registry_instance = ToolRegistry()
    return _tool_registry_instance
