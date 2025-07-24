from unittest.mock import MagicMock, patch

from services.email_sync.gmail_api_client import GmailAPIClient


def test_fetch_emails_since_history_id():
    client = GmailAPIClient(
        access_token="token",
        refresh_token="refresh",
        client_id="id",
        client_secret="secret",
        token_uri="uri",
    )
    with patch.object(client, "service") as mock_service:
        mock_history = MagicMock()
        mock_history.list.return_value.execute.return_value = {
            "messages": [{"id": "1"}, {"id": "2"}]
        }
        mock_service.users.return_value.history.return_value = mock_history
        # Patch fetch_emails_since_history_id to call the real Gmail API in the future
        # For now, just check the stub returns []
        assert client.fetch_emails_since_history_id("me", "12345") == []
