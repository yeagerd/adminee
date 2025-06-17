"""
Unit tests for ClarifierStep workflow step.

Tests the LLM-based question generation, user response routing,
clarification analysis, and timeout handling capabilities.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from llama_index.core.workflow import Context
from llama_index.core.llms import LLM

from services.chat.steps.clarifier_step import ClarifierStep
from services.chat.events import (
    ClarificationRequestedEvent,
    UserInputEvent,
    ClarificationReplanRequestedEvent,
    ClarificationPlannerUnblockedEvent,
    ClarificationDraftUnblockedEvent,
    WorkflowMetadata
)


class TestClarifierStep:
    """Test the ClarifierStep workflow step."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = Mock(spec=LLM)
        llm.complete = AsyncMock()
        return llm
    
    @pytest.fixture
    def clarifier_step(self, mock_llm):
        """Create a ClarifierStep instance."""
        return ClarifierStep(llm=mock_llm)
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock workflow context."""
        context = Mock(spec=Context)
        context.send_event = Mock()
        return context
    
    @pytest.fixture
    def sample_clarification_requested_event(self):
        """Create a sample ClarificationRequestedEvent."""
        return ClarificationRequestedEvent(
            thread_id="test_thread",
            user_id="test_user",
            clarification_requests=[
                {
                    "question": "What time would you prefer for the meeting?",
                    "context": "time_preference",
                    "blocking": False,
                    "confidence_impact": 0.2
                }
            ],
            parent_plan_event_id="plan_123",
            can_proceed_without=True,
            blocks_planning=False,
            metadata=WorkflowMetadata(confidence=0.7, priority="medium")
        )
    
    @pytest.fixture
    def sample_user_response_event(self):
        """Create a sample UserInputEvent with clarification response."""
        return UserInputEvent(
            thread_id="test_thread",
            user_id="test_user",
            message="I prefer 2pm for the meeting",
            context={
                "clarification_response": True,
                "original_question": "What time would you prefer?",
                "conversation_history": []
            },
            metadata=WorkflowMetadata(confidence=1.0, priority="high")
        )
    
    def test_initialization(self, clarifier_step):
        """Test ClarifierStep initialization."""
        assert clarifier_step.step_name == "ClarifierStep"
        assert hasattr(clarifier_step, '_clarification_history')
        assert hasattr(clarifier_step, '_blocking_contexts')
        assert hasattr(clarifier_step, '_clarification_timeouts')
        assert hasattr(clarifier_step, '_default_timeout')
        assert clarifier_step._default_timeout == 300  # 5 minutes
    
    def test_get_clarification_timeout_default(self, clarifier_step):
        """Test getting default clarification timeout."""
        from services.chat.events import ClarificationRequest
        
        requests = [
            ClarificationRequest(
                question="What time?",
                context={"type": "time_preference"},
                blocking=False,
                confidence_impact=0.2
            )
        ]
        
        timeout = clarifier_step._get_clarification_timeout(requests)
        
        assert timeout == 300  # Default 5 minutes
    
    def test_get_clarification_timeout_urgent(self, clarifier_step):
        """Test getting timeout for urgent clarification."""
        from services.chat.events import ClarificationRequest
        
        requests = [
            ClarificationRequest(
                question="Urgent: What time?",
                context={"type": "time_preference", "urgency": "high"},
                blocking=True,
                confidence_impact=0.8
            )
        ]
        
        timeout = clarifier_step._get_clarification_timeout(requests)
        
        assert timeout >= 300  # Should be longer for blocking/critical requests
    
    def test_get_default_analysis_value(self, clarifier_step):
        """Test getting default analysis values."""
        assert clarifier_step._get_default_analysis_value("confidence") == 0.7
        assert clarifier_step._get_default_analysis_value("intent_changed") is False
        assert clarifier_step._get_default_analysis_value("planning_unblocked") is True
        assert clarifier_step._get_default_analysis_value("unknown_key") is None
    
    def test_get_fallback_analysis(self, clarifier_step):
        """Test getting fallback analysis."""
        user_responses = {"response_0": "I prefer 2pm"}
        
        analysis = clarifier_step._get_fallback_analysis(user_responses)
        
        assert analysis["confidence"] == 0.5
        assert analysis["intent_changed"] is False
        assert analysis["planning_unblocked"] is True
        assert analysis["draft_ready"] is False  # Only 1 response, needs 2+
    
    def test_extract_updated_request(self, clarifier_step):
        """Test extracting updated request from user responses."""
        user_responses = {
            "response_0": "Actually, I want to send an email instead of scheduling a meeting",
            "response_1": "Please make it urgent priority"
        }
        
        updated_request = clarifier_step._extract_updated_request(user_responses)
        
        assert isinstance(updated_request, str)
        assert len(updated_request) > 0
    
    @pytest.mark.asyncio
    async def test_simulate_user_responses(self, clarifier_step):
        """Test simulating user responses for testing."""
        from services.chat.events import ClarificationRequest
        
        requests = [
            ClarificationRequest(
                question="Can you provide more details?",
                context={"type": "details"},
                blocking=False,
                confidence_impact=0.3
            ),
            ClarificationRequest(
                question="What are your preferences?",
                context={"type": "preferences"}, 
                blocking=False,
                confidence_impact=0.2
            )
        ]
        
        responses = await clarifier_step._simulate_user_responses(requests)
        
        assert len(responses) == 2
        assert "response_0" in responses
        assert "response_1" in responses
        assert "meeting" in responses["response_0"].lower()
        assert "professional" in responses["response_1"].lower()
    
    def test_build_response_analysis_prompt(self, clarifier_step):
        """Test building response analysis prompt."""
        from services.chat.events import ClarificationRequest
        
        original_requests = [
            ClarificationRequest(
                question="What time works for you?",
                context={"type": "time_preference"},
                blocking=False,
                confidence_impact=0.3
            )
        ]
        user_responses = {"response_0": "I prefer 2pm"}
        
        prompt = clarifier_step._build_response_analysis_prompt(
            original_requests, user_responses
        )
        
        assert isinstance(prompt, str)
        assert "analyze" in prompt.lower()
        assert "What time works for you?" in prompt
        assert "I prefer 2pm" in prompt 