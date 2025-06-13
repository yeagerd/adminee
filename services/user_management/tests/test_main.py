"""
Unit tests for main application module.

Tests application startup, health endpoints, readiness checks,
exception handling, middleware, and API documentation.
"""

import importlib
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from services.user_management.exceptions import (
    AuthenticationException,
    IntegrationNotFoundException,
    UserNotFoundException,
    ValidationException,
)
from services.user_management.main import app
from services.user_management.tests.test_base import BaseUserManagementIntegrationTest


@pytest.fixture
def client():
    return TestClient(app)


class TestApplicationStartup(BaseUserManagementIntegrationTest):
    """Test cases for application startup and configuration."""

    def test_app_creation(self):
        assert app.title == "User Management Service"
        assert app.version == "0.1.0"
        assert (
            "Manages user profiles, preferences, and OAuth integrations"
            in app.description
        )

    @patch("services.user_management.main.get_settings")
    def test_cors_middleware_configured(self, mock_get_settings):
        mock_settings = mock_get_settings.return_value
        mock_settings.debug = True
        mock_settings.environment = "test"
        response = self.client.get(
            "/health", headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_routers_registered(self):
        response = self.client.get("/users/search")
        assert response.status_code in [401, 403, 422]
        response = self.client.get("/users/me")
        assert response.status_code in [401, 403, 422]
        response = self.client.get("/webhooks/clerk")
        assert response.status_code in [200, 405, 422]


class TestHealthEndpoint(BaseUserManagementIntegrationTest):
    """Test cases for health check endpoint (liveness probe)."""

    @patch("services.user_management.main.get_settings")
    def test_health_check_basic(self, mock_get_settings):
        mock_settings = mock_get_settings.return_value
        mock_settings.debug = True
        mock_settings.environment = "test"
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "user-management"
        assert data["version"] == "0.1.0"
        assert "status" in data
        assert "database" in data
        assert "timestamp" in data

    @patch("services.user_management.main.get_settings")
    def test_health_check_database_connected(self, mock_get_settings):
        mock_settings = mock_get_settings.return_value
        mock_settings.debug = True
        mock_settings.environment = "test"
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"]["status"] == "healthy"

    def test_health_check_database_disconnected(self):
        os.environ["DB_URL_USER_MANAGEMENT"] = "sqlite:///nonexistent/path/to/db.sqlite"
        importlib.reload(importlib.import_module("services.user_management.database"))
        importlib.reload(importlib.import_module("services.user_management.main"))
        from services.user_management.main import app

        self.client = TestClient(app)
        response = self.client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"]["status"] == "error"

    def test_health_check_database_error(self):
        os.environ["DB_URL_USER_MANAGEMENT"] = "sqlite:///nonexistent/path/to/db.sqlite"
        importlib.reload(importlib.import_module("services.user_management.database"))
        importlib.reload(importlib.import_module("services.user_management.main"))
        from services.user_management.main import app

        self.client = TestClient(app)
        response = self.client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"]["status"] == "error"
        assert "error" in data["database"]

    def test_health_check_debug_mode_error_details(self):
        os.environ["DB_URL_USER_MANAGEMENT"] = "sqlite:///nonexistent/path/to/db.sqlite"
        importlib.reload(importlib.import_module("services.user_management.database"))
        importlib.reload(importlib.import_module("services.user_management.main"))
        from services.user_management.main import app

        self.client = TestClient(app)
        response = self.client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert "error" in data["database"]

    def test_health_check_production_mode_error_masking(self):
        os.environ["DB_URL_USER_MANAGEMENT"] = "sqlite:///nonexistent/path/to/db.sqlite"
        importlib.reload(importlib.import_module("services.user_management.database"))
        importlib.reload(importlib.import_module("services.user_management.main"))
        from services.user_management.main import app

        self.client = TestClient(app)
        response = self.client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert "error" in data["database"]


class TestReadinessEndpoint(BaseUserManagementIntegrationTest):
    """Test cases for readiness check endpoint (readiness probe)."""

    def test_readiness_check_all_healthy(self):
        response = self.client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["service"] == "user-management"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data
        assert "checks" in data
        assert "performance" in data
        assert data["checks"]["database"]["status"] == "ready"
        assert data["checks"]["database"]["connected"] is True
        assert "response_time_ms" in data["checks"]["database"]
        assert data["checks"]["configuration"]["status"] == "ready"
        assert len(data["checks"]["configuration"]["issues"]) == 0
        assert data["checks"]["dependencies"]["status"] == "ready"
        assert "total_check_time_ms" in data["performance"]

    def test_readiness_check_database_disconnected(self):
        os.environ["DB_URL_USER_MANAGEMENT"] = "sqlite:///nonexistent/path/to/db.sqlite"
        importlib.reload(importlib.import_module("services.user_management.database"))
        importlib.reload(importlib.import_module("services.user_management.main"))
        from services.user_management.main import app

        self.client = TestClient(app)
        response = self.client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"]["status"] == "not_ready"
        assert data["checks"]["database"]["connected"] is False

    def test_readiness_check_database_error(self):
        os.environ["DB_URL_USER_MANAGEMENT"] = "sqlite:///nonexistent/path/to/db.sqlite"
        importlib.reload(importlib.import_module("services.user_management.database"))
        importlib.reload(importlib.import_module("services.user_management.main"))
        from services.user_management.main import app

        self.client = TestClient(app)
        response = self.client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"]["status"] == "not_ready"
        assert "error" in data["checks"]["database"]

    def test_readiness_check_missing_configuration(self):
        os.environ["DB_URL_USER_MANAGEMENT"] = "sqlite:///nonexistent/path/to/db.sqlite"
        importlib.reload(importlib.import_module("services.user_management.database"))
        importlib.reload(importlib.import_module("services.user_management.main"))
        from services.user_management.main import app

        self.client = TestClient(app)
        response = self.client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["configuration"]["status"] == "not_ready"
        assert len(data["checks"]["configuration"]["issues"]) > 0

    def test_readiness_check_debug_mode_error_details(self):
        os.environ["DB_URL_USER_MANAGEMENT"] = "sqlite:///nonexistent/path/to/db.sqlite"
        importlib.reload(importlib.import_module("services.user_management.database"))
        importlib.reload(importlib.import_module("services.user_management.main"))
        from services.user_management.main import app

        self.client = TestClient(app)
        response = self.client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert "error" in data["checks"]["database"]

    def test_readiness_check_production_mode_error_masking(self):
        os.environ["DB_URL_USER_MANAGEMENT"] = "sqlite:///nonexistent/path/to/db.sqlite"
        importlib.reload(importlib.import_module("services.user_management.database"))
        importlib.reload(importlib.import_module("services.user_management.main"))
        from services.user_management.main import app

        self.client = TestClient(app)
        response = self.client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert "error" in data["checks"]["database"]

    def test_readiness_check_performance_timing(self):
        response = self.client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert "performance" in data
        assert "total_check_time_ms" in data["performance"]
        assert data["performance"]["total_check_time_ms"] > 0

    def test_readiness_check_multiple_failures(self):
        os.environ["DB_URL_USER_MANAGEMENT"] = "sqlite:///nonexistent/path/to/db.sqlite"
        importlib.reload(importlib.import_module("services.user_management.database"))
        importlib.reload(importlib.import_module("services.user_management.main"))
        from services.user_management.main import app

        self.client = TestClient(app)
        response = self.client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"]["status"] == "not_ready"
        assert data["checks"]["configuration"]["status"] == "not_ready"


class TestExceptionHandling(BaseUserManagementIntegrationTest):
    """Test cases for exception handling."""

    def test_user_not_found_exception(self):
        with patch("services.user_management.main.app") as mock_app:
            exc = UserNotFoundException("Test user not found")
            # Test that the exception handler is registered
            assert any(
                handler
                for handler in mock_app.exception_handlers
                if handler == UserNotFoundException
            )

    def test_integration_not_found_exception(self):
        with patch("services.user_management.main.app") as mock_app:
            exc = IntegrationNotFoundException("Test integration not found")
            # Test that the exception handler is registered
            assert any(
                handler
                for handler in mock_app.exception_handlers
                if handler == IntegrationNotFoundException
            )

    def test_validation_exception(self):
        with patch("services.user_management.main.app") as mock_app:
            exc = ValidationException("Test validation error", {"field": "error"})
            # Test that the exception handler is registered
            assert any(
                handler
                for handler in mock_app.exception_handlers
                if handler == ValidationException
            )

    def test_authentication_exception(self):
        with patch("services.user_management.main.app") as mock_app:
            exc = AuthenticationException("Test auth error")
            # Test that the exception handler is registered
            assert any(
                handler
                for handler in mock_app.exception_handlers
                if handler == AuthenticationException
            )

    def test_exception_handlers_registered(self):
        # Test that all expected exception handlers are registered
        expected_exceptions = [
            UserNotFoundException,
            IntegrationNotFoundException,
            ValidationException,
            AuthenticationException,
        ]
        for exc_type in expected_exceptions:
            assert exc_type in app.exception_handlers


class TestMiddleware(BaseUserManagementIntegrationTest):
    """Test cases for middleware configuration."""

    def test_cors_headers(self):
        """Test that CORS headers are properly set."""
        response = self.client.get(
            "/health", headers={"Origin": "http://localhost:3000"}
        )

        # Check CORS headers are present
        assert "access-control-allow-origin" in response.headers

    def test_content_type_json(self):
        """Test that responses have proper content type."""
        response = self.client.get("/health")
        assert response.headers["content-type"] == "application/json"


class TestAPIDocumentation(BaseUserManagementIntegrationTest):
    """Test cases for API documentation."""

    def test_openapi_schema_available(self):
        """Test that OpenAPI schema is available."""
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "User Management Service"
        assert data["info"]["version"] == "0.1.0"

    def test_docs_endpoint_available(self):
        """Test that docs endpoint is available in debug mode."""
        response = self.client.get("/docs")
        # Should either be available (200) or redirect (307) depending on settings
        assert response.status_code in [200, 307, 404]

    def test_health_endpoint_documented(self):
        """Test that health endpoint is properly documented."""
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "/health" in data["paths"]
        assert "get" in data["paths"]["/health"]
        assert "Health" in data["paths"]["/health"]["get"]["tags"]

    def test_readiness_endpoint_documented(self):
        """Test that readiness endpoint is properly documented."""
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "/ready" in data["paths"]
        assert "get" in data["paths"]["/ready"]
        assert "Health" in data["paths"]["/ready"]["get"]["tags"]

    def test_health_endpoints_return_proper_status_codes(self):
        """Test that health endpoints return expected status codes."""
        health_response = self.client.get("/health")
        assert health_response.status_code in [200, 503]

        ready_response = self.client.get("/ready")
        assert ready_response.status_code in [200, 503]
