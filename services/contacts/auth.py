"""
Authentication middleware for the Contacts Service.

Validates API keys from other services to enable service-to-service communication.
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.contacts.settings import get_settings

security = HTTPBearer()


async def get_api_key_from_header(request: Request) -> Optional[str]:
    """Extract API key from request headers."""
    # Check for API key in headers (common pattern for service-to-service auth)
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    
    # Fallback to Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix
    
    return None


async def validate_service_api_key(
    api_key: str,
    service_name: str
) -> bool:
    """Validate API key for a specific service."""
    settings = get_settings()
    
    # Map service names to their API keys
    service_api_keys = {
        "user": settings.api_contacts_user_key,
        "office": settings.api_contacts_office_key,
        "chat": settings.api_chat_contacts_key,
        "meetings": settings.api_meetings_contacts_key,
        "shipments": settings.api_shipments_contacts_key,
        "frontend": settings.api_frontend_contacts_key,
    }
    
    expected_key = service_api_keys.get(service_name)
    if not expected_key:
        return False
    
    return api_key == expected_key


async def require_service_auth(
    service_name: str,
    request: Request
) -> str:
    """Require authentication from a specific service."""
    api_key = await get_api_key_from_header(request)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    is_valid = await validate_service_api_key(api_key, service_name)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Invalid API key for {service_name} service",
        )
    
    return service_name


# Convenience functions for specific services
async def require_user_service_auth(request: Request) -> str:
    """Require authentication from User Service."""
    return await require_service_auth("user", request)


async def require_office_service_auth(request: Request) -> str:
    """Require authentication from Office Service."""
    return await require_service_auth("office", request)


async def require_chat_service_auth(request: Request) -> str:
    """Require authentication from Chat Service."""
    return await require_service_auth("chat", request)


async def require_meetings_service_auth(request: Request) -> str:
    """Require authentication from Meetings Service."""
    return await require_service_auth("meetings", request)


async def require_shipments_service_auth(request: Request) -> str:
    """Require authentication from Shipments Service."""
    return await require_service_auth("shipments", request)


async def require_frontend_auth(request: Request) -> str:
    """Require authentication from Frontend."""
    return await require_service_auth("frontend", request)
