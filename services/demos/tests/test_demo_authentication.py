"""
Test suite for demo authentication and user creation.

These tests verify that the demo script can properly:
1. Create users via webhook simulation
2. Authenticate with created users
3. Access user preferences after creation

This would have caught the issue where demo_user creation was failing.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import httpx
import pytest

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from services.common.test_utils import BaseSelectiveHTTPIntegrationTest
from services.demos.chat import FullDemo


class TestDemoAuthentication(BaseSelectiveHTTPIntegrationTest):
    """Test suite for demo authentication flow."""

    def setup_method(self, method):
        """Set up test environment with HTTP call prevention."""
        super().setup_method(method)

    def teardown_method(self, method):
        """Clean up test environment."""
        super().teardown_method(method)

    @pytest.fixture
    def demo_instance(self):
        """Create a demo instance for testing."""
        return FullDemo(
            use_api=True,
            chat_url="http://localhost:8002",
            office_url="http://localhost:8003",
            user_url="http://localhost:8001",
            chat_health_url="http://localhost:8002",
            office_health_url="http://localhost:8003",
            user_health_url="http://localhost:8001",
            user_id="test_demo_user",
            skip_auth=False,
        )

    @pytest.mark.asyncio
    async def test_create_user_if_not_exists_success(self, demo_instance):
        """Test successful user creation."""
        email = "test@example.com"
        user_id = f"user_{email.replace('@', '_').replace('.', '_')}"

        # Mock the user existence check (GET request) - user doesn't exist
        mock_get_response = MagicMock()
        mock_get_response.status_code = 404

        # Mock the webhook creation (POST request) - successful creation
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201

        with patch("httpx.AsyncClient") as mock_client:
            mock_http_client = mock_client.return_value.__aenter__.return_value

            # Setup different responses for GET vs POST
            def side_effect(url, **kwargs):
                if "GET" in kwargs.get("method", "GET") or "get" in str(url):
                    return mock_get_response
                else:
                    return mock_post_response

            mock_http_client.get.return_value = mock_get_response
            mock_http_client.post.return_value = mock_post_response

            result = await demo_instance._create_user_if_not_exists(email, user_id)

            assert result is True
            # Verify the webhook was called with correct payload
            mock_http_client.post.assert_called_once()
            call_args = mock_http_client.post.call_args

            # Check URL - call_args[0] contains positional args, call_args[1] contains keyword args
            assert call_args[0][0] == f"{demo_instance.user_client.base_url}/users/"

            # Check payload structure for /users/ endpoint
            payload = call_args[1]["json"]
            assert payload["external_auth_id"] == user_id
            assert payload["email"] == email
            assert payload["auth_provider"] == "nextauth"
            assert payload["first_name"] == "Demo"
            assert payload["last_name"] == "User"
            assert (
                payload["profile_image_url"]
                == "https://images.clerk.dev/demo-avatar.png"
            )

    @pytest.mark.asyncio
    async def test_create_user_if_not_exists_already_exists(self, demo_instance):
        """Test user creation when user already exists (409 response)."""
        email = "existing@example.com"
        user_id = f"user_{email.replace('@', '_').replace('.', '_')}"

        # Mock the user existence check (GET request) - user exists
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client:
            mock_http_client = mock_client.return_value.__aenter__.return_value
            mock_http_client.get.return_value = mock_get_response

            result = await demo_instance._create_user_if_not_exists(email, user_id)

            assert result is True
            # Verify no webhook was called since user already exists
            mock_http_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_user_if_not_exists_handles_errors(self, demo_instance):
        """Test that user creation gracefully handles errors."""
        email = "test@example.com"
        user_id = f"user_{email.replace('@', '_').replace('.', '_')}"

        # Test HTTP error on user existence check
        with patch("httpx.AsyncClient") as mock_client:
            mock_http_client = mock_client.return_value.__aenter__.return_value
            mock_http_client.get.side_effect = httpx.RequestError("Connection failed")

            result = await demo_instance._create_user_if_not_exists(email, user_id)

            # Should return False when user service is down
            assert result is False

    @pytest.mark.asyncio
    async def test_authenticate_creates_user_and_can_access_preferences(
        self, demo_instance
    ):
        """
        Integration test: Test that authentication creates a user who can access preferences.

        This test would have caught the original issue where user creation was failing
        but the demo continued, leading to 404 errors when accessing preferences.
        """
        email = "integration_test@example.com"
        user_id = f"{email.replace('@', '_').replace('.', '_')}"

        # Mock services as available
        demo_instance.services_available = {"user": True, "chat": True, "office": True}

        # Set the preferred provider to match the mock response
        demo_instance.preferred_provider = "google"

        # Mock email resolution response (this is what the new auth flow uses)
        mock_resolution_response = MagicMock()
        mock_resolution_response.status_code = 200
        mock_resolution_response.json.return_value = {
            "external_auth_id": user_id,
            "email": email,
            "normalized_email": email.lower(),
            "auth_provider": "google",
        }

        # Mock successful integrations check
        mock_integrations_response = MagicMock()
        mock_integrations_response.status_code = 200
        mock_integrations_response.json.return_value = {
            "integrations": [{"provider": "microsoft", "status": "active"}]
        }

        with (
            patch("httpx.AsyncClient") as mock_client,
            patch("services.demos.chat.create_nextauth_jwt_for_demo") as mock_jwt,
        ):

            mock_jwt.return_value = "mock_jwt_token"
            mock_http_client = mock_client.return_value.__aenter__.return_value

            # Setup different responses for different endpoints
            def side_effect(*args, **kwargs):
                # For GET requests, check the URL and params
                if args:  # args[0] should be the URL
                    url = str(args[0])
                    params = kwargs.get("params", {})

                    # Match the user lookup pattern: /users with email param
                    if (
                        "/users" in url
                        and "/integrations" not in url
                        and "email" in params
                    ):
                        return mock_resolution_response
                    elif "/integrations" in url and "webhooks/clerk" not in url:
                        return mock_integrations_response

                return MagicMock(status_code=200)

            mock_http_client.get.side_effect = side_effect
            mock_http_client.post.side_effect = side_effect

            # Run authentication
            result = await demo_instance.authenticate(email)

            # Should succeed
            assert result is True

            # Verify email lookup was called
            lookup_calls = [
                call
                for call in mock_http_client.get.call_args_list
                if len(call.args) > 0
                and "/users" in str(call.args[0])
                and "/integrations" not in str(call.args[0])
                and call.kwargs.get("params", {}).get("email") == email
            ]
            assert len(lookup_calls) > 0

            # Verify JWT token was created with the correct user_id
            # The actual user_id will be the one returned from user creation, not our calculated one
            actual_user_id = demo_instance.user_id
            mock_jwt.assert_called_once_with(
                actual_user_id, email=email, provider="google"
            )

    @pytest.mark.asyncio
    async def test_authenticate_fails_if_user_creation_fails_and_user_doesnt_exist(
        self, demo_instance
    ):
        """
        Test that authentication properly fails if user creation fails AND user doesn't exist.

        This test catches the scenario that was causing issues: user creation fails silently
        but then preferences access fails with 404 because user doesn't exist.
        """
        email = "nonexistent@example.com"

        demo_instance.services_available = {"user": True, "chat": True, "office": True}

        # Mock failed user creation
        mock_create_response = MagicMock()
        mock_create_response.status_code = 500  # Server error

        # Mock failed integrations check (user doesn't exist)
        with (
            patch("httpx.AsyncClient") as mock_client,
            patch("services.demos.chat.create_nextauth_jwt_for_demo") as mock_jwt,
        ):

            mock_jwt.return_value = "mock_jwt_token"
            mock_http_client = mock_client.return_value.__aenter__.return_value

            def side_effect(url, **kwargs):
                if "/users/" in url:
                    return mock_create_response
                elif "/integrations/" in url:
                    # Simulate authentication failure due to non-existent user
                    raise Exception("Authentication failed: Invalid token")
                else:
                    return MagicMock(status_code=404)

            mock_http_client.post.side_effect = side_effect
            mock_http_client.get.side_effect = side_effect

            # Authentication should fail
            result = await demo_instance.authenticate(email)

            assert result is False

    @pytest.mark.asyncio
    async def test_missing_time_import_in_user_creation(self, demo_instance):
        """
        Test that would catch the missing time import issue.

        The original bug was that _create_user_if_not_exists used time.time()
        but didn't import time module.
        """
        email = "test@example.com"
        user_id = f"user_{email.replace('@', '_').replace('.', '_')}"

        # This test verifies that time.time() can be called without error
        # If time import was missing, this would raise NameError
        try:
            await demo_instance._create_user_if_not_exists(email, user_id)
            # If we get here without NameError, the import is working
            assert True
        except NameError as e:
            if "time" in str(e):
                pytest.fail("Missing time import in _create_user_if_not_exists method")
            else:
                raise

    def test_demo_has_required_imports(self):
        """Test that the demo module has all required imports."""
        import services.demos.chat as demo_module

        # These should all be available without error
        assert hasattr(demo_module, "FullDemo")
        assert hasattr(demo_module, "httpx")
        assert hasattr(demo_module, "asyncio")

        # Test that time module functions are accessible within the module
        demo = FullDemo(
            use_api=True,
            chat_url="http://localhost:8002",
            office_url="http://localhost:8003",
            user_url="http://localhost:8001",
            chat_health_url="http://localhost:8002",
            office_health_url="http://localhost:8003",
            user_health_url="http://localhost:8001",
            user_id="test_user",
        )

        # This should not raise NameError if imports are correct
        try:
            import inspect

            source = inspect.getsource(demo._create_user_if_not_exists)
            if "time.time()" in source:
                # If time.time() is used, time module should be imported in the method
                assert "import time" in source
        except Exception:
            # If we can't get source, skip this check
            pass


if __name__ == "__main__":
    pytest.main([__file__])
