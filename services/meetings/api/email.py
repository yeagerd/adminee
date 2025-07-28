import datetime
from uuid import uuid4

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
    Expects users to move slots under headings like "I'm AVAILABLE:", "I'm UNAVAILABLE:", "I'm MAYBE:"
    """
    slot_responses = {}
    lines = content.strip().splitlines()

    # Track current section for new format
    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for section headers in new format
        if line.upper() in ["I'M AVAILABLE:", "I'M UNAVAILABLE:", "I'M MAYBE:"]:
            current_section = line.upper().replace("I'M ", "").replace(":", "").lower()
            continue

        # Skip lines that don't start with SLOT_
        if not line.startswith("SLOT_"):
            continue

        # Parse slot response line
        try:
            # Split on first colon to separate slot identifier from response
            parts = line.split(":", 1)
            if len(parts) != 2:
                continue

            slot_identifier = parts[0].strip()
            response_part = parts[1].strip()

            # Extract slot number from identifier (SLOT_1)
            if not slot_identifier.startswith("SLOT_"):
                continue

            slot_number_str = slot_identifier[5:]  # Remove "SLOT_" prefix
            if not slot_number_str:
                continue

            try:
                slot_number = int(slot_number_str)
                if slot_number < 1:
                    continue
            except ValueError:
                # Skip invalid slot numbers
                continue

            response = None
            comment = None

            # Handle slots under headings format
            if current_section:
                response = current_section
                # Extract comment if present (after timezone)
                # Look for dash after timezone pattern like "(UTC)" or "(EST)"
                import re

                timezone_pattern = r"\([^)]+\)\s*-\s*"
                match = re.search(timezone_pattern, response_part)
                if match:
                    # Extract comment after the timezone and dash
                    comment_start = match.end()
                    if comment_start < len(response_part):
                        comment = response_part[comment_start:].strip()
                        if (
                            not comment
                        ):  # If comment is empty after trimming, set to None
                            comment = None
                else:
                    comment = None
            else:
                # Skip slots that aren't under any heading
                continue

            if response:
                slot_responses[str(slot_number)] = {
                    "response": response,
                    "comment": comment,
                }

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
        for slot_number_str, response_data in parsed.slot_responses.items():
            response_value = response_data.get("response")
            comment = response_data.get("comment")

            if response_value not in {"available", "unavailable", "maybe"}:
                logger.warning(
                    f"Invalid response value: {response_value} for slot {slot_number_str}"
                )
                continue

            # Convert slot number to integer
            try:
                slot_number = int(slot_number_str)
                if slot_number < 1 or slot_number > len(poll.time_slots):
                    logger.warning(
                        f"Invalid slot number: {slot_number} (valid range: 1-{len(poll.time_slots)})"
                    )
                    continue
            except ValueError:
                logger.warning(f"Invalid slot number format: {slot_number_str}")
                continue

            # Get the time slot by its position (1-indexed)
            slot = poll.time_slots[slot_number - 1]  # Convert to 0-indexed
            if not slot:
                logger.warning(f"Time slot {slot_number} not found for poll {poll.id}")
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
                existing.updated_at = datetime.datetime.now(datetime.timezone.utc)  # type: ignore[assignment]
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
            participant.responded_at = datetime.datetime.now(datetime.timezone.utc)  # type: ignore[assignment]

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
