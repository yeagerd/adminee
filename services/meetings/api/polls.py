from datetime import datetime, timedelta
from typing import List
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request

from services.meetings.models import MeetingPoll as MeetingPollModel
from services.meetings.models import PollParticipant as PollParticipantModel
from services.meetings.models import TimeSlot as TimeSlotModel
from services.meetings.models import get_session
from services.meetings.schemas import MeetingPoll, MeetingPollCreate
from services.meetings.services import calendar_integration

router = APIRouter()


def get_user_id_from_request(request: Request) -> UUID:
    """
    Extract user ID from request headers.

    The meetings service expects user identity via X-User-Id header.
    """
    user_id_str = request.headers.get("X-User-Id")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    try:
        return UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-User-Id format")


@router.get("/", response_model=List[MeetingPoll])
def list_polls() -> List[MeetingPoll]:
    with get_session() as session:
        polls = session.query(MeetingPollModel).all()
        return [MeetingPoll.model_validate(p) for p in polls]


@router.get("/{poll_id}", response_model=MeetingPoll)
def get_poll(poll_id: UUID) -> MeetingPoll:
    with get_session() as session:
        poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        return MeetingPoll.model_validate(poll)


@router.post("/", response_model=MeetingPoll)
def create_poll(poll: MeetingPollCreate, request: Request) -> MeetingPoll:
    user_id = get_user_id_from_request(request)
    with get_session() as session:
        poll_token = uuid4().hex
        db_poll = MeetingPollModel(
            id=uuid4(),
            user_id=user_id,  # Use actual user context
            title=poll.title,
            description=poll.description,
            duration_minutes=poll.duration_minutes,
            location=poll.location,
            meeting_type=poll.meeting_type,
            response_deadline=poll.response_deadline,
            min_participants=poll.min_participants or 1,
            max_participants=poll.max_participants,
            allow_anonymous_responses=poll.allow_anonymous_responses or False,
            poll_token=str(poll_token),
        )
        session.add(db_poll)
        session.flush()
        # Add time slots
        for slot in poll.time_slots:
            db_slot = TimeSlotModel(
                id=uuid4(),
                poll_id=db_poll.id,
                start_time=slot.start_time,
                end_time=slot.end_time,
                timezone=slot.timezone,
            )
            session.add(db_slot)
        # Add participants
        for part in poll.participants:
            response_token = part.response_token or uuid4().hex
            db_part = PollParticipantModel(
                id=uuid4(),
                poll_id=db_poll.id,  # type: ignore[assignment]
                email=part.email,
                name=part.name,
                response_token=response_token,
            )
            session.add(db_part)
        session.commit()
        session.refresh(db_poll)
        return MeetingPoll.model_validate(db_poll)


@router.put("/{poll_id}", response_model=MeetingPoll)
def update_poll(
    poll_id: UUID, poll: MeetingPollCreate, request: Request
) -> MeetingPoll:
    user_id = get_user_id_from_request(request)
    with get_session() as session:
        db_poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not db_poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        # Ownership check: only the poll creator can update
        if str(db_poll.user_id) != str(user_id):
            raise HTTPException(
                status_code=403, detail="Not authorized to update this poll"
            )
        db_poll.title = poll.title  # type: ignore[assignment]
        db_poll.description = poll.description  # type: ignore[assignment]
        db_poll.duration_minutes = poll.duration_minutes  # type: ignore[assignment]
        db_poll.location = poll.location  # type: ignore[assignment]
        db_poll.meeting_type = poll.meeting_type  # type: ignore[assignment]
        db_poll.response_deadline = poll.response_deadline  # type: ignore[assignment]
        db_poll.min_participants = poll.min_participants or 1  # type: ignore[assignment]
        db_poll.max_participants = poll.max_participants  # type: ignore[assignment]
        db_poll.allow_anonymous_responses = poll.allow_anonymous_responses or False  # type: ignore[assignment]
        # TODO: update time slots and participants as needed
        session.commit()
        session.refresh(db_poll)
        return MeetingPoll.model_validate(db_poll)


@router.delete("/{poll_id}")
def delete_poll(poll_id: UUID, request: Request) -> dict:
    user_id = get_user_id_from_request(request)
    with get_session() as session:
        db_poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not db_poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        # Ownership check: only the poll creator can delete
        if str(db_poll.user_id) != str(user_id):
            raise HTTPException(
                status_code=403, detail="Not authorized to delete this poll"
            )
        session.delete(db_poll)
        session.commit()
        return {"ok": True}


@router.get("/{poll_id}/suggest-slots")
async def suggest_slots(poll_id: UUID, request: Request) -> dict:
    user_id = get_user_id_from_request(request)
    # For demo, use poll duration and a 2-week window
    with get_session() as session:
        poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        duration = int(poll.duration_minutes)
    start = datetime.utcnow().isoformat()
    end = (datetime.utcnow() + timedelta(days=14)).isoformat()
    slots = await calendar_integration.get_user_availability(
        str(user_id), start, end, duration
    )
    return slots


@router.post("/{poll_id}/schedule")
async def schedule_meeting(poll_id: UUID, request: Request, body: dict) -> dict:
    user_id = get_user_id_from_request(request)
    selected_slot_id = body.get("selectedSlotId")
    participants = body.get("participants", [])
    if not selected_slot_id:
        raise HTTPException(status_code=400, detail="Missing selectedSlotId")
    result = await calendar_integration.create_calendar_event(
        str(user_id), str(poll_id), selected_slot_id, participants
    )
    # Optionally update poll status to scheduled here
    with get_session() as session:
        poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if poll:
            poll.status = "scheduled"  # type: ignore[assignment]
            session.commit()
    return result
