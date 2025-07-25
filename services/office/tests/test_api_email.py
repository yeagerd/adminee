"""
Unit tests for email API endpoints.

Tests email listing, searching, sending, and management functionality
for both Google and Microsoft providers with comprehensive error handling.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from services.office.app.main import app
from services.office.models import Provider
from services.office.schemas import EmailAddress, EmailMessage, SendEmailRequest


@pytest.fixture(autouse=True)
def patch_settings():
    """Patch the _settings global variable to return test settings."""
    import services.office.core.settings as office_settings

    test_settings = office_settings.Settings(
        db_url_office="sqlite:///:memory:",
        api_frontend_office_key="test-frontend-office-key",
        api_chat_office_key="test-chat-office-key",
        api_meetings_office_key="test-meetings-office-key",
        api_office_user_key="test-office-user-key",
    )

    # Directly set the singleton instead of using monkeypatch
    office_settings._settings = test_settings
    yield
    office_settings._settings = None


@pytest.fixture
def client():
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authentication headers with X-User-Id and API key."""
    return {"X-User-Id": "test_user", "X-API-Key": "test-frontend-office-key"}


@pytest.fixture
def mock_email_message():
    """Create a mock EmailMessage for testing."""
    return EmailMessage(
        id="gmail_test123",
        provider=Provider.GOOGLE,
        provider_message_id="test123",
        subject="Test Email",
        from_address=EmailAddress(email="sender@example.com", name="Test Sender"),
        to_addresses=[
            EmailAddress(email="recipient@example.com", name="Test Recipient")
        ],
        date=datetime.now(timezone.utc),
        body_text="Test email body",
        body_html="<p>Test email body</p>",
        labels=["INBOX"],
        account_email="user@gmail.com",
        account_name="Test Account",
    )


@pytest.fixture
def mock_cache_manager():
    """Mock the cache manager."""
    with patch("services.office.api.email.cache_manager") as mock:
        mock.get_from_cache = AsyncMock(return_value=None)
        mock.set_to_cache = AsyncMock()
        yield mock


@pytest.fixture
def mock_api_client_factory():
    """Mock the API client factory."""
    with patch("services.office.api.email.api_client_factory") as mock:
        yield mock


class TestEmailMessagesEndpoint:
    """Tests for the GET /email/messages endpoint."""

    @patch("services.office.api.email.fetch_provider_emails")
    @pytest.mark.asyncio
    async def test_get_email_messages_success(
        self,
        mock_fetch_provider_emails,
        mock_cache_manager,
        mock_api_client_factory,
        mock_email_message,
        client,
        auth_headers,
    ):
        """Test successful email messages retrieval."""
        # Mock fetch_provider_emails to return test data
        mock_fetch_provider_emails.side_effect = [
            ([mock_email_message], "google"),
            ([mock_email_message], "microsoft"),
        ]

        response = client.get("/v1/email/messages?limit=10", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["cache_hit"] is False
        assert len(data["data"]["messages"]) == 2
        assert data["data"]["providers_used"] == ["google", "microsoft"]
        assert data["data"]["total_count"] == 2

    @patch("services.office.api.email.fetch_provider_emails")
    @pytest.mark.asyncio
    async def test_get_email_messages_with_cache_hit(
        self,
        mock_fetch_provider_emails,
        mock_cache_manager,
        mock_api_client_factory,
        client,
        auth_headers,
    ):
        """Test email messages retrieval with cache hit."""
        # Mock cache to return cached data
        cached_data = {
            "messages": [],
            "total_count": 0,
            "providers_used": ["google"],
            "provider_errors": None,
        }
        mock_cache_manager.get_from_cache.return_value = cached_data

        response = client.get("/v1/email/messages?limit=10", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["cache_hit"] is True
        assert data["data"] == cached_data

        # Ensure fetch_provider_emails was not called due to cache hit
        mock_fetch_provider_emails.assert_not_called()

    @patch("services.office.api.email.fetch_provider_emails")
    @pytest.mark.asyncio
    async def test_get_email_messages_with_provider_errors(
        self,
        mock_fetch_provider_emails,
        mock_cache_manager,
        mock_api_client_factory,
        client,
        auth_headers,
    ):
        """Test email messages retrieval with provider errors."""
        # Mock one provider success, one failure
        mock_fetch_provider_emails.side_effect = [
            Exception("Provider failed"),
            ([], "microsoft"),
        ]

        response = client.get("/v1/email/messages?limit=10", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["provider_errors"]["google"] == "Provider failed"
        assert data["data"]["providers_used"] == ["microsoft"]

    @pytest.mark.asyncio
    async def test_get_email_messages_invalid_providers(self, client, auth_headers):
        """Test email messages with invalid provider names."""
        response = client.get(
            "/v1/email/messages?providers=invalid", headers=auth_headers
        )

        assert response.status_code == 422  # ValidationError now returns 422
        assert "No valid providers specified" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_get_email_messages_missing_user_id(self, client):
        """Test email messages without X-User-Id header."""
        # Include API key but not user ID
        headers = {"X-API-Key": "test-frontend-office-key"}
        response = client.get("/v1/email/messages", headers=headers)

        assert response.status_code == 422  # Validation error

    @patch("services.office.api.email.fetch_provider_emails")
    @pytest.mark.asyncio
    async def test_get_email_messages_no_caching_when_all_providers_fail(
        self,
        mock_fetch_provider_emails,
        mock_cache_manager,
        mock_api_client_factory,
        client,
        auth_headers,
    ):
        """Test that email messages are not cached when all providers fail."""
        # Mock cache miss
        mock_cache_manager.get_from_cache.return_value = None

        # Mock all providers failing with different error types
        mock_fetch_provider_emails.side_effect = [
            Exception("Token expired"),
            Exception("Authentication failed"),
        ]

        # Mock API client factory to return None (simulating no valid clients)
        mock_api_client_factory.create_client.return_value = None

        response = client.get("/v1/email/messages?limit=10", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["success"] is True
        assert data["data"]["messages"] == []
        assert data["data"]["total_count"] == 0
        assert data["data"]["providers_used"] == []
        assert data["data"]["provider_errors"] is not None
        assert len(data["data"]["provider_errors"]) == 2

        # Verify that the response was NOT cached since all providers failed
        mock_cache_manager.set_to_cache.assert_not_called()

        # Verify that cache was checked but not set
        mock_cache_manager.get_from_cache.assert_called_once()
        assert mock_cache_manager.set_to_cache.call_count == 0


class TestEmailMessageDetailEndpoint:
    """Tests for the GET /email/messages/{message_id} endpoint."""

    @patch("services.office.api.email.fetch_single_message")
    @pytest.mark.asyncio
    async def test_get_email_message_success(
        self,
        mock_fetch_single_message,
        mock_cache_manager,
        mock_api_client_factory,
        mock_email_message,
        client,
        auth_headers,
    ):
        """Test successful single email message retrieval."""
        mock_fetch_single_message.return_value = mock_email_message

        response = client.get("/v1/email/messages/gmail_test123", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["cache_hit"] is False
        assert data["data"]["message"]["id"] == "gmail_test123"
        assert data["data"]["provider"] == "google"

    @patch("services.office.api.email.fetch_single_message")
    @pytest.mark.asyncio
    async def test_get_email_message_not_found(
        self,
        mock_fetch_single_message,
        mock_cache_manager,
        mock_api_client_factory,
        client,
        auth_headers,
    ):
        """Test email message not found."""
        mock_fetch_single_message.return_value = None

        response = client.get(
            "/v1/email/messages/gmail_nonexistent", headers=auth_headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["message"]


class TestSendEmailEndpoint:
    """Tests for the POST /email/send endpoint."""

    @pytest.fixture
    def send_email_request(self):
        """Create a sample send email request."""
        return SendEmailRequest(
            to=[EmailAddress(email="recipient@example.com", name="Test Recipient")],
            subject="Test Email",
            body="This is a test email body.",
            cc=[EmailAddress(email="cc@example.com", name="CC Recipient")],
            provider="google",
        )

    @patch("services.office.api.email.api_client_factory.create_client")
    @pytest.mark.asyncio
    async def test_send_email_google_success(
        self,
        mock_create_client,
        send_email_request,
        client,
        auth_headers,
    ):
        """Test successful email sending via Google."""
        # Create a mock client that properly handles async context manager
        mock_google_client = AsyncMock()

        # Mock the async context manager methods
        async def mock_aenter(self):
            return mock_google_client

        async def mock_aexit(self, exc_type, exc_val, exc_tb):
            return None

        mock_google_client.__aenter__ = mock_aenter
        mock_google_client.__aexit__ = mock_aexit

        # Mock the send_message method
        mock_google_client.send_message = AsyncMock(
            return_value={"id": "gmail_sent_123"}
        )

        # Configure the factory to return our mock client
        mock_create_client.return_value = mock_google_client

        response = client.post(
            "/v1/email/send",
            json=send_email_request.model_dump(),
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["message_id"] == "gmail_sent_123"
        assert data["data"]["provider"] == "google"
        assert data["data"]["status"] == "sent"

        # Verify API client was created
        mock_create_client.assert_called_once_with("test_user", "google")

    @patch("services.office.api.email.api_client_factory.create_client")
    @pytest.mark.asyncio
    async def test_send_email_microsoft_success(
        self,
        mock_create_client,
        send_email_request,
        client,
        auth_headers,
    ):
        """Test successful email sending via Microsoft."""
        # Modify request to use Microsoft
        send_email_request.provider = "microsoft"

        # Create a mock client that properly handles async context manager
        mock_microsoft_client = AsyncMock()

        # Mock the async context manager methods
        async def mock_aenter(self):
            return mock_microsoft_client

        async def mock_aexit(self, exc_type, exc_val, exc_tb):
            return None

        mock_microsoft_client.__aenter__ = mock_aenter
        mock_microsoft_client.__aexit__ = mock_aexit

        # Mock the send_message method (Microsoft returns None)
        mock_microsoft_client.send_message = AsyncMock(return_value=None)

        # Configure the factory to return our mock client
        mock_create_client.return_value = mock_microsoft_client

        response = client.post(
            "/v1/email/send",
            json=send_email_request.model_dump(),
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        # Microsoft generates a custom ID since the API doesn't return one
        assert data["data"]["message_id"].startswith("outlook_sent_")
        assert data["data"]["provider"] == "microsoft"
        assert data["data"]["status"] == "sent"

        # Verify API client was created
        mock_create_client.assert_called_once_with("test_user", "microsoft")

    @patch("services.office.api.email.api_client_factory.create_client")
    @pytest.mark.asyncio
    async def test_send_email_default_provider(
        self,
        mock_create_client,
        client,
        auth_headers,
    ):
        """Test that default provider is Google when not specified."""
        # Create request without provider
        request_data = {
            "to": [{"email": "recipient@example.com", "name": "Test Recipient"}],
            "subject": "Test Email",
            "body": "Test body",
        }

        # Mock API client factory to return None (no client available)
        mock_create_client.return_value = None

        response = client.post(
            "/v1/email/send",
            json=request_data,
            headers=auth_headers,
        )

        # Should fail because no client available, but verify it tried Google
        assert response.status_code == 502  # ServiceError now returns 502
        mock_create_client.assert_called_once_with("test_user", "google")

    @pytest.mark.asyncio
    async def test_send_email_invalid_provider(self, client, auth_headers):
        """Test sending email with invalid provider."""
        request_data = {
            "to": [{"email": "recipient@example.com", "name": "Test Recipient"}],
            "subject": "Test Email",
            "body": "Test body",
            "provider": "invalid_provider",
        }

        response = client.post(
            "/v1/email/send",
            json=request_data,
            headers=auth_headers,
        )

        assert response.status_code == 422  # ValidationError now returns 422
        assert "Invalid provider" in response.json()["message"]

    @patch("services.office.api.email.api_client_factory.create_client")
    @pytest.mark.asyncio
    async def test_send_email_no_client_available(
        self,
        mock_create_client,
        send_email_request,
        client,
        auth_headers,
    ):
        """Test sending email when no API client is available."""
        # Mock API client factory to return None
        mock_create_client.return_value = None

        response = client.post(
            "/v1/email/send",
            json=send_email_request.model_dump(),
            headers=auth_headers,
        )

        assert response.status_code == 502  # ServiceError now returns 502
        assert "Failed to create API client" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_send_email_missing_user_id(self, send_email_request, client):
        """Test sending email without X-User-Id header."""
        # Include API key but not user ID
        headers = {"X-API-Key": "test-frontend-office-key"}
        response = client.post(
            "/v1/email/send",
            json=send_email_request.model_dump(),
            headers=headers,
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_send_email_invalid_request_data(self, client, auth_headers):
        """Test sending email with invalid request data."""
        # Missing required fields
        request_data = {
            "subject": "Test Email",
            # Missing 'to' and 'body'
        }

        response = client.post(
            "/v1/email/send",
            json=request_data,
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    @patch("services.office.api.email.api_client_factory.create_client")
    @pytest.mark.asyncio
    async def test_send_email_with_all_fields(
        self,
        mock_create_client,
        client,
        auth_headers,
    ):
        """Test sending email with all optional fields."""
        # Create a mock client that properly handles async context manager
        mock_google_client = AsyncMock()

        # Mock the async context manager methods
        async def mock_aenter(self):
            return mock_google_client

        async def mock_aexit(self, exc_type, exc_val, exc_tb):
            return None

        mock_google_client.__aenter__ = mock_aenter
        mock_google_client.__aexit__ = mock_aexit

        # Mock the send_message method
        mock_google_client.send_message = AsyncMock(
            return_value={"id": "gmail_sent_789"}
        )

        # Configure the factory to return our mock client
        mock_create_client.return_value = mock_google_client

        request_data = {
            "to": [{"email": "to@example.com", "name": "To Recipient"}],
            "cc": [{"email": "cc@example.com", "name": "CC Recipient"}],
            "bcc": [{"email": "bcc@example.com", "name": "BCC Recipient"}],
            "subject": "Test Email with All Fields",
            "body": "This is a comprehensive test email.",
            "provider": "google",
            "importance": "high",
            "reply_to_message_id": "gmail_original_123",
        }

        response = client.post(
            "/v1/email/send",
            json=request_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["message_id"] == "gmail_sent_789"
        assert data["data"]["provider"] == "google"

        # Verify the client send_message was called
        mock_google_client.send_message.assert_called_once()

        # Verify API client was created
        mock_create_client.assert_called_once_with("test_user", "google")

    @pytest.mark.asyncio
    async def test_get_email_message_invalid_id_format(self, client, auth_headers):
        """Test invalid message ID format."""
        response = client.get("/v1/email/messages/invalid_id", headers=auth_headers)
        assert response.status_code == 422  # ValidationError now returns 422
        assert "Invalid message ID format" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_get_email_message_with_cache_hit(
        self, mock_cache_manager, client, auth_headers
    ):
        """Test email message retrieval with cache hit."""
        cached_data = {
            "message": {"id": "gmail_test123", "subject": "Test"},
            "provider": "google",
        }
        mock_cache_manager.get_from_cache.return_value = cached_data

        response = client.get("/v1/email/messages/gmail_test123", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["cache_hit"] is True
        assert data["data"] == cached_data


class TestEmailHelperFunctions:
    """Tests for helper functions in the email module."""

    def test_parse_message_id_valid_gmail(self):
        """Test parsing valid Gmail message ID."""
        from services.office.api.email import parse_message_id

        provider, original_id = parse_message_id("gmail_abc123")

        assert provider == "google"
        assert original_id == "abc123"

    def test_parse_message_id_valid_outlook(self):
        """Test parsing valid Outlook message ID."""
        from services.office.api.email import parse_message_id

        provider, original_id = parse_message_id("microsoft_xyz789")

        assert provider == "microsoft"
        assert original_id == "xyz789"

    def test_parse_message_id_invalid_format(self):
        """Test parsing invalid message ID format."""
        from services.common.http_errors import ValidationError
        from services.office.api.email import parse_message_id

        with pytest.raises(ValidationError) as exc_info:
            parse_message_id("invalid_format_no_underscore")

        assert exc_info.value.status_code == 422
        assert "Invalid message ID format" in str(exc_info.value.message)

    def test_parse_message_id_unknown_provider(self):
        """Test parsing message ID with unknown provider."""
        from services.common.http_errors import ValidationError
        from services.office.api.email import parse_message_id

        with pytest.raises(ValidationError) as exc_info:
            parse_message_id("unknown_abc123")

        assert exc_info.value.status_code == 422
        assert "Invalid message ID format" in str(exc_info.value.message)


class TestFetchProviderEmails:
    """Tests for the fetch_provider_emails function."""

    @patch("services.office.api.email.api_client_factory")
    @patch("services.office.api.email.normalize_google_email")
    @pytest.mark.asyncio
    async def test_fetch_google_emails_success(
        self, mock_normalize_google_email, mock_api_client_factory, mock_email_message
    ):
        """Test successful Google email fetching."""
        from services.office.api.email import fetch_provider_emails

        # Mock API client
        mock_client = AsyncMock()
        mock_client.get_messages.return_value = {"messages": [{"id": "test123"}]}
        mock_client.get_message.return_value = {"id": "test123", "payload": {}}
        mock_api_client_factory.create_client = AsyncMock(return_value=mock_client)

        # Mock normalizer
        mock_normalize_google_email.return_value = mock_email_message

        result = await fetch_provider_emails(
            "req_123", "test_user", "google", 10, False, None, None, None
        )

        messages, provider = result
        assert len(messages) == 1
        assert provider == "google"
        assert messages[0] == mock_email_message

    @patch("services.office.api.email.api_client_factory")
    @patch("services.office.api.email.normalize_microsoft_email")
    @pytest.mark.asyncio
    async def test_fetch_microsoft_emails_success(
        self,
        mock_normalize_microsoft_email,
        mock_api_client_factory,
        mock_email_message,
    ):
        """Test successful Microsoft email fetching."""
        from services.office.api.email import fetch_provider_emails

        # Mock API client
        mock_client = AsyncMock()
        mock_client.get_messages.return_value = {"value": [{"id": "test123"}]}
        mock_api_client_factory.create_client = AsyncMock(return_value=mock_client)

        # Mock normalizer
        mock_normalize_microsoft_email.return_value = mock_email_message

        result = await fetch_provider_emails(
            "req_123", "test_user", "microsoft", 10, False, None, None, None
        )

        messages, provider = result
        assert len(messages) == 1
        assert provider == "microsoft"
        assert messages[0] == mock_email_message

    @patch("services.office.api.email.api_client_factory")
    @pytest.mark.asyncio
    async def test_fetch_provider_emails_api_client_failure(
        self, mock_api_client_factory
    ):
        """Test handling of API client creation failure."""
        from services.office.api.email import fetch_provider_emails

        # Mock API client factory to raise exception
        mock_api_client_factory.create_client = AsyncMock(
            side_effect=Exception("Token retrieval failed")
        )

        with pytest.raises(Exception) as exc_info:
            await fetch_provider_emails(
                "req_123", "test_user", "google", 10, False, None, None, None
            )

        assert "Token retrieval failed" in str(exc_info.value)


class TestFetchSingleMessage:
    """Tests for the fetch_single_message function."""

    @patch("services.office.api.email.api_client_factory")
    @patch("services.office.api.email.normalize_google_email")
    @pytest.mark.asyncio
    async def test_fetch_single_google_message_success(
        self, mock_normalize_google_email, mock_api_client_factory, mock_email_message
    ):
        """Test successful single Google message fetching."""
        from services.office.api.email import fetch_single_message

        # Mock API client
        mock_client = AsyncMock()
        mock_client.get_message.return_value = {"id": "test123", "payload": {}}
        mock_api_client_factory.create_client = AsyncMock(return_value=mock_client)

        # Mock normalizer
        mock_normalize_google_email.return_value = mock_email_message

        result = await fetch_single_message(
            "req_123", "test_user", "google", "test123", True
        )

        assert result == mock_email_message
        mock_client.get_message.assert_called_once_with("test123", format="full")

    @patch("services.office.api.email.api_client_factory")
    @patch("services.office.api.email.normalize_microsoft_email")
    @pytest.mark.asyncio
    async def test_fetch_single_microsoft_message_success(
        self,
        mock_normalize_microsoft_email,
        mock_api_client_factory,
        mock_email_message,
    ):
        """Test successful single Microsoft message fetching."""
        from services.office.api.email import fetch_single_message

        # Mock API client
        mock_client = AsyncMock()
        mock_client.get_message.return_value = {"id": "test123"}
        mock_api_client_factory.create_client = AsyncMock(return_value=mock_client)

        # Mock normalizer
        mock_normalize_microsoft_email.return_value = mock_email_message

        result = await fetch_single_message(
            "req_123", "test_user", "microsoft", "test123", True
        )

        assert result == mock_email_message
        mock_client.get_message.assert_called_once_with("test123")

    @patch("services.office.api.email.api_client_factory")
    @pytest.mark.asyncio
    async def test_fetch_single_message_not_found(self, mock_api_client_factory):
        """Test handling of message not found."""
        from services.office.api.email import fetch_single_message

        # Mock API client to raise exception
        mock_client = AsyncMock()
        mock_client.get_message.side_effect = Exception("Message not found")
        mock_api_client_factory.create_client = AsyncMock(return_value=mock_client)

        result = await fetch_single_message(
            "req_123", "test_user", "google", "nonexistent", True
        )

        assert result is None
