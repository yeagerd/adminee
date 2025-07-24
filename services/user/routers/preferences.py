"""
User preferences management router.

Handles user preference retrieval, updates, and default restoration.
Supports partial updates and preference validation.

# Endpoint Pattern Note:
# - User-facing endpoints use /me/preferences and extract user from JWT/session (requires user authentication)
# - /users/{user_id}/preferences endpoints are deprecated and removed; use /me/preferences instead
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from services.common.logging_config import get_logger
from services.user.auth.nextauth import get_current_user
from services.user.schemas.preferences import (
    PreferencesResetRequest,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)
from services.user.services.preferences_service import PreferencesService

# Set up logging
logger = get_logger(__name__)

# User-facing preferences router (no prefix)
router = APIRouter(tags=["Preferences"])


@router.get(
    "/users/me/preferences",
    response_model=UserPreferencesResponse,
    summary="Get current user's preferences",
    description="Retrieve preferences for the authenticated user.",
    status_code=status.HTTP_200_OK,
)
async def get_my_preferences(
    current_user: Annotated[str, Depends(get_current_user)],
) -> UserPreferencesResponse:
    """
    Get preferences for the authenticated user (user-facing endpoint).
    """
    return await PreferencesService.get_user_preferences(current_user)


@router.put(
    "/users/me/preferences",
    response_model=UserPreferencesResponse,
    summary="Update current user's preferences",
    description="Update preferences for the authenticated user.",
    status_code=status.HTTP_200_OK,
)
async def update_my_preferences(
    preferences_update: UserPreferencesUpdate,
    current_user: Annotated[str, Depends(get_current_user)],
) -> UserPreferencesResponse:
    """
    Update preferences for the authenticated user (user-facing endpoint).
    """
    return await PreferencesService.update_user_preferences(
        current_user, preferences_update
    )


@router.post(
    "/users/me/preferences/reset",
    response_model=UserPreferencesResponse,
    summary="Reset current user's preferences",
    description="Reset preferences for the authenticated user.",
    status_code=status.HTTP_200_OK,
)
async def reset_my_preferences(
    reset_request: PreferencesResetRequest,
    current_user: Annotated[str, Depends(get_current_user)],
) -> UserPreferencesResponse:
    """
    Reset preferences for the authenticated user (user-facing endpoint).
    """
    return await PreferencesService.reset_user_preferences(
        current_user, reset_request.categories
    )


# --- END USER-FACING ENDPOINTS ---
