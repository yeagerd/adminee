"""
User preferences management router.

Handles user preference retrieval, updates, and default restoration.
Supports partial updates and preference validation.
"""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from services.user_management.auth.clerk import get_current_user, verify_user_ownership
from services.user_management.exceptions import (
    AuthorizationException,
    DatabaseException,
    PreferencesNotFoundException,
    UserNotFoundException,
    ValidationException,
)
from services.user_management.schemas.preferences import (
    PreferencesResetRequest,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)
from services.user_management.services import preferences_service

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

        preferences = await preferences_service.get_user_preferences(user_id)

        if not preferences:
            logger.warning("Preferences not found", user_id=user_id)
            raise PreferencesNotFoundException(
                f"Preferences not found for user {user_id}"
            )

        logger.info("Successfully retrieved preferences", user_id=user_id)
        return preferences

    except PreferencesNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found"
        )
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except AuthorizationException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access your own preferences",
        )
    except DatabaseException as e:
        logger.error(
            "Database error getting preferences", user_id=user_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve preferences",
        )
    except Exception as e:
        logger.error(
            "Unexpected error getting preferences", user_id=user_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


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

        updated_preferences = await preferences_service.update_user_preferences(
            user_id, preferences_update
        )

        logger.info("Successfully updated preferences", user_id=user_id)
        return updated_preferences

    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except PreferencesNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found"
        )
    except AuthorizationException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only update your own preferences",
        )
    except ValidationException as e:
        logger.warning(
            "Validation error updating preferences", user_id=user_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except DatabaseException as e:
        logger.error(
            "Database error updating preferences", user_id=user_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences",
        )
    except Exception as e:
        logger.error(
            "Unexpected error updating preferences", user_id=user_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


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

        reset_preferences = await preferences_service.reset_user_preferences(
            user_id, reset_request.categories
        )

        logger.info(
            "Successfully reset preferences",
            user_id=user_id,
            categories=reset_request.categories,
        )
        return reset_preferences

    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except PreferencesNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found"
        )
    except AuthorizationException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only reset your own preferences",
        )
    except ValidationException as e:
        logger.warning(
            "Validation error resetting preferences", user_id=user_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except DatabaseException as e:
        logger.error(
            "Database error resetting preferences", user_id=user_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset preferences",
        )
    except Exception as e:
        logger.error(
            "Unexpected error resetting preferences", user_id=user_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
