"""
Test suite for the availability service.

Note: This test suite has been made robust against datetime edge cases that can cause
failures in CI environments. The tests now use a helper method `_get_future_monday()`
to ensure that test slots are always created for future dates, preventing failures
when tests run late at night on the same day that the test is trying to create slots for.

This addresses the issue where tests would fail when:
1. Running on Monday late at night (e.g., 11:30 PM)
2. Creating slots for 9:00 AM and 6:00 PM on the same Monday
3. The 6:00 PM slot would have already passed, causing the business hours filter to fail
4. The test would expect 1 slot but get 0 slots

The fix ensures all test slots are created for future dates, making the tests deterministic
regardless of when they are run.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.meetings.services.booking_availability import (
    _apply_booking_settings,
    _is_within_business_hours,
    compute_available_slots,
)
from services.meetings.tests.meetings_test_base import BaseMeetingsTest


class TestAvailabilityService(BaseMeetingsTest):
    """Test suite for the availability service."""

    def _get_future_monday(self, days_offset: int = 0) -> datetime:
        """
        Get a future Monday date to ensure test slots are always in the future.

        This prevents test failures when running tests late at night on Monday,
        where slots created for the current Monday would have already passed.

        Args:
            days_offset: Additional days to add beyond the next Monday (default: 0)

        Returns:
            A datetime representing a future Monday at midnight UTC
        """
        now = datetime.now(timezone.utc)
        # Find the next Monday
        days_until_monday = (0 - now.weekday()) % 7
        if days_until_monday == 0:  # If today is Monday, use next Monday
            days_until_monday = 7

        # Add the offset to ensure it's far enough in the future
        monday_date = now + timedelta(days=days_until_monday + days_offset)
        return monday_date.replace(hour=0, minute=0, second=0, microsecond=0)

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)

        # Test data
        self.test_user_id = "test-user-123"
        self.start_date = datetime.now(timezone.utc)
        self.end_date = self.start_date + timedelta(days=30)
        self.duration_minutes = 30

        # Mock office service response
        future_date = datetime.now(timezone.utc) + timedelta(days=7)
        self.mock_office_response = {
            "data": {
                "available_slots": [
                    {
                        "start": future_date.replace(
                            hour=9, minute=0, second=0, microsecond=0
                        ).isoformat(),
                        "end": future_date.replace(
                            hour=9, minute=30, second=0, microsecond=0
                        ).isoformat(),
                        "duration_minutes": 30,
                    },
                    {
                        "start": future_date.replace(
                            hour=14, minute=0, second=0, microsecond=0
                        ).isoformat(),
                        "end": future_date.replace(
                            hour=14, minute=30, second=0, microsecond=0
                        ).isoformat(),
                        "duration_minutes": 30,
                    },
                    {
                        "start": future_date.replace(
                            hour=17, minute=0, second=0, microsecond=0
                        ).isoformat(),
                        "end": future_date.replace(
                            hour=17, minute=30, second=0, microsecond=0
                        ).isoformat(),
                        "duration_minutes": 30,
                    },
                ],
                "total_slots": 3,
                "providers_used": ["microsoft"],
                "request_metadata": {},
            }
        }

        # Sample settings for testing
        self.sample_settings = {
            "buffer_before": 15,
            "buffer_after": 15,
            "business_hours": {
                "monday": {"enabled": True, "start": "09:00", "end": "17:00"},
                "tuesday": {"enabled": True, "start": "09:00", "end": "17:00"},
                "wednesday": {"enabled": True, "start": "09:00", "end": "17:00"},
                "thursday": {"enabled": True, "start": "09:00", "end": "17:00"},
                "friday": {"enabled": True, "start": "09:00", "end": "17:00"},
            },
            "max_per_day": 10,
            "max_per_week": 50,
            "advance_days": 1,
            "max_advance_days": 90,
            "last_minute_cutoff": 2,
        }

        # Sample time slots for testing
        base_time = datetime.now(timezone.utc).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        self.sample_time_slots = [
            {"start": base_time, "end": base_time + timedelta(minutes=30)},
            {
                "start": base_time + timedelta(hours=1),
                "end": base_time + timedelta(hours=1, minutes=30),
            },
            {
                "start": base_time + timedelta(hours=2),
                "end": base_time + timedelta(hours=2, minutes=30),
            },
        ]

    @patch("services.meetings.services.calendar_integration.get_user_availability")
    async def test_compute_available_slots_success(self, mock_get_availability):
        """Test successful computation of available slots."""
        # Mock the office service response
        mock_get_availability.return_value = self.mock_office_response

        # Call the service
        result = await compute_available_slots(
            user_id=self.test_user_id,
            start=self.start_date,
            end=self.end_date,
            duration_minutes=self.duration_minutes,
        )

        # Verify result
        assert "slots" in result
        assert len(result["slots"]) == 3
        assert result["duration"] == self.duration_minutes
        assert result["timezone"] == "UTC"

        # Verify the mock was called correctly
        mock_get_availability.assert_called_once()
        call_args = mock_get_availability.call_args
        assert call_args[0][0] == self.test_user_id  # user_id
        assert call_args[0][1] == self.start_date.isoformat()  # start
        assert call_args[0][2] == self.end_date.isoformat()  # end
        assert call_args[0][3] == self.duration_minutes  # duration

    @patch("services.meetings.services.calendar_integration.get_user_availability")
    async def test_compute_available_slots_no_slots(self, mock_get_availability):
        """Test computation when no slots are available."""
        # Mock empty response
        mock_get_availability.return_value = {
            "data": {
                "available_slots": [],
                "total_slots": 0,
                "providers_used": [],
                "request_metadata": {},
            }
        }

        # Call the service
        result = await compute_available_slots(
            user_id=self.test_user_id,
            start=self.start_date,
            end=self.end_date,
            duration_minutes=self.duration_minutes,
        )

        # Verify result
        assert "slots" in result
        assert len(result["slots"]) == 0
        assert result["duration"] == self.duration_minutes

    @patch("services.meetings.services.calendar_integration.get_user_availability")
    async def test_compute_available_slots_with_settings(self, mock_get_availability):
        """Test computation with booking settings applied."""
        # Mock the office service response
        mock_get_availability.return_value = self.mock_office_response

        # Use the sample settings from setup_method
        settings = self.sample_settings

        # Call the service
        result = await compute_available_slots(
            user_id=self.test_user_id,
            start=self.start_date,
            end=self.end_date,
            duration_minutes=self.duration_minutes,
            buffer_before_minutes=15,
            buffer_after_minutes=15,
            settings=settings,
        )

        # Verify result
        assert "slots" in result
        assert result["duration"] == self.duration_minutes

    @patch("services.meetings.services.calendar_integration.get_user_availability")
    async def test_compute_available_slots_office_service_error(
        self, mock_get_availability
    ):
        """Test handling of office service errors."""
        # Mock office service error
        mock_get_availability.side_effect = Exception("Office service unavailable")

        # Call the service
        result = await compute_available_slots(
            user_id=self.test_user_id,
            start=self.start_date,
            end=self.end_date,
            duration_minutes=self.duration_minutes,
        )

        # Should return empty slots on error
        assert "slots" in result
        assert len(result["slots"]) == 0

    def test_apply_booking_settings_no_settings(self):
        """Test applying booking settings when no settings are provided."""
        # Use future dates to avoid advance booking window filtering
        future_date = datetime.now(timezone.utc) + timedelta(days=7)
        slots = [
            {
                "start": future_date.replace(hour=9, minute=0, second=0, microsecond=0),
                "end": future_date.replace(hour=9, minute=30, second=0, microsecond=0),
            },
            {
                "start": future_date.replace(
                    hour=14, minute=0, second=0, microsecond=0
                ),
                "end": future_date.replace(hour=14, minute=30, second=0, microsecond=0),
            },
        ]

        result = _apply_booking_settings(
            slots=slots,
            duration_minutes=30,
            buffer_before_minutes=0,
            buffer_after_minutes=0,
            settings={},
        )

        # Should return all slots when no settings
        assert len(result) == 2

    def test_apply_booking_settings_with_buffers(self):
        """Test applying buffer settings to slots."""
        # Use future dates to avoid advance booking window filtering
        future_date = datetime.now(timezone.utc) + timedelta(days=7)
        slots = [
            {
                "start": future_date.replace(hour=9, minute=0, second=0, microsecond=0),
                "end": future_date.replace(hour=9, minute=30, second=0, microsecond=0),
            },
            {
                "start": future_date.replace(
                    hour=14, minute=0, second=0, microsecond=0
                ),
                "end": future_date.replace(hour=14, minute=30, second=0, microsecond=0),
            },
        ]

        settings = {"buffer_before": 5, "buffer_after": 5}

        result = _apply_booking_settings(
            slots=slots,
            duration_minutes=30,
            buffer_before_minutes=5,
            buffer_after_minutes=5,
            settings=settings,
        )

        # Should return adjusted slots
        assert len(result) == 2
        for slot in result:
            assert "original_start" in slot
            assert "original_end" in slot

    def test_apply_booking_settings_business_hours(self):
        """Test applying business hours filtering."""
        # Create slots for a future Monday to ensure they're in the future
        monday_date = self._get_future_monday()

        slots = [
            {
                "start": monday_date.replace(hour=9, minute=0, second=0, microsecond=0),
                "end": monday_date.replace(hour=9, minute=30, second=0, microsecond=0),
            },
            {
                "start": monday_date.replace(
                    hour=18, minute=0, second=0, microsecond=0
                ),
                "end": monday_date.replace(hour=18, minute=30, second=0, microsecond=0),
            },
        ]

        settings = {
            "business_hours": {
                "monday": {"enabled": True, "start": "09:00", "end": "17:00"}
            }
        }

        result = _apply_booking_settings(
            slots=slots,
            duration_minutes=30,
            buffer_before_minutes=0,
            buffer_after_minutes=0,
            settings=settings,
        )

        # Should filter out the 18:00 slot (outside business hours)
        assert len(result) == 1
        # The result contains ISO strings, so we need to parse them
        start_time = datetime.fromisoformat(result[0]["start"])
        assert start_time.hour == 9

    def test_apply_booking_settings_advance_booking(self):
        """Test advance booking window filtering."""
        # Create slots with different advance times
        now = datetime.now(timezone.utc)
        slots = [
            {
                "start": now + timedelta(hours=1),  # Too soon
                "end": now + timedelta(hours=1, minutes=30),
            },
            {
                "start": now + timedelta(days=2),  # Within window
                "end": now + timedelta(days=2, minutes=30),
            },
            {
                "start": now + timedelta(days=100),  # Too far
                "end": now + timedelta(days=100, minutes=30),
            },
        ]

        settings = {"advance_days": 1, "max_advance_days": 90}

        result = _apply_booking_settings(
            slots=slots,
            duration_minutes=30,
            buffer_before_minutes=0,
            buffer_after_minutes=0,
            settings=settings,
        )

        # Should only return the slot within the advance booking window
        assert len(result) == 1
        start_time = datetime.fromisoformat(result[0]["start"])
        assert (start_time - now).days == 2

    def test_apply_booking_settings_last_minute_cutoff(self):
        """Test last-minute cutoff filtering."""
        # Create slots with different proximity to now
        now = datetime.now(timezone.utc)
        slots = [
            {
                "start": now + timedelta(hours=1),  # Too close
                "end": now + timedelta(hours=1, minutes=30),
            },
            {
                "start": now + timedelta(hours=3),  # Acceptable
                "end": now + timedelta(hours=3, minutes=30),
            },
        ]

        settings = {"last_minute_cutoff": 2}  # 2 hours

        result = _apply_booking_settings(
            slots=slots,
            duration_minutes=30,
            buffer_before_minutes=0,
            buffer_after_minutes=0,
            settings=settings,
        )

        # Should only return the slot that's not too close
        assert len(result) == 1
        start_time = datetime.fromisoformat(result[0]["start"])
        assert (start_time - now).total_seconds() / 3600 >= 2

    def test_apply_booking_settings_daily_limits(self):
        """Test daily booking limits."""
        # Create multiple slots for the same day in the future
        future_date = datetime.now(timezone.utc) + timedelta(days=7)
        base_date = future_date.replace(hour=9, minute=0, second=0, microsecond=0)
        slots = []
        for i in range(12):  # More than the daily limit
            slots.append(
                {
                    "start": base_date + timedelta(hours=i),
                    "end": base_date + timedelta(hours=i, minutes=30),
                }
            )

        settings = {"max_per_day": 10}

        result = _apply_booking_settings(
            slots=slots,
            duration_minutes=30,
            buffer_before_minutes=0,
            buffer_after_minutes=0,
            settings=settings,
        )

        # Should respect daily limit
        assert len(result) == 10

    def test_apply_booking_settings_weekly_limits(self):
        """Test weekly booking limits."""
        # Create multiple slots for a future day to ensure they're in the future
        now = datetime.now(timezone.utc)
        future_date = now + timedelta(days=7)  # Use a future date
        base_date = future_date.replace(hour=9, minute=0, second=0, microsecond=0)

        slots = []
        # Create exactly 60 slots within the same week
        # Start with Monday and create slots across multiple days but within the same week
        slot_count = 0
        current_date = base_date
        
        # Ensure we start on a Monday to have a full week
        while current_date.weekday() != 0:  # 0 = Monday
            current_date += timedelta(days=1)
        
        # Create slots for up to 5 days (Monday to Friday) within the same week
        for day_offset in range(5):  # Monday to Friday
            if slot_count >= 60:
                break
                
            day_date = current_date + timedelta(days=day_offset)
            
            # Create slots for this day (9 AM to 6 PM, 30-minute intervals)
            for hour in range(9, 18):  # 9 AM to 6 PM
                for minute in [0, 30]:  # 30-minute intervals
                    if slot_count >= 60:
                        break
                    
                    slot_start = day_date.replace(hour=hour, minute=minute)
                    slot_end = slot_start + timedelta(minutes=30)
                    
                    slots.append({"start": slot_start, "end": slot_end})
                    slot_count += 1
                
                if slot_count >= 60:
                    break

        # Verify we have the expected number of slots
        assert len(slots) == 60, f"Expected 60 slots, got {len(slots)}"
        
        # Verify all slots are within the same week
        first_week = slots[0]["start"].isocalendar()
        last_week = slots[-1]["start"].isocalendar()
        assert (first_week.year, first_week.week) == (last_week.year, last_week.week), f"All slots should be in the same week: {first_week} vs {last_week}"

        settings = {
            "max_per_week": 50,
            "max_per_day": 60,  # Allow more than 60 slots per day
            "advance_days": 0,  # Allow same-day bookings
        }

        result = _apply_booking_settings(
            slots=slots,
            duration_minutes=30,
            buffer_before_minutes=0,
            buffer_after_minutes=0,
            settings=settings,
        )

        # Should respect weekly limit - only 50 slots within the same week
        assert len(result) == 50, f"Expected 50 slots due to weekly limit, got {len(result)}"

    def test_is_within_business_hours_enabled_day(self):
        """Test business hours check for enabled day."""
        # Monday 10:00 AM - ensure we're testing on a future Monday
        monday = self._get_future_monday()

        start_time = monday.replace(hour=10, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=30)

        business_hours = {"monday": {"enabled": True, "start": "09:00", "end": "17:00"}}

        result = _is_within_business_hours(start_time, end_time, business_hours)
        assert result is True

    def test_is_within_business_hours_disabled_day(self):
        """Test business hours check for disabled day."""
        # Monday 10:00 AM - use a future Monday
        monday = self._get_future_monday()

        start_time = monday.replace(hour=10, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=30)

        business_hours = {
            "monday": {"enabled": False, "start": "09:00", "end": "17:00"}
        }

        result = _is_within_business_hours(start_time, end_time, business_hours)
        assert result is False

    def test_is_within_business_hours_outside_hours(self):
        """Test business hours check for time outside business hours."""
        # Monday 18:00 (6 PM) - outside 9 AM - 5 PM - use a future Monday
        monday = self._get_future_monday()

        start_time = monday.replace(hour=18, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=30)

        business_hours = {"monday": {"enabled": True, "start": "09:00", "end": "17:00"}}

        result = _is_within_business_hours(start_time, end_time, business_hours)
        assert result is False

    def test_is_within_business_hours_no_config(self):
        """Test business hours check when no configuration is provided."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=30)

        result = _is_within_business_hours(start_time, end_time, {})
        assert result is True  # Should allow all times when no config

    def test_is_within_business_hours_overnight_slot(self):
        """Test business hours check for overnight slots."""
        # Monday 23:00 to Tuesday 01:00 - use a future Monday
        monday = self._get_future_monday()

        start_time = monday.replace(hour=23, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=2)  # Goes to 01:00 next day

        business_hours = {
            "monday": {"enabled": True, "start": "09:00", "end": "17:00"},
            "tuesday": {"enabled": True, "start": "09:00", "end": "17:00"},
        }

        result = _is_within_business_hours(start_time, end_time, business_hours)
        # Should be False since it's outside business hours
        assert result is False

    def test_apply_booking_settings_timezone_aware_datetimes(self):
        """Test handling of timezone-aware datetime objects from office service."""
        # Create timezone-aware slots (like what the office service returns)
        utc_tz = timezone.utc
        now = datetime.now(utc_tz)

        slots = [
            {
                "start": now + timedelta(hours=2),
                "end": now + timedelta(hours=2, minutes=30),
            }
        ]

        settings = {"advance_days": 0, "max_advance_days": 90, "last_minute_cutoff": 0}

        result = _apply_booking_settings(
            slots=slots,
            duration_minutes=30,
            buffer_before_minutes=0,
            buffer_after_minutes=0,
            settings=settings,
        )

        # Should handle timezone-aware datetimes correctly
        assert len(result) == 1
        start_time = datetime.fromisoformat(result[0]["start"])
        end_time = datetime.fromisoformat(result[0]["end"])
        assert start_time.tzinfo is not None
        assert end_time.tzinfo is not None
