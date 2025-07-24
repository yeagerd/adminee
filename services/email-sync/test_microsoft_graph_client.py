import pytest
from microsoft_graph_client import MicrosoftGraphClient
from unittest.mock import patch

def test_fetch_emails_from_notification():
    client = MicrosoftGraphClient(access_token="token")
    # For now, just check the stub returns []
    notification = {"value": [{"changeType": "created", "resource": "me/messages/1"}]}
    assert client.fetch_emails_from_notification(notification) == [] 