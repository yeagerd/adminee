import os
import logging
from flask import Flask, jsonify, request, abort
from dotenv import load_dotenv
from pydantic import ValidationError

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

GMAIL_WEBHOOK_SECRET = os.getenv("GMAIL_WEBHOOK_SECRET")
GMAIL_TOPIC = "gmail-notifications"

# Patch pubsub_client for test mode
test_mode = os.getenv("PYTHON_ENV") == "test"
if test_mode:
    from unittest.mock import MagicMock
    publish_message = MagicMock()
else:
    from pubsub_client import publish_message
from schemas import GmailNotification

app.publish_message = publish_message

@app.route("/healthz")
def health_check():
    return jsonify({"status": "ok"}), 200

@app.route("/gmail/webhook", methods=["POST"])
def gmail_webhook():
    # Auth check
    secret = request.headers.get("X-Gmail-Webhook-Secret")
    if not secret or secret != GMAIL_WEBHOOK_SECRET:
        logging.warning("Unauthorized webhook attempt")
        abort(401, description="Unauthorized")
    # Parse and validate payload
    try:
        data = request.get_json(force=True)
        notification = GmailNotification(**data)
    except (TypeError, ValidationError) as e:
        logging.error(f"Invalid payload: {e}")
        abort(400, description="Invalid payload")
    # Publish to pubsub
    try:
        app.publish_message(GMAIL_TOPIC, notification.dict())
    except Exception as e:
        logging.error(f"Pubsub publish failed: {e}")
        abort(503, description="Pubsub unavailable")
    return jsonify({"status": "published"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080) 