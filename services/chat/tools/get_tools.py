"""
Get tools for service API access with pre-authenticated user context.
"""

import logging
from typing import Any, Dict, List, Optional

import requests

from services.chat.settings import get_settings

logger = logging.getLogger(__name__)


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

                result = get_calendar_events(
                    user_id=user_id,
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

                result = get_emails(
                    user_id=user_id,
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

                result = get_notes(
                    user_id=user_id,
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

                result = get_documents(
                    user_id=user_id,
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


class GetTool:
    """Generic tool gateway backed by ToolRegistry.

    Allows the LLM to discover and invoke available "get_*" tools dynamically.
    """

    def __init__(self, registry: ToolRegistry, default_user_id: str):
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
            if "user_id" not in kwargs:
                kwargs["user_id"] = self.default_user_id
            result = self.registry.execute_tool(tool_name, **kwargs)
            # Unwrap ToolOutput-like object
            raw = getattr(result, "raw_output", result)
            return {"status": "success", "tool": tool_name, "result": raw}
        except Exception as e:
            logger.error(f"GetTool execute failed for {tool_name}: {e}")
            return {"status": "error", "tool": tool_name, "error": str(e)}


class GetTools:
    """Collection of get tools with pre-authenticated user context."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.registry = ToolRegistry()
        self.get_tool = GetTool(registry=self.registry, default_user_id=user_id)


# Global tool registry instance
_tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return _tool_registry


# Legacy get_* functions moved from llm_tools.py
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
    """
    try:
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

                # Convert events to list format
                events_list = []
                for event in events:
                    if hasattr(event, "__dict__"):
                        # Convert object to dictionary
                        event_dict = {}
                        for key, value in event.__dict__.items():
                            if not key.startswith("_"):
                                event_dict[key] = value
                        events_list.append(event_dict)
                    else:
                        # Handle dictionary events
                        events_list.append(event.copy())

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
    """
    try:
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


def get_notes(
    user_id: str,
    notebook: Optional[str] = None,
    tags: Optional[str] = None,
    search_query: Optional[str] = None,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Get notes from the office service.
    """
    try:
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
    """
    try:
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
