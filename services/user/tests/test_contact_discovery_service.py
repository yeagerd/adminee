"""
Tests for the contact discovery service.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from services.common.events import CalendarEvent, DocumentEvent, EmailEvent, TodoEvent
from services.common.events.base_events import EventMetadata
from services.common.models.email_contact import EmailContact, EmailContactUpdate
from services.user.services.contact_discovery_service import ContactDiscoveryService


class TestContactDiscoveryService:
    """Test cases for ContactDiscoveryService."""

    @pytest.fixture
    def mock_pubsub_client(self):
        """Create a mock Pub/Sub client."""
        return Mock()

    @pytest.fixture
    def service(self, mock_pubsub_client):
        """Create a ContactDiscoveryService instance."""
        return ContactDiscoveryService(mock_pubsub_client)

    @pytest.fixture
    def sample_email_event(self):
        """Create a sample email event."""
        return EmailEvent(
            user_id="user123",
            email={
                "id": "email123",
                "thread_id": "thread123",
                "subject": "Test Email",
                "body": "Test body",
                "from_address": "sender@example.com",
                "to_addresses": [
                    "recipient1@example.com",
                    "recipient2@example.com",
                ],
                "cc_addresses": ["cc@example.com"],
                "received_date": datetime(2024, 1, 1, 10, 0, 0),
                "provider": "gmail",
                "provider_message_id": "msg123",
            },
            operation="create",
            batch_id="batch123",
            last_updated=datetime(2024, 1, 1, 10, 0, 0),
            sync_timestamp=datetime(2024, 1, 1, 10, 0, 0),
            provider="gmail",
            sync_type="backfill",
            metadata=EventMetadata(
                source_service="test-service",
                source_version="1.0.0",
            ),
        )

    @pytest.fixture
    def sample_calendar_event(self):
        """Create a sample calendar event."""
        return CalendarEvent(
            user_id="user123",
            event={
                "id": "cal123",
                "title": "Test Meeting",
                "organizer": "organizer@example.com",
                "attendees": [
                    "attendee1@example.com",
                    "attendee2@example.com",
                ],
                "start_time": datetime(2024, 1, 1, 14, 0, 0),
                "end_time": datetime(2024, 1, 1, 15, 0, 0),
                "calendar_id": "cal1",
                "provider": "google",
                "provider_event_id": "cal123",
            },
            operation="create",
            batch_id="batch123",
            last_updated=datetime(2024, 1, 1, 14, 0, 0),
            sync_timestamp=datetime(2024, 1, 1, 14, 0, 0),
            provider="google",
            calendar_id="cal1",
            metadata=EventMetadata(
                source_service="test-service",
                source_version="1.0.0",
            ),
        )

    def test_process_email_event_creates_contacts(self, service, sample_email_event):
        """Test that processing an email event creates contacts."""
        service.process_email_event(sample_email_event)

        # Check that contacts were created
        from_contact = service.get_contact("user123", "sender@example.com")
        to_contact1 = service.get_contact("user123", "recipient1@example.com")
        to_contact2 = service.get_contact("user123", "recipient2@example.com")
        cc_contact = service.get_contact("user123", "cc@example.com")

        assert from_contact is not None
        assert from_contact.email_address == "sender@example.com"
        assert "email_sync" in from_contact.source_services

        assert to_contact1 is not None
        assert to_contact1.email_address == "recipient1@example.com"

        assert to_contact2 is not None
        assert to_contact2.email_address == "recipient2@example.com"

        assert cc_contact is not None
        assert cc_contact.email_address == "cc@example.com"

    def test_process_calendar_event_creates_contacts(
        self, service, sample_calendar_event
    ):
        """Test that processing a calendar event creates contacts."""
        service.process_calendar_event(sample_calendar_event)

        # Check that contacts were created
        organizer_contact = service.get_contact("user123", "organizer@example.com")
        attendee1_contact = service.get_contact("user123", "attendee1@example.com")
        attendee2_contact = service.get_contact("user123", "attendee2@example.com")

        assert organizer_contact is not None
        assert organizer_contact.email_address == "organizer@example.com"
        assert "calendar_sync" in organizer_contact.source_services

        assert attendee1_contact is not None
        assert attendee1_contact.email_address == "attendee1@example.com"

        assert attendee2_contact is not None
        assert attendee2_contact.email_address == "attendee2@example.com"

    def test_contact_event_counting(self, service, sample_email_event):
        """Test that contact event counting works correctly."""
        # Process email event
        service.process_email_event(sample_email_event)

        # Process another email event with the same sender
        sample_email_event2 = EmailEvent(
            user_id="user123",
            email={
                "id": "email124",
                "thread_id": "thread124",
                "subject": "Test Email 2",
                "body": "Test body 2",
                "from_address": "sender@example.com",
                "to_addresses": [
                    "recipient1@example.com",
                    "recipient2@example.com",
                ],
                "cc_addresses": ["cc@example.com"],
                "received_date": datetime(2024, 1, 2, 10, 0, 0),
                "provider": "gmail",
                "provider_message_id": "msg124",
            },
            operation="create",
            batch_id="batch124",
            last_updated=datetime(2024, 1, 2, 10, 0, 0),
            sync_timestamp=datetime(2024, 1, 2, 10, 0, 0),
            provider="gmail",
            sync_type="backfill",
            metadata=EventMetadata(
                source_service="test-service",
                source_version="1.0.0",
            ),
        )
        service.process_email_event(sample_email_event2)

        # Check contact
        contact = service.get_contact("user123", "sender@example.com")
        assert contact.total_event_count == 2
        assert contact.event_counts["email"].count == 2
        assert contact.event_counts["email"].last_seen == datetime(2024, 1, 2, 10, 0, 0)

    def test_contact_relevance_scoring(self, service, sample_email_event):
        """Test that contact relevance scoring works."""
        service.process_email_event(sample_email_event)

        contact = service.get_contact("user123", "sender@example.com")
        relevance_score = contact.calculate_relevance_score()

        assert 0.0 <= relevance_score <= 1.0
        assert "recency" in contact.relevance_factors
        assert "frequency" in contact.relevance_factors
        assert "diversity" in contact.relevance_factors
        assert "name_completeness" in contact.relevance_factors

    def test_contact_name_extraction(self, service):
        """Test that contact names are extracted correctly."""
        # Test full name
        given_name = service._extract_given_name("John Doe")
        family_name = service._extract_family_name("John Doe")

        assert given_name == "John"
        assert family_name == "Doe"

        # Test single name
        given_name = service._extract_given_name("John")
        family_name = service._extract_family_name("John")

        assert given_name == "John"
        assert family_name is None

        # Test empty name
        given_name = service._extract_given_name("")
        family_name = service._extract_family_name("")

        assert given_name is None
        assert family_name is None

    def test_contact_update(self, service, sample_email_event):
        """Test that contact updates work correctly."""
        service.process_email_event(sample_email_event)

        # Update contact
        update_data = EmailContactUpdate(
            display_name="John Smith",
            tags=["important", "work"],
            notes="Key contact for project",
        )

        updated_contact = service.update_contact(
            "user123", "sender@example.com", update_data
        )

        assert updated_contact is not None
        assert updated_contact.display_name == "John Smith"
        assert updated_contact.given_name == "John"
        assert updated_contact.family_name == "Smith"
        assert "important" in updated_contact.tags
        assert "work" in updated_contact.tags
        assert updated_contact.notes == "Key contact for project"

    def test_contact_search(self, service, sample_email_event, sample_calendar_event):
        """Test that contact search works correctly."""
        service.process_email_event(sample_email_event)
        service.process_calendar_event(sample_calendar_event)

        # Search by email (since names are not available in current model)
        results = service.search_contacts("user123", "sender@example.com")
        assert len(results) >= 1
        assert any("sender@example.com" in contact.email_address for contact in results)

        # Search by another email
        results = service.search_contacts("user123", "organizer@example.com")
        assert len(results) >= 1
        assert any(
            "organizer@example.com" in contact.email_address for contact in results
        )

        # Search with no query
        results = service.search_contacts("user123", "")
        assert len(results) > 0

    def test_contact_stats(self, service, sample_email_event, sample_calendar_event):
        """Test that contact statistics are calculated correctly."""
        service.process_email_event(sample_email_event)
        service.process_calendar_event(sample_calendar_event)

        stats = service.get_contact_stats("user123")

        assert stats["total_contacts"] > 0
        assert stats["total_events"] > 0
        assert "email_sync" in stats["by_service"]
        assert "calendar_sync" in stats["by_service"]

    def test_contact_removal(self, service, sample_email_event):
        """Test that contact removal works correctly."""
        service.process_email_event(sample_email_event)

        # Verify contact exists
        contact = service.get_contact("user123", "sender@example.com")
        assert contact is not None

        # Remove contact
        removed = service.remove_contact("user123", "sender@example.com")
        assert removed is True

        # Verify contact is gone
        contact = service.get_contact("user123", "sender@example.com")
        assert contact is None

    def test_invalid_email_handling(self, service):
        """Test that invalid emails are handled gracefully."""
        # Create event with invalid email
        invalid_email_event = EmailEvent(
            user_id="user123",
            email={
                "id": "email123",
                "thread_id": "thread123",
                "subject": "Test",
                "body": "Test",
                "from_address": "invalid-email",
                "to_addresses": [],
                "cc_addresses": [],
                "received_date": datetime(2024, 1, 1, 10, 0, 0),
                "provider": "gmail",
                "provider_message_id": "msg123",
            },
            operation="create",
            batch_id="batch123",
            last_updated=datetime(2024, 1, 1, 10, 0, 0),
            sync_timestamp=datetime(2024, 1, 1, 10, 0, 0),
            provider="gmail",
            sync_type="backfill",
            metadata=EventMetadata(
                source_service="test-service",
                source_version="1.0.0",
            ),
        )

        service.process_email_event(invalid_email_event)

        # Contact should not be created
        contact = service.get_contact("user123", "invalid-email")
        assert contact is None

    def test_vespa_document_conversion(self, service, sample_email_event):
        """Test that contacts can be converted to Vespa documents."""
        service.process_email_event(sample_email_event)

        contact = service.get_contact("user123", "sender@example.com")
        vespa_doc = contact.to_vespa_document()

        assert vespa_doc["doc_id"] == f"contact_user123_sender@example.com"
        assert vespa_doc["user_id"] == "user123"
        assert vespa_doc["content_type"] == "contact"
        assert vespa_doc["operation"] == "create"
        assert "email_address" in vespa_doc["metadata"]
        assert "relevance_score" in vespa_doc["metadata"]
