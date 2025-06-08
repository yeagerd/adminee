"""
Unified files endpoints for the Office Service.

Provides endpoints for reading files across Google Drive and Microsoft OneDrive providers,
with unified data models, caching, and parallel API calls for optimal performance.
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import uuid

from fastapi import APIRouter, HTTPException, Query, Path
from fastapi.responses import JSONResponse

from services.office_service.core.config import settings
from services.office_service.core.api_client_factory import APIClientFactory
from services.office_service.core.normalizer import normalize_google_drive_file
from services.office_service.core.cache_manager import cache_manager, generate_cache_key
from services.office_service.schemas import DriveFile, ApiResponse, PaginatedResponse
from services.office_service.models import Provider

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/files", tags=["files"])

# Initialize dependencies
api_client_factory = APIClientFactory()


@router.get("/", response_model=ApiResponse)
async def get_files(
    user_id: str = Query(..., description="ID of the user to fetch files for"),
    providers: Optional[List[str]] = Query(None, description="Providers to fetch from (google, microsoft). If not specified, fetches from all available providers"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of files to return per provider"),
    folder_id: Optional[str] = Query(None, description="Folder ID to list files from (provider-specific)"),
    file_types: Optional[List[str]] = Query(None, description="Filter by file types/mime types"),
    q: Optional[str] = Query(None, description="Search query to filter files"),
    order_by: Optional[str] = Query("modifiedTime desc", description="Sort order (modifiedTime, name, size)"),
    include_folders: bool = Query(True, description="Whether to include folders in results")
):
    """
    Get unified files from multiple providers.
    
    Fetches files from Google Drive and Microsoft OneDrive APIs,
    normalizes them to a unified format, and returns aggregated results.
    Responses are cached for improved performance.
    
    Args:
        user_id: ID of the user to fetch files for
        providers: List of providers to query (defaults to all available)
        limit: Maximum files per provider
        folder_id: Specific folder to list (provider-specific ID)
        file_types: Filter by file types/mime types
        q: Search query string
        order_by: Sort order for results
        include_folders: Whether to include folders
        
    Returns:
        ApiResponse with aggregated files
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.utcnow()
    
    logger.info(f"[{request_id}] Files request: user_id={user_id}, providers={providers}, limit={limit}")
    
    try:
        # Default to all providers if not specified
        if not providers:
            providers = ["google", "microsoft"]
        
        # Validate providers
        valid_providers = []
        for provider in providers:
            if provider.lower() in ["google", "microsoft"]:
                valid_providers.append(provider.lower())
            else:
                logger.warning(f"[{request_id}] Invalid provider: {provider}")
        
        if not valid_providers:
            raise HTTPException(status_code=400, detail="No valid providers specified")
        
        # Build cache key
        cache_params = {
            "providers": valid_providers,
            "limit": limit,
            "folder_id": folder_id or "",
            "file_types": file_types or [],
            "q": q or "",
            "order_by": order_by,
            "include_folders": include_folders
        }
        cache_key = generate_cache_key(user_id, "unified", "files", cache_params)
        
        # Check cache first (shortened TTL for files as they change frequently)
        cached_result = await cache_manager.get_from_cache(cache_key)
        if cached_result:
            logger.info(f"[{request_id}] Cache hit for files")
            return ApiResponse(
                success=True,
                data=cached_result,
                cache_hit=True,
                request_id=request_id
            )
        
        # Build response with placeholder for MVP
        response_data = {
            "files": [],
            "total_count": 0,
            "providers_used": [],
            "provider_errors": {"google": "Not yet implemented", "microsoft": "Not yet implemented"},
            "folder_context": {
                "folder_id": folder_id,
                "include_folders": include_folders
            },
            "request_metadata": {
                "user_id": user_id,
                "providers_requested": valid_providers,
                "limit": limit,
                "order_by": order_by
            }
        }
        
        # Calculate response time
        end_time = datetime.utcnow()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        logger.info(f"[{request_id}] Files request completed in {response_time_ms}ms (placeholder)")
        
        return ApiResponse(
            success=True,
            data=response_data,
            cache_hit=False,
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Files request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch files: {str(e)}")


@router.get("/search", response_model=ApiResponse)
async def search_files(
    user_id: str = Query(..., description="ID of the user to search files for"),
    q: str = Query(..., description="Search query"),
    providers: Optional[List[str]] = Query(None, description="Providers to search in (google, microsoft)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results per provider"),
    file_types: Optional[List[str]] = Query(None, description="Filter by file types/mime types")
):
    """
    Search files across multiple providers.
    
    Performs a unified search across Google Drive and Microsoft OneDrive,
    returning aggregated and normalized results.
    
    Args:
        user_id: ID of the user to search files for
        q: Search query string
        providers: List of providers to search (defaults to all)
        limit: Maximum results per provider
        file_types: Filter by file types
        
    Returns:
        ApiResponse with search results
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.utcnow()
    
    logger.info(f"[{request_id}] File search request: user_id={user_id}, query='{q}', providers={providers}")
    
    try:
        # Default to all providers if not specified
        if not providers:
            providers = ["google", "microsoft"]
        
        # Validate providers
        valid_providers = []
        for provider in providers:
            if provider.lower() in ["google", "microsoft"]:
                valid_providers.append(provider.lower())
            else:
                logger.warning(f"[{request_id}] Invalid provider: {provider}")
        
        if not valid_providers:
            raise HTTPException(status_code=400, detail="No valid providers specified")
        
        # Build response with placeholder for MVP
        response_data = {
            "files": [],
            "total_count": 0,
            "search_query": q,
            "providers_used": [],
            "provider_errors": {"google": "Not yet implemented", "microsoft": "Not yet implemented"},
            "request_metadata": {
                "user_id": user_id,
                "providers_requested": valid_providers,
                "limit": limit,
                "file_types": file_types
            }
        }
        
        # Calculate response time
        end_time = datetime.utcnow()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        logger.info(f"[{request_id}] File search completed in {response_time_ms}ms (placeholder)")
        
        return ApiResponse(
            success=True,
            data=response_data,
            cache_hit=False,
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] File search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search files: {str(e)}")


@router.get("/{file_id}", response_model=ApiResponse)
async def get_file(
    file_id: str = Path(..., description="File ID (format: provider_originalId)"),
    user_id: str = Query(..., description="ID of the user who owns the file"),
    include_download_url: bool = Query(False, description="Whether to include download URL")
):
    """
    Get a specific file by ID.
    
    The file_id should be in the format "provider_originalId" (e.g., "google_abc123" or "microsoft_xyz789").
    This endpoint determines the correct provider from the file ID and fetches the full file details.
    
    Args:
        file_id: File ID with provider prefix
        user_id: ID of the user who owns the file
        include_download_url: Whether to include download URL
        
    Returns:
        ApiResponse with the specific file
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.utcnow()
    
    logger.info(f"[{request_id}] File detail request: file_id={file_id}, user_id={user_id}")
    
    try:
        # Parse provider from file_id
        provider, original_file_id = parse_file_id(file_id)
        
        # Build response with placeholder for MVP
        response_data = {
            "file": None,
            "provider": provider,
            "error": "File detail endpoint not yet implemented",
            "request_metadata": {
                "user_id": user_id,
                "file_id": file_id,
                "include_download_url": include_download_url
            }
        }
        
        # Calculate response time
        end_time = datetime.utcnow()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        logger.info(f"[{request_id}] File detail request completed in {response_time_ms}ms (placeholder)")
        
        return ApiResponse(
            success=False,
            data=response_data,
            cache_hit=False,
            provider_used=provider,
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] File detail request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch file: {str(e)}")


def parse_file_id(file_id: str) -> tuple[str, str]:
    """
    Parse a unified file ID to extract provider and original ID.
    
    Args:
        file_id: Unified file ID (format: "provider_originalId")
        
    Returns:
        Tuple of (provider, original_file_id)
        
    Raises:
        HTTPException: If file ID format is invalid
    """
    try:
        if "_" not in file_id:
            raise ValueError("Invalid file ID format")
        
        parts = file_id.split("_", 1)
        provider_prefix = parts[0].lower()
        original_id = parts[1]
        
        # Map provider prefixes to standard names
        provider_map = {
            "google": "google",
            "microsoft": "microsoft"
        }
        
        provider = provider_map.get(provider_prefix)
        if not provider:
            raise ValueError(f"Unknown provider prefix: {provider_prefix}")
        
        return provider, original_id
        
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file ID format: {file_id}. Expected format: 'provider_originalId'"
        ) 