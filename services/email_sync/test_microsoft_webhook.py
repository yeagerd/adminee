import os
from unittest.mock import patch

# Set environment variables before importing app
os.environ["MICROSOFT_WEBHOOK_SECRET"] = "test-microsoft-webhook-secret"
os.environ["GMAIL_WEBHOOK_SECRET"] = "test-gmail-webhook-secret"
os.environ["PYTHON_ENV"] = "test"

from services.email_sync.app import app


def valid_payload():
    return {"value": [{"changeType": "created", "resource": "me/messages/1"}]}


def test_microsoft_webhook_success():
    with patch("services.email_sync.microsoft_webhook.publish_message") as mock_publish:
        with app.test_client() as client:
            resp = client.post(
                "/microsoft/webhook",
                json=valid_payload(),
                headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
            )
            assert resp.status_code == 200
            assert resp.json["status"] == "published"
            mock_publish.assert_called_once()


def test_microsoft_webhook_invalid_signature():
    with patch("services.email_sync.microsoft_webhook.publish_message") as mock_publish:
        with app.test_client() as client:
            resp = client.post(
                "/microsoft/webhook",
                json=valid_payload(),
                headers={"X-Microsoft-Signature": "wrong-secret"},
            )
            assert resp.status_code == 401
            mock_publish.assert_not_called()


def test_microsoft_webhook_invalid_payload():
    with patch("services.email_sync.microsoft_webhook.publish_message") as mock_publish:
        with app.test_client() as client:
            resp = client.post(
                "/microsoft/webhook",
                data="not a json",
                headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                content_type="application/json",
            )
            assert resp.status_code == 400
            mock_publish.assert_not_called()


def test_microsoft_webhook_pubsub_failure():
    with patch(
        "services.email_sync.microsoft_webhook.publish_message",
        side_effect=Exception("pubsub error"),
    ) as mock_publish:
        with app.test_client() as client:
            resp = client.post(
                "/microsoft/webhook",
                json=valid_payload(),
                headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
            )
            assert resp.status_code == 400
            mock_publish.assert_called_once()
