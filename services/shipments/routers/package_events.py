"""
Tracking events ("/packages/{id}/events") endpoints for the shipments service
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from services.shipments.auth import get_current_user
from services.shipments.database import get_async_session_dep
from services.shipments.models import Package, TrackingEvent
from services.shipments.schemas import TrackingEventCreate, TrackingEventOut
from services.shipments.service_auth import service_permission_required

# Router for package-specific tracking events
# This allows /api/v1/shipments/packages/{id}/events to work
package_events_router = APIRouter()


@package_events_router.get(
    "/{package_id}/events", response_model=List[TrackingEventOut]
)
async def get_tracking_events(
    package_id: UUID,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["read_shipments"])),
) -> list[TrackingEventOut]:
    # Query package and validate user ownership
    query = select(Package).where(Package.id == package_id, Package.user_id == current_user)  # type: ignore
    result = await session.execute(query)
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(
            status_code=404, detail="Package not found or access denied"
        )

    # Query tracking events for the package
    events_query = (
        select(TrackingEvent)
        .where(TrackingEvent.package_id == package_id)
        .order_by(TrackingEvent.event_date.desc())  # type: ignore[attr-defined]
    )
    events_result = await session.execute(events_query)
    events = events_result.scalars().all()

    return [
        TrackingEventOut(
            id=event.id,  # type: ignore[arg-type]
            event_date=event.event_date,
            status=event.status,
            location=event.location,
            description=event.description,
            created_at=event.created_at,
        )
        for event in events
    ]


@package_events_router.post("/{package_id}/events", response_model=TrackingEventOut)
async def create_tracking_event(
    package_id: UUID,
    event: TrackingEventCreate,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> TrackingEventOut:
    # Query package and validate user ownership
    query = select(Package).where(Package.id == package_id, Package.user_id == current_user)  # type: ignore
    result = await session.execute(query)
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(
            status_code=404, detail="Package not found or access denied"
        )

    # Check if an event with the same email_message_id already exists for this package
    if event.email_message_id:
        existing_event_query = select(TrackingEvent).where(
            TrackingEvent.email_message_id == event.email_message_id,
            TrackingEvent.package_id == package_id,
        )
        existing_event_result = await session.execute(existing_event_query)
        existing_event = existing_event_result.scalar_one_or_none()

        if existing_event:
            # Update the existing event instead of creating a new one
            # Ensure event_date is timezone-naive for database compatibility
            event_date = event.event_date
            if event_date and event_date.tzinfo is not None:
                event_date = event_date.replace(tzinfo=None)

            existing_event.event_date = event_date
            existing_event.status = event.status
            existing_event.location = event.location
            existing_event.description = event.description

            await session.commit()
            await session.refresh(existing_event)

            return TrackingEventOut(
                id=existing_event.id,  # type: ignore
                event_date=existing_event.event_date,
                status=existing_event.status,
                location=existing_event.location,
                description=existing_event.description,
                created_at=existing_event.created_at,
            )

    # Create new tracking event
    # Ensure event_date is timezone-naive for database compatibility before converting to dict
    if event.event_date and event.event_date.tzinfo is not None:
        event.event_date = event.event_date.replace(tzinfo=None)

    event_data = event.model_dump()
    event_data["package_id"] = package_id

    db_event = TrackingEvent(**event_data)
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


@package_events_router.delete("/{package_id}/events/{event_id}")
async def delete_tracking_event(
    package_id: UUID,
    event_id: UUID,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> dict:
    """
    Delete a tracking event by ID

    Validates that the user owns the package associated with the tracking event
    before allowing deletion.
    """
    # Query package and validate user ownership
    package_query = select(Package).where(
        Package.id == package_id, Package.user_id == current_user
    )
    package_result = await session.execute(package_query)
    package = package_result.scalar_one_or_none()

    if not package:
        raise HTTPException(
            status_code=404, detail="Package not found or access denied"
        )

    # Query tracking event and validate it belongs to the package
    event_query = select(TrackingEvent).where(
        TrackingEvent.id == event_id,
        TrackingEvent.package_id == package_id,
    )
    event_result = await session.execute(event_query)
    event = event_result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=404, detail="Tracking event not found or access denied"
        )

    # Delete the event
    await session.delete(event)
    await session.commit()

    return {"message": "Tracking event deleted successfully"}
