import datetime
import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from services.common.api_key_auth import (
    APIKeyConfig,
    build_api_key_mapping,
    get_api_key_from_request,
    verify_api_key,
)
from services.meetings.models import (
    MeetingPoll,
    PollParticipant,
    PollResponse,
    get_session,
)
from services.meetings.models.meeting import ParticipantStatus, ResponseType
from services.meetings.settings import get_settings

router = APIRouter()

API_KEY_CONFIGS = {
    "email_sync": APIKeyConfig(
        client="email_sync",
        service="meetings",
        permissions=["email:sync"],
        settings_key="api_email_sync_meetings_key",
    ),
}


class EmailResponseRequest(BaseModel):
    emailId: str
    content: str
    sender: str


# Result object for parsed email content
class EmailContentParseResult(BaseModel):
    response: str | None
    comment: str | None


def parse_email_content(content: str) -> EmailContentParseResult:
    """
    Dummy parser: expects content to be of the form:
    RESPONSE: <available|unavailable|maybe> [OPTIONAL_COMMENT]
    """
    lines = content.strip().splitlines()
    if not lines:
        return EmailContentParseResult(response=None, comment=None)
    first = lines[0].strip().lower()
    if first.startswith("response:"):
        parts = first[len("response:") :].strip().split(None, 1)
        if not parts:
            return EmailContentParseResult(response=None, comment=None)
        response = parts[0]
        comment = parts[1] if len(parts) > 1 else None
        return EmailContentParseResult(response=response, comment=comment)
    return EmailContentParseResult(response=None, comment=None)


@router.post("/")
def process_email_response(req: EmailResponseRequest, request: Request) -> Response:
    api_key_mapping = build_api_key_mapping(API_KEY_CONFIGS, get_settings)
    api_key = get_api_key_from_request(request)
    if not api_key or not verify_api_key(api_key, api_key_mapping):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    # Parse email content
    parsed = parse_email_content(req.content)
    if parsed.response not in {"available", "unavailable", "maybe"}:
        raise HTTPException(
            status_code=400, detail="Could not parse response from email content."
        )

    # Find participant by sender email
    with get_session() as session:
        participant = session.query(PollParticipant).filter_by(email=req.sender).first()
        if not participant:
            raise HTTPException(
                status_code=404, detail="Participant not found for sender email."
            )
        poll = session.query(MeetingPoll).filter_by(id=participant.poll_id).first()
        if not poll:
            raise HTTPException(
                status_code=404, detail="Poll not found for participant."
            )
        # For each time slot, create/update a response (for demo, mark all slots with the same response)
        for slot in poll.time_slots:
            existing = (
                session.query(PollResponse)
                .filter_by(participant_id=participant.id, time_slot_id=slot.id)
                .first()
            )
            if existing:
                existing.response = ResponseType(parsed.response).value  # type: ignore[assignment]
                existing.comment = parsed.comment  # type: ignore[assignment]
                existing.updated_at = datetime.datetime.utcnow()  # type: ignore[assignment]
            else:
                resp = PollResponse(
                    id=uuid4(),
                    poll_id=poll.id,
                    participant_id=participant.id,
                    time_slot_id=slot.id,
                    response=ResponseType(parsed.response).value,  # type: ignore[assignment]
                    comment=parsed.comment,  # type: ignore[assignment]
                )
                session.add(resp)
        participant.status = ParticipantStatus.responded.value  # type: ignore[assignment]
        participant.responded_at = datetime.datetime.utcnow()  # type: ignore[assignment]
        session.commit()
        logging.info(
            f"Processed email response from {req.sender}: {parsed.response} ({parsed.comment})"
        )
        return Response(status_code=200)
