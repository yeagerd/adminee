from typing import List

from fastapi import APIRouter

from services.shipments.schemas import LabelCreate, LabelOut, LabelUpdate

router = APIRouter()


@router.get("/", response_model=List[LabelOut])
def list_labels() -> list[LabelOut]:
    # TODO: Implement label listing
    return []


@router.post("/", response_model=LabelOut)
def create_label(label: LabelCreate) -> LabelOut:
    # TODO: Implement label creation
    raise NotImplementedError


@router.put("/{id}", response_model=LabelOut)
def update_label(id: int, label: LabelUpdate) -> LabelOut:
    # TODO: Implement label update
    raise NotImplementedError


@router.delete("/{id}")
def delete_label(id: int) -> None:
    # TODO: Implement label deletion
    raise NotImplementedError
