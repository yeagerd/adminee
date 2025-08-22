from unittest.mock import patch

import pytest
import requests


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError()


# All tests now rely on patch_chat_settings_singleton fixture for settings


@pytest.fixture(autouse=True)
def clear_drafts(monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.draft_tools import DraftTools

    draft_tools = DraftTools("test_user_id")
    draft_tools.clear_all_drafts()


@pytest.fixture(autouse=True)
def mock_requests():
    """Mock requests module for all tests to work in parallel execution."""
    with patch("services.chat.tools.data_tools.requests.get") as mock_get:
        yield mock_get


@pytest.fixture(autouse=True)
def patch_chat_settings_singleton():
    import services.chat.settings as chat_settings
    from services.chat.settings import Settings

    chat_settings._settings = Settings(
        api_frontend_chat_key="test-frontend-chat-key",
        api_chat_office_key="test-chat-office-key",
        api_chat_user_key="test-chat-user-key",
        db_url_chat="sqlite:///:memory:",
        user_service_url="http://test-user-server",
        office_service_url="http://test-office-server",
        llm_provider="fake",
        llm_model="fake-model",
        max_tokens=2000,
        openai_api_key=None,
        service_name="chat-service",
        host="0.0.0.0",
        port=8000,
        debug=False,
        environment="test",
        log_level="INFO",
        log_format="json",
        pagination_secret_key="test-pagination-secret-key",
    )
    yield
    chat_settings._settings = None


def test_get_calendar_events_success(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from datetime import datetime, timezone

    from services.chat.tools.data_tools import DataTools
    from services.office.schemas import CalendarEvent, Provider

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
                            "scopes": ["calendar", "email", "notes", "documents"],
                        }
                    ],
                    "total": 1,
                },
                200,
            )
        elif "calendar/events" in url:
            # Create proper CalendarEvent objects
            event1 = CalendarEvent(
                id="google_event_1",
                calendar_id="google_primary",
                title="Daily Standup",
                description=None,
                start_time=datetime(2025, 6, 20, 17, 0, 0, tzinfo=timezone.utc),
                end_time=datetime(2025, 6, 20, 18, 0, 0, tzinfo=timezone.utc),
                all_day=False,
                location=None,
                attendees=[],
                provider=Provider.GOOGLE,
                provider_event_id="google_event_1",
                account_email="test@example.com",
                calendar_name="Primary Calendar",
                created_at=datetime(2025, 6, 20, 16, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 6, 20, 16, 0, 0, tzinfo=timezone.utc),
            )
            event2 = CalendarEvent(
                id="google_event_2",
                calendar_id="google_primary",
                title="Team Meeting",
                description="Weekly team sync",
                start_time=datetime(2025, 6, 21, 14, 0, 0, tzinfo=timezone.utc),
                end_time=datetime(2025, 6, 21, 15, 0, 0, tzinfo=timezone.utc),
                all_day=False,
                location="Conference Room A",
                attendees=[],
                provider=Provider.GOOGLE,
                provider_event_id="google_event_2",
                account_email="test@example.com",
                calendar_name="Primary Calendar",
                created_at=datetime(2025, 6, 20, 16, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 6, 20, 16, 0, 0, tzinfo=timezone.utc),
            )
            return MockResponse(
                {
                    "success": True,
                    "request_id": "test-request-id",
                    "data": {"events": [event1, event2]},
                },
                200,
            )
        else:
            return MockResponse({"error": "Not found"}, 404)

    # Set the side_effect on the mock
    mock_requests.side_effect = mock_get

    data_tools = DataTools("user123")
    result = data_tools.get_calendar_events()
    assert result is not None
    assert "events" in result
    assert len(result["events"]) == 2
    assert result["events"][0]["title"] == "Daily Standup"
    assert result["events"][1]["title"] == "Team Meeting"


def test_get_calendar_events_malformed(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.data_tools import DataTools

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
                            "scopes": ["calendar", "email", "notes", "documents"],
                        }
                    ],
                    "total": 1,
                },
                200,
            )
        elif "calendar/events" in url:
            # Return malformed response
            return MockResponse(
                {
                    "success": True,
                    "request_id": "test-request-id",
                    "data": {
                        "events": [
                            {
                                "id": "google_event_1",
                                "title": "Daily Standup",
                                # Missing required fields
                            }
                        ]
                    },
                },
                200,
            )
        else:
            return MockResponse({"error": "Not found"}, 404)

    # Set the side_effect on the mock
    mock_requests.side_effect = mock_get

    data_tools = DataTools("user123")
    result = data_tools.get_calendar_events()
    assert result is not None
    assert "error" in result
    assert "validation" in result["error"].lower()


def test_get_calendar_events_timeout(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.data_tools import DataTools

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
                            "scopes": ["calendar", "email", "notes", "documents"],
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
    data_tools = DataTools("user123")
    result = data_tools.get_calendar_events()
    assert "error" in result
    assert "timed out" in result["error"]


def test_get_calendar_events_http_error(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.data_tools import DataTools

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
                            "scopes": ["calendar", "email", "notes", "documents"],
                        }
                    ],
                    "total": 1,
                    "active_count": 1,
                    "error_count": 0,
                },
                200,
            )
        else:
            raise requests.HTTPError()

    mock_requests.side_effect = mock_get
    data_tools = DataTools("user123")
    result = data_tools.get_calendar_events()
    assert "error" in result
    assert "HTTP error" in result["error"]


def test_get_calendar_events_unexpected(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.data_tools import DataTools

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
                            "scopes": ["calendar", "email", "notes", "documents"],
                        }
                    ],
                    "total": 1,
                    "active_count": 1,
                    "error_count": 0,
                },
                200,
            )
        else:
            raise Exception("kaboom")

    mock_requests.side_effect = mock_get
    data_tools = DataTools("user123")
    result = data_tools.get_calendar_events()
    assert "error" in result
    assert "Unexpected error" in result["error"]


def test_get_emails_success(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.data_tools import DataTools

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
                            "scopes": ["calendar", "email", "notes", "documents"],
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
                        "emails": [{"id": "1", "subject": "Test"}],
                        "total_count": 1,
                        "providers_used": ["google"],
                        "provider_errors": None,
                    },
                },
                200,
            )

    mock_requests.side_effect = mock_get
    data_tools = DataTools("user123")
    result = data_tools.get_emails()
    assert "emails" in result
    assert result["emails"][0]["subject"] == "Test"


def test_get_emails_malformed(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.data_tools import DataTools

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
                            "scopes": ["calendar", "email", "notes", "documents"],
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
    result = DataTools("user123").get_emails()
    assert "error" in result
    assert "Malformed" in result["error"]


def test_get_emails_timeout(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.data_tools import DataTools

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
                            "scopes": ["calendar", "email", "notes", "documents"],
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
    result = DataTools("user123").get_emails()
    assert "error" in result
    assert "timed out" in result["error"]


def test_get_emails_http_error(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.data_tools import DataTools

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
                            "scopes": ["calendar", "email", "notes", "documents"],
                        }
                    ],
                    "total": 1,
                    "active_count": 1,
                    "error_count": 0,
                },
                200,
            )
        else:
            raise requests.HTTPError()

    mock_requests.side_effect = mock_get
    result = DataTools("user123").get_emails()
    assert "error" in result
    assert "HTTP error" in result["error"]


def test_get_emails_unexpected(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.data_tools import DataTools

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
                            "scopes": ["calendar", "email", "notes", "documents"],
                        }
                    ],
                    "total": 1,
                    "active_count": 1,
                    "error_count": 0,
                },
                200,
            )
        else:
            raise Exception("kaboom")

    mock_requests.side_effect = mock_get
    result = DataTools("user123").get_emails()
    assert "error" in result
    assert "Unexpected error" in result["error"]


def test_get_notes_success(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.data_tools import DataTools

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
                            "scopes": ["calendar", "email", "notes", "documents"],
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
                        "notes": [{"id": "1", "content": "Note"}],
                        "total_count": 1,
                        "providers_used": ["google"],
                        "provider_errors": None,
                    },
                },
                200,
            )

    mock_requests.side_effect = mock_get
    result = DataTools("user123").get_notes()
    assert "notes" in result
    assert result["notes"][0]["content"] == "Note"


def test_get_documents_success(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.data_tools import DataTools

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
                            "scopes": ["calendar", "email", "notes", "documents"],
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
                        "files": [{"id": "1", "title": "Doc"}],
                        "total_count": 1,
                        "providers_used": ["google"],
                        "provider_errors": None,
                    },
                },
                200,
            )

    mock_requests.side_effect = mock_get
    result = DataTools("user123").get_documents()
    assert "documents" in result
    assert result["documents"][0]["title"] == "Doc"


def test_create_draft_email(monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.draft_tools import DraftTools

    draft_tools = DraftTools("user123")
    result = draft_tools.create_draft_email(
        thread_id="thread123", to="test@example.com", subject="Test", body="Body"
    )
    assert result["success"] is True
    assert "draft" in result
    assert result["draft"]["to"] == "test@example.com"


def test_delete_draft_email(monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.draft_tools import DraftTools

    draft_tools = DraftTools("user123")
    draft_tools.create_draft_email(thread_id="thread123", to="test@example.com")
    result = draft_tools.delete_draft_email(thread_id="thread123")
    assert result["success"] is True
    assert "deleted" in result["message"]


def test_create_draft_calendar_event(monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.draft_tools import DraftTools

    draft_tools = DraftTools("user123")
    result = draft_tools.create_draft_calendar_event(
        thread_id="thread123",
        title="Meeting",
        start_time="2025-06-07T10:00:00Z",
        end_time="2025-06-07T11:00:00Z",
    )
    assert result["success"] is True
    assert "draft" in result
    assert result["draft"]["title"] == "Meeting"


def test_delete_draft_calendar_event(monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.draft_tools import DraftTools

    draft_tools = DraftTools("user123")
    draft_tools.create_draft_calendar_event(thread_id="thread123", title="Meeting")
    result = draft_tools.delete_draft_calendar_event(thread_id="thread123")
    assert result["success"] is True
    assert "deleted" in result["message"]


def test_create_draft_calendar_change(monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.draft_tools import DraftTools

    draft_tools = DraftTools("user123")
    result = draft_tools.create_draft_calendar_change(
        thread_id="thread123",
        event_id="event456",
        change_type="reschedule",
        new_start_time="2025-06-08T10:00:00Z",
        new_end_time="2025-06-08T11:00:00Z",
    )
    assert result["success"] is True
    assert "draft" in result
    assert result["draft"]["event_id"] == "event456"


def test_delete_draft_calendar_change(monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.draft_tools import DraftTools

    draft_tools = DraftTools("user123")
    draft_tools.create_draft_calendar_change(
        thread_id="thread123",
        event_id="event456",
        change_type="cancel",
        new_title="Updated Meeting",
    )
    result = draft_tools.delete_draft_calendar_edit(thread_id="thread123")
    assert result["success"] is True
    assert "deleted" in result["message"]


def test_draft_tools_thread_isolation(monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.draft_tools import DraftTools

    draft_tools = DraftTools("user123")
    draft_tools.create_draft_email(thread_id="thread1", to="user1@example.com")
    draft_tools.create_draft_email(thread_id="thread2", to="user2@example.com")
    draft_tools.create_draft_calendar_event(thread_id="thread1", title="Meeting 1")
    draft_tools.create_draft_calendar_event(thread_id="thread2", title="Meeting 2")
    
    # Get draft data to verify
    thread1_data = draft_tools.get_draft_data("thread1")
    thread2_data = draft_tools.get_draft_data("thread2")
    
    # Check that drafts were created
    assert len(thread1_data) > 0
    assert len(thread2_data) > 0
    
    # Verify email drafts
    email_drafts = [d for d in thread1_data if d.get("type") == "email"]
    assert len(email_drafts) > 0
    assert email_drafts[0]["to"] == "user1@example.com"
    
    email_drafts2 = [d for d in thread2_data if d.get("type") == "email"]
    assert len(email_drafts2) > 0
    assert email_drafts2[0]["to"] == "user2@example.com"
    
    # Verify calendar event drafts
    calendar_drafts = [d for d in thread1_data if d.get("type") == "calendar_event"]
    assert len(calendar_drafts) > 0
    assert calendar_drafts[0]["title"] == "Meeting 1"
    
    calendar_drafts2 = [d for d in thread2_data if d.get("type") == "calendar_event"]
    assert len(calendar_drafts2) > 0
    assert calendar_drafts2[0]["title"] == "Meeting 2"


def test_tool_registry(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.get_tools import GetTools

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
                            "scopes": ["calendar", "email", "notes", "documents"],
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
                        "events": [
                            {
                                "id": "1",
                                "title": "Meeting",
                                "start_time": "2025-06-20T10:00:00Z",
                                "end_time": "2025-06-20T11:00:00Z",
                            }
                        ],
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
    registry = GetTools().get_tool.registry
    calendar_result = registry.execute_tool("get_calendar_events", user_id="user123")
    assert "events" in calendar_result.raw_output
    email_result = registry.execute_tool("get_emails", user_id="user123")
    assert "emails" in email_result.raw_output


def test_tool_registry_tooloutput_success(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.get_tools import GetTools

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
                            "scopes": ["calendar", "email", "notes", "documents"],
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
                        "events": [
                            {
                                "id": "1",
                                "title": "Meeting",
                                "start_time": "2025-06-20T10:00:00Z",
                                "end_time": "2025-06-20T11:00:00Z",
                            }
                        ],
                        "total_count": 1,
                        "providers_used": ["google"],
                        "provider_errors": None,
                    },
                },
                200,
            )
        else:
            return MockResponse(
                {
                    "success": True,
                    "data": {"emails": [{"id": "1", "subject": "Test Email"}]},
                },
                200,
            )

    mock_requests.side_effect = mock_get
    registry = GetTools().get_tool.registry
    calendar_result = registry.execute_tool("get_calendar_events", user_id="user123")
    assert hasattr(calendar_result, "raw_output")
    assert "events" in calendar_result.raw_output


def test_tool_registry_tooloutput_error(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.get_tools import GetTools

    registry = GetTools().get_tool.registry
    error_result = registry.execute_tool("calendar")
    assert hasattr(error_result, "raw_output")
    assert "error" in error_result.raw_output


def test_tool_registry_tooloutput_for_get_tools(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.get_tools import GetTools

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
                            "scopes": ["calendar", "email", "notes", "documents"],
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
                        "events": [
                            {
                                "id": "1",
                                "title": "Meeting",
                                "start_time": "2025-06-20T10:00:00Z",
                                "end_time": "2025-06-20T11:00:00Z",
                            }
                        ],
                        "total_count": 1,
                        "providers_used": ["google"],
                        "provider_errors": None,
                    },
                },
                200,
            )
        else:
            return MockResponse(
                {
                    "success": True,
                    "data": {"emails": [{"id": "1", "subject": "Test Email"}]},
                },
                200,
            )

    mock_requests.side_effect = mock_get
    registry = GetTools().get_tool.registry
    calendar_result = registry.execute_tool("get_calendar_events", user_id="user123")
    assert "events" in calendar_result.raw_output
    email_result = registry.execute_tool("get_emails", user_id="user123")
    assert "emails" in email_result.raw_output


def test_tool_registry_execute_tool_returns_tooloutput(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.get_tools import GetTools

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
                            "scopes": ["calendar", "email", "notes", "documents"],
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
                        "events": [
                            {
                                "id": "1",
                                "title": "Meeting",
                                "start_time": "2025-06-20T10:00:00Z",
                                "end_time": "2025-06-20T11:00:00Z",
                            }
                        ],
                        "total_count": 1,
                        "providers_used": ["google"],
                        "provider_errors": None,
                    },
                },
                200,
            )
        else:
            return MockResponse(
                {
                    "success": True,
                    "data": {"emails": [{"id": "1", "subject": "Test Email"}]},
                },
                200,
            )

    mock_requests.side_effect = mock_get
    registry = GetTools().get_tool.registry
    email_result = registry.execute_tool("get_emails", user_id="user123")
    assert hasattr(email_result, "raw_output")
    assert "emails" in email_result.raw_output
    calendar_result = registry.execute_tool("get_calendar_events", user_id="user123")
    assert hasattr(calendar_result, "raw_output")
    assert "events" in calendar_result.raw_output


def test_tool_registry_execute_tool_error(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.get_tools import GetTools

    registry = GetTools().get_tool.registry
    result = registry.execute_tool("calendar")
    assert hasattr(result, "raw_output")
    assert "error" in result.raw_output


def test_get_tool_registry_singleton(mock_requests, monkeypatch):
    # setup_chat_settings_env(monkeypatch) # Removed
    from services.chat.tools.get_tools import GetTools

    registry1 = GetTools().get_tool.registry
    registry2 = GetTools().get_tool.registry
    assert registry1 is registry2
