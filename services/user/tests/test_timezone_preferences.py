"""
Test timezone preferences functionality in the user management service.

This module tests the timezone field we added to UserPreferences model
and ensures it integrates properly with the preferences API.
"""

from services.user.models.preferences import UserPreferences
from services.user.models.user import User
from services.user.tests.test_base import BaseUserManagementIntegrationTest


class TestTimezonePreferences(BaseUserManagementIntegrationTest):
    """Test timezone preferences functionality."""

    def test_create_user_preferences_with_timezone(self):
        """Test creating user preferences with timezone field."""
        # Create a test user first
        user = User(
            external_auth_id="test_user_timezone",
            auth_provider="microsoft",
            email="timezone@test.com",
            first_name="Timezone",
            last_name="User",
        )

        # Create preferences with timezone
        preferences = UserPreferences(
            user=user,
            timezone="America/New_York",
            ui_preferences={"theme": "dark"},
            notification_preferences={"email": True},
        )

        # Verify the timezone was set correctly
        assert preferences.timezone == "America/New_York"

    def test_user_preferences_default_timezone(self):
        """Test that UserPreferences defaults to UTC timezone."""
        # Create a test user first
        user = User(
            external_auth_id="test_user_default_tz",
            auth_provider="microsoft",
            email="defaulttz@test.com",
            first_name="Default",
            last_name="Timezone",
        )

        # Create preferences without specifying timezone
        preferences = UserPreferences(user=user, ui_preferences={"theme": "light"})

        # Verify the default timezone is UTC
        assert preferences.timezone == "UTC"

    def test_timezone_field_validation(self):
        """Test that timezone field accepts valid IANA timezone strings."""
        # Create a test user first
        user = User(
            external_auth_id="test_user_validation",
            auth_provider="microsoft",
            email="validation@test.com",
            first_name="Validation",
            last_name="User",
        )

        # Test various valid timezone strings
        valid_timezones = [
            "UTC",
            "America/New_York",
            "America/Los_Angeles",
            "Europe/London",
            "Asia/Tokyo",
            "Australia/Sydney",
            "America/Chicago",
            "Europe/Paris",
        ]

        for timezone_str in valid_timezones:
            preferences = UserPreferences(user=user, timezone=timezone_str)
            assert preferences.timezone == timezone_str


class TestTimezonePreferencesAPI(BaseUserManagementIntegrationTest):
    """Test timezone preferences through the API endpoints."""

    def setup_method(self):
        """Set up test client and authentication."""
        super().setup_method()
        self.headers = {
            "X-API-Key": "test-frontend-key",
            "Content-Type": "application/json",
        }

    def test_preferences_timezone_in_schema(self):
        """Test that timezone fields are included in the preferences schema (top-level, not UI)."""
        from datetime import datetime, timezone

        from services.api.v1.user.preferences import (
            AIPreferencesSchema,
            IntegrationPreferencesSchema,
            NotificationPreferencesSchema,
            PrivacyPreferencesSchema,
            UIPreferencesSchema,
            UserPreferencesResponse,
        )

        # Test that the new timezone fields exist and have correct defaults
        prefs = UserPreferencesResponse(
            user_id="test",
            version="1.0",
            ui=UIPreferencesSchema(),
            notifications=NotificationPreferencesSchema(),
            ai=AIPreferencesSchema(),
            integrations=IntegrationPreferencesSchema(),
            privacy=PrivacyPreferencesSchema(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert hasattr(prefs, "timezone_mode")
        assert hasattr(prefs, "manual_timezone")
        assert prefs.timezone_mode == "auto"
        assert prefs.manual_timezone == ""

        # Optionally, test with explicit values
        prefs2 = UserPreferencesResponse(
            user_id="test2",
            version="1.0",
            ui=UIPreferencesSchema(),
            notifications=NotificationPreferencesSchema(),
            ai=AIPreferencesSchema(),
            integrations=IntegrationPreferencesSchema(),
            privacy=PrivacyPreferencesSchema(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            timezone_mode="manual",
            manual_timezone="America/New_York",
        )
        assert prefs2.timezone_mode == "manual"
        assert prefs2.manual_timezone == "America/New_York"

        # The UI schema no longer has a timezone field
        ui_prefs = UIPreferencesSchema()
        assert not hasattr(ui_prefs, "timezone")


class TestTimezonePreferencesIntegration:
    """Test integration between timezone preferences and other services."""

    def test_timezone_preference_format_validation(self):
        """Test that timezone preferences accept valid IANA timezone formats."""
        from services.user.models.preferences import UserPreferences

        # Test various timezone formats that should be valid
        valid_timezones = [
            "UTC",
            "GMT",
            "America/New_York",
            "America/Los_Angeles",
            "America/Chicago",
            "America/Denver",
            "Europe/London",
            "Europe/Paris",
            "Europe/Berlin",
            "Asia/Tokyo",
            "Asia/Shanghai",
            "Australia/Sydney",
            "Pacific/Auckland",
        ]

        for tz in valid_timezones:
            # Should not raise an exception
            preferences = UserPreferences(user_id=1, timezone=tz)
            assert preferences.timezone == tz

    def test_timezone_field_accepts_common_values(self):
        """Test that timezone field accepts common timezone values."""
        from services.user.models.preferences import UserPreferences

        # Test with common timezone values
        common_timezones = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"]

        for tz in common_timezones:
            preferences = UserPreferences(user_id=1, timezone=tz)
            assert preferences.timezone == tz


class TestTimezoneModePreferences(BaseUserManagementIntegrationTest):
    """Test new timezone_mode/manual_timezone logic."""

    def test_default_timezone_mode(self):
        user = User(
            external_auth_id="tzmode_default",
            auth_provider="microsoft",
            email="tzmode_default@test.com",
        )
        preferences = UserPreferences(user=user)
        assert preferences.timezone_mode == "auto"
        assert preferences.manual_timezone == ""

    def test_manual_timezone_override(self):
        user = User(
            external_auth_id="tzmode_manual",
            auth_provider="microsoft",
            email="tzmode_manual@test.com",
        )
        preferences = UserPreferences(
            user=user, timezone_mode="manual", manual_timezone="Europe/Paris"
        )
        assert preferences.timezone_mode == "manual"
        assert preferences.manual_timezone == "Europe/Paris"

    def test_api_update_and_retrieve_timezone_mode(self):
        # Simulate API update and retrieval
        user = User(
            external_auth_id="tzmode_api",
            auth_provider="microsoft",
            email="tzmode_api@test.com",
        )
        preferences = UserPreferences(user=user)
        preferences.timezone_mode = "manual"
        preferences.manual_timezone = "Asia/Tokyo"
        assert preferences.timezone_mode == "manual"
        assert preferences.manual_timezone == "Asia/Tokyo"

    def test_fallback_to_auto_if_manual_not_set(self):
        user = User(
            external_auth_id="tzmode_fallback",
            auth_provider="microsoft",
            email="tzmode_fallback@test.com",
        )
        preferences = UserPreferences(
            user=user, timezone_mode="auto", manual_timezone=""
        )
        # Simulate frontend logic
        browser_tz = "America/Los_Angeles"
        effective_tz = (
            preferences.manual_timezone
            if preferences.timezone_mode == "manual" and preferences.manual_timezone
            else browser_tz
        )
        assert effective_tz == browser_tz
