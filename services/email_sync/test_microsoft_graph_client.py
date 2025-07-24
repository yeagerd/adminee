from services.email_sync.microsoft_graph_client import MicrosoftGraphClient


def test_fetch_emails_from_notification():
    client = MicrosoftGraphClient(access_token="token")
    # For now, just check the stub returns []
    notification = {"value": [{"changeType": "created", "resource": "me/messages/1"}]}
    assert client.fetch_emails_from_notification(notification) == []
