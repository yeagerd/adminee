"""
User profile management router for User Management Service.

Implements CRUD operations for user profiles with authentication,
authorization, and comprehensive error handling.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from services.user_management.auth import get_current_user
from services.user_management.exceptions import UserNotFoundException, ValidationException
from services.user_management.schemas.user import (
    UserDeleteResponse,
    UserListResponse,
    UserOnboardingUpdate,
    UserResponse,
    UserSearchRequest,
    UserUpdate,
)
from services.user_management.services.user_service import user_service

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
        current_user = await user_service.get_user_by_external_auth_id(
            current_user_external_auth_id
        )
        user_response = UserResponse.from_orm(current_user)

        logger.info(
            f"Retrieved current user profile for {current_user_external_auth_id}"
        )
        return user_response

    except UserNotFoundException as e:
        logger.warning(f"Current user not found: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "UserNotFound", "message": e.message},
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving current user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "Failed to retrieve current user profile",
            },
        )


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
    user_id: int = Path(..., description="User database ID"),
    current_user_external_auth_id: str = Depends(get_current_user),
) -> UserResponse:
    """
    Get user profile by database ID.

    Users can only access their own profile. The user_id must belong
    to the authenticated user.
    """
    try:
        # Get the user to verify they exist and check ownership
        user = await user_service.get_user_by_id(user_id)

        # Verify ownership - check if the authenticated user's external auth ID matches
        if current_user_external_auth_id != user.external_auth_id:
            logger.warning(
                f"User {current_user_external_auth_id} attempted to access profile of user {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "AuthorizationError",
                    "message": "Access denied: You can only access your own profile",
                },
            )

        user_profile = await user_service.get_user_profile(user_id)

        logger.info(f"Retrieved profile for user {user_id}")
        return user_profile

    except UserNotFoundException as e:
        logger.warning(f"User not found: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "UserNotFound", "message": e.message},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving user profile {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "Failed to retrieve user profile",
            },
        )


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
    user_id: int = Path(..., description="User database ID"),
    current_user_external_auth_id: str = Depends(get_current_user),
) -> UserResponse:
    """
    Update user profile.

    Users can only update their own profile. Supports partial updates
    - only provided fields will be updated.
    """
    try:
        # Get the user to verify they exist and check ownership
        user = await user_service.get_user_by_id(user_id)

        # Verify ownership
        if current_user_external_auth_id != user.external_auth_id:
            logger.warning(
                f"User {current_user_external_auth_id} attempted to update profile of user {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "AuthorizationError",
                    "message": "Access denied: You can only update your own profile",
                },
            )

        updated_user = await user_service.update_user(user_id, user_data)
        user_response = UserResponse.from_orm(updated_user)

        logger.info(f"Updated profile for user {user_id}")
        return user_response

    except UserNotFoundException as e:
        logger.warning(f"User not found: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "UserNotFound", "message": e.message},
        )
    except ValidationException as e:
        logger.warning(f"Validation error updating user {user_id}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "ValidationError", "message": e.message},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating user profile {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "Failed to update user profile",
            },
        )


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
    user_id: int = Path(..., description="User database ID"),
    current_user_external_auth_id: str = Depends(get_current_user),
) -> UserDeleteResponse:
    """
    Delete user profile (soft delete).

    Users can only delete their own profile. This performs a soft delete
    by setting the deleted_at timestamp.
    """
    try:
        # Get the user to verify they exist and check ownership
        user = await user_service.get_user_by_id(user_id)

        # Verify ownership
        if current_user_external_auth_id != user.external_auth_id:
            logger.warning(
                f"User {current_user_external_auth_id} attempted to delete profile of user {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "AuthorizationError",
                    "message": "Access denied: You can only delete your own profile",
                },
            )

        delete_response = await user_service.delete_user(user_id)

        logger.info(f"Deleted profile for user {user_id}")
        return delete_response

    except UserNotFoundException as e:
        logger.warning(f"User not found: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "UserNotFound", "message": e.message},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting user profile {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "Failed to delete user profile",
            },
        )


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
    user_id: int = Path(..., description="User database ID"),
    current_user_external_auth_id: str = Depends(get_current_user),
) -> UserResponse:
    """
    Update user onboarding status.

    Users can only update their own onboarding status. This endpoint
    is used to track user progress through the onboarding flow.
    """
    try:
        # Get the user to verify they exist and check ownership
        user = await user_service.get_user_by_id(user_id)

        # Verify ownership
        if current_user_external_auth_id != user.external_auth_id:
            logger.warning(
                f"User {current_user_external_auth_id} attempted to update onboarding of user {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "AuthorizationError",
                    "message": "Access denied: You can only update your own onboarding",
                },
            )

        updated_user = await user_service.update_user_onboarding(
            user_id, onboarding_data
        )
        user_response = UserResponse.from_orm(updated_user)

        logger.info(
            f"Updated onboarding for user {user_id}: completed={onboarding_data.onboarding_completed}"
        )
        return user_response

    except UserNotFoundException as e:
        logger.warning(f"User not found: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "UserNotFound", "message": e.message},
        )
    except ValidationException as e:
        logger.warning(
            f"Validation error updating onboarding for user {user_id}: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "ValidationError", "message": e.message},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating onboarding for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "Failed to update onboarding",
            },
        )


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

        search_results = await user_service.search_users(search_request)

        logger.info(
            f"User search performed by {current_user_id}, found {search_results.total} results"
        )
        return search_results

    except ValidationException as e:
        logger.warning(f"Validation error in user search: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "ValidationError", "message": e.message},
        )
    except Exception as e:
        logger.error(f"Unexpected error in user search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "Failed to search users",
            },
        )
