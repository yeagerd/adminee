from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class EmailResponseRequest(BaseModel):
    emailId: str
    content: str
    sender: str

@router.post("/")
def process_email_response(req: EmailResponseRequest):
    # TODO: Implement email parsing and DB update logic
    return {"ok": True} 