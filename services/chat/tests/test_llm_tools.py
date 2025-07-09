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
    """Mock settings for all tests to work in parallel execution."""
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


@pytest.fixture(autouse=True)
def mock_requests():
    """Mock requests module for all tests to work in parallel execution."""
    with patch("services.chat.agents.llm_tools.requests.get") as mock_get:
        yield mock_get


def test_get_calendar_events_success(mock_requests):
    def mock_get(*args, **kwargs):
        url = args[0] if args else ""
        if "internal/users" in url and "integrations" in url:
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

    mock_requests.side_effect = mock_get
    result = get_calendar_events(
        "user123",
        start_date="2025-06-05",
        end_date="2025-06-06",
        time_zone="UTC",
        providers="google",
    )
    assert "events" in result
    assert result["events"][0]["title"] == "Meeting"


def test_get_calendar_events_malformed(mock_requests):
    def mock_get(*args, **kwargs):
        url = args[0] if args else ""
        if "internal/users" in url and "integrations" in url:
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
            return MockResponse({"success": True, "data": {"bad": "data"}}, 200)

    mock_requests.side_effect = mock_get
    result = get_calendar_events("user123")
    assert "error" in result
    assert "Malformed" in result["error"]


def test_get_calendar_events_timeout(mock_requests):
    def mock_get(*args, **kwargs):
        url = args[0] if args else ""
        if "internal/users" in url and "integrations" in url:
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
            raise requests.Timeout()

    mock_requests.side_effect = mock_get
    result = get_calendar_events("user123")
    assert "error" in result
    assert "timed out" in result["error"]


def test_get_calendar_events_http_error(mock_requests):
    def mock_get(*args, **kwargs):
        url = args[0] if args else ""
        if "internal/users" in url and "integrations" in url:
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
            return MockResponse({}, 500)

    mock_requests.side_effect = mock_get
    result = get_calendar_events("user123")
    assert "error" in result
    assert "HTTP error" in result["error"]


def test_get_calendar_events_unexpected(mock_requests):
    def mock_get(*args, **kwargs):
        url = args[0] if args else ""
        if "internal/users" in url and "integrations" in url:
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
            raise Exception("boom")

    mock_requests.side_effect = mock_get
    result = get_calendar_events("user123")
    assert "error" in result
    assert "Unexpected error" in result["error"]


def test_get_emails_success(mock_requests):
    def mock_get(*args, **kwargs):
        return MockResponse(
            {
                "success": True,
                "data": {
                    "emails": [
                        {
                            "id": "1",
                            "subject": "Test Email",
                            "from": "test@example.com",
                            "to": "user123@example.com",
                        }
                    ]
                },
            },
            200,
        )

    mock_requests.side_effect = mock_get
    result = get_emails("user123", unread_only=True, folder="inbox", max_results=10)
    assert "emails" in result
    assert result["emails"][0]["subject"] == "Test Email"


def test_get_emails_malformed(mock_requests):
    def mock_get(*args, **kwargs):
        return MockResponse({"success": True, "data": {"bad": "data"}}, 200)

    mock_requests.side_effect = mock_get
    result = get_emails("user123")
    assert "error" in result
    assert "Malformed" in result["error"]


def test_get_emails_timeout(mock_requests):
    def mock_get(*args, **kwargs):
        raise requests.Timeout()

    mock_requests.side_effect = mock_get
    result = get_emails("user123")
    assert "error" in result
    assert "timed out" in result["error"]


def test_get_emails_http_error(mock_requests):
    def mock_get(*args, **kwargs):
        return MockResponse({}, 404)

    mock_requests.side_effect = mock_get
    result = get_emails("user123")
    assert "error" in result
    assert "HTTP error" in result["error"]


def test_get_emails_unexpected(mock_requests):
    def mock_get(*args, **kwargs):
        raise Exception("boom")

    mock_requests.side_effect = mock_get
    result = get_emails("user123")
    assert "error" in result
    assert "Unexpected error" in result["error"]


def test_get_notes_success(mock_requests):
    def mock_get(*args, **kwargs):
        return MockResponse(
            {
                "success": True,
                "data": {
                    "notes": [
                        {
                            "id": "1",
                            "title": "Test Note",
                            "content": "This is a test note.",
                        }
                    ]
                },
            },
            200,
        )

    mock_requests.side_effect = mock_get
    result = get_notes(
        "user123",
        notebook="work",
        tags="important",
        search_query="test",
        max_results=5,
    )
    assert "notes" in result
    assert result["notes"][0]["title"] == "Test Note"


def test_get_documents_success(mock_requests):
    def mock_get(*args, **kwargs):
        return MockResponse(
            {
                "success": True,
                "data": {
                    "documents": [
                        {
                            "id": "1",
                            "title": "Test Document",
                            "type": "word",
                        }
                    ]
                },
            },
            200,
        )

    mock_requests.side_effect = mock_get
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


def test_tool_registry(mock_requests):
    def mock_get(*args, **kwargs):
        url = args[0]
        if "internal/users" in url and "integrations" in url:
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
        if "calendar/events" in url:
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
                        "emails": [{"id": "1", "subject": "Test Email"}],
                    },
                },
                200,
            )
        else:
            return MockResponse({"error": "Not found"}, 404)
    mock_requests.side_effect = mock_get
    registry = get_tool_registry()
    calendar_result = registry.execute_tool("get_calendar_events", user_id="user123")
    assert "events" in calendar_result.raw_output
    email_result = registry.execute_tool("get_emails", user_id="user123")
    assert "emails" in email_result.raw_output


def test_tool_registry_tooloutput_success(mock_requests):
    def mock_get(*args, **kwargs):
        url = args[0]
        if "internal/users" in url and "integrations" in url:
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
        if "calendar/events" in url:
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
        else:
            return MockResponse({"success": True, "data": {"emails": [{"id": "1", "subject": "Test Email"}]}}, 200)
    mock_requests.side_effect = mock_get
    registry = get_tool_registry()
    calendar_result = registry.execute_tool("get_calendar_events", user_id="user123")
    assert hasattr(calendar_result, "raw_output")
    assert "events" in calendar_result.raw_output


def test_tool_registry_tooloutput_error(mock_requests):
    registry = get_tool_registry()
    error_result = registry.execute_tool("calendar")
    assert hasattr(error_result, "raw_output")
    assert "error" in error_result.raw_output


def test_tool_registry_tooloutput_for_get_tools(mock_requests):
    def mock_get(*args, **kwargs):
        url = args[0]
        if "internal/users" in url and "integrations" in url:
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
        if "calendar/events" in url:
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
        else:
            return MockResponse({"success": True, "data": {"emails": [{"id": "1", "subject": "Test Email"}]}}, 200)
    mock_requests.side_effect = mock_get
    registry = get_tool_registry()
    calendar_result = registry.execute_tool("get_calendar_events", user_id="user123")
    assert "events" in calendar_result.raw_output
    email_result = registry.execute_tool("get_emails", user_id="user123")
    assert "emails" in email_result.raw_output


def test_tool_registry_execute_tool_returns_tooloutput(mock_requests):
    def mock_get(*args, **kwargs):
        url = args[0]
        if "internal/users" in url and "integrations" in url:
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
        if "calendar/events" in url:
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
        else:
            return MockResponse({"success": True, "data": {"emails": [{"id": "1", "subject": "Test Email"}]}}, 200)
    mock_requests.side_effect = mock_get
    registry = get_tool_registry()
    email_result = registry.execute_tool("get_emails", user_id="user123")
    assert hasattr(email_result, "raw_output")
    assert "emails" in email_result.raw_output
    calendar_result = registry.execute_tool("get_calendar_events", user_id="user123")
    assert hasattr(calendar_result, "raw_output")
    assert "events" in calendar_result.raw_output


def test_tool_registry_execute_tool_error(mock_requests):
    registry = get_tool_registry()
    result = registry.execute_tool("calendar")
    assert hasattr(result, "raw_output")
    assert "error" in result.raw_output


def test_get_tool_registry_singleton(mock_requests):
    registry1 = get_tool_registry()
    registry2 = get_tool_registry()
    assert registry1 is registry2
