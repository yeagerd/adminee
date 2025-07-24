# mypy: disable-error-code=attr-defined
import logging

from flask import (  # type: ignore[attr-defined]
    Flask,
    Response,
    abort,
    jsonify,
    make_response,
    request,
)
from pydantic import ValidationError

from services.common.settings import BaseSettings, Field
from services.email_sync.microsoft_webhook import microsoft_webhook_bp
from services.email_sync.pubsub_client import publish_message
from services.email_sync.schemas import GmailNotification


class EmailSyncSettings(BaseSettings):
    GMAIL_WEBHOOK_SECRET: str = Field(..., description="Gmail webhook secret")
    PYTHON_ENV: str = Field("production", description="Python environment")


settings = EmailSyncSettings()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

GMAIL_WEBHOOK_SECRET = settings.GMAIL_WEBHOOK_SECRET
GMAIL_TOPIC = "gmail-notifications"

# Patch pubsub_client for test mode
test_mode = settings.PYTHON_ENV == "test"
if test_mode:
    from unittest.mock import MagicMock

    publish_message = MagicMock()

# type: ignore[attr-defined]
app.publish_message = publish_message
app.register_blueprint(microsoft_webhook_bp)


@app.route("/healthz")
def health_check() -> Response:
    return make_response(jsonify({"status": "ok"}), 200)


@app.route("/gmail/webhook", methods=["POST"])
def gmail_webhook() -> Response:
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
        app.publish_message(GMAIL_TOPIC, notification.model_dump())  # type: ignore[attr-defined]
    except Exception as e:
        logging.error(f"Pubsub publish failed: {e}")
        abort(503, description="Pubsub unavailable")
    return make_response(jsonify({"status": "ok"}), 200)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
