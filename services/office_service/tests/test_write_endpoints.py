"""Unit tests for write endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.office_service.api.calendar import router as calendar_router
from services.office_service.api.email import router as email_router
from services.office_service.schemas import (
    CreateCalendarEventRequest,
    EmailAddress,
    SendEmailRequest,
)


@pytest.fixture
def app():
    """Create a test FastAPI app with routers."""
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
        provider="google",
    )


class TestEmailSend:
    """Test cases for email send endpoint."""

    @patch("services.office_service.api.email.api_client_factory")
    async def test_send_email_success(self, mock_factory, client, sample_email_request):
        """Test successful email send."""
        # Mock API client factory
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_factory.create_client = AsyncMock(return_value=mock_client)

        # Mock email send function
        with patch(
            "services.office_service.api.email.send_gmail_message",
            new_callable=AsyncMock,
        ) as mock_send:
            mock_send.return_value = {"id": "test_message_id"}

            response = client.post(
                "/email/send?user_id=test_user_123",
                json=sample_email_request.model_dump(),
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "sent"

    @patch("services.office_service.api.email.api_client_factory")
    async def test_send_email_no_client(
        self, mock_factory, client, sample_email_request
    ):
        """Test email send when client creation fails."""
        mock_factory.create_client = AsyncMock(return_value=None)

        response = client.post(
            "/email/send?user_id=test_user_123",
            json=sample_email_request.model_dump(),
        )

        assert response.status_code == 503
        assert "Failed to create API client" in response.json()["detail"]

    def test_send_email_invalid_provider(self, client):
        """Test email send with invalid provider."""
        invalid_request = SendEmailRequest(
            to=[EmailAddress(email="test@example.com")],
            subject="Test",
            body="Test body",
            provider="invalid_provider",
        )

        response = client.post(
            "/email/send?user_id=test_user_123",
            json=invalid_request.model_dump(),
        )

        assert response.status_code == 400
        assert "Invalid provider" in response.json()["detail"]


class TestCalendarEvents:
    """Test cases for calendar event endpoints."""

    @patch("services.office_service.api.calendar.api_client_factory")
    async def test_create_event_success(
        self, mock_factory, client, sample_calendar_event_request
    ):
        """Test successful calendar event creation."""
        # Mock API client factory
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_factory.create_client = AsyncMock(return_value=mock_client)

        # Mock event creation function
        with patch(
            "services.office_service.api.calendar.create_google_calendar_event",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = {"id": "test_event_id"}

            response = client.post(
                "/calendar/events?user_id=test_user_123",
                json=sample_calendar_event_request.model_dump(),
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "created"

    @patch("services.office_service.api.calendar.api_client_factory")
    async def test_delete_event_success(self, mock_factory, client):
        """Test successful calendar event deletion."""
        # Mock API client factory
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_factory.create_client = AsyncMock(return_value=mock_client)

        # Mock event deletion function
        with patch(
            "services.office_service.api.calendar.delete_google_event",
            new_callable=AsyncMock,
        ) as mock_delete:
            # delete_google_event doesn't return anything, just completes successfully

            response = client.delete(
                "/calendar/events/google_event_123?user_id=test_user_123"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "deleted"

    @patch("services.office_service.api.calendar.api_client_factory")
    async def test_delete_event_not_found(self, mock_factory, client):
        """Test calendar event deletion when event not found."""
        # Mock API client factory
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_factory.create_client = AsyncMock(return_value=mock_client)

        # Mock event deletion function to raise exception (not found)
        with patch(
            "services.office_service.api.calendar.delete_google_event",
            new_callable=AsyncMock,
        ) as mock_delete:
            mock_delete.side_effect = Exception("Event not found")

            response = client.delete(
                "/calendar/events/google_event_123?user_id=test_user_123"
            )

            assert response.status_code == 500
            assert "Failed to delete calendar event" in response.json()["detail"]
