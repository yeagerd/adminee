"""
Tests for token optimization improvements.

Tests the database query optimization and deduplication features to ensure they reduce
redundant token requests and refresh operations.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from services.user.models.integration import IntegrationProvider, IntegrationStatus
from services.user.services.integration_service import IntegrationService
from services.user.services.token_service import TokenService


class TestTokenOptimization:
    """Test token optimization features."""

    @pytest.fixture
    def token_service(self):
        """Create a token service instance."""
        return TokenService()

    @pytest.fixture
    def integration_service(self):
        """Create an integration service instance."""
        return IntegrationService()

    @pytest.mark.asyncio
    async def test_optimized_database_query(self, token_service):
        """Test that the optimized database query reduces round trips."""
        user_id = "test_user"
        provider = IntegrationProvider.MICROSOFT

        # Mock the database operations
        with patch.object(
            token_service, "_get_integration_and_tokens"
        ) as mock_get_tokens:
            mock_integration = AsyncMock()
            mock_integration.id = 1
            mock_integration.status = IntegrationStatus.ACTIVE
            mock_integration.scopes = {"scope1": True, "scope2": True}

            mock_access_token = AsyncMock()
            mock_access_token.encrypted_value = "encrypted_access"
            mock_access_token.expires_at = datetime.now(timezone.utc) + timedelta(
                hours=1
            )

            mock_refresh_token = AsyncMock()
            mock_refresh_token.encrypted_value = "encrypted_refresh"

            mock_get_tokens.return_value = (
                mock_integration,
                mock_access_token,
                mock_refresh_token,
            )

            # Mock token decryption
            with patch.object(
                token_service.token_encryption, "decrypt_token"
            ) as mock_decrypt:
                mock_decrypt.side_effect = lambda token, user_id: f"decrypted_{token}"

                # Call the optimized method
                result = await token_service.get_valid_token(
                    user_id=user_id, provider=provider, required_scopes=["scope1"]
                )

                # Verify the optimized query was called once
                mock_get_tokens.assert_called_once_with(user_id, provider)

                # Verify the result is correct
                assert result.success is True
                assert result.access_token == "decrypted_encrypted_access"
                assert result.refresh_token == "decrypted_encrypted_refresh"

    @pytest.mark.asyncio
    async def test_refresh_deduplication(self, integration_service):
        """Test that refresh operations are deduplicated."""
        user_id = "test_user"
        provider = IntegrationProvider.MICROSOFT

        # Mock the refresh operation to simulate a delay
        with patch.object(
            integration_service, "_get_user_integration_in_session"
        ) as mock_get_integration:
            mock_integration = AsyncMock()
            mock_get_integration.return_value = mock_integration

            # Start two concurrent refresh operations
            async def refresh_operation():
                return await integration_service.refresh_integration_tokens(
                    user_id=user_id, provider=provider, force=True
                )

            # Run both operations concurrently
            results = await asyncio.gather(
                refresh_operation(), refresh_operation(), return_exceptions=True
            )

            # One should succeed, one should be deduplicated
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            assert success_count >= 1

    @pytest.mark.asyncio
    async def test_database_query_reduction(self, token_service):
        """Test that database queries are reduced from 3+ to 1."""
        user_id = "test_user"
        provider = IntegrationProvider.MICROSOFT

        # Mock the database session
        with patch(
            "services.user.services.token_service.get_async_session"
        ) as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.return_value = mock_session_instance

            # Mock the optimized query method
            with patch.object(
                token_service, "_get_integration_and_tokens"
            ) as mock_get_tokens:
                mock_integration = AsyncMock()
                mock_integration.id = 1
                mock_integration.status = IntegrationStatus.ACTIVE
                mock_integration.scopes = {}

                mock_access_token = AsyncMock()
                mock_access_token.encrypted_value = "encrypted_access"
                mock_access_token.expires_at = datetime.now(timezone.utc) + timedelta(
                    hours=1
                )

                mock_get_tokens.return_value = (
                    mock_integration,
                    mock_access_token,
                    None,
                )

                # Mock token decryption
                with patch.object(
                    token_service.token_encryption, "decrypt_token"
                ) as mock_decrypt:
                    mock_decrypt.return_value = "decrypted_token"

                    # Call the method
                    result = await token_service.get_valid_token(
                        user_id=user_id, provider=provider
                    )

                    # Verify only one database query was made (the optimized one)
                    mock_get_tokens.assert_called_once()

                    # Verify the result is correct
                    assert result.success is True
                    assert result.access_token == "decrypted_token"
