"""
Office service files schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field

from services.api.v1.office.models import Provider


# Unified File Models
class DriveFile(BaseModel):
    id: str
    name: str
    mime_type: str
    size: Optional[int] = None
    created_time: datetime
    modified_time: datetime
    web_view_link: Optional[str] = None
    download_link: Optional[str] = None
    thumbnail_link: Optional[str] = None
    parent_folder_id: Optional[str] = None
    is_folder: bool = False
    # Provenance Information
    provider: Provider
    provider_file_id: str
    account_email: EmailStr  # Which account this file belongs to
    account_name: Optional[str] = None  # Display name for the account


class DriveFileList(BaseModel):
    """Response model for drive file lists."""

    success: bool
    data: Optional[List[DriveFile]] = None
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str


class FileListResponse(BaseModel):
    """Response model for file list operations."""

    success: bool
    data: Optional[List[Dict[str, Any]]] = None  # List of files
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str


class FileDetailResponse(BaseModel):
    """Response model for file detail operations."""

    success: bool
    data: Optional[Dict[str, Any]] = None  # File details
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str


class FileSearchResponse(BaseModel):
    """Response model for file search operations."""

    success: bool
    data: Optional[List[Dict[str, Any]]] = None  # Search results
    error: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    provider_used: Optional[Provider] = None
    request_id: str
