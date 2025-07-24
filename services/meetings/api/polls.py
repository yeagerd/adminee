from fastapi import APIRouter, HTTPException
from uuid import UUID, uuid4
from ..schemas import MeetingPoll, MeetingPollCreate
from ..models import MeetingPoll as MeetingPollModel, TimeSlot as TimeSlotModel, PollParticipant as PollParticipantModel, get_session
from typing import List

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
def create_poll(poll: MeetingPollCreate):
    with get_session() as session:
        poll_token = uuid4().hex
        db_poll = MeetingPollModel(
            id=uuid4(),
            user_id=uuid4(),  # TODO: Replace with actual user context
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
def update_poll(poll_id: UUID, poll: MeetingPollCreate):
    with get_session() as session:
        db_poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not db_poll:
            raise HTTPException(status_code=404, detail="Poll not found")
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
def delete_poll(poll_id: UUID):
    with get_session() as session:
        db_poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not db_poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        session.delete(db_poll)
        session.commit()
        return {"ok": True} 