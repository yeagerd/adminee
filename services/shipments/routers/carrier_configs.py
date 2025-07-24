from fastapi import APIRouter
from typing import List
from services.shipments.schemas import CarrierConfigOut

router = APIRouter()

@router.get("/", response_model=List[CarrierConfigOut])
def list_carriers():
    # TODO: Implement list carrier configs
    return [] 