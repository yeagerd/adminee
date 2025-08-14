from datetime import datetime
from typing import Any, List, Optional

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


async def create_booking_calendar_event(booking: Any) -> Optional[str]:
    """
    Create a calendar event for a booking.

    Args:
        booking: The booking object containing start_at, end_at, attendee_email, etc.

    Returns:
        The calendar event ID if successful, None if failed
    """
    try:
        # Extract booking details
        start_time = booking.start_at
        end_time = booking.end_at
        attendee_email = booking.attendee_email

        # Get the owner user ID from the booking link
        from services.meetings.models.booking_entities import BookingLink

        from services.meetings.models import get_session

        with get_session() as session:
            booking_link = (
                session.query(BookingLink).filter_by(id=booking.link_id).first()
            )
            if not booking_link:
                return None

            owner_user_id = booking_link.owner_user_id

        # Create event title and description
        title = f"Meeting with {attendee_email}"
        description = "Meeting scheduled via booking link"

        # Add answers to description if available
        if booking.answers:
            answers_text = "\n".join([f"{k}: {v}" for k, v in booking.answers.items()])
            description += f"\n\nAttendee Information:\n{answers_text}"

        # Create the calendar event
        event_result = await calendar_integration.create_calendar_event(
            user_id=owner_user_id,  # type: ignore[arg-type]
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            attendees_emails=[attendee_email],
            location=None,  # Could be added to booking settings in the future
        )

        # Extract event ID from response
        if (
            event_result
            and "data" in event_result
            and event_result["data"]
            and "event_id" in event_result["data"]
        ):
            return event_result["data"]["event_id"]
        else:
            return None

    except Exception as e:
        # Log the error but don't fail the booking creation
        # In production, this should use proper logging
        print(f"Failed to create calendar event for booking {booking.id}: {e}")
        return None
