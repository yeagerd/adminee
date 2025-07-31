"""
Label management endpoints for the shipments service
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.api_key_auth import get_current_user, service_permission_required
from services.shipments.database import get_async_session_dep
from services.shipments.models import Label
from services.shipments.schemas import LabelCreate, LabelOut, LabelUpdate

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
    - User ownership is automatically derived from authenticated user context
    - Requires service API key for service-to-service calls
    """
    # TODO: Implement label creation with user ownership
    # The user_id should be derived from current_user, not from client input
    raise NotImplementedError


@router.put("/{id}", response_model=LabelOut)
async def update_label(
    id: UUID,  # Changed from int to UUID
    label: LabelUpdate,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> LabelOut:
    # Query label and validate user ownership
    query = select(Label).where(Label.id == id, Label.user_id == current_user)
    result = await session.execute(query)
    db_label = result.scalar_one_or_none()

    if not db_label:
        raise HTTPException(
            status_code=404, detail="Label not found or access denied"
        )

    # Update label fields
    update_data = label.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_label, field, value)

    await session.commit()
    await session.refresh(db_label)

    return LabelOut(
        id=db_label.id,
        user_id=db_label.user_id,
        name=db_label.name,
        color=db_label.color,
        created_at=db_label.created_at,
    )


@router.delete("/{id}")
async def delete_label(
    id: UUID,  # Changed from int to UUID
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> dict:
    # Query label and validate user ownership
    query = select(Label).where(Label.id == id, Label.user_id == current_user)
    result = await session.execute(query)
    label = result.scalar_one_or_none()

    if not label:
        raise HTTPException(
            status_code=404, detail="Label not found or access denied"
        )

    await session.delete(label)
    await session.commit()

    return {"message": "Label deleted successfully"}
