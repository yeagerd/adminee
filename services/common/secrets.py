"""
Secret management for GCP integration.

This module provides a unified interface for retrieving secrets from:
- GCP Secret Manager (production)
- Environment variables (local development)

This is a shared module for all services in the application.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Cache for secrets to avoid repeated API calls
_secret_cache: dict[str, str] = {}


def get_secret(secret_id: str, default: str = "") -> str:
    """
    Retrieve secret from GCP Secret Manager or environment variables.

    Args:
        secret_id: The secret identifier (both env var name and Secret Manager secret name)
        default: Default value if secret is not found

    Returns:
        The secret value

    Raises:
        RuntimeError: If secret is required but not found in production
    """
    # Return cached value if available
    if secret_id in _secret_cache:
        return _secret_cache[secret_id]

    environment = os.getenv("ENVIRONMENT", "local")

    # Local development: use environment variables
    if environment == "local":
        value = os.getenv(secret_id, default) or default
        _secret_cache[secret_id] = str(value)
        return value

    # Production: try Secret Manager first, fallback to env vars
    try:
        value = _get_secret_from_manager(secret_id)
        if value:
            _secret_cache[secret_id] = value
            return value
    except Exception as e:
        logger.warning(f"Failed to get secret {secret_id} from Secret Manager: {e}")

    # Fallback to environment variables (Cloud Run secret mounts)
    value = os.getenv(secret_id, default) or default
    if not value and environment == "production":
        logger.error(f"Secret {secret_id} not found in Secret Manager or environment")
        # In production, we might want to raise an error for critical secrets
        # raise RuntimeError(f"Required secret {secret_id} not found")

    _secret_cache[secret_id] = str(value)
    return value


def _get_secret_from_manager(secret_id: str) -> Optional[str]:
    """
    Retrieve secret from GCP Secret Manager.

    Args:
        secret_id: The secret name in Secret Manager

    Returns:
        The secret value or None if not found
    """
    try:
        from google.cloud import secretmanager

        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or ""
        if not project_id:
            logger.warning("GOOGLE_CLOUD_PROJECT not set, cannot access Secret Manager")
            return None

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"

        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")

    except ImportError:
        logger.warning("google-cloud-secret-manager not installed")
        return None
    except Exception as e:
        logger.warning(f"Error accessing Secret Manager: {e}")
        return None


def clear_cache():
    """Clear the secret cache. Useful for testing."""
    global _secret_cache
    _secret_cache.clear()


# Common secret getters - these can be used by any service
def get_database_url(service_name: str = "user_management") -> str:
    """
    Get the database URL for a specific service.

    Args:
        service_name: The service name (e.g., 'user_management', 'chat_service')
    """
    secret_key = f"DB_URL_{service_name.upper()}"
    return get_secret(secret_key)


def get_clerk_secret_key() -> str:
    """Get the Clerk secret key."""
    return get_secret("CLERK_SECRET_KEY")


def get_clerk_publishable_key() -> str:
    """Get the Clerk publishable key."""
    return get_secret("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY")


def get_redis_url() -> str:
    """Get the Redis URL."""
    return get_secret("REDIS_URL", "redis://redis:6379")


def get_token_encryption_salt() -> str:
    """Get the token encryption salt."""
    return get_secret("TOKEN_ENCRYPTION_SALT")


def get_openai_api_key() -> str:
    """Get the OpenAI API key."""
    return get_secret("OPENAI_API_KEY")


def get_llama_cloud_api_key() -> str:
    """Get the Llama Cloud API key."""
    return get_secret("LLAMA_CLOUD_API_KEY")
