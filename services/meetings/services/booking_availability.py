from datetime import datetime
from typing import Any, Dict

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

    # TODO: post-process availability to enforce buffers, business hours, limits
    # For now, return as-is
    return availability


