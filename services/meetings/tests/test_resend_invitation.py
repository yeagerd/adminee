from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from services.meetings.main import app


@pytest.fixture
def client():
    return TestClient(app)


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


class TestResendInvitation:
    """Test cases for the resend invitation endpoint."""

    @patch("services.meetings.api.polls.email_integration.send_invitation_email")
    @patch("services.meetings.api.polls.get_session")
    def test_resend_invitation_success(
        self, mock_get_session, mock_send_email, client, mock_poll, mock_participant
    ):
        """Test successful resend of invitation email."""
        # Mock the database session
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock poll query
        mock_poll_obj = type("MockPoll", (), mock_poll)()
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
        response = client.post(
            f"/api/v1/meetings/polls/{mock_poll['id']}/participants/{mock_participant['id']}/resend-invitation",
            headers={"X-User-Id": mock_poll["user_id"]},
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
    def test_resend_invitation_poll_not_found(self, mock_get_session, client):
        """Test resend invitation when poll doesn't exist."""
        # Mock empty poll query
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        response = client.post(
            f"/api/v1/meetings/polls/{uuid4()}/participants/{uuid4()}/resend-invitation",
            headers={"X-User-Id": "test-user"},
        )

        assert response.status_code == 404
        assert "Poll not found" in response.json()["message"]

    @patch("services.meetings.api.polls.get_session")
    def test_resend_invitation_unauthorized(self, mock_get_session, client, mock_poll):
        """Test resend invitation when user doesn't own the poll."""
        # Mock poll query with different user
        mock_poll_obj = type("MockPoll", (), mock_poll)()
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_poll_obj
        )

        response = client.post(
            f"/api/v1/meetings/polls/{mock_poll['id']}/participants/{uuid4()}/resend-invitation",
            headers={"X-User-Id": "different-user"},
        )

        assert response.status_code == 403
        assert "Not authorized" in response.json()["message"]

    @patch("services.meetings.api.polls.get_session")
    def test_resend_invitation_participant_not_found(
        self, mock_get_session, client, mock_poll, mock_participant
    ):
        """Test resend invitation when participant doesn't exist."""
        # Mock poll query
        mock_poll_obj = type("MockPoll", (), mock_poll)()
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            mock_poll_obj,  # First call for poll
            None,  # Second call for participant (not found)
        ]

        response = client.post(
            f"/api/v1/meetings/polls/{mock_poll['id']}/participants/{mock_participant['id']}/resend-invitation",
            headers={"X-User-Id": mock_poll["user_id"]},
        )

        assert response.status_code == 404
        assert "Participant not found" in response.json()["message"]

    @patch("services.meetings.api.polls.email_integration.send_invitation_email")
    @patch("services.meetings.api.polls.get_session")
    def test_resend_invitation_email_failure(
        self, mock_get_session, mock_send_email, client, mock_poll, mock_participant
    ):
        """Test resend invitation when email sending fails."""
        # Mock the database session
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock poll query
        mock_poll_obj = type("MockPoll", (), mock_poll)()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_poll_obj
        )

        # Mock participant query
        mock_participant_obj = type("MockParticipant", (), mock_participant)()
        mock_session.query.return_value.filter_by.return_value.first.side_effect = [
            mock_poll_obj,  # First call for poll
            mock_participant_obj,  # Second call for participant
        ]

        # Mock email sending failure
        mock_send_email.side_effect = ValueError("Email service unavailable")

        response = client.post(
            f"/api/v1/meetings/polls/{mock_poll['id']}/participants/{mock_participant['id']}/resend-invitation",
            headers={"X-User-Id": mock_poll["user_id"]},
        )

        assert response.status_code == 400
        assert "Failed to resend invitation" in response.json()["message"]

    def test_resend_invitation_missing_user_id(self, client):
        """Test resend invitation without user ID header."""
        response = client.post(
            f"/api/v1/meetings/polls/{uuid4()}/participants/{uuid4()}/resend-invitation",
        )

        assert response.status_code == 400
        assert "Missing X-User-Id header" in response.json()["message"]
