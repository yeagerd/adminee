from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest

from services.meetings.tests.meetings_test_base import BaseMeetingsTest


class TestPollCreation(BaseMeetingsTest):
    """Test poll creation functionality."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)

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

    def test_create_poll_sets_user_id(self, poll_payload):
        user_id = str(uuid4())
        resp = self.client.post(
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
        resp = self.client.post(
            "/api/v1/meetings/polls/",
            json=poll_payload,
            headers={"X-API-Key": "test-frontend-meetings-key"},
        )
        assert resp.status_code == 400
        assert "Missing X-User-Id header" in resp.text

    def test_token_based_poll_response_flow(self, poll_payload):
        user_id = str(uuid4())
        # Create poll
        resp = self.client.post(
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
        resp2 = self.client.put(
            f"/api/v1/public/polls/response/{response_token}",
            json=response_payload,
        )
        assert resp2.status_code == 200, resp2.text
        assert resp2.json()["ok"] is True

    def test_get_poll_includes_responses(self, poll_payload):
        user_id = str(uuid4())
        # Create poll
        resp = self.client.post(
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
        resp2 = self.client.put(
            f"/api/v1/public/polls/response/{response_token}",
            json=response_payload,
        )
        assert resp2.status_code == 200, resp2.text

        # Get the poll and verify responses are included
        resp3 = self.client.get(
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

        resp = self.client.post(
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

        resp = self.client.post(
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

    @patch("services.meetings.api.polls.email_integration.send_invitation_email")
    def test_create_poll_with_send_emails_sends_invitations(self, mock_send_email):
        """Test that creating a poll with send_emails=True sends invitation emails."""
        # Mock email sending
        mock_send_email.return_value = {"ok": True}

        poll_data = {
            "title": "Test Poll with Emails",
            "description": "Test Description",
            "duration_minutes": 60,
            "location": "Test Location",
            "meeting_type": "tbd",
            "time_slots": [
                {
                    "start_time": "2024-01-01T10:00:00Z",
                    "end_time": "2024-01-01T11:00:00Z",
                    "timezone": "UTC",
                }
            ],
            "participants": [
                {
                    "email": "test1@example.com",
                    "name": "Test User 1",
                },
                {
                    "email": "test2@example.com",
                    "name": "Test User 2",
                },
            ],
            "response_deadline": "2024-01-02T00:00:00Z",
            "reveal_participants": False,
            "send_emails": True,
        }

        # Create the poll
        response = self.client.post(
            "/api/v1/meetings/polls",
            json=poll_data,
            headers={
                "X-User-Id": "test-user-123",
                "X-API-Key": "test-frontend-meetings-key",
            },
        )

        assert response.status_code == 200
        poll = response.json()

        # Verify that emails were sent to both participants
        assert mock_send_email.call_count == 2

        # Check first participant email
        first_call = mock_send_email.call_args_list[0]
        assert first_call[0][0] == "test1@example.com"  # email
        assert "You're invited: Test Poll with Emails" in first_call[0][1]  # subject
        assert "Test Poll with Emails" in first_call[0][2]  # body contains poll title
        assert first_call[0][3] == "test-user-123"  # user_id

        # Check second participant email
        second_call = mock_send_email.call_args_list[1]
        assert second_call[0][0] == "test2@example.com"  # email
        assert "You're invited: Test Poll with Emails" in second_call[0][1]  # subject
        assert "Test Poll with Emails" in second_call[0][2]  # body contains poll title
        assert second_call[0][3] == "test-user-123"  # user_id

    @patch("services.meetings.api.polls.email_integration.send_invitation_email")
    def test_create_poll_without_send_emails_does_not_send_invitations(
        self, mock_send_email
    ):
        """Test that creating a poll with send_emails=False does not send invitation emails."""
        poll_data = {
            "title": "Test Poll without Emails",
            "description": "Test Description",
            "duration_minutes": 60,
            "location": "Test Location",
            "meeting_type": "tbd",
            "time_slots": [
                {
                    "start_time": "2024-01-01T10:00:00Z",
                    "end_time": "2024-01-01T11:00:00Z",
                    "timezone": "UTC",
                }
            ],
            "participants": [
                {
                    "email": "test@example.com",
                    "name": "Test User",
                }
            ],
            "response_deadline": "2024-01-02T00:00:00Z",
            "reveal_participants": False,
            "send_emails": False,
        }

        # Create the poll
        response = self.client.post(
            "/api/v1/meetings/polls",
            json=poll_data,
            headers={
                "X-User-Id": "test-user-123",
                "X-API-Key": "test-frontend-meetings-key",
            },
        )

        assert response.status_code == 200

        # Verify that no emails were sent
        mock_send_email.assert_not_called()

    @patch("services.meetings.api.polls.email_integration.send_invitation_email")
    def test_create_poll_email_sending_failure_does_not_fail_creation(
        self, mock_send_email
    ):
        """Test that poll creation succeeds even if email sending fails."""
        # Mock email sending to fail
        mock_send_email.side_effect = ValueError("Email service unavailable")

        poll_data = {
            "title": "Test Poll with Email Failure",
            "description": "Test Description",
            "duration_minutes": 60,
            "location": "Test Location",
            "meeting_type": "tbd",
            "time_slots": [
                {
                    "start_time": "2024-01-01T10:00:00Z",
                    "end_time": "2024-01-01T11:00:00Z",
                    "timezone": "UTC",
                }
            ],
            "participants": [
                {
                    "email": "test@example.com",
                    "name": "Test User",
                }
            ],
            "response_deadline": "2024-01-02T00:00:00Z",
            "reveal_participants": False,
            "send_emails": True,
        }

        # Create the poll - should succeed despite email failure
        response = self.client.post(
            "/api/v1/meetings/polls",
            json=poll_data,
            headers={
                "X-User-Id": "test-user-123",
                "X-API-Key": "test-frontend-meetings-key",
            },
        )

        assert response.status_code == 200
        poll = response.json()

        # Verify that the poll was created successfully
        assert poll["title"] == "Test Poll with Email Failure"
        assert len(poll["participants"]) == 1
        assert len(poll["time_slots"]) == 1
