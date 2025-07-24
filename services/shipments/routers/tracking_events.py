from typing import List

from fastapi import APIRouter

from services.shipments.schemas import TrackingEventOut

router = APIRouter()


@router.get("/packages/{id}/events", response_model=List[TrackingEventOut])
def get_tracking_events(id: int) -> list[TrackingEventOut]:
    # TODO: Implement get tracking events for a package
    raise NotImplementedError
