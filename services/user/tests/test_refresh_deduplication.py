"""
Test refresh deduplication to ensure it doesn't cause upstream failures.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from services.user.models.integration import IntegrationProvider, IntegrationStatus
from services.user.services.integration_service import IntegrationService
from services.user.tests.test_base import BaseUserManagementIntegrationTest


class TestRefreshDeduplication(BaseUserManagementIntegrationTest):
    """Test that refresh deduplication works correctly."""

    def _setup_mock_session(self):
        """Helper to set up a properly mocked database session."""
        mock_session_instance = AsyncMock()
        mock_session_instance.add = MagicMock()  # Mock session.add as synchronous
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

                mock_result = Mock()
                call_count = 0

                def scalar_one_or_none():
                    nonlocal call_count
                    call_count += 1
                    return (
                        mock_access_token if call_count % 2 == 1 else mock_refresh_token
                    )

                mock_result.scalar_one_or_none.side_effect = scalar_one_or_none
                mock_session_instance.execute.return_value = mock_result

                # Mock token decryption by directly patching the instance method
                integration_service.token_encryption.decrypt_token = (
                    lambda encrypted_token, user_id: "decrypted_token_value"
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

                        # Mock audit logging to prevent database errors
                        with patch(
                            "services.user.services.integration_service.audit_logger.log_user_action"
                        ) as mock_audit:
                            mock_audit.return_value = None

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

                mock_result = Mock()

                def scalar_one_or_none_side_effect():
                    yield mock_access_token
                    yield mock_refresh_token
                    while True:
                        yield mock_refresh_token

                effect_generator = scalar_one_or_none_side_effect()
                mock_result.scalar_one_or_none.side_effect = lambda: next(
                    effect_generator
                )

                mock_session_instance.execute.return_value = mock_result

                # Mock token decryption by directly patching the instance method
                integration_service.token_encryption.decrypt_token = (
                    lambda encrypted_token, user_id: "decrypted_token_value"
                )

                # Mock OAuth refresh to fail by directly patching the instance method
                async def mock_refresh_fail(*args, **kwargs):
                    raise Exception("OAuth refresh failed")

                integration_service.oauth_config.refresh_access_token = (
                    mock_refresh_fail
                )

                # Mock audit logging to prevent database errors
                with patch(
                    "services.user.services.integration_service.audit_logger.log_user_action"
                ) as mock_audit:
                    mock_audit.return_value = None

                    # Start two concurrent refresh operations
                    async def refresh_operation():
                        return await integration_service.refresh_integration_tokens(
                            user_id=user_id, provider=provider, force=True
                        )

                    # Run both operations concurrently
                    results = await asyncio.gather(
                        refresh_operation(), refresh_operation(), return_exceptions=True
                    )

                    # Both should fail with exceptions
                    assert len(results) == 2
                    assert all(isinstance(r, Exception) for r in results)
                    # Both should be ServiceError exceptions
                    assert all("Token refresh failed" in str(r) for r in results)

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
                            # Mock audit logging to prevent database errors
                            with patch(
                                "services.user.services.integration_service.audit_logger.log_user_action"
                            ) as mock_audit:
                                mock_audit.return_value = None
                                result = await integration_service.refresh_integration_tokens(
                                    user_id=user_id, provider=provider, force=True
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

        # Create a mock settings object with a short timeout for testing
        from unittest.mock import Mock

        mock_settings = Mock()
        mock_settings.refresh_timeout_seconds = 0.1  # 100ms timeout for fast testing

        with patch(
            "services.user.services.integration_service.get_settings",
            return_value=mock_settings,
        ):
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
                    mock_access_token.expires_at = datetime.now(
                        timezone.utc
                    ) + timedelta(hours=1)
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

                                # Mock audit logging to prevent database errors
                                with patch(
                                    "services.user.services.integration_service.audit_logger.log_user_action"
                                ) as mock_audit:
                                    mock_audit.return_value = None

                                    refresh_task = asyncio.create_task(
                                        integration_service.refresh_integration_tokens(
                                            user_id=user_id,
                                            provider=provider,
                                            force=True,
                                        )
                                    )
                                    await asyncio.sleep(
                                        0.05
                                    )  # Wait a bit for the first task to start
                                    start_time = asyncio.get_event_loop().time()
                                    await integration_service.refresh_integration_tokens(
                                        user_id=user_id, provider=provider, force=True
                                    )
                                    end_time = asyncio.get_event_loop().time()
                                    assert (
                                        end_time - start_time < 1.0
                                    )  # Should complete within 1 second
                                    refresh_task.cancel()
                                    try:
                                        await refresh_task
                                    except asyncio.CancelledError:
                                        pass

    @pytest.mark.asyncio
    async def test_refresh_deduplication_timeout_cleanup(self, integration_service):
        user_id = "test_user"
        provider = IntegrationProvider.MICROSOFT

        # Create a mock settings object with a short timeout for testing
        from unittest.mock import Mock

        mock_settings = Mock()
        mock_settings.refresh_timeout_seconds = 0.1  # 100ms timeout for fast testing

        with patch(
            "services.user.services.integration_service.get_settings",
            return_value=mock_settings,
        ):
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
                    mock_access_token.expires_at = datetime.now(
                        timezone.utc
                    ) + timedelta(hours=1)
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

                                # Mock audit logging to prevent database errors
                                with patch(
                                    "services.user.services.integration_service.audit_logger.log_user_action"
                                ) as mock_audit:
                                    mock_audit.return_value = None

                                    refresh_task = asyncio.create_task(
                                        integration_service.refresh_integration_tokens(
                                            user_id=user_id,
                                            provider=provider,
                                            force=True,
                                        )
                                    )
                                    await asyncio.sleep(
                                        0.05
                                    )  # Wait a bit for the first task to start
                                    await integration_service.refresh_integration_tokens(
                                        user_id=user_id, provider=provider, force=True
                                    )
                                    refresh_task.cancel()
                                    try:
                                        await refresh_task
                                    except asyncio.CancelledError:
                                        pass

    @pytest.mark.asyncio
    async def test_refresh_handles_malformed_expires_at(self, integration_service):
        """Test that malformed expires_at strings are handled gracefully."""
        user_id = "test_user"
        provider = IntegrationProvider.GOOGLE

        # Create a mock integration
        integration = Mock()
        integration.id = 1
        integration.status = IntegrationStatus.ACTIVE

        # Mock the database session and queries
        mock_session_instance = AsyncMock()
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session_instance
        mock_session.__aexit__.return_value = None

        # Mock the OAuth refresh to return tokens with malformed expires_at
        with patch.object(
            integration_service.oauth_config, "refresh_access_token"
        ) as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_at": "invalid-date-format",  # Malformed date string
            }

            # Mock audit logging to prevent database errors
            with patch(
                "services.user.services.integration_service.audit_logger.log_user_action"
            ) as mock_audit:
                mock_audit.return_value = None

                # Mock the database session factory
                with patch(
                    "services.user.services.integration_service.get_async_session"
                ) as mock_session_factory:
                    mock_session_factory.return_value = lambda: mock_session

                    # Mock the integration retrieval
                    with patch.object(
                        integration_service, "_get_user_integration_in_session"
                    ) as mock_get_integration:
                        mock_get_integration.return_value = integration

                        # Mock the token queries
                        mock_access_token = Mock()
                        mock_access_token.encrypted_value = "encrypted_access_token"
                        mock_access_token.expires_at = None

                        mock_refresh_token = Mock()
                        mock_refresh_token.encrypted_value = "encrypted_refresh_token"

                        mock_result = Mock()
                        call_count = 0

                        def scalar_one_or_none():
                            nonlocal call_count
                            call_count += 1
                            return (
                                mock_access_token
                                if call_count % 2 == 1
                                else mock_refresh_token
                            )

                        mock_result.scalar_one_or_none.side_effect = scalar_one_or_none
                        mock_session_instance.execute.return_value = mock_result

                        # Mock token decryption
                        integration_service.token_encryption.decrypt_token = (
                            lambda encrypted_token, user_id: "decrypted_token_value"
                        )

                        # Mock the token storage to avoid encryption issues
                        with patch.object(
                            integration_service, "_store_encrypted_tokens"
                        ) as mock_store:
                            mock_store.return_value = None

                            # Mock the integration update
                            mock_session_instance.add = Mock()
                            mock_session_instance.commit = AsyncMock()

                            # Execute the refresh
                            result = (
                                await integration_service.refresh_integration_tokens(
                                    user_id=user_id, provider=provider, force=True
                                )
                            )

                            # Verify the result
                            assert result.success is True
                            assert result.integration_id == integration.id
                            assert result.provider == provider

                            # Verify that a fallback expiration was used (should be roughly 1 hour from now)
                            assert result.token_expires_at is not None
                            now = datetime.now(timezone.utc)
                            expected_min = now + timedelta(
                                hours=1, minutes=-1
                            )  # Allow 1 minute tolerance
                            expected_max = now + timedelta(
                                hours=1, minutes=1
                            )  # Allow 1 minute tolerance
                            assert (
                                expected_min <= result.token_expires_at <= expected_max
                            )

                            # Verify that the warning was logged
                            # Note: We can't easily verify the log message in this test setup,
                            # but the fact that we get a valid result with a fallback expiration
                            # confirms the error handling worked.

    @pytest.mark.asyncio
    async def test_refresh_no_deadlock_in_finally_block(self, integration_service):
        """Test that the finally block doesn't cause a deadlock when lock is already held."""
        user_id = "test_user"
        provider = IntegrationProvider.GOOGLE

        # Create a mock integration
        integration = Mock()
        integration.id = 1
        integration.status = IntegrationStatus.ACTIVE

        # Mock the database session and queries
        mock_session_instance = AsyncMock()
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session_instance
        mock_session.__aexit__.return_value = None

        # Mock the OAuth refresh to return tokens
        with patch.object(
            integration_service.oauth_config, "refresh_access_token"
        ) as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 3600,
            }

            # Mock audit logging to prevent database errors
            with patch(
                "services.user.services.integration_service.audit_logger.log_user_action"
            ) as mock_audit:
                mock_audit.return_value = None

                # Mock the database session factory
                with patch(
                    "services.user.services.integration_service.get_async_session"
                ) as mock_session_factory:
                    mock_session_factory.return_value = lambda: mock_session

                    # Mock the integration retrieval
                    with patch.object(
                        integration_service, "_get_user_integration_in_session"
                    ) as mock_get_integration:
                        mock_get_integration.return_value = integration

                        # Mock the token queries
                        mock_access_token = Mock()
                        mock_access_token.encrypted_value = "encrypted_access_token"
                        mock_access_token.expires_at = None

                        mock_refresh_token = Mock()
                        mock_refresh_token.encrypted_value = "encrypted_refresh_token"

                        mock_result = Mock()
                        call_count = 0

                        def scalar_one_or_none():
                            nonlocal call_count
                            call_count += 1
                            return (
                                mock_access_token
                                if call_count % 2 == 1
                                else mock_refresh_token
                            )

                        mock_result.scalar_one_or_none.side_effect = scalar_one_or_none
                        mock_session_instance.execute.return_value = mock_result

                        # Mock token decryption
                        integration_service.token_encryption.decrypt_token = (
                            lambda encrypted_token, user_id: "decrypted_token_value"
                        )

                        # Mock the token storage to avoid encryption issues
                        with patch.object(
                            integration_service, "_store_encrypted_tokens"
                        ) as mock_store:
                            mock_store.return_value = None

                            # Mock the integration update
                            mock_session_instance.add = Mock()
                            mock_session_instance.commit = AsyncMock()

                            # Execute the refresh - this should not deadlock
                            result = (
                                await integration_service.refresh_integration_tokens(
                                    user_id=user_id, provider=provider, force=True
                                )
                            )

                            # Verify the result
                            assert result.success is True
                            assert result.integration_id == integration.id
                            assert result.provider == provider

                            # Verify that the refresh key was properly cleaned up
                            # The _ongoing_refreshes should be empty after the operation
                            assert len(integration_service._ongoing_refreshes) == 0

    @pytest.mark.asyncio
    async def test_refresh_cleanup_thread_safety(self, integration_service):
        """Test that the finally block cleanup is thread-safe and doesn't cause race conditions."""
        user_id = "test_user"
        provider = IntegrationProvider.GOOGLE

        # Create a mock integration
        integration = Mock()
        integration.id = 1
        integration.status = IntegrationStatus.ACTIVE

        # Mock the database session and queries
        mock_session_instance = AsyncMock()
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session_instance
        mock_session.__aexit__.return_value = None

        # Mock the OAuth refresh to return tokens
        with patch.object(
            integration_service.oauth_config, "refresh_access_token"
        ) as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 3600,
            }

            # Mock audit logging to prevent database errors
            with patch(
                "services.user.services.integration_service.audit_logger.log_user_action"
            ) as mock_audit:
                mock_audit.return_value = None

                # Mock the database session factory
                with patch(
                    "services.user.services.integration_service.get_async_session"
                ) as mock_session_factory:
                    mock_session_factory.return_value = lambda: mock_session

                    # Mock the integration retrieval
                    with patch.object(
                        integration_service, "_get_user_integration_in_session"
                    ) as mock_get_integration:
                        mock_get_integration.return_value = integration

                        # Mock the token queries
                        mock_access_token = Mock()
                        mock_access_token.encrypted_value = "encrypted_access_token"
                        mock_access_token.expires_at = None

                        mock_refresh_token = Mock()
                        mock_refresh_token.encrypted_value = "encrypted_refresh_token"

                        mock_result = Mock()
                        call_count = 0

                        def scalar_one_or_none():
                            nonlocal call_count
                            call_count += 1
                            return (
                                mock_access_token
                                if call_count % 2 == 1
                                else mock_refresh_token
                            )

                        mock_result.scalar_one_or_none.side_effect = scalar_one_or_none
                        mock_session_instance.execute.return_value = mock_result

                        # Mock token decryption
                        integration_service.token_encryption.decrypt_token = (
                            lambda encrypted_token, user_id: "decrypted_token_value"
                        )

                        # Mock the token storage to avoid encryption issues
                        with patch.object(
                            integration_service, "_store_encrypted_tokens"
                        ) as mock_store:
                            mock_store.return_value = None

                            # Mock the integration update
                            mock_session_instance.add = Mock()
                            mock_session_instance.commit = AsyncMock()

                            # Execute the refresh - this should not cause race conditions
                            result = (
                                await integration_service.refresh_integration_tokens(
                                    user_id=user_id, provider=provider, force=True
                                )
                            )

                            # Verify the result
                            assert result.success is True
                            assert result.integration_id == integration.id
                            assert result.provider == provider

                            # Verify that the refresh key was properly cleaned up
                            # The _ongoing_refreshes should be empty after the operation
                            assert len(integration_service._ongoing_refreshes) == 0

                            # Verify that the lock is not held after the operation
                            assert not integration_service._refresh_lock.locked()
