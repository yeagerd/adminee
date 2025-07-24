import os
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from ..models import MeetingPoll as MeetingPollModel
from ..models import PollParticipant as PollParticipantModel
from ..models import (
    get_session,
)
from ..services import email_integration

router = APIRouter()


@router.post("/")
async def send_invitations(poll_id: UUID, request: Request):
    with get_session() as session:
        poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        participants = (
            session.query(PollParticipantModel).filter_by(poll_id=poll_id).all()
        )
        user_id = request.headers.get("X-User-Id") or str(poll.user_id)
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
        poll_url = f"{frontend_url}/public/polls/{poll.poll_token}"
        subject = f"You're invited: {poll.title}"
        body = f"You have been invited to respond to a meeting poll: {poll.title}\n\n{poll.description or ''}\n\nRespond here: {poll_url}"
        # Send emails asynchronously
        for participant in participants:
            await email_integration.send_invitation_email(
                participant.email, subject, body, user_id
            )
            participant.status = "pending"  # Mark as invited
        session.commit()
    return {"ok": True, "sent": [p.email for p in participants]}
