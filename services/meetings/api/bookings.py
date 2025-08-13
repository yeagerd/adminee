from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from services.meetings.models import get_session
from services.meetings.models.bookings import (
    BookingLink as BookingLinkModel,
    BookingTemplate as BookingTemplateModel,
    Booking as BookingModel,
    OneTimeLink as OneTimeLinkModel,
)
from services.meetings.services.booking_availability import compute_available_slots
from services.meetings.services.booking_emails import (
    send_booking_confirmations,
    send_optional_followup,
)
from services.meetings.services.booking_events import create_owner_calendar_event


router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/public/{token}")
def get_public_link(token: str) -> dict:
    with get_session() as session:
        link = session.query(OneTimeLinkModel).filter_by(token=token).first()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        expires_at = getattr(link, "expires_at", None)
        status = getattr(link, "status", "active")
        if (expires_at and expires_at < datetime.now(timezone.utc)) or status != "active":
            raise HTTPException(status_code=404, detail="Link expired or inactive")

        # Load template if present
        parent = (
            session.query(BookingLinkModel)
            .filter_by(id=getattr(link, "booking_link_id"))
            .first()
        )
        template_questions = None
        if parent and getattr(parent, "template_id", None):
            tmpl = (
                session.query(BookingTemplateModel)
                .filter_by(id=getattr(parent, "template_id"))
                .first()
            )
            if tmpl and getattr(tmpl, "questions", None):
                template_questions = getattr(tmpl, "questions")

        return {
            "ok": True,
            "data": {
                "token": token,
                "booking_link_id": str(getattr(link, "booking_link_id", "")),
                "status": status,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "template_questions": template_questions,
            },
        }


@router.get("/public/{token}/availability")
async def get_public_availability(
    token: str,
    duration: int = Query(30, ge=5, le=240),
    days_ahead: int = Query(14, ge=1, le=60),
) -> dict:
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(days=days_ahead)

    with get_session() as session:
        link = session.query(OneTimeLinkModel).filter_by(token=token).first()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        expires_at = getattr(link, "expires_at", None)
        status = getattr(link, "status", "active")
        if (expires_at and expires_at < datetime.now(timezone.utc)) or status != "active":
            raise HTTPException(status_code=404, detail="Link expired or inactive")

        # Resolve owner and settings from parent BookingLink
        parent = (
            session.query(BookingLinkModel)
            .filter_by(id=getattr(link, "booking_link_id"))
            .first()
        )
        if not parent:
            raise HTTPException(status_code=404, detail="Parent link not found")

        owner_user_id = str(getattr(parent, "owner_user_id"))

    availability = await compute_available_slots(
        owner_user_id,
        start,
        end,
        duration,
    )

    # Normalize to a standard response with slots list
    slots = []
    if isinstance(availability, dict):
        if "slots" in availability and isinstance(availability["slots"], list):
            slots = availability["slots"]
        elif "data" in availability and isinstance(availability["data"], dict):
            maybe = availability["data"].get("slots")
            if isinstance(maybe, list):
                slots = maybe

    return {"ok": True, "data": {"slots": slots}}


@router.post("/public/{token}/book")
async def submit_booking(token: str, body: dict) -> dict:
    """
    Create a booking for a selected slot.
    Body must include: { start: iso, end: iso, attendeeEmail: string, answers?: dict }
    """
    start_raw = body.get("start")
    end_raw = body.get("end")
    attendee_email = body.get("attendeeEmail")
    answers = body.get("answers") or {}
    if not (start_raw and end_raw and attendee_email):
        raise HTTPException(status_code=400, detail="Missing required fields")

    try:
        start = datetime.fromisoformat(start_raw)
        end = datetime.fromisoformat(end_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid datetime format")

    with get_session() as session:
        link = session.query(OneTimeLinkModel).filter_by(token=token).first()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        # Validate link status
        expires_at = getattr(link, "expires_at", None)
        status = getattr(link, "status", "active")
        if (expires_at and expires_at < datetime.now(timezone.utc)) or status != "active":
            raise HTTPException(status_code=404, detail="Link expired or inactive")

        parent = (
            session.query(BookingLinkModel)
            .filter_by(id=getattr(link, "booking_link_id"))
            .first()
        )
        if not parent:
            raise HTTPException(status_code=404, detail="Parent link not found")

        owner_user_id = str(getattr(parent, "owner_user_id"))
        title = "Meeting"
        location = None

        # Create calendar event
        result = await create_owner_calendar_event(
            owner_user_id,
            title,
            None,
            start,
            end,
            [attendee_email],
            location,
        )
        event_id = None
        try:
            data = result.get("data", {}) if isinstance(result, dict) else {}
            event_id = data.get("event_id")
        except Exception:
            pass

        # Persist booking
        booking = BookingModel(
            link_id=getattr(parent, "id"),
            one_time_link_id=getattr(link, "id"),
            start_at=start,
            end_at=end,
            attendee_email=attendee_email,
            answers=answers,
            calendar_event_id=event_id,
        )
        session.add(booking)

        # Mark one-time link inactive
        setattr(link, "status", "used")
        session.commit()

    # Send emails
    try:
        await send_booking_confirmations(
            owner_user_id,
            owner_email="noreply@example.com",  # TODO: resolve owner email via User service
            recipient_email=attendee_email,
            title=title,
            start_time=start,
            end_time=end,
            location=location,
            answers=answers,
        )
        # Optionally: send follow-up if enabled in template (omitted here for brevity)
    except Exception:
        # Do not fail booking on email errors
        pass

    return {"ok": True}


