from typing import List

from fastapi import APIRouter, Depends

from services.shipments.schemas import CarrierConfigOut
from services.shipments.service_auth import service_permission_required

router = APIRouter()


@router.get("/", response_model=List[CarrierConfigOut])
def list_carriers(
    service_name: str = Depends(service_permission_required(["read_shipments"])),
) -> list[CarrierConfigOut]:
    # TODO: Implement list carrier configs
    return []
