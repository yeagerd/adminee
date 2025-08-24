"""
Contact service for business logic operations on contacts.

Provides CRUD operations, search, filtering, and statistics for contacts.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select as sqlmodel_select

from services.common.http_errors import NotFoundError, ValidationError
from services.contacts.models.contact import Contact
from services.contacts.schemas.contact import ContactCreate, EmailContactUpdate

logger = logging.getLogger(__name__)


class ContactService:
    """Service for contact business logic operations."""

    async def create_contact(
        self, session: AsyncSession, contact_data: ContactCreate
    ) -> Contact:
        """Create a new contact."""
        try:
            # Check if contact already exists for this user and email
            existing_contact = await self.get_contact_by_email(
                session, contact_data.user_id, contact_data.email_address
            )

            if existing_contact:
                raise ValidationError(
                    message="Contact already exists for this user and email",
                    field="email_address",
                )

            # Create new contact
            contact = Contact(
                user_id=contact_data.user_id,
                email_address=contact_data.email_address.lower(),
                display_name=contact_data.display_name,
                given_name=contact_data.given_name,
                family_name=contact_data.family_name,
                tags=contact_data.tags or [],
                notes=contact_data.notes,
            )

            # Add to database
            session.add(contact)
            await session.commit()
            await session.refresh(contact)

            logger.info(
                f"Created new contact: {contact.email_address} for user {contact.user_id}"
            )
            return contact

        except Exception as e:
            logger.error(f"Error creating contact: {e}")
            await session.rollback()
            raise

    async def get_contact_by_id(
        self, session: AsyncSession, contact_id: str, user_id: str
    ) -> Optional[Contact]:
        """Get a contact by ID and user ID."""
        try:
            result = await session.execute(
                select(Contact).where(
                    Contact.id == contact_id, Contact.user_id == user_id  # type: ignore
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting contact {contact_id}: {e}")
            return None

    async def get_contact_by_email(
        self, session: AsyncSession, user_id: str, email: str
    ) -> Optional[Contact]:
        """Get a contact by email and user ID."""
        try:
            result = await session.execute(
                select(Contact).where(
                    Contact.user_id == user_id, Contact.email_address == email.lower()  # type: ignore
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting contact by email {email}: {e}")
            return None

    async def list_contacts(
        self,
        session: AsyncSession,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        tags: Optional[List[str]] = None,
        source_services: Optional[List[str]] = None,
    ) -> List[Contact]:
        """List contacts for a user with optional filtering."""
        try:
            query = select(Contact).where(Contact.user_id == user_id)  # type: ignore

            # Apply filters
            if tags:
                # Filter by tags (contacts must have at least one of the specified tags)
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append(Contact.tags.contains([tag]))  # type: ignore
                query = query.where(or_(*tag_conditions))  # type: ignore

            if source_services:
                # Filter by source services (contacts must have at least one of the specified services)
                service_conditions = []
                for service in source_services:
                    service_conditions.append(
                        Contact.source_services.contains([service])  # type: ignore
                    )
                query = query.where(or_(*service_conditions))  # type: ignore

            # Order by relevance score and apply pagination
            query = (
                query.order_by(desc(Contact.relevance_score))  # type: ignore
                .offset(offset)
                .limit(limit)
            )

            result = await session.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error listing contacts for user {user_id}: {e}")
            return []

    async def count_contacts(self, session: AsyncSession, user_id: str) -> int:
        """Count total contacts for a user."""
        try:
            result = await session.execute(
                select(func.count()).where(Contact.user_id == user_id)  # type: ignore
            )
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting contacts for user {user_id}: {e}")
            return 0

    async def search_contacts(
        self,
        session: AsyncSession,
        user_id: str,
        query: str,
        limit: int = 20,
        tags: Optional[List[str]] = None,
        source_services: Optional[List[str]] = None,
    ) -> List[Contact]:
        """Search contacts for a user by query."""
        try:
            if not query:
                return await self.list_contacts(
                    session, user_id, limit, tags=tags, source_services=source_services
                )

            query_lower = query.lower()
            base_query = select(Contact).where(
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

            # Apply filters
            if tags:
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append(Contact.tags.contains([tag]))  # type: ignore
                base_query = base_query.where(or_(*tag_conditions))  # type: ignore

            if source_services:
                service_conditions = []
                for service in source_services:
                    service_conditions.append(
                        Contact.source_services.contains([service])  # type: ignore
                    )
                base_query = base_query.where(or_(*service_conditions))  # type: ignore

            # Order by relevance score and apply limit
            base_query = base_query.order_by(desc(Contact.relevance_score)).limit(  # type: ignore
                limit
            )

            result = await session.execute(base_query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error searching contacts for user {user_id}: {e}")
            return []

    async def update_contact(
        self,
        session: AsyncSession,
        contact_id: str,
        user_id: str,
        update_data: EmailContactUpdate,
    ) -> Optional[Contact]:
        """Update an existing contact."""
        try:
            contact = await self.get_contact_by_id(session, contact_id, user_id)
            if not contact:
                return None

            # Apply updates
            if update_data.display_name is not None:
                contact.display_name = update_data.display_name
                # Update derived fields
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
            from datetime import datetime, timezone

            contact.updated_at = datetime.now(timezone.utc)

            # Recalculate relevance score
            contact.calculate_relevance_score()

            # Update in database
            await session.commit()
            await session.refresh(contact)

            logger.info(f"Updated contact {contact_id}")
            return contact

        except Exception as e:
            logger.error(f"Error updating contact {contact_id}: {e}")
            await session.rollback()
            return None

    async def delete_contact(
        self, session: AsyncSession, contact_id: str, user_id: str
    ) -> bool:
        """Delete a contact."""
        try:
            contact = await self.get_contact_by_id(session, contact_id, user_id)
            if not contact:
                return False

            await session.delete(contact)
            await session.commit()

            logger.info(f"Deleted contact {contact_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting contact {contact_id}: {e}")
            await session.rollback()
            return False

    async def get_contact_stats(
        self, session: AsyncSession, user_id: str
    ) -> Dict[str, Any]:
        """Get contact statistics for a user."""
        try:
            # Get total contacts
            total_contacts = await self.count_contacts(session, user_id)

            # Get total events
            result = await session.execute(
                select(func.coalesce(func.sum(Contact.total_event_count), 0)).where(
                    Contact.user_id == user_id  # type: ignore
                )
            )
            total_events = result.scalar() or 0

            # Get contacts by source service
            result = await session.execute(
                select(Contact).where(Contact.user_id == user_id)  # type: ignore
            )
            source_services_data = result.scalars().all()

            service_counts: Dict[str, int] = {}
            for contact in source_services_data:
                if hasattr(contact, "source_services") and contact.source_services:
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
