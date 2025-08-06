"""
Internal service-to-service API router.

Provides secure endpoints for other services to retrieve user tokens
and integration status with service authentication.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from services.common.http_errors import (
    BrieflyAPIError,
    ErrorCode,
    NotFoundError,
    ServiceError,
    ValidationError,
)
from services.common.logging_config import get_logger, request_id_var
from services.user.auth.service_auth import service_permission_required
from services.user.schemas.integration import (
    InternalTokenRefreshRequest,
    InternalTokenRequest,
    InternalTokenResponse,
    InternalUserStatusResponse,
)
from services.user.schemas.preferences import (
    PreferencesResetRequest,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)
from services.user.schemas.user import (
    EmailResolutionRequest,
    UserCreate,
    UserResponse,
)
from services.user.services.preferences_service import PreferencesService
from services.user.services.token_service import get_token_service
from services.user.services.user_service import get_user_service

logger = get_logger(__name__)


class UserCreateResponse(BaseModel):
    """Response model for user creation/upsert with creation status."""

    user: UserResponse
    created: bool


router = APIRouter(
    prefix="/internal",
    tags=["Internal"],
    responses={401: {"description": "Service authentication required"}},
)


@router.post("/tokens/get", response_model=InternalTokenResponse)
async def get_user_token(
    request: InternalTokenRequest,
    service_name: str = Depends(service_permission_required(["read_tokens"])),
) -> InternalTokenResponse:
    """
    Get a valid access token for a user and provider.

    This endpoint is used by other services to retrieve tokens for API operations.
    """

    request_id = request_id_var.get()
    logger.info(
        f"[{request_id}] Token request received: user_id={request.user_id}, provider={request.provider}, scopes={request.required_scopes}"
    )

    try:
        token_service = get_token_service()
        result = await token_service.get_valid_token(
            user_id=request.user_id,
            provider=request.provider,
            required_scopes=request.required_scopes,
            refresh_if_needed=request.refresh_if_needed,
        )

        logger.info(
            f"[{request_id}] Token request completed: success={result.success}, provider={request.provider}"
        )
        return result

    except NotFoundError:
        logger.error(
            f"[{request_id}] Token request failed: user_id={request.user_id}, provider={request.provider}, error=User not found"
        )
        raise NotFoundError("User", request.user_id)
    except ServiceError as e:
        logger.error(
            f"[{request_id}] Token request failed: user_id={request.user_id}, provider={request.provider}, error={str(e)}"
        )
        # Return error in response rather than raising HTTP exception
        return InternalTokenResponse(
            success=False,
            access_token=None,
            refresh_token=None,
            expires_at=None,
            provider=request.provider,
            user_id=request.user_id,
            integration_id=None,
            error=str(e),
        )
    except Exception as e:
        logger.error(
            f"[{request_id}] Token request failed: user_id={request.user_id}, provider={request.provider}, error={str(e)}"
        )
        raise


@router.post("/tokens/refresh", response_model=InternalTokenResponse)
async def refresh_user_tokens(
    request: InternalTokenRefreshRequest,
    service_name: str = Depends(service_permission_required(["write_tokens"])),
) -> InternalTokenResponse:
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
    except NotFoundError:
        raise NotFoundError("User", request.user_id)
    except ServiceError as e:
        # Return error in response rather than raising HTTP exception
        return InternalTokenResponse(
            success=False,
            access_token=None,
            refresh_token=None,
            expires_at=None,
            provider=request.provider,
            user_id=request.user_id,
            integration_id=None,
            error=str(e),
        )


@router.get("/users/{user_id}/status", response_model=InternalUserStatusResponse)
async def get_user_status(
    user_id: str,
    service_name: str = Depends(service_permission_required(["read_users"])),
) -> InternalUserStatusResponse:
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
    except NotFoundError:
        raise NotFoundError("User", user_id)
    except ServiceError as e:
        raise ServiceError(message=str(e))


@router.get("/users/by-external-id/{external_auth_id}")
async def get_user_by_external_auth_id(
    external_auth_id: str,
    service_name: str = Depends(service_permission_required(["read_users"])),
) -> Dict[str, Any]:
    """
    Get user information by external_auth_id (internal service endpoint).

    This endpoint always returns 200 with user information or null,
    avoiding 404 logs for missing users.

    Returns:
        User data if found, or {"exists": false} if not found
    """
    try:
        user = await get_user_service().get_user_by_external_auth_id_auto_detect(
            external_auth_id
        )

        return {
            "exists": True,
            "user_id": user.external_auth_id,
            "internal_id": user.id,
            "provider": user.auth_provider,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "preferred_provider": user.preferred_provider,
            "onboarding_completed": user.onboarding_completed,
            "onboarding_step": user.onboarding_step,
        }
    except NotFoundError:
        return {
            "exists": False,
            "user_id": external_auth_id,
        }
    except Exception as e:
        logger.error(f"Unexpected error during user lookup by external_auth_id: {e}")
        raise ServiceError(message="Failed to lookup user by external_auth_id")


@router.get("/users/exists")
async def check_user_exists(
    email: str = Query(..., description="Email address to check"),
    provider: Optional[str] = Query(
        None, description="OAuth provider (google, microsoft, etc.)"
    ),
    service_name: str = Depends(service_permission_required(["read_users"])),
) -> Dict[str, Any]:
    """
    Check if a user exists by email (primary endpoint for user existence checks).

    This endpoint always returns 200 with a detailed response,
    avoiding 404 logs for missing users. Use this instead of GET /users/id
    when you only need to check existence.

    Returns:
        {"exists": true/false, "user_id": "id_if_exists", "provider": "provider_if_exists"}
    """
    try:
        email_request = EmailResolutionRequest(email=email, provider=provider)
        resolution_result = await get_user_service().resolve_email_to_user_id(
            email_request
        )

        # Get full user data to return additional info
        user = await get_user_service().get_user_by_external_auth_id_auto_detect(
            resolution_result.external_auth_id
        )

        return {
            "exists": True,
            "user_id": user.external_auth_id,
            "provider": user.auth_provider,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
    except NotFoundError:
        return {
            "exists": False,
            "user_id": None,
            "provider": provider,
            "email": email,
        }
    except ValidationError as e:
        logger.warning(f"User existence check failed - validation error: {e.message}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during user existence check: {e}")
        raise ServiceError(message="Failed to check user existence")


@router.get("/users/id", response_model=UserResponse)
async def get_user_by_email_internal(
    email: str = Query(..., description="Email address to lookup"),
    provider: Optional[str] = Query(
        None, description="OAuth provider (google, microsoft, etc.)"
    ),
    service_name: str = Depends(service_permission_required(["read_users"])),
) -> UserResponse:
    """
    Get user by exact email lookup (internal service endpoint).

    ⚠️  DEPRECATED: Use GET /v1/internal/users/exists instead to avoid 404 error logs.
    This endpoint will be removed in a future version.

    This endpoint provides a clean RESTful way to find users by email address
    without exposing internal email normalization implementation details.
    Perfect for NextAuth integration where you need to check user existence
    before deciding whether to create a new user.

    **Authentication:**
    - Requires service-to-service API key authentication
    - Only authorized services (frontend, chat, office) can lookup users
    - Never accepts user JWTs

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


@router.post("/users/", response_model=UserCreateResponse)
async def create_or_upsert_user_internal(
    user_data: UserCreate,
    service_name: str = Depends(service_permission_required(["write_users"])),
) -> UserCreateResponse:
    """
    Create a new user or return existing user by external_auth_id and auth_provider (internal service endpoint).

    This is a protected endpoint designed for OAuth/NextAuth flows where
    we want to create users if they don't exist, or return existing
    users if they do. Requires service authentication (API key).

    **Authentication:**
    - Requires service-to-service API key authentication
    - Only authorized services (frontend, chat, office) can create users
    - Never accepts user JWTs

    **Response Status Codes:**
    - 200 (OK): Existing user found and returned
    - 201 (Created): New user created successfully
    - 409 (Conflict): Email collision detected
    - 422 (Validation Error): Invalid request data
    - 500 (Internal Server Error): Unexpected error
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
        # Try to find existing user first using the same method as GET /internal/users/id
        # This ensures consistency between GET and POST endpoints
        email_request = EmailResolutionRequest(
            email=user_data.email, provider=user_data.auth_provider
        )

        try:
            # Use the same resolution logic as GET endpoint
            resolution_result = await get_user_service().resolve_email_to_user_id(
                email_request
            )

            # Get full user data to return
            existing_user = (
                await get_user_service().get_user_by_external_auth_id_auto_detect(
                    resolution_result.external_auth_id
                )
            )
            user_response = UserResponse.from_orm(existing_user)

            logger.info(
                f"Found existing user for email {user_data.email} with provider {user_data.auth_provider}: {existing_user.external_auth_id}"
            )
            # Return existing user with created=False
            return UserCreateResponse(user=user_response, created=False)

        except NotFoundError:
            # User doesn't exist, create new one
            logger.info(
                f"User not found for email {user_data.email}, attempting to create new user with {user_data.auth_provider} ID: {user_data.external_auth_id}"
            )

            new_user = await get_user_service().create_user(user_data)
            user_response = UserResponse.from_orm(new_user)

            logger.info(
                f"Created new user with {user_data.auth_provider} ID: {user_data.external_auth_id}"
            )
            # Return new user with created=True
            return UserCreateResponse(user=user_response, created=True)

    except ValidationError as e:
        logger.error(f"Validation error during user creation: {e.message}")
        logger.error(f"Validation error details: {e.details}")
        if "collision" in str(e.message).lower():
            logger.warning(f"Email collision during user creation: {e.message}")
            raise BrieflyAPIError(
                message="Email collision detected",
                details=e.details,
                error_code=ErrorCode.ALREADY_EXISTS,
                status_code=409,
            )
        else:
            logger.warning(f"Validation error during user creation: {e.message}")
            raise e
    except Exception as e:
        logger.error(f"Unexpected error in create_or_upsert_user: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {str(e)}")
        raise ServiceError(message="Failed to create or retrieve user")


# --- INTERNAL-ONLY: /internal/users/{user_id}/preferences endpoints ---
@router.put("/users/{user_id}/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences_internal(
    user_id: str,
    preferences_update: UserPreferencesUpdate,
    service_name: str = Depends(service_permission_required(["write_preferences"])),
) -> UserPreferencesResponse:
    """
    Internal service endpoint to update user preferences by user_id.
    Requires service-to-service API key authentication.
    """
    return await PreferencesService.update_user_preferences(user_id, preferences_update)


@router.post(
    "/users/{user_id}/preferences/reset", response_model=UserPreferencesResponse
)
async def reset_user_preferences_internal(
    user_id: str,
    reset_request: PreferencesResetRequest,
    service_name: str = Depends(service_permission_required(["write_preferences"])),
) -> UserPreferencesResponse:
    """
    Internal service endpoint to reset user preferences by user_id.
    Requires service-to-service API key authentication.
    """
    return await PreferencesService.reset_user_preferences(
        user_id, reset_request.categories
    )


# --- END INTERNAL-ONLY ---


@router.get("/users/{user_id}/preferences")
async def get_user_preferences_internal(
    user_id: str,
    service_name: str = Depends(service_permission_required(["read_preferences"])),
) -> Any:
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
    service_name: str = Depends(service_permission_required(["read_users"])),
) -> Dict[str, Any]:
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
