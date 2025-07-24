from fastapi import APIRouter, HTTPException
from uuid import UUID, uuid4
from ..schemas import TimeSlot, TimeSlotCreate
from ..models import TimeSlot as TimeSlotModel, get_session
from typing import List

router = APIRouter()

@router.post("/", response_model=TimeSlot)
def add_slot(poll_id: UUID, slot: TimeSlotCreate):
    with get_session() as session:
        db_slot = TimeSlotModel(
            id=uuid4(),
            poll_id=poll_id,
            start_time=slot.start_time,
            end_time=slot.end_time,
            timezone=slot.timezone,
        )
        session.add(db_slot)
        session.commit()
        session.refresh(db_slot)
        return db_slot

@router.put("/{slot_id}", response_model=TimeSlot)
def update_slot(poll_id: UUID, slot_id: UUID, slot: TimeSlotCreate):
    with get_session() as session:
        db_slot = session.query(TimeSlotModel).filter_by(id=slot_id, poll_id=poll_id).first()
        if not db_slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        db_slot.start_time = slot.start_time
        db_slot.end_time = slot.end_time
        db_slot.timezone = slot.timezone
        session.commit()
        session.refresh(db_slot)
        return db_slot

@router.delete("/{slot_id}")
def delete_slot(poll_id: UUID, slot_id: UUID):
    with get_session() as session:
        db_slot = session.query(TimeSlotModel).filter_by(id=slot_id, poll_id=poll_id).first()
        if not db_slot:
            raise HTTPException(status_code=404, detail="Slot not found")
        session.delete(db_slot)
        session.commit()
        return {"ok": True} 