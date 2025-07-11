"""
Router package for User Management Service.

Exports all API routers for registration with the FastAPI application.
"""

from .integrations import provider_router
from .integrations import router as integrations_router
from .internal import router as internal_router
from .preferences import router as preferences_router
from .users import router as users_router

__all__ = [
    "users_router",
    "preferences_router",
    "integrations_router",
    "provider_router",
    "internal_router",
]
