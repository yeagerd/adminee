"""
Authentication package for User Management Service.

Provides NextAuth JWT validation, service-to-service authentication,
and user authorization helpers.
"""

from .nextauth import (
    get_current_user,
    get_current_user_flexible,
    get_current_user_from_gateway_headers,
    get_current_user_with_claims,
    require_user_ownership,
    verify_jwt_token,
    verify_user_ownership,
)
from .service_auth import (
    client_has_permission,
    get_client_permissions,
    service_permission_required,
    verify_service_authentication,
)

__all__ = [
    # NextAuth authentication
    "verify_jwt_token",
    "get_current_user",
    "get_current_user_with_claims",
    "get_current_user_flexible",
    "get_current_user_from_gateway_headers",
    "verify_user_ownership",
    "require_user_ownership",
    # Service authentication
    "verify_service_authentication",
    "service_permission_required",
    "get_client_permissions",
    "client_has_permission",
]
