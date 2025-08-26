"""
Pydantic schemas package for User Management Service.

Exports all schema models for API request/response validation.
"""

from services.api.v1.user.integration import (
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
from services.api.v1.user.user import (
    UserBase,
    UserCreate,
    UserDeleteResponse,
    UserOnboardingUpdate,
    UserResponse,
    UserUpdate,
)
from services.api.v1.user.requests import (
    UserSearchRequest,
    UserListRequest,
)
from services.api.v1.user.preferences import (
    TimezonePreference,
    TimezonePreferenceCreate,
    TimezonePreferenceResponse,
    TimezonePreferenceUpdate,
)
from services.api.v1.user.health import (
    HealthResponse,
)

__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserDeleteResponse",
    "UserOnboardingUpdate",
    # Request schemas
    "UserSearchRequest",
    "UserListRequest",
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
    # Preference schemas
    "TimezonePreference",
    "TimezonePreferenceCreate",
    "TimezonePreferenceResponse",
    "TimezonePreferenceUpdate",
    # Health schemas
    "HealthResponse",
]
