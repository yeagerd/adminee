"""Unit tests for chat service events."""

import pytest
from pydantic import ValidationError
from services.chat.events import (
    WorkflowMetadata,
    UserInputEvent,
    ContextUpdatedEvent,
    DraftCreatedEvent,
    ToolExecutionRequestedEvent
)

class TestWorkflowMetadata:
    def test_create_default(self):
        metadata = WorkflowMetadata()
        assert metadata.confidence is None
        assert metadata.retry_count == 0

class TestUserInputEvent:
    def test_create_valid_event(self):
        event = UserInputEvent(
            thread_id="thread123",
            user_id="user456", 
            message="Test message"
        )
        assert event.thread_id == "thread123"
        assert event.message == "Test message"

class TestContextUpdatedEvent:
    def test_create_valid_event(self):
        event = ContextUpdatedEvent(
            thread_id="thread123",
            user_id="user456",
            context_updates={"key": "value"},
            update_source="test",
            update_type="merge"
        )
        assert event.update_type == "merge"
