from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from services.shipments.auth import get_current_user
from services.shipments.database import get_async_session_dep
from services.shipments.models import Package, TrackingEvent
from services.shipments.schemas import TrackingEventCreate, TrackingEventOut
from services.shipments.service_auth import service_permission_required

router = APIRouter()


@router.get("/packages/{id}/events", response_model=List[TrackingEventOut])
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
        .order_by(TrackingEvent.event_date.desc())
    )
    events_result = await session.execute(events_query)
    events = events_result.scalars().all()

    return [
        TrackingEventOut(
            id=event.id,
            event_date=event.event_date,
            status=event.status,
            location=event.location,
            description=event.description,
            created_at=event.created_at,
        )
        for event in events
    ]


@router.post("/packages/{id}/events", response_model=TrackingEventOut)
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
        id=db_event.id,
        event_date=db_event.event_date,
        status=db_event.status,
        location=db_event.location,
        description=db_event.description,
        created_at=db_event.created_at,
    )
