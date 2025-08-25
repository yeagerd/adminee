from uuid import uuid4

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel

from services.api.v1.meetings.meetings import MeetingPoll, PollResponseCreate
from services.meetings.models import MeetingPoll as MeetingPollModel
from services.meetings.models import PollParticipant as PollParticipantModel
from services.meetings.models import PollResponse as PollResponseModel
from services.meetings.models import (
    get_session,
)
from services.meetings.models.meeting import ParticipantStatus

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

        # Get existing responses for this participant
        existing_responses = (
            session.query(PollResponseModel)
            .filter_by(participant_id=participant.id)
            .all()
        )

        # Convert to the format expected by frontend
        responses = []
        for resp in existing_responses:
            comment_value = str(resp.comment) if resp.comment is not None else ""
            responses.append(
                {
                    "time_slot_id": str(resp.time_slot_id),
                    "response": resp.response.value,
                    "comment": comment_value,
                }
            )

        # Create poll data with filtered participants (exclude current participant)
        poll_data = MeetingPoll.model_validate(poll)

        # Filter out the current participant from the participants list
        if poll_data.participants:
            poll_data.participants = [
                p for p in poll_data.participants if str(p.id) != str(participant.id)
            ]

        return {
            "poll": poll_data,
            "participant": {
                "id": str(participant.id),
                "email": participant.email,
                "name": participant.name,
                "status": participant.status.value,
            },
            "responses": responses,
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
