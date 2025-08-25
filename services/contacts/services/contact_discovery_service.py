"""
Contact discovery service for managing email contacts from various events.

Moved from services/user/services/contact_discovery_service.py and adapted
for database persistence in the Contacts Service.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select as sqlmodel_select

from services.common.events import (
    CalendarEvent,
    ContactEvent,
    DocumentEvent,
    EmailEvent,
    TodoEvent,
)
from services.common.events.todo_events import TodoData, TodoEvent
from services.common.logging_config import get_logger
from services.common.pubsub_client import PubSubClient
from services.contacts.models.contact import Contact
from services.contacts.schemas.contact import EmailContactUpdate

logger = get_logger(__name__)


class ContactDiscoveryService:
    """Service for discovering and managing email contacts from events."""

    def __init__(self, pubsub_client: PubSubClient):
        self.pubsub_client = pubsub_client

    async def process_email_event(
        self, event: EmailEvent, session: AsyncSession
    ) -> None:
        """Process an email event to discover contacts."""
        try:
            # Extract contacts from email
            contacts_to_process = []

            # From address
            if event.email.from_address:
                contacts_to_process.append(
                    {
                        "email": event.email.from_address,
                        "name": None,  # Names not available in current model
                        "event_type": "email",
                        "timestamp": event.last_updated or datetime.now(timezone.utc),
                    }
                )

            # To addresses
            if event.email.to_addresses:
                for to_addr in event.email.to_addresses:
                    # Current model has to_addresses as list of strings
                    if isinstance(to_addr, str):
                        email: Optional[str] = to_addr
                        name: Optional[str] = None
                    else:
                        # Fallback for backward compatibility
                        email = (
                            to_addr.get("email")
                            if isinstance(to_addr, dict)
                            else str(to_addr)
                        )
                        name = (
                            to_addr.get("name") if isinstance(to_addr, dict) else None
                        )

                    if email and isinstance(email, str):
                        contacts_to_process.append(
                            {
                                "email": email,
                                "name": name,
                                "event_type": "email",
                                "timestamp": event.last_updated
                                or datetime.now(timezone.utc),
                            }
                        )

            # CC addresses
            if event.email.cc_addresses:
                for cc_addr in event.email.cc_addresses:
                    # Current model has cc_addresses as list of strings
                    if isinstance(cc_addr, str):
                        cc_email: Optional[str] = cc_addr
                        cc_name: Optional[str] = None
                    else:
                        # Fallback for backward compatibility
                        cc_email = (
                            cc_addr.get("email")
                            if isinstance(cc_addr, dict)
                            else str(cc_addr)
                        )
                        cc_name = (
                            cc_addr.get("name") if isinstance(cc_addr, dict) else None
                        )

                    if cc_email and isinstance(cc_email, str):
                        contacts_to_process.append(
                            {
                                "email": cc_email,
                                "name": cc_name,
                                "event_type": "email",
                                "timestamp": event.last_updated
                                or datetime.now(timezone.utc),
                            }
                        )

            # Process discovered contacts
            for contact_info in contacts_to_process:
                await self._process_discovered_contact(
                    session=session,
                    user_id=event.user_id,
                    email=str(contact_info["email"]),
                    name=(
                        str(contact_info["name"])
                        if contact_info["name"] is not None
                        and not isinstance(contact_info["name"], datetime)
                        else None
                    ),
                    event_type=str(contact_info["event_type"]),
                    timestamp=(
                        contact_info["timestamp"]
                        if isinstance(contact_info["timestamp"], datetime)
                        else datetime.now(timezone.utc)
                    ),
                    source_service="email_sync",
                )

        except Exception as e:
            logger.error(f"Error processing email event for contact discovery: {e}")

    async def process_calendar_event(
        self, event: CalendarEvent, session: AsyncSession
    ) -> None:
        """Process a calendar event to discover contacts."""
        try:
            contacts_to_process = []

            # Organizer
            if event.event.organizer:
                organizer = event.event.organizer
                if isinstance(organizer, dict):
                    email = organizer.get("email")
                    name = organizer.get("name")
                else:
                    email = organizer
                    name = None

                if email:
                    contacts_to_process.append(
                        {
                            "email": email,
                            "name": name,
                            "event_type": "calendar",
                            "timestamp": event.last_updated
                            or datetime.now(timezone.utc),
                        }
                    )

            # Attendees
            if event.event.attendees:
                for attendee in event.event.attendees:
                    if isinstance(attendee, dict):
                        email = attendee.get("email")
                        name = attendee.get("name")
                    else:
                        email = attendee
                        name = None

                    if email:
                        contacts_to_process.append(
                            {
                                "email": email,
                                "name": name,
                                "event_type": "calendar",
                                "timestamp": event.last_updated
                                or datetime.now(timezone.utc),
                            }
                        )

            # Process discovered contacts
            for contact_info in contacts_to_process:
                await self._process_discovered_contact(
                    session=session,
                    user_id=event.user_id,
                    email=str(contact_info["email"]),
                    name=(
                        str(contact_info["name"])
                        if contact_info["name"] is not None
                        and not isinstance(contact_info["name"], datetime)
                        else None
                    ),
                    event_type=str(contact_info["event_type"]),
                    timestamp=(
                        contact_info["timestamp"]
                        if isinstance(contact_info["timestamp"], datetime)
                        else datetime.now(timezone.utc)
                    ),
                    source_service="calendar_sync",
                )

        except Exception as e:
            logger.error(f"Error processing calendar event for contact discovery: {e}")

    async def process_document_event(
        self, event: DocumentEvent, session: AsyncSession
    ) -> None:
        """Process a document event to discover contacts."""
        try:
            # Extract owner information from document
            if hasattr(event.document, "owner_email") and event.document.owner_email:
                await self._process_discovered_contact(
                    session=session,
                    user_id=event.user_id,
                    email=event.document.owner_email,
                    name=None,  # Document owner name not typically available
                    event_type="document",
                    timestamp=event.last_updated or datetime.now(timezone.utc),
                    source_service="document_sync",
                )

        except Exception as e:
            logger.error(f"Error processing document event for contact discovery: {e}")

    async def process_todo_event(self, event: TodoEvent, session: AsyncSession) -> None:
        """Process a todo event to discover contacts."""
        try:
            # Validate event structure first
            if not self._validate_todo_event_structure(event):
                logger.warning(
                    "Todo event validation failed, skipping contact discovery"
                )
                return

            # Extract assignee information from todo with proper field validation
            assignee_email = self._extract_todo_assignee_email(event.todo)

            if assignee_email:
                # Extract creator information as well for comprehensive contact discovery
                creator_email = self._extract_todo_creator_email(event.todo)

                # Process assignee contact
                await self._process_discovered_contact(
                    session=session,
                    user_id=event.user_id,
                    email=assignee_email,
                    name=self._extract_todo_assignee_name(event.todo),
                    event_type="todo_assignee",
                    timestamp=event.last_updated or datetime.now(timezone.utc),
                    source_service="todo_sync",
                )

                # Process creator contact if different from assignee
                if creator_email and creator_email != assignee_email:
                    await self._process_discovered_contact(
                        session=session,
                        user_id=event.user_id,
                        email=creator_email,
                        name=self._extract_todo_creator_name(event.todo),
                        event_type="todo_creator",
                        timestamp=event.last_updated or datetime.now(timezone.utc),
                        source_service="todo_sync",
                    )

                # Process shared list contacts if available
                await self._process_todo_shared_contacts(event, session)

            else:
                logger.debug(f"No assignee email found in todo event {event.todo.id}")

        except Exception as e:
            logger.error(f"Error processing todo event for contact discovery: {e}")
            # Log additional context for debugging
            if event and event.todo:
                logger.error(
                    f"Todo event context: id={event.todo.id}, user_id={event.user_id}, operation={event.operation}"
                )

    def _extract_todo_assignee_email(self, todo: TodoData) -> Optional[str]:
        """Extract assignee email with proper field validation."""
        try:
            # Check if assignee_email field exists and has a valid value
            if hasattr(todo, "assignee_email"):
                assignee_email = getattr(todo, "assignee_email")
                if (
                    assignee_email
                    and isinstance(assignee_email, str)
                    and "@" in assignee_email
                ):
                    return assignee_email.strip()

            # Fallback: check metadata for assignee information
            if hasattr(todo, "metadata") and todo.metadata:
                assignee_email = todo.metadata.get("assignee_email")
                if (
                    assignee_email
                    and isinstance(assignee_email, str)
                    and "@" in assignee_email
                ):
                    return assignee_email.strip()

            return None

        except Exception as e:
            logger.warning(
                f"Error extracting assignee email from todo {getattr(todo, 'id', 'unknown')}: {e}"
            )
            return None

    def _extract_todo_creator_email(self, todo: TodoData) -> Optional[str]:
        """Extract creator email with proper field validation."""
        try:
            # Check if creator_email field exists and has a valid value
            if hasattr(todo, "creator_email"):
                creator_email = getattr(todo, "creator_email")
                if (
                    creator_email
                    and isinstance(creator_email, str)
                    and "@" in creator_email
                ):
                    return creator_email.strip()

            # Fallback: check metadata for creator information
            if hasattr(todo, "metadata") and todo.metadata:
                creator_email = todo.metadata.get("creator_email")
                if (
                    creator_email
                    and isinstance(creator_email, str)
                    and "@" in creator_email
                ):
                    return creator_email.strip()

            return None

        except Exception as e:
            logger.warning(
                f"Error extracting creator email from todo {getattr(todo, 'id', 'unknown')}: {e}"
            )
            return None

    def _extract_todo_assignee_name(self, todo: TodoData) -> Optional[str]:
        """Extract assignee name with graceful degradation."""
        try:
            # Check metadata for assignee name
            if hasattr(todo, "metadata") and todo.metadata:
                assignee_name = todo.metadata.get("assignee_name")
                if assignee_name and isinstance(assignee_name, str):
                    return assignee_name.strip()

            # Fallback: try to extract from title or description
            if hasattr(todo, "title") and todo.title:
                # Look for patterns like "Assigned to: John Doe" in title
                title = todo.title
                if "assigned to:" in title.lower():
                    name_part = title.split("assigned to:", 1)[1].strip()
                    if name_part and len(name_part) < 100:  # Reasonable name length
                        return name_part

            return None

        except Exception as e:
            logger.debug(
                f"Error extracting assignee name from todo {getattr(todo, 'id', 'unknown')}: {e}"
            )
            return None

    def _extract_todo_creator_name(self, todo: TodoData) -> Optional[str]:
        """Extract creator name with graceful degradation."""
        try:
            # Check metadata for creator name
            if hasattr(todo, "metadata") and todo.metadata:
                creator_name = todo.metadata.get("creator_name")
                if creator_name and isinstance(creator_name, str):
                    return creator_name.strip()

            return None

        except Exception as e:
            logger.debug(
                f"Error extracting creator name from todo {getattr(todo, 'id', 'unknown')}: {e}"
            )
            return None

    async def _process_todo_shared_contacts(
        self, event: TodoEvent, session: AsyncSession
    ) -> None:
        """Process contacts from shared todo lists."""
        try:
            if not event.todo or not hasattr(event.todo, "metadata"):
                return

            # Check for shared list information
            shared_emails = []

            # Look for shared_with field in metadata
            if event.todo.metadata and "shared_with" in event.todo.metadata:
                shared_emails.extend(event.todo.metadata["shared_with"])

            # Look for list sharing information
            if hasattr(event, "list_id") and event.list_id:
                # This would typically require additional service calls to get list sharing info
                # For now, we'll log that this capability exists
                logger.debug(
                    f"Todo list {event.list_id} may have shared contacts (requires list service integration)"
                )

            # Process shared contacts
            for email in shared_emails:
                if email and isinstance(email, str) and "@" in email:
                    await self._process_discovered_contact(
                        session=session,
                        user_id=event.user_id,
                        email=email.strip(),
                        name=None,  # Shared contact names not typically available
                        event_type="todo_shared",
                        timestamp=event.last_updated or datetime.now(timezone.utc),
                        source_service="todo_sync",
                    )

        except Exception as e:
            logger.warning(f"Error processing shared contacts for todo event: {e}")

    def _validate_todo_event_structure(self, event: TodoEvent) -> bool:
        """Validate todo event structure and required fields."""
        try:
            # Check required fields
            if not event.user_id:
                logger.warning("Todo event missing user_id")
                return False

            if not event.todo:
                logger.warning("Todo event missing todo data")
                return False

            if not event.operation:
                logger.warning("Todo event missing operation")
                return False

            # Check todo data structure
            if not hasattr(event.todo, "id") or not event.todo.id:
                logger.warning("Todo event missing todo.id")
                return False

            # Validate operation type
            valid_operations = ["create", "update", "delete"]
            if event.operation not in valid_operations:
                logger.warning(f"Todo event has invalid operation: {event.operation}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating todo event structure: {e}")
            return False

    async def _process_discovered_contact(
        self,
        session: AsyncSession,
        user_id: str,
        email: str,
        name: Optional[str],
        event_type: str,
        timestamp: datetime,
        source_service: str,
    ) -> None:
        """Process a discovered contact."""
        try:
            # Skip if email is invalid or is the user's own email
            if not email or "@" not in email:
                return

            # Check if contact already exists
            existing_contact = await self.get_contact(session, user_id, email)

            if not existing_contact:
                # Create new contact
                contact = Contact(
                    id=str(uuid4()),
                    user_id=user_id,
                    email_address=email.lower(),
                    display_name=name,
                    given_name=self._extract_given_name(name) if name else None,
                    family_name=self._extract_family_name(name) if name else None,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    source_services=[source_service],  # Initialize with source service
                    notes=None,
                )

                # Add to database
                session.add(contact)
                await session.commit()

                logger.info(f"Created new contact: {email} for user {user_id}")
            else:
                # Update existing contact
                if name and not existing_contact.display_name:
                    existing_contact.display_name = name
                    existing_contact.given_name = self._extract_given_name(name)
                    existing_contact.family_name = self._extract_family_name(name)

                # Add source service if not already present
                if source_service not in existing_contact.source_services:
                    existing_contact.source_services.append(source_service)

                # Add event
                existing_contact.add_event(event_type, timestamp)

                # Calculate relevance score
                existing_contact.calculate_relevance_score()

                # Update in database
                await session.commit()

            # Publish contact update event for Vespa integration
            # Note: We'll need to get the contact again to ensure we have the latest data
            updated_contact = await self.get_contact(session, user_id, email)
            if updated_contact:
                self._publish_contact_update(updated_contact)

        except Exception as e:
            logger.error(f"Error processing discovered contact {email}: {e}")
            await session.rollback()

    def _extract_given_name(self, full_name: str) -> Optional[str]:
        """Extract given name from full name."""
        if not full_name:
            return None

        parts = full_name.strip().split()
        if len(parts) >= 1:
            return parts[0]
        return None

    def _extract_family_name(self, full_name: str) -> Optional[str]:
        """Extract family name from full name."""
        if not full_name:
            return None

        parts = full_name.strip().split()
        if len(parts) >= 2:
            return " ".join(parts[1:])
        return None

    def _publish_contact_update(self, contact: Contact) -> None:
        """Publish contact update event for Vespa integration."""
        try:
            # Convert to Vespa document format
            vespa_doc = contact.to_vespa_document()

            # Create ContactEvent and publish to contacts topic
            from services.common.events.base_events import EventMetadata
            from services.common.events.contact_events import ContactData, ContactEvent

            contact_data = ContactData(
                id=contact.id or str(uuid4()),
                display_name=contact.display_name or contact.email_address,
                given_name=contact.given_name,
                family_name=contact.family_name,
                email_addresses=[contact.email_address],
                provider="contact_discovery",
                provider_contact_id=contact.id or str(uuid4()),
                notes=contact.notes,
                last_modified=contact.updated_at,
            )

            metadata = EventMetadata(
                source_service="contact-discovery",
                user_id=contact.user_id,
                correlation_id=None,
                trace_id=None,
                span_id=None,
                parent_span_id=None,
                request_id=None,
            )

            contact_event = ContactEvent(
                user_id=contact.user_id,
                contact=contact_data,
                operation="update",
                batch_id=None,
                last_updated=contact.last_seen,
                sync_timestamp=contact.updated_at,
                provider="contact_discovery",
                metadata=metadata,
            )

            self.pubsub_client.publish_contact_event(contact_event)

            logger.debug(f"Published contact update for {contact.email_address}")

        except Exception as e:
            logger.error(f"Error publishing contact update: {e}")

    async def get_contact(
        self, session: AsyncSession, user_id: str, email: str
    ) -> Optional[Contact]:
        """Get a contact by user ID and email."""
        try:
            result = await session.execute(
                select(Contact).where(
                    and_(Contact.user_id == user_id, Contact.email_address == email.lower())  # type: ignore
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting contact {email} for user {user_id}: {e}")
            return None

    async def get_user_contacts(
        self, session: AsyncSession, user_id: str, limit: int = 100
    ) -> List[Contact]:
        """Get all contacts for a user, sorted by relevance score."""
        try:
            result = await session.execute(
                select(Contact)
                .where(Contact.user_id == user_id)  # type: ignore
                .order_by(desc(Contact.relevance_score))  # type: ignore
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting contacts for user {user_id}: {e}")
            return []

    async def search_contacts(
        self, session: AsyncSession, user_id: str, query: str, limit: int = 20
    ) -> List[Contact]:
        """Search contacts for a user by name or email."""
        if not query:
            return await self.get_user_contacts(session, user_id, limit)

        try:
            query_lower = query.lower()
            result = await session.execute(
                select(Contact)
                .where(
                    and_(
                        Contact.user_id == user_id,  # type: ignore
                        (
                            Contact.email_address.ilike(f"%{query_lower}%")  # type: ignore
                            | Contact.display_name.ilike(f"%{query_lower}%")  # type: ignore
                            | Contact.given_name.ilike(f"%{query_lower}%")  # type: ignore
                            | Contact.family_name.ilike(f"%{query_lower}%")  # type: ignore
                        ),
                    )
                )
                .order_by(desc(Contact.relevance_score))  # type: ignore
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error searching contacts for user {user_id}: {e}")
            return []

    async def update_contact(
        self,
        session: AsyncSession,
        user_id: str,
        email: str,
        update_data: EmailContactUpdate,
    ) -> Optional[Contact]:
        """Update a contact with new information."""
        contact = await self.get_contact(session, user_id, email)
        if not contact:
            return None

        try:
            # Apply updates
            if update_data.display_name is not None:
                contact.display_name = update_data.display_name
                contact.given_name = self._extract_given_name(update_data.display_name)
                contact.family_name = self._extract_family_name(
                    update_data.display_name
                )

            if update_data.given_name is not None:
                contact.given_name = update_data.given_name

            if update_data.family_name is not None:
                contact.family_name = update_data.family_name

            if update_data.tags is not None:
                contact.tags = update_data.tags

            if update_data.notes is not None:
                contact.notes = update_data.notes

            # Update timestamps
            contact.updated_at = datetime.now(timezone.utc)

            # Recalculate relevance score
            contact.calculate_relevance_score()

            # Update in database
            await session.commit()

            # Publish update
            self._publish_contact_update(contact)

            return contact
        except Exception as e:
            logger.error(f"Error updating contact {email}: {e}")
            await session.rollback()
            return None

    async def remove_contact(
        self, session: AsyncSession, user_id: str, email: str
    ) -> bool:
        """Remove a contact."""
        try:
            contact = await self.get_contact(session, user_id, email)
            if contact:
                await session.delete(contact)
                await session.commit()
                logger.info(f"Removed contact: {email} for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing contact {email}: {e}")
            await session.rollback()
            return False

    async def get_contact_stats(
        self, session: AsyncSession, user_id: str
    ) -> Dict[str, Any]:
        """Get contact statistics for a user."""
        try:
            result = await session.execute(
                select(Contact).where(Contact.user_id == user_id)  # type: ignore
            )
            user_contacts = result.scalars().all()

            total_contacts = len(user_contacts)
            total_events = sum(contact.total_event_count for contact in user_contacts)

            # Count by source service
            service_counts: Dict[str, int] = {}
            for contact in user_contacts:
                for service in contact.source_services:
                    service_counts[service] = service_counts.get(service, 0) + 1

            return {
                "total_contacts": total_contacts,
                "total_events": total_events,
                "by_service": service_counts,
            }
        except Exception as e:
            logger.error(f"Error getting contact stats for user {user_id}: {e}")
            return {
                "total_contacts": 0,
                "total_events": 0,
                "by_service": {},
            }
