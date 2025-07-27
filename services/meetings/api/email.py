import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from services.common.api_key_auth import (
    APIKeyConfig,
    build_api_key_mapping,
    get_api_key_from_request,
    verify_api_key,
)
from services.common.logging_config import get_logger
from services.meetings.models import (
    MeetingPoll,
    PollParticipant,
    PollResponse,
    TimeSlot,
    get_session,
)
from services.meetings.models.meeting import ParticipantStatus, ResponseType
from services.meetings.settings import get_settings

# Configure logging
logger = get_logger(__name__)

router = APIRouter()

API_KEY_CONFIGS = {
    "email_sync": APIKeyConfig(
        client="email_sync",
        service="meetings",
        permissions=["email:sync"],
        settings_key="api_email_sync_meetings_key",
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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return "email_sync"


class EmailResponseRequest(BaseModel):
    emailId: str
    content: str
    sender: str


# Result object for parsed email content
class EmailContentParseResult(BaseModel):
    slot_responses: dict[
        str, dict[str, str | None]
    ]  # slot_id -> {"response": str, "comment": str | None}


def parse_email_content(content: str) -> EmailContentParseResult:
    """
    Parse email content for slot-specific responses.
    Expects content to contain lines like:
    SLOT_1_123e4567-e89b-12d3-a456-426614174000: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC) - available - I prefer this time slot
    """
    slot_responses = {}
    lines = content.strip().splitlines()

    for line in lines:
        line = line.strip()
        if not line or not line.startswith("SLOT_"):
            continue

        # Parse slot response line
        # Format: SLOT_1_123e4567-e89b-12d3-a456-426614174000: Monday, January 15, 2024 at 2:00 PM - 3:00 PM (UTC) - available - I prefer this time slot
        try:
            # Split on first colon to separate slot identifier from response
            parts = line.split(":", 1)
            if len(parts) != 2:
                continue

            slot_identifier = parts[0].strip()
            response_part = parts[1].strip()

            # Extract slot ID from identifier (SLOT_1_123e4567-e89b-12d3-a456-426614174000)
            slot_id = (
                slot_identifier.split("_", 2)[2] if "_" in slot_identifier else None
            )
            if not slot_id:
                continue

            # Parse response and comment
            # Check if any response keyword is in the response part
            response_keywords = ["available", "unavailable", "maybe"]
            response = None
            comment = None

            # Check if any response keyword is in the response part
            for keyword in response_keywords:
                # Use word boundaries to avoid partial matches
                import re

                pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
                if re.search(pattern, response_part.lower()):
                    response = keyword.lower()
                    # Extract comment (everything after the response keyword)
                    keyword_index = response_part.lower().find(keyword.lower())
                    if keyword_index != -1:
                        comment_start = keyword_index + len(keyword)
                        if comment_start < len(response_part):
                            comment = response_part[comment_start:].strip()
                            if comment.startswith("-"):
                                comment = comment[1:].strip()
                            if comment.startswith(" "):
                                comment = comment[1:]
                            # If comment is empty after trimming, set to None
                            if not comment:
                                comment = None
                    break

            if response:
                slot_responses[slot_id] = {"response": response, "comment": comment}

        except Exception as e:
            # Log parsing errors but continue processing other lines
            logger.warning(f"Failed to parse line: {line}", error=str(e))
            continue

    return EmailContentParseResult(slot_responses=slot_responses)


@router.post("/")
def process_email_response(
    req: EmailResponseRequest,
    request: Request,
    service_name: str = Depends(verify_api_key_auth),
) -> Response:

    # Parse email content
    parsed = parse_email_content(req.content)
    if not parsed.slot_responses:
        raise HTTPException(
            status_code=400,
            detail="Could not parse any slot responses from email content.",
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

        # Process each slot response
        processed_slots = 0
        for slot_id, response_data in parsed.slot_responses.items():
            response_value = response_data.get("response")
            comment = response_data.get("comment")

            if response_value not in {"available", "unavailable", "maybe"}:
                logger.warning(
                    f"Invalid response value: {response_value} for slot {slot_id}"
                )
                continue

            # Find the time slot by ID
            slot = (
                session.query(TimeSlot)
                .filter_by(id=UUID(slot_id), poll_id=poll.id)
                .first()
            )
            if not slot:
                logger.warning(f"Time slot {slot_id} not found for poll {poll.id}")
                continue

            # Create or update response for this slot
            existing = (
                session.query(PollResponse)
                .filter_by(participant_id=participant.id, time_slot_id=slot.id)
                .first()
            )
            if existing:
                existing.response = ResponseType(response_value)
                existing.comment = comment  # type: ignore[assignment]
                existing.updated_at = datetime.datetime.utcnow()  # type: ignore[assignment]
            else:
                resp = PollResponse(
                    id=uuid4(),
                    poll_id=poll.id,
                    participant_id=participant.id,
                    time_slot_id=slot.id,
                    response=ResponseType(response_value),
                    comment=comment,  # type: ignore[assignment]
                )
                session.add(resp)
            processed_slots += 1

        # Update participant status if we processed any responses
        if processed_slots > 0:
            participant.status = ParticipantStatus.responded
            participant.responded_at = datetime.datetime.utcnow()  # type: ignore[assignment]

        session.commit()
        logger.info(
            "Processed email response",
            sender=req.sender,
            processed_slots=processed_slots,
            total_slots=len(parsed.slot_responses),
            poll_id=str(poll.id),
            participant_id=str(participant.id),
        )
        return Response(status_code=200)
