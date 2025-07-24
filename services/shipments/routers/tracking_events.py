from fastapi import APIRouter
from typing import List
from services.shipments.schemas import TrackingEventOut, TrackingEventCreate

router = APIRouter()

@router.get("/packages/{id}/events", response_model=List[TrackingEventOut])
def get_tracking_events(id: int):
    # TODO: Implement get tracking events for a package
    raise NotImplementedError 