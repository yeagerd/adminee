from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from services.meetings.models import get_session
from services.meetings.models.bookings import (
    BookingLink as BookingLinkModel,
    OneTimeLink as OneTimeLinkModel,
)
from services.meetings.services.booking_availability import compute_available_slots


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

        return {
            "ok": True,
            "data": {
                "token": token,
                "booking_link_id": str(getattr(link, "booking_link_id", "")),
                "status": status,
                "expires_at": expires_at.isoformat() if expires_at else None,
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


