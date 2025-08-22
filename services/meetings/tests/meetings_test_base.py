"""
Base classes for Meetings Service tests.

Provides common setup and teardown for all meetings service tests,
including required environment variables and database setup.
"""

import os
import tempfile
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.common.http_errors import register_briefly_exception_handlers
from services.common.logging_config import create_request_logging_middleware
from services.common.test_utils import BaseSelectiveHTTPIntegrationTest


class BaseMeetingsTest(BaseSelectiveHTTPIntegrationTest):
    """Base class for all Meetings Service tests with HTTP call prevention."""

    def setup_method(self, method):
        """Set up Meetings Service test environment with required variables."""
        # Call parent setup to enable HTTP call detection
        super().setup_method(method)

        # Disable rate limiting for tests
        from services.meetings.services.security import set_test_mode

        set_test_mode(True)

        # Reset any existing database connections to ensure clean state
        from services.meetings.models import reset_db

        reset_db()

        # Use a unique temp file for each test
        self._db_fd, self._db_path = tempfile.mkstemp(suffix=".sqlite3")
        db_url = f"sqlite:///{self._db_path}"

        # Set environment variables for test settings instead of manipulating the module
        os.environ["DB_URL_MEETINGS"] = db_url
        os.environ["API_EMAIL_SYNC_MEETINGS_KEY"] = "test-email-sync-key"
        os.environ["API_MEETINGS_OFFICE_KEY"] = "test-meetings-office-key"
        os.environ["API_MEETINGS_USER_KEY"] = "test-meetings-user-key"
        os.environ["API_FRONTEND_MEETINGS_KEY"] = "test-frontend-meetings-key"
        os.environ["OFFICE_SERVICE_URL"] = "http://localhost:8003"
        os.environ["USER_SERVICE_URL"] = "http://localhost:8001"
        os.environ["LOG_LEVEL"] = "INFO"
        os.environ["LOG_FORMAT"] = "json"
        os.environ["PAGINATION_SECRET_KEY"] = "test-pagination-secret-key"

        # Import all models to ensure they're registered with metadata
        import services.meetings.models.booking_entities
        import services.meetings.models.meeting
        from services.meetings.models import get_engine

        # Create all tables directly
        from services.meetings.models.base import Base

        engine = get_engine()
        Base.metadata.create_all(engine)

        # Import API modules to ensure they're loaded with the test session
        from services.meetings.api import (
            bookings_router,
            email_router,
            invitations_router,
            polls_router,
            public_router,
            slots_router,
        )

        # Create a new FastAPI app instance to avoid reloading the main module
        # This ensures the app uses the updated settings without breaking mocks
        self.app = FastAPI(
            title="Briefly Meetings Service Test",
            version="0.1.0",
            description="Meeting scheduling and polling microservice for Briefly (Test).",
        )

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Add request logging middleware
        self.app.middleware("http")(create_request_logging_middleware())

        # Register standardized exception handlers
        register_briefly_exception_handlers(self.app)

        self.app.include_router(
            polls_router, prefix="/api/v1/meetings/polls", tags=["polls"]
        )
        self.app.include_router(
            slots_router,
            prefix="/api/v1/meetings/polls/{poll_id}/slots",
            tags=["slots"],
        )
        self.app.include_router(
            invitations_router,
            prefix="/api/v1/meetings/polls/{poll_id}/send-invitations",
            tags=["invitations"],
        )
        self.app.include_router(
            public_router, prefix="/api/v1/public/polls", tags=["public"]
        )
        self.app.include_router(
            email_router,
            prefix="/api/v1/meetings/process-email-response",
            tags=["email"],
        )

        # Include booking endpoints router
        self.app.include_router(
            bookings_router, prefix="/api/v1/bookings", tags=["bookings"]
        )

        from fastapi.testclient import TestClient

        self.client = TestClient(self.app)

    def teardown_method(self, method):
        """Clean up test environment."""

        # Clean up database connections
        try:
            import asyncio

            from services.meetings.models import close_db

            # Run the async close_db function
            try:
                asyncio.run(close_db())
            except RuntimeError:
                # If we're already in an event loop, create a task in a separate thread
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, close_db())
                    future.result()
        except Exception as e:
            # If cleanup fails, log it but don't fail the test
            print(f"Warning: Could not close database connections: {e}")

        # Clean up environment variables
        env_vars_to_remove = [
            "DB_URL_MEETINGS",
            "API_EMAIL_SYNC_MEETINGS_KEY",
            "API_MEETINGS_OFFICE_KEY",
            "API_MEETINGS_USER_KEY",
            "API_FRONTEND_MEETINGS_KEY",
            "OFFICE_SERVICE_URL",
            "USER_SERVICE_URL",
            "LOG_LEVEL",
            "LOG_FORMAT",
            "PAGINATION_SECRET_KEY",
        ]

        for var in env_vars_to_remove:
            if var in os.environ:
                del os.environ[var]

        # Remove the temp DB file
        if hasattr(self, "_db_fd"):
            os.close(self._db_fd)
        if hasattr(self, "_db_path") and os.path.exists(self._db_path):
            os.unlink(self._db_path)

        # Call parent teardown to clean up HTTP patches
        super().teardown_method(method)


class BaseMeetingsIntegrationTest(BaseMeetingsTest):
    """Base class for Meetings Service integration tests with full app setup."""

    def setup_method(self, method):
        """Set up Meetings Service integration test environment."""
        # Call parent setup for environment variables and database
        super().setup_method(method)

        # Create test client using app from base class
        from fastapi.testclient import TestClient

        self.client = TestClient(self.app)

        # Set up authentication overrides if needed
        self._override_auth()

    def _override_auth(self):
        """Override authentication for testing."""
        # Override authentication dependencies if needed for testing
        # This can be customized based on specific test requirements
        pass
