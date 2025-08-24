"""
Tests for the Vespa Document Factory

This module tests the VespaDocumentFactory class and parse_event_by_topic function
that were moved from pubsub_consumer.py to improve modularity.
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from services.common.events.base_events import EventMetadata
from services.common.events.calendar_events import CalendarEvent, CalendarEventData
from services.common.events.contact_events import ContactData, ContactEvent
from services.common.events.document_events import DocumentData, DocumentEvent
from services.common.events.email_events import EmailData, EmailEvent
from services.common.events.todo_events import TodoData, TodoEvent
from services.vespa_loader.document_factory import (
    VespaDocumentFactory,
    parse_event_by_topic,
)
from services.vespa_loader.vespa_types import VespaDocumentType


class TestVespaDocumentFactory:
    """Test the VespaDocumentFactory class functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.factory = VespaDocumentFactory()
        self.test_user_id = "test_user_123"
        self.test_batch_id = "test_batch_789"
        self.test_timestamp = datetime.now(timezone.utc)
        self.test_metadata = EventMetadata(
            event_id="test_event_001",
            timestamp=self.test_timestamp,
            source_service="test-service",
            source_version="1.0.0",
        )

    def test_create_email_document(self):
        """Test creating email document from EmailEvent"""
        # Create test email data
        email_data = EmailData(
            id="email_001",
            thread_id="thread_001",
            subject="Test Email",
            body="This is a test email body",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            received_date=datetime.now(timezone.utc),
            sent_date=datetime.now(timezone.utc),
            provider="gmail",
            provider_message_id="gmail_msg_001",
            is_read=False,
            is_starred=False,
            has_attachments=False,
            labels=["inbox"],
            size_bytes=1024,
            mime_type="text/plain",
            headers={},
        )

        email_event = EmailEvent(
            user_id=self.test_user_id,
            email=email_data,
            operation="create",
            batch_id=self.test_batch_id,
            last_updated=self.test_timestamp,
            sync_timestamp=self.test_timestamp,
            sync_type="backfill",
            provider="gmail",
            metadata=self.test_metadata,
        )

        # Create document
        doc = self.factory.create_email_document(email_event)

        # Verify document structure
        assert isinstance(doc, VespaDocumentType)
        assert doc.id == "email_001"
        assert doc.user_id == self.test_user_id
        assert doc.type == "email"
        assert doc.provider == "gmail"
        assert doc.subject == "Test Email"
        assert doc.body == "This is a test email body"
        assert doc.from_address == "sender@example.com"
        assert doc.to_addresses == ["recipient@example.com"]
        assert doc.thread_id == "thread_001"
        assert doc.metadata["operation"] == "create"
        # Note: batch_id is no longer tracked in metadata as it's not needed for search/retrieval

    def test_create_calendar_document(self):
        """Test creating calendar document from CalendarEvent"""
        # Create test calendar data
        calendar_data = CalendarEventData(
            id="calendar_001",
            title="Test Meeting",
            description="This is a test meeting",
            organizer="organizer@example.com",
            attendees=["attendee1@example.com", "attendee2@example.com"],
            calendar_id="cal_001",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            all_day=False,
            location="Conference Room A",
            status="confirmed",
            visibility="public",
            provider="google",
            provider_event_id="google_event_001",
            recurrence=None,
            reminders=[],
            attachments=[],
            color_id="1",
            html_link="https://calendar.google.com/event/001",
        )

        calendar_event = CalendarEvent(
            user_id=self.test_user_id,
            event=calendar_data,
            operation="create",
            batch_id=self.test_batch_id,
            last_updated=self.test_timestamp,
            sync_timestamp=self.test_timestamp,
            provider="google",
            calendar_id="cal_001",
            metadata=self.test_metadata,
        )

        # Create document
        doc = self.factory.create_calendar_document(calendar_event)

        # Verify document structure
        assert isinstance(doc, VespaDocumentType)
        assert doc.id == "calendar_001"
        assert doc.user_id == self.test_user_id
        assert doc.type == "calendar"
        assert doc.provider == "google"
        assert doc.subject == "Test Meeting"
        assert doc.body == "This is a test meeting"
        assert doc.from_address == "organizer@example.com"
        assert doc.to_addresses == ["attendee1@example.com", "attendee2@example.com"]
        assert doc.folder == "cal_001"
        assert doc.metadata["operation"] == "create"
        assert doc.metadata["event_type"] == "calendar"

    def test_create_document_document(self):
        """Test creating document from DocumentEvent"""
        # Create test document data
        document_data = DocumentData(
            id="doc_001",
            title="Test Document",
            content="This is test document content",
            content_type="word",
            provider="microsoft",
            provider_document_id="ms_doc_001",
            owner_email="owner@example.com",
            permissions=["read", "write"],
            tags=["work", "important"],
            metadata={"version": "1.0"},
        )

        document_event = DocumentEvent(
            user_id=self.test_user_id,
            document=document_data,
            operation="create",
            batch_id=self.test_batch_id,
            last_updated=self.test_timestamp,
            sync_timestamp=self.test_timestamp,
            provider="microsoft",
            content_type="word",
            metadata=self.test_metadata,
        )

        # Create document
        doc = self.factory.create_document_document(document_event)

        # Verify document structure
        assert isinstance(doc, VespaDocumentType)
        assert doc.id == "doc_001"
        assert doc.user_id == self.test_user_id
        assert doc.type == "word"
        assert doc.provider == "microsoft"
        assert doc.subject == "Test Document"
        assert doc.body == "This is test document content"
        assert doc.from_address == "owner@example.com"
        assert doc.to_addresses == []
        assert doc.metadata["operation"] == "create"
        assert doc.metadata["content_type"] == "word"

    def test_create_todo_document(self):
        """Test creating todo document from TodoEvent"""
        # Create test todo data
        todo_data = TodoData(
            id="todo_001",
            title="Test Todo",
            description="This is a test todo item",
            status="pending",
            priority="high",
            due_date=datetime.now(timezone.utc),
            completed_date=None,
            assignee_email="assignee@example.com",
            creator_email="creator@example.com",
            parent_todo_id=None,
            subtask_ids=[],
            list_id="list_001",
            provider="microsoft",
            provider_todo_id="ms_todo_001",
            tags=["work", "urgent"],
        )

        todo_event = TodoEvent(
            user_id=self.test_user_id,
            todo=todo_data,
            operation="create",
            batch_id=self.test_batch_id,
            last_updated=self.test_timestamp,
            sync_timestamp=self.test_timestamp,
            provider="microsoft",
            list_id="list_001",
            metadata=self.test_metadata,
        )

        # Create document
        doc = self.factory.create_todo_document(todo_event)

        # Verify document structure
        assert isinstance(doc, VespaDocumentType)
        assert doc.id == "todo_001"
        assert doc.user_id == self.test_user_id
        assert doc.type == "todo"
        assert doc.provider == "microsoft"
        assert doc.subject == "Test Todo"
        assert doc.body == "This is a test todo item"
        assert doc.from_address == "creator@example.com"
        assert doc.to_addresses == ["assignee@example.com"]
        assert doc.folder == "list_001"
        assert doc.metadata["operation"] == "create"
        assert doc.metadata["todo_type"] == "todo"

    def test_create_document_from_event_generic(self):
        """Test the generic create_document_from_event method"""
        # Test with email event
        email_data = EmailData(
            id="email_002",
            thread_id="thread_002",
            subject="Generic Test",
            body="Generic test body",
            from_address="test@example.com",
            to_addresses=["user@example.com"],
            received_date=datetime.now(timezone.utc),
            sent_date=datetime.now(timezone.utc),
            provider="gmail",
            provider_message_id="gmail_msg_002",
            is_read=False,
            is_starred=False,
            has_attachments=False,
            labels=[],
            size_bytes=512,
            mime_type="text/plain",
            headers={},
        )

        email_event = EmailEvent(
            user_id=self.test_user_id,
            email=email_data,
            operation="create",
            batch_id=self.test_batch_id,
            last_updated=self.test_timestamp,
            sync_timestamp=self.test_timestamp,
            sync_type="backfill",
            provider="gmail",
            metadata=self.test_metadata,
        )

        # Use generic method
        doc = self.factory.create_document_from_event(email_event)
        assert isinstance(doc, VespaDocumentType)
        assert doc.type == "email"

    def test_get_supported_event_types(self):
        """Test getting list of supported event types"""
        supported_types = self.factory.get_supported_event_types()
        expected_types = [
            "EmailEvent",
            "CalendarEvent",
            "ContactEvent",
            "DocumentEvent",
            "TodoEvent",
        ]
        assert supported_types == expected_types

    def test_email_document_field_mappings(self):
        """Test that email documents are created with correct field mappings for Vespa."""
        from datetime import datetime, timezone

        from services.common.events import EmailData, EmailEvent, EventMetadata

        # Create a sample email event
        email_data = EmailData(
            id="email_test_123",
            thread_id="thread_456",
            subject="Test Email Subject",
            body="This is a test email body with some content that should be chunked properly.",
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            cc_addresses=[],
            bcc_addresses=[],
            received_date=datetime.now(timezone.utc),
            sent_date=None,
            labels=["INBOX"],
            is_read=False,
            is_starred=False,
            has_attachments=False,
            provider="gmail",
            provider_message_id="gmail_123",
            size_bytes=1024,
            mime_type="text/plain",
            headers={},
        )

        email_event = EmailEvent(
            user_id="user_789",
            email=email_data,
            operation="create",
            batch_id="batch_123",
            last_updated=datetime.now(timezone.utc),
            sync_timestamp=datetime.now(timezone.utc),
            provider="gmail",
            sync_type="sync",
            metadata=EventMetadata(
                source_service="office-service",
                source_version="1.0.0",
                correlation_id="test_123",
            ),
        )

        # Create Vespa document
        vespa_doc = VespaDocumentFactory.create_email_document(email_event)

        # Convert to dict for Vespa indexing
        doc_dict = vespa_doc.to_dict()

        # Verify that the correct field mappings are used
        assert "doc_id" in doc_dict, "Should have doc_id field for Vespa schema"
        assert doc_dict["doc_id"] == "email_test_123", "doc_id should map from email.id"

        assert (
            "source_type" in doc_dict
        ), "Should have source_type field for Vespa schema"
        assert (
            doc_dict["source_type"] == "email"
        ), "source_type should map from email type"

        assert "title" in doc_dict, "Should have title field for Vespa schema"
        assert (
            doc_dict["title"] == "Test Email Subject"
        ), "title should map from email.subject"

        assert "content" in doc_dict, "Should have content field for Vespa schema"
        assert (
            doc_dict["content"]
            == "This is a test email body with some content that should be chunked properly."
        ), "content should map from email.body"

        assert "sender" in doc_dict, "Should have sender field for Vespa schema"
        assert (
            doc_dict["sender"] == "sender@example.com"
        ), "sender should map from email.from_address"

        assert "recipients" in doc_dict, "Should have recipients field for Vespa schema"
        assert doc_dict["recipients"] == [
            "recipient@example.com"
        ], "recipients should map from email.to_addresses"

        # Verify that the id field is NOT present (should be excluded)
        assert "id" not in doc_dict, "id field should not be present in Vespa document"

        # Verify other required fields
        assert "user_id" in doc_dict, "Should have user_id field"
        assert "provider" in doc_dict, "Should have provider field"
        assert "thread_id" in doc_dict, "Should have thread_id field"
        assert "folder" in doc_dict, "Should have folder field"
        assert "created_at" in doc_dict, "Should have created_at field"
        assert "updated_at" in doc_dict, "Should have updated_at field"
        assert "metadata" in doc_dict, "Should have metadata field"
        # Note: content_chunks is not included in Vespa schema, so it's not in to_dict()
        assert "quoted_content" in doc_dict, "Should have quoted_content field"
        assert "thread_summary" in doc_dict, "Should have thread_summary field"
        assert "search_text" in doc_dict, "Should have search_text field"


class TestParseEventByTopic:
    """Test the parse_event_by_topic function"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_message_id = "msg_001"
        self.test_metadata = EventMetadata(
            event_id="test_event_002",
            timestamp=datetime.now(timezone.utc),
            source_service="test-service",
            source_version="1.0.0",
        )

    def test_parse_email_event(self):
        """Test parsing email event from raw data"""
        raw_data = {
            "user_id": "test_user",
            "email": {
                "id": "email_001",
                "thread_id": "thread_001",
                "subject": "Test",
                "body": "Test body",
                "from_address": "test@example.com",
                "to_addresses": ["user@example.com"],
                "received_date": "2023-01-01T00:00:00Z",
                "sent_date": "2023-01-01T00:00:00Z",
                "is_read": False,
                "is_starred": False,
                "has_attachments": False,
                "labels": [],
                "size_bytes": 512,
                "mime_type": "text/plain",
                "headers": {},
                "provider": "gmail",
                "provider_message_id": "gmail_msg_001",
            },
            "operation": "create",
            "batch_id": "batch_001",
            "last_updated": "2023-01-01T00:00:00Z",
            "sync_timestamp": "2023-01-01T00:00:00Z",
            "sync_type": "backfill",
            "provider": "gmail",
            "metadata": self.test_metadata.model_dump(),
        }

        event = parse_event_by_topic("emails", raw_data, self.test_message_id)
        assert isinstance(event, EmailEvent)
        assert event.user_id == "test_user"
        assert event.email.id == "email_001"

    def test_parse_calendar_event(self):
        """Test parsing calendar event from raw data"""
        raw_data = {
            "user_id": "test_user",
            "event": {
                "id": "calendar_001",
                "title": "Meeting",
                "description": "Test meeting",
                "organizer": "organizer@example.com",
                "attendees": ["attendee@example.com"],
                "calendar_id": "cal_001",
                "start_time": "2023-01-01T10:00:00Z",
                "end_time": "2023-01-01T11:00:00Z",
                "all_day": False,
                "location": "Room A",
                "status": "confirmed",
                "visibility": "public",
                "provider": "google",
                "provider_event_id": "google_event_001",
                "recurrence": None,
                "reminders": [],
                "attachments": [],
                "color_id": "1",
                "html_link": "https://calendar.google.com/event/001",
            },
            "operation": "create",
            "batch_id": "batch_001",
            "last_updated": "2023-01-01T00:00:00Z",
            "sync_timestamp": "2023-01-01T00:00:00Z",
            "provider": "google",
            "calendar_id": "cal_001",
            "metadata": self.test_metadata.model_dump(),
        }

        event = parse_event_by_topic("calendars", raw_data, self.test_message_id)
        assert isinstance(event, CalendarEvent)
        assert event.user_id == "test_user"
        assert event.event.id == "calendar_001"

    def test_parse_document_event(self):
        """Test parsing document event from raw data"""
        raw_data = {
            "user_id": "test_user_123",
            "document": {
                "id": "doc_123",
                "title": "Test Document",
                "content": "Test content",
                "content_type": "text/plain",
                "provider": "google",
                "provider_document_id": "google_doc_123",
                "owner_email": "owner@example.com",
                "file_id": "file_123",
                "mime_type": "text/plain",
                "size_bytes": 1000,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "permissions": [],
                "owners": [],
                "web_view_link": "https://example.com",
                "web_content_link": "https://example.com/download",
                "tags": [],
                "metadata": {},
            },
            "operation": "create",
            "batch_id": "batch_123",
            "last_updated": "2023-01-01T00:00:00Z",
            "sync_timestamp": "2023-01-01T00:00:00Z",
            "provider": "google",
            "content_type": "word_documents",
            "metadata": self.test_metadata.model_dump(),
        }

        event = parse_event_by_topic("word_documents", raw_data, self.test_message_id)
        assert isinstance(event, DocumentEvent)
        assert event.user_id == "test_user_123"
        assert event.document.id == "doc_123"

    def test_parse_todo_event(self):
        """Test parsing todo event from raw data"""
        raw_data = {
            "user_id": "test_user",
            "todo": {
                "id": "todo_001",
                "title": "Test Todo",
                "description": "Test description",
                "status": "pending",
                "priority": "high",
                "due_date": "2023-01-01T00:00:00Z",
                "completed_date": None,
                "assignee_email": "assignee@example.com",
                "creator_email": "creator@example.com",
                "parent_todo_id": None,
                "subtask_ids": [],
                "list_id": "list_001",
                "provider": "microsoft",
                "provider_todo_id": "ms_todo_001",
                "tags": ["work"],
            },
            "operation": "create",
            "batch_id": "batch_001",
            "last_updated": "2023-01-01T00:00:00Z",
            "sync_timestamp": "2023-01-01T00:00:00Z",
            "provider": "microsoft",
            "list_id": "list_001",
            "metadata": self.test_metadata.model_dump(),
        }

        event = parse_event_by_topic("todos", raw_data, self.test_message_id)
        assert isinstance(event, TodoEvent)
        assert event.user_id == "test_user"
        assert event.todo.id == "todo_001"

    def test_parse_unknown_topic(self):
        """Test parsing with unknown topic raises error"""
        raw_data = {"user_id": "test_user", "data": "test"}

        with pytest.raises(ValueError, match="Unsupported topic: unknown_topic"):
            parse_event_by_topic("unknown_topic", raw_data, self.test_message_id)

    def test_parse_invalid_data(self):
        """Test parsing with invalid data raises error"""
        raw_data = {"invalid": "data"}

        with pytest.raises(Exception):
            parse_event_by_topic("emails", raw_data, self.test_message_id)
