"""
Unit tests for DraftBuilderStep workflow step.

Tests the draft generation logic, templating system, versioning,
validation, and completeness checking capabilities.
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
    DraftUpdatedEvent,
    WorkflowMetadata
)


class TestDraftBuilderStep:
    """Test the DraftBuilderStep workflow step."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = Mock(spec=LLM)
        llm.complete = AsyncMock()
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
            tool_results={
                "get_calendar_events": {
                    "success": True,
                    "data": {
                        "events": [
                            {"title": "Team Meeting", "start": "2024-01-15T14:00:00Z"}
                        ],
                        "availability": "Available 2-4pm"
                    }
                },
                "get_emails": {
                    "success": True,
                    "data": {
                        "emails": [
                            {"subject": "Project Update", "from": "john@example.com"}
                        ]
                    }
                }
            },
            draft_context={
                "user_request": "Schedule a meeting with John",
                "intent": "calendar_scheduling",
                "user_preferences": {"timezone": "UTC"}
            },
            metadata=WorkflowMetadata(confidence=0.8, priority="medium")
        )
    
    @pytest.fixture
    def sample_clarification_unblocked_event(self):
        """Create a sample ClarificationDraftUnblockedEvent."""
        return ClarificationDraftUnblockedEvent(
            thread_id="test_thread",
            user_id="test_user",
            draft_context={
                "user_request": "Send email to team",
                "intent": "email_composition",
                "clarification_insights": {"recipients": "team@example.com"}
            },
            clarification_insights={
                "recipients": "team@example.com",
                "subject": "Weekly Update"
            },
            metadata=WorkflowMetadata(confidence=0.9, priority="high")
        )
    
    def test_initialization(self, draft_builder_step):
        """Test DraftBuilderStep initialization."""
        assert draft_builder_step.step_name == "DraftBuilderStep"
        assert hasattr(draft_builder_step, '_draft_templates')
        assert hasattr(draft_builder_step, '_user_style_preferences')
        assert hasattr(draft_builder_step, '_quality_metrics')
        assert hasattr(draft_builder_step, '_draft_versions')
        assert hasattr(draft_builder_step, '_draft_history')
    
    def test_determine_draft_type_email(self, draft_builder_step):
        """Test determining draft type for email."""
        context = {
            "intent": "email_composition",
            "user_request": "Send an email to John"
        }
        tool_results = {}
        
        draft_type = draft_builder_step._determine_draft_type(context, tool_results)
        
        assert draft_type == "email"
    
    def test_determine_draft_type_calendar(self, draft_builder_step):
        """Test determining draft type for calendar event."""
        context = {
            "intent": "calendar_scheduling",
            "user_request": "Schedule a meeting"
        }
        tool_results = {"get_calendar_events": {"data": {"events": []}}}
        
        draft_type = draft_builder_step._determine_draft_type(context, tool_results)
        
        assert draft_type == "calendar_event"
    
    def test_determine_draft_type_document(self, draft_builder_step):
        """Test determining draft type for document."""
        context = {
            "intent": "document_creation",
            "user_request": "Create a report"
        }
        tool_results = {"get_documents": {"data": {"documents": []}}}
        
        draft_type = draft_builder_step._determine_draft_type(context, tool_results)
        
        assert draft_type == "document"
    
    def test_get_draft_template_email(self, draft_builder_step):
        """Test getting email draft template."""
        template = draft_builder_step._get_draft_template("email", "professional")
        
        assert "To:" in template
        assert "Subject:" in template
        assert "Dear" in template
        assert "{recipient}" in template
        assert "{subject}" in template
    
    def test_get_draft_template_calendar(self, draft_builder_step):
        """Test getting calendar event draft template."""
        template = draft_builder_step._get_draft_template("calendar_event", "standard")
        
        assert "Title:" in template
        assert "Date:" in template
        assert "Time:" in template
        assert "{title}" in template
        assert "{date}" in template
    
    def test_get_draft_template_custom(self, draft_builder_step):
        """Test getting custom draft template."""
        # Set up custom template
        draft_builder_step._draft_templates["custom_email"] = {
            "professional": "Custom: {content}"
        }
        
        template = draft_builder_step._get_draft_template("custom_email", "professional")
        
        assert template == "Custom: {content}"
    
    def test_extract_draft_data_from_tools_calendar(self, draft_builder_step):
        """Test extracting draft data from calendar tools."""
        tool_results = {
            "get_calendar_events": {
                "data": {
                    "events": [{"title": "Existing Meeting"}],
                    "availability": "2-4pm available"
                }
            }
        }
        context = {"user_request": "Schedule team meeting"}
        
        data = draft_builder_step._extract_draft_data_from_tools(tool_results, context, "calendar_event")
        
        assert "calendar_info" in data
        assert "availability" in data["calendar_info"]
        assert "2-4pm available" in data["calendar_info"]["availability"]
    
    def test_extract_draft_data_from_tools_email(self, draft_builder_step):
        """Test extracting draft data from email tools."""
        tool_results = {
            "get_emails": {
                "data": {
                    "emails": [{"subject": "Re: Project", "from": "john@example.com"}]
                }
            }
        }
        context = {"user_request": "Reply to John's email"}
        
        data = draft_builder_step._extract_draft_data_from_tools(tool_results, context, "email")
        
        assert "email_context" in data
        assert "recent_emails" in data["email_context"]
        assert len(data["email_context"]["recent_emails"]) == 1
    
    def test_extract_draft_data_from_clarification(self, draft_builder_step):
        """Test extracting draft data from clarification insights."""
        clarification_insights = {
            "recipients": "team@example.com",
            "subject": "Weekly Update",
            "urgency": "high"
        }
        context = {"user_request": "Send email to team"}
        
        data = draft_builder_step._extract_draft_data_from_clarification(clarification_insights, context, "email")
        
        assert "clarification_data" in data
        assert data["clarification_data"]["recipients"] == "team@example.com"
        assert data["clarification_data"]["subject"] == "Weekly Update"
    
    def test_get_user_style_preferences_default(self, draft_builder_step):
        """Test getting default user style preferences."""
        prefs = draft_builder_step._get_user_style_preferences("new_user")
        
        assert prefs["tone"] == "professional"
        assert prefs["formality"] == "standard"
        assert prefs["length"] == "medium"
        assert isinstance(prefs["templates"], dict)
    
    def test_get_user_style_preferences_existing(self, draft_builder_step):
        """Test getting existing user style preferences."""
        # Set up existing preferences
        draft_builder_step._user_style_preferences["existing_user"] = {
            "tone": "casual",
            "formality": "relaxed",
            "length": "brief"
        }
        
        prefs = draft_builder_step._get_user_style_preferences("existing_user")
        
        assert prefs["tone"] == "casual"
        assert prefs["formality"] == "relaxed"
        assert prefs["length"] == "brief"
    
    @pytest.mark.asyncio
    async def test_generate_draft_content_email(self, draft_builder_step):
        """Test generating email draft content."""
        mock_content = {
            "content": "Dear John,\n\nI hope this email finds you well...",
            "subject": "Meeting Request",
            "recipient": "john@example.com"
        }
        
        draft_builder_step.safe_llm_call = AsyncMock(return_value=json.dumps(mock_content))
        
        draft_data = {
            "email_context": {"recent_emails": []},
            "user_request": "Send email to John"
        }
        user_prefs = {"tone": "professional"}
        
        content = await draft_builder_step._generate_draft_content(
            "email", draft_data, user_prefs
        )
        
        assert content["content"] == mock_content["content"]
        assert content["subject"] == mock_content["subject"]
        assert "Dear John" in content["content"]
    
    @pytest.mark.asyncio
    async def test_generate_draft_content_calendar(self, draft_builder_step):
        """Test generating calendar event draft content."""
        mock_content = {
            "title": "Team Meeting",
            "description": "Weekly team sync meeting",
            "date": "2024-01-15",
            "time": "14:00"
        }
        
        draft_builder_step.safe_llm_call = AsyncMock(return_value=json.dumps(mock_content))
        
        draft_data = {
            "calendar_info": {"availability": "2-4pm available"},
            "user_request": "Schedule team meeting"
        }
        user_prefs = {"length": "medium"}
        
        content = await draft_builder_step._generate_draft_content(
            "calendar_event", draft_data, user_prefs
        )
        
        assert content["title"] == mock_content["title"]
        assert content["description"] == mock_content["description"]
        assert "Team Meeting" in content["title"]
    
    def test_calculate_draft_quality_score_high(self, draft_builder_step):
        """Test calculating high quality draft score."""
        draft_content = {
            "type": "email",
            "content": "Dear John,\n\nI hope this message finds you well. I wanted to reach out regarding our upcoming project meeting.",
            "subject": "Project Meeting - Schedule Review",
            "recipient": "john@example.com"
        }
        tool_results = {"get_emails": {"success": True}}
        
        score = draft_builder_step._calculate_draft_quality_score(draft_content, tool_results, {})
        
        assert score >= 0.7  # Should be high quality
    
    def test_calculate_draft_quality_score_low(self, draft_builder_step):
        """Test calculating low quality draft score."""
        draft_content = {
            "type": "email",
            "content": "Hi",
            "subject": "",
            "recipient": ""
        }
        tool_results = {}
        
        score = draft_builder_step._calculate_draft_quality_score(draft_content, tool_results, {})
        
        assert score <= 0.5  # Should be low quality
    
    def test_validate_draft_completeness_complete(self, draft_builder_step):
        """Test validating complete draft."""
        draft_content = {
            "type": "email",
            "content": "Dear John,\n\nThis is a well-formed email with proper structure and content.",
            "subject": "Meeting Request",
            "recipient": "john@example.com"
        }
        tool_results = {"get_emails": {"success": True}}
        
        validation = draft_builder_step._validate_draft_completeness(
            draft_content, tool_results, {}
        )
        
        assert validation["is_complete"] is True
        assert validation["score"] > 0.5
        assert len(validation["issues"]) == 0
    
    def test_validate_draft_completeness_incomplete(self, draft_builder_step):
        """Test validating incomplete draft."""
        draft_content = {
            "type": "email",
            "content": "Hi",
            "subject": "",
            "recipient": ""
        }
        tool_results = {}
        
        validation = draft_builder_step._validate_draft_completeness(
            draft_content, tool_results, {}
        )
        
        assert validation["is_complete"] is False
        assert validation["score"] < 0.5
        assert len(validation["issues"]) > 0
    
    def test_create_draft_version_new(self, draft_builder_step):
        """Test creating new draft version."""
        thread_id = "test_thread"
        draft_content = {
            "type": "email",
            "content": "Test email content",
            "subject": "Test Subject"
        }
        
        version = draft_builder_step._create_draft_version(thread_id, draft_content)
        
        assert version["version_number"] == 1
        assert version["thread_id"] == thread_id
        assert version["content"] == draft_content
        assert "created_at" in version
        assert "version_id" in version
    
    def test_create_draft_version_update(self, draft_builder_step):
        """Test creating updated draft version."""
        thread_id = "test_thread"
        
        # Create initial version
        initial_content = {"type": "email", "content": "Initial content"}
        draft_builder_step._create_draft_version(thread_id, initial_content)
        
        # Create updated version
        updated_content = {"type": "email", "content": "Updated content"}
        version = draft_builder_step._create_draft_version(thread_id, updated_content)
        
        assert version["version_number"] == 2
        assert version["content"] == updated_content
    
    def test_get_draft_history(self, draft_builder_step):
        """Test getting draft history."""
        thread_id = "test_thread"
        
        # Create multiple versions
        content1 = {"type": "email", "content": "Version 1"}
        content2 = {"type": "email", "content": "Version 2"}
        
        draft_builder_step._create_draft_version(thread_id, content1)
        draft_builder_step._create_draft_version(thread_id, content2)
        
        history = draft_builder_step._get_draft_history(thread_id)
        
        assert len(history) == 2
        assert history[0]["version_number"] == 1
        assert history[1]["version_number"] == 2
    
    def test_get_latest_draft_version(self, draft_builder_step):
        """Test getting latest draft version."""
        thread_id = "test_thread"
        
        # Create multiple versions
        content1 = {"type": "email", "content": "Version 1"}
        content2 = {"type": "email", "content": "Version 2"}
        
        draft_builder_step._create_draft_version(thread_id, content1)
        draft_builder_step._create_draft_version(thread_id, content2)
        
        latest = draft_builder_step._get_latest_draft_version(thread_id)
        
        assert latest["version_number"] == 2
        assert latest["content"]["content"] == "Version 2"
    
    def test_get_latest_draft_version_none(self, draft_builder_step):
        """Test getting latest draft version when none exists."""
        latest = draft_builder_step._get_latest_draft_version("nonexistent_thread")
        
        assert latest is None
    
    def test_update_quality_metrics(self, draft_builder_step):
        """Test updating quality metrics."""
        user_id = "test_user"
        draft_type = "email"
        quality_score = 0.85
        
        draft_builder_step._update_quality_metrics(user_id, draft_type, quality_score)
        
        metrics = draft_builder_step._quality_metrics[user_id][draft_type]
        assert metrics["total_drafts"] == 1
        assert metrics["total_score"] == quality_score
        assert metrics["average_score"] == quality_score
    
    def test_learn_user_style_preferences(self, draft_builder_step):
        """Test learning user style preferences."""
        user_id = "test_user"
        draft_content = {
            "content": "Hey there! Hope you're doing well. Quick question about the project...",
            "type": "email"
        }
        
        draft_builder_step._learn_user_style_preferences(user_id, draft_content)
        
        prefs = draft_builder_step._user_style_preferences[user_id]
        assert prefs["tone"] == "casual"  # Should detect casual tone
        assert prefs["formality"] == "relaxed"  # Should detect informal style 