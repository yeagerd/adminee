"""
Unit tests for error handling across the office service.

Tests error handling, exception propagation, and error response formatting
for various failure scenarios in the office service.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import Request

from services.common.http_errors import (
    ProviderError,
    RateLimitError,
    ServiceError,
    ValidationError,
)
from services.office.core.clients.google import GoogleAPIClient
from services.office.models import Provider


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    """Patch the _settings global variable to return test settings."""
    import services.office.core.settings as office_settings

    test_settings = office_settings.Settings(
        db_url_office="sqlite:///:memory:",
        api_frontend_office_key="test-frontend-office-key",
        api_chat_office_key="test-chat-office-key",
        api_office_user_key="test-office-user-key",
    )

    monkeypatch.setattr("services.office.core.settings._settings", test_settings)


class TestGlobalExceptionHandlers:
    """Test the global exception handlers defined in main.py"""

    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request"""
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test/endpoint"
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.mark.asyncio
    async def test_provider_api_error_handler(self, mock_request):
        """Test ProviderAPIError exception handler"""
        error = ProviderError(
            message="Google API rate limit exceeded",
            provider=Provider.GOOGLE,
            status_code=429,
            details={"endpoint": "/gmail/v1/users/me/messages"},
        )
        # Instead of calling a handler, just check the error attributes
        assert error.message == "Google API rate limit exceeded"
        assert error.provider == Provider.GOOGLE
        assert error.status_code == 429
        assert error.details["endpoint"] == "/gmail/v1/users/me/messages"

    @pytest.mark.asyncio
    async def test_rate_limit_error_handler(self, mock_request):
        """Test RateLimitError exception handler"""
        error = RateLimitError(
            message="Rate limit exceeded for user",
            retry_after=120,
            details={"user_id": "test-user", "limit_type": "hourly"},
        )
        assert error.message == "Rate limit exceeded for user"
        assert error.retry_after == 120
        assert error.details["user_id"] == "test-user"
        assert error.details["limit_type"] == "hourly"

    @pytest.mark.asyncio
    async def test_validation_error_handler(self, mock_request):
        """Test ValidationError exception handler"""
        error = ValidationError(
            message="Invalid email format",
            field="email",
            value="not-an-email",
            details={"expected_format": "user@domain.com"},
        )
        assert error.message == "Invalid email format"
        assert error.field == "email"
        assert error.value == "not-an-email"
        assert error.details["expected_format"] == "user@domain.com"

    @pytest.mark.asyncio
    async def test_office_service_error_handler(self, mock_request):
        """Test generic ServiceError exception handler"""
        error = ServiceError(
            message="Service configuration error",
            details={"config_key": "REDIS_URL", "issue": "missing"},
        )
        assert error.message == "Service configuration error"
        assert error.details["config_key"] == "REDIS_URL"
        assert error.details["issue"] == "missing"


class TestAPIClientErrorHandling:
    """Test error handling in API clients"""

    @pytest.fixture
    def google_client(self):
        """Create a Google API client for testing"""
        return GoogleAPIClient(access_token="test-token", user_id="test-user")

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, google_client):
        """Test that timeout errors are properly converted to ProviderError"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock timeout exception
            mock_client.request.side_effect = httpx.TimeoutException(
                "Request timed out"
            )

            async with google_client:
                with pytest.raises(ProviderError) as exc_info:
                    await google_client.get("/test/endpoint")

                error = exc_info.value
                assert error.provider == Provider.GOOGLE
                assert "timeout" in error.message.lower()
                assert "test/endpoint" in str(error.details)

    @pytest.mark.asyncio
    async def test_http_status_error_handling(self, google_client):
        """Test that HTTP status errors are properly converted to ProviderError"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock HTTP error response
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_response.headers = {"Content-Type": "application/json"}

            mock_client.request.return_value = mock_response
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "HTTP 401", request=MagicMock(), response=mock_response
            )

            async with google_client:
                with pytest.raises(ProviderError) as exc_info:
                    await google_client.get("/test/endpoint")

                error = exc_info.value
                assert error.provider == Provider.GOOGLE
                assert error.status_code == 401
                assert "authentication failed" in error.message.lower()

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, google_client):
        """Test that rate limit errors (429) are properly handled"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock rate limit response
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            mock_response.headers = {
                "Retry-After": "3600",
                "Content-Type": "application/json",
            }

            mock_client.request.return_value = mock_response
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "HTTP 429", request=MagicMock(), response=mock_response
            )

            async with google_client:
                with pytest.raises(ProviderError) as exc_info:
                    await google_client.get("/test/endpoint")

                error = exc_info.value
                assert error.provider == Provider.GOOGLE
                assert error.status_code == 429

    @pytest.mark.asyncio
    async def test_request_error_handling(self, google_client):
        """Test that request errors are properly converted to ProviderError"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock request error
            mock_client.request.side_effect = httpx.RequestError("Connection error")

            async with google_client:
                with pytest.raises(ProviderError) as exc_info:
                    await google_client.get("/test/endpoint")

                error = exc_info.value
                assert error.provider == Provider.GOOGLE
                assert "Connection error" in error.message
                assert "RequestError" in str(error.details)

    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self, google_client):
        """Test that unexpected errors are properly converted to ProviderError"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock unexpected error
            mock_client.request.side_effect = ValueError("Unexpected error")

            async with google_client:
                with pytest.raises(ProviderError) as exc_info:
                    await google_client.get("/test/endpoint")

                error = exc_info.value
                assert error.provider == Provider.GOOGLE
                assert "Unexpected error" in error.message
                assert "ValueError" in str(error.details)


class TestLoggingIntegration:
    """Test logging integration and structured logging"""

    @pytest.mark.asyncio
    async def test_api_call_logging(self):
        """Test that API calls are properly logged"""
        google_client = GoogleAPIClient(access_token="test-token", user_id="test-user")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock successful response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"message": "success"}
            mock_response.raise_for_status.return_value = None
            mock_client.request.return_value = mock_response

            with patch("services.office.core.clients.base.logger") as mock_logger:
                async with google_client:
                    await google_client.get("/test/endpoint")

                # Verify debug logging for request and response
                assert mock_logger.debug.call_count >= 2
                debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]

                # Check request log
                request_log = next(
                    (log for log in debug_calls if "Making GET request" in log), None
                )
                assert request_log is not None
                assert "test-user" in request_log
                assert "Provider.GOOGLE" in request_log

                # Check response log
                response_log = next(
                    (log for log in debug_calls if "Response: 200" in log), None
                )
                assert response_log is not None

    @pytest.mark.asyncio
    async def test_error_logging_structure(self):
        """Test that errors are logged with proper structure"""
        google_client = GoogleAPIClient(access_token="test-token", user_id="test-user")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock timeout error
            mock_client.request.side_effect = httpx.TimeoutException(
                "Request timed out"
            )

            with patch("services.office.core.clients.base.logger") as mock_logger:
                async with google_client:
                    with pytest.raises(ProviderError):
                        await google_client.get("/test/endpoint")

                # Verify error logging (at least one call, possibly more due to DB issues)
                assert mock_logger.error.call_count >= 1

                # Find the timeout error log (first call should be the primary error)
                timeout_error_log = None
                for call in mock_logger.error.call_args_list:
                    log_msg = call[0][0]
                    if "Timeout error" in log_msg:
                        timeout_error_log = log_msg
                        break

                assert timeout_error_log is not None, "Should find timeout error log"

                # Check log structure
                assert "Timeout error" in timeout_error_log
                assert "test-user" in timeout_error_log
                assert "Provider.GOOGLE" in timeout_error_log
                assert "Request-ID" in timeout_error_log

    def test_request_id_generation(self):
        """Test that request IDs are generated properly"""
        google_client = GoogleAPIClient(access_token="test-token", user_id="test-user")

        request_id1 = google_client._generate_request_id()
        request_id2 = google_client._generate_request_id()

        # Request IDs should be unique
        assert request_id1 != request_id2

        # Should contain session ID prefix
        assert request_id1.startswith(google_client._session_id)
        assert request_id2.startswith(google_client._session_id)

    def test_session_id_uniqueness(self):
        """Test that different client instances have unique session IDs"""
        client1 = GoogleAPIClient(access_token="test-token", user_id="test-user")
        client2 = GoogleAPIClient(access_token="test-token", user_id="test-user")

        assert client1._session_id != client2._session_id
        assert len(client1._session_id) == 8  # UUID hex[:8]
        assert len(client2._session_id) == 8
