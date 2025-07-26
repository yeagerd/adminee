from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from services.office.schemas import (
    AvailabilityRequest,
    CreateCalendarEventRequest,
    EmailAddress,
)


class TestCreateCalendarEventRequestValidation:
    """Test business logic validation for calendar event creation."""

    def test_valid_event_request(self):
        """Test that a valid event request passes validation."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=1)

        request = CreateCalendarEventRequest(
            title="Test Meeting",
            start_time=start_time,
            end_time=end_time,
        )

        assert request.title == "Test Meeting"
        assert request.start_time == start_time
        assert request.end_time == end_time

    def test_end_time_before_start_time_fails(self):
        """Test that end_time before start_time raises validation error."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time - timedelta(hours=1)  # End before start

        with pytest.raises(ValidationError) as exc_info:
            CreateCalendarEventRequest(
                title="Test Meeting",
                start_time=start_time,
                end_time=end_time,
            )

        assert "end_time must be after start_time" in str(exc_info.value)

    def test_end_time_equal_to_start_time_fails(self):
        """Test that end_time equal to start_time raises validation error."""
        start_time = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            CreateCalendarEventRequest(
                title="Test Meeting",
                start_time=start_time,
                end_time=start_time,  # Same as start
            )

        assert "end_time must be after start_time" in str(exc_info.value)

    def test_empty_title_fails(self):
        """Test that empty title raises validation error."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=1)

        with pytest.raises(ValidationError) as exc_info:
            CreateCalendarEventRequest(
                title="",  # Empty title
                start_time=start_time,
                end_time=end_time,
            )

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_whitespace_only_title_fails(self):
        """Test that whitespace-only title raises validation error."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=1)

        with pytest.raises(ValidationError) as exc_info:
            CreateCalendarEventRequest(
                title="   ",  # Only whitespace
                start_time=start_time,
                end_time=end_time,
            )

        assert "title cannot be empty" in str(exc_info.value)

    def test_title_gets_stripped(self):
        """Test that title gets stripped of leading/trailing whitespace."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=1)

        request = CreateCalendarEventRequest(
            title="  Test Meeting  ",  # With whitespace
            start_time=start_time,
            end_time=end_time,
        )

        assert request.title == "Test Meeting"  # Should be stripped

    def test_invalid_visibility_fails(self):
        """Test that invalid visibility raises validation error."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=1)

        with pytest.raises(ValidationError) as exc_info:
            CreateCalendarEventRequest(
                title="Test Meeting",
                start_time=start_time,
                end_time=end_time,
                visibility="invalid",  # Invalid visibility
            )

        assert "visibility must be one of: default, public, private" in str(
            exc_info.value
        )

    def test_invalid_status_fails(self):
        """Test that invalid status raises validation error."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=1)

        with pytest.raises(ValidationError) as exc_info:
            CreateCalendarEventRequest(
                title="Test Meeting",
                start_time=start_time,
                end_time=end_time,
                status="invalid",  # Invalid status
            )

        assert "status must be one of: confirmed, tentative, cancelled" in str(
            exc_info.value
        )

    def test_invalid_provider_fails(self):
        """Test that invalid provider raises validation error."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=1)

        with pytest.raises(ValidationError) as exc_info:
            CreateCalendarEventRequest(
                title="Test Meeting",
                start_time=start_time,
                end_time=end_time,
                provider="invalid",  # Invalid provider
            )

        assert "provider must be one of: google, microsoft" in str(exc_info.value)

    def test_provider_gets_lowercased(self):
        """Test that provider gets converted to lowercase."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=1)

        request = CreateCalendarEventRequest(
            title="Test Meeting",
            start_time=start_time,
            end_time=end_time,
            provider="GOOGLE",  # Uppercase
        )

        assert request.provider == "google"  # Should be lowercase


class TestAvailabilityRequestValidation:
    """Test business logic validation for availability requests."""

    def test_valid_availability_request(self):
        """Test that a valid availability request passes validation."""
        start = "2024-01-01T09:00:00"
        end = "2024-01-01T17:00:00"

        request = AvailabilityRequest(
            start=start,
            end=end,
            duration=60,
        )

        assert request.start == start
        assert request.end == end
        assert request.duration == 60

    def test_invalid_datetime_format_fails(self):
        """Test that invalid datetime format raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AvailabilityRequest(
                start="invalid-date",
                end="2024-01-01T17:00:00",
                duration=60,
            )

        assert "datetime must be in ISO format" in str(exc_info.value)

    def test_end_before_start_fails(self):
        """Test that end time before start time raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AvailabilityRequest(
                start="2024-01-01T17:00:00",
                end="2024-01-01T09:00:00",  # Before start
                duration=60,
            )

        assert "end time must be after start time" in str(exc_info.value)

    def test_end_equal_to_start_fails(self):
        """Test that end time equal to start time raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AvailabilityRequest(
                start="2024-01-01T09:00:00",
                end="2024-01-01T09:00:00",  # Same as start
                duration=60,
            )

        assert "end time must be after start time" in str(exc_info.value)

    def test_duration_too_short_fails(self):
        """Test that duration less than 1 minute fails."""
        with pytest.raises(ValidationError) as exc_info:
            AvailabilityRequest(
                start="2024-01-01T09:00:00",
                end="2024-01-01T17:00:00",
                duration=0,  # Too short
            )

        assert "greater than or equal to 1" in str(exc_info.value)

    def test_duration_too_long_fails(self):
        """Test that duration more than 24 hours fails."""
        with pytest.raises(ValidationError) as exc_info:
            AvailabilityRequest(
                start="2024-01-01T09:00:00",
                end="2024-01-01T17:00:00",
                duration=1441,  # More than 24 hours
            )

        assert "less than or equal to 1440" in str(exc_info.value)

    def test_invalid_provider_fails(self):
        """Test that invalid provider raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AvailabilityRequest(
                start="2024-01-01T09:00:00",
                end="2024-01-01T17:00:00",
                duration=60,
                providers=["invalid"],  # Invalid provider
            )

        assert "provider must be one of: google, microsoft" in str(exc_info.value)

    def test_providers_get_lowercased(self):
        """Test that providers get converted to lowercase."""
        request = AvailabilityRequest(
            start="2024-01-01T09:00:00",
            end="2024-01-01T17:00:00",
            duration=60,
            providers=["GOOGLE", "MICROSOFT"],  # Uppercase
        )

        assert request.providers == ["google", "microsoft"]  # Should be lowercase


class TestEmailAddressValidation:
    """Test business logic validation for email addresses."""

    def test_valid_email_address(self):
        """Test that a valid email address passes validation."""
        email = EmailAddress(
            email="test@example.com",
            name="Test User",
        )

        assert email.email == "test@example.com"
        assert email.name == "Test User"

    def test_empty_name_gets_converted_to_none(self):
        """Test that empty name gets converted to None."""
        email = EmailAddress(
            email="test@example.com",
            name="",  # Empty string
        )

        assert email.name is None

    def test_whitespace_only_name_gets_converted_to_none(self):
        """Test that whitespace-only name gets converted to None."""
        email = EmailAddress(
            email="test@example.com",
            name="   ",  # Only whitespace
        )

        assert email.name is None

    def test_name_gets_stripped(self):
        """Test that name gets stripped of leading/trailing whitespace."""
        email = EmailAddress(
            email="test@example.com",
            name="  Test User  ",  # With whitespace
        )

        assert email.name == "Test User"  # Should be stripped
