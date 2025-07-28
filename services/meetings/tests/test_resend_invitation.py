from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from services.meetings.tests.test_base import BaseMeetingsTest


@pytest.fixture
def mock_poll():
    return {
        "id": str(uuid4()),
        "user_id": "test-user-123",
        "title": "Test Meeting",
        "description": "Test meeting description",
        "duration_minutes": 60,
        "status": "active",
        "poll_token": "test-token-123",
    }


@pytest.fixture
def mock_participant():
    return {
        "id": str(uuid4()),
        "poll_id": str(uuid4()),
        "email": "test@example.com",
        "name": "Test User",
        "status": "pending",
        "reminder_sent_count": 0,
        "response_token": "participant-token-123",
    }


class TestResendInvitation(BaseMeetingsTest):
    """Test cases for the resend invitation endpoint."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)

    @patch("services.meetings.api.polls.email_integration.send_invitation_email")
    @patch("services.meetings.api.polls.get_session")
    def test_resend_invitation_success(
        self, mock_get_session, mock_send_email, mock_poll, mock_participant
    ):
        """Test successful resend of invitation email."""
        # Mock the database session
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock poll query
        mock_poll_obj = type("MockPoll", (), mock_poll)()
        # Add time_slots attribute to the mock poll
        mock_poll_obj.time_slots = []
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_poll_obj
        )

        # Mock participant query
        mock_participant_obj = type("MockParticipant", (), mock_participant)()
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            mock_poll_obj,  # First call for poll
            mock_participant_obj,  # Second call for participant
        ]

        # Mock email sending
        mock_send_email.return_value = {"ok": True}

        # Make the request
        response = self.client.post(
            f"/api/v1/meetings/polls/{mock_poll['id']}/participants/{mock_participant['id']}/resend-invitation",
            headers={
                "X-User-Id": mock_poll["user_id"],
                "X-API-Key": "test-frontend-meetings-key",
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["message"] == "Invitation resent successfully"
        assert data["participant_email"] == mock_participant["email"]
        assert data["reminder_count"] == 1

        # Verify email was sent
        mock_send_email.assert_called_once()

        # Verify participant was updated
        assert mock_participant_obj.reminder_sent_count == 1
        mock_session.commit.assert_called_once()

    @patch("services.meetings.api.polls.get_session")
    def test_resend_invitation_poll_not_found(self, mock_get_session):
        """Test resend invitation when poll doesn't exist."""
        # Mock empty poll query
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        # Use valid UUIDs for the test
        poll_id = str(uuid4())
        participant_id = str(uuid4())

        # Make the request
        response = self.client.post(
            f"/api/v1/meetings/polls/{poll_id}/participants/{participant_id}/resend-invitation",
            headers={
                "X-User-Id": "test-user",
                "X-API-Key": "test-frontend-meetings-key",
            },
        )

        # Verify response
        assert response.status_code == 404
        # Now that mocks are working properly, we should get the business logic response
        data = response.json()
        assert "Poll not found" in data.get("message", "")

    @patch("services.meetings.api.polls.get_session")
    def test_resend_invitation_unauthorized(self, mock_get_session, mock_poll):
        """Test resend invitation when user is not authorized."""
        # Mock poll query with different user
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_poll_obj = type("MockPoll", (), mock_poll)()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_poll_obj
        )

        # Use valid UUID for participant
        participant_id = str(uuid4())

        # Make the request with different user
        response = self.client.post(
            f"/api/v1/meetings/polls/{mock_poll['id']}/participants/{participant_id}/resend-invitation",
            headers={
                "X-User-Id": "different-user",
                "X-API-Key": "test-frontend-meetings-key",
            },
        )

        # Verify response
        assert response.status_code == 403
        # Now that mocks are working properly, we should get the business logic response
        data = response.json()
        assert "Not authorized to resend invitations for this poll" in data.get(
            "message", ""
        )

    @patch("services.meetings.api.polls.get_session")
    def test_resend_invitation_participant_not_found(
        self, mock_get_session, mock_poll, mock_participant
    ):
        """Test resend invitation when participant doesn't exist."""
        # Mock poll query
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_poll_obj = type("MockPoll", (), mock_poll)()
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            mock_poll_obj,  # First call for poll
            None,  # Second call for participant (not found)
        ]

        # Make the request
        response = self.client.post(
            f"/api/v1/meetings/polls/{mock_poll['id']}/participants/{mock_participant['id']}/resend-invitation",
            headers={
                "X-User-Id": mock_poll["user_id"],
                "X-API-Key": "test-frontend-meetings-key",
            },
        )

        # Verify response
        assert response.status_code == 404
        # Now that mocks are working properly, we should get the business logic response
        data = response.json()
        assert "Participant not found" in data.get("message", "")

    @patch("services.meetings.api.polls.email_integration.send_invitation_email")
    @patch("services.meetings.api.polls.get_session")
    def test_resend_invitation_email_failure(
        self, mock_get_session, mock_send_email, mock_poll, mock_participant
    ):
        """Test resend invitation when email sending fails."""
        # Mock the database session
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock poll query
        mock_poll_obj = type("MockPoll", (), mock_poll)()
        mock_poll_obj.time_slots = []
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            mock_poll_obj,  # First call for poll
            type(
                "MockParticipant", (), mock_participant
            )(),  # Second call for participant
        ]

        # Mock email sending failure - the endpoint catches ValueError and raises HTTPException
        mock_send_email.side_effect = ValueError("Email service unavailable")

        # Make the request - should return HTTP 400 response, not raise exception
        response = self.client.post(
            f"/api/v1/meetings/polls/{mock_poll['id']}/participants/{mock_participant['id']}/resend-invitation",
            headers={
                "X-User-Id": mock_poll["user_id"],
                "X-API-Key": "test-frontend-meetings-key",
            },
        )

        # Verify response indicates failure
        assert response.status_code == 400
        data = response.json()
        # The error message is in the message field
        assert "Failed to resend invitation" in data["message"]
        assert "Email service unavailable" in data["message"]

        # Verify email service was called
        mock_send_email.assert_called_once()

    def test_resend_invitation_missing_api_key(self, mock_poll, mock_participant):
        """Test resend invitation without API key."""
        response = self.client.post(
            f"/api/v1/meetings/polls/{mock_poll['id']}/participants/{mock_participant['id']}/resend-invitation",
            headers={"X-User-Id": mock_poll["user_id"]},
        )

        assert response.status_code == 401
        # Check for the actual error message in the response
        assert "Invalid or missing API key" in response.text

    def test_resend_invitation_missing_user_id(self):
        """Test resend invitation without user ID."""
        # Use valid UUIDs for the test
        poll_id = str(uuid4())
        participant_id = str(uuid4())

        response = self.client.post(
            f"/api/v1/meetings/polls/{poll_id}/participants/{participant_id}/resend-invitation",
            headers={"X-API-Key": "test-frontend-meetings-key"},
        )

        assert response.status_code == 400
        assert "Missing X-User-Id header" in response.text
