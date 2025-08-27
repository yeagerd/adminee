"""Office Service Core Models for API Package.

This module contains the core models and enums that are referenced by the office service schemas,
enabling inter-service communication without circular dependencies.
"""

from enum import Enum


class Provider(str, Enum):
    """Provider enumeration for office integrations."""

    GOOGLE = "google"
    MICROSOFT = "microsoft"


class ApiCallStatus(str, Enum):
    """API call status enumeration."""

    SUCCESS = "success"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
