"""
Tests for user service pagination implementation.

This module tests the user-specific cursor pagination functionality.
"""

import pytest
from common.pagination import PaginationConfig
from common.pagination.base import CursorInfo

from services.api.v1.user.requests import UserFilterRequest
from services.common.api.v1.schemas import (
    CursorValidationError,
    PaginationError,
)
from services.user.utils.pagination import UserCursorPagination


class TestUserCursorPagination:
    """Test user-specific cursor pagination."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = PaginationConfig(
            secret_key="test-secret-key",
            token_expiry=3600,
            max_page_size=100,
            default_page_size=20,
        )
        self.pagination = UserCursorPagination(self.config)

    def test_build_query_filters_next(self):
        """Test building query filters for next page."""
        cursor_info = CursorInfo(
            last_id=123,
            last_timestamp="2023-01-01T00:00:00Z",
            filters={
                "query": "john",
                "email": "john@example.com",
                "onboarding_completed": True,
            },
            direction="next",
            limit=20,
            created_at="2023-01-01T00:00:00Z",
        )

        filters = self.pagination.build_query_filters(cursor_info)

        assert "cursor_filter" in filters
        assert "cursor_params" in filters
        assert "query" in filters
        assert "email" in filters
        assert "onboarding_completed" in filters
        assert filters["query"] == "john"
        assert filters["email"] == "john@example.com"
        assert filters["onboarding_completed"] is True

    def test_build_query_filters_prev(self):
        """Test building query filters for previous page."""
        cursor_info = CursorInfo(
            last_id=123,
            last_timestamp="2023-01-01T00:00:00Z",
            filters={"query": "jane"},
            direction="prev",
            limit=20,
            created_at="2023-01-01T00:00:00Z",
        )

        filters = self.pagination.build_query_filters(cursor_info)

        assert "cursor_filter" in filters
        assert "cursor_params" in filters
        assert "query" in filters
        assert filters["query"] == "jane"

    def test_get_ordering_clause(self):
        """Test getting ordering clause."""
        next_ordering = self.pagination.get_ordering_clause("next")
        prev_ordering = self.pagination.get_ordering_clause("prev")

        assert next_ordering == "created_at ASC, id ASC"
        assert prev_ordering == "created_at DESC, id DESC"

    def test_create_user_cursor_info(self):
        """Test creating user-specific cursor info."""
        cursor_info = self.pagination.create_user_cursor_info(
            last_id=123,
            last_created_at="2023-01-01T00:00:00Z",
            filters={"query": "john"},
            direction="next",
            limit=30,
        )

        assert cursor_info.last_id == 123
        assert cursor_info.last_timestamp == "2023-01-01T00:00:00Z"
        assert cursor_info.filters == {"query": "john"}
        assert cursor_info.direction == "next"
        assert cursor_info.limit == 30

    def test_build_user_query(self):
        """Test building user query."""
        cursor_info = CursorInfo(
            last_id=123,
            last_timestamp="2023-01-01T00:00:00Z",
            filters={"query": "john"},
            direction="next",
            limit=20,
            created_at="2023-01-01T00:00:00Z",
        )

        query, params = self.pagination.build_user_query(
            cursor_info=cursor_info, additional_filters={"onboarding_completed": True}
        )

        assert "SELECT * FROM users" in query
        assert "WHERE" in query
        assert "ORDER BY" in query
        assert "LIMIT" in query

    def test_create_user_pagination_response(self):
        """Test creating user pagination response."""
        users = [
            {"id": 1, "email": "user1@example.com"},
            {"id": 2, "email": "user2@example.com"},
        ]

        cursor_info = CursorInfo(
            last_id=2,
            last_timestamp="2023-01-01T00:00:00Z",
            filters={"query": "john"},
            direction="next",
            limit=20,
            created_at="2023-01-01T00:00:00Z",
        )

        response = self.pagination.create_user_pagination_response(
            users=users, cursor_info=cursor_info, has_next=True, has_prev=False
        )

        assert "users" in response
        assert response["users"] == users
        assert response["has_next"] is True
        assert response["has_prev"] is False
        assert response["limit"] == 20
        assert "next_cursor" in response

    def test_validate_user_filters(self):
        """Test validating user filters."""
        raw_filters = {
            "query": "  john  ",
            "email": "  john@example.com  ",
            "onboarding_completed": "true",
            "invalid_filter": "should_be_ignored",
        }

        validated_filters = self.pagination.validate_user_filters(raw_filters)

        assert "query" in validated_filters
        assert "email" in validated_filters
        assert "onboarding_completed" in validated_filters
        assert "invalid_filter" not in validated_filters

        # Check that whitespace was stripped
        assert validated_filters["query"] == "john"
        assert validated_filters["email"] == "john@example.com"
        assert validated_filters["onboarding_completed"] is True

    def test_validate_user_filters_empty_values(self):
        """Test validating user filters with empty values."""
        raw_filters = {"query": "", "email": None, "onboarding_completed": None}

        validated_filters = self.pagination.validate_user_filters(raw_filters)

        # Empty values should be filtered out
        assert len(validated_filters) == 0

    def test_validate_user_filters_boolean_conversion(self):
        """Test boolean conversion in user filters."""
        raw_filters = {"onboarding_completed": "true"}

        validated_filters = self.pagination.validate_user_filters(raw_filters)

        assert validated_filters["onboarding_completed"] is True

        # Test other boolean values
        raw_filters = {"onboarding_completed": "false"}

        validated_filters = self.pagination.validate_user_filters(raw_filters)

        assert validated_filters["onboarding_completed"] is False


class TestUserFilterRequest:
    """Test user filter request schema."""

    def test_user_filter_request_defaults(self):
        """Test user filter request with default values."""
        request = UserFilterRequest()

        assert request.cursor is None
        assert request.limit is None
        assert request.direction == "next"
        assert request.query is None
        assert request.email is None
        assert request.onboarding_completed is None

    def test_user_filter_request_with_values(self):
        """Test user filter request with values."""
        request = UserFilterRequest(
            cursor="test-cursor",
            limit=50,
            direction="prev",
            query="john",
            email="john@example.com",
            onboarding_completed=True,
        )

        assert request.cursor == "test-cursor"
        assert request.limit == 50
        assert request.direction == "prev"
        assert request.query == "john"
        assert request.email == "john@example.com"
        assert request.onboarding_completed is True

    def test_user_filter_request_invalid_direction(self):
        """Test user filter request with invalid direction."""
        with pytest.raises(ValueError):
            UserFilterRequest(direction="invalid")


class TestCursorValidationError:
    """Test cursor validation error schema."""

    def test_cursor_validation_error(self):
        """Test cursor validation error."""
        error = CursorValidationError(
            error="Invalid cursor token",
            error_code="CURSOR_VALIDATION_FAILED",
            cursor_token="invalid-token",
            reason="Token expired",
        )

        assert error.error == "Invalid cursor token"
        assert error.error_code == "CURSOR_VALIDATION_FAILED"
        assert error.cursor_token == "invalid-token"
        assert error.reason == "Token expired"

    def test_cursor_validation_error_defaults(self):
        """Test cursor validation error with default values."""
        error = CursorValidationError(
            error="Invalid cursor token",
            cursor_token="invalid-token",
            reason="Token expired",
        )

        assert error.error == "Invalid cursor token"
        assert error.error_code == "INVALID_CURSOR"  # Default value
        assert error.cursor_token == "invalid-token"
        assert error.reason == "Token expired"


class TestPaginationError:
    """Test pagination error schema."""

    def test_pagination_error(self):
        """Test pagination error."""
        error = PaginationError(
            error="Pagination failed",
            error_code="PAGINATION_ERROR",
            details={"reason": "Invalid parameters"},
        )

        assert error.error == "Pagination failed"
        assert error.error_code == "PAGINATION_ERROR"
        assert error.details == {"reason": "Invalid parameters"}


class TestUserPaginationIntegration:
    """Integration tests for user pagination."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = PaginationConfig(
            secret_key="test-secret-key",
            token_expiry=3600,
            max_page_size=100,
            default_page_size=20,
        )
        self.pagination = UserCursorPagination(self.config)

    def test_full_pagination_flow(self):
        """Test complete pagination flow."""
        # Create initial cursor info
        cursor_info = self.pagination.create_user_cursor_info(
            last_id=123,
            last_created_at="2023-01-01T00:00:00Z",
            filters={"query": "john"},
            direction="next",
            limit=20,
        )

        # Encode cursor
        token = self.pagination.encode_cursor(cursor_info)

        # Decode cursor
        decoded_info = self.pagination.decode_cursor(token)

        # Verify cursor info
        assert decoded_info is not None
        assert decoded_info.last_id == 123
        assert decoded_info.last_timestamp == "2023-01-01T00:00:00Z"
        assert decoded_info.filters == {"query": "john"}
        assert decoded_info.direction == "next"
        assert decoded_info.limit == 20

        # Build query filters
        filters = self.pagination.build_query_filters(decoded_info)

        # Verify filters
        assert "cursor_filter" in filters
        assert "cursor_params" in filters
        assert "query" in filters
        assert filters["query"] == "john"

        # Create pagination response
        users = [{"id": 1}, {"id": 2}]
        response = self.pagination.create_user_pagination_response(
            users=users, cursor_info=decoded_info, has_next=True, has_prev=False
        )

        # Verify response
        assert "users" in response
        assert response["users"] == users
        assert response["has_next"] is True
        assert response["has_prev"] is False
        assert "next_cursor" in response

    def test_pagination_with_various_filters(self):
        """Test pagination with different filter combinations."""
        filter_combinations = [
            {"query": "john"},
            {"email": "john@example.com"},
            {"onboarding_completed": True},
            {"query": "john", "email": "john@example.com"},
            {"query": "john", "onboarding_completed": False},
            {},  # No filters
        ]

        for filters in filter_combinations:
            cursor_info = self.pagination.create_user_cursor_info(
                last_id=123,
                last_created_at="2023-01-01T00:00:00Z",
                filters=filters,
                direction="next",
                limit=20,
            )

            # Validate filters
            validated_filters = self.pagination.validate_user_filters(filters)

            # Build query filters
            query_filters = self.pagination.build_query_filters(cursor_info)

            # Verify that filters are properly handled
            for key, value in validated_filters.items():
                assert key in query_filters
                assert query_filters[key] == value

    def test_bidirectional_pagination(self):
        """Test bidirectional pagination."""
        # Test next page
        # next_cursor_info = self.pagination.create_user_cursor_info(
        #     last_id=123,
        #     last_created_at="2023-01-01T00:00:00Z",
        #     filters={"query": "john"},
        #     direction="next",
        #     limit=20,
        # )

        # next_filters = self.pagination.build_query_filters(next_cursor_info)
        next_ordering = self.pagination.get_ordering_clause("next")

        # Test previous page
        # prev_cursor_info = self.pagination.create_user_cursor_info(
        #     last_id=123,
        #     last_created_at="2023-01-01T00:00:00Z",
        #     filters={"query": "john"},
        #     direction="prev",
        #     limit=20,
        # )

        # prev_filters = self.pagination.build_query_filters(prev_cursor_info)
        prev_ordering = self.pagination.get_ordering_clause("prev")

        # Verify different behavior for next vs prev
        assert next_ordering != prev_ordering
        assert "ASC" in next_ordering
        assert "DESC" in prev_ordering
