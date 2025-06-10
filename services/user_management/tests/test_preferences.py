"""
Unit tests for user preferences functionality.

Tests preferences service, router endpoints, validation,
partial updates, and default value handling.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ..auth.clerk import get_current_user
from ..exceptions import (
    PreferencesNotFoundException,
    UserNotFoundException,
    ValidationException,
)
from ..main import app
from ..schemas.preferences import (
    AIPreferencesSchema,
    IntegrationPreferencesSchema,
    Language,
    NotificationPreferencesSchema,
    PreferencesResetRequest,
    PrivacyPreferencesSchema,
    ThemeMode,
    UIPreferencesSchema,
    UserPreferencesResponse,
    UserPreferencesUpdate,
)
from ..services.preferences_service import PreferencesService


class TestPreferencesSchemas:
    """Test preferences Pydantic schemas."""

    def test_ui_preferences_schema_defaults(self):
        """Test UI preferences schema with default values."""
        prefs = UIPreferencesSchema()

        assert prefs.theme == ThemeMode.SYSTEM
        assert prefs.language == Language.EN
        assert prefs.compact_mode is False
        assert prefs.show_tooltips is True

    def test_ui_preferences_schema_custom_values(self):
        """Test UI preferences schema with custom values."""
        prefs = UIPreferencesSchema(
            theme=ThemeMode.DARK,
            language=Language.ES,
            compact_mode=True,
            show_tooltips=False,
        )

        assert prefs.theme == ThemeMode.DARK
        assert prefs.language == Language.ES
        assert prefs.compact_mode is True
        assert prefs.show_tooltips is False

    def test_notification_preferences_schema_time_validation(self):
        """Test notification preferences time format validation."""
        # Valid time formats
        prefs = NotificationPreferencesSchema(
            quiet_hours_start="22:00", quiet_hours_end="08:00"
        )
        assert prefs.quiet_hours_start == "22:00"
        assert prefs.quiet_hours_end == "08:00"

        # Invalid time format should raise validation error
        with pytest.raises(ValueError, match="Time must be in HH:MM format"):
            NotificationPreferencesSchema(quiet_hours_start="25:00")

        with pytest.raises(ValueError, match="Time must be in HH:MM format"):
            NotificationPreferencesSchema(quiet_hours_end="12:60")

    def test_ai_preferences_schema_validation(self):
        """Test AI preferences schema validation."""
        # Valid temperature range
        prefs = AIPreferencesSchema(temperature=0.5, max_tokens=1000)
        assert prefs.temperature == 0.5
        assert prefs.max_tokens == 1000

        # Invalid temperature range
        with pytest.raises(ValueError):
            AIPreferencesSchema(temperature=1.5)  # > 1.0

        with pytest.raises(ValueError):
            AIPreferencesSchema(temperature=-0.1)  # < 0.0

        # Invalid token range
        with pytest.raises(ValueError):
            AIPreferencesSchema(max_tokens=50)  # < 100

        with pytest.raises(ValueError):
            AIPreferencesSchema(max_tokens=10000)  # > 8000

    def test_ai_preferences_response_style_validation(self):
        """Test AI preferences response style validation."""
        # Valid styles
        valid_styles = ["concise", "balanced", "detailed", "creative", "technical"]
        for style in valid_styles:
            prefs = AIPreferencesSchema(response_style=style)
            assert prefs.response_style == style

        # Invalid style
        with pytest.raises(ValidationError, match="Must be one of"):
            AIPreferencesSchema(response_style="invalid")

    def test_user_preferences_update_partial(self):
        """Test partial preferences update."""
        update = UserPreferencesUpdate(
            ui=UIPreferencesSchema(theme=ThemeMode.DARK),
            notifications=NotificationPreferencesSchema(email_notifications=False),
        )

        assert update.ui is not None
        assert update.notifications is not None
        assert update.ai is None
        assert update.integrations is None
        assert update.privacy is None

    def test_preferences_reset_request_validation(self):
        """Test preferences reset request validation."""
        # Valid categories
        reset_req = PreferencesResetRequest(categories=["ui", "notifications"])
        assert "ui" in reset_req.categories
        assert "notifications" in reset_req.categories

        # Invalid category
        with pytest.raises(ValueError, match="Invalid category"):
            PreferencesResetRequest(categories=["invalid_category"])

    def test_user_preferences_response_version_field(self):
        """Test that UserPreferencesResponse includes version field."""
        response = UserPreferencesResponse(
            user_id="user_123",
            version="1.0",
            ui=UIPreferencesSchema(),
            notifications=NotificationPreferencesSchema(),
            ai=AIPreferencesSchema(),
            integrations=IntegrationPreferencesSchema(),
            privacy=PrivacyPreferencesSchema(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert response.version == "1.0"
        assert response.user_id == "user_123"

    def test_user_preferences_response_default_version(self):
        """Test default version value in UserPreferencesResponse."""
        response = UserPreferencesResponse(
            user_id="user_123",
            ui=UIPreferencesSchema(),
            notifications=NotificationPreferencesSchema(),
            ai=AIPreferencesSchema(),
            integrations=IntegrationPreferencesSchema(),
            privacy=PrivacyPreferencesSchema(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert response.version == "1.0"  # Default version


class TestPreferencesService:
    """Test preferences service business logic."""

    @pytest.fixture
    def mock_user(self):
        """Mock user object."""
        user = Mock()
        user.id = 1
        user.clerk_id = "user_123"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_preferences(self):
        """Mock preferences object."""
        prefs = Mock()
        prefs.user_id = 1
        prefs.version = "1.0"  # Add version field
        prefs.ui_preferences = {
            "theme": "system",
            "language": "en",
            "compact_mode": False,
            "show_tooltips": True,
            "animations_enabled": True,
        }
        prefs.notification_preferences = {
            "email_notifications": True,
            "push_notifications": True,
            "summary_frequency": "daily",
        }
        prefs.ai_preferences = {
            "preferred_provider": "openai",
            "auto_summarization": True,
            "smart_suggestions": True,
        }
        prefs.integration_preferences = {
            "auto_sync": True,
            "google_drive_enabled": False,
        }
        prefs.privacy_preferences = {"data_collection": True, "analytics": True}
        prefs.created_at = datetime.utcnow()
        prefs.updated_at = datetime.utcnow()
        prefs.update = AsyncMock()
        return prefs

    @pytest.mark.asyncio
    async def test_get_user_preferences_success(self, mock_user, mock_preferences):
        """Test successful retrieval of user preferences."""
        with (
            patch(
                "services.user_management.services.preferences_service.User"
            ) as mock_user_model,
            patch(
                "services.user_management.services.preferences_service.UserPreferences"
            ) as mock_prefs_model,
        ):

            mock_user_model.objects.get_or_none = AsyncMock(return_value=mock_user)
            mock_prefs_model.objects.get_or_none = AsyncMock(
                return_value=mock_preferences
            )

            result = await PreferencesService.get_user_preferences("user_123")

            assert result is not None
            assert result.user_id == "user_123"
            assert result.version == "1.0"
            assert result.ui.theme == ThemeMode.SYSTEM
            assert result.notifications.email_notifications is True

    @pytest.mark.asyncio
    async def test_get_user_preferences_user_not_found(self):
        """Test preferences retrieval when user doesn't exist."""
        with patch(
            "services.user_management.services.preferences_service.User"
        ) as mock_user_model:
            mock_user_model.objects.get_or_none = AsyncMock(return_value=None)

            with pytest.raises(UserNotFoundException):
                await PreferencesService.get_user_preferences("nonexistent")

    @pytest.mark.asyncio
    async def test_get_user_preferences_create_defaults(self, mock_user):
        """Test automatic creation of default preferences."""
        with (
            patch(
                "services.user_management.services.preferences_service.User"
            ) as mock_user_model,
            patch(
                "services.user_management.services.preferences_service.UserPreferences"
            ) as mock_prefs_model,
        ):

            mock_user_model.objects.get_or_none = AsyncMock(return_value=mock_user)
            mock_prefs_model.objects.get_or_none = AsyncMock(return_value=None)

            created_prefs = Mock()
            created_prefs.user_id = 1
            created_prefs.version = "1.0"  # Add version field
            created_prefs.ui_preferences = UIPreferencesSchema().model_dump()
            created_prefs.notification_preferences = (
                NotificationPreferencesSchema().model_dump()
            )
            created_prefs.ai_preferences = AIPreferencesSchema().model_dump()
            created_prefs.integration_preferences = (
                IntegrationPreferencesSchema().model_dump()
            )
            created_prefs.privacy_preferences = PrivacyPreferencesSchema().model_dump()
            created_prefs.created_at = datetime.utcnow()
            created_prefs.updated_at = datetime.utcnow()

            mock_prefs_model.objects.create = AsyncMock(return_value=created_prefs)

            result = await PreferencesService.get_user_preferences("user_123")

            assert result is not None
            # Verify that version is set when creating defaults
            mock_prefs_model.objects.create.assert_called_once()
            create_call_args = mock_prefs_model.objects.create.call_args
            assert create_call_args[1]["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_update_user_preferences_success(self, mock_user, mock_preferences):
        """Test successful preferences update."""
        with (
            patch(
                "services.user_management.services.preferences_service.User"
            ) as mock_user_model,
            patch(
                "services.user_management.services.preferences_service.UserPreferences"
            ) as mock_prefs_model,
        ):

            mock_user_model.objects.get_or_none = AsyncMock(return_value=mock_user)
            mock_prefs_model.objects.get_or_none = AsyncMock(
                return_value=mock_preferences
            )

            # Mock the get_user_preferences method for return value
            with patch.object(PreferencesService, "get_user_preferences") as mock_get:
                mock_response = UserPreferencesResponse(
                    user_id="user_123",
                    ui=UIPreferencesSchema(theme=ThemeMode.DARK),
                    notifications=NotificationPreferencesSchema(),
                    ai=AIPreferencesSchema(),
                    integrations=IntegrationPreferencesSchema(),
                    privacy=PrivacyPreferencesSchema(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                mock_get.return_value = mock_response

                update_data = UserPreferencesUpdate(
                    ui=UIPreferencesSchema(theme=ThemeMode.DARK)
                )

                result = await PreferencesService.update_user_preferences(
                    "user_123", update_data
                )

                assert result is not None
                mock_preferences.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_preferences_no_changes(
        self, mock_user, mock_preferences
    ):
        """Test preferences update with no changes."""
        with (
            patch(
                "services.user_management.services.preferences_service.User"
            ) as mock_user_model,
            patch(
                "services.user_management.services.preferences_service.UserPreferences"
            ) as mock_prefs_model,
        ):

            mock_user_model.objects.get_or_none = AsyncMock(return_value=mock_user)
            mock_prefs_model.objects.get_or_none = AsyncMock(
                return_value=mock_preferences
            )

            with patch.object(PreferencesService, "get_user_preferences") as mock_get:
                mock_response = UserPreferencesResponse(
                    user_id="user_123",
                    ui=UIPreferencesSchema(),
                    notifications=NotificationPreferencesSchema(),
                    ai=AIPreferencesSchema(),
                    integrations=IntegrationPreferencesSchema(),
                    privacy=PrivacyPreferencesSchema(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                mock_get.return_value = mock_response

                # Empty update
                update_data = UserPreferencesUpdate()

                result = await PreferencesService.update_user_preferences(
                    "user_123", update_data
                )

                assert result is not None
                # Should not call update if no changes
                mock_preferences.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_reset_user_preferences_all_categories(
        self, mock_user, mock_preferences
    ):
        """Test resetting all preference categories."""
        with (
            patch(
                "services.user_management.services.preferences_service.User"
            ) as mock_user_model,
            patch(
                "services.user_management.services.preferences_service.UserPreferences"
            ) as mock_prefs_model,
        ):

            mock_user_model.objects.get_or_none = AsyncMock(return_value=mock_user)
            mock_prefs_model.objects.get_or_none = AsyncMock(
                return_value=mock_preferences
            )

            with patch.object(PreferencesService, "get_user_preferences") as mock_get:
                mock_response = UserPreferencesResponse(
                    user_id="user_123",
                    ui=UIPreferencesSchema(),
                    notifications=NotificationPreferencesSchema(),
                    ai=AIPreferencesSchema(),
                    integrations=IntegrationPreferencesSchema(),
                    privacy=PrivacyPreferencesSchema(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                mock_get.return_value = mock_response

                result = await PreferencesService.reset_user_preferences("user_123")

                assert result is not None
                mock_preferences.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_user_preferences_specific_categories(
        self, mock_user, mock_preferences
    ):
        """Test resetting specific preference categories."""
        with (
            patch(
                "services.user_management.services.preferences_service.User"
            ) as mock_user_model,
            patch(
                "services.user_management.services.preferences_service.UserPreferences"
            ) as mock_prefs_model,
        ):

            mock_user_model.objects.get_or_none = AsyncMock(return_value=mock_user)
            mock_prefs_model.objects.get_or_none = AsyncMock(
                return_value=mock_preferences
            )

            with patch.object(PreferencesService, "get_user_preferences") as mock_get:
                mock_response = UserPreferencesResponse(
                    user_id="user_123",
                    ui=UIPreferencesSchema(),
                    notifications=NotificationPreferencesSchema(),
                    ai=AIPreferencesSchema(),
                    integrations=IntegrationPreferencesSchema(),
                    privacy=PrivacyPreferencesSchema(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                mock_get.return_value = mock_response

                categories = ["ui", "notifications"]
                result = await PreferencesService.reset_user_preferences(
                    "user_123", categories
                )

                assert result is not None
                mock_preferences.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_user_preferences_invalid_category(
        self, mock_user, mock_preferences
    ):
        """Test resetting with invalid category."""
        with (
            patch(
                "services.user_management.services.preferences_service.User"
            ) as mock_user_model,
            patch(
                "services.user_management.services.preferences_service.UserPreferences"
            ) as mock_prefs_model,
        ):

            mock_user_model.objects.get_or_none = AsyncMock(return_value=mock_user)
            mock_prefs_model.objects.get_or_none = AsyncMock(
                return_value=mock_preferences
            )

            categories = ["invalid_category"]

            with pytest.raises(ValidationException):
                await PreferencesService.reset_user_preferences("user_123", categories)

    def test_version_field_for_migration_support(self):
        """Test that version field supports future migration scenarios."""
        # Test that different version values are handled correctly
        response_v1 = UserPreferencesResponse(
            user_id="user_123",
            version="1.0",
            ui=UIPreferencesSchema(),
            notifications=NotificationPreferencesSchema(),
            ai=AIPreferencesSchema(),
            integrations=IntegrationPreferencesSchema(),
            privacy=PrivacyPreferencesSchema(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        response_v2 = UserPreferencesResponse(
            user_id="user_123",
            version="2.0",
            ui=UIPreferencesSchema(),
            notifications=NotificationPreferencesSchema(),
            ai=AIPreferencesSchema(),
            integrations=IntegrationPreferencesSchema(),
            privacy=PrivacyPreferencesSchema(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert response_v1.version == "1.0"
        assert response_v2.version == "2.0"

        # Verify that version field can be used for migration logic
        assert response_v1.version != response_v2.version


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_auth_dependencies():
    """Mock authentication dependencies."""

    async def mock_get_current_user():
        return "user_123"

    # Override dependencies in the FastAPI app
    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Mock the verify_user_ownership function
    with patch(
        "services.user_management.routers.preferences.verify_user_ownership"
    ) as mock_verify:
        mock_verify.return_value = None  # No exception means authorized

        yield {
            "get_user": mock_get_current_user,
            "verify": mock_verify,
        }

    # Clean up
    app.dependency_overrides.clear()


class TestPreferencesEndpoints:
    """Test preferences API endpoints."""

    def test_get_preferences_success(self, client, mock_auth_dependencies):
        """Test successful preferences retrieval."""
        mock_response = UserPreferencesResponse(
            user_id="user_123",
            ui=UIPreferencesSchema(),
            notifications=NotificationPreferencesSchema(),
            ai=AIPreferencesSchema(),
            integrations=IntegrationPreferencesSchema(),
            privacy=PrivacyPreferencesSchema(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        with patch(
            "services.user_management.services.preferences_service.preferences_service.get_user_preferences"
        ) as mock_service:
            mock_service.return_value = mock_response

            response = client.get(
                "/users/user_123/preferences/",
                headers={"Authorization": "Bearer valid-token"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["user_id"] == "user_123"
            assert "version" in data
            assert data["version"] == "1.0"

    def test_get_preferences_not_found(self, client, mock_auth_dependencies):
        """Test preferences not found."""
        with patch(
            "services.user_management.services.preferences_service.preferences_service.get_user_preferences"
        ) as mock_service:
            mock_service.side_effect = PreferencesNotFoundException("user_123")

            response = client.get(
                "/users/user_123/preferences/",
                headers={"Authorization": "Bearer valid-token"},
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_preferences_success(self, client, mock_auth_dependencies):
        """Test successful preferences update."""
        mock_response = UserPreferencesResponse(
            user_id="user_123",
            ui=UIPreferencesSchema(theme=ThemeMode.DARK),
            notifications=NotificationPreferencesSchema(),
            ai=AIPreferencesSchema(),
            integrations=IntegrationPreferencesSchema(),
            privacy=PrivacyPreferencesSchema(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        with patch(
            "services.user_management.services.preferences_service.preferences_service.update_user_preferences"
        ) as mock_service:
            mock_service.return_value = mock_response

            update_data = {"ui": {"theme": "dark"}}

            response = client.put(
                "/users/user_123/preferences/",
                json=update_data,
                headers={"Authorization": "Bearer valid-token"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["ui"]["theme"] == "dark"

    def test_update_preferences_validation_error(self, client, mock_auth_dependencies):
        """Test preferences update with validation error."""
        with patch(
            "services.user_management.services.preferences_service.preferences_service.update_user_preferences"
        ) as mock_service:
            mock_service.side_effect = ValidationException(
                "theme", "invalid", "Invalid theme value"
            )

            update_data = {"ui": {"theme": "invalid"}}

            response = client.put(
                "/users/user_123/preferences/",
                json=update_data,
                headers={"Authorization": "Bearer valid-token"},
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_reset_preferences_success(self, client, mock_auth_dependencies):
        """Test successful preferences reset."""
        mock_response = UserPreferencesResponse(
            user_id="user_123",
            ui=UIPreferencesSchema(),
            notifications=NotificationPreferencesSchema(),
            ai=AIPreferencesSchema(),
            integrations=IntegrationPreferencesSchema(),
            privacy=PrivacyPreferencesSchema(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        with patch(
            "services.user_management.services.preferences_service.preferences_service.reset_user_preferences"
        ) as mock_service:
            mock_service.return_value = mock_response

            reset_data = {"categories": ["ui", "notifications"]}

            response = client.post(
                "/users/user_123/preferences/reset",
                json=reset_data,
                headers={"Authorization": "Bearer valid-token"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["user_id"] == "user_123"

    def test_reset_preferences_invalid_category(self, client, mock_auth_dependencies):
        """Test preferences reset with invalid category."""
        with patch(
            "services.user_management.services.preferences_service.preferences_service.reset_user_preferences"
        ) as mock_service:
            mock_service.side_effect = ValidationException(
                "categories", ["invalid"], "Invalid category"
            )

            reset_data = {"categories": ["invalid"]}

            response = client.post(
                "/users/user_123/preferences/reset",
                json=reset_data,
                headers={"Authorization": "Bearer valid-token"},
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
