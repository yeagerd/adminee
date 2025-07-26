from datetime import datetime, timedelta, timezone
from typing import List

import httpx

from services.meetings.settings import get_settings


async def get_user_availability(
    user_id: str, start: str, end: str, duration: int
) -> dict:
    settings = get_settings()
    url = f"{settings.office_service_url}/v1/calendar/availability"
    headers = {"X-API-Key": settings.api_meetings_office_key, "X-User-Id": user_id}
    params = {"start": start, "end": end, "duration": str(duration)}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()


async def create_calendar_event(
    user_id: str, poll_id: str, selected_slot_id: str, participants: List[str]
) -> dict:
    settings = get_settings()
    url = f"{settings.office_service_url}/v1/calendar/events"
    headers = {"X-API-Key": settings.api_meetings_office_key, "X-User-Id": user_id}

    # Convert participants to EmailAddress format
    from services.office.schemas import EmailAddress

    attendee_list = [
        EmailAddress(email=email, name=email.split("@")[0]) for email in participants
    ]

    # Create event data using the existing CreateCalendarEventRequest schema
    from services.office.schemas import CreateCalendarEventRequest

    event_data = CreateCalendarEventRequest(
        title=f"Meeting from poll {poll_id}",
        description=f"Meeting created from poll {poll_id}",
        start_time=datetime.now(timezone.utc),  # This should come from the slot data
        end_time=datetime.now(timezone.utc)
        + timedelta(hours=1),  # This should come from the slot data
        attendees=attendee_list,
        provider=None,  # Let the office service use the user's preferred provider
    )

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=event_data.model_dump())
        resp.raise_for_status()
        return resp.json()
