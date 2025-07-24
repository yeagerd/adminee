import os

os.environ["PYTHON_ENV"] = "test"
os.environ["GMAIL_WEBHOOK_SECRET"] = "your-gmail-webhook-secret"

from services.email_sync.app import app


def valid_payload():
    return {"history_id": "12345", "email_address": "user@example.com"}


def test_gmail_webhook_success():
    with app.test_client() as client:
        resp = client.post(
            "/gmail/webhook",
            json=valid_payload(),
            headers={"X-Gmail-Webhook-Secret": "your-gmail-webhook-secret"},
        )
        assert resp.status_code == 200
        assert resp.json["status"] == "ok"


def test_gmail_webhook_invalid_secret():
    with app.test_client() as client:
        resp = client.post(
            "/gmail/webhook",
            json=valid_payload(),
            headers={"X-Gmail-Webhook-Secret": "wrong-secret"},
        )
        assert resp.status_code == 401


def test_gmail_webhook_invalid_payload():
    with app.test_client() as client:
        resp = client.post(
            "/gmail/webhook",
            json={"bad": "data"},
            headers={"X-Gmail-Webhook-Secret": "your-gmail-webhook-secret"},
        )
        assert resp.status_code == 400


def test_gmail_webhook_pubsub_failure(monkeypatch):
    def fail_publish(*args, **kwargs):
        raise Exception("pubsub error")

    app.publish_message = fail_publish
    with app.test_client() as client:
        resp = client.post(
            "/gmail/webhook",
            json=valid_payload(),
            headers={"X-Gmail-Webhook-Secret": "your-gmail-webhook-secret"},
        )
        assert resp.status_code == 503
