"""
Pydantic schemas for integration management.

Defines request and response models for OAuth integration endpoints,
including integration status, token management, and provider-specific data.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class IntegrationProvider(str, Enum):
    """Supported OAuth integration providers."""

    GOOGLE = "google"
    MICROSOFT = "microsoft"
    SLACK = "slack"


class IntegrationStatus(str, Enum):
    """Integration connection status."""

    ACTIVE = "ACTIVE"  # Connected and working
    INACTIVE = "INACTIVE"  # Disconnected by user
    ERROR = "ERROR"  # Connection error or expired tokens
    PENDING = "PENDING"  # OAuth flow in progress
    EXPIRED = "EXPIRED"  # Token was valid but is now expired


def validate_oauth_scopes(scopes: List[str]) -> List[str]:
    """Validate OAuth scopes.
    
    Args:
        scopes: List of scope strings to validate
        
    Returns:
        List of validated and cleaned scope strings
        
    Raises:
        ValueError: If scopes validation fails
    """
    if not scopes:
        raise ValueError("At least one scope must be requested")
    
    # Basic scope validation
    for scope in scopes:
        if not scope or not scope.strip():
            raise ValueError("Scope cannot be empty")
        if len(scope) > 100:
            raise ValueError("Scope must be 100 characters or less")
    
    return [scope.strip() for scope in scopes]


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
    total_count: int = Field(..., description="Total number of integrations")
    active_count: int = Field(..., description="Number of active integrations")
    error_count: int = Field(..., description="Number of integrations with errors")


class IntegrationCreateRequest(BaseModel):
    """Request model for creating a new integration."""

    provider: IntegrationProvider = Field(..., description="OAuth provider")
    scopes: List[str] = Field(default_factory=list, description="Requested OAuth scopes")
    redirect_uri: str = Field(..., description="OAuth redirect URI")

    @field_validator("redirect_uri")
    @classmethod
    def validate_redirect_uri(cls: type["IntegrationCreateRequest"], v: str) -> str:
        """Validate redirect URI format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Redirect URI must be a valid HTTP/HTTPS URL")
        return v

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls: type["IntegrationCreateRequest"], v: List[str]) -> List[str]:
        """Validate OAuth scopes."""
        return validate_oauth_scopes(v)


class IntegrationUpdateRequest(BaseModel):
    """Request model for updating an integration."""

    scopes: Optional[List[str]] = Field(None, description="Updated OAuth scopes")
    status: Optional[IntegrationStatus] = Field(None, description="Integration status")

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls: type["IntegrationUpdateRequest"], v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate OAuth scopes."""
        if v is None:
            return v
        return validate_oauth_scopes(v)


class IntegrationDeleteRequest(BaseModel):
    """Request model for deleting an integration."""

    force: bool = Field(
        default=False, description="Force deletion even if integration is active"
    )


class IntegrationDeleteResponse(BaseModel):
    """Response model for integration deletion."""

    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Deletion status message")
    integration_id: int = Field(..., description="ID of deleted integration")
    deleted_at: datetime = Field(..., description="Deletion timestamp")


class IntegrationSyncRequest(BaseModel):
    """Request model for triggering integration sync."""

    force: bool = Field(
        default=False, description="Force sync even if recently synced"
    )
    scopes: Optional[List[str]] = Field(
        None, description="Specific scopes to sync"
    )


class IntegrationSyncResponse(BaseModel):
    """Response model for integration sync."""

    success: bool = Field(..., description="Whether sync was successful")
    message: str = Field(..., description="Sync status message")
    synced_at: datetime = Field(..., description="Sync timestamp")
    items_synced: int = Field(..., description="Number of items synced")
    errors: List[str] = Field(default_factory=list, description="Any sync errors")


class IntegrationHealthCheck(BaseModel):
    """Response model for integration health check."""

    provider: IntegrationProvider = Field(..., description="OAuth provider")
    status: IntegrationStatus = Field(..., description="Current integration status")
    last_sync: Optional[datetime] = Field(None, description="Last successful sync")
    token_expires_in: Optional[int] = Field(
        None, description="Seconds until token expires"
    )
    error_count: int = Field(..., description="Consecutive error count")
    is_healthy: bool = Field(..., description="Overall health status")


class IntegrationHealthSummary(BaseModel):
    """Summary of all integration health statuses."""

    total_integrations: int = Field(..., description="Total number of integrations")
    healthy_integrations: int = Field(..., description="Number of healthy integrations")
    unhealthy_integrations: int = Field(..., description="Number of unhealthy integrations")
    integrations: List[IntegrationHealthCheck] = Field(
        ..., description="Health status for each integration"
    )
    overall_health: str = Field(..., description="Overall system health status")
