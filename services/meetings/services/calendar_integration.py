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
    url = f"{settings.office_service_url}/v1/calendar/create-meeting"
    headers = {"X-API-Key": settings.api_meetings_office_key, "X-User-Id": user_id}
    data = {
        "pollId": poll_id,
        "selectedSlotId": selected_slot_id,
        "participants": participants,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=data)
        resp.raise_for_status()
        return resp.json()
