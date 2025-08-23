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
from services.vespa_loader.types import VespaDocumentType


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
        assert doc.metadata["batch_id"] == self.test_batch_id

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

    def test_create_contact_document(self):
        """Test creating contact document from ContactEvent"""
        # Create test contact data
        contact_data = ContactData(
            id="contact_001",
            display_name="John Doe",
            email_addresses=["john@example.com"],
            phone_numbers=[{"type": "mobile", "number": "+1234567890"}],
            given_name="John",
            family_name="Doe",
            company="Example Corp",
            job_title="Developer",
            provider="google",
            provider_contact_id="google_contact_001",
            last_modified=datetime.now(timezone.utc),
            addresses=[],
            organizations=[],
            birthdays=[],
            photos=[],
            groups=[],
            tags=["work"],
        )

        contact_event = ContactEvent(
            user_id=self.test_user_id,
            contact=contact_data,
            operation="create",
            batch_id=self.test_batch_id,
            last_updated=self.test_timestamp,
            sync_timestamp=self.test_timestamp,
            provider="google",
            metadata=self.test_metadata,
        )

        # Create document
        doc = self.factory.create_contact_document(contact_event)

        # Verify document structure
        assert isinstance(doc, VespaDocumentType)
        assert doc.id == "contact_001"
        assert doc.user_id == self.test_user_id
        assert doc.type == "contact"
        assert doc.provider == "google"
        assert doc.subject == "John Doe"
        assert doc.body == ""
        assert doc.from_address == ""
        assert doc.to_addresses == ["john@example.com"]
        assert doc.metadata["operation"] == "create"
        assert doc.metadata["contact_type"] == "contact"

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

    def test_parse_contact_event(self):
        """Test parsing contact event from raw data"""
        raw_data = {
            "user_id": "test_user",
            "contact": {
                "id": "contact_001",
                "display_name": "John Doe",
                "email_addresses": ["john@example.com"],
                "phone_numbers": [{"type": "mobile", "number": "+1234567890"}],
                "given_name": "John",
                "family_name": "Doe",
                "company": "Example Corp",
                "job_title": "Developer",
                "provider": "google",
                "provider_contact_id": "google_contact_001",
                "last_modified": "2023-01-01T00:00:00Z",
                "addresses": [],
                "organizations": [],
                "birthdays": [],
                "photos": [],
                "groups": [],
                "tags": ["work"],
            },
            "operation": "create",
            "batch_id": "batch_001",
            "last_updated": "2023-01-01T00:00:00Z",
            "sync_timestamp": "2023-01-01T00:00:00Z",
            "provider": "google",
            "metadata": self.test_metadata.model_dump(),
        }

        event = parse_event_by_topic("contacts", raw_data, self.test_message_id)
        assert isinstance(event, ContactEvent)
        assert event.user_id == "test_user"
        assert event.contact.id == "contact_001"

    def test_parse_document_event(self):
        """Test parsing document event from raw data"""
        raw_data = {
            "user_id": "test_user",
            "document": {
                "id": "doc_001",
                "title": "Test Doc",
                "content": "Test content",
                "content_type": "word",
                "provider": "microsoft",
                "provider_document_id": "ms_doc_001",
                "owner_email": "owner@example.com",
                "permissions": ["read"],
                "tags": ["work"],
                "metadata": {},
            },
            "operation": "create",
            "batch_id": "batch_001",
            "last_updated": "2023-01-01T00:00:00Z",
            "sync_timestamp": "2023-01-01T00:00:00Z",
            "provider": "microsoft",
            "content_type": "word",
            "metadata": self.test_metadata.model_dump(),
        }

        event = parse_event_by_topic("word_documents", raw_data, self.test_message_id)
        assert isinstance(event, DocumentEvent)
        assert event.user_id == "test_user"
        assert event.document.id == "doc_001"

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
