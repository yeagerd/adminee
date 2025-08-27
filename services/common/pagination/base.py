"""
Base cursor pagination implementation.

This module provides the foundation for cursor-based pagination across all services.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from itsdangerous import BadSignature, SignatureExpired

from ..api.v1.schemas import PaginationConfig
from .token_manager import TokenManager

T = TypeVar("T")


@dataclass
class CursorInfo:
    """Cursor information for pagination."""

    last_id: Union[str, int]
    last_timestamp: str
    filters: Dict[str, Any]
    direction: str
    limit: int
    created_at: str


class BaseCursorPagination(ABC, Generic[T]):
    """
    Abstract base class for cursor-based pagination.

    This class provides common functionality for cursor-based pagination
    across all Briefly services.
    """

    def __init__(self, config: PaginationConfig):
        """
        Initialize the pagination instance.

        Args:
            config: Pagination configuration including secret key and limits
        """
        self.config = config
        self.token_manager = TokenManager(config.secret_key, config.token_expiry)
        self.max_page_size = config.max_page_size
        self.default_page_size = config.default_page_size

    def encode_cursor(self, cursor_info: CursorInfo) -> str:
        """
        Encode cursor information into a secure token.

        Args:
            cursor_info: Cursor information to encode

        Returns:
            URL-safe encoded token string
        """
        cursor_dict = asdict(cursor_info)
        return self.token_manager.encode_token(cursor_dict)

    def decode_cursor(self, cursor_token: str) -> Optional[CursorInfo]:
        """
        Decode a cursor token back to cursor information.

        Args:
            cursor_token: Encoded cursor token

        Returns:
            CursorInfo object or None if invalid/expired
        """
        try:
            cursor_dict = self.token_manager.decode_token(cursor_token)
            return CursorInfo(**cursor_dict)
        except (BadSignature, SignatureExpired, ValueError, KeyError):
            return None

    def validate_cursor(self, cursor_token: str) -> bool:
        """
        Validate if a cursor token is valid and not expired.

        Args:
            cursor_token: Encoded cursor token

        Returns:
            True if valid, False otherwise
        """
        return self.decode_cursor(cursor_token) is not None

    def sanitize_limit(self, limit: Optional[int]) -> int:
        """
        Sanitize and validate the page size limit.

        Args:
            limit: Requested page size limit

        Returns:
            Sanitized limit within allowed bounds
        """
        if limit is None:
            return self.default_page_size

        # Ensure limit is within bounds
        limit = max(1, min(limit, self.max_page_size))
        return limit

    def create_cursor_info(
        self,
        last_id: Union[str, int],
        last_timestamp: Union[str, datetime],
        filters: Dict[str, Any],
        direction: str = "next",
        limit: int = None,
    ) -> CursorInfo:
        """
        Create cursor information for pagination.

        Args:
            last_id: ID of the last item in the current page
            last_timestamp: Timestamp of the last item
            filters: Active filters for the query
            direction: Pagination direction ('next' or 'prev')
            limit: Page size limit

        Returns:
            CursorInfo object
        """
        # Convert datetime to ISO string if needed
        if isinstance(last_timestamp, datetime):
            last_timestamp = last_timestamp.isoformat()

        # Sanitize limit
        limit = self.sanitize_limit(limit)

        # Create cursor info
        return CursorInfo(
            last_id=last_id,
            last_timestamp=last_timestamp,
            filters=filters,
            direction=direction,
            limit=limit,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    @abstractmethod
    def build_query_filters(self, cursor_info: CursorInfo) -> Dict[str, Any]:
        """
        Build database query filters based on cursor information.

        Args:
            cursor_info: Cursor information containing filters and position

        Returns:
            Dictionary of query filters
        """
        pass

    @abstractmethod
    def get_ordering_clause(self, direction: str = "next") -> str:
        """
        Get the database ordering clause for cursor-based pagination.

        Args:
            direction: Pagination direction ('next' or 'prev')

        Returns:
            SQL ordering clause
        """
        pass

    def create_pagination_response(
        self,
        items: List[T],
        cursor_info: Optional[CursorInfo] = None,
        has_next: bool = False,
        has_prev: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a pagination response with cursor information.

        Args:
            items: List of items for the current page
            cursor_info: Current cursor information
            has_next: Whether there are more items after this page
            has_prev: Whether there are items before this page

        Returns:
            Dictionary with items and pagination metadata
        """
        response = {
            "items": items,
            "has_next": has_next,
            "has_prev": has_prev,
            "limit": cursor_info.limit if cursor_info else self.default_page_size,
        }

        # Add cursor tokens if we have cursor info
        if cursor_info:
            if has_next:
                next_cursor_info = CursorInfo(
                    last_id=cursor_info.last_id,
                    last_timestamp=cursor_info.last_timestamp,
                    filters=cursor_info.filters,
                    direction="next",
                    limit=cursor_info.limit,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                response["next_cursor"] = self.encode_cursor(next_cursor_info)

            if has_prev:
                prev_cursor_info = CursorInfo(
                    last_id=cursor_info.last_id,
                    last_timestamp=cursor_info.last_timestamp,
                    filters=cursor_info.filters,
                    direction="prev",
                    limit=cursor_info.limit,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                response["prev_cursor"] = self.encode_cursor(prev_cursor_info)

        return response
