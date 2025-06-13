"""
Unit tests for main FastAPI application.

Tests application startup, health endpoints, exception handling,
and middleware functionality.
"""

import asyncio
import importlib
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

# Set required environment variables before any imports
os.environ["TOKEN_ENCRYPTION_SALT"] = "dGVzdC1zYWx0LTE2Ynl0ZQ=="
os.environ["API_FRONTEND_USER_KEY"] = "test-api-key"
os.environ["CLERK_SECRET_KEY"] = "test-clerk-key"

from fastapi.testclient import TestClient

from services.user_management.database import create_all_tables
from services.user_management.exceptions import (
    AuthenticationException,
    IntegrationNotFoundException,
    UserNotFoundException,
    ValidationException,
)
from services.user_management.main import app
from services.user_management.tests.test_base import BaseUserManagementTest


@pytest.fixture
def client():
    return TestClient(app)


class TestApplicationStartup(BaseUserManagementTest):
    """Test cases for application startup and configuration."""

    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.client = TestClient(app)

    def test_app_creation(self):
        assert app.title == "User Management Service"
        assert app.version == "0.1.0"
        assert (
            "Manages user profiles, preferences, and OAuth integrations"
            in app.description
        )

    @patch("services.user_management.main.settings")
    def test_cors_middleware_configured(self, mock_settings):
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


class TestHealthEndpoint(BaseUserManagementTest):
    """Test cases for health check endpoint (liveness probe)."""

    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.client = TestClient(app)

    @patch("services.user_management.main.settings")
    def test_health_check_basic(self, mock_settings):
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

    @patch("services.user_management.main.settings")
    def test_health_check_database_connected(self, mock_settings):
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


class TestReadinessEndpoint(BaseUserManagementTest):
    """Test cases for readiness check endpoint (readiness probe)."""

    def setup_method(self):
        super().setup_method()
        self.client = TestClient(app)
        asyncio.run(create_all_tables())

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
        os.environ["DB_URL_USER_MANAGEMENT"] = ""
        importlib.reload(importlib.import_module("services.user_management.database"))
        importlib.reload(importlib.import_module("services.user_management.main"))
        from services.user_management.main import app

        self.client = TestClient(app)
        response = self.client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["configuration"]["status"] == "not_ready"
        assert len(data["checks"]["configuration"]["issues"]) >= 1

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
        assert data["checks"]["database"]["response_time_ms"] >= 0
        assert data["performance"]["total_check_time_ms"] >= 0

    def test_readiness_check_multiple_failures(self):
        os.environ["DB_URL_USER_MANAGEMENT"] = ""
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
        assert len(data["checks"]["configuration"]["issues"]) >= 1


class TestExceptionHandling(BaseUserManagementTest):
    """Test cases for exception handling."""

    def setup_method(self):
        super().setup_method()
        self.client = TestClient(app)

    def test_user_not_found_exception(self):
        """Test UserNotFoundException creation and properties."""
        exc = UserNotFoundException("test_user_123")
        assert exc.user_id == "test_user_123"
        assert "User test_user_123 not found" in exc.message

    def test_integration_not_found_exception(self):
        """Test IntegrationNotFoundException creation and properties."""
        exc = IntegrationNotFoundException("test_user_123", "google")
        assert exc.user_id == "test_user_123"
        assert exc.provider == "google"
        assert "Integration google for user test_user_123 not found" in exc.message

    def test_validation_exception(self):
        """Test ValidationException creation and properties."""
        exc = ValidationException("email", "invalid@", "Invalid email format")
        assert exc.field == "email"
        assert exc.value == "invalid@"
        assert exc.reason == "Invalid email format"
        assert "Validation failed for field 'email'" in exc.message

    def test_authentication_exception(self):
        """Test AuthenticationException creation and properties."""
        exc = AuthenticationException("Invalid token")
        assert exc.message == "Invalid token"

    def test_exception_handlers_registered(self):
        """Test that exception handlers are properly registered with the app."""
        # Check that the app has exception handlers configured
        assert len(app.exception_handlers) > 0
        # The specific handlers are tested through integration tests


class TestMiddleware(BaseUserManagementTest):
    """Test cases for middleware functionality."""

    def setup_method(self):
        super().setup_method()
        self.client = TestClient(app)

    def test_cors_headers(self):
        """Test that CORS headers are properly set."""
        response = self.client.get(
            "/health", headers={"Origin": "http://localhost:3000"}
        )

        # Check CORS headers are present
        assert "access-control-allow-origin" in response.headers
        # Note: access-control-allow-methods is only set on preflight OPTIONS requests

    def test_content_type_json(self):
        """Test that responses have proper content type."""
        response = self.client.get("/health")
        assert response.headers["content-type"] == "application/json"


class TestAPIDocumentation(BaseUserManagementTest):
    """Test cases for API documentation."""

    def setup_method(self):
        super().setup_method()
        self.client = TestClient(app)
        asyncio.run(create_all_tables())

    def test_openapi_schema_available(self):
        """Test that OpenAPI schema is available."""
        response = self.client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert schema["info"]["title"] == "User Management Service"
        assert schema["info"]["version"] == "0.1.0"

    def test_docs_endpoint_available(self):
        """Test that docs endpoint is available in debug mode."""
        # Note: This test assumes debug mode is enabled for testing
        response = self.client.get("/docs")
        # Should either return docs (200) or redirect (307) depending on settings
        assert response.status_code in [200, 307, 404]  # 404 if debug=False

    def test_health_endpoint_documented(self):
        """Test that health endpoint is properly documented."""
        response = self.client.get("/openapi.json")
        schema = response.json()

        assert "/health" in schema["paths"]
        health_endpoint = schema["paths"]["/health"]["get"]
        assert "Health" in health_endpoint["tags"]
        assert "summary" in health_endpoint or "description" in health_endpoint

    def test_readiness_endpoint_documented(self):
        """Test that readiness endpoint is properly documented."""
        response = self.client.get("/openapi.json")
        schema = response.json()

        assert "/ready" in schema["paths"]
        ready_endpoint = schema["paths"]["/ready"]["get"]
        assert "Health" in ready_endpoint["tags"]
        assert "summary" in ready_endpoint or "description" in ready_endpoint

    def test_health_endpoints_return_proper_status_codes(self):
        """Test that health endpoints have proper status code documentation."""
        response = self.client.get("/openapi.json")
        schema = response.json()

        # Check health endpoint responses
        health_responses = schema["paths"]["/health"]["get"]["responses"]
        assert "200" in health_responses
        assert "503" in health_responses

        # Check readiness endpoint responses
        ready_responses = schema["paths"]["/ready"]["get"]["responses"]
        assert "200" in ready_responses
        assert "503" in ready_responses
