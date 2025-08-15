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
    try:
        availability = await calendar_integration.get_user_availability(
            user_id, start_iso, end_iso, duration_minutes
        )
    except Exception as e:
        print(f"DEBUG: Office service error: {e}")
        # Return empty response on error
        return {
            "slots": [],
            "duration": duration_minutes,
            "timezone": "UTC"
        }

    # Extract available slots from office service response
    # Office service returns: {"data": {"available_slots": [...], "total_slots": N, ...}}
    # We need to transform this to: {"slots": [...], "duration": N, "timezone": "UTC"}
    
    print(f"DEBUG: Raw availability response: {availability}")
    
    available_slots = []
    if availability.get("data", {}).get("available_slots"):
        available_slots = availability["data"]["available_slots"]
    
    print(f"DEBUG: Extracted {len(available_slots)} available slots")
    print(f"DEBUG: Settings: {settings}")
    
    # Post-process availability to enforce buffers, business hours, limits
    if settings and available_slots:
        print(f"DEBUG: Found {len(available_slots)} slots, applying settings")
        # Apply booking settings to filter and adjust slots
        available_slots = _apply_booking_settings(
            available_slots,
            duration_minutes,
            buffer_before_minutes or 0,
            buffer_after_minutes or 0,
            settings
        )
        print(f"DEBUG: After applying settings: {len(available_slots)} slots")
    else:
        print(f"DEBUG: No settings or slots - settings: {bool(settings)}, slots: {len(available_slots)}")

    # Return transformed format that matches meetings service schema
    result = {
        "slots": available_slots,
        "duration": duration_minutes,
        "timezone": "UTC"
    }
    print(f"DEBUG: Returning result: {result}")
    return result


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
    
    print(f"DEBUG: Processing {len(slots)} slots with settings: {settings}")
    print(f"DEBUG: Buffer before: {buffer_before_minutes}, after: {buffer_after_minutes}")

    filtered_slots = []
    business_hours = settings.get("business_hours", {})
    max_per_day = settings.get("max_per_day", 10)
    max_per_week = settings.get("max_per_week", 50)
    advance_days = settings.get("advance_days", 0)  # Allow same-day bookings
    max_advance_days = settings.get("max_advance_days", 90)
    last_minute_cutoff = settings.get("last_minute_cutoff", 0)  # Allow last-minute bookings

    # Track bookings per day and week for limit enforcement
    bookings_per_day: Dict[str, int] = {}
    bookings_per_week: Dict[str, int] = {}

    for i, slot in enumerate(slots):
        print(f"DEBUG: Processing slot {i}: {slot}")
        # Handle both dict format and AvailableSlot objects from office service
        if hasattr(slot, 'start') and hasattr(slot, 'end'):
            # AvailableSlot object from office service
            slot_start = slot.start
            slot_end = slot.end
            print(f"DEBUG: Slot {i} is AvailableSlot object: start={slot_start}, end={slot_end}")
        else:
            # Dict format
            if not slot.get("available", True):
                print(f"DEBUG: Slot {i} filtered - not available")
                continue
            
            # Handle both string and datetime values
            if isinstance(slot["start"], str):
                slot_start = datetime.fromisoformat(slot["start"])
            else:
                slot_start = slot["start"]
            
            if isinstance(slot["end"], str):
                slot_end = datetime.fromisoformat(slot["end"])
            else:
                slot_end = slot["end"]
            
            print(f"DEBUG: Slot {i} is dict: start={slot_start}, end={slot_end}")

        # Check advance booking window
        now = datetime.now(slot_start.tzinfo) if slot_start.tzinfo else datetime.now()
        days_until_slot = (slot_start - now).days

        if days_until_slot < advance_days:
            print(f"DEBUG: Slot filtered - too soon: {slot_start} (days until: {days_until_slot}, min: {advance_days})")
            continue  # Too soon
        if days_until_slot > max_advance_days:
            print(f"DEBUG: Slot filtered - too far: {slot_start} (days until: {days_until_slot}, max: {max_advance_days})")
            continue  # Too far in advance

        # Check last-minute cutoff
        hours_until_slot = (slot_start - now).total_seconds() / 3600
        if hours_until_slot < last_minute_cutoff:
            continue  # Too close to meeting time

        # Check business hours - only if explicitly configured
        if business_hours and not _is_within_business_hours(slot_start, slot_end, business_hours):
            continue  # Outside business hours

        # Check daily limit
        day_key = slot_start.date().isoformat()
        if bookings_per_day.get(day_key, 0) >= max_per_day:
            continue  # Daily limit reached

        # Check weekly limit
        week_key = f"{slot_start.year}-W{slot_start.isocalendar()[1]}"
        if bookings_per_week.get(week_key, 0) >= max_per_week:
            continue  # Weekly limit reached

        # Apply buffers
        adjusted_start = slot_start + timedelta(minutes=buffer_before_minutes)
        adjusted_end = slot_end - timedelta(minutes=buffer_after_minutes)

        # Ensure adjusted slot is still valid (must have at least 1 minute)
        if adjusted_start >= adjusted_end - timedelta(minutes=1):
            continue  # Buffer makes slot too short

        # Create adjusted slot
        adjusted_slot = {
            "start": adjusted_start.isoformat(),
            "end": adjusted_end.isoformat(),
            "available": True,
            "original_start": slot.start.isoformat() if hasattr(slot, 'start') else slot["start"],
            "original_end": slot.end.isoformat() if hasattr(slot, 'end') else slot["end"],
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
        return False  # Day not configured, reject the slot

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
        # Slot spans midnight - check if any part overlaps with business hours
        # For overnight slots, we need to check if the slot overlaps with business hours
        # This is complex, so for now, reject overnight slots as they're typically outside business hours
        return False
    else:
        # Normal slot - check if slot is completely within business hours
        return slot_start_hour >= start_hour and slot_end_hour <= end_hour
