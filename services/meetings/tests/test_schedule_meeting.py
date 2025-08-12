from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from services.meetings.tests.meetings_test_base import BaseMeetingsTest


class TestScheduleMeeting(BaseMeetingsTest):
    def create_poll(self, client):
        # Create a simple poll with two time slots and two participants
        payload = {
            "title": "Team Sync",
            "description": "Discuss project updates",
            "duration_minutes": 60,
            "location": "Zoom",
            "meeting_type": "virtual",
            "response_deadline": (
                datetime.now(timezone.utc) + timedelta(days=7)
            ).isoformat(),
            "time_slots": [
                {
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "end_time": (
                        datetime.now(timezone.utc) + timedelta(hours=1)
                    ).isoformat(),
                    "timezone": "UTC",
                },
                {
                    "start_time": (
                        datetime.now(timezone.utc) + timedelta(days=1)
                    ).isoformat(),
                    "end_time": (
                        datetime.now(timezone.utc) + timedelta(days=1, hours=1)
                    ).isoformat(),
                    "timezone": "UTC",
                },
            ],
            "participants": [
                {"email": "alice@example.com", "name": "Alice"},
                {"email": "bob@example.com", "name": "Bob"},
            ],
        }
        headers = {
            "X-User-Id": "owner@example.com",
            "Authorization": "Bearer test-frontend-meetings-key",
        }
        resp = client.post("/api/v1/meetings/polls", json=payload, headers=headers)
        assert resp.status_code == 200, resp.text
        return resp.json()

    def test_schedule_creates_event_and_sets_scheduled_slot(self):
        poll = self.create_poll(self.client)
        poll_id = poll["id"]
        slot_id = poll["time_slots"][0]["id"]

        with patch(
            "services.meetings.services.calendar_integration.create_calendar_event",
            return_value={
                "success": True,
                "data": {
                    "event_id": "google_abc123",
                    "status": "created",
                    "provider": "google",
                },
            },
        ) as mock_create:
            headers = {
                "X-User-Id": "owner@example.com",
                "Authorization": "Bearer test-frontend-meetings-key",
            }
            resp = self.client.post(
                f"/api/v1/meetings/polls/{poll_id}/schedule",
                json={"selectedSlotId": slot_id},
                headers=headers,
            )
            assert resp.status_code == 200, resp.text
            mock_create.assert_called_once()

        # Fetch poll and verify scheduled_slot_id and calendar_event_id set
        headers = {
            "Authorization": "Bearer test-frontend-meetings-key",
        }
        get_resp = self.client.get(f"/api/v1/meetings/polls/{poll_id}", headers=headers)
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data.get("scheduled_slot_id") == slot_id
        assert data.get("calendar_event_id") == "google_abc123"
        assert data.get("status") == "scheduled"

    def test_schedule_updates_existing_event_when_rescheduling(self):
        poll = self.create_poll(self.client)
        poll_id = poll["id"]
        first_slot_id = poll["time_slots"][0]["id"]
        second_slot_id = poll["time_slots"][1]["id"]

        # First schedule to create an event
        with patch(
            "services.meetings.services.calendar_integration.create_calendar_event",
            return_value={
                "success": True,
                "data": {
                    "event_id": "google_abc123",
                    "status": "created",
                    "provider": "google",
                },
            },
        ):
            headers = {
                "X-User-Id": "owner@example.com",
                "Authorization": "Bearer test-frontend-meetings-key",
            }
            resp = self.client.post(
                f"/api/v1/meetings/polls/{poll_id}/schedule",
                json={"selectedSlotId": first_slot_id},
                headers=headers,
            )
            assert resp.status_code == 200

        # Now reschedule to second slot; should call update
        with patch(
            "services.meetings.services.calendar_integration.update_calendar_event",
            return_value={
                "success": True,
                "data": {
                    "event_id": "google_abc123",
                    "status": "updated",
                    "provider": "google",
                },
            },
        ) as mock_update:
            headers = {
                "X-User-Id": "owner@example.com",
                "Authorization": "Bearer test-frontend-meetings-key",
            }
            resp = self.client.post(
                f"/api/v1/meetings/polls/{poll_id}/schedule",
                json={"selectedSlotId": second_slot_id},
                headers=headers,
            )
            assert resp.status_code == 200
            mock_update.assert_called_once()

        # Verify scheduled_slot_id updated and calendar_event_id unchanged
        headers = {
            "Authorization": "Bearer test-frontend-meetings-key",
        }
        get_resp = self.client.get(f"/api/v1/meetings/polls/{poll_id}", headers=headers)
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data.get("scheduled_slot_id") == second_slot_id
        assert data.get("calendar_event_id") == "google_abc123"
        assert data.get("status") == "scheduled"
