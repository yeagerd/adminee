import requests

from services.chat_service.llm_tools import (
    CalendarTool,
    CreateDraftCalendarChangeTool,
    CreateDraftCalendarEventTool,
    CreateDraftEmailTool,
    DeleteDraftCalendarChangeTool,
    DeleteDraftCalendarEventTool,
    DeleteDraftEmailTool,
    DocumentsTool,
    EmailTool,
    NotesTool,
    ToolRegistry,
    _draft_storage,
    get_tool_registry,
)


class MockResponse:
    def __init__(self, json_data, status_code):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_calendar_tool_success(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse({"events": [{"id": "1", "title": "Meeting"}]}, 200)

    monkeypatch.setattr(requests, "get", mock_get)
    tool = CalendarTool("http://office-service")
    result = tool(
        "token123",
        start_date="2025-06-05",
        end_date="2025-06-06",
        user_timezone="UTC",
        provider_type="google",
    )
    assert "events" in result
    assert result["events"][0]["title"] == "Meeting"


def test_calendar_tool_malformed_response(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse({"bad": "data"}, 200)

    monkeypatch.setattr(requests, "get", mock_get)
    tool = CalendarTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "Malformed" in result["error"]


def test_calendar_tool_timeout(monkeypatch):
    def mock_get(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "get", mock_get)
    tool = CalendarTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "timed out" in result["error"]


def test_calendar_tool_http_error(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse({}, 500)

    monkeypatch.setattr(requests, "get", mock_get)
    tool = CalendarTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "HTTP error" in result["error"]


def test_calendar_tool_unexpected_error(monkeypatch):
    def mock_get(*args, **kwargs):
        raise Exception("boom")

    monkeypatch.setattr(requests, "get", mock_get)
    tool = CalendarTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "Unexpected error" in result["error"]


# EmailTool tests
def test_email_tool_success(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse(
            {
                "emails": [
                    {"id": "1", "subject": "Test Email", "from": "test@example.com"}
                ]
            },
            200,
        )

    monkeypatch.setattr(requests, "get", mock_get)
    tool = EmailTool("http://office-service")
    result = tool(
        "token123",
        start_date="2025-06-05",
        end_date="2025-06-06",
        unread_only=True,
        folder="inbox",
        max_results=10,
    )
    assert "emails" in result
    assert result["emails"][0]["subject"] == "Test Email"


def test_email_tool_malformed_response(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse({"bad": "data"}, 200)

    monkeypatch.setattr(requests, "get", mock_get)
    tool = EmailTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "Malformed" in result["error"]


def test_email_tool_timeout(monkeypatch):
    def mock_get(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "get", mock_get)
    tool = EmailTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "timed out" in result["error"]


def test_email_tool_http_error(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse({}, 404)

    monkeypatch.setattr(requests, "get", mock_get)
    tool = EmailTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "HTTP error" in result["error"]


def test_email_tool_unexpected_error(monkeypatch):
    def mock_get(*args, **kwargs):
        raise Exception("boom")

    monkeypatch.setattr(requests, "get", mock_get)
    tool = EmailTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "Unexpected error" in result["error"]


def test_email_tool_with_filters(monkeypatch):
    def mock_get(*args, **kwargs):
        # Verify that parameters are passed correctly
        params = kwargs.get("params", {})
        assert params.get("unread_only") == "true"
        assert params.get("folder") == "sent"
        return MockResponse({"emails": []}, 200)

    monkeypatch.setattr(requests, "get", mock_get)
    tool = EmailTool("http://office-service")
    result = tool("token123", unread_only=True, folder="sent")
    assert "emails" in result


# NotesTool tests
def test_notes_tool_success(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse(
            {"notes": [{"id": "1", "title": "Test Note", "content": "Note content"}]},
            200,
        )

    monkeypatch.setattr(requests, "get", mock_get)
    tool = NotesTool("http://office-service")
    result = tool(
        "token123",
        notebook="work",
        tags="important,meeting",
        search_query="project",
        max_results=5,
    )
    assert "notes" in result
    assert result["notes"][0]["title"] == "Test Note"


def test_notes_tool_malformed_response(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse({"bad": "data"}, 200)

    monkeypatch.setattr(requests, "get", mock_get)
    tool = NotesTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "Malformed" in result["error"]


def test_notes_tool_timeout(monkeypatch):
    def mock_get(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "get", mock_get)
    tool = NotesTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "timed out" in result["error"]


def test_notes_tool_http_error(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse({}, 403)

    monkeypatch.setattr(requests, "get", mock_get)
    tool = NotesTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "HTTP error" in result["error"]


def test_notes_tool_unexpected_error(monkeypatch):
    def mock_get(*args, **kwargs):
        raise Exception("boom")

    monkeypatch.setattr(requests, "get", mock_get)
    tool = NotesTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "Unexpected error" in result["error"]


def test_notes_tool_with_filters(monkeypatch):
    def mock_get(*args, **kwargs):
        # Verify that parameters are passed correctly
        params = kwargs.get("params", {})
        assert params.get("notebook") == "personal"
        assert params.get("tags") == "todo"
        assert params.get("search_query") == "meeting"
        return MockResponse({"notes": []}, 200)

    monkeypatch.setattr(requests, "get", mock_get)
    tool = NotesTool("http://office-service")
    result = tool("token123", notebook="personal", tags="todo", search_query="meeting")
    assert "notes" in result


# DocumentsTool tests
def test_documents_tool_success(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse(
            {"documents": [{"id": "1", "title": "Test Document", "type": "word"}]}, 200
        )

    monkeypatch.setattr(requests, "get", mock_get)
    tool = DocumentsTool("http://office-service")
    result = tool(
        "token123",
        document_type="word",
        start_date="2025-06-01",
        end_date="2025-06-07",
        search_query="project",
        max_results=10,
    )
    assert "documents" in result
    assert result["documents"][0]["title"] == "Test Document"


def test_documents_tool_malformed_response(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse({"bad": "data"}, 200)

    monkeypatch.setattr(requests, "get", mock_get)
    tool = DocumentsTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "Malformed" in result["error"]


def test_documents_tool_timeout(monkeypatch):
    def mock_get(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "get", mock_get)
    tool = DocumentsTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "timed out" in result["error"]


def test_documents_tool_http_error(monkeypatch):
    def mock_get(*args, **kwargs):
        return MockResponse({}, 500)

    monkeypatch.setattr(requests, "get", mock_get)
    tool = DocumentsTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "HTTP error" in result["error"]


def test_documents_tool_unexpected_error(monkeypatch):
    def mock_get(*args, **kwargs):
        raise Exception("boom")

    monkeypatch.setattr(requests, "get", mock_get)
    tool = DocumentsTool("http://office-service")
    result = tool("token123")
    assert "error" in result
    assert "Unexpected error" in result["error"]


def test_documents_tool_with_filters(monkeypatch):
    def mock_get(*args, **kwargs):
        # Verify that parameters are passed correctly
        params = kwargs.get("params", {})
        assert params.get("document_type") == "excel"
        assert params.get("search_query") == "budget"
        return MockResponse({"documents": []}, 200)

    monkeypatch.setattr(requests, "get", mock_get)
    tool = DocumentsTool("http://office-service")
    result = tool("token123", document_type="excel", search_query="budget")
    assert "documents" in result


# Draft tools tests
def test_create_draft_email_tool():
    # Clear storage before test
    _draft_storage.clear()

    tool = CreateDraftEmailTool()
    result = tool(
        thread_id="thread123",
        to="test@example.com",
        subject="Test Subject",
        body="Test body content",
    )

    assert result["success"] is True
    assert "draft" in result
    assert result["draft"]["to"] == "test@example.com"
    assert result["draft"]["subject"] == "Test Subject"
    assert result["draft"]["body"] == "Test body content"
    assert result["draft"]["type"] == "email"


def test_create_draft_email_tool_update_existing():
    # Clear storage and create initial draft
    _draft_storage.clear()

    tool = CreateDraftEmailTool()
    # Create initial draft
    tool(thread_id="thread123", to="initial@example.com", subject="Initial Subject")

    # Update the draft
    result = tool(thread_id="thread123", subject="Updated Subject", body="New body")

    assert result["success"] is True
    assert result["draft"]["to"] == "initial@example.com"  # Should keep existing
    assert result["draft"]["subject"] == "Updated Subject"  # Should update
    assert result["draft"]["body"] == "New body"  # Should add new


def test_delete_draft_email_tool():
    # Clear storage and create a draft
    _draft_storage.clear()
    create_tool = CreateDraftEmailTool()
    create_tool(thread_id="thread123", to="test@example.com")

    delete_tool = DeleteDraftEmailTool()
    result = delete_tool("thread123")

    assert result["success"] is True
    assert "deleted" in result["message"]


def test_delete_draft_email_tool_not_found():
    # Clear storage
    _draft_storage.clear()

    delete_tool = DeleteDraftEmailTool()
    result = delete_tool("nonexistent")

    assert result["success"] is False
    assert "No draft email found" in result["message"]


def test_create_draft_calendar_event_tool():
    # Clear storage before test
    _draft_storage.clear()

    tool = CreateDraftCalendarEventTool()
    result = tool(
        thread_id="thread123",
        title="Team Meeting",
        start_time="2025-06-07T10:00:00Z",
        end_time="2025-06-07T11:00:00Z",
        attendees="team@example.com",
        location="Conference Room A",
    )

    assert result["success"] is True
    assert "draft" in result
    assert result["draft"]["title"] == "Team Meeting"
    assert result["draft"]["start_time"] == "2025-06-07T10:00:00Z"
    assert result["draft"]["type"] == "calendar_event"


def test_delete_draft_calendar_event_tool():
    # Clear storage and create a draft
    _draft_storage.clear()
    create_tool = CreateDraftCalendarEventTool()
    create_tool(thread_id="thread123", title="Test Event")

    delete_tool = DeleteDraftCalendarEventTool()
    result = delete_tool("thread123")

    assert result["success"] is True
    assert "deleted" in result["message"]


def test_create_draft_calendar_change_tool():
    # Clear storage before test
    _draft_storage.clear()

    tool = CreateDraftCalendarChangeTool()
    result = tool(
        thread_id="thread123",
        event_id="event456",
        change_type="reschedule",
        new_start_time="2025-06-08T10:00:00Z",
        new_end_time="2025-06-08T11:00:00Z",
    )

    assert result["success"] is True
    assert "draft" in result
    assert result["draft"]["event_id"] == "event456"
    assert result["draft"]["change_type"] == "reschedule"
    assert result["draft"]["type"] == "calendar_change"


def test_delete_draft_calendar_change_tool():
    # Clear storage and create a draft
    _draft_storage.clear()
    create_tool = CreateDraftCalendarChangeTool()
    create_tool(thread_id="thread123", event_id="event456", change_type="cancel")

    delete_tool = DeleteDraftCalendarChangeTool()
    result = delete_tool("thread123")

    assert result["success"] is True
    assert "deleted" in result["message"]


def test_draft_tools_thread_isolation():
    # Clear storage
    _draft_storage.clear()

    # Create drafts for different threads
    email_tool = CreateDraftEmailTool()
    calendar_tool = CreateDraftCalendarEventTool()

    email_tool(thread_id="thread1", to="user1@example.com")
    email_tool(thread_id="thread2", to="user2@example.com")
    calendar_tool(thread_id="thread1", title="Meeting 1")
    calendar_tool(thread_id="thread2", title="Meeting 2")

    # Verify each thread has its own drafts
    assert "thread1_email" in _draft_storage
    assert "thread2_email" in _draft_storage
    assert "thread1_calendar_event" in _draft_storage
    assert "thread2_calendar_event" in _draft_storage

    # Verify content is isolated
    assert _draft_storage["thread1_email"]["to"] == "user1@example.com"
    assert _draft_storage["thread2_email"]["to"] == "user2@example.com"
    assert _draft_storage["thread1_calendar_event"]["title"] == "Meeting 1"
    assert _draft_storage["thread2_calendar_event"]["title"] == "Meeting 2"


# Tool registry and integration tests
def test_tool_registry_initialization():
    registry = ToolRegistry("http://test-office-service")

    # Verify all tools are registered
    tools = registry.list_tools()
    expected_tools = [
        "calendar",
        "email",
        "notes",
        "documents",
        "create_draft_email",
        "delete_draft_email",
        "create_draft_calendar_event",
        "delete_draft_calendar_event",
        "create_draft_calendar_change",
        "delete_draft_calendar_change",
    ]

    for tool_name in expected_tools:
        assert tool_name in tools


def test_tool_registry_get_tool():
    registry = ToolRegistry("http://test-office-service")

    # Test getting existing tools
    calendar_tool = registry.get_tool("calendar")
    assert isinstance(calendar_tool, CalendarTool)

    email_tool = registry.get_tool("email")
    assert isinstance(email_tool, EmailTool)

    # Test getting non-existent tool
    non_existent = registry.get_tool("non_existent")
    assert non_existent is None


def test_tool_registry_schemas():
    registry = ToolRegistry("http://test-office-service")
    schemas = registry.get_tool_schemas()

    # Verify all tools have schemas
    expected_tools = [
        "calendar",
        "email",
        "notes",
        "documents",
        "create_draft_email",
        "delete_draft_email",
        "create_draft_calendar_event",
        "delete_draft_calendar_event",
        "create_draft_calendar_change",
        "delete_draft_calendar_change",
    ]

    for tool_name in expected_tools:
        assert tool_name in schemas
        assert "type" in schemas[tool_name]
        assert "function" in schemas[tool_name]
        assert "name" in schemas[tool_name]["function"]
        assert "description" in schemas[tool_name]["function"]
        assert "parameters" in schemas[tool_name]["function"]


def test_tool_registry_execute_tool(monkeypatch):
    # Mock requests for data retrieval tools
    def mock_get(*args, **kwargs):
        return MockResponse({"events": [{"id": "1", "title": "Test Event"}]}, 200)

    monkeypatch.setattr(requests, "get", mock_get)

    registry = ToolRegistry("http://test-office-service")

    # Test executing calendar tool
    result = registry.execute_tool("calendar", user_token="test_token")
    assert "events" in result

    # Test executing draft tool
    _draft_storage.clear()
    result = registry.execute_tool(
        "create_draft_email", thread_id="test_thread", to="test@example.com"
    )
    assert result["success"] is True

    # Test executing non-existent tool
    result = registry.execute_tool("non_existent", param="value")
    assert "error" in result
    assert "not found" in result["error"]


def test_tool_registry_execute_tool_error():
    registry = ToolRegistry("http://test-office-service")

    # Test tool execution with missing required parameters
    result = registry.execute_tool("calendar")  # Missing user_token
    assert "error" in result


def test_get_tool_registry_singleton():
    # Test that get_tool_registry returns the same instance
    registry1 = get_tool_registry("http://test1")
    registry2 = get_tool_registry(
        "http://test2"
    )  # URL should be ignored for existing instance

    assert registry1 is registry2


def test_tool_integration_end_to_end(monkeypatch):
    """Integration test simulating LiteLLM usage."""

    # Mock office service responses
    def mock_get(*args, **kwargs):
        url = args[0]
        if "events" in url:
            return MockResponse({"events": [{"id": "1", "title": "Meeting"}]}, 200)
        elif "emails" in url:
            return MockResponse({"emails": [{"id": "1", "subject": "Email"}]}, 200)
        elif "notes" in url:
            return MockResponse({"notes": [{"id": "1", "title": "Note"}]}, 200)
        elif "documents" in url:
            return MockResponse({"documents": [{"id": "1", "title": "Doc"}]}, 200)
        return MockResponse({}, 404)

    monkeypatch.setattr(requests, "get", mock_get)
    _draft_storage.clear()

    registry = ToolRegistry("http://test-office-service")

    # Simulate a conversation flow
    thread_id = "conversation_123"
    user_token = "user_token_456"

    # 1. Get calendar events
    calendar_result = registry.execute_tool("calendar", user_token=user_token)
    assert "events" in calendar_result
    assert calendar_result["events"][0]["title"] == "Meeting"

    # 2. Get emails
    email_result = registry.execute_tool(
        "email", user_token=user_token, unread_only=True
    )
    assert "emails" in email_result
    assert email_result["emails"][0]["subject"] == "Email"

    # 3. Create a draft email
    draft_result = registry.execute_tool(
        "create_draft_email",
        thread_id=thread_id,
        to="colleague@example.com",
        subject="Follow-up on meeting",
        body="Let's schedule a follow-up meeting.",
    )
    assert draft_result["success"] is True
    assert draft_result["draft"]["to"] == "colleague@example.com"

    # 4. Create a draft calendar event
    event_result = registry.execute_tool(
        "create_draft_calendar_event",
        thread_id=thread_id,
        title="Follow-up Meeting",
        start_time="2025-06-08T10:00:00Z",
        end_time="2025-06-08T11:00:00Z",
    )
    assert event_result["success"] is True
    assert event_result["draft"]["title"] == "Follow-up Meeting"

    # 5. Verify drafts are stored separately
    assert f"{thread_id}_email" in _draft_storage
    assert f"{thread_id}_calendar_event" in _draft_storage

    # 6. Delete drafts
    delete_email_result = registry.execute_tool(
        "delete_draft_email", thread_id=thread_id
    )
    assert delete_email_result["success"] is True

    delete_event_result = registry.execute_tool(
        "delete_draft_calendar_event", thread_id=thread_id
    )
    assert delete_event_result["success"] is True

    # 7. Verify drafts are deleted
    assert f"{thread_id}_email" not in _draft_storage
    assert f"{thread_id}_calendar_event" not in _draft_storage
