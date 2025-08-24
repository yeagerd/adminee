"""
Permission-based API key authentication for the Contacts Service.

Uses the common api_key_auth implementation to provide consistent
authentication patterns across all Briefly services.
"""

from typing import Any, Callable, Dict, List

from fastapi import Request

from services.common.api_key_auth import (
    APIKeyConfig,
    make_service_permission_required,
    make_verify_service_authentication,
)
from services.contacts.settings import get_settings

# API Key configurations mapped by settings key names
API_KEY_CONFIGS: Dict[str, APIKeyConfig] = {
    "api_frontend_contacts_key": APIKeyConfig(
        client="frontend",
        service="contacts-service-access",
        permissions=[
            "read_contacts",
            "write_contacts",
            "search_contacts",
            "read_contact_stats",
        ],
        settings_key="api_frontend_contacts_key",
    ),
    "api_contacts_user_key": APIKeyConfig(
        client="user-service",
        service="contacts-service-access",
        permissions=[
            "read_contacts",
            "write_contacts",
            "search_contacts",
            "read_contact_stats",
        ],
        settings_key="api_contacts_user_key",
    ),
    "api_contacts_office_key": APIKeyConfig(
        client="office-service",
        service="contacts-service-access",
        permissions=[
            "read_contacts",
            "write_contacts",
            "search_contacts",
            "read_contact_stats",
        ],
        settings_key="api_contacts_office_key",
    ),
    "api_chat_contacts_key": APIKeyConfig(
        client="chat-service",
        service="contacts-service-access",
        permissions=[
            "read_contacts",
            "search_contacts",
        ],  # Read-only access for chat service
        settings_key="api_chat_contacts_key",
    ),
    "api_meetings_contacts_key": APIKeyConfig(
        client="meetings-service",
        service="contacts-service-access",
        permissions=[
            "read_contacts",
            "search_contacts",
        ],  # Read-only access for meetings service
        settings_key="api_meetings_contacts_key",
    ),
    "api_shipments_contacts_key": APIKeyConfig(
        client="shipments-service",
        service="contacts-service-access",
        permissions=[
            "read_contacts",
            "search_contacts",
        ],  # Read-only access for shipments service
        settings_key="api_shipments_contacts_key",
    ),
}

# Service-level permissions fallback
SERVICE_PERMISSIONS = {
    "contacts-service-access": [
        "read_contacts",
        "write_contacts",
        "search_contacts",
        "read_contact_stats",
    ],
}

# FastAPI dependencies using common implementation
verify_service_authentication = make_verify_service_authentication(
    API_KEY_CONFIGS, get_settings
)


def service_permission_required(
    required_permissions: List[str],
) -> Callable[[Request], Any]:
    """Require specific permissions for API key authentication."""
    return make_service_permission_required(
        required_permissions,
        API_KEY_CONFIGS,
        get_settings,
        SERVICE_PERMISSIONS,
    )


# Legacy convenience functions for backward compatibility
# These are kept for any existing code that might still use them
async def require_user_service_auth(request: Request) -> str:
    """Require authentication from User Service (legacy)."""
    return verify_service_authentication(request)


async def require_office_service_auth(request: Request) -> str:
    """Require authentication from Office Service (legacy)."""
    return verify_service_authentication(request)


async def require_chat_service_auth(request: Request) -> str:
    """Require authentication from Chat Service (legacy)."""
    return verify_service_authentication(request)


async def require_meetings_service_auth(request: Request) -> str:
    """Require authentication from Meetings Service (legacy)."""
    return verify_service_authentication(request)


async def require_shipments_service_auth(request: Request) -> str:
    """Require authentication from Shipments Service (legacy)."""
    return verify_service_authentication(request)


async def require_frontend_auth(request: Request) -> str:
    """Require authentication from Frontend (legacy)."""
    return verify_service_authentication(request)
