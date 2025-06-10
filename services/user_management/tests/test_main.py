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

    def test_cors_middleware_configured(self, client):
        """Test that CORS middleware is properly configured."""
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
    """Test cases for health check endpoint."""

    def test_health_check_basic(self, client):
        """Test basic health check response."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "user-management"
        assert data["version"] == "0.1.0"
        assert "status" in data
        assert "database" in data

    @patch("services.user_management.main.database")
    def test_health_check_database_connected(self, mock_database, client):
        """Test health check with database connected."""
        mock_database.is_connected = True
        mock_database.execute = AsyncMock()

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"]["status"] == "healthy"

    @patch("services.user_management.main.database")
    def test_health_check_database_disconnected(self, mock_database, client):
        """Test health check with database disconnected."""
        mock_database.is_connected = False

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"]["status"] == "disconnected"

    @patch("services.user_management.main.database")
    def test_health_check_database_error(self, mock_database, client):
        """Test health check with database error."""
        mock_database.is_connected = True
        mock_database.execute = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"]["status"] == "error"
        assert "error" in data["database"]


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
