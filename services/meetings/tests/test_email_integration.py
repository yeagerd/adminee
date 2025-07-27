"""
Tests for email integration functionality in meetings service.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from services.meetings.services.email_integration import (
    get_user_email_providers,
    send_invitation_email,
)
from services.meetings.tests.test_base import BaseMeetingsTest


class TestEmailIntegration(BaseMeetingsTest):
    """Test email integration functionality."""

    @pytest.mark.asyncio
    async def test_get_user_email_providers_success(self):
        """Test successful retrieval of user email providers."""
        mock_response = {
            "integrations": [
                {
                    "provider": "microsoft",
                    "status": "active",
                },
                {
                    "provider": "google",
                    "status": "active",
                },
            ]
        }

        # Mock the httpx.AsyncClient context manager
        mock_client = AsyncMock()
        mock_response_obj = AsyncMock()
        mock_response_obj.raise_for_status = Mock()  # Not async
        mock_response_obj.json = Mock(return_value=mock_response)  # Not async
        mock_client.get = AsyncMock(return_value=mock_response_obj)

        # Create a context manager that returns the mock client
        async def mock_context_manager():
            return mock_client

        with patch(
            "services.meetings.services.email_integration.httpx.AsyncClient"
        ) as mock_async_client:
            mock_async_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_async_client.return_value.__aexit__ = AsyncMock(return_value=None)

            providers = await get_user_email_providers("test-user-id")
            assert providers == ["microsoft", "google"]

    @pytest.mark.asyncio
    async def test_get_user_email_providers_only_microsoft(self):
        """Test retrieval when user only has Microsoft integration."""
        mock_response = {
            "integrations": [
                {
                    "provider": "microsoft",
                    "status": "active",
                }
            ]
        }

        # Mock the httpx.AsyncClient context manager
        mock_client = AsyncMock()
        mock_response_obj = AsyncMock()
        mock_response_obj.raise_for_status = Mock()  # Not async
        mock_response_obj.json = Mock(return_value=mock_response)  # Not async
        mock_client.get = AsyncMock(return_value=mock_response_obj)

        with patch(
            "services.meetings.services.email_integration.httpx.AsyncClient"
        ) as mock_async_client:
            mock_async_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_async_client.return_value.__aexit__ = AsyncMock(return_value=None)

            providers = await get_user_email_providers("test-user-id")
            assert providers == ["microsoft"]

    @pytest.mark.asyncio
    async def test_get_user_email_providers_no_providers(self):
        """Test when user has no email providers."""
        mock_response = {"integrations": []}

        # Mock the httpx.AsyncClient context manager
        mock_client = AsyncMock()
        mock_response_obj = AsyncMock()
        mock_response_obj.raise_for_status = Mock()  # Not async
        mock_response_obj.json = Mock(return_value=mock_response)  # Not async
        mock_client.get = AsyncMock(return_value=mock_response_obj)

        with patch(
            "services.meetings.services.email_integration.httpx.AsyncClient"
        ) as mock_async_client:
            mock_async_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_async_client.return_value.__aexit__ = AsyncMock(return_value=None)

            providers = await get_user_email_providers("test-user-id")
            assert providers == []

    @pytest.mark.asyncio
    async def test_send_invitation_email_with_provider(self):
        """Test sending email with specific provider."""
        mock_response = {"success": True, "message_id": "test-123"}

        # Mock the httpx.AsyncClient context manager
        mock_client = AsyncMock()
        mock_response_obj = AsyncMock()
        mock_response_obj.raise_for_status = Mock()  # Not async
        mock_response_obj.json = Mock(return_value=mock_response)  # Not async
        mock_client.post = AsyncMock(return_value=mock_response_obj)

        with patch(
            "services.meetings.services.email_integration.httpx.AsyncClient"
        ) as mock_async_client:
            mock_async_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_async_client.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await send_invitation_email(
                "test@example.com",
                "Test Subject",
                "Test Body",
                "test-user-id",
                provider="microsoft",
            )
            assert result == mock_response

    @pytest.mark.asyncio
    async def test_send_invitation_email_auto_detect_microsoft(self):
        """Test sending email with automatic Microsoft provider detection."""
        mock_send_response = {"success": True, "message_id": "test-123"}

        # Mock the httpx.AsyncClient context manager
        mock_client = AsyncMock()
        mock_response_obj = AsyncMock()
        mock_response_obj.raise_for_status = Mock()  # Not async
        mock_response_obj.json = Mock(return_value=mock_send_response)  # Not async
        mock_client.post = AsyncMock(return_value=mock_response_obj)

        with (
            patch(
                "services.meetings.services.email_integration.httpx.AsyncClient"
            ) as mock_async_client,
            patch(
                "services.meetings.services.email_integration.get_user_email_providers"
            ) as mock_get_providers,
        ):
            mock_async_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_async_client.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_providers.return_value = ["microsoft"]

            result = await send_invitation_email(
                "test@example.com", "Test Subject", "Test Body", "test-user-id"
            )
            assert result == mock_send_response

    @pytest.mark.asyncio
    async def test_send_invitation_email_auto_detect_google(self):
        """Test sending email with automatic Google provider detection."""
        mock_send_response = {"success": True, "message_id": "test-123"}

        # Mock the httpx.AsyncClient context manager
        mock_client = AsyncMock()
        mock_response_obj = AsyncMock()
        mock_response_obj.raise_for_status = Mock()  # Not async
        mock_response_obj.json = Mock(return_value=mock_send_response)  # Not async
        mock_client.post = AsyncMock(return_value=mock_response_obj)

        with (
            patch(
                "services.meetings.services.email_integration.httpx.AsyncClient"
            ) as mock_async_client,
            patch(
                "services.meetings.services.email_integration.get_user_email_providers"
            ) as mock_get_providers,
        ):
            mock_async_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_async_client.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_providers.return_value = ["google"]

            result = await send_invitation_email(
                "test@example.com", "Test Subject", "Test Body", "test-user-id"
            )
            assert result == mock_send_response

    @pytest.mark.asyncio
    async def test_send_invitation_email_no_providers(self):
        """Test sending email when user has no email providers."""
        with patch(
            "services.meetings.services.email_integration.get_user_email_providers"
        ) as mock_get_providers:
            mock_get_providers.return_value = []

            with pytest.raises(ValueError) as exc_info:
                await send_invitation_email(
                    "test@example.com", "Test Subject", "Test Body", "test-user-id"
                )
            assert "no connected email providers" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_send_invitation_email_prefer_microsoft(self):
        """Test that Microsoft is preferred when both providers are available."""
        mock_send_response = {"success": True, "message_id": "test-123"}

        # Mock the httpx.AsyncClient context manager
        mock_client = AsyncMock()
        mock_response_obj = AsyncMock()
        mock_response_obj.raise_for_status = Mock()  # Not async
        mock_response_obj.json = Mock(return_value=mock_send_response)  # Not async
        mock_client.post = AsyncMock(return_value=mock_response_obj)

        with (
            patch(
                "services.meetings.services.email_integration.httpx.AsyncClient"
            ) as mock_async_client,
            patch(
                "services.meetings.services.email_integration.get_user_email_providers"
            ) as mock_get_providers,
        ):
            mock_async_client.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_async_client.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_providers.return_value = ["google", "microsoft"]

            result = await send_invitation_email(
                "test@example.com", "Test Subject", "Test Body", "test-user-id"
            )
            assert result == mock_send_response
