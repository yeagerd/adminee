"""
Common utilities and configurations for Briefly services.
"""

from .auth import (
    API_KEYS,
    APIKeyConfig,
    ServicePermissionRequired,
    get_api_key_from_request,
    get_client_from_api_key,
    get_permissions_from_api_key,
    has_permission,
    optional_service_auth,
    validate_service_permissions,
    verify_api_key,
    verify_service_authentication,
)
from .telemetry import (
    add_span_attributes,
    get_tracer,
    record_exception,
    setup_telemetry,
)

__all__ = [
    # Authentication
    "APIKeyConfig",
    "API_KEYS",
    "ServicePermissionRequired",
    "get_api_key_from_request",
    "get_client_from_api_key",
    "get_permissions_from_api_key",
    "has_permission",
    "optional_service_auth",
    "validate_service_permissions",
    "verify_api_key",
    "verify_service_authentication",
    # Telemetry
    "setup_telemetry",
    "get_tracer",
    "add_span_attributes",
    "record_exception",
]
