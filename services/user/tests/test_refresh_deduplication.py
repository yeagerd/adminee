"""
Test refresh deduplication to ensure it doesn't cause upstream failures.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from services.user.models.integration import IntegrationProvider
from services.user.services.integration_service import IntegrationService


class TestRefreshDeduplication:
    """Test that refresh deduplication works correctly."""

    @pytest.fixture
    def integration_service(self):
        """Create an integration service instance."""
        return IntegrationService()

    @pytest.mark.asyncio
    async def test_refresh_deduplication_waits_for_completion(
        self, integration_service
    ):
        """Test that duplicate refresh requests wait for the first one to complete."""
        user_id = "test_user"
        provider = IntegrationProvider.MICROSOFT

        # Mock the database operations to simulate a delay
        with patch.object(
            integration_service, "_get_user_integration_in_session"
        ) as mock_get_integration:
            mock_integration = AsyncMock()
            mock_integration.id = 1
            mock_get_integration.return_value = mock_integration

            # Mock token operations
            with patch.object(
                integration_service, "_store_encrypted_tokens"
            ) as mock_store:
                mock_store.return_value = None

                # Mock OAuth refresh
                with patch.object(
                    integration_service.oauth_config, "refresh_access_token"
                ) as mock_refresh:
                    mock_refresh.return_value = {
                        "access_token": "new_access_token",
                        "refresh_token": "new_refresh_token",
                        "expires_in": 3600,
                    }

                    # Start two concurrent refresh operations
                    async def refresh_operation():
                        return await integration_service.refresh_integration_tokens(
                            user_id=user_id, provider=provider, force=True
                        )

                    # Run both operations concurrently
                    results = await asyncio.gather(
                        refresh_operation(), refresh_operation(), return_exceptions=True
                    )

                    # Both should succeed and return the same result
                    assert len(results) == 2
                    assert not any(isinstance(r, Exception) for r in results)

                    # Both results should be identical (same refresh operation)
                    result1, result2 = results
                    assert result1.success == result2.success
                    assert result1.integration_id == result2.integration_id
                    assert result1.provider == result2.provider

    @pytest.mark.asyncio
    async def test_refresh_deduplication_handles_failures(self, integration_service):
        """Test that refresh failures are properly propagated to waiting callers."""
        user_id = "test_user"
        provider = IntegrationProvider.MICROSOFT

        # Mock the database operations
        with patch.object(
            integration_service, "_get_user_integration_in_session"
        ) as mock_get_integration:
            mock_integration = AsyncMock()
            mock_integration.id = 1
            mock_get_integration.return_value = mock_integration

            # Mock OAuth refresh to fail
            with patch.object(
                integration_service.oauth_config, "refresh_access_token"
            ) as mock_refresh:
                mock_refresh.side_effect = Exception("OAuth refresh failed")

                # Start two concurrent refresh operations
                async def refresh_operation():
                    return await integration_service.refresh_integration_tokens(
                        user_id=user_id, provider=provider, force=True
                    )

                # Run both operations concurrently
                results = await asyncio.gather(
                    refresh_operation(), refresh_operation(), return_exceptions=True
                )

                # Both should fail with the same exception
                assert len(results) == 2
                assert all(isinstance(r, Exception) for r in results)
                assert str(results[0]) == str(results[1])

    @pytest.mark.asyncio
    async def test_refresh_deduplication_cleanup(self, integration_service):
        """Test that refresh keys are properly cleaned up after completion."""
        user_id = "test_user"
        provider = IntegrationProvider.MICROSOFT
        refresh_key = f"{user_id}:{provider.value}"

        # Initially, no refresh should be in progress
        assert refresh_key not in integration_service._ongoing_refreshes

        # Mock the database operations
        with patch.object(
            integration_service, "_get_user_integration_in_session"
        ) as mock_get_integration:
            mock_integration = AsyncMock()
            mock_integration.id = 1
            mock_get_integration.return_value = mock_integration

            # Mock token operations
            with patch.object(
                integration_service, "_store_encrypted_tokens"
            ) as mock_store:
                mock_store.return_value = None

                # Mock OAuth refresh
                with patch.object(
                    integration_service.oauth_config, "refresh_access_token"
                ) as mock_refresh:
                    mock_refresh.return_value = {
                        "access_token": "new_access_token",
                        "refresh_token": "new_refresh_token",
                        "expires_in": 3600,
                    }

                    # Start a refresh operation
                    result = await integration_service.refresh_integration_tokens(
                        user_id=user_id, provider=provider, force=True
                    )

                    # After completion, the refresh key should be cleaned up
                    assert refresh_key not in integration_service._ongoing_refreshes
                    assert result.success is True

    @pytest.mark.asyncio
    async def test_refresh_deduplication_timeout(self, integration_service):
        """Test that refresh operations timeout properly to prevent deadlocks."""
        user_id = "test_user"
        provider = IntegrationProvider.MICROSOFT

        # Mock the database operations
        with patch.object(
            integration_service, "_get_user_integration_in_session"
        ) as mock_get_integration:
            mock_integration = AsyncMock()
            mock_integration.id = 1
            mock_get_integration.return_value = mock_integration

            # Mock OAuth refresh to hang indefinitely
            with patch.object(
                integration_service.oauth_config, "refresh_access_token"
            ) as mock_refresh:
                # Create a future that never completes
                hanging_future = asyncio.Future()
                mock_refresh.return_value = hanging_future

                # Start a refresh operation that will hang
                refresh_task = asyncio.create_task(
                    integration_service.refresh_integration_tokens(
                        user_id=user_id, provider=provider, force=True
                    )
                )

                # Wait a bit for the first operation to start
                await asyncio.sleep(0.1)

                # Start a second refresh operation that should timeout waiting for the first
                start_time = asyncio.get_event_loop().time()
                await integration_service.refresh_integration_tokens(
                    user_id=user_id, provider=provider, force=True
                )
                end_time = asyncio.get_event_loop().time()

                # The second operation should timeout and proceed with its own refresh
                # It should complete in less than 35 seconds (30s timeout + buffer)
                assert end_time - start_time < 35.0

                # Cancel the hanging task
                refresh_task.cancel()
                try:
                    await refresh_task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_refresh_deduplication_timeout_cleanup(self, integration_service):
        """Test that timeout cleanup properly removes the hanging refresh from tracking."""
        user_id = "test_user"
        provider = IntegrationProvider.MICROSOFT

        # Mock the database operations
        with patch.object(
            integration_service, "_get_user_integration_in_session"
        ) as mock_get_integration:
            mock_integration = AsyncMock()
            mock_integration.id = 1
            mock_get_integration.return_value = mock_integration

            # Mock OAuth refresh to hang indefinitely
            with patch.object(
                integration_service.oauth_config, "refresh_access_token"
            ) as mock_refresh:
                # Create a future that never completes
                hanging_future = asyncio.Future()
                mock_refresh.return_value = hanging_future

                # Start a refresh operation that will hang
                refresh_task = asyncio.create_task(
                    integration_service.refresh_integration_tokens(
                        user_id=user_id, provider=provider, force=True
                    )
                )

                # Wait a bit for the first operation to start
                await asyncio.sleep(0.1)

                # Verify the refresh is being tracked
                assert (
                    f"{user_id}:{provider.value}"
                    in integration_service._ongoing_refreshes
                )

                # Start a second refresh operation that should timeout and clean up
                await integration_service.refresh_integration_tokens(
                    user_id=user_id, provider=provider, force=True
                )

                # The hanging refresh should be removed from tracking
                assert (
                    f"{user_id}:{provider.value}"
                    not in integration_service._ongoing_refreshes
                )

                # Cancel the hanging task
                refresh_task.cancel()
                try:
                    await refresh_task
                except asyncio.CancelledError:
                    pass
