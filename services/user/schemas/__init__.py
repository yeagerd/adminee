"""
Pydantic schemas package for User Management Service.

Exports all schema models for API request/response validation.
"""

from services.user.schemas.integration import (
    IntegrationDisconnectRequest,
    IntegrationDisconnectResponse,
    IntegrationErrorResponse,
    IntegrationHealthResponse,
    IntegrationListResponse,
    IntegrationProviderInfo,
    IntegrationResponse,
    IntegrationScopeResponse,
    IntegrationStatsResponse,
    IntegrationSyncRequest,
    IntegrationSyncResponse,
    IntegrationUpdateRequest,
    InternalTokenRefreshRequest,
    InternalTokenRequest,
    InternalTokenResponse,
    InternalUserStatusResponse,
    OAuthCallbackRequest,
    OAuthCallbackResponse,
    OAuthStartRequest,
    OAuthStartResponse,
    ProviderListResponse,
    ScopeValidationRequest,
    ScopeValidationResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
)
from services.user.schemas.user import (
    UserBase,
    UserCreate,
    UserDeleteResponse,
    UserOnboardingUpdate,
    UserResponse,
    UserUpdate,
)
from services.user.schemas.pagination import (
    UserListResponse,
    UserSearchRequest,
)

__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
    "UserDeleteResponse",
    "UserOnboardingUpdate",
    "UserSearchRequest",
    # Integration schemas
    "IntegrationResponse",
    "IntegrationListResponse",
    "IntegrationProviderInfo",
    "IntegrationScopeResponse",
    "IntegrationStatsResponse",
    "IntegrationHealthResponse",
    "IntegrationUpdateRequest",
    "IntegrationDisconnectRequest",
    "IntegrationDisconnectResponse",
    "IntegrationSyncRequest",
    "IntegrationSyncResponse",
    "IntegrationErrorResponse",
    "InternalTokenRequest",
    "InternalTokenResponse",
    "InternalTokenRefreshRequest",
    "InternalUserStatusResponse",
    "OAuthStartRequest",
    "OAuthStartResponse",
    "OAuthCallbackRequest",
    "OAuthCallbackResponse",
    "TokenRefreshRequest",
    "TokenRefreshResponse",
    "ProviderListResponse",
    "ScopeValidationRequest",
    "ScopeValidationResponse",
]
