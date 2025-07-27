from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from services.meetings.main import app
from services.meetings.models import MeetingPoll, PollParticipant, get_session
from services.meetings.models.base import Base
from services.meetings.models.meeting import ParticipantStatus, ResponseType
from services.meetings.tests.test_base import BaseMeetingsTest

client = TestClient(app)

API_KEY = "test-email-sync-key"


class TestEmailResponse(BaseMeetingsTest):
    """Test email response functionality."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)

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


def create_poll_and_participant():
    now = datetime.utcnow()
    poll_id = uuid4()
    slot_id = uuid4()
    poll_token = uuid4().hex
    with get_session() as session:
        poll = MeetingPoll(
            id=poll_id,
            user_id="user-1",
            title="Email Poll",
            description="Test poll for email response",
            duration_minutes=30,
            location="Test Room",
            meeting_type="virtual",
            status="active",
            response_deadline=now + timedelta(days=2),
            poll_token=poll_token,
        )
        session.add(poll)
        # Add a time slot
        from services.meetings.models.meeting import TimeSlot

        slot = TimeSlot(
            id=slot_id,
            poll_id=poll_id,
            start_time=now + timedelta(days=3),
            end_time=now + timedelta(days=3, minutes=30),
            timezone="UTC",
        )
        session.add(slot)
        # Add a participant
        participant = PollParticipant(
            id=uuid4(),
            poll_id=poll_id,
            email="alice@example.com",
            name="Alice",
            status="pending",
            response_token=uuid4().hex,
        )
        session.add(participant)
        session.commit()
        return poll, slot, participant

    def test_process_email_response_success(self):
        poll, slot, participant = create_poll_and_participant()
        payload = {
            "emailId": "irrelevant",
            "content": "RESPONSE: available Looking forward to it!",
            "sender": "alice@example.com",
        }
        resp = client.post(
            "/api/v1/meetings/process-email-response/",
            json=payload,
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 200, resp.text
        assert resp.content == b""  # Empty response body
        # Check DB updated
        with get_session() as session:
            updated = (
                session.query(PollParticipant)
                .filter_by(email="alice@example.com")
                .first()
            )
            assert updated is not None
            assert updated.status == ParticipantStatus.responded
            # Re-query the slot to ensure it is attached to the session
            from services.meetings.models.meeting import TimeSlot

            slot_db = (
                session.query(TimeSlot)
                .filter_by(poll_id=updated.poll_id, timezone="UTC")
                .first()
            )
            responses = list(slot_db.responses)  # type: ignore[reportGeneralTypeIssues]
            assert len(responses) > 0
            assert any(r.response == ResponseType.available for r in responses)

    def test_process_email_response_invalid_key(self):
        poll, slot, participant = create_poll_and_participant()
        payload = {
            "emailId": "irrelevant",
            "content": "RESPONSE: available",
            "sender": "alice@example.com",
        }
        resp = client.post(
            "/api/v1/meetings/process-email-response/",
            json=payload,
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_process_email_response_unparseable_content(self):
        poll, slot, participant = create_poll_and_participant()
        payload = {
            "emailId": "irrelevant",
            "content": "I am not following the format",
            "sender": "alice@example.com",
        }
        resp = client.post(
            "/api/v1/meetings/process-email-response/",
            json=payload,
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 400
        assert "Could not parse response" in resp.text

    def test_process_email_response_unknown_sender(self):
        poll, slot, participant = create_poll_and_participant()
        payload = {
            "emailId": "irrelevant",
            "content": "RESPONSE: available",
            "sender": "unknown@example.com",
        }
        resp = client.post(
            "/api/v1/meetings/process-email-response/",
            json=payload,
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 404
        assert "Participant not found" in resp.text
