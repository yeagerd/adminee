"""
Router package for User Management Service.

Exports all API routers for registration with the FastAPI application.
"""

from services.user.routers.integrations import provider_router
from services.user.routers.integrations import router as integrations_router
from services.user.routers.internal import router as internal_router
from services.user.routers.preferences import router as preferences_router
from services.user.routers.users import router as users_router

__all__ = [
    "users_router",
    "preferences_router",
    "integrations_router",
    "provider_router",
    "internal_router",
]
