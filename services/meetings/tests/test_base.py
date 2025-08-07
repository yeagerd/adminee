"""
Base classes for Meetings Service tests.

Provides common setup and teardown for all meetings service tests,
including required environment variables and database setup.
"""

import importlib
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

        # Use a unique temp file for each test
        self._db_fd, self._db_path = tempfile.mkstemp(suffix=".sqlite3")
        db_url = f"sqlite:///{self._db_path}"

        import services.meetings.settings as meetings_settings
        from services.meetings.settings import Settings

        test_settings = Settings(
            db_url_meetings=db_url,
            api_email_sync_meetings_key="test-email-sync-key",
            api_meetings_office_key="test-meetings-office-key",
            api_meetings_user_key="test-meetings-user-key",
            api_frontend_meetings_key="test-frontend-meetings-key",
            office_service_url="http://localhost:8003",
            user_service_url="http://localhost:8001",
            log_level="INFO",
            log_format="json",
            pagination_secret_key="test-pagination-secret-key",
        )
        self._original_settings = getattr(meetings_settings, "_settings", None)
        meetings_settings._settings = test_settings

        # Only reload models, not API modules to preserve mock patches
        # This prevents breaking mock patches applied by test decorators
        import services.meetings.models

        importlib.reload(services.meetings.models)
        import services.meetings.models.base

        importlib.reload(services.meetings.models.base)
        import services.meetings.models.meeting

        importlib.reload(services.meetings.models.meeting)

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from services.meetings import models

        # Ensure models are imported after reload

        models._test_engine = create_engine(
            db_url,
            echo=False,
            future=True,
            connect_args={"check_same_thread": False},
        )

        self._test_sessionmaker = sessionmaker(
            bind=models._test_engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )

        models.get_engine = lambda: models._test_engine

        @contextmanager
        def test_get_session():
            session = self._test_sessionmaker()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        self._original_get_session = models.get_session
        models.get_session = test_get_session

        from services.meetings.models.base import Base

        # Skip drop_all since tables might not exist yet
        Base.metadata.create_all(models._test_engine)

        # Create a new FastAPI app instance to avoid reloading the main module
        # This ensures the app uses the updated settings without breaking mocks
        app = FastAPI(
            title="Briefly Meetings Service Test",
            version="0.1.0",
            description="Meeting scheduling and polling microservice for Briefly (Test).",
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Add request logging middleware
        app.middleware("http")(create_request_logging_middleware())

        # Register standardized exception handlers
        register_briefly_exception_handlers(app)

        # Import and include routers after settings are configured
        from services.meetings.api import (
            email_router,
            invitations_router,
            polls_router,
            public_router,
            slots_router,
        )

        app.include_router(
            polls_router, prefix="/api/v1/meetings/polls", tags=["polls"]
        )
        app.include_router(
            slots_router,
            prefix="/api/v1/meetings/polls/{poll_id}/slots",
            tags=["slots"],
        )
        app.include_router(
            invitations_router,
            prefix="/api/v1/meetings/polls/{poll_id}/send-invitations",
            tags=["invitations"],
        )
        app.include_router(
            public_router, prefix="/api/v1/public/polls", tags=["public"]
        )
        app.include_router(
            email_router,
            prefix="/api/v1/meetings/process-email-response",
            tags=["email"],
        )

        from fastapi.testclient import TestClient

        self.client = TestClient(app)

    def teardown_method(self, method):
        """Clean up test environment."""

        import services.meetings.models

        if hasattr(self, "_original_get_session"):
            services.meetings.models.get_session = self._original_get_session

        import services.meetings.settings as meetings_settings

        if hasattr(self, "_original_settings"):
            if self._original_settings is None:
                if hasattr(meetings_settings, "_settings"):
                    delattr(meetings_settings, "_settings")
            else:
                meetings_settings._settings = self._original_settings

        from services.meetings import models

        if hasattr(models, "_test_engine"):
            models._test_engine.dispose()
            delattr(models, "_test_engine")

        # Remove the temp DB file
        if hasattr(self, "_db_fd"):
            os.close(self._db_fd)
        if hasattr(self, "_db_path") and os.path.exists(self._db_path):
            os.unlink(self._db_path)
        super().teardown_method(method)
