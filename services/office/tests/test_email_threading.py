"""
Tests for email threading functionality.

Tests the new thread API endpoints and normalization functions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from services.office.api.email import (
    get_email_threads,
    get_email_thread,
    get_message_thread,
    parse_thread_id,
    fetch_provider_threads,
    fetch_single_thread,
    fetch_message_thread,
)
from services.office.core.normalizer import (
    normalize_google_thread,
    normalize_microsoft_conversation,
    normalize_thread_id,
    merge_threads,
)
from services.office.schemas import EmailThread, EmailMessage, EmailAddress, Provider


class TestThreadIDParsing:
    """Test thread ID parsing functionality."""

    def test_parse_thread_id_valid(self):
        """Test parsing valid thread IDs."""
        # Test Gmail thread ID
        provider, thread_id = parse_thread_id("gmail_12345")
        assert provider == "google"
        assert thread_id == "12345"

        # Test Microsoft thread ID
        provider, thread_id = parse_thread_id("microsoft_abc123")
        assert provider == "microsoft"
        assert thread_id == "abc123"

        # Test with different prefixes
        provider, thread_id = parse_thread_id("google_thread456")
        assert provider == "google"
        assert thread_id == "thread456"

        provider, thread_id = parse_thread_id("outlook_conv789")
        assert provider == "microsoft"
        assert thread_id == "conv789"

    def test_parse_thread_id_invalid(self):
        """Test parsing invalid thread IDs."""
        with pytest.raises(ValueError, match="Invalid thread ID format"):
            parse_thread_id("invalid")

        with pytest.raises(ValueError, match="Invalid thread ID format"):
            parse_thread_id("gmail")

        with pytest.raises(ValueError, match="Unknown provider prefix"):
            parse_thread_id("unknown_123")


class TestThreadNormalization:
    """Test thread normalization functions."""

    def test_normalize_thread_id(self):
        """Test thread ID normalization."""
        assert normalize_thread_id("google", "123") == "gmail_123"
        assert normalize_thread_id("microsoft", "abc") == "microsoft_abc"
        assert normalize_thread_id("gmail", "456") == "gmail_456"
        assert normalize_thread_id("outlook", "def") == "microsoft_def"

    def test_normalize_google_thread(self):
        """Test Gmail thread normalization."""
        # Create mock Gmail thread data
        mock_thread_data = {
            "id": "thread123",
            "messages": [
                {
                    "id": "msg1",
                    "threadId": "thread123",
                    "snippet": "Test message 1",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Test Thread"},
                            {"name": "From", "value": "sender@example.com"},
                            {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"},
                        ]
                    },
                    "labelIds": ["INBOX"],
                },
                {
                    "id": "msg2",
                    "threadId": "thread123",
                    "snippet": "Test message 2",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Re: Test Thread"},
                            {"name": "From", "value": "reply@example.com"},
                            {"name": "Date", "value": "Mon, 1 Jan 2024 13:00:00 +0000"},
                        ]
                    },
                    "labelIds": ["INBOX", "UNREAD"],
                }
            ]
        }

        thread = normalize_google_thread(mock_thread_data, "user@example.com", "Test User")
        
        assert thread.id == "gmail_thread123"
        assert thread.subject == "Test Thread"
        assert len(thread.messages) == 2
        assert thread.participant_count >= 2
        assert thread.providers == [Provider.GOOGLE]

    def test_normalize_microsoft_conversation(self):
        """Test Microsoft conversation normalization."""
        # Create mock Microsoft conversation data
        mock_conv_data = {
            "id": "conv123",
            "topic": "Test Conversation",
        }
        
        mock_messages_data = [
            {
                "id": "msg1",
                "conversationId": "conv123",
                "subject": "Test Conversation",
                "bodyPreview": "Test message 1",
                "from": {"emailAddress": {"address": "sender@example.com", "name": "Sender"}},
                "toRecipients": [{"emailAddress": {"address": "recipient@example.com", "name": "Recipient"}}],
                "receivedDateTime": "2024-01-01T12:00:00Z",
                "isRead": True,
                "hasAttachments": False,
            },
            {
                "id": "msg2",
                "conversationId": "conv123",
                "subject": "Re: Test Conversation",
                "bodyPreview": "Test message 2",
                "from": {"emailAddress": {"address": "reply@example.com", "name": "Replier"}},
                "toRecipients": [{"emailAddress": {"address": "sender@example.com", "name": "Sender"}}],
                "receivedDateTime": "2024-01-01T13:00:00Z",
                "isRead": False,
                "hasAttachments": False,
            }
        ]

        thread = normalize_microsoft_conversation(
            mock_conv_data, mock_messages_data, "user@example.com", "Test User"
        )
        
        assert thread.id == "microsoft_conv123"
        assert thread.subject == "Test Conversation"
        assert len(thread.messages) == 2
        assert thread.participant_count >= 2
        assert thread.providers == [Provider.MICROSOFT]

    def test_merge_threads(self):
        """Test thread merging functionality."""
        # Create two threads that should be merged
        thread1 = EmailThread(
            id="gmail_thread1",
            subject="Test Thread",
            messages=[
                EmailMessage(
                    id="gmail_msg1",
                    subject="Test Thread",
                    from_address=EmailAddress(email="sender@example.com"),
                    to_addresses=[EmailAddress(email="recipient@example.com")],
                    date=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                    provider=Provider.GOOGLE,
                    provider_message_id="msg1",
                    account_email="user@example.com",
                )
            ],
            participant_count=2,
            last_message_date=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            is_read=True,
            providers=[Provider.GOOGLE],
        )

        thread2 = EmailThread(
            id="microsoft_conv1",
            subject="Test Thread",
            messages=[
                EmailMessage(
                    id="microsoft_msg1",
                    subject="Test Thread",
                    from_address=EmailAddress(email="sender@example.com"),
                    to_addresses=[EmailAddress(email="recipient@example.com")],
                    date=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                    provider=Provider.MICROSOFT,
                    provider_message_id="msg1",
                    account_email="user@example.com",
                )
            ],
            participant_count=2,
            last_message_date=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            is_read=True,
            providers=[Provider.MICROSOFT],
        )

        merged_threads = merge_threads([thread1, thread2])
        
        assert len(merged_threads) == 1
        merged_thread = merged_threads[0]
        assert len(merged_thread.messages) == 2
        assert Provider.GOOGLE in merged_thread.providers
        assert Provider.MICROSOFT in merged_thread.providers


class TestThreadAPIEndpoints:
    """Test thread API endpoints."""

    @pytest.mark.asyncio
    async def test_get_email_threads_success(self):
        """Test successful thread fetching."""
        with patch('services.office.api.email.fetch_provider_threads') as mock_fetch:
            mock_fetch.return_value = ([], "google")
            
            # Mock request and dependencies
            mock_request = MagicMock()
            mock_request.headers = {"X-User-Id": "test_user"}
            
            with patch('services.office.api.email.get_request_id') as mock_request_id:
                mock_request_id.return_value = "test_request"
                
                with patch('services.office.api.email.cache_manager.get') as mock_cache_get:
                    mock_cache_get.return_value = None
                    
                    with patch('services.office.api.email.cache_manager.set') as mock_cache_set:
                        response = await get_email_threads(
                            request=mock_request,
                            service_name="test_service",
                            providers=["google"],
                            limit=10,
                        )
                        
                        assert response.success is True
                        assert "threads" in response.data
                        mock_cache_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_email_thread_success(self):
        """Test successful single thread fetching."""
        with patch('services.office.api.email.fetch_single_thread') as mock_fetch:
            mock_thread = EmailThread(
                id="gmail_thread1",
                subject="Test Thread",
                messages=[],
                participant_count=2,
                last_message_date=datetime.now(timezone.utc),
                is_read=True,
                providers=[Provider.GOOGLE],
            )
            mock_fetch.return_value = mock_thread
            
            # Mock request and dependencies
            mock_request = MagicMock()
            mock_request.headers = {"X-User-Id": "test_user"}
            
            with patch('services.office.api.email.get_request_id') as mock_request_id:
                mock_request_id.return_value = "test_request"
                
                with patch('services.office.api.email.cache_manager.get') as mock_cache_get:
                    mock_cache_get.return_value = None
                    
                    with patch('services.office.api.email.cache_manager.set') as mock_cache_set:
                        response = await get_email_thread(
                            request=mock_request,
                            thread_id="gmail_thread1",
                            service_name="test_service",
                        )
                        
                        assert response.success is True
                        assert "thread" in response.data
                        mock_cache_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_message_thread_success(self):
        """Test successful message thread fetching."""
        with patch('services.office.api.email.fetch_message_thread') as mock_fetch:
            mock_thread = EmailThread(
                id="gmail_thread1",
                subject="Test Thread",
                messages=[],
                participant_count=2,
                last_message_date=datetime.now(timezone.utc),
                is_read=True,
                providers=[Provider.GOOGLE],
            )
            mock_fetch.return_value = mock_thread
            
            # Mock request and dependencies
            mock_request = MagicMock()
            mock_request.headers = {"X-User-Id": "test_user"}
            
            with patch('services.office.api.email.get_request_id') as mock_request_id:
                mock_request_id.return_value = "test_request"
                
                with patch('services.office.api.email.cache_manager.get') as mock_cache_get:
                    mock_cache_get.return_value = None
                    
                    with patch('services.office.api.email.cache_manager.set') as mock_cache_set:
                        response = await get_message_thread(
                            request=mock_request,
                            message_id="gmail_msg1",
                            service_name="test_service",
                        )
                        
                        assert response.success is True
                        assert "thread" in response.data
                        mock_cache_set.assert_called_once()


class TestThreadFetchFunctions:
    """Test thread fetching helper functions."""

    @pytest.mark.asyncio
    async def test_fetch_provider_threads_google(self):
        """Test fetching threads from Google provider."""
        with patch('services.office.api.email.get_api_client_factory') as mock_factory:
            mock_client = AsyncMock()
            mock_factory.return_value.create_client.return_value = mock_client
            
            # Mock Gmail API responses
            mock_client.get_threads.return_value = {
                "threads": [{"id": "thread1"}]
            }
            mock_client.get_thread.return_value = {
                "messages": [
                    {
                        "id": "msg1",
                        "threadId": "thread1",
                        "snippet": "Test",
                        "payload": {
                            "headers": [
                                {"name": "Subject", "value": "Test"},
                                {"name": "From", "value": "sender@example.com"},
                                {"name": "Date", "value": "Mon, 1 Jan 2024 12:00:00 +0000"},
                            ]
                        },
                        "labelIds": ["INBOX"],
                    }
                ]
            }
            
            threads, provider = await fetch_provider_threads(
                "test_request",
                "test_user",
                "google",
                10,
                False,
                None,
                None,
                None,
                None,
            )
            
            assert provider == "google"
            assert len(threads) == 1
            assert threads[0].id == "gmail_thread1"

    @pytest.mark.asyncio
    async def test_fetch_provider_threads_microsoft(self):
        """Test fetching threads from Microsoft provider."""
        with patch('services.office.api.email.get_api_client_factory') as mock_factory:
            mock_client = AsyncMock()
            mock_factory.return_value.create_client.return_value = mock_client
            
            # Mock Microsoft API responses
            mock_client.get_conversations.return_value = {
                "value": [{"id": "conv1", "topic": "Test Conversation"}]
            }
            mock_client.get_conversation_messages.return_value = {
                "value": [
                    {
                        "id": "msg1",
                        "conversationId": "conv1",
                        "subject": "Test Conversation",
                        "bodyPreview": "Test",
                        "from": {"emailAddress": {"address": "sender@example.com", "name": "Sender"}},
                        "toRecipients": [{"emailAddress": {"address": "recipient@example.com", "name": "Recipient"}}],
                        "receivedDateTime": "2024-01-01T12:00:00Z",
                        "isRead": True,
                        "hasAttachments": False,
                    }
                ]
            }
            
            threads, provider = await fetch_provider_threads(
                "test_request",
                "test_user",
                "microsoft",
                10,
                False,
                None,
                None,
                None,
                None,
            )
            
            assert provider == "microsoft"
            assert len(threads) == 1
            assert threads[0].id == "microsoft_conv1" 