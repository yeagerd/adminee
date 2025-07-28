"""
Base classes for Meetings Service tests.

Provides common setup and teardown for all meetings service tests,
including required environment variables and database setup.
"""

import importlib
import os
import tempfile
from contextlib import contextmanager

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
        )
        self._original_settings = getattr(meetings_settings, "_settings", None)
        meetings_settings._settings = test_settings

        # Force reload models and main after patching settings
        import services.meetings.models

        importlib.reload(services.meetings.models)
        import services.meetings.models.base

        importlib.reload(services.meetings.models.base)
        import services.meetings.models.meeting

        importlib.reload(services.meetings.models.meeting)
        import services.meetings.main

        importlib.reload(services.meetings.main)

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

        from fastapi.testclient import TestClient

        from services.meetings.main import app

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
