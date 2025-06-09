"""
Integration tests for Office Service API endpoints.

These tests verify the complete end-to-end functionality of the API
endpoints with properly mocked external dependencies.
"""

from unittest.mock import patch

from core.exceptions import ProviderAPIError
from core.token_manager import TokenData
from fastapi import status


class TestHealthEndpoints:
    """Test health and diagnostic endpoints."""

    def test_health_basic(self, client):
        """Test basic health check endpoint."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "checks" in data
        assert data["checks"]["database"] is True
        assert data["checks"]["redis"] is True

    def test_health_integrations_success(self, client, integration_test_setup):
        """Test integration health check with successful token retrieval."""
        user_id = integration_test_setup["user_id"]

        response = client.get(f"/health/integrations/{user_id}")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["user_id"] == user_id
        assert "google" in data["integrations"]
        assert "microsoft" in data["integrations"]
        assert data["integrations"]["google"]["healthy"] is True
        assert data["integrations"]["microsoft"]["healthy"] is True

    def test_health_integrations_partial_failure(self, client, test_user_id):
        """Test integration health with one provider failing."""

        def failing_token_side_effect(user_id, provider, scopes=None):
            if provider == "google":
                return TokenData(
                    access_token="mock-google-token",
                    refresh_token="mock-refresh",
                    expires_at=None,
                    scopes=[],
                    provider="google",
                    user_id=user_id,
                )
            else:
                raise ProviderAPIError("Microsoft integration failed")

        with patch(
            "core.token_manager.TokenManager.get_user_token",
            side_effect=failing_token_side_effect,
        ):
            response = client.get(f"/health/integrations/{test_user_id}")
            assert response.status_code == status.HTTP_200_OK

            data = response.json()
            assert data["integrations"]["google"]["healthy"] is True
            assert data["integrations"]["microsoft"]["healthy"] is False
            assert "error" in data["integrations"]["microsoft"]


class TestEmailEndpoints:
    """Test unified email API endpoints."""

    def test_get_email_messages_success(self, client, integration_test_setup):
        """Test successful retrieval of email messages from multiple providers."""
        user_id = integration_test_setup["user_id"]

        response = client.get(f"/email/messages?user_id={user_id}")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 2  # At least one from each provider

        # Verify structure of first message
        first_message = data["data"][0]
        assert "id" in first_message
        assert "subject" in first_message
        assert "sender" in first_message
        assert "recipients" in first_message
        assert "timestamp" in first_message
        assert "body_preview" in first_message
        assert "provider" in first_message

    def test_get_email_messages_with_pagination(self, client, integration_test_setup):
        """Test email messages endpoint with pagination parameters."""
        user_id = integration_test_setup["user_id"]

        response = client.get(f"/email/messages?user_id={user_id}&limit=1&offset=0")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) <= 1

    def test_get_email_messages_missing_user_id(self, client):
        """Test email messages endpoint without user_id parameter."""
        response = client.get("/email/messages")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_email_message_by_id_success(self, client, integration_test_setup):
        """Test retrieval of specific email message by ID."""
        user_id = integration_test_setup["user_id"]
        message_id = "google-msg-1"  # From mock data

        response = client.get(f"/email/messages/{message_id}?user_id={user_id}")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == message_id
        assert data["data"]["provider"] == "google"

    def test_get_email_message_not_found(self, client, integration_test_setup):
        """Test retrieval of non-existent email message."""
        user_id = integration_test_setup["user_id"]

        with patch("httpx.AsyncClient.request") as mock_request:
            mock_request.side_effect = Exception("Message not found")

            response = client.get(f"/email/messages/nonexistent-id?user_id={user_id}")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_send_email_success(self, client, integration_test_setup):
        """Test successful email sending."""
        user_id = integration_test_setup["user_id"]

        email_data = {
            "to": [{"email": "recipient@example.com", "name": "Recipient"}],
            "subject": "Test Email",
            "body": "This is a test email",
            "provider": "google",
        }

        with patch("httpx.AsyncClient.request") as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.json.return_value = {"id": "sent-message-123"}

            response = client.post(f"/email/send?user_id={user_id}", json=email_data)
            assert response.status_code == status.HTTP_200_OK

            data = response.json()
            assert data["success"] is True

    def test_send_email_missing_fields(self, client, test_user_id):
        """Test email sending with missing required fields."""
        incomplete_data = {
            "to": [{"email": "recipient@example.com"}],
            # Missing subject and body
        }

        response = client.post(
            f"/email/send?user_id={test_user_id}", json=incomplete_data
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCalendarEndpoints:
    """Test unified calendar API endpoints."""

    def test_get_calendar_events_success(self, client, integration_test_setup):
        """Test successful retrieval of calendar events."""
        user_id = integration_test_setup["user_id"]

        response = client.get(f"/calendar/events?user_id={user_id}")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

        if len(data["data"]) > 0:
            first_event = data["data"][0]
            assert "id" in first_event
            assert "title" in first_event
            assert "start_time" in first_event
            assert "end_time" in first_event
            assert "provider" in first_event

    def test_get_calendar_events_with_date_range(self, client, integration_test_setup):
        """Test calendar events with date range filtering."""
        user_id = integration_test_setup["user_id"]

        response = client.get(
            f"/calendar/events?user_id={user_id}&start_date=2024-01-01&end_date=2024-01-31"
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["success"] is True

    def test_create_calendar_event_success(self, client, integration_test_setup):
        """Test successful calendar event creation."""
        user_id = integration_test_setup["user_id"]

        event_data = {
            "title": "New Test Event",
            "description": "Created via API test",
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T11:00:00Z",
            "attendees": [{"email": "attendee@example.com", "name": "Attendee"}],
            "provider": "google",
        }

        with patch("httpx.AsyncClient.request") as mock_request:
            mock_request.return_value.status_code = 200
            mock_request.return_value.json.return_value = {"id": "new-event-123"}

            response = client.post(
                f"/calendar/events?user_id={user_id}", json=event_data
            )
            assert response.status_code == status.HTTP_200_OK

            data = response.json()
            assert data["success"] is True

    def test_delete_calendar_event_success(self, client, integration_test_setup):
        """Test successful calendar event deletion."""
        user_id = integration_test_setup["user_id"]
        event_id = "google-event-1"

        with patch("httpx.AsyncClient.request") as mock_request:
            mock_request.return_value.status_code = 204

            response = client.delete(f"/calendar/events/{event_id}?user_id={user_id}")
            assert response.status_code == status.HTTP_200_OK

            data = response.json()
            assert data["success"] is True


class TestFilesEndpoints:
    """Test unified files API endpoints."""

    def test_get_files_success(self, client, integration_test_setup):
        """Test successful retrieval of files."""
        user_id = integration_test_setup["user_id"]

        response = client.get(f"/files/?user_id={user_id}")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

        if len(data["data"]) > 0:
            first_file = data["data"][0]
            assert "id" in first_file
            assert "name" in first_file
            assert "size" in first_file
            assert "created_at" in first_file
            assert "provider" in first_file

    def test_search_files_success(self, client, integration_test_setup):
        """Test successful file search."""
        user_id = integration_test_setup["user_id"]

        response = client.get(f"/files/search?user_id={user_id}&q=document")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_get_file_by_id_success(self, client, integration_test_setup):
        """Test retrieval of specific file by ID."""
        user_id = integration_test_setup["user_id"]
        file_id = "google-file-1"

        response = client.get(f"/files/{file_id}?user_id={user_id}")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == file_id


class TestErrorScenarios:
    """Test error handling across different scenarios."""

    def test_provider_api_error_handling(self, client, test_user_id):
        """Test handling of provider API errors."""

        def failing_http_side_effect(*args, **kwargs):
            raise Exception("Provider API is down")

        with (
            patch("core.token_manager.TokenManager.get_user_token") as mock_token,
            patch("httpx.AsyncClient.request", side_effect=failing_http_side_effect),
        ):
            mock_token.return_value = TokenData(
                access_token="mock-token",
                refresh_token="mock-refresh",
                expires_at=None,
                scopes=[],
                provider="google",
                user_id=test_user_id,
            )

            response = client.get(f"/email/messages?user_id={test_user_id}")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

            data = response.json()
            assert data["success"] is False
            assert "error" in data

    def test_authentication_failure(self, client, test_user_id):
        """Test handling of authentication failures."""
        with patch("core.token_manager.TokenManager.get_user_token") as mock_token:
            mock_token.side_effect = ProviderAPIError("Authentication failed")

            response = client.get(f"/email/messages?user_id={test_user_id}")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestCaching:
    """Test caching behavior."""

    def test_cache_hit_behavior(self, client, integration_test_setup):
        """Test that cache hits return cached data without API calls."""
        user_id = integration_test_setup["user_id"]
        cached_data = {
            "success": True,
            "data": [{"id": "cached-msg-1", "subject": "Cached Email"}],
        }

        with patch(
            "core.cache_manager.cache_manager.get_from_cache", return_value=cached_data
        ):
            response = client.get(f"/email/messages?user_id={user_id}")
            assert response.status_code == status.HTTP_200_OK

            data = response.json()
            assert data == cached_data

    def test_cache_miss_behavior(self, client, integration_test_setup):
        """Test that cache misses trigger API calls and cache the result."""
        user_id = integration_test_setup["user_id"]

        with (
            patch(
                "core.cache_manager.cache_manager.get_from_cache", return_value=None
            ) as mock_get,
            patch("core.cache_manager.cache_manager.set_to_cache") as mock_set,
        ):
            response = client.get(f"/email/messages?user_id={user_id}")
            assert response.status_code == status.HTTP_200_OK

            # Verify cache was checked and data was cached
            mock_get.assert_called_once()
            mock_set.assert_called_once()
