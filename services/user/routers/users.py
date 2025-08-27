"""
User profile management router for User Management Service.

Implements CRUD operations for user profiles with authentication,
authorization, and comprehensive error handling.

# Endpoint Pattern Note:
# - User-facing endpoints use /me and extract user from JWT/session (requires user authentication)
# - Internal/service endpoints use /internal and require API key/service authentication
# - /users/{user_id} endpoints are deprecated and removed; use /me instead
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Path, Query

from services.api.v1.user.integration import (
    IntegrationDisconnectRequest,
    IntegrationDisconnectResponse,
    IntegrationHealthResponse,
    IntegrationListResponse,
    IntegrationResponse,
    OAuthCallbackRequest,
    OAuthCallbackResponse,
    OAuthStartRequest,
    OAuthStartResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
)
from services.api.v1.user.requests import UserFilterRequest
from services.api.v1.user.user import (
    UserCreate,
    UserResponse,
)
from services.common.http_errors import (
    BrieflyAPIError,
    ErrorCode,
    NotFoundError,
    ServiceError,
    ValidationError,
)
from services.common.logging_config import get_logger
from services.common.pagination.schemas import CursorPaginationResponse
from services.user.auth import get_current_user
from services.user.auth.service_auth import service_permission_required
from services.user.models.integration import IntegrationProvider, IntegrationStatus
from services.user.services.audit_service import audit_logger
from services.user.services.user_service import get_user_service

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Get the profile of the currently authenticated user.",
    responses={
        200: {"description": "Current user profile retrieved successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "User not found"},
    },
)
async def get_current_user_profile(
    current_user_external_auth_id: str = Depends(get_current_user),
) -> UserResponse:
    """
    Get current user's profile.

    Convenience endpoint to get the authenticated user's profile
    without needing to know their database ID.
    """
    try:
        current_user = (
            await get_user_service().get_user_by_external_auth_id_auto_detect(
                current_user_external_auth_id
            )
        )
        user_response = UserResponse.from_orm(current_user)

        logger.info(
            f"Retrieved current user profile for {current_user_external_auth_id}"
        )
        return user_response

    except NotFoundError as e:
        logger.warning(f"Current user not found: {e.message}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error retrieving current user profile: {e}")
        raise ServiceError(message="Failed to retrieve current user profile")


@router.get(
    "/me/integrations",
    response_model=IntegrationListResponse,
    summary="Get current user integrations",
    description="Get all integrations for the currently authenticated user.",
    responses={
        200: {"description": "Current user integrations retrieved successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "User not found"},
    },
)
async def get_current_user_integrations(
    provider: Optional[IntegrationProvider] = Query(
        None, description="Filter by provider"
    ),
    integration_status: Optional[IntegrationStatus] = Query(
        None, description="Filter by status", alias="status"
    ),
    include_token_info: bool = Query(True, description="Include token metadata"),
    current_user_external_auth_id: str = Depends(get_current_user),
) -> IntegrationListResponse:
    """
    Get current user's integrations.

    Convenience endpoint to get the authenticated user's integrations
    without needing to know their database ID.
    """
    try:
        from services.user.services.integration_service import get_integration_service

        integrations_response = await get_integration_service().get_user_integrations(
            user_id=current_user_external_auth_id,
            provider=provider,
            status=integration_status,
            include_token_info=include_token_info,
        )

        logger.info(
            f"Retrieved current user integrations for {current_user_external_auth_id}"
        )
        return integrations_response

    except NotFoundError as e:
        logger.warning(f"Current user not found: {e.message}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error retrieving current user integrations: {e}")
        raise ServiceError(message="Failed to retrieve current user integrations")


@router.delete(
    "/me/integrations/{provider}",
    response_model=IntegrationDisconnectResponse,
    summary="Disconnect current user integration",
    description="Disconnect an OAuth integration for the currently authenticated user.",
    responses={
        200: {"description": "Integration disconnected successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Integration not found"},
        422: {"description": "Validation error"},
    },
)
async def disconnect_current_user_integration(
    provider: IntegrationProvider = Path(..., description="OAuth provider"),
    request: IntegrationDisconnectRequest | None = None,
    current_user_external_auth_id: str = Depends(get_current_user),
) -> IntegrationDisconnectResponse:
    """
    Disconnect an OAuth integration for the current user.

    Convenience endpoint to disconnect the authenticated user's integration
    without needing to know their database ID.
    """
    try:
        from services.user.services.integration_service import get_integration_service

        if request is None:
            request = IntegrationDisconnectRequest()

        result = await get_integration_service().disconnect_integration(
            user_id=current_user_external_auth_id,
            provider=provider,
            revoke_tokens=request.revoke_tokens,
            delete_data=request.delete_data,
        )

        logger.info(
            f"Disconnected {provider.value} integration for user {current_user_external_auth_id}"
        )
        return IntegrationDisconnectResponse(**result)

    except NotFoundError as e:
        logger.warning(f"Integration not found: {e.message}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error disconnecting integration: {e}")
        raise ServiceError(message="Failed to disconnect integration")


@router.put(
    "/me/integrations/{provider}/refresh",
    response_model=TokenRefreshResponse,
    summary="Refresh current user integration tokens",
    description="Refresh access tokens for an integration of the currently authenticated user.",
    responses={
        200: {"description": "Tokens refreshed successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Integration not found"},
        422: {"description": "Validation error"},
    },
)
async def refresh_current_user_integration_tokens(
    provider: IntegrationProvider = Path(..., description="OAuth provider"),
    request: TokenRefreshRequest | None = None,
    current_user_external_auth_id: str = Depends(get_current_user),
) -> TokenRefreshResponse:
    """
    Refresh access tokens for the current user's integration.

    Convenience endpoint to refresh the authenticated user's integration tokens
    without needing to know their database ID.
    """
    try:
        from services.user.services.integration_service import get_integration_service

        if request is None:
            request = TokenRefreshRequest()  # type: ignore[assignment]

        result = await get_integration_service().refresh_integration_tokens(
            user_id=current_user_external_auth_id,
            provider=provider,
            force=request.force,
        )

        logger.info(
            f"Refreshed tokens for {provider.value} integration for user {current_user_external_auth_id}"
        )
        return result
    except NotFoundError as e:
        logger.warning(f"Integration not found: {e.message}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error refreshing tokens: {e}")
        # Return a failed TokenRefreshResponse instead of raising HTTP error
        return TokenRefreshResponse(
            success=False,
            integration_id=None,
            provider=provider,
            token_expires_at=None,
            refreshed_at=datetime.now(timezone.utc),
            error=str(e),
        )


@router.get(
    "/me/integrations/{provider}",
    response_model=IntegrationResponse,
    summary="Get current user specific integration",
    description="Get details for a specific integration of the currently authenticated user.",
    responses={
        200: {"description": "Integration details retrieved successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Integration not found"},
    },
)
async def get_current_user_specific_integration(
    provider: IntegrationProvider = Path(..., description="OAuth provider"),
    current_user_external_auth_id: str = Depends(get_current_user),
) -> IntegrationResponse:
    """
    Get details for a specific integration of the current user.

    Convenience endpoint to get the authenticated user's specific integration
    without needing to know their database ID.
    """
    try:
        from services.user.services.integration_service import get_integration_service

        # Get all integrations and filter for the specific provider
        integrations_response = await get_integration_service().get_user_integrations(
            user_id=current_user_external_auth_id,
            provider=provider,
            include_token_info=True,
        )

        if not integrations_response.integrations:
            raise NotFoundError("Integration", identifier=f"provider: {provider.value}")

        logger.info(
            f"Retrieved {provider.value} integration for user {current_user_external_auth_id}"
        )
        # Return the first (and should be only) integration for this provider
        return integrations_response.integrations[0]

    except NotFoundError as e:
        logger.warning(f"Integration not found: {e.message}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error retrieving integration: {e}")
        raise ServiceError(message="Failed to retrieve integration")


@router.get(
    "/me/integrations/{provider}/health",
    response_model=IntegrationHealthResponse,
    summary="Check current user integration health",
    description="Check the health status of an integration for the currently authenticated user.",
    responses={
        200: {"description": "Health check completed successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Integration not found"},
    },
)
async def check_current_user_integration_health(
    provider: IntegrationProvider = Path(..., description="OAuth provider"),
    current_user_external_auth_id: str = Depends(get_current_user),
) -> IntegrationHealthResponse:
    """
    Check the health status of the current user's integration.

    Convenience endpoint to check the authenticated user's integration health
    without needing to know their database ID.
    """
    try:
        from services.user.services.integration_service import get_integration_service

        result = await get_integration_service().check_integration_health(
            user_id=current_user_external_auth_id,
            provider=provider,
        )

        logger.info(
            f"Checked health for {provider.value} integration for user {current_user_external_auth_id}"
        )
        return result
    except NotFoundError as e:
        logger.warning(f"Integration not found: {e.message}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error checking integration health: {e}")
        raise ServiceError(message="Failed to check integration health")


@router.get(
    "/me/integrations/{provider}/scopes",
    summary="Get available OAuth scopes for provider",
    description="Get the list of available OAuth scopes for a specific provider.",
    responses={
        200: {"description": "Scopes retrieved successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Provider not found"},
    },
)
async def get_provider_scopes(
    provider: IntegrationProvider = Path(..., description="OAuth provider"),
    current_user_external_auth_id: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get available OAuth scopes for a provider.

    Returns the list of available scopes with their descriptions,
    required status, and sensitivity level.
    """
    try:
        from services.user.integrations.oauth_config import get_oauth_config

        oauth_config = get_oauth_config()
        provider_config = oauth_config.get_provider_config(provider)

        if not provider_config:
            raise NotFoundError("Provider", identifier=f"provider: {provider.value}")

        scopes = []
        for scope in provider_config.scopes:
            scopes.append(
                {
                    "name": scope.name,
                    "description": scope.description,
                    "required": scope.required,
                    "sensitive": scope.sensitive,
                }
            )

        return {
            "provider": provider.value,
            "scopes": scopes,
            "default_scopes": provider_config.default_scopes,
        }

    except NotFoundError as e:
        logger.warning(f"Provider not found: {e.message}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error retrieving scopes: {e}")
        raise ServiceError(message="Failed to retrieve scopes")


@router.get(
    "/search",
    response_model=CursorPaginationResponse,
    summary="Search users",
    description="Search users with cursor-based pagination. For admin/service use.",
    responses={
        200: {"description": "User search results retrieved successfully"},
        401: {"description": "Authentication required"},
        422: {"description": "Validation error in search parameters"},
        400: {"description": "Invalid cursor token"},
    },
)
async def search_users(
    cursor: Optional[str] = Query(None, description="Cursor token for pagination"),
    limit: Optional[int] = Query(
        None, ge=1, le=100, description="Number of users per page"
    ),
    direction: Optional[str] = Query(
        "next", pattern="^(next|prev)$", description="Pagination direction"
    ),
    query: Optional[str] = Query(None, max_length=255, description="Search query"),
    email: Optional[str] = Query(None, description="Filter by email"),
    onboarding_completed: Optional[bool] = Query(
        None, description="Filter by onboarding status"
    ),
    current_user_id: str = Depends(get_current_user),
) -> CursorPaginationResponse:
    """
    Search users with cursor-based pagination.

    This endpoint uses cursor-based pagination instead of offset-based pagination
    for better performance and consistency with concurrent updates.

    This endpoint is primarily for administrative or service use.
    Regular users should use other endpoints for their own data.
    """
    try:
        search_request = UserFilterRequest(
            cursor=cursor,
            limit=limit,
            direction=direction,
            query=query,
            email=email,
            onboarding_completed=onboarding_completed,
        )

        search_results = await get_user_service().search_users(search_request)

        logger.info(
            f"User search performed by {current_user_id}, found {len(search_results.items)} results"
        )
        return search_results

    except Exception as e:
        logger.error(f"Unexpected error in user search: {e}")
        raise ServiceError(message="Failed to search users")


@router.post(
    "/",
    response_model=UserResponse,
    status_code=201,
    summary="Create or upsert user (OAuth/NextAuth)",
    description="Create a new user or return existing user by external_auth_id and auth_provider. Protected endpoint for OAuth/NextAuth flows with service authentication.",
    responses={
        200: {"description": "User already exists, returned successfully"},
        201: {"description": "User created successfully"},
        401: {"description": "Service authentication required"},
        409: {"description": "Email collision detected"},
        422: {"description": "Validation error in request data"},
    },
)
async def create_or_upsert_user(
    user_data: UserCreate,
    service_name: str = Depends(service_permission_required(["write_users"])),
) -> UserResponse:
    """
    Create a new user or return existing user by external_auth_id and auth_provider.

    This is a protected endpoint designed for OAuth/NextAuth flows where
    we want to create users if they don't exist, or return existing
    users if they do. Requires service authentication (API key).

    **Authentication:**
    - Requires service-to-service API key authentication
    - Only authorized services (frontend, chat, office) can create users
    """
    # Add detailed logging for debugging
    logger.info(f"User creation request from service: {service_name}")
    logger.info(
        f"User data received: external_auth_id={user_data.external_auth_id}, "
        f"auth_provider={user_data.auth_provider}, email={user_data.email}, "
        f"first_name={user_data.first_name}, last_name={user_data.last_name}, "
        f"profile_image_url={user_data.profile_image_url}"
    )

    try:
        # Try to find existing user first
        existing_user = (
            await get_user_service().get_user_by_external_auth_id_auto_detect(
                user_data.external_auth_id
            )
        )
        user_response = UserResponse.from_orm(existing_user)

        logger.info(
            f"Found existing user for {user_data.auth_provider} ID: {user_data.external_auth_id}"
        )
        return user_response

    except NotFoundError:
        # User doesn't exist, create new one
        logger.info(
            f"User not found, attempting to create new user with {user_data.auth_provider} ID: {user_data.external_auth_id}"
        )
        try:
            new_user = await get_user_service().create_user(user_data)
            user_response = UserResponse.from_orm(new_user)

            logger.info(
                f"Created new user with {user_data.auth_provider} ID: {user_data.external_auth_id}"
            )
            return user_response

        except ValidationError as e:
            logger.error(f"Validation error during user creation: {e.message}")
            logger.error(f"Validation error details: {e.details}")
            if "collision" in str(e.message).lower():
                logger.warning(f"Email collision during user creation: {e.message}")
                raise BrieflyAPIError(
                    status_code=409,
                    error_code=ErrorCode.ALREADY_EXISTS,
                    message="Email collision detected",
                    details=e.details,
                )
            else:
                logger.warning(f"Validation error during user creation: {e.message}")
                raise e

    except Exception as e:
        logger.error(f"Unexpected error in create_or_upsert_user: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {str(e)}")
        raise ServiceError(message="Failed to create or retrieve user")


@router.post(
    "/me/integrations/oauth/start",
    response_model=OAuthStartResponse,
    summary="Start OAuth flow for current user",
    description="Start OAuth authorization flow for the currently authenticated user.",
    responses={
        200: {"description": "OAuth flow started successfully"},
        401: {"description": "Authentication required"},
        422: {"description": "Validation error"},
    },
)
async def start_current_user_oauth_flow(
    request: OAuthStartRequest,
    current_user_external_auth_id: str = Depends(get_current_user),
) -> OAuthStartResponse:
    """
    Start OAuth authorization flow for the current user.

    Convenience endpoint to start OAuth flow for the authenticated user
    without needing to know their database ID.
    """
    try:
        from services.user.services.integration_service import get_integration_service

        result = await get_integration_service().start_oauth_flow(
            user_id=current_user_external_auth_id,
            provider=request.provider,
            redirect_uri=request.redirect_uri,
            scopes=request.scopes,
            state_data=request.state_data,
        )

        logger.info(
            f"Started OAuth flow for {request.provider.value} for user {current_user_external_auth_id}"
        )
        return result

    except Exception as e:
        logger.error(f"Unexpected error starting OAuth flow: {e}")
        raise ServiceError(message="Failed to start OAuth flow")


@router.post(
    "/me/integrations/oauth/callback",
    response_model=OAuthCallbackResponse,
    summary="Complete OAuth flow for current user",
    description="Complete OAuth authorization flow for the currently authenticated user.",
    responses={
        200: {"description": "OAuth flow completed successfully"},
        401: {"description": "Authentication required"},
        422: {"description": "Validation error"},
    },
)
async def complete_current_user_oauth_flow(
    request: OAuthCallbackRequest,
    provider: IntegrationProvider = Query(..., description="OAuth provider"),
    current_user_external_auth_id: str = Depends(get_current_user),
) -> OAuthCallbackResponse:
    """
    Complete OAuth authorization flow for the current user.

    Convenience endpoint to complete OAuth flow for the authenticated user
    without needing to know their database ID.
    """
    try:
        from services.user.services.integration_service import get_integration_service

        # Handle OAuth errors from provider
        if request.error:
            await audit_logger.log_security_event(
                user_id=current_user_external_auth_id,
                action="oauth_callback_error",
                severity="medium",
                details={
                    "provider": provider.value,
                    "error": request.error,
                    "error_description": request.error_description,
                },
            )
            return OAuthCallbackResponse(
                success=False,
                integration_id=None,
                provider=provider,
                status=IntegrationStatus.ERROR,
                scopes=[],
                external_user_info=None,
                error=f"OAuth error: {request.error} - {request.error_description}",
            )

        # Complete the OAuth flow
        if request.code is None:
            raise ValidationError(
                message="Authorization code is required", field="code", value=None
            )
        result = await get_integration_service().complete_oauth_flow(
            user_id=current_user_external_auth_id,
            provider=provider,
            authorization_code=request.code,
            state=request.state,
        )

        logger.info(
            f"Completed OAuth flow for {provider.value} for user {current_user_external_auth_id}"
        )
        return result

    except Exception as e:
        logger.error(f"Unexpected error completing OAuth flow: {e}")
        raise ServiceError(message="Failed to complete OAuth flow")
