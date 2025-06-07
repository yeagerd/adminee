import requests

from services.chat_service.llm_tools import (
    CalendarTool, EmailTool, NotesTool, DocumentsTool,
    CreateDraftEmailTool, DeleteDraftEmailTool,
    CreateDraftCalendarEventTool, DeleteDraftCalendarEventTool,
    CreateDraftCalendarChangeTool, DeleteDraftCalendarChangeTool,
    _draft_storage
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
        return MockResponse({"emails": [{"id": "1", "subject": "Test Email", "from": "test@example.com"}]}, 200)

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
        return MockResponse({"notes": [{"id": "1", "title": "Test Note", "content": "Note content"}]}, 200)

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
        return MockResponse({"documents": [{"id": "1", "title": "Test Document", "type": "word"}]}, 200)

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
