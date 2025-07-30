"""
User authentication for Shipments Service.

Provides JWT token validation, user extraction, and user ownership validation.
Follows the same patterns as the user service authentication.
"""

from .nextauth import (
    get_current_user,
    get_current_user_flexible,
    get_current_user_from_gateway_headers,
    get_current_user_with_claims,
    require_user_ownership,
    verify_user_ownership,
)

__all__ = [
    "get_current_user",
    "get_current_user_flexible",
    "get_current_user_from_gateway_headers",
    "get_current_user_with_claims",
    "require_user_ownership",
    "verify_user_ownership",
]
