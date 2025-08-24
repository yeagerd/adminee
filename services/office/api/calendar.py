"""
Unified calendar endpoints for the Office Service.

All user-facing endpoints extract user from the X-User-Id header (set by the gateway).
No user_id is accepted in the path or query for user-facing endpoints.
Internal/service endpoints, if any, should be under /internal and require API key auth.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, Depends, Path, Query, Request

from services.common.http_errors import (
    AuthError,
    NotFoundError,
    ServiceError,
    ValidationError,
)
from services.common.logging_config import get_logger, request_id_var
from services.office.core.api_client_factory import APIClientFactory
from services.office.core.auth import service_permission_required
from services.office.core.cache_manager import cache_manager, generate_cache_key
from services.office.core.clients.google import GoogleAPIClient
from services.office.core.clients.microsoft import MicrosoftAPIClient
from services.office.core.normalizer import normalize_google_calendar_event
from services.api.v1.office.models import Provider
from services.api.v1.office.calendar import (
    ApiResponse,
    AvailabilityApiResponse,
    AvailabilityResponse,
    AvailableSlot,
    CalendarEvent,
    CalendarEventApiResponse,
    CalendarEventDetailResponse,
    CalendarEventListApiResponse,
    CalendarEventResponse,
    CreateCalendarEventRequest,
    TimeRange,
)

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/calendar", tags=["calendar"])

# Lazy-initialized API client factory instance
_api_client_factory = None
_api_client_factory_lock = asyncio.Lock()


async def get_api_client_factory() -> APIClientFactory:
    """Get or create the shared API client factory instance."""
    global _api_client_factory

    if _api_client_factory is None:
        async with _api_client_factory_lock:
            if _api_client_factory is None:
                _api_client_factory = APIClientFactory()
                logger.info(
                    "Created lazy-initialized APIClientFactory instance with shared TokenManager"
                )

    return _api_client_factory


async def get_user_id_from_gateway(request: Request) -> str:
    """
    Extract user ID from gateway headers.

    The office service only supports requests through the gateway,
    which forwards user identity via X-User-Id header.
    """
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise ValidationError(message="X-User-Id header is required", field="X-User-Id")
    return user_id


def get_request_id() -> str:
    """
    Get the current request ID from context or generate a fallback.
    """
    request_id = request_id_var.get()
    if not request_id or request_id == "uninitialized":
        # Fallback for cases where middleware hasn't set the context
        return "no-request-id"
    return request_id


def _get_calendar_scopes(provider: str) -> List[str]:
    """Get calendar-specific scopes for a provider."""
    if provider == "google":
        return ["https://www.googleapis.com/auth/calendar"]
    elif provider == "microsoft":
        return ["https://graph.microsoft.com/Calendars.ReadWrite"]
    else:
        return []


@router.get("/availability", response_model=AvailabilityApiResponse)
async def get_user_availability(
    request: Request,
    start: str = Query(
        ..., description="Start time for availability check (ISO format)"
    ),
    end: str = Query(..., description="End time for availability check (ISO format)"),
    duration: int = Query(..., description="Duration in minutes for the meeting"),
    providers: Optional[List[str]] = Query(
        None,
        description="Providers to check (google, microsoft). If not specified, checks all available providers",
    ),
    service_name: str = Depends(service_permission_required(["read_calendar"])),
) -> AvailabilityApiResponse:
    """
    Get user availability for a given time range.

    Checks the user's calendar across multiple providers to find available time slots
    for a meeting of the specified duration.

    Args:
        start: Start time for availability check
        end: End time for availability check
        duration: Duration in minutes for the meeting
        providers: List of providers to check (defaults to all available)

    Returns:
        ApiResponse with available time slots
    """
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"Availability request: user_id={user_id}, start={start}, end={end}, duration={duration}"
    )

    try:
        # Parse datetime strings
        try:
            start_dt = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
            end_dt = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
        except ValueError:
            raise ValidationError(
                message="Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS)",
                field="start/end",
            )

        # If no providers specified, get user's preferred provider
        if not providers:
            factory = await get_api_client_factory()
            preferred_provider = await factory.get_user_preferred_provider(user_id)
            if preferred_provider:
                providers = [preferred_provider.value]
            else:
                # Fallback to all providers if no preferred provider is set
                providers = ["google", "microsoft"]

        # Validate providers
        valid_providers = []
        for provider in providers:
            if provider.lower() in ["google", "microsoft"]:
                valid_providers.append(provider.lower())
            else:
                logger.warning(
                    "Invalid provider specified",
                    request_id=request_id,
                    provider=provider,
                )

        if not valid_providers:
            raise ValidationError(
                message="No valid providers specified", field="providers"
            )

        # Build cache key
        cache_params = {
            "providers": valid_providers,
            "start": start,
            "end": end,
            "duration": duration,
        }
        cache_key = generate_cache_key(user_id, "unified", "availability", cache_params)

        # Check cache first
        cached_result = await cache_manager.get_from_cache(cache_key)
        if cached_result:
            logger.info("Cache hit for availability", request_id=request_id)
            return AvailabilityApiResponse(
                success=True, data=cached_result, cache_hit=True, request_id=request_id
            )

        # Fetch events from providers in parallel
        tasks = []
        for provider in valid_providers:
            task = fetch_provider_events(
                request_id,
                user_id,
                provider,
                1000,  # High limit to get all events in range
                start_dt,
                end_dt,
                None,  # No specific calendar IDs
                None,  # No search query
                "UTC",
            )
            tasks.append(task)

        # Execute parallel requests
        provider_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and find available slots
        all_events: List[CalendarEvent] = []
        provider_errors = {}
        providers_used = []

        for i, result in enumerate(provider_results):
            provider = valid_providers[i]

            if isinstance(result, Exception):
                logger.error(
                    "Provider failed",
                    request_id=request_id,
                    provider=provider,
                    error=str(result),
                )
                provider_errors[provider] = str(result)
            elif result is not None and not isinstance(result, BaseException):
                try:
                    # Type narrowing: result should be tuple[List[CalendarEvent], str]
                    events, provider_name = result
                    all_events.extend(events)
                    providers_used.append(provider_name)
                    logger.info(f"Provider {provider} returned {len(events)} events")
                except (TypeError, ValueError) as e:
                    logger.error(f"Invalid result format from {provider}: {e}")
                    provider_errors[provider] = f"Invalid result format: {e}"

        # Find available time slots
        available_slots = find_available_slots(start_dt, end_dt, duration, all_events)

        # Build response using Pydantic models
        available_slot_models = [
            AvailableSlot(
                start=slot["start"],
                end=slot["end"],
                duration_minutes=duration,
            )
            for slot in available_slots
        ]

        response_data = AvailabilityResponse(
            available_slots=available_slot_models,
            total_slots=len(available_slots),
            time_range=TimeRange(start=start_dt.isoformat(), end=end_dt.isoformat()),
            providers_used=providers_used,
            provider_errors=provider_errors if provider_errors else None,
            request_metadata={
                "user_id": user_id,
                "providers_requested": valid_providers,
                "duration_minutes": duration,
            },
        )

        # Cache the result for 5 minutes (availability changes frequently)
        if providers_used:  # Only cache if at least one provider succeeded
            await cache_manager.set_to_cache(cache_key, response_data, ttl_seconds=300)
        else:
            logger.info(
                "Not caching response due to no successful providers",
                request_id=request_id,
                providers_used=providers_used,
            )

        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            "Availability request completed",
            request_id=request_id,
            response_time_ms=response_time_ms,
            providers_used=providers_used,
            available_slots=len(available_slots),
        )

        return AvailabilityApiResponse(
            success=True,
            data=response_data,
            cache_hit=False,
            provider_used=(
                Provider(providers_used[0]) if len(providers_used) == 1 else None
            ),
            request_id=request_id,
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error("Availability request failed", request_id=request_id, error=str(e))
        raise ServiceError(message=f"Failed to check availability: {str(e)}")


@router.get("/events", response_model=CalendarEventListApiResponse)
async def get_calendar_events(
    request: Request,
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
    no_cache: bool = Query(
        False, description="Bypass cache and fetch fresh data from providers"
    ),
    service_name: str = Depends(service_permission_required(["read_calendar"])),
) -> CalendarEventListApiResponse:
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
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"Calendar events request: user_id={user_id}, providers={providers}, limit={limit}"
    )

    try:
        # If no providers specified, get user's preferred provider
        if not providers:
            factory = await get_api_client_factory()
            preferred_provider = await factory.get_user_preferred_provider(user_id)
            if preferred_provider:
                providers = [preferred_provider.value]
            else:
                # Fallback to all providers if no preferred provider is set
                providers = ["google", "microsoft"]

        # Validate providers
        valid_providers = []
        for provider in providers:
            if provider.lower() in ["google", "microsoft"]:
                valid_providers.append(provider.lower())
            else:
                logger.warning(
                    "Invalid provider specified",
                    request_id=request_id,
                    provider=provider,
                )

        if not valid_providers:
            raise ValidationError(
                message="No valid providers specified", field="providers"
            )

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
                raise ValidationError(
                    message="Invalid start_date format. Use YYYY-MM-DD",
                    field="start_date",
                )

        if not end_date:
            end_dt = start_dt + timedelta(days=30)
        else:
            try:
                end_dt = datetime.fromisoformat(end_date).replace(
                    tzinfo=timezone.utc, hour=23, minute=59, second=59
                )
            except ValueError:
                raise ValidationError(
                    message="Invalid end_date format. Use YYYY-MM-DD", field="end_date"
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
            "no_cache": no_cache,
        }
        cache_key = generate_cache_key(user_id, "unified", "events", cache_params)
        logger.debug(f"Generated cache key: {cache_key}")

        # Check cache first
        cached_result = await cache_manager.get_from_cache(cache_key)
        if cached_result and not no_cache:
            logger.info("Cache hit for calendar events", request_id=request_id)
            # Extract events from cached result
            if isinstance(cached_result, dict) and "events" in cached_result:
                events = cached_result["events"]
                logger.debug(
                    f"Retrieved {len(events)} events from cache (dict format)",
                    request_id=request_id,
                )
            else:
                # Fallback for old cache format
                events = cached_result if isinstance(cached_result, list) else []
                logger.debug(
                    f"Retrieved {len(events)} events from cache (list format)",
                    request_id=request_id,
                )

            # If we have an empty cache entry, clear it and proceed with fresh fetch
            if len(events) == 0:
                logger.warning(
                    "Found empty cache entry, clearing and fetching fresh data",
                    request_id=request_id,
                )
                await cache_manager.delete_from_cache(cache_key)
            else:
                return CalendarEventListApiResponse(
                    success=True, data=events, cache_hit=True, request_id=request_id
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
                logger.error(
                    "Provider failed",
                    request_id=request_id,
                    provider=provider,
                    error=str(result),
                )
                provider_errors[provider] = str(result)
            elif result is not None and not isinstance(result, BaseException):
                try:
                    # Type narrowing: result should be tuple[List[CalendarEvent], str]
                    events, provider_name = result
                    aggregated_events.extend(events)
                    providers_used.append(provider_name)
                    logger.info(f"Provider {provider} returned {len(events)} events")
                except (TypeError, ValueError) as e:
                    logger.error(f"Invalid result format from {provider}: {e}")
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
        if (
            providers_used and len(aggregated_events) > 0
        ):  # Only cache if at least one provider succeeded and we have events
            # Cache the result for 10 minutes (calendar data changes more frequently)
            await cache_manager.set_to_cache(cache_key, response_data, ttl_seconds=600)
            logger.debug(
                f"Cached {len(aggregated_events)} events for user {user_id}",
                request_id=request_id,
                providers_used=providers_used,
            )
        else:
            logger.info(
                "Not caching response due to no successful providers or empty events",
                request_id=request_id,
                providers_used=providers_used,
                provider_errors=provider_errors,
                event_count=len(aggregated_events),
            )

        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            "Calendar events request completed",
            request_id=request_id,
            response_time_ms=response_time_ms,
            providers_used=providers_used,
        )

        return CalendarEventListApiResponse(
            success=True,
            data=aggregated_events,
            cache_hit=False,
            provider_used=(
                Provider(providers_used[0]) if len(providers_used) == 1 else None
            ),
            request_id=request_id,
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error(
            "Calendar events request failed", request_id=request_id, error=str(e)
        )
        raise ServiceError(message=f"Failed to fetch calendar events: {str(e)}")


@router.get("/events/{event_id}", response_model=CalendarEventDetailResponse)
async def get_calendar_event(
    request: Request,
    event_id: str = Path(..., description="Event ID (format: provider_originalId)"),
    service_name: str = Depends(service_permission_required(["read_calendar"])),
) -> CalendarEventDetailResponse:
    """
    Get a specific calendar event by ID.

    The event_id should be in the format "provider_originalId" (e.g., "google_abc123" or "microsoft_xyz789").
    This endpoint determines the correct provider from the event ID and fetches the full event details.

    Args:
        event_id: Event ID with provider prefix

    Returns:
        ApiResponse with the specific calendar event
    """
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()
    start_time = datetime.now(timezone.utc)

    logger.info(
        "Calendar event detail request",
        request_id=request_id,
        event_id=event_id,
        user_id=user_id,
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
            logger.info("Cache hit for event detail", request_id=request_id)
            return CalendarEventDetailResponse(
                success=True, data=cached_result, cache_hit=True, request_id=request_id
            )

        # Fetch from the specific provider
        event = await fetch_single_event(
            request_id, user_id, provider, original_event_id
        )

        if not event:
            raise NotFoundError("Event", event_id)

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

        logger.info(f"Event detail request completed in {response_time_ms}ms")

        return CalendarEventDetailResponse(
            success=True,
            data=response_data,
            cache_hit=False,
            provider_used=Provider(provider),
            request_id=request_id,
        )

    except NotFoundError:
        raise
    except Exception as e:
        logger.error("Event detail request failed", request_id=request_id, error=str(e))
        raise ServiceError(message=f"Failed to fetch event: {str(e)}")


@router.post("/events", response_model=CalendarEventApiResponse)
async def create_calendar_event(
    request: Request,
    event_data: CreateCalendarEventRequest,
    service_name: str = Depends(service_permission_required(["write_calendar"])),
) -> CalendarEventApiResponse:
    """
    Create a calendar event in a specific provider.

    This endpoint takes unified CalendarEvent data, "de-normalizes" it into the
    provider-specific format, and uses the correct API client to create the event.

    Args:
        event_data: Event content and configuration

    Returns:
        ApiResponse with created event details
    """
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"Create calendar event request: user_id={user_id}, "
        f"title='{event_data.title}', provider={event_data.provider}"
    )

    try:
        # Determine provider:
        # - If explicitly provided, use it
        # - Otherwise, attempt to use user's preferred provider
        # - Fallback to Google if no preferred provider is set
        provider: str
        if event_data.provider:
            provider = event_data.provider
        else:
            factory = await get_api_client_factory()
            preferred_provider = await factory.get_user_preferred_provider(user_id)
            provider = preferred_provider.value if preferred_provider else "google"

        # Validate provider
        if provider.lower() not in ["google", "microsoft"]:
            raise ValidationError(
                message=f"Invalid provider: {provider}. Must be 'google' or 'microsoft'",
                field="provider",
            )

        provider = provider.lower()

        # Get API client for provider (with graceful fallback when no provider specified)
        factory = await get_api_client_factory()
        client = await factory.create_client(user_id, provider)
        if client is None and not event_data.provider:
            # Try the other provider as a fallback if caller didn't specify
            fallback_provider = "microsoft" if provider == "google" else "google"
            client = await factory.create_client(user_id, fallback_provider)
            if client:
                provider = fallback_provider

        if client is None:
            raise AuthError(
                message=f"Failed to create API client for provider {provider}. User may not have connected this provider."
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

        # Build response using Pydantic model
        response_data = CalendarEventResponse(
            event_id=created_event_data.get("id") if created_event_data else None,
            provider=provider,
            status="created",
            created_at=datetime.now(timezone.utc).isoformat(),
            request_metadata={
                "user_id": user_id,
                "title": event_data.title,
                "start_time": event_data.start_time.isoformat(),
                "end_time": event_data.end_time.isoformat(),
                "provider": provider,
            },
        )

        # Calculate response time
        end_time = datetime.now(timezone.utc)
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)

        logger.info(
            f"Calendar event created successfully in {response_time_ms}ms via {provider}"
        )

        return CalendarEventApiResponse(
            success=True,
            data=response_data,
            cache_hit=False,
            provider_used=(
                Provider.GOOGLE if provider == "google" else Provider.MICROSOFT
            ),
            request_id=request_id,
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Create calendar event request failed: {e}")
        raise ServiceError(message=f"Failed to create calendar event: {str(e)}")


@router.put("/events/{event_id}", response_model=CalendarEventResponse)
async def update_calendar_event(
    request: Request,
    event_data: CreateCalendarEventRequest,
    event_id: str = Path(..., description="Event ID (format: provider_originalId)"),
    service_name: str = Depends(service_permission_required(["write_calendar"])),
) -> CalendarEventResponse:
    """
    Update a calendar event by ID.

    This endpoint takes unified CalendarEvent data, "de-normalizes" it into the
    provider-specific format, and uses the correct API client to update the event.

    Args:
        event_id: Event ID with provider prefix (e.g., "google_abc123")
        event_data: Updated event content and configuration

    Returns:
        ApiResponse with updated event details
    """
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"Update calendar event request: event_id={event_id}, user_id={user_id}, "
        f"title='{event_data.title}'"
    )

    try:
        # Parse provider from event_id
        provider, original_event_id = parse_event_id(event_id)

        # Get API client for provider
        factory = await get_api_client_factory()
        client = await factory.create_client(user_id, provider)
        if client is None:
            raise AuthError(
                message=f"Failed to create API client for provider {provider}. User may not have connected this provider."
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
            f"Calendar event updated successfully in {response_time_ms}ms via {provider}"
        )

        # Help type checker understand the dict type
        request_metadata: Dict[str, Any] = cast(
            Dict[str, Any], response_data["request_metadata"]
        )
        return CalendarEventResponse(
            event_id=event_id,
            provider=provider,
            status="updated",
            updated_at=datetime.now(timezone.utc).isoformat(),
            event_data=CalendarEvent(
                id=event_id,
                calendar_id="primary",
                title=actual_title,
                description=actual_description,
                start_time=datetime.fromisoformat(actual_start_time),
                end_time=datetime.fromisoformat(actual_end_time),
                all_day=False,
                location=actual_location,
                attendees=event_data.attendees or [],
                organizer=None,
                status="confirmed",
                visibility="default",
                provider=Provider(provider),
                provider_event_id=original_event_id,
                account_email="",  # Will be filled by the client
                account_name="",  # Will be filled by the client
                calendar_name="Primary Calendar",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            request_metadata=request_metadata,
        )

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Update calendar event request failed: {e}")
        raise ServiceError(message=f"Failed to update calendar event: {str(e)}")


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

        logger.info(f"Google Calendar event created successfully: {result.get('id')}")
        return result

    except Exception as e:
        logger.error(f"Failed to create Google Calendar event: {e}")
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
            f"Microsoft Calendar event created successfully: {result.get('id')}"
        )
        return result

    except Exception as e:
        logger.error(f"Failed to create Microsoft Calendar event: {e}")
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

        logger.info(f"Google Calendar event updated successfully: {event_id}")
        return result

    except Exception as e:
        logger.error(f"Failed to update Google Calendar event: {e}")
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

        logger.info(f"Microsoft Calendar event updated successfully: {event_id}")
        return result

    except Exception as e:
        logger.error(f"Failed to update Microsoft Calendar event: {e}")
        raise


@router.delete("/events/{event_id}", response_model=CalendarEventDetailResponse)
async def delete_calendar_event(
    request: Request,
    event_id: str = Path(..., description="Event ID (format: provider_originalId)"),
    service_name: str = Depends(service_permission_required(["write_calendar"])),
) -> CalendarEventDetailResponse:
    """
    Delete a calendar event by ID.

    This endpoint requires logic to find the original provider from the event ID
    and use its API to delete the event.

    Args:
        event_id: Event ID with provider prefix (e.g., "google_abc123")

    Returns:
        ApiResponse confirming deletion
    """
    user_id = await get_user_id_from_gateway(request)
    request_id = get_request_id()
    start_time = datetime.now(timezone.utc)

    logger.info(
        f"Delete calendar event request: event_id={event_id}, user_id={user_id}"
    )

    try:
        # Parse provider from event_id
        provider, original_event_id = parse_event_id(event_id)

        # Get API client for provider
        factory = await get_api_client_factory()
        client = await factory.create_client(user_id, provider)
        if client is None:
            raise AuthError(
                message=f"Failed to create API client for provider {provider}. User may not have connected this provider."
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
            f"Calendar event deleted successfully in {response_time_ms}ms via {provider}"
        )

        return CalendarEventDetailResponse(
            success=True,
            data=response_data,
            cache_hit=False,
            provider_used=Provider(provider),
            request_id=request_id,
        )

    except AuthError:
        raise
    except Exception as e:
        logger.error(f"Delete calendar event request failed: {e}")
        raise ServiceError(message=f"Failed to delete calendar event: {str(e)}")


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

        logger.info(f"Google Calendar event deleted successfully: {event_id}")

    except Exception as e:
        logger.error(f"Failed to delete Google Calendar event: {e}")
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

        logger.info(f"Microsoft Calendar event deleted successfully: {event_id}")

    except Exception as e:
        logger.error(f"Failed to delete Microsoft Calendar event: {e}")
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
        logger.debug(f"Creating {provider} client with scopes: {calendar_scopes}")
        factory = await get_api_client_factory()
        client = await factory.create_client(user_id, provider, calendar_scopes)
        if client is None:
            logger.error(f"Failed to create API client for provider {provider}")
            raise ValueError(f"Failed to create API client for provider {provider}")
        logger.debug(f"Successfully created {provider} client")

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
                            f"Failed to fetch from Google calendar {calendar_id}: {calendar_error}"
                        )
                        continue

                normalized_events = all_events[:limit]  # Apply limit after aggregation

            elif provider == "microsoft":
                microsoft_client = cast(MicrosoftAPIClient, client)

                # Fetch events from Outlook
                logger.debug(
                    f"Fetching Microsoft events with start_time={start_dt.isoformat()}, end_time={end_dt.isoformat()}"
                )
                events_response = await microsoft_client.get_events(
                    calendar_id=None,  # Use primary calendar
                    start_time=start_dt.isoformat(),
                    end_time=end_dt.isoformat(),
                    top=limit,
                    skip=0,
                    order_by="start/dateTime asc",
                )
                events = events_response.get("value", [])
                logger.debug(f"Microsoft API returned {len(events)} events")

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
                f"Successfully fetched {len(normalized_events)} events from {provider}"
            )
            return normalized_events, provider

    except Exception as e:
        logger.error(
            "Failed to fetch events from provider",
            request_id=request_id,
            provider=provider,
            error=str(e),
        )
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
        factory = await get_api_client_factory()
        client = await factory.create_client(user_id, provider, calendar_scopes)
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
        logger.error(f"Failed to fetch event {original_event_id} from {provider}: {e}")
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


def find_available_slots(
    start_dt: datetime,
    end_dt: datetime,
    duration_minutes: int,
    events: List[CalendarEvent],
) -> List[Dict[str, datetime]]:
    """
    Find available time slots within a given range.

    Args:
        start_dt: Start datetime for the search range
        end_dt: End datetime for the search range
        duration_minutes: Duration of the meeting in minutes
        events: List of existing calendar events

    Returns:
        List of available time slots as dictionaries with 'start' and 'end' keys
    """
    # Sort events by start time
    sorted_events = sorted(events, key=lambda e: e.start_time)

    # Ensure all datetimes are timezone-aware and in UTC
    def ensure_timezone_aware(dt: datetime) -> datetime:
        """Ensure datetime is timezone-aware and convert to UTC."""
        if dt.tzinfo is None:
            # If naive, assume UTC
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            # If timezone-aware, convert to UTC
            dt = dt.astimezone(timezone.utc)
        return dt

    # Convert input datetimes to UTC
    start_dt = ensure_timezone_aware(start_dt)
    end_dt = ensure_timezone_aware(end_dt)

    # Initialize available slots
    available_slots = []
    current_time = start_dt

    # Duration as timedelta
    duration_td = timedelta(minutes=duration_minutes)

    for event in sorted_events:
        # Ensure event datetimes are timezone-aware and in UTC
        event_start = ensure_timezone_aware(event.start_time)
        event_end = ensure_timezone_aware(event.end_time)

        # Skip events outside our range
        if event_end <= start_dt or event_start >= end_dt:
            continue

        # If there's a gap before this event, check if it's long enough
        if event_start > current_time:
            slot_end = event_start
            if slot_end - current_time >= duration_td:
                available_slots.append(
                    {
                        "start": current_time,
                        "end": slot_end,
                    }
                )

        # Move current_time to the end of this event
        current_time = max(current_time, event_end)

    # Check if there's time after the last event
    if current_time < end_dt:
        slot_end = end_dt
        if slot_end - current_time >= duration_td:
            available_slots.append(
                {
                    "start": current_time,
                    "end": slot_end,
                }
            )

    return available_slots


def parse_event_id(event_id: str) -> tuple[str, str]:
    """
    Parse a unified event ID to extract provider and original ID.

    Args:
        event_id: Unified event ID (format: "provider_originalId")

    Returns:
        Tuple of (provider, original_event_id)

    Raises:
        ValidationError: If event ID format is invalid
    """
    try:
        if "_" not in event_id:
            raise ValidationError(message="Invalid event ID format", field="event_id")

        parts = event_id.split("_", 1)
        provider_prefix = parts[0].lower()
        original_id = parts[1]

        # Map provider prefixes to standard names
        provider_map = {"google": "google", "microsoft": "microsoft"}

        provider = provider_map.get(provider_prefix)
        if not provider:
            raise ValidationError(
                message=f"Unknown provider prefix: {provider_prefix}", field="provider"
            )

        return provider, original_id

    except Exception:
        raise ValidationError(
            message=f"Invalid event ID format: {event_id}. Expected format: 'provider_originalId'",
            field="event_id",
        )
