"""
Internal service-to-service API router.

Provides secure endpoints for other services to retrieve user tokens
and integration status with service authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from services.user.auth.service_auth import get_current_service
from services.user.exceptions import IntegrationException, NotFoundException
from services.user.schemas.integration import (
    InternalTokenRefreshRequest,
    InternalTokenRequest,
    InternalTokenResponse,
    InternalUserStatusResponse,
)
from services.user.services.token_service import get_token_service

router = APIRouter(
    prefix="/internal",
    tags=["Internal"],
    responses={401: {"description": "Service authentication required"}},
)


@router.post("/tokens/get", response_model=InternalTokenResponse)
async def get_user_tokens(
    request: InternalTokenRequest,
    current_service: str = Depends(get_current_service),
):
    """
    Get user tokens for other services.

    Retrieves valid OAuth tokens for a user and provider with automatic
    refresh, scope validation, and comprehensive error handling.

    **Authentication:**
    - Requires service-to-service API key authentication
    - Only authorized services can retrieve user tokens

    **Request Body:**
    - `user_id`: User identifier
    - `provider`: OAuth provider (google, microsoft, etc.)
    - `required_scopes`: Required OAuth scopes (optional)
    - `refresh_if_needed`: Auto-refresh if token near expiration (default: true)

    **Response:**
    - `success`: Whether token retrieval succeeded
    - `access_token`: OAuth access token (if successful)
    - `refresh_token`: OAuth refresh token (if available)
    - `expires_at`: Token expiration time
    - `scopes`: Granted OAuth scopes
    - `error`: Error message (if failed)

    **Security Features:**
    - Encrypted token storage with user-specific keys
    - Automatic token refresh with 5-minute buffer
    - Scope validation and error reporting
    - Comprehensive audit logging
    """
    try:
        return await get_token_service().get_valid_token(
            user_id=request.user_id,
            provider=request.provider,
            required_scopes=request.required_scopes,
            refresh_if_needed=request.refresh_if_needed,
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IntegrationException as e:
        # Return error in response rather than raising HTTP exception
        return InternalTokenResponse(
            success=False,
            provider=request.provider,
            user_id=request.user_id,
            error=str(e),
        )


@router.post("/tokens/refresh", response_model=InternalTokenResponse)
async def refresh_user_tokens(
    request: InternalTokenRefreshRequest,
    current_service: str = Depends(get_current_service),
):
    """
    Refresh user tokens for other services.

    Manually refresh OAuth access tokens using stored refresh tokens.
    Useful for recovering from token expiration or API errors.

    **Authentication:**
    - Requires service-to-service API key authentication
    - Only authorized services can refresh user tokens

    **Request Body:**
    - `user_id`: User identifier
    - `provider`: OAuth provider (google, microsoft, etc.)
    - `force`: Force refresh even if not near expiration (default: false)

    **Response:**
    - `success`: Whether token refresh succeeded
    - `access_token`: New OAuth access token (if successful)
    - `refresh_token`: Refresh token (if available)
    - `expires_at`: New token expiration time
    - `error`: Error message (if failed)

    **Features:**
    - Uses stored refresh tokens for token exchange
    - Updates token records with new expiration times
    - Comprehensive error handling and logging
    - Returns updated token information
    """
    try:
        return await get_token_service().refresh_tokens(
            user_id=request.user_id,
            provider=request.provider,
            force=request.force,
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IntegrationException as e:
        # Return error in response rather than raising HTTP exception
        return InternalTokenResponse(
            success=False,
            provider=request.provider,
            user_id=request.user_id,
            error=str(e),
        )


@router.get("/users/{user_id}/status", response_model=InternalUserStatusResponse)
async def get_user_status(
    user_id: str,
    current_service: str = Depends(get_current_service),
):
    """
    Get user integration status for other services.

    Provides comprehensive integration status information including
    active integrations, error states, and provider availability.

    **Authentication:**
    - Requires service-to-service API key authentication
    - Only authorized services can retrieve user status

    **Path Parameters:**
    - `user_id`: User identifier

    **Response:**
    - `user_id`: User identifier
    - `active_integrations`: Number of active integrations
    - `total_integrations`: Total number of integrations
    - `providers`: List of available providers
    - `has_errors`: Whether any integrations have errors
    - `last_sync_at`: Last successful sync time

    **Use Cases:**
    - Check user integration health before making API calls
    - Determine available OAuth providers for a user
    - Monitor integration error states
    - Track sync activity across services
    """
    try:
        return await get_token_service().get_user_status(user_id=user_id)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IntegrationException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/users/{user_id}/preferences")
async def get_user_preferences_internal(
    user_id: str,
    current_service: str = Depends(get_current_service),
):
    """
    Get user preferences for other services.

    Internal service endpoint to retrieve user preferences with service authentication.
    Used by chat service and other internal services to get user timezone and settings.

    **Authentication:**
    - Requires service-to-service API key authentication
    - Only authorized services can retrieve user preferences

    **Path Parameters:**
    - `user_id`: User identifier (external auth ID)

    **Response:**
    - User preferences object or null if not found
    - Returns 404 if user not found (normal for new users)

    **Use Cases:**
    - Chat service getting user timezone for scheduling
    - Office service getting user notification preferences
    - Any service needing user settings for personalization
    """
    try:
        from services.user.services.preferences_service import get_preferences_service

        preferences = await get_preferences_service().get_user_preferences(user_id)
        return preferences
    except Exception:
        # Return null for missing preferences (normal for new users)
        return None


@router.get("/users/{user_id}/integrations")
async def get_user_integrations_internal(
    user_id: str,
    current_service: str = Depends(get_current_service),
):
    """
    Get user integrations for other services.

    Internal service endpoint to retrieve user integrations with service authentication.
    Used by chat service and other internal services to determine available providers.

    **Authentication:**
    - Requires service-to-service API key authentication
    - Only authorized services can retrieve user integrations

    **Path Parameters:**
    - `user_id`: User identifier (external auth ID)

    **Response:**
    - List of user integrations with status and provider information
    - Returns empty list if user not found or no integrations

    **Use Cases:**
    - Chat service determining available calendar providers
    - Office service checking user's connected accounts
    - Any service needing to know user's OAuth connections
    """
    try:
        from services.user.services.integration_service import get_integration_service

        integrations_response = await get_integration_service().get_user_integrations(
            user_id=user_id,
            include_token_info=False,  # Don't include sensitive token info for internal calls
        )

        # Return simplified integration data for internal services
        integrations = []
        for integration in integrations_response.integrations:
            integrations.append(
                {
                    "id": integration.id,
                    "provider": integration.provider.value,
                    "status": integration.status.value,
                    "external_user_id": integration.external_user_id,
                    "external_email": integration.external_email,
                    "scopes": integration.scopes,
                    "last_sync_at": (
                        integration.last_sync_at.isoformat()
                        if integration.last_sync_at
                        else None
                    ),
                    "error_message": integration.last_error,
                    "created_at": integration.created_at.isoformat(),
                    "updated_at": integration.updated_at.isoformat(),
                }
            )

        return {
            "integrations": integrations,
            "total": integrations_response.total,
            "active_count": integrations_response.active_count,
            "error_count": integrations_response.error_count,
        }
    except Exception:
        # Return empty list for errors (don't break other services)
        return {"integrations": [], "total": 0, "active_count": 0, "error_count": 0}
