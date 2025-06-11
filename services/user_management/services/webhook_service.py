"""
Webhook service for User Management Service.

Handles business logic for processing webhook events from external providers.
"""

import logging
from datetime import datetime, timezone

from sqlmodel import select

from ..database import async_session
from ..exceptions import DatabaseError, WebhookProcessingError
from ..models import User, UserPreferences
from ..schemas.webhook import ClerkWebhookEvent, ClerkWebhookEventData

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for processing webhook events."""

    async def process_clerk_webhook(self, event: ClerkWebhookEvent) -> dict:
        """
        Process a Clerk webhook event.

        Args:
            event: The validated Clerk webhook event

        Returns:
            dict: Processing result with status and details

        Raises:
            WebhookProcessingError: If event processing fails
        """
        try:
            if event.type == "user.created":
                return await self._handle_user_created(event.data)
            elif event.type == "user.updated":
                return await self._handle_user_updated(event.data)
            elif event.type == "user.deleted":
                return await self._handle_user_deleted(event.data)
            else:
                raise WebhookProcessingError(f"Unsupported event type: {event.type}")

        except Exception as e:
            logger.error(f"Failed to process webhook event {event.type}: {str(e)}")
            raise WebhookProcessingError(f"Webhook processing failed: {str(e)}")

    async def _handle_user_created(self, user_data: ClerkWebhookEventData) -> dict:
        """
        Handle user.created event by creating User and UserPreferences records.

        Args:
            user_data: Clerk user data from webhook

        Returns:
            dict: Creation result
        """
        logger.info(f"Processing user.created event for user {user_data.id}")

        try:
            async with async_session() as session:
                # Check if user already exists (idempotency)
                result = await session.execute(
                    select(User).where(
                        User.external_auth_id == user_data.id,
                        User.auth_provider == "clerk",
                    )
                )
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    logger.info(
                        f"User {user_data.id} already exists, skipping creation"
                    )
                    return {
                        "action": "user_creation_skipped",
                        "user_id": user_data.id,
                        "reason": "User already exists",
                    }

                # Extract primary email
                primary_email = user_data.primary_email
                if not primary_email:
                    raise WebhookProcessingError("No primary email found in user data")

                # Create User record
                user = User(
                    external_auth_id=user_data.id,
                    auth_provider="clerk",
                    email=primary_email,
                    first_name=user_data.first_name,
                    last_name=user_data.last_name,
                    profile_image_url=user_data.image_url,
                    onboarding_completed=False,
                    onboarding_step="welcome",
                )

                session.add(user)
                await session.commit()
                await session.refresh(user)

                # Create default UserPreferences
                preferences = UserPreferences(
                    user_id=user.id,
                    # All other fields will use their default values
                )

                session.add(preferences)
                await session.commit()
                await session.refresh(preferences)

                logger.info(
                    f"Successfully created user {user_data.id} with preferences"
                )
                return {
                    "action": "user_created",
                    "user_id": user.id,  # Return the database ID
                    "external_auth_id": user_data.id,  # Also return the external auth ID
                    "preferences_id": preferences.id,
                }

        except Exception as e:
            logger.error(f"Failed to create user {user_data.id}: {str(e)}")
            raise DatabaseError(f"User creation failed: {str(e)}")

    async def _handle_user_updated(self, user_data: ClerkWebhookEventData) -> dict:
        """
        Handle user.updated event by updating User record.

        Args:
            user_data: Clerk user data from webhook

        Returns:
            dict: Update result
        """
        logger.info(f"Processing user.updated event for user {user_data.id}")

        try:
            async with async_session() as session:
                # Find existing user
                result = await session.execute(
                    select(User).where(
                        User.external_auth_id == user_data.id,
                        User.auth_provider == "clerk",
                    )
                )
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(
                        f"User {user_data.id} not found for update, creating new user"
                    )
                    # User doesn't exist, create it (handle out-of-order events)
                    return await self._handle_user_created(user_data)

                # Update user fields
                update_data = {}

                if user_data.primary_email and user_data.primary_email != user.email:
                    update_data["email"] = user_data.primary_email

                if (
                    user_data.first_name is not None
                    and user_data.first_name != user.first_name
                ):
                    update_data["first_name"] = user_data.first_name

                if (
                    user_data.last_name is not None
                    and user_data.last_name != user.last_name
                ):
                    update_data["last_name"] = user_data.last_name

                if (
                    user_data.image_url is not None
                    and user_data.image_url != user.profile_image_url
                ):
                    update_data["profile_image_url"] = user_data.image_url

                if update_data:
                    for field, value in update_data.items():
                        setattr(user, field, value)
                    user.updated_at = datetime.now(timezone.utc)
                    await session.commit()
                    await session.refresh(user)

                    logger.info(
                        f"Updated user {user_data.id} with fields: {list(update_data.keys())}"
                    )
                    return {
                        "action": "user_updated",
                        "user_id": user_data.id,
                        "updated_fields": list(update_data.keys()),
                    }
                else:
                    logger.info(f"No changes detected for user {user_data.id}")
                    return {"action": "user_no_changes", "user_id": user_data.id}

        except Exception as e:
            logger.error(f"Failed to update user {user_data.id}: {str(e)}")
            raise DatabaseError(f"User update failed: {str(e)}")

    async def _handle_user_deleted(self, user_data: ClerkWebhookEventData) -> dict:
        """
        Handle user.deleted event by soft deleting User and related records.

        Args:
            user_data: Clerk user data from webhook

        Returns:
            dict: Deletion result
        """
        logger.info(f"Processing user.deleted event for user {user_data.id}")

        try:
            async with async_session() as session:
                # Find existing user
                result = await session.execute(
                    select(User).where(
                        User.external_auth_id == user_data.id,
                        User.auth_provider == "clerk",
                    )
                )
                user = result.scalar_one_or_none()

                if not user:
                    logger.info(
                        f"User {user_data.id} not found for deletion, already removed"
                    )
                    return {
                        "action": "user_deletion_skipped",
                        "external_auth_id": user_data.id,
                        "reason": "User not found",
                    }

                # Soft delete by updating deleted_at timestamp
                user.deleted_at = datetime.now(timezone.utc)
                user.updated_at = datetime.now(timezone.utc)
                await session.commit()
                await session.refresh(user)

                logger.info(f"Successfully deleted user {user_data.id}")
                return {
                    "action": "user_deleted",
                    "user_id": user.id,  # Return the database ID
                    "external_auth_id": user_data.id,  # Also return the external auth ID
                }

        except Exception as e:
            logger.error(f"Failed to delete user {user_data.id}: {str(e)}")
            raise DatabaseError(f"User deletion failed: {str(e)}")

    def _is_event_duplicate(self, event_id: str, user_id: str) -> bool:
        """
        Check if webhook event has already been processed (idempotency).

        Args:
            event_id: Unique event identifier
            user_id: User ID from the event

        Returns:
            bool: True if event was already processed
        """
        # TODO: Implement idempotency tracking using Redis or database table
        # For now, we rely on database constraints and get_or_none checks
        return False


# Create service instance
webhook_service = WebhookService()
