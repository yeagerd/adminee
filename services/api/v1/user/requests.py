"""
User-specific request schemas that extend common pagination schemas.
"""

from typing import Optional

from pydantic import Field

from services.common.pagination.schemas import CursorPaginationRequest


class UserFilterRequest(CursorPaginationRequest):
    """Request schema for user filtering and listing with cursor pagination.

    This schema is used for both search and list operations, as they share
    the same filtering and pagination parameters. The distinction between
    search and list operations is handled at the service level based on
    whether a query parameter is provided.
    """

    # Filter parameters
    query: Optional[str] = Field(None, description="Search query for users")
    email: Optional[str] = Field(None, description="Filter by email")
    onboarding_completed: Optional[bool] = Field(
        None, description="Filter by onboarding completion status"
    )
