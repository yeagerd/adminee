"""
Shipments service pagination schemas.

This module defines shipments-specific pagination schemas that extend the
common pagination schemas.
"""

from typing import Any, Dict, List, Optional

from common.pagination.schemas import CursorPaginationRequest, CursorPaginationResponse
from pydantic import BaseModel, ConfigDict, Field


class PackageCursorPaginationRequest(CursorPaginationRequest):
    """Request schema for package cursor-based pagination."""

    # Shipments-specific filter parameters
    tracking_number: Optional[str] = Field(
        None, description="Filter by tracking number"
    )
    carrier: Optional[str] = Field(None, description="Filter by carrier")
    status: Optional[str] = Field(None, description="Filter by package status")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    date_range: Optional[str] = Field(
        None,
        pattern="^(7|30|90|all)$",
        description="Filter by date range: 7, 30, 90 days, or 'all'",
    )


class PackageCursorPaginationResponse(CursorPaginationResponse):
    """Response schema for package cursor-based pagination."""

    # Override items to be packages - properly override parent field
    packages: List[dict] = Field(description="List of packages")
    
    # Override the items field from parent class to use packages data
    items: List[dict] = Field(default_factory=list, description="List of packages")
    
    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        # Ensure items field is synchronized with packages
        if 'packages' in data:
            self.items = data['packages']
    
    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        # Override to use packages field instead of items
        data = super().model_dump(**kwargs)
        data['items'] = self.packages
        if 'packages' in data:
            del data['packages']
        return data
    
    def __setattr__(self, name: str, value: Any) -> None:
        # Ensure items and packages fields stay synchronized
        if name == 'packages':
            super().__setattr__('items', value)
        elif name == 'items':
            super().__setattr__('packages', value)
        super().__setattr__(name, value)


class PackageSearchRequest(BaseModel):
    """Request schema for package search with cursor pagination."""

    # Pagination parameters
    cursor: Optional[str] = Field(None, description="Cursor token for pagination")
    limit: Optional[int] = Field(
        None, ge=1, le=100, description="Number of packages per page"
    )
    direction: Optional[str] = Field(
        "next", pattern="^(next|prev)$", description="Pagination direction"
    )

    # Search parameters
    tracking_number: Optional[str] = Field(
        None, description="Search by tracking number"
    )
    carrier: Optional[str] = Field(None, description="Filter by carrier")
    status: Optional[str] = Field(None, description="Filter by package status")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    query: Optional[str] = Field(None, description="General search query")
    date_range: Optional[str] = Field(
        None,
        pattern="^(7|30|90|all)$",
        description="Filter by date range: 7, 30, 90 days, or 'all'",
    )


class PackageListRequest(BaseModel):
    """Request schema for package listing with cursor pagination."""

    # Pagination parameters
    cursor: Optional[str] = Field(None, description="Cursor token for pagination")
    limit: Optional[int] = Field(
        None, ge=1, le=100, description="Number of packages per page"
    )
    direction: Optional[str] = Field(
        "next", pattern="^(next|prev)$", description="Pagination direction"
    )

    # Filter parameters
    carrier: Optional[str] = Field(None, description="Filter by carrier")
    status: Optional[str] = Field(None, description="Filter by package status")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    date_range: Optional[str] = Field(
        None,
        pattern="^(7|30|90|all)$",
        description="Filter by date range: 7, 30, 90 days, or 'all'",
    )


class PackageListResponse(BaseModel):
    """Response schema for package listing with cursor pagination."""

    packages: List[dict] = Field(description="List of packages")
    next_cursor: Optional[str] = Field(None, description="Cursor token for next page")
    prev_cursor: Optional[str] = Field(
        None, description="Cursor token for previous page"
    )
    has_next: bool = Field(
        description="Whether there are more packages after this page"
    )
    has_prev: bool = Field(description="Whether there are packages before this page")
    limit: int = Field(description="Number of packages per page")


class PackageSearchResponse(BaseModel):
    """Response schema for package search with cursor pagination."""

    packages: List[dict] = Field(
        description="List of packages matching search criteria"
    )
    next_cursor: Optional[str] = Field(None, description="Cursor token for next page")
    prev_cursor: Optional[str] = Field(
        None, description="Cursor token for previous page"
    )
    has_next: bool = Field(
        description="Whether there are more packages after this page"
    )
    has_prev: bool = Field(description="Whether there are packages before this page")
    limit: int = Field(description="Number of packages per page")
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
