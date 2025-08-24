"""
User service pagination schemas.

This module defines user-specific pagination schemas that extend the
common pagination schemas.
"""

from typing import Any, Dict, List, Optional

from common.pagination.schemas import CursorPaginationRequest, CursorPaginationResponse
from pydantic import BaseModel, Field


class UserCursorPaginationRequest(CursorPaginationRequest):
    """Request schema for user cursor-based pagination."""

    # User-specific filter parameters
    query: Optional[str] = Field(None, description="Search query for users")
    email: Optional[str] = Field(None, description="Filter by email")
    onboarding_completed: Optional[bool] = Field(
        None, description="Filter by onboarding completion status"
    )


class UserCursorPaginationResponse(CursorPaginationResponse):
    """Response schema for user cursor-based pagination."""

        # Override items to be users - properly override parent field
    users: List[dict] = Field(description="List of users")
    
    # Override the items field from parent class to use users data
    items: List[dict] = Field(default_factory=list, description="List of users")
    
    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        # Ensure items field is synchronized with users
        if "users" in data:
            self.items = data["users"]
    
    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        # Override to maintain API contract - output 'users' field, not 'items'
        data = super().model_dump(**kwargs)
        # Remove items field to maintain API contract
        if "items" in data:
            del data["items"]
        return data
    
    def __setattr__(self, name: str, value: Any) -> None:
        # Ensure items and users fields stay synchronized without infinite recursion
        if name == "users":
            # Set users first, then update items to avoid recursion
            super().__setattr__(name, value)
            if hasattr(self, '_items_initialized'):
                super().__setattr__("items", value)
        elif name == "items":
            # Set items first, then update users to avoid recursion
            super().__setattr__(name, value)
            if hasattr(self, '_items_initialized'):
                super().__setattr__("users", value)
        else:
            super().__setattr__(name, value)
        
        # Mark items as initialized after first set
        if name in ["users", "items"]:
            self._items_initialized = True


class UserSearchRequest(BaseModel):
    """Request schema for user search with cursor pagination."""

    # Pagination parameters
    cursor: Optional[str] = Field(None, description="Cursor token for pagination")
    limit: Optional[int] = Field(
        None, ge=1, le=100, description="Number of users per page"
    )
    direction: Optional[str] = Field(
        "next", pattern="^(next|prev)$", description="Pagination direction"
    )

    # Search parameters
    query: Optional[str] = Field(None, description="Search query for users")
    email: Optional[str] = Field(None, description="Filter by email")
    onboarding_completed: Optional[bool] = Field(
        None, description="Filter by onboarding completion status"
    )


class UserListRequest(BaseModel):
    """Request schema for user listing with cursor pagination."""

    # Pagination parameters
    cursor: Optional[str] = Field(None, description="Cursor token for pagination")
    limit: Optional[int] = Field(
        None, ge=1, le=100, description="Number of users per page"
    )
    direction: Optional[str] = Field(
        "next", pattern="^(next|prev)$", description="Pagination direction"
    )

    # Filter parameters
    query: Optional[str] = Field(None, description="Search query for users")
    email: Optional[str] = Field(None, description="Filter by email")
    onboarding_completed: Optional[bool] = Field(
        None, description="Filter by onboarding completion status"
    )


class UserListResponse(BaseModel):
    """Response schema for user listing with cursor pagination."""

    users: List[dict] = Field(description="List of users")
    next_cursor: Optional[str] = Field(None, description="Cursor token for next page")
    prev_cursor: Optional[str] = Field(
        None, description="Cursor token for previous page"
    )
    has_next: bool = Field(description="Whether there are more users after this page")
    has_prev: bool = Field(description="Whether there are users before this page")
    limit: int = Field(description="Number of users per page")


class UserSearchResponse(BaseModel):
    """Response schema for user search with cursor pagination."""

    users: List[dict] = Field(description="List of users matching search criteria")
    next_cursor: Optional[str] = Field(None, description="Cursor token for next page")
    prev_cursor: Optional[str] = Field(
        None, description="Cursor token for previous page"
    )
    has_next: bool = Field(description="Whether there are more users after this page")
    has_prev: bool = Field(description="Whether there are users before this page")
    limit: int = Field(description="Number of users per page")
    search_query: Optional[str] = Field(
        None, description="The search query that was used"
    )


class CursorValidationError(BaseModel):
    """Error response for invalid cursor tokens."""

    error: str = Field(description="Error message")
    error_code: str = Field(default="INVALID_CURSOR", description="Error code")
    cursor_token: Optional[str] = Field(None, description="The invalid cursor token")
    reason: str = Field(description="Reason for validation failure")


class PaginationError(BaseModel):
    """Error response for pagination-related errors."""

    error: str = Field(description="Error message")
    error_code: str = Field(description="Error code")
    details: Optional[dict] = Field(None, description="Additional error details")
