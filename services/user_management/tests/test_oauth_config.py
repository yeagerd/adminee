"""
Unit tests for OAuth configuration module.

Tests OAuth provider configurations, state management, PKCE challenges,
authorization URL generation, token exchange, and user info retrieval.
"""

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from ..exceptions import ValidationException
from ..integrations.oauth_config import (
    OAuthConfig,
    OAuthProviderConfig,
    OAuthScope,
    OAuthState,
    PKCEChallenge,
    PKCEChallengeMethod,
    get_oauth_config,
    reset_oauth_config,
)
from ..models.integration import IntegrationProvider
from ..settings import Settings


class TestPKCEChallenge:
    """Test PKCE challenge generation and validation."""

    def test_generate_s256_challenge(self):
        """Test S256 PKCE challenge generation."""
        challenge = PKCEChallenge.generate(PKCEChallengeMethod.S256)

        assert challenge.code_challenge_method == PKCEChallengeMethod.S256
        assert len(challenge.code_verifier) >= 43
        assert len(challenge.code_verifier) <= 128
        assert challenge.code_challenge != challenge.code_verifier

        # Verify challenge is correctly derived from verifier
        expected_challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(challenge.code_verifier.encode("utf-8")).digest()
            )
            .decode("utf-8")
            .rstrip("=")
        )
        assert challenge.code_challenge == expected_challenge

    def test_generate_plain_challenge(self):
        """Test PLAIN PKCE challenge generation."""
        challenge = PKCEChallenge.generate(PKCEChallengeMethod.PLAIN)

        assert challenge.code_challenge_method == PKCEChallengeMethod.PLAIN
        assert challenge.code_challenge == challenge.code_verifier

    def test_challenge_randomness(self):
        """Test that generated challenges are unique."""
        challenge1 = PKCEChallenge.generate()
        challenge2 = PKCEChallenge.generate()

        assert challenge1.code_verifier != challenge2.code_verifier
        assert challenge1.code_challenge != challenge2.code_challenge


class TestOAuthScope:
    """Test OAuth scope configuration."""

    def test_scope_creation(self):
        """Test OAuth scope creation."""
        scope = OAuthScope(
            name="email",
            description="Access to user's email",
            required=True,
            sensitive=True,
        )

        assert scope.name == "email"
        assert scope.description == "Access to user's email"
        assert scope.required is True
        assert scope.sensitive is True

    def test_scope_defaults(self):
        """Test OAuth scope default values."""
        scope = OAuthScope(name="profile", description="Basic profile")

        assert scope.required is False
        assert scope.sensitive is False


class TestOAuthState:
    """Test OAuth state management."""

    def test_state_creation(self):
        """Test OAuth state creation."""
        state = OAuthState(
            state="test-state",
            user_id="user123",
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
            scopes=["email", "profile"],
            pkce_verifier="test-verifier",
        )

        assert state.state == "test-state"
        assert state.user_id == "user123"
        assert state.provider == IntegrationProvider.GOOGLE
        assert state.redirect_uri == "https://example.com/callback"
        assert state.scopes == ["email", "profile"]
        assert state.pkce_verifier == "test-verifier"
        assert isinstance(state.created_at, datetime)
        assert isinstance(state.expires_at, datetime)

    def test_state_expiration(self):
        """Test OAuth state expiration logic."""
        # Create expired state
        expired_state = OAuthState(
            state="expired-state",
            user_id="user123",
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=15),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )

        assert expired_state.is_expired() is True

        # Create valid state
        valid_state = OAuthState(
            state="valid-state",
            user_id="user123",
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
        )

        assert valid_state.is_expired() is False

    def test_state_validation_for_callback(self):
        """Test OAuth state validation for callback."""
        state = OAuthState(
            state="test-state",
            user_id="user123",
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
        )

        # Valid callback
        assert (
            state.is_valid_for_callback(
                "test-state", "user123", IntegrationProvider.GOOGLE
            )
            is True
        )

        # Invalid state
        assert (
            state.is_valid_for_callback(
                "wrong-state", "user123", IntegrationProvider.GOOGLE
            )
            is False
        )

        # Invalid user
        assert (
            state.is_valid_for_callback(
                "test-state", "wrong-user", IntegrationProvider.GOOGLE
            )
            is False
        )

        # Invalid provider
        assert (
            state.is_valid_for_callback(
                "test-state", "user123", IntegrationProvider.MICROSOFT
            )
            is False
        )


class TestOAuthProviderConfig:
    """Test OAuth provider configuration."""

    def test_provider_config_creation(self):
        """Test OAuth provider configuration creation."""
        scopes = [
            OAuthScope(name="email", description="Email access", required=True),
            OAuthScope(name="profile", description="Profile access"),
        ]

        config = OAuthProviderConfig(
            name="Google",
            provider=IntegrationProvider.GOOGLE,
            client_id="test-client-id",
            client_secret="test-client-secret",
            authorization_url="https://accounts.google.com/oauth2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://www.googleapis.com/oauth2/userinfo",
            scopes=scopes,
            default_scopes=["email", "profile"],
        )

        assert config.name == "Google"
        assert config.provider == IntegrationProvider.GOOGLE
        assert config.client_id == "test-client-id"
        assert len(config.scopes) == 2
        assert config.default_scopes == ["email", "profile"]

    def test_scope_validation(self):
        """Test scope validation."""
        scopes = [
            OAuthScope(name="email", description="Email access"),
            OAuthScope(name="profile", description="Profile access"),
        ]

        config = OAuthProviderConfig(
            name="Test",
            provider=IntegrationProvider.GOOGLE,
            authorization_url="https://example.com/auth",
            token_url="https://example.com/token",
            userinfo_url="https://example.com/userinfo",
            scopes=scopes,
        )

        # Valid scopes
        valid, invalid = config.validate_scopes(["email", "profile"])
        assert valid == ["email", "profile"]
        assert invalid == []

        # Mix of valid and invalid scopes
        valid, invalid = config.validate_scopes(["email", "invalid", "profile"])
        assert valid == ["email", "profile"]
        assert invalid == ["invalid"]

    def test_get_scope_by_name(self):
        """Test getting scope by name."""
        scopes = [
            OAuthScope(name="email", description="Email access", required=True),
            OAuthScope(name="profile", description="Profile access"),
        ]

        config = OAuthProviderConfig(
            name="Test",
            provider=IntegrationProvider.GOOGLE,
            authorization_url="https://example.com/auth",
            token_url="https://example.com/token",
            userinfo_url="https://example.com/userinfo",
            scopes=scopes,
        )

        email_scope = config.get_scope_by_name("email")
        assert email_scope is not None
        assert email_scope.name == "email"
        assert email_scope.required is True

        invalid_scope = config.get_scope_by_name("invalid")
        assert invalid_scope is None

    def test_get_required_scopes(self):
        """Test getting required scopes."""
        scopes = [
            OAuthScope(name="email", description="Email access", required=True),
            OAuthScope(name="profile", description="Profile access", required=False),
            OAuthScope(name="openid", description="OpenID", required=True),
        ]

        config = OAuthProviderConfig(
            name="Test",
            provider=IntegrationProvider.GOOGLE,
            authorization_url="https://example.com/auth",
            token_url="https://example.com/token",
            userinfo_url="https://example.com/userinfo",
            scopes=scopes,
        )

        required_scopes = config.get_required_scopes()
        assert set(required_scopes) == {"email", "openid"}

    def test_get_sensitive_scopes(self):
        """Test getting sensitive scopes."""
        scopes = [
            OAuthScope(name="email", description="Email access", sensitive=False),
            OAuthScope(name="drive", description="Drive access", sensitive=True),
            OAuthScope(name="gmail", description="Gmail access", sensitive=True),
        ]

        config = OAuthProviderConfig(
            name="Test",
            provider=IntegrationProvider.GOOGLE,
            authorization_url="https://example.com/auth",
            token_url="https://example.com/token",
            userinfo_url="https://example.com/userinfo",
            scopes=scopes,
        )

        sensitive_scopes = config.get_sensitive_scopes()
        assert set(sensitive_scopes) == {"drive", "gmail"}


class TestOAuthConfig:
    """Test OAuth configuration manager."""

    def setup_method(self):
        """Set up test environment."""
        # Reset global config before each test
        reset_oauth_config()

        # Create test settings
        self.settings = Settings(
            google_client_id="test-google-client-id",
            google_client_secret="test-google-client-secret",
            azure_ad_client_id="test-microsoft-client-id",
            azure_ad_client_secret="test-microsoft-client-secret",
        )

        self.oauth_config = OAuthConfig(self.settings)

    def test_oauth_config_initialization(self):
        """Test OAuth configuration initialization."""
        assert self.oauth_config is not None
        assert len(self.oauth_config.get_available_providers()) == 2
        assert IntegrationProvider.GOOGLE in self.oauth_config.get_available_providers()
        assert (
            IntegrationProvider.MICROSOFT in self.oauth_config.get_available_providers()
        )

    def test_oauth_config_missing_credentials(self):
        """Test OAuth configuration with missing credentials."""
        settings_no_creds = Settings(
            google_client_id=None,
            google_client_secret=None,
            azure_ad_client_id=None,
            azure_ad_client_secret=None,
        )
        config = OAuthConfig(settings_no_creds)

        # Should have no providers available
        assert len(config.get_available_providers()) == 0

    def test_get_provider_config(self):
        """Test getting provider configuration."""
        google_config = self.oauth_config.get_provider_config(
            IntegrationProvider.GOOGLE
        )
        assert google_config is not None
        assert google_config.name == "Google"
        assert google_config.client_id == "test-google-client-id"

        microsoft_config = self.oauth_config.get_provider_config(
            IntegrationProvider.MICROSOFT
        )
        assert microsoft_config is not None
        assert microsoft_config.name == "Microsoft"
        assert microsoft_config.client_id == "test-microsoft-client-id"

    def test_is_provider_available(self):
        """Test provider availability check."""
        assert (
            self.oauth_config.is_provider_available(IntegrationProvider.GOOGLE) is True
        )
        assert (
            self.oauth_config.is_provider_available(IntegrationProvider.MICROSOFT)
            is True
        )

    def test_microsoft_provider_initialization(self):
        """Test Microsoft OAuth provider initialization."""
        config = self.oauth_config.get_provider_config(IntegrationProvider.MICROSOFT)
        assert isinstance(config, OAuthProviderConfig)

        assert (
            config.authorization_url
            == "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        )
        assert (
            config.token_url
            == "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        )
        assert config.userinfo_url == "https://graph.microsoft.com/v1.0/me"
        assert config.client_id == self.settings.azure_ad_client_id
        assert config.client_secret == self.settings.azure_ad_client_secret
        assert set(config.default_scopes) == {
            "openid",
            "email",
            "profile",
            "offline_access",
            "https://graph.microsoft.com/User.Read",
        }
        assert config.supports_pkce is True
        assert config.pkce_method == PKCEChallengeMethod.S256

    def test_generate_state(self):
        """Test OAuth state generation."""
        state = self.oauth_config.generate_state(
            user_id="user123",
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
            scopes=["email", "profile"],
        )

        assert state.user_id == "user123"
        assert state.provider == IntegrationProvider.GOOGLE
        assert state.redirect_uri == "https://example.com/callback"
        assert state.scopes == ["email", "profile"]
        assert state.pkce_verifier is not None  # Google supports PKCE
        assert len(state.state) > 0

        # State should be stored
        assert state.state in self.oauth_config._active_states

    def test_validate_state(self):
        """Test OAuth state validation."""
        # Generate state
        state = self.oauth_config.generate_state(
            user_id="user123",
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
        )

        # Valid validation
        validated_state = self.oauth_config.validate_state(
            state.state, "user123", IntegrationProvider.GOOGLE
        )
        assert validated_state is not None
        assert validated_state.state == state.state

        # Invalid state
        invalid_validated = self.oauth_config.validate_state(
            "invalid-state", "user123", IntegrationProvider.GOOGLE
        )
        assert invalid_validated is None

        # Invalid user
        invalid_user = self.oauth_config.validate_state(
            state.state, "wrong-user", IntegrationProvider.GOOGLE
        )
        assert invalid_user is None

    def test_cleanup_expired_states(self):
        """Test cleanup of expired OAuth states."""
        # Generate expired state
        expired_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        expired_state = OAuthState(
            state="expired-state",
            user_id="user123",
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
            created_at=expired_time,
            expires_at=expired_time + timedelta(minutes=10),
        )

        # Manually add expired state
        self.oauth_config._active_states["expired-state"] = expired_state

        # Generate valid state
        valid_state = self.oauth_config.generate_state(
            user_id="user123",
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
        )

        # Should have 2 states
        assert len(self.oauth_config._active_states) == 2

        # Cleanup expired states
        cleaned_count = self.oauth_config.cleanup_expired_states()
        assert cleaned_count == 1
        assert len(self.oauth_config._active_states) == 1
        assert valid_state.state in self.oauth_config._active_states
        assert "expired-state" not in self.oauth_config._active_states

    def test_remove_state(self):
        """Test removing OAuth state."""
        state = self.oauth_config.generate_state(
            user_id="user123",
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
        )

        # State should exist
        assert state.state in self.oauth_config._active_states

        # Remove state
        result = self.oauth_config.remove_state(state.state)
        assert result is True
        assert state.state not in self.oauth_config._active_states

        # Try to remove again
        result = self.oauth_config.remove_state(state.state)
        assert result is False

    def test_generate_authorization_url(self):
        """Test authorization URL generation."""
        auth_url, oauth_state = self.oauth_config.generate_authorization_url(
            provider=IntegrationProvider.GOOGLE,
            user_id="user123",
            redirect_uri="https://example.com/callback",
            scopes=["email", "profile"],
        )

        assert auth_url.startswith("https://accounts.google.com/o/oauth2/v2/auth")
        assert "client_id=test-google-client-id" in auth_url
        assert "redirect_uri=https%3A%2F%2Fexample.com%2Fcallback" in auth_url
        assert "scope=email+profile" in auth_url
        assert f"state={oauth_state.state}" in auth_url
        assert "code_challenge=" in auth_url  # PKCE challenge
        assert "code_challenge_method=S256" in auth_url

    def test_generate_microsoft_authorization_url(self):
        """Test authorization URL generation for Microsoft."""
        auth_url, oauth_state = self.oauth_config.generate_authorization_url(
            provider=IntegrationProvider.MICROSOFT,
            user_id="user-msft-123",
            redirect_uri="https://example.com/msft-callback",
            scopes=["Mail.Read"],  # Additional scope
        )

        assert auth_url.startswith(
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        )
        assert f"client_id={self.settings.azure_ad_client_id}" in auth_url
        assert "redirect_uri=https%3A%2F%2Fexample.com%2Fmsft-callback" in auth_url
        assert "response_type=code" in auth_url
        # Check for default and additional scopes
        expected_scopes = {
            "openid",
            "email",
            "profile",
            "offline_access",
            "https://graph.microsoft.com/User.Read",
            "Mail.Read",
        }
        # URL scopes are space-encoded, so we need to check for each one
        for scope in expected_scopes:
            assert (
                scope in oauth_state.scopes
            )  # Check that the state object has the correct scopes
            assert scope in auth_url  # Check that the url has the correct scopes

        assert f"state={oauth_state.state}" in auth_url
        assert "code_challenge=" in auth_url
        assert "code_challenge_method=S256" in auth_url
        assert oauth_state.provider == IntegrationProvider.MICROSOFT
        assert oauth_state.user_id == "user-msft-123"

    def test_generate_authorization_url_invalid_provider(self):
        """Test authorization URL generation with invalid provider."""
        with patch.object(self.oauth_config, "get_provider_config", return_value=None):
            with pytest.raises(ValidationException) as exc_info:
                self.oauth_config.generate_authorization_url(
                    provider=IntegrationProvider.GOOGLE,
                    user_id="user123",
                    redirect_uri="https://example.com/callback",
                )
            assert "OAuth provider not available" in str(exc_info.value)

    def test_generate_authorization_url_invalid_scopes(self):
        """Test authorization URL generation with invalid scopes."""
        with pytest.raises(ValidationException) as exc_info:
            self.oauth_config.generate_authorization_url(
                provider=IntegrationProvider.GOOGLE,
                user_id="user123",
                redirect_uri="https://example.com/callback",
                scopes=["invalid_scope"],
            )
        assert "Invalid scopes" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(self):
        """Test successful authorization code exchange."""
        # Generate state for exchange
        oauth_state = self.oauth_config.generate_state(
            user_id="user123",
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
        )

        # Mock successful token response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_patch:
            mock_async_client = AsyncMock()
            mock_async_client.post = AsyncMock(return_value=mock_response)
            mock_client_patch.return_value.__aenter__.return_value = mock_async_client

            tokens = await self.oauth_config.exchange_code_for_tokens(
                provider=IntegrationProvider.GOOGLE,
                authorization_code="test-auth-code",
                oauth_state=oauth_state,
            )

            assert tokens["access_token"] == "test-access-token"
            assert tokens["refresh_token"] == "test-refresh-token"
            assert tokens["expires_in"] == 3600

            expected_token_url = "https://oauth2.googleapis.com/token"
            expected_payload = {
                "client_id": self.settings.google_client_id,
                "client_secret": self.settings.google_client_secret,
                "code": "test-auth-code",
                "redirect_uri": oauth_state.redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": oauth_state.pkce_verifier,
            }
            mock_async_client.post.assert_called_once_with(
                expected_token_url, data=expected_payload
            )

    @pytest.mark.asyncio
    async def test_refresh_access_token_microsoft_success(self):
        """Test successful token refresh for Microsoft."""
        mock_response_data = {
            "access_token": "new-msft-access-token",
            "refresh_token": "new-msft-refresh-token",  # Microsoft may return a new refresh token
            "expires_in": 3599,
            "scope": "openid email profile offline_access https://graph.microsoft.com/User.Read",
            "token_type": "Bearer",
        }
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_patch:
            mock_async_client = AsyncMock()
            mock_async_client.post = AsyncMock(return_value=mock_response)
            mock_client_patch.return_value.__aenter__.return_value = mock_async_client

            tokens = await self.oauth_config.refresh_access_token(
                provider=IntegrationProvider.MICROSOFT,
                refresh_token="test-msft-refresh-token",
            )

            assert tokens["access_token"] == "new-msft-access-token"
            assert tokens["refresh_token"] == "new-msft-refresh-token"
            assert tokens["expires_in"] == 3599
            assert (
                tokens["scope"]
                == "openid email profile offline_access https://graph.microsoft.com/User.Read"
            )

            expected_token_url = (
                "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            )
            expected_payload = {
                "client_id": self.settings.azure_ad_client_id,
                "client_secret": self.settings.azure_ad_client_secret,
                "refresh_token": "test-msft-refresh-token",
                "grant_type": "refresh_token",
            }
            mock_async_client.post.assert_called_once_with(
                expected_token_url, data=expected_payload
            )

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_microsoft_success(self):
        """Test successful authorization code exchange for Microsoft."""
        oauth_state = self.oauth_config.generate_state(
            user_id="user-msft-123",
            provider=IntegrationProvider.MICROSOFT,
            redirect_uri="https://example.com/msft-callback",
            scopes=[
                "openid",
                "email",
                "profile",
                "offline_access",
                "https://graph.microsoft.com/User.Read",
            ],
        )

        mock_response_data = {
            "access_token": "msft-access-token",
            "refresh_token": "msft-refresh-token",
            "expires_in": 3599,
            "scope": "openid email profile offline_access https://graph.microsoft.com/User.Read",
            "token_type": "Bearer",
        }
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_patch:
            mock_async_client = AsyncMock()
            mock_async_client.post = AsyncMock(return_value=mock_response)
            mock_client_patch.return_value.__aenter__.return_value = mock_async_client

            tokens = await self.oauth_config.exchange_code_for_tokens(
                provider=IntegrationProvider.MICROSOFT,
                authorization_code="test-msft-auth-code",
                oauth_state=oauth_state,
            )

            assert tokens["access_token"] == "msft-access-token"
            assert tokens["refresh_token"] == "msft-refresh-token"
            assert tokens["expires_in"] == 3599
            assert (
                tokens["scope"]
                == "openid email profile offline_access https://graph.microsoft.com/User.Read"
            )

            expected_token_url = (
                "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            )
            expected_payload = {
                "client_id": self.settings.azure_ad_client_id,
                "client_secret": self.settings.azure_ad_client_secret,
                "code": "test-msft-auth-code",
                "redirect_uri": "https://example.com/msft-callback",
                "grant_type": "authorization_code",
                "code_verifier": oauth_state.pkce_verifier,
            }
            mock_async_client.post.assert_called_once_with(
                expected_token_url, data=expected_payload
            )

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_failure(self):
        """Test failed authorization code exchange."""
        oauth_state = self.oauth_config.generate_state(
            user_id="user123",
            provider=IntegrationProvider.GOOGLE,
            redirect_uri="https://example.com/callback",
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPError("Token exchange failed")
            )

            with pytest.raises(ValidationException) as exc_info:
                await self.oauth_config.exchange_code_for_tokens(
                    provider=IntegrationProvider.GOOGLE,
                    authorization_code="invalid-code",
                    oauth_state=oauth_state,
                )
            assert "Failed to exchange authorization code" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self):
        """Test successful token refresh."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            tokens = await self.oauth_config.refresh_access_token(
                provider=IntegrationProvider.GOOGLE,
                refresh_token="test-refresh-token",
            )

            assert tokens["access_token"] == "new-access-token"
            assert tokens["expires_in"] == 3600

    @pytest.mark.asyncio
    async def test_refresh_access_token_failure(self):
        """Test failed token refresh."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPError("Refresh failed")
            )

            with pytest.raises(ValidationException) as exc_info:
                await self.oauth_config.refresh_access_token(
                    provider=IntegrationProvider.GOOGLE,
                    refresh_token="invalid-refresh-token",
                )
            assert "Failed to refresh access token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_info_success(self):
        """Test successful user info retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "user123",
            "email": "user@example.com",
            "name": "Test User",
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            user_info = await self.oauth_config.get_user_info(
                provider=IntegrationProvider.GOOGLE,
                access_token="test-access-token",
            )

            assert user_info["id"] == "user123"
            assert user_info["email"] == "user@example.com"
            assert user_info["name"] == "Test User"

    @pytest.mark.asyncio
    async def test_get_user_info_microsoft_success(self):
        """Test successful user info retrieval for Microsoft."""
        mock_user_data = {
            "id": "msft-user-id-123",
            "userPrincipalName": "test.user@example.com",
            "displayName": "Test User Microsoft",
            "mail": "test.user@example.com",  # Sometimes 'mail' is preferred over 'userPrincipalName'
            "givenName": "Test",
            "surname": "User",
        }
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_user_data
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client_patch:
            mock_async_client = AsyncMock()
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_client_patch.return_value.__aenter__.return_value = mock_async_client

            user_info = await self.oauth_config.get_user_info(
                provider=IntegrationProvider.MICROSOFT,
                access_token="test-msft-access-token",
            )

            assert user_info["id"] == "msft-user-id-123"
            assert user_info["userPrincipalName"] == "test.user@example.com"
            assert user_info["displayName"] == "Test User Microsoft"

            expected_userinfo_url = "https://graph.microsoft.com/v1.0/me"
            expected_headers = {"Authorization": "Bearer test-msft-access-token"}
            mock_async_client.get.assert_called_once_with(
                expected_userinfo_url, headers=expected_headers
            )

    @pytest.mark.asyncio
    async def test_get_user_info_failure(self):
        """Test failed user info retrieval."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPError("User info failed")
            )

            with pytest.raises(ValidationException) as exc_info:
                await self.oauth_config.get_user_info(
                    provider=IntegrationProvider.GOOGLE,
                    access_token="invalid-token",
                )
            assert "Failed to retrieve user info" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_revoke_token_success(self):
        """Test successful token revocation."""
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await self.oauth_config.revoke_token(
                provider=IntegrationProvider.GOOGLE,
                token="test-token",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_revoke_token_not_supported(self):
        """Test token revocation for provider without revoke endpoint."""
        result = await self.oauth_config.revoke_token(
            provider=IntegrationProvider.MICROSOFT,
            token="test-token",
        )

        # Microsoft doesn't have revoke URL configured
        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_token_failure(self):
        """Test failed token revocation."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPError("Revoke failed")
            )

            result = await self.oauth_config.revoke_token(
                provider=IntegrationProvider.GOOGLE,
                token="test-token",
            )

            assert result is False


class TestGlobalOAuthConfig:
    """Test global OAuth configuration management."""

    def setup_method(self):
        """Set up test environment."""
        reset_oauth_config()

    def test_get_oauth_config_singleton(self):
        """Test that get_oauth_config returns singleton instance."""
        config1 = get_oauth_config()
        config2 = get_oauth_config()

        assert config1 is config2

    def test_get_oauth_config_with_settings(self):
        """Test get_oauth_config with custom settings."""
        custom_settings = Settings(
            google_client_id="custom-google-id",
            google_client_secret="custom-google-secret",
        )

        config = get_oauth_config(custom_settings)
        assert config is not None

        google_config = config.get_provider_config(IntegrationProvider.GOOGLE)
        assert google_config.client_id == "custom-google-id"

    def test_reset_oauth_config(self):
        """Test resetting global OAuth configuration."""
        # Get initial config
        config1 = get_oauth_config()

        # Reset and get new config
        reset_oauth_config()
        config2 = get_oauth_config()

        # Should be different instances
        assert config1 is not config2


class TestOAuthConfigIntegration:
    """Integration tests for OAuth configuration."""

    def setup_method(self):
        """Set up test environment."""
        reset_oauth_config()
        self.settings = Settings(
            google_client_id="test-google-id",
            google_client_secret="test-google-secret",
        )
        self.oauth_config = OAuthConfig(self.settings)

    def test_full_oauth_flow_state_management(self):
        """Test complete OAuth flow state management."""
        # 1. Generate authorization URL
        auth_url, oauth_state = self.oauth_config.generate_authorization_url(
            provider=IntegrationProvider.GOOGLE,
            user_id="user123",
            redirect_uri="https://example.com/callback",
            scopes=["email", "profile"],
        )

        assert oauth_state.state in self.oauth_config._active_states

        # 2. Validate state during callback
        validated_state = self.oauth_config.validate_state(
            oauth_state.state, "user123", IntegrationProvider.GOOGLE
        )
        assert validated_state is not None

        # 3. Remove state after successful completion
        result = self.oauth_config.remove_state(oauth_state.state)
        assert result is True
        assert oauth_state.state not in self.oauth_config._active_states

    def test_scope_validation_with_required_scopes(self):
        """Test scope validation including required scopes."""
        # Request scopes without required ones
        auth_url, oauth_state = self.oauth_config.generate_authorization_url(
            provider=IntegrationProvider.GOOGLE,
            user_id="user123",
            redirect_uri="https://example.com/callback",
            scopes=["email"],  # Missing required 'openid' and 'profile'
        )

        # Should automatically include required scopes
        google_config = self.oauth_config.get_provider_config(
            IntegrationProvider.GOOGLE
        )
        required_scopes = google_config.get_required_scopes()

        for required_scope in required_scopes:
            assert required_scope in oauth_state.scopes
