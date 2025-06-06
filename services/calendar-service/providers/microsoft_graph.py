import json
from datetime import datetime
from typing import (
    List,
)  # Keep List if CalendarEventResponse uses it, though not directly here

import httpx
import pytz

from ..exceptions import (
    GraphAPIAuthError,
    GraphAPIClientError,
    GraphAPIDecodingError,
    GraphAPIRateLimitError,
    GraphAPIServerError,
    GraphClientError,
    InvalidInputError,
)
from ..models import CalendarEventResponse
from .base import CalendarProvider

GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"  # Specific to Microsoft Graph


class MicrosoftGraphProvider(CalendarProvider):
    """Calendar provider implementation for Microsoft Graph API."""

    async def get_events(
        self,
        token: str,
        user_timezone: str,
        start_datetime: datetime,
        end_datetime: datetime,
        top: int = 50,
    ) -> CalendarEventResponse:
        """Fetches calendar events from Microsoft Graph. Interprets datetimes in the context of user_timezone."""

        try:
            pytz.timezone(user_timezone)  # Validate timezone string
        except pytz.exceptions.UnknownTimeZoneError as e:
            raise InvalidInputError(f"Invalid user_timezone: {user_timezone}") from e

        if start_datetime >= end_datetime:
            # This was the duplicated print/return None from previous file, now raising InvalidInputError
            raise InvalidInputError(
                f"start_datetime must be before end_datetime. Got start: {start_datetime}, end: {end_datetime}"
            )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": f'outlook.timezone="{user_timezone}"',
        }

        params = {
            "$top": str(top),
            "$select": "id,subject,bodyPreview,body,start,end,isAllDay,isCancelled,organizer,attendees,webLink,location,locations",
            "startDateTime": start_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
            "endDateTime": end_datetime.strftime("%Y-%m-%dT%H:%M:%S"),
        }

        request_url = f"{GRAPH_API_ENDPOINT}/me/calendarview"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(request_url, headers=headers, params=params)
                response.raise_for_status()
                return CalendarEventResponse(**response.json())
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                error_details = None
                try:
                    error_details = e.response.json()
                except json.JSONDecodeError:
                    pass

                error_message = (
                    f"Microsoft Graph API error ({status_code}) calling {request_url}"
                )
                if (
                    error_details
                    and "error" in error_details
                    and "message" in error_details["error"]
                ):
                    error_message += f": {error_details['error']['message']}"
                elif e.response.text:
                    error_message += f": {e.response.text[:200]}..."

                if status_code == 401 or status_code == 403:
                    raise GraphAPIAuthError(
                        error_message,
                        status_code=status_code,
                        graph_error_details=error_details,
                    ) from e
                elif status_code == 429:
                    raise GraphAPIRateLimitError(
                        error_message,
                        status_code=status_code,
                        graph_error_details=error_details,
                    ) from e
                elif 400 <= status_code < 500:
                    raise GraphAPIClientError(
                        error_message,
                        status_code=status_code,
                        graph_error_details=error_details,
                    ) from e
                elif 500 <= status_code < 600:
                    raise GraphAPIServerError(
                        error_message,
                        status_code=status_code,
                        graph_error_details=error_details,
                    ) from e
                else:
                    raise GraphClientError(
                        error_message,
                        status_code=status_code,
                        graph_error_details=error_details,
                    ) from e
            except httpx.RequestError as e:
                raise GraphClientError(
                    f"Request error occurred while calling {e.request.url!r}: {e}"
                ) from e
            except json.JSONDecodeError as e:
                raise GraphAPIDecodingError(
                    f"Failed to decode JSON response from {request_url}: {e}"
                ) from e
            except Exception as e:
                raise GraphClientError(
                    f"An unexpected error occurred in MicrosoftGraphProvider: {e}"
                ) from e
