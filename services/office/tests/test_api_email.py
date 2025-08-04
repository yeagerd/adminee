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
    with patch("services.office.api.email.get_api_client_factory") as mock:
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

    @patch("services.office.api.email.fetch_provider_emails")
    @pytest.mark.asyncio
    async def test_get_email_messages_no_cache_bypass(
        self,
        mock_fetch_provider_emails,
        mock_cache_manager,
        mock_api_client_factory,
        mock_email_message,
        client,
        auth_headers,
    ):
        """Test that no_cache parameter bypasses cache."""
        # Mock fetch_provider_emails to return test data for both providers
        mock_fetch_provider_emails.side_effect = [
            ([mock_email_message], "google"),
            ([mock_email_message], "microsoft"),
        ]

        # Mock cache to return None (cache miss)
        mock_cache_manager.get_from_cache.return_value = None

        response = client.get(
            "/v1/email/messages?limit=10&no_cache=true", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["cache_hit"] is False
        assert len(data["data"]["messages"]) == 2  # One from each provider
        assert data["data"]["providers_used"] == ["google", "microsoft"]
        assert data["data"]["total_count"] == 2

        # Verify that fetch_provider_emails was called twice (once for each provider)
        assert mock_fetch_provider_emails.call_count == 2


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

    @patch("services.office.api.email.get_api_client_factory")
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
        mock_factory = AsyncMock()
        mock_factory.create_client = AsyncMock(return_value=mock_google_client)
        mock_create_client.return_value = mock_factory

        response = client.post(
            "/v1/email/send",
            json=send_email_request.model_dump(),
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["id"] == "gmail_sent_123"

        # Verify API client was created
        mock_create_client.assert_called_once()
        mock_factory.create_client.assert_called_once_with("test_user", "google")

    @patch("services.office.api.email.get_api_client_factory")
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
        mock_factory = AsyncMock()
        mock_factory.create_client = AsyncMock(return_value=mock_microsoft_client)
        mock_create_client.return_value = mock_factory

        response = client.post(
            "/v1/email/send",
            json=send_email_request.model_dump(),
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        # Microsoft generates a custom ID since the API doesn't return one
        assert data["data"]["id"].startswith("outlook_sent_")

        # Verify API client was created
        mock_create_client.assert_called_once()
        mock_factory.create_client.assert_called_once_with("test_user", "microsoft")

    @patch("services.office.api.email.get_user_email_providers")
    @patch("services.office.api.email.get_api_client_factory")
    @pytest.mark.asyncio
    async def test_send_email_default_provider(
        self,
        mock_create_client,
        mock_get_user_providers,
        client,
        auth_headers,
    ):
        """Test that default provider is dynamically selected when not specified."""
        # Create request without provider
        request_data = {
            "to": [{"email": "recipient@example.com", "name": "Test Recipient"}],
            "subject": "Test Email",
            "body": "Test body",
        }

        # Mock user providers to return Google as first available
        mock_get_user_providers.return_value = ["google", "microsoft"]

        # Mock API client factory to return None (no client available)
        mock_factory = AsyncMock()
        mock_factory.create_client = AsyncMock(return_value=None)
        mock_create_client.return_value = mock_factory

        response = client.post(
            "/v1/email/send",
            json=request_data,
            headers=auth_headers,
        )

        # Should fail because no client available, but verify it tried the first available provider
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Failed to create API client" in data["error"]["message"]
        mock_get_user_providers.assert_called_once_with("test_user")
        mock_create_client.assert_called_once()
        mock_factory.create_client.assert_called_once_with("test_user", "google")

    @patch("services.office.api.email.get_user_email_providers")
    @pytest.mark.asyncio
    async def test_send_email_no_providers_available(
        self,
        mock_get_user_providers,
        client,
        auth_headers,
    ):
        """Test sending email when no email providers are available."""
        # Create request without provider
        request_data = {
            "to": [{"email": "recipient@example.com", "name": "Test Recipient"}],
            "subject": "Test Email",
            "body": "Test body",
        }

        # Mock user providers to return empty list
        mock_get_user_providers.return_value = []

        response = client.post(
            "/v1/email/send",
            json=request_data,
            headers=auth_headers,
        )

        # Should fail because no providers available
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "No email providers available" in data["error"]["message"]
        mock_get_user_providers.assert_called_once_with("test_user")

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

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Unsupported provider" in data["error"]["message"]

    @patch("services.office.api.email.get_api_client_factory")
    @pytest.mark.asyncio
    async def test_send_email_case_insensitive_provider(
        self,
        mock_create_client,
        client,
        auth_headers,
    ):
        """Test that provider names are handled case-insensitively."""
        # Create request with capitalized provider
        request_data = {
            "to": [{"email": "recipient@example.com", "name": "Test Recipient"}],
            "subject": "Test Email",
            "body": "Test body",
            "provider": "Google",  # Capitalized
        }

        # Mock API client factory to return None (no client available)
        mock_factory = AsyncMock()
        mock_factory.create_client = AsyncMock(return_value=None)
        mock_create_client.return_value = mock_factory

        response = client.post(
            "/v1/email/send",
            json=request_data,
            headers=auth_headers,
        )

        # Should fail because no client available, but verify it tried the normalized provider
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Failed to create API client" in data["error"]["message"]
        mock_create_client.assert_called_once()
        mock_factory.create_client.assert_called_once_with(
            "test_user", "google"
        )  # Lowercase

    @patch("services.office.api.email.get_api_client_factory")
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
        mock_factory = AsyncMock()
        mock_factory.create_client = AsyncMock(return_value=None)
        mock_create_client.return_value = mock_factory

        response = client.post(
            "/v1/email/send",
            json=send_email_request.model_dump(),
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Failed to create API client" in data["error"]["message"]

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

    @patch("services.office.api.email.get_api_client_factory")
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
        mock_factory = AsyncMock()
        mock_factory.create_client = AsyncMock(return_value=mock_google_client)
        mock_create_client.return_value = mock_factory

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
        assert data["data"]["id"] == "gmail_sent_789"

        # Verify the client send_message was called
        mock_google_client.send_message.assert_called_once()

        # Verify API client was created
        mock_create_client.assert_called_once()
        mock_factory.create_client.assert_called_once_with("test_user", "google")

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

    def test_escape_odata_string_literal_basic(self):
        """Test basic OData string literal escaping."""
        from services.office.api.email import escape_odata_string_literal

        # Test normal string (no escaping needed)
        result = escape_odata_string_literal("normal_string")
        assert result == "normal_string"

        # Test string with single quote
        result = escape_odata_string_literal("O'Connor")
        assert result == "O''Connor"

        # Test string with multiple single quotes
        result = escape_odata_string_literal("can't won't don't")
        assert result == "can''t won''t don''t"

    def test_escape_odata_string_literal_edge_cases(self):
        """Test edge cases for OData string literal escaping."""
        from services.office.api.email import escape_odata_string_literal

        # Test empty string
        result = escape_odata_string_literal("")
        assert result == ""

        # Test string with only single quotes
        result = escape_odata_string_literal("'")
        assert result == "''"

        # Test string with consecutive single quotes
        result = escape_odata_string_literal("''")
        assert result == "''''"

        # Test string with mixed quotes
        result = escape_odata_string_literal("'hello' world")
        assert result == "''hello'' world"

    def test_escape_odata_string_literal_injection_attempts(self):
        """Test OData string literal escaping against injection attempts."""
        from services.office.api.email import escape_odata_string_literal

        # Test SQL injection attempt
        malicious_input = "'; DROP TABLE users; --"
        result = escape_odata_string_literal(malicious_input)
        expected = "''; DROP TABLE users; --"
        assert result == expected

        # Test OData injection attempt
        malicious_input = "'; eq 'admin' or id eq '"
        result = escape_odata_string_literal(malicious_input)
        expected = "''; eq ''admin'' or id eq ''"
        assert result == expected

        # Test with newlines and special characters
        malicious_input = "'; \n eq 'admin' \t or \r id eq '"
        result = escape_odata_string_literal(malicious_input)
        expected = "''; \n eq ''admin'' \t or \r id eq ''"
        assert result == expected

    def test_escape_odata_string_literal_invalid_input(self):
        """Test OData string literal escaping with invalid input types."""
        from services.office.api.email import escape_odata_string_literal

        # Test with None
        with pytest.raises(ValueError, match="Value must be a string"):
            escape_odata_string_literal(None)

        # Test with integer
        with pytest.raises(ValueError, match="Value must be a string"):
            escape_odata_string_literal(123)

        # Test with list
        with pytest.raises(ValueError, match="Value must be a string"):
            escape_odata_string_literal(["not", "a", "string"])

        # Test with dictionary
        with pytest.raises(ValueError, match="Value must be a string"):
            escape_odata_string_literal({"key": "value"})

    def test_escape_odata_string_literal_unicode(self):
        """Test OData string literal escaping with Unicode characters."""
        from services.office.api.email import escape_odata_string_literal

        # Test with Unicode characters
        unicode_string = "café résumé naïve"
        result = escape_odata_string_literal(unicode_string)
        assert result == unicode_string

        # Test with Unicode and single quotes
        unicode_with_quotes = "café's résumé's naïve's"
        result = escape_odata_string_literal(unicode_with_quotes)
        expected = "café''s résumé''s naïve''s"
        assert result == expected

        # Test with emoji and quotes
        emoji_string = "🚀 rocket's 🎉 party's 🎊"
        result = escape_odata_string_literal(emoji_string)
        expected = "🚀 rocket''s 🎉 party''s 🎊"
        assert result == expected


class TestFetchProviderEmails:
    """Tests for the fetch_provider_emails function."""

    @patch("services.office.api.email.get_api_client_factory")
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
        mock_factory = AsyncMock()
        mock_factory.create_client = AsyncMock(return_value=mock_client)
        mock_api_client_factory.return_value = mock_factory

        # Mock normalizer
        mock_normalize_google_email.return_value = mock_email_message

        result = await fetch_provider_emails(
            "req_123", "test_user", "google", 10, False, None, None, None, None
        )

        messages, provider = result
        assert len(messages) == 1
        assert provider == "google"
        assert messages[0] == mock_email_message

    @patch("services.office.api.email.get_api_client_factory")
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
        mock_factory = AsyncMock()
        mock_factory.create_client = AsyncMock(return_value=mock_client)
        mock_api_client_factory.return_value = mock_factory

        # Mock normalizer
        mock_normalize_microsoft_email.return_value = mock_email_message

        result = await fetch_provider_emails(
            "req_123", "test_user", "microsoft", 10, False, None, None, None, None
        )

        messages, provider = result
        assert len(messages) == 1
        assert provider == "microsoft"
        assert messages[0] == mock_email_message

    @patch("services.office.api.email.get_api_client_factory")
    @pytest.mark.asyncio
    async def test_fetch_provider_emails_api_client_failure(
        self, mock_api_client_factory
    ):
        """Test handling of API client creation failure."""
        from services.office.api.email import fetch_provider_emails

        # Mock API client factory to raise exception
        mock_factory = AsyncMock()
        mock_factory.create_client = AsyncMock(
            side_effect=Exception("Token retrieval failed")
        )
        mock_api_client_factory.return_value = mock_factory

        with pytest.raises(Exception) as exc_info:
            await fetch_provider_emails(
                "req_123", "test_user", "google", 10, False, None, None, None, None
            )

        assert "Token retrieval failed" in str(exc_info.value)


class TestFetchSingleMessage:
    """Tests for the fetch_single_message function."""

    @patch("services.office.api.email.get_api_client_factory")
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
        mock_factory = AsyncMock()
        mock_factory.create_client = AsyncMock(return_value=mock_client)
        mock_api_client_factory.return_value = mock_factory

        # Mock normalizer
        mock_normalize_google_email.return_value = mock_email_message

        result = await fetch_single_message(
            "req_123", "test_user", "google", "test123", True
        )

        assert result == mock_email_message

    @patch("services.office.api.email.get_api_client_factory")
    @pytest.mark.asyncio
    async def test_fetch_single_message_not_found(self, mock_api_client_factory):
        """Test handling of message not found."""
        from services.office.api.email import fetch_single_message

        # Mock API client factory to raise exception
        mock_factory = AsyncMock()
        mock_factory.create_client = AsyncMock(
            side_effect=Exception("Token retrieval failed")
        )
        mock_api_client_factory.return_value = mock_factory

        result = await fetch_single_message(
            "req_123", "test_user", "google", "test123", True
        )

        assert result is None


class TestODataInjectionProtection:
    """Tests to verify OData injection protection is working."""

    @patch("services.office.api.email.get_api_client_factory")
    @patch("services.office.api.email.normalize_microsoft_conversation")
    @pytest.mark.asyncio
    async def test_fetch_single_thread_escapes_original_thread_id(
        self, mock_normalize_microsoft_conversation, mock_api_client_factory
    ):
        """Test that fetch_single_thread properly escapes original_thread_id in OData filter."""
        from services.office.api.email import fetch_single_thread

        # Mock API client
        mock_client = AsyncMock()
        mock_client.get_messages.return_value = {"value": [{"id": "test123"}]}
        mock_factory = AsyncMock()
        mock_factory.create_client = AsyncMock(return_value=mock_client)
        mock_api_client_factory.return_value = mock_factory

        # Mock normalizer
        mock_normalize_microsoft_conversation.return_value = {"id": "test_thread"}

        # Test with malicious thread_id containing single quote
        malicious_thread_id = "thread'; DROP TABLE users; --"

        await fetch_single_thread(
            "req_123", "test_user", "microsoft", malicious_thread_id, True
        )

        # Verify that get_messages was called with properly escaped filter
        mock_client.get_messages.assert_called_once()
        call_args = mock_client.get_messages.call_args
        filter_param = call_args[1]["filter"]

        # The filter should contain the escaped thread_id
        expected_filter = "conversationId eq 'thread''; DROP TABLE users; --'"
        assert filter_param == expected_filter

    @patch("services.office.api.email.get_api_client_factory")
    @patch("services.office.api.email.normalize_microsoft_email")
    @pytest.mark.asyncio
    async def test_fetch_provider_emails_escapes_labels(
        self, mock_normalize_microsoft_email, mock_api_client_factory
    ):
        """Test that fetch_provider_emails properly escapes labels in OData filter."""
        from services.office.api.email import fetch_provider_emails

        # Mock API client
        mock_client = AsyncMock()
        mock_client.get_messages.return_value = {"value": [{"id": "test123"}]}
        mock_factory = AsyncMock()
        mock_factory.create_client = AsyncMock(return_value=mock_client)
        mock_api_client_factory.return_value = mock_factory

        # Mock normalizer
        mock_normalize_microsoft_email.return_value = {"id": "test_message"}

        # Test with malicious labels containing single quotes
        malicious_labels = [
            "normal_label",
            "label'; DROP TABLE users; --",
            "another'label",
        ]

        await fetch_provider_emails(
            "req_123",
            "test_user",
            "microsoft",
            10,
            False,
            malicious_labels,
            None,
            None,
            None,
        )

        # Verify that get_messages was called with properly escaped filter
        mock_client.get_messages.assert_called_once()
        call_args = mock_client.get_messages.call_args
        filter_param = call_args[1]["filter"]

        # The filter should contain the escaped labels
        expected_filter = "categories/any(c:c eq 'normal_label') or categories/any(c:c eq 'label''; DROP TABLE users; --') or categories/any(c:c eq 'another''label')"
        assert filter_param == expected_filter

    @patch("services.office.api.email.get_api_client_factory")
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
        mock_factory = AsyncMock()
        mock_factory.create_client = AsyncMock(return_value=mock_client)
        mock_api_client_factory.return_value = mock_factory

        # Mock normalizer
        mock_normalize_microsoft_email.return_value = mock_email_message

        result = await fetch_single_message(
            "req_123", "test_user", "microsoft", "test123", True
        )

        assert result == mock_email_message
        mock_client.get_message.assert_called_once_with("test123")

    @patch("services.office.api.email.get_api_client_factory")
    @pytest.mark.asyncio
    async def test_fetch_single_message_not_found(self, mock_api_client_factory):
        """Test handling of message not found."""
        from services.office.api.email import fetch_single_message

        # Mock API client to raise exception
        mock_client = AsyncMock()
        mock_client.get_message.side_effect = Exception("Message not found")
        mock_factory = AsyncMock()
        mock_factory.create_client = AsyncMock(return_value=mock_client)
        mock_api_client_factory.return_value = mock_factory

        result = await fetch_single_message(
            "req_123", "test_user", "google", "nonexistent", True
        )

        assert result is None


class TestEmailFoldersEndpoint:
    """Tests for the GET /email/folders endpoint."""

    @pytest.fixture
    def mock_email_folder(self):
        """Create a mock EmailFolder for testing."""
        from services.office.schemas import EmailFolder, Provider

        return EmailFolder(
            label="inbox",
            name="Inbox",
            provider=Provider.GOOGLE,
            provider_folder_id="INBOX",
            account_email="test@example.com",
            account_name="Test Account",
            is_system=True,
            message_count=42,
        )

    @patch("services.office.api.email.fetch_provider_folders")
    @pytest.mark.asyncio
    async def test_get_email_folders_success(
        self,
        mock_fetch_provider_folders,
        mock_cache_manager,
        mock_api_client_factory,
        mock_email_folder,
        client,
        auth_headers,
    ):
        """Test successful email folders fetching."""
        # Mock the fetch_provider_folders function
        mock_fetch_provider_folders.return_value = ([mock_email_folder], "google")

        # Mock cache miss
        mock_cache_manager.get_from_cache.return_value = None

        response = client.get("/v1/email/folders", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cache_hit"] is False
        assert "request_id" in data
        assert "data" in data

        # Verify the response structure
        response_data = data["data"]
        assert "folders" in response_data
        assert "providers_used" in response_data
        assert "provider_errors" in response_data

        # Verify folders data
        folders = response_data["folders"]
        assert len(folders) == 1
        assert folders[0]["label"] == "inbox"
        assert folders[0]["name"] == "Inbox"
        assert folders[0]["provider"] == "google"

        # Verify cache was called
        mock_cache_manager.set_to_cache.assert_called_once()

        # Verify the cached data is serializable (this would catch the original bug)
        cache_call_args = mock_cache_manager.set_to_cache.call_args
        cached_data = cache_call_args[0][1]  # Second argument is the data

        # This test would have caught the serialization error
        import json

        try:
            json.dumps(cached_data)
        except TypeError as e:
            pytest.fail(f"Cache data is not JSON serializable: {e}")

    @pytest.mark.asyncio
    async def test_get_email_folders_with_cache_hit(
        self,
        mock_cache_manager,
        mock_email_folder,
        client,
        auth_headers,
    ):
        """Test email folders with cache hit."""
        # Mock cache hit with serialized data
        cached_data = {
            "folders": [mock_email_folder.model_dump()],
            "providers_used": ["google"],
            "provider_errors": {},
        }
        mock_cache_manager.get_from_cache.return_value = cached_data

        response = client.get("/v1/email/folders", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cache_hit"] is True
        assert "request_id" in data

        # Verify the response structure
        response_data = data["data"]
        assert "folders" in response_data
        assert len(response_data["folders"]) == 1

        # Verify the folder was properly reconstructed from cache
        folder = response_data["folders"][0]
        assert folder["label"] == "inbox"
        assert folder["name"] == "Inbox"
        assert folder["provider"] == "google"

    @patch("services.office.api.email.fetch_provider_folders")
    @pytest.mark.asyncio
    async def test_get_email_folders_with_provider_errors(
        self,
        mock_fetch_provider_folders,
        mock_cache_manager,
        mock_api_client_factory,
        mock_email_folder,
        client,
        auth_headers,
    ):
        """Test email folders with provider errors."""
        # Mock one provider success, one failure
        mock_fetch_provider_folders.side_effect = [
            ([mock_email_folder], "google"),  # Google succeeds
            Exception("Microsoft API error"),  # Microsoft fails
        ]

        # Mock cache miss
        mock_cache_manager.get_from_cache.return_value = None

        response = client.get(
            "/v1/email/folders?providers=google&providers=microsoft",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cache_hit"] is False

        response_data = data["data"]
        assert "provider_errors" in response_data
        assert "microsoft" in response_data["provider_errors"]
        assert "Microsoft API error" in response_data["provider_errors"]["microsoft"]

    @pytest.mark.asyncio
    async def test_get_email_folders_invalid_providers(self, client, auth_headers):
        """Test email folders with invalid providers."""
        response = client.get(
            "/v1/email/folders?providers=invalid", headers=auth_headers
        )

        # The endpoint returns 502 when no valid providers are specified
        assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_get_email_folders_missing_user_id(self, client):
        """Test email folders without user ID."""
        response = client.get("/v1/email/folders")

        assert response.status_code == 401  # Unauthorized

    @patch("services.office.api.email.fetch_provider_folders")
    @pytest.mark.asyncio
    async def test_get_email_folders_no_cache_bypass(
        self,
        mock_fetch_provider_folders,
        mock_cache_manager,
        mock_api_client_factory,
        mock_email_folder,
        client,
        auth_headers,
    ):
        """Test email folders with no_cache bypass."""
        # Mock the fetch_provider_folders function
        mock_fetch_provider_folders.return_value = ([mock_email_folder], "google")

        # Mock cache hit (should be ignored due to no_cache=True)
        cached_data = {"folders": [], "providers_used": [], "provider_errors": {}}
        mock_cache_manager.get_from_cache.return_value = cached_data

        response = client.get("/v1/email/folders?no_cache=true", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cache_hit"] is False  # Should be False due to no_cache bypass

        # Verify fresh data was fetched
        mock_fetch_provider_folders.assert_called()

    @patch("services.office.api.email.fetch_provider_folders")
    @pytest.mark.asyncio
    async def test_get_email_folders_serialization_error_caught(
        self,
        mock_fetch_provider_folders,
        mock_cache_manager,
        mock_api_client_factory,
        mock_email_folder,
        client,
        auth_headers,
    ):
        """Test that would have caught the original serialization error."""
        # Mock the fetch_provider_folders function
        mock_fetch_provider_folders.return_value = ([mock_email_folder], "google")

        # Mock cache miss
        mock_cache_manager.get_from_cache.return_value = None

        # This test specifically verifies that the cache data is serializable
        # The original bug would have caused this test to fail
        response = client.get("/v1/email/folders", headers=auth_headers)

        assert response.status_code == 200

        # Verify cache was called and the data is serializable
        mock_cache_manager.set_to_cache.assert_called_once()
        cache_call_args = mock_cache_manager.set_to_cache.call_args
        cached_data = cache_call_args[0][1]  # Second argument is the data

        # This assertion would have failed with the original bug
        import json

        try:
            serialized = json.dumps(cached_data)
            # Additional verification that the serialized data can be deserialized
            deserialized = json.loads(serialized)
            assert "folders" in deserialized
            assert len(deserialized["folders"]) == 1
            assert deserialized["folders"][0]["label"] == "inbox"
        except TypeError as e:
            pytest.fail(f"Cache data is not JSON serializable: {e}")
        except json.JSONDecodeError as e:
            pytest.fail(f"Serialized cache data is not valid JSON: {e}")

    @patch("services.office.api.email.fetch_provider_folders")
    @pytest.mark.asyncio
    async def test_get_email_folders_duplicate_removal(
        self,
        mock_fetch_provider_folders,
        mock_cache_manager,
        mock_api_client_factory,
        mock_email_folder,
        client,
        auth_headers,
    ):
        """Test that duplicate folders are removed based on label."""
        # Create a duplicate folder with same label but different name
        duplicate_folder = mock_email_folder.model_copy(
            update={"name": "Inbox (Duplicate)"}
        )

        # Mock both providers returning the same folder
        mock_fetch_provider_folders.side_effect = [
            ([mock_email_folder], "google"),
            ([duplicate_folder], "microsoft"),
        ]

        # Mock cache miss
        mock_cache_manager.get_from_cache.return_value = None

        response = client.get(
            "/v1/email/folders?providers=google&providers=microsoft",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        response_data = data["data"]

        # Should only have one folder (duplicates removed)
        assert len(response_data["folders"]) == 1
        assert response_data["folders"][0]["label"] == "inbox"
        # Should keep the first occurrence (Google's version)
        assert response_data["folders"][0]["name"] == "Inbox"
