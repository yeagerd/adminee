from datetime import datetime, timedelta
from typing import List
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request

from ..models import MeetingPoll as MeetingPollModel
from ..models import PollParticipant as PollParticipantModel
from ..models import TimeSlot as TimeSlotModel
from ..models import (
    get_session,
)
from ..schemas import MeetingPoll, MeetingPollCreate
from ..services import calendar_integration

router = APIRouter()


@router.get("/", response_model=List[MeetingPoll])
def list_polls():
    with get_session() as session:
        polls = session.query(MeetingPollModel).all()
        return polls


@router.get("/{poll_id}", response_model=MeetingPoll)
def get_poll(poll_id: UUID):
    with get_session() as session:
        poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        return poll


@router.post("/", response_model=MeetingPoll)
def create_poll(poll: MeetingPollCreate, request: Request):
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
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
            poll_token=poll_token,
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
            db_part = PollParticipantModel(
                id=uuid4(),
                poll_id=db_poll.id,
                email=part.email,
                name=part.name,
            )
            session.add(db_part)
        session.commit()
        session.refresh(db_poll)
        return db_poll


@router.put("/{poll_id}", response_model=MeetingPoll)
def update_poll(poll_id: UUID, poll: MeetingPollCreate, request: Request):
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    with get_session() as session:
        db_poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not db_poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        # Ownership check: only the poll creator can update
        if str(db_poll.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Not authorized to update this poll")
        db_poll.title = poll.title
        db_poll.description = poll.description
        db_poll.duration_minutes = poll.duration_minutes
        db_poll.location = poll.location
        db_poll.meeting_type = poll.meeting_type
        db_poll.response_deadline = poll.response_deadline
        db_poll.min_participants = poll.min_participants or 1
        db_poll.max_participants = poll.max_participants
        db_poll.allow_anonymous_responses = poll.allow_anonymous_responses or False
        # TODO: update time slots and participants as needed
        session.commit()
        session.refresh(db_poll)
        return db_poll


@router.delete("/{poll_id}")
def delete_poll(poll_id: UUID, request: Request):
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    with get_session() as session:
        db_poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not db_poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        # Ownership check: only the poll creator can delete
        if str(db_poll.user_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Not authorized to delete this poll")
        session.delete(db_poll)
        session.commit()
        return {"ok": True}


@router.get("/{poll_id}/suggest-slots")
async def suggest_slots(poll_id: UUID, request: Request):
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    # For demo, use poll duration and a 2-week window
    with get_session() as session:
        poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        duration = poll.duration_minutes
    start = datetime.utcnow().isoformat()
    end = (datetime.utcnow() + timedelta(days=14)).isoformat()
    slots = await calendar_integration.get_user_availability(
        user_id, start, end, duration
    )
    return slots


@router.post("/{poll_id}/schedule")
async def schedule_meeting(poll_id: UUID, request: Request, body: dict):
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing X-User-Id header")
    selected_slot_id = body.get("selectedSlotId")
    participants = body.get("participants", [])
    if not selected_slot_id:
        raise HTTPException(status_code=400, detail="Missing selectedSlotId")
    result = await calendar_integration.create_calendar_event(
        user_id, str(poll_id), selected_slot_id, participants
    )
    # Optionally update poll status to scheduled here
    with get_session() as session:
        poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if poll:
            poll.status = "scheduled"
            session.commit()
    return result
