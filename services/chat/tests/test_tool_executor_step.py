"""
Unit tests for ToolExecutorStep workflow step.

Tests the parallel tool execution engine with asyncio support,
tool result aggregation, and progress streaming.
"""

import pytest
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from llama_index.core.workflow import Context
from llama_index.core.llms import LLM

from services.chat.steps.tool_executor_step import ToolExecutorStep
from services.chat.events import (
    ToolExecutionRequestedEvent,
    ToolResultsForPlannerEvent,
    ToolResultsForDrafterEvent,
    WorkflowMetadata
)


class TestToolExecutorStep:
    """Test the ToolExecutorStep workflow step."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = Mock(spec=LLM)
        llm.complete = AsyncMock()
        return llm
    
    @pytest.fixture
    def tool_executor_step(self, mock_llm):
        """Create a ToolExecutorStep instance."""
        return ToolExecutorStep(llm=mock_llm)
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock workflow context."""
        context = Mock(spec=Context)
        context.send_event = Mock()
        return context
    
    @pytest.fixture
    def sample_tool_execution_event(self):
        """Create a sample ToolExecutionRequestedEvent."""
        return ToolExecutionRequestedEvent(
            thread_id="test_thread",
            user_id="test_user",
            tools_to_execute=[
                {
                    "tool_name": "get_calendar_events",
                    "inputs": {"goal": "Check availability"},
                    "execution_group_id": "group_1"
                },
                {
                    "tool_name": "get_emails", 
                    "inputs": {"goal": "Get recent emails"},
                    "execution_group_id": "group_1"
                }
            ],
            execution_strategy="parallel",
            parent_plan_event_id="plan_123",
            route_to_planner=False,
            priority="medium",
            metadata=WorkflowMetadata(confidence=0.8, priority="medium")
        )
    
    def test_initialization(self, tool_executor_step):
        """Test ToolExecutorStep initialization."""
        assert tool_executor_step.step_name == "ToolExecutorStep"
        assert hasattr(tool_executor_step, 'tool_registry')
        assert hasattr(tool_executor_step, '_execution_cache')
        assert hasattr(tool_executor_step, '_tool_dependencies')
    
    def test_extract_planning_insights(self, tool_executor_step):
        """Test extracting planning insights from tool results."""
        tool_results = {
            "get_calendar_events": {"data": {"events": [], "availability": "busy"}},
            "get_emails": {"data": {"emails": [{"urgent": True}]}}
        }
        
        insights = tool_executor_step._extract_planning_insights(tool_results)
        
        assert isinstance(insights, dict)
        assert "calendar_availability" in insights
        assert "email_context" in insights
        assert "needs_replanning" in insights
    
    def test_extract_draft_context(self, tool_executor_step):
        """Test extracting draft context from tool results."""
        tool_results = {
            "get_calendar_events": {"data": {"events": [{"title": "Meeting"}]}},
            "get_emails": {"data": {"emails": [{"subject": "Project Update"}]}}
        }
        
        context = tool_executor_step._extract_draft_context(tool_results)
        
        assert isinstance(context, dict)
        assert "get_calendar_events_data" in context
        assert "get_emails_data" in context
    
    def test_create_context_updates(self, tool_executor_step):
        """Test creating context updates from tool results."""
        tool_results = {
            "get_calendar_events": {"data": {"events": []}},
            "get_emails": {"data": {"emails": []}}
        }
        
        updates = tool_executor_step._create_context_updates(tool_results, "planner")
        
        assert isinstance(updates, dict)
        assert "tool_results_planner" in updates
        assert updates["tool_results_planner"]["result_count"] == 2
    
    def test_create_cache_key(self, tool_executor_step):
        """Test creating cache key for tool results."""
        tool_name = "get_calendar_events"
        inputs = {"user_id": "test_user", "goal": "Check availability"}
        
        cache_key = tool_executor_step._create_cache_key(tool_name, inputs)
        
        assert isinstance(cache_key, str)
        assert tool_name in cache_key
    
    def test_is_cache_valid(self, tool_executor_step):
        """Test cache validity checking."""
        # Valid cache result (recent)
        valid_cache = {"timestamp": datetime.now(), "data": {"events": []}}
        assert tool_executor_step._is_cache_valid(valid_cache) is True
        
        # Invalid cache result (old)
        old_time = datetime.now() - timedelta(hours=2)
        invalid_cache = {"timestamp": old_time, "data": {"events": []}}  # 2 hours old
        assert tool_executor_step._is_cache_valid(invalid_cache) is False
    
    def test_should_cache_result(self, tool_executor_step):
        """Test determining if result should be cached."""
        # Should cache user preferences (based on actual implementation)
        assert tool_executor_step._should_cache_result("get_user_preferences", {"prefs": {}}) is True
        
        # Should not cache calendar events (real-time data)
        assert tool_executor_step._should_cache_result("get_calendar_events", {"events": []}) is False
    
    def test_is_critical_tool(self, tool_executor_step):
        """Test identifying critical tools."""
        # Auth tools should be critical (based on actual implementation)
        assert tool_executor_step._is_critical_tool("authenticate_user") is True
        assert tool_executor_step._is_critical_tool("get_user_context") is True
        
        # Other tools may not be critical
        assert tool_executor_step._is_critical_tool("get_calendar_events") is False
    
    def test_should_replan_from_results(self, tool_executor_step):
        """Test determining if results require re-planning."""
        # Results with errors should trigger re-planning
        error_results = {
            "get_calendar_events": {"error": "API connection failed"}
        }
        assert tool_executor_step._should_replan_from_results(error_results) is True
        
        # Normal results should not trigger re-planning
        normal_results = {
            "get_calendar_events": {"data": {"events": []}}
        }
        assert tool_executor_step._should_replan_from_results(normal_results) is False
    
    def test_sanitize_for_draft(self, tool_executor_step):
        """Test sanitizing tool results for draft creation."""
        # Test with complex nested data
        complex_result = {
            "data": {"events": [{"title": "Meeting", "attendees": ["user1", "user2"]}]},
            "metadata": {"source": "calendar_api"}
        }
        
        sanitized = tool_executor_step._sanitize_for_draft(complex_result)
        
        assert isinstance(sanitized, dict)
        assert "data" in sanitized
    
    @pytest.mark.asyncio 
    async def test_execute_single_tool_success(self, tool_executor_step):
        """Test executing a single tool successfully."""
        # Mock the tool registry to return a successful result object
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = {"events": []}
        
        tool_executor_step.tool_registry.execute_tool = AsyncMock(
            return_value=mock_result
        )
        
        result = await tool_executor_step._execute_single_tool(
            "get_calendar_events",
            {"user_id": "test_user"}
        )
        
        assert result == {"events": []}
    
    @pytest.mark.asyncio
    async def test_execute_single_tool_failure(self, tool_executor_step):
        """Test executing a single tool with failure."""
        # Mock the tool registry to return a failed result object
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Tool execution failed"
        
        tool_executor_step.tool_registry.execute_tool = AsyncMock(
            return_value=mock_result
        )
        
        with pytest.raises(Exception, match="Tool execution failed"):
            await tool_executor_step._execute_single_tool(
                "get_calendar_events", 
                {"user_id": "test_user"}
            ) 