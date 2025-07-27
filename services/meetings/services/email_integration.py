from typing import Optional

import httpx

from services.meetings.settings import get_settings


async def get_user_email_providers(user_id: str) -> list[str]:
    """
    Get list of available email providers for a user.

    Args:
        user_id: User identifier

    Returns:
        List of available provider names (e.g., ['google', 'microsoft'])
    """
    settings = get_settings()
    url = f"{settings.user_management_service_url}/v1/internal/users/{user_id}/integrations"
    headers = {"X-API-Key": settings.api_meetings_user_key}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            # Extract active email providers
            available_providers = []
            for integration in data.get("integrations", []):
                provider = integration.get("provider", "").lower()
                status = integration.get("status", "").lower()

                # Only include active integrations for email providers
                if status == "active" and provider in ["google", "microsoft"]:
                    available_providers.append(provider)

            return available_providers
    except Exception:
        # If we can't fetch providers, return empty list
        return []


async def send_invitation_email(
    to_email: str, subject: str, body: str, user_id: str, provider: Optional[str] = None
) -> dict:
    settings = get_settings()
    url = f"{settings.office_service_url}/v1/email/send"
    headers = {"X-API-Key": settings.api_meetings_office_key, "X-User-Id": user_id}

    # If no provider specified, try to find an available one
    if not provider:
        available_providers = await get_user_email_providers(user_id)
        if available_providers:
            # Prefer Microsoft if available, otherwise use first available
            if "microsoft" in available_providers:
                provider = "microsoft"
            else:
                provider = available_providers[0]
        else:
            # No providers available
            raise ValueError(
                f"User {user_id} has no connected email providers. "
                "Please connect your email account in settings before sending meeting invitations."
            )

    data = {
        "to": [{"email": to_email}],
        "subject": subject,
        "body": body,
        "provider": provider,
    }

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
