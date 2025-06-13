# Set required environment variables before any imports
import os
os.environ.setdefault("DB_URL_OFFICE", "sqlite:///test.db")
os.environ.setdefault("API_OFFICE_USER_KEY", "test-api-key")

"""
Unit tests for error handling across the office service.

Tests error handling, exception propagation, and error response formatting
for various failure scenarios in the office service.
"""

import json

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from services.office_service.app.main import (
    office_service_error_handler,
    provider_api_error_handler,
    rate_limit_error_handler,
    validation_error_handler,
)
from services.office_service.core.clients.google import GoogleAPIClient
from services.office_service.core.exceptions import (
    OfficeServiceError,
    ProviderAPIError,
    RateLimitError,
    ValidationError,
)
from services.office_service.models import Provider


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
        # Create a ProviderAPIError
        error = ProviderAPIError(
            message="Google API rate limit exceeded",
            provider=Provider.GOOGLE,
            status_code=429,
            retry_after=60,
            details={"endpoint": "/gmail/v1/users/me/messages"},
        )

        with patch("services.office_service.app.main.logger") as mock_logger:
            # Call the handler
            response = await provider_api_error_handler(mock_request, error)

        # Verify response
        assert isinstance(response, JSONResponse)
        assert (
            response.status_code == 429
        )  # Rate limited for provider errors with retry_after

        # Parse response content
        response_data = json.loads(response.body.decode())
        assert response_data["type"] == "provider_error"
        assert "Google API rate limit exceeded" in response_data["message"]
        assert "request_id" in response_data
        assert response_data["provider"] == "google"
        assert response_data["details"]["endpoint"] == "/gmail/v1/users/me/messages"
        assert response_data["retry_after"] == 60

        # Verify logging
        mock_logger.error.assert_called_once()
        log_call = mock_logger.error.call_args[0][0]
        assert "Provider API error occurred" in log_call

    @pytest.mark.asyncio
    async def test_rate_limit_error_handler(self, mock_request):
        """Test RateLimitError exception handler"""
        error = RateLimitError(
            message="Rate limit exceeded for user",
            retry_after=120,
            details={"user_id": "test-user", "limit_type": "hourly"},
        )

        with patch("services.office_service.app.main.logger") as mock_logger:
            response = await rate_limit_error_handler(mock_request, error)

        # Verify response
        assert isinstance(response, JSONResponse)
        assert response.status_code == 429  # Too Many Requests

        # Parse response content
        response_data = json.loads(response.body.decode())
        assert response_data["type"] == "rate_limit_error"
        assert "Rate limit exceeded" in response_data["message"]
        assert response_data["retry_after"] == 120

        # Verify retry-after header
        assert response.headers["Retry-After"] == "120"

        # Verify logging
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_validation_error_handler(self, mock_request):
        """Test ValidationError exception handler"""
        # Create our custom ValidationError (not Pydantic's)
        error = ValidationError(
            message="Invalid email format",
            field="email",
            value="not-an-email",
            details={"expected_format": "user@domain.com"},
        )

        with patch("services.office_service.app.main.logger") as mock_logger:
            response = await validation_error_handler(mock_request, error)

        # Verify response
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400  # Bad Request

        # Parse response content
        response_data = json.loads(response.body.decode())
        assert response_data["type"] == "validation_error"
        assert "Invalid email format" in response_data["message"]
        assert "request_id" in response_data
        assert response_data["details"]["expected_format"] == "user@domain.com"

        # Verify logging
        mock_logger.warning.assert_called_once()
        log_call = mock_logger.warning.call_args
        log_extra = log_call[1]["extra"]
        assert log_extra["field"] == "email"
        assert log_extra["value"] == "not-an-email"

    @pytest.mark.asyncio
    async def test_office_service_error_handler(self, mock_request):
        """Test generic OfficeServiceError exception handler"""
        error = OfficeServiceError(
            message="Service configuration error",
            details={"config_key": "REDIS_URL", "issue": "missing"},
        )

        with patch("services.office_service.app.main.logger") as mock_logger:
            response = await office_service_error_handler(mock_request, error)

        # Verify response
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500  # Internal Server Error

        # Parse response content
        response_data = json.loads(response.body.decode())
        assert response_data["type"] == "service_error"
        assert "Service configuration error" in response_data["message"]
        assert response_data["details"]["config_key"] == "REDIS_URL"

        # Verify logging
        mock_logger.error.assert_called_once()


class TestAPIClientErrorHandling:
    """Test error handling in API clients"""

    @pytest.fixture
    def google_client(self):
        """Create a Google API client for testing"""
        return GoogleAPIClient(access_token="test-token", user_id="test-user")

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, google_client):
        """Test that timeout errors are properly converted to ProviderAPIError"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock timeout exception
            mock_client.request.side_effect = httpx.TimeoutException(
                "Request timed out"
            )

            async with google_client:
                with pytest.raises(ProviderAPIError) as exc_info:
                    await google_client.get("/test/endpoint")

                error = exc_info.value
                assert error.provider == Provider.GOOGLE
                assert "timeout" in error.message.lower()
                assert "test/endpoint" in str(error.details)

    @pytest.mark.asyncio
    async def test_http_status_error_handling(self, google_client):
        """Test that HTTP status errors are properly converted to ProviderAPIError"""
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
                with pytest.raises(ProviderAPIError) as exc_info:
                    await google_client.get("/test/endpoint")

                error = exc_info.value
                assert error.provider == Provider.GOOGLE
                assert error.status_code == 401
                assert "authentication failed" in error.message.lower()
                assert error.response_body == "Unauthorized"

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
                with pytest.raises(ProviderAPIError) as exc_info:
                    await google_client.get("/test/endpoint")

                error = exc_info.value
                assert error.provider == Provider.GOOGLE
                assert error.status_code == 429
                assert error.retry_after == 3600
                assert "Rate limit exceeded" in error.response_body

    @pytest.mark.asyncio
    async def test_request_error_handling(self, google_client):
        """Test that request errors are properly converted to ProviderAPIError"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock request error
            mock_client.request.side_effect = httpx.RequestError("Connection error")

            async with google_client:
                with pytest.raises(ProviderAPIError) as exc_info:
                    await google_client.get("/test/endpoint")

                error = exc_info.value
                assert error.provider == Provider.GOOGLE
                assert "Connection error" in error.message
                assert "RequestError" in str(error.details)

    @pytest.mark.asyncio
    async def test_unexpected_error_handling(self, google_client):
        """Test that unexpected errors are properly converted to ProviderAPIError"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock unexpected error
            mock_client.request.side_effect = ValueError("Unexpected error")

            async with google_client:
                with pytest.raises(ProviderAPIError) as exc_info:
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

            with patch(
                "services.office_service.core.clients.base.logger"
            ) as mock_logger:
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

            with patch(
                "services.office_service.core.clients.base.logger"
            ) as mock_logger:
                async with google_client:
                    with pytest.raises(ProviderAPIError):
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
