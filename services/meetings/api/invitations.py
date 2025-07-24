from fastapi import APIRouter, HTTPException
from uuid import UUID
from ..models import MeetingPoll as MeetingPollModel, get_session

router = APIRouter()

@router.post("/")
def send_invitations(poll_id: UUID):
    with get_session() as session:
        poll = session.query(MeetingPollModel).filter_by(id=poll_id).first()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found")
        # TODO: Implement email sending logic
        return {"ok": True} 