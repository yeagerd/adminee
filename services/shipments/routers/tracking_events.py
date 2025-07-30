from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from services.shipments.auth import get_current_user
from services.shipments.database import get_async_session_dep
from services.shipments.models import Package
from services.shipments.schemas import TrackingEventOut
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
    query = select(Package).where(Package.id == id, Package.user_id == current_user)
    result = await session.execute(query)
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(
            status_code=404, detail="Package not found or access denied"
        )

    # TODO: Implement actual tracking events query
    # For now, return empty list
    return []
