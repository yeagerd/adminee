import logging

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class EmailResponseRequest(BaseModel):
    emailId: str
    content: str
    sender: str


@router.post("/")
def process_email_response(req: EmailResponseRequest):
    # TODO: Parse email content, match to poll/participant, update response
    logging.info(f"Received email response from {req.sender}: {req.content}")
    # For now, just acknowledge receipt
    return {"ok": True, "received_from": req.sender}
