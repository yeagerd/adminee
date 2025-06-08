"""
Unified calendar endpoints for the Office Service.

Provides endpoints for reading calendar events across Google and Microsoft providers,
with unified data models, caching, and parallel API calls for optimal performance.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query

from services.office_service.core.api_client_factory import APIClientFactory
from services.office_service.core.cache_manager import cache_manager, generate_cache_key
from services.office_service.core.normalizer import normalize_google_calendar_event
from services.office_service.models import Provider
from services.office_service.schemas import (
    ApiResponse,
    CalendarEvent,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/calendar", tags=["calendar"])

# Initialize dependencies
api_client_factory = APIClientFactory()


@router.get("/events", response_model=ApiResponse)
async def get_calendar_events(
    user_id: str = Query(..., description="ID of the user to fetch events for"),
    providers: Optional[List[str]] = Query(
        None,
        description="Providers to fetch from (google, microsoft). If not specified, fetches from all available providers",
    ),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum number of events to return per provider"
    ),
    start_date: Optional[str] = Query(
        None, description="Start date for event range (ISO format: YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(
        None, description="End date for event range (ISO format: YYYY-MM-DD)"
    ),
    calendar_ids: Optional[List[str]] = Query(
        None, description="Specific calendar IDs to fetch from"
    ),
    q: Optional[str] = Query(None, description="Search query to filter events"),
    time_zone: Optional[str] = Query("UTC", description="Time zone for date filtering"),
):
    """
    Get unified calendar events from multiple providers.

    Fetches calendar events from Google Calendar and Microsoft Calendar APIs,
    normalizes them to a unified format, and returns aggregated results.
    Responses are cached for improved performance.

    Args:
        user_id: ID of the user to fetch events for
        providers: List of providers to query (defaults to all available)
        limit: Maximum events per provider
        start_date: Start date for filtering (defaults to today)
        end_date: End date for filtering (defaults to 30 days from start)
        calendar_ids: Specific calendars to query
        q: Search query string
        time_zone: Time zone for date operations

    Returns:
        ApiResponse with aggregated calendar events
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.utcnow()

    logger.info(
        f"[{request_id}] Calendar events request: user_id={user_id}, providers={providers}, limit={limit}"
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
            raise HTTPException(status_code=400, detail="No valid providers specified")

        # Parse and validate dates
        if not start_date:
            start_dt = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            try:
                start_dt = datetime.fromisoformat(start_date).replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD"
                )

        if not end_date:
            end_dt = start_dt + timedelta(days=30)
        else:
            try:
                end_dt = datetime.fromisoformat(end_date).replace(
                    tzinfo=timezone.utc, hour=23, minute=59, second=59
                )
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD"
                )

        # Build cache key
        cache_params = {
            "providers": valid_providers,
            "limit": limit,
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
            "calendar_ids": calendar_ids or [],
            "q": q or "",
            "time_zone": time_zone,
        }
        cache_key = generate_cache_key(user_id, "unified", "events", cache_params)

        # Check cache first
        cached_result = await cache_manager.get_from_cache(cache_key)
        if cached_result:
            logger.info(f"[{request_id}] Cache hit for calendar events")
            return ApiResponse(
                success=True, data=cached_result, cache_hit=True, request_id=request_id
            )

        # Fetch from providers in parallel
        tasks = []
        for provider in valid_providers:
            task = fetch_provider_events(
                request_id,
                user_id,
                provider,
                limit,
                start_dt,
                end_dt,
                calendar_ids,
                q,
                time_zone,
            )
            tasks.append(task)

        # Execute parallel requests
        provider_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        aggregated_events = []
        provider_errors = {}
        providers_used = []

        for i, result in enumerate(provider_results):
            provider = valid_providers[i]

            if isinstance(result, Exception):
                logger.error(f"[{request_id}] Provider {provider} failed: {result}")
                provider_errors[provider] = str(result)
            elif result:
                events, provider_name = result
                aggregated_events.extend(events)
                providers_used.append(provider_name)
                logger.info(
                    f"[{request_id}] Provider {provider} returned {len(events)} events"
                )

        # Sort events by start time
        aggregated_events.sort(key=lambda event: event.start_time)

        # Apply global limit if we have results from multiple providers
        if len(providers_used) > 1:
            aggregated_events = aggregated_events[: limit * 2]  # Allow some overlap

        # Build response
        response_data = {
            "events": [event.dict() for event in aggregated_events],
            "total_count": len(aggregated_events),
            "providers_used": providers_used,
            "provider_errors": provider_errors if provider_errors else None,
            "date_range": {
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat(),
                "time_zone": time_zone,
            },
            "request_metadata": {
                "user_id": user_id,
                "providers_requested": valid_providers,
                "limit": limit,
                "calendar_ids": calendar_ids,
            },
        }

        # Cache the result for 10 minutes (calendar data changes more frequently)
        await cache_manager.set_to_cache(cache_key, response_data, ttl_seconds=600)

        # Calculate response time
        end_time = datetime.utcnow()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"[{request_id}] Calendar events request completed in {response_time_ms}ms"
        )

        return ApiResponse(
            success=True,
            data=response_data,
            cache_hit=False,
            provider_used=providers_used[0] if len(providers_used) == 1 else None,
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Calendar events request failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch calendar events: {str(e)}"
        )


@router.get("/events/{event_id}", response_model=ApiResponse)
async def get_calendar_event(
    event_id: str = Path(..., description="Event ID (format: provider_originalId)"),
    user_id: str = Query(..., description="ID of the user who owns the event"),
):
    """
    Get a specific calendar event by ID.

    The event_id should be in the format "provider_originalId" (e.g., "google_abc123" or "microsoft_xyz789").
    This endpoint determines the correct provider from the event ID and fetches the full event details.

    Args:
        event_id: Event ID with provider prefix
        user_id: ID of the user who owns the event

    Returns:
        ApiResponse with the specific calendar event
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.utcnow()

    logger.info(
        f"[{request_id}] Calendar event detail request: event_id={event_id}, user_id={user_id}"
    )

    try:
        # Parse provider from event_id
        provider, original_event_id = parse_event_id(event_id)

        # Build cache key
        cache_params = {"event_id": event_id}
        cache_key = generate_cache_key(user_id, provider, "event_detail", cache_params)

        # Check cache first
        cached_result = await cache_manager.get_from_cache(cache_key)
        if cached_result:
            logger.info(f"[{request_id}] Cache hit for event detail")
            return ApiResponse(
                success=True, data=cached_result, cache_hit=True, request_id=request_id
            )

        # Fetch from the specific provider
        event = await fetch_single_event(
            request_id, user_id, provider, original_event_id
        )

        if not event:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

        # Build response
        response_data = {
            "event": event.dict(),
            "provider": provider,
            "request_metadata": {"user_id": user_id, "event_id": event_id},
        }

        # Cache the result for 30 minutes (events don't change very often)
        await cache_manager.set_to_cache(cache_key, response_data, ttl_seconds=1800)

        # Calculate response time
        end_time = datetime.utcnow()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"[{request_id}] Event detail request completed in {response_time_ms}ms"
        )

        return ApiResponse(
            success=True,
            data=response_data,
            cache_hit=False,
            provider_used=provider,
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Event detail request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch event: {str(e)}")


async def fetch_provider_events(
    request_id: str,
    user_id: str,
    provider: str,
    limit: int,
    start_dt: datetime,
    end_dt: datetime,
    calendar_ids: Optional[List[str]],
    q: Optional[str],
    time_zone: str,
) -> tuple[List[CalendarEvent], str]:
    """
    Fetch calendar events from a specific provider.

    Args:
        request_id: Request tracking ID
        user_id: User ID
        provider: Provider name (google, microsoft)
        limit: Maximum number of events
        start_dt: Start datetime for filtering
        end_dt: End datetime for filtering
        calendar_ids: Specific calendar IDs
        q: Search query
        time_zone: Time zone for operations

    Returns:
        Tuple of (events list, provider name)
    """
    try:
        # Get API client for provider
        client = await api_client_factory.create_client(user_id, provider)

        # Build provider-specific parameters
        if provider == "google":
            params = {
                "maxResults": limit,
                "timeMin": start_dt.isoformat(),
                "timeMax": end_dt.isoformat(),
                "singleEvents": True,
                "orderBy": "startTime",
            }
            if q:
                params["q"] = q
            if time_zone:
                params["timeZone"] = time_zone

            # Handle calendar IDs for Google
            calendars_to_query = calendar_ids or ["primary"]
            all_events = []

            for calendar_id in calendars_to_query:
                try:
                    # Fetch events from specific calendar
                    events_response = await client.get_calendar_events(
                        calendar_id, **params
                    )
                    events = events_response.get("items", [])

                    # Normalize events
                    for event_data in events:
                        # Get calendar info (simplified)
                        calendar_name = f"Calendar {calendar_id}"
                        account_email = f"{user_id}@gmail.com"  # Placeholder
                        account_name = f"Google Account ({user_id})"  # Placeholder

                        normalized_event = normalize_google_calendar_event(
                            event_data, account_email, account_name, calendar_name
                        )
                        all_events.append(normalized_event)

                except Exception as calendar_error:
                    logger.warning(
                        f"[{request_id}] Failed to fetch from Google calendar {calendar_id}: {calendar_error}"
                    )
                    continue

            normalized_events = all_events[:limit]  # Apply limit after aggregation

        elif provider == "microsoft":
            params = {
                "$top": limit,
                "$orderby": "start/dateTime asc",
                "$filter": f"start/dateTime ge '{start_dt.isoformat()}' and end/dateTime le '{end_dt.isoformat()}'",
            }
            if q:
                params["$search"] = f'"{q}"'

            # Fetch events from Outlook
            events_response = await client.get_calendar_events(**params)
            events = events_response.get("value", [])

            # Normalize events
            normalized_events = []
            for event_data in events:
                # Get user account info (simplified)
                account_email = f"{user_id}@outlook.com"  # Placeholder
                account_name = f"Microsoft Account ({user_id})"  # Placeholder
                calendar_name = "Default Calendar"  # Placeholder

                # Convert Microsoft event to Google format for normalization
                google_format_event = convert_microsoft_event_to_google_format(
                    event_data
                )

                normalized_event = normalize_google_calendar_event(
                    google_format_event, account_email, account_name, calendar_name
                )
                # Update provider to Microsoft
                normalized_event.provider = Provider.MICROSOFT
                normalized_event.id = f"microsoft_{event_data['id']}"
                normalized_event.provider_event_id = event_data["id"]

                normalized_events.append(normalized_event)

        else:
            raise ValueError(f"Unsupported provider: {provider}")

        logger.info(
            f"[{request_id}] Successfully fetched {len(normalized_events)} events from {provider}"
        )
        return normalized_events, provider

    except Exception as e:
        logger.error(f"[{request_id}] Failed to fetch events from {provider}: {e}")
        raise


async def fetch_single_event(
    request_id: str, user_id: str, provider: str, original_event_id: str
) -> Optional[CalendarEvent]:
    """
    Fetch a single calendar event from a specific provider.

    Args:
        request_id: Request tracking ID
        user_id: User ID
        provider: Provider name
        original_event_id: Original provider event ID

    Returns:
        CalendarEvent or None if not found
    """
    try:
        # Get API client for provider
        client = await api_client_factory.create_client(user_id, provider)

        if provider == "google":
            # Fetch event from Google Calendar
            event = await client.get_calendar_event("primary", original_event_id)

            # Get user account info (simplified)
            account_email = f"{user_id}@gmail.com"  # Placeholder
            account_name = f"Google Account ({user_id})"  # Placeholder
            calendar_name = "Primary Calendar"  # Placeholder

            return normalize_google_calendar_event(
                event, account_email, account_name, calendar_name
            )

        elif provider == "microsoft":
            # Fetch event from Microsoft Calendar
            event = await client.get_calendar_event(original_event_id)

            # Get user account info (simplified)
            account_email = f"{user_id}@outlook.com"  # Placeholder
            account_name = f"Microsoft Account ({user_id})"  # Placeholder
            calendar_name = "Default Calendar"  # Placeholder

            # Convert Microsoft event to Google format for normalization
            google_format_event = convert_microsoft_event_to_google_format(event)

            normalized_event = normalize_google_calendar_event(
                google_format_event, account_email, account_name, calendar_name
            )
            # Update provider to Microsoft
            normalized_event.provider = Provider.MICROSOFT
            normalized_event.id = f"microsoft_{event['id']}"
            normalized_event.provider_event_id = event["id"]

            return normalized_event

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    except Exception as e:
        logger.error(
            f"[{request_id}] Failed to fetch event {original_event_id} from {provider}: {e}"
        )
        return None


def convert_microsoft_event_to_google_format(
    ms_event: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convert Microsoft Calendar event format to Google Calendar format for normalization.

    Args:
        ms_event: Microsoft Calendar event data

    Returns:
        Event data in Google Calendar format
    """
    google_event = {
        "id": ms_event.get("id"),
        "summary": ms_event.get("subject"),
        "description": ms_event.get("body", {}).get("content"),
        "location": ms_event.get("location", {}).get("displayName"),
        "status": "confirmed" if not ms_event.get("isCancelled") else "cancelled",
        "visibility": (
            "private" if ms_event.get("sensitivity") == "private" else "default"
        ),
        "created": ms_event.get("createdDateTime"),
        "updated": ms_event.get("lastModifiedDateTime"),
    }

    # Convert start/end times
    start_time = ms_event.get("start", {})
    end_time = ms_event.get("end", {})

    if start_time.get("dateTime"):
        google_event["start"] = {"dateTime": start_time["dateTime"]}
        google_event["end"] = {"dateTime": end_time["dateTime"]}
    else:
        # All-day event
        google_event["start"] = {"date": start_time.get("date")}
        google_event["end"] = {"date": end_time.get("date")}

    # Convert attendees
    attendees = []
    for attendee in ms_event.get("attendees", []):
        email_addr = attendee.get("emailAddress", {})
        attendees.append(
            {
                "email": email_addr.get("address"),
                "displayName": email_addr.get("name"),
                "responseStatus": attendee.get("status", {}).get(
                    "response", "needsAction"
                ),
            }
        )
    google_event["attendees"] = attendees

    # Convert organizer
    organizer = ms_event.get("organizer", {})
    if organizer:
        email_addr = organizer.get("emailAddress", {})
        google_event["organizer"] = {
            "email": email_addr.get("address"),
            "displayName": email_addr.get("name"),
        }

    return google_event


def parse_event_id(event_id: str) -> tuple[str, str]:
    """
    Parse a unified event ID to extract provider and original ID.

    Args:
        event_id: Unified event ID (format: "provider_originalId")

    Returns:
        Tuple of (provider, original_event_id)

    Raises:
        HTTPException: If event ID format is invalid
    """
    try:
        if "_" not in event_id:
            raise ValueError("Invalid event ID format")

        parts = event_id.split("_", 1)
        provider_prefix = parts[0].lower()
        original_id = parts[1]

        # Map provider prefixes to standard names
        provider_map = {"google": "google", "microsoft": "microsoft"}

        provider = provider_map.get(provider_prefix)
        if not provider:
            raise ValueError(f"Unknown provider prefix: {provider_prefix}")

        return provider, original_id

    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event ID format: {event_id}. Expected format: 'provider_originalId'",
        )
