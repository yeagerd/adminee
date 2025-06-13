"""
Unit tests for OAuth configuration and PKCE functionality.

Tests OAuth provider configuration, PKCE challenge generation,
state management, and token exchange operations.
"""

import base64
import hashlib
import os
import tempfile
import urllib.parse
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from services.user_management.exceptions import ValidationException
from services.user_management.integrations.oauth_config import (
    OAuthConfig,
    OAuthProviderConfig,
    OAuthScope,
    OAuthState,
    PKCEChallenge,
    PKCEChallengeMethod,
    get_oauth_config,
    reset_oauth_config,
)
from services.user_management.models.integration import IntegrationProvider
from services.user_management.utils import secrets as user_secrets


class TestPKCEChallenge:
    """Test PKCE challenge generation and validation."""

    def setup_method(self):
        pass

    def teardown_method(self):
        pass

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

    def setup_method(self):
        pass

    def teardown_method(self):
        pass

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

    def setup_method(self):
        pass

    def teardown_method(self):
        pass

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

    def setup_method(self):
        pass

    def teardown_method(self):
        """Clean up test environment."""
        pass

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

        # Create temporary database file for test isolation
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()

        # Mock environment variables instead of modifying os.environ directly
        # This prevents race conditions in parallel execution
        self.env_patch = patch.dict(
            os.environ,
            {
                "DB_URL_USER_MANAGEMENT": f"sqlite:///{self.temp_db.name}",
                "TOKEN_ENCRYPTION_SALT": "dGVzdC1zYWx0LTE2Ynl0ZQ==",
                "API_FRONTEND_USER_KEY": "test-api-key",
                "CLERK_SECRET_KEY": "test-clerk-key",
                "OAUTH_REDIRECT_URI": "https://example.com/oauth/callback",
            },
            clear=False,
        )
        self.env_patch.start()

    def teardown_method(self):
        """Clean up test environment."""
        # Stop environment patch
        if hasattr(self, "env_patch"):
            self.env_patch.stop()

        # Clean up temporary database file
        if hasattr(self, "temp_db") and os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

        # Reset global config after each test
        reset_oauth_config()

    @patch('services.user_management.utils.secrets.get_google_client_id', return_value="test-google-client-id")
    @patch('services.user_management.utils.secrets.get_google_client_secret', return_value="test-google-client-secret")
    @patch('services.user_management.utils.secrets.get_azure_ad_client_id', return_value="test-azure-client-id")
    @patch('services.user_management.utils.secrets.get_azure_ad_client_secret', return_value="test-azure-client-secret")
    @patch('services.user_management.utils.secrets.get_azure_ad_tenant_id', return_value="test-azure-tenant-id")
    def test_oauth_config_initialization(self, *args):
        """Test OAuth configuration initialization."""
        # Clear any cached values
        user_secrets.clear_cache()
        
        # Initialize OAuth config
        oauth_config = OAuthConfig()

        # Verify providers were initialized
        providers = oauth_config.get_available_providers()
        assert IntegrationProvider.GOOGLE in providers
        assert IntegrationProvider.MICROSOFT in providers

        # Verify Google provider config
        google_config = oauth_config.get_provider_config(IntegrationProvider.GOOGLE)
        assert google_config is not None
        assert google_config.client_id == "test-google-client-id"
        assert google_config.client_secret == "test-google-client-secret"

        # Verify Microsoft provider config
        microsoft_config = oauth_config.get_provider_config(IntegrationProvider.MICROSOFT)
        assert microsoft_config is not None
        assert microsoft_config.client_id == "test-azure-client-id"
        assert microsoft_config.client_secret == "test-azure-client-secret"

    def test_is_provider_available(self):
        """Test provider availability check."""
        assert (
            self.oauth_config.is_provider_available(IntegrationProvider.GOOGLE) is True
        )
        assert (
            self.oauth_config.is_provider_available(IntegrationProvider.MICROSOFT)
            is True
        )

    @patch('services.user_management.utils.secrets.get_google_client_id', return_value="test-id")
    @patch('services.user_management.utils.secrets.get_google_client_secret', return_value="test-secret")
    @patch('services.user_management.utils.secrets.get_azure_ad_client_id', return_value="test-azure-id")
    @patch('services.user_management.utils.secrets.get_azure_ad_client_secret', return_value="test-azure-secret")
    @patch('services.user_management.utils.secrets.get_azure_ad_tenant_id', return_value="test-tenant")
    def test_get_oauth_config_singleton(self, *args):
        """Test that get_oauth_config returns singleton instance."""
        # Clear any cached values
        user_secrets.clear_cache()
        
        # Reset global config
        reset_oauth_config()

        # First call should create a new instance
        config1 = get_oauth_config()
        assert config1 is not None

        # Second call should return the same instance
        config2 = get_oauth_config()
        assert config2 is config1

        # Reset and verify new instance is created
        reset_oauth_config()
        config3 = get_oauth_config()
        assert config3 is not config1

    @patch('services.user_management.utils.secrets.get_google_client_id', return_value="test-google-id")
    @patch('services.user_management.utils.secrets.get_google_client_secret', return_value="test-google-secret")
    def test_get_oauth_config_uses_secrets(self, mock_client_id, mock_client_secret):
        """Test get_oauth_config uses values from secrets module."""
        # Clear any cached values
        user_secrets.clear_cache()
        
        # Reset global config
        reset_oauth_config()

        # Get config which should use the mocked secrets
        config = get_oauth_config()
        assert config is not None

        # Verify secrets were used
        google_config = config.get_provider_config(IntegrationProvider.GOOGLE)
        assert google_config.client_id == "test-google-id"
        assert google_config.client_secret == "test-google-secret"

    # ... rest of the code remains the same ...
            assert config is not None
