"""
Contact discovery service for managing email contacts from various events.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from uuid import uuid4

from services.common.events import (
    EmailEvent, CalendarEvent, ContactEvent, DocumentEvent, TodoEvent
)
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
                contacts_to_process.append({
                    'email': event.email.from_address,
                    'name': event.email.from_name,
                    'event_type': 'email',
                    'timestamp': event.last_updated or datetime.utcnow()
                })
            
            # To addresses
            if event.email.to_addresses:
                for to_addr in event.email.to_addresses:
                    if isinstance(to_addr, dict):
                        email = to_addr.get('email')
                        name = to_addr.get('name')
                    else:
                        email = to_addr
                        name = None
                    
                    if email:
                        contacts_to_process.append({
                            'email': email,
                            'name': name,
                            'event_type': 'email',
                            'timestamp': event.last_updated or datetime.utcnow()
                        })
            
            # CC addresses
            if event.email.cc_addresses:
                for cc_addr in event.email.cc_addresses:
                    if isinstance(cc_addr, dict):
                        email = cc_addr.get('email')
                        name = cc_addr.get('name')
                    else:
                        email = cc_addr
                        name = None
                    
                    if email:
                        contacts_to_process.append({
                            'email': email,
                            'name': name,
                            'event_type': 'email',
                            'timestamp': event.last_updated or datetime.utcnow()
                        })
            
            # Process discovered contacts
            for contact_info in contacts_to_process:
                self._process_discovered_contact(
                    user_id=event.user_id,
                    email=contact_info['email'],
                    name=contact_info['name'],
                    event_type=contact_info['event_type'],
                    timestamp=contact_info['timestamp'],
                    source_service='email_sync'
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
                    email = organizer.get('email')
                    name = organizer.get('name')
                else:
                    email = organizer
                    name = None
                
                if email:
                    contacts_to_process.append({
                        'email': email,
                        'name': name,
                        'event_type': 'calendar',
                        'timestamp': event.last_updated or datetime.utcnow()
                    })
            
            # Attendees
            if event.event.attendees:
                for attendee in event.event.attendees:
                    if isinstance(attendee, dict):
                        email = attendee.get('email')
                        name = attendee.get('name')
                    else:
                        email = attendee
                        name = None
                    
                    if email:
                        contacts_to_process.append({
                            'email': email,
                            'name': name,
                            'event_type': 'calendar',
                            'timestamp': event.last_updated or datetime.utcnow()
                        })
            
            # Process discovered contacts
            for contact_info in contacts_to_process:
                self._process_discovered_contact(
                    user_id=event.user_id,
                    email=contact_info['email'],
                    name=contact_info['name'],
                    event_type=contact_info['event_type'],
                    timestamp=contact_info['timestamp'],
                    source_service='calendar_sync'
                )
                
        except Exception as e:
            logger.error(f"Error processing calendar event for contact discovery: {e}")
    
    def process_document_event(self, event: DocumentEvent) -> None:
        """Process a document event to discover contacts."""
        try:
            # Extract owner information from document
            if hasattr(event.document, 'owner_email') and event.document.owner_email:
                self._process_discovered_contact(
                    user_id=event.user_id,
                    email=event.document.owner_email,
                    name=None,  # Document owner name not typically available
                    event_type='document',
                    timestamp=event.last_updated or datetime.utcnow(),
                    source_service='document_sync'
                )
                
        except Exception as e:
            logger.error(f"Error processing document event for contact discovery: {e}")
    
    def process_todo_event(self, event: TodoEvent) -> None:
        """Process a todo event to discover contacts."""
        try:
            # Extract assignee information from todo
            if hasattr(event.todo, 'assignee_email') and event.todo.assignee_email:
                self._process_discovered_contact(
                    user_id=event.user_id,
                    email=event.todo.assignee_email,
                    name=None,  # Todo assignee name not typically available
                    event_type='todo',
                    timestamp=event.last_updated or datetime.utcnow(),
                    source_service='todo_sync'
                )
                
        except Exception as e:
            logger.error(f"Error processing todo event for contact discovery: {e}")
    
    def _process_discovered_contact(
        self,
        user_id: str,
        email: str,
        name: Optional[str],
        event_type: str,
        timestamp: datetime,
        source_service: str
    ) -> None:
        """Process a discovered contact."""
        try:
            # Skip if email is invalid or is the user's own email
            if not email or '@' not in email:
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
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
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
            return ' '.join(parts[1:])
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
                sync_timestamp=contact.updated_at
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
            contact for contact in self._contacts_cache.values()
            if contact.user_id == user_id
        ]
        
        # Sort by relevance score (descending)
        user_contacts.sort(key=lambda c: c.relevance_score, reverse=True)
        
        return user_contacts[:limit]
    
    def search_contacts(
        self,
        user_id: str,
        query: str,
        limit: int = 20
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
            if (query_lower in contact.email_address.lower() or
                (contact.display_name and query_lower in contact.display_name.lower()) or
                (contact.given_name and query_lower in contact.given_name.lower()) or
                (contact.family_name and query_lower in contact.family_name.lower())):
                
                matching_contacts.append(contact)
        
        # Sort by relevance score
        matching_contacts.sort(key=lambda c: c.relevance_score, reverse=True)
        
        return matching_contacts[:limit]
    
    def update_contact(
        self,
        user_id: str,
        email: str,
        update_data: EmailContactUpdate
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
        contact.updated_at = datetime.utcnow()
        
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
            contact for contact in self._contacts_cache.values()
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
            "by_service": service_counts
        }
