from unittest.mock import MagicMock, patch

import pytest
import requests

from services.chat.agents.llm_tools import (
    _draft_storage,
    create_draft_calendar_change,
    create_draft_calendar_event,
    create_draft_email,
    delete_draft_calendar_edit,
    delete_draft_calendar_event,
    delete_draft_email,
    get_calendar_events,
    get_documents,
    get_emails,
    get_notes,
    get_tool_registry,
)


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError()


@pytest.fixture(autouse=True)
def clear_drafts():
    """Clear draft storage before each test."""
    _draft_storage.clear()


@pytest.fixture(autouse=True)
def mock_settings():
    with patch("services.chat.agents.llm_tools.get_settings") as mock_get_settings:
        # Create a mock settings object with all required attributes
        mock_settings_obj = MagicMock()
        mock_settings_obj.db_url_chat = "sqlite:///test.db"
        mock_settings_obj.api_chat_user_key = "test-api-key"
        mock_settings_obj.api_chat_office_key = "test-api-key"
        mock_settings_obj.api_frontend_chat_key = "test-api-key"
        mock_settings_obj.user_management_service_url = "http://test-user-server"
        mock_settings_obj.office_service_url = "http://test-office-server"
        mock_settings_obj.llm_provider = "fake"
        mock_settings_obj.llm_model = "fake-model"
        mock_settings_obj.max_tokens = 2000
        mock_settings_obj.openai_api_key = None
        mock_settings_obj.service_name = "chat-service"
        mock_settings_obj.host = "0.0.0.0"
        mock_settings_obj.port = 8000
        mock_settings_obj.debug = False
        mock_settings_obj.environment = "test"
        mock_settings_obj.log_level = "INFO"
        mock_settings_obj.log_format = "json"

        mock_get_settings.return_value = mock_settings_obj
        yield mock_settings_obj


def test_get_calendar_events_success(monkeypatch):
    def mock_get(*args, **kwargs):
        # Check if this is a call to user service (integrations) or office service (calendar)
        url = args[0] if args else ""
        if "internal/users" in url and "integrations" in url:
            # Mock user service response for integrations
            return MockResponse(
                {
                    "integrations": [
                        {
                            "id": 1,
                            "provider": "google",
                            "status": "active",
                            "external_user_id": "user123",
                            "scopes": ["calendar"],
                        }
                    ],
                    "total": 1,
                    "active_count": 1,
                    "error_count": 0,
                },
                200,
            )
        else:
            # Mock office service response for calendar events
            return MockResponse(
                {
                    "success": True,
                    "data": {
                        "events": [{"id": "1", "title": "Meeting"}],
                        "total_count": 1,
                        "providers_used": ["google"],
                        "provider_errors": None,
                    },
                },
                200,
            )

    monkeypatch.setattr(requests, "get", mock_get)
    result = get_calendar_events(
        "user123",
        start_date="2025-06-05",
        end_date="2025-06-06",
        time_zone="UTC",
        providers="google",
    )
    assert "events" in result
    assert result["events"][0]["title"] == "Meeting"


def test_get_calendar_events_malformed(monkeypatch):
    def mock_get(*args, **kwargs):
        # Check if this is a call to user service (integrations) or office service (calendar)
        url = args[0] if args else ""
        if "internal/users" in url and "integrations" in url:
            # Mock user service response for integrations
            return MockResponse(
                {
                    "integrations": [
                        {
                            "id": 1,
                            "provider": "google",
                            "status": "active",
                            "external_user_id": "user123",
                            "scopes": ["calendar"],
                        }
                    ],
                    "total": 1,
                    "active_count": 1,
                    "error_count": 0,
                },
                200,
            )
        else:
            # Mock office service response with malformed data
            return MockResponse({"success": True, "data": {"bad": "data"}}, 200)

    monkeypatch.setattr(requests, "get", mock_get)
    result = get_calendar_events("user123")
    assert "error" in result
    assert "Malformed" in result["error"]


def test_get_calendar_events_timeout(monkeypatch):
    def mock_get(*args, **kwargs):
        # Check if this is a call to user service (integrations) or office service (calendar)
        url = args[0] if args else ""
        if "internal/users" in url and "integrations" in url:
            # Mock user service response for integrations
            return MockResponse(
                {
                    "integrations": [
                        {
                            "id": 1,
                            "provider": "google",
                            "status": "active",
                            "external_user_id": "user123",
                            "scopes": ["calendar"],
                        }
                    ],
                    "total": 1,
                    "active_count": 1,
                    "error_count": 0,
                },
                200,
            )
        else:
            # Mock office service timeout
            raise requests.Timeout()

    monkeypatch.setattr(requests, "get", mock_get)
    result = get_calendar_events("user123")
    assert "error" in result
    assert "timed out" in result["error"]


def test_get_calendar_events_http_error(monkeypatch):
    def mock_get(*args, **kwargs):
        # Check if this is a call to user service (integrations) or office service (calendar)
        url = args[0] if args else ""
        if "internal/users" in url and "integrations" in url:
            # Mock user service response for integrations
            return MockResponse(
                {
                    "integrations": [
                        {
                            "id": 1,
                            "provider": "google",
                            "status": "active",
                            "external_user_id": "user123",
                            "scopes": ["calendar"],
                        }
                    ],
                    "total": 1,
                    "active_count": 1,
                    "error_count": 0,
                },
                200,
            )
        else:
            # Mock office service HTTP error
            return MockResponse({}, 500)

    monkeypatch.setattr(requests, "get", mock_get)
    result = get_calendar_events("user123")
    assert "error" in result
    assert "HTTP error" in result["error"]


def test_get_calendar_events_unexpected(monkeypatch):
    def mock_get(*args, **kwargs):
        # Check if this is a call to user service (integrations) or office service (calendar)
        url = args[0] if args else ""
        if "internal/users" in url and "integrations" in url:
            # Mock user service response for integrations
            return MockResponse(
                {
                    "integrations": [
                        {
                            "id": 1,
                            "provider": "google",
                            "status": "active",
                            "external_user_id": "user123",
                            "scopes": ["calendar"],
                        }
                    ],
                    "total": 1,
                    "active_count": 1,
                    "error_count": 0,
                },
                200,
            )
        else:
            # Mock office service unexpected error
            raise Exception("boom")

    monkeypatch.setattr(requests, "get", mock_get)
    result = get_calendar_events("user123")
    assert "error" in result
    assert "Unexpected error" in result["error"]


def test_get_emails_success(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse(
            {
                "success": True,
                "data": {
                    "emails": [{"id": "1", "subject": "Test Email"}],
                    "total_count": 1,
                },
            },
            200,
        )

    monkeypatch.setattr(requests, "get", mock_get)
    result = get_emails("user123", unread_only=True, folder="inbox", max_results=10)
    assert "emails" in result
    assert result["emails"][0]["subject"] == "Test Email"


def test_get_emails_malformed(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse({"success": True, "data": {"bad": "data"}}, 200)

    monkeypatch.setattr(requests, "get", mock_get)
    result = get_emails("user123")
    assert "error" in result
    assert "Malformed" in result["error"]


def test_get_emails_timeout(monkeypatch):
    def mock_get(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "get", mock_get)
    result = get_emails("user123")
    assert "error" in result
    assert "timed out" in result["error"]


def test_get_emails_http_error(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse({}, 404)

    monkeypatch.setattr(requests, "get", mock_get)
    result = get_emails("user123")
    assert "error" in result
    assert "HTTP error" in result["error"]


def test_get_emails_unexpected(monkeypatch):
    def mock_get(*args, **kwargs):
        raise Exception("boom")

    monkeypatch.setattr(requests, "get", mock_get)
    result = get_emails("user123")
    assert "error" in result
    assert "Unexpected error" in result["error"]


def test_get_notes_success(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse(
            {
                "success": True,
                "data": {
                    "notes": [{"id": "1", "title": "Test Note"}],
                    "total_count": 1,
                },
            },
            200,
        )

    monkeypatch.setattr(requests, "get", mock_get)
    result = get_notes(
        "user123",
        notebook="work",
        tags="important",
        search_query="project",
        max_results=5,
    )
    assert "notes" in result
    assert result["notes"][0]["title"] == "Test Note"


def test_get_documents_success(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse(
            {
                "success": True,
                "data": {
                    "documents": [{"id": "1", "title": "Test Document"}],
                    "total_count": 1,
                },
            },
            200,
        )

    monkeypatch.setattr(requests, "get", mock_get)
    result = get_documents(
        "user123", document_type="word", search_query="project", max_results=10
    )
    assert "documents" in result
    assert result["documents"][0]["title"] == "Test Document"


def test_create_draft_email():
    result = create_draft_email(
        thread_id="thread123", to="test@example.com", subject="Test", body="Body"
    )
    assert result["success"] is True
    assert "draft" in result
    assert result["draft"]["to"] == "test@example.com"


def test_delete_draft_email():
    create_draft_email(thread_id="thread123", to="test@example.com")
    result = delete_draft_email(thread_id="thread123")
    assert result["success"] is True
    assert "deleted" in result["message"]


def test_create_draft_calendar_event():
    result = create_draft_calendar_event(
        thread_id="thread123",
        title="Meeting",
        start_time="2025-06-07T10:00:00Z",
        end_time="2025-06-07T11:00:00Z",
    )
    assert result["success"] is True
    assert "draft" in result
    assert result["draft"]["title"] == "Meeting"


def test_delete_draft_calendar_event():
    create_draft_calendar_event(thread_id="thread123", title="Meeting")
    result = delete_draft_calendar_event(thread_id="thread123")
    assert result["success"] is True
    assert "deleted" in result["message"]


def test_create_draft_calendar_change():
    result = create_draft_calendar_change(
        thread_id="thread123",
        event_id="event456",
        change_type="reschedule",
        new_start_time="2025-06-08T10:00:00Z",
        new_end_time="2025-06-08T11:00:00Z",
    )
    assert result["success"] is True
    assert "draft" in result
    assert result["draft"]["event_id"] == "event456"


def test_delete_draft_calendar_change():
    create_draft_calendar_change(
        thread_id="thread123",
        event_id="event456",
        change_type="cancel",
        new_title="Updated Meeting",
    )
    result = delete_draft_calendar_edit(thread_id="thread123")
    assert result["success"] is True
    assert "deleted" in result["message"]


def test_draft_tools_thread_isolation():
    create_draft_email(thread_id="thread1", to="user1@example.com")
    create_draft_email(thread_id="thread2", to="user2@example.com")
    create_draft_calendar_event(thread_id="thread1", title="Meeting 1")
    create_draft_calendar_event(thread_id="thread2", title="Meeting 2")
    assert "thread1_email" in _draft_storage
    assert "thread2_email" in _draft_storage
    assert "thread1_calendar_event" in _draft_storage
    assert "thread2_calendar_event" in _draft_storage
    assert _draft_storage["thread1_email"]["to"] == "user1@example.com"
    assert _draft_storage["thread2_email"]["to"] == "user2@example.com"
    assert _draft_storage["thread1_calendar_event"]["title"] == "Meeting 1"
    assert _draft_storage["thread2_calendar_event"]["title"] == "Meeting 2"


def test_tool_registry(monkeypatch):
    def mock_get(*args, **kwargs):
        url = args[0]
        if "internal/users" in url and "integrations" in url:
            # Mock user service response for integrations
            return MockResponse(
                {
                    "integrations": [
                        {
                            "id": 1,
                            "provider": "google",
                            "status": "active",
                            "external_user_id": "user123",
                            "scopes": ["calendar"],
                        }
                    ],
                    "total": 1,
                    "active_count": 1,
                    "error_count": 0,
                },
                200,
            )
        elif "events" in url:
            return MockResponse(
                {
                    "success": True,
                    "data": {
                        "events": [{"id": "1", "title": "Meeting"}],
                        "total_count": 1,
                        "providers_used": ["google"],
                        "provider_errors": None,
                    },
                },
                200,
            )
        elif "emails" in url:
            return MockResponse(
                {
                    "success": True,
                    "data": {
                        "emails": [{"id": "1", "subject": "Email"}],
                        "total_count": 1,
                    },
                },
                200,
            )
        elif "notes" in url:
            return MockResponse(
                {
                    "success": True,
                    "data": {"notes": [{"id": "1", "title": "Note"}], "total_count": 1},
                },
                200,
            )
        elif "documents" in url:
            return MockResponse(
                {
                    "success": True,
                    "data": {
                        "documents": [{"id": "1", "title": "Doc"}],
                        "total_count": 1,
                    },
                },
                200,
            )
        return MockResponse({"error": "Not found"}, 404)

    monkeypatch.setattr(requests, "get", mock_get)
    registry = get_tool_registry()
    # Calendar
    calendar_result = registry.execute_tool("get_calendar_events", user_id="user123")
    assert "events" in calendar_result.raw_output
    # Email
    email_result = registry.execute_tool(
        "get_emails", user_id="user123", unread_only=True
    )
    assert "emails" in email_result.raw_output
    # Notes
    notes_result = registry.execute_tool("get_notes", user_id="user123")
    assert "notes" in notes_result.raw_output
    # Documents
    documents_result = registry.execute_tool("get_documents", user_id="user123")
    assert "documents" in documents_result.raw_output
    # Draft email
    draft_result = registry.execute_tool(
        "create_draft_email",
        thread_id="thread",
        to="colleague@example.com",
        subject="Subject",
        body="Body",
    )
    assert draft_result.raw_output.get("success") is True
    # Draft calendar event
    event_result = registry.execute_tool(
        "create_draft_calendar_event",
        thread_id="thread",
        title="Meeting",
        start_time="2025-06-08T10:00:00Z",
        end_time="2025-06-08T11:00:00Z",
    )
    assert event_result.raw_output.get("success") is True
    # Delete drafts
    delete_email_result = registry.execute_tool(
        "delete_draft_email", thread_id="thread"
    )
    assert delete_email_result.raw_output.get("success") is True
    delete_event_result = registry.execute_tool(
        "delete_draft_calendar_event", thread_id="thread"
    )
    assert delete_event_result.raw_output.get("success") is True


def test_tool_registry_tooloutput_success(monkeypatch):
    # This test checks that ToolOutput objects returned by registry.execute_tool
    # have a .raw_output attribute containing the original dict, and that
    # success is only present in .raw_output, not as a direct attribute.
    def mock_get(*args, **kwargs):
        url = args[0]
        if "internal/users" in url and "integrations" in url:
            # Mock user service response for integrations
            return MockResponse(
                {
                    "integrations": [
                        {
                            "id": 1,
                            "provider": "google",
                            "status": "active",
                            "external_user_id": "user123",
                            "scopes": ["calendar"],
                        }
                    ],
                    "total": 1,
                    "active_count": 1,
                    "error_count": 0,
                },
                200,
            )
        else:
            # Mock office service response
            return MockResponse(
                {
                    "success": True,
                    "data": {
                        "events": [{"id": "1", "title": "Meeting"}],
                        "total_count": 1,
                        "providers_used": ["google"],
                        "provider_errors": None,
                    },
                },
                200,
            )

    monkeypatch.setattr(requests, "get", mock_get)
    registry = get_tool_registry()
    # Call a tool that returns a dict with 'success'
    draft_result = registry.execute_tool(
        "create_draft_email",
        thread_id="thread",
        to="colleague@example.com",
        subject="Subject",
        body="Body",
    )
    # ToolOutput should have .raw_output, not .success
    assert hasattr(draft_result, "raw_output")
    assert isinstance(draft_result.raw_output, dict)
    assert draft_result.raw_output.get("success") is True
    # .success attribute should not exist
    assert not hasattr(draft_result, "success")
    # For backward compatibility, check that .raw_output["draft"]["to"] is correct
    assert draft_result.raw_output["draft"]["to"] == "colleague@example.com"


def test_tool_registry_tooloutput_error(monkeypatch):
    # This test checks that ToolOutput objects wrap error dicts as .raw_output
    registry = get_tool_registry()
    result = registry.execute_tool("not_a_tool")
    assert hasattr(result, "raw_output")
    assert isinstance(result.raw_output, dict)
    assert "error" in result.raw_output
    assert "not found" in result.raw_output["error"]


def test_tool_registry_tooloutput_for_get_tools(monkeypatch):
    # This test checks that ToolOutput is returned for get_calendar_events and contains expected keys
    def mock_get(*args, **kwargs):
        url = args[0]
        if "internal/users" in url and "integrations" in url:
            # Mock user service response for integrations
            return MockResponse(
                {
                    "integrations": [
                        {
                            "id": 1,
                            "provider": "google",
                            "status": "active",
                            "external_user_id": "user123",
                            "scopes": ["calendar"],
                        }
                    ],
                    "total": 1,
                    "active_count": 1,
                    "error_count": 0,
                },
                200,
            )
        else:
            # Mock office service response
            return MockResponse(
                {
                    "success": True,
                    "data": {
                        "events": [{"id": "1", "title": "Meeting"}],
                        "total_count": 1,
                        "providers_used": ["google"],
                        "provider_errors": None,
                    },
                },
                200,
            )

    monkeypatch.setattr(requests, "get", mock_get)
    registry = get_tool_registry()
    calendar_result = registry.execute_tool("get_calendar_events", user_id="user123")
    assert hasattr(calendar_result, "raw_output")
    assert "events" in calendar_result.raw_output
    assert isinstance(calendar_result.raw_output["events"], list)
    assert len(calendar_result.raw_output["events"]) > 0
    assert "title" in calendar_result.raw_output["events"][0]


def test_tool_registry_execute_tool_returns_tooloutput(monkeypatch):
    # This test checks that all registry.execute_tool calls return a ToolOutput object (except for errors)
    def mock_get(*args, **kwargs):
        url = args[0]
        if "internal/users" in url and "integrations" in url:
            # Mock user service response for integrations
            return MockResponse(
                {
                    "integrations": [
                        {
                            "id": 1,
                            "provider": "google",
                            "status": "active",
                            "external_user_id": "user123",
                            "scopes": ["calendar"],
                        }
                    ],
                    "total": 1,
                    "active_count": 1,
                    "error_count": 0,
                },
                200,
            )
        else:
            # Mock office service response
            return MockResponse(
                {
                    "success": True,
                    "data": {
                        "emails": [{"id": "1", "subject": "Email"}],
                        "total_count": 1,
                    },
                },
                200,
            )

    monkeypatch.setattr(requests, "get", mock_get)
    registry = get_tool_registry()
    email_result = registry.execute_tool("get_emails", user_id="user123")
    # Should be a ToolOutput-like object with .raw_output
    assert hasattr(email_result, "raw_output")
    assert "emails" in email_result.raw_output
    assert isinstance(email_result.raw_output["emails"], list)
    assert len(email_result.raw_output["emails"]) > 0
    assert "subject" in email_result.raw_output["emails"][0]


def test_tool_registry_execute_tool_error():
    registry = get_tool_registry()
    result = registry.execute_tool("calendar")
    # Should be a ToolOutput-like object with .raw_output
    assert hasattr(result, "raw_output")
    assert isinstance(result.raw_output, dict)
    assert "error" in result.raw_output
    assert "Tool 'calendar' not found" in result.raw_output["error"]


def test_get_tool_registry_singleton():
    registry1 = get_tool_registry()
    registry2 = get_tool_registry()
    assert registry1 is registry2
