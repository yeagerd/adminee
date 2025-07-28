from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from services.meetings.main import app
from services.meetings.models.base import Base
from services.meetings.tests.test_base import BaseMeetingsTest

client = TestClient(app)


class TestPollAuthorization(BaseMeetingsTest):
    """Test poll authorization functionality."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)

        # Set up database tables
        from sqlalchemy import create_engine

        from services.meetings import models

        # Clear any existing test engine to ensure fresh tables
        if hasattr(models, "_test_engine"):
            delattr(models, "_test_engine")

        models._test_engine = create_engine(
            "sqlite:///file::memory:?cache=shared",
            echo=False,
            future=True,
            connect_args={"check_same_thread": False},
        )
        models.get_engine = lambda: models._test_engine

        # Drop all tables and recreate them to ensure latest schema
        Base.metadata.drop_all(models._test_engine)
        Base.metadata.create_all(models._test_engine)

    @pytest.fixture
    def poll_payload(self):
        now = datetime.utcnow()
        return {
            "title": "Test Poll",
            "description": "A test poll.",
            "duration_minutes": 30,
            "location": "Test Room",
            "meeting_type": "virtual",
            "response_deadline": (now + timedelta(days=2)).isoformat() + "Z",
            "min_participants": 1,
            "max_participants": 5,
            "reveal_participants": False,
            "time_slots": [
                {
                    "start_time": (now + timedelta(days=3)).isoformat() + "Z",
                    "end_time": (now + timedelta(days=3, minutes=30)).isoformat() + "Z",
                    "timezone": "UTC",
                }
            ],
            "participants": [
                {"email": "alice@example.com", "name": "Alice"},
                {"email": "bob@example.com", "name": "Bob"},
            ],
        }

    def test_delete_poll_authorized_user(self, poll_payload):
        """Test that poll creator can delete their own poll."""
        user_id = str(uuid4())

        # Create poll
        resp = client.post(
            "/api/v1/meetings/polls/",
            json=poll_payload,
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        poll_id = data["id"]

        # Delete poll with same user
        resp = client.delete(
            f"/api/v1/meetings/polls/{poll_id}",
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"ok": True}

    def test_delete_poll_unauthorized_user(self, poll_payload):
        """Test that non-owner cannot delete poll."""
        user_id_1 = str(uuid4())
        user_id_2 = str(uuid4())

        # Create poll with user 1
        resp = client.post(
            "/api/v1/meetings/polls/",
            json=poll_payload,
            headers={"X-User-Id": user_id_1, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        poll_id = data["id"]

        # Try to delete poll with user 2
        resp = client.delete(
            f"/api/v1/meetings/polls/{poll_id}",
            headers={"X-User-Id": user_id_2, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 403, resp.text
        assert "Not authorized to delete this poll" in resp.text

    def test_update_poll_authorized_user(self, poll_payload):
        """Test that poll creator can update their own poll."""
        user_id = str(uuid4())

        # Create poll
        resp = client.post(
            "/api/v1/meetings/polls/",
            json=poll_payload,
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        poll_id = data["id"]

        # Update poll with same user
        update_payload = {"title": "Updated Title"}
        resp = client.put(
            f"/api/v1/meetings/polls/{poll_id}",
            json=update_payload,
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text
        updated_data = resp.json()
        assert updated_data["title"] == "Updated Title"

    def test_update_poll_unauthorized_user(self, poll_payload):
        """Test that non-owner cannot update poll."""
        user_id_1 = str(uuid4())
        user_id_2 = str(uuid4())

        # Create poll with user 1
        resp = client.post(
            "/api/v1/meetings/polls/",
            json=poll_payload,
            headers={"X-User-Id": user_id_1, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        poll_id = data["id"]

        # Try to update poll with user 2
        update_payload = {"title": "Updated Title"}
        resp = client.put(
            f"/api/v1/meetings/polls/{poll_id}",
            json=update_payload,
            headers={"X-User-Id": user_id_2, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 403, resp.text
        assert "Not authorized to update this poll" in resp.text

    def test_delete_poll_missing_user_id(self, poll_payload):
        """Test that delete fails without user ID header."""
        user_id = str(uuid4())

        # Create poll
        resp = client.post(
            "/api/v1/meetings/polls/",
            json=poll_payload,
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        poll_id = data["id"]

        # Try to delete poll without user ID header
        resp = client.delete(
            f"/api/v1/meetings/polls/{poll_id}",
            headers={"X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 400, resp.text
        assert "Missing X-User-Id header" in resp.text

    def test_delete_nonexistent_poll(self):
        """Test that delete fails for nonexistent poll."""
        user_id = str(uuid4())
        fake_poll_id = str(uuid4())

        resp = client.delete(
            f"/api/v1/meetings/polls/{fake_poll_id}",
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 404, resp.text
        assert "Poll not found" in resp.text

    def test_user_id_format_edge_cases(self, poll_payload):
        """Test various user ID formats to ensure they work correctly."""
        # Test with a user ID that looks like the one from the logs
        user_id = "AAAAAAAAAAAAAAAAAAAAAG_WiRzTkk4vuAr97CA2Dc4"

        # Create poll
        resp = client.post(
            "/api/v1/meetings/polls/",
            json=poll_payload,
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        poll_id = data["id"]

        # Verify the user_id was stored correctly
        assert data["user_id"] == user_id

        # Delete poll with same user ID
        resp = client.delete(
            f"/api/v1/meetings/polls/{poll_id}",
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"ok": True}

    def test_user_id_with_underscores(self, poll_payload):
        """Test user ID with underscores (like the one in the logs)."""
        user_id = "AAAAAAAAAAAAAAAAAAAAAG_WiRzTkk4vuAr97CA2Dc4"

        # Create poll
        resp = client.post(
            "/api/v1/meetings/polls/",
            json=poll_payload,
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        poll_id = data["id"]

        # Try to delete with a slightly different user ID
        different_user_id = "AAAAAAAAAAAAAAAAAAAAAG_WiRzTkk4vuAr97CA2Dc5"
        resp = client.delete(
            f"/api/v1/meetings/polls/{poll_id}",
            headers={
                "X-User-Id": different_user_id,
                "X-API-Key": "test-frontend-meetings-key",
            },
        )
        assert resp.status_code == 403, resp.text
        assert "Not authorized to delete this poll" in resp.text
