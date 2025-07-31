"""
Test refresh deduplication to ensure it doesn't cause upstream failures.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from services.user.models.integration import IntegrationProvider
from services.user.services.integration_service import IntegrationService


class TestRefreshDeduplication:
    """Test that refresh deduplication works correctly."""

    def _setup_mock_session(self):
        """Helper to set up a properly mocked database session."""
        mock_session_instance = AsyncMock()
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)
        return mock_session_instance

    @pytest.fixture
    def integration_service(self):
        """Create an integration service instance."""
        return IntegrationService()

    @pytest.mark.asyncio
    async def test_refresh_deduplication_waits_for_completion(
        self, integration_service
    ):
        user_id = "test_user"
        provider = IntegrationProvider.MICROSOFT

        with patch(
            "services.user.services.integration_service.get_async_session"
        ) as mock_session:
            mock_session_instance = self._setup_mock_session()
            mock_session.return_value = lambda: mock_session_instance

            with patch.object(
                integration_service, "_get_user_integration_in_session"
            ) as mock_get_integration:
                mock_integration = AsyncMock()
                mock_integration.id = 1
                mock_get_integration.return_value = mock_integration

                from unittest.mock import Mock

                mock_access_token = Mock()
                mock_access_token.encrypted_value = "encrypted_access_token"
                mock_access_token.expires_at = datetime.now(timezone.utc) + timedelta(
                    hours=1
                )
                mock_refresh_token = Mock()
                mock_refresh_token.encrypted_value = "encrypted_refresh_token"
                calls = [mock_access_token, mock_refresh_token]

                def scalar_one_or_none():
                    return calls.pop(0)

                mock_result = Mock()
                mock_result.scalar_one_or_none.side_effect = scalar_one_or_none
                mock_session_instance.execute.return_value = mock_result

                with patch.object(
                    integration_service.token_encryption, "decrypt_token"
                ) as mock_decrypt:
                    mock_decrypt.side_effect = (
                        lambda encrypted_token, user_id: f"decrypted_{encrypted_token}"
                    )

                    with patch.object(
                        integration_service, "_store_encrypted_tokens"
                    ) as mock_store:
                        mock_store.return_value = None
                        with patch.object(
                            integration_service.oauth_config, "refresh_access_token"
                        ) as mock_refresh:
                            mock_refresh.return_value = {
                                "access_token": "new_access_token",
                                "refresh_token": "new_refresh_token",
                                "expires_in": 3600,
                            }

                            async def refresh_operation():
                                return await integration_service.refresh_integration_tokens(
                                    user_id=user_id, provider=provider, force=True
                                )

                            results = await asyncio.gather(
                                refresh_operation(),
                                refresh_operation(),
                                return_exceptions=True,
                            )
                            assert len(results) == 2
                            assert not any(isinstance(r, Exception) for r in results)
                            result1, result2 = results
                            assert result1.success == result2.success
                            assert result1.integration_id == result2.integration_id
                            assert result1.provider == result2.provider

    @pytest.mark.asyncio
    async def test_refresh_deduplication_handles_failures(self, integration_service):
        """Test that refresh failures are properly propagated to waiting callers."""
        user_id = "test_user"
        provider = IntegrationProvider.MICROSOFT

        # Mock the database session
        with patch(
            "services.user.services.integration_service.get_async_session"
        ) as mock_session:
            mock_session_instance = self._setup_mock_session()
            mock_session.return_value = lambda: mock_session_instance

            # Mock the integration retrieval
            with patch.object(
                integration_service, "_get_user_integration_in_session"
            ) as mock_get_integration:
                mock_integration = AsyncMock()
                mock_integration.id = 1
                mock_get_integration.return_value = mock_integration

                from unittest.mock import Mock

                mock_access_token = Mock()
                mock_access_token.encrypted_value = "encrypted_access_token"
                mock_access_token.expires_at = datetime.now(timezone.utc) + timedelta(
                    hours=1
                )

                mock_refresh_token = Mock()
                mock_refresh_token.encrypted_value = "encrypted_refresh_token"

                async def return_access_token():
                    return mock_access_token

                async def return_refresh_token():
                    return mock_refresh_token

                mock_result = Mock()
                mock_result.scalar_one_or_none.side_effect = [
                    return_access_token(),
                    return_refresh_token(),
                ]
                mock_session_instance.execute.return_value = mock_result

                # Mock token decryption
                with patch.object(
                    integration_service.token_encryption, "decrypt_token"
                ) as mock_decrypt:
                    mock_decrypt.side_effect = (
                        lambda encrypted_token, user_id: f"decrypted_{encrypted_token}"
                    )

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
        user_id = "test_user"
        provider = IntegrationProvider.MICROSOFT
        refresh_key = f"{user_id}:{provider.value}"
        assert refresh_key not in integration_service._ongoing_refreshes
        with patch(
            "services.user.services.integration_service.get_async_session"
        ) as mock_session:
            mock_session_instance = self._setup_mock_session()
            mock_session.return_value = lambda: mock_session_instance
            with patch.object(
                integration_service, "_get_user_integration_in_session"
            ) as mock_get_integration:
                mock_integration = AsyncMock()
                mock_integration.id = 1
                mock_get_integration.return_value = mock_integration
                from unittest.mock import Mock

                mock_access_token = Mock()
                mock_access_token.encrypted_value = "encrypted_access_token"
                mock_access_token.expires_at = datetime.now(timezone.utc) + timedelta(
                    hours=1
                )
                mock_refresh_token = Mock()
                mock_refresh_token.encrypted_value = "encrypted_refresh_token"
                calls = [mock_access_token, mock_refresh_token]

                def scalar_one_or_none():
                    return calls.pop(0)

                mock_result = Mock()
                mock_result.scalar_one_or_none.side_effect = scalar_one_or_none
                mock_session_instance.execute.return_value = mock_result
                with patch.object(
                    integration_service.token_encryption, "decrypt_token"
                ) as mock_decrypt:
                    mock_decrypt.side_effect = (
                        lambda encrypted_token, user_id: f"decrypted_{encrypted_token}"
                    )
                    with patch.object(
                        integration_service, "_store_encrypted_tokens"
                    ) as mock_store:
                        mock_store.return_value = None
                        with patch.object(
                            integration_service.oauth_config, "refresh_access_token"
                        ) as mock_refresh:
                            mock_refresh.return_value = {
                                "access_token": "new_access_token",
                                "refresh_token": "new_refresh_token",
                                "expires_in": 3600,
                            }
                            result = (
                                await integration_service.refresh_integration_tokens(
                                    user_id=user_id, provider=provider, force=True
                                )
                            )
                            assert (
                                refresh_key
                                not in integration_service._ongoing_refreshes
                            )
                            assert result.success is True

    @pytest.mark.asyncio
    async def test_refresh_deduplication_timeout(self, integration_service):
        user_id = "test_user"
        provider = IntegrationProvider.MICROSOFT
        with patch(
            "services.user.services.integration_service.get_async_session"
        ) as mock_session:
            mock_session_instance = self._setup_mock_session()
            mock_session.return_value = lambda: mock_session_instance
            with patch.object(
                integration_service, "_get_user_integration_in_session"
            ) as mock_get_integration:
                mock_integration = AsyncMock()
                mock_integration.id = 1
                mock_get_integration.return_value = mock_integration
                from unittest.mock import Mock

                mock_access_token = Mock()
                mock_access_token.encrypted_value = "encrypted_access_token"
                mock_access_token.expires_at = datetime.now(timezone.utc) + timedelta(
                    hours=1
                )
                mock_refresh_token = Mock()
                mock_refresh_token.encrypted_value = "encrypted_refresh_token"
                calls = [mock_access_token, mock_refresh_token]

                def scalar_one_or_none():
                    if calls:
                        return calls.pop(0)
                    return mock_refresh_token

                mock_result = Mock()
                mock_result.scalar_one_or_none.side_effect = scalar_one_or_none
                mock_session_instance.execute.return_value = mock_result
                with patch.object(
                    integration_service.token_encryption, "decrypt_token"
                ) as mock_decrypt:
                    mock_decrypt.side_effect = (
                        lambda encrypted_token, user_id: f"decrypted_{encrypted_token}"
                    )
                    with patch.object(
                        integration_service, "_store_encrypted_tokens"
                    ) as mock_store:
                        mock_store.return_value = None
                        with patch.object(
                            integration_service.oauth_config, "refresh_access_token"
                        ) as mock_refresh:
                            # Use side_effect to return different values based on call count
                            call_count = 0

                            async def refresh_side_effect(*args, **kwargs):
                                nonlocal call_count
                                call_count += 1
                                if call_count == 1:
                                    # First call hangs indefinitely
                                    await asyncio.Future()  # This will never complete
                                else:
                                    # Subsequent calls return a valid dict
                                    return {
                                        "access_token": "new_access_token",
                                        "refresh_token": "new_refresh_token",
                                        "expires_in": 3600,
                                    }

                            mock_refresh.side_effect = refresh_side_effect

                            refresh_task = asyncio.create_task(
                                integration_service.refresh_integration_tokens(
                                    user_id=user_id, provider=provider, force=True
                                )
                            )
                            await asyncio.sleep(0.1)
                            start_time = asyncio.get_event_loop().time()
                            await integration_service.refresh_integration_tokens(
                                user_id=user_id, provider=provider, force=True
                            )
                            end_time = asyncio.get_event_loop().time()
                            assert end_time - start_time < 35.0
                            refresh_task.cancel()
                            try:
                                await refresh_task
                            except asyncio.CancelledError:
                                pass

    @pytest.mark.asyncio
    async def test_refresh_deduplication_timeout_cleanup(self, integration_service):
        user_id = "test_user"
        provider = IntegrationProvider.MICROSOFT
        with patch(
            "services.user.services.integration_service.get_async_session"
        ) as mock_session:
            mock_session_instance = self._setup_mock_session()
            mock_session.return_value = lambda: mock_session_instance
            with patch.object(
                integration_service, "_get_user_integration_in_session"
            ) as mock_get_integration:
                mock_integration = AsyncMock()
                mock_integration.id = 1
                mock_get_integration.return_value = mock_integration
                from unittest.mock import Mock

                mock_access_token = Mock()
                mock_access_token.encrypted_value = "encrypted_access_token"
                mock_access_token.expires_at = datetime.now(timezone.utc) + timedelta(
                    hours=1
                )
                mock_refresh_token = Mock()
                mock_refresh_token.encrypted_value = "encrypted_refresh_token"
                calls = [mock_access_token, mock_refresh_token]

                def scalar_one_or_none():
                    if calls:
                        return calls.pop(0)
                    return mock_refresh_token

                mock_result = Mock()
                mock_result.scalar_one_or_none.side_effect = scalar_one_or_none
                mock_session_instance.execute.return_value = mock_result
                with patch.object(
                    integration_service.token_encryption, "decrypt_token"
                ) as mock_decrypt:
                    mock_decrypt.side_effect = (
                        lambda encrypted_token, user_id: f"decrypted_{encrypted_token}"
                    )
                    with patch.object(
                        integration_service, "_store_encrypted_tokens"
                    ) as mock_store:
                        mock_store.return_value = None
                        with patch.object(
                            integration_service.oauth_config, "refresh_access_token"
                        ) as mock_refresh:
                            # Use side_effect to return different values based on call count
                            call_count = 0

                            async def refresh_side_effect(*args, **kwargs):
                                nonlocal call_count
                                call_count += 1
                                if call_count == 1:
                                    # First call hangs indefinitely
                                    await asyncio.Future()  # This will never complete
                                else:
                                    # Subsequent calls return a valid dict
                                    return {
                                        "access_token": "new_access_token",
                                        "refresh_token": "new_refresh_token",
                                        "expires_in": 3600,
                                    }

                            mock_refresh.side_effect = refresh_side_effect

                            refresh_task = asyncio.create_task(
                                integration_service.refresh_integration_tokens(
                                    user_id=user_id, provider=provider, force=True
                                )
                            )
                            await asyncio.sleep(0.1)
                            await integration_service.refresh_integration_tokens(
                                user_id=user_id, provider=provider, force=True
                            )
                            refresh_task.cancel()
                            try:
                                await refresh_task
                            except asyncio.CancelledError:
                                pass
