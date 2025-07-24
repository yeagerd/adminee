import pytest
from schemas import GmailNotification
from gmail_sync_service import process_gmail_notification

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
    process_gmail_notification(msg)
    assert msg.acked
    assert not msg.nacked

def test_process_gmail_notification_invalid(monkeypatch):
    msg = DummyMessage(data=b"not a json")
    process_gmail_notification(msg)
    assert not msg.acked
    assert msg.nacked 