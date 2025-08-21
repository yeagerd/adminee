from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from services.meetings.models.meeting import ParticipantStatus, ResponseType
from services.meetings.tests.meetings_test_base import BaseMeetingsTest

API_KEY = "test-email-sync-key"


class TestEmailResponse(BaseMeetingsTest):
    """Test email response functionality."""

    def setup_method(self, method):
        """Set up each test method with clean database."""
        super().setup_method(method)
        # Clear any existing data
        self._clear_test_data()

    def teardown_method(self, method):
        """Clean up after each test method."""
        self._clear_test_data()
        super().teardown_method(method)

    def _clear_test_data(self):
        """Clear all test data from the database."""
        from services.meetings.models import (
            MeetingPoll,
            PollParticipant,
            PollResponse,
            TimeSlot,
            get_session,
        )

        try:
            with get_session() as session:
                # Delete in reverse order to avoid foreign key constraints
                session.query(PollResponse).delete()
                session.query(PollParticipant).delete()
                session.query(TimeSlot).delete()
                session.query(MeetingPoll).delete()
                session.commit()
        except Exception as e:
            # If there's an error clearing data, log it but don't fail the test
            # This can happen if the database is readonly or tables don't exist
            print(f"Warning: Could not clear test data: {e}")
            pass

    def create_poll_and_participant(self, num_slots=1):
        """Create a poll with the specified number of time slots and a participant."""
        from services.meetings.models import MeetingPoll, PollParticipant, get_session
        from services.meetings.models.meeting import TimeSlot

        now = datetime.now(timezone.utc)
        poll_id = uuid4()
        participant_id = uuid4()
        slot_ids = []

        with get_session() as session:
            # Add a poll
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
                min_participants=1,
                reveal_participants=False,
                poll_token=str(uuid4()),
            )
            session.add(poll)

            # Add time slots
            for i in range(num_slots):
                slot = TimeSlot(
                    id=uuid4(),
                    poll_id=poll_id,
                    start_time=now + timedelta(days=i + 1),
                    end_time=now + timedelta(days=i + 1, hours=1),
                    timezone="UTC",
                )
                session.add(slot)
                slot_ids.append(str(slot.id))

            # Add a participant
            participant = PollParticipant(
                id=participant_id,
                poll_id=poll_id,
                email="alice@example.com",
                name="Alice",
                status=ParticipantStatus.pending,
                response_token=str(uuid4()),
            )
            session.add(participant)
            session.commit()

        # Return only the IDs to avoid detached object issues
        return str(poll_id), slot_ids, str(participant_id)

    def test_process_email_response_success(self):

        from services.meetings.models import PollParticipant, PollResponse, get_session

        poll_id, slot_ids, participant_id = self.create_poll_and_participant()
        payload = {
            "emailId": "irrelevant",
            "content": "I'm AVAILABLE:\nSLOT_1: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC) - I prefer this time",
            "sender": "alice@example.com",
        }
        resp = self.client.post(
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

            # Check response was saved
            response = (
                session.query(PollResponse)
                .filter_by(
                    participant_id=UUID(participant_id), time_slot_id=UUID(slot_ids[0])
                )
                .first()
            )
            assert response is not None
            assert response.response == ResponseType.available
            assert "I prefer this time" in response.comment

    def test_process_email_response_invalid_key(self):
        poll_id, slot_ids, participant_id = self.create_poll_and_participant()
        payload = {
            "emailId": "irrelevant",
            "content": "I'm AVAILABLE:\nSLOT_1: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC)",
            "sender": "alice@example.com",
        }
        resp = self.client.post(
            "/api/v1/meetings/process-email-response/",
            json=payload,
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_process_email_response_unparseable_content(self):
        poll_id, slot_ids, participant_id = self.create_poll_and_participant()
        payload = {
            "emailId": "irrelevant",
            "content": "I am not following the format",
            "sender": "alice@example.com",
        }
        resp = self.client.post(
            "/api/v1/meetings/process-email-response/",
            json=payload,
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 400
        assert "Could not parse any slot responses" in resp.text

    def test_process_email_response_unknown_sender(self):
        poll_id, slot_ids, participant_id = self.create_poll_and_participant()
        payload = {
            "emailId": "irrelevant",
            "content": "I'm AVAILABLE:\nSLOT_1: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC)",
            "sender": "unknown@example.com",
        }
        resp = self.client.post(
            "/api/v1/meetings/process-email-response/",
            json=payload,
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 404
        assert "Participant not found" in resp.text

    def test_process_email_response_multiple_slots(self):
        from uuid import UUID

        from services.meetings.models import (
            PollParticipant,
            PollResponse,
            TimeSlot,
            get_session,
        )

        # Create a poll with 2 time slots
        poll_id, slot_ids, participant_id = self.create_poll_and_participant(
            num_slots=2
        )

        payload = {
            "emailId": "irrelevant",
            "content": "I'm AVAILABLE:\nSLOT_1: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC) - I prefer this time\n\nI'm UNAVAILABLE:\nSLOT_2: Tuesday, January 16, 2024 at 10:00 AM - 11:00 AM (UTC) - I have a conflict",
            "sender": "alice@example.com",
        }
        resp = self.client.post(
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
                    participant_id=UUID(participant_id), time_slot_id=UUID(slot_ids[0])
                )
                .all()
            )
            slot2_responses = (
                session.query(PollResponse)
                .filter_by(
                    participant_id=UUID(participant_id), time_slot_id=UUID(slot_ids[1])
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

        poll_id, slot_ids, participant_id = self.create_poll_and_participant(
            num_slots=1
        )

        # Test with malformed slot identifiers that should be skipped
        payload = {
            "emailId": "irrelevant",
            "content": "I'm AVAILABLE:\nSLOT_: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC)\nSLOT_abc: Tuesday, January 16, 2024 at 10:00 AM - 11:00 AM (UTC)\nSLOT_0: Wednesday, January 17, 2024 at 3:00 PM - 4:00 PM (UTC)",
            "sender": "alice@example.com",
        }
        resp = self.client.post(
            "/api/v1/meetings/process-email-response/",
            json=payload,
            headers={"X-API-Key": API_KEY},
        )
        assert resp.status_code == 400
        assert "Could not parse any slot responses" in resp.text

    def test_process_email_response_keyword_position_mismatch(self):
        """Test that comment extraction works correctly with keyword position matching."""

        from services.meetings.models import PollResponse, get_session

        poll_id, slot_ids, participant_id = self.create_poll_and_participant(
            num_slots=1
        )

        # Test cases that would cause keyword position mismatch
        test_cases = [
            # Case 1: "available" appears in "unavailable" - should extract comment correctly
            "I'm AVAILABLE:\nSLOT_1: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC) - I prefer this time",
            # Case 2: Multiple occurrences of keyword - should use the first word boundary match
            "I'm MAYBE:\nSLOT_1: Tuesday, January 16, 2024 at 10:00 AM - 11:00 AM (UTC) - I'm available for this time",
            # Case 3: Keyword with punctuation - should handle correctly
            "I'm UNAVAILABLE:\nSLOT_1: Wednesday, January 17, 2024 at 3:00 PM - 4:00 PM (UTC) - I have a conflict",
        ]

        for i, content in enumerate(test_cases):
            payload = {
                "emailId": "irrelevant",
                "content": content,
                "sender": "alice@example.com",
            }
            resp = self.client.post(
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
                        participant_id=UUID(participant_id),
                        time_slot_id=UUID(slot_ids[0]),
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

        from services.meetings.models import PollParticipant, PollResponse, get_session

        poll_id, slot_ids, participant_id = self.create_poll_and_participant(
            num_slots=1
        )

        # Test with a valid slot response and an invalid slot number response
        payload = {
            "emailId": "irrelevant",
            "content": "I'm AVAILABLE:\nSLOT_1: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC) - Valid response\n\nI'm UNAVAILABLE:\nSLOT_99: Tuesday, January 16, 2024 at 10:00 AM - 11:00 AM (UTC) - Invalid slot number response",
            "sender": "alice@example.com",
        }
        resp = self.client.post(
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
                    participant_id=UUID(participant_id), time_slot_id=UUID(slot_ids[0])
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

    def test_process_email_response_comment_extraction_fix(self):
        """Test that comment extraction correctly handles timezone patterns and doesn't split on time range dashes."""

        from services.meetings.models import PollResponse, get_session

        poll_id, slot_ids, participant_id = self.create_poll_and_participant(
            num_slots=1
        )

        # Test cases that would have failed with the old split logic
        test_cases = [
            # Case 1: Comment after timezone - should extract only the comment
            {
                "content": "I'm AVAILABLE:\nSLOT_1: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC) - I prefer this time slot",
                "expected_comment": "I prefer this time slot",
            },
            # Case 2: Comment with dash in time range - should not split on time range dash
            {
                "content": "I'm UNAVAILABLE:\nSLOT_1: Tuesday, January 16, 2024 at 10:00 AM - 11:00 AM (EST) - I have a conflict",
                "expected_comment": "I have a conflict",
            },
            # Case 3: Comment with multiple dashes - should only extract after timezone
            {
                "content": "I'm MAYBE:\nSLOT_1: Wednesday, January 17, 2024 at 3:00 PM - 4:00 PM (PST) - I'll try to make this work - but no guarantees",
                "expected_comment": "I'll try to make this work - but no guarantees",
            },
            # Case 4: No comment - should be None
            {
                "content": "I'm AVAILABLE:\nSLOT_1: Thursday, January 18, 2024 at 1:00 PM - 2:00 PM (UTC)",
                "expected_comment": None,
            },
            # Case 5: Different timezone format - should still work
            {
                "content": "I'm AVAILABLE:\nSLOT_1: Friday, January 19, 2024 at 9:00 AM - 10:00 AM (America/New_York) - This works for me",
                "expected_comment": "This works for me",
            },
        ]

        for i, test_case in enumerate(test_cases):
            payload = {
                "emailId": "irrelevant",
                "content": test_case["content"],
                "sender": "alice@example.com",
            }
            resp = self.client.post(
                "/api/v1/meetings/process-email-response/",
                json=payload,
                headers={"X-API-Key": API_KEY},
            )
            assert resp.status_code == 200, f"Test case {i+1} failed: {resp.text}"

            # Check that the comment was extracted correctly
            with get_session() as session:
                response = (
                    session.query(PollResponse)
                    .filter_by(
                        participant_id=UUID(participant_id),
                        time_slot_id=UUID(slot_ids[0]),
                    )
                    .first()
                )
                assert response is not None, f"Test case {i+1}: No response found"

                if test_case["expected_comment"] is None:
                    assert (
                        response.comment is None
                    ), f"Test case {i+1}: Expected no comment but got '{response.comment}'"
                else:
                    assert (
                        response.comment == test_case["expected_comment"]
                    ), f"Test case {i+1}: Expected '{test_case['expected_comment']}' but got '{response.comment}'"
