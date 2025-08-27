"""
User preferences service.

Business logic for managing user preferences including CRUD operations,
default value management, and preference validation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from services.api.v1.user.preferences import (
    AIPreferencesSchema,
    IntegrationPreferencesSchema,
    NotificationPreferencesSchema,
    PrivacyPreferencesSchema,
    UIPreferencesSchema,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)
from services.common.http_errors import NotFoundError, ServiceError, ValidationError
from services.common.logging_config import get_logger
from services.user.database import get_async_session
from services.user.models.preferences import UserPreferences
from services.user.models.user import User

# Set up logging
logger = get_logger(__name__)


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
            user_id: The user's external authentication ID (Clerk ID)

        Returns:
            UserPreferencesResponse object or None if not found

        Raises:
            NotFoundError: If user doesn't exist
            ServiceError: If database operation fails
        """
        try:
            logger.info("Getting user preferences", user_id=user_id)

            async_session = get_async_session()
            async with async_session() as session:
                # Check if user exists by external auth ID
                user_result = await session.execute(
                    select(User).where(User.external_auth_id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    logger.warning("User not found", user_id=user_id)
                    raise NotFoundError(resource="User", identifier=user_id)

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
                    if user.id is None:
                        raise ValueError(
                            "user.id cannot be None when creating preferences"
                        )
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
                timezone_mode=getattr(preferences, "timezone_mode", "auto"),
                manual_timezone=getattr(preferences, "manual_timezone", ""),
            )

        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Database error getting preferences", user_id=user_id, error=str(e)
            )
            raise ServiceError(message="Failed to retrieve preferences")
        except Exception as e:
            logger.error(
                "Unexpected error getting preferences", user_id=user_id, error=str(e)
            )
            raise ServiceError(message="Failed to retrieve preferences")

    @staticmethod
    async def update_user_preferences(
        user_id: str, preferences_update: UserPreferencesUpdate
    ) -> UserPreferencesResponse:
        """
        Update user preferences with partial update support.

        Args:
            user_id: The user's external authentication ID (Clerk ID)
            preferences_update: Preferences update data

        Returns:
            Updated UserPreferencesResponse

        Raises:
            NotFoundError: If user doesn't exist
            NotFoundError: If preferences don't exist
            ValidationError: If validation fails
            ServiceError: If database operation fails
        """
        try:
            logger.info("Updating user preferences", user_id=user_id)

            async_session = get_async_session()
            async with async_session() as session:
                # Check if user exists by external auth ID
                user_result = await session.execute(
                    select(User).where(User.external_auth_id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    logger.warning("User not found", user_id=user_id)
                    raise NotFoundError(resource="User", identifier=user_id)

                # Get existing preferences
                prefs_result = await session.execute(
                    select(UserPreferences).where(UserPreferences.user_id == user.id)
                )
                preferences = prefs_result.scalar_one_or_none()
                if not preferences:
                    logger.warning("Preferences not found", user_id=user_id)
                    raise NotFoundError(resource="Preferences", identifier=user_id)

            # Prepare update data
            update_data: dict[str, Any] = {}

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

            # New: Update timezone_mode and manual_timezone if present
            if preferences_update.timezone_mode is not None:
                update_data["timezone_mode"] = preferences_update.timezone_mode
                logger.debug("Updating timezone_mode", user_id=user_id)
            if preferences_update.manual_timezone is not None:
                update_data["manual_timezone"] = preferences_update.manual_timezone
                logger.debug("Updating manual_timezone", user_id=user_id)

            if not update_data:
                logger.warning("No preferences to update", user_id=user_id)
                # Return current preferences if nothing to update
                return await PreferencesService.get_user_preferences(user_id)

            # Update timestamp directly on the preferences model after updating fields
            async_session = get_async_session()
            async with async_session() as session:
                # Re-fetch preferences in the new session
                prefs_result = await session.execute(
                    select(UserPreferences).where(UserPreferences.user_id == user.id)
                )
                preferences = prefs_result.scalar_one()

                for key, value in update_data.items():
                    setattr(preferences, key, value)
                preferences.updated_at = datetime.now(timezone.utc)
                session.add(preferences)
                await session.commit()

            logger.info(
                "Successfully updated preferences",
                user_id=user_id,
                categories=list(update_data.keys()),
            )

            # Return updated preferences
            return await PreferencesService.get_user_preferences(user_id)

        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Database error updating preferences", user_id=user_id, error=str(e)
            )
            raise ServiceError(message="Failed to update preferences")
        except Exception as e:
            logger.error(
                "Unexpected error updating preferences", user_id=user_id, error=str(e)
            )
            raise ServiceError(message="Failed to update preferences")

    @staticmethod
    async def reset_user_preferences(
        user_id: str, categories: Optional[List[str]] = None
    ) -> UserPreferencesResponse:
        """
        Reset user preferences to default values.

        Args:
            user_id: The user's external authentication ID (Clerk ID)
            categories: List of categories to reset (None = reset all)

        Returns:
            Reset UserPreferencesResponse

        Raises:
            NotFoundError: If user doesn't exist
            NotFoundError: If preferences don't exist
            ValidationError: If validation fails
            ServiceError: If database operation fails
        """
        try:
            logger.info(
                "Resetting user preferences", user_id=user_id, categories=categories
            )

            async_session = get_async_session()
            async with async_session() as session:
                # Check if user exists by external auth ID
                user_result = await session.execute(
                    select(User).where(User.external_auth_id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    logger.warning("User not found", user_id=user_id)
                    raise NotFoundError(resource="User", identifier=user_id)

                # Get existing preferences
                prefs_result = await session.execute(
                    select(UserPreferences).where(UserPreferences.user_id == user.id)
                )
                preferences = prefs_result.scalar_one_or_none()
            if not preferences:
                logger.warning("Preferences not found", user_id=user_id)
                raise NotFoundError(resource="Preferences", identifier=user_id)

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
                        raise ValidationError(
                            message="Invalid category for reset_user_preferences",
                            field="categories",
                            value=categories,
                        )

            # Update timestamp directly on the preferences model after updating fields
            async_session = get_async_session()
            async with async_session() as session:
                # Re-fetch preferences in the new session
                prefs_result = await session.execute(
                    select(UserPreferences).where(UserPreferences.user_id == user.id)
                )
                preferences = prefs_result.scalar_one()

                for key, value in reset_data.items():
                    setattr(preferences, key, value)
                preferences.updated_at = datetime.now(timezone.utc)
                session.add(preferences)
                await session.commit()

            logger.info(
                "Successfully reset preferences", user_id=user_id, categories=categories
            )

            # Return reset preferences
            return await PreferencesService.get_user_preferences(user_id)

        except NotFoundError:
            raise
        except ValidationError:
            raise
        except SQLAlchemyError as e:
            logger.error(
                "Database error resetting preferences", user_id=user_id, error=str(e)
            )
            raise ServiceError(message="Failed to reset preferences")
        except Exception as e:
            logger.error(
                "Unexpected error resetting preferences", user_id=user_id, error=str(e)
            )
            raise ServiceError(message="Failed to reset preferences")


# Global preferences service instance
_preferences_service: PreferencesService | None = None


def get_preferences_service() -> PreferencesService:
    """Get the global preferences service instance, creating it if necessary."""
    global _preferences_service
    if _preferences_service is None:
        _preferences_service = PreferencesService()
    return _preferences_service
