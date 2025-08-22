"""
Get tools for service API access with pre-authenticated user context.

This module provides dynamic tool discovery and execution capabilities.
"""

import logging
from typing import Any, Dict, List, Optional

import requests

from services.chat.settings import get_settings
from services.chat.tools.tool_registry import ToolMetadata, ToolRegistry as EnhancedToolRegistry
from services.chat.tools.data_tools import DataTools
from services.chat.tools.draft_tools import DraftTools
from services.chat.tools.search_tools import SearchTools
from services.chat.tools.web_tools import WebTools
from services.chat.tools.utility_tools import UtilityTools

logger = logging.getLogger(__name__)


class GetTool:
    """Generic tool gateway backed by Enhanced ToolRegistry.

    Allows the LLM to discover and invoke available tools dynamically.
    """

    def __init__(self, registry: EnhancedToolRegistry, default_user_id: str):
        self.registry = registry
        self.default_user_id = default_user_id
        self.tool_name = "get_tool"
        self.description = (
            "Execute a named tool (e.g., get_calendar_events, get_emails) with params"
        )

    def list_tools(self) -> Dict[str, Any]:
        """List available tools for discovery."""
        try:
            tools_list = self.registry.list_tools()
            return {"status": "success", "tools": tools_list}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_tool_info(self, tool_id: str) -> Dict[str, Any]:
        """Get complete API specification for a tool."""
        try:
            tool_info = self.registry.get_tool_info(tool_id)
            if tool_info:
                return {
                    "status": "success",
                    "tool_info": tool_info.to_dict()
                }
            else:
                return {
                    "status": "error",
                    "error": f"Tool not found: {tool_id}"
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def execute(
        self, tool_name: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a tool by name with parameters."""
        try:
            kwargs = params.copy() if params else {}
            
            # All tools are pre-bound with user context, no user_id injection needed
            result = self.registry.execute_tool(tool_name, **kwargs)
            return {"status": "success", "tool": tool_name, "result": result}
        except Exception as e:
            logger.error(f"GetTool execute failed for {tool_name}: {e}")
            return {"status": "error", "tool": tool_name, "error": str(e)}


class GetTools:
    """Collection of get tools with pre-authenticated user context."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.registry = EnhancedToolRegistry()
        self.get_tool = GetTool(registry=self.registry, default_user_id=user_id)
        
        # Initialize tool classes
        self.data_tools = DataTools(user_id)
        self.draft_tools = DraftTools(user_id)
        self.search_tools = SearchTools("", user_id)  # Empty vespa_endpoint for now
        self.web_tools = WebTools()
        self.utility_tools = UtilityTools()
        
        # Register all tools with the enhanced registry
        self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all tools with the enhanced registry."""
        # Register get_calendar_events
        calendar_metadata = ToolMetadata(
            tool_id="get_calendar_events",
            description="Get calendar events for a user from the office service",
            category="data_retrieval",
            parameters={
                "start_date": {"type": "str", "description": "Start date in YYYY-MM-DD format", "required": False},
                "end_date": {"type": "str", "description": "End date in YYYY-MM-DD format", "required": False},
                "time_zone": {"type": "str", "description": "Timezone for date filtering", "required": False, "default": "UTC"},
                "providers": {"type": "list", "description": "List of calendar providers to query", "required": False},
                "limit": {"type": "int", "description": "Maximum number of events to return", "required": False, "default": 50}
            },
            examples=[
                {"description": "Get today's events", "params": {"start_date": "2024-01-15", "end_date": "2024-01-15"}},
                {"description": "Get events from specific providers", "params": {"providers": ["google", "outlook"]}}
            ],
            return_format={
                "status": "success/error",
                "events": "List of calendar events",
                "total_count": "Number of events returned",
                "user_id": "User ID queried"
            },
            requires_auth=True,
            service_dependency="office_service"
        )
        self.registry.register_tool(calendar_metadata, self.data_tools.get_calendar_events)
        
        # Register get_emails
        emails_metadata = ToolMetadata(
            tool_id="get_emails",
            description="Get emails from the office service",
            category="data_retrieval",
            parameters={
                "start_date": {"type": "str", "description": "Start date in YYYY-MM-DD format", "required": False},
                "end_date": {"type": "str", "description": "End date in YYYY-MM-DD format", "required": False},
                "folder": {"type": "str", "description": "Folder to filter by", "required": False},
                "unread_only": {"type": "bool", "description": "Whether to return only unread emails", "required": False},
                "search_query": {"type": "str", "description": "Search query to filter emails", "required": False},
                "max_results": {"type": "int", "description": "Maximum number of results to return", "required": False}
            },
            examples=[
                {"description": "Get unread emails", "params": {"unread_only": True}},
                {"description": "Search emails with query", "params": {"search_query": "meeting"}}
            ],
            return_format={
                "status": "success/error",
                "emails": "List of emails",
                "total_count": "Number of emails returned",
                "user_id": "User ID queried"
            },
            requires_auth=True,
            service_dependency="office_service"
        )
        self.registry.register_tool(emails_metadata, self.data_tools.get_emails)
        
        # Register get_notes
        notes_metadata = ToolMetadata(
            tool_id="get_notes",
            description="Get notes from the office service",
            category="data_retrieval",
            parameters={
                "notebook": {"type": "str", "description": "Notebook to filter by", "required": False},
                "tags": {"type": "str", "description": "Tags to filter by", "required": False},
                "search_query": {"type": "str", "description": "Search query to filter notes", "required": False},
                "max_results": {"type": "int", "description": "Maximum number of results to return", "required": False}
            },
            examples=[
                {"description": "Get notes with specific tags", "params": {"tags": "work,important"}},
                {"description": "Search notes by query", "params": {"search_query": "project update"}}
            ],
            return_format={
                "status": "success/error",
                "notes": "List of notes",
                "total_count": "Number of notes returned",
                "user_id": "User ID queried"
            },
            requires_auth=True,
            service_dependency="office_service"
        )
        self.registry.register_tool(notes_metadata, self.data_tools.get_notes)
        
        # Register get_documents
        documents_metadata = ToolMetadata(
            tool_id="get_documents",
            description="Get documents from the office service",
            category="data_retrieval",
            parameters={
                "document_type": {"type": "str", "description": "Type of document to filter by", "required": False},
                "start_date": {"type": "str", "description": "Start date in YYYY-MM-DD format", "required": False},
                "end_date": {"type": "str", "description": "End date in YYYY-MM-DD format", "required": False},
                "search_query": {"type": "str", "description": "Search query to filter documents", "required": False},
                "max_results": {"type": "int", "description": "Maximum number of results to return", "required": False}
            },
            examples=[
                {"description": "Get documents by type", "params": {"document_type": "pdf"}},
                {"description": "Search documents by query", "params": {"search_query": "contract"}}
            ],
            return_format={
                "status": "success/error",
                "documents": "List of documents",
                "total_count": "Number of documents returned",
                "user_id": "User ID queried"
            },
            requires_auth=True,
            service_dependency="office_service"
        )
        self.registry.register_tool(documents_metadata, self.data_tools.get_documents)
        
        # Register draft management tools
        self._register_draft_tools()
        
        # Register search tools
        self._register_search_tools()
        
        # Register web tools
        self._register_web_tools()
        
        # Register utility tools
        self._register_utility_tools()
        
        logger.info(f"Registered {self.registry.get_tool_count()} tools in enhanced registry")
    
    def _register_draft_tools(self):
        """Register draft management tools."""
        # Register create_draft_email
        create_email_metadata = ToolMetadata(
            tool_id="create_draft_email",
            description="Create or update an email draft for the current thread",
            category="draft_management",
            parameters={
                "thread_id": {"type": "str", "description": "Thread ID for the draft", "required": True},
                "to": {"type": "str", "description": "Recipient email address", "required": False},
                "subject": {"type": "str", "description": "Email subject", "required": False},
                "body": {"type": "str", "description": "Email body content", "required": False}
            },
            examples=[
                {"description": "Create email draft", "params": {"to": "user@example.com", "subject": "Meeting reminder"}},
                {"description": "Update existing draft", "params": {"body": "Updated meeting details"}}
            ],
            return_format={
                "success": "true/false",
                "draft": "Draft data object",
                "error": "Error message if failed"
            },
            requires_auth=True,
            service_dependency="none"
        )
        self.registry.register_tool(create_email_metadata, self.draft_tools.create_draft_email)
        
        # Register create_draft_calendar_event
        create_calendar_metadata = ToolMetadata(
            tool_id="create_draft_calendar_event",
            description="Create or update a calendar event draft for the current thread",
            category="draft_management",
            parameters={
                "thread_id": {"type": "str", "description": "Thread ID for the draft", "required": True},
                "title": {"type": "str", "description": "Event title", "required": False},
                "start_time": {"type": "str", "description": "Start time (ISO format)", "required": False},
                "end_time": {"type": "str", "description": "End time (ISO format)", "required": False},
                "attendees": {"type": "str", "description": "Comma-separated attendee emails", "required": False},
                "location": {"type": "str", "description": "Event location", "required": False},
                "description": {"type": "str", "description": "Event description", "required": False}
            },
            examples=[
                {"description": "Create calendar event draft", "params": {"title": "Team Meeting", "start_time": "2024-01-15T10:00:00Z"}},
                {"description": "Update existing draft", "params": {"location": "Conference Room A"}}
            ],
            return_format={
                "success": "true/false",
                "draft": "Draft data object",
                "error": "Error message if failed"
            },
            requires_auth=True,
            service_dependency="none"
        )
        self.registry.register_tool(create_calendar_metadata, self.draft_tools.create_draft_calendar_event)
        
        # Register create_draft_calendar_change
        create_calendar_change_metadata = ToolMetadata(
            tool_id="create_draft_calendar_change",
            description="Create or update a calendar change draft for the current thread",
            category="draft_management",
            parameters={
                "thread_id": {"type": "str", "description": "Thread ID for the draft", "required": True},
                "event_id": {"type": "str", "description": "Event ID to modify", "required": True},
                "change_type": {"type": "str", "description": "Type of change (reschedule, cancel, update)", "required": False},
                "new_title": {"type": "str", "description": "New event title", "required": False},
                "new_start_time": {"type": "str", "description": "New start time (ISO format)", "required": False},
                "new_end_time": {"type": "str", "description": "New end time (ISO format)", "required": False},
                "new_attendees": {"type": "str", "description": "New comma-separated attendee emails", "required": False},
                "new_location": {"type": "str", "description": "New event location", "required": False},
                "new_description": {"type": "str", "description": "New event description", "required": False}
            },
            examples=[
                {"description": "Reschedule event", "params": {"change_type": "reschedule", "new_start_time": "2024-01-15T11:00:00Z"}},
                {"description": "Update event details", "params": {"new_title": "Updated Meeting", "new_location": "New Room"}}
            ],
            return_format={
                "success": "true/false",
                "draft": "Draft data object",
                "error": "Error message if failed"
            },
            requires_auth=True,
            service_dependency="none"
        )
        self.registry.register_tool(create_calendar_change_metadata, self.draft_tools.create_draft_calendar_change)
        
        # Register delete_draft_email
        delete_email_metadata = ToolMetadata(
            tool_id="delete_draft_email",
            description="Delete an email draft for the current thread",
            category="draft_management",
            parameters={
                "thread_id": {"type": "str", "description": "Thread ID for the draft", "required": True}
            },
            examples=[
                {"description": "Delete email draft", "params": {"thread_id": "thread123"}}
            ],
            return_format={
                "success": "true/false",
                "deleted": "true/false",
                "message": "Status message"
            },
            requires_auth=True,
            service_dependency="none"
        )
        self.registry.register_tool(delete_email_metadata, self.draft_tools.delete_draft_email)
        
        # Register delete_draft_calendar_event
        delete_calendar_metadata = ToolMetadata(
            tool_id="delete_draft_calendar_event",
            description="Delete a calendar event draft for the current thread",
            category="draft_management",
            parameters={
                "thread_id": {"type": "str", "description": "Thread ID for the draft", "required": True}
            },
            examples=[
                {"description": "Delete calendar event draft", "params": {"thread_id": "thread123"}}
            ],
            return_format={
                "success": "true/false",
                "deleted": "true/false",
                "message": "Status message"
            },
            requires_auth=True,
            service_dependency="none"
        )
        self.registry.register_tool(delete_calendar_metadata, self.draft_tools.delete_draft_calendar_event)
        
        # Register delete_draft_calendar_edit
        delete_calendar_edit_metadata = ToolMetadata(
            tool_id="delete_draft_calendar_edit",
            description="Delete a calendar edit draft for the current thread",
            category="draft_management",
            parameters={
                "thread_id": {"type": "str", "description": "Thread ID for the draft", "required": True}
            },
            examples=[
                {"description": "Delete calendar edit draft", "params": {"thread_id": "thread123"}}
            ],
            return_format={
                "success": "true/false",
                "deleted": "true/false",
                "message": "Status message"
            },
            requires_auth=True,
            service_dependency="none"
        )
        self.registry.register_tool(delete_calendar_edit_metadata, self.draft_tools.delete_draft_calendar_edit)
        
        # Register clear_all_drafts
        clear_drafts_metadata = ToolMetadata(
            tool_id="clear_all_drafts",
            description="Clear all drafts for the current thread",
            category="draft_management",
            parameters={
                "thread_id": {"type": "str", "description": "Thread ID for the drafts", "required": True}
            },
            examples=[
                {"description": "Clear all drafts", "params": {"thread_id": "thread123"}}
            ],
            return_format={
                "success": "true/false",
                "cleared_count": "Number of drafts cleared",
                "cleared_drafts": "List of draft types cleared"
            },
            requires_auth=True,
            service_dependency="none"
        )
        self.registry.register_tool(clear_drafts_metadata, self.draft_tools.clear_all_drafts)
    
    def _register_search_tools(self):
        """Register search tools."""
        # Register vespa_search
        vespa_search_metadata = ToolMetadata(
            tool_id="vespa_search",
            description="Search through user's emails, calendar events, contacts, and files using semantic and keyword search",
            category="search",
            parameters={
                "query": {"type": "str", "description": "Search query string", "required": True},
                "max_results": {"type": "int", "description": "Maximum number of results", "required": False, "default": 10},
                "source_types": {"type": "list", "description": "Types of sources to search", "required": False},
                "ranking_profile": {"type": "str", "description": "Search ranking profile", "required": False, "default": "hybrid"}
            },
            examples=[
                {"description": "Search for emails about meetings", "params": {"query": "meeting", "source_types": ["email"]}},
                {"description": "General search across all data", "params": {"query": "project update"}}
            ],
            return_format={
                "status": "success/error",
                "results": "List of search results",
                "total_found": "Total number of results",
                "search_time_ms": "Search execution time"
            },
            requires_auth=True,
            service_dependency="vespa"
        )
        self.registry.register_tool(vespa_search_metadata, self.search_tools.vespa_search.search)
        
        # Register user_data_search
        user_data_search_metadata = ToolMetadata(
            tool_id="user_data_search",
            description="Search across all user data types (email, calendar, contacts, files) using intelligent method selection",
            category="search",
            parameters={
                "query": {"type": "str", "description": "Search query string", "required": True},
                "max_results": {"type": "int", "description": "Maximum number of results", "required": False, "default": 20}
            },
            examples=[
                {"description": "Search for meeting-related data", "params": {"query": "meeting", "max_results": 15}},
                {"description": "Search for project updates", "params": {"query": "project update", "max_results": 10}}
            ],
            return_format={
                "status": "success/error",
                "results": "List of search results",
                "total_found": "Total number of results",
                "search_method": "Method used for search"
            },
            requires_auth=True,
            service_dependency="office_service"
        )
        self.registry.register_tool(user_data_search_metadata, self.search_tools.user_data_search.search_all_data)
        
        # Register semantic_search
        semantic_search_metadata = ToolMetadata(
            tool_id="semantic_search",
            description="Perform semantic search through user data using vector embeddings",
            category="search",
            parameters={
                "query": {"type": "str", "description": "Search query string", "required": True},
                "max_results": {"type": "int", "description": "Maximum number of results", "required": False, "default": 10}
            },
            examples=[
                {"description": "Semantic search for similar concepts", "params": {"query": "about project planning", "max_results": 8}},
                {"description": "Find related documents", "params": {"query": "similar to budget report", "max_results": 12}}
            ],
            return_format={
                "status": "success/error",
                "results": "List of semantically similar results",
                "total_found": "Total number of results",
                "similarity_scores": "Relevance scores for results"
            },
            requires_auth=True,
            service_dependency="vespa"
        )
        self.registry.register_tool(semantic_search_metadata, self.search_tools.semantic_search.semantic_search)
    
    def _register_web_tools(self):
        """Register web search tools."""
        # Register web_search
        web_search_metadata = ToolMetadata(
            tool_id="web_search",
            description="Search the public web for information and return a concise list of results",
            category="web_search",
            parameters={
                "query": {"type": "str", "description": "Search query string", "required": True},
                "max_results": {"type": "int", "description": "Maximum number of results", "required": False, "default": 5}
            },
            examples=[
                {"description": "Search for current news", "params": {"query": "latest technology news"}},
                {"description": "Search for specific information", "params": {"query": "Python async programming"}}
            ],
            return_format={
                "status": "success/error",
                "query": "Original search query",
                "results": "List of web search results with title and URL"
            },
            requires_auth=False,
            service_dependency="duckduckgo"
        )
        self.registry.register_tool(web_search_metadata, self.web_tools.web_search.search)
    
    def _register_utility_tools(self):
        """Register utility tools."""
        # Register format_event_time_for_display
        time_format_metadata = ToolMetadata(
            tool_id="format_event_time_for_display",
            description="Format a datetime range for display in the specified timezone",
            category="utility",
            parameters={
                "start_time": {"type": "str", "description": "Start time in ISO format", "required": True},
                "end_time": {"type": "str", "description": "End time in ISO format", "required": True},
                "timezone_str": {"type": "str", "description": "Timezone string", "required": False, "default": "UTC"}
            },
            examples=[
                {"description": "Format UTC times", "params": {"start_time": "2024-01-15T10:00:00Z", "end_time": "2024-01-15T11:00:00Z"}},
                {"description": "Format with specific timezone", "params": {"start_time": "2024-01-15T10:00:00Z", "end_time": "2024-01-15T11:00:00Z", "timezone_str": "US/Eastern"}}
            ],
            return_format={
                "formatted_time": "Human-readable time range string"
            },
            requires_auth=False,
            service_dependency="none"
        )
        self.registry.register_tool(time_format_metadata, self.utility_tools.format_event_time_for_display)
        
        # Register validate_email_format
        validate_email_metadata = ToolMetadata(
            tool_id="validate_email_format",
            description="Validate if a string is a properly formatted email address",
            category="utility",
            parameters={
                "email": {"type": "str", "description": "Email address to validate", "required": True}
            },
            examples=[
                {"description": "Validate email format", "params": {"email": "user@example.com"}}
            ],
            return_format={
                "is_valid": "true/false"
            },
            requires_auth=False,
            service_dependency="none"
        )
        self.registry.register_tool(validate_email_metadata, self.utility_tools.validate_email_format)
        
        # Register sanitize_string
        sanitize_metadata = ToolMetadata(
            tool_id="sanitize_string",
            description="Sanitize and clean a text string, optionally truncating to specified length",
            category="utility",
            parameters={
                "text": {"type": "str", "description": "Text to sanitize", "required": True},
                "max_length": {"type": "int", "description": "Maximum length for truncation", "required": False}
            },
            examples=[
                {"description": "Sanitize text", "params": {"text": "Raw text with special chars", "max_length": 100}}
            ],
            return_format={
                "sanitized_text": "Cleaned and optionally truncated text"
            },
            requires_auth=False,
            service_dependency="none"
        )
        self.registry.register_tool(sanitize_metadata, self.utility_tools.sanitize_string)
        
        # Register parse_date_range
        parse_date_metadata = ToolMetadata(
            tool_id="parse_date_range",
            description="Parse a date range string and extract start and end dates",
            category="utility",
            parameters={
                "date_string": {"type": "str", "description": "Date range string to parse", "required": True}
            },
            examples=[
                {"description": "Parse date range", "params": {"date_string": "last week"}},
                {"description": "Parse specific dates", "params": {"date_string": "2024-01-01 to 2024-01-31"}}
            ],
            return_format={
                "start_date": "Start date in YYYY-MM-DD format",
                "end_date": "End date in YYYY-MM-DD format"
            },
            requires_auth=False,
            service_dependency="none"
        )
        self.registry.register_tool(parse_date_metadata, self.utility_tools.parse_date_range)
        
        # Register format_file_size
        format_size_metadata = ToolMetadata(
            tool_id="format_file_size",
            description="Format file size in bytes to human-readable format",
            category="utility",
            parameters={
                "size_bytes": {"type": "int", "description": "File size in bytes", "required": True}
            },
            examples=[
                {"description": "Format file size", "params": {"size_bytes": 1048576}}
            ],
            return_format={
                "formatted_size": "Human-readable file size (e.g., '1.0 MB')"
            },
            requires_auth=False,
            service_dependency="none"
        )
        self.registry.register_tool(format_size_metadata, self.utility_tools.format_file_size)
        
        # Register extract_phone_number
        extract_phone_metadata = ToolMetadata(
            tool_id="extract_phone_number",
            description="Extract phone number from text using pattern matching",
            category="utility",
            parameters={
                "text": {"type": "str", "description": "Text to extract phone number from", "required": True}
            },
            examples=[
                {"description": "Extract phone number", "params": {"text": "Call me at 555-123-4567 tomorrow"}}
            ],
            return_format={
                "phone_number": "Extracted phone number or null if not found"
            },
            requires_auth=False,
            service_dependency="none"
        )
        self.registry.register_tool(extract_phone_metadata, self.utility_tools.extract_phone_number)
        
        # Register generate_summary
        generate_summary_metadata = ToolMetadata(
            tool_id="generate_summary",
            description="Generate a concise summary of text content",
            category="utility",
            parameters={
                "text": {"type": "str", "description": "Text to summarize", "required": True},
                "max_length": {"type": "int", "description": "Maximum length of summary", "required": False, "default": 200}
            },
            examples=[
                {"description": "Generate summary", "params": {"text": "Long text content", "max_length": 150}}
            ],
            return_format={
                "summary": "Concise summary of the input text"
            },
            requires_auth=False,
            service_dependency="none"
        )
        self.registry.register_tool(generate_summary_metadata, self.utility_tools.generate_summary)


# Note: Legacy get_* functions have been moved to DataTools class
# Use self.data_tools.get_calendar_events(), self.data_tools.get_emails(), etc.


# Note: Global tool registry is now handled by the enhanced registry system
# Use get_global_registry() from tool_registry.py instead


