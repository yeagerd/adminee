from pydantic import BaseModel


class GmailNotification(BaseModel):
    history_id: str
    email_address: str
