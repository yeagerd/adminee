from typing import List

from fastapi import APIRouter

from services.shipments.schemas import CarrierConfigOut

router = APIRouter()


@router.get("/", response_model=List[CarrierConfigOut])
def list_carriers() -> list[CarrierConfigOut]:
    # TODO: Implement list carrier configs
    return []
