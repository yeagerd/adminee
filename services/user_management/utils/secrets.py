"""
Secret management for User Management Service.

This module provides a unified interface for retrieving secrets:
- From GCP Secret Manager (production)
- From environment variables (local development)
"""

from typing import List, Optional

from services.common.secrets import get_secret


def get_user_management_database_url() -> str:
    """Get the user management service database URL.
    
    Returns:
        str: The database connection string for the user management service.
    """
    return get_secret("DB_URL_USER_MANAGEMENT", "")


def get_api_frontend_user_key() -> Optional[str]:
    """Get the API key for frontend to user management service communication.
    
    Returns:
        Optional[str]: The API key if set, None otherwise.
    """
    return get_secret("API_FRONTEND_USER_KEY")


def get_clerk_webhook_secret() -> Optional[str]:
    """Get the Clerk webhook secret for signature verification.
    
    Returns:
        Optional[str]: The Clerk webhook secret if set, None otherwise.
    """
    return get_secret("CLERK_WEBHOOK_SECRET")


def get_clerk_jwt_key() -> Optional[str]:
    """Get the Clerk JWT public key for token verification.
    
    Returns:
        Optional[str]: The Clerk JWT public key if set, None otherwise.
    """
    return get_secret("CLERK_JWT_KEY")


def get_google_client_id() -> Optional[str]:
    """Get the Google OAuth client ID.
    
    Returns:
        Optional[str]: The Google OAuth client ID if set, None otherwise.
    """
    return get_secret("GOOGLE_CLIENT_ID")


def get_google_client_secret() -> Optional[str]:
    """Get the Google OAuth client secret.
    
    Returns:
        Optional[str]: The Google OAuth client secret if set, None otherwise.
    """
    return get_secret("GOOGLE_CLIENT_SECRET")


def get_azure_ad_client_id() -> Optional[str]:
    """Get the Azure AD client ID.
    
    Returns:
        Optional[str]: The Azure AD client ID if set, None otherwise.
    """
    return get_secret("AZURE_AD_CLIENT_ID")


def get_azure_ad_client_secret() -> Optional[str]:
    """Get the Azure AD client secret.
    
    Returns:
        Optional[str]: The Azure AD client secret if set, None otherwise.
    """
    return get_secret("AZURE_AD_CLIENT_SECRET")


def get_azure_ad_tenant_id() -> Optional[str]:
    """Get the Azure AD tenant ID.
    
    Returns:
        Optional[str]: The Azure AD tenant ID if set, None otherwise.
    """
    return get_secret("AZURE_AD_TENANT_ID")


def get_oauth_redirect_uri() -> str:
    """Get the OAuth redirect URI.
    
    Returns:
        str: The OAuth redirect URI (default: http://localhost:8000/oauth/callback).
    """
    return get_secret("OAUTH_REDIRECT_URI", "http://localhost:8000/oauth/callback")


def get_oauth_base_url() -> str:
    """Get the base URL for OAuth callbacks.
    
    Returns:
        str: The base URL for OAuth callbacks (default: http://localhost:8000).
    """
    return get_secret("OAUTH_BASE_URL", "http://localhost:8000")


def get_celery_broker_url() -> str:
    """Get the Celery broker URL.
    
    Returns:
        str: The Celery broker URL (default: redis://localhost:6379/0).
    """
    return get_secret("CELERY_BROKER_URL", "redis://localhost:6379/0")


def get_celery_result_backend() -> str:
    """Get the Celery result backend URL.
    
    Returns:
        str: The Celery result backend URL (default: redis://localhost:6379/0).
    """
    return get_secret("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
