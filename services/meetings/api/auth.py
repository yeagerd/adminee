from fastapi import HTTPException, Request

from services.common.api_key_auth import (
    APIKeyConfig,
    build_api_key_mapping,
    get_api_key_from_request,
    verify_api_key,
)
from services.meetings.settings import get_settings

# API Key configurations
API_KEY_CONFIGS = {
    "frontend": APIKeyConfig(
        client="frontend",
        service="meetings",
        permissions=["meetings:read", "meetings:write", "meetings:resend_invitation"],
        settings_key="api_frontend_meetings_key",
    ),
}


def verify_api_key_auth(request: Request) -> str:
    """
    Verify API key authentication and return the service name.
    """
    api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
    api_key = get_api_key_from_request(request)
    if not api_key or not verify_api_key(api_key, api_key_mapping):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )
    return "frontend"


def get_user_id_from_request(request: Request) -> str:
    """
    Extract user ID from request headers.

    The meetings service expects user identity via X-User-Id header.
    """
    user_id_str = request.headers.get("X-User-Id")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    return user_id_str
