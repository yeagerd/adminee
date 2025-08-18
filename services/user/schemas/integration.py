"""
Pydantic schemas for integration management.

Defines request and response models for OAuth integration endpoints,
including integration status, token management, and provider-specific data.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from services.user.models.integration import (
    IntegrationProvider,
    IntegrationStatus,
)
from services.user.utils.validation import (
    check_sql_injection_patterns,
    sanitize_text_input,
    validate_json_safe_string,
    validate_url,
)


class IntegrationScopeResponse(BaseModel):
    """Response model for OAuth scope information."""

    name: str = Field(..., description="Scope name")
    description: str = Field(..., description="Human-readable scope description")
    required: bool = Field(..., description="Whether scope is required")
    sensitive: bool = Field(..., description="Whether scope accesses sensitive data")
    granted: bool = Field(..., description="Whether user has granted this scope")


class IntegrationProviderInfo(BaseModel):
    """Information about an OAuth provider."""

    name: str = Field(..., description="Provider display name")
    provider: IntegrationProvider = Field(..., description="Provider identifier")
    available: bool = Field(
        ..., description="Whether provider is configured and available"
    )
    supported_scopes: List[IntegrationScopeResponse] = Field(
        default_factory=list, description="Available scopes for this provider"
    )
    default_scopes: List[str] = Field(
        default_factory=list, description="Default scopes requested"
    )


class IntegrationResponse(BaseModel):
    """Response model for user integration."""

    id: int = Field(..., description="Integration ID")
    user_id: str = Field(..., description="User ID")
    provider: IntegrationProvider = Field(..., description="OAuth provider")
    status: IntegrationStatus = Field(..., description="Integration status")

    # OAuth metadata
    scopes: List[str] = Field(default_factory=list, description="Granted OAuth scopes")
    external_user_id: Optional[str] = Field(
        None, description="User ID from external provider"
    )
    external_email: Optional[str] = Field(
        None, description="Email from external provider"
    )
    external_name: Optional[str] = Field(
        None, description="Display name from external provider"
    )

    # Token metadata (without actual tokens)
    has_access_token: bool = Field(..., description="Whether access token is available")
    has_refresh_token: bool = Field(
        ..., description="Whether refresh token is available"
    )
    token_expires_at: Optional[datetime] = Field(
        None, description="Access token expiration"
    )
    token_created_at: Optional[datetime] = Field(
        None, description="Token creation time"
    )

    # Integration metadata
    last_sync_at: Optional[datetime] = Field(None, description="Last successful sync")
    last_error: Optional[str] = Field(None, description="Last error message if any")
    error_count: int = Field(default=0, description="Consecutive error count")

    # Timestamps
    created_at: datetime = Field(..., description="Integration creation time")
    updated_at: datetime = Field(..., description="Last update time")

    model_config = ConfigDict(from_attributes=True)


class IntegrationListResponse(BaseModel):
    """Response model for listing user integrations."""

    integrations: List[IntegrationResponse] = Field(
        default_factory=list, description="List of user integrations"
    )
    total: int = Field(..., description="Total number of integrations")
    active_count: int = Field(..., description="Number of active integrations")
    error_count: int = Field(..., description="Number of integrations with errors")


class OAuthStartRequest(BaseModel):
    """Request model for starting OAuth flow."""

    provider: IntegrationProvider = Field(..., description="OAuth provider")
    redirect_uri: Optional[str] = Field(
        None, description="OAuth callback redirect URI (uses default if not provided)"
    )
    scopes: Optional[List[str]] = Field(
        None, description="Requested OAuth scopes (uses defaults if not provided)"
    )
    state_data: Optional[Dict[str, Any]] = Field(
        None, description="Additional state data to preserve through OAuth flow"
    )

    @field_validator("redirect_uri")
    @classmethod
    def validate_redirect_uri(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced redirect URI validation."""
        if v is None:
            return None
        # Use comprehensive URL validation
        return validate_url(v, allowed_schemes=["http", "https"])

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Enhanced OAuth scopes validation."""
        if v is not None:
            cleaned_scopes = []
            for scope in v:
                if scope and scope.strip():
                    # Check for SQL injection patterns
                    check_sql_injection_patterns(scope, "oauth_scope")

                    # Sanitize the scope
                    sanitized_scope = sanitize_text_input(scope, max_length=200)
                    if sanitized_scope:
                        cleaned_scopes.append(sanitized_scope)

            # Remove duplicates
            v = list(set(cleaned_scopes))
            if not v:
                return None
        return v


class OAuthStartResponse(BaseModel):
    """Response model for OAuth flow initiation."""

    provider: IntegrationProvider = Field(..., description="OAuth provider")
    authorization_url: str = Field(..., description="OAuth authorization URL")
    state: str = Field(..., description="OAuth state parameter")
    expires_at: datetime = Field(..., description="State expiration time")
    requested_scopes: List[str] = Field(
        default_factory=list, description="Scopes that will be requested"
    )


class ExternalUserInfo(BaseModel):
    """Model for external user information from OAuth providers."""

    id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None
    verified_email: Optional[bool] = None
    provider: str


class OAuthCallbackRequest(BaseModel):
    """Request model for OAuth callback handling."""

    code: Optional[str] = Field(None, description="OAuth authorization code")
    state: str = Field(..., description="OAuth state parameter")
    error: Optional[str] = Field(None, description="OAuth error if any")
    error_description: Optional[str] = Field(
        None, description="OAuth error description"
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced authorization code validation."""
        if v is None:
            return None

        v = v.strip()
        if not v:
            raise ValueError("Authorization code cannot be empty")

        # Check for SQL injection patterns
        check_sql_injection_patterns(v, "authorization_code")

        # Validate JSON safety
        validate_json_safe_string(v, "authorization_code")

        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Enhanced OAuth state validation."""
        v = v.strip()
        if not v:
            raise ValueError("OAuth state cannot be empty")

        # Check for SQL injection patterns
        check_sql_injection_patterns(v, "oauth_state")

        # Validate JSON safety
        validate_json_safe_string(v, "oauth_state")

        return v

    @model_validator(mode="after")
    def validate_code_or_error(self) -> Any:
        """Ensure either code or error is provided."""
        if not self.code and not self.error:
            raise ValueError("Either 'code' or 'error' must be provided")
        return self


class OAuthCallbackResponse(BaseModel):
    """Response model for OAuth callback completion."""

    success: bool = Field(..., description="Whether OAuth flow completed successfully")
    integration_id: Optional[int] = Field(
        None, description="Created/updated integration ID"
    )
    provider: IntegrationProvider = Field(..., description="OAuth provider")
    status: IntegrationStatus = Field(..., description="Integration status")
    scopes: List[str] = Field(default_factory=list, description="Granted scopes")
    external_user_info: Optional[ExternalUserInfo] = Field(
        None, description="User info from external provider"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class IntegrationUpdateRequest(BaseModel):
    """Request model for updating integration settings."""

    scopes: Optional[List[str]] = Field(
        None, description="Update requested scopes (triggers re-authorization)"
    )
    enabled: Optional[bool] = Field(None, description="Enable/disable integration")

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate OAuth scopes."""
        if v is not None:
            v = list(set(scope.strip() for scope in v if scope.strip()))
            if not v:
                return None
        return v


class TokenRefreshRequest(BaseModel):
    """Request model for manual token refresh."""

    force: bool = Field(
        default=False, description="Force refresh even if token is not near expiration"
    )


class TokenRefreshResponse(BaseModel):
    """Response model for token refresh operation."""

    success: bool = Field(..., description="Whether token refresh succeeded")
    integration_id: Optional[int] = Field(None, description="Integration ID")
    provider: IntegrationProvider = Field(..., description="OAuth provider")
    token_expires_at: Optional[datetime] = Field(
        None, description="New token expiration time"
    )
    refreshed_at: Optional[datetime] = Field(
        None, description="Refresh completion time"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class IntegrationHealthResponse(BaseModel):
    """Response model for integration health check."""

    integration_id: int = Field(..., description="Integration ID")
    provider: IntegrationProvider = Field(..., description="OAuth provider")
    status: IntegrationStatus = Field(..., description="Integration status")
    healthy: bool = Field(..., description="Whether integration is healthy")
    last_check_at: datetime = Field(..., description="Last health check time")
    issues: List[str] = Field(default_factory=list, description="List of health issues")
    recommendations: List[str] = Field(
        default_factory=list, description="Recommended actions"
    )


class IntegrationErrorSummary(BaseModel):
    """Model for integration error summary."""

    integration_id: int
    provider: str
    error_type: str
    error_message: str
    occurred_at: datetime
    retry_count: int = 0


class SyncStats(BaseModel):
    """Model for synchronization statistics."""

    total_syncs: int = 0
    successful_syncs: int = 0
    failed_syncs: int = 0
    last_successful_sync: Optional[datetime] = None
    last_failed_sync: Optional[datetime] = None
    average_sync_duration: Optional[float] = None  # seconds
    sync_errors_by_type: Dict[str, int] = Field(default_factory=dict)


class IntegrationStatsResponse(BaseModel):
    """Response model for integration statistics."""

    total_integrations: int = Field(..., description="Total integrations")
    active_integrations: int = Field(..., description="Active integrations")
    failed_integrations: int = Field(..., description="Failed integrations")
    pending_integrations: int = Field(..., description="Pending integrations")

    by_provider: Dict[str, int] = Field(
        default_factory=dict, description="Integration counts by provider"
    )
    by_status: Dict[str, int] = Field(
        default_factory=dict, description="Integration counts by status"
    )

    recent_errors: List[IntegrationErrorSummary] = Field(
        default_factory=list, description="Recent integration errors"
    )

    sync_stats: SyncStats = Field(
        default_factory=SyncStats, description="Synchronization statistics"
    )


class IntegrationDisconnectRequest(BaseModel):
    """Request model for disconnecting integration."""

    revoke_tokens: bool = Field(
        default=True, description="Whether to revoke tokens with provider"
    )
    delete_data: bool = Field(
        default=False, description="Whether to delete associated user data"
    )


class IntegrationDisconnectResponse(BaseModel):
    """Response model for integration disconnection."""

    success: bool = Field(..., description="Whether disconnection succeeded")
    integration_id: int = Field(..., description="Integration ID")
    provider: IntegrationProvider = Field(..., description="OAuth provider")
    tokens_revoked: bool = Field(..., description="Whether tokens were revoked")
    data_deleted: bool = Field(..., description="Whether associated data was deleted")
    disconnected_at: datetime = Field(..., description="Disconnection time")
    error: Optional[str] = Field(None, description="Error message if failed")


class ProviderListResponse(BaseModel):
    """Response model for listing available OAuth providers."""

    providers: List[IntegrationProviderInfo] = Field(
        default_factory=list, description="Available OAuth providers"
    )
    total: int = Field(..., description="Total number of providers")
    available_count: int = Field(..., description="Number of available providers")


class IntegrationSyncRequest(BaseModel):
    """Request model for triggering integration sync."""

    force: bool = Field(default=False, description="Force sync even if recently synced")
    sync_type: Optional[str] = Field(
        None, description="Type of sync to perform (provider-specific)"
    )


class IntegrationSyncResponse(BaseModel):
    """Response model for integration sync operation."""

    success: bool = Field(..., description="Whether sync completed successfully")
    integration_id: int = Field(..., description="Integration ID")
    provider: IntegrationProvider = Field(..., description="OAuth provider")
    sync_started_at: datetime = Field(..., description="Sync start time")
    sync_completed_at: Optional[datetime] = Field(
        None, description="Sync completion time"
    )
    items_synced: int = Field(default=0, description="Number of items synced")
    errors: List[str] = Field(default_factory=list, description="Sync errors if any")


# Error response schemas
class ErrorDetail(BaseModel):
    """Model for detailed error information."""

    field: Optional[str] = None
    value: Optional[str] = None
    constraint: Optional[str] = None
    code: Optional[str] = None
    context: Optional[Dict[str, str]] = None


class IntegrationErrorResponse(BaseModel):
    """Error response for integration operations."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[List[ErrorDetail]] = Field(
        None, description="Additional error details"
    )
    provider: Optional[IntegrationProvider] = Field(
        None, description="Related provider"
    )
    integration_id: Optional[int] = Field(None, description="Related integration ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Error timestamp",
    )

    model_config = ConfigDict(use_enum_values=True)


# Validation schemas
class ScopeValidationRequest(BaseModel):
    """Request model for validating OAuth scopes."""

    provider: IntegrationProvider = Field(..., description="OAuth provider")
    scopes: List[str] = Field(..., description="Scopes to validate")


class ScopeValidationResponse(BaseModel):
    """Response model for OAuth scope validation."""

    provider: IntegrationProvider = Field(..., description="OAuth provider")
    requested_scopes: List[str] = Field(..., description="Requested scopes")
    valid_scopes: List[str] = Field(..., description="Valid scopes for provider")
    invalid_scopes: List[str] = Field(
        default_factory=list, description="Invalid scopes"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Scope validation warnings"
    )


# Internal API schemas for service-to-service communication
class InternalTokenRequest(BaseModel):
    """Request model for internal token retrieval."""

    user_id: str = Field(..., description="User ID to retrieve tokens for")
    provider: IntegrationProvider = Field(..., description="OAuth provider")
    required_scopes: List[str] = Field(
        default_factory=list, description="Required OAuth scopes"
    )
    refresh_if_needed: bool = Field(
        default=True, description="Automatically refresh if token is near expiration"
    )


class InternalTokenResponse(BaseModel):
    """Response model for internal token retrieval."""

    success: bool = Field(..., description="Whether token retrieval succeeded")
    access_token: Optional[str] = Field(None, description="OAuth access token")
    refresh_token: Optional[str] = Field(None, description="OAuth refresh token")
    expires_at: Optional[datetime] = Field(None, description="Token expiration time")
    scopes: List[str] = Field(default_factory=list, description="Granted scopes")
    provider: IntegrationProvider = Field(..., description="OAuth provider")
    user_id: str = Field(..., description="User ID")
    integration_id: Optional[int] = Field(None, description="Integration ID")
    token_type: str = Field(default="Bearer", description="Token type")
    error: Optional[str] = Field(None, description="Error message if failed")


class InternalTokenRefreshRequest(BaseModel):
    """Request model for internal token refresh."""

    user_id: str = Field(..., description="User ID to refresh tokens for")
    provider: IntegrationProvider = Field(..., description="OAuth provider")
    force: bool = Field(
        default=False, description="Force refresh even if not near expiration"
    )


class InternalUserStatusResponse(BaseModel):
    """Response model for internal user status retrieval."""

    user_id: str = Field(..., description="User ID")
    active_integrations: int = Field(..., description="Number of active integrations")
    total_integrations: int = Field(..., description="Total number of integrations")
    providers: List[IntegrationProvider] = Field(
        default_factory=list, description="Available providers"
    )
    has_errors: bool = Field(..., description="Whether any integrations have errors")
    last_sync_at: Optional[datetime] = Field(
        None, description="Last successful sync across all integrations"
    )


class ProviderRevocationResponse(BaseModel):
    """Model for provider token revocation response."""

    success: bool
    message: Optional[str] = None
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    timestamp: Optional[datetime] = None


class TokenRevocationResponse(BaseModel):
    """Response model for token revocation requests."""

    success: bool = Field(..., description="Whether token revocation succeeded")
    provider: IntegrationProvider = Field(..., description="OAuth provider")
    user_id: str = Field(..., description="User ID")
    integration_id: Optional[int] = Field(None, description="Integration ID")
    revoked_at: Optional[datetime] = Field(None, description="Revocation timestamp")
    reason: Optional[str] = Field(None, description="Reason for revocation")
    error: Optional[str] = Field(None, description="Error message if failed")
    provider_response: Optional[ProviderRevocationResponse] = Field(
        None, description="Provider revocation response"
    )
