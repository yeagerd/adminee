"""
Secret management for Office Service.

This module provides a unified interface for retrieving secrets:
- From GCP Secret Manager (production)
- From environment variables (local development)
"""

from typing import Optional

from services.common.secrets import get_secret


def get_office_database_url() -> str:
    """Get the office service database URL.
    
    Returns:
        str: The database connection string for the office service.
    """
    return get_secret("DB_URL_OFFICE", "")


def get_api_frontend_office_key() -> str:
    """Get the API key for frontend to office service communication.
    
    Returns:
        str: The API key (default: 'default-office-key').
    """
    return get_secret("API_FRONTEND_OFFICE_KEY", "default-office-key")


def get_api_office_user_key() -> Optional[str]:
    """Get the API key for office service to user management service communication.
    
    Returns:
        Optional[str]: The API key if set, None otherwise.
    """
    return get_secret("API_OFFICE_USER_KEY")


def get_redis_url() -> str:
    """Get the Redis connection URL.
    
    Returns:
        str: The Redis connection URL (default: 'redis://localhost:6379').
    """
    return get_secret("REDIS_URL", "redis://localhost:6379")


def get_user_management_service_url() -> str:
    """Get the User Management service URL.
    
    Returns:
        str: The URL of the User Management service (default: 'http://localhost:8001').
    """
    return get_secret("USER_MANAGEMENT_SERVICE_URL", "http://localhost:8001")
