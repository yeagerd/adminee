from typing import List

from fastapi import APIRouter, Depends

from services.shipments.auth import get_current_user
from services.shipments.schemas import CarrierConfigOut
from services.shipments.service_auth import service_permission_required

router = APIRouter()


@router.get("/", response_model=List[CarrierConfigOut])
def list_carriers(
    current_user: str = Depends(get_current_user),
    service_name: str = Depends(service_permission_required(["read_shipments"])),
) -> list[CarrierConfigOut]:
    """
    List carrier configurations.

    **Authentication:**
    - Requires user authentication (JWT token or gateway headers)
    - Requires service API key for service-to-service calls
    - Note: Carrier configs are typically system-wide, not user-specific
    """
    # TODO: Implement list carrier configs
    # Note: Carrier configs are typically system-wide configurations
    # but we still require authentication for access control
    return []
