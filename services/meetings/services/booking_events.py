from datetime import datetime
from typing import List, Optional

from services.meetings.services import calendar_integration


async def create_owner_calendar_event(
    user_id: str,
    title: str,
    description: Optional[str],
    start_time: datetime,
    end_time: datetime,
    attendees_emails: List[str],
    location: Optional[str] = None,
) -> dict:
    return await calendar_integration.create_calendar_event(
        user_id,
        title,
        description,
        start_time,
        end_time,
        attendees_emails,
        location,
    )


