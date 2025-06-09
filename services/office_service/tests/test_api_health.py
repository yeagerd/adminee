"""
Unit tests for health API endpoints.

Tests all health check endpoints with mocked dependencies to ensure
proper error handling and response formatting.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.office_service.api.health import (
    check_database_connection,
    check_redis_connection,
    check_service_connection,
    check_user_integration,
    router,
)
from services.office_service.core.token_manager import TokenData


@pytest.fixture
def app():
    """Create a test FastAPI app with health router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_token_data():
    """Create mock token data for tests."""
    return TokenData(
        access_token="mock_access_token",
        refresh_token="mock_refresh_token",
        provider="google",
        user_id="test_user_123",
        scopes=["https://www.googleapis.com/auth/userinfo.profile"],
        expires_at=datetime.now(timezone.utc),
    )


class TestHealthEndpoints:
    """Test cases for health check endpoints."""

    @patch("services.office_service.api.health.check_database_connection")
    @patch("services.office_service.api.health.check_redis_connection")
    @patch("services.office_service.api.health.check_service_connection")
    async def test_health_check_all_healthy(
        self, mock_service_check, mock_redis_check, mock_db_check, client
    ):
        """Test health check when all services are healthy."""
        # Mock all checks to return True
        mock_db_check.return_value = True
        mock_redis_check.return_value = True
        mock_service_check.return_value = True

        response = client.get("/health/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["database"] is True
        assert data["checks"]["redis"] is True
        assert data["checks"]["user_management_service"] is True
        assert "timestamp" in data
        assert "response_time_ms" in data
        assert "version" in data
        assert "service" in data

    @patch("services.office_service.api.health.check_database_connection")
    @patch("services.office_service.api.health.check_redis_connection")
    @patch("services.office_service.api.health.check_service_connection")
    async def test_health_check_partial_failure(
        self, mock_service_check, mock_redis_check, mock_db_check, client
    ):
        """Test health check when some services are unhealthy."""
        # Mock partial failure
        mock_db_check.return_value = True
        mock_redis_check.return_value = False
        mock_service_check.return_value = True

        response = client.get("/health/")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["database"] is True
        assert data["checks"]["redis"] is False
        assert data["checks"]["user_management_service"] is True

    @patch("services.office_service.api.health.check_database_connection")
    @patch("services.office_service.api.health.check_redis_connection")
    @patch("services.office_service.api.health.check_service_connection")
    async def test_health_check_all_failed(
        self, mock_service_check, mock_redis_check, mock_db_check, client
    ):
        """Test health check when all services are unhealthy."""
        # Mock all checks to return False
        mock_db_check.return_value = False
        mock_redis_check.return_value = False
        mock_service_check.return_value = False

        response = client.get("/health/")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert all(not check for check in data["checks"].values())

    @patch("services.office_service.api.health.check_database_connection")
    async def test_health_check_exception_handling(self, mock_db_check, client):
        """Test health check exception handling."""
        # Mock database check to raise exception
        mock_db_check.side_effect = Exception("Database connection failed")

        response = client.get("/health/")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data

    @patch("services.office_service.api.health.check_user_integration")
    async def test_integration_health_all_healthy(self, mock_integration_check, client):
        """Test integration health check when all integrations are healthy."""
        # Mock both integrations as healthy
        mock_integration_check.side_effect = [
            {"provider": "google", "healthy": True, "error": None},
            {"provider": "microsoft", "healthy": True, "error": None},
        ]

        response = client.get("/health/integrations/test_user_123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "all_healthy"
        assert data["user_id"] == "test_user_123"
        assert data["integrations"]["google"]["healthy"] is True
        assert data["integrations"]["microsoft"]["healthy"] is True

    @patch("services.office_service.api.health.check_user_integration")
    async def test_integration_health_partial(self, mock_integration_check, client):
        """Test integration health check with partial success."""
        # Mock one integration healthy, one unhealthy
        mock_integration_check.side_effect = [
            {"provider": "google", "healthy": True, "error": None},
            {
                "provider": "microsoft",
                "healthy": False,
                "error": "Token expired",
            },
        ]

        response = client.get("/health/integrations/test_user_123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "partial"
        assert data["integrations"]["google"]["healthy"] is True
        assert data["integrations"]["microsoft"]["healthy"] is False

    @patch("services.office_service.api.health.check_user_integration")
    async def test_integration_health_all_unhealthy(
        self, mock_integration_check, client
    ):
        """Test integration health check when all integrations are unhealthy."""
        # Mock both integrations as unhealthy
        mock_integration_check.side_effect = [
            {
                "provider": "google",
                "healthy": False,
                "error": "Token not found",
            },
            {
                "provider": "microsoft",
                "healthy": False,
                "error": "Token expired",
            },
        ]

        response = client.get("/health/integrations/test_user_123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["integrations"]["google"]["healthy"] is False
        assert data["integrations"]["microsoft"]["healthy"] is False

    @patch("services.office_service.api.health.check_user_integration")
    async def test_integration_health_exception(self, mock_integration_check, client):
        """Test integration health check exception handling."""
        # Mock integration check to raise exception
        mock_integration_check.side_effect = Exception("Integration check failed")

        response = client.get("/health/integrations/test_user_123")

        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "error" in data

    def test_quick_health_check(self, client):
        """Test quick health check endpoint."""
        response = client.get("/health/quick")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "version" in data
        assert "timestamp" in data


class TestHealthCheckHelpers:
    """Test cases for health check helper functions."""

    @patch("services.office_service.api.health.database")
    async def test_check_database_connection_success_connected(self, mock_database):
        """Test database connection check when already connected."""
        mock_database.is_connected = True
        mock_database.execute_query = AsyncMock()

        result = await check_database_connection()

        assert result is True
        mock_database.execute_query.assert_called_once_with("SELECT 1")

    @patch("services.office_service.api.health.database")
    async def test_check_database_connection_success_reconnect(self, mock_database):
        """Test database connection check when needs to reconnect."""
        mock_database.is_connected = False
        mock_database.connect = AsyncMock()
        mock_database.execute_query = AsyncMock()

        result = await check_database_connection()

        assert result is True
        mock_database.connect.assert_called_once()
        mock_database.execute_query.assert_called_once_with("SELECT 1")

    @patch("services.office_service.api.health.database")
    async def test_check_database_connection_failure(self, mock_database):
        """Test database connection check failure."""
        mock_database.is_connected = True
        mock_database.execute_query = AsyncMock(side_effect=Exception("Database error"))

        result = await check_database_connection()

        assert result is False

    @patch("services.office_service.api.health.cache_manager")
    async def test_check_redis_connection_success(self, mock_cache_manager):
        """Test Redis connection check success."""
        mock_cache_manager.health_check = AsyncMock(return_value=True)

        result = await check_redis_connection()

        assert result is True
        mock_cache_manager.health_check.assert_called_once()

    @patch("services.office_service.api.health.cache_manager")
    async def test_check_redis_connection_failure(self, mock_cache_manager):
        """Test Redis connection check failure."""
        mock_cache_manager.health_check = AsyncMock(return_value=False)

        result = await check_redis_connection()

        assert result is False

    @patch("services.office_service.api.health.cache_manager")
    async def test_check_redis_connection_exception(self, mock_cache_manager):
        """Test Redis connection check exception."""
        mock_cache_manager.health_check = AsyncMock(
            side_effect=Exception("Redis error")
        )

        result = await check_redis_connection()

        assert result is False

    @patch("services.office_service.api.health.httpx.AsyncClient")
    async def test_check_service_connection_success(self, mock_httpx_client):
        """Test external service connection check success."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.get.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client

        result = await check_service_connection("https://example.com")

        assert result is True
        mock_client.get.assert_called_once_with("https://example.com/health")

    @patch("services.office_service.api.health.httpx.AsyncClient")
    async def test_check_service_connection_failure(self, mock_httpx_client):
        """Test external service connection check failure."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.get.return_value = mock_response
        mock_httpx_client.return_value.__aenter__.return_value = mock_client

        result = await check_service_connection("https://example.com")

        assert result is False

    @patch("services.office_service.api.health.httpx.AsyncClient")
    async def test_check_service_connection_timeout(self, mock_httpx_client):
        """Test external service connection check timeout."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        mock_httpx_client.return_value.__aenter__.return_value = mock_client

        result = await check_service_connection("https://example.com")

        assert result is False

    @patch("services.office_service.api.health.httpx.AsyncClient")
    async def test_check_service_connection_exception(self, mock_httpx_client):
        """Test external service connection check exception."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection error")
        mock_httpx_client.return_value.__aenter__.return_value = mock_client

        result = await check_service_connection("https://example.com")

        assert result is False

    @patch("services.office_service.api.health.token_manager")
    async def test_check_user_integration_success(
        self, mock_token_manager, mock_token_data
    ):
        """Test user integration check success."""
        mock_token_manager.get_user_token = AsyncMock(return_value=mock_token_data)

        result = await check_user_integration("test_user_123", "google")

        assert result["provider"] == "google"
        assert result["healthy"] is True
        assert result["error"] is None
        assert "token_expires_at" in result
        assert "last_checked" in result

    @patch("services.office_service.api.health.token_manager")
    async def test_check_user_integration_no_token(self, mock_token_manager):
        """Test user integration check when no token available."""
        mock_token_manager.get_user_token = AsyncMock(return_value=None)

        result = await check_user_integration("test_user_123", "google")

        assert result["provider"] == "google"
        assert result["healthy"] is False
        assert result["error"] == "No valid token available"

    @patch("services.office_service.api.health.token_manager")
    async def test_check_user_integration_token_no_access_token(
        self, mock_token_manager
    ):
        """Test user integration check when token has no access token."""
        mock_token_data = TokenData(
            access_token=None,
            refresh_token="refresh_token",
            provider="google",
            user_id="test_user_123",
            scopes=["scope1"],
            expires_at=datetime.now(timezone.utc),
        )
        mock_token_manager.get_user_token = AsyncMock(return_value=mock_token_data)

        result = await check_user_integration("test_user_123", "google")

        assert result["provider"] == "google"
        assert result["healthy"] is False
        assert result["error"] == "No valid token available"

    @patch("services.office_service.api.health.token_manager")
    async def test_check_user_integration_exception(self, mock_token_manager):
        """Test user integration check exception handling."""
        mock_token_manager.get_user_token = AsyncMock(
            side_effect=Exception("Token fetch failed")
        )

        result = await check_user_integration("test_user_123", "google")

        assert result["provider"] == "google"
        assert result["healthy"] is False
        assert result["error"] == "Token fetch failed"

    @patch("services.office_service.api.health.token_manager")
    async def test_check_user_integration_microsoft_scopes(
        self, mock_token_manager, mock_token_data
    ):
        """Test user integration check uses correct scopes for Microsoft."""
        mock_token_data.provider = "microsoft"
        mock_token_manager.get_user_token = AsyncMock(return_value=mock_token_data)

        result = await check_user_integration("test_user_123", "microsoft")

        # Verify Microsoft scopes were used
        mock_token_manager.get_user_token.assert_called_once_with(
            "test_user_123",
            "microsoft",
            ["https://graph.microsoft.com/user.read"],
        )
        assert result["provider"] == "microsoft"
        assert result["healthy"] is True
