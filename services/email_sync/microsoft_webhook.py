import logging
import os
from typing import Any

from flask import Blueprint, abort, jsonify, request

from services.email_sync.pubsub_client import publish_message

MICROSOFT_TOPIC = "microsoft-notifications"
MICROSOFT_WEBHOOK_SECRET = os.getenv(
    "MICROSOFT_WEBHOOK_SECRET", "test-microsoft-webhook-secret"
)

# Use mocked publish_message in test mode
if os.getenv("PYTHON_ENV") == "test":
    from unittest.mock import MagicMock

    publish_message = MagicMock()

microsoft_webhook_bp = Blueprint("microsoft_webhook", __name__)


@microsoft_webhook_bp.route("/microsoft/webhook", methods=["POST"])
def microsoft_webhook() -> Any:
    # Signature validation (mock for now)
    signature = request.headers.get("X-Microsoft-Signature")
    if not signature or signature != MICROSOFT_WEBHOOK_SECRET:
        logging.warning("Unauthorized Microsoft webhook attempt")
        abort(401, description="Unauthorized")
    try:
        data = request.get_json(force=True)
        # Validate that payload contains required "value" field
        if "value" not in data:
            logging.error("Invalid Microsoft webhook payload: missing 'value' field")
            abort(400, description="Invalid payload")
        # TODO: Add real validation for Microsoft Graph webhook payload
        publish_message(MICROSOFT_TOPIC, data)
    except Exception as e:
        logging.error(f"Failed to process Microsoft webhook: {e}")
        abort(400, description="Invalid payload")
    return jsonify({"status": "published"}), 200
