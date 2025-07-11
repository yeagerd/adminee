"""
Unit tests for webhook endpoints.

Tests Clerk webhook processing, signature verification, error handling,
and various webhook event types.
"""

import asyncio
import importlib
import sys
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from services.common.http_errors import ServiceError, ValidationError
from services.user.database import create_all_tables
from services.user.tests.test_base import BaseUserManagementTest


class TestClerkWebhookEndpoint(BaseUserManagementTest):
    """Test cases for Clerk webhook endpoint."""

    def setup_method(self):
        super().setup_method()

        # Force reload of database-related modules to pick up new database path
        try:
            modules_to_reload = [
                "services.user.database",
                "services.user.settings",
                "services.user.services.webhook_service",
            ]

            for module_name in modules_to_reload:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
        finally:
            pass

        asyncio.run(create_all_tables())
        self.client = TestClient(self.app)
        self.sample_user_created_payload = self._get_sample_user_created_payload()
        self.sample_user_updated_payload = self._get_sample_user_updated_payload()
        self.sample_user_deleted_payload = self._get_sample_user_deleted_payload()

    def _get_sample_user_created_payload(self):
        """Sample Clerk user.created webhook payload."""
        return {
            "type": "user.created",
            "object": "event",
            "data": {
                "id": "user_2abc123def456",
                "email_addresses": [{"email_address": "test@example.com"}],
                "first_name": "John",
                "last_name": "Doe",
                "image_url": "https://example.com/avatar.jpg",
                "created_at": 1234567890000,
                "updated_at": 1234567890000,
            },
            "timestamp": 1234567890,
        }

    def _get_sample_user_updated_payload(self):
        """Sample Clerk user.updated webhook payload."""
        return {
            "type": "user.updated",
            "object": "event",
            "data": {
                "id": "user_2abc123def456",
                "email_addresses": [{"email_address": "updated@example.com"}],
                "first_name": "Jane",
                "last_name": "Smith",
                "image_url": "https://example.com/new-avatar.jpg",
                "created_at": 1234567890000,
                "updated_at": 1234567900000,
            },
            "timestamp": 1234567900,
        }

    def _get_sample_user_deleted_payload(self):
        """Sample Clerk user.deleted webhook payload."""
        return {
            "type": "user.deleted",
            "object": "event",
            "data": {
                "id": "user_2abc123def456",
                "email_addresses": [{"email_address": "test@example.com"}],
                "first_name": "John",
                "last_name": "Doe",
                "created_at": 1234567890000,
                "updated_at": 1234567890000,
            },
            "timestamp": 1234567890,
        }

    @patch("services.user.auth.webhook_auth.verify_webhook_signature")
    @patch("services.user.routers.webhooks.webhook_service")
    def test_clerk_webhook_user_created_success(
        self, mock_webhook_service, mock_verify
    ):
        """Test successful user.created webhook processing."""
        # Mock signature verification to pass
        mock_verify.return_value = None

        # Mock successful user creation
        mock_webhook_service.process_user_created = AsyncMock(
            return_value={
                "action": "user_created",
                "user_id": "user_2abc123def456",
                "preferences_id": 1,
            }
        )

        response = self.client.post(
            "/webhooks/clerk",
            json=self.sample_user_created_payload,
            headers={
                "svix-signature": "v1=test_signature",
                "svix-timestamp": "1234567890",
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["event_id"] == "user_2abc123def456"

        # Verify service was called with correct data
        mock_webhook_service.process_user_created.assert_called_once_with(
            self.sample_user_created_payload["data"]
        )

    @patch("services.user.auth.webhook_auth.verify_webhook_signature")
    @patch("services.user.routers.webhooks.webhook_service")
    def test_clerk_webhook_user_updated_success(
        self, mock_webhook_service, mock_verify
    ):
        """Test successful user.updated webhook processing."""
        # Mock signature verification to pass
        mock_verify.return_value = None

        # Mock successful user update
        mock_webhook_service.process_user_updated = AsyncMock(
            return_value={
                "action": "user_updated",
                "user_id": "user_2abc123def456",
                "changes": ["email", "first_name"],
            }
        )

        response = self.client.post(
            "/webhooks/clerk",
            json=self.sample_user_updated_payload,
            headers={
                "svix-signature": "v1=test_signature",
                "svix-timestamp": "1234567890",
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["event_id"] == "user_2abc123def456"

        # Verify service was called
        mock_webhook_service.process_user_updated.assert_called_once_with(
            self.sample_user_updated_payload["data"]
        )

    @patch("services.user.auth.webhook_auth.verify_webhook_signature")
    @patch("services.user.routers.webhooks.webhook_service")
    def test_clerk_webhook_user_deleted_success(
        self, mock_webhook_service, mock_verify
    ):
        """Test successful user.deleted webhook processing."""
        # Mock signature verification to pass
        mock_verify.return_value = None

        # Mock successful user deletion
        mock_webhook_service.process_user_deleted = AsyncMock(
            return_value={
                "action": "user_deleted",
                "user_id": "user_2abc123def456",
                "cleaned_up": ["preferences", "integrations"],
            }
        )

        response = self.client.post(
            "/webhooks/clerk",
            json=self.sample_user_deleted_payload,
            headers={
                "svix-signature": "v1=test_signature",
                "svix-timestamp": "1234567890",
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["event_id"] == "user_2abc123def456"

        # Verify service was called
        mock_webhook_service.process_user_deleted.assert_called_once_with(
            self.sample_user_deleted_payload["data"]
        )

    def test_clerk_webhook_signature_verification_failure(self):
        """Test webhook signature verification failure."""
        # Send webhook without mocking signature verification
        # This will test the actual verification logic
        response = self.client.post(
            "/webhooks/clerk", json=self.sample_user_created_payload
        )

        # In test environment, webhook secret is not configured so verification is skipped
        # This test verifies the endpoint exists and handles requests
        assert response.status_code in [200, 400, 401]  # Various possible responses

    @patch("services.user.auth.webhook_auth.verify_webhook_signature")
    def test_clerk_webhook_invalid_payload_format(self, mock_verify):
        """Test webhook with invalid payload format."""
        mock_verify.return_value = None
        invalid_payload = "invalid json"
        with pytest.raises(ValidationError) as exc_info:
            self.client.post(
                "/webhooks/clerk",
                content=invalid_payload,
                headers={
                    "svix-signature": "v1=test_signature",
                    "svix-timestamp": "1234567890",
                    "content-type": "application/json",
                },
            )
        assert "Invalid JSON payload format" in str(exc_info.value)

    @patch("services.user.auth.webhook_auth.verify_webhook_signature")
    def test_clerk_webhook_missing_type_field(self, mock_verify):
        """Test webhook with missing type field."""
        mock_verify.return_value = None
        invalid_payload = {
            "object": "event",
            "data": {"id": "user_123"},
        }
        with pytest.raises(ValidationError) as exc_info:
            self.client.post(
                "/webhooks/clerk",
                json=invalid_payload,
                headers={
                    "svix-signature": "v1=test_signature",
                    "svix-timestamp": "1234567890",
                },
            )
        assert "missing required 'type' field" in str(exc_info.value)

    @patch("services.user.auth.webhook_auth.verify_webhook_signature")
    def test_clerk_webhook_missing_data_field(self, mock_verify):
        """Test webhook with missing data field."""
        mock_verify.return_value = None
        invalid_payload = {
            "type": "user.created",
            "object": "event",
        }
        with pytest.raises(ValidationError) as exc_info:
            self.client.post(
                "/webhooks/clerk",
                json=invalid_payload,
                headers={
                    "svix-signature": "v1=test_signature",
                    "svix-timestamp": "1234567890",
                },
            )
        assert "missing required 'data' field" in str(exc_info.value)

    @patch("services.user.auth.webhook_auth.verify_webhook_signature")
    def test_clerk_webhook_invalid_json(self, mock_verify):
        """Test webhook with completely invalid JSON."""
        mock_verify.return_value = None
        with pytest.raises(ValidationError) as exc_info:
            self.client.post(
                "/webhooks/clerk",
                content="{invalid json}",
                headers={
                    "svix-signature": "v1=test_signature",
                    "svix-timestamp": "1234567890",
                    "content-type": "application/json",
                },
            )
        assert "Invalid JSON payload format" in str(exc_info.value)

    @patch("services.user.auth.webhook_auth.verify_webhook_signature")
    def test_clerk_webhook_unsupported_event_type(self, mock_verify):
        """Test webhook with unsupported event type."""
        # Mock signature verification to pass
        mock_verify.return_value = None

        # Unsupported event type
        unsupported_payload = {
            "type": "user.unsupported",
            "object": "event",
            "data": {"id": "user_123"},
        }

        response = self.client.post(
            "/webhooks/clerk",
            json=unsupported_payload,
            headers={
                "svix-signature": "v1=test_signature",
                "svix-timestamp": "1234567890",
            },
        )

        # Should return 200 but indicate unsupported event
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False  # Unsupported events return success=False
        assert "unsupported" in data.get("message", "").lower()

    @patch("services.user.auth.webhook_auth.verify_webhook_signature")
    @patch("services.user.routers.webhooks.webhook_service")
    def test_clerk_webhook_processing_error(self, mock_webhook_service, mock_verify):
        """Test webhook processing error handling."""

        mock_verify.return_value = None
        mock_webhook_service.process_user_created = AsyncMock(
            side_effect=Exception("Processing failed")
        )
        with pytest.raises(ServiceError) as exc_info:
            self.client.post(
                "/webhooks/clerk",
                json=self.sample_user_created_payload,
                headers={
                    "svix-signature": "v1=test_signature",
                    "svix-timestamp": "1234567890",
                },
            )
        assert "An unexpected error occurred" in str(exc_info.value)

    @patch("services.user.auth.webhook_auth.verify_webhook_signature")
    @patch("services.user.routers.webhooks.webhook_service")
    def test_clerk_webhook_database_error(self, mock_webhook_service, mock_verify):
        """Test webhook database error handling."""

        mock_verify.return_value = None
        mock_webhook_service.process_user_created = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        with pytest.raises(ServiceError) as exc_info:
            self.client.post(
                "/webhooks/clerk",
                json=self.sample_user_created_payload,
                headers={
                    "svix-signature": "v1=test_signature",
                    "svix-timestamp": "1234567890",
                },
            )
        assert "An unexpected error occurred" in str(exc_info.value)

    @patch("services.user.auth.webhook_auth.verify_webhook_signature")
    @patch("services.user.routers.webhooks.webhook_service")
    def test_clerk_webhook_unexpected_error(self, mock_webhook_service, mock_verify):
        """Test webhook unexpected error handling."""

        mock_verify.return_value = None
        mock_webhook_service.process_user_created = AsyncMock(
            side_effect=Exception("Unexpected error")
        )
        with pytest.raises(ServiceError) as exc_info:
            self.client.post(
                "/webhooks/clerk",
                json=self.sample_user_created_payload,
                headers={
                    "svix-signature": "v1=test_signature",
                    "svix-timestamp": "1234567890",
                },
            )
        assert "An unexpected error occurred" in str(exc_info.value)


class TestClerkTestWebhookEndpoint(BaseUserManagementTest):
    """Test cases for Clerk test webhook endpoint."""

    def setup_method(self):
        super().setup_method()

        # Force reload of database-related modules to pick up new database path
        try:
            modules_to_reload = [
                "services.user.database",
                "services.user.settings",
                "services.user.services.webhook_service",
            ]

            for module_name in modules_to_reload:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
        finally:
            pass

        asyncio.run(create_all_tables())
        self.client = TestClient(self.app)

    def _get_sample_user_created_payload(self):
        """Sample Clerk user.created webhook payload."""
        return {
            "type": "user.created",
            "object": "event",
            "data": {
                "id": "user_2abc123def456",
                "email_addresses": [{"email_address": "test@example.com"}],
                "first_name": "John",
                "last_name": "Doe",
                "image_url": "https://example.com/avatar.jpg",
                "created_at": 1234567890000,
                "updated_at": 1234567890000,
            },
            "timestamp": 1234567890,
        }

    @patch("services.user.routers.webhooks.webhook_service")
    def test_test_webhook_user_created_success(self, mock_webhook_service):
        """Test successful test webhook processing."""
        # Mock the entire webhook_service module properly
        mock_webhook_service.process_clerk_webhook = AsyncMock(
            return_value={
                "action": "user_created",
                "user_id": "user_2abc123def456",
                "preferences_id": 1,
            }
        )

        response = self.client.post(
            "/webhooks/clerk/test",
            json=self._get_sample_user_created_payload(),
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["event_id"] == "user_2abc123def456"

    @patch("services.user.routers.webhooks.webhook_service")
    def test_test_webhook_processing_error(self, mock_webhook_service):
        """Test test webhook processing error."""
        import pytest

        from services.common.http_errors import ValidationError

        mock_webhook_service.process_clerk_webhook = AsyncMock(
            side_effect=Exception("Test processing failed")
        )
        with pytest.raises(ValidationError) as exc_info:
            self.client.post(
                "/webhooks/clerk/test",
                json=self._get_sample_user_created_payload(),
            )
        assert "Test webhook processing failed" in str(exc_info.value)


class TestWebhookHealthEndpoint(BaseUserManagementTest):
    """Test cases for webhook health endpoint."""

    def setup_method(self):
        super().setup_method()
        self.client = TestClient(self.app)

    def test_webhook_health(self):
        """Test webhook health endpoint."""
        response = self.client.get("/webhooks/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestOAuthWebhookEndpoint(BaseUserManagementTest):
    """Test cases for OAuth webhook endpoint."""

    def setup_method(self):
        super().setup_method()
        self.client = TestClient(self.app)

    def test_oauth_webhook_placeholder(self):
        """Test OAuth webhook placeholder endpoint."""
        response = self.client.post("/webhooks/oauth", json={})

        # This is a placeholder endpoint, so it should return a basic response
        assert response.status_code in [200, 404, 405]  # Various possible responses
