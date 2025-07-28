from typing import List

from fastapi import APIRouter, Depends

from services.shipments.schemas import LabelCreate, LabelOut, LabelUpdate
from services.shipments.service_auth import service_permission_required

router = APIRouter()


@router.get("/", response_model=List[LabelOut])
def list_labels(
    service_name: str = Depends(service_permission_required(["read_labels"])),
) -> list[LabelOut]:
    # TODO: Implement label listing
    return []


@router.post("/", response_model=LabelOut)
def create_label(
    label: LabelCreate,
    service_name: str = Depends(service_permission_required(["write_labels"])),
) -> LabelOut:
    # TODO: Implement label creation
    raise NotImplementedError


@router.put("/{id}", response_model=LabelOut)
def update_label(
    id: int,
    label: LabelUpdate,
    service_name: str = Depends(service_permission_required(["write_labels"])),
) -> LabelOut:
    # TODO: Implement label update
    raise NotImplementedError


@router.delete("/{id}")
def delete_label(
    id: int, service_name: str = Depends(service_permission_required(["write_labels"]))
) -> None:
    # TODO: Implement label deletion
    raise NotImplementedError
