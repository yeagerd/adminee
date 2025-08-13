from datetime import datetime, timedelta
from typing import Any, Dict, List

from services.meetings.services import calendar_integration


async def compute_available_slots(
    user_id: str,
    start: datetime,
    end: datetime,
    duration_minutes: int,
    *,
    buffer_before_minutes: int = 0,
    buffer_after_minutes: int = 0,
    timezone: str | None = None,
    settings: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Return available slots for the user between start and end for a given duration.

    For MVP, this delegates to the Office service unified availability endpoint.
    Future iterations can apply buffers, business hours, limits and template rules here.
    """
    # Office service expects ISO strings
    start_iso = start.isoformat()
    end_iso = end.isoformat()

    # Delegate to existing integration
    availability = await calendar_integration.get_user_availability(
        user_id, start_iso, end_iso, duration_minutes
    )

    # Post-process availability to enforce buffers, business hours, limits
    if settings and availability.get("slots"):
        availability["slots"] = _apply_booking_settings(
            availability["slots"],
            duration_minutes,
            buffer_before_minutes,
            buffer_after_minutes,
            settings,
        )

    return availability


def _apply_booking_settings(
    slots: List[Dict[str, Any]],
    duration_minutes: int,
    buffer_before_minutes: int,
    buffer_after_minutes: int,
    settings: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Apply booking settings to filter and adjust available slots.

    Args:
        slots: List of available time slots from Office Service
        duration_minutes: Meeting duration in minutes
        buffer_before_minutes: Buffer before meeting in minutes
        buffer_after_minutes: Buffer after meeting in minutes
        settings: Booking link settings including business hours, limits, etc.

    Returns:
        Filtered and adjusted list of available slots
    """
    if not slots:
        return []

    filtered_slots = []
    business_hours = settings.get("business_hours", {})
    max_per_day = settings.get("max_per_day", 10)
    max_per_week = settings.get("max_per_week", 50)
    advance_days = settings.get("advance_days", 1)
    max_advance_days = settings.get("max_advance_days", 90)
    last_minute_cutoff = settings.get("last_minute_cutoff", 2)  # hours

    # Track bookings per day and week for limit enforcement
    bookings_per_day: Dict[str, int] = {}
    bookings_per_week: Dict[str, int] = {}

    for slot in slots:
        if not slot.get("available", True):
            continue

        slot_start = datetime.fromisoformat(slot["start"])
        slot_end = datetime.fromisoformat(slot["end"])

        # Check advance booking window
        now = datetime.now()
        days_until_slot = (slot_start - now).days

        if days_until_slot < advance_days:
            continue  # Too soon
        if days_until_slot > max_advance_days:
            continue  # Too far in advance

        # Check last-minute cutoff
        hours_until_slot = (slot_start - now).total_seconds() / 3600
        if hours_until_slot < last_minute_cutoff:
            continue  # Too close to meeting time

        # Check business hours
        if not _is_within_business_hours(slot_start, slot_end, business_hours):
            continue  # Outside business hours

        # Check daily and weekly limits
        day_key = slot_start.date().isoformat()
        week_key = f"{slot_start.year}-W{slot_start.isocalendar()[1]}"

        if bookings_per_day.get(day_key, 0) >= max_per_day:
            continue  # Daily limit reached

        if bookings_per_week.get(week_key, 0) >= max_per_week:
            continue  # Weekly limit reached

        # Apply buffers
        adjusted_start = slot_start + timedelta(minutes=buffer_before_minutes)
        adjusted_end = slot_end - timedelta(minutes=buffer_after_minutes)

        # Ensure adjusted slot is still valid
        if adjusted_start >= adjusted_end:
            continue  # Buffer makes slot too short

        # Create adjusted slot
        adjusted_slot = {
            "start": adjusted_start.isoformat(),
            "end": adjusted_end.isoformat(),
            "available": True,
            "original_start": slot["start"],
            "original_end": slot["end"],
        }

        filtered_slots.append(adjusted_slot)

        # Update counters
        bookings_per_day[day_key] = bookings_per_day.get(day_key, 0) + 1
        bookings_per_week[week_key] = bookings_per_week.get(week_key, 0) + 1

    return filtered_slots


def _is_within_business_hours(
    start_time: datetime, end_time: datetime, business_hours: Dict[str, Any]
) -> bool:
    """
    Check if a time slot falls within business hours.

    Args:
        start_time: Start time of the slot
        end_time: End time of the slot
        business_hours: Business hours configuration

    Returns:
        True if slot is within business hours, False otherwise
    """
    if not business_hours:
        return True  # No business hours configured, allow all times

    # Get day of week (lowercase)
    day_name = start_time.strftime("%A").lower()

    # Check if this day has business hours configured
    if day_name not in business_hours:
        return True  # Day not configured, allow all times

    day_config = business_hours[day_name]
    if not day_config.get("enabled", True):
        return False  # Day explicitly disabled

    # Parse business hours
    try:
        start_hour = int(day_config.get("start", "09:00").split(":")[0])
        end_hour = int(day_config.get("end", "17:00").split(":")[0])
    except (ValueError, AttributeError):
        return True  # Invalid time format, allow all times

    # Check if slot overlaps with business hours
    slot_start_hour = start_time.hour
    slot_end_hour = end_time.hour

    # Handle overnight slots (e.g., 23:00 to 01:00)
    if slot_start_hour > slot_end_hour:
        # Slot spans midnight
        return slot_start_hour >= start_hour or slot_end_hour <= end_hour
    else:
        # Normal slot
        return slot_start_hour >= start_hour and slot_end_hour <= end_hour
