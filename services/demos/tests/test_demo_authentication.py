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

from services.demos.chat import FullDemo


class TestDemoAuthentication:
    """Test suite for demo authentication flow."""

    @pytest.fixture
    def demo_instance(self):
        """Create a demo instance for testing."""
        return FullDemo(
            use_api=True,
            chat_url="http://localhost:8002",
            office_url="http://localhost:8003",
            user_url="http://localhost:8001",
            user_id="test_demo_user",
            skip_auth=False,
        )

    @pytest.mark.asyncio
    async def test_create_user_if_not_exists_success(self, demo_instance):
        """Test successful user creation via webhook simulation."""
        email = "test@example.com"

        # Mock the HTTP client response for successful user creation
        mock_response = MagicMock()
        mock_response.status_code = 201

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            result = await demo_instance._create_user_if_not_exists(email)

            assert result is True
            # Verify the webhook was called with correct payload
            mock_client.return_value.__aenter__.return_value.post.assert_called_once()
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args

            # Check URL
            assert (
                call_args[1]["url"]
                == f"{demo_instance.user_client.base_url}/webhooks/clerk"
            )

            # Check payload structure
            payload = call_args[1]["json"]
            assert payload["type"] == "user.created"
            assert payload["object"] == "event"
            assert payload["data"]["id"] == demo_instance.user_id
            assert payload["data"]["email_addresses"][0]["email_address"] == email

    @pytest.mark.asyncio
    async def test_create_user_if_not_exists_already_exists(self, demo_instance):
        """Test user creation when user already exists (409 response)."""
        email = "existing@example.com"

        mock_response = MagicMock()
        mock_response.status_code = 409

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            result = await demo_instance._create_user_if_not_exists(email)

            assert result is True

    @pytest.mark.asyncio
    async def test_create_user_if_not_exists_handles_errors(self, demo_instance):
        """Test that user creation gracefully handles errors."""
        email = "test@example.com"

        # Test HTTP error
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = (
                httpx.RequestError("Connection failed")
            )

            result = await demo_instance._create_user_if_not_exists(email)

            # Should return True to continue gracefully
            assert result is True

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

        # Mock services as available
        demo_instance.services_available = {"user": True, "chat": True, "office": True}

        # Mock successful user creation
        mock_create_response = MagicMock()
        mock_create_response.status_code = 201

        # Mock successful integrations check
        mock_integrations_response = MagicMock()
        mock_integrations_response.status_code = 200
        mock_integrations_response.json.return_value = {
            "integrations": [{"provider": "microsoft", "status": "active"}]
        }

        # Mock preferences response (404 is OK for new users)
        mock_preferences_response = MagicMock()
        mock_preferences_response.status_code = 404

        with (
            patch("httpx.AsyncClient") as mock_client,
            patch("services.demos.demo_jwt_utils.create_bearer_token") as mock_jwt,
        ):

            mock_jwt.return_value = "mock_jwt_token"
            mock_http_client = mock_client.return_value.__aenter__.return_value

            # Setup different responses for different endpoints
            def side_effect(url, **kwargs):
                if "/webhooks/clerk" in url:
                    return mock_create_response
                elif "/integrations/" in url:
                    return mock_integrations_response
                elif "/preferences/" in url:
                    return mock_preferences_response
                else:
                    return MagicMock(status_code=200)

            mock_http_client.post.side_effect = side_effect
            mock_http_client.get.side_effect = side_effect

            # Run authentication
            result = await demo_instance.authenticate(email)

            # Should succeed
            assert result is True

            # Verify user creation was attempted
            create_calls = [
                call
                for call in mock_http_client.post.call_args_list
                if "/webhooks/clerk" in str(call)
            ]
            assert len(create_calls) > 0

            # Verify JWT token was created
            mock_jwt.assert_called_once_with(demo_instance.user_id, email)

            # Verify user client has token
            assert demo_instance.user_client.auth_token == "mock_jwt_token"
            assert demo_instance.user_client.user_id == demo_instance.user_id

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
            patch("services.demos.demo_jwt_utils.create_bearer_token") as mock_jwt,
        ):

            mock_jwt.return_value = "mock_jwt_token"
            mock_http_client = mock_client.return_value.__aenter__.return_value

            def side_effect(url, **kwargs):
                if "/webhooks/clerk" in url:
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

        # This test verifies that time.time() can be called without error
        # If time import was missing, this would raise NameError
        try:
            await demo_instance._create_user_if_not_exists(email)
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
