import os
import httpx
from typing import Optional

OFFICE_SERVICE_URL = os.environ.get("OFFICE_SERVICE_URL", "http://localhost:8003")
API_KEY = os.environ.get("API_FRONTEND_OFFICE_KEY", "test-office-key")

async def send_invitation_email(to_email: str, subject: str, body: str, user_id: str, provider: Optional[str] = None):
    url = f"{OFFICE_SERVICE_URL}/email/send"
    headers = {"X-API-Key": API_KEY, "X-User-Id": user_id}
    data = {
        "to": [{"email": to_email}],
        "subject": subject,
        "body": body,
    }
    if provider:
        data["provider"] = provider
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=data)
        resp.raise_for_status()
        return resp.json() 