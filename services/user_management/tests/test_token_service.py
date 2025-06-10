"""
Unit tests for Token Service.

Tests the TokenService class functionality including token retrieval,
refresh operations, user status tracking, and error handling.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from ..models.integration import Integration, IntegrationProvider, IntegrationStatus
from ..models.user import User
from ..services.token_service import TokenService


class TestTokenService:
    """Test suite for TokenService."""

    @pytest.fixture
    def token_service(self):
        """Create a TokenService instance for testing."""
        return TokenService()

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = MagicMock(spec=User)
        user.clerk_id = "test_user_123"
        user.id = 1
        return user

    @pytest.fixture
    def mock_integration(self, mock_user):
        """Create a mock integration for testing."""
        integration = MagicMock(spec=Integration)
        integration.id = 1
        integration.user = mock_user
        integration.provider = IntegrationProvider.GOOGLE
        integration.status = IntegrationStatus.ACTIVE
        integration.scopes = {"read": True, "write": True}
        integration.created_at = datetime.now(timezone.utc)
        integration.updated_at = datetime.now(timezone.utc)
        return integration

    @pytest.mark.asyncio
    async def test_store_tokens_success(self, token_service, mock_integration):
        """Test successful token storage."""
        tokens = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_123",
            "expires_in": 3600,
        }

        with (
            patch.object(
                token_service, "_get_user_integration", return_value=mock_integration
            ),
            patch.object(token_service, "_store_token_record") as mock_store,
            patch(
                "services.user_management.services.token_service.audit_logger.log_user_action"
            ),
        ):

            await token_service.store_tokens(
                user_id="test_user_123",
                provider=IntegrationProvider.GOOGLE,
                tokens=tokens,
                scopes=["read", "write"],
            )

            # Should be called twice (access and refresh tokens)
            assert mock_store.call_count == 2

    @pytest.mark.asyncio
    async def test_has_required_scopes_success(self, token_service):
        """Test successful scope validation."""
        granted_scopes = ["read", "write", "admin"]
        required_scopes = ["read", "write"]

        result = token_service._has_required_scopes(granted_scopes, required_scopes)
        assert result is True

    @pytest.mark.asyncio
    async def test_has_required_scopes_failure(self, token_service):
        """Test scope validation failure."""
        granted_scopes = ["read"]
        required_scopes = ["read", "write", "admin"]

        result = token_service._has_required_scopes(granted_scopes, required_scopes)
        assert result is False
