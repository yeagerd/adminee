"""
User profile management router for User Management Service.

Implements CRUD operations for user profiles with authentication,
authorization, and comprehensive error handling.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from services.common.http_errors import (
    AuthError,
    BrieflyAPIException,
    ErrorCode,
    NotFoundError,
    ServiceError,
    ValidationError,
)
from services.user.auth import get_current_user
from services.user.auth.service_auth import get_current_service
from services.user.models.integration import IntegrationProvider, IntegrationStatus
from services.user.schemas.integration import (
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
from services.user.schemas.user import (
    EmailResolutionRequest,
    UserCreate,
    UserDeleteResponse,
    UserListResponse,
    UserOnboardingUpdate,
    UserResponse,
    UserSearchRequest,
    UserUpdate,
)
from services.user.services.audit_service import audit_logger
from services.user.services.user_service import get_user_service


logger = logging.getLogger(__name__)

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
    "/id",
    response_model=UserResponse,
    summary="Get user by email lookup",
    description="Find a user by exact email address match. Returns 404 if user doesn't exist. Protected endpoint for service-to-service communication.",
    responses={
        200: {"description": "User found"},
        401: {"description": "Service authentication required"},
        404: {"description": "User not found"},
        422: {"description": "Invalid email format or validation error"},
    },
)
async def get_user_by_email(
    email: str = Query(..., description="Email address to lookup"),
    provider: Optional[str] = Query(
        None, description="OAuth provider (google, microsoft, etc.)"
    ),
    current_service: str = Depends(get_current_service),
) -> UserResponse:
    """
    Get user by exact email lookup.

    This endpoint provides a clean RESTful way to find users by email address
    without exposing internal email normalization implementation details.
    Perfect for NextAuth integration where you need to check user existence
    before deciding whether to create a new user.

    **Authentication:**
    - Requires service-to-service API key authentication
    - Only authorized services (frontend, chat, office) can lookup users

    Args:
        email: Email address to lookup
        provider: OAuth provider for context (optional)

    Returns:
        UserResponse if user found

    Raises:
        404: If no user found for the email
        422: If email format is invalid
    """
    try:
        # Create email resolution request (reusing existing internal logic)
        email_request = EmailResolutionRequest(email=email, provider=provider)

        # Use existing resolution service (abstracts normalization)
        resolution_result = await get_user_service().resolve_email_to_user_id(
            email_request
        )

        # Get full user data to return
        user = await get_user_service().get_user_by_external_auth_id_auto_detect(
            resolution_result.external_auth_id
        )

        user_response = UserResponse.from_orm(user)

        logger.info(
            f"Successfully found user for email {email} with provider {provider}: {user.external_auth_id}"
        )
        return user_response

    except NotFoundError as e:
        logger.info(f"User lookup failed - no user found for email {email}")
        raise e
    except ValidationError as e:
        logger.warning(f"User lookup failed - validation error: {e.message}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during user lookup: {e}")
        raise ServiceError(message="Failed to lookup user")


@router.get(
    "/search",
    response_model=UserListResponse,
    summary="Search users",
    description="Search users with filtering and pagination. For admin/service use.",
    responses={
        200: {"description": "User search results retrieved successfully"},
        401: {"description": "Authentication required"},
        422: {"description": "Validation error in search parameters"},
    },
)
async def search_users(
    query: Optional[str] = Query(None, max_length=255, description="Search query"),
    email: Optional[str] = Query(None, description="Filter by email"),
    onboarding_completed: Optional[bool] = Query(
        None, description="Filter by onboarding status"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of results per page"),
    current_user_id: str = Depends(get_current_user),
) -> UserListResponse:
    """
    Search users with filtering and pagination.

    This endpoint is primarily for administrative or service use.
    Regular users should use other endpoints for their own data.
    """
    try:
        search_request = UserSearchRequest(
            query=query,
            email=email,
            onboarding_completed=onboarding_completed,
            page=page,
            page_size=page_size,
        )

        search_results = await get_user_service().search_users(search_request)

        logger.info(
            f"User search performed by {current_user_id}, found {search_results.total} results"
        )
        return search_results

    except Exception as e:
        logger.error(f"Unexpected error in user search: {e}")
        raise ServiceError(message="Failed to search users")


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user profile",
    description="Retrieve user profile information by user ID. Users can only access their own profile.",
    responses={
        200: {"description": "User profile retrieved successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied - users can only access their own profile"},
        404: {"description": "User not found"},
    },
)
async def get_user_profile(
    user_id: str = Path(..., description="User external auth ID"),
    current_user_external_auth_id: str = Depends(get_current_user),
) -> UserResponse:
    """
    Get user profile by external auth ID.

    Users can only access their own profile. The user_id must match
    the authenticated user's external auth ID.
    """
    try:
        # Verify ownership - user can only access their own profile
        if current_user_external_auth_id != user_id:
            logger.warning(
                f"User {current_user_external_auth_id} attempted to access profile of user {user_id}"
            )
            raise AuthError(
                message="Access denied: You can only access your own profile"
            )

        # Get the user profile by external auth ID
        user_profile = await get_user_service().get_user_profile_by_external_auth_id(
            user_id
        )

        logger.info(f"Retrieved profile for user {user_id}")
        return user_profile

    except NotFoundError as e:
        logger.warning(f"User not found: {e.message}")
        raise e
    except AuthError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving user profile {user_id}: {e}")
        raise ServiceError(message="Failed to retrieve user profile")


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user profile",
    description="Update user profile information. Users can only update their own profile.",
    responses={
        200: {"description": "User profile updated successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied - users can only update their own profile"},
        404: {"description": "User not found"},
        422: {"description": "Validation error in request data"},
    },
)
async def update_user_profile(
    user_data: UserUpdate,
    user_id: str = Path(..., description="User external auth ID"),
    current_user_external_auth_id: str = Depends(get_current_user),
) -> UserResponse:
    """
    Update user profile.

    Users can only update their own profile. Supports partial updates
    - only provided fields will be updated.
    """
    try:
        # Verify ownership - user can only update their own profile
        if current_user_external_auth_id != user_id:
            logger.warning(
                f"User {current_user_external_auth_id} attempted to update profile of user {user_id}"
            )
            raise AuthError(
                message="Access denied: You can only update your own profile"
            )

        updated_user = await get_user_service().update_user_by_external_auth_id(
            user_id, user_data
        )
        user_response = UserResponse.from_orm(updated_user)

        logger.info(f"Updated profile for user {user_id}")
        return user_response

    except NotFoundError as e:
        logger.warning(f"User not found: {e.message}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error updating user profile {user_id}: {e}")
        raise ServiceError(message="Failed to update user profile")


@router.delete(
    "/{user_id}",
    response_model=UserDeleteResponse,
    summary="Delete user profile",
    description="Soft delete user profile. Users can only delete their own profile.",
    responses={
        200: {"description": "User profile deleted successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied - users can only delete their own profile"},
        404: {"description": "User not found"},
    },
)
async def delete_user_profile(
    user_id: str = Path(..., description="User external auth ID"),
    current_user_external_auth_id: str = Depends(get_current_user),
) -> UserDeleteResponse:
    """
    Delete user profile (soft delete).

    Users can only delete their own profile. This performs a soft delete
    by setting the deleted_at timestamp.
    """
    try:
        # Verify ownership - user can only delete their own profile
        if current_user_external_auth_id != user_id:
            logger.warning(
                f"User {current_user_external_auth_id} attempted to delete profile of user {user_id}"
            )
            raise AuthError(
                message="Access denied: You can only delete your own profile"
            )

        delete_response = await get_user_service().delete_user_by_external_auth_id(
            user_id
        )

        logger.info(f"Deleted profile for user {user_id}")
        return delete_response

    except NotFoundError as e:
        logger.warning(f"User not found: {e.message}")
        raise e
    except AuthError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting user profile {user_id}: {e}")
        raise ServiceError(message="Failed to delete user profile")


@router.put(
    "/{user_id}/onboarding",
    response_model=UserResponse,
    summary="Update user onboarding status",
    description="Update user onboarding completion status and current step.",
    responses={
        200: {"description": "Onboarding status updated successfully"},
        401: {"description": "Authentication required"},
        403: {
            "description": "Access denied - users can only update their own onboarding"
        },
        404: {"description": "User not found"},
        422: {"description": "Validation error in onboarding data"},
    },
)
async def update_user_onboarding(
    onboarding_data: UserOnboardingUpdate,
    user_id: str = Path(..., description="User external auth ID"),
    current_user_external_auth_id: str = Depends(get_current_user),
) -> UserResponse:
    """
    Update user onboarding status.

    Users can only update their own onboarding status. This endpoint
    is used to track user progress through the onboarding flow.
    """
    try:
        # Verify ownership - user can only update their own onboarding
        if current_user_external_auth_id != user_id:
            logger.warning(
                f"User {current_user_external_auth_id} attempted to update onboarding of user {user_id}"
            )
            raise AuthError(
                message="Access denied: You can only update your own onboarding"
            )

        updated_user = (
            await get_user_service().update_user_onboarding_by_external_auth_id(
                user_id, onboarding_data
            )
        )
        user_response = UserResponse.from_orm(updated_user)

        logger.info(
            f"Updated onboarding for user {user_id}: completed={onboarding_data.onboarding_completed}"
        )
        return user_response

    except NotFoundError as e:
        logger.warning(f"User not found: {e.message}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error updating onboarding for user {user_id}: {e}")
        raise ServiceError(message="Failed to update onboarding")


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
    current_service: str = Depends(get_current_service),
):
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
    logger.info(f"User creation request from service: {current_service}")
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
                raise BrieflyAPIException(
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
