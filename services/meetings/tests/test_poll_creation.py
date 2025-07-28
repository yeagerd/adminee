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

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)

        # Import meetings settings module
        import services.meetings.settings as meetings_settings

        # Store original settings singleton for cleanup
        self._original_settings = meetings_settings._settings

        # Create test settings instance that doesn't load from .env file
        from services.meetings.settings import Settings

        test_settings = Settings(
            db_url_meetings="sqlite:///file::memory:?cache=shared",
            api_email_sync_meetings_key="test-email-sync-key",
            api_meetings_office_key="test-meetings-office-key",
            api_meetings_user_key="test-meetings-user-key",
            api_frontend_meetings_key="test-frontend-meetings-key",
            office_service_url="http://localhost:8003",
            user_service_url="http://localhost:8001",
            log_level="INFO",
            log_format="json",
        )

        # Set the test settings as the singleton
        meetings_settings._settings = test_settings

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

    def teardown_method(self, method):
        """Clean up test environment."""
        # Restore original settings singleton
        import services.meetings.settings as meetings_settings

        meetings_settings._settings = self._original_settings

        # Call parent teardown
        super().teardown_method(method)

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

    def test_create_poll_with_reveal_participants(self, poll_payload):
        user_id = str(uuid4())
        # Set reveal_participants to True
        poll_payload["reveal_participants"] = True

        resp = client.post(
            "/api/v1/meetings/polls/",
            json=poll_payload,
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["user_id"] == user_id
        assert data["title"] == poll_payload["title"]
        assert data["reveal_participants"] is True
        assert data["participants"][0]["email"] == "alice@example.com"

    def test_create_poll_without_reveal_participants(self, poll_payload):
        user_id = str(uuid4())
        # Set reveal_participants to False
        poll_payload["reveal_participants"] = False

        resp = client.post(
            "/api/v1/meetings/polls/",
            json=poll_payload,
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["user_id"] == user_id
        assert data["title"] == poll_payload["title"]
        assert data["reveal_participants"] is False
        assert data["participants"][0]["email"] == "alice@example.com"

    def test_public_poll_endpoint_filters_current_participant(self, poll_payload):
        """Test that the public poll endpoint filters out the current participant from the participants list."""
        user_id = str(uuid4())
        # Set reveal_participants to True so participants are included
        poll_payload["reveal_participants"] = True

        # Create poll
        resp = client.post(
            "/api/v1/meetings/polls/",
            json=poll_payload,
            headers={"X-User-Id": user_id, "X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Verify we have multiple participants
        assert len(data["participants"]) == 2
        alice_participant = data["participants"][0]
        bob_participant = data["participants"][1]

        # Test with Alice's response token
        alice_response_token = alice_participant["response_token"]
        resp2 = client.get(f"/api/v1/public/polls/response/{alice_response_token}")
        assert resp2.status_code == 200, resp2.text
        public_data = resp2.json()

        # Verify the poll data is returned
        assert "poll" in public_data
        assert "participant" in public_data
        assert public_data["participant"]["id"] == alice_participant["id"]

        # Verify that Alice (current participant) is NOT in the participants list
        poll_participants = public_data["poll"]["participants"]
        assert len(poll_participants) == 1  # Should only have Bob
        assert poll_participants[0]["id"] == bob_participant["id"]
        assert poll_participants[0]["email"] == "bob@example.com"

        # Verify Alice is not in the list
        alice_ids = [p["id"] for p in poll_participants]
        assert alice_participant["id"] not in alice_ids

        # Test with Bob's response token
        bob_response_token = bob_participant["response_token"]
        resp3 = client.get(f"/api/v1/public/polls/response/{bob_response_token}")
        assert resp3.status_code == 200, resp3.text
        public_data_bob = resp3.json()

        # Verify that Bob (current participant) is NOT in the participants list
        poll_participants_bob = public_data_bob["poll"]["participants"]
        assert len(poll_participants_bob) == 1  # Should only have Alice
        assert poll_participants_bob[0]["id"] == alice_participant["id"]
        assert poll_participants_bob[0]["email"] == "alice@example.com"

        # Verify Bob is not in the list
        bob_ids = [p["id"] for p in poll_participants_bob]
        assert bob_participant["id"] not in bob_ids
