"""
Webhook service for User Management Service.

Handles business logic for processing webhook events from external providers.
"""

import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, and_

from services.user.database import get_async_session
from services.user.exceptions import DatabaseError, WebhookProcessingError
from services.user.models.preferences import UserPreferences
from services.user.models.user import User
from services.user.schemas.webhook import (
    ClerkWebhookEvent,
    ClerkWebhookEventData,
)
from services.user.utils.email_collision import EmailCollisionDetector

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for processing webhook events."""

    def __init__(self):
        self.email_detector = EmailCollisionDetector()

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
        logger.info(f"Processing Clerk webhook: {event.type} for user {event.data.id}")

        try:
            if event.type == "user.created":
                result = await self._handle_user_created(event.data)
            elif event.type == "user.updated":
                result = await self._handle_user_updated(event.data)
            elif event.type == "user.deleted":
                result = await self._handle_user_deleted(event.data)
            else:
                raise WebhookProcessingError(f"Unsupported event type: {event.type}")

            return result

        except Exception as e:
            logger.error(f"Unexpected error processing webhook: {str(e)}")
            raise DatabaseError(f"Webhook processing failed: {str(e)}")

    async def process_user_created(self, user_data: dict) -> dict:
        """
        Process user.created event with raw data.

        Args:
            user_data: Raw user data from webhook

        Returns:
            dict: Processing result
        """
        # Convert raw data to ClerkWebhookEventData
        event_data = ClerkWebhookEventData(**user_data)
        return await self._handle_user_created(event_data)

    async def process_user_updated(self, user_data: dict) -> dict:
        """
        Process user.updated event with raw data.

        Args:
            user_data: Raw user data from webhook

        Returns:
            dict: Processing result
        """
        # Convert raw data to ClerkWebhookEventData
        event_data = ClerkWebhookEventData(**user_data)
        return await self._handle_user_updated(event_data)

    async def process_user_deleted(self, user_data: dict) -> dict:
        """
        Process user.deleted event with raw data.

        Args:
            user_data: Raw user data from webhook

        Returns:
            dict: Processing result
        """
        # Convert raw data to ClerkWebhookEventData
        event_data = ClerkWebhookEventData(**user_data)
        return await self._handle_user_deleted(event_data)

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
            async_session = get_async_session()
            async with async_session() as session:
                # Check if user already exists by external_auth_id (idempotency)
                result = await session.execute(
                    select(User).where(
                        and_(User.external_auth_id == user_data.id, User.auth_provider == "clerk")  # type: ignore[arg-type]
                    )
                )
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    # User exists, check if email changed
                    primary_email = user_data.primary_email
                    if not primary_email:
                        raise WebhookProcessingError(
                            "No primary email found in user data"
                        )

                    if existing_user.email != primary_email:
                        old_email = existing_user.email
                        existing_user.email = primary_email
                        existing_user.updated_at = datetime.now(timezone.utc)
                        await session.commit()
                        await session.refresh(existing_user)

                        logger.info(
                            f"Updated email for user {user_data.id}: {old_email} → {primary_email}"
                        )
                        return {
                            "action": "user_email_updated",
                            "user_id": existing_user.id,
                            "external_auth_id": user_data.id,
                            "old_email": old_email,
                            "new_email": primary_email,
                        }
                    else:
                        logger.info(
                            f"User {user_data.id} already exists with same email, skipping creation"
                        )
                        return {
                            "action": "user_already_exists",
                            "user_id": existing_user.id,
                            "external_auth_id": user_data.id,
                            "reason": "User already exists with same email",
                        }

                # Extract primary email
                primary_email = user_data.primary_email
                if not primary_email:
                    raise WebhookProcessingError("No primary email found in user data")

                # Check for email collision using the new EmailCollisionDetector
                collision_details = await self.email_detector.get_collision_details(
                    primary_email
                )

                if collision_details["collision"]:
                    logger.warning(
                        f"Email collision: {primary_email} exists with external_auth_id {collision_details['existing_user_id']}, but new user has external_auth_id {user_data.id}"
                    )
                    logger.debug("Raising HTTPException 409 for email collision!")
                    # Instead of updating the existing user's external_auth_id, raise a 409 Conflict
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "error": "EmailCollision",
                            "message": f"Email {primary_email} already exists with a different user.",
                        },
                    )

                # Normalize email for storage
                normalized_email = await self.email_detector.normalize_email_async(
                    primary_email
                )

                # Create User record
                user = User(
                    external_auth_id=user_data.id,
                    auth_provider="clerk",
                    email=primary_email,
                    normalized_email=normalized_email,
                    first_name=user_data.first_name,
                    last_name=user_data.last_name,
                    profile_image_url=user_data.image_url,
                    onboarding_completed=False,
                    onboarding_step="welcome",
                )

                session.add(user)
                await session.commit()
                await session.refresh(user)

                assert user.id is not None

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

        except HTTPException:
            raise
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
            async_session = get_async_session()
            async with async_session() as session:
                # Find existing user
                result = await session.execute(
                    select(User).where(
                        and_(User.external_auth_id == user_data.id, User.auth_provider == "clerk")  # type: ignore[arg-type]
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
                    # Check for email collision using the new EmailCollisionDetector
                    collision_details = await self.email_detector.get_collision_details(
                        user_data.primary_email
                    )

                    if collision_details["collision"]:
                        logger.warning(
                            f"Email collision on update: {user_data.primary_email} exists with external_auth_id {collision_details['existing_user_id']}, but update user has external_auth_id {user_data.id}"
                        )
                        raise WebhookProcessingError(
                            f"Email {user_data.primary_email} already exists with different external ID {collision_details['existing_user_id']}"
                        )

                    # Normalize the new email
                    normalized_email = await self.email_detector.normalize_email_async(
                        user_data.primary_email
                    )
                    update_data["email"] = user_data.primary_email
                    update_data["normalized_email"] = normalized_email

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
            async_session = get_async_session()
            async with async_session() as session:
                # Find existing user
                result = await session.execute(
                    select(User).where(
                        and_(User.external_auth_id == user_data.id, User.auth_provider == "clerk")  # type: ignore[arg-type]
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


# Global webhook service instance
_webhook_service: WebhookService | None = None


def get_webhook_service() -> WebhookService:
    """Get the global webhook service instance, creating it if necessary."""
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService()
    return _webhook_service
