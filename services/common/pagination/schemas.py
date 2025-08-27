"""
Pagination schemas and data models.

This module defines the base schemas and data models for cursor-based pagination
across all Briefly services.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field

T = TypeVar("T")


class CursorData(BaseModel):
    """Base cursor data structure."""

    last_id: Union[str, int]
    last_timestamp: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    direction: str = "next"
    limit: int = 20
    created_at: str


class PaginationConfig(BaseModel):
    """Configuration for pagination settings."""

    secret_key: str
    token_expiry: int = 3600  # 1 hour in seconds
    max_page_size: int = 100
    default_page_size: int = 20


class CursorPaginationRequest(BaseModel):
    """Base request schema for cursor-based pagination."""

    cursor: Optional[str] = Field(None, description="Cursor token for pagination")
    limit: Optional[int] = Field(
        None, ge=1, le=100, description="Number of items per page"
    )
    direction: Optional[str] = Field(
        "next", pattern="^(next|prev)$", description="Pagination direction"
    )


class CursorPaginationResponse(BaseModel, Generic[T]):
    """Base response schema for cursor-based pagination."""

    items: List[T]
    next_cursor: Optional[str] = Field(None, description="Cursor token for next page")
    prev_cursor: Optional[str] = Field(
        None, description="Cursor token for previous page"
    )
    has_next: bool = Field(description="Whether there are more items after this page")
    has_prev: bool = Field(description="Whether there are items before this page")
    limit: int = Field(description="Number of items per page")


class PaginationError(BaseModel):
    """Error response for pagination-related errors."""

    error: str = Field(description="Error message")
    error_code: str = Field(description="Error code")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )


class PaginationMetadata(BaseModel):
    """Metadata for pagination operations."""

    total_items: Optional[int] = Field(
        None, description="Total number of items (if available)"
    )
    current_page_size: int = Field(description="Number of items in current page")
    cursor_age: Optional[int] = Field(
        None, description="Age of cursor token in seconds"
    )
    query_time_ms: Optional[float] = Field(
        None, description="Query execution time in milliseconds"
    )


class CursorValidationError(BaseModel):
    """Validation error for cursor tokens."""

    error: str = Field(description="Validation error message")
    error_code: str = Field(description="Error code for cursor validation failures")
    cursor_token: Optional[str] = Field(None, description="The invalid cursor token")
    reason: str = Field(description="Reason for validation failure")


class PaginationState(BaseModel):
    """State information for pagination."""

    current_cursor: Optional[str] = Field(None, description="Current cursor token")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Active filters")
    sort_order: str = Field("asc", description="Current sort order")
    page_size: int = Field(20, description="Current page size")


class PaginationInfo(BaseModel):
    """Information about pagination capabilities."""

    supports_cursor_pagination: bool = Field(
        True, description="Whether cursor pagination is supported"
    )
    supports_offset_pagination: bool = Field(
        False, description="Whether offset pagination is supported"
    )
    max_page_size: int = Field(100, description="Maximum allowed page size")
    default_page_size: int = Field(20, description="Default page size")
    cursor_expiry_seconds: int = Field(
        3600, description="Cursor token expiry time in seconds"
    )


class CursorPaginationParams(BaseModel):
    """Parameters for cursor-based pagination."""

    cursor: Optional[str] = None
    limit: Optional[int] = Field(None, ge=1, le=100)
    direction: str = Field("next", pattern="^(next|prev)$")

    def get_sanitized_limit(self, default_limit: int = 20, max_limit: int = 100) -> int:
        """Get sanitized limit value."""
        if self.limit is None:
            return default_limit
        return max(1, min(self.limit, max_limit))


class PaginationResult(BaseModel, Generic[T]):
    """Result of a pagination operation."""

    items: List[T]
    pagination: CursorPaginationResponse[T]
    metadata: Optional[PaginationMetadata] = None
    state: Optional[PaginationState] = None
