import logging
import os
from typing import Dict

from fastapi import APIRouter, HTTPException, Request

from services.email_sync.pubsub_client import publish_message

MICROSOFT_TOPIC = "microsoft-notifications"
MICROSOFT_WEBHOOK_SECRET = os.getenv(
    "MICROSOFT_WEBHOOK_SECRET", "test-microsoft-webhook-secret"
)

# Use mocked publish_message in test mode
if os.getenv("PYTHON_ENV") == "test":
    from unittest.mock import MagicMock

    publish_message = MagicMock()

microsoft_webhook_bp = APIRouter()


@microsoft_webhook_bp.post("/microsoft/webhook")
async def microsoft_webhook(request: Request) -> Dict[str, str]:
    # Signature validation (mock for now)
    signature = request.headers.get("X-Microsoft-Signature")
    if not signature or signature != MICROSOFT_WEBHOOK_SECRET:
        logging.warning("Unauthorized Microsoft webhook attempt")
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        data = await request.json()
        # Validate that payload contains required "value" field
        if "value" not in data:
            logging.error("Invalid Microsoft webhook payload: missing 'value' field")
            raise HTTPException(status_code=400, detail="Invalid payload")
        # TODO: Add real validation for Microsoft Graph webhook payload
        publish_message(MICROSOFT_TOPIC, data)
    except Exception as e:
        logging.error(f"Failed to process Microsoft webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")

    return {"status": "published"}
