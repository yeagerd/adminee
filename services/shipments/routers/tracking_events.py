from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from services.shipments.auth import get_current_user
from services.shipments.database import get_async_session_dep
from services.shipments.email_parser import EmailParser
from services.shipments.models import Package, TrackingEvent
from services.shipments.schemas import TrackingEventCreate, TrackingEventOut
from services.shipments.schemas.email_parser import (
    EmailParseRequest,
    EmailParseResponse,
    ParsedTrackingInfo,
)
from services.shipments.service_auth import service_permission_required

router = APIRouter()


@router.get("/{id}/events", response_model=List[TrackingEventOut])
async def get_tracking_events(
    id: int,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["read_shipments"])),
) -> list[TrackingEventOut]:
    # Query package and validate user ownership
    query = select(Package).where(Package.id == id, Package.user_id == current_user)  # type: ignore
    result = await session.execute(query)
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(
            status_code=404, detail="Package not found or access denied"
        )

    # Query tracking events for this package
    events_query = (
        select(TrackingEvent)
        .where(TrackingEvent.package_id == id)  # type: ignore
        .order_by(TrackingEvent.event_date.desc())  # type: ignore
    )
    events_result = await session.execute(events_query)
    events = events_result.scalars().all()

    return [
        TrackingEventOut(
            id=event.id,  # type: ignore
            event_date=event.event_date,
            status=event.status,
            location=event.location,
            description=event.description,
            created_at=event.created_at,
        )
        for event in events
    ]


@router.post("/{id}/events", response_model=TrackingEventOut)
async def create_tracking_event(
    id: int,
    event: TrackingEventCreate,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> TrackingEventOut:
    # Query package and validate user ownership
    query = select(Package).where(Package.id == id, Package.user_id == current_user)  # type: ignore
    result = await session.execute(query)
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(
            status_code=404, detail="Package not found or access denied"
        )

    # Create tracking event
    event_data = event.dict()
    event_data["package_id"] = id

    db_event = TrackingEvent(**event_data)  # type: ignore
    session.add(db_event)
    await session.commit()
    await session.refresh(db_event)

    return TrackingEventOut(
        id=db_event.id,  # type: ignore
        event_date=db_event.event_date,
        status=db_event.status,
        location=db_event.location,
        description=db_event.description,
        created_at=db_event.created_at,
    )


# Email parsing endpoint
email_parser = EmailParser()


@router.post("/from-email", response_model=EmailParseResponse)
async def parse_email_from_event(
    request: EmailParseRequest,
    current_user: str = Depends(get_current_user),
    service_name: str = Depends(service_permission_required(["parse_emails"])),
) -> EmailParseResponse:
    """
    Parse email content to detect shipment information and create events

    This endpoint analyzes email content to identify shipment information
    and can optionally create tracking events from the parsed data.
    """
    try:
        # Parse the email using the EmailParser
        parsed_data = email_parser.parse_email(
            subject=request.subject,
            sender=request.sender,
            body=request.body,
            content_type=request.content_type,
        )

        # Convert tracking numbers to ParsedTrackingInfo objects
        tracking_info = []
        for tracking_number in parsed_data.tracking_numbers:
            # Determine carrier for this tracking number
            carrier = parsed_data.detected_carrier
            if not carrier:
                # Try to detect carrier from tracking number format
                carrier = _detect_carrier_from_tracking_number(tracking_number)

            tracking_info.append(
                ParsedTrackingInfo(
                    tracking_number=tracking_number,
                    carrier=carrier,
                    confidence=parsed_data.confidence,
                    source=parsed_data.detected_from,
                )
            )

        # Create response
        response = EmailParseResponse(
            is_shipment_email=parsed_data.is_shipment_email,
            detected_carrier=parsed_data.detected_carrier,
            tracking_numbers=tracking_info,
            confidence=parsed_data.confidence,
            detected_from=parsed_data.detected_from,
            suggested_package_data=parsed_data.suggested_package_data,
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to parse email",
                "details": str(e),
                "error_code": "PARSE_ERROR",
            },
        )


def _detect_carrier_from_tracking_number(tracking_number: str) -> str:
    """
    Attempt to detect carrier from tracking number format

    This is a fallback when carrier detection from sender domain fails
    """
    tracking_number = tracking_number.upper()

    # UPS patterns
    if tracking_number.startswith("1Z") and len(tracking_number) == 18:
        return "ups"

    # FedEx patterns
    if len(tracking_number) in [12, 15, 22] and tracking_number.isdigit():
        return "fedex"

    # USPS patterns
    if len(tracking_number) in [20, 22, 13, 15] and tracking_number.isdigit():
        return "usps"

    # DHL patterns
    if len(tracking_number) in [10, 11, 12, 13] and tracking_number.isdigit():
        return "dhl"

    # Amazon patterns
    if tracking_number.startswith("TBA") and len(tracking_number) == 13:
        return "amazon"

    return "unknown"
