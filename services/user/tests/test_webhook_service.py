"""
Unit tests for Webhook Service.

Tests webhook processing, user lifecycle management,
database operations, and error handling scenarios.
"""

import os
import tempfile

import pytest
from sqlalchemy import text

from services.user.database import create_all_tables, get_async_session
from services.user.models.user import User
from services.user.schemas.webhook import ClerkWebhookEventData
from services.user.services.webhook_service import WebhookService
from services.user.tests.test_base import BaseUserManagementTest


class TestWebhookServiceIntegration(BaseUserManagementTest):
    def setup_method(self):
        super().setup_method()
        self.webhook_service = WebhookService()

    async def _setup_test_database(self):
        """Create a fresh temporary database for each test."""
        # Create a new temporary database file for this test
        self.test_db_fd, self.test_db_path = tempfile.mkstemp(suffix=".db")

        # Set the database URL to use our test database
        os.environ["DB_URL_USER_MANAGEMENT"] = f"sqlite:///{self.test_db_path}"

        # Force reload of all database-related modules
        import importlib
        import sys

        # Clear any cached database connections
        modules_to_reload = [
            "services.user.database",
            "services.user.settings",
            "services.user.services.webhook_service",
        ]

        for module_name in modules_to_reload:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])

        # Re-import and recreate the webhook service to use new database connection
        from services.user.services.webhook_service import WebhookService

        self.webhook_service = WebhookService()

        # Create all tables in the fresh database
        await create_all_tables()

    def _cleanup_test_database(self):
        """Clean up the temporary database file."""
        if hasattr(self, "test_db_fd"):
            os.close(self.test_db_fd)
        if hasattr(self, "test_db_path") and os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    def sample_clerk_user_data(self):
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

    def sample_clerk_user_data_updated(self):
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

    @pytest.mark.asyncio
    async def test_complete_user_lifecycle(self):
        """Test complete user lifecycle: create, update, delete."""
        # Set up fresh database for this test
        await self._setup_test_database()

        try:
            # 1. Create user
            create_result = await self.webhook_service._handle_user_created(
                self.sample_clerk_user_data()
            )
            assert create_result["action"] == "user_created"
            user_id = create_result["user_id"]

            # 2. Update user
            update_result = await self.webhook_service._handle_user_updated(
                self.sample_clerk_user_data_updated()
            )
            assert update_result["action"] == "user_updated"

            # 3. Delete user
            delete_result = await self.webhook_service._handle_user_deleted(
                self.sample_clerk_user_data()
            )
            assert delete_result["action"] == "user_deleted"
            assert delete_result["user_id"] == user_id

            # 4. Verify final state
            async_session = get_async_session()
            async with async_session() as session:
                from sqlmodel import select

                user_result = await session.execute(
                    select(User).where(User.external_auth_id == "user_test_123")
                )
                user = user_result.scalar_one_or_none()
                assert user is not None
                assert user.deleted_at is not None
                assert (
                    user.email == "updated@example.com"
                )  # Updates should be preserved
        finally:
            # Clean up the test database
            self._cleanup_test_database()

    @pytest.mark.asyncio
    async def test_idempotency_with_real_database(self):
        """Test idempotency behavior with real database operations."""
        # Set up fresh database for this test
        await self._setup_test_database()

        try:
            # Create same user multiple times
            results = []
            for i in range(3):
                result = await self.webhook_service._handle_user_created(
                    self.sample_clerk_user_data()
                )
                results.append(result)
            # First should create, rest should skip
            assert results[0]["action"] == "user_created"
            assert results[1]["action"] == "user_already_exists"
            assert results[2]["action"] == "user_already_exists"
            # Verify only one user exists
            async_session = get_async_session()
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
        finally:
            # Clean up the test database
            self._cleanup_test_database()

    @pytest.mark.asyncio
    async def test_update_external_auth_id_when_email_exists(self):
        """Test that if a user exists with the same email but a different external_auth_id, the webhook returns a 409 EmailCollision error."""
        await self._setup_test_database()

        # In test environment, email normalization will use simple normalization automatically
        try:
            # 1. Create a user with one external_auth_id
            initial_data = ClerkWebhookEventData(
                id="demo_user",
                email_addresses=[
                    {
                        "email_address": "trybriefly@outlook.com",
                        "verification": {"status": "verified"},
                    }
                ],
                first_name="Demo",
                last_name="User",
                image_url="https://images.clerk.dev/demo-avatar.png",
                created_at=1640995200000,
                updated_at=1640995200000,
            )
            create_result = await self.webhook_service._handle_user_created(
                initial_data
            )
            assert create_result["action"] == "user_created"

            # 2. Call webhook with a new external_auth_id but same email
            new_data = ClerkWebhookEventData(
                id="user_trybriefly_outlook_com",
                email_addresses=[
                    {
                        "email_address": "trybriefly@outlook.com",
                        "verification": {"status": "verified"},
                    }
                ],
                first_name="Demo",
                last_name="User",
                image_url="https://images.clerk.dev/demo-avatar.png",
                created_at=1640995200000,
                updated_at=1640995200000,
            )
            import pytest

            from services.common.http_errors import ServiceError

            with pytest.raises(ServiceError) as exc_info:
                await self.webhook_service._handle_user_created(new_data)
            assert "already exists with a different user" in str(exc_info.value)

            # 3. Verify only one user exists and external_auth_id is NOT updated
            async_session = get_async_session()
            async with async_session() as session:
                from sqlmodel import select

                user_result = await session.execute(
                    select(User).where(User.email == "trybriefly@outlook.com")
                )
                user = user_result.scalar_one_or_none()
                assert user is not None
                assert user.external_auth_id == "demo_user"
                # There should only be one user with this email
                count_result = await session.execute(
                    text(
                        "SELECT COUNT(*) FROM users WHERE email = 'trybriefly@outlook.com'"
                    )
                )
                count = count_result.scalar()
                assert count == 1
        finally:
            self._cleanup_test_database()
