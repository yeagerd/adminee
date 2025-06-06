import pytest
from ..llm_tools import CalendarTool
import requests

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
    result = tool("token123", start_date="2025-06-05", end_date="2025-06-06", user_timezone="UTC", provider_type="google")
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
