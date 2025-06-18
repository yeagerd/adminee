from typing import Any, Dict, Optional

import requests
from llama_index.core.tools import FunctionTool
from llama_index.core.tools.types import ToolOutput

from services.chat.settings import get_settings


def get_calendar_events(
    user_token: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_timezone: Optional[str] = None,
    provider_type: Optional[str] = None,
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if user_timezone:
        params["user_timezone"] = user_timezone
    if provider_type:
        params["provider_type"] = provider_type
    try:
        office_service_url = get_settings().office_service_url
        response = requests.get(
            f"{office_service_url}/events",
            headers=headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if "events" not in data:
            return {"error": "Malformed response from office-service."}
        return {"events": data["events"]}
    except requests.Timeout:
        return {"error": "Request to office-service timed out."}
    except requests.HTTPError as e:
        return {"error": f"HTTP error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def get_emails(
    user_token: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    unread_only: Optional[bool] = None,
    folder: Optional[str] = None,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {}
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
        office_service_url = get_settings().office_service_url
        response = requests.get(
            f"{office_service_url}/emails",
            headers=headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if "emails" not in data:
            return {"error": "Malformed response from office-service."}
        return {"emails": data["emails"]}
    except requests.Timeout:
        return {"error": "Request to office-service timed out."}
    except requests.HTTPError as e:
        return {"error": f"HTTP error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def get_notes(
    user_token: str,
    notebook: Optional[str] = None,
    tags: Optional[str] = None,
    search_query: Optional[str] = None,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {}
    if notebook:
        params["notebook"] = notebook
    if tags:
        params["tags"] = tags
    if search_query:
        params["search_query"] = search_query
    if max_results:
        params["max_results"] = str(max_results)
    try:
        office_service_url = get_settings().office_service_url
        response = requests.get(
            f"{office_service_url}/notes",
            headers=headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if "notes" not in data:
            return {"error": "Malformed response from office-service."}
        return {"notes": data["notes"]}
    except requests.Timeout:
        return {"error": "Request to office-service timed out."}
    except requests.HTTPError as e:
        return {"error": f"HTTP error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def get_documents(
    user_token: str,
    document_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search_query: Optional[str] = None,
    max_results: Optional[int] = None,
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {}
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
        office_service_url = get_settings().office_service_url
        response = requests.get(
            f"{office_service_url}/documents",
            headers=headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if "documents" not in data:
            return {"error": "Malformed response from office-service."}
        return {"documents": data["documents"]}
    except requests.Timeout:
        return {"error": "Request to office-service timed out."}
    except requests.HTTPError as e:
        return {"error": f"HTTP error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


# --- Draft Storage and Functions ---
_draft_storage: Dict[str, Dict[str, Any]] = {}


def create_draft_email(
    thread_id: str,
    to: Optional[str] = None,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    subject: Optional[str] = None,
    body: Optional[str] = None,
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
    title: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    attendees: Optional[str] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
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
            return {"success": True, "message": "Draft calendar event deleted"}
        else:
            return {
                "success": False,
                "message": "No draft calendar event found for this thread",
            }
    except Exception as e:
        return {"error": f"Failed to delete draft: {str(e)}"}


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
) -> Dict[str, Any]:
    try:
        draft_key = f"{thread_id}_calendar_change"
        draft = (
            _draft_storage[draft_key].copy()
            if draft_key in _draft_storage
            else {
                "type": "calendar_change",
                "thread_id": thread_id,
                "created_at": "2025-06-07T00:00:00Z",
            }
        )
        if event_id is not None:
            draft["event_id"] = event_id
        if change_type is not None:
            draft["change_type"] = change_type
        if new_title is not None:
            draft["new_title"] = new_title
        if new_start_time is not None:
            draft["new_start_time"] = new_start_time
        if new_end_time is not None:
            draft["new_end_time"] = new_end_time
        if new_attendees is not None:
            draft["new_attendees"] = new_attendees
        if new_location is not None:
            draft["new_location"] = new_location
        if new_description is not None:
            draft["new_description"] = new_description
        draft["updated_at"] = "2025-06-07T00:00:00Z"
        _draft_storage[draft_key] = draft
        return {"success": True, "draft": draft}
    except Exception as e:
        return {"error": f"Failed to create/update draft: {str(e)}"}


def delete_draft_calendar_change(thread_id: str) -> Dict[str, Any]:
    try:
        draft_key = f"{thread_id}_calendar_change"
        if draft_key in _draft_storage:
            del _draft_storage[draft_key]
            return {"success": True, "message": "Draft calendar change deleted"}
        else:
            return {
                "success": False,
                "message": "No draft calendar change found for this thread",
            }
    except Exception as e:
        return {"error": f"Failed to delete draft: {str(e)}"}


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
        description="Create or update draft email for a thread.",
    )
    delete_draft_email_tool = FunctionTool.from_defaults(
        fn=delete_draft_email,
        name="delete_draft_email",
        description="Delete draft email for a thread.",
    )
    create_draft_calendar_event_tool = FunctionTool.from_defaults(
        fn=create_draft_calendar_event,
        name="create_draft_calendar_event",
        description="Create or update draft calendar event for a thread.",
    )
    delete_draft_calendar_event_tool = FunctionTool.from_defaults(
        fn=delete_draft_calendar_event,
        name="delete_draft_calendar_event",
        description="Delete draft calendar event for a thread.",
    )
    create_draft_calendar_change_tool = FunctionTool.from_defaults(
        fn=create_draft_calendar_change,
        name="create_draft_calendar_change",
        description="Create or update draft calendar change for a thread.",
    )
    delete_draft_calendar_change_tool = FunctionTool.from_defaults(
        fn=delete_draft_calendar_change,
        name="delete_draft_calendar_change",
        description="Delete draft calendar change for a thread.",
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
        "delete_draft_calendar_change": delete_draft_calendar_change_tool,
    }


class ToolRegistry:
    def __init__(self):
        self.office_service_url = get_settings().office_service_url
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
