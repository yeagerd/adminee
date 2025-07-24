import pytest
from microsoft_sync_service import process_microsoft_notification

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