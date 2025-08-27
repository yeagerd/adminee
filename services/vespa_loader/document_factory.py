"""
Vespa Document Factory for creating Vespa documents from different event types.

This module provides a factory pattern for converting various event types
into Vespa-ready document structures for indexing.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from services.api.v1.vespa.vespa_types import VespaDocumentType
from services.common.events.calendar_events import CalendarEvent, CalendarEventData
from services.common.events.contact_events import ContactData, ContactEvent
from services.common.events.document_events import DocumentData, DocumentEvent
from services.common.events.email_events import EmailData, EmailEvent
from services.common.events.todo_events import TodoData, TodoEvent
from services.common.logging_config import get_logger

logger = get_logger(__name__)

# Define union type for all supported event types
SupportedEventType = Union[
    EmailEvent,
    CalendarEvent,
    ContactEvent,
    DocumentEvent,
    TodoEvent,
]


class VespaDocumentFactory:
    """Factory for creating Vespa documents from different event types"""

    @staticmethod
    def create_email_document(event: EmailEvent) -> VespaDocumentType:
        """Create a Vespa document from an EmailEvent"""
        from services.vespa_loader.services.document_chunking_service import (
            DocumentChunkingService,
        )

        email = event.email

        # Create chunks using the chunking service
        chunking_service = DocumentChunkingService()
        chunking_result = chunking_service.chunk_document(
            document_id=email.id,
            content=email.body or "",
            document_type="email",
            metadata={
                "document_type": "email",  # Add document_type for chunking service
                "provider": email.provider,
                "subject": email.subject,
                "thread_id": email.thread_id,
            },
        )

        # Extract chunk content for Vespa indexing
        content_chunks = [chunk.content for chunk in chunking_result.chunks]

        return VespaDocumentType(
            id=email.id,
            user_id=event.user_id,
            type="email",
            provider=email.provider,
            subject=email.subject or "",
            body=email.body or "",
            from_address=email.from_address or "",
            to_addresses=email.to_addresses or [],
            thread_id=email.thread_id,
            folder="",  # Not available in current model
            created_at=email.received_date,
            updated_at=email.sent_date,
            metadata={
                "operation": event.operation,
                "last_updated": (
                    event.last_updated.isoformat() if event.last_updated else None
                ),
                "sync_timestamp": (
                    event.sync_timestamp.isoformat() if event.sync_timestamp else None
                ),
                "sync_type": event.sync_type,
                "is_read": email.is_read,
                "is_starred": email.is_starred,
                "has_attachments": email.has_attachments,
                "labels": email.labels,
                "size_bytes": email.size_bytes,
                "mime_type": email.mime_type,
                "headers": email.headers or {},
                "chunking_info": {
                    "total_chunks": chunking_result.total_chunks,
                    "chunking_strategy": chunking_result.chunking_strategy.value,
                    "average_chunk_size": chunking_result.average_chunk_size,
                },
            },
            content_chunks=content_chunks,
            quoted_content="",
            thread_summary={},
            search_text="",
        )

    @staticmethod
    def create_calendar_document(event: CalendarEvent) -> VespaDocumentType:
        """Create a Vespa document from a CalendarEvent"""
        from services.vespa_loader.services.document_chunking_service import (
            DocumentChunkingService,
        )

        calendar_event = event.event

        # Create chunks using the chunking service
        chunking_service = DocumentChunkingService()
        chunking_result = chunking_service.chunk_document(
            document_id=calendar_event.id,
            content=calendar_event.description or "",
            document_type="calendar",
            metadata={
                "document_type": "calendar",  # Add document_type for chunking service
                "provider": calendar_event.provider,
                "title": calendar_event.title,
                "calendar_id": calendar_event.calendar_id,
            },
        )

        # Extract chunk content for Vespa indexing
        content_chunks = [chunk.content for chunk in chunking_result.chunks]

        return VespaDocumentType(
            id=calendar_event.id,
            user_id=event.user_id,
            type="calendar",
            provider=calendar_event.provider,
            subject=calendar_event.title,
            body=calendar_event.description or "",
            from_address=calendar_event.organizer,
            to_addresses=calendar_event.attendees,
            thread_id="",
            folder=calendar_event.calendar_id,
            created_at=calendar_event.start_time,
            updated_at=calendar_event.end_time,
            content_chunks=content_chunks,
            metadata={
                "operation": event.operation,
                "last_updated": (
                    event.last_updated.isoformat() if event.last_updated else None
                ),
                "sync_timestamp": (
                    event.sync_timestamp.isoformat() if event.sync_timestamp else None
                ),
                "event_type": "calendar",
                "all_day": calendar_event.all_day,
                "location": calendar_event.location,
                "status": calendar_event.status,
                "visibility": calendar_event.visibility,
                "recurrence": calendar_event.recurrence,
                "reminders": calendar_event.reminders,
                "attachments": calendar_event.attachments,
                "color_id": calendar_event.color_id,
                "html_link": calendar_event.html_link,
                "chunking_info": {
                    "total_chunks": chunking_result.total_chunks,
                    "chunking_strategy": chunking_result.chunking_strategy.value,
                    "average_chunk_size": chunking_result.average_chunk_size,
                },
            },
        )

    @staticmethod
    def create_contact_document(event: ContactEvent) -> VespaDocumentType:
        """Create a Vespa document from a ContactEvent"""
        from services.vespa_loader.services.document_chunking_service import (
            DocumentChunkingService,
        )

        contact = event.contact

        # Create chunks using the chunking service
        chunking_service = DocumentChunkingService()
        chunking_result = chunking_service.chunk_document(
            document_id=contact.id,
            content=contact.notes or "",
            document_type="contact",
            metadata={
                "document_type": "contact",  # Add document_type for chunking service
                "provider": contact.provider,
                "display_name": contact.display_name,
                "email_addresses": contact.email_addresses,
            },
        )

        # Extract chunk content for Vespa indexing
        content_chunks = [chunk.content for chunk in chunking_result.chunks]

        return VespaDocumentType(
            id=contact.id,
            user_id=event.user_id,
            type="contact",
            provider=contact.provider,
            subject=contact.display_name,
            body=contact.notes or "",
            from_address="",
            to_addresses=contact.email_addresses,
            thread_id="",
            folder="",
            created_at=None,
            updated_at=contact.last_modified,
            content_chunks=content_chunks,
            metadata={
                "operation": event.operation,
                "last_updated": (
                    event.last_updated.isoformat() if event.last_updated else None
                ),
                "sync_timestamp": (
                    event.sync_timestamp.isoformat() if event.sync_timestamp else None
                ),
                "contact_type": "contact",
                "given_name": contact.given_name,
                "family_name": contact.family_name,
                "phone_numbers": contact.phone_numbers,
                "addresses": contact.addresses,
                "organizations": contact.organizations,
                "birthdays": (
                    [bd.isoformat() for bd in contact.birthdays]
                    if contact.birthdays
                    else []
                ),
                "photos": contact.photos,
                "groups": contact.groups,
                "tags": contact.tags,
                "chunking_info": {
                    "total_chunks": chunking_result.total_chunks,
                    "chunking_strategy": chunking_result.chunking_strategy.value,
                    "average_chunk_size": chunking_result.average_chunk_size,
                },
            },
        )

    @staticmethod
    def create_document_document(event: DocumentEvent) -> VespaDocumentType:
        """Create a Vespa document from a DocumentEvent"""
        from services.vespa_loader.services.document_chunking_service import (
            DocumentChunkingService,
        )

        document = event.document

        # Create chunks using the chunking service
        chunking_service = DocumentChunkingService()
        chunking_result = chunking_service.chunk_document(
            document_id=document.id,
            content=document.content,
            document_type=document.content_type,
            metadata={
                "document_type": document.content_type,  # Add document_type for chunking service
                "provider": document.provider,
                "content_type": document.content_type,
                "title": document.title,
            },
        )

        # Extract chunk content for Vespa indexing
        content_chunks = [chunk.content for chunk in chunking_result.chunks]

        return VespaDocumentType(
            id=document.id,
            user_id=event.user_id,
            type=document.content_type,
            provider=document.provider,
            subject=document.title,
            body=document.content,
            from_address=document.owner_email,
            to_addresses=[],
            thread_id="",
            folder="",
            created_at=None,
            updated_at=None,
            content_chunks=content_chunks,  # Populate the existing chunks field
            metadata={
                "operation": event.operation,
                "last_updated": (
                    event.last_updated.isoformat() if event.last_updated else None
                ),
                "sync_timestamp": (
                    event.sync_timestamp.isoformat() if event.sync_timestamp else None
                ),
                "content_type": document.content_type,
                "provider_document_id": document.provider_document_id,
                "permissions": document.permissions,
                "tags": document.tags,
                "document_metadata": document.metadata,
                "chunking_info": {
                    "total_chunks": chunking_result.total_chunks,
                    "chunking_strategy": chunking_result.chunking_strategy.value,
                    "average_chunk_size": chunking_result.average_chunk_size,
                },
            },
        )

    @staticmethod
    def create_todo_document(event: TodoEvent) -> VespaDocumentType:
        """Create a Vespa document from a TodoEvent"""
        from services.vespa_loader.services.document_chunking_service import (
            DocumentChunkingService,
        )

        todo = event.todo

        # Create chunks using the chunking service
        chunking_service = DocumentChunkingService()
        chunking_result = chunking_service.chunk_document(
            document_id=todo.id,
            content=todo.description or "",
            document_type="todo",
            metadata={
                "document_type": "todo",  # Add document_type for chunking service
                "provider": todo.provider,
                "title": todo.title,
                "list_id": todo.list_id,
            },
        )

        # Extract chunk content for Vespa indexing
        content_chunks = [chunk.content for chunk in chunking_result.chunks]

        return VespaDocumentType(
            id=todo.id,
            user_id=event.user_id,
            type="todo",
            provider=todo.provider,
            subject=todo.title,
            body=todo.description or "",
            from_address=todo.creator_email,
            to_addresses=[todo.assignee_email] if todo.assignee_email else [],
            thread_id="",
            folder=todo.list_id or "",
            created_at=None,
            updated_at=todo.due_date,
            content_chunks=content_chunks,
            metadata={
                "operation": event.operation,
                "last_updated": (
                    event.last_updated.isoformat() if event.last_updated else None
                ),
                "sync_timestamp": (
                    event.sync_timestamp.isoformat() if event.sync_timestamp else None
                ),
                "todo_type": "todo",
                "status": todo.status,
                "priority": todo.priority,
                "due_date": todo.due_date.isoformat() if todo.due_date else None,
                "completed_date": (
                    todo.completed_date.isoformat() if todo.completed_date else None
                ),
                "assignee_email": todo.assignee_email,
                "creator_email": todo.creator_email,
                "parent_todo_id": todo.parent_todo_id,
                "subtask_ids": todo.subtask_ids,
                "list_id": todo.list_id,
                "provider_todo_id": todo.provider_todo_id,
                "tags": todo.tags,
                "chunking_info": {
                    "total_chunks": chunking_result.total_chunks,
                    "chunking_strategy": chunking_result.chunking_strategy.value,
                    "average_chunk_size": chunking_result.average_chunk_size,
                },
            },
        )

    @classmethod
    def create_document_from_event(cls, event: Any) -> VespaDocumentType:
        """Create a Vespa document from any supported event type."""
        if isinstance(event, EmailEvent):
            return cls.create_email_document(event)
        elif isinstance(event, CalendarEvent):
            return cls.create_calendar_document(event)
        elif isinstance(event, ContactEvent):
            return cls.create_contact_document(event)
        elif isinstance(event, DocumentEvent):
            return cls.create_document_document(event)
        elif isinstance(event, TodoEvent):
            return cls.create_todo_document(event)
        else:
            raise ValueError(f"Unsupported event type: {type(event).__name__}")

    @classmethod
    def get_supported_event_types(cls) -> List[str]:
        """Get list of supported event type names."""
        return [
            "EmailEvent",
            "CalendarEvent",
            "ContactEvent",
            "DocumentEvent",
            "TodoEvent",
        ]


def parse_event_by_topic(
    topic_name: str, raw_data: Dict[str, Any], message_id: str
) -> SupportedEventType:
    """Parse raw data into appropriate typed event based on topic name"""
    try:
        if topic_name == "emails":
            email_event: EmailEvent = EmailEvent(**raw_data)
            logger.debug(
                f"Parsed as EmailEvent: message_id={message_id}, user_id={email_event.user_id}, email_id={email_event.email.id}"
            )
            return email_event
        elif topic_name == "calendars":
            calendar_event: CalendarEvent = CalendarEvent(**raw_data)
            logger.debug(
                f"Parsed as CalendarEvent: message_id={message_id}, user_id={calendar_event.user_id}, event_id={calendar_event.event.id}"
            )
            return calendar_event
        elif topic_name in [
            "word_documents",
            "sheet_documents",
            "presentation_documents",
            "task_documents",
        ]:
            document_event: DocumentEvent = DocumentEvent(**raw_data)
            logger.debug(
                f"Parsed as DocumentEvent: message_id={message_id}, user_id={document_event.user_id}, document_id={document_event.document.id}, content_type={document_event.content_type}"
            )
            return document_event
        elif topic_name == "contacts":
            contact_event: ContactEvent = ContactEvent(**raw_data)
            logger.debug(
                f"Parsed as ContactEvent: message_id={message_id}, user_id={contact_event.user_id}, contact_id={contact_event.contact.id}"
            )
            return contact_event
        elif topic_name == "todos":
            todo_event: TodoEvent = TodoEvent(**raw_data)
            logger.debug(
                f"Parsed as TodoEvent: message_id={message_id}, user_id={todo_event.user_id}, todo_id={todo_event.todo.id}"
            )
            return todo_event
        else:
            logger.warning(
                f"Unknown topic {topic_name}, message_id={message_id} - skipping"
            )
            raise ValueError(f"Unsupported topic: {topic_name}")
    except Exception as e:
        logger.error(
            f"Failed to parse event for topic {topic_name}, message_id={message_id}: {e}"
        )
        raise


def process_message(
    topic_name: str, raw_data: Dict[str, Any], message_id: str
) -> VespaDocumentType:
    """
    Single entry point to process a raw message into a Vespa document.

    This function combines event parsing and document creation in one step.

    Args:
        topic_name: The Pub/Sub topic name
        raw_data: Raw JSON data from the message
        message_id: Message ID for logging

    Returns:
        VespaDocumentType ready for indexing

    Raises:
        ValueError: If topic is unsupported or data is invalid
        ValidationError: If event data doesn't validate
    """
    try:
        # Step 1: Parse raw data into typed event
        event = parse_event_by_topic(topic_name, raw_data, message_id)

        # Step 2: Create Vespa document from typed event
        document = VespaDocumentFactory.create_document_from_event(event)

        logger.info(
            f"Successfully processed message {message_id} from topic {topic_name} "
            f"into document {document.id} for user {document.user_id}"
        )

        return document

    except Exception as e:
        logger.error(
            f"Failed to process message {message_id} from topic {topic_name}: {e}"
        )
        raise
