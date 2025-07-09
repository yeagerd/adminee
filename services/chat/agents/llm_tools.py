from typing import Any, Dict, List, Optional

import requests
from llama_index.core.tools import FunctionTool
from llama_index.core.tools.types import ToolOutput

from services.chat.settings import get_settings


def format_event_time_for_display(
    start_time_utc: str, end_time_utc: str, timezone: str = None
) -> str:
    """
    Format calendar event times from UTC to a human-readable local time format.

    Args:
        start_time_utc: Start time in UTC ISO format (e.g., "2025-06-20T17:00:00Z")
        end_time_utc: End time in UTC ISO format
        timezone: Target timezone (e.g., "America/New_York"), defaults to system timezone

    Returns:
        Formatted time string (e.g., "5:00 PM to 5:30 PM")
    """
    try:
        from datetime import datetime

        import pytz

        # Parse UTC times
        start_utc = datetime.fromisoformat(start_time_utc.replace("Z", "+00:00"))
        end_utc = datetime.fromisoformat(end_time_utc.replace("Z", "+00:00"))

        # If timezone provided, convert to that timezone
        if timezone:
            try:
                target_tz = pytz.timezone(timezone)
                start_local = start_utc.astimezone(target_tz)
                end_local = end_utc.astimezone(target_tz)
            except (pytz.UnknownTimeZoneError, ValueError, TypeError):
                # Fallback to system timezone if provided timezone is invalid
                start_local = start_utc.astimezone()
                end_local = end_utc.astimezone()
        else:
            # Convert to system timezone
            start_local = start_utc.astimezone()
            end_local = end_utc.astimezone()

        # Format times (12-hour format with AM/PM)
        start_formatted = start_local.strftime(
            "%-I:%M %p" if start_local.minute != 0 else "%-I:%M %p"
        )
        end_formatted = end_local.strftime(
            "%-I:%M %p" if end_local.minute != 0 else "%-I:%M %p"
        )

        # Handle overnight events
        if start_local.date() != end_local.date():
            return (
                f"{start_formatted} to {end_formatted} ({end_local.strftime('%b %d')})"
            )
        else:
            return f"{start_formatted} to {end_formatted}"

    except Exception:
        # Fallback to original times if parsing fails
        return f"{start_time_utc} to {end_time_utc}"


def get_calendar_events(
    user_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    time_zone: str | None = None,
    providers: str | None = None,
) -> Dict[str, Any]:
    # Use service-to-service authentication
    headers = {"Content-Type": "application/json"}
    if get_settings().api_chat_office_key:
        headers["X-API-Key"] = get_settings().api_chat_office_key or ""

    params: Dict[str, str | List[str]] = {"user_id": user_id}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if time_zone:
        params["time_zone"] = time_zone

    # If no providers specified, get user's available integrations
    if not providers:
        available_providers = get_user_available_providers(user_id)
        if available_providers:
            params["providers"] = available_providers
        else:
            return {
                "error": "No calendar integrations available. Please connect Google or Microsoft calendar first."
            }
    else:
        # Convert comma-separated string to list format expected by office service
        provider_list = [p.strip() for p in providers.split(",")]
        params["providers"] = provider_list

    try:
        office_service_url = get_settings().office_service_url or ""
        response = requests.get(
            f"{office_service_url}/calendar/events",
            headers=headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        # Check for successful response structure
        if not data.get("success", False):
            return {
                "error": f"Office service error: {data.get('message', 'Unknown error')}"
            }

        # Extract events from the data field
        events_data = data.get("data", {})
        if "events" not in events_data:
            return {
                "error": "Malformed response from office-service: missing events data."
            }

        # Check for provider errors - if all providers failed, return error
        provider_errors = events_data.get("provider_errors", {})
        providers_used = events_data.get("providers_used", [])

        if provider_errors and not providers_used:
            # All providers failed
            error_messages = [
                f"{provider}: {error}" for provider, error in provider_errors.items()
            ]
            return {"error": f"Calendar access failed - {'; '.join(error_messages)}"}
        elif provider_errors:
            # Some providers failed, but we have data from others
            # Log warning but continue with available data
            print(f"Warning: Some calendar providers failed: {provider_errors}")

        # Format event times for better display
        events = events_data["events"]
        for event in events:
            if "start_time" in event and "end_time" in event:
                # Add a formatted time field for display
                event["display_time"] = format_event_time_for_display(
                    event["start_time"], event["end_time"], time_zone
                )

        return {"events": events}
    except requests.Timeout:
        return {"error": "Request to office-service timed out."}
    except requests.HTTPError as e:
        return {
            "error": f"HTTP error: {str(e)} - Response: {e.response.text if e.response else 'No response'}"
        }
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def get_user_available_providers(user_id: str) -> List[str]:
    """
    Get list of available calendar providers for a user.

    Args:
        user_id: User identifier

    Returns:
        List of available provider names (e.g., ['google', 'microsoft'])
    """
    try:
        # Use service-to-service authentication to get user integrations
        headers = {"Content-Type": "application/json"}
        if get_settings().api_chat_user_key:
            headers["X-API-Key"] = get_settings().api_chat_user_key or ""

        user_service_url = get_settings().user_management_service_url or ""
        response = requests.get(
            f"{user_service_url}/internal/users/{user_id}/integrations",
            headers=headers,
            timeout=5,
        )

        if response.status_code == 200:
            data = response.json()
            integrations = data.get("integrations", [])

            # Extract active calendar providers
            available_providers = []
            for integration in integrations:
                provider = integration.get("provider", "").lower()
                status = integration.get("status", "").lower()

                # Only include active integrations for calendar providers
                if status == "active" and provider in ["google", "microsoft"]:
                    available_providers.append(provider)

            return available_providers
        else:
            print(f"Warning: Could not fetch user integrations: {response.status_code}")
            return []

    except Exception as e:
        print(f"Warning: Error fetching user integrations: {e}")
        return []


def get_emails(
    user_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    unread_only: bool | None = None,
    folder: str | None = None,
    max_results: int | None = None,
) -> Dict[str, Any]:
    # Use service-to-service authentication
    headers = {"Content-Type": "application/json"}
    if get_settings().api_chat_office_key:
        headers["X-API-Key"] = get_settings().api_chat_office_key or ""

    params = {"user_id": user_id}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if unread_only is not None:
        params["unread_only"] = str(unread_only).lower()
    if folder:
        params["folder"] = folder
    if max_results:
        params["max_results"] = str(max_results)

    try:
        office_service_url = get_settings().office_service_url or ""
        response = requests.get(
            f"{office_service_url}/emails",
            headers=headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        # Check for successful response structure
        if not data.get("success", False):
            return {
                "error": f"Office service error: {data.get('message', 'Unknown error')}"
            }

        # Extract emails from the data field
        emails_data = data.get("data", {})
        if "emails" not in emails_data:
            return {
                "error": "Malformed response from office-service: missing emails data."
            }

        return {"emails": emails_data["emails"]}

    except requests.Timeout:
        return {"error": "Request to office-service timed out."}
    except requests.HTTPError as e:
        return {
            "error": f"HTTP error: {str(e)} - Response: {e.response.text if e.response else 'No response'}"
        }
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def get_notes(
    user_id: str,
    notebook: str | None = None,
    tags: str | None = None,
    search_query: str | None = None,
    max_results: int | None = None,
) -> Dict[str, Any]:
    # Use service-to-service authentication
    headers = {"Content-Type": "application/json"}
    if get_settings().api_chat_office_key:
        headers["X-API-Key"] = get_settings().api_chat_office_key or ""

    params = {"user_id": user_id}
    if notebook:
        params["notebook"] = notebook
    if tags:
        params["tags"] = tags
    if search_query:
        params["search_query"] = search_query
    if max_results:
        params["max_results"] = str(max_results)

    try:
        office_service_url = get_settings().office_service_url or ""
        response = requests.get(
            f"{office_service_url}/notes",
            headers=headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        # Check for successful response structure
        if not data.get("success", False):
            return {
                "error": f"Office service error: {data.get('message', 'Unknown error')}"
            }

        # Extract notes from the data field
        notes_data = data.get("data", {})
        if "notes" not in notes_data:
            return {
                "error": "Malformed response from office-service: missing notes data."
            }

        return {"notes": notes_data["notes"]}

    except requests.Timeout:
        return {"error": "Request to office-service timed out."}
    except requests.HTTPError as e:
        return {
            "error": f"HTTP error: {str(e)} - Response: {e.response.text if e.response else 'No response'}"
        }
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def get_documents(
    user_id: str,
    document_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    search_query: str | None = None,
    max_results: int | None = None,
) -> Dict[str, Any]:
    # Use service-to-service authentication
    headers = {"Content-Type": "application/json"}
    if get_settings().api_chat_office_key:
        headers["X-API-Key"] = get_settings().api_chat_office_key or ""

    params = {"user_id": user_id}
    if document_type:
        params["document_type"] = document_type
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if search_query:
        params["search_query"] = search_query
    if max_results:
        params["max_results"] = str(max_results)

    try:
        office_service_url = get_settings().office_service_url or ""
        response = requests.get(
            f"{office_service_url}/documents",
            headers=headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        # Check for successful response structure
        if not data.get("success", False):
            return {
                "error": f"Office service error: {data.get('message', 'Unknown error')}"
            }

        # Extract documents from the data field
        documents_data = data.get("data", {})
        if "documents" not in documents_data:
            return {
                "error": "Malformed response from office-service: missing documents data."
            }

        return {"documents": documents_data["documents"]}

    except requests.Timeout:
        return {"error": "Request to office-service timed out."}
    except requests.HTTPError as e:
        return {
            "error": f"HTTP error: {str(e)} - Response: {e.response.text if e.response else 'No response'}"
        }
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


# --- Draft Storage and Functions ---
_draft_storage: Dict[str, Dict[str, Any]] = {}


def has_draft_calendar_event(thread_id: str) -> bool:
    """Check if a calendar event draft exists for the given thread."""
    draft_key = f"{thread_id}_calendar_event"
    return draft_key in _draft_storage


def has_draft_email(thread_id: str) -> bool:
    """Check if an email draft exists for the given thread."""
    draft_key = f"{thread_id}_email"
    return draft_key in _draft_storage


def get_draft_calendar_event(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get the calendar event draft for the given thread, if it exists."""
    draft_key = f"{thread_id}_calendar_event"
    return _draft_storage.get(draft_key)


def get_draft_email(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get the email draft for the given thread, if it exists."""
    draft_key = f"{thread_id}_email"
    return _draft_storage.get(draft_key)


def clear_all_drafts(thread_id: str) -> Dict[str, Any]:
    """Clear all drafts for the given thread."""
    cleared_drafts = []

    # Clear calendar event draft
    calendar_key = f"{thread_id}_calendar_event"
    if calendar_key in _draft_storage:
        del _draft_storage[calendar_key]
        cleared_drafts.append("calendar_event")

    # Clear calendar event edit draft
    calendar_edit_key = f"{thread_id}_calendar_edit"
    if calendar_edit_key in _draft_storage:
        del _draft_storage[calendar_edit_key]
        cleared_drafts.append("calendar_edit")

    # Clear email draft
    email_key = f"{thread_id}_email"
    if email_key in _draft_storage:
        del _draft_storage[email_key]
        cleared_drafts.append("email")

    return {
        "success": True,
        "message": f"Cleared {len(cleared_drafts)} draft(s): {', '.join(cleared_drafts)}",
        "cleared_drafts": cleared_drafts,
    }


def create_draft_email(
    thread_id: str,
    to: str | None = None,
    cc: str | None = None,
    bcc: str | None = None,
    subject: str | None = None,
    body: str | None = None,
) -> Dict[str, Any]:
    try:
        draft_key = f"{thread_id}_email"
        draft = (
            _draft_storage[draft_key].copy()
            if draft_key in _draft_storage
            else {
                "type": "email",
                "thread_id": thread_id,
                "created_at": "2025-06-07T00:00:00Z",
            }
        )
        if to is not None:
            draft["to"] = to
        if cc is not None:
            draft["cc"] = cc
        if bcc is not None:
            draft["bcc"] = bcc
        if subject is not None:
            draft["subject"] = subject
        if body is not None:
            draft["body"] = body
        draft["updated_at"] = "2025-06-07T00:00:00Z"
        _draft_storage[draft_key] = draft
        return {"success": True, "draft": draft}
    except Exception as e:
        return {"error": f"Failed to create/update draft: {str(e)}"}


def delete_draft_email(thread_id: str) -> Dict[str, Any]:
    try:
        draft_key = f"{thread_id}_email"
        if draft_key in _draft_storage:
            del _draft_storage[draft_key]
            return {"success": True, "message": "Draft email deleted"}
        else:
            return {"success": False, "message": "No draft email found for this thread"}
    except Exception as e:
        return {"error": f"Failed to delete draft: {str(e)}"}


def create_draft_calendar_event(
    thread_id: str,
    title: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    attendees: str | None = None,
    location: str | None = None,
    description: str | None = None,
) -> Dict[str, Any]:
    try:
        draft_key = f"{thread_id}_calendar_event"
        draft = (
            _draft_storage[draft_key].copy()
            if draft_key in _draft_storage
            else {
                "type": "calendar_event",
                "thread_id": thread_id,
                "created_at": "2025-06-07T00:00:00Z",
            }
        )
        if title is not None:
            draft["title"] = title
        if start_time is not None:
            draft["start_time"] = start_time
        if end_time is not None:
            draft["end_time"] = end_time
        if attendees is not None:
            draft["attendees"] = attendees
        if location is not None:
            draft["location"] = location
        if description is not None:
            draft["description"] = description
        draft["updated_at"] = "2025-06-07T00:00:00Z"
        _draft_storage[draft_key] = draft
        return {"success": True, "draft": draft}
    except Exception as e:
        return {"error": f"Failed to create/update draft: {str(e)}"}


def delete_draft_calendar_event(thread_id: str) -> Dict[str, Any]:
    try:
        draft_key = f"{thread_id}_calendar_event"
        if draft_key in _draft_storage:
            del _draft_storage[draft_key]
            return {"success": True, "message": "Calendar event draft deleted"}
        else:
            return {"success": False, "message": "No calendar event draft found"}
    except Exception as e:
        return {
            "success": False,
            "message": f"Error deleting calendar event draft: {str(e)}",
        }


def create_draft_calendar_change(
    thread_id: str,
    event_id: str,
    change_type: str | None = None,
    new_title: str | None = None,
    new_start_time: str | None = None,
    new_end_time: str | None = None,
    new_attendees: str | None = None,
    new_location: str | None = None,
    new_description: str | None = None,
) -> Dict[str, Any]:
    """
    Create a draft for editing an existing calendar event.
    This creates a local draft that will be sent to the client for execution.

    Args:
        thread_id: Thread ID for the conversation
        event_id: ID of the calendar event to edit (format: provider_originalId) - REQUIRED
        change_type: Type of change (update, reschedule, etc.)
        new_title: New event title
        new_start_time: New start time (ISO format)
        new_end_time: New end time (ISO format)
        new_attendees: New attendees (comma-separated email addresses)
        new_location: New location
        new_description: New description

    Returns:
        Dictionary with success status and draft details
    """
    try:
        # Validate required parameters
        if not event_id or not event_id.strip():
            return {
                "success": False,
                "message": "event_id is required and cannot be empty",
            }

        draft_key = f"{thread_id}_calendar_edit"

        # Build the edit draft with only provided fields
        edit_draft: Dict[str, Any] = {
            "type": "calendar_event_edit",
            "thread_id": thread_id,
            "event_id": event_id.strip(),
            "change_type": change_type or "update",
            "created_at": "2025-06-07T00:00:00Z",
            "changes": {},
        }

        # Add only the fields that were provided
        if new_title is not None:
            edit_draft["changes"]["title"] = new_title
        if new_start_time is not None:
            edit_draft["changes"]["start_time"] = new_start_time
        if new_end_time is not None:
            edit_draft["changes"]["end_time"] = new_end_time
        if new_location is not None:
            edit_draft["changes"]["location"] = new_location
        if new_description is not None:
            edit_draft["changes"]["description"] = new_description

        # Handle attendees - convert comma-separated string to list
        if new_attendees is not None:
            attendee_list = []
            for email in new_attendees.split(","):
                email = email.strip()
                if email:
                    attendee_list.append({"email": email, "name": email})
            edit_draft["changes"]["attendees"] = attendee_list

        if not edit_draft["changes"]:
            return {"success": False, "message": "No changes provided to edit"}

        # Store the edit draft
        _draft_storage[draft_key] = edit_draft

        return {
            "success": True,
            "message": f"Calendar event edit draft created for event {event_id}",
            "draft": edit_draft,
            "changes_count": len(edit_draft["changes"]),
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating calendar event edit draft: {str(e)}",
        }


def delete_draft_calendar_edit(thread_id: str) -> Dict[str, Any]:
    """Delete the draft calendar event edit for the given thread."""
    try:
        draft_key = f"{thread_id}_calendar_edit"
        if draft_key in _draft_storage:
            del _draft_storage[draft_key]
            return {"success": True, "message": "Calendar event edit draft deleted"}
        else:
            return {"success": False, "message": "No calendar event edit draft found"}
    except Exception as e:
        return {
            "success": False,
            "message": f"Error deleting calendar event edit draft: {str(e)}",
        }


def get_draft_calendar_edit(thread_id: str) -> Optional[Dict[str, Any]]:
    """Get the calendar event edit draft for the given thread, if it exists."""
    draft_key = f"{thread_id}_calendar_edit"
    return _draft_storage.get(draft_key)


def has_draft_calendar_edit(thread_id: str) -> bool:
    """Check if a calendar event edit draft exists for the given thread."""
    draft_key = f"{thread_id}_calendar_edit"
    return draft_key in _draft_storage


# --- Tool Registry ---


def make_tools() -> Dict[str, FunctionTool]:
    # Create tools without partial application since office_service_url is now from settings
    get_calendar_events_tool = FunctionTool.from_defaults(
        fn=get_calendar_events,
        name="get_calendar_events",
        description="Retrieve calendar events from office service.",
    )
    get_emails_tool = FunctionTool.from_defaults(
        fn=get_emails,
        name="get_emails",
        description="Retrieve emails from office service.",
    )
    get_notes_tool = FunctionTool.from_defaults(
        fn=get_notes,
        name="get_notes",
        description="Retrieve notes from office service.",
    )
    get_documents_tool = FunctionTool.from_defaults(
        fn=get_documents,
        name="get_documents",
        description="Retrieve documents from office service.",
    )
    create_draft_email_tool = FunctionTool.from_defaults(
        fn=create_draft_email,
        name="create_draft_email",
        description="Create or update draft email in the current conversation.",
    )
    delete_draft_email_tool = FunctionTool.from_defaults(
        fn=delete_draft_email,
        name="delete_draft_email",
        description="Delete draft email in the current conversation.",
    )
    create_draft_calendar_event_tool = FunctionTool.from_defaults(
        fn=create_draft_calendar_event,
        name="create_draft_calendar_event",
        description="Create or update a draft calendar event in the current conversation. Use this tool for both creating new calendar event drafts AND modifying existing calendar event drafts (e.g., changing time, location, attendees, etc.). If a draft already exists, it will be updated with the new values.",
    )
    delete_draft_calendar_event_tool = FunctionTool.from_defaults(
        fn=delete_draft_calendar_event,
        name="delete_draft_calendar_event",
        description="Delete draft calendar event in the current conversation.",
    )
    create_draft_calendar_change_tool = FunctionTool.from_defaults(
        fn=create_draft_calendar_change,
        name="create_draft_calendar_change",
        description="[DEPRECATED] Create or update draft calendar change in the current conversation. Use create_draft_calendar_event instead for all calendar draft operations.",
    )

    return {
        "get_calendar_events": get_calendar_events_tool,
        "get_emails": get_emails_tool,
        "get_notes": get_notes_tool,
        "get_documents": get_documents_tool,
        "create_draft_email": create_draft_email_tool,
        "delete_draft_email": delete_draft_email_tool,
        "create_draft_calendar_event": create_draft_calendar_event_tool,
        "delete_draft_calendar_event": delete_draft_calendar_event_tool,
        "create_draft_calendar_change": create_draft_calendar_change_tool,
    }


class ToolRegistry:
    def __init__(self):
        self._tools = make_tools()

    def get_tool(self, tool_name: str):
        return self._tools.get(tool_name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def get_tool_schemas(self) -> Dict[str, Dict[str, Any]]:
        schemas = {}
        for name, tool in self._tools.items():
            if hasattr(tool, "to_openai_tool"):
                schemas[name] = tool.to_openai_tool()
            else:
                schemas[name] = {}
        return schemas

    def execute_tool(self, tool_name: str, **kwargs):
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolOutput(
                content=f"Tool '{tool_name}' not found",
                tool_name=tool_name,
                raw_input=kwargs,
                raw_output={"error": f"Tool '{tool_name}' not found"},
                is_error=True,
            )
        try:
            result = tool(**kwargs)
            # If already ToolOutput, return as is
            if hasattr(result, "raw_output"):
                return result
            # Otherwise, wrap in ToolOutput
            return ToolOutput(
                content=str(result),
                tool_name=tool_name,
                raw_input=kwargs,
                raw_output=result,
                is_error=False,
            )
        except Exception as e:
            return ToolOutput(
                content=f"Tool execution failed: {str(e)}",
                tool_name=tool_name,
                raw_input=kwargs,
                raw_output={"error": f"Tool execution failed: {str(e)}"},
                is_error=True,
            )


_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
