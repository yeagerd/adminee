"""
Authentication module for Chat Service.

Provides API key based authentication for incoming requests from the frontend.
"""

from typing import Any, Callable, Dict, List

from fastapi import Request

from services.chat.settings import get_settings
from services.common.api_key_auth import (
    APIKeyConfig,
    make_service_permission_required,
    make_verify_service_authentication,
)
from services.common.logging_config import get_logger

logger = get_logger(__name__)

# API Key configurations mapped by settings key names
API_KEY_CONFIGS: Dict[str, APIKeyConfig] = {
    "api_frontend_chat_key": APIKeyConfig(
        client="frontend",
        service="chat-service-access",
        permissions=[
            "read_chats",
            "write_chats",
            "read_threads",
            "write_threads",
            "read_feedback",
            "write_feedback",
        ],
        settings_key="api_frontend_chat_key",
    ),
}

# Client-level permissions
CLIENT_PERMISSIONS = {
    "frontend": [
        "read_chats",
        "write_chats",
        "read_threads",
        "write_threads",
        "read_feedback",
        "write_feedback",
    ],
}

# Service-level permissions fallback (optional, for legacy support)
SERVICE_PERMISSIONS = {
    "chat-service-access": [
        "read_chats",
        "write_chats",
        "read_threads",
        "write_threads",
        "read_feedback",
        "write_feedback",
    ],
}

verify_service_authentication = make_verify_service_authentication(
    API_KEY_CONFIGS, get_settings
)


def service_permission_required(
    required_permissions: List[str],
) -> Callable[[Request], Any]:
    return make_service_permission_required(
        required_permissions,
        API_KEY_CONFIGS,
        get_settings,
        SERVICE_PERMISSIONS,
    )
