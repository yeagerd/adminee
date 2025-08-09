import os
from unittest.mock import patch

os.environ["PYTHON_ENV"] = "test"
os.environ["GMAIL_WEBHOOK_SECRET"] = "test-gmail-webhook-secret"

from services.common.test_utils import BaseSelectiveHTTPIntegrationTest
from services.email_sync.app import app


def valid_payload():
    return {"history_id": "12345", "email_address": "user@example.com"}


class TestGmailWebhook(BaseSelectiveHTTPIntegrationTest):
    def test_gmail_webhook_success(self):
        with patch("services.email_sync.app.publish_message") as mock_publish:
            client = self.create_test_client(app)
            resp = client.post(
                "/gmail/webhook",
                json=valid_payload(),
                headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "ok"
            mock_publish.assert_called_once()

    def test_gmail_webhook_invalid_secret(self):
        with patch("services.email_sync.app.publish_message") as mock_publish:
            client = self.create_test_client(app)
            resp = client.post(
                "/gmail/webhook",
                json=valid_payload(),
                headers={"X-Gmail-Webhook-Secret": "wrong-secret"},
            )
            assert resp.status_code == 401
            mock_publish.assert_not_called()

    def test_gmail_webhook_invalid_payload(self):
        with patch("services.email_sync.app.publish_message") as mock_publish:
            client = self.create_test_client(app)
            resp = client.post(
                "/gmail/webhook",
                json={"bad": "data"},
                headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
            )
            assert resp.status_code == 400
            mock_publish.assert_not_called()

    def test_gmail_webhook_pubsub_failure(self):
        with patch(
            "services.email_sync.app.publish_message",
            side_effect=Exception("pubsub error"),
        ) as mock_publish:
            client = self.create_test_client(app)
            resp = client.post(
                "/gmail/webhook",
                json=valid_payload(),
                headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
            )
            assert resp.status_code == 503
            mock_publish.assert_called_once()
