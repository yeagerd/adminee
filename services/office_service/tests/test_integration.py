from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from services.office_service.app.main import app
from services.office_service.models import Provider


class TestHealthEndpoints:
    """Integration tests for health endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test GET /health endpoint"""
        with (
            patch("services.office_service.models.database.is_connected", True),
            patch(
                "services.office_service.models.database.execute_query"
            ) as mock_db_query,
            patch(
                "services.office_service.core.cache_manager.cache_manager.health_check",
                return_value=True,
            ),
            patch(
                "services.office_service.api.health.check_service_connection",
                return_value=True,
            ),
        ):
            mock_db_query.return_value = None

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "checks" in data
            assert "timestamp" in data

    def test_health_endpoint_unhealthy_database(self, client):
        """Test health endpoint when database is unhealthy"""
        with (
            patch("services.office_service.models.database.is_connected", False),
            patch(
                "services.office_service.models.database.execute_query"
            ) as mock_db_query,
            patch(
                "services.office_service.core.cache_manager.cache_manager.health_check",
                return_value=True,
            ),
            patch(
                "services.office_service.api.health.check_service_connection",
                return_value=True,
            ),
        ):
            mock_db_query.side_effect = Exception("Database connection failed")

            response = client.get("/health")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_integrations_endpoint(self, client):
        """Test GET /health/integrations/{user_id} endpoint"""
        user_id = "test-user-123"

        with patch(
            "services.office_service.core.token_manager.TokenManager.get_user_token"
        ) as mock_get_token:
            # Mock successful token retrieval for both providers
            mock_get_token.side_effect = [
                "google-token-123",  # Google token
                "microsoft-token-456",  # Microsoft token
            ]

            response = client.get(f"/health/integrations/{user_id}")

            assert response.status_code == 200
            data = response.json()
            assert "google" in data["integrations"]
            assert "microsoft" in data["integrations"]
            assert data["integrations"]["google"]["status"] == "connected"
            assert data["integrations"]["microsoft"]["status"] == "connected"

    @pytest.mark.asyncio
    async def test_health_integrations_endpoint_partial_failure(self, client):
        """Test integrations endpoint when one provider fails"""
        user_id = "test-user-123"

        with patch(
            "services.office_service.core.token_manager.TokenManager.get_user_token"
        ) as mock_get_token:
            # Mock Google success, Microsoft failure
            async def mock_token_side_effect(user_id, provider):
                if provider == "google":
                    return "google-token-123"
                else:
                    raise Exception("Token not found")

            mock_get_token.side_effect = mock_token_side_effect

            response = client.get(f"/health/integrations/{user_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["integrations"]["google"]["status"] == "connected"
            assert data["integrations"]["microsoft"]["status"] == "error"


class TestEmailEndpoints:
    """Integration tests for email endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_get_email_messages(self, client):
        """Test GET /email/messages endpoint"""
        user_id = "test-user-123"

        # Mock responses from both providers
        google_messages = {
            "messages": [
                {
                    "id": "google-msg-1",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Test Email 1"},
                            {"name": "From", "value": "sender@gmail.com"},
                            {
                                "name": "Date",
                                "value": "Thu, 01 Jan 2024 12:00:00 +0000",
                            },
                        ],
                        "body": {"data": "VGVzdCBib2R5"},  # Base64 encoded "Test body"
                    },
                    "snippet": "Test email snippet",
                }
            ]
        }

        microsoft_messages = {
            "value": [
                {
                    "id": "microsoft-msg-1",
                    "subject": "Test Email 2",
                    "from": {
                        "emailAddress": {
                            "address": "sender@outlook.com",
                            "name": "Sender",
                        }
                    },
                    "receivedDateTime": "2024-01-01T12:00:00Z",
                    "body": {"content": "Test body 2", "contentType": "text"},
                    "bodyPreview": "Test email snippet 2",
                }
            ]
        }

        with (
            patch(
                "services.office_service.core.token_manager.TokenManager.get_user_token"
            ) as mock_get_token,
            patch(
                "services.office_service.core.cache_manager.CacheManager.get_from_cache",
                return_value=None,
            ),
            patch(
                "services.office_service.core.cache_manager.CacheManager.set_to_cache"
            ) as mock_set_cache,
            patch("httpx.AsyncClient.request") as mock_request,
        ):

            # Setup token manager
            mock_get_token.side_effect = ["google-token", "microsoft-token"]

            # Setup HTTP responses
            mock_responses = [
                MagicMock(
                    status_code=200,
                    json=lambda: google_messages,
                    raise_for_status=lambda: None,
                ),
                MagicMock(
                    status_code=200,
                    json=lambda: microsoft_messages,
                    raise_for_status=lambda: None,
                ),
            ]
            mock_request.side_effect = mock_responses

            response = client.get(f"/email/messages?user_id={user_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 2
            assert data["data"]["items"][0]["provider"] in ["google", "microsoft"]
            assert data["data"]["items"][1]["provider"] in ["google", "microsoft"]

            # Verify caching was called
            mock_set_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_email_message_by_id(self, client):
        """Test GET /email/messages/{message_id} endpoint"""
        user_id = "test-user-123"
        message_id = "google:gmail-message-123"

        google_message = {
            "id": "gmail-message-123",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Email"},
                    {"name": "From", "value": "sender@gmail.com"},
                    {"name": "Date", "value": "Thu, 01 Jan 2024 12:00:00 +0000"},
                ],
                "body": {"data": "VGVzdCBib2R5"},  # Base64 encoded "Test body"
            },
            "snippet": "Test email snippet",
        }

        with (
            patch(
                "services.office_service.core.token_manager.TokenManager.get_user_token",
                return_value="google-token",
            ),
            patch(
                "services.office_service.core.cache_manager.CacheManager.get_from_cache",
                return_value=None,
            ),
            patch(
                "services.office_service.core.cache_manager.CacheManager.set_to_cache"
            ),
            patch("httpx.AsyncClient.request") as mock_request,
        ):

            mock_request.return_value = MagicMock(
                status_code=200,
                json=lambda: google_message,
                raise_for_status=lambda: None,
            )

            response = client.get(f"/email/messages/{message_id}?user_id={user_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["id"] == message_id
            assert data["data"]["provider"] == "google"

    @pytest.mark.asyncio
    async def test_send_email(self, client):
        """Test POST /email/send endpoint"""
        user_id = "test-user-123"
        email_data = {
            "to": [{"email": "recipient@example.com", "name": "Recipient"}],
            "subject": "Test Email",
            "body": "This is a test email",
            "provider": "google",
        }

        with (
            patch(
                "services.office_service.core.token_manager.TokenManager.get_user_token",
                return_value="google-token",
            ),
            patch("httpx.AsyncClient.request") as mock_request,
        ):

            mock_request.return_value = MagicMock(
                status_code=200,
                json=lambda: {"id": "sent-message-123"},
                raise_for_status=lambda: None,
            )

            response = client.post(f"/email/send?user_id={user_id}", json=email_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "sent_message_id" in data["data"]


class TestCalendarEndpoints:
    """Integration tests for calendar endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_get_calendar_events(self, client):
        """Test GET /calendar/events endpoint"""
        user_id = "test-user-123"

        google_events = {
            "items": [
                {
                    "id": "google-event-1",
                    "summary": "Test Event 1",
                    "start": {"dateTime": "2024-01-01T10:00:00Z"},
                    "end": {"dateTime": "2024-01-01T11:00:00Z"},
                    "creator": {"email": "creator@gmail.com"},
                    "organizer": {"email": "organizer@gmail.com"},
                }
            ]
        }

        microsoft_events = {
            "value": [
                {
                    "id": "microsoft-event-1",
                    "subject": "Test Event 2",
                    "start": {"dateTime": "2024-01-01T14:00:00Z", "timeZone": "UTC"},
                    "end": {"dateTime": "2024-01-01T15:00:00Z", "timeZone": "UTC"},
                    "organizer": {"emailAddress": {"address": "organizer@outlook.com"}},
                }
            ]
        }

        with (
            patch(
                "services.office_service.core.token_manager.TokenManager.get_user_token"
            ) as mock_get_token,
            patch(
                "services.office_service.core.cache_manager.CacheManager.get_from_cache",
                return_value=None,
            ),
            patch(
                "services.office_service.core.cache_manager.CacheManager.set_to_cache"
            ),
            patch("httpx.AsyncClient.request") as mock_request,
        ):

            mock_get_token.side_effect = ["google-token", "microsoft-token"]

            mock_responses = [
                MagicMock(
                    status_code=200,
                    json=lambda: google_events,
                    raise_for_status=lambda: None,
                ),
                MagicMock(
                    status_code=200,
                    json=lambda: microsoft_events,
                    raise_for_status=lambda: None,
                ),
            ]
            mock_request.side_effect = mock_responses

            response = client.get(f"/calendar/events?user_id={user_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 2

    @pytest.mark.asyncio
    async def test_create_calendar_event(self, client):
        """Test POST /calendar/events endpoint"""
        user_id = "test-user-123"
        event_data = {
            "title": "New Meeting",
            "description": "Team sync meeting",
            "start_time": "2024-01-01T10:00:00Z",
            "end_time": "2024-01-01T11:00:00Z",
            "attendees": [{"email": "attendee@example.com"}],
            "provider": "google",
        }

        with (
            patch(
                "services.office_service.core.token_manager.TokenManager.get_user_token",
                return_value="google-token",
            ),
            patch("httpx.AsyncClient.request") as mock_request,
        ):

            mock_request.return_value = MagicMock(
                status_code=200,
                json=lambda: {"id": "created-event-123", "summary": "New Meeting"},
                raise_for_status=lambda: None,
            )

            response = client.post(
                f"/calendar/events?user_id={user_id}", json=event_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["id"] == "google:created-event-123"

    @pytest.mark.asyncio
    async def test_delete_calendar_event(self, client):
        """Test DELETE /calendar/events/{event_id} endpoint"""
        user_id = "test-user-123"
        event_id = "google:calendar-event-123"

        with (
            patch(
                "services.office_service.core.token_manager.TokenManager.get_user_token",
                return_value="google-token",
            ),
            patch("httpx.AsyncClient.request") as mock_request,
        ):

            mock_request.return_value = MagicMock(
                status_code=204, raise_for_status=lambda: None
            )

            response = client.delete(f"/calendar/events/{event_id}?user_id={user_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestFilesEndpoints:
    """Integration tests for files endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_get_files(self, client):
        """Test GET /files/ endpoint"""
        user_id = "test-user-123"

        google_files = {
            "files": [
                {
                    "id": "google-file-1",
                    "name": "Document.pdf",
                    "mimeType": "application/pdf",
                    "size": "1024",
                    "createdTime": "2024-01-01T10:00:00Z",
                    "modifiedTime": "2024-01-01T10:00:00Z",
                    "webViewLink": "https://drive.google.com/file/d/abc123",
                }
            ]
        }

        microsoft_files = {
            "value": [
                {
                    "id": "microsoft-file-1",
                    "name": "Spreadsheet.xlsx",
                    "file": {
                        "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    },
                    "size": 2048,
                    "createdDateTime": "2024-01-01T14:00:00Z",
                    "lastModifiedDateTime": "2024-01-01T14:00:00Z",
                    "webUrl": "https://onedrive.live.com/edit.aspx?resid=def456",
                }
            ]
        }

        with (
            patch(
                "services.office_service.core.token_manager.TokenManager.get_user_token"
            ) as mock_get_token,
            patch(
                "services.office_service.core.cache_manager.CacheManager.get_from_cache",
                return_value=None,
            ),
            patch(
                "services.office_service.core.cache_manager.CacheManager.set_to_cache"
            ),
            patch("httpx.AsyncClient.request") as mock_request,
        ):

            mock_get_token.side_effect = ["google-token", "microsoft-token"]

            mock_responses = [
                MagicMock(
                    status_code=200,
                    json=lambda: google_files,
                    raise_for_status=lambda: None,
                ),
                MagicMock(
                    status_code=200,
                    json=lambda: microsoft_files,
                    raise_for_status=lambda: None,
                ),
            ]
            mock_request.side_effect = mock_responses

            response = client.get(f"/files/?user_id={user_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["items"]) == 2

    @pytest.mark.asyncio
    async def test_search_files(self, client):
        """Test GET /files/search endpoint"""
        user_id = "test-user-123"
        query = "test document"

        google_search_results = {
            "files": [
                {
                    "id": "search-result-1",
                    "name": "Test Document.pdf",
                    "mimeType": "application/pdf",
                    "size": "1024",
                    "createdTime": "2024-01-01T10:00:00Z",
                    "modifiedTime": "2024-01-01T10:00:00Z",
                }
            ]
        }

        with (
            patch(
                "services.office_service.core.token_manager.TokenManager.get_user_token"
            ) as mock_get_token,
            patch(
                "services.office_service.core.cache_manager.CacheManager.get_from_cache",
                return_value=None,
            ),
            patch(
                "services.office_service.core.cache_manager.CacheManager.set_to_cache"
            ),
            patch("httpx.AsyncClient.request") as mock_request,
        ):

            mock_get_token.side_effect = ["google-token", "microsoft-token"]

            # Google response
            mock_request.return_value = MagicMock(
                status_code=200,
                json=lambda: google_search_results,
                raise_for_status=lambda: None,
            )

            response = client.get(f"/files/search?user_id={user_id}&q={query}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_file_by_id(self, client):
        """Test GET /files/{file_id} endpoint"""
        user_id = "test-user-123"
        file_id = "google:drive-file-123"

        google_file = {
            "id": "drive-file-123",
            "name": "Important Document.pdf",
            "mimeType": "application/pdf",
            "size": "2048",
            "createdTime": "2024-01-01T10:00:00Z",
            "modifiedTime": "2024-01-01T10:00:00Z",
            "webViewLink": "https://drive.google.com/file/d/abc123",
        }

        with (
            patch(
                "services.office_service.core.token_manager.TokenManager.get_user_token",
                return_value="google-token",
            ),
            patch(
                "services.office_service.core.cache_manager.CacheManager.get_from_cache",
                return_value=None,
            ),
            patch(
                "services.office_service.core.cache_manager.CacheManager.set_to_cache"
            ),
            patch("httpx.AsyncClient.request") as mock_request,
        ):

            mock_request.return_value = MagicMock(
                status_code=200, json=lambda: google_file, raise_for_status=lambda: None
            )

            response = client.get(f"/files/{file_id}?user_id={user_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["id"] == file_id
            assert data["data"]["provider"] == "google"


class TestErrorScenarios:
    """Integration tests for error scenarios"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_missing_user_id(self, client):
        """Test endpoints without required user_id parameter"""
        response = client.get("/email/messages")
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_invalid_provider_in_message_id(self, client):
        """Test endpoint with invalid provider in composite ID"""
        user_id = "test-user-123"
        invalid_message_id = "invalid:message-123"

        response = client.get(f"/email/messages/{invalid_message_id}?user_id={user_id}")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_provider_api_error_handling(self, client):
        """Test how provider API errors are handled"""
        user_id = "test-user-123"

        with (
            patch(
                "services.office_service.core.token_manager.TokenManager.get_user_token",
                return_value="token",
            ),
            patch("httpx.AsyncClient.request") as mock_request,
        ):

            # Simulate provider API error
            from httpx import HTTPStatusError

            error_response = MagicMock()
            error_response.status_code = 429
            error_response.text = "Rate limit exceeded"
            error_response.headers = {"Retry-After": "3600"}

            mock_request.side_effect = HTTPStatusError(
                "HTTP 429", request=MagicMock(), response=error_response
            )
            error_response.raise_for_status.side_effect = HTTPStatusError(
                "HTTP 429", request=MagicMock(), response=error_response
            )

            response = client.get(f"/email/messages?user_id={user_id}")

            assert response.status_code == 429
            data = response.json()
            assert data["type"] == "provider_error"

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, client):
        """Test authentication error handling"""
        user_id = "test-user-123"

        with patch(
            "services.office_service.core.token_manager.TokenManager.get_user_token"
        ) as mock_get_token:
            from services.office_service.core.exceptions import TokenError

            mock_get_token.side_effect = TokenError(
                message="Token not found", user_id=user_id, provider=Provider.GOOGLE
            )

            response = client.get(f"/email/messages?user_id={user_id}")

            assert response.status_code == 401
            data = response.json()
            assert data["type"] == "auth_error"


class TestCachingBehavior:
    """Integration tests for caching behavior"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_cache_hit_on_repeated_requests(self, client):
        """Test that repeated requests hit the cache"""
        user_id = "test-user-123"

        cached_data = {
            "items": [{"id": "cached-message", "subject": "Cached Email"}],
            "total_count": 1,
            "has_more": False,
        }

        with (
            patch(
                "services.office_service.core.token_manager.TokenManager.get_user_token"
            ),
            patch(
                "services.office_service.core.cache_manager.CacheManager.get_from_cache",
                return_value=cached_data,
            ),
            patch(
                "services.office_service.core.cache_manager.CacheManager.set_to_cache"
            ),
            patch("httpx.AsyncClient.request") as mock_request,
        ):

            response = client.get(f"/email/messages?user_id={user_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["cache_hit"] is True

            # HTTP request should not be called since we hit cache
            mock_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_makes_api_calls(self, client):
        """Test that cache miss results in API calls"""
        user_id = "test-user-123"

        api_response = {
            "messages": [
                {
                    "id": "fresh-message",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Fresh Email"},
                            {"name": "From", "value": "sender@gmail.com"},
                            {
                                "name": "Date",
                                "value": "Thu, 01 Jan 2024 12:00:00 +0000",
                            },
                        ],
                        "body": {"data": "VGVzdA=="},
                    },
                    "snippet": "Fresh content",
                }
            ]
        }

        with (
            patch(
                "services.office_service.core.token_manager.TokenManager.get_user_token"
            ) as mock_get_token,
            patch(
                "services.office_service.core.cache_manager.CacheManager.get_from_cache",
                return_value=None,
            ),
            patch(
                "services.office_service.core.cache_manager.CacheManager.set_to_cache"
            ) as mock_set_cache,
            patch("httpx.AsyncClient.request") as mock_request,
        ):

            mock_get_token.side_effect = ["google-token", "microsoft-token"]
            mock_request.side_effect = [
                MagicMock(
                    status_code=200,
                    json=lambda: api_response,
                    raise_for_status=lambda: None,
                ),
                MagicMock(
                    status_code=200,
                    json=lambda: {"value": []},
                    raise_for_status=lambda: None,
                ),
            ]

            response = client.get(f"/email/messages?user_id={user_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["cache_hit"] is False

            # Should have made API calls and cached the result
            assert mock_request.call_count == 2
            mock_set_cache.assert_called_once()
