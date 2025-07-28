from typing import List

from fastapi import APIRouter, Depends

from services.shipments.schemas import TrackingEventOut
from services.shipments.service_auth import service_permission_required

router = APIRouter()


@router.get("/packages/{id}/events", response_model=List[TrackingEventOut])
def get_tracking_events(
    id: int,
    service_name: str = Depends(service_permission_required(["read_shipments"])),
) -> list[TrackingEventOut]:
    # TODO: Implement get tracking events for a package
    raise NotImplementedError
