# mypy: disable-error-code=attr-defined
import logging
from typing import Dict

from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError

from services.common.settings import BaseSettings, Field
from services.email_sync.microsoft_webhook import microsoft_webhook_bp
from services.email_sync.pubsub_client import publish_message
from services.email_sync.schemas import GmailNotification


class EmailSyncSettings(BaseSettings):
    GMAIL_WEBHOOK_SECRET: str = Field(..., description="Gmail webhook secret")
    PYTHON_ENV: str = Field("production", description="Python environment")


settings = EmailSyncSettings()

app = FastAPI(title="Email Sync Service", version="0.1.0")
logging.basicConfig(level=logging.INFO)

GMAIL_WEBHOOK_SECRET = settings.GMAIL_WEBHOOK_SECRET
GMAIL_TOPIC = "gmail-notifications"

# Patch pubsub_client for test mode
test_mode = settings.PYTHON_ENV == "test"
if test_mode:
    from unittest.mock import MagicMock

    publish_message = MagicMock()


@app.get("/healthz")
async def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/gmail/webhook")
async def gmail_webhook(request: Request) -> Dict[str, str]:
    # Auth check
    secret = request.headers.get("X-Gmail-Webhook-Secret")
    if not secret or secret != GMAIL_WEBHOOK_SECRET:
        logging.warning("Unauthorized webhook attempt")
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Parse and validate payload
    try:
        data = await request.json()
        notification = GmailNotification(**data)
    except (TypeError, ValidationError) as e:
        logging.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Publish to pubsub
    try:
        publish_message(GMAIL_TOPIC, notification.model_dump())
    except Exception as e:
        logging.error(f"Pubsub publish failed: {e}")
        raise HTTPException(status_code=503, detail="Pubsub unavailable")

    return {"status": "ok"}


# Include Microsoft webhook routes
app.include_router(microsoft_webhook_bp)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
