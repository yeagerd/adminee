from datetime import datetime
from typing import Any, Dict, Optional

from services.meetings.services import email_integration


def _format_dt(dt: datetime) -> str:
    return dt.strftime("%A, %B %d, %Y at %I:%M %p %Z")


async def send_confirmation_email(booking: Any) -> bool:
    """
    Send confirmation email for a booking.

    Args:
        booking: The booking object containing all necessary details

    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        # Get the owner user ID from the booking link
        from services.meetings.models import get_session
        from services.meetings.models.bookings import BookingLink

        with get_session() as session:
            booking_link = (
                session.query(BookingLink).filter_by(id=booking.link_id).first()
            )
            if not booking_link:
                return False

            owner_user_id = booking_link.owner_user_id

        # Get owner email (for now, we'll use a placeholder - in production this would come from user service)
        # TODO: Get actual owner email from user service
        owner_email = f"{owner_user_id}@example.com"  # Placeholder

        # Format the meeting details
        title = "Meeting Confirmation"
        start_time = booking.start_at
        end_time = booking.end_at
        location = None  # Could be added to booking settings in the future
        answers = booking.answers

        # Send confirmation emails
        await send_booking_confirmations(
            user_id=owner_user_id,  # type: ignore[arg-type]
            owner_email=owner_email,
            recipient_email=booking.attendee_email,
            title=title,
            start_time=start_time,
            end_time=end_time,
            location=location,
            answers=answers,
        )

        return True

    except Exception as e:
        # Log the error but don't fail the booking creation
        # In production, this should use proper logging
        print(f"Failed to send confirmation email for booking {booking.id}: {e}")
        return False


async def send_follow_up_email(booking: Any) -> bool:
    """
    Send optional follow-up email if enabled in the template.

    Args:
        booking: The booking object containing all necessary details

    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        # Get the owner user ID from the booking link
        from services.meetings.models import get_session
        from services.meetings.models.bookings import BookingLink

        with get_session() as session:
            booking_link = (
                session.query(BookingLink).filter_by(id=booking.link_id).first()
            )
            if not booking_link:
                return False

            owner_user_id = booking_link.owner_user_id

            # Check if follow-up is enabled in the template
            if booking_link.template_id is not None:
                from services.meetings.models.bookings import BookingTemplate

                template = (
                    session.query(BookingTemplate)
                    .filter_by(id=booking_link.template_id)
                    .first()
                )
                if template is None or not template.email_followup_enabled:
                    return True  # Follow-up not enabled, consider this successful

        # Send follow-up email
        title = "Meeting Follow-up"
        await send_optional_followup(
            user_id=owner_user_id,  # type: ignore[arg-type]
            recipient_email=booking.attendee_email,
            title=title,
        )

        return True

    except Exception as e:
        # Log the error but don't fail the booking creation
        # In production, this should use proper logging
        print(f"Failed to send follow-up email for booking {booking.id}: {e}")
        return False


async def send_booking_confirmations(
    user_id: str,
    owner_email: str,
    recipient_email: str,
    title: str,
    start_time: datetime,
    end_time: datetime,
    location: Optional[str],
    answers: Optional[Dict[str, str]] = None,
) -> None:
    """
    Send confirmation emails to both owner and recipient.
    """
    start_s = _format_dt(start_time)
    end_s = _format_dt(end_time)

    details_lines = [
        f"Title: {title}",
        f"Start: {start_s}",
        f"End: {end_s}",
    ]
    if location:
        details_lines.append(f"Location: {location}")
    if answers:
        details_lines.append("")
        details_lines.append("Responses:")
        for k, v in answers.items():
            details_lines.append(f"- {k}: {v}")

    body = "\n".join(details_lines)
    subject = f"Meeting confirmed: {title}"

    # Send to recipient
    await email_integration.send_invitation_email(
        recipient_email, subject, body, user_id
    )
    # Send to owner
    await email_integration.send_invitation_email(owner_email, subject, body, user_id)


async def send_optional_followup(
    user_id: str,
    recipient_email: str,
    title: str,
) -> None:
    """
    Send an optional short follow-up email when enabled in the template.
    """
    subject = f"Follow-up: {title}"
    body = "Thanks for booking. If you need to reschedule, reply to this email or use your link."
    await email_integration.send_invitation_email(
        recipient_email, subject, body, user_id
    )
