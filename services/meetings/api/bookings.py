from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from services.meetings.models import get_session
from services.meetings.models.bookings import OneTimeLink as OneTimeLinkModel


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


