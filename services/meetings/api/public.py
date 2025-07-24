from uuid import uuid4

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, EmailStr, Field

from ..models import MeetingPoll as MeetingPollModel
from ..models import PollParticipant as PollParticipantModel
from ..models import PollResponse as PollResponseModel
from ..models import (
    get_session,
)
from ..schemas import PollResponseCreate

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
        participant = (
            session.query(PollParticipantModel)
            .filter_by(poll_id=poll.id, email=req.participant_email)
            .first()
        )
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
