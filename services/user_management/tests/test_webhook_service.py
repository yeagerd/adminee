"""
Unit tests for the webhook service business logic.

Tests the WebhookService class directly, focusing on idempotency,
database operations, and error handling scenarios.
"""

import os
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlmodel import SQLModel, select, text

from ..database import async_session, engine
from ..exceptions import DatabaseError
from ..models import User, UserPreferences
from ..schemas.webhook import ClerkWebhookEventData
from ..services.webhook_service import WebhookService


@pytest.fixture(scope="module", autouse=True)
def setup_test_environment():
    """Set up test environment variables for webhook service tests."""
    with patch.dict(
        os.environ,
        {"DB_URL_USER_MANAGEMENT": "sqlite+aiosqlite:///./test_webhook_service.db"},
        clear=False,
    ):
        yield


@pytest_asyncio.fixture
async def setup_database():
    """Create database tables for testing."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture
async def clean_database(setup_database):
    """Ensure clean database state for each test."""
    async with async_session() as session:
        # Clear all tables
        await session.execute(text("UPDATE users SET deleted_at = NULL"))
        await session.execute(text("DELETE FROM user_preferences"))
        await session.execute(text("DELETE FROM users"))
        await session.commit()
    yield
    # Clean up after test - no need to clean again since the database is dropped


@pytest.fixture
def webhook_service():
    """Create webhook service instance for testing."""
    return WebhookService()


@pytest.fixture
def sample_clerk_user_data():
    """Sample Clerk user data for webhook testing."""
    return ClerkWebhookEventData(
        id="user_test_123",
        email_addresses=[
            {
                "email_address": "test@example.com",
                "verification": {"status": "verified"},
            }
        ],
        first_name="Test",
        last_name="User",
        image_url="https://example.com/test-avatar.jpg",
        created_at=1640995200000,
        updated_at=1640995200000,
    )


@pytest.fixture
def sample_clerk_user_data_updated():
    """Sample Clerk user data with updates for webhook testing."""
    return ClerkWebhookEventData(
        id="user_test_123",
        email_addresses=[
            {
                "email_address": "updated@example.com",
                "verification": {"status": "verified"},
            }
        ],
        first_name="Updated",
        last_name="User",
        image_url="https://example.com/updated-avatar.jpg",
        created_at=1640995200000,
        updated_at=1640999200000,
    )


class TestWebhookServiceUserCreation:
    """Test cases for user creation webhook handling."""

    @pytest.mark.asyncio
    async def test_create_new_user_success(
        self, webhook_service, sample_clerk_user_data, clean_database
    ):
        """Test successful creation of a new user."""
        result = await webhook_service._handle_user_created(sample_clerk_user_data)

        # Verify return value
        assert result["action"] == "user_created"
        assert result["external_auth_id"] == "user_test_123"
        assert "user_id" in result
        assert "preferences_id" in result

        # Verify user was created in database
        async with async_session() as session:
            user_result = await session.execute(
                select(User).where(User.external_auth_id == "user_test_123")
            )
            user = user_result.scalar_one_or_none()

            assert user is not None
            assert user.external_auth_id == "user_test_123"
            assert user.auth_provider == "clerk"
            assert user.email == "test@example.com"
            assert user.first_name == "Test"
            assert user.last_name == "User"
            assert user.profile_image_url == "https://example.com/test-avatar.jpg"
            assert user.onboarding_completed is False
            assert user.onboarding_step == "welcome"

            # Verify preferences were created
            prefs_result = await session.execute(
                select(UserPreferences).where(UserPreferences.user_id == user.id)
            )
            preferences = prefs_result.scalar_one_or_none()
            assert preferences is not None

    @pytest.mark.asyncio
    async def test_create_user_idempotency_skips_duplicate(
        self, webhook_service, sample_clerk_user_data, clean_database
    ):
        """Test that creating the same user twice skips the second creation."""
        # First creation
        result1 = await webhook_service._handle_user_created(sample_clerk_user_data)
        assert result1["action"] == "user_created"

        # Second creation (should be skipped)
        result2 = await webhook_service._handle_user_created(sample_clerk_user_data)
        assert result2["action"] == "user_creation_skipped"
        assert result2["user_id"] == "user_test_123"
        assert result2["reason"] == "User already exists"

        # Verify only one user exists in database
        async with async_session() as session:
            count_result = await session.execute(
                text(
                    "SELECT COUNT(*) FROM users WHERE external_auth_id = 'user_test_123'"
                )
            )
            count = count_result.scalar()
            assert count == 1

    @pytest.mark.asyncio
    async def test_create_user_no_primary_email_error(
        self, webhook_service, clean_database
    ):
        """Test error handling when no primary email is provided."""
        user_data = ClerkWebhookEventData(
            id="user_no_email",
            email_addresses=None,  # No email addresses
            first_name="No",
            last_name="Email",
            created_at=1640995200000,
            updated_at=1640995200000,
        )

        with pytest.raises(DatabaseError) as exc_info:
            await webhook_service._handle_user_created(user_data)

        assert "No primary email found in user data" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_user_database_error_handling(
        self, webhook_service, sample_clerk_user_data, clean_database
    ):
        """Test error handling when database operations fail."""
        # Mock database session to raise an exception
        with patch(
            "services.user_management.services.webhook_service.async_session"
        ) as mock_session:
            mock_session.return_value.__aenter__.side_effect = Exception(
                "Database connection failed"
            )

            with pytest.raises(DatabaseError) as exc_info:
                await webhook_service._handle_user_created(sample_clerk_user_data)

            assert "User creation failed" in str(exc_info.value)


class TestWebhookServiceUserUpdate:
    """Test cases for user update webhook handling."""

    @pytest.mark.asyncio
    async def test_update_existing_user_success(
        self,
        webhook_service,
        sample_clerk_user_data,
        sample_clerk_user_data_updated,
        clean_database,
    ):
        """Test successful update of an existing user."""
        # First create a user
        await webhook_service._handle_user_created(sample_clerk_user_data)

        # Then update the user
        result = await webhook_service._handle_user_updated(
            sample_clerk_user_data_updated
        )

        assert result["action"] == "user_updated"
        assert result["user_id"] == "user_test_123"
        assert "updated_fields" in result
        assert "email" in result["updated_fields"]
        assert "first_name" in result["updated_fields"]

        # Verify user was updated in database
        async with async_session() as session:
            user_result = await session.execute(
                select(User).where(User.external_auth_id == "user_test_123")
            )
            user = user_result.scalar_one_or_none()

            assert user is not None
            assert user.email == "updated@example.com"
            assert user.first_name == "Updated"

    @pytest.mark.asyncio
    async def test_update_nonexistent_user_creates_user(
        self, webhook_service, sample_clerk_user_data, clean_database
    ):
        """Test that updating a non-existent user creates the user instead."""
        result = await webhook_service._handle_user_updated(sample_clerk_user_data)

        # Should create the user instead of updating
        assert result["action"] == "user_created"
        assert result["external_auth_id"] == "user_test_123"

        # Verify user was created in database
        async with async_session() as session:
            user_result = await session.execute(
                select(User).where(User.external_auth_id == "user_test_123")
            )
            user = user_result.scalar_one_or_none()
            assert user is not None

    @pytest.mark.asyncio
    async def test_update_user_no_changes(
        self, webhook_service, sample_clerk_user_data, clean_database
    ):
        """Test updating a user with no actual changes."""
        # Create user
        await webhook_service._handle_user_created(sample_clerk_user_data)

        # Update with same data
        result = await webhook_service._handle_user_updated(sample_clerk_user_data)

        assert result["action"] == "user_no_changes"
        assert result["user_id"] == "user_test_123"


class TestWebhookServiceUserDeletion:
    """Test cases for user deletion webhook handling."""

    @pytest.mark.asyncio
    async def test_delete_existing_user_success(
        self, webhook_service, sample_clerk_user_data, clean_database
    ):
        """Test successful soft deletion of an existing user."""
        # First create a user
        create_result = await webhook_service._handle_user_created(
            sample_clerk_user_data
        )
        user_id = create_result["user_id"]

        # Then delete the user
        result = await webhook_service._handle_user_deleted(sample_clerk_user_data)

        assert result["action"] == "user_deleted"
        assert result["user_id"] == user_id
        assert result["external_auth_id"] == "user_test_123"

        # Verify user was soft deleted in database
        async with async_session() as session:
            user_result = await session.execute(
                select(User).where(User.external_auth_id == "user_test_123")
            )
            user = user_result.scalar_one_or_none()

            assert user is not None
            assert user.deleted_at is not None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user_skipped(
        self, webhook_service, sample_clerk_user_data, clean_database
    ):
        """Test deletion of a non-existent user is skipped."""
        result = await webhook_service._handle_user_deleted(sample_clerk_user_data)

        assert result["action"] == "user_deletion_skipped"
        assert result["external_auth_id"] == "user_test_123"
        assert result["reason"] == "User not found"


class TestWebhookServiceIntegration:
    """Integration tests for webhook service with real database operations."""

    @pytest.mark.asyncio
    async def test_complete_user_lifecycle(
        self,
        webhook_service,
        sample_clerk_user_data,
        sample_clerk_user_data_updated,
        clean_database,
    ):
        """Test complete user lifecycle: create, update, delete."""

        # 1. Create user
        create_result = await webhook_service._handle_user_created(
            sample_clerk_user_data
        )
        assert create_result["action"] == "user_created"
        user_id = create_result["user_id"]

        # 2. Update user
        update_result = await webhook_service._handle_user_updated(
            sample_clerk_user_data_updated
        )
        assert update_result["action"] == "user_updated"

        # 3. Delete user
        delete_result = await webhook_service._handle_user_deleted(
            sample_clerk_user_data
        )
        assert delete_result["action"] == "user_deleted"
        assert delete_result["user_id"] == user_id

        # 4. Verify final state
        async with async_session() as session:
            user_result = await session.execute(
                select(User).where(User.external_auth_id == "user_test_123")
            )
            user = user_result.scalar_one_or_none()

            assert user is not None
            assert user.deleted_at is not None
            assert user.email == "updated@example.com"  # Updates should be preserved

    @pytest.mark.asyncio
    async def test_idempotency_with_real_database(
        self, webhook_service, sample_clerk_user_data, clean_database
    ):
        """Test idempotency behavior with real database operations."""

        # Create same user multiple times
        results = []
        for i in range(3):
            result = await webhook_service._handle_user_created(sample_clerk_user_data)
            results.append(result)

        # First should create, rest should skip
        assert results[0]["action"] == "user_created"
        assert results[1]["action"] == "user_creation_skipped"
        assert results[2]["action"] == "user_creation_skipped"

        # Verify only one user exists
        async with async_session() as session:
            count_result = await session.execute(
                text(
                    "SELECT COUNT(*) FROM users WHERE external_auth_id = 'user_test_123'"
                )
            )
            count = count_result.scalar()
            assert count == 1

            # Verify only one preferences record exists
            prefs_count_result = await session.execute(
                text("SELECT COUNT(*) FROM user_preferences")
            )
            prefs_count = prefs_count_result.scalar()
            assert prefs_count == 1
