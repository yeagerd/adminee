from uuid import uuid4

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel

from services.meetings.models import MeetingPoll as MeetingPollModel
from services.meetings.models import PollParticipant as PollParticipantModel
from services.meetings.models import PollResponse as PollResponseModel
from services.meetings.models import (
    get_session,
)
from services.meetings.schemas import PollResponseCreate

router = APIRouter()


@router.get("/{token}")
def get_public_poll(token: str):
    with get_session() as session:
        poll = session.query(MeetingPollModel).filter_by(poll_token=token).first()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        return poll


class PollResponseTokenRequest(BaseModel):
    responses: list[PollResponseCreate]


@router.put("/meetings/response/{response_token}", status_code=status.HTTP_200_OK)
def respond_with_token(response_token: str, req: PollResponseTokenRequest = Body(...)):
    with get_session() as session:
        participant = (
            session.query(PollParticipantModel)
            .filter_by(response_token=response_token)
            .first()
        )
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        poll = session.query(MeetingPollModel).filter_by(id=participant.poll_id).first()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")
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
