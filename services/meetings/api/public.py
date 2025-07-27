from uuid import uuid4

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel

from services.meetings.models import MeetingPoll as MeetingPollModel
from services.meetings.models import PollParticipant as PollParticipantModel
from services.meetings.models import PollResponse as PollResponseModel
from services.meetings.models import (
    get_session,
)
from services.meetings.models.meeting import ParticipantStatus
from services.meetings.schemas import MeetingPoll, PollResponseCreate

router = APIRouter()


@router.get("/response/{response_token}")
def get_poll_by_response_token(response_token: str) -> dict:
    """Get poll data for a specific response token."""
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

        return {
            "poll": MeetingPoll.model_validate(poll),
            "participant": {
                "id": str(participant.id),
                "email": participant.email,
                "name": participant.name,
                "status": participant.status.value,
            },
        }


class PollResponseTokenRequest(BaseModel):
    responses: list[PollResponseCreate]


@router.put("/response/{response_token}", status_code=status.HTTP_200_OK)
def respond_with_token(
    response_token: str, req: PollResponseTokenRequest = Body(...)
) -> dict:
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

        # Clear existing responses for this participant
        session.query(PollResponseModel).filter_by(
            participant_id=participant.id
        ).delete()

        # Add new responses
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

        participant.status = ParticipantStatus.responded
        session.commit()
        return {"ok": True}
