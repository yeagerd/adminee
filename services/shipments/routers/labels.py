from fastapi import APIRouter
from typing import List
from services.shipments.schemas import LabelOut, LabelCreate, LabelUpdate

router = APIRouter()

@router.get("/", response_model=List[LabelOut])
def list_labels():
    # TODO: Implement label listing
    return []

@router.post("/", response_model=LabelOut)
def create_label(label: LabelCreate):
    # TODO: Implement label creation
    raise NotImplementedError

@router.put("/{id}", response_model=LabelOut)
def update_label(id: int, label: LabelUpdate):
    # TODO: Implement label update
    raise NotImplementedError

@router.delete("/{id}")
def delete_label(id: int):
    # TODO: Implement label deletion
    raise NotImplementedError 