from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from services.meetings.main import app
from services.meetings.models.base import Base
from services.meetings.tests.test_base import BaseMeetingsTest

client = TestClient(app)


class TestPollCreation(BaseMeetingsTest):
    """Test poll creation functionality."""

    def setup_method(self):
        """Set up test environment."""
        super().setup_method()

        # Set up database tables
        from sqlalchemy import create_engine

        from services.meetings import models

        if not hasattr(models, "_test_engine"):
            models._test_engine = create_engine(
                "sqlite:///file::memory:?cache=shared",
                echo=False,
                future=True,
                connect_args={"check_same_thread": False},
            )
        models.get_engine = lambda: models._test_engine
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

    def test_create_poll_sets_user_id(self, poll_payload):
        user_id = str(uuid4())
        resp = client.post(
            "/api/v1/meetings/polls/", json=poll_payload, headers={"X-User-Id": user_id}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["user_id"] == user_id
        assert data["title"] == poll_payload["title"]
        assert data["participants"][0]["email"] == "alice@example.com"

    def test_create_poll_missing_user_id_returns_400(self, poll_payload):
        resp = client.post("/api/v1/meetings/polls/", json=poll_payload)
        assert resp.status_code == 400
        assert "Missing X-User-Id header" in resp.text

    def test_token_based_poll_response_flow(self, poll_payload):
        user_id = str(uuid4())
        # Create poll
        resp = client.post(
            "/api/v1/meetings/polls/", json=poll_payload, headers={"X-User-Id": user_id}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # Get a participant's response_token
        participant = data["participants"][0]
        response_token = participant["response_token"]
        # Submit a response via the new endpoint
        response_payload = {
            "responses": [
                {
                    "time_slot_id": data["time_slots"][0]["id"],
                    "response": "available",
                    "comment": "Works for me!",
                }
            ]
        }
        resp2 = client.put(
            f"/api/v1/public/polls/response/{response_token}",
            json=response_payload,
        )
        assert resp2.status_code == 200, resp2.text
        assert resp2.json()["ok"] is True
