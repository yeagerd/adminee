"""
Base classes for Shipments Service tests.

Provides common setup and teardown for all shipments service tests,
including required settings and HTTP call prevention.
"""

from services.common.test_utils import BaseSelectiveHTTPIntegrationTest


class BaseShipmentsTest(BaseSelectiveHTTPIntegrationTest):
    """Base class for all Shipments Service tests with HTTP call prevention."""

    def setup_method(self, method: object) -> None:
        """Set up Shipments Service test environment with required settings."""
        # Call parent setup to enable HTTP call detection
        super().setup_method(method)

        # Import shipments settings module
        import services.shipments.settings as shipments_settings

        # Store original settings singleton for cleanup
        self._original_settings = shipments_settings._settings

        # Create test settings instance
        from services.shipments.settings import Settings

        test_settings = Settings(
            db_url_shipments="sqlite:///:memory:",
            api_frontend_shipments_key="test-api-key",
            log_level="INFO",
            log_format="json",
            environment="development",
            debug=False,
            pagination_secret_key="test-pagination-secret-key",
        )

        # Set the test settings as the singleton
        shipments_settings._settings = test_settings

    def teardown_method(self, method: object) -> None:
        """Clean up Shipments Service test environment."""
        # Call parent teardown to clean up HTTP patches
        super().teardown_method(method)

        # Restore original settings singleton
        import services.shipments.settings as shipments_settings

        shipments_settings._settings = self._original_settings
