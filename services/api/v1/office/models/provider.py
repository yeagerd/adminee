"""
Office service provider models.
"""

from enum import Enum


class Provider(str, Enum):
    """Supported office integration providers."""

    GOOGLE = "google"
    MICROSOFT = "microsoft"
