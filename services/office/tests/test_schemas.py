"""
Unit tests for Pydantic schemas and data models.

Tests schema validation, serialization, deserialization,
and data transformation for office service models.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from services.office.models import Provider
from services.api.v1.office.email import (
    ApiError,
    ApiResponse,
    CalendarEvent,
    DriveFile,
    EmailAddress,
    EmailMessage,
    PaginatedResponse,
)


@pytest.fixture(autouse=True)
def patch_settings():
    """Patch the _settings global variable to return test settings."""
    import services.office.core.settings as office_settings

    test_settings = office_settings.Settings(
        db_url_office="sqlite:///:memory:",
        api_frontend_office_key="test-frontend-office-key",
        api_chat_office_key="test-chat-office-key",
        api_meetings_office_key="test-meetings-office-key",
        api_backfill_office_key="test-backfill-office-key",
        api_office_user_key="test-office-user-key",
        pagination_secret_key="test-pagination-secret-key",
    )

    # Directly set the singleton instead of using monkeypatch
    office_settings._settings = test_settings
    yield
    office_settings._settings = None


class TestEmailAddress:
    """Tests for EmailAddress model."""

    def test_valid_email_address_creation(self):
        """Test creating a valid EmailAddress."""
        email = EmailAddress(email="test@example.com", name="Test User")
        assert email.email == "test@example.com"
        assert email.name == "Test User"

    def test_email_address_without_name(self):
        """Test creating EmailAddress without name (optional field)."""
        email = EmailAddress(email="test@example.com")
        assert email.email == "test@example.com"
        assert email.name is None

    def test_invalid_email_format(self):
        """Test EmailAddress with invalid email format."""
        with pytest.raises(ValidationError) as exc_info:
            EmailAddress(email="invalid-email", name="Test User")

        assert "value is not a valid email address" in str(exc_info.value)

    def test_email_address_serialization(self):
        """Test EmailAddress serialization to dict."""
        email = EmailAddress(email="test@example.com", name="Test User")
        data = email.model_dump()

        assert data == {"email": "test@example.com", "name": "Test User"}


class TestEmailMessage:
    """Tests for EmailMessage model."""

    def test_valid_email_message_creation(self):
        """Test creating a valid EmailMessage."""
        from_addr = EmailAddress(email="sender@example.com", name="Sender")
        to_addr = EmailAddress(email="recipient@example.com", name="Recipient")

        message = EmailMessage(
            id="msg_123",
            subject="Test Subject",
            body_text="Test body",
            from_address=from_addr,
            to_addresses=[to_addr],
            date=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            provider=Provider.GOOGLE,
            provider_message_id="gmail_123",
            account_email="account@example.com",
        )

        assert message.id == "msg_123"
        assert message.subject == "Test Subject"
        assert message.from_address.email == "sender@example.com"
        assert len(message.to_addresses) == 1
        assert message.provider == Provider.GOOGLE

    def test_email_message_optional_fields(self):
        """Test EmailMessage with only required fields."""
        message = EmailMessage(
            id="msg_123",
            date=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            provider=Provider.MICROSOFT,
            provider_message_id="outlook_123",
            account_email="account@example.com",
        )

        assert message.id == "msg_123"
        assert message.thread_id is None
        assert message.subject is None
        assert message.to_addresses == []
        assert message.is_read is False
        assert message.has_attachments is False

    def test_email_message_with_all_fields(self):
        """Test EmailMessage with all optional fields populated."""
        from_addr = EmailAddress(email="sender@example.com")
        to_addr = EmailAddress(email="to@example.com")
        cc_addr = EmailAddress(email="cc@example.com")
        bcc_addr = EmailAddress(email="bcc@example.com")

        message = EmailMessage(
            id="msg_123",
            thread_id="thread_456",
            subject="Test Subject",
            snippet="Test snippet",
            body_text="Test body text",
            body_html="<p>Test body HTML</p>",
            from_address=from_addr,
            to_addresses=[to_addr],
            cc_addresses=[cc_addr],
            bcc_addresses=[bcc_addr],
            date=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            labels=["INBOX", "IMPORTANT"],
            is_read=True,
            has_attachments=True,
            provider=Provider.GOOGLE,
            provider_message_id="gmail_123",
            account_email="account@example.com",
            account_name="Test Account",
        )

        assert message.thread_id == "thread_456"
        assert len(message.labels) == 2
        assert message.is_read is True
        assert message.has_attachments is True
        assert message.account_name == "Test Account"


class TestCalendarEvent:
    """Tests for CalendarEvent model."""

    def test_valid_calendar_event_creation(self):
        """Test creating a valid CalendarEvent."""
        organizer = EmailAddress(email="organizer@example.com", name="Organizer")
        attendee = EmailAddress(email="attendee@example.com", name="Attendee")

        event = CalendarEvent(
            id="event_123",
            calendar_id="cal_456",
            title="Team Meeting",
            start_time=datetime(2023, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2023, 6, 15, 11, 0, 0, tzinfo=timezone.utc),
            organizer=organizer,
            attendees=[attendee],
            provider=Provider.GOOGLE,
            provider_event_id="gcal_123",
            account_email="account@example.com",
            calendar_name="Work Calendar",
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        )

        assert event.id == "event_123"
        assert event.title == "Team Meeting"
        assert event.all_day is False
        assert event.status == "confirmed"
        assert event.visibility == "default"
        assert len(event.attendees) == 1

    def test_calendar_event_all_day(self):
        """Test creating an all-day calendar event."""
        event = CalendarEvent(
            id="event_123",
            calendar_id="cal_456",
            title="All Day Event",
            start_time=datetime(2023, 6, 15, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2023, 6, 15, 23, 59, 59, tzinfo=timezone.utc),
            all_day=True,
            provider=Provider.MICROSOFT,
            provider_event_id="outlook_123",
            account_email="account@example.com",
            calendar_name="Personal Calendar",
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        )

        assert event.all_day is True
        assert event.provider == Provider.MICROSOFT


class TestDriveFile:
    """Tests for DriveFile model."""

    def test_valid_drive_file_creation(self):
        """Test creating a valid DriveFile."""
        file = DriveFile(
            id="file_123",
            name="document.pdf",
            mime_type="application/pdf",
            size=1024,
            created_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
            modified_time=datetime(2023, 1, 2, tzinfo=timezone.utc),
            web_view_link="https://drive.google.com/file/123",
            provider=Provider.GOOGLE,
            provider_file_id="gdrive_123",
            account_email="account@example.com",
        )

        assert file.id == "file_123"
        assert file.name == "document.pdf"
        assert file.mime_type == "application/pdf"
        assert file.size == 1024
        assert file.is_folder is False

    def test_drive_folder_creation(self):
        """Test creating a DriveFile representing a folder."""
        folder = DriveFile(
            id="folder_123",
            name="My Folder",
            mime_type="application/vnd.google-apps.folder",
            created_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
            modified_time=datetime(2023, 1, 2, tzinfo=timezone.utc),
            is_folder=True,
            provider=Provider.GOOGLE,
            provider_file_id="gdrive_folder_123",
            account_email="account@example.com",
        )

        assert folder.is_folder is True
        assert folder.size is None


class TestApiResponse:
    """Tests for ApiResponse model."""

    def test_successful_api_response(self):
        """Test creating a successful API response."""
        response = ApiResponse(
            success=True,
            data={"items": [1, 2, 3]},
            cache_hit=True,
            provider_used=Provider.GOOGLE,
            request_id="req_123",
        )

        assert response.success is True
        assert response.data == {"items": [1, 2, 3]}
        assert response.cache_hit is True
        assert response.provider_used == Provider.GOOGLE
        assert response.error is None

    def test_error_api_response(self):
        """Test creating an error API response."""
        error_details = {"code": "RATE_LIMITED", "message": "Too many requests"}

        response = ApiResponse(
            success=False,
            error=error_details,
            request_id="req_123",
        )

        assert response.success is False
        assert response.error == error_details
        assert response.data is None
        assert response.cache_hit is False


class TestPaginatedResponse:
    """Tests for PaginatedResponse model."""

    def test_paginated_response_creation(self):
        """Test creating a PaginatedResponse."""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]

        response = PaginatedResponse(
            items=items,
            total_count=100,
            next_page_token="next_page_123",
            has_more=True,
        )

        assert len(response.items) == 3
        assert response.total_count == 100
        assert response.next_page_token == "next_page_123"
        assert response.has_more is True

    def test_paginated_response_minimal(self):
        """Test creating a minimal PaginatedResponse."""
        response = PaginatedResponse(items=[])

        assert response.items == []
        assert response.total_count is None
        assert response.next_page_token is None
        assert response.has_more is False


class TestApiError:
    """Tests for ApiError model."""

    def test_api_error_creation(self):
        """Test creating an ApiError."""
        error = ApiError(
            type="validation_error",
            message="Invalid input data",
            details={"field": "email", "issue": "Invalid format"},
            provider=Provider.GOOGLE,
            retry_after=60,
            request_id="req_123",
        )

        assert error.type == "validation_error"
        assert error.message == "Invalid input data"
        assert error.details["field"] == "email"
        assert error.provider == Provider.GOOGLE
        assert error.retry_after == 60

    def test_api_error_minimal(self):
        """Test creating minimal ApiError."""
        error = ApiError(
            type="server_error",
            message="Internal server error",
            request_id="req_123",
        )

        assert error.type == "server_error"
        assert error.message == "Internal server error"
        assert error.details is None
        assert error.provider is None
        assert error.retry_after is None


class TestModelSerialization:
    """Tests for model serialization and deserialization."""

    def test_email_message_round_trip(self):
        """Test EmailMessage serialization and deserialization."""
        original = EmailMessage(
            id="msg_123",
            subject="Test",
            date=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            provider=Provider.GOOGLE,
            provider_message_id="gmail_123",
            account_email="account@example.com",
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize back to object
        restored = EmailMessage(**data)

        assert restored.id == original.id
        assert restored.subject == original.subject
        assert restored.date == original.date
        assert restored.provider == original.provider

    def test_calendar_event_json_serialization(self):
        """Test CalendarEvent JSON serialization."""
        event = CalendarEvent(
            id="event_123",
            calendar_id="cal_456",
            title="Meeting",
            start_time=datetime(2023, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2023, 6, 15, 11, 0, 0, tzinfo=timezone.utc),
            provider=Provider.GOOGLE,
            provider_event_id="gcal_123",
            account_email="account@example.com",
            calendar_name="Work Calendar",
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
        )

        # Test JSON serialization
        json_str = event.model_dump_json()
        assert "event_123" in json_str
        assert "Meeting" in json_str
        assert "google" in json_str
