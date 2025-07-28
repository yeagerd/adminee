from unittest.mock import MagicMock, patch

import pytest

from services.common.test_utils import BaseSelectiveHTTPIntegrationTest
from services.email_sync.gmail_api_client import GmailAPIClient


@patch("services.email_sync.gmail_api_client.build")
def test_fetch_emails_since_history_id(mock_build):
    """Test the fetch_emails_since_history_id method."""
    # Mock the build function before creating the client
    mock_service = MagicMock()
    mock_build.return_value = mock_service

    client = GmailAPIClient(
        access_token="test-token",
        refresh_token="test-refresh",
        client_id="test-client-id",
        client_secret="test-client-secret",
        token_uri="https://oauth2.googleapis.com/token",
    )

    # Mock empty response
    mock_service.users.return_value.history.return_value.list.return_value.execute.return_value = {
        "history": []
    }

    # Test that the method exists and can be called
    result = client.fetch_emails_since_history_id("me", "12345")
    assert isinstance(result, list)


class TestGmailAPIClientIntegration(BaseSelectiveHTTPIntegrationTest):
    """Integration tests for Gmail API client."""

    @pytest.fixture
    def gmail_client(self):
        """Create a Gmail API client for testing."""
        with patch("services.email_sync.gmail_api_client.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            client = GmailAPIClient(
                access_token="test-token",
                refresh_token="test-refresh",
                client_id="test-client-id",
                client_secret="test-client-secret",
                token_uri="https://oauth2.googleapis.com/token",
            )

            # Store the mock service for tests to use
            client._mock_service = mock_service
            return client

    def test_real_gmail_api_integration_mocked(self, gmail_client):
        """Test integration with Gmail API using mocked service."""
        # Mock the history list response
        mock_history_response = {
            "history": [
                {
                    "messagesAdded": [
                        {"message": {"id": "msg1"}},
                        {"message": {"id": "msg2"}},
                    ],
                    "labelsAdded": [{"message": {"id": "msg3"}}],
                }
            ]
        }
        gmail_client._mock_service.users.return_value.history.return_value.list.return_value.execute.return_value = (
            mock_history_response
        )

        # Mock the message get responses
        mock_message1 = {
            "id": "msg1",
            "threadId": "thread1",
            "labelIds": ["INBOX"],
            "snippet": "Test email 1",
            "internalDate": "1642233600000",
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender1@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Subject", "value": "Test Subject 1"},
                ],
                "body": {"data": "VGVzdCBib2R5IDE="},  # Base64 encoded "Test body 1"
            },
        }
        mock_message2 = {
            "id": "msg2",
            "threadId": "thread2",
            "labelIds": ["INBOX"],
            "snippet": "Test email 2",
            "internalDate": "1642237200000",
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender2@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Subject", "value": "Test Subject 2"},
                ],
                "body": {"data": "VGVzdCBib2R5IDI="},  # Base64 encoded "Test body 2"
            },
        }

        def mock_get_message(userId, id, format):
            if id == "msg1":
                return MagicMock(execute=lambda: mock_message1)
            elif id == "msg2":
                return MagicMock(execute=lambda: mock_message2)
            else:
                return MagicMock(
                    execute=lambda: {
                        "id": id,
                        "threadId": "thread3",
                        "payload": {"headers": [], "body": {"data": ""}},
                    }
                )

        gmail_client._mock_service.users.return_value.messages.return_value.get.side_effect = (
            mock_get_message
        )

        # Call the method
        result = gmail_client.fetch_emails_since_history_id("me", "12345")

        # Verify the result
        assert len(result) == 3  # 3 unique message IDs

        # Find the message with id "msg1" (order is not guaranteed due to set processing)
        msg1_result = None
        for email in result:
            if email["id"] == "msg1":
                msg1_result = email
                break

        assert msg1_result is not None, "msg1 not found in result"
        assert msg1_result["from"] == "sender1@example.com"
        assert msg1_result["subject"] == "Test Subject 1"
        assert msg1_result["body"] == "Test body 1"
        assert msg1_result["provider"] == "gmail"

    @patch("time.sleep")
    def test_gmail_api_rate_limit_handling_mocked(self, mock_sleep, gmail_client):
        """Test handling of Gmail API rate limits with mocked service."""
        from googleapiclient.errors import HttpError

        # Mock rate limit error (429)
        rate_limit_error = HttpError(
            resp=MagicMock(status=429), content=b"Rate limit exceeded"
        )
        gmail_client._mock_service.users.return_value.history.return_value.list.return_value.execute.side_effect = (
            rate_limit_error
        )

        # The method should raise an exception after retries
        with pytest.raises(Exception, match="Max retries exceeded"):
            gmail_client.fetch_emails_since_history_id("me", "12345")

    def test_gmail_api_authentication_error_handling_mocked(self, gmail_client):
        """Test handling of authentication errors with mocked service."""
        from googleapiclient.errors import HttpError

        # Mock authentication error (401)
        auth_error = HttpError(resp=MagicMock(status=401), content=b"Unauthorized")
        gmail_client._mock_service.users.return_value.history.return_value.list.return_value.execute.side_effect = (
            auth_error
        )

        # The method should raise the authentication error
        with pytest.raises(HttpError):
            gmail_client.fetch_emails_since_history_id("me", "12345")

    def test_gmail_api_pagination_handling_mocked(self, gmail_client):
        """Test handling of paginated responses from Gmail API with mocked service."""
        # Mock paginated history response
        mock_history_response = {
            "history": [{"messagesAdded": [{"message": {"id": "msg1"}}]}],
            "nextPageToken": "next_page_token",
        }
        gmail_client._mock_service.users.return_value.history.return_value.list.return_value.execute.return_value = (
            mock_history_response
        )

        # Mock message response
        mock_message = {
            "id": "msg1",
            "threadId": "thread1",
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "Test Subject"},
                ],
                "body": {"data": "VGVzdCBib2R5"},  # Base64 encoded "Test body"
            },
        }
        gmail_client._mock_service.users.return_value.messages.return_value.get.return_value.execute.return_value = (
            mock_message
        )

        # Call the method
        result = gmail_client.fetch_emails_since_history_id("me", "12345")

        # Verify the result
        assert len(result) == 1
        assert result[0]["id"] == "msg1"

    def test_gmail_api_network_error_handling_mocked(self, gmail_client):
        """Test handling of network errors with mocked service."""
        # Mock network error
        gmail_client._mock_service.users.return_value.history.return_value.list.return_value.execute.side_effect = Exception(
            "Network error"
        )

        # The method should raise the original exception since it's not an HttpError
        with pytest.raises(Exception, match="Network error"):
            gmail_client.fetch_emails_since_history_id("me", "12345")

    @patch("services.email_sync.gmail_api_client.build")
    def test_gmail_api_client_initialization(self, mock_build):
        """Test Gmail API client initialization with various configurations."""
        # Mock the build function
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Test with all required parameters
        client = GmailAPIClient(
            access_token="test-token",
            refresh_token="test-refresh",
            client_id="test-client-id",
            client_secret="test-client-secret",
            token_uri="https://oauth2.googleapis.com/token",
        )

        # Verify credentials are properly set
        assert client.creds.token == "test-token"
        assert client.creds.refresh_token == "test-refresh"
        assert client.creds.client_id == "test-client-id"
        assert client.creds.client_secret == "test-client-secret"
        assert client.creds.token_uri == "https://oauth2.googleapis.com/token"

        # Verify service is built
        assert client.service == mock_service

    def test_gmail_api_empty_history_response_mocked(self, gmail_client):
        """Test handling of empty history responses with mocked service."""
        # Mock empty history response
        mock_history_response = {"history": []}
        gmail_client._mock_service.users.return_value.history.return_value.list.return_value.execute.return_value = (
            mock_history_response
        )

        # Call the method
        result = gmail_client.fetch_emails_since_history_id("me", "12345")

        # Verify empty list is returned
        assert result == []

    @patch("services.email_sync.gmail_api_client.build")
    def test_gmail_api_service_build_integration(self, mock_build):
        """Test that the Gmail API service is built correctly."""
        # Mock the build function
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Create client
        client = GmailAPIClient(
            access_token="test-token",
            refresh_token="test-refresh",
            client_id="test-client-id",
            client_secret="test-client-secret",
            token_uri="https://oauth2.googleapis.com/token",
        )

        # Verify build was called correctly
        mock_build.assert_called_once_with("gmail", "v1", credentials=client.creds)
        assert client.service == mock_service

    @patch("services.email_sync.gmail_api_client.build")
    def test_gmail_api_client_with_different_parameters(self, mock_build):
        """Test Gmail API client with different parameter combinations."""
        # Mock the build function
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Test with different token URIs
        client1 = GmailAPIClient(
            access_token="token1",
            refresh_token="refresh1",
            client_id="client1",
            client_secret="secret1",
            token_uri="https://custom.oauth2.com/token",
        )

        client2 = GmailAPIClient(
            access_token="token2",
            refresh_token="refresh2",
            client_id="client2",
            client_secret="secret2",
            token_uri="https://oauth2.googleapis.com/token",
        )

        assert client1.creds.token_uri == "https://custom.oauth2.com/token"
        assert client2.creds.token_uri == "https://oauth2.googleapis.com/token"
        assert client1.creds.token != client2.creds.token

    def test_gmail_api_fetch_with_different_user_ids(self, gmail_client):
        """Test fetching emails with different user IDs."""
        # Mock empty responses
        gmail_client._mock_service.users.return_value.history.return_value.list.return_value.execute.return_value = {
            "history": []
        }

        # Test with different user IDs
        result1 = gmail_client.fetch_emails_since_history_id("me", "12345")
        result2 = gmail_client.fetch_emails_since_history_id(
            "user@example.com", "12345"
        )

        # Verify both calls work
        assert result1 == []
        assert result2 == []

        # Verify the correct user IDs were used
        calls = (
            gmail_client._mock_service.users.return_value.history.return_value.list.call_args_list
        )
        assert calls[0][1]["userId"] == "me"
        assert calls[1][1]["userId"] == "user@example.com"

    def test_gmail_api_fetch_with_different_history_ids(self, gmail_client):
        """Test fetching emails with different history IDs."""
        # Mock empty responses
        gmail_client._mock_service.users.return_value.history.return_value.list.return_value.execute.return_value = {
            "history": []
        }

        # Test with different history IDs
        result1 = gmail_client.fetch_emails_since_history_id("me", "12345")
        result2 = gmail_client.fetch_emails_since_history_id("me", "67890")

        # Verify both calls work
        assert result1 == []
        assert result2 == []

        # Verify the correct history IDs were used
        calls = (
            gmail_client._mock_service.users.return_value.history.return_value.list.call_args_list
        )
        assert calls[0][1]["startHistoryId"] == "12345"
        assert calls[1][1]["startHistoryId"] == "67890"

    def test_gmail_api_fetch_with_retry_parameters(self, gmail_client):
        """Test fetching emails with different retry parameters."""
        # Mock empty responses
        gmail_client._mock_service.users.return_value.history.return_value.list.return_value.execute.return_value = {
            "history": []
        }

        # Test with different max_retries values
        result1 = gmail_client.fetch_emails_since_history_id(
            "me", "12345", max_retries=3
        )
        result2 = gmail_client.fetch_emails_since_history_id(
            "me", "12345", max_retries=5
        )

        # Verify both calls work
        assert result1 == []
        assert result2 == []
