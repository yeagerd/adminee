"""
API key authentication and authorization for Office Service.

Provides granular permission-based API key authentication for service-to-service
and frontend-to-service communication with the principle of least privilege.
"""

from typing import Any, Callable, Dict, List, Optional

from fastapi import Request

from services.common.api_key_auth import (
    APIKeyConfig,
    build_api_key_mapping,
    get_client_from_api_key,
    get_permissions_from_api_key,
    make_service_permission_required,
    make_verify_service_authentication,
    verify_api_key,
)
from services.common.http_errors import AuthError
from services.common.logging_config import get_logger
from services.office.core.settings import get_settings

logger = get_logger(__name__)


# API Key configurations mapped by settings key names
API_KEY_CONFIGS: Dict[str, APIKeyConfig] = {
    # Frontend (Next.js API) keys - full permissions for user-facing operations
    "api_frontend_office_key": APIKeyConfig(
        client="frontend",
        service="office-service-access",
        permissions=[
            "read_emails",
            "send_emails",
            "read_calendar",
            "write_calendar",
            "read_files",
            "write_files",
            "read_contacts",
            "write_contacts",
            "health",
        ],
        settings_key="api_frontend_office_key",
    ),
    # Service-to-service keys - limited permissions
    "api_chat_office_key": APIKeyConfig(
        client="chat-service",
        service="office-service-access",
        permissions=[
            "read_emails",
            "read_calendar",
            "read_files",
            "read_contacts",
            "health",
        ],  # No write permissions
        settings_key="api_chat_office_key",
    ),
    # Meetings service key - can send emails for meeting invitations and manage calendar events
    "api_meetings_office_key": APIKeyConfig(
        client="meetings-service",
        service="office-service-access",
        permissions=[
            "send_emails",
            "read_calendar",
            "write_calendar",
            "read_contacts",
            "health",
        ],  # Send emails, read/write calendar, and health check
        settings_key="api_meetings_office_key",
    ),
    # Backfill service key - can trigger backfill jobs for any user
    "api_backfill_office_key": APIKeyConfig(
        client="backfill-service",
        service="office-service-access",
        permissions=[
            "backfill",  # New permission for backfill operations
            "read_emails",
            "read_calendar",
            "read_contacts",
            "health",
        ],
        settings_key="api_backfill_office_key",  # This maps to the settings field
    ),
}

# Service-level permissions fallback (optional, for legacy support)
SERVICE_PERMISSIONS = {
    "office-service-access": [
        "read_emails",
        "send_emails",
        "read_calendar",
        "write_calendar",
        "read_files",
        "write_files",
        "read_contacts",
        "write_contacts",
        "health",
        "backfill",  # Add backfill permission
    ],
}

# FastAPI dependencies
verify_service_authentication = make_verify_service_authentication(
    API_KEY_CONFIGS, get_settings
)


def service_permission_required(
    required_permissions: List[str],
) -> Callable[[Request], Any]:
    return make_service_permission_required(
        required_permissions,
        API_KEY_CONFIGS,
        get_settings,
        SERVICE_PERMISSIONS,
    )


def verify_backfill_api_key(request: Request) -> str:
    """Verify API key has backfill permission"""
    try:
        # Extract API key from request headers
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise AuthError("API key required")

        # Build API key mapping and verify API key
        api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
        service_name = verify_api_key(api_key, api_key_mapping)

        if not service_name:
            raise AuthError("Invalid API key")

        # Get client and permissions from the API key
        client_name = get_client_from_api_key(api_key, api_key_mapping)
        permissions = get_permissions_from_api_key(api_key, api_key_mapping)

        # Check if API key has backfill permission
        if "backfill" not in permissions:
            raise AuthError("API key does not have backfill permission")

        # Ensure client_name is not None
        if not client_name:
            raise AuthError("Invalid client name from API key")

        return client_name

    except Exception as e:
        logger.error(f"Backfill API key verification failed: {e}")
        raise AuthError(f"Backfill API key verification failed: {str(e)}")


def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Get current user from API key authentication.
    This function is used by FastAPI dependencies for user authentication.

    Returns:
        Dict containing user information including user_id
    """
    try:
        # Extract API key from request headers
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise AuthError("API key required")

        # Build API key mapping and verify API key
        api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
        service_name = verify_api_key(api_key, api_key_mapping)

        if not service_name:
            raise AuthError("Invalid API key")

        # Get client and permissions from the API key
        client_name = get_client_from_api_key(api_key, api_key_mapping)
        permissions = get_permissions_from_api_key(api_key, api_key_mapping)

        # hrm, I don't like this - we shouldn't be putting demo code in our production services.  I suspect the problem is that when we run as a demo, we don't have a JWT?  But we could get one from the nextauth_teset_server, asking the user to log in.  Afterall, we're only going to run backfill O(1) times, and run search many times

        # For demo purposes, we'll create a user context from the API key
        # In production, this would typically decode a JWT or look up user details
        user_id = client_name or "demo_user"

        return {
            "user_id": user_id,
            "client": client_name,
            "permissions": permissions,
            "authenticated": True,
        }

    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise AuthError(f"Authentication failed: {str(e)}")


def optional_service_auth(request: Request) -> Optional[str]:
    """Optional service authentication that returns None if no valid API key is provided."""
    try:
        return verify_service_authentication(request)
    except AuthError:
        return None


# Legacy compatibility - keeping existing class structure
class ServiceAPIKeyAuth:
    """Legacy service API key authentication handler for backward compatibility."""

    def __init__(self) -> None:
        logger.warning(
            "ServiceAPIKeyAuth is deprecated. Use the new functions directly."
        )

    def verify_api_key(self, api_key: str) -> Optional[str]:
        """Legacy method - use verify_api_key function instead."""
        api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
        return verify_api_key(api_key, api_key_mapping)

    def is_valid_service(self, service_name: str) -> bool:
        """Legacy method - use validate_service_permissions function instead."""
        return service_name == "office-service-access"


# Global service auth instance for backward compatibility
service_auth = ServiceAPIKeyAuth()


# Helper function for testing
def get_test_api_keys() -> Dict[str, str]:
    """Get test API keys for testing purposes."""
    settings = get_settings()
    return {
        "frontend": settings.api_frontend_office_key,
        "chat": settings.api_chat_office_key,
        "meetings": settings.api_meetings_office_key,
    }


# Helper function for testing
def verify_api_key_for_testing(api_key: str) -> Optional[str]:
    """Helper function for testing API key verification."""
    api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
    return verify_api_key(api_key, api_key_mapping)
