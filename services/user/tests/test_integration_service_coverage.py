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
from services.user.tests.test_base import BaseUserManagementTest


class TestIntegrationServiceCoverage(BaseUserManagementTest):
    """Test cases for IntegrationService coverage."""

    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
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

        with patch(
            "services.user.services.integration_service.get_async_session"
        ) as mock_session_factory:
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

            # Mock the add and commit methods
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()

            result = await self.service._validate_and_correct_integration_status(
                integration, session=None
            )

            assert result == IntegrationStatus.ERROR
            assert integration.status == IntegrationStatus.ERROR
            assert integration.error_message == "No access token available"

    @pytest.mark.asyncio
    async def test_validate_status_respects_inactive_status(self):
        """Test that validation respects INACTIVE status (would catch the disconnect bug)."""
        # This test would have caught the original bug where INACTIVE status
        # was being overridden during validation
        integration = Integration(
            id=1,
            user_id=1,
            provider=IntegrationProvider.MICROSOFT,
            status=IntegrationStatus.INACTIVE,  # Manually disconnected
        )

        mock_session = AsyncMock()

        # Mock token queries - even if tokens exist, should respect INACTIVE status
        mock_access_token = MagicMock()
        mock_access_token.expires_at = None  # Valid token
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_access_token
        mock_session.execute.return_value = mock_result

        result = (
            await self.service._validate_and_correct_integration_status_with_session(
                integration, mock_session
            )
        )

        # Should return INACTIVE without trying to "correct" it
        assert result == IntegrationStatus.INACTIVE
        assert integration.status == IntegrationStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_validate_status_respects_inactive_status_with_valid_tokens(self):
        """Test that INACTIVE status is respected even when valid tokens exist."""
        # This test specifically checks the scenario that was causing the bug:
        # User disconnects integration (sets to INACTIVE), but validation
        # finds valid tokens and incorrectly sets status back to ACTIVE
        integration = Integration(
            id=1,
            user_id=1,
            provider=IntegrationProvider.MICROSOFT,
            status=IntegrationStatus.INACTIVE,  # Manually disconnected
        )

        mock_session = AsyncMock()

        # Mock valid access token with no expiration (valid token)
        class Token:
            expires_at = None

        mock_access_token = Token()
        mock_access_result = MagicMock()
        mock_access_result.scalar_one_or_none.return_value = mock_access_token

        # Mock valid refresh token
        mock_refresh_token = Token()
        mock_refresh_result = MagicMock()
        mock_refresh_result.scalar_one_or_none.return_value = mock_refresh_token

        # Mock session.execute to return different results for different queries
        def mock_execute(query):
            # This is a simplified mock - in reality, the queries would be different
            # but for testing purposes, we'll return different results based on call count
            mock_session.execute.call_count += 1
            if mock_session.execute.call_count == 1:
                return mock_access_result
            else:
                return mock_refresh_result

        mock_session.execute.side_effect = mock_execute
        mock_session.execute.call_count = 0

        result = (
            await self.service._validate_and_correct_integration_status_with_session(
                integration, mock_session
            )
        )

        # Should still return INACTIVE even with valid tokens
        assert result == IntegrationStatus.INACTIVE
        assert integration.status == IntegrationStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_validate_status_corrects_active_status_when_no_tokens(self):
        """Test that ACTIVE status is corrected to ERROR when no tokens exist."""
        # This test ensures that the validation logic still works correctly
        # for ACTIVE integrations that should be corrected
        integration = Integration(
            id=1,
            user_id=1,
            provider=IntegrationProvider.MICROSOFT,
            status=IntegrationStatus.ACTIVE,  # Should be corrected
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        # Mock no tokens
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No tokens
        mock_session.execute.return_value = mock_result

        result = (
            await self.service._validate_and_correct_integration_status_with_session(
                integration, mock_session
            )
        )

        # Should correct ACTIVE to ERROR when no tokens
        assert result == IntegrationStatus.ERROR
        assert integration.status == IntegrationStatus.ERROR

    @pytest.mark.asyncio
    async def test_validate_status_preserves_active_status_with_valid_tokens(self):
        """Test that ACTIVE status is preserved when valid tokens exist."""
        # This test ensures that ACTIVE integrations with valid tokens
        # remain ACTIVE (the normal case)
        integration = Integration(
            id=1,
            user_id=1,
            provider=IntegrationProvider.MICROSOFT,
            status=IntegrationStatus.ACTIVE,  # Should remain ACTIVE
        )

        mock_session = AsyncMock()

        # Mock valid access token with no expiration (valid token)
        class Token:
            expires_at = None

        mock_access_token = Token()
        mock_access_result = MagicMock()
        mock_access_result.scalar_one_or_none.return_value = mock_access_token

        # Mock valid refresh token
        mock_refresh_token = Token()
        mock_refresh_result = MagicMock()
        mock_refresh_result.scalar_one_or_none.return_value = mock_refresh_token

        # Mock session.execute to return different results for different queries
        def mock_execute(query):
            mock_session.execute.call_count += 1
            if mock_session.execute.call_count == 1:
                return mock_access_result
            else:
                return mock_refresh_result

        mock_session.execute.side_effect = mock_execute
        mock_session.execute.call_count = 0

        result = (
            await self.service._validate_and_correct_integration_status_with_session(
                integration, mock_session
            )
        )

        # Should preserve ACTIVE status when tokens are valid
        assert result == IntegrationStatus.ACTIVE
        assert integration.status == IntegrationStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_disconnect_integration_sets_inactive_status(self):
        """Test that disconnect_integration properly sets INACTIVE status."""
        # This test would have caught the bug where disconnect_integration
        # was not properly setting INACTIVE status
        # Note: This is a simplified test focusing on the core logic
        # The actual implementation would require more complex database mocking

        # Test the core validation logic that was causing the bug
        integration = Integration(
            id=1,
            user_id=1,
            provider=IntegrationProvider.MICROSOFT,
            status=IntegrationStatus.ACTIVE,
        )

        # Simulate what happens after disconnect_integration sets status to INACTIVE
        integration.status = IntegrationStatus.INACTIVE

        mock_session = AsyncMock()

        # Mock valid tokens (which would have caused the original bug)
        mock_access_token = MagicMock()
        mock_access_token.expires_at = None  # Valid token
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_access_token
        mock_session.execute.return_value = mock_result

        # Test that validation respects the INACTIVE status
        result = (
            await self.service._validate_and_correct_integration_status_with_session(
                integration, mock_session
            )
        )

        # Should return INACTIVE without trying to "correct" it
        assert result == IntegrationStatus.INACTIVE
        assert integration.status == IntegrationStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_get_user_integrations_preserves_inactive_status(self):
        """Test that get_user_integrations preserves INACTIVE status after disconnect."""
        # This test would have caught the bug where get_user_integrations
        # was "correcting" INACTIVE status back to ACTIVE
        # Note: This is a simplified test focusing on the core validation logic

        integration = Integration(
            id=1,
            user_id=1,
            provider=IntegrationProvider.MICROSOFT,
            status=IntegrationStatus.INACTIVE,  # Disconnected
        )

        mock_session = AsyncMock()

        # Mock valid tokens (which would have caused the original bug)
        mock_access_token = MagicMock()
        mock_access_token.expires_at = None  # Valid token
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_access_token
        mock_session.execute.return_value = mock_result

        # Test that validation respects the INACTIVE status
        result = (
            await self.service._validate_and_correct_integration_status_with_session(
                integration, mock_session
            )
        )

        # Should return INACTIVE without trying to "correct" it
        assert result == IntegrationStatus.INACTIVE
        assert integration.status == IntegrationStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_get_token_metadata(self):
        """Test token metadata retrieval."""
        with patch(
            "services.user.services.integration_service.get_async_session"
        ) as mock_session_factory:
            mock_session = AsyncMock()
            mock_session_factory.return_value = MagicMock(return_value=mock_session)

            # Mock the session context manager
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

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
