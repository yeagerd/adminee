from datetime import datetime
from typing import List, Optional

import httpx

from services.common.logging_config import request_id_var
from services.meetings.settings import get_settings


async def get_user_availability(
    user_id: str, start: str, end: str, duration: int
) -> dict:
    settings = get_settings()
    url = f"{settings.office_service_url}/v1/calendar/availability"
    headers = {"X-API-Key": settings.api_meetings_office_key, "X-User-Id": user_id}

    # Propagate request ID for distributed tracing
    request_id = request_id_var.get()
    if request_id and request_id != "uninitialized":
        headers["X-Request-Id"] = request_id

    params = {"start": start, "end": end, "duration": str(duration)}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()


async def create_calendar_event(
    user_id: str,
    title: str,
    description: Optional[str],
    start_time: datetime,
    end_time: datetime,
    attendees_emails: List[str],
    location: Optional[str] = None,
) -> dict:
    settings = get_settings()
    url = f"{settings.office_service_url}/v1/calendar/events"
    headers = {"X-API-Key": settings.api_meetings_office_key, "X-User-Id": user_id}

    # Propagate request ID for distributed tracing
    request_id = request_id_var.get()
    if request_id and request_id != "uninitialized":
        headers["X-Request-Id"] = request_id

    # Convert participants to EmailAddress format
    from services.office.schemas import EmailAddress

    attendee_list = [
        EmailAddress(email=email, name=email.split("@")[0])
        for email in attendees_emails
    ]

    # Create event data using the existing CreateCalendarEventRequest schema
    from services.office.schemas import CreateCalendarEventRequest

    event_data = CreateCalendarEventRequest(
        title=title,
        description=description or "",
        start_time=start_time,
        end_time=end_time,
        all_day=False,
        location=location,
        attendees=attendee_list,
        calendar_id=None,
        provider=None,  # Let the office service use the user's preferred provider
        visibility="default",
        status="confirmed",
    )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url, headers=headers, json=event_data.model_dump(mode="json")
        )
        resp.raise_for_status()
        return resp.json()


async def update_calendar_event(
    user_id: str,
    event_id: str,
    title: str,
    description: Optional[str],
    start_time: datetime,
    end_time: datetime,
    attendees_emails: List[str],
    location: Optional[str] = None,
) -> dict:
    settings = get_settings()
    url = f"{settings.office_service_url}/v1/calendar/events/{event_id}"
    headers = {"X-API-Key": settings.api_meetings_office_key, "X-User-Id": user_id}

    # Propagate request ID for distributed tracing
    request_id = request_id_var.get()
    if request_id and request_id != "uninitialized":
        headers["X-Request-Id"] = request_id

    # Convert participants to EmailAddress format
    from services.office.schemas import CreateCalendarEventRequest, EmailAddress

    attendee_list = [
        EmailAddress(email=email, name=email.split("@")[0])
        for email in attendees_emails
    ]

    event_data = CreateCalendarEventRequest(
        title=title,
        description=description or "",
        start_time=start_time,
        end_time=end_time,
        all_day=False,
        location=location,
        attendees=attendee_list,
        calendar_id=None,
        provider=None,
        visibility="default",
        status="confirmed",
    )

    params = {"user_id": user_id}
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            url,
            headers=headers,
            params=params,
            json=event_data.model_dump(mode="json"),
        )
        resp.raise_for_status()
        return resp.json()
