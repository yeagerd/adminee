"""
Authentication package for Contacts Service.

Provides permission-based API key authentication and JWT validation.
Uses the common api_key_auth and jwt_auth implementations for consistency.
"""

from services.contacts.auth.auth import (
    require_chat_service_auth,
    require_frontend_auth,
    require_meetings_service_auth,
    require_office_service_auth,
    require_shipments_service_auth,
    require_user_service_auth,
    service_permission_required,
    verify_service_authentication,
)
from services.common.jwt_auth import (
    get_current_user_from_gateway_headers,
    make_get_current_user,
    make_get_current_user_with_claims,
    require_user_ownership,
    verify_user_ownership,
)
from services.contacts.settings import get_settings

# Create JWT authentication functions using the service's settings
get_current_user = make_get_current_user(get_settings)
get_current_user_with_claims = make_get_current_user_with_claims(get_settings)

__all__ = [
    # Permission-based API key authentication (using common implementation)
    "verify_service_authentication",
    "service_permission_required",
    # JWT authentication (using common implementation)
    "get_current_user",
    "get_current_user_with_claims",
    "get_current_user_from_gateway_headers",
    "verify_user_ownership",
    "require_user_ownership",
    # Legacy service authentication (for backward compatibility)
    "require_user_service_auth",
    "require_office_service_auth",
    "require_chat_service_auth",
    "require_meetings_service_auth",
    "require_shipments_service_auth",
    "require_frontend_auth",
]
