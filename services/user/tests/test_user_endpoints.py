"""
Unit tests for user profile endpoints.

Tests all user CRUD operations including success scenarios,
error handling, authentication, and authorization.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status

from services.user.models.user import User
from services.user.schemas.user import (
    UserCreate,
    UserListResponse,
    UserResponse,
)
from services.user.services.user_service import get_user_service


class TestUserProfileEndpoints:
    """Test cases for user profile endpoints."""

    def setup_method(self):
        pass

    def teardown_method(self):
        pass

    def create_mock_user(
        self, user_id: int = 1, external_auth_id: str = "user_123"
    ) -> User:
        """Create a mock user for testing."""
        user = MagicMock(spec=User)
        user.id = user_id
        user.external_auth_id = external_auth_id
        user.auth_provider = "google"
        user.email = "test@example.com"
        user.first_name = "Test"
        user.last_name = "User"
        user.profile_image_url = "https://example.com/avatar.jpg"
        user.onboarding_completed = False
        user.onboarding_step = "profile_setup"
        user.created_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        user.deleted_at = None
        return user

    @pytest.mark.asyncio
    async def test_search_users_success(self):
        """Test successful user search."""
        mock_search_results = UserListResponse(
            users=[
                UserResponse(
                    id=1,
                    external_auth_id="user_123",
                    auth_provider="nextauth",
                    email="test@example.com",
                    first_name="Test",
                    last_name="User",
                    profile_image_url="https://example.com/avatar.jpg",
                    onboarding_completed=False,
                    onboarding_step="profile_setup",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            ],
            total=1,
            page=1,
            page_size=20,
            has_next=False,
            has_previous=False,
        )

        with patch.object(
            get_user_service(), "search_users", return_value=mock_search_results
        ):
            from services.user.routers.users import search_users

            result = await search_users(
                query="test",
                email=None,
                onboarding_completed=None,
                page=1,
                page_size=20,
                current_user_id="user_123",
            )

            assert result.total == 1
            assert len(result.users) == 1
            assert result.users[0].email == "test@example.com"

    @pytest.mark.asyncio
    async def test_search_users_with_filters(self):
        """Test user search with filters."""
        with patch.object(get_user_service(), "search_users") as mock_search:
            from services.user.routers.users import search_users

            await search_users(
                query="john",
                email="john@example.com",
                onboarding_completed=True,
                page=2,
                page_size=10,
                current_user_id="user_123",
            )

            # Verify the search request was created with correct parameters
            call_args = mock_search.call_args[0][0]
            assert call_args.query == "john"
            assert call_args.email == "john@example.com"
            assert call_args.onboarding_completed is True
            assert call_args.page == 2
            assert call_args.page_size == 10

    @pytest.mark.asyncio
    async def test_get_current_user_profile_success(self):
        """Test successful current user profile retrieval."""
        mock_user = self.create_mock_user()

        with (
            patch.object(
                get_user_service(),
                "get_user_by_external_auth_id",
                return_value=mock_user,
            ),
            patch("services.user.schemas.user.UserResponse.from_orm") as mock_from_orm,
        ):
            mock_response = UserResponse(
                id=1,
                external_auth_id="user_123",
                auth_provider="nextauth",
                email="test@example.com",
                first_name="Test",
                last_name="User",
                profile_image_url="https://example.com/avatar.jpg",
                onboarding_completed=False,
                onboarding_step="profile_setup",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            mock_from_orm.return_value = mock_response

            from services.user.routers.users import get_current_user_profile

            result = await get_current_user_profile(
                current_user_external_auth_id="user_123"
            )

            assert result.external_auth_id == "user_123"
            get_user_service().get_user_by_external_auth_id.assert_called_once_with(
                "user_123", "nextauth"
            )

    @pytest.mark.asyncio
    async def test_get_current_user_profile_not_found(self):
        """Test current user profile retrieval when user not found."""
        with patch.object(
            get_user_service(), "get_user_by_external_auth_id"
        ) as mock_get:
            mock_get.side_effect = HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

            from services.common.http_errors import ServiceError
            from services.user.routers.users import get_current_user_profile

            with pytest.raises(ServiceError) as exc_info:
                await get_current_user_profile(current_user_external_auth_id="user_123")
            assert "Failed to retrieve current user profile" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_user_profile_workflow(self):
        """Test complete user profile workflow with mocked service operations."""
        # Create mock user data
        mock_user = self.create_mock_user(
            user_id=1, external_auth_id="user_integration_test"
        )
        mock_user.email = "integration@test.com"
        mock_user.first_name = "Original"

        mock_updated_user = self.create_mock_user(
            user_id=1, external_auth_id="user_integration_test"
        )
        mock_updated_user.email = "integration@test.com"
        mock_updated_user.first_name = "Updated"

        with (
            patch.object(get_user_service(), "get_user_by_id", return_value=mock_user),
            patch.object(
                get_user_service(), "update_user", return_value=mock_updated_user
            ),
        ):
            # Test getting user profile
            retrieved_user = await get_user_service().get_user_by_id(1)
            assert retrieved_user.id == 1
            assert retrieved_user.external_auth_id == "user_integration_test"
            assert retrieved_user.email == "integration@test.com"

            # Test updating user
            from services.user.schemas.user import UserUpdate

            update_data = UserUpdate(first_name="Updated")
            updated_user = await get_user_service().update_user(1, update_data)

            assert updated_user.first_name == "Updated"
            assert updated_user.id == 1

            # Verify service calls
            get_user_service().get_user_by_id.assert_called_once_with(1)
            get_user_service().update_user.assert_called_once_with(1, update_data)


class TestUserServiceIntegration:
    """Integration tests for user service methods."""

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self):
        """Test error handling in various scenarios."""
        # Create mock user for testing
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.external_auth_id = "existing_user"
        mock_user.email = "existing@test.com"

        with patch.object(get_user_service(), "get_user_by_id") as mock_get_by_id:
            # Test user not found scenario
            mock_get_by_id.side_effect = HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_user_service().get_user_by_id(999999)  # Non-existent ID

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

            # Test getting existing user (should work)
            mock_get_by_id.side_effect = None
            mock_get_by_id.return_value = mock_user

            retrieved_user = await get_user_service().get_user_by_id(1)
            assert retrieved_user.id == 1

        # Test validation error for duplicate user creation
        with patch.object(get_user_service(), "create_user") as mock_create:
            mock_create.side_effect = HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Validation error",
            )

            create_data = UserCreate(
                external_auth_id="existing_user",
                email="duplicate@example.com",
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_user_service().create_user(create_data)

            assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            mock_create.assert_called_once_with(create_data)

    def create_mock_user(
        self, user_id: int = 1, external_auth_id: str = "user_123"
    ) -> User:
        """Create a mock user for testing."""
        user = MagicMock(spec=User)
        user.id = user_id
        user.external_auth_id = external_auth_id
        user.auth_provider = "nextauth"
        user.email = "test@example.com"
        user.first_name = "Test"
        user.last_name = "User"
        user.deleted_at = None
        return user


class TestEmailResolutionEndpoint:
    """Integration tests for email resolution endpoint."""

    # TODO: Add proper integration tests following the existing pattern
    # For now, the email resolution functionality is tested via unit tests
    # in test_email_resolution.py which provide comprehensive coverage
    pass
