from typing import Any, Dict, List

import httpx

from services.common.logging_config import request_id_var
from services.meetings.settings import get_settings


async def search_contacts(
    user_id: str, query: str, page_size: int = 25
) -> List[Dict[str, Any]]:
    """
    Search user's contacts via Office service unified contacts endpoint.
    """
    settings = get_settings()
    url = f"{settings.office_service_url}/v1/contacts"
    headers = {"X-API-Key": settings.api_meetings_office_key, "X-User-Id": user_id}

    request_id = request_id_var.get()
    if request_id and request_id != "uninitialized":
        headers["X-Request-Id"] = request_id

    params = {"q": query, "page_size": str(page_size)}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        # Expect list under "items" or return raw
        if isinstance(data, dict) and "items" in data:
            return data["items"] or []
        if isinstance(data, list):
            return data
        return []


async def create_contact(
    user_id: str, email: str, name: str | None = None
) -> Dict[str, Any]:
    """
    Create a new contact via Office service if not present.
    """
    settings = get_settings()
    url = f"{settings.office_service_url}/v1/contacts"
    headers = {"X-API-Key": settings.api_meetings_office_key, "X-User-Id": user_id}

    request_id = request_id_var.get()
    if request_id and request_id != "uninitialized":
        headers["X-Request-Id"] = request_id

    payload: Dict[str, Any] = {"email": email}
    if name:
        payload["name"] = name

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()
