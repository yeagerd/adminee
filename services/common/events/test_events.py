"""
Test file for the events module to verify the structure works correctly.
"""

from datetime import datetime, timezone

from services.common.events import (
    CalendarEventData,
    CalendarUpdateEvent,
    ContactData,
    ContactUpdateEvent,
    EmailBackfillEvent,
    EmailData,
    EventMetadata,
)


def test_email_backfill_event_creation():
    """Test creating an EmailBackfillEvent with proper metadata."""
    # Create email data
    email_data = EmailData(
        id="email_123",
        thread_id="thread_456",
        subject="Test Email",
        body="This is a test email body",
        from_address="sender@example.com",
        to_addresses=["recipient@example.com"],
        cc_addresses=[],
        bcc_addresses=[],
        received_date=datetime.now(timezone.utc),
        sent_date=None,
        labels=["INBOX"],
        is_read=False,
        is_starred=False,
        has_attachments=False,
        provider="gmail",
        provider_message_id="gmail_123",
    )

    # Create backfill event
    event = EmailBackfillEvent(
        user_id="user_789",
        provider="gmail",
        emails=[email_data],
        batch_size=1,
        sync_type="backfill",
        metadata=EventMetadata(
            source_service="office-service",
            source_version="1.0.0",
            correlation_id="backfill_job_123",
        ),
    )

    assert event.user_id == "user_789"
    assert event.provider == "gmail"
    assert len(event.emails) == 1
    assert event.emails[0].subject == "Test Email"
    assert event.metadata.source_service == "office-service"
    assert event.metadata.correlation_id == "backfill_job_123"


def test_calendar_update_event_creation():
    """Test creating a CalendarUpdateEvent."""
    calendar_data = CalendarEventData(
        id="event_123",
        title="Test Meeting",
        description="A test meeting",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        all_day=False,
        location="Conference Room A",
        organizer="organizer@example.com",
        attendees=["attendee@example.com"],
        status="confirmed",
        visibility="default",
        provider="google",
        provider_event_id="google_123",
        calendar_id="calendar_456",
    )

    event = CalendarUpdateEvent(
        user_id="user_789",
        event=calendar_data,
        update_type="create",
        metadata=EventMetadata(
            source_service="office-service",
            source_version="1.0.0",
        ),
    )

    assert event.user_id == "user_789"
    assert event.event.title == "Test Meeting"
    assert event.update_type == "create"
    assert event.metadata.source_service == "office-service"


def test_contact_update_event_creation():
    """Test creating a ContactUpdateEvent."""
    contact_data = ContactData(
        id="contact_123",
        display_name="John Doe",
        given_name="John",
        family_name="Doe",
        email_addresses=["john.doe@example.com"],
        phone_numbers=[],
        addresses=[],
        organizations=[],
        birthdays=[],
        notes="Test contact",
        provider="google",
        provider_contact_id="google_123",
    )

    event = ContactUpdateEvent(
        user_id="user_789",
        contact=contact_data,
        update_type="create",
        metadata=EventMetadata(
            source_service="office-service",
            source_version="1.0.0",
        ),
    )

    assert event.user_id == "user_789"
    assert event.contact.display_name == "John Doe"
    assert event.update_type == "create"
    assert event.metadata.source_service == "office-service"


def test_event_metadata_tracing():
    """Test that events can have tracing context added."""
    event = EmailBackfillEvent(
        user_id="user_123",
        provider="gmail",
        emails=[],
        batch_size=0,
        metadata=EventMetadata(
            source_service="office-service",
            source_version="1.0.0",
        ),
    )

    # Add tracing context
    event.add_trace_context("trace_123", "span_456", "parent_789")
    event.add_request_context("request_123", "user_456")
    event.add_correlation_id("correlation_123")
    event.add_tags(environment="test", priority="high")

    assert event.metadata.trace_id == "trace_123"
    assert event.metadata.span_id == "span_456"
    assert event.metadata.parent_span_id == "parent_789"
    assert event.metadata.request_id == "request_123"
    assert event.metadata.user_id == "user_456"
    assert event.metadata.correlation_id == "correlation_123"
    assert event.metadata.tags["environment"] == "test"
    assert event.metadata.tags["priority"] == "high"


if __name__ == "__main__":
    # Run tests
    test_email_backfill_event_creation()
    test_calendar_update_event_creation()
    test_contact_update_event_creation()
    test_event_metadata_tracing()
    print("All tests passed!")
