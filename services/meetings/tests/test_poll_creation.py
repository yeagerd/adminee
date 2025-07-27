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
            "/api/v1/meetings/polls/",
            json=poll_payload,
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["user_id"] == user_id
        assert data["title"] == poll_payload["title"]
        assert data["participants"][0]["email"] == "alice@example.com"

    def test_create_poll_missing_user_id_returns_400(self, poll_payload):
        resp = client.post(
            "/api/v1/meetings/polls/",
            json=poll_payload,
            headers={"X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 400
        assert "Missing X-User-Id header" in resp.text

    def test_token_based_poll_response_flow(self, poll_payload):
        user_id = str(uuid4())
        # Create poll
        resp = client.post(
            "/api/v1/meetings/polls/",
            json=poll_payload,
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
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

    def test_get_poll_includes_responses(self, poll_payload):
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

        # Submit a response
        participant = data["participants"][0]
        response_token = participant["response_token"]
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

        # Get the poll and verify responses are included
        resp3 = client.get(
            f"/api/v1/meetings/polls/{poll_id}",
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp3.status_code == 200, resp3.text
        poll_data = resp3.json()

        # Verify responses field is present and contains the submitted response
        assert "responses" in poll_data
        assert len(poll_data["responses"]) == 1
        response = poll_data["responses"][0]
        assert response["time_slot_id"] == data["time_slots"][0]["id"]
        assert response["response"] == "available"
        assert response["comment"] == "Works for me!"
        assert "participant_id" in response
        assert "created_at" in response
        assert "updated_at" in response
