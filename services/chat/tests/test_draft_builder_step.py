"""
Unit tests for DraftBuilderStep workflow step.

Tests the draft creation and assembly engine with tool result integration,
clarification context handling, and quality validation.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from llama_index.core.workflow import Context
from llama_index.core.llms import LLM

from services.chat.steps.draft_builder_step import DraftBuilderStep
from services.chat.events import (
    ToolResultsForDrafterEvent,
    ClarificationDraftUnblockedEvent,
    DraftCreatedEvent,
    WorkflowMetadata
)


class TestDraftBuilderStep:
    """Test the DraftBuilderStep workflow step."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = Mock(spec=LLM)
        llm.complete = AsyncMock()
        llm.acomplete = AsyncMock()
        return llm
    
    @pytest.fixture
    def draft_builder_step(self, mock_llm):
        """Create a DraftBuilderStep instance."""
        return DraftBuilderStep(llm=mock_llm)
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock workflow context."""
        context = Mock(spec=Context)
        context.send_event = Mock()
        return context
    
    @pytest.fixture
    def sample_tool_results_event(self):
        """Create a sample ToolResultsForDrafterEvent."""
        return ToolResultsForDrafterEvent(
            thread_id="test_thread",
            user_id="test_user",
            parent_request_event_id="plan_123",
            tool_results={
                "get_calendar_events": {"data": {"events": [{"title": "Meeting"}]}},
                "get_emails": {"data": {"emails": [{"subject": "Project Update"}]}}
            },
            execution_success=True,
            error_messages=[],
            draft_context={"purpose": "create_email", "recipient": "team@company.com"},
            context_updates={},
            metadata=WorkflowMetadata(confidence=0.9, priority="medium")
        )
    
    def test_initialization(self, draft_builder_step):
        """Test DraftBuilderStep initialization."""
        assert draft_builder_step.step_name == "DraftBuilderStep"
        assert hasattr(draft_builder_step, '_draft_templates')
        assert hasattr(draft_builder_step, '_user_style_preferences')
        assert hasattr(draft_builder_step, '_quality_metrics')
        assert hasattr(draft_builder_step, '_draft_versions')
        assert hasattr(draft_builder_step, '_draft_history')
    
    def test_analyze_draft_requirements(self, draft_builder_step):
        """Test analyzing draft requirements from tool results."""
        tool_results = {
            "get_calendar_events": {"data": {"events": [{"title": "Meeting"}]}},
            "get_emails": {"data": {"emails": []}}
        }
        draft_context = {"purpose": "create_email", "recipient": "team@company.com"}
        
        analysis = draft_builder_step._analyze_draft_requirements(tool_results, draft_context)
        
        assert isinstance(analysis, dict)
        assert "draft_type" in analysis
        assert "content_sources" in analysis
        assert "required_elements" in analysis
    
    def test_build_draft_prompt(self, draft_builder_step):
        """Test building draft prompt from context."""
        tool_results = {"get_emails": {"data": {"emails": []}}}
        draft_context = {"purpose": "create_email"}
        draft_analysis = {"draft_type": "email", "content_sources": ["emails"]}
        user_style = {"tone": "professional", "length": "medium"}
        
        prompt = draft_builder_step._build_draft_prompt(
            tool_results, draft_context, draft_analysis, user_style
        )
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "email" in prompt.lower()
    
    def test_build_clarification_draft_prompt(self, draft_builder_step):
        """Test building clarification-based draft prompt."""
        combined_context = {"purpose": "create_email", "recipient": "team@company.com"}
        clarification_insights = {"user_intent": "schedule_meeting", "preferences": {"time": "afternoon"}}
        user_style = {"tone": "professional"}
        
        prompt = draft_builder_step._build_clarification_draft_prompt(
            combined_context, clarification_insights, user_style
        )
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "schedule" in prompt.lower()
    
    def test_structure_draft_content(self, draft_builder_step):
        """Test structuring raw draft content."""
        raw_content = "Subject: Team Meeting\n\nHi team,\n\nLet's schedule a meeting for next week.\n\nBest regards"
        draft_type = "email"
        tool_results = {"get_calendar_events": {"data": {"events": []}}}
        
        structured = draft_builder_step._structure_draft_content(raw_content, draft_type, tool_results)
        
        assert isinstance(structured, dict)
        assert "type" in structured
        assert "content" in structured
        assert structured["type"] == "email"
    
    def test_get_user_style_preferences_default(self, draft_builder_step):
        """Test getting default user style preferences."""
        prefs = draft_builder_step._get_user_style_preferences("new_user")
        
        assert isinstance(prefs, dict)
        assert "tone" in prefs
        assert "format" in prefs
        assert prefs["tone"] == "professional"
    
    def test_get_user_style_preferences_existing(self, draft_builder_step):
        """Test getting existing user style preferences."""
        # Set up existing preferences
        draft_builder_step._user_style_preferences["existing_user"] = {
            "tone": "casual",
            "format": "concise"
        }
        
        prefs = draft_builder_step._get_user_style_preferences("existing_user")
        
        assert prefs["tone"] == "casual"
        assert prefs["format"] == "concise"
    
    def test_summarize_tool_results(self, draft_builder_step):
        """Test summarizing tool results."""
        tool_results = {
            "get_calendar_events": {"data": {"events": [{"title": "Meeting", "time": "2pm"}]}},
            "get_emails": {"data": {"emails": [{"subject": "Project Update", "from": "alice@company.com"}]}}
        }
        
        summary = draft_builder_step._summarize_tool_results(tool_results)
        
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "Meeting" in summary or "Project Update" in summary
    
    def test_extract_email_components(self, draft_builder_step):
        """Test extracting email components from content."""
        content = "Subject: Team Meeting\n\nHi team,\n\nLet's schedule a meeting.\n\nBest regards,\nAlice"
        
        components = draft_builder_step._extract_email_components(content)
        
        assert isinstance(components, dict)
        assert "subject" in components
        assert "body" in components
        assert components["subject"] == "Team Meeting"
    
    def test_extract_meeting_elements(self, draft_builder_step):
        """Test extracting meeting elements from content."""
        content = "Meeting: Project Review\nTime: 2pm tomorrow\nAttendees: Alice, Bob, Charlie"
        
        elements = draft_builder_step._extract_meeting_elements(content)
        
        assert isinstance(elements, dict)
        assert "title" in elements
        assert "time" in elements
        assert "attendees" in elements
    
    def test_extract_document_insights(self, draft_builder_step):
        """Test extracting document insights from content."""
        content = "This document contains important project information including timelines and deliverables."
        
        insights = draft_builder_step._extract_document_insights(content)
        
        assert isinstance(insights, dict)
        assert "key_topics" in insights
        assert "document_type" in insights
    
    def test_calculate_draft_quality(self, draft_builder_step):
        """Test calculating draft quality score."""
        high_quality_draft = {
            "type": "email",
            "content": "Subject: Important Meeting\n\nDear team,\n\nI hope this email finds you well. I would like to schedule an important meeting to discuss our upcoming project milestones and deliverables.\n\nBest regards,\nAlice",
            "metadata": {"word_count": 25}
        }
        
        score = draft_builder_step._calculate_draft_quality(high_quality_draft)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be reasonably high quality
    
    def test_calculate_draft_quality_low(self, draft_builder_step):
        """Test calculating draft quality for low quality content."""
        low_quality_draft = {
            "type": "email",
            "content": "hi",
            "metadata": {"word_count": 1}
        }
        
        score = draft_builder_step._calculate_draft_quality(low_quality_draft)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Should be low quality
    
    @pytest.mark.asyncio
    async def test_validate_draft_completeness_complete(self, draft_builder_step):
        """Test validating complete draft."""
        draft_content = {
            "type": "email",
            "content": "Subject: Meeting\n\nHi team,\n\nLet's meet tomorrow.\n\nBest regards",
            "metadata": {"word_count": 10}
        }
        tool_results = {"get_calendar_events": {"data": {"events": []}}}
        draft_context = {"purpose": "create_email"}
        
        validation = await draft_builder_step._validate_draft_completeness(
            draft_content, tool_results, draft_context
        )
        
        assert isinstance(validation, dict)
        assert "is_complete" in validation
        assert "completeness_score" in validation
        assert "missing_elements" in validation
    
    def test_validate_email_draft(self, draft_builder_step):
        """Test validating email draft structure."""
        content = "Subject: Team Meeting\n\nHi team,\n\nLet's schedule a meeting.\n\nBest regards"
        
        validation = draft_builder_step._validate_email_draft(content)
        
        assert isinstance(validation, dict)
        assert "has_subject" in validation
        assert "has_greeting" in validation
        assert "has_closing" in validation
        assert validation["has_subject"] is True
    
    def test_validate_meeting_summary(self, draft_builder_step):
        """Test validating meeting summary."""
        content = "Meeting Summary: Project Review\nAttendees: Alice, Bob\nDecisions: Continue with current timeline"
        tool_results = {"get_calendar_events": {"data": {"events": [{"title": "Project Review"}]}}}
        
        validation = draft_builder_step._validate_meeting_summary(content, tool_results)
        
        assert isinstance(validation, dict)
        assert "has_title" in validation
        assert "has_attendees" in validation
        assert "has_decisions" in validation
    
    def test_validate_document_summary(self, draft_builder_step):
        """Test validating document summary."""
        content = "Document Summary: This document outlines the project requirements and timeline."
        tool_results = {"get_documents": {"data": {"documents": [{"title": "Project Requirements"}]}}}
        
        validation = draft_builder_step._validate_document_summary(content, tool_results)
        
        assert isinstance(validation, dict)
        assert "has_summary" in validation
        assert "covers_key_points" in validation
    
    def test_create_draft_version_new(self, draft_builder_step):
        """Test creating new draft version."""
        thread_id = "test_thread"
        draft_content = {"type": "email", "content": "Test email content"}
        source = "tool_results"
        
        version_info = draft_builder_step._create_draft_version(thread_id, draft_content, source)
        
        assert isinstance(version_info, dict)
        assert "version" in version_info
        assert "timestamp" in version_info
        assert "source" in version_info
        assert version_info["version"] == 1
        assert version_info["source"] == source
    
    def test_create_draft_version_update(self, draft_builder_step):
        """Test creating updated draft version."""
        thread_id = "test_thread"
        initial_content = {"type": "email", "content": "Initial content"}
        updated_content = {"type": "email", "content": "Updated content"}
        
        # Create initial version
        draft_builder_step._create_draft_version(thread_id, initial_content, "tool_results")
        
        # Create updated version
        version_info = draft_builder_step._create_draft_version(thread_id, updated_content, "clarification")
        
        assert version_info["version"] == 2
        assert version_info["source"] == "clarification"
    
    def test_get_draft_history(self, draft_builder_step):
        """Test getting draft history."""
        thread_id = "test_thread"
        content1 = {"type": "email", "content": "First draft"}
        content2 = {"type": "email", "content": "Second draft"}
        
        # Create multiple versions
        draft_builder_step._create_draft_version(thread_id, content1, "tool_results")
        draft_builder_step._create_draft_version(thread_id, content2, "clarification")
        
        history = draft_builder_step._get_draft_history(thread_id)
        
        assert isinstance(history, list)
        assert len(history) == 2
        assert history[0]["version"] == 1
        assert history[1]["version"] == 2
    
    def test_get_draft_version(self, draft_builder_step):
        """Test getting specific draft version."""
        thread_id = "test_thread"
        content = {"type": "email", "content": "Test content"}
        
        # Create version
        draft_builder_step._create_draft_version(thread_id, content, "tool_results")
        
        # Get specific version
        version = draft_builder_step._get_draft_version(thread_id, 1)
        
        assert version is not None
        assert version["version"] == 1
        assert version["draft_content"] == content
    
    def test_get_draft_version_nonexistent(self, draft_builder_step):
        """Test getting nonexistent draft version."""
        version = draft_builder_step._get_draft_version("nonexistent_thread", 1)
        
        assert version is None
    
    @pytest.mark.asyncio
    async def test_create_draft_from_tools(self, draft_builder_step):
        """Test creating draft from tool results."""
        # Mock the LLM response
        draft_builder_step.llm.acomplete.return_value.text = "Subject: Meeting Update\n\nHi team,\n\nBased on the calendar events, we should schedule our next meeting.\n\nBest regards"
        
        tool_results = {
            "get_calendar_events": {"data": {"events": [{"title": "Team Meeting"}]}}
        }
        draft_context = {"purpose": "create_email", "recipient": "team@company.com"}
        user_id = "test_user"
        
        draft = await draft_builder_step._create_draft_from_tools(tool_results, draft_context, user_id)
        
        assert isinstance(draft, dict)
        assert "type" in draft
        assert "content" in draft
        assert "metadata" in draft
    
    @pytest.mark.asyncio
    async def test_create_draft_from_clarification(self, draft_builder_step):
        """Test creating draft from clarification context."""
        # Mock the LLM response
        draft_builder_step.llm.acomplete.return_value.text = "Subject: Meeting Request\n\nHi team,\n\nI would like to schedule a meeting based on our discussion.\n\nBest regards"
        
        draft_context = {"purpose": "create_email", "recipient": "team@company.com"}
        clarification_insights = {"user_intent": "schedule_meeting", "preferences": {"time": "afternoon"}}
        user_id = "test_user"
        
        draft = await draft_builder_step._create_draft_from_clarification(
            draft_context, clarification_insights, user_id
        )
        
        assert isinstance(draft, dict)
        assert "type" in draft
        assert "content" in draft
        assert "metadata" in draft 