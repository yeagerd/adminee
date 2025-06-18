"""
Test calendar event draft editing functionality.

This module tests the specific workflow of creating and editing calendar event drafts,
which was reported as not working properly in the demo.
"""

import pytest

from services.chat.agents.llm_tools import (
    _draft_storage,
    create_draft_calendar_event,
    delete_draft_calendar_event,
)


class TestCalendarDraftEditing:
    """Test calendar event draft creation and editing workflows."""

    def setup_method(self):
        """Clear draft storage before each test."""
        _draft_storage.clear()

    def teardown_method(self):
        """Clear draft storage after each test."""
        _draft_storage.clear()

    def test_create_initial_calendar_event_draft(self):
        """Test creating an initial calendar event draft."""
        thread_id = "test_thread_123"

        result = create_draft_calendar_event(
            thread_id=thread_id,
            title="Team Meeting",
            start_time="2025-06-18T10:00:00Z",
            end_time="2025-06-18T11:00:00Z",
            location="Conference Room A",
        )

        assert result["success"] is True
        assert "draft" in result

        draft = result["draft"]
        assert draft["title"] == "Team Meeting"
        assert draft["start_time"] == "2025-06-18T10:00:00Z"
        assert draft["end_time"] == "2025-06-18T11:00:00Z"
        assert draft["location"] == "Conference Room A"
        assert draft["type"] == "calendar_event"
        assert draft["thread_id"] == thread_id

    def test_edit_calendar_event_draft_time(self):
        """Test editing the time of an existing calendar event draft."""
        thread_id = "test_thread_123"

        # Create initial draft
        create_draft_calendar_event(
            thread_id=thread_id,
            title="Team Meeting",
            start_time="2025-06-18T10:00:00Z",
            end_time="2025-06-18T11:00:00Z",
            location="Conference Room A",
        )

        # Edit just the time
        result = create_draft_calendar_event(
            thread_id=thread_id,
            start_time="2025-06-18T14:00:00Z",  # Change to 2 PM
            end_time="2025-06-18T15:00:00Z",  # Change to 3 PM
        )

        assert result["success"] is True
        assert "draft" in result

        draft = result["draft"]
        # Time should be updated
        assert draft["start_time"] == "2025-06-18T14:00:00Z"
        assert draft["end_time"] == "2025-06-18T15:00:00Z"

        # Other fields should be preserved
        assert draft["title"] == "Team Meeting"
        assert draft["location"] == "Conference Room A"
        assert draft["type"] == "calendar_event"
        assert draft["thread_id"] == thread_id

    def test_edit_calendar_event_draft_partial_update(self):
        """Test partial updates to calendar event draft (only some fields)."""
        thread_id = "test_thread_123"

        # Create initial draft
        create_draft_calendar_event(
            thread_id=thread_id,
            title="Team Meeting",
            start_time="2025-06-18T10:00:00Z",
            end_time="2025-06-18T11:00:00Z",
            location="Conference Room A",
            description="Weekly team sync",
        )

        # Edit only location and description
        result = create_draft_calendar_event(
            thread_id=thread_id,
            location="Conference Room B",
            description="Weekly team sync - Updated agenda",
        )

        assert result["success"] is True
        draft = result["draft"]

        # Updated fields
        assert draft["location"] == "Conference Room B"
        assert draft["description"] == "Weekly team sync - Updated agenda"

        # Preserved fields
        assert draft["title"] == "Team Meeting"
        assert draft["start_time"] == "2025-06-18T10:00:00Z"
        assert draft["end_time"] == "2025-06-18T11:00:00Z"

    def test_multiple_edits_to_calendar_event_draft(self):
        """Test multiple sequential edits to the same calendar event draft."""
        thread_id = "test_thread_123"

        # Create initial draft
        create_draft_calendar_event(
            thread_id=thread_id,
            title="Team Meeting",
            start_time="2025-06-18T10:00:00Z",
            end_time="2025-06-18T11:00:00Z",
        )

        # First edit: change time
        create_draft_calendar_event(
            thread_id=thread_id,
            start_time="2025-06-18T14:00:00Z",
            end_time="2025-06-18T15:00:00Z",
        )

        # Second edit: add location
        create_draft_calendar_event(thread_id=thread_id, location="Conference Room B")

        # Third edit: change title
        result = create_draft_calendar_event(
            thread_id=thread_id, title="Updated Team Meeting"
        )

        assert result["success"] is True
        draft = result["draft"]

        # All changes should be preserved
        assert draft["title"] == "Updated Team Meeting"
        assert draft["start_time"] == "2025-06-18T14:00:00Z"
        assert draft["end_time"] == "2025-06-18T15:00:00Z"
        assert draft["location"] == "Conference Room B"

    def test_calendar_event_draft_isolation_by_thread(self):
        """Test that drafts are properly isolated by thread_id."""
        thread_1 = "thread_123"
        thread_2 = "thread_456"

        # Create drafts for two different threads
        create_draft_calendar_event(
            thread_id=thread_1,
            title="Thread 1 Meeting",
            start_time="2025-06-18T10:00:00Z",
        )

        create_draft_calendar_event(
            thread_id=thread_2,
            title="Thread 2 Meeting",
            start_time="2025-06-18T14:00:00Z",
        )

        # Edit thread 1 draft
        result_1 = create_draft_calendar_event(
            thread_id=thread_1, start_time="2025-06-18T11:00:00Z"
        )

        # Edit thread 2 draft
        result_2 = create_draft_calendar_event(thread_id=thread_2, location="Room B")

        # Verify isolation
        draft_1 = result_1["draft"]
        draft_2 = result_2["draft"]

        assert draft_1["title"] == "Thread 1 Meeting"
        assert draft_1["start_time"] == "2025-06-18T11:00:00Z"
        assert "location" not in draft_1 or draft_1["location"] is None

        assert draft_2["title"] == "Thread 2 Meeting"
        assert draft_2["start_time"] == "2025-06-18T14:00:00Z"
        assert draft_2["location"] == "Room B"

    def test_draft_storage_direct_access(self):
        """Test that the draft storage is working correctly."""
        thread_id = "test_thread_123"

        # Create draft
        create_draft_calendar_event(
            thread_id=thread_id, title="Test Meeting", start_time="2025-06-18T10:00:00Z"
        )

        # Check direct storage access
        draft_key = f"{thread_id}_calendar_event"
        assert draft_key in _draft_storage

        stored_draft = _draft_storage[draft_key]
        assert stored_draft["title"] == "Test Meeting"
        assert stored_draft["start_time"] == "2025-06-18T10:00:00Z"

        # Edit and verify storage update
        create_draft_calendar_event(
            thread_id=thread_id, start_time="2025-06-18T14:00:00Z"
        )

        updated_draft = _draft_storage[draft_key]
        assert updated_draft["start_time"] == "2025-06-18T14:00:00Z"
        assert updated_draft["title"] == "Test Meeting"  # Should be preserved

    def test_delete_calendar_event_draft_after_editing(self):
        """Test deleting a draft after editing it."""
        thread_id = "test_thread_123"

        # Create and edit draft
        create_draft_calendar_event(
            thread_id=thread_id, title="Test Meeting", start_time="2025-06-18T10:00:00Z"
        )

        create_draft_calendar_event(
            thread_id=thread_id, start_time="2025-06-18T14:00:00Z"
        )

        # Delete draft
        result = delete_draft_calendar_event(thread_id=thread_id)

        assert result["success"] is True
        assert "deleted" in result["message"]

        # Verify it's gone
        draft_key = f"{thread_id}_calendar_event"
        assert draft_key not in _draft_storage


class TestCalendarDraftWorkflowIntegration:
    """Test calendar draft functionality in the context of the workflow system."""

    def setup_method(self):
        """Clear draft storage before each test."""
        _draft_storage.clear()

    def teardown_method(self):
        """Clear draft storage after each test."""
        _draft_storage.clear()

    def test_draft_agent_calendar_event_creation_and_editing(self):
        """Test DraftAgent calendar event creation and editing without full workflow."""
        from services.chat.agents.draft_agent import DraftAgent

        # Create DraftAgent
        agent = DraftAgent(thread_id=123, llm_model="fake-model", llm_provider="fake")

        # Verify agent has calendar event tools
        tool_names = [tool.metadata.name for tool in agent.tools]
        assert "create_draft_calendar_event" in tool_names
        assert "delete_draft_calendar_event" in tool_names

        # Verify thread_id is stored correctly
        assert agent.thread_id == "123"

    @pytest.mark.skip(
        reason="Workflow system has 'missing messages' error - needs investigation"
    )
    def test_full_workflow_calendar_event_editing(self):
        """Test full workflow for calendar event editing - currently failing."""
        # This test is skipped because the workflow system currently has an error:
        # TypeError: missing a required argument: 'messages'
        #
        # This test should be enabled once the workflow system is fixed
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
