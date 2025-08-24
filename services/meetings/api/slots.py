from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from services.common.api_key_auth import (
    APIKeyConfig,
    build_api_key_mapping,
    get_api_key_from_request,
    verify_api_key,
)
from services.meetings.api.polls import get_user_id_from_request
from services.meetings.models import MeetingPoll as MeetingPollModel
from services.meetings.models import TimeSlot as TimeSlotModel
from services.meetings.models import get_session
from services.api.v1.meetings.meetings import TimeSlot, TimeSlotCreate
from services.meetings.settings import get_settings

router = APIRouter()

# API Key configurations
API_KEY_CONFIGS = {
    "frontend": APIKeyConfig(
        client="frontend",
        service="meetings",
        permissions=["meetings:read", "meetings:write"],
        settings_key="api_frontend_meetings_key",
    ),
}


def verify_api_key_auth(request: Request) -> str:
    """
    Verify API key authentication and return the service name.
    """
    api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
    api_key = get_api_key_from_request(request)
    if not api_key or not verify_api_key(api_key, api_key_mapping):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )
    return "frontend"


@router.post("/", response_model=TimeSlot)
def add_slot(
    poll_id: UUID,
    slot: TimeSlotCreate,
    request: Request,
    service_name: str = Depends(verify_api_key_auth),
) -> TimeSlot:
    user_id = get_user_id_from_request(request)

    with get_session() as session:
        # Check that the poll exists and user owns it
        poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")

        if str(poll.user_id) != str(user_id):
            raise HTTPException(
                status_code=403, detail="Not authorized to modify this poll"
            )

        db_slot = TimeSlotModel(
            id=uuid4(),
            poll_id=poll_id,
            start_time=slot.start_time,
            end_time=slot.end_time,
            timezone=slot.timezone,
        )
        session.add(db_slot)
        session.commit()
        session.refresh(db_slot)
        return TimeSlot.model_validate(db_slot)


@router.put("/{slot_id}", response_model=TimeSlot)
def update_slot(
    poll_id: UUID,
    slot_id: UUID,
    slot: TimeSlotCreate,
    request: Request,
    service_name: str = Depends(verify_api_key_auth),
) -> TimeSlot:
    user_id = get_user_id_from_request(request)

    with get_session() as session:
        # Check that the poll exists and user owns it
        poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")

        if str(poll.user_id) != str(user_id):
            raise HTTPException(
                status_code=403, detail="Not authorized to modify this poll"
            )

        db_slot = (
            session.query(TimeSlotModel).filter_by(id=slot_id, poll_id=poll_id).first()
        )
        if not db_slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        db_slot.start_time = slot.start_time  # type: ignore[assignment]
        db_slot.end_time = slot.end_time  # type: ignore[assignment]
        db_slot.timezone = slot.timezone  # type: ignore[assignment]
        session.commit()
        session.refresh(db_slot)
        return TimeSlot.model_validate(db_slot)


@router.delete("/{slot_id}")
def delete_slot(
    poll_id: UUID,
    slot_id: UUID,
    request: Request,
    service_name: str = Depends(verify_api_key_auth),
) -> dict:
    user_id = get_user_id_from_request(request)

    with get_session() as session:
        # Check that the poll exists and user owns it
        poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")

        if str(poll.user_id) != str(user_id):
            raise HTTPException(
                status_code=403, detail="Not authorized to modify this poll"
            )

        db_slot = (
            session.query(TimeSlotModel).filter_by(id=slot_id, poll_id=poll_id).first()
        )
        if not db_slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        session.delete(db_slot)
        session.commit()
        return {"ok": True}
