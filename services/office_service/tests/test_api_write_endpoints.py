"""
Unit tests for unified write API endpoints.

Tests all write endpoints (email send, calendar events) with mocked dependencies
to ensure proper request handling, provider delegation, and error handling.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.office_service.api.calendar import router as calendar_router
from services.office_service.api.email import router as email_router
from services.office_service.core.clients.google import GoogleAPIClient
from services.office_service.core.clients.microsoft import MicrosoftAPIClient
from services.office_service.schemas import (
    CreateCalendarEventRequest,
    EmailAddress,
    SendEmailRequest,
)


@pytest.fixture
def app():
    """Create a test FastAPI app with email and calendar routers."""
    app = FastAPI()
    app.include_router(email_router, prefix="/email")
    app.include_router(calendar_router, prefix="/calendar")
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_email_request():
    """Create a sample email request for testing."""
    return SendEmailRequest(
        to=[EmailAddress(email="recipient@example.com", name="Test Recipient")],
        subject="Test Subject",
        body="Test email body content",
        cc=[EmailAddress(email="cc@example.com", name="CC User")],
        provider="google",
    )


@pytest.fixture
def sample_calendar_event_request():
    """Create a sample calendar event request for testing."""
    return CreateCalendarEventRequest(
        title="Test Meeting",
        description="Test meeting description",
        start_time=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc),
        location="Conference Room A",
        attendees=[EmailAddress(email="attendee@example.com", name="Attendee")],
        provider="google",
    )


@pytest.fixture
def mock_google_client():
    """Create a mock Google API client."""
    client = AsyncMock(spec=GoogleAPIClient)
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    return client


@pytest.fixture
def mock_microsoft_client():
    """Create a mock Microsoft API client."""
    client = AsyncMock(spec=MicrosoftAPIClient)
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    return client


class TestEmailSendEndpoint:
    """Test cases for POST /email/send endpoint."""

    @patch("services.office_service.api.email.api_client_factory")
    async def test_send_email_google_success(
        self, mock_factory, client, sample_email_request, mock_google_client
    ):
        """Test successful email send via Google."""
        # Mock factory to return Google client
        mock_factory.create_client = AsyncMock(return_value=mock_google_client)

        # Mock Gmail API response
        mock_sent_data = {
            "id": "gmail_message_123",
            "threadId": "thread_123",
            "labelIds": ["SENT"],
        }

        with patch(
            "services.office_service.api.email.send_gmail_message",
            new_callable=AsyncMock,
        ) as mock_send_gmail:
            mock_send_gmail.return_value = mock_sent_data

            response = client.post(
                "/email/send?user_id=test_user_123",
                json=sample_email_request.model_dump(),
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["message_id"] == "gmail_message_123"
            assert data["data"]["provider"] == "google"
            assert data["data"]["status"] == "sent"

            # Verify factory was called with correct parameters
            mock_factory.create_client.assert_called_once_with(
                "test_user_123", "google"
            )
            mock_send_gmail.assert_called_once()

    @patch("services.office_service.api.email.api_client_factory")
    async def test_send_email_microsoft_success(
        self, mock_factory, client, mock_microsoft_client
    ):
        """Test successful email send via Microsoft."""
        # Create Microsoft email request
        email_request = SendEmailRequest(
            to=[EmailAddress(email="recipient@example.com", name="Test Recipient")],
            subject="Test Subject",
            body="Test email body content",
            provider="microsoft",
        )

        # Mock factory to return Microsoft client
        mock_factory.create_client = AsyncMock(return_value=mock_microsoft_client)

        # Mock Outlook API response
        mock_sent_data = {
            "id": "outlook_message_456",
            "parentFolderId": "sentitems",
        }

        with patch(
            "services.office_service.api.email.send_outlook_message",
            new_callable=AsyncMock,
        ) as mock_send_outlook:
            mock_send_outlook.return_value = mock_sent_data

            response = client.post(
                "/email/send?user_id=test_user_123", json=email_request.model_dump()
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["message_id"] == "outlook_message_456"
            assert data["data"]["provider"] == "microsoft"
            assert data["data"]["status"] == "sent"

            # Verify factory was called with correct parameters
            mock_factory.create_client.assert_called_once_with(
                "test_user_123", "microsoft"
            )
            mock_send_outlook.assert_called_once()

    @patch("services.office_service.api.email.api_client_factory")
    async def test_send_email_default_provider(
        self, mock_factory, client, mock_google_client
    ):
        """Test email send with default provider (should use Google)."""
        # Create email request without provider (should default to google)
        email_request = SendEmailRequest(
            to=[EmailAddress(email="recipient@example.com", name="Test Recipient")],
            subject="Test Subject",
            body="Test email body content",
        )

        # Mock factory to return Google client
        mock_factory.create_client = AsyncMock(return_value=mock_google_client)

        mock_sent_data = {"id": "gmail_message_123"}

        with patch(
            "services.office_service.api.email.send_gmail_message",
            new_callable=AsyncMock,
        ) as mock_send_gmail:
            mock_send_gmail.return_value = mock_sent_data

            response = client.post(
                "/email/send?user_id=test_user_123", json=email_request.model_dump()
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["provider"] == "google"  # Should default to google

            # Verify factory was called with google
            mock_factory.create_client.assert_called_once_with(
                "test_user_123", "google"
            )

    def test_send_email_invalid_provider(self, client):
        """Test email send with invalid provider."""
        email_request = SendEmailRequest(
            to=[EmailAddress(email="recipient@example.com", name="Test Recipient")],
            subject="Test Subject",
            body="Test email body content",
            provider="invalid_provider",
        )

        response = client.post(
            "/email/send?user_id=test_user_123", json=email_request.model_dump()
        )

        assert response.status_code == 400
        assert "Invalid provider" in response.json()["detail"]

    @patch("services.office_service.api.email.api_client_factory")
    async def test_send_email_no_client(
        self, mock_factory, client, sample_email_request
    ):
        """Test email send when API client creation fails."""
        # Mock factory to return None (client creation failed)
        mock_factory.create_client = AsyncMock(return_value=None)

        response = client.post(
            "/email/send?user_id=test_user_123", json=sample_email_request.model_dump()
        )

        assert response.status_code == 503
        assert "Failed to create API client" in response.json()["detail"]

    @patch("services.office_service.api.email.api_client_factory")
    async def test_send_email_api_error(
        self, mock_factory, client, sample_email_request, mock_google_client
    ):
        """Test email send when API call fails."""
        # Mock factory to return Google client
        mock_factory.create_client = AsyncMock(return_value=mock_google_client)

        with patch(
            "services.office_service.api.email.send_gmail_message",
            new_callable=AsyncMock,
        ) as mock_send_gmail:
            mock_send_gmail.side_effect = Exception("Gmail API error")

            response = client.post(
                "/email/send?user_id=test_user_123",
                json=sample_email_request.model_dump(),
            )

            assert response.status_code == 500
            assert "Failed to send email" in response.json()["detail"]


class TestCalendarEventEndpoints:
    """Test cases for calendar event write endpoints."""

    @patch("services.office_service.api.calendar.api_client_factory")
    async def test_create_calendar_event_google_success(
        self, mock_factory, client, sample_calendar_event_request, mock_google_client
    ):
        """Test successful calendar event creation via Google."""
        # Mock factory to return Google client
        mock_factory.create_client = AsyncMock(return_value=mock_google_client)

        # Mock Google Calendar API response
        mock_event_data = {
            "id": "google_event_123",
            "summary": "Test Meeting",
            "start": {"dateTime": "2024-01-15T10:00:00Z"},
            "end": {"dateTime": "2024-01-15T11:00:00Z"},
            "status": "confirmed",
        }

        with patch(
            "services.office_service.api.calendar.create_google_calendar_event",
            new_callable=AsyncMock,
        ) as mock_create_google:
            mock_create_google.return_value = mock_event_data

            response = client.post(
                "/calendar/events?user_id=test_user_123",
                json=sample_calendar_event_request.model_dump(),
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["event_id"] == "google_event_123"
            assert data["data"]["provider"] == "google"
            assert data["data"]["status"] == "created"

            # Verify factory was called with correct parameters
            mock_factory.create_client.assert_called_once_with(
                "test_user_123", "google"
            )
            mock_create_google.assert_called_once()

    @patch("services.office_service.api.calendar.api_client_factory")
    async def test_create_calendar_event_microsoft_success(
        self, mock_factory, client, mock_microsoft_client
    ):
        """Test successful calendar event creation via Microsoft."""
        # Create Microsoft calendar event request
        event_request = CreateCalendarEventRequest(
            title="Test Meeting",
            description="Test meeting description",
            start_time=datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 15, 11, 0, tzinfo=timezone.utc),
            provider="microsoft",
        )

        # Mock factory to return Microsoft client
        mock_factory.create_client = AsyncMock(return_value=mock_microsoft_client)

        # Mock Microsoft Graph API response
        mock_event_data = {
            "id": "microsoft_event_456",
            "subject": "Test Meeting",
            "start": {"dateTime": "2024-01-15T10:00:00.0000000", "timeZone": "UTC"},
            "end": {"dateTime": "2024-01-15T11:00:00.0000000", "timeZone": "UTC"},
            "showAs": "busy",
        }

        with patch(
            "services.office_service.api.calendar.create_microsoft_calendar_event",
            new_callable=AsyncMock,
        ) as mock_create_microsoft:
            mock_create_microsoft.return_value = mock_event_data

            response = client.post(
                "/calendar/events?user_id=test_user_123",
                json=event_request.model_dump(),
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["event_id"] == "microsoft_event_456"
            assert data["data"]["provider"] == "microsoft"
            assert data["data"]["status"] == "created"

            # Verify factory was called with correct parameters
            mock_factory.create_client.assert_called_once_with(
                "test_user_123", "microsoft"
            )
            mock_create_microsoft.assert_called_once()

    @patch("services.office_service.api.calendar.api_client_factory")
    async def test_create_calendar_event_no_client(
        self, mock_factory, client, sample_calendar_event_request
    ):
        """Test calendar event creation when API client creation fails."""
        # Mock factory to return None
        mock_factory.create_client = AsyncMock(return_value=None)

        response = client.post(
            "/calendar/events?user_id=test_user_123",
            json=sample_calendar_event_request.model_dump(),
        )

        assert response.status_code == 503
        assert "Failed to create API client" in response.json()["detail"]

    @patch("services.office_service.api.calendar.api_client_factory")
    async def test_create_calendar_event_api_error(
        self, mock_factory, client, sample_calendar_event_request, mock_google_client
    ):
        """Test calendar event creation when API call fails."""
        # Mock factory to return Google client
        mock_factory.create_client = AsyncMock(return_value=mock_google_client)

        with patch(
            "services.office_service.api.calendar.create_google_calendar_event",
            new_callable=AsyncMock,
        ) as mock_create_google:
            mock_create_google.side_effect = Exception("Calendar API error")

            response = client.post(
                "/calendar/events?user_id=test_user_123",
                json=sample_calendar_event_request.model_dump(),
            )

            assert response.status_code == 500
            assert "Failed to create calendar event" in response.json()["detail"]

    @patch("services.office_service.api.calendar.api_client_factory")
    async def test_delete_calendar_event_success(
        self, mock_factory, client, mock_google_client
    ):
        """Test successful calendar event deletion."""
        # Mock factory to return Google client
        mock_factory.create_client = AsyncMock(return_value=mock_google_client)

        with patch(
            "services.office_service.api.calendar.delete_provider_event",
            new_callable=AsyncMock,
        ) as mock_delete_event:
            mock_delete_event.return_value = True

            response = client.delete(
                "/calendar/events/google_event_123?user_id=test_user_123"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "deleted"
            assert data["data"]["event_id"] == "google_event_123"

            # Verify delete was called
            mock_delete_event.assert_called_once()

    @patch("services.office_service.api.calendar.api_client_factory")
    async def test_delete_calendar_event_not_found(
        self, mock_factory, client, mock_google_client
    ):
        """Test calendar event deletion when event not found."""
        # Mock factory to return Google client
        mock_factory.create_client = AsyncMock(return_value=mock_google_client)

        with patch(
            "services.office_service.api.calendar.delete_provider_event",
            new_callable=AsyncMock,
        ) as mock_delete_event:
            mock_delete_event.return_value = False

            response = client.delete(
                "/calendar/events/google_event_123?user_id=test_user_123"
            )

            assert response.status_code == 404
            assert "Event not found" in response.json()["detail"]

    def test_delete_calendar_event_invalid_id(self, client):
        """Test calendar event deletion with invalid event ID format."""
        response = client.delete("/calendar/events/invalid_id?user_id=test_user_123")

        assert response.status_code == 400
        assert "Invalid event ID format" in response.json()["detail"]

    @patch("services.office_service.api.calendar.api_client_factory")
    async def test_delete_calendar_event_no_client(self, mock_factory, client):
        """Test calendar event deletion when API client creation fails."""
        # Mock factory to return None
        mock_factory.create_client = AsyncMock(return_value=None)

        response = client.delete(
            "/calendar/events/google_event_123?user_id=test_user_123"
        )

        assert response.status_code == 503
        assert "Failed to create API client" in response.json()["detail"]

    @patch("services.office_service.api.calendar.api_client_factory")
    async def test_delete_calendar_event_api_error(
        self, mock_factory, client, mock_google_client
    ):
        """Test calendar event deletion when API call fails."""
        # Mock factory to return Google client
        mock_factory.create_client = AsyncMock(return_value=mock_google_client)

        with patch(
            "services.office_service.api.calendar.delete_provider_event",
            new_callable=AsyncMock,
        ) as mock_delete_event:
            mock_delete_event.side_effect = Exception("Calendar API deletion error")

            response = client.delete(
                "/calendar/events/google_event_123?user_id=test_user_123"
            )

            assert response.status_code == 500
            assert "Failed to delete calendar event" in response.json()["detail"]


class TestWriteEndpointValidation:
    """Test cases for write endpoint request validation."""

    def test_send_email_missing_required_fields(self, client):
        """Test email send with missing required fields."""
        incomplete_request = {"subject": "Test Subject"}  # Missing 'to' and 'body'

        response = client.post(
            "/email/send?user_id=test_user_123", json=incomplete_request
        )

        assert response.status_code == 422  # Validation error

    def test_send_email_invalid_email_format(self, client):
        """Test email send with invalid email format."""
        invalid_request = {
            "to": [{"email": "invalid-email", "name": "Test"}],
            "subject": "Test Subject",
            "body": "Test body",
        }

        response = client.post(
            "/email/send?user_id=test_user_123", json=invalid_request
        )

        assert response.status_code == 422  # Validation error

    def test_create_calendar_event_missing_required_fields(self, client):
        """Test calendar event creation with missing required fields."""
        incomplete_request = {"title": "Test Meeting"}  # Missing start_time, end_time

        response = client.post(
            "/calendar/events?user_id=test_user_123", json=incomplete_request
        )

        assert response.status_code == 422  # Validation error

    def test_create_calendar_event_invalid_datetime(self, client):
        """Test calendar event creation with invalid datetime format."""
        invalid_request = {
            "title": "Test Meeting",
            "start_time": "not-a-datetime",
            "end_time": "2024-01-15T11:00:00Z",
        }

        response = client.post(
            "/calendar/events?user_id=test_user_123", json=invalid_request
        )

        assert response.status_code == 422  # Validation error

    def test_create_calendar_event_end_before_start(self, client):
        """Test calendar event creation with end time before start time."""
        invalid_request = {
            "title": "Test Meeting",
            "start_time": "2024-01-15T11:00:00Z",
            "end_time": "2024-01-15T10:00:00Z",  # End before start
        }

        response = client.post(
            "/calendar/events?user_id=test_user_123", json=invalid_request
        )

        # This might be handled by business logic validation
        # The exact status code depends on implementation
        assert response.status_code in [400, 422]
