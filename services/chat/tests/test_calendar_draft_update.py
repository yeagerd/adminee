"""
Test calendar event draft update functionality.

This test verifies that calendar event drafts can be properly updated
using the create_draft_calendar_event function, which should be used
for both creating and updating drafts.
"""


from services.chat.agents.llm_tools import (
    _draft_storage,
    create_draft_calendar_event,
)


class TestCalendarDraftUpdate:
    """Test calendar event draft update workflows."""

    def setup_method(self):
        """Clear draft storage before each test."""
        _draft_storage.clear()

    def teardown_method(self):
        """Clear draft storage after each test."""
        _draft_storage.clear()

    def test_create_then_update_calendar_event_draft(self):
        """Test creating a calendar event draft and then updating its time."""
        thread_id = "1150"

        # Step 1: Create initial draft
        result1 = create_draft_calendar_event(
            thread_id=thread_id,
            title="Breakfast with Laura",
            start_time="2023-10-05T08:00:00",
            end_time="2023-10-05T09:00:00",
            attendees="laura@gmail.com",
            location="Pete's coffee",
            description="Breakfast with Laura at Pete's coffee.",
        )

        assert result1["success"] is True
        assert result1["draft"]["title"] == "Breakfast with Laura"
        assert result1["draft"]["start_time"] == "2023-10-05T08:00:00"

        # Verify draft is stored
        draft_key = f"{thread_id}_calendar_event"
        assert draft_key in _draft_storage
        assert _draft_storage[draft_key]["start_time"] == "2023-10-05T08:00:00"

        # Step 2: Update the start time to 9am (this should update the existing draft)
        result2 = create_draft_calendar_event(
            thread_id=thread_id, start_time="2023-10-05T09:00:00"  # Change to 9am
        )

        assert result2["success"] is True
        assert (
            result2["draft"]["title"] == "Breakfast with Laura"
        )  # Should keep existing title
        assert (
            result2["draft"]["start_time"] == "2023-10-05T09:00:00"
        )  # Should update time
        assert (
            result2["draft"]["attendees"] == "laura@gmail.com"
        )  # Should keep existing attendees
        assert (
            result2["draft"]["location"] == "Pete's coffee"
        )  # Should keep existing location

        # Verify only ONE draft exists (the updated one)
        assert len([k for k in _draft_storage.keys() if k.startswith(thread_id)]) == 1
        assert _draft_storage[draft_key]["start_time"] == "2023-10-05T09:00:00"

        # Step 3: Update multiple fields at once
        result3 = create_draft_calendar_event(
            thread_id=thread_id,
            start_time="2023-10-05T10:00:00",  # Change to 10am
            location="Starbucks on Main St",  # Change location
        )

        assert result3["success"] is True
        assert result3["draft"]["start_time"] == "2023-10-05T10:00:00"
        assert result3["draft"]["location"] == "Starbucks on Main St"
        assert (
            result3["draft"]["title"] == "Breakfast with Laura"
        )  # Should keep existing title
        assert (
            result3["draft"]["attendees"] == "laura@gmail.com"
        )  # Should keep existing attendees

        # Still only one draft
        assert len([k for k in _draft_storage.keys() if k.startswith(thread_id)]) == 1

    def test_partial_update_preserves_existing_fields(self):
        """Test that partial updates preserve existing field values."""
        thread_id = "test_partial"

        # Create full draft
        create_draft_calendar_event(
            thread_id=thread_id,
            title="Team Meeting",
            start_time="2023-10-05T14:00:00",
            end_time="2023-10-05T15:00:00",
            attendees="team@company.com",
            location="Conference Room A",
            description="Weekly team sync",
        )

        # Update only the time
        result = create_draft_calendar_event(
            thread_id=thread_id,
            start_time="2023-10-05T15:00:00",  # Only change start time
            end_time="2023-10-05T16:00:00",  # Only change end time
        )

        # All other fields should be preserved
        draft = result["draft"]
        assert draft["title"] == "Team Meeting"
        assert draft["attendees"] == "team@company.com"
        assert draft["location"] == "Conference Room A"
        assert draft["description"] == "Weekly team sync"

        # New times should be applied
        assert draft["start_time"] == "2023-10-05T15:00:00"
        assert draft["end_time"] == "2023-10-05T16:00:00"
