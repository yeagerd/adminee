"""
OAuth provider configuration for User Management Service.

Provides comprehensive OAuth 2.0 configurations for Google, Microsoft,
and other providers with PKCE support, state validation, and scope management.
"""

import base64
import hashlib
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx
import structlog
from pydantic import BaseModel, Field, field_validator

from ..exceptions import ValidationException
from ..models.integration import IntegrationProvider
from ..settings import Settings

# Set up logging
logger = structlog.get_logger(__name__)


class OAuthGrantType(str, Enum):
    """OAuth grant types supported by the system."""

    AUTHORIZATION_CODE = "authorization_code"
    REFRESH_TOKEN = "refresh_token"


class PKCEChallengeMethod(str, Enum):
    """PKCE challenge methods for OAuth security."""

    S256 = "S256"
    PLAIN = "plain"


class OAuthScope(BaseModel):
    """OAuth scope configuration."""

    name: str = Field(..., description="Scope name")
    description: str = Field(..., description="Human-readable scope description")
    required: bool = Field(default=False, description="Whether scope is required")
    sensitive: bool = Field(
        default=False, description="Whether scope accesses sensitive data"
    )


class OAuthState(BaseModel):
    """OAuth state for security validation."""

    state: str = Field(..., description="Random state string")
    user_id: str = Field(..., description="User ID for this OAuth flow")
    provider: IntegrationProvider = Field(..., description="OAuth provider")
    redirect_uri: str = Field(..., description="Redirect URI for this flow")
    scopes: List[str] = Field(default_factory=list, description="Requested scopes")
    pkce_verifier: Optional[str] = Field(None, description="PKCE code verifier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=10)
    )

    @field_validator("expires_at", mode="before")
    @classmethod
    def set_expires_at(cls, v, info):
        """Set expiration time if not provided."""
        if v is None and info.data.get("created_at"):
            return info.data["created_at"] + timedelta(minutes=10)
        return v

    def is_expired(self) -> bool:
        """Check if the state has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def is_valid_for_callback(
        self, state: str, user_id: str, provider: IntegrationProvider
    ) -> bool:
        """Validate state for OAuth callback."""
        return (
            not self.is_expired()
            and self.state == state
            and self.user_id == user_id
            and self.provider == provider
        )


class OAuthProviderConfig(BaseModel):
    """OAuth provider configuration."""

    name: str = Field(..., description="Provider name")
    provider: IntegrationProvider = Field(..., description="Provider enum")
    client_id: Optional[str] = Field(None, description="OAuth client ID")
    client_secret: Optional[str] = Field(None, description="OAuth client secret")

    # OAuth endpoints
    authorization_url: str = Field(..., description="Authorization endpoint URL")
    token_url: str = Field(..., description="Token exchange endpoint URL")
    userinfo_url: str = Field(..., description="User info endpoint URL")
    revoke_url: Optional[str] = Field(None, description="Token revocation endpoint")

    # OAuth configuration
    scopes: List[OAuthScope] = Field(
        default_factory=list, description="Available scopes"
    )
    default_scopes: List[str] = Field(
        default_factory=list, description="Default scopes to request"
    )
    supports_pkce: bool = Field(
        default=True, description="Whether provider supports PKCE"
    )
    pkce_method: PKCEChallengeMethod = Field(
        default=PKCEChallengeMethod.S256, description="PKCE method"
    )

    # Additional configuration
    extra_auth_params: Dict[str, str] = Field(
        default_factory=dict, description="Extra auth parameters"
    )
    extra_token_params: Dict[str, str] = Field(
        default_factory=dict, description="Extra token parameters"
    )

    def get_scope_by_name(self, name: str) -> Optional[OAuthScope]:
        """Get scope configuration by name."""
        return next((scope for scope in self.scopes if scope.name == name), None)

    def validate_scopes(
        self, requested_scopes: List[str]
    ) -> Tuple[List[str], List[str]]:
        """Validate requested scopes and return valid/invalid lists."""
        valid_scope_names = {scope.name for scope in self.scopes}
        valid_scopes = [
            scope for scope in requested_scopes if scope in valid_scope_names
        ]
        invalid_scopes = [
            scope for scope in requested_scopes if scope not in valid_scope_names
        ]
        return valid_scopes, invalid_scopes

    def get_required_scopes(self) -> List[str]:
        """Get list of required scopes."""
        return [scope.name for scope in self.scopes if scope.required]

    def get_sensitive_scopes(self) -> List[str]:
        """Get list of sensitive scopes."""
        return [scope.name for scope in self.scopes if scope.sensitive]


class PKCEChallenge(BaseModel):
    """PKCE challenge for OAuth security."""

    code_verifier: str = Field(..., description="Code verifier")
    code_challenge: str = Field(..., description="Code challenge")
    code_challenge_method: PKCEChallengeMethod = Field(
        ..., description="Challenge method"
    )

    @classmethod
    def generate(
        cls, method: PKCEChallengeMethod = PKCEChallengeMethod.S256
    ) -> "PKCEChallenge":
        """Generate a new PKCE challenge."""
        # Generate code verifier (43-128 characters)
        code_verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )

        # Generate code challenge
        if method == PKCEChallengeMethod.S256:
            code_challenge = (
                base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode("utf-8")).digest()
                )
                .decode("utf-8")
                .rstrip("=")
            )
        else:  # PLAIN method
            code_challenge = code_verifier

        return cls(
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            code_challenge_method=method,
        )


class OAuthConfig:
    """
    OAuth configuration manager for all providers.

    Handles provider configurations, state management, PKCE challenges,
    and OAuth flow coordination.
    """

    def __init__(self, settings: Settings):
        """Initialize OAuth configuration."""
        self.settings = settings
        self.logger = structlog.get_logger(__name__)
        self._providers = self._initialize_providers()
        self._active_states: Dict[str, OAuthState] = {}

    def _initialize_providers(self) -> Dict[IntegrationProvider, OAuthProviderConfig]:
        """Initialize OAuth provider configurations."""
        providers = {}

        # Google OAuth configuration
        google_scopes = [
            OAuthScope(
                name="openid",
                description="OpenID Connect authentication",
                required=True,
            ),
            OAuthScope(
                name="email",
                description="Access to user's email address",
                required=True,
            ),
            OAuthScope(
                name="profile",
                description="Access to user's basic profile information",
                required=True,
            ),
            OAuthScope(
                name="https://www.googleapis.com/auth/gmail.readonly",
                description="Read-only access to Gmail messages",
                sensitive=True,
            ),
            OAuthScope(
                name="https://www.googleapis.com/auth/gmail.modify",
                description="Modify Gmail messages and settings",
                sensitive=True,
            ),
            OAuthScope(
                name="https://www.googleapis.com/auth/calendar.readonly",
                description="Read-only access to Google Calendar",
                sensitive=True,
            ),
            OAuthScope(
                name="https://www.googleapis.com/auth/calendar",
                description="Full access to Google Calendar",
                sensitive=True,
            ),
            OAuthScope(
                name="https://www.googleapis.com/auth/drive.readonly",
                description="Read-only access to Google Drive",
                sensitive=True,
            ),
            OAuthScope(
                name="https://www.googleapis.com/auth/drive.file",
                description="Access to files created or opened by the app",
                sensitive=True,
            ),
        ]

        providers[IntegrationProvider.GOOGLE] = OAuthProviderConfig(
            name="Google",
            provider=IntegrationProvider.GOOGLE,
            client_id=self.settings.google_client_id,
            client_secret=self.settings.google_client_secret,
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
            revoke_url="https://oauth2.googleapis.com/revoke",
            scopes=google_scopes,
            default_scopes=["openid", "email", "profile"],
            supports_pkce=True,
            pkce_method=PKCEChallengeMethod.S256,
            extra_auth_params={"access_type": "offline", "prompt": "consent"},
        )

        # Microsoft OAuth configuration
        microsoft_scopes = [
            # OpenID Connect scopes (standard for Microsoft)
            OAuthScope(
                name="openid",
                description="OpenID Connect authentication",
                required=True,
            ),
            OAuthScope(
                name="email",
                description="Access to user's email address",
                required=True,
            ),
            OAuthScope(
                name="profile",
                description="Access to user's basic profile information",
                required=True,
            ),
            OAuthScope(
                name="offline_access",
                description="Maintain access to data you have given it access to",  # Standard Microsoft description
                required=False,  # Typically not required, but can be requested
                sensitive=False,
            ),
            # Microsoft Graph API scopes
            OAuthScope(
                name="https://graph.microsoft.com/User.Read",
                description="Read user profile information",
                required=False,
            ),
            OAuthScope(
                name="https://graph.microsoft.com/Mail.Read",
                description="Read-only access to Outlook mail",
                sensitive=True,
            ),
            OAuthScope(
                name="https://graph.microsoft.com/Mail.ReadWrite",
                description="Read and write access to Outlook mail",
                sensitive=True,
            ),
            OAuthScope(
                name="https://graph.microsoft.com/Calendars.Read",
                description="Read-only access to Outlook calendar",
                sensitive=True,
            ),
            OAuthScope(
                name="https://graph.microsoft.com/Calendars.ReadWrite",
                description="Read and write access to Outlook calendar",
                sensitive=True,
            ),
            OAuthScope(
                name="https://graph.microsoft.com/Files.Read",
                description="Read-only access to OneDrive files",
                sensitive=True,
            ),
            OAuthScope(
                name="https://graph.microsoft.com/Files.ReadWrite",
                description="Read and write access to OneDrive files",
                sensitive=True,
            ),
        ]

        # Do not use the tenant-specific id, as then the user must be registered in the tenant
        tenant_id = "common"

        providers[IntegrationProvider.MICROSOFT] = OAuthProviderConfig(
            name="Microsoft",
            provider=IntegrationProvider.MICROSOFT,
            client_id=self.settings.azure_ad_client_id,
            client_secret=self.settings.azure_ad_client_secret,
            authorization_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
            token_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            userinfo_url="https://graph.microsoft.com/v1.0/me",
            revoke_url=None,  # Microsoft doesn't have a standard revoke endpoint
            scopes=microsoft_scopes,
            default_scopes=[
                "openid",
                "email",
                "profile",
                "offline_access",
                "https://graph.microsoft.com/User.Read",
            ],
            supports_pkce=True,
            pkce_method=PKCEChallengeMethod.S256,
        )

        # Filter out providers with missing credentials
        active_providers = {}
        for provider, config in providers.items():
            if config.client_id and config.client_secret:
                active_providers[provider] = config
            else:
                self.logger.warning(
                    "oauth_provider_disabled",
                    provider=provider.value,
                    reason="missing_credentials",
                )

        return active_providers

    def get_provider_config(
        self, provider: IntegrationProvider
    ) -> Optional[OAuthProviderConfig]:
        """Get provider configuration."""
        return self._providers.get(provider)

    def get_available_providers(self) -> List[IntegrationProvider]:
        """Get list of available OAuth providers."""
        return list(self._providers.keys())

    def is_provider_available(self, provider: IntegrationProvider) -> bool:
        """Check if a provider is available."""
        return provider in self._providers

    def get_default_redirect_uri(self) -> str:
        """Get the default OAuth redirect URI from settings."""
        return self.settings.oauth_redirect_uri

    def generate_state(
        self,
        user_id: str,
        provider: IntegrationProvider,
        redirect_uri: str,
        scopes: Optional[List[str]] = None,
    ) -> OAuthState:
        """Generate OAuth state for security validation."""
        # Generate secure random state
        state_value = secrets.token_urlsafe(32)

        # Use default scopes if none provided
        if scopes is None:
            provider_config = self.get_provider_config(provider)
            scopes = provider_config.default_scopes if provider_config else []

        # Generate PKCE verifier if provider supports it
        pkce_verifier = None
        provider_config = self.get_provider_config(provider)
        if provider_config and provider_config.supports_pkce:
            pkce_challenge = PKCEChallenge.generate(provider_config.pkce_method)
            pkce_verifier = pkce_challenge.code_verifier

        oauth_state = OAuthState(
            state=state_value,
            user_id=user_id,
            provider=provider,
            redirect_uri=redirect_uri,
            scopes=scopes,
            pkce_verifier=pkce_verifier,
        )

        # Store state for validation
        self._active_states[state_value] = oauth_state

        self.logger.info(
            "oauth_state_generated",
            user_id=user_id,
            provider=provider.value,
            state=state_value,
            scopes=scopes,
        )

        return oauth_state

    def validate_state(
        self,
        state: str,
        user_id: str,
        provider: IntegrationProvider,
    ) -> Optional[OAuthState]:
        """Validate OAuth state from callback."""
        oauth_state = self._active_states.get(state)

        if not oauth_state:
            self.logger.warning(
                "oauth_state_not_found",
                state=state,
                user_id=user_id,
                provider=provider.value,
            )
            return None

        if not oauth_state.is_valid_for_callback(state, user_id, provider):
            self.logger.warning(
                "oauth_state_invalid",
                state=state,
                user_id=user_id,
                provider=provider.value,
                stored_user_id=oauth_state.user_id,
                stored_provider=oauth_state.provider.value,
                expired=oauth_state.is_expired(),
            )
            return None

        self.logger.info(
            "oauth_state_validated",
            state=state,
            user_id=user_id,
            provider=provider.value,
        )

        return oauth_state

    def cleanup_expired_states(self) -> int:
        """Clean up expired OAuth states."""
        current_time = datetime.now(timezone.utc)
        expired_states = [
            state
            for state, oauth_state in self._active_states.items()
            if oauth_state.expires_at < current_time
        ]

        for state in expired_states:
            del self._active_states[state]

        if expired_states:
            self.logger.info(
                "oauth_states_cleaned_up",
                expired_count=len(expired_states),
            )

        return len(expired_states)

    def remove_state(self, state: str) -> bool:
        """Remove OAuth state after successful completion."""
        if state in self._active_states:
            del self._active_states[state]
            return True
        return False

    def generate_authorization_url(
        self,
        provider: IntegrationProvider,
        user_id: str,
        redirect_uri: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        extra_params: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, OAuthState]:
        """Generate OAuth authorization URL."""
        provider_config = self.get_provider_config(provider)
        if not provider_config:
            raise ValidationException(
                "provider",
                provider.value,
                "OAuth provider not available or configured",
            )

        # Use default redirect URI if none provided
        if redirect_uri is None:
            redirect_uri = self.get_default_redirect_uri()

        # Validate and use scopes
        if scopes is None:
            scopes = provider_config.default_scopes.copy()

        # Validate requested scopes
        valid_scopes, invalid_scopes = provider_config.validate_scopes(scopes)

        # Debug logging to understand scope validation issues
        self.logger.debug(
            "oauth_scope_validation",
            provider=provider.value,
            requested_scopes=scopes,
            valid_scopes=valid_scopes,
            invalid_scopes=invalid_scopes,
            available_scopes=[scope.name for scope in provider_config.scopes],
        )

        if invalid_scopes:
            self.logger.error(
                "oauth_scope_validation_failed",
                provider=provider.value,
                invalid_scopes=invalid_scopes,
                available_scopes=[scope.name for scope in provider_config.scopes],
            )
            raise ValidationException(
                "scopes",
                invalid_scopes,
                f"Invalid scopes for provider {provider.value}",
            )

        # Ensure required scopes are included
        required_scopes = provider_config.get_required_scopes()
        for required_scope in required_scopes:
            if required_scope not in valid_scopes:
                valid_scopes.append(required_scope)

        # Generate OAuth state
        oauth_state = self.generate_state(user_id, provider, redirect_uri, valid_scopes)

        # Build authorization URL
        auth_params = {
            "client_id": provider_config.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(valid_scopes),
            "response_type": "code",
            "state": oauth_state.state,
        }

        # Add PKCE challenge if supported
        if provider_config.supports_pkce and oauth_state.pkce_verifier:
            pkce_challenge = PKCEChallenge.generate(provider_config.pkce_method)
            # Update stored state with challenge
            oauth_state.pkce_verifier = pkce_challenge.code_verifier
            self._active_states[oauth_state.state] = oauth_state

            auth_params["code_challenge"] = pkce_challenge.code_challenge
            auth_params["code_challenge_method"] = (
                pkce_challenge.code_challenge_method.value
            )

        # Add provider-specific extra parameters
        auth_params.update(provider_config.extra_auth_params)

        # Add user-provided extra parameters
        if extra_params:
            auth_params.update(extra_params)

        # Build final URL
        auth_url = (
            f"{provider_config.authorization_url}?{urllib.parse.urlencode(auth_params)}"
        )

        self.logger.info(
            "oauth_authorization_url_generated",
            provider=provider.value,
            user_id=user_id,
            scopes=valid_scopes,
            redirect_uri=redirect_uri,
        )

        return auth_url, oauth_state

    async def exchange_code_for_tokens(
        self,
        provider: IntegrationProvider,
        authorization_code: str,
        oauth_state: OAuthState,
    ) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        provider_config = self.get_provider_config(provider)
        if not provider_config:
            raise ValidationException(
                "provider",
                provider.value,
                "OAuth provider not available or configured",
            )

        # Prepare token exchange parameters
        token_params = {
            "client_id": provider_config.client_id,
            "client_secret": provider_config.client_secret,
            "code": authorization_code,
            "grant_type": OAuthGrantType.AUTHORIZATION_CODE.value,
            "redirect_uri": oauth_state.redirect_uri,
        }

        # Add PKCE verifier if used
        if provider_config.supports_pkce and oauth_state.pkce_verifier:
            token_params["code_verifier"] = oauth_state.pkce_verifier

        # Add provider-specific extra parameters
        token_params.update(provider_config.extra_token_params)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    provider_config.token_url,
                    data=token_params,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )
                response.raise_for_status()
                token_data = response.json()

            self.logger.info(
                "oauth_tokens_exchanged",
                provider=provider.value,
                user_id=oauth_state.user_id,
                has_refresh_token=bool(token_data.get("refresh_token")),
            )

            return token_data

        except httpx.HTTPError as e:
            self.logger.error(
                "oauth_token_exchange_failed",
                provider=provider.value,
                user_id=oauth_state.user_id,
                error=str(e),
            )
            raise ValidationException(
                "authorization_code",
                authorization_code,
                f"Failed to exchange authorization code: {str(e)}",
            )

    async def refresh_access_token(
        self,
        provider: IntegrationProvider,
        refresh_token: str,
    ) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        provider_config = self.get_provider_config(provider)
        if not provider_config:
            raise ValidationException(
                "provider",
                provider.value,
                "OAuth provider not available or configured",
            )

        # Prepare refresh token parameters
        refresh_params = {
            "client_id": provider_config.client_id,
            "client_secret": provider_config.client_secret,
            "refresh_token": refresh_token,
            "grant_type": OAuthGrantType.REFRESH_TOKEN.value,
        }

        # Add provider-specific extra parameters
        refresh_params.update(provider_config.extra_token_params)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    provider_config.token_url,
                    data=refresh_params,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )
                response.raise_for_status()
                token_data = response.json()

            self.logger.info(
                "oauth_token_refreshed",
                provider=provider.value,
                has_new_refresh_token=bool(token_data.get("refresh_token")),
            )

            return token_data

        except httpx.HTTPError as e:
            self.logger.error(
                "oauth_token_refresh_failed",
                provider=provider.value,
                error=str(e),
            )
            raise ValidationException(
                "refresh_token",
                refresh_token,
                f"Failed to refresh access token: {str(e)}",
            )

    async def get_user_info(
        self,
        provider: IntegrationProvider,
        access_token: str,
    ) -> Dict[str, Any]:
        """Get user information using access token."""
        provider_config = self.get_provider_config(provider)
        if not provider_config:
            raise ValidationException(
                "provider",
                provider.value,
                "OAuth provider not available or configured",
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    provider_config.userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30.0,
                )
                response.raise_for_status()
                user_info = response.json()

            self.logger.info(
                "oauth_user_info_retrieved",
                provider=provider.value,
                user_id=user_info.get("id") or user_info.get("sub"),
            )

            return user_info

        except httpx.HTTPError as e:
            self.logger.error(
                "oauth_user_info_failed",
                provider=provider.value,
                error=str(e),
            )
            raise ValidationException(
                "access_token",
                access_token,
                f"Failed to retrieve user info: {str(e)}",
            )

    async def revoke_token(
        self,
        provider: IntegrationProvider,
        token: str,
        token_type: str = "access_token",
    ) -> bool:
        """Revoke an OAuth token."""
        provider_config = self.get_provider_config(provider)
        if not provider_config or not provider_config.revoke_url:
            self.logger.warning(
                "oauth_revoke_not_supported",
                provider=provider.value,
            )
            return False

        revoke_params = {
            "token": token,
            "token_type_hint": token_type,
            "client_id": provider_config.client_id,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    provider_config.revoke_url,
                    data=revoke_params,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )
                # Note: Some providers return 200, others 204
                success = response.status_code in [200, 204]

            if success:
                self.logger.info(
                    "oauth_token_revoked",
                    provider=provider.value,
                    token_type=token_type,
                )
            else:
                self.logger.warning(
                    "oauth_token_revoke_failed",
                    provider=provider.value,
                    status_code=response.status_code,
                )

            return success

        except httpx.HTTPError as e:
            self.logger.error(
                "oauth_token_revoke_error",
                provider=provider.value,
                error=str(e),
            )
            return False


# Global OAuth configuration instance
_oauth_config: Optional[OAuthConfig] = None


def get_oauth_config(settings: Optional[Settings] = None) -> OAuthConfig:
    """Get global OAuth configuration instance."""
    global _oauth_config

    # Force reload if settings are provided or if config doesn't exist
    if _oauth_config is None or settings is not None:
        if settings is None:
            settings = Settings()
        _oauth_config = OAuthConfig(settings)

    return _oauth_config


def reset_oauth_config() -> None:
    """Reset global OAuth configuration (for testing)."""
    global _oauth_config
    _oauth_config = None
