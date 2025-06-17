"""
Unit tests for ToolExecutorStep workflow step.

Tests the parallel tool execution engine with asyncio support,
tool result aggregation, and progress streaming.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

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
        assert hasattr(tool_executor_step, '_tool_registry')
        assert hasattr(tool_executor_step, '_progress_callbacks')
        assert hasattr(tool_executor_step, '_tool_dependencies')
    
    def test_get_execution_groups(self, tool_executor_step, sample_tool_execution_event):
        """Test grouping tools by execution group ID."""
        groups = tool_executor_step._get_execution_groups(sample_tool_execution_event.tools_to_execute)
        
        assert "group_1" in groups
        assert len(groups["group_1"]) == 2
        assert groups["group_1"][0]["tool_name"] == "get_calendar_events"
        assert groups["group_1"][1]["tool_name"] == "get_emails"
    
    def test_determine_execution_strategy_parallel(self, tool_executor_step):
        """Test determining parallel execution strategy."""
        tools = [
            {"tool_name": "get_calendar_events", "inputs": {}},
            {"tool_name": "get_emails", "inputs": {}}
        ]
        
        strategy = tool_executor_step._determine_execution_strategy(tools, "parallel")
        
        assert strategy == "parallel"
    
    def test_determine_execution_strategy_sequential_override(self, tool_executor_step):
        """Test sequential execution when tools have dependencies."""
        # Mock tool dependencies
        tool_executor_step._tool_dependencies = {
            "create_draft_email": ["get_emails"]
        }
        
        tools = [
            {"tool_name": "get_emails", "inputs": {}},
            {"tool_name": "create_draft_email", "inputs": {}}
        ]
        
        strategy = tool_executor_step._determine_execution_strategy(tools, "parallel")
        
        assert strategy == "sequential"
    
    def test_validate_tool_inputs_valid(self, tool_executor_step):
        """Test tool input validation with valid inputs."""
        tool_config = {
            "tool_name": "get_calendar_events",
            "inputs": {"goal": "Check availability", "user_id": "test_user"}
        }
        
        # Should not raise exception
        tool_executor_step._validate_tool_inputs(tool_config)
    
    def test_validate_tool_inputs_missing_name(self, tool_executor_step):
        """Test tool input validation with missing tool name."""
        tool_config = {
            "inputs": {"goal": "Check availability"}
        }
        
        with pytest.raises(ValueError, match="Tool name is required"):
            tool_executor_step._validate_tool_inputs(tool_config)
    
    def test_validate_tool_inputs_missing_inputs(self, tool_executor_step):
        """Test tool input validation with missing inputs."""
        tool_config = {
            "tool_name": "get_calendar_events"
        }
        
        with pytest.raises(ValueError, match="Tool inputs are required"):
            tool_executor_step._validate_tool_inputs(tool_config)
    
    def test_aggregate_tool_results_success(self, tool_executor_step):
        """Test aggregating successful tool results."""
        individual_results = {
            "get_calendar_events": {
                "success": True,
                "data": {"events": [{"title": "Meeting"}]},
                "execution_time": 1.5
            },
            "get_emails": {
                "success": True,
                "data": {"emails": [{"subject": "Test"}]},
                "execution_time": 2.0
            }
        }
        
        aggregated = tool_executor_step._aggregate_tool_results(individual_results)
        
        assert aggregated["overall_success"] is True
        assert aggregated["successful_tools"] == ["get_calendar_events", "get_emails"]
        assert aggregated["failed_tools"] == []
        assert aggregated["total_execution_time"] == 3.5
        assert "get_calendar_events" in aggregated["results"]
        assert "get_emails" in aggregated["results"]
    
    def test_aggregate_tool_results_partial_failure(self, tool_executor_step):
        """Test aggregating tool results with some failures."""
        individual_results = {
            "get_calendar_events": {
                "success": True,
                "data": {"events": []},
                "execution_time": 1.0
            },
            "get_emails": {
                "success": False,
                "error": "Connection timeout",
                "execution_time": 0.5
            }
        }
        
        aggregated = tool_executor_step._aggregate_tool_results(individual_results)
        
        assert aggregated["overall_success"] is False
        assert aggregated["successful_tools"] == ["get_calendar_events"]
        assert aggregated["failed_tools"] == ["get_emails"]
        assert aggregated["total_execution_time"] == 1.5
        assert "Connection timeout" in str(aggregated["errors"])
    
    def test_should_route_to_planner_true(self, tool_executor_step):
        """Test routing decision - should route to planner."""
        event = Mock()
        event.route_to_planner = True
        
        aggregated_results = {"overall_success": True, "successful_tools": ["get_emails"]}
        
        should_route = tool_executor_step._should_route_to_planner(event, aggregated_results)
        
        assert should_route is True
    
    def test_should_route_to_planner_false(self, tool_executor_step):
        """Test routing decision - should route to drafter."""
        event = Mock()
        event.route_to_planner = False
        
        aggregated_results = {"overall_success": True, "successful_tools": ["get_emails"]}
        
        should_route = tool_executor_step._should_route_to_planner(event, aggregated_results)
        
        assert should_route is False
    
    def test_should_route_to_planner_failure_override(self, tool_executor_step):
        """Test routing decision - failures should route to planner."""
        event = Mock()
        event.route_to_planner = False
        
        aggregated_results = {"overall_success": False, "failed_tools": ["get_emails"]}
        
        should_route = tool_executor_step._should_route_to_planner(event, aggregated_results)
        
        assert should_route is True  # Override due to failures
    
    def test_create_summary_message_success(self, tool_executor_step):
        """Test creating summary message for successful execution."""
        aggregated_results = {
            "overall_success": True,
            "successful_tools": ["get_calendar_events", "get_emails"],
            "failed_tools": [],
            "total_execution_time": 2.5
        }
        
        summary = tool_executor_step._create_summary_message(aggregated_results)
        
        assert "Successfully executed 2 tools" in summary
        assert "get_calendar_events" in summary
        assert "get_emails" in summary
        assert "2.5" in summary
    
    def test_create_summary_message_partial_failure(self, tool_executor_step):
        """Test creating summary message for partial failure."""
        aggregated_results = {
            "overall_success": False,
            "successful_tools": ["get_calendar_events"],
            "failed_tools": ["get_emails"],
            "total_execution_time": 1.5
        }
        
        summary = tool_executor_step._create_summary_message(aggregated_results)
        
        assert "Executed 2 tools" in summary
        assert "1 successful" in summary
        assert "1 failed" in summary
        assert "get_calendar_events" in summary
        assert "get_emails" in summary 