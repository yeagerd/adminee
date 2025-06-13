"""
Test configuration and fixtures for User Management Service tests.

This module provides reusable fixtures and configurations for testing
the User Management Service with proper mocking of dependencies.
"""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set default test database URL if not already set - needed for imports to work
if "DB_URL_USER_MANAGEMENT" not in os.environ:
    os.environ["DB_URL_USER_MANAGEMENT"] = "sqlite:///./test_default.db"

# Import the application and models for testing
from ..main import app
from ..models import User, UserPreferences


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "clerk_id": "user_2abc123def456",
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "profile_image_url": "https://example.com/avatar.jpg",
        "onboarding_completed": False,
        "onboarding_step": "welcome",
        "timezone": "America/New_York",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_preferences_data():
    """Sample user preferences data for testing."""
    return {
        "theme": "light",
        "language": "en",
        "timezone": "America/New_York",
        "notifications_email": True,
        "notifications_push": True,
        "notifications_sms": False,
        "ai_suggestions": True,
        "ai_auto_categorize": False,
        "ai_smart_replies": True,
        "integration_google_enabled": False,
        "integration_microsoft_enabled": False,
        "integration_slack_enabled": False,
        "privacy_data_sharing": False,
        "privacy_analytics": True,
        "privacy_personalization": True,
    }


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = MagicMock(spec=User)
    user.id = 1
    user.clerk_id = "user_2abc123def456"
    user.email = "test@example.com"
    user.first_name = "John"
    user.last_name = "Doe"
    user.profile_image_url = "https://example.com/avatar.jpg"
    user.onboarding_completed = False
    user.onboarding_step = "welcome"
    user.timezone = "America/New_York"
    user.deleted_at = None
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def mock_preferences():
    """Create mock user preferences for testing."""
    preferences = MagicMock(spec=UserPreferences)
    preferences.id = 1
    preferences.user_id = 1
    preferences.theme = "light"
    preferences.language = "en"
    preferences.timezone = "America/New_York"
    preferences.notifications_email = True
    preferences.notifications_push = True
    preferences.notifications_sms = False
    preferences.ai_suggestions = True
    preferences.ai_auto_categorize = False
    preferences.ai_smart_replies = True
    preferences.integration_google_enabled = False
    preferences.integration_microsoft_enabled = False
    preferences.integration_slack_enabled = False
    preferences.privacy_data_sharing = False
    preferences.privacy_analytics = True
    preferences.privacy_personalization = True
    return preferences


@pytest.fixture
def mock_clerk_token():
    """Mock Clerk JWT token data."""
    return {
        "sub": "user_2abc123def456",
        "email": "test@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "image_url": "https://example.com/avatar.jpg",
        "iat": 1640995200,  # 2022-01-01
        "exp": 1640998800,  # 2022-01-01 + 1 hour
    }


@pytest.fixture
def mock_service_auth():
    """Mock service authentication."""
    return {
        "service_name": "test-service",
        "permissions": ["read", "write"],
        "user_id": "user_2abc123def456",
    }


@pytest.fixture
def mock_webhook_signature_verification():
    """Mock webhook signature verification to always pass."""
    with patch(
        "services.user_management.auth.webhook_auth.verify_webhook_signature"
    ) as mock_verify:
        mock_verify.return_value = None
        yield mock_verify


@pytest.fixture
def sample_clerk_webhook_payload():
    """Sample Clerk webhook payload for testing."""
    return {
        "type": "user.created",
        "data": {
            "id": "user_2abc123def456",
            "email_addresses": [
                {
                    "email_address": "test@example.com",
                    "id": "idn_2abc123def456",
                    "object": "email_address",
                    "verification": {"status": "verified", "strategy": "email_code"},
                }
            ],
            "first_name": "John",
            "last_name": "Doe",
            "image_url": "https://example.com/avatar.jpg",
            "created_at": 1640995200000,  # Milliseconds since epoch
            "updated_at": 1640995200000,
        },
        "object": "event",
        "timestamp": 1640995200,
    }


@pytest.fixture
def mock_auth_dependencies():
    """Mock authentication dependencies for testing."""
    with (
        patch("services.user_management.auth.clerk.get_current_user") as mock_get_user,
        patch(
            "services.user_management.auth.clerk.verify_user_ownership"
        ) as mock_verify_ownership,
        patch(
            "services.user_management.auth.service_auth.require_service_auth"
        ) as mock_service_auth,
    ):
        # Default mocks that can be overridden in individual tests
        mock_get_user.return_value = "user_2abc123def456"
        mock_verify_ownership.return_value = True
        mock_service_auth.return_value = {
            "service_name": "test-service",
            "permissions": ["read", "write"],
        }

        yield {
            "get_current_user": mock_get_user,
            "verify_user_ownership": mock_verify_ownership,
            "require_service_auth": mock_service_auth,
        }


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch("services.user_management.settings.settings") as mock_settings:
        mock_settings.database_url = "sqlite:///test.db"
        mock_settings.clerk_webhook_secret = "test-webhook-secret"
        mock_settings.api_key_user_management = "test-api-key"
        mock_settings.cors_origins = ["http://localhost:3000"]
        yield mock_settings


@pytest.fixture
def integration_test_setup():
    """
    Set up comprehensive mocking for integration tests.

    This provides a controlled environment for testing business logic
    without requiring real database operations.
    """

    # Create mock user and preferences
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.clerk_id = "user_integration_test"
    mock_user.email = "integration@test.com"
    mock_user.first_name = "Integration"
    mock_user.last_name = "Test"
    mock_user.profile_image_url = "https://example.com/integration.jpg"
    mock_user.onboarding_completed = True
    mock_user.onboarding_step = "completed"
    mock_user.timezone = "UTC"
    mock_user.deleted_at = None
    mock_user.created_at = datetime.now(timezone.utc)
    mock_user.updated_at = datetime.now(timezone.utc)

    # Mock user update method
    async def mock_update():
        mock_user.updated_at = datetime.now(timezone.utc)
        return mock_user

    mock_user.update = AsyncMock(side_effect=mock_update)
    mock_user.load = AsyncMock(return_value=mock_user)

    mock_preferences = MagicMock(spec=UserPreferences)
    mock_preferences.id = 1
    mock_preferences.user_id = 1
    mock_preferences.theme = "light"
    mock_preferences.language = "en"
    mock_preferences.timezone = "UTC"

    # Set up database mocking
    with (
        patch.object(User.objects, "get") as mock_get,
        patch.object(User.objects, "create") as mock_create,
        patch.object(User.objects, "filter") as mock_filter,
        patch.object(UserPreferences.objects, "create") as mock_prefs_create,
    ):

        # Configure mocks
        mock_get.return_value = mock_user
        mock_create.return_value = mock_user
        mock_prefs_create.return_value = mock_preferences

        # Mock filter chain for validation tests
        mock_query = MagicMock()
        mock_query.get_or_none = AsyncMock(return_value=None)  # For new user validation
        mock_filter.return_value = mock_query

        yield {
            "user": mock_user,
            "preferences": mock_preferences,
            "mocks": {
                "get": mock_get,
                "create": mock_create,
                "filter": mock_filter,
                "prefs_create": mock_prefs_create,
            },
        }


@pytest.fixture
def integration_test_user(integration_test_setup):
    """Simplified integration test user that returns the mocked objects."""
    setup = integration_test_setup
    return setup["user"], setup["preferences"]
