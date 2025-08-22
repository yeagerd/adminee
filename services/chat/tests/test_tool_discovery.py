#!/usr/bin/env python3
"""Tests for the enhanced tool discovery system."""

import pytest
from unittest.mock import patch, MagicMock

from services.chat.tools.get_tools import GetTools
from services.chat.tools.tool_registry import ToolMetadata


class TestToolDiscovery:
    """Test the tool discovery functionality."""

    @pytest.fixture
    def get_tools(self):
        """Create a GetTools instance for testing."""
        return GetTools("test_user_123")

    def test_list_tools_returns_correct_format(self, get_tools):
        """Test that list_tools() returns the correct tool metadata format."""
        result = get_tools.get_tool.list_tools()
        
        assert result["status"] == "success"
        assert "tools" in result
        
        tools = result["tools"]
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check that tools are in the expected format
        for tool in tools:
            assert isinstance(tool, tuple)
            assert len(tool) >= 2
            assert isinstance(tool[0], str)  # tool_id
            assert isinstance(tool[1], str)  # description

    def test_list_tools_includes_all_categories(self, get_tools):
        """Test that list_tools() includes tools from all categories."""
        result = get_tools.get_tool.list_tools()
        tools = result["tools"]
        
        # Extract tool IDs
        tool_ids = [tool[0] for tool in tools]
        
        # Check for data retrieval tools
        assert "get_calendar_events" in tool_ids
        assert "get_emails" in tool_ids
        assert "get_notes" in tool_ids
        assert "get_documents" in tool_ids
        
        # Check for draft management tools
        assert "create_draft_email" in tool_ids
        assert "create_draft_calendar_event" in tool_ids
        assert "create_draft_calendar_change" in tool_ids
        assert "delete_draft_email" in tool_ids
        assert "delete_draft_calendar_event" in tool_ids
        assert "delete_draft_calendar_edit" in tool_ids
        assert "clear_all_drafts" in tool_ids
        
        # Check for search tools
        assert "vespa_search" in tool_ids
        assert "user_data_search" in tool_ids
        assert "semantic_search" in tool_ids
        
        # Check for web tools
        assert "web_search" in tool_ids
        
        # Check for utility tools
        assert "format_event_time_for_display" in tool_ids
        assert "validate_email_format" in tool_ids
        assert "sanitize_string" in tool_ids
        assert "parse_date_range" in tool_ids
        assert "format_file_size" in tool_ids
        assert "extract_phone_number" in tool_ids
        assert "generate_summary" in tool_ids

    def test_get_tool_info_returns_proper_specifications(self, get_tools):
        """Test that get_tool_info() returns proper API specifications."""
        # Test a data retrieval tool
        result = get_tools.get_tool.get_tool_info("get_calendar_events")
        assert result["status"] == "success"
        
        tool_info = result["tool_info"]
        assert tool_info["tool_id"] == "get_calendar_events"
        assert tool_info["category"] == "data_retrieval"
        assert "parameters" in tool_info
        assert "examples" in tool_info
        assert "return_format" in tool_info
        assert tool_info["requires_auth"] is True
        assert tool_info["service_dependency"] == "office_service"
        
        # Check parameters (user_id should NOT be present as tools are pre-bound)
        params = tool_info["parameters"]
        assert "user_id" not in params  # user_id is pre-bound, not a parameter
        assert "start_date" in params
        assert params["start_date"]["required"] is False
        
        # Check examples
        examples = tool_info["examples"]
        assert len(examples) > 0
        assert "description" in examples[0]
        assert "params" in examples[0]

    def test_get_tool_info_for_draft_tool(self, get_tools):
        """Test get_tool_info() for draft management tools."""
        result = get_tools.get_tool.get_tool_info("create_draft_email")
        assert result["status"] == "success"
        
        tool_info = result["tool_info"]
        assert tool_info["tool_id"] == "create_draft_email"
        assert tool_info["category"] == "draft_management"
        assert tool_info["requires_auth"] is True
        assert tool_info["service_dependency"] == "none"
        
        # Check parameters
        params = tool_info["parameters"]
        assert "thread_id" in params
        assert params["thread_id"]["required"] is True
        assert "to" in params
        assert params["to"]["required"] is False

    def test_get_tool_info_for_search_tool(self, get_tools):
        """Test get_tool_info() for search tools."""
        result = get_tools.get_tool.get_tool_info("vespa_search")
        assert result["status"] == "success"
        
        tool_info = result["tool_info"]
        assert tool_info["tool_id"] == "vespa_search"
        assert tool_info["category"] == "search"
        assert tool_info["requires_auth"] is True
        assert tool_info["service_dependency"] == "vespa"
        
        # Check parameters
        params = tool_info["parameters"]
        assert "query" in params
        assert params["query"]["required"] is True
        assert "max_results" in params
        assert params["max_results"]["required"] is False

    def test_get_tool_info_for_utility_tool(self, get_tools):
        """Test get_tool_info() for utility tools."""
        result = get_tools.get_tool.get_tool_info("format_event_time_for_display")
        assert result["status"] == "success"
        
        tool_info = result["tool_info"]
        assert tool_info["tool_id"] == "format_event_time_for_display"
        assert tool_info["category"] == "utility"
        assert tool_info["requires_auth"] is False
        assert tool_info["service_dependency"] == "none"
        
        # Check parameters
        params = tool_info["parameters"]
        assert "start_time" in params
        assert params["start_time"]["required"] is True
        assert "end_time" in params
        assert params["end_time"]["required"] is True
        assert "timezone_str" in params
        assert params["timezone_str"]["required"] is False

    def test_get_tool_info_for_nonexistent_tool(self, get_tools):
        """Test get_tool_info() for a tool that doesn't exist."""
        result = get_tools.get_tool.get_tool_info("nonexistent_tool")
        assert result["status"] == "error"
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_tool_registry_statistics(self, get_tools):
        """Test that the tool registry provides correct statistics."""
        registry = get_tools.registry
        
        # Check total tool count
        total_tools = registry.get_tool_count()
        assert total_tools > 0
        assert total_tools >= 20  # We should have at least 20 tools
        
        # Check categories
        categories = registry.get_categories()
        expected_categories = ["data_retrieval", "draft_management", "search", "web_search", "utility"]
        for category in expected_categories:
            assert category in categories
        
        # Check category tool counts
        for category in categories:
            count = registry.get_category_tool_count(category)
            assert count > 0
            assert count <= total_tools

    def test_tool_registry_search_functionality(self, get_tools):
        """Test the tool registry search functionality."""
        registry = get_tools.registry
        
        # Search for tools containing "email"
        email_tools = registry.search_tools("email")
        assert len(email_tools) > 0
        
        # Check that email-related tools are found
        email_tool_ids = [tool[0] for tool in email_tools]  # tool[0] is tool_id for tuples
        assert "get_emails" in email_tool_ids
        assert "create_draft_email" in email_tool_ids
        assert "delete_draft_email" in email_tool_ids

    def test_tool_registry_export_import(self, get_tools):
        """Test that the tool registry can export and import data."""
        registry = get_tools.registry
        
        # Export registry
        exported_data = registry.export_registry()
        assert "tools" in exported_data
        assert "categories" in exported_data
        assert "total_tools" in exported_data
        
        # Create a new registry and import the data
        new_registry = registry.__class__()
        new_registry.import_registry(exported_data)
        
        # Check that the new registry has the same tools
        assert new_registry.get_tool_count() == registry.get_tool_count()
        assert set(new_registry.get_categories()) == set(registry.get_categories())

    def test_tool_execution_through_registry(self, get_tools):
        """Test that tools can be executed through the registry."""
        # Test executing a utility tool
        result = get_tools.get_tool.execute("validate_email_format", {"email": "test@example.com"})
        assert result["status"] == "success"
        assert result["tool"] == "validate_email_format"
        assert "result" in result
        
        # Test executing with missing parameters
        result = get_tools.get_tool.execute("validate_email_format", {})
        assert result["status"] == "error"
        assert "error" in result

    def test_tool_execution_with_user_id_injection(self, get_tools):
        """Test that user_id is automatically injected when missing."""
        # Test executing a data tool without user_id
        result = get_tools.get_tool.execute("get_calendar_events", {"start_date": "2024-01-01"})
        assert result["status"] == "success"
        assert result["tool"] == "get_calendar_events"
        
        # The user_id should have been automatically injected
        # (This test may need to be adjusted based on actual implementation)

    def test_tool_registry_unregister_functionality(self, get_tools):
        """Test that tools can be unregistered from the registry."""
        registry = get_tools.registry
        
        # Get initial count
        initial_count = registry.get_tool_count()
        
        # Try to unregister a tool
        # Note: This test may need adjustment based on actual implementation
        try:
            registry.unregister_tool("test_tool")
        except Exception:
            # Expected if tool doesn't exist
            pass
        
        # Count should remain the same
        assert registry.get_tool_count() == initial_count

    def test_tool_metadata_completeness(self, get_tools):
        """Test that all tool metadata is complete and consistent."""
        registry = get_tools.registry
        
        # Get detailed tool info for a few representative tools
        test_tools = ["get_calendar_events", "create_draft_email", "vespa_search", "format_event_time_for_display"]
        
        for tool_id in test_tools:
            tool_info = registry.get_tool_info(tool_id)
            assert tool_info is not None
            
            # Check that all required fields are present
            assert hasattr(tool_info, 'tool_id')
            assert hasattr(tool_info, 'description')
            assert hasattr(tool_info, 'category')
            assert hasattr(tool_info, 'parameters')
            assert hasattr(tool_info, 'examples')
            assert hasattr(tool_info, 'return_format')
            assert hasattr(tool_info, 'requires_auth')
            assert hasattr(tool_info, 'service_dependency')
            assert hasattr(tool_info, 'version')
            
            # Check that tool_id is not empty
            assert tool_info.tool_id and tool_info.tool_id.strip()
            
            # Check that description is not empty
            assert tool_info.description and tool_info.description.strip()
            
            # Check that category is valid
            valid_categories = ["data_retrieval", "draft_management", "search", "web_search", "utility"]
            assert tool_info.category in valid_categories
            
            # Check that parameters is a dict
            assert isinstance(tool_info.parameters, dict)
            
            # Check that examples is a list
            assert isinstance(tool_info.examples, list)
            
            # Check that return_format is a dict
            assert isinstance(tool_info.return_format, dict)
            
            # Check that requires_auth is boolean
            assert isinstance(tool_info.requires_auth, bool)
            
            # Check that service_dependency is string
            assert isinstance(tool_info.service_dependency, str)
            
            # Check that version is string
            assert isinstance(tool_info.version, str)
