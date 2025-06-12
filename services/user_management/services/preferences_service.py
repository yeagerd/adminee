"""
User preferences service.

Business logic for managing user preferences including CRUD operations,
default value management, and preference validation.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from services.user_management.database import get_async_session
from services.user_management.exceptions import (
    DatabaseException,
    PreferencesNotFoundException,
    UserNotFoundException,
    ValidationException,
)
from services.user_management.models.preferences import UserPreferences
from services.user_management.models.user import User
from services.user_management.schemas.preferences import (
    AIPreferencesSchema,
    IntegrationPreferencesSchema,
    NotificationPreferencesSchema,
    PrivacyPreferencesSchema,
    UIPreferencesSchema,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)

# Set up logging
logger = structlog.get_logger(__name__)


class PreferencesService:
    """Service for managing user preferences."""

    @staticmethod
    def _get_default_preferences() -> Dict:
        """Get default preference values for all categories."""
        ui_defaults = UIPreferencesSchema()
        notification_defaults = NotificationPreferencesSchema()
        ai_defaults = AIPreferencesSchema()
        integration_defaults = IntegrationPreferencesSchema()
        privacy_defaults = PrivacyPreferencesSchema()

        return {
            "ui_preferences": ui_defaults.model_dump(),
            "notification_preferences": notification_defaults.model_dump(),
            "ai_preferences": ai_defaults.model_dump(),
            "integration_preferences": integration_defaults.model_dump(),
            "privacy_preferences": privacy_defaults.model_dump(),
        }

    @staticmethod
    async def get_user_preferences(user_id: str) -> UserPreferencesResponse:
        """
        Get user preferences by user ID.

        Args:
            user_id: The user's Clerk ID

        Returns:
            UserPreferencesResponse object or None if not found

        Raises:
            UserNotFoundException: If user doesn't exist
            DatabaseException: If database operation fails
        """
        try:
            logger.info("Getting user preferences", user_id=user_id)

            async_session = get_async_session()
            async with async_session() as session:
                # Check if user exists
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    logger.warning("User not found", user_id=user_id)
                    raise UserNotFoundException(f"User {user_id} not found")

                # Get or create preferences
                prefs_result = await session.execute(
                    select(UserPreferences).where(UserPreferences.user_id == user.id)
                )
                preferences = prefs_result.scalar_one_or_none()
                if not preferences:
                    logger.info(
                        "Creating default preferences for user", user_id=user_id
                    )
                    # Create default preferences
                    default_prefs = PreferencesService._get_default_preferences()
                    preferences = UserPreferences(
                        user_id=user.id, version="1.0", **default_prefs
                    )
                    session.add(preferences)
                    await session.commit()
                    await session.refresh(preferences)

            # Convert to response schema
            return UserPreferencesResponse(
                user_id=user_id,
                version=preferences.version,
                ui=UIPreferencesSchema(**preferences.ui_preferences),
                notifications=NotificationPreferencesSchema(
                    **preferences.notification_preferences
                ),
                ai=AIPreferencesSchema(**preferences.ai_preferences),
                integrations=IntegrationPreferencesSchema(
                    **preferences.integration_preferences
                ),
                privacy=PrivacyPreferencesSchema(**preferences.privacy_preferences),
                created_at=preferences.created_at,
                updated_at=preferences.updated_at,
            )

        except UserNotFoundException:
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Database error getting preferences", user_id=user_id, error=str(e)
            )
            raise DatabaseException("Failed to retrieve preferences")
        except Exception as e:
            logger.error(
                "Unexpected error getting preferences", user_id=user_id, error=str(e)
            )
            raise DatabaseException("Failed to retrieve preferences")

    @staticmethod
    async def update_user_preferences(
        user_id: str, preferences_update: UserPreferencesUpdate
    ) -> UserPreferencesResponse:
        """
        Update user preferences with partial update support.

        Args:
            user_id: The user's Clerk ID
            preferences_update: Preferences update data

        Returns:
            Updated UserPreferencesResponse

        Raises:
            UserNotFoundException: If user doesn't exist
            PreferencesNotFoundException: If preferences don't exist
            ValidationException: If validation fails
            DatabaseException: If database operation fails
        """
        try:
            logger.info("Updating user preferences", user_id=user_id)

            async_session = get_async_session()
            async with async_session() as session:
                # Check if user exists
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    logger.warning("User not found", user_id=user_id)
                    raise UserNotFoundException(f"User {user_id} not found")

                # Get existing preferences
                prefs_result = await session.execute(
                    select(UserPreferences).where(UserPreferences.user_id == user.id)
                )
                preferences = prefs_result.scalar_one_or_none()
                if not preferences:
                    logger.warning("Preferences not found", user_id=user_id)
                    raise PreferencesNotFoundException(
                        f"Preferences not found for user {user_id}"
                    )

            # Prepare update data
            update_data = {}

            # Update only provided categories
            if preferences_update.ui is not None:
                update_data["ui_preferences"] = preferences_update.ui.model_dump()
                logger.debug("Updating UI preferences", user_id=user_id)

            if preferences_update.notifications is not None:
                update_data["notification_preferences"] = (
                    preferences_update.notifications.model_dump()
                )
                logger.debug("Updating notification preferences", user_id=user_id)

            if preferences_update.ai is not None:
                update_data["ai_preferences"] = preferences_update.ai.model_dump()
                logger.debug("Updating AI preferences", user_id=user_id)

            if preferences_update.integrations is not None:
                update_data["integration_preferences"] = (
                    preferences_update.integrations.model_dump()
                )
                logger.debug("Updating integration preferences", user_id=user_id)

            if preferences_update.privacy is not None:
                update_data["privacy_preferences"] = (
                    preferences_update.privacy.model_dump()
                )
                logger.debug("Updating privacy preferences", user_id=user_id)

            if not update_data:
                logger.warning("No preferences to update", user_id=user_id)
                # Return current preferences if nothing to update
                return await PreferencesService.get_user_preferences(user_id)

            # Update timestamp
            update_data["updated_at"] = datetime.now(timezone.utc)

            # Update preferences
            async_session = get_async_session()
            async with async_session() as session:
                # Re-fetch preferences in the new session
                prefs_result = await session.execute(
                    select(UserPreferences).where(UserPreferences.user_id == user.id)
                )
                preferences = prefs_result.scalar_one()

                for key, value in update_data.items():
                    setattr(preferences, key, value)
                session.add(preferences)
                await session.commit()

            logger.info(
                "Successfully updated preferences",
                user_id=user_id,
                categories=list(update_data.keys()),
            )

            # Return updated preferences
            return await PreferencesService.get_user_preferences(user_id)

        except (UserNotFoundException, PreferencesNotFoundException):
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Database error updating preferences", user_id=user_id, error=str(e)
            )
            raise DatabaseException("Failed to update preferences")
        except Exception as e:
            logger.error(
                "Unexpected error updating preferences", user_id=user_id, error=str(e)
            )
            raise DatabaseException("Failed to update preferences")

    @staticmethod
    async def reset_user_preferences(
        user_id: str, categories: Optional[List[str]] = None
    ) -> UserPreferencesResponse:
        """
        Reset user preferences to default values.

        Args:
            user_id: The user's Clerk ID
            categories: List of categories to reset (None = reset all)

        Returns:
            Reset UserPreferencesResponse

        Raises:
            UserNotFoundException: If user doesn't exist
            PreferencesNotFoundException: If preferences don't exist
            ValidationException: If validation fails
            DatabaseException: If database operation fails
        """
        try:
            logger.info(
                "Resetting user preferences", user_id=user_id, categories=categories
            )

            async_session = get_async_session()
            async with async_session() as session:
                # Check if user exists
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    logger.warning("User not found", user_id=user_id)
                    raise UserNotFoundException(f"User {user_id} not found")

                # Get existing preferences
                prefs_result = await session.execute(
                    select(UserPreferences).where(UserPreferences.user_id == user.id)
                )
                preferences = prefs_result.scalar_one_or_none()
            if not preferences:
                logger.warning("Preferences not found", user_id=user_id)
                raise PreferencesNotFoundException(
                    f"Preferences not found for user {user_id}"
                )

            # Get default values
            defaults = PreferencesService._get_default_preferences()

            # Prepare reset data
            reset_data = {}

            if categories is None:
                # Reset all categories
                reset_data.update(defaults)
                logger.debug("Resetting all preference categories", user_id=user_id)
            else:
                # Reset specific categories
                category_mapping = {
                    "ui": "ui_preferences",
                    "notifications": "notification_preferences",
                    "ai": "ai_preferences",
                    "integrations": "integration_preferences",
                    "privacy": "privacy_preferences",
                }

                for category in categories:
                    if category in category_mapping:
                        field_name = category_mapping[category]
                        reset_data[field_name] = defaults[field_name]
                        logger.debug(
                            "Resetting category", user_id=user_id, category=category
                        )
                    else:
                        logger.warning(
                            "Unknown category for reset",
                            user_id=user_id,
                            category=category,
                        )
                        raise ValidationException(
                            "categories",
                            category,
                            f"Unknown preference category: {category}",
                        )

            # Update timestamp
            reset_data["updated_at"] = datetime.now(timezone.utc)

            # Reset preferences
            async_session = get_async_session()
            async with async_session() as session:
                # Re-fetch preferences in the new session
                prefs_result = await session.execute(
                    select(UserPreferences).where(UserPreferences.user_id == user.id)
                )
                preferences = prefs_result.scalar_one()

                for key, value in reset_data.items():
                    setattr(preferences, key, value)
                session.add(preferences)
                await session.commit()

            logger.info(
                "Successfully reset preferences", user_id=user_id, categories=categories
            )

            # Return reset preferences
            return await PreferencesService.get_user_preferences(user_id)

        except (
            UserNotFoundException,
            PreferencesNotFoundException,
            ValidationException,
        ):
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Database error resetting preferences", user_id=user_id, error=str(e)
            )
            raise DatabaseException("Failed to reset preferences")
        except Exception as e:
            logger.error(
                "Unexpected error resetting preferences", user_id=user_id, error=str(e)
            )
            raise DatabaseException("Failed to reset preferences")


# Create service instance
preferences_service = PreferencesService()
