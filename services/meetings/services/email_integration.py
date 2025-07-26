from typing import Optional

import httpx

from services.meetings.settings import get_settings


async def send_invitation_email(
    to_email: str, subject: str, body: str, user_id: str, provider: Optional[str] = None
) -> dict:
    settings = get_settings()
    url = f"{settings.office_service_url}/v1/email/send"
    headers = {"X-API-Key": settings.api_meetings_office_key, "X-User-Id": user_id}
    data = {
        "to": [{"email": to_email}],
        "subject": subject,
        "body": body,
    }
    if provider:
        data["provider"] = provider

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=data)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            # User hasn't connected their email provider
            raise ValueError(
                f"User {user_id} has not connected their email provider. "
                "Please connect your email account in settings before sending meeting invitations."
            )
        elif e.response.status_code == 403:
            # API key or permission issue
            raise ValueError(
                "Permission denied. Please check your email provider connection and try again."
            )
        else:
            # Other HTTP errors
            raise ValueError(f"Failed to send email: {e.response.text}")
    except httpx.RequestError as e:
        # Network or connection errors
        raise ValueError(f"Failed to connect to email service: {str(e)}")
    except Exception as e:
        # Unexpected errors
        raise ValueError(f"Unexpected error sending email: {str(e)}")
