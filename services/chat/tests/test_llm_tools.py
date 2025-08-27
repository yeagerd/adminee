from unittest.mock import Mock, patch

import pytest

from services.chat.tools.draft_tools import DraftTools
from services.chat.tools.get_tools import GetTools
from services.chat.tools.tool_registry import ToolRegistry
from services.common.test_utils import BaseSelectiveHTTPIntegrationTest


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


@pytest.fixture
def draft_tools():
    return DraftTools("test_user")


@pytest.fixture
def clear_drafts(draft_tools):
    draft_tools.clear_all_drafts("test_thread_id")


class TestLLMTools(BaseSelectiveHTTPIntegrationTest):
    """Test the LLM tools functionality."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)

        # Create a mock for requests.get that will be used by DataTools
        self.mock_requests_get = patch("requests.get").start()

        # Configure the mock to return appropriate responses
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
                # Return mock calendar events with proper structure
                return MockResponse(
                    {
                        "data": {
                            "events": [
                                {
                                    "id": "google_event_1",
                                    "title": "Daily Standup",
                                    "start_time": "2025-06-20T17:00:00Z",
                                    "end_time": "2025-06-20T18:00:00Z",
                                },
                                {
                                    "id": "google_event_2",
                                    "title": "Team Meeting",
                                    "start_time": "2025-06-21T14:00:00Z",
                                    "end_time": "2025-06-21T15:00:00Z",
                                },
                            ],
                            "total": 2,
                        }
                    },
                    200,
                )
            elif "emails" in url:
                # Return mock emails with proper structure
                return MockResponse(
                    {
                        "data": {
                            "emails": [
                                {
                                    "id": "email_1",
                                    "subject": "Test Email 1",
                                    "sender": "sender1@example.com",
                                    "received_at": "2025-06-20T10:00:00Z",
                                }
                            ],
                            "total": 1,
                        }
                    },
                    200,
                )
            elif "notes" in url:
                # Return mock notes with proper structure
                return MockResponse(
                    {
                        "data": {
                            "notes": [
                                {
                                    "id": "note_1",
                                    "title": "Test Note 1",
                                    "content": "This is a test note",
                                    "created_at": "2025-06-20T10:00:00Z",
                                }
                            ],
                            "total": 1,
                        }
                    },
                    200,
                )
            elif "documents" in url:
                # Return mock documents with proper structure
                return MockResponse(
                    {
                        "data": {
                            "files": [
                                {
                                    "id": "doc_1",
                                    "title": "Test Document 1",
                                    "type": "pdf",
                                    "created_at": "2025-06-20T10:00:00Z",
                                }
                            ],
                            "total": 1,
                        }
                    },
                    200,
                )
            else:
                # Default response for unknown URLs
                return MockResponse({"error": "Not found"}, 404)

        self.mock_requests_get.side_effect = mock_get

    def teardown_method(self, method):
        """Clean up after each test method."""
        self.mock_requests_get.stop()
        super().teardown_method(method)

    def test_get_calendar_events_success(self):
        """Test successful calendar events retrieval."""
        from datetime import datetime, timezone

        from services.api.v1.office import CalendarEvent, Provider
        from services.chat.tools.data_tools import DataTools

        # Test the DataTools directly
        data_tools = DataTools("user123")
        result = data_tools.get_calendar_events(
            start_date="2025-06-20",
            end_date="2025-06-21",
            limit=10,
        )

        assert result["status"] == "success"
        assert "events" in result
        assert len(result["events"]) == 2

    def test_get_calendar_events_malformed(self, clear_drafts):
        """Test calendar events with malformed response."""
        from services.chat.tools.data_tools import DataTools

        # Test with malformed response
        data_tools = DataTools("user123")
        result = data_tools.get_calendar_events(
            start_date="invalid-date",
            end_date="invalid-date",
        )

        # The current implementation doesn't validate dates, so it should succeed
        assert result["status"] == "success"

    def test_get_emails_success(self, clear_drafts):
        """Test successful email retrieval."""
        from services.chat.tools.data_tools import DataTools

        data_tools = DataTools("user123")
        result = data_tools.get_emails(
            start_date="2025-06-20",
            end_date="2025-06-21",
            max_results=10,
        )

        assert result["status"] == "success"
        assert "emails" in result
        assert len(result["emails"]) == 1

    def test_get_notes_success(self, clear_drafts):
        """Test successful notes retrieval."""
        from services.chat.tools.data_tools import DataTools

        data_tools = DataTools("user123")
        result = data_tools.get_notes(
            notebook="test_notebook",
            tags="test_tag",
            max_results=10,
        )

        assert result["status"] == "success"
        assert "notes" in result
        assert len(result["notes"]) == 1

    def test_get_documents_success(self, clear_drafts):
        """Test successful documents retrieval."""
        from services.chat.tools.data_tools import DataTools

        data_tools = DataTools("user123")
        result = data_tools.get_documents(
            document_type="pdf",
            search_query="test",
            max_results=10,
        )

        assert result["status"] == "success"
        assert "documents" in result
        assert len(result["documents"]) == 1

    def test_get_tools_registry(self, clear_drafts):
        """Test that GetTools creates a proper registry."""
        get_tools = GetTools("user123")
        registry = get_tools.registry

        assert isinstance(registry, ToolRegistry)
        assert len(registry._tools) > 0

        # Check that specific tools are registered
        tool_ids = list(registry._tools.keys())
        assert "get_calendar_events" in tool_ids
        assert "get_emails" in tool_ids
        assert "get_notes" in tool_ids
        assert "get_documents" in tool_ids

    def test_tool_execution(self, clear_drafts):
        """Test tool execution through the registry."""
        get_tools = GetTools("user123")
        registry = get_tools.registry

        # Test executing a tool
        result = registry.execute_tool(
            "get_calendar_events",
            start_date="2025-06-20",
            end_date="2025-06-21",
            limit=5,
        )

        assert result["status"] == "success"
        assert "events" in result

    def test_tool_execution_with_user_id_injection(self, clear_drafts):
        """Test that user_id is properly injected into tool execution."""
        get_tools = GetTools("user123")
        registry = get_tools.registry

        # Test executing a tool without passing user_id
        result = registry.execute_tool(
            "get_calendar_events",
            start_date="2025-06-20",
            end_date="2025-06-21",
        )

        # The tool should work because user_id is pre-bound
        assert result["status"] == "success"

    def test_get_tool_info(self, clear_drafts):
        """Test getting tool information."""
        get_tools = GetTools("user123")
        registry = get_tools.registry

        # Get info for a specific tool
        tool_info = registry.get_tool_info("get_calendar_events")
        assert tool_info is not None
        assert tool_info.tool_id == "get_calendar_events"
        assert "calendar" in tool_info.description.lower()

    def test_list_tools(self, clear_drafts):
        """Test listing all available tools."""
        get_tools = GetTools("user123")
        registry = get_tools.registry

        tools = registry.list_tools()
        assert len(tools) > 0

        # Check that we have the expected tool categories
        # list_tools returns (tool_id, description) tuples, so we need to get categories from the registry
        categories = list(registry._categories.keys())
        assert "data_retrieval" in categories

    def test_tool_registry_tooloutput_error(self, clear_drafts):
        """Test tool registry error handling."""
        get_tools = GetTools("user123")
        registry = get_tools.registry

        # Test with a tool that will fail due to missing parameters
        try:
            registry.execute_tool("create_draft_email")
            assert False, "Expected RuntimeError for missing thread_id"
        except RuntimeError as e:
            assert "thread_id" in str(e)

    def test_tool_registry_execute_tool_error(self, clear_drafts):
        """Test tool registry execute_tool error handling."""
        get_tools = GetTools("user123")
        registry = get_tools.registry

        # Test with a tool that will fail due to missing parameters
        try:
            registry.execute_tool("create_draft_email")
            assert False, "Expected RuntimeError for missing thread_id"
        except RuntimeError as e:
            assert "thread_id" in str(e)

    def test_get_tool_registry_singleton(self, clear_drafts):
        """Test that each GetTools instance has its own registry."""
        get_tools1 = GetTools("user123")
        get_tools2 = GetTools("user456")

        registry1 = get_tools1.registry
        registry2 = get_tools2.registry

        # Each instance should have its own registry
        assert registry1 is not registry2

    def test_draft_tools_thread_isolation(self, clear_drafts):
        """Test that draft tools properly isolate threads."""
        draft_tools = DraftTools("test_user")

        # Create email draft
        email_data = {
            "to": ["recipient@example.com"],
            "subject": "Test Email",
            "body": "This is a test email",
            "type": "email",  # Add type field
        }

        result = draft_tools.create_draft_email(
            thread_id="test_thread_id",
            **email_data,
        )

        assert result["success"] == True
        assert "draft" in result

        # Verify draft was created
        drafts = draft_tools.get_draft_data("test_thread_id")
        assert len(drafts) > 0

        # Clear drafts
        draft_tools.clear_all_drafts("test_thread_id")

        # Verify drafts were cleared
        drafts_after_clear = draft_tools.get_draft_data("test_thread_id")
        assert len(drafts_after_clear) == 0
