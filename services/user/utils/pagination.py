"""
User-specific cursor pagination implementation.

This module provides user-specific cursor pagination functionality
extending the common base pagination.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from services.common.api.v1.schemas import PaginationConfig
from services.common.pagination.base import BaseCursorPagination, CursorInfo
from services.common.pagination.query_builder import PostgreSQLCursorQueryBuilder


def _parse_iso_datetime(dt_str: str) -> datetime:
    """
    Parse ISO datetime string to datetime object.

    Args:
        dt_str: ISO datetime string

    Returns:
        datetime object with timezone info

    Raises:
        ValueError: If the string cannot be parsed
    """
    try:
        # Try parsing with timezone info
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt
    except ValueError:
        # Try parsing without timezone info (assume UTC)
        dt = datetime.fromisoformat(dt_str)
        return dt.replace(tzinfo=timezone.utc)


class UserCursorPagination(BaseCursorPagination):
    """User-specific cursor pagination implementation."""

    def __init__(self, config: PaginationConfig):
        """Initialize user pagination with configuration."""
        super().__init__(config)
        self.query_builder = PostgreSQLCursorQueryBuilder()

    def build_query_filters(self, cursor_info: CursorInfo) -> Dict[str, Any]:
        """
        Build database query filters based on cursor information.

        Args:
            cursor_info: Cursor information containing filters and position

        Returns:
            Dictionary of query filters
        """
        filters: Dict[str, Any] = {}

        # Add cursor-based position filters
        if cursor_info.direction == "next":
            # For next page: (created_at > last_created_at) OR
            # (created_at = last_created_at AND id > last_id)
            filters["cursor_filter"] = (
                "(created_at > :last_created_at) OR "
                "(created_at = :last_created_at AND id > :last_id)"
            )
            filters["cursor_params"] = {
                "last_created_at": _parse_iso_datetime(cursor_info.last_timestamp),
                "last_id": cursor_info.last_id,
            }
        else:
            # For previous page: (created_at < last_created_at) OR
            # (created_at = last_created_at AND id < last_id)
            filters["cursor_filter"] = (
                "(created_at < :last_created_at) OR "
                "(created_at = :last_created_at AND id < :last_id)"
            )
            filters["cursor_params"] = {
                "last_created_at": _parse_iso_datetime(cursor_info.last_timestamp),
                "last_id": cursor_info.last_id,
            }

        # Add user-specific filters from cursor
        user_filters = cursor_info.filters

        # Query filter (for search)
        if "query" in user_filters and user_filters["query"]:
            filters["query"] = user_filters["query"]

        # Email filter
        if "email" in user_filters and user_filters["email"]:
            filters["email"] = user_filters["email"]

        # Onboarding completed filter
        if (
            "onboarding_completed" in user_filters
            and user_filters["onboarding_completed"] is not None
        ):
            filters["onboarding_completed"] = user_filters["onboarding_completed"]

        return filters

    def get_ordering_clause(self, direction: str = "next") -> str:
        """
        Get the database ordering clause for user pagination.

        Args:
            direction: Pagination direction ('next' or 'prev')

        Returns:
            SQL ordering clause
        """
        if direction == "next":
            return "created_at ASC, id ASC"
        else:
            return "created_at DESC, id DESC"

    def create_user_cursor_info(
        self,
        last_id: int,
        last_created_at: Union[str, datetime],
        filters: Dict[str, Any],
        direction: str = "next",
        limit: int = None,
    ) -> CursorInfo:
        """
        Create cursor information specific to users.

        Args:
            last_id: Integer ID of last user in current page
            last_created_at: ISO timestamp for consistent ordering
            filters: JSON string of active filters (query, email, onboarding_completed)
            direction: 'next' or 'prev'
            limit: Number of items per page

        Returns:
            CursorInfo object
        """
        return self.create_cursor_info(
            last_id=last_id,
            last_timestamp=last_created_at,
            filters=filters,
            direction=direction,
            limit=limit,
        )

    def build_user_query(
        self,
        cursor_info: Optional[CursorInfo] = None,
        additional_filters: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Build a complete user query with cursor pagination.

        Args:
            cursor_info: Optional cursor information for pagination
            additional_filters: Additional filter conditions

        Returns:
            Tuple of (query_string, parameters)
        """
        return self.query_builder.build_base_query(
            table_name="users",
            cursor_info=cursor_info,
            additional_filters=additional_filters,
            id_column="id",
            timestamp_column="created_at",
        )

    def create_user_pagination_response(
        self,
        users: List[Any],
        cursor_info: Optional[CursorInfo] = None,
        has_next: bool = False,
        has_prev: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a user-specific pagination response.

        Args:
            users: List of user objects
            cursor_info: Current cursor information
            has_next: Whether there are more users after this page
            has_prev: Whether there are users before this page

        Returns:
            Dictionary with users and pagination metadata
        """
        response = self.create_pagination_response(
            items=users, cursor_info=cursor_info, has_next=has_next, has_prev=has_prev
        )

        # Rename 'items' to 'users' for user API
        response["users"] = response.pop("items")

        return response

    def validate_user_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize user-specific filters.

        Args:
            filters: Raw filter dictionary

        Returns:
            Sanitized filter dictionary
        """
        validated_filters = {}

        # Validate query filter
        if "query" in filters and filters["query"]:
            query = str(filters["query"]).strip()
            if query:
                validated_filters["query"] = query

        # Validate email filter
        if "email" in filters and filters["email"]:
            email = str(filters["email"]).strip()
            if email:
                validated_filters["email"] = email

        # Validate onboarding completed filter
        if (
            "onboarding_completed" in filters
            and filters["onboarding_completed"] is not None
        ):
            # Convert to boolean if it's a string
            onboarding_completed = filters["onboarding_completed"]
            if isinstance(onboarding_completed, str):
                onboarding_completed = onboarding_completed.lower() in (
                    "true",
                    "1",
                    "yes",
                )
            validated_filters["onboarding_completed"] = bool(onboarding_completed)  # type: ignore[assignment]

        return validated_filters
