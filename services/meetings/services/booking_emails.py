from datetime import datetime
from typing import Dict, Optional

from services.meetings.services import email_integration


def _format_dt(dt: datetime) -> str:
    return dt.strftime("%A, %B %d, %Y at %I:%M %p %Z")


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
    body = (
        "Thanks for booking. If you need to reschedule, reply to this email or use your link."
    )
    await email_integration.send_invitation_email(
        recipient_email, subject, body, user_id
    )


