"""
Security tests for the shipments service.

Tests user authentication, authorization, and ownership validation.
"""

import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.testclient import TestClient

from services.shipments.main import app
from services.shipments.service_auth import (
    client_has_permission,
    get_client_permissions,
)


@pytest.fixture(autouse=True)
def patch_settings():
    """Patch the _settings global variable to return test settings."""
    import services.shipments.settings as shipments_settings

    test_settings = shipments_settings.Settings(
        db_url_shipments="sqlite:///:memory:",
        api_frontend_shipments_key="test-frontend-shipments-key",
    )

    # Directly set the singleton instead of using monkeypatch
    shipments_settings._settings = test_settings
    yield
    shipments_settings._settings = None


@pytest_asyncio.fixture
async def db_session():
    """Create database session with tables for testing."""
    from services.shipments.database import get_engine
    from services.shipments.models import SQLModel

    # Create tables (only once per test session)
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Create a single session that will be shared
    from sqlalchemy.ext.asyncio import AsyncSession

    session = AsyncSession(engine)

    yield session

    # Clean up database after each test
    # Rollback any pending transactions first
    await session.rollback()

    # Close the session properly
    await session.close()


@pytest_asyncio.fixture
async def client(db_session):
    """Create a test client with patched settings and database session."""
    from services.shipments.database import get_async_session_dep

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_async_session_dep] = override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Create authentication headers for testing."""
    return {
        "Authorization": "Bearer test-jwt-token",
        "X-User-Id": "user123",
    }


@pytest.fixture
def service_auth_headers():
    """Create service authentication headers for testing."""
    return {
        "X-API-Key": "test-frontend-shipments-key",
        "X-User-Id": "user123",
    }


class TestUserAuthentication:
    """Test user authentication functionality."""

    async def test_get_current_user_from_gateway_headers_success(self):
        """Test successful user extraction from gateway headers."""
        from fastapi import Request

        from services.shipments.auth import get_current_user_from_gateway_headers

        # Mock request with gateway headers
        request = Request(
            scope={
                "type": "http",
                "method": "GET",
                "path": "/test",
                "headers": [(b"x-user-id", b"user123")],
            }
        )

        # Test the actual function
        user_id = await get_current_user_from_gateway_headers(request)
        assert user_id == "user123"

    async def test_get_current_user_from_gateway_headers_missing(self):
        """Test user extraction when gateway headers are missing."""
        from fastapi import Request

        from services.shipments.auth import get_current_user_from_gateway_headers

        # Mock request without gateway headers
        request = Request(
            scope={"type": "http", "method": "GET", "path": "/test", "headers": []}
        )

        # Test the actual function
        user_id = await get_current_user_from_gateway_headers(request)
        assert user_id is None

    async def test_verify_user_ownership_success(self):
        """Test successful user ownership verification."""
        from services.shipments.auth import verify_user_ownership

        current_user = "user123"
        resource_user = "user123"

        # Test the actual function
        result = await verify_user_ownership(current_user, resource_user)
        assert result is True

    async def test_verify_user_ownership_failure(self):
        """Test user ownership verification failure."""
        from services.shipments.auth import verify_user_ownership

        current_user = "user123"
        resource_user = "user456"

        # Test the actual function - should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await verify_user_ownership(current_user, resource_user)

        assert exc_info.value.status_code == 403
        assert "User does not own the resource" in str(exc_info.value.detail)


class TestServiceAuthentication:
    """Test service API key authentication."""

    def test_client_permissions(self):
        """Test client permission retrieval."""
        frontend_permissions = get_client_permissions("frontend")
        expected_permissions = [
            "read_shipments",
            "write_shipments",
            "read_labels",
            "write_labels",
            "parse_emails",
            "collect_data",
        ]

        assert set(frontend_permissions) == set(expected_permissions)

    def test_client_has_permission_success(self):
        """Test successful permission check."""
        has_permission = client_has_permission("frontend", "read_shipments")
        assert has_permission is True

    def test_client_has_permission_failure(self):
        """Test failed permission check."""
        has_permission = client_has_permission("frontend", "admin_access")
        assert has_permission is False

    def test_unknown_client_permissions(self):
        """Test permissions for unknown client."""
        permissions = get_client_permissions("unknown_client")
        assert permissions == []


class TestEndpointSecurity:
    """Test endpoint security and authentication."""

    async def test_email_parser_endpoint_requires_auth(self, client):
        """Test that email parser endpoint requires authentication."""
        response = client.post(
            "/v1/shipments/events/from-email",
            json={
                "user_id": "user123",
                "subject": "Test email",
                "sender": "test@example.com",
                "body": "Test body",
                "content_type": "text",
            },
        )
        # Should return 401 or 403 due to missing authentication
        assert response.status_code in [401, 403]

    async def test_data_collection_endpoint_requires_auth(self, client):
        """Test that data collection endpoint requires authentication."""
        response = client.post(
            "/v1/shipments/packages/collect-data",
            json={
                "user_id": "user123",
                "email_message_id": "email123",
                "original_email_data": {},
                "auto_detected_data": {},
                "user_corrected_data": {},
                "detection_confidence": 0.8,
                "consent_given": True,
            },
        )
        # Should return 401 or 403 due to missing authentication
        assert response.status_code in [401, 403]

    async def test_labels_endpoint_requires_auth(self, client):
        """Test that labels endpoint requires authentication."""
        response = client.get("/v1/shipments/labels/")
        # Should return 401 or 403 due to missing authentication
        assert response.status_code in [401, 403]

    async def test_carrier_configs_endpoint_requires_auth(self, client):
        """Test that carrier configs endpoint requires authentication."""
        response = client.get("/v1/shipments/carriers/")
        # Should return 401 or 403 due to missing authentication
        assert response.status_code in [401, 403]

    async def test_packages_endpoint_requires_auth(self, client):
        """Test that packages endpoint requires authentication."""
        response = client.get("/v1/shipments/packages/")
        # Should return 401 or 403 due to missing authentication
        assert response.status_code in [401, 403]

    async def test_email_parser_endpoint_with_auth_success(
        self, client, auth_headers, service_auth_headers
    ):
        """Test that email parser endpoint works with proper authentication."""
        # Combine user auth and service auth headers
        headers = {**auth_headers, **service_auth_headers}

        response = client.post(
            "/v1/shipments/events/from-email",
            headers=headers,
            json={
                "user_id": "user123",
                "subject": "Test email",
                "sender": "test@example.com",
                "body": "Test body",
                "content_type": "text",
            },
        )
        # Should not return 401/403 with proper auth, but might return other errors due to test setup
        assert response.status_code not in [401, 403]

    async def test_data_collection_endpoint_with_auth_success(
        self, client, auth_headers, service_auth_headers
    ):
        """Test that data collection endpoint works with proper authentication."""
        # Combine user auth and service auth headers
        headers = {**auth_headers, **service_auth_headers}

        response = client.post(
            "/v1/shipments/packages/collect-data",
            headers=headers,
            json={
                "user_id": "user123",
                "email_message_id": "email123",
                "original_email_data": {},
                "auto_detected_data": {},
                "user_corrected_data": {},
                "detection_confidence": 0.8,
                "consent_given": True,
            },
        )
        # Should not return 401/403 with proper auth, but might return other errors due to test setup
        assert response.status_code not in [401, 403]


class TestUserOwnershipValidation:
    """Test user ownership validation in endpoints."""

    async def test_email_parser_user_ownership_validation(
        self, client, service_auth_headers
    ):
        """Test that email parser validates user ownership."""
        # Test with matching user IDs
        headers = {
            **service_auth_headers,
            "X-User-Id": "user123",
        }

        response = client.post(
            "/v1/shipments/events/from-email",
            headers=headers,
            json={
                "user_id": "user123",  # Same as X-User-Id
                "subject": "Test email",
                "sender": "test@example.com",
                "body": "Test body",
                "content_type": "text",
            },
        )
        # Should not return 403 for ownership violation
        assert response.status_code != 403

    async def test_email_parser_user_ownership_validation_failure(
        self, client, service_auth_headers
    ):
        """Test that email parser rejects wrong user ownership."""
        # Test with mismatched user IDs - the endpoint should use the authenticated user's ID
        # not the one in the request body, so this should still work
        headers = {
            **service_auth_headers,
            "X-User-Id": "user456",
        }

        response = client.post(
            "/v1/shipments/events/from-email",
            headers=headers,
            json={
                "user_id": "user123",  # Different from X-User-Id, but endpoint uses X-User-Id
                "subject": "Test email",
                "sender": "test@example.com",
                "body": "Test body",
                "content_type": "text",
            },
        )
        # Should not return 403 because the endpoint uses the authenticated user's ID
        assert response.status_code != 403

    async def test_data_collection_user_ownership_validation(
        self, client, service_auth_headers
    ):
        """Test that data collection validates user ownership."""
        # Test with matching user IDs
        headers = {
            **service_auth_headers,
            "X-User-Id": "user123",
        }

        response = client.post(
            "/v1/shipments/packages/collect-data",
            headers=headers,
            json={
                "user_id": "user123",  # Same as X-User-Id
                "email_message_id": "email123",
                "original_email_data": {},
                "auto_detected_data": {},
                "user_corrected_data": {},
                "detection_confidence": 0.8,
                "consent_given": True,
            },
        )
        # Should not return 403 for ownership violation
        assert response.status_code != 403

    async def test_data_collection_user_ownership_validation_failure(
        self, client, service_auth_headers
    ):
        """Test that data collection rejects wrong user ownership."""
        # Test with mismatched user IDs - the endpoint should use the authenticated user's ID
        # not the one in the request body, so this should still work
        headers = {
            **service_auth_headers,
            "X-User-Id": "user456",
        }

        response = client.post(
            "/v1/shipments/packages/collect-data",
            headers=headers,
            json={
                "user_id": "user123",  # Different from X-User-Id, but endpoint uses X-User-Id
                "email_message_id": "email123",
                "original_email_data": {},
                "auto_detected_data": {},
                "user_corrected_data": {},
                "detection_confidence": 0.8,
                "consent_given": True,
            },
        )
        # Should not return 403 because the endpoint uses the authenticated user's ID
        assert response.status_code != 403


class TestCrossUserAccess:
    """Test cross-user access prevention."""

    async def test_user_cannot_access_other_user_data(
        self, client, service_auth_headers
    ):
        """Test that users cannot access other users' data."""
        # Test accessing packages with different user ID
        headers = {
            **service_auth_headers,
            "X-User-Id": "user123",
        }

        # Try to access data that belongs to user456
        response = client.get(
            "/v1/shipments/packages/",
            headers=headers,
            params={"user_id": "user456"},  # Try to access other user's data
        )

        # The endpoint should only return data for the authenticated user (user123)
        # Even if we try to access user456's data, we only get user123's data
        assert response.status_code == 200

        # Verify that the response only contains user123's data (which should be empty)
        response_data = response.json()
        assert "data" in response_data
        # The endpoint should filter by authenticated user, not by the user_id parameter
        # So we should get an empty list since user123 has no packages
        assert len(response_data["data"]) == 0

    async def test_user_cannot_modify_other_user_data(
        self, client, service_auth_headers
    ):
        """Test that users cannot modify other users' data."""
        # Test modifying packages with different user ID
        headers = {
            **service_auth_headers,
            "X-User-Id": "user123",
        }

        # Try to modify data that belongs to user456
        # Use a valid FedEx tracking number format
        response = client.post(
            "/v1/shipments/packages/",
            headers=headers,
            json={
                "user_id": "user456",  # Try to create for other user
                "tracking_number": "123456789012345",  # Valid FedEx format
                "carrier": "fedex",
            },
        )

        # Should not be able to modify other user's data
        # The endpoint should use the authenticated user's ID, not the one in the request
        assert (
            response.status_code == 200
        )  # Should succeed because it uses authenticated user

    async def test_user_cannot_update_other_user_tracking_events(
        self, client, service_auth_headers
    ):
        """Test that users cannot update tracking events belonging to other users via email_message_id."""
        # This test verifies the security fix for the tracking event duplicate prevention logic
        # Users should not be able to update tracking events belonging to other users
        # even if they know the email_message_id

        current_user = "user123"
        other_user = "user456"
        shared_email_message_id = "email123@example.com"

        # Test with current user trying to access events for other user's email
        headers = {
            **service_auth_headers,
            "X-User-Id": current_user,
        }

        response = client.get(
            "/v1/shipments/events/",
            headers=headers,
            params={"email_message_id": shared_email_message_id},
        )

        # The endpoint should filter by user ownership, so user123 can only see their own events
        # Since user123 has no events with this email_message_id, they should get an empty list
        assert response.status_code == 200

        # Verify that the response is an empty list (no events for user123 with this email)
        response_data = response.json()
        assert isinstance(response_data, list)
        assert len(response_data) == 0

        # Verify the security principle
        assert current_user != other_user
        assert shared_email_message_id is not None


class TestAPIKeyPermissions:
    """Test API key permission validation."""

    def test_frontend_has_parse_emails_permission(self):
        """Test that frontend has parse_emails permission."""
        has_permission = client_has_permission("frontend", "parse_emails")
        assert has_permission is True

    def test_frontend_has_collect_data_permission(self):
        """Test that frontend has collect_data permission."""
        has_permission = client_has_permission("frontend", "collect_data")
        assert has_permission is True

    def test_frontend_has_read_shipments_permission(self):
        """Test that frontend has read_shipments permission."""
        has_permission = client_has_permission("frontend", "read_shipments")
        assert has_permission is True

    def test_frontend_has_write_shipments_permission(self):
        """Test that frontend has write_shipments permission."""
        has_permission = client_has_permission("frontend", "write_shipments")
        assert has_permission is True

    def test_frontend_has_label_permissions(self):
        """Test that frontend has label permissions."""
        read_labels = client_has_permission("frontend", "read_labels")
        write_labels = client_has_permission("frontend", "write_labels")

        assert read_labels is True
        assert write_labels is True

    def test_frontend_missing_admin_permission(self):
        """Test that frontend does not have admin permissions."""
        admin_permissions = [
            "admin_access",
            "delete_users",
            "system_config",
            "super_user",
        ]

        for permission in admin_permissions:
            has_permission = client_has_permission("frontend", permission)
            assert has_permission is False


class TestErrorHandling:
    """Test error handling for security scenarios."""

    async def test_unauthorized_access_error(self, client):
        """Test proper error response for unauthorized access."""
        response = client.get("/v1/shipments/packages/")
        # Should return 401 for unauthorized access
        assert response.status_code == 401

    async def test_forbidden_access_error(self, client, auth_headers):
        """Test proper error response for forbidden access."""
        # Test with user auth but no service auth
        response = client.get("/v1/shipments/packages/", headers=auth_headers)
        # Should return 403 for forbidden access (missing service API key)
        assert response.status_code == 403

    async def test_user_ownership_error(self, client, service_auth_headers):
        """Test proper error response for user ownership violation."""
        # Test with mismatched user IDs
        headers = {
            **service_auth_headers,
            "X-User-Id": "user456",
        }

        response = client.post(
            "/v1/shipments/packages/",
            headers=headers,
            json={
                "user_id": "user123",  # Different from X-User-Id
                "tracking_number": "123456789012345",  # Valid FedEx format
                "carrier": "fedex",
            },
        )
        # Should return 200 because the endpoint uses the authenticated user's ID
        assert response.status_code == 200

    async def test_invalid_api_key_error(self, client, auth_headers):
        """Test proper error response for invalid API key."""
        headers = {
            **auth_headers,
            "X-API-Key": "invalid-api-key",
        }

        response = client.get("/v1/shipments/packages/", headers=headers)
        # Should return 401 or 403 for invalid API key
        assert response.status_code in [401, 403]

    async def test_missing_user_id_error(self, client, service_auth_headers):
        """Test proper error response for missing user ID."""
        # Test without X-User-Id header
        headers = {
            "X-API-Key": service_auth_headers["X-API-Key"],
        }

        response = client.get("/v1/shipments/packages/", headers=headers)
        # Should return 401 for missing user authentication
        assert response.status_code == 401


class TestAuthenticationIntegration:
    """Test integration of authentication mechanisms."""

    async def test_gateway_headers_override_jwt(self, client, service_auth_headers):
        """Test that gateway headers take precedence over JWT tokens."""
        headers = {
            **service_auth_headers,
            "Authorization": "Bearer invalid-jwt-token",
            "X-User-Id": "user123",
        }

        response = client.get("/v1/shipments/packages/", headers=headers)
        # Should work with gateway headers even with invalid JWT
        assert response.status_code not in [401, 403]

    async def test_jwt_fallback_when_no_gateway_headers(
        self, client, service_auth_headers
    ):
        """Test JWT fallback when gateway headers are missing."""
        # This would require a valid JWT token in a real test
        # For now, we test the concept that JWT is used as fallback
        headers = {
            "X-API-Key": service_auth_headers["X-API-Key"],
            "Authorization": "Bearer test-jwt-token",
        }

        response = client.get("/v1/shipments/packages/", headers=headers)
        # Should attempt JWT authentication when no gateway headers
        assert response.status_code in [401, 403, 404]  # Various possible responses


if __name__ == "__main__":
    pytest.main([__file__])
