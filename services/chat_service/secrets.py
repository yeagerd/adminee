"""
Secret management for Chat Service.

This module provides a unified interface for retrieving secrets:
- From GCP Secret Manager (production)
- From environment variables (local development)
"""

from typing import Optional

from services.common.secrets import get_secret


def get_chat_database_url() -> str:
    """Get the chat service database URL.
    
    Returns:
        str: The database connection string for the chat service.
    """
    return get_secret("DB_URL_CHAT", "")


def get_api_frontend_chat_key() -> Optional[str]:
    """Get the API key for frontend to chat service communication.
    
    Returns:
        Optional[str]: The API key if set, None otherwise.
    """
    return get_secret("API_FRONTEND_CHAT_KEY")


def get_api_chat_user_key() -> Optional[str]:
    """Get the API key for chat service to user management service communication.
    
    Returns:
        Optional[str]: The API key if set, None otherwise.
    """
    return get_secret("API_CHAT_USER_KEY")


def get_api_chat_office_key() -> Optional[str]:
    """Get the API key for chat service to office service communication.
    
    Returns:
        Optional[str]: The API key if set, None otherwise.
    """
    return get_secret("API_CHAT_OFFICE_KEY")


def get_user_management_service_url() -> str:
    """Get the User Management service URL.
    
    Returns:
        str: The URL of the User Management service.
    """
    return get_secret("USER_MANAGEMENT_SERVICE_URL", "http://localhost:8001")


def get_office_service_url() -> str:
    """Get the Office service URL.
    
    Returns:
        str: The URL of the Office service.
    """
    return get_secret("OFFICE_SERVICE_URL", "http://localhost:8080")


def get_llm_provider() -> str:
    """Get the LLM provider name.
    
    Returns:
        str: The name of the LLM provider (default: 'openai').
    """
    return get_secret("LLM_PROVIDER", "openai")


def get_llm_model() -> str:
    """Get the LLM model name.
    
    Returns:
        str: The name of the LLM model (default: 'gpt-4.1-nano').
    """
    return get_secret("LLM_MODEL", "gpt-4.1-nano")
