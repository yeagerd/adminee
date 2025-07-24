from unittest.mock import patch

from services.email_sync.gmail_sync_service import process_gmail_notification
from services.email_sync.schemas import GmailNotification


class DummyMessage:
    def __init__(self, data):
        self.data = data
        self.acked = False
        self.nacked = False

    def ack(self):
        self.acked = True

    def nack(self):
        self.nacked = True


def test_process_gmail_notification_valid(monkeypatch):
    notif = GmailNotification(history_id="12345", email_address="user@example.com")
    msg = DummyMessage(data=notif.model_dump_json().encode("utf-8"))
    with patch("services.email_sync.gmail_sync_service.GmailAPIClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.fetch_emails_since_history_id.return_value = [
            {"id": "email1"},
            {"id": "email2"},
        ]
        with patch("services.email_sync.gmail_sync_service.publish_message") as mock_publish:
            process_gmail_notification(msg)
            assert msg.acked
            assert not msg.nacked
            assert mock_publish.call_count == 2


def test_process_gmail_notification_invalid(monkeypatch):
    msg = DummyMessage(data=b"not a json")
    process_gmail_notification(msg)
    assert not msg.acked
    assert msg.nacked


def test_process_gmail_notification_pubsub_failure(monkeypatch):
    notif = GmailNotification(history_id="12345", email_address="user@example.com")
    msg = DummyMessage(data=notif.model_dump_json().encode("utf-8"))
    with patch(
        "services.email_sync.gmail_sync_service.GmailAPIClient"
    ) as MockClient:
        mock_client = MockClient.return_value
        mock_client.fetch_emails_since_history_id.return_value = [{"id": "email1"}]
        with patch(
            "services.email_sync.gmail_sync_service.publish_message", side_effect=Exception("pubsub error")
        ) as mock_publish, patch("time.sleep", lambda x: None):
            process_gmail_notification(msg)
            assert msg.acked
            assert not msg.nacked
            assert mock_publish.call_count == 5
