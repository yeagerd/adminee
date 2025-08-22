#!/usr/bin/env python3
"""
LLM Tools for chat workflows - Enhanced with Vespa search capabilities
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import unquote

import requests

from services.chat.service_client import ServiceClient
from services.vespa_query.search_engine import SearchEngine

logger = logging.getLogger(__name__)

# Global draft storage for in-memory draft management
# This is used by the workflow system to maintain draft state during conversations
_draft_storage: Dict[str, Dict[str, Any]] = {}


# Draft management functions
def create_draft_email(
    thread_id: str,
    to: Optional[str] = None,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create a draft email for the given thread."""
    try:
        key = f"{thread_id}_email"
        email_data = {
            "to": to or "",
            "subject": subject or "",
            "body": body or "",
            **kwargs,
        }
        _draft_storage[key] = email_data
        logger.info(f"📧 Created email draft for thread {thread_id}")
        return {"success": True, "draft": email_data}
    except Exception as e:
        logger.error(f"Failed to create email draft: {e}")
        return {"success": False, "error": str(e)}


def create_draft_calendar_event(
    thread_id: str,
    title: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    attendees: Optional[str] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create or update a draft calendar event for the given thread."""
    try:
        key = f"{thread_id}_calendar_event"

        # Get existing draft if it exists
        existing_draft = _draft_storage.get(key, {})

        # Build event data, only including fields that are provided or already exist
        event_data = {
            "type": "calendar_event",
            "thread_id": thread_id,
        }

        # Add fields that are provided or already exist
        if title is not None:
            event_data["title"] = title
        elif "title" in existing_draft:
            event_data["title"] = existing_draft["title"]

        if start_time is not None:
            event_data["start_time"] = start_time
        elif "start_time" in existing_draft:
            event_data["start_time"] = existing_draft["start_time"]

        if end_time is not None:
            event_data["end_time"] = end_time
        elif "end_time" in existing_draft:
            event_data["end_time"] = existing_draft["end_time"]

        if attendees is not None:
            event_data["attendees"] = attendees
        elif "attendees" in existing_draft:
            event_data["attendees"] = existing_draft["attendees"]

        if location is not None:
            event_data["location"] = location
        elif "location" in existing_draft:
            event_data["location"] = existing_draft["location"]

        if description is not None:
            event_data["description"] = description
        elif "description" in existing_draft:
            event_data["description"] = existing_draft["description"]

        # Add any additional kwargs
        event_data.update(kwargs)

        _draft_storage[key] = event_data
        logger.info(f"📅 Created/updated calendar event draft for thread {thread_id}")
        return {"success": True, "draft": event_data}
    except Exception as e:
        logger.error(f"Failed to create calendar event draft: {e}")
        return {"success": False, "error": str(e)}


def create_draft_calendar_change(
    thread_id: str,
    event_id: Optional[str] = None,
    change_type: Optional[str] = None,
    new_title: Optional[str] = None,
    new_start_time: Optional[str] = None,
    new_end_time: Optional[str] = None,
    new_attendees: Optional[str] = None,
    new_location: Optional[str] = None,
    new_description: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create a draft calendar change for the given thread."""
    try:
        # Validate required parameters
        if not event_id or not event_id.strip():
            return {"success": False, "message": "event_id is required"}

        key = f"{thread_id}_calendar_edit"

        # Get existing draft if it exists
        existing_draft = _draft_storage.get(key, {})

        # Build change data, only including fields that are provided or already exist
        change_data: Dict[str, Any] = {}

        # Add fields that are provided or already exist
        if event_id is not None:
            change_data["event_id"] = event_id
        elif "event_id" in existing_draft:
            change_data["event_id"] = existing_draft["event_id"]

        if change_type is not None:
            change_data["change_type"] = change_type
        elif "change_type" in existing_draft:
            change_data["change_type"] = existing_draft["change_type"]

        # Initialize changes dict with proper typing
        changes: Dict[str, Any] = {}

        if new_title is not None:
            changes["title"] = new_title
        elif "changes" in existing_draft and "title" in existing_draft["changes"]:
            changes["title"] = existing_draft["changes"]["title"]

        if new_start_time is not None:
            changes["start_time"] = new_start_time
        elif "changes" in existing_draft and "start_time" in existing_draft["changes"]:
            changes["start_time"] = existing_draft["changes"]["start_time"]

        if new_end_time is not None:
            changes["end_time"] = new_end_time
        elif "changes" in existing_draft and "end_time" in existing_draft["changes"]:
            changes["end_time"] = existing_draft["changes"]["end_time"]

        if new_attendees is not None:
            attendee_list = []
            for email in new_attendees.split(","):
                email = email.strip()
                if email:
                    attendee_list.append({"email": email, "name": email.split("@")[0]})
            changes["attendees"] = attendee_list
        elif "changes" in existing_draft and "attendees" in existing_draft["changes"]:
            changes["attendees"] = existing_draft["changes"]["attendees"]

        if new_location is not None:
            changes["location"] = new_location
        elif "changes" in existing_draft and "location" in existing_draft["changes"]:
            changes["location"] = existing_draft["changes"]["location"]

        if new_description is not None:
            changes["description"] = new_description
        elif "changes" in existing_draft and "description" in existing_draft["changes"]:
            changes["description"] = existing_draft["changes"]["description"]

        # Add any additional kwargs to changes if they're not already handled
        for key_name, value in kwargs.items():
            if key_name not in ["event_id", "change_type"] and value is not None:
                changes[key_name] = value

        # Check if any new changes were actually provided (not just existing ones)
        new_params_provided = any(
            [
                new_title is not None,
                new_start_time is not None,
                new_end_time is not None,
                new_attendees is not None,
                new_location is not None,
                new_description is not None,
            ]
        )

        if not new_params_provided and not kwargs:
            return {"success": False, "message": "No changes provided"}

        # Add the changes to the change data
        change_data["changes"] = changes

        _draft_storage[key] = change_data
        logger.info(f"✏️ Created/updated calendar edit draft for thread {thread_id}")
        return {"success": True, "draft": change_data}
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


def get_draft_calendar_edit(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get the calendar edit draft for the given thread."""
    key = f"{thread_id}_calendar_edit"
    return _draft_storage.get(key)


def has_draft_email(thread_id: str) -> bool:
    """Check if there's an email draft for the given thread."""
    key = f"{thread_id}_email"
    return key in _draft_storage


def has_draft_calendar_event(thread_id: str) -> bool:
    """Check if there's a calendar event draft for the given thread."""
    key = f"{thread_id}_calendar_event"
    return key in _draft_storage


def has_draft_calendar_edit(thread_id: str) -> bool:
    """Check if there's a calendar edit draft for the given thread."""
    key = f"{thread_id}_calendar_edit"
    return key in _draft_storage


def delete_draft_email(thread_id: str) -> Dict[str, Any]:
    """Delete the email draft for the given thread."""
    try:
        key = f"{thread_id}_email"
        if key in _draft_storage:
            del _draft_storage[key]
            logger.info(f"🗑️ Deleted email draft for thread {thread_id}")
            return {
                "success": True,
                "deleted": True,
                "message": "Email draft deleted successfully",
            }
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
            return {
                "success": True,
                "deleted": True,
                "message": "Calendar event draft deleted successfully",
            }
        return {
            "success": True,
            "deleted": False,
            "message": "No calendar event draft found",
        }
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
            return {
                "success": True,
                "deleted": True,
                "message": "Calendar edit draft deleted successfully",
            }
        return {"success": False, "message": "No calendar event edit draft found"}
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

        # Extract draft types from keys
        cleared_drafts = []
        for key in keys_to_remove:
            if key.endswith("_email"):
                cleared_drafts.append("email")
            elif key.endswith("_calendar_event"):
                cleared_drafts.append("calendar_event")
            elif key.endswith("_calendar_edit"):
                cleared_drafts.append("calendar_edit")
            else:
                # For any other draft types, extract the type
                draft_type = key.replace(thread_prefix, "")
                cleared_drafts.append(draft_type)

        for key in keys_to_remove:
            del _draft_storage[key]

        logger.info(f"🗑️ Cleared {len(keys_to_remove)} drafts for thread {thread_id}")
        return {
            "success": True,
            "cleared_count": len(keys_to_remove),
            "cleared_drafts": cleared_drafts,
        }
    except Exception as e:
        logger.error(f"Failed to clear drafts: {e}")
        return {"success": False, "error": str(e)}


# Document and note retrieval functions
def get_documents(
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
        import requests

        from services.chat.settings import get_settings

        # Get settings
        settings = get_settings()

        # First, check if user has document integrations
        try:
            integrations_response = requests.get(
                f"{settings.user_service_url}/v1/internal/users/{user_id}/integrations",
                headers={"Authorization": f"Bearer {settings.api_chat_user_key}"},
                timeout=10,
            )

            if integrations_response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Failed to get user integrations: {integrations_response.status_code}",
                    "user_id": user_id,
                }

            integrations_data = integrations_response.json()
            document_integrations = [
                integration
                for integration in integrations_data.get("integrations", [])
                if "documents" in integration.get("scopes", [])
            ]

            if not document_integrations:
                return {
                    "status": "error",
                    "error": "No document integrations found for user",
                    "user_id": user_id,
                }

        except Exception as e:
            logger.error(f"Error checking user integrations: {e}")
            return {
                "status": "error",
                "error": f"Failed to check user integrations: {str(e)}",
                "user_id": user_id,
            }

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
        try:
            response = requests.get(
                f"{settings.office_service_url}/v1/documents",
                params=params,
                headers={"Authorization": f"Bearer {settings.api_chat_office_key}"},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()

                # Validate response structure
                if "data" not in data:
                    return {
                        "status": "error",
                        "error": "Malformed response: missing 'data' field",
                        "user_id": user_id,
                    }

                documents = data.get("data", {}).get("files", [])
                if not isinstance(documents, list):
                    return {
                        "status": "error",
                        "error": "Malformed response: 'files' field is not a list",
                        "user_id": user_id,
                    }

                return {
                    "status": "success",
                    "documents": documents,
                    "total_count": len(documents),
                    "user_id": user_id,
                    "query_params": params,
                }
            else:
                logger.error(
                    f"Failed to get documents: {response.status_code} - {response.text}"
                )
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "user_id": user_id,
                }

        except requests.Timeout:
            logger.error("Document request timed out")
            return {"status": "error", "error": "Request timed out", "user_id": user_id}
        except requests.HTTPError:
            logger.error("Document request failed with HTTP error")
            return {
                "status": "error",
                "error": "HTTP error occurred",
                "user_id": user_id,
            }
        except Exception as e:
            logger.error(f"Error making document request: {e}")
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "user_id": user_id,
            }

    except Exception as e:
        logger.error(f"Error getting documents for user {user_id}: {e}")
        return {"status": "error", "error": str(e), "user_id": user_id}


def get_notes(
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
        import requests

        from services.chat.settings import get_settings

        # Get settings
        settings = get_settings()

        # First, check if user has note integrations
        try:
            integrations_response = requests.get(
                f"{settings.user_service_url}/v1/internal/users/{user_id}/integrations",
                headers={"Authorization": f"Bearer {settings.api_chat_user_key}"},
                timeout=10,
            )

            if integrations_response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Failed to get user integrations: {integrations_response.status_code}",
                    "user_id": user_id,
                }

            integrations_data = integrations_response.json()
            note_integrations = [
                integration
                for integration in integrations_data.get("integrations", [])
                if "notes" in integration.get("scopes", [])
            ]

            if not note_integrations:
                return {
                    "status": "error",
                    "error": "No note integrations found for user",
                    "user_id": user_id,
                }

        except Exception as e:
            logger.error(f"Error checking user integrations: {e}")
            return {
                "status": "error",
                "error": f"Failed to check user integrations: {str(e)}",
                "user_id": user_id,
            }

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
        try:
            response = requests.get(
                f"{settings.office_service_url}/v1/notes",
                params=params,
                headers={"Authorization": f"Bearer {settings.api_chat_office_key}"},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()

                # Validate response structure
                if "data" not in data:
                    return {
                        "status": "error",
                        "error": "Malformed response: missing 'data' field",
                        "user_id": user_id,
                    }

                notes = data.get("data", {}).get("notes", [])
                if not isinstance(notes, list):
                    return {
                        "status": "error",
                        "error": "Malformed response: 'notes' field is not a list",
                        "user_id": user_id,
                    }

                return {
                    "status": "success",
                    "notes": notes,
                    "total_count": len(notes),
                    "user_id": user_id,
                    "query_params": params,
                }
            else:
                logger.error(
                    f"Failed to get notes: {response.status_code} - {response.text}"
                )
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "user_id": user_id,
                }

        except requests.Timeout:
            logger.error("Note request timed out")
            return {"status": "error", "error": "Request timed out", "user_id": user_id}
        except requests.HTTPError:
            logger.error("Note request failed with HTTP error")
            return {
                "status": "error",
                "error": "HTTP error occurred",
                "user_id": user_id,
            }
        except Exception as e:
            logger.error(f"Error making note request: {e}")
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "user_id": user_id,
            }

    except Exception as e:
        logger.error(f"Error getting notes for user {user_id}: {e}")
        return {"status": "error", "error": str(e), "user_id": user_id}


class VespaSearchTool:
    """Tool for searching user data using Vespa"""

    def __init__(self, vespa_endpoint: str, user_id: str):
        self.search_engine = SearchEngine(vespa_endpoint)
        self.user_id = user_id
        self.tool_name = "vespa_search"
        self.description = "Search through user's emails, calendar events, contacts, and files using semantic and keyword search"

    async def search(
        self,
        query: str,
        max_results: int = 10,
        source_types: Optional[List[str]] = None,
        ranking_profile: str = "hybrid",
    ) -> Dict[str, Any]:
        """Search user data using Vespa"""
        try:
            # Build search query
            yql_query = self._build_yql_query(query, source_types)
            search_query = {
                "yql": yql_query,
                "hits": max_results,
                "ranking": ranking_profile,
                "timeout": "5.0s",
                "streaming.groupname": self.user_id,  # Add streaming mode support for user isolation
            }

            # Debug logging
            logger.info(f"Search query: {search_query}")

            # Execute search
            results = await self.search_engine.search(search_query)

            # Process results
            processed_results = self._process_search_results(results, query)

            return {
                "status": "success",
                "query": query,
                "results": processed_results,
                "total_found": results.get("root", {})
                .get("fields", {})
                .get("totalCount", 0),
                "search_time_ms": results.get("performance", {}).get(
                    "query_time_ms", 0
                ),
            }

        except Exception as e:
            logger.error(f"Vespa search failed: {e}")
            return {"status": "error", "query": query, "error": str(e), "results": []}

    def _build_yql_query(
        self, query: str, source_types: Optional[List[str]] = None
    ) -> str:
        """Build YQL query for Vespa"""
        # Base query - use streaming group for user isolation instead of user_id filter
        yql = "select * from briefly_document where true"

        # Add source type filtering
        if source_types:
            source_types_str = '", "'.join(source_types)
            yql += f' and source_type in ("{source_types_str}")'

        # Add text search across all indexed text fields
        yql += f' and (search_text contains "{query}" or title contains "{query}" or content contains "{query}")'

        return yql

    def _process_search_results(
        self, results: Dict[str, Any], query: str
    ) -> List[Dict[str, Any]]:
        """Process and format search results with enhanced metadata"""
        processed = []

        try:
            root = results.get("root", {})
            children = root.get("children", [])

            for child in children:
                fields = child.get("fields", {})

                # Determine search method based on relevance score and content analysis
                search_method = self._determine_search_method(child, fields, query)

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
                    "snippet": self._generate_snippet(
                        fields.get("search_text", ""), query
                    ),
                    "search_method": search_method,
                    "match_confidence": self._calculate_match_confidence(
                        child, fields, query
                    ),
                    "vector_similarity": fields.get("embedding_similarity", None),
                    "keyword_matches": self._count_keyword_matches(
                        fields.get("search_text", ""), query
                    ),
                    "content_length": len(fields.get("content", "")),
                    "search_text_length": len(fields.get("search_text", "")),
                }

                # Add type-specific fields
                if fields.get("source_type") == "email":
                    result.update(
                        {
                            "sender": fields.get("sender"),
                            "recipients": fields.get("recipients", []),
                            "thread_id": fields.get("thread_id"),
                            "folder": fields.get("folder"),
                            "quoted_content": fields.get("quoted_content", ""),
                            "thread_summary": fields.get("thread_summary", {}),
                            "is_read": fields.get("metadata", {}).get("is_read", False),
                            "has_attachments": fields.get("metadata", {}).get(
                                "has_attachments", False
                            ),
                            "attachment_count": fields.get("metadata", {}).get(
                                "attachment_count", 0
                            ),
                        }
                    )
                elif fields.get("source_type") == "calendar":
                    result.update(
                        {
                            "start_time": fields.get("start_time"),
                            "end_time": fields.get("end_time"),
                            "attendees": fields.get("attendees", []),
                            "location": fields.get("location"),
                            "is_all_day": fields.get("is_all_day", False),
                            "recurring": fields.get("recurring", False),
                        }
                    )
                elif fields.get("source_type") == "contact":
                    result.update(
                        {
                            "display_name": fields.get("title"),
                            "email_addresses": fields.get("email_addresses", []),
                            "company": fields.get("company"),
                            "job_title": fields.get("job_title"),
                            "phone_numbers": fields.get("phone_numbers", []),
                            "address": fields.get("address", ""),
                        }
                    )

                processed.append(result)

            # Sort by relevance score
            processed.sort(key=lambda x: x.get("relevance_score", 0.0), reverse=True)

        except Exception as e:
            logger.error(f"Error processing search results: {e}")

        return processed

    def _determine_search_method(
        self, child: Dict[str, Any], fields: Dict[str, Any], query: str
    ) -> str:
        """Determine whether result came from vector similarity or keyword matching"""
        relevance = child.get("relevance", 0.0)
        search_text = fields.get("search_text", "").lower()
        query_lower = query.lower()

        # Check for exact keyword matches
        exact_matches = query_lower in search_text
        word_matches = any(word in search_text for word in query_lower.split())

        # Check if we have vector similarity data
        has_vector = fields.get("embedding") is not None

        if has_vector and relevance > 0.5:
            if exact_matches or word_matches:
                return "Hybrid (Vector + Keyword)"
            else:
                return "Vector Similarity"
        elif exact_matches or word_matches:
            return "Keyword Matching"
        else:
            return "Semantic/Contextual"

    def _calculate_match_confidence(
        self, child: Dict[str, Any], fields: Dict[str, Any], query: str
    ) -> str:
        """Calculate confidence level of the match"""
        relevance = child.get("relevance", 0.0)
        search_text = fields.get("search_text", "").lower()
        query_lower = query.lower()

        # Count keyword matches
        query_words = query_lower.split()
        matches = sum(1 for word in query_words if word in search_text)
        match_ratio = matches / len(query_words) if query_words else 0

        if relevance > 0.8 and match_ratio > 0.8:
            return "Very High"
        elif relevance > 0.6 and match_ratio > 0.6:
            return "High"
        elif relevance > 0.4 and match_ratio > 0.4:
            return "Medium"
        elif relevance > 0.2:
            return "Low"
        else:
            return "Very Low"

    def _count_keyword_matches(self, search_text: str, query: str) -> Dict[str, Any]:
        """Count keyword matches and their positions"""
        if not search_text or not query:
            return {"count": 0, "words": [], "positions": []}

        search_lower = search_text.lower()
        query_lower = query.lower()
        query_words = query_lower.split()

        matches = []
        positions = []

        for word in query_words:
            if word in search_lower:
                matches.append(word)
                # Find all positions of this word
                start = 0
                while True:
                    pos = search_lower.find(word, start)
                    if pos == -1:
                        break
                    positions.append(pos)
                    start = pos + 1

        return {
            "count": len(matches),
            "words": list(set(matches)),
            "positions": sorted(positions),
            "match_ratio": len(matches) / len(query_words) if query_words else 0,
        }

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

    async def search_all_data(
        self, query: str, max_results: int = 20
    ) -> Dict[str, Any]:
        """Search across all data types with intelligent grouping"""
        try:
            # Search across all source types
            results = await self.vespa_search.search(
                query=query, max_results=max_results, ranking_profile="hybrid"
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
                "search_time_ms": results["search_time_ms"],
            }

        except Exception as e:
            logger.error(f"User data search failed: {e}")
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "grouped_results": {},
            }

    def _group_results_by_type(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group search results by data type"""
        grouped: Dict[str, List[Dict[str, Any]]] = {
            "emails": [],
            "calendar": [],
            "contacts": [],
            "files": [],
            "other": [],
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

    def _generate_search_summary(
        self, grouped_results: Dict[str, List[Dict[str, Any]]], query: str
    ) -> Dict[str, Any]:
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
                "other": len(grouped_results["other"]),
            },
            "top_results": [],
            "insights": [],
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

    async def semantic_search(
        self, query: str, max_results: int = 10
    ) -> Dict[str, Any]:
        """Perform semantic search using vector similarity"""
        try:
            # Build semantic search query
            search_query = {
                "yql": f'select * from briefly_document where user_id contains "{self.user_id}"',
                "hits": max_results,
                "ranking": "semantic",
                "timeout": "5.0s",
                "streaming.groupname": self.user_id,  # Add streaming mode support for user isolation
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
                "total_found": results.get("root", {})
                .get("fields", {})
                .get("totalCount", 0),
                "search_time_ms": results.get("performance", {}).get(
                    "query_time_ms", 0
                ),
            }

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return {"status": "error", "query": query, "error": str(e), "results": []}

    def _process_semantic_results(
        self, results: Dict[str, Any], query: str
    ) -> List[Dict[str, Any]]:
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
                    "snippet": self._generate_snippet(
                        fields.get("search_text", ""), query
                    ),
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


# Simple web search tool (no external API key required).
# Uses DuckDuckGo HTML endpoint and best-effort parsing.
class WebSearchTool:
    """Lightweight web search tool for general web information retrieval."""

    def __init__(self) -> None:
        self.tool_name = "web_search"
        self.description = (
            "Search the public web for information and return a concise list of results"
        )

    async def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the web and return a list of title/url/snippet entries.

        Note: This uses DuckDuckGo's HTML endpoint and simple parsing. It may be brittle
        and should be replaced with a proper search API in production.
        """
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            }
            resp = requests.get(
                "https://duckduckgo.com/html/",
                params={"q": query},
                headers=headers,
                timeout=10,
            )
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HTTP {resp.status_code}",
                    "results": [],
                }

            html = resp.text
            results: List[Dict[str, Any]] = []

            # Very lightweight parsing: look for links shaped like /l/?uddg=...
            # and extract adjacent title text. This is intentionally simple.
            # We avoid heavy dependencies for now.
            anchor_marker = 'href="/l/?uddg='
            pos = 0
            while len(results) < max_results:
                idx = html.find(anchor_marker, pos)
                if idx == -1:
                    break
                # Extract URL
                start = idx + len('href="/l/?uddg=')
                end = html.find('"', start)
                if end == -1:
                    break
                raw = html[start:end]
                url = unquote(raw)
                # Extract a crude title by looking for ">...<" after the anchor
                title_start = html.find(">", end) + 1
                title_end = html.find("<", title_start)
                title = html[title_start:title_end].strip()
                if title and url:
                    results.append({"title": title, "url": url})
                pos = end + 1

            return {"status": "success", "query": query, "results": results}
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {"status": "error", "error": str(e), "results": []}


class GetTool:
    """Generic tool gateway backed by ToolRegistry.

    Allows the LLM to discover and invoke available "get_*" tools dynamically.
    """

    def __init__(self, registry: "ToolRegistry", default_user_id: Optional[str] = None):
        self.registry = registry
        self.default_user_id = default_user_id
        self.tool_name = "get_tool"
        self.description = (
            "Execute a named tool (e.g., get_calendar_events, get_emails) with params"
        )

    def list_tools(self) -> Dict[str, Any]:
        try:
            return {"status": "success", "tools": self.registry.list_tools()}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def execute(
        self, tool_name: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            kwargs = params.copy() if params else {}
            if self.default_user_id and "user_id" not in kwargs:
                kwargs["user_id"] = self.default_user_id
            result = self.registry.execute_tool(tool_name, **kwargs)
            # Unwrap ToolOutput-like object
            raw = getattr(result, "raw_output", result)
            return {"status": "success", "tool": tool_name, "result": raw}
        except Exception as e:
            logger.error(f"GetTool execute failed for {tool_name}: {e}")
            return {"status": "error", "tool": tool_name, "error": str(e)}


# Register tools with the chat service
def register_vespa_tools(
    chat_service: ServiceClient, vespa_endpoint: str, user_id: str
) -> None:
    """Register Vespa search tools with the chat service"""
    tools = {
        "vespa_search": VespaSearchTool(vespa_endpoint, user_id),
        "user_data_search": UserDataSearchTool(vespa_endpoint, user_id),
        "semantic_search": SemanticSearchTool(vespa_endpoint, user_id),
    }

    # Note: ServiceClient doesn't have add_tool method, tools are registered differently
    # This function is kept for compatibility but doesn't actually register tools
    logger.info(
        f"Vespa search tools created for user {user_id} (registration handled by caller)"
    )


def get_calendar_events(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    time_zone: str = "UTC",
    providers: Optional[List[str]] = None,
    limit: int = 50,
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
        import requests

        from services.chat.settings import get_settings

        # Get settings
        settings = get_settings()

        # First, check if user has calendar integrations
        try:
            integrations_response = requests.get(
                f"{settings.user_service_url}/v1/internal/users/{user_id}/integrations",
                headers={"Authorization": f"Bearer {settings.api_chat_user_key}"},
                timeout=10,
            )

            if integrations_response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Failed to get user integrations: {integrations_response.status_code}",
                    "user_id": user_id,
                }

            integrations_data = integrations_response.json()
            calendar_integrations = [
                integration
                for integration in integrations_data.get("integrations", [])
                if "calendar" in integration.get("scopes", [])
            ]

            if not calendar_integrations:
                return {
                    "status": "error",
                    "error": "No calendar integrations found for user",
                    "user_id": user_id,
                }

        except Exception as e:
            logger.error(f"Error checking user integrations: {e}")
            return {
                "status": "error",
                "error": f"Failed to check user integrations: {str(e)}",
                "user_id": user_id,
            }

        # Build query parameters
        params: Dict[str, Any] = {"user_id": user_id, "limit": limit}

        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if time_zone and time_zone != "UTC":
            params["timezone"] = time_zone
        if providers:
            params["providers"] = ",".join(providers)

        # Make request to office service
        try:
            response = requests.get(
                f"{settings.office_service_url}/v1/calendar/events",
                params=params,
                headers={"Authorization": f"Bearer {settings.api_chat_office_key}"},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()

                # Validate response structure
                if "data" not in data:
                    return {
                        "status": "error",
                        "error": "Malformed response: missing 'data' field",
                        "user_id": user_id,
                    }

                events = data.get("data", {}).get("events", [])
                if not isinstance(events, list):
                    return {
                        "status": "error",
                        "error": "Malformed response: 'events' field is not a list",
                        "user_id": user_id,
                    }

                # Validate individual events have required fields
                for i, event in enumerate(events):
                    # Check for required fields
                    if hasattr(event, "id"):
                        # CalendarEvent object
                        if not event.id:
                            return {
                                "status": "error",
                                "error": f"Validation error: event {i} missing required field: id",
                                "user_id": user_id,
                            }
                        # Check for other required fields in CalendarEvent objects
                        if not hasattr(event, "start_time") or not hasattr(
                            event, "end_time"
                        ):
                            return {
                                "status": "error",
                                "error": f"Validation error: event {i} missing required fields: start_time, end_time",
                                "user_id": user_id,
                            }
                    elif isinstance(event, dict):
                        # Dictionary
                        required_fields = ["id", "start_time", "end_time"]
                        missing_fields = [
                            field for field in required_fields if field not in event
                        ]
                        if missing_fields:
                            return {
                                "status": "error",
                                "error": f"Validation error: event {i} missing required fields: {', '.join(missing_fields)}",
                                "user_id": user_id,
                            }
                    else:
                        # Neither CalendarEvent object nor dictionary
                        return {
                            "status": "error",
                            "error": f"Malformed response: event {i} is neither a CalendarEvent object nor a dictionary",
                            "user_id": user_id,
                        }

                # Convert CalendarEvent objects to dictionaries if they are objects
                events_list = []
                for event in events:
                    if hasattr(event, "__dict__"):
                        # Convert object to dictionary
                        event_dict = {}
                        for key, value in event.__dict__.items():
                            if not key.startswith("_"):
                                event_dict[key] = value

                        # Add display_time field if timezone is provided
                        if (
                            time_zone
                            and time_zone != "UTC"
                            and hasattr(event, "start_time")
                            and hasattr(event, "end_time")
                        ):
                            # Ensure variables exist even if formatting fails
                            start_time_str = str(getattr(event, "start_time", ""))
                            end_time_str = str(getattr(event, "end_time", ""))
                            try:
                                event_dict.update(
                                    {
                                        "display_time": format_event_time_for_display(
                                            start_time_str, end_time_str, time_zone
                                        )
                                    }
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to format display_time for event {getattr(event, 'id', 'unknown')}: {e}"
                                )
                                event_dict.update(
                                    {
                                        "display_time": f"{start_time_str} to {end_time_str}"
                                    }
                                )

                        events_list.append(event_dict)
                    else:
                        # Handle dictionary events
                        event_dict = event.copy()

                        # Add display_time field if timezone is provided
                        if (
                            time_zone
                            and time_zone != "UTC"
                            and "start_time" in event
                            and "end_time" in event
                        ):
                            # Ensure variables exist even if formatting fails
                            start_time_str = str(event.get("start_time", ""))
                            end_time_str = str(event.get("end_time", ""))
                            try:
                                event_dict.update(
                                    {
                                        "display_time": format_event_time_for_display(
                                            start_time_str, end_time_str, time_zone
                                        )
                                    }
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to format display_time for event {event.get('id', 'unknown')}: {e}"
                                )
                                event_dict.update(
                                    {
                                        "display_time": f"{start_time_str} to {end_time_str}"
                                    }
                                )

                        events_list.append(event_dict)

                return {
                    "status": "success",
                    "events": events_list,
                    "total_count": len(events_list),
                    "user_id": user_id,
                    "query_params": params,
                }
            else:
                logger.error(
                    f"Failed to get calendar events: {response.status_code} - {response.text}"
                )
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "user_id": user_id,
                }

        except requests.Timeout:
            logger.error("Calendar request timed out")
            return {"status": "error", "error": "Request timed out", "user_id": user_id}
        except requests.HTTPError:
            logger.error("Calendar request failed with HTTP error")
            return {
                "status": "error",
                "error": "HTTP error occurred",
                "user_id": user_id,
            }
        except Exception as e:
            logger.error(f"Error making calendar request: {e}")
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "user_id": user_id,
            }

    except Exception as e:
        logger.error(f"Error getting calendar events for user {user_id}: {e}")
        return {"status": "error", "error": str(e), "user_id": user_id}


# Email retrieval function
def get_emails(
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
        import requests

        from services.chat.settings import get_settings

        # Get settings
        settings = get_settings()

        # First, check if user has email integrations
        try:
            integrations_response = requests.get(
                f"{settings.user_service_url}/v1/internal/users/{user_id}/integrations",
                headers={"Authorization": f"Bearer {settings.api_chat_user_key}"},
                timeout=10,
            )

            if integrations_response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Failed to get user integrations: {integrations_response.status_code}",
                    "user_id": user_id,
                }

            integrations_data = integrations_response.json()
            email_integrations = [
                integration
                for integration in integrations_data.get("integrations", [])
                if "email" in integration.get("scopes", [])
            ]

            if not email_integrations:
                return {
                    "status": "error",
                    "error": "No email integrations found for user",
                    "user_id": user_id,
                }

        except Exception as e:
            logger.error(f"Error checking user integrations: {e}")
            return {
                "status": "error",
                "error": f"Failed to check user integrations: {str(e)}",
                "user_id": user_id,
            }

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
        try:
            response = requests.get(
                f"{settings.office_service_url}/v1/emails",
                params=params,
                headers={"Authorization": f"Bearer {settings.api_chat_office_key}"},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()

                # Validate response structure
                if "data" not in data:
                    return {
                        "status": "error",
                        "error": "Malformed response: missing 'data' field",
                        "user_id": user_id,
                    }

                emails = data.get("data", {}).get("emails", [])
                if "emails" not in data.get("data", {}):
                    return {
                        "status": "error",
                        "error": "Malformed response: missing 'emails' field",
                        "user_id": user_id,
                    }
                if not isinstance(emails, list):
                    return {
                        "status": "error",
                        "error": "Malformed response: 'emails' field is not a list",
                        "user_id": user_id,
                    }

                return {
                    "status": "success",
                    "emails": emails,
                    "total_count": len(emails),
                    "user_id": user_id,
                    "query_params": params,
                }
            else:
                logger.error(
                    f"Failed to get emails: {response.status_code} - {response.text}"
                )
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "user_id": user_id,
                }

        except requests.Timeout:
            logger.error("Email request timed out")
            return {"status": "error", "error": "Request timed out", "user_id": user_id}
        except requests.HTTPError:
            logger.error("Email request failed with HTTP error")
            return {
                "status": "error",
                "error": "HTTP error occurred",
                "user_id": user_id,
            }
        except Exception as e:
            logger.error(f"Error making email request: {e}")
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "user_id": user_id,
            }

    except Exception as e:
        logger.error(f"Error getting emails for user {user_id}: {e}")
        return {"status": "error", "error": str(e), "user_id": user_id}


# Tool Registry for executing various tools
class ToolRegistry:
    """Registry for executing various tools and functions."""

    def __init__(self) -> None:
        pass

    def list_tools(self) -> List[str]:
        """Return a list of available tool names."""
        return ["get_calendar_events", "get_emails", "get_notes", "get_documents"]

    def execute_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Execute a tool by name with the given arguments."""
        try:
            if tool_name == "get_calendar_events":
                user_id = kwargs.get("user_id")
                if not user_id:
                    return type(
                        "ToolOutput",
                        (),
                        {"raw_output": {"error": "user_id is required"}},
                    )()

                # Use DataTools instead of circular import
                from services.chat.tools.data_tools import DataTools

                data_tools = DataTools(user_id)
                result = data_tools.get_calendar_events(
                    start_date=kwargs.get("start_date"),
                    end_date=kwargs.get("end_date"),
                    time_zone=kwargs.get("time_zone", "UTC"),
                    providers=kwargs.get("providers"),
                    limit=kwargs.get("limit", 50),
                )

                return type("ToolOutput", (), {"raw_output": result})()

            elif tool_name == "get_emails":
                user_id = kwargs.get("user_id")
                if not user_id:
                    return type(
                        "ToolOutput",
                        (),
                        {"raw_output": {"error": "user_id is required"}},
                    )()

                # Use DataTools instead of circular import
                from services.chat.tools.data_tools import DataTools

                data_tools = DataTools(user_id)
                result = data_tools.get_emails(
                    start_date=kwargs.get("start_date"),
                    end_date=kwargs.get("end_date"),
                    folder=kwargs.get("folder"),
                    unread_only=kwargs.get("unread_only"),
                    search_query=kwargs.get("search_query"),
                    max_results=kwargs.get("max_results"),
                )

                return type("ToolOutput", (), {"raw_output": result})()

            elif tool_name == "get_notes":
                user_id = kwargs.get("user_id")
                if not user_id:
                    return type(
                        "ToolOutput",
                        (),
                        {"raw_output": {"error": "user_id is required"}},
                    )()

                # Use DataTools instead of circular import
                from services.chat.tools.data_tools import DataTools

                data_tools = DataTools(user_id)
                result = data_tools.get_notes(
                    search_query=kwargs.get("search_query"),
                    max_results=kwargs.get("max_results"),
                )

                return type("ToolOutput", (), {"raw_output": result})()

            elif tool_name == "get_documents":
                user_id = kwargs.get("user_id")
                if not user_id:
                    return type(
                        "ToolOutput",
                        (),
                        {"raw_output": {"error": "user_id is required"}},
                    )()

                # Use DataTools instead of circular import
                from services.chat.tools.data_tools import DataTools

                data_tools = DataTools(user_id)
                result = data_tools.get_documents(
                    document_type=kwargs.get("document_type"),
                    start_date=kwargs.get("start_date"),
                    end_date=kwargs.get("end_date"),
                    search_query=kwargs.get("search_query"),
                    max_results=kwargs.get("max_results"),
                )

                return type("ToolOutput", (), {"raw_output": result})()

            else:
                return type(
                    "ToolOutput",
                    (),
                    {"raw_output": {"error": f"Unknown tool: {tool_name}"}},
                )()

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return type("ToolOutput", (), {"raw_output": {"error": str(e)}})()


# Timezone formatting functions
def format_event_time_for_display(
    start_time: str, end_time: str, timezone_str: str = "UTC"
) -> str:
    """
    Format a datetime range for display in the specified timezone.

    Args:
        start_time: ISO datetime string for start time (e.g., "2025-06-18T10:00:00Z")
        end_time: ISO datetime string for end time (e.g., "2025-06-18T11:00:00Z")
        timezone_str: Timezone string (e.g., "US/Eastern", "US/Pacific")

    Returns:
        Formatted datetime range string in the specified timezone
    """
    try:
        from datetime import datetime
        from typing import Union

        import pytz

        def format_single_time(dt_str: str) -> Union[datetime, str]:
            """Format a single datetime string."""
            try:
                # Parse the datetime string
                if dt_str.endswith("Z"):
                    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                else:
                    dt = datetime.fromisoformat(dt_str)

                # If no timezone info, assume UTC
                if dt.tzinfo is None:
                    dt = pytz.UTC.localize(dt)

                return dt
            except Exception:
                # Return original string if parsing fails
                return dt_str

        # Parse both times
        start_dt = format_single_time(start_time)
        end_dt = format_single_time(end_time)

        # If either failed to parse, return original format
        if isinstance(start_dt, str) or isinstance(end_dt, str):
            return f"{start_time} to {end_time}"

        # Convert to target timezone
        try:
            target_tz = pytz.timezone(timezone_str)
            localized_start = start_dt.astimezone(target_tz)
            localized_end = end_dt.astimezone(target_tz)
        except pytz.exceptions.UnknownTimeZoneError:
            # Fall back to UTC if timezone is invalid
            localized_start = start_dt.astimezone(pytz.UTC)
            localized_end = end_dt.astimezone(pytz.UTC)

        # Format for display
        start_formatted = localized_start.strftime("%I:%M %p")
        end_formatted = localized_end.strftime("%I:%M %p")

        # Check if same day
        if localized_start.date() == localized_end.date():
            return f"{start_formatted} to {end_formatted}"
        else:
            # Different days, include dates
            start_date = localized_start.strftime("%b %d")
            end_date = localized_end.strftime("%b %d")
            return f"{start_date} {start_formatted} to {end_date} {end_formatted}"

    except Exception as e:
        logger.error(f"Error formatting datetime range {start_time} to {end_time}: {e}")
        return (
            f"{start_time} to {end_time}"  # Return original format if formatting fails
        )


# Global tool registry instance
_tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return _tool_registry
