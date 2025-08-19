"""
Unit tests for token management functionality.

Tests token storage, retrieval, refresh, validation,
and lifecycle management for OAuth tokens.
"""

# Set required environment variables before any imports
import os

os.environ.setdefault("DB_URL_OFFICE", "sqlite:///:memory:")
os.environ.setdefault("API_OFFICE_USER_KEY", "test-api-key")

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.office.core.token_manager import TokenData, TokenManager


@pytest.fixture(autouse=True)
def patch_settings():
    """Patch the _settings global variable to return test settings."""
    import services.office.core.settings as office_settings

    test_settings = office_settings.Settings(
        db_url_office="sqlite:///:memory:",
        api_frontend_office_key="test-frontend-office-key",
        api_chat_office_key="test-chat-office-key",
        api_meetings_office_key="test-meetings-office-key",
        api_backfill_office_key="test-backfill-office-key",
        api_office_user_key="test-office-user-key",
        pagination_secret_key="test-pagination-secret-key",
    )

    # Directly set the singleton instead of using monkeypatch
    office_settings._settings = test_settings
    yield
    office_settings._settings = None


class TestTokenManager:
    """Tests for TokenManager class."""

    @pytest.fixture
    def mock_token_data_dict(self):
        """Mock TokenData response from User Management Service."""
        # Use a future expiration date to ensure tokens are not immediately expired
        future_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        return {
            "success": True,
            "access_token": "test_access_token_123",
            "refresh_token": "test_refresh_token",
            "expires_at": future_expiry.isoformat(),
            "scopes": ["read", "write"],
            "provider": "google",
            "user_id": "test_user",
        }

    @pytest.mark.asyncio
    async def test_get_user_token_success(self, mock_token_data_dict):
        """Test successful token retrieval."""
        async with TokenManager() as token_manager:
            with patch.object(
                token_manager.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_token_data_dict
                mock_post.return_value = mock_response

                result = await token_manager.get_user_token(
                    "test_user", "google", ["read", "write"]
                )

                assert result is not None
                assert isinstance(result, TokenData)
                assert result.access_token == "test_access_token_123"
                assert result.provider == "google"
                assert result.user_id == "test_user"

    @pytest.mark.asyncio
    async def test_get_user_token_cache_hit(self, mock_token_data_dict):
        """Test token retrieval with cache hit."""
        async with TokenManager() as token_manager:
            with patch.object(
                token_manager.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_token_data_dict
                mock_post.return_value = mock_response

                # First request - cache miss
                result1 = await token_manager.get_user_token(
                    "test_user", "google", ["read", "write"]
                )
                assert result1 is not None
                assert mock_post.call_count == 1

                # Second request - cache hit (should not make HTTP call)
                result2 = await token_manager.get_user_token(
                    "test_user", "google", ["read", "write"]
                )
                assert result2 is not None
                assert mock_post.call_count == 1  # Still 1, no additional call
                assert result2.access_token == result1.access_token

    @pytest.mark.asyncio
    async def test_get_user_token_different_users_different_cache(
        self, mock_token_data_dict
    ):
        """Test token retrieval for different users creates separate cache entries."""
        async with TokenManager() as token_manager:
            with patch.object(
                token_manager.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_token_data_dict
                mock_post.return_value = mock_response

                # Request for user1
                result1 = await token_manager.get_user_token(
                    "user1", "google", ["read"]
                )
                assert result1 is not None

                # Request for user2 (different user, should make new HTTP call)
                result2 = await token_manager.get_user_token(
                    "user2", "google", ["read"]
                )
                assert result2 is not None

                assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_get_user_token_different_scopes_different_cache(
        self, mock_token_data_dict
    ):
        """Test token retrieval for different scopes creates separate cache entries."""
        async with TokenManager() as token_manager:
            with patch.object(
                token_manager.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_token_data_dict
                mock_post.return_value = mock_response

                # Request for read scopes
                result1 = await token_manager.get_user_token(
                    "test_user", "google", ["read"]
                )
                assert result1 is not None

                # Request for write scopes (different scopes, should make new HTTP call)
                result2 = await token_manager.get_user_token(
                    "test_user", "google", ["write"]
                )
                assert result2 is not None

                assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_get_user_token_404_not_found(self):
        """Test token retrieval when user/provider not found."""
        async with TokenManager() as token_manager:
            with patch.object(
                token_manager.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 404
                mock_response.text = "Token not found"
                mock_post.return_value = mock_response

                result = await token_manager.get_user_token(
                    "nonexistent_user", "google", ["read"]
                )

                assert result is None

    @pytest.mark.asyncio
    async def test_get_user_token_403_forbidden(self):
        """Test token retrieval with insufficient permissions."""
        async with TokenManager() as token_manager:
            with patch.object(
                token_manager.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 403
                mock_response.text = "Insufficient permissions"
                mock_post.return_value = mock_response

                result = await token_manager.get_user_token(
                    "test_user", "google", ["admin"]
                )

                assert result is None

    @pytest.mark.asyncio
    async def test_get_user_token_500_server_error(self):
        """Test token retrieval with server error."""
        async with TokenManager() as token_manager:
            with patch.object(
                token_manager.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 500
                mock_response.text = "Internal Server Error"
                mock_post.return_value = mock_response

                result = await token_manager.get_user_token(
                    "test_user", "google", ["read"]
                )

                assert result is None

    @pytest.mark.asyncio
    async def test_get_user_token_network_error(self):
        """Test token retrieval with network connectivity issues."""
        async with TokenManager() as token_manager:
            with patch.object(
                token_manager.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.side_effect = httpx.NetworkError("Connection failed")

                result = await token_manager.get_user_token(
                    "test_user", "google", ["read"]
                )

                assert result is None

    @pytest.mark.asyncio
    async def test_get_user_token_timeout_error(self):
        """Test token retrieval with timeout."""
        async with TokenManager() as token_manager:
            with patch.object(
                token_manager.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_post.side_effect = httpx.TimeoutException("Request timeout")

                result = await token_manager.get_user_token(
                    "test_user", "google", ["read"]
                )

                assert result is None

    @pytest.mark.asyncio
    async def test_token_manager_without_context_manager(self):
        """Test TokenManager usage without async context manager."""
        token_manager = TokenManager()

        result = await token_manager.get_user_token("test_user", "google", ["read"])

        # Should return None because http_client is not initialized
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_key_generation_consistent(self):
        """Test that cache key generation is consistent for same parameters."""
        token_manager = TokenManager()

        key1 = token_manager._generate_cache_key("user1", "google", ["read", "write"])
        key2 = token_manager._generate_cache_key("user1", "google", ["write", "read"])

        # Should be the same despite different order of scopes
        assert key1 == key2

    @pytest.mark.asyncio
    async def test_cache_key_generation_different_users(self):
        """Test that cache key generation differs for different users."""
        token_manager = TokenManager()

        key1 = token_manager._generate_cache_key("user1", "google", ["read"])
        key2 = token_manager._generate_cache_key("user2", "google", ["read"])

        assert key1 != key2

    @pytest.mark.asyncio
    async def test_cache_cleanup_expired_tokens(self, mock_token_data_dict):
        """Test cleanup of expired tokens."""
        async with TokenManager() as token_manager:
            with patch.object(
                token_manager.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_token_data_dict
                mock_post.return_value = mock_response

                # Get a token (adds to cache)
                await token_manager.get_user_token("test_user", "google", ["read"])

                # Verify cache has the entry
                assert len(token_manager._token_cache) == 1

                # Manually expire the token
                cache_key = list(token_manager._token_cache.keys())[0]
                token_manager._token_cache[cache_key].cache_expires_at = datetime.now(
                    timezone.utc
                )

                # Trigger cleanup by requesting another token
                await token_manager.get_user_token("test_user", "microsoft", ["read"])

                # Should have removed the expired token and added the new one
                assert len(token_manager._token_cache) == 1

    @pytest.mark.asyncio
    async def test_invalidate_cache_specific_provider(self, mock_token_data_dict):
        """Test cache invalidation for specific provider."""
        async with TokenManager() as token_manager:
            with patch.object(
                token_manager.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_token_data_dict
                mock_post.return_value = mock_response

                # Add tokens for different providers
                await token_manager.get_user_token("test_user", "google", ["read"])
                await token_manager.get_user_token("test_user", "microsoft", ["read"])

                assert len(token_manager._token_cache) == 2

                # Invalidate only Google tokens
                await token_manager.invalidate_cache("test_user", "google")

                # Should have only Microsoft token left
                assert len(token_manager._token_cache) == 1
                remaining_key = list(token_manager._token_cache.keys())[0]
                assert "microsoft" in remaining_key

    @pytest.mark.asyncio
    async def test_invalidate_cache_all_providers(self, mock_token_data_dict):
        """Test cache invalidation for all providers."""
        async with TokenManager() as token_manager:
            with patch.object(
                token_manager.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_token_data_dict
                mock_post.return_value = mock_response

                # Add tokens for different providers
                await token_manager.get_user_token("test_user", "google", ["read"])
                await token_manager.get_user_token("test_user", "microsoft", ["read"])

                assert len(token_manager._token_cache) == 2

                # Invalidate all tokens for user
                await token_manager.invalidate_cache("test_user")

                # Should have no tokens left
                assert len(token_manager._token_cache) == 0

    @pytest.mark.asyncio
    async def test_token_expiration_with_actual_token_expiry(
        self, mock_token_data_dict
    ):
        """Test that tokens are considered expired when the actual token expires."""
        async with TokenManager() as token_manager:
            with patch.object(
                token_manager.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_token_data_dict
                mock_post.return_value = mock_response

                # Get a token (adds to cache)
                result1 = await token_manager.get_user_token(
                    "test_user", "google", ["read"]
                )
                assert result1 is not None
                assert mock_post.call_count == 1

                # Verify cache hit on second request
                result2 = await token_manager.get_user_token(
                    "test_user", "google", ["read"]
                )
                assert result2 is not None
                assert mock_post.call_count == 1  # Should still be 1 due to cache hit

                # Manually set the token to expire in the past (but keep cache TTL valid)
                cache_key = list(token_manager._token_cache.keys())[0]
                cached_token = token_manager._token_cache[cache_key]
                # Set token to expire 10 minutes ago
                cached_token.token_data.expires_at = datetime.now(
                    timezone.utc
                ) - timedelta(minutes=10)

                # Request the same token again - should be a cache miss due to token expiration
                result3 = await token_manager.get_user_token(
                    "test_user", "google", ["read"]
                )
                assert result3 is not None
                assert mock_post.call_count == 2  # Should be 2 now due to cache miss

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, mock_token_data_dict):
        """Test cache statistics reporting."""
        async with TokenManager() as token_manager:
            with patch.object(
                token_manager.http_client, "post", new_callable=AsyncMock
            ) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_token_data_dict
                mock_post.return_value = mock_response

                # Initially empty cache
                stats = token_manager.get_cache_stats()
                assert stats["total_cached_tokens"] == 0

                # Add some tokens
                await token_manager.get_user_token("user1", "google", ["read"])
                await token_manager.get_user_token("user2", "microsoft", ["write"])

                stats = token_manager.get_cache_stats()
                assert stats["total_cached_tokens"] == 2
                assert stats["active_tokens"] == 2
                assert stats["expired_tokens"] == 0


class TestTokenData:
    """Tests for TokenData model."""

    def test_token_data_creation(self):
        """Test TokenData model creation."""
        token_data = TokenData(
            access_token="test_token",
            provider="google",
            user_id="test_user",
            scopes=["read", "write"],
        )

        assert token_data.access_token == "test_token"
        assert token_data.provider == "google"
        assert token_data.user_id == "test_user"
        assert token_data.scopes == ["read", "write"]
        assert token_data.refresh_token is None
        assert token_data.expires_at is None

    def test_token_data_with_all_fields(self):
        """Test TokenData model with all fields."""
        expires_at = datetime.now(timezone.utc)

        token_data = TokenData(
            access_token="test_token",
            refresh_token="refresh_token",
            expires_at=expires_at,
            scopes=["read", "write"],
            provider="microsoft",
            user_id="test_user",
        )

        assert token_data.access_token == "test_token"
        assert token_data.refresh_token == "refresh_token"
        assert token_data.expires_at == expires_at
        assert token_data.scopes == ["read", "write"]
        assert token_data.provider == "microsoft"
        assert token_data.user_id == "test_user"
