"""
Pydantic schemas package for User Management Service.

Exports all schema models for API request/response validation.
"""

from .user import (
    UserBase,
    UserCreate,
    UserDeleteResponse,
    UserListResponse,
    UserOnboardingUpdate,
    UserResponse,
    UserSearchRequest,
    UserUpdate,
)
from .webhook import ClerkWebhookEvent, ClerkWebhookEventData, WebhookResponse

__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
    "UserDeleteResponse",
    "UserOnboardingUpdate",
    "UserSearchRequest",
    # Webhook schemas
    "ClerkWebhookEvent",
    "ClerkWebhookEventData",
    "WebhookResponse",
]
