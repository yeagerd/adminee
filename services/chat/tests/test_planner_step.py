"""
Unit tests for PlannerStep workflow step.

Tests the LLM-based planner that converts user intent into structured execution plans
with confidence assessment, routing logic, and re-planning capabilities.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from llama_index.core.workflow import Context
from llama_index.core.llms import LLM

from services.chat.steps.planner_step import PlannerStep
from services.chat.events import (
    UserInputEvent,
    ToolExecutionRequestedEvent,
    ClarificationRequestedEvent,
    ClarificationReplanRequestedEvent,
    ToolResultsForPlannerEvent,
    ContextUpdatedEvent,
    WorkflowMetadata
)


class TestPlannerStep:
    """Test the PlannerStep workflow step."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = Mock(spec=LLM)
        llm.complete = AsyncMock()
        return llm
    
    @pytest.fixture
    def planner_step(self, mock_llm):
        """Create a PlannerStep instance."""
        return PlannerStep(llm=mock_llm)
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock workflow context."""
        context = Mock(spec=Context)
        context.send_event = Mock()
        return context
    
    @pytest.fixture
    def sample_user_input_event(self):
        """Create a sample UserInputEvent."""
        return UserInputEvent(
            thread_id="test_thread",
            user_id="test_user",
            message="Schedule a meeting with John next week",
            context={
                "user_preferences": {"timezone": "UTC"},
                "conversation_history": []
            },
            metadata=WorkflowMetadata(
                confidence=1.0,
                priority="high"
            )
        )
    
    @pytest.mark.asyncio
    async def test_handle_user_input_basic_planning(self, planner_step, mock_context, sample_user_input_event):
        """Test basic planning from user input."""
        # Mock the analysis method to return a proper analysis
        mock_analysis = {
            "intent": "schedule_meeting",
            "confidence": 0.85,
            "entities": {"person": "John", "timeframe": "next week"},
            "requires_tools": True,
            "complexity": "medium",
            "suggested_tools": ["get_calendar_events", "create_draft_calendar_event"],
            "assumptions": ["User wants to schedule for next week"],
            "clarification_points": []
        }
        
        # Mock the LLM call
        planner_step.safe_llm_call = AsyncMock(return_value=json.dumps(mock_analysis))
        
        # Mock emit methods
        planner_step.emit_context_update = AsyncMock()
        planner_step._emit_tool_execution_requests = AsyncMock()
        
        # Execute planning
        await planner_step._handle_user_input(mock_context, sample_user_input_event)
        
        # Verify LLM was called for analysis
        planner_step.safe_llm_call.assert_called_once()
        
        # Verify context update was emitted
        planner_step.emit_context_update.assert_called()
        
        # Verify tool execution was requested
        planner_step._emit_tool_execution_requests.assert_called_once()
    
    def test_get_user_preferences_default(self, planner_step):
        """Test getting default user preferences."""
        prefs = planner_step._get_user_preferences("new_user")
        
        assert "communication_style" in prefs
        assert "urgency_preference" in prefs
        assert "detail_level" in prefs
        assert "preferred_tools" in prefs
        assert prefs["communication_style"] == "professional"
        assert isinstance(prefs["preferred_tools"], list)
    
    def test_get_user_preferences_existing(self, planner_step):
        """Test getting existing user preferences."""
        # Set up existing preferences
        planner_step._user_preferences["existing_user"] = {
            "communication_style": "brief",
            "urgency_preference": "high"
        }
        
        prefs = planner_step._get_user_preferences("existing_user")
        
        assert prefs["communication_style"] == "brief"
        assert prefs["urgency_preference"] == "high"
    
    def test_get_default_analysis_value(self, planner_step):
        """Test getting default analysis values."""
        assert planner_step._get_default_analysis_value("intent") == "unknown_request"
        assert planner_step._get_default_analysis_value("confidence") == 0.5
        assert isinstance(planner_step._get_default_analysis_value("entities"), dict)
        assert isinstance(planner_step._get_default_analysis_value("suggested_tools"), list)
    
    def test_get_fallback_analysis(self, planner_step):
        """Test fallback analysis generation."""
        message = "Schedule a meeting"
        analysis = planner_step._get_fallback_analysis(message)
        
        assert "Schedule a meeting" in analysis["intent"]
        assert analysis["confidence"] == 0.3
        assert isinstance(analysis["entities"], dict)
        assert isinstance(analysis["suggested_tools"], list)
    
    def test_get_default_tool_analysis_value(self, planner_step):
        """Test getting default tool analysis values."""
        assert planner_step._get_default_tool_analysis_value("confidence") == 0.7
        assert isinstance(planner_step._get_default_tool_analysis_value("next_steps"), list)
        assert planner_step._get_default_tool_analysis_value("ready_for_drafting") == True
    
    def test_get_fallback_tool_analysis(self, planner_step):
        """Test fallback tool analysis generation."""
        analysis = planner_step._get_fallback_tool_analysis()
        
        assert analysis["confidence"] == 0.6
        assert analysis["ready_for_drafting"] == True
        assert isinstance(analysis["next_steps"], list)
        assert isinstance(analysis["suggested_tools"], list) 