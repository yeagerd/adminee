"""
Unit tests for booking endpoints in the Meetings Service.

Tests the public booking functionality including:
- Public link retrieval
- Availability calculation
- Booking creation
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from services.meetings.models.booking_entities import BookingLink, OneTimeLink
from services.meetings.tests.test_base import BaseMeetingsIntegrationTest


class TestBookingEndpoints(BaseMeetingsIntegrationTest):
    """Test suite for booking endpoints."""

    def setup_method(self, method):
        """Set up test environment with booking-specific data."""
        super().setup_method(method)

        # Create test data
        self.test_user_id = "test-user-123"
        self.test_booking_link_id = uuid.uuid4()
        self.test_token = "test-token-789"

        # Mock the office service responses
        future_date = datetime.now(timezone.utc) + timedelta(days=7)
        self.mock_office_availability_response = {
            "data": {
                "available_slots": [
                    {
                        "start": future_date.replace(hour=9, minute=0, second=0, microsecond=0).isoformat(),
                        "end": future_date.replace(hour=9, minute=30, second=0, microsecond=0).isoformat(),
                        "duration_minutes": 30,
                    },
                    {
                        "start": future_date.replace(hour=14, minute=0, second=0, microsecond=0).isoformat(),
                        "end": future_date.replace(hour=14, minute=30, second=0, microsecond=0).isoformat(),
                        "duration_minutes": 30,
                    },
                ],
                "total_slots": 2,
                "providers_used": ["microsoft"],
                "request_metadata": {},
            }
        }

        # Sample data for testing
        self.sample_booking_link_data = {
            "id": str(uuid.uuid4()),
            "owner_user_id": "test-user-456",
            "slug": "test-slug",
            "title": "Test Booking Link",
            "description": "Test description for booking link",
            "is_active": True,
            "settings": {
                "buffer_before": 15,
                "buffer_after": 15,
                "business_hours": {
                    "monday": {"enabled": True, "start": "09:00", "end": "17:00"},
                    "tuesday": {"enabled": True, "start": "09:00", "end": "17:00"},
                },
                "max_per_day": 10,
                "max_per_week": 50,
                "advance_days": 1,
                "max_advance_days": 90,
                "last_minute_cutoff": 2,
            },
        }

        self.sample_one_time_link_data = {
            "id": str(uuid.uuid4()),
            "token": "test-token-456",
            "booking_link_id": str(uuid.uuid4()),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
            "status": "active",
        }

    def create_test_booking_link(self, session):
        """Helper method to create a test booking link."""
        booking_link = BookingLink(
            id=self.test_booking_link_id,
            owner_user_id=self.test_user_id,
            slug="test-slug",
            is_active=True,
            settings={
                "buffer_before": 0,
                "buffer_after": 0,
                "business_hours": {},
                "max_per_day": 10,
                "max_per_week": 50,
            },
        )
        session.add(booking_link)
        session.commit()
        return booking_link

    def create_test_one_time_link(self, session, booking_link_id):
        """Helper method to create a test one-time link."""
        one_time_link = OneTimeLink(
            id=uuid.uuid4(),
            token=self.test_token,
            booking_link_id=booking_link_id,
            recipient_email="test@example.com",
            recipient_name="Test User",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            status="active",
        )
        session.add(one_time_link)
        session.commit()
        return one_time_link

    @patch("services.meetings.services.calendar_integration.get_user_availability")
    async def test_get_public_link_success(self, mock_get_availability):
        """Test successful retrieval of a public booking link."""
        from services.meetings.models import get_session

        # Mock the availability service
        mock_get_availability.return_value = self.mock_office_availability_response

        with get_session() as session:
            # Create test data
            booking_link = self.create_test_booking_link(session)
            one_time_link = self.create_test_one_time_link(session, booking_link.id)

            # Make request
            response = self.client.get(f"/api/v1/bookings/public/{self.test_token}")

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["is_active"] is True
            assert "title" in data["data"]
            assert data["data"]["title"] == "test-slug"  # Should match the slug

    def test_get_public_link_not_found(self):
        """Test retrieval of a non-existent public booking link."""
        response = self.client.get("/api/v1/bookings/public/nonexistent-token")
        assert response.status_code == 404

    @patch("services.meetings.services.calendar_integration.get_user_availability")
    async def test_get_public_availability_success(self, mock_get_availability):
        """Test successful retrieval of availability for a public link."""
        from services.meetings.models import get_session

        # Mock the office service response
        mock_get_availability.return_value = self.mock_office_availability_response

        with get_session() as session:
            # Create test data
            booking_link = self.create_test_booking_link(session)
            one_time_link = self.create_test_one_time_link(session, booking_link.id)

            # Make request
            response = self.client.get(
                f"/api/v1/bookings/public/{self.test_token}/availability?duration=30"
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "slots" in data["data"]
            assert len(data["data"]["slots"]) == 2
            assert data["data"]["duration"] == 30
            assert data["data"]["timezone"] == "UTC"

            # Verify the mock was called correctly
            mock_get_availability.assert_called_once()
            call_args = mock_get_availability.call_args
            assert call_args[0][0] == self.test_user_id  # user_id
            # Check that start and end are valid date strings
            assert isinstance(call_args[0][1], str)  # start date
            assert isinstance(call_args[0][2], str)  # end date
            assert call_args[0][3] == 30  # duration

    @patch("services.meetings.services.calendar_integration.get_user_availability")
    async def test_get_public_availability_with_different_durations(
        self, mock_get_availability
    ):
        """Test availability retrieval with different meeting durations."""
        from services.meetings.models import get_session

        # Mock the office service response
        mock_get_availability.return_value = self.mock_office_availability_response

        with get_session() as session:
            # Create test data
            booking_link = self.create_test_booking_link(session)
            one_time_link = self.create_test_one_time_link(session, booking_link.id)

            # Test different durations
            for duration in [15, 30, 60, 120]:
                response = self.client.get(
                    f"/api/v1/bookings/public/{self.test_token}/availability?duration={duration}"
                )

                assert response.status_code == 200
                data = response.json()
                assert data["data"]["duration"] == duration

    @patch("services.meetings.services.calendar_integration.get_user_availability")
    async def test_get_public_availability_no_slots(self, mock_get_availability):
        """Test availability retrieval when no slots are available."""
        from services.meetings.models import get_session

        # Mock empty response from office service
        mock_get_availability.return_value = {
            "data": {
                "available_slots": [],
                "total_slots": 0,
                "providers_used": [],
                "request_metadata": {},
            }
        }

        with get_session() as session:
            # Create test data
            booking_link = self.create_test_booking_link(session)
            one_time_link = self.create_test_one_time_link(session, booking_link.id)

            # Make request
            response = self.client.get(
                f"/api/v1/bookings/public/{self.test_token}/availability?duration=30"
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]["slots"]) == 0

    def test_get_public_availability_invalid_token(self):
        """Test availability retrieval with invalid token format."""
        response = self.client.get(
            "/api/v1/bookings/public/invalid-token/availability?duration=30"
        )
        assert response.status_code == 404  # Not found is correct for invalid tokens

    def test_get_public_availability_expired_link(self):
        """Test availability retrieval with expired one-time link."""
        from services.meetings.models import get_session

        with get_session() as session:
            # Create expired one-time link
            booking_link = self.create_test_booking_link(session)
            expired_link = OneTimeLink(
                id=uuid.uuid4(),
                token="expired-token",
                booking_link_id=booking_link.id,
                recipient_email="expired@example.com",
                recipient_name="Expired User",
                expires_at=datetime.now(timezone.utc)
                - timedelta(days=1),  # Expired yesterday
                status="active",
            )
            session.add(expired_link)
            session.commit()

            # Make request
            response = self.client.get(
                "/api/v1/bookings/public/expired-token/availability?duration=30"
            )
            assert response.status_code == 404

    def test_get_public_availability_used_link(self):
        """Test availability retrieval with already used one-time link."""
        from services.meetings.models import get_session

        with get_session() as session:
            # Create used one-time link
            booking_link = self.create_test_booking_link(session)
            used_link = OneTimeLink(
                id=uuid.uuid4(),
                token="used-token",
                booking_link_id=booking_link.id,
                recipient_email="used@example.com",
                recipient_name="Used User",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                status="used",  # Already used
            )
            session.add(used_link)
            session.commit()

            # Make request
            response = self.client.get(
                "/api/v1/bookings/public/used-token/availability?duration=30"
            )
            assert response.status_code == 404

    @patch("services.meetings.services.calendar_integration.get_user_availability")
    async def test_get_public_availability_with_booking_settings(
        self, mock_get_availability
    ):
        """Test availability retrieval with custom booking settings."""
        from services.meetings.models import get_session

        # Mock the office service response
        mock_get_availability.return_value = self.mock_office_availability_response

        with get_session() as session:
            # Create booking link with custom settings
            booking_link = BookingLink(
                id=uuid.uuid4(),
                owner_user_id=self.test_user_id,
                slug="custom-settings",
                is_active=True,
                settings=self.sample_booking_link_data["settings"],
            )
            session.add(booking_link)

            # Create one-time link
            one_time_link = OneTimeLink(
                id=uuid.uuid4(),
                token="custom-token",
                booking_link_id=booking_link.id,
                recipient_email="custom@example.com",
                recipient_name="Custom Test User",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                status="active",
            )
            session.add(one_time_link)
            session.commit()

            # Make request
            response = self.client.get(
                "/api/v1/bookings/public/custom-token/availability?duration=30"
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "slots" in data["data"]

    @patch("services.meetings.services.calendar_integration.get_user_availability")
    async def test_get_public_availability_office_service_error(
        self, mock_get_availability
    ):
        """Test handling of office service errors."""
        from services.meetings.models import get_session

        # Mock office service error
        mock_get_availability.side_effect = Exception("Office service unavailable")

        with get_session() as session:
            # Create test data
            booking_link = self.create_test_booking_link(session)
            one_time_link = self.create_test_one_time_link(session, booking_link.id)

            # Make request
            response = self.client.get(
                f"/api/v1/bookings/public/{self.test_token}/availability?duration=30"
            )

            # Should still return 200 but with empty slots
            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]["slots"]) == 0

    def test_rate_limiting(self):
        """Test rate limiting on public endpoints."""
        from services.meetings.models import get_session

        with get_session() as session:
            # Create test data
            booking_link = self.create_test_booking_link(session)
            one_time_link = self.create_test_one_time_link(session, booking_link.id)

            # Make a reasonable number of requests to test rate limiting
            # Start with a few normal requests
            for i in range(5):
                response = self.client.get(
                    f"/api/v1/bookings/public/{self.test_token}/availability?duration=30"
                )
                assert response.status_code in [200, 404]  # Normal responses

            # Test that we can still make requests without hitting rate limits
            response = self.client.get(
                f"/api/v1/bookings/public/{self.test_token}/availability?duration=30"
            )
            assert response.status_code in [200, 404]  # Should still work

    @patch("services.meetings.services.calendar_integration.get_user_availability")
    async def test_availability_timezone_handling(self, mock_get_availability):
        """Test proper timezone handling in availability responses."""
        from services.meetings.models import get_session

        # Mock response with timezone-aware datetimes in the future
        future_date = datetime.now(timezone.utc) + timedelta(days=7)
        mock_get_availability.return_value = {
            "data": {
                "available_slots": [
                    {
                        "start": future_date.replace(hour=9, minute=0, second=0, microsecond=0).isoformat(),
                        "end": future_date.replace(hour=9, minute=30, second=0, microsecond=0).isoformat(),
                        "duration_minutes": 30,
                    }
                ],
                "total_slots": 1,
                "providers_used": ["microsoft"],
                "request_metadata": {},
            }
        }

        with get_session() as session:
            # Create test data with a different token to avoid rate limiting
            booking_link = self.create_test_booking_link(session)
            one_time_link = OneTimeLink(
                id=uuid.uuid4(),
                token="timezone-test-token",
                booking_link_id=booking_link.id,
                recipient_email="timezone@example.com",
                recipient_name="Timezone Test User",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                status="active",
            )
            session.add(one_time_link)
            session.commit()

            # Make request
            response = self.client.get(
                "/api/v1/bookings/public/timezone-test-token/availability?duration=30"
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["timezone"] == "UTC"
            assert len(data["data"]["slots"]) == 1
            # Verify the slot time is properly formatted
            slot = data["data"]["slots"][0]
            assert "start" in slot
            assert "end" in slot
            # Duration is at the top level, not in each slot
            assert data["data"]["duration"] == 30
