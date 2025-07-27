import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from services.common.api_key_auth import (
    APIKeyConfig,
    build_api_key_mapping,
    get_api_key_from_request,
    verify_api_key,
)
from services.meetings.api.polls import get_user_id_from_request
from services.meetings.models import MeetingPoll as MeetingPollModel
from services.meetings.models import PollParticipant as PollParticipantModel
from services.meetings.models import get_session
from services.meetings.models.meeting import ParticipantStatus
from services.meetings.services import email_integration
from services.meetings.settings import get_settings

router = APIRouter()

# API Key configurations
API_KEY_CONFIGS = {
    "frontend": APIKeyConfig(
        client="frontend",
        service="meetings",
        permissions=["meetings:read", "meetings:write", "meetings:send_invitations"],
        settings_key="api_frontend_meetings_key",
    ),
}


def verify_api_key_auth(request: Request) -> str:
    """
    Verify API key authentication and return the service name.
    """
    api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
    api_key = get_api_key_from_request(request)
    if not api_key or not verify_api_key(api_key, api_key_mapping):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )
    return "frontend"


@router.post("/")
async def send_invitations(
    poll_id: UUID, request: Request, service_name: str = Depends(verify_api_key_auth)
) -> dict:
    user_id = get_user_id_from_request(request)

    with get_session() as session:
        poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")

        # Check that the user owns the poll
        if str(poll.user_id) != str(user_id):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to send invitations for this poll",
            )

        participants = (
            session.query(PollParticipantModel).filter_by(poll_id=poll_id).all()
        )
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")

        # Send emails and track results
        sent_emails = []
        failed_emails = []

        for participant in participants:
            response_url = f"{frontend_url}/public/meetings/respond/{getattr(participant, 'response_token')}"
            subject = f"You're invited: {poll.title}"
            description = getattr(poll, "description", "") or ""

            # Build email body
            body = f"You have been invited to respond to a meeting poll: {poll.title}\n\n{description}\n\nRespond here: {response_url}"

            # Add participant list if reveal_participants is enabled
            if bool(poll.reveal_participants):  # type: ignore[arg-type]
                body += "\n\nOther participants:\n"
                for other_participant in participants:
                    if (
                        other_participant.id != participant.id
                    ):  # Don't include the current participant
                        name = getattr(other_participant, "name", None) or "Unknown"
                        email = getattr(other_participant, "email", "")
                        body += f"- {name} ({email})\n"

            try:
                await email_integration.send_invitation_email(
                    getattr(participant, "email"), subject, body, user_id  # type: ignore[arg-type]
                )
                setattr(participant, "status", ParticipantStatus.pending)
                sent_emails.append(getattr(participant, "email"))
            except ValueError as e:
                # Email sending failed - don't update participant status
                failed_emails.append(
                    {"email": getattr(participant, "email"), "error": str(e)}
                )

        session.commit()

        # Return results
        result = {
            "ok": len(failed_emails) == 0,
            "sent": sent_emails,
            "failed": failed_emails,
            "total_participants": len(participants),
            "successful_sends": len(sent_emails),
            "failed_sends": len(failed_emails),
        }

        # If any emails failed, return a 400 status with details
        if len(failed_emails) > 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Some invitation emails could not be sent",
                    "results": result,
                },
            )

        return result
