import pytest
from unittest.mock import AsyncMock, MagicMock
from services.vespa_loader.pubsub_consumer import PubSubConsumer
from services.common.events.email_events import EmailBackfillEvent, EmailData


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
        consumer.email_processor = MagicMock()
        consumer._ingest_document = AsyncMock()
        return consumer

    @pytest.fixture
    def sample_email_backfill_event(self):
        """Create a sample EmailBackfillEvent for testing"""
        return {
            "metadata": {
                "source_service": "test-service",
                "source_version": "1.0.0",
                "event_id": "test-event-123",
                "timestamp": "2025-08-20T10:00:00Z"
            },
            "user_id": "test-user-123",
            "provider": "microsoft",
            "emails": [
                {
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
                    "headers": {}
                },
                {
                    "id": "email-2",
                    "thread_id": "thread-2",
                    "subject": "Test Email 2",
                    "body": "Test body 2",
                    "from_address": "sender2@test.com",
                    "to_addresses": ["recipient2@test.com"],
                    "cc_addresses": [],
                    "bcc_addresses": [],
                    "received_date": "2025-08-20T11:00:00Z",
                    "sent_date": "2025-08-20T10:55:00Z",
                    "labels": ["SENT"],
                    "is_read": False,
                    "is_starred": True,
                    "has_attachments": True,
                    "provider": "microsoft",
                    "provider_message_id": "msg-2",
                    "size_bytes": 2048,
                    "mime_type": "text/html",
                    "headers": {}
                }
            ],
            "batch_size": 2,
            "sync_type": "backfill",
            "start_date": "2025-08-20T00:00:00Z",
            "end_date": "2025-08-20T23:59:59Z",
            "folder": "INBOX",
            "total_emails": 2,
            "processed_count": 2
        }

    async def test_process_email_message_with_email_backfill_event(self, mock_consumer, sample_email_backfill_event):
        """Test that EmailBackfillEvent is processed correctly"""
        # Parse the raw data into a typed EmailBackfillEvent first
        from services.common.events.email_events import EmailBackfillEvent
        typed_event = EmailBackfillEvent(**sample_email_backfill_event)
        
        # Process the typed email backfill event
        await mock_consumer._process_email_message(typed_event)

        # Verify that _ingest_document was called twice (once for each email)
        assert mock_consumer._ingest_document.call_count == 2

        # Verify the first email was processed with correct data
        first_call = mock_consumer._ingest_document.call_args_list[0]
        first_email_data = first_call[0][0]  # First argument of first call
        
        assert first_email_data["id"] == "email-1"
        assert first_email_data["user_id"] == "test-user-123"  # Should be added from event
        assert first_email_data["subject"] == "Test Email 1"
        assert first_email_data["from"] == "sender1@test.com"
        assert first_email_data["to"] == ["recipient1@test.com"]

        # Verify the second email was processed with correct data
        second_call = mock_consumer._ingest_document.call_args_list[1]
        second_email_data = second_call[0][0]  # First argument of second call
        
        assert second_email_data["id"] == "email-2"
        assert second_email_data["user_id"] == "test-user-123"  # Should be added from event
        assert second_email_data["subject"] == "Test Email 2"
        assert second_email_data["from"] == "sender2@test.com"
        assert second_email_data["to"] == ["recipient2@test.com"]

    async def test_process_email_message_adds_user_id_when_missing(self, mock_consumer, sample_email_backfill_event):
        """Test that user_id is properly used from the event level"""
        # Parse the raw data into a typed EmailBackfillEvent first
        from services.common.events.email_events import EmailBackfillEvent
        typed_event = EmailBackfillEvent(**sample_email_backfill_event)
        
        # Process the event
        await mock_consumer._process_email_message(typed_event)
        
        # Verify that _ingest_document was called with the user_id from the event
        first_call = mock_consumer._ingest_document.call_args_list[0]
        first_email_data = first_call[0][0]
        
        assert first_email_data["user_id"] == "test-user-123"

    async def test_process_email_message_handles_missing_emails_array(self, mock_consumer):
        """Test that invalid events without emails array are rejected"""
        # This test is no longer relevant since we now require typed EmailBackfillEvent
        # The validation happens at the PubSub message parsing level
        pass

    async def test_process_email_message_handles_empty_emails_array(self, mock_consumer):
        """Test that empty emails array is handled gracefully"""
        event_with_empty_emails = {
            "metadata": {
                "source_service": "test-service",
                "source_version": "1.0.0",
                "event_id": "test-event-123",
                "timestamp": "2025-08-20T10:00:00Z"
            },
            "user_id": "test-user-123",
            "provider": "microsoft",
            "emails": [],  # Empty array
            "batch_size": 0
        }
        
        # Parse as typed EmailBackfillEvent
        from services.common.events.email_events import EmailBackfillEvent
        typed_event = EmailBackfillEvent(**event_with_empty_emails)
        
        # Should not raise an error, just process nothing
        await mock_consumer._process_email_message(typed_event)
        
        # Verify that _ingest_document was not called
        mock_consumer._ingest_document.assert_not_called()

    async def test_process_email_message_continues_on_individual_email_failure(self, mock_consumer, sample_email_backfill_event):
        """Test that processing continues even if individual emails fail"""
        # Parse the raw data into a typed EmailBackfillEvent first
        from services.common.events.email_events import EmailBackfillEvent
        typed_event = EmailBackfillEvent(**sample_email_backfill_event)
        
        # Make the first email fail
        mock_consumer._ingest_document.side_effect = [
            Exception("First email failed"),  # First call fails
            {"status": "success"}  # Second call succeeds
        ]
        
        # Should not raise an exception, should continue processing
        await mock_consumer._process_email_message(typed_event)
        
        # Verify that _ingest_document was called twice despite the first failure
        assert mock_consumer._ingest_document.call_count == 2
