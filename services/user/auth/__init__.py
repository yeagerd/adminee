"""
Authentication package for User Management Service.

Provides NextAuth JWT validation, service-to-service authentication,
and user authorization helpers.
"""

from .nextauth import (  # Changed from .clerk
    get_current_user,
    get_current_user_with_claims,
    require_user_ownership,
    verify_jwt_token,
    verify_user_ownership,
)
from .service_auth import (
    client_has_permission,
    get_client_permissions,
    get_current_service,
    require_service_auth,
    verify_service_authentication,
)
from .webhook_auth import WebhookSignatureVerifier, verify_webhook_signature

__all__ = [
    # Clerk authentication
    "verify_jwt_token",
    "get_current_user",
    "get_current_user_with_claims",
    "verify_user_ownership",
    "require_user_ownership",
    # Service authentication
    "verify_service_authentication",
    "get_current_service",
    "require_service_auth",
    "get_client_permissions",
    "client_has_permission",
    # Webhook authentication
    "WebhookSignatureVerifier",
    "verify_webhook_signature",
]
