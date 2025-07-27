from datetime import datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from services.meetings.main import app
from services.meetings.models import (
    MeetingPoll,
    PollParticipant,
    PollResponse,
    TimeSlot,
    get_session,
)
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

        # Set up database tables using the same engine as the service
        from sqlalchemy import create_engine

        from services.meetings import models

        # Use the same database URL as configured in the test base
        db_url = f"sqlite:///{self.db_path}"

        # Create engine and override the get_engine function
        if not hasattr(models, "_test_engine"):
            models._test_engine = create_engine(
                db_url,
                echo=False,
                future=True,
                connect_args={"check_same_thread": False},
            )

        # Override the get_engine function to use our test engine
        models.get_engine = lambda: models._test_engine
        Base.metadata.create_all(models._test_engine)

    def teardown_method(self, method):
        """Clean up test environment."""
        # Clean up the engine before calling parent teardown
        from services.meetings import models

        if hasattr(models, "_test_engine"):
            models._test_engine.dispose()
            delattr(models, "_test_engine")

        # Call parent teardown to clean up the database file
        super().teardown_method(method)

    def create_poll_and_participant(self):
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
            # Return IDs as strings to avoid detached instance issues
            return (
                poll,
                slot,
                participant,
                str(slot.id),
                str(poll.id),
                str(participant.id),
            )

    def test_process_email_response_success(self):
        poll, slot, participant, slot_id, poll_id, participant_id = (
            self.create_poll_and_participant()
        )
        payload = {
            "emailId": "irrelevant",
            "content": "SLOT_1: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC) - available - Looking forward to it!",
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
        poll, slot, participant, slot_id, poll_id, participant_id = (
            self.create_poll_and_participant()
        )
        payload = {
            "emailId": "irrelevant",
            "content": "SLOT_1: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC) - available",
            "sender": "alice@example.com",
        }
        resp = client.post(
            "/api/v1/meetings/process-email-response/",
            json=payload,
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_process_email_response_unparseable_content(self):
        poll, slot, participant, slot_id, poll_id, participant_id = (
            self.create_poll_and_participant()
        )
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
        assert "Could not parse any slot responses" in resp.text

    def test_process_email_response_unknown_sender(self):
        poll, slot, participant, slot_id, poll_id, participant_id = (
            self.create_poll_and_participant()
        )
        payload = {
            "emailId": "irrelevant",
            "content": "SLOT_1: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC) - available",
            "sender": "unknown@example.com",
        }
        resp = client.post(
            "/api/v1/meetings/process-email-response/",
            json=payload,
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 404
        assert "Participant not found" in resp.text

    def test_process_email_response_multiple_slots(self):
        poll, slot, participant, slot_id, poll_id, participant_id = (
            self.create_poll_and_participant()
        )

        # Create a second time slot
        with get_session() as session:
            slot2 = TimeSlot(
                id=uuid4(),
                poll_id=UUID(poll_id),  # Convert string back to UUID
                start_time=datetime.utcnow() + timedelta(days=4),
                end_time=datetime.utcnow() + timedelta(days=4, minutes=30),
                timezone="UTC",
            )
            session.add(slot2)
            session.commit()
            slot2_id = str(slot2.id)  # Get the ID as string before session closes

        payload = {
            "emailId": "irrelevant",
            "content": "SLOT_1: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC) - available - I prefer this time\nSLOT_2: Tuesday, January 16, 2024 at 10:00 AM - 11:00 AM (UTC) - unavailable - I have a conflict",
            "sender": "alice@example.com",
        }
        resp = client.post(
            "/api/v1/meetings/process-email-response/",
            json=payload,
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 200, resp.text

        # Check DB updated
        with get_session() as session:
            updated = (
                session.query(PollParticipant)
                .filter_by(email="alice@example.com")
                .first()
            )
            assert updated is not None
            assert updated.status == ParticipantStatus.responded

            # Check responses for both slots
            slot1_responses = (
                session.query(PollResponse)
                .filter_by(
                    participant_id=UUID(participant_id), time_slot_id=UUID(slot_id)
                )
                .all()
            )
            slot2_responses = (
                session.query(PollResponse)
                .filter_by(
                    participant_id=UUID(participant_id), time_slot_id=UUID(slot2_id)
                )
                .all()
            )

            assert len(slot1_responses) == 1
            assert len(slot2_responses) == 1
            assert slot1_responses[0].response == ResponseType.available
            assert slot2_responses[0].response == ResponseType.unavailable
            assert "I prefer this time" in slot1_responses[0].comment
            assert "I have a conflict" in slot2_responses[0].comment

    def test_process_email_response_malformed_slot_identifier(self):
        """Test that malformed slot identifiers don't cause errors."""
        poll, slot, participant, slot_id, poll_id, participant_id = (
            self.create_poll_and_participant()
        )

        # Test with malformed slot identifiers that should be skipped
        payload = {
            "emailId": "irrelevant",
            "content": "SLOT_: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC) - available\nSLOT_abc: Tuesday, January 16, 2024 at 10:00 AM - 11:00 AM (UTC) - unavailable\nSLOT_0: Wednesday, January 17, 2024 at 3:00 PM - 4:00 PM (UTC) - maybe",
            "sender": "alice@example.com",
        }
        resp = client.post(
            "/api/v1/meetings/process-email-response/",
            json=payload,
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 400
        assert "Could not parse any slot responses" in resp.text

    def test_process_email_response_keyword_position_mismatch(self):
        """Test that comment extraction works correctly with keyword position matching."""
        poll, slot, participant, slot_id, poll_id, participant_id = (
            self.create_poll_and_participant()
        )

        # Test cases that would cause keyword position mismatch
        test_cases = [
            # Case 1: "available" appears in "unavailable" - should extract comment correctly
            "SLOT_1: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC) - available - I prefer this time",
            # Case 2: Multiple occurrences of keyword - should use the first word boundary match
            "SLOT_1: Tuesday, January 16, 2024 at 10:00 AM - 11:00 AM (UTC) - maybe - I'm available for this time",
            # Case 3: Keyword with punctuation - should handle correctly
            "SLOT_1: Wednesday, January 17, 2024 at 3:00 PM - 4:00 PM (UTC) - unavailable! - I have a conflict",
        ]

        for i, content in enumerate(test_cases):
            payload = {
                "emailId": "irrelevant",
                "content": content,
                "sender": "alice@example.com",
            }
            resp = client.post(
                "/api/v1/meetings/process-email-response/",
                json=payload,
                headers={"X-API-Key": API_KEY},
            )
            assert resp.status_code == 200, f"Test case {i+1} failed: {resp.text}"

            # Check that the response was saved correctly
            with get_session() as session:
                response = (
                    session.query(PollResponse)
                    .filter_by(
                        participant_id=UUID(participant_id), time_slot_id=UUID(slot_id)
                    )
                    .first()
                )
                assert response is not None, f"Test case {i+1}: No response found"

                # Verify the comment was extracted correctly
                if i == 0:
                    assert (
                        "I prefer this time" in response.comment
                    ), f"Test case {i+1}: Comment not extracted correctly"
                elif i == 1:
                    assert (
                        "I'm available for this time" in response.comment
                    ), f"Test case {i+1}: Comment not extracted correctly"
                elif i == 2:
                    assert (
                        "I have a conflict" in response.comment
                    ), f"Test case {i+1}: Comment not extracted correctly"

    def test_process_email_response_invalid_slot_number_handling(self):
        """Test that invalid slot numbers in slot responses are handled gracefully."""
        poll, slot, participant, slot_id, poll_id, participant_id = (
            self.create_poll_and_participant()
        )

        # Test with a valid slot response and an invalid slot number response
        payload = {
            "emailId": "irrelevant",
            "content": "SLOT_1: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC) - available - Valid response\nSLOT_99: Tuesday, January 16, 2024 at 10:00 AM - 11:00 AM (UTC) - unavailable - Invalid slot number response",
            "sender": "alice@example.com",
        }
        resp = client.post(
            "/api/v1/meetings/process-email-response/",
            json=payload,
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 200, resp.text

        # Check that only the valid response was processed
        with get_session() as session:
            response = (
                session.query(PollResponse)
                .filter_by(
                    participant_id=UUID(participant_id), time_slot_id=UUID(slot_id)
                )
                .first()
            )
            assert response is not None, "Valid response should be processed"
            assert response.response == ResponseType.available
            assert "Valid response" in response.comment

            # Verify participant status was updated
            updated_participant = (
                session.query(PollParticipant)
                .filter_by(email="alice@example.com")
                .first()
            )
            assert updated_participant.status == ParticipantStatus.responded
