from datetime import datetime
from typing import List, Optional, Type  # Added Type for provider class type hint

import pytz
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel  # Added BaseModel import

from .exceptions import (  # These GraphAPI... errors are specific to MS Graph.; We might need more generic versions for ProviderError; This might become ProviderError later if we generalize exceptions
    GraphAPIAuthError,
    GraphAPIClientError,
    GraphAPIDecodingError,
    GraphAPIError,
    GraphAPIRateLimitError,
    GraphAPIServerError,
    GraphClientError,
    InvalidInputError,
    ProviderAuthError,
    ProviderNotFoundError,
)
from .models import CalendarEvent, CalendarEventResponse

# Removed: from .services.graph_client import get_calendar_events
from .providers.base import CalendarProvider
from .providers.google_calendar import GoogleCalendarProvider  # Placeholder
from .providers.microsoft_graph import MicrosoftGraphProvider

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Mapping of provider_type strings to provider classes
PROVIDER_MAP: dict[str, Type[CalendarProvider]] = {
    "microsoft": MicrosoftGraphProvider,
    "google": GoogleCalendarProvider,
}


@app.get("/events", response_model=CalendarEventResponse)
async def list_calendar_events(
    token: str = Depends(oauth2_scheme),
    provider_type: str = Query(
        ..., description="The calendar provider to use (e.g., 'microsoft', 'google')"
    ),
    start_date: Optional[str] = Query(
        None, description="Start date in YYYY-MM-DD format (user's local time)"
    ),
    end_date: Optional[str] = Query(
        None, description="End date in YYYY-MM-DD format (user's local time)"
    ),
    user_timezone: Optional[str] = Query(
        "UTC",
        description="User's IANA timezone ID (e.g., America/New_York). Defaults to UTC.",
    ),
):
    """
    Lists calendar events from the specified provider, interpreted in the user's local timezone.
    Requires a provider-specific access token. Defaults to today's events in user_timezone.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Bearer token missing or invalid")

    ProviderClass = PROVIDER_MAP.get(provider_type.lower())
    if not ProviderClass:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider_type: {provider_type}. Supported types are: {list(PROVIDER_MAP.keys())}",
        )

    provider_instance = ProviderClass()  # Instantiate the chosen provider

    final_user_timezone = (
        user_timezone if user_timezone and user_timezone.strip() else "UTC"
    )

    start_dt_obj: Optional[datetime] = None
    end_dt_obj: Optional[datetime] = None

    # Default to "today" if no date range is provided by the API caller
    if start_date is None and end_date is None:
        today_date = datetime.now().date()
        start_dt_obj = datetime(
            today_date.year, today_date.month, today_date.day, 0, 0, 0
        )
        end_dt_obj = datetime(
            today_date.year, today_date.month, today_date.day, 23, 59, 59, 999999
        )
    else:
        if start_date:
            try:
                parsed_date = datetime.strptime(start_date, "%Y-%m-%d")
                start_dt_obj = datetime(
                    parsed_date.year, parsed_date.month, parsed_date.day, 0, 0, 0
                )
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD."
                )

        if end_date:
            try:
                parsed_date = datetime.strptime(end_date, "%Y-%m-%d")
                end_dt_obj = datetime(
                    parsed_date.year,
                    parsed_date.month,
                    parsed_date.day,
                    23,
                    59,
                    59,
                    999999,
                )
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD."
                )

        # Ensure both are set if one was provided, or raise if only one is set (as provider expects both or none for defaulting)
        if (start_dt_obj and not end_dt_obj) or (not start_dt_obj and end_dt_obj):
            raise HTTPException(
                status_code=400,
                detail="If providing a date range, both start_date and end_date are required.",
            )

    # At this point, start_dt_obj and end_dt_obj are either both set (to today, or from params) or an error was raised.
    # The provider's get_events expects non-optional datetime for start/end.
    if start_dt_obj is None or end_dt_obj is None:
        raise HTTPException(
            status_code=400,
            detail="Both start_date and end_date must be provided or defaulted."
        )
    if start_dt_obj >= end_dt_obj:  # This check is now for non-None dates
        raise HTTPException(
            status_code=400,
            detail="If both dates are provided, end_date must be after start_date.",
        )

    try:
        events_response = await provider_instance.get_events(
            token=token,
            user_timezone=final_user_timezone,
            start_datetime=start_dt_obj,  # Now guaranteed to be non-None datetime
            end_datetime=end_dt_obj,  # Now guaranteed to be non-None datetime
        )
        return events_response
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Note: The GraphAPI... exceptions are specific to MicrosoftGraphProvider.
    # If GoogleCalendarProvider raises different exceptions, we'd need to handle them
    # or make the providers raise more generic exceptions defined in base or exceptions.py.
    except GraphAPIAuthError as e:
        detail_msg = f"Authentication error with {provider_type} calendar provider."
        if e.status_code == 401:
            detail_msg = f"{provider_type.capitalize()} token is invalid or expired."
        elif e.status_code == 403:
            detail_msg = f"Forbidden. Insufficient permissions for {provider_type} calendar access."
        if e.graph_error_details and e.graph_error_details.get("error", {}).get(
            "message"
        ):
            detail_msg += (
                f" Provider details: {e.graph_error_details['error']['message']}"
            )
        raise HTTPException(
            status_code=e.status_code if e.status_code else 401, detail=detail_msg
        )
    except GraphAPIRateLimitError as e:
        detail_msg = f"Rate limit exceeded with {provider_type} calendar API."
        if e.graph_error_details and e.graph_error_details.get("error", {}).get(
            "message"
        ):
            detail_msg += (
                f" Provider details: {e.graph_error_details['error']['message']}"
            )
        raise HTTPException(status_code=429, detail=detail_msg)
    except GraphAPIClientError as e:
        detail_msg = f"A client-side error occurred with {provider_type} calendar API."
        if e.graph_error_details and e.graph_error_details.get("error", {}).get(
            "message"
        ):
            detail_msg += (
                f" Provider details: {e.graph_error_details['error']['message']}"
            )
        raise HTTPException(
            status_code=e.status_code if e.status_code else 400, detail=detail_msg
        )
    except (GraphAPIServerError, GraphAPIDecodingError, GraphClientError) as e:
        print(
            f"Unhandled Provider Client or Server Error ({provider_type}): {type(e).__name__} - {str(e)}"
        )
        raise HTTPException(
            status_code=502,
            detail=f"An error occurred while communicating with the {provider_type} calendar service.",
        )
    except Exception as e:
        print(
            f"Unexpected server error in list_calendar_events ({provider_type}): {type(e).__name__} - {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail="An unexpected internal server error occurred."
        )


@app.get("/")
async def root():
    return {"message": "Calendar Service is running"}


# Placeholder for future Pydantic models and CRUD operations


def get_calendar_provider(
    provider_type: str, token: Optional[str] = None
) -> CalendarProvider:
    provider_class = PROVIDER_MAP.get(provider_type.lower())
    if not provider_class:
        raise ProviderNotFoundError(f"Calendar provider '{provider_type}' not found.")
    # Check if provider_class has requires_auth attribute and call it if present
    requires_auth = getattr(provider_class, "requires_auth", None)
    if callable(requires_auth) and requires_auth():
        if not token:
            raise ProviderAuthError(
                f"Authentication token required for {provider_type} but not provided."
            )
    # Instantiate provider without unexpected keyword arguments
    return provider_class()


@app.post("/events/", response_model=List[CalendarEvent])
async def get_events_from_provider(
    provider_type: str = Query(
        ..., description="The type of calendar provider (e.g., 'microsoft_graph')"
    ),
    token: Optional[str] = Query(None, description="OAuth token for the provider"),
    user_timezone: Optional[str] = Query(
        "UTC",
        description="User's local IANA timezone. Defaults to UTC. Event times will be returned in this timezone if provider supports it, or converted.",
    ),
    start_datetime_str: Optional[str] = Query(
        None,
        description="Start datetime in ISO format (YYYY-MM-DDTHH:MM:SS). Defaults to start of today in user_timezone.",
    ),
    end_datetime_str: Optional[str] = Query(
        None,
        description="End datetime in ISO format (YYYY-MM-DDTHH:MM:SS). Defaults to end of today in user_timezone.",
    ),
):
    try:
        provider = get_calendar_provider(provider_type, token)
    except ProviderNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ProviderAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))

    try:
        if user_timezone is None:
            raise HTTPException(
                status_code=400, detail="User timezone must be provided."
            )
        tz = pytz.timezone(user_timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        raise HTTPException(
            status_code=400, detail=f"Invalid timezone: {user_timezone}"
        )

    now_user_tz = datetime.now(tz)

    if start_datetime_str:
        try:
            start_dt_naive = datetime.fromisoformat(start_datetime_str)
            start_dt = tz.localize(
                start_dt_naive, is_dst=None
            )  # Assume naive input is in user_timezone
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid start_datetime format. Use YYYY-MM-DDTHH:MM:SS.",
            )
    else:
        start_dt = now_user_tz.replace(hour=0, minute=0, second=0, microsecond=0)

    if end_datetime_str:
        try:
            end_dt_naive = datetime.fromisoformat(end_datetime_str)
            end_dt = tz.localize(
                end_dt_naive, is_dst=None
            )  # Assume naive input is in user_timezone
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid end_datetime format. Use YYYY-MM-DDTHH:MM:SS.",
            )
    else:
        end_dt = now_user_tz.replace(hour=23, minute=59, second=59, microsecond=999999)

    if start_dt >= end_dt:
        raise HTTPException(
            status_code=400, detail="End datetime must be after start datetime."
        )

    try:
        # Providers expect naive datetime objects representing the user's local time window
        events = await provider.get_events(
            token=token or "",
            user_timezone=user_timezone,
            start_datetime=start_dt.replace(tzinfo=None),
            end_datetime=end_dt.replace(tzinfo=None),
        )
        return events
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GraphAPIError as e:  # Catching specific provider errors
        raise HTTPException(
            status_code=e.status_code if e.status_code is not None else 500,
            detail=str(e),
        )
    except Exception as e:
        # Generic error catch for unexpected issues with the provider call
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve events from provider: {str(e)}"
        )


# --- Analysis Endpoints ---


class EventListPayload(BaseModel):
    events: List[CalendarEvent]


class SingleEventPayload(BaseModel):
    event: CalendarEvent


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
