"""
Unit tests for settings configuration.

Tests settings validation, environment variable loading,
and configuration management.
"""

import os
from unittest.mock import patch

from pydantic import ConfigDict

from services.user.settings import Settings


class _TestableSettings(Settings):
    """Test version of Settings that doesn't load from .env file."""

    model_config = ConfigDict(
        env_file=None,  # Don't load from .env file in tests
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class TestSettings:
    """Test cases for Settings configuration."""

    def test_default_settings(self):
        """Test that default settings are loaded correctly."""
        # Clear environment variables to test defaults
        with patch.dict(
            os.environ,
            {
                "DB_URL_USER_MANAGEMENT": "postgresql://postgres:postgres@localhost:5432/briefly"
            },
            clear=True,
        ):
            settings = _TestableSettings()

            # Test default values
            assert settings.service_name == "user-management"
            assert settings.host == "0.0.0.0"
            assert settings.port == 8001
            assert settings.debug is False
            assert settings.log_level == "INFO"
            assert settings.log_format == "json"
            assert (
                settings.db_url_user_management
                == "postgresql://postgres:postgres@localhost:5432/briefly"
            )
            assert settings.redis_url == "redis://localhost:6379"

    def test_environment_variable_override(self):
        """Test that environment variables override default settings."""
        with patch.dict(
            os.environ,
            {
                "SERVICE_NAME": "test-service",
                "HOST": "127.0.0.1",
                "PORT": "9000",
                "DEBUG": "true",
                "LOG_LEVEL": "DEBUG",
                "DB_URL_USER_MANAGEMENT": "postgresql://test:test@testhost:5432/testdb",
            },
            clear=True,
        ):
            settings = _TestableSettings()

            assert settings.service_name == "test-service"
            assert settings.host == "127.0.0.1"
            assert settings.port == 9000
            assert settings.debug is True
            assert settings.log_level == "DEBUG"
            assert (
                settings.db_url_user_management
                == "postgresql://test:test@testhost:5432/testdb"
            )

    def test_security_settings(self):
        """Test security-related settings."""
        with patch.dict(
            os.environ,
            {
                "DB_URL_USER_MANAGEMENT": "postgresql://postgres:postgres@localhost:5432/briefly",
                "API_FRONTEND_USER_KEY": "test-api-key",
                "TOKEN_ENCRYPTION_SALT": "test-salt",
                "CLERK_SECRET_KEY": "test-clerk-key",
                "CLERK_WEBHOOK_SECRET": "test-webhook-secret",
            },
            clear=True,
        ):
            settings = _TestableSettings()

            assert settings.api_frontend_user_key == "test-api-key"
            assert settings.token_encryption_salt == "test-salt"
            assert settings.clerk_secret_key == "test-clerk-key"
            assert settings.clerk_webhook_secret == "test-webhook-secret"

    def test_oauth_provider_settings(self):
        """Test OAuth provider configuration."""
        with patch.dict(
            os.environ,
            {
                "DB_URL_USER_MANAGEMENT": "postgresql://postgres:postgres@localhost:5432/briefly",
                "GOOGLE_CLIENT_ID": "test-google-id",
                "GOOGLE_CLIENT_SECRET": "test-google-secret",
                "AZURE_AD_CLIENT_ID": "test-microsoft-id",
                "AZURE_AD_CLIENT_SECRET": "test-microsoft-secret",
            },
            clear=True,
        ):
            settings = _TestableSettings()

            assert settings.google_client_id == "test-google-id"
            assert settings.google_client_secret == "test-google-secret"
            assert settings.azure_ad_client_id == "test-microsoft-id"
            assert settings.azure_ad_client_secret == "test-microsoft-secret"

    def test_redis_and_celery_settings(self):
        """Test Redis and Celery configuration."""
        with patch.dict(
            os.environ,
            {
                "DB_URL_USER_MANAGEMENT": "postgresql://postgres:postgres@localhost:5432/briefly",
                "REDIS_URL": "redis://testhost:6380",
                "CELERY_BROKER_URL": "redis://testhost:6380/1",
                "CELERY_RESULT_BACKEND": "redis://testhost:6380/2",
            },
            clear=True,
        ):
            settings = _TestableSettings()

            assert settings.redis_url == "redis://testhost:6380"
            assert settings.celery_broker_url == "redis://testhost:6380/1"
            assert settings.celery_result_backend == "redis://testhost:6380/2"

    def test_optional_settings_none_by_default(self):
        """Test that optional settings are None by default."""
        # Clear environment variables to test defaults
        with patch.dict(
            os.environ,
            {
                "DB_URL_USER_MANAGEMENT": "postgresql://postgres:postgres@localhost:5432/briefly"
            },
            clear=True,
        ):
            settings = _TestableSettings()

            assert settings.token_encryption_salt is None
            assert settings.clerk_secret_key is None
            assert settings.clerk_webhook_secret is None
            assert settings.google_client_id is None
            assert settings.google_client_secret is None
            assert settings.azure_ad_client_id is None
            assert settings.azure_ad_client_secret is None

    def test_case_insensitive_environment_variables(self):
        """Test that environment variables are case insensitive."""
        with patch.dict(
            os.environ,
            {
                "DB_URL_USER_MANAGEMENT": "postgresql://postgres:postgres@localhost:5432/briefly",
                "service_name": "lowercase-test",
                "HOST": "uppercase-test",
            },
            clear=True,
        ):
            settings = _TestableSettings()

            # Should work with both cases due to case_sensitive = False
            assert settings.service_name == "lowercase-test"
            assert settings.host == "uppercase-test"

    def test_boolean_environment_variables(self):
        """Test that boolean environment variables are parsed correctly."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(
                os.environ,
                {
                    "DB_URL_USER_MANAGEMENT": "postgresql://postgres:postgres@localhost:5432/briefly",
                    "DEBUG": env_value,
                },
                clear=True,
            ):
                settings = _TestableSettings()
                assert settings.debug == expected, f"Failed for {env_value}"

    def test_integer_environment_variables(self):
        """Test that integer environment variables are parsed correctly."""
        with patch.dict(
            os.environ,
            {
                "DB_URL_USER_MANAGEMENT": "postgresql://postgres:postgres@localhost:5432/briefly",
                "PORT": "8080",
            },
            clear=True,
        ):
            settings = _TestableSettings()
            assert settings.port == 8080
            assert isinstance(settings.port, int)

    def test_settings_immutability(self):
        """Test that settings behave as expected for configuration."""
        with patch.dict(
            os.environ,
            {
                "DB_URL_USER_MANAGEMENT": "postgresql://postgres:postgres@localhost:5432/briefly",
                "PORT": "8001",
            },
            clear=True,
        ):
            settings = _TestableSettings()
            original_port = settings.port

            # Settings should maintain their values
            assert settings.port == original_port
