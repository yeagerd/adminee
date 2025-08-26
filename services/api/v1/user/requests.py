"""
User-specific request schemas that extend common pagination schemas.
"""

from typing import Optional
from pydantic import BaseModel, Field

from services.api.v1.common.pagination import CursorPaginationRequest


class UserSearchRequest(CursorPaginationRequest):
    """Request schema for user search with cursor pagination."""

    # Search parameters
    query: Optional[str] = Field(None, description="Search query for users")
    email: Optional[str] = Field(None, description="Filter by email")
    onboarding_completed: Optional[bool] = Field(
        None, description="Filter by onboarding completion status"
    )


class UserListRequest(CursorPaginationRequest):
    """Request schema for user listing with cursor pagination."""

    # Filter parameters
    query: Optional[str] = Field(None, description="Search query for users")
    email: Optional[str] = Field(None, description="Filter by email")
    onboarding_completed: Optional[bool] = Field(
        None, description="Filter by onboarding completion status"
    )
