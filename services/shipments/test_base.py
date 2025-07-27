"""
Base classes for Shipments Service tests.

Provides common setup and teardown for all shipments service tests,
including required environment variables and HTTP call prevention.
"""

import os

from services.common.test_utils import BaseSelectiveHTTPIntegrationTest


class BaseShipmentsTest(BaseSelectiveHTTPIntegrationTest):
    """Base class for all Shipments Service tests with HTTP call prevention."""

    def setup_method(self):
        """Set up Shipments Service test environment with required variables."""
        # Call parent setup to enable HTTP call detection
        super().setup_method(None)

        # Set required environment variables for Shipments Service
        os.environ["DB_URL_SHIPMENTS"] = "sqlite:///:memory:"
        os.environ["API_FRONTEND_SHIPMENTS_KEY"] = "test-api-key"

        # Optional environment variables with test defaults
        os.environ.setdefault("LOG_LEVEL", "INFO")
        os.environ.setdefault("LOG_FORMAT", "json")

    def teardown_method(self):
        """Clean up Shipments Service test environment."""
        # Call parent teardown to clean up HTTP patches
        super().teardown_method(None)
