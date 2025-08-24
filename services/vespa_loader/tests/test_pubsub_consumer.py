from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.common.events.base_events import EventMetadata
from services.common.events.email_events import EmailData, EmailEvent
from services.vespa_loader.document_factory import process_message
from services.vespa_loader.pubsub_consumer import PubSubConsumer


class TestPubSubConsumer:
    """Test the PubSubConsumer class"""

    @pytest.fixture
    def mock_consumer(self):
        """Create a mock PubSubConsumer instance"""
        from services.vespa_loader.settings import Settings

        # Create mock settings
        mock_settings = MagicMock(spec=Settings)
        mock_settings.pubsub_project_id = "test-project"
        mock_settings.pubsub_emulator_host = "localhost:8085"

        consumer = PubSubConsumer(mock_settings)
        return consumer

    @pytest.fixture
    def sample_email_event(self):
        """Create a sample EmailEvent for testing"""
        return {
            "metadata": {
                "source_service": "test-service",
                "source_version": "1.0.0",
                "event_id": "test-event-123",
                "timestamp": "2025-08-20T10:00:00Z",
            },
            "user_id": "test-user-123",
            "email": {
                "id": "email-1",
                "thread_id": "thread-1",
                "subject": "Test Email 1",
                "body": "Test body 1",
                "from_address": "sender1@test.com",
                "to_addresses": ["recipient1@test.com"],
                "cc_addresses": [],
                "bcc_addresses": [],
                "received_date": "2025-08-20T10:00:00Z",
                "sent_date": "2025-08-20T09:55:00Z",
                "labels": ["INBOX"],
                "is_read": True,
                "is_starred": False,
                "has_attachments": False,
                "provider": "microsoft",
                "provider_message_id": "msg-1",
                "size_bytes": 1024,
                "mime_type": "text/plain",
                "headers": {},
            },
            "operation": "create",
            "batch_id": "batch-123",
            "last_updated": "2025-08-20T10:00:00Z",
            "sync_timestamp": "2025-08-20T10:00:00Z",
            "sync_type": "backfill",
            "provider": "microsoft",
        }

    async def test_process_message_creates_email_document(self, sample_email_event):
        """Test that process_message creates email document correctly"""
        # Test the process_message function directly
        vespa_document = process_message(
            "emails", sample_email_event, "test-message-123"
        )

        # Verify document structure
        assert vespa_document.id == "email-1"
        assert vespa_document.user_id == "test-user-123"
        assert vespa_document.type == "email"
        assert vespa_document.provider == "microsoft"
        assert vespa_document.subject == "Test Email 1"
        assert vespa_document.body == "Test body 1"
        assert vespa_document.from_address == "sender1@test.com"
        assert vespa_document.to_addresses == ["recipient1@test.com"]
        assert vespa_document.thread_id == "thread-1"
        assert vespa_document.metadata["operation"] == "create"
        # Note: batch_id is no longer tracked in metadata as it's not needed for search/retrieval

    async def test_process_message_handles_invalid_topic(self):
        """Test that process_message rejects invalid topics"""
        raw_data = {"user_id": "test-user", "data": "test"}

        with pytest.raises(ValueError, match="Unsupported topic: invalid_topic"):
            process_message("invalid_topic", raw_data, "test-message-123")

    async def test_process_message_handles_invalid_data(self):
        """Test that process_message handles invalid data gracefully"""
        invalid_data = {"invalid": "data"}

        with pytest.raises(Exception):
            process_message("emails", invalid_data, "test-message-123")

    async def test_consumer_initialization(self, mock_consumer):
        """Test that PubSubConsumer initializes correctly"""
        assert mock_consumer.settings is not None
        assert mock_consumer.topics is not None
        assert mock_consumer.running is False
        assert mock_consumer.processed_count == 0
        assert mock_consumer.error_count == 0

    async def test_consumer_stats(self, mock_consumer):
        """Test that consumer statistics are tracked correctly"""
        stats = mock_consumer.get_stats()

        assert "running" in stats
        assert "processed_count" in stats
        assert "error_count" in stats
        assert "subscriptions" in stats
        assert "subscription_details" in stats

        assert stats["running"] is False
        assert stats["processed_count"] == 0
        assert stats["error_count"] == 0

    async def test_consumer_topics_configuration(self, mock_consumer):
        """Test that consumer configures topics correctly"""
        # The consumer should have topics configured from SubscriptionConfig
        assert isinstance(mock_consumer.topics, dict)

        # Check that topics have the expected structure
        for topic_name, config in mock_consumer.topics.items():
            assert "subscription_name" in config
            assert isinstance(config["subscription_name"], str)

    @patch("services.vespa_loader.pubsub_consumer.ingest_document_service")
    async def test_process_message_immediate_handles_success(
        self, mock_ingest_service, mock_consumer
    ):
        """Test that _process_message_immediate handles successful processing"""
        from services.vespa_loader.vespa_types import VespaDocumentType

        # Create a mock Vespa document
        mock_document = MagicMock(spec=VespaDocumentType)
        mock_document.id = "test-doc-123"
        mock_document.type = "email"
        mock_document.user_id = "test-user-123"

        # Create a mock message
        mock_message = MagicMock()
        mock_message.message_id = "test-message-123"

        # Mock the ingest_document_service to succeed
        mock_ingest_service.return_value = {"status": "success"}

        # Process the message
        await mock_consumer._process_message_immediate(mock_document, mock_message)

        # Verify that the message was acknowledged
        mock_message.ack.assert_called_once()
        assert mock_consumer.processed_count == 1
        assert mock_consumer.error_count == 0

    @patch("services.vespa_loader.pubsub_consumer.ingest_document_service")
    async def test_process_message_immediate_handles_failure(
        self, mock_ingest_service, mock_consumer
    ):
        """Test that _process_message_immediate handles processing failures"""
        from services.vespa_loader.vespa_types import VespaDocumentType

        # Create a mock Vespa document
        mock_document = MagicMock(spec=VespaDocumentType)
        mock_document.id = "test-doc-123"
        mock_document.type = "email"
        mock_document.user_id = "test-user-123"

        # Create a mock message
        mock_message = MagicMock()
        mock_message.message_id = "test-message-123"

        # Mock the ingest_document_service to fail
        mock_ingest_service.side_effect = Exception("Processing failed")

        # Process the message
        await mock_consumer._process_message_immediate(mock_document, mock_message)

        # Verify that the message was not acknowledged
        mock_message.ack.assert_not_called()
        mock_message.nack.assert_called_once()
        assert mock_consumer.processed_count == 0
        assert mock_consumer.error_count == 1
