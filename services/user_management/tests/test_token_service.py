"""
Unit tests for Token Service.

Tests the TokenService class functionality including token retrieval,
refresh operations, user status tracking, and error handling.
"""

import asyncio
import os
import tempfile

# Set required environment variables before any imports
os.environ.setdefault("TOKEN_ENCRYPTION_SALT", "dGVzdC1zYWx0LTE2Ynl0ZQ==")

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from services.user_management.database import create_all_tables
from services.user_management.models.integration import Integration, IntegrationProvider, IntegrationStatus
from services.user_management.models.user import User
from services.user_management.services.token_service import TokenService


class TestTokenService:
    """Test suite for TokenService."""

    def setup_method(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        os.environ["DB_URL_USER_MANAGEMENT"] = f"sqlite:///{self.db_path}"
        asyncio.run(create_all_tables())
        self.token_service = TokenService()
        self.mock_user = self._create_mock_user()
        self.mock_integration = self._create_mock_integration()

    def teardown_method(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def _create_mock_user(self):
        """Create a mock user for testing."""
        user = MagicMock(spec=User)
        user.clerk_id = "test_user_123"
        user.id = 1
        return user

    def _create_mock_integration(self):
        """Create a mock integration for testing."""
        integration = MagicMock(spec=Integration)
        integration.id = 1
        integration.user = self.mock_user
        integration.provider = IntegrationProvider.GOOGLE
        integration.status = IntegrationStatus.ACTIVE
        integration.scopes = {"read": True, "write": True}
        integration.created_at = datetime.now(timezone.utc)
        integration.updated_at = datetime.now(timezone.utc)
        return integration

    @pytest.mark.asyncio
    async def test_store_tokens_success(self):
        """Test successful token storage."""
        tokens = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_123",
            "expires_in": 3600,
        }

        with (
            patch.object(
                self.token_service, "_get_user_integration", return_value=self.mock_integration
            ),
            patch.object(self.token_service, "_store_token_record") as mock_store,
            patch(
                "services.user_management.services.token_service.audit_logger.log_user_action"
            ),
        ):

            await self.token_service.store_tokens(
                user_id="test_user_123",
                provider=IntegrationProvider.GOOGLE,
                tokens=tokens,
                scopes=["read", "write"],
            )

            # Should be called twice (access and refresh tokens)
            assert mock_store.call_count == 2

    @pytest.mark.asyncio
    async def test_has_required_scopes_success(self):
        """Test successful scope validation."""
        granted_scopes = ["read", "write", "admin"]
        required_scopes = ["read", "write"]

        result = self.token_service._has_required_scopes(granted_scopes, required_scopes)
        assert result is True

    @pytest.mark.asyncio
    async def test_has_required_scopes_failure(self):
        """Test scope validation failure."""
        granted_scopes = ["read"]
        required_scopes = ["read", "write", "admin"]

        result = self.token_service._has_required_scopes(granted_scopes, required_scopes)
        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_google_token_success(self):
        """Test successful Google token revocation."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            result = await self.token_service._revoke_google_token("test_token")

            assert result["success"] is True
            assert result["provider"] == "google"

    @pytest.mark.asyncio
    async def test_revoke_google_token_failure(self):
        """Test Google token revocation failure."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "Invalid token"
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            result = await self.token_service._revoke_google_token("test_token")

            assert result["success"] is False
            assert "Google revocation failed: 400" in result["error"]

    @pytest.mark.asyncio
    async def test_revoke_microsoft_token_success(self):
        """Test successful Microsoft token revocation."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            result = await self.token_service._revoke_microsoft_token("test_token")

            assert result["success"] is True
            assert result["provider"] == "microsoft"

    @pytest.mark.asyncio
    async def test_revoke_with_provider_unsupported(self):
        """Test token revocation with unsupported provider."""
        # Create a mock provider that's not implemented
        mock_provider = MagicMock()
        mock_provider.value = "unsupported"

        result = await self.token_service._revoke_with_provider(
            mock_provider, "test_token", "access_token"
        )

        assert result["success"] is False
        assert "not implemented" in result["error"]
