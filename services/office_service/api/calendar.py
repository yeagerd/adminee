import asyncio
import logging
from typing import List, Optional, Annotated
from fastapi import APIRouter, Depends, Query, HTTPException, status
from datetime import datetime, timezone

from schemas.common_schemas import CalendarEvent, ApiResponse, Provider
from core.dependencies import get_api_client_factory
from core.api_client_factory import APIClientFactory
from core.clients.google import GoogleAPIClient
from core.clients.microsoft import MicrosoftAPIClient
from core.normalizer import normalize_google_calendar_event, normalize_microsoft_calendar_event
from core.cache_manager import get_from_cache, set_to_cache, generate_cache_key
from api.email import parse_providers

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calendar", tags=["Calendar"])

@router.get("/events", response_model=ApiResponse[List[CalendarEvent]])
async def list_calendar_events(
    user_id: str,
    start_time: datetime,
    end_time: datetime,
    providers: Annotated[Optional[str], Query(description="Comma-separated list of providers (e.g., google,microsoft)")] = None,
    api_client_factory: APIClientFactory = Depends(get_api_client_factory)
):
    try:
        requested_providers = parse_providers(providers)
    except HTTPException as e:
        return ApiResponse[List[CalendarEvent]](success=False, error={"type": "validation_error", "message": e.detail}, data=[])

    cache_params = {
        "providers": sorted([p.value for p in requested_providers]),
        "start_time": start_time.isoformat(), "end_time": end_time.isoformat()
    }
    cache_key = generate_cache_key(user_id=user_id, endpoint="calendar_events_list", params=cache_params)

    cached_response = await get_from_cache(cache_key)
    if cached_response:
        try:
            restored_events = [CalendarEvent(**evt_data) for evt_data in cached_response]
            return ApiResponse[List[CalendarEvent]](data=restored_events, cache_hit=True, success=True)
        except Exception as e:
            logger.warning(f"Cache data for {cache_key} (calendar) is stale or invalid: {e}")


    all_events: List[CalendarEvent] = []
    for provider_enum in requested_providers:
        client = await api_client_factory.get_client(user_id, provider_enum)
        if not client:
            logger.warning(f"Could not get client for provider {provider_enum.value} (calendar list) for user {user_id}")
            continue

        provider_api_params = {}
        if isinstance(client, GoogleAPIClient): provider_api_params = {"timeMin": start_time.isoformat(), "timeMax": end_time.isoformat()}
        elif isinstance(client, MicrosoftAPIClient): provider_api_params = {"startDateTime": start_time.isoformat(), "endDateTime": end_time.isoformat()}

        try:
            raw_result_list: Optional[dict] = None
            if isinstance(client, GoogleAPIClient):
                raw_result_list = await client.list_calendar_events(calendar_id="primary", params=provider_api_params)
                if raw_result_list and 'items' in raw_result_list:
                    for item in raw_result_list.get("items", []):
                        normalized = normalize_google_calendar_event(item, account_email=user_id, calendar_id=f"google_primary_{user_id}", calendar_name="Primary")
                        if normalized: all_events.append(normalized)
            elif isinstance(client, MicrosoftAPIClient):
                raw_result_list = await client.list_calendar_events(params=provider_api_params)
                if raw_result_list and 'value' in raw_result_list:
                    for item in raw_result_list.get("value", []):
                        normalized = normalize_microsoft_calendar_event(item, account_email=user_id, calendar_id=f"microsoft_primary_{user_id}", calendar_name="Calendar")
                        if normalized: all_events.append(normalized)
        except Exception as e:
            logger.error(f"Error processing calendar events for {provider_enum.value} for user {user_id}: {e}", exc_info=True)
        finally:
            if client: await client.close()

    if all_events:
        await set_to_cache(cache_key, [evt.model_dump() for evt in all_events])
    return ApiResponse[List[CalendarEvent]](data=all_events, success=True)
