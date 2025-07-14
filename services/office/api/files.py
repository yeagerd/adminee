"""
Unified files endpoints for the Office Service.

Provides endpoints for reading files across Google Drive and Microsoft OneDrive providers,
with unified data models, caching, and parallel API calls for optimal performance.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, cast

from fastapi import APIRouter, Depends, Path, Query

from services.common.http_errors import (
    ServiceError,
    ValidationError,
)
from services.office.core.api_client_factory import APIClientFactory
from services.office.core.auth import ServicePermissionRequired
from services.office.core.cache_manager import cache_manager, generate_cache_key
from services.office.core.normalizer import (
    normalize_google_drive_file,
    normalize_microsoft_drive_file,
)
from services.office.models import Provider
from services.office.schemas import (
    ApiResponse,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/files", tags=["files"])

# Initialize dependencies
api_client_factory = APIClientFactory()


@router.get("/", response_model=ApiResponse)
async def get_files(
    user_id: str = Query(..., description="ID of the user to fetch files for"),
    providers: Optional[List[str]] = Query(
        None,
        description="Providers to fetch from (google, microsoft). If not specified, fetches from all available providers",
    ),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum number of files to return per provider"
    ),
    folder_id: Optional[str] = Query(
        None, description="Folder ID to list files from (provider-specific)"
    ),
    file_types: Optional[List[str]] = Query(
        None, description="Filter by file types/mime types"
    ),
    q: Optional[str] = Query(None, description="Search query to filter files"),
    order_by: Optional[str] = Query(
        "modifiedTime desc", description="Sort order (modifiedTime, name, size)"
    ),
    include_folders: bool = Query(
        True, description="Whether to include folders in results"
    ),
    service_name: str = Depends(ServicePermissionRequired(["read_files"])),
) -> ApiResponse:
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
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"[{request_id}] Files request: user_id={user_id}, providers={providers}, limit={limit}"
    )

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
            raise ValidationError(message="No valid providers specified")

        # Build cache key
        cache_params = {
            "providers": valid_providers,
            "limit": limit,
            "folder_id": folder_id or "",
            "file_types": file_types or [],
            "q": q or "",
            "order_by": order_by,
            "include_folders": include_folders,
        }
        cache_key = generate_cache_key(user_id, "unified", "files", cache_params)

        # Check cache first (shortened TTL for files as they change frequently)
        cached_result = await cache_manager.get_from_cache(cache_key)
        if cached_result:
            logger.info(f"[{request_id}] Cache hit for files")
            return ApiResponse(
                success=True, data=cached_result, cache_hit=True, request_id=request_id
            )

        # Fetch files from each provider
        all_files: List = []
        providers_used: List[str] = []
        provider_errors = {}

        async def fetch_from_provider(provider: str) -> None:
            try:
                logger.info(f"[{request_id}] Fetching files from {provider}")

                # Get API client for the provider
                client = await api_client_factory.create_client(user_id, provider)
                if client is None:
                    raise Exception(
                        f"Failed to create API client for provider {provider}"
                    )

                async with client:
                    if provider == "google":
                        from services.office.core.clients.google import (
                            GoogleAPIClient,
                        )

                        if not isinstance(client, GoogleAPIClient):
                            raise Exception(
                                f"Expected GoogleAPIClient for provider {provider}"
                            )

                        # Build query for Google Drive
                        query_parts = []
                        if q:
                            query_parts.append(f"name contains '{q}'")
                        if file_types:
                            mime_queries = [f"mimeType='{ft}'" for ft in file_types]
                            query_parts.append(f"({' or '.join(mime_queries)})")
                        if not include_folders:
                            query_parts.append(
                                "mimeType!='application/vnd.google-apps.folder'"
                            )

                        google_query = (
                            " and ".join(query_parts) if query_parts else None
                        )

                        # Fetch files from Google Drive
                        response = await client.get_files(
                            page_size=limit, query=google_query
                        )

                        # Normalize Google Drive files
                        if "files" in response:
                            for file_data in response["files"]:
                                try:
                                    normalized_file = normalize_google_drive_file(
                                        file_data, user_id
                                    )
                                    all_files.append(normalized_file)
                                except Exception as norm_error:
                                    logger.error(
                                        f"[{request_id}] Failed to normalize Google Drive file: {norm_error}"
                                    )
                                    continue

                        providers_used.append("google")
                        logger.info(
                            f"[{request_id}] Successfully fetched {len(response.get('files', []))} files from Google"
                        )

                    elif provider == "microsoft":
                        from services.office.core.clients.microsoft import (
                            MicrosoftAPIClient,
                        )

                        if not isinstance(client, MicrosoftAPIClient):
                            raise Exception(
                                f"Expected MicrosoftAPIClient for provider {provider}"
                            )

                        # Fetch files from Microsoft OneDrive
                        response = await client.get_drive_items(
                            top=limit,
                            search=q if q else None,
                            order_by=(
                                "lastModifiedDateTime desc"
                                if order_by and order_by.startswith("modifiedTime")
                                else None
                            ),
                        )

                        # Normalize Microsoft OneDrive files
                        if "value" in response:
                            for file_data in response["value"]:
                                try:
                                    # Filter out folders if not requested
                                    if not include_folders and file_data.get("folder"):
                                        continue

                                    # Filter by file types if specified
                                    if file_types:
                                        file_mime = file_data.get("file", {}).get(
                                            "mimeType", ""
                                        )
                                        if not any(
                                            ft in file_mime for ft in file_types
                                        ):
                                            continue

                                    normalized_file = normalize_microsoft_drive_file(
                                        file_data, user_id
                                    )
                                    all_files.append(normalized_file)
                                except Exception as norm_error:
                                    logger.error(
                                        f"[{request_id}] Failed to normalize Microsoft Drive file: {norm_error}"
                                    )
                                    continue

                        providers_used.append("microsoft")
                        logger.info(
                            f"[{request_id}] Successfully fetched {len(response.get('value', []))} files from Microsoft"
                        )

            except Exception as e:
                error_msg = str(e)
                logger.error(
                    f"[{request_id}] Failed to fetch files from {provider}: {error_msg}"
                )
                provider_errors[provider] = error_msg

        # Execute provider requests in parallel
        await asyncio.gather(
            *[fetch_from_provider(provider) for provider in valid_providers],
            return_exceptions=True,
        )

        # Build response data
        files_list = cast(list, all_files if all_files is not None else [])
        providers_list = cast(
            list, providers_used if providers_used is not None else []
        )
        response_data = {
            "files": files_list,
            "providers": providers_list,
            "errors": provider_errors if provider_errors is not None else {},
            "folder_context": {
                "folder_id": folder_id,
                "include_folders": include_folders,
            },
            "request_metadata": {
                "user_id": user_id,
                "providers_requested": valid_providers,
                "limit": limit,
                "order_by": order_by,
            },
        }
        # Fix for mypy: ensure no dict value is None for Collection[str] types
        for k, v in response_data.items():
            if isinstance(v, list) and v is None:
                response_data[k] = []

        # Explicitly ensure all values in response_data that should be collections are not None and are of the correct type
        if response_data.get("files") is None:
            response_data["files"] = []
        if response_data.get("providers") is None:
            response_data["providers"] = []

        # Cache the result (5 minutes TTL for files)
        await cache_manager.set_to_cache(cache_key, response_data, ttl_seconds=300)

        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"[{request_id}] Files request completed in {response_time_ms}ms: {len(all_files)} files from {len(providers_used)} providers"
        )

        # Ensure all collection values are not None for mypy
        for k in ["files", "providers"]:
            if k in response_data and response_data[k] is None:
                response_data[k] = []  # type: ignore[assignment]
        return ApiResponse(
            success=True, data=response_data, cache_hit=False, request_id=request_id
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Files request failed: {e}")
        raise ServiceError(message=f"Failed to fetch files: {str(e)}")


@router.get("/search", response_model=ApiResponse)
async def search_files(
    user_id: str = Query(..., description="ID of the user to search files for"),
    q: str = Query(..., description="Search query"),
    providers: Optional[List[str]] = Query(
        None, description="Providers to search in (google, microsoft)"
    ),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum number of results per provider"
    ),
    file_types: Optional[List[str]] = Query(
        None, description="Filter by file types/mime types"
    ),
    service_name: str = Depends(ServicePermissionRequired(["read_files"])),
) -> ApiResponse:
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
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"[{request_id}] File search request: user_id={user_id}, query='{q}', providers={providers}"
    )

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
            raise ValidationError(message="No valid providers specified")

        # Build cache key for search results
        cache_params = {
            "query": q,
            "providers": valid_providers,
            "limit": limit,
            "file_types": file_types or [],
        }
        cache_key = generate_cache_key(user_id, "unified", "files_search", cache_params)

        # Check cache first (5 minute TTL for search results)
        cached_result = await cache_manager.get_from_cache(cache_key)
        if cached_result:
            logger.info(f"[{request_id}] Cache hit for file search")
            return ApiResponse(
                success=True, data=cached_result, cache_hit=True, request_id=request_id
            )

        # Search files from each provider
        all_results = []
        providers_used = []
        provider_errors = {}

        async def search_provider(provider: str) -> None:
            try:
                logger.info(f"[{request_id}] Searching files in {provider}")

                # Get API client for the provider
                client = await api_client_factory.create_client(user_id, provider)
                if client is None:
                    raise Exception(
                        f"Failed to create API client for provider {provider}"
                    )

                async with client:
                    if provider == "google":
                        from services.office.core.clients.google import (
                            GoogleAPIClient,
                        )

                        if not isinstance(client, GoogleAPIClient):
                            raise Exception(
                                f"Expected GoogleAPIClient for provider {provider}"
                            )

                        # Search Google Drive
                        response = await client.search_files(q, max_results=limit)

                        # Normalize Google Drive search results
                        if "files" in response:
                            for file_data in response["files"]:
                                try:
                                    # Filter by file types if specified
                                    if file_types:
                                        file_mime = file_data.get("mimeType", "")
                                        if not any(
                                            ft in file_mime for ft in file_types
                                        ):
                                            continue

                                    normalized_file = normalize_google_drive_file(
                                        file_data, user_id
                                    )
                                    all_results.append(normalized_file)
                                except Exception as norm_error:
                                    logger.error(
                                        f"[{request_id}] Failed to normalize Google search result: {norm_error}"
                                    )
                                    continue

                        providers_used.append("google")
                        logger.info(
                            f"[{request_id}] Successfully searched Google: {len(response.get('files', []))} results"
                        )

                    elif provider == "microsoft":
                        from services.office.core.clients.microsoft import (
                            MicrosoftAPIClient,
                        )

                        if not isinstance(client, MicrosoftAPIClient):
                            raise Exception(
                                f"Expected MicrosoftAPIClient for provider {provider}"
                            )

                        # Search Microsoft OneDrive
                        response = await client.search_drive_items(q, top=limit)

                        # Normalize Microsoft OneDrive search results
                        if "value" in response:
                            for file_data in response["value"]:
                                try:
                                    # Filter by file types if specified
                                    if file_types:
                                        file_mime = file_data.get("file", {}).get(
                                            "mimeType", ""
                                        )
                                        if not any(
                                            ft in file_mime for ft in file_types
                                        ):
                                            continue

                                    normalized_file = normalize_microsoft_drive_file(
                                        file_data, user_id
                                    )
                                    all_results.append(normalized_file)
                                except Exception as norm_error:
                                    logger.error(
                                        f"[{request_id}] Failed to normalize Microsoft search result: {norm_error}"
                                    )
                                    continue

                        providers_used.append("microsoft")
                        logger.info(
                            f"[{request_id}] Successfully searched Microsoft: {len(response.get('value', []))} results"
                        )

            except Exception as e:
                error_msg = str(e)
                logger.error(
                    f"[{request_id}] Failed to search files in {provider}: {error_msg}"
                )
                provider_errors[provider] = error_msg

        # Execute provider searches in parallel
        await asyncio.gather(
            *[search_provider(provider) for provider in valid_providers],
            return_exceptions=True,
        )

        # Build response data
        response_data = {
            "files": all_results if all_results is not None else [],
            "total_count": len(all_results),
            "providers_used": providers_used if providers_used is not None else [],
            "provider_errors": provider_errors if provider_errors is not None else {},
            "search_metadata": {
                "query": q,
                "user_id": user_id,
                "providers_requested": valid_providers,
                "limit": limit,
                "file_types": file_types,
            },
        }

        # Cache the search results (5 minutes TTL)
        await cache_manager.set_to_cache(cache_key, response_data, ttl_seconds=300)

        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"[{request_id}] File search completed in {response_time_ms}ms: {len(all_results)} results from {len(providers_used)} providers"
        )

        return ApiResponse(
            success=True, data=response_data, cache_hit=False, request_id=request_id
        )  # type: ignore

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] File search failed: {e}")
        raise ServiceError(message=f"Failed to search files: {str(e)}")


@router.get("/{file_id}", response_model=ApiResponse)
async def get_file(
    file_id: str = Path(..., description="File ID (format: provider_originalId)"),
    user_id: str = Query(..., description="ID of the user who owns the file"),
    include_download_url: bool = Query(
        False, description="Whether to include download URL"
    ),
    service_name: str = Depends(ServicePermissionRequired(["read_files"])),
) -> ApiResponse:
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
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"[{request_id}] File detail request: file_id={file_id}, user_id={user_id}"
    )

    try:
        # Parse provider from file_id
        provider, original_file_id = parse_file_id(file_id)

        logger.info(f"[{request_id}] Fetching file from {provider}: {original_file_id}")

        # Get API client for the provider
        client = await api_client_factory.create_client(user_id, provider)
        if client is None:
            raise Exception(f"Failed to create API client for provider {provider}")

        async with client:
            try:
                if provider == "google":
                    from services.office.core.clients.google import (
                        GoogleAPIClient,
                    )

                    if not isinstance(client, GoogleAPIClient):
                        raise Exception(
                            f"Expected GoogleAPIClient for provider {provider}"
                        )

                    # Fetch file from Google Drive
                    response = await client.get_file(original_file_id)

                    # Normalize Google Drive file
                    normalized_file = normalize_google_drive_file(response, user_id)

                elif provider == "microsoft":
                    from services.office.core.clients.microsoft import (
                        MicrosoftAPIClient,
                    )

                    if not isinstance(client, MicrosoftAPIClient):
                        raise Exception(
                            f"Expected MicrosoftAPIClient for provider {provider}"
                        )

                    # Fetch file from Microsoft OneDrive
                    response = await client.get_drive_item(original_file_id)

                    # Normalize Microsoft OneDrive file
                    normalized_file = normalize_microsoft_drive_file(response, user_id)

                else:
                    raise ValidationError(message=f"Unsupported provider: {provider}")

                # Build response data
                response_data = {
                    "file": normalized_file.model_dump(),
                    "provider": provider,
                    "request_metadata": {
                        "user_id": user_id,
                        "file_id": file_id,
                        "include_download_url": include_download_url,
                    },
                }

                # Calculate response time
                end_time = datetime.now(timezone.utc)
                response_time_ms = int((end_time - start_time).total_seconds() * 1000)

                logger.info(
                    f"[{request_id}] File detail request completed in {response_time_ms}ms: {normalized_file.name}"
                )

                return ApiResponse(
                    success=True,
                    data=response_data,
                    cache_hit=False,
                    provider_used=Provider(provider),
                    request_id=request_id,
                )

            except Exception as e:
                error_msg = str(e)
                logger.error(
                    f"[{request_id}] Failed to fetch file from {provider}: {error_msg}"
                )

                # Return error response
                response_data = {
                    "file": [],  # Changed from None to [] for mypy Collection[str] compatibility
                    "provider": provider,
                    "error": error_msg,
                    "request_metadata": {
                        "user_id": user_id,
                        "file_id": file_id,
                        "include_download_url": include_download_url,
                    },
                }

                return ApiResponse(
                    success=False,
                    data=response_data,
                    cache_hit=False,
                    provider_used=Provider(provider),
                    request_id=request_id,
                )

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] File detail request failed: {e}")
        raise ServiceError(message=f"Failed to fetch file: {str(e)}")


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
            raise ValidationError(message="Invalid file ID format")

        parts = file_id.split("_", 1)
        provider_prefix = parts[0].lower()
        original_id = parts[1]

        # Map provider prefixes to standard names
        provider_map = {"google": "google", "microsoft": "microsoft"}

        provider = provider_map.get(provider_prefix)
        if not provider:
            raise ValidationError(message=f"Unknown provider prefix: {provider_prefix}")

        return provider, original_id

    except Exception:
        raise ValidationError(
            message=f"Invalid file ID format: {file_id}. Expected format: 'provider_originalId'",
            field="file_id",
            value=file_id,
        )
