import pytest
from microsoft_sync_service import process_microsoft_notification
from unittest.mock import patch

class DummyMessage:
    def __init__(self, data):
        self.data = data
        self.acked = False
        self.nacked = False
    def ack(self):
        self.acked = True
    def nack(self):
        self.nacked = True

def test_process_microsoft_notification_valid():
    msg = DummyMessage(data=b'{"value": [{"changeType": "created"}]}')
    process_microsoft_notification(msg)
    assert msg.acked
    assert not msg.nacked

def test_process_microsoft_notification_invalid():
    msg = DummyMessage(data=b'not a json')
    process_microsoft_notification(msg)
    assert not msg.acked
    assert msg.nacked 

def test_process_microsoft_notification_publish():
    msg = DummyMessage(data=b'{"value": [{"changeType": "created"}]}')
    with patch("microsoft_sync_service.MicrosoftGraphClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.fetch_emails_from_notification.return_value = [{"id": "email1"}, {"id": "email2"}]
        with patch("microsoft_sync_service.publish_message") as mock_publish:
            process_microsoft_notification(msg)
            assert msg.acked
            assert not msg.nacked
            assert mock_publish.call_count == 2

def test_process_microsoft_notification_pubsub_failure():
    msg = DummyMessage(data=b'{"value": [{"changeType": "created"}]}')
    with patch("microsoft_sync_service.MicrosoftGraphClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.fetch_emails_from_notification.return_value = [{"id": "email1"}]
        with patch("microsoft_sync_service.publish_message", side_effect=Exception("pubsub error")) as mock_publish:
            process_microsoft_notification(msg)
            assert msg.acked
            assert not msg.nacked
            assert mock_publish.call_count == 5 