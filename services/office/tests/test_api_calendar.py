"""
Tests for the calendar API endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from services.office.app.main import app
from services.office.models import Provider
from services.office.schemas import CalendarEvent


@pytest.fixture(autouse=True)
def patch_settings():
    """Patch the _settings global variable to return test settings."""
    import services.office.core.settings as office_settings

    test_settings = office_settings.Settings(
        db_url_office="sqlite:///:memory:",
        api_frontend_office_key="test-frontend-office-key",
        api_chat_office_key="test-chat-office-key",
        api_meetings_office_key="test-meetings-office-key",
        api_backfill_office_key="test-backfill-office-key",
        api_office_user_key="test-office-user-key",
        pagination_secret_key="test-pagination-secret-key",
    )

    # Directly set the singleton instead of using monkeypatch
    office_settings._settings = test_settings
    yield
    office_settings._settings = None


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authentication headers with X-User-Id and API key."""
    return {"X-User-Id": "test_user", "X-API-Key": "test-frontend-office-key"}


@pytest.fixture
def mock_calendar_event():
    """Create a mock calendar event."""
    return CalendarEvent(
        id="google_test123",
        calendar_id="primary",
        title="Test Event",
        description="Test calendar event",
        start_time="2024-01-15T10:00:00Z",
        end_time="2024-01-15T11:00:00Z",
        all_day=False,
        location="Test Location",
        attendees=[],
        organizer=None,
        status="confirmed",
        visibility="default",
        provider=Provider.GOOGLE,
        provider_event_id="test123",
        account_email="user@gmail.com",
        account_name="Test Account",
        calendar_name="Primary Calendar",
        created_at="2024-01-15T09:00:00Z",
        updated_at="2024-01-15T09:00:00Z",
    )


@pytest.fixture
def mock_cache_manager():
    """Mock the cache manager."""
    with patch("services.office.api.calendar.cache_manager") as mock:
        mock.get_from_cache = AsyncMock(return_value=None)
        mock.set_to_cache = AsyncMock()
        yield mock


@pytest.fixture
def mock_api_client_factory():
    """Mock the API client factory."""
    with patch("services.office.api.calendar.get_api_client_factory") as mock:
        # Create a mock factory
        mock_factory = MagicMock()
        mock_factory.get_user_preferred_provider = AsyncMock(return_value=None)
        mock_factory.create_client = AsyncMock(return_value=None)
        # Make the mock return the factory directly when awaited
        mock.return_value = mock_factory
        # Also make the mock itself awaitable
        mock.__await__ = lambda: iter([mock_factory])
        yield mock


class TestCalendarEventsEndpoint:
    """Tests for the GET /calendar/events endpoint."""

    @patch("services.office.api.calendar.fetch_provider_events")
    @pytest.mark.asyncio
    async def test_get_calendar_events_no_cache_bypass(
        self,
        mock_fetch_provider_events,
        mock_cache_manager,
        mock_api_client_factory,
        mock_calendar_event,
        client,
        auth_headers,
    ):
        """Test that no_cache parameter bypasses cache."""
        # Mock fetch_provider_events to return test data for both providers
        mock_fetch_provider_events.side_effect = [
            ([mock_calendar_event], "google"),
            ([mock_calendar_event], "microsoft"),
        ]

        # Mock cache to return None (cache miss)
        mock_cache_manager.get_from_cache.return_value = None

        response = client.get(
            "/v1/calendar/events?limit=10&no_cache=true", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["cache_hit"] is False
        assert len(data["data"]) == 2  # One from each provider
        assert data["data"][0]["provider"] in ["google", "microsoft"]
        assert data["data"][1]["provider"] in ["google", "microsoft"]

        # Verify that fetch_provider_events was called twice (once for each provider)
        assert mock_fetch_provider_events.call_count == 2
