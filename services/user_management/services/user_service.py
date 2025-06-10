"""
User service business logic for User Management Service.

Handles user profile operations including CRUD operations,
onboarding management, and user search functionality.
"""

import logging
from datetime import datetime
from typing import List

from ..exceptions import (
    UserNotFoundException,
    ValidationException,
)
from ..models import User
from ..schemas.user import (
    UserCreate,
    UserDeleteResponse,
    UserListResponse,
    UserOnboardingUpdate,
    UserResponse,
    UserSearchRequest,
    UserUpdate,
)

logger = logging.getLogger(__name__)


class UserService:
    """Service class for user profile operations."""

    async def get_user_by_id(self, user_id: int) -> User:
        """
        Get user by internal database ID.

        Args:
            user_id: Internal database ID of the user

        Returns:
            User model instance

        Raises:
            UserNotFoundException: If user is not found
        """
        try:
            user = await User.objects.get(id=user_id)
            if user.deleted_at is not None:
                raise UserNotFoundException(str(user_id))

            logger.info(f"Retrieved user by ID: {user_id}")
            return user

        except Exception as e:
            if isinstance(e, UserNotFoundException):
                raise
            logger.error(f"Error retrieving user by ID {user_id}: {e}")
            raise UserNotFoundException(str(user_id))

    async def get_user_by_external_auth_id(self, external_auth_id: str, auth_provider: str = "clerk") -> User:
        """
        Get user by external authentication ID.

        Args:
            external_auth_id: External auth provider user ID
            auth_provider: Authentication provider name

        Returns:
            User model instance

        Raises:
            UserNotFoundException: If user is not found
        """
        try:
            user = await User.objects.get(external_auth_id=external_auth_id, auth_provider=auth_provider)
            if user.deleted_at is not None:
                raise UserNotFoundException(f"{auth_provider}:{external_auth_id}")

            logger.info(f"Retrieved user by external auth ID: {auth_provider}:{external_auth_id}")
            return user

        except Exception as e:
            if isinstance(e, UserNotFoundException):
                raise
            logger.error(f"Error retrieving user by external auth ID {auth_provider}:{external_auth_id}: {e}")
            raise UserNotFoundException(f"{auth_provider}:{external_auth_id}")



    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.

        Args:
            user_data: User creation data

        Returns:
            Created user model instance

        Raises:
            ValidationException: If user data is invalid or external_auth_id already exists
        """
        try:
            # Check if user with this external_auth_id already exists
            existing_user = await User.objects.filter(
                external_auth_id=user_data.external_auth_id,
                auth_provider=user_data.auth_provider
            ).get_or_none()

            if existing_user and existing_user.deleted_at is None:
                raise ValidationException(
                    field="external_auth_id",
                    value=user_data.external_auth_id,
                    reason=f"User with {user_data.auth_provider} ID {user_data.external_auth_id} already exists",
                )

            # Create new user
            user = await User.objects.create(
                external_auth_id=user_data.external_auth_id,
                auth_provider=user_data.auth_provider,
                email=user_data.email,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                profile_image_url=user_data.profile_image_url,
                onboarding_completed=False,
                onboarding_step="profile_setup",
            )

            logger.info(f"Created new user with {user_data.auth_provider} ID: {user_data.external_auth_id}")
            return user

        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise ValidationException(
                field="user_data",
                value=str(user_data),
                reason=f"Failed to create user: {str(e)}",
            )

    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """
        Update an existing user.

        Args:
            user_id: Internal database ID of the user
            user_data: User update data

        Returns:
            Updated user model instance

        Raises:
            UserNotFoundException: If user is not found
            ValidationException: If update data is invalid
        """
        try:
            user = await self.get_user_by_id(user_id)

            # Update only provided fields
            update_fields = {}
            if user_data.email is not None:
                update_fields["email"] = user_data.email
            if user_data.first_name is not None:
                update_fields["first_name"] = user_data.first_name
            if user_data.last_name is not None:
                update_fields["last_name"] = user_data.last_name
            if user_data.profile_image_url is not None:
                update_fields["profile_image_url"] = user_data.profile_image_url

            if update_fields:
                for field, value in update_fields.items():
                    setattr(user, field, value)
                await user.update()
                await user.load()  # Reload to get updated data

            logger.info(
                f"Updated user {user_id} with fields: {list(update_fields.keys())}"
            )
            return user

        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            raise ValidationException(
                field="user_data",
                value=str(user_data),
                reason=f"Failed to update user: {str(e)}",
            )

    async def update_user_onboarding(
        self, user_id: int, onboarding_data: UserOnboardingUpdate
    ) -> User:
        """
        Update user onboarding status.

        Args:
            user_id: Internal database ID of the user
            onboarding_data: Onboarding update data

        Returns:
            Updated user model instance

        Raises:
            UserNotFoundException: If user is not found
            ValidationException: If onboarding data is invalid
        """
        try:
            user = await self.get_user_by_id(user_id)

            await user.update(
                onboarding_completed=onboarding_data.onboarding_completed,
                onboarding_step=onboarding_data.onboarding_step,
            )
            await user.load()

            logger.info(
                f"Updated onboarding for user {user_id}: completed={onboarding_data.onboarding_completed}"
            )
            return user

        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error updating onboarding for user {user_id}: {e}")
            raise ValidationException(
                field="onboarding_data",
                value=str(onboarding_data),
                reason=f"Failed to update onboarding: {str(e)}",
            )

    async def delete_user(self, user_id: int) -> UserDeleteResponse:
        """
        Soft delete a user.

        Args:
            user_id: Internal database ID of the user

        Returns:
            Deletion response with status

        Raises:
            UserNotFoundException: If user is not found
        """
        try:
            user = await self.get_user_by_id(user_id)

            # Perform soft delete
            deleted_at = datetime.utcnow()
            await user.update(deleted_at=deleted_at)

            logger.info(f"Soft deleted user {user_id}")

            return UserDeleteResponse(
                success=True,
                message=f"User {user_id} successfully deleted",
                user_id=user_id,
                external_auth_id=user.external_auth_id,
                deleted_at=deleted_at,
            )

        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            raise ValidationException(
                field="user_id",
                value=user_id,
                reason=f"Failed to delete user: {str(e)}",
            )

    async def search_users(self, search_request: UserSearchRequest) -> UserListResponse:
        """
        Search users with pagination.

        Args:
            search_request: Search criteria and pagination parameters

        Returns:
            Paginated user list response
        """
        try:
            # Build query
            query = User.objects.filter(deleted_at__isnull=True)

            # Apply filters
            if search_request.email:
                query = query.filter(email__icontains=search_request.email)

            if search_request.onboarding_completed is not None:
                query = query.filter(
                    onboarding_completed=search_request.onboarding_completed
                )

            if search_request.query:
                # Search in first_name, last_name, and email
                query = query.filter(
                    # This would need to be adjusted based on your ORM's syntax
                    # For now, we'll search in first_name
                    first_name__icontains=search_request.query
                )

            # Get total count
            total = await query.count()

            # Apply pagination
            offset = (search_request.page - 1) * search_request.page_size
            users = await query.offset(offset).limit(search_request.page_size).all()

            # Calculate pagination info
            has_next = (search_request.page * search_request.page_size) < total
            has_previous = search_request.page > 1

            logger.info(f"Found {total} users matching search criteria")

            return UserListResponse(
                users=[UserResponse.from_orm(user) for user in users],
                total=total,
                page=search_request.page,
                page_size=search_request.page_size,
                has_next=has_next,
                has_previous=has_previous,
            )

        except Exception as e:
            logger.error(f"Error searching users: {e}")
            raise ValidationException(
                field="search_request",
                value=str(search_request),
                reason=f"Failed to search users: {str(e)}",
            )

    async def get_user_profile(self, user_id: int) -> UserResponse:
        """
        Get user profile response.

        Args:
            user_id: Internal database ID of the user

        Returns:
            User response schema

        Raises:
            UserNotFoundException: If user is not found
        """
        user = await self.get_user_by_id(user_id)
        return UserResponse.from_orm(user)

    async def verify_user_exists(self, user_id: int) -> bool:
        """
        Verify if user exists (for authorization checks).

        Args:
            user_id: Internal database ID of the user

        Returns:
            True if user exists and is not deleted
        """
        try:
            await self.get_user_by_id(user_id)
            return True
        except UserNotFoundException:
            return False

    async def get_users_by_ids(self, user_ids: List[int]) -> List[User]:
        """
        Get multiple users by their internal database IDs.

        Args:
            user_ids: List of internal database IDs

        Returns:
            List of user model instances
        """
        try:
            users = await User.objects.filter(
                id__in=user_ids, deleted_at__isnull=True
            ).all()

            logger.info(
                f"Retrieved {len(users)} users from {len(user_ids)} requested IDs"
            )
            return users

        except Exception as e:
            logger.error(f"Error retrieving users by IDs: {e}")
            return []

    async def update_user_last_login(self, user_id: int) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: Internal database ID of the user
        """
        try:
            user = await self.get_user_by_id(user_id)
            await user.update(updated_at=datetime.utcnow())

            logger.debug(f"Updated last login for user {user_id}")

        except Exception as e:
            # Don't raise exception for this non-critical operation
            logger.warning(f"Failed to update last login for user {user_id}: {e}")


# Global service instance
user_service = UserService()
