"""
Unit tests for user profile endpoints.

Tests all user CRUD operations including success scenarios,
error handling, authentication, and authorization.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status

from ..exceptions import UserNotFoundException, ValidationException
from ..models import User
from ..schemas.user import (
    UserCreate,
    UserDeleteResponse,
    UserListResponse,
    UserOnboardingUpdate,
    UserResponse,
    UserUpdate,
)
from ..services.user_service import user_service


class TestUserProfileEndpoints:
    """Test cases for user profile endpoints."""

    def create_mock_user(self, user_id: int = 1, clerk_id: str = "user_123") -> User:
        """Create a mock user for testing."""
        user = MagicMock(spec=User)
        user.id = user_id
        user.clerk_id = clerk_id
        user.email = "test@example.com"
        user.first_name = "Test"
        user.last_name = "User"
        user.profile_image_url = "https://example.com/avatar.jpg"
        user.onboarding_completed = False
        user.onboarding_step = "profile_setup"
        user.created_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        user.deleted_at = None
        return user

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self):
        """Test successful user profile retrieval."""
        mock_user = self.create_mock_user()

        with (
            patch.object(user_service, "get_user_by_clerk_id", return_value=mock_user),
            patch.object(user_service, "get_user_profile") as mock_get_profile,
        ):

            mock_response = UserResponse(
                id=1,
                clerk_id="user_123",
                email="test@example.com",
                first_name="Test",
                last_name="User",
                profile_image_url="https://example.com/avatar.jpg",
                onboarding_completed=False,
                onboarding_step="profile_setup",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            mock_get_profile.return_value = mock_response

            # Import here to avoid circular imports during testing
            from ..routers.users import get_user_profile

            result = await get_user_profile(user_id=1, current_user_id="user_123")

            assert result.id == 1
            assert result.clerk_id == "user_123"
            assert result.email == "test@example.com"
            mock_get_profile.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_user_profile_unauthorized(self):
        """Test user profile retrieval with unauthorized access."""
        mock_current_user = self.create_mock_user(user_id=1, clerk_id="user_123")

        with patch.object(
            user_service, "get_user_by_clerk_id", return_value=mock_current_user
        ):

            from ..routers.users import get_user_profile

            # Try to access different user's profile
            with pytest.raises(HTTPException) as exc_info:
                await get_user_profile(user_id=2, current_user_id="user_123")

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Access denied" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_user_profile_not_found(self):
        """Test user profile retrieval when user not found."""
        with patch.object(user_service, "get_user_by_clerk_id") as mock_get_by_clerk:
            mock_get_by_clerk.side_effect = UserNotFoundException("User not found")

            from ..routers.users import get_user_profile

            with pytest.raises(HTTPException) as exc_info:
                await get_user_profile(user_id=1, current_user_id="user_123")

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_user_profile_success(self):
        """Test successful user profile update."""
        mock_user = self.create_mock_user()
        mock_updated_user = self.create_mock_user()
        mock_updated_user.first_name = "Updated"

        user_update = UserUpdate(first_name="Updated", last_name="Name")

        with (
            patch.object(user_service, "get_user_by_clerk_id", return_value=mock_user),
            patch.object(user_service, "update_user", return_value=mock_updated_user),
            patch(
                "services.user_management.schemas.user.UserResponse.from_orm"
            ) as mock_from_orm,
        ):

            mock_response = UserResponse(
                id=1,
                clerk_id="user_123",
                email="test@example.com",
                first_name="Updated",
                last_name="Name",
                profile_image_url="https://example.com/avatar.jpg",
                onboarding_completed=False,
                onboarding_step="profile_setup",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            mock_from_orm.return_value = mock_response

            from ..routers.users import update_user_profile

            result = await update_user_profile(
                user_data=user_update, user_id=1, current_user_id="user_123"
            )

            assert result.first_name == "Updated"
            user_service.update_user.assert_called_once_with(1, user_update)

    @pytest.mark.asyncio
    async def test_update_user_profile_validation_error(self):
        """Test user profile update with validation error."""
        mock_user = self.create_mock_user()
        user_update = UserUpdate(first_name="Updated")

        with (
            patch.object(user_service, "get_user_by_clerk_id", return_value=mock_user),
            patch.object(user_service, "update_user") as mock_update,
        ):

            mock_update.side_effect = ValidationException(
                field="email", value="invalid-email", reason="Invalid email format"
            )

            from ..routers.users import update_user_profile

            with pytest.raises(HTTPException) as exc_info:
                await update_user_profile(
                    user_data=user_update, user_id=1, current_user_id="user_123"
                )

            assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_delete_user_profile_success(self):
        """Test successful user profile deletion."""
        mock_user = self.create_mock_user()
        mock_delete_response = UserDeleteResponse(
            success=True,
            message="User 1 successfully deleted",
            user_id=1,
            deleted_at=datetime.utcnow(),
        )

        with (
            patch.object(user_service, "get_user_by_clerk_id", return_value=mock_user),
            patch.object(
                user_service, "delete_user", return_value=mock_delete_response
            ),
        ):

            from ..routers.users import delete_user_profile

            result = await delete_user_profile(user_id=1, current_user_id="user_123")

            assert result.success is True
            assert result.user_id == 1
            user_service.delete_user.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_user_profile_unauthorized(self):
        """Test user profile deletion with unauthorized access."""
        mock_current_user = self.create_mock_user(user_id=1, clerk_id="user_123")

        with patch.object(
            user_service, "get_user_by_clerk_id", return_value=mock_current_user
        ):

            from ..routers.users import delete_user_profile

            # Try to delete different user's profile
            with pytest.raises(HTTPException) as exc_info:
                await delete_user_profile(user_id=2, current_user_id="user_123")

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_update_user_onboarding_success(self):
        """Test successful user onboarding update."""
        mock_user = self.create_mock_user()
        mock_updated_user = self.create_mock_user()
        mock_updated_user.onboarding_completed = True
        mock_updated_user.onboarding_step = None

        onboarding_update = UserOnboardingUpdate(
            onboarding_completed=True, onboarding_step=None
        )

        with (
            patch.object(user_service, "get_user_by_clerk_id", return_value=mock_user),
            patch.object(
                user_service, "update_user_onboarding", return_value=mock_updated_user
            ),
            patch(
                "services.user_management.schemas.user.UserResponse.from_orm"
            ) as mock_from_orm,
        ):

            mock_response = UserResponse(
                id=1,
                clerk_id="user_123",
                email="test@example.com",
                first_name="Test",
                last_name="User",
                profile_image_url="https://example.com/avatar.jpg",
                onboarding_completed=True,
                onboarding_step=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            mock_from_orm.return_value = mock_response

            from ..routers.users import update_user_onboarding

            result = await update_user_onboarding(
                onboarding_data=onboarding_update, user_id=1, current_user_id="user_123"
            )

            assert result.onboarding_completed is True
            assert result.onboarding_step is None
            user_service.update_user_onboarding.assert_called_once_with(
                1, onboarding_update
            )

    @pytest.mark.asyncio
    async def test_search_users_success(self):
        """Test successful user search."""
        mock_search_results = UserListResponse(
            users=[
                UserResponse(
                    id=1,
                    clerk_id="user_123",
                    email="test@example.com",
                    first_name="Test",
                    last_name="User",
                    profile_image_url="https://example.com/avatar.jpg",
                    onboarding_completed=False,
                    onboarding_step="profile_setup",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            ],
            total=1,
            page=1,
            page_size=20,
            has_next=False,
            has_previous=False,
        )

        with patch.object(
            user_service, "search_users", return_value=mock_search_results
        ):

            from ..routers.users import search_users

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
        with patch.object(user_service, "search_users") as mock_search:

            from ..routers.users import search_users

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
            patch.object(user_service, "get_user_by_clerk_id", return_value=mock_user),
            patch(
                "services.user_management.schemas.user.UserResponse.from_orm"
            ) as mock_from_orm,
        ):

            mock_response = UserResponse(
                id=1,
                clerk_id="user_123",
                email="test@example.com",
                first_name="Test",
                last_name="User",
                profile_image_url="https://example.com/avatar.jpg",
                onboarding_completed=False,
                onboarding_step="profile_setup",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            mock_from_orm.return_value = mock_response

            from ..routers.users import get_current_user_profile

            result = await get_current_user_profile(current_user_id="user_123")

            assert result.clerk_id == "user_123"
            assert result.email == "test@example.com"
            user_service.get_user_by_clerk_id.assert_called_once_with("user_123")

    @pytest.mark.asyncio
    async def test_get_current_user_profile_not_found(self):
        """Test current user profile retrieval when user not found."""
        with patch.object(user_service, "get_user_by_clerk_id") as mock_get:
            mock_get.side_effect = UserNotFoundException("User not found")

            from ..routers.users import get_current_user_profile

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_profile(current_user_id="user_123")

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestUserServiceIntegration:
    """Integration tests for user service methods."""

    @pytest.mark.skip(
        reason="Integration test requiring complex Ormar ORM mocking - recommend unit tests for service logic instead"
    )
    @pytest.mark.asyncio
    async def test_user_profile_workflow(self, integration_test_user):
        """Test complete user profile workflow with mocked database operations."""
        user, preferences = integration_test_user

        # Test getting user profile
        retrieved_user = await user_service.get_user_by_id(user.id)
        assert retrieved_user.id == user.id
        assert retrieved_user.clerk_id == "user_integration_test"
        assert retrieved_user.email == "integration@test.com"

        # Test updating user
        from ..schemas.user import UserUpdate

        update_data = UserUpdate(first_name="Updated")

        # Mock the update behavior
        user.first_name = "Updated"

        updated_user = await user_service.update_user(user.id, update_data)
        assert updated_user.first_name == "Updated"
        assert updated_user.id == user.id

    @pytest.mark.skip(
        reason="Integration test requiring complex Ormar ORM mocking - recommend unit tests for service logic instead"
    )
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, integration_test_setup):
        """Test error handling in various scenarios."""
        setup = integration_test_setup
        user = setup["user"]
        mocks = setup["mocks"]

        # Test user not found - configure mock to raise exception for non-existent ID
        from ..exceptions import UserNotFoundException

        mocks["get"].side_effect = lambda user_id: (
            user if user_id == user.id else UserNotFoundException("User not found")
        )

        # Test getting existing user (should work)
        retrieved_user = await user_service.get_user_by_id(user.id)
        assert retrieved_user.id == user.id

        # Test user not found scenario
        with pytest.raises(UserNotFoundException):
            await user_service.get_user_by_id(999999)  # Non-existent ID

        # Test validation error - configure filter to return existing user for duplicate check
        from ..exceptions import ValidationException

        # Set up the mock to simulate finding an existing user with the same clerk_id
        mock_query = MagicMock()
        mock_query.get_or_none = AsyncMock(return_value=user)  # User exists
        mocks["filter"].return_value = mock_query

        create_data = UserCreate(
            clerk_id=user.clerk_id,  # Use existing clerk_id to trigger validation error
            email="duplicate@example.com",
        )

        with pytest.raises(ValidationException):
            await user_service.create_user(create_data)

    def create_mock_user(self, user_id: int = 1, clerk_id: str = "user_123") -> User:
        """Create a mock user for testing."""
        user = MagicMock(spec=User)
        user.id = user_id
        user.clerk_id = clerk_id
        user.email = "test@example.com"
        user.first_name = "Test"
        user.last_name = "User"
        user.deleted_at = None
        return user
