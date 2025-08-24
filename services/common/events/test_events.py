"""
Test file for the events module to verify the structure works correctly.
"""

from datetime import datetime, timezone

from services.common.events import (
    CalendarEvent,
    CalendarEventData,
    ContactData,
    ContactEvent,
    EmailData,
    EmailEvent,
    EventMetadata,
)


def test_email_event_creation():
    """Test creating an EmailEvent with proper metadata."""
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

    # Create email event
    event = EmailEvent(
        user_id="user_789",
        email=email_data,
        operation="create",
        batch_id="batch_123",
        last_updated=datetime.now(timezone.utc),
        sync_timestamp=datetime.now(timezone.utc),
        provider="gmail",
        sync_type="backfill",
        metadata=EventMetadata(
            source_service="office-service",
            source_version="1.0.0",
            correlation_id="email_job_123",
        ),
    )

    assert event.user_id == "user_789"
    assert event.provider == "gmail"
    assert event.email.subject == "Test Email"
    assert event.operation == "create"
    assert event.batch_id == "batch_123"
    assert event.metadata.source_service == "office-service"
    assert event.metadata.correlation_id == "email_job_123"


def test_calendar_event_creation():
    """Test creating a CalendarEvent."""
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

    event = CalendarEvent(
        user_id="user_789",
        event=calendar_data,
        operation="create",
        batch_id="batch_123",
        last_updated=datetime.now(timezone.utc),
        sync_timestamp=datetime.now(timezone.utc),
        provider="google",
        calendar_id="calendar_456",
        metadata=EventMetadata(
            source_service="office-service",
            source_version="1.0.0",
        ),
    )

    assert event.user_id == "user_789"
    assert event.event.title == "Test Meeting"
    assert event.operation == "create"
    assert event.batch_id == "batch_123"
    assert event.metadata.source_service == "office-service"


def test_contact_event_creation():
    """Test creating a ContactEvent."""
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

    event = ContactEvent(
        user_id="user_789",
        contact=contact_data,
        operation="create",
        batch_id="batch_123",
        last_updated=datetime.now(timezone.utc),
        sync_timestamp=datetime.now(timezone.utc),
        provider="google",
        metadata=EventMetadata(
            source_service="office-service",
            source_version="1.0.0",
        ),
    )

    assert event.user_id == "user_789"
    assert event.contact.display_name == "John Doe"
    assert event.operation == "create"
    assert event.batch_id == "batch_123"
    assert event.metadata.source_service == "office-service"


def test_event_metadata_tracing():
    """Test that events can have tracing context added."""
    event = EmailEvent(
        user_id="user_123",
        email=EmailData(
            id="email_123",
            thread_id="thread_456",
            subject="Test Email",
            body="Test body",
            from_address="test@example.com",
            to_addresses=["recipient@example.com"],
            received_date=datetime.now(timezone.utc),
            provider="gmail",
            provider_message_id="gmail_123",
        ),
        operation="create",
        batch_id="batch_123",
        last_updated=datetime.now(timezone.utc),
        sync_timestamp=datetime.now(timezone.utc),
        provider="gmail",
        sync_type="sync",
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
    test_email_event_creation()
    test_calendar_event_creation()
    test_contact_event_creation()
    test_event_metadata_tracing()
    print("All tests passed!")
