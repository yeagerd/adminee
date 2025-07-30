from typing import List

from fastapi import APIRouter, Depends, HTTPException

from services.shipments.auth import get_current_user
from services.shipments.schemas import LabelCreate, LabelOut, LabelUpdate
from services.shipments.service_auth import service_permission_required

router = APIRouter()


@router.get("/", response_model=List[LabelOut])
def list_labels(
    current_user: str = Depends(get_current_user),
    service_name: str = Depends(service_permission_required(["read_labels"])),
) -> list[LabelOut]:
    """
    List all labels for the authenticated user.

    **Authentication:**
    - Requires user authentication (JWT token or gateway headers)
    - Returns only labels owned by the authenticated user
    - Requires service API key for service-to-service calls
    """
    # TODO: Implement label listing with user filtering
    # This should filter labels by current_user
    return []


@router.post("/", response_model=LabelOut)
def create_label(
    label: LabelCreate,
    current_user: str = Depends(get_current_user),
    service_name: str = Depends(service_permission_required(["write_labels"])),
) -> LabelOut:
    """
    Create a new label for the authenticated user.

    **Authentication:**
    - Requires user authentication (JWT token or gateway headers)
    - Validates user ownership of label data
    - Requires service API key for service-to-service calls
    """
    # Validate user ownership of label data
    # Note: In a real implementation, this would be done in the service layer
    # For now, we'll validate that the user_id in the request matches the authenticated user
    if label.user_id != current_user:
        raise HTTPException(status_code=403, detail="User does not own the label data")

    # TODO: Implement label creation with user ownership
    raise NotImplementedError


@router.put("/{id}", response_model=LabelOut)
def update_label(
    id: int,
    label: LabelUpdate,
    current_user: str = Depends(get_current_user),
    service_name: str = Depends(service_permission_required(["write_labels"])),
) -> LabelOut:
    """
    Update a label for the authenticated user.

    **Authentication:**
    - Requires user authentication (JWT token or gateway headers)
    - Validates user ownership of the label
    - Requires service API key for service-to-service calls
    """
    # TODO: Implement label update with user ownership validation
    # This should validate that the label belongs to current_user
    raise NotImplementedError


@router.delete("/{id}")
def delete_label(
    id: int,
    current_user: str = Depends(get_current_user),
    service_name: str = Depends(service_permission_required(["write_labels"])),
) -> None:
    """
    Delete a label for the authenticated user.

    **Authentication:**
    - Requires user authentication (JWT token or gateway headers)
    - Validates user ownership of the label
    - Requires service API key for service-to-service calls
    """
    # TODO: Implement label deletion with user ownership validation
    # This should validate that the label belongs to current_user
    raise NotImplementedError
