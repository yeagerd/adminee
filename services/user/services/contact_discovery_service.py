"""
Contact discovery service for managing email contacts from various events.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from services.common.events import (
    CalendarEvent,
    ContactEvent,
    DocumentEvent,
    EmailEvent,
    TodoEvent,
)
from services.common.events.todo_events import TodoData, TodoEvent
from services.common.models.email_contact import EmailContact, EmailContactUpdate
from services.common.pubsub_client import PubSubClient

logger = logging.getLogger(__name__)


class ContactDiscoveryService:
    """Service for discovering and managing email contacts from events."""

    def __init__(self, pubsub_client: PubSubClient):
        self.pubsub_client = pubsub_client
        self._contacts_cache: Dict[str, EmailContact] = {}

    def process_email_event(self, event: EmailEvent) -> None:
        """Process an email event to discover contacts."""
        try:
            # Extract contacts from email
            contacts_to_process = []

            # From address
            if event.email.from_address:
                contacts_to_process.append(
                    {
                        "email": event.email.from_address,
                        "name": event.email.from_name,
                        "event_type": "email",
                        "timestamp": event.last_updated or datetime.now(timezone.utc),
                    }
                )

            # To addresses
            if event.email.to_addresses:
                for to_addr in event.email.to_addresses:
                    if isinstance(to_addr, dict):
                        email = to_addr.get("email")
                        name = to_addr.get("name")
                    else:
                        email = to_addr
                        name = None

                    if email:
                        contacts_to_process.append(
                            {
                                "email": email,
                                "name": name,
                                "event_type": "email",
                                "timestamp": event.last_updated or datetime.now(timezone.utc),
                            }
                        )

            # CC addresses
            if event.email.cc_addresses:
                for cc_addr in event.email.cc_addresses:
                    if isinstance(cc_addr, dict):
                        email = cc_addr.get("email")
                        name = cc_addr.get("name")
                    else:
                        email = cc_addr
                        name = None

                    if email:
                        contacts_to_process.append(
                            {
                                "email": email,
                                "name": name,
                                "event_type": "email",
                                "timestamp": event.last_updated or datetime.now(timezone.utc),
                            }
                        )

            # Process discovered contacts
            for contact_info in contacts_to_process:
                self._process_discovered_contact(
                    user_id=event.user_id,
                    email=contact_info["email"],
                    name=contact_info["name"],
                    event_type=contact_info["event_type"],
                    timestamp=contact_info["timestamp"],
                    source_service="email_sync",
                )

        except Exception as e:
            logger.error(f"Error processing email event for contact discovery: {e}")

    def process_calendar_event(self, event: CalendarEvent) -> None:
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
                            "timestamp": event.last_updated or datetime.now(timezone.utc),
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
                                "timestamp": event.last_updated or datetime.now(timezone.utc),
                            }
                        )

            # Process discovered contacts
            for contact_info in contacts_to_process:
                self._process_discovered_contact(
                    user_id=event.user_id,
                    email=contact_info["email"],
                    name=contact_info["name"],
                    event_type=contact_info["event_type"],
                    timestamp=contact_info["timestamp"],
                    source_service="calendar_sync",
                )

        except Exception as e:
            logger.error(f"Error processing calendar event for contact discovery: {e}")

    def process_document_event(self, event: DocumentEvent) -> None:
        """Process a document event to discover contacts."""
        try:
            # Extract owner information from document
            if hasattr(event.document, "owner_email") and event.document.owner_email:
                self._process_discovered_contact(
                    user_id=event.user_id,
                    email=event.document.owner_email,
                    name=None,  # Document owner name not typically available
                    event_type="document",
                    timestamp=event.last_updated or datetime.now(timezone.utc),
                    source_service="document_sync",
                )

        except Exception as e:
            logger.error(f"Error processing document event for contact discovery: {e}")

    def process_todo_event(self, event: TodoEvent) -> None:
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
                self._process_discovered_contact(
                    user_id=event.user_id,
                    email=assignee_email,
                    name=self._extract_todo_assignee_name(event.todo),
                    event_type="todo_assignee",
                    timestamp=event.last_updated or datetime.now(timezone.utc),
                    source_service="todo_sync",
                )

                # Process creator contact if different from assignee
                if creator_email and creator_email != assignee_email:
                    self._process_discovered_contact(
                        user_id=event.user_id,
                        email=creator_email,
                        name=self._extract_todo_creator_name(event.todo),
                        event_type="todo_creator",
                        timestamp=event.last_updated or datetime.now(timezone.utc),
                        source_service="todo_sync",
                    )

                # Process shared list contacts if available
                self._process_todo_shared_contacts(event)

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

    def _process_todo_shared_contacts(self, event: TodoEvent) -> None:
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
                    self._process_discovered_contact(
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

    def _process_discovered_contact(
        self,
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

            # Create contact key
            contact_key = f"{user_id}:{email.lower()}"

            # Get or create contact
            contact = self._contacts_cache.get(contact_key)
            if not contact:
                # Create new contact
                contact = EmailContact(
                    id=str(uuid4()),
                    user_id=user_id,
                    email_address=email.lower(),
                    display_name=name,
                    given_name=self._extract_given_name(name) if name else None,
                    family_name=self._extract_family_name(name) if name else None,
                    first_seen=timestamp,
                    last_seen=timestamp,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                self._contacts_cache[contact_key] = contact
                logger.info(f"Created new contact: {email} for user {user_id}")
            else:
                # Update existing contact
                if name and not contact.display_name:
                    contact.display_name = name
                    contact.given_name = self._extract_given_name(name)
                    contact.family_name = self._extract_family_name(name)

                # Add source service if not already present
                if source_service not in contact.source_services:
                    contact.source_services.append(source_service)

            # Add event
            contact.add_event(event_type, timestamp)

            # Calculate relevance score
            contact.calculate_relevance_score()

            # Publish contact update event for Vespa integration
            self._publish_contact_update(contact)

        except Exception as e:
            logger.error(f"Error processing discovered contact {email}: {e}")

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

    def _publish_contact_update(self, contact: EmailContact) -> None:
        """Publish contact update event for Vespa integration."""
        try:
            # Convert to Vespa document format
            vespa_doc = contact.to_vespa_document()

            # Publish to contacts topic
            self.pubsub_client.publish_contact_event(
                user_id=contact.user_id,
                contact=vespa_doc,
                operation="update",
                batch_id=None,
                last_updated=contact.last_seen,
                sync_timestamp=contact.updated_at,
            )

            logger.debug(f"Published contact update for {contact.email_address}")

        except Exception as e:
            logger.error(f"Error publishing contact update: {e}")

    def get_contact(self, user_id: str, email: str) -> Optional[EmailContact]:
        """Get a contact by user ID and email."""
        contact_key = f"{user_id}:{email.lower()}"
        return self._contacts_cache.get(contact_key)

    def get_user_contacts(self, user_id: str, limit: int = 100) -> List[EmailContact]:
        """Get all contacts for a user, sorted by relevance score."""
        user_contacts = [
            contact
            for contact in self._contacts_cache.values()
            if contact.user_id == user_id
        ]

        # Sort by relevance score (descending)
        user_contacts.sort(key=lambda c: c.relevance_score, reverse=True)

        return user_contacts[:limit]

    def search_contacts(
        self, user_id: str, query: str, limit: int = 20
    ) -> List[EmailContact]:
        """Search contacts for a user by name or email."""
        if not query:
            return self.get_user_contacts(user_id, limit)

        query_lower = query.lower()
        matching_contacts = []

        for contact in self._contacts_cache.values():
            if contact.user_id != user_id:
                continue

            # Check if query matches email, name, or display name
            if (
                query_lower in contact.email_address.lower()
                or (
                    contact.display_name and query_lower in contact.display_name.lower()
                )
                or (contact.given_name and query_lower in contact.given_name.lower())
                or (contact.family_name and query_lower in contact.family_name.lower())
            ):

                matching_contacts.append(contact)

        # Sort by relevance score
        matching_contacts.sort(key=lambda c: c.relevance_score, reverse=True)

        return matching_contacts[:limit]

    def update_contact(
        self, user_id: str, email: str, update_data: EmailContactUpdate
    ) -> Optional[EmailContact]:
        """Update a contact with new information."""
        contact = self.get_contact(user_id, email)
        if not contact:
            return None

        # Apply updates
        if update_data.display_name is not None:
            contact.display_name = update_data.display_name
            contact.given_name = self._extract_given_name(update_data.display_name)
            contact.family_name = self._extract_family_name(update_data.display_name)

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

        # Publish update
        self._publish_contact_update(contact)

        return contact

    def remove_contact(self, user_id: str, email: str) -> bool:
        """Remove a contact."""
        contact_key = f"{user_id}:{email.lower()}"
        if contact_key in self._contacts_cache:
            del self._contacts_cache[contact_key]
            logger.info(f"Removed contact: {email} for user {user_id}")
            return True
        return False

    def get_contact_stats(self, user_id: str) -> Dict[str, Any]:
        """Get contact statistics for a user."""
        user_contacts = [
            contact
            for contact in self._contacts_cache.values()
            if contact.user_id == user_id
        ]

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
