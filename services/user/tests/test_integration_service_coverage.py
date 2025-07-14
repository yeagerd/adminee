"""
Coverage tests for IntegrationService.

Simple tests to ensure good coverage of the key functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.user.models.integration import (
    Integration,
    IntegrationProvider,
    IntegrationStatus,
)
from services.user.services.integration_service import IntegrationService


class TestIntegrationServiceCoverage:
    """Test cases for IntegrationService coverage."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = IntegrationService()

    @pytest.mark.asyncio
    async def test_validate_status_no_integration_id(self):
        """Test validation when integration has no ID."""
        integration = Integration(
            id=None,
            user_id=1,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.PENDING,
        )

        result = await self.service._validate_and_correct_integration_status(
            integration
        )
        assert result == IntegrationStatus.PENDING

    @pytest.mark.asyncio
    async def test_validate_status_with_session_creation(self):
        """Test validation when no session is provided (creates its own session)."""
        integration = Integration(
            id=1,
            user_id=1,
            provider=IntegrationProvider.GOOGLE,
            status=IntegrationStatus.ACTIVE,
        )

        with patch("services.user.database.get_async_session") as mock_session_factory:
            # Create a mock session context manager
            mock_session = AsyncMock()
            mock_session_factory.return_value = MagicMock(return_value=mock_session)

            # Mock the session context manager
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            # Mock the execute method to return a result with scalar_one_or_none
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None  # No tokens
            mock_session.execute.return_value = mock_result

            result = await self.service._validate_and_correct_integration_status(
                integration, session=None
            )

            assert result == IntegrationStatus.ERROR
            assert integration.status == IntegrationStatus.ERROR
            assert integration.error_message == "No access token available"

    @pytest.mark.asyncio
    async def test_get_token_metadata(self):
        """Test token metadata retrieval."""
        with patch("services.user.database.get_async_session") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value = MagicMock(return_value=mock_session)

            # Mock the execute method
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None  # No tokens
            mock_session.execute.return_value = mock_result

            result = await self.service._get_token_metadata(integration_id=1)

            assert result["has_access_token"] is False
            assert result["has_refresh_token"] is False
            assert result["expires_at"] is None
            assert result["created_at"] is None

    @pytest.mark.asyncio
    async def test_get_error_count(self):
        """Test error count retrieval."""
        with patch("services.user.database.get_async_session") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value = MagicMock(return_value=mock_session)

            # Mock the execute method
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None  # No integration found
            mock_session.execute.return_value = mock_result

            result = await self.service._get_error_count(integration_id=999)
            assert result == 0

    @pytest.mark.asyncio
    async def test_start_oauth_flow_provider_unavailable(self):
        """Test OAuth flow initiation with unavailable provider."""
        with patch.object(
            self.service.oauth_config, "is_provider_available"
        ) as mock_available:
            mock_available.return_value = False

            with pytest.raises(Exception):  # Should raise some kind of error
                await self.service.start_oauth_flow(
                    user_id="test_user_123", provider=IntegrationProvider.GOOGLE
                )

    @pytest.mark.asyncio
    async def test_get_user_integrations_user_not_found(self):
        """Test retrieval when user is not found."""
        with patch("services.user.database.get_async_session") as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value = MagicMock(return_value=mock_session)

            # Mock user not found
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None  # User not found
            mock_session.execute.return_value = mock_result

            with pytest.raises(Exception):  # Should raise NotFoundError
                await self.service.get_user_integrations("nonexistent_user")

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test that the service initializes correctly."""
        service = IntegrationService()
        assert service is not None
        assert hasattr(service, "oauth_config")

    @pytest.mark.asyncio
    async def test_get_integration_service_singleton(self):
        """Test the singleton pattern for getting the integration service."""
        from services.user.services.integration_service import get_integration_service

        service1 = get_integration_service()
        service2 = get_integration_service()

        assert service1 is service2  # Should be the same instance


if __name__ == "__main__":
    pytest.main([__file__])
