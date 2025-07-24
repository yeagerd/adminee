from fastapi import APIRouter, HTTPException, Body
from uuid import UUID, uuid4
from pydantic import BaseModel, EmailStr, Field
from ..schemas import PollResponseCreate
from ..models import MeetingPoll as MeetingPollModel, PollParticipant as PollParticipantModel, PollResponse as PollResponseModel, get_session
from typing import List

router = APIRouter()

@router.get("/{token}")
def get_public_poll(token: str):
    with get_session() as session:
        poll = session.query(MeetingPollModel).filter_by(poll_token=token).first()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        return poll

class PollResponseRequest(BaseModel):
    participant_email: EmailStr = Field(..., alias="participantEmail")
    responses: list[PollResponseCreate]

@router.post("/{token}/respond")
def respond_to_poll(token: str, req: PollResponseRequest = Body(...)):
    with get_session() as session:
        poll = session.query(MeetingPollModel).filter_by(poll_token=token).first()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        participant = session.query(PollParticipantModel).filter_by(poll_id=poll.id, email=req.participant_email).first()
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        for resp in req.responses:
            db_resp = PollResponseModel(
                id=uuid4(),
                poll_id=poll.id,
                participant_id=participant.id,
                time_slot_id=resp.time_slot_id,
                response=resp.response,
                comment=resp.comment,
            )
            session.add(db_resp)
        participant.status = "responded"
        session.commit()
        return {"ok": True} 