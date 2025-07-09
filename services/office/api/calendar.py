"""
Unified calendar endpoints for the Office Service.

Provides endpoints for reading calendar events across Google and Microsoft providers,
with unified data models, caching, and parallel API calls for optimal performance.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from services.office.core.api_client_factory import APIClientFactory
from services.office.core.auth import ServicePermissionRequired
from services.office.core.cache_manager import cache_manager, generate_cache_key
from services.office.core.clients.google import GoogleAPIClient
from services.office.core.clients.microsoft import MicrosoftAPIClient
from services.office.core.normalizer import normalize_google_calendar_event
from services.office.models import Provider
from services.office.schemas import (
    ApiResponse,
    CalendarEvent,
    CreateCalendarEventRequest,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/calendar", tags=["calendar"])

# Initialize dependencies
api_client_factory = APIClientFactory()


def _get_calendar_scopes(provider: str) -> List[str]:
    """Get calendar-specific scopes for a provider."""
    if provider == "google":
        return ["https://www.googleapis.com/auth/calendar"]
    elif provider == "microsoft":
        return ["https://graph.microsoft.com/Calendars.ReadWrite"]
    else:
        return []


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
    service_name: str = Depends(ServicePermissionRequired(["read_calendar"])),
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
    start_time = datetime.now(timezone.utc)

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
                time_zone or "UTC",  # Ensure time_zone is never None
            )
            tasks.append(task)

        # Execute parallel requests
        provider_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        aggregated_events: List[CalendarEvent] = []
        provider_errors = {}
        providers_used = []

        for i, result in enumerate(provider_results):
            provider = valid_providers[i]

            if isinstance(result, Exception):
                logger.error(f"[{request_id}] Provider {provider} failed: {result}")
                provider_errors[provider] = str(result)
            elif result is not None and not isinstance(result, BaseException):
                try:
                    # Type narrowing: result should be tuple[List[CalendarEvent], str]
                    events, provider_name = result
                    aggregated_events.extend(events)
                    providers_used.append(provider_name)
                    logger.info(
                        f"[{request_id}] Provider {provider} returned {len(events)} events"
                    )
                except (TypeError, ValueError) as e:
                    logger.error(
                        f"[{request_id}] Invalid result format from {provider}: {e}"
                    )
                    provider_errors[provider] = f"Invalid result format: {e}"

        # Sort events by start time
        aggregated_events.sort(key=lambda event: event.start_time)

        # Apply global limit if we have results from multiple providers
        if len(providers_used) > 1:
            aggregated_events = aggregated_events[: limit * 2]  # Allow some overlap

        # Build response
        response_data = {
            "events": [event.model_dump() for event in aggregated_events],
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

        # Only cache if we have successful results from at least one provider
        if providers_used:  # Only cache if at least one provider succeeded
            # Cache the result for 10 minutes (calendar data changes more frequently)
            await cache_manager.set_to_cache(cache_key, response_data, ttl_seconds=600)
        else:
            logger.info(
                f"[{request_id}] Not caching response due to no successful providers"
            )

        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"[{request_id}] Calendar events request completed in {response_time_ms}ms"
        )

        return ApiResponse(
            success=True,
            data=response_data,
            cache_hit=False,
            provider_used=(
                Provider(providers_used[0]) if len(providers_used) == 1 else None
            ),
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
    service_name: str = Depends(ServicePermissionRequired(["read_calendar"])),
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
    start_time = datetime.now(timezone.utc)

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
            "event": event.model_dump(),
            "provider": provider,
            "request_metadata": {"user_id": user_id, "event_id": event_id},
        }

        # Cache the result for 30 minutes (events don't change very often)
        await cache_manager.set_to_cache(cache_key, response_data, ttl_seconds=1800)

        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"[{request_id}] Event detail request completed in {response_time_ms}ms"
        )

        return ApiResponse(
            success=True,
            data=response_data,
            cache_hit=False,
            provider_used=Provider(provider),
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Event detail request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch event: {str(e)}")


@router.post("/events", response_model=ApiResponse)
async def create_calendar_event(
    event_data: CreateCalendarEventRequest,
    user_id: str = Query(..., description="ID of the user creating the event"),
    service_name: str = Depends(ServicePermissionRequired(["write_calendar"])),
):
    """
    Create a calendar event in a specific provider.

    This endpoint takes unified CalendarEvent data, "de-normalizes" it into the
    provider-specific format, and uses the correct API client to create the event.

    Args:
        event_data: Event content and configuration
        user_id: ID of the user creating the event

    Returns:
        ApiResponse with created event details
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"[{request_id}] Create calendar event request: user_id={user_id}, "
        f"title='{event_data.title}', provider={event_data.provider}"
    )

    try:
        # Determine provider (default to google if not specified)
        provider = event_data.provider or "google"

        # Validate provider
        if provider.lower() not in ["google", "microsoft"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider: {provider}. Must be 'google' or 'microsoft'",
            )

        provider = provider.lower()

        # Get API client for provider
        client = await api_client_factory.create_client(user_id, provider)
        if client is None:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to create API client for provider {provider}. "
                "User may not have connected this provider.",
            )

        # Create event based on provider
        created_event_data = None

        async with client:
            if provider == "google":
                google_client = cast(GoogleAPIClient, client)
                created_event_data = await create_google_event(
                    request_id, google_client, event_data
                )
            elif provider == "microsoft":
                microsoft_client = cast(MicrosoftAPIClient, client)
                created_event_data = await create_microsoft_event(
                    request_id, microsoft_client, event_data
                )

        # Build response
        response_data = {
            "event_id": created_event_data.get("id") if created_event_data else None,
            "provider": provider,
            "status": "created",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "request_metadata": {
                "user_id": user_id,
                "title": event_data.title,
                "start_time": event_data.start_time.isoformat(),
                "end_time": event_data.end_time.isoformat(),
                "provider": provider,
            },
        }

        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"[{request_id}] Calendar event created successfully in {response_time_ms}ms via {provider}"
        )

        return ApiResponse(
            success=True,
            data=response_data,
            cache_hit=False,
            provider_used=(
                Provider.GOOGLE if provider == "google" else Provider.MICROSOFT
            ),
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Create calendar event request failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create calendar event: {str(e)}"
        )


@router.put("/events/{event_id}", response_model=ApiResponse)
async def update_calendar_event(
    event_data: CreateCalendarEventRequest,
    event_id: str = Path(..., description="Event ID (format: provider_originalId)"),
    user_id: str = Query(..., description="ID of the user updating the event"),
    service_name: str = Depends(ServicePermissionRequired(["write_calendar"])),
):
    """
    Update a calendar event by ID.

    This endpoint takes unified CalendarEvent data, "de-normalizes" it into the
    provider-specific format, and uses the correct API client to update the event.

    Args:
        event_id: Event ID with provider prefix (e.g., "google_abc123")
        event_data: Updated event content and configuration
        user_id: ID of the user updating the event

    Returns:
        ApiResponse with updated event details
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"[{request_id}] Update calendar event request: event_id={event_id}, user_id={user_id}, "
        f"title='{event_data.title}'"
    )

    try:
        # Parse provider from event_id
        provider, original_event_id = parse_event_id(event_id)

        # Get API client for provider
        client = await api_client_factory.create_client(user_id, provider)
        if client is None:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to create API client for provider {provider}. "
                "User may not have connected this provider.",
            )

        # Update event based on provider and capture the updated data
        updated_event_data = None

        async with client:
            if provider == "google":
                google_client = cast(GoogleAPIClient, client)
                updated_event_data = await update_google_event(
                    request_id, google_client, original_event_id, event_data
                )
            elif provider == "microsoft":
                microsoft_client = cast(MicrosoftAPIClient, client)
                ms_updated_data = await update_microsoft_event(
                    request_id, microsoft_client, original_event_id, event_data
                )
                # Convert Microsoft format to Google format for consistency
                updated_event_data = convert_microsoft_event_to_google_format(
                    ms_updated_data
                )

        # Extract actual updated values from the provider response
        actual_title = (
            updated_event_data.get("summary", event_data.title)
            if updated_event_data
            else event_data.title
        )
        actual_location = (
            updated_event_data.get("location", event_data.location)
            if updated_event_data
            else event_data.location
        )
        actual_description = (
            updated_event_data.get("description", event_data.description)
            if updated_event_data
            else event_data.description
        )

        # Extract datetime values, handling different formats
        actual_start_time = event_data.start_time.isoformat()
        actual_end_time = event_data.end_time.isoformat()

        if updated_event_data:
            start_data = updated_event_data.get("start", {})
            end_data = updated_event_data.get("end", {})

            if isinstance(start_data, dict) and "dateTime" in start_data:
                actual_start_time = start_data["dateTime"]
            if isinstance(end_data, dict) and "dateTime" in end_data:
                actual_end_time = end_data["dateTime"]

        # Build response with actual updated data
        response_data = {
            "event_id": event_id,
            "provider": provider,
            "status": "updated",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "event_data": {
                "title": actual_title,
                "start_time": actual_start_time,
                "end_time": actual_end_time,
                "location": actual_location,
                "description": actual_description,
            },
            "request_metadata": {
                "user_id": user_id,
                "event_id": event_id,
                "title": event_data.title,
                "start_time": event_data.start_time.isoformat(),
                "end_time": event_data.end_time.isoformat(),
                "provider": provider,
            },
        }

        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"[{request_id}] Calendar event updated successfully in {response_time_ms}ms via {provider}"
        )

        return ApiResponse(
            success=True,
            data=response_data,
            cache_hit=False,
            provider_used=(
                Provider.GOOGLE if provider == "google" else Provider.MICROSOFT
            ),
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Update calendar event request failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update calendar event: {str(e)}"
        )


async def create_google_event(
    request_id: str, client: GoogleAPIClient, event_data: CreateCalendarEventRequest
) -> Dict[str, Any]:
    """
    Create a calendar event via Google Calendar API.

    Args:
        request_id: Request tracking ID
        client: Google API client
        event_data: Event content and configuration

    Returns:
        Dictionary containing created event details
    """
    try:
        # Build Google Calendar event data
        calendar_id = event_data.calendar_id or "primary"

        # Convert attendees to Google format
        attendees = []
        if event_data.attendees:
            attendees = [
                {
                    "email": attendee.email,
                    "displayName": attendee.name or attendee.email,
                }
                for attendee in event_data.attendees
            ]

        # Build event data in Google Calendar format
        google_event_data = {
            "summary": event_data.title,
            "description": event_data.description or "",
            "location": event_data.location or "",
            "start": {
                "dateTime": event_data.start_time.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": event_data.end_time.isoformat(),
                "timeZone": "UTC",
            },
            "attendees": attendees,
            "visibility": event_data.visibility or "default",
            "status": event_data.status or "confirmed",
        }

        # Handle all-day events
        if event_data.all_day:
            start_date = event_data.start_time.date().isoformat()
            end_date = event_data.end_time.date().isoformat()
            google_event_data["start"] = {"date": start_date}
            google_event_data["end"] = {"date": end_date}

        # Create the event
        result = await client.create_event(calendar_id, google_event_data)

        logger.info(
            f"[{request_id}] Google Calendar event created successfully: {result.get('id')}"
        )
        return result

    except Exception as e:
        logger.error(f"[{request_id}] Failed to create Google Calendar event: {e}")
        raise


async def create_microsoft_event(
    request_id: str, client: MicrosoftAPIClient, event_data: CreateCalendarEventRequest
) -> Dict[str, Any]:
    """
    Create a calendar event via Microsoft Graph API.

    Args:
        request_id: Request tracking ID
        client: Microsoft API client
        event_data: Event content and configuration

    Returns:
        Dictionary containing created event details
    """
    try:
        # Convert attendees to Microsoft format
        attendees: List[Dict[str, Any]] = []
        if event_data.attendees:
            attendees = [
                {
                    "emailAddress": {
                        "address": attendee.email,
                        "name": attendee.name or attendee.email,
                    },
                    "type": "required",
                }
                for attendee in event_data.attendees
            ]

        # Build event data in Microsoft Graph format
        microsoft_event_data: Dict[str, Any] = {
            "subject": event_data.title,
            "body": {
                "contentType": "Text",
                "content": event_data.description or "",
            },
            "start": {
                "dateTime": event_data.start_time.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": event_data.end_time.isoformat(),
                "timeZone": "UTC",
            },
            "location": {
                "displayName": event_data.location or "",
            },
            "attendees": attendees,
            "showAs": "busy",  # Default availability
            "sensitivity": "normal",  # Default sensitivity
        }

        # Handle all-day events
        if event_data.all_day:
            microsoft_event_data["isAllDay"] = True

        # Map visibility to Microsoft sensitivity
        if event_data.visibility == "private":
            microsoft_event_data["sensitivity"] = "private"
        elif event_data.visibility == "public":
            microsoft_event_data["sensitivity"] = "normal"

        # Create the event
        result = await client.create_event(microsoft_event_data, event_data.calendar_id)

        logger.info(
            f"[{request_id}] Microsoft Calendar event created successfully: {result.get('id')}"
        )
        return result

    except Exception as e:
        logger.error(f"[{request_id}] Failed to create Microsoft Calendar event: {e}")
        raise


async def update_google_event(
    request_id: str,
    client: GoogleAPIClient,
    event_id: str,
    event_data: CreateCalendarEventRequest,
    calendar_id: str = "primary",
) -> Dict[str, Any]:
    """
    Update a calendar event via Google Calendar API.

    Args:
        request_id: Request tracking ID
        client: Google API client
        event_id: Google Calendar event ID
        event_data: Updated event content and configuration
        calendar_id: Calendar ID (defaults to primary)

    Returns:
        Dictionary containing updated event details
    """
    try:
        # Convert attendees to Google format
        attendees = []
        if event_data.attendees:
            attendees = [
                {
                    "email": attendee.email,
                    "displayName": attendee.name or attendee.email,
                }
                for attendee in event_data.attendees
            ]

        # Build event data in Google Calendar format
        google_event_data = {
            "summary": event_data.title,
            "description": event_data.description or "",
            "location": event_data.location or "",
            "start": {
                "dateTime": event_data.start_time.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": event_data.end_time.isoformat(),
                "timeZone": "UTC",
            },
            "attendees": attendees,
            "visibility": event_data.visibility or "default",
            "status": event_data.status or "confirmed",
        }

        # Handle all-day events
        if event_data.all_day:
            start_date = event_data.start_time.date().isoformat()
            end_date = event_data.end_time.date().isoformat()
            google_event_data["start"] = {"date": start_date}
            google_event_data["end"] = {"date": end_date}

        # Update the event
        result = await client.update_event(calendar_id, event_id, google_event_data)

        logger.info(
            f"[{request_id}] Google Calendar event updated successfully: {event_id}"
        )
        return result

    except Exception as e:
        logger.error(f"[{request_id}] Failed to update Google Calendar event: {e}")
        raise


async def update_microsoft_event(
    request_id: str,
    client: MicrosoftAPIClient,
    event_id: str,
    event_data: CreateCalendarEventRequest,
    calendar_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update a calendar event via Microsoft Graph API.

    Args:
        request_id: Request tracking ID
        client: Microsoft API client
        event_id: Microsoft Graph event ID
        event_data: Updated event content and configuration
        calendar_id: Calendar ID (optional, uses primary if not specified)

    Returns:
        Dictionary containing updated event details
    """
    try:
        # Convert attendees to Microsoft format
        attendees: List[Dict[str, Any]] = []
        if event_data.attendees:
            attendees = [
                {
                    "emailAddress": {
                        "address": attendee.email,
                        "name": attendee.name or attendee.email,
                    },
                    "type": "required",
                }
                for attendee in event_data.attendees
            ]

        # Build event data in Microsoft Graph format
        microsoft_event_data: Dict[str, Any] = {
            "subject": event_data.title,
            "body": {
                "contentType": "Text",
                "content": event_data.description or "",
            },
            "start": {
                "dateTime": event_data.start_time.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": event_data.end_time.isoformat(),
                "timeZone": "UTC",
            },
            "location": {
                "displayName": event_data.location or "",
            },
            "attendees": attendees,
            "showAs": "busy",  # Default availability
            "sensitivity": "normal",  # Default sensitivity
        }

        # Handle all-day events
        if event_data.all_day:
            microsoft_event_data["isAllDay"] = True

        # Map visibility to Microsoft sensitivity
        if event_data.visibility == "private":
            microsoft_event_data["sensitivity"] = "private"
        elif event_data.visibility == "public":
            microsoft_event_data["sensitivity"] = "normal"

        # Update the event
        result = await client.update_event(event_id, microsoft_event_data, calendar_id)

        logger.info(
            f"[{request_id}] Microsoft Calendar event updated successfully: {event_id}"
        )
        return result

    except Exception as e:
        logger.error(f"[{request_id}] Failed to update Microsoft Calendar event: {e}")
        raise


@router.delete("/events/{event_id}", response_model=ApiResponse)
async def delete_calendar_event(
    event_id: str = Path(..., description="Event ID (format: provider_originalId)"),
    user_id: str = Query(..., description="ID of the user who owns the event"),
    service_name: str = Depends(ServicePermissionRequired(["write_calendar"])),
):
    """
    Delete a calendar event by ID.

    This endpoint requires logic to find the original provider from the event ID
    and use its API to delete the event.

    Args:
        event_id: Event ID with provider prefix (e.g., "google_abc123")
        user_id: ID of the user who owns the event

    Returns:
        ApiResponse confirming deletion
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"[{request_id}] Delete calendar event request: event_id={event_id}, user_id={user_id}"
    )

    try:
        # Parse provider from event_id
        provider, original_event_id = parse_event_id(event_id)

        # Get API client for provider
        client = await api_client_factory.create_client(user_id, provider)
        if client is None:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to create API client for provider {provider}. "
                "User may not have connected this provider.",
            )

        # Delete event based on provider
        async with client:
            if provider == "google":
                google_client = cast(GoogleAPIClient, client)
                await delete_google_event(request_id, google_client, original_event_id)
            elif provider == "microsoft":
                microsoft_client = cast(MicrosoftAPIClient, client)
                await delete_microsoft_event(
                    request_id, microsoft_client, original_event_id
                )

        # Build response
        response_data = {
            "event_id": event_id,
            "provider": provider,
            "status": "deleted",
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "request_metadata": {
                "user_id": user_id,
                "event_id": event_id,
                "provider": provider,
            },
        }

        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"[{request_id}] Calendar event deleted successfully in {response_time_ms}ms via {provider}"
        )

        return ApiResponse(
            success=True,
            data=response_data,
            cache_hit=False,
            provider_used=(
                Provider.GOOGLE if provider == "google" else Provider.MICROSOFT
            ),
            request_id=request_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Delete calendar event request failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete calendar event: {str(e)}"
        )


async def delete_google_event(
    request_id: str,
    client: GoogleAPIClient,
    event_id: str,
    calendar_id: str = "primary",
) -> None:
    """
    Delete a calendar event via Google Calendar API.

    Args:
        request_id: Request tracking ID
        client: Google API client
        event_id: Google Calendar event ID
        calendar_id: Calendar ID (defaults to primary)
    """
    try:
        # Delete the event
        await client.delete_event(calendar_id, event_id)

        logger.info(
            f"[{request_id}] Google Calendar event deleted successfully: {event_id}"
        )

    except Exception as e:
        logger.error(f"[{request_id}] Failed to delete Google Calendar event: {e}")
        raise


async def delete_microsoft_event(
    request_id: str,
    client: MicrosoftAPIClient,
    event_id: str,
    calendar_id: Optional[str] = None,
) -> None:
    """
    Delete a calendar event via Microsoft Graph API.

    Args:
        request_id: Request tracking ID
        client: Microsoft API client
        event_id: Microsoft Graph event ID
        calendar_id: Calendar ID (optional, uses primary if not specified)
    """
    try:
        # Delete the event
        await client.delete_event(event_id, calendar_id)

        logger.info(
            f"[{request_id}] Microsoft Calendar event deleted successfully: {event_id}"
        )

    except Exception as e:
        logger.error(f"[{request_id}] Failed to delete Microsoft Calendar event: {e}")
        raise


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
        # Get API client for provider with calendar-specific scopes
        calendar_scopes = _get_calendar_scopes(provider)
        client = await api_client_factory.create_client(
            user_id, provider, calendar_scopes
        )
        if client is None:
            raise ValueError(f"Failed to create API client for provider {provider}")

        # Use client as async context manager
        async with client:
            # Build provider-specific parameters
            if provider == "google":
                google_client = cast(GoogleAPIClient, client)

                # Handle calendar IDs for Google
                calendars_to_query = calendar_ids or ["primary"]
                all_events = []

                for calendar_id in calendars_to_query:
                    try:
                        # Fetch events from specific calendar
                        events_response = await google_client.get_events(
                            calendar_id=calendar_id,
                            time_min=start_dt.isoformat(),
                            time_max=end_dt.isoformat(),
                            max_results=limit,
                            page_token=None,
                        )
                        events = events_response.get("items", [])

                        # Normalize events
                        for event_data in events:
                            # Get calendar info (simplified)
                            calendar_name = f"Calendar {calendar_id}"
                            # Handle case where user_id is already an email address
                            if "@" in user_id:
                                account_email = user_id
                                account_name = (
                                    f"Google Account ({user_id.split('@')[0]})"
                                )
                            else:
                                account_email = f"{user_id}@gmail.com"  # Placeholder
                                account_name = (
                                    f"Google Account ({user_id})"  # Placeholder
                                )

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
                microsoft_client = cast(MicrosoftAPIClient, client)

                # Fetch events from Outlook
                events_response = await microsoft_client.get_events(
                    calendar_id=None,  # Use primary calendar
                    start_time=start_dt.isoformat(),
                    end_time=end_dt.isoformat(),
                    top=limit,
                    skip=0,
                    order_by="start/dateTime asc",
                )
                events = events_response.get("value", [])

                # Normalize events
                normalized_events = []
                for event_data in events:
                    # Get user account info (simplified)
                    # Handle case where user_id is already an email address
                    if "@" in user_id:
                        account_email = user_id
                        account_name = f"Microsoft Account ({user_id.split('@')[0]})"
                    else:
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
        # Get API client for provider with calendar-specific scopes
        calendar_scopes = _get_calendar_scopes(provider)
        client = await api_client_factory.create_client(
            user_id, provider, calendar_scopes
        )
        if client is None:
            raise ValueError(f"Failed to create API client for provider {provider}")

        # Use client as async context manager
        async with client:
            if provider == "google":
                google_client = cast(GoogleAPIClient, client)
                # For now, we'll need to implement get_event method or use a workaround
                # Fetch event from Google Calendar by making a direct API call
                response = await google_client.get(
                    f"/calendar/v3/calendars/primary/events/{original_event_id}"
                )
                event = response.json()

                # Get user account info (simplified)
                # Handle case where user_id is already an email address
                if "@" in user_id:
                    account_email = user_id
                    account_name = f"Google Account ({user_id.split('@')[0]})"
                else:
                    account_email = f"{user_id}@gmail.com"  # Placeholder
                    account_name = f"Google Account ({user_id})"  # Placeholder
                calendar_name = "Primary Calendar"  # Placeholder

                return normalize_google_calendar_event(
                    event, account_email, account_name, calendar_name
                )

            elif provider == "microsoft":
                microsoft_client = cast(MicrosoftAPIClient, client)
                # Fetch event from Microsoft Calendar by making a direct API call
                response = await microsoft_client.get(f"/me/events/{original_event_id}")
                event = response.json()

                # Get user account info (simplified)
                # Handle case where user_id is already an email address
                if "@" in user_id:
                    account_email = user_id
                    account_name = f"Microsoft Account ({user_id.split('@')[0]})"
                else:
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
