"""
Unit tests for Webhook Service.

Tests webhook processing, user lifecycle management,
database operations, and error handling scenarios.
"""

import asyncio
import os
import tempfile

# Set required environment variables before any imports
os.environ.setdefault("TOKEN_ENCRYPTION_SALT", "dGVzdC1zYWx0LTE2Ynl0ZQ==")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from services.user_management.database import create_all_tables, get_async_session
from services.user_management.main import app
from services.user_management.models.user import User

from ..schemas.webhook import ClerkWebhookEventData
from ..services.webhook_service import WebhookService


class TestWebhookServiceIntegration:
    def setup_method(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        os.environ["DB_URL_USER_MANAGEMENT"] = f"sqlite:///{self.db_path}"
        asyncio.run(create_all_tables())  # Create tables before cleaning
        self.client = TestClient(app)
        self._clean_database()
        self.webhook_service = WebhookService()

    def teardown_method(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def _clean_database(self):
        import asyncio

        async def clean():
            async_session = get_async_session()
            async with async_session() as session:
                await session.execute(text("UPDATE users SET deleted_at = NULL"))
                await session.execute(text("DELETE FROM user_preferences"))
                await session.execute(text("DELETE FROM users"))
                await session.commit()

        asyncio.run(clean())

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
            assert user.email == "updated@example.com"  # Updates should be preserved

    @pytest.mark.asyncio
    async def test_idempotency_with_real_database(self):
        """Test idempotency behavior with real database operations."""
        # Create same user multiple times
        results = []
        for i in range(3):
            result = await self.webhook_service._handle_user_created(
                self.sample_clerk_user_data()
            )
            results.append(result)
        # First should create, rest should skip
        assert results[0]["action"] == "user_created"
        assert results[1]["action"] == "user_creation_skipped"
        assert results[2]["action"] == "user_creation_skipped"
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
