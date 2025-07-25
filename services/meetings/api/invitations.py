import os
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from services.meetings.models import MeetingPoll as MeetingPollModel
from services.meetings.models import PollParticipant as PollParticipantModel
from services.meetings.models import get_session
from services.meetings.services import email_integration

router = APIRouter()


@router.post("/")
async def send_invitations(poll_id: UUID, request: Request) -> dict:
    with get_session() as session:
        poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        participants = (
            session.query(PollParticipantModel).filter_by(poll_id=poll_id).all()
        )
        user_id = request.headers.get("X-User-Id") or str(poll.user_id)
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
        # Send emails asynchronously
        for participant in participants:
            response_url = (
                f"{frontend_url}/public/meetings/respond/{participant.response_token}"
            )
            subject = f"You're invited: {poll.title}"
            body = f"You have been invited to respond to a meeting poll: {poll.title}\n\n{poll.description or ''}\n\nRespond here: {response_url}"
            await email_integration.send_invitation_email(
                participant.email, subject, body, user_id  # type: ignore[arg-type]
            )
            participant.status = "pending"  # type: ignore[assignment]
        session.commit()
    return {"ok": True, "sent": [p.email for p in participants]}
