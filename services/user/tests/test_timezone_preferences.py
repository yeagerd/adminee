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
            auth_provider="clerk",
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
            auth_provider="clerk",
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
            auth_provider="clerk",
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
        """Test that timezone field is included in the preferences schema."""
        from services.user.schemas.preferences import Timezone, UIPreferencesSchema

        # Test UI preferences schema which contains timezone
        ui_prefs = UIPreferencesSchema(timezone=Timezone.US_EASTERN)
        assert ui_prefs.timezone == "America/New_York"

        # Test with different timezone
        ui_prefs_pacific = UIPreferencesSchema(timezone=Timezone.US_PACIFIC)
        assert ui_prefs_pacific.timezone == "America/Los_Angeles"


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
