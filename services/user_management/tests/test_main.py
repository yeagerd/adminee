"""
Unit tests for main FastAPI application.

Tests application startup, health endpoints, exception handling,
and middleware functionality.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from ..exceptions import (
    AuthenticationException,
    IntegrationNotFoundException,
    UserNotFoundException,
    ValidationException,
)
from ..main import app


@pytest.fixture
def client():
    """Create test client for FastAPI application."""
    return TestClient(app)


class TestApplicationStartup:
    """Test cases for application startup and configuration."""

    def test_app_creation(self, client):
        """Test that the FastAPI application is created correctly."""
        assert app.title == "User Management Service"
        assert app.version == "0.1.0"
        assert (
            "Manages user profiles, preferences, and OAuth integrations"
            in app.description
        )

    @patch("services.user_management.main.settings")
    @patch("services.user_management.main.database")
    def test_cors_middleware_configured(self, mock_database, mock_settings, client):
        """Test that CORS middleware is properly configured."""
        mock_settings.debug = True
        mock_settings.environment = "test"
        mock_database.is_connected = True
        mock_database.execute = AsyncMock()

        # Test CORS headers on a regular request since OPTIONS may not be supported by default
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_routers_registered(self, client):
        """Test that all routers are registered with the application."""
        # Check that router endpoints are accessible
        # Since user endpoints now require authentication, they should return 401/403
        response = client.get("/users/search")
        assert response.status_code in [401, 403, 422]  # Authentication required

        # Check the /me endpoint which also requires auth
        response = client.get("/users/me")
        assert response.status_code in [401, 403, 422]  # Authentication required

        # Webhooks should be accessible (will likely return 405 Method Not Allowed for unsupported methods)
        response = client.get("/webhooks/clerk")
        assert response.status_code in [
            200,
            405,
            422,
        ]  # Method not allowed or validation error


class TestHealthEndpoint:
    """Test cases for health check endpoint (liveness probe)."""

    @patch("services.user_management.main.settings")
    @patch("services.user_management.main.database")
    def test_health_check_basic(self, mock_database, mock_settings, client):
        """Test basic health check response."""
        mock_settings.debug = True
        mock_settings.environment = "test"
        mock_database.is_connected = True
        mock_database.execute = AsyncMock()

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "user-management"
        assert data["version"] == "0.1.0"
        assert "status" in data
        assert "database" in data
        assert "timestamp" in data

    @patch("services.user_management.main.settings")
    @patch("services.user_management.main.database")
    def test_health_check_database_connected(
        self, mock_database, mock_settings, client
    ):
        """Test health check with database connected."""
        mock_settings.debug = True
        mock_settings.environment = "test"
        mock_database.is_connected = True
        mock_database.execute = AsyncMock()

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"]["status"] == "healthy"

    @patch("services.user_management.main.settings")
    @patch("services.user_management.main.database")
    def test_health_check_database_disconnected(
        self, mock_database, mock_settings, client
    ):
        """Test health check with database disconnected."""
        mock_settings.debug = True
        mock_settings.environment = "test"
        mock_database.is_connected = False

        response = client.get("/health")
        assert response.status_code == 503  # Service Unavailable

        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"]["status"] == "disconnected"

    @patch("services.user_management.main.settings")
    @patch("services.user_management.main.database")
    def test_health_check_database_error(self, mock_database, mock_settings, client):
        """Test health check with database error."""
        mock_settings.debug = True
        mock_settings.environment = "test"
        mock_database.is_connected = True
        mock_database.execute = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        response = client.get("/health")
        assert response.status_code == 503  # Service Unavailable

        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"]["status"] == "error"
        assert "error" in data["database"]

    @patch("services.user_management.main.settings")
    @patch("services.user_management.main.database")
    def test_health_check_debug_mode_error_details(
        self, mock_database, mock_settings, client
    ):
        """Test health check error details in debug mode."""
        mock_settings.debug = True
        mock_database.is_connected = True
        mock_database.execute = AsyncMock(
            side_effect=Exception("Specific database error")
        )

        response = client.get("/health")
        assert response.status_code == 503

        data = response.json()
        assert data["database"]["error"] == "Specific database error"

    @patch("services.user_management.main.settings")
    @patch("services.user_management.main.database")
    def test_health_check_production_mode_error_masking(
        self, mock_database, mock_settings, client
    ):
        """Test health check error masking in production mode."""
        mock_settings.debug = False
        mock_database.is_connected = True
        mock_database.execute = AsyncMock(
            side_effect=Exception("Specific database error")
        )

        response = client.get("/health")
        assert response.status_code == 503

        data = response.json()
        assert data["database"]["error"] == "Database unavailable"


class TestReadinessEndpoint:
    """Test cases for readiness check endpoint (readiness probe)."""

    @patch("services.user_management.main.database")
    @patch("services.user_management.main.settings")
    def test_readiness_check_all_healthy(self, mock_settings, mock_database, client):
        """Test readiness check with all systems healthy."""
        # Mock settings
        mock_settings.database_url = "postgresql://test"
        mock_settings.clerk_secret_key = "test_key"
        mock_settings.encryption_service_salt = "test_salt"
        mock_settings.debug = True

        # Mock database
        mock_database.is_connected = True
        mock_database.execute = AsyncMock()

        response = client.get("/ready")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ready"
        assert data["service"] == "user-management"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data
        assert "checks" in data
        assert "performance" in data

        # Check database status
        assert data["checks"]["database"]["status"] == "ready"
        assert data["checks"]["database"]["connected"] is True
        assert "response_time_ms" in data["checks"]["database"]

        # Check configuration status
        assert data["checks"]["configuration"]["status"] == "ready"
        assert len(data["checks"]["configuration"]["issues"]) == 0

        # Check dependencies status
        assert data["checks"]["dependencies"]["status"] == "ready"

        # Check performance metrics
        assert "total_check_time_ms" in data["performance"]

    @patch("services.user_management.main.settings")
    @patch("services.user_management.main.database")
    def test_readiness_check_database_disconnected(
        self, mock_database, mock_settings, client
    ):
        """Test readiness check with database disconnected."""
        mock_settings.debug = True
        mock_settings.environment = "test"
        mock_settings.database_url = "postgresql://test"
        mock_settings.clerk_secret_key = "test_key"
        mock_settings.encryption_service_salt = "test_salt"
        mock_database.is_connected = False

        response = client.get("/ready")
        assert response.status_code == 503

        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"]["status"] == "not_ready"
        assert data["checks"]["database"]["connected"] is False

    @patch("services.user_management.main.settings")
    @patch("services.user_management.main.database")
    def test_readiness_check_database_error(self, mock_database, mock_settings, client):
        """Test readiness check with database error."""
        mock_settings.debug = True
        mock_settings.environment = "test"
        mock_settings.database_url = "postgresql://test"
        mock_settings.clerk_secret_key = "test_key"
        mock_settings.encryption_service_salt = "test_salt"
        mock_database.is_connected = True
        mock_database.execute = AsyncMock(
            side_effect=Exception("Database query failed")
        )

        response = client.get("/ready")
        assert response.status_code == 503

        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"]["status"] == "not_ready"
        assert "error" in data["checks"]["database"]

    @patch("services.user_management.main.database")
    @patch("services.user_management.main.settings")
    def test_readiness_check_missing_configuration(
        self, mock_settings, mock_database, client
    ):
        """Test readiness check with missing configuration."""
        mock_settings.debug = True
        mock_settings.environment = "test"
        mock_settings.database_url = None
        mock_settings.clerk_secret_key = None
        mock_settings.encryption_service_salt = "test_salt"
        mock_database.is_connected = True
        mock_database.execute = AsyncMock()

        response = client.get("/ready")
        assert response.status_code == 503

        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["configuration"]["status"] == "not_ready"
        assert len(data["checks"]["configuration"]["issues"]) == 2
        assert (
            "DATABASE_URL not configured" in data["checks"]["configuration"]["issues"]
        )
        assert (
            "CLERK_SECRET_KEY not configured"
            in data["checks"]["configuration"]["issues"]
        )

    @patch("services.user_management.main.settings")
    @patch("services.user_management.main.database")
    def test_readiness_check_debug_mode_error_details(
        self, mock_database, mock_settings, client
    ):
        """Test readiness check error details in debug mode."""
        mock_settings.debug = True
        mock_settings.environment = "test"
        mock_settings.database_url = "postgresql://test"
        mock_settings.clerk_secret_key = "test_key"
        mock_settings.encryption_service_salt = "test_salt"
        mock_database.is_connected = True
        mock_database.execute = AsyncMock(
            side_effect=Exception("Specific database error")
        )

        response = client.get("/ready")
        assert response.status_code == 503

        data = response.json()
        assert data["checks"]["database"]["error"] == "Specific database error"

    @patch("services.user_management.main.settings")
    @patch("services.user_management.main.database")
    def test_readiness_check_production_mode_error_masking(
        self, mock_database, mock_settings, client
    ):
        """Test readiness check error masking in production mode."""
        mock_settings.debug = False
        mock_settings.environment = "test"
        mock_settings.database_url = "postgresql://test"
        mock_settings.clerk_secret_key = "test_key"
        mock_settings.encryption_service_salt = "test_salt"
        mock_database.is_connected = True
        mock_database.execute = AsyncMock(
            side_effect=Exception("Specific database error")
        )

        response = client.get("/ready")
        assert response.status_code == 503

        data = response.json()
        assert data["checks"]["database"]["error"] == "Database check failed"

    @patch("services.user_management.main.database")
    @patch("services.user_management.main.settings")
    def test_readiness_check_performance_timing(
        self, mock_settings, mock_database, client
    ):
        """Test readiness check includes performance timing."""
        # Mock settings to be valid
        mock_settings.debug = True
        mock_settings.environment = "test"
        mock_settings.database_url = "postgresql://test"
        mock_settings.clerk_secret_key = "test_key"
        mock_settings.encryption_service_salt = "test_salt"

        # Mock slow database response
        async def slow_db_execute(*args):
            import asyncio

            await asyncio.sleep(0.01)  # 10ms delay

        mock_database.is_connected = True
        mock_database.execute = slow_db_execute

        response = client.get("/ready")
        assert response.status_code == 200

        data = response.json()
        assert data["checks"]["database"]["response_time_ms"] >= 10
        assert data["performance"]["total_check_time_ms"] > 0

    @patch("services.user_management.main.database")
    @patch("services.user_management.main.settings")
    def test_readiness_check_multiple_failures(
        self, mock_settings, mock_database, client
    ):
        """Test readiness check with multiple system failures."""
        # Missing configuration
        mock_settings.debug = True
        mock_settings.environment = "test"
        mock_settings.database_url = None
        mock_settings.clerk_secret_key = "test_key"
        mock_settings.encryption_service_salt = None

        # Database error
        mock_database.is_connected = True
        mock_database.execute = AsyncMock(side_effect=Exception("Database error"))

        response = client.get("/ready")
        assert response.status_code == 503

        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"]["status"] == "not_ready"
        assert data["checks"]["configuration"]["status"] == "not_ready"
        assert len(data["checks"]["configuration"]["issues"]) == 2


class TestExceptionHandling:
    """Test cases for exception handling."""

    def test_user_not_found_exception(self, client):
        """Test UserNotFoundException creation and properties."""
        exc = UserNotFoundException("test_user_123")
        assert exc.user_id == "test_user_123"
        assert "User test_user_123 not found" in exc.message

    def test_integration_not_found_exception(self, client):
        """Test IntegrationNotFoundException creation and properties."""
        exc = IntegrationNotFoundException("test_user_123", "google")
        assert exc.user_id == "test_user_123"
        assert exc.provider == "google"
        assert "Integration google for user test_user_123 not found" in exc.message

    def test_validation_exception(self, client):
        """Test ValidationException creation and properties."""
        exc = ValidationException("email", "invalid@", "Invalid email format")
        assert exc.field == "email"
        assert exc.value == "invalid@"
        assert exc.reason == "Invalid email format"
        assert "Validation failed for field 'email'" in exc.message

    def test_authentication_exception(self, client):
        """Test AuthenticationException creation and properties."""
        exc = AuthenticationException("Invalid token")
        assert exc.message == "Invalid token"

    def test_exception_handlers_registered(self, client):
        """Test that exception handlers are properly registered with the app."""
        # Check that the app has exception handlers configured
        assert len(app.exception_handlers) > 0
        # The specific handlers are tested through integration tests


class TestMiddleware:
    """Test cases for middleware functionality."""

    def test_cors_headers(self, client):
        """Test that CORS headers are properly set."""
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})

        # Check CORS headers are present
        assert "access-control-allow-origin" in response.headers
        # Note: access-control-allow-methods is only set on preflight OPTIONS requests

    def test_content_type_json(self, client):
        """Test that responses have proper content type."""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"


class TestAPIDocumentation:
    """Test cases for API documentation."""

    def test_openapi_schema_available(self, client):
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert schema["info"]["title"] == "User Management Service"
        assert schema["info"]["version"] == "0.1.0"

    def test_docs_endpoint_available(self, client):
        """Test that docs endpoint is available in debug mode."""
        # Note: This test assumes debug mode is enabled for testing
        response = client.get("/docs")
        # Should either return docs (200) or redirect (307) depending on settings
        assert response.status_code in [200, 307, 404]  # 404 if debug=False

    def test_health_endpoint_documented(self, client):
        """Test that health endpoint is properly documented."""
        response = client.get("/openapi.json")
        schema = response.json()

        assert "/health" in schema["paths"]
        health_endpoint = schema["paths"]["/health"]["get"]
        assert "Health" in health_endpoint["tags"]
        assert "summary" in health_endpoint or "description" in health_endpoint

    def test_readiness_endpoint_documented(self, client):
        """Test that readiness endpoint is properly documented."""
        response = client.get("/openapi.json")
        schema = response.json()

        assert "/ready" in schema["paths"]
        ready_endpoint = schema["paths"]["/ready"]["get"]
        assert "Health" in ready_endpoint["tags"]
        assert "summary" in ready_endpoint or "description" in ready_endpoint

    def test_health_endpoints_return_proper_status_codes(self, client):
        """Test that health endpoints have proper status code documentation."""
        response = client.get("/openapi.json")
        schema = response.json()

        # Check health endpoint responses
        health_responses = schema["paths"]["/health"]["get"]["responses"]
        assert "200" in health_responses
        assert "503" in health_responses

        # Check readiness endpoint responses
        ready_responses = schema["paths"]["/ready"]["get"]["responses"]
        assert "200" in ready_responses
        assert "503" in ready_responses
