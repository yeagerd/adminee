from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from services.meetings.main import app
from services.meetings.models.base import Base
from services.meetings.tests.test_base import BaseMeetingsTest

client = TestClient(app)


class TestSecurityFixes(BaseMeetingsTest):
    """Test security fixes for slots and invitations routers."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)

        # Set up database tables using the engine from the base class
        from services.meetings import models

        # Ensure all tables exist with the latest schema
        engine = models.get_engine()
        Base.metadata.create_all(engine)

    @pytest.fixture
    def poll_payload(self):
        now = datetime.now(timezone.utc)
        return {
            "title": "Test Poll",
            "description": "A test poll.",
            "duration_minutes": 30,
            "location": "Test Room",
            "meeting_type": "virtual",
            "response_deadline": (now + timedelta(days=2)).isoformat(),
            "min_participants": 1,
            "max_participants": 5,
            "reveal_participants": False,
            "time_slots": [
                {
                    "start_time": (now + timedelta(days=3)).isoformat(),
                    "end_time": (now + timedelta(days=3, minutes=30)).isoformat(),
                    "timezone": "UTC",
                }
            ],
            "participants": [
                {"email": "alice@example.com", "name": "Alice"},
                {"email": "bob@example.com", "name": "Bob"},
            ],
        }

    def test_slots_add_authorized_user(self, poll_payload):
        """Test that poll owner can add time slots."""
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

        # Add time slot
        slot_payload = {
            "start_time": (datetime.now(timezone.utc) + timedelta(days=4)).isoformat(),
            "end_time": (
                datetime.now(timezone.utc) + timedelta(days=4, minutes=30)
            ).isoformat(),
            "timezone": "UTC",
        }
        resp = client.post(
            f"/api/v1/meetings/polls/{poll_id}/slots/",
            json=slot_payload,
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text

    def test_slots_add_unauthorized_user(self, poll_payload):
        """Test that non-owner cannot add time slots."""
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

        # Try to add time slot with user 2
        slot_payload = {
            "start_time": (datetime.now(timezone.utc) + timedelta(days=4)).isoformat(),
            "end_time": (
                datetime.now(timezone.utc) + timedelta(days=4, minutes=30)
            ).isoformat(),
            "timezone": "UTC",
        }
        resp = client.post(
            f"/api/v1/meetings/polls/{poll_id}/slots/",
            json=slot_payload,
            headers={"X-User-Id": user_id_2, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 403, resp.text
        assert "Not authorized to modify this poll" in resp.text

    def test_slots_update_authorized_user(self, poll_payload):
        """Test that poll owner can update time slots."""
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
        slot_id = data["time_slots"][0]["id"]

        # Update time slot
        slot_payload = {
            "start_time": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
            "end_time": (
                datetime.now(timezone.utc) + timedelta(days=5, minutes=30)
            ).isoformat(),
            "timezone": "UTC",
        }
        resp = client.put(
            f"/api/v1/meetings/polls/{poll_id}/slots/{slot_id}",
            json=slot_payload,
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text

    def test_slots_update_unauthorized_user(self, poll_payload):
        """Test that non-owner cannot update time slots."""
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
        slot_id = data["time_slots"][0]["id"]

        # Try to update time slot with user 2
        slot_payload = {
            "start_time": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
            "end_time": (
                datetime.now(timezone.utc) + timedelta(days=5, minutes=30)
            ).isoformat(),
            "timezone": "UTC",
        }
        resp = client.put(
            f"/api/v1/meetings/polls/{poll_id}/slots/{slot_id}",
            json=slot_payload,
            headers={"X-User-Id": user_id_2, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 403, resp.text
        assert "Not authorized to modify this poll" in resp.text

    def test_slots_delete_authorized_user(self, poll_payload):
        """Test that poll owner can delete time slots."""
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
        slot_id = data["time_slots"][0]["id"]

        # Delete time slot
        resp = client.delete(
            f"/api/v1/meetings/polls/{poll_id}/slots/{slot_id}",
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text

    def test_slots_delete_unauthorized_user(self, poll_payload):
        """Test that non-owner cannot delete time slots."""
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
        slot_id = data["time_slots"][0]["id"]

        # Try to delete time slot with user 2
        resp = client.delete(
            f"/api/v1/meetings/polls/{poll_id}/slots/{slot_id}",
            headers={"X-User-Id": user_id_2, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 403, resp.text
        assert "Not authorized to modify this poll" in resp.text

    def test_invitations_authorized_user(self, poll_payload):
        """Test that poll owner can send invitations."""
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

        # Send invitations
        resp = client.post(
            f"/api/v1/meetings/polls/{poll_id}/send-invitations/",
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        # Should succeed (though email sending might fail in test environment)
        assert resp.status_code in [200, 400], resp.text

    def test_invitations_unauthorized_user(self, poll_payload):
        """Test that non-owner cannot send invitations."""
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

        # Try to send invitations with user 2
        resp = client.post(
            f"/api/v1/meetings/polls/{poll_id}/send-invitations/",
            headers={"X-User-Id": user_id_2, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 403, resp.text
        assert "Not authorized to send invitations for this poll" in resp.text

    def test_slots_missing_user_id(self, poll_payload):
        """Test that slots operations fail without user ID header."""
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

        # Try to add slot without user ID header
        slot_payload = {
            "start_time": (datetime.now(timezone.utc) + timedelta(days=4)).isoformat(),
            "end_time": (
                datetime.now(timezone.utc) + timedelta(days=4, minutes=30)
            ).isoformat(),
            "timezone": "UTC",
        }
        resp = client.post(
            f"/api/v1/meetings/polls/{poll_id}/slots/",
            json=slot_payload,
            headers={"X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 400, resp.text
        assert "Missing X-User-Id header" in resp.text

    def test_invitations_missing_user_id(self, poll_payload):
        """Test that invitations fail without user ID header."""
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

        # Try to send invitations without user ID header
        resp = client.post(
            f"/api/v1/meetings/polls/{poll_id}/send-invitations/",
            headers={"X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 400, resp.text
        assert "Missing X-User-Id header" in resp.text
