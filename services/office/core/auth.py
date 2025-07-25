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
            "health",
        ],  # No write permissions
        settings_key="api_chat_office_key",
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
        "health",
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
    }


# Helper function for testing
def verify_api_key_for_testing(api_key: str) -> Optional[str]:
    """Helper function for testing API key verification."""
    api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
    return verify_api_key(api_key, api_key_mapping)
