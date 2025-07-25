from unittest.mock import patch

import pytest
import requests

from services.chat.settings import get_settings


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError()


def setup_chat_settings_env(monkeypatch):
    monkeypatch.setenv("DB_URL_CHAT", "sqlite:///test.db")
    monkeypatch.setenv("API_CHAT_USER_KEY", "test-api-key")
    monkeypatch.setenv("API_CHAT_OFFICE_KEY", "test-api-key")
    monkeypatch.setenv("API_FRONTEND_CHAT_KEY", "test-FRONTEND_CHAT_KEY")
    monkeypatch.setenv("USER_MANAGEMENT_SERVICE_URL", "http://test-user-server")
    monkeypatch.setenv("OFFICE_SERVICE_URL", "http://test-office-server")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("LLM_MODEL", "fake-model")
    monkeypatch.setenv("MAX_TOKENS", "2000")
    monkeypatch.setenv("SERVICE_NAME", "chat-service")
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "8000")
    monkeypatch.setenv("DEBUG", "False")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings()._settings = None


@pytest.fixture(autouse=True)
def clear_drafts(monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import _draft_storage

    _draft_storage.clear()


@pytest.fixture(autouse=True)
def mock_requests():
    """Mock requests module for all tests to work in parallel execution."""
    with patch("services.chat.agents.llm_tools.requests.get") as mock_get:
        yield mock_get


def test_get_calendar_events_success(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_calendar_events

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


def test_get_calendar_events_malformed(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_calendar_events

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


def test_get_calendar_events_timeout(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_calendar_events

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


def test_get_calendar_events_http_error(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_calendar_events

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
            raise requests.HTTPError()

    mock_requests.side_effect = mock_get
    result = get_calendar_events("user123")
    assert "error" in result
    assert "HTTP error" in result["error"]


def test_get_calendar_events_unexpected(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_calendar_events

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
            raise Exception("kaboom")

    mock_requests.side_effect = mock_get
    result = get_calendar_events("user123")
    assert "error" in result
    assert "Unexpected error" in result["error"]


def test_get_emails_success(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_emails

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
                        "emails": [{"id": "1", "subject": "Test"}],
                        "total_count": 1,
                        "providers_used": ["google"],
                        "provider_errors": None,
                    },
                },
                200,
            )

    mock_requests.side_effect = mock_get
    result = get_emails("user123")
    assert "emails" in result
    assert result["emails"][0]["subject"] == "Test"


def test_get_emails_malformed(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_emails

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
    result = get_emails("user123")
    assert "error" in result
    assert "Malformed" in result["error"]


def test_get_emails_timeout(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_emails

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
    result = get_emails("user123")
    assert "error" in result
    assert "timed out" in result["error"]


def test_get_emails_http_error(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_emails

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
            raise requests.HTTPError()

    mock_requests.side_effect = mock_get
    result = get_emails("user123")
    assert "error" in result
    assert "HTTP error" in result["error"]


def test_get_emails_unexpected(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_emails

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
            raise Exception("kaboom")

    mock_requests.side_effect = mock_get
    result = get_emails("user123")
    assert "error" in result
    assert "Unexpected error" in result["error"]


def test_get_notes_success(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_notes

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
                        "notes": [{"id": "1", "content": "Note"}],
                        "total_count": 1,
                        "providers_used": ["google"],
                        "provider_errors": None,
                    },
                },
                200,
            )

    mock_requests.side_effect = mock_get
    result = get_notes("user123")
    assert "notes" in result
    assert result["notes"][0]["content"] == "Note"


def test_get_documents_success(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_documents

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
                        "documents": [{"id": "1", "title": "Doc"}],
                        "total_count": 1,
                        "providers_used": ["google"],
                        "provider_errors": None,
                    },
                },
                200,
            )

    mock_requests.side_effect = mock_get
    result = get_documents("user123")
    assert "documents" in result
    assert result["documents"][0]["title"] == "Doc"


def test_create_draft_email(monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import create_draft_email

    result = create_draft_email(
        thread_id="thread123", to="test@example.com", subject="Test", body="Body"
    )
    assert result["success"] is True
    assert "draft" in result
    assert result["draft"]["to"] == "test@example.com"


def test_delete_draft_email(monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import create_draft_email, delete_draft_email

    create_draft_email(thread_id="thread123", to="test@example.com")
    result = delete_draft_email(thread_id="thread123")
    assert result["success"] is True
    assert "deleted" in result["message"]


def test_create_draft_calendar_event(monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import create_draft_calendar_event

    result = create_draft_calendar_event(
        thread_id="thread123",
        title="Meeting",
        start_time="2025-06-07T10:00:00Z",
        end_time="2025-06-07T11:00:00Z",
    )
    assert result["success"] is True
    assert "draft" in result
    assert result["draft"]["title"] == "Meeting"


def test_delete_draft_calendar_event(monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import (
        create_draft_calendar_event,
        delete_draft_calendar_event,
    )

    create_draft_calendar_event(thread_id="thread123", title="Meeting")
    result = delete_draft_calendar_event(thread_id="thread123")
    assert result["success"] is True
    assert "deleted" in result["message"]


def test_create_draft_calendar_change(monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import create_draft_calendar_change

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


def test_delete_draft_calendar_change(monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import (
        create_draft_calendar_change,
        delete_draft_calendar_edit,
    )

    create_draft_calendar_change(
        thread_id="thread123",
        event_id="event456",
        change_type="cancel",
        new_title="Updated Meeting",
    )
    result = delete_draft_calendar_edit(thread_id="thread123")
    assert result["success"] is True
    assert "deleted" in result["message"]


def test_draft_tools_thread_isolation(monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import (
        _draft_storage,
        create_draft_calendar_event,
        create_draft_email,
    )

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


def test_tool_registry(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_tool_registry

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


def test_tool_registry_tooloutput_success(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_tool_registry

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
            return MockResponse(
                {
                    "success": True,
                    "data": {"emails": [{"id": "1", "subject": "Test Email"}]},
                },
                200,
            )

    mock_requests.side_effect = mock_get
    registry = get_tool_registry()
    calendar_result = registry.execute_tool("get_calendar_events", user_id="user123")
    assert hasattr(calendar_result, "raw_output")
    assert "events" in calendar_result.raw_output


def test_tool_registry_tooloutput_error(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_tool_registry

    registry = get_tool_registry()
    error_result = registry.execute_tool("calendar")
    assert hasattr(error_result, "raw_output")
    assert "error" in error_result.raw_output


def test_tool_registry_tooloutput_for_get_tools(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_tool_registry

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
            return MockResponse(
                {
                    "success": True,
                    "data": {"emails": [{"id": "1", "subject": "Test Email"}]},
                },
                200,
            )

    mock_requests.side_effect = mock_get
    registry = get_tool_registry()
    calendar_result = registry.execute_tool("get_calendar_events", user_id="user123")
    assert "events" in calendar_result.raw_output
    email_result = registry.execute_tool("get_emails", user_id="user123")
    assert "emails" in email_result.raw_output


def test_tool_registry_execute_tool_returns_tooloutput(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_tool_registry

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
            return MockResponse(
                {
                    "success": True,
                    "data": {"emails": [{"id": "1", "subject": "Test Email"}]},
                },
                200,
            )

    mock_requests.side_effect = mock_get
    registry = get_tool_registry()
    email_result = registry.execute_tool("get_emails", user_id="user123")
    assert hasattr(email_result, "raw_output")
    assert "emails" in email_result.raw_output
    calendar_result = registry.execute_tool("get_calendar_events", user_id="user123")
    assert hasattr(calendar_result, "raw_output")
    assert "events" in calendar_result.raw_output


def test_tool_registry_execute_tool_error(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_tool_registry

    registry = get_tool_registry()
    result = registry.execute_tool("calendar")
    assert hasattr(result, "raw_output")
    assert "error" in result.raw_output


def test_get_tool_registry_singleton(mock_requests, monkeypatch):
    setup_chat_settings_env(monkeypatch)
    from services.chat.agents.llm_tools import get_tool_registry

    registry1 = get_tool_registry()
    registry2 = get_tool_registry()
    assert registry1 is registry2
