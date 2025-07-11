"""
User preferences management router.

Handles user preference retrieval, updates, and default restoration.
Supports partial updates and preference validation.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends

from services.common.http_errors import (
    NotFoundError,
    ServiceError,
)
from services.user.auth.nextauth import get_current_user, verify_user_ownership
from services.user.schemas.preferences import (
    PreferencesResetRequest,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)
from services.user.services.preferences_service import PreferencesService

# Set up logging
logger = structlog.get_logger(__name__)


router = APIRouter(
    prefix="/users/{user_id}/preferences",
    tags=["Preferences"],
    responses={404: {"description": "User or preferences not found"}},
)


@router.get(
    "/",
    response_model=UserPreferencesResponse,
    summary="Get user preferences",
    description="Retrieve all user preferences including UI, notification, AI, integration, and privacy settings",
    responses={
        200: {"description": "Preferences retrieved successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied - can only access own preferences"},
        404: {"description": "User or preferences not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_preferences(
    user_id: str,
    current_user: Annotated[str, Depends(get_current_user)],
):
    """
    Get user preferences endpoint.

    Returns all preference categories for the authenticated user.
    Users can only access their own preferences.
    """
    try:
        logger.info(
            "Getting user preferences", user_id=user_id, current_user=current_user
        )

        # Verify user ownership
        await verify_user_ownership(current_user, user_id)

        # Pass external auth ID directly to service (service handles internal lookup)
        preferences = await PreferencesService.get_user_preferences(user_id)

        if not preferences:
            logger.warning("Preferences not found", user_id=user_id)
            raise NotFoundError(
                "Preferences", identifier=f"Preferences not found for user {user_id}"
            )

        logger.info("Successfully retrieved preferences", user_id=user_id)
        return preferences

    except NotFoundError:
        raise NotFoundError(
            "Preferences", identifier=f"Preferences not found for user {user_id}"
        )
    except Exception as e:
        logger.error(
            "Unexpected error getting preferences", user_id=user_id, error=str(e)
        )
        raise ServiceError(message="Internal server error", details={"error": str(e)})


@router.put(
    "/",
    response_model=UserPreferencesResponse,
    summary="Update user preferences",
    description="Update user preferences with partial update support. Only provided categories will be updated.",
    responses={
        200: {"description": "Preferences updated successfully"},
        400: {"description": "Invalid preference values"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied - can only update own preferences"},
        404: {"description": "User or preferences not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def update_preferences(
    user_id: str,
    preferences_update: UserPreferencesUpdate,
    current_user: Annotated[str, Depends(get_current_user)],
):
    """
    Update user preferences endpoint.

    Supports partial updates - only the provided preference categories will be updated.
    Users can only update their own preferences.
    All updates are logged for audit purposes.
    """
    try:
        logger.info(
            "Updating user preferences",
            user_id=user_id,
            current_user=current_user,
            update_categories=[
                k for k, v in preferences_update.model_dump().items() if v is not None
            ],
        )

        # Verify user ownership
        await verify_user_ownership(current_user, user_id)

        # Pass external auth ID directly to service (service handles internal lookup)
        updated_preferences = await PreferencesService.update_user_preferences(
            user_id, preferences_update
        )

        logger.info("Successfully updated preferences", user_id=user_id)
        return updated_preferences

    except Exception as e:
        logger.error(
            "Unexpected error updating preferences", user_id=user_id, error=str(e)
        )
        raise ServiceError(message="Internal server error", details={"error": str(e)})


@router.post(
    "/reset",
    response_model=UserPreferencesResponse,
    summary="Reset user preferences",
    description="Reset user preferences to default values. Can reset all categories or specific ones.",
    responses={
        200: {"description": "Preferences reset successfully"},
        400: {"description": "Invalid reset request"},
        401: {"description": "Authentication required"},
        403: {"description": "Access denied - can only reset own preferences"},
        404: {"description": "User or preferences not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def reset_preferences(
    user_id: str,
    reset_request: PreferencesResetRequest,
    current_user: Annotated[str, Depends(get_current_user)],
):
    """
    Reset user preferences to defaults endpoint.

    Can reset all preferences or specific categories.
    All resets are logged for audit purposes.
    """
    try:
        logger.info(
            "Resetting user preferences",
            user_id=user_id,
            current_user=current_user,
            categories=reset_request.categories,
        )

        # Verify user ownership
        await verify_user_ownership(current_user, user_id)

        # Pass external auth ID directly to service (service handles internal lookup)
        reset_preferences = await PreferencesService.reset_user_preferences(
            user_id, reset_request.categories
        )

        logger.info("Successfully reset preferences", user_id=user_id)
        return reset_preferences

    except Exception as e:
        logger.error(
            "Unexpected error resetting preferences", user_id=user_id, error=str(e)
        )
        raise ServiceError(message="Internal server error", details={"error": str(e)})
