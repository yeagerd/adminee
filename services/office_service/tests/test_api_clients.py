"""
Unit tests for API clients and factory.

Tests the base API client, provider-specific clients (Google, Microsoft),
and API client factory with mocked HTTP responses and error handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.office_service.core.api_client_factory import APIClientFactory
from services.office_service.core.clients.base import BaseAPIClient
from services.office_service.core.clients.google import GoogleAPIClient
from services.office_service.core.clients.microsoft import MicrosoftAPIClient
from services.office_service.core.exceptions import ProviderAPIError
from services.office_service.core.token_manager import TokenData
from services.office_service.models import Provider


class MockAPIClient(BaseAPIClient):
    """Mock API client for testing base functionality."""

    def _get_default_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _get_base_url(self):
        return "https://api.example.com"


class TestBaseAPIClient:
    """Tests for BaseAPIClient class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock API client for testing."""
        return MockAPIClient("test_token", "test_user", Provider.GOOGLE)

    @pytest.mark.asyncio
    async def test_client_initialization(self, mock_client):
        """Test client initialization."""
        assert mock_client.access_token == "test_token"
        assert mock_client.user_id == "test_user"
        assert mock_client.provider == Provider.GOOGLE
        assert mock_client.http_client is None

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_client):
        """Test async context manager functionality."""
        async with mock_client:
            assert mock_client.http_client is not None
            assert isinstance(mock_client.http_client, httpx.AsyncClient)

        # Client should be closed after context
        assert mock_client.http_client.is_closed

    @pytest.mark.asyncio
    async def test_get_request_success(self, mock_client):
        """Test successful GET request."""
        mock_response_data = {"result": "success", "data": [1, 2, 3]}

        async with mock_client:
            with patch.object(
                mock_client.http_client, "request", new_callable=AsyncMock
            ) as mock_request:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status.return_value = None
                mock_request.return_value = mock_response

                response = await mock_client.get("/test/endpoint", params={"q": "test"})

                assert response.status_code == 200
                assert response.json() == mock_response_data
                mock_request.assert_called_once()

                # Verify request parameters
                call_args = mock_request.call_args
                assert call_args[1]["method"] == "GET"
                assert call_args[1]["url"] == "https://api.example.com/test/endpoint"
                assert call_args[1]["params"] == {"q": "test"}

    @pytest.mark.asyncio
    async def test_post_request_success(self, mock_client):
        """Test successful POST request."""
        request_data = {"name": "test", "value": 123}
        mock_response_data = {"id": "created_123", "status": "created"}

        async with mock_client:
            with patch.object(
                mock_client.http_client, "request", new_callable=AsyncMock
            ) as mock_request:
                mock_response = MagicMock()
                mock_response.status_code = 201
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status.return_value = None
                mock_request.return_value = mock_response

                response = await mock_client.post(
                    "/test/create", json_data=request_data
                )

                assert response.status_code == 201
                assert response.json() == mock_response_data

                # Verify request parameters
                call_args = mock_request.call_args
                assert call_args[1]["method"] == "POST"
                assert call_args[1]["json"] == request_data

    @pytest.mark.asyncio
    async def test_request_headers(self, mock_client):
        """Test that request includes proper headers."""
        async with mock_client:
            with patch.object(
                mock_client.http_client, "request", new_callable=AsyncMock
            ) as mock_request:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.raise_for_status.return_value = None
                mock_request.return_value = mock_response

                await mock_client.get("/test")

                call_args = mock_request.call_args
                headers = call_args[1]["headers"]
                assert "Authorization" in headers
                assert headers["Authorization"] == "Bearer test_token"
                assert headers["Content-Type"] == "application/json"
                assert "X-Request-ID" in headers

    @pytest.mark.asyncio
    async def test_http_error_handling(self, mock_client):
        """Test HTTP error handling."""
        async with mock_client:
            with patch.object(
                mock_client.http_client, "request", new_callable=AsyncMock
            ) as mock_request:
                mock_response = MagicMock()
                mock_response.status_code = 404
                mock_response.text = "Not Found"
                mock_response.headers = {}
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Not Found", request=MagicMock(), response=mock_response
                )
                mock_request.return_value = mock_response

                with pytest.raises(ProviderAPIError) as exc_info:
                    await mock_client.get("/nonexistent")

                # Verify the ProviderAPIError contains the expected details
                error = exc_info.value
                assert error.provider == Provider.GOOGLE
                assert error.status_code == 404

    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_client):
        """Test timeout error handling."""
        async with mock_client:
            with patch.object(
                mock_client.http_client, "request", new_callable=AsyncMock
            ) as mock_request:
                mock_request.side_effect = httpx.TimeoutException("Request timeout")

                with pytest.raises(ProviderAPIError) as exc_info:
                    await mock_client.get("/slow-endpoint")

                # Verify the ProviderAPIError contains the expected details
                error = exc_info.value
                assert error.provider == Provider.GOOGLE
                assert "timeout" in error.message.lower()

    @pytest.mark.asyncio
    async def test_network_error_handling(self, mock_client):
        """Test network error handling."""
        async with mock_client:
            with patch.object(
                mock_client.http_client, "request", new_callable=AsyncMock
            ) as mock_request:
                mock_request.side_effect = httpx.NetworkError("Connection failed")

                with pytest.raises(ProviderAPIError) as exc_info:
                    await mock_client.get("/unreachable")

                # Verify the ProviderAPIError contains the expected details
                error = exc_info.value
                assert error.provider == Provider.GOOGLE
                assert (
                    "network" in error.message.lower()
                    or "connection" in error.message.lower()
                )

    @pytest.mark.asyncio
    async def test_client_without_context_manager(self, mock_client):
        """Test that requests fail without context manager."""
        with pytest.raises(RuntimeError, match="HTTP client not initialized"):
            await mock_client.get("/test")


class TestGoogleAPIClient:
    """Tests for GoogleAPIClient class."""

    @pytest.fixture
    def google_client(self):
        """Create a Google API client for testing."""
        return GoogleAPIClient("google_token", "test_user")

    @pytest.mark.asyncio
    async def test_google_client_initialization(self, google_client):
        """Test Google client initialization."""
        assert google_client.access_token == "google_token"
        assert google_client.user_id == "test_user"
        assert google_client.provider == Provider.GOOGLE

    @pytest.mark.asyncio
    async def test_google_headers(self, google_client):
        """Test Google API headers."""
        headers = google_client._get_default_headers()

        assert headers["Authorization"] == "Bearer google_token"
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"
        assert "BrieflyOfficeService" in headers["User-Agent"]

    @pytest.mark.asyncio
    async def test_google_base_url(self, google_client):
        """Test Google API base URL."""
        assert google_client._get_base_url() == "https://www.googleapis.com"

    @pytest.mark.asyncio
    async def test_get_messages(self, google_client):
        """Test Gmail get messages API call."""
        mock_response_data = {
            "messages": [
                {"id": "msg1", "threadId": "thread1"},
                {"id": "msg2", "threadId": "thread2"},
            ],
            "nextPageToken": "next_token",
        }

        async with google_client:
            with patch.object(
                google_client.http_client, "request", new_callable=AsyncMock
            ) as mock_request:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status.return_value = None
                mock_request.return_value = mock_response

                result = await google_client.get_messages(
                    max_results=10, query="is:unread"
                )

                assert result == mock_response_data

                # Verify request parameters
                call_args = mock_request.call_args
                assert "/gmail/v1/users/me/messages" in call_args[1]["url"]
                params = call_args[1]["params"]
                assert params["maxResults"] == 10
                assert params["q"] == "is:unread"

    @pytest.mark.asyncio
    async def test_get_message(self, google_client):
        """Test Gmail get message API call."""
        mock_response_data = {
            "id": "msg123",
            "payload": {"headers": [{"name": "Subject", "value": "Test Subject"}]},
        }

        async with google_client:
            with patch.object(
                google_client.http_client, "request", new_callable=AsyncMock
            ) as mock_request:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status.return_value = None
                mock_request.return_value = mock_response

                result = await google_client.get_message("msg123", format="full")

                assert result == mock_response_data

                # Verify request parameters
                call_args = mock_request.call_args
                assert "/gmail/v1/users/me/messages/msg123" in call_args[1]["url"]
                assert call_args[1]["params"]["format"] == "full"

    @pytest.mark.asyncio
    async def test_get_events(self, google_client):
        """Test Google Calendar get events API call."""
        mock_response_data = {
            "items": [
                {"id": "event1", "summary": "Meeting 1"},
                {"id": "event2", "summary": "Meeting 2"},
            ],
            "nextPageToken": "next_events_token",
        }

        async with google_client:
            with patch.object(
                google_client.http_client, "request", new_callable=AsyncMock
            ) as mock_request:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status.return_value = None
                mock_request.return_value = mock_response

                result = await google_client.get_events(
                    calendar_id="primary",
                    time_min="2023-01-01T00:00:00Z",
                    max_results=50,
                )

                assert result == mock_response_data

                # Verify request parameters
                call_args = mock_request.call_args
                assert "/calendar/v3/calendars/primary/events" in call_args[1]["url"]
                params = call_args[1]["params"]
                assert params["maxResults"] == 50
                assert params["timeMin"] == "2023-01-01T00:00:00Z"
                assert params["singleEvents"] is True

    @pytest.mark.asyncio
    async def test_get_files(self, google_client):
        """Test Google Drive get files API call."""
        mock_response_data = {
            "files": [
                {"id": "file1", "name": "document1.pdf"},
                {"id": "file2", "name": "document2.docx"},
            ],
            "nextPageToken": "next_files_token",
        }

        async with google_client:
            with patch.object(
                google_client.http_client, "request", new_callable=AsyncMock
            ) as mock_request:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status.return_value = None
                mock_request.return_value = mock_response

                result = await google_client.get_files(
                    page_size=20, query="mimeType='application/pdf'"
                )

                assert result == mock_response_data

                # Verify request parameters
                call_args = mock_request.call_args
                assert "/drive/v3/files" in call_args[1]["url"]
                params = call_args[1]["params"]
                assert params["pageSize"] == 20
                assert params["q"] == "mimeType='application/pdf'"


class TestMicrosoftAPIClient:
    """Tests for MicrosoftAPIClient class."""

    @pytest.fixture
    def microsoft_client(self):
        """Create a Microsoft API client for testing."""
        return MicrosoftAPIClient("microsoft_token", "test_user")

    @pytest.mark.asyncio
    async def test_microsoft_client_initialization(self, microsoft_client):
        """Test Microsoft client initialization."""
        assert microsoft_client.access_token == "microsoft_token"
        assert microsoft_client.user_id == "test_user"
        assert microsoft_client.provider == Provider.MICROSOFT

    @pytest.mark.asyncio
    async def test_microsoft_headers(self, microsoft_client):
        """Test Microsoft Graph API headers."""
        headers = microsoft_client._get_default_headers()

        assert headers["Authorization"] == "Bearer microsoft_token"
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_microsoft_base_url(self, microsoft_client):
        """Test Microsoft Graph API base URL."""
        assert microsoft_client._get_base_url() == "https://graph.microsoft.com/v1.0"

    @pytest.mark.asyncio
    async def test_get_messages(self, microsoft_client):
        """Test Microsoft Graph get messages API call."""
        mock_response_data = {
            "value": [
                {"id": "msg1", "subject": "Email 1"},
                {"id": "msg2", "subject": "Email 2"},
            ],
            "@odata.nextLink": "next_link_url",
        }

        async with microsoft_client:
            with patch.object(
                microsoft_client.http_client, "request", new_callable=AsyncMock
            ) as mock_request:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status.return_value = None
                mock_request.return_value = mock_response

                result = await microsoft_client.get_messages(
                    top=25, filter="isRead eq false"
                )

                assert result == mock_response_data

                # Verify request parameters
                call_args = mock_request.call_args
                assert "/v1.0/me/messages" in call_args[1]["url"]
                params = call_args[1]["params"]
                assert params["$top"] == 25
                assert params["$filter"] == "isRead eq false"

    @pytest.mark.asyncio
    async def test_get_events(self, microsoft_client):
        """Test Microsoft Graph get events API call."""
        mock_response_data = {
            "value": [
                {"id": "event1", "subject": "Meeting 1"},
                {"id": "event2", "subject": "Meeting 2"},
            ]
        }

        async with microsoft_client:
            with patch.object(
                microsoft_client.http_client, "request", new_callable=AsyncMock
            ) as mock_request:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status.return_value = None
                mock_request.return_value = mock_response

                result = await microsoft_client.get_events(
                    top=10, start_time="2023-01-01T00:00:00Z"
                )

                assert result == mock_response_data

                # Verify request parameters
                call_args = mock_request.call_args
                assert "/v1.0/me/events" in call_args[1]["url"]
                params = call_args[1]["params"]
                assert params["$top"] == 10
                assert params["$filter"] == "start/dateTime ge '2023-01-01T00:00:00Z'"


class TestAPIClientFactory:
    """Tests for APIClientFactory class."""

    @pytest.fixture
    def mock_token_data(self):
        """Mock token data for testing."""
        return TokenData(
            access_token="test_access_token",
            provider="google",
            user_id="test_user",
            scopes=["read", "write"],
        )

    @pytest.mark.asyncio
    async def test_create_google_client_success(self, mock_token_data):
        """Test successful Google client creation."""
        with patch(
            "services.office_service.core.api_client_factory.TokenManager"
        ) as MockTokenManager:
            mock_token_manager = AsyncMock()
            mock_token_manager.__aenter__.return_value = mock_token_manager
            mock_token_manager.get_user_token.return_value = mock_token_data
            MockTokenManager.return_value = mock_token_manager

            factory = APIClientFactory()
            client = await factory.create_client("test_user", "google")

            assert client is not None
            assert isinstance(client, GoogleAPIClient)
            assert client.access_token == "test_access_token"
            assert client.user_id == "test_user"
            assert client.provider == Provider.GOOGLE

    @pytest.mark.asyncio
    async def test_create_microsoft_client_success(self, mock_token_data):
        """Test successful Microsoft client creation."""
        mock_token_data.provider = "microsoft"

        with patch(
            "services.office_service.core.api_client_factory.TokenManager"
        ) as MockTokenManager:
            mock_token_manager = AsyncMock()
            mock_token_manager.__aenter__.return_value = mock_token_manager
            mock_token_manager.get_user_token.return_value = mock_token_data
            MockTokenManager.return_value = mock_token_manager

            factory = APIClientFactory()
            client = await factory.create_client("test_user", "microsoft")

            assert client is not None
            assert isinstance(client, MicrosoftAPIClient)
            assert client.access_token == "test_access_token"
            assert client.user_id == "test_user"
            assert client.provider == Provider.MICROSOFT

    @pytest.mark.asyncio
    async def test_create_client_with_enum_provider(self, mock_token_data):
        """Test client creation with Provider enum."""
        with patch(
            "services.office_service.core.api_client_factory.TokenManager"
        ) as MockTokenManager:
            mock_token_manager = AsyncMock()
            mock_token_manager.__aenter__.return_value = mock_token_manager
            mock_token_manager.get_user_token.return_value = mock_token_data
            MockTokenManager.return_value = mock_token_manager

            factory = APIClientFactory()
            client = await factory.create_client("test_user", Provider.GOOGLE)

            assert client is not None
            assert isinstance(client, GoogleAPIClient)

    @pytest.mark.asyncio
    async def test_create_client_invalid_provider(self):
        """Test client creation with invalid provider."""
        factory = APIClientFactory()

        with pytest.raises(ValueError, match="Invalid provider"):
            await factory.create_client("test_user", "invalid_provider")

    @pytest.mark.asyncio
    async def test_create_client_no_token(self):
        """Test client creation when no token is available."""
        with patch(
            "services.office_service.core.api_client_factory.TokenManager"
        ) as MockTokenManager:
            mock_token_manager = AsyncMock()
            mock_token_manager.__aenter__.return_value = mock_token_manager
            mock_token_manager.get_user_token.return_value = None  # No token
            MockTokenManager.return_value = mock_token_manager

            factory = APIClientFactory()
            client = await factory.create_client("test_user", "google")

            assert client is None

    @pytest.mark.asyncio
    async def test_create_client_with_custom_scopes(self, mock_token_data):
        """Test client creation with custom scopes."""
        custom_scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

        with patch(
            "services.office_service.core.api_client_factory.TokenManager"
        ) as MockTokenManager:
            mock_token_manager = AsyncMock()
            mock_token_manager.__aenter__.return_value = mock_token_manager
            mock_token_manager.get_user_token.return_value = mock_token_data
            MockTokenManager.return_value = mock_token_manager

            factory = APIClientFactory()
            client = await factory.create_client("test_user", "google", custom_scopes)

            assert client is not None
            # Verify that custom scopes were passed to token manager
            mock_token_manager.get_user_token.assert_called_with(
                "test_user", "google", custom_scopes
            )

    @pytest.mark.asyncio
    async def test_convenience_methods(self, mock_token_data):
        """Test convenience methods for specific providers."""
        with patch(
            "services.office_service.core.api_client_factory.TokenManager"
        ) as MockTokenManager:
            mock_token_manager = AsyncMock()
            mock_token_manager.__aenter__.return_value = mock_token_manager
            mock_token_manager.get_user_token.return_value = mock_token_data
            MockTokenManager.return_value = mock_token_manager

            factory = APIClientFactory()

            # Test Google convenience method
            google_client = await factory.create_google_client("test_user")
            assert isinstance(google_client, GoogleAPIClient)

            # Test Microsoft convenience method
            mock_token_data.provider = "microsoft"
            microsoft_client = await factory.create_microsoft_client("test_user")
            assert isinstance(microsoft_client, MicrosoftAPIClient)

    @pytest.mark.asyncio
    async def test_create_all_clients(self, mock_token_data):
        """Test creating clients for all providers."""
        with patch(
            "services.office_service.core.api_client_factory.TokenManager"
        ) as MockTokenManager:
            mock_token_manager = AsyncMock()
            mock_token_manager.__aenter__.return_value = mock_token_manager
            mock_token_manager.get_user_token.return_value = mock_token_data
            MockTokenManager.return_value = mock_token_manager

            factory = APIClientFactory()
            clients = await factory.create_all_clients("test_user")

            assert Provider.GOOGLE in clients
            assert Provider.MICROSOFT in clients
            assert isinstance(clients[Provider.GOOGLE], GoogleAPIClient)
            assert isinstance(clients[Provider.MICROSOFT], MicrosoftAPIClient)

    @pytest.mark.asyncio
    async def test_get_default_scopes(self):
        """Test default scopes for providers."""
        factory = APIClientFactory()

        google_scopes = factory._get_default_scopes(Provider.GOOGLE)
        assert "https://www.googleapis.com/auth/gmail.readonly" in google_scopes
        assert "https://www.googleapis.com/auth/calendar" in google_scopes

        microsoft_scopes = factory._get_default_scopes(Provider.MICROSOFT)
        assert "https://graph.microsoft.com/Mail.Read" in microsoft_scopes
        assert "https://graph.microsoft.com/Calendars.ReadWrite" in microsoft_scopes

    @pytest.mark.asyncio
    async def test_factory_with_provided_token_manager(self, mock_token_data):
        """Test factory with provided token manager."""
        mock_token_manager = AsyncMock()
        mock_token_manager.__aenter__.return_value = mock_token_manager
        mock_token_manager.get_user_token.return_value = mock_token_data

        factory = APIClientFactory(token_manager=mock_token_manager)
        client = await factory.create_client("test_user", "google")

        assert client is not None
        # Should use the provided token manager, not create a new one
        mock_token_manager.get_user_token.assert_called_once()

    def test_get_supported_providers(self):
        """Test getting supported providers."""
        factory = APIClientFactory()
        providers = factory.get_supported_providers()

        assert Provider.GOOGLE in providers
        assert Provider.MICROSOFT in providers
        assert len(providers) == 2
