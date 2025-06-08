import asyncio
import logging
from typing import List, Optional, Annotated
from fastapi import APIRouter, Depends, Query, HTTPException, status

from schemas.common_schemas import DriveFile, ApiResponse, Provider
from core.dependencies import get_api_client_factory
from core.api_client_factory import APIClientFactory
from core.clients.google import GoogleAPIClient
from core.clients.microsoft import MicrosoftAPIClient
from core.normalizer import normalize_google_drive_file, normalize_microsoft_drive_file
from core.cache_manager import get_from_cache, set_to_cache, generate_cache_key
from api.email import parse_providers

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["Files"])

@router.get("", response_model=ApiResponse[List[DriveFile]])
async def list_files(
    user_id: str,
    providers: Annotated[Optional[str], Query(description="Comma-separated list of providers (e.g., google,microsoft)")] = None,
    api_client_factory: APIClientFactory = Depends(get_api_client_factory)
):
    try:
        requested_providers = parse_providers(providers)
    except HTTPException as e:
        return ApiResponse[List[DriveFile]](success=False, error={"type": "validation_error", "message": e.detail}, data=[])

    cache_params = {"providers": sorted([p.value for p in requested_providers])}
    cache_key = generate_cache_key(user_id=user_id, endpoint="files_list", params=cache_params)

    cached_response = await get_from_cache(cache_key)
    if cached_response:
        try:
            restored_files = [DriveFile(**file_data) for file_data in cached_response]
            return ApiResponse[List[DriveFile]](data=restored_files, cache_hit=True, success=True)
        except Exception as e:
            logger.warning(f"Cache data for {cache_key} (files) is stale or invalid: {e}")


    all_files: List[DriveFile] = []
    for provider_enum in requested_providers:
        client = await api_client_factory.get_client(user_id, provider_enum)
        if not client:
            logger.warning(f"Could not get client for provider {provider_enum.value} (files list) for user {user_id}")
            continue

        try:
            raw_result_list: Optional[dict] = None
            if isinstance(client, GoogleAPIClient):
                raw_result_list = await client.list_drive_files()
                if raw_result_list and 'files' in raw_result_list:
                    for item in raw_result_list.get("files", []):
                        normalized = normalize_google_drive_file(item, account_email=user_id)
                        if normalized: all_files.append(normalized)
            elif isinstance(client, MicrosoftAPIClient):
                raw_result_list = await client.list_onedrive_files(item_path="root")
                if raw_result_list and 'value' in raw_result_list:
                    for item in raw_result_list.get("value", []):
                        normalized = normalize_microsoft_drive_file(item, account_email=user_id)
                        if normalized: all_files.append(normalized)
        except Exception as e:
            logger.error(f"Error processing files for {provider_enum.value} for user {user_id}: {e}", exc_info=True)
        finally:
            if client: await client.close()

    if all_files:
        await set_to_cache(cache_key, [f.model_dump() for f in all_files])
    return ApiResponse[List[DriveFile]](data=all_files, success=True)
