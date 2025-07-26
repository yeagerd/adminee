import os
from typing import List

import httpx

OFFICE_SERVICE_URL = os.environ.get("OFFICE_SERVICE_URL", "http://localhost:8003")
API_KEY = os.environ.get("API_FRONTEND_OFFICE_KEY", "test-office-key")


async def get_user_availability(
    user_id: str, start: str, end: str, duration: int
) -> dict:
    url = f"{OFFICE_SERVICE_URL}/v1/calendar/availability"
    headers = {"X-API-Key": API_KEY, "X-User-Id": user_id}
    params = {"start": start, "end": end, "duration": str(duration)}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()


async def create_calendar_event(
    user_id: str, poll_id: str, selected_slot_id: str, participants: List[str]
) -> dict:
    url = f"{OFFICE_SERVICE_URL}/v1/calendar/create-meeting"
    headers = {"X-API-Key": API_KEY, "X-User-Id": user_id}
    data = {
        "pollId": poll_id,
        "selectedSlotId": selected_slot_id,
        "participants": participants,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=data)
        resp.raise_for_status()
        return resp.json()
