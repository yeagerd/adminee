"""
User service for User Management Service.

Provides business logic for user operations including CRUD operations,
profile management, and user lifecycle management.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import func, select

from services.common.http_errors import NotFoundError, ValidationError
from services.user.database import get_async_session
from services.user.models.user import User
from services.user.schemas.user import (
    EmailResolutionRequest,
    EmailResolutionResponse,
    UserCreate,
    UserDeleteResponse,
    UserListResponse,
    UserOnboardingUpdate,
    UserResponse,
    UserSearchRequest,
    UserUpdate,
)
from services.user.services.audit_service import audit_logger
from services.user.utils.email_collision import EmailCollisionDetector

logger = audit_logger.logger


class UserService:
    """Service class for user profile operations."""

    async def get_user_by_id(self, user_id: int) -> User:
        """
        Get user by internal database ID.

        Args:
            user_id: Internal database ID

        Returns:
            User model instance

        Raises:
            NotFoundError: If user is not found
        """
        try:
            async_session = get_async_session()
            async with async_session() as session:
                result = await session.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()

                if user is None or user.deleted_at is not None:
                    raise NotFoundError(resource="User", identifier=str(user_id or ""))

                logger.info(f"Retrieved user by ID: {user_id}")
                return user

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving user by ID {user_id}: {e}")
            raise NotFoundError(resource="User", identifier=str(user_id))

    async def get_user_by_external_auth_id(
        self, external_auth_id: str, auth_provider: str = "nextauth"
    ) -> User:
        """
        Get user by external authentication ID.

        Args:
            external_auth_id: External auth provider user ID
            auth_provider: Authentication provider name

        Returns:
            User model instance

        Raises:
            NotFoundError: If user is not found
        """
        try:
            async_session = get_async_session()
            async with async_session() as session:
                result = await session.execute(
                    select(User).where(
                        User.external_auth_id == external_auth_id,
                        User.auth_provider == auth_provider,
                    )
                )
                user = result.scalar_one_or_none()

                if user is None or user.deleted_at is not None:
                    id_str = (
                        f"{auth_provider}:{external_auth_id}"
                        if auth_provider
                        else str(external_auth_id or "")
                    )
                    raise NotFoundError(resource="User", identifier=str(id_str or ""))

                logger.info(
                    f"Retrieved user by external auth ID: {auth_provider}:{external_auth_id}"
                )
                return user

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Error retrieving user by external auth ID {auth_provider}:{external_auth_id}: {e}"
            )
            id_str = (
                f"{auth_provider}:{external_auth_id}"
                if auth_provider
                else str(external_auth_id or "")
            )
            raise NotFoundError(resource="User", identifier=str(id_str or ""))

    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.

        Args:
            user_data: User creation data

        Returns:
            Created user model instance

        Raises:
            ValidationError: If user data is invalid or external_auth_id already exists
        """
        detector = EmailCollisionDetector()
        try:
            async_session = get_async_session()
            async with async_session() as session:
                # Check if user with this external_auth_id already exists
                result = await session.execute(
                    select(User).where(
                        User.external_auth_id == user_data.external_auth_id,
                        User.auth_provider == user_data.auth_provider,
                    )
                )
                existing_user = result.scalar_one_or_none()

                if existing_user and existing_user.deleted_at is None:
                    raise ValidationError(
                        message="User already exists",
                        field="email",
                        value=user_data.email,
                        details={"collision": True},
                    )

                # Check for email collision using normalized_email
                collision = await detector.get_collision_details(user_data.email)
                if collision["collision"]:
                    raise ValidationError(
                        message="Email collision detected",
                        field="email",
                        value=user_data.email,
                        details=collision,
                    )

                # Normalize email for storage
                normalized_email = await detector.normalize_email_async(user_data.email)

                # Create new user
                user = User(
                    external_auth_id=user_data.external_auth_id,
                    auth_provider=user_data.auth_provider,
                    email=user_data.email,
                    normalized_email=normalized_email,
                    first_name=user_data.first_name,
                    last_name=user_data.last_name,
                    profile_image_url=user_data.profile_image_url,
                    onboarding_completed=False,
                    onboarding_step="profile_setup",
                )

                session.add(user)
                await session.commit()
                await session.refresh(user)

                logger.info(
                    f"Created new user with {user_data.auth_provider} ID: {user_data.external_auth_id}"
                )
                return user

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise ValidationError(
                message=f"Failed to create user: {str(e)}",
                field="user_data",
                value=str(user_data),
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
            NotFoundError: If user is not found
            ValidationError: If update data is invalid
        """
        from services.user.utils.email_collision import EmailCollisionDetector

        detector = EmailCollisionDetector()
        try:
            async_session = get_async_session()
            async with async_session() as session:
                # Get user first
                result = await session.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()

                if user is None or user.deleted_at is not None:
                    raise NotFoundError(resource="User", identifier=str(user_id or ""))

                # Update only provided fields
                update_fields = {}
                if user_data.email is not None:
                    # Only check collision if the email is actually changing
                    if user.email != user_data.email:
                        collision = await detector.get_collision_details(
                            user_data.email
                        )
                        if collision["collision"]:
                            raise ValidationError(
                                message="Email collision detected",
                                field="email",
                                value=user_data.email,
                                details=collision,
                            )
                        # Normalize the new email
                        normalized_email = await detector.normalize_email_async(
                            user_data.email
                        )
                        update_fields["normalized_email"] = normalized_email
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
                    await session.commit()
                    await session.refresh(user)

                logger.info(
                    f"Updated user {user_id} with fields: {list(update_fields.keys())}"
                )
                return user

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            raise ValidationError(
                message=f"Failed to update user: {str(e)}",
                field="user_data",
                value=str(user_data),
            )

    async def update_user_by_external_auth_id(
        self,
        external_auth_id: str,
        user_data: UserUpdate,
        auth_provider: Optional[str] = None,
    ) -> User:
        """
        Update an existing user by external auth ID.

        Args:
            external_auth_id: External auth provider user ID
            user_data: User update data
            auth_provider: Authentication provider name (optional, will auto-detect if not provided)

        Returns:
            Updated user model instance

        Raises:
            NotFoundError: If user is not found
            ValidationError: If update data is invalid
        """
        try:
            # First get the user by external auth ID to get the internal ID
            if auth_provider:
                user = await self.get_user_by_external_auth_id(
                    external_auth_id, auth_provider
                )
            else:
                user = await self.get_user_by_external_auth_id_auto_detect(
                    external_auth_id
                )

            # Then use the existing update method with the internal ID
            if user.id is None:
                raise ValueError("user.id cannot be None")
            return await self.update_user(user.id, user_data)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Error updating user by external auth ID {external_auth_id}: {e}"
            )
            raise ValidationError(
                message=f"Failed to update user: {str(e)}",
                field="user_data",
                value=str(user_data),
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
            NotFoundError: If user is not found
            ValidationError: If onboarding data is invalid
        """
        try:
            async_session = get_async_session()
            async with async_session() as session:
                # Get user first
                result = await session.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()

                if user is None or user.deleted_at is not None:
                    raise NotFoundError(resource="User", identifier=str(user_id or ""))

                user.onboarding_completed = onboarding_data.onboarding_completed
                user.onboarding_step = onboarding_data.onboarding_step

                await session.commit()
                await session.refresh(user)

                logger.info(
                    f"Updated onboarding for user {user_id}: completed={onboarding_data.onboarding_completed}"
                )
                return user

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating onboarding for user {user_id}: {e}")
            raise ValidationError(
                message=f"Failed to update onboarding: {str(e)}",
                field="onboarding_data",
                value=str(onboarding_data),
            )

    async def update_user_onboarding_by_external_auth_id(
        self,
        external_auth_id: str,
        onboarding_data: UserOnboardingUpdate,
        auth_provider: Optional[str] = None,
    ) -> User:
        """
        Update user onboarding status by external auth ID.

        Args:
            external_auth_id: External auth provider user ID
            onboarding_data: Onboarding update data
            auth_provider: Authentication provider name (optional, will auto-detect if not provided)

        Returns:
            Updated user model instance

        Raises:
            NotFoundError: If user is not found
            ValidationError: If onboarding data is invalid
        """
        try:
            # First get the user by external auth ID to get the internal ID
            if auth_provider:
                user = await self.get_user_by_external_auth_id(
                    external_auth_id, auth_provider
                )
            else:
                user = await self.get_user_by_external_auth_id_auto_detect(
                    external_auth_id
                )

            # Then use the existing onboarding update method with the internal ID
            if user.id is None:
                raise ValueError("user.id cannot be None")
            return await self.update_user_onboarding(user.id, onboarding_data)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Error updating user onboarding by external auth ID {external_auth_id}: {e}"
            )
            raise ValidationError(
                message=f"Failed to update user onboarding: {str(e)}",
                field="onboarding_data",
                value=str(onboarding_data),
            )

    async def delete_user(self, user_id: int) -> UserDeleteResponse:
        """
        Soft delete a user.

        Args:
            user_id: Internal database ID of the user

        Returns:
            Deletion response with status

        Raises:
            NotFoundError: If user is not found
        """
        try:
            async_session = get_async_session()
            async with async_session() as session:
                # Get user first
                result = await session.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()

                if user is None or user.deleted_at is not None:
                    raise NotFoundError(resource="User", identifier=str(user_id or ""))

                # Perform soft delete
                deleted_at = datetime.now(timezone.utc)
                user.deleted_at = deleted_at

                await session.commit()

                logger.info(f"Soft deleted user {user_id}")

                return UserDeleteResponse(
                    success=True,
                    message=f"User {user_id} successfully deleted",
                    user_id=user_id,
                    external_auth_id=user.external_auth_id,
                    deleted_at=deleted_at,
                )

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            raise ValidationError(
                message=f"Failed to delete user: {str(e)}",
                field="user_id",
                value=str(user_id) if user_id is not None else "",
            )

    async def delete_user_by_external_auth_id(
        self, external_auth_id: str, auth_provider: Optional[str] = None
    ) -> UserDeleteResponse:
        """
        Delete (soft delete) a user by external auth ID.

        Args:
            external_auth_id: External auth provider user ID
            auth_provider: Authentication provider name (optional, will auto-detect if not provided)

        Returns:
            UserDeleteResponse with deletion details

        Raises:
            NotFoundError: If user is not found
        """
        try:
            # First get the user by external auth ID to get the internal ID
            if auth_provider:
                user = await self.get_user_by_external_auth_id(
                    external_auth_id, auth_provider
                )
            else:
                user = await self.get_user_by_external_auth_id_auto_detect(
                    external_auth_id
                )

            # Then use the existing delete method with the internal ID
            if user.id is None:
                raise ValueError("user.id cannot be None")
            return await self.delete_user(user.id)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Error deleting user by external auth ID {external_auth_id}: {e}"
            )
            value = (
                str(user.id)
                if "user" in locals() and hasattr(user, "id") and user.id is not None
                else ""
            )
            raise ValidationError(
                message=f"Failed to delete user: {str(e)}",
                field="user_id",
                value=value,
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
            async_session = get_async_session()
            async with async_session() as session:
                # Build base query for non-deleted users
                query = select(User).where(User.deleted_at is None)

                # Apply filters with simple comparisons for now
                if search_request.email:
                    query = query.where(User.email == search_request.email)

                if search_request.onboarding_completed is not None:
                    query = query.where(
                        User.onboarding_completed == search_request.onboarding_completed
                    )

                if search_request.query:
                    # Search by exact first_name match for simplicity
                    query = query.where(User.first_name == search_request.query)

                # Get total count
                count_query = select(func.count()).select_from(query.subquery())
                total_result = await session.execute(count_query)
                total = total_result.scalar() or 0

                # Apply pagination
                offset = (search_request.page - 1) * search_request.page_size
                paginated_query = query.offset(offset).limit(search_request.page_size)

                result = await session.execute(paginated_query)
                users = list(result.scalars().all())

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
            raise ValidationError(
                message=f"Failed to search users: {str(e)}",
                field="search_request",
                value=str(search_request),
            )

    async def get_user_profile(self, user_id: int) -> UserResponse:
        """
        Get user profile response.

        Args:
            user_id: Internal database ID of the user

        Returns:
            User response schema

        Raises:
            NotFoundError: If user is not found
        """
        user = await self.get_user_by_id(user_id)
        return UserResponse.from_orm(user)

    async def get_user_by_external_auth_id_auto_detect(
        self, external_auth_id: str
    ) -> User:
        """
        Get user by external auth ID with auto-detection of auth provider.

        Tries multiple auth providers to find the user.

        Args:
            external_auth_id: External auth provider user ID

        Returns:
            User model instance

        Raises:
            NotFoundError: If user is not found with any provider
        """
        # Try different auth providers in order of preference
        providers_to_try = [
            "nextauth",
            "clerk",
            "custom",
            "auth0",
            "firebase",
            "supabase",
        ]

        for provider in providers_to_try:
            try:
                user = await self.get_user_by_external_auth_id(
                    external_auth_id, provider
                )
                logger.info(f"Found user {external_auth_id} with provider {provider}")
                return user
            except NotFoundError:
                continue

        # If we get here, user was not found with any provider
        raise NotFoundError(resource="User", identifier=str(external_auth_id or ""))

    async def get_user_profile_by_external_auth_id(
        self, external_auth_id: str, auth_provider: Optional[str] = None
    ) -> UserResponse:
        """
        Get user profile response by external auth ID.

        Args:
            external_auth_id: External auth provider user ID
            auth_provider: Authentication provider name (optional, will auto-detect if not provided)

        Returns:
            User response schema

        Raises:
            NotFoundError: If user is not found
        """
        if auth_provider:
            user = await self.get_user_by_external_auth_id(
                external_auth_id, auth_provider
            )
        else:
            user = await self.get_user_by_external_auth_id_auto_detect(external_auth_id)
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
        except NotFoundError:
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
            async_session = get_async_session()
            async with async_session() as session:
                all_users = []
                for user_id in user_ids:
                    result = await session.execute(
                        select(User).where(User.id == user_id, User.deleted_at is None)
                    )
                    user = result.scalar_one_or_none()
                    if user:
                        all_users.append(user)

                logger.info(
                    f"Retrieved {len(all_users)} users from {len(user_ids)} requested IDs"
                )
                return all_users

        except Exception as e:
            logger.error(f"Error retrieving users by IDs: {e}")
            return []

    async def update_user_last_login(self, user_id: int) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: Internal database ID of the user

        Raises:
            NotFoundError: If user is not found
        """
        try:
            async_session = get_async_session()
            async with async_session() as session:
                # Get user first
                result = await session.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()

                if user is None or user.deleted_at is not None:
                    raise NotFoundError(resource="User", identifier=str(user_id or ""))

                # Update last login timestamp
                user.updated_at = datetime.now(timezone.utc)
                await session.commit()

                logger.info(f"Updated last login for user {user_id}")

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {e}")
            raise NotFoundError(
                resource="User", identifier=str(user_id) if user_id else ""
            )

    async def resolve_email_to_user_id(
        self, email_request: EmailResolutionRequest
    ) -> EmailResolutionResponse:
        """
        Resolve an email address to external_auth_id using email normalization.

        Args:
            email_request: Email resolution request containing the email to resolve

        Returns:
            EmailResolutionResponse: Contains external_auth_id and related user information

        Raises:
            NotFoundError: If no user is found for the resolved email
            ValidationError: If email format is invalid
        """
        try:
            detector = EmailCollisionDetector()

            # Use fast local normalization (all normalization is now local and instant)
            normalized_email = detector._simple_email_normalize(email_request.email)

            logger.info(
                f"Resolving email {email_request.email} (normalized: {normalized_email}) to external_auth_id"
            )

            # Query database by normalized email
            user = await self._find_user_by_normalized_email(normalized_email)

            if not user:
                raise NotFoundError(
                    resource="User", identifier=f"email:{email_request.email}"
                )

            # Create response with user information
            response = EmailResolutionResponse(
                external_auth_id=user.external_auth_id,
                email=user.email,  # Original email from database
                normalized_email=normalized_email,
                auth_provider=user.auth_provider,
            )

            logger.info(
                f"Successfully resolved email {email_request.email} to external_auth_id {user.external_auth_id}"
            )
            return response

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error resolving email {email_request.email}: {e}")
            raise ValidationError(
                message=f"Failed to resolve email: {str(e)}",
                field="email",
                value=email_request.email,
            )

    async def _find_user_by_normalized_email(
        self, normalized_email: str
    ) -> Optional[User]:
        """
        Find user by normalized email address.

        Args:
            normalized_email: Normalized email address to search for

        Returns:
            User model instance if found, None otherwise

        Raises:
            ValidationError: If multiple users found for the same normalized email (data integrity issue)
        """
        try:
            async_session = get_async_session()
            async with async_session() as session:
                # Query users by normalized_email
                result = await session.execute(
                    select(User).where(
                        User.normalized_email == normalized_email,
                        User.deleted_at == None,  # noqa: E711 # Only active users
                    )
                )
                users = result.scalars().all()

                if not users:
                    logger.debug(
                        f"No user found for normalized email: {normalized_email}"
                    )
                    return None

                if len(users) > 1:
                    # This shouldn't happen due to normalized_email uniqueness, but handle gracefully
                    logger.error(
                        f"Multiple users found for normalized email {normalized_email}: "
                        f"{[u.external_auth_id for u in users]}"
                    )
                    raise ValidationError(
                        message="Data integrity error: multiple users found for email",
                        field="normalized_email",
                        value=normalized_email,
                        details={
                            "user_count": len(users),
                            "user_ids": [u.external_auth_id for u in users],
                        },
                    )

                user = users[0]
                logger.debug(
                    f"Found user {user.external_auth_id} for normalized email: {normalized_email}"
                )
                return user

        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                f"Database error finding user by normalized email {normalized_email}: {e}"
            )
            return None


# Global user service instance
_user_service: UserService | None = None


def get_user_service() -> UserService:
    """Get UserService instance."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
